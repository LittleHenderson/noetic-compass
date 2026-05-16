"""Stage 3.2 — per-class targeted ablation at layer 3.

Stage 3.1 showed that removing the full 9-dim noetic subspace from
Pythia's layer-3 residual stream changes its continuations. The
follow-up question Codex flagged:

  > Do the changes actually track noetic meaning, or are they just
  > general distribution shifts?

This script answers that with a targeted-ablation specificity test.

For each noetic class c in {0..9}:

* Extract just that class's probe direction in raw activation space:
  w_c_raw = w_c_std / sigma. Normalize to unit length: u_c.
* Build a 1D projection matrix P_c = u_c @ u_c^T.
* For each test-set prompt + continuation prefix (same as Stage 3.1),
  generate the baseline continuation (no hook) and the ablated
  continuation with the hook removing only u_c.
* Bucket every (ablated_class, true_y) pair into a 10x10 matrix.
* Compute per-cell mean of two divergence metrics:
    - first_token_changed: fraction of cases where baseline_top1 !=
      ablated_top1 at the first generated step.
    - mean_token_match: fraction of token positions that matched
      between baseline and ablated continuations.

Headline metric:

  Specificity ratio per class c =
      mean( divergence when ablated=c AND true_y=c )
    / mean( divergence when ablated=c AND true_y!=c )

  Ratio > 1 means ablating class c is more disruptive to class-c
  prompts than to other-class prompts. A class-specific direction
  shows a clean ratio > 1; a generic / pooled direction shows ratio
  ~ 1; a noise direction shows ratio fluctuating around 1.

We also report two aggregate views:

  diagonal_mean   = mean over the 10 diagonal cells
  off_diag_mean   = mean over the 90 off-diagonal cells

If diagonal_mean > off_diag_mean by a clear margin, the
ablation is class-specific in aggregate. If the two are
indistinguishable, the layer-3 directions point at a common
"noetic-shaped" axis without class-specific information.

This is a NARROW mechanistic test, not full semantic interpretation.
Per Codex's standing rule: exploratory only, no public Glass House
claims off this single experiment.

Run:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/ablate_noetic_per_class_layer3.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_TODAY = "20260515"

_ACTIVATIONS_PATH = _HERE / f"pythia_probe_activations_{_TODAY}.npz"
_PROBES_PATH = _HERE / f"pythia_noetic_probes_{_TODAY}.npz"
_PROBES_REPORT_PATH = _HERE / f"pythia_noetic_probes_report_{_TODAY}.json"
_LABELS_PATH = _HERE / f"pythia_probe_labels_{_TODAY}.jsonl"
_OUT_REPORT = _HERE / f"pythia_ablation_per_class_layer3_{_TODAY}.json"

_MODEL_NAME = "EleutherAI/pythia-160m"
_TARGET_LAYER_INDEX = 3
_HOOK_BLOCK_INDEX = _TARGET_LAYER_INDEX - 1
_MAX_NEW_TOKENS = 8
_CONTINUATION_PREFIXES: tuple[tuple[str, str], ...] = (
    ("in_other_words", "\nIn other words,"),
    ("this_concept_means", "\nThis concept means"),
    ("good_explanation", "\nA good explanation is"),
)


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
        import torch
        import transformers
        from sklearn.metrics import accuracy_score
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        print(
            f"missing dependency: {exc}\n"
            f"  pip install scikit-learn numpy torch transformers",
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
    intercepts = probes["intercepts"]
    scaler_mean = probes["scaler_mean"]
    scaler_scale = probes["scaler_scale"]
    idx_test = probes["idx_test"]

    with _PROBES_REPORT_PATH.open(encoding="utf-8") as fh:
        report_in = json.load(fh)
    headline_layer = int(report_in["headline_layer"]["layer"])
    assert headline_layer == _TARGET_LAYER_INDEX, (
        f"this script ablates layer {_TARGET_LAYER_INDEX} but the headline "
        f"is layer {headline_layer}"
    )

    labels: dict[str, str] = {}
    with _LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                labels[r["sample_id"]] = r["english"]

    layer = _TARGET_LAYER_INDEX
    w_std = coefs[layer]
    sigma = scaler_scale[layer]
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = w_std / sigma_safe[None, :]
    n_classes = w_raw.shape[0]

    # Unit-normalize each class's raw-space direction. Each u_c is a
    # single 768-dim unit vector. P_c = u_c outer u_c.
    norms = np.linalg.norm(w_raw, axis=1, keepdims=True)
    norms_safe = np.where(norms == 0, 1.0, norms)
    u = w_raw / norms_safe  # (10, 768) unit vectors

    print(f"per-class direction norms: {[f'{n:.3f}' for n in norms.ravel()]}")
    # Off-diagonal cosine similarities — these tell us how separated the
    # per-class directions are.
    cos_matrix = u @ u.T
    off_diag_mask = np.ones_like(cos_matrix, dtype=bool)
    np.fill_diagonal(off_diag_mask, False)
    off_diag_cos = cos_matrix[off_diag_mask]
    print(
        f"per-class direction off-diagonal cosine: mean={off_diag_cos.mean():.3f}"
        f" max_abs={np.max(np.abs(off_diag_cos)):.3f}"
    )

    # ------------------------------------------------------------------ #
    # Sanity gate (probe self-ablation) — same as Stage 3.1, kept for
    # cross-reference. Here we ablate only ONE direction at a time; the
    # probe accuracy on that class's predictions should drop sharply.
    # ------------------------------------------------------------------ #
    print()
    print("Sanity gate per class (probe self-ablation, test set):")
    h_raw_all = X[:, layer, :]
    y_test = y[idx_test]
    sanity_pass_per_class: list[bool] = []
    sanity_gate_per_class: list[dict[str, Any]] = []
    for c in range(n_classes):
        Pc_np = np.outer(u[c], u[c])
        h_ablated = h_raw_all - h_raw_all @ Pc_np
        h_std = (h_raw_all - scaler_mean[layer]) / sigma_safe
        h_ablated_std = (h_ablated - scaler_mean[layer]) / sigma_safe
        logits = h_ablated_std @ w_std.T + intercepts[layer][None, :]
        preds_ablated = np.argmax(logits, axis=1)
        # Look at how often the ablated probe still predicts class c.
        n_test = len(idx_test)
        ablated_preds_test = preds_ablated[idx_test]
        # Among true-y == c records in test, how often is ablated pred == c?
        mask_c = y_test == c
        if mask_c.sum() > 0:
            ablated_self_correct = float(np.mean(
                ablated_preds_test[mask_c] == c
            ))
        else:
            ablated_self_correct = float("nan")
        # And among all test records, how often is ablated pred == c?
        ablated_pred_c_rate = float(np.mean(ablated_preds_test == c))
        # Expected behavior: ablating direction c suppresses class c
        # predictions. So ablated_pred_c_rate should drop below the
        # baseline rate (which is just majority class share for c).
        baseline_pred_c_rate = float(np.mean(y_test == c))
        print(
            f"  ^{c}: self-class kept-rate={ablated_self_correct:.3f} "
            f"(baseline support {baseline_pred_c_rate:.3f}, "
            f"ablated pred=c rate={ablated_pred_c_rate:.3f})"
        )
        sanity_pass = bool(ablated_self_correct < 0.5)
        sanity_pass_per_class.append(sanity_pass)
        sanity_gate_per_class.append(
            {
                "class": int(c),
                "self_class_kept_rate": float(ablated_self_correct),
                "baseline_support": float(baseline_pred_c_rate),
                "ablated_pred_c_rate": float(ablated_pred_c_rate),
                "pass": sanity_pass,
            }
        )

    # ------------------------------------------------------------------ #
    # Load Pythia + tokenizer.
    # ------------------------------------------------------------------ #
    print()
    print(f"loading {_MODEL_NAME} from local cache only ...")
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=True)
    model.eval()
    # CPU is intentional here: it preserves the committed Stage 3.2
    # artifact's execution mode. If this moves to CUDA, record it as a
    # distinct rerun instead of silently changing the experiment.
    device = torch.device("cpu")
    model.to(device)
    model_revision = getattr(model.config, "_commit_hash", None)
    model_config_name = getattr(model.config, "_name_or_path", None)

    block = model.gpt_neox.layers[_HOOK_BLOCK_INDEX]

    # Pre-build per-class projection matrices on device.
    P_per_class = [
        torch.tensor(np.outer(u[c], u[c]), dtype=torch.float32, device=device)
        for c in range(n_classes)
    ]

    def make_class_hook(c: int) -> Any:
        Pc = P_per_class[c]
        def hook(_module, _input, output):
            if isinstance(output, tuple):
                hs = output[0]
                hs_ablated = hs - hs @ Pc.to(hs.dtype)
                return (hs_ablated,) + output[1:]
            return output - output @ Pc.to(output.dtype)
        return hook

    def greedy_generate(
        prompt_text: str,
        n_new: int,
        hook_fn: Any | None,
    ) -> list[int]:
        """Greedy decode n_new tokens after prompt_text. If hook_fn is
        provided, install it on the target block for the duration."""
        encoded = tokenizer(
            prompt_text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        ).to(device)
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
                    cur_ids = torch.cat(
                        [cur_ids, torch.tensor([[next_tok]], device=device)],
                        dim=1,
                    )
                    if cur_mask is not None:
                        cur_mask = torch.cat(
                            [cur_mask, torch.tensor([[1]], device=device)],
                            dim=1,
                        )
        finally:
            if handle is not None:
                handle.remove()
        return generated

    # ------------------------------------------------------------------ #
    # Generate baselines once per (prompt, prefix). Then ablate per-class.
    # ------------------------------------------------------------------ #
    print()
    print("generating baselines + per-class ablations ...")
    started = time.perf_counter()

    test_ids = [str(sample_ids[i]) for i in idx_test.tolist()]
    test_y_list = [int(y[i]) for i in idx_test.tolist()]

    # cells[ablated_c][true_y] = list of per-case rows
    cells: list[list[list[dict[str, Any]]]] = [
        [[] for _ in range(n_classes)] for _ in range(n_classes)
    ]
    per_case: list[dict[str, Any]] = []

    # First: cache baselines
    baseline_cache: dict[tuple[str, str], list[int]] = {}
    for ti, sid in enumerate(test_ids):
        text = labels[sid]
        for prefix_name, suffix in _CONTINUATION_PREFIXES:
            prompt_text = text + suffix
            key = (sid, prefix_name)
            baseline_cache[key] = greedy_generate(prompt_text, _MAX_NEW_TOKENS, None)

    base_elapsed = time.perf_counter() - started
    print(f"  baselines done in {base_elapsed:.1f}s")

    # Then per-class ablations
    for c in range(n_classes):
        hook = make_class_hook(c)
        for ti, sid in enumerate(test_ids):
            text = labels[sid]
            true_y = test_y_list[ti]
            for prefix_name, suffix in _CONTINUATION_PREFIXES:
                prompt_text = text + suffix
                key = (sid, prefix_name)
                baseline_tokens = baseline_cache[key]
                ablated_tokens = greedy_generate(
                    prompt_text, _MAX_NEW_TOKENS, hook
                )
                first_match = (
                    baseline_tokens[0] == ablated_tokens[0]
                    if baseline_tokens and ablated_tokens
                    else True
                )
                pos_matches = sum(
                    1 for a, b in zip(baseline_tokens, ablated_tokens) if a == b
                )
                token_match_rate = (
                    pos_matches / max(1, min(len(baseline_tokens),
                                             len(ablated_tokens)))
                )
                exact = baseline_tokens == ablated_tokens
                row = {
                    "sample_id": sid,
                    "true_y": true_y,
                    "ablated_class": c,
                    "prefix": prefix_name,
                    "first_token_changed": not first_match,
                    "token_match_rate": float(token_match_rate),
                    "exact_match": bool(exact),
                }
                cells[c][true_y].append(row)
                per_case.append(row)
        elapsed = time.perf_counter() - started
        print(f"  ablated direction ^{c} done at elapsed={elapsed:.1f}s")

    # ------------------------------------------------------------------ #
    # Aggregate: 10x10 matrix of mean first_token_changed rate.
    # ------------------------------------------------------------------ #
    import numpy as _np
    matrix_first_changed = _np.zeros((n_classes, n_classes), dtype=float)
    matrix_token_match = _np.zeros((n_classes, n_classes), dtype=float)
    matrix_n = _np.zeros((n_classes, n_classes), dtype=int)
    for c in range(n_classes):
        for ty in range(n_classes):
            rows = cells[c][ty]
            if not rows:
                matrix_first_changed[c, ty] = float("nan")
                matrix_token_match[c, ty] = float("nan")
                matrix_n[c, ty] = 0
                continue
            matrix_first_changed[c, ty] = float(_np.mean(
                [int(r["first_token_changed"]) for r in rows]
            ))
            matrix_token_match[c, ty] = float(_np.mean(
                [r["token_match_rate"] for r in rows]
            ))
            matrix_n[c, ty] = len(rows)

    diag_first = float(_np.nanmean(_np.diag(matrix_first_changed)))
    off_mask = ~_np.eye(n_classes, dtype=bool)
    off_first = float(_np.nanmean(matrix_first_changed[off_mask]))

    diag_match = float(_np.nanmean(_np.diag(matrix_token_match)))
    off_match = float(_np.nanmean(matrix_token_match[off_mask]))

    # Per-class specificity ratio.
    spec_ratios: list[dict[str, Any]] = []
    token_match_specificity: list[dict[str, Any]] = []
    for c in range(n_classes):
        self_rate = matrix_first_changed[c, c]
        cross_rates = matrix_first_changed[c, [ty for ty in range(n_classes) if ty != c]]
        cross_mean = float(_np.nanmean(cross_rates))
        ratio = (
            self_rate / cross_mean
            if cross_mean and not _np.isnan(cross_mean) and cross_mean > 0
            else float("nan")
        )
        spec_ratios.append(
            {
                "class": c,
                "self_first_changed_rate": float(self_rate),
                "cross_first_changed_rate_mean": cross_mean,
                "specificity_ratio": ratio,
            }
        )
        self_match = matrix_token_match[c, c]
        cross_match_rates = matrix_token_match[c, [ty for ty in range(n_classes) if ty != c]]
        cross_match_mean = float(_np.nanmean(cross_match_rates))
        token_match_specificity.append(
            {
                "class": c,
                "self_token_match_rate": float(self_match),
                "cross_token_match_rate_mean": cross_match_mean,
                "extra_same_class_disruption": float(cross_match_mean - self_match),
            }
        )

    # ------------------------------------------------------------------ #
    # Print summary.
    # ------------------------------------------------------------------ #
    print()
    print("first_token_changed rate, 10x10 (rows=ablated_class, cols=true_y):")
    header = "       " + "  ".join(f"^{c}" for c in range(n_classes))
    print(header)
    for c in range(n_classes):
        cells_line = "  ".join(
            f"{matrix_first_changed[c, ty]:.2f}" if not _np.isnan(matrix_first_changed[c, ty])
            else "  - "
            for ty in range(n_classes)
        )
        print(f"  ^{c}    {cells_line}")
    print()
    print(
        f"diagonal mean first_changed:    {diag_first:.3f}  "
        f"(ablate ^c on class ^c prompts)"
    )
    print(
        f"off-diagonal mean first_changed: {off_first:.3f}  "
        f"(ablate ^c on other-class prompts)"
    )
    print(
        f"delta (diag - off):              {(diag_first - off_first):+.3f}"
    )
    print()
    print("Per-class specificity ratio (self / cross):")
    for sr in spec_ratios:
        print(
            f"  ^{sr['class']}: self={sr['self_first_changed_rate']:.3f} "
            f"cross={sr['cross_first_changed_rate_mean']:.3f} "
            f"ratio={sr['specificity_ratio']:.2f}"
        )

    # ------------------------------------------------------------------ #
    # Verdict.
    # ------------------------------------------------------------------ #
    delta = diag_first - off_first
    if delta >= 0.10:
        verdict = "PER_CLASS_DIRECTIONS_SHOW_SPECIFICITY"
        verdict_text = (
            f"Ablating per-class noetic directions affects same-class prompts "
            f"more than other-class prompts by {delta:.3f} (diag mean "
            f"{diag_first:.3f} vs off-diag mean {off_first:.3f}). The "
            f"layer-3 per-class directions carry class-specific behavioural "
            f"weight, not just generic 'noetic-shaped' axis content. This "
            f"upgrades the Stage 3.1 evidence: ablation is behaviourally "
            f"active AND class-specific. Exploratory only; semantic content "
            f"of the changes still needs human audit before any mechanistic "
            f"claim about CAS encoding."
        )
    elif delta >= 0.03:
        verdict = "WEAK_PER_CLASS_SPECIFICITY"
        verdict_text = (
            f"Diagonal vs off-diagonal first_token_changed delta is "
            f"{delta:.3f}. Some class-specific structure exists but the "
            f"effect is small. May be noise on the per-class cell sizes "
            f"(~6-9 cases per cell). Needs more data or a stricter test "
            f"before claiming specificity."
        )
    elif delta >= -0.03:
        verdict = "NO_PER_CLASS_SPECIFICITY"
        verdict_text = (
            f"Diagonal and off-diagonal first_token_changed rates are "
            f"indistinguishable ({diag_first:.3f} vs {off_first:.3f}). "
            f"Ablating one class's direction is no more disruptive to "
            f"its own class's prompts than to other classes' prompts. "
            f"The Stage 3.1 behavioural effect is real but not class-"
            f"specific at layer 3 — the directions point at a shared "
            f"'noetic-shaped' axis, not at distinct per-class features. "
            f"This bounds the mechanistic claim sharply."
        )
    else:
        verdict = "REVERSED_SPECIFICITY"
        verdict_text = (
            f"Ablation appears MORE disruptive to other-class prompts "
            f"than to same-class prompts (diag {diag_first:.3f} < "
            f"off-diag {off_first:.3f}). Unexpected. Likely small-cell "
            f"noise; needs replication."
        )

    print()
    print(f"VERDICT: {verdict}")
    print(verdict_text)

    report = {
        "schema_version": "pythia_ablation_per_class_layer3.v1",
        "experiment": (
            "Stage 3.2 — per-class targeted ablation of layer-3 noetic "
            "directions on Pythia-160M"
        ),
        "model_name": _MODEL_NAME,
        "model_revision": model_revision,
        "model_config_name_or_path": model_config_name,
        "local_files_only": True,
        "device": str(device),
        "package_versions": {
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
        "target_layer_index": _TARGET_LAYER_INDEX,
        "hook_block_index": _HOOK_BLOCK_INDEX,
        "max_new_tokens": _MAX_NEW_TOKENS,
        "continuation_prefixes": [
            {"name": p[0], "suffix": p[1]} for p in _CONTINUATION_PREFIXES
        ],
        "activations_file": _ACTIVATIONS_PATH.name,
        "activations_sha256": activations_sha,
        "probes_file": _PROBES_PATH.name,
        "probes_sha256": probes_sha,
        "n_classes": int(n_classes),
        "per_class_direction_norms": [float(n) for n in norms.ravel()],
        "per_class_direction_off_diag_cosine_stats": {
            "mean": float(off_diag_cos.mean()),
            "max_abs": float(_np.max(_np.abs(off_diag_cos))),
        },
        "sanity_gate_per_class": sanity_gate_per_class,
        "sanity_gate_per_class_self_kept_rates": (
            "see stdout — class c's pred rate on true_y==c after ablating "
            "only direction c. Should drop below 0.5 for the ablation to "
            "be considered specific to that class."
        ),
        "matrix_first_token_changed": matrix_first_changed.tolist(),
        "matrix_mean_token_match_rate": matrix_token_match.tolist(),
        "matrix_n_cases": matrix_n.tolist(),
        "axis_order_rows_are_ablated_class": True,
        "axis_order_cols_are_true_y": True,
        "diagonal_first_changed_mean": diag_first,
        "off_diagonal_first_changed_mean": off_first,
        "diag_minus_off_first_changed": delta,
        "diagonal_token_match_mean": diag_match,
        "off_diagonal_token_match_mean": off_match,
        "extra_same_class_token_disruption": float(off_match - diag_match),
        "per_class_specificity": spec_ratios,
        "per_class_token_match_specificity": token_match_specificity,
        "decision_thresholds": {
            "strong_specificity_delta_min": 0.10,
            "weak_specificity_delta_min": 0.03,
        },
        "per_case": per_case,
        "verdict": verdict,
        "verdict_text": verdict_text,
    }
    with _OUT_REPORT.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print()
    print(f"report written: {_OUT_REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
