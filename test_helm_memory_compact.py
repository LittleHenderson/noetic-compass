"""test_helm_memory_compact.py -- HELM memory compaction v1 (SPEC 7.115, DESIGN sections 3-6), FIX FIRST.

Written BEFORE helm_memory_compact.py existed (owner's word 2026-10-21: "Override the census floor. Start build v1 of
memory compaction now: rule capsules, behind HELM_MEMORY_COMPACT default OFF, FIX FIRST tests, 0 USD, and fix the
user_facts [:20] slip with a test in the same build."). Every test here failed on the thread head before the build.

What is checked, in plain words:
  - the switch is OFF by default and OFF means today's behaviour: the oldest turn is dropped from working memory;
  - ON: a turn that would be dropped is compacted instead into a CAPSULE (a CCE sentence that round-trips + its CAS
    text that compiles + 1..8 clues copied verbatim from the turns + pointers to cubes + a breadcrumb to the verbatim
    cold copy with its sha256 + a receipt); a capsule never holds a number; nothing is lost silently;
  - recall is fetch-first: EXACT only on a digest-checked original; a damaged copy is never EXACT (M1's H8);
  - a refresh question quotes a clue, invents nothing, carries no CAS token, is capped (2 per thread, 1 per item);
  - the fit check F1-F4 is a program; a capsule whose Atlas node does not match its clues is not served;
  - strengthening is four appends (mass, clues from the person's words, cube provenance CHECKED, Atlas side -> fact)
    and never changes the capsule's content; a strengthened item is not compacted again;
  - the Atlas files capsules on the possibility side under the thread's node and the lookup reads the anchor first;
  - the Eye is report-only: 0 writes; the brain's learned digest and every cube face are unchanged by memory work;
  - replay of the same turns gives the same receipts.
Run:  python -m pytest test_helm_memory_compact.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_memory  # noqa: E402
import helm_memory_compact as hmc  # noqa: E402
import helm_voice  # noqa: E402
from helm_memory import HELMConversationalMemory  # noqa: E402


# ----------------------------------------------------------------------------------------------- helpers
BEES = [
    ("USER_NARRATIVE", "My grandfather kept bees in the south of France"),
    ("USER_NARRATIVE", "The hives were counted every spring"),
    ("USER_NARRATIVE", "There were nine hives at the river site"),
    ("USER_NARRATIVE", "I still have his smoker"),
]
FILLER = [("GENERAL_KNOWLEDGE_INQUIRY", f"Tell me something about topic number {i}") for i in range(1, 40)]


class FakeBrain:
    """Stands in for the recipe brain: the only thing memory work may read is learned_digest()."""

    def __init__(self) -> None:
        self.state = {"a": {"bread": {"flour": "3/2"}}}

    def learned_digest(self) -> str:
        return hashlib.sha256(json.dumps(self.state, sort_keys=True).encode("utf-8")).hexdigest()


def _mem(tmp_path, on: bool, max_turns: int = 6, **kw) -> HELMConversationalMemory:
    mem = HELMConversationalMemory(session_id="t-compact", max_turns=max_turns, storage_dir=str(tmp_path / "log"))
    if on:
        hmc.attach(mem, cold_dir=str(tmp_path / "cold"), **kw)
    return mem


def _say(mem, intent, text, response="Noted."):
    if intent == "USER_NARRATIVE":
        mem.context.add_user_fact(text, turn_index=len(mem.turns) + 1)
    return mem.record_turn(text, text, intent, {}, response)


def _fill(mem, turns):
    for intent, text in turns:
        _say(mem, intent, text)


# ----------------------------------------------------------------------------------------------- the switch
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv("HELM_MEMORY_COMPACT", raising=False)
    assert hmc.compact_on() is False
    assert hmc.compact_on(True) is True


@pytest.mark.parametrize("value,expected", [("1", True), ("ON", True), ("true", True), ("yes", True), ("0", False), ("off", False), ("", False)])
def test_switch_env(monkeypatch, value, expected):
    monkeypatch.setenv("HELM_MEMORY_COMPACT", value)
    assert hmc.compact_on() is expected


def test_off_path_is_todays_fifo(tmp_path, monkeypatch):
    monkeypatch.delenv("HELM_MEMORY_COMPACT", raising=False)
    mem = _mem(tmp_path, on=False, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    assert len(mem.turns) == 6
    assert mem.turns[0].user_raw_text == BEES[2][1]  # the two oldest turns were dropped silently, as today
    assert getattr(mem, "compactor", None) is None


# ----------------------------------------------------------------------------------------------- compaction
def test_on_compacts_instead_of_dropping(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    comp = mem.compactor
    assert len(mem.turns) <= 6
    assert comp.capsules, "nothing was compacted"
    dropped_ids = set(range(1, 9)) - {t.turn_id for t in mem.turns}
    assert dropped_ids, "the budget did not bite"
    covered = set()
    for cap in comp.capsules:
        covered.update(cap.crumb["turn_ids"])
    assert dropped_ids <= covered, "a turn left working memory with no capsule covering it"
    assert len(comp.receipts) >= len(comp.capsules)


def test_capsule_shape_and_rules(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    cap = mem.compactor.capsules[0]
    # F1: the CAS text compiles; F2: the CCE sentence round-trips
    assert cap.cas["compiles"] is True
    assert cap.cas["round_trip"] is True
    assert cap.cas["notation"].startswith("^")
    # clues: 1..8, every clue copied verbatim (case-insensitive) from the compacted turns' own words
    assert 1 <= len(cap.clues) <= 8
    source = " ".join(t["user_raw_text"].lower() for t in hmc.read_cold(cap.crumb["cold_path"]))
    for clue in cap.clues:
        assert clue.lower() in source, clue
    # a capsule never holds a number
    assert not any(ch.isdigit() for ch in " ".join(cap.clues))
    assert not any(ch.isdigit() for ch in cap.cas["sentence"])
    # breadcrumb: the cold copy exists and its sha256 matches
    assert os.path.isfile(cap.crumb["cold_path"])
    with open(cap.crumb["cold_path"], "rb") as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == cap.crumb["sha256"]
    # receipt: sha256 over the five fields, present in the ledger
    assert cap.receipt in {r["receipt"] for r in mem.compactor.receipts}
    assert cap.atlas["side"] == "possibility"


def test_capsule_binds_cubes_and_cubes_unchanged(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    if mem.context.cube_store is None:
        pytest.skip("cube store not importable here")
    _fill(mem, BEES)                                       # four facts written by the chat path (legitimate writes)
    before = hmc.cube_faces_digest(mem.context.cube_store)
    _fill(mem, FILLER[:4])                                 # fillers only: the compaction fires, no fact is written
    cap = mem.compactor.capsules[0]
    assert cap.binds["cubes"], "the capsule binds no cube although the turns wrote user facts"
    for cid in cap.binds["cubes"]:
        assert mem.context.cube_store.get_cube(cid, view_profile="Authoring") is not None
    assert hmc.cube_faces_digest(mem.context.cube_store) == before  # HG-CUBE: no face changed


def test_brain_digest_unchanged_by_memory_work(tmp_path):
    brain = FakeBrain()
    mem = _mem(tmp_path, on=True, max_turns=6, brain=brain)
    d0 = brain.learned_digest()
    _fill(mem, BEES + FILLER[:4])
    hit = mem.compactor.recall("how many hives at the river site")
    assert brain.learned_digest() == d0  # HG-COEF
    assert mem.compactor.coefficient_digest_checks and all(c["equal"] for c in mem.compactor.coefficient_digest_checks)
    assert hit["label"] in hmc.LABELS


def test_active_thread_never_compacted(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    last_ids = {t.turn_id for t in mem.turns[-hmc.ACTIVE_TAIL:]}
    for cap in mem.compactor.capsules:
        assert not (set(cap.crumb["turn_ids"]) & last_ids)


def test_turn_ids_keep_counting_when_on(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:6])
    assert mem.turns[-1].turn_id == 10


# ----------------------------------------------------------------------------------------------- recall
def test_recall_fetch_first_exact(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    hit = mem.compactor.recall("what did I say about the river site")
    assert hit["label"] == "EXACT"
    assert hit["question"] is None
    assert any("river site" in t.lower() for t in hit["texts"])
    assert hit["lookup"]["anchor_first"] is True


def test_damaged_cold_copy_is_never_exact(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    cap = mem.compactor.capsules[0]
    with open(cap.crumb["cold_path"], "ab") as fh:
        fh.write(b"\n{\"planted\": \"corruption\"}\n")
    hit = mem.compactor.recall("grandfather bees")
    assert hit["label"] != "EXACT"
    assert hit["label"] in ("RECONSTRUCTED", "UNKNOWN")
    flags = mem.compactor.eye_report()
    assert any(f["kind"] == "DIGEST_FAILED" for f in flags)


def test_missing_cold_copy_rebuilds_or_unknown_and_asks_with_a_clue(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    cap = mem.compactor.capsules[0]
    os.remove(cap.crumb["cold_path"])
    hit = mem.compactor.recall("grandfather bees", will_act=True)
    assert hit["label"] in ("RECONSTRUCTED", "UNKNOWN")
    q = hit["question"]
    assert q, "a rebuilt memory that will be acted on must be confirmed by a question"
    assert any(clue.lower() in q.lower() for clue in cap.clues), q
    assert helm_voice.cas_tokens(q) == []
    assert q.count("?") == 1
    assert not any(ch.isdigit() for ch in q)


def test_nothing_matches_is_unknown_with_reason(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    hit = mem.compactor.recall("quantum chromodynamics lecture")
    assert hit["label"] == "UNKNOWN"
    assert hit["reason"]
    assert hit["question"] is None


def test_refresh_caps(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    comp = mem.compactor
    for cap in comp.capsules:
        os.remove(cap.crumb["cold_path"])
    asked = 0
    for _ in range(5):
        hit = comp.recall("grandfather bees", will_act=True)
        asked += 1 if hit["question"] else 0
    assert asked <= hmc.REFRESH_CAP_PER_THREAD
    # a "no" marks the item UNKNOWN and it is not asked again
    comp.answer(comp.capsules[0].capsule_id, "no, I don't remember")
    hit = comp.recall("grandfather bees", will_act=True)
    assert hit["question"] is None


# ----------------------------------------------------------------------------------------------- fit check
def test_fit_check_passes_on_clean_capsule(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    cap = mem.compactor.capsules[0]
    fit = mem.compactor.fit_check(cap)
    assert fit["F1_compile"] and fit["F2_round_trip"] and fit["F3_no_contradiction"] and fit["F4_atlas"]


def test_fit_check_f4_refuses_misfiled_capsule(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    cap = mem.compactor.capsules[0]
    cap.atlas["node"] = "thread-does-not-exist"
    os.remove(cap.crumb["cold_path"])
    fit = mem.compactor.fit_check(cap)
    assert fit["F4_atlas"] is False
    hit = mem.compactor.recall("grandfather bees")
    assert hit["label"] == "UNKNOWN"
    assert "fit" in hit["reason"].lower()


# ----------------------------------------------------------------------------------------------- strengthen
def test_strengthen_is_four_appends(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    comp = mem.compactor
    cap = comp.capsules[0]
    cas_before = dict(cap.cas)
    clues_before = list(cap.clues)
    mass_before = cap.mass["value"]
    receipts_before = len(comp.receipts)
    rec = comp.answer(cap.capsule_id, "Yes, the ones by the old mill")
    assert rec["strengthened"] is True
    assert cap.mass["value"] == mass_before + hmc.MASS_STEP
    assert cap.mass["confirmed"] == 1
    assert clues_before == cap.clues[: len(clues_before)]  # nothing removed
    assert "old mill" in cap.clues or "mill" in cap.clues
    assert len(cap.clues) <= 8
    assert cap.cas == cas_before  # content unchanged
    assert cap.atlas["side"] == "fact"
    assert len(comp.receipts) == receipts_before + 1
    if mem.context.cube_store is not None and cap.binds["cubes"]:
        cube = mem.context.cube_store.get_cube(cap.binds["cubes"][0], view_profile="Authoring")
        assert cube.provenance.source == "CHECKED"
        assert any(cap.capsule_id in r for r in cube.provenance.refs)


def test_strengthened_item_not_compacted_again(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    comp = mem.compactor
    cap = comp.capsules[0]
    comp.answer(cap.capsule_id, "yes")
    _fill(mem, FILLER[4:20])
    assert cap.capsule_id in {c.capsule_id for c in comp.capsules}
    assert comp.is_strengthened(cap.capsule_id)
    assert cap.crumb["turn_ids"] and all(comp.pinned_texts()), "strengthened originals stay available"


# ----------------------------------------------------------------------------------------------- atlas
def test_atlas_filing_and_lookup_order(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    comp = mem.compactor
    cap = comp.capsules[0]
    atlas = comp.atlas
    node = atlas.node(cap.atlas["node_id"])
    assert node.kind == "POSSIBILITY"
    assert atlas.node(cap.atlas["node"]).kind == "CONTEXT"
    hit = comp.recall("river site")
    assert hit["lookup"]["anchor_first"] is True
    assert hit["lookup"]["radius"] in (0, 1, 2, 4, 8)
    assert hit["lookup"]["candidates"] == 1


def test_three_candidates_asks_which_never_guesses(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=4)
    turns = [("USER_NARRATIVE", "We walked along the river on Sunday"),
             ("USER_NARRATIVE", "The river recipe uses trout and lemon"),
             ("USER_NARRATIVE", "My cousin lives by the river in Spain")]
    for intent, text in turns:
        _say(mem, intent, text)
        _fill(mem, FILLER[:3])
    _fill(mem, FILLER[3:7])  # push the third river turn out of working memory too
    comp = mem.compactor
    assert sum(1 for c in comp.capsules if any("river" in k.lower() for k in c.clues)) >= 3
    hit = comp.recall("tell me about the river")
    assert hit["label"] == "UNKNOWN"
    assert hit["question"] and "which" in hit["question"].lower()
    assert hit["lookup"]["candidates"] >= 3


# ----------------------------------------------------------------------------------------------- eye, replay
def test_eye_report_only(tmp_path):
    mem = _mem(tmp_path, on=True, max_turns=6)
    _fill(mem, BEES + FILLER[:4])
    comp = mem.compactor
    comp.housekeep()
    assert comp.eye_writes == 0
    assert isinstance(comp.eye_report(), list)


def test_replay_gives_same_receipts(tmp_path, monkeypatch):
    # a replay of the same ledger carries the same timestamps; here two fresh sessions, so the clock is frozen
    monkeypatch.setattr(helm_memory.time, "strftime", lambda fmt, *a: "2026-10-21T00:00:00Z")
    a = _mem(tmp_path / "a", on=True, max_turns=6)
    b = _mem(tmp_path / "b", on=True, max_turns=6)
    _fill(a, BEES + FILLER[:4])
    _fill(b, BEES + FILLER[:4])
    assert [c.receipt for c in a.compactor.capsules] == [c.receipt for c in b.compactor.capsules]
    assert [c.crumb["sha256"] for c in a.compactor.capsules] == [c.crumb["sha256"] for c in b.compactor.capsules]
