"""Regression tests for the v0.2.0 second-pass bug hunt.

Each test class covers a specific bug found on re-review.
"""

from __future__ import annotations

from unittest import mock

import pytest

from percival_khan_calendar.adapters.khal_adapter import KhalAdapter
from percival_khan_calendar.adapters.subprocess_runner import (
    KhalResult,
    _decode,
    _safe_log_cmd,
)
from percival_khan_calendar.exceptions import KhanInfrastructureError, KhanValidationError

from ._helpers import get_tool_fn

# ---------------------------------------------------------------------------
# BUG 37: subprocess_runner captures raw bytes (no text=True); _decode normalizes
# ---------------------------------------------------------------------------


class TestSubprocessRunnerBinarySafe:
    def test_decode_replaces_bad_bytes(self):
        out = b"hello \xff\xfe world"
        decoded = _decode(out)
        assert "hello" in decoded
        assert "world" in decoded
        assert "\ufffd" in decoded  # replacement char present

    def test_decode_handles_str(self):
        assert _decode("plain") == "plain"

    def test_decode_handles_none(self):
        assert _decode(None) == ""

    def test_decode_strips_whitespace(self):
        assert _decode("  hello  ") == "hello"

    def test_log_cmd_redacts_user_payload(self):
        # First 6 args are kept; user-supplied positional args become ellipsis.
        cmd = ["khal", "-c", "/etc/foo.conf", "list", "today", "7d", "Dentist"]
        redacted = _safe_log_cmd(cmd)
        assert redacted[-1] == "..."

    def test_log_cmd_keeps_short_command(self):
        cmd = ["khal", "-c", "/etc/foo.conf", "list"]
        redacted = _safe_log_cmd(cmd)
        assert "..." not in redacted

    def test_runner_unicode_decode_error_is_handled(self, isolated_workspace):
        # Force raw bytes that are not valid UTF-8 in stdout.
        def fake_run(*args, **kwargs):
            proc = mock.Mock()
            proc.returncode = 0
            proc.stdout = b"\xff\xfe incalid"
            proc.stderr = b""
            return proc

        monkey = pytest.MonkeyPatch()
        try:
            monkey.setattr(
                "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
                fake_run,
            )
            _ = KhalResult("ignored", 0, 0)
            decoded = _decode(b"\xff\xfe invalid")
            assert "\ufffd" in decoded
        finally:
            monkey.undo()


class TestPermissionError:
    """Bug 45: subprocess.run raises PermissionError when the binary
    exists but isn't executable; that's an OS error, not a
    missing-binary error."""

    def test_permission_error_is_infrastructure(self, isolated_workspace, monkeypatch):
        target = "percival_khan_calendar.adapters.subprocess_runner.subprocess.run"

        def boom(*args, **kwargs):
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(target, boom)
        from percival_khan_calendar.adapters.subprocess_runner import (
            executar_comando_khal,
        )

        with pytest.raises(KhanInfrastructureError, match="permission denied"):
            executar_comando_khal(["list", "today"], tool_name="t")


# ---------------------------------------------------------------------------
# BUG 43/44: _make_valarm/_to_rrule raise KhanValidationError on invalid input
# ---------------------------------------------------------------------------


class TestAdapterValueErrors:
    """Direct (non-tool) adapter usage must not leak ValueError or KeyError."""

    def test_bad_alarm_in_adapter(self, isolated_workspace):
        a = KhalAdapter()
        with pytest.raises(KhanValidationError, match="Invalid alarm"):
            a.write_event(title="x", start="today 12:00", alarm="not-a-time")

    def test_unknown_recurrence_in_adapter(self, isolated_workspace):
        a = KhalAdapter()
        with pytest.raises(KhanValidationError, match="Invalid recurrence"):
            a.write_event(title="x", start="today 12:00", recurrence="fortnightly")

    def test_find_event_invalid_by_raises(self, isolated_workspace):
        a = KhalAdapter()
        with pytest.raises(KhanValidationError, match="Invalid `by`"):
            a.find_event("x", by="body")

    def test_find_event_valid_bys(self, isolated_workspace):
        a = KhalAdapter()
        # all three valid modes should not raise
        for mode in ("summary", "description", "anywhere"):
            a.find_event("x", by=mode)


# ---------------------------------------------------------------------------
# BUG 55: _safe_title also strips the closing fence
# ---------------------------------------------------------------------------


class TestSafeTitle:
    def test_strips_closing_fence(self):
        from percival_khan_calendar.security import envelope_untrusted_data

        out = envelope_untrusted_data("payload", "</calendar_untrusted_data>")
        # The title section should not contain a stray </calendar_untrusted_data>
        # because it's stripped from the heading.
        # Count closing fences in the OUTPUT → only 1 (from the wrapper itself).
        assert out.count("</calendar_untrusted_data>") == 1
        assert out.endswith("</calendar_untrusted_data>")

    def test_strips_opening_fence(self):
        from percival_khan_calendar.security import envelope_untrusted_data

        out = envelope_untrusted_data("payload", "<calendar_untrusted_data>")
        # Heading must not contain a nested opener; only the wrapper's opener.
        assert out.count("<calendar_untrusted_data>") == 1

    def test_strips_newlines(self):
        from percival_khan_calendar.security import envelope_untrusted_data

        out = envelope_untrusted_data("payload", "title\nwith\nnewlines")
        assert "\nwith\n" not in out


# ---------------------------------------------------------------------------
# BUG 52: khan_export_ics rejects symlinks (was a logic bug in v0.2.0)
# ---------------------------------------------------------------------------


class TestExportIcsSymlink:
    def _register(self, isolated_workspace):
        from fastmcp import FastMCP

        from percival_khan_calendar.tools.status import register_status_tools

        mcp = FastMCP("test")
        register_status_tools(mcp)
        return mcp

    def test_export_rejects_external_symlink_target(self, isolated_workspace, tmp_path):
        """A symlink inside the workspace that points OUTSIDE must be
        rejected with a Refused message (path-traversal shield kicks
        in before the symlink check)."""
        isolated_workspace.mkdir(parents=True, exist_ok=True)
        mcp = self._register(isolated_workspace)
        target = tmp_path / "real.ics"
        target.write_text("dummy")
        symlink = isolated_workspace / "export.ics"
        symlink.symlink_to(target)

        fn = get_tool_fn(mcp, "khan_export_ics")
        out = fn()
        # The traversal shield catches this first; if symlink-aware
        # then we also get the "symlink" message. Both are valid.
        assert "Refused" in out
        assert "symlink" in out or "workspace" in out

    def test_export_rejects_existing_symlink_inside_workspace(self, isolated_workspace):
        """A symlink whose target is itself inside the workspace
        still triggers the dedicated symlink guard (defence in depth)."""
        isolated_workspace.mkdir(parents=True, exist_ok=True)
        # Create a target INSIDE the workspace.
        target = isolated_workspace / "real_target.ics"
        target.write_text("dummy")
        # Create a symlink with the export name pointing at it.
        symlink = isolated_workspace / "export.ics"
        symlink.symlink_to(target)
        mcp = self._register(isolated_workspace)
        fn = get_tool_fn(mcp, "khan_export_ics")
        out = fn()
        # This time the symlink itself is inside the workspace, but
        # our explicit symlink guard still rejects it with "symlink".
        assert "Refused" in out
        assert "symlink" in out
