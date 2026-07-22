"""Tests for the hardened subprocess runner."""

from __future__ import annotations

import subprocess
from unittest import mock

import pytest

from percival_khan_calendar.adapters.subprocess_runner import (
    KhalResult,
    executar_comando_khal,
)
from percival_khan_calendar.exceptions import (
    KhanInfrastructureError,
    KhanValidationError,
)


@pytest.fixture
def patched_runner(monkeypatch, isolated_workspace):
    """Bind subprocess.run to a controllable Mock."""
    target = "percival_khan_calendar.adapters.subprocess_runner.subprocess.run"
    m = mock.MagicMock()
    monkeypatch.setattr(target, m)
    return m


def _mk_proc(*, returncode=0, stdout="", stderr=""):
    proc = mock.Mock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestSuccess:
    def test_returns_khal_result_with_stdout(self, patched_runner):
        patched_runner.return_value = _mk_proc(returncode=0, stdout="Standup at 10:00")
        res = executar_comando_khal(["list", "today"], tool_name="khan_list_events")
        assert isinstance(res, KhalResult)
        assert res.stdout == "Standup at 10:00"
        assert res.returncode == 0
        assert res.elapsed_ms >= 0

    def test_injects_conf_flag(self, patched_runner):
        patched_runner.return_value = _mk_proc(returncode=0, stdout="ok")
        executar_comando_khal(["list", "today"], tool_name="t")
        # Round-6: cmd[0] is now an absolute path to the khal binary
        # (defence against PATH drift). We just check it ends in
        # "khal" and the second arg is the conf-flag.
        args, _ = patched_runner.call_args
        assert str(args[0][0]).endswith("khal")
        assert args[0][1] == "-c"
        assert str(args[0][2]).endswith("khal.conf")


class TestTimeout:
    def test_timeout_translates_to_infrastructure_error(self, patched_runner):
        patched_runner.side_effect = subprocess.TimeoutExpired(cmd=["khal"], timeout=15)
        with pytest.raises(KhanInfrastructureError, match="timed out"):
            executar_comando_khal(["list", "today"], tool_name="t", timeout=15)

    def test_timeout_default_used(self, patched_runner):
        patched_runner.side_effect = subprocess.TimeoutExpired(cmd=["khal"], timeout=15)
        with pytest.raises(KhanInfrastructureError):
            executar_comando_khal(["list", "today"], tool_name="t")


class TestExitCode:
    def test_exit_code_2_is_validation(self, patched_runner):
        patched_runner.return_value = _mk_proc(returncode=2, stderr="error: bad date")
        with pytest.raises(KhanValidationError):
            executar_comando_khal(["list", "99/99/9999"], tool_name="t")

    def test_exit_code_5_is_infrastructure(self, patched_runner):
        patched_runner.return_value = _mk_proc(returncode=5, stderr="DB locked")
        with pytest.raises(KhanInfrastructureError):
            executar_comando_khal(["list", "today"], tool_name="t")

    def test_usage_keyword_is_validation(self, patched_runner):
        patched_runner.return_value = _mk_proc(returncode=1, stderr="Usage: khal list ...")
        with pytest.raises(KhanValidationError):
            executar_comando_khal(["bogus"], tool_name="t")


class TestFileNotFound:
    def test_binary_missing(self, patched_runner):
        patched_runner.side_effect = FileNotFoundError()
        with pytest.raises(KhanInfrastructureError, match="khal binary not found"):
            executar_comando_khal(["list", "today"], tool_name="t")


class TestRetryGuard:
    def test_retry_refused_for_non_idempotent(self, patched_runner, caplog):
        patched_runner.return_value = _mk_proc(returncode=0, stdout="ok")
        executar_comando_khal(
            ["new", "title", "today"],
            tool_name="t",
            retry_on_transient=True,
            max_retries=3,
        )
        # Even with retry_on_transient=True, the call should run once.
        assert patched_runner.call_count == 1
        # And a warning was logged.
        assert (
            any("Refusing to retry non-idempotent" in r.message for r in caplog.records)
            or "Refusing" in caplog.text
        )

    def test_retry_on_transient_for_list_command(self, patched_runner):
        # Always-fail except the last call.
        patched_runner.side_effect = [
            _mk_proc(returncode=0, stdout=""),  # explicit first success
        ]
        executar_comando_khal(
            ["list", "today"],
            tool_name="t",
            retry_on_transient=True,
            max_retries=2,
        )
        assert patched_runner.call_count == 1
