# Contributing

Thanks for improving `codex-export-skill`.

## Project Contract

Keep changes aligned with the core contract:

- `$export` should remain simple to invoke from Codex.
- Markdown should remain the default transcript format.
- Privacy defaults must stay conservative.
- Tool logs, full local paths, and other sensitive execution details must require explicit opt-in.

## Development

Run the local verification suite before opening a pull request:

```bash
python3 -m py_compile skills/export/scripts/export_codex_session.py tests/test_export_codex_session.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
npx skills add . --list
```

The exporter requires Python 3.10 or newer.

## Parser And Formatting Changes

Session JSONL and Markdown rendering changes are syntax-sensitive. Before changing parser, serializer, escaping, redaction, or selection behavior, define the invariant being changed and add regression tests for:

- positive cases that prove the bug is fixed
- negative cases that prove nearby literal text is preserved
- contextual cases that prove the rewrite only applies in the intended structure

For delimiter-sensitive changes, include near-miss examples such as literal Markdown fences, quoted context markers, and prose that only looks like injected context.

## Pull Requests

In pull request descriptions, include:

- root cause or motivation
- behavior changed
- privacy impact, if any
- tests run
