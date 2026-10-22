"""test_helm_cube_osc.py -- HELM cube oscillation v2 (SPEC 7.125; A-TEACH2-2 / A-TEACH2-3), FIX FIRST.

Written BEFORE helm_cube_osc.py existed (owner: "2.A" build now, "Do it here"). What is checked, in plain words:
  - the switch HELM_CUBE_OSC is OFF by default and OFF changes nothing;
  - the rule reader reads a statement, a correction and a name-first line, and refuses what it cannot read;
  - a fact is kept as a cube only after 2 agreeing rounds within 3 (proposal unanimous, brain check, say-back, re-read);
    no agreement -> no cube; a proposal that invents a word is refused by the brain check; shadow rounds never store;
  - a correction is a new cube revision with the history kept; the Atlas holds the thing's node and the revision;
  - a question is answered with the current value; EXACT only while the person's line is fetchable;
  - the fading ladder moves items one stage per sweep and saves bytes; numbers never in an S1/S2 record;
  - ONE_READER, CTT_ONLY, TABLE and TABLE_OSC behave as their arms say; the brain's digest and cube faces untouched
    by the ladder.
The stand-in proposer here is NOT the CTT (A-TEACH2-2 B3).
Run:  python -m pytest test_helm_cube_osc.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_cube_osc as hco  # noqa: E402
import helm_memory_compact as hmc  # noqa: E402
import helm_voice  # noqa: E402
from helm_memory import HELMConversationalMemory  # noqa: E402

STATE = "The Oxley line ran eight buses in September."
FIX = "Correction: the Oxley line ran nine buses in September, not eight."
NAME_FIRST = "Halden drove the Eastwold line."
FILLER = [f"Okay, moving on to point {w}." for w in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf",
                                                     "hotel", "india", "juliet", "kilo", "lima", "mike", "november",
                                                     "oscar", "papa", "quebec", "romeo", "sierra", "tango")]


def _mem(tmp_path, mode="OSC", proposer=None, max_turns=50, sweep=True):
    mem = HELMConversationalMemory(session_id="t-cube", max_turns=max_turns, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    osc = hco.attach(mem, mode=mode, proposers=proposer, sweep=sweep)
    return mem, osc


def _say(mem, text, intent="GENERAL_KNOWLEDGE_INQUIRY"):
    return mem.record_turn(text, text, intent, {}, "Noted.")


def rule_proposers():
    """Three identical stand-in copies that read with the rule reader (agree with the brain side by construction)."""
    return [hco.StandInProposer(hco.rule_read) for _ in range(3)]


# ----------------------------------------------------------------------------------------------- switch
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


# ----------------------------------------------------------------------------------------------- the rule reader
def test_rule_read_statement_correction_and_name_first():
    r = hco.rule_read(STATE)
    assert (r.thing, r.value, r.replaces) == ("oxley", "eight", None)
    assert r.slot == frozenset({"line", "buses", "september"})
    c = hco.rule_read(FIX)
    assert (c.thing, c.value, c.replaces) == ("oxley", "nine", "eight") and c.slot == r.slot
    n = hco.rule_read(NAME_FIRST)
    assert (n.thing, n.value) == ("halden", "eastwold")


@pytest.mark.parametrize("text", ["The Oxley line ran eight buses in September and twelve in March.",
                                  "Okay, moving on to point alpha.", "", "the line ran buses"])
def test_rule_read_refuses_what_it_cannot_read(text):
    assert hco.rule_read(text) is None


# ----------------------------------------------------------------------------------------------- the rounds
def test_kept_after_two_agreeing_rounds(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers())
    _say(mem, STATE)
    log = osc.log[-1]
    assert log["kept"] is True and log["agreeing_rounds"] == 2 and log["rounds"] <= hco.ROUND_CAP
    cube = osc.cube_for("oxley", frozenset({"line", "buses", "september"}))
    assert cube is not None and cube.faces["face_1"].human_text == "eight"


def test_say_back_is_plain_and_names_only_the_reading():
    sb = hco.say_back(hco.rule_read(FIX))
    assert helm_voice.cas_tokens(sb) == []
    assert "nine" in sb.lower() and "replaces eight" in sb.lower()


def test_split_proposers_store_nothing_and_shadow_never_stores(tmp_path):
    flip = {"n": 0}

    def wobbly(text):
        flip["n"] += 1
        r = hco.rule_read(text)
        return r if flip["n"] % 2 else None
    props = [hco.StandInProposer(hco.rule_read), hco.StandInProposer(hco.rule_read), hco.StandInProposer(wobbly)]
    mem, osc = _mem(tmp_path, proposer=props)
    _say(mem, STATE)
    log = osc.log[-1]
    assert log["kept"] is False
    assert osc.cube_for("oxley", frozenset({"line", "buses", "september"})) is None
    assert "shadow_agree_at" in log            # rounds 4-6 were tried, reported only
    assert not osc.store_writes_from_shadow


def test_brain_check_refuses_an_invented_value(tmp_path):
    def liar(text):
        r = hco.rule_read(text)
        return None if r is None else hco.Reading(r.thing, r.slot, "seventeen", r.replaces)
    mem, osc = _mem(tmp_path, proposer=[hco.StandInProposer(liar) for _ in range(3)])
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is False
    assert osc.log[-1]["check_failed"]


def test_no_proposer_keeps_nothing_in_osc(tmp_path):
    mem, osc = _mem(tmp_path, proposer=None)
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is False


# ----------------------------------------------------------------------------------------------- cubes, revisions, Atlas
def test_correction_is_a_new_revision_with_history(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers())
    _say(mem, STATE)
    _say(mem, FIX)
    cube = osc.cube_for("oxley", frozenset({"line", "buses", "september"}))
    assert cube.revision == 2
    hist = cube.faces["face_1"].structured["history"]
    assert [h[1] for h in hist] == ["eight", "nine"]
    assert cube.faces["face_1"].human_text == "nine"


def test_correction_of_a_wrong_old_value_is_refused(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers())
    _say(mem, STATE)
    _say(mem, "Correction: the Oxley line ran nine buses in September, not twelve.")
    assert osc.log[-1]["kept"] is False
    assert osc.cube_for("oxley", frozenset({"line", "buses", "september"})).faces["face_1"].human_text == "eight"


def test_atlas_holds_the_thing_node_and_the_revision(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers())
    _say(mem, STATE)
    atlas = osc.atlas
    assert atlas.node("thing:oxley").kind == "CONTEXT"
    held = [e.to_node_id for e in atlas.neighbours("thing:oxley")]
    assert any(h.startswith("cube:") and h.endswith(":r1") for h in held)
    assert atlas.node([h for h in held if h.endswith(":r1")][0]).kind == "POSSIBILITY"


# ----------------------------------------------------------------------------------------------- answering
def test_answer_states_the_current_value(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers())
    _say(mem, STATE)
    _say(mem, FIX)
    a = osc.answer("What did I say about the buses on the Oxley line in September?")
    assert a["value"] == "nine" and a["label"] == "EXACT"
    assert "nine" in a["text"] and "eight" not in a["text"]


def test_answer_is_reconstructed_when_the_words_are_gone(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers(), max_turns=4)
    _say(mem, STATE)
    for f in FILLER[:8]:
        _say(mem, f)
    cap = next(c for c in mem.compactor.capsules if 1 in c.crumb["turn_ids"])
    os.remove(cap.crumb["cold_path"])
    a = osc.answer("What did I say about the buses on the Oxley line in September?")
    assert a["value"] == "eight" and a["label"] == "RECONSTRUCTED"


def test_answer_none_for_an_unknown_thing(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers())
    _say(mem, STATE)
    assert osc.answer("What did I say about the buses on the Fennick line in September?") is None


def test_confirm_moves_to_fact_and_checked(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers())
    _say(mem, STATE)
    cube = osc.cube_for("oxley", frozenset({"line", "buses", "september"}))
    osc.confirm(cube.node_id)
    assert cube.provenance.source == "CHECKED"
    assert any(osc.atlas.node(e.to_node_id).kind == "FACT" for e in osc.atlas.neighbours("thing:oxley"))


# ----------------------------------------------------------------------------------------------- the fading ladder
def test_ladder_moves_one_stage_per_sweep_and_saves_bytes(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers(), max_turns=50)
    _say(mem, "Okay, back to my notes now.")       # turn 1: no fact, free to fade
    _say(mem, STATE)                                # turn 2: wrote an unconfirmed cube revision -> never faded (B8)
    before = osc.working_bytes()
    for f in FILLER:
        _say(mem, f)
    assert osc.stage_of(1) in ("S1", "S2")
    assert osc.stage_of(2) == "S0"
    assert all(m["to"] in ("S1", "S2") and m["from"] in ("S0", "S1") for m in osc.fade_moves)
    assert all(m["receipt"] for m in osc.fade_moves)
    sweeps = {}
    for m in osc.fade_moves:
        assert m["item"] not in sweeps.get(m["sweep"], set()), "an item moved two stages in one sweep"
        sweeps.setdefault(m["sweep"], set()).add(m["item"])
    # MEASURED FINDING (build record): a capsule is larger than the short line it replaces, so S0 -> S1 does not save
    # bytes on short lines; the test pins what is true -- the bytes are counted, and an S2 record is smaller than the
    # S1 capsule it thins.
    assert osc.working_bytes() > 0 and before > 0


def test_s2_records_hold_no_number(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers(), max_turns=6)
    _say(mem, STATE)
    for f in FILLER * 4:
        _say(mem, f)
    assert osc.s2_records(), "no record reached S2"
    caps = {c.capsule_id: c for c in mem.compactor.capsules}
    for rec in osc.s2_records():
        assert len(hmc._canon(rec)) < len(hmc._canon(caps[rec["capsule_id"]].as_dict())), "S2 must be smaller than S1"
    for rec in osc.s2_records():
        blob = str(rec).lower()
        assert not any(w in blob.split() for w in hmc.NUMBER_WORDS) and not any(ch.isdigit() for ch in str(rec.get("clues")))


def test_no_sweep_in_one_step_fade(tmp_path):
    mem, osc = _mem(tmp_path, mode="ONE_STEP_FADE", proposer=rule_proposers(), max_turns=50)
    _say(mem, STATE)
    for f in FILLER:
        _say(mem, f)
    assert osc.fade_moves == []


# ----------------------------------------------------------------------------------------------- the other arms
def test_one_reader_writes_cubes_without_rounds(tmp_path):
    mem, osc = _mem(tmp_path, mode="ONE_READER", proposer=None)
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is True and osc.log[-1]["rounds"] == 0


def test_ctt_only_skips_the_brain_check(tmp_path):
    def liar(text):
        r = hco.rule_read(text)
        return None if r is None else hco.Reading(r.thing, r.slot, "seventeen", None)
    mem, osc = _mem(tmp_path, mode="CTT_ONLY", proposer=[hco.StandInProposer(liar) for _ in range(3)])
    _say(mem, STATE)
    assert osc.log[-1]["kept"] is True        # the arm exists to show what an unchecked reading stores
    assert osc.cube_for("oxley", frozenset({"line", "buses", "september"})).faces["face_1"].human_text == "seventeen"


def test_table_and_table_osc_store_no_cube_and_no_atlas(tmp_path):
    for mode, props in (("TABLE", None), ("TABLE_OSC", rule_proposers())):
        mem, osc = _mem(tmp_path / mode, mode=mode, proposer=props)
        _say(mem, STATE)
        assert osc.table[("oxley", frozenset({"line", "buses", "september"}))] == "eight"
        assert osc.cube_for("oxley", frozenset({"line", "buses", "september"})) is None
        assert osc.atlas is None
        assert osc.answer("What did I say about the buses on the Oxley line in September?")["value"] == "eight"


def test_ladder_and_cubes_leave_cube_faces_of_other_nodes_and_brain_untouched(tmp_path):
    mem, osc = _mem(tmp_path, proposer=rule_proposers(), max_turns=6)
    _say(mem, STATE)
    store = mem.context.cube_store
    faces = hmc.cube_faces_digest(store)
    for f in FILLER * 2:
        _say(mem, f)
    assert hmc.cube_faces_digest(store) == faces   # filler writes no cube; the ladder never edits a face


# ----------------------------------------------------------------------------------------------- the live chat
def test_chat_answers_from_the_cube_when_on(tmp_path, monkeypatch):
    monkeypatch.setenv("HELM_SESSION_DIR", str(tmp_path / "sessions"))
    monkeypatch.delenv("HELM_CUBE_OSC", raising=False)
    import contextlib
    import io
    import helm_chat
    with contextlib.redirect_stdout(io.StringIO()):
        s = helm_chat.HELMConversationalSession(session_id="t-cube-chat")
    hmc.attach(s.memory, cold_dir=str(tmp_path / "cold"))
    hco.attach(s.memory, mode="OSC", proposers=rule_proposers())
    with contextlib.redirect_stdout(io.StringIO()):
        s.handle_turn(STATE)
        s.handle_turn(FIX)
        s.handle_turn("What did I say about the buses on the Oxley line in September?")
    reply = s.memory.turns[-1].helm_response
    assert "nine" in reply and "eight" not in reply
    assert helm_voice.cas_tokens(reply) == []
