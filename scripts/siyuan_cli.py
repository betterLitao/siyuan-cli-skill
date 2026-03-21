from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

from siyuan_client import SiyuanClient, SiyuanError
from siyuan_config import config_summary, load_config
from siyuan_ops import (
    append_doc,
    choose_default_notebook,
    create_doc,
    delete_doc,
    ensure_allowed_notebook,
    ensure_doc_meta_in_allowed_scope,
    load_markdown_text,
    read_doc,
    replace_doc_section,
    resolve_doc,
    search_docs,
    update_doc,
)


def configure_windows_stdio() -> None:
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Siyuan CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("config", help="Show effective connection and scope config")
    config_parser.set_defaults(handler=handle_config)

    read_parser = subparsers.add_parser("read", help="Read a document as Markdown")
    add_doc_selector_args(read_parser, require_target=True)
    read_parser.set_defaults(handler=handle_read)

    search_parser = subparsers.add_parser("search", help="Search documents in allowed notebooks")
    search_parser.add_argument("--query", required=True, help="Search keyword")
    search_parser.add_argument("--notebook", default="", help="Restrict search to one allowed notebook")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results, default 10")
    search_parser.set_defaults(handler=handle_search)

    update_parser = subparsers.add_parser("update", help="Replace an entire document with Markdown")
    add_doc_selector_args(update_parser, require_target=True)
    add_markdown_args(update_parser)
    update_parser.set_defaults(handler=handle_update)

    append_parser = subparsers.add_parser("append", help="Append Markdown to the end of a document")
    add_doc_selector_args(append_parser, require_target=True)
    add_markdown_args(append_parser)
    append_parser.set_defaults(handler=handle_append)

    replace_section_parser = subparsers.add_parser("replace-section", help="Replace one section under a heading")
    add_doc_selector_args(replace_section_parser, require_target=True)
    add_section_args(replace_section_parser)
    add_markdown_args(replace_section_parser)
    replace_section_parser.set_defaults(handler=handle_replace_section)

    upsert_section_parser = subparsers.add_parser("upsert-section", help="Replace a section or create it if missing")
    add_doc_selector_args(upsert_section_parser, require_target=True)
    add_section_args(upsert_section_parser)
    add_markdown_args(upsert_section_parser)
    upsert_section_parser.set_defaults(handler=handle_upsert_section)

    create_parser = subparsers.add_parser("create-doc", help="Create a new document")
    create_parser.add_argument("--notebook", default="", help="Target notebook name. Defaults to learn or 服务器运维 depending on intent")
    create_parser.add_argument("--path", required=True, help="Target doc path, e.g. /工具 / 工作流/思源包装器")
    add_markdown_args(create_parser)
    create_parser.add_argument("--if-exists", choices=["error", "skip", "replace"], default="error", help="Conflict strategy when the target path already exists")
    create_parser.add_argument("--purpose", choices=["default", "learn"], default="default", help="Choose default notebook purpose")
    create_parser.set_defaults(handler=handle_create_doc)

    delete_parser = subparsers.add_parser("delete-doc", help="Delete a document by doc-id or path")
    add_doc_selector_args(delete_parser, require_target=True)
    delete_parser.add_argument("--yes", action="store_true", default=False, help="Required safety flag to confirm deletion")
    delete_parser.set_defaults(handler=handle_delete_doc)

    return parser


def add_doc_selector_args(parser: argparse.ArgumentParser, *, require_target: bool) -> None:
    parser.add_argument("--doc-id", default="", help="Document ID")
    parser.add_argument("--path", default="", help="Document path inside notebook")
    parser.add_argument("--notebook", default="", help="Notebook name when using --path")
    parser.add_argument("--require-allowed-notebook", action="store_true", default=False, help="Fail if --notebook is outside default scope")
    parser.set_defaults(require_target=require_target)


def add_markdown_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text", default="", help="Short Markdown content")
    parser.add_argument("--input-file", default="", help="UTF-8 file path for long Markdown content")


def add_section_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--heading", required=True, help="Heading text or full Markdown heading, e.g. '注意事项' or '## 注意事项'")
    parser.add_argument("--level", type=int, default=None, help="Heading level when --heading is plain text. Defaults to 2")


def handle_config(args: argparse.Namespace) -> Dict[str, Any]:
    config = load_config()
    return {
        "ok": True,
        "action": "config",
        "message": "Loaded Siyuan configuration.",
        "data": config_summary(config),
        "error": None,
    }


def handle_read(args: argparse.Namespace) -> Dict[str, Any]:
    client, config = create_client_and_config()
    doc = resolve_doc(
        client,
        doc_id=args.doc_id or None,
        doc_path=args.path or None,
        notebook_name=checked_notebook_arg(config, args.notebook, args.require_allowed_notebook),
    )
    doc = ensure_doc_meta_in_allowed_scope(client, config, doc)
    payload = read_doc(client, doc["id"])
    payload.update({
        "resolved_from": {
            "doc_id": args.doc_id or None,
            "path": args.path or None,
            "notebook": args.notebook or None,
        },
        "meta": doc,
    })
    return success("read", "Read document successfully.", payload)


def handle_search(args: argparse.Namespace) -> Dict[str, Any]:
    client, config = create_client_and_config()
    notebook = checked_notebook_arg(config, args.notebook, bool(args.notebook))
    rows = search_docs(client, config, query=args.query, notebook_name=notebook, limit=args.limit)
    return success(
        "search",
        f"Found {len(rows)} candidate document(s).",
        {
            "query": args.query,
            "notebook": notebook,
            "count": len(rows),
            "items": rows,
        },
    )


def handle_update(args: argparse.Namespace) -> Dict[str, Any]:
    client, config = create_client_and_config()
    doc = resolve_doc(
        client,
        doc_id=args.doc_id or None,
        doc_path=args.path or None,
        notebook_name=checked_notebook_arg(config, args.notebook, args.require_allowed_notebook),
    )
    doc = ensure_doc_meta_in_allowed_scope(client, config, doc)
    markdown = load_markdown_text(args.text or None, args.input_file or None)
    result = update_doc(client, doc_id=doc["id"], markdown=markdown)
    message = "Updated document and verified read-back."
    if not result.get("verified"):
        message = "Updated document, but read-back verification reported a mismatch."
    result["meta"] = doc
    return success("update", message, result)


def handle_append(args: argparse.Namespace) -> Dict[str, Any]:
    client, config = create_client_and_config()
    doc = resolve_doc(
        client,
        doc_id=args.doc_id or None,
        doc_path=args.path or None,
        notebook_name=checked_notebook_arg(config, args.notebook, args.require_allowed_notebook),
    )
    doc = ensure_doc_meta_in_allowed_scope(client, config, doc)
    markdown = load_markdown_text(args.text or None, args.input_file or None)
    result = append_doc(client, doc_id=doc["id"], markdown=markdown)
    message = "Appended document and verified read-back."
    if not result.get("verified"):
        message = "Appended document, but read-back verification reported a mismatch."
    result["meta"] = doc
    return success("append", message, result)


def handle_replace_section(args: argparse.Namespace) -> Dict[str, Any]:
    client, config = create_client_and_config()
    doc = resolve_doc(
        client,
        doc_id=args.doc_id or None,
        doc_path=args.path or None,
        notebook_name=checked_notebook_arg(config, args.notebook, args.require_allowed_notebook),
    )
    doc = ensure_doc_meta_in_allowed_scope(client, config, doc)
    markdown = load_markdown_text(args.text or None, args.input_file or None)
    result = replace_doc_section(
        client,
        doc_id=doc["id"],
        heading=args.heading,
        markdown=markdown,
        level=args.level,
        create_if_missing=False,
    )
    message = "Replaced section and verified read-back."
    if not result.get("verified"):
        message = "Replaced section, but read-back verification reported a mismatch."
    result["meta"] = doc
    return success("replace-section", message, result)


def handle_upsert_section(args: argparse.Namespace) -> Dict[str, Any]:
    client, config = create_client_and_config()
    doc = resolve_doc(
        client,
        doc_id=args.doc_id or None,
        doc_path=args.path or None,
        notebook_name=checked_notebook_arg(config, args.notebook, args.require_allowed_notebook),
    )
    doc = ensure_doc_meta_in_allowed_scope(client, config, doc)
    markdown = load_markdown_text(args.text or None, args.input_file or None)
    result = replace_doc_section(
        client,
        doc_id=doc["id"],
        heading=args.heading,
        markdown=markdown,
        level=args.level,
        create_if_missing=True,
    )
    message = "Upserted section and verified read-back."
    if not result.get("verified"):
        message = "Upserted section, but read-back verification reported a mismatch."
    result["meta"] = doc
    return success("upsert-section", message, result)


def handle_create_doc(args: argparse.Namespace) -> Dict[str, Any]:
    client, config = create_client_and_config()
    notebook = args.notebook or choose_default_notebook(config, purpose=args.purpose)
    notebook = ensure_allowed_notebook(config, notebook)
    markdown = load_markdown_text(args.text or None, args.input_file or None)
    result = create_doc(
        client,
        config,
        notebook_name=notebook,
        path=args.path,
        markdown=markdown,
        if_exists=args.if_exists,
    )
    message = "Created document and verified read-back."
    if not result.get("created") and result.get("skipped"):
        message = "Document already existed, skipped creation and returned the current content."
    elif not result.get("created") and args.if_exists == "replace":
        message = "Document already existed, replaced it and verified read-back."
    if not result.get("verified"):
        if not result.get("created") and args.if_exists == "replace":
            message = "Document already existed, replaced it, but read-back verification reported a mismatch."
        else:
            message = "Created document, but read-back verification reported a mismatch."
    return success("create-doc", message, result)


def handle_delete_doc(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.yes:
        raise SiyuanError("delete-doc requires --yes to confirm deletion.", action="delete-doc")
    client, config = create_client_and_config()
    doc = resolve_doc(
        client,
        doc_id=args.doc_id or None,
        doc_path=args.path or None,
        notebook_name=checked_notebook_arg(config, args.notebook, args.require_allowed_notebook),
    )
    doc = ensure_doc_meta_in_allowed_scope(client, config, doc)
    result = delete_doc(client, doc_meta=doc)
    message = "Deleted document and verified removal."
    if not result.get("verified"):
        message = "Deleted document, but post-delete verification reported that it may still exist."
    result["meta"] = doc
    return success("delete-doc", message, result)


def checked_notebook_arg(config, notebook: str, enforce_allowed: bool) -> Optional[str]:
    if not notebook:
        return None
    return ensure_allowed_notebook(config, notebook)


def create_client_and_config():
    config = load_config()
    return SiyuanClient(config), config


def success(action: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "action": action,
        "message": message,
        "data": data,
        "error": None,
    }


def failure(action: str, exc: SiyuanError) -> Dict[str, Any]:
    return {
        "ok": False,
        "action": action,
        "message": str(exc),
        "data": None,
        "error": exc.to_dict(),
    }


def main() -> int:
    configure_windows_stdio()
    parser = build_parser()
    args = parser.parse_args()
    action = args.command
    try:
        result = args.handler(args)
    except SiyuanError as exc:
        result = failure(action, exc)
        print_json(result)
        return 1
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        result = {
            "ok": False,
            "action": action,
            "message": str(exc),
            "data": None,
            "error": {
                "type": exc.__class__.__name__,
                "action": action,
                "message": str(exc),
                "details": None,
            },
        }
        print_json(result)
        return 1

    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
