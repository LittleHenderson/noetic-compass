"""Path D Wave 1 — Seed CAS object enumerator.

Path D corpus pipeline §2 deliverable B: enumerate ~6K compiler-valid base
CAS objects spanning the full grammar surface (`docs/working/
path_D_corpus_pipeline_design_2026_05_07.md`). Every record round-trips
through `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`.
Failed parses / admissibility errors are written to a sibling
`seeds_rejected.jsonl` with the compiler error text annotated.

Coverage targets (Path D corpus pipeline §3 + memory feedback rule
`feedback_cas_token_enum_must_include_metalogic_and_fractals.md`):

  Per task slot (≈1K each, six slots → ~6K):
    cas_to_english          : seeds suitable for CAS→NL paraphrase
    english_to_cas          : seeds suitable as NL→CAS targets
    invalid_to_explanation  : valid bases for downstream Wave 2 mutation
    invalid_to_corrected    : valid bases for downstream Wave 2 mutation
    operation_to_outcome    : seeds whose runtime result is interesting
    expression_to_trace     : seeds whose AST/admissibility/RPM trace is rich

  Per grammar category (≥500 each — the "7 categories" of the memory rule):
    state_literal           : ^N, ^N^D, ^N^D_{Fk}, ^N^D|R, ^N^D_{Fk}|R, multi-register
    binary_composition      : two-operand `+`, `×`, `∘`, `→`, `=`
    cross_register_omega    : (^N^D|R1 × ^N^D|R2 [× ...]) = ^N^D|Ω_name
    recipe                  : Θ(Ω_name) = a₁·X₁ + ... → Ω_name [+ Λ·Ω_side]
    meta_logic_relation     : NoeticCluster / StateCluster / set ops / CoverOf
                              / PartitionOf / Tuple / Coordinate / Product
                              / membership / subset / cardinality
    fractal_sequence        : Phi⟨k₁:k₂:...:kₙ⟩
    let_binding             : let / export let bindings
    diagram_export          : `export let name = expr` (compiler-diagrammable)
    rpm_chain               : `let A0 = ...; let D2 = ...; ...; A0 -> D2`-style
                              prerequisite chains constructible inside the
                              grammar
    inversion               : structural patterns covering the 7 inversion
                              axes (involution-pair compositions, domain-
                              precedence chains, drive-pair contrasts, ...)

The script is single-shot, deterministic given a seed, and offline (no
network / API). Output:

    cas-synthetic/data/path_d/seeds.jsonl              (validated)
    cas-synthetic/data/path_d/seeds_rejected.jsonl      (rejected, for audit)
    cas-synthetic/data/path_d/seeds_coverage_report.md  (coverage stats)

Usage:
    python -m cas_synthetic.scripts.generate_path_d_seeds \
        --out cas-synthetic/data/path_d \
        --target 6000 \
        --seed 4242

A `--limit N` flag is provided for fast smoke runs (e.g. tests use
`--limit 100`). Default behavior aims for ~6K validated seeds.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Compiler loader (mirrors the meta_logic generator's pattern; the hyphenated
# `noetic-compass-scaffold` directory is not an importable package).
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
    module_name = "cas_synthetic_path_d_compiler"
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
# Vocabulary constants (mirrors compiler.py canonical names).
# ---------------------------------------------------------------------------

NOETICS = list(range(10))               # 0..9
DOMAINS = ("P", "C", "E", "O")
DRIVES = (1, 2, 3, 4, 5, 6, 7)
REGISTERS = ("T", "A", "f", "E")        # CAS v7.5 Phenomenological Register
INVOLUTION_PAIRS = ((2, 3), (5, 6), (8, 9))
SELF_DUAL_NOETICS = (0, 1, 4, 7)

# Curated emergent register names (must look like Ω_<lowercase_word>; the
# compiler accepts arbitrary identifier suffixes, so any name works). Kept
# small and content-meaningful so downstream NL annotation has anchors.
OMEGA_NAMES = (
    "presence", "refusal", "clarity", "resolve", "compassion",
    "wisdom", "judgment", "discernment", "integration", "release",
    "alignment", "coherence", "stability", "trust", "boundary",
    "honesty", "calm", "courage", "patience", "agency",
)

# Recipe ingredient name suffixes (informational — recipes use the form
# Θ(Ω_<name>) = ... → Ω_<name>; `RECIPE_NAMES` mirrors the v76 generator's
# scenario names).
RECIPE_NAMES = (
    "reasoning", "decision", "explanation", "verification", "synthesis",
    "translation", "judgment", "self_correction", "remembering", "rest",
    "engagement", "withdrawal", "production", "rehearsal", "tracking",
)


# ---------------------------------------------------------------------------
# Seed record schema
# ---------------------------------------------------------------------------


@dataclass
class Seed:
    seed_id: str
    task_slot: str
    grammar_category: str
    expression: str
    compiler_validated: bool = True
    axes: dict[str, list[Any]] = field(default_factory=dict)
    n_state_literals: int = 0
    n_operators: int = 0
    uses_named_omega: bool = False
    uses_theta_recipe: bool = False
    uses_meta_logic: bool = False
    uses_fractal: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "seed_id": self.seed_id,
            "task_slot": self.task_slot,
            "grammar_category": self.grammar_category,
            "expression": self.expression,
            "compiler_validated": self.compiler_validated,
            "axes": self.axes,
            "n_state_literals": self.n_state_literals,
            "n_operators": self.n_operators,
            "uses_named_omega": self.uses_named_omega,
            "uses_theta_recipe": self.uses_theta_recipe,
            "uses_meta_logic": self.uses_meta_logic,
            "uses_fractal": self.uses_fractal,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Axis extraction helpers — populate the `axes` field from the surface form
# without re-implementing the compiler.
# ---------------------------------------------------------------------------

import re

_RE_NOETIC = re.compile(r"\^(\d)(?!\d)")
_RE_DOMAIN = re.compile(r"\^\d\^([PCEO])")
_RE_DOMAIN_BARE = re.compile(r"(?<![A-Za-z_])([PCEO])(?=[\s,}\)\|])")
_RE_DRIVE = re.compile(r"F([1-7])")
_RE_REGISTER_SINGLE = re.compile(r"\|([TAfE])(?![a-zA-Z])")
_RE_REGISTER_SET = re.compile(r"\|⟨([TAfE,\s]+)⟩")
_RE_OMEGA_NAME = re.compile(r"Ω_(\w+)")
_RE_OPS = {
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


def _extract_axes(expr: str) -> tuple[dict[str, list[Any]], int, int]:
    noetics = sorted({int(m) for m in _RE_NOETIC.findall(expr)})
    domains = sorted(set(_RE_DOMAIN.findall(expr)))
    drives = sorted({int(m) for m in _RE_DRIVE.findall(expr)})
    regs_single = sorted(set(_RE_REGISTER_SINGLE.findall(expr)))
    regs_set: list[str] = []
    for m in _RE_REGISTER_SET.finditer(expr):
        for piece in m.group(1).split(","):
            r = piece.strip()
            if r and r not in regs_set:
                regs_set.append(r)
    registers = sorted(set(regs_single) | set(regs_set))
    operators = [name for name, rx in _RE_OPS.items() if rx.search(expr)]

    n_state_literals = len(_RE_DOMAIN.findall(expr))
    if n_state_literals == 0:
        # Fall back to bare-noetic counts (e.g. NoeticCluster{^2,^3}).
        n_state_literals = len(_RE_NOETIC.findall(expr))

    # Count the dynamics-relevant operators (not parentheses, not glyph counts).
    dynamic_ops = ["+", "×", "∘", "→", "←", "↔", "=", "·", "∪", "∩", "∖", "∈", "⊂", "⊆"]
    n_operators = sum(len(_RE_OPS[op].findall(expr)) for op in dynamic_ops)

    axes = {
        "noetics_used": noetics,
        "domains_used": domains,
        "drives_used": drives,
        "registers_used": registers,
        "operators_used": operators,
    }
    return axes, n_state_literals, n_operators


def _has(expr: str, *needles: str) -> bool:
    return any(n in expr for n in needles)


# ---------------------------------------------------------------------------
# Generator core — emits Seed candidates per grammar category, then packs
# them into task slots.
# ---------------------------------------------------------------------------


class PathDSeedEnumerator:
    """Combinatorial + curated enumerator of compiler-valid base CAS objects."""

    def __init__(self, seed: int = 4242, target_total: int = 6000) -> None:
        self.rng = random.Random(seed)
        self.target_total = target_total
        compiler_module = _load_compiler()
        self.compile_expression = compiler_module.compile_expression
        self.accepted: list[Seed] = []
        self.rejected: list[dict[str, Any]] = []
        # next_id counter per grammar category for stable IDs.
        self._id_counters: dict[str, int] = defaultdict(int)

    # ---- helpers ----------------------------------------------------------

    def _new_id(self, category: str) -> str:
        self._id_counters[category] += 1
        return f"seed_{category}_{self._id_counters[category]:05d}"

    def _try(
        self,
        expression: str,
        grammar_category: str,
        task_slot: str,
        source: str = "combinatorial",
        extra_meta: dict[str, Any] | None = None,
    ) -> bool:
        artifact = self.compile_expression(expression)
        if not getattr(artifact, "valid", False):
            self.rejected.append(
                {
                    "expression": expression,
                    "grammar_category": grammar_category,
                    "task_slot": task_slot,
                    "source": source,
                    "error": getattr(artifact, "error", "") or "",
                }
            )
            return False
        axes, n_states, n_ops = _extract_axes(expression)
        seed = Seed(
            seed_id=self._new_id(grammar_category),
            task_slot=task_slot,
            grammar_category=grammar_category,
            expression=expression,
            compiler_validated=True,
            axes=axes,
            n_state_literals=n_states,
            n_operators=n_ops,
            uses_named_omega=bool(_RE_OMEGA_NAME.search(expression)) or "Ω" in expression,
            uses_theta_recipe=("Θ" in expression) or expression.lstrip().startswith("Theta"),
            uses_meta_logic=_has(
                expression,
                "Cluster", "Set{", "CoverOf", "PartitionOf", "Tuple",
                "Coordinate", "Product(", "Pullback(", "∈", "⊆", "⊂",
                "∪", "∩", "∖",
            ),
            uses_fractal=_has(expression, "Phi<", "Phi⟨", "Φ<", "Φ⟨"),
            metadata={
                "source": source,
                "seed_for_task_slot": task_slot,
                **(extra_meta or {}),
            },
        )
        self.accepted.append(seed)
        return True

    # ---- grammar category emitters ---------------------------------------

    # The six task slots are sampled uniformly across each emitter. We pin
    # different slots to different categories where the slot's training
    # signal is naturally aligned (e.g. fractal_sequence → expression_to_trace
    # works particularly well because the trace exposes the sequence).

    TASK_SLOTS = (
        "cas_to_english",
        "english_to_cas",
        "invalid_to_explanation",
        "invalid_to_corrected",
        "operation_to_outcome",
        "expression_to_trace",
    )

    def _slot(self) -> str:
        return self.rng.choice(self.TASK_SLOTS)

    # 1. State literals: ^N, ^N^D, ^N^D_{Fk}, ^N^D|R, ^N^D_{Fk}|R, ^N^D|⟨...⟩
    def emit_state_literals(self, target: int) -> None:
        emitted = 0
        # Phase A: bare ^N (10 forms).
        for n in NOETICS:
            if self._try(f"^{n}", "state_literal", self._slot()):
                emitted += 1
        # Phase B: ^N^D (10 × 4 = 40 forms).
        for n, d in itertools.product(NOETICS, DOMAINS):
            if emitted >= target:
                return
            if self._try(f"^{n}^{d}", "state_literal", self._slot()):
                emitted += 1
        # Phase C: ^N^D_{Fk} (10 × 4 × 7 = 280 forms).
        for n, d, fk in itertools.product(NOETICS, DOMAINS, DRIVES):
            if emitted >= target:
                return
            if self._try(f"^{n}^{d}_{{F{fk}}}", "state_literal", self._slot()):
                emitted += 1
        # Phase D: ^N^D|R single register (10 × 4 × 4 = 160 forms).
        for n, d, r in itertools.product(NOETICS, DOMAINS, REGISTERS):
            if emitted >= target:
                return
            if self._try(f"^{n}^{d}|{r}", "state_literal", self._slot()):
                emitted += 1
        # Phase E: ^N^D_{Fk}|R (10 × 4 × 7 × 4 = 1120 — sample).
        combos = list(itertools.product(NOETICS, DOMAINS, DRIVES, REGISTERS))
        self.rng.shuffle(combos)
        for n, d, fk, r in combos:
            if emitted >= target:
                return
            expr = f"^{n}^{d}_{{F{fk}}}|{r}"
            if self._try(expr, "state_literal", self._slot()):
                emitted += 1
        # Phase F: ^N^D|⟨R1,R2[,R3]⟩ (multi-register specification, v7.7).
        for n, d in itertools.product(NOETICS, DOMAINS):
            if emitted >= target:
                return
            # Pick 2-3 distinct registers in deterministic order.
            k = self.rng.choice([2, 2, 3])
            regs = self.rng.sample(REGISTERS, k)
            inner = ",".join(regs)
            expr = f"^{n}^{d}|⟨{inner}⟩"
            if self._try(expr, "state_literal", self._slot(),
                         extra_meta={"multi_register": True}):
                emitted += 1

    # 2. Binary composition: two-operand `+`, `×`, `∘`, `→`.
    def emit_binary_compositions(self, target: int) -> None:
        emitted = 0
        # `+` — same-Noetic register co-presence (Clarification 10 §3 |+).
        for n, d in itertools.product(NOETICS, DOMAINS):
            if emitted >= target:
                return
            r1, r2 = self.rng.sample(REGISTERS, 2)
            expr = f"^{n}^{d}|{r1} + ^{n}^{d}|{r2}"
            if self._try(expr, "binary_composition", self._slot(),
                         extra_meta={"op": "+"}):
                emitted += 1
        # `+` cross-Noetic (different-state association).
        ops_made = 0
        while ops_made < target // 4 and emitted < target:
            n1, n2 = self.rng.sample(NOETICS, 2)
            d = self.rng.choice(DOMAINS)
            expr = f"^{n1}^{d} + ^{n2}^{d}"
            if self._try(expr, "binary_composition", self._slot(),
                         extra_meta={"op": "+"}):
                emitted += 1
            ops_made += 1
        # `×` — generative integration (different-Noetic).
        ops_made = 0
        while ops_made < target // 4 and emitted < target:
            n1, n2 = self.rng.sample(NOETICS, 2)
            d = self.rng.choice(DOMAINS)
            expr = f"^{n1}^{d} × ^{n2}^{d}"
            if self._try(expr, "binary_composition", self._slot(),
                         extra_meta={"op": "×"}):
                emitted += 1
            ops_made += 1
        # `∘` — fractal composition. Apply at the operator level (CO-N ∘ CO-M).
        for n1, n2 in itertools.product(NOETICS, NOETICS):
            if emitted >= target:
                return
            expr = f"CO-{n1} ∘ CO-{n2}"
            if self._try(expr, "binary_composition", self._slot(),
                         extra_meta={"op": "∘"}):
                emitted += 1
        # `→` — relation (state -> state, single arrow only — chained arrows
        # type-check fails because relation-typed values can't appear in a
        # second arrow position). Domain descent rule (compiler typecheck):
        # ARROW requires DOMAIN_ORDER[left] ≤ DOMAIN_ORDER[right] (P=0 ≤ C ≤
        # E ≤ O); ascending arrows like O -> P are rejected. Generate only
        # admissible domain pairs.
        for _ in range(target - emitted):
            if emitted >= target:
                return
            n1, n2 = self.rng.choice(NOETICS), self.rng.choice(NOETICS)
            d1_idx = self.rng.randint(0, 3)
            d2_idx = self.rng.randint(d1_idx, 3)  # non-decreasing
            d1, d2 = DOMAINS[d1_idx], DOMAINS[d2_idx]
            expr = f"^{n1}^{d1} -> ^{n2}^{d2}"
            if self._try(expr, "binary_composition", self._slot(),
                         extra_meta={"op": "->"}):
                emitted += 1

    # 3. Cross-register Ω forms: (state|R1 × state|R2 [× state|R3]) = state|Ω_name
    def emit_cross_register_omega(self, target: int) -> None:
        emitted = 0
        attempts = 0
        max_attempts = target * 4
        while emitted < target and attempts < max_attempts:
            attempts += 1
            n = self.rng.choice(NOETICS)
            d = self.rng.choice(DOMAINS + (None,))
            k = self.rng.choice([2, 2, 3])
            regs = self.rng.sample(REGISTERS, k)
            omega = self.rng.choice(OMEGA_NAMES)
            dom_part = f"^{d}" if d else ""
            terms = [f"^{n}{dom_part}|{r}" for r in regs]
            expr = "(" + " × ".join(terms) + f") = ^{n}{dom_part}|Ω_{omega}"
            if self._try(expr, "cross_register_omega", self._slot(),
                         extra_meta={"omega_name": f"Omega_{omega}",
                                     "n_registers": k}):
                emitted += 1

    # 4. Recipes: Θ(Ω_name) = a₁·X₁ + a₂·X₂ [+ ...] → Ω_name [+ Λ·Ω_side]
    def emit_recipes(self, target: int) -> None:
        emitted = 0
        attempts = 0
        max_attempts = target * 4
        while emitted < target and attempts < max_attempts:
            attempts += 1
            name = self.rng.choice(RECIPE_NAMES) + f"_{attempts % 100:02d}"
            n_ingredients = self.rng.choice([2, 2, 3])
            ingredients: list[str] = []
            used_states: set[tuple[int, str]] = set()
            for _ in range(n_ingredients):
                # Pick a unique (n, d) for each ingredient to keep recipes
                # well-formed.
                tries = 0
                while tries < 8:
                    nn = self.rng.choice(NOETICS)
                    dd = self.rng.choice(DOMAINS)
                    if (nn, dd) not in used_states:
                        used_states.add((nn, dd))
                        break
                    tries += 1
                coef = self.rng.choice([1, 2, 0.5, 0.7, 1.5])
                coef_str = f"{coef:g}"
                # Sometimes attach a drive / register to the ingredient.
                state_str = f"^{nn}^{dd}"
                if self.rng.random() < 0.4:
                    state_str += f"_{{F{self.rng.choice(DRIVES)}}}"
                if self.rng.random() < 0.3:
                    state_str += f"|{self.rng.choice(REGISTERS)}"
                ingredients.append(f"{coef_str}*{state_str}")
            # Optional leakage on the RHS.
            rhs = f"Ω_{name}"
            has_leak = self.rng.random() < 0.25
            if has_leak:
                leak_name = self.rng.choice(RECIPE_NAMES)
                leak_mag = self.rng.choice([0.05, 0.1, 0.15])
                rhs += f" + {leak_mag:g}*Λ·Ω_{leak_name}_side"
            expr = (
                f"Θ(Ω_{name}) = "
                + " + ".join(ingredients)
                + f" → {rhs}"
            )
            if self._try(expr, "recipe", self._slot(),
                         extra_meta={"recipe_name": name,
                                     "n_ingredients": n_ingredients,
                                     "has_leakage": has_leak}):
                emitted += 1

    # 5. Meta-logic relations: clusters, set ops, CoverOf, PartitionOf,
    # Tuple/Coordinate, Product, membership, subset, cardinality.
    def emit_meta_logic(self, target: int) -> None:
        emitted = 0
        # NoeticCluster — core building block.
        while emitted < target * 3 // 10:
            k = self.rng.randint(2, 6)
            chosen = sorted(self.rng.sample(NOETICS, k))
            inner = ", ".join(f"^{n}" for n in chosen)
            expr = f"NoeticCluster{{{inner}}}"
            if self._try(expr, "meta_logic_relation", self._slot(),
                         extra_meta={"constructor": "NoeticCluster"}):
                emitted += 1
            else:
                # Should never fail for non-empty bare-noetic clusters.
                break
            if emitted >= target:
                return

        # StateCluster
        while emitted < target * 5 // 10:
            k = self.rng.randint(2, 6)
            pool = [(n, d) for n in NOETICS for d in DOMAINS]
            chosen = self.rng.sample(pool, k)
            inner = ", ".join(f"^{n}^{d}" for n, d in chosen)
            expr = f"StateCluster{{{inner}}}"
            if self._try(expr, "meta_logic_relation", self._slot(),
                         extra_meta={"constructor": "StateCluster"}):
                emitted += 1
            if emitted >= target:
                return

        # StateVariantCluster (drive + register variants)
        while emitted < target * 6 // 10:
            k = self.rng.randint(2, 4)
            atoms: list[str] = []
            seen = set()
            tries = 0
            while len(atoms) < k and tries < 16:
                tries += 1
                n = self.rng.choice(NOETICS)
                d = self.rng.choice(DOMAINS)
                f = self.rng.choice(DRIVES) if self.rng.random() < 0.5 else None
                r = self.rng.choice(REGISTERS)
                key = (n, d, f, r)
                if key in seen:
                    continue
                seen.add(key)
                if f is not None:
                    atoms.append(f"^{n}^{d}_{{F{f}}}|{r}")
                else:
                    atoms.append(f"^{n}^{d}|{r}")
            inner = ", ".join(atoms)
            expr = f"StateVariantCluster{{{inner}}}"
            if self._try(expr, "meta_logic_relation", self._slot(),
                         extra_meta={"constructor": "StateVariantCluster"}):
                emitted += 1
            if emitted >= target:
                return

        # Set ops on clusters: ∪, ∩, ∖.
        while emitted < target * 7 // 10:
            op = self.rng.choice(("∪", "∩", "∖"))
            a = sorted(self.rng.sample(NOETICS, self.rng.randint(2, 4)))
            b = sorted(self.rng.sample(NOETICS, self.rng.randint(2, 4)))
            inner_a = ", ".join(f"^{n}" for n in a)
            inner_b = ", ".join(f"^{n}" for n in b)
            expr = f"NoeticCluster{{{inner_a}}} {op} NoeticCluster{{{inner_b}}}"
            if self._try(expr, "meta_logic_relation", self._slot(),
                         extra_meta={"constructor": "set_op", "op": op}):
                emitted += 1
            if emitted >= target:
                return

        # CoverOf / PartitionOf — base must be covered by union of members,
        # and (for PartitionOf) members disjoint. Use Noetics base partitioned
        # into halves / quarters so the cover/partition is always valid.
        cover_partition_attempts = 0
        while emitted < target * 8 // 10 and cover_partition_attempts < target:
            cover_partition_attempts += 1
            constructor = self.rng.choice(("CoverOf", "PartitionOf"))
            # Random partition of NOETICS into 2-3 disjoint groups.
            shuffled = list(NOETICS)
            self.rng.shuffle(shuffled)
            n_groups = self.rng.choice([2, 3])
            cuts = sorted(self.rng.sample(range(1, len(shuffled)), n_groups - 1))
            groups: list[list[int]] = []
            prev = 0
            for c in cuts:
                groups.append(sorted(shuffled[prev:c]))
                prev = c
            groups.append(sorted(shuffled[prev:]))
            if any(len(g) == 0 for g in groups):
                continue
            members_str = ", ".join(
                f"NoeticCluster{{{', '.join(f'^{n}' for n in g)}}}"
                for g in groups
            )
            # For CoverOf, optionally add overlap between groups by re-adding
            # a Noetic to the first group from the second.
            if constructor == "CoverOf" and self.rng.random() < 0.4 and len(groups) >= 2:
                if groups[1]:
                    extra = groups[1][0]
                    if extra not in groups[0]:
                        groups_overlap = [sorted(groups[0] + [extra])] + groups[1:]
                        members_str = ", ".join(
                            f"NoeticCluster{{{', '.join(f'^{n}' for n in g)}}}"
                            for g in groups_overlap
                        )
            expr = f"{constructor}(Noetics, {members_str})"
            if self._try(expr, "meta_logic_relation", self._slot(),
                         extra_meta={"constructor": constructor,
                                     "n_members": len(groups)}):
                emitted += 1
            if emitted >= target:
                return

        # Tuple / Coordinate / Product / membership / subset / cardinality.
        while emitted < target:
            choice = self.rng.choice(
                ("tuple", "coordinate", "product", "member", "subset", "cardinality")
            )
            if choice == "tuple":
                n = self.rng.choice(NOETICS)
                d = self.rng.choice(DOMAINS)
                fk = self.rng.choice(DRIVES)
                # Lexer ambiguity: bare `E` lexes as DOMAIN (Evaluative),
                # never REGISTER. Tuple/Coordinate slot-4 typecheck requires
                # a register symbol. Restrict bare-register slot to T / A / f.
                r = self.rng.choice(("T", "A", "f"))
                expr = f"Tuple{{^{n}, {d}, F{fk}, {r}}}"
            elif choice == "coordinate":
                n = self.rng.choice(NOETICS)
                d = self.rng.choice(DOMAINS)
                fk = self.rng.choice(DRIVES)
                r = self.rng.choice(("T", "A", "f"))
                expr = f"Coordinate{{^{n}, {d}, F{fk}, {r}}}"
            elif choice == "product":
                a = sorted(self.rng.sample(NOETICS, self.rng.randint(2, 3)))
                b = sorted(self.rng.sample(NOETICS, self.rng.randint(2, 3)))
                expr = (
                    f"Product(NoeticCluster{{{', '.join(f'^{n}' for n in a)}}}, "
                    f"NoeticCluster{{{', '.join(f'^{n}' for n in b)}}})"
                )
            elif choice == "member":
                # ^N ∈ Noetics, F_k ∈ Drives, ^N^D ∈ States, etc.
                pick = self.rng.choice(("noetic", "drive", "state"))
                if pick == "noetic":
                    expr = f"^{self.rng.choice(NOETICS)} ∈ Noetics"
                elif pick == "drive":
                    expr = f"F{self.rng.choice(DRIVES)} ∈ Drives"
                else:
                    expr = (
                        f"^{self.rng.choice(NOETICS)}^"
                        f"{self.rng.choice(DOMAINS)} ∈ States"
                    )
            elif choice == "subset":
                k = self.rng.randint(1, 3)
                chosen = sorted(self.rng.sample(NOETICS, k))
                inner = ", ".join(f"^{n}" for n in chosen)
                op = self.rng.choice(("⊂", "⊆"))
                expr = f"NoeticCluster{{{inner}}} {op} Noetics"
            else:  # cardinality
                pick = self.rng.choice(("noetics", "drives", "states", "cluster"))
                if pick == "noetics":
                    expr = "|Noetics|"
                elif pick == "drives":
                    expr = "|Drives|"
                elif pick == "states":
                    expr = "|States|"
                else:
                    k = self.rng.randint(2, 5)
                    chosen = sorted(self.rng.sample(NOETICS, k))
                    inner = ", ".join(f"^{n}" for n in chosen)
                    expr = f"|NoeticCluster{{{inner}}}|"
            if self._try(expr, "meta_logic_relation", self._slot(),
                         extra_meta={"constructor": choice}):
                emitted += 1
            else:
                # Bail to avoid pathological retry loops if a category
                # mis-fires; we already accepted plenty by this point.
                break

    # 6. Fractal sequences: Phi⟨k₁:k₂:...:kₙ⟩ (digits 0-9).
    def emit_fractal_sequences(self, target: int) -> None:
        emitted = 0
        # Lengths 2..8 — covers short involution echoes through deep
        # multi-level fractal trees.
        while emitted < target:
            n_steps = self.rng.choice([2, 2, 3, 3, 4, 4, 5, 6, 7, 8])
            # Allow repeats — fractal compositions can revisit Noetic indices.
            steps = [self.rng.choice(NOETICS) for _ in range(n_steps)]
            seq = ":".join(str(s) for s in steps)
            # Mix Phi/Φ and `<>`/`⟨⟩` brackets.
            head = self.rng.choice(("Phi", "Φ"))
            brackets = self.rng.choice(("<>", "⟨⟩"))
            l, r = brackets[0], brackets[1]
            expr = f"{head}{l}{seq}{r}"
            if self._try(expr, "fractal_sequence", self._slot(),
                         extra_meta={"sequence_length": n_steps,
                                     "head": head}):
                emitted += 1
            else:
                break

    # 7. let bindings + diagram exports.
    def emit_let_bindings(self, target: int) -> None:
        emitted = 0
        while emitted < target * 6 // 10:
            n = self.rng.choice(NOETICS)
            d = self.rng.choice(DOMAINS)
            name = self.rng.choice(
                ("attraction", "judgment", "balance", "echo", "weight",
                 "anchor", "phase", "drift", "settle", "trace")
            ) + f"_{emitted:04d}"
            optional_drive = ""
            if self.rng.random() < 0.4:
                optional_drive = f"_{{F{self.rng.choice(DRIVES)}}}"
            optional_reg = ""
            if self.rng.random() < 0.4:
                optional_reg = f"|{self.rng.choice(REGISTERS)}"
            expr = f"let {name} = ^{n}^{d}{optional_drive}{optional_reg}"
            if self._try(expr, "let_binding", self._slot(),
                         extra_meta={"binding_name": name}):
                emitted += 1
            if emitted >= target:
                return

        # Two-statement let; reference the first inside the second so the
        # variable resolution path is exercised. Honor domain descent
        # (P=0 ≤ C ≤ E ≤ O for ARROW operands).
        while emitted < target:
            n1 = self.rng.choice(NOETICS)
            n2 = self.rng.choice(NOETICS)
            d1_idx = self.rng.randint(0, 3)
            d2_idx = self.rng.randint(d1_idx, 3)
            d1, d2 = DOMAINS[d1_idx], DOMAINS[d2_idx]
            # Identifier names: avoid PCEO-prefix that the lexer reads as
            # STATE_REF (e.g. `P1`, `D2`, `O0`); prefix with `vsrc_`/`vtgt_`.
            v1 = f"vsrc_{emitted:04d}"
            v2 = f"vtgt_{emitted:04d}"
            expr = (
                f"let {v1} = ^{n1}^{d1}; "
                f"let {v2} = ^{n2}^{d2}; "
                f"{v1} -> {v2}"
            )
            if self._try(expr, "let_binding", self._slot(),
                         extra_meta={"binding_name": f"{v1},{v2}",
                                     "multi_statement": True}):
                emitted += 1
            else:
                break

    def emit_diagram_exports(self, target: int) -> None:
        emitted = 0
        # `export let` statements — these are diagrammable artifacts at the
        # compiler layer (`CompilationArtifact.diagram()` consumes them).
        # Identifier roots: avoid bare `eta` / `iota` / `kappa` / `Theta` /
        # `Omega` / `Lambda` / `Phi` because the lexer matches them as v7.6
        # recipe keywords (KAPPA / ETA / IOTA tokens) regardless of trailing
        # underscore; the safe Greek-flavored roots below all start with a
        # letter that has no compiler-keyword conflict.
        SAFE_NAME_ROOTS = (
            "alpha", "beta", "gamma", "delta", "epsilon", "zeta",
            "mu", "nu", "xi", "rho", "sigma", "tau", "upsilon", "chi",
            "psi", "node",
        )
        while emitted < target:
            kind = self.rng.choice(("state", "recipe", "cluster", "relation"))
            name_root = self.rng.choice(SAFE_NAME_ROOTS)
            name = f"{name_root}_{emitted:04d}"
            if kind == "state":
                n = self.rng.choice(NOETICS)
                d = self.rng.choice(DOMAINS)
                fk = self.rng.choice(DRIVES)
                expr = f"export let {name} = ^{n}^{d}_{{F{fk}}}"
            elif kind == "recipe":
                rname = self.rng.choice(RECIPE_NAMES)
                n1 = self.rng.choice(NOETICS)
                n2 = self.rng.choice(NOETICS)
                d = self.rng.choice(DOMAINS)
                if n1 == n2:
                    n2 = (n2 + 1) % 10
                expr = (
                    f"export let {name} = "
                    f"Theta(Omega_{rname}) = 1*^{n1}^{d} + 1*^{n2}^{d} -> Omega_{rname}"
                )
            elif kind == "cluster":
                k = self.rng.randint(2, 5)
                chosen = sorted(self.rng.sample(NOETICS, k))
                inner = ", ".join(f"^{n}" for n in chosen)
                expr = f"export let {name} = NoeticCluster{{{inner}}}"
            else:  # relation
                n1 = self.rng.choice(NOETICS)
                n2 = self.rng.choice(NOETICS)
                d1_idx = self.rng.randint(0, 3)
                d2_idx = self.rng.randint(d1_idx, 3)  # ARROW domain descent
                d1, d2 = DOMAINS[d1_idx], DOMAINS[d2_idx]
                expr = f"export let {name} = ^{n1}^{d1} -> ^{n2}^{d2}"
            if self._try(expr, "diagram_export", self._slot(),
                         extra_meta={"export_name": name, "export_kind": kind}):
                emitted += 1
            else:
                # Fall back to next iteration with a fresh seed — single
                # failure should not stall the loop.
                continue

    # 8. RPM chains — let-bind A0/Dn/Wn/Pn-style stages and chain them with
    # `->`. The compiler accepts only single-arrow relations (state -> state),
    # so we build chains by emitting multiple let-bindings + a single arrow
    # per seed. The "chain" identity is structural: each seed contains a full
    # RPM stage list as named variables, with one displayed arrow.
    #
    # Identifier discipline: the lexer matches `[PCEO]\d+` as STATE_REF
    # (e.g. `P1` lexes as state ref `^1^P`, not as identifier `P1`). RPM
    # stage names that begin with a domain letter immediately followed by
    # a digit collide with state_ref. Prefix every stage name with
    # `stage` so the lexer reads the full token as IDENT.
    def emit_rpm_chains(self, target: int) -> None:
        emitted = 0
        while emitted < target:
            # Pick an RPM stage to surface (D, W, or P), and a drive index.
            drive_idx = self.rng.randint(1, 7)
            n = self.rng.choice(NOETICS)
            # Bind A0 (Pure Desire), Dn, Wn, Pn as concrete states. The CAS
            # capability-pathway scheme: A0 → Dn → Wn → Pn.
            a0_state = f"^0^P"
            d_state = f"^{n}^P_{{F{drive_idx}}}"
            w_state = f"^{n}^C_{{F{drive_idx}}}"
            p_state = f"^{n}^E_{{F{drive_idx}}}"
            chain_uid = f"{drive_idx}_{emitted:04d}"
            arrow_pair = self.rng.choice(
                (("A0", "D"), ("D", "W"), ("W", "P"))
            )
            arrow_src, arrow_tgt = arrow_pair
            # Stage variable names — `stage` prefix avoids the [PCEO]\d
            # STATE_REF collision the lexer enforces.
            sa0 = f"stageA0_{chain_uid}"
            sd = f"stageD{drive_idx}_{chain_uid}"
            sw = f"stageW{drive_idx}_{chain_uid}"
            sp = f"stageP{drive_idx}_{chain_uid}"
            stage_to_name = {"A0": sa0, "D": sd, "W": sw, "P": sp}
            src_name = stage_to_name[arrow_src]
            tgt_name = stage_to_name[arrow_tgt]
            stmts = [
                f"let {sa0} = {a0_state}",
                f"let {sd} = {d_state}",
                f"let {sw} = {w_state}",
                f"let {sp} = {p_state}",
                f"{src_name} -> {tgt_name}",
            ]
            expr = "; ".join(stmts)
            if self._try(expr, "rpm_chain", self._slot(),
                         extra_meta={"drive_index": drive_idx,
                                     "stage_pair": arrow_src + "->" + arrow_tgt,
                                     "chain_uid": chain_uid}):
                emitted += 1
            else:
                break

    # 9. Inversion-axis structural patterns.
    def emit_inversion_patterns(self, target: int) -> None:
        emitted = 0
        # Axis N — operator/Noetic involution: pair ^p^D with ^q^D where
        # (p, q) is an involution pair. Compose with `+` (co-presence)
        # instead of `×` (since `×` on different Noetics in the same domain
        # is generative).
        for p, q in INVOLUTION_PAIRS:
            for d in DOMAINS:
                if emitted >= target * 2 // 7:
                    break
                expr = f"^{p}^{d} + ^{q}^{d}"
                if self._try(expr, "inversion", self._slot(),
                             extra_meta={"axis": "N", "involution_pair": [p, q]}):
                    emitted += 1
        # Axis W — domain-precedence chain (P -> C, C -> E, E -> O).
        precedence_pairs = [("P", "C"), ("C", "E"), ("E", "O")]
        for d1, d2 in precedence_pairs:
            for n in NOETICS[:6]:
                if emitted >= target * 3 // 7:
                    break
                expr = f"^{n}^{d1} -> ^{n}^{d2}"
                if self._try(expr, "inversion", self._slot(),
                             extra_meta={"axis": "W",
                                         "domain_pair": [d1, d2]}):
                    emitted += 1
        # Axis F — drive-pair contrast (F1↔F7, F2↔F6, F3↔F5).
        drive_pairs = [(1, 7), (2, 6), (3, 5)]
        for f1, f2 in drive_pairs:
            for d in DOMAINS:
                if emitted >= target * 4 // 7:
                    break
                expr = f"^{2}^{d}_{{F{f1}}} + ^{3}^{d}_{{F{f2}}}"
                if self._try(expr, "inversion", self._slot(),
                             extra_meta={"axis": "F",
                                         "drive_pair": [f1, f2]}):
                    emitted += 1
        # Axis E — entropy-deficit structural shape (cluster on a single
        # noetic, all four domains).
        for n in NOETICS[:6]:
            if emitted >= target * 5 // 7:
                break
            inner = ", ".join(f"^{n}^{d}" for d in DOMAINS)
            expr = f"StateCluster{{{inner}}}"
            if self._try(expr, "inversion", self._slot(),
                         extra_meta={"axis": "E", "noetic": n}):
                emitted += 1
        # Axis S — sub-drive cross-domain variance (same drive, all 4 domains).
        for fk in DRIVES:
            if emitted >= target * 6 // 7:
                break
            inner = ", ".join(f"^{2}^{d}_{{F{fk}}}" for d in DOMAINS)
            expr = f"StateVariantCluster{{{inner}}}"
            if self._try(expr, "inversion", self._slot(),
                         extra_meta={"axis": "S", "drive": fk}):
                emitted += 1
        # Axis A — RPM chain endpoints (A0 -> P3 short bind+arrow). Use
        # `stage`-prefixed names to avoid [PCEO]\d STATE_REF lexer collision.
        # The arrow `^0^P -> ^N^E` honors domain descent (P=0 < E=2).
        for fk in DRIVES:
            if emitted >= target:
                break
            chain_uid = f"axisA_{fk}"
            stmts = [
                f"let stageA0_{chain_uid} = ^0^P",
                f"let stageP{fk}_{chain_uid} = ^{(fk + 1) % 10}^E_{{F{fk}}}",
                f"stageA0_{chain_uid} -> stageP{fk}_{chain_uid}",
            ]
            expr = "; ".join(stmts)
            if self._try(expr, "inversion", self._slot(),
                         extra_meta={"axis": "A", "drive": fk}):
                emitted += 1
        # Axis P (compound) — combined Noetic + Domain + Drive variation in
        # a single named emergent integration.
        for n in (2, 3, 5, 6):
            for d in DOMAINS:
                if emitted >= target:
                    break
                expr = (
                    f"(^{n}^{d}|A × ^{n}^{d}|f × ^{n}^{d}|T) "
                    f"= ^{n}^{d}|Ω_compound"
                )
                if self._try(expr, "inversion", self._slot(),
                             extra_meta={"axis": "P", "noetic": n,
                                         "domain": d}):
                    emitted += 1

    # 10. Edge cases — identity composition, self-dual operators on self-dual
    # noetics, RPM endpoints.
    def emit_edge_cases(self, target: int = 60) -> None:
        emitted = 0
        # Identity composition (CO-X ∘ CO-X) — valid; runtime handles it.
        for n in NOETICS:
            if self._try(
                f"CO-{n} ∘ CO-{n}",
                "binary_composition",
                "operation_to_outcome",
                source="curated_edge",
                extra_meta={"edge_case": "identity_composition"},
            ):
                emitted += 1
            if emitted >= target:
                return
        # Self-dual operators on self-dual noetics.
        for n in SELF_DUAL_NOETICS:
            for d in DOMAINS:
                if self._try(
                    f"^{n}^{d} ∘ ^{n}^{d}",
                    "binary_composition",
                    "operation_to_outcome",
                    source="curated_edge",
                    extra_meta={"edge_case": "self_dual_state_composition",
                                "noetic": n},
                ):
                    emitted += 1
                if emitted >= target:
                    return
        # Identity Ω — registers fully overlap themselves.
        for n in NOETICS:
            for d in DOMAINS:
                if emitted >= target:
                    return
                expr = (
                    f"(^{n}^{d}|A × ^{n}^{d}|f) = ^{n}^{d}|Ω_self"
                )
                if self._try(
                    expr, "cross_register_omega", "expression_to_trace",
                    source="curated_edge",
                    extra_meta={"edge_case": "two_register_omega",
                                "noetic": n, "domain": d},
                ):
                    emitted += 1

    # ---- top-level orchestration ----------------------------------------

    def run(self) -> None:
        # Targets per category. The 7 token categories in the Path D
        # pipeline §4 (state literals, drive subscripts, register tags,
        # operators, production recipes, meta-logic constructors, fractals)
        # must each appear in ≥500 accepted seeds. The grammar-category
        # targets below over-allocate for the categories that carry those
        # token signatures so the per-token threshold is comfortably met
        # with margin.
        TARGETS = {
            "state_literals": 1100,
            "binary_compositions": 750,
            "cross_register_omega": 650,
            "recipes": 600,
            "meta_logic": 800,
            "fractal_sequences": 600,
            "let_bindings": 500,
            "diagram_exports": 500,
            "rpm_chains": 400,
            "inversion": 350,
        }
        # Scale to target_total. The default sums to 6250 — tightly within
        # the 6K target band.
        scale = self.target_total / sum(TARGETS.values())
        scaled = {k: max(1, int(v * scale)) for k, v in TARGETS.items()}

        t0 = time.time()
        self.emit_state_literals(scaled["state_literals"])
        self.emit_binary_compositions(scaled["binary_compositions"])
        self.emit_cross_register_omega(scaled["cross_register_omega"])
        self.emit_recipes(scaled["recipes"])
        self.emit_meta_logic(scaled["meta_logic"])
        self.emit_fractal_sequences(scaled["fractal_sequences"])
        self.emit_let_bindings(scaled["let_bindings"])
        self.emit_diagram_exports(scaled["diagram_exports"])
        self.emit_rpm_chains(scaled["rpm_chains"])
        self.emit_inversion_patterns(scaled["inversion"])
        self.emit_edge_cases(target=60)
        elapsed = time.time() - t0
        print(
            f"[generate_path_d_seeds] accepted={len(self.accepted)} "
            f"rejected={len(self.rejected)} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )


# ---------------------------------------------------------------------------
# Output: jsonl + coverage report
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _build_coverage_report(
    seeds: list[Seed],
    rejected: list[dict[str, Any]],
    out_path: Path,
) -> None:
    by_slot: Counter = Counter(s.task_slot for s in seeds)
    by_grammar: Counter = Counter(s.grammar_category for s in seeds)
    noetic_counter: Counter = Counter()
    domain_counter: Counter = Counter()
    drive_counter: Counter = Counter()
    register_counter: Counter = Counter()
    operator_counter: Counter = Counter()
    n_omega = 0
    n_theta = 0
    n_meta_logic = 0
    n_fractal = 0
    for s in seeds:
        for n in s.axes.get("noetics_used", []):
            noetic_counter[n] += 1
        for d in s.axes.get("domains_used", []):
            domain_counter[d] += 1
        for fk in s.axes.get("drives_used", []):
            drive_counter[fk] += 1
        for r in s.axes.get("registers_used", []):
            register_counter[r] += 1
        for op in s.axes.get("operators_used", []):
            operator_counter[op] += 1
        if s.uses_named_omega:
            n_omega += 1
        if s.uses_theta_recipe:
            n_theta += 1
        if s.uses_meta_logic:
            n_meta_logic += 1
        if s.uses_fractal:
            n_fractal += 1

    total_attempted = len(seeds) + len(rejected)
    rejection_rate = (len(rejected) / total_attempted) if total_attempted else 0.0

    lines: list[str] = []
    lines.append("# Path D Wave 1B — Seed Coverage Report")
    lines.append("")
    lines.append(f"- Total accepted seeds: **{len(seeds)}**")
    lines.append(f"- Total rejected attempts: **{len(rejected)}**")
    lines.append(f"- Validation rejection rate: **{rejection_rate:.2%}**")
    lines.append("")
    lines.append("## Per task slot")
    lines.append("")
    lines.append("| task_slot | count |")
    lines.append("|---|---|")
    for slot, count in sorted(by_slot.items()):
        lines.append(f"| {slot} | {count} |")
    lines.append("")
    lines.append("## Per grammar category")
    lines.append("")
    lines.append("| grammar_category | count |")
    lines.append("|---|---|")
    for g, count in sorted(by_grammar.items()):
        lines.append(f"| {g} | {count} |")
    lines.append("")
    lines.append("## 7-category coverage check (≥500 threshold per memory rule)")
    lines.append("")
    seven_cats = {
        "1. state_literal": by_grammar.get("state_literal", 0),
        "2. drive subscripts (drives_used > 0)": sum(1 for s in seeds if s.axes.get("drives_used")),
        "3. registers (registers_used > 0)": sum(1 for s in seeds if s.axes.get("registers_used")),
        "4. operators (binary_composition + arrows + ∘)": by_grammar.get("binary_composition", 0),
        "5. recipes (uses_theta_recipe)": n_theta,
        "6. meta-logic (uses_meta_logic)": n_meta_logic,
        "7. fractals (uses_fractal)": n_fractal,
    }
    lines.append("| category | count | met ≥500 |")
    lines.append("|---|---|---|")
    for name, count in seven_cats.items():
        ok = "PASS" if count >= 500 else "FAIL"
        lines.append(f"| {name} | {count} | {ok} |")
    lines.append("")
    lines.append("## Per axis token distribution")
    lines.append("")
    lines.append("### Noetics used (count of seeds containing each Noetic)")
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
    reject_reasons = Counter(
        (r.get("error", "")).split(":", 1)[0] for r in rejected
    )
    if reject_reasons:
        lines.append("| stage | count |")
        lines.append("|---|---|")
        for stage, count in reject_reasons.most_common(10):
            lines.append(f"| {stage} | {count} |")
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
            "Generate Path D Wave 1B compiler-validated CAS seed objects."
        )
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("cas-synthetic/data/path_d"),
        help="output directory for seeds.jsonl, seeds_rejected.jsonl, and "
             "seeds_coverage_report.md",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=6000,
        help="approximate total accepted seed count target (default 6000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=4242,
        help="random seed for deterministic enumeration",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="if set, truncate accepted seeds to this many before writing "
             "(used by the smoke test to produce a small enumeration)",
    )
    args = parser.parse_args(argv)

    enum = PathDSeedEnumerator(seed=args.seed, target_total=args.target)
    enum.run()

    accepted = enum.accepted
    if args.limit is not None and args.limit > 0:
        accepted = accepted[: args.limit]

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out_dir / "seeds.jsonl", (s.to_record() for s in accepted))
    _write_jsonl(out_dir / "seeds_rejected.jsonl", iter(enum.rejected))
    _build_coverage_report(
        accepted, enum.rejected, out_dir / "seeds_coverage_report.md"
    )

    print(
        f"[generate_path_d_seeds] wrote "
        f"{out_dir / 'seeds.jsonl'} ({len(accepted)} records), "
        f"{out_dir / 'seeds_rejected.jsonl'} ({len(enum.rejected)} records), "
        f"{out_dir / 'seeds_coverage_report.md'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
