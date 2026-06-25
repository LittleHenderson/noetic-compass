"""Unit tests for the operator-audit primitive."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from cas_forex.operator_audit import (
    GUARD_PHRASE_ERROR_MESSAGE,
    OBSERVATIONAL_GUARD_PHRASES,
    OperatorAuditEntry,
    OperatorAuditLog,
    build_entry,
)


def _log(tmp_path: Path) -> OperatorAuditLog:
    return OperatorAuditLog(path=tmp_path / "operator-audit.jsonl")


def _ts(offset_minutes: int = 0) -> datetime:
    base = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(minutes=offset_minutes)


# ---------------------------------------------------------------------------


def test_list_recent_on_empty_log_returns_empty(tmp_path):
    log = _log(tmp_path)
    assert log.list_recent() == []
    assert log.list_recent(limit=10) == []
    assert log.count_by_kind() == {}
    stats = log.stats()
    assert stats["total"] == 0
    assert stats["by_kind"] == {}
    assert stats["oldest_at_iso"] is None
    assert stats["newest_at_iso"] is None
    assert stats["reversible_count"] == 0


def test_append_then_list_recent_roundtrips_record(tmp_path):
    log = _log(tmp_path)
    entry = build_entry(
        action_kind="STRATEGY_PROMOTED",
        summary="Promoted SMA-cross to live runtime queue.",
        target_id="strat-001",
        target_label="SMA-cross",
        payload={"queue_pos": 3},
        reversible=True,
        reversal_hint="Re-demote via /api/forex/strategy-dev-actions/demote",
        when=_ts(),
    )
    log.append(entry)

    listed = log.list_recent(limit=10)
    assert len(listed) == 1
    got = listed[0]
    assert got.entry_id == entry.entry_id
    assert got.action_kind == "STRATEGY_PROMOTED"
    assert got.summary == entry.summary
    assert got.target_id == "strat-001"
    assert got.target_label == "SMA-cross"
    assert dict(got.payload) == {"queue_pos": 3}
    assert got.reversible is True
    assert got.reversal_hint == entry.reversal_hint
    assert got.actor == "operator"


def test_since_iso_filter_drops_older_entries(tmp_path):
    log = _log(tmp_path)
    older = build_entry(
        action_kind="STRATEGY_PROMOTED",
        summary="older event",
        target_id="a",
        when=_ts(offset_minutes=-60),
    )
    newer = build_entry(
        action_kind="STRATEGY_DEMOTED",
        summary="newer event",
        target_id="b",
        when=_ts(offset_minutes=+60),
    )
    log.append(older)
    log.append(newer)

    cutoff = _ts(offset_minutes=0).replace(microsecond=0).isoformat()
    filtered = log.list_recent(limit=10, since_iso=cutoff)
    assert [e.entry_id for e in filtered] == [newer.entry_id]


def test_action_kinds_filter_whitelists_entries(tmp_path):
    log = _log(tmp_path)
    a = build_entry(action_kind="STRATEGY_PROMOTED", summary="a", target_id="1", when=_ts(0))
    b = build_entry(action_kind="STRATEGY_DEMOTED", summary="b", target_id="2", when=_ts(1))
    c = build_entry(action_kind="RUNTIME_GATE_FLIP", summary="c", target_id="3", when=_ts(2))
    for e in (a, b, c):
        log.append(e)

    filtered = log.list_recent(
        limit=10,
        action_kinds=["STRATEGY_PROMOTED", "RUNTIME_GATE_FLIP"],
    )
    kinds = {e.action_kind for e in filtered}
    assert kinds == {"STRATEGY_PROMOTED", "RUNTIME_GATE_FLIP"}
    assert len(filtered) == 2


def test_count_by_kind_tallies_correctly(tmp_path):
    log = _log(tmp_path)
    log.append(build_entry(action_kind="STRATEGY_PROMOTED", summary="x", target_id="1", when=_ts(0)))
    log.append(build_entry(action_kind="STRATEGY_PROMOTED", summary="y", target_id="2", when=_ts(1)))
    log.append(build_entry(action_kind="RUNTIME_GATE_FLIP", summary="z", target_id="g1", when=_ts(2)))

    counts = log.count_by_kind()
    assert counts == {"STRATEGY_PROMOTED": 2, "RUNTIME_GATE_FLIP": 1}


def test_stats_returns_all_required_fields(tmp_path):
    log = _log(tmp_path)
    e1 = build_entry(
        action_kind="STRATEGY_PROMOTED",
        summary="one",
        target_id="t1",
        reversible=True,
        when=_ts(0),
    )
    e2 = build_entry(
        action_kind="LEGACY_RECEIPTS_ARCHIVED",
        summary="two",
        target_id="t2",
        reversible=False,
        when=_ts(5),
    )
    log.append(e1)
    log.append(e2)

    stats = log.stats()
    assert stats["total"] == 2
    assert stats["by_kind"] == {
        "STRATEGY_PROMOTED": 1,
        "LEGACY_RECEIPTS_ARCHIVED": 1,
    }
    assert stats["oldest_at_iso"] == e1.recorded_at_iso
    assert stats["newest_at_iso"] == e2.recorded_at_iso
    assert stats["reversible_count"] == 1


def test_append_rejects_guard_phrase_summary(tmp_path):
    log = _log(tmp_path)
    bad = build_entry(
        action_kind="OTHER",
        summary="You should sell EURUSD before close",
        target_id="t1",
        when=_ts(0),
    )
    with pytest.raises(ValueError) as excinfo:
        log.append(bad)
    assert GUARD_PHRASE_ERROR_MESSAGE in str(excinfo.value)

    # File must remain in prior state (not exist OR be empty of bad entry).
    assert log.list_recent() == []


def test_append_rejects_each_guard_phrase_case_insensitive(tmp_path):
    log = _log(tmp_path)
    for phrase in OBSERVATIONAL_GUARD_PHRASES:
        bad = build_entry(
            action_kind="OTHER",
            summary=f"Note: {phrase.upper()} the next position",
            target_id=phrase,
            when=_ts(0),
        )
        with pytest.raises(ValueError):
            log.append(bad)


def test_entry_id_is_deterministic_for_same_triple(tmp_path):
    e1 = build_entry(
        action_kind="STRATEGY_PROMOTED",
        summary="anything",
        target_id="strat-001",
        when=_ts(0),
    )
    e2 = build_entry(
        action_kind="STRATEGY_PROMOTED",
        summary="totally different text",
        target_id="strat-001",
        when=_ts(0),
    )
    assert e1.entry_id == e2.entry_id

    e3 = build_entry(
        action_kind="STRATEGY_PROMOTED",
        summary="anything",
        target_id="strat-002",
        when=_ts(0),
    )
    assert e1.entry_id != e3.entry_id


def test_append_is_atomic_on_io_error(tmp_path):
    log = _log(tmp_path)
    # Seed one good entry first.
    good = build_entry(
        action_kind="STRATEGY_PROMOTED",
        summary="seed entry",
        target_id="seed",
        when=_ts(0),
    )
    log.append(good)
    seed_count = len(log.list_recent())
    assert seed_count == 1

    bad = build_entry(
        action_kind="STRATEGY_DEMOTED",
        summary="would-be entry",
        target_id="bad",
        when=_ts(1),
    )

    # Simulate I/O failure mid-write: monkey-patch ``open`` used inside
    # the audit module so the append raises before the line is written.
    def boom(*args, **kwargs):
        raise OSError("simulated disk full")

    with patch("cas_forex.operator_audit.open", boom, create=True):
        with pytest.raises(OSError):
            log.append(bad)

    # The seed entry must still be there and the bad entry must NOT
    # have been written.
    after = log.list_recent()
    assert len(after) == seed_count
    assert all(e.entry_id != bad.entry_id for e in after)


def test_list_recent_returns_newest_first(tmp_path):
    log = _log(tmp_path)
    first = build_entry(
        action_kind="STRATEGY_PROMOTED", summary="first", target_id="1", when=_ts(0)
    )
    second = build_entry(
        action_kind="STRATEGY_DEMOTED", summary="second", target_id="2", when=_ts(1)
    )
    third = build_entry(
        action_kind="RUNTIME_GATE_FLIP", summary="third", target_id="3", when=_ts(2)
    )
    # Append in chronological order.
    for e in (first, second, third):
        log.append(e)

    listed = log.list_recent(limit=10)
    assert [e.entry_id for e in listed] == [third.entry_id, second.entry_id, first.entry_id]


def test_list_recent_respects_limit(tmp_path):
    log = _log(tmp_path)
    for i in range(5):
        log.append(
            build_entry(
                action_kind="OTHER",
                summary=f"entry {i}",
                target_id=f"id-{i}",
                when=_ts(i),
            )
        )
    listed = log.list_recent(limit=2)
    assert len(listed) == 2
    # Newest two: i=4, i=3
    assert [e.target_id for e in listed] == ["id-4", "id-3"]


def test_file_is_append_only_not_rewritten(tmp_path):
    log = _log(tmp_path)
    e1 = build_entry(action_kind="OTHER", summary="one", target_id="1", when=_ts(0))
    log.append(e1)

    raw_after_first = log.path.read_text(encoding="utf-8")

    e2 = build_entry(action_kind="OTHER", summary="two", target_id="2", when=_ts(1))
    log.append(e2)

    raw_after_second = log.path.read_text(encoding="utf-8")
    # The second file must START with the first file's content verbatim
    # (append semantics, no rewrite).
    assert raw_after_second.startswith(raw_after_first)
    # And contain one additional line beyond it.
    lines = [ln for ln in raw_after_second.splitlines() if ln.strip()]
    assert len(lines) == 2
    decoded = [json.loads(ln) for ln in lines]
    assert decoded[0]["entry_id"] == e1.entry_id
    assert decoded[1]["entry_id"] == e2.entry_id


def test_stats_with_since_iso_drops_older_entries(tmp_path):
    log = _log(tmp_path)
    log.append(build_entry(action_kind="OTHER", summary="old", target_id="o", when=_ts(-30)))
    log.append(
        build_entry(
            action_kind="STRATEGY_PROMOTED",
            summary="new",
            target_id="n",
            reversible=True,
            when=_ts(30),
        )
    )
    cutoff = _ts(0).isoformat()
    stats = log.stats(since_iso=cutoff)
    assert stats["total"] == 1
    assert stats["by_kind"] == {"STRATEGY_PROMOTED": 1}
    assert stats["reversible_count"] == 1


def test_from_jsonl_dict_roundtrip_preserves_entry(tmp_path):
    entry = build_entry(
        action_kind="WEBHOOK_SUBSCRIBED",
        summary="webhook target registered",
        target_id="https://example.test/hook",
        target_label="slack",
        payload={"label": "slack"},
        reversible=True,
        reversal_hint="POST /webhook-notifications/unsubscribe",
        when=_ts(0),
    )
    payload = entry.to_jsonl_dict()
    rebuilt = OperatorAuditEntry.from_jsonl_dict(payload)
    assert rebuilt == entry
