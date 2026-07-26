"""Matched A/B blind-recovery driver — Gate 2 closure, 2026-07-26.

Re-runs the June 2026 blind-recovery comparison (original TKS foundation
wording vs generic drive+register shorthand COMPOSITION — NOT "original vs
shortened": the compact texts measure 125-150 chars vs TKS 98-152, so the
compact arm is not shorter) as a SINGLE-SESSION matched A/B in which both
arms are authored under an identical protocol and differ ONLY in the
definition text (R1). The June result (89/140 = 63.57% vs 22/140 = 15.71%)
is NOT LICENSED because the arms used different fixture sets authored on
different days, different judges reported the two headline numbers, and the
blind row ids leaked the foundation label (e.g. "F1A_000").

This driver:
  R1  builds both arm plans from one template (definition text is the only
      variable), same deterministic seeds, same row counts (280/arm =
      10 per foundation), arm-interleaved chunk authoring order A,D,A,D...
      Template identity is enforced by a REAL guard: every paired authoring
      prompt is byte-compared after stripping exactly the two injection
      segments (the definition line and the source-terms JSON line); any
      diff hard-fails the driver.
  R2  one frozen blind judge model for both arms, temperature 0.0, answer
      key withheld, all 560 rows pooled, seeded shuffle, OPAQUE row ids,
      no arm labels. SYMMETRIC JUDGE CROSS: two passes over the same
      shuffled pool — pass K_A uses the original TKS 28 meanings as the
      choice key, pass K_D uses the compact meanings as the choice key;
      prompts otherwise identical (June's choice-set-anchoring sentence is
      removed, verified at runtime). Per-arm recovery = MEAN over passes.
  R3  Gate 1 surface control per arm: surface_X = max(word TF-IDF baseline,
      char 3-5-gram baseline), both 5-fold CV with the same fixed
      random_state, identical config across arms (standing char-level
      surface-control mandate); primary endpoint is DE-LEAKED:
      (recovery_A - surface_A) - (recovery_D - surface_D).
  R4  TWO-TIER frozen criteria: PRIMARY (strong claim) = margin >= +0.10
      AND paired permutation p < 0.01 (10,000 label-preserving sign-flip
      permutations) AND bootstrap 95% CI of the margin excludes 0.
      SECONDARY (wording capped at "directionally supported below the
      pre-registered strong margin") = 0 < margin < 0.10 with the same
      p and CI requirements. Plus degeneracy guards.
  R5  writes every raw artifact (plans, chunks, fixtures, prompt
      transcripts, blind pool, key, permutation, preds, results) under
      this directory.
  R6  --dry-run prints planned request counts + token/cost estimate and
      makes NO API calls.
  R7  model pins: June-exact set (authoring models/gemini-2.5-flash-lite,
      judge models/gemini-2.5-flash); fallback pin for BOTH roles and BOTH
      arms (never mixed) is models/gemini-3.1-pro-preview if the June
      models are gone; models actually used are recorded in the results.

June pathway code is imported (not copied) from the read-only lineage dirs
so the authoring prompt, validators, judge prompt, and Gate 1 word-baseline
math are the June bytes, not paraphrases. The three judge-prompt
neutralizations (anchoring sentence removed, header neutralized, meaning
field renamed) are applied identically to both passes and verified by exact
occurrence counts at runtime.

NOT LICENSED note: passing this A/B licenses only a fixture-level claim
about definition wording (see PREREG_DRAFT.md). It licenses no hidden-state,
GPU-probe, or model-internals claim.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
JUNE_DIR = REPO / "docs" / "working" / "mtc_f28_goemotions_20260615"

CANONICAL_TKS = Path(
    r"C:\Users\wakil\Downloads\Everthing-Tootra-TKS\canon\normalized\canon_subfoundations_28_defs.json"
)
CANONICAL_TKS_SHA256 = "5507bf6f85f63dc62847ea5f9018b6ad4471ca8acfe851a0f50d2b4ebbf6c88d"
COMPACT_DEFS = HERE / "compact_defs_28.json"
COMPACT_DEFS_SHA256 = "d6fb9ea114abaad583f3933d3c88882b4ba1b6e6e04cf11021dc39417d9209b9"

JUDGE_PASSES = ("K_A", "K_D")

# ---------------------------------------------------------------- frozen config
FROZEN = {
    "schema_version": "gate2_closure_matched_ab.v2",
    "date": "20260726",
    "base_seed": 20260726,
    "arms": ["A", "D"],  # A = original TKS defs, D = compact drive+register shorthand compositions
    "framing": (
        "The manipulation is 'original TKS foundation wording vs generic drive+register shorthand "
        "composition' — NOT 'original vs shortened'. Measured definition lengths: compact 125-150 chars "
        "vs TKS 98-152 chars; the compact arm is NOT shorter."
    ),
    "n_per_foundation": 10,          # 280 rows per arm
    "rows_per_chunk": 10,            # 1 chunk per foundation per arm = 28 chunks/arm
    "author_batch_size": 5,          # June exact => 2 batches per chunk
    "author_model": "models/gemini-2.5-flash-lite",   # June exact (flash-LITE, both June lineages)
    "judge_model": "models/gemini-2.5-flash",         # June exact
    "adjudication_model": "models/gemini-2.5-pro",    # optional, reported separately, never primary
    "fallback_model": "models/gemini-3.1-pro-preview",  # single pin for both roles+arms if June models unavailable
    "author_generation_config": {    # June exact (author_confirmatory_chunks_gemini.py lines 467-474)
        "response_mime_type": "application/json",
        "temperature": 0.95,
        "top_p": 0.95,
        "max_output_tokens": 8192,
    },
    "judge_generation_config": {     # temperature 0.0 is a DELIBERATE change vs June's 0.1 (pre-registered, R2)
        "response_mime_type": "application/json",
        "temperature": 0.0,
        "max_output_tokens": 16384,
    },
    "judge_cross": {                 # H2 fix: symmetric judge cross kills choice-set anchoring
        "passes": {
            "K_A": "choice key = original TKS 28 subfoundation meanings (sha-pinned canon file)",
            "K_D": "choice key = compact drive+register shorthand compositions (compact_defs_28.json)",
        },
        "pool": "both passes score the SAME shuffled 560-row blind pool with the same opaque ids",
        "per_arm_recovery": "MEAN over the two passes",
        "prompt_neutralizations": [
            "remove the line 'Use the original TKS meanings below, not shorthand drive/register summaries.' (must occur exactly once)",
            "replace the header 'Foundation options from original TKS definitions:' with 'Foundation options:' (must occur exactly once)",
            "rename the JSON field 'original_tks_meaning' to 'meaning' (must occur exactly 28 times)",
        ],
        "rationale": (
            "June's judge used the original TKS meanings as the choice set for BOTH arms and told the judge "
            "to prefer them, anchoring toward arm A. The full cross (each arm's definition style serves as "
            "the choice key in one pass, averaged) removes choice-set anchoring symmetrically."
        ),
    },
    "judge_batch_size": 10,          # June exact
    "retries": 3,                    # June exact
    "retry_sleep_s": 2.0,            # June exact (sleep = 2.0 * attempt)
    "gate1_threshold": 0.60,         # June exact, now applied to max(word, char) surface
    "surface_control": {             # H1 fix: standing mandatory char-level surface control
        "rule": "surface_X = max(word_tfidf_answer_stripped, char_3to5_gram_answer_stripped) per arm, per label task",
        "word_vectorizer": {"ngram_range": [1, 2], "min_df": 2, "sublinear_tf": True, "max_features": 20000},
        "char_vectorizer": {"analyzer": "char", "ngram_range": [3, 5], "min_df": 2, "sublinear_tf": True, "max_features": 20000},
        "classifier": "LogisticRegression(max_iter=2000, class_weight='balanced')",
        "cv": {"n_splits": 5, "shuffle": True, "random_state": 0},
        "cv_seed_sensitivity_seeds": [0, 1, 2, 3, 4],
        "note": (
            "Both baselines 5-fold stratified CV with the SAME fixed random_state, identical config across "
            "arms. The word config is June-exact (verified against the imported June cv_accuracy at "
            "random_state=0). The char control is the project's standing mandatory char-level surface "
            "control. The 5-seed CV sensitivity report is descriptive only."
        ),
    },
    "criteria": {                    # two-tier frozen criteria (replaces the single 0.10-margin dependency)
        "margin_definition": "M = (recovery_A - surface_A) - (recovery_D - surface_D); recovery = mean over judge passes K_A,K_D",
        "primary": {
            "margin_floor": 0.10,
            "alpha_one_sided": 0.01,
            "bootstrap": {"iterations": 10000, "ci_level": 0.95},
            "rule": (
                "M >= +0.10 AND one-sided paired sign-flip permutation p < 0.01 on paired per-row "
                "correctness (10,000 label-preserving permutations) AND bootstrap 95% CI of M excludes 0"
            ),
            "licenses": "the strong claim (verdict PASS_TKS_SUPERIORITY_LICENSED)",
        },
        "secondary": {
            "rule": "0 < M < 0.10 AND permutation p < 0.01 AND bootstrap 95% CI of M excludes 0",
            "licenses": "ONLY the wording: 'directionally supported below the pre-registered strong margin'",
        },
        "sanity": (
            "with n=280/arm the SE of the paired accuracy difference is ~0.042, so the +0.10 primary "
            "floor is ~2.4 SE"
        ),
    },
    "primary_margin_floor": 0.10,    # frozen BEFORE authoring
    "alpha_one_sided": 0.01,         # tightened from 0.05 per adversarial review, frozen BEFORE authoring
    "permutation_iterations": 10000,
    "bootstrap_iterations": 10000,
    "bootstrap_ci_level": 0.95,
    "guards": {
        "max_single_foundation_pred_share": 0.30,  # judge-collapse degeneracy guard (V6 spirit), per arm per pass
        "max_invalid_pred_rate": 0.05,             # per arm per pass
        "saturation_ceiling": 0.95,                # both arms above => ceiling, margin not interpretable
        "min_scored_rows_per_arm": 280,            # per pass
    },
    "banned_term_symmetry": (
        "Arm D source_banned_terms are derived with the SAME call signature as Arm A: "
        "source_terms_to_avoid(meaning, name) — compact_meaning + its shorthand label name, mirroring "
        "June's source_terms_to_avoid(original_tks_meaning, legacy_tks_name) for arm A."
    ),
    "inherent_asymmetry_disclosure": (
        "ASYMMETRY 2 (inherent to the manipulation, pre-registered): the original TKS definition text "
        "intersects the June validator's HARD_SOURCE_FORBIDDEN mystical vocabulary (13 terms measured, "
        "e.g. divine/sacred/soul), so Arm A authoring faces extra regeneration constraints Arm D never "
        "does. The direction of this pressure is AGAINST arm A (harder authoring), so it cannot "
        "manufacture an A win."
    ),
    "goemotion_floor_policy": (
        "descriptive_only: the June goemotion>=max(surface,0.50) floor is reported per arm but is NOT part of "
        "the primary endpoint (frozen choice (a); the winning June delink recipe scored goemotion 0.0786)."
    ),
    "known_june_flaws_fixed": [
        "June blind row ids encoded the answer (e.g. 'F1A_000'); this run uses opaque ids row_NNNN",
        "June arms were authored on different days; this run interleaves chunks A,D,A,D in one session",
        "June headline numbers came from different judges (flash vs pro); this run freezes one judge model for both arms",
        "June authoring had no reproducible seeds; this run derives the in-prompt variety seed deterministically",
        "June's judge anchored on the TKS choice set for both arms; this run crosses the choice key symmetrically",
    ],
    "adversarial_review_fixes_20260726": [
        "H1: per-arm surface baseline = max(word TF-IDF, char 3-5-gram), both 5-fold CV random_state=0, identical config across arms",
        "Two-tier frozen criteria: PRIMARY M>=0.10 & p<0.01 & bootstrap 95% CI excludes 0; SECONDARY 0<M<0.10 with same p+CI licenses only 'directionally supported below the pre-registered strong margin'",
        "H2: symmetric judge cross — passes K_A (TKS choice key) and K_D (compact choice key) over the same shuffled pool; per-arm recovery = mean over passes; June anchoring sentence removed (runtime-verified)",
        "A1: arm D banned terms derived with the same call signature as arm A: source_terms_to_avoid(meaning, name)",
        "A2: TKS-text intersection with HARD_SOURCE_FORBIDDEN pre-registered as inherent-to-manipulation disclosure (pressure direction AGAINST arm A)",
        "A3: template-identity guard is a real per-chunk byte-compare of paired prompts after stripping exactly the two injection segments; driver hard-fails on any diff",
        "Framing corrected: 'original TKS foundation wording vs generic drive+register shorthand composition', NOT 'original vs shortened' (compact 125-150 chars vs TKS 98-152)",
    ],
}

PRICES_PER_M = {  # USD per 1M tokens (input, output)
    "models/gemini-2.5-flash-lite": (0.10, 0.40),
    "models/gemini-2.5-flash": (0.30, 2.50),
    "models/gemini-2.5-pro": (1.25, 10.00),
    "models/gemini-3.1-pro-preview": (2.00, 12.00),
}

# ---------------------------------------------------------------- June imports


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import June module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


june_author = _load_module("june_author", JUNE_DIR / "author_confirmatory_chunks_gemini.py")
june_plan = _load_module("june_plan", JUNE_DIR / "build_confirmatory_authoring_plan_tks_original_delink.py")
june_judge = _load_module("june_judge", JUNE_DIR / "gate2_confirmatory_tks_original_blind.py")

# ---------------------------------------------------------------- helpers


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def verify_inputs() -> None:
    for path, expected in ((CANONICAL_TKS, CANONICAL_TKS_SHA256), (COMPACT_DEFS, COMPACT_DEFS_SHA256)):
        if not path.exists():
            raise SystemExit(f"required definition source missing: {path}")
        got = sha256_file(path)
        if got != expected:
            raise SystemExit(f"sha256 mismatch for {path}: expected {expected} got {got}")


# ---------------------------------------------------------------- plans (R1)


def foundations_for_arm(arm: str) -> list[dict[str, Any]]:
    """Both arms share every field except the definition text (and the banned
    terms mechanically derived from that text with the SAME call signature —
    a pre-registered, inherent part of the manipulation)."""
    if arm == "A":
        base = june_plan.load_original_foundations(CANONICAL_TKS)
        out = []
        for row in base:
            row = dict(row)
            row["authoring_profile"] = "matched_ab_delink_arm_a_v1"
            row["definition_label"] = f"{row['legacy_tks_id']} ({row['legacy_tks_name']})"
            row["definition_text"] = row["original_tks_meaning"]
            out.append(row)
        return out
    if arm == "D":
        payload = read_json(COMPACT_DEFS)
        out = []
        for item in payload["entries"]:
            meaning = item["compact_meaning"]
            label_name = f"{item['drive']}-{item['register']} shorthand"
            # ASYMMETRY 1 fix: same call signature as June arm A —
            # source_terms_to_avoid(meaning, name) — meaning + its name, both arms.
            banned = sorted(
                set(june_plan.CAS_BANNED_WORDS).union(june_plan.source_terms_to_avoid(meaning, label_name))
            )
            out.append(
                {
                    "foundation": item["foundation"],
                    "drive": item["drive"],
                    "drive_code": item["drive_code"],
                    "register": item["register"],
                    "register_code": item["register_code"],
                    "legacy_tks_id": f"compact-{item['foundation']}",
                    "legacy_tks_name": label_name,
                    "legacy_tks_world": "",
                    "legacy_tks_world_label": "",
                    "original_tks_meaning": meaning,  # field name kept for June-schema compatibility
                    "drive_definition": item["drive_definition"],
                    "register_definition": item["register_definition"],
                    "source_banned_terms": banned,
                    "authoring_profile": "matched_ab_delink_arm_d_v1",
                    "definition_label": f"compact-{item['foundation']} ({label_name})",
                    "definition_text": meaning,
                }
            )
        register_order = ["T", "A", "f", "E"]
        return sorted(out, key=lambda r: (int(r["drive_code"][1:]), register_order.index(r["register_code"])))
    raise SystemExit(f"unknown arm {arm}")


def authoring_instructions_template(
    n_rows: int, foundation: str, definition_label: str, definition_text: str, banned: list[str]
) -> str:
    """June's delink authoring_instructions() with exactly two injection points:
    the definition label and the definition text. Everything else byte-identical
    across arms (banned list is mechanically derived from the definition text)."""
    return (
        f"Author {n_rows} ordinary-world scenario prompts for hidden CAS/TKS Foundation {foundation}. "
        f"Private definition source: {definition_label}. "
        f"Private meaning: {definition_text} "
        "Use this private meaning only to shape the situation's logic. "
        "The visible scene must use the assigned neutral cover setting, task, and objects for each row. "
        "These same cover controls are reused across all 28 CAS/TKS classes, so do not make them class-specific. "
        "Do not print labels, ids, world names, emotion labels, religious/mystical language, or source vocabulary. "
        "Return JSON only: {\"rows\":[{\"id\":\"...\",\"prompt\":\"...\"}, ...]}. "
        f"Banned literal words include: {', '.join(banned)}."
    )


def build_arm_plan(arm: str) -> dict[str, Any]:
    foundations = foundations_for_arm(arm)
    n = FROZEN["n_per_foundation"]
    rows: list[dict[str, Any]] = []
    for foundation_index, foundation in enumerate(foundations):
        for row_index in range(n):
            emotion = june_plan.GOEMOTIONS[(foundation_index + row_index) % len(june_plan.GOEMOTIONS)]
            split = "train" if row_index < int(n * 0.8) else "test"  # June's 80/20, descriptive only
            rows.append(
                {
                    **foundation,
                    **june_plan.cover_fields(row_index),  # June exact => byte-identical cover controls across arms
                    # Row ids are ARM-INDEPENDENT so the paired authoring prompts are
                    # byte-identical outside the two injection segments (A3 guard).
                    # The arm lives in the 'arm' field and the chunk file location;
                    # the judge only ever sees opaque row_NNNN ids.
                    "id": f"{foundation['foundation']}_{row_index:03d}",
                    "arm": arm,
                    "goemotion": emotion,
                    "split": split,
                    "foundation_index": foundation_index,
                    "row_index": row_index,
                    "chunk_id": f"{arm}_{foundation['foundation']}_chunk_01",
                }
            )
    by_chunk: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_chunk[row["chunk_id"]].append(row)
    chunks = []
    for chunk_id in sorted(by_chunk):
        chunk_rows = by_chunk[chunk_id]
        first = chunk_rows[0]
        emotions = sorted({str(r["goemotion"]) for r in chunk_rows})
        banned = sorted(
            set(june_plan.CAS_BANNED_WORDS)
            .union(str(t) for t in first["source_banned_terms"])
            .union(*(june_plan.EMOTION_BANNED_WORDS[e] for e in emotions))
        )
        chunks.append(
            {
                "schema_version": "gate2_closure_matched_ab_chunk.v2",
                "authoring_profile": first["authoring_profile"],
                "arm": arm,
                "chunk_id": chunk_id,
                "foundation": first["foundation"],
                "legacy_tks_id": first["legacy_tks_id"],
                "legacy_tks_name": first["legacy_tks_name"],
                "source_banned_terms": first["source_banned_terms"],
                "row_count": len(chunk_rows),
                "rows": chunk_rows,
                "authoring_instructions": authoring_instructions_template(
                    len(chunk_rows),
                    str(first["foundation"]),
                    str(first["definition_label"]),
                    str(first["definition_text"]),
                    banned,
                ),
            }
        )
    plan = {
        "schema_version": "gate2_closure_matched_ab_plan.v2",
        "arm": arm,
        "arm_meaning": (
            "original TKS 28 subfoundation meanings"
            if arm == "A"
            else "generic drive+register shorthand compositions (compact texts; NOT shorter than TKS)"
        ),
        "date": FROZEN["date"],
        "status": "authoring_plan_only_not_a_fixture",
        "definition_source": str(CANONICAL_TKS if arm == "A" else COMPACT_DEFS),
        "definition_source_sha256": CANONICAL_TKS_SHA256 if arm == "A" else COMPACT_DEFS_SHA256,
        "row_plan": rows,
        "chunks": chunks,
        "important_limit": (
            "Authoring plan only. No claim is licensed until both arms are authored, Gate 1 runs per arm, "
            "the frozen blind judge cross scores the pooled shuffled 560 rows twice, and the pre-registered "
            "two-tier criteria compute."
        ),
    }
    return plan


# ---------------------------------------------------------------- seeds (R1 fix)


def variety_seed(foundation: str, batch_index: int, attempt: int) -> int:
    """Deterministic replacement for June's unseeded random.randint(100000, 999999).
    Keyed WITHOUT the arm so both arms get the same in-prompt seed schedule."""
    key = f"{FROZEN['base_seed']}|{foundation}|{batch_index}|{attempt}".encode()
    return 100000 + int(hashlib.sha256(key).hexdigest()[:12], 16) % 900000


def build_batch_prompt(chunk: dict[str, Any], batch_rows: list[dict[str, Any]], batch_index: int, attempt: int) -> tuple[str, int]:
    seed = variety_seed(str(chunk["foundation"]), batch_index, attempt)
    random.seed(seed)  # june prompt_for_chunk_delink draws its in-prompt seed from module random
    prompt = june_author.prompt_for_chunk_delink(chunk, batch_rows)
    return prompt, seed


# ---------------------------------------------------------------- template guard (A3 fix)

DEFINITION_LINE_MARKER = "ordinary-world scenario prompts for hidden CAS/TKS Foundation"
SOURCE_TERMS_MARKER = "Especially avoid these source terms:"


def _strip_injection_segments(prompt: str) -> tuple[str, dict[str, str]]:
    """Strip exactly the two injection segments from a built authoring prompt:
    (1) the definition line (June's authoring_instructions line, which carries
        the definition label, the definition text, and the banned literal list),
    (2) the 'Especially avoid these source terms' JSON line.
    Hard-fails unless each segment is found exactly once."""
    lines = prompt.split("\n")
    def_idx = [
        i for i, line in enumerate(lines) if line.startswith("Author ") and DEFINITION_LINE_MARKER in line
    ]
    marker_idx = [i for i, line in enumerate(lines) if line.endswith(SOURCE_TERMS_MARKER)]
    if len(def_idx) != 1:
        raise SystemExit(f"template guard: expected exactly 1 definition line, found {len(def_idx)}")
    if len(marker_idx) != 1:
        raise SystemExit(f"template guard: expected exactly 1 source-terms marker, found {len(marker_idx)}")
    ban_idx = marker_idx[0] + 1
    if ban_idx >= len(lines) or not lines[ban_idx].lstrip().startswith("["):
        raise SystemExit("template guard: source-terms JSON line not found after its marker")
    removed = {"definition_line": lines[def_idx[0]], "source_terms_line": lines[ban_idx]}
    kept = [line for i, line in enumerate(lines) if i not in {def_idx[0], ban_idx}]
    return "\n".join(kept), removed


def _first_diff_line(text_a: str, text_b: str) -> str:
    for i, (la, lb) in enumerate(zip(text_a.split("\n"), text_b.split("\n"))):
        if la != lb:
            return f"line {i}: A={la[:120]!r} D={lb[:120]!r}"
    return "length mismatch after common prefix"


def template_identity_guard(plan_a: dict[str, Any], plan_d: dict[str, Any]) -> dict[str, Any]:
    """REAL template-identity guard (replaces the earlier tautological check):
    for every paired authoring batch, build both arms' actual prompts
    (attempt 1, shared variety seed), strip exactly the two injection segments,
    and BYTE-COMPARE the remainders. Any diff hard-fails the driver.
    Also verifies cover controls and GoEmotions are identical per paired row."""
    chunks_a = {c["foundation"]: c for c in plan_a["chunks"]}
    chunks_d = {c["foundation"]: c for c in plan_d["chunks"]}
    if sorted(chunks_a) != sorted(chunks_d):
        raise SystemExit("template guard: arm foundation sets differ")
    batch_size = FROZEN["author_batch_size"]
    per_chunk: list[dict[str, Any]] = []
    mismatches: list[str] = []
    for foundation in sorted(chunks_a):
        ca, cd = chunks_a[foundation], chunks_d[foundation]
        batches_a = [ca["rows"][i : i + batch_size] for i in range(0, len(ca["rows"]), batch_size)]
        batches_d = [cd["rows"][i : i + batch_size] for i in range(0, len(cd["rows"]), batch_size)]
        if len(batches_a) != len(batches_d):
            raise SystemExit(f"template guard: batch count differs for {foundation}")
        for batch_index, (ba, bd) in enumerate(zip(batches_a, batches_d), start=1):
            prompt_a, seed_a = build_batch_prompt(ca, ba, batch_index, attempt=1)
            prompt_d, seed_d = build_batch_prompt(cd, bd, batch_index, attempt=1)
            remainder_a, removed_a = _strip_injection_segments(prompt_a)
            remainder_d, removed_d = _strip_injection_segments(prompt_d)
            byte_equal = remainder_a.encode("utf-8") == remainder_d.encode("utf-8")
            record = {
                "foundation": foundation,
                "batch_index": batch_index,
                "variety_seed_shared": seed_a == seed_d,
                "byte_equal_after_stripping_two_injection_segments": byte_equal,
                "remainder_bytes_arm_A": len(remainder_a.encode("utf-8")),
                "remainder_bytes_arm_D": len(remainder_d.encode("utf-8")),
                "remainder_sha256_arm_A": sha256_text(remainder_a),
                "remainder_sha256_arm_D": sha256_text(remainder_d),
                "stripped_definition_line_chars": {
                    "A": len(removed_a["definition_line"]),
                    "D": len(removed_d["definition_line"]),
                },
                "stripped_source_terms_line_chars": {
                    "A": len(removed_a["source_terms_line"]),
                    "D": len(removed_d["source_terms_line"]),
                },
            }
            if not byte_equal:
                record["first_diff"] = _first_diff_line(remainder_a, remainder_d)
                mismatches.append(f"{foundation} batch {batch_index}: {record['first_diff']}")
            if seed_a != seed_d:
                mismatches.append(f"{foundation} batch {batch_index}: variety seeds differ ({seed_a} vs {seed_d})")
            per_chunk.append(record)

    rows_a = {(r["foundation"], r["row_index"]): r for r in plan_a["row_plan"]}
    rows_d = {(r["foundation"], r["row_index"]): r for r in plan_d["row_plan"]}
    cover_identical = set(rows_a) == set(rows_d) and all(
        rows_a[k]["cover_setting"] == rows_d[k]["cover_setting"]
        and rows_a[k]["cover_task"] == rows_d[k]["cover_task"]
        and rows_a[k]["cover_objects"] == rows_d[k]["cover_objects"]
        and rows_a[k]["goemotion"] == rows_d[k]["goemotion"]
        and rows_a[k]["surface_frame_id"] == rows_d[k]["surface_frame_id"]
        and rows_a[k]["id"] == rows_d[k]["id"]
        for k in rows_a
    )
    if not cover_identical:
        mismatches.append("cover controls / GoEmotions / row ids not identical across arms")

    audit = {
        "schema_version": "gate2_closure_matched_ab_template_identity_audit.v2",
        "guard": (
            "for each paired authoring batch prompt, strip exactly the two injection segments "
            "(the definition line and the 'Especially avoid these source terms' JSON line) and "
            "byte-compare the remainders; driver hard-fails on any diff"
        ),
        "n_paired_prompts_compared": len(per_chunk),
        "n_byte_equal": sum(1 for r in per_chunk if r["byte_equal_after_stripping_two_injection_segments"]),
        "cover_controls_and_emotions_identical_across_arms": cover_identical,
        "n_paired_rows": len(rows_a),
        "per_chunk": per_chunk,
    }
    write_json(HERE / "template_identity_audit.json", audit)
    if mismatches:
        raise SystemExit(
            "TEMPLATE IDENTITY GUARD FAILED (audit written to template_identity_audit.json): "
            + "; ".join(mismatches[:5])
        )
    return audit


def assert_matched_ab_inputs(plan_a: dict[str, Any], plan_d: dict[str, Any]) -> None:
    """Dual-arm replacement for June's assert_original_tks_inputs (which would
    hard-stop arm D). Verifies each arm is backed by its own sha256-pinned
    definition source and that row counts match. Template identity is enforced
    separately by template_identity_guard (real byte-compare)."""
    canon = {item["meaning"] for item in read_json(CANONICAL_TKS)}
    compact = {item["compact_meaning"] for item in read_json(COMPACT_DEFS)["entries"]}
    bad_a = [r["id"] for r in plan_a["row_plan"] if r["original_tks_meaning"] not in canon]
    bad_d = [r["id"] for r in plan_d["row_plan"] if r["original_tks_meaning"] not in compact]
    if bad_a:
        raise SystemExit(f"arm A rows not backed by canon defs; first: {bad_a[:5]}")
    if bad_d:
        raise SystemExit(f"arm D rows not backed by compact defs; first: {bad_d[:5]}")
    if len(plan_a["row_plan"]) != len(plan_d["row_plan"]):
        raise SystemExit("arm row counts differ")


# ---------------------------------------------------------------- authoring (interleaved)


def interleaved_chunk_queue(plan_a: dict[str, Any], plan_d: dict[str, Any]) -> list[dict[str, Any]]:
    chunks_a = sorted(plan_a["chunks"], key=lambda c: c["chunk_id"])
    chunks_d = sorted(plan_d["chunks"], key=lambda c: c["chunk_id"])
    queue: list[dict[str, Any]] = []
    for a, d in zip(chunks_a, chunks_d):
        queue.append(a)
        queue.append(d)
    return queue


def author_all(queue: list[dict[str, Any]], model_name: str, dry_run: bool) -> dict[str, Any]:
    transcripts_path = HERE / ("authoring_prompts_dryrun.jsonl" if dry_run else "authoring_prompts.jsonl")
    transcripts_path.parent.mkdir(parents=True, exist_ok=True)
    model = None
    if not dry_run:
        import google.generativeai as genai  # noqa: deferred so --dry-run never needs it

        import os

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY is required for a real run")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

    stats = {"planned_requests": 0, "input_tokens_est": 0, "output_tokens_est": 0, "chunks_ok": 0, "chunks_failed": []}
    with transcripts_path.open("w", encoding="utf-8", newline="\n") as log:
        for chunk in queue:
            arm = chunk["arm"]
            out_dir = HERE / f"chunks_{arm}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{chunk['chunk_id']}.json"
            if not dry_run and out_path.exists():
                payload = read_json(out_path)
                if not payload.get("failed") and not payload.get("validation_errors"):
                    stats["chunks_ok"] += 1
                    print(f"resume-ok {chunk['chunk_id']}")
                    continue
            batch_size = FROZEN["author_batch_size"]
            batches = [chunk["rows"][i : i + batch_size] for i in range(0, len(chunk["rows"]), batch_size)]
            authored_rows: list[dict[str, str]] = []
            chunk_failed = False
            for batch_index, batch in enumerate(batches, start=1):
                last_error = ""
                success = False
                for attempt in range(1, FROZEN["retries"] + 1):
                    prompt, seed = build_batch_prompt(chunk, batch, batch_index, attempt)
                    log.write(
                        json.dumps(
                            {
                                "arm": arm,
                                "chunk_id": chunk["chunk_id"],
                                "batch_index": batch_index,
                                "attempt": attempt,
                                "variety_seed": seed,
                                "model": model_name,
                                "dry_run": dry_run,
                                "prompt_chars": len(prompt),
                                "prompt": prompt,
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    if attempt == 1:
                        stats["planned_requests"] += 1
                        stats["input_tokens_est"] += est_tokens(prompt)
                        # ~85 words/row * 1.4 tokens/word + JSON overhead
                        stats["output_tokens_est"] += len(batch) * 130 + 40
                    if dry_run:
                        success = True
                        break
                    try:
                        response = model.generate_content(
                            prompt, generation_config=dict(FROZEN["author_generation_config"])
                        )
                        payload = june_author.extract_json(response.text)
                        errors = june_author.validate_chunk_payload(chunk, payload, batch)
                        if not errors:
                            authored_rows.extend(payload["rows"])
                            success = True
                            break
                        last_error = "; ".join(errors[:8])
                    except Exception as exc:  # noqa: BLE001 — June parity
                        last_error = f"{type(exc).__name__}: {exc}"
                    if attempt < FROZEN["retries"]:
                        time.sleep(FROZEN["retry_sleep_s"] * attempt)
                if not success and not dry_run:
                    write_json(
                        out_path,
                        {
                            "schema_version": "gate2_closure_matched_ab_chunk_result.v2",
                            "chunk_id": chunk["chunk_id"],
                            "arm": arm,
                            "model": model_name,
                            "failed": True,
                            "failed_batch": batch_index,
                            "last_error": last_error,
                            "generated_at_epoch": int(time.time()),
                            "rows": authored_rows,
                        },
                    )
                    stats["chunks_failed"].append(chunk["chunk_id"])
                    chunk_failed = True
                    break
            if dry_run or chunk_failed:
                continue
            payload = {"rows": authored_rows}
            errors = june_author.validate_chunk_payload(chunk, payload)
            write_json(
                out_path,
                {
                    "schema_version": "gate2_closure_matched_ab_chunk_result.v2",
                    "chunk_id": chunk["chunk_id"],
                    "arm": arm,
                    "model": model_name,
                    "generated_at_epoch": int(time.time()),
                    "validation_errors": errors,
                    "rows": authored_rows,
                },
            )
            if errors:
                stats["chunks_failed"].append(chunk["chunk_id"])
            else:
                stats["chunks_ok"] += 1
                print(f"ok {chunk['chunk_id']}")
    return stats


# ---------------------------------------------------------------- assemble + gate1 (R3)


def assemble_arm(arm: str, plan: dict[str, Any], model_name: str) -> Path:
    plan_by_id = {row["id"]: row for row in plan["row_plan"]}
    out_dir = HERE / f"chunks_{arm}"
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    failed: list[str] = []
    for chunk in plan["chunks"]:
        path = out_dir / f"{chunk['chunk_id']}.json"
        if not path.exists():
            missing.append(chunk["chunk_id"])
            continue
        payload = read_json(path)
        if payload.get("failed") or payload.get("validation_errors"):
            failed.append(chunk["chunk_id"])
            continue
        for authored in payload["rows"]:
            base = dict(plan_by_id[authored["id"]])
            base["prompt"] = " ".join(authored["prompt"].split())
            base["authoring_provenance"] = "gate2_closure_matched_ab_v2"
            base["authoring_model"] = model_name
            base["authoring_chunk_file"] = str(path)
            rows.append(base)
    if missing or failed:
        raise SystemExit(f"arm {arm} incomplete: missing={missing[:5]} failed={failed[:5]}")
    fixture_path = HERE / f"fixture_arm_{arm}.json"
    write_json(
        fixture_path,
        {
            "fixture_family": "gate2_closure_matched_ab_v2",
            "arm": arm,
            "authoring_model": model_name,
            "important_limit": (
                "Model-authored synthetic fixture. Must pass Gate 1 per arm and the pooled symmetric "
                "judge cross before the pre-registered two-tier criteria mean anything."
            ),
            "validation": {
                "rows": len(rows),
                "foundation": dict(sorted(Counter(r["foundation"] for r in rows).items())),
                "goemotion": dict(sorted(Counter(r["goemotion"] for r in rows).items())),
            },
            "rows": rows,
        },
    )
    write_json(
        HERE / f"fixture_arm_{arm}_manifest.json",
        {"fixture": str(fixture_path), "fixture_sha256": sha256_file(fixture_path), "rows": len(rows)},
    )
    return fixture_path


def _surface_cv_accuracy(
    texts: list[str], labels: list[str], vectorizer_config: dict[str, Any], random_state: int
) -> float:
    """Frozen surface-baseline CV (word or char config), parameterized random_state.
    Identical pipeline shape to June's cv_accuracy; the word config at
    random_state=0 is runtime-verified to reproduce the June value exactly."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.pipeline import make_pipeline

    cfg = dict(vectorizer_config)
    cfg["ngram_range"] = tuple(cfg["ngram_range"])
    min_class = min(Counter(labels).values())
    folds = min(int(FROZEN["surface_control"]["cv"]["n_splits"]), min_class)
    if folds < 2:
        raise SystemExit("each label needs at least 2 rows for CV")
    pipe = make_pipeline(
        TfidfVectorizer(**cfg),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_state)
    return float(cross_val_score(pipe, texts, labels, cv=cv, scoring="accuracy").mean())


def gate1_arm(arm: str, fixture_path: Path) -> dict[str, Any]:
    june_gate = _load_module("june_gate", JUNE_DIR / "surface_gate_f28_goemotions.py")  # lazy: needs sklearn
    rows = june_gate.load_rows(fixture_path)
    raw = [row["prompt"] for row in rows]
    stripped = june_gate.strip_texts(raw)
    foundation = [r["foundation"] for r in rows]
    goemotion = [r["goemotion"] for r in rows]
    sc = FROZEN["surface_control"]
    rs = int(sc["cv"]["random_state"])

    word_results = {
        "foundation_raw": june_gate.cv_accuracy(raw, foundation),
        "foundation_answer_stripped": june_gate.cv_accuracy(stripped, foundation),
        "goemotion_raw": june_gate.cv_accuracy(raw, goemotion),
        "goemotion_answer_stripped": june_gate.cv_accuracy(stripped, goemotion),
        "drive_answer_stripped": june_gate.cv_accuracy(stripped, [r["drive"] for r in rows]),
        "register_answer_stripped": june_gate.cv_accuracy(stripped, [r["register"] for r in rows]),
    }
    # config-fidelity check: the parameterized replica must reproduce June's number at random_state=0
    replica = _surface_cv_accuracy(stripped, foundation, sc["word_vectorizer"], rs)
    if abs(replica - word_results["foundation_answer_stripped"]) > 1e-12:
        raise SystemExit(
            f"arm {arm}: word-baseline replica ({replica}) does not reproduce June cv_accuracy "
            f"({word_results['foundation_answer_stripped']}); surface-control config drift"
        )
    char_results = {
        "foundation_answer_stripped": _surface_cv_accuracy(stripped, foundation, sc["char_vectorizer"], rs),
        "goemotion_answer_stripped": _surface_cv_accuracy(stripped, goemotion, sc["char_vectorizer"], rs),
    }
    surface = {
        "rule": sc["rule"],
        "foundation_answer_stripped": max(
            word_results["foundation_answer_stripped"], char_results["foundation_answer_stripped"]
        ),
        "goemotion_answer_stripped": max(
            word_results["goemotion_answer_stripped"], char_results["goemotion_answer_stripped"]
        ),
        "components": {
            "word_foundation": word_results["foundation_answer_stripped"],
            "char_foundation": char_results["foundation_answer_stripped"],
            "word_goemotion": word_results["goemotion_answer_stripped"],
            "char_goemotion": char_results["goemotion_answer_stripped"],
        },
    }
    seeds = list(sc["cv_seed_sensitivity_seeds"])
    sensitivity = {
        "seeds": seeds,
        "foundation_answer_stripped": {
            "word": [_surface_cv_accuracy(stripped, foundation, sc["word_vectorizer"], s) for s in seeds],
            "char": [_surface_cv_accuracy(stripped, foundation, sc["char_vectorizer"], s) for s in seeds],
        },
        "note": (
            "descriptive only (pre-registered): the primary surface numbers use random_state=0; "
            "this report shows CV-seed spread for the two surface numbers entering surface_X"
        ),
    }
    result = {
        "schema_version": "gate2_closure_matched_ab_surface_gate.v2",
        "arm": arm,
        "fixture": str(fixture_path),
        "fixture_sha256": sha256_file(fixture_path),
        "threshold": FROZEN["gate1_threshold"],
        "word_results": word_results,
        "char_results": char_results,
        "surface": surface,
        "cv_seed_sensitivity": sensitivity,
    }
    result["verdict"] = (
        "PASS"
        if surface["foundation_answer_stripped"] <= FROZEN["gate1_threshold"]
        and surface["goemotion_answer_stripped"] <= FROZEN["gate1_threshold"]
        else "BLOCKED_TEXT_BASELINE_TOO_HIGH"
    )
    write_json(HERE / f"gate1_arm_{arm}.json", result)
    return result


# ---------------------------------------------------------------- blind pool (R2)


def blind_prep(fixtures: dict[str, Path] | None, plans: dict[str, dict[str, Any]], dry_run: bool) -> dict[str, Any]:
    """Pool both arms, assign OPAQUE ids, seeded shuffle, no arm labels.
    Fixes June's id leak (June blind ids were e.g. 'F1A_000')."""
    pooled: list[dict[str, Any]] = []
    if dry_run:
        for arm, plan in plans.items():
            for row in plan["row_plan"]:
                pooled.append({**row, "prompt": None})
    else:
        for arm, fixture_path in fixtures.items():
            for row in read_json(fixture_path)["rows"]:
                pooled.append(row)
    # deterministic pre-shuffle order: plan ids are shared across arms by design,
    # so sort by (id, arm) to keep the order fully specified
    pooled.sort(key=lambda r: (r["id"], r["arm"]))
    rng = random.Random(FROZEN["base_seed"] * 1000003 + 17)
    rng.shuffle(pooled)
    blind_rows = []
    key = {}
    for k, row in enumerate(pooled):
        opaque = f"row_{k:04d}"
        blind_rows.append({"id": opaque, "prompt": row["prompt"]})
        key[opaque] = {
            "arm": row["arm"],
            "source_id": row["id"],
            "foundation": row["foundation"],
            "drive": row["drive"],
            "register": row["register"],
            "goemotion": row["goemotion"],
            "row_index": row["row_index"],
        }
    suffix = "_dryrun" if dry_run else ""
    write_json(HERE / f"blind_pool{suffix}.json", blind_rows)
    write_json(HERE / f"blind_key{suffix}.json", key)
    write_json(
        HERE / f"blind_permutation{suffix}.json",
        {"shuffle_seed": FROZEN["base_seed"] * 1000003 + 17, "order": [r["id"] for r in blind_rows], "n": len(blind_rows)},
    )
    return {"rows": len(blind_rows)}


# ---------------------------------------------------------------- judge (R2, symmetric cross)

ANCHOR_SENTENCE = "Use the original TKS meanings below, not shorthand drive/register summaries.\n"
HEADER_OLD = "Foundation options from original TKS definitions:"
HEADER_NEW = "Foundation options:"
MEANING_FIELD_OLD = '"original_tks_meaning":'
MEANING_FIELD_NEW = '"meaning":'


def neutralize_judge_prompt(prompt: str) -> str:
    """Apply the three pre-registered symmetric neutralizations to June's judge
    prompt (identical treatment for BOTH passes), verified by occurrence counts:
    1. remove the choice-set anchoring sentence,
    2. neutralize the 'from original TKS definitions' header,
    3. rename the 'original_tks_meaning' field to 'meaning'."""
    if prompt.count(ANCHOR_SENTENCE) != 1:
        raise SystemExit(
            f"judge-prompt neutralization: anchoring sentence found {prompt.count(ANCHOR_SENTENCE)} times, expected 1"
        )
    prompt = prompt.replace(ANCHOR_SENTENCE, "")
    if prompt.count(HEADER_OLD) != 1:
        raise SystemExit(
            f"judge-prompt neutralization: TKS header found {prompt.count(HEADER_OLD)} times, expected 1"
        )
    prompt = prompt.replace(HEADER_OLD, HEADER_NEW)
    n_fields = prompt.count(MEANING_FIELD_OLD)
    if n_fields != 28:
        raise SystemExit(
            f"judge-prompt neutralization: meaning field found {n_fields} times, expected 28"
        )
    prompt = prompt.replace(MEANING_FIELD_OLD, MEANING_FIELD_NEW)
    return prompt


def compact_foundation_choices() -> dict[str, dict[str, str]]:
    """Choice set for pass K_D: the compact drive+register shorthand compositions,
    in the same structure june_judge.judge_prompt expects."""
    payload = read_json(COMPACT_DEFS)
    choices: dict[str, dict[str, str]] = {}
    for item in payload["entries"]:
        foundation = item["foundation"]
        choices[foundation] = {
            "foundation": foundation,
            "legacy_tks_id": f"compact-{foundation}",
            "legacy_tks_name": f"{item['drive']}-{item['register']} shorthand",
            "drive": item["drive"],
            "register": item["register"],
            "meaning": item["compact_meaning"],
        }
    return dict(sorted(choices.items()))


import judge_parse_repair  # apparatus-level JSON repair; see its docstring


def judge_choices(pass_key: str) -> dict[str, dict[str, str]]:
    if pass_key == "K_A":
        return june_judge.load_foundation_choices(CANONICAL_TKS)
    if pass_key == "K_D":
        return compact_foundation_choices()
    raise SystemExit(f"unknown judge pass {pass_key}")


def judge_all(model_name: str, pass_key: str) -> None:
    import os

    import google.generativeai as genai  # noqa: deferred

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY is required for a real run")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    choices = judge_choices(pass_key)
    blind_rows = read_json(HERE / "blind_pool.json")
    preds_path = HERE / f"judge_preds_{pass_key}.json"
    predictions: list[dict[str, str]] = []
    if preds_path.exists():
        predictions = [row for row in read_json(preds_path) if isinstance(row, dict)]
    seen = {str(r.get("id")) for r in predictions}
    todo = [r for r in blind_rows if r["id"] not in seen]
    transcripts = HERE / f"judge_prompts_{pass_key}.jsonl"
    with transcripts.open("a", encoding="utf-8", newline="\n") as log:
        for offset in range(0, len(todo), FROZEN["judge_batch_size"]):
            batch = todo[offset : offset + FROZEN["judge_batch_size"]]
            prompt = neutralize_judge_prompt(june_judge.judge_prompt(batch, choices))
            log.write(
                json.dumps(
                    {
                        "pass": pass_key,
                        "offset": offset,
                        "model": model_name,
                        "ids": [r["id"] for r in batch],
                        "prompt": prompt,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            last_error = ""
            for attempt in range(1, FROZEN["retries"] + 1):
                try:
                    response = model.generate_content(
                        prompt, generation_config=dict(FROZEN["judge_generation_config"])
                    )
                    payload = judge_parse_repair.robust_extract_json(
                        response.text, june_judge.extract_json,
                        context={"pass": pass_key, "offset": offset, "attempt": attempt},
                    )
                    errors = june_judge.validate_preds(batch, payload, choices)
                    if not errors:
                        for row in payload["rows"]:
                            rid = str(row.get("id"))
                            if rid in seen:
                                continue
                            predictions.append(row)
                            seen.add(rid)
                        write_json(preds_path, predictions)
                        print(f"judged[{pass_key}] {len(predictions)}/{len(blind_rows)}", flush=True)
                        break
                    last_error = "; ".join(errors[:5])
                except Exception as exc:  # noqa: BLE001 — June parity
                    last_error = f"{type(exc).__name__}: {exc}"
                if attempt < FROZEN["retries"]:
                    time.sleep(FROZEN["retry_sleep_s"] * attempt)
            else:
                raise SystemExit(f"judge pass {pass_key} failed at offset {offset}: {last_error}")


# ---------------------------------------------------------------- score (R3/R4)


def paired_sign_flip_permutation(diffs: list[float], iterations: int, seed: int) -> float:
    observed = sum(diffs) / len(diffs)
    rng = random.Random(seed)
    at_least = 0
    for _ in range(iterations):
        total = 0.0
        for d in diffs:
            total += d if rng.random() < 0.5 else -d
        if total / len(diffs) >= observed:
            at_least += 1
    return (at_least + 1) / (iterations + 1)


def bootstrap_margin_ci(
    diffs: list[float], surface_offset: float, iterations: int, ci_level: float, seed: int
) -> tuple[float, float]:
    """Percentile bootstrap CI of the de-leaked margin M: resample the 280 pairs
    with replacement; each resample's statistic = mean(d_i) - (surface_A -
    surface_D), with the surface terms held as fixed arm-level point estimates
    (pre-registered convention, consistent with the margin definition)."""
    rng = random.Random(seed)
    n = len(diffs)
    stats: list[float] = []
    for _ in range(iterations):
        total = 0.0
        for _ in range(n):
            total += diffs[rng.randrange(n)]
        stats.append(total / n - surface_offset)
    stats.sort()
    lo_idx = max(0, int(((1.0 - ci_level) / 2.0) * iterations))
    hi_idx = min(iterations - 1, int((1.0 - (1.0 - ci_level) / 2.0) * iterations) - 1)
    return stats[lo_idx], stats[hi_idx]


def score_all(models_used: dict[str, str]) -> dict[str, Any]:
    choices_a = june_judge.load_foundation_choices(CANONICAL_TKS)
    label_map = {f: {"drive": c["drive"], "register": c["register"]} for f, c in choices_a.items()}
    key = read_json(HERE / "blind_key.json")
    preds_by_pass: dict[str, dict[str, dict[str, Any]]] = {}
    for pass_key in JUDGE_PASSES:
        preds_raw = read_json(HERE / f"judge_preds_{pass_key}.json")
        by_id: dict[str, dict[str, Any]] = {}
        for row in preds_raw:
            if isinstance(row, dict) and str(row.get("id")) not in by_id:
                by_id[str(row.get("id"))] = row
        preds_by_pass[pass_key] = by_id

    per_arm_pass: dict[str, dict[str, dict[str, Any]]] = {
        arm: {
            pass_key: {"n": 0, "fnd": 0, "drv": 0, "reg": 0, "emo": 0, "invalid": 0, "pred_share": Counter()}
            for pass_key in JUDGE_PASSES
        }
        for arm in FROZEN["arms"]
    }
    combined_correct: dict[str, dict[tuple[str, int], float]] = {arm: {} for arm in FROZEN["arms"]}
    row_records = []
    for rid in sorted(key):
        truth = key[rid]
        arm = truth["arm"]
        rec: dict[str, Any] = {
            "id": rid,
            "arm": arm,
            "source_id": truth["source_id"],
            "truth_foundation": truth["foundation"],
            "truth_goemotion": truth["goemotion"],
        }
        per_pass_correct: dict[str, int] = {}
        for pass_key in JUDGE_PASSES:
            pred = preds_by_pass[pass_key].get(rid)
            if pred is None:
                continue
            stats = per_arm_pass[arm][pass_key]
            stats["n"] += 1
            pf = str(pred.get("foundation", "")).strip()
            pe = str(pred.get("goemotion", "")).strip().lower()
            stats["pred_share"][pf] += 1
            stats["invalid"] += int(pf not in label_map)
            got_fnd = pf == truth["foundation"]
            stats["fnd"] += int(got_fnd)
            stats["drv"] += int(label_map.get(pf, {}).get("drive") == truth["drive"])
            stats["reg"] += int(label_map.get(pf, {}).get("register") == truth["register"])
            stats["emo"] += int(pe == truth["goemotion"].lower())
            per_pass_correct[pass_key] = int(got_fnd)
            rec[f"pred_foundation_{pass_key}"] = pf
            rec[f"foundation_correct_{pass_key}"] = got_fnd
        if len(per_pass_correct) == len(JUDGE_PASSES):
            c = sum(per_pass_correct.values()) / len(JUDGE_PASSES)
            combined_correct[arm][(truth["foundation"], truth["row_index"])] = c
            rec["foundation_correct_mean"] = c
        row_records.append(rec)

    gate1 = {arm: read_json(HERE / f"gate1_arm_{arm}.json") for arm in FROZEN["arms"]}
    summary_arms = {}
    guard_failures: list[str] = []
    for arm in FROZEN["arms"]:
        pass_summaries = {}
        for pass_key in JUDGE_PASSES:
            s = per_arm_pass[arm][pass_key]
            n = s["n"] or 1
            max_share = max(s["pred_share"].values()) / n if s["pred_share"] else 0.0
            pass_summaries[pass_key] = {
                "n": s["n"],
                "accuracy": {
                    "foundation": s["fnd"] / n,
                    "drive": s["drv"] / n,
                    "register": s["reg"] / n,
                    "goemotion": s["emo"] / n,
                },
                "invalid_pred_rate": s["invalid"] / n,
                "max_single_foundation_pred_share": max_share,
            }
            if s["n"] < FROZEN["guards"]["min_scored_rows_per_arm"]:
                guard_failures.append(
                    f"arm {arm} pass {pass_key}: scored rows {s['n']} < {FROZEN['guards']['min_scored_rows_per_arm']}"
                )
            if s["invalid"] / n > FROZEN["guards"]["max_invalid_pred_rate"]:
                guard_failures.append(f"arm {arm} pass {pass_key}: invalid pred rate {s['invalid']/n:.3f} > cap")
            if max_share > FROZEN["guards"]["max_single_foundation_pred_share"]:
                guard_failures.append(
                    f"arm {arm} pass {pass_key}: judge collapse, max pred share {max_share:.3f} > cap"
                )
        mean_acc = {
            metric: sum(pass_summaries[p]["accuracy"][metric] for p in JUDGE_PASSES) / len(JUDGE_PASSES)
            for metric in ("foundation", "drive", "register", "goemotion")
        }
        surface_f = float(gate1[arm]["surface"]["foundation_answer_stripped"])
        surface_g = float(gate1[arm]["surface"]["goemotion_answer_stripped"])
        summary_arms[arm] = {
            "per_pass": pass_summaries,
            "accuracy_mean_over_passes": mean_acc,
            "surface": {
                "rule": gate1[arm]["surface"]["rule"],
                "foundation_answer_stripped": surface_f,
                "goemotion_answer_stripped": surface_g,
                "components": gate1[arm]["surface"]["components"],
            },
            "deleaked_foundation": mean_acc["foundation"] - surface_f,
            "june_descriptive_verdict": (
                "PASS"
                if mean_acc["foundation"] >= max(surface_f, 0.35) and mean_acc["goemotion"] >= max(surface_g, 0.50)
                else "CHECK"
            ),
            "gate1_verdict": gate1[arm]["verdict"],
        }

    # paired per-row foundation-correctness differences (A - D), pairs by (foundation, row_index);
    # per-row correctness = mean over the two judge passes, so d_i in {-1,-0.5,0,0.5,1}
    diffs: list[float] = []
    for pair_key, a_val in combined_correct["A"].items():
        d_val = combined_correct["D"].get(pair_key)
        if d_val is not None:
            diffs.append(a_val - d_val)
    perm_seed = FROZEN["base_seed"] * 7919 + 42
    boot_seed = FROZEN["base_seed"] * 104729 + 7
    p_value = (
        paired_sign_flip_permutation(diffs, FROZEN["permutation_iterations"], perm_seed) if diffs else 1.0
    )
    surface_offset = (
        summary_arms["A"]["surface"]["foundation_answer_stripped"]
        - summary_arms["D"]["surface"]["foundation_answer_stripped"]
    )
    deleaked_margin = summary_arms["A"]["deleaked_foundation"] - summary_arms["D"]["deleaked_foundation"]
    if diffs:
        ci_low, ci_high = bootstrap_margin_ci(
            diffs, surface_offset, FROZEN["bootstrap_iterations"], FROZEN["bootstrap_ci_level"], boot_seed
        )
    else:
        ci_low, ci_high = -1.0, 1.0
    ci_excludes_zero = ci_low > 0.0

    blocked = [arm for arm in FROZEN["arms"] if summary_arms[arm]["gate1_verdict"] != "PASS"]
    saturated = all(
        summary_arms[arm]["accuracy_mean_over_passes"]["foundation"] >= FROZEN["guards"]["saturation_ceiling"]
        for arm in FROZEN["arms"]
    )
    stat_floor = p_value < FROZEN["alpha_one_sided"] and ci_excludes_zero
    if blocked:
        verdict = "BLOCKED_SURFACE"
    elif guard_failures:
        verdict = "NOT_LICENSED_DEGENERATE"
    elif saturated:
        verdict = "NOT_LICENSED_CEILING"
    elif deleaked_margin >= FROZEN["primary_margin_floor"] and stat_floor:
        verdict = "PASS_TKS_SUPERIORITY_LICENSED"
    elif 0.0 < deleaked_margin < FROZEN["primary_margin_floor"] and stat_floor:
        verdict = "SECONDARY_DIRECTIONAL_SUPPORT"
    else:
        verdict = "FAIL_NO_LICENSED_SUPERIORITY"

    licensed_wording = {
        "PASS_TKS_SUPERIORITY_LICENSED": (
            "LICENSED (fixture-level only): under a matched single-session A/B in which both arms were authored by "
            "the same pinned model from one template differing only in definition text, scenario prompts authored "
            "from original TKS foundation wording carried more blind-judge-recoverable class meaning than prompts "
            "authored from generic drive+register shorthand compositions, beyond each arm's own surface baseline "
            "(max of word TF-IDF and char 3-5-gram), symmetric over both judge choice keys (per-arm recovery = mean "
            f"over passes K_A and K_D; de-leaked margin >= {FROZEN['primary_margin_floor']}, one-sided paired "
            f"permutation p < {FROZEN['alpha_one_sided']}, bootstrap 95% CI of the margin excluding 0). "
            "This licenses NO hidden-state, GPU-probe, or model-internals claim, and NO claim that the TKS grid "
            "itself is 'derived' or uniquely correct. The manipulation is wording provenance, not length: the "
            "compact texts are NOT shorter (125-150 chars vs TKS 98-152)."
        ),
        "SECONDARY_DIRECTIONAL_SUPPORT": (
            "SECONDARY TIER ONLY: the pre-registered strong margin (>= "
            f"{FROZEN['primary_margin_floor']}) was NOT met. The ONLY licensed wording is: 'directionally "
            "supported below the pre-registered strong margin' (margin > 0, one-sided paired permutation p < "
            f"{FROZEN['alpha_one_sided']}, bootstrap 95% CI excluding 0, margin < "
            f"{FROZEN['primary_margin_floor']}). The strong claim 'original TKS foundation wording beats generic "
            "drive+register shorthand composition' is NOT licensed. This licenses NO hidden-state, GPU-probe, or "
            "model-internals claim."
        ),
        "FAIL_NO_LICENSED_SUPERIORITY": (
            "NOT LICENSED: the matched A/B cleared neither the pre-registered PRIMARY tier (margin >= "
            f"{FROZEN['primary_margin_floor']} with p < {FROZEN['alpha_one_sided']} and CI excluding 0) nor the "
            "SECONDARY tier (positive margin with the same statistical floors). The June 63.57%-vs-15.71% "
            "comparison remains NOT LICENSED, and 'original TKS foundation wording beats generic drive+register "
            "shorthand composition' may not be claimed in any form from this campaign. Descriptive per-arm "
            "numbers may be reported only with this verdict attached."
        ),
    }

    results = {
        "schema_version": "gate2_closure_matched_ab_result.v2",
        "date": FROZEN["date"],
        "frozen_config": FROZEN,
        "models_used": models_used,
        "arms": summary_arms,
        "primary_endpoint": {
            "definition": (
                "M = (recovery_A - surface_A) - (recovery_D - surface_D); recovery = foundation accuracy "
                "averaged over judge passes K_A and K_D; surface = max(word TF-IDF, char 3-5-gram), "
                "answer-stripped, per arm"
            ),
            "deleaked_margin_observed": deleaked_margin,
            "margin_floor_primary": FROZEN["primary_margin_floor"],
            "paired_permutation": {
                "n_pairs": len(diffs),
                "iterations": FROZEN["permutation_iterations"],
                "seed": perm_seed,
                "p_one_sided": p_value,
                "alpha": FROZEN["alpha_one_sided"],
                "note": (
                    "sign-flip (label-preserving) test on per-pair foundation-correctness differences (A - D), "
                    "per-row correctness averaged over the two judge passes; surface subtraction enters the "
                    "margin criterion as arm-level point estimates (pre-registered convention)"
                ),
            },
            "bootstrap": {
                "iterations": FROZEN["bootstrap_iterations"],
                "ci_level": FROZEN["bootstrap_ci_level"],
                "seed": boot_seed,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "excludes_zero": ci_excludes_zero,
                "note": "percentile bootstrap over pairs; surface offset held fixed (pre-registered convention)",
            },
            "criteria": FROZEN["criteria"],
        },
        "guard_failures": guard_failures,
        "verdict": verdict,
        "licensed_wording": licensed_wording.get(verdict, licensed_wording["FAIL_NO_LICENSED_SUPERIORITY"]),
        "rows": row_records,
    }
    write_json(HERE / "results_matched_ab.json", results)
    printable = {k: v for k, v in results.items() if k != "rows"}
    print(json.dumps(printable, indent=2, sort_keys=True))
    return results


# ---------------------------------------------------------------- cost (R6)


def cost_report(author_stats: dict[str, Any], n_blind_rows: int) -> dict[str, Any]:
    placeholder_prompt = " ".join(["word"] * 90)
    sample_batch = [{"id": f"row_{i:04d}", "prompt": placeholder_prompt} for i in range(FROZEN["judge_batch_size"])]
    calls_per_pass = (n_blind_rows + FROZEN["judge_batch_size"] - 1) // FROZEN["judge_batch_size"]
    pass_prompt_tokens = {}
    judge_in = 0
    for pass_key in JUDGE_PASSES:
        choices = judge_choices(pass_key)
        # building + neutralizing here also exercises the runtime neutralization checks in dry-run
        tok = est_tokens(neutralize_judge_prompt(june_judge.judge_prompt(sample_batch, choices)))
        pass_prompt_tokens[pass_key] = tok
        judge_in += calls_per_pass * tok
    judge_calls = calls_per_pass * len(JUDGE_PASSES)
    judge_out = judge_calls * (FROZEN["judge_batch_size"] * 25 + 20)

    def usd(model: str, tokens_in: int, tokens_out: int) -> float:
        p_in, p_out = PRICES_PER_M[model]
        return tokens_in / 1e6 * p_in + tokens_out / 1e6 * p_out

    retry_factor = 1.5  # worst-case retry inflation
    author_in = int(author_stats["input_tokens_est"] * retry_factor)
    author_out = int(author_stats["output_tokens_est"] * retry_factor)
    report = {
        "authoring": {
            "requests_planned": author_stats["planned_requests"],
            "input_tokens_est_with_retries": author_in,
            "output_tokens_est_with_retries": author_out,
            "model": FROZEN["author_model"],
            "usd_est": round(usd(FROZEN["author_model"], author_in, author_out), 4),
        },
        "judging": {
            "requests_planned": judge_calls,
            "passes": len(JUDGE_PASSES),
            "calls_per_pass": calls_per_pass,
            "prompt_tokens_per_call_by_pass": pass_prompt_tokens,
            "input_tokens_est": int(judge_in * retry_factor),
            "output_tokens_est": int(judge_out * retry_factor),
            "model": FROZEN["judge_model"],
            "usd_est": round(usd(FROZEN["judge_model"], int(judge_in * retry_factor), int(judge_out * retry_factor)), 4),
            "note": "symmetric judge cross (K_A + K_D) roughly doubles judging cost vs a single pass",
        },
        "optional_pro_adjudication_usd_est": round(
            usd(FROZEN["adjudication_model"], int(judge_in * retry_factor), int(judge_out * retry_factor)), 4
        ),
        "worst_case_all_fallback_model_usd_est": round(
            usd(FROZEN["fallback_model"], author_in + int(judge_in * retry_factor), author_out + int(judge_out * retry_factor)),
            4,
        ),
        "cost_cap_usd": 25.0,
    }
    report["total_usd_est_june_models"] = round(
        report["authoring"]["usd_est"] + report["judging"]["usd_est"], 4
    )
    report["under_cap"] = bool(
        max(report["total_usd_est_june_models"], report["worst_case_all_fallback_model_usd_est"]) < report["cost_cap_usd"]
    )
    return report


# ---------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="do everything except API calls; print request counts + token/cost estimate")
    parser.add_argument("--stage", choices=["all", "plan", "author", "assemble", "gate1", "blind", "judge", "score"], default="all")
    parser.add_argument("--author-model", default=FROZEN["author_model"])
    parser.add_argument("--judge-model", default=FROZEN["judge_model"])
    args = parser.parse_args()

    if (args.author_model, args.judge_model) != (FROZEN["author_model"], FROZEN["judge_model"]) and not args.dry_run:
        allowed = {FROZEN["fallback_model"]}
        if {args.author_model, args.judge_model} - {FROZEN["author_model"], FROZEN["judge_model"]} - allowed:
            raise SystemExit(
                "model override must be the pre-registered fallback pin "
                f"({FROZEN['fallback_model']}) for BOTH roles, or the June-exact defaults"
            )

    verify_inputs()
    write_json(HERE / "frozen_config.json", FROZEN)
    models_used = {
        "author_model": args.author_model,
        "judge_model": args.judge_model,
        "judge_passes": list(JUDGE_PASSES),
        "fallback_rule": (
            f"if any June-exact model is unavailable, BOTH roles for BOTH arms move to {FROZEN['fallback_model']}; "
            "mixed pins prohibited"
        ),
    }

    # ---- plan (R1)
    plan_a = build_arm_plan("A")
    plan_d = build_arm_plan("D")
    assert_matched_ab_inputs(plan_a, plan_d)
    audit = template_identity_guard(plan_a, plan_d)  # REAL guard: hard-fails on any byte diff
    write_json(HERE / "plan_arm_A.json", plan_a)
    write_json(HERE / "plan_arm_D.json", plan_d)
    for arm, plan in (("A", plan_a), ("D", plan_d)):
        chunks_path = HERE / f"plan_arm_{arm}_chunks.jsonl"
        with chunks_path.open("w", encoding="utf-8", newline="\n") as fh:
            for chunk in plan["chunks"]:
                fh.write(json.dumps(chunk, sort_keys=True) + "\n")
    audit_summary = {
        "n_paired_prompts_compared": audit["n_paired_prompts_compared"],
        "n_byte_equal": audit["n_byte_equal"],
        "cover_controls_and_emotions_identical_across_arms": audit["cover_controls_and_emotions_identical_across_arms"],
    }
    print(json.dumps({"stage": "plan", "template_identity_guard": audit_summary, "rows_per_arm": len(plan_a["row_plan"])}, indent=2))
    if args.stage == "plan":
        return 0

    queue = interleaved_chunk_queue(plan_a, plan_d)
    plans = {"A": plan_a, "D": plan_d}

    if args.dry_run:
        author_stats = author_all(queue, args.author_model, dry_run=True)
        blind_info = blind_prep(None, plans, dry_run=True)
        report = {
            "dry_run": True,
            "no_api_calls_made": True,
            "template_identity_guard": audit_summary,
            "authoring": {
                "chunks_total": len(queue),
                "interleave_head": [f"{c['arm']}:{c['foundation']}" for c in queue[:6]],
                "requests_planned": author_stats["planned_requests"],
                "input_tokens_est": author_stats["input_tokens_est"],
                "output_tokens_est": author_stats["output_tokens_est"],
            },
            "blind_pool_planned_rows": blind_info["rows"],
            "cost": cost_report(author_stats, blind_info["rows"]),
        }
        write_json(HERE / "dryrun_report.json", report)
        print(json.dumps(report, indent=2, sort_keys=True))
        print("DRY RUN COMPLETE — no API calls were made.")
        return 0

    # ---- real run stages
    if args.stage in {"all", "author"}:
        stats = author_all(queue, args.author_model, dry_run=False)
        print(json.dumps({"stage": "author", **{k: v for k, v in stats.items() if k != "input_tokens_est"}}, indent=2))
        if stats["chunks_failed"]:
            return 1
    fixtures = {}
    if args.stage in {"all", "assemble", "gate1", "blind"}:
        for arm, plan in plans.items():
            fixtures[arm] = assemble_arm(arm, plan, args.author_model)
    if args.stage in {"all", "gate1"}:
        for arm in FROZEN["arms"]:
            result = gate1_arm(arm, fixtures[arm])
            print(
                json.dumps(
                    {
                        "stage": "gate1",
                        "arm": arm,
                        "verdict": result["verdict"],
                        "surface": result["surface"],
                        "cv_seed_sensitivity": result["cv_seed_sensitivity"],
                    },
                    indent=2,
                )
            )
    if args.stage in {"all", "blind"}:
        blind_prep(fixtures, plans, dry_run=False)
    if args.stage in {"all", "judge"}:
        for pass_key in JUDGE_PASSES:
            judge_all(args.judge_model, pass_key)
    if args.stage in {"all", "score"}:
        results = score_all(models_used)
        return 0 if results["verdict"] == "PASS_TKS_SUPERIORITY_LICENSED" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
