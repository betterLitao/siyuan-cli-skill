from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict

from siyuan_config import SiyuanConfig


class SiyuanError(RuntimeError):
    def __init__(self, message: str, *, action: str = "request", details: Any = None):
        super().__init__(message)
        self.action = action
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "action": self.action,
            "message": str(self),
            "details": self.details,
        }


@dataclass
class SiyuanClient:
    config: SiyuanConfig

    def post(self, endpoint: str, payload: Dict[str, Any], *, action: str) -> Dict[str, Any]:
        url = self.config.base_url + endpoint
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Token {self.config.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details: Any
            try:
                details = exc.read().decode("utf-8", errors="replace")
            except Exception:
                details = None
            raise SiyuanError(
                f"HTTP {exc.code} when calling {endpoint}",
                action=action,
                details=details,
            ) from exc
        except urllib.error.URLError as exc:
            raise SiyuanError(
                f"Network error when calling {endpoint}: {exc.reason}",
                action=action,
                details=str(exc.reason),
            ) from exc

        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise SiyuanError(
                f"Invalid JSON returned by {endpoint}",
                action=action,
                details=raw_body[:2000],
            ) from exc

        if not isinstance(body, dict):
            raise SiyuanError(
                f"Unexpected response shape from {endpoint}",
                action=action,
                details=body,
            )

        if body.get("code") != 0:
            raise SiyuanError(
                body.get("msg") or f"Siyuan API returned code={body.get('code')}",
                action=action,
                details=body,
            )

        return body
