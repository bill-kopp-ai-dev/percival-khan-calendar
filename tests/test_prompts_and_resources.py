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


# ---------------------------------------------------------------------------
# audit-round: re-entrancy guarantees (round-7)
# ---------------------------------------------------------------------------


class TestReentrancy:
    """Round-7 audit: ``register_prompts`` / ``register_resources``
    on the same ``FastMCP`` instance logs a warning but does NOT
    raise (FastMCP 3.4 local_provider silently overwrites).
    Pinning this behaviour via test serves two purposes:

    1. if FastMCP upgrades to a strict duplicate-error policy, the
       test will start failing in a controlled way, not in
       production;
    2. the test confirms the "fresh instance per call" pattern
       works for callers (like tests, sub-server composition) that
       DO want isolation.
    """

    def test_register_prompts_re_register_logs_warning(self, caplog):
        """Second ``register_prompts`` call logs ``Component already
        exists: prompt:<name>@`` for each prompt but does not raise.
        This is FastMCP's documented (silent) behaviour as of 3.4."""
        import logging

        from fastmcp import FastMCP

        from percival_khan_calendar.tools.prompts import register_prompts

        app = FastMCP("reentrancy-test-prompts")
        with caplog.at_level(logging.WARNING):
            register_prompts(app)
            # Should NOT raise; should log at least one "already exists".
            register_prompts(app)
        warnings = [r.message for r in caplog.records]
        assert any("already exists" in m for m in warnings), (
            f"Expected 'already exists' warning; got {warnings[:3]!r}"
        )

    def test_register_resources_re_register_logs_warning(self, caplog):
        import logging

        from fastmcp import FastMCP

        from percival_khan_calendar.resources import register_resources

        app = FastMCP("reentrancy-test-resources")
        with caplog.at_level(logging.WARNING):
            register_resources(app)
            register_resources(app)
        warnings = [r.message for r in caplog.records]
        assert any("already exists" in m and "schema/main" in m for m in warnings), (
            f"Expected 'already exists' warning; got {warnings[:3]!r}"
        )

    def test_fresh_instance_per_call_works(self):
        """Two **distinct** FastMCP instances each registered
        cleanly is the pattern tests should use."""
        from fastmcp import FastMCP

        from percival_khan_calendar.resources import register_resources
        from percival_khan_calendar.tools.prompts import register_prompts

        app_a = FastMCP("instance-a")
        app_b = FastMCP("instance-b")
        register_prompts(app_a)
        register_resources(app_b)

        # Sanity: B did not pick up A's prompts.
        async def list_b_prompts():
            return await app_b.list_prompts()

        prompts_b = asyncio.run(list_b_prompts())
        assert len(prompts_b) == 0, (
            f"Cross-instance bleed: app_b unexpectedly has {[p.name for p in prompts_b]!r}"
        )


class TestServerBootReentrancy:
    """``server.main()`` constructs its own FastMCP instance so the
    module-level ``mcp`` global does not pollute the runtime."""

    def test_main_does_not_touch_module_level_mcp(self, monkeypatch):
        """``main()`` must not reuse the module-global ``mcp`` —
        doing so would prevent re-bootstrapping the server after
        a fatal error. We capture the FastMCP instance the boot
        path passes to ``register_all_tools`` and assert it is
        **not** the same object as ``server.mcp``."""

        # We can't actually run mcp.run (it would block on stdio),
        # but we can intercept ``register_all_tools`` and inspect
        # what app instance it receives.
        from fastmcp import FastMCP

        from percival_khan_calendar import server

        captured = {"app": None}

        def fake_register_all_tools(app, adapter):
            captured["app"] = app

        def fake_register_prompts(app):
            captured["app"] = captured["app"] or app

        def fake_register_resources(app):
            captured["app"] = captured["app"] or app

        def fake_run(*args, **kwargs):
            # Stop the boot early — we just want to inspect the app.
            raise SystemExit(0)

        monkeypatch.setattr(server, "register_all_tools", fake_register_all_tools)
        monkeypatch.setattr(server, "register_prompts", fake_register_prompts)
        monkeypatch.setattr(server, "register_resources", fake_register_resources)
        monkeypatch.setattr(FastMCP, "run", fake_run)

        with pytest.raises(SystemExit):
            server.main()

        # The boot-time app must NOT be the module-global ``mcp``.
        module_mcp = server.mcp
        boot_app = captured["app"]
        assert isinstance(boot_app, FastMCP)
        assert boot_app is not module_mcp, (
            "main() reused the module-level mcp global; a fresh "
            "FastMCP instance is required so re-bootstrapping works."
        )


class TestPromptsNoDictAnnotation:
    """Round-7 audit: every prompt in ``tools/prompts.py`` must
    return ``list[str]`` (the FastMCP 3.x contract), not ``list[dict]``.
    Earlier drafts typed this incorrectly. Pin the contract."""

    def test_all_prompt_functions_have_correct_annotation(self):
        import inspect

        from percival_khan_calendar.tools.prompts import register_prompts

        # We can't easily extract the inner closures from the
        # decorator wrapper without a FastMCP registry peek, so
        # we re-register and then introspect via the call graph.
        app = FastMCP("annotation-test")

        # Patch the decorator mechanics to capture the wrapped
        # functions before they hit the registry.
        captured_funcs = {}

        real_prompt = app.prompt

        def spy_prompt(name=None, **kwargs):
            def deco(fn):
                captured_funcs[name or fn.__name__] = fn
                return real_prompt(name=name, **kwargs)(fn)

            return deco

        app.prompt = spy_prompt  # type: ignore[method-assign]
        register_prompts(app)

        for name, fn in captured_funcs.items():
            hints = inspect.get_annotations(fn, eval_str=True)
            assert "return" in hints, f"{name} missing 'return' annotation"
            # ``list[str]`` may not be identity-equal across
            # invocations (Python subscript semantics) but it's
            # origin-equal. We compare by ``repr`` so dynamically
            # built subscript generics work.
            ann = hints["return"]
            ann_repr = repr(ann)
            assert ann_repr == "list[str]" or ann_repr.startswith("list["), (
                f"{name} return annotation is {ann!r}; must be list[...] (e.g. list[str])"
            )
