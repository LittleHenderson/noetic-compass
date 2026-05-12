"""Broader B3 eval runner — applies the 7 locked gate criteria.

Per user 2026-05-12 design (`docs/working/simplex_mvp_b3_broader_eval_design_2026_05_12.md`).

Loads two checkpoints (B3 + B2) and the frozen 24-record eval pack, runs
each model through:
  - decode_canary_pack with hard_typed_emission=True   (B3 "hard_full" mode)
  - decode_canary_pack with hard_typed_emission=False  (B3 "full" mode)
  - teacher_forced_canary_pack                          (B3 TF analysis)
  - decode_canary_pack(full) on B2                      (criterion 7 baseline)

Computes the seven locked criteria, reported with rpm_chain split into
canonical_order vs prefix_variety_stress buckets so struggles on stress
records don't blur the canonical result.

Writes:
  - <output_dir>/broader_b3_eval_report.json    (machine-readable, full per-record)
  - <output_dir>/broader_b3_eval_findings.md    (human-readable pass/fail per criterion)

Usage:
  python broader_b3_eval_runner.py \\
    --b3-checkpoint /workspace/tksCAS/stage7_candidate_b3_full_hardemit_.../ckpt_final.pt \\
    --b2-checkpoint /workspace/tksCAS/stage7_candidate_b2_lmfr_slot_.../ckpt_final.pt \\
    --eval-pack /workspace/tksCAS/cas-synthetic/data/eval/broader_b3_eval_pack_2026_05_12.jsonl \\
    --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \\
    --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \\
    --output-dir /workspace/tksCAS/broader_b3_eval_<TS>/ \\
    --device cuda:0
"""
from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path
from typing import Any

import torch


_THIS_FILE = Path(__file__).resolve()
_CAS_NATIVE = _THIS_FILE.parent.parent
_PROJECT_ROOT = _CAS_NATIVE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__file__ = str(_CAS_NATIVE / "__init__.py")
    pkg.__path__ = [str(_CAS_NATIVE)]
    sys.modules["cas_native"] = pkg


# ---------------------------------------------------------------------------
# Per-record canonical identifier recovery
# ---------------------------------------------------------------------------

def per_record_recovery(record: dict[str, Any],
                         generated_text: str) -> dict[str, Any]:
    """For an rpm_chain record, count canonical identifiers exact-matched
    in the generated text. Returns a dict with the counts + per-ident hits.

    Non-rpm records get an empty result (recovery is not meaningful).
    """
    meta = record.get("eval_meta", {})
    idents: list[str] = meta.get("canonical_identifiers", []) or []
    if not idents:
        return {"applicable": False, "n_target": 0, "n_recovered": 0,
                "recovery_rate": None, "per_ident_hits": {}}
    hits = {}
    n_recovered = 0
    for ident in idents:
        present = ident in generated_text
        hits[ident] = present
        if present:
            n_recovered += 1
    return {
        "applicable": True,
        "n_target": len(idents),
        "n_recovered": n_recovered,
        "recovery_rate": n_recovered / len(idents),
        "per_ident_hits": hits,
    }


# ---------------------------------------------------------------------------
# Helpers — longest-run, slot stats
# ---------------------------------------------------------------------------

def longest_run(trace: list[int], target: int) -> int:
    cur = best = 0
    for s in trace:
        if s == target:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


# ---------------------------------------------------------------------------
# Main pipeline — load checkpoints, run decode/TF, compute gates
# ---------------------------------------------------------------------------

def build_model_and_load(cfg_template: Any, vocab_size: int,
                          checkpoint_path: str, device: torch.device) -> Any:
    """Build the simplex MVP model and warm-load a checkpoint."""
    from cas_native.training.train_simplex_mvp import (
        build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
    )
    from cas_native.training.simplex_checkpoint import load_checkpoint
    cfg = SimplexTrainConfig(
        data_path="", output_dir="",
        d_model=384, encoder_n_layers=4, decoder_n_layers=6,
        encoder_n_heads=6, decoder_n_heads=6, batch_size=1,
    )
    cfg.loss_weights = dict(DEFAULT_LOSS_WEIGHTS)
    model = build_simplex_mvp_model(
        cfg, vocab_size=vocab_size, vocab_size_english=vocab_size,
    )
    load_checkpoint(
        checkpoint_path, model=model, optimizer=None,
        map_location="cpu", strict=True, restore_rng=False,
    )
    model = model.to(device)
    model.eval()
    return model


def run_decode(model, records, collator, tokenizer, *,
               device, hard_typed_emission: bool,
               max_new_tokens: int = 128) -> list[dict[str, Any]]:
    """Wrap decode_canary_pack; returns per-record entries."""
    from cas_native.evaluation.sample_decoder import decode_canary_pack
    return decode_canary_pack(
        model, records, collator, tokenizer,
        device=device, max_new_tokens=max_new_tokens,
        hard_typed_emission=hard_typed_emission,
        copy_confidence_threshold=0.5,
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--b3-checkpoint", required=True)
    p.add_argument("--b2-checkpoint", required=True)
    p.add_argument("--eval-pack", required=True)
    p.add_argument("--tokenizer-path", required=True)
    p.add_argument("--english-bpe-path", default="")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--max-new-tokens", type=int, default=128)
    args = p.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    print(json.dumps({"event": "eval_start"}), flush=True)

    # ---- Load eval pack -----------------------------------------------
    records: list[dict[str, Any]] = []
    with open(args.eval_pack, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(json.dumps({"event": "eval_pack_loaded",
                      "n_records": len(records)}), flush=True)

    rpm_records = [r for r in records if r["v1mix_grammar_category_or_error_class"] == "rpm_chain"]
    non_rpm_records = [r for r in records if r["v1mix_grammar_category_or_error_class"] != "rpm_chain"]

    # ---- Tokenizer ---------------------------------------------------
    from cas_native.training.tokenizer import HybridCASTokenizer
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    tokenizer = HybridCASTokenizer.load(args.tokenizer_path)
    if args.english_bpe_path:
        tokenizer = tokenizer.with_english_bpe(args.english_bpe_path)
    vocab_size = int(tokenizer.vocab_size)
    collator = SimplexCollator(tokenizer, enable_simplex_aux=True)
    print(json.dumps({"event": "tokenizer_loaded",
                      "vocab_size": vocab_size}), flush=True)

    # ---- B3 model ----------------------------------------------------
    print(json.dumps({"event": "loading_b3"}), flush=True)
    model_b3 = build_model_and_load(None, vocab_size, args.b3_checkpoint, device)

    # ---- B3 decode: full + hard_full --------------------------------
    print(json.dumps({"event": "b3_decode_full"}), flush=True)
    b3_full = run_decode(model_b3, records, collator, tokenizer,
                          device=device, hard_typed_emission=False,
                          max_new_tokens=args.max_new_tokens)
    print(json.dumps({"event": "b3_decode_hard_full"}), flush=True)
    b3_hard = run_decode(model_b3, records, collator, tokenizer,
                          device=device, hard_typed_emission=True,
                          max_new_tokens=args.max_new_tokens)

    # ---- B3 TF analysis ----------------------------------------------
    print(json.dumps({"event": "b3_tf_analysis"}), flush=True)
    from cas_native.evaluation.teacher_forced_canary import (
        teacher_forced_canary_pack,
    )
    b3_tf = teacher_forced_canary_pack(model_b3, records, collator, tokenizer,
                                         device=device)

    # Free B3 GPU memory before loading B2
    del model_b3
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ---- B2 model + decode (full mode only — criterion 7 baseline) ---
    print(json.dumps({"event": "loading_b2"}), flush=True)
    model_b2 = build_model_and_load(None, vocab_size, args.b2_checkpoint, device)
    print(json.dumps({"event": "b2_decode_full"}), flush=True)
    b2_full = run_decode(model_b2, records, collator, tokenizer,
                          device=device, hard_typed_emission=False,
                          max_new_tokens=args.max_new_tokens)
    del model_b2
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ---- Damage analysis on each generation set ----------------------
    from cas_native.evaluation.damage_detector import (
        analyze_sample, aggregate_pack_verdict,
    )
    def damages_for(samples: list[dict[str, Any]]) -> tuple[list[Any], dict[str, Any]]:
        reports = [analyze_sample(s["generated_text"], s.get("target_text", ""))
                   for s in samples]
        return reports, aggregate_pack_verdict(reports)

    b3_full_dam, b3_full_pack = damages_for(b3_full)
    b3_hard_dam, b3_hard_pack = damages_for(b3_hard)
    b2_full_dam, b2_full_pack = damages_for(b2_full)

    # ---- Per-record assembly with bucket + recovery -----------------
    def build_per_record(samples, damages, model_label):
        result = []
        for s, dmg in zip(samples, damages):
            rid = s["id"]
            # Find source record for eval_meta
            src = next(r for r in records if r["id"] == rid)
            rec = {
                "id": rid,
                "model": model_label,
                "category": s["category"],
                "bucket": src.get("eval_meta", {}).get("bucket"),
                "target_text": s["target_text"],
                "generated_text": s["generated_text"],
                "n_tokens_generated": s["n_tokens_generated"],
                "text_len": len(s["generated_text"]),
                "hit_eos": s["hit_eos"],
                "slot_type_trace": s.get("slot_type_trace", []),
                "emission_route_counts": s.get("emission_route_counts",
                                                {"lm": 0, "copy": 0}),
                "damage_verdict": dmg.verdict,
                "damage_severity": dmg.severity_score,
                "damage_signatures": dmg.signatures,
                "recovery": per_record_recovery(src, s["generated_text"]),
                "longest_stage_var_run": longest_run(
                    s.get("slot_type_trace", []), 2
                ),
            }
            result.append(rec)
        return result

    b3_full_per = build_per_record(b3_full, b3_full_dam, "b3_full")
    b3_hard_per = build_per_record(b3_hard, b3_hard_dam, "b3_hard_full")
    b2_full_per = build_per_record(b2_full, b2_full_dam, "b2_full")

    # ---- Apply the 7 locked gate criteria ---------------------------
    rpm_canon = [r for r in b3_hard_per
                 if r["category"] == "rpm_chain"
                 and r["bucket"] == "canonical_order"]
    rpm_stress = [r for r in b3_hard_per
                  if r["category"] == "rpm_chain"
                  and r["bucket"] == "prefix_variety_stress"]
    non_rpm_hard = [r for r in b3_hard_per if r["category"] != "rpm_chain"]

    # Gate 1: rpm_chain canonical identifier exact-match recovery
    # First measured on canonical_order bucket separately; then on stress.
    def bucket_recovery(bucket: list[dict[str, Any]]) -> dict[str, Any]:
        n_target = sum(b["recovery"]["n_target"] for b in bucket)
        n_rec = sum(b["recovery"]["n_recovered"] for b in bucket)
        return {"n_target": n_target, "n_recovered": n_rec,
                "rate": n_rec / max(n_target, 1)}

    canon_recovery_hard = bucket_recovery(rpm_canon)
    stress_recovery_hard = bucket_recovery(rpm_stress)

    # full-mode comparison
    rpm_canon_full = [r for r in b3_full_per
                      if r["category"] == "rpm_chain"
                      and r["bucket"] == "canonical_order"]
    rpm_stress_full = [r for r in b3_full_per
                       if r["category"] == "rpm_chain"
                       and r["bucket"] == "prefix_variety_stress"]
    canon_recovery_full = bucket_recovery(rpm_canon_full)
    stress_recovery_full = bucket_recovery(rpm_stress_full)

    gate1_first_bar = canon_recovery_hard["rate"] >= 0.50
    gate1_strong = canon_recovery_hard["rate"] >= 0.70

    # Gate 2: hard_full identifier recovery > full identifier recovery
    # (use canonical bucket; the more rigorous metric is canonical, not stress)
    gate2 = canon_recovery_hard["n_recovered"] > canon_recovery_full["n_recovered"]

    # Gate 3: non-rpm emission_route_counts.copy = 0 on every non-rpm record
    non_rpm_copy_emissions = [
        (r["id"], r["emission_route_counts"].get("copy", 0))
        for r in non_rpm_hard
    ]
    gate3 = all(c == 0 for _, c in non_rpm_copy_emissions)

    # Gate 4: non-rpm sustained STAGE_VAR run >= 3 = leakage = fail
    non_rpm_stage_var_runs = [
        (r["id"], longest_run(r["slot_type_trace"], 2))
        for r in non_rpm_hard
    ]
    gate4 = all(run < 3 for _, run in non_rpm_stage_var_runs)

    # Gate 5: no trivial outputs - n_tokens >= 50 AND text_len >= 100
    trivial = [
        r["id"] for r in b3_hard_per
        if r["n_tokens_generated"] < 50 or r["text_len"] < 100
    ]
    gate5 = (len(trivial) == 0)

    # Gate 6: no catastrophic loop (count >= 5 non-function-word) and
    # no excessive truncation (>2/24 records)
    _function_words = {"a", "an", "the", "to", "of", "in", "and", "or",
                       "that", "is", "by", "with", "for", "on", "at",
                       "as", "it", "be", "are", "name"}
    catastrophic_loops = []
    truncations = []
    for r in b3_hard_per:
        loop = r["damage_signatures"].get("repeated_phrase_loop", {})
        if loop.get("found"):
            phrase = (loop.get("phrase") or "").strip().lower()
            count = loop.get("count", 0)
            if count >= 8:
                catastrophic_loops.append((r["id"], phrase, count))
            elif count >= 5 and phrase not in _function_words:
                catastrophic_loops.append((r["id"], phrase, count))
        trunc = r["damage_signatures"].get("truncation", {})
        if trunc.get("found"):
            truncations.append(r["id"])
    gate6 = (len(catastrophic_loops) == 0) and (len(truncations) <= 2)

    # Gate 7: B3 hard_full pack mean_severity <= B2 full pack mean_severity + 0.10
    b3_hard_pack_sev = b3_hard_pack.get("mean_severity", 0.0)
    b2_full_pack_sev = b2_full_pack.get("mean_severity", 0.0)
    gate7 = (b3_hard_pack_sev <= b2_full_pack_sev + 0.10)

    all_gates_pass = all([gate1_first_bar, gate2, gate3, gate4, gate5, gate6, gate7])

    # ---- Assemble report ---------------------------------------------
    report = {
        "schema_version": "broader_b3_eval.v1",
        "eval_pack": args.eval_pack,
        "b3_checkpoint": args.b3_checkpoint,
        "b2_checkpoint": args.b2_checkpoint,
        "n_records": len(records),
        "tf_analysis_b3": b3_tf.get("summary"),
        "pack_verdicts": {
            "b3_full": {
                "verdict": b3_full_pack["verdict"],
                "by_verdict": b3_full_pack["by_verdict"],
                "mean_severity": b3_full_pack.get("mean_severity"),
            },
            "b3_hard_full": {
                "verdict": b3_hard_pack["verdict"],
                "by_verdict": b3_hard_pack["by_verdict"],
                "mean_severity": b3_hard_pack.get("mean_severity"),
            },
            "b2_full": {
                "verdict": b2_full_pack["verdict"],
                "by_verdict": b2_full_pack["by_verdict"],
                "mean_severity": b2_full_pack.get("mean_severity"),
            },
        },
        "recovery_by_bucket": {
            "canonical_order_hard_full": canon_recovery_hard,
            "canonical_order_full": canon_recovery_full,
            "prefix_variety_stress_hard_full": stress_recovery_hard,
            "prefix_variety_stress_full": stress_recovery_full,
        },
        "non_rpm_copy_emissions": non_rpm_copy_emissions,
        "non_rpm_stage_var_runs": non_rpm_stage_var_runs,
        "trivial_outputs": trivial,
        "catastrophic_loops": catastrophic_loops,
        "truncations": truncations,
        "locked_gates": {
            "gate1_canonical_recovery_first_bar_50": gate1_first_bar,
            "gate1_canonical_recovery_strong_70": gate1_strong,
            "gate2_hard_full_beats_full_on_canonical": gate2,
            "gate3_no_non_rpm_copy_emissions": gate3,
            "gate4_no_non_rpm_stage_var_leakage": gate4,
            "gate5_no_trivial_outputs": gate5,
            "gate6_no_catastrophic_loops_or_excessive_truncations": gate6,
            "gate7_b3_severity_within_b2_baseline_plus_0.10": gate7,
        },
        "verdict": "validate" if all_gates_pass else "falsify",
        "per_record": {
            "b3_hard_full": b3_hard_per,
            "b3_full": b3_full_per,
            "b2_full": b2_full_per,
        },
    }

    report_path = out_dir / "broader_b3_eval_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # ---- Human-readable findings -------------------------------------
    findings_lines = [
        "# Broader B3 Eval — Findings",
        "",
        f"Verdict: **{report['verdict'].upper()}**",
        "",
        f"Eval pack: {args.eval_pack}",
        f"B3 ckpt:   {args.b3_checkpoint}",
        f"B2 ckpt:   {args.b2_checkpoint}",
        f"Records:   {len(records)} (15 rpm_chain + 9 non-rpm)",
        "",
        "## Locked gate results",
        "",
        f"| Gate | Pass | Detail |",
        f"|---|---|---|",
        f"| 1. Canonical recovery ≥ 50% (first bar) | {gate1_first_bar} | {canon_recovery_hard['n_recovered']}/{canon_recovery_hard['n_target']} = {canon_recovery_hard['rate']:.1%} |",
        f"| 1+. Canonical recovery ≥ 70% (strong)   | {gate1_strong} | same |",
        f"| 2. hard_full > full on canonical        | {gate2} | hard {canon_recovery_hard['n_recovered']} vs full {canon_recovery_full['n_recovered']} |",
        f"| 3. Non-rpm copy = 0                     | {gate3} | offenders: {[t for t in non_rpm_copy_emissions if t[1] > 0]} |",
        f"| 4. Non-rpm STAGE_VAR run < 3            | {gate4} | offenders: {[t for t in non_rpm_stage_var_runs if t[1] >= 3]} |",
        f"| 5. No trivial outputs                   | {gate5} | trivial ids: {trivial} |",
        f"| 6. No catastrophic loops / >2 truncations | {gate6} | loops: {catastrophic_loops} / truncations: {truncations} |",
        f"| 7. B3 sev ≤ B2 + 0.10                   | {gate7} | B3 {b3_hard_pack_sev:.3f} vs B2 {b2_full_pack_sev:.3f} (Δ {b3_hard_pack_sev - b2_full_pack_sev:+.3f}) |",
        "",
        "## Recovery by bucket",
        "",
        f"- canonical_order: hard_full {canon_recovery_hard['n_recovered']}/{canon_recovery_hard['n_target']} = {canon_recovery_hard['rate']:.1%}; full {canon_recovery_full['n_recovered']}/{canon_recovery_full['n_target']} = {canon_recovery_full['rate']:.1%}",
        f"- prefix_variety_stress: hard_full {stress_recovery_hard['n_recovered']}/{stress_recovery_hard['n_target']} = {stress_recovery_hard['rate']:.1%}; full {stress_recovery_full['n_recovered']}/{stress_recovery_full['n_target']} = {stress_recovery_full['rate']:.1%}",
        "",
        "## TF analysis (B3)",
        "",
        f"```json\n{json.dumps(report['tf_analysis_b3'], indent=2)}\n```",
        "",
        "## Per-record breakdown — see broader_b3_eval_report.json",
    ]
    findings_path = out_dir / "broader_b3_eval_findings.md"
    findings_path.write_text("\n".join(findings_lines), encoding="utf-8")

    print(json.dumps({
        "event": "eval_done",
        "verdict": report["verdict"],
        "gate_summary": report["locked_gates"],
        "report_path": str(report_path),
        "findings_path": str(findings_path),
    }, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
