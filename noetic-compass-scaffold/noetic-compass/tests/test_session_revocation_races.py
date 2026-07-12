from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from api.services.production.state_substrate import InMemoryStateStore, VersionConflict
from api.services.sessions.store import (
    REVOKE_CAS_ATTEMPTS,
    SESSIONS_STORAGE_TENANT,
    SessionStore,
)


class TouchRacingStore(InMemoryStateStore):
    """Advance the session version just before selected revoke writes."""

    conflicts_remaining = 0

    def put(self, record, *, expected_version):
        if (
            record.kind == "session"
            and expected_version > 0
            and self.conflicts_remaining > 0
        ):
            self.conflicts_remaining -= 1
            current = super().get(record.tenant_id, record.kind, record.record_id)
            assert current is not None
            payload = dict(current.payload)
            payload["last_seen"] = datetime.now(UTC).isoformat()
            super().put(current.with_payload(payload), expected_version=current.version)
        return super().put(record, expected_version=expected_version)


def _new_store() -> tuple[TouchRacingStore, SessionStore, str]:
    backend = TouchRacingStore()
    sessions = SessionStore(backend)
    created = sessions.create_session(
        account_id="acct-1",
        tenant_id="tenant-1",
        role="member",
        auth_epoch=7,
    )
    return backend, sessions, created.session_id


def test_revoke_retries_when_touch_wins_version_race() -> None:
    backend, sessions, session_id = _new_store()
    backend.conflicts_remaining = 1

    assert sessions.revoke_session(session_id) is True
    revoked = sessions.get_session(session_id)
    assert revoked is not None and revoked.is_revoked
    assert revoked.auth_epoch == 7


def test_revoke_exhaustion_raises_real_conflict_and_leaves_live() -> None:
    backend, sessions, session_id = _new_store()
    backend.conflicts_remaining = REVOKE_CAS_ATTEMPTS

    with pytest.raises(VersionConflict):
        sessions.revoke_session(session_id)
    current = sessions.get_session(session_id)
    assert current is not None and current.is_live()

    # Once contention subsides, a later targeted revoke still converges.
    assert sessions.revoke_session(session_id) is True
    assert sessions.get_session(session_id).is_revoked


def test_touch_is_throttled_and_preserves_auth_epoch() -> None:
    backend, sessions, session_id = _new_store()
    before = backend.get(SESSIONS_STORAGE_TENANT, "session", session_id)
    assert before is not None

    sessions.touch_session(session_id)
    unchanged = backend.get(SESSIONS_STORAGE_TENANT, "session", session_id)
    assert unchanged is not None and unchanged.version == before.version

    later = (datetime.now(UTC) + timedelta(seconds=61)).isoformat()
    sessions.touch_session(session_id, when=later)
    touched = backend.get(SESSIONS_STORAGE_TENANT, "session", session_id)
    assert touched is not None and touched.version == before.version + 1
    assert sessions.get_session(session_id).auth_epoch == 7
