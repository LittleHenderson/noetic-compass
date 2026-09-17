"""Synthetic arithmetic/evidence tests; none are numerical learning results."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from cas_meta2.typed_teaching import matched_analysis as a, matched_contract as c, source


def row(kind, correct, target="same"):
    return {"kind": kind, "correct": correct, "target_digest": target}


def test_family_weighting_does_not_weight_large_graphs_more():
    rows, families = {}, []
    for i in range(6):
        keys = [str(i) + "p"] + [str(i) + "r" + str(j) for j in range(i+1)]
        families.append({"world_id": str(i), "record_ids": keys})
        rows[keys[0]] = row("parts", True)
        rows.update({k: row("reach", False) for k in keys[1:]})
    result = a.family_score(rows, families)
    assert result["family_balanced_accuracy"] == 0.5
    assert result["raw"]["accuracy"] == 6/27
    families[-1]["record_ids"] = families[0]["record_ids"]
    with pytest.raises(ValueError): a.family_score(rows, families)


def test_speed_uses_all_five_fixed_checkpoints():
    assert a.speed_auc(dict(zip(a.CHECKPOINTS, [0, .25, .5, .75, 1]))) == .5
    assert a.speed_auc(dict(zip(a.CHECKPOINTS, [0, 0, 0, 0, 1]))) == .125
    with pytest.raises(ValueError): a.speed_auc({0: 0, 160: 1})


def test_retention_reports_losses_and_low_competence():
    before = {str(i): row("parts" if i<2 else "reach", i==0) for i in range(4)}
    after = {str(i): row("parts" if i<2 else "reach", i>1) for i in range(4)}
    result = a.transition_panel(before, after, retention=True)
    assert result["status"] == "RETENTION_UNASSESSED" and result["accuracy_change"] == .25
    assert (result["lost"], result["gained"], result["retained_correct"]) == (1, 2, 0)
    assert result["by_kind"]["parts"]["accuracy_change"] == -.5
    assert result["fraction_baseline_correct_retained"] == 0
    before['1']["correct"] = True
    assert a.transition_panel(before, after, retention=True)["eligible"] is True
    after['1']["target_digest"] = "different"
    with pytest.raises(ValueError): a.transitions(before, after)


def synthetic_arms():
    return [{"model_seed": s, "condition": cond, "source_sha": "a"*40, "job": str(s)+cond,
        "initial_state": {k: "synthetic" for k in a.STATE_KEYS}, "runtime": {"device": "synthetic"},
        "target_identities": {}, "correction_multiset_digest": "synthetic", "work_phases": {}, "global_work": {},
        "development_curve": {0: 0}, "speed_auc": .4 if cond==c.CONDITIONS[0] else .5,
        "transfer": .7 if cond==c.CONDITIONS[0] else .5,
        "retention": {"eligible": True, "fraction_baseline_correct_retained": .8}}
        for s in c.MODEL_SEEDS for cond in c.CONDITIONS]


def test_all_three_pairs_required_and_negative_speed_preserved():
    arms = synthetic_arms()
    result = a.compare_pairs(arms)
    assert result["mean_speed_auc_difference"] == pytest.approx(-.1)
    assert result["mean_transfer_difference"] == pytest.approx(.2)
    assert result["learning_advantage_established"] is False
    arms[0]["retention"]["eligible"] = False
    assert a.compare_pairs(arms)["mean_retained_fraction_difference"] is None
    with pytest.raises(ValueError): a.compare_pairs(arms[:-1])


@pytest.mark.parametrize("key", ["initial_state", "runtime", "target_identities", "correction_multiset_digest", "work_phases", "global_work", "source_sha"])
def test_pair_rejects_confounded_inputs_or_work(key):
    arms = synthetic_arms(); arms[0][key] = "changed"
    with pytest.raises(ValueError): a.compare_pairs(arms)


def make_join_fixture():
    query = {"kind": "parts", "query_id": "q", "source_digest": "s", "rule": "r"}
    packet = {"record": {"query": query}}
    prediction = {"record_id": "id", "packet_digest": source.digest(packet), "answer": {"value": []}}
    prediction["prediction_id"] = "typed-prediction-" + source.digest(prediction)
    body = {**query, "answer_digest": source.digest(prediction["answer"]), "target_digest": "synthetic", "correct": True}
    checked = {**body, "check_digest": source.digest(body), "record_id": "id", "prediction_id": prediction["prediction_id"]}
    raw = c.canonical({"phase": "x", "predictions": [prediction]})
    score = {"phase": "x", "rows": [checked], "correct": 1, "total": 1,
        "public_seal": {"name": "x_predictions.json", "bytes": len(raw), "sha256": sha256(raw).hexdigest()}}
    return raw, score, {"id": packet}


def test_prediction_scoring_join_validates_bytes_and_reported_correctness():
    raw, score, packets = make_join_fixture()
    assert a.join_scoring(raw, score, packets, phase="x")["id"]["correct"] is True
    score["rows"][0]["correct"] = False
    with pytest.raises(ValueError, match="CHECK_ID"): a.join_scoring(raw, score, packets, phase="x")


@pytest.mark.parametrize("change", ["bytes", "packet", "prediction", "total"])
def test_scoring_join_rejects_rebound_data(change):
    raw, score, packets = make_join_fixture()
    if change == "bytes": raw += b' '
    if change == "packet": packets["id"]["extra"] = True
    if change == "prediction": score["rows"][0]["prediction_id"] = "other"
    if change == "total": score["total"] = 2
    with pytest.raises(ValueError): a.join_scoring(raw, score, packets, phase="x")
