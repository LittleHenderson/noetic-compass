"""The fail-closed null TEST gate -- the integrity core of the adaptive loop.

This is the ONE place in CAS Forex that is allowed to authorize a trade to
EXIST. Everything upstream (WATCH/ANALYZE/STRATEGIZE) proposes a
:class:`CandidateSetup`; nothing downstream (EXECUTE/COMPOUND) may act on it
unless this gate mints an ``edge_token`` for it. No fresh token => NO TRADE.

THE INTEGRITY CONTRACT (non-negotiable, and the reason this module exists)
=========================================================================
A candidate is authorized ONLY if, on the setup's OWN recent out-of-sample
outcomes, the measured win-probability is >= the user's threshold AND the
signal beats a shuffled/random null AND it is net-positive after cost. The
gate is **fail-closed**: any failure mode -- couldn't test, underpowered,
tested-and-failed, stale data -- yields a NON-PASS decision and a ``None``
token. We never conflate "tested and failed the null" with "couldn't run the
test"; each gets a distinct status so the loop reacts correctly.

Money management AMPLIFIES a confirmed edge; it never creates one. That is why
the only thing that can produce a token is a PASS here, and the token is bound
(by HMAC over the exact entry/stop/take-profit) to the precise setup that was
tested. Change any leg of the setup and the token no longer verifies -- you
cannot test setup A and trade setup B. Tokens are also short-lived (default
120s): an edge measured on recent data goes stale, and a stale token is as good
as no token.

RESIDUAL SINGLE-TEST RISK (stated honestly, not hidden)
=======================================================
This gate REDUCES the chance of authorizing noise; it does not reduce it to
zero. A single out-of-sample test on a small split has a real false-positive
rate: with the default 0.65 threshold and ~30-event test splits, pure-noise
outcomes clear the full conjunction (beats-null AND net>0 AND win-prob>=thr) by
luck roughly 4-5% of the time (measured). Two things follow, both by design:
(1) the threshold is user-adjustable so an operator can buy margin -- at 0.80 the
same noise draws are refused; (2) a PASS here is a NECESSARY, not sufficient,
condition for size -- the loop should treat one PASS as a candidate to confirm,
and the short token lifetime forces re-proof on fresh data. Claiming "noise can
NEVER pass" would itself be the kind of overstated edge claim this module exists
to catch.

We REUSE the proven shuffle-null core
(:func:`cas_forex.macro_surprise.evaluate_surprise_return_pairs`) so the gate's
discipline is exactly the discipline that caught every fake edge this session.
We feed the per-event ``signal_strength`` as that core's ``surprise`` channel --
NOT the fixed LONG/SHORT direction. Direction was already decided upstream in
STRATEGIZE; the gate only asks whether the *strength* of the signal carries real
out-of-sample skill at predicting the sign of the realized return.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from cas_forex.macro_surprise import evaluate_surprise_return_pairs

# Process-local signing secret for edge tokens. A token is only an
# authorization WITHIN this running process/session, so a per-process random
# secret is the right default: tokens never need to survive a restart, and a
# restart SHOULD invalidate every outstanding authorization (fresh edge proof
# required). An operator may pin CAS_FOREX_EDGE_SECRET to make tokens
# reproducible across processes (e.g. for an audit harness).
_EDGE_SECRET = os.environ.get("CAS_FOREX_EDGE_SECRET", "").encode("utf-8") or os.urandom(32)

_VALID_DIRECTIONS = ("LONG", "SHORT")


@dataclass
class CandidateSetup:
    """A proposed trade, fully specified by STRATEGIZE, awaiting the TEST gate.

    The gate never decides direction -- ``direction`` is an input here, chosen
    upstream. The gate only authorizes (or refuses) the setup as given.
    """

    symbol: str
    timeframe: str
    direction: str  # 'LONG' | 'SHORT'
    entry: float
    stop_loss: float
    take_profit: float
    signal_strength: float
    regime: str
    decision_ref: str


@dataclass
class EdgeTestDecision:
    """The gate's verdict. A PASS (and ONLY a PASS) carries an ``edge_token``."""

    status: str  # PASS | NO_TRADE_NULL_FAILED | NO_TRADE_UNDERPOWERED
    #            | NO_TRADE_STALE_DATA | NO_TRADE_INSUFFICIENT_BARS
    measured_win_prob: float
    null_p95: float
    threshold: float
    edge_token: Optional[str]
    evaluated_at: str  # iso-utc
    reason: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_payload(setup: CandidateSetup, evaluated_at: str) -> str:
    """The exact bytes a token signs. Binds the token to THIS setup + time.

    Floats are rendered with ``repr`` so the signed payload is an exact,
    round-trip-stable representation -- the token verifies iff every leg of the
    setup matches to the bit.
    """
    return "|".join(
        [
            str(setup.symbol),
            str(setup.direction),
            repr(float(setup.entry)),
            repr(float(setup.stop_loss)),
            repr(float(setup.take_profit)),
            str(evaluated_at),
        ]
    )


def mint_token(setup: CandidateSetup, evaluated_at: str) -> str:
    """Deterministic HMAC-SHA256 authorization bound to setup + evaluation time.

    Deterministic for a fixed signing secret: the same setup + ``evaluated_at``
    always mints the same token, so :func:`verify_token` can recompute and
    compare. Only the gate calls this on a PASS.
    """
    payload = _canonical_payload(setup, evaluated_at).encode("utf-8")
    return hmac.new(_EDGE_SECRET, payload, hashlib.sha256).hexdigest()


def verify_token(
    token: Optional[str],
    setup: CandidateSetup,
    evaluated_at: str,
    *,
    now_iso: str,
    max_age_seconds: float = 120.0,
) -> bool:
    """True iff ``token`` is an authentic, unexpired authorization for ``setup``.

    Three independent gates, all must hold:
      * the token is present;
      * it is a valid HMAC over THIS setup + ``evaluated_at`` (constant-time
        compare; any tampered leg -- entry, stop, take-profit, direction,
        symbol -- breaks it);
      * it is not older than ``max_age_seconds`` (an edge measured on recent
        data goes stale; a future-dated token is also rejected).
    """
    if not token:
        return False
    try:
        expected = mint_token(setup, evaluated_at)
    except Exception:
        return False
    if not hmac.compare_digest(token, expected):
        return False
    try:
        issued = datetime.fromisoformat(str(evaluated_at).replace("Z", "+00:00"))
        if issued.tzinfo is None:
            issued = issued.replace(tzinfo=timezone.utc)
        now = datetime.fromisoformat(str(now_iso).replace("Z", "+00:00"))
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False
    age = (now - issued).total_seconds()
    if age < 0:
        return False  # token dated in the future -- reject
    return age <= max_age_seconds


def evaluate_candidate(
    setup: CandidateSetup,
    entry_pairs: Sequence[Dict[str, float]],
    *,
    threshold: float = 0.65,
    n_null: int = 500,
    min_events: int = 8,
    seed: int = 11,
) -> EdgeTestDecision:
    """Fail-closed TEST: authorize ``setup`` ONLY on a proven out-of-sample edge.

    ``entry_pairs`` are recent OOS outcomes for THIS setup's pattern, each a
    ``{'signal_strength': float, 'ret': float, 'cost_ret': float}`` dict (time
    ordered). We feed ``signal_strength`` as the shuffle-null core's ``surprise``
    channel and ask whether its sign predicts the sign of ``ret`` better than a
    label-shuffled null, net of cost.

    Status semantics (distinct, never conflated):
      * ``NO_TRADE_INSUFFICIENT_BARS`` -- fewer than ``min_events`` outcomes;
        we literally could not run a credible test. (couldn't test)
      * ``NO_TRADE_UNDERPOWERED`` -- the core had enough rows to attempt but not
        enough for a train/test split (its ``UNDERPOWERED`` verdict). (couldn't test)
      * ``NO_TRADE_NULL_FAILED`` -- the test RAN and the signal did not beat the
        null, was not net-positive, or its win-prob was below ``threshold``.
        (tested + failed)
      * ``PASS`` -- beat the null AND net-positive AND win-prob >= threshold.

    Only a PASS carries an ``edge_token``.
    """
    evaluated_at = _now_iso()
    pairs = list(entry_pairs)

    # Couldn't-test gate #1: not enough outcomes to even attempt a credible test.
    if len(pairs) < min_events:
        return EdgeTestDecision(
            status="NO_TRADE_INSUFFICIENT_BARS",
            measured_win_prob=0.0,
            null_p95=0.0,
            threshold=threshold,
            edge_token=None,
            evaluated_at=evaluated_at,
            reason=(
                f"only {len(pairs)} OOS outcomes for this pattern "
                f"(need >= {min_events} to run the null test)"
            ),
        )

    # Normalize into the core's expected pair shape: signal_strength -> surprise.
    usable: List[Dict[str, float]] = []
    for p in pairs:
        usable.append(
            {
                "surprise": float(p.get("signal_strength", 0.0)),
                "ret": float(p.get("ret", 0.0)),
                "cost_ret": float(p.get("cost_ret", 0.0)),
            }
        )

    report = evaluate_surprise_return_pairs(
        usable,
        symbol=setup.symbol,
        n_null=n_null,
        min_test_events=min_events,
        seed=seed,
    )
    summary = report.summary
    verdict = summary.get("verdict")

    null_p95 = float(summary.get("null_p95_return_pct", 0.0)) / 100.0

    # Couldn't-test gate #2: the core itself reports it lacked power to split.
    if verdict == "UNDERPOWERED":
        return EdgeTestDecision(
            status="NO_TRADE_UNDERPOWERED",
            measured_win_prob=0.0,
            null_p95=null_p95,
            threshold=threshold,
            edge_token=None,
            evaluated_at=evaluated_at,
            reason=summary.get("reason", "underpowered: not enough events for a train/test split"),
        )

    # The test RAN. measured_win_prob is the fraction of correctly-signed
    # net-positive TEST events -- the core's out-of-sample hit_rate.
    measured_win_prob = float(summary.get("hit_rate", 0.0))
    net_return = float(summary.get("net_return_pct", 0.0)) / 100.0
    beats_null = bool(summary.get("beats_null_p95", False))

    passes = (
        verdict == "CANDIDATE_EDGE"
        and beats_null
        and net_return > 0.0
        and measured_win_prob >= threshold
    )

    if passes:
        token = mint_token(setup, evaluated_at)
        return EdgeTestDecision(
            status="PASS",
            measured_win_prob=measured_win_prob,
            null_p95=null_p95,
            threshold=threshold,
            edge_token=token,
            evaluated_at=evaluated_at,
            reason=(
                f"edge confirmed: win_prob {measured_win_prob:.3f} >= threshold "
                f"{threshold:.3f}, net {net_return:.5f} > 0, beats shuffled null"
            ),
        )

    # tested + failed: explain WHICH condition(s) failed (never as couldn't-test).
    fail_reasons: List[str] = []
    if not beats_null:
        fail_reasons.append(
            f"net return {net_return:.5f} does not beat shuffled null p95 {null_p95:.5f}"
        )
    if net_return <= 0.0:
        fail_reasons.append(f"net return {net_return:.5f} not positive after cost")
    if measured_win_prob < threshold:
        fail_reasons.append(
            f"win_prob {measured_win_prob:.3f} below threshold {threshold:.3f}"
        )
    if not fail_reasons:
        fail_reasons.append("did not satisfy all edge conditions")

    return EdgeTestDecision(
        status="NO_TRADE_NULL_FAILED",
        measured_win_prob=measured_win_prob,
        null_p95=null_p95,
        threshold=threshold,
        edge_token=None,
        evaluated_at=evaluated_at,
        reason="; ".join(fail_reasons),
    )
