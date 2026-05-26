"""Run the Stage-7 eta-to-epsilon likelihood bridge on an open-weight model.

This ports the original Stage 7.CPL2 protocol into the live-trace-worker lane:

    scenario text -> hidden-state Foundation readout (eta)
    -> readable CAS realization prefix (epsilon)
    -> second model likelihood pass

The key condition is ``probe_readable``: the prefix is built from the probe's
predicted Foundation label, not the gold label. Gold prefixes are reported as
oracle upper-bound controls. Raw CAS-symbol prefixes are reported as a negative
control because the original Stage 7 chain found raw symbols were not the
load-bearing route.
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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_probe_dataset import fit_eval_centroid, predict_centroid  # noqa: E402
from run_open_weight_probe_shard import (  # noqa: E402
    ProbeShardConfig,
    first_real_parameter_device,
    inference_context,
    load_open_weight_model,
)


REGISTERS = ("T", "A", "f", "E")

REGISTER_GLOSSES = {
    "T": "highest purpose and sacred orientation",
    "A": "explicit reasoning and analysis",
    "f": "stored identity and familiar pattern",
    "E": "embodied action and practical contact",
}

DRIVE_PHRASES = {
    1: "belonging and ultimate orientation",
    2: "reward and positive attraction",
    3: "vitality and embodied life",
    4: "power and effective force",
    5: "structure and stable order",
    6: "making and productive formation",
    7: "rhythm and repeated timing",
}

DRIVE_PREFIX_GLOSSES = {
    1: "source-connection, union, and a pull toward what the mind belongs with",
    2: "liking, approach, appeal, and movement toward what is wanted",
    3: "life-energy, bodily aliveness, health, and active force",
    4: "capacity, strength, influence, and the ability to make something happen",
    5: "ordered form, bounded arrangement, stability, and reliable structure",
    6: "productive assembly, making, generative composition, and bringing parts together",
    7: "recurrence, tempo, practice, repetition, and patterned timing",
}


@dataclass(frozen=True)
class BridgeConfig:
    model_id: str
    scenario_path: Path
    dataset: Path
    eval_report: Path
    output: Path
    axis: str = "foundation"
    model_revision: str | None = None
    torch_dtype: str = "float16"
    device_map: str = "auto"
    per_drive: int = 16
    selection_seed: int = 449
    readout_seed: int = 42
    readout_layer: int | None = None
    min_readout_margin: float | None = None
    readout_margin_quantile: float | None = None
    max_length: int = 256
    trust_remote_code: bool = False
    output_md: Path | None = None


@dataclass(frozen=True)
class ScenarioMeta:
    scenario_id: str
    prompt: str
    split: str
    foundation: str
    partner_foundation: str
    pair_kind: str


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--scenario-path", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--eval-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--axis", default="foundation", choices=("foundation",))
    parser.add_argument("--model-revision")
    parser.add_argument("--torch-dtype", default="float16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--selection-seed", type=int, default=449)
    parser.add_argument("--readout-seed", type=int, default=42)
    parser.add_argument("--readout-layer", type=int)
    parser.add_argument(
        "--min-readout-margin",
        type=float,
        help="Keep only rows whose centroid readout margin is at least this value.",
    )
    parser.add_argument(
        "--readout-margin-quantile",
        type=float,
        help="Keep only rows at or above this selected-row readout-margin quantile, e.g. 0.5.",
    )
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
        axis=args.axis,
        model_revision=args.model_revision,
        torch_dtype=args.torch_dtype,
        device_map=args.device_map,
        per_drive=args.per_drive,
        selection_seed=args.selection_seed,
        readout_seed=args.readout_seed,
        readout_layer=args.readout_layer,
        min_readout_margin=args.min_readout_margin,
        readout_margin_quantile=args.readout_margin_quantile,
        max_length=args.max_length,
        trust_remote_code=args.trust_remote_code,
    )
    report = run_eta_epsilon_bridge(config)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if config.output_md:
        config.output_md.parent.mkdir(parents=True, exist_ok=True)
        config.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"[eta-epsilon] status={report['status']}")
    print(f"[eta-epsilon] wrote {config.output}")
    if config.output_md:
        print(f"[eta-epsilon] wrote {config.output_md}")
    return 0


def run_eta_epsilon_bridge(config: BridgeConfig) -> dict[str, Any]:
    started = time.perf_counter()
    scenario_meta = load_stage7_scenario_meta(config.scenario_path)
    with np.load(config.dataset, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        layers = np.asarray(data["layers"], dtype=int)
        scenario_ids = np.asarray(data["scenario_ids"], dtype=str)
        labels = np.asarray(data[f"labels_{config.axis}"], dtype=str)

    split = split_from_scenario_meta(scenario_ids, scenario_meta)
    readout_layer = config.readout_layer if config.readout_layer is not None else best_layer_from_eval(config.eval_report, config.axis)
    layer_positions = {int(layer): idx for idx, layer in enumerate(layers.tolist())}
    if readout_layer not in layer_positions:
        raise RuntimeError(f"Readout layer {readout_layer} not present in dataset layers {layers.tolist()}.")
    layer_position = layer_positions[readout_layer]
    metrics, model = fit_eval_centroid(features[:, layer_position, :], labels, split)
    predicted = predict_centroid(features[:, layer_position, :], model)
    readout_scores = centroid_readout_scores(features[:, layer_position, :], model)

    unfiltered_selected_indices = select_stage7_bridge_indices(
        scenario_ids=scenario_ids,
        labels=labels,
        split=split,
        scenario_meta=scenario_meta,
        per_drive=config.per_drive,
        seed=config.selection_seed,
    )
    selected_indices, readout_filter = apply_readout_filter(
        unfiltered_selected_indices,
        readout_scores,
        min_margin=config.min_readout_margin,
        margin_quantile=config.readout_margin_quantile,
    )
    if not selected_indices:
        raise RuntimeError("No Stage 7 same-register drive-cycle test rows survived selection/filtering.")

    model_config = ProbeShardConfig(
        model_id=config.model_id,
        worker_id="local-eta-epsilon",
        audit_id="open-weight-eta-epsilon-bridge",
        job_id="manual-stage7-cpl2-equivalent",
        layer_start=0,
        layer_end=0,
        shard_id="eta-epsilon",
        assigned_methods=("foundation_probe", "eta_epsilon_bridge"),
        expected_outputs=("foundation_readout", "eta_epsilon_likelihood_bridge", "worker_evidence_manifest"),
        result_path=config.output,
        model_revision=config.model_revision,
        torch_dtype=config.torch_dtype,
        device_map=config.device_map,
        max_scenarios=len(selected_indices),
        max_length=config.max_length,
        trust_remote_code=config.trust_remote_code,
    )
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
    selected_foundation_hits = 0
    selected_drive_hits = 0

    for case_number, idx in enumerate(selected_indices, start=1):
        sid = str(scenario_ids[int(idx)])
        meta = scenario_meta[sid]
        gold_label = canonical_foundation(labels[int(idx)])
        predicted_label = canonical_foundation(predicted[int(idx)])
        partner_label = canonical_foundation(meta.partner_foundation)
        gold_drive, _gold_register = parse_foundation_label(gold_label)
        predicted_drive, _predicted_register = parse_foundation_label(predicted_label)
        partner_drive, _partner_register = parse_foundation_label(partner_label)
        selected_foundation_hits += int(predicted_label == gold_label)
        selected_drive_hits += int(predicted_drive == gold_drive)

        correct_continuation = f" {DRIVE_PHRASES[gold_drive]}."
        partner_continuation = f" {DRIVE_PHRASES[partner_drive]}."
        case: dict[str, Any] = {
            "scenario_id": sid,
            "gold_label": gold_label,
            "predicted_label": predicted_label,
            "partner_label": partner_label,
            "gold_drive": gold_drive,
            "predicted_drive": predicted_drive,
            "partner_drive": partner_drive,
            "readout_confidence": readout_scores[int(idx)],
            "foundation_correct": predicted_label == gold_label,
            "drive_correct": predicted_drive == gold_drive,
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
            "[eta-epsilon] "
            f"{case_number}/{len(selected_indices)} {sid} "
            f"gold={gold_label} probe={predicted_label} "
            f"probe_readable_margin={case['condition_scores']['probe_readable']['margin']:.6f}",
            flush=True,
        )
        cases.append(case)

    summaries = summarize_conditions(margins_by_condition)
    key = key_comparisons(summaries)
    n_cases = len(selected_indices)
    selected_foundation_acc = selected_foundation_hits / max(n_cases, 1)
    selected_drive_acc = selected_drive_hits / max(n_cases, 1)
    gates = bridge_gates(summaries, key)
    status, implication = interpret_bridge_status(summaries, key)

    return {
        "schema_version": "cas_harness_open_weight_eta_epsilon_bridge.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "experiment": "Open-weight Stage 7 eta-to-epsilon likelihood bridge",
        "status": status,
        "plain_english_read": (
            "This is the original Stage 7 full-loop shape on an open-weight model: "
            "hidden states are read by a Foundation probe, the predicted Foundation "
            "label is realized into readable CAS context, and the model's conditional "
            "likelihood is measured against partner/raw controls."
        ),
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "model_info": model_info,
        "axis": config.axis,
        "scenario_path": str(config.scenario_path),
        "scenario_path_sha256": sha256_file(config.scenario_path),
        "dataset": str(config.dataset),
        "dataset_sha256": sha256_file(config.dataset),
        "eval_report": str(config.eval_report),
        "eval_report_sha256": sha256_file(config.eval_report),
        "readout_layer": int(readout_layer),
        "readout_layer_position": int(layer_position),
        "readout_seed": config.readout_seed,
        "selection_seed": config.selection_seed,
        "per_drive": config.per_drive,
        "readout_filter": readout_filter,
        "n_cases": n_cases,
        "probe_prediction": {
            "all_train_foundation_accuracy": metrics["train_acc"],
            "all_val_foundation_accuracy": metrics["val_acc"],
            "all_test_foundation_accuracy": metrics["test_acc"],
            "all_test_macro_f1": metrics["test_macro_f1"],
            "selected_foundation_accuracy": round(float(selected_foundation_acc), 6),
            "selected_drive_accuracy": round(float(selected_drive_acc), 6),
        },
        "conditions": summaries,
        "key_comparisons": key,
        "bridge_gates": gates,
        "correctness_buckets": summarize_correctness_buckets(cases),
        "cases": cases,
        "produced_outputs": ["foundation_readout", "eta_epsilon_likelihood_bridge", "worker_evidence_manifest"],
        "missing_outputs": ["verifier_accept_suppress_merge", "full_evidence_packet"],
        "important_limit": (
            "Likelihood-level eta-to-epsilon bridge evidence. This is not an "
            "ACCEPT/SUPPRESS verdict until merged with verifier and Evidence Packet layers."
        ),
        "implication": implication,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def load_stage7_scenario_meta(path: Path) -> dict[str, ScenarioMeta]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise RuntimeError("Scenario file must be a list or contain scenarios.")
    out: dict[str, ScenarioMeta] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or item.get("scenario_id") or f"scenario-{index + 1:04d}")
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        expected = item.get("expected_cas_axes") if isinstance(item.get("expected_cas_axes"), dict) else {}
        foundation = canonical_foundation(
            metadata.get("foundation")
            or metadata.get("foundation_label")
            or expected.get("foundation")
            or ""
        )
        partner = canonical_foundation(metadata.get("contrast_partner_foundation") or "")
        split = str(metadata.get("split") or item.get("split") or "").strip()
        pair_kind = str(metadata.get("pair_kind") or item.get("pair_kind") or "")
        prompt = str(item.get("prompt") or item.get("prompt_text") or item.get("text") or "").strip()
        if sid and prompt and foundation and partner and split:
            out[sid] = ScenarioMeta(
                scenario_id=sid,
                prompt=prompt,
                split=split,
                foundation=foundation,
                partner_foundation=partner,
                pair_kind=pair_kind,
            )
    if not out:
        raise RuntimeError("No Stage 7 scenario metadata found.")
    return out


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


def best_layer_from_eval(eval_report: Path, axis: str) -> int:
    payload = json.loads(eval_report.read_text(encoding="utf-8"))
    try:
        return int(payload["axes"][axis]["best_layer"]["layer"])
    except Exception as exc:
        raise RuntimeError(f"Could not resolve axes.{axis}.best_layer.layer from {eval_report}") from exc


def select_stage7_bridge_indices(
    *,
    scenario_ids: np.ndarray,
    labels: np.ndarray,
    split: dict[str, np.ndarray],
    scenario_meta: dict[str, ScenarioMeta],
    per_drive: int,
    seed: int,
) -> list[int]:
    test_lookup = set(int(idx) for idx in split["test"].tolist())
    by_drive: dict[int, list[int]] = defaultdict(list)
    for idx, sid in enumerate(scenario_ids.tolist()):
        if idx not in test_lookup:
            continue
        meta = scenario_meta[str(sid)]
        if not meta.pair_kind.startswith("same_register_drive_cycle_"):
            continue
        drive, _register = parse_foundation_label(labels[idx])
        by_drive[drive].append(idx)
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    for drive in range(1, 8):
        candidates = list(by_drive[drive])
        rng.shuffle(candidates)
        if len(candidates) < per_drive:
            raise RuntimeError(f"Drive {drive} needs {per_drive} bridge rows, got {len(candidates)}.")
        selected.extend(int(idx) for idx in candidates[:per_drive])
    return selected


def centroid_readout_scores(x: np.ndarray, model: dict[str, Any]) -> list[dict[str, Any]]:
    scaled = (x.astype(np.float32) - model["mean"]) / model["std"]
    classes = [str(label) for label in model["classes"]]
    centroid_matrix = np.stack([model["centroids"][label] for label in model["classes"]], axis=0)
    distances = ((scaled[:, None, :] - centroid_matrix[None, :, :]) ** 2).sum(axis=2)
    out: list[dict[str, Any]] = []
    for row in distances:
        order = np.argsort(row)
        best_idx = int(order[0])
        second_idx = int(order[1]) if len(order) > 1 else best_idx
        best_distance = float(row[best_idx])
        second_distance = float(row[second_idx])
        margin = second_distance - best_distance
        normalized_margin = margin / max(abs(second_distance), 1e-9)
        out.append(
            {
                "predicted_label": classes[best_idx],
                "runner_up_label": classes[second_idx],
                "best_distance": round(best_distance, 6),
                "runner_up_distance": round(second_distance, 6),
                "centroid_margin": round(float(margin), 6),
                "normalized_centroid_margin": round(float(normalized_margin), 6),
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
    margins = [float(readout_scores[int(idx)]["normalized_centroid_margin"]) for idx in indices]
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
            if float(readout_scores[int(idx)]["normalized_centroid_margin"]) >= threshold
        ]
        mode = "normalized_centroid_margin"
    return kept, {
        "mode": mode,
        "score": "normalized_centroid_margin",
        "min_readout_margin": min_margin,
        "readout_margin_quantile": margin_quantile,
        "effective_threshold": round(threshold, 6) if threshold is not None else None,
        "original_selected_cases": len(indices),
        "kept_cases": len(kept),
        "coverage": round(len(kept) / len(indices), 6) if indices else 0.0,
    }


def canonical_foundation(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "|" in text:
        drive, register = text.split("|", 1)
        if drive.startswith("F") and register in REGISTERS:
            return f"{drive}|{register}"
    if text.startswith("F") and len(text) >= 3:
        drive = text[:-1]
        register = text[-1]
        if drive.startswith("F") and register in REGISTERS:
            return f"{drive}|{register}"
    return ""


def parse_foundation_label(label: Any) -> tuple[int, str]:
    canonical = canonical_foundation(label)
    if not canonical:
        raise ValueError(f"Bad Foundation label: {label!r}")
    drive, register = canonical.split("|", 1)
    return int(drive[1:]), register


def raw_prefix(label: str) -> str:
    drive, register = parse_foundation_label(label)
    return f"CAS frame: F{drive}|{register}.\n"


def readable_prefix(label: str) -> str:
    drive, register = parse_foundation_label(label)
    return (
        "CAS realization frame for the focused role:\n"
        f"- Foundation code: F{drive}|{register}\n"
        f"- Drive: {DRIVE_PREFIX_GLOSSES[drive]}\n"
        f"- Register: {REGISTER_GLOSSES[register]}\n"
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


def base_prompt(prompt: str) -> str:
    return f"{prompt}\nThe focused role is about"


def mean_logprob_continuation(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    continuation: str,
    max_length: int,
) -> dict[str, Any]:
    import torch

    prompt_ids = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)["input_ids"]
    full = tokenizer(prompt + continuation, return_tensors="pt", truncation=True, max_length=max_length)
    input_ids = full["input_ids"]
    if input_ids.shape[-1] <= prompt_ids.shape[-1]:
        raise RuntimeError("Continuation was truncated away; increase max_length or shorten prompt.")
    device = first_real_parameter_device(model)
    if device is not None:
        input_ids = input_ids.to(device)
    with inference_context():
        outputs = model(input_ids=input_ids, use_cache=False)
    logits = outputs.logits[:, :-1, :].float()
    labels = input_ids[:, 1:]
    start = max(0, int(prompt_ids.shape[-1]) - 1)
    continuation_logits = logits[:, start:, :]
    continuation_labels = labels[:, start:]
    log_probs = torch.log_softmax(continuation_logits, dim=-1)
    gathered = log_probs.gather(-1, continuation_labels.unsqueeze(-1)).squeeze(-1)
    return {
        "mean_logprob": float(gathered.mean().detach().cpu().item()),
        "sum_logprob": float(gathered.sum().detach().cpu().item()),
        "n_tokens": int(continuation_labels.shape[-1]),
    }


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
        "probe_readable_delta_vs_none": round(
            float(summaries["probe_readable"]["delta_vs_none"]["mean"]), 6
        ),
        "probe_readable_minus_partner_readable_margin": round(
            float(summaries["probe_readable"]["margin"]["mean"])
            - float(summaries["partner_readable"]["margin"]["mean"]),
            6,
        ),
        "gold_readable_delta_vs_none": round(
            float(summaries["gold_readable"]["delta_vs_none"]["mean"]), 6
        ),
        "gold_readable_minus_partner_readable_margin": round(
            float(summaries["gold_readable"]["margin"]["mean"])
            - float(summaries["partner_readable"]["margin"]["mean"]),
            6,
        ),
        "probe_raw_delta_vs_none": round(float(summaries["probe_raw"]["delta_vs_none"]["mean"]), 6),
        "gold_raw_delta_vs_none": round(float(summaries["gold_raw"]["delta_vs_none"]["mean"]), 6),
    }


def summarize_correctness_buckets(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "all": summarize_case_subset(cases),
        "foundation_correct": summarize_case_subset([case for case in cases if case.get("foundation_correct") is True]),
        "drive_correct": summarize_case_subset([case for case in cases if case.get("drive_correct") is True]),
        "foundation_wrong": summarize_case_subset([case for case in cases if case.get("foundation_correct") is False]),
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


def interpret_bridge_status(summaries: dict[str, Any], key: dict[str, float]) -> tuple[str, str]:
    gates = bridge_gates(summaries, key)
    probe_pass = bool(gates["probe_readable"]["passed"])
    gold_pass = bool(gates["gold_readable"]["passed"])
    if probe_pass:
        status = "PROBE_PREDICTED_ETA_EPSILON_BRIDGE_PASS"
        implication = (
            "The full eta-to-epsilon loop works in this likelihood assay: the model's "
            "own hidden-state Foundation readout can be realized as readable CAS context, "
            "and that context moves semantic likelihood in the intended direction."
        )
    elif gold_pass:
        status = "ORACLE_ETA_EPSILON_BRIDGE_PASS_PROBE_LOOP_WEAK"
        implication = (
            "Readable CAS realization works with gold labels, but the probe-predicted "
            "full loop is not strong enough under the preregistered gate."
        )
    else:
        status = "ETA_EPSILON_BRIDGE_NOT_ESTABLISHED"
        implication = (
            "This run did not establish the full eta-to-epsilon bridge under the "
            "original Stage 7 likelihood gates."
        )
    if key["probe_raw_delta_vs_none"] <= 0.03 and key["gold_raw_delta_vs_none"] <= 0.03:
        implication += " Raw CAS-symbol prefixes remain non-load-bearing."
    return status, implication


def bridge_gates(summaries: dict[str, Any], key: dict[str, float]) -> dict[str, Any]:
    def gate(prefix: str) -> dict[str, Any]:
        delta_key = f"{prefix}_delta_vs_none"
        partner_key = f"{prefix}_minus_partner_readable_margin"
        sign_p = float(summaries[prefix]["delta_positive_sign_p"])
        checks = {
            "delta_vs_none": {
                "value": key[delta_key],
                "threshold": 0.20,
                "operator": ">",
                "passed": key[delta_key] > 0.20,
            },
            "minus_partner_readable_margin": {
                "value": key[partner_key],
                "threshold": 0.30,
                "operator": ">",
                "passed": key[partner_key] > 0.30,
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Open-Weight Eta-To-Epsilon Bridge",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Readout",
        "",
        f"- Model: `{report['model_id']}`",
        f"- Axis: `{report['axis']}`",
        f"- Readout layer: `{report['readout_layer']}`",
        f"- Selected Foundation accuracy: `{report['probe_prediction']['selected_foundation_accuracy']:.4f}`",
        f"- Selected Drive accuracy: `{report['probe_prediction']['selected_drive_accuracy']:.4f}`",
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
