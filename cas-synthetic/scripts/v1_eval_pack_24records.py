"""v1 PREFIX128 5ep — 24-record stratified eval pack.

Builds on the v1 hygiene fixes (commit 79614f1):
  - cas_native.inference.routed_generate.routed_generate as entry point
  - task-aware max_new_tokens (cas_to_english=150, invalid_to_explanation=250)
  - truncation flag in PostprocessResult.truncated
  - identifier_repair (Ω names, coefficients, variables) applied by default
  - compilability gate routes valid vs invalid CAS deterministically

Loads the archived v1 PREFIX128 5ep checkpoint from the durable
location at D:\\tksCAS-archive\\runpod_runs\\..., samples 3 records
per (task_type, grammar_category) bucket = 24 records total, runs
greedy generation with the unified pipeline, and emits a markdown
grading template.

The output template has one section per record with:
  - source CAS expression
  - target reply (ground truth)
  - raw model gen
  - repaired model gen
  - structural metrics (auto-filled): truncation flag, hard-notation
    count, jargon count, Ω-recovery pre+post repair, coef-recovery,
    routing decision
  - 5-axis human grading slots (empty, per the v1 audit rubric):
      correct task / CAS meaning / natural language / completion /
      useful ending

The grading is the human's job. This script never grades its own
output (per ``feedback_grade_samples_dont_hand_procedure.md``).
"""
from __future__ import annotations

import json
import os
import random
import sys
import textwrap
import types
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


# Path bootstrap for direct invocation.
REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(SCAFFOLD_ROOT))

import torch
from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
from cas_native.model.nl_generation_head import (
    NLGenerationHead,
    NLGenerationHeadConfig,
)
from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.inference.routed_generate import routed_generate


# Stratification target: 3 records per category × 8 categories = 24.
# These categories mirror the v1 audit's 8-record sample so grades
# are directly comparable, plus 2 additional records per category
# for breadth.
STRATIFY_BUCKETS = [
    ("cas_to_english", "state_literal"),
    ("cas_to_english", "binary_composition"),
    ("cas_to_english", "cross_register_omega"),
    ("cas_to_english", "recipe"),
    ("cas_to_english", "fractal_sequence"),
    ("cas_to_english", "meta_logic_relation"),
    ("cas_to_english", "rpm_chain"),
    ("invalid_to_explanation", "rpm"),
]
RECORDS_PER_BUCKET = 3
SAMPLE_SEED = 20260509


DEFAULT_CHECKPOINT_DIR = Path(
    r"D:\tksCAS-archive\runpod_runs\2026-05-09_session_61_v1_milestone"
    r"\runs\v1_path_d_PREFIX128_5ep_20260509T035024Z"
)
# Set to True to load a v1c checkpoint (TaskTokenExtendedTokenizer +
# prepend_task_token=True). Set to False for the original v1 path
# (preserves comparability with the prior 24-record audit log).
USE_V1C_TASK_TOKENS = bool(int(os.environ.get("USE_V1C_TASK_TOKENS", "0")))
CHECKPOINT_DIR_OVERRIDE = os.environ.get("CHECKPOINT_DIR")
CHECKPOINT_DIR = Path(CHECKPOINT_DIR_OVERRIDE) if CHECKPOINT_DIR_OVERRIDE else DEFAULT_CHECKPOINT_DIR
VAL_PATH = REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "v1_mix_nlgen_val.jsonl"
OUT_DIR = REPO_ROOT / "cas-synthetic" / "data" / "path_d"


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_checkpoint():
    print(f"loading checkpoint from {CHECKPOINT_DIR}")
    print(f"  USE_V1C_TASK_TOKENS={USE_V1C_TASK_TOKENS}")
    tokenizer = HybridCASTokenizer.load(CHECKPOINT_DIR / "tokenizer.json")
    bpe = CHECKPOINT_DIR / "english_bpe.json"
    if bpe.exists():
        tokenizer = tokenizer.with_english_bpe(bpe)
    if USE_V1C_TASK_TOKENS:
        from cas_native.training.tokenizer_task_tokens import (
            extend_with_task_tokens,
        )
        tokenizer = extend_with_task_tokens(tokenizer)
        print(
            f"  v1c task tokens: VALID={tokenizer.task_token_ids.valid}, "
            f"INVALID={tokenizer.task_token_ids.invalid}"
        )
    vocab_size = int(tokenizer.vocab_size)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  device={device}, vocab_size={vocab_size}")

    enc_cfg = CASNativeConfig(
        d_model=512, n_layers=6, n_heads=8, vocab_size=vocab_size,
    )
    model = CASNativeModel(enc_cfg).to(device)
    head_cfg = NLGenerationHeadConfig(
        vocab_size=vocab_size, d_model=512, n_heads=8, n_layers=6,
    )
    head = NLGenerationHead(head_cfg).to(device)
    model.attach_nl_gen_head(head)
    state = torch.load(
        CHECKPOINT_DIR / "model_final.pt",
        map_location=device,
        weights_only=False,
    )
    model.load_state_dict(state["model"])
    model.eval()
    return model, tokenizer, device


def stratify_sample(records: list[dict]) -> list[dict]:
    rng = random.Random(SAMPLE_SEED)
    by_bucket: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        task = r.get("v1mix_task_type", "?")
        cat = r.get("v1mix_grammar_category_or_error_class", "?")
        by_bucket[(task, cat)].append(r)

    picks: list[dict] = []
    for bucket in STRATIFY_BUCKETS:
        pool = by_bucket.get(bucket, [])
        if not pool:
            print(f"  WARN: bucket {bucket} has no val records; skipping")
            continue
        n = min(RECORDS_PER_BUCKET, len(pool))
        chosen = rng.sample(pool, n)
        picks.extend(chosen)
    return picks


def render_grading_template(
    *,
    timestamp: str,
    records: list[dict],
    results: list[dict],
) -> str:
    """Build the markdown grading template.

    Each record gets a section with structural metrics (auto-filled)
    and 5-axis grading slots (empty for the human grader).
    """
    out: list[str] = []
    out.append(f"# v1 PREFIX128 5ep — 24-record human grading pack ({timestamp})")
    out.append("")
    out.append("## How to grade")
    out.append("")
    out.append(textwrap.dedent("""\
        For each record below, fill in the 5-axis grading row at the bottom:

        - **correct_task** — did the gen produce the right silhouette for
          this task family? (cas_to_english silhouette for valid CAS,
          invalid_to_explanation silhouette for invalid CAS)
        - **cas_meaning** — does the gen's content reflect the actual CAS
          source semantics (correct noetic, domain, drive, register)?
        - **natural_language** — does it read like English a human would
          write, or like translation-ese?
        - **completion** — does the sentence complete cleanly, or trail
          off / get clipped mid-clause?
        - **useful_ending** — does the gen land a conclusion / "bring it
          home," or just stop?

        Scale: ``green`` (faithful, lands), ``high_yellow`` (one slip),
        ``yellow`` (understandable but body content drifts),
        ``flop`` (target is clearly better),
        ``wrong`` (wrong task or major content error),
        ``incoherent`` (broken language).

        After grading all 24 records, run::

            python cas-synthetic/scripts/v1_eval_pack_aggregator.py \\
                --grades cas-synthetic/data/path_d/v1_eval_pack_24records_GRADED_<timestamp>.md

        to aggregate against the v1 audit baseline (5/8 combined on
        the prior 8-record pack)."""))
    out.append("")
    out.append("## Structural summary (auto-filled, not the audit)")
    out.append("")

    # Aggregate structural metrics
    n = len(results)
    truncated = sum(1 for r in results if r["truncated"])
    quality_passed = sum(1 for r in results if r["quality_passed"])
    omega_pre = sum(r["omega_recovered_pre"] for r in results)
    omega_total = sum(r["omega_total"] for r in results)
    omega_post = sum(r["omega_recovered_post"] for r in results)
    coef_pre = sum(r["coef_recovered_pre"] for r in results)
    coef_total = sum(r["coef_total"] for r in results)
    coef_post = sum(r["coef_recovered_post"] for r in results)
    hard_hits = sum(r["hard_notation_count"] for r in results)
    jargon_hits = sum(r["jargon_count"] for r in results)
    valid_routed = sum(1 for r in results if r["task_routed"] == "cas_to_english")
    invalid_routed = sum(1 for r in results if r["task_routed"] == "invalid_to_explanation")

    out.append(f"- records:                      {n}")
    out.append(f"- truncated (no EOS reached):   {truncated}/{n}")
    out.append(f"- quality_passed (no flags):    {quality_passed}/{n}")
    out.append(f"- task routed cas_to_english:   {valid_routed}/{n}")
    out.append(f"- task routed invalid_to_expl:  {invalid_routed}/{n}")
    out.append(f"- hard CAS notation in gens:    {hard_hits} (must be 0)")
    out.append(f"- jargon in gens:               {jargon_hits} (must be 0)")
    out.append(
        f"- Ω-name recovery pre-repair:   {omega_pre}/{omega_total}"
        f" ({100*omega_pre/max(omega_total,1):.1f}%)"
    )
    out.append(
        f"- Ω-name recovery post-repair:  {omega_post}/{omega_total}"
        f" ({100*omega_post/max(omega_total,1):.1f}%)"
    )
    out.append(
        f"- coefficient recovery pre:     {coef_pre}/{coef_total}"
        f" ({100*coef_pre/max(coef_total,1):.1f}%)"
    )
    out.append(
        f"- coefficient recovery post:    {coef_post}/{coef_total}"
        f" ({100*coef_post/max(coef_total,1):.1f}%)"
    )
    out.append("")
    out.append("Aggregate counts are a starting point, not the audit. Per-record")
    out.append("human grades below are the truth source.")
    out.append("")
    out.append("---")
    out.append("")

    # Per-record sections
    for i, (rec, res) in enumerate(zip(records, results), start=1):
        task = rec["v1mix_task_type"]
        cat = rec["v1mix_grammar_category_or_error_class"]
        out.append(f"## Record {i}/{len(results)} — [{task} / {cat}]")
        out.append("")
        out.append(f"**source CAS:** `{rec['cas_expression']}`")
        out.append("")
        out.append("**target reply:**")
        out.append("> " + rec["reply_text"].replace("\n", "\n> "))
        out.append("")
        out.append("**raw model gen:**")
        out.append("> " + res["raw_text"].replace("\n", "\n> "))
        out.append("")
        out.append("**repaired model gen:**")
        out.append("> " + res["final_text"].replace("\n", "\n> "))
        out.append("")
        out.append("**structural metrics (auto-filled):**")
        out.append("")
        out.append(f"- routing:           `{res['task_routed']}` (compiled={res['compiled']})")
        out.append(f"- truncated:         `{res['truncated']}`")
        out.append(f"- quality_passed:    `{res['quality_passed']}`")
        out.append(f"- quality_failures:  `{res['quality_failures'] or 'none'}`")
        out.append(
            f"- Ω recovery:        pre {res['omega_recovered_pre']}/{res['omega_total']}, "
            f"post {res['omega_recovered_post']}/{res['omega_total']}"
        )
        out.append(
            f"- coef recovery:     pre {res['coef_recovered_pre']}/{res['coef_total']}, "
            f"post {res['coef_recovered_post']}/{res['coef_total']}"
        )
        out.append(
            f"- repair subs:       Ω={res['n_omega_subs']} "
            f"coef={res['n_coef_subs']} var={res['n_var_subs']}"
        )
        out.append(f"- gen tokens:        {res['n_steps']}/{res['max_new_tokens']}")
        out.append("")
        out.append("**human grading (fill in):**")
        out.append("")
        out.append("| axis | grade | one-line note |")
        out.append("|---|---|---|")
        out.append("| correct_task | _____ | |")
        out.append("| cas_meaning | _____ | |")
        out.append("| natural_language | _____ | |")
        out.append("| completion | _____ | |")
        out.append("| useful_ending | _____ | |")
        out.append("")
        out.append("---")
        out.append("")

    return "\n".join(out)


def main() -> int:
    timestamp = _utc_now_compact()
    print(f"v1 eval pack 24-records — {timestamp}")
    print()

    # 1. Load checkpoint
    model, tokenizer, device = load_checkpoint()

    # 2. Sample
    print(f"loading val records from {VAL_PATH}")
    val_records: list[dict] = []
    with VAL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                val_records.append(json.loads(line))
    print(f"  total val records: {len(val_records)}")

    picks = stratify_sample(val_records)
    print(f"  stratified sample: {len(picks)} records")
    print()

    # 3. Run inference for each pick
    results: list[dict] = []
    for i, rec in enumerate(picks, start=1):
        cas = rec["cas_expression"]
        task = rec["v1mix_task_type"]
        cat = rec["v1mix_grammar_category_or_error_class"]
        register = rec.get("register", "T")
        print(f"  [{i:>2}/{len(picks)}] {task}/{cat} -- {cas[:60]}")

        with torch.no_grad():
            r = routed_generate(
                model=model, tokenizer=tokenizer,
                source_cas=cas,
                register=register,
                apply_repair=True,
                sampling="greedy",
                use_cas_prefix=True,
                device=device,
                prepend_task_token=USE_V1C_TASK_TOKENS,
            )

        pp = r.postprocess_result
        result = {
            "raw_text": r.raw_text,
            "final_text": r.final_text,
            "task_routed": r.task_type,
            "compiled": r.routing.compiled,
            "truncated": r.truncated,
            "quality_passed": pp.quality_passed,
            "quality_failures": pp.quality_failures,
            "hard_notation_count": pp.hard_notation_count,
            "jargon_count": pp.jargon_count,
            "omega_recovered_pre": pp.recovery_pre_repair.omega_recovered if pp.recovery_pre_repair else 0,
            "omega_total": pp.recovery_pre_repair.omega_total if pp.recovery_pre_repair else 0,
            "omega_recovered_post": pp.recovery_post_repair.omega_recovered if pp.recovery_post_repair else 0,
            "coef_recovered_pre": pp.recovery_pre_repair.coefficient_recovered if pp.recovery_pre_repair else 0,
            "coef_total": pp.recovery_pre_repair.coefficient_total if pp.recovery_pre_repair else 0,
            "coef_recovered_post": pp.recovery_post_repair.coefficient_recovered if pp.recovery_post_repair else 0,
            "n_omega_subs": len(pp.repair_log.omega_substitutions) if pp.repair_log else 0,
            "n_coef_subs": len(pp.repair_log.coefficient_substitutions) if pp.repair_log else 0,
            "n_var_subs": len(pp.repair_log.variable_substitutions) if pp.repair_log else 0,
            "n_steps": r.generation_metadata.get("n_steps"),
            "max_new_tokens": r.generation_metadata.get("max_new_tokens"),
        }
        results.append(result)

    # 4. Render grading template
    template_md = render_grading_template(
        timestamp=timestamp, records=picks, results=results,
    )

    # 5. Persist artifacts
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    template_path = OUT_DIR / f"v1_eval_pack_24records_{timestamp}.md"
    raw_path = OUT_DIR / f"v1_eval_pack_24records_{timestamp}.jsonl"
    with template_path.open("w", encoding="utf-8") as f:
        f.write(template_md)
    with raw_path.open("w", encoding="utf-8") as f:
        for rec, res in zip(picks, results):
            row = {
                "record_id": rec["id"],
                "task_type": rec["v1mix_task_type"],
                "grammar_category": rec["v1mix_grammar_category_or_error_class"],
                "cas_expression": rec["cas_expression"],
                "target": rec["reply_text"],
                **res,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print()
    print(f"wrote grading template: {template_path}")
    print(f"wrote structured raw:   {raw_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
