"""End-to-end belief store integration tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cas_native.belief import (
    BeliefStore,
    DEFAULT_HALF_LIFE_DAYS,
    MIN_RHYTHM_FOR_LOCK,
    VIBRATION_LOCK_THRESHOLD,
    derive_claim_key,
    lock_rule,
)


@pytest.fixture()
def store(tmp_path):
    s = BeliefStore(tmp_path / "beliefs.db")
    try:
        yield s
    finally:
        s.close()


def _t(hour: int = 12) -> datetime:
    return datetime(2026, 5, 4, hour, 0, 0)


# ---------------------------------------------------------------------------
# derive_claim_key
# ---------------------------------------------------------------------------


def test_derive_claim_key_stable_across_whitespace_and_case():
    a = derive_claim_key("Practice Makes  perfect", "^7^O")
    b = derive_claim_key("practice makes perfect", "^7^O")
    assert a == b


def test_derive_claim_key_changes_with_expression():
    a = derive_claim_key("foo", "^4^P")
    b = derive_claim_key("foo", "^4^O")
    assert a != b


# ---------------------------------------------------------------------------
# lock_rule pure function
# ---------------------------------------------------------------------------


def test_lock_rule_requires_all_four():
    from cas_native.belief import Belief

    base = dict(
        claim_key="k",
        claim_text="t",
        cas_expression="^4^P",
        vibration=0.9,
        rhythm_count=MIN_RHYTHM_FOR_LOCK,
        rpm_chain_satisfied=True,
        rpm_chain_status={},
        inversion_scan_clean=True,
        inversion_scan_axes={},
        first_seen=_t(),
        last_reinforced=_t(),
    )
    assert lock_rule(Belief(**base)) is True
    assert lock_rule(Belief(**{**base, "rpm_chain_satisfied": False})) is False
    assert lock_rule(Belief(**{**base, "vibration": 0.5})) is False
    assert lock_rule(Belief(**{**base, "inversion_scan_clean": False})) is False
    assert (
        lock_rule(Belief(**{**base, "rhythm_count": MIN_RHYTHM_FOR_LOCK - 1}))
        is False
    )


# ---------------------------------------------------------------------------
# BeliefStore lifecycle
# ---------------------------------------------------------------------------


def test_first_observation_creates_belief(store):
    b = store.record_observation(
        "practice makes perfect",
        "^7^O",
        evidence_strength=0.5,
        now=_t(10),
    )
    assert b.rhythm_count == 1
    assert b.vibration == pytest.approx(0.5)
    assert b.locked is False  # rhythm < threshold
    assert "chat-session" in b.sources


def test_three_observations_lock_belief(store):
    base = _t()
    for i in range(3):
        b = store.record_observation(
            "practice makes perfect",
            "^7^O",
            evidence_strength=0.5,
            now=base + timedelta(minutes=i),
        )
    # After three observations: rhythm = 3, vibration = 0.875.
    assert b.rhythm_count == 3
    assert b.vibration > VIBRATION_LOCK_THRESHOLD
    assert b.rpm_chain_satisfied is True
    assert b.inversion_scan_clean is True
    assert b.locked is True


def test_invalid_expression_never_locks(store):
    base = _t()
    for i in range(5):
        b = store.record_observation(
            "garbage",
            "not a CAS expression",
            evidence_strength=1.0,
            now=base + timedelta(minutes=i),
        )
    assert b.rpm_chain_satisfied is False
    assert b.locked is False


def test_check_belief_returns_none_for_unknown(store):
    assert store.check_belief("nothing", "^4^P") is None


def test_check_belief_returns_recorded(store):
    store.record_observation("x", "^4^P", now=_t())
    out = store.check_belief("x", "^4^P")
    assert out is not None
    assert out.cas_expression == "^4^P"


def test_list_locked_returns_only_locked_sorted(store):
    base = _t()
    # claim A: locks
    for i in range(4):
        store.record_observation(
            "claim a", "^4^P", 0.6, now=base + timedelta(minutes=i)
        )
    # claim B: doesn't lock (only one observation)
    store.record_observation(
        "claim b", "^4^C", 0.6, now=base + timedelta(hours=1)
    )
    locked = store.list_locked()
    assert len(locked) == 1
    assert locked[0].claim_text == "claim a"


def test_record_then_contradict_unlocks(store):
    base = _t()
    # Lock claim a.
    for i in range(4):
        last = store.record_observation(
            "claim a", "^4^P", 0.6, now=base + timedelta(minutes=i)
        )
    assert last.locked is True

    # Contradict.
    after = store.add_contradiction(
        "claim a",
        "^4^P",
        reason="user disagreed",
        now=base + timedelta(minutes=10),
    )
    assert after is not None
    # Inversion axis N should now flag because contradiction history is non-empty.
    assert after.inversion_scan_clean is False
    assert after.inversion_scan_axes["N"]["clean"] is False
    assert after.locked is False


def test_add_contradiction_unknown_claim_returns_none(store):
    out = store.add_contradiction("unknown", "^4^P", reason="x")
    assert out is None


def test_decay_all_unlocks_after_long_gap(store):
    base = _t()
    for i in range(4):
        last = store.record_observation(
            "stale claim", "^4^P", 0.6, now=base + timedelta(minutes=i)
        )
    assert last.locked is True
    far_future = base + timedelta(days=10 * DEFAULT_HALF_LIFE_DAYS)
    changed = store.decay_all(now=far_future)
    assert changed >= 1
    refreshed = store.check_belief("stale claim", "^4^P")
    assert refreshed.locked is False
    assert refreshed.vibration < VIBRATION_LOCK_THRESHOLD


def test_explain_returns_full_breakdown(store):
    store.record_observation("x", "^4^P", 0.5, now=_t(10))
    b = store.check_belief("x", "^4^P")
    explanation = store.explain(b.claim_key)
    assert explanation is not None
    assert explanation["belief"].claim_text == "x"
    assert "lock_rule" in explanation
    assert "vibration_above" in explanation["lock_rule"]
    assert explanation["lock_rule"]["min_rhythm"] == MIN_RHYTHM_FOR_LOCK


def test_explain_unknown_returns_none(store):
    assert store.explain("nope") is None


def test_history_returns_observations_and_contradictions(store):
    store.record_observation("x", "^4^P", 0.5, now=_t(10))
    store.record_observation("x", "^4^P", 0.5, now=_t(11))
    b = store.check_belief("x", "^4^P")
    store.add_contradiction("x", "^4^P", "nope", now=_t(12))
    h = store.history(b.claim_key)
    assert len(h["observations"]) == 2
    assert len(h["contradictions"]) == 1


def test_find_by_claim_returns_all_matching(store):
    store.record_observation("same", "^4^P", 0.5, now=_t(10))
    store.record_observation("same", "^4^O", 0.5, now=_t(11))
    out = store.find_by_claim("SAME ")
    assert len(out) == 2


def test_context_manager_closes(tmp_path):
    with BeliefStore(tmp_path / "b.db") as s:
        s.record_observation("x", "^4^P", 0.5)
    # No exception means close() ran cleanly.


def test_evidence_strength_affects_lock_speed(store):
    base = _t()
    # Strong evidence: 1 obs at 1.0 -> vibration 1.0 but rhythm only 1 -> not locked.
    b = store.record_observation("x", "^4^P", 1.0, now=base)
    assert b.vibration == pytest.approx(1.0)
    assert b.locked is False
    # Need MIN_RHYTHM_FOR_LOCK observations.
    for i in range(1, MIN_RHYTHM_FOR_LOCK):
        b = store.record_observation(
            "x", "^4^P", 0.1, now=base + timedelta(minutes=i)
        )
    assert b.rhythm_count >= MIN_RHYTHM_FOR_LOCK
    assert b.locked is True
