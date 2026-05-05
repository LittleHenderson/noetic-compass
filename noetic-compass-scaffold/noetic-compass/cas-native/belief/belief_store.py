"""High-level belief store API for the CAS-as-Belief-Substrate.

The store mediates between:

* the chat REPL (which calls :meth:`record_observation` after each prediction),
* the four CAS gates (^4 Vibration, ^7 Rhythm, RPM, Inversion Scan),
* the SQLite persistence layer.

The lock rule is the single point where all four gates compose:

    locked == (
        rpm_chain_satisfied
        AND vibration > VIBRATION_LOCK_THRESHOLD
        AND inversion_scan_clean
        AND rhythm_count >= MIN_RHYTHM_FOR_LOCK
    )

Section-retraction (CORRECTION 2): once a belief locks, the cached gate
results survive future observations until either (a) ``decay_all`` drops the
vibration below the threshold or (b) :meth:`add_contradiction` inserts a
contradiction that triggers a forced re-evaluation.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from .belief import Belief
from .inversion_gate import run_inversion_scan
from . import persistence
from .rhythm import MIN_RHYTHM_FOR_LOCK, bump_rhythm
from .rpm_gate import check_rpm_chain
from .vibration import (
    DEFAULT_HALF_LIFE_DAYS,
    Observation,
    apply_decay,
    compute_vibration,
)


VIBRATION_LOCK_THRESHOLD: float = 0.7


def lock_rule(belief: Belief) -> bool:
    """Pure function from belief state → lock decision."""
    return (
        belief.rpm_chain_satisfied
        and belief.vibration > VIBRATION_LOCK_THRESHOLD
        and belief.inversion_scan_clean
        and belief.rhythm_count >= MIN_RHYTHM_FOR_LOCK
    )


def derive_claim_key(claim_text: str, cas_expression: str) -> str:
    """Stable key for a (claim_text, cas_expression) pair.

    Lowercases and collapses whitespace in claim_text; keeps cas_expression
    as-is (notation is case- and whitespace-sensitive). 16-byte SHA1 prefix.
    """
    normalized = re.sub(r"\s+", " ", claim_text.strip().lower())
    payload = f"{normalized}\x00{cas_expression}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class BeliefStore:
    """Stateful façade around persistence + gates.

    Construction is cheap; the SQLite connection is opened eagerly. Call
    :meth:`close` when finished, or use the store as a context manager.
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        *,
        half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
        vibration_lock_threshold: float = VIBRATION_LOCK_THRESHOLD,
    ) -> None:
        self._conn: sqlite3.Connection = persistence.open_db(db_path)
        self._half_life_days = float(half_life_days)
        self._vibration_lock_threshold = float(vibration_lock_threshold)

    # ---- context manager -------------------------------------------------

    def __enter__(self) -> "BeliefStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # pragma: no cover - defensive
            pass

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    # ---- write-side ------------------------------------------------------

    def record_observation(
        self,
        claim_text: str,
        cas_expression: str,
        evidence_strength: float = 0.5,
        *,
        source: str = "chat-session",
        now: datetime | None = None,
    ) -> Belief:
        """Record one observation and return the updated belief.

        If the belief does not yet exist, it is created. Otherwise it is
        reinforced: vibration grows, rhythm count bumps, both gates re-run.
        The belief is persisted in its post-observation state.
        """
        if not claim_text:
            raise ValueError("claim_text must be non-empty")
        if evidence_strength <= 0:
            raise ValueError(
                f"evidence_strength must be > 0, got {evidence_strength!r}"
            )

        when = now if now is not None else datetime.now()
        claim_key = derive_claim_key(claim_text, cas_expression)
        existing = persistence.fetch_belief(self._conn, claim_key)

        # Foreign-key parents: ensure a beliefs row exists before inserting an
        # observation that references it. For first-time observations we
        # insert a placeholder belief that will be overwritten by the upsert
        # at the end of this method with the post-gate values.
        if existing is None:
            placeholder = Belief(
                claim_key=claim_key,
                claim_text=claim_text,
                cas_expression=cas_expression,
                vibration=0.0,
                rhythm_count=0,
                rpm_chain_satisfied=False,
                rpm_chain_status={},
                inversion_scan_clean=True,
                inversion_scan_axes={},
                first_seen=when,
                last_reinforced=when,
                sources=[source],
                locked=False,
            )
            persistence.upsert_belief(self._conn, placeholder)

        persistence.insert_observation(
            self._conn, claim_key, when, evidence_strength, source
        )
        observations = persistence.fetch_observations(self._conn, claim_key)
        contradiction_count = persistence.count_contradictions(
            self._conn, claim_key
        )

        # ^4 Vibration: replay all observations with decay.
        vibration_value = compute_vibration(
            observations, when, half_life_days=self._half_life_days
        )

        # ^7 Rhythm: count is the number of observations.
        rhythm_count = len(observations)

        # RPM gate.
        rpm_result = check_rpm_chain(
            claim_text, cas_expression, prior_observation_count=rhythm_count
        )

        # Inversion scan. Pass contradiction history so axis N can flag.
        contradiction_reasons = [
            c["reason"]
            for c in persistence.fetch_contradictions(self._conn, claim_key)
        ]
        scan = run_inversion_scan(
            cas_expression,
            history=contradiction_reasons,
            rpm_satisfied=rpm_result.satisfied,
        )

        # Build / update belief.
        if existing is None:
            sources = [source]
            first_seen = when
        else:
            sources = list(existing.sources)
            if source not in sources:
                sources.append(source)
            first_seen = existing.first_seen

        belief = Belief(
            claim_key=claim_key,
            claim_text=claim_text,
            cas_expression=cas_expression,
            vibration=vibration_value,
            rhythm_count=rhythm_count,
            rpm_chain_satisfied=rpm_result.satisfied,
            rpm_chain_status=rpm_result.status,
            inversion_scan_clean=scan.clean,
            inversion_scan_axes=scan.axes,
            first_seen=first_seen,
            last_reinforced=when,
            sources=sources,
            locked=False,
        )
        belief = replace(belief, locked=lock_rule(belief))
        persistence.upsert_belief(self._conn, belief)
        return belief

    def add_contradiction(
        self,
        claim_text: str,
        cas_expression: str,
        reason: str = "user contradiction",
        *,
        now: datetime | None = None,
    ) -> Belief | None:
        """Insert a contradiction for a claim and force a re-evaluation.

        Returns the updated belief, or ``None`` if no belief exists for the
        derived claim_key. After contradiction:

        * a contradiction row is inserted;
        * the RPM gate and inversion scan are re-run (axis N flags because
          contradiction history is non-empty);
        * the belief unlocks (because inversion is no longer clean and
          potentially because rpm/vibration shifted);
        * vibration is decayed to ``now`` but not zeroed (the contradiction
          adds doubt rather than overwriting the prior).
        """
        when = now if now is not None else datetime.now()
        claim_key = derive_claim_key(claim_text, cas_expression)
        belief = persistence.fetch_belief(self._conn, claim_key)
        if belief is None:
            return None

        persistence.insert_contradiction(self._conn, claim_key, when, reason)

        observations = persistence.fetch_observations(self._conn, claim_key)
        vibration_value = compute_vibration(
            observations, when, half_life_days=self._half_life_days
        )

        rpm_result = check_rpm_chain(
            claim_text,
            cas_expression,
            prior_observation_count=len(observations),
        )
        contradiction_reasons = [
            c["reason"]
            for c in persistence.fetch_contradictions(self._conn, claim_key)
        ]
        scan = run_inversion_scan(
            cas_expression,
            history=contradiction_reasons,
            rpm_satisfied=rpm_result.satisfied,
        )

        updated = Belief(
            claim_key=claim_key,
            claim_text=belief.claim_text,
            cas_expression=belief.cas_expression,
            vibration=vibration_value,
            rhythm_count=len(observations),
            rpm_chain_satisfied=rpm_result.satisfied,
            rpm_chain_status=rpm_result.status,
            inversion_scan_clean=scan.clean,
            inversion_scan_axes=scan.axes,
            first_seen=belief.first_seen,
            last_reinforced=belief.last_reinforced,
            sources=belief.sources,
            locked=False,
        )
        updated = replace(updated, locked=lock_rule(updated))
        persistence.upsert_belief(self._conn, updated)
        return updated

    # ---- read-side -------------------------------------------------------

    def check_belief(
        self, claim_text: str, cas_expression: str
    ) -> Belief | None:
        """Return the belief for the given (claim_text, cas_expression), if any."""
        claim_key = derive_claim_key(claim_text, cas_expression)
        return persistence.fetch_belief(self._conn, claim_key)

    def get_by_key(self, claim_key: str) -> Belief | None:
        return persistence.fetch_belief(self._conn, claim_key)

    def list_locked(self) -> list[Belief]:
        """All currently locked beliefs, sorted by vibration desc."""
        return persistence.list_beliefs(self._conn, locked_only=True)

    def list_all(self) -> list[Belief]:
        """All beliefs, sorted by vibration desc."""
        return persistence.list_beliefs(self._conn, locked_only=False)

    def find_by_claim(self, claim_text: str) -> list[Belief]:
        """Return every belief whose claim_text matches (case-insensitive,
        whitespace-collapsed). Same claim_text under different cas_expressions
        produces multiple beliefs; this surfaces all of them."""
        target = re.sub(r"\s+", " ", claim_text.strip().lower())
        out: list[Belief] = []
        for b in persistence.list_beliefs(self._conn):
            if re.sub(r"\s+", " ", b.claim_text.strip().lower()) == target:
                out.append(b)
        return out

    def history(self, claim_key: str) -> dict[str, Any]:
        """Return observations + contradictions for a claim_key."""
        return {
            "observations": persistence.fetch_observations(
                self._conn, claim_key
            ),
            "contradictions": persistence.fetch_contradictions(
                self._conn, claim_key
            ),
        }

    # ---- maintenance -----------------------------------------------------

    def decay_all(self, *, now: datetime | None = None) -> int:
        """Recompute vibration for every belief and re-evaluate the lock rule.

        Returns the number of beliefs whose locked status changed.
        """
        when = now if now is not None else datetime.now()
        changed = 0
        for key in list(persistence.all_claim_keys(self._conn)):
            belief = persistence.fetch_belief(self._conn, key)
            if belief is None:
                continue
            observations = persistence.fetch_observations(self._conn, key)
            new_vib = compute_vibration(
                observations, when, half_life_days=self._half_life_days
            )
            updated = replace(
                belief,
                vibration=new_vib,
                last_reinforced=belief.last_reinforced,
            )
            updated = replace(updated, locked=lock_rule(updated))
            if updated.locked != belief.locked or new_vib != belief.vibration:
                persistence.upsert_belief(self._conn, updated)
                if updated.locked != belief.locked:
                    changed += 1
        return changed

    def explain(self, claim_key: str) -> dict[str, Any] | None:
        """Return a structured explanation for ``/why <claim>``.

        The shape:

            {
              "belief": Belief,
              "observations": [Observation, ...],
              "contradictions": [{"timestamp", "reason"}, ...],
              "rpm": {"satisfied": bool, "stages": {...}, ...},
              "inversion": {"clean": bool, "axes": {...}},
              "lock_rule": {
                  "rpm": bool,
                  "vibration_above": bool,
                  "inversion": bool,
                  "rhythm": bool,
                  "locked": bool,
              },
            }
        """
        belief = persistence.fetch_belief(self._conn, claim_key)
        if belief is None:
            return None
        history = self.history(claim_key)
        return {
            "belief": belief,
            "observations": history["observations"],
            "contradictions": history["contradictions"],
            "rpm": belief.rpm_chain_status,
            "inversion": belief.inversion_scan_axes,
            "lock_rule": {
                "rpm": belief.rpm_chain_satisfied,
                "vibration_above": (
                    belief.vibration > self._vibration_lock_threshold
                ),
                "inversion": belief.inversion_scan_clean,
                "rhythm": belief.rhythm_count >= MIN_RHYTHM_FOR_LOCK,
                "locked": belief.locked,
                "vibration_threshold": self._vibration_lock_threshold,
                "min_rhythm": MIN_RHYTHM_FOR_LOCK,
            },
        }
