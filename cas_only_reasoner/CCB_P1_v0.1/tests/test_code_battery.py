"""CCB-P1 permanent battery - the goal's fifteen rows plus the exit
gate: sandbox law, compiler authority, walk-down diagnosis, minimal
repair, structural transfer, causal ablation, determinism."""

import json
import os

import pytest

from codeboard import (CodeStudent, ProcedureStore, SKILLS, SPECS,
                       adapt_code, algorithm_battery, examine,
                       first_divergence, make_mutants,
                       missing_prerequisites, run, static_gate,
                       teach, trace_run, validate_packet)
from codeboard.spec import DEV_SEED


def _packet(skill_id, **overrides):
    base = {"lesson_id": f"TEST_{skill_id}", "skill_id": skill_id,
            "teacher_model": "hand_authored_test_teacher",
            "teacher_revision": "test",
            "explanation": f"a lesson about {skill_id}",
            "provenance": "test_channel"}
    content = {
        "read_and_trace": {
            "strategy": "run the code one line at a time and write "
                        "down every variable after each line"},
        "sum_list": {
            "implementation": ("def sum_list(xs):\n"
                               "    total = 0\n"
                               "    for x in xs:\n"
                               "        total = total + x\n"
                               "    return total\n"),
            "common_bug": ("def sum_list(xs):\n"
                           "    total = 1\n"
                           "    for x in xs:\n"
                           "        total = total + x\n"
                           "    return total\n")},
        "reverse_string": {
            "implementation": ("def reverse_string(s):\n"
                               "    out = ''\n"
                               "    for ch in s:\n"
                               "        out = ch + out\n"
                               "    return out\n"),
            "common_bug": ("def reverse_string(s):\n"
                           "    out = ''\n"
                           "    for ch in s:\n"
                           "        out = out + ch\n"
                           "    return out\n")},
        "max_list": {
            "implementation": ("def max_list(xs):\n"
                               "    if len(xs) == 0:\n"
                               "        return None\n"
                               "    best = xs[0]\n"
                               "    for x in xs:\n"
                               "        if x > best:\n"
                               "            best = x\n"
                               "    return best\n"),
            "common_bug": ("def max_list(xs):\n"
                           "    best = 0\n"
                           "    for x in xs:\n"
                           "        if x > best:\n"
                           "            best = x\n"
                           "    return best\n")},
        "count_matching": {
            "implementation": (
                "def count_matching(xs, predicate_name):\n"
                "    count = 0\n"
                "    for x in xs:\n"
                "        if predicate_name == 'positive':\n"
                "            matched = x > 0\n"
                "        elif predicate_name == 'negative':\n"
                "            matched = x < 0\n"
                "        elif predicate_name == 'even':\n"
                "            matched = x % 2 == 0\n"
                "        else:\n"
                "            matched = x % 2 != 0\n"
                "        if matched:\n"
                "            count = count + 1\n"
                "    return count\n"),
            "common_bug": (
                "def count_matching(xs, predicate_name):\n"
                "    count = 1\n"
                "    for x in xs:\n"
                "        if predicate_name == 'positive':\n"
                "            matched = x > 0\n"
                "        elif predicate_name == 'negative':\n"
                "            matched = x < 0\n"
                "        elif predicate_name == 'even':\n"
                "            matched = x % 2 == 0\n"
                "        else:\n"
                "            matched = x % 2 != 0\n"
                "        if matched:\n"
                "            count = count + 1\n"
                "    return count\n")},
        "contracts_testing": {
            "strategy": "one passing example proves nothing: test "
                        "boundaries (empty, single, zero, "
                        "negative), test wrong usage expecting "
                        "errors, and check general properties"},
        "debug_repair": {
            "strategy": "reproduce the failure, trace both runs, "
                        "find the first state that differs from the "
                        "known-good run, patch only that cause, "
                        "then rerun everything"},
    }[skill_id]
    base.update(content)
    base.update(overrides)
    return base


CHAIN = ["read_and_trace", "sum_list", "reverse_string", "max_list",
         "count_matching", "contracts_testing", "debug_repair"]


def _teach_chain(path, upto="debug_repair"):
    for skill_id in CHAIN[:CHAIN.index(upto) + 1]:
        episode = teach(_packet(skill_id), path)
        assert episode["verdict"] == "PROMOTED", \
            f"{skill_id}: {episode['verdict']} " \
            f"{episode['stages'][-1]}"


# --------------------------------------------------- the sandbox law
def test_unsandboxed_file_write_rejected_before_execution():
    outcome = run("def f():\n    open('x','w').write('boom')\n",
                  "f", [])
    assert outcome["status"] == "FORBIDDEN_EFFECT"
    assert outcome["executed"] is False
    assert not os.path.exists("x")


def test_network_and_import_rejected():
    for code in ("import socket\ndef f():\n    return 1\n",
                 "import os\ndef f():\n    return 1\n",
                 "def f():\n    return __import__('os')\n"):
        outcome = run(code, "f", [])
        assert outcome["status"] == "FORBIDDEN_EFFECT"


def test_dunder_reach_and_eval_blocked():
    assert static_gate("def f(x):\n    return x.__class__\n")
    assert static_gate("def f():\n    return eval('1+1')\n")


def test_runaway_loop_dies_typed():
    outcome = run("def f():\n    while True:\n        pass\n",
                  "f", [], step_budget=5000)
    assert outcome["status"] == "STEP_BUDGET_EXCEEDED"


# ------------------------------------------- authority in the packet
def test_test_tampering_is_evaluator_contamination():
    for field in ("tests", "examiner", "protected", "threshold",
                  "verified", "promote"):
        defects = validate_packet(_packet("sum_list",
                                          **{field: True}))
        assert any("authority" in d or "contamination" in d
                   for d in defects)


def test_teacher_broken_code_rejected_despite_confidence(tmp_path):
    path = os.path.join(tmp_path, "p.json")
    teach(_packet("read_and_trace"), path)
    broken = _packet("sum_list", implementation=(
        "def sum_list(xs):\n"
        "    total = 0\n"
        "    for x in xs:\n"
        "        total = total - x\n"
        "    return total\n"))
    broken["teacher_confidence"] = "absolutely certain"
    episode = teach(broken, path)
    assert episode["verdict"] == "REJECTED_TESTS"


def test_bug_that_is_not_a_bug_is_rejected(tmp_path):
    path = os.path.join(tmp_path, "p.json")
    teach(_packet("read_and_trace"), path)
    packet = _packet("sum_list")
    packet["common_bug"] = packet["implementation"]
    episode = teach(packet, path)
    assert episode["verdict"] == "REJECTED_BUG_NOT_A_BUG"


# ------------------------------------------------ capability honesty
def test_unknown_skill_requests_instruction_never_invents():
    student = CodeStudent(ProcedureStore())
    result = student.implement("sum_list", SPECS["sum_list"])
    assert result["status"] == "CANNOT_MISSING_SKILL"
    assert "not learned" in result["detail"]


# -------------------------------------------- hidden edge case law
def test_hidden_edge_case_caught_beyond_public_examples():
    bug = ("def count_matching(xs, predicate_name):\n"
           "    count = 0\n"
           "    for x in xs:\n"
           "        if predicate_name == 'positive':\n"
           "            matched = x >= 0\n"
           "        elif predicate_name == 'negative':\n"
           "            matched = x < 0\n"
           "        elif predicate_name == 'even':\n"
           "            matched = x % 2 == 0\n"
           "        else:\n"
           "            matched = x % 2 != 0\n"
           "        if matched:\n"
           "            count = count + 1\n"
           "    return count\n")
    spec = SPECS["count_matching"]
    from codeboard.ladder import run_code
    for example in spec["public_examples"]:
        ok, value = run_code(bug, "count_matching", example["args"])
        assert ok and value == example["expected"]
    ok, detail = algorithm_battery("count_matching", bug, spec)
    assert not ok and detail["stage"] in ("boundary",
                                          "seeded:3301",
                                          "seeded:77007")


# ------------------------------------------------- the walk-down law
def test_off_by_one_first_incorrect_iteration_located():
    correct = ("def f(n):\n"
               "    total = 0\n"
               "    for i in range(n):\n"
               "        total = total + i\n"
               "    return total\n")
    off_by_one = ("def f(n):\n"
                  "    total = 0\n"
                  "    for i in range(1, n):\n"
                  "        total = total + i\n"
                  "    return total\n")
    buggy = trace_run(off_by_one, "f", [4])
    reference = trace_run(correct, "f", [4])
    verdict = first_divergence(buggy["events"],
                               reference["events"])
    assert verdict is not None
    assert verdict["variable"] == "i"
    assert verdict["got"] == "1" and verdict["reference"] == "0"


def test_wrong_variable_mutation_located_by_name():
    correct = ("def f(xs):\n"
               "    total = 0\n"
               "    count = 0\n"
               "    for x in xs:\n"
               "        total = total + x\n"
               "        count = count + 1\n"
               "    return total\n")
    wrong_var = ("def f(xs):\n"
                 "    total = 0\n"
                 "    count = 0\n"
                 "    for x in xs:\n"
                 "        total = total + x\n"
                 "        count = count + x\n"
                 "    return total\n")
    verdict = first_divergence(
        trace_run(wrong_var, "f", [[5, 2]])["events"],
        trace_run(correct, "f", [[5, 2]])["events"])
    assert verdict is not None
    assert verdict["variable"] == "count"


# ---------------------------------------------------- the full chain
def test_full_chain_promotes_and_every_stage_holds(tmp_path):
    path = os.path.join(tmp_path, "p.json")
    _teach_chain(path)
    store = ProcedureStore.load(path)
    assert store.promoted_ids() == sorted(CHAIN)
    # simple function synthesis + structural transfer, live
    student = CodeStudent(store)
    from codeboard.spec import TRANSFER_SPECS
    adapted = student.implement("sum_list",
                                TRANSFER_SPECS["sum_list"])
    assert adapted["status"] == "SOLVED"
    assert "def total_scores(scores):" in adapted["code"]
    ok, _ = algorithm_battery("sum_list", adapted["code"],
                              TRANSFER_SPECS["sum_list"])
    assert ok


def test_minimal_patch_and_regression(tmp_path):
    path = os.path.join(tmp_path, "p.json")
    _teach_chain(path)
    store = ProcedureStore.load(path)
    student = CodeStudent(store)
    code = store.get("sum_list")["formal"]["code"]
    mutant = make_mutants("sum_list", code, count=1)[0]

    def battery(candidate):
        return algorithm_battery("sum_list", candidate,
                                 SPECS["sum_list"])

    result = student.diagnose_and_repair("sum_list", mutant,
                                         [[1, 2, 3]], battery)
    assert result["status"] == "SOLVED"
    assert len(result["changed_lines"]) == 1        # minimal
    assert result["diagnosis"] is not None
    ok, _ = algorithm_battery("sum_list", result["patched_code"],
                              SPECS["sum_list"])
    assert ok                                        # regression


# ------------------------------------------------- causal ablation
def test_causal_ablation_reduces_only_the_ablated_skill(tmp_path):
    path = os.path.join(tmp_path, "p.json")
    _teach_chain(path, upto="reverse_string")
    store = ProcedureStore.load(path)
    store._ablate("sum_list", "causal ablation test")
    student = CodeStudent(store)
    gone = student.implement("sum_list", SPECS["sum_list"])
    assert gone["status"] == "CANNOT_MISSING_SKILL"
    kept = student.implement("reverse_string",
                             SPECS["reverse_string"])
    assert kept["status"] == "SOLVED"
    assert store.history[-1]["action"] == "ABLATED"  # never silent


# ------------------------------------------------- determinism law
def test_deterministic_replay_identical_episodes(tmp_path):
    a = teach(_packet("read_and_trace"),
              os.path.join(tmp_path, "a.json"))
    b = teach(_packet("read_and_trace"),
              os.path.join(tmp_path, "b.json"))
    assert a["episode_digest"] == b["episode_digest"]
    assert a["examiner_digest"] == b["examiner_digest"]


# ------------------------------------------------- prerequisite law
def test_prerequisites_and_tampered_store(tmp_path):
    path = os.path.join(tmp_path, "p.json")
    episode = teach(_packet("debug_repair"), path)
    assert episode["verdict"] == "REJECTED_PREREQUISITE_MISSING"
    assert "read_and_trace" in episode["stages"][0]["detail"]
    store = ProcedureStore()
    store.save(path)
    payload = json.load(open(path, encoding="utf-8"))
    payload["revision"] = 9
    json.dump(payload, open(path, "w", encoding="utf-8"))
    with pytest.raises(Exception, match="digest mismatch"):
        ProcedureStore.load(path)
