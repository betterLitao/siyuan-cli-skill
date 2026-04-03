# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- `config --doctor` diagnostics for config source tracing, missing-value hints, and Windows environment layer inspection
- config file fallback support via `SIYUAN_CONFIG_FILE` and per-user default config paths
- regression tests for config loading, append preservation, strict verification, and section fallback behavior

### Changed
- replaced the public-facing `learn_notebooks` model with generic `default_notebook` and `purpose_notebooks`
- kept `SIYUAN_LEARN_NOTEBOOKS` only as a deprecated compatibility alias for `purpose=learn`
- updated README, Chinese README, skill instructions, and API contract to document the generic config model
- extended CI to run the unittest suite instead of compile-only validation

### Fixed
- `append` now preserves frontmatter and the top-level title instead of rewriting only the editable body
- `replace-section` now falls back to a document rewrite when block heading matching fails
- write verification no longer passes on substring-only matches
- `create-doc --purpose <key>` now resolves against generic purpose mappings instead of a hard-coded learn/default pair

## [1.0.0] - 2026-03-21

### Added
- public GitHub repository with MIT license
- reusable multi-file Siyuan skill layout (`SKILL.md`, `scripts/`, `references/`)
- structured CLI commands for config, read, search, update, append, section edits, create, and delete
- block-first `replace-section` / `upsert-section`
- explicit `create-doc --if-exists error|skip|replace`
- read-back verification after all writes
- cross-platform examples for Windows and macOS / Linux
- sample repository screenshot asset for README

### Changed
- removed user-specific notebook names and private workflow assumptions
- moved notebook scope control to environment variables
- made scope behavior explicit: restricted when configured, unrestricted when empty
- made default notebook selection fail fast when no default can be resolved
- rewrote docs as general-purpose public documentation

### Security
- removed local/private placeholders and user-specific operational traces from public docs
- verified repository content with a basic sensitive-string scan before publishing
