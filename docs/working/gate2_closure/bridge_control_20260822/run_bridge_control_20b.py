# -*- coding: utf-8 -*-
"""Bridge stance-control run (frontier #16) — executes on the AWS GPU standby.

Compares, on the SAME frozen 80-case 40E fixture:
  none / CAS-readable (probe+gold) / CONTROL-readable (probe+gold) / CAS-raw prefixes,
against correct-vs-partner continuations, using the same likelihood machinery as the
original bridge (mean_logprob_continuation). Emits likelihood evidence only; no ACCEPT.

Preregistered in PREREG_BRIDGE_STANCE_CONTROL_20260822.md. Run ONLY on the pinned GPU
binding; records model revision + fixture sha256 in the output.
"""
import argparse, hashlib, json, math, pathlib, sys, datetime
import numpy as np

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from run_open_weight_eta_epsilon_bridge import mean_logprob_continuation  # noqa: E402
from run_open_weight_probe_shard import ProbeShardConfig, load_open_weight_model  # noqa: E402
from run_stage9_40e_eta_epsilon_bridge import base_prompt  # noqa: E402

CONDITIONS = ("none", "cas_probe", "ctrl_probe", "cas_gold", "ctrl_gold", "cas_raw")

def sign_test_p(n_pos: int, n: int) -> float:
    if n == 0:
        return 1.0
    p = sum(math.comb(n, k) for k in range(0, n + 1) if abs(2 * k - n) >= abs(2 * n_pos - n)) / (2.0 ** n)
    return float(p)

def summarize(xs):
    xs = [float(x) for x in xs]
    return {"mean": float(np.mean(xs)), "std": float(np.std(xs)), "n": len(xs)}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--model-id", default="EleutherAI/gpt-neox-20b")
    ap.add_argument("--model-revision", default=None)
    ap.add_argument("--output", required=True)
    ap.add_argument("--torch-dtype", default="float16")
    ap.add_argument("--device-map", default="auto")
    ap.add_argument("--max-length", type=int, default=256)
    args = ap.parse_args()

    fx = json.loads(pathlib.Path(args.fixture).read_text(encoding="utf-8"))
    cases = fx["cases"]
    cfg = ProbeShardConfig(
        model_id=args.model_id, worker_id="bridge-stance-control", audit_id="bridge-stance-control-20260822",
        job_id="manual-stage9-40e-control-equivalent", layer_start=0, layer_end=0,
        shard_id="stage9-40e-control", assigned_methods=("eta_epsilon_bridge",),
        expected_outputs=("eta_epsilon_likelihood_bridge",), result_path=args.output,
        model_revision=args.model_revision, torch_dtype=args.torch_dtype, device_map=args.device_map,
        max_scenarios=len(cases), max_length=args.max_length, trust_remote_code=False,
    )
    print("loading model (40GB, fp16)...", flush=True)
    lm, tokenizer, model_info = load_open_weight_model(cfg)
    print("model loaded:", model_info.get("parameter_count"), flush=True)

    margins = {c: [] for c in CONDITIONS}
    per_case = []
    for i, case in enumerate(cases, start=1):
        base = case["base_prompt"]
        row = {"scenario_id": case["scenario_id"], "conditions": {}}
        for cond in CONDITIONS:
            prefix = "" if cond == "none" else case["prefixes"][cond]
            prompt = prefix + base
            correct = mean_logprob_continuation(model=lm, tokenizer=tokenizer, prompt=prompt,
                                                continuation=case["correct_continuation"], max_length=args.max_length)
            partner = mean_logprob_continuation(model=lm, tokenizer=tokenizer, prompt=prompt,
                                                continuation=case["partner_continuation"], max_length=args.max_length)
            margin = correct["mean_logprob"] - partner["mean_logprob"]
            margins[cond].append(margin)
            row["conditions"][cond] = {"margin": margin, "correct_mean_logprob": correct["mean_logprob"],
                                       "partner_mean_logprob": partner["mean_logprob"], "n_tokens": correct["n_tokens"]}
        per_case.append(row)
        if i % 10 == 0:
            print(f"{i}/{len(cases)} done", flush=True)

    summaries = {}
    for cond in CONDITIONS:
        deltas = [m - b for m, b in zip(margins[cond], margins["none"])]
        n_pos = sum(1 for d in deltas if d > 0)
        summaries[cond] = {"margin": summarize(margins[cond]), "delta_vs_none": summarize(deltas),
                           "delta_positive_count": int(n_pos), "delta_positive_sign_p": sign_test_p(n_pos, len(deltas))}
    paired = [a - b for a, b in zip(margins["cas_probe"], margins["ctrl_probe"])]
    paired_delta = [a - b for a, b in zip(
        [c["conditions"]["cas_probe"]["margin"] for c in per_case],
        [c["conditions"]["ctrl_probe"]["margin"] for c in per_case])]
    n_cas_wins = sum(1 for d in paired_delta if d > 0)
    cas_minus_ctrl_mean = float(np.mean(paired_delta))

    C1 = summaries["ctrl_probe"]["delta_vs_none"]["mean"] > 0.0
    C2_pos = (cas_minus_ctrl_mean >= 0.10) and (sign_test_p(n_cas_wins, len(paired_delta)) <= 0.05)
    C2_neg = (cas_minus_ctrl_mean <= -0.10) and (sign_test_p(n_cas_wins, len(paired_delta)) <= 0.05)
    if C1 and C2_pos:
        verdict = "CAS_FRAMING_ADDS_BEYOND_CONTENT"
    elif C1 and C2_neg:
        verdict = "CAS_FRAMING_WORSE_THAN_PLAIN_NAMING"
    elif C1:
        verdict = "NO_DETECTABLE_FRAMING_ADVANTAGE"
    else:
        verdict = "CONTROL_ARM_INVALID_C1"

    out = {
        "schema": "bridge_stance_control_results.v1",
        "prereg": "PREREG_BRIDGE_STANCE_CONTROL_20260822.md",
        "fixture_sha256": hashlib.sha256(pathlib.Path(args.fixture).read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "model": {"model_id": args.model_id, "model_revision": args.model_revision, "model_info": model_info},
        "config": {"torch_dtype": args.torch_dtype, "device_map": args.device_map, "max_length": args.max_length},
        "summaries": summaries,
        "key_comparisons": {
            "cas_probe_delta_vs_none": round(summaries["cas_probe"]["delta_vs_none"]["mean"], 6),
            "ctrl_probe_delta_vs_none": round(summaries["ctrl_probe"]["delta_vs_none"]["mean"], 6),
            "cas_minus_ctrl_mean_delta": round(cas_minus_ctrl_mean, 6),
            "cas_wins_over_ctrl_count": int(n_cas_wins),
            "paired_sign_p": sign_test_p(n_cas_wins, len(paired_delta)),
            "cas_raw_delta_vs_none": round(summaries["cas_raw"]["delta_vs_none"]["mean"], 6),
            "may_2026_reference_probe_readable_delta": 1.412050,
        },
        "criteria": {"C1_ctrl_positive": bool(C1), "C2_pos": bool(C2_pos), "C2_neg": bool(C2_neg)},
        "verdict": verdict,
        "cases": per_case,
    }
    raw = json.dumps(out, indent=2, sort_keys=True).encode("utf-8")
    pathlib.Path(args.output).write_bytes(raw)
    print(json.dumps({k: out["key_comparisons"][k] for k in out["key_comparisons"]}, indent=2))
    print("verdict:", verdict)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
