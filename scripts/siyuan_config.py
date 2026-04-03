from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_SERVER_BASE_URL = "http://127.0.0.1:3000"
DEFAULT_TIMEOUT = 30

BASE_URL_ENV_KEYS = ["SIYUAN_BASE_URL", "SIYUAN_URL", "SIYUAN_REMOTE_URL"]
TOKEN_ENV_KEYS = ["SIYUAN_TOKEN"]
TIMEOUT_ENV_KEYS = ["SIYUAN_TIMEOUT"]
ALLOWED_NOTEBOOKS_ENV_KEYS = ["SIYUAN_ALLOWED_NOTEBOOKS"]
DEFAULT_NOTEBOOK_ENV_KEYS = ["SIYUAN_DEFAULT_NOTEBOOK"]
PURPOSE_NOTEBOOKS_ENV_KEYS = ["SIYUAN_PURPOSE_NOTEBOOKS"]
LEGACY_LEARN_NOTEBOOKS_ENV_KEYS = ["SIYUAN_LEARN_NOTEBOOKS"]
CONFIG_FILE_ENV_KEYS = ["SIYUAN_CONFIG_FILE"]


@dataclass(frozen=True)
class SiyuanConfig:
    base_url: str
    token: str
    timeout: int
    allowed_notebook_names: List[str]
    default_notebook_name: str
    purpose_notebook_names: Dict[str, str]
    config_file_path: Optional[str]


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_purpose_name(value: str) -> str:
    return value.strip().lower()


def _first_non_empty(source: Dict[str, str], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value and value.strip():
            return value.strip()
    return ""


def _first_present(source: Dict[str, str], *keys: str) -> tuple[str, str]:
    for key in keys:
        value = source.get(key)
        if value and value.strip():
            return value.strip(), f"env:{key}"
    return "", ""


def _default_config_file_path() -> Path:
    if os.name == "nt":
        return Path.home() / ".siyuan-cli-skill.json"
    return Path.home() / ".config" / "siyuan-cli-skill" / "config.json"


def _resolve_config_file_path(source: Dict[str, str]) -> tuple[Path, str]:
    explicit_path, explicit_source = _first_present(source, *CONFIG_FILE_ENV_KEYS)
    if explicit_path:
        return Path(explicit_path).expanduser(), explicit_source
    return _default_config_file_path(), "default"


def _read_config_file(path: Path) -> tuple[Dict[str, Any], Optional[str]]:
    if not path.exists():
        return {}, None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, str(exc)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, f"Invalid JSON: {exc}"
    if not isinstance(data, dict):
        return {}, "Top-level config file content must be a JSON object."
    return data, None


def _coerce_csv_or_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return _split_csv(value)
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
        return result
    return []


def _parse_purpose_notebooks(value: Any) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if isinstance(value, dict):
        for key, notebook in value.items():
            if not isinstance(key, str) or not isinstance(notebook, str):
                continue
            purpose = _normalize_purpose_name(key)
            if purpose and notebook.strip():
                result[purpose] = notebook.strip()
        return result
    if isinstance(value, str):
        for item in _split_csv(value):
            if "=" not in item:
                continue
            purpose, notebook = item.split("=", 1)
            normalized_purpose = _normalize_purpose_name(purpose)
            normalized_notebook = notebook.strip()
            if normalized_purpose and normalized_notebook:
                result[normalized_purpose] = normalized_notebook
    return result


def _resolve_config_values(env: Dict[str, str] | None = None) -> Dict[str, Any]:
    source = env or os.environ
    config_path, config_path_source = _resolve_config_file_path(source)
    file_data, file_error = _read_config_file(config_path)

    base_url, base_url_source = _first_present(source, *BASE_URL_ENV_KEYS)
    if not base_url:
        file_base_url = file_data.get("base_url") or file_data.get("url") or file_data.get("remote_url") or ""
        if isinstance(file_base_url, str) and file_base_url.strip():
            base_url = file_base_url.strip()
            base_url_source = f"config:{config_path}#base_url"

    token, token_source = _first_present(source, *TOKEN_ENV_KEYS)
    if not token:
        file_token = file_data.get("token") or ""
        if isinstance(file_token, str) and file_token.strip():
            token = file_token.strip()
            token_source = f"config:{config_path}#token"

    timeout_raw, timeout_source = _first_present(source, *TIMEOUT_ENV_KEYS)
    if not timeout_raw:
        timeout_value = file_data.get("timeout")
        if isinstance(timeout_value, int):
            timeout_raw = str(timeout_value)
            timeout_source = f"config:{config_path}#timeout"
        elif isinstance(timeout_value, str) and timeout_value.strip():
            timeout_raw = timeout_value.strip()
            timeout_source = f"config:{config_path}#timeout"
    if not timeout_raw:
        timeout_raw = str(DEFAULT_TIMEOUT)
        timeout_source = "default"
    try:
        timeout = max(1, int(timeout_raw))
    except ValueError:
        timeout = DEFAULT_TIMEOUT
        timeout_source = f"{timeout_source} (invalid -> default)" if timeout_source else "default"

    allowed_raw, allowed_source = _first_present(source, *ALLOWED_NOTEBOOKS_ENV_KEYS)
    if allowed_raw:
        allowed_notebooks = _coerce_csv_or_list(allowed_raw)
    else:
        allowed_notebooks = _coerce_csv_or_list(file_data.get("allowed_notebooks"))
        if allowed_notebooks:
            allowed_source = f"config:{config_path}#allowed_notebooks"

    default_notebook, default_notebook_source = _first_present(source, *DEFAULT_NOTEBOOK_ENV_KEYS)
    if not default_notebook:
        file_default_notebook = file_data.get("default_notebook")
        if isinstance(file_default_notebook, str) and file_default_notebook.strip():
            default_notebook = file_default_notebook.strip()
            default_notebook_source = f"config:{config_path}#default_notebook"

    purpose_notebooks = _parse_purpose_notebooks(file_data.get("purpose_notebooks"))
    purpose_notebooks_source = f"config:{config_path}#purpose_notebooks" if purpose_notebooks else ""

    env_purpose_raw, env_purpose_source = _first_present(source, *PURPOSE_NOTEBOOKS_ENV_KEYS)
    env_purpose_notebooks = _parse_purpose_notebooks(env_purpose_raw)
    if env_purpose_notebooks:
        purpose_notebooks.update(env_purpose_notebooks)
        purpose_notebooks_source = env_purpose_source

    if default_notebook:
        purpose_notebooks["default"] = default_notebook
        if not purpose_notebooks_source:
            purpose_notebooks_source = default_notebook_source

    legacy_learn_raw, legacy_learn_source = _first_present(source, *LEGACY_LEARN_NOTEBOOKS_ENV_KEYS)
    legacy_learn = _coerce_csv_or_list(legacy_learn_raw)
    if (not legacy_learn) and ("learn_notebooks" in file_data):
        legacy_learn = _coerce_csv_or_list(file_data.get("learn_notebooks"))
        if legacy_learn:
            legacy_learn_source = f"config:{config_path}#learn_notebooks (deprecated)"
    if legacy_learn and "learn" not in purpose_notebooks:
        purpose_notebooks["learn"] = legacy_learn[0]
        if not purpose_notebooks_source:
            purpose_notebooks_source = legacy_learn_source or "deprecated"

    if not default_notebook and purpose_notebooks.get("default"):
        default_notebook = purpose_notebooks["default"]
        if not default_notebook_source:
            default_notebook_source = purpose_notebooks_source

    if (not default_notebook) and allowed_notebooks:
        default_notebook = allowed_notebooks[0]
        default_notebook_source = "derived:first-allowed-notebook"

    return {
        "base_url": base_url.rstrip("/") if base_url else "",
        "token": token,
        "timeout": timeout,
        "allowed_notebooks": allowed_notebooks,
        "default_notebook": default_notebook,
        "purpose_notebooks": purpose_notebooks,
        "scope_mode": "restricted" if allowed_notebooks else "unrestricted",
        "config_file_path": str(config_path),
        "config_file_exists": config_path.exists(),
        "config_file_error": file_error,
        "sources": {
            "config_file": config_path_source,
            "base_url": base_url_source,
            "token": token_source,
            "timeout": timeout_source,
            "allowed_notebooks": allowed_source,
            "default_notebook": default_notebook_source,
            "purpose_notebooks": purpose_notebooks_source,
            "legacy_learn_notebooks": legacy_learn_source,
        },
        "missing_required": [
            key
            for key, value in (
                ("base_url", base_url),
                ("token", token),
            )
            if not value
        ],
    }


def _get_windows_env_value(root: str, value_name: str) -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg
    except ImportError:
        return ""
    hive_name, sub_key = root.split("\\", 1)
    hive = getattr(winreg, hive_name, None)
    if hive is None:
        return ""
    try:
        with winreg.OpenKey(hive, sub_key) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
    except OSError:
        return ""
    return str(value).strip()


def _mask_value(name: str, value: str) -> Optional[str]:
    if not value:
        return None
    if "TOKEN" in name or "KEY" in name or "SECRET" in name:
        return "<set>"
    return value


def inspect_config(env: Dict[str, str] | None = None) -> Dict[str, Any]:
    resolved = _resolve_config_values(env)
    env_source = env or os.environ

    env_layers: Dict[str, Dict[str, Optional[str]]] = {
        "process": {
            name: _mask_value(name, str(env_source.get(name, "")).strip())
            for name in [
                *BASE_URL_ENV_KEYS,
                *TOKEN_ENV_KEYS,
                *ALLOWED_NOTEBOOKS_ENV_KEYS,
                *DEFAULT_NOTEBOOK_ENV_KEYS,
                *PURPOSE_NOTEBOOKS_ENV_KEYS,
                *LEGACY_LEARN_NOTEBOOKS_ENV_KEYS,
                *CONFIG_FILE_ENV_KEYS,
            ]
        }
    }

    if os.name == "nt":
        env_layers["user"] = {
            name: _mask_value(name, _get_windows_env_value("HKEY_CURRENT_USER\\Environment", name))
            for name in env_layers["process"]
        }
        env_layers["machine"] = {
            name: _mask_value(
                name,
                _get_windows_env_value(
                    "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment",
                    name,
                ),
            )
            for name in env_layers["process"]
        }

    doctor = {
        "scope_mode": resolved["scope_mode"],
        "allowed_notebooks": resolved["allowed_notebooks"],
        "default_notebook": resolved["default_notebook"] or None,
        "purpose_notebooks": resolved["purpose_notebooks"],
        "config_file": {
            "path": resolved["config_file_path"],
            "exists": resolved["config_file_exists"],
            "error": resolved["config_file_error"],
        },
        "sources": resolved["sources"],
        "environment_layers": env_layers,
        "missing_required": resolved["missing_required"],
        "deprecated": {
            "legacy_learn_notebooks_env": bool(resolved["sources"]["legacy_learn_notebooks"]),
        },
    }

    config: Optional[SiyuanConfig] = None
    if not resolved["missing_required"]:
        config = SiyuanConfig(
            base_url=resolved["base_url"],
            token=resolved["token"],
            timeout=resolved["timeout"],
            allowed_notebook_names=list(resolved["allowed_notebooks"]),
            default_notebook_name=resolved["default_notebook"],
            purpose_notebook_names=dict(resolved["purpose_notebooks"]),
            config_file_path=resolved["config_file_path"],
        )

    return {
        "config": config,
        "doctor": doctor,
    }


def load_config(env: Dict[str, str] | None = None) -> SiyuanConfig:
    inspection = inspect_config(env)
    config = inspection["config"]
    if config is not None:
        return config

    missing_required = inspection["doctor"]["missing_required"]
    if "base_url" in missing_required:
        raise ValueError(f"Missing Siyuan base URL. Set one of: {', '.join(BASE_URL_ENV_KEYS)}")
    raise ValueError(f"Missing Siyuan token. Set one of: {', '.join(TOKEN_ENV_KEYS)}")


def config_summary(config: SiyuanConfig, doctor: Optional[Dict[str, Any]] = None) -> Dict[str, object]:
    summary: Dict[str, object] = {
        "base_url": config.base_url,
        "timeout": config.timeout,
        "allowed_notebooks": config.allowed_notebook_names,
        "scope_mode": "restricted" if config.allowed_notebook_names else "unrestricted",
        "default_notebook": config.default_notebook_name or None,
        "purpose_notebooks": config.purpose_notebook_names,
        "has_token": bool(config.token),
        "config_file_path": config.config_file_path,
        "server_base_url_hint": DEFAULT_SERVER_BASE_URL,
        "required_env": {
            "base_url": BASE_URL_ENV_KEYS,
            "token": TOKEN_ENV_KEYS,
        },
        "optional_env": {
            "timeout": TIMEOUT_ENV_KEYS,
            "allowed_notebooks": ALLOWED_NOTEBOOKS_ENV_KEYS,
            "default_notebook": DEFAULT_NOTEBOOK_ENV_KEYS,
            "purpose_notebooks": PURPOSE_NOTEBOOKS_ENV_KEYS,
            "config_file": CONFIG_FILE_ENV_KEYS,
        },
        "deprecated_env": {
            "learn_notebooks": LEGACY_LEARN_NOTEBOOKS_ENV_KEYS,
        },
    }
    if doctor is not None:
        summary["doctor"] = doctor
    return summary
