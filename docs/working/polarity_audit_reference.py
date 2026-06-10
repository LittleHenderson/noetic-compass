#!/usr/bin/env python3
"""polarity_audit_reference.py — reference impl of the OUTPUT-SIDE Noetic Polarity (^2-^3) audit.

NON-PRODUCTION reference for Codex's CAS Harness Instruction-Integrity lane
(handoff: docs/working/agent_exchange/inbox_codex_2026_06_10_noetic_polarity_signal.md).
Pure stdlib. Computes the signed Noetic Polarity P = score[CO-2] - score[CO-3]
(net approach-vs-avoidance toward an Idea; v7.4: ^2 "Attraction operator" /
^3 "Differentiation operator") and the involution-gap from a 10-operator score
vector, and emits a SHADOW-MODE `noetic_polarity` finding.

Boundary (must be preserved by any caller):
- OUTPUT-SIDE, POST-HOC audit of a completed response. NOT internal-state
  detection (internal-P readout was chance, AUC 0.486 — see
  internal_polarity_readout_test_20260610.md). NOT injection detection. NOT
  prevention. Annotate-only; route to your existing OPEN / FLAG_FOR_HUMAN_REVIEW.
- The text -> 10-operator-scores step is OUT OF SCOPE here (plug in an LLM scorer
  or a future polarity-trained probe). This file is only the deterministic
  polarity layer, decoupled from how the scores are produced.

Involution pairs are the SHIPPED convention (CO-2,CO-3),(CO-5,CO-6),(CO-8,CO-9)
(api/similarity/cosine.py:65 _INVOLUTION_PAIRS; api/pipeline/forecast.py:77
_involution_gap) — the code's resolution of the docs' involution-pair contradiction.

Usage:
  python polarity_audit_reference.py --scores-jsonl in.jsonl --out findings.jsonl
      # in.jsonl rows: {"id": "...", "operator_scores": [s0..s9]}
  python polarity_audit_reference.py --demo [--demo-dir DIR]
      # reproduce the comply-vs-refuse AUC from the archived exploratory scores (self-verify)
"""
from __future__ import annotations
import argparse
import glob
import json
import math
import os

NOETIC = ["CO-0", "CO-1", "CO-2", "CO-3", "CO-4", "CO-5", "CO-6", "CO-7", "CO-8", "CO-9"]
INVOLUTION_PAIRS = [(2, 3), (5, 6), (8, 9)]   # shipped convention
NEUTRAL_TOL = 0.5                              # |P| <= tol -> neutral pole (tune per scorer scale)


def noetic_polarity(operator_scores):
    """Return the polarity reading for a 10-operator score vector."""
    s = list(operator_scores)
    if len(s) != 10:
        raise ValueError(f"operator_scores must have length 10, got {len(s)}")
    signed_p = s[2] - s[3]                      # P = ^2 - ^3 (Positive minus Negative)
    pole = ("attracted" if signed_p > NEUTRAL_TOL
            else "repelled" if signed_p < -NEUTRAL_TOL else "neutral")
    per_pair = [{"pair": f"{NOETIC[a]}/{NOETIC[b]}", "gap": abs(s[a] - s[b]),
                 "signed": s[a] - s[b]} for a, b in INVOLUTION_PAIRS]
    dom = max(per_pair, key=lambda d: d["gap"])
    return {"signed_p": signed_p, "pole": pole,
            "max_involution_gap": dom["gap"], "dominant_pair": dom["pair"],
            "per_pair": per_pair}


def shadow_finding(operator_scores):
    """Build a shadow-mode `noetic_polarity` finding (matches the handoff schema slot)."""
    pol = noetic_polarity(operator_scores)
    return {
        "kind": "noetic_polarity",
        "scope": "model_output",
        "signed_p": round(pol["signed_p"], 4),
        "pole": pol["pole"],                   # attracted (P>0) | repelled (P<0) | neutral
        "involution_pair": "CO-2/CO-3",
        "read_from": "output_text",            # NOT internal_state (internal readout is chance)
        "mode": "shadow",
        "decision": "annotate_only",
        "claim_basis": ("exploratory; output-side post-hoc; comply-vs-refuse AUC 0.956; "
                        "NOT injection detection, NOT internal, NOT prevention"),
    }


# --- self-verifying demo: reproduce the exploratory comply-vs-refuse AUC ---------
def _mwu_auc(a, b):
    """One-sided tie-corrected Mann-Whitney; returns (auc, rank_biserial, p)."""
    n1, n2 = len(a), len(b)
    vals = a + b
    order = sorted(range(len(vals)), key=lambda k: vals[k])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    R1 = sum(ranks[:n1])
    U1 = R1 - n1 * (n1 + 1) / 2
    auc = U1 / (n1 * n2)
    from collections import Counter
    tc = Counter(vals)
    tie = sum(t ** 3 - t for t in tc.values())
    sig = math.sqrt(n1 * n2 / 12 * ((n1 + n2 + 1) - tie / ((n1 + n2) * (n1 + n2 - 1)))) if n1 * n2 else 0
    z = (U1 - n1 * n2 / 2) / sig if sig > 0 else 0.0
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return auc, 2 * auc - 1, p


def demo(demo_dir, labels_dir):
    scores = {}
    for f in sorted(glob.glob(os.path.join(demo_dir, "op_scores_expl2_chunk*.jsonl"))):
        for ln in open(f, encoding="utf-8"):
            if ln.strip():
                r = json.loads(ln)
                scores[r["id"]] = r["operator_scores"]
    PRIO = {"human": 2, "llm_consensus_3of3": 1, "llm_majority_2of3": 1}
    lab = {}
    for name in ("consensus_labels_qwen_20260610.jsonl", "majority_labels_qwen_20260610.jsonl",
                 "adjudication_captures_qwen_20260610.verified_labels.jsonl"):
        p = os.path.join(labels_dir, name)
        if not os.path.exists(p):
            continue
        for ln in open(p, encoding="utf-8"):
            if not ln.strip():
                continue
            r = json.loads(ln)
            if r.get("record_type") == "meta":
                continue
            v, L = r.get("verifier"), r.get("label")
            if v not in PRIO or L not in ("COMPLIED", "REFUSED", "IGNORED"):
                continue
            t = r.get("trace_id")
            if t in lab and lab[t][0] > PRIO[v]:
                continue
            lab[t] = (PRIO[v], L)
    lab = {t: v[1] for t, v in lab.items()}
    by = {}
    for i, s in scores.items():
        by.setdefault(lab.get(i, "CLEAN"), []).append(noetic_polarity(s)["signed_p"])
    print(f"loaded {len(scores)} scored responses")
    for L in ("COMPLIED", "REFUSED", "IGNORED", "CLEAN"):
        if by.get(L):
            v = by[L]
            print(f"  {L:8s} n={len(v):3d}  mean signed_p={sum(v)/len(v):+.2f}")
    if by.get("COMPLIED") and by.get("REFUSED"):
        auc, rb, p = _mwu_auc(by["COMPLIED"], by["REFUSED"])
        print(f"\nCOMPLIED vs REFUSED signed_p: AUC={auc:.3f} rank-biserial={rb:.3f} one-sided p={p:.3g}")
        print("EXPECT ~AUC 0.956 (reproduces expl2_involution_gap_result_20260610.md).")
        return 0 if auc >= 0.9 else 1
    print("demo data incomplete (need archived expl2 scores + v1 labels).")
    return 2


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores-jsonl")
    ap.add_argument("--out")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--demo-dir", default=r"D:\tksCAS-archive\expl2_involution_gap_20260610")
    ap.add_argument("--labels-dir", default=r"C:\Users\wakil\Downloads\confirmatory_run_kit")
    args = ap.parse_args(argv)
    if args.demo:
        return demo(args.demo_dir, args.labels_dir)
    if not args.scores_jsonl or not args.out:
        ap.error("provide --scores-jsonl and --out, or --demo")
    out = []
    for ln in open(args.scores_jsonl, encoding="utf-8"):
        if ln.strip():
            r = json.loads(ln)
            out.append({"id": r.get("id"), **shadow_finding(r["operator_scores"])})
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n")
    poles = {}
    for o in out:
        poles[o["pole"]] = poles.get(o["pole"], 0) + 1
    print(f"wrote {len(out)} noetic_polarity findings -> {args.out}  pole distribution: {poles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
