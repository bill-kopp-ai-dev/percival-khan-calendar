"""Tests for the typed exception hierarchy."""

from __future__ import annotations

from percival_khan_calendar.exceptions import (
    KhanAmbiguousMatchError,
    KhanError,
    KhanInfrastructureError,
    KhanLockError,
    KhanNotFoundError,
    KhanValidationError,
)


def test_all_errors_inherit_from_khan_error():
    for cls in (
        KhanValidationError,
        KhanNotFoundError,
        KhanAmbiguousMatchError,
        KhanInfrastructureError,
        KhanLockError,
    ):
        assert issubclass(cls, KhanError)


def test_validation_error_is_value_error():
    # Multiple inheritance lets ``except ValueError`` also catch it.
    assert issubclass(KhanValidationError, ValueError)


def test_not_found_is_lookup_error():
    assert issubclass(KhanNotFoundError, LookupError)


def test_ambiguous_carries_matches():
    err = KhanAmbiguousMatchError("foo", ["A", "B", "C", "D"])
    assert err.term == "foo"
    assert err.matches == ["A", "B", "C", "D"]
    # message contains at most the first three candidates
    assert "A" in str(err)
    assert "B" in str(err)
    assert "C" in str(err)


def test_ambiguous_short_list():
    err = KhanAmbiguousMatchError("foo", ["A"])
    assert "1 candidate:" in str(err)


def test_infrastructure_carries_message():
    err = KhanInfrastructureError("boom")
    assert str(err) == "boom"
    assert isinstance(err, RuntimeError)


def test_lock_carries_message():
    err = KhanLockError("held")
    assert "held" in str(err)


def test_khan_error_is_exception():
    assert issubclass(KhanError, Exception)
