"""Stage 6.7: counterfactual focus-token activation patching.

This is a different causal test from Stage 6.6 ablation.

Instead of deleting the noetic subspace, it swaps the receiver's focus-token
hidden state with the donor's matched counterfactual focus-token hidden state.

Directional metric:

    directional_score = match(patched_output, donor_baseline)
                        - match(patched_output, receiver_baseline)

The true donor patch passes only if it moves the receiver continuation toward
the matched donor baseline more than random donor patches do.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 20260517
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 5
_HOOK_BLOCK_INDEX = _LAYER - 1
_PROMPT_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("in_other_words", "\nIn other words,"),
    ("focused_role_means", "\nThe focused role means"),
    ("concise_explanation", "\nA concise explanation is"),
)


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _find_focus_char_index(text: str, expected_focus: str) -> int:
    if expected_focus not in {"A", "B"}:
        raise ValueError(f"expected_focus must be A or B, got {expected_focus!r}")
    match = re.search(r"\bFocus:\s*([AB])\s*\.?\s*$", text)
    if not match:
        raise ValueError(f"missing terminal Focus marker in {text!r}")
    actual = match.group(1)
    if actual != expected_focus:
        raise ValueError(f"focus mismatch: expected {expected_focus!r}, found {actual!r}")
    return match.start(1)


def _find_token_for_char(offsets: list[tuple[int, int]], char_index: int) -> int:
    for i, (start, end) in enumerate(offsets):
        if start <= char_index < end:
            return i
    candidates = [
        (abs(start - char_index), i)
        for i, (start, end) in enumerate(offsets)
        if end > 0 and start <= char_index + 1
    ]
    if not candidates:
        raise ValueError(f"could not map char index {char_index} to token offsets")
    return min(candidates)[1]


def _split_indices(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> dict[str, Any]:
    import numpy as np

    split_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, sid in enumerate(sample_ids):
        split_to_indices[str(rows_by_id[sid]["split"])].append(i)
    return {split: np.array(indices, dtype=np.int64) for split, indices in split_to_indices.items()}


def _load_excluded_sample_ids(report_paths: list[str]) -> set[str]:
    excluded: set[str] = set()
    for report_path in report_paths:
        report = json.loads(_resolve(report_path).read_text(encoding="utf-8"))
        excluded.update(str(x) for x in report.get("selected_sample_ids", []))
    return excluded


def _partner_by_sample_id(rows: list[dict[str, Any]]) -> dict[str, str]:
    by_pair: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_pair[str(row["counterfactual_pair_id"])].append(str(row["sample_id"]))
    partner: dict[str, str] = {}
    for pair_id, ids in by_pair.items():
        if len(ids) != 2:
            continue
        a, b = ids
        partner[a] = b
        partner[b] = a
    return partner


def _select_receivers(
    sample_ids: list[str],
    y: Any,
    idx_test: Any,
    partner_by_id: dict[str, str],
    sample_id_to_index: dict[str, int],
    per_label: int,
    *,
    selection_mode: str,
    selection_seed: int,
    exclude_sample_ids: set[str],
) -> list[int]:
    import numpy as np

    by_label: dict[int, list[int]] = defaultdict(list)
    for idx in idx_test.tolist():
        sid = sample_ids[int(idx)]
        if sid in exclude_sample_ids:
            continue
        partner_id = partner_by_id.get(sid)
        if not partner_id or partner_id not in sample_id_to_index:
            continue
        by_label[int(y[idx])].append(int(idx))

    selected: list[int] = []
    rng = np.random.default_rng(selection_seed)
    for label in sorted(by_label):
        candidates = list(by_label[label])
        if selection_mode == "seeded":
            rng.shuffle(candidates)
        elif selection_mode != "first":
            raise ValueError(f"unsupported selection_mode: {selection_mode}")
        if len(candidates) < per_label:
            raise ValueError(
                f"not enough eligible receiver rows for label {label}: "
                f"need {per_label}, got {len(candidates)}"
            )
        selected.extend(candidates[:per_label])
    return selected


def _token_match_rate(a: list[int], b: list[int]) -> float:
    if not a and not b:
        return 1.0
    denom = max(len(a), len(b), 1)
    n = min(len(a), len(b))
    return sum(1 for i in range(n) if a[i] == b[i]) / denom


def _first_divergence(a: list[int], b: list[int]) -> int | None:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


def _softmax_kl(torch: Any, p_logits: Any, q_logits: Any) -> float:
    p = torch.softmax(p_logits.double(), dim=-1)
    q = torch.softmax(q_logits.double(), dim=-1)
    eps = 1e-30
    return float(
        torch.sum(
            p.clamp_min(eps)
            * (torch.log(p.clamp_min(eps)) - torch.log(q.clamp_min(eps)))
        ).item()
    )


def _summarize_patch_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {
            "cases": 0,
            "mean_directional_score": 0.0,
            "mean_donor_gain_vs_receiver_baseline": 0.0,
            "mean_receiver_disruption": 0.0,
            "first_step_top1_changed_rate": 0.0,
            "mean_first_step_kl": 0.0,
        }
    return {
        "cases": len(cases),
        "mean_directional_score": sum(float(c["directional_score"]) for c in cases) / len(cases),
        "mean_donor_gain_vs_receiver_baseline": sum(
            float(c["donor_gain_vs_receiver_baseline"]) for c in cases
        )
        / len(cases),
        "mean_receiver_disruption": sum(float(c["receiver_disruption"]) for c in cases)
        / len(cases),
        "first_step_top1_changed_rate": sum(
            1 for c in cases if not bool(c["first_step_top1_match_receiver"])
        )
        / len(cases),
        "mean_first_step_kl": sum(float(c["first_step_kl_receiver_to_patched"]) for c in cases)
        / len(cases),
        "receiver_first_token_distribution": dict(
            Counter(repr(c["receiver_first_top1_str"]) for c in cases)
        ),
        "patched_first_token_distribution": dict(
            Counter(repr(c["patched_first_top1_str"]) for c in cases)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--stage64-report", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--per-label", type=int, default=1)
    parser.add_argument("--n-random", type=int, default=3)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    parser.add_argument("--selection-mode", choices=["first", "seeded"], default="seeded")
    parser.add_argument("--selection-seed", type=int, default=_SEED)
    parser.add_argument("--exclude-report", action="append", default=[])
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    stage64_report_path = _resolve(args.stage64_report)
    out_report = _resolve(args.out_report)

    try:
        import numpy as np
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise SystemExit(f"missing dependency: {exc}") from exc

    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    partner_by_id = _partner_by_sample_id(rows)

    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    sample_id_to_index = {sid: i for i, sid in enumerate(sample_ids)}
    y = data["y"]
    splits = _split_indices(rows_by_id, sample_ids)
    idx_test = splits["test"]

    with stage64_report_path.open(encoding="utf-8") as fh:
        stage64 = json.load(fh)
    headline = stage64["headline"]
    if headline["readout"] != _READOUT_NAME or int(headline["layer"]) != _LAYER:
        raise SystemExit(
            f"Stage 6.7 is locked to {_READOUT_NAME} layer {_LAYER}; "
            f"Stage 6.4 report has {headline['readout']} layer {headline['layer']}"
        )

    exclude_sample_ids = _load_excluded_sample_ids(list(args.exclude_report))
    selected_indices = _select_receivers(
        sample_ids,
        y,
        idx_test,
        partner_by_id,
        sample_id_to_index,
        int(args.per_label),
        selection_mode=str(args.selection_mode),
        selection_seed=int(args.selection_seed),
        exclude_sample_ids=exclude_sample_ids,
    )
    selected_ids = [sample_ids[i] for i in selected_indices]

    rng = np.random.default_rng(int(args.selection_seed) + 17)
    test_pool = [int(i) for i in idx_test.tolist()]

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=True, use_fast=True)
    if not getattr(tokenizer, "is_fast", False):
        raise SystemExit("patching requires fast tokenizer offsets")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=True)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    block = model.gpt_neox.layers[_HOOK_BLOCK_INDEX]

    X_focus = data[_READOUT_KEY]

    def focus_token_index_for_prompt(prompt: str, base_text: str, expected_focus: str) -> int:
        focus_char = _find_focus_char_index(base_text, expected_focus)
        encoded = tokenizer(prompt, return_offsets_mapping=True, truncation=True, max_length=256)
        offsets = [(int(a), int(b)) for a, b in encoded["offset_mapping"]]
        return _find_token_for_char(offsets, focus_char)

    def make_patch_hook(donor_vector: Any, focus_token_index: int) -> Any:
        donor = torch.tensor(donor_vector, dtype=torch.float32, device=device).view(1, 1, -1)

        def hook(_module: Any, _input: Any, output: Any) -> Any:
            if isinstance(output, tuple):
                hs = output[0]
                if focus_token_index >= hs.shape[1]:
                    return output
                hs_patched = hs.clone()
                hs_patched[:, focus_token_index : focus_token_index + 1, :] = donor.to(hs.dtype)
                return (hs_patched,) + output[1:]
            if focus_token_index >= output.shape[1]:
                return output
            out_patched = output.clone()
            out_patched[:, focus_token_index : focus_token_index + 1, :] = donor.to(output.dtype)
            return out_patched

        return hook

    def greedy_continuation(prompt: str, donor_vector: Any | None, focus_token_index: int | None) -> dict[str, Any]:
        encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256).to(device)
        generated = encoded["input_ids"].clone()
        first_step_logits = None
        first_step_top1_id = None
        handle = None
        if donor_vector is not None:
            if focus_token_index is None:
                raise ValueError("focus_token_index required for patching")
            handle = block.register_forward_hook(make_patch_hook(donor_vector, focus_token_index))
        try:
            with torch.no_grad():
                for step in range(int(args.max_new_tokens)):
                    out = model(input_ids=generated)
                    logits = out.logits[:, -1, :]
                    if step == 0:
                        first_step_logits = logits.detach().cpu()
                    next_token = torch.argmax(logits, dim=-1, keepdim=True)
                    if step == 0:
                        first_step_top1_id = int(next_token.item())
                    generated = torch.cat([generated, next_token], dim=1)
        finally:
            if handle is not None:
                handle.remove()
        new_ids = generated[0, encoded["input_ids"].shape[1] :].detach().cpu().tolist()
        assert first_step_logits is not None
        assert first_step_top1_id is not None
        return {
            "new_token_ids": [int(x) for x in new_ids],
            "text": tokenizer.decode(new_ids),
            "first_step_logits": first_step_logits[0],
            "first_top1_id": int(first_step_top1_id),
            "first_top1_str": tokenizer.decode([first_step_top1_id]),
        }

    baseline_cache: dict[tuple[str, str], dict[str, Any]] = {}

    def baseline_for(sample_idx: int, template_name: str, suffix: str) -> dict[str, Any]:
        sid = sample_ids[sample_idx]
        key = (sid, template_name)
        if key not in baseline_cache:
            row = rows_by_id[sid]
            prompt = str(row["english"]).rstrip() + suffix
            baseline_cache[key] = greedy_continuation(prompt, None, None)
        return baseline_cache[key]

    true_patch_cases: list[dict[str, Any]] = []
    random_patch_cases_by_index: list[list[dict[str, Any]]] = [[] for _ in range(int(args.n_random))]
    reproducibility_cases: list[dict[str, Any]] = []
    started = time.perf_counter()

    for row_i, receiver_idx in enumerate(selected_indices):
        receiver_id = sample_ids[receiver_idx]
        donor_id = partner_by_id[receiver_id]
        donor_idx = sample_id_to_index[donor_id]
        receiver_row = rows_by_id[receiver_id]
        donor_row = rows_by_id[donor_id]

        excluded_indices = {int(receiver_idx), int(donor_idx)}
        random_candidates = [i for i in test_pool if i not in excluded_indices]
        random_indices = [int(x) for x in rng.choice(random_candidates, size=int(args.n_random), replace=False)]

        for template_name, suffix in _PROMPT_TEMPLATES:
            receiver_prompt = str(receiver_row["english"]).rstrip() + suffix
            receiver_focus_index = focus_token_index_for_prompt(
                receiver_prompt, str(receiver_row["english"]).rstrip(), str(receiver_row["focus_span"])
            )
            receiver_base_a = greedy_continuation(receiver_prompt, None, None)
            receiver_base_b = greedy_continuation(receiver_prompt, None, None)
            donor_base = baseline_for(donor_idx, template_name, suffix)

            repro_exact = receiver_base_a["new_token_ids"] == receiver_base_b["new_token_ids"]
            reproducibility_cases.append(
                {
                    "sample_id": receiver_id,
                    "template": template_name,
                    "exact_match": repro_exact,
                    "token_match_rate": _token_match_rate(
                        receiver_base_a["new_token_ids"], receiver_base_b["new_token_ids"]
                    ),
                }
            )

            donor_vector = X_focus[donor_idx, _LAYER, :]
            true_patch = greedy_continuation(receiver_prompt, donor_vector, receiver_focus_index)

            def build_case(kind: str, patched: dict[str, Any], patch_idx: int, random_index: int | None = None) -> dict[str, Any]:
                receiver_ids = receiver_base_a["new_token_ids"]
                donor_ids = donor_base["new_token_ids"]
                patched_ids = patched["new_token_ids"]
                patched_to_donor = _token_match_rate(patched_ids, donor_ids)
                patched_to_receiver = _token_match_rate(patched_ids, receiver_ids)
                receiver_to_donor = _token_match_rate(receiver_ids, donor_ids)
                return {
                    "receiver_sample_id": receiver_id,
                    "donor_sample_id": donor_id,
                    "patch_sample_id": sample_ids[patch_idx],
                    "receiver_true_y": int(receiver_row["noetic_label"]),
                    "donor_true_y": int(donor_row["noetic_label"]),
                    "patch_true_y": int(rows_by_id[sample_ids[patch_idx]]["noetic_label"]),
                    "template": template_name,
                    "intervention": kind,
                    "random_index": random_index,
                    "focus_token_index": int(receiver_focus_index),
                    "receiver_baseline_text": receiver_base_a["text"],
                    "donor_baseline_text": donor_base["text"],
                    "patched_text": patched["text"],
                    "receiver_baseline_token_ids": receiver_ids,
                    "donor_baseline_token_ids": donor_ids,
                    "patched_token_ids": patched_ids,
                    "receiver_to_donor_baseline_match": receiver_to_donor,
                    "patched_to_donor_match": patched_to_donor,
                    "patched_to_receiver_match": patched_to_receiver,
                    "directional_score": patched_to_donor - patched_to_receiver,
                    "donor_gain_vs_receiver_baseline": patched_to_donor - receiver_to_donor,
                    "receiver_disruption": 1.0 - patched_to_receiver,
                    "first_divergence_from_receiver": _first_divergence(receiver_ids, patched_ids),
                    "first_step_top1_match_receiver": patched["first_top1_id"]
                    == receiver_base_a["first_top1_id"],
                    "receiver_first_top1_id": receiver_base_a["first_top1_id"],
                    "receiver_first_top1_str": receiver_base_a["first_top1_str"],
                    "patched_first_top1_id": patched["first_top1_id"],
                    "patched_first_top1_str": patched["first_top1_str"],
                    "first_step_kl_receiver_to_patched": _softmax_kl(
                        torch, receiver_base_a["first_step_logits"], patched["first_step_logits"]
                    ),
                }

            true_patch_cases.append(build_case("matched_counterfactual_patch", true_patch, donor_idx))

            for rand_i, random_idx in enumerate(random_indices):
                random_vector = X_focus[random_idx, _LAYER, :]
                random_patch = greedy_continuation(receiver_prompt, random_vector, receiver_focus_index)
                random_patch_cases_by_index[rand_i].append(
                    build_case("random_donor_patch", random_patch, random_idx, random_index=rand_i)
                )

        done = row_i + 1
        if done % 5 == 0 or done == len(selected_indices):
            elapsed = time.perf_counter() - started
            print(f"[{done}/{len(selected_indices)} receiver rows] elapsed={elapsed:.1f}s")

    true_summary = _summarize_patch_cases(true_patch_cases)
    random_summaries = [_summarize_patch_cases(cases) for cases in random_patch_cases_by_index]
    random_mean_directional = sum(float(x["mean_directional_score"]) for x in random_summaries) / max(
        1, len(random_summaries)
    )
    random_mean_donor_gain = sum(
        float(x["mean_donor_gain_vs_receiver_baseline"]) for x in random_summaries
    ) / max(1, len(random_summaries))
    true_extra_directional = float(true_summary["mean_directional_score"] - random_mean_directional)
    true_extra_donor_gain = float(true_summary["mean_donor_gain_vs_receiver_baseline"] - random_mean_donor_gain)
    random_directional_scores = [float(x["mean_directional_score"]) for x in random_summaries]
    empirical_p_random_ge_true = float(
        (1 + sum(1 for score in random_directional_scores if score >= true_summary["mean_directional_score"]))
        / (len(random_directional_scores) + 1)
    )

    repro_exact_rate = sum(1 for c in reproducibility_cases if c["exact_match"]) / max(
        1, len(reproducibility_cases)
    )
    if repro_exact_rate < 1.0:
        status = "PATCHING_BASELINE_NOT_REPRODUCIBLE"
    elif true_extra_directional >= 0.03 and empirical_p_random_ge_true <= 0.05:
        status = "COUNTERFACTUAL_PATCH_DIRECTIONAL_EFFECT_ABOVE_RANDOM_CONTROL"
    elif true_extra_directional > 0.0:
        status = "COUNTERFACTUAL_PATCH_DIRECTIONAL_EFFECT_NUMERICAL_ONLY"
    else:
        status = "COUNTERFACTUAL_PATCH_DIRECTIONAL_EFFECT_NOT_ABOVE_RANDOM_CONTROL"

    report = {
        "schema_version": "stage6_counterfactual_focus_token_patch_report.v1",
        "experiment": "Stage 6.7 counterfactual focus-token patching",
        "status": status,
        "model_name": _MODEL_NAME,
        "device": str(device),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "stage64_report_file": stage64_report_path.name,
        "stage64_report_sha256": _sha256_of_file(stage64_report_path),
        "readout": _READOUT_NAME,
        "layer": _LAYER,
        "hook_block_index": _HOOK_BLOCK_INDEX,
        "hook_scope": "receiver_focus_token_replaced_with_donor_focus_vector",
        "per_label": int(args.per_label),
        "selection_mode": str(args.selection_mode),
        "selection_seed": int(args.selection_seed),
        "excluded_sample_ids": sorted(exclude_sample_ids),
        "n_selected_receivers": len(selected_indices),
        "selected_receiver_sample_ids": selected_ids,
        "prompt_templates": [{"name": name, "suffix": suffix} for name, suffix in _PROMPT_TEMPLATES],
        "max_new_tokens": int(args.max_new_tokens),
        "n_random_controls": int(args.n_random),
        "no_hook_reproducibility": {
            "cases": len(reproducibility_cases),
            "exact_match_rate": repro_exact_rate,
            "mean_token_match_rate": sum(float(c["token_match_rate"]) for c in reproducibility_cases)
            / max(1, len(reproducibility_cases)),
        },
        "true_patch_summary": true_summary,
        "random_patch_summaries": random_summaries,
        "comparison": {
            "random_mean_directional_score": random_mean_directional,
            "random_mean_donor_gain_vs_receiver_baseline": random_mean_donor_gain,
            "true_extra_directional_vs_random_mean": true_extra_directional,
            "true_extra_donor_gain_vs_random_mean": true_extra_donor_gain,
            "empirical_p_random_directional_ge_true": empirical_p_random_ge_true,
        },
        "reserved_interpretation": (
            "This test patches the matched donor focus-token activation into the receiver "
            "prompt and measures whether generated text moves toward the donor baseline "
            "more than random donor patches. It is separate from Stage 6.6 ablation."
        ),
        "elapsed_seconds": time.perf_counter() - started,
        "reproducibility_cases": reproducibility_cases,
        "true_patch_cases": true_patch_cases,
        "random_patch_cases_by_index": random_patch_cases_by_index,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "repro_exact_rate": repro_exact_rate,
                "true_mean_directional": true_summary["mean_directional_score"],
                "random_mean_directional": random_mean_directional,
                "true_extra_directional": true_extra_directional,
                "true_mean_donor_gain": true_summary["mean_donor_gain_vs_receiver_baseline"],
                "random_mean_donor_gain": random_mean_donor_gain,
                "empirical_p": empirical_p_random_ge_true,
                "receivers": len(selected_indices),
                "cases": true_summary["cases"],
            },
            indent=2,
        )
    )
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
