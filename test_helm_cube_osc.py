"""test_helm_cube_osc.py -- HELM cube oscillation v2, REWORKED onto the existing Cube Node Schema and cube store
(SPEC 7.125; A-TEACH2-4), FIX FIRST.

Rewritten BEFORE the rework code (owner: "Yes: rework v2 onto the existing Cube Node Schema and cube store (things as
cubes, facts as branches with commonality, answers through the three operations, no second parser)"). In plain words:
  - the switch HELM_CUBE_OSC is OFF by default and OFF changes nothing;
  - there is NO parser inside HELM: readings come from the proposer interface only (the exam's rule reader lives in
    docs/working/helm_cube_oscillation_v1/teach2_rule_reader.py and feeds the stand-in proposer used here, NOT the CTT);
  - a kept fact makes THINGS into schema cubes (six faces; face_1 named; face_2..face_6, incl. face_3 analogy, unknown
    with an explanation, never invented) and the FACT into a branch whose commonality says what the two nodes share;
  - a correction is a newer branch (the history stays); two different facts between the same two nodes both stand;
  - answers come through LIST_PARTS / FIND_SHARED_PART / REACHED_VIA and cite the operation;
  - the rounds, the shadow, the brain-side check, the Atlas filing and the fading ladder keep working.
Run:  python -m pytest test_helm_cube_osc.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, "docs", "working", "helm_cube_oscillation_v1"),
          os.path.join(HERE, "docs", "working", "noetic_council", "cube_store")):
    if p not in sys.path:
        sys.path.insert(0, p)

import helm_cube_osc as hco  # noqa: E402
import helm_memory_compact as hmc  # noqa: E402
import helm_voice  # noqa: E402
import teach2_rule_reader as trr  # noqa: E402  (exam side; NOT inside HELM)
from helm_memory import HELMConversationalMemory  # noqa: E402

STATE = "The Oxley line ran eight buses in September."
FIX = "Correction: the Oxley line ran nine buses in September, not eight."
NAME_FIRST = "Halden drove the Eastwold line."
ENDS_A = "The Oxley line ended at Moorcroft."
ENDS_B = "The Eastwold line ended at Moorcroft."
FILLER = [f"Okay, moving on to point {w}." for w in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf",
                                                     "hotel", "india", "juliet", "kilo", "lima", "mike", "november",
                                                     "oscar", "papa", "quebec", "romeo", "sierra", "tango")]
SLOT = frozenset({"line", "buses", "september"})


def stand_in():
    """Three identical stand-in proposer copies that read with the exam's rule reader. NOT the CTT."""
    return [hco.StandInProposer(trr.rule_read) for _ in range(3)]


def _mem(tmp_path, mode="OSC", proposer="stand_in", max_turns=50, sweep=True, reader=None):
    mem = HELMConversationalMemory(session_id="t-cube", max_turns=max_turns, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    props = stand_in() if proposer == "stand_in" else proposer
    # these tests exercise the ladder path (per-4-turn sweep, turn budget); the size-limit path is test_helm_cube_tiers.py
    osc = hco.attach(mem, mode=mode, proposers=props, sweep=sweep, reader=reader, limit_bytes=None)
    return mem, osc


def _say(mem, text, intent="GENERAL_KNOWLEDGE_INQUIRY"):
    return mem.record_turn(text, text, intent, {}, "Noted.")


def _store(mem):
    return mem.context.cube_store


# ----------------------------------------------------------------------------------------------- switch, no parser
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv("HELM_CUBE_OSC", raising=False)
    assert hco.cube_osc_mode() is None


@pytest.mark.parametrize("value,mode", [("1", "OSC"), ("ON", "OSC"), ("OSC", "OSC"), ("ONE_READER", "ONE_READER"),
                                        ("CTT_ONLY", "CTT_ONLY"), ("TABLE", "TABLE"), ("TABLE_OSC", "TABLE_OSC"),
                                        ("ONE_STEP_FADE", "ONE_STEP_FADE"), ("0", None), ("off", None), ("", None)])
def test_switch_modes(monkeypatch, value, mode):
    monkeypatch.setenv("HELM_CUBE_OSC", value)
    assert hco.cube_osc_mode() == mode


def test_off_changes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("HELM_CUBE_OSC", raising=False)
    mem = HELMConversationalMemory(session_id="t-off", max_turns=6, storage_dir=str(tmp_path / "log"))
    assert getattr(mem, "cube_osc", None) is None
    for t in [STATE] + FILLER[:7]:
        _say(mem, t)
    assert len(mem.turns) == 6


def test_no_parser_inside_helm():
    assert not hasattr(hco, "rule_read"), "the rule reader must live on the exam side (A-TEACH2-4 R5)"


def test_exam_reader_reads_and_refuses():
    r = trr.rule_read(STATE)
    assert (r.thing, r.value, r.replaces, r.slot) == ("oxley", "eight", None, SLOT)
    c = trr.rule_read(FIX)
    assert (c.value, c.replaces) == ("nine", "eight")
    assert (trr.rule_read(NAME_FIRST).thing, trr.rule_read(NAME_FIRST).value) == ("halden", "eastwold")
    assert trr.rule_read("Okay, moving on to point alpha.") is None


# ----------------------------------------------------------------------------------------------- things are cubes
def test_things_are_schema_cubes_with_six_faces(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, STATE)
    st = _store(mem)
    for name in ("oxley", "september"):
        cube = st.nodes["thing_" + name]
        assert cube.core.label.lower() == name and cube.core.kind == "instance"
        assert set(cube.faces) == {f"face_{i}" for i in range(1, 7)}
        assert cube.faces["face_1"].availability == "populated"
        assert cube.faces["face_1"].structured["canonical_name"] == name
        for i in range(2, 7):
            f = cube.faces[f"face_{i}"]
            assert f.availability == "unknown" and f.human_text, "an unknown face must carry its explanation"
        assert cube.faces["face_3"].availability == "unknown", "the analogy face is never invented"
        assert cube.provenance.source == "USER_SAID"


# ----------------------------------------------------------------------------------------------- facts are branches
def test_a_fact_is_a_branch_whose_commonality_is_what_the_two_share(tmp_path):
    mem, osc = _mem(tmp_path)
    turn = _say(mem, STATE)
    br = [b for b in _store(mem).branches if b.source_node_id == "thing_oxley"]
    assert len(br) == 1
    b = br[0]
    assert b.target_node_id == "thing_september" and b.predicate == "contains"
    assert b.commonality["kind"] == "buses line"
    assert b.commonality["referent"] == "eight" and b.commonality["amount"] == "eight"
    assert b.provenance_refs == [f"turn:{turn.turn_id}"]


def test_correction_is_a_newer_branch_and_the_history_stays(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, STATE)
    _say(mem, FIX)
    br = [b for b in _store(mem).branches if b.source_node_id == "thing_oxley"]
    assert [b.commonality["referent"] for b in br] == ["eight", "nine"]
    a = osc.answer("What did I say about the buses on the Oxley line in September?")
    assert a["value"] == "nine" and a["operation"] == "LIST_PARTS"
    assert "nine" in a["text"] and "eight" not in a["text"]


def test_two_different_facts_between_the_same_two_nodes_both_stand(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, NAME_FIRST)
    _say(mem, "Halden repaired the Eastwold line.")
    import operations
    parts = operations.list_parts(_store(mem), "thing_halden").output
    kinds = sorted(p["commonality"]["kind"] for p in parts)
    assert kinds == ["drove line", "line repaired"]


def test_a_wrong_old_value_is_refused(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, STATE)
    _say(mem, "Correction: the Oxley line ran nine buses in September, not twelve.")
    assert osc.log[-1]["kept"] is False
    assert osc.answer("What did I say about the buses on the Oxley line in September?")["value"] == "eight"


def test_pantry_branches_behave_as_before(tmp_path):
    """The two additive operation changes keep the pantry's kind-less branches exactly as they were."""
    import operations
    from cube import Branch
    mem, osc = _mem(tmp_path)
    st = _store(mem)
    _say(mem, STATE)
    st.write_branch(Branch(branch_id="b1", context_id=st.context_id, source_node_id="thing_oxley", predicate="contains",
                           target_node_id="thing_september", commonality={"amount": "3", "unit": "x"}))
    out = operations.list_parts(st, "thing_oxley").output
    assert any(p["amount"] == "3" for p in out) and any(p["commonality"].get("kind") == "buses line" for p in out)


# ----------------------------------------------------------------------------------------------- the three operations
def test_who_question_answers_with_the_other_node(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, NAME_FIRST)
    a = osc.answer("What did I say about who drove the Eastwold line?")
    assert a["value"] == "halden" and "Halden" in a["text"] and a["operation"] == "LIST_PARTS"


def test_find_shared_part_is_what_two_things_have_in_common(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, ENDS_A)
    _say(mem, ENDS_B)
    c = osc.common("oxley", "eastwold")
    assert c["operation"] == "FIND_SHARED_PART" and c["shared"] == ["moorcroft"]


def test_reached_via_direct(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, ENDS_A)
    r = osc.related("oxley", "moorcroft")
    assert r["operation"] == "REACHED_VIA" and r["output"] == "direct"


def test_answer_none_for_an_unknown_thing(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, STATE)
    assert osc.answer("What did I say about the buses on the Fennick line in September?") is None


def test_answer_is_reconstructed_when_the_words_are_gone(tmp_path):
    mem, osc = _mem(tmp_path, max_turns=4)
    _say(mem, STATE)
    for f in FILLER[:8]:
        _say(mem, f)
    cap = next(c for c in mem.compactor.capsules if 1 in c.crumb["turn_ids"])
    os.remove(cap.crumb["cold_path"])
    a = osc.answer("What did I say about the buses on the Oxley line in September?")
    assert a["value"] == "eight" and a["label"] == "RECONSTRUCTED"


def test_confirm_makes_a_checked_revision_and_a_fact_node(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, STATE)
    osc.confirm("oxley")
    cube = _store(mem).nodes["thing_oxley"]
    assert cube.provenance.source == "CHECKED" and cube.revision == 2
    assert any(osc.atlas.node(e.to_node_id).kind == "FACT" for e in osc.atlas.neighbours("thing:oxley"))


# ----------------------------------------------------------------------------------------------- the rounds
def test_kept_after_two_agreeing_rounds(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, STATE)
    log = osc.log[-1]
    assert log["kept"] is True and log["agreeing_rounds"] == 2 and log["rounds"] <= hco.ROUND_CAP


def test_say_back_is_plain():
    sb = hco.say_back(trr.rule_read(FIX))
    assert helm_voice.cas_tokens(sb) == [] and "nine" in sb.lower() and "replaces eight" in sb.lower()


def test_split_proposers_store_nothing_and_shadow_never_stores(tmp_path):
    flip = {"n": 0}

    def wobbly(text):
        flip["n"] += 1
        r = trr.rule_read(text)
        return r if flip["n"] % 2 else None
    props = [hco.StandInProposer(trr.rule_read), hco.StandInProposer(trr.rule_read), hco.StandInProposer(wobbly)]
    mem, osc = _mem(tmp_path, proposer=props)
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is False and "shadow_agree_at" in osc.log[-1]
    assert not _store(mem).branches and osc.store_writes_from_shadow == 0


def test_brain_check_refuses_an_invented_value(tmp_path):
    def liar(text):
        r = trr.rule_read(text)
        return None if r is None else hco.Reading(r.thing, r.slot, "seventeen", r.replaces)
    mem, osc = _mem(tmp_path, proposer=[hco.StandInProposer(liar) for _ in range(3)])
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is False and osc.log[-1]["check_failed"]


def test_no_proposer_keeps_nothing_in_osc(tmp_path):
    mem, osc = _mem(tmp_path, proposer=None)
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is False and not _store(mem).branches


def test_atlas_files_the_thing_and_the_fact(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, STATE)
    assert osc.atlas.node("thing:oxley").kind == "CONTEXT"
    held = [e.to_node_id for e in osc.atlas.neighbours("thing:oxley")]
    assert any(osc.atlas.node(h).kind == "POSSIBILITY" for h in held)


# ----------------------------------------------------------------------------------------------- the fading ladder
def test_ladder_moves_one_stage_per_sweep_and_protects_unconfirmed_facts(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, "Okay, back to my notes now.")
    _say(mem, STATE)
    for f in FILLER:
        _say(mem, f)
    assert osc.stage_of(1) in ("S1", "S2") and osc.stage_of(2) == "S0"
    sweeps = {}
    for m in osc.fade_moves:
        assert m["receipt"] and m["item"] not in sweeps.get(m["sweep"], set())
        sweeps.setdefault(m["sweep"], set()).add(m["item"])


def test_s2_records_are_smaller_than_s1_and_hold_no_number(tmp_path):
    mem, osc = _mem(tmp_path, max_turns=6)
    _say(mem, STATE)
    for f in FILLER * 4:
        _say(mem, f)
    assert osc.s2_records()
    caps = {c.capsule_id: c for c in mem.compactor.capsules}
    for rec in osc.s2_records():
        assert len(hmc._canon(rec)) < len(hmc._canon(caps[rec["capsule_id"]].as_dict()))
        assert not any(w in str(rec).lower().split() for w in hmc.NUMBER_WORDS)


def test_no_sweep_in_one_step_fade(tmp_path):
    mem, osc = _mem(tmp_path, mode="ONE_STEP_FADE")
    _say(mem, STATE)
    for f in FILLER:
        _say(mem, f)
    assert osc.fade_moves == []


# ----------------------------------------------------------------------------------------------- the other arms
def test_one_reader_writes_branches_from_the_exam_reader(tmp_path):
    mem, osc = _mem(tmp_path, mode="ONE_READER", proposer=None, reader=trr.rule_read)
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is True and osc.log[-1]["rounds"] == 0
    assert any(b.target_node_id == "thing_september" for b in _store(mem).branches)


def test_one_reader_without_a_reader_stores_nothing(tmp_path):
    mem, osc = _mem(tmp_path, mode="ONE_READER", proposer=None, reader=None)
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is False


def test_ctt_only_skips_the_brain_check(tmp_path):
    def liar(text):
        r = trr.rule_read(text)
        return None if r is None else hco.Reading(r.thing, r.slot, "seventeen", None)
    mem, osc = _mem(tmp_path, mode="CTT_ONLY", proposer=[hco.StandInProposer(liar) for _ in range(3)])
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is True


def test_table_and_table_osc_store_no_cube_and_no_branch(tmp_path):
    for mode, props, reader in (("TABLE", None, trr.rule_read), ("TABLE_OSC", "stand_in", None)):
        mem, osc = _mem(tmp_path / mode, mode=mode, proposer=props, reader=reader)
        _say(mem, STATE)
        assert osc.table[("oxley", SLOT)] == "eight"
        assert not _store(mem).branches and "thing_oxley" not in _store(mem).nodes and osc.atlas is None
        assert osc.answer("What did I say about the buses on the Oxley line in September?")["value"] == "eight"


# ----------------------------------------------------------------------------------------------- the live chat
def test_chat_answers_through_the_store_when_on(tmp_path, monkeypatch):
    monkeypatch.setenv("HELM_SESSION_DIR", str(tmp_path / "sessions"))
    monkeypatch.delenv("HELM_CUBE_OSC", raising=False)
    import contextlib
    import io
    import helm_chat
    with contextlib.redirect_stdout(io.StringIO()):
        s = helm_chat.HELMConversationalSession(session_id="t-cube-chat")
    hmc.attach(s.memory, cold_dir=str(tmp_path / "cold"))
    hco.attach(s.memory, mode="OSC", proposers=stand_in())
    with contextlib.redirect_stdout(io.StringIO()):
        s.handle_turn(STATE)
        s.handle_turn(FIX)
        s.handle_turn("What did I say about the buses on the Oxley line in September?")
    reply = s.memory.turns[-1].helm_response
    assert "nine" in reply and "eight" not in reply and helm_voice.cas_tokens(reply) == []
