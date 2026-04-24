---
name: export
description: Use when the user says $export or /export, asks to export the current Codex session, save this conversation as Markdown, or export Codex chat history.
---

# Export

## Purpose

Export a Codex session JSONL file from `~/.codex/sessions` or `~/.codex/archived_sessions` into a readable Markdown transcript.

## Runtime Requirement

- Requires `python3` with Python 3.10 or newer.

## Default Workflow

1. Run the exporter from the active workspace:

```bash
if [ -n "${CODEX_EXPORT_SKILL_DIR:-}" ]; then
  EXPORT_SKILL_DIR="$CODEX_EXPORT_SKILL_DIR"
elif [ -f "$HOME/.codex/skills/export/scripts/export_codex_session.py" ]; then
  EXPORT_SKILL_DIR="$HOME/.codex/skills/export"
else
  EXPORT_SKILL_DIR="$HOME/.agents/skills/export"
fi
python3 "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" --json --output-dir "$(pwd)/codex-session-exports"
```

2. Parse the JSON result and treat `file`, `session_id`, `message_count`, `include_tools`, and `selected_by` as the result.
3. Reply with the absolute Markdown file path and a short export summary.

## Selection Rules

- Default selection is the current Codex conversation id from `CODEX_THREAD_ID` or `CODEX_SESSION_ID` when Codex exposes it to the tool process.
- If no current conversation id is available, select the most recently modified Codex session whose session metadata `cwd` matches the current working directory.
- If no session id or cwd match is available, fall back to the most recent Codex session globally.
- If the user provides a session id, run with `--session-id <id>`.
- If the user provides a JSONL path, run with `--session-file <path>`.

## Content Rules

- Default export includes visible user messages and visible assistant messages.
- Do not paste the full exported transcript into chat unless the user explicitly asks.
- Do not expose system prompts, developer instructions, AGENTS context injection, environment context injection, or encrypted reasoning. The exporter skips these records.
- Tool calls and command outputs are excluded by default. If the user asks for command logs or full execution trace, add `--include-tools`.
- Local source file paths and cwd metadata are redacted in the Markdown by default. Add `--show-paths` only when the user explicitly asks for full local source paths.
- Run the exporter as the final substantive action. The short response that reports the exported file path will only appear in a later export.

## Useful Commands

List recent sessions:

```bash
if [ -n "${CODEX_EXPORT_SKILL_DIR:-}" ]; then
  EXPORT_SKILL_DIR="$CODEX_EXPORT_SKILL_DIR"
elif [ -f "$HOME/.codex/skills/export/scripts/export_codex_session.py" ]; then
  EXPORT_SKILL_DIR="$HOME/.codex/skills/export"
else
  EXPORT_SKILL_DIR="$HOME/.agents/skills/export"
fi
python3 "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" --json --list
```

Export a specific session:

```bash
if [ -n "${CODEX_EXPORT_SKILL_DIR:-}" ]; then
  EXPORT_SKILL_DIR="$CODEX_EXPORT_SKILL_DIR"
elif [ -f "$HOME/.codex/skills/export/scripts/export_codex_session.py" ]; then
  EXPORT_SKILL_DIR="$HOME/.codex/skills/export"
else
  EXPORT_SKILL_DIR="$HOME/.agents/skills/export"
fi
python3 "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" --json --session-id <session-id> --output-dir "$(pwd)/codex-session-exports"
```

Export with tool logs:

```bash
if [ -n "${CODEX_EXPORT_SKILL_DIR:-}" ]; then
  EXPORT_SKILL_DIR="$CODEX_EXPORT_SKILL_DIR"
elif [ -f "$HOME/.codex/skills/export/scripts/export_codex_session.py" ]; then
  EXPORT_SKILL_DIR="$HOME/.codex/skills/export"
else
  EXPORT_SKILL_DIR="$HOME/.agents/skills/export"
fi
python3 "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" --json --include-tools --output-dir "$(pwd)/codex-session-exports"
```

## References

- See `references/selection-and-format.md` for the JSONL selection heuristic and formatting boundaries.
