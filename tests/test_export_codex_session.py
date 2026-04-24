from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "export" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import export_codex_session as exporter  # noqa: E402


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")


class ExportCodexSessionTest(unittest.TestCase):
    def test_extracts_visible_user_and_assistant_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "rollout-2026-04-24T10-00-00-019dbd51-d1c6-7943-a58a-9fa11f102ea8.jsonl"
            write_jsonl(
                session_file,
                [
                    {
                        "timestamp": "2026-04-24T02:00:00Z",
                        "type": "session_meta",
                        "payload": {
                            "id": "019dbd51-d1c6-7943-a58a-9fa11f102ea8",
                            "cwd": "/repo",
                            "timestamp": "2026-04-24T02:00:00Z",
                            "cli_version": "0.124.0",
                        },
                    },
                    {
                        "timestamp": "2026-04-24T02:00:01Z",
                        "type": "event_msg",
                        "payload": {"type": "user_message", "message": "export this session"},
                    },
                    {
                        "timestamp": "2026-04-24T02:00:02Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "phase": "final_answer",
                            "content": [{"type": "output_text", "text": "done"}],
                        },
                    },
                ],
            )

            transcript = exporter.read_transcript(session_file, include_tools=False)
            markdown = exporter.render_markdown(transcript, selected_by="test", include_tools=False)

        self.assertIn("### User", markdown)
        self.assertIn("export this session", markdown)
        self.assertIn("### Assistant (final_answer)", markdown)
        self.assertIn("done", markdown)

    def test_skips_developer_context_and_encrypted_reasoning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "rollout-2026-04-24T10-00-00-019dbd51-d1c6-7943-a58a-9fa11f102ea8.jsonl"
            write_jsonl(
                session_file,
                [
                    {
                        "timestamp": "2026-04-24T02:00:00Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "developer",
                            "content": [{"type": "input_text", "text": "secret developer instruction"}],
                        },
                    },
                    {
                        "timestamp": "2026-04-24T02:00:01Z",
                        "type": "response_item",
                        "payload": {"type": "reasoning", "encrypted_content": "ciphertext"},
                    },
                    {
                        "timestamp": "2026-04-24T02:00:02Z",
                        "type": "event_msg",
                        "payload": {"type": "user_message", "message": "visible request"},
                    },
                ],
            )

            transcript = exporter.read_transcript(session_file, include_tools=False)
            markdown = exporter.render_markdown(transcript, selected_by="test", include_tools=False)

        self.assertIn("visible request", markdown)
        self.assertNotIn("secret developer instruction", markdown)
        self.assertNotIn("ciphertext", markdown)

    def test_selects_latest_matching_cwd_before_global_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / ".codex"
            matching = codex_home / "sessions/2026/04/24/rollout-2026-04-24T10-00-00-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jsonl"
            other = codex_home / "sessions/2026/04/24/rollout-2026-04-24T11-00-00-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb.jsonl"
            write_jsonl(matching, [{"type": "session_meta", "payload": {"id": "match", "cwd": "/repo"}}])
            write_jsonl(other, [{"type": "session_meta", "payload": {"id": "other", "cwd": "/elsewhere"}}])
            os.utime(matching, (100, 100))
            os.utime(other, (200, 200))

            summary, selected_by = exporter.select_session(
                codex_home=codex_home,
                session_id=None,
                session_file=None,
                cwd="/repo",
                all_cwds=False,
            )

        self.assertEqual("match", summary.session_id)
        self.assertEqual("latest session matching cwd", selected_by)

    def test_prefers_codex_thread_id_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / ".codex"
            current = codex_home / "sessions/2026/04/24/rollout-2026-04-24T10-00-00-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jsonl"
            newer_same_cwd = codex_home / "sessions/2026/04/24/rollout-2026-04-24T11-00-00-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb.jsonl"
            write_jsonl(current, [{"type": "session_meta", "payload": {"id": "current-thread", "cwd": "/repo"}}])
            write_jsonl(newer_same_cwd, [{"type": "session_meta", "payload": {"id": "newer-thread", "cwd": "/repo"}}])
            os.utime(current, (100, 100))
            os.utime(newer_same_cwd, (200, 200))

            previous = os.environ.get("CODEX_THREAD_ID")
            os.environ["CODEX_THREAD_ID"] = "current-thread"
            try:
                summary, selected_by = exporter.select_session(
                    codex_home=codex_home,
                    session_id=None,
                    session_file=None,
                    cwd="/repo",
                    all_cwds=False,
                )
            finally:
                if previous is None:
                    os.environ.pop("CODEX_THREAD_ID", None)
                else:
                    os.environ["CODEX_THREAD_ID"] = previous

        self.assertEqual("current-thread", summary.session_id)
        self.assertEqual("explicit session id", selected_by)

    def test_tool_output_fence_expands_for_nested_backticks(self) -> None:
        transcript = exporter.Transcript(
            source_file=Path("/tmp/session.jsonl"),
            session_id="session",
            cwd="/repo",
            created_at="2026-04-24T02:00:00Z",
            cli_version="0.124.0",
            originator="Codex",
            events=[
                exporter.TranscriptEvent(
                    role="tool-output",
                    name="call_1",
                    content="content with ``` fenced code",
                    language="text",
                )
            ],
        )

        markdown = exporter.render_markdown(transcript, selected_by="test", include_tools=True)

        self.assertIn("````text", markdown)
        self.assertIn("content with ``` fenced code", markdown)

    def test_response_item_user_fallback_preserves_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "rollout-2026-04-24T10-00-00-019dbd51-d1c6-7943-a58a-9fa11f102ea8.jsonl"
            write_jsonl(
                session_file,
                [
                    {
                        "timestamp": "2026-04-24T02:00:01Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "first visible user"}],
                        },
                    },
                    {
                        "timestamp": "2026-04-24T02:00:02Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "then assistant"}],
                        },
                    },
                ],
            )

            transcript = exporter.read_transcript(session_file, include_tools=False)

        self.assertEqual(["user", "assistant"], [event.role for event in transcript.events])
        self.assertEqual("first visible user", transcript.events[0].content)
        self.assertEqual("then assistant", transcript.events[1].content)

    def test_skips_context_injected_event_user_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "rollout-2026-04-24T10-00-00-019dbd51-d1c6-7943-a58a-9fa11f102ea8.jsonl"
            write_jsonl(
                session_file,
                [
                    {
                        "timestamp": "2026-04-24T02:00:00Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "user_message",
                            "message": "# AGENTS.md instructions\n\n<INSTRUCTIONS>\nsecret project rules\n</INSTRUCTIONS>",
                        },
                    },
                    {
                        "timestamp": "2026-04-24T02:00:01Z",
                        "type": "event_msg",
                        "payload": {"type": "user_message", "message": "visible user request"},
                    },
                ],
            )

            transcript = exporter.read_transcript(session_file, include_tools=False)
            markdown = exporter.render_markdown(transcript, selected_by="test", include_tools=False)

        self.assertIn("visible user request", markdown)
        self.assertNotIn("secret project rules", markdown)

    def test_preserves_literal_agents_mention_in_normal_user_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "rollout-2026-04-24T10-00-00-019dbd51-d1c6-7943-a58a-9fa11f102ea8.jsonl"
            write_jsonl(
                session_file,
                [
                    {
                        "timestamp": "2026-04-24T02:00:00Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "user_message",
                            "message": "Please review whether AGENTS.md should mention exports.",
                        },
                    },
                ],
            )

            transcript = exporter.read_transcript(session_file, include_tools=False)
            markdown = exporter.render_markdown(transcript, selected_by="test", include_tools=False)

        self.assertIn("Please review whether AGENTS.md should mention exports.", markdown)


if __name__ == "__main__":
    unittest.main()
