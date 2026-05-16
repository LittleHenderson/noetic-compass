"""Stage 3 — causal ablation of the layer-3 noetic subspace.

Narrow question (per Codex audit `0421e7f`):

  Does the small Pythia-vs-text activation-side difference have
  causal bite, or is it just lexical decoration?

The Stage 2.2 probe found a +1.4 pp accuracy lift at layer 3 over a
plain TF-IDF baseline, which McNemar's exact test could not reliably
distinguish from chance (p=1.0 on 5 discordant samples). Stage 3
asks a different question: even if that lift is small, does ablating
the direction the probe reads change Pythia's actual next-token
behaviour?

Two checks:

1. **Probe-self-ablation sanity gate.** Take the trained layer-3
   probe. Build an orthonormal basis of the 10 noetic-readout
   directions IN THE RAW ACTIVATION SPACE (un-standardized). Project
   each captured layer-3 activation onto the orthogonal complement.
   Re-run the SAME trained probe on the ablated activations. The
   probe accuracy MUST drop sharply — ideally toward the
   majority-class baseline (~0.13) or chance (0.10). If it does not,
   our ablation did not actually remove the signal the probe reads
   and the rest of Stage 3 is invalid.

2. **Next-token causal effect.** For each test-set prompt, run two
   forward passes through Pythia-160M:
       (a) baseline — no hook
       (b) ablated — hook on transformer block 2's output that
           subtracts the noetic-subspace projection from the
           residual stream
   Take the top-1 next-token argmax from each. Report the fraction of
   prompts where baseline_top1 == ablated_top1. A high match rate
   (e.g., >= 95%) means ablation has effectively no causal effect on
   what Pythia says next — the noetic direction is read-out
   decoration. A low match rate (e.g., <= 70%) means ablation does
   change behaviour, suggesting some causal role.

This is a NARROW causal test, not a full mechanistic interpretation.
Exploratory only — no public Glass House claims off this result
regardless of the outcome.

Run:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/ablate_noetic_layer3.py
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
_OUT_REPORT = _HERE / f"pythia_ablation_layer3_{_TODAY}.json"

_MODEL_NAME = "EleutherAI/pythia-160m"
# Hidden-state index 3 (= the captured "layer 3" in Stage 1.1) is the
# residual stream AFTER transformer block index 2. So to ablate the
# layer-3 representation in-flight we hook block index 2's output.
_TARGET_LAYER_INDEX = 3
_HOOK_BLOCK_INDEX = _TARGET_LAYER_INDEX - 1  # transformer block index


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
    X = act["X"]            # (N, 13, 768)
    y = act["y"]            # (N,)
    sample_ids = act["sample_ids"]

    probes = np.load(_PROBES_PATH, allow_pickle=False)
    coefs = probes["coefs"]            # (13, 10, 768) — std space
    intercepts = probes["intercepts"]  # (13, 10)
    scaler_mean = probes["scaler_mean"]    # (13, 768)
    scaler_scale = probes["scaler_scale"]  # (13, 768)
    idx_test = probes["idx_test"]      # (n_test,)

    # Headline layer per the Stage 2.2 report. Read it back rather than
    # hard-code so a re-run with a different headline still works.
    with _PROBES_REPORT_PATH.open(encoding="utf-8") as fh:
        report_in = json.load(fh)
    headline_layer = int(report_in["headline_layer"]["layer"])
    assert headline_layer == _TARGET_LAYER_INDEX, (
        f"this script ablates layer {_TARGET_LAYER_INDEX} but the headline "
        f"is layer {headline_layer}; update _TARGET_LAYER_INDEX or the "
        f"probe pipeline."
    )

    # Load labels file so we can look up the English text per test record.
    labels: dict[str, str] = {}
    with _LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            labels[r["sample_id"]] = r["english"]

    # ------------------------------------------------------------------ #
    # Build the ablation projection in RAW activation space.
    # ------------------------------------------------------------------ #
    # Probe coefs at the headline layer are in standardized space:
    #   logit_c = w_c_std . ((h_raw - mu) / sigma) + b_c
    # The direction the probe reads in RAW space is (w_c_std / sigma).
    layer = _TARGET_LAYER_INDEX
    w_std = coefs[layer]            # (10, 768)
    sigma = scaler_scale[layer]     # (768,)
    # Avoid divide-by-zero if any dim had zero variance (shouldn't, but
    # be defensive).
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = w_std / sigma_safe[None, :]   # (10, 768) — directions in raw space.

    # Orthonormal basis for the span of w_raw via SVD.
    U, S, Vh = np.linalg.svd(w_raw, full_matrices=False)
    if S.size == 0:
        raise SystemExit("probe coefficient matrix is empty.")
    threshold = S.max() * 1e-6
    keep = S > threshold
    basis_rows = Vh[keep]              # (k, 768) — rows orthonormal.
    k = basis_rows.shape[0]
    print(f"noetic subspace rank: {k}")

    # Projection matrix onto the subspace.
    P = basis_rows.T @ basis_rows      # (768, 768) — symmetric idempotent.

    # ------------------------------------------------------------------ #
    # Check 1: probe-self-ablation sanity gate.
    # ------------------------------------------------------------------ #
    # Take the captured layer-3 raw activations, ablate, re-run the
    # same trained probe (sklearn-style: standardize then linear, no
    # re-fitting). Probe accuracy should collapse.
    h_raw = X[:, layer, :]               # (N, 768)
    h_ablated_raw = h_raw - h_raw @ P    # (N, 768)
    mu = scaler_mean[layer]              # (768,)
    h_std = (h_raw - mu) / sigma_safe
    h_ablated_std = (h_ablated_raw - mu) / sigma_safe

    # Apply the trained probe manually (so we don't depend on having
    # an sklearn classifier object).
    def logits(h_std_input: "np.ndarray") -> "np.ndarray":
        # (N, 768) @ (768, 10) + (10,) -> (N, 10)
        return h_std_input @ w_std.T + intercepts[layer][None, :]

    preds_unablated = np.argmax(logits(h_std), axis=1)
    preds_ablated = np.argmax(logits(h_ablated_std), axis=1)
    y_test = y[idx_test]
    acc_unablated_test = float(accuracy_score(y_test, preds_unablated[idx_test]))
    acc_ablated_test = float(accuracy_score(y_test, preds_ablated[idx_test]))

    print()
    print("Check 1 — probe-self-ablation sanity gate (test set, n="
          f"{len(idx_test)}):")
    print(f"  unablated probe accuracy: {acc_unablated_test:.3f}")
    print(f"  ablated   probe accuracy: {acc_ablated_test:.3f}")
    # The probe was trained to read this exact subspace, so ablation
    # should drive accuracy AT LEAST toward majority-class (~0.13).
    sanity_pass = acc_ablated_test <= 0.20
    print(f"  sanity pass (ablated <= 0.20): {sanity_pass}")
    if not sanity_pass:
        print("  WARNING: ablation did not drop the probe to near chance.")
        print("  Stage 3 results below are invalid until this is fixed.")

    # ------------------------------------------------------------------ #
    # Check 2: next-token causal effect on Pythia-160M.
    # ------------------------------------------------------------------ #
    print()
    print(f"loading {_MODEL_NAME} for forward-pass ablation ...")
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME)
    model.eval()
    device = torch.device("cpu")
    model.to(device)

    # Pre-build a torch tensor of the projection matrix on the model's device.
    P_t = torch.tensor(P, dtype=torch.float32, device=device)

    # Hook on transformer block _HOOK_BLOCK_INDEX's output.
    # GPTNeoXLayer's forward returns a tuple where the first element is
    # the residual stream tensor of shape (batch, seq, hidden).
    block = model.gpt_neox.layers[_HOOK_BLOCK_INDEX]

    def make_ablate_hook() -> Any:
        def hook(_module, _input, output):
            if isinstance(output, tuple):
                hs = output[0]
                # h_ablated = h - h @ P
                hs_ablated = hs - hs @ P_t.to(hs.dtype)
                return (hs_ablated,) + output[1:]
            else:
                return output - output @ P_t.to(output.dtype)
        return hook

    # ------------------------------------------------------------------ #
    # For each test-set prompt: baseline top-1 next token vs ablated
    # top-1 next token. Match rate is the causal-effect summary.
    # ------------------------------------------------------------------ #
    sample_id_list = [str(s) for s in sample_ids]
    per_record: list[dict[str, Any]] = []
    started = time.perf_counter()

    with torch.no_grad():
        for i, test_idx in enumerate(idx_test.tolist()):
            sid = sample_id_list[test_idx]
            text = labels[sid]
            true_y = int(y[test_idx])

            encoded = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=256,
            ).to(device)

            # Baseline pass.
            baseline_out = model(**encoded)
            baseline_logits = baseline_out.logits[0, -1, :]
            baseline_top1 = int(torch.argmax(baseline_logits).item())

            # Ablated pass.
            handle = block.register_forward_hook(make_ablate_hook())
            try:
                ablated_out = model(**encoded)
            finally:
                handle.remove()
            ablated_logits = ablated_out.logits[0, -1, :]
            ablated_top1 = int(torch.argmax(ablated_logits).item())

            # Distance between full logit vectors (after softmax) — a
            # finer-grained causal-effect signal than top-1 match alone.
            # Compute in float64 with explicit clamping so subnormal
            # probabilities at the tail of the softmax cannot produce
            # NaN via 0 * log(0).
            baseline_probs = torch.softmax(baseline_logits.double(), dim=-1)
            ablated_probs = torch.softmax(ablated_logits.double(), dim=-1)
            eps = 1e-30
            kl_b_a = float(torch.sum(
                baseline_probs.clamp_min(eps)
                * (torch.log(baseline_probs.clamp_min(eps))
                   - torch.log(ablated_probs.clamp_min(eps)))
            ).item())

            per_record.append({
                "sample_id": sid,
                "true_y": true_y,
                "baseline_top1_token_id": baseline_top1,
                "ablated_top1_token_id": ablated_top1,
                "match": baseline_top1 == ablated_top1,
                "baseline_top1_token_str": tokenizer.decode([baseline_top1]),
                "ablated_top1_token_str": tokenizer.decode([ablated_top1]),
                "kl_baseline_to_ablated": kl_b_a,
            })

            if (i + 1) % 20 == 0 or i == len(idx_test) - 1:
                elapsed = time.perf_counter() - started
                print(
                    f"  [{i + 1}/{len(idx_test)}] elapsed={elapsed:.1f}s"
                )

    # ------------------------------------------------------------------ #
    # Aggregate.
    # ------------------------------------------------------------------ #
    n_records = len(per_record)
    n_match = sum(1 for r in per_record if r["match"])
    match_rate = float(n_match) / max(1, n_records)
    kl_values = [r["kl_baseline_to_ablated"] for r in per_record]
    kl_mean = float(sum(kl_values) / max(1, len(kl_values)))
    kl_median = float(sorted(kl_values)[len(kl_values) // 2])

    print()
    print("Check 2 — next-token causal effect on Pythia-160M:")
    print(f"  test records: {n_records}")
    print(f"  baseline_top1 == ablated_top1: {n_match} / {n_records}"
          f"  ({match_rate:.3f})")
    print(f"  KL(baseline || ablated) mean:   {kl_mean:.4f}")
    print(f"  KL(baseline || ablated) median: {kl_median:.4f}")

    # ------------------------------------------------------------------ #
    # Verdict — narrow Stage 3 framing.
    # ------------------------------------------------------------------ #
    if not sanity_pass:
        verdict = "ABLATION_INVALID_SANITY_GATE_FAILED"
        verdict_text = (
            "Probe-self-ablation gate did not drop probe accuracy on the "
            "ablated activations sufficiently. The ablation did not remove "
            "what the probe reads. Stage 3 next-token results are not "
            "interpretable until the ablation construction is fixed."
        )
    elif match_rate >= 0.95:
        verdict = "ABLATION_NO_CAUSAL_BITE"
        verdict_text = (
            "Probe-self-ablation confirms the probe's signal was removed "
            "from layer-3 activations, but Pythia's next-token argmax "
            "matches the baseline on >= 95% of test prompts. The noetic "
            "subspace at layer 3 carries readable information but does "
            "not drive next-token behaviour on this corpus. Consistent "
            "with the Stage 2.2 finding that the +1.4 pp probe lift over "
            "TF-IDF is lexical decoration, not mechanistic encoding."
        )
    elif match_rate >= 0.70:
        verdict = "ABLATION_PARTIAL_CAUSAL_EFFECT"
        verdict_text = (
            "Probe sanity gate passes and ablation changes Pythia's "
            "next-token argmax on a measurable minority of test prompts. "
            "Some causal influence exists but is not dominant. Larger "
            "study (more samples, more axes, longer continuations) "
            "required before any mechanistic claim."
        )
    else:
        verdict = "ABLATION_STRONG_CAUSAL_EFFECT"
        verdict_text = (
            "Probe sanity gate passes and ablation changes Pythia's "
            "next-token argmax on a majority of test prompts. The noetic "
            "subspace at layer 3 has measurable causal influence on "
            "output behaviour. Exploratory only — no public Glass House "
            "claims off this single experiment; cross-axis and cross-"
            "model replication required."
        )

    print()
    print(f"VERDICT: {verdict}")
    print(verdict_text)

    report = {
        "schema_version": "pythia_ablation_layer3_report.v1",
        "experiment": (
            "Stage 3 — causal ablation of layer-3 noetic subspace on "
            "Pythia-160M"
        ),
        "model_name": _MODEL_NAME,
        "target_layer_index": _TARGET_LAYER_INDEX,
        "hook_block_index": _HOOK_BLOCK_INDEX,
        "activations_file": _ACTIVATIONS_PATH.name,
        "activations_sha256": activations_sha,
        "probes_file": _PROBES_PATH.name,
        "probes_sha256": probes_sha,
        "subspace_rank": int(k),
        "probe_self_ablation_sanity_gate": {
            "test_records": int(len(idx_test)),
            "probe_accuracy_unablated": acc_unablated_test,
            "probe_accuracy_ablated": acc_ablated_test,
            "pass_threshold": 0.20,
            "pass": bool(sanity_pass),
            "note": (
                "If pass=False, the ablation construction did not remove "
                "what the probe reads; Check 2 results below are not "
                "interpretable."
            ),
        },
        "next_token_causal_effect": {
            "test_records": int(n_records),
            "n_match": int(n_match),
            "match_rate": match_rate,
            "kl_baseline_to_ablated_mean": kl_mean,
            "kl_baseline_to_ablated_median": kl_median,
        },
        "decision_thresholds": {
            "no_causal_bite_match_rate_min": 0.95,
            "partial_causal_effect_match_rate_min": 0.70,
        },
        "per_record": per_record,
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
