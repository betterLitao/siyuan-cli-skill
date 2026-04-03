from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from siyuan_config import config_summary, inspect_config, load_config


class SiyuanConfigTest(unittest.TestCase):
    def test_config_command_omits_doctor_without_flag(self) -> None:
        env = os.environ.copy()
        env.update(
            {
                "SIYUAN_BASE_URL": "http://example.com:6806",
                "SIYUAN_TOKEN": "token-value",
            }
        )

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "siyuan_cli.py"), "config"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertNotIn("doctor", payload["data"])

    def test_config_command_supports_doctor_mode(self) -> None:
        env = os.environ.copy()
        env.update(
            {
                "SIYUAN_BASE_URL": "http://example.com:6806",
                "SIYUAN_TOKEN": "token-value",
                "SIYUAN_ALLOWED_NOTEBOOKS": "Notes,Projects",
                "SIYUAN_DEFAULT_NOTEBOOK": "Projects",
                "SIYUAN_PURPOSE_NOTEBOOKS": "learn=Notes",
            }
        )

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "siyuan_cli.py"), "config", "--doctor"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("doctor", payload["data"])
        self.assertEqual(payload["data"]["doctor"]["scope_mode"], "restricted")
        self.assertEqual(payload["data"]["doctor"]["advisories"], [])

    def test_doctor_warns_when_windows_global_env_is_not_inherited(self) -> None:
        windows_env = {
            ("HKEY_CURRENT_USER\\Environment", "SIYUAN_BASE_URL"): "http://example.com:6806",
            ("HKEY_CURRENT_USER\\Environment", "SIYUAN_TOKEN"): "token-value",
        }

        with (
            patch("siyuan_config.os.name", "nt"),
            patch(
                "siyuan_config._get_windows_env_value",
                side_effect=lambda root, value_name: windows_env.get((root, value_name), ""),
            ),
        ):
            inspection = inspect_config({})

        doctor = inspection["doctor"]

        self.assertEqual(doctor["missing_required"], ["base_url", "token"])
        self.assertEqual(
            doctor["advisories"],
            [
                {
                    "code": "windows-env-not-inherited",
                    "level": "warning",
                    "field": "base_url",
                    "env_keys": ["SIYUAN_BASE_URL"],
                    "layers": ["user"],
                    "message": "Found SIYUAN_BASE_URL in the Windows user environment, but the current process did not inherit it. Restart the current shell or host app to pick up updated environment variables, or move the value into the config file.",
                },
                {
                    "code": "windows-env-not-inherited",
                    "level": "warning",
                    "field": "token",
                    "env_keys": ["SIYUAN_TOKEN"],
                    "layers": ["user"],
                    "message": "Found SIYUAN_TOKEN in the Windows user environment, but the current process did not inherit it. Restart the current shell or host app to pick up updated environment variables, or move the value into the config file.",
                },
            ],
        )

    def test_supports_generic_purpose_notebook_mapping(self) -> None:
        config = load_config(
            {
                "SIYUAN_BASE_URL": "http://example.com:6806",
                "SIYUAN_TOKEN": "token-value",
                "SIYUAN_ALLOWED_NOTEBOOKS": "Notes,Projects",
                "SIYUAN_DEFAULT_NOTEBOOK": "Projects",
                "SIYUAN_PURPOSE_NOTEBOOKS": "learn=Notes,reference=Projects",
            }
        )

        summary = config_summary(config)

        self.assertEqual(summary["default_notebook"], "Projects")
        self.assertEqual(
            summary["purpose_notebooks"],
            {
                "default": "Projects",
                "learn": "Notes",
                "reference": "Projects",
            },
        )
        self.assertNotIn("learn_notebooks", summary)

    def test_loads_config_file_when_env_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "siyuan-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "base_url": "http://config-file-host:6806",
                        "token": "config-file-token",
                        "allowed_notebooks": ["Notes", "Projects"],
                        "default_notebook": "Projects",
                        "purpose_notebooks": {"learn": "Notes"},
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(
                {
                    "SIYUAN_CONFIG_FILE": str(config_path),
                }
            )

        self.assertEqual(config.base_url, "http://config-file-host:6806")
        self.assertEqual(config.allowed_notebook_names, ["Notes", "Projects"])
        summary = config_summary(config)
        self.assertEqual(summary["default_notebook"], "Projects")
        self.assertEqual(summary["purpose_notebooks"]["learn"], "Notes")


if __name__ == "__main__":
    unittest.main()
