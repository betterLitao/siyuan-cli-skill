# Siyuan CLI API contract

`scripts/siyuan_cli.py` provides a stable, structured interface for assistants and automation.

## Common output shape

Success:

```json
{
  "ok": true,
  "action": "read",
  "message": "Read document successfully.",
  "data": {},
  "error": null
}
```

Failure:

```json
{
  "ok": false,
  "action": "update",
  "message": "Notebook 'Archive' is outside the configured allowed scope.",
  "data": null,
  "error": {
    "type": "SiyuanError",
    "action": "scope-check",
    "message": "Notebook 'Archive' is outside the configured allowed scope.",
    "details": {
      "requested": "Archive",
      "allowed": ["Notes", "Projects"]
    }
  }
}
```

## `config`

Returns the effective connection and scope config.

Typical fields in `data`:

- `base_url`
- `timeout`
- `allowed_notebooks`
- `learn_notebooks`
- `scope_mode` (`restricted` or `unrestricted`)
- `has_token`
- `required_env`
- `optional_env`

## `read`

Input:

- `--doc-id <id>` or
- `--path <path> --notebook <name>`

Path normalization:

- converts `\` to `/`
- removes `.sy`
- trims extra whitespace around separators
- normalizes to a Siyuan hpath internally

Windows Git Bash note:

- prefer `Guides/API Wrapper` over `/Guides/API Wrapper`

`data` fields:

- `id`
- `hPath`
- `content`
- `raw_content`
- `editable_content`
- `title`
- `resolved_from`
- `meta`

Notes:

- `content` and `raw_content` currently represent the same original Markdown export
- `editable_content` removes frontmatter and top-level title for follow-up editing

## `search`

Input:

- `--query <keyword>`
- `--notebook <name>` optional
- `--limit <n>` optional

`data` fields:

- `query`
- `notebook`
- `count`
- `items`

Each entry in `items` includes at least:

- `id`
- `box`
- `path`
- `hpath`
- `content`
- `root_id`

Notes:

- searches title, hpath, and block content
- returns root-document rows, not loose blocks
- body search relies on `query/sql`
- if SQL access is unavailable, use precise `read` lookups instead

Scope behavior:

- if `SIYUAN_ALLOWED_NOTEBOOKS` is set, `search` is limited to those notebooks
- if it is empty, `search` spans all notebooks visible to the API token

## `update`

Input:

- `--doc-id <id>` or `--path + --notebook`
- `--text <markdown>` or `--input-file <file>`

Behavior:

1. read current content
2. replace the whole document body
3. read back and verify

`data` fields:

- `id`
- `before`
- `after`
- `verified`
- `mismatch_reason`
- `meta`

## `append`

Input:

- `--doc-id <id>` or `--path + --notebook`
- `--text <markdown>` or `--input-file <file>`

Behavior:

1. read current content
2. append content by rewriting the document body
3. read back and verify

`data` fields:

- `id`
- `before`
- `after`
- `verified`
- `mismatch_reason`
- `appended_markdown`
- `meta`

## `replace-section`

Input:

- `--doc-id <id>` or `--path + --notebook`
- `--heading <text>`; supports `Summary` or `## Summary`
- `--level <n>` optional when `--heading` is plain text
- `--text <markdown>` or `--input-file <file>`

Behavior:

1. read the document body view
2. find the target heading
3. keep the heading block and replace only its child blocks
4. read back and verify

`data` fields:

- `id`
- `before`
- `after`
- `verified`
- `mismatch_reason`
- `mode`
- `section`
- `meta`

## `upsert-section`

Input:

- same as `replace-section`

Behavior:

1. read the document body view
2. replace the section if the heading exists
3. otherwise create a new section at the end
4. read back and verify

`data` fields:

- same as `replace-section`

## `create-doc`

Input:

- `--path <path>`
- `--text <markdown>` or `--input-file <file>`
- `--notebook <name>` optional
- `--if-exists error|skip|replace` optional
- `--purpose learn|default` optional

Behavior:

1. resolve target notebook
2. check whether the target path already exists
3. error, skip, or replace based on `--if-exists`
4. create or reuse the document
5. read back and verify

`data` fields:

- `id`
- `notebook`
- `notebook_id`
- `path`
- `content`
- `hPath`
- `verified`
- `mismatch_reason`
- `created`
- `skipped`
- `if_exists`

Default notebook resolution:

- if `--notebook` is present, that value is used
- if `--purpose learn` and `SIYUAN_LEARN_NOTEBOOKS` is configured, the first learn notebook is used
- otherwise the first entry in `SIYUAN_ALLOWED_NOTEBOOKS` is used
- if none of the above are available, the command fails and requires `--notebook`

## `delete-doc`

Input:

- `--doc-id <id>` or `--path + --notebook`
- `--yes` required

Behavior:

1. resolve target document
2. preserve the pre-delete content in the result
3. call official `removeDoc`
4. verify that the document ID / hpath is gone

`data` fields:

- `id`
- `notebook_id`
- `path`
- `hpath`
- `before`
- `verified`
- `deleted`
- `exists_after_id`
- `remaining_doc_ids`
- `meta`

## Scope rules

The CLI supports two modes:

### Restricted mode

When `SIYUAN_ALLOWED_NOTEBOOKS` is set:

- read/write/search operations are restricted to that whitelist
- passing a notebook outside the whitelist raises a scope error

### Unrestricted mode

When `SIYUAN_ALLOWED_NOTEBOOKS` is empty:

- the CLI does not enforce a notebook whitelist
- searches span all notebooks visible to the token
- `create-doc` still needs either `--notebook` or a resolvable default notebook
