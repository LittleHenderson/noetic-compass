"""Stage 7.3: Drive-only focus-token-localized generation hook.

Stage 7.2 showed that the Drive factor is the cleanest part of the
28-Foundation result:

* activation readout beats text by +22.3 points,
* activation readout beats metadata by +22.4 points,
* Drive-subspace ablation drops the readout to exact chance.

This script asks the next, harder question:

    If we remove the Drive readout subspace at the terminal Focus: A/B
    token while Pythia generates a continuation, does the text change
    more than it changes under same-rank random complement removals?

This is still not semantic steering. A pass here means "Drive removal
has a generated-language effect above random controls." It does not mean
"CAS can steer Pythia toward a chosen Drive."
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 11037
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 6
_HOOK_BLOCK_INDEX = _LAYER - 1
_DRIVE_LABELS = tuple(f"F{drive}" for drive in range(1, 8))
_PROMPT_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("in_other_words", "\nIn other words,"),
    ("focused_role_means", "\nThe focused role means"),
    ("concise_explanation", "\nA concise explanation is"),
)
_GATES = {
    "min_extra_divergence_vs_random_mean": 0.05,
    "empirical_p_random_le_drive_max": 0.05,
    "paired_case_sign_p_max": 0.05,
}


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
        if sid not in rows_by_id:
            raise ValueError(f"activation sample_id missing from input JSONL: {sid}")
        split_to_indices[str(rows_by_id[sid]["split"])].append(i)
    missing = sorted({"train", "val", "test"} - set(split_to_indices))
    if missing:
        raise ValueError(f"missing required splits: {missing}")
    return {split: np.array(indices, dtype=np.int64) for split, indices in split_to_indices.items()}


def _drive_labels(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> Any:
    import numpy as np

    return np.array([int(rows_by_id[sid]["foundation_drive"]) - 1 for sid in sample_ids], dtype=np.int64)


def _fit_drive_projection(X: Any, y_drive: Any, idx_train: Any) -> dict[str, Any]:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X[idx_train])
    clf = LogisticRegression(
        solver="lbfgs",
        max_iter=3000,
        class_weight="balanced",
        random_state=42,
    )
    clf.fit(X_train, y_drive[idx_train])
    sigma = scaler.scale_
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = clf.coef_ / sigma_safe[None, :]
    _u, s, vh = np.linalg.svd(w_raw, full_matrices=False)
    threshold = float(s.max() * 1e-6)
    basis_rows = vh[s > threshold]
    if basis_rows.size == 0:
        raise ValueError("no non-zero Drive probe directions found")
    return {
        "projection": basis_rows.T @ basis_rows,
        "basis_rows": basis_rows,
        "rank": int(basis_rows.shape[0]),
        "singular_values": [float(x) for x in s.tolist()],
        "threshold": threshold,
    }


def _select_drive_contrast_subset(
    rows_by_id: dict[str, dict[str, Any]],
    sample_ids: list[str],
    y_drive: Any,
    idx_test: Any,
    per_drive: int,
    seed: int,
) -> list[int]:
    import numpy as np

    by_drive: dict[int, list[int]] = defaultdict(list)
    for idx in idx_test.tolist():
        sid = sample_ids[int(idx)]
        row = rows_by_id[sid]
        if not str(row["pair_kind"]).startswith("same_register_drive_cycle_"):
            continue
        by_drive[int(y_drive[idx])].append(int(idx))
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    for drive in range(len(_DRIVE_LABELS)):
        candidates = list(by_drive[drive])
        rng.shuffle(candidates)
        if len(candidates) < per_drive:
            raise ValueError(
                f"not enough drive-contrast test rows for Drive {drive + 1}: "
                f"need {per_drive}, got {len(candidates)}"
            )
        selected.extend(candidates[:per_drive])
    return selected


def _sample_random_projections(drive_basis: Any, hidden_dim: int, rank: int, n_random: int) -> tuple[list[Any], float]:
    import numpy as np

    rng = np.random.default_rng(_SEED)
    p_drive = drive_basis.T @ drive_basis
    p_complement = np.eye(hidden_dim) - p_drive
    projections: list[Any] = []
    max_abs_cosine = 0.0
    for _ in range(n_random):
        raw = rng.standard_normal((rank, hidden_dim))
        projected = raw @ p_complement
        q, _ = np.linalg.qr(projected.T)
        basis = q[:, :rank].T
        max_abs_cosine = max(max_abs_cosine, float(np.max(abs(basis @ drive_basis.T))))
        projections.append(basis.T @ basis)
    return projections, max_abs_cosine


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
            p.clamp_min(eps) * (torch.log(p.clamp_min(eps)) - torch.log(q.clamp_min(eps)))
        ).item()
    )


def _summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {"cases": 0}
    n = len(cases)
    return {
        "cases": n,
        "first_step_top1_match_rate": sum(1 for c in cases if c["first_step_top1_match"]) / n,
        "exact_continuation_match_rate": sum(1 for c in cases if c["exact_token_sequence_match"]) / n,
        "mean_token_match_rate": sum(float(c["token_match_rate"]) for c in cases) / n,
        "mean_first_step_kl": sum(float(c["first_step_kl_baseline_to_ablated"]) for c in cases) / n,
        "baseline_first_token_distribution": dict(Counter(repr(c["baseline_first_top1_str"]) for c in cases)),
        "ablated_first_token_distribution": dict(Counter(repr(c["ablated_first_top1_str"]) for c in cases)),
    }


def _sign_p_ge(n_positive: int, n_total: int) -> float:
    if n_total <= 0:
        return 1.0
    return float(min(1.0, sum(math.comb(n_total, i) for i in range(n_positive, n_total + 1)) / (2.0**n_total)))


def _case_level_comparison(drive_cases: list[dict[str, Any]], random_cases_by_index: list[list[dict[str, Any]]]) -> dict[str, Any]:
    extras: list[float] = []
    positives = 0
    for case_i, drive_case in enumerate(drive_cases):
        random_matches = [float(cases[case_i]["token_match_rate"]) for cases in random_cases_by_index]
        random_mean = sum(random_matches) / max(1, len(random_matches))
        extra = random_mean - float(drive_case["token_match_rate"])
        extras.append(extra)
        if extra > 0:
            positives += 1
    n = len(extras)
    return {
        "cases": n,
        "mean_extra_divergence": sum(extras) / max(1, n),
        "positive_extra_count": positives,
        "negative_or_zero_extra_count": n - positives,
        "one_sided_sign_p_positive_extra": _sign_p_ge(positives, n),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--stage72-report", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--per-drive", type=int, default=4)
    parser.add_argument("--n-random", type=int, default=30)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    parser.add_argument("--selection-seed", type=int, default=20260517)
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    stage72_report_path = _resolve(args.stage72_report)
    out_report = _resolve(args.out_report)

    try:
        import numpy as np
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise SystemExit(f"missing dependency: {exc}") from exc

    with stage72_report_path.open(encoding="utf-8") as fh:
        stage72 = json.load(fh)
    drive_status = stage72.get("tasks", {}).get("drive", {}).get("status")
    if drive_status != "FACTOR_READOUT_AND_ABLATION_PASS":
        raise SystemExit(f"Stage 7.2 Drive factor is not pass-clean: {drive_status}")

    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    y_drive = _drive_labels(rows_by_id, sample_ids)
    splits = _split_indices(rows_by_id, sample_ids)
    idx_train = splits["train"]
    idx_test = splits["test"]

    X = data[_READOUT_KEY][:, _LAYER, :]
    projection_info = _fit_drive_projection(X, y_drive, idx_train)
    drive_projection = projection_info["projection"]
    random_projections, random_cosine = _sample_random_projections(
        projection_info["basis_rows"],
        hidden_dim=int(X.shape[1]),
        rank=int(projection_info["rank"]),
        n_random=int(args.n_random),
    )
    selected_indices = _select_drive_contrast_subset(
        rows_by_id,
        sample_ids,
        y_drive,
        idx_test,
        per_drive=int(args.per_drive),
        seed=int(args.selection_seed),
    )
    selected_ids = [sample_ids[i] for i in selected_indices]

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=True, use_fast=True)
    if not getattr(tokenizer, "is_fast", False):
        raise SystemExit("localized hook requires fast tokenizer offsets")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=True)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    block = model.gpt_neox.layers[_HOOK_BLOCK_INDEX]

    p_drive_t = torch.tensor(drive_projection, dtype=torch.float32, device=device)
    p_random_t = [torch.tensor(p, dtype=torch.float32, device=device) for p in random_projections]

    def make_local_hook(projection: Any, focus_token_index: int) -> Any:
        def hook(_module: Any, _input: Any, output: Any) -> Any:
            if isinstance(output, tuple):
                hs = output[0]
                if focus_token_index >= hs.shape[1]:
                    return output
                hs_ablated = hs.clone()
                token = hs[:, focus_token_index : focus_token_index + 1, :]
                hs_ablated[:, focus_token_index : focus_token_index + 1, :] = token - token @ projection.to(hs.dtype)
                return (hs_ablated,) + output[1:]
            if focus_token_index >= output.shape[1]:
                return output
            out_ablated = output.clone()
            token = output[:, focus_token_index : focus_token_index + 1, :]
            out_ablated[:, focus_token_index : focus_token_index + 1, :] = token - token @ projection.to(output.dtype)
            return out_ablated

        return hook

    def focus_token_index_for_prompt(prompt: str, base_text: str, expected_focus: str) -> int:
        focus_char = _find_focus_char_index(base_text, expected_focus)
        encoded = tokenizer(prompt, return_offsets_mapping=True, truncation=True, max_length=256)
        offsets = [(int(a), int(b)) for a, b in encoded["offset_mapping"]]
        return _find_token_for_char(offsets, focus_char)

    def greedy_continuation(prompt: str, projection: Any | None, focus_token_index: int | None) -> dict[str, Any]:
        encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256).to(device)
        generated = encoded["input_ids"].clone()
        new_tokens: list[int] = []
        first_logits = None
        handle = None
        if projection is not None:
            if focus_token_index is None:
                raise ValueError("focus_token_index required for localized hook")
            handle = block.register_forward_hook(make_local_hook(projection, focus_token_index))
        try:
            with torch.no_grad():
                for step in range(int(args.max_new_tokens)):
                    attention_mask = torch.ones_like(generated, device=device)
                    out = model(input_ids=generated, attention_mask=attention_mask, use_cache=False)
                    logits = out.logits[0, -1, :]
                    if step == 0:
                        first_logits = logits.detach().cpu()
                    next_id = int(torch.argmax(logits).item())
                    new_tokens.append(next_id)
                    generated = torch.cat(
                        [generated, torch.tensor([[next_id]], dtype=generated.dtype, device=device)],
                        dim=1,
                    )
                    if tokenizer.eos_token_id is not None and next_id == tokenizer.eos_token_id:
                        break
        finally:
            if handle is not None:
                handle.remove()
        if first_logits is None:
            raise RuntimeError("no logits produced")
        return {
            "new_token_ids": new_tokens,
            "text": tokenizer.decode(new_tokens, skip_special_tokens=True),
            "first_logits": first_logits,
            "first_top1_id": new_tokens[0] if new_tokens else None,
            "first_top1_str": tokenizer.decode([new_tokens[0]]) if new_tokens else "",
        }

    reproducibility_cases: list[dict[str, Any]] = []
    drive_cases: list[dict[str, Any]] = []
    random_cases_by_index: list[list[dict[str, Any]]] = [[] for _ in range(int(args.n_random))]
    started = time.perf_counter()

    for row_i, sample_idx in enumerate(selected_indices):
        sid = sample_ids[sample_idx]
        row = rows_by_id[sid]
        base_text = str(row["english"]).rstrip()
        expected_focus = str(row["focus_span"])
        true_drive = int(y_drive[sample_idx])

        for template_name, suffix in _PROMPT_TEMPLATES:
            prompt = base_text + suffix
            focus_token_index = focus_token_index_for_prompt(prompt, base_text, expected_focus)
            baseline_a = greedy_continuation(prompt, None, None)
            baseline_b = greedy_continuation(prompt, None, None)
            reproducibility_cases.append(
                {
                    "sample_id": sid,
                    "template": template_name,
                    "exact_match": baseline_a["new_token_ids"] == baseline_b["new_token_ids"],
                    "token_match_rate": _token_match_rate(baseline_a["new_token_ids"], baseline_b["new_token_ids"]),
                    "first_step_top1_match": baseline_a["first_top1_id"] == baseline_b["first_top1_id"],
                }
            )

            drive = greedy_continuation(prompt, p_drive_t, focus_token_index)

            def build_case(kind: str, ablated: dict[str, Any], random_index: int | None = None) -> dict[str, Any]:
                base_ids = baseline_a["new_token_ids"]
                ablated_ids = ablated["new_token_ids"]
                return {
                    "sample_id": sid,
                    "true_drive": true_drive,
                    "true_drive_label": _DRIVE_LABELS[true_drive],
                    "foundation_label": str(row["foundation_label"]),
                    "focus_span": expected_focus,
                    "focus_token_index": int(focus_token_index),
                    "pair_kind": str(row["pair_kind"]),
                    "contrast_partner_foundation": str(row["contrast_partner_foundation"]),
                    "template": template_name,
                    "intervention": kind,
                    "random_index": random_index,
                    "baseline_text": baseline_a["text"],
                    "ablated_text": ablated["text"],
                    "baseline_token_ids": base_ids,
                    "ablated_token_ids": ablated_ids,
                    "exact_token_sequence_match": base_ids == ablated_ids,
                    "token_match_rate": _token_match_rate(base_ids, ablated_ids),
                    "first_divergence_token_index": _first_divergence(base_ids, ablated_ids),
                    "first_step_top1_match": baseline_a["first_top1_id"] == ablated["first_top1_id"],
                    "first_step_kl_baseline_to_ablated": _softmax_kl(
                        torch,
                        baseline_a["first_logits"],
                        ablated["first_logits"],
                    ),
                    "baseline_first_top1_id": baseline_a["first_top1_id"],
                    "baseline_first_top1_str": baseline_a["first_top1_str"],
                    "ablated_first_top1_id": ablated["first_top1_id"],
                    "ablated_first_top1_str": ablated["first_top1_str"],
                }

            drive_cases.append(build_case("localized_drive_subspace", drive))
            for rand_i, rand_projection in enumerate(p_random_t):
                random = greedy_continuation(prompt, rand_projection, focus_token_index)
                random_cases_by_index[rand_i].append(
                    build_case("localized_random_complement", random, random_index=rand_i)
                )

        done = row_i + 1
        if done % 5 == 0 or done == len(selected_indices):
            elapsed = time.perf_counter() - started
            print(f"[{done}/{len(selected_indices)} rows] elapsed={elapsed:.1f}s")

    drive_summary = _summarize_cases(drive_cases)
    random_summaries = [_summarize_cases(cases) for cases in random_cases_by_index]
    random_mean_token_match = (
        sum(summary["mean_token_match_rate"] for summary in random_summaries) / max(1, len(random_summaries))
    )
    random_mean_kl = sum(summary["mean_first_step_kl"] for summary in random_summaries) / max(1, len(random_summaries))
    random_token_match_rates = [summary["mean_token_match_rate"] for summary in random_summaries]
    drive_extra_divergence = float(random_mean_token_match - drive_summary["mean_token_match_rate"])
    drive_extra_kl = float(drive_summary["mean_first_step_kl"] - random_mean_kl)
    empirical_p_random_le_drive = float(
        (1 + sum(1 for rate in random_token_match_rates if rate <= drive_summary["mean_token_match_rate"]))
        / (len(random_token_match_rates) + 1)
    )
    paired_case = _case_level_comparison(drive_cases, random_cases_by_index)
    repro_exact_rate = sum(1 for c in reproducibility_cases if c["exact_match"]) / max(1, len(reproducibility_cases))

    if repro_exact_rate < 1.0:
        status = "DRIVE_GENERATION_BASELINE_NOT_REPRODUCIBLE"
    elif (
        drive_extra_divergence >= _GATES["min_extra_divergence_vs_random_mean"]
        and empirical_p_random_le_drive < _GATES["empirical_p_random_le_drive_max"]
        and paired_case["one_sided_sign_p_positive_extra"] < _GATES["paired_case_sign_p_max"]
    ):
        status = "DRIVE_LOCALIZED_GENERATION_EFFECT_ABOVE_RANDOM_CONTROL"
    elif drive_extra_divergence > 0.0:
        status = "DRIVE_LOCALIZED_GENERATION_EFFECT_NUMERICALLY_ABOVE_RANDOM_CONTROL"
    else:
        status = "DRIVE_LOCALIZED_GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL"

    report = {
        "schema_version": "stage7_drive_generation_localized_hook_report.v1",
        "experiment": "Stage 7.3 Drive-only focus-token-localized generation hook",
        "status": status,
        "decision_gates": _GATES,
        "model_name": _MODEL_NAME,
        "device": str(device),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "stage72_report_file": stage72_report_path.name,
        "stage72_report_sha256": _sha256_of_file(stage72_report_path),
        "readout": _READOUT_NAME,
        "layer": _LAYER,
        "hook_block_index": _HOOK_BLOCK_INDEX,
        "hook_scope": "focus_token_only",
        "factor": "drive",
        "drive_subspace_rank": int(projection_info["rank"]),
        "drive_subspace_singular_values": projection_info["singular_values"],
        "svd_threshold": projection_info["threshold"],
        "per_drive": int(args.per_drive),
        "selection_seed": int(args.selection_seed),
        "selection_filter": "test split rows with pair_kind starting same_register_drive_cycle_",
        "n_selected_rows": len(selected_indices),
        "selected_sample_ids": selected_ids,
        "selected_drive_distribution": dict(Counter(_DRIVE_LABELS[int(y_drive[i])] for i in selected_indices)),
        "prompt_templates": [{"name": name, "suffix": suffix} for name, suffix in _PROMPT_TEMPLATES],
        "max_new_tokens": int(args.max_new_tokens),
        "n_random_controls": int(args.n_random),
        "max_abs_random_x_drive_cosine": random_cosine,
        "no_hook_reproducibility": {
            "cases": len(reproducibility_cases),
            "exact_match_rate": repro_exact_rate,
            "first_step_top1_match_rate": sum(1 for c in reproducibility_cases if c["first_step_top1_match"])
            / max(1, len(reproducibility_cases)),
            "mean_token_match_rate": sum(float(c["token_match_rate"]) for c in reproducibility_cases)
            / max(1, len(reproducibility_cases)),
        },
        "drive_summary": drive_summary,
        "random_summaries": random_summaries,
        "comparison": {
            "random_mean_token_match_rate": random_mean_token_match,
            "random_mean_first_step_kl": random_mean_kl,
            "drive_extra_divergence_vs_random_mean": drive_extra_divergence,
            "drive_extra_kl_vs_random_mean": drive_extra_kl,
            "empirical_p_random_token_match_le_drive": empirical_p_random_le_drive,
            "paired_case_extra_divergence": paired_case,
        },
        "reserved_interpretation": (
            "This test removes the Stage 7 Drive subspace only at the original Focus: A/B "
            "token position during greedy generation. A pass would show generated-language "
            "effect above random controls, not semantic steering toward a chosen Drive."
        ),
        "elapsed_seconds": time.perf_counter() - started,
        "reproducibility_cases": reproducibility_cases,
        "drive_cases": drive_cases,
        "random_cases_by_index": random_cases_by_index,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "repro_exact_rate": repro_exact_rate,
                "drive_mean_token_match": drive_summary["mean_token_match_rate"],
                "random_mean_token_match": random_mean_token_match,
                "drive_extra_divergence": drive_extra_divergence,
                "drive_mean_kl": drive_summary["mean_first_step_kl"],
                "random_mean_kl": random_mean_kl,
                "empirical_p": empirical_p_random_le_drive,
                "paired_case_sign_p": paired_case["one_sided_sign_p_positive_extra"],
                "rows": len(selected_indices),
                "cases": drive_summary["cases"],
                "rank": int(projection_info["rank"]),
            },
            indent=2,
        )
    )
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
