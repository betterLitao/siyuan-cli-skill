from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List

DEFAULT_SERVER_BASE_URL = "http://127.0.0.1:3000"
DEFAULT_ALLOWED_NOTEBOOK_NAMES = ("服务器运维", "learn")
DEFAULT_LEARN_NOTEBOOK_NAMES = ("learn",)
DEFAULT_TIMEOUT = 30


@dataclass(frozen=True)
class SiyuanConfig:
    base_url: str
    token: str
    timeout: int
    allowed_notebook_names: List[str]
    learn_notebook_names: List[str]


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _first_non_empty(source: Dict[str, str], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value and value.strip():
            return value.strip()
    return ""


def _require_env_value(source: Dict[str, str], *, keys: List[str], label: str) -> str:
    value = _first_non_empty(source, *keys)
    if value:
        return value
    raise ValueError(
        f"Missing Siyuan {label}. Set one of: {', '.join(keys)}"
    )


def load_config(env: Dict[str, str] | None = None) -> SiyuanConfig:
    source = env or os.environ

    base_url = _require_env_value(
        source,
        keys=["SIYUAN_BASE_URL", "SIYUAN_URL", "SIYUAN_REMOTE_URL"],
        label="base URL",
    ).rstrip("/")

    token = _require_env_value(
        source,
        keys=["SIYUAN_TOKEN"],
        label="token",
    )

    timeout_raw = source.get("SIYUAN_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        timeout = max(1, int(timeout_raw))
    except ValueError:
        timeout = DEFAULT_TIMEOUT

    allowed_raw = source.get("SIYUAN_ALLOWED_NOTEBOOKS", ",".join(DEFAULT_ALLOWED_NOTEBOOK_NAMES))
    allowed_notebook_names = _split_csv(allowed_raw) or list(DEFAULT_ALLOWED_NOTEBOOK_NAMES)

    learn_raw = source.get("SIYUAN_LEARN_NOTEBOOKS", ",".join(DEFAULT_LEARN_NOTEBOOK_NAMES))
    learn_notebook_names = _split_csv(learn_raw) or list(DEFAULT_LEARN_NOTEBOOK_NAMES)

    return SiyuanConfig(
        base_url=base_url,
        token=token,
        timeout=timeout,
        allowed_notebook_names=allowed_notebook_names,
        learn_notebook_names=learn_notebook_names,
    )


def config_summary(config: SiyuanConfig) -> Dict[str, object]:
    return {
        "base_url": config.base_url,
        "timeout": config.timeout,
        "allowed_notebooks": config.allowed_notebook_names,
        "learn_notebooks": config.learn_notebook_names,
        "has_token": bool(config.token),
        "server_base_url_hint": DEFAULT_SERVER_BASE_URL,
        "required_env": {
            "base_url": ["SIYUAN_BASE_URL", "SIYUAN_URL", "SIYUAN_REMOTE_URL"],
            "token": ["SIYUAN_TOKEN"],
        },
    }
