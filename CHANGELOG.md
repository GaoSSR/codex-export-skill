# Changelog

All notable changes to this project will be documented in this file.

## 0.1.1 - 2026-04-24

- Redact Codex Skill context blocks embedded in visible messages while preserving surrounding user text.

## 0.1.0 - 2026-04-24

- Initial public Codex Skill for exporting local Codex sessions as Markdown transcripts.
- Added current-session, cwd-aware, and global session selection fallback.
- Added conservative privacy defaults that exclude system/developer context, reasoning records, and tool logs.
- Added optional tool-log export for explicit debugging workflows.
- Added path-redacted Markdown metadata by default.
- Added machine-readable `--json` CLI output for Skill invocation.
