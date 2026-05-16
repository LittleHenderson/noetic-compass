"""Stage 3.3 control: 30 random directions + permutation test.

This is the higher-power follow-up to Stage 3.2-control.

Question:

    Is the noetic arm's +0.079 mean same-class continuation disruption
    larger than what matched random directions produce by chance?

Design:

* Build the same layer-3 noetic subspace from the trained noetic probe.
* Sample 30 random unit directions in the noetic subspace's orthogonal
  complement.
* Run the same forced-continuation ablation test for all 30 directions.
* Build a null distribution by sampling 10 random directions from the
  30-direction pool, randomly assigning them to the 10 noetic classes,
  and computing the same mean disruption statistic as the noetic arm.
* Repeat 10,000 times and report a one-sided permutation p-value.

This test avoids treating 30 random directions as if they were 30 CAS
classes. The unit of comparison remains a 10-direction set, matching the
real noetic arm.
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
_PROBES_PATH = _HERE / "pythia_noetic_probes_20260515.npz"
_PROBES_REPORT_PATH = _HERE / "pythia_noetic_probes_report_20260515.json"
_LABELS_PATH = _HERE / "pythia_probe_labels_20260515.jsonl"
_NOETIC_STAGE32_PATH = _HERE / "pythia_ablation_per_class_layer3_clean_20260516.json"
_OUT_REPORT = _HERE / f"pythia_ablation_random_control_layer3_n30_{_TODAY}.json"

_MODEL_NAME = "EleutherAI/pythia-160m"
_TARGET_LAYER_INDEX = 3
_HOOK_BLOCK_INDEX = _TARGET_LAYER_INDEX - 1
_MAX_NEW_TOKENS = 8
_CONTINUATION_PREFIXES: tuple[tuple[str, str], ...] = (
    ("in_other_words", "\nIn other words,"),
    ("this_concept_means", "\nThis concept means"),
    ("good_explanation", "\nA good explanation is"),
)
_RANDOM_SEED = 4242
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


def main() -> int:
    for p in (_ACTIVATIONS_PATH, _PROBES_PATH, _PROBES_REPORT_PATH, _LABELS_PATH, _NOETIC_STAGE32_PATH):
        if not p.is_file():
            raise SystemExit(f"missing prerequisite: {p}")

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

    activations_sha = _sha256_of_file(_ACTIVATIONS_PATH)
    probes_sha = _sha256_of_file(_PROBES_PATH)
    noetic_stage32_sha = _sha256_of_file(_NOETIC_STAGE32_PATH)
    print(f"activations sha256:       {activations_sha}")
    print(f"probes sha256:            {probes_sha}")
    print(f"stage3.2 noetic sha256:   {noetic_stage32_sha}")

    act = np.load(_ACTIVATIONS_PATH, allow_pickle=False)
    y = act["y"]
    sample_ids = act["sample_ids"]
    probes = np.load(_PROBES_PATH, allow_pickle=False)
    coefs = probes["coefs"]
    scaler_scale = probes["scaler_scale"]
    idx_test = probes["idx_test"]

    with _PROBES_REPORT_PATH.open(encoding="utf-8") as fh:
        report_in = json.load(fh)
    headline_layer = int(report_in["headline_layer"]["layer"])
    assert headline_layer == _TARGET_LAYER_INDEX

    labels: dict[str, str] = {}
    with _LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                labels[r["sample_id"]] = r["english"]

    with _NOETIC_STAGE32_PATH.open(encoding="utf-8") as fh:
        noetic_report = json.load(fh)
    noetic_match = np.array(noetic_report["matrix_mean_token_match_rate"], dtype=float)

    layer = _TARGET_LAYER_INDEX
    w_std = coefs[layer]
    sigma = scaler_scale[layer]
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = w_std / sigma_safe[None, :]
    n_classes = int(w_raw.shape[0])
    hidden_dim = int(w_raw.shape[1])
    if _N_RANDOM_DIRECTIONS < n_classes:
        raise SystemExit("_N_RANDOM_DIRECTIONS must be >= n_classes")

    _, s_svd, vh = np.linalg.svd(w_raw, full_matrices=False)
    keep = s_svd > s_svd.max() * 1e-6
    noetic_basis = vh[keep]
    noetic_rank = int(noetic_basis.shape[0])
    p_noetic = noetic_basis.T @ noetic_basis
    p_complement = np.eye(hidden_dim) - p_noetic

    rng = np.random.default_rng(_RANDOM_SEED)
    raw_random = rng.standard_normal((_N_RANDOM_DIRECTIONS, hidden_dim))
    proj_random = raw_random @ p_complement
    q, _ = np.linalg.qr(proj_random.T)
    u_random = q[:, :_N_RANDOM_DIRECTIONS].T

    rand_norms = np.linalg.norm(u_random, axis=1)
    rand_x_noetic = u_random @ noetic_basis.T
    rand_x_rand = u_random @ u_random.T
    print(
        "random direction norms: "
        f"min={rand_norms.min():.4f} max={rand_norms.max():.4f}"
    )
    print(f"random x noetic cosine: max_abs={np.max(np.abs(rand_x_noetic)):.8f} (target 0)")
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
    p_per_dir = [
        torch.tensor(np.outer(u_random[d], u_random[d]), dtype=torch.float32, device=device)
        for d in range(_N_RANDOM_DIRECTIONS)
    ]

    def make_dir_hook(direction_index: int) -> Any:
        pc = p_per_dir[direction_index]

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

    print()
    print(f"generating baselines + {_N_RANDOM_DIRECTIONS} random-direction ablations ...")
    started = time.perf_counter()

    test_ids = [str(sample_ids[i]) for i in idx_test.tolist()]
    test_y_list = [int(y[i]) for i in idx_test.tolist()]

    baseline_cache: dict[tuple[str, str], list[int]] = {}
    for sid in test_ids:
        text = labels[sid]
        for prefix_name, suffix in _CONTINUATION_PREFIXES:
            baseline_cache[(sid, prefix_name)] = greedy_generate(text + suffix, _MAX_NEW_TOKENS, None)
    print(f"  baselines done in {time.perf_counter() - started:.1f}s")

    cells_token_match: list[list[list[float]]] = [
        [[] for _ in range(n_classes)] for _ in range(_N_RANDOM_DIRECTIONS)
    ]
    per_case: list[dict[str, Any]] = []

    for direction_index in range(_N_RANDOM_DIRECTIONS):
        hook = make_dir_hook(direction_index)
        for ti, sid in enumerate(test_ids):
            true_y = int(test_y_list[ti])
            text = labels[sid]
            for prefix_name, suffix in _CONTINUATION_PREFIXES:
                prompt_text = text + suffix
                baseline_tokens = baseline_cache[(sid, prefix_name)]
                ablated_tokens = greedy_generate(prompt_text, _MAX_NEW_TOKENS, hook)
                pos_matches = sum(1 for a, b in zip(baseline_tokens, ablated_tokens) if a == b)
                tlen = max(1, min(len(baseline_tokens), len(ablated_tokens)))
                token_match = pos_matches / tlen
                cells_token_match[direction_index][true_y].append(float(token_match))
                per_case.append(
                    {
                        "sample_id": sid,
                        "true_y": true_y,
                        "random_dir_index": direction_index,
                        "prefix": prefix_name,
                        "token_match_rate": float(token_match),
                    }
                )
        print(
            f"  random direction {direction_index} done at "
            f"elapsed={time.perf_counter() - started:.1f}s"
        )

    random_match = np.zeros((_N_RANDOM_DIRECTIONS, n_classes), dtype=float)
    random_n = np.zeros((_N_RANDOM_DIRECTIONS, n_classes), dtype=int)
    for direction_index in range(_N_RANDOM_DIRECTIONS):
        for true_class in range(n_classes):
            rows = cells_token_match[direction_index][true_class]
            random_match[direction_index, true_class] = float(np.mean(rows)) if rows else float("nan")
            random_n[direction_index, true_class] = len(rows)

    random_assigned_disruptions = np.zeros((_N_RANDOM_DIRECTIONS, n_classes), dtype=float)
    for direction_index in range(_N_RANDOM_DIRECTIONS):
        for assigned_class in range(n_classes):
            self_v = random_match[direction_index, assigned_class]
            cross = np.delete(random_match[direction_index], assigned_class)
            random_assigned_disruptions[direction_index, assigned_class] = float(np.nanmean(cross) - self_v)

    noetic_disruptions = []
    for c in range(n_classes):
        self_v = noetic_match[c, c]
        cross = np.delete(noetic_match[c], c)
        noetic_disruptions.append(float(np.nanmean(cross) - self_v))
    noetic_disruption_arr = np.array(noetic_disruptions, dtype=float)
    observed_noetic_mean = float(noetic_disruption_arr.mean())
    t_noetic, p_noetic = ttest_1samp(noetic_disruption_arr, 0.0)

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

    permutation_p = float((1 + np.sum(null_means >= observed_noetic_mean)) / (1 + _N_PERMUTATIONS))
    null_mean = float(null_means.mean())
    null_std = float(null_means.std(ddof=1))
    null_quantiles = {
        "p50": float(np.quantile(null_means, 0.50)),
        "p90": float(np.quantile(null_means, 0.90)),
        "p95": float(np.quantile(null_means, 0.95)),
        "p99": float(np.quantile(null_means, 0.99)),
    }
    effect_over_null = float(observed_noetic_mean - null_mean)

    if permutation_p < _ALPHA and observed_noetic_mean > null_quantiles["p95"]:
        verdict = "NOETIC_EFFECT_DIRECTION_MEANINGFUL_N30_PERMUTATION"
    elif observed_noetic_mean > null_mean and permutation_p < 0.10:
        verdict = "NOETIC_EFFECT_SUGGESTIVE_N30_PERMUTATION"
    else:
        verdict = "NOETIC_EFFECT_NOT_ABOVE_RANDOM_N30_PERMUTATION"

    verdict_text = (
        f"Noetic mean disruption is {observed_noetic_mean:+.3f}. "
        f"The n=30 random-direction permutation null has mean {null_mean:+.3f}, "
        f"std {null_std:.3f}, p95 {null_quantiles['p95']:+.3f}. "
        f"One-sided permutation p={permutation_p:.4f} over {_N_PERMUTATIONS} "
        f"matched 10-direction samples. Verdict: {verdict}."
    )

    print()
    print("STAGE 3.3 N=30 PERMUTATION CONTROL")
    print(f"  noetic mean disruption: {observed_noetic_mean:+.4f}")
    print(f"  noetic one-sample t: t={float(t_noetic):.3f} p={float(p_noetic):.4f}")
    print(f"  random null mean: {null_mean:+.4f} std={null_std:.4f}")
    print(f"  random null quantiles: {null_quantiles}")
    print(f"  effect over null mean: {effect_over_null:+.4f}")
    print(f"  permutation p(one-sided): {permutation_p:.4f}")
    print(f"VERDICT: {verdict}")
    print(verdict_text)

    report = {
        "schema_version": "pythia_ablation_random_control_layer3_n30.v1",
        "experiment": "Stage 3.3 random-direction n=30 permutation control",
        "model_name": _MODEL_NAME,
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "target_layer_index": _TARGET_LAYER_INDEX,
        "hook_block_index": _HOOK_BLOCK_INDEX,
        "max_new_tokens": _MAX_NEW_TOKENS,
        "continuation_prefixes": [{"name": p[0], "suffix": p[1]} for p in _CONTINUATION_PREFIXES],
        "device": str(device),
        "local_files_only": True,
        "random_seed": _RANDOM_SEED,
        "n_random_directions": _N_RANDOM_DIRECTIONS,
        "n_noetic_directions": n_classes,
        "n_permutations": _N_PERMUTATIONS,
        "package_versions": {
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "activations_file": _ACTIVATIONS_PATH.name,
        "activations_sha256": activations_sha,
        "probes_file": _PROBES_PATH.name,
        "probes_sha256": probes_sha,
        "noetic_stage32_file": _NOETIC_STAGE32_PATH.name,
        "noetic_stage32_sha256": noetic_stage32_sha,
        "noetic_subspace_rank": noetic_rank,
        "random_direction_diagnostics": {
            "norms_min": float(rand_norms.min()),
            "norms_max": float(rand_norms.max()),
            "max_cosine_with_noetic": float(np.max(np.abs(rand_x_noetic))),
            "max_offdiag_cosine_with_other_random": float(
                np.max(np.abs(rand_x_rand - np.eye(_N_RANDOM_DIRECTIONS)))
            ),
        },
        "random_matrix_mean_token_match_rate": random_match.tolist(),
        "random_matrix_n_cases": random_n.tolist(),
        "random_assigned_disruption_matrix": random_assigned_disruptions.tolist(),
        "noetic_per_class_disruption_deltas": noetic_disruption_arr.tolist(),
        "noetic_one_sample_t_test": {
            "t": float(t_noetic),
            "p_two_sided": float(p_noetic),
            "df": int(n_classes - 1),
            "n": int(n_classes),
        },
        "permutation_test": {
            "observed_noetic_mean": observed_noetic_mean,
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
        "per_case": per_case,
        "verdict": verdict,
        "verdict_text": verdict_text,
    }
    with _OUT_REPORT.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"report written: {_OUT_REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
