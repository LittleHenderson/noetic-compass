from cas_forex.ai_operator import (
    _compact_mt5_symbol_diagnostic,
    _local_chat_reply,
    _operator_briefing_context,
    _should_answer_chat_locally_first,
)


def test_operator_local_chat_reports_tick_context_integrity():
    context = {
        "operator_tick_context_delivery": {
            "status": "DECISION_GRADE_CONTEXT",
            "decision_grade": True,
            "critical_sections_present": ["profit_and_balance", "learning_outcomes"],
            "critical_section_count": 2,
            "critical_sections_missing": [],
            "packet_json_chars": 20813,
            "source_context_chars": 61640,
            "blind_character_slice_used": False,
            "evidence_fingerprint": "abc123def456",
        }
    }

    reply = _local_chat_reply(
        "was the Operator evidence packet truncated?",
        context,
        model_attempted=False,
    )

    assert "status=DECISION_GRADE_CONTEXT" in reply
    assert "decision_grade=True" in reply
    assert "critical=2/2" in reply
    assert "packet_chars=20813" in reply
    assert "source_chars=61640" in reply
    assert "blind_character_slice=False" in reply
    assert "fingerprint=abc123def456" in reply
    assert "directly from the local CAS runtime" in reply
    assert "model path could not be started" not in reply.lower()
    assert _should_answer_chat_locally_first("was the Operator evidence packet truncated?")


def test_operator_local_chat_mentions_unresolved_mt5_symbol_diagnostic():
    context = {
        "trade_path_diagnostics": {
            "dispatch_loop": {"running": True, "mode": "PAPER", "last_summary": "watching"},
            "mt5_symbol_diagnostic": {
                "available": True,
                "symbols": [
                    {
                        "symbol": "NAS100",
                        "status": "NO_BROKER_GRADE_CANDLES",
                        "selected_broker_symbol": None,
                        "detail": "MT5 symbol unresolved for NAS100",
                    }
                ],
            },
        }
    }

    reply = _local_chat_reply("what is wrong with the broker symbol map?", context, model_attempted=False)

    assert "MT5 symbol diagnostic needs attention" in reply
    assert "NAS100 NO_BROKER_GRADE_CANDLES" in reply
    assert "selected broker symbol none" in reply


def test_operator_local_chat_mentions_ready_mt5_symbol_map():
    context = {
        "trade_path_diagnostics": {
            "mt5_symbol_diagnostic": {
                "available": True,
                "symbols": [
                    {
                        "symbol": "NAS100",
                        "status": "BROKER_TRUTH_READY",
                        "selected_broker_symbol": "NAS100.pro",
                    },
                    {
                        "symbol": "US30",
                        "status": "BROKER_TRUTH_READY",
                        "selected_broker_symbol": "US30.cash",
                    },
                ],
            },
        }
    }

    reply = _local_chat_reply("show me the broker symbol mapping", context, model_attempted=False)

    assert "MT5 symbol map is ready" in reply
    assert "NAS100->NAS100.pro" in reply
    assert "US30->US30.cash" in reply


def test_operator_chat_explains_completed_candle_learning_and_voided_incident():
    context = {
        "trade_path_diagnostics": {
            "dispatch_loop": {
                "running": True,
                "requested_mode": "LIVE",
                "execution_lane": "PAPER",
                "mode": "PAPER_FALLBACK",
                "last_summary": "intents=0 executed=0",
            },
            "live_candle_route_source": {
                "available": True,
                "status": "NO_ROUTE",
                "symbol": "US30",
                "paper_learning_allowed": True,
                "setup": {"direction": "SHORT"},
                "edge": {
                    "status": "NO_TRADE_NULL_FAILED",
                    "measured_win_prob": 0.6111,
                },
                "candle_completion": {
                    "decision_candle_timestamp": "2026-07-10T10:00:00+00:00",
                    "completed_candle_count": 299,
                    "forming_or_invalid_candle_count": 1,
                },
            },
            "route_filter": {
                "available": True,
                "filtered_count": 2,
                "filtered": [{"symbol": "AUD/CAD"}],
            },
            "paper_execution": {
                "available": True,
                "open_position_count": 1,
                "forming_candle_incident_void_count": 10,
                "invalidated_outcome_count": 1,
                "positions": [
                    {
                        "broker_ticket": "923871908",
                        "symbol": "US30",
                        "direction": "SHORT",
                        "volume": 0.01,
                        "fill_price": 52582.49,
                        "stop_loss": 52661.0,
                        "take_profit": 52477.0,
                    }
                ],
            },
        }
    }

    reply = _local_chat_reply(
        "why hasn't the Operator made another trade?",
        context,
        model_attempted=False,
    )

    assert "decision_candle=2026-07-10T10:00:00+00:00" in reply
    assert "forming_or_invalid_excluded=1" in reply
    assert "non-PASS PAPER learning label" in reply
    assert "Replay-template quarantine is active" in reply
    assert "open_positions=1" in reply
    assert "voided_incident_positions=10" in reply
    assert "ticket=923871908 US30 SHORT 0.01 lots" in reply


def test_operator_chat_explains_mt5_demo_handoff_and_learning_sync():
    context = {
        "trade_path_diagnostics": {
            "dispatch_loop": {
                "running": True,
                "requested_mode": "LIVE",
                "execution_lane": "PAPER",
                "mode": "PAPER_FALLBACK",
                "paper_fallback_active": True,
                "last_bridge_class": "MT5Bridge",
                "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
                "last_management_primary_position_count": 1,
                "last_management_simulator_handoff_position_count": 1,
                "last_mt5_demo_learning_sync_status": "MT5_DEMO_LEARNING_SYNCED",
                "last_mt5_demo_learning_history_count": 4,
                "last_mt5_demo_learning_bound_trade_count": 2,
                "last_mt5_demo_learning_sync_error": None,
                "last_operator_trade_edge_status": "AI_OPERATOR_DECIDED",
                "last_operator_trade_edge_provider": "claude",
                "last_operator_trade_edge_candidate_count": 2,
                "last_operator_trade_edge_approved_count": 1,
                "last_operator_trade_edge_stand_down_count": 1,
                "last_operator_trade_edge_summary": "Approved NAS100; stood down US30.",
            }
        }
    }

    reply = _local_chat_reply(
        "is MT5 demo execution and learning working?",
        context,
        model_attempted=False,
    )

    assert "bridge=MT5Bridge" in reply
    assert "legacy_simulator_positions=1" in reply
    assert "older simulator positions remain managed" in reply
    assert "status=MT5_DEMO_LEARNING_SYNCED" in reply
    assert "closed_history=4" in reply
    assert "bound_learning_trades=2" in reply
    assert "status=AI_OPERATOR_DECIDED" in reply
    assert "provider=claude" in reply
    assert "approved=1" in reply
    assert "stood_down=1" in reply


def test_operator_compacts_latest_market_data_symbol_resolution():
    compact = _compact_mt5_symbol_diagnostic(
        {
            "status": "MT5_MARKET_DATA_READY",
            "ready_symbol_count": 1,
            "checked_symbol_count": 1,
            "symbols": [
                {
                    "symbol": "NAS100",
                    "status": "BROKER_TRUTH_READY",
                    "selected_broker_symbol": "NAS100.pro",
                    "symbol_resolution": {"resolution_source": "BROKER_SYMBOL_DISCOVERY"},
                }
            ],
        }
    )

    assert compact["available"] is True
    assert compact["symbols"][0]["selected_broker_symbol"] == "NAS100.pro"
    assert compact["symbols"][0]["resolution_source"] == "BROKER_SYMBOL_DISCOVERY"


def test_symbol_contract_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("what is the min lot and lot step for NAS100?")


def test_operator_local_chat_reports_account_health_metrics():
    context = {
        "account_health": {
            "status": "ATTENTION",
            "blockers": ["One or more open positions has no visible stop loss."],
            "account": {
                "balance_usd": 1080.0,
                "equity_usd": 1095.0,
                "free_margin_usd": 900.0,
                "realized_pnl_usd": 80.0,
                "floating_pnl_usd": 15.0,
                "drawdown_pct": 0.0,
            },
            "closed_trade_performance": {
                "closed_trade_count": 2,
                "win_rate_pct": 50.0,
                "profit_factor": 3.0,
                "profit_factor_state": "CALCULATED",
                "expectancy_usd": 40.0,
            },
            "open_exposure": {
                "open_position_count": 2,
                "open_lots": 0.12,
                "unprotected_position_count": 1,
                "protective_order_coverage_pct": 50.0,
                "open_risk_estimate_usd": 25.0,
            },
            "source_health": {
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "broker_ticket_position_count": 0,
                "simulator_position_count": 2,
                "provider_priced_simulator_position_count": 0,
                "static_simulator_position_count": 2,
                "stale_price_position_count": 2,
                "static_fallback_symbols": ["NAS100", "US30"],
                "attention_required": True,
                "position_feed_detail": "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. Static simulator fallback is active for 2/2 row(s), so prices and floating P&L can remain at entry until usable provider or MT5 quotes arrive. Static fallback symbols: NAS100, US30.",
                "detail": "Static rows can sit at entry price until provider/MT5 prices are usable.",
            },
        }
    }

    reply = _local_chat_reply("what is the win rate, profit factor, and protection?", context, model_attempted=False)

    assert "Account health: status=ATTENTION" in reply
    assert "Closed-trade metrics: 2 closed, win rate 50.0%, profit factor 3.00" in reply
    assert "Open exposure: 2 open, 0.12 lots, protected 50.0%, unprotected=1" in reply
    assert "Position source health: price_source_status=STATIC_SIMULATION_FALLBACK" in reply
    assert "static=2, stale=2" in reply
    assert "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions." in reply
    assert "Static fallback symbols: NAS100, US30" in reply
    assert "Account health blockers" in reply


def test_operator_local_chat_explains_static_simulation_when_floating_pnl_is_flat():
    context = {
        "live_mt5": {
            "connected": False,
            "detail": "MT5 snapshot is unavailable.",
        },
        "account_health": {
            "status": "ATTENTION",
            "account": {
                "balance_usd": 5000.0,
                "equity_usd": 5000.0,
                "realized_pnl_usd": 0.0,
            },
            "source_health": {
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "broker_ticket_position_count": 0,
                "simulator_position_count": 2,
                "provider_priced_simulator_position_count": 0,
                "static_simulator_position_count": 2,
                "stale_price_position_count": 2,
                "configured_market_data_provider": "YFinanceConnector",
                "static_fallback_symbols": ["NAS100", "US30"],
                "detail": "Static rows can sit at entry price until provider/MT5 prices are usable.",
            },
        },
    }

    reply = _local_chat_reply("why hasn't the floating P&L changed in 24 hours?", context, model_attempted=False)

    assert "MT5 is not producing a connected live snapshot right now" in reply
    assert "static simulator proof rows, not live MT5 terminal positions" in reply
    assert "floating P&L can sit at entry until provider/MT5 quotes are usable" in reply


def test_operator_local_chat_reports_stale_provider_rejections_for_flat_pnl():
    context = {
        "live_mt5": {
            "connected": False,
            "detail": "MT5 snapshot is unavailable.",
        },
        "account_health": {
            "status": "ATTENTION",
            "account": {
                "balance_usd": 5000.0,
                "equity_usd": 5000.0,
                "realized_pnl_usd": 0.0,
            },
            "source_health": {
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "broker_ticket_position_count": 0,
                "simulator_position_count": 1,
                "provider_priced_simulator_position_count": 0,
                "static_simulator_position_count": 1,
                "stale_price_position_count": 1,
                "configured_market_data_provider": "Yahoo",
                "provider_stale_symbols": ["NAS100"],
                "provider_freshness_max_age_seconds": 900,
                "price_source_warning": "Static simulator rows are not being moved by usable provider/MT5 quotes right now; prices and floating P/L can remain unchanged at entry.",
                "detail": "Static rows can sit at entry price until provider/MT5 prices are usable.",
            },
        },
    }

    reply = _local_chat_reply("why hasn't the floating P&L changed in 24 hours?", context, model_attempted=False)

    assert "Static simulator rows are not being moved by usable provider/MT5 quotes right now" in reply
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in reply


def test_operator_local_chat_reports_clustered_signal_quality():
    context = {
        "profit_and_balance": {
            "balance_growth_net_pnl_usd": 480.0,
            "raw_trades": 12,
            "honest_unique_signal_net_pnl_usd": 165.0,
            "unique_signals": 4,
            "cluster_inflation_x": 3.0,
            "biggest_cluster_size": 5,
            "avg_winning_stack_depth": 2.5,
            "avg_losing_stack_depth": 2.5,
            "stacking_is_blind": True,
        }
    }

    reply = _local_chat_reply("is the profit inflated by clustered duplicate trades?", context, model_attempted=False)

    assert "Signal quality: balance-growth P&L $480.00 across 12 raw trades" in reply
    assert "de-clustered evidence $165.00 across 4 unique signals" in reply
    assert "Cluster inflation 3.00x, biggest copy stack 5" in reply
    assert "avg win stack 2.50, avg loss stack 2.50." in reply
    assert "Blind stacking warning: losers are stacking as deep as winners" in reply


def test_profit_factor_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("what is the current profit factor and win rate?")


def test_stale_price_source_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("why are these simulator prices static and stale?")


def test_cluster_signal_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("are these duplicate clustered wins or independent signals?")


def test_broker_truth_paper_force_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("why is broker truth paper force active?")


def test_operator_local_chat_reports_broker_truth_monitor_paper_force():
    context = {
        "broker_truth_monitor": {
            "available": True,
            "monitor_status": "BROKER_TRUTH_RECONCILIATION_FAILED",
            "ready_for_live": False,
            "auto_halt_latched_from_monitor": True,
            "monitor_auto_halt_reason_summary": "Stop-Loss Protection, Terminal Reconciliation",
            "position_protection_label": "UNPROTECTED POSITIONS",
            "position_protection_unprotected_position_count": 2,
            "position_protection_detail": "2 broker-visible live positions have no stop-loss protection.",
            "mt5_connected": True,
            "mt5_is_demo": False,
            "mt5_open_position_count": 2,
            "next_action": "Keep paper force active until broker truth clears.",
        }
    }

    reply = _local_chat_reply("why is broker truth paper force active?", context, model_attempted=False)

    assert "Broker truth monitor: status=BROKER_TRUTH_RECONCILIATION_FAILED" in reply
    assert "ready_for_live=False" in reply
    assert "paper_force_latched=True" in reply
    assert "reasons=Stop-Loss Protection, Terminal Reconciliation" in reply
    assert "position_protection=UNPROTECTED POSITIONS" in reply
    assert "unprotected_positions=2" in reply
    assert "Position protection detail: 2 broker-visible live positions have no stop-loss protection." in reply
    assert "Next broker-truth action: Keep paper force active until broker truth clears." in reply


def test_operator_local_chat_reports_trade_explanation_card():
    context = {
        "trade_path_diagnostics": {
            "latest_dispatch": {
                "available": True,
                "results": [
                    {
                        "symbol": "EUR/USD",
                        "status": "EXECUTED",
                        "reason": "Edge token passed and broker bridge accepted the paper order.",
                        "trade_explanation_card": {
                            "summary": "Edge token passed and broker bridge accepted the paper order.",
                            "protective_orders": {
                                "status": "PROTECTED",
                                "stop_loss": 1.0812,
                                "take_profit": 1.0902,
                            },
                            "money_impact": {
                                "broker_bridge_touched": True,
                                "order_executed": True,
                                "real_broker": False,
                                "summary": "Paper/demo bridge reported an executed order; no external money movement.",
                            },
                            "live_gate_report": {
                                "overall_status": "PASSED",
                                "blocking_stage": None,
                            },
                            "gate_trace": [
                                {"stage": "market_availability", "status": "PASSED"},
                                {"stage": "risk_engine", "status": "NOT_BLOCKING_THIS_RESULT"},
                                {"stage": "broker_bridge", "status": "EXECUTED"},
                            ],
                        },
                    }
                ],
            }
        }
    }

    reply = _local_chat_reply("show me the latest dispatch gate trace", context, model_attempted=False)

    assert "Latest dispatch result: EUR/USD EXECUTED" in reply
    assert "Trade explanation card: summary=Edge token passed" in reply
    assert "protection=PROTECTED SL=1.0812 TP=1.0902" in reply
    assert "money impact=Paper/demo bridge reported an executed order" in reply
    assert "market_availability=PASSED" in reply
    assert "broker_bridge=EXECUTED" in reply


def test_operator_local_chat_reports_broker_truth_evidence_for_blocked_live_dispatch():
    context = {
        "trade_path_diagnostics": {
            "latest_dispatch": {
                "available": True,
                "results": [
                    {
                        "symbol": "EUR/USD",
                        "status": "BLOCKED_LIVE_GATE",
                        "reason": "Fresh broker truth is required before real dispatch.",
                        "trade_explanation_card": {
                            "summary": "Fresh broker truth is required before real dispatch.",
                            "protective_orders": {"status": "PROTECTED", "stop_loss": 1.0812, "take_profit": 1.0902},
                            "money_impact": {
                                "broker_bridge_touched": False,
                                "order_executed": False,
                                "real_broker": False,
                                "summary": "No broker bridge was touched; no order was placed.",
                            },
                            "live_gate_report": {
                                "overall_status": "BLOCKED",
                                "blocking_stage": "broker_truth",
                            },
                            "live_readiness_evidence": {
                                "broker_truth": {
                                    "overall_status": "RECONCILIATION_FAILED",
                                    "mt5_connected": True,
                                    "mt5_is_demo": False,
                                    "mt5_open_position_count": 2,
                                    "terminal_unmatched_open_position_count": 1,
                                    "terminal_unattributed_open_position_count": 1,
                                    "terminal_memory_gap_open_position_count": 0,
                                    "cas_memory_only_open_position_count": 0,
                                    "cas_receipt_pending_open_position_count": 1,
                                    "terminal_unmatched_history_count": 1,
                                    "terminal_unattributed_history_count": 1,
                                    "terminal_attributed_history_memory_gap_count": 0,
                                    "terminal_pending_receipt_count": 1,
                                }
                            },
                            "gate_trace": [
                                {"stage": "live_gate", "status": "PASSED"},
                                {"stage": "broker_truth", "status": "BLOCKED"},
                            ],
                        },
                    }
                ],
            }
        }
    }

    reply = _local_chat_reply("why was the latest dispatch blocked by broker truth?", context, model_attempted=False)

    assert "Latest dispatch result: EUR/USD BLOCKED_LIVE_GATE" in reply
    assert "broker_truth=BLOCKED" in reply
    assert "Live readiness evidence: broker truth status=RECONCILIATION_FAILED" in reply
    assert "unmatched=1" in reply
    assert "pending_receipts=1" in reply
    assert "unattributed_broker_positions=1" in reply
    assert "unmatched_history=1" in reply
    assert "unattributed_history=1" in reply


def test_operator_local_chat_reports_mt5_terminal_evidence_for_blocked_live_dispatch():
    context = {
        "trade_path_diagnostics": {
            "latest_dispatch": {
                "available": True,
                "results": [
                    {
                        "symbol": "EUR/USD",
                        "status": "BLOCKED_LIVE_GATE",
                        "reason": "MT5 order_send is blocked before CAS can submit: MT5 Algo Trading is off in the terminal.",
                        "trade_explanation_card": {
                            "summary": "MT5 order_send is blocked before CAS can submit: MT5 Algo Trading is off in the terminal.",
                            "protective_orders": {"status": "PROTECTED", "stop_loss": 1.0812, "take_profit": 1.0902},
                            "money_impact": {
                                "broker_bridge_touched": False,
                                "order_executed": False,
                                "real_broker": False,
                                "summary": "No broker bridge was touched; no order was placed.",
                            },
                            "live_gate_report": {
                                "overall_status": "BLOCKED",
                                "blocking_stage": "mt5_terminal_permissions",
                            },
                            "live_readiness_evidence": {
                                "mt5_terminal_permissions": {
                                    "connected": True,
                                    "is_demo": False,
                                    "account": {
                                        "login": 12345,
                                        "server": "HugosWay-Live",
                                    },
                                    "permission_state": {
                                        "status": "MT5_ORDER_SEND_BLOCKED",
                                        "can_submit_order_send": False,
                                        "blockers": ["MT5 Algo Trading is off in the terminal."],
                                    },
                                }
                            },
                            "gate_trace": [
                                {"stage": "live_gate", "status": "PASSED"},
                                {"stage": "mt5_terminal_permissions", "status": "BLOCKED"},
                            ],
                        },
                    }
                ],
            }
        }
    }

    reply = _local_chat_reply("why was the latest dispatch blocked by the MT5 terminal?", context, model_attempted=False)

    assert "Latest dispatch result: EUR/USD BLOCKED_LIVE_GATE" in reply
    assert "mt5_terminal_permissions=BLOCKED" in reply
    assert "Live readiness evidence: MT5 terminal connected=True" in reply
    assert "login=12345" in reply
    assert "server=HugosWay-Live" in reply
    assert "can_submit_order_send=False" in reply


def test_operator_local_chat_reports_psychology_guard_state():
    context = {
        "psychology_guard": {
            "available": True,
            "ai_dial": {
                "cooldown_active": True,
                "cooldown_remaining_seconds": 540,
                "recent_loosen_count": 3,
                "loosen_warning_limit": 6,
                "warning_active": False,
                "journal_prompt": "Explain why widening the AI dial is not revenge or FOMO.",
            },
            "risk_caps": {
                "real_money_controls_armed": True,
                "typed_confirmation_required_on_loosen": True,
                "journal_required_on_loosen": True,
                "would_block_new_loosening": True,
                "cooldown_active": True,
                "cooldown_remaining_seconds": 900,
                "journal_prompt": "Explain why loosening live risk is not revenge trading.",
            },
        }
    }

    reply = _local_chat_reply("are the revenge or FOMO guards cooling down right now?", context, model_attempted=False)

    assert "Psychology guard: AI dial cooldown=ACTIVE 9m" in reply
    assert "risk-cap loosening cooldown=ACTIVE 15m" in reply
    assert "typed confirmation=REQUIRED" in reply
    assert "anti-impulse journal=REQUIRED" in reply
    assert "Another risk-cap loosening would be blocked right now" in reply


def test_operator_local_chat_reports_emergency_control_state():
    context = {
        "auto_halt": {
            "available": True,
            "status": "AUTO_HALT_ACTIVE",
            "halt_active": True,
            "force_paper_mode": True,
            "active_reasons": ["MANUAL_EMERGENCY_STOP"],
            "triggered_checks": ["manual_emergency_stop"],
        },
        "emergency_controls": {
            "available": True,
            "status": "OK",
            "automation_stop_ok": True,
            "broker_exposure_gap": False,
            "recommended_terminal_actions": [
                "Keep MT4/MT5 visible when automation is running.",
                "For urgent existing-position management, use the broker terminal until a tested app-level flatten/cancel route is added.",
            ],
            "controls": [
                {"key": "broker_close_all_positions", "status": "OK"},
                {"key": "selective_close_profitable_positions", "status": "OK"},
                {"key": "selective_close_losing_positions", "status": "OK"},
                {"key": "broker_cancel_pending_orders", "status": "OK"},
            ],
        },
    }

    reply = _local_chat_reply("what does the emergency stop do and can I close all positions?", context, model_attempted=False)

    assert "Emergency state: auto-halt=AUTO_HALT_ACTIVE, halt_active=True, force_paper_mode=True" in reply
    assert "reasons=MANUAL_EMERGENCY_STOP, triggered_checks=manual_emergency_stop." in reply
    assert "Emergency controls: status=OK, automation_stop_ok=True, broker_exposure_gap=False." in reply
    assert "Manual emergency stop blocks new automated dispatch only; it does not close existing broker positions." in reply
    assert "Broker emergency actions: close_all=OK, close_profitable=OK, close_losing=OK, cancel_pending=OK." in reply


def test_operator_local_chat_reports_critical_notification_state():
    context = {
        "critical_notifications": {
            "available": True,
            "delivery_status": "CONFIGURED_NOT_TESTED",
            "offscreen_delivery_status": "CONFIGURED_NOT_TESTED",
            "local_in_app_status": "ACTIVE",
            "visible_warning_or_alert_count": 1,
            "subscription_count": 1,
            "recent_dispatch_success_count": 0,
            "recent_dispatch_attempt_count": 0,
            "blockers": ["Webhook destination exists, but no recent critical notification delivery attempt is recorded."],
            "next_action": "Send a critical alert test and verify delivery before relying on off-screen alerts.",
            "latest_event_kind": "UNPROTECTED_POSITION",
            "latest_event_title": "Unprotected position",
            "latest_event_body": "One open position has no stop loss.",
            "latest_event_severity": "alert",
        }
    }

    reply = _local_chat_reply("are alerts working and what is the latest critical alert?", context, model_attempted=False)

    assert "Critical notifications: delivery=CONFIGURED_NOT_TESTED, offscreen=CONFIGURED_NOT_TESTED, local_channel=ACTIVE" in reply
    assert "visible_alerts=1, webhooks=1, recent_delivery=0/0." in reply
    assert "Latest visible alert: ALERT Unprotected position (UNPROTECTED_POSITION) - One open position has no stop loss." in reply
    assert "Alert blockers: Webhook destination exists, but no recent critical notification delivery attempt is recorded." in reply


def test_operator_local_chat_reports_performance_discipline_state():
    context = {
        "performance_discipline": {
            "available": True,
            "status": "ATTENTION",
            "record_count": 2,
            "attention_count": 1,
            "plain_english_summary": "1 of 2 strategy performance record(s) are missing at least one critical performance-reporting field.",
            "diagnostic_hints": ["thin-lead missing critical fields: cost_model, out_of_sample."],
            "records": [
                {
                    "strategy_id": "thin-lead",
                    "mode_label": "RESEARCH/BACKTEST",
                    "coverage_pct": 40.0,
                    "cost_model_present": False,
                    "out_of_sample_present": False,
                    "mode_separation_present": False,
                },
                {
                    "strategy_id": "rich-lead",
                    "mode_label": "BACKTEST",
                    "coverage_pct": 100.0,
                    "cost_model_present": True,
                    "out_of_sample_present": True,
                    "mode_separation_present": True,
                },
            ],
        }
    }

    reply = _local_chat_reply("do our strategy records include costs and out-of-sample coverage?", context, model_attempted=False)

    assert "Performance discipline: status=ATTENTION, records=2, need_review=1." in reply
    assert "1 of 2 strategy performance record(s) are missing at least one critical performance-reporting field." in reply
    assert "Top gaps: thin-lead missing critical fields: cost_model, out_of_sample." in reply
    assert "Record preview: thin-lead RESEARCH/BACKTEST coverage=40.0% costs=MISSING oos=MISSING mode_sep=MISSING" in reply
    assert "rich-lead BACKTEST coverage=100.0% costs=COVERED oos=COVERED mode_sep=COVERED." in reply


def test_operator_local_chat_reports_operational_readiness_state():
    context = {
        "operational_readiness": {
            "available": True,
            "status": "ATTENTION",
            "attention_count": 2,
            "backup_snapshot_count": 0,
            "runbook_path": "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md",
            "external_monitoring": {
                "status": "ATTENTION",
                "top_attention_items": [
                    "Configure external uptime monitoring.",
                    "Configure CAS_FOREX_ERROR_TRACKING_DSN or SENTRY_DSN before hosted production.",
                ],
                "deployment_handoff": {
                    "status": "ACTION_REQUIRED",
                    "owner_ui_path": "?page=settings",
                    "health_endpoints": ["/health", "/api/forex/stack-health/check"],
                    "verification_commands": ["curl -fsS https://your-cas-forex-host/health"],
                    "setup_steps": ["Deploy CAS Forex behind HTTPS with owner authentication enabled."],
                    "package_documents": [
                        {"path": "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md", "present": True},
                        {"path": "docs/operations/CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example", "present": True},
                        {"path": "cas_forex/external_monitoring_control.py", "present": True},
                    ],
                },
                "checks": [
                    {"key": "external_uptime_monitor", "status": "MISSING"},
                    {"key": "error_tracking_dsn", "status": "MISSING"},
                    {"key": "offscreen_alert_destination", "status": "ATTENTION"},
                    {"key": "external_monitoring_runbook", "status": "OK"},
                ],
            },
        }
    }

    reply = _local_chat_reply("is uptime monitoring and error tracking configured for hosted production?", context, model_attempted=False)

    assert "Production operations: status=ATTENTION, attention=2, backups=0, runbook=docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md, external_monitoring=ATTENTION." in reply
    assert "External hooks: external_uptime_monitor=MISSING; error_tracking_dsn=MISSING; offscreen_alert_destination=ATTENTION; external_monitoring_runbook=OK." in reply
    assert "Monitoring gaps: Configure external uptime monitoring.; Configure CAS_FOREX_ERROR_TRACKING_DSN or SENTRY_DSN before hosted production." in reply
    assert "Hosted monitoring handoff: status=ACTION_REQUIRED, owner_ui=?page=settings, health_endpoints=/health, /api/forex/stack-health/check." in reply
    assert "Verify with: curl -fsS https://your-cas-forex-host/health." in reply
    assert "First setup step: Deploy CAS Forex behind HTTPS with owner authentication enabled." in reply
    assert "Handoff files: docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md; docs/operations/CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example; cas_forex/external_monitoring_control.py." in reply


def test_operator_local_chat_reports_legal_compliance_state():
    context = {
        "legal_review": {
            "available": True,
            "status": "ATTENTION",
            "launch_legal_status": "BLOCK_PUBLIC_LAUNCH",
            "counsel_review_accepted": False,
            "counsel_review_record_path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
            "top_attention_items": ["Counsel review record is absent or incomplete; drafts are not public-launch approval."],
            "counsel_review_handoff": {
                "status": "COUNSEL_REVIEW_REQUIRED",
                "launch_legal_status": "BLOCK_PUBLIC_LAUNCH",
                "package_documents": [
                    {"path": "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md", "present": True},
                    {"path": "docs/legal/CAS_FOREX_TERMS_OF_SERVICE_DRAFT.md", "present": True},
                    {"path": "docs/legal/CAS_FOREX_PRIVACY_POLICY_DRAFT.md", "present": True},
                    {"path": "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md", "present": True},
                    {"path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md", "present": False},
                ],
                "required_record_fields": [
                    "counsel_review_status: accepted",
                    "reviewed_by",
                    "review_date",
                    "scope",
                    "qualified_counsel_confirmed: yes",
                ],
                "setup_steps": [
                    "Give qualified counsel the draft disclosure, Terms, Privacy Policy, legal review checklist, and current product/spec evidence."
                ],
                "record_template": [
                    "counsel_review_status: accepted",
                    "reviewed_by: <qualified counsel name or firm>",
                ],
            },
            "checks": [
                {"key": "draft_disclosure_package", "status": "OK"},
                {"key": "legal_review_checklist", "status": "OK"},
                {"key": "counsel_review_record", "status": "MISSING"},
                {"key": "public_launch_legal_status", "status": "ATTENTION"},
            ],
        },
        "professional_claims": {
            "available": True,
            "status": "ATTENTION",
            "disclosure_document_present": True,
            "risky_claim_count": 1,
            "missing_disclosure_count": 1,
            "missing_disclosures": [
                {"key": "not_financial_advice", "label": "No Financial Advice", "status": "MISSING_DRAFT_COPY"}
            ],
            "top_risky_claims": [
                {
                    "path": "ui/src/pages/FakePage.tsx",
                    "line": 12,
                    "claim_type": "guaranteed_profit",
                    "label": "Guaranteed profit/return claim",
                    "excerpt": "Guaranteed profits every day.",
                }
            ],
        },
    }

    reply = _local_chat_reply("are the legal disclosures and compliance boundaries ready for public launch?", context, model_attempted=False)

    assert "Legal review: status=ATTENTION, launch_legal_status=BLOCK_PUBLIC_LAUNCH, counsel_review_accepted=False, record=docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md." in reply
    assert "Legal checks: draft_disclosure_package=OK; legal_review_checklist=OK; counsel_review_record=MISSING; public_launch_legal_status=ATTENTION." in reply
    assert "Legal blockers: Counsel review record is absent or incomplete; drafts are not public-launch approval." in reply
    assert "Counsel handoff: status=COUNSEL_REVIEW_REQUIRED, launch=BLOCK_PUBLIC_LAUNCH, package_docs=4/5." in reply
    assert "Counsel first step: Give qualified counsel the draft disclosure, Terms, Privacy Policy, legal review checklist, and current product/spec evidence." in reply
    assert "Counsel handoff docs: docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md; docs/legal/CAS_FOREX_TERMS_OF_SERVICE_DRAFT.md; docs/legal/CAS_FOREX_PRIVACY_POLICY_DRAFT.md; docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md; docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md." in reply
    assert "Counsel record fields: counsel_review_status: accepted; reviewed_by; review_date; scope; qualified_counsel_confirmed: yes." in reply
    assert "Disclosure/copy posture: status=ATTENTION, draft_present=True, risky_claims=1, missing_disclosures=1." in reply
    assert "Missing disclosure draft items: not_financial_advice." in reply
    assert "Top risky claim hit: Guaranteed profit/return claim at ui/src/pages/FakePage.tsx:12 - Guaranteed profits every day." in reply


def test_operator_local_chat_reports_professional_readiness_matrix():
    context = {
        "professional_readiness": {
            "available": True,
            "status": "ATTENTION",
            "item_count": 37,
            "ok_count": 34,
            "partial_count": 3,
            "gap_count": 0,
            "satisfied_count": 34,
            "internal_partial_count": 0,
            "external_blocked_count": 3,
            "missing_count": 0,
            "top_attention_items": [
                "Obtain legal/compliance review before public launch or advising others for compensation.",
                "Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch.",
            ],
            "remaining_rows": [
                {
                    "item_number": 13,
                    "key": "compliance_awareness",
                    "status": "PARTIAL",
                    "completion_state": "EXTERNAL_BLOCKED",
                    "blocked_by_external_dependency": True,
                    "external_dependency": "Qualified legal/compliance review and accepted counsel record.",
                    "next_action": "Obtain legal/compliance review before public launch or advising others for compensation.",
                },
                {
                    "item_number": 32,
                    "key": "legal_disclosures",
                    "status": "PARTIAL",
                    "completion_state": "EXTERNAL_BLOCKED",
                    "blocked_by_external_dependency": True,
                    "external_dependency": "Counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures.",
                    "next_action": "Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch.",
                },
                {
                    "item_number": 34,
                    "key": "production_operations",
                    "status": "PARTIAL",
                    "completion_state": "EXTERNAL_BLOCKED",
                    "blocked_by_external_dependency": True,
                    "external_dependency": "Hosted uptime monitor and error-tracking DSN configured in the deployment environment.",
                    "next_action": "Add external uptime/error monitoring before public cloud deployment.",
                },
            ],
        }
    }

    reply = _local_chat_reply("what remains from the 37-item checklist?", context, model_attempted=False)

    assert "Professional readiness matrix: status=ATTENTION, ok=34/37, partial=3, gaps=0." in reply
    assert "Completion states: satisfied=34, internal_partial=0, external_blocked=3, missing=0." in reply
    assert "Remaining items: #13 compliance_awareness=PARTIAL; #32 legal_disclosures=PARTIAL; #34 production_operations=PARTIAL." in reply
    assert "External blockers: #13 Qualified legal/compliance review and accepted counsel record.; #32 Counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures.; #34 Hosted uptime monitor and error-tracking DSN configured in the deployment environment." in reply
    assert "Next actions: #13 Obtain legal/compliance review before public launch or advising others for compensation.; #32 Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch.; #34 Add external uptime/error monitoring before public cloud deployment." in reply
    assert "Top attention: Obtain legal/compliance review before public launch or advising others for compensation.; Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch." in reply


def test_operator_local_chat_reports_ai_hedge_intelligence_layer():
    context = {
        "ai_hedge_intelligence_layer": {
            "available": True,
            "status": "SPECIFIED_GOVERNED_LAYER",
            "thesis": "CAS treats the AI Operator as the adaptive trading edge engine inside deterministic guardrails.",
            "edge_role": "The Operator creates and maintains edge by reading regime, strategy fit, account state, open-position health, evidence quality, and psychology risk.",
            "layers": [
                {
                    "label": "Trading Edge Intelligence",
                    "purpose": "Generate and maintain edge.",
                },
                {
                    "label": "Market Regime Intelligence",
                    "purpose": "Classify current market behavior.",
                },
                {
                    "label": "Strategy Selection Intelligence",
                    "purpose": "Select, restrict, pause, or stand down strategy behavior.",
                },
                {
                    "label": "Trade Management Intelligence",
                    "purpose": "Supervise exits, partial closes, breakeven moves, and trailing stops.",
                },
            ],
            "allowed_trade_intents": [
                "enter",
                "skip",
                "reduce",
                "close_partial",
                "close_full",
                "trail_stop",
                "move_stop_to_breakeven",
                "pause_strategy",
                "switch_strategy",
                "stand_down",
            ],
            "allowed_operator_edge_decisions": [
                "classify_regime",
                "score_edge",
                "select_strategy",
                "reject_low_edge",
                "supervise_open_trade",
                "adapt_exit",
                "protect_profit",
                "reduce_exposure",
                "pause_trading",
                "stand_down",
            ],
            "hard_boundaries": [
                "All broker-bound intent must pass through order_dispatch.py.",
                "execution_guard.py remains the final pre-broker gate.",
                "Live-capable entries require fresh one-use edge PASS authorization.",
                "Fresh broker truth is required before live dispatch.",
            ],
            "claim_boundary": "This layer is architecture/spec memory and does not weaken CAS risk controls.",
        }
    }

    reply = _local_chat_reply("what is the AI Hedge Intelligence Layer and can it supervise take profit?", context, model_attempted=False)

    assert "AI Hedge Intelligence Layer: status=SPECIFIED_GOVERNED_LAYER" in reply
    assert "Operator edge role: The Operator creates and maintains edge by reading regime, strategy fit, account state, open-position health, evidence quality, and psychology risk." in reply
    assert "Edge/Hedge layers: Trading Edge Intelligence: Generate and maintain edge.; Market Regime Intelligence: Classify current market behavior.; Strategy Selection Intelligence: Select, restrict, pause, or stand down strategy behavior.; Trade Management Intelligence: Supervise exits, partial closes, breakeven moves, and trailing stops." in reply
    assert "Allowed intents: enter, skip, reduce, close_partial, close_full, trail_stop, move_stop_to_breakeven, pause_strategy, switch_strategy, stand_down." in reply
    assert "Allowed Operator edge decisions: classify_regime, score_edge, select_strategy, reject_low_edge, supervise_open_trade, adapt_exit, protect_profit, reduce_exposure, pause_trading, stand_down." in reply
    assert "Hard boundaries: All broker-bound intent must pass through order_dispatch.py.; execution_guard.py remains the final pre-broker gate.; Live-capable entries require fresh one-use edge PASS authorization.; Fresh broker truth is required before live dispatch." in reply


def test_operator_local_chat_reports_runtime_ai_hedge_supervision():
    context = {
        "ai_hedge_supervision": {
            "available": True,
            "status": "ACTIVE_RECOMMENDATIONS",
            "price_source_status": "PROVIDER_ACTIVE",
            "position_count": 1,
            "action_recommendation_count": 1,
            "high_urgency_count": 0,
            "orders_placed": False,
            "money_moved": False,
            "next_action": "Review the top AI Hedge recommendation, then route any broker-bound action through the protected dispatch path.",
            "recommendations": [
                {
                    "intent": "move_stop_to_breakeven",
                    "symbol": "US30",
                    "urgency": "MEDIUM",
                    "reason": "Position is up 1.20R and stop is not at breakeven.",
                    "gate_path": "AI Hedge -> order_dispatch.py -> execution_guard.py",
                }
            ],
            "positions": [
                {
                    "symbol": "US30",
                    "side": "LONG",
                    "r_multiple": 1.2,
                    "position_source_label": "PAPER_SIM_MT5_PRICED",
                }
            ],
            "claim_boundary": "AI Hedge supervision is read-only.",
        },
        "ai_hedge_intelligence_layer": {
            "available": True,
            "status": "SPECIFIED_GOVERNED_LAYER",
            "thesis": "CAS treats the AI Operator as the adaptive trading edge engine inside deterministic guardrails.",
            "layers": [],
            "allowed_trade_intents": ["move_stop_to_breakeven"],
            "hard_boundaries": ["All broker-bound intent must pass through order_dispatch.py."],
        },
    }

    reply = _local_chat_reply("what is AI Hedge doing right now?", context, model_attempted=False)

    assert "AI Hedge supervision: status=ACTIVE_RECOMMENDATIONS, price_source=PROVIDER_ACTIVE, positions=1, action_intents=1, high_urgency=0, orders_placed=False, money_moved=False." in reply
    assert "Top Hedge intents: move_stop_to_breakeven US30 (MEDIUM): Position is up 1.20R and stop is not at breakeven." in reply
    assert "Top gate path: AI Hedge -> order_dispatch.py -> execution_guard.py." in reply
    assert "Hedge position sample: US30 LONG R=1.2 source=PAPER_SIM_MT5_PRICED." in reply
    assert "Hedge next action: Review the top AI Hedge recommendation, then route any broker-bound action through the protected dispatch path." in reply


def test_operator_local_chat_reports_ai_hedge_management_handoff():
    context = {
        "ai_hedge_management_execution": {
            "available": True,
            "status": "EXECUTED_RECONCILED",
            "latest_status": "EXECUTED_RECONCILED",
            "broker_touched": True,
            "latest_audit_id": "abc123",
            "latest_method": "modify_position",
            "latest_symbol": "US30",
            "latest_ticket": 123456,
            "latest_stop_loss": 100.0,
            "latest_volume": None,
            "latest_broker_result_status": "EXECUTED",
            "latest_terminal_receipt_status": "RECONCILED",
            "latest_post_execution_refresh_status": "REFRESH_RAN",
            "latest_post_execution_refresh_error_count": 0,
            "latest_post_execution_refresh_packets": [
                "account_reconciliation",
                "live_telemetry",
            ],
            "latest_next_action": "Refresh broker truth.",
            "claim_boundary": "AI Hedge management execution is confirmed only.",
        },
        "ai_hedge_management_handoff": {
            "available": True,
            "status": "READY_FOR_GUARDED_EXECUTION",
            "management_action_count": 1,
            "blocked_action_count": 0,
            "ready_for_owner_review": False,
            "ready_for_guarded_execution": True,
            "dry_run_only": False,
            "broker_touched": False,
            "orders_placed": False,
            "money_moved": False,
            "next_action": "Review the drafted management action.",
            "management_actions": [
                {
                    "intent": "move_stop_to_breakeven",
                    "symbol": "US30",
                    "broker_method": "modify_position",
                    "broker_ticket": 123456,
                    "volume": None,
                    "stop_loss": 100.0,
                    "take_profit": 140.0,
                    "risk_effect": "principal_lock",
                    "requires_owner_confirmation": False,
                    "requires_fresh_broker_truth": True,
                    "requires_execution_guard": True,
                    "reason": "Position is up 1.20R and stop is not at breakeven.",
                }
            ],
            "blocked_actions": [],
            "claim_boundary": "AI Hedge management handoff prepares guarded execution drafts.",
        }
    }

    reply = _local_chat_reply("can the Operator move stop to breakeven?", context, model_attempted=False)

    assert "AI Hedge management execution latest: status=EXECUTED_RECONCILED, latest_status=EXECUTED_RECONCILED, broker_touched=True, method=modify_position, symbol=US30, ticket=123456, broker_result=EXECUTED, terminal_receipt=RECONCILED, post_execution_refresh=REFRESH_RAN." in reply
    assert "Post-execution refresh errors: 0." in reply
    assert "Refreshed packets: account_reconciliation, live_telemetry." in reply
    assert "Latest management audit id: abc123." in reply
    assert "AI Hedge management handoff: status=READY_FOR_GUARDED_EXECUTION, drafts=1, blocked=0, ready_for_guarded_execution=True, dry_run_only=False, broker_touched=False, orders_placed=False." in reply
    assert "Top management draft: modify_position US30 ticket=123456 stop_loss=100.0 volume=None risk_effect=principal_lock." in reply
    assert "Required before execution: per_action_owner_confirmation=False, fresh_broker_truth=True, execution_guard=True." in reply
    assert "AI Hedge management handoff prepares guarded execution drafts." in reply


def test_ai_hedge_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("what is the AI Hedge Intelligence Layer?")
    assert _should_answer_chat_locally_first("can the Operator move stop to breakeven?")


def test_operator_local_chat_reports_general_system_health_state():
    context = {
        "stack_health": {
            "available": True,
            "overall_status": "DEGRADED",
            "ok_count": 4,
            "degraded_count": 1,
            "missing_count": 1,
            "unknown_count": 0,
            "checks": [
                {"name": "uvicorn-api", "status": "OK"},
                {"name": "autowake-supervisor", "status": "OK"},
                {"name": "mt5-terminal", "status": "DEGRADED"},
                {"name": "autonomous-loop", "status": "OK"},
                {"name": "readiness-gates", "status": "DEGRADED"},
                {"name": "live-telemetry", "status": "OK"},
            ],
            "next_actions": [
                "Connect MT5 terminal API verification.",
                "Clear live readiness blockers.",
            ],
        },
        "operator_briefing": {
            "available": True,
            "loop_health_status": "running",
            "decisions_today": 5,
            "executions_today": 1,
            "blocked_today": 2,
            "open_position_count": 2,
            "total_floating_pnl": 15.0,
            "live_position_feed_label": "SIM PROOF",
            "live_telemetry_source": "movement_stream",
            "live_price_source_status": "STATIC_SIMULATION_FALLBACK",
            "mt5_terminal_connected": True,
            "readiness_gates_open": 3,
            "readiness_gates_total": 5,
            "diagnostic_hints": ["MT5 broker verification is not current."],
        },
        "public_launch_gate": {
            "launch_gate_status": "BLOCKED",
            "live_money_production_status": "BLOCKED",
        },
    }

    reply = _local_chat_reply("is everything working correctly?", context, model_attempted=False)

    assert "System health: overall=DEGRADED, ok=4, degraded=1, missing=1, unknown=0." in reply
    assert "Checks: uvicorn-api=OK, autowake-supervisor=OK, mt5-terminal=DEGRADED" in reply
    assert "Next actions: Connect MT5 terminal API verification.; Clear live readiness blockers." in reply
    assert "Operator briefing: loop=running, decisions_today=5, executions_today=1, blocked_today=2" in reply
    assert "floating_pnl=$15.00, position_feed=SIM PROOF, telemetry_source=movement_stream, price_source_status=STATIC_SIMULATION_FALLBACK" in reply
    assert "Public launch gate=BLOCKED; live-money production=BLOCKED." in reply


def test_operator_briefing_context_overlays_running_runtime_on_stale_archive(monkeypatch):
    import cas_forex.operator_briefing as briefing_module
    from api.routes import operator_briefing as briefing_route

    monkeypatch.setattr(
        briefing_module,
        "load_operator_briefing_inputs",
        lambda _root: {
            "loop_health": {
                "overall_status": "stalled",
                "cycles_today": 2,
                "diagnostic_hints": ["The most recent cycle is stale."],
            }
        },
    )
    monkeypatch.setattr(
        briefing_route,
        "_runtime_loop_status",
        lambda: {
            "source": "dispatch_loop",
            "running": True,
            "mode": "PAPER",
            "cycles_run": 21,
            "last_run_iso": "2026-07-13T21:54:18+00:00",
            "status": "RUNNING",
        },
    )

    context = _operator_briefing_context()

    assert context["available"] is True
    assert context["loop_health_status"] == "running"
    assert context["cycles_today"] == 21
    assert context["runtime_loop"]["source"] == "dispatch_loop"
    assert context["diagnostic_hints"] == []


def test_operator_default_update_uses_position_feed_truth_when_mt5_is_connected():
    context = {
        "live_mt5": {
            "connected": True,
            "open_position_count": 2,
            "account": {
                "floating_pnl_usd": 0.0,
            },
        },
        "operator_briefing": {
            "available": True,
            "live_position_feed_label": "WRONG",
            "live_telemetry_source": "wrong_source",
            "live_price_source_status": "WRONG_STATUS",
            "live_telemetry_stale": True,
            "live_telemetry_last_update_iso": "wrong-update",
            "live_position_feed_detail": "wrong detail",
            "live_movement_source_truth": {
                "position_feed_label": "SIM PROOF",
                "telemetry_source": "movement_stream",
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "telemetry_stale": False,
                "telemetry_last_update_iso": "2026-07-09T12:00:00+00:00",
                "position_feed_detail": (
                    "Position rows are paper/demo simulator proof rows with static simulation fallback, not live MT5 terminal positions."
                ),
                "detail": (
                    "Position rows are paper/demo simulator proof rows with static simulation fallback, not live MT5 terminal positions."
                ),
            },
        },
    }

    reply = _local_chat_reply("give me a quick update", context, model_attempted=False)

    assert "Paper/demo movement mirror: 2 open positions, floating P&L $0.00." in reply
    assert "Position feed: SIM PROOF, telemetry_source=movement_stream, price_source_status=STATIC_SIMULATION_FALLBACK" in reply
    assert "not live MT5 terminal positions" in reply
    assert "wrong_source" not in reply
    assert "WRONG_STATUS" not in reply


def test_gate_trace_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("show me the latest dispatch gate trace and money impact")


def test_psychology_guard_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("is the revenge or FOMO cooldown active right now?")


def test_emergency_control_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("what does the emergency stop do and can I close all positions?")


def test_notification_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("are alerts working and are off-screen notifications configured?")


def test_performance_discipline_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("do our backtests include spread, slippage, commission, and walk-forward coverage?")


def test_operational_readiness_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("is uptime monitoring and error tracking configured for hosted production?")


def test_legal_compliance_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("are the legal disclosures and compliance boundaries ready for public launch?")


def test_professional_readiness_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("what remains from the 37-item checklist?")


def test_close_all_positions_command_is_not_mistaken_for_status_question():
    assert _should_answer_chat_locally_first("close all positions") is False


def test_general_health_questions_are_answered_locally_first():
    assert _should_answer_chat_locally_first("is everything working correctly?")
