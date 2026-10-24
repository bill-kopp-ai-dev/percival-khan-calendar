"""Protocol-level tests: real MCP stdio client against the real server.

Why this file exists
--------------------
The rest of the suite calls the Python function *behind* each tool
(``tests/_helpers.py`` → ``FastMCP.get_tool(name).fn``). That bypasses
the wire entirely: no ``initialize`` handshake, no JSON-RPC framing,
no ``tools/list``, no ``tools/call``. A defect in the transport, in
the framing, or in the server's request dispatch could therefore pass
the whole suite green while every real agent failed to use the server.

That gap was live: the F4/F5 closure recorded the Khan server as
"not returning the JSON-RPC frame on ``tools/call``" and fell back to
filesystem/stderr evidence. The report blamed the FastMCP version, but
the real cause was the harness: it piped the requests into
``subprocess.run(input=...)``, which closes stdin the instant the
payload is written. The MCP SDK cancels in-flight handlers when the
transport closes, so the response frame was dropped *before* it could
be written — a harness race, not a server bug.

These tests drive the server over stdio with the SDK's own client
(``mcp.ClientSession`` + ``mcp.client.stdio.stdio_client``), so the
evidence lives in the protocol: ``initialize`` → ``initialized`` →
``tools/list`` → ``tools/call``. Each server gets its own temporary
workspace via ``KHAN_WORKSPACE_DIR``, so the real calendar is never
touched.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

# The twelve tools that make up the stable MCP contract surface.
EXPECTED_TOOLS = {
    "khan_list_events",
    "khan_search_events",
    "khan_get_event",
    "khan_view_agenda",
    "khan_view_calendar",
    "khan_list_calendars",
    "khan_get_status",
    "khan_create_event",
    "khan_update_event",
    "khan_delete_event",
    "khan_delete_event_safe",
    "khan_export_ics",
}


def _khal_available() -> bool:
    """Return True when a ``khal`` binary can be located.

    The CLI-backed tools (``khan_list_events`` and friends) shell out to
    ``khal``; the adapter-only tools do not. We detect the binary the
    same way ``adapters/subprocess_runner._locate_khal`` does — next
    to the running interpreter — so the suite behaves the same in CI
    and on a developer host.
    """
    if shutil.which("khal") is not None:
        return True
    sibling = Path(sys.executable).parent / "khal"
    if sibling.exists():
        return True
    for ancestor in (Path(sys.executable).parent, *Path(sys.executable).parents):
        candidate = ancestor / "bin" / "khal"
        if candidate.exists():
            return True
    return False


def _server_params(workspace: Path) -> StdioServerParameters:
    """Build the stdio parameters for an isolated server process.

    ``KHAN_WORKSPACE_DIR`` redirects every path the server derives
    (``DATA_DIR``, ``CONF_FILE``, ``DB_FILE``, ``LOCK_FILE``) into the
    temporary workspace, so no test can reach the production calendar
    under ``~/.nanobot/workspace/khalCalendar``.
    """
    env = dict(os.environ)
    env["KHAN_WORKSPACE_DIR"] = str(workspace)
    env["KHAN_ENABLE_LOCK"] = "false"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(SRC_DIR), env["PYTHONPATH"]] if env.get("PYTHONPATH") else [str(SRC_DIR)]
    )
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "percival_khan_calendar.server"],
        env=env,
        cwd=str(REPO_ROOT),
    )


@contextlib.asynccontextmanager
async def _session(params: StdioServerParameters) -> AsyncIterator[ClientSession]:
    """Open the stdio transport and an initialized MCP session.

    The transport stays open for the whole block — closing stdin
    cancels in-flight handlers inside the MCP SDK, which is exactly
    the race that produced the false "no JSON-RPC frame" report.
    """
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def _call(session: ClientSession, name: str, arguments: dict[str, Any]) -> str:
    """Call a tool and return its textual payload.

    Raises ``AssertionError`` when the server reports ``isError`` — a
    tool that fails inside the server must not be silently accepted.
    """
    result = await asyncio.wait_for(session.call_tool(name, arguments), timeout=60)
    assert result.isError is False, f"{name} returned isError=True: {result.content}"
    return "\n".join(getattr(block, "text", "") for block in result.content)


@pytest.fixture
def protocol_workspace(tmp_path: Path) -> Path:
    """An isolated workspace directory for the spawned server."""
    workspace = tmp_path / "khalCalendar"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def server_params(protocol_workspace: Path) -> StdioServerParameters:
    return _server_params(protocol_workspace)


class TestProtocolHandshake:
    """The MCP lifecycle must complete over the wire."""

    def test_initialize_reports_server_info(self, server_params):
        async def go():
            async with _session(server_params) as session:
                return await session.initialize()

        result = asyncio.run(go())
        assert result.serverInfo.name == "percival-khan-calendar"
        assert result.protocolVersion

    def test_tools_list_exposes_the_contract_surface(self, server_params):
        async def go():
            async with _session(server_params) as session:
                listed = await session.list_tools()
                return {tool.name for tool in listed.tools}

        assert asyncio.run(go()) == EXPECTED_TOOLS


class TestProtocolToolCalls:
    """``tools/call`` must return a frame the client can consume."""

    def test_get_status_answers_over_the_protocol(self, server_params, protocol_workspace):
        async def go():
            async with _session(server_params) as session:
                return await _call(session, "khan_get_status", {})

        text = asyncio.run(go())
        assert "Percival Khan Calendar Server operational." in text
        # The answer must describe the *isolated* workspace, proving the
        # server never fell back to the production calendar.
        assert str(protocol_workspace) in text

    @pytest.mark.skipif(not _khal_available(), reason="requires the `khal` binary")
    def test_cli_backed_tool_answers_over_the_protocol(self, server_params):
        """``khan_list_calendars`` shells out to ``khal`` and must still
        answer on the wire — this is the exact tool the F4 fixture
        exercised through a broken harness."""

        async def go():
            async with _session(server_params) as session:
                return await _call(session, "khan_list_calendars", {})

        assert "nanobot" in asyncio.run(go())

    @pytest.mark.skipif(not _khal_available(), reason="requires the `khal` binary")
    def test_write_then_read_round_trip(self, server_params):
        """A created event must be visible to a later read *through the
        protocol* — the F4 acceptance the harness could not prove."""

        async def go():
            async with _session(server_params) as session:
                created = await _call(
                    session,
                    "khan_create_event",
                    {
                        "title": "Protocol probe",
                        "start": "today 14:00",
                        "end": "today 15:00",
                        "description": "protocol round trip",
                    },
                )
                listed = await _call(session, "khan_list_events", {"start_date": "today"})
                searched = await _call(session, "khan_search_events", {"query": "Protocol probe"})
                return created, listed, searched

        created, listed, searched = asyncio.run(go())
        assert "Protocol probe" in created
        assert "Protocol probe" in listed
        assert "Protocol probe" in searched

    def test_invalid_arguments_are_reported_on_the_protocol(self, server_params):
        """A validation failure must come back as a frame, not as a
        silent hang or a dropped connection."""

        async def go():
            async with _session(server_params) as session:
                return await asyncio.wait_for(
                    session.call_tool("khan_list_events", {"calendar": "nanobot"}),
                    timeout=60,
                )

        result = asyncio.run(go())
        assert result.isError is True
        text = "\n".join(getattr(block, "text", "") for block in result.content)
        assert "unexpected_keyword_argument" in text


class TestProtocolIsolation:
    """The spawned server must never touch the production calendar."""

    def test_production_workspace_is_untouched(self, server_params, protocol_workspace):
        production = Path.home() / ".nanobot" / "workspace" / "khalCalendar"
        before = sorted(p.name for p in production.iterdir()) if production.exists() else None

        async def go():
            async with _session(server_params) as session:
                return await _call(session, "khan_get_status", {})

        asyncio.run(go())

        after = sorted(p.name for p in production.iterdir()) if production.exists() else None
        assert after == before
        assert str(protocol_workspace) != str(production)
