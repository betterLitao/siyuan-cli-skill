---
name: siyuan
description: Use when an assistant or automation needs to read or edit Siyuan documents reliably through a local CLI instead of hand-writing Kernel API payloads.
---

# Siyuan document operations

This is a multi-file skill.

- Keep `SKILL.md`, `scripts/`, and `references/` together.
- Main entry: `scripts/siyuan_cli.py`
- Raw HTTP requests are fallback only, not the default path.

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

1. Use the CLI first. Do not hand-write Kernel API payloads unless the CLI is unavailable.
2. For long Markdown, prefer `--input-file` over inline `--text`.
3. If the target document is ambiguous, run `search` first and confirm before writing.
4. Every write must be followed by read-back verification.
5. Prefer section-level edits before full-document rewrites.
6. Notebook scope must be config-driven, not hard-coded in prompts.
7. Authentication is driven by `SIYUAN_TOKEN`; do not treat `accessAuthCode` as the request auth header.
8. On Windows Git Bash, avoid leading `/` in Siyuan hpaths.

## Config workflow

Show effective config:

```bash
python scripts/siyuan_cli.py config
```

Diagnose missing or conflicting config:

```bash
python scripts/siyuan_cli.py config --doctor
```

Doctor mode is the first thing to run when config seems to disappear. It shows:

- resolved scope and default notebook
- purpose mapping
- config file path and parse errors
- which source won for each value
- missing required values
- advisories when Windows global env exists but the current process did not inherit it
- Windows process, user, and machine environment layers

Important:

- On Windows, values shown only in `user` or `machine` layers are not active until a new shell or host app inherits them.
- Syncing the skill files across devices does not sync runtime config into the current process. Each machine still needs its own env or config file path.

## Config model

Required:

- `SIYUAN_BASE_URL` or `SIYUAN_URL` or `SIYUAN_REMOTE_URL`
- `SIYUAN_TOKEN`

Recommended optional:

- `SIYUAN_TIMEOUT`
- `SIYUAN_ALLOWED_NOTEBOOKS`
- `SIYUAN_DEFAULT_NOTEBOOK`
- `SIYUAN_PURPOSE_NOTEBOOKS`
- `SIYUAN_CONFIG_FILE`

Deprecated compatibility alias:

- `SIYUAN_LEARN_NOTEBOOKS`

Default config file lookup:

- Windows: `~/.siyuan-cli-skill.json`
- macOS / Linux: `~/.config/siyuan-cli-skill/config.json`

Environment variables override config file values.

## Notebook selection

`create-doc` resolves its target notebook in this order:

1. explicit `--notebook`
2. `purpose_notebooks[--purpose]`
3. `default_notebook`
4. first entry in `allowed_notebooks`
5. fail fast and require `--notebook`

Compatibility rule:

- if `SIYUAN_LEARN_NOTEBOOKS` exists and `purpose_notebooks.learn` is missing, the first legacy learn notebook becomes `purpose=learn`

## Common workflow

Show config:

```bash
python scripts/siyuan_cli.py config --doctor
```

Read a document:

```bash
python scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python scripts/siyuan_cli.py read --path "Guides/API Wrapper" --notebook "Projects"
```

Search candidates:

```bash
python scripts/siyuan_cli.py search --query "API gateway"
python scripts/siyuan_cli.py search --query "incident review" --notebook "Notes"
```

Update or append:

```bash
python scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
```

Section edits:

```bash
python scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "Notes" --input-file "section.md"
python scripts/siyuan_cli.py upsert-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --level 2 --input-file "section.md"
```

Create a document with purpose routing:

```bash
python scripts/siyuan_cli.py create-doc --purpose reference --path "Guides/API Wrapper" --input-file "content.md"
```

Delete a document:

```bash
python scripts/siyuan_cli.py delete-doc --doc-id "20260314140600-8gkfmc2" --yes
```

## Write behavior

- `append` preserves frontmatter and the top-level title instead of rewriting only the editable body.
- `replace-section` prefers block edits but falls back to a document rewrite if heading block matching is unreliable.
- verification only succeeds on exact full-document or exact editable-body matches.

## Search notes

- `search` looks at title, hpath, and block content, then returns root-document rows.
- body search still relies on `query/sql`
- if SQL access is unavailable, use `read --doc-id` or `read --path + --notebook` for precise access

## Fallback guidance

Only fall back to raw HTTP requests when:

- the CLI files are unavailable
- the environment cannot run Python
- or you are debugging the CLI itself

Even then:

- keep using the same token auth model
- prefer official filetree or block endpoints first
- keep request bodies minimal and explicit
