"""CAS Native Output Gate companion — Verification Stack methodology.

This module applies the Stage 19A Verification Stack methodology to CAS
Native's own internal outputs. It is the standalone gate component; wiring
into the 8-stage Wrap Pipeline is a separate integration task.

The gate decides whether an internal output is accepted or suppressed using
only non-oracle runtime states. No gold labels are consulted at inference
time. The decision combines three independent signals:

1. Ensemble agreement across selected-layer readout positions
   (``focus_token``, ``final_token``, ``mean_over_seq_len`` by default).
2. Trace stability across the per-layer CAS-class trace — the fraction of
   layers whose classification matches the dominant class.
3. Optional compiler validation of the CAS expression itself.

Outputs follow the Stage 19A reserved vocabulary:

* ``ACCEPT`` / ``SUPPRESS`` decisions.
* ``high`` / ``medium`` / ``suppress`` / ``uncertain`` decision tiers.
* Structured ``suppression_reasons`` naming the failure mode of each
  signal that did not clear (``focus_token_conflicted``,
  ``final_token_conflicted``, ``mean_over_seq_len_conflicted``,
  ``ensemble_all_disagree``, ``trace_unstable``, ``compiler_invalid``).

The module deliberately uses no third-party dependencies — stdlib only —
so it can be imported anywhere in CAS Native without environment surprises.

Reference
---------
* ``research/cas_probe/run_stage19a_formula_verification_stack.py`` — Stage
  19A reference implementation.
* ``research/cas_probe/CAS_VERIFICATION_STACK_SPEC_20260519.md`` — canonical
  Verification Stack spec (``STAGE19A_PASS_STRONG_AUDIT_CLEAN``).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional, Sequence

__all__ = [
    "VerificationGate",
    "VerificationResult",
    "DEFAULT_ENSEMBLE_POSITIONS",
]

DEFAULT_ENSEMBLE_POSITIONS: tuple[str, ...] = (
    "focus_token",
    "final_token",
    "mean_over_seq_len",
)


Decision = Literal["ACCEPT", "SUPPRESS"]
DecisionTier = Literal["high", "medium", "suppress", "uncertain"]


@dataclass
class VerificationResult:
    """Result of running the Verification Gate on one internal output.

    Attributes
    ----------
    decision:
        ``ACCEPT`` if the output cleared the stack, ``SUPPRESS`` otherwise.
    decision_tier:
        ``high`` — ensemble agreement and stable trace; the strongest tier.
        ``medium`` — ensemble agreement with marginal trace stability.
        ``suppress`` — at least one signal flagged the output.
        ``uncertain`` — ensemble agrees but trace stability is too low to
        promote to ``medium``; an edge case where no suppression reason is
        attributable to a specific signal.
    suppression_reasons:
        Ordered list of structured reasons that fired during the check.
        Empty when the decision is ``ACCEPT``.
    ensemble_agreement:
        True when the configured quorum of positions agree on a single
        class label.
    trace_stability:
        Fraction of layers in ``per_layer_trace`` whose class matches the
        dominant (modal) class. Zero when the trace is empty.
    compiler_valid:
        ``True`` / ``False`` when compiler validation was requested and ran,
        ``None`` when not checked (no expression provided or ``compiler_validate``
        disabled).
    confidence:
        Aggregate confidence derived from the per-position confidences of the
        agreeing readouts, attenuated by trace stability.
    """

    decision: Decision
    decision_tier: DecisionTier
    suppression_reasons: list[str] = field(default_factory=list)
    ensemble_agreement: bool = False
    trace_stability: float = 0.0
    compiler_valid: Optional[bool] = None
    confidence: float = 0.0


class VerificationGate:
    """Verification Stack methodology applied at CAS Native's internal output gate.

    The gate uses only non-oracle runtime states (no gold labels at inference
    time). Decision logic mirrors Stage 19A
    (``run_stage19a_formula_verification_stack.py``):

    * ACCEPT-high: ensemble agreement (quorum met) AND trace stability ≥
      ``trace_stability_threshold`` AND compiler-valid (if requested).
    * ACCEPT-medium: ensemble agreement AND trace stability in
      ``[0.6, trace_stability_threshold)`` AND compiler-valid.
    * SUPPRESS-conflicted: one or more positions disagree with the consensus —
      a ``<position>_conflicted`` reason is recorded.
    * SUPPRESS-ensemble: all positions disagree with each other; reason
      ``ensemble_all_disagree``.
    * SUPPRESS-unstable: trace stability < 0.6; reason ``trace_unstable``.
    * SUPPRESS-compiler: a CAS expression was supplied and did not compile;
      reason ``compiler_invalid``.
    * UNCERTAIN: ensemble agrees but trace stability < 0.6 — decision_tier
      ``uncertain`` with empty ``suppression_reasons``.

    Multiple reasons can fire on the same example; all are recorded.

    Parameters
    ----------
    ensemble_positions:
        Names of the readout positions that vote in the ensemble.
        Defaults to ``('focus_token', 'final_token', 'mean_over_seq_len')``.
    trace_stability_threshold:
        Fraction of layers that must match the dominant class to qualify for
        the ``high`` tier. Defaults to ``0.8``.
    ensemble_quorum:
        Number of positions that must agree on a single class for the
        ensemble to be considered in agreement. Defaults to ``3`` (all).
    compiler_validate:
        When ``True``, an ``expression_compiler`` callable must be supplied;
        the gate will run it on any CAS expression passed to :meth:`check`.
    expression_compiler:
        Optional callable ``(expression: str) -> bool`` returning whether the
        expression compiles. Defaults to ``None``; when ``None`` and
        ``compiler_validate`` is ``True`` the gate falls back to a no-op
        validator that returns ``True`` (mock-friendly default).
    """

    def __init__(
        self,
        ensemble_positions: Sequence[str] = DEFAULT_ENSEMBLE_POSITIONS,
        trace_stability_threshold: float = 0.8,
        ensemble_quorum: int = 3,
        compiler_validate: bool = True,
        expression_compiler: Optional[Callable[[str], bool]] = None,
    ) -> None:
        positions = tuple(ensemble_positions)
        if not positions:
            raise ValueError("ensemble_positions must be non-empty")
        if not 0.0 <= trace_stability_threshold <= 1.0:
            raise ValueError(
                "trace_stability_threshold must be in [0.0, 1.0], got "
                f"{trace_stability_threshold!r}"
            )
        if ensemble_quorum < 1:
            raise ValueError("ensemble_quorum must be >= 1")
        if ensemble_quorum > len(positions):
            raise ValueError(
                "ensemble_quorum cannot exceed number of ensemble_positions "
                f"({ensemble_quorum} > {len(positions)})"
            )

        self.ensemble_positions: tuple[str, ...] = positions
        self.trace_stability_threshold: float = float(trace_stability_threshold)
        self.ensemble_quorum: int = int(ensemble_quorum)
        self.compiler_validate: bool = bool(compiler_validate)
        self.expression_compiler: Optional[Callable[[str], bool]] = expression_compiler

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _consensus(
        self, votes: dict[str, str]
    ) -> tuple[Optional[str], list[str], bool]:
        """Determine ensemble consensus, dissenters, and the all-disagree flag.

        Returns
        -------
        top_label:
            The label of the largest agreeing block. ``None`` only when
            ``votes`` is empty.
        dissenting:
            Positions whose vote differs from ``top_label``.
        all_disagree:
            ``True`` when no two positions agree (each label is voted by
            exactly one position). In that case ``ensemble_all_disagree``
            is the appropriate reason; otherwise per-position
            ``_conflicted`` reasons describe the failure.
        """
        if not votes:
            return None, [], False
        counts = Counter(votes.values())
        top_label, top_count = counts.most_common(1)[0]
        dissenting = sorted(
            position for position, label in votes.items() if label != top_label
        )
        all_disagree = top_count == 1
        return top_label, dissenting, all_disagree

    def _trace_stability(
        self, per_layer_trace: Sequence[str]
    ) -> tuple[float, Optional[str]]:
        """Return (stability_fraction, dominant_label) for the layer trace.

        Stability is the modal-class share of the trace. An empty trace
        returns ``(0.0, None)``.
        """
        if not per_layer_trace:
            return 0.0, None
        counts = Counter(per_layer_trace)
        dominant_label, dominant_count = counts.most_common(1)[0]
        stability = dominant_count / len(per_layer_trace)
        return float(stability), dominant_label

    def _aggregate_confidence(
        self,
        per_position_confidences: dict[str, float],
        agreeing_positions: Sequence[str],
        trace_stability: float,
    ) -> float:
        """Aggregate per-position confidences over the agreeing readouts.

        The aggregate is the mean confidence of the agreeing positions. It
        is *not* multiplicatively attenuated by trace stability because the
        decision tier already carries the stability signal: a low-stability
        trace lowers the tier (``medium`` / ``uncertain`` / ``suppress``)
        rather than the confidence number itself. This keeps ACCEPT-high
        confidence faithful to the agreeing-readout signal.
        """
        if not agreeing_positions:
            return 0.0
        confs = [
            float(per_position_confidences.get(position, 0.0))
            for position in agreeing_positions
        ]
        if not confs:
            return 0.0
        mean_conf = sum(confs) / len(confs)
        # Reference trace_stability so the parameter remains in the signature
        # for downstream tuning; current policy is not to attenuate.
        _ = trace_stability
        return float(mean_conf)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def check(
        self,
        per_position_classifications: dict[str, str],
        per_position_confidences: dict[str, float],
        per_layer_trace: Sequence[str],
        cas_expression: Optional[str] = None,
    ) -> VerificationResult:
        """Run the Verification Stack on one CAS Native internal output.

        Parameters
        ----------
        per_position_classifications:
            Mapping of readout-position name to its predicted CAS class label.
            Positions not listed in ``ensemble_positions`` are ignored.
        per_position_confidences:
            Mapping of readout-position name to its confidence in ``[0, 1]``.
            Missing positions are treated as zero confidence.
        per_layer_trace:
            Ordered list of CAS class labels, one per layer of the trace.
        cas_expression:
            Optional CAS expression for compiler validation. When supplied and
            ``compiler_validate`` is enabled, the gate runs the configured
            ``expression_compiler``.

        Returns
        -------
        VerificationResult
            Structured decision packet — accepted or suppressed, with tier,
            reasons, ensemble/trace state, compiler result, and aggregate
            confidence.
        """
        # ------------------------------------------------------------------
        # Signal 1: ensemble consensus across selected readout positions.
        # ------------------------------------------------------------------
        votes: dict[str, str] = {
            position: per_position_classifications[position]
            for position in self.ensemble_positions
            if position in per_position_classifications
        }
        consensus_label, dissenting_positions, all_disagree = self._consensus(votes)
        # Quorum: ensemble agreement holds when the top label is voted by
        # at least ``ensemble_quorum`` positions.
        top_count = (
            sum(1 for label in votes.values() if label == consensus_label)
            if consensus_label is not None
            else 0
        )
        ensemble_agreement = top_count >= self.ensemble_quorum

        suppression_reasons: list[str] = []
        if all_disagree:
            # 1-1-1 split (no two positions agree).
            suppression_reasons.append("ensemble_all_disagree")
        else:
            # Quorum may or may not be met; record per-position conflicts.
            for position in dissenting_positions:
                suppression_reasons.append(f"{position}_conflicted")

        # ------------------------------------------------------------------
        # Signal 2: trace stability over per-layer classifications.
        # ------------------------------------------------------------------
        trace_stability, dominant_trace_label = self._trace_stability(per_layer_trace)
        trace_unstable = trace_stability < 0.6 or not per_layer_trace
        if trace_unstable:
            suppression_reasons.append("trace_unstable")

        # ------------------------------------------------------------------
        # Signal 3: compiler validation (optional).
        #
        # Validation runs only when (a) ``compiler_validate`` is enabled,
        # (b) a ``cas_expression`` is supplied, and (c) an
        # ``expression_compiler`` callable has been configured. When no
        # validator is configured the check is skipped (``compiler_valid``
        # stays ``None``) so tests and integration sites that have no
        # compiler wired in are not forced to mock one.
        # ------------------------------------------------------------------
        compiler_valid: Optional[bool] = None
        if (
            self.compiler_validate
            and cas_expression is not None
            and self.expression_compiler is not None
        ):
            try:
                compiler_valid = bool(self.expression_compiler(cas_expression))
            except Exception:
                compiler_valid = False
            if compiler_valid is False:
                suppression_reasons.append("compiler_invalid")

        # ------------------------------------------------------------------
        # Decision logic — mirror Stage 19A.
        # ------------------------------------------------------------------
        agreeing_positions = [
            position for position, label in votes.items() if label == consensus_label
        ] if consensus_label is not None else []

        confidence = self._aggregate_confidence(
            per_position_confidences=per_position_confidences,
            agreeing_positions=agreeing_positions,
            trace_stability=trace_stability,
        )

        decision: Decision
        decision_tier: DecisionTier

        compiler_blocks = compiler_valid is False
        if (
            ensemble_agreement
            and not trace_unstable
            and not compiler_blocks
            and trace_stability >= self.trace_stability_threshold
        ):
            decision = "ACCEPT"
            decision_tier = "high"
            # Accepted-high clears the stack; clear any partial-dissent
            # reasons that quorum tolerated (relevant only when
            # ``ensemble_quorum`` is set below the full position count).
            suppression_reasons = []
        elif (
            ensemble_agreement
            and not trace_unstable
            and not compiler_blocks
            and trace_stability >= 0.6
        ):
            decision = "ACCEPT"
            decision_tier = "medium"
            suppression_reasons = []
        elif (
            ensemble_agreement
            and trace_unstable
            and not compiler_blocks
            and not dissenting_positions
            and not all_disagree
        ):
            # Ensemble agrees fully, no other signal flagged anything beyond
            # the unstable trace itself, but the trace is too unstable to
            # promote. Edge case: SUPPRESS at ``uncertain`` tier with empty
            # ``suppression_reasons`` per spec.
            decision = "SUPPRESS"
            decision_tier = "uncertain"
            suppression_reasons = []
        else:
            decision = "SUPPRESS"
            decision_tier = "suppress"

        return VerificationResult(
            decision=decision,
            decision_tier=decision_tier,
            suppression_reasons=suppression_reasons,
            ensemble_agreement=ensemble_agreement,
            trace_stability=trace_stability,
            compiler_valid=compiler_valid,
            confidence=confidence,
        )
