# siyuan-cli-skill

[![CI](https://github.com/betterLitao/siyuan-cli-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/betterLitao/siyuan-cli-skill/actions/workflows/ci.yml)
[简体中文](README.zh-CN.md)

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-6f42c1.svg)

A reusable multi-file skill and standalone CLI for stable Siyuan document operations.

It wraps Siyuan Kernel APIs behind a Python CLI so assistants and scripts can avoid hand-writing request payloads for common document reads and writes.

## Demo

![Siyuan CLI config demo](assets/demo-config.svg)

## Features

- structured JSON output for every command
- `config --doctor` diagnostics for config sources and missing values
- config file fallback for persistent setup across shells
- generic default notebook routing via `default_notebook` and `purpose_notebooks`
- deprecated `SIYUAN_LEARN_NOTEBOOKS` compatibility for older setups
- read, search, update, append, create, and delete document operations
- block-first `replace-section` / `upsert-section` with document-level fallback
- append flow preserves frontmatter and top-level title
- strict read-back verification after writes
- UTF-8 file input support for long Markdown
- no third-party Python dependencies

## Project structure

```text
siyuan-cli-skill/
├─ assets/
│  └─ demo-config.svg
├─ CHANGELOG.md
├─ LICENSE
├─ README.md
├─ README.zh-CN.md
├─ SKILL.md
├─ references/
│  └─ api-contract.md
├─ scripts/
│  ├─ siyuan_cli.py
│  ├─ siyuan_client.py
│  ├─ siyuan_config.py
│  └─ siyuan_ops.py
└─ tests/
   ├─ test_siyuan_config.py
   └─ test_siyuan_ops.py
```

## Why this exists

Directly calling Siyuan Kernel APIs from prompts is brittle:

- request bodies are easy to get wrong
- long Markdown is noisy to inline
- write verification is easy to skip
- platform-specific encoding and shell issues show up fast

This wrapper centralizes:

- token-based auth
- content normalization
- scope checks
- block and document write flows
- read-back verification
- stable JSON contracts for automation

## Installation

### Option A: use it as a standalone CLI

Requirements:

- Python 3.9+
- a reachable Siyuan instance
- a valid Siyuan API token

```bash
git clone https://github.com/betterLitao/siyuan-cli-skill.git
cd siyuan-cli-skill
```

No `pip install` is required. The CLI uses only the Python standard library.

Set the required environment variables.

#### macOS / Linux

```bash
export SIYUAN_BASE_URL="http://your-siyuan-host:6806"
export SIYUAN_TOKEN="your-siyuan-token"
```

#### PowerShell

```powershell
$env:SIYUAN_BASE_URL = "http://your-siyuan-host:6806"
$env:SIYUAN_TOKEN = "your-siyuan-token"
```

Smoke test:

```bash
python3 scripts/siyuan_cli.py config
python3 scripts/siyuan_cli.py config --doctor
```

On Windows use `python` instead of `python3`.

### Option B: use it as a multi-file skill

Do not copy `SKILL.md` alone. Copy the whole directory.

Typical target layout:

```text
<your-skills-root>/siyuan/
├─ SKILL.md
├─ references/
└─ scripts/
```

Then invoke from the copied skill directory:

```bash
python scripts/siyuan_cli.py config
```

## Quick start

### Windows

```bash
python scripts/siyuan_cli.py config --doctor
python scripts/siyuan_cli.py search --query "API gateway"
python scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
python scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --input-file "section.md"
python scripts/siyuan_cli.py create-doc --purpose reference --path "Guides/API Wrapper" --input-file "content.md"
python scripts/siyuan_cli.py delete-doc --path "Scratch/Test Doc" --notebook "Inbox" --yes
```

### macOS / Linux

```bash
python3 scripts/siyuan_cli.py config --doctor
python3 scripts/siyuan_cli.py search --query "API gateway"
python3 scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python3 scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python3 scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
python3 scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --input-file "section.md"
python3 scripts/siyuan_cli.py create-doc --purpose reference --path "Guides/API Wrapper" --input-file "content.md"
python3 scripts/siyuan_cli.py delete-doc --path "Scratch/Test Doc" --notebook "Inbox" --yes
```

## Configuration model

Required config:

- `SIYUAN_BASE_URL` or `SIYUAN_URL` or `SIYUAN_REMOTE_URL`
- `SIYUAN_TOKEN`

Recommended optional config:

- `SIYUAN_TIMEOUT`
- `SIYUAN_ALLOWED_NOTEBOOKS`
- `SIYUAN_DEFAULT_NOTEBOOK`
- `SIYUAN_PURPOSE_NOTEBOOKS`
- `SIYUAN_CONFIG_FILE`

Deprecated compatibility alias:

- `SIYUAN_LEARN_NOTEBOOKS`

### Example: environment variables

#### macOS / Linux

```bash
export SIYUAN_BASE_URL="http://your-siyuan-host:6806"
export SIYUAN_TOKEN="your-siyuan-token"
export SIYUAN_ALLOWED_NOTEBOOKS="Notes,Projects"
export SIYUAN_DEFAULT_NOTEBOOK="Projects"
export SIYUAN_PURPOSE_NOTEBOOKS="learn=Notes,reference=Projects"
```

#### PowerShell

```powershell
$env:SIYUAN_BASE_URL = "http://your-siyuan-host:6806"
$env:SIYUAN_TOKEN = "your-siyuan-token"
$env:SIYUAN_ALLOWED_NOTEBOOKS = "Notes,Projects"
$env:SIYUAN_DEFAULT_NOTEBOOK = "Projects"
$env:SIYUAN_PURPOSE_NOTEBOOKS = "learn=Notes,reference=Projects"
```

### Example: config file

Default lookup paths:

- Windows: `~/.siyuan-cli-skill.json`
- macOS / Linux: `~/.config/siyuan-cli-skill/config.json`

You can override the path with `SIYUAN_CONFIG_FILE`.

Example:

```json
{
  "base_url": "http://your-siyuan-host:6806",
  "token": "your-siyuan-token",
  "timeout": 30,
  "allowed_notebooks": ["Notes", "Projects"],
  "default_notebook": "Projects",
  "purpose_notebooks": {
    "learn": "Notes",
    "reference": "Projects"
  }
}
```

Environment variables override config file values.

## Scope and default notebook behavior

Notebook scope is config-driven, not hard-coded.

- If `SIYUAN_ALLOWED_NOTEBOOKS` is set, operations are restricted to that whitelist.
- If `SIYUAN_ALLOWED_NOTEBOOKS` is empty, the CLI does not enforce a notebook whitelist.
- `create-doc` resolves the target notebook in this order:
  1. explicit `--notebook`
  2. `purpose_notebooks[--purpose]`
  3. `default_notebook`
  4. first notebook in `allowed_notebooks`
  5. fail fast and require `--notebook`

Compatibility rule:

- if `SIYUAN_LEARN_NOTEBOOKS` is set and `purpose_notebooks.learn` is not set, the first legacy learn notebook is treated as `purpose=learn`

## Diagnostics

Use doctor mode when config seems to disappear:

```bash
python3 scripts/siyuan_cli.py config --doctor
```

Doctor mode reports:

- effective scope and default notebook
- purpose mapping
- config file path and parse errors
- exact source of each resolved value
- missing required values
- Windows process, user, and machine environment layers

That makes it obvious whether a value exists only as a global environment variable, only in the current shell, or nowhere at all.

## Path handling notes

- When using Windows Git Bash, do not start Siyuan paths with `/`.
- Prefer `Guides/API Wrapper` over `/Guides/API Wrapper`.
- Path normalization converts `\` to `/`, removes `.sy`, trims whitespace, and normalizes to Siyuan hpaths internally.

## Auth model

This project uses token-based API auth.

- request auth is driven by `SIYUAN_TOKEN`
- `accessAuthCode` is mainly related to Siyuan service exposure or startup config
- it is not the request auth header used by this CLI

## Write strategy

All write flows follow the same pattern:

1. load Markdown from `--text` or `--input-file`
2. normalize line endings to `\n`
3. strip invalid control characters
4. call the corresponding Siyuan API
5. read back the document
6. verify the result
7. return structured JSON

Additional guarantees:

- `append` preserves frontmatter and the top-level title instead of rewriting only the editable body
- `replace-section` prefers block edits, but falls back to a document rewrite if Siyuan block matching is unreliable
- read-back verification requires exact full-document or exact editable-body matches

## Release notes

See [`CHANGELOG.md`](CHANGELOG.md).

## Notes for maintainers

- keep `SKILL.md` focused on usage strategy
- keep `references/api-contract.md` focused on CLI contract details
- keep `scripts/` as the stable execution layer
- keep tests aligned with hidden regression cases before changing write behavior
