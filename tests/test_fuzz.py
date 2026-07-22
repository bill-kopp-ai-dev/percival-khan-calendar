"""Property-based fuzzing of input models using Hypothesis."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from percival_khan_calendar.models import CreateEventInput


@given(
    title=st.text(min_size=0, max_size=500),
    start=st.text(min_size=0, max_size=200),
    description=st.text(min_size=0, max_size=2000),
    location=st.text(min_size=0, max_size=200),
    alarm=st.text(min_size=0, max_size=16),
    recurrence=st.text(min_size=0, max_size=16),
)
def test_create_event_input_never_crashes(title, start, description, location, alarm, recurrence):
    """The validator must always raise ValidationError or return a model,
    never crash with an unexpected exception."""
    try:
        CreateEventInput(
            title=title or "x",
            start=start or "today",
            description=description,
            location=location,
            alarm=alarm,
            recurrence=recurrence,
        )
    except ValidationError:
        pass
    except Exception as exc:  # pragma: no cover -- regression check
        pytest.fail(f"Unexpected exception: {exc!r}")


@given(text=st.text(min_size=0, max_size=500))
def test_search_input_never_crashes(text):
    try:
        from percival_khan_calendar.models import SearchEventsInput

        if 1 <= len(text) <= 128 and not text.startswith("-") and "--" not in text:
            SearchEventsInput(query=text)
        else:
            try:
                SearchEventsInput(query=text)
            except ValidationError:
                pass
    except ValidationError:
        pass
    except Exception as exc:  # pragma: no cover -- regression check
        pytest.fail(f"Unexpected exception: {exc!r}")
