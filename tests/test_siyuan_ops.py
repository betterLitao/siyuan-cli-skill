from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from siyuan_config import SiyuanConfig
from siyuan_ops import append_doc, choose_default_notebook, replace_doc_section, verify_write


class SiyuanOpsTest(unittest.TestCase):
    def test_choose_default_notebook_uses_generic_purpose_mapping(self) -> None:
        config = SiyuanConfig(
            base_url="http://example.com:6806",
            token="token-value",
            timeout=30,
            allowed_notebook_names=["Notes", "Projects"],
            default_notebook_name="Projects",
            purpose_notebook_names={"default": "Projects", "reference": "Notes"},
            config_file_path=None,
        )

        notebook = choose_default_notebook(config, purpose="reference")

        self.assertEqual(notebook, "Notes")

    def test_append_preserves_frontmatter_and_title(self) -> None:
        current = {
            "id": "doc-1",
            "content": "---\ntitle: Demo\n---\n\n# Demo\n\nBody\n",
            "editable_content": "Body\n",
            "title": "Demo",
            "hPath": "/Demo",
        }
        captured: dict[str, str] = {}

        def fake_update_doc(client, *, doc_id: str, markdown: str):
            captured["doc_id"] = doc_id
            captured["markdown"] = markdown
            return {
                "id": doc_id,
                "before": current,
                "after": {"content": markdown, "editable_content": markdown},
                "verified": True,
                "mismatch_reason": None,
            }

        with (
            patch("siyuan_ops.read_doc", return_value=current),
            patch("siyuan_ops.update_doc", side_effect=fake_update_doc),
        ):
            append_doc(object(), doc_id="doc-1", markdown="## Added\n\nMore")

        self.assertEqual(captured["doc_id"], "doc-1")
        self.assertTrue(captured["markdown"].startswith("---\ntitle: Demo\n---\n\n# Demo\n\n"))
        self.assertIn("\nBody\n\n## Added\n\nMore\n", captured["markdown"])

    def test_verify_write_rejects_substring_only_match(self) -> None:
        verified, mismatch_reason = verify_write(expected="needle", actual="prefix needle suffix")

        self.assertFalse(verified)
        self.assertIsNotNone(mismatch_reason)

    def test_replace_section_falls_back_to_document_update_when_block_match_fails(self) -> None:
        current = {
            "id": "doc-1",
            "content": "# Demo\n\n## Heading `code`\n\nOld body\n",
            "editable_content": "## Heading `code`\n\nOld body\n",
            "title": "Demo",
            "hPath": "/Demo",
        }
        captured: dict[str, str] = {}

        def fake_update_doc(client, *, doc_id: str, markdown: str):
            captured["doc_id"] = doc_id
            captured["markdown"] = markdown
            return {
                "id": doc_id,
                "before": current,
                "after": {
                    "content": markdown,
                    "editable_content": markdown,
                    "title": "Demo",
                    "hPath": "/Demo",
                },
                "verified": True,
                "mismatch_reason": None,
            }

        with (
            patch("siyuan_ops.read_doc", return_value=current),
            patch("siyuan_ops.get_child_blocks", return_value=[]),
            patch("siyuan_ops.update_doc", side_effect=fake_update_doc),
        ):
            result = replace_doc_section(
                object(),
                doc_id="doc-1",
                heading="Heading `code`",
                markdown="New body",
            )

        self.assertEqual(result["mode"], "document")
        self.assertEqual(captured["doc_id"], "doc-1")
        self.assertIn("## Heading `code`\n\nNew body\n", captured["markdown"])


if __name__ == "__main__":
    unittest.main()
