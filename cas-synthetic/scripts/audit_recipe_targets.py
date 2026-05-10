"""Audit existing recipe training targets with strict structural validator.

Per user directive 2026-05-10 (post fractal audit commit 153dd49):
queue recipe + meta-logic audits BEFORE regeneration so we know
whether to bundle the v1d retrain into one wave covering all weak
categories or fractal-only.

This is a Stage-1 one-off audit. Mirror of audit_fractal_targets.py
but for recipe sources of shape:
  Θ(Ω_X) = a1*N1 + a2*N2 + ... → Ω_X [+ a_side*Λ·Ω_side]

Per-row strict checks:
  1. Ω target preservation: source's primary Ω name (and any side
     products) appear verbatim or with recoverable spelling in
     the target text.
  2. Coefficient multiset: source coefficients appear as numeric
     tokens in target with matching multiplicities (e.g., source
     [0.7, 0.7, 2] -> target must have two 0.7s and one 2).
  3. Ingredient noetic + domain + drive + register: each source
     LHS term's Noetic colloquialism, domain word, drive word,
     and register word (when present) must have at least one
     indicator in target text.
  4. Side-product preservation: if source has `Λ`, target must
     mention side-product / leakage / byproduct / Λ explicitly.

The audit is read-only — does not delete or rewrite any corpus
rows. Outputs JSONL with per-row diagnostic + markdown summary.

Output format mirrors audit_fractal_targets.py for cross-reference
of weak categories before deciding on regeneration scope.
"""
from __future__ import annotations

import json
import re
import sys
import types
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(SCAFFOLD_ROOT))


CORPUS_FILES = [
    "cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl",
    "cas-synthetic/data/path_d/v1_mix_nlgen_val.jsonl",
    "cas-synthetic/data/path_d/v1_mix_nlgen_test.jsonl",
]
OUT_DIR = REPO_ROOT / "cas-synthetic/data/path_d"


# ---------------------------------------------------------------------------
# Recipe parser (inline; this is a one-off audit, not production)
# ---------------------------------------------------------------------------

# Recipe shape: Θ(Ω_X) = LHS → Ω_X [+ side]
_RECIPE_RX = re.compile(
    r"Θ\s*\(\s*(?P<primary_omega>Ω_\w+)\s*\)\s*=\s*"
    r"(?P<lhs>[^→]+)→\s*"
    r"(?P<rhs>.+?)$",
    re.DOTALL,
)
_OMEGA_RX = re.compile(r"Ω_\w+")
_TERM_COEF_RX = re.compile(
    r"(?P<coef>\d+(?:\.\d+)?)\s*\*\s*"
    r"(?:Λ\s*[·.]\s*)?"  # optional Λ· for leakage terms
    r"(?P<expr>(?:\^\d(?:\^[PCEO])?(?:_\{F\d\})?(?:\|[TAfE])?|Ω_\w+))"
)
_LAMBDA_RX = re.compile(r"Λ\s*[·.]")

# CAS-axis indicator maps (mirrors meta_logic_repair / fractal_repair).
_NOETIC_INDICATORS: dict[int, tuple[str, ...]] = {
    0: ("foundational thought", "an idea", "a thought", "in your head"),
    1: ("paying attention", "make up your mind", "cognitive attention"),
    2: ("drawn to", "speaks to", "attracted toward"),
    3: ("rubs the wrong way", "averse to", "repelled", "pushed away",
        "can't stomach"),
    4: ("struck a chord", "made an impression", "resonated"),
    5: ("who one is", "who you are", "shaped by experiences",
        "sum of experiences"),
    6: ("breaking it down", "unpacking", "pulling apart"),
    7: ("muscle memory", "practice makes perfect", "practiced rhythm",
        "practice-based"),
    8: ("that reminds", "one thing leads", "triggered a memory"),
    9: ("popped into mind", "popped to mind", "just clicked", "popped"),
}
_DOMAIN_INDICATORS: dict[str, tuple[str, ...]] = {
    "P": ("principled", "foundational"),
    "C": ("cognitive thinking", "cognitive attention", "cognitive"),
    "E": ("evaluative judgment", "evaluative arena", "evaluative"),
    "O": ("operational behavior", "operational"),
}
_DRIVE_INDICATORS: dict[int, tuple[str, ...]] = {
    1: ("unity", "togetherness"),
    2: ("wisdom", "insight"),
    3: ("vitality", "energy"),
    4: ("connection", "attachment"),
    5: ("agency", "self-determination"),
    6: ("structure", "order"),
    7: ("purpose", "meaning"),
}
_REGISTER_INDICATORS: dict[str, tuple[str, ...]] = {
    "T": ("transcendent", "big-picture", "strategic"),
    "A": ("analytical", "reasoned"),
    "f": ("affective", "felt", "emotional"),
    "E": ("embodied", "sensorimotor"),
}
_SIDE_INDICATORS = (
    "side product", "side-product", "side reaction", "leakage",
    "byproduct", "by-product", "side", "λ", "Λ",
)


def parse_term_axes(expr: str) -> dict:
    """Decompose a term expression like ^9^P_{F3}|T into axes."""
    n = re.search(r"\^(\d)", expr)
    d = re.search(r"\^\d\^([PCEO])", expr)
    f = re.search(r"_\{F(\d)\}", expr)
    r = re.search(r"\|([TAfE])(?![A-Za-z])", expr)
    return {
        "noetic": int(n.group(1)) if n else None,
        "domain": d.group(1) if d else None,
        "drive": int(f.group(1)) if f else None,
        "register": r.group(1) if r else None,
    }


def parse_recipe(cas: str) -> dict | None:
    """Extract recipe structure: primary Ω, LHS coef-term pairs,
    side-product Ω names, has_side flag. Returns None for non-recipe."""
    m = _RECIPE_RX.search(cas)
    if m is None:
        return None
    primary = m.group("primary_omega")
    lhs = m.group("lhs")
    rhs = m.group("rhs")
    # LHS terms
    lhs_terms = []
    for tm in _TERM_COEF_RX.finditer(lhs):
        coef_str = tm.group("coef")
        try:
            coef = float(coef_str)
        except ValueError:
            continue
        # Coerce to canonical form (1.0 -> 1, 0.10 -> 0.1)
        if coef == int(coef):
            coef_canon = str(int(coef))
        else:
            coef_canon = f"{coef:g}"
        expr = tm.group("expr")
        axes = parse_term_axes(expr)
        lhs_terms.append({
            "coef": coef_canon,
            "expr": expr,
            "axes": axes,
        })
    # RHS side products: look for terms with Λ in the RHS portion
    has_side_in_rhs = bool(_LAMBDA_RX.search(rhs))
    has_side_anywhere = bool(_LAMBDA_RX.search(cas))
    side_omegas = [
        o for o in _OMEGA_RX.findall(rhs)
        if o != primary
    ]
    return {
        "primary_omega": primary,
        "lhs_terms": lhs_terms,
        "side_omegas": side_omegas,
        "has_lambda": has_side_anywhere,
    }


# ---------------------------------------------------------------------------
# Strict target validation
# ---------------------------------------------------------------------------

_NUMBER_RX = re.compile(r"\d+(?:\.\d+)?")


def _coef_multiset_match(source_coefs: list[str], target_text: str) -> bool:
    """Source's coefficient multiset must be a subset of target's."""
    target_nums = _NUMBER_RX.findall(target_text)
    target_canon = []
    for n in target_nums:
        try:
            f = float(n)
            target_canon.append(str(int(f)) if f == int(f) else f"{f:g}")
        except ValueError:
            pass
    src = Counter(source_coefs)
    tgt = Counter(target_canon)
    for k, v in src.items():
        if tgt.get(k, 0) < v:
            return False
    return True


def _omega_in_target(omega: str, target_text: str) -> bool:
    """Source's Ω name must appear in target either verbatim
    (``Ω_rehearsal_40``) or with the bare suffix form
    (``rehearsal_40``) since cas_to_english targets typically
    drop the Ω_ prefix in natural prose ("the outcome called
    rehearsal_40")."""
    if omega in target_text:
        return True
    # Strip "Ω_" prefix and look for the suffix as a standalone word.
    if omega.startswith("Ω_"):
        suffix = omega[2:]
        # Word-boundary match: precede with non-word char or start;
        # follow with non-word char or end.
        pat = re.compile(rf"(?<!\w){re.escape(suffix)}(?!\w)")
        if pat.search(target_text):
            return True
    return False


def _axes_present_for_term(axes: dict, target_lower: str) -> dict:
    """For one source term, check whether each axis indicator
    appears anywhere in the target. Returns per-axis bool dict."""
    out = {}
    if axes["noetic"] is not None:
        ind = _NOETIC_INDICATORS.get(axes["noetic"], ())
        out["noetic_present"] = any(i in target_lower for i in ind)
    if axes["domain"] is not None:
        ind = _DOMAIN_INDICATORS.get(axes["domain"], ())
        out["domain_present"] = any(i in target_lower for i in ind)
    if axes["drive"] is not None:
        ind = _DRIVE_INDICATORS.get(axes["drive"], ())
        out["drive_present"] = any(i in target_lower for i in ind)
    if axes["register"] is not None:
        ind = _REGISTER_INDICATORS.get(axes["register"], ())
        out["register_present"] = any(i in target_lower for i in ind)
    return out


def _side_product_mentioned(target_text: str) -> bool:
    target_lower = target_text.lower()
    return any(ind.lower() in target_lower for ind in _SIDE_INDICATORS)


def audit_one_record(rec: dict) -> dict | None:
    # Filter by task_type: only audit cas_to_english rows. Recipe-shaped
    # sources also appear in invalid_to_explanation rows where the target
    # is an explanation of why the source is broken, NOT a rendering of
    # the recipe — those rows would always fail strict validation and
    # contaminate the headline.
    task_type = rec.get("v1mix_task_type") or rec.get("task_type") or ""
    if task_type and task_type != "cas_to_english":
        return None
    cas = rec.get("cas_expression", "")
    target = rec.get("reply_text", "")
    if not cas or not target:
        return None
    parsed = parse_recipe(cas)
    if parsed is None:
        return None
    target_lower = target.lower()
    primary = parsed["primary_omega"]
    side_omegas = parsed["side_omegas"]
    lhs_terms = parsed["lhs_terms"]
    coefs = [t["coef"] for t in lhs_terms]

    # Per-check booleans
    primary_omega_match = _omega_in_target(primary, target)
    side_omega_match = (
        all(_omega_in_target(o, target) for o in side_omegas)
        if side_omegas else True
    )
    coef_match = _coef_multiset_match(coefs, target)
    has_lambda = parsed["has_lambda"]
    side_kw_match = _side_product_mentioned(target) if has_lambda else True

    # Per-term axis presence
    n_terms = len(lhs_terms)
    noetic_misses = []
    domain_misses = []
    drive_misses = []
    register_misses = []
    for i, t in enumerate(lhs_terms):
        axes_status = _axes_present_for_term(t["axes"], target_lower)
        if "noetic_present" in axes_status and not axes_status["noetic_present"]:
            noetic_misses.append(i)
        if "domain_present" in axes_status and not axes_status["domain_present"]:
            domain_misses.append(i)
        if "drive_present" in axes_status and not axes_status["drive_present"]:
            drive_misses.append(i)
        if "register_present" in axes_status and not axes_status["register_present"]:
            register_misses.append(i)

    strict_match = (
        primary_omega_match
        and side_omega_match
        and coef_match
        and side_kw_match
        and not noetic_misses
        and not domain_misses
        and not drive_misses
        and not register_misses
    )

    return {
        "id": rec.get("id", ""),
        "source_split": rec.get("__source_split", ""),
        "cas_expression": cas,
        "target_text": target,
        "n_terms": n_terms,
        "primary_omega": primary,
        "has_lambda": has_lambda,
        "n_side_omegas": len(side_omegas),
        "primary_omega_match": primary_omega_match,
        "side_omega_match": side_omega_match,
        "coef_multiset_match": coef_match,
        "side_kw_match": side_kw_match,
        "noetic_misses_at_terms": noetic_misses,
        "domain_misses_at_terms": domain_misses,
        "drive_misses_at_terms": drive_misses,
        "register_misses_at_terms": register_misses,
        "strict_match": strict_match,
    }


def run_audit():
    rows = []
    files_scanned = []
    for rel in CORPUS_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            files_scanned.append((rel, 0, 0))
            continue
        n_rows = 0
        n_recipe = 0
        split_name = path.stem.replace("v1_mix_nlgen_", "")
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                rec["__source_split"] = split_name
                n_rows += 1
                row = audit_one_record(rec)
                if row is not None:
                    rows.append(row)
                    n_recipe += 1
        files_scanned.append((rel, n_rows, n_recipe))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUT_DIR / f"recipe_target_audit_{timestamp}.jsonl"
    md_path = OUT_DIR / f"recipe_target_audit_{timestamp}.md"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    md_path.write_text(render_markdown(rows, files_scanned), encoding="utf-8")
    return jsonl_path, md_path, rows


def render_markdown(rows, files_scanned) -> str:
    lines = ["# Recipe target audit", ""]
    lines.append(
        "Strict structural validation of every recipe-shaped training row "
        "in the v1 mix corpus."
    )
    lines.append("")
    lines.append("## Files scanned")
    lines.append("")
    lines.append("| File | Rows | Recipe rows |")
    lines.append("|---|---:|---:|")
    for path, n, n_r in files_scanned:
        lines.append(f"| `{path}` | {n} | {n_r} |")
    lines.append("")
    if not rows:
        lines.append("No recipe rows found.")
        return "\n".join(lines)
    total = len(rows)
    pct = lambda n: f"{100*n/total:.1f}%"

    strict = sum(1 for r in rows if r["strict_match"])
    pri_omega = sum(1 for r in rows if r["primary_omega_match"])
    side_omega = sum(1 for r in rows if r["side_omega_match"])
    coef = sum(1 for r in rows if r["coef_multiset_match"])
    side_kw = sum(1 for r in rows if r["side_kw_match"])
    has_lambda_count = sum(1 for r in rows if r["has_lambda"])
    noetic_clean = sum(1 for r in rows if not r["noetic_misses_at_terms"])
    domain_clean = sum(1 for r in rows if not r["domain_misses_at_terms"])
    drive_clean = sum(1 for r in rows if not r["drive_misses_at_terms"])
    register_clean = sum(1 for r in rows if not r["register_misses_at_terms"])

    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Total recipe rows: **{total}**")
    lines.append(f"- Strict match (all checks pass): **{strict} ({pct(strict)})**")
    lines.append(f"- Primary Ω preserved: {pri_omega} ({pct(pri_omega)})")
    lines.append(f"- Side Ω preserved (where present): {side_omega} ({pct(side_omega)})")
    lines.append(f"- Coefficient multiset preserved: {coef} ({pct(coef)})")
    lines.append(
        f"- Λ side-product mentioned (where present): {side_kw} ({pct(side_kw)}) "
        f"[Λ-bearing rows: {has_lambda_count}]"
    )
    lines.append(f"- All Noetic indicators present per term: {noetic_clean} ({pct(noetic_clean)})")
    lines.append(f"- All domain indicators present per term: {domain_clean} ({pct(domain_clean)})")
    lines.append(f"- All drive indicators present per term: {drive_clean} ({pct(drive_clean)})")
    lines.append(f"- All register indicators present per term: {register_clean} ({pct(register_clean)})")
    lines.append("")

    # By n_terms bucket
    lines.append("## By LHS term count")
    lines.append("")
    by_n = Counter(r["n_terms"] for r in rows)
    lines.append("| n_terms | Rows | Strict match |")
    lines.append("|---:|---:|---:|")
    for n in sorted(by_n):
        bucket = [r for r in rows if r["n_terms"] == n]
        sm = sum(1 for r in bucket if r["strict_match"])
        sm_pct = f"{100*sm/len(bucket):.1f}%"
        lines.append(f"| {n} | {len(bucket)} | {sm} ({sm_pct}) |")
    lines.append("")

    # Worst offenders
    failing = [r for r in rows if not r["strict_match"]]
    if failing:
        worst = sorted(
            failing,
            key=lambda r: (
                int(not r["primary_omega_match"])
                + int(not r["coef_multiset_match"])
                + int(not r["side_kw_match"])
                + (len(r["noetic_misses_at_terms"]) > 0)
                + (len(r["domain_misses_at_terms"]) > 0)
                + (len(r["drive_misses_at_terms"]) > 0)
            ),
            reverse=True,
        )[:6]
        lines.append("## Sample of worst offenders")
        lines.append("")
        for r in worst:
            lines.append(f"**id**: `{r['id']}` ({r['source_split']})")
            lines.append("")
            lines.append(f"- source: `{r['cas_expression'][:160]}`")
            lines.append(
                f"- checks: pri_Ω={r['primary_omega_match']} "
                f"side_Ω={r['side_omega_match']} "
                f"coef={r['coef_multiset_match']} "
                f"sideΛ={r['side_kw_match']} "
                f"noetic_misses={r['noetic_misses_at_terms']} "
                f"domain_misses={r['domain_misses_at_terms']} "
                f"drive_misses={r['drive_misses_at_terms']}"
            )
            lines.append(f"- target: {r['target_text'][:240]}")
            lines.append("")
    return "\n".join(lines)


def main():
    print("Auditing recipe training targets with strict validator...")
    jsonl_path, md_path, rows = run_audit()
    print()
    print(f"Audit JSONL: {jsonl_path}")
    print(f"Audit report: {md_path}")
    print()
    if rows:
        strict = sum(1 for r in rows if r["strict_match"])
        total = len(rows)
        print(
            f"Headline: {strict}/{total} ({100*strict/total:.1f}%) recipe "
            f"training rows pass strict structural validation."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
