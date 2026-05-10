"""v1d targeted regen — replace failing teacher rows in three categories.

Per user directive 2026-05-10 (post audit commit dc79ff0): regen-first
discipline. Don't generate net-new infill until we measure the cleaned
distribution. Strict gates enforced for all three categories — bad rows
do not enter v1d. Then v1d retrain from v1c VALIDTOK 5ep, 2 epochs first
with sample-check.

Inputs (the three audit JSONLs):
  cas-synthetic/data/path_d/fractal_target_audit_<ts>.jsonl
  cas-synthetic/data/path_d/recipe_target_audit_<ts>.jsonl
  cas-synthetic/data/path_d/meta_logic_target_audit_<ts>.jsonl

For each row failing strict validation, the script will:
  1. Build a category-specific cas_to_english prompt that includes the
     source CAS PLUS explicit preservation constraints (e.g., for
     fractals: "render exactly N stages in this order: ^k1 ^k2 ... ^kn").
  2. Call the model (default claude-haiku-4-5-20251001).
  3. Pack the model's reply into a synthetic record and run the
     audit script's strict validator on it.
  4. If pass: keep. If fail: retry up to ``--max-retries`` times.

Outputs:
  v1d_regen_clean_<ts>.jsonl       — accepted rows, ready for v1d corpus
  v1d_regen_rejects_<ts>.jsonl     — rejected attempts with reasons
  v1d_regen_summary_<ts>.json      — per-category pass rates, retry burden
  v1d_regen_manifest_<ts>.json     — what changed (replaced row IDs etc.)

Cost discipline (mirrors Wave 2.5):
  - Default ``--dry-run`` is on; paid execution requires BOTH ``--paid``
    AND ``--yes-i-am-sure``.
  - ``--cost-cap-usd`` 25.0 default; per-call reserve enforced.
  - Dry-run prints planned spend, sample prompts, and target row counts
    so the user can review before authorizing API calls.

Validators reused from the audit scripts (importlib-loaded so we don't
fork the strict gate definitions):
  - cas-synthetic/scripts/audit_fractal_targets.py: audit_one_record
  - cas-synthetic/scripts/audit_recipe_targets.py: audit_one_record
  - cas-synthetic/scripts/audit_meta_logic_targets.py: audit_one_record
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import types
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "cas-synthetic" / "scripts"
DATA_DIR = REPO_ROOT / "cas-synthetic" / "data" / "path_d"


# ---------------------------------------------------------------------------
# Module loaders (importlib pattern — established by Wave 2.5)
# ---------------------------------------------------------------------------

def _load_script(name: str, filename: str):
    """Load a sibling script as a module via importlib."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, SCRIPTS_DIR / filename,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_phase1_module():
    """Load generate_path_d_wave3_smoke.py for AnthropicClient +
    CostTracker + load_api_key reuse."""
    return _load_script(
        "v1d_phase1_helpers",
        "generate_path_d_wave3_smoke.py",
    )


def _load_audit_fractal():
    return _load_script(
        "v1d_audit_fractal", "audit_fractal_targets.py",
    )


def _load_audit_recipe():
    return _load_script(
        "v1d_audit_recipe", "audit_recipe_targets.py",
    )


def _load_audit_meta_logic():
    return _load_script(
        "v1d_audit_meta_logic", "audit_meta_logic_targets.py",
    )


# ---------------------------------------------------------------------------
# Audit-row loading (failing rows only, per regen-first directive)
# ---------------------------------------------------------------------------

def _latest_audit_file(prefix: str) -> Optional[Path]:
    """Find the most recent audit JSONL with given prefix."""
    candidates = sorted(DATA_DIR.glob(f"{prefix}_*.jsonl"))
    return candidates[-1] if candidates else None


def load_failing_rows(category: str) -> list[dict]:
    """Return the failing rows from the latest audit JSONL for the
    given category. Categories: 'fractal', 'recipe', 'meta_logic'."""
    prefix_map = {
        "fractal": "fractal_target_audit",
        "recipe": "recipe_target_audit",
        "meta_logic": "meta_logic_target_audit",
    }
    prefix = prefix_map[category]
    path = _latest_audit_file(prefix)
    if path is None:
        raise FileNotFoundError(
            f"no audit file found for prefix {prefix} in {DATA_DIR}"
        )
    pass_field = "sequence_matches" if category == "fractal" else "strict_match"
    failing: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not row.get(pass_field, False):
                failing.append(row)
    return failing


# ---------------------------------------------------------------------------
# Per-category prompt builders
# ---------------------------------------------------------------------------
#
# Each builder returns (system, user) for a Claude messages.create call.
# Prompts extend the standard cas_to_english template (from phase1) with
# category-specific preservation rules so the regen has a fighting chance
# at strict validation. Constraint lists are explicit and verbose — the
# Wave 2.5 audit found that lighter prompts produced silhouette-shaped
# but content-drifted output, which is exactly what we're regenerating
# AWAY from.

_BASE_GUIDANCE = (
    "You are a translator that turns formal CAS (Cognitive Architecture "
    "System) expressions into clear English paraphrases. CAS is a formal "
    "notation describing cognitive states and operations. Your job is to "
    "express what the expression MEANS in plain, fluent English, using "
    "the approved colloquial aliases for cognitive operators."
)

_NOETIC_ALIAS_TABLE = (
    "Approved Noetic colloquialisms (use these for ^N where they fit):\n"
    "  ^0 Idea          -> 'a thought' / 'a foundational thought' / 'an idea'\n"
    "  ^1 Mind          -> 'paying attention' / 'cognitive attention'\n"
    "  ^2 Positive      -> 'drawn to' / 'speaks to'\n"
    "  ^3 Negative      -> 'an aversion' / 'rubs the wrong way' / 'pushed away'\n"
    "  ^4 Vibration     -> 'struck a chord' / 'made an impression' / 'resonated'\n"
    "  ^5 Female        -> 'who one is' / 'shaped by experiences'\n"
    "  ^6 Male          -> 'breaking it down' / 'unpacking'\n"
    "  ^7 Rhythm        -> 'practiced rhythm' / 'practice makes perfect' / 'muscle memory'\n"
    "  ^8 Above/Cause   -> 'triggered a memory' / 'one thing leads to another' / 'that reminds me'\n"
    "  ^9 Below/Effect  -> 'popped into mind' / 'just clicked'\n"
)

_DOMAIN_ALIAS_TABLE = (
    "Domain words (^P/^C/^E/^O):\n"
    "  ^P -> 'principled' / 'foundational'\n"
    "  ^C -> 'cognitive' / 'cognitive thinking'\n"
    "  ^E -> 'evaluative' / 'evaluative judgment'\n"
    "  ^O -> 'operational' / 'operational behavior'\n"
)

_DRIVE_ALIAS_TABLE = (
    "Drive words (F1..F7):\n"
    "  F1 unity / togetherness\n"
    "  F2 wisdom and insight\n"
    "  F3 vitality and energy\n"
    "  F4 connection / attachment\n"
    "  F5 agency and self-determination\n"
    "  F6 structure / order\n"
    "  F7 purpose / meaning\n"
)


def build_fractal_prompt(row: dict) -> tuple[str, str]:
    """Fractal regen prompt: name N stages explicitly, in order."""
    cas = row["cas_expression"]
    k_values = row["k_values"]
    n = len(k_values)
    # Render the exact required sequence as a constraint list.
    sequence_lines = []
    for i, k in enumerate(k_values, 1):
        sequence_lines.append(f"  Stage {i}: ^{k} (use a ^{k} colloquialism)")
    sequence_block = "\n".join(sequence_lines)
    system = _BASE_GUIDANCE
    user = (
        f"CAS expression (fractal sequence):\n\n    {cas}\n\n"
        f"This is a fractal of EXACTLY {n} stages. The English paraphrase "
        f"must render EXACTLY {n} clauses in this order:\n\n"
        f"{sequence_block}\n\n"
        f"{_NOETIC_ALIAS_TABLE}\n"
        "Constraints:\n"
        f"  - Render exactly {n} stages, no more, no fewer.\n"
        "  - Stages must be in the exact source order.\n"
        "  - Each stage uses a colloquialism for its specific ^N (do NOT swap).\n"
        "  - Do not invent stages not in the source.\n"
        "  - Connect the stages with natural transitions ('then', "
        "'which led to', 'and finally').\n\n"
        "Reply with ONLY the English paraphrase. No preamble, no list, "
        "no quotes."
    )
    return system, user


def build_recipe_prompt(row: dict) -> tuple[str, str]:
    """Recipe regen prompt: stress per-term Noetic preservation."""
    cas = row["cas_expression"]
    system = _BASE_GUIDANCE
    user = (
        f"CAS expression (recipe / production):\n\n    {cas}\n\n"
        "Render this recipe in plain English. Preserve EVERY component:\n\n"
        f"{_NOETIC_ALIAS_TABLE}\n{_DOMAIN_ALIAS_TABLE}{_DRIVE_ALIAS_TABLE}\n"
        "Constraints:\n"
        "  - Mention every Ω name from the source verbatim "
        "(or the bare suffix, e.g., 'rehearsal_40' for Ω_rehearsal_40).\n"
        "  - Mention every coefficient as a numeric token (e.g., "
        "'0.7 of', '2 parts', '1.5 measures').\n"
        "  - Each LHS term must use a colloquialism that matches its "
        "specific ^N — do not substitute different Noetic colloquialisms.\n"
        "  - If the source contains Λ (a side product / leakage), "
        "mention 'side product' or 'leakage' explicitly.\n"
        "  - Preserve domain word, drive word, and register where present.\n\n"
        "Reply with ONLY the English paraphrase. No preamble, no list, "
        "no quotes."
    )
    return system, user


_NOETIC_EXAMPLE_PER_K: dict[int, str] = {
    0: 'a foundational thought / an idea',
    1: 'paying attention / cognitive attention',
    2: 'drawn to / speaks to',
    3: 'an aversion / rubs the wrong way / pushed away',
    4: 'struck a chord / made an impression / resonated',
    5: 'who one is / shaped by experiences',
    6: 'breaking it down / unpacking',
    7: 'practiced rhythm / muscle memory / practice makes perfect',
    8: 'triggered a memory / one thing leads to another / that reminds me',
    9: 'popped into mind / just clicked',
}


def build_meta_logic_prompt(row: dict) -> tuple[str, str]:
    """Meta-logic regen prompt: force per-cluster numbered enumeration.

    Per user directive 2026-05-10 (post v1d smoke 0/5): Haiku omits
    1-2 members when enumerating 7-8 noetics in a flowing paragraph.
    The fix is to make the enumeration MECHANICALLY HARDER TO SKIP —
    explicit per-cluster member checklist, numbered format requirement,
    and "do not summarize" / "do not say 'and others'" instructions.

    Falls back to the older flowing-paragraph prompt only if the
    source CAS doesn't parse as meta-logic (defensive).
    """
    cas = row["cas_expression"]
    expected_rel = row["expected_relation"]
    rel_word = {
        "PartitionOf": "partition",
        "CoverOf": "cover",
        "Product": "product",
    }[expected_rel]
    # Parse source clusters from the audit_meta_logic module (which
    # already imports parse_meta_logic at module load time).
    audit_mod = _load_audit_meta_logic()
    parsed = audit_mod.parse_meta_logic(cas)
    if parsed is None or not parsed.clusters:
        # Defensive fallback — should not normally hit since the
        # audit row already passed parse_meta_logic during audit.
        system = _BASE_GUIDANCE
        user = (
            f"CAS expression (meta-logic relation, type: {expected_rel}):\n\n"
            f"    {cas}\n\nRender in plain English."
        )
        return system, user

    # Build per-cluster numbered enumeration scaffolding.
    cluster_blocks: list[str] = []
    for i, cluster in enumerate(parsed.clusters, start=1):
        n_members = len(cluster.noetics)
        member_lines: list[str] = []
        for j, k in enumerate(cluster.noetics, start=1):
            example = _NOETIC_EXAMPLE_PER_K.get(k, "")
            member_lines.append(
                f"    {j}. ^{k} — use a ^{k} colloquialism, "
                f"e.g., \"{example}\""
            )
        block = (
            f"Cluster {i} must contain EXACTLY {n_members} members:\n"
            + "\n".join(member_lines)
        )
        cluster_blocks.append(block)
    cluster_section = "\n\n".join(cluster_blocks)
    n_clusters = len(parsed.clusters)

    system = _BASE_GUIDANCE
    user = (
        f"CAS expression (meta-logic relation, type: {expected_rel}):\n\n"
        f"    {cas}\n\n"
        f"You are rendering a {expected_rel} relation. Use the relation "
        f"word '{rel_word}'. Name EXACTLY {n_clusters} clusters/groups.\n\n"
        f"{cluster_section}\n\n"
        "FORMAT REQUIREMENTS (these are the load-bearing instructions):\n"
        "  - Use a numbered or semicolon-separated list of members "
        "WITHIN each cluster description. Do not flow members into a "
        "single paragraph clause.\n"
        "  - Do NOT summarize a cluster. Do NOT write 'and others', "
        "'and so on', 'etc.', or 'and the rest'.\n"
        "  - Do NOT omit any listed member. Every member above must "
        "appear by colloquialism in the corresponding cluster.\n"
        "  - Do NOT add Noetics that aren't in the source clusters.\n"
        "  - Connect the clusters with a transition phrase appropriate "
        f"to '{rel_word}' (e.g., 'partitions into', 'covers', "
        "'the product of').\n\n"
        "Reply with ONLY the English paraphrase. No preamble, no quotes."
    )
    return system, user


def build_prompt(row: dict, category: str) -> tuple[str, str]:
    if category == "fractal":
        return build_fractal_prompt(row)
    if category == "recipe":
        return build_recipe_prompt(row)
    if category == "meta_logic":
        return build_meta_logic_prompt(row)
    raise ValueError(f"unknown category {category}")


# ---------------------------------------------------------------------------
# Per-category strict validators (reuse audit scripts)
# ---------------------------------------------------------------------------

def make_validator(category: str) -> Callable[[dict, str], tuple[bool, dict]]:
    """Return a function ``(audit_row, candidate_target) -> (passed, log)``.

    Builds a synthetic record with the candidate target replacing the
    old reply_text, runs the audit's strict validator, returns whether
    it passes plus the audit's diagnostic log for reject-record clarity.
    """
    if category == "fractal":
        mod = _load_audit_fractal()

        def validator(audit_row: dict, candidate: str):
            synthetic = {
                "id": audit_row["id"],
                "cas_expression": audit_row["cas_expression"],
                "reply_text": candidate,
                "v1mix_task_type": "cas_to_english",
                "__source_split": audit_row.get("source_split", ""),
            }
            result = mod.audit_one_record(synthetic)
            if result is None:
                return False, {"reason": "validator returned None"}
            return result["sequence_matches"], result
        return validator

    if category == "recipe":
        mod = _load_audit_recipe()

        def validator(audit_row: dict, candidate: str):
            synthetic = {
                "id": audit_row["id"],
                "cas_expression": audit_row["cas_expression"],
                "reply_text": candidate,
                "v1mix_task_type": "cas_to_english",
                "__source_split": audit_row.get("source_split", ""),
            }
            result = mod.audit_one_record(synthetic)
            if result is None:
                return False, {"reason": "validator returned None"}
            return result["strict_match"], result
        return validator

    if category == "meta_logic":
        mod = _load_audit_meta_logic()

        def validator(audit_row: dict, candidate: str):
            synthetic = {
                "id": audit_row["id"],
                "cas_expression": audit_row["cas_expression"],
                "reply_text": candidate,
                "v1mix_task_type": "cas_to_english",
                "__source_split": audit_row.get("source_split", ""),
            }
            result = mod.audit_one_record(synthetic)
            if result is None:
                return False, {"reason": "validator returned None"}
            return result["strict_match"], result
        return validator

    raise ValueError(f"unknown category {category}")


# ---------------------------------------------------------------------------
# Generation loop (with retry + cost tracking)
# ---------------------------------------------------------------------------

def regenerate_one_row(
    *,
    audit_row: dict,
    category: str,
    validator: Callable[[dict, str], tuple[bool, dict]],
    client: Any,
    cost_tracker: Any,
    model: str,
    max_retries: int,
    dry_run: bool,
) -> dict:
    """Try up to max_retries to produce a strict-passing target for
    one failing audit row. Returns a result dict suitable for both
    clean.jsonl and rejects.jsonl serialization."""
    system, user = build_prompt(audit_row, category)
    attempts: list[dict] = []
    accepted_target: Optional[str] = None
    accepted_log: Optional[dict] = None

    for attempt_idx in range(1, max_retries + 1):
        if dry_run:
            attempts.append({
                "attempt": attempt_idx,
                "dry_run": True,
                "system_preview": system[:80] + "...",
                "user_preview": user[:160] + "...",
            })
            break  # dry-run does not iterate retries
        # Real API call. ApiCallResult has text/input_tokens/output_tokens
        # /error_reason; the wrapper handles transient retries internally.
        result = client.call(
            model=model,
            system_prompt=system,
            user_message=user,
            max_output_tokens=400,
            temperature=0.4,
        )
        if result.text is None:
            # API error path — record and try next attempt.
            attempts.append({
                "attempt": attempt_idx,
                "model": model,
                "input_tokens": int(result.input_tokens),
                "output_tokens": int(result.output_tokens),
                "cost_usd": 0.0,
                "passed_strict": False,
                "validator_log": {
                    "reason": f"api_error: {result.error_reason}",
                },
                "candidate_target": None,
            })
            continue
        cost = cost_tracker.add(
            slot=category,
            model=model,
            input_tokens=int(result.input_tokens),
            output_tokens=int(result.output_tokens),
        )
        text = (result.text or "").strip()
        passed, log = validator(audit_row, text)
        attempts.append({
            "attempt": attempt_idx,
            "model": model,
            "input_tokens": int(result.input_tokens),
            "output_tokens": int(result.output_tokens),
            "cost_usd": cost,
            "passed_strict": passed,
            "validator_log": log if not passed else {"passed": True},
            "candidate_target": text,
        })
        if passed:
            accepted_target = text
            accepted_log = log
            break

    return {
        "audit_row_id": audit_row["id"],
        "audit_row_split": audit_row.get("source_split", ""),
        "category": category,
        "cas_expression": audit_row["cas_expression"],
        "old_target": audit_row.get("target_text", ""),
        "new_target": accepted_target,
        "accepted": accepted_target is not None,
        "n_attempts": len(attempts),
        "attempts": attempts,
        "accepted_log": accepted_log,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_outputs(
    *,
    results: list[dict],
    timestamp: str,
    dry_run: bool,
    summary_extra: dict,
) -> dict[str, Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "_dryrun" if dry_run else ""
    paths = {
        "clean": DATA_DIR / f"v1d_regen_clean_{timestamp}{suffix}.jsonl",
        "rejects": DATA_DIR / f"v1d_regen_rejects_{timestamp}{suffix}.jsonl",
        "summary": DATA_DIR / f"v1d_regen_summary_{timestamp}{suffix}.json",
        "manifest": DATA_DIR / f"v1d_regen_manifest_{timestamp}{suffix}.json",
    }

    accepted = [r for r in results if r["accepted"]]
    rejects = [r for r in results if not r["accepted"]]

    with paths["clean"].open("w", encoding="utf-8") as fh:
        for r in accepted:
            row = {
                "id": f"{r['audit_row_id']}_v1d",  # mark as v1d-regenerated
                "original_id": r["audit_row_id"],
                "source_split": r["audit_row_split"],
                "v1mix_task_type": "cas_to_english",
                "v1mix_grammar_category_or_error_class": _audit_to_v1mix_category(r["category"]),
                "cas_expression": r["cas_expression"],
                "reply_text": r["new_target"],
                "regen_n_attempts": r["n_attempts"],
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    with paths["rejects"].open("w", encoding="utf-8") as fh:
        for r in rejects:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_cat_total = Counter(r["category"] for r in results)
    by_cat_accepted = Counter(r["category"] for r in accepted)
    by_cat_attempts = defaultdict(list)
    for r in results:
        by_cat_attempts[r["category"]].append(r["n_attempts"])
    avg_attempts = {
        c: sum(v) / len(v) if v else 0.0
        for c, v in by_cat_attempts.items()
    }

    summary = {
        "timestamp": timestamp,
        "dry_run": dry_run,
        "total_rows_processed": len(results),
        "accepted": len(accepted),
        "rejected": len(rejects),
        "pass_rate_overall": (
            len(accepted) / len(results) if results else 0.0
        ),
        "by_category": {
            cat: {
                "total": by_cat_total.get(cat, 0),
                "accepted": by_cat_accepted.get(cat, 0),
                "rejected": by_cat_total.get(cat, 0) - by_cat_accepted.get(cat, 0),
                "pass_rate": (
                    by_cat_accepted.get(cat, 0) / by_cat_total[cat]
                    if by_cat_total.get(cat) else 0.0
                ),
                "avg_attempts": avg_attempts.get(cat, 0.0),
            }
            for cat in by_cat_total
        },
        **summary_extra,
    }
    paths["summary"].write_text(
        json.dumps(summary, indent=2), encoding="utf-8",
    )

    manifest = {
        "timestamp": timestamp,
        "dry_run": dry_run,
        "outputs": {k: str(v) for k, v in paths.items()},
        "v1d_corpus_intent": (
            "Replace these audit_row_id rows in v1_mix_nlgen_train.jsonl "
            "(and val/test analogs) with the corresponding v1d_regen_clean "
            "rows. The replacement keys on original_id."
        ),
        "replacement_ids": [r["audit_row_id"] for r in accepted],
        "still_failing_ids": [r["audit_row_id"] for r in rejects],
    }
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2), encoding="utf-8",
    )
    return paths


def _audit_to_v1mix_category(cat: str) -> str:
    return {
        "fractal": "fractal_sequence",
        "recipe": "recipe",
        "meta_logic": "meta_logic_relation",
    }[cat]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="v1d targeted regen — replace failing teacher rows.",
    )
    parser.add_argument(
        "--paid", action="store_true",
        help="Authorize live API calls. Without this flag we dry-run only.",
    )
    parser.add_argument(
        "--yes-i-am-sure", action="store_true",
        help="Required alongside --paid to prevent accidental spend.",
    )
    parser.add_argument(
        "--max-retries", type=int, default=3,
        help="Retries per failing row before giving up (default 3).",
    )
    parser.add_argument(
        "--cost-cap-usd", type=float, default=25.0,
        help="Hard cap on total spend (default $25).",
    )
    parser.add_argument(
        "--model", type=str, default="claude-haiku-4-5-20251001",
        help="Anthropic model id (default claude-haiku-4-5-20251001).",
    )
    parser.add_argument(
        "--limit-per-category", type=int, default=0,
        help="Cap rows processed per category (0 = no limit). "
        "Useful for staged execution: --limit-per-category 5 --paid "
        "for a tiny smoke before full run.",
    )
    parser.add_argument(
        "--categories", type=str, default="fractal,recipe,meta_logic",
        help="Comma-separated categories to regen. Default all three.",
    )
    args = parser.parse_args()

    dry_run = not args.paid
    if args.paid and not args.yes_i_am_sure:
        print(
            "[gate] --paid requires --yes-i-am-sure. Showing planned "
            "spend without calling API."
        )
        dry_run = True

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    print(f"v1d targeted regen — timestamp {timestamp}")
    print(f"mode: {'DRY-RUN (no API calls)' if dry_run else 'PAID'}")
    print(f"categories: {categories}")
    print(f"max_retries: {args.max_retries}, cost_cap_usd: {args.cost_cap_usd}")
    print(f"model: {args.model}")
    print()

    # Load failing rows for each requested category.
    work: list[tuple[str, dict]] = []
    by_cat_count: Counter = Counter()
    for cat in categories:
        rows = load_failing_rows(cat)
        if args.limit_per_category > 0:
            rows = rows[: args.limit_per_category]
        for r in rows:
            work.append((cat, r))
            by_cat_count[cat] += 1
        print(f"  {cat}: {len(rows)} failing rows queued for regen")
    print()
    print(f"Total work: {len(work)} rows.")
    print()

    # Estimate spend for dry-run preview.
    # Recipe Wave 2.5 cost basis: ~$0.0058 per accepted record at Haiku
    # rates. Allow 2.5x retry overhead for the strict-gate failure rate
    # we expect (~30-50% pass per attempt based on the audit's failure
    # severity).
    est_per_row = 0.0058 * 2.5
    est_total = est_per_row * len(work)
    print(
        f"Estimated spend (Haiku, ~2.5x retry overhead): "
        f"${est_total:.2f} (vs cap ${args.cost_cap_usd:.2f})"
    )
    if est_total > args.cost_cap_usd:
        print(
            "  WARNING: estimated spend exceeds cap. Use "
            "--limit-per-category to stage."
        )
    print()

    # Show one sample prompt per category in dry-run.
    if dry_run:
        seen_cats: set[str] = set()
        for cat, row in work:
            if cat in seen_cats:
                continue
            seen_cats.add(cat)
            system, user = build_prompt(row, cat)
            print(f"--- sample {cat} prompt ---")
            print(f"  source CAS: {row['cas_expression'][:120]}")
            print(f"  user prompt (first 400 chars):")
            for ln in user[:400].splitlines():
                print(f"    {ln}")
            print()

    # If dry-run, write a planned-summary file and exit.
    if dry_run:
        results = [
            {
                "audit_row_id": row["id"],
                "audit_row_split": row.get("source_split", ""),
                "category": cat,
                "cas_expression": row["cas_expression"],
                "old_target": row.get("target_text", ""),
                "new_target": None,
                "accepted": False,
                "n_attempts": 0,
                "attempts": [{"attempt": 0, "dry_run": True}],
                "accepted_log": None,
            }
            for cat, row in work
        ]
        paths = write_outputs(
            results=results,
            timestamp=timestamp,
            dry_run=True,
            summary_extra={
                "estimated_spend_usd": round(est_total, 4),
                "by_category_queued": dict(by_cat_count),
                "model": args.model,
                "max_retries": args.max_retries,
            },
        )
        print()
        print("Dry-run artifacts:")
        for k, v in paths.items():
            print(f"  {k}: {v}")
        print()
        print(
            "To execute: rerun with --paid --yes-i-am-sure (and adjust "
            "--cost-cap-usd if needed)."
        )
        return 0

    # Paid path.
    phase1 = _load_phase1_module()
    api_key = phase1.load_api_key()
    if not api_key:
        print(
            "[error] no Anthropic API key. Set ANTHROPIC_API_KEY or "
            "NC_ANTHROPIC_API_KEY in env."
        )
        return 2
    client = phase1.AnthropicClient(api_key)
    cost_tracker = phase1.CostTracker(cost_cap_usd=args.cost_cap_usd)
    validators = {cat: make_validator(cat) for cat in categories}

    results: list[dict] = []
    for i, (cat, row) in enumerate(work, 1):
        if cost_tracker.would_exceed(projected_call_cost=0.05):
            print(
                f"[cap] would exceed cost cap; stopping at row {i-1}/{len(work)}."
            )
            break
        try:
            r = regenerate_one_row(
                audit_row=row,
                category=cat,
                validator=validators[cat],
                client=client,
                cost_tracker=cost_tracker,
                model=args.model,
                max_retries=args.max_retries,
                dry_run=False,
            )
        except Exception as exc:
            r = {
                "audit_row_id": row["id"],
                "audit_row_split": row.get("source_split", ""),
                "category": cat,
                "cas_expression": row["cas_expression"],
                "old_target": row.get("target_text", ""),
                "new_target": None,
                "accepted": False,
                "n_attempts": 0,
                "attempts": [],
                "accepted_log": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        results.append(r)
        if i % 10 == 0 or i == len(work):
            accepted = sum(1 for x in results if x["accepted"])
            print(
                f"  [{i}/{len(work)}] accepted={accepted}, "
                f"spend=${cost_tracker.total_cost_usd:.3f}"
            )

    paths = write_outputs(
        results=results,
        timestamp=timestamp,
        dry_run=False,
        summary_extra={
            "spend_usd": round(cost_tracker.total_cost_usd, 4),
            "model": args.model,
            "max_retries": args.max_retries,
            "by_category_queued": dict(by_cat_count),
        },
    )
    print()
    print(f"Total spend: ${cost_tracker.total_cost_usd:.3f}")
    print()
    print("Artifacts:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
