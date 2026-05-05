"""Belief dataclass for the CAS-as-Belief-Substrate (CABS).

A `Belief` is a claim that the system has been exposed to enough times, through
sufficient evidence, with structural sanity intact, that it can be locked in as
factually correct under the CAS framework. The four CAS primitives that govern
locking are:

* **^4 Vibration** — the degree to which an Idea resonates with the Mind, its
  impression. Implemented as a saturating real in [0, 1] that decays without
  reinforcement.
* **^7 Rhythm** — the rate and pattern a Mind is exposed to an Idea, entraining
  / conditioning it. Implemented as an exposure count.
* **RPM (Roadmap of Prerequisites for Manifestation)** — A0 → Dn → Wn → Pn →
  claim. Section-retraction: once satisfied, cache.
* **Inversion Scan** — the 7-axis structural sanity check (N, W, F, E, S, A, P).
  Must be clean for a belief to lock.

The lock rule (see `belief_store.lock_rule`) requires all four gates to pass
together: RPM satisfied, vibration above threshold, inversion scan clean,
rhythm count above threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Belief:
    """A claim under the CAS belief substrate.

    Attributes
    ----------
    claim_key:
        Stable, normalized identifier for the claim. Used as the primary key in
        the persistence layer and to deduplicate observations across sessions.
    claim_text:
        The original natural-language utterance that produced the claim.
    cas_expression:
        The CAS expression (e.g. ``^3^P|A``) the predictor emitted for this
        claim. The compiler is expected to accept this expression.
    vibration:
        ^4 Vibration in [0, 1]. Saturating reinforcement, exponential decay with
        a 30-day half-life by default. See ``vibration.py``.
    rhythm_count:
        ^7 Rhythm exposure count. Strictly non-negative integer.
    rpm_chain_satisfied:
        Whether the most recent RPM gate evaluation cleared. Section-retraction
        means once satisfied + cached, subsequent observations may rely on the
        cached result; the gate still re-evaluates on contradictions.
    rpm_chain_status:
        Detail dict from the RPM gate (compiler validity, admissibility status,
        prior-observation count, cache hit/miss).
    inversion_scan_clean:
        Whether the most recent 7-axis inversion scan returned clean.
    inversion_scan_axes:
        Per-axis status from the inversion scan. Keys: ``N``, ``W``, ``F``,
        ``E``, ``S``, ``A``, ``P``. Values are dicts with at least a ``clean``
        boolean and a ``reason`` string.
    first_seen:
        Timestamp the belief was first recorded.
    last_reinforced:
        Timestamp of the most recent observation that reinforced this belief.
    sources:
        List of source identifiers (e.g. ``"chat-session"``). Append-only.
    locked:
        Whether the belief satisfies the lock rule at the time of inspection.
        This is a derived flag; the canonical lock decision is computed by
        :func:`belief_store.lock_rule` against the live state.
    """

    claim_key: str
    claim_text: str
    cas_expression: str
    vibration: float
    rhythm_count: int
    rpm_chain_satisfied: bool
    rpm_chain_status: dict[str, Any]
    inversion_scan_clean: bool
    inversion_scan_axes: dict[str, Any]
    first_seen: datetime
    last_reinforced: datetime
    sources: list[str] = field(default_factory=list)
    locked: bool = False

    def __post_init__(self) -> None:
        if not (0.0 <= self.vibration <= 1.0):
            raise ValueError(
                f"vibration must be in [0, 1], got {self.vibration!r}"
            )
        if self.rhythm_count < 0:
            raise ValueError(
                f"rhythm_count must be >= 0, got {self.rhythm_count!r}"
            )
        if not self.claim_key:
            raise ValueError("claim_key must be a non-empty string")
        if not isinstance(self.first_seen, datetime):
            raise TypeError(
                f"first_seen must be datetime, got {type(self.first_seen).__name__}"
            )
        if not isinstance(self.last_reinforced, datetime):
            raise TypeError(
                "last_reinforced must be datetime, got "
                f"{type(self.last_reinforced).__name__}"
            )

    def short_status(self) -> str:
        """One-line status string for REPL rendering.

        Format: ``LOCKED  ^4=0.82  ^7=14  RPM✓  Inv✓`` or
        ``open    ^4=0.34  ^7=2   RPM✓  Inv✗(W)``.
        """
        head = "LOCKED" if self.locked else "open  "
        rpm = "RPM✓" if self.rpm_chain_satisfied else "RPM✗"
        if self.inversion_scan_clean:
            inv = "Inv✓"
        else:
            failing = [
                axis
                for axis, info in self.inversion_scan_axes.items()
                if not info.get("clean", True)
            ]
            tag = ",".join(failing) if failing else "?"
            inv = f"Inv✗({tag})"
        return (
            f"{head}  ^4={self.vibration:.2f}  ^7={self.rhythm_count}  {rpm}  {inv}"
        )
