#!/usr/bin/env python3
"""Export Codex session JSONL files to Markdown."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@dataclass(frozen=True)
class SessionSummary:
    path: Path
    session_id: str
    cwd: str | None
    created_at: str | None
    updated_at: float
    line_count: int


@dataclass
class TranscriptEvent:
    role: str
    content: str
    timestamp: str | None = None
    phase: str | None = None
    name: str | None = None
    language: str | None = None


@dataclass
class Transcript:
    source_file: Path
    session_id: str
    cwd: str | None
    created_at: str | None
    cli_version: str | None
    originator: str | None
    events: list[TranscriptEvent] = field(default_factory=list)
    skipped_json_lines: int = 0


def resolve_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


def iter_session_files(codex_home: Path) -> Iterable[Path]:
    sessions_dir = codex_home / "sessions"
    archived_dir = codex_home / "archived_sessions"

    if sessions_dir.exists():
        yield from sessions_dir.rglob("*.jsonl")
    if archived_dir.exists():
        yield from archived_dir.glob("*.jsonl")


def parse_json_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def extract_session_id_from_path(path: Path) -> str:
    match = UUID_RE.search(path.name)
    if match:
        return match.group(0)
    return path.stem


def read_session_summary(path: Path) -> SessionSummary:
    session_id = extract_session_id_from_path(path)
    cwd: str | None = None
    created_at: str | None = None
    line_count = 0

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line_count += 1
            record = parse_json_line(line)
            if not record:
                continue

            record_type = record.get("type")
            payload = record.get("payload")
            if not isinstance(payload, dict):
                payload = {}

            if record_type == "session_meta":
                session_id = str(payload.get("id") or session_id)
                cwd = str(payload.get("cwd") or cwd) if payload.get("cwd") else cwd
                created_at = str(payload.get("timestamp") or record.get("timestamp") or created_at)
            elif record_type == "turn_context":
                cwd = str(payload.get("cwd") or cwd) if payload.get("cwd") else cwd

    return SessionSummary(
        path=path,
        session_id=session_id,
        cwd=cwd,
        created_at=created_at,
        updated_at=path.stat().st_mtime,
        line_count=line_count,
    )


def load_summaries(codex_home: Path) -> list[SessionSummary]:
    summaries: list[SessionSummary] = []
    for path in iter_session_files(codex_home):
        try:
            summaries.append(read_session_summary(path))
        except OSError:
            continue
    summaries.sort(key=lambda item: item.updated_at, reverse=True)
    return summaries


def normalize_path(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve())


def select_session(
    *,
    codex_home: Path,
    session_id: str | None,
    session_file: str | None,
    cwd: str,
    all_cwds: bool,
) -> tuple[SessionSummary, str]:
    if session_file:
        path = Path(session_file).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Session file not found: {path}")
        return read_session_summary(path), "explicit session file"

    env_session_file = os.environ.get("CODEX_SESSION_FILE")
    if env_session_file and not session_id:
        path = Path(env_session_file).expanduser().resolve()
        if path.exists():
            return read_session_summary(path), "CODEX_SESSION_FILE"

    explicit_session_id = session_id
    env_session_id = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    if env_session_id and not explicit_session_id:
        session_id = env_session_id

    summaries = load_summaries(codex_home)
    if not summaries:
        raise FileNotFoundError(f"No Codex session JSONL files found under {codex_home}")

    if session_id:
        for summary in summaries:
            if summary.session_id == session_id or session_id in summary.path.name:
                return summary, "explicit session id"
        if explicit_session_id:
            raise FileNotFoundError(f"No Codex session found for id: {session_id}")

    if not all_cwds:
        wanted_cwd = normalize_path(cwd)
        for summary in summaries:
            if summary.cwd and normalize_path(summary.cwd) == wanted_cwd:
                return summary, "latest session matching cwd"

    return summaries[0], "latest session globally"


def text_from_content_items(items: Any, wanted_types: set[str]) -> str:
    if isinstance(items, str):
        return items
    if not isinstance(items, list):
        return ""

    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type in wanted_types and isinstance(item.get("text"), str):
            parts.append(item["text"])
        elif isinstance(item.get("text"), str) and not item_type:
            parts.append(item["text"])
    return "\n".join(part for part in parts if part)


def looks_like_context_injection(text: str) -> bool:
    stripped = text.lstrip()
    markers = (
        "# AGENTS.md instructions",
        "<INSTRUCTIONS>",
        "<environment_context>",
        "<permissions instructions>",
        "# Global Coding Rules",
    )
    return any(marker in stripped[:2000] for marker in markers)


def pretty_json_string(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    return json.dumps(parsed, ensure_ascii=False, indent=2)


def read_transcript(path: Path, *, include_tools: bool) -> Transcript:
    session_id = extract_session_id_from_path(path)
    transcript = Transcript(
        source_file=path,
        session_id=session_id,
        cwd=None,
        created_at=None,
        cli_version=None,
        originator=None,
    )
    collected_events: list[tuple[str, TranscriptEvent]] = []
    has_event_user_messages = False

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = parse_json_line(line)
            if record is None:
                if line.strip():
                    transcript.skipped_json_lines += 1
                continue

            record_type = record.get("type")
            timestamp = record.get("timestamp")
            payload = record.get("payload")
            if not isinstance(payload, dict):
                payload = {}

            if record_type == "session_meta":
                transcript.session_id = str(payload.get("id") or transcript.session_id)
                transcript.cwd = str(payload.get("cwd") or transcript.cwd) if payload.get("cwd") else transcript.cwd
                transcript.created_at = str(payload.get("timestamp") or timestamp or transcript.created_at)
                transcript.cli_version = str(payload.get("cli_version") or "") or transcript.cli_version
                transcript.originator = str(payload.get("originator") or "") or transcript.originator
                continue

            if record_type == "turn_context":
                transcript.cwd = str(payload.get("cwd") or transcript.cwd) if payload.get("cwd") else transcript.cwd
                continue

            if record_type == "event_msg" and payload.get("type") == "user_message":
                content = str(payload.get("message") or "").strip()
                if content and not looks_like_context_injection(content):
                    has_event_user_messages = True
                    collected_events.append(("event-user", TranscriptEvent(role="user", content=content, timestamp=timestamp)))
                continue

            if record_type != "response_item":
                continue

            payload_type = payload.get("type")
            if payload_type == "reasoning":
                continue

            if payload_type == "message":
                role = str(payload.get("role") or "unknown")
                if role not in {"user", "assistant"}:
                    continue

                wanted = {"output_text"} if role == "assistant" else {"input_text"}
                content = text_from_content_items(payload.get("content"), wanted).strip()
                if not content:
                    continue
                if looks_like_context_injection(content):
                    continue

                event = TranscriptEvent(
                    role=role,
                    content=content,
                    timestamp=timestamp,
                    phase=payload.get("phase"),
                )
                if role == "user":
                    collected_events.append(("response-user", event))
                elif role == "assistant":
                    collected_events.append(("message", event))
                continue

            if not include_tools:
                continue

            if payload_type == "function_call":
                name = str(payload.get("name") or "unknown")
                arguments = payload.get("arguments")
                if isinstance(arguments, str):
                    content = pretty_json_string(arguments)
                else:
                    content = json.dumps(arguments, ensure_ascii=False, indent=2, default=str)
                collected_events.append(
                    (
                        "tool",
                        TranscriptEvent(
                            role="tool-call",
                            content=content,
                            timestamp=timestamp,
                            name=name,
                            language="json",
                        ),
                    )
                )
                continue

            if payload_type == "function_call_output":
                output = payload.get("output")
                content = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False, indent=2, default=str)
                collected_events.append(
                    (
                        "tool",
                        TranscriptEvent(
                            role="tool-output",
                            content=content,
                            timestamp=timestamp,
                            name=str(payload.get("call_id") or "unknown"),
                            language="text",
                        ),
                    )
                )

    if not has_event_user_messages:
        transcript.events = [event for _, event in collected_events]
    else:
        transcript.events = [event for source, event in collected_events if source != "response-user"]

    return transcript


def markdown_fence(content: str) -> str:
    longest = 0
    for match in re.finditer(r"`+", content):
        longest = max(longest, len(match.group(0)))
    return "`" * max(3, longest + 1)


def role_heading(event: TranscriptEvent) -> str:
    if event.role == "user":
        return "User"
    if event.role == "assistant":
        return f"Assistant ({event.phase})" if event.phase else "Assistant"
    if event.role == "tool-call":
        return f"Tool Call: {event.name}"
    if event.role == "tool-output":
        return f"Tool Output: {event.name}"
    return event.role.title()


def render_content(event: TranscriptEvent) -> list[str]:
    content = event.content.strip()
    if event.role in {"tool-call", "tool-output"}:
        fence = markdown_fence(content)
        language = event.language or ""
        return [f"{fence}{language}", content, fence]
    return [content]


def render_markdown(transcript: Transcript, *, selected_by: str, include_tools: bool) -> str:
    exported_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    lines: list[str] = [
        "# Codex Session Export",
        "",
        "## Metadata",
        "",
        f"- Session ID: `{transcript.session_id}`",
        f"- Source File: `{transcript.source_file}`",
        f"- Selected By: {selected_by}",
        f"- CWD: `{transcript.cwd or 'unknown'}`",
        f"- Created At: {transcript.created_at or 'unknown'}",
        f"- Exported At: {exported_at}",
        f"- Originator: {transcript.originator or 'unknown'}",
        f"- CLI Version: {transcript.cli_version or 'unknown'}",
        f"- Include Tools: {str(include_tools).lower()}",
        f"- Message Count: {len(transcript.events)}",
        "",
        "## Conversation",
        "",
    ]

    if not transcript.events:
        lines.append("No visible user or assistant messages were found.")
        return "\n".join(lines) + "\n"

    for event in transcript.events:
        lines.append(f"### {role_heading(event)}")
        lines.append("")
        if event.timestamp:
            lines.append(f"> {event.timestamp}")
            lines.append("")
        lines.extend(render_content(event))
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return cleaned or "codex-session"


def default_output_path(output_dir: Path, transcript: Transcript) -> Path:
    timestamp = transcript.created_at or dt.datetime.now().astimezone().isoformat(timespec="seconds")
    timestamp = timestamp.replace(":", "").replace("+", "-").replace("Z", "Z")
    return output_dir / f"codex-session-{safe_filename(timestamp)}-{safe_filename(transcript.session_id)}.md"


def write_export(markdown: str, *, output: str | None, output_dir: str | None, transcript: Transcript) -> Path:
    if output:
        target = Path(output).expanduser().resolve()
    else:
        base = Path(output_dir).expanduser().resolve() if output_dir else Path.cwd().resolve() / "codex-session-exports"
        target = default_output_path(base, transcript)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown, encoding="utf-8")
    return target


def list_recent_sessions(codex_home: Path, *, cwd: str, limit: int) -> int:
    summaries = load_summaries(codex_home)
    wanted_cwd = normalize_path(cwd)
    print(f"Codex home: {codex_home}")
    print(f"Current cwd: {wanted_cwd}")
    print("")
    for summary in summaries[:limit]:
        cwd_marker = "cwd-match" if summary.cwd and normalize_path(summary.cwd) == wanted_cwd else "other-cwd"
        updated = dt.datetime.fromtimestamp(summary.updated_at).astimezone().isoformat(timespec="seconds")
        print(f"{summary.session_id}  {updated}  {cwd_marker}  {summary.path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a Codex session JSONL file to Markdown.")
    parser.add_argument("--session-id", help="Export a specific Codex session id.")
    parser.add_argument("--session-file", help="Export a specific Codex JSONL file.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory used by current-session selection.")
    parser.add_argument("--all-cwds", action="store_true", help="Ignore cwd matching and select the newest session globally.")
    parser.add_argument("--output", help="Write to this exact Markdown file path.")
    parser.add_argument("--output-dir", help="Directory for generated Markdown exports.")
    parser.add_argument("--include-tools", action="store_true", help="Include tool call arguments and tool outputs.")
    parser.add_argument("--list", action="store_true", help="List recent Codex sessions instead of exporting.")
    parser.add_argument("--limit", type=int, default=20, help="Session count for --list.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    codex_home = resolve_codex_home()
    if args.list:
        return list_recent_sessions(codex_home, cwd=args.cwd, limit=args.limit)

    try:
        summary, selected_by = select_session(
            codex_home=codex_home,
            session_id=args.session_id,
            session_file=args.session_file,
            cwd=args.cwd,
            all_cwds=args.all_cwds,
        )
        transcript = read_transcript(
            summary.path,
            include_tools=args.include_tools,
        )
        markdown = render_markdown(transcript, selected_by=selected_by, include_tools=args.include_tools)
        output_path = write_export(markdown, output=args.output, output_dir=args.output_dir, transcript=transcript)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("Exported Codex session markdown")
    print(f"file: {output_path}")
    print(f"session_id: {transcript.session_id}")
    print(f"source_file: {summary.path}")
    print(f"selected_by: {selected_by}")
    print(f"message_count: {len(transcript.events)}")
    print(f"include_tools: {str(args.include_tools).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
