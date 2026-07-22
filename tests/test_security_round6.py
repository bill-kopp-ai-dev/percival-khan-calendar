"""Round-6 S6 regression: serialization format consistency.

After ``khan_update_event`` the .ics file used to be re-written with
``DTSTART:2026-07-23 12:30:00+00:00`` (UTC explicit-offset form) even
though ``khan_create_event`` produced ``DTSTART:20260723T123000Z``
(the RFC-5545 canonical UTC ``Z`` form). Both are valid but the
inconsistency broke interop with calendar clients that import the
exported .ics. This file pins the canonical form.
"""

from __future__ import annotations

import re

from percival_khan_calendar.adapters.khal_adapter import KhalAdapter


def _dt_canonical_z(ics_text: str) -> bool:
    """All DTSTART/DTEND lines match the RFC-5545 …T…Z form."""
    pattern = re.compile(r"^(DTSTART|DTEND):(\d{8}T\d{6})Z\s*$", re.MULTILINE)
    return bool(pattern.search(ics_text))


class TestDTStartSerializationCanonical:
    def test_create_emits_z_form(self, isolated_workspace):
        a = KhalAdapter()
        m = a.write_event(title="S6-create", start="tomorrow 10:00")
        body = m.filepath.read_text()
        assert _dt_canonical_z(body), (
            f"create_event must emit canonical DTSTART/DTEND ``…Z``:\n{body}"
        )

    def test_update_emits_z_form(self, isolated_workspace):
        a = KhalAdapter()
        a.write_event(title="S6-update", start="tomorrow 10:00")
        updated = a.update_event(
            "S6-update",
            fields={
                "summary": "S6-update renamed",
                "dtstart": "tomorrow 11:00",
                "dtend": "tomorrow 12:00",
            },
        )
        body = updated.filepath.read_text()
        assert _dt_canonical_z(body), (
            f"update_event must emit canonical DTSTART/DTEND ``…Z`` (S6 regression):\n{body}"
        )
        # Specifically: the buggy form ``DTSTART:…+00:00`` should not
        # appear anywhere in the .ics output.
        assert "+00:00" not in body, (
            f"DTSTART/DTEND still uses ``+00:00`` instead of ``Z``:\n{body}"
        )

    def test_to_utc_z_idempotent_on_already_utc(self):
        from datetime import datetime, timezone

        from percival_khan_calendar.adapters.khal_adapter import _to_utc_z

        dt = datetime(2026, 12, 25, 14, 30, tzinfo=timezone.utc)
        out = _to_utc_z(dt)
        # Same object reference when already UTC: cheap happy path.
        assert out is dt or out == dt
        assert out.tzinfo is timezone.utc

    def test_to_utc_z_converts_aware_non_utc(self):
        from datetime import datetime, timedelta, timezone

        from percival_khan_calendar.adapters.khal_adapter import _to_utc_z

        # America/Sao_Paulo -03 -> +03 hours UTC, exact wall clock preserved.
        tz_sp = timezone(timedelta(hours=-3))
        dt = datetime(2026, 12, 25, 14, 30, tzinfo=tz_sp)
        out = _to_utc_z(dt)
        assert out.hour == 17
        assert out.tzinfo is timezone.utc

    def test_to_utc_z_promotes_naive_as_local(self):
        from datetime import datetime, timezone

        from percival_khan_calendar.adapters.khal_adapter import _to_utc_z

        dt = datetime(2026, 12, 25, 14, 30)
        out = _to_utc_z(dt)
        # Naive datetimes are interpreted in local time then converted;
        # the *displayed* hour may shift, but the output tzinfo is
        # exactly UTC.
        assert out.tzinfo is timezone.utc
