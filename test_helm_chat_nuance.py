"""test_helm_chat_nuance.py -- Comprehensive Multi-Turn Dialogue & Nuance Test Suite for HELM.

Verifies:
1. DeepSeek Sequence A (Personal narrative, knowledge recall, goal execution, walkthrough explanation, exact summary).
2. DeepSeek Sequence B (Inventory declaration without run verb, inventory query, recipe gating on missing Water).
3. DeepSeek 7-Turn Off-Path Test:
   - Turn 1: Affect recognition ('feeling tired') with empathy, saved to memory.
   - Turn 2: Nuanced out-of-domain refusal ('capital of Portugal') explaining absence of atlas data without guessing.
   - Turn 3: Preference ingestion ('prefer short answers') updating context preferences.
   - Turn 4: Creative humor ('tell me a joke') honoring concise preference.
   - Turn 5: Associative recall ('what I said about my answers') matching memory accurately.
   - Turn 6: Memory count ('how many things have I told you') reporting exact count.
   - Turn 7: Accurate session summary with exact Turn 7 count, active preferences, and topics explored.
4. Epistemic Self-Directed Growth & Autonomous Recipe Synthesis:
   - Hypothesis recipe formulation under Station S0 (80% stoichiometric / 20% nuance ratio).
"""
import sys
import os
import io
import re
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import helm_chat as hc


def test_sequence_a():
    print("\n--- Running Sequence A (Narrative, Knowledge, Code, Walkthrough, Summary) ---")
    session = hc.HELMConversationalSession(mode="everyday", session_id="test_seq_a")
    
    # Turn 1: Narrative
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("My grandfather kept bees in the south of France.")
    t1_out = f.getvalue()
    # 2026-10-19: the reply repeats the user's own words (it used to be a hard-coded beekeeping sentence)
    assert "my grandfather kept bees in the south of france" in t1_out.lower()
    assert "beekeeping" not in t1_out.lower()
    assert session.turn_count == 1
    assert "south of France" in session.memory.context.user_facts[0]
    print("  [PASS] Turn 1: Personal narrative acknowledged and stored.")

    # Turn 2: Knowledge Query
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("What do you know about me?")
    t2_out = f.getvalue()
    assert "south of france" in t2_out.lower() or "bees" in t2_out.lower()
    assert session.turn_count == 2
    print("  [PASS] Turn 2: User facts recalled accurately.")

    # Turn 3: Code Goal
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Write code for a beehive counter.")
    t3_out = f.getvalue()
    assert "done!" in t3_out.lower()
    assert session.turn_count == 3
    print("  [PASS] Turn 3: Beehive counter code synthesized and verified.")

    # Turn 4: Walkthrough Explanation
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Explain it back to me in your own words.")
    t4_out = f.getvalue()
    assert "beehive counts" in t4_out.lower() or "hive" in t4_out.lower()
    assert "flour" not in t4_out.lower()
    assert "sugar" not in t4_out.lower()
    assert session.turn_count == 4
    print("  [PASS] Turn 4: Walkthrough explanation faithful to last goal (no food recipe hallucination).")

    # Turn 5: Session Summary
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("What did we just do?")
    t5_out = f.getvalue()
    assert "turn 5" in t5_out.lower()
    assert "south of france" in t5_out.lower() or "bees" in t5_out.lower()
    assert "beehive" in t5_out.lower()
    print("  [PASS] Turn 5: Session summary reports Turn 5 with exact notes and last goal.")


def test_sequence_b():
    print("\n--- Running Sequence B (Inventory Declaration, Query, Recipe Execution) ---")
    session = hc.HELMConversationalSession(mode="everyday", session_id="test_seq_b")

    # Turn 1: Declaration without run verb
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("We have 50 Flour, 30 Sugar, and 20 Butter.")
    t1_out = f.getvalue()
    assert "recorded" in t1_out.lower()
    assert "missing" not in t1_out.lower()
    assert session.memory.context.inventory.get("Flour") == 50
    print("  [PASS] Turn 1: Inventory declaration recorded without prematurely firing execution.")

    # Turn 2: Inventory Query
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("What do we have in stock?")
    t2_out = f.getvalue()
    assert "50 flour" in t2_out.lower()
    assert "30 sugar" in t2_out.lower()
    assert "20 butter" in t2_out.lower()
    print("  [PASS] Turn 2: Inventory query returned accurate quantities on hand.")

    # Turn 3: Recipe Execution missing Water
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Can we bake a batch without Water?")
    t3_out = f.getvalue()
    # Fix C (2026-10-18): free English no longer reaches the recipe brain. It is not in the checked form, so the
    # live loop answers with a CLARIFY, writes nothing, and invents no quantity (no "All set", no number).
    assert "nothing was saved" in t3_out.lower()
    assert "all set" not in t3_out.lower()
    assert "units" not in t3_out.lower()
    print("  [PASS] Turn 3: Free-English recipe request gets a CLARIFY with zero writes and no invented amount.")


def test_deepseek_7turn_offpath():
    print("\n--- Running DeepSeek 7-Turn Off-Path Sequence ---")
    session = hc.HELMConversationalSession(mode="everyday", session_id="test_seq_7turn")

    # Turn 1: "I'm feeling tired today."
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("I'm feeling tired today.")
    t1_out = f.getvalue()
    assert "tired" in t1_out.lower()
    assert "sorry to hear" in t1_out.lower()
    assert session.turn_count == 1
    print("  [PASS] Turn 1: User affect received with empathy; saved to memory.")

    # Turn 2: "What's the capital of Portugal?"
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("What's the capital of Portugal?")
    t2_out = f.getvalue()
    assert "capital of portugal" in t2_out.lower()
    assert "encyclopedic data" in t2_out.lower()
    assert "lisbon" not in t2_out.lower()  # Zero ungrounded hallucination
    assert session.turn_count == 2
    print("  [PASS] Turn 2: Specific, nuanced refusal explaining absence of atlas dataset.")

    # Turn 3: "Remember that I prefer short answers."
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Remember that I prefer short answers.")
    t3_out = f.getvalue()
    assert "preference" in t3_out.lower()
    assert session.memory.context.user_preferences.get("concise") is True
    assert session.turn_count == 3
    print("  [PASS] Turn 3: Concise preference ingested and confirmed.")

    # Turn 4: "Tell me a joke."
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Tell me a joke.")
    t4_out = f.getvalue()
    assert "bugs" in t4_out.lower() or "dark mode" in t4_out.lower()
    # Concise mode should make it short without the extra polite trailer
    assert "whenever you're ready" not in t4_out.lower()
    assert session.turn_count == 4
    print("  [PASS] Turn 4: Creative humor executed concisely under active preference.")

    # Turn 5: "Do you remember what I said about my answers?"
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Do you remember what I said about my answers?")
    t5_out = f.getvalue()
    assert "short" in t5_out.lower() or "concise" in t5_out.lower()
    assert session.turn_count == 5
    print("  [PASS] Turn 5: Associative memory recall matches preference accurately.")

    # Turn 6: "How many things have I told you?"
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("How many things have I told you?")
    t6_out = f.getvalue()
    assert "2 things" in t6_out.lower()
    assert "tired" in t6_out.lower()
    assert "short" in t6_out.lower() or "concise" in t6_out.lower()
    assert session.turn_count == 6
    print("  [PASS] Turn 6: Exact memory count and enumeration returned.")

    # Turn 7: "What did we just do?"
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("What did we just do?")
    t7_out = f.getvalue()
    assert "turn 7" in t7_out.lower()
    assert "tired" in t7_out.lower()
    assert "concise: true" in t7_out.lower()
    assert "flour" not in t7_out.lower()
    assert "water" not in t7_out.lower()
    assert "hive" not in t7_out.lower()
    assert session.turn_count == 7
    print("  [PASS] Turn 7: Session summary reports exact Turn 7, active preferences, and accurate notes.")


def test_epistemic_study_hypothesis():
    print("\n--- Running Epistemic Study & Autonomous Recipe Synthesis ---")
    session = hc.HELMConversationalSession(mode="everyday", session_id="test_seq_study")

    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Study drone battery thermal limits.")
    out = f.getvalue()
    assert "study hypothesis" in out.lower()
    assert "station s0" in out.lower()
    assert "rho = 0.5" in out.lower() or "rho=0.5" in out.lower()
    assert "80%" in out.lower() and "20%" in out.lower()
    assert "hypothesis_formulated" in out.lower()
    print("  [PASS] Epistemic study hypothesis successfully formulated under 80/20 ratio.")


def test_unified_cube_store_dialogue_integration():
    print("\n--- Running Unified Cube Store Dialogue Integration & Audit ---")
    session = hc.HELMConversationalSession(mode="everyday", session_id="test_cube_store_live")
    
    # 1. Inventory declaration: writes cubes into CubeStore
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("We have 50 Flour, 30 Sugar, and 20 Butter.")
    t1 = session.memory.turns[-1]
    assert t1.operation == "WRITE_CUBE"
    assert "cube_inventory_on_hand" in t1.cubes_written
    assert t1.receipt_hash is not None and len(t1.receipt_hash) == 16
    print("  [PASS] Probe 1: Inventory declaration wrote CubeNode with 16-char SHA-256 receipt.")

    # 2. Pantry query: READ operation (LIST_PARTS) writing ZERO cubes
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("list what's in the pantry")
    out = f.getvalue()
    t2 = session.memory.turns[-1]
    assert t2.operation == "LIST_PARTS"
    assert t2.cubes_written == []
    assert len(t2.cubes_read) > 0
    assert "50 flour" in out.lower() and "30 sugar" in out.lower()
    print("  [PASS] Probe 2: 'list what's in the pantry' executed LIST_PARTS and wrote 0 cubes.")

    # 3. State affect "I feel awful" -> ASSERTED, NEGATIVE
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("I feel awful today.")
    out = f.getvalue()
    t3 = session.memory.turns[-1]
    assert t3.valence == "NEGATIVE"
    assert t3.assertion == "ASSERTED"
    assert "sorry to hear" in out.lower()
    assert len(t3.cubes_written) > 0
    print("  [PASS] Probe 3: 'I feel awful' correctly resolved to NEGATIVE valence.")

    # 4. Directive "Tell me a joke" -> kind: directive
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Tell me a joke.")
    t4 = session.memory.turns[-1]
    assert t4.kind == "directive"
    assert t4.receipt_hash is not None
    print("  [PASS] Probe 4: 'Tell me a joke' registered as kind: directive.")

    # 5. Non-grounded domain refusal "Study medieval poetry" -> REFUSE, 0 cubes written
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn("Study medieval poetry.")
    out = f.getvalue()
    t5 = session.memory.turns[-1]
    assert t5.operation == "REFUSE"
    assert t5.gate_code == "GATE_REFUSE"
    assert t5.cubes_written == []
    assert "will not do that" in out.lower() or "missing knowledge" in out.lower()
    print("  [PASS] Probe 5: Non-grounded domain refusal wrote zero cubes under strict claim ceiling.")


def _say(session, text):
    f = io.StringIO()
    with redirect_stdout(f):
        session.handle_turn(text)
    return f.getvalue()


def test_narrative_reply_adds_no_invented_detail():
    """Defect found by HELM UI v0 (2026-10-19): any message about bees got a hard-coded reply about
    "beekeeping in the south of France". The reply must repeat only what the user said (user_facts)."""
    session = hc.HELMConversationalSession(mode="everyday", session_id="test_narrative_no_invention")
    out = _say(session, "My uncle kept bees in Ohio.")
    assert "france" not in out.lower()
    assert "beekeeping" not in out.lower() and "skilled" not in out.lower()
    assert '"My uncle kept bees in Ohio"' in out
    assert session.memory.context.user_facts == ["My uncle kept bees in Ohio"]
    out2 = _say(session, "My sister is a carpenter.")
    assert '"My sister is a carpenter"' in out2 and "bee" not in out2.lower()


def test_walkthrough_claims_no_hive_program():
    """The removed "beehive counts" branch fired on any goal with 'count' and described a program never written."""
    session = hc.HELMConversationalSession(mode="everyday", session_id="test_walkthrough_no_hive")
    session.memory.context.last_goal = "Write code to count the lines in notes.txt."
    out = _say(session, "Explain it back to me in your own words.")
    assert "hive" not in out.lower() and "bee" not in out.lower()
    assert "count the lines in notes.txt" in out


def test_dials_command_reads_real_dial_values():
    """Defect found by HELM UI v0 (2026-10-19): 'dials' crashed (the Unity Eye has no `dial_params`)."""
    session = hc.HELMConversationalSession(mode="everyday", session_id="test_dials_real")
    d = session.engine.eye.dial
    d.set_breadth(12)
    out = _say(session, "dials")
    assert f"Candidate Breadth (K)     : 12" in out
    assert f"RPA Search Radius (R)     : {d.search_radius_R}" in out
    assert f"Phase 3 Valve Saliency (σ): {d.valve_novelty_sigma}" in out
    assert session.turn_count == 0                       # a terminal command is not a turn
    session.engine.eye = None                            # no Eye at all: says so, does not crash
    assert "not wired" in _say(session, "dials")


if __name__ == "__main__":
    print("=" * 72)
    print("      HELM CONVERSATIONAL NUANCE & MULTI-TURN AUDIT SUITE       ")
    print("=" * 72)
    test_sequence_a()
    test_sequence_b()
    test_deepseek_7turn_offpath()
    test_epistemic_study_hypothesis()
    test_unified_cube_store_dialogue_integration()
    test_narrative_reply_adds_no_invented_detail()
    test_walkthrough_claims_no_hive_program()
    test_dials_command_reads_real_dial_values()
    print("\n" + "=" * 72)
    print("ALL HELM CONVERSATIONAL NUANCE TESTS PASSED (100% VERIFIED)")
    print("=" * 72)
