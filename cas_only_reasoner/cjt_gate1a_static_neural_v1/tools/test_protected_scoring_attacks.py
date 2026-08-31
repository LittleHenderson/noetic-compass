"""test_protected_scoring_attacks.py -- the section-6 protected-evaluation attacks."""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from exec.protected_eval import run_protected_evaluation  # noqa: E402
from exec.protected_scoring import (PREDICTION_FORBIDDEN_KEYS, GoldScorer,  # noqa: E402
                                    ScoringViolation, build_prediction_input)


def load_records(n=20):
    lines = (PKG / "data" / "candidate" / "train.jsonl").read_text(
        encoding="utf-8").splitlines()[:n]
    return [json.loads(x) for x in lines]


def test_arbitrary_evaluator_callback_does_not_exist():
    params = inspect.signature(run_protected_evaluation).parameters
    assert "evaluate_arm_seed" not in params, "the callback is back"
    for p in params.values():
        assert "callback" not in p.name and "evaluator" not in p.name
    print("PASS test_arbitrary_evaluator_callback_does_not_exist")


def test_prediction_path_cannot_read_answer_or_trace():
    verbs = {v: i % 4 for i, v in enumerate(
        ["drawn", "pulled", "felt", "captured", "withdrew", "repelled",
         "recoiled", "backed", "broke", "lay", "split", "made",
         "brought", "thought", "reminded", "summoned"])}
    for rec in load_records():
        for arm in ("S0", "S2", "S3", "S4", "S5", "S6", "S7"):
            ex = build_prediction_input(rec, arm, verbs)
            leaked = set(ex) & PREDICTION_FORBIDDEN_KEYS
            assert not leaked, f"{arm}: leaked {leaked}"
            assert "answer" not in ex and "answer_index" not in ex
            assert "seed_trace" not in ex and "idea_labels" not in ex
    print("PASS test_prediction_path_cannot_read_answer")
    print("PASS test_prediction_path_cannot_read_seed_trace")


def test_prediction_path_receives_profiles_not_raw_gold_labels():
    from exec.labels import one_hot
    rec = load_records(1)[0]
    ex = build_prediction_input(rec, "S3")
    assert ex["profiles"] == [one_hot(c) for c in rec["idea_labels"]]
    assert all(isinstance(v, list) and len(v) == 4 for v in ex["profiles"]), \
        "profiles must be the registered 4-dim tensors, not label strings"
    ex4 = build_prediction_input(rec, "S4")
    assert ex4["profiles"] != ex["profiles"], "S4 corruption not applied"
    print("PASS test_prediction_path_receives_profiles_not_raw_gold_labels")


def test_scorer_cannot_modify_predictions():
    recs = load_records(3)
    scorer = GoldScorer(recs)
    pred = 2
    scorer.score(recs[0]["passage_id"], pred, "S3", 11, "aa" * 32)
    assert pred == 2 and scorer.provenance[0]["predicted_candidate_index"] == 2
    sig = inspect.signature(GoldScorer.score).parameters
    assert list(sig) == ["self", "passage_id", "predicted_candidate_index",
                        "arm", "seed", "checkpoint_sha256"], \
        "the scorer receives integers and ids only"
    print("PASS test_scorer_cannot_modify_predictions")


def test_fabricated_all_correct_vector_refused():
    """There is no path that accepts a caller-provided correctness vector: the
    only correctness source is GoldScorer.score, which requires a real
    prediction and a checkpoint digest per passage."""
    params = inspect.signature(run_protected_evaluation).parameters
    for p in params:
        assert "correct" not in p and "vector" not in p, \
            f"suspicious injectable parameter {p}"
    scorer = GoldScorer(load_records(2))
    try:
        scorer.score("t000000", 0, "S3", 11, "not-a-digest")
        raise AssertionError("scored without checkpoint provenance")
    except ScoringViolation:
        pass
    print("PASS test_fabricated_all_correct_vector_refused")


def test_checkpoint_to_prediction_provenance_is_complete():
    recs = load_records(4)
    scorer = GoldScorer(recs)
    for r in recs:
        scorer.score(r["passage_id"], 0, "S3", 11, "bb" * 32)
    assert len(scorer.provenance) == 4
    for row in scorer.provenance:
        assert set(row) == {"passage_id", "arm", "seed", "checkpoint_sha256",
                            "predicted_candidate_index", "correct"}
        assert row["checkpoint_sha256"] == "bb" * 32
    print("PASS test_checkpoint_to_prediction_provenance_is_complete")


def main():
    test_arbitrary_evaluator_callback_does_not_exist()
    test_prediction_path_cannot_read_answer_or_trace()
    test_prediction_path_receives_profiles_not_raw_gold_labels()
    test_scorer_cannot_modify_predictions()
    test_fabricated_all_correct_vector_refused()
    test_checkpoint_to_prediction_provenance_is_complete()
    print("ALL PROTECTED-SCORING ATTACKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
