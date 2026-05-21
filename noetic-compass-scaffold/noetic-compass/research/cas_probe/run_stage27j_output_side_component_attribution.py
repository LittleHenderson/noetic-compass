"""Stage 27J output-side component attribution for CPL2 likelihood.

Stage 27I showed that localized Layer-5 neuron-cover interventions do not
survive to the output-side likelihood path. Stage 27J searches that output
side directly: late attention heads and MLP blocks are ablated only at
continuation prediction positions, learned on half of the CPL2 rows, and
evaluated on held-out rows against matched random covers.

Boundary: this is late-layer component attribution for Pythia-160M likelihood
margins. It is not complete circuit discovery, not model-wide control, not
weight editing, and not visible free-form generation control.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
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


_HERE = Path(__file__).resolve().parent
_SEED = 27037
_EXPECTED_STAGE7_PREFIX_STATUS = "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD"
_EXPECTED_STAGE27I_STATUS = "NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED"


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _candidate_components(candidate_layers: tuple[int, ...]) -> list[Component]:
    components: list[Component] = []
    for layer in candidate_layers:
        components.extend(Component("head", int(layer), head) for head in range(12))
        components.append(Component("mlp", int(layer), None))
    return components


def _split_by_drive(rows: list[dict[str, Any]], learn_rows_per_drive: int, eval_rows_per_drive: int) -> dict[str, Any]:
    by_drive: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_drive[int(row["foundation_drive"])].append(row)
    learn: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    for drive in range(1, 8):
        drive_rows = by_drive[drive]
        need = learn_rows_per_drive + eval_rows_per_drive
        if len(drive_rows) < need:
            raise ValueError(f"drive {drive} has {len(drive_rows)} rows, need {need}")
        learn.extend(drive_rows[:learn_rows_per_drive])
        eval_rows.extend(drive_rows[learn_rows_per_drive:need])
    return {
        "learn_rows": learn,
        "eval_rows": eval_rows,
        "learn_ids": [str(row["sample_id"]) for row in learn],
        "eval_ids": [str(row["sample_id"]) for row in eval_rows],
        "learn_eval_disjoint": bool({str(row["sample_id"]) for row in learn}.isdisjoint({str(row["sample_id"]) for row in eval_rows})),
    }


def _prediction_positions(prompt_len: int, continuation_len: int) -> tuple[int, ...]:
    if prompt_len <= 0 or continuation_len <= 0:
        raise ValueError("prompt and continuation lengths must be positive")
    return tuple(prompt_len + offset - 1 for offset in range(continuation_len))


def _component_targets(components: list[Component]) -> tuple[dict[int, set[int]], set[int]]:
    head_targets: dict[int, set[int]] = {}
    mlp_targets: set[int] = set()
    for component in components:
        if component.kind == "head":
            if component.head is None:
                raise ValueError(f"head component missing head index: {component}")
            head_targets.setdefault(int(component.layer), set()).add(int(component.head))
        elif component.kind == "mlp":
            mlp_targets.add(int(component.layer))
        else:
            raise ValueError(f"unknown component kind {component.kind!r}")
    return head_targets, mlp_targets


def _score_continuation_component_ablated(
    model: Any,
    tokenizer: Any,
    prompt: str,
    continuation: str,
    device: Any,
    *,
    components: list[Component] | None = None,
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
    if components:
        layers = _model_layers(model)
        head_targets, mlp_targets = _component_targets(components)
        head_dim = int(model.config.hidden_size // model.config.num_attention_heads)

        def make_head_hook(layer_idx: int):
            targets = sorted(head_targets.get(layer_idx, set()))

            def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
                x = inputs[0].clone()
                for pos in pos_idx:
                    for head in targets:
                        start = int(head) * head_dim
                        stop = start + head_dim
                        x[:, pos, start:stop] = 0
                return (x,)

            return hook

        def make_mlp_hook(_layer_idx: int):
            def hook(_module: Any, _inputs: tuple[Any, ...], output: Any) -> Any:
                y = output.clone()
                for pos in pos_idx:
                    y[:, pos, :] = 0
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
    components: list[Component] | None = None,
) -> float:
    current = int(row["foundation_drive"])
    partner = _partner_drive(row)
    register = str(row["foundation_register"])
    prompt = _prefix("plain", current, register) + _base_prompt(row)
    correct_continuation = f" {_DRIVE_PHRASES[current]}."
    partner_continuation = f" {_DRIVE_PHRASES[partner]}."
    correct = _score_continuation_component_ablated(
        model, tokenizer, prompt, correct_continuation, device, components=components
    )
    wrong = _score_continuation_component_ablated(
        model, tokenizer, prompt, partner_continuation, device, components=components
    )
    return float(correct["mean_logprob"] - wrong["mean_logprob"])


def _learn_component_scores(
    learn_rows: list[dict[str, Any]],
    components: list[Component],
    model: Any,
    tokenizer: Any,
    device: Any,
) -> dict[str, Any]:
    base_margins = [_margin_for_row(row, model, tokenizer, device) for row in learn_rows]
    rows: list[dict[str, Any]] = []
    for component in components:
        drops: list[float] = []
        for row, base_margin in zip(learn_rows, base_margins):
            ablated_margin = _margin_for_row(row, model, tokenizer, device, components=[component])
            drops.append(float(base_margin - ablated_margin))
        mean_drop = float(np.mean(drops)) if drops else 0.0
        rows.append(
            {
                "component": component.name,
                "kind": component.kind,
                "layer": int(component.layer),
                "mean_drop": mean_drop,
                "mean_lift": float(-mean_drop),
                "positive_drop_share": float(np.mean(np.asarray(drops) > 0.0)) if drops else 0.0,
                "n": int(len(drops)),
            }
        )
    carrier_rank = sorted(rows, key=lambda item: item["mean_drop"], reverse=True)
    eraser_rank = sorted(rows, key=lambda item: item["mean_lift"], reverse=True)
    return {
        "prefix_margin": _margin_summary(base_margins),
        "component_scores": rows,
        "carrier_rank": carrier_rank,
        "eraser_rank": eraser_rank,
    }


def _matched_random_covers(
    selected_names: list[str],
    candidates: list[Component],
    *,
    n_random: int,
    seed: int,
) -> list[list[str]]:
    rng = np.random.default_rng(seed)
    by_signature: dict[tuple[str, int], list[str]] = defaultdict(list)
    by_kind: dict[str, list[str]] = defaultdict(list)
    selected = set(selected_names)
    for component in candidates:
        by_signature[(component.kind, int(component.layer))].append(component.name)
        by_kind[component.kind].append(component.name)
    covers: list[list[str]] = []
    for _ in range(n_random):
        used: set[str] = set()
        cover: list[str] = []
        for name in selected_names:
            component = _component_from_name(name)
            pool = [
                candidate
                for candidate in by_signature[(component.kind, int(component.layer))]
                if candidate not in selected and candidate not in used
            ]
            if not pool:
                # MLP blocks are singleton per layer, so an exact layer/kind
                # replacement can be impossible. Preserve kind before falling
                # back to a fully unmatched replacement.
                pool = [candidate for candidate in by_kind[component.kind] if candidate not in selected and candidate not in used]
            if not pool:
                pool = [
                    candidate
                    for values in by_signature.values()
                    for candidate in values
                    if candidate not in selected and candidate not in used
                ]
            if not pool:
                raise ValueError(f"could not construct matched random control for {name}")
            chosen = str(rng.choice(pool))
            cover.append(chosen)
            used.add(chosen)
        covers.append(cover)
    return covers


def _control_match_profile(selected_names: list[str], candidates: list[Component]) -> dict[str, Any]:
    by_signature: dict[tuple[str, int], list[str]] = defaultdict(list)
    by_kind: dict[str, list[str]] = defaultdict(list)
    selected = set(selected_names)
    for component in candidates:
        by_signature[(component.kind, int(component.layer))].append(component.name)
        by_kind[component.kind].append(component.name)
    rows: list[dict[str, Any]] = []
    for name in selected_names:
        component = _component_from_name(name)
        exact = [
            candidate
            for candidate in by_signature[(component.kind, int(component.layer))]
            if candidate not in selected
        ]
        kind_only = [candidate for candidate in by_kind[component.kind] if candidate not in selected]
        if exact:
            level = "layer_kind_exact"
        elif kind_only:
            level = "kind_only_singleton_layer"
        else:
            level = "unmatched_fallback"
        rows.append(
            {
                "component": name,
                "kind": component.kind,
                "layer": int(component.layer),
                "match_level": level,
                "exact_pool_size": int(len(exact)),
                "kind_pool_size": int(len(kind_only)),
            }
        )
    return {
        "policy": (
            "Random controls use same layer/kind replacements when available. For singleton MLP blocks, "
            "the fallback preserves kind across candidate layers; if that is impossible, the report marks an unmatched fallback."
        ),
        "rows": rows,
        "all_exact_layer_kind": bool(all(row["match_level"] == "layer_kind_exact" for row in rows)),
        "has_kind_only_singleton_fallback": bool(any(row["match_level"] == "kind_only_singleton_layer" for row in rows)),
        "has_unmatched_fallback": bool(any(row["match_level"] == "unmatched_fallback" for row in rows)),
    }


def _evaluate_cover(
    eval_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    cover_names: list[str],
    random_covers: list[list[str]],
) -> dict[str, Any]:
    components = [_component_from_name(name) for name in cover_names]
    prefix_margins: list[float] = []
    cover_margins: list[float] = []
    cover_drops: list[float] = []
    cover_lifts: list[float] = []
    random_mean_drops: list[float] = []
    random_mean_lifts: list[float] = []
    row_reports: list[dict[str, Any]] = []
    for row in eval_rows:
        base_margin = _margin_for_row(row, model, tokenizer, device)
        cover_margin = _margin_for_row(row, model, tokenizer, device, components=components)
        random_drops: list[float] = []
        random_lifts: list[float] = []
        for random_names in random_covers:
            random_margin = _margin_for_row(
                row,
                model,
                tokenizer,
                device,
                components=[_component_from_name(name) for name in random_names],
            )
            random_drops.append(float(base_margin - random_margin))
            random_lifts.append(float(random_margin - base_margin))
        drop = float(base_margin - cover_margin)
        lift = float(cover_margin - base_margin)
        random_drop = float(np.mean(random_drops)) if random_drops else 0.0
        random_lift = float(np.mean(random_lifts)) if random_lifts else 0.0
        prefix_margins.append(float(base_margin))
        cover_margins.append(float(cover_margin))
        cover_drops.append(drop)
        cover_lifts.append(lift)
        random_mean_drops.append(random_drop)
        random_mean_lifts.append(random_lift)
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "foundation_label": row["foundation_label"],
                "prefix_margin": float(base_margin),
                "cover_margin": float(cover_margin),
                "cover_drop": drop,
                "cover_lift": lift,
                "random_mean_drop": random_drop,
                "random_mean_lift": random_lift,
            }
        )
    return {
        "row_reports": row_reports,
        "margins": {"prefix": _margin_summary(prefix_margins), "cover_ablated": _margin_summary(cover_margins)},
        "drop": _margin_summary(cover_drops),
        "lift": _margin_summary(cover_lifts),
        "random_mean_drop": _margin_summary(random_mean_drops),
        "random_mean_lift": _margin_summary(random_mean_lifts),
        "drop_vs_random": _paired_summary(cover_drops, random_mean_drops),
        "lift_vs_random": _paired_summary(cover_lifts, random_mean_lifts),
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not all(block["formal_gate_valid"] for block in report["source_contracts"].values()):
        return "STAGE27J_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["split_contract"]["learn_eval_disjoint"]:
        return "NULL_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_SPLIT_INVALID"
    carrier_pair = report["evaluation"]["carrier_cover"]["drop_vs_random"]
    eraser_pair = report["evaluation"]["eraser_cover"]["lift_vs_random"]
    carrier_drop = report["evaluation"]["carrier_cover"]["drop"]
    eraser_lift = report["evaluation"]["eraser_cover"]["lift"]
    carrier_ok = (
        carrier_pair["win_share"] >= report["gates"]["min_random_win_share"]
        and carrier_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and carrier_drop["positive_share"] >= report["gates"]["min_positive_effect_share"]
        and carrier_drop["mean"] > report["evaluation"]["carrier_cover"]["random_mean_drop"]["mean"]
    )
    eraser_ok = (
        eraser_pair["win_share"] >= report["gates"]["min_random_win_share"]
        and eraser_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and eraser_lift["positive_share"] >= report["gates"]["min_positive_effect_share"]
        and eraser_lift["mean"] > report["evaluation"]["eraser_cover"]["random_mean_lift"]["mean"]
    )
    if carrier_ok and eraser_ok:
        return "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION"
    if carrier_ok or eraser_ok:
        return "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_ATTRIBUTION"
    if carrier_pair["win_share"] >= 0.55 or eraser_pair["win_share"] >= 0.55:
        return "GREY_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_PARTIAL"
    return "NULL_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, int(args.per_drive), int(args.selection_seed))
    split = _split_by_drive(selected, int(args.learn_rows_per_drive), int(args.eval_rows_per_drive))
    stage7_prefix_contract = _load_status_contract(
        _resolve(args.stage7_prefix_report), _EXPECTED_STAGE7_PREFIX_STATUS
    )
    stage27i_contract = _load_status_contract(_resolve(args.stage27i_report), _EXPECTED_STAGE27I_STATUS)
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    candidate_layers = tuple(int(x) for x in str(args.candidate_layers).split(",") if str(x).strip())
    candidates = _candidate_components(candidate_layers)
    learned = _learn_component_scores(split["learn_rows"], candidates, model, tokenizer, device)
    carrier_cover = [row["component"] for row in learned["carrier_rank"][: int(args.cover_size)]]
    eraser_cover = [row["component"] for row in learned["eraser_rank"][: int(args.cover_size)]]
    random_carrier = _matched_random_covers(
        carrier_cover, candidates, n_random=int(args.n_random_covers), seed=int(args.seed)
    )
    random_eraser = _matched_random_covers(
        eraser_cover, candidates, n_random=int(args.n_random_covers), seed=int(args.seed) + 1000
    )
    carrier_eval = _evaluate_cover(split["eval_rows"], model, tokenizer, device, carrier_cover, random_carrier)
    eraser_eval = _evaluate_cover(split["eval_rows"], model, tokenizer, device, eraser_cover, random_eraser)
    report: dict[str, Any] = {
        "schema_version": "stage27j_output_side_component_attribution.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model": model_meta,
        "source_contracts": {"stage7_prefix": stage7_prefix_contract, "stage27i": stage27i_contract},
        "candidate_layers": [int(layer) for layer in candidate_layers],
        "candidate_components": [component.name for component in candidates],
        "split_contract": {
            "per_drive": int(args.per_drive),
            "learn_rows_per_drive": int(args.learn_rows_per_drive),
            "eval_rows_per_drive": int(args.eval_rows_per_drive),
            "learn_rows": int(len(split["learn_rows"])),
            "eval_rows": int(len(split["eval_rows"])),
            "learn_eval_disjoint": bool(split["learn_eval_disjoint"]),
        },
        "learned_component_scores": {
            "prefix_margin": learned["prefix_margin"],
            "carrier_rank": learned["carrier_rank"],
            "eraser_rank": learned["eraser_rank"],
        },
        "cover_size": int(args.cover_size),
        "carrier_cover": carrier_cover,
        "eraser_cover": eraser_cover,
        "random_carrier_covers": random_carrier,
        "random_eraser_covers": random_eraser,
        "random_control_match_profile": {
            "carrier_cover": _control_match_profile(carrier_cover, candidates),
            "eraser_cover": _control_match_profile(eraser_cover, candidates),
        },
        "evaluation": {"carrier_cover": carrier_eval, "eraser_cover": eraser_eval},
        "gates": {
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_effect_share": float(args.min_positive_effect_share),
        },
        "boundary": (
            "Stage 27J is bounded late-layer output-side component attribution for Pythia-160M semantic likelihood "
            "margins. It is not complete circuit discovery, not model-wide control, not weight editing, and not "
            "visible free-form generation control."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    carrier = report["evaluation"]["carrier_cover"]
    eraser = report["evaluation"]["eraser_cover"]
    lines = [
        "# Stage 27J Output-Side Component Attribution",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 prefix source: `{report['source_contracts']['stage7_prefix']['source_status']}`",
        f"- Stage 27I source: `{report['source_contracts']['stage27i']['source_status']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        "",
        "## Learned Covers",
        "",
        f"- Carrier cover: {', '.join(f'`{name}`' for name in report['carrier_cover'])}",
        f"- Eraser cover: {', '.join(f'`{name}`' for name in report['eraser_cover'])}",
        f"- Carrier random-control exact layer/kind: `{report['random_control_match_profile']['carrier_cover']['all_exact_layer_kind']}`",
        f"- Eraser random-control exact layer/kind: `{report['random_control_match_profile']['eraser_cover']['all_exact_layer_kind']}`",
        "",
        "## Held-Out Evaluation",
        "",
        f"- Carrier drop mean: `{carrier['drop']['mean']:.6f}`",
        f"- Random carrier drop mean: `{carrier['random_mean_drop']['mean']:.6f}`",
        f"- Carrier drop > random: `{carrier['drop_vs_random']['wins']} / {carrier['drop_vs_random']['n']}` "
        f"(share `{carrier['drop_vs_random']['win_share']:.4f}`, p `{carrier['drop_vs_random']['sign_test_p']:.6g}`, mean delta `{carrier['drop_vs_random']['mean_delta']:.6f}`)",
        f"- Eraser lift mean: `{eraser['lift']['mean']:.6f}`",
        f"- Random eraser lift mean: `{eraser['random_mean_lift']['mean']:.6f}`",
        f"- Eraser lift > random: `{eraser['lift_vs_random']['wins']} / {eraser['lift_vs_random']['n']}` "
        f"(share `{eraser['lift_vs_random']['win_share']:.4f}`, p `{eraser['lift_vs_random']['sign_test_p']:.6g}`, mean delta `{eraser['lift_vs_random']['mean_delta']:.6f}`)",
        "",
        "## Top Learned Carrier Components",
        "",
    ]
    for row in report["learned_component_scores"]["carrier_rank"][:10]:
        lines.append(f"- `{row['component']}` mean_drop `{row['mean_drop']:.6f}` positive_share `{row['positive_drop_share']:.4f}`")
    lines.extend(["", "## Top Learned Eraser Components", ""])
    for row in report["learned_component_scores"]["eraser_rank"][:10]:
        lines.append(f"- `{row['component']}` mean_lift `{row['mean_lift']:.6f}`")
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--stage7-prefix-report", default="stage7_cas_prefix_likelihood_20260517.json")
    parser.add_argument("--stage27i-report", default="stage27i_prediction_position_steering_20260521.json")
    parser.add_argument("--out-report", default="stage27j_output_side_component_attribution_20260521.json")
    parser.add_argument("--out-md", default="STAGE27J_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_20260521.md")
    parser.add_argument("--candidate-layers", default="8,9,10,11")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--learn-rows-per-drive", type=int, default=8)
    parser.add_argument("--eval-rows-per-drive", type=int, default=8)
    parser.add_argument("--selection-seed", type=int, default=431)
    parser.add_argument("--cover-size", type=int, default=6)
    parser.add_argument("--n-random-covers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=_SEED)
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
                "carrier_cover": report["carrier_cover"],
                "eraser_cover": report["eraser_cover"],
                "carrier_drop": report["evaluation"]["carrier_cover"]["drop"]["mean"],
                "random_carrier_drop": report["evaluation"]["carrier_cover"]["random_mean_drop"]["mean"],
                "carrier_vs_random": report["evaluation"]["carrier_cover"]["drop_vs_random"],
                "eraser_lift": report["evaluation"]["eraser_cover"]["lift"]["mean"],
                "random_eraser_lift": report["evaluation"]["eraser_cover"]["random_mean_lift"]["mean"],
                "eraser_vs_random": report["evaluation"]["eraser_cover"]["lift_vs_random"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
