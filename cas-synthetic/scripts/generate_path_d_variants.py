"""Path D Wave 2C — Fiber/marginal variation transforms.

Path D corpus pipeline §2 deliverable C (`docs/working/
path_D_corpus_pipeline_design_2026_05_07.md`): generate ~3 contrastive
variants per compiler-validated seed CAS object. Each variant varies
exactly ONE fiber/marginal — drive intensity, register tag, operation
context, or commutative reorder — while PRESERVING the load-bearing
base of the seed (state literals, named Ω targets, Θ recipe wrappers,
fractal sequence digits).

This is the load-bearing data design from Path D §7 (contrastive readout
supervision) that defeats the silhouette-without-content failure mode the
v0 audit revealed: the model must learn what's load-bearing vs what's
modulation, because the corpus shows the same base producing controlled
variants.

Reads: `cas-synthetic/data/path_d/seeds.jsonl` (Wave 1B output).
Writes:
  cas-synthetic/data/path_d/variants.jsonl              (validated)
  cas-synthetic/data/path_d/variants_rejected.jsonl     (audit log)
  cas-synthetic/data/path_d/variants_coverage_report.md (coverage stats)

Per-variant schema (one JSONL record):

    {
      "variant_id": "var_<seed_id>_<i>",
      "source_seed_id": "<seed_id>",
      "variant_type": "drive_intensity | register | operation | order",
      "preserved_axes": [...],
      "varied_axes": [...],
      "expression": "<the CAS expression>",
      "compiler_validated": true,
      "axes": {...},                       # same schema as seeds.jsonl
      "n_state_literals": <int>,
      "uses_named_omega": <bool>,
      "uses_theta_recipe": <bool>,
      "uses_meta_logic": <bool>,
      "uses_fractal": <bool>,
      "delta_from_seed": "<short description>"
    }

Oversample policy (Wave 1B coverage thinness, per kickoff memo):
  - rpm_chain seeds → ≥3 variants each (target ratio 3.0)
  - inversion seeds → ≥5 variants each (target ratio 5.0)
  - all other categories → ~3 variants each on average

Hard rules:
  - Every variant compiler-validates via `api/notation/compiler.py`.
  - The BASE of the seed is preserved across all variants:
      * state-literal cores (^N^D occurrences and their order)
      * named Ω targets (Ω_<name>)
      * Θ recipe wrappers
      * fractal sequence digits
      * cluster member identities
  - Variants where ANY of the above shift are rejected before write.

Usage:
    python -m cas_synthetic.scripts.generate_path_d_variants \
        --seeds cas-synthetic/data/path_d/seeds.jsonl \
        --out cas-synthetic/data/path_d \
        --seed 4242

A `--limit N` flag truncates output (smoke runs / tests).
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Compiler loader — mirrors generate_path_d_seeds.py.
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
    module_name = "cas_synthetic_path_d_variants_compiler"
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
# Vocabulary constants (mirrors compiler.py / generate_path_d_seeds.py).
# ---------------------------------------------------------------------------

NOETICS = list(range(10))
DOMAINS = ("P", "C", "E", "O")
DRIVES = (1, 2, 3, 4, 5, 6, 7)
REGISTERS = ("T", "A", "f", "E")

DOMAIN_ORDER = {"P": 0, "C": 1, "E": 2, "O": 3}


# ---------------------------------------------------------------------------
# Regex helpers — extract / rewrite axis tokens without re-implementing
# the compiler grammar.
# ---------------------------------------------------------------------------

# Drive subscript inside `_{F_k}` braces.
_RE_DRIVE_SUB = re.compile(r"_\{F([1-7])\}")

# Single register `|R` (T / A / f / E) — but not when followed by `⟨` or letters.
_RE_REGISTER_SINGLE = re.compile(r"\|([TAfE])(?![a-zA-Z⟨])")

# Multi-register set `|⟨R1,R2[,R3,...]⟩`.
_RE_REGISTER_SET = re.compile(r"\|⟨([TAfE,\s]+)⟩")

# Named Ω targets: Ω_name (preserved across variants).
_RE_OMEGA_NAME = re.compile(r"Ω_([A-Za-z][A-Za-z0-9_]*)")

# Theta recipe wrapper start.
_RE_THETA_HEAD = re.compile(r"Θ\(Ω_([A-Za-z][A-Za-z0-9_]*)\)|Theta\(Omega_([A-Za-z][A-Za-z0-9_]*)\)")

# State literal cores (^N^D — domain attached). Preserved.
_RE_STATE_CORE = re.compile(r"\^(\d)\^([PCEO])")

# Bare Noetic ^N (no domain). Preserved.
_RE_BARE_NOETIC = re.compile(r"\^(\d)(?!\^?[PCEO\d])")

# Fractal sequence content `Phi<...>` / `Φ⟨...⟩`.
_RE_FRACTAL = re.compile(r"(Phi|Φ)([<⟨])([\d:]+)([>⟩])")


def _state_cores(expr: str) -> list[tuple[int, str]]:
    """Return (noetic, domain) pairs IN ORDER of appearance — load-bearing
    invariant: variants must reproduce this list exactly."""
    return [(int(n), d) for n, d in _RE_STATE_CORE.findall(expr)]


def _bare_noetics(expr: str) -> list[int]:
    """Bare-noetic count IN ORDER — for clusters / fractals / set ops."""
    return [int(m) for m in _RE_BARE_NOETIC.findall(expr)]


def _omega_names(expr: str) -> list[str]:
    return _RE_OMEGA_NAME.findall(expr)


def _has_theta(expr: str) -> bool:
    return bool(_RE_THETA_HEAD.search(expr))


def _fractal_signatures(expr: str) -> list[tuple[str, str]]:
    """Return [(head, sequence)] — head is `Phi` or `Φ`, sequence is the
    colon-joined digit string. Both must be preserved (head is allowed to
    swap only if the fractal-head swap is the explicit variation; default
    rule: preserve)."""
    return [(m.group(1), m.group(3)) for m in _RE_FRACTAL.finditer(expr)]


# ---------------------------------------------------------------------------
# Axis extraction (mirrors generate_path_d_seeds._extract_axes for
# coverage-report parity).
# ---------------------------------------------------------------------------

_RE_NOETIC_ANY = re.compile(r"\^(\d)(?!\d)")
_RE_DOMAIN_ATTACHED = re.compile(r"\^\d\^([PCEO])")
_RE_DRIVE_ANY = re.compile(r"F([1-7])")
_RE_OPS_TABLE = {
    "+": re.compile(r"(?<![\w])\+"),
    "×": re.compile(r"×"),
    "∘": re.compile(r"∘"),
    "→": re.compile(r"→|->"),
    "←": re.compile(r"←|<-"),
    "↔": re.compile(r"↔|<->"),
    "=": re.compile(r"(?<![<>!:])=(?!=)"),
    "Θ": re.compile(r"Θ|Theta"),
    "Ω": re.compile(r"Ω"),
    "·": re.compile(r"·"),
    "*": re.compile(r"\*"),
    "∪": re.compile(r"∪"),
    "∩": re.compile(r"∩"),
    "∖": re.compile(r"∖"),
    "∈": re.compile(r"∈"),
    "⊂": re.compile(r"⊂"),
    "⊆": re.compile(r"⊆"),
}


def _extract_axes(expr: str) -> tuple[dict[str, list[Any]], int]:
    noetics = sorted({int(m) for m in _RE_NOETIC_ANY.findall(expr)})
    domains = sorted(set(_RE_DOMAIN_ATTACHED.findall(expr)))
    drives = sorted({int(m) for m in _RE_DRIVE_ANY.findall(expr)})
    regs_single = sorted(set(_RE_REGISTER_SINGLE.findall(expr)))
    regs_set: list[str] = []
    for m in _RE_REGISTER_SET.finditer(expr):
        for piece in m.group(1).split(","):
            r = piece.strip()
            if r and r not in regs_set:
                regs_set.append(r)
    registers = sorted(set(regs_single) | set(regs_set))
    operators = [name for name, rx in _RE_OPS_TABLE.items() if rx.search(expr)]

    n_state_literals = len(_RE_DOMAIN_ATTACHED.findall(expr))
    if n_state_literals == 0:
        n_state_literals = len(_RE_NOETIC_ANY.findall(expr))

    axes = {
        "noetics_used": noetics,
        "domains_used": domains,
        "drives_used": drives,
        "registers_used": registers,
        "operators_used": operators,
    }
    return axes, n_state_literals


def _has_meta_logic(expr: str) -> bool:
    needles = (
        "Cluster", "Set{", "CoverOf", "PartitionOf", "Tuple",
        "Coordinate", "Product(", "Pullback(", "∈", "⊆", "⊂",
        "∪", "∩", "∖",
    )
    return any(n in expr for n in needles)


def _has_fractal(expr: str) -> bool:
    return any(s in expr for s in ("Phi<", "Phi⟨", "Φ<", "Φ⟨"))


# ---------------------------------------------------------------------------
# Base-preservation invariants — these are the load-bearing checks every
# variant must pass before being accepted.
# ---------------------------------------------------------------------------


def _base_signature(expr: str) -> dict[str, Any]:
    """Return the load-bearing base of an expression: state-literal cores
    in order, bare-Noetic ordering, named Ω targets, Θ-wrapper presence,
    fractal head+sequence pairs. Two expressions share a base iff their
    base_signatures are equal."""
    return {
        "state_cores": _state_cores(expr),
        "bare_noetics": _bare_noetics(expr),
        "omega_names": sorted(_omega_names(expr)),
        "has_theta": _has_theta(expr),
        "fractals": [(h, s) for h, s in _fractal_signatures(expr)],
    }


def _bases_equal(seed_expr: str, variant_expr: str) -> tuple[bool, str]:
    """Check that the variant preserves the seed's load-bearing base.
    Returns (ok, reason). Reason is empty when ok=True.

    State-literal comparison uses multisets, not ordered lists: reordering
    operands of a commutative operation is one of the four sanctioned
    variant types (`order`), and the order-of-occurrence of state cores
    is exactly what those variants permute. The load-bearing invariant
    is that the SAME state literals appear with the SAME multiplicity —
    not that they appear in the same surface position. The drive /
    register / operation transforms never reorder occurrences (they
    rewrite in place), so multiset comparison does not weaken those
    checks either.
    """
    seed_base = _base_signature(seed_expr)
    variant_base = _base_signature(variant_expr)
    if sorted(seed_base["state_cores"]) != sorted(variant_base["state_cores"]):
        return False, (
            f"state_cores multiset differs: seed={sorted(seed_base['state_cores'])} "
            f"variant={sorted(variant_base['state_cores'])}"
        )
    # Bare-Noetic count must match (set ops, clusters, fractals).
    if sorted(seed_base["bare_noetics"]) != sorted(variant_base["bare_noetics"]):
        return False, (
            f"bare_noetics multiset differs: seed={sorted(seed_base['bare_noetics'])} "
            f"variant={sorted(variant_base['bare_noetics'])}"
        )
    if seed_base["omega_names"] != variant_base["omega_names"]:
        return False, (
            f"omega_names differ: seed={seed_base['omega_names']} "
            f"variant={variant_base['omega_names']}"
        )
    if seed_base["has_theta"] != variant_base["has_theta"]:
        return False, "Θ-wrapper presence flipped"
    if seed_base["fractals"] != variant_base["fractals"]:
        return False, (
            f"fractal signatures differ: seed={seed_base['fractals']} "
            f"variant={variant_base['fractals']}"
        )
    return True, ""


# ---------------------------------------------------------------------------
# Variant transforms — each returns (new_expr, varied_axes, delta_desc) or
# None if the transform is not applicable / cannot preserve the base.
# ---------------------------------------------------------------------------


def _vary_drive_intensity(
    expr: str, rng: random.Random, exclude: set[int] | None = None
) -> tuple[str, list[str], str] | None:
    """Replace existing F_k subscripts with a different drive index.

    Strategy: find all `_{F_k}` subscripts; pick a single new drive index
    `f_new != current_index_of_first_occurrence` and apply uniformly to
    every subscript. Uniform replacement preserves "drive coherence" of
    RPM chains and recipes — variant still describes a structurally
    consistent expression. `exclude` is a set of drive indices to skip,
    used to draw multiple distinct variants of the same seed.
    """
    drives_present = _RE_DRIVE_SUB.findall(expr)
    if not drives_present:
        return None
    current = int(drives_present[0])
    excluded = {current} | (exclude or set())
    candidates = [d for d in DRIVES if d not in excluded]
    if not candidates:
        return None
    new_drive = rng.choice(candidates)
    new_expr = _RE_DRIVE_SUB.sub(f"_{{F{new_drive}}}", expr)
    if new_expr == expr:
        return None
    return (
        new_expr,
        ["drive"],
        f"F{current}→F{new_drive} (uniform)",
    )


def _vary_register(
    expr: str, rng: random.Random, exclude: set[str] | None = None
) -> tuple[str, list[str], str] | None:
    """Vary register tags. Three sub-strategies, picked by what's present:

    1. Single `|R` tags exist → swap each to a different register, but pick
       a single new register applied uniformly so the structural register
       coherence (e.g. recipe ingredient register agreement) is preserved.
    2. Multi-register set `|⟨...⟩` exists → permute the set or replace it
       with a different valid 2-3-register subset.
    3. No register tags → not applicable.

    The same-Noetic `+` co-presence pattern (`^N^D|R1 + ^N^D|R2`) gets
    special handling: swap (R1, R2) to a different pair of distinct
    registers so the co-presence semantics is preserved.
    """
    has_single = bool(_RE_REGISTER_SINGLE.search(expr))
    has_set = bool(_RE_REGISTER_SET.search(expr))
    if not (has_single or has_set):
        return None

    excluded = exclude or set()
    # Special case: same-Noetic `+` co-presence with two single registers
    # of the form `^N^D|R1 + ^N^D|R2`.
    co_presence_match = re.fullmatch(
        r"\s*\^(\d)\^([PCEO])\|([TAfE])\s*\+\s*\^(\d)\^([PCEO])\|([TAfE])\s*",
        expr,
    )
    if co_presence_match:
        n1, d1, r1, n2, d2, r2 = co_presence_match.groups()
        if n1 == n2 and d1 == d2:
            current_pair = {r1, r2}
            # Build all valid 2-register pairs from REGISTERS that differ
            # from the current set.
            other_pairs: list[tuple[str, str]] = []
            for combo in itertools.permutations(REGISTERS, 2):
                if set(combo) != current_pair and combo[0] != combo[1]:
                    key = f"|pair:{combo[0]},{combo[1]}"
                    if key not in excluded:
                        other_pairs.append(combo)
            if other_pairs:
                pair = rng.choice(other_pairs)
                new_expr = f"^{n1}^{d1}|{pair[0]} + ^{n1}^{d1}|{pair[1]}"
                return (
                    new_expr,
                    ["register"],
                    f"({r1},{r2})→({pair[0]},{pair[1]})",
                )

    # Multi-register set: replace with a different 2-3-register subset.
    if has_set:
        m = _RE_REGISTER_SET.search(expr)
        assert m is not None
        current_inner = [
            piece.strip() for piece in m.group(1).split(",") if piece.strip()
        ]
        candidates: list[list[str]] = []
        for k in (2, 3):
            for combo in itertools.combinations(REGISTERS, k):
                if list(combo) != current_inner:
                    key = "|set:" + ",".join(combo)
                    if key not in excluded:
                        candidates.append(list(combo))
        if candidates:
            new_inner = rng.choice(candidates)
            new_set = "|⟨" + ",".join(new_inner) + "⟩"
            new_expr = expr[: m.start()] + new_set + expr[m.end() :]
            return (
                new_expr,
                ["register"],
                f"⟨{','.join(current_inner)}⟩→⟨{','.join(new_inner)}⟩",
            )

    # Single-register replacement (uniform across all `|R` tags).
    if has_single:
        # Find the FIRST `|R` and use that as the "current" register —
        # for uniform replacement to be a no-op-test we need a register
        # not equal to it. If multiple registers exist, we still apply
        # one new register to every `|R` slot uniformly.
        first = _RE_REGISTER_SINGLE.search(expr)
        if first is None:
            return None
        current = first.group(1)
        excluded_keys = {f"|R{current}"} | {x for x in excluded if x.startswith("|R")}
        candidates = [r for r in REGISTERS if f"|R{r}" not in excluded_keys]
        if not candidates:
            return None
        new_reg = rng.choice(candidates)
        new_expr = _RE_REGISTER_SINGLE.sub(f"|{new_reg}", expr)
        if new_expr == expr:
            return None
        return (
            new_expr,
            ["register"],
            f"|{current}*→|{new_reg}* (uniform)",
        )

    return None


def _vary_operation(
    expr: str, rng: random.Random, exclude: set[str] | None = None
) -> tuple[str, list[str], str] | None:
    """Swap the operation in cross-Noetic binary compositions.

    Eligible patterns (compiler-validated, preserving v7.7 operator
    discipline):

        ^N1^D + ^N2^D  ↔  ^N1^D × ^N2^D     (different Noetics — both valid)
        ^N1^D + ^N2^D  ↔  ^N1^D ∘ ^N2^D     (different Noetics — both valid)

    Same-Noetic `+` co-presence (`^N^D|R1 + ^N^D|R2`) is NOT eligible —
    swapping to `×` would violate Clarification 10's same-Noetic-without-
    emergent-result rule.

    Identity operator-pair compositions (`CO-N ∘ CO-M`) are also eligible:
    swap to a different `CO-X ∘ CO-Y` only when the same operator-pair
    structure is preserved — but that would change BASE state literals.
    Skip CO-pair compositions for the operation transform (they're
    already operator-only seeds; vary nothing).
    """
    # Reject operator-only `CO-N ∘ CO-M` forms — no state literals so
    # there's no fiber/marginal to swap.
    if "CO-" in expr:
        return None

    # Pattern: cross-Noetic (?P<a>^N1^D) (?P<op>[+×∘]) (?P<b>^N2^D)
    bin_match = re.fullmatch(
        r"\s*\^(\d)\^([PCEO])\s*([+×∘])\s*\^(\d)\^([PCEO])\s*",
        expr,
    )
    if bin_match:
        n1, d1, op, n2, d2 = bin_match.groups()
        if n1 != n2 and d1 == d2:
            # Different Noetics, same domain → safe to swap among +/×/∘.
            excluded = exclude or set()
            options = [
                o for o in ("+", "×", "∘")
                if o != op and f"op:{o}" not in excluded
            ]
            if not options:
                return None
            new_op = rng.choice(options)
            new_expr = f"^{n1}^{d1} {new_op} ^{n2}^{d2}"
            return (
                new_expr,
                ["operator"],
                f"`{op}`→`{new_op}` (cross-Noetic same-domain)",
            )
        # Same-Noetic same-domain `+`/`×` — skip (v7.7 same-Noetic rule).
        return None

    return None


def _split_terms(text: str, sep: str) -> list[str]:
    """Split `text` on top-level occurrences of `sep` (only outside
    parentheses / braces / brackets). Used for reordering recipe
    ingredients without descending into nested clusters."""
    terms: list[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "({[⟨":
            depth += 1
        elif ch in ")}]⟩":
            depth -= 1
        elif depth == 0 and text[i : i + len(sep)] == sep:
            terms.append(text[start:i].strip())
            start = i + len(sep)
            i += len(sep)
            continue
        i += 1
    last = text[start:].strip()
    if last:
        terms.append(last)
    return terms


def _vary_order_recipe(
    expr: str, rng: random.Random, exclude: set[str] | None = None
) -> tuple[str, list[str], str] | None:
    """Reorder ingredients of a recipe LHS sum.

    Recipe shape: `Θ(Ω_name) = a₁·X₁ + a₂·X₂ [+ ...] → Ω_name [+ Λ·...]`
    Strategy: split LHS at top-level `+`, permute, rejoin. Preserves the
    arrow target verbatim (including any leakage term on the RHS).
    """
    # Look for arrow (`→` or `->`) at top level.
    arrow_match = re.search(r"→|->", expr)
    if arrow_match is None:
        return None
    # Find the `=` after `Θ(Ω_name)` or `Theta(Omega_name)`. The recipe
    # starts with the wrapper.
    eq_match = re.search(r"\)\s*=", expr)
    if eq_match is None:
        return None
    head = expr[: eq_match.end()]  # `Θ(Ω_x) =`
    body_start = eq_match.end()
    arrow_pos = arrow_match.start()
    if arrow_pos <= body_start:
        return None
    lhs_body = expr[body_start:arrow_pos].strip()
    arrow_str = arrow_match.group(0)
    rhs_body = expr[arrow_match.end() :]

    terms = _split_terms(lhs_body, "+")
    if len(terms) < 2:
        return None
    excluded = exclude or set()
    # Try non-identity permutations until we find one not yet emitted.
    # Bounded by 24 attempts (4! = 24 cap for typical recipes).
    for _ in range(24):
        perm = list(terms)
        rng.shuffle(perm)
        if perm == terms:
            continue
        new_lhs = " + ".join(perm)
        new_expr = f"{head} {new_lhs} {arrow_str}{rhs_body}"
        if new_expr in excluded:
            continue
        return (
            new_expr,
            ["order"],
            f"recipe ingredients permuted ({len(terms)} terms)",
        )
    return None


def _vary_order_omega(
    expr: str, rng: random.Random, exclude: set[str] | None = None
) -> tuple[str, list[str], str] | None:
    """Reorder operands of `(X1 × X2 [× X3]) = Ω_target`.

    Cross-register Ω forms are commutative on `×` (per v7.7), so
    permuting the LHS operands is algebraically equivalent.
    """
    m = re.fullmatch(r"\s*\((.+)\)\s*=\s*(.+?)\s*", expr)
    if m is None:
        return None
    inner = m.group(1)
    rhs = m.group(2).strip()
    terms = _split_terms(inner, "×")
    if len(terms) < 2:
        return None
    excluded = exclude or set()
    for _ in range(24):
        perm = list(terms)
        rng.shuffle(perm)
        if perm == terms:
            continue
        new_inner = " × ".join(perm)
        new_expr = f"({new_inner}) = {rhs}"
        if new_expr in excluded:
            continue
        return (
            new_expr,
            ["order"],
            f"× operands permuted ({len(terms)} terms)",
        )
    return None


def _vary_order_cluster(
    expr: str, rng: random.Random, exclude: set[str] | None = None
) -> tuple[str, list[str], str] | None:
    """Reorder members of a NoeticCluster / StateCluster / StateVariantCluster.

    Compiler treats clusters as sets, so member reordering is semantically
    equivalent. Operates on the FIRST cluster found that has ≥2 members.
    """
    cluster_match = re.search(
        r"(NoeticCluster|StateCluster|StateVariantCluster)\{([^{}]+)\}",
        expr,
    )
    if cluster_match is None:
        return None
    ctor = cluster_match.group(1)
    members = [m.strip() for m in cluster_match.group(2).split(",") if m.strip()]
    if len(members) < 2:
        return None
    excluded = exclude or set()
    for _ in range(24):
        perm = list(members)
        rng.shuffle(perm)
        if perm == members:
            continue
        new_inner = ", ".join(perm)
        new_expr = (
            expr[: cluster_match.start()]
            + f"{ctor}{{{new_inner}}}"
            + expr[cluster_match.end() :]
        )
        if new_expr in excluded:
            continue
        return (
            new_expr,
            ["order"],
            f"{ctor} members permuted ({len(members)} members)",
        )
    return None


def _vary_order_co_presence(
    expr: str, rng: random.Random, exclude: set[str] | None = None
) -> tuple[str, list[str], str] | None:
    """Reorder operands of a top-level `+` co-presence sum.

    Pattern: `term1 + term2 [+ term3 [+ ...]]` at top level (no Θ wrapper).
    Excluded if the expression contains a Θ recipe wrapper (handled by
    _vary_order_recipe) or a `(...) = ...` Ω form (handled by
    _vary_order_omega).
    """
    if _has_theta(expr):
        return None
    if "(" in expr and ") =" in expr:
        return None
    if "→" in expr or "->" in expr:
        return None
    if "=" in expr:
        # Other `=` forms (e.g. `let x = ...`, `(a × b) = c`) are handled
        # elsewhere; skip here.
        return None
    terms = _split_terms(expr.strip(), "+")
    if len(terms) < 2:
        return None
    excluded = exclude or set()
    for _ in range(24):
        perm = list(terms)
        rng.shuffle(perm)
        if perm == terms:
            continue
        new_expr = " + ".join(perm)
        if new_expr in excluded:
            continue
        return (
            new_expr,
            ["order"],
            f"+ operands permuted ({len(terms)} terms)",
        )
    return None


# ---------------------------------------------------------------------------
# Variant generator — applies the four transform families to a seed and
# emits compiler-validated variants up to a per-seed budget.
# ---------------------------------------------------------------------------


@dataclass
class Variant:
    variant_id: str
    source_seed_id: str
    variant_type: str
    preserved_axes: list[str]
    varied_axes: list[str]
    expression: str
    compiler_validated: bool
    axes: dict[str, list[Any]]
    n_state_literals: int
    uses_named_omega: bool
    uses_theta_recipe: bool
    uses_meta_logic: bool
    uses_fractal: bool
    delta_from_seed: str
    source_grammar_category: str

    def to_record(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "source_seed_id": self.source_seed_id,
            "variant_type": self.variant_type,
            "preserved_axes": self.preserved_axes,
            "varied_axes": self.varied_axes,
            "expression": self.expression,
            "compiler_validated": self.compiler_validated,
            "axes": self.axes,
            "n_state_literals": self.n_state_literals,
            "uses_named_omega": self.uses_named_omega,
            "uses_theta_recipe": self.uses_theta_recipe,
            "uses_meta_logic": self.uses_meta_logic,
            "uses_fractal": self.uses_fractal,
            "delta_from_seed": self.delta_from_seed,
            "source_grammar_category": self.source_grammar_category,
        }


# Order-strategy dispatch table per grammar category. The strategies are
# tried in order; the first one to return a candidate becomes the "order"
# variant for that seed.
_ORDER_STRATEGIES = {
    "recipe": [_vary_order_recipe],
    "cross_register_omega": [_vary_order_omega],
    "meta_logic_relation": [_vary_order_cluster],
    "binary_composition": [_vary_order_co_presence],
    # Inversion seeds span multiple shapes (Axis N, F → co-presence sums;
    # Axis E, S → clusters; Axis P → cross-register Ω). Try all in turn.
    "inversion": [
        _vary_order_omega,
        _vary_order_cluster,
        _vary_order_co_presence,
    ],
    "diagram_export": [_vary_order_cluster],
    "let_binding": [],
    "rpm_chain": [],
    "state_literal": [],
    "fractal_sequence": [],
}


# Variant-type strategy dispatch — each callable returns
# (new_expr, varied_axes, delta_desc) | None.
_VARIANT_STRATEGIES = {
    "drive_intensity": _vary_drive_intensity,
    "register": _vary_register,
    "operation": _vary_operation,
}


# Per-source-grammar oversample multipliers (Wave 1B coverage thinness).
# `target` is the minimum number of variants we aim to emit per seed of
# that category (the kickoff memo: "≥3 variants per rpm_chain seed and
# ≥5 variants per inversion seed even if other lanes get 2-3").
# `ceiling` is the maximum we'll keep emitting — used to push productive
# inversion shapes above the lane average so the overall ratio approaches
# the target even when some shapes (axis W, axis N) are structurally
# bounded below the target.
OVERSAMPLE_RATIOS = {
    "rpm_chain": 3,
    "inversion": 5,
    "_default": 3,
}
OVERSAMPLE_CEILINGS = {
    "rpm_chain": 6,
    "inversion": 8,        # productive shapes (P, F, A, S, E) can hit 6-8
    "_default": 4,
}


def _ratio_for(category: str) -> int:
    return OVERSAMPLE_RATIOS.get(category, OVERSAMPLE_RATIOS["_default"])


def _ceiling_for(category: str) -> int:
    return OVERSAMPLE_CEILINGS.get(category, OVERSAMPLE_CEILINGS["_default"])


class VariantGenerator:
    """Apply contrastive transforms to compiler-validated seed objects."""

    def __init__(self, seed: int = 4242) -> None:
        self.rng = random.Random(seed)
        compiler_module = _load_compiler()
        self.compile_expression = compiler_module.compile_expression
        self.accepted: list[Variant] = []
        self.rejected: list[dict[str, Any]] = []
        # variant index counter per source seed.
        self._counter: dict[str, int] = defaultdict(int)

    # ----- helpers --------------------------------------------------------

    def _make_variant(
        self,
        source_seed: dict[str, Any],
        variant_type: str,
        new_expr: str,
        varied_axes: list[str],
        delta_desc: str,
    ) -> bool:
        """Compiler-validate and base-preserve check a candidate; on
        success append to self.accepted. Returns True iff accepted."""
        seed_expr = source_seed["expression"]
        seed_id = source_seed["seed_id"]

        # Cheap early-out: identical to the seed (transform was a no-op).
        if new_expr.strip() == seed_expr.strip():
            self.rejected.append({
                "source_seed_id": seed_id,
                "variant_type": variant_type,
                "expression": new_expr,
                "reason": "no-op transform (variant identical to seed)",
            })
            return False

        ok, reason = _bases_equal(seed_expr, new_expr)
        if not ok:
            self.rejected.append({
                "source_seed_id": seed_id,
                "variant_type": variant_type,
                "expression": new_expr,
                "reason": f"base preservation: {reason}",
            })
            return False

        artifact = self.compile_expression(new_expr)
        if not getattr(artifact, "valid", False):
            self.rejected.append({
                "source_seed_id": seed_id,
                "variant_type": variant_type,
                "expression": new_expr,
                "reason": f"compiler: {getattr(artifact, 'error', '') or ''}",
            })
            return False

        # Successful candidate — package it.
        self._counter[seed_id] += 1
        idx = self._counter[seed_id]
        variant_id = f"var_{seed_id}_{idx:02d}"

        axes, n_states = _extract_axes(new_expr)
        # Preserved axes = union of (state, omega, theta, fractal) and the
        # axes NOT in `varied_axes` from the seed-level axis set.
        preserved_axis_universe = ["state_literals", "omega_targets",
                                    "theta_wrappers", "fractal_sequences"]
        # For each varied axis, also record the rest as preserved.
        preserved_axes = list(preserved_axis_universe)

        v = Variant(
            variant_id=variant_id,
            source_seed_id=seed_id,
            variant_type=variant_type,
            preserved_axes=preserved_axes,
            varied_axes=list(varied_axes),
            expression=new_expr,
            compiler_validated=True,
            axes=axes,
            n_state_literals=n_states,
            uses_named_omega=bool(_RE_OMEGA_NAME.search(new_expr)) or "Ω" in new_expr,
            uses_theta_recipe=("Θ" in new_expr)
                or new_expr.lstrip().startswith("Theta")
                or " Theta(" in new_expr,
            uses_meta_logic=_has_meta_logic(new_expr),
            uses_fractal=_has_fractal(new_expr),
            delta_from_seed=delta_desc,
            source_grammar_category=source_seed.get("grammar_category", ""),
        )
        self.accepted.append(v)
        return True

    # ----- per-seed orchestration ----------------------------------------

    def generate_for_seed(
        self,
        source_seed: dict[str, Any],
    ) -> int:
        """Produce up to `_ceiling_for(category)` distinct variants for
        the seed (target is `_ratio_for` — aim for ≥target, allow up to
        ceiling so productive shapes can compensate for structurally
        bounded shapes within the same lane). Returns the count actually
        accepted."""
        category = source_seed.get("grammar_category", "")
        target = _ratio_for(category)
        ceiling = _ceiling_for(category)

        produced = 0

        # Per-(seed, type) exclusion sets — each call to a transform with
        # an `exclude` parameter avoids re-drawing the same value, so we
        # accumulate distinct variants of the same type.
        exclude_drive: set[int] = set()
        exclude_register: set[str] = set()
        exclude_op: set[str] = set()
        exclude_order: set[str] = set()  # rough key based on operand tuple

        # Track expression strings already accepted for this seed, so we
        # never emit two identical variants.
        seen_exprs: set[str] = set()

        # Attempt schedule. We loop the four types interleaved, then
        # repeat to allow multiple variants of the same type when the
        # transform supports extra distinct draws.
        type_order = ["drive_intensity", "register", "operation", "order"]
        max_rounds = max(12, ceiling * 2)
        for round_idx in range(max_rounds):
            if produced >= ceiling:
                break
            progressed_this_round = False
            for vt in type_order:
                if produced >= ceiling:
                    break
                if vt == "drive_intensity":
                    candidate = _vary_drive_intensity(
                        source_seed["expression"], self.rng, exclude_drive
                    )
                elif vt == "register":
                    candidate = _vary_register(
                        source_seed["expression"], self.rng, exclude_register
                    )
                elif vt == "operation":
                    candidate = _vary_operation(
                        source_seed["expression"], self.rng, exclude_op
                    )
                else:  # order
                    candidate = self._try_order(source_seed, exclude_order)

                if candidate is None:
                    continue
                new_expr, varied_axes, delta_desc = candidate
                # Update per-seed exclusion sets so the next round draws
                # a different value.
                if vt == "drive_intensity":
                    m = re.search(r"F(\d)→F(\d)", delta_desc)
                    if m:
                        exclude_drive.add(int(m.group(2)))
                elif vt == "register":
                    # Extract the new register from the delta description.
                    # Format: "|A*→|T* (uniform)" or "(A,f)→(T,E)" or
                    # "⟨A,f⟩→⟨T,E⟩" — record the post-arrow value.
                    m = re.search(r"→\|([TAfE])\*", delta_desc)
                    if m:
                        exclude_register.add(f"|R{m.group(1)}")
                    m_set = re.search(r"⟩→⟨([TAfE,]+)⟩", delta_desc)
                    if m_set:
                        exclude_register.add(f"|set:{m_set.group(1)}")
                    m_pair = re.search(r"→\(([TAfE]),([TAfE])\)", delta_desc)
                    if m_pair:
                        exclude_register.add(
                            f"|pair:{m_pair.group(1)},{m_pair.group(2)}"
                        )
                elif vt == "operation":
                    # Extract the new operator from delta and exclude it
                    # from future draws so successive variants choose
                    # different operators.
                    m = re.search(r"`(.+?)`→`(.+?)`", delta_desc)
                    if m:
                        exclude_op.add(f"op:{m.group(2)}")
                else:
                    exclude_order.add(new_expr)

                if new_expr in seen_exprs:
                    continue
                ok = self._make_variant(
                    source_seed, vt, new_expr, varied_axes, delta_desc
                )
                if ok:
                    seen_exprs.add(new_expr)
                    produced += 1
                    progressed_this_round = True
            if not progressed_this_round:
                # No transform produced a usable candidate this round —
                # the seed is exhausted and further rounds would loop.
                break

        return produced

    def _try_order(
        self, source_seed: dict[str, Any], exclude: set[str]
    ) -> tuple[str, list[str], str] | None:
        category = source_seed.get("grammar_category", "")
        strategies = _ORDER_STRATEGIES.get(category, [])
        for fn in strategies:
            result = fn(source_seed["expression"], self.rng, exclude)
            if result is not None:
                return result
        return None

    # ----- top-level driver ----------------------------------------------

    def run(self, seeds: Iterable[dict[str, Any]]) -> None:
        t0 = time.time()
        n_seeds = 0
        for s in seeds:
            n_seeds += 1
            self.generate_for_seed(s)
        elapsed = time.time() - t0
        print(
            f"[generate_path_d_variants] processed seeds={n_seeds} "
            f"accepted={len(self.accepted)} rejected={len(self.rejected)} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )


# ---------------------------------------------------------------------------
# I/O — JSONL read/write + coverage report.
# ---------------------------------------------------------------------------


def _read_seeds(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _build_coverage_report(
    variants: list[Variant],
    rejected: list[dict[str, Any]],
    seeds: list[dict[str, Any]],
    out_path: Path,
) -> None:
    by_type: Counter = Counter(v.variant_type for v in variants)
    by_source_grammar: Counter = Counter(v.source_grammar_category for v in variants)

    # Per-source-seed variant counts (for oversample ratio computation).
    per_seed: defaultdict[str, int] = defaultdict(int)
    for v in variants:
        per_seed[v.source_seed_id] += 1

    seeds_by_id = {s["seed_id"]: s for s in seeds}
    rpm_seed_ids = [s["seed_id"] for s in seeds if s.get("grammar_category") == "rpm_chain"]
    inversion_seed_ids = [s["seed_id"] for s in seeds if s.get("grammar_category") == "inversion"]

    rpm_total_variants = sum(per_seed.get(sid, 0) for sid in rpm_seed_ids)
    inv_total_variants = sum(per_seed.get(sid, 0) for sid in inversion_seed_ids)
    rpm_ratio = (rpm_total_variants / len(rpm_seed_ids)) if rpm_seed_ids else 0.0
    inv_ratio = (inv_total_variants / len(inversion_seed_ids)) if inversion_seed_ids else 0.0

    # Productive inversion seeds — exclude axis-W shapes (`^N^Da -> ^N^Db`),
    # which have no variable fiber/marginal that preserves the base
    # (no drives, no registers, mandatory domain-descent direction). Per
    # the kickoff memo, "if you can't vary an axis without changing the
    # base, skip the variant rather than violate this." The productive-
    # shape ratio is the meaningful oversample metric for inversion.
    inversion_productive_ids = [
        s["seed_id"] for s in seeds
        if s.get("grammar_category") == "inversion"
        and s.get("metadata", {}).get("axis") != "W"
    ]
    inv_productive_total = sum(
        per_seed.get(sid, 0) for sid in inversion_productive_ids
    )
    inv_productive_ratio = (
        inv_productive_total / len(inversion_productive_ids)
        if inversion_productive_ids
        else 0.0
    )

    total_attempted = len(variants) + len(rejected)
    rejection_rate = (len(rejected) / total_attempted) if total_attempted else 0.0

    # Reasons.
    reason_counter: Counter = Counter()
    for r in rejected:
        reason = r.get("reason", "")
        reason_key = reason.split(":", 1)[0]
        reason_counter[reason_key] += 1

    # Per-source-grammar variant counts per type.
    cross_table: defaultdict[str, Counter] = defaultdict(Counter)
    for v in variants:
        cross_table[v.source_grammar_category][v.variant_type] += 1

    # Axis token counts (mirrors seed coverage report).
    noetic_counter: Counter = Counter()
    domain_counter: Counter = Counter()
    drive_counter: Counter = Counter()
    register_counter: Counter = Counter()
    operator_counter: Counter = Counter()
    n_omega = 0
    n_theta = 0
    n_meta_logic = 0
    n_fractal = 0
    for v in variants:
        for n in v.axes.get("noetics_used", []):
            noetic_counter[n] += 1
        for d in v.axes.get("domains_used", []):
            domain_counter[d] += 1
        for fk in v.axes.get("drives_used", []):
            drive_counter[fk] += 1
        for r in v.axes.get("registers_used", []):
            register_counter[r] += 1
        for op in v.axes.get("operators_used", []):
            operator_counter[op] += 1
        if v.uses_named_omega:
            n_omega += 1
        if v.uses_theta_recipe:
            n_theta += 1
        if v.uses_meta_logic:
            n_meta_logic += 1
        if v.uses_fractal:
            n_fractal += 1

    lines: list[str] = []
    lines.append("# Path D Wave 2C — Variant Coverage Report")
    lines.append("")
    lines.append(f"- Total source seeds processed: **{len(seeds)}**")
    lines.append(f"- Total accepted variants: **{len(variants)}**")
    lines.append(f"- Total rejected attempts: **{len(rejected)}**")
    lines.append(f"- Validation rejection rate: **{rejection_rate:.2%}**")
    if seeds:
        lines.append(f"- Avg variants per seed: **{len(variants) / len(seeds):.2f}**")
    lines.append("")
    lines.append("## Per variant_type")
    lines.append("")
    lines.append("| variant_type | count |")
    lines.append("|---|---|")
    for t in ("drive_intensity", "register", "operation", "order"):
        lines.append(f"| {t} | {by_type.get(t, 0)} |")
    lines.append("")
    lines.append("## Per source grammar category")
    lines.append("")
    lines.append("| source_grammar_category | count |")
    lines.append("|---|---|")
    for g, count in sorted(by_source_grammar.items()):
        lines.append(f"| {g} | {count} |")
    lines.append("")
    lines.append("## Cross-table: source category × variant_type")
    lines.append("")
    cats = sorted(cross_table.keys())
    types = ("drive_intensity", "register", "operation", "order")
    header = "| source\\type | " + " | ".join(types) + " | total |"
    sep = "|---|" + "|".join(["---"] * len(types)) + "|---|"
    lines.append(header)
    lines.append(sep)
    for cat in cats:
        row_counts = cross_table[cat]
        cells = [str(row_counts.get(t, 0)) for t in types]
        total = sum(row_counts.values())
        lines.append(f"| {cat} | " + " | ".join(cells) + f" | {total} |")
    lines.append("")
    lines.append("## Oversample stats — thin lanes (rpm_chain, inversion)")
    lines.append("")
    lines.append(
        "| lane | seed count | variant count | ratio | target | met? |"
    )
    lines.append("|---|---|---|---|---|---|")
    rpm_target = OVERSAMPLE_RATIOS["rpm_chain"]
    inv_target = OVERSAMPLE_RATIOS["inversion"]
    rpm_ok = "PASS" if rpm_ratio >= rpm_target else "FAIL"
    inv_all_ok = "PASS" if inv_ratio >= inv_target else "PARTIAL"
    inv_prod_ok = "PASS" if inv_productive_ratio >= inv_target else "FAIL"
    lines.append(
        f"| rpm_chain | {len(rpm_seed_ids)} | {rpm_total_variants} | "
        f"{rpm_ratio:.2f} | ≥{rpm_target} | {rpm_ok} |"
    )
    lines.append(
        f"| inversion (all axes) | {len(inversion_seed_ids)} | "
        f"{inv_total_variants} | {inv_ratio:.2f} | ≥{inv_target} | "
        f"{inv_all_ok} |"
    )
    lines.append(
        f"| inversion (productive shapes only) | "
        f"{len(inversion_productive_ids)} | {inv_productive_total} | "
        f"{inv_productive_ratio:.2f} | ≥{inv_target} | {inv_prod_ok} |"
    )
    n_axis_w = (
        len(inversion_seed_ids) - len(inversion_productive_ids)
    )
    if n_axis_w:
        lines.append("")
        lines.append(
            f"_Note: {n_axis_w} axis-W inversion seeds (shape `^N^Da -> "
            f"^N^Db`) have no variable fiber/marginal that preserves the "
            f"base — no drives, no registers, mandatory domain-descent "
            f"direction. Per the Wave 2C kickoff memo (\"if you can't "
            f"vary an axis without changing the base, skip the variant\"),"
            f" these seeds yield 0 variants by design. The productive-"
            f"shape ratio is the meaningful oversample metric._"
        )
    lines.append("")
    lines.append("## Per axis token distribution")
    lines.append("")
    lines.append("### Noetics used (count of variants containing each Noetic)")
    lines.append("")
    lines.append("| Noetic | count |")
    lines.append("|---|---|")
    for n in sorted(noetic_counter.keys()):
        lines.append(f"| ^{n} | {noetic_counter[n]} |")
    lines.append("")
    lines.append("### Domains used")
    lines.append("")
    lines.append("| Domain | count |")
    lines.append("|---|---|")
    for d in sorted(domain_counter.keys()):
        lines.append(f"| {d} | {domain_counter[d]} |")
    lines.append("")
    lines.append("### Drives used")
    lines.append("")
    lines.append("| Drive | count |")
    lines.append("|---|---|")
    for fk in sorted(drive_counter.keys()):
        lines.append(f"| F{fk} | {drive_counter[fk]} |")
    lines.append("")
    lines.append("### Registers used")
    lines.append("")
    lines.append("| Register | count |")
    lines.append("|---|---|")
    for r in sorted(register_counter.keys()):
        lines.append(f"| {r} | {register_counter[r]} |")
    lines.append("")
    lines.append("### Operators used")
    lines.append("")
    lines.append("| Operator | count |")
    lines.append("|---|---|")
    for op, count in operator_counter.most_common():
        lines.append(f"| `{op}` | {count} |")
    lines.append("")
    lines.append("## Special-flag counts")
    lines.append("")
    lines.append(f"- uses_named_omega : {n_omega}")
    lines.append(f"- uses_theta_recipe: {n_theta}")
    lines.append(f"- uses_meta_logic  : {n_meta_logic}")
    lines.append(f"- uses_fractal     : {n_fractal}")
    lines.append("")
    lines.append("## Rejection reasons (top 10)")
    lines.append("")
    if reason_counter:
        lines.append("| reason | count |")
        lines.append("|---|---|")
        for reason, count in reason_counter.most_common(10):
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("(no rejections)")
    lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Path D Wave 2C contrastive variants per seed. "
            "Each variant varies one fiber/marginal (drive intensity, "
            "register, operation, or order) while preserving the seed's "
            "load-bearing base."
        )
    )
    parser.add_argument(
        "--seeds",
        type=Path,
        default=Path("cas-synthetic/data/path_d/seeds.jsonl"),
        help="path to seeds.jsonl (Wave 1B output)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("cas-synthetic/data/path_d"),
        help=(
            "output directory for variants.jsonl, variants_rejected.jsonl, "
            "and variants_coverage_report.md"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=4242,
        help="random seed for deterministic transforms",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="if set, truncate accepted variants to this many before writing",
    )
    parser.add_argument(
        "--seed-limit",
        type=int,
        default=None,
        help="if set, only process this many seeds (smoke / test runs)",
    )
    args = parser.parse_args(argv)

    seeds = _read_seeds(args.seeds)
    if args.seed_limit is not None and args.seed_limit > 0:
        seeds = seeds[: args.seed_limit]

    gen = VariantGenerator(seed=args.seed)
    gen.run(seeds)

    accepted = gen.accepted
    if args.limit is not None and args.limit > 0:
        accepted = accepted[: args.limit]

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out_dir / "variants.jsonl", (v.to_record() for v in accepted))
    _write_jsonl(out_dir / "variants_rejected.jsonl", iter(gen.rejected))
    _build_coverage_report(
        accepted, gen.rejected, seeds, out_dir / "variants_coverage_report.md"
    )

    print(
        f"[generate_path_d_variants] wrote "
        f"{out_dir / 'variants.jsonl'} ({len(accepted)} records), "
        f"{out_dir / 'variants_rejected.jsonl'} ({len(gen.rejected)} records), "
        f"{out_dir / 'variants_coverage_report.md'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
