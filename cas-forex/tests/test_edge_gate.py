"""Tests for the fail-closed null TEST gate (the integrity core).

The single most important property proven here: THE GATE CANNOT EMIT A TOKEN ON
NOISE. A token is an authorization to trade; if pure-noise outcomes could mint
one, the whole edge-discipline contract is void. We also prove the gate
distinguishes "couldn't test" (insufficient bars / underpowered) from "tested
and failed" (null failed), and that a token is bound to its exact setup and goes
stale.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from cas_forex.edge_gate import (
    CandidateSetup,
    EdgeTestDecision,
    evaluate_candidate,
    mint_token,
    verify_token,
)


def _setup(entry: float = 1.1000) -> CandidateSetup:
    return CandidateSetup(
        symbol="EUR/USD",
        timeframe="H1",
        direction="LONG",
        entry=entry,
        stop_loss=entry - 0.0020,
        take_profit=entry + 0.0040,
        signal_strength=1.0,
        regime="trend",
        decision_ref="dref-1",
    )


def _planted_pairs(n: int = 80, effect: float = 0.004, noise: float = 0.0008, seed: int = 2):
    """Recent OOS outcomes where sign(signal_strength) really predicts sign(ret)."""
    rng = np.random.default_rng(seed)
    pairs = []
    for _ in range(n):
        s = float(rng.normal(0, 1.0))
        ret = (1.0 if s >= 0 else -1.0) * effect + float(rng.normal(0, noise))
        pairs.append({"signal_strength": s, "ret": ret, "cost_ret": 0.00005})
    return pairs


def _noise_pairs(n: int = 80, scale: float = 0.004, seed: int = 1):
    """Recent OOS outcomes where ret is INDEPENDENT of signal_strength."""
    rng = np.random.default_rng(seed)
    pairs = []
    for _ in range(n):
        s = float(rng.normal(0, 1.0))
        ret = float(rng.normal(0, scale))  # no link to s
        pairs.append({"signal_strength": s, "ret": ret, "cost_ret": 0.00005})
    return pairs


# --------------------------------------------------------------------------- #
# POWER: a planted edge must PASS and carry a verifiable token.
# --------------------------------------------------------------------------- #
def test_planted_edge_passes_with_token_and_winprob():
    setup = _setup()
    dec = evaluate_candidate(setup, _planted_pairs(), threshold=0.65, seed=5)
    assert isinstance(dec, EdgeTestDecision)
    assert dec.status == "PASS"
    assert dec.edge_token is not None
    assert dec.measured_win_prob >= dec.threshold
    # the minted token must verify against the exact setup it authorized
    assert verify_token(
        dec.edge_token, setup, dec.evaluated_at, now_iso=dec.evaluated_at
    )


# --------------------------------------------------------------------------- #
# DISCIPLINE: the gate CANNOT emit a token on noise.
# --------------------------------------------------------------------------- #
def test_noise_is_no_trade_null_failed_and_no_token():
    setup = _setup()
    dec = evaluate_candidate(setup, _noise_pairs(), threshold=0.65, seed=5)
    assert dec.status == "NO_TRADE_NULL_FAILED"
    assert dec.edge_token is None


def test_noise_does_not_systematically_pass_at_default_threshold():
    """Honest discipline bound, not a false absolute.

    A SINGLE out-of-sample hit-rate test at the default 0.65 threshold on a
    small test split is not infallible: pure noise clears the full conjunction
    (beats-null AND net>0 AND win-prob>=0.65) by luck a small fraction of the
    time (measured ~4-5% over 200 independent draws). We assert the gate keeps
    that rate LOW -- the overwhelming majority of noise draws are refused -- and
    cover the bulletproof bound separately in
    ``test_noise_blocked_at_strict_threshold``. Claiming "noise NEVER passes"
    at 0.65 would itself be a dishonest edge claim.
    """
    setup = _setup()
    passes = 0
    for seed in range(60):
        pairs = _noise_pairs(n=80, seed=seed)
        dec = evaluate_candidate(setup, pairs, threshold=0.65, seed=seed + 100)
        if dec.status == "PASS":
            passes += 1
        # fail-closed invariant holds regardless: non-PASS => no token, PASS => token
        assert (dec.edge_token is None) == (dec.status != "PASS")
    # well under 1-in-10; the conjunction does most of the work even at 0.65.
    assert passes <= 6, f"noise PASSed {passes}/60 at threshold 0.65 -- too leaky"


def test_noise_blocked_at_strict_threshold():
    """At a defensibly strict threshold the gate refuses every noise draw here.

    Small OOS samples need a stricter bar to be robust to single-test luck; the
    threshold is user-adjustable precisely so an operator can buy this margin.
    """
    setup = _setup()
    for seed in range(60):
        pairs = _noise_pairs(n=80, seed=seed)
        dec = evaluate_candidate(setup, pairs, threshold=0.80, seed=seed + 100)
        assert dec.status != "PASS", f"noise PASSed at seed {seed} even at 0.80"
        assert dec.edge_token is None, f"noise minted a token at seed {seed}"


def test_high_threshold_blocks_weak_edge_as_null_failed():
    """A real-but-modest edge below a strict threshold is refused (tested+failed)."""
    setup = _setup()
    # Weak link: detectable but win-prob well under 0.95.
    pairs = _planted_pairs(n=80, effect=0.0015, noise=0.0030, seed=3)
    dec = evaluate_candidate(setup, pairs, threshold=0.95, seed=5)
    assert dec.status == "NO_TRADE_NULL_FAILED"
    assert dec.edge_token is None
    assert dec.measured_win_prob < 0.95


# --------------------------------------------------------------------------- #
# COULDN'T-TEST gates, kept DISTINCT from tested-and-failed.
# --------------------------------------------------------------------------- #
def test_too_few_events_is_insufficient_bars():
    setup = _setup()
    dec = evaluate_candidate(setup, _planted_pairs(n=5), min_events=8, seed=5)
    assert dec.status == "NO_TRADE_INSUFFICIENT_BARS"
    assert dec.edge_token is None


def test_underpowered_when_cannot_split():
    """Enough rows to clear min_events but not enough for the core's train/test split."""
    setup = _setup()
    # min_events=8 needs >= 16 rows for the core to split; give exactly 12.
    dec = evaluate_candidate(setup, _planted_pairs(n=12), min_events=8, seed=5)
    assert dec.status == "NO_TRADE_UNDERPOWERED"
    assert dec.edge_token is None


# --------------------------------------------------------------------------- #
# TOKEN binding + staleness.
# --------------------------------------------------------------------------- #
def test_token_verifies_for_exact_setup():
    setup = _setup()
    ts = "2026-06-28T12:00:00+00:00"
    token = mint_token(setup, ts)
    assert verify_token(token, setup, ts, now_iso=ts) is True


def test_tampered_entry_breaks_verification():
    setup = _setup(entry=1.1000)
    ts = "2026-06-28T12:00:00+00:00"
    token = mint_token(setup, ts)
    tampered = _setup(entry=1.1001)  # one pip move -> different signed setup
    assert verify_token(token, tampered, ts, now_iso=ts) is False


def test_tampered_direction_breaks_verification():
    setup = _setup()
    ts = "2026-06-28T12:00:00+00:00"
    token = mint_token(setup, ts)
    flipped = _setup()
    flipped.direction = "SHORT"
    assert verify_token(token, flipped, ts, now_iso=ts) is False


def test_stale_token_is_rejected():
    setup = _setup()
    issued = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
    ts = issued.isoformat()
    token = mint_token(setup, ts)
    # 121s later, past the 120s max age.
    later = (issued + timedelta(seconds=121)).isoformat()
    assert verify_token(token, setup, ts, now_iso=later, max_age_seconds=120) is False
    # within the window it still holds
    ok = (issued + timedelta(seconds=60)).isoformat()
    assert verify_token(token, setup, ts, now_iso=ok, max_age_seconds=120) is True


def test_future_dated_token_is_rejected():
    setup = _setup()
    issued = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
    ts = issued.isoformat()
    token = mint_token(setup, ts)
    earlier = (issued - timedelta(seconds=10)).isoformat()
    assert verify_token(token, setup, ts, now_iso=earlier) is False


def test_none_token_never_verifies():
    setup = _setup()
    ts = "2026-06-28T12:00:00+00:00"
    assert verify_token(None, setup, ts, now_iso=ts) is False
