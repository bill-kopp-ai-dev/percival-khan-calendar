"""Prompts primitivos (Protocol MCP) para o servidor de calendário.

Cada prompt é um *template* parametrizado que o agente recebe via
``prompts/list`` e ``prompts/get`` no protocolo MCP. Os prompts
ajudam o LLM a entender:

* **quando** preferir cada tool,
* **quais invariantes** respeitar (TZ, UID, formato DD/MM/YYYY),
* **o fluxo completo** de um CRUD do calendário.

Convenção:

* Prompt *fixo* — argumentos zero. O texto é determinístico.
* Prompt *parametrizado* — argumentos via type hints + docstring.
  FastMCP gera o JSON Schema a partir deles.
* O retorno é uma ``list[mcp.types.PromptMessage]`` com role
  ``user`` (Mensagem de "system prompt" para o LLM) e ``assistant``
  (opcional — usado em few-shot).

Ver:

* https://modelcontextprotocol.io/specification/server/prompts
* FastMCP 3.x ``@mcp.prompt`` decorator.
"""

from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Constantes compartilhadas — texto que aparece em vários prompts.
# Manter sincronizado com ``models.py`` (validação) e
# ``security.py`` (argument-injection guard).
# ---------------------------------------------------------------------------

_INVARIANTS_BLOCK = """\
Invariantes não-negociáveis:

1. **Formato de data.** Prefira ``DD/MM/YYYY`` em vez de ``"tomorrow"``
   ou ``"7d"`` quando o horário é importante. O ``khal 0.14.0`` CLI
   pode calcular janelas ``tomorrow 1d`` de forma imprecisa em
   containers com TZ != local; usar ``DD/MM/YYYY 7d`` (start+range
   absolutos) é deterministicamente correto em qualquer fuso.
2. **Timezone.** Todos os eventos são serializados em UTC ``Z``
   no .ics (round-5 fix). O ``khan_view_*`` e ``khan_list_*``
   formatam em horário local (TZ do agente). Não confunda os dois.
3. **UID preservado.** ``khan_update_event`` mantém o UID; nunca
   delete+recrie para "atualizar". A função preserva também RRULE,
   VALARM, EXDATE, LOCATION, DESCRIPTION se você não as sobrescrever.
4. **Argument injection.** Toda string começa com ``-`` ou contém
   ``--`` é rejeitada pela Pydantic guard. Use letras normais.
   Para tarefas como "check-in", escreva ``title="checkin"`` em vez
   de ``title="--checkin"``.
5. **Dry-run por default.** Deletar sempre via
   ``khan_delete_event_safe(confirm=False)`` primeiro para mostrar
   ao usuário o que será apagado. ``khan_delete_event`` é o canivete
   suíço — só use se o usuário *explicitamente* pediu delete duro.
"""


def _msg(text: str) -> list[str]:
    """Return a single-element list of the prompt body.

    FastMCP 3.x ``Prompt.convert_result`` accepts ``str`` directly
    and wraps it into a ``PromptMessage(role='user')`` for us. We
    keep the return type as ``list[str]`` to match the documented
    FastMCP convention of returning a list — easier to swap to
    multi-message few-shot examples later without changing every
    prompt site.
    """
    return [text.strip()]


def register_prompts(mcp: FastMCP) -> None:
    """Register all 6 primitive prompts. Idempotent (skips duplicates)."""

    @mcp.prompt(
        name="khan_overview",
        description=(
            "Overview of the percival-khan-calendar server. Use this "
            "prompt at the start of a session before the agent makes "
            "any calendar call — it lists every tool, the recommended "
            "happy-path workflow, and the global invariants."
        ),
        tags={"orientation", "beginner"},
    )
    def khan_overview() -> list[dict]:
        return _msg(
            f"""\
You have access to the **percival-khan-calendar** MCP server. It
exposes 12 tools grouped into reads, writes, views, and admin.

**Recommended workflow** (in order):
1. ``khan_get_status`` to confirm the server is operational.
2. ``khan_list_events(start_date="DD/MM/YYYY", range_or_end="7d")``
   to see what's coming up.
3. ``khan_view_agenda(period="7d")`` for a chat-friendly agenda.
4. ``khan_view_calendar(reference_month="today")`` for a visual
   month grid.
5. ``khan_search_events(query="...")`` when the user asks "find the
   meeting about X".
6. ``khan_get_event(exact_term="...")`` when you already know the
   summary (or have the UID).
7. ``khan_create_event(...)`` for new entries.
8. ``khan_update_event(...)`` for in-place edits (preserves UID).
9. ``khan_delete_event_safe(exact_term=..., confirm=False)`` then
   ``(..., confirm=True)`` for destructive operations.
10. ``khan_export_ics()`` for human-readable backups.

Available side tools: ``khan_list_calendars``, ``khan_export_ics``.

{_INVARIANTS_BLOCK}

If a tool returns a short string with an error, treat it as a
[recoverable_by_agent=false] signal ONLY when the string starts with
that tag prefix. Otherwise the tool succeeded and the data is in the
text you received.
"""
        )

    @mcp.prompt(
        name="khan_create_event_semantics",
        description=(
            "Pre-flight for khan_create_event. Use this prompt before "
            "creating any event — it documents the field syntax, the "
            "alarm format, the recurrence whitelist, and the timezone "
            "behaviour so you get the call right the first time."
        ),
        tags={"create", "writing"},
    )
    def khan_create_event_semantics() -> list[dict]:
        return _msg(
            f"""\
Calling pattern:

    khan_create_event(
        title="string not starting with - and not containing --",
        start="see TIME-EXPRESSIONS below",
        end="see TIME-EXPRESSIONS below",     # optional, default = start+1h
        description="string, free-form",      # optional
        location="string, free-form",        # optional
        alarm="",                             # or "15m" / "1h" / "2d"
        recurrence="",                        # or "daily" / "weekly" /
                                              #     "monthly" / "yearly"
    )

TIME-EXPRESSIONS (the ``start`` and ``end`` fields):

* ``"today"`` / ``"tomorrow"`` / ``"now"``
* ``"DD/MM/YYYY"`` → all-day, midnight
* ``"DD/MM/YYYY HH:MM"`` → exact local time  (PREFERRED for predictability)
* ``"HH:MM"`` → today's wall clock at that time
* ``"today HH:MM"`` / ``"tomorrow HH:MM"`` (compound)

ALARM FORMAT — ``alarm="<n><unit>"`` where unit ∈ {{m, h, d}}:
* ``"15m"`` 15 minutes before
* ``"1h"`` 1 hour before
* ``"2d"`` 2 days before

RECURRENCE — one of:
* ``"daily"``, ``"weekly"``, ``"monthly"``, ``"yearly"``

{_INVARIANTS_BLOCK}

The tool returns one of:

* A short markdown block with ``UID=<hex>@percival-khan-calendar`` —
  **success**. Save the UID if you intend to update or delete the
  event later.
* A string starting with ``[recoverable_by_agent=...]`` —
  **failure**. Read the message; Pydantic validation failures are
  recoverable (adjust the input and retry); missing-binary errors
  are NOT recoverable.

When the user says "tomorrow at 10:00", prefer::

    start="tomorrow 10:00", end="tomorrow 11:00"

When the user says "next Tuesday morning":

    start="<next Tuesday> 09:00", end="<next Tuesday> 10:00"

When the user is explicit ("24/12/2026 14:00"):

    start="24/12/2026 14:00", end="24/12/2026 15:00"
"""
        )

    @mcp.prompt(
        name="khan_update_workflow",
        description=(
            "Workflow for khan_update_event. Use this prompt before "
            "mutating any existing event — it explains the in-place "
            "update semantics, the UID preservation rule, and how "
            "ambiguous matches are surfaced."
        ),
        tags={"update", "writing"},
    )
    def khan_update_workflow() -> list[dict]:
        return _msg(
            f"""\
Calling pattern:

    khan_update_event(
        old_term="<summary or UID that uniquely matches ONE event>",
        new_title="new title (preserved if omitted)",
        new_start="<time expression, see khan_create_event_semantics>",
        new_end="<time expression>",
        new_description="...",
        new_location="...",
    )

Key rules:

1. The update is **in place**: UID stays the same, the file stays
   on disk at the same path, RRULE/VALARM are preserved unless you
   re-pass them.
2. **Lookup is by summary first, then UID.** ``find_event_unique``
   raises ``KhanAmbiguousMatchError`` if multiple events match. If
   you get that error, run ``khan_search_events(old_term)`` to see
   the candidates; either pick a more specific ``old_term`` or use
   a UID.
3. Only the fields you supply are updated. Omitted fields stay at
   their current value. To "remove" a description, pass
   ``new_description=""`` — empty string is treated as ``None``.
4. Datetime is normalised to UTC via ``khan_get_status``. The
   on-disk file will serialise DTSTART as ``YYYYMMDDTHHMMSSZ``.

{_INVARIANTS_BLOCK}
"""
        )

    @mcp.prompt(
        name="khan_delete_with_confirmation",
        description=(
            "Dry-run / confirm pattern for khan_delete_event_safe. "
            "Use this prompt before any destructive operation — it "
            "implements the safe-by-default two-call delete protocol."
        ),
        tags={"delete", "safety"},
    )
    def khan_delete_with_confirmation() -> list[dict]:
        return _msg(
            f"""\
Never delete without explicit user confirmation.

Two-call protocol:

1. ``khan_delete_event_safe(exact_term="<summary>", confirm=False)``
   → returns a DRY-RUN block listing UID + summary + file. Show
   this to the user. Do NOT proceed if the user is unsure.
2. Only after the user confirms in a follow-up message::

       khan_delete_event_safe(exact_term="<summary>", confirm=True)

   → returns ``DELETED <UID>``.

If ``exact_term`` matches more than one event, the tool refuses
with ``KhanAmbiguousMatchError`` and returns a list. Use
``khan_search_events`` to disambiguate, then retry with a more
specific term or with a UID.

If ``exact_term`` matches nothing, the tool returns::

    [recoverable_by_agent=false] Refused: No event matches '<term>'.

—this is NOT a recoverable error; do not retry with empty strings.
Ask the user for a hint instead.

If the user explicitly says "delete it for real, I don't want a
dry run", and the message is unambiguous, you can use
``khan_delete_event(exact_term="...")`` once. Always show the user
what you are about to delete *before* invoking it.

{_INVARIANTS_BLOCK}
"""
        )

    @mcp.prompt(
        name="khan_search_strategy",
        description=(
            "Strategies for khan_search_events. Pass a ``keyword`` "
            "and an optional ``scope`` (summary/location/description) "
            "so the agent knows which field to query. Use this when "
            "the agent can't find a specific event."
        ),
        tags={"search", "discovery"},
    )
    def khan_search_strategy(
        keyword: str,
        scope: Literal["summary", "location", "description"] = "summary",
    ) -> list[dict]:
        return _msg(
            f"""\
You are searching for calendar events whose ``{scope}`` field
contains the substring ``{keyword}``.

Strategy:

1. ``khan_search_events`` does a **substring match** (case
   insensitive) on the chosen field. Searching for ``meeting``
   matches ``"Team meeting"`` *and* ``"Meetings 2026-01"``.
2. If ``{scope}=summary`` returns nothing, broaden the scope by
   re-running with ``scope="location"`` then ``scope="description"``.
3. A hit count above 5 usually means the keyword is too generic.
   Prefix-match: re-search with a longer substring ("Team" instead
   of "T").
4. To find the **next** occurrence of a recurring event, use
   ``khan_list_events(start_date="<today>", range_or_end="30d")``
   after locating the UID — that's faster than guessing.
5. UID format returned by every find/list/create call is
   ``<uuid>@percival-khan-calendar``. Use it directly with
   ``khan_get_event(exact_term="<UID>")`` if you want to skip the
   substring search.

{_INVARIANTS_BLOCK}

Search keyword: ``{keyword}``. Scope: ``{scope}``.
"""
        )

    @mcp.prompt(
        name="khan_quick_action_quick_create",
        description=(
            "Quick-create template. Pass the user's free-form intent "
            "(Portuguese or English) and the prompt injects the "
            "exact khan_create_event call to invoke. Use this when "
            "the user says things like 'marque dentista amanhã 10h'."
        ),
        tags={"create", "nlp", "user-facing"},
    )
    def khan_quick_action_quick_create(user_intent: str) -> list[dict]:
        # Keep the user's words verbatim in the agent-side message;
        # this lets the LLM ground its response on the literal text.
        return _msg(
            f"""\
You received this user intent: ``{user_intent}``.

Translate it into a single ``khan_create_event`` call following
the rules of ``khan_create_event_semantics``.

Resolução rápida (Português):

* "amanhã" / "tomorrow" → ``"tomorrow"``
* "hoje" / "today" → ``"today"``
* "amanhã 10h" → ``"tomorrow 10:00"``
* "sexta 14h" → ``"<YYYY-MM-DD of next Friday> 14:00"``
* "dia 25" → ``"25/<current-month or next-month> 09:00"``

Default duration: 1 hour unless the intent explicitly says
"30 minutos" / "1 hora" / "2 dias".

Required:

* If the user's words do NOT name a calendar name, assume the
  default calendar (``nanobot``).
* If the user's words do NOT name an alarm, do not pass ``alarm``.
* If the user's words mention ``"toda semana"``, pass
  ``recurrence="weekly"``.

Example mapping — given intent "marque dentista amanhã 10h":

    khan_create_event(
        title="Dentista",
        start="tomorrow 10:00",
        end="tomorrow 11:00",
    )

{_INVARIANTS_BLOCK}
"""
        )


__all__ = ["register_prompts"]
