# Selection And Format

## Session Sources

The exporter searches these locations under `CODEX_HOME` or `~/.codex`:

- `sessions/**/*.jsonl`
- `archived_sessions/*.jsonl`

The current-session selection first uses a process-provided conversation id when available:

- `CODEX_THREAD_ID`
- `CODEX_SESSION_ID`

If neither exists, the fallback heuristic is intentionally narrow: prefer the latest file whose `session_meta.payload.cwd` equals the process working directory. This matches the way Codex records interactive sessions while still working in older or stripped-down environments.

## Included Records

Default export includes:

- `event_msg` records with `payload.type == "user_message"`
- `response_item` records with assistant `payload.type == "message"`

Optional `--include-tools` export also includes:

- `response_item` records with `payload.type == "function_call"`
- `response_item` records with `payload.type == "function_call_output"`

## Excluded Records

The exporter intentionally skips:

- `session_meta.payload.base_instructions`
- `turn_context`
- `response_item` messages from developer/system roles
- AGENTS/project-doc context injection messages
- encrypted or summarized reasoning records
- duplicate `event_msg.agent_message` records

## Markdown Boundaries

Visible message content is emitted as-is. Tool call arguments and tool outputs are wrapped in code fences. If content contains triple backticks, the exporter chooses a longer fence so the Markdown remains valid.

Local source file paths and cwd values in Markdown metadata are redacted by default to their basenames. Use `--show-paths` only when a full source path is intentionally needed.

Use `--json` when the caller needs stable machine-readable result fields such as `file`, `session_id`, `source_file`, `selected_by`, `message_count`, and `include_tools`.

## Known Boundary

An export captures the session file state at the moment the script reads it. The assistant response that reports the exported path is written after the export command finishes, so it is not part of that same export.
