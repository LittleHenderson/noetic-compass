"""Stage 6.6: live generation hook for the role-bound noetic subspace.

This is the first language-behaviour follow-up to Stage 6.5.

Stage 6.5 proved that removing the focus-token layer-5 noetic subspace
collapses the CAS readout. Stage 6.6 asks a narrower language question:

    If we remove that same subspace inside Pythia during greedy generation,
    do continuations change more than same-rank random orthogonal removals?

This script is intentionally a locked-subset test by default. Full 1,400-row
generation is expensive on CPU and should only follow after this design is
audited.

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/ablate_stage6_role_bound_generation.py \
      --input stage6_role_bound_full_20260516.jsonl \
      --activations stage6_role_bound_full_activations_20260516.npz \
      --stage64-report stage6_role_bound_full_probe_report_20260516.json \
      --out-report stage6_role_bound_generation_hook_report_20260516.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 4242
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


def _split_indices(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> dict[str, Any]:
    import numpy as np

    split_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, sid in enumerate(sample_ids):
        split_to_indices[str(rows_by_id[sid]["split"])].append(i)
    return {split: np.array(indices, dtype=np.int64) for split, indices in split_to_indices.items()}


def _fit_probe_and_projection(X: Any, y: Any, idx_train: Any) -> dict[str, Any]:
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
    clf.fit(X_train, y[idx_train])

    sigma = scaler.scale_
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = clf.coef_ / sigma_safe[None, :]
    _u, s, vh = np.linalg.svd(w_raw, full_matrices=False)
    threshold = float(s.max() * 1e-6)
    basis_rows = vh[s > threshold]
    p = basis_rows.T @ basis_rows
    return {
        "scaler": scaler,
        "clf": clf,
        "basis_rows": basis_rows,
        "projection": p,
        "rank": int(basis_rows.shape[0]),
        "singular_values": [float(x) for x in s.tolist()],
        "threshold": threshold,
    }


def _select_subset(sample_ids: list[str], y: Any, idx_test: Any, per_label: int) -> list[int]:
    by_label: dict[int, list[int]] = defaultdict(list)
    for idx in idx_test.tolist():
        by_label[int(y[idx])].append(int(idx))
    selected: list[int] = []
    for label in sorted(by_label):
        selected.extend(by_label[label][:per_label])
    return selected


def _sample_random_projections(noetic_basis: Any, hidden_dim: int, rank: int, n_random: int) -> tuple[list[Any], float]:
    import numpy as np

    rng = np.random.default_rng(_SEED)
    p_noetic = noetic_basis.T @ noetic_basis
    p_complement = np.eye(hidden_dim) - p_noetic
    projections: list[Any] = []
    max_abs_cosine = 0.0
    for _ in range(n_random):
        raw = rng.standard_normal((rank, hidden_dim))
        projected = raw @ p_complement
        q, _ = np.linalg.qr(projected.T)
        basis = q[:, :rank].T
        max_abs_cosine = max(max_abs_cosine, float(np.max(np.abs(basis @ noetic_basis.T))))
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
    return float(torch.sum(p.clamp_min(eps) * (torch.log(p.clamp_min(eps)) - torch.log(q.clamp_min(eps)))).item())


def _summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {
            "cases": 0,
            "first_step_top1_match_rate": 0.0,
            "exact_continuation_match_rate": 0.0,
            "mean_token_match_rate": 0.0,
            "mean_first_step_kl": 0.0,
        }
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--stage64-report", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--per-label", type=int, default=2)
    parser.add_argument("--n-random", type=int, default=3)
    parser.add_argument("--max-new-tokens", type=int, default=8)
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
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    y = data["y"]
    splits = _split_indices(rows_by_id, sample_ids)
    idx_train = splits["train"]
    idx_test = splits["test"]

    with stage64_report_path.open(encoding="utf-8") as fh:
        stage64 = json.load(fh)
    headline = stage64["headline"]
    if headline["readout"] != _READOUT_NAME or int(headline["layer"]) != _LAYER:
        raise SystemExit(
            f"Stage 6.6 is locked to {_READOUT_NAME} layer {_LAYER}; "
            f"Stage 6.4 report has {headline['readout']} layer {headline['layer']}"
        )

    X = data[_READOUT_KEY][:, _LAYER, :]
    projection_info = _fit_probe_and_projection(X, y, idx_train)
    p_noetic = projection_info["projection"]
    random_projections, random_cosine = _sample_random_projections(
        projection_info["basis_rows"],
        hidden_dim=int(X.shape[1]),
        rank=int(projection_info["rank"]),
        n_random=int(args.n_random),
    )

    selected_indices = _select_subset(sample_ids, y, idx_test, per_label=int(args.per_label))
    selected_ids = [sample_ids[i] for i in selected_indices]

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=True)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    block = model.gpt_neox.layers[_HOOK_BLOCK_INDEX]

    p_noetic_t = torch.tensor(p_noetic, dtype=torch.float32, device=device)
    p_random_t = [torch.tensor(p, dtype=torch.float32, device=device) for p in random_projections]

    def make_hook(projection: Any) -> Any:
        def hook(_module: Any, _input: Any, output: Any) -> Any:
            if isinstance(output, tuple):
                hs = output[0]
                hs_ablated = hs - hs @ projection.to(hs.dtype)
                return (hs_ablated,) + output[1:]
            return output - output @ projection.to(output.dtype)

        return hook

    def greedy_continuation(prompt: str, projection: Any | None) -> dict[str, Any]:
        encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256).to(device)
        generated = encoded["input_ids"].clone()
        new_tokens: list[int] = []
        first_logits = None
        handle = block.register_forward_hook(make_hook(projection)) if projection is not None else None
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

    baseline_cache: dict[tuple[str, str], dict[str, Any]] = {}
    noetic_cases: list[dict[str, Any]] = []
    random_cases_by_index: list[list[dict[str, Any]]] = [[] for _ in range(int(args.n_random))]
    started = time.perf_counter()

    for row_i, sample_idx in enumerate(selected_indices):
        sid = sample_ids[sample_idx]
        row = rows_by_id[sid]
        text = str(row["english"]).rstrip()
        true_y = int(y[sample_idx])

        for template_name, suffix in _PROMPT_TEMPLATES:
            prompt = text + suffix
            key = (sid, template_name)
            baseline = greedy_continuation(prompt, None)
            baseline_cache[key] = baseline
            noetic = greedy_continuation(prompt, p_noetic_t)

            def build_case(kind: str, ablated: dict[str, Any], random_index: int | None = None) -> dict[str, Any]:
                base_ids = baseline["new_token_ids"]
                ablated_ids = ablated["new_token_ids"]
                return {
                    "sample_id": sid,
                    "true_y": true_y,
                    "focus_span": row["focus_span"],
                    "pair": "_".join(str(int(x)) for x in sorted(row["hard_contrast_labels"])),
                    "template": template_name,
                    "intervention": kind,
                    "random_index": random_index,
                    "baseline_text": baseline["text"],
                    "ablated_text": ablated["text"],
                    "baseline_token_ids": base_ids,
                    "ablated_token_ids": ablated_ids,
                    "exact_token_sequence_match": base_ids == ablated_ids,
                    "token_match_rate": _token_match_rate(base_ids, ablated_ids),
                    "first_divergence_token_index": _first_divergence(base_ids, ablated_ids),
                    "first_step_top1_match": baseline["first_top1_id"] == ablated["first_top1_id"],
                    "first_step_kl_baseline_to_ablated": _softmax_kl(torch, baseline["first_logits"], ablated["first_logits"]),
                    "baseline_first_top1_id": baseline["first_top1_id"],
                    "baseline_first_top1_str": baseline["first_top1_str"],
                    "ablated_first_top1_id": ablated["first_top1_id"],
                    "ablated_first_top1_str": ablated["first_top1_str"],
                }

            noetic_cases.append(build_case("noetic_subspace", noetic))
            for rand_i, rand_projection in enumerate(p_random_t):
                random = greedy_continuation(prompt, rand_projection)
                random_cases_by_index[rand_i].append(build_case("random_complement", random, random_index=rand_i))

        done = row_i + 1
        if done % 5 == 0 or done == len(selected_indices):
            elapsed = time.perf_counter() - started
            print(f"[{done}/{len(selected_indices)} rows] elapsed={elapsed:.1f}s")

    noetic_summary = _summarize_cases(noetic_cases)
    random_summaries = [_summarize_cases(cases) for cases in random_cases_by_index]
    random_mean_token_match = (
        sum(summary["mean_token_match_rate"] for summary in random_summaries) / max(1, len(random_summaries))
    )
    random_mean_kl = sum(summary["mean_first_step_kl"] for summary in random_summaries) / max(1, len(random_summaries))
    noetic_extra_divergence = float(random_mean_token_match - noetic_summary["mean_token_match_rate"])
    noetic_extra_kl = float(noetic_summary["mean_first_step_kl"] - random_mean_kl)
    random_token_match_rates = [summary["mean_token_match_rate"] for summary in random_summaries]
    empirical_p_random_le_noetic = float(
        (1 + sum(1 for rate in random_token_match_rates if rate <= noetic_summary["mean_token_match_rate"]))
        / (len(random_token_match_rates) + 1)
    )

    if noetic_extra_divergence >= 0.10 and empirical_p_random_le_noetic < 0.05:
        status = "GENERATION_EFFECT_ABOVE_RANDOM_CONTROL"
    elif noetic_extra_divergence > 0.0:
        status = "GENERATION_EFFECT_NUMERICALLY_ABOVE_RANDOM_CONTROL"
    else:
        status = "GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL"

    report = {
        "schema_version": "stage6_role_bound_generation_hook_report.v1",
        "experiment": "Stage 6.6 role-bound live generation hook subset",
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
        "subspace_rank": int(projection_info["rank"]),
        "per_label": int(args.per_label),
        "n_selected_rows": len(selected_indices),
        "selected_sample_ids": selected_ids,
        "prompt_templates": [{"name": name, "suffix": suffix} for name, suffix in _PROMPT_TEMPLATES],
        "max_new_tokens": int(args.max_new_tokens),
        "n_random_controls": int(args.n_random),
        "max_abs_random_x_noetic_cosine": random_cosine,
        "noetic_summary": noetic_summary,
        "random_summaries": random_summaries,
        "comparison": {
            "random_mean_token_match_rate": random_mean_token_match,
            "random_mean_first_step_kl": random_mean_kl,
            "noetic_extra_divergence_vs_random_mean": noetic_extra_divergence,
            "noetic_extra_kl_vs_random_mean": noetic_extra_kl,
            "empirical_p_random_token_match_le_noetic": empirical_p_random_le_noetic,
        },
        "reserved_interpretation": (
            "This subset test measures whether layer-5 noetic subspace removal changes greedy "
            "continuations more than same-rank random removals. It is not a full benchmark and "
            "does not assign CAS semantics to the changed text without a separate semantic audit."
        ),
        "elapsed_seconds": time.perf_counter() - started,
        "noetic_cases": noetic_cases,
        "random_cases_by_index": random_cases_by_index,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "noetic_mean_token_match": noetic_summary["mean_token_match_rate"],
                "random_mean_token_match": random_mean_token_match,
                "noetic_extra_divergence": noetic_extra_divergence,
                "noetic_mean_kl": noetic_summary["mean_first_step_kl"],
                "random_mean_kl": random_mean_kl,
                "empirical_p": empirical_p_random_le_noetic,
                "rows": len(selected_indices),
                "cases": noetic_summary["cases"],
            },
            indent=2,
        )
    )
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
