"""Stage 27K output-side component steering for CPL2 likelihood.

Stage 27J identified late-layer carrier and eraser components for readable
prefix likelihood margins. Stage 27K tests whether those covers can be used as
an intervention surface: carrier components are amplified, eraser components
are suppressed, and the held-out margin lift is compared against matched random
component interventions.

Boundary: this is bounded late-layer intervention steering over Pythia-160M
CPL2 likelihood margins. It is not complete circuit discovery, not weight
editing, not model-wide control, and not visible free-form generation control.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import _load_jsonl
from probe_stage7_cas_prefix_likelihood import (
    _DRIVE_PHRASES,
    _base_prompt,
    _partner_drive,
    _prefix,
    _select_rows,
)
from run_stage26_component_attribution import Component, _component_from_name
from run_stage27c_per_class_component_covers import _margin_summary, _paired_summary
from run_stage27h_prefix_neuron_steering import _load_model_and_tokenizer, _load_status_contract, _model_layers
from run_stage27j_output_side_component_attribution import (
    _candidate_components,
    _control_match_profile,
    _matched_random_covers,
    _prediction_positions,
    _sha256_of_file,
    _split_by_drive,
)


_HERE = Path(__file__).resolve().parent
_SEED = 27038
_EXPECTED_STAGE7_PREFIX_STATUS = "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD"
_EXPECTED_STAGE27J_STATUS = "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION"


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_stage27j_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    status = str(report.get("status"))
    carrier_cover = [str(name) for name in report.get("carrier_cover", [])]
    eraser_cover = [str(name) for name in report.get("eraser_cover", [])]
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": status,
        "expected_status": _EXPECTED_STAGE27J_STATUS,
        "formal_gate_valid": bool(
            status == _EXPECTED_STAGE27J_STATUS and carrier_cover and eraser_cover
        ),
        "carrier_cover": carrier_cover,
        "eraser_cover": eraser_cover,
    }


def _component_scale_targets(
    component_scales: list[tuple[list[Component], float]] | None,
) -> tuple[dict[int, dict[int, float]], dict[int, float]]:
    head_targets: dict[int, dict[int, float]] = {}
    mlp_targets: dict[int, float] = {}
    for components, scale in component_scales or []:
        for component in components:
            if component.kind == "head":
                if component.head is None:
                    raise ValueError(f"head component missing head index: {component}")
                head_targets.setdefault(int(component.layer), {})[int(component.head)] = float(scale)
            elif component.kind == "mlp":
                mlp_targets[int(component.layer)] = float(scale)
            else:
                raise ValueError(f"unknown component kind {component.kind!r}")
    return head_targets, mlp_targets


def _score_continuation_component_scaled(
    model: Any,
    tokenizer: Any,
    prompt: str,
    continuation: str,
    device: Any,
    *,
    component_scales: list[tuple[list[Component], float]] | None = None,
) -> dict[str, Any]:
    import torch

    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    continuation_ids = tokenizer.encode(continuation, add_special_tokens=False)
    if not prompt_ids or not continuation_ids:
        raise ValueError("prompt and continuation must both tokenize non-empty")
    ids = prompt_ids + continuation_ids
    input_ids = torch.tensor([ids], dtype=torch.long, device=device)
    positions = _prediction_positions(len(prompt_ids), len(continuation_ids))
    pos_idx = [pos for pos in positions if 0 <= pos < len(ids)]
    handles = []
    if component_scales:
        layers = _model_layers(model)
        head_targets, mlp_targets = _component_scale_targets(component_scales)
        head_dim = int(model.config.hidden_size // model.config.num_attention_heads)

        def make_head_hook(layer_idx: int):
            targets = dict(head_targets.get(layer_idx, {}))

            def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
                x = inputs[0].clone()
                for pos in pos_idx:
                    for head, scale in targets.items():
                        start = int(head) * head_dim
                        stop = start + head_dim
                        x[:, pos, start:stop] = x[:, pos, start:stop] * float(scale)
                return (x,)

            return hook

        def make_mlp_hook(layer_idx: int):
            scale = float(mlp_targets[layer_idx])

            def hook(_module: Any, _inputs: tuple[Any, ...], output: Any) -> Any:
                y = output.clone()
                for pos in pos_idx:
                    y[:, pos, :] = y[:, pos, :] * scale
                return y

            return hook

        for layer_idx in sorted(head_targets):
            handles.append(layers[layer_idx].attention.dense.register_forward_pre_hook(make_head_hook(layer_idx)))
        for layer_idx in sorted(mlp_targets):
            handles.append(layers[layer_idx].mlp.register_forward_hook(make_mlp_hook(layer_idx)))
    try:
        with torch.no_grad():
            logits = model(input_ids=input_ids, use_cache=False).logits[0]
            log_probs = torch.log_softmax(logits, dim=-1)
    finally:
        for handle in handles:
            handle.remove()
    start = len(prompt_ids)
    token_logps: list[float] = []
    for offset, token_id in enumerate(continuation_ids):
        token_logps.append(float(log_probs[start + offset - 1, int(token_id)].detach().cpu().item()))
    return {
        "mean_logprob": float(np.mean(token_logps)),
        "sum_logprob": float(np.sum(token_logps)),
        "n_tokens": int(len(continuation_ids)),
        "prediction_positions": [int(pos) for pos in positions],
    }


def _margin_for_row(
    row: dict[str, Any],
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    component_scales: list[tuple[list[Component], float]] | None = None,
) -> float:
    current = int(row["foundation_drive"])
    partner = _partner_drive(row)
    register = str(row["foundation_register"])
    prompt = _prefix("plain", current, register) + _base_prompt(row)
    correct_continuation = f" {_DRIVE_PHRASES[current]}."
    partner_continuation = f" {_DRIVE_PHRASES[partner]}."
    correct = _score_continuation_component_scaled(
        model, tokenizer, prompt, correct_continuation, device, component_scales=component_scales
    )
    wrong = _score_continuation_component_scaled(
        model, tokenizer, prompt, partner_continuation, device, component_scales=component_scales
    )
    return float(correct["mean_logprob"] - wrong["mean_logprob"])


def _names_to_components(names: list[str]) -> list[Component]:
    return [_component_from_name(name) for name in names]


def _evaluate(
    eval_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    carrier_cover: list[str],
    eraser_cover: list[str],
    random_carrier_covers: list[list[str]],
    random_eraser_covers: list[list[str]],
    carrier_scale: float,
    eraser_scale: float,
    carrier_flip_scale: float,
) -> dict[str, Any]:
    carrier_components = _names_to_components(carrier_cover)
    eraser_components = _names_to_components(eraser_cover)
    prefix_margins: list[float] = []
    carrier_amp_increments: list[float] = []
    eraser_suppress_increments: list[float] = []
    combined_increments: list[float] = []
    random_combined_mean_increments: list[float] = []
    carrier_flip_reductions: list[float] = []
    random_carrier_flip_mean_reductions: list[float] = []
    row_reports: list[dict[str, Any]] = []

    for row in eval_rows:
        prefix_margin = _margin_for_row(row, model, tokenizer, device)
        carrier_amp_margin = _margin_for_row(
            row,
            model,
            tokenizer,
            device,
            component_scales=[(carrier_components, carrier_scale)],
        )
        eraser_suppress_margin = _margin_for_row(
            row,
            model,
            tokenizer,
            device,
            component_scales=[(eraser_components, eraser_scale)],
        )
        combined_margin = _margin_for_row(
            row,
            model,
            tokenizer,
            device,
            component_scales=[(carrier_components, carrier_scale), (eraser_components, eraser_scale)],
        )
        carrier_flip_margin = _margin_for_row(
            row,
            model,
            tokenizer,
            device,
            component_scales=[(carrier_components, carrier_flip_scale)],
        )
        random_combined_increments: list[float] = []
        random_flip_reductions: list[float] = []
        for random_carrier, random_eraser in zip(random_carrier_covers, random_eraser_covers):
            random_combined_margin = _margin_for_row(
                row,
                model,
                tokenizer,
                device,
                component_scales=[
                    (_names_to_components(random_carrier), carrier_scale),
                    (_names_to_components(random_eraser), eraser_scale),
                ],
            )
            random_flip_margin = _margin_for_row(
                row,
                model,
                tokenizer,
                device,
                component_scales=[(_names_to_components(random_carrier), carrier_flip_scale)],
            )
            random_combined_increments.append(float(random_combined_margin - prefix_margin))
            random_flip_reductions.append(float(prefix_margin - random_flip_margin))

        carrier_amp_increment = float(carrier_amp_margin - prefix_margin)
        eraser_suppress_increment = float(eraser_suppress_margin - prefix_margin)
        combined_increment = float(combined_margin - prefix_margin)
        random_combined_increment = float(np.mean(random_combined_increments)) if random_combined_increments else 0.0
        carrier_flip_reduction = float(prefix_margin - carrier_flip_margin)
        random_flip_reduction = float(np.mean(random_flip_reductions)) if random_flip_reductions else 0.0
        prefix_margins.append(float(prefix_margin))
        carrier_amp_increments.append(carrier_amp_increment)
        eraser_suppress_increments.append(eraser_suppress_increment)
        combined_increments.append(combined_increment)
        random_combined_mean_increments.append(random_combined_increment)
        carrier_flip_reductions.append(carrier_flip_reduction)
        random_carrier_flip_mean_reductions.append(random_flip_reduction)
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "foundation_label": row["foundation_label"],
                "prefix_margin": float(prefix_margin),
                "carrier_amp_increment": carrier_amp_increment,
                "eraser_suppress_increment": eraser_suppress_increment,
                "combined_increment": combined_increment,
                "random_combined_mean_increment": random_combined_increment,
                "carrier_flip_reduction": carrier_flip_reduction,
                "random_carrier_flip_mean_reduction": random_flip_reduction,
            }
        )

    return {
        "row_reports": row_reports,
        "effects": {
            "prefix_margin": _margin_summary(prefix_margins),
            "carrier_amplification_increment": _margin_summary(carrier_amp_increments),
            "eraser_suppression_increment": _margin_summary(eraser_suppress_increments),
            "combined_increment": _margin_summary(combined_increments),
            "random_combined_mean_increment": _margin_summary(random_combined_mean_increments),
            "carrier_flip_reduction": _margin_summary(carrier_flip_reductions),
            "random_carrier_flip_mean_reduction": _margin_summary(random_carrier_flip_mean_reductions),
        },
        "paired_controls": {
            "combined_vs_random_mean": _paired_summary(combined_increments, random_combined_mean_increments),
            "carrier_flip_vs_random_mean": _paired_summary(
                carrier_flip_reductions, random_carrier_flip_mean_reductions
            ),
        },
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not all(block["formal_gate_valid"] for block in report["source_contracts"].values()):
        return "STAGE27K_OUTPUT_SIDE_COMPONENT_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["split_contract"]["held_out_eval_only"]:
        return "NULL_OUTPUT_SIDE_COMPONENT_STEERING_SPLIT_INVALID"
    effects = report["evaluation"]["effects"]
    paired = report["evaluation"]["paired_controls"]
    combined = paired["combined_vs_random_mean"]
    polarity = paired["carrier_flip_vs_random_mean"]
    combined_ok = (
        combined["win_share"] >= report["gates"]["min_random_win_share"]
        and combined["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and effects["combined_increment"]["mean"] > 0.0
        and effects["combined_increment"]["positive_share"] >= report["gates"]["min_positive_effect_share"]
        and effects["combined_increment"]["mean"] > effects["random_combined_mean_increment"]["mean"]
    )
    polarity_ok = (
        polarity["win_share"] >= report["gates"]["min_random_win_share"]
        and polarity["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and effects["carrier_flip_reduction"]["positive_share"] >= report["gates"]["min_positive_effect_share"]
        and effects["carrier_flip_reduction"]["mean"] > effects["random_carrier_flip_mean_reduction"]["mean"]
    )
    if combined_ok and polarity_ok:
        return "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_STEERING_WITH_POLARITY_CONTROL"
    if combined_ok:
        return "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_STEERING"
    if combined["win_share"] >= 0.55 or effects["combined_increment"]["mean"] > 0.0:
        return "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL"
    return "NULL_OUTPUT_SIDE_COMPONENT_STEERING_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, int(args.per_drive), int(args.selection_seed))
    split = _split_by_drive(selected, int(args.learn_rows_per_drive), int(args.eval_rows_per_drive))
    eval_rows = split["eval_rows"]
    stage7_prefix_contract = _load_status_contract(
        _resolve(args.stage7_prefix_report), _EXPECTED_STAGE7_PREFIX_STATUS
    )
    stage27j_contract = _load_stage27j_contract(_resolve(args.stage27j_report))
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    candidate_layers = tuple(int(x) for x in str(args.candidate_layers).split(",") if str(x).strip())
    candidates = _candidate_components(candidate_layers)
    carrier_cover = stage27j_contract["carrier_cover"]
    eraser_cover = stage27j_contract["eraser_cover"]
    random_carrier = _matched_random_covers(
        carrier_cover, candidates, n_random=int(args.n_random_covers), seed=int(args.seed)
    )
    random_eraser = _matched_random_covers(
        eraser_cover, candidates, n_random=int(args.n_random_covers), seed=int(args.seed) + 1000
    )
    evaluation = _evaluate(
        eval_rows,
        model,
        tokenizer,
        device,
        carrier_cover=carrier_cover,
        eraser_cover=eraser_cover,
        random_carrier_covers=random_carrier,
        random_eraser_covers=random_eraser,
        carrier_scale=float(args.carrier_scale),
        eraser_scale=float(args.eraser_scale),
        carrier_flip_scale=float(args.carrier_flip_scale),
    )
    report: dict[str, Any] = {
        "schema_version": "stage27k_output_side_component_steering.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model": model_meta,
        "source_contracts": {"stage7_prefix": stage7_prefix_contract, "stage27j": stage27j_contract},
        "candidate_layers": [int(layer) for layer in candidate_layers],
        "split_contract": {
            "per_drive": int(args.per_drive),
            "learn_rows_per_drive": int(args.learn_rows_per_drive),
            "eval_rows_per_drive": int(args.eval_rows_per_drive),
            "eval_rows": int(len(eval_rows)),
            "held_out_eval_only": bool(split["learn_eval_disjoint"] and len(eval_rows) > 0),
            "eval_ids": split["eval_ids"],
        },
        "intervention": {
            "carrier_scale": float(args.carrier_scale),
            "eraser_scale": float(args.eraser_scale),
            "carrier_flip_scale": float(args.carrier_flip_scale),
            "positions": "continuation_prediction_positions_only",
        },
        "carrier_cover": carrier_cover,
        "eraser_cover": eraser_cover,
        "random_carrier_covers": random_carrier,
        "random_eraser_covers": random_eraser,
        "random_control_match_profile": {
            "carrier_cover": _control_match_profile(carrier_cover, candidates),
            "eraser_cover": _control_match_profile(eraser_cover, candidates),
        },
        "evaluation": evaluation,
        "gates": {
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_effect_share": float(args.min_positive_effect_share),
        },
        "boundary": (
            "Stage 27K is bounded late-layer intervention steering over Pythia-160M CPL2 likelihood margins. "
            "It is not complete circuit discovery, not weight editing, not model-wide control, not cross-model "
            "control, and not visible free-form generation control."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    effects = report["evaluation"]["effects"]
    paired = report["evaluation"]["paired_controls"]
    lines = [
        "# Stage 27K Output-Side Component Steering",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 prefix source: `{report['source_contracts']['stage7_prefix']['source_status']}`",
        f"- Stage 27J source: `{report['source_contracts']['stage27j']['source_status']}`",
        f"- Held-out eval only: `{report['split_contract']['held_out_eval_only']}`",
        "",
        "## Covers",
        "",
        f"- Carrier cover: {', '.join(f'`{name}`' for name in report['carrier_cover'])}",
        f"- Eraser cover: {', '.join(f'`{name}`' for name in report['eraser_cover'])}",
        f"- Carrier scale: `{report['intervention']['carrier_scale']}`",
        f"- Eraser scale: `{report['intervention']['eraser_scale']}`",
        f"- Carrier flip scale: `{report['intervention']['carrier_flip_scale']}`",
        "",
        "## Held-Out Evaluation",
        "",
        f"- Combined increment mean: `{effects['combined_increment']['mean']:.6f}`",
        f"- Random combined increment mean: `{effects['random_combined_mean_increment']['mean']:.6f}`",
        f"- Combined > random: `{paired['combined_vs_random_mean']['wins']} / {paired['combined_vs_random_mean']['n']}` "
        f"(share `{paired['combined_vs_random_mean']['win_share']:.4f}`, p `{paired['combined_vs_random_mean']['sign_test_p']:.6g}`, mean delta `{paired['combined_vs_random_mean']['mean_delta']:.6f}`)",
        f"- Carrier amplification increment mean: `{effects['carrier_amplification_increment']['mean']:.6f}`",
        f"- Eraser suppression increment mean: `{effects['eraser_suppression_increment']['mean']:.6f}`",
        f"- Carrier flip reduction mean: `{effects['carrier_flip_reduction']['mean']:.6f}`",
        f"- Random carrier flip reduction mean: `{effects['random_carrier_flip_mean_reduction']['mean']:.6f}`",
        f"- Carrier flip > random: `{paired['carrier_flip_vs_random_mean']['wins']} / {paired['carrier_flip_vs_random_mean']['n']}` "
        f"(share `{paired['carrier_flip_vs_random_mean']['win_share']:.4f}`, p `{paired['carrier_flip_vs_random_mean']['sign_test_p']:.6g}`, mean delta `{paired['carrier_flip_vs_random_mean']['mean_delta']:.6f}`)",
        "",
        "## Boundary",
        "",
        report["boundary"],
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--stage7-prefix-report", default="stage7_cas_prefix_likelihood_20260517.json")
    parser.add_argument("--stage27j-report", default="stage27j_output_side_component_attribution_20260521.json")
    parser.add_argument("--out-report", default="stage27k_output_side_component_steering_20260521.json")
    parser.add_argument("--out-md", default="STAGE27K_OUTPUT_SIDE_COMPONENT_STEERING_20260521.md")
    parser.add_argument("--candidate-layers", default="8,9,10,11")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--learn-rows-per-drive", type=int, default=8)
    parser.add_argument("--eval-rows-per-drive", type=int, default=8)
    parser.add_argument("--selection-seed", type=int, default=431)
    parser.add_argument("--n-random-covers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--carrier-scale", type=float, default=2.0)
    parser.add_argument("--eraser-scale", type=float, default=0.0)
    parser.add_argument("--carrier-flip-scale", type=float, default=-1.0)
    parser.add_argument("--min-random-win-share", type=float, default=0.60)
    parser.add_argument("--max-sign-test-p", type=float, default=0.05)
    parser.add_argument("--min-positive-effect-share", type=float, default=0.55)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(
        json.dumps(
            {
                "status": report["status"],
                "combined_increment": report["evaluation"]["effects"]["combined_increment"]["mean"],
                "random_combined_increment": report["evaluation"]["effects"]["random_combined_mean_increment"]["mean"],
                "combined_vs_random": report["evaluation"]["paired_controls"]["combined_vs_random_mean"],
                "carrier_flip_reduction": report["evaluation"]["effects"]["carrier_flip_reduction"]["mean"],
                "random_carrier_flip_reduction": report["evaluation"]["effects"]["random_carrier_flip_mean_reduction"]["mean"],
                "carrier_flip_vs_random": report["evaluation"]["paired_controls"]["carrier_flip_vs_random_mean"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

