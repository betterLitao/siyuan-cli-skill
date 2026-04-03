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
- `scope_mode`
- `default_notebook`
- `purpose_notebooks`
- `has_token`
- `config_file_path`
- `server_base_url_hint`
- `required_env`
- `optional_env`
- `deprecated_env`
- `doctor` when `--doctor` is used

`doctor` fields:

- `scope_mode`
- `allowed_notebooks`
- `default_notebook`
- `purpose_notebooks`
- `config_file`
- `sources`
- `environment_layers`
- `missing_required`
- `advisories`
- `deprecated`

Notes:

- `config --doctor` can succeed even when required config is missing
- plain `config` fails fast if required connection values are missing
- on Windows, `advisories` can explain that a value exists in `user` or `machine` env but the current process did not inherit it yet

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
2. replace the whole document
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
2. append content to the editable body
3. rebuild the full document while preserving frontmatter and top-level title
4. read back and verify

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

1. read the editable document body
2. find the target heading
3. prefer block-level replacement under the existing heading block
4. if the markdown section exists but block matching fails, fall back to a document-level rewrite
5. read back and verify

`data` fields:

- `id`
- `before`
- `after`
- `verified`
- `mismatch_reason`
- `mode`
- `section`
- `meta`

Mode values:

- `block`: block edit path succeeded
- `document`: fallback document rewrite path was used

## `upsert-section`

Input:

- same as `replace-section`

Behavior:

1. read the editable document body
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
- `--purpose <key>` optional

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

1. if `--notebook` is present, that value is used
2. else if `purpose_notebooks[--purpose]` exists, that value is used
3. else if `default_notebook` exists, that value is used
4. else if `allowed_notebooks` is not empty, the first value is used
5. otherwise the command fails and requires `--notebook`

Compatibility rule:

- if `SIYUAN_LEARN_NOTEBOOKS` is configured and `purpose_notebooks.learn` is missing, the first legacy learn notebook is used for `--purpose learn`

## `delete-doc`

Input:

- `--doc-id <id>` or `--path + --notebook`
- `--yes` required

Behavior:

1. resolve target document
2. preserve the pre-delete content in the result
3. call official `removeDoc`
4. verify that the document ID and hpath are gone

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

## Verification rules

Write verification only succeeds on:

- exact full-document match, or
- exact editable-body match

Substring-only matches are rejected.

## Scope rules

The CLI supports two modes:

### Restricted mode

When `SIYUAN_ALLOWED_NOTEBOOKS` is set:

- read, search, and write operations are restricted to that whitelist
- passing a notebook outside the whitelist raises a scope error

### Unrestricted mode

When `SIYUAN_ALLOWED_NOTEBOOKS` is empty:

- the CLI does not enforce a notebook whitelist
- searches span all notebooks visible to the token
- `create-doc` still needs either `--notebook` or a resolvable default notebook
