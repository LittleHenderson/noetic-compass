"""The fail-closed edge gate, verified at the registry AND the dispatch chokepoint.

PROVES: a real-money order with no registered PASS is refused; a tampered order
(geometry swapped after the PASS) is refused; a stale PASS is refused; an
authorized matching order goes through; and legacy paper dispatch (no registration,
not live) is unaffected.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cas_forex import edge_authorization as EA
from cas_forex import execution_guard
from cas_forex.edge_authorization import EdgeNotAuthorized
from cas_forex.edge_gate import CandidateSetup, EdgeTestDecision, _now_iso, mint_token


def _pass(decision_ref="D1", symbol="EUR/USD", direction="LONG",
          entry=1.10, sl=1.09, tp=1.13, evat=None):
    evat = evat or _now_iso()
    setup = CandidateSetup(symbol=symbol, timeframe="H1", direction=direction, entry=entry,
                           stop_loss=sl, take_profit=tp, signal_strength=1.5,
                           regime="trend", decision_ref=decision_ref)
    dec = EdgeTestDecision(status="PASS", measured_win_prob=0.72, null_p95=0.10,
                           threshold=0.65, edge_token=mint_token(setup, evat),
                           evaluated_at=evat, reason="passed")
    return setup, dec, evat


class FakeOrder:
    def __init__(self, decision_ref="D1", symbol="EUR/USD", direction="LONG",
                 stop_loss=1.09, take_profit=1.13):
        self.decision_ref = decision_ref
        self.symbol = symbol
        self.direction = direction
        self.stop_loss = stop_loss
        self.take_profit = take_profit


class PaperBridge:
    def execute_order(self, order):
        return "FILLED"


class RealBridge:
    def will_execute_real_order(self):
        return True

    def execute_order(self, order):
        return "FILLED"


@pytest.fixture(autouse=True)
def _clean_registry():
    EA.reset()
    yield
    EA.reset()


# --- registry ---------------------------------------------------------------

def test_authorize_only_accepts_a_pass():
    setup, _, evat = _pass()
    no_trade = EdgeTestDecision(status="NO_TRADE_NULL_FAILED", measured_win_prob=0.5,
                                null_p95=0.6, threshold=0.65, edge_token=None,
                                evaluated_at=evat, reason="failed null")
    with pytest.raises(EdgeNotAuthorized):
        EA.authorize("D1", no_trade, setup)
    assert not EA.is_required("D1")


def test_require_passes_for_fresh_matching_pass():
    setup, dec, _ = _pass("D1")
    EA.authorize("D1", dec, setup)
    assert EA.is_required("D1")
    EA.require(FakeOrder("D1"), is_real=False)  # no raise


def test_require_refuses_unregistered():
    with pytest.raises(EdgeNotAuthorized):
        EA.require(FakeOrder("UNKNOWN"), is_real=True)


def test_require_refuses_stale_token():
    setup, dec, evat = _pass("D1")
    EA.authorize("D1", dec, setup, max_age_seconds=120)
    later = (datetime.fromisoformat(evat) + timedelta(minutes=10)).isoformat()
    with pytest.raises(EdgeNotAuthorized):
        EA.require(FakeOrder("D1"), is_real=False, now_iso=later)


def test_require_refuses_geometry_divergence():
    setup, dec, _ = _pass("D1", sl=1.09)
    EA.authorize("D1", dec, setup)
    with pytest.raises(EdgeNotAuthorized):
        EA.require(FakeOrder("D1", stop_loss=1.05), is_real=False)  # SL swapped after PASS


# --- chokepoint (execution_guard.guarded_place_order) ------------------------

def test_chokepoint_blocks_real_money_without_edge(monkeypatch):
    # Isolate the EDGE gate: neutralize the live-auth recheck so we test edge, not auth.
    import cas_forex.runtime_gates as rg
    monkeypatch.setattr(rg, "require_authorized", lambda *a, **k: None)
    with pytest.raises(EdgeNotAuthorized):
        execution_guard.guarded_place_order(RealBridge(), FakeOrder("NOPE"))


def test_chokepoint_blocks_diverged_authorized_order(monkeypatch):
    setup, dec, _ = _pass("D2", sl=1.09)
    EA.authorize("D2", dec, setup)
    monkeypatch.setattr(execution_guard, "guard", lambda *a, **k: None)  # isolate edge from risk gate
    with pytest.raises(EdgeNotAuthorized):
        execution_guard.guarded_place_order(PaperBridge(), FakeOrder("D2", stop_loss=1.05))


def test_chokepoint_allows_authorized_matching_order(monkeypatch):
    setup, dec, _ = _pass("D3")
    EA.authorize("D3", dec, setup)
    monkeypatch.setattr(execution_guard, "guard", lambda *a, **k: None)
    assert execution_guard.guarded_place_order(PaperBridge(), FakeOrder("D3")) == "FILLED"


def test_chokepoint_legacy_paper_order_unaffected(monkeypatch):
    # Not registered, not live -> edge gate skipped -> dispatch proceeds (no retro-break).
    monkeypatch.setattr(execution_guard, "guard", lambda *a, **k: None)
    assert execution_guard.guarded_place_order(PaperBridge(), FakeOrder("LEGACY")) == "FILLED"
