"""RPM (Roadmap of Prerequisites for Manifestation) gate for CABS.

The RPM chain in the wider CAS framework is ``A0 → Dn → Wn → Pn → Outcome``.
For the v1 belief substrate we encode a pragmatic, parser-grounded version of
that chain: a claim's RPM is satisfied when

1. **A0 — Pure Desire (input is willing).** At least one prior observation
   exists. Without an observation there is no desire to anchor the chain.
2. **Dn — Desire-shaped (input is well-formed).** The CAS expression compiles
   cleanly via ``api.notation.compile_expression``. A non-compiling expression
   has no admissible source.
3. **Wn — Will-shaped (input is admissible).** The compiler's typecheck and
   admissibility pass produced no error. We treat ``valid==True`` as the
   admissibility witness in v1; the existing ``cas-engine`` admissibility
   relations (CORRECTION 1) are surfaced through the same compiler.
4. **Pn → claim — Production-shaped.** Reaching this point is the production
   step; the claim survives the gate.

Section-retraction (CORRECTION 2): once an RPM gate clears, we cache the result
on the belief. The gate is idempotent in the forward direction
(``ε ∘ η = id``). Re-entering the gate after a contradiction must recompute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.notation import compile_expression


@dataclass
class RPMResult:
    """Outcome of one RPM gate evaluation.

    `satisfied` is the AND of all four prerequisite stages. `status` carries a
    per-stage breakdown so the REPL ``/why`` command can show exactly which
    stage blocked.
    """

    satisfied: bool
    status: dict[str, Any]


def check_rpm_chain(
    claim_text: str,
    cas_expression: str,
    prior_observation_count: int,
) -> RPMResult:
    """Walk A0 → Dn → Wn → Pn for a claim under v1 semantics.

    Parameters
    ----------
    claim_text:
        Human-readable claim (used for diagnostics; not used in gate logic).
    cas_expression:
        The CAS expression to validate via the compiler.
    prior_observation_count:
        How many observations have been recorded for the claim, including the
        current one. The A0 stage requires this to be >= 1.

    Returns
    -------
    RPMResult
        ``satisfied`` is True iff every stage passed. ``status`` includes a
        ``stages`` dict mapping each of {``A0``, ``Dn``, ``Wn``, ``Pn``} to a
        dict with ``passed`` and a ``reason`` string, plus aggregated keys
        ``compiler_valid``, ``compiler_error``, ``observations``.
    """
    stages: dict[str, dict[str, Any]] = {}

    # A0 — Pure Desire. At least one observation must exist.
    a0_pass = prior_observation_count >= 1
    stages["A0"] = {
        "passed": a0_pass,
        "reason": (
            "at least one prior observation exists"
            if a0_pass
            else "no observations recorded yet"
        ),
        "observations": prior_observation_count,
    }

    # Dn — Desire-shaped. Compile the expression.
    if not cas_expression:
        compile_artifact = None
        compiler_valid = False
        compiler_error = "empty cas_expression"
    else:
        try:
            compile_artifact = compile_expression(cas_expression)
            compiler_valid = compile_artifact.valid
            compiler_error = compile_artifact.error
        except Exception as exc:  # pragma: no cover - compiler hardening
            compile_artifact = None
            compiler_valid = False
            compiler_error = f"compiler raised: {exc!r}"

    dn_pass = bool(compiler_valid)
    stages["Dn"] = {
        "passed": dn_pass,
        "reason": (
            "expression compiles cleanly"
            if dn_pass
            else f"compiler rejected expression: {compiler_error!r}"
        ),
    }

    # Wn — Will-shaped. v1: same as Dn (compiler subsumes admissibility).
    # We surface this as a separate stage so future versions can plug in the
    # cas-engine admissibility relation here without changing the public API.
    wn_pass = dn_pass and (
        compile_artifact is not None and not compile_artifact.warnings
    )
    if not dn_pass:
        wn_reason = "blocked by Dn"
    elif compile_artifact is not None and compile_artifact.warnings:
        wn_reason = (
            f"compiler emitted warnings: {compile_artifact.warnings!r}"
        )
    else:
        wn_reason = "admissibility relation cleared (compiler typecheck)"
    stages["Wn"] = {"passed": wn_pass, "reason": wn_reason}

    # Pn — Production. If the upstream stages all passed, the claim is allowed
    # through. We record the type kind for the trace.
    pn_pass = a0_pass and dn_pass and wn_pass
    if pn_pass and compile_artifact is not None and compile_artifact.type_info is not None:
        pn_reason = (
            "production cleared; "
            f"type={compile_artifact.type_info.kind.value}"
        )
    elif pn_pass:
        pn_reason = "production cleared"
    else:
        failed = [k for k, v in stages.items() if not v["passed"]]
        pn_reason = f"production blocked by upstream stage(s): {failed}"
    stages["Pn"] = {"passed": pn_pass, "reason": pn_reason}

    status: dict[str, Any] = {
        "stages": stages,
        "compiler_valid": compiler_valid,
        "compiler_error": compiler_error,
        "observations": prior_observation_count,
    }
    return RPMResult(satisfied=pn_pass, status=status)
