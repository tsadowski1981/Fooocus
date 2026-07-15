"""Minimal Tuya Cloud OpenAPI client (token auth + device status).

Deliberately dependency-free beyond `requests`: the official `tuya-iot-py-sdk`
and the popular `tinytuya` package both pull in `cryptography` (for the local
LAN protocol's AES encryption), which requires a Rust toolchain to build on
platforms without prebuilt wheels (e.g. Termux/Android). We only ever call
the Cloud API (token + device status), which just needs HMAC-SHA256 request
signing - available from the stdlib `hmac`/`hashlib`. See:
https://developer.tuya.com/en/docs/iot/open-api/api-reference/singnature
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import requests

REGION_ENDPOINTS = {
    "eu": "https://openapi.tuyaeu.com",
    "eu-w": "https://openapi-weaz.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "us-e": "https://openapi-ueaz.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
    "sg": "https://openapi-sg.iotbing.com",
}


class TuyaApiError(Exception):
    pass


class TuyaCloudClient:
    def __init__(self, api_region: str, access_id: str, access_secret: str):
        self.endpoint = REGION_ENDPOINTS.get(api_region, REGION_ENDPOINTS["eu"])
        self.access_id = access_id
        self.access_secret = access_secret
        self._access_token = ""
        self._token_expire_at_ms = 0

    def _sign(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None,
        body: dict[str, Any] | None,
        token: str,
    ) -> tuple[str, str]:
        body_bytes = json.dumps(body).encode("utf8") if body else b""
        content_sha256 = hashlib.sha256(body_bytes).hexdigest()
        query = ""
        if params:
            keys = sorted(params.keys())
            query = "?" + "&".join(f"{k}={params[k]}" for k in keys)
        string_to_sign = f"{method}\n{content_sha256}\n\n{path}{query}"
        t = str(int(time.time() * 1000))
        message = f"{self.access_id}{token}{t}{string_to_sign}"
        sign = (
            hmac.new(self.access_secret.encode("utf8"), message.encode("utf8"), hashlib.sha256)
            .hexdigest()
            .upper()
        )
        return sign, t

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        authed: bool = True,
    ) -> dict[str, Any]:
        token = self._access_token if authed else ""
        sign, t = self._sign(method, path, params, body, token)
        headers = {
            "client_id": self.access_id,
            "sign": sign,
            "sign_method": "HMAC-SHA256",
            "t": t,
        }
        if authed:
            headers["access_token"] = self._access_token
        response = requests.request(
            method, f"{self.endpoint}{path}", params=params, json=body, headers=headers, timeout=15
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise TuyaApiError(f"Tuya API error calling {path}: {json.dumps(data, ensure_ascii=False)}")
        return data

    def _get(self, path: str, params: dict[str, Any] | None = None, authed: bool = True) -> dict[str, Any]:
        return self._request("GET", path, params=params, authed=authed)

    def _post(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", path, body=body)

    def _ensure_token(self) -> None:
        now_ms = int(time.time() * 1000)
        if self._access_token and now_ms < self._token_expire_at_ms - 60_000:
            return
        data = self._get("/v1.0/token", params={"grant_type": "1"}, authed=False)
        result = data["result"]
        self._access_token = result["access_token"]
        self._token_expire_at_ms = now_ms + int(result["expire_time"]) * 1000

    def get_device_status(self, device_id: str) -> list[dict[str, Any]]:
        self._ensure_token()
        data = self._get(f"/v1.0/devices/{device_id}/status")
        return data["result"]

    def get_device_report_logs(
        self, device_id: str, start_time_ms: int, end_time_ms: int, size: int = 100
    ) -> list[dict[str, Any]]:
        """Recent data-point report events (same data the "Device Log" tab
        in the Tuya console shows). Some devices only expose their less
        frequently updated sensors here rather than via /status."""
        self._ensure_token()
        params = {
            "start_time": start_time_ms,
            "end_time": end_time_ms,
            "size": size,
            # 1..7: device online/offline/dev-change/automation/scene/command/dp-report.
            # Ask for everything - we don't know in advance which type this
            # device's less-common sensors (pH, chlorine, ...) get logged under.
            "type": "1,2,3,4,5,6,7",
        }
        data = self._get(f"/v1.0/devices/{device_id}/logs", params=params)
        return data["result"].get("logs", [])

    def send_command(self, device_id: str, commands: list[dict[str, Any]]) -> None:
        """Send DP commands to a device, e.g. [{"code": "switch_1", "value": True}]."""
        self._ensure_token()
        self._post(f"/v1.0/devices/{device_id}/commands", body={"commands": commands})
