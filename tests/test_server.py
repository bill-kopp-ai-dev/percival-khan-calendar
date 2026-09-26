"""Tests for the CLI surface of ``server.main`` (v0.4.0 docker entrypoint)."""

from __future__ import annotations

from percival_khan_calendar import __version__
from percival_khan_calendar.server import _build_parser, main


class TestVersionFlag:
    def test_version_flag_prints_semver(self, capsys):
        """``--version`` exits 0 with the package SemVer (Docker smoke check)."""
        rc = main(["--version"])
        out = capsys.readouterr().out
        assert rc == 0
        assert f"Percival Khan Calendar MCP Server version {__version__}" in out
        # The SemVer must look like x.y.z (not 'unknown' or empty).
        parts = __version__.split(".")
        assert len(parts) == 3, f"SemVer malformed: {__version__!r}"
        assert all(p.isdigit() for p in parts), f"non-numeric SemVer: {__version__!r}"

    def test_help_flag_mentions_mcp_protocol(self, capsys):
        rc = main(["--help"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Model Context Protocol" in out or "MCP" in out
        assert "--version" in out


class TestParserShape:
    def test_parser_has_version_and_help(self):
        p = _build_parser()
        # ``--version`` is store_true; just check the namespace round-trip.
        ns = p.parse_args(["--version"])
        assert ns.version is True
        ns = p.parse_args(["--help"])
        assert ns.help is True
        ns = p.parse_args([])
        assert ns.version is False
        assert ns.help is False


class TestMainReturns:
    def test_version_path_does_not_invoke_lifecycle(self, monkeypatch):
        """``--version`` must short-circuit before any I/O — the Docker
        smoke runs against an isolated ``/data`` with no khal installed."""
        from percival_khan_calendar import lifecycle, server

        called = {"setup_workspace": False}

        def boom_setup():
            called["setup_workspace"] = True
            raise AssertionError("setup_workspace must not run for --version")

        monkeypatch.setattr(server, "setup_workspace", boom_setup)
        monkeypatch.setattr(lifecycle, "setup_workspace", boom_setup)
        rc = server.main(["--version"])
        assert rc == 0
        assert called["setup_workspace"] is False
