"""Stage 3.2 control — random-direction ablation at layer 3.

Stage 3.2's clean GPU rerun produced a `MIXED_SPECIFICITY_EVIDENCE`
verdict: ablating per-class noetic directions disrupts same-class
continuations by 0.079 token-match more than other-class continuations,
with t=2.56, p=0.031.

But the per-class disruption is uneven: ^7 carries +0.214, ^2 +0.186,
^3 and ^5 show the opposite sign. **Risk:** the "specificity" might be
class-difficulty (^7-typical Pythia continuations might be more
vocabulary-narrow and more disrupted by ANY ablation), not anything
specific about the noetic directions.

This script is the control that disambiguates:

* Sample 10 random unit vectors in the orthogonal complement of the
  noetic-subspace span.
* Fixed seed (42) for reproducibility.
* Run the same 10x10 per-class disruption experiment with these
  random directions in place of the noetic per-class directions.
* Compute the same diag-vs-off-diag and per-class disruption stats.

Decision rule:

Audit note: full `NOETIC_EFFECT_DIRECTION_MEANINGFUL` now requires
the direct noetic-vs-random Welch comparison to pass alpha=0.05.
The weaker pattern "noetic non-zero, random null" is suggestive
control evidence only.

* random diag-off >= noetic diag-off  → "specificity" is class-
  difficulty artifact. Glass House claim blocked.
* random diag-off ≈ 0 AND noetic diag-off remains positive →
  suggestive control evidence. Direction-meaningful upgrade requires
  the direct Welch comparison to pass.

Also folds in audit Patch 1: report formal one-sample t-test on
per-class disruption deltas (both noetic and random arms).

Run on the pod (A6000):

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/ablate_random_direction_layer3.py
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
# Read the prior Stage 3.2 noetic-arm result for side-by-side compare.
_NOETIC_STAGE32_PATH = _HERE / "pythia_ablation_per_class_layer3_clean_20260516.json"
_OUT_REPORT = _HERE / f"pythia_ablation_random_control_layer3_{_TODAY}.json"

_MODEL_NAME = "EleutherAI/pythia-160m"
_TARGET_LAYER_INDEX = 3
_HOOK_BLOCK_INDEX = _TARGET_LAYER_INDEX - 1
_MAX_NEW_TOKENS = 8
_CONTINUATION_PREFIXES: tuple[tuple[str, str], ...] = (
    ("in_other_words", "\nIn other words,"),
    ("this_concept_means", "\nThis concept means"),
    ("good_explanation", "\nA good explanation is"),
)
_RANDOM_SEED = 42


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
    for p in (_ACTIVATIONS_PATH, _PROBES_PATH, _PROBES_REPORT_PATH, _LABELS_PATH):
        if not p.is_file():
            raise SystemExit(f"missing prerequisite: {p}")

    try:
        import numpy as np
        import scipy
        import torch
        import transformers
        from scipy.stats import ttest_1samp, ttest_ind
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
    print(f"activations sha256: {activations_sha}")
    print(f"probes sha256:      {probes_sha}")

    act = np.load(_ACTIVATIONS_PATH, allow_pickle=False)
    X = act["X"]
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

    # ------------------------------------------------------------------ #
    # Build the noetic subspace orthonormal basis (raw activation space).
    # Then sample 10 random unit vectors in the orthogonal complement.
    # ------------------------------------------------------------------ #
    layer = _TARGET_LAYER_INDEX
    w_std = coefs[layer]
    sigma = scaler_scale[layer]
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = w_std / sigma_safe[None, :]  # (10, 768) noetic directions
    n_classes = w_raw.shape[0]
    hidden_dim = w_raw.shape[1]

    # SVD of noetic directions; columns of Vh (rows) span the subspace.
    U_svd, S_svd, Vh = np.linalg.svd(w_raw, full_matrices=False)
    keep = S_svd > S_svd.max() * 1e-6
    noetic_basis = Vh[keep]  # (k, 768)
    noetic_rank = noetic_basis.shape[0]
    # Projection onto noetic subspace
    P_noetic = noetic_basis.T @ noetic_basis  # (768, 768)
    P_complement = np.eye(hidden_dim) - P_noetic  # projection onto orthogonal complement

    # Sample n_classes random unit vectors. Procedure:
    # 1. Sample Gaussian, shape (10, 768)
    # 2. Project onto noetic complement (zero out noetic-subspace component)
    # 3. Gram-Schmidt orthonormalize so the 10 random directions are mutually orthonormal
    #    (parallel to how noetic directions are roughly orthogonal)
    # 4. Normalize each to unit length
    rng = np.random.default_rng(_RANDOM_SEED)
    raw_random = rng.standard_normal((n_classes, hidden_dim))
    # Project away from noetic subspace
    proj_random = raw_random @ P_complement
    # Orthonormalize the 10 random vectors among themselves (QR decomposition).
    # proj_random.T is (768, 10); QR gives Q (768, 10) with orthonormal columns.
    Q, _ = np.linalg.qr(proj_random.T)
    u_random = Q.T  # (10, 768) — orthonormal rows

    # Sanity: each u_random is unit-length, orthogonal to noetic basis,
    # mutually orthogonal.
    rand_norms = np.linalg.norm(u_random, axis=1)
    rand_x_noetic = u_random @ noetic_basis.T  # (10, k) — should be ~0
    rand_x_rand = u_random @ u_random.T  # (10, 10) — should be identity
    print(f"random direction norms: min={rand_norms.min():.4f} max={rand_norms.max():.4f}")
    print(f"random x noetic cosine: max_abs={np.max(np.abs(rand_x_noetic)):.6f} (target 0)")
    print(f"random x random off-diag: max_abs={np.max(np.abs(rand_x_rand - np.eye(n_classes))):.6f} (target 0)")

    # ------------------------------------------------------------------ #
    # Load Pythia.
    # ------------------------------------------------------------------ #
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

    P_per_dir = [
        torch.tensor(np.outer(u_random[c], u_random[c]), dtype=torch.float32, device=device)
        for c in range(n_classes)
    ]

    def make_dir_hook(c: int) -> Any:
        Pc = P_per_dir[c]
        def hook(_module, _input, output):
            if isinstance(output, tuple):
                hs = output[0]
                hs_ablated = hs - hs @ Pc.to(hs.dtype)
                return (hs_ablated,) + output[1:]
            return output - output @ Pc.to(output.dtype)
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

    # ------------------------------------------------------------------ #
    # Baselines (no hook). Same prompts as Stage 3.2.
    # ------------------------------------------------------------------ #
    print()
    print("generating baselines + 10 random-direction ablations ...")
    started = time.perf_counter()

    test_ids = [str(sample_ids[i]) for i in idx_test.tolist()]
    test_y_list = [int(y[i]) for i in idx_test.tolist()]

    baseline_cache: dict[tuple[str, str], list[int]] = {}
    for ti, sid in enumerate(test_ids):
        text = labels[sid]
        for prefix_name, suffix in _CONTINUATION_PREFIXES:
            prompt_text = text + suffix
            baseline_cache[(sid, prefix_name)] = greedy_generate(prompt_text, _MAX_NEW_TOKENS, None)
    base_elapsed = time.perf_counter() - started
    print(f"  baselines done in {base_elapsed:.1f}s")

    # Per-random-direction ablations. For each "random class" c in 0..9, run
    # ablation and bucket by true_y. This gives a 10x10 matrix matching
    # the noetic-arm shape, but where "ablated class" is just a random-dir
    # index, not a CAS class.
    cells_first_changed: list[list[list[int]]] = [[[] for _ in range(n_classes)] for _ in range(n_classes)]
    cells_token_match: list[list[list[float]]] = [[[] for _ in range(n_classes)] for _ in range(n_classes)]
    per_case: list[dict[str, Any]] = []

    for c in range(n_classes):
        hook = make_dir_hook(c)
        for ti, sid in enumerate(test_ids):
            true_y = test_y_list[ti]
            text = labels[sid]
            for prefix_name, suffix in _CONTINUATION_PREFIXES:
                prompt_text = text + suffix
                baseline_tokens = baseline_cache[(sid, prefix_name)]
                ablated_tokens = greedy_generate(prompt_text, _MAX_NEW_TOKENS, hook)
                first_match = (baseline_tokens[0] == ablated_tokens[0]) if baseline_tokens and ablated_tokens else True
                pos_matches = sum(1 for a, b in zip(baseline_tokens, ablated_tokens) if a == b)
                tlen = max(1, min(len(baseline_tokens), len(ablated_tokens)))
                tmatch = pos_matches / tlen
                cells_first_changed[c][true_y].append(0 if first_match else 1)
                cells_token_match[c][true_y].append(float(tmatch))
                per_case.append({
                    "sample_id": sid,
                    "true_y": true_y,
                    "random_dir_index": c,
                    "prefix": prefix_name,
                    "first_token_changed": not first_match,
                    "token_match_rate": float(tmatch),
                })
        elapsed = time.perf_counter() - started
        print(f"  random direction {c} done at elapsed={elapsed:.1f}s")

    # ------------------------------------------------------------------ #
    # Aggregate matrices.
    # ------------------------------------------------------------------ #
    M_first = np.zeros((n_classes, n_classes), dtype=float)
    M_match = np.zeros((n_classes, n_classes), dtype=float)
    M_n = np.zeros((n_classes, n_classes), dtype=int)
    for c in range(n_classes):
        for ty in range(n_classes):
            rows_fc = cells_first_changed[c][ty]
            rows_tm = cells_token_match[c][ty]
            M_first[c, ty] = float(np.mean(rows_fc)) if rows_fc else float("nan")
            M_match[c, ty] = float(np.mean(rows_tm)) if rows_tm else float("nan")
            M_n[c, ty] = len(rows_fc)

    diag_first_rand = float(np.nanmean(np.diag(M_first)))
    off_mask = ~np.eye(n_classes, dtype=bool)
    off_first_rand = float(np.nanmean(M_first[off_mask]))
    diag_match_rand = float(np.nanmean(np.diag(M_match)))
    off_match_rand = float(np.nanmean(M_match[off_mask]))

    # Per-direction disruption (cross - self) on token-match, paired t-test.
    disruptions = []
    for c in range(n_classes):
        self_v = M_match[c, c]
        cross = np.delete(M_match[c], c)
        disruptions.append(np.nanmean(cross) - self_v)
    disruption_arr = np.array(disruptions)
    t_stat, p_val = ttest_1samp(disruption_arr, 0.0)

    # Same stats from the noetic arm for side-by-side compare.
    try:
        with _NOETIC_STAGE32_PATH.open(encoding="utf-8") as fh:
            noetic_report = json.load(fh)
        M_noetic_match = np.array(noetic_report["matrix_mean_token_match_rate"])
        noetic_disruptions = []
        for c in range(n_classes):
            self_v = M_noetic_match[c, c]
            cross = np.delete(M_noetic_match[c], c)
            noetic_disruptions.append(np.nanmean(cross) - self_v)
        noetic_disruption_arr = np.array(noetic_disruptions)
        t_noetic, p_noetic = ttest_1samp(noetic_disruption_arr, 0.0)
        t_welch, p_welch = ttest_ind(
            noetic_disruption_arr,
            disruption_arr,
            equal_var=False,
        )
    except Exception as exc:
        print(f"WARN could not load noetic stage 3.2 report for compare: {exc}")
        noetic_disruption_arr = None
        t_noetic = None
        p_noetic = None
        t_welch = None
        p_welch = None

    # ------------------------------------------------------------------ #
    # Verdict.
    # ------------------------------------------------------------------ #
    print()
    print("RANDOM-CONTROL token-match diagonal vs off-diagonal:")
    print(f"  diag:    {diag_match_rand:.3f}")
    print(f"  off:     {off_match_rand:.3f}")
    print(f"  delta (off - diag):  {off_match_rand - diag_match_rand:+.3f}")
    print(f"  mean per-dir disruption: {disruption_arr.mean():+.3f} (std {disruption_arr.std():.3f})")
    print(f"  one-sample t against 0: t={t_stat:.3f} p={p_val:.4f}")

    if noetic_disruption_arr is not None:
        print()
        print("NOETIC arm (from clean Stage 3.2 report) for compare:")
        print(f"  mean per-class disruption: {noetic_disruption_arr.mean():+.3f} (std {noetic_disruption_arr.std():.3f})")
        print(f"  one-sample t against 0: t={t_noetic:.3f} p={p_noetic:.4f}")
        print(f"  Welch noetic vs random: t={t_welch:.3f} p={p_welch:.4f}")

    # Decision rule. Random disruption near zero AND noetic disruption
    # remains the established +0.079 → noetic effect IS direction-
    # meaningful. Random disruption similar to noetic → class-difficulty
    # artifact.
    # Superseding audit gate: the above pattern is only suggestive unless
    # the direct noetic-vs-random Welch comparison also passes.
    NEAR_ZERO_THRESHOLD = 0.03
    ALPHA = 0.05
    random_is_null = abs(disruption_arr.mean()) < NEAR_ZERO_THRESHOLD and p_val > ALPHA
    noetic_is_nonzero = (
        noetic_disruption_arr is not None
        and p_noetic is not None
        and p_noetic < ALPHA
        and float(noetic_disruption_arr.mean()) > 0
    )
    direct_compare_pass = (
        noetic_disruption_arr is not None
        and p_welch is not None
        and p_welch < ALPHA
        and float(noetic_disruption_arr.mean()) > float(disruption_arr.mean())
    )
    if random_is_null and noetic_is_nonzero and direct_compare_pass:
        verdict = "NOETIC_EFFECT_DIRECTION_MEANINGFUL"
        verdict_text = (
            f"Random unit directions in the noetic subspace's orthogonal "
            f"complement produce per-direction disruption {disruption_arr.mean():+.3f} "
            f"(t={t_stat:.3f}, p={p_val:.4f}) — indistinguishable from zero. "
            f"The noetic-arm disruption (+0.079, p=0.031) survives the "
            f"control: it is not class-difficulty artifact, it reflects "
            f"direction-meaningful structure in the noetic subspace. "
            f"Stage 3.2 MIXED_SPECIFICITY_EVIDENCE upgrades to "
            f"NOETIC_EFFECT_DIRECTION_MEANINGFUL on this evidence. "
            f"Per-class variance (8 of 10 positive, ^7/^2/^8 strong) "
            f"remains a caveat; ^3/^5 wrong-direction also still applies."
        )
    elif disruption_arr.mean() >= 0.5 * abs(noetic_disruption_arr.mean() if noetic_disruption_arr is not None else 0):
        verdict = "CLASS_DIFFICULTY_ARTIFACT"
        verdict_text = (
            f"Random-direction control produces disruption "
            f"{disruption_arr.mean():+.3f} that is comparable to the "
            f"noetic arm. The Stage 3.2 'specificity' is class-"
            f"difficulty artifact — some classes' prompts are simply "
            f"more disrupted by ANY direction ablation. Glass House "
            f"per-class specificity claim is not supported by this "
            f"evidence; back to LABELS_RECOVERABLE_MOSTLY_FROM_TEXT "
            f"as the standing finding."
        )
    else:
        verdict = "CONTROL_INTERMEDIATE"
        verdict_text = (
            f"Random-direction control shows disruption {disruption_arr.mean():+.3f} "
            f"(p={p_val:.4f}), which is non-zero but smaller than the "
            f"noetic arm's +0.079. The noetic effect is partly "
            f"direction-meaningful and partly class-difficulty. "
            f"Verdict held at MIXED_SPECIFICITY_EVIDENCE with this "
            f"control as bounding evidence. No upgrade to direction-"
            f"meaningful claim."
        )

    if random_is_null and noetic_is_nonzero and p_welch is not None and not direct_compare_pass:
        verdict = "NOETIC_EFFECT_SUGGESTIVE_CONTROL_PASSED"
        verdict_text = (
            f"Random unit directions in the noetic subspace's orthogonal "
            f"complement produce per-direction disruption {disruption_arr.mean():+.3f} "
            f"(t={t_stat:.3f}, p={p_val:.4f}), indistinguishable from zero. "
            f"The noetic arm is non-zero (t={t_noetic:.3f}, p={p_noetic:.4f}) "
            f"and points in the expected direction, but the direct noetic-vs-random "
            f"Welch comparison does not pass alpha=0.05 "
            f"(t={t_welch:.3f}, p={p_welch:.4f}). "
            f"This is suggestive control evidence, not a full upgrade to "
            f"NOETIC_EFFECT_DIRECTION_MEANINGFUL. Stage 3.2 remains a modest "
            f"mechanistic signal with a borderline direct comparison."
        )
    elif random_is_null and noetic_is_nonzero and p_welch is not None and direct_compare_pass:
        verdict_text = (
            f"Random unit directions in the noetic subspace's orthogonal "
            f"complement produce per-direction disruption {disruption_arr.mean():+.3f} "
            f"(t={t_stat:.3f}, p={p_val:.4f}), indistinguishable from zero. "
            f"The noetic arm is non-zero (t={t_noetic:.3f}, p={p_noetic:.4f}) "
            f"and the direct noetic-vs-random Welch comparison passes "
            f"(t={t_welch:.3f}, p={p_welch:.4f}). "
            f"Stage 3.2 upgrades to NOETIC_EFFECT_DIRECTION_MEANINGFUL on this "
            f"evidence. Per-class variance remains a caveat."
        )
    print()
    print(f"VERDICT: {verdict}")
    print(verdict_text)

    # ------------------------------------------------------------------ #
    # Write report.
    # ------------------------------------------------------------------ #
    report = {
        "schema_version": "pythia_ablation_random_control_layer3.v1",
        "experiment": "Stage 3.2 random-direction ablation control (audit Patch 3)",
        "model_name": _MODEL_NAME,
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "target_layer_index": _TARGET_LAYER_INDEX,
        "hook_block_index": _HOOK_BLOCK_INDEX,
        "max_new_tokens": _MAX_NEW_TOKENS,
        "continuation_prefixes": [{"name": p[0], "suffix": p[1]} for p in _CONTINUATION_PREFIXES],
        "device": str(device),
        "local_files_only": True,
        "random_seed": _RANDOM_SEED,
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
        "noetic_subspace_rank": int(noetic_rank),
        "random_direction_diagnostics": {
            "norms_min": float(rand_norms.min()),
            "norms_max": float(rand_norms.max()),
            "max_cosine_with_noetic": float(np.max(np.abs(rand_x_noetic))),
            "max_offdiag_cosine_with_other_random": float(np.max(np.abs(rand_x_rand - np.eye(n_classes)))),
        },
        "matrix_first_token_changed": M_first.tolist(),
        "matrix_mean_token_match_rate": M_match.tolist(),
        "matrix_n_cases": M_n.tolist(),
        "diagonal_first_changed_mean": diag_first_rand,
        "off_diagonal_first_changed_mean": off_first_rand,
        "diagonal_token_match_mean": diag_match_rand,
        "off_diagonal_token_match_mean": off_match_rand,
        "per_direction_disruption_deltas": disruption_arr.tolist(),
        "random_one_sample_t_test": {
            "t": float(t_stat),
            "p_two_sided": float(p_val),
            "df": int(n_classes - 1),
            "n": int(n_classes),
        },
        "noetic_one_sample_t_test_for_compare": (
            {
                "t": float(t_noetic),
                "p_two_sided": float(p_noetic),
                "df": int(n_classes - 1),
                "n": int(n_classes),
                "per_class_disruption_deltas": noetic_disruption_arr.tolist(),
                "source_file": _NOETIC_STAGE32_PATH.name,
            }
            if noetic_disruption_arr is not None
            else None
        ),
        "welch_noetic_vs_random_t_test": (
            {
                "t": float(t_welch),
                "p_two_sided": float(p_welch),
                "n_noetic": int(len(noetic_disruption_arr)),
                "n_random": int(len(disruption_arr)),
                "equal_var": False,
            }
            if noetic_disruption_arr is not None and t_welch is not None
            else None
        ),
        "decision_thresholds": {
            "near_zero_random_disruption_max": NEAR_ZERO_THRESHOLD,
            "alpha": ALPHA,
            "direction_meaningful_requires_welch_p_below_alpha": True,
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
