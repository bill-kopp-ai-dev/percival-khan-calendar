"""Regression tests for the MCP ``prompts.primitives`` and ``resources``.

Each prompt in ``tools/prompts.py`` is registered against a fresh
``FastMCP`` instance so we can verify:
  1. it appears in ``list_prompts()``;
  2. it renders without errors via ``render_prompt``;
  3. the rendered text carries the expected substrings (workflow,
     invariants, examples);
  4. parametrized prompts enforce their argument shape.

The single resource at ``khan://schema/main`` is checked for MIME
type, URI, and the absence of placeholder text.
"""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import FastMCP

from percival_khan_calendar.resources import register_resources
from percival_khan_calendar.resources.docs import SCHEMA_URI
from percival_khan_calendar.tools.prompts import register_prompts


@pytest.fixture
def mcp_app():
    """Fresh FastMCP app with prompts + resources registered.

    Pinning a single shared instance keeps the prompt registry
    clean across tests and avoids the FastMCP duplicate-name
    guard.
    """
    app = FastMCP("test-khan-prompts")
    register_prompts(app)
    register_resources(app)
    return app


# ---------------------------------------------------------------------------
# prompt rendering — happy paths for all 6 prompts
# ---------------------------------------------------------------------------


class TestPromptRegistration:
    @pytest.mark.parametrize(
        "prompt_name",
        [
            "khan_overview",
            "khan_create_event_semantics",
            "khan_update_workflow",
            "khan_delete_with_confirmation",
            "khan_search_strategy",
            "khan_quick_action_quick_create",
        ],
    )
    def test_prompt_in_list(self, mcp_app, prompt_name):
        async def go():
            return await mcp_app.list_prompts()

        prompts = asyncio.run(go())
        names = {p.name for p in prompts}
        assert prompt_name in names, f"Prompt {prompt_name!r} not registered. Got: {sorted(names)}"


class TestPromptRender:
    """Each prompt renders cleanly with the documented arguments."""

    def test_khan_overview_has_invariants_and_workflow(self, mcp_app):
        async def go():
            return await mcp_app.render_prompt("khan_overview", {})

        result = asyncio.run(go())
        assert len(result.messages) >= 1
        body = result.messages[0].content.text
        assert "Recommended workflow" in body
        # Cross-check a few key workflow steps appear.
        for step in (
            "khan_get_status",
            "khan_list_events",
            "khan_view_agenda",
            "khan_create_event",
            "khan_delete_event_safe",
            "khan_export_ics",
        ):
            assert step in body, f"Workflow step {step!r} missing in khan_overview"
        # The invariants block should be shared across prompts.
        assert "Invariantes não-negociáveis" in body

    def test_khan_create_event_semantics_documents_field_shape(self, mcp_app):
        async def go():
            return await mcp_app.render_prompt("khan_create_event_semantics", {})

        body = asyncio.run(go()).messages[0].content.text
        assert "TIME-EXPRESSIONS" in body
        assert "ALARM FORMAT" in body
        assert "RECURRENCE" in body
        # When the user says "tomorrow at 10:00" the prompt must
        # spell out the exact call.
        assert "khan_create_event(" in body
        assert 'start="tomorrow 10:00"' in body

    def test_khan_update_workflow_warns_about_ambiguous_match(self, mcp_app):
        async def go():
            return await mcp_app.render_prompt("khan_update_workflow", {})

        body = asyncio.run(go()).messages[0].content.text
        # The prompt must mention UID preservation and the
        # ambiguity-raise behaviour.
        assert "UID" in body
        assert "KhanAmbiguousMatchError" in body

    def test_khan_delete_with_confirmation_enforces_dry_run(self, mcp_app):
        async def go():
            return await mcp_app.render_prompt("khan_delete_with_confirmation", {})

        body = asyncio.run(go()).messages[0].content.text
        # Two-call protocol must be present.
        assert "confirm=False" in body
        assert "confirm=True" in body
        assert "DRY-RUN" in body

    def test_khan_search_strategy_accepts_scope_literal(self, mcp_app):
        """The ``scope`` parameter is a Literal[summary, location,
        description]. FastMCP generates a JSON Schema with an
        ``enum`` that matches. We render with each valid value and
        confirm the body mentions the chosen scope."""

        async def render(scope):
            return await mcp_app.render_prompt(
                "khan_search_strategy",
                {"keyword": "team", "scope": scope},
            )

        for scope in ("summary", "location", "description"):
            body = asyncio.run(render(scope)).messages[0].content.text
            # The closing paragraph of the prompt template uses
            # ``Scope: ``<scope>```` (double-backticks) to announce
            # which scope the agent is searching in.
            assert f"Scope: ``{scope}``" in body, (
                f"scope {scope!r} not echoed; got body={body[-200:]!r}"
            )
            # The user-supplied keyword should be echoed back.
            assert "team" in body

    def test_khan_quick_action_quick_create_inlines_user_intent(self, mcp_app):
        async def go():
            return await mcp_app.render_prompt(
                "khan_quick_action_quick_create",
                {"user_intent": "reuniao 3a 14h"},
            )

        body = asyncio.run(go()).messages[0].content.text
        # Verbatim echo + mapping instructions.
        assert "reuniao 3a 14h" in body
        assert "khan_create_event(" in body
        # Portuguese helpers.
        assert "Resolução rápida" in body

    def test_prompt_body_does_not_leak_internal_path(self, mcp_app):
        """The prompts should never include the user's workspace
        directory or any absolute path. Defensive check."""

        async def render(name):
            return await mcp_app.render_prompt(name, {})

        for name in (
            "khan_overview",
            "khan_create_event_semantics",
            "khan_update_workflow",
            "khan_delete_with_confirmation",
        ):
            body = asyncio.run(render(name)).messages[0].content.text
            for forbidden in (
                "/tmp/",
                "/home/",
                "/Users/",
                "WORKSPACE_DIR",
            ):
                assert forbidden not in body, (
                    f"Prompt {name!r} leaks {forbidden!r}: {body[:200]!r}…"
                )


# ---------------------------------------------------------------------------
# resource at khan://schema/main
# ---------------------------------------------------------------------------


class TestSchemaResource:
    def test_resource_listed(self, mcp_app):
        async def go():
            return await mcp_app.list_resources()

        resources = asyncio.run(go())
        uris = {str(r.uri) for r in resources}
        assert str(SCHEMA_URI) in uris

    def test_resource_readable(self, mcp_app):
        async def go():
            return await mcp_app.read_resource(str(SCHEMA_URI))

        result = asyncio.run(go())
        # FastMCP returns a wrapper with ``contents`` list.
        contents = getattr(result, "contents", None) or result
        # Each item has a ``text`` attribute.
        assert contents, f"empty contents from {SCHEMA_URI}"
        first = contents[0]
        text = getattr(first, "text", str(first))
        assert isinstance(text, str) and len(text) > 100
        # Sections we promised to ship.
        assert "Storage layout" in text
        assert "khal.conf" in text
        assert "Datetime and timezone" in text
        assert "Error taxonomy" in text
        assert "KhanInfrastructureError" in text
        assert "Where things live" in text

    def test_resource_mime_is_markdown(self, mcp_app):
        async def go():
            return await mcp_app.list_resources()

        resources = asyncio.run(go())
        for r in resources:
            if str(r.uri) == str(SCHEMA_URI):
                # FastMCP 3 returns ``mime_type`` (snake) but the
                # protocol uses ``mimeType``. Accept either form.
                mt = getattr(r, "mime_type", None) or getattr(r, "mimeType", None)
                assert mt == "text/markdown", mt


# ---------------------------------------------------------------------------
# defense in depth: prompts are not invoked when the kwargs do not match
# ---------------------------------------------------------------------------


class TestPromptArguments:
    def test_khan_search_strategy_rejects_unknown_scope(self, mcp_app):
        """Passing an unsupported ``scope`` value should either be
        rejected or surface a clear error — never silently accept
        it as if it were valid."""
        import fastmcp.exceptions as fe

        async def go():
            return await mcp_app.render_prompt(
                "khan_search_strategy",
                {"keyword": "team", "scope": "title"},  # invalid
            )

        with pytest.raises((fe.PromptError, fe.ValidationError, ValueError, TypeError)):
            asyncio.run(go())

    def test_missing_required_argument(self, mcp_app):
        """``khan_quick_action_quick_create`` requires ``user_intent``.
        Without it, the library must raise a typed error rather
        than render an empty prompt."""
        import fastmcp.exceptions as fe

        async def go():
            return await mcp_app.render_prompt("khan_quick_action_quick_create", {})

        with pytest.raises((fe.PromptError, fe.ValidationError, TypeError)):
            asyncio.run(go())
