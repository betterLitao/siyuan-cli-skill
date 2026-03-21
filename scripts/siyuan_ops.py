from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from siyuan_client import SiyuanClient, SiyuanError
from siyuan_config import SiyuanConfig

CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
DOC_SQL_COLUMNS = "id, box, path, hpath, content, root_id"
HEADING_LINE_PATTERN = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
HEADING_SUBTYPE_PATTERN = re.compile(r"^h([1-6])$")


def normalize_markdown(content: str) -> str:
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = CONTROL_CHAR_PATTERN.sub("", content)
    return content


def strip_frontmatter(content: str) -> str:
    normalized = normalize_markdown(content)
    if not normalized.startswith("---\n"):
        return normalized
    return re.sub(r"^---\n.*?\n---\n*", "", normalized, count=1, flags=re.DOTALL)


def extract_title_line(content: str) -> Optional[str]:
    normalized = strip_frontmatter(content).lstrip("\n")
    first_line = normalized.split("\n", 1)[0].strip()
    match = HEADING_LINE_PATTERN.match(first_line)
    if not match or len(match.group(1)) != 1:
        return None
    return match.group(2).strip()


def extract_editable_markdown(content: str) -> str:
    without_frontmatter = strip_frontmatter(content)
    without_title = re.sub(r"^# .*\n+", "", without_frontmatter, count=1)
    return without_title.lstrip("\n")


def load_markdown_text(input_text: Optional[str] = None, input_file: Optional[str] = None) -> str:
    if input_file:
        try:
            return normalize_markdown(Path(input_file).read_text(encoding="utf-8"))
        except OSError as exc:
            raise SiyuanError(
                f"Failed to read input file: {input_file}",
                action="load-content",
                details=str(exc),
            ) from exc
        except UnicodeError as exc:
            raise SiyuanError(
                f"Input file is not valid UTF-8: {input_file}",
                action="load-content",
                details=str(exc),
            ) from exc
    if input_text is None:
        raise SiyuanError("Missing content. Provide --text or --input-file.", action="load-content")
    return normalize_markdown(input_text)


def ensure_not_empty(value: str, *, field_name: str, action: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise SiyuanError(f"{field_name} cannot be empty.", action=action)
    return stripped


def list_notebooks(client: SiyuanClient) -> List[Dict[str, Any]]:
    response = client.post("/api/notebook/lsNotebooks", {}, action="list-notebooks")
    data = response.get("data") or {}
    notebooks = data.get("notebooks") or []
    if not isinstance(notebooks, list):
        raise SiyuanError("Invalid notebook list response.", action="list-notebooks", details=response)
    return notebooks


def find_notebook_by_name(client: SiyuanClient, notebook_name: str) -> Dict[str, Any]:
    target_name = ensure_not_empty(notebook_name, field_name="notebook name", action="resolve-notebook")
    notebooks = list_notebooks(client)
    for notebook in notebooks:
        if notebook.get("name") == target_name:
            return notebook
    raise SiyuanError(
        f"Notebook not found: {target_name}",
        action="resolve-notebook",
        details={"requested": target_name, "available": [item.get('name') for item in notebooks]},
    )


def ensure_allowed_notebook(config: SiyuanConfig, notebook_name: str) -> str:
    target_name = ensure_not_empty(notebook_name, field_name="notebook name", action="scope-check")
    if not config.allowed_notebook_names:
        return target_name
    if target_name not in config.allowed_notebook_names:
        raise SiyuanError(
            f"Notebook '{target_name}' is outside the configured allowed scope.",
            action="scope-check",
            details={
                "requested": target_name,
                "allowed": config.allowed_notebook_names,
            },
        )
    return target_name


def choose_default_notebook(config: SiyuanConfig, *, purpose: str) -> str:
    if purpose == "learn" and config.learn_notebook_names:
        return config.learn_notebook_names[0]
    if config.allowed_notebook_names:
        return config.allowed_notebook_names[0]
    raise SiyuanError(
        "No default notebook configured. Pass --notebook explicitly or set SIYUAN_ALLOWED_NOTEBOOKS / SIYUAN_LEARN_NOTEBOOKS.",
        action="scope-check",
        details={
            "purpose": purpose,
            "allowed_notebooks": config.allowed_notebook_names,
            "learn_notebooks": config.learn_notebook_names,
        },
    )


def get_allowed_notebook_ids(client: SiyuanClient, config: SiyuanConfig) -> Dict[str, str]:
    notebooks = list_notebooks(client)
    result: Dict[str, str] = {}
    for notebook in notebooks:
        name = notebook.get("name")
        notebook_id = notebook.get("id")
        if not notebook_id:
            continue
        if not config.allowed_notebook_names or name in config.allowed_notebook_names:
            result[str(notebook_id)] = str(name)
    return result


def ensure_doc_meta_in_allowed_scope(client: SiyuanClient, config: SiyuanConfig, doc_meta: Dict[str, Any]) -> Dict[str, Any]:
    if not config.allowed_notebook_names:
        return doc_meta
    allowed_ids = get_allowed_notebook_ids(client, config)
    box = str(doc_meta.get("box") or "")
    if box not in allowed_ids:
        raise SiyuanError(
            "Document is outside the configured allowed scope.",
            action="scope-check",
            details={
                "doc_id": doc_meta.get("id"),
                "box": doc_meta.get("box"),
                "allowed_notebooks": config.allowed_notebook_names,
            },
        )
    return doc_meta


def resolve_doc(client: SiyuanClient, *, doc_id: Optional[str] = None, doc_path: Optional[str] = None, notebook_name: Optional[str] = None) -> Dict[str, Any]:
    if doc_id:
        return get_doc_meta_by_id(client, doc_id)

    if not doc_path:
        raise SiyuanError("Provide --doc-id or --path.", action="resolve-doc")

    if not notebook_name:
        raise SiyuanError("--path requires --notebook.", action="resolve-doc")

    notebook = find_notebook_by_name(client, notebook_name)
    return get_doc_meta_by_path(client, notebook_id=notebook["id"], notebook_name=notebook_name, doc_path=doc_path)


def list_docs_by_path(client: SiyuanClient, *, notebook_id: str, path: str) -> List[Dict[str, Any]]:
    response = client.post(
        "/api/filetree/listDocsByPath",
        {"notebook": notebook_id, "path": path},
        action="list-docs-by-path",
    )
    data = response.get("data") or {}
    files = data.get("files") or []
    if not isinstance(files, list):
        raise SiyuanError("Invalid listDocsByPath response.", action="list-docs-by-path", details=response)
    results: List[Dict[str, Any]] = []
    for item in files:
        path_value = item.get("path") or ""
        item_id = item.get("id")
        if not item_id:
            continue
        results.append(
            {
                "id": item_id,
                "root_id": item_id,
                "box": notebook_id,
                "path": path_value,
                "hpath": item.get("name", "").removesuffix('.sy'),
                "content": item.get("name", "").removesuffix('.sy'),
                "name": item.get("name"),
                "subFileCount": item.get("subFileCount"),
            }
        )
    return results


def get_doc_path_by_id(client: SiyuanClient, doc_id: str) -> Dict[str, str]:
    safe_id = ensure_not_empty(doc_id, field_name="doc id", action="get-doc-path")
    response = client.post("/api/filetree/getPathByID", {"id": safe_id}, action="get-doc-path")
    data = response.get("data") or {}
    notebook_id = str(data.get("notebook") or "")
    path = str(data.get("path") or "")
    if not notebook_id or not path:
        raise SiyuanError("Invalid getPathByID response.", action="get-doc-path", details=response)
    return {
        "notebook": notebook_id,
        "path": path,
    }


def get_doc_hpath_by_id(client: SiyuanClient, doc_id: str) -> str:
    safe_id = ensure_not_empty(doc_id, field_name="doc id", action="get-doc-hpath")
    response = client.post("/api/filetree/getHPathByID", {"id": safe_id}, action="get-doc-hpath")
    data = response.get("data")
    if not isinstance(data, str) or not data.strip():
        raise SiyuanError("Invalid getHPathByID response.", action="get-doc-hpath", details=response)
    return data


def get_doc_ids_by_hpath(client: SiyuanClient, *, notebook_id: str, hpath: str) -> List[str]:
    response = client.post(
        "/api/filetree/getIDsByHPath",
        {
            "path": hpath,
            "notebook": notebook_id,
        },
        action="get-doc-ids-by-hpath",
    )
    data = response.get("data") or []
    if not isinstance(data, list):
        raise SiyuanError("Invalid getIDsByHPath response.", action="get-doc-ids-by-hpath", details=response)
    return [str(item) for item in data if isinstance(item, str) and item.strip()]


def get_doc_meta_by_id(client: SiyuanClient, doc_id: str) -> Dict[str, Any]:
    safe_id = ensure_not_empty(doc_id, field_name="doc id", action="get-doc-meta")
    path_info = get_doc_path_by_id(client, safe_id)
    hpath = get_doc_hpath_by_id(client, safe_id)
    content = hpath.rstrip("/").split("/")[-1] if hpath.strip("/") else ""
    return {
        "id": safe_id,
        "root_id": safe_id,
        "box": path_info["notebook"],
        "path": path_info["path"],
        "hpath": hpath,
        "content": content,
    }


def get_doc_meta_by_path(client: SiyuanClient, *, notebook_id: str, notebook_name: str, doc_path: str) -> Dict[str, Any]:
    safe_path = normalize_doc_path(doc_path)
    doc_ids = get_doc_ids_by_hpath(client, notebook_id=notebook_id, hpath=safe_path)
    if not doc_ids:
        raise SiyuanError(
            f"Document path not found: {safe_path}",
            action="get-doc-meta-by-path",
            details={"notebook": notebook_name, "path": safe_path},
        )
    if len(doc_ids) > 1:
        raise SiyuanError(
            f"Multiple documents matched path: {safe_path}",
            action="get-doc-meta-by-path",
            details={"doc_ids": doc_ids},
        )
    return get_doc_meta_by_id(client, doc_ids[0])


def read_doc(client: SiyuanClient, doc_id: str) -> Dict[str, Any]:
    safe_id = ensure_not_empty(doc_id, field_name="doc id", action="read")
    response = client.post("/api/export/exportMdContent", {"id": safe_id}, action="read")
    data = response.get("data") or {}
    raw_content = data.get("content", "")
    return {
        "id": safe_id,
        "hPath": data.get("hPath"),
        "content": raw_content,
        "raw_content": raw_content,
        "editable_content": extract_editable_markdown(raw_content),
        "title": extract_title_line(raw_content),
    }


def get_child_blocks(client: SiyuanClient, block_id: str) -> List[Dict[str, Any]]:
    safe_id = ensure_not_empty(block_id, field_name="block id", action="get-child-blocks")
    response = client.post("/api/block/getChildBlocks", {"id": safe_id}, action="get-child-blocks")
    data = response.get("data") or []
    if not isinstance(data, list):
        raise SiyuanError("Invalid getChildBlocks response.", action="get-child-blocks", details=response)
    return data


def insert_block(
    client: SiyuanClient,
    *,
    markdown: str,
    previous_id: Optional[str] = None,
    next_id: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_markdown = normalize_markdown(markdown).strip("\n")
    payload: Dict[str, Any] = {
        "dataType": "markdown",
        "data": normalized_markdown,
    }
    if previous_id:
        payload["previousID"] = previous_id
    if next_id:
        payload["nextID"] = next_id
    if parent_id:
        payload["parentID"] = parent_id
    if not any(payload.get(key) for key in ("previousID", "nextID", "parentID")):
        raise SiyuanError(
            "insertBlock requires previousID, nextID, or parentID.",
            action="insert-block",
        )
    response = client.post("/api/block/insertBlock", payload, action="insert-block")
    data = response.get("data") or []
    if not isinstance(data, list):
        raise SiyuanError("Invalid insertBlock response.", action="insert-block", details=response)
    return {
        "markdown": normalized_markdown,
        "data": data,
    }


def delete_block(client: SiyuanClient, block_id: str) -> None:
    safe_id = ensure_not_empty(block_id, field_name="block id", action="delete-block")
    client.post("/api/block/deleteBlock", {"id": safe_id}, action="delete-block")


def extract_first_inserted_block_id(insert_result: Dict[str, Any]) -> Optional[str]:
    operations = insert_result.get("data") or []
    for batch in operations:
        if not isinstance(batch, dict):
            continue
        for operation in batch.get("doOperations") or []:
            if not isinstance(operation, dict):
                continue
            block_id = operation.get("id")
            if isinstance(block_id, str) and block_id.strip():
                return block_id
    return None


def run_sql(client: SiyuanClient, statement: str, *, action: str) -> List[Dict[str, Any]]:
    safe_stmt = ensure_not_empty(statement, field_name="SQL statement", action=action)
    response = client.post("/api/query/sql", {"stmt": safe_stmt}, action=action)
    rows = response.get("data") or []
    if not isinstance(rows, list):
        raise SiyuanError("Invalid SQL response.", action=action, details=response)
    return rows


def escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def search_docs(
    client: SiyuanClient,
    config: SiyuanConfig,
    *,
    query: str,
    notebook_name: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    safe_query = ensure_not_empty(query, field_name="query", action="search")
    search_limit = max(1, min(limit, 50))
    notebook_names: Sequence[str]
    if notebook_name:
        notebook_names = [ensure_allowed_notebook(config, notebook_name)]
        notebook_rows = [find_notebook_by_name(client, notebook_names[0])]
    elif config.allowed_notebook_names:
        notebook_names = config.allowed_notebook_names
        notebook_rows = [find_notebook_by_name(client, name) for name in notebook_names]
    else:
        notebook_rows = list_notebooks(client)
        notebook_names = [str(item.get("name") or "") for item in notebook_rows if item.get("name")]

    if not notebook_rows:
        return []

    box_clause = ", ".join(f"'{escape_sql_literal(item['id'])}'" for item in notebook_rows)
    escaped_query = escape_sql_literal(safe_query)
    stmt = (
        f"SELECT {DOC_SQL_COLUMNS} FROM blocks "
        f"WHERE type = 'd' AND box IN ({box_clause}) AND id IN ("
        f"SELECT root_id FROM blocks "
        f"WHERE box IN ({box_clause}) "
        f"AND (content LIKE '%{escaped_query}%' OR hpath LIKE '%{escaped_query}%') "
        f"GROUP BY root_id "
        f"ORDER BY MAX(updated) DESC "
        f"LIMIT {search_limit}"
        f") "
        f"ORDER BY updated DESC LIMIT {search_limit}"
    )
    return run_sql(client, stmt, action="search")


def create_doc(
    client: SiyuanClient,
    config: SiyuanConfig,
    *,
    notebook_name: str,
    path: str,
    markdown: str,
    if_exists: str = "error",
) -> Dict[str, Any]:
    target_notebook_name = ensure_allowed_notebook(config, notebook_name)
    notebook = find_notebook_by_name(client, target_notebook_name)
    safe_path = normalize_doc_path(path)
    normalized_markdown = normalize_markdown(markdown)
    existing_doc_ids = get_doc_ids_by_hpath(client, notebook_id=notebook["id"], hpath=safe_path)
    if len(existing_doc_ids) > 1:
        raise SiyuanError(
            f"Multiple documents matched path: {safe_path}",
            action="create-doc",
            details={"path": safe_path, "doc_ids": existing_doc_ids},
        )
    if existing_doc_ids:
        existing_doc_id = existing_doc_ids[0]
        if if_exists == "error":
            raise SiyuanError(
                f"Document already exists: {safe_path}",
                action="create-doc",
                details={
                    "path": safe_path,
                    "doc_id": existing_doc_id,
                    "if_exists": if_exists,
                },
            )
        if if_exists == "skip":
            verification = read_doc(client, existing_doc_id)
            return {
                "id": existing_doc_id,
                "notebook": target_notebook_name,
                "notebook_id": notebook["id"],
                "path": safe_path,
                "content": verification.get("content", ""),
                "hPath": verification.get("hPath"),
                "verified": True,
                "mismatch_reason": None,
                "created": False,
                "skipped": True,
                "if_exists": if_exists,
            }
        if if_exists == "replace":
            update_result = update_doc(client, doc_id=existing_doc_id, markdown=normalized_markdown)
            return {
                "id": existing_doc_id,
                "notebook": target_notebook_name,
                "notebook_id": notebook["id"],
                "path": safe_path,
                "content": update_result["after"].get("content", ""),
                "hPath": update_result["after"].get("hPath"),
                "verified": update_result.get("verified", False),
                "mismatch_reason": update_result.get("mismatch_reason"),
                "created": False,
                "skipped": False,
                "if_exists": if_exists,
                "before": update_result.get("before"),
                "after": update_result.get("after"),
            }
        raise SiyuanError(
            f"Unsupported if_exists strategy: {if_exists}",
            action="create-doc",
            details={"if_exists": if_exists},
        )
    payload = {
        "notebook": notebook["id"],
        "path": safe_path,
        "markdown": normalized_markdown,
    }
    response = client.post("/api/filetree/createDocWithMd", payload, action="create-doc")
    doc_id = response.get("data")
    if not isinstance(doc_id, str) or not doc_id:
        raise SiyuanError("Unexpected createDocWithMd response.", action="create-doc", details=response)
    verification = read_doc(client, doc_id)
    verified, mismatch_reason = verify_write(expected=normalized_markdown, actual=verification.get("content", ""))
    return {
        "id": doc_id,
        "notebook": target_notebook_name,
        "notebook_id": notebook["id"],
        "path": safe_path,
        "content": verification.get("content", ""),
        "hPath": verification.get("hPath"),
        "verified": verified,
        "mismatch_reason": mismatch_reason,
        "created": True,
        "skipped": False,
        "if_exists": if_exists,
    }


def delete_doc(client: SiyuanClient, *, doc_meta: Dict[str, Any]) -> Dict[str, Any]:
    doc_id = ensure_not_empty(str(doc_meta.get("id") or ""), field_name="doc id", action="delete-doc")
    notebook_id = ensure_not_empty(str(doc_meta.get("box") or ""), field_name="notebook id", action="delete-doc")
    raw_path = ensure_not_empty(str(doc_meta.get("path") or ""), field_name="doc path", action="delete-doc")
    hpath = ensure_not_empty(str(doc_meta.get("hpath") or ""), field_name="doc hpath", action="delete-doc")

    before = read_doc(client, doc_id)
    client.post(
        "/api/filetree/removeDoc",
        {
            "notebook": notebook_id,
            "path": raw_path,
        },
        action="delete-doc",
    )

    exists_after_id = True
    remaining_doc_ids: List[str] = [doc_id]
    for _ in range(10):
        try:
            get_doc_meta_by_id(client, doc_id)
            exists_after_id = True
        except SiyuanError:
            exists_after_id = False
        remaining_doc_ids = get_doc_ids_by_hpath(client, notebook_id=notebook_id, hpath=hpath)
        if (not exists_after_id) and (doc_id not in remaining_doc_ids):
            break
        time.sleep(0.2)

    verified = (not exists_after_id) and (doc_id not in remaining_doc_ids)

    return {
        "id": doc_id,
        "notebook_id": notebook_id,
        "path": raw_path,
        "hpath": hpath,
        "before": before,
        "verified": verified,
        "deleted": verified,
        "exists_after_id": exists_after_id,
        "remaining_doc_ids": remaining_doc_ids,
    }


def update_doc(client: SiyuanClient, *, doc_id: str, markdown: str) -> Dict[str, Any]:
    safe_id = ensure_not_empty(doc_id, field_name="doc id", action="update")
    normalized_markdown = normalize_markdown(markdown)
    before = read_doc(client, safe_id)
    payload = {
        "id": safe_id,
        "dataType": "markdown",
        "data": normalized_markdown,
    }
    client.post("/api/block/updateBlock", payload, action="update")
    after = read_doc(client, safe_id)
    verified, mismatch_reason = verify_write(expected=normalized_markdown, actual=after.get("content", ""))
    return {
        "id": safe_id,
        "before": before,
        "after": after,
        "verified": verified,
        "mismatch_reason": mismatch_reason,
    }


def append_doc(client: SiyuanClient, *, doc_id: str, markdown: str, separator: str = "\n\n") -> Dict[str, Any]:
    current = read_doc(client, doc_id)
    normalized_append = normalize_markdown(markdown).strip("\n")
    existing_body = current.get("editable_content") or extract_editable_markdown(current.get("content", ""))
    if existing_body.rstrip("\n"):
        new_content = existing_body.rstrip("\n") + separator + normalized_append + "\n"
    else:
        new_content = normalized_append + "\n"
    result = update_doc(client, doc_id=doc_id, markdown=new_content)
    result["appended_markdown"] = normalized_append
    return result


def verify_write(*, expected: str, actual: str) -> Tuple[bool, Optional[str]]:
    normalized_expected = normalize_markdown(expected).strip()
    normalized_actual = normalize_markdown(actual).strip()
    normalized_actual_editable = extract_editable_markdown(actual).strip()
    if normalized_expected == normalized_actual:
        return True, None
    if normalized_expected == normalized_actual_editable:
        return True, None
    if normalized_expected in normalized_actual:
        return True, None
    if normalized_expected in normalized_actual_editable:
        return True, None
    return False, "Read-back content does not match expected markdown."


def normalize_doc_path(path: str) -> str:
    stripped = ensure_not_empty(path, field_name="path", action="normalize-path")
    if re.match(r"^[A-Za-z]:[\\/]", stripped):
        raise SiyuanError(
            "Detected a Windows filesystem path in --path. If you are using Git Bash on Windows, do not start the Siyuan hpath with '/'. Use a human path like '网络配置' or '运维指南/SSH 免密登录'.",
            action="normalize-path",
            details={"path": stripped},
        )
    normalized = stripped.replace("\\", "/")
    if normalized.endswith(".sy"):
        normalized = normalized[:-3]
    parts = [part.strip() for part in normalized.split("/") if part.strip()]
    canonical = "/" + "/".join(parts)
    return canonical or "/"


def get_heading_level_from_block(block: Dict[str, Any]) -> Optional[int]:
    if block.get("type") != "h":
        return None
    sub_type = str(block.get("subType") or "")
    match = HEADING_SUBTYPE_PATTERN.match(sub_type)
    if not match:
        return None
    return int(match.group(1))


def parse_heading_selector(heading: str, level: Optional[int] = None) -> Tuple[int, str]:
    raw_heading = ensure_not_empty(heading, field_name="heading", action="section")
    heading_match = HEADING_LINE_PATTERN.match(raw_heading)
    if heading_match:
        return len(heading_match.group(1)), heading_match.group(2).strip()

    if level is None:
        level = 2
    if level < 1 or level > 6:
        raise SiyuanError("Heading level must be between 1 and 6.", action="section", details={"level": level})
    return level, raw_heading.strip()


def find_heading_block(
    blocks: Sequence[Dict[str, Any]],
    *,
    heading: str,
    level: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    target_level, target_heading = parse_heading_selector(heading, level)
    matches: List[Dict[str, Any]] = []
    for block in blocks:
        current_level = get_heading_level_from_block(block)
        if current_level != target_level:
            continue
        current_heading = str(block.get("content") or "").strip()
        if current_heading == target_heading:
            matches.append(block)
    if len(matches) > 1:
        raise SiyuanError(
            f"Multiple headings matched: {'#' * target_level} {target_heading}",
            action="section",
            details={
                "heading": target_heading,
                "level": target_level,
                "matches": [item.get("id") for item in matches],
            },
        )
    return matches[0] if matches else None


def find_section_bounds(markdown: str, *, heading: str, level: Optional[int] = None) -> Optional[Tuple[int, int, int, str]]:
    target_level, target_heading = parse_heading_selector(heading, level)
    normalized = normalize_markdown(markdown)
    lines = normalized.splitlines(keepends=True)
    offsets: List[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)

    start_index: Optional[int] = None
    for idx, line in enumerate(lines):
        match = HEADING_LINE_PATTERN.match(line.rstrip("\n"))
        if not match:
            continue
        current_level = len(match.group(1))
        current_heading = match.group(2).strip()
        if current_level == target_level and current_heading == target_heading:
            start_index = idx
            break

    if start_index is None:
        return None

    end_offset = len(normalized)
    for idx in range(start_index + 1, len(lines)):
        match = HEADING_LINE_PATTERN.match(lines[idx].rstrip("\n"))
        if not match:
            continue
        current_level = len(match.group(1))
        if current_level <= target_level:
            end_offset = offsets[idx]
            break

    return offsets[start_index], end_offset, target_level, target_heading


def render_section(*, heading: str, level: int, markdown: str) -> str:
    body = normalize_markdown(markdown).strip("\n")
    section_title = f"{'#' * level} {heading}"
    if not body:
        return section_title + "\n"
    return section_title + "\n\n" + body + "\n"


def merge_markdown_parts(*parts: str) -> str:
    stripped_parts = [normalize_markdown(part).strip("\n") for part in parts if normalize_markdown(part).strip("\n")]
    if not stripped_parts:
        return ""
    return "\n\n".join(stripped_parts) + "\n"


def replace_section_markdown(
    markdown: str,
    *,
    heading: str,
    replacement_markdown: str,
    level: Optional[int] = None,
    create_if_missing: bool = False,
) -> Tuple[str, bool]:
    normalized = normalize_markdown(markdown)
    bounds = find_section_bounds(normalized, heading=heading, level=level)
    target_level, target_heading = parse_heading_selector(heading, level)
    new_section = render_section(heading=target_heading, level=target_level, markdown=replacement_markdown)

    if bounds is None:
        if not create_if_missing:
            raise SiyuanError(
                f"Section not found: {'#' * target_level} {target_heading}",
                action="section",
                details={"heading": target_heading, "level": target_level},
            )
        return merge_markdown_parts(normalized, new_section), True

    start_offset, end_offset, _, _ = bounds
    prefix = normalized[:start_offset]
    suffix = normalized[end_offset:]
    return merge_markdown_parts(prefix, new_section, suffix), False


def replace_doc_section(
    client: SiyuanClient,
    *,
    doc_id: str,
    heading: str,
    markdown: str,
    level: Optional[int] = None,
    create_if_missing: bool = False,
) -> Dict[str, Any]:
    current = read_doc(client, doc_id)
    current_body = current.get("editable_content") or extract_editable_markdown(current.get("content", ""))
    updated_body, created = replace_section_markdown(
        current_body,
        heading=heading,
        replacement_markdown=markdown,
        level=level,
        create_if_missing=create_if_missing,
    )
    target_level, target_heading = parse_heading_selector(heading, level)
    doc_blocks = get_child_blocks(client, doc_id)
    heading_block = find_heading_block(doc_blocks, heading=target_heading, level=target_level)
    normalized_body_markdown = normalize_markdown(markdown).strip("\n")

    if heading_block is None:
        if not create_if_missing:
            raise SiyuanError(
                f"Section not found: {'#' * target_level} {target_heading}",
                action="section",
                details={"heading": target_heading, "level": target_level},
            )
        new_section_markdown = render_section(heading=target_heading, level=target_level, markdown=markdown)
        if doc_blocks:
            insert_result = insert_block(
                client,
                markdown=new_section_markdown,
                previous_id=str(doc_blocks[-1].get("id") or ""),
            )
        else:
            insert_result = insert_block(client, markdown=new_section_markdown, parent_id=doc_id)
        inserted_heading_id = extract_first_inserted_block_id(insert_result)
        after = read_doc(client, doc_id)
        verified, mismatch_reason = verify_write(expected=updated_body, actual=after.get("content", ""))
        return {
            "id": doc_id,
            "before": current,
            "after": after,
            "verified": verified,
            "mismatch_reason": mismatch_reason,
            "mode": "block",
            "section": {
                "heading": target_heading,
                "level": target_level,
                "created": True,
                "heading_block_id": inserted_heading_id,
                "replaced_child_count": 0,
                "inserted_markdown": new_section_markdown.strip("\n"),
            },
        }

    heading_id = str(heading_block.get("id") or "")
    existing_children = get_child_blocks(client, heading_id)
    existing_child_ids = [str(item.get("id") or "") for item in existing_children if str(item.get("id") or "")]
    if normalized_body_markdown:
        insert_result = insert_block(client, markdown=normalized_body_markdown, previous_id=heading_id)
    else:
        insert_result = None

    for block_id in reversed(existing_child_ids):
        delete_block(client, block_id)

    after = read_doc(client, doc_id)
    verified, mismatch_reason = verify_write(expected=updated_body, actual=after.get("content", ""))
    result = {
        "id": doc_id,
        "before": current,
        "after": after,
        "verified": verified,
        "mismatch_reason": mismatch_reason,
        "mode": "block",
    }
    result["section"] = {
        "heading": target_heading,
        "level": target_level,
        "created": created,
        "heading_block_id": heading_id,
        "replaced_child_count": len(existing_child_ids),
        "inserted_markdown": normalized_body_markdown,
    }
    if insert_result is not None:
        result["section"]["first_inserted_block_id"] = extract_first_inserted_block_id(insert_result)
    return result
