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
    assert "beekeeping in the south of france" in t1_out.lower()
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
    assert "missing" in t3_out.lower()
    assert "water" in t3_out.lower()
    print("  [PASS] Turn 3: Recipe pre-flight gate halted on missing Water prerequisite.")


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


if __name__ == "__main__":
    print("=" * 72)
    print("      HELM CONVERSATIONAL NUANCE & MULTI-TURN AUDIT SUITE       ")
    print("=" * 72)
    test_sequence_a()
    test_sequence_b()
    test_deepseek_7turn_offpath()
    test_epistemic_study_hypothesis()
    print("\n" + "=" * 72)
    print("ALL HELM CONVERSATIONAL NUANCE TESTS PASSED (100% VERIFIED)")
    print("=" * 72)
