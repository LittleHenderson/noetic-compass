from __future__ import annotations

from datetime import datetime, timezone
import json
from types import SimpleNamespace

from cas_forex.edge_gate import CandidateSetup, EdgeTestDecision
from cas_forex import live_candle_route_policy as policy


def test_live_candle_route_forwards_effective_symbol_universe_to_market_scan(
    tmp_path, monkeypatch
):
    policy.reset_live_candle_route_cache_for_testing()
    captured = {}

    def scan(**kwargs):
        captured.update(kwargs)
        return {
            "symbol": "USD/JPY",
            "timeframe": "H1",
            "candles": [],
            "broker_grade_market_truth": True,
            "fallback_used": False,
        }

    monkeypatch.setattr(policy, "build_waste_market_state_scan", scan)
    monkeypatch.setattr(policy, "analyze_market_state", lambda state: {"reason": "no candle"})
    monkeypatch.setattr(policy, "strategize_market_state", lambda state, analysis: None)

    result = policy.build_live_candle_route_intents(
        allowed_symbols=["USD/JPY", "EUR/USD"],
        max_scan_candidates=1,
        source_path=tmp_path / "source.json",
        emission_state_path=tmp_path / "emissions.json",
        use_cache=False,
    )

    assert result == []
    assert captured["allowed_symbols"] == ["EUR/USD", "USD/JPY"]
    assert captured["max_scan_candidates"] == 2
    assert callable(captured["candidate_state_transform"])
    assert callable(captured["candidate_block_reason"])


def test_runtime_status_aggregates_all_lanes_below_directional_floor():
    policy.reset_live_candle_route_cache_for_testing()
    for timeframe, score, shadow_status in (
        ("M1", 0.22, "NO_TRADE_NULL_FAILED"),
        ("M5", 0.31, "PASS"),
    ):
        policy._record_invocation_status(
            f"{timeframe}|60|NAS100",
            {
                "status": "FULL_SCAN_COMPLETED",
                "fresh_market_scan_performed": True,
                "timeframe": timeframe,
                "attempt_count": 1,
                "entry_stage_summary": {
                    "candidate_formation_status_counts": {
                        "BELOW_DIRECTIONAL_FLOOR": 1
                    },
                    "edge_status_counts": {"NO_CANDIDATE": 1},
                    "shadow_edge_status_counts": {shadow_status: 1},
                    "directional_candidate_count": 0,
                    "best_shadow_pass_lane": (
                        {
                            "symbol": "NAS100",
                            "timeframe": timeframe,
                            "direction": "LONG",
                            "directional_score": score,
                            "directional_floor": 0.5,
                            "shadow_edge_status": "PASS",
                            "shadow_measured_win_prob": 0.8,
                            "shadow_threshold": 0.65,
                            "shadow_edge_preview_unregistered": True,
                            "shadow_has_edge_token": False,
                        }
                        if shadow_status == "PASS"
                        else None
                    ),
                    "strongest_rejected_lane": {
                        "symbol": "NAS100",
                        "timeframe": timeframe,
                        "directional_score": score,
                        "directional_floor": 0.5,
                        "shadow_edge_status": shadow_status,
                        "shadow_edge_preview_unregistered": True,
                        "shadow_has_edge_token": False,
                    },
                },
            },
        )

    runtime = policy.live_candle_route_runtime_status()

    assert runtime["attempt_count"] == 2
    assert runtime["directional_candidate_count"] == 0
    assert runtime["all_observed_lanes_below_directional_floor"] is True
    assert runtime["shadow_edge_status_counts"] == {
        "NO_TRADE_NULL_FAILED": 1,
        "PASS": 1,
    }
    assert runtime["shadow_pass_preview_count"] == 1
    assert runtime["best_shadow_pass_lane"]["timeframe"] == "M5"
    assert runtime["best_shadow_pass_lane"]["directional_score"] == 0.31
    assert runtime["strongest_rejected_lane"]["timeframe"] == "M5"
    assert runtime["strongest_rejected_lane"]["directional_score"] == 0.31
    assert runtime["strongest_rejected_lane"]["shadow_edge_status"] == "PASS"


def test_scan_candidate_block_reason_rejects_closed_and_emitted_routes(tmp_path):
    open_state = {
        "symbol": "EUR/USD",
        "timeframe": "H1",
        "quote": {
            "bid": 1.1020,
            "ask": 1.1022,
            "is_market_open": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "candles": [
            {
                "timestamp": "2026-07-13T20:00:00+00:00",
                "open": 1.1000,
                "high": 1.1030,
                "low": 1.0990,
                "close": 1.1020,
            }
        ],
    }
    edge = {
        "status": "PASS",
        "has_edge_token": True,
        "threshold": 0.65,
        "candidate_symbol": "EUR/USD",
        "candidate_timeframe": "H1",
        "candidate_direction": "LONG",
        "candidate_entry": 1.1020,
        "candidate_stop_loss": 1.0980,
        "candidate_take_profit": 1.1100,
        "candidate_regime": "directional_pressure",
        "candidate_decision_ref": "waste-dir-eurusd-h1",
    }
    emissions_path = tmp_path / "emissions.json"

    assert (
        policy._scan_candidate_block_reason(
            open_state,
            edge,
            emission_state_path=emissions_path,
            config=None,
        )
        == ""
    )

    route_key = policy._route_key_from_preview(open_state, edge)
    setup = CandidateSetup(
        symbol="EUR/USD",
        timeframe="H1",
        direction="LONG",
        entry=1.1020,
        stop_loss=1.0980,
        take_profit=1.1100,
        signal_strength=0.7,
        regime="directional_pressure",
        decision_ref="waste-dir-eurusd-h1",
    )
    decision = EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.70,
        null_p95=0.55,
        threshold=0.65,
        edge_token="preview-token",
        evaluated_at="2026-07-13T20:30:00+00:00",
        reason="test preview",
    )
    assert route_key == policy._route_key(open_state, setup, decision)
    emissions_path.write_text(
        json.dumps({"emitted_route_keys": [route_key]}),
        encoding="utf-8",
    )
    assert (
        policy._scan_candidate_block_reason(
            open_state,
            edge,
            emission_state_path=emissions_path,
            config=None,
        )
        == "current candle/setup route already emitted"
    )

    closed_state = {
        **open_state,
        "quote": {**open_state["quote"], "is_market_open": False},
    }
    assert "closed" in policy._scan_candidate_block_reason(
        closed_state,
        edge,
        emission_state_path=emissions_path,
        config=None,
    )


def test_live_candle_route_emits_once_per_candle_setup(tmp_path, monkeypatch):
    policy.reset_live_candle_route_cache_for_testing()
    state = {
        "report_kind": "cas_forex_waste_market_state",
        "symbol": "NAS100",
        "timeframe": "H1",
        "broker_grade_market_truth": True,
        "fallback_used": False,
        "source": "MT5TerminalMarketDataConnector",
        "quote": {
            "bid": 28774.96,
            "ask": 28776.08,
            "is_market_open": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "candles": [
            {"timestamp": "2026-07-08T10:00:00+00:00", "open": 28810.0, "high": 28820.0, "low": 28740.0, "close": 28774.96}
        ],
        "entry_pairs": [
            {"signal_strength": -0.55, "direction": "SHORT", "ret": -0.001, "cost_ret": 0.0}
            for _ in range(12)
        ],
        "waste_market_scan": {"status": "WASTE_MARKET_SCAN_PASS_PREVIEW"},
    }
    setup = CandidateSetup(
        symbol="NAS100",
        timeframe="H1",
        direction="SHORT",
        entry=28774.96,
        stop_loss=28982.66,
        take_profit=28498.03,
        signal_strength=-0.55,
        regime="directional_pressure",
        decision_ref="waste-dir-test",
    )
    setattr(setup, "entry_pairs", list(state["entry_pairs"]))

    monkeypatch.setattr(policy, "build_waste_market_state_scan", lambda **kwargs: state)
    monkeypatch.setattr(policy, "analyze_market_state", lambda state: {"confidence": 0.7, "reason": "test"})
    monkeypatch.setattr(policy, "strategize_market_state", lambda state, analysis: setup)
    monkeypatch.setattr(
        policy,
        "evaluate_candidate",
        lambda setup, entry_pairs, threshold: EdgeTestDecision(
            status="PASS",
            measured_win_prob=0.625,
            null_p95=0.05,
            threshold=0.6,
            edge_token="edge-token",
            evaluated_at="2026-07-08T12:00:00+00:00",
            reason="edge confirmed",
        ),
    )

    source_path = tmp_path / "live-candle-source.json"
    emissions_path = tmp_path / "live-candle-emissions.json"
    first = policy.build_live_candle_route_intents(
        source_path=source_path,
        emission_state_path=emissions_path,
        use_cache=False,
    )
    first_status = policy.live_candle_route_invocation_status()
    cached = policy.build_live_candle_route_intents(
        source_path=source_path,
        emission_state_path=emissions_path,
        use_cache=True,
    )
    cached_status = policy.live_candle_route_invocation_status()
    runtime_status = policy.live_candle_route_runtime_status()
    second = policy.build_live_candle_route_intents(
        source_path=source_path,
        emission_state_path=emissions_path,
        use_cache=False,
    )

    assert len(first) == 1
    assert cached == []
    assert second == []
    assert first_status["status"] == "FULL_SCAN_COMPLETED"
    assert first_status["fresh_market_scan_performed"] is True
    assert cached_status["status"] == "SCAN_THROTTLED_CACHE"
    assert cached_status["fresh_market_scan_performed"] is False
    assert cached_status["last_full_scan"]["status"] == "FULL_SCAN_COMPLETED"
    assert runtime_status["full_scan_lane_count"] == 1
    assert runtime_status["broker_execution_touched"] is False
    assert runtime_status["orders_placed"] is False
    intent = first[0]
    assert intent.agent_id == "live_candle_agent"
    assert intent.symbol == "NAS100"
    assert intent.direction == "SHORT"
    assert "measured_hit_rate=0.625" in intent.reason
    assert "win_prob" not in intent.reason
    assert intent.order_request["direction"] == "SHORT"
    assert intent.order_request["take_profit"] < intent.order_request["stop_loss"]
    assert intent.evidence_refs == [str(source_path)]
    assert intent.edge_authorization_ready is True
    assert intent.learning_trade is False
    assert intent._runtime_context["edge"].edge_token == "edge-token"
    serialized_intent = json.dumps(intent.to_dict(), sort_keys=True)
    assert "_runtime_context" not in serialized_intent
    assert "edge-token" not in serialized_intent
    report = json.loads(source_path.read_text(encoding="utf-8"))
    assert report["status"] == "NO_ROUTE"
    assert "current candle/setup route already emitted" in report["blockers"]


def test_non_pass_current_setup_emits_owner_enabled_tokenless_paper_learning(tmp_path, monkeypatch):
    policy.reset_live_candle_route_cache_for_testing()
    state = {
        "symbol": "US30",
        "timeframe": "H1",
        "broker_grade_market_truth": True,
        "fallback_used": False,
        "source": "MT5TerminalMarketDataConnector",
        "quote": {
            "bid": 52575.0,
            "ask": 52577.0,
            "is_market_open": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "candles": [
            {
                "timestamp": "2026-07-10T10:00:00+00:00",
                "open": 52520.0,
                "high": 52610.0,
                "low": 52480.0,
                "close": 52575.0,
            }
        ],
        "entry_pairs": [
            {"signal_strength": -0.9, "direction": "SHORT", "ret": -0.001, "cost_ret": 0.0}
            for _ in range(18)
        ],
        "waste_market_scan": {"status": "WASTE_MARKET_SCAN_PASS_PREVIEW"},
    }
    setup = CandidateSetup(
        symbol="US30",
        timeframe="H1",
        direction="SHORT",
        entry=52575.0,
        stop_loss=52675.0,
        take_profit=52375.0,
        signal_strength=-0.9014,
        regime="compressed_range_extension",
        decision_ref="waste-dir-current-learning",
    )
    setattr(setup, "entry_pairs", list(state["entry_pairs"]))

    class _Control:
        def get(self, name):
            return {"edge_threshold": 0.6, "paper_learning_trades": 1}[name]

    authority = SimpleNamespace(control=_Control())
    refused = EdgeTestDecision(
        status="NO_TRADE_NULL_FAILED",
        measured_win_prob=0.6111,
        null_p95=0.008,
        threshold=0.6,
        edge_token=None,
        evaluated_at="2026-07-10T10:01:00+00:00",
        reason="net return did not beat random-direction null",
    )
    monkeypatch.setattr(policy, "build_waste_market_state_scan", lambda **kwargs: state)
    monkeypatch.setattr(policy, "analyze_market_state", lambda state: {"confidence": 0.9014})
    monkeypatch.setattr(policy, "strategize_market_state", lambda state, analysis: setup)
    monkeypatch.setattr(policy, "evaluate_candidate", lambda setup, pairs, threshold: refused)

    source = tmp_path / "paper-learning-source.json"
    emitted = policy.build_live_candle_route_intents(
        authority=authority,
        config=SimpleNamespace(live_mode=False, paper_trading=True),
        source_path=source,
        emission_state_path=tmp_path / "paper-learning-emissions.json",
        use_cache=False,
    )

    assert len(emitted) == 1
    intent = emitted[0]
    assert intent.action == "OPEN_LIVE_CANDLE_LEARNING"
    assert intent.direction == "SHORT"
    assert intent.learning_trade is True
    assert intent.edge_authorization_ready is False
    assert intent.edge_label["status"] == "NO_TRADE_NULL_FAILED"
    assert intent.order_request["decision_ref"] == "waste-dir-current-learning"
    assert intent.order_request["order_id"] == "waste-waste-dir-current-learning"
    assert "no edge token carried" in intent.reason
    report = json.loads(source.read_text(encoding="utf-8"))
    assert report["status"] == "PAPER_LEARNING_ROUTE_EMITTED"
    assert report["paper_learning_allowed"] is True
    assert report["learning_trade_emitted"] is True


def test_non_pass_learning_route_is_never_formed_for_live_runtime(tmp_path, monkeypatch):
    policy.reset_live_candle_route_cache_for_testing()
    state = {
        "symbol": "US30",
        "timeframe": "H1",
        "broker_grade_market_truth": True,
        "fallback_used": False,
        "source": "MT5TerminalMarketDataConnector",
        "candles": [{"timestamp": "2026-07-10T10:00:00+00:00", "close": 52575.0}],
        "entry_pairs": [{"direction": "SHORT", "ret": -0.001} for _ in range(12)],
    }
    setup = CandidateSetup(
        symbol="US30",
        timeframe="H1",
        direction="SHORT",
        entry=52575.0,
        stop_loss=52675.0,
        take_profit=52375.0,
        signal_strength=-0.9,
        regime="range",
        decision_ref="waste-dir-live-refused",
    )
    setattr(setup, "entry_pairs", list(state["entry_pairs"]))

    class _Control:
        def get(self, name):
            return {"edge_threshold": 0.6, "paper_learning_trades": 1}[name]

    refused = EdgeTestDecision(
        status="NO_TRADE_NULL_FAILED",
        measured_win_prob=0.6,
        null_p95=0.01,
        threshold=0.6,
        edge_token=None,
        evaluated_at="2026-07-10T10:01:00+00:00",
        reason="null failed",
    )
    monkeypatch.setattr(policy, "build_waste_market_state_scan", lambda **kwargs: state)
    monkeypatch.setattr(policy, "analyze_market_state", lambda state: {"confidence": 0.9})
    monkeypatch.setattr(policy, "strategize_market_state", lambda state, analysis: setup)
    monkeypatch.setattr(policy, "evaluate_candidate", lambda setup, pairs, threshold: refused)

    source = tmp_path / "live-no-learning-source.json"
    intents = policy.build_live_candle_route_intents(
        authority=SimpleNamespace(control=_Control()),
        config=SimpleNamespace(live_mode=True, paper_trading=True),
        source_path=source,
        emission_state_path=tmp_path / "live-no-learning-emissions.json",
        use_cache=False,
    )

    assert intents == []
    report = json.loads(source.read_text(encoding="utf-8"))
    assert report["status"] == "NO_ROUTE"
    assert report["paper_learning_allowed"] is False
    assert any("edge gate NO_TRADE_NULL_FAILED" in reason for reason in report["blockers"])


def test_closed_quote_cannot_consume_one_shot_route_identity(tmp_path, monkeypatch):
    policy.reset_live_candle_route_cache_for_testing()
    state = {
        "symbol": "EUR/USD",
        "timeframe": "M1",
        "broker_grade_market_truth": True,
        "fallback_used": False,
        "source": "MT5TerminalMarketDataConnector",
        "quote": {
            "bid": 1.0849,
            "ask": 1.0851,
            "is_market_open": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "candles": [
            {
                "timestamp": "2026-07-10T09:00:00+00:00",
                "open": 1.0850,
                "high": 1.0860,
                "low": 1.0840,
                "close": 1.0850,
            }
        ],
        "entry_pairs": [{"direction": "SHORT", "ret": -0.001} for _ in range(12)],
    }
    setup = CandidateSetup(
        symbol="EUR/USD",
        timeframe="M1",
        direction="SHORT",
        entry=1.0850,
        stop_loss=1.0865,
        take_profit=1.0830,
        signal_strength=-0.8,
        regime="short_horizon_momentum",
        decision_ref="waste-dir-closed-scalp",
    )
    setattr(setup, "entry_pairs", list(state["entry_pairs"]))

    class _Control:
        def get(self, name):
            return {"edge_threshold": 0.6, "paper_learning_trades": 1}[name]

    monkeypatch.setattr(policy, "build_waste_market_state_scan", lambda **kwargs: state)
    monkeypatch.setattr(policy, "analyze_market_state", lambda state: {"confidence": 0.8})
    monkeypatch.setattr(policy, "strategize_market_state", lambda state, analysis: setup)
    monkeypatch.setattr(
        policy,
        "evaluate_candidate",
        lambda *args, **kwargs: EdgeTestDecision(
            status="NO_TRADE_NULL_FAILED",
            measured_win_prob=0.55,
            null_p95=0.02,
            threshold=0.6,
            edge_token=None,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            reason="paper sample would otherwise be eligible",
        ),
    )
    source = tmp_path / "closed-source.json"
    emissions = tmp_path / "closed-emissions.json"

    intents = policy.build_live_candle_route_intents(
        authority=SimpleNamespace(control=_Control()),
        config=SimpleNamespace(live_mode=False, paper_trading=True),
        timeframe="M1",
        source_path=source,
        emission_state_path=emissions,
        use_cache=False,
    )

    assert intents == []
    assert emissions.exists() is False
    report = json.loads(source.read_text(encoding="utf-8"))
    assert report["route_key"] is None
    assert report["entry_lane"] == "MICRO_SCALP"
    assert "current broker quote reports the market or symbol is closed" in report["blockers"]


def test_forming_h1_candle_cannot_create_a_new_route_each_refresh(tmp_path, monkeypatch):
    policy.reset_live_candle_route_cache_for_testing()
    now = datetime(2026, 7, 10, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(policy, "utc_now", lambda: now)
    forming_close = {"value": 52_600.0}

    def scan(**kwargs):
        return {
            "symbol": "US30",
            "timeframe": "H1",
            "broker_grade_market_truth": True,
            "fallback_used": False,
            "source": "MT5TerminalMarketDataConnector",
            "quote": {
                "bid": 52_574.0,
                "ask": 52_576.0,
                "is_market_open": True,
                "timestamp": now.isoformat(),
            },
            "candles": [
                {
                    "timestamp": "2026-07-10T09:00:00+00:00",
                    "open": 52_500.0,
                    "high": 52_610.0,
                    "low": 52_480.0,
                    "close": 52_575.0,
                },
                {
                    "timestamp": "2026-07-10T10:00:00+00:00",
                    "open": 52_575.0,
                    "high": 52_620.0,
                    "low": 52_550.0,
                    "close": forming_close["value"],
                },
            ],
            "entry_pairs": [{"direction": "SHORT", "ret": -0.001} for _ in range(12)],
        }

    analyzed_closes: list[float] = []

    def analyze(state):
        analyzed_closes.append(float(state["candles"][-1]["close"]))
        return {"confidence": 0.8}

    def strategize(state, analysis):
        setup = CandidateSetup(
            symbol="US30",
            timeframe="H1",
            direction="SHORT",
            entry=float(state["candles"][-1]["close"]),
            stop_loss=52_675.0,
            take_profit=52_375.0,
            signal_strength=-0.8,
            regime="range",
            decision_ref="waste-dir-completed-h1",
        )
        setattr(setup, "entry_pairs", list(state["entry_pairs"]))
        return setup

    monkeypatch.setattr(policy, "build_waste_market_state_scan", scan)
    monkeypatch.setattr(policy, "analyze_market_state", analyze)
    monkeypatch.setattr(policy, "strategize_market_state", strategize)
    monkeypatch.setattr(
        policy,
        "evaluate_candidate",
        lambda *args, **kwargs: EdgeTestDecision(
            status="PASS",
            measured_win_prob=0.7,
            null_p95=0.01,
            threshold=0.6,
            edge_token="one-shot",
            evaluated_at=now.isoformat(),
            reason="test edge",
        ),
    )
    source = tmp_path / "completed-candle-source.json"
    emissions = tmp_path / "completed-candle-emissions.json"

    first = policy.build_live_candle_route_intents(
        source_path=source,
        emission_state_path=emissions,
        use_cache=False,
    )
    forming_close["value"] = 52_612.0
    second = policy.build_live_candle_route_intents(
        source_path=source,
        emission_state_path=emissions,
        use_cache=False,
    )

    assert len(first) == 1
    assert second == []
    assert analyzed_closes == [52_575.0, 52_575.0]
    report = json.loads(source.read_text(encoding="utf-8"))
    assert report["candle_completion"]["decision_candle_timestamp"] == (
        "2026-07-10T09:00:00+00:00"
    )
    assert report["candle_completion"]["forming_or_invalid_candle_count"] == 1
    assert "current candle/setup route already emitted" in report["blockers"]


def test_m1_m5_use_fresh_micro_scalp_identity_and_independent_caches(tmp_path, monkeypatch):
    policy.reset_live_candle_route_cache_for_testing()
    scans: list[str] = []

    def scan(**kwargs):
        timeframe = str(kwargs["timeframe"])
        scans.append(timeframe)
        return {
            "symbol": "EUR/USD",
            "timeframe": timeframe,
            "broker_grade_market_truth": True,
            "fallback_used": False,
            "source": "MT5TerminalMarketDataConnector",
            "quote": {
                "bid": 1.0849,
                "ask": 1.0851,
                "is_market_open": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "candles": [
                {
                    "timestamp": "2026-07-10T09:00:00+00:00",
                    "open": 1.0850,
                    "high": 1.0860,
                    "low": 1.0840,
                    "close": 1.0850,
                }
            ],
            "entry_pairs": [
                {"direction": "SHORT", "ret": -0.001, "cost_ret": 0.0001}
                for _ in range(12)
            ],
        }

    def strategize(state, analysis):
        timeframe = str(state["timeframe"])
        direction = "SHORT" if timeframe == "M1" else "LONG"
        setup = CandidateSetup(
            symbol="EUR/USD",
            timeframe=timeframe,
            direction=direction,
            entry=1.0850,
            stop_loss=1.0865 if direction == "SHORT" else 1.0835,
            take_profit=1.0830 if direction == "SHORT" else 1.0870,
            signal_strength=-0.8 if direction == "SHORT" else 0.8,
            regime="short_horizon_momentum",
            decision_ref=f"waste-dir-{timeframe.lower()}-fresh",
        )
        setattr(setup, "entry_pairs", list(state["entry_pairs"]))
        return setup

    monkeypatch.setattr(policy, "build_waste_market_state_scan", scan)
    monkeypatch.setattr(policy, "analyze_market_state", lambda state: {"confidence": 0.8})
    monkeypatch.setattr(policy, "strategize_market_state", strategize)
    monkeypatch.setattr(
        policy,
        "evaluate_candidate",
        lambda *args, **kwargs: EdgeTestDecision(
            status="PASS",
            measured_win_prob=0.7,
            null_p95=0.02,
            threshold=0.6,
            edge_token="fresh-one-shot",
            evaluated_at="2026-07-10T09:02:00+00:00",
            reason="cost-aware short-horizon edge confirmed",
        ),
    )
    emissions = tmp_path / "emissions.json"

    m1 = policy.build_live_candle_route_intents(
        timeframe="M1",
        source_path=tmp_path / "m1-source.json",
        emission_state_path=emissions,
        use_cache=True,
    )
    m5 = policy.build_live_candle_route_intents(
        timeframe="M5",
        source_path=tmp_path / "m5-source.json",
        emission_state_path=emissions,
        use_cache=True,
    )
    cached_m1 = policy.build_live_candle_route_intents(
        timeframe="M1",
        source_path=tmp_path / "m1-source.json",
        emission_state_path=emissions,
        use_cache=True,
    )

    assert scans == ["M1", "M5"]
    assert cached_m1 == []
    assert len(m1) == len(m5) == 1
    assert m1[0].agent_id == "micro_scalp_agent"
    assert m1[0].action == "OPEN_MICRO_SCALP_EDGE"
    assert m1[0].direction == "SHORT"
    assert m1[0].order_request["comment"] == "CAS_MICRO_SCALP"
    assert m1[0].strategy_setting.startswith("micro_scalp_")
    assert m1[0]._runtime_context["entry_lane"] == "MICRO_SCALP"
    assert m5[0].agent_id == "micro_scalp_agent"
    assert m5[0].direction == "LONG"
    report = json.loads((tmp_path / "m1-source.json").read_text(encoding="utf-8"))
    assert report["entry_lane"] == "MICRO_SCALP"
