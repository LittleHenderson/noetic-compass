"""Stage 4A English→CAS evaluator (2026-05-14).

Gates pod launch for Stage 4A per Codex audit `dbbce48`. Six measurements on
a held-out validation split (same `deterministic_split` seed as the trainer):

  1. teacher_forced_token_accuracy
  2. free_decode_validity_rate (via api/notation/compiler.py)
  3. exact_recovery_rate (gold string equality)
  4. normalized_recovery_rate (whitespace-stripped)
  5. per-grammar-category breakdown
  6. per-surface-family breakdown

Plus sample reads stratified across surface families.

Usage:
  python noetic-compass-scaffold/noetic-compass/cas-native/evaluation/\\
      evaluate_stage4a.py \\
    --checkpoint <dir>   # contains model_final.pt + checkpoint_manifest.json \\
    --corpus cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl \\
    --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \\
    --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \\
    --output-dir <out> \\
    --device cpu --limit 50 --max-new-tokens 96 --sample-reads 10 \\
    --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \\
    --head-n-layers 6 --head-n-heads 8

The d-model / n-layers / n-heads flags must match what was used to train the
checkpoint. Otherwise `load_state_dict` will mismatch.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import time
import types
from pathlib import Path
from typing import Any

import torch

# cas_native package import shim
_THIS = Path(__file__).resolve()
_CAS_NATIVE = _THIS.parent.parent
_PROJECT_ROOT = _CAS_NATIVE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__file__ = str(_CAS_NATIVE / "__init__.py")
    pkg.__path__ = [str(_CAS_NATIVE)]
    sys.modules["cas_native"] = pkg


# ---- Surface-family classifier (regex over the GOLD reply) ---------------

_RE_LET_STAGE = re.compile(r"\blet\s+stage[ADWP]?\d", re.IGNORECASE)
_RE_CO_FORM = re.compile(r"\bCO-\d")
_RE_FRACTAL = re.compile(r"(Phi|Φ|⟨)")
_RE_DIAGRAM = re.compile(r"\b(diagram|export|->\s*\{|DiagramNode|graph)\b", re.IGNORECASE)
_RE_CARET = re.compile(r"\^\d")


def classify_surface(cas_text: str) -> str:
    """Pick one surface family for the gold CAS text. Order matters; the first
    match wins. Mirror the 5+other split Codex specified.
    """
    if _RE_LET_STAGE.search(cas_text):
        return "caret_stage"
    if _RE_DIAGRAM.search(cas_text):
        return "caret_export"
    if _RE_CO_FORM.search(cas_text):
        return "co_form"
    if _RE_FRACTAL.search(cas_text):
        return "phi_fractal"
    if _RE_CARET.search(cas_text):
        return "caret_only"
    return "other"


# ---- Compiler validity ----------------------------------------------------

def compile_ok(cas_text: str) -> tuple[bool, str | None]:
    """Run the CAS compiler on a candidate string. Returns (valid, error_msg).

    Uses the CompilationArtifact's ``.valid`` flag, not absence-of-exception.
    Empty/whitespace input is always invalid.
    """
    if not cas_text or not cas_text.strip():
        return False, "empty_or_whitespace"
    try:
        from api.notation.compiler import compile_expression
    except Exception as exc:
        return False, f"compiler_import_failed:{exc}"
    try:
        art = compile_expression(cas_text)
    except Exception as exc:
        return False, str(exc)[:240]
    valid = bool(getattr(art, "valid", False))
    err = None if valid else (getattr(art, "error", "") or "")[:240]
    return valid, err


# ---- Eval primitives ------------------------------------------------------

def _normalize(s: str) -> str:
    return re.sub(r"\s+", "", s.strip())


def teacher_forced_accuracy(model, batch, *, pad_id: int) -> tuple[int, int]:
    """Single-batch TF accuracy on the LM head's reply targets.

    Mirrors the trainer's forward call (train_native_nl_gen.py:1329) which
    passes positional args, NOT a batch dict. Returns (n_correct, n_total)
    over reply positions where loss_mask=True.
    """
    model.eval()
    with torch.no_grad():
        out = model.forward_with_lm(
            batch["input_ids"],
            batch["lm_decoder_input_ids"],
            attention_mask=batch.get("attention_mask"),
            cas_prefix_ids=batch.get("cas_prefix_ids"),
            cas_prefix_mask=batch.get("cas_prefix_mask"),
            register_id=batch.get("register_id"),
        )
    logits = out.get("lm_logits") if isinstance(out, dict) else None
    if logits is None:
        return 0, 0
    targets = batch.get("lm_targets")
    loss_mask = batch.get("loss_mask")
    if targets is None or loss_mask is None:
        return 0, 0
    preds = logits.argmax(dim=-1)
    mask = loss_mask.bool()
    correct = int(((preds == targets) & mask).sum().item())
    total = int(mask.sum().item())
    return correct, total


# ---- Main -----------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 4A English→CAS evaluator")
    p.add_argument("--checkpoint", type=str, required=True,
                   help="Directory containing model_final.pt + checkpoint_manifest.json")
    p.add_argument("--corpus", type=str, required=True)
    p.add_argument("--tokenizer-path", type=str, required=True)
    p.add_argument("--english-bpe-path", type=str, required=True)
    p.add_argument("--output-dir", type=str, required=True)
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--val-fraction", type=float, default=0.05)
    p.add_argument("--val-seed", type=int, default=42)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--max-prompt-len", type=int, default=256)
    p.add_argument("--max-reply-len", type=int, default=256)
    p.add_argument("--max-new-tokens", type=int, default=96)
    p.add_argument("--sample-reads", type=int, default=10)
    p.add_argument("--d-model", type=int, default=512)
    p.add_argument("--encoder-n-layers", type=int, default=6)
    p.add_argument("--encoder-n-heads", type=int, default=8)
    p.add_argument("--head-n-layers", type=int, default=6)
    p.add_argument("--head-n-heads", type=int, default=8)
    p.add_argument(
        "--allow-load-mismatch",
        action="store_true",
        help=(
            "Permit a tolerant load_state_dict (missing/unexpected keys allowed). "
            "Default is strict — Codex pre-launch lock per audit 27236de. "
            "Use only for known-incompatible smoke runs."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    # ---- Load corpus + deterministic split (match trainer) ----
    from cas_native.training.train_native_nl_gen import (
        load_corpus, deterministic_split, _build_cas_native_model_with_head,
    )
    records = load_corpus(args.corpus)
    if not records:
        print(json.dumps({"event": "fatal", "reason": "empty_corpus"}))
        return 2
    _train, val_records = deterministic_split(
        records, val_fraction=float(args.val_fraction), seed=int(args.val_seed),
    )
    if int(args.limit) > 0:
        val_records = val_records[: int(args.limit)]

    # Corpus hash for provenance
    h = hashlib.sha256()
    with open(args.corpus, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    corpus_sha = h.hexdigest()

    # ---- Tokenizer (mirror train_native_nl_gen.py:1042-1056) ----
    from cas_native.training.tokenizer import HybridCASTokenizer
    tokenizer = HybridCASTokenizer.load(args.tokenizer_path)
    if args.english_bpe_path:
        tokenizer = tokenizer.with_english_bpe(args.english_bpe_path)
    vocab_size = int(getattr(tokenizer, "vocab_size", 24388))
    pad_id = int(getattr(tokenizer, "PAD_ID", 0))

    # ---- Build model + load checkpoint ----
    model = _build_cas_native_model_with_head(
        vocab_size=vocab_size,
        d_model=int(args.d_model),
        n_layers=int(args.encoder_n_layers),
        n_heads=int(args.encoder_n_heads),
        head_n_layers=int(args.head_n_layers),
        head_n_heads=int(args.head_n_heads),
        seed=42,
    ).to(device)
    ckpt_dir = Path(args.checkpoint)
    ckpt_path = ckpt_dir / "model_final.pt"
    if not ckpt_path.exists():
        print(json.dumps({"event": "fatal", "reason": "checkpoint_not_found", "path": str(ckpt_path)}))
        return 3
    raw = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    state = raw.get("model") if isinstance(raw, dict) and "model" in raw else raw
    result = model.load_state_dict(state, strict=False)
    missing_keys = list(getattr(result, "missing_keys", []))
    unexpected_keys = list(getattr(result, "unexpected_keys", []))
    n_missing = len(missing_keys)
    n_unexpected = len(unexpected_keys)
    # Codex pre-launch lock (audit 27236de): if checkpoint loading reports
    # any missing or unexpected keys, the eval is invalid. Hard-fail unless
    # the operator explicitly opts into a tolerant load.
    if (n_missing > 0 or n_unexpected > 0) and not bool(getattr(args, "allow_load_mismatch", False)):
        print(json.dumps({
            "event": "fatal",
            "reason": "load_state_dict_key_mismatch",
            "n_missing_keys": n_missing,
            "n_unexpected_keys": n_unexpected,
            "missing_keys_sample": missing_keys[:10],
            "unexpected_keys_sample": unexpected_keys[:10],
            "hint": "model architecture flags must match the trained checkpoint exactly; pass --allow-load-mismatch only for known-incompatible smoke runs",
        }))
        return 4
    model.eval()

    # ---- Collator (for TF batch building) ----
    from cas_native.training.datasets.native_nl_collator import NativeNLCollator
    collator = NativeNLCollator(
        tokenizer=tokenizer,
        max_prompt_len=int(args.max_prompt_len),
        max_reply_len=int(args.max_reply_len),
        max_cas_prefix_len=32,
        enable_aux_labels=False,
        prepend_task_token=False,
    )

    # ---- Free-decode entrypoint ----
    from cas_native.inference.native_nl_generate import generate_reply

    # ---- Per-record eval loop ----
    per_record: list[dict[str, Any]] = []
    tf_correct = 0
    tf_total = 0
    n_valid_compile = 0
    n_exact = 0
    n_norm = 0
    # Generation-diversity counter — Codex v0.1 directive 2026-05-14T16:??Z
    # (commit 3b03207). Counts repeated greedy outputs across the full val
    # split to measure mode collapse directly. Normalized form (whitespace-
    # stripped) so trivial spacing differences don't inflate diversity.
    gen_counts: collections.Counter[str] = collections.Counter()
    by_cat: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"n": 0, "tf_correct": 0, "tf_total": 0, "valid": 0, "exact": 0, "norm": 0}
    )
    by_surf: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"n": 0, "tf_correct": 0, "tf_total": 0, "valid": 0, "exact": 0, "norm": 0}
    )

    t_start = time.time()
    for rec in val_records:
        gold_cas = (rec.get("reply_text") or "").strip()
        prompt = (rec.get("prompt_text") or "").strip()
        category = rec.get("grammar_category", "?")
        surface = classify_surface(gold_cas)
        # Teacher-forced
        try:
            batch = collator([rec], device=device)
            if batch is None:
                rec_tf_correct, rec_tf_total = 0, 0
            else:
                rec_tf_correct, rec_tf_total = teacher_forced_accuracy(model, batch, pad_id=pad_id)
        except Exception as exc:
            rec_tf_correct, rec_tf_total = 0, 0
            tf_err = str(exc)[:120]
        else:
            tf_err = None
        # Free-decode
        try:
            gen_out = generate_reply(
                model, tokenizer, prompt_text=prompt,
                cas_expression=None, use_cas_prefix=False,
                max_prompt_len=int(args.max_prompt_len),
                max_new_tokens=int(args.max_new_tokens),
                sampling="greedy", device=device,
            )
            gen_text = (gen_out.get("reply_text") or "").strip()
            gen_err = None
        except Exception as exc:
            gen_text = ""
            gen_err = str(exc)[:120]
        # Compile
        valid, comp_err = compile_ok(gen_text) if gen_text else (False, "empty_generation")
        # Exact / normalized
        exact = gen_text == gold_cas
        norm = _normalize(gen_text) == _normalize(gold_cas)
        # Track normalized generated text for diversity
        gen_counts[_normalize(gen_text) or "<EMPTY>"] += 1

        per_record.append({
            "id": rec.get("id"),
            "category": category,
            "surface": surface,
            "prompt_text": prompt,
            "gold_reply": gold_cas,
            "generated_reply": gen_text,
            "tf_correct": rec_tf_correct,
            "tf_total": rec_tf_total,
            "valid": valid,
            "compile_error": comp_err,
            "exact_match": exact,
            "normalized_match": norm,
            "tf_error": tf_err,
            "gen_error": gen_err,
        })
        tf_correct += rec_tf_correct
        tf_total += rec_tf_total
        n_valid_compile += int(valid)
        n_exact += int(exact)
        n_norm += int(norm)

        for bucket, key in ((by_cat, category), (by_surf, surface)):
            d = bucket[key]
            d["n"] += 1
            d["tf_correct"] += rec_tf_correct
            d["tf_total"] += rec_tf_total
            d["valid"] += int(valid)
            d["exact"] += int(exact)
            d["norm"] += int(norm)

    elapsed_s = time.time() - t_start
    n = len(val_records)

    def rate(num: int, den: int) -> float:
        return (num / den) if den > 0 else 0.0

    # Diversity / mode-collapse metrics (Codex v0.1 directive 3b03207).
    # All ratios are over normalized (whitespace-stripped) generated text.
    unique_outputs = len(gen_counts)
    top_modes = gen_counts.most_common(5)
    top_mode_count = top_modes[0][1] if top_modes else 0
    aggregate = {
        "tf_per_token_accuracy": rate(tf_correct, tf_total),
        "free_decode_validity_rate": rate(n_valid_compile, n),
        "exact_recovery_rate": rate(n_exact, n),
        "normalized_recovery_rate": rate(n_norm, n),
        "tf_tokens_scored": tf_total,
        "n_records": n,
        "unique_outputs_count": unique_outputs,
        "unique_output_ratio": rate(unique_outputs, n),
        "top_mode_count": top_mode_count,
        "mode_collapse_ratio": rate(top_mode_count, n),
    }
    diversity = {
        "unique_outputs_count": unique_outputs,
        "unique_output_ratio": rate(unique_outputs, n),
        "top_mode_count": top_mode_count,
        "mode_collapse_ratio": rate(top_mode_count, n),
        "top_5_modes": [
            {"normalized_text": text[:200], "count": count, "share": rate(count, n)}
            for text, count in top_modes
        ],
    }

    def bucket_summary(b: dict[str, dict[str, int]]) -> dict[str, Any]:
        return {
            key: {
                "n": d["n"],
                "tf_acc": rate(d["tf_correct"], d["tf_total"]),
                "validity": rate(d["valid"], d["n"]),
                "exact_recovery": rate(d["exact"], d["n"]),
                "normalized_recovery": rate(d["norm"], d["n"]),
            }
            for key, d in sorted(b.items())
        }

    # Stratified sample reads: take first 2 per surface family until budget hit
    samples: list[dict[str, Any]] = []
    by_surf_records: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in per_record:
        by_surf_records[r["surface"]].append(r)
    n_per_family = max(1, int(args.sample_reads) // max(1, len(by_surf_records)))
    for fam, recs in sorted(by_surf_records.items()):
        for r in recs[:n_per_family]:
            samples.append(r)
            if len(samples) >= int(args.sample_reads):
                break
        if len(samples) >= int(args.sample_reads):
            break

    report = {
        "schema_version": "stage4a_eval.v1",
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checkpoint": str(ckpt_dir.resolve()),
        "corpus": str(Path(args.corpus).resolve()),
        "corpus_sha256": corpus_sha,
        "n_val_records": n,
        "elapsed_seconds": elapsed_s,
        "load_state_dict_missing_keys": n_missing,
        "load_state_dict_unexpected_keys": n_unexpected,
        "aggregate": aggregate,
        "diversity": diversity,
        "per_category": bucket_summary(by_cat),
        "per_surface_family": bucket_summary(by_surf),
        "config": {
            "val_fraction": float(args.val_fraction),
            "val_seed": int(args.val_seed),
            "limit": int(args.limit),
            "max_new_tokens": int(args.max_new_tokens),
            "sampling": "greedy",
            "d_model": int(args.d_model),
            "encoder_n_layers": int(args.encoder_n_layers),
            "head_n_layers": int(args.head_n_layers),
        },
    }

    report_path = out_dir / "stage4a_eval_report.json"
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)

    samples_path = out_dir / "samples.jsonl"
    with samples_path.open("w", encoding="utf-8") as fh:
        for s in samples:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(json.dumps({
        "event": "stage4a_eval_complete",
        "n_records": n,
        "tf_per_token_accuracy": aggregate["tf_per_token_accuracy"],
        "free_decode_validity_rate": aggregate["free_decode_validity_rate"],
        "exact_recovery_rate": aggregate["exact_recovery_rate"],
        "normalized_recovery_rate": aggregate["normalized_recovery_rate"],
        "unique_output_ratio": aggregate["unique_output_ratio"],
        "mode_collapse_ratio": aggregate["mode_collapse_ratio"],
        "report_path": str(report_path),
        "samples_path": str(samples_path),
        "elapsed_seconds": elapsed_s,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
