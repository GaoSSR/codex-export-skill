<div align="center">

  <img src="assets/header.png" width="480" alt="export - Codex 会话导出为 Markdown 转录稿" />

  <p><strong>将 Codex 会话导出为干净、适合 LLM 再分析的 Markdown。</strong></p>

  <p>
    🌐 <a href="README.md">English</a> |
    🇨🇳 简体中文
  </p>

  <p>
    <img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Skill-111827?style=flat-square" />
    <img alt="Markdown" src="https://img.shields.io/badge/output-Markdown-2563EB?style=flat-square" />
    <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-0F766E?style=flat-square" />
    <img alt="CI" src="https://github.com/GaoSSR/codex-export-skill/actions/workflows/ci.yml/badge.svg" />
  </p>

</div>

`export` 是一个 Codex Skill，用于为 Codex 用户提供 Claude Code 的 `/export` 会话导出工作流。它可以把本地 Codex 会话历史导出为干净的 Markdown 转录稿，更有利于大模型继续解析、复盘和分析。

## 安装

运行要求：

- 支持 Skill 的 Codex
- 可通过 `python3` 调用的 Python 3.10 或更新版本
- 用于执行 `npx skills` 的 Node.js/npm

```bash
npx skills add GaoSSR/codex-export-skill --agent codex -g -y --copy
```

安装完成后重启 Codex，让 `$export` 触发词被重新发现。

### 升级或重装

如果你之前安装过旧版本，请先删除旧副本。否则旧的 `~/.codex/skills/export` 可能会遮蔽 `npx skills` 新安装的版本。

```bash
rm -rf "${CODEX_HOME:-$HOME/.codex}/skills/export" "$HOME/.agents/skills/export"
npx skills add GaoSSR/codex-export-skill --agent codex -g -y --copy
```

重装完成后重启 Codex。

## 快速开始

在 Codex 对话中输入：

```text
$export export the current session to Markdown
```

Skill 会把会话转录稿写入当前工作区下的 `codex-session-exports/`，并返回导出文件的绝对路径和简短摘要。

更多用法：

```text
$export list recent Codex sessions
$export export session <session-id> to Markdown
$export export this session with tool logs
```

安装完成后不需要再运行任何额外 shell 命令。

## 为什么需要它

导出会话的价值在于，你可以把完整交互过程交给另一个模型复盘，分析自己和模型在协作中反复出现的问题，再把这些经验沉淀成稳定的项目规则，例如 `AGENTS.md`。

默认导出 Markdown，是因为 LLM 的输入输出本身就大量使用 Markdown。导出的内容既适合人阅读、归档和 diff，也适合再次交给模型做分析。

## 功能特性

- **一条命令安装**：通过 `npx skills add` 安装为 Codex Skill。
- **对话内直接使用**：安装后在 Codex 中直接调用 `$export`。
- **Markdown 优先**：输出干净的 Markdown 转录稿，便于人和 LLM 阅读。
- **优先导出当前会话**：可用时优先选择当前 Codex conversation。
- **工作区感知回退**：当前会话 id 不可用时，回退到当前工作区最近会话，再回退到全局最近会话。
- **隐私友好的默认边界**：默认排除 system prompt、developer 指令、AGENTS 上下注入、环境上下文注入、reasoning 记录和工具日志。
- **默认路径脱敏**：Markdown 元数据默认只保留本地源文件 basename 和工作区目录名，除非明确要求完整源路径。
- **可选工具日志**：只有你明确要求包含 tool logs 时，才会导出工具调用和命令输出。

## 安全边界

默认导出内容包括：

- 可见的用户消息
- 可见的助手回复
- 会话元数据，例如 session id、source file、cwd、时间戳、originator 和 CLI version

本地源文件路径和 cwd 元数据默认会脱敏。导出的 Markdown 只保留 `rollout-...jsonl` 这样的文件名和工作区目录名。

默认不会导出：

- system prompt
- developer 指令
- AGENTS 或 project-doc 上下注入
- 环境上下文注入
- 加密或摘要形式的 reasoning 记录
- 工具调用和命令输出

只有你明确要求 Skill 包含 tool logs 时，工具调用和命令输出才会被导出。

如果直接调用脚本，可以使用 `--json` 获取机器可解析输出；只有在确实需要完整本地源路径时才使用 `--show-paths`。

## 会话选择

当你不指定 session id 时，Skill 会优先尝试导出当前 Codex 会话。如果当前会话 id 不可用，则回退到当前工作区最近的会话，再回退到全局最近会话。

如果要导出指定会话，可以在 Codex 中按 session id 指定：

```text
$export export session <session-id> to Markdown
```

## 路线图

长期目标是推动 Codex CLI 原生支持 `/export`，并以 Markdown 作为默认转录格式。在上游原生能力可用之前，本仓库以 Skill 的形式提供可用的过渡方案。

## 贡献

欢迎提交 Issue 和 Pull Request。请保持项目核心契约稳定：简单的 Codex Skill 使用入口、Markdown 优先输出，以及保守的隐私默认边界。

## 开源协议

本项目基于 [Apache License 2.0](LICENSE) 开源。

Copyright 2026 GaoSSR.

本项目不是 OpenAI 官方项目。
