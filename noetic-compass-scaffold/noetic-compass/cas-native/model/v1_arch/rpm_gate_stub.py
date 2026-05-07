"""RPMGateStub — Path C-1 stub.

Returns a Boolean per ``(state_prev, transition_op, state_next)`` triple
indicating whether the transition is admissible. C-1 is intentionally a
STUB: it reads the compiler's existing ``_is_admissible`` table for
operator-driven state transitions and falls back to a small hardcoded
table for the few op kinds the compiler doesn't directly expose.

Path C §3.3 phasing:

    C1: RPM stub — Boolean only, scalar gate evidence.
    C2-C4: build out drive intensity / register / meta-logic proofs.
    C5: RPM uses meta-logic proofs as gate evidence (instead of scalar).

This module implements C1 only. Do NOT extend it to consume meta-logic
proofs — that work belongs in a different module that ships in C5.
The existing legacy module ``cas_native.model.rpm_gate`` is the
neural soft-gate per-layer satisfaction signal; this stub is a
distinct, structural Boolean check.

Design constraints
------------------

- Reads the compiler's ``_is_admissible`` function (load-bearing
  reuse — DO NOT reimplement the Cognitive Operator admissibility
  table here). The compiler is the single source of truth.
- Forward signature::

      result = stub(p_state_prev, p_state_next, transition_op)

  where:
      - ``p_state_prev`` and ``p_state_next`` are ``(B, 40)`` simplex
        distributions; we read the dominant (argmax) atom of each as
        the structural source/target.
      - ``transition_op`` is either:
            - an int CO id in [0, 9] (see CAS Correction 1), OR
            - a string from :data:`TRANSITION_OPS` (a hardcoded enum
              of compositional ops the C-1 stub recognises),
            - or a ``(B,)`` long tensor / list of per-example op ids.
- Returns a :class:`RPMGateResult` carrying the Boolean ``passed``
  flag, a ``broken_at`` diagnostic string when ``False``, and an
  ``evidence`` dict including the dominant-atom indices and the
  compiler's verdict.

No gradient flows through this module. It is a forward-only structural
check used for trace and refusal evidence, not for backprop. C-2/C-3
will keep this contract — gate evidence is a discrete Boolean, the
soft-gate satisfaction stays in the neural rpm_gate module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Union

import torch
import torch.nn as nn


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hardcoded fallback transition-op table.
# ---------------------------------------------------------------------------
#
# The compiler's ``_is_admissible`` function takes a Cognitive Operator
# id (CO-0 through CO-9) plus a source/target index in [0, 40). For the
# C-1 stub we additionally recognise a small set of compositional op
# names from the CAS notation (``+``, ``×``, ``∘``, ``→``, etc.). For
# those, the C-1 contract is:
#
#     - ``"identity"``: passed iff source == target.
#     - ``"any"``      : passed unconditionally (test-fixture escape
#                        hatch; do NOT use in production).
#     - the rest      : delegated to the per-CO admissibility table
#                        with the operator id mapped via the table
#                        below.
#
# The op-name → CO mapping is a *coarse approximation* fit for a STUB.
# Full multi-op admissibility lives in C-5.
TRANSITION_OPS: tuple[str, ...] = (
    "identity",   # CO-0 (diagonal only)
    "positive",   # CO-2
    "negative",   # CO-3
    "vibration",  # CO-4
    "female",     # CO-5
    "male",       # CO-6
    "rhythm",     # CO-7
    "cause",      # CO-8
    "effect",     # CO-9
    "any",        # test-fixture escape hatch
)

_OP_TO_CO: dict[str, int] = {
    "identity": 0,
    "mind": 1,
    "positive": 2,
    "negative": 3,
    "vibration": 4,
    "female": 5,
    "male": 6,
    "rhythm": 7,
    "cause": 8,
    "above": 8,
    "effect": 9,
    "below": 9,
}


# ---------------------------------------------------------------------------
# Compiler hook (with safe fallback)
# ---------------------------------------------------------------------------


def _load_compiler_admissibility():
    """Return the compiler's ``_is_admissible`` function or a fallback.

    The compiler at ``api/notation/compiler.py`` is the single source
    of truth for Cognitive Operator admissibility. We import lazily so
    the stub remains usable in environments where the compiler can't
    be imported (e.g. minimal model-only test runs).

    Fallback is the same heuristic the compiler uses when its own
    Rust ``cas_engine`` binding is unavailable:

        - operator 0 (identity): source == target.
        - else: same domain (``// 10``) OR target is the operator
          (``% 10 == operator``).
    """
    try:  # pragma: no cover — import-time only
        from api.notation.compiler import _is_admissible as compiler_is_admissible

        return compiler_is_admissible
    except Exception as exc:  # pragma: no cover - logged then fallback
        logger.debug(
            "RPMGateStub: compiler import failed (%s); using fallback "
            "admissibility heuristic.",
            exc,
        )

        def _fallback(operator: int, source_index: int, target_index: int) -> bool:
            if operator == 0:
                return source_index == target_index
            return (source_index // 10) == (target_index // 10) or (
                target_index % 10
            ) == operator

        return _fallback


_IS_ADMISSIBLE = _load_compiler_admissibility()


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class RPMGateResult:
    """Outcome of one RPM stub check.

    Attributes
    ----------
    passed:
        ``(B,)`` boolean tensor — True iff the structural transition
        is admissible according to the compiler's table (or the C-1
        fallback heuristic).
    broken_at:
        Per-batch list of strings. ``None`` for samples where the gate
        passed; otherwise a short diagnostic of the form
        ``"<source_label> -> <op_name> -> <target_label> not in D_op"``.
    evidence:
        Dict of structural evidence used to make the decision::

            {
                "source_index": (B,) int — argmax of p_state_prev,
                "target_index": (B,) int — argmax of p_state_next,
                "operator_id":  (B,) int — CO id used for the check,
                "op_name":      (B,) list[str] — the op-name string,
            }

    Notes
    -----
    The dataclass is consumed by the test suite and by V1ArchModel's
    forward return dict. ``passed`` is a tensor (not a scalar) so the
    rest of the pipeline can broadcast it cleanly across the batch
    dimension.
    """

    passed: torch.Tensor
    broken_at: list[Optional[str]] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    def __bool__(self) -> bool:
        # Convenience for single-example scalar use only.
        if self.passed.numel() == 1:
            return bool(self.passed.item())
        raise ValueError(
            "RPMGateResult.__bool__ called on a batch result; index a "
            "specific element (`result.passed[i].item()`) instead."
        )


# ---------------------------------------------------------------------------
# Stub module
# ---------------------------------------------------------------------------


_STATE_LABELS: tuple[str, ...] = tuple(
    f"^{n}^{d}" for d in "PCEO" for n in range(10)
)


class RPMGateStub(nn.Module):
    """C-1 RPM gate stub.

    Boolean per ``(p_state_prev, p_state_next, transition_op)`` whether
    the structural transition is admissible. Reads the compiler's
    ``_is_admissible`` table; emits ``passed`` and ``broken_at`` for
    Mode 7 trace.
    """

    def __init__(self) -> None:
        super().__init__()
        # No learnable parameters — this is a structural check.

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_op(
        transition_op: Union[int, str, Sequence[Union[int, str]], torch.Tensor],
        batch_size: int,
    ) -> tuple[list[int], list[str]]:
        """Normalize the per-example operator argument.

        Returns:
            (op_ids, op_names) — both length-batch_size lists.
            ``op_ids`` are int in ``[0, 9]`` (Cognitive Operator id) OR
            the special sentinel ``-1`` for ``"any"`` (the test-fixture
            escape hatch — always-pass).
        """
        if isinstance(transition_op, (str, int)):
            transition_op = [transition_op] * batch_size

        if isinstance(transition_op, torch.Tensor):
            if transition_op.dim() == 0:
                transition_op = [int(transition_op.item())] * batch_size
            else:
                transition_op = transition_op.tolist()

        op_ids: list[int] = []
        op_names: list[str] = []
        for entry in transition_op:
            if isinstance(entry, str):
                key = entry.strip().lower()
                if key == "any":
                    op_ids.append(-1)
                    op_names.append("any")
                    continue
                if key not in _OP_TO_CO:
                    raise ValueError(
                        f"Unknown transition op name {entry!r}. "
                        f"Recognized: {sorted(_OP_TO_CO)} or {list(TRANSITION_OPS)}."
                    )
                op_ids.append(_OP_TO_CO[key])
                op_names.append(key)
            elif isinstance(entry, (int, bool)):
                if not (0 <= int(entry) <= 9):
                    raise ValueError(
                        f"Cognitive Operator id must be in [0, 9]; got {entry!r}."
                    )
                op_ids.append(int(entry))
                op_names.append(f"CO-{int(entry)}")
            else:
                raise TypeError(
                    f"transition_op entries must be str / int; got {type(entry).__name__}."
                )

        if len(op_ids) != batch_size:
            raise ValueError(
                f"transition_op length {len(op_ids)} does not match batch size {batch_size}."
            )
        return op_ids, op_names

    @staticmethod
    def _label(idx: int) -> str:
        if 0 <= idx < len(_STATE_LABELS):
            return _STATE_LABELS[idx]
        return f"<oob:{idx}>"

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------

    def forward(
        self,
        p_state_prev: torch.Tensor,
        p_state_next: torch.Tensor,
        transition_op: Union[
            int, str, Sequence[Union[int, str]], torch.Tensor
        ],
    ) -> RPMGateResult:
        """Run the structural admissibility check.

        Args:
            p_state_prev: ``(B, 40)`` simplex distribution.
            p_state_next: ``(B, 40)`` simplex distribution.
            transition_op: see module docstring. Per-example op ids/
                names or a single id/name broadcast across the batch.

        Returns:
            :class:`RPMGateResult` with ``passed``, ``broken_at``, and
            structural ``evidence``.
        """
        if p_state_prev.dim() != 2 or p_state_next.dim() != 2:
            raise ValueError(
                f"p_state_prev/p_state_next must be (B, K); got "
                f"{tuple(p_state_prev.shape)} and {tuple(p_state_next.shape)}."
            )
        if p_state_prev.shape != p_state_next.shape:
            raise ValueError("p_state_prev and p_state_next must have matching shapes.")
        batch_size, num_states = p_state_prev.shape
        if num_states != 40:
            raise ValueError(
                f"RPMGateStub assumes 40 Cognitive States; got {num_states}."
            )

        op_ids, op_names = self._coerce_op(transition_op, batch_size)

        # Dominant-atom argmax per example. detach() because no grads
        # flow through this module.
        source_idx = p_state_prev.detach().argmax(dim=-1)
        target_idx = p_state_next.detach().argmax(dim=-1)

        passed = torch.zeros(batch_size, dtype=torch.bool, device=p_state_prev.device)
        broken_at: list[Optional[str]] = [None] * batch_size

        for b in range(batch_size):
            op_id = op_ids[b]
            s = int(source_idx[b].item())
            t = int(target_idx[b].item())

            if op_id == -1:
                # "any" — test-fixture escape hatch; always pass.
                passed[b] = True
                continue

            verdict = bool(_IS_ADMISSIBLE(op_id, s, t))
            passed[b] = verdict
            if not verdict:
                broken_at[b] = (
                    f"{self._label(s)} -> {op_names[b]} -> {self._label(t)} "
                    f"not in D_{op_id}"
                )

        evidence = {
            "source_index": source_idx,
            "target_index": target_idx,
            "operator_id": torch.tensor(op_ids, dtype=torch.long, device=p_state_prev.device),
            "op_name": op_names,
        }
        return RPMGateResult(passed=passed, broken_at=broken_at, evidence=evidence)


__all__ = [
    "RPMGateStub",
    "RPMGateResult",
    "TRANSITION_OPS",
]
