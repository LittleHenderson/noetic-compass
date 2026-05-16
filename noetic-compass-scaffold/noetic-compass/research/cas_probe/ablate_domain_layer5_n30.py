"""Stage 4.1: domain-axis ablation with n=30 random permutation control.

This is the causal follow-up to the Stage 4.0 cross-axis probe screen.
Domain was the only non-noetic axis with a promising discriminative
signal, so this script tests whether its layer-5 directions have a
behavioral effect beyond matched random directions.

Design mirrors Stage 3.3:

* Use the domain probe's headline layer (layer 5).
* Ablate each domain class direction (P, C, E, O) and measure forced
  continuation disruption.
* Sample 30 random unit directions in the domain-subspace complement.
* Build a matched null by sampling 4 random directions at a time,
  assigning them to the 4 domain labels, and comparing mean disruption
  against the real domain arm over 10,000 permutations.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TODAY = "20260516"

_ACTIVATIONS_PATH = _HERE / "pythia_probe_activations_20260515.npz"
_LABELS_PATH = _HERE / "pythia_probe_labels_20260515.jsonl"
_CROSS_PROBES_PATH = _HERE / "pythia_cross_axis_probes_20260516.npz"
_CROSS_REPORT_PATH = _HERE / "pythia_cross_axis_probes_report_20260516.json"
_OUT_REPORT = _HERE / f"pythia_ablation_domain_layer5_n30_{_TODAY}.json"

_MODEL_NAME = "EleutherAI/pythia-160m"
_AXIS = "domain"
_TARGET_LAYER_INDEX = 5
_HOOK_BLOCK_INDEX = _TARGET_LAYER_INDEX - 1
_MAX_NEW_TOKENS = 8
_CONTINUATION_PREFIXES: tuple[tuple[str, str], ...] = (
    ("in_other_words", "\nIn other words,"),
    ("this_concept_means", "\nThis concept means"),
    ("good_explanation", "\nA good explanation is"),
)
_RANDOM_SEED = 5252
_N_RANDOM_DIRECTIONS = 30
_N_PERMUTATIONS = 10_000
_ALPHA = 0.05


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _mean_disruption_from_matrix(match_matrix: Any, n_classes: int) -> tuple[Any, float]:
    import numpy as np

    per_class = []
    for c in range(n_classes):
        self_v = match_matrix[c, c]
        cross = np.delete(match_matrix[c], c)
        per_class.append(float(np.nanmean(cross) - self_v))
    arr = np.array(per_class, dtype=float)
    return arr, float(arr.mean())


def main() -> int:
    for path in (_ACTIVATIONS_PATH, _LABELS_PATH, _CROSS_PROBES_PATH, _CROSS_REPORT_PATH):
        if not path.is_file():
            raise SystemExit(f"missing prerequisite: {path}")

    try:
        import numpy as np
        import scipy
        import torch
        import transformers
        from scipy.stats import ttest_1samp
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        print(
            f"missing dependency: {exc}\n"
            f"  pip install scikit-learn numpy scipy torch transformers",
            file=sys.stderr,
        )
        return 2

    started = time.perf_counter()
    activations_sha = _sha256_of_file(_ACTIVATIONS_PATH)
    labels_sha = _sha256_of_file(_LABELS_PATH)
    cross_probes_sha = _sha256_of_file(_CROSS_PROBES_PATH)
    cross_report_sha = _sha256_of_file(_CROSS_REPORT_PATH)
    print(f"activations sha256:   {activations_sha}")
    print(f"labels sha256:        {labels_sha}")
    print(f"cross probes sha256:  {cross_probes_sha}")
    print(f"cross report sha256:  {cross_report_sha}")

    act = np.load(_ACTIVATIONS_PATH, allow_pickle=False)
    X = act["X"]
    sample_ids_all = [str(s) for s in act["sample_ids"]]
    probes = np.load(_CROSS_PROBES_PATH, allow_pickle=False)

    coefs = probes[f"{_AXIS}_coefs"]
    intercepts = probes[f"{_AXIS}_intercepts"]
    scaler_mean = probes[f"{_AXIS}_scaler_mean"]
    scaler_scale = probes[f"{_AXIS}_scaler_scale"]
    label_order = [str(x) for x in probes[f"{_AXIS}_label_order"]]
    row_indices = probes[f"{_AXIS}_row_indices"]
    y_axis = probes[f"{_AXIS}_y"]
    idx_test = probes[f"{_AXIS}_idx_test"]

    with _CROSS_REPORT_PATH.open(encoding="utf-8") as fh:
        cross_report = json.load(fh)
    headline_layer = int(cross_report["axes"][_AXIS]["headline_layer"]["layer"])
    if headline_layer != _TARGET_LAYER_INDEX:
        raise SystemExit(
            f"{_AXIS} headline layer is {headline_layer}, expected {_TARGET_LAYER_INDEX}"
        )

    labels_by_sample_id: dict[str, str] = {}
    with _LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                labels_by_sample_id[str(r["sample_id"])] = str(r["english"])

    layer = _TARGET_LAYER_INDEX
    w_std = coefs[layer]
    sigma = scaler_scale[layer]
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = w_std / sigma_safe[None, :]
    n_classes = int(w_raw.shape[0])
    hidden_dim = int(w_raw.shape[1])
    if n_classes != len(label_order):
        raise SystemExit("label_order and coefficient class count mismatch")
    if _N_RANDOM_DIRECTIONS < n_classes:
        raise SystemExit("_N_RANDOM_DIRECTIONS must be >= n_classes")

    norms = np.linalg.norm(w_raw, axis=1, keepdims=True)
    norms_safe = np.where(norms == 0, 1.0, norms)
    u_domain = w_raw / norms_safe
    cos_matrix = u_domain @ u_domain.T
    off_diag_mask = np.ones_like(cos_matrix, dtype=bool)
    np.fill_diagonal(off_diag_mask, False)
    off_diag_cos = cos_matrix[off_diag_mask]
    print(f"domain label order: {label_order}")
    print(f"domain direction norms: {[f'{n:.3f}' for n in norms.ravel()]}")
    print(
        "domain direction off-diagonal cosine: "
        f"mean={off_diag_cos.mean():.3f} max_abs={np.max(np.abs(off_diag_cos)):.3f}"
    )

    # Probe self-ablation sanity gate.
    h_raw_all = X[row_indices, layer, :]
    y_test = y_axis[idx_test]
    sanity_gate_per_class: list[dict[str, Any]] = []
    for c, label in enumerate(label_order):
        pc_np = np.outer(u_domain[c], u_domain[c])
        h_ablated = h_raw_all - h_raw_all @ pc_np
        h_ablated_std = (h_ablated - scaler_mean[layer]) / sigma_safe
        logits = h_ablated_std @ w_std.T + intercepts[layer][None, :]
        preds_ablated = np.argmax(logits, axis=1)
        ablated_preds_test = preds_ablated[idx_test]
        mask_c = y_test == c
        kept_rate = float(np.mean(ablated_preds_test[mask_c] == c)) if mask_c.sum() else float("nan")
        pred_c_rate = float(np.mean(ablated_preds_test == c))
        support_rate = float(np.mean(y_test == c))
        sanity_gate_per_class.append(
            {
                "class_index": c,
                "label": label,
                "true_class_kept_rate": kept_rate,
                "ablated_pred_class_rate": pred_c_rate,
                "test_support_rate": support_rate,
                "n_true_class_test": int(mask_c.sum()),
            }
        )
        print(
            f"sanity {label}: kept={kept_rate:.3f} "
            f"pred_rate={pred_c_rate:.3f} support={support_rate:.3f}"
        )

    _, s_svd, vh = np.linalg.svd(w_raw, full_matrices=False)
    keep = s_svd > s_svd.max() * 1e-6
    domain_basis = vh[keep]
    domain_rank = int(domain_basis.shape[0])
    p_domain = domain_basis.T @ domain_basis
    p_complement = np.eye(hidden_dim) - p_domain

    rng = np.random.default_rng(_RANDOM_SEED)
    raw_random = rng.standard_normal((_N_RANDOM_DIRECTIONS, hidden_dim))
    proj_random = raw_random @ p_complement
    q, _ = np.linalg.qr(proj_random.T)
    u_random = q[:, :_N_RANDOM_DIRECTIONS].T
    rand_norms = np.linalg.norm(u_random, axis=1)
    rand_x_domain = u_random @ domain_basis.T
    rand_x_rand = u_random @ u_random.T
    print(
        "random direction norms: "
        f"min={rand_norms.min():.4f} max={rand_norms.max():.4f}"
    )
    print(f"random x domain cosine: max_abs={np.max(np.abs(rand_x_domain)):.8f} (target 0)")
    print(
        "random x random off-diag: "
        f"max_abs={np.max(np.abs(rand_x_rand - np.eye(_N_RANDOM_DIRECTIONS))):.8f} (target 0)"
    )

    print()
    print(f"loading {_MODEL_NAME} ...")
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=True)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"device: {device}")

    block = model.gpt_neox.layers[_HOOK_BLOCK_INDEX]
    domain_proj = [
        torch.tensor(np.outer(u_domain[c], u_domain[c]), dtype=torch.float32, device=device)
        for c in range(n_classes)
    ]
    random_proj = [
        torch.tensor(np.outer(u_random[d], u_random[d]), dtype=torch.float32, device=device)
        for d in range(_N_RANDOM_DIRECTIONS)
    ]

    def make_hook(projections: list[Any], index: int) -> Any:
        pc = projections[index]

        def hook(_module, _input, output):
            if isinstance(output, tuple):
                hs = output[0]
                hs_ablated = hs - hs @ pc.to(hs.dtype)
                return (hs_ablated,) + output[1:]
            return output - output @ pc.to(output.dtype)

        return hook

    def greedy_generate(prompt_text: str, n_new: int, hook_fn: Any | None) -> list[int]:
        encoded = tokenizer(prompt_text, return_tensors="pt", truncation=True, max_length=256).to(device)
        input_ids = encoded["input_ids"]
        attention_mask = encoded.get("attention_mask")
        handle = None
        if hook_fn is not None:
            handle = block.register_forward_hook(hook_fn)
        generated: list[int] = []
        try:
            with torch.no_grad():
                cur_ids = input_ids
                cur_mask = attention_mask
                for _ in range(n_new):
                    out = model(input_ids=cur_ids, attention_mask=cur_mask)
                    next_logits = out.logits[0, -1, :]
                    next_tok = int(torch.argmax(next_logits).item())
                    generated.append(next_tok)
                    cur_ids = torch.cat([cur_ids, torch.tensor([[next_tok]], device=device)], dim=1)
                    if cur_mask is not None:
                        cur_mask = torch.cat([cur_mask, torch.tensor([[1]], device=device)], dim=1)
        finally:
            if handle is not None:
                handle.remove()
        return generated

    test_domain_indices = idx_test.tolist()
    test_rows = [
        {
            "domain_index": int(i),
            "activation_row": int(row_indices[i]),
            "sample_id": sample_ids_all[int(row_indices[i])],
            "true_y": int(y_axis[i]),
            "label": label_order[int(y_axis[i])],
        }
        for i in test_domain_indices
    ]

    print()
    print(
        f"generating baselines + {n_classes} domain ablations + "
        f"{_N_RANDOM_DIRECTIONS} random ablations ..."
    )
    gen_started = time.perf_counter()

    baseline_cache: dict[tuple[str, str], list[int]] = {}
    for row in test_rows:
        text = labels_by_sample_id[row["sample_id"]]
        for prefix_name, suffix in _CONTINUATION_PREFIXES:
            baseline_cache[(row["sample_id"], prefix_name)] = greedy_generate(
                text + suffix,
                _MAX_NEW_TOKENS,
                None,
            )
    print(f"  baselines done in {time.perf_counter() - gen_started:.1f}s")

    domain_cells: list[list[list[float]]] = [[[] for _ in range(n_classes)] for _ in range(n_classes)]
    random_cells: list[list[list[float]]] = [
        [[] for _ in range(n_classes)] for _ in range(_N_RANDOM_DIRECTIONS)
    ]
    per_case_domain: list[dict[str, Any]] = []
    per_case_random: list[dict[str, Any]] = []

    def token_match_rate(baseline_tokens: list[int], ablated_tokens: list[int]) -> float:
        pos_matches = sum(1 for a, b in zip(baseline_tokens, ablated_tokens) if a == b)
        tlen = max(1, min(len(baseline_tokens), len(ablated_tokens)))
        return pos_matches / tlen

    for c, label in enumerate(label_order):
        hook = make_hook(domain_proj, c)
        for row in test_rows:
            text = labels_by_sample_id[row["sample_id"]]
            true_y = row["true_y"]
            for prefix_name, suffix in _CONTINUATION_PREFIXES:
                baseline_tokens = baseline_cache[(row["sample_id"], prefix_name)]
                ablated_tokens = greedy_generate(text + suffix, _MAX_NEW_TOKENS, hook)
                tmatch = token_match_rate(baseline_tokens, ablated_tokens)
                domain_cells[c][true_y].append(float(tmatch))
                per_case_domain.append(
                    {
                        "sample_id": row["sample_id"],
                        "true_y": true_y,
                        "true_label": row["label"],
                        "ablated_class_index": c,
                        "ablated_label": label,
                        "prefix": prefix_name,
                        "token_match_rate": float(tmatch),
                    }
                )
        print(f"  domain ablation {label} done at elapsed={time.perf_counter() - gen_started:.1f}s")

    for direction_index in range(_N_RANDOM_DIRECTIONS):
        hook = make_hook(random_proj, direction_index)
        for row in test_rows:
            text = labels_by_sample_id[row["sample_id"]]
            true_y = row["true_y"]
            for prefix_name, suffix in _CONTINUATION_PREFIXES:
                baseline_tokens = baseline_cache[(row["sample_id"], prefix_name)]
                ablated_tokens = greedy_generate(text + suffix, _MAX_NEW_TOKENS, hook)
                tmatch = token_match_rate(baseline_tokens, ablated_tokens)
                random_cells[direction_index][true_y].append(float(tmatch))
                per_case_random.append(
                    {
                        "sample_id": row["sample_id"],
                        "true_y": true_y,
                        "true_label": row["label"],
                        "random_dir_index": direction_index,
                        "prefix": prefix_name,
                        "token_match_rate": float(tmatch),
                    }
                )
        print(f"  random direction {direction_index} done at elapsed={time.perf_counter() - gen_started:.1f}s")

    domain_match = np.zeros((n_classes, n_classes), dtype=float)
    domain_n = np.zeros((n_classes, n_classes), dtype=int)
    for c in range(n_classes):
        for true_class in range(n_classes):
            rows = domain_cells[c][true_class]
            domain_match[c, true_class] = float(np.mean(rows)) if rows else float("nan")
            domain_n[c, true_class] = len(rows)

    random_match = np.zeros((_N_RANDOM_DIRECTIONS, n_classes), dtype=float)
    random_n = np.zeros((_N_RANDOM_DIRECTIONS, n_classes), dtype=int)
    for direction_index in range(_N_RANDOM_DIRECTIONS):
        for true_class in range(n_classes):
            rows = random_cells[direction_index][true_class]
            random_match[direction_index, true_class] = float(np.mean(rows)) if rows else float("nan")
            random_n[direction_index, true_class] = len(rows)

    domain_disruptions, observed_domain_mean = _mean_disruption_from_matrix(domain_match, n_classes)
    t_domain, p_domain = ttest_1samp(domain_disruptions, 0.0)

    random_assigned_disruptions = np.zeros((_N_RANDOM_DIRECTIONS, n_classes), dtype=float)
    for direction_index in range(_N_RANDOM_DIRECTIONS):
        for assigned_class in range(n_classes):
            self_v = random_match[direction_index, assigned_class]
            cross = np.delete(random_match[direction_index], assigned_class)
            random_assigned_disruptions[direction_index, assigned_class] = float(np.nanmean(cross) - self_v)

    perm_rng = np.random.default_rng(_RANDOM_SEED + 1)
    null_means = np.zeros(_N_PERMUTATIONS, dtype=float)
    for i in range(_N_PERMUTATIONS):
        sampled_dirs = perm_rng.choice(_N_RANDOM_DIRECTIONS, size=n_classes, replace=False)
        perm_rng.shuffle(sampled_dirs)
        values = [
            random_assigned_disruptions[int(direction_index), assigned_class]
            for assigned_class, direction_index in enumerate(sampled_dirs)
        ]
        null_means[i] = float(np.mean(values))

    permutation_p = float((1 + np.sum(null_means >= observed_domain_mean)) / (1 + _N_PERMUTATIONS))
    null_mean = float(null_means.mean())
    null_std = float(null_means.std(ddof=1))
    null_quantiles = {
        "p50": float(np.quantile(null_means, 0.50)),
        "p90": float(np.quantile(null_means, 0.90)),
        "p95": float(np.quantile(null_means, 0.95)),
        "p99": float(np.quantile(null_means, 0.99)),
    }
    effect_over_null = float(observed_domain_mean - null_mean)

    if permutation_p < _ALPHA and observed_domain_mean > null_quantiles["p95"]:
        verdict = "DOMAIN_EFFECT_DIRECTION_MEANINGFUL_N30_PERMUTATION"
    elif observed_domain_mean > null_mean and permutation_p < 0.10:
        verdict = "DOMAIN_EFFECT_SUGGESTIVE_N30_PERMUTATION"
    else:
        verdict = "DOMAIN_EFFECT_NOT_ABOVE_RANDOM_N30_PERMUTATION"

    verdict_text = (
        f"Domain mean disruption is {observed_domain_mean:+.3f}. "
        f"The n=30 random-direction permutation null has mean {null_mean:+.3f}, "
        f"std {null_std:.3f}, p95 {null_quantiles['p95']:+.3f}. "
        f"One-sided permutation p={permutation_p:.4f} over {_N_PERMUTATIONS} "
        f"matched {n_classes}-direction samples. Verdict: {verdict}."
    )

    print()
    print("STAGE 4.1 DOMAIN N=30 PERMUTATION CONTROL")
    print(f"  domain mean disruption: {observed_domain_mean:+.4f}")
    print(f"  domain one-sample t: t={float(t_domain):.3f} p={float(p_domain):.4f}")
    print(f"  random null mean: {null_mean:+.4f} std={null_std:.4f}")
    print(f"  random null quantiles: {null_quantiles}")
    print(f"  effect over null mean: {effect_over_null:+.4f}")
    print(f"  permutation p(one-sided): {permutation_p:.4f}")
    print(f"VERDICT: {verdict}")
    print(verdict_text)

    report = {
        "schema_version": "pythia_ablation_domain_layer5_n30.v1",
        "experiment": "Stage 4.1 domain-axis n=30 permutation ablation",
        "model_name": _MODEL_NAME,
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "axis": _AXIS,
        "label_order": label_order,
        "target_layer_index": _TARGET_LAYER_INDEX,
        "hook_block_index": _HOOK_BLOCK_INDEX,
        "max_new_tokens": _MAX_NEW_TOKENS,
        "continuation_prefixes": [{"name": p[0], "suffix": p[1]} for p in _CONTINUATION_PREFIXES],
        "device": str(device),
        "local_files_only": True,
        "random_seed": _RANDOM_SEED,
        "n_random_directions": _N_RANDOM_DIRECTIONS,
        "n_axis_directions": n_classes,
        "n_permutations": _N_PERMUTATIONS,
        "n_test_records": int(len(test_rows)),
        "package_versions": {
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "activations_file": _ACTIVATIONS_PATH.name,
        "activations_sha256": activations_sha,
        "labels_file": _LABELS_PATH.name,
        "labels_sha256": labels_sha,
        "cross_probes_file": _CROSS_PROBES_PATH.name,
        "cross_probes_sha256": cross_probes_sha,
        "cross_report_file": _CROSS_REPORT_PATH.name,
        "cross_report_sha256": cross_report_sha,
        "domain_subspace_rank": domain_rank,
        "domain_direction_norms": [float(n) for n in norms.ravel()],
        "domain_direction_off_diag_cosine_stats": {
            "mean": float(off_diag_cos.mean()),
            "max_abs": float(np.max(np.abs(off_diag_cos))),
        },
        "probe_self_ablation_sanity_gate": sanity_gate_per_class,
        "random_direction_diagnostics": {
            "norms_min": float(rand_norms.min()),
            "norms_max": float(rand_norms.max()),
            "max_cosine_with_domain": float(np.max(np.abs(rand_x_domain))),
            "max_offdiag_cosine_with_other_random": float(
                np.max(np.abs(rand_x_rand - np.eye(_N_RANDOM_DIRECTIONS)))
            ),
        },
        "domain_matrix_mean_token_match_rate": domain_match.tolist(),
        "domain_matrix_n_cases": domain_n.tolist(),
        "domain_per_class_disruption_deltas": domain_disruptions.tolist(),
        "domain_one_sample_t_test": {
            "t": float(t_domain),
            "p_two_sided": float(p_domain),
            "df": int(n_classes - 1),
            "n": int(n_classes),
        },
        "random_matrix_mean_token_match_rate": random_match.tolist(),
        "random_matrix_n_cases": random_n.tolist(),
        "random_assigned_disruption_matrix": random_assigned_disruptions.tolist(),
        "permutation_test": {
            "observed_domain_mean": observed_domain_mean,
            "null_mean": null_mean,
            "null_std": null_std,
            "effect_over_null_mean": effect_over_null,
            "p_one_sided": permutation_p,
            "n_permutations": _N_PERMUTATIONS,
            "null_quantiles": null_quantiles,
            "plus_one_correction": True,
            "sample_size_per_permutation": n_classes,
            "sample_without_replacement": True,
            "random_assignment_to_classes": True,
        },
        "decision_thresholds": {
            "alpha": _ALPHA,
            "direction_meaningful_requires_permutation_p_below_alpha": True,
            "direction_meaningful_requires_observed_above_null_p95": True,
        },
        "test_rows": test_rows,
        "per_case_domain": per_case_domain,
        "per_case_random": per_case_random,
        "elapsed_sec": float(time.perf_counter() - started),
        "verdict": verdict,
        "verdict_text": verdict_text,
    }
    with _OUT_REPORT.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"report written: {_OUT_REPORT}")
    print(f"elapsed: {report['elapsed_sec']:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
