#!/usr/bin/env python3
"""Run the Stage 9 40E eta-to-epsilon likelihood bridge.

This is the 40-Element port of the original eta-to-epsilon bridge shape:

    scenario text -> hidden-state 40E readout (eta)
    -> readable 40E CAS realization prefix (epsilon)
    -> second model likelihood pass against the paired counterfactual element

The report is likelihood-level evidence only. It deliberately does not emit
ACCEPT or SUPPRESS; that requires the verifier/Evidence Packet merge layer.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_open_weight_eta_epsilon_bridge import mean_logprob_continuation  # noqa: E402
from run_open_weight_probe_shard import (  # noqa: E402
    ProbeShardConfig,
    load_open_weight_model,
)


SCHEMA_VERSION = "cas_harness_stage9_40e_eta_epsilon_bridge.v1"
METHOD_LABEL = "S9-40E-ORIGINAL-BASELINE-READOUT::ETA-EPSILON-BRIDGE"
AXIS = "40_element_operator_x_domain"

DOMAIN_GLOSSES = {
    "P": {
        "name": "Spiritual",
        "gloss": "soul-level meaning, sacred orientation, and relation to ultimate purpose",
    },
    "C": {
        "name": "Mental",
        "gloss": "thought, interpretation, memory, analysis, and cognitive framing",
    },
    "E": {
        "name": "Emotional",
        "gloss": "felt meaning, mood, attachment, affect, and emotional movement",
    },
    "O": {
        "name": "Physical",
        "gloss": "embodied matter, action, material form, and concrete conditions",
    },
}

OPERATOR_GLOSSES = {
    "^0": {
        "name": "Idea",
        "gloss": "the aspect or form of the thing itself as it appears in that domain",
    },
    "^1": {
        "name": "Mind",
        "gloss": "awareness, orientation, and the mind-like organizing center",
    },
    "^2": {
        "name": "Positive",
        "gloss": "affirming, clarifying, beneficial, stabilizing, or desirable force",
    },
    "^3": {
        "name": "Negative",
        "gloss": "disturbing, obstructing, harmful, confusing, or undesirable force",
    },
    "^4": {
        "name": "Vibration",
        "gloss": "the signal, energy, frequency, mood, or signature being emitted",
    },
    "^5": {
        "name": "Female",
        "gloss": "receiving, nurturing, protecting, opening, or matrix-like capacity",
    },
    "^6": {
        "name": "Male",
        "gloss": "transmitting, delivering, testing, projecting, or seed-like force",
    },
    "^7": {
        "name": "Rhythm",
        "gloss": "pattern, timing, recurrence, habit, cycle, or repeated motion",
    },
    "^8": {
        "name": "Above/Cause",
        "gloss": "higher cause, inner meaning, deeper reason, or organizing principle",
    },
    "^9": {
        "name": "Below/Effect",
        "gloss": "outer sign, lower expression, visible effect, or surface manifestation",
    },
}


@dataclass(frozen=True)
class BridgeConfig:
    model_id: str
    scenario_path: Path
    dataset: Path
    eval_report: Path
    output: Path
    output_md: Path | None = None
    model_revision: str | None = None
    model_artifact_manifest_path: Path | None = None
    model_artifact_manifest_sha256: str | None = None
    torch_dtype: str = "float16"
    device_map: str = "auto"
    per_element: int = 2
    selection_seed: int = 20260528
    readout_seed: int = 20260527
    readout_layer: int | None = None
    probe_C: float = 0.1
    probe_max_iter: int = 1000
    min_readout_margin: float | None = None
    readout_margin_quantile: float | None = None
    max_length: int = 256
    trust_remote_code: bool = False


@dataclass(frozen=True)
class ScenarioMeta:
    scenario_id: str
    prompt: str
    split: str
    element: str
    partner_element: str
    pair_id: str
    pair_kind: str
    paraphrase_family: str


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--scenario-path", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--eval-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--model-artifact-manifest-path", required=True, type=Path)
    parser.add_argument("--model-artifact-manifest-sha256", required=True)
    parser.add_argument("--torch-dtype", default="float16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--per-element", type=int, default=2)
    parser.add_argument("--selection-seed", type=int, default=20260528)
    parser.add_argument("--readout-seed", type=int, default=20260527)
    parser.add_argument("--readout-layer", type=int)
    parser.add_argument("--probe-C", type=float, default=0.1)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument("--min-readout-margin", type=float)
    parser.add_argument("--readout-margin-quantile", type=float)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = BridgeConfig(
        model_id=args.model_id,
        scenario_path=args.scenario_path,
        dataset=args.dataset,
        eval_report=args.eval_report,
        output=args.output,
        output_md=args.output_md,
        model_revision=args.model_revision,
        model_artifact_manifest_path=args.model_artifact_manifest_path,
        model_artifact_manifest_sha256=args.model_artifact_manifest_sha256,
        torch_dtype=args.torch_dtype,
        device_map=args.device_map,
        per_element=args.per_element,
        selection_seed=args.selection_seed,
        readout_seed=args.readout_seed,
        readout_layer=args.readout_layer,
        probe_C=args.probe_C,
        probe_max_iter=args.probe_max_iter,
        min_readout_margin=args.min_readout_margin,
        readout_margin_quantile=args.readout_margin_quantile,
        max_length=args.max_length,
        trust_remote_code=args.trust_remote_code,
    )
    report = run_stage9_40e_bridge(config)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if config.output_md:
        config.output_md.parent.mkdir(parents=True, exist_ok=True)
        config.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"[stage9-40e-bridge] status={report['status']}")
    print(f"[stage9-40e-bridge] wrote {config.output}")
    if config.output_md:
        print(f"[stage9-40e-bridge] wrote {config.output_md}")
    return 0


def run_stage9_40e_bridge(config: BridgeConfig) -> dict[str, Any]:
    started = time.perf_counter()
    model_config = ProbeShardConfig(
        model_id=config.model_id,
        worker_id="local-stage9-40e-bridge",
        audit_id="stage9-40e-eta-epsilon-bridge",
        job_id="manual-stage9-40e-equivalent",
        layer_start=0,
        layer_end=0,
        shard_id="stage9-40e-eta-epsilon",
        assigned_methods=("stage9_40e_readout", "eta_epsilon_bridge"),
        expected_outputs=("40e_readout", "eta_epsilon_likelihood_bridge", "worker_evidence_manifest"),
        result_path=config.output,
        model_revision=config.model_revision,
        model_artifact_manifest_path=config.model_artifact_manifest_path,
        model_artifact_manifest_sha256=config.model_artifact_manifest_sha256,
        torch_dtype=config.torch_dtype,
        device_map=config.device_map,
        max_scenarios=max(1, config.per_element * 40),
        max_length=config.max_length,
        trust_remote_code=config.trust_remote_code,
    )
    scenario_meta = load_stage9_scenario_meta(config.scenario_path)
    with np.load(config.dataset, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        layers = np.asarray(data["layers"], dtype=int)
        scenario_ids = np.asarray(data["scenario_ids"], dtype=str)
        labels = canonical_labels(np.asarray(data["labels_element"], dtype=str))

    split = split_from_scenario_meta(scenario_ids, scenario_meta)
    layer_positions = {int(layer): idx for idx, layer in enumerate(layers.tolist())}
    readout_layer = select_readout_layer(
        config.eval_report,
        available_layers=layers.tolist(),
        requested_layer=config.readout_layer,
    )
    metrics, readout_model = fit_eval_logistic_readout(
        features,
        labels,
        split,
        layer_positions[int(readout_layer)],
        C=config.probe_C,
        max_iter=config.probe_max_iter,
    )
    predicted = np.asarray(
        readout_model.predict(features[:, layer_positions[int(readout_layer)], :]),
        dtype=str,
    )
    readout_scores = probability_scores(
        readout_model.predict_proba(features[:, layer_positions[int(readout_layer)], :]),
        [str(label) for label in readout_model.named_steps["logisticregression"].classes_.tolist()],
    )
    unfiltered_selected = select_stage9_bridge_indices(
        scenario_ids=scenario_ids,
        labels=labels,
        split=split,
        scenario_meta=scenario_meta,
        per_element=config.per_element,
        seed=config.selection_seed,
    )
    selected_indices, readout_filter = apply_readout_filter(
        unfiltered_selected,
        readout_scores,
        min_margin=config.min_readout_margin,
        margin_quantile=config.readout_margin_quantile,
    )
    if not selected_indices:
        raise RuntimeError("No Stage 9 40E test rows survived selection/filtering.")

    lm, tokenizer, model_info = load_open_weight_model(model_config)
    conditions = (
        "none",
        "gold_readable",
        "probe_readable",
        "partner_readable",
        "gold_raw",
        "probe_raw",
        "partner_raw",
    )
    margins_by_condition: dict[str, list[float]] = {condition: [] for condition in conditions}
    cases: list[dict[str, Any]] = []
    selected_element_hits = 0
    selected_operator_hits = 0
    selected_domain_hits = 0

    for case_number, idx in enumerate(selected_indices, start=1):
        sid = str(scenario_ids[int(idx)])
        meta = scenario_meta[sid]
        gold_label = canonical_element(labels[int(idx)])
        predicted_label = canonical_element(predicted[int(idx)])
        partner_label = canonical_element(meta.partner_element)
        gold_operator, gold_domain = parse_element_label(gold_label)
        predicted_operator, predicted_domain = parse_element_label(predicted_label)
        partner_operator, partner_domain = parse_element_label(partner_label)
        selected_element_hits += int(predicted_label == gold_label)
        selected_operator_hits += int(predicted_operator == gold_operator)
        selected_domain_hits += int(predicted_domain == gold_domain)

        correct_continuation = f" {element_phrase(gold_label)}."
        partner_continuation = f" {element_phrase(partner_label)}."
        case: dict[str, Any] = {
            "scenario_id": sid,
            "gold_label": gold_label,
            "predicted_label": predicted_label,
            "partner_label": partner_label,
            "gold_operator": gold_operator,
            "gold_domain": gold_domain,
            "predicted_operator": predicted_operator,
            "predicted_domain": predicted_domain,
            "partner_operator": partner_operator,
            "partner_domain": partner_domain,
            "readout_confidence": readout_scores[int(idx)],
            "element_correct": predicted_label == gold_label,
            "operator_correct": predicted_operator == gold_operator,
            "domain_correct": predicted_domain == gold_domain,
            "condition_scores": {},
        }
        for condition in conditions:
            prefix = condition_prefix(condition, gold_label, predicted_label, partner_label)
            prompt = prefix + base_prompt(meta.prompt)
            correct = mean_logprob_continuation(
                model=lm,
                tokenizer=tokenizer,
                prompt=prompt,
                continuation=correct_continuation,
                max_length=config.max_length,
            )
            partner = mean_logprob_continuation(
                model=lm,
                tokenizer=tokenizer,
                prompt=prompt,
                continuation=partner_continuation,
                max_length=config.max_length,
            )
            margin = float(correct["mean_logprob"] - partner["mean_logprob"])
            margins_by_condition[condition].append(margin)
            case["condition_scores"][condition] = {
                "margin": margin,
                "correct_mean_logprob": correct["mean_logprob"],
                "partner_mean_logprob": partner["mean_logprob"],
                "correct_n_tokens": correct["n_tokens"],
                "partner_n_tokens": partner["n_tokens"],
            }
        print(
            "[stage9-40e-bridge] "
            f"{case_number}/{len(selected_indices)} {sid} "
            f"gold={gold_label} probe={predicted_label} "
            f"probe_readable_margin={case['condition_scores']['probe_readable']['margin']:.6f}",
            flush=True,
        )
        cases.append(case)

    summaries = summarize_conditions(margins_by_condition)
    key = key_comparisons(summaries)
    n_cases = len(selected_indices)
    selected_element_acc = selected_element_hits / max(n_cases, 1)
    selected_operator_acc = selected_operator_hits / max(n_cases, 1)
    selected_domain_acc = selected_domain_hits / max(n_cases, 1)
    gates = bridge_gates(summaries, key)
    status, implication = interpret_bridge_status(summaries, key)

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "experiment": "Open-weight Stage 9 40E eta-to-epsilon likelihood bridge",
        "status": status,
        "method_label": METHOD_LABEL,
        "plain_english_read": (
            "Hidden states are read as one of 40 TKS Elements, the predicted "
            "Element is realized into readable CAS context, and the model's "
            "conditional likelihood is measured against the paired counterfactual element."
        ),
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "model_info": model_info,
        "axis": AXIS,
        "scenario_path": str(config.scenario_path),
        "scenario_path_sha256": sha256_file(config.scenario_path),
        "dataset": str(config.dataset),
        "dataset_sha256": sha256_file(config.dataset),
        "eval_report": str(config.eval_report),
        "eval_report_sha256": sha256_file(config.eval_report),
        "readout_layer": int(readout_layer),
        "readout_layer_position": int(layer_positions[int(readout_layer)]),
        "readout_mode": "logistic_linear_probe",
        "readout_seed": config.readout_seed,
        "probe_C": config.probe_C,
        "probe_max_iter": config.probe_max_iter,
        "selection_seed": config.selection_seed,
        "per_element": config.per_element,
        "readout_filter": readout_filter,
        "n_cases": n_cases,
        "probe_prediction": {
            "all_train_element_accuracy": metrics["train_acc"],
            "all_val_element_accuracy": metrics["val_acc"],
            "all_test_element_accuracy": metrics["test_acc"],
            "all_test_macro_f1": metrics["test_macro_f1"],
            "selected_element_accuracy": round(float(selected_element_acc), 6),
            "selected_operator_accuracy": round(float(selected_operator_acc), 6),
            "selected_domain_accuracy": round(float(selected_domain_acc), 6),
        },
        "conditions": summaries,
        "key_comparisons": key,
        "bridge_gates": gates,
        "correctness_buckets": summarize_correctness_buckets(cases),
        "cases": cases,
        "produced_outputs": ["40e_readout", "eta_epsilon_likelihood_bridge", "worker_evidence_manifest"],
        "missing_outputs": ["verifier_accept_suppress_merge", "full_evidence_packet"],
        "important_limit": (
            "Likelihood-level eta-to-epsilon bridge evidence. This is not an "
            "ACCEPT/SUPPRESS verdict until merged with verifier and Evidence Packet layers."
        ),
        "implication": implication,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def load_stage9_scenario_meta(path: Path) -> dict[str, ScenarioMeta]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise RuntimeError("Scenario file must be a list or contain scenarios.")

    raw: dict[str, dict[str, Any]] = {}
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or item.get("scenario_id") or f"scenario-{index + 1:04d}")
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        pair_id = str(metadata.get("counterfactual_pair_id") or item.get("counterfactual_pair_id") or "")
        if not pair_id:
            continue
        raw[sid] = item
        by_pair[pair_id].append(item)

    out: dict[str, ScenarioMeta] = {}
    for sid, item in raw.items():
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        expected = item.get("expected_cas_axes") if isinstance(item.get("expected_cas_axes"), dict) else {}
        pair_id = str(metadata.get("counterfactual_pair_id") or item.get("counterfactual_pair_id") or "")
        element = canonical_element(expected.get("element") or metadata.get("element") or "")
        split = str(metadata.get("split") or item.get("split") or "").strip()
        prompt = str(item.get("prompt") or item.get("prompt_text") or item.get("text") or "").strip()
        partner = partner_element_for_item(item, by_pair[pair_id])
        if sid and prompt and element and partner and split:
            out[sid] = ScenarioMeta(
                scenario_id=sid,
                prompt=prompt,
                split=split,
                element=element,
                partner_element=partner,
                pair_id=pair_id,
                pair_kind=str(metadata.get("pair_kind") or item.get("pair_kind") or ""),
                paraphrase_family=str(metadata.get("paraphrase_family") or ""),
            )
    if not out:
        raise RuntimeError("No Stage 9 scenario metadata found.")
    return out


def partner_element_for_item(item: dict[str, Any], pair_items: list[dict[str, Any]]) -> str:
    expected = item.get("expected_cas_axes") if isinstance(item.get("expected_cas_axes"), dict) else {}
    own_element = canonical_element(expected.get("element") or "")
    own_id = str(item.get("id") or item.get("scenario_id") or "")
    for candidate in pair_items:
        cid = str(candidate.get("id") or candidate.get("scenario_id") or "")
        cexpected = candidate.get("expected_cas_axes") if isinstance(candidate.get("expected_cas_axes"), dict) else {}
        celement = canonical_element(cexpected.get("element") or "")
        if cid != own_id and celement and celement != own_element:
            return celement
    return ""


def split_from_scenario_meta(
    scenario_ids: np.ndarray,
    scenario_meta: dict[str, ScenarioMeta],
) -> dict[str, np.ndarray]:
    by_split: dict[str, list[int]] = defaultdict(list)
    for index, sid in enumerate(scenario_ids.tolist()):
        meta = scenario_meta.get(str(sid))
        if meta is None:
            raise RuntimeError(f"Dataset scenario_id missing from scenario JSON: {sid}")
        by_split[meta.split].append(index)
    missing = sorted({"train", "val", "test"} - set(by_split))
    if missing:
        raise RuntimeError(f"Missing required scenario splits: {missing}")
    return {split: np.asarray(indices, dtype=int) for split, indices in by_split.items()}


def select_readout_layer(
    eval_report: Path,
    *,
    available_layers: list[int],
    requested_layer: int | None,
) -> int:
    available = {int(layer) for layer in available_layers}
    if requested_layer is not None:
        if int(requested_layer) not in available:
            raise RuntimeError(f"Readout layer {requested_layer} not present in dataset layers {available_layers}.")
        return int(requested_layer)
    payload = json.loads(eval_report.read_text(encoding="utf-8"))
    layer = payload.get("best_layer", {}).get("layer")
    if layer is None:
        raise RuntimeError(f"Could not resolve best_layer.layer from {eval_report}")
    if int(layer) not in available:
        raise RuntimeError(f"Best layer {layer} not present in dataset layers {available_layers}.")
    return int(layer)


def fit_eval_logistic_readout(
    features: np.ndarray,
    labels: np.ndarray,
    split: dict[str, np.ndarray],
    layer_position: int,
    *,
    C: float,
    max_iter: int,
) -> tuple[dict[str, Any], Any]:
    pipeline = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=C, max_iter=max_iter, class_weight="balanced", solver="lbfgs"),
    )
    pipeline.fit(features[split["train"], layer_position, :], labels[split["train"]])
    classes = [str(label) for label in pipeline.named_steps["logisticregression"].classes_.tolist()]
    metrics = {
        "train_acc": accuracy(labels[split["train"]], pipeline.predict(features[split["train"], layer_position, :])),
        "val_acc": accuracy(labels[split["val"]], pipeline.predict(features[split["val"], layer_position, :])),
        "test_acc": accuracy(labels[split["test"]], pipeline.predict(features[split["test"], layer_position, :])),
        "test_macro_f1": macro_f1(labels[split["test"]], pipeline.predict(features[split["test"], layer_position, :]), classes),
    }
    return {key: round(float(value), 6) for key, value in metrics.items()}, pipeline


def select_stage9_bridge_indices(
    *,
    scenario_ids: np.ndarray,
    labels: np.ndarray,
    split: dict[str, np.ndarray],
    scenario_meta: dict[str, ScenarioMeta],
    per_element: int,
    seed: int,
) -> list[int]:
    test_lookup = set(int(idx) for idx in split["test"].tolist())
    by_element: dict[str, list[int]] = defaultdict(list)
    for idx, sid in enumerate(scenario_ids.tolist()):
        if idx not in test_lookup:
            continue
        meta = scenario_meta[str(sid)]
        if not meta.partner_element:
            continue
        by_element[canonical_element(labels[idx])].append(idx)
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    for element in sorted(by_element):
        candidates = list(by_element[element])
        rng.shuffle(candidates)
        if len(candidates) < per_element:
            raise RuntimeError(f"Element {element} needs {per_element} bridge rows, got {len(candidates)}.")
        selected.extend(int(idx) for idx in candidates[:per_element])
    if len(by_element) != 40:
        raise RuntimeError(f"Expected 40 bridge elements, got {len(by_element)}.")
    return selected


def probability_scores(probabilities: np.ndarray, classes: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in probabilities:
        order = np.argsort(row)[::-1]
        best_idx = int(order[0])
        second_idx = int(order[1]) if len(order) > 1 else best_idx
        best_prob = float(row[best_idx])
        second_prob = float(row[second_idx])
        margin = best_prob - second_prob
        out.append(
            {
                "predicted_label": classes[best_idx],
                "runner_up_label": classes[second_idx],
                "best_probability": round(best_prob, 6),
                "runner_up_probability": round(second_prob, 6),
                "probability_margin": round(float(margin), 6),
                "normalized_readout_margin": round(float(margin), 6),
            }
        )
    return out


def apply_readout_filter(
    indices: list[int],
    readout_scores: list[dict[str, Any]],
    *,
    min_margin: float | None,
    margin_quantile: float | None,
) -> tuple[list[int], dict[str, Any]]:
    if margin_quantile is not None and not (0.0 <= margin_quantile <= 1.0):
        raise ValueError("--readout-margin-quantile must be between 0.0 and 1.0")
    margins = [float(readout_scores[int(idx)]["normalized_readout_margin"]) for idx in indices]
    threshold: float | None = None
    if margin_quantile is not None:
        threshold = float(np.quantile(np.asarray(margins, dtype=np.float64), margin_quantile))
    if min_margin is not None:
        threshold = float(min_margin) if threshold is None else max(float(min_margin), threshold)
    if threshold is None:
        kept = list(indices)
        mode = "none"
    else:
        kept = [
            int(idx)
            for idx in indices
            if float(readout_scores[int(idx)]["normalized_readout_margin"]) >= threshold
        ]
        mode = "normalized_readout_margin"
    return kept, {
        "mode": mode,
        "score": "normalized_readout_margin",
        "min_readout_margin": min_margin,
        "readout_margin_quantile": margin_quantile,
        "effective_threshold": round(threshold, 6) if threshold is not None else None,
        "original_selected_cases": len(indices),
        "kept_cases": len(kept),
        "coverage": round(len(kept) / len(indices), 6) if indices else 0.0,
    }


def canonical_labels(labels: np.ndarray) -> np.ndarray:
    return np.asarray([canonical_element(label) for label in labels.tolist()], dtype=str)


def canonical_element(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "|" not in text:
        return ""
    operator, domain = text.split("|", 1)
    if operator in OPERATOR_GLOSSES and domain in DOMAIN_GLOSSES:
        return f"{operator}|{domain}"
    return ""


def parse_element_label(label: Any) -> tuple[str, str]:
    canonical = canonical_element(label)
    if not canonical:
        raise ValueError(f"Bad 40E label: {label!r}")
    operator, domain = canonical.split("|", 1)
    return operator, domain


def raw_prefix(label: str) -> str:
    operator, domain = parse_element_label(label)
    return f"CAS 40E frame: {operator}|{domain}.\n"


def readable_prefix(label: str) -> str:
    operator, domain = parse_element_label(label)
    operator_info = OPERATOR_GLOSSES[operator]
    domain_info = DOMAIN_GLOSSES[domain]
    return (
        "CAS 40-Element realization frame for the focused role:\n"
        f"- Element code: {operator}|{domain}\n"
        f"- Operator: {operator_info['name']} - {operator_info['gloss']}\n"
        f"- Domain: {domain_info['name']} - {domain_info['gloss']}\n"
        f"- Readable meaning: {element_phrase(label)}\n"
        "Use this realized structure as context for the next sentence.\n\n"
    )


def condition_prefix(condition: str, gold_label: str, predicted_label: str, partner_label: str) -> str:
    if condition == "none":
        return ""
    if condition == "gold_readable":
        return readable_prefix(gold_label)
    if condition == "probe_readable":
        return readable_prefix(predicted_label)
    if condition == "partner_readable":
        return readable_prefix(partner_label)
    if condition == "gold_raw":
        return raw_prefix(gold_label)
    if condition == "probe_raw":
        return raw_prefix(predicted_label)
    if condition == "partner_raw":
        return raw_prefix(partner_label)
    raise ValueError(f"Unknown bridge condition: {condition!r}")


def element_phrase(label: str) -> str:
    operator, domain = parse_element_label(label)
    return f"{DOMAIN_GLOSSES[domain]['name'].lower()} {OPERATOR_GLOSSES[operator]['name'].lower()}: {OPERATOR_GLOSSES[operator]['gloss']}"


def base_prompt(prompt: str) -> str:
    return f"{prompt}\nThe focused role is about"


def summarize_conditions(margins_by_condition: dict[str, list[float]]) -> dict[str, Any]:
    baseline = margins_by_condition["none"]
    summaries: dict[str, Any] = {}
    for condition, margins in margins_by_condition.items():
        deltas = [margin - base for margin, base in zip(margins, baseline)]
        n_pos = sum(1 for delta in deltas if delta > 0)
        summaries[condition] = {
            "margin": summarize(margins),
            "delta_vs_none": summarize(deltas),
            "delta_positive_count": int(n_pos),
            "delta_positive_sign_p": sign_test_p(n_pos, len(deltas)),
        }
    return summaries


def key_comparisons(summaries: dict[str, Any]) -> dict[str, float]:
    return {
        "probe_readable_delta_vs_none": round(float(summaries["probe_readable"]["delta_vs_none"]["mean"]), 6),
        "probe_readable_minus_partner_readable_margin": round(
            float(summaries["probe_readable"]["margin"]["mean"])
            - float(summaries["partner_readable"]["margin"]["mean"]),
            6,
        ),
        "gold_readable_delta_vs_none": round(float(summaries["gold_readable"]["delta_vs_none"]["mean"]), 6),
        "gold_readable_minus_partner_readable_margin": round(
            float(summaries["gold_readable"]["margin"]["mean"])
            - float(summaries["partner_readable"]["margin"]["mean"]),
            6,
        ),
        "probe_raw_delta_vs_none": round(float(summaries["probe_raw"]["delta_vs_none"]["mean"]), 6),
        "gold_raw_delta_vs_none": round(float(summaries["gold_raw"]["delta_vs_none"]["mean"]), 6),
    }


def bridge_gates(summaries: dict[str, Any], key: dict[str, float]) -> dict[str, Any]:
    def gate(prefix: str) -> dict[str, Any]:
        delta_key = f"{prefix}_delta_vs_none"
        partner_key = f"{prefix}_minus_partner_readable_margin"
        sign_p = float(summaries[prefix]["delta_positive_sign_p"])
        checks = {
            "delta_vs_none": {
                "value": key[delta_key],
                "threshold": 0.10,
                "operator": ">",
                "passed": key[delta_key] > 0.10,
            },
            "minus_partner_readable_margin": {
                "value": key[partner_key],
                "threshold": 0.10,
                "operator": ">",
                "passed": key[partner_key] > 0.10,
            },
            "delta_positive_sign_p": {
                "value": sign_p,
                "threshold": 0.01,
                "operator": "<=",
                "passed": sign_p <= 0.01,
            },
        }
        return {
            "passed": all(bool(check["passed"]) for check in checks.values()),
            "checks": checks,
        }

    return {
        "probe_readable": gate("probe_readable"),
        "gold_readable": gate("gold_readable"),
    }


def interpret_bridge_status(summaries: dict[str, Any], key: dict[str, float]) -> tuple[str, str]:
    gates = bridge_gates(summaries, key)
    probe_pass = bool(gates["probe_readable"]["passed"])
    gold_pass = bool(gates["gold_readable"]["passed"])
    if probe_pass:
        status = "PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS"
        implication = (
            "The 40E eta-to-epsilon loop passes this likelihood assay: the model's "
            "own hidden-state 40-Element readout can be realized as readable CAS "
            "context, and that context moves paired likelihood in the intended direction."
        )
    elif gold_pass:
        status = "ORACLE_40E_ETA_EPSILON_BRIDGE_PASS_PROBE_LOOP_WEAK"
        implication = (
            "Readable 40E realization works with gold labels, but the probe-predicted "
            "full loop is not strong enough under the preregistered gate."
        )
    else:
        status = "40E_ETA_EPSILON_BRIDGE_NOT_ESTABLISHED"
        implication = "This run did not establish the 40E eta-to-epsilon bridge under the likelihood gates."
    if key["probe_raw_delta_vs_none"] <= 0.03 and key["gold_raw_delta_vs_none"] <= 0.03:
        implication += " Raw CAS-symbol prefixes remain non-load-bearing."
    return status, implication


def summarize_correctness_buckets(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "all": summarize_case_subset(cases),
        "element_correct": summarize_case_subset([case for case in cases if case.get("element_correct") is True]),
        "operator_correct": summarize_case_subset([case for case in cases if case.get("operator_correct") is True]),
        "domain_correct": summarize_case_subset([case for case in cases if case.get("domain_correct") is True]),
        "element_wrong": summarize_case_subset([case for case in cases if case.get("element_correct") is False]),
    }


def summarize_case_subset(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {"n": 0, "status": "empty"}
    none = [float(case["condition_scores"]["none"]["margin"]) for case in cases]
    probe = [float(case["condition_scores"]["probe_readable"]["margin"]) for case in cases]
    gold = [float(case["condition_scores"]["gold_readable"]["margin"]) for case in cases]
    partner = [float(case["condition_scores"]["partner_readable"]["margin"]) for case in cases]
    return {
        "n": len(cases),
        "probe_readable_delta_vs_none": round(mean([p - b for p, b in zip(probe, none)]), 6),
        "gold_readable_delta_vs_none": round(mean([g - b for g, b in zip(gold, none)]), 6),
        "probe_readable_minus_partner_readable_margin": round(mean(probe) - mean(partner), 6),
        "mean_probe_readable_margin": round(mean(probe), 6),
        "mean_partner_readable_margin": round(mean(partner), 6),
    }


def summarize(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    return {
        "mean": round(float(arr.mean()) if arr.size else 0.0, 6),
        "std": round(float(arr.std(ddof=1)) if arr.size > 1 else 0.0, 6),
        "p05": round(float(np.quantile(arr, 0.05)) if arr.size else 0.0, 6),
        "p50": round(float(np.quantile(arr, 0.50)) if arr.size else 0.0, 6),
        "p95": round(float(np.quantile(arr, 0.95)) if arr.size else 0.0, 6),
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def sign_test_p(n_pos: int, n: int) -> float:
    if n <= 0:
        return 1.0
    return round(float(sum(math.comb(n, k) for k in range(n_pos, n + 1)) / (2**n)), 12)


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(accuracy_score(y_true, y_pred))


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> float:
    return float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Stage 9 40E Eta-To-Epsilon Bridge",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Readout",
        "",
        f"- Model: `{report['model_id']}`",
        f"- Axis: `{report['axis']}`",
        f"- Readout mode: `{report['readout_mode']}`",
        f"- Readout layer: `{report['readout_layer']}`",
        f"- Selected element accuracy: `{report['probe_prediction']['selected_element_accuracy']:.4f}`",
        f"- Selected operator accuracy: `{report['probe_prediction']['selected_operator_accuracy']:.4f}`",
        f"- Selected domain accuracy: `{report['probe_prediction']['selected_domain_accuracy']:.4f}`",
        f"- Filter coverage: `{report['readout_filter']['kept_cases']} / {report['readout_filter']['original_selected_cases']}` (`{report['readout_filter']['coverage']:.4f}`)",
        f"- Filter threshold: `{report['readout_filter']['effective_threshold']}` on `{report['readout_filter']['score']}`",
        "",
        "## Likelihood Conditions",
        "",
        "| Condition | Mean margin | Mean delta vs none | Positive rows | Sign p |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition, block in report["conditions"].items():
        lines.append(
            f"| {condition} | {block['margin']['mean']:.4f} | "
            f"{block['delta_vs_none']['mean']:.4f} | "
            f"{block['delta_positive_count']} / {report['n_cases']} | "
            f"{block['delta_positive_sign_p']:.6f} |"
        )
    lines.extend(["", "## Key Comparisons", ""])
    for name, value in report["key_comparisons"].items():
        lines.append(f"- `{name}`: `{value:.6f}`")
    lines.extend(["", "## Bridge Gates", ""])
    lines.append("| Loop | Gate | Value | Required | Pass |")
    lines.append("|---|---|---:|---:|---|")
    for loop_name, loop_gate in report.get("bridge_gates", {}).items():
        for gate_name, check in loop_gate.get("checks", {}).items():
            lines.append(
                f"| {loop_name} | {gate_name} | "
                f"{float(check['value']):.6f} | {check['operator']} {float(check['threshold']):.2f} | "
                f"{'yes' if check['passed'] else 'no'} |"
            )
    lines.extend(["", "## Correctness Buckets", ""])
    lines.append("| Bucket | Rows | Probe delta vs none | Probe minus partner | Gold delta vs none |")
    lines.append("|---|---:|---:|---:|---:|")
    for name, block in report.get("correctness_buckets", {}).items():
        if not block or block.get("n", 0) == 0:
            continue
        lines.append(
            f"| {name} | {block['n']} | "
            f"{block['probe_readable_delta_vs_none']:.4f} | "
            f"{block['probe_readable_minus_partner_readable_margin']:.4f} | "
            f"{block['gold_readable_delta_vs_none']:.4f} |"
        )
    lines.extend(["", "## Implication", "", report["implication"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
