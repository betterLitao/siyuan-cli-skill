---
name: siyuan
description: Use a stable Python CLI wrapper to read, search, update, append, and create Siyuan documents without hand-writing Kernel API request bodies.
---

# Siyuan document operations

This is a **multi-file skill**.

- Keep `SKILL.md`, `scripts/`, and `references/` together.
- Main entry: `scripts/siyuan_cli.py`
- Raw `curl` / `Invoke-RestMethod` should be fallback only, not the default path.

## Primary invocation

### Windows

```bash
python scripts/siyuan_cli.py <command> [...args]
```

### macOS / Linux

```bash
python3 scripts/siyuan_cli.py <command> [...args]
```

## Commands

- `config`
- `read`
- `search`
- `update`
- `append`
- `replace-section`
- `upsert-section`
- `create-doc`
- `delete-doc`

All commands return JSON with these top-level fields:

- `ok`
- `action`
- `message`
- `data`
- `error`

Detailed contract: `references/api-contract.md`

## Hard rules

1. **Use the CLI first. Do not hand-write Kernel API payloads unless the CLI is unavailable.**
2. **For long Markdown, prefer `--input-file` over inline `--text`.**
3. **If the target document is ambiguous, run `search` first and ask before writing.**
4. **Every write must be followed by read-back verification.**
5. **Prefer section-level edits before full-document rewrites.**
6. **Document resolution should use official filetree APIs first; SQL is only for search-like cases.**
7. **Authentication is driven by `SIYUAN_TOKEN`; do not treat `accessAuthCode` as the request auth header.**
8. **Notebook scope is controlled by environment variables, not hard-coded notebook names.**
9. **On Windows Git Bash, avoid leading `/` in Siyuan hpaths to prevent path rewriting.**

## Scope and defaults

The CLI supports two optional environment variables:

- `SIYUAN_ALLOWED_NOTEBOOKS`: comma-separated notebook whitelist
- `SIYUAN_LEARN_NOTEBOOKS`: comma-separated notebook list used when `--purpose learn` is selected

Behavior:

- If `SIYUAN_ALLOWED_NOTEBOOKS` is set, read/search/write operations are restricted to that scope.
- If `SIYUAN_ALLOWED_NOTEBOOKS` is empty, the CLI does **not** enforce a notebook whitelist.
- If `create-doc` is called without `--notebook`, the CLI resolves a default notebook from:
  1. `SIYUAN_LEARN_NOTEBOOKS` when `--purpose learn`
  2. otherwise the first notebook in `SIYUAN_ALLOWED_NOTEBOOKS`
- If no default notebook can be resolved, `create-doc` fails fast and asks for `--notebook` or environment config.

## Recommended workflow

### Show effective config

```bash
python scripts/siyuan_cli.py config
```

### Read a known document

By ID:

```bash
python scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
```

By notebook + path:

```bash
python scripts/siyuan_cli.py read --path "Guides/API Wrapper" --notebook "Projects"
```

`read` returns:

- `content` / `raw_content`: original Markdown from `exportMdContent`
- `editable_content`: body view with frontmatter and top-level title removed

### Search candidate documents

```bash
python scripts/siyuan_cli.py search --query "API gateway"
python scripts/siyuan_cli.py search --query "incident review" --notebook "Notes"
```

If multiple candidates are returned, do not guess. Use `hpath` / `content` to disambiguate first.

### Replace the whole document

```bash
python scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
```

### Append to the end of a document

```bash
python scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
```

### Replace only one heading section

```bash
python scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "Notes" --input-file "section.md"
```

Create the section if it does not exist:

```bash
python scripts/siyuan_cli.py upsert-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --input-file "section.md"
```

Optional explicit heading level:

```bash
python scripts/siyuan_cli.py upsert-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --level 2 --input-file "section.md"
```

These section commands now prefer block-level editing:

- keep the heading block
- delete old child blocks under that heading
- insert new Markdown child blocks
- create a new section at the end when `upsert-section` cannot find the heading

### Create a new document

Explicit notebook:

```bash
python scripts/siyuan_cli.py create-doc --notebook "Projects" --path "Guides/API Wrapper" --input-file "content.md"
```

Use default learn notebook mapping:

```bash
python scripts/siyuan_cli.py create-doc --purpose learn --path "Guides/Working Notes" --input-file "content.md"
```

Conflict handling is explicit:

```bash
python scripts/siyuan_cli.py create-doc --notebook "Projects" --path "Guides/API Wrapper" --input-file "content.md" --if-exists skip
python scripts/siyuan_cli.py create-doc --notebook "Projects" --path "Guides/API Wrapper" --input-file "content.md" --if-exists replace
```

`--if-exists` values:

- `error`: fail if the path already exists
- `skip`: keep the existing document and return its current content
- `replace`: reuse the existing document and replace its content

### Delete a document

```bash
python scripts/siyuan_cli.py delete-doc --doc-id "20260314140600-8gkfmc2" --yes
python scripts/siyuan_cli.py delete-doc --path "Scratch/Test Doc" --notebook "Inbox" --yes
```

Delete flow:

- resolve the target document
- read and preserve the pre-delete content in the result
- call official `removeDoc`
- verify the document ID / hpath no longer exists

## Search semantics

`search` does more than title matching.

Within the configured scope, it searches:

- document title / hpath
- block content inside documents

and returns root-document rows.

Notes:

- body search still relies on `query/sql`
- if Siyuan runs in a mode that blocks SQL access, `search` may fail
- in that case use `read --doc-id` or `read --path + --notebook` for precise access

## Environment variables

Required:

- `SIYUAN_BASE_URL` (or `SIYUAN_URL` / `SIYUAN_REMOTE_URL`)
- `SIYUAN_TOKEN`

Optional:

- `SIYUAN_TIMEOUT`
- `SIYUAN_ALLOWED_NOTEBOOKS`
- `SIYUAN_LEARN_NOTEBOOKS`

Examples:

### macOS / Linux

```bash
export SIYUAN_BASE_URL="http://your-siyuan-host:6806"
export SIYUAN_TOKEN="your-siyuan-token"
export SIYUAN_ALLOWED_NOTEBOOKS="Notes,Projects"
export SIYUAN_LEARN_NOTEBOOKS="Notes"
```

### PowerShell

```powershell
$env:SIYUAN_BASE_URL = "http://your-siyuan-host:6806"
$env:SIYUAN_TOKEN = "your-siyuan-token"
$env:SIYUAN_ALLOWED_NOTEBOOKS = "Notes,Projects"
$env:SIYUAN_LEARN_NOTEBOOKS = "Notes"
```

## Fallback guidance

Only fall back to raw HTTP requests when:

- the CLI files are unavailable
- the environment is too constrained to run Python
- or you are debugging the CLI itself

Even then:

- keep using the same environment variable auth model
- prefer official endpoints first
- keep request bodies minimal and explicit
