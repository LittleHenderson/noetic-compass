"""Candidate E Stage 2 TF / source-swap evaluator (2026-05-12).

Reads the two Stage 1B artifacts produced by
``cas-synthetic/scripts/build_rpm_copy_grounding_v2.py``:

  --dev-path                  data/path_d/rpm_copy_grounding_v2_dev.jsonl
  --source-swap-dev-path      data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl

For each rpm_chain record in dev, decodes the reply (free-decode by default;
``--tf-mode`` enables teacher-forced) and scores **exact** canonical
identifier recovery in left-to-right position via the same bounded-regex
positional match used by ``broader_b3_eval_runner.per_record_recovery``.

For each source-swap PAIR in source-swap-dev (grouped by
``eval_meta.source_swap_pair_id``), decodes both members and scores:

  - per_member_recovery   — same metric as dev (does the member's output
                            contain the member's own canonical bodies in
                            the correct positions?)
  - cross_emission_count  — number of OTHER member's canonical bodies that
                            leaked into THIS member's output (must be zero
                            for true source-grounded binding; non-zero =
                            memorization signature)
  - pair_pass             — both members recovered fully AND zero cross-
                            emission in either direction

Outputs:
  <output_dir>/evaluate_candidate_e_stage2_report.json
  <output_dir>/evaluate_candidate_e_stage2_findings.md

The script does NOT gate-pass at Stage 2a (E2a is warmup; identifier
recovery is expected near 0 because copy is off). Gate thresholds become
load-bearing at Stage 2b after L_span / L_contrastive_margin / L_coverage
land. The report includes the metrics either way so E2b loss design can
be informed by E2a residuals.

Usage:
  python noetic-compass-scaffold/noetic-compass/cas-native/evaluation/\
      evaluate_candidate_e_stage2.py \\
    --checkpoint /workspace/tksCAS/runs/e2a_*/ckpt_final.pt \\
    --dev-path cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl \\
    --source-swap-dev-path \\
        cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl \\
    --tokenizer-path stage6_v6_artifacts/tokenizer.json \\
    --english-bpe-path stage6_v6_artifacts/english_bpe.json \\
    --output-dir /workspace/tksCAS/eval_candidate_e_stage2_<TS>/ \\
    --device cuda:0 \\
    --max-cas-prefix-len 192 \\
    --max-new-tokens 192
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import types
from pathlib import Path
from typing import Any

import torch


# Bounded-regex identifier shape — matches broader_b3_eval_runner exactly
# so the recovery scoring rule is consistent across evaluators.
_BOUNDED_IDENT_RE = re.compile(r"\bstage[ADWP]\d+_\d+_\d{3,5}\b")


def extract_identifiers_in_order(text: str) -> list[str]:
    return _BOUNDED_IDENT_RE.findall(text)


# ---- cas_native package import shim (standalone-script safe) -------------

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


# ---- Per-record scoring ---------------------------------------------------

def longest_stage_var_run(trace: list[int],
                          stage_var_slot_id: int = 2) -> int:
    """Length of the longest contiguous STAGE_VAR run in ``trace``.

    Mirrors broader_b3_eval_runner.longest_run; duplicated for evaluator
    self-containment. SLOT_STAGE_VAR = 2 in
    cas_native.training.datasets.simplex_collator.
    """
    cur = best = 0
    for s in trace:
        if s == stage_var_slot_id:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def stage_var_token_count(trace: list[int],
                          stage_var_slot_id: int = 2) -> int:
    """Total STAGE_VAR positions in the slot trace (sum across all spans)."""
    return sum(1 for s in trace if s == stage_var_slot_id)


def per_record_recovery(record: dict[str, Any],
                        generated_text: str) -> dict[str, Any]:
    """Score canonical identifier recovery via positional bounded-regex.

    Identical method to broader_b3_eval_runner.per_record_recovery — kept
    duplicated here so this evaluator imports cleanly without cycling
    through the broader_b3 runner's heavier dependencies.
    """
    meta = record.get("eval_meta", {})
    targets: list[str] = meta.get("canonical_identifiers", []) or []
    if not targets:
        return {
            "applicable": False, "n_target": 0, "n_recovered": 0,
            "recovery_rate": None, "per_ident_hits": {},
            "generated_identifiers": [],
        }
    gen_idents = extract_identifiers_in_order(generated_text)
    hits: dict[str, bool] = {}
    n_recovered = 0
    for k, target_ident in enumerate(targets):
        if k < len(gen_idents) and gen_idents[k] == target_ident:
            hits[target_ident] = True
            n_recovered += 1
        else:
            hits[target_ident] = False
    return {
        "applicable": True,
        "n_target": len(targets),
        "n_recovered": n_recovered,
        "recovery_rate": n_recovered / len(targets),
        "per_ident_hits": hits,
        "generated_identifiers": gen_idents,
    }


def pair_cross_emission(member: dict[str, Any], other: dict[str, Any],
                        member_gen_text: str) -> int:
    """Count occurrences of `other`'s canonical-body bodies in `member`'s
    generated text. Non-zero = memorization signature (the model emitted
    the OTHER source's identifiers despite seeing THIS source).
    """
    other_meta = other.get("eval_meta", {})
    other_targets: list[str] = other_meta.get("canonical_identifiers", []) or []
    if not other_targets:
        return 0
    # The bodies that legitimately appear in `member` are member's own
    # canonical bodies + the SHARED distractor bodies. The "other" member's
    # canonical bodies are what we want to flag as cross-emission.
    member_meta = member.get("eval_meta", {})
    member_canonical_set = set(member_meta.get("canonical_identifiers", []) or [])
    # Bodies of the other-member-canonical identifiers, that are NOT also
    # member-canonical (cf groups have identical prefix-middle so we have
    # to compare full identifier strings).
    foreign = [t for t in other_targets if t not in member_canonical_set]
    if not foreign:
        return 0
    count = 0
    for f in foreign:
        # word-bounded count to avoid false positives on shared prefixes
        pattern = r"\b" + re.escape(f) + r"\b"
        count += len(re.findall(pattern, member_gen_text))
    return count


# ---- Checkpoint load + decode --------------------------------------------

def build_model_and_load(vocab_size: int, checkpoint_path: str,
                         device: torch.device,
                         max_cas_prefix_len: int) -> Any:
    from cas_native.training.train_simplex_mvp import (
        build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
    )
    from cas_native.training.simplex_checkpoint import load_checkpoint
    cfg = SimplexTrainConfig(
        data_path="", output_dir="",
        d_model=384, encoder_n_layers=4, decoder_n_layers=6,
        encoder_n_heads=6, decoder_n_heads=6, batch_size=1,
        max_cas_prefix_len=max_cas_prefix_len,
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


def decode_records(model: Any, records: list[dict[str, Any]],
                   collator: Any, tokenizer: Any, *,
                   device: torch.device, max_new_tokens: int,
                   tf_mode: bool) -> list[dict[str, Any]]:
    """Greedy decode each record. ``tf_mode=True`` is reserved for the
    teacher-forced path; not implemented in this evaluator's first cut —
    free-decode is the falsification metric (matches A/B/C/D postmortem
    pattern where TF passed but free-decode collapsed).
    """
    if tf_mode:
        raise NotImplementedError(
            "tf-mode is reserved; first cut runs free-decode only because "
            "TF / free-decode divergence is the exposure-bias signature "
            "we are hunting. Pass --tf-mode in a follow-on PR after the "
            "TF entrypoint is wired."
        )
    from cas_native.evaluation.sample_decoder import decode_canary_pack
    return decode_canary_pack(
        model, records, collator, tokenizer,
        device=device, max_new_tokens=max_new_tokens,
        hard_typed_emission=False,
        copy_confidence_threshold=0.5,
        truncate_traces=False,
    )


# ---- Main pipeline --------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", required=True,
                   help="Path to the model checkpoint produced by an E2a run.")
    p.add_argument("--dev-path", required=True,
                   help="Path to rpm_copy_grounding_v2_dev.jsonl")
    p.add_argument("--source-swap-dev-path", required=True,
                   help="Path to rpm_copy_grounding_v2_source_swap_dev.jsonl")
    p.add_argument("--tokenizer-path", required=True)
    p.add_argument("--english-bpe-path", default="")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--max-new-tokens", type=int, default=192)
    p.add_argument("--max-cas-prefix-len", type=int, default=192,
                   help="MUST match the value used at training time. "
                        "Defaults to 192 (Candidate E spec).")
    p.add_argument("--tf-mode", action="store_true",
                   help="Reserved; raises NotImplementedError until TF "
                        "entrypoint lands. Free-decode is the primary "
                        "falsification metric (A/B/C/D postmortem).")
    p.add_argument("--stage", choices=["e2a", "e2b"], default="e2a",
                   help="Reporting tag. ONLY e2a is implemented today; "
                        "passing e2b raises NotImplementedError because "
                        "the evaluator lacks (a) teacher-forced recovery, "
                        "(b) slot F1 scoring, (c) non-rpm leakage scoring, "
                        "(d) fail-exit thresholds — all of which the E2b "
                        "gate semantics require. Per Codex audit "
                        "2026-05-12 finding 2.")
    args = p.parse_args()

    if args.stage == "e2b":
        raise NotImplementedError(
            "--stage e2b is blocked. The Stage 2b gate semantics require "
            "teacher-forced recovery, slot F1, non-rpm leakage scoring, "
            "and fail-exit threshold enforcement — none of which are "
            "implemented in this evaluator yet. Implementing them is "
            "coupled to the Stage 2b loss PR (L_span + L_contrastive_margin "
            "+ L_coverage + pair-aware batcher). Use --stage e2a for "
            "warmup runs; rerun this evaluator with --stage e2b only "
            "after the Stage 2b PR adds the missing scoring paths AND "
            "their tests."
        )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    print(json.dumps({"event": "eval_start",
                      "stage": args.stage,
                      "tf_mode": bool(args.tf_mode)}), flush=True)

    # ---- Load eval records --------------------------------------------
    def _load_jsonl(path: str) -> list[dict[str, Any]]:
        with open(path, encoding="utf-8") as f:
            return [json.loads(ln) for ln in f if ln.strip()]

    dev_records = _load_jsonl(args.dev_path)
    swap_records = _load_jsonl(args.source_swap_dev_path)

    # Group swap records by pair_id
    pairs: dict[str, list[dict[str, Any]]] = {}
    for r in swap_records:
        pid = r.get("eval_meta", {}).get("source_swap_pair_id")
        if pid:
            pairs.setdefault(pid, []).append(r)
    # Sort pair members by variant_idx so member 0 / 1 ordering is stable
    for pid, members in pairs.items():
        members.sort(key=lambda x: x.get("eval_meta", {}).get(
            "counterfactual_variant_idx", 0))

    print(json.dumps({"event": "eval_records_loaded",
                      "n_dev": len(dev_records),
                      "n_swap_records": len(swap_records),
                      "n_swap_pairs": len(pairs)}), flush=True)

    # ---- Load tokenizer + collator ------------------------------------
    from cas_native.training.tokenizer import HybridCASTokenizer
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    tok = HybridCASTokenizer.load(args.tokenizer_path)
    if args.english_bpe_path:
        tok = tok.with_english_bpe(args.english_bpe_path)
    coll = SimplexCollator(
        tok, enable_simplex_aux=True,
        max_cas_prefix_len=args.max_cas_prefix_len,
    )

    # ---- Build model + load checkpoint --------------------------------
    vocab_size = tok.vocab_size
    model = build_model_and_load(
        vocab_size, args.checkpoint, device, args.max_cas_prefix_len,
    )

    print(json.dumps({"event": "model_loaded",
                      "vocab_size": vocab_size,
                      "max_cas_prefix_len": args.max_cas_prefix_len}),
          flush=True)

    # ---- Dev (canonical recovery) -------------------------------------
    dev_decoded = decode_records(
        model, dev_records, coll, tok,
        device=device, max_new_tokens=args.max_new_tokens,
        tf_mode=args.tf_mode,
    )
    dev_per_record: list[dict[str, Any]] = []
    total_target = 0
    total_recovered = 0
    n_dev_applicable = 0
    n_dev_full_recovery = 0
    for rec, dec in zip(dev_records, dev_decoded):
        rec_id = rec.get("id")
        gen = dec.get("generated_text", "")
        rcv = per_record_recovery(rec, gen)
        full_trace = list(dec.get("slot_type_trace", []))
        dev_per_record.append({
            "id": rec_id,
            "category": rec.get("v1mix_grammar_category_or_error_class"),
            "n_target": rcv["n_target"],
            "n_recovered": rcv["n_recovered"],
            "recovery_rate": rcv["recovery_rate"],
            "generated_identifiers": rcv["generated_identifiers"],
            "generated_text_prefix": gen[:200],
            # Slot-trace evidence — load-bearing for E2a LM/slot-head
            # stability inspection (Codex audit 2026-05-12).
            "slot_type_trace": full_trace,
            "slot_type_trace_prefix": full_trace[:40],
            "longest_stage_var_run": longest_stage_var_run(full_trace),
            "stage_var_token_count": stage_var_token_count(full_trace),
            "n_tokens_generated": dec.get("n_tokens_generated"),
            "hit_eos": dec.get("hit_eos"),
            "text_len": len(gen),
        })
        if rcv["applicable"]:
            n_dev_applicable += 1
            total_target += rcv["n_target"]
            total_recovered += rcv["n_recovered"]
            if rcv["recovery_rate"] == 1.0:
                n_dev_full_recovery += 1

    dev_summary = {
        "n_records": len(dev_records),
        "n_applicable": n_dev_applicable,
        "total_target_identifiers": total_target,
        "total_recovered_identifiers": total_recovered,
        "aggregate_recovery_rate": (
            total_recovered / total_target if total_target > 0 else None
        ),
        "n_full_recovery_records": n_dev_full_recovery,
        "full_recovery_rate": (
            n_dev_full_recovery / n_dev_applicable
            if n_dev_applicable > 0 else None
        ),
    }
    print(json.dumps({"event": "dev_scored", **dev_summary}), flush=True)

    # ---- Source-swap pairs --------------------------------------------
    # Flatten pairs to records in stable order, decode, then re-group.
    swap_records_ordered: list[dict[str, Any]] = []
    pair_index_to_pid: list[tuple[str, int]] = []
    for pid in sorted(pairs.keys()):
        for idx, m in enumerate(pairs[pid]):
            swap_records_ordered.append(m)
            pair_index_to_pid.append((pid, idx))

    swap_decoded = decode_records(
        model, swap_records_ordered, coll, tok,
        device=device, max_new_tokens=args.max_new_tokens,
        tf_mode=args.tf_mode,
    )
    # Map back to per-pair structure
    pair_results: list[dict[str, Any]] = []
    n_pairs_full_pass = 0
    n_pairs_with_cross_emission = 0
    n_pairs_with_partial_recovery = 0
    total_pair_cross_emissions = 0
    for pid in sorted(pairs.keys()):
        members = pairs[pid]
        if len(members) != 2:
            pair_results.append({
                "pair_id": pid,
                "issue": "non_paired_member_count",
                "n_members": len(members),
            })
            continue
        member_results: list[dict[str, Any]] = []
        for member_idx, member_rec in enumerate(members):
            # Find this member's decoded text
            decoded_idx = pair_index_to_pid.index((pid, member_idx))
            decoded = swap_decoded[decoded_idx]
            gen = decoded.get("generated_text", "")
            rcv = per_record_recovery(member_rec, gen)
            other_rec = members[1 - member_idx]
            cross = pair_cross_emission(member_rec, other_rec, gen)
            full_trace = list(decoded.get("slot_type_trace", []))
            member_results.append({
                "member_idx": member_idx,
                "id": member_rec.get("id"),
                "body": member_rec.get("eval_meta", {}).get("body"),
                "n_target": rcv["n_target"],
                "n_recovered": rcv["n_recovered"],
                "recovery_rate": rcv["recovery_rate"],
                "cross_emission_count": cross,
                "generated_identifiers": rcv["generated_identifiers"],
                "generated_text_prefix": gen[:200],
                # Slot-trace evidence (Codex audit 2026-05-12)
                "slot_type_trace": full_trace,
                "slot_type_trace_prefix": full_trace[:40],
                "longest_stage_var_run": longest_stage_var_run(full_trace),
                "stage_var_token_count": stage_var_token_count(full_trace),
                "n_tokens_generated": decoded.get("n_tokens_generated"),
                "hit_eos": decoded.get("hit_eos"),
                "text_len": len(gen),
            })
        rate_a = member_results[0]["recovery_rate"]
        rate_b = member_results[1]["recovery_rate"]
        cross_a = member_results[0]["cross_emission_count"]
        cross_b = member_results[1]["cross_emission_count"]
        pair_pass = (
            rate_a == 1.0 and rate_b == 1.0
            and cross_a == 0 and cross_b == 0
        )
        if pair_pass:
            n_pairs_full_pass += 1
        if cross_a > 0 or cross_b > 0:
            n_pairs_with_cross_emission += 1
            total_pair_cross_emissions += cross_a + cross_b
        if not pair_pass and not (cross_a > 0 or cross_b > 0):
            n_pairs_with_partial_recovery += 1
        pair_results.append({
            "pair_id": pid,
            "member_a": member_results[0],
            "member_b": member_results[1],
            "pair_pass": pair_pass,
        })

    swap_summary = {
        "n_pairs": len(pairs),
        "n_pairs_full_pass": n_pairs_full_pass,
        "pair_pass_rate": (
            n_pairs_full_pass / len(pairs) if pairs else None
        ),
        "n_pairs_with_cross_emission": n_pairs_with_cross_emission,
        "total_cross_emission_count": total_pair_cross_emissions,
        "n_pairs_with_partial_recovery": n_pairs_with_partial_recovery,
    }
    print(json.dumps({"event": "swap_scored", **swap_summary}), flush=True)

    # ---- Reports ------------------------------------------------------
    report = {
        "stage": args.stage,
        "checkpoint": args.checkpoint,
        "dev_path": args.dev_path,
        "source_swap_dev_path": args.source_swap_dev_path,
        "max_cas_prefix_len": args.max_cas_prefix_len,
        "max_new_tokens": args.max_new_tokens,
        "tf_mode": bool(args.tf_mode),
        "dev_summary": dev_summary,
        "swap_summary": swap_summary,
        "dev_per_record": dev_per_record,
        "swap_per_pair": pair_results,
    }
    report_path = out_dir / "evaluate_candidate_e_stage2_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    # ---- Human-readable findings --------------------------------------
    findings_path = out_dir / "evaluate_candidate_e_stage2_findings.md"
    lines: list[str] = []
    lines.append(f"# Candidate E Stage 2 evaluation — `{args.stage}`")
    lines.append("")
    lines.append(f"- checkpoint: `{args.checkpoint}`")
    lines.append(f"- dev_path: `{args.dev_path}`")
    lines.append(f"- source_swap_dev_path: `{args.source_swap_dev_path}`")
    lines.append(f"- max_cas_prefix_len: {args.max_cas_prefix_len}")
    lines.append(f"- max_new_tokens: {args.max_new_tokens}")
    lines.append(f"- tf_mode: {bool(args.tf_mode)} (False = free-decode)")
    lines.append("")
    lines.append("## Dev (canonical recovery)")
    lines.append("")
    lines.append(f"- records:                       {dev_summary['n_records']}")
    lines.append(f"- applicable rpm records:        {dev_summary['n_applicable']}")
    lines.append(f"- total target identifiers:      {dev_summary['total_target_identifiers']}")
    lines.append(f"- total recovered identifiers:   {dev_summary['total_recovered_identifiers']}")
    lines.append(f"- aggregate recovery rate:       {dev_summary['aggregate_recovery_rate']}")
    lines.append(f"- full-recovery records:         {dev_summary['n_full_recovery_records']} / {dev_summary['n_applicable']}")
    lines.append(f"- full-recovery rate:            {dev_summary['full_recovery_rate']}")
    lines.append("")
    lines.append("## Source-swap pairs (swap fidelity)")
    lines.append("")
    lines.append(f"- pairs:                              {swap_summary['n_pairs']}")
    lines.append(f"- pairs with full pass:               {swap_summary['n_pairs_full_pass']}")
    lines.append(f"- pair pass rate:                     {swap_summary['pair_pass_rate']}")
    lines.append(f"- pairs with cross-emission:          {swap_summary['n_pairs_with_cross_emission']}")
    lines.append(f"- total cross-emission count:         {swap_summary['total_cross_emission_count']}")
    lines.append(f"- pairs with partial recovery only:   {swap_summary['n_pairs_with_partial_recovery']}")
    lines.append("")
    lines.append("## Gate semantics")
    lines.append("")
    # E2b is blocked at parse-time (see --stage handling); this evaluator
    # only ever reports E2a today. Per Codex audit 2026-05-12 finding 2.
    lines.append("**E2a is warmup.** Identifier recovery is expected near 0 because")
    lines.append("copy is off (loss_weight `copy=0.0`). Metrics are informational —")
    lines.append("they inform L_span / L_contrastive_margin / L_coverage design")
    lines.append("for Stage 2b. The gate the warmup must clear is LM/slot-head")
    lines.append("stability, NOT recovery; inspect `slot_type_trace`,")
    lines.append("`longest_stage_var_run`, and `stage_var_token_count` per record")
    lines.append("in the JSON report.")
    lines.append("")
    lines.append("**E2b is NOT implemented in this evaluator.** When the Stage 2b")
    lines.append("loss PR lands, this evaluator must be extended with TF recovery,")
    lines.append("slot F1, non-rpm leakage scoring, and fail-exit thresholds")
    lines.append("(≥80% / ≥85% / ≥90% / 0). Until then `--stage e2b` raises.")
    with findings_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({
        "event": "eval_done",
        "stage": args.stage,
        "report": str(report_path),
        "findings": str(findings_path),
        "dev_summary": dev_summary,
        "swap_summary": swap_summary,
    }, default=str), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
