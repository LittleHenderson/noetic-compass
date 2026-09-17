"""Private, checked loss plans after caller-bound public prediction bytes.

No tensor package is imported here. The semantic checker is imported only by
compile_loss_plan, after exact sealed-byte and public prediction validation.
The caller remains responsible for durable custody/authenticity of the seal.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from . import answers, course, slots, source

SCHEMA = "cas.typed-teaching-loss-plan/0.1"
PREDICTION_SCHEMA = "cas.typed-teaching-prediction/0.1"
POLICY = {"training": "RAW_FIELD_MEAN_THEN_TASK_MEAN_THEN_BATCH_MEAN",
          "reporting": "DIVIDE_EACH_CATEGORICAL_OR_BINARY_TERM_BY_LOG_PUBLIC_ALPHABET_SIZE_THEN_SAME_MEANS",
          "membership": "mean over ALL public binary slots, never only positive members",
          "correspondence": "one normalized hierarchical whole-candidate valid-set field; no independent mapping-node marginals",
          "role_set": "one exact multi-hot field; ambiguity is not alternative singleton labels",
          "forced": "singleton categorical field has zero loss, zero normalized loss, separately counted"}
require, digest, canonical = source.require, source.digest, source.canonical


def profile():
    raw = Path(__file__).read_bytes()
    body = {"schema": "cas.typed-teaching-loss-profile/0.1", "policy": deepcopy(POLICY),
            "source_sha256": sha256(raw).hexdigest(), "slots_profile": slots.profile(),
            "status": "PURE_LOSS_CONTRACT_NOT_NUMERIC_LEARNING_ACCEPTANCE"}
    return {**body, "profile_digest": digest(body)}


def validate_prediction(packet, prediction):
    """Check public wire/scalar coherence, not whether a model actually ran."""
    fields = {"schema", "prediction_id", "record_id", "packet_digest", "slot_plan_digest", "depth",
              "model_revision", "run_context_digest", "encoder_identity_digest", "scores", "decisions", "answer"}
    require(type(prediction) is dict and set(prediction) == fields and prediction["schema"] == PREDICTION_SCHEMA,
            "TYPED_LOSS_PREDICTION_FIELDS")
    require(type(prediction["depth"]) is int and prediction["depth"] in (1, 2, 4, 8)
            and type(prediction["model_revision"]) is int and prediction["model_revision"] >= 0,
            "TYPED_LOSS_PREDICTION_COORDINATES")
    require(all(type(prediction[key]) is str and re.fullmatch("[0-9a-f]{64}", prediction[key]) for key in
                ("run_context_digest", "encoder_identity_digest")), "TYPED_LOSS_PREDICTION_IDENTITIES")
    plan = slots.compile_slots(packet)
    require(prediction["record_id"] == plan["record_id"] and prediction["packet_digest"] == plan["packet_digest"]
            and prediction["slot_plan_digest"] == plan["plan_digest"], "TYPED_LOSS_PUBLIC_BINDING")
    decision = slots.score_decisions(packet, prediction["scores"])
    answer = slots.assemble_answer(packet, decision)
    require(canonical(prediction["decisions"]) == canonical(decision)
            and canonical(prediction["answer"]) == canonical(answer), "TYPED_LOSS_PREDICTION_COHERENCE")
    require(prediction["prediction_id"] == "typed-prediction-" + digest({k: v for k, v in prediction.items() if k != "prediction_id"}),
            "TYPED_LOSS_PREDICTION_DIGEST")
    return deepcopy(prediction)


def _sealed(packet, raw, expected_sha256):
    require(type(raw) is bytes and 0 < len(raw) <= 2 * 1024 * 1024
            and type(expected_sha256) is str and re.fullmatch("[0-9a-f]{64}", expected_sha256)
            and sha256(raw).hexdigest() == expected_sha256, "TYPED_LOSS_SEAL_BYTES")
    try:
        prediction = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("TYPED_LOSS_SEAL_JSON") from exc
    require((canonical(prediction) + "\n").encode() == raw, "TYPED_LOSS_SEAL_NONCANONICAL")
    return validate_prediction(packet, prediction)


def _symbols_for_answer(plan, answer):
    value = answer["value"]
    world_alias = {w["world_id"]: w["alias"] for w in plan["aliases"]["worlds"]}
    node_alias = {n["ref"]: n["alias"] for w in plan["aliases"]["worlds"] for n in w["nodes"]}
    result = {}
    for row in plan["slots"]:
        field, coordinates = row["field"], row["coordinates"]
        if field == "role": symbol = "PRESENT" if coordinates[0] in value["roles"] else "ABSENT"
        elif field == "whole": symbol = node_alias[value["whole"]]
        elif field in ("kind_ref", "function_ref", "setting_ref"):
            symbol = world_alias[value[field].rsplit("/decl/", 1)[0]]
        elif field == "participant": symbol = "PRESENT" if coordinates[0] in value["participants"] else "ABSENT"
        elif field == "world_id": symbol = "NO_MATCH" if value["world_id"] is None else world_alias[value["world_id"]]
        elif field == "node": symbol = "PRESENT" if coordinates[0] in value["nodes"] else "ABSENT"
        elif field == "edge": symbol = "PRESENT" if {"source": coordinates[0], "target": coordinates[1]} in value["edges"] else "ABSENT"
        elif field == "reach": symbol = "VIA_" + node_alias[value["via"]] if value["state"] == "VIA" else value["state"]
        else: raise ValueError("TYPED_LOSS_FIELD_UNSUPPORTED")
        require(symbol in row["symbols"], "TYPED_LOSS_TARGET_SYMBOL")
        result[row["slot_id"]] = symbol
    return result


def compile_loss_plan(packet, target_receipt, *, sealed_prediction_bytes, expected_prediction_sha256):
    prediction = _sealed(packet, sealed_prediction_bytes, expected_prediction_sha256)
    # Deliberately after all public seal checks. Importing/predicting does not call this.
    from . import checker
    checked = checker.validate_target(packet["source"], packet["record"]["query"], target_receipt)
    plan = slots.compile_slots(packet)
    admissible = checked["admissible_answers"]
    fields = []
    if plan["kind"] == "correspondence":
        valid = {canonical(answer["value"]) for answer in admissible}
        ids = [row["candidate_id"] for row in plan["correspondence_candidates"] if canonical(row["value"]) in valid]
        require(len(ids) == len(valid) and ids, "TYPED_LOSS_JOINT_VALID_SET")
        fields.append({"field": "correspondence", "kind": "joint_correspondence", "slot_ids": [s["slot_id"] for s in plan["slots"]],
                       "valid_candidate_ids": ids, "targets": {}, "public_alphabet_size": len(plan["correspondence_candidates"])})
    else:
        encoded = [_symbols_for_answer(plan, answer) for answer in admissible]
        groups = list(dict.fromkeys(row["group"] for row in plan["slots"]))
        for group in groups:
            rows = [row for row in plan["slots"] if row["group"] == group]
            membership = all(row["symbols"] == ["ABSENT", "PRESENT"] for row in rows)
            require(membership or len(rows) == 1, "TYPED_LOSS_FIELD_SHAPE")
            if membership:
                require(len({canonical([value[row["slot_id"]] for row in rows]) for value in encoded}) == 1,
                        "TYPED_LOSS_CORRELATED_MEMBERSHIP_TARGETS_UNSUPPORTED")
            targets = {row["slot_id"]: [symbol for symbol in row["symbols"] if any(value[row["slot_id"]] == symbol for value in encoded)]
                       for row in rows}
            fields.append({"field": group, "kind": "membership" if membership else "categorical",
                           "slot_ids": [r["slot_id"] for r in rows], "valid_candidate_ids": [], "targets": targets,
                           "public_alphabet_size": 2 if membership else len(rows[0]["symbols"])})
    body = {"schema": SCHEMA, "record_id": plan["record_id"], "query_id": plan["query_id"], "packet_digest": plan["packet_digest"],
            "slot_plan_digest": plan["plan_digest"], "prediction_id": prediction["prediction_id"],
            "prediction_sha256": expected_prediction_sha256, "target_digest": checked["target_digest"],
            "checker_profile_digest": checked["checker_profile_digest"], "admissible_answer_count": len(admissible),
            "fields": fields, "policy": deepcopy(POLICY), "profile": profile(),
            "forced_fields": sum(row["public_alphabet_size"] == 1 for row in fields),
            "authority": "SOURCE_RECONSTRUCTED_PRIVATE_TARGET; SEAL_CUSTODY_AND_MODEL_EXECUTION_ARE_CALLER_BOUNDARIES"}
    return {**body, "loss_plan_digest": digest(body)}


def validate_loss_plan(packet, target_receipt, plan, *, sealed_prediction_bytes, expected_prediction_sha256):
    source._bounded(plan)
    expected = compile_loss_plan(packet, target_receipt, sealed_prediction_bytes=sealed_prediction_bytes,
                                 expected_prediction_sha256=expected_prediction_sha256)
    require(canonical(plan) == canonical(expected), "TYPED_LOSS_PLAN_RECONSTRUCTION")
    return expected


def scalar_report(packet, plan, scores):
    """Scalar audit of an already checked plan; not model/tensor execution."""
    public_plan = slots.compile_slots(packet)
    require(plan["schema"] == SCHEMA and plan["slot_plan_digest"] == public_plan["plan_digest"]
            and plan["loss_plan_digest"] == digest({k: v for k, v in plan.items() if k != "loss_plan_digest"}),
            "TYPED_LOSS_REPORT_PLAN_BINDING")
    slots._check_scores(public_plan, scores)
    rows = []
    for field in plan["fields"]:
        if field["kind"] == "joint_correspondence":
            probabilities = slots._candidate_scores(public_plan, scores)
            raw = -slots._logsumexp([r["log_probability"] for r in probabilities if r["candidate_id"] in field["valid_candidate_ids"]])
        else:
            terms = [slots._logsumexp(list(scores[key].values())) - slots._logsumexp([scores[key][symbol] for symbol in field["targets"][key]])
                     for key in field["slot_ids"]]
            raw = sum(terms) / len(terms)
        require(math.isfinite(raw), "TYPED_LOSS_NONFINITE_REPORT")
        size = field["public_alphabet_size"]
        rows.append({"field": field["field"], "raw_loss": raw, "normalized_loss": raw / math.log(size) if size > 1 else 0.0,
                     "public_alphabet_size": size, "slot_count": len(field["slot_ids"]), "forced": size == 1})
    return {"fields": rows, "raw_task_loss": sum(r["raw_loss"] for r in rows) / len(rows),
            "normalized_task_loss": sum(r["normalized_loss"] for r in rows) / len(rows),
            "training_uses": "raw_task_loss", "numeric_model_executed": False}
