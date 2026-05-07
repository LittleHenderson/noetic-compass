"""Path D Wave 2F — Compile-trace generator.

Path D corpus pipeline §2 deliverable F (`docs/working/
path_D_corpus_pipeline_design_2026_05_07.md`): produce one structured
compile trace per seed in `cas-synthetic/data/path_d/seeds.jsonl`. The
model learns to predict these traces in compiler-fluency curriculum task
#6 — *expression → compile trace* (`docs/working/
path_D_compiler_fluency_curriculum_2026_05_07.md` §6).

Trace contents per seed:

    trace_id              : "trace_<seed_id>"
    source_seed_id        : the originating seed_id
    expression            : the source CAS expression
    parse_tree            : hierarchical AST (serialize_ast output) +
                            source-position metadata when available from
                            the compiler tokens
    ast_summary           : flattened diagnostic — n_nodes, depth,
                            node_type_counts
    admissibility         : passes / checks_performed / violations
    rpm_result            : present only for RPM-pathway seeds
                            (chain, satisfied, broken_at)
    fractal_canonical     : present only for Cognitive Fractal seeds
                            (raw, simplified, convergence_class)
    register_analysis     : present only for register-tagged seeds
                            (single_or_multi, registers_used,
                             v77_operator_discipline_check)
    recipe_analysis       : present only for Θ recipe seeds
                            (target_omega, ingredients,
                             stoichiometry_balanced)
    meta_logic_analysis   : present only for set/relation constructor
                            seeds (constructors_used, well_formed)

Hard constraints honored:
- Does NOT modify the compiler.
- Does NOT modify seeds.jsonl or seed enumerator.
- Does NOT touch cas-native/inference or cas-native/evaluation.
- Does NOT generate variants (Agent C owns that).
- Does NOT generate invalid CAS (Agent D owns that).
- Does NOT tokenize the trace text — trace is structured JSON, which
  side-steps the v1↔v2 tokenizer compatibility question entirely
  (`docs/working/path_D_tokenizer_v2_coverage_2026_05_07.md`).
- Does NOT retrain anything.

Cognitive Fractal canonical form is re-derived in Python because the
Python `cas_engine` PyO3 binding does not expose the Rust fractal calculus
(`noetic-compass-scaffold/noetic-compass/cas-engine/src/python_bindings.rs`
exposes operators / states / RPM / drives but not `CognitiveFractal`).
The re-derivation matches the Rust authoritative semantics in
`noetic-compass-scaffold/noetic-compass/cas-engine/src/fractals/`:

    Involution-pair cancellation: (2,3) (3,2) (5,6) (6,5) (8,9) (9,8) → 0
    Identity elimination: interior 0s removed unless sequence collapses
    Convergence classification: Neutral (identity), Stabilizing
        (fixed-point reached), Oscillatory (cycle period > 1),
        Amplifying (orbit visits many distinct states without settling).

Output:
    cas-synthetic/data/path_d/compile_traces.jsonl
    cas-synthetic/data/path_d/compile_traces_coverage_report.md

Usage:
    python -m cas_synthetic.scripts.generate_path_d_compile_traces \
        --seeds cas-synthetic/data/path_d/seeds.jsonl \
        --out   cas-synthetic/data/path_d
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Compiler loader (mirrors generate_path_d_seeds.py).
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
    module_name = "cas_synthetic_path_d_trace_compiler"
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
# Cognitive Fractal canonical form (Python re-derivation).
#
# Authoritative reference: cas-engine/src/fractals/simplification.rs
#   Definitions 8.9-8.11, Theorem 8.12 (v6.1 manuscript).
# Authoritative classification: cas-engine/src/fractals/convergence.rs
#   Definition 8.20.
# ---------------------------------------------------------------------------

INVOLUTION_PAIRS = ((2, 3), (5, 6), (8, 9))


def _is_dual_pair(a: int, b: int) -> bool:
    for x, y in INVOLUTION_PAIRS:
        if (a == x and b == y) or (a == y and b == x):
            return True
    return False


def _cancel_duals_pass(ops: list[int]) -> int:
    """One pass of dual cancellation. Returns number of cancellations."""
    cancellations = 0
    i = 0
    while i + 1 < len(ops):
        if _is_dual_pair(ops[i], ops[i + 1]):
            ops[i] = 0
            ops.pop(i + 1)
            cancellations += 1
        else:
            i += 1
    return cancellations


def _eliminate_identities(ops: list[int]) -> None:
    """Remove interior zeros (Definition 8.10)."""
    if len(ops) <= 1:
        return
    ops[:] = [op for op in ops if op != 0]
    if not ops:
        ops.append(0)


def canonicalize_fractal(sequence: list[int]) -> list[int]:
    """Reduce sequence to its unique canonical form (Theorem 8.12).

    Applies dual cancellation + identity elimination to a fixed point.
    Mirrors `canonicalize` in cas-engine/src/fractals/simplification.rs.
    """
    ops = list(sequence)
    while True:
        cancellations = _cancel_duals_pass(ops)
        len_before = len(ops)
        _eliminate_identities(ops)
        len_after = len(ops)
        if cancellations == 0 and len_before == len_after:
            break
    if not ops:
        ops = [0]
    return ops


# Apply a fractal once to a CO operator state. The fractal sequence is
# applied as a *composition* of operators: ⟨a,b,c⟩ applied to E means
# c(b(a(E))) — left-to-right in monoid notation. For classifying
# convergence on the discrete CO-domain we treat the operator algebra
# of the Noetic involution-pair monoid: composing CO-k with another
# CO-k on a self-dual operator produces CO-k; composing CO-k with its
# involution produces CO-0. For non-paired operators, composition is
# the right-most operator (free monoid; CAS v6.1 Definition 8.7).
def _compose_step(state: int, op: int) -> int:
    """Single-step fractal composition on the CO operator domain."""
    if op == 0:
        return state
    if state == 0:
        return op
    # Involution pairs cancel to 0.
    if _is_dual_pair(state, op):
        return 0
    # Same operator twice = idempotent (self-dual or repeated absorption
    # in the canonical free monoid).
    if state == op:
        return state
    # Otherwise the right-most operator wins (free monoid composition).
    return op


def classify_fractal(canonical_sequence: list[int]) -> str:
    """Classify a canonicalized fractal sequence (Definition 8.20).

    - Neutral: identity ⟨0⟩
    - Stabilizing: orbit converges to a fixed point (period 1)
    - Oscillatory: orbit is periodic with period > 1
    - Amplifying: orbit visits many distinct states without settling

    Operates on the canonical sequence applied as Φ. The orbit is
    computed over the 10 CO operators (0-9), so the orbit must enter
    a cycle within ≤ 11 steps. Distinguishes period-1 (Stabilizing)
    from period > 1 (Oscillatory) by tracking the visit history.
    """
    if not canonical_sequence or canonical_sequence == [0]:
        return "Neutral"

    # Apply the fractal once: starting state = ⟨0⟩-composed.
    def apply_fractal(initial: int) -> int:
        s = initial
        for op in canonical_sequence:
            s = _compose_step(s, op)
        return s

    # Orbit from the all-domain test element: pick CO-0 as the natural
    # base (matches `Idea` as the universal substrate in CAS v7.4).
    seen_states: list[int] = []
    seen_set: set[int] = set()
    current = 0
    for _ in range(12):  # bounded by |CO-0..9| + 1
        nxt = apply_fractal(current)
        if nxt == current:
            return "Stabilizing"
        if nxt in seen_set:
            # Found a cycle. If the cycle returns immediately to a
            # different earlier state, period > 1 → Oscillatory.
            cycle_start = seen_states.index(nxt)
            period = len(seen_states) - cycle_start
            if period == 1:
                return "Stabilizing"
            return "Oscillatory"
        seen_states.append(nxt)
        seen_set.add(nxt)
        current = nxt
    # Walked the bound without settling: amplifying (orbit visits many
    # distinct states without entering a fixed point).
    return "Amplifying"


# ---------------------------------------------------------------------------
# AST walking helpers — counts/depth/type histogram.
# ---------------------------------------------------------------------------


def _walk_ast(node: Any) -> Iterable[dict[str, Any]]:
    """Iterate over every dict-shaped AST node returned by serialize_ast."""
    if isinstance(node, dict) and "node" in node:
        yield node
        for value in node.values():
            yield from _walk_ast(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_ast(item)


def _ast_depth(node: Any, depth: int = 0) -> int:
    """Maximum nesting depth of an AST returned by serialize_ast."""
    if isinstance(node, dict) and "node" in node:
        child_depths = [_ast_depth(v, depth + 1) for v in node.values()]
        return max([depth + 1] + child_depths)
    if isinstance(node, list):
        if not node:
            return depth
        return max(_ast_depth(item, depth) for item in node)
    return depth


def _ast_summary(ast: Any) -> dict[str, Any]:
    """Flattened diagnostic summary."""
    counts: Counter = Counter()
    n_nodes = 0
    for n in _walk_ast(ast):
        n_nodes += 1
        counts[n.get("node", "<unknown>")] += 1
    return {
        "n_nodes": n_nodes,
        "depth": _ast_depth(ast),
        "node_type_counts": dict(counts),
    }


# ---------------------------------------------------------------------------
# Source-position metadata: derived from compiler lex tokens. We attach a
# coarse `(start_position, end_position)` band to the top-level AST node.
# Token-by-token mapping is not surfaced (the compiler's serialize_ast
# does not carry per-node positions), but lex tokens give us the source
# span the parser consumed.
# ---------------------------------------------------------------------------


def _source_position_band(tokens: list[Any], expression: str) -> dict[str, Any]:
    """Coarse start/end span derived from the lex tokens."""
    if not tokens:
        return {"start": 0, "end": len(expression)}
    starts = [getattr(t, "position", 0) for t in tokens]
    end = len(expression)
    return {"start": min(starts) if starts else 0, "end": end,
            "n_tokens": len(tokens)}


# ---------------------------------------------------------------------------
# Admissibility checks performed (derived from artifact stage population).
# ---------------------------------------------------------------------------


def _admissibility_checks(artifact: Any) -> dict[str, Any]:
    """Translate compiler stage population into a checks/violations record.

    The compiler runs five stages (CompilerStage in compiler.py: lexing,
    parsing, typecheck, lowering, execution). A passing artifact has all
    five populated; a failing artifact has `valid=False` and the error
    string carries the stage tag (`stage@position: message`).
    """
    checks: list[str] = []
    violations: list[dict[str, Any]] = []

    if getattr(artifact, "tokens", None):
        checks.append("lexing")
    if getattr(artifact, "ast", None) is not None:
        checks.append("parsing")
    if getattr(artifact, "type_info", None) is not None:
        checks.append("typecheck")
    if getattr(artifact, "bytecode", None):
        checks.append("lowering")
    if getattr(artifact, "result", None) is not None:
        checks.append("execution")

    passes = bool(getattr(artifact, "valid", False))
    if not passes:
        err = getattr(artifact, "error", "") or ""
        # The compiler error format is `stage@position: message` — split.
        m = re.match(r"^([a-z]+)(?:@(\d+))?:\s*(.+)$", err, re.DOTALL)
        if m:
            stage_name, position, message = m.group(1), m.group(2), m.group(3)
            violations.append(
                {
                    "stage": stage_name,
                    "position": int(position) if position else None,
                    "message": message.strip(),
                }
            )
        else:
            violations.append({"stage": "unknown", "message": err})

    return {
        "passes": passes,
        "checks_performed": checks,
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# RPM analysis. The seed enumerator emits RPM chains as named let-bindings
# (`stageA0_*`, `stageD<k>_*`, `stageW<k>_*`, `stageP<k>_*`) connected by
# a single arrow. We also surface explicit `RPM(...)` calls when present.
# ---------------------------------------------------------------------------


_RE_RPM_STAGE = re.compile(
    r"\blet\s+(stage(?:A0|[DWP])(\d?)_[A-Za-z0-9_]+)\s*=\s*([^;]+)"
)
_RE_RPM_ARROW = re.compile(
    r"(stage(?:A0|[DWP])\d?_[A-Za-z0-9_]+)\s*(?:->|→)\s*"
    r"(stage(?:A0|[DWP])\d?_[A-Za-z0-9_]+)"
)
_RE_RPM_CALL = re.compile(r"\bRPM\(")


def _rpm_analysis(expression: str, artifact: Any) -> dict[str, Any] | None:
    has_explicit_rpm = bool(_RE_RPM_CALL.search(expression))
    stages = _RE_RPM_STAGE.findall(expression)
    arrow_match = _RE_RPM_ARROW.search(expression)
    if not has_explicit_rpm and not stages:
        return None

    chain: list[str] = []
    broken_at: str | None = None

    if stages:
        # Stage names look like stageA0_<uid>, stageD<k>_<uid>, etc. Order
        # them on the canonical capability-pathway A0 → D → W → P.
        order = {"A0": 0, "D": 1, "W": 2, "P": 3}

        def _stage_key(name: str) -> tuple[int, str]:
            m = re.match(r"stage(A0|[DWP])(\d?)_", name)
            if not m:
                return (99, name)
            label = m.group(1)
            return (order.get(label, 99), name)

        seen: list[str] = []
        for stage_name, _, _ in stages:
            if stage_name not in seen:
                seen.append(stage_name)
        seen.sort(key=_stage_key)
        chain = [_stage_label(s) for s in seen]

        # Satisfaction: chain is satisfied when the four canonical stages
        # are present (A0, D*, W*, P*) AND the visible arrow does not
        # skip a stage (A0->D / D->W / W->P are admissible single-step
        # arrows; A0->W / A0->P / D->P are skip-arrows).
        present_stage_kinds = {
            re.match(r"stage(A0|[DWP])", s).group(1)
            for s in seen
            if re.match(r"stage(A0|[DWP])", s)
        }
        all_present = present_stage_kinds >= {"A0", "D", "W", "P"}

        if arrow_match:
            src, tgt = arrow_match.group(1), arrow_match.group(2)
            src_kind = re.match(r"stage(A0|[DWP])", src).group(1)
            tgt_kind = re.match(r"stage(A0|[DWP])", tgt).group(1)
            adjacent = (
                (src_kind == "A0" and tgt_kind == "D")
                or (src_kind == "D" and tgt_kind == "W")
                or (src_kind == "W" and tgt_kind == "P")
            )
            satisfied = all_present and adjacent and bool(
                getattr(artifact, "valid", False)
            )
            if not adjacent:
                broken_at = f"{src_kind}->{tgt_kind} skip"
            elif not all_present:
                broken_at = "missing_stage"
        else:
            satisfied = all_present and bool(getattr(artifact, "valid", False))
            if not all_present:
                broken_at = "missing_stage"
    else:
        # Pure RPM(...) call. The compiler produces an RpmValue with
        # completeness ∈ [0,1]; we report satisfied iff the artifact
        # compiled and the runtime result is present.
        chain = ["RPM_call"]
        result = getattr(artifact, "result", None)
        satisfied = bool(getattr(artifact, "valid", False)) and result is not None
        if not satisfied:
            broken_at = "compilation_failed" if not getattr(artifact, "valid", False) else "no_runtime_value"

    return {
        "chain": chain,
        "satisfied": bool(satisfied),
        "broken_at": broken_at,
    }


def _stage_label(stage_var: str) -> str:
    """Translate stage variable name → canonical A0/Dn/Wn/Pn label."""
    m = re.match(r"stage(A0|[DWP])(\d?)_", stage_var)
    if not m:
        return stage_var
    kind, drive = m.group(1), m.group(2)
    if kind == "A0":
        return "A0"
    return f"{kind}{drive or ''}"


# ---------------------------------------------------------------------------
# Fractal analysis — extract Phi sequence, canonicalize, classify.
# ---------------------------------------------------------------------------


_RE_FRACTAL = re.compile(
    r"(?:Phi|Φ)\s*(?:<|⟨)\s*([0-9](?:\s*:\s*[0-9])*)\s*(?:>|⟩)"
)


def _fractal_analysis(expression: str) -> dict[str, Any] | None:
    m = _RE_FRACTAL.search(expression)
    if not m:
        return None
    raw_seq = [int(x) for x in re.split(r"\s*:\s*", m.group(1))]
    canonical = canonicalize_fractal(raw_seq)
    raw_str = "⟨" + ":".join(str(x) for x in raw_seq) + "⟩"
    canonical_str = "⟨" + ":".join(str(x) for x in canonical) + "⟩"
    convergence = classify_fractal(canonical)
    return {
        "raw": raw_str,
        "simplified": canonical_str,
        "convergence_class": convergence,
    }


# ---------------------------------------------------------------------------
# Register analysis — single, multi-register-set, or cross-register
# integration. Operator discipline (CAS v7.7 Clarification 10).
# ---------------------------------------------------------------------------


_RE_REG_SINGLE = re.compile(r"\|([TAfE])(?![a-zA-Z])")
_RE_REG_SET = re.compile(r"\|⟨([TAfE,\s]+)⟩")
_RE_OMEGA_NAME = re.compile(r"Ω_(\w+)")
_RE_TIMES_PAREN = re.compile(r"\(([^()]*)\)\s*=\s*[^=]+\|Ω_")


def _register_analysis(expression: str) -> dict[str, Any] | None:
    singles = _RE_REG_SINGLE.findall(expression)
    set_pieces: list[str] = []
    for m in _RE_REG_SET.finditer(expression):
        for p in m.group(1).split(","):
            r = p.strip()
            if r:
                set_pieces.append(r)

    if not singles and not set_pieces:
        return None

    used = sorted(set(singles) | set(set_pieces))

    has_set_notation = bool(set_pieces)
    # Cross-register integration: explicit `× ... = ... |Ω_<name>` form.
    has_cross_integration = (
        "×" in expression and "Ω_" in expression and "=" in expression
    )

    if has_cross_integration:
        single_or_multi = "cross-register-integration"
    elif has_set_notation:
        single_or_multi = "multi-register-set"
    else:
        single_or_multi = "single"

    # v7.7 operator discipline:
    # - Same-Noetic `×` between register variants requires named Ω.
    # - `+` on register variants is co-presence (always OK).
    # - `|⟨…⟩` is set-specification (always OK).
    discipline = "n_a"
    if "×" in expression:
        # Inspect the parenthesized integration: if `×` connects same
        # Noetic + same Domain register variants, an explicit `=
        # ...|Ω_name` is required.
        if has_cross_integration:
            discipline = "satisfied"
        else:
            # Cross-Noetic / cross-Domain integration is admissible
            # without Ω naming, so for non-same-Noetic uses operator
            # discipline is satisfied as well. Detect same-Noetic
            # repetition of the form `^N^D|R1 × ^N^D|R2` lacking `=
            # |Ω_`.
            same_noetic_pattern = re.search(
                r"\^(\d)(\^[PCEO])?(?:_\{F\d\})?\|[TAfE]\s*×\s*"
                r"\^\1(?:\^[PCEO])?(?:_\{F\d\})?\|[TAfE]",
                expression,
            )
            if same_noetic_pattern and "Ω_" not in expression:
                discipline = "violated"
            else:
                discipline = "satisfied"
    elif "+" in expression or has_set_notation:
        discipline = "satisfied"

    return {
        "single_or_multi": single_or_multi,
        "registers_used": used,
        "v77_operator_discipline_check": discipline,
    }


# ---------------------------------------------------------------------------
# Recipe analysis — detect Θ, parse target Ω, parse ingredient list,
# assess stoichiometric balance.
# ---------------------------------------------------------------------------


_RE_RECIPE = re.compile(
    r"(?:Θ|Theta)\s*\(\s*Ω?_?\s*(\w+)\s*\)\s*=\s*(.+?)\s*(?:→|->)\s*(.+)"
)
_RE_INGREDIENT = re.compile(
    r"([0-9]*\.?[0-9]+)\s*[\*·]\s*(\^[0-9](?:\^[PCEO])?(?:_\{F[1-7]\})?(?:\|[TAfE])?)"
)


def _recipe_analysis(expression: str) -> dict[str, Any] | None:
    if "Θ" not in expression and "Theta" not in expression:
        return None
    m = _RE_RECIPE.search(expression)
    if not m:
        return None

    target_raw = m.group(1).lstrip("_")
    # Normalize ASCII alias `Omega_<name>` to canonical `Ω_<name>` so the
    # downstream record uses the Unicode form regardless of source style.
    if target_raw.startswith("Omega_"):
        target_name = target_raw[len("Omega_"):]
        target_omega_full = f"Ω_{target_name}"
    elif target_raw.startswith("Omega"):
        # `Omega<...>` without underscore — keep as a single token.
        target_name = target_raw[len("Omega"):]
        target_omega_full = f"Ω_{target_name}" if target_name else "Ω"
    elif target_raw.startswith("Ω_"):
        target_name = target_raw[len("Ω_"):]
        target_omega_full = target_raw
    elif target_raw.startswith("Ω"):
        target_name = target_raw[len("Ω"):]
        target_omega_full = target_raw
    else:
        target_name = target_raw
        target_omega_full = f"Ω_{target_raw}"
    lhs = m.group(2)
    rhs = m.group(3)

    ingredients: list[dict[str, Any]] = []
    for im in _RE_INGREDIENT.finditer(lhs):
        coef_str, state_str = im.group(1), im.group(2)
        register = None
        reg_match = re.search(r"\|([TAfE])(?![a-zA-Z])", state_str)
        if reg_match:
            register = reg_match.group(1)
        ingredients.append(
            {
                "coefficient": float(coef_str),
                "state": state_str,
                "register": register,
            }
        )

    # Stoichiometric balance: every ingredient parsed AND the LHS Ω-name
    # equals the RHS primary Ω-name. (The CAS v7.6 leakage term Λ·Ω_*_side
    # is allowed on the RHS; we extract the primary RHS Ω-name as the
    # first match.) Accept both `Ω_<name>` and ASCII `Omega_<name>` forms
    # so recipes authored on keyboards without Greek input still balance.
    rhs_primary = re.search(r"(?:Ω_|Omega_)(\w+)", rhs)
    rhs_name = rhs_primary.group(1) if rhs_primary else None
    balanced = (
        len(ingredients) > 0
        and rhs_name is not None
        and rhs_name == target_name
    )

    return {
        "target_omega": target_omega_full,
        "ingredients": ingredients,
        "stoichiometry_balanced": balanced,
    }


# ---------------------------------------------------------------------------
# Meta-logic analysis — set/relation constructors and well-formedness.
# ---------------------------------------------------------------------------


_META_CONSTRUCTORS = (
    "NoeticCluster",
    "NoeticSet",
    "Cluster",
    "StateSet",
    "StateCluster",
    "StateVariantSet",
    "StateVariantCluster",
    "RelationSet",
    "RelationCluster",
    "DriveSet",
    "DomainSet",
    "RegisterSet",
    "FoundationSet",
    "SubFoundationSet",
    "CoverOf",
    "PartitionOf",
    "Tuple",
    "Coordinate",
    "Product",
    "Pullback",
)
_META_OPS = ("∪", "∩", "∖", "∈", "∉", "⊂", "⊆", "⊃", "⊇")


def _meta_logic_analysis(expression: str, artifact: Any) -> dict[str, Any] | None:
    constructors_used: list[str] = []
    for ctor in _META_CONSTRUCTORS:
        if re.search(rf"\b{re.escape(ctor)}\b", expression):
            constructors_used.append(ctor)
    for op in _META_OPS:
        if op in expression:
            constructors_used.append(op)

    if not constructors_used:
        return None

    well_formed = bool(getattr(artifact, "valid", False))
    return {
        "constructors_used": constructors_used,
        "well_formed": well_formed,
    }


# ---------------------------------------------------------------------------
# Trace assembly.
# ---------------------------------------------------------------------------


def build_trace(seed: dict[str, Any], artifact: Any) -> dict[str, Any] | None:
    """Build a single compile trace record from a seed + compiled artifact.

    Returns None if the seed produced an incomplete trace (missing parse
    tree on a compiler-validated seed). Such seeds are flagged for
    follow-up in the coverage report.
    """
    expression = seed["expression"]
    seed_id = seed["seed_id"]
    serialize_ast = sys.modules["cas_synthetic_path_d_trace_compiler"].serialize_ast

    if artifact.ast is None and getattr(artifact, "valid", False):
        # Compiler reported valid but no AST — incomplete; skip.
        return None

    parse_tree: dict[str, Any] = {
        "ast": serialize_ast(artifact.ast) if artifact.ast is not None else None,
        "source_position_band": _source_position_band(
            list(getattr(artifact, "tokens", []) or []), expression
        ),
    }
    summary = _ast_summary(parse_tree["ast"])

    record: dict[str, Any] = {
        "trace_id": f"trace_{seed_id}",
        "source_seed_id": seed_id,
        "expression": expression,
        "parse_tree": parse_tree,
        "ast_summary": summary,
        "admissibility": _admissibility_checks(artifact),
    }

    rpm = _rpm_analysis(expression, artifact)
    if rpm is not None:
        record["rpm_result"] = rpm

    fractal = _fractal_analysis(expression)
    if fractal is not None:
        record["fractal_canonical"] = fractal

    register = _register_analysis(expression)
    if register is not None:
        record["register_analysis"] = register

    recipe = _recipe_analysis(expression)
    if recipe is not None:
        record["recipe_analysis"] = recipe

    meta = _meta_logic_analysis(expression, artifact)
    if meta is not None:
        record["meta_logic_analysis"] = meta

    return record


# ---------------------------------------------------------------------------
# Coverage report.
# ---------------------------------------------------------------------------


def _build_coverage_report(
    traces: list[dict[str, Any]],
    seeds_by_id: dict[str, dict[str, Any]],
    incomplete_seed_ids: list[str],
    out_path: Path,
) -> None:
    n = len(traces)
    by_grammar: Counter = Counter()
    optional_field_counts: dict[str, int] = defaultdict(int)
    fractal_class_counts: Counter = Counter()
    rpm_satisfied = 0
    rpm_present = 0

    for t in traces:
        seed = seeds_by_id.get(t["source_seed_id"])
        if seed is not None:
            by_grammar[seed["grammar_category"]] += 1
        for field_name in (
            "rpm_result",
            "fractal_canonical",
            "register_analysis",
            "recipe_analysis",
            "meta_logic_analysis",
        ):
            if field_name in t and t[field_name] is not None:
                optional_field_counts[field_name] += 1
        if "fractal_canonical" in t and t["fractal_canonical"] is not None:
            fractal_class_counts[t["fractal_canonical"]["convergence_class"]] += 1
        if "rpm_result" in t and t["rpm_result"] is not None:
            rpm_present += 1
            if t["rpm_result"].get("satisfied"):
                rpm_satisfied += 1

    lines: list[str] = []
    lines.append("# Path D Wave 2F — Compile-Trace Coverage Report")
    lines.append("")
    lines.append(f"- Total traces written: **{n}**")
    lines.append(f"- Incomplete seeds (no trace produced): **{len(incomplete_seed_ids)}**")
    if seeds_by_id:
        rejection_rate = len(incomplete_seed_ids) / max(1, len(seeds_by_id))
        lines.append(f"- Rejection rate: **{rejection_rate:.2%}**")
    lines.append("")
    lines.append("## Per grammar-category trace counts")
    lines.append("")
    lines.append("| grammar_category | count |")
    lines.append("|---|---|")
    for g, count in sorted(by_grammar.items()):
        lines.append(f"| {g} | {count} |")
    lines.append("")
    lines.append("## Per optional-field population rates")
    lines.append("")
    lines.append("| optional_field | populated | rate |")
    lines.append("|---|---|---|")
    optional_fields = (
        "rpm_result",
        "fractal_canonical",
        "register_analysis",
        "recipe_analysis",
        "meta_logic_analysis",
    )
    for field_name in optional_fields:
        c = optional_field_counts.get(field_name, 0)
        rate = (c / n) if n else 0.0
        lines.append(f"| {field_name} | {c} | {rate:.2%} |")
    lines.append("")
    lines.append("## Fractal-class distribution")
    lines.append("")
    if fractal_class_counts:
        lines.append("| convergence_class | count |")
        lines.append("|---|---|")
        for cls, count in sorted(
            fractal_class_counts.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            lines.append(f"| {cls} | {count} |")
    else:
        lines.append("(no fractal traces in corpus)")
    lines.append("")
    lines.append("## RPM-satisfaction rate")
    lines.append("")
    if rpm_present:
        lines.append(
            f"- RPM-bearing traces: **{rpm_present}**"
            f" — satisfied: **{rpm_satisfied}** "
            f"({rpm_satisfied / rpm_present:.2%})"
        )
    else:
        lines.append("(no RPM traces in corpus)")
    lines.append("")
    if incomplete_seed_ids:
        lines.append("## Incomplete seeds (flag for follow-up)")
        lines.append("")
        for seed_id in incomplete_seed_ids[:50]:
            lines.append(f"- {seed_id}")
        if len(incomplete_seed_ids) > 50:
            lines.append(f"- … and {len(incomplete_seed_ids) - 50} more")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI entry point.
# ---------------------------------------------------------------------------


def _read_seeds_jsonl(path: Path) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            seeds.append(json.loads(line))
    return seeds


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Path D Wave 2F compile traces (one per seed). "
            "Trace contents: parse tree, AST summary, admissibility verdict, "
            "RPM result, fractal canonical form, register analysis, "
            "recipe analysis, meta-logic analysis."
        )
    )
    parser.add_argument(
        "--seeds",
        type=Path,
        default=Path("cas-synthetic/data/path_d/seeds.jsonl"),
        help="path to compiler-validated seeds.jsonl from Wave 1B",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("cas-synthetic/data/path_d"),
        help="output directory for compile_traces.jsonl + coverage report",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="if set, only process the first N seeds (smoke test)",
    )
    args = parser.parse_args(argv)

    compiler = _load_compiler()
    compile_expression = compiler.compile_expression

    seeds = _read_seeds_jsonl(args.seeds)
    if args.limit is not None and args.limit > 0:
        seeds = seeds[: args.limit]

    seeds_by_id: dict[str, dict[str, Any]] = {s["seed_id"]: s for s in seeds}
    traces: list[dict[str, Any]] = []
    incomplete: list[str] = []

    t0 = time.time()
    for seed in seeds:
        try:
            artifact = compile_expression(seed["expression"])
        except Exception as exc:  # pragma: no cover - defensive
            incomplete.append(seed["seed_id"])
            continue
        trace = build_trace(seed, artifact)
        if trace is None:
            incomplete.append(seed["seed_id"])
            continue
        traces.append(trace)
    elapsed = time.time() - t0

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out_dir / "compile_traces.jsonl", iter(traces))
    _build_coverage_report(
        traces, seeds_by_id, incomplete,
        out_dir / "compile_traces_coverage_report.md",
    )

    print(
        f"[generate_path_d_compile_traces] traces={len(traces)} "
        f"incomplete={len(incomplete)} "
        f"elapsed={elapsed:.1f}s",
        flush=True,
    )
    print(
        f"[generate_path_d_compile_traces] wrote "
        f"{out_dir / 'compile_traces.jsonl'} ({len(traces)} records), "
        f"{out_dir / 'compile_traces_coverage_report.md'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
