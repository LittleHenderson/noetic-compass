"""Tests for the SQLite persistence layer (isolated temp DB per test)."""

from __future__ import annotations

from datetime import datetime

import pytest

from cas_native.belief import Belief
from cas_native.belief import persistence


def _t(hour: int = 12) -> datetime:
    return datetime(2026, 5, 4, hour, 0, 0)


def _build(claim_key: str = "k1", **overrides) -> Belief:
    base = dict(
        claim_key=claim_key,
        claim_text="practice makes perfect",
        cas_expression="^7^O",
        vibration=0.5,
        rhythm_count=2,
        rpm_chain_satisfied=True,
        rpm_chain_status={"stages": {"A0": {"passed": True}}},
        inversion_scan_clean=True,
        inversion_scan_axes={"N": {"clean": True}},
        first_seen=_t(),
        last_reinforced=_t(),
        sources=["chat-session"],
        locked=False,
    )
    base.update(overrides)
    return Belief(**base)


@pytest.fixture()
def db_conn(tmp_path):
    path = tmp_path / "beliefs.db"
    conn = persistence.open_db(path)
    try:
        yield conn
    finally:
        conn.close()


def test_open_db_creates_schema(db_conn):
    tables = {
        r[0]
        for r in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "beliefs" in tables
    assert "observations" in tables
    assert "contradictions" in tables
    belief_columns = {
        r[1] for r in db_conn.execute("PRAGMA table_info(beliefs)").fetchall()
    }
    assert "inversion_scanner_version" in belief_columns


def test_upsert_and_fetch(db_conn):
    b = _build()
    persistence.upsert_belief(db_conn, b)
    out = persistence.fetch_belief(db_conn, "k1")
    assert out is not None
    assert out.claim_key == "k1"
    assert out.claim_text == b.claim_text
    assert out.vibration == pytest.approx(0.5)
    assert out.rpm_chain_satisfied is True
    assert out.inversion_scan_axes == {"N": {"clean": True}}


def test_fetch_missing_returns_none(db_conn):
    assert persistence.fetch_belief(db_conn, "nope") is None


def test_upsert_overwrites_existing(db_conn):
    persistence.upsert_belief(db_conn, _build(vibration=0.2))
    persistence.upsert_belief(db_conn, _build(vibration=0.9))
    out = persistence.fetch_belief(db_conn, "k1")
    assert out.vibration == pytest.approx(0.9)


def test_list_beliefs_order_by_vibration_desc(db_conn):
    persistence.upsert_belief(db_conn, _build(claim_key="a", vibration=0.2))
    persistence.upsert_belief(db_conn, _build(claim_key="b", vibration=0.9))
    persistence.upsert_belief(db_conn, _build(claim_key="c", vibration=0.5))
    rows = persistence.list_beliefs(db_conn)
    assert [b.claim_key for b in rows] == ["b", "c", "a"]


def test_list_beliefs_locked_only(db_conn):
    persistence.upsert_belief(
        db_conn, _build(claim_key="a", locked=True, vibration=0.9)
    )
    persistence.upsert_belief(
        db_conn, _build(claim_key="b", locked=False, vibration=0.5)
    )
    rows = persistence.list_beliefs(db_conn, locked_only=True)
    assert len(rows) == 1
    assert rows[0].claim_key == "a"


def test_observation_insert_and_fetch(db_conn):
    persistence.upsert_belief(db_conn, _build())
    persistence.insert_observation(db_conn, "k1", _t(10), 0.5, "chat")
    persistence.insert_observation(db_conn, "k1", _t(11), 0.3, "chat")
    obs = persistence.fetch_observations(db_conn, "k1")
    assert len(obs) == 2
    assert obs[0].timestamp == _t(10)
    assert obs[0].evidence_strength == pytest.approx(0.5)


def test_observation_count(db_conn):
    persistence.upsert_belief(db_conn, _build())
    assert persistence.count_observations(db_conn, "k1") == 0
    persistence.insert_observation(db_conn, "k1", _t(10), 0.5, "chat")
    persistence.insert_observation(db_conn, "k1", _t(11), 0.5, "chat")
    assert persistence.count_observations(db_conn, "k1") == 2


def test_contradiction_insert_and_fetch(db_conn):
    persistence.upsert_belief(db_conn, _build())
    persistence.insert_contradiction(db_conn, "k1", _t(13), "user said no")
    rows = persistence.fetch_contradictions(db_conn, "k1")
    assert len(rows) == 1
    assert rows[0]["reason"] == "user said no"
    assert persistence.count_contradictions(db_conn, "k1") == 1


def test_delete_belief_cascades_to_history(db_conn):
    persistence.upsert_belief(db_conn, _build())
    persistence.insert_observation(db_conn, "k1", _t(10), 0.5, "chat")
    persistence.insert_contradiction(db_conn, "k1", _t(11), "x")
    persistence.delete_belief(db_conn, "k1")
    assert persistence.fetch_belief(db_conn, "k1") is None
    assert persistence.count_observations(db_conn, "k1") == 0
    assert persistence.count_contradictions(db_conn, "k1") == 0


def test_all_claim_keys(db_conn):
    persistence.upsert_belief(db_conn, _build(claim_key="a"))
    persistence.upsert_belief(db_conn, _build(claim_key="b"))
    keys = sorted(persistence.all_claim_keys(db_conn))
    assert keys == ["a", "b"]


def test_round_trip_preserves_complex_status(db_conn):
    status = {
        "stages": {
            "A0": {"passed": True, "reason": "ok", "observations": 3},
            "Dn": {"passed": True, "reason": "compiled clean"},
        },
        "compiler_valid": True,
        "compiler_error": None,
    }
    axes = {
        "N": {"clean": True, "reason": "no involution"},
        "W": {"clean": False, "reason": "P after O"},
    }
    persistence.upsert_belief(
        db_conn,
        _build(
            rpm_chain_status=status,
            inversion_scan_axes=axes,
            inversion_scan_clean=False,
        ),
    )
    out = persistence.fetch_belief(db_conn, "k1")
    assert out.rpm_chain_status == status
    assert out.inversion_scan_axes == axes
    assert out.inversion_scan_clean is False


def test_upsert_records_current_inversion_scanner_version(db_conn):
    from cas_native.belief.inversion_gate import INVERSION_SCANNER_VERSION

    persistence.upsert_belief(db_conn, _build())

    assert (
        persistence.inversion_scanner_version_for_claim(db_conn, "k1")
        == INVERSION_SCANNER_VERSION
    )
