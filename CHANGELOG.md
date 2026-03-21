# Changelog

All notable changes to this project will be documented in this file.

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
