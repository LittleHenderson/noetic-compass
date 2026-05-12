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
from typing import Any, Optional

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
    """Greedy decode each record (free-decode). ``tf_mode`` here only
    distinguishes the legacy --tf-mode CLI flag; the actual TF
    identifier-level recovery is computed by ``teacher_forced_eval`` and
    is the E2b gate metric per design doc §Stage 2b.
    """
    if tf_mode:
        # The actual TF metric lives in teacher_forced_eval(), which is
        # called separately in main(). decode_records is the free-decode
        # path for slot-trace evidence + swap-pair cross-emission.
        raise NotImplementedError(
            "decode_records does not implement TF; use teacher_forced_eval() "
            "for the load-bearing TF identifier-level recovery metric."
        )
    from cas_native.evaluation.sample_decoder import decode_canary_pack
    return decode_canary_pack(
        model, records, collator, tokenizer,
        device=device, max_new_tokens=max_new_tokens,
        hard_typed_emission=False,
        copy_confidence_threshold=0.5,
        truncate_traces=False,
    )


# ---- Teacher-forced identifier-level recovery (E2b primary gate) ---------

SLOT_STAGE_VAR_ID = 2  # cas_native.training.datasets.simplex_collator.SLOT_STAGE_VAR


def teacher_forced_eval(
    model: Any, records: list[dict[str, Any]],
    collator: Any, *, device: torch.device,
) -> list[dict[str, Any]]:
    """Run teacher-forced forward pass on each record; compute per-record
    identifier-level recovery (the design doc §Stage 2b TF gate).

    Method:
      1. Use SimplexCollator to build the same batch the trainer would see,
         which includes the GOLD lm_decoder_input_ids (so forward is TF).
      2. Forward model(batch). Extract p_copy at each output position.
      3. For each STAGE_VAR target span (contiguous run of slot_id == 2):
         per-token argmax(p_copy[k]) is the model's predicted source pos
         under TF. Compare against gold typed_slot_source[k]. The span
         "recovers" the identifier iff ALL tokens in the span have
         correct argmax src.

    Per-token correctness IS the standard "fresh source recovery" metric
    when teacher-forced: under TF, the model sees the correct context,
    so the only thing that matters is "did the copy/pointer head learn
    to point at the right source token for each output position." This
    isolates the copy-learning question from generation drift.

    Returns per-record list with: id, category, n_target_identifiers,
    n_recovered_identifiers, identifier_recovery_rate, per_token_correct,
    per_identifier_correct.
    """
    model.eval()
    results: list[dict[str, Any]] = []
    with torch.no_grad():
        for rec in records:
            batch = collator([rec], device=device)
            if batch is None:
                results.append({
                    "id": rec.get("id"), "n_target_identifiers": 0,
                    "n_recovered_identifiers": 0,
                    "identifier_recovery_rate": None,
                    "per_token_correct": 0,
                    "per_token_total": 0,
                    "applicable": False,
                    "error": "collator_returned_none",
                })
                continue
            try:
                out = model(batch)
            except Exception as exc:
                results.append({
                    "id": rec.get("id"), "n_target_identifiers": 0,
                    "n_recovered_identifiers": 0,
                    "identifier_recovery_rate": None,
                    "per_token_correct": 0,
                    "per_token_total": 0,
                    "applicable": False,
                    "error": f"forward_failed: {exc!r}",
                })
                continue

            p_copy = out["p_copy"][0]                                 # (L_out, L_src)
            argmax_src = p_copy.argmax(dim=-1).to(dtype=torch.long)   # (L_out,)
            tsp = batch["typed_slot_positions"][0].argmax(dim=-1)     # (L_out,)
            tss = batch["typed_slot_source"][0].to(dtype=torch.long)  # (L_out,)

            # Find contiguous STAGE_VAR spans in target
            spans: list[tuple[int, int]] = []
            in_span = False
            sp_start = -1
            L_out = int(tsp.shape[0])
            for k in range(L_out):
                is_sv = int(tsp[k].item()) == SLOT_STAGE_VAR_ID
                if is_sv and not in_span:
                    in_span = True
                    sp_start = k
                elif not is_sv and in_span:
                    spans.append((sp_start, k))
                    in_span = False
            if in_span:
                spans.append((sp_start, L_out))

            # Score each span: identifier recovered iff every gold-mapped
            # in-span token has correct argmax src.
            #
            # Per-span failure-mode diagnostics (Candidate E Stage 2c
            # 2026-05-12 per user directive): for each failed span,
            # classify the failure pattern:
            #   exact:             all in-span tokens correct
            #   wrong_start:       first in-span gold-mapped token's argmax
            #                      is wrong (whole-ID lost from the start)
            #   right_start_drift: first token correct, at least one later
            #                      token wrong (model started right but
            #                      pointer slipped mid-ID)
            # Per-token off-by-one tracking captures the "drift by ±1
            # source position" failure mode that L_span specifically
            # targets and L_start_anchor targets the start of.
            per_identifier_correct: list[bool] = []
            failure_modes: dict[str, int] = {
                "exact": 0,
                "wrong_start": 0,
                "right_start_drift": 0,
            }
            per_token_correct = 0
            per_token_total = 0
            per_token_off_by_one = 0  # pred_src in {gold ± 1}
            for sp_s, sp_e in spans:
                ident_correct = True
                ident_has_gold = False
                first_gold_correct: Optional[bool] = None
                for k in range(sp_s, sp_e):
                    gold_src = int(tss[k].item())
                    if gold_src < 0:
                        continue
                    ident_has_gold = True
                    pred_src = int(argmax_src[k].item())
                    per_token_total += 1
                    token_correct = (pred_src == gold_src)
                    if first_gold_correct is None:
                        first_gold_correct = token_correct
                    if token_correct:
                        per_token_correct += 1
                    else:
                        ident_correct = False
                        if abs(pred_src - gold_src) == 1:
                            per_token_off_by_one += 1
                if ident_has_gold:
                    per_identifier_correct.append(ident_correct)
                    if ident_correct:
                        failure_modes["exact"] += 1
                    elif first_gold_correct is False:
                        failure_modes["wrong_start"] += 1
                    else:  # first_gold_correct is True
                        failure_modes["right_start_drift"] += 1

            n_target = len(per_identifier_correct)
            n_recovered = sum(per_identifier_correct)
            results.append({
                "id": rec.get("id"),
                "category": rec.get("v1mix_grammar_category_or_error_class"),
                "n_target_identifiers": n_target,
                "n_recovered_identifiers": n_recovered,
                "identifier_recovery_rate": (
                    n_recovered / n_target if n_target > 0 else None
                ),
                "per_token_correct": per_token_correct,
                "per_token_total": per_token_total,
                "per_token_off_by_one": per_token_off_by_one,
                "per_token_accuracy": (
                    per_token_correct / per_token_total
                    if per_token_total > 0 else None
                ),
                "per_identifier_correct": per_identifier_correct,
                "failure_modes": failure_modes,
                "applicable": n_target > 0,
            })
    return results


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
                   help="Legacy flag for decode_records; teacher-forced "
                        "evaluation is now always run via teacher_forced_eval() "
                        "to compute the e2b gate, regardless of this flag. "
                        "Setting this only affects the secondary free-decode "
                        "path (which raises if true). Kept for CLI backward "
                        "compatibility.")
    p.add_argument("--stage", choices=["e2a", "e2b", "e2c"], default="e2a",
                   help="Reporting tag. e2a is informational (no gate). "
                        "e2b: PRIMARY gate is TF identifier_recovery_rate "
                        ">= --gate-recovery (default 0.80). e2c: PRIMARY "
                        "gate is TF per_token_accuracy >= "
                        "--gate-per-token-accuracy (default 0.70) — "
                        "intermediate gate before whole-ID recovery, per "
                        "user 2026-05-12 post-E2b directive. Both e2b and "
                        "e2c also report swap pair_pass_rate. Exits "
                        "non-zero (return 2) if PRIMARY gate misses.")
    p.add_argument("--gate-recovery", type=float, default=0.80,
                   help="E2b PRIMARY gate: teacher-forced "
                        "tf_dev_summary.identifier_recovery_rate must meet "
                        "or exceed this value. Per design doc §Stage 2b "
                        "'fresh source recovery >=80%'. Identifier-level: "
                        "total_recovered_identifiers / total_target_identifiers.")
    p.add_argument("--gate-per-token-accuracy", type=float, default=0.70,
                   help="E2c PRIMARY gate: teacher-forced "
                        "tf_dev_summary.per_token_accuracy must meet or "
                        "exceed this value. Per user 2026-05-12 directive: "
                        "after E2b's 38% per-token result, target 70%+ "
                        "before whole-ID recovery is meaningful. "
                        "Total correct / total in-span gold-mapped tokens.")
    p.add_argument("--gate-swap", type=float, default=0.85,
                   help="Swap gate: swap_summary.pair_pass_rate must meet "
                        "or exceed this value. Reported at e2b/e2c.")
    args = p.parse_args()

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

    # ---- Dev TF identifier-level recovery (E2b primary gate) ----------
    # Per design doc §Stage 2b + user audit 2026-05-12: E2b is supposed
    # to answer "Can the model copy the right source ID when the correct
    # prefix/context is held stable?" That is a TEACHER-FORCED question.
    # Free-decode metrics (slot trace, swap cross-emission) come AFTER
    # this TF gate as supplementary evidence.
    tf_results = teacher_forced_eval(
        model, dev_records, coll, device=device,
    )
    # Aggregate identifier-level + full-record metrics
    tf_total_target = sum(r["n_target_identifiers"] for r in tf_results)
    tf_total_recovered = sum(r["n_recovered_identifiers"] for r in tf_results)
    tf_n_applicable = sum(1 for r in tf_results if r["applicable"])
    tf_n_full_recovery = sum(
        1 for r in tf_results
        if r["applicable"] and r["identifier_recovery_rate"] == 1.0
    )
    tf_per_token_correct = sum(r["per_token_correct"] for r in tf_results)
    tf_per_token_total = sum(r["per_token_total"] for r in tf_results)
    tf_per_token_off_by_one = sum(r.get("per_token_off_by_one", 0) for r in tf_results)
    # Aggregate per-span failure-mode counts across records
    tf_failure_modes = {"exact": 0, "wrong_start": 0, "right_start_drift": 0}
    for r in tf_results:
        fm = r.get("failure_modes", {})
        for k in tf_failure_modes:
            tf_failure_modes[k] += fm.get(k, 0)
    tf_total_spans = sum(tf_failure_modes.values())
    tf_dev_summary = {
        "n_records": len(tf_results),
        "n_applicable": tf_n_applicable,
        # IDENTIFIER-LEVEL recovery (the E2b design doc gate metric)
        "total_target_identifiers": tf_total_target,
        "total_recovered_identifiers": tf_total_recovered,
        "identifier_recovery_rate": (
            tf_total_recovered / tf_total_target
            if tf_total_target > 0 else None
        ),
        # FULL-RECORD recovery (stricter, secondary)
        "n_full_recovery_records": tf_n_full_recovery,
        "full_recovery_rate": (
            tf_n_full_recovery / tf_n_applicable
            if tf_n_applicable > 0 else None
        ),
        # PER-TOKEN accuracy (most granular — E2c PRIMARY gate metric)
        "per_token_correct": tf_per_token_correct,
        "per_token_total": tf_per_token_total,
        "per_token_accuracy": (
            tf_per_token_correct / tf_per_token_total
            if tf_per_token_total > 0 else None
        ),
        "per_token_off_by_one": tf_per_token_off_by_one,
        "per_token_off_by_one_rate": (
            tf_per_token_off_by_one / max(tf_per_token_total - tf_per_token_correct, 1)
            if tf_per_token_total > 0 else None
        ),
        # Per-span failure-mode diagnostics (E2c per user 2026-05-12)
        "span_failure_modes": tf_failure_modes,
        "span_failure_mode_rates": {
            k: (v / tf_total_spans if tf_total_spans > 0 else None)
            for k, v in tf_failure_modes.items()
        },
    }
    print(json.dumps({"event": "tf_dev_scored", **tf_dev_summary}), flush=True)

    # ---- Dev free-decode (informational + slot-trace evidence) --------
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
        "tf_dev_summary": tf_dev_summary,   # PRIMARY e2b gate source
        "tf_dev_per_record": tf_results,
        "dev_summary": dev_summary,         # free-decode, informational
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
    lines.append(f"- tf_mode legacy flag: {bool(args.tf_mode)} (TF eval is always run for the e2b gate)")
    lines.append("")
    lines.append("## TF dev (teacher-forced identifier-level recovery — PRIMARY E2b GATE)")
    lines.append("")
    lines.append(f"- records:                              {tf_dev_summary['n_records']}")
    lines.append(f"- applicable rpm records:               {tf_dev_summary['n_applicable']}")
    lines.append(f"- total target identifiers:             {tf_dev_summary['total_target_identifiers']}")
    lines.append(f"- total recovered identifiers (TF):     {tf_dev_summary['total_recovered_identifiers']}")
    lines.append(f"- identifier_recovery_rate (TF):        **{tf_dev_summary['identifier_recovery_rate']}** ← GATE METRIC")
    lines.append(f"- full_recovery_rate (TF, strict):      {tf_dev_summary['full_recovery_rate']}")
    lines.append(f"- per_token_accuracy (TF, granular):    {tf_dev_summary['per_token_accuracy']}")
    lines.append("")
    lines.append("Identifier-level (gate metric) credits a record-IDs as recovered iff")
    lines.append("EVERY token in its STAGE_VAR span has correct argmax(p_copy) under TF.")
    lines.append("Full-record (strict) requires ALL canonical identifiers in a record")
    lines.append("recovered. Per-token is the most granular: fraction of in-span tokens")
    lines.append("with correct argmax src.")
    lines.append("")
    lines.append("## Dev free-decode (informational — slot-trace + drift evidence)")
    lines.append("")
    lines.append(f"- records:                       {dev_summary['n_records']}")
    lines.append(f"- applicable rpm records:        {dev_summary['n_applicable']}")
    lines.append(f"- total target identifiers:      {dev_summary['total_target_identifiers']}")
    lines.append(f"- total recovered identifiers:   {dev_summary['total_recovered_identifiers']}")
    lines.append(f"- aggregate recovery rate:       {dev_summary['aggregate_recovery_rate']}")
    lines.append(f"- full-recovery records:         {dev_summary['n_full_recovery_records']} / {dev_summary['n_applicable']}")
    lines.append(f"- full-recovery rate:            {dev_summary['full_recovery_rate']}")
    lines.append("")
    lines.append("Free-decode metrics measure what happens when the model generates its")
    lines.append("own prefix — drift failure modes show here. TF/free-decode divergence is")
    lines.append("the exposure-bias signature from the A/B/C/D postmortems.")
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
    # E2b/E2c gates per design doc §Stage 2b + user audit 2026-05-12:
    #   E2b PRIMARY:  TF identifier_recovery_rate >= --gate-recovery
    #   E2c PRIMARY:  TF per_token_accuracy >= --gate-per-token-accuracy
    #                 (intermediate gate before whole-ID recovery)
    #   SECONDARY (both stages): swap pair_pass_rate >= --gate-swap
    tf_recovery_value = tf_dev_summary.get("identifier_recovery_rate") or 0.0
    tf_per_token_value = tf_dev_summary.get("per_token_accuracy") or 0.0
    swap_value = swap_summary.get("pair_pass_rate") or 0.0
    tf_recovery_gate_pass = tf_recovery_value >= args.gate_recovery
    tf_per_token_gate_pass = tf_per_token_value >= args.gate_per_token_accuracy
    swap_gate_pass = swap_value >= args.gate_swap
    gates = {
        "tf_identifier_recovery": {
            "value": tf_recovery_value,
            "threshold": args.gate_recovery,
            "pass": tf_recovery_gate_pass,
        },
        "tf_per_token_accuracy": {
            "value": tf_per_token_value,
            "threshold": args.gate_per_token_accuracy,
            "pass": tf_per_token_gate_pass,
        },
        "swap": {
            "value": swap_value,
            "threshold": args.gate_swap,
            "pass": swap_gate_pass,
        },
    }
    # Also surface the strict full-record recovery rate (TF) for context —
    # not gated, but informative if it's much lower than identifier-level
    # (means model gets most IDs right but misses 1 in long chains).
    tf_full_recovery = tf_dev_summary.get("full_recovery_rate")
    tf_per_token_acc = tf_per_token_value
    if args.stage == "e2a":
        lines.append("**E2a is warmup.** Identifier recovery is expected near 0 because")
        lines.append("copy is off (loss_weight `copy=0.0`). Metrics are informational —")
        lines.append("they inform L_span / L_contrastive_margin / L_coverage design")
        lines.append("for Stage 2b. The gate the warmup must clear is LM/slot-head")
        lines.append("stability, NOT recovery; inspect `slot_type_trace`,")
        lines.append("`longest_stage_var_run`, and `stage_var_token_count` per record")
        lines.append("in the JSON report.")
        lines.append("")
        lines.append("Gates below are reported but NOT enforced at --stage e2a.")
    else:
        lines.append("**E2b enforces fail-exit gates** per design doc §Stage 2b.")
        lines.append("Evaluator exits non-zero if any gate misses.")
    lines.append("")
    lines.append("| gate | value | threshold | pass |")
    lines.append("|---|---|---|---|")
    if args.stage == "e2c":
        lines.append(f"| **TF per_token_accuracy** (E2c PRIMARY) | {tf_per_token_value:.4f} | {args.gate_per_token_accuracy:.4f} | {'✓' if tf_per_token_gate_pass else '✗'} |")
        lines.append(f"| TF identifier_recovery_rate (informational at e2c) | {tf_recovery_value:.4f} | {args.gate_recovery:.4f} | {'✓' if tf_recovery_gate_pass else '✗'} |")
    else:
        lines.append(f"| **TF identifier_recovery_rate** (E2b PRIMARY) | {tf_recovery_value:.4f} | {args.gate_recovery:.4f} | {'✓' if tf_recovery_gate_pass else '✗'} |")
        lines.append(f"| TF per_token_accuracy (informational at e2b) | {tf_per_token_value:.4f} | {args.gate_per_token_accuracy:.4f} | {'✓' if tf_per_token_gate_pass else '✗'} |")
    lines.append(f"| swap pair_pass_rate (SECONDARY, free-decode) | {swap_value:.4f} | {args.gate_swap:.4f} | {'✓' if swap_gate_pass else '✗'} |")
    lines.append("")
    lines.append("**Context (not gated):**")
    lines.append(f"- TF full_recovery_rate (strict whole-record): {tf_full_recovery}")
    sfm = tf_dev_summary.get("span_failure_modes", {})
    sfm_rates = tf_dev_summary.get("span_failure_mode_rates", {})
    lines.append(f"- TF span failure modes: exact={sfm.get('exact',0)} ({sfm_rates.get('exact')}), wrong_start={sfm.get('wrong_start',0)} ({sfm_rates.get('wrong_start')}), right_start_drift={sfm.get('right_start_drift',0)} ({sfm_rates.get('right_start_drift')})")
    obo = tf_dev_summary.get("per_token_off_by_one", 0)
    obo_rate = tf_dev_summary.get("per_token_off_by_one_rate")
    lines.append(f"- TF per-token off-by-one (of incorrect tokens): {obo} ({obo_rate})")
    lines.append("")
    lines.append("**Not yet implemented in this evaluator** (deferred per user")
    lines.append("2026-05-12 evaluator-upgrade scope decision): slot F1 against")
    lines.append("gold target slot tags, non-rpm leakage scoring against a non-rpm")
    lines.append("dev subset. These extensions land in a follow-on PR; they are")
    lines.append("NOT prerequisites for E2b launch, because exact-ID recovery and")
    lines.append("wrong-pair leakage are the load-bearing E2b signals.")

    # Stage-specific overall pass determination:
    #   e2a: informational only, no fail-exit
    #   e2b: PRIMARY = tf_identifier_recovery; SECONDARY = swap
    #   e2c: PRIMARY = tf_per_token_accuracy; SECONDARY = swap
    if args.stage == "e2c":
        overall_pass = tf_per_token_gate_pass and swap_gate_pass
        primary_gate_name = "tf_per_token_accuracy"
    else:  # e2a or e2b
        overall_pass = tf_recovery_gate_pass and swap_gate_pass
        primary_gate_name = "tf_identifier_recovery"
    report["gate_stage"] = args.stage
    report["gate_primary"] = primary_gate_name
    report["e2b_gates"] = gates  # key kept for backward-compatibility
    report["gates"] = gates
    report["e2b_overall_pass"] = overall_pass  # legacy key
    report["overall_pass"] = overall_pass
    # Rewrite report with gate fields added
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    with findings_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({
        "event": "eval_done",
        "stage": args.stage,
        "primary_gate": primary_gate_name,
        "report": str(report_path),
        "findings": str(findings_path),
        "tf_dev_summary": tf_dev_summary,
        "dev_summary": dev_summary,
        "swap_summary": swap_summary,
        "gates": gates,
        "overall_pass": overall_pass,
    }, default=str), flush=True)
    # Fail-exit on PRIMARY gate miss at --stage e2b or e2c.
    # At --stage e2a, gates are informational only.
    if args.stage in ("e2b", "e2c") and not overall_pass:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
