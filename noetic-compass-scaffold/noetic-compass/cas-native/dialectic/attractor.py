"""Attractor data class plus CAS-native scoring rubric.

Each rotation produces an ``Attractor`` -- a candidate Omega that the
``(A x B)`` integration of the two CAS-Native instances landed on. The
rubric scores the attractor on four CAS-native quality signals:

- substance       (structural richness, non-degeneracy)
- relevance       (axis matches between query CAS-content and attractor)
- admissibility   (does the integrated expression compile)
- invariant_balance (involution distance, domain precedence, etc.)

The rubric is heuristic-with-real-bones: ``admissibility`` calls the
real ``api.notation.compile_expression`` so it lights up whenever the
attractor expression is well-formed CAS. ``invariant_balance`` uses a
small set of structural checks. ``substance`` and ``relevance`` are
intentionally heuristic for now -- a learned scorer will replace them
post-Lever-3.

The composite score is a weighted sum with weights chosen to favour
admissibility and structural balance over substance volume; this
biases the scaffold against the failure mode where a lush but malformed
expression beats a clean but spare one. Weights are exposed in
``DEFAULT_WEIGHTS`` so the rubric can be re-tuned without code edits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# --------------------------------------------------------------------------
# Composite weights (exported for tuning)
# --------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    # Structural correctness > volume. Admissibility leads.
    "admissibility": 0.35,
    "invariant_balance": 0.25,
    "relevance": 0.25,
    "substance": 0.15,
}


# --------------------------------------------------------------------------
# Attractor + score dataclasses
# --------------------------------------------------------------------------

@dataclass
class Attractor:
    """Candidate Omega from one rotation's ``(A x B)`` integration.

    Fields:
        rotation_label: short human-readable label, e.g. "^2 vs ^3".
        instance_a_prediction: full prediction dict from instance A.
        instance_b_prediction: full prediction dict from instance B.
        integrated_expression: CAS expression string for the integrated
            attractor. Format depends on ``integration_kind``.
        integration_kind: one of {"co_presence", "integration",
            "set_spec", "fallback"}.
            - "co_presence": A and B are distinct compatible states
              joined with ``+``.
            - "integration": A and B fuse into a named ``Omega`` with
              ``x``.
            - "set_spec": A and B share a state but differ only in
              register; rendered as register-set ``|<...>``.
            - "fallback": no clean integration; the higher-confidence
              prediction wins, expression is just A's.
        metadata: free-form dict. Holds, e.g., the AxisPriming labels,
            timing, instance notes.
    """

    rotation_label: str
    instance_a_prediction: dict[str, Any]
    instance_b_prediction: dict[str, Any]
    integrated_expression: str
    integration_kind: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rotation_label": self.rotation_label,
            "instance_a_prediction": dict(self.instance_a_prediction),
            "instance_b_prediction": dict(self.instance_b_prediction),
            "integrated_expression": self.integrated_expression,
            "integration_kind": self.integration_kind,
            "metadata": dict(self.metadata),
        }


@dataclass
class AttractorScore:
    """Quality scores for an attractor. All in [0, 1] except composite
    which is also in [0, 1] given normalised weights."""

    substance: float
    relevance: float
    admissibility: float
    invariant_balance: float
    composite: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "substance": round(self.substance, 4),
            "relevance": round(self.relevance, 4),
            "admissibility": round(self.admissibility, 4),
            "invariant_balance": round(self.invariant_balance, 4),
            "composite": round(self.composite, 4),
            "notes": list(self.notes),
        }


# --------------------------------------------------------------------------
# Building an Attractor from two predictions
# --------------------------------------------------------------------------

def _safe_render_expression(prediction: dict[str, Any]) -> str:
    """Render a prediction dict to a CAS expression string. Best-effort."""
    try:
        from cas_native.inference.cas_renderer import render_cas_expression_string
    except Exception:
        return "<render-unavailable>"
    try:
        return render_cas_expression_string(prediction)
    except Exception as exc:
        return f"<render-failed: {exc!s}>"


def integrate_predictions(
    rotation_label: str,
    a_prediction: dict[str, Any],
    b_prediction: dict[str, Any],
    *,
    metadata: Optional[dict[str, Any]] = None,
) -> Attractor:
    """Build a candidate Attractor from instance A and B predictions.

    Integration policy (deliberately conservative -- per CLAUDE.md
    Clarification 10, ``x`` requires an emergent result; ``+`` requires
    structurally distinct co-presents; ``|<...>`` is the right choice
    when only registers differ).

    Decision procedure (mirrors Clarification 10 Section 6):
        1. If A and B share Noetic, Domain, Drive but only Registers
           differ -> ``set_spec``. Render as ``^N^D_{F}|<R_a, R_b>``.
        2. If A and B differ in Noetic / Domain / Drive (different
           states), the rotation produced two distinct candidate states.
           We render the canonical co-presence ``A + B``.
        3. If A == B exactly, the rotation is degenerate -- there is no
           meaningful integration. We mark integration_kind="fallback"
           and use A's expression.

    Note: we do NOT emit ``x``-form integration here. Doing so requires
    an explicit named emergent result, which the heuristic policy can't
    fabricate. ``x``-form attractors are produced only when the
    underlying predictor explicitly emits ``register_mode="integration"``
    with ``has_omega=True``; the `(... x ...) = ^N^D|Omega` rendering is
    handled inside cas_renderer and shows up in ``integrated_expression``
    for the relevant single-instance prediction. This scaffold prefers
    underclaiming integration to overclaiming it.
    """

    # Equality test: structurally identical predictions.
    if _predictions_equal(a_prediction, b_prediction):
        expr = _safe_render_expression(a_prediction)
        return Attractor(
            rotation_label=rotation_label,
            instance_a_prediction=a_prediction,
            instance_b_prediction=b_prediction,
            integrated_expression=expr,
            integration_kind="fallback",
            metadata={"reason": "instances_agreed", **(metadata or {})},
        )

    # Same state, different registers -> set_spec.
    if _same_state_modulo_registers(a_prediction, b_prediction):
        regs_a = tuple(a_prediction.get("registers") or ())
        regs_b = tuple(b_prediction.get("registers") or ())
        # Union (order-preserved) of registers.
        joined: list[str] = []
        for r in list(regs_a) + list(regs_b):
            if r not in joined:
                joined.append(r)
        n = a_prediction.get("noetic", 0)
        d = a_prediction.get("domain", "P")
        f = a_prediction.get("drive", "F1")
        if joined:
            spec_expr = f"^{n}^{d}_{{{f}}}|<" + ",".join(joined) + ">"
        else:
            spec_expr = f"^{n}^{d}_{{{f}}}"
        return Attractor(
            rotation_label=rotation_label,
            instance_a_prediction=a_prediction,
            instance_b_prediction=b_prediction,
            integrated_expression=spec_expr,
            integration_kind="set_spec",
            metadata={"reason": "registers_differ_only", **(metadata or {})},
        )

    # Different states -> co-presence.
    expr_a = _safe_render_expression(a_prediction)
    expr_b = _safe_render_expression(b_prediction)
    co_expr = f"({expr_a}) + ({expr_b})"
    return Attractor(
        rotation_label=rotation_label,
        instance_a_prediction=a_prediction,
        instance_b_prediction=b_prediction,
        integrated_expression=co_expr,
        integration_kind="co_presence",
        metadata={"reason": "distinct_states", **(metadata or {})},
    )


def _predictions_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Cheap structural equality for prediction dicts."""
    keys = (
        "noetic",
        "domain",
        "drive",
        "register_mode",
        "expression_family",
        "transition_kind",
        "authority",
        "has_omega",
        "has_meta_logic",
    )
    for k in keys:
        if a.get(k) != b.get(k):
            return False
    if tuple(a.get("registers") or ()) != tuple(b.get("registers") or ()):
        return False
    if tuple(a.get("meta_relations") or ()) != tuple(b.get("meta_relations") or ()):
        return False
    return True


def _same_state_modulo_registers(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """True iff Noetic/Domain/Drive match but registers differ."""
    if a.get("noetic") != b.get("noetic"):
        return False
    if a.get("domain") != b.get("domain"):
        return False
    if a.get("drive") != b.get("drive"):
        return False
    return tuple(a.get("registers") or ()) != tuple(b.get("registers") or ())


# --------------------------------------------------------------------------
# Scoring components
# --------------------------------------------------------------------------

def _score_substance(attractor: Attractor) -> tuple[float, list[str]]:
    """Heuristic substance score in [0, 1].

    Ingredients:
      - +0.30 for a non-trivial integration_kind (not "fallback").
      - +0.10 per CAS axis specified in either prediction (Noetic always
              counts, Domain/Drive/Register count if non-default), capped
              at +0.40 total.
      - +0.10 if the integrated expression is non-empty / non-error.
      - +0.10 if the registers list has >= 2 distinct registers across
              A and B (richer co-presence / set_spec attractor).
      - +0.10 if has_omega or has_meta_logic on either side (compound
              structural payload).

    Capped at 1.0. We do NOT linearly reward expression length -- that
    would just inflate any compound expression. The cap also prevents
    "stuffing" -- the user's note in the proposal.
    """
    score = 0.0
    notes: list[str] = []

    if attractor.integration_kind != "fallback":
        score += 0.30
        notes.append("integration_kind_nontrivial+0.30")

    axes = 0
    a = attractor.instance_a_prediction
    b = attractor.instance_b_prediction
    if a.get("noetic") is not None:
        axes += 1
    if a.get("domain"):
        axes += 1
    if a.get("drive"):
        axes += 1
    if a.get("registers"):
        axes += 1
    axes_score = min(0.10 * axes, 0.40)
    score += axes_score
    notes.append(f"axes_specified+{axes_score:.2f}")

    if attractor.integrated_expression and not attractor.integrated_expression.startswith("<"):
        score += 0.10
        notes.append("expr_renderable+0.10")

    distinct_regs = set(a.get("registers") or ()) | set(b.get("registers") or ())
    if len(distinct_regs) >= 2:
        score += 0.10
        notes.append(f"distinct_registers={len(distinct_regs)}+0.10")

    has_omega = bool(a.get("has_omega") or b.get("has_omega"))
    has_meta = bool(a.get("has_meta_logic") or b.get("has_meta_logic"))
    if has_omega or has_meta:
        score += 0.10
        notes.append("compound_payload+0.10")

    return min(score, 1.0), notes


def _score_relevance(attractor: Attractor, query_text: str) -> tuple[float, list[str]]:
    """Heuristic relevance score in [0, 1] using rewrite_shim signal.

    Counts axis matches between the query's detected CAS signal and the
    attractor's predictions. Each match adds 0.25 (up to 1.0).
    """
    notes: list[str] = []
    try:
        from cas_native.inference.rewrite_shim import detect_cas_signal
    except Exception:
        notes.append("rewrite_shim_unavailable")
        return 0.0, notes

    signal = detect_cas_signal(query_text or "")
    if not signal.get("has_signal"):
        notes.append("query_no_signal")
        return 0.0, notes

    score = 0.0
    a = attractor.instance_a_prediction
    b = attractor.instance_b_prediction

    q_noetic = signal.get("noetic")
    if q_noetic is not None and (
        str(a.get("noetic")) == str(q_noetic)
        or str(b.get("noetic")) == str(q_noetic)
    ):
        score += 0.25
        notes.append(f"noetic_match=^{q_noetic}+0.25")

    q_domain = signal.get("domain")
    if q_domain is not None and (
        a.get("domain") == q_domain or b.get("domain") == q_domain
    ):
        score += 0.25
        notes.append(f"domain_match=^{q_domain}+0.25")

    q_drive = signal.get("drive")
    if q_drive is not None and (
        a.get("drive") == q_drive or b.get("drive") == q_drive
    ):
        score += 0.25
        notes.append(f"drive_match={q_drive}+0.25")

    q_register = signal.get("register")
    if q_register is not None:
        regs = set(a.get("registers") or ()) | set(b.get("registers") or ())
        if q_register in regs:
            score += 0.25
            notes.append(f"register_match=|{q_register}+0.25")

    return min(score, 1.0), notes


def _score_admissibility(attractor: Attractor) -> tuple[float, list[str]]:
    """Try to compile the integrated expression. 1.0 if compiles, else 0.0.

    Compilation here is a hard binary signal: does the CAS compiler
    accept the expression. The composite weight balances this against
    the heuristic pieces. The set_spec angle-bracket form
    (``|<R1,R2>``) is currently NOT in the CAS compiler grammar -- this
    is a known limitation, and set_spec attractors will register
    admissibility=0 even when structurally clean. The note records this
    so the diagnostic trace is honest.
    """
    notes: list[str] = []
    expr = attractor.integrated_expression
    if not expr or expr.startswith("<"):
        notes.append("expression_unrenderable->0.0")
        return 0.0, notes

    try:
        from api.notation import compile_expression
    except Exception as exc:
        notes.append(f"compiler_unavailable:{exc!s}->0.0")
        return 0.0, notes

    # Co-presence form ``(expr_a) + (expr_b)`` is what we emit; the CAS
    # compiler accepts ``A + B`` directly without the parens, so try
    # both forms before giving up.
    candidates = [expr]
    if expr.startswith("(") and ") + (" in expr:
        # Strip paren-wrapping when both sides are simple state expressions.
        inner = expr.strip()
        try:
            mid = inner.index(") + (")
            left = inner[1:mid]
            right = inner[mid + 5: -1]
            candidates.append(f"{left} + {right}")
        except ValueError:
            pass

    last_err: Optional[str] = None
    for candidate in candidates:
        try:
            artifact = compile_expression(candidate)
        except Exception as exc:
            last_err = f"compile_raised:{exc!s}"
            continue
        if getattr(artifact, "valid", False):
            notes.append(f"compiled_ok:{candidate!r}->1.0")
            return 1.0, notes
        last_err = getattr(artifact, "error", "compile_invalid")

    notes.append(f"compile_failed:{last_err}->0.0")
    if attractor.integration_kind == "set_spec":
        notes.append("note: set_spec |<...> form not yet in compiler grammar")
    return 0.0, notes


def _score_invariant_balance(attractor: Attractor) -> tuple[float, list[str]]:
    """Structural-invariant respect: involution / domain precedence / drive pairs.

    Checks (each contributes 0.25 of the total, max 1.0):

      1. Involution distance: if A and B sit on a Noetic involution pair
         ((^2,^3), (^5,^6), (^8,^9)) we award full weight; if they are on
         the same Noetic we award full weight (no involution stress); if
         they are at unrelated Noetics we award 0.10 (it is a co-presence,
         not an involution-collapse, but it is also not a clean opposition).

      2. Domain precedence: P > C > E > O. If A.domain and B.domain are
         neighbours in the precedence chain or identical, full credit.
         If they jump (e.g. P and O), partial credit (0.10) -- this is
         legitimate but structurally riskier per Domain Descent.

      3. Drive inversion: if A.drive and B.drive are an inversion pair
         ((F1,F7),(F2,F6),(F3,F5)) or identical, full credit. F4 is
         self-dual. Otherwise partial credit (0.10).

      4. Register-mode coherence: if both predictions agree on
         register_mode, full credit. Otherwise partial credit (0.10).
    """
    INVOLUTION_PAIRS = {(2, 3), (3, 2), (5, 6), (6, 5), (8, 9), (9, 8)}
    DRIVE_PAIRS = {
        ("F1", "F7"), ("F7", "F1"),
        ("F2", "F6"), ("F6", "F2"),
        ("F3", "F5"), ("F5", "F3"),
    }
    DOMAIN_ORDER = {"P": 0, "C": 1, "E": 2, "O": 3}

    a = attractor.instance_a_prediction
    b = attractor.instance_b_prediction
    score = 0.0
    notes: list[str] = []

    n_a, n_b = a.get("noetic"), b.get("noetic")
    try:
        n_a_i = int(n_a) if n_a is not None else None
        n_b_i = int(n_b) if n_b is not None else None
    except (TypeError, ValueError):
        n_a_i, n_b_i = None, None

    if n_a_i is not None and n_b_i is not None:
        if n_a_i == n_b_i or (n_a_i, n_b_i) in INVOLUTION_PAIRS:
            score += 0.25
            notes.append("noetic_clean_involution+0.25")
        else:
            score += 0.10
            notes.append("noetic_unrelated+0.10")
    else:
        notes.append("noetic_missing+0.00")

    d_a, d_b = a.get("domain"), b.get("domain")
    if d_a in DOMAIN_ORDER and d_b in DOMAIN_ORDER:
        diff = abs(DOMAIN_ORDER[d_a] - DOMAIN_ORDER[d_b])
        if diff <= 1:
            score += 0.25
            notes.append(f"domain_diff={diff}+0.25")
        else:
            score += 0.10
            notes.append(f"domain_jump={diff}+0.10")
    else:
        notes.append("domain_missing+0.00")

    f_a, f_b = a.get("drive"), b.get("drive")
    if f_a == f_b or f_a == "F4" or f_b == "F4":
        score += 0.25
        notes.append("drive_self_dual_or_match+0.25")
    elif (f_a, f_b) in DRIVE_PAIRS:
        score += 0.25
        notes.append("drive_inversion_pair+0.25")
    else:
        score += 0.10
        notes.append("drive_unrelated+0.10")

    rm_a, rm_b = a.get("register_mode"), b.get("register_mode")
    if rm_a == rm_b:
        score += 0.25
        notes.append("register_mode_match+0.25")
    else:
        score += 0.10
        notes.append("register_mode_diverge+0.10")

    return min(score, 1.0), notes


# --------------------------------------------------------------------------
# Top-level scoring
# --------------------------------------------------------------------------

def score_attractor(
    attractor: Attractor,
    query_text: str,
    *,
    weights: Optional[dict[str, float]] = None,
) -> AttractorScore:
    """Score a candidate Attractor against a query.

    All four sub-scores are in [0, 1]. The composite is the
    weighted sum of the sub-scores using DEFAULT_WEIGHTS unless an
    explicit ``weights`` dict is provided. Weights need not sum to 1.0 --
    they are normalised internally so the composite stays in [0, 1].
    """
    if not isinstance(attractor, Attractor):
        raise TypeError(f"attractor must be Attractor, got {type(attractor).__name__}")

    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    total_w = sum(w.values()) or 1.0
    w = {k: v / total_w for k, v in w.items()}

    substance, sub_notes = _score_substance(attractor)
    relevance, rel_notes = _score_relevance(attractor, query_text)
    admissibility, adm_notes = _score_admissibility(attractor)
    balance, bal_notes = _score_invariant_balance(attractor)

    composite = (
        substance * w["substance"]
        + relevance * w["relevance"]
        + admissibility * w["admissibility"]
        + balance * w["invariant_balance"]
    )

    notes: list[str] = []
    notes.extend(f"substance:{n}" for n in sub_notes)
    notes.extend(f"relevance:{n}" for n in rel_notes)
    notes.extend(f"admissibility:{n}" for n in adm_notes)
    notes.extend(f"balance:{n}" for n in bal_notes)
    notes.append(
        f"weights={{adm:{w['admissibility']:.2f},"
        f"bal:{w['invariant_balance']:.2f},"
        f"rel:{w['relevance']:.2f},"
        f"sub:{w['substance']:.2f}}}"
    )

    return AttractorScore(
        substance=substance,
        relevance=relevance,
        admissibility=admissibility,
        invariant_balance=balance,
        composite=composite,
        notes=notes,
    )


__all__ = [
    "Attractor",
    "AttractorScore",
    "DEFAULT_WEIGHTS",
    "integrate_predictions",
    "score_attractor",
]
