"""Run 27H-style forward-pass cover ablation on an open-weight model.

This is stronger than ``ablate_probe_dataset.py``: it suppresses candidate
cover coordinates during a fresh model forward pass and measures whether the
true CAS label/verbalizer likelihood drops more than matched controls.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_dataset_common import LabeledProbeScenario, load_labeled_scenarios  # noqa: E402
from run_open_weight_probe_shard import (  # noqa: E402
    ProbeShardConfig,
    first_real_parameter_device,
    inference_context,
    load_open_weight_model,
    locate_transformer_layers,
)

try:  # noqa: E402
    from scripts.ablate_probe_dataset import parse_cover_indices
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from ablate_probe_dataset import parse_cover_indices


DOMAIN_VERBALIZERS = {
    "P": "personal lived experience and perspective",
    "C": "conceptual thought and interpretation",
    "E": "evaluation, judgment, and value",
    "O": "practical operation and action",
}

REGISTER_VERBALIZERS = {
    "T": "meaning-level",
    "A": "analytical",
    "f": "felt",
    "E": "embodied",
}

DRIVE_VERBALIZERS = {
    "F1": "Unity, inclusion, protection, and connection",
    "F2": "Wisdom, facts, context, and uncertainty",
    "F3": "Vitality, harm, safety, health, and survival",
    "F4": "Connection, trust, empathy, and social pressure",
    "F5": "Agency, choice, consent, responsibility, and control",
    "F6": "Structure, rules, boundaries, safeguards, and constraints",
    "F7": "Purpose, larger goals, meaning, and long-term consequences",
}

OPERATOR_VERBALIZERS = {
    "^0": "presence, this is here",
    "^1": "identity, this is itself",
    "^2": "attraction, this speaks to me",
    "^3": "aversion, this rubs me the wrong way",
    "^4": "resonance, this struck a chord",
    "^5": "composition, putting pieces together",
    "^6": "decomposition, breaking it down",
    "^7": "habit or rhythm, getting into a groove",
    "^8": "triggering, that reminds me",
    "^9": "landing, it just clicked",
}


@dataclass(frozen=True)
class CoverAblationConfig:
    model_id: str
    scenario_path: Path
    cover_map_path: Path
    output: Path
    axis: str
    model_revision: str | None = None
    model_artifact_manifest_path: Path | None = None
    model_artifact_manifest_sha256: str | None = None
    torch_dtype: str = "float16"
    device_map: str = "auto"
    max_scenarios: int = 12
    max_length: int = 192
    ablation_gain: float = 1.0
    control_count: int = 5
    seed: int = 42
    trust_remote_code: bool = False


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--scenario-path", required=True, type=Path)
    parser.add_argument("--cover-map-path", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--axis", required=True, choices=("domain", "drive", "foundation", "operator"))
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--model-artifact-manifest-path", required=True, type=Path)
    parser.add_argument("--model-artifact-manifest-sha256", required=True)
    parser.add_argument("--torch-dtype", default="float16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--max-scenarios", type=int, default=12)
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument("--ablation-gain", type=float, default=1.0)
    parser.add_argument("--control-count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = CoverAblationConfig(
        model_id=args.model_id,
        scenario_path=args.scenario_path,
        cover_map_path=args.cover_map_path,
        output=args.output,
        axis=args.axis,
        model_revision=args.model_revision,
        model_artifact_manifest_path=args.model_artifact_manifest_path,
        model_artifact_manifest_sha256=args.model_artifact_manifest_sha256,
        torch_dtype=args.torch_dtype,
        device_map=args.device_map,
        max_scenarios=args.max_scenarios,
        max_length=args.max_length,
        ablation_gain=args.ablation_gain,
        control_count=args.control_count,
        seed=args.seed,
        trust_remote_code=args.trust_remote_code,
    )
    report = run_cover_ablation(config)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[cover-ablation] wrote {config.output}")
    return 0


def run_cover_ablation(config: CoverAblationConfig) -> dict[str, Any]:
    model_config = ProbeShardConfig(
        model_id=config.model_id,
        worker_id="local-cover-ablation",
        audit_id="open-weight-cover-ablation",
        job_id="manual-27h-equivalent",
        layer_start=0,
        layer_end=0,
        shard_id="cover-ablation",
        assigned_methods=("drive_local_eraser",),
        expected_outputs=("forward_pass_cover_ablation", "matched_random_controls", "worker_evidence_manifest"),
        result_path=config.output,
        model_revision=config.model_revision,
        model_artifact_manifest_path=config.model_artifact_manifest_path,
        model_artifact_manifest_sha256=config.model_artifact_manifest_sha256,
        torch_dtype=config.torch_dtype,
        device_map=config.device_map,
        max_scenarios=config.max_scenarios,
        max_length=config.max_length,
        trust_remote_code=config.trust_remote_code,
    )
    candidates = [
        scenario
        for scenario in load_labeled_scenarios(config.scenario_path)
        if scenario.labels.get(config.axis) in verbalizers_for_axis(config.axis)
    ]
    scenarios = select_balanced_scenarios(candidates, axis=config.axis, limit=config.max_scenarios)
    if not scenarios:
        raise RuntimeError(f"No scenarios with labels for axis={config.axis!r}.")

    cover_payload = json.loads(config.cover_map_path.read_text(encoding="utf-8"))
    cover_axis = cover_payload.get("covers", {}).get(config.axis)
    if not isinstance(cover_axis, dict):
        raise RuntimeError(f"Cover map missing covers.{config.axis}.")

    model, tokenizer, model_info = load_open_weight_model(model_config)
    layers = locate_transformer_layers(model)
    hidden_size = int(model_info.get("hidden_size") or 0)
    if hidden_size <= 0:
        raise RuntimeError("Model config did not expose hidden_size.")

    parsed_covers = parse_cover_axis(cover_axis, hidden_size=hidden_size)
    rows = []
    for index, scenario in enumerate(scenarios, start=1):
        label = scenario.labels[config.axis]
        target_coords = parsed_covers.get(label, [])
        if not target_coords:
            rows.append({"scenario_id": scenario.scenario_id, "label": label, "status": "missing_target_cover"})
            continue
        row = score_scenario(
            model=model,
            tokenizer=tokenizer,
            layers=layers,
            scenario=scenario,
            axis=config.axis,
            label=label,
            cover_coords_by_label=parsed_covers,
            hidden_size=hidden_size,
            max_length=config.max_length,
            gain=config.ablation_gain,
            control_count=config.control_count,
            rng=random.Random(config.seed + index),
        )
        print(
            "[cover-ablation] "
            f"{index}/{len(scenarios)} {scenario.scenario_id} {config.axis}={label} "
            f"target_drop={row['target_drop']:.6f} random_mean_drop={row['random_mean_drop']:.6f}",
            flush=True,
        )
        rows.append(row)

    summary = summarise_rows([row for row in rows if row.get("status") == "evaluated"])
    return {
        "schema_version": "cas_harness_open_weight_cover_ablation.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "real_model_forward_cover_ablation_completed",
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "model_info": model_info,
        "axis": config.axis,
        "scenario_path": str(config.scenario_path),
        "scenario_path_sha256": sha256_file(config.scenario_path),
        "cover_map_path": str(config.cover_map_path),
        "cover_map_sha256": sha256_file(config.cover_map_path),
        "scenario_count": len(rows),
        "ablation_gain": config.ablation_gain,
        "control_count": config.control_count,
        "max_length": config.max_length,
        "coordinate_space": "transformer_block_mlp_output_hidden_size",
        "produced_outputs": ["forward_pass_cover_ablation", "matched_random_controls", "worker_evidence_manifest"],
        "missing_outputs": ["verifier_accept_suppress_merge", "full_evidence_packet"],
        "important_limit": (
            "27H-style forward-pass candidate-cover intervention. This measures "
            "output likelihood shifts under cover suppression; it is not a final "
            "CAS Harness ACCEPT/SUPPRESS verdict until merged with the verifier."
        ),
        "summary": summary,
        "rows": rows,
    }


def parse_cover_axis(cover_axis: dict[str, Any], *, hidden_size: int) -> dict[str, list[tuple[int, int]]]:
    parsed: dict[str, list[tuple[int, int]]] = {}
    for label, info in cover_axis.items():
        if not isinstance(info, dict):
            continue
        layer = int(info.get("layer", -1))
        indices = parse_cover_indices(info.get("neuron_cover", []), expected_layer=layer, hidden_size=hidden_size)
        parsed[str(label)] = [(layer, index) for index in indices]
    return parsed


def select_balanced_scenarios(
    scenarios: list[LabeledProbeScenario],
    *,
    axis: str,
    limit: int,
) -> list[LabeledProbeScenario]:
    if limit <= 0 or len(scenarios) <= limit:
        return scenarios
    by_label: dict[str, list[LabeledProbeScenario]] = {}
    for scenario in scenarios:
        label = scenario.labels.get(axis)
        if label:
            by_label.setdefault(label, []).append(scenario)
    selected: list[LabeledProbeScenario] = []
    labels = sorted(by_label)
    cursor = 0
    while len(selected) < limit and any(by_label.values()):
        label = labels[cursor % len(labels)]
        bucket = by_label[label]
        if bucket:
            selected.append(bucket.pop(0))
        cursor += 1
    return selected


def score_scenario(
    *,
    model: Any,
    tokenizer: Any,
    layers: list[Any],
    scenario: LabeledProbeScenario,
    axis: str,
    label: str,
    cover_coords_by_label: dict[str, list[tuple[int, int]]],
    hidden_size: int,
    max_length: int,
    gain: float,
    control_count: int,
    rng: random.Random,
) -> dict[str, Any]:
    scoring_prompt, continuation = build_scoring_text(scenario.prompt, axis, label)
    target_coords = cover_coords_by_label[label]
    clean = continuation_logprob(
        model=model,
        tokenizer=tokenizer,
        prompt=scoring_prompt,
        continuation=continuation,
        layers=layers,
        max_length=max_length,
    )
    target = continuation_logprob(
        model=model,
        tokenizer=tokenizer,
        prompt=scoring_prompt,
        continuation=continuation,
        layers=layers,
        max_length=max_length,
        intervention=target_coords,
        gain=gain,
    )
    wrong_label = choose_wrong_label(label, cover_coords_by_label)
    wrong_coords = cover_coords_by_label.get(wrong_label, [])
    wrong = continuation_logprob(
        model=model,
        tokenizer=tokenizer,
        prompt=scoring_prompt,
        continuation=continuation,
        layers=layers,
        max_length=max_length,
        intervention=wrong_coords,
        gain=gain,
    )
    random_scores = []
    random_drops = []
    for _trial in range(max(1, control_count)):
        random_coords = random_like_cover(target_coords, hidden_size=hidden_size, rng=rng)
        scored = continuation_logprob(
            model=model,
            tokenizer=tokenizer,
            prompt=scoring_prompt,
            continuation=continuation,
            layers=layers,
            max_length=max_length,
            intervention=random_coords,
            gain=gain,
        )
        random_scores.append(round(scored, 6))
        random_drops.append(clean - scored)

    target_drop = clean - target
    wrong_drop = clean - wrong
    random_mean_drop = sum(random_drops) / len(random_drops)
    random_max_drop = max(random_drops)
    return {
        "status": "evaluated",
        "scenario_id": scenario.scenario_id,
        "axis": axis,
        "label": label,
        "target_cover_size": len(target_coords),
        "wrong_control_label": wrong_label,
        "scoring_prompt_sha256": sha256_text(scoring_prompt),
        "continuation": continuation,
        "clean_logprob": round(clean, 6),
        "target_ablated_logprob": round(target, 6),
        "wrong_control_logprob": round(wrong, 6),
        "random_control_logprobs": random_scores,
        "target_drop": round(target_drop, 6),
        "wrong_drop": round(wrong_drop, 6),
        "random_mean_drop": round(random_mean_drop, 6),
        "random_max_drop": round(random_max_drop, 6),
        "target_drop_minus_random_mean": round(target_drop - random_mean_drop, 6),
        "target_drop_minus_wrong_drop": round(target_drop - wrong_drop, 6),
        "target_beats_random_max": bool(target_drop > random_max_drop),
    }


def continuation_logprob(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    continuation: str,
    layers: list[Any],
    max_length: int,
    intervention: list[tuple[int, int]] | None = None,
    gain: float = 1.0,
) -> float:
    import torch

    prompt_ids = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)["input_ids"]
    full = tokenizer(prompt + continuation, return_tensors="pt", truncation=True, max_length=max_length)
    input_ids = full["input_ids"]
    if input_ids.shape[-1] <= prompt_ids.shape[-1]:
        raise RuntimeError("Continuation was truncated away; increase max_length or shorten prompt.")
    device = first_real_parameter_device(model)
    if device is not None:
        input_ids = input_ids.to(device)
    handles = []
    try:
        if intervention:
            for layer_idx, layer in enumerate(layers):
                coords = [index for layer, index in intervention if layer == layer_idx]
                if coords:
                    module = getattr(layer, "mlp", layer)
                    handles.append(module.register_forward_hook(make_eraser_hook(coords, gain=gain)))
        with inference_context():
            outputs = model(input_ids=input_ids, use_cache=False)
        logits = outputs.logits[:, :-1, :].float()
        labels = input_ids[:, 1:]
        start = max(0, int(prompt_ids.shape[-1]) - 1)
        continuation_logits = logits[:, start:, :]
        continuation_labels = labels[:, start:]
        log_probs = torch.log_softmax(continuation_logits, dim=-1)
        gathered = log_probs.gather(-1, continuation_labels.unsqueeze(-1)).squeeze(-1)
        return float(gathered.sum().detach().cpu().item())
    finally:
        for handle in handles:
            handle.remove()


def make_eraser_hook(indices: list[int], *, gain: float) -> Any:
    factor = max(0.0, 1.0 - max(0.0, float(gain)))
    valid = sorted({int(index) for index in indices if int(index) >= 0})

    def hook(_module: Any, _inputs: Any, output: Any) -> Any:
        value = output[0] if isinstance(output, tuple) else output
        width = int(value.shape[-1])
        clipped = [index for index in valid if index < width]
        if not clipped:
            return output
        modified = value.clone()
        modified[..., clipped] = modified[..., clipped] * factor
        if isinstance(output, tuple):
            return (modified, *output[1:])
        return modified

    return hook


def build_scoring_text(prompt: str, axis: str, label: str) -> tuple[str, str]:
    verbalizer = verbalizers_for_axis(axis)[label]
    axis_name = {"domain": "domain", "drive": "drive", "foundation": "foundation", "operator": "operator"}[axis]
    scoring_prompt = prompt.rstrip() + f"\n\nThe CAS {axis_name} most expressed here is:"
    return scoring_prompt, f" {label} {verbalizer}."


def verbalizers_for_axis(axis: str) -> dict[str, str]:
    if axis == "domain":
        return DOMAIN_VERBALIZERS
    if axis == "drive":
        return DRIVE_VERBALIZERS
    if axis == "foundation":
        return foundation_verbalizers()
    if axis == "operator":
        return OPERATOR_VERBALIZERS
    raise KeyError(axis)


def foundation_verbalizers() -> dict[str, str]:
    out: dict[str, str] = {}
    for drive, drive_text in DRIVE_VERBALIZERS.items():
        for register, register_text in REGISTER_VERBALIZERS.items():
            out[f"{drive}|{register}"] = f"{drive_text} in the {register_text} register"
    return out


def choose_wrong_label(label: str, cover_coords_by_label: dict[str, list[tuple[int, int]]]) -> str:
    candidates = sorted(candidate for candidate, coords in cover_coords_by_label.items() if candidate != label and coords)
    if not candidates:
        return label
    return candidates[0]


def random_like_cover(coords: list[tuple[int, int]], *, hidden_size: int, rng: random.Random) -> list[tuple[int, int]]:
    by_layer: dict[int, int] = {}
    for layer, _index in coords:
        by_layer[layer] = by_layer.get(layer, 0) + 1
    out: list[tuple[int, int]] = []
    for layer, count in sorted(by_layer.items()):
        count = min(count, hidden_size)
        for index in rng.sample(range(hidden_size), count):
            out.append((layer, index))
    return out


def summarise_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "no_evaluated_rows"}
    target_drops = [float(row["target_drop"]) for row in rows]
    random_mean_drops = [float(row["random_mean_drop"]) for row in rows]
    wrong_drops = [float(row["wrong_drop"]) for row in rows]
    target_minus_random = [float(row["target_drop_minus_random_mean"]) for row in rows]
    target_minus_wrong = [float(row["target_drop_minus_wrong_drop"]) for row in rows]
    wins_random = [bool(row["target_drop"] > row["random_mean_drop"]) for row in rows]
    wins_wrong = [bool(row["target_drop"] > row["wrong_drop"]) for row in rows]
    return {
        "status": "evaluated",
        "evaluated_rows": len(rows),
        "mean_target_drop": round(mean(target_drops), 6),
        "mean_random_control_drop": round(mean(random_mean_drops), 6),
        "mean_wrong_control_drop": round(mean(wrong_drops), 6),
        "mean_target_drop_minus_random": round(mean(target_minus_random), 6),
        "mean_target_drop_minus_wrong": round(mean(target_minus_wrong), 6),
        "target_drop_beats_random_mean_rows": int(sum(wins_random)),
        "target_drop_beats_wrong_rows": int(sum(wins_wrong)),
        "target_drop_beats_random_mean_rate": round(sum(wins_random) / len(rows), 6),
        "target_drop_beats_wrong_rate": round(sum(wins_wrong) / len(rows), 6),
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
