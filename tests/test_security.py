"""Regression tests for the bugs caught in the v0.2.0 review pass."""

from __future__ import annotations

import pytest

from percival_khan_calendar.adapters.khal_adapter import KhalAdapter
from percival_khan_calendar.adapters.subprocess_runner import (
    KhalResult,
)
from percival_khan_calendar.exceptions import KhanValidationError


class TestParseKhalTimeRaises:
    """_parse_khal_time used to silently fall back to datetime.now()."""

    def test_invalid_string_raises(self, isolated_workspace):
        a = KhalAdapter()
        with pytest.raises(KhanValidationError, match="Invalid time expression"):
            a.write_event(title="x", start="not a date at all")

    def test_injection_via_start_raises(self, isolated_workspace):
        a = KhalAdapter()
        # Pydantic already rejects leading "-"; this exercises a
        # non-arg-injection garbage value to confirm ValidationError
        # surfaces from _parse_khal_time, not silently returns now.
        with pytest.raises(KhanValidationError):
            a.write_event(title="x", start="foo bar")


class TestViewToolsAreEnveloped:
    """All tools returning calendar data must wrap in envelope_untrusted_data."""

    def test_view_agenda_enveloped(self, view_app_for_review, monkeypatch, isolated_workspace):
        from ._helpers import get_tool_fn

        monkeypatch.setattr(
            "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
            lambda *a, **kw: KhalResult(stdout="10:00 Standup", returncode=0, elapsed_ms=1),
        )
        fn = get_tool_fn(view_app_for_review, "khan_view_agenda")
        out = fn(period="7d")
        assert "<calendar_untrusted_data>" in out
        assert "Standup" in out

    def test_view_calendar_enveloped(self, view_app_for_review, monkeypatch, isolated_workspace):
        from ._helpers import get_tool_fn

        monkeypatch.setattr(
            "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
            lambda *a, **kw: KhalResult(stdout="Mo Tu We", returncode=0, elapsed_ms=1),
        )
        fn = get_tool_fn(view_app_for_review, "khan_view_calendar")
        out = fn()
        assert "<calendar_untrusted_data>" in out
        assert "Mo Tu We" in out


class TestAdapterDataDir:
    """BUG 27: _persist_event used constants.DATA_DIR, ignoring
    the adapter's data_dir constructor argument."""

    def test_uses_custom_data_dir(self, tmp_path, isolated_workspace):
        custom = tmp_path / "custom_calendar"
        a = KhalAdapter(data_dir=custom)
        m = a.write_event(title="X", start="today 12:00")
        assert custom in m.filepath.parents


class TestDeleteEventSafeAtomic:
    """BUG 4: khan_delete_event_safe(confirm=True) used to do
    find-then-delete in separate operations; the lock now wraps both.

    Note: the workspace lock is a no-op when ENABLE_LOCK=false (the
    test default), so here we just verify that the new method exists
    and preserves the right semantics: with confirm=False it returns
    'DRY-RUN' and the file is still on disk; with confirm=True it
    returns 'DELETED <uid>' and the file is gone.
    """

    def test_dry_run_does_not_delete(self, isolated_workspace):
        a = KhalAdapter()
        a.write_event(title="LockMe", start="today 12:00")
        out = a.delete_event_safe("LockMe", confirm=False)
        assert "DRY-RUN" in out
        assert a.find_event("LockMe")

    def test_confirm_true_deletes(self, isolated_workspace):
        a = KhalAdapter()
        a.write_event(title="LockMe", start="today 12:00")
        out = a.delete_event_safe("LockMe", confirm=True)
        assert "DELETED" in out
        import pytest

        from percival_khan_calendar.exceptions import KhanNotFoundError

        with pytest.raises(KhanNotFoundError):
            a.find_event_unique("LockMe")


class TestExportIcsSanitizesErrors:
    """BUG 18: status.py used to leak internal exception messages
    to the agent (which can include absolute paths, stack frames)."""

    def test_export_error_returns_class_only(
        self, status_app_for_review, monkeypatch, isolated_workspace
    ):
        # Force a TypeError inside the export by patching the
        # Calendar constructor. The icalendar module is imported
        # lazily inside export_ics, so we patch the symbol in the
        # icalendar module namespace (not tools.status).
        from icalendar import Calendar as RealCal

        from ._helpers import get_tool_fn

        def boom(*a, **kw):
            raise TypeError("internal: /tmp/secret/key leaked path")

        monkeypatch.setattr(RealCal, "add", boom)
        fn = get_tool_fn(status_app_for_review, "khan_export_ics")
        out = fn()
        assert "/tmp/secret" not in out, "Path must not leak"
        assert "TypeError" in out

    def test_export_rejects_path_traversal(self, status_app_for_review, isolated_workspace):
        from ._helpers import get_tool_fn

        fn = get_tool_fn(status_app_for_review, "khan_export_ics")
        out = fn(output_path="/etc/passwd")
        assert "Refused" in out


@pytest.fixture
def view_app_for_review(isolated_workspace):
    from fastmcp import FastMCP

    from percival_khan_calendar.tools.view import register_view_tools

    mcp = FastMCP("test")
    register_view_tools(mcp)
    return mcp


@pytest.fixture
def status_app_for_review(isolated_workspace):
    from fastmcp import FastMCP

    from percival_khan_calendar.tools.status import register_status_tools

    mcp = FastMCP("test")
    register_status_tools(mcp)
    return mcp
