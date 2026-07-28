"""TRACK_A_PHASE_A_IDENTIFIABILITY — implementation lock.

Phase A of PREREG_CJT_JSPACE_JOINED_NARROW_v1 (amendment 1, commit 17159fce).

THE QUESTION, and it is NOT the one Attempt 11 answered:
    Attempt 11 proved derivatives can be PRODUCED CORRECTLY.
    Phase A asks whether a registered output-causal direction is IDENTIFIABLE.

Plant a deliberately present output-causal signal, construct a direction from
CALIBRATION groups only, then require it to move the target logit margin on
UNTOUCHED groups while every frozen control stays bounded.

CRITICAL INDEPENDENCE CHECK: the direction must work on held-out groups. If it
only recovers the calibration examples it was built from, that is direction
FITTING, not direction IDENTIFIABILITY, and it fails closed.

FAIL-CLOSED: anything other than a clean pass emits
PHASE_A_FAIL_CLOSED_NO_CAS_INTERPRETATION and the CAS arm must not be run.

FIREWALL: this track may not read the TKS corpus, its labels, or its partitions.
Layer, hook, position and direction are chosen HERE and never from corpus labels.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
import transformers

HERE = Path(__file__).resolve().parent
MODEL = "EleutherAI/pythia-160m"

# ---- FROZEN PROTOCOL --------------------------------------------------------
LAYER = 6                 # frozen: middle layer, floor(12/2)
POSITION = -1             # frozen: last token
WRONG_LAYER = 2           # control
WRONG_POSITION = 0        # control
ALPHA = 4.0               # frozen intervention dose
SEEDS = [0, 1, 2, 3, 4]
PASS_MARGIN = 0.50        # registered direction must exceed the control envelope by this
# Target / distractor: exact single tokens, verified at runtime.
TARGET_WORD = " Paris"
DISTRACTOR_WORD = " London"

# Calibration and untouched groups are DISJOINT prompt families.
CALIB_PROMPTS = [
    "The capital of France is",
    "France's capital city is",
    "If you visit France, the capital you land in is",
    "Q: What is the capital of France? A:",
    "The French government sits in the capital,",
    "Everyone knows the capital of France is",
]
UNTOUCHED_PROMPTS = [                      # never used to build the direction
    "The seat of French national government is located in",
    "When travelling to France, tourists first reach the capital,",
    "Among European capitals, the French one is",
    "The Eiffel Tower stands in the French capital of",
    "Napoleon ruled France from its capital,",
    "The French capital, home to the Louvre, is",
]
# The contrast used to BUILD the direction: same syntactic frame, other country.
CALIB_CONTRAST = [p.replace("France", "England").replace("French", "English")
                  for p in CALIB_PROMPTS]


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def git_tree() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "UNAVAILABLE"


def hidden_at(model, tok, prompts, layer, position):
    out = []
    with torch.no_grad():
        for p in prompts:
            e = tok(p, return_tensors="pt")
            h = model(**e, output_hidden_states=True).hidden_states[layer][0]
            out.append(h[position].float().numpy())
    return np.vstack(out)


def margin_with_hook(model, tok, prompt, layer, position, vec, alpha, t_id, d_id):
    """Add alpha*vec at (layer, position); return target-minus-distractor logit margin."""
    handle = None
    if vec is not None and alpha != 0.0:
        v = torch.tensor(vec, dtype=torch.float32)

        def hook(_mod, _inp, output):
            hs = output[0] if isinstance(output, tuple) else output
            hs[:, position, :] = hs[:, position, :] + alpha * v.to(hs.dtype).to(hs.device)
            return (hs,) + output[1:] if isinstance(output, tuple) else hs
        handle = model.gpt_neox.layers[layer - 1].register_forward_hook(hook)
    try:
        with torch.no_grad():
            logits = model(**tok(prompt, return_tensors="pt")).logits[0, -1]
        return float(logits[t_id] - logits[d_id])
    finally:
        if handle is not None:
            handle.remove()


def main() -> int:
    tok = transformers.AutoTokenizer.from_pretrained(MODEL)
    model = transformers.AutoModelForCausalLM.from_pretrained(MODEL).eval()

    # ---- verify target and distractor resolve to EXACT single tokens
    t_ids, d_ids = tok(TARGET_WORD).input_ids, tok(DISTRACTOR_WORD).input_ids
    if len(t_ids) != 1 or len(d_ids) != 1:
        print(f"FAIL: target {t_ids} / distractor {d_ids} are not single tokens")
        print("VERDICT: PHASE_A_FAIL_CLOSED_NO_CAS_INTERPRETATION")
        return 1
    t_id, d_id = t_ids[0], d_ids[0]
    print(f"target {TARGET_WORD!r} -> {t_id}   distractor {DISTRACTOR_WORD!r} -> {d_id}")

    # ---- construct the registered direction from CALIBRATION GROUPS ONLY
    A = hidden_at(model, tok, CALIB_PROMPTS, LAYER, POSITION)
    B = hidden_at(model, tok, CALIB_CONTRAST, LAYER, POSITION)
    direction = (A.mean(0) - B.mean(0))
    direction = direction / (np.linalg.norm(direction) + 1e-12)

    rng = np.random.default_rng(20260727)

    def orthogonalize(v):
        v = v - direction * float(v @ direction)
        return v / (np.linalg.norm(v) + 1e-12)

    # sham direction: same construction on SHUFFLED group assignment
    pool = np.vstack([A, B])
    idx = rng.permutation(len(pool))
    sham = pool[idx[:len(A)]].mean(0) - pool[idx[len(A):]].mean(0)
    sham = sham / (np.linalg.norm(sham) + 1e-12)

    arms = {}
    for seed in SEEDS:
        r = np.random.default_rng(seed)
        rand = r.normal(size=direction.shape)
        rand = rand / (np.linalg.norm(rand) + 1e-12)
        conds = {
            "registered": (direction, LAYER, POSITION, +ALPHA),
            "wrong_sign": (direction, LAYER, POSITION, -ALPHA),
            "random": (rand, LAYER, POSITION, +ALPHA),
            "orthogonal": (orthogonalize(rand), LAYER, POSITION, +ALPHA),
            "wrong_layer": (direction, WRONG_LAYER, POSITION, +ALPHA),
            "wrong_token": (direction, LAYER, WRONG_POSITION, +ALPHA),
            "sham": (sham, LAYER, POSITION, +ALPHA),
        }
        for name, (vec, lay, pos, al) in conds.items():
            deltas = []
            for p in UNTOUCHED_PROMPTS:                    # UNTOUCHED groups only
                base = margin_with_hook(model, tok, p, lay, pos, None, 0.0, t_id, d_id)
                got = margin_with_hook(model, tok, p, lay, pos, vec, al, t_id, d_id)
                deltas.append(got - base)
            arms.setdefault(name, []).extend(deltas)

    stats = {k: {"mean": float(np.mean(v)), "sd": float(np.std(v)), "n": len(v),
                 "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]}
             for k, v in arms.items()}

    # ---- independence check: the direction must ALSO work where it was built,
    # but the PASS is decided on UNTOUCHED groups only (computed above).
    calib_deltas = []
    for p in CALIB_PROMPTS:
        base = margin_with_hook(model, tok, p, LAYER, POSITION, None, 0.0, t_id, d_id)
        got = margin_with_hook(model, tok, p, LAYER, POSITION, direction, ALPHA, t_id, d_id)
        calib_deltas.append(got - base)
    calib_mean = float(np.mean(calib_deltas))

    reg = stats["registered"]["mean"]
    control_env = max(abs(stats[k]["mean"]) for k in
                      ("random", "orthogonal", "wrong_layer", "wrong_token", "sham"))
    generalizes = bool(reg > 0 and abs(reg) >= 0.5 * abs(calib_mean))
    passed = bool(reg - control_env >= PASS_MARGIN
                  and stats["wrong_sign"]["mean"] < reg
                  and generalizes)

    print(f"\n  calibration-group effect (diagnostic only) = {calib_mean:+.4f}")
    for k in ("registered", "wrong_sign", "random", "orthogonal",
              "wrong_layer", "wrong_token", "sham"):
        s = stats[k]
        print(f"  {k:12s} delta={s['mean']:+.4f}  sd={s['sd']:.4f}  "
              f"CI[{s['ci95'][0]:+.4f},{s['ci95'][1]:+.4f}]")
    print(f"\n  control envelope (max |mean| over controls) = {control_env:.4f}")
    print(f"  registered - envelope = {reg - control_env:+.4f}   bar {PASS_MARGIN}")
    print(f"  generalizes to untouched groups = {generalizes}")

    verdict = "PHASE_A_IDENTIFIABILITY_PASS" if passed else \
              "PHASE_A_FAIL_CLOSED_NO_CAS_INTERPRETATION"
    print(f"\nVERDICT: {verdict}")
    if not passed:
        print("  -> the CAS interpretation arm MUST NOT be run.")

    receipt = {
        "track": "TRACK_A_PHASE_A_IDENTIFIABILITY",
        "prereg": "PREREG_CJT_JSPACE_JOINED_NARROW_v1.md amendment 1 (17159fce)",
        "protocol_hash": sha(json.dumps({
            "LAYER": LAYER, "POSITION": POSITION, "ALPHA": ALPHA, "SEEDS": SEEDS,
            "PASS_MARGIN": PASS_MARGIN, "TARGET": TARGET_WORD, "DISTRACTOR": DISTRACTOR_WORD,
            "CALIB": CALIB_PROMPTS, "UNTOUCHED": UNTOUCHED_PROMPTS}, sort_keys=True)),
        "code_commit": git_tree(),
        "model": MODEL, "tokenizer_identity": tok.__class__.__name__,
        "transformers": transformers.__version__, "torch": torch.__version__,
        "python": platform.python_version(),
        "target_token_id": int(t_id), "distractor_token_id": int(d_id),
        "layer": LAYER, "hook": "gpt_neox.layers[LAYER-1] forward_hook", "position": POSITION,
        "direction_construction": "mean(calibration hidden) - mean(frame-matched contrast), L2-normalised",
        "calibration_groups": CALIB_PROMPTS, "untouched_groups": UNTOUCHED_PROMPTS,
        "firewall": "no TKS corpus text, labels or partitions were read by this track",
        "seed_list": SEEDS,
        "calibration_effect_diagnostic_only": calib_mean,
        "target_logit_margin_effects": stats,
        "control_envelope": control_env,
        "generalizes_to_untouched": generalizes,
        "pass_threshold": PASS_MARGIN, "verdict": verdict,
    }
    (HERE / "phase_a_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True),
                                               encoding="utf-8")
    print("WROTE phase_a_receipt.json")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
