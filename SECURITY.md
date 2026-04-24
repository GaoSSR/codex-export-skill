# Security Policy

## Supported Versions

Security fixes target the current `main` branch and the latest tagged release.

## Reporting A Vulnerability

Please do not open a public issue for vulnerabilities that could expose private session content, local paths, secrets, or tool output.

Report security issues privately through GitHub Security Advisories for this repository. Include:

- affected version or commit
- sanitized reproduction steps
- whether the issue can expose hidden prompts, local paths, tool logs, or secrets
- suggested fix, if known

## Privacy Boundary

The default export must not include:

- system prompts
- developer instructions
- AGENTS or project-doc context injection
- Codex Skill context injection such as `<skill>...</skill>`
- environment context injection
- encrypted or summarized reasoning records
- tool calls or command output
- full local source paths in Markdown metadata

Any change that expands exported data must require explicit user opt-in and dedicated regression tests.

If a visible message embeds a Codex Skill context block, the exporter redacts that internal `<skill>...</skill>` block while preserving the rest of the message.
