"""Path D Wave 2 — Invalid CAS generator.

Path D corpus pipeline §2 deliverable D: produce invalid CAS expressions in
instructive ways for the two repair-track tasks (`invalid_to_explanation`
and `invalid_to_corrected`). Each invalid sample MUST FAIL the compiler in
a known, classified way. Samples that compile cleanly are bugs.

Read the design memo before extending:
  docs/working/path_D_corpus_pipeline_design_2026_05_07.md   (sprint kickoff)
  docs/working/path_D_compiler_fluency_curriculum_2026_05_07.md  (§6 tasks 3+4)

Inputs:
  cas-synthetic/data/path_d/seeds.jsonl  (5802 compiler-validated bases)

Outputs:
  cas-synthetic/data/path_d/invalids.jsonl                 (~6K invalid samples)
  cas-synthetic/data/path_d/invalids_coverage_report.md     (per-class stats)

Mutation classes (each invalid sample is tagged with its `error_class`):

  parse          syntax errors that fail the lexer/parser before typecheck
  admissibility  parse cleanly but fail typecheck (unknown noetic, bad
                 register, x-without-omega, etc.)
  rpm            RPM chain ordering / prerequisite violations (compiler
                 catches these as undefined-variable / domain-descent
                 errors)
  recipe         Θ(...) recipe stoichiometry violations
  meta_logic     set/relation violations (CoverOf non-subset, PartitionOf
                 overlap or non-cover, malformed cluster)
  fractal        Cognitive Fractal sequence violations (digit out of
                 range, empty, non-digit content)

Per-invalid record schema (JSONL):
  {
    "invalid_id": "inv_<seed_id>_<error_class>_<i>",
    "source_seed_id": "<seed_id>",
    "mutation_type": "<specific mutation>",
    "error_class": "parse|admissibility|rpm|recipe|meta_logic|fractal",
    "expression": "<the broken CAS>",
    "corrected_form": "<original seed expression>",
    "compiler_validated": false,
    "compiler_error_message": "<verbatim compiler error>",
    "compiler_error_type": "CompilerError",
    "axes_in_corrected_form": {...}
  }

Distribution targets (approximate):
  parse           ~1000
  admissibility   ~1000
  recipe          ~1000
  meta_logic+fractal ~1000 total
  rpm             ~500-1000 (limited by thin rpm_chain seed lane)
  remainder distributed across categories to hit ~6K total

Hard constraints:
  - Don't modify the compiler.
  - Don't modify seeds.jsonl.
  - Don't ship samples that COMPILE. Every record must be rejected.
  - Capture the compiler's error message verbatim in
    `compiler_error_message`.

Usage:
  python -m cas_synthetic.scripts.generate_path_d_invalids \
      --seeds cas-synthetic/data/path_d/seeds.jsonl \
      --out cas-synthetic/data/path_d \
      --target 6000 \
      --seed 4242
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

# ---------------------------------------------------------------------------
# Compiler loader (same pattern as generate_path_d_seeds.py).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPILER_PATH = (
    _REPO_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)


def _load_compiler():
    module_name = "cas_synthetic_path_d_invalids_compiler"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"could not load compiler module from {_COMPILER_PATH}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Vocabulary constants (mirror compiler.py canonical names).
# ---------------------------------------------------------------------------

NOETICS = list(range(10))
DOMAINS = ("P", "C", "E", "O")
DRIVES = (1, 2, 3, 4, 5, 6, 7)
REGISTERS = ("T", "A", "f", "E")  # CAS v7.5
INVALID_REGISTERS = ("X", "Y", "Z", "B", "S", "M", "g", "v", "x", "a", "t", "F")
INVALID_NOETICS = (10, 11, 12, 13, 15, 20, 99)
INVALID_DOMAINS = ("Q", "Z", "X", "K", "W")
INVALID_DRIVES = (0, 8, 9, 10, 11)
INVALID_FRACTAL_DIGITS = (10, 11, 13, 17, 99)


# ---------------------------------------------------------------------------
# Invalid record schema.
# ---------------------------------------------------------------------------


@dataclass
class InvalidRecord:
    invalid_id: str
    source_seed_id: str
    mutation_type: str
    error_class: str
    expression: str
    corrected_form: str
    compiler_validated: bool
    compiler_error_message: str
    compiler_error_type: str
    axes_in_corrected_form: dict[str, Any]

    def to_record(self) -> dict[str, Any]:
        return {
            "invalid_id": self.invalid_id,
            "source_seed_id": self.source_seed_id,
            "mutation_type": self.mutation_type,
            "error_class": self.error_class,
            "expression": self.expression,
            "corrected_form": self.corrected_form,
            "compiler_validated": self.compiler_validated,
            "compiler_error_message": self.compiler_error_message,
            "compiler_error_type": self.compiler_error_type,
            "axes_in_corrected_form": self.axes_in_corrected_form,
        }


# ---------------------------------------------------------------------------
# Surface-form regexes used by mutators (lightweight; mutator returns None
# when the seed has no matching surface to mutate).
# ---------------------------------------------------------------------------

_RE_NOETIC_SUP = re.compile(r"\^(\d)(?!\d)")            # ^N  (one digit)
_RE_DOMAIN_SUP = re.compile(r"(\^\d)\^([PCEO])")          # ^N^D
_RE_DRIVE = re.compile(r"_\{F([1-7])\}")                  # _{F1..7}
_RE_REGISTER_SINGLE = re.compile(r"\|([TAfE])(?![a-zA-Z])")
_RE_REGISTER_SET = re.compile(r"\|⟨([TAfE,\s]+)⟩")
_RE_THETA_KW = re.compile(r"\b(?:Theta|Θ)\b")
_RE_OMEGA_KW = re.compile(r"\b(?:Omega|Ω)")
_RE_ARROW = re.compile(r"→|->")
_RE_FRACTAL_HEAD = re.compile(r"(?:Phi|Φ)")
_RE_FRACTAL_BODY = re.compile(r"(?:Phi|Φ)\s*[<⟨]\s*([0-9:\s]+?)\s*[>⟩]")
_RE_LET = re.compile(r"\blet\b")
_RE_OPENING_PAREN = re.compile(r"\(")
_RE_OPENING_BRACE = re.compile(r"\{")
_RE_OPENING_LANGLE = re.compile(r"⟨")
_RE_RECIPE_PREREQ_TIMES = re.compile(r"(\d+(?:\.\d+)?)(\s*)\*(\s*)")  # `1*X` style
_RE_RECIPE_FULL = re.compile(
    r"(?:Theta|Θ)\(\s*((?:Omega|Ω)_\w+)\s*\)\s*=\s*(.+?)\s*(?:→|->)\s*((?:Omega|Ω)_\w+)"
)


# ---------------------------------------------------------------------------
# Axis extractor — copied (light) from generate_path_d_seeds for parity.
# ---------------------------------------------------------------------------

_RE_AXIS_DOMAIN = re.compile(r"\^\d\^([PCEO])")
_RE_AXIS_DRIVE = re.compile(r"F([1-7])")
_RE_AXIS_REG_SINGLE = re.compile(r"\|([TAfE])(?![a-zA-Z])")
_RE_AXIS_REG_SET = re.compile(r"\|⟨([TAfE,\s]+)⟩")
_RE_AXIS_OPS = {
    "+": re.compile(r"(?<![\w])\+"),
    "×": re.compile(r"×"),
    "∘": re.compile(r"∘"),
    "→": re.compile(r"→|->"),
    "=": re.compile(r"(?<![<>!:])=(?!=)"),
    "Θ": re.compile(r"Θ|Theta"),
    "Ω": re.compile(r"Ω"),
    "·": re.compile(r"·"),
    "*": re.compile(r"\*"),
}


def _extract_axes(expr: str) -> dict[str, list[Any]]:
    noetics = sorted({int(m) for m in _RE_NOETIC_SUP.findall(expr)})
    domains = sorted(set(_RE_AXIS_DOMAIN.findall(expr)))
    drives = sorted({int(m) for m in _RE_AXIS_DRIVE.findall(expr)})
    regs_single = set(_RE_AXIS_REG_SINGLE.findall(expr))
    regs_set: set[str] = set()
    for m in _RE_AXIS_REG_SET.finditer(expr):
        for piece in m.group(1).split(","):
            r = piece.strip()
            if r:
                regs_set.add(r)
    registers = sorted(regs_single | regs_set)
    operators = [name for name, rx in _RE_AXIS_OPS.items() if rx.search(expr)]
    return {
        "noetics_used": noetics,
        "domains_used": domains,
        "drives_used": drives,
        "registers_used": registers,
        "operators_used": operators,
    }


# ---------------------------------------------------------------------------
# Mutator helpers.  Each mutator takes a seed-record dict and an rng and
# returns either (mutated_expression, mutation_type) or None (mutation
# inapplicable to this seed).
# ---------------------------------------------------------------------------


Mutation = tuple[str, str]  # (expression, mutation_type)
Mutator = Callable[[dict[str, Any], random.Random], Mutation | None]


# ----- parse mutators ------------------------------------------------------


def mut_drop_closing_paren(seed: dict[str, Any], rng: random.Random) -> Mutation | None:
    expr = seed["expression"]
    if ")" not in expr:
        return None
    # Drop the last `)`.
    idx = expr.rfind(")")
    return expr[:idx] + expr[idx + 1 :], "dropped_closing_paren"


def mut_drop_closing_brace(seed: dict[str, Any], rng: random.Random) -> Mutation | None:
    expr = seed["expression"]
    if "}" not in expr:
        return None
    idx = expr.rfind("}")
    return expr[:idx] + expr[idx + 1 :], "dropped_closing_brace"


def mut_drop_closing_rangle(seed: dict[str, Any], rng: random.Random) -> Mutation | None:
    expr = seed["expression"]
    if "⟩" not in expr:
        return None
    idx = expr.rfind("⟩")
    return expr[:idx] + expr[idx + 1 :], "dropped_closing_rangle"


def mut_drop_closing_ascii_gt(seed: dict[str, Any], rng: random.Random) -> Mutation | None:
    expr = seed["expression"]
    if "<" not in expr or ">" not in expr or "Phi" not in expr:
        return None
    idx = expr.rfind(">")
    return expr[:idx] + expr[idx + 1 :], "dropped_closing_ascii_gt"


def mut_dangling_caret(seed: dict[str, Any], rng: random.Random) -> Mutation | None:
    expr = seed["expression"]
    matches = list(_RE_DOMAIN_SUP.finditer(expr))
    if not matches:
        return None
    # Skip the LAST state literal in cross-register `(... × ... × ...) = ^N^D|Ω_x`
    # form because the right-side `^N^D` is followed by `|Ω_xxx` and dropping
    # the domain leaves `^N^|Ω_xxx` which the compiler accepts (parses the
    # `|Ω_xxx` as register-name on a missing-domain literal). Pick from
    # earlier matches instead.
    if "|Ω_" in expr or "|Omega_" in expr:
        # Filter out the last match if it's followed shortly by `|Ω_` or `|Omega_`.
        filtered = []
        for m in matches:
            tail = expr[m.end() : m.end() + 12]
            if tail.startswith(("|Ω_", "|Omega_")):
                continue
            filtered.append(m)
        if not filtered:
            return None
        pick = rng.choice(filtered)
    else:
        pick = rng.choice(matches)
    # Replace `^N^D` with `^N^` (drop the domain letter).
    new_expr = expr[: pick.start()] + pick.group(1) + "^" + expr[pick.end() :]
    return new_expr, "dangling_caret_no_domain"


def mut_corrupt_drive_subscript(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    # Drive-subscript typecheck has a known gap inside recipe-prereq
    # positions (`Θ(Ω_x) = 0.7*^1^C_{F10} → Ω_x` compiles despite the F10
    # being out of range). Skip recipe seeds — drive corruption alone is
    # not a guaranteed-fail on those. The dropped_closing_brace and
    # dangling_caret mutations cover recipe seeds via parse failures.
    if _RE_THETA_KW.search(expr):
        return None
    matches = list(_RE_DRIVE.finditer(expr))
    if not matches:
        return None
    pick = rng.choice(matches)
    bad = rng.choice(INVALID_DRIVES)
    new_expr = expr[: pick.start()] + f"_{{F{bad}}}" + expr[pick.end() :]
    return new_expr, f"corrupted_drive_F{bad}"


def mut_swap_plus_for_times_in_recipe(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    if not _RE_THETA_KW.search(expr):
        return None
    # Replace coefficient `*` with `+` so `1*X` becomes `1+X`.
    m = _RE_RECIPE_PREREQ_TIMES.search(expr)
    if not m:
        return None
    new_expr = (
        expr[: m.start()] + m.group(1) + m.group(2) + "+" + m.group(3) + expr[m.end() :]
    )
    return new_expr, "recipe_swap_times_for_plus"


def mut_truncate_recipe_before_arrow(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    if not _RE_THETA_KW.search(expr):
        return None
    m = _RE_ARROW.search(expr)
    if not m:
        return None
    new_expr = expr[: m.start()].rstrip()
    if not new_expr:
        return None
    return new_expr, "recipe_truncate_before_arrow"


def mut_misplace_colon_in_fractal(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    if not _RE_FRACTAL_HEAD.search(expr):
        return None
    # Replace the LANGLE/`<` with COLON: `Φ⟨2:9⟩` -> `Φ:2:9⟩`.
    if "⟨" in expr:
        return expr.replace("⟨", ":", 1), "fractal_misplaced_colon_unicode"
    if "<" in expr:
        return expr.replace("<", ":", 1), "fractal_misplaced_colon_ascii"
    return None


def mut_remove_fractal_colons(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    m = _RE_FRACTAL_BODY.search(expr)
    if not m:
        return None
    body = m.group(1)
    if ":" not in body:
        return None
    new_body = body.replace(":", " ")
    new_expr = expr[: m.start(1)] + new_body + expr[m.end(1) :]
    return new_expr, "fractal_remove_colons"


def mut_drop_comma_in_cluster(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    if "}" not in expr or "," not in expr:
        return None
    # Find the body inside the first `{...}`.
    open_idx = expr.find("{")
    close_idx = expr.find("}", open_idx)
    if open_idx == -1 or close_idx == -1:
        return None
    body = expr[open_idx + 1 : close_idx]
    if "," not in body:
        return None
    # Drop a random comma from that body.
    commas = [i for i, ch in enumerate(body) if ch == ","]
    pick = rng.choice(commas)
    new_body = body[:pick] + " " + body[pick + 1 :]
    new_expr = expr[: open_idx + 1] + new_body + expr[close_idx:]
    return new_expr, "cluster_drop_comma"


# ----- admissibility mutators ---------------------------------------------


def mut_unknown_noetic_index(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    # Recipe prerequisites have a typecheck gap for noetic-out-of-range
    # (`Θ(Ω_x) = 0.7*^11^C → Ω_x` compiles). Skip recipe seeds so this
    # mutation always rejects.
    if _RE_THETA_KW.search(expr):
        return None
    matches = list(_RE_NOETIC_SUP.finditer(expr))
    if not matches:
        return None
    # Cross-register expressions of the form `(...) = ^N^D|Ω_x` carry an
    # `^N^D|Ω_xxx` site on the right where bumping the noetic doesn't
    # trigger typecheck (the `|Ω_xxx` is treated as register/name path).
    # Same gap exists for the no-domain shape `^N|Ω_x`. Filter both.
    if "|Ω_" in expr or "|Omega_" in expr:
        filtered = []
        for m in matches:
            tail = expr[m.end() : m.end() + 16]
            # `^N` consumed; tail starts with optional `^D` then `|Ω_…`.
            if re.match(r"(?:\^[PCEO])?\|(?:Ω_|Omega_)", tail):
                continue
            filtered.append(m)
        if not filtered:
            return None
        pick = rng.choice(filtered)
    else:
        pick = rng.choice(matches)
    bad = rng.choice(INVALID_NOETICS)
    # Replace `^N` with `^<bad>` (multi-digit forces the typecheck path).
    new_expr = expr[: pick.start()] + f"^{bad}" + expr[pick.end() :]
    return new_expr, f"unknown_noetic_{bad}"


def mut_unknown_domain(seed: dict[str, Any], rng: random.Random) -> Mutation | None:
    expr = seed["expression"]
    matches = list(_RE_DOMAIN_SUP.finditer(expr))
    if not matches:
        return None
    # Same `|Ω_xxx` filter as the noetic-mutator: the right-side state in
    # `(...) = ^N^D|Ω_xxx` parses with a bad domain because the `|Ω_xxx`
    # path treats it as register-or-name.
    if "|Ω_" in expr or "|Omega_" in expr:
        filtered = []
        for m in matches:
            tail = expr[m.end() : m.end() + 16]
            if tail.startswith(("|Ω_", "|Omega_")):
                continue
            filtered.append(m)
        if not filtered:
            return None
        pick = rng.choice(filtered)
    else:
        pick = rng.choice(matches)
    bad = rng.choice(INVALID_DOMAINS)
    new_expr = expr[: pick.start()] + pick.group(1) + "^" + bad + expr[pick.end() :]
    return new_expr, f"unknown_domain_{bad}"


def mut_invalid_register(seed: dict[str, Any], rng: random.Random) -> Mutation | None:
    expr = seed["expression"]
    matches = list(_RE_REGISTER_SINGLE.finditer(expr))
    if not matches:
        return None
    pick = rng.choice(matches)
    bad = rng.choice(INVALID_REGISTERS)
    # Make sure we pick a truly invalid register.
    while bad in REGISTERS:
        bad = rng.choice(INVALID_REGISTERS)
    new_expr = expr[: pick.start()] + "|" + bad + expr[pick.end() :]
    return new_expr, f"invalid_register_{bad}"


def mut_duplicate_register_in_set(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Force a duplicate-register multi-set on a state that already has a
    single-register tag. Constructs `|⟨R,R,A⟩` from a `|R` site."""
    expr = seed["expression"]
    matches = list(_RE_REGISTER_SINGLE.finditer(expr))
    if not matches:
        return None
    pick = rng.choice(matches)
    r = pick.group(1)
    other = rng.choice([x for x in REGISTERS if x != r])
    new_tag = f"|⟨{r},{r},{other}⟩"
    new_expr = expr[: pick.start()] + new_tag + expr[pick.end() :]
    return new_expr, f"duplicate_register_set_{r}{r}{other}"


def mut_invalid_register_in_set(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Inject an invalid register letter into a `|⟨...⟩` set."""
    expr = seed["expression"]
    matches = list(_RE_REGISTER_SET.finditer(expr))
    if not matches:
        # Synthesize from a single `|R` site instead.
        single = list(_RE_REGISTER_SINGLE.finditer(expr))
        if not single:
            return None
        pick = rng.choice(single)
        r = pick.group(1)
        bad = rng.choice([x for x in INVALID_REGISTERS if x not in REGISTERS])
        new_tag = f"|⟨{r},{bad}⟩"
        new_expr = expr[: pick.start()] + new_tag + expr[pick.end() :]
        return new_expr, f"invalid_register_in_set_{bad}"
    pick = rng.choice(matches)
    body = pick.group(1)
    bad = rng.choice([x for x in INVALID_REGISTERS if x not in REGISTERS])
    pieces = [p.strip() for p in body.split(",") if p.strip()]
    pieces.append(bad)
    new_tag = "|⟨" + ",".join(pieces) + "⟩"
    new_expr = expr[: pick.start()] + new_tag + expr[pick.end() :]
    return new_expr, f"invalid_register_in_set_{bad}"


def mut_cross_register_without_omega(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Generate `(^N^D|R1 × ^N^D|R2)` without the named-emergent target.

    This is a CAS v7.7 admissibility violation per Clarification 10 §4.
    The mutator constructs a fresh same-Noetic multi-register expression
    independent of the seed's exact form, but tags it back to that seed so
    the corrected_form preserves the seed expression as repair target.
    """
    n = rng.randint(0, 9)
    d = rng.choice(DOMAINS)
    r1, r2 = rng.sample(REGISTERS, 2)
    expr = f"(^{n}^{d}|{r1} × ^{n}^{d}|{r2})"
    return expr, f"cross_register_no_omega_{r1}{r2}"


def mut_cross_register_three_no_omega(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    n = rng.randint(0, 9)
    d = rng.choice(DOMAINS)
    r1, r2, r3 = rng.sample(REGISTERS, 3)
    expr = f"(^{n}^{d}|{r1} × ^{n}^{d}|{r2} × ^{n}^{d}|{r3})"
    return expr, f"cross_register_three_no_omega_{r1}{r2}{r3}"


# ----- recipe mutators ----------------------------------------------------


def mut_recipe_drop_theta_wrapper(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    if not _RE_THETA_KW.search(expr):
        return None
    # Drop everything from start of expression up through `Theta(Ω_xxx) = `
    # leaving just `<prereqs> -> Ω_target`. This makes a bare equation that
    # parses to a different shape and gets caught at typecheck.
    # Actually simpler and more robust: replace `Theta(Ω_xxx) = ` prefix
    # with `Ω_xxx = ` so the recipe wrapper is gone.
    m = re.search(r"(?:Theta|Θ)\((Omega_\w+|Ω_\w+)\)\s*=\s*", expr)
    if not m:
        return None
    new_expr = expr[: m.start()] + m.group(1) + " = " + expr[m.end() :]
    return new_expr, "recipe_drop_theta_wrapper"


def mut_recipe_missing_arrow(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    if not _RE_THETA_KW.search(expr):
        return None
    m = _RE_ARROW.search(expr)
    if not m:
        return None
    # Drop the arrow and everything after it (tail must be re-added if
    # there was none, so keep the tail empty).
    # Strip both arrow and the named target after it; we want: prereqs
    # followed by EOF so the parser sees "expected `→` after prereqs".
    head = expr[: m.start()].rstrip()
    if not head:
        return None
    return head, "recipe_missing_arrow"


def mut_recipe_missing_target(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Force `Theta() = ...` — empty inside the parens."""
    expr = seed["expression"]
    m = re.search(r"(?:Theta|Θ)\(\s*(?:Omega_\w+|Ω_\w+)\s*\)", expr)
    if not m:
        return None
    new_expr = expr[: m.start()] + "Theta()" + expr[m.end() :]
    return new_expr, "recipe_empty_target_parens"


def mut_recipe_missing_coefficient(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Drop the leading numeric coefficient on a recipe ingredient."""
    expr = seed["expression"]
    if not _RE_THETA_KW.search(expr):
        return None
    m = _RE_RECIPE_PREREQ_TIMES.search(expr)
    if not m:
        return None
    # `1*X` -> `X` (drop the coefficient AND the `*`).
    new_expr = expr[: m.start()] + expr[m.end() :]
    return new_expr, "recipe_missing_coefficient"


def mut_recipe_missing_equals(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Replace `Theta(Ω_x) = ...` with `Theta(Ω_x) ...` — drop the `=`."""
    expr = seed["expression"]
    m = re.search(r"((?:Theta|Θ)\(\s*(?:Omega_\w+|Ω_\w+)\s*\))\s*=\s*", expr)
    if not m:
        return None
    new_expr = expr[: m.start()] + m.group(1) + " " + expr[m.end() :]
    return new_expr, "recipe_missing_equals"


def mut_recipe_misplace_arrow_for_equals(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Replace `Theta(Ω_x) = ...` with `Theta(Ω_x) → ...` — bad operator."""
    expr = seed["expression"]
    m = re.search(r"((?:Theta|Θ)\(\s*(?:Omega_\w+|Ω_\w+)\s*\))\s*=\s*", expr)
    if not m:
        return None
    new_expr = expr[: m.start()] + m.group(1) + " → " + expr[m.end() :]
    return new_expr, "recipe_arrow_for_equals"


# ----- meta_logic mutators -----------------------------------------------


def mut_coverof_non_subset(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Construct CoverOf(base, member) where member is NOT a subset of base."""
    base_size = rng.randint(3, 5)
    base = sorted(rng.sample(NOETICS, base_size))
    # Choose a member that has at least one element NOT in base.
    leftover = [n for n in NOETICS if n not in base]
    if not leftover:
        return None
    member = sorted({rng.choice(leftover)} | set(rng.sample(base, k=min(2, len(base)))))
    base_str = ", ".join(f"^{n}" for n in base)
    member_str = ", ".join(f"^{n}" for n in member)
    expr = (
        f"CoverOf(NoeticCluster{{{base_str}}}, NoeticCluster{{{member_str}}})"
    )
    return expr, "coverof_non_subset_member"


def mut_partitionof_overlap(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Construct PartitionOf(base, member1, member2) where members overlap."""
    base = sorted(rng.sample(NOETICS, k=4))
    a, b, c, d = base
    # Overlapping members on element `b`.
    m1 = sorted({a, b})
    m2 = sorted({b, c})
    base_str = ", ".join(f"^{n}" for n in base)
    m1_str = ", ".join(f"^{n}" for n in m1)
    m2_str = ", ".join(f"^{n}" for n in m2)
    expr = (
        f"PartitionOf(NoeticCluster{{{base_str}}}, "
        f"NoeticCluster{{{m1_str}}}, NoeticCluster{{{m2_str}}})"
    )
    return expr, "partitionof_overlap"


def mut_partitionof_undercover(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """PartitionOf(base, member1, member2) where members do not cover base."""
    base = sorted(rng.sample(NOETICS, k=4))
    a, b, c, d = base
    m1 = [a]
    m2 = [b]
    base_str = ", ".join(f"^{n}" for n in base)
    m1_str = ", ".join(f"^{n}" for n in m1)
    m2_str = ", ".join(f"^{n}" for n in m2)
    expr = (
        f"PartitionOf(NoeticCluster{{{base_str}}}, "
        f"NoeticCluster{{{m1_str}}}, NoeticCluster{{{m2_str}}})"
    )
    return expr, "partitionof_undercover"


def mut_meta_cluster_bad_noetic(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Inject an out-of-range noetic into a NoeticCluster body."""
    expr = seed["expression"]
    if "NoeticCluster{" not in expr and "StateSet{" not in expr:
        return None
    # Locate first `{...}` body.
    open_idx = expr.find("{")
    close_idx = expr.find("}", open_idx)
    if open_idx == -1 or close_idx == -1:
        return None
    body = expr[open_idx + 1 : close_idx]
    bad = rng.choice(INVALID_NOETICS)
    if body.strip():
        new_body = body + f", ^{bad}"
    else:
        new_body = f"^{bad}"
    new_expr = expr[: open_idx + 1] + new_body + expr[close_idx:]
    return new_expr, f"meta_cluster_bad_noetic_{bad}"


# ----- fractal mutators ---------------------------------------------------


def mut_fractal_digit_out_of_range(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    m = _RE_FRACTAL_BODY.search(expr)
    if not m:
        return None
    body = m.group(1).strip()
    parts = [p for p in body.split(":") if p.strip()]
    if not parts:
        return None
    bad = rng.choice(INVALID_FRACTAL_DIGITS)
    pos = rng.randrange(len(parts))
    parts[pos] = str(bad)
    new_body = ":".join(parts)
    new_expr = expr[: m.start(1)] + new_body + expr[m.end(1) :]
    return new_expr, f"fractal_digit_out_of_range_{bad}"


def mut_fractal_empty_sequence(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    m = _RE_FRACTAL_BODY.search(expr)
    if not m:
        return None
    new_expr = expr[: m.start(1)] + expr[m.end(1) :]
    # Now expr looks like `Φ⟨⟩` or `Phi<>`.
    return new_expr, "fractal_empty_sequence"


def mut_fractal_non_digit(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    m = _RE_FRACTAL_BODY.search(expr)
    if not m:
        return None
    body = m.group(1).strip()
    parts = [p for p in body.split(":") if p.strip()]
    if not parts:
        return None
    junk = rng.choice(["X", "Y", "Z", "abc", "foo"])
    pos = rng.randrange(len(parts))
    parts[pos] = junk
    new_body = ":".join(parts)
    new_expr = expr[: m.start(1)] + new_body + expr[m.end(1) :]
    return new_expr, f"fractal_non_digit_{junk}"


def mut_fractal_negative_digit(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    expr = seed["expression"]
    m = _RE_FRACTAL_BODY.search(expr)
    if not m:
        return None
    body = m.group(1).strip()
    parts = [p for p in body.split(":") if p.strip()]
    if not parts:
        return None
    pos = rng.randrange(len(parts))
    parts[pos] = "-1"
    new_body = ":".join(parts)
    new_expr = expr[: m.start(1)] + new_body + expr[m.end(1) :]
    return new_expr, "fractal_negative_digit"


# ----- rpm mutators -------------------------------------------------------


def mut_rpm_skip_intermediate_stages(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Construct `let stageA0=^0^P; stageA0 -> stageP_k` where stageP_k is
    NEVER let-bound. The compiler raises `undefined variable stageP_k` —
    this is a structural RPM violation: A0→P jumps over the D and W
    intermediate stages.
    """
    drive = rng.choice(DRIVES)
    uid = f"{drive}_{rng.randrange(10000):04d}"
    expr = f"let stageA0_{uid} = ^0^P; stageA0_{uid} -> stageP_{uid}"
    return expr, "rpm_skip_to_undefined_stageP"


def mut_rpm_skip_to_W(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    drive = rng.choice(DRIVES)
    uid = f"{drive}_{rng.randrange(10000):04d}"
    expr = f"let stageA0_{uid} = ^0^P; stageA0_{uid} -> stageW_{uid}"
    return expr, "rpm_skip_to_undefined_stageW"


def mut_rpm_undefined_chain(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Reference both stages without ever defining them — RPM chain that
    skips A0 entirely."""
    drive = rng.choice(DRIVES)
    uid = f"{drive}_{rng.randrange(10000):04d}"
    expr = f"stageD{drive}_{uid} -> stageW{drive}_{uid}"
    return expr, "rpm_no_let_undefined_stages"


def mut_rpm_domain_descent_violation(
    seed: dict[str, Any], rng: random.Random
) -> Mutation | None:
    """Domain descent must go P→C→E→O. Construct a backwards descent like
    C→P or E→C, which the compiler catches as a domain-descent violation.

    This is a structural RPM violation: stages must descend in the
    correct domain order.
    """
    # Pairs that violate descent.
    bad_pairs = [
        ("C", "P"),
        ("E", "P"),
        ("O", "P"),
        ("E", "C"),
        ("O", "C"),
        ("O", "E"),
    ]
    src_d, dst_d = rng.choice(bad_pairs)
    drive = rng.choice(DRIVES)
    uid = f"{drive}_{rng.randrange(10000):04d}"
    expr = (
        f"let stageA_{uid} = ^3^{src_d}_{{F{drive}}}; "
        f"let stageB_{uid} = ^3^{dst_d}_{{F{drive}}}; "
        f"stageA_{uid} -> stageB_{uid}"
    )
    return expr, f"rpm_domain_descent_{src_d}_to_{dst_d}"


# ---------------------------------------------------------------------------
# Mutator registry — grouped by error_class so the generator can target a
# distribution.
# ---------------------------------------------------------------------------


MUTATORS_BY_CLASS: dict[str, list[Mutator]] = {
    "parse": [
        mut_drop_closing_paren,
        mut_drop_closing_brace,
        mut_drop_closing_rangle,
        mut_drop_closing_ascii_gt,
        mut_dangling_caret,
        mut_corrupt_drive_subscript,
        mut_swap_plus_for_times_in_recipe,
        mut_truncate_recipe_before_arrow,
        mut_misplace_colon_in_fractal,
        mut_remove_fractal_colons,
        mut_drop_comma_in_cluster,
    ],
    "admissibility": [
        mut_unknown_noetic_index,
        mut_unknown_domain,
        mut_invalid_register,
        mut_duplicate_register_in_set,
        mut_invalid_register_in_set,
        mut_cross_register_without_omega,
        mut_cross_register_three_no_omega,
    ],
    "rpm": [
        mut_rpm_skip_intermediate_stages,
        mut_rpm_skip_to_W,
        mut_rpm_undefined_chain,
        mut_rpm_domain_descent_violation,
    ],
    "recipe": [
        mut_recipe_drop_theta_wrapper,
        mut_recipe_missing_arrow,
        mut_recipe_missing_target,
        mut_recipe_missing_coefficient,
        mut_recipe_missing_equals,
        mut_recipe_misplace_arrow_for_equals,
    ],
    "meta_logic": [
        mut_coverof_non_subset,
        mut_partitionof_overlap,
        mut_partitionof_undercover,
        mut_meta_cluster_bad_noetic,
    ],
    "fractal": [
        mut_fractal_digit_out_of_range,
        mut_fractal_empty_sequence,
        mut_fractal_non_digit,
        mut_fractal_negative_digit,
    ],
}


# Which seed grammar categories are best for each error class. Mutators
# that don't depend on the seed (e.g. cross_register_without_omega, the
# RPM constructors, meta_logic constructors) are always applicable.
ELIGIBLE_SEED_CATEGORIES: dict[str, set[str] | None] = {
    "parse": None,                   # any seed
    "admissibility": None,           # any seed
    "rpm": None,                     # constructed independently
    "recipe": {"recipe", "diagram_export"},
    "meta_logic": {"meta_logic_relation", "diagram_export"},
    "fractal": {"fractal_sequence"},
}


# ---------------------------------------------------------------------------
# Generator core.
# ---------------------------------------------------------------------------


# Default per-class distribution shares (per the design memo: ~1K each
# for parse/admissibility/recipe; ~1K total across meta_logic+fractal;
# ~500-1K for rpm). These shares sum to ~5200 with target_total=6000.
_DEFAULT_CLASS_TARGETS = {
    "parse": 1100,
    "admissibility": 1100,
    "recipe": 1000,
    "meta_logic": 600,
    "fractal": 600,
    "rpm": 800,
}


@dataclass
class InvalidGenerator:
    seeds: list[dict[str, Any]]
    target_total: int = 6000
    seed: int = 4242

    # Distribution targets per error class. Defaults to None and is
    # populated from _DEFAULT_CLASS_TARGETS scaled to target_total in
    # __post_init__.
    target_per_class: dict[str, int] | None = None

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        compiler_module = _load_compiler()
        self.compile_expression = compiler_module.compile_expression
        self.accepted: list[InvalidRecord] = []
        self.unexpected_compile: list[dict[str, Any]] = []
        self._counter: Counter = Counter()
        self._seeds_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for s in self.seeds:
            self._seeds_by_category[s.get("grammar_category", "")].append(s)
        if self.target_per_class is None:
            default_sum = sum(_DEFAULT_CLASS_TARGETS.values())
            scale = self.target_total / default_sum
            self.target_per_class = {
                k: max(1, int(round(v * scale)))
                for k, v in _DEFAULT_CLASS_TARGETS.items()
            }

    # -------------------------------------------------------------------

    def _sample_seeds_for(self, error_class: str, n: int) -> list[dict[str, Any]]:
        eligible = ELIGIBLE_SEED_CATEGORIES.get(error_class)
        if eligible is None:
            pool = list(self.seeds)
        else:
            pool = []
            for cat in eligible:
                pool.extend(self._seeds_by_category.get(cat, []))
            if not pool:
                pool = list(self.seeds)
        # Sample with replacement so we can reach distribution targets even
        # when the eligible pool is thin (e.g. fractal_sequence has 576).
        return [self.rng.choice(pool) for _ in range(n)]

    def _try_record(
        self,
        seed: dict[str, Any],
        error_class: str,
        expression: str,
        mutation_type: str,
    ) -> bool:
        artifact = self.compile_expression(expression)
        valid = bool(getattr(artifact, "valid", False))
        if valid:
            self.unexpected_compile.append(
                {
                    "source_seed_id": seed.get("seed_id", ""),
                    "error_class": error_class,
                    "mutation_type": mutation_type,
                    "expression": expression,
                    "corrected_form": seed["expression"],
                }
            )
            return False
        err_msg = getattr(artifact, "error", "") or ""
        idx = self._counter[error_class]
        self._counter[error_class] += 1
        invalid_id = f"inv_{seed.get('seed_id','seed')}_{error_class}_{idx:05d}"
        record = InvalidRecord(
            invalid_id=invalid_id,
            source_seed_id=seed.get("seed_id", ""),
            mutation_type=mutation_type,
            error_class=error_class,
            expression=expression,
            corrected_form=seed["expression"],
            compiler_validated=False,
            compiler_error_message=err_msg,
            compiler_error_type="CompilerError",
            axes_in_corrected_form=_extract_axes(seed["expression"]),
        )
        self.accepted.append(record)
        return True

    # -------------------------------------------------------------------

    def _apply_class(self, error_class: str, target_n: int) -> None:
        mutators = MUTATORS_BY_CLASS[error_class]
        # Over-sample to absorb mutator-inapplicable cases and unexpected
        # compiles. 2.5x the target is plenty.
        sample_pool = self._sample_seeds_for(error_class, target_n * 3)
        produced = 0
        # Round-robin through mutators so all surface forms get exercised.
        for i, seed_record in enumerate(sample_pool):
            if produced >= target_n:
                break
            mutator = mutators[i % len(mutators)]
            try:
                result = mutator(seed_record, self.rng)
            except Exception:
                continue
            if result is None:
                continue
            mutated_expr, mutation_type = result
            if mutated_expr == seed_record["expression"]:
                continue
            ok = self._try_record(
                seed_record, error_class, mutated_expr, mutation_type
            )
            if ok:
                produced += 1

    def run(self) -> None:
        for error_class, target_n in self.target_per_class.items():
            self._apply_class(error_class, target_n)


# ---------------------------------------------------------------------------
# Coverage report writer.
# ---------------------------------------------------------------------------


def _coverage_report(
    accepted: list[InvalidRecord],
    unexpected_compile: list[dict[str, Any]],
) -> str:
    total = len(accepted)
    total_attempted = total + len(unexpected_compile)
    rejection_rate = (total / total_attempted) if total_attempted else 0.0

    by_class = Counter(r.error_class for r in accepted)
    by_mutation = Counter(r.mutation_type for r in accepted)
    by_seed_category = Counter(
        r.axes_in_corrected_form.get("noetics_used", []) and "with_noetics" or "no_noetics"
        for r in accepted
    )

    # 7-category coverage rough proxy from corrected_form.
    seen_state_literal = sum(
        1 for r in accepted if any(d in r.corrected_form for d in ["P", "C", "E", "O"])
    )
    seen_drive = sum(
        1 for r in accepted if "_{F" in r.corrected_form
    )
    seen_register = sum(
        1 for r in accepted if "|T" in r.corrected_form or "|A" in r.corrected_form
        or "|f" in r.corrected_form or "|E" in r.corrected_form or "|⟨" in r.corrected_form
    )
    seen_operator = sum(
        1
        for r in accepted
        if any(op in r.corrected_form for op in ["+", "×", "→", "->", "∘"])
    )
    seen_recipe = sum(
        1 for r in accepted if "Theta" in r.corrected_form or "Θ" in r.corrected_form
    )
    seen_meta = sum(
        1
        for r in accepted
        if any(
            k in r.corrected_form
            for k in (
                "NoeticCluster",
                "StateSet",
                "RelationCluster",
                "Tuple",
                "Coordinate",
                "CoverOf",
                "PartitionOf",
                "Product",
                "∪",
                "∩",
                "∖",
            )
        )
    )
    seen_fractal = sum(
        1 for r in accepted if r.corrected_form.startswith(("Φ", "Phi"))
    )

    out: list[str] = []
    out.append("# Path D Wave 2D — Invalid CAS Coverage Report")
    out.append("")
    out.append(f"- Total invalid samples emitted: **{total}**")
    out.append(
        f"- Unexpected compiles (mutator bugs / compile-clean leaks): "
        f"**{len(unexpected_compile)}**"
    )
    out.append(f"- Compiler-rejection rate: **{rejection_rate:.4%}**")
    out.append("")
    out.append("## Per error_class counts")
    out.append("")
    out.append("| error_class | count |")
    out.append("|---|---|")
    for cls in sorted(by_class):
        out.append(f"| {cls} | {by_class[cls]} |")
    out.append("")
    out.append("## Per mutation_type counts (top 60)")
    out.append("")
    out.append("| mutation_type | count |")
    out.append("|---|---|")
    for mt, count in by_mutation.most_common(60):
        out.append(f"| {mt} | {count} |")
    out.append("")
    out.append("## 7-category surface coverage in `corrected_form`")
    out.append("")
    out.append("Each row counts how many invalid samples have the given category present in the original (correct) seed expression. Coverage check: every category should be exercised so the repair-track curriculum touches the full grammar surface.")
    out.append("")
    out.append("| category | seeds-with-surface |")
    out.append("|---|---|")
    out.append(f"| 1. state_literal | {seen_state_literal} |")
    out.append(f"| 2. drive subscripts | {seen_drive} |")
    out.append(f"| 3. registers | {seen_register} |")
    out.append(f"| 4. operators | {seen_operator} |")
    out.append(f"| 5. recipes (Θ) | {seen_recipe} |")
    out.append(f"| 6. meta-logic | {seen_meta} |")
    out.append(f"| 7. fractals | {seen_fractal} |")
    out.append("")
    if unexpected_compile:
        out.append("## Unexpected compiles (flag for compiler-team follow-up)")
        out.append("")
        out.append(
            "Samples below were emitted by a mutator but the compiler accepted them. "
            "Either the mutator is too weak (fix the mutator) or the compiler's check "
            "has a gap (file a follow-up). First 30 listed:"
        )
        out.append("")
        out.append("| mutation_type | error_class | expression |")
        out.append("|---|---|---|")
        for entry in unexpected_compile[:30]:
            ex = entry["expression"].replace("|", "\\|")
            out.append(
                f"| {entry['mutation_type']} | {entry['error_class']} | `{ex}` |"
            )
        out.append("")
    out.append("## Compiler-team follow-ups (gaps the mutator works around)")
    out.append("")
    out.append(
        "While building the mutators, three compiler typecheck gaps were identified. "
        "The mutators skip the affected seed shapes so every emitted sample rejects, "
        "but the compiler-team should consider tightening these checks:"
    )
    out.append("")
    out.append(
        "1. **Recipe prereq drive subscripts not typechecked.** "
        "`Θ(Ω_x) = 0.7*^1^C_{F10} → Ω_x` compiles cleanly even though `F10` is "
        "out of the F1–F7 range. Standalone `^1^C_{F10}` correctly rejects with "
        "`drive number must be 1-7`. The check should propagate into recipe-prereq "
        "positions. Workaround: `mut_corrupt_drive_subscript` skips recipe seeds."
    )
    out.append("")
    out.append(
        "2. **Recipe prereq noetic indices not typechecked.** "
        "`Θ(Ω_x) = 0.7*^11^C → Ω_x` compiles cleanly even though `^11` is "
        "out of the 0–9 range. Standalone `^11` correctly rejects with "
        "`operator index must be 0-9`. Same propagation issue as the drive case. "
        "Workaround: `mut_unknown_noetic_index` skips recipe seeds."
    )
    out.append("")
    out.append(
        "3. **Right-side `^N^D|Ω_xxx` in cross-register expressions accepts "
        "structurally bad domain/noetic.** `(^9^O|f × ^9^O|E) = ^9^|Ω_judgment` "
        "and `(^8|f × ^8|A) = ^10|Ω_trust` both compile cleanly. The `|Ω_xxx` "
        "register-or-name path appears to swallow malformed left-of-pipe content. "
        "Workaround: `mut_dangling_caret`, `mut_unknown_noetic_index`, and "
        "`mut_unknown_domain` filter out the `|Ω_…` site when picking a mutation "
        "target."
    )
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _read_seeds(path: Path) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            seeds.append(json.loads(line))
    return seeds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds",
        type=Path,
        default=Path("cas-synthetic/data/path_d/seeds.jsonl"),
        help="Path to compiler-validated seeds.jsonl",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("cas-synthetic/data/path_d"),
        help="Output directory; writes invalids.jsonl + invalids_coverage_report.md",
    )
    parser.add_argument("--target", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=4242)
    parser.add_argument(
        "--limit-seeds",
        type=int,
        default=0,
        help="Smoke testing: limit input seeds to this many (0 = all)",
    )
    args = parser.parse_args(argv)

    seeds = _read_seeds(args.seeds)
    if args.limit_seeds:
        seeds = seeds[: args.limit_seeds]
    if not seeds:
        raise SystemExit("no seeds loaded")

    gen = InvalidGenerator(
        seeds=seeds,
        target_total=args.target,
        seed=args.seed,
    )
    gen.run()

    args.out.mkdir(parents=True, exist_ok=True)
    out_jsonl = args.out / "invalids.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as handle:
        for record in gen.accepted:
            handle.write(json.dumps(record.to_record(), ensure_ascii=False))
            handle.write("\n")

    report = _coverage_report(gen.accepted, gen.unexpected_compile)
    (args.out / "invalids_coverage_report.md").write_text(report, encoding="utf-8")

    print(
        f"path_D invalids: emitted={len(gen.accepted)} "
        f"unexpected_compiles={len(gen.unexpected_compile)} "
        f"out={out_jsonl}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
