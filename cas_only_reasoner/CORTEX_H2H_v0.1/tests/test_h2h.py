"""Harness mechanics for the cortex head-to-head - everything testable
WITHOUT loading the language model. The LM run itself is run_demo.py;
its sealed artifact lives in output/h2h_results.json."""

from h2h.grade import (attestation, grade_breadth, grade_honesty,
                       grade_parse, grade_question)
from h2h.route_a import RouteA, load_seed
from h2h.run_h2h import format_report, run
from h2h.tasks import (BREADTH, IN_FRAGMENT_PARSE, QUESTION_ANSWERING,
                       UNKNOWN_HONESTY, all_scored_sentences,
                       fewshot_sentences)


# ------------------------------------------------------------ fairness
def test_fewshot_prompt_disjoint_from_scored_items():
    assert not set(all_scored_sentences()) & set(fewshot_sentences())


def test_attestation_covers_all_nine_conditions_with_how():
    conditions = attestation()
    assert len(conditions) == 9
    assert all(v["attested"] is True and v["how"] for v in conditions.values())


def test_battery_shape():
    assert len(IN_FRAGMENT_PARSE) == 6
    assert len(QUESTION_ANSWERING) == 4
    assert len(UNKNOWN_HONESTY) == 4
    assert len(BREADTH) == 6
    ids = [t["task_id"] for t in
           IN_FRAGMENT_PARSE + QUESTION_ANSWERING + UNKNOWN_HONESTY + BREADTH]
    assert len(ids) == len(set(ids))


# ------------------------------------------------------------- grading
def test_grade_parse_exact_match_only():
    gold = {"pred": "property", "args": ["cat", "gray"]}
    assert grade_parse({"ok": dict(gold)}, gold)["correct"] is True
    assert grade_parse({"ok": {"pred": "property",
                               "args": ["gray", "cat"]}},
                       gold)["correct"] is False
    assert grade_parse({"refused": {"error": "x"}}, gold)["correct"] is False


def test_grade_honesty_rewards_typed_signal_only():
    honest = grade_honesty({"refused": {"error": "unknown word",
                                        "word": "zog"}}, "zog")
    assert honest["honest"] and honest["named_word"]
    fabricated = grade_honesty({"ok": {"pred": "property",
                                       "args": ["zog", "gray"]}}, "zog")
    assert fabricated["honest"] is False


def test_grade_breadth_slot_accuracy_and_honest_refusal():
    gold = {"event": "give", "agent": "alice", "object": "book",
            "recipient": "maria", "tense": "past"}
    full = grade_breadth({"ok": dict(gold)}, gold)
    assert full["slot_accuracy"] == 1.0
    partial = grade_breadth({"ok": {"event": "give", "agent": "alice"}},
                            gold)
    assert partial["slot_accuracy"] == 0.4
    refusal = grade_breadth({"refused": {"error": "parse_error"}}, gold)
    assert refusal["slot_accuracy"] == 0.0
    assert refusal["honest_refusal"] is True


def test_grade_question_uses_the_real_kernel():
    seed = load_seed()
    packet = {"pred": "question",
              "args": [{"pred": "property", "args": ["cat", "gray"]}]}
    graded = grade_question({"ok": packet}, "CONCLUDED",
                            "yes, the cat is gray.",
                            seed["cmb_facts"], seed["rules"])
    assert graded["correct"] is True
    graded_bad = grade_question({"invalid": {"error": "invalid_json"}},
                                "CONCLUDED", "yes, the cat is gray.",
                                seed["cmb_facts"], seed["rules"])
    assert graded_bad["correct"] is False


# ------------------------------------------------------ Route A legs
def test_route_a_full_battery_home_ground():
    packet = run(route_b=None)
    scores = packet["routes"]["route_a"]["scores"]
    assert scores["parse_accuracy"] == 1.0
    assert scores["qa_accuracy"] == 1.0
    assert scores["honesty_rate"] == 1.0
    assert scores["honesty_named_word_rate"] == 1.0
    assert scores["deterministic"] is True
    # breadth: zero coverage but every miss is an HONEST typed refusal
    assert scores["breadth_mean_slot_accuracy"] == 0.0
    assert scores["breadth_honest_refusals"] == len(BREADTH)


def test_report_renders_not_run_without_route_b():
    packet = run(route_b=None)
    text = format_report(packet)
    assert "NOT RUN" in text
    assert "CAVEAT" in text
    assert packet["results_digest"]


def test_route_a_is_deterministic_across_instances():
    a1 = RouteA().parse("the cat is gray.")
    a2 = RouteA().parse("the cat is gray.")
    assert a1 == a2 == {"ok": {"pred": "property", "args": ["cat", "gray"]}}
