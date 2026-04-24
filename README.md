# export

Markdown session export for Codex.

`export` is a Codex Skill that turns a local Codex session JSONL file into a readable Markdown transcript. It is intended as an interim, user-installable `/export`-style workflow while native Codex session export support is unavailable in the installed CLI.

## Why

Conversation exports are useful when you want another model pass to review how a session went, identify repeated mistakes, and turn those lessons into project rules such as `AGENTS.md`. Markdown is the default format because LLM conversations are already mostly Markdown, and the result is easy to read, diff, archive, and feed back into another model.

## What It Exports

By default, the Skill exports:

- visible user messages
- visible assistant messages
- session metadata such as session id, source file, cwd, timestamps, originator, and CLI version

By default, the Skill does not export:

- system prompts
- developer instructions
- AGENTS or environment context injection
- encrypted reasoning
- tool calls or command output

Tool calls and command output are included only when explicitly requested with `--include-tools`.

## Install

```bash
npx skills add GaoSSR/codex-export-skill --agent codex -g -y --copy
```

This installs `export` as a global Codex Skill. Restart Codex after installing so the `$export` trigger is discovered.

To inspect before installing:

```bash
npx skills add GaoSSR/codex-export-skill --list
```

## Usage

In Codex, ask:

```text
$export export the current session to Markdown
```

The Skill writes the Markdown file into `codex-session-exports/` under the active workspace and replies with the absolute path plus a short summary.

You can also run the bundled script directly:

```bash
EXPORT_SKILL_DIR="${CODEX_EXPORT_SKILL_DIR:-$HOME/.agents/skills/export}"
[ -f "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" ] || EXPORT_SKILL_DIR="$HOME/.codex/skills/export"
python3 "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" \
  --output-dir "$(pwd)/codex-session-exports"
```

List recent sessions:

```bash
EXPORT_SKILL_DIR="${CODEX_EXPORT_SKILL_DIR:-$HOME/.agents/skills/export}"
[ -f "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" ] || EXPORT_SKILL_DIR="$HOME/.codex/skills/export"
python3 "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" --list
```

Export a specific session:

```bash
EXPORT_SKILL_DIR="${CODEX_EXPORT_SKILL_DIR:-$HOME/.agents/skills/export}"
[ -f "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" ] || EXPORT_SKILL_DIR="$HOME/.codex/skills/export"
python3 "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" \
  --session-id <session-id> \
  --output-dir "$(pwd)/codex-session-exports"
```

Export with tool logs:

```bash
EXPORT_SKILL_DIR="${CODEX_EXPORT_SKILL_DIR:-$HOME/.agents/skills/export}"
[ -f "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" ] || EXPORT_SKILL_DIR="$HOME/.codex/skills/export"
python3 "$EXPORT_SKILL_DIR/scripts/export_codex_session.py" \
  --include-tools \
  --output-dir "$(pwd)/codex-session-exports"
```

## Session Selection

The exporter selects a session in this order:

1. `--session-file <path>`
2. `CODEX_SESSION_FILE`
3. `--session-id <id>`
4. `CODEX_THREAD_ID` or `CODEX_SESSION_ID`
5. latest Codex session whose recorded cwd matches the active workspace
6. latest Codex session globally

Codex session files are read from `CODEX_HOME` or `~/.codex`, including `sessions/**/*.jsonl` and `archived_sessions/*.jsonl`.

## Development

Run the test suite:

```bash
python3 -m unittest discover -s skills/export/tests -p 'test_*.py' -v
```

Validate the Skill shape when Codex's system skill validator is available:

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skills/export
```

## Upstream Direction

The long-term target is native Codex CLI support for `/export`, with Markdown as the default output format. This repository keeps the workflow usable as a Skill until an upstream implementation is available and merged.

This is not an official OpenAI project.

## License

MIT
