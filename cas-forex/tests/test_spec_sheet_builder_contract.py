from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "tmp" / "cas_forex_spec_sheet_builder" / "build_cas_forex_spec_sheet.mjs"


def _builder_source() -> str:
    return BUILDER.read_text(encoding="utf-8")


def test_spec_sheet_builder_reads_canonical_professional_readiness_matrix():
    source = _builder_source()

    assert "readProfessionalReadinessMatrix" in source
    assert "build_professional_readiness_matrix" in source
    assert "cas_forex.professional_readiness_matrix" in source
    assert "professionalReadinessSummary(professionalReadiness)" in source
    assert "readinessEvidenceStatus(professionalReadiness)" in source


def test_spec_sheet_builder_exports_professional_readiness_completion_states():
    source = _builder_source()

    assert 'addSheet("Professional Readiness"' in source
    assert '"Completion State"' in source
    assert "completion_state" in source
    assert "external_blocked_count" in source
    assert "internal_partial_count" in source
    assert "missing_count" in source
    assert "'Professional Readiness'!E10:E80" in source
    assert '\\"MISSING\\"' in source
    assert '\\"EXTERNAL_BLOCKED\\"' in source


def test_spec_sheet_builder_threads_latest_broker_truth_proof_into_export():
    source = _builder_source()

    assert (
        "tests/test_broker_truth_cross_surface.py:"
        "test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces"
    ) in source
    assert "brokerTruthCrossSurfaceRows.length >= 4" in source
    assert "Broker-truth cross-surface proof" in source


def test_spec_sheet_builder_inventory_and_checks_cover_professional_readiness():
    source = _builder_source()

    assert "/api/forex/settings/professional-readiness" in source
    assert "Professional readiness rows present" in source
    assert "Professional readiness missing rows" in source
    assert "Professional readiness internal partial rows" in source
    assert "Professional readiness external blockers" in source
    assert '"A11", "Professional readiness matrix"' in source


def test_spec_sheet_builder_sources_canonical_autonomous_execution_authority():
    source = _builder_source()

    assert "readSpecAuthorityBundle" in source
    assert "autonomous_execution_correction" in source
    assert "ai_hedge_intelligence_layer" in source
    assert 'addSheet("Autonomous Execution"' in source
    assert 'addSheet("AI Edge Layer"' in source
    assert 'addSheet("Operator Contracts"' in source
    assert 'addSheet("Runtime Truth"' in source
    assert 'addSheet("Acceptance Tests"' in source
    assert "CAS_Forex_Web_Phone_AI_Trading_Spec_2026-07-15.xlsx" in source
    assert "deepseek-v4-flash:cloud" in source
    assert "deepseek-v4-pro:cloud" in source
    assert "PASS_DEEPSEEK_V4_ROLE_CAPABILITY" in source
    assert "redteam-deepseek-v4-role-routing-latest.json" in source
    assert "gemma4:31b-cloud" in source
    assert "PASS_GEMMA4_BACKUP_CAPABILITY" in source
    assert "redteam-gemma4-backup-latest.json" in source
    assert '"A57", "Gemma 4 31B structured failover backup"' in source
    assert "MT5 Algo Trading" in source
    assert "MODEL_PRIMARY" in source
    assert "OPERATOR_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS = 55.0" in source
    assert "ASSISTANT_CONTEXT_RESPONSE_BUDGET_SECONDS = 2.0" in source
    assert "ASSISTANT_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS = 45.0" in source
    assert "LOCAL_SYSTEM_PROMPT" in source
    assert "test_assistant_context_timeout_does_not_block_event_loop" in source
    assert "test_assistant_current_strategy_comparison_refuses_to_invent_regime" in source
    assert "deepseek-r1:latest" in source
    assert "Entry timeframe / scalp lane" in source
    assert "m1_m5_fresh_micro_scalp_reaches_operator_dispatch" in source
    assert "Pre-Operator entry opportunity pipeline" in source
    assert "cache_throttled_scheduler_call_is_not_a_completed_market_scan" in source
    assert "pre_operator_candidate_starvation_reaches_operator_context" in source
    assert "below_floor_shadow_pass_is_non_authorizing" in source
    assert "best_shadow_pass_lane_drives_bounded_paper_admission" in source
    assert "paper_shadow_pass_policy_restores_candidate_flow_after_invalid_model" in source
    assert "restored_candidate_reaches_immediate_operator_and_mt5_demo" in source
    assert "runtime/redteam-entry-opportunity-starvation-latest.json" in source
    assert "runtime/entry-opportunity-restoration-latest.json" in source
    assert "PASS_OPERATOR_FLOOR_RESTORATION_TO_MT5_DEMO_FILL" in source
    assert "PAPER_SHADOW_PASS_POLICY_FALLBACK" in source
    assert "FOCUSED ENTRY-OPPORTUNITY REPAIR" in source
    assert "Micro-scalp label masks replay template" in source
    assert "Owner risk authority persistence" in source
    assert "explicit_owner_risk_override_survives_api_restart" in source
    assert "risk_preview_uses_effective_dispatch_posture" in source
    assert "ACTIVE_ACCOUNT_NORTH_STAR" in source
    assert "fast_owner_chat" in source
    assert "operator_chat_preserves_north_star_account_truth_under_context_pressure" in source
    assert "mt5_cashflow_adjusted_realized_growth_reconciles_to_balance" in source
    assert "runtime/mt5-account-growth.json" in source
    assert "Deposit mistaken for profit or mismatched growth baseline" in source
    assert '"A22", "Cashflow-adjusted realized-growth baseline"' in source
    assert "Recent-loss logic reads insertion order" in source
    assert "Cross-timeframe learning pool" in source
    assert "High win rate outranks account growth" in source
    assert "Pooled profit subsidizes losing promotion" in source
    assert "Historical lot size confounds strategy edge" in source
    assert "Conviction silently chooses lot" in source
    assert "Position prompt negates after-cost ranking" in source
    assert "Management action hides immediate realization effect" in source
    assert "Timeframe dropped before outcome learning join" in source
    assert "Per-lot dollars compared across instrument contracts" in source
    assert "Stale stored risk becomes learning authority" in source
    assert "Incomplete admission risk promotes or supports press size" in source
    assert "Malformed scheduled growth-ranking prompt" in source
    assert "Broker alias fragments growth and exposure identity" in source
    assert "Observational poll blocks Operator control plane" in source
    assert '"A23", "Exact-group after-cost adaptation evidence"' in source
    assert '"A24", "Explicit sizing and management growth utility"' in source
    assert '"A25", "Broker-risk-normalized edge utility"' in source
    assert '"A26", "Canonical broker-alias growth identity"' in source
    assert '"A27", "Non-blocking Operator observability"' in source
    assert '"A28", "Sunday reopen and tick freshness truth"' in source
    assert '"A29", "Interrupted MT5 demo receipt recovery"' in source
    assert '"A30", "Bounded Assistant and Operator conversations"' in source
    assert '"A31", "Daily realized-loss execution invariant"' in source
    assert '"A34", "Operator discretion between fixed thresholds"' in source
    assert '"A35", "Ticket-scoped same-symbol management"' in source
    assert '"A36", "Working local Operator failover"' in source
    assert '"A37", "Local structured trading-decision continuity"' in source
    assert "runtime/operator-position-v14-local-natural-receipt-latest.json" in source
    assert '"A38", "Original-risk compounding, semantic close, and actual-model receipts"' in source
    assert '"A39", "Trade-path chat/cockpit consistency"' in source
    assert '"A40", "Growth-aware entry failover and lot-envelope receipts"' in source
    assert '"A41", "Exact-stop legacy risk completeness"' in source
    assert '"A42", "Actionability-aware candidate exploration"' in source
    assert '"A43", "Merged exact-group learning sources"' in source
    assert '"A44", "Completed-candle preview/final route identity"' in source
    assert '"A45", "Fresh-position discretionary-close hysteresis"' in source
    assert '"A46", "Bounded v14 no-action schema adapter"' in source
    assert '"A47", "Execution-receipt position-age authority"' in source
    assert '"A48", "Natural v14 management decision-to-outcome receipt"' in source
    assert '"A49", "Model transport versus contract-rejection truth"' in source
    assert '"A50", "Scale-in model attribution and dedicated compound slot"' in source
    assert '"A51", "Mandatory pre-Operator opportunity evidence"' in source
    assert '"A52", "Outlier-resistant edge classification"' in source
    assert '"A53", "Grounded dual-chat availability"' in source
    assert '"A54", "Regime-attributed adaptive edge learning"' in source
    assert '"A55", "Bounded Operator position-capacity recovery"' in source
    assert '"A56", "Tiered request-time model capability and late-result delivery"' in source
    assert '"PRD-019", "Truthful tiered model capability"' in source
    assert '"PRD-018", "Operator recovers low-exposure position-cap starvation"' in source
    assert '"import yaml"' in source
    assert "CAS_FOREX_SPEC_PYTHON" in source
    assert "YAML-backed autonomous execution acceptance tests are missing" in source
    assert '"RT-076", "Trade-path chat contradicts cockpit dispatch state"' in source
    assert '"RT-077", "Paper model outage reuses a known losing group at default size"' in source
    assert '"RT-078", "Approximate legacy close fabricates admission-risk evidence"' in source
    assert '"RT-079", "Untradeable first PASS starves the candidate universe"' in source
    assert '"RT-080", "Combined group table hides broker-verified exact group"' in source
    assert '"RT-081", "Forming-candle preview and final route identity drift"' in source
    assert '"RT-082", "Fresh initial spread triggers immediate discretionary churn"' in source
    assert '"RT-083", "Actionless SELECT mislabeled as model outage"' in source
    assert '"RT-084", "Noncanonical HOLD either silences positions or gains mutation authority"' in source
    assert '"RT-085", "Future broker-server timestamp freezes position age at zero"' in source
    assert '"RT-086", "Rotating latest files corrupt historical receipt provenance"' in source
    assert '"RT-087", "Healthy model response mislabeled as provider outage"' in source
    assert '"RT-088", "Ordinary symbol cap silently disables authorized compounding"' in source
    assert '"RT-089", "Single winning outlier masquerades as scalable edge"' in source
    assert '"RT-090", "Assistant context rebuild and model contention silence or hallucinate chat"' in source
    assert '"RT-091", "Management handoff inspects the wrong account runtime"' in source
    assert '"RT-092", "Review pacing is mislabeled as an AI stand-down"' in source
    assert '"RT-093", "Generic JSON mode corrupts local trading decisions"' in source
    assert '"RT-094", "Bare ticket spelling silently erases a valid exact decision"' in source
    assert '"RT-095", "Chat reply source is hidden or misrepresented"' in source
    assert '"RT-096", "Mixed market regimes masquerade as one scalable edge"' in source
    assert '"RT-097", "Low-exposure position cap silently starves Operator entries"' in source
    assert '"RT-098", "Stale or hallucinated account truth reaches owner chat"' in source
    assert '"RT-099", "Configured model or role label masks real capability"' in source
    assert "redteam-operator-outlier-edge-robustness-latest.json" in source
    assert "redteam-operator-regime-attribution-latest.json" in source
    assert "redteam-dual-chat-responsiveness-latest.json" in source
    assert "redteam-operator-capacity-starvation-latest.json" in source
    assert "runtime/ai-control-authority-audit.jsonl" in source
    assert "capacityAdjustmentAudit" in source
    assert "test_capacity_apply_revalidation_blocks_when_positions_cleared" in source
    assert "test_capacity_redteam_is_no_touch_and_rejects_multi_slot_jump" in source
    assert "runtime/ai-operator-scale-in-execution-audit.jsonl" in source
    assert '"=COUNTA(\'Red Team Register\'!A5:A102)", 98' in source
    assert '"=COUNTA(\'Roadmap Acceptance\'!A5:A60)", 56' in source
    assert '"=COUNTA(\'Operator Contracts\'!A5:A30)", 25' in source
    assert '"=COUNTA(\'Runtime Truth\'!A5:A70)", 66' in source
    assert 'lookupFormula("Runtime Truth", "Operator position-capacity recovery", "C")' in source
    assert 'lookupFormula("Runtime Truth", "Trade-path chat/cockpit consistency", "C")' in source
    assert 'lookupFormula("Runtime Truth", "MT5 demo learning", "C")' in source
    assert 'lookupFormula("Runtime Truth", "Natural larger-lot and compound-slot execution", "C")' in source
    assert 'lookupFormula("Operator Contracts", "Natural position proof", "E")' in source
    assert '"=\'Runtime Truth\'!C20"' not in source
    assert '"=\'Operator Contracts\'!E23"' not in source
    assert "Operator has no action menu between fixed thresholds" in source
    assert "Same-symbol positions collapse onto the first ticket" in source
    assert "recent_outcome_logic_uses_chronological_broker_closes" in source
    assert "learning_groups_rank_after_cost_expectancy_before_win_rate" in source
    assert "adaptation_promotion_requires_exact_profitable_behavior_group" in source
    assert "press_size_and_promotion_require_regime_comparable_outcomes" in source
    assert "operator_approval_requires_explicit_sizing_ref" in source
    assert "paper_model_failure_cannot_recycle_known_losing_group_or_press_size" in source
    assert "blocked_pass_cannot_starve_later_actionable_candidate_lanes" in source
    assert "combined_and_broker_exact_group_stats_are_merged" in source
    assert "completed_candle_transform_precedes_candidate_preview" in source
    assert "fresh_protected_position_initial_spread_cannot_force_discretionary_close" in source
    assert "explicit_actionless_select_normalizes_to_stand_down_only" in source
    assert "noncanonical_position_hold_is_bounded_and_mutations_fail_closed" in source
    assert "omitted_position_decision_becomes_audited_stand_down" in source
    assert "execution_receipt_time_overrides_materially_future_broker_position_time" in source
    assert "natural_operator_management_receipt_binds_decision_execution_and_learning" in source
    assert "model_response_contract_rejection_is_not_reported_as_provider_outage" in source
    assert "settings_and_management_runtime_share_active_scheduler_broker_truth" in source
    assert "review_interval_deferral_is_not_operator_stand_down" in source
    assert "local_entry_and_position_models_receive_exact_json_schema" in source
    assert "unique_bare_ticket_key_normalizes_without_relaxing_action_authority" in source
    assert "dual_chat_surfaces_disclose_answer_source" in source
    assert "natural_local_model_scale_in_executes_and_reconciles" in source
    assert "repeated_low_exposure_position_cap_starvation_reaches_operator" in source
    assert "position_capacity_widening_revalidates_fresh_mt5_state_at_apply_time" in source
    assert "multi_slot_position_capacity_increase_from_single_review" in source
    assert "position_capacity_increase_without_fresh_action_time_mt5_revalidation" in source
    assert "learning_ranking_normalizes_historical_lot_size" in source
    assert "dispatch_retains_timeframe_for_outcome_learning" in source
    assert "position_prompt_preserves_after_cost_ranking_and_origin" in source
    assert "management_actions_expose_immediate_growth_effect" in source
    assert "scale_in_r_uses_original_entry_stop_after_breakeven" in source
    assert "tiny_winner_realization_close_requires_explicit_growth_case" in source
    assert "contradictory_select_close_and_hold_language_stands_down" in source
    assert "autonomous_broker_effect_receipt_binds_actual_operator_identity" in source
    assert "after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl" in source
    assert "historical_admission_risk_recomputed_from_broker_tick_contract" in source
    assert "learning_ranking_prefers_after_cost_r_expectancy_across_instruments" in source
    assert "incomplete_admission_risk_cannot_promote_or_supply_press_evidence" in source
    assert "entry_projection_uses_historical_r_expectancy_times_current_stop_risk" in source
    assert "operator_growth_ranking_prompt_is_well_formed" in source
    assert "broker_aliases_share_learning_promotion_and_exposure_identity" in source
    assert "operator_observability_remains_responsive_during_slow_evidence_refresh" in source
    assert "sunday_reopen_and_tick_freshness_are_not_conflated" in source
    assert "interrupted_demo_order_receipt_recovers_without_retry" in source
    assert "dispatch_status_reports_running_while_rich_diagnostics_refresh" in source
    assert "assistant_and_operator_answer_compounding_without_timeout_or_navigation_misroute" in source
    assert "exhausted_claude_budget_uses_working_local_operator_model" in source
    assert "late_completed_trading_model_result_is_single_use_and_kind_bound" in source
    assert "model_ready_requires_fresh_successful_generation" in source
    assert "test_http_provider_error_preserves_ollama_capacity_detail" in source
    assert "test_provider_health_becomes_stale_without_claiming_current_readiness" in source
    assert "test_late_result_is_not_delivered_to_a_different_decision_kind" in source
    assert "daily_realized_loss_cap_blocks_model_and_degraded_fallback_entries" in source
    assert "The AI autonomously trade and initiate configured money movement" not in source
    assert "Operator cannot directly place trades or move money" not in source
    assert "Cannot place orders or move money by construction." not in source


def _sheet_text_by_name(xlsx_path: Path, sheet_name: str) -> str:
    namespace = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(xlsx_path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        workbook_rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_target_by_id = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in workbook_rels.findall("pkg:Relationship", namespace)
        }
        target = None
        for sheet in workbook.findall("main:sheets/main:sheet", namespace):
            if sheet.attrib.get("name") == sheet_name:
                target = rel_target_by_id[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
                break
        if target is None:
            raise AssertionError(f"Sheet not found: {sheet_name}")
        normalized_target = str(target).lstrip("/").removeprefix("xl/")
        sheet_xml = ET.fromstring(zf.read(f"xl/{normalized_target}"))
    return " ".join(text.strip() for text in sheet_xml.itertext() if text and text.strip())


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the spec workbook builder")
def test_spec_sheet_builder_generates_live_authority_content(tmp_path):
    output_dir = tmp_path / "spec-output"
    subprocess.run(
        ["node", str(BUILDER), str(REPO_ROOT), str(output_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    workbook = output_dir / "CAS_Forex_Web_Phone_AI_Trading_Spec_2026-07-15.xlsx"
    assert workbook.exists()

    autonomous_execution_text = _sheet_text_by_name(workbook, "Autonomous Execution")
    ai_edge_text = _sheet_text_by_name(workbook, "AI Edge Layer")
    operator_contracts_text = _sheet_text_by_name(workbook, "Operator Contracts")
    runtime_truth_text = _sheet_text_by_name(workbook, "Runtime Truth")
    acceptance_tests_text = _sheet_text_by_name(workbook, "Acceptance Tests")
    red_team_text = _sheet_text_by_name(workbook, "Red Team Register")
    sources_text = _sheet_text_by_name(workbook, "Sources")

    assert "2026-07-09-AUTONOMOUS-EXECUTION-CORRECTION" in autonomous_execution_text
    assert "GOVERNING_REPLACEMENT_LANGUAGE" in autonomous_execution_text
    assert "owner_owned_account_transfer" in autonomous_execution_text
    assert "flatten_exposure" in autonomous_execution_text
    assert "UNAVAILABLE" not in autonomous_execution_text
    assert "Autonomous execution correction unavailable from Python" not in autonomous_execution_text
    assert "SPECIFIED_GOVERNED_LAYER" in ai_edge_text
    assert "adaptive trading edge engine" in ai_edge_text
    assert "ai_operator_trade_edge.v11" in operator_contracts_text
    assert "ai_operator_position_edge.v14" in operator_contracts_text
    assert "Exact candidate + exact size menu" in operator_contracts_text
    assert "operator_sizing.v2" in operator_contracts_text
    assert "0.01 is a broker floor, not a fixed policy" in operator_contracts_text
    assert "Winner scale-in" in operator_contracts_text
    assert "Position decision cache binding" in operator_contracts_text
    assert "Original-risk compounding geometry" in operator_contracts_text
    assert "Tiny-winner close semantics and provenance" in operator_contracts_text
    assert "Local structured decision transport" in operator_contracts_text
    assert "Entry sizing envelope evidence" in operator_contracts_text
    assert "Position-capacity recovery" in operator_contracts_text
    assert "Every fresh manageable position" in operator_contracts_text
    assert "Terminal Algo Trading" in runtime_truth_text
    assert "Market-regime outcome attribution" in runtime_truth_text
    assert "Operator position-capacity recovery" in runtime_truth_text
    assert "MODEL_PRIMARY" in runtime_truth_text or "unavailable" in runtime_truth_text
    assert "algo_on_enables_real_mt5_demo_execution_learning" in acceptance_tests_text
    assert "ai_operator_selects_exact_position_management_action" in acceptance_tests_text
    assert "ai_operator_selects_larger_risk_compliant_lot" in acceptance_tests_text
    assert "press_size_and_promotion_require_regime_comparable_outcomes" in acceptance_tests_text
    assert "ai_operator_compounds_protected_winner_autonomously" in acceptance_tests_text
    assert "scale_in_requires_net_profit_after_reported_open_costs" in acceptance_tests_text
    assert "position_decision_cache_invalidates_on_account_or_pnl_change" in acceptance_tests_text
    assert "scale_in_authorization_rechecks_parent_profit_and_geometry" in acceptance_tests_text
    assert "authorized_compound_slot_extends_only_exact_scale_in_lane" in acceptance_tests_text
    assert "broker_tick_value_risk_cap_blocks_understated_index_order" in acceptance_tests_text
    assert "open_position_stop_risk_reaches_operator_and_ui" in acceptance_tests_text
    assert "Per-trade stop-risk cap" in runtime_truth_text
    assert "Open-position stop-risk telemetry" in runtime_truth_text
    assert "Scheduled Operator reasoning" in runtime_truth_text
    assert "Entry timeframe / scalp lane" in runtime_truth_text
    assert "m1_m5_fresh_micro_scalp_reaches_operator_dispatch" in acceptance_tests_text
    assert "timeframe_scans_rotate_without_cross_cache_starvation" in acceptance_tests_text
    assert "cache_throttled_scheduler_call_is_not_a_completed_market_scan" in acceptance_tests_text
    assert "pre_operator_candidate_starvation_reaches_operator_context" in acceptance_tests_text
    assert "Pre-Operator entry opportunity pipeline" in runtime_truth_text
    assert "closed_quote_cannot_consume_route_identity" in acceptance_tests_text
    assert "blocked_pass_cannot_starve_later_actionable_candidate_lanes" in acceptance_tests_text
    assert "combined_and_broker_exact_group_stats_are_merged" in acceptance_tests_text
    assert "completed_candle_transform_precedes_candidate_preview" in acceptance_tests_text
    assert "fresh_protected_position_initial_spread_cannot_force_discretionary_close" in acceptance_tests_text
    assert "Micro-scalp label masks replay template" in red_team_text
    assert "Cross-timeframe cache starvation" in red_team_text
    assert "Candidate starvation is mislabeled as prudence" in red_team_text
    assert "Closed quote consumes one-shot setup" in red_team_text
    assert "Permanent 0.01-lot throttle" in red_team_text
    assert "Martingale disguised as compounding" in red_team_text
    assert "Scale-in authorization replay" in red_team_text
    assert "Owner risk authority lost on restart" in red_team_text
    assert "Static fallback mislabeled effective" in red_team_text
    assert "Stale verifier overrides current MT5 account" in red_team_text
    assert "Simulator masquerades as active account" in red_team_text
    assert "Pre-cost P&L masquerades as growth" in red_team_text
    assert "Context compression drops the growth scoreboard" in red_team_text
    assert "Pre-cost winner compounded into a net loser" in red_team_text
    assert "Stale position decision reused after costs change" in red_team_text
    assert "Scale-in authority survives changed parent protection" in red_team_text
    assert "Deposit mistaken for profit or mismatched growth baseline" in red_team_text
    assert "Recent-loss logic reads insertion order" in red_team_text
    assert "Cross-timeframe learning pool" in red_team_text
    assert "High win rate outranks account growth" in red_team_text
    assert "Pooled profit subsidizes losing promotion" in red_team_text
    assert "Historical lot size confounds strategy edge" in red_team_text
    assert "Conviction silently chooses lot" in red_team_text
    assert "Position prompt negates after-cost ranking" in red_team_text
    assert "Management action hides immediate realization effect" in red_team_text
    assert "Timeframe dropped before outcome learning join" in red_team_text
    assert "Per-lot dollars compared across instrument contracts" in red_team_text
    assert "Stale stored risk becomes learning authority" in red_team_text
    assert "Incomplete admission risk promotes or supports press size" in red_team_text
    assert "Malformed scheduled growth-ranking prompt" in red_team_text
    assert "Broker alias fragments growth and exposure identity" in red_team_text
    assert "Observational poll blocks Operator control plane" in red_team_text
    assert "Sunday reopen falsely reported closed" in red_team_text
    assert "Broker executes but CAS receipt remains unresolved" in red_team_text
    assert "Chat timeout or navigation intent collision" in red_team_text
    assert "Degraded fallback bypasses daily realized-loss cap" in red_team_text
    assert "Paid-model exhaustion leaves a dead or noisy local Operator" in red_team_text
    assert "Local context truncation corrupts structured trading decisions" in red_team_text
    assert "Breakeven stop manufactures a false 1.0R compounding winner" in red_team_text
    assert "Operator selects close while explaining HOLD" in red_team_text
    assert "Receipt names configured model instead of actual decision model" in red_team_text
    assert "Paper model outage reuses a known losing group at default size" in red_team_text
    assert "Approximate legacy close fabricates admission-risk evidence" in red_team_text
    assert "Untradeable first PASS starves the candidate universe" in red_team_text
    assert "Combined group table hides broker-verified exact group" in red_team_text
    assert "Forming-candle preview and final route identity drift" in red_team_text
    assert "Fresh initial spread triggers immediate discretionary churn" in red_team_text
    assert "Actionless SELECT mislabeled as model outage" in red_team_text
    assert "Noncanonical HOLD either silences positions or gains mutation authority" in red_team_text
    assert "Future broker-server timestamp freezes position age at zero" in red_team_text
    assert "Rotating latest files corrupt historical receipt provenance" in red_team_text
    assert "Healthy model response mislabeled as provider outage" in red_team_text
    assert "Ordinary symbol cap silently disables authorized compounding" in red_team_text
    assert "Operator has no action menu between fixed thresholds" in red_team_text
    assert "Effective dispatch caps / restart authority" in runtime_truth_text
    assert "Active-account cockpit source" in runtime_truth_text
    assert "Open P&L after carry/costs" in runtime_truth_text
    assert "Cashflow-adjusted realized growth" in runtime_truth_text
    assert "Exact-group after-cost learning" in runtime_truth_text
    assert "Current account truth across surfaces" in runtime_truth_text
    assert "Operator north-star account truth" in runtime_truth_text
    assert "Broker-action north-star context" in runtime_truth_text
    assert "Risk-normalized growth utility" in runtime_truth_text
    assert "Historical admission-risk reconstruction" in runtime_truth_text
    assert "Exact MT5 stop-fill legacy risk repair" in runtime_truth_text
    assert "Canonical broker-alias growth identity" in runtime_truth_text
    assert "Non-blocking Operator observability" in runtime_truth_text
    assert "Account snapshot freshness" in runtime_truth_text
    assert "Open-position market tick freshness" in runtime_truth_text
    assert "Interrupted demo receipt recovery" in runtime_truth_text
    assert "Natural MT5 position-management receipt" in runtime_truth_text
    assert "Bounded conversational control plane" in runtime_truth_text
    assert "Daily realized-loss entry boundary" in runtime_truth_text
    assert "Entry outage growth gate / sizing envelope" in runtime_truth_text
    assert "Actionable candidate-universe selection" in runtime_truth_text
    assert "Pre-Operator entry opportunity pipeline" in runtime_truth_text
    assert "PASS_OPERATOR_FLOOR_RESTORATION_TO_MT5_DEMO_FILL" in sources_text
    assert "Merged exact-group learning sources" in runtime_truth_text
    assert "Completed-candle preview/final identity" in runtime_truth_text
    assert "Fresh-position close hysteresis" in runtime_truth_text
    assert "Bounded no-action model normalization" in runtime_truth_text
    assert "Execution-receipt position age" in runtime_truth_text
    assert "Natural v14 decision-to-outcome chain" in runtime_truth_text
    assert "Natural larger-lot and compound-slot execution" in runtime_truth_text
    assert "Active scheduler management handoff" in runtime_truth_text
    assert "Exact local decision schemas" in runtime_truth_text
    assert "Deferred position-review semantics" in runtime_truth_text
    assert "Unique broker-ticket normalization" in runtime_truth_text
    assert "Visible dual-chat responder attribution" in runtime_truth_text
    # The local-fallback model id is asserted against the Red Team Register,
    # where the builder emits it unconditionally (RT-071). The Runtime Truth
    # sheet is point-in-time machine evidence - its own header says unavailable
    # values are expected - so asserting a model id there tested the state of
    # the machine running the suite, not the product.
    assert "deepseek-r1:latest" in red_team_text
    # The v11 no-touch probe row must cite its durable evidence file. The
    # previous assertion pinned one packet hash from that file - machine state,
    # not product structure; whether the evidence is loadable is what the
    # sheet's present/OPEN cell already reports.
    assert "runtime/redteam-position-edge-v11-latest.json" in runtime_truth_text
    assert "Local structured Operator continuity" in runtime_truth_text
    assert "Operator model failure-stage truth" in runtime_truth_text
    assert "Bounded trading-model capability" in runtime_truth_text
    assert "Gemma 4 structured failover proof" in runtime_truth_text
    assert "Original-risk R and compounding horizon" in runtime_truth_text
    assert "Semantic close guard and broker-effect provenance" in runtime_truth_text
    assert "sunday_reopen_and_tick_freshness_are_not_conflated" in acceptance_tests_text
    assert (
        "exact_mt5_stop_fill_repairs_legacy_admission_risk_without_outcome_leakage"
        in acceptance_tests_text
    )
    assert "interrupted_demo_order_receipt_recovers_without_retry" in acceptance_tests_text
    assert "dispatch_status_reports_running_while_rich_diagnostics_refresh" in acceptance_tests_text
    assert "assistant_and_operator_answer_compounding_without_timeout_or_navigation_misroute" in acceptance_tests_text
    assert "assistant_context_builders_are_bounded_and_topic_scoped" in acceptance_tests_text
    assert "assistant_local_fallback_cannot_invent_current_regime" in acceptance_tests_text
    assert "below_floor_shadow_pass_is_non_authorizing" in acceptance_tests_text
    assert "best_shadow_pass_lane_drives_bounded_paper_admission" in acceptance_tests_text
    assert "paper_shadow_pass_policy_restores_candidate_flow_after_invalid_model" in acceptance_tests_text
    assert "restored_candidate_reaches_immediate_operator_and_mt5_demo" in acceptance_tests_text
    assert "exhausted_claude_budget_uses_working_local_operator_model" in acceptance_tests_text
    assert "local_operator_structured_decisions_survive_paid_budget_exhaustion" in acceptance_tests_text
    assert "daily_realized_loss_cap_blocks_model_and_degraded_fallback_entries" in acceptance_tests_text
    assert "explicit_actionless_select_normalizes_to_stand_down_only" in acceptance_tests_text
    assert "noncanonical_position_hold_is_bounded_and_mutations_fail_closed" in acceptance_tests_text
    assert "omitted_position_decision_becomes_audited_stand_down" in acceptance_tests_text
    assert "execution_receipt_time_overrides_materially_future_broker_position_time" in acceptance_tests_text
    assert "natural_operator_management_receipt_binds_decision_execution_and_learning" in acceptance_tests_text
    assert "model_response_contract_rejection_is_not_reported_as_provider_outage" in acceptance_tests_text
    assert "settings_and_management_runtime_share_active_scheduler_broker_truth" in acceptance_tests_text
    assert "review_interval_deferral_is_not_operator_stand_down" in acceptance_tests_text
    assert "local_entry_and_position_models_receive_exact_json_schema" in acceptance_tests_text
    assert "unique_bare_ticket_key_normalizes_without_relaxing_action_authority" in acceptance_tests_text
    assert "dual_chat_surfaces_disclose_answer_source" in acceptance_tests_text
    assert "natural_local_model_scale_in_executes_and_reconciles" in acceptance_tests_text
    assert "repeated_low_exposure_position_cap_starvation_reaches_operator" in acceptance_tests_text
    assert "position_capacity_widening_revalidates_fresh_mt5_state_at_apply_time" in acceptance_tests_text
    assert "every_fresh_position_receives_operator_discretion_without_fixed_threshold" in acceptance_tests_text
    assert "same_symbol_positions_receive_ticket_scoped_operator_choices" in acceptance_tests_text
    assert "operator_discretion_model_failure_never_auto_closes_position" in acceptance_tests_text
    assert "explicit_owner_risk_override_survives_api_restart" in acceptance_tests_text
    assert "risk_preview_uses_effective_dispatch_posture" in acceptance_tests_text
    assert "current_mt5_account_truth_replaces_stale_verifier_across_cockpit" in acceptance_tests_text
    assert "secondary_simulator_never_masquerades_as_active_mt5_account" in acceptance_tests_text
    assert "open_pnl_and_growth_measurement_include_reported_carry_costs" in acceptance_tests_text
    assert "mt5_cashflow_adjusted_realized_growth_reconciles_to_balance" in acceptance_tests_text
    assert "recent_outcome_logic_uses_chronological_broker_closes" in acceptance_tests_text
    assert "learning_groups_rank_after_cost_expectancy_before_win_rate" in acceptance_tests_text
    assert "adaptation_promotion_requires_exact_profitable_behavior_group" in acceptance_tests_text
    assert "operator_approval_requires_explicit_sizing_ref" in acceptance_tests_text
    assert "paper_model_failure_cannot_recycle_known_losing_group_or_press_size" in acceptance_tests_text
    assert "learning_ranking_normalizes_historical_lot_size" in acceptance_tests_text
    assert "dispatch_retains_timeframe_for_outcome_learning" in acceptance_tests_text
    assert "position_prompt_preserves_after_cost_ranking_and_origin" in acceptance_tests_text
    assert "management_actions_expose_immediate_growth_effect" in acceptance_tests_text
    assert "scale_in_r_uses_original_entry_stop_after_breakeven" in acceptance_tests_text
    assert "tiny_winner_realization_close_requires_explicit_growth_case" in acceptance_tests_text
    assert "contradictory_select_close_and_hold_language_stands_down" in acceptance_tests_text
    assert "autonomous_broker_effect_receipt_binds_actual_operator_identity" in acceptance_tests_text
    assert "historical_admission_risk_recomputed_from_broker_tick_contract" in acceptance_tests_text
    assert "learning_ranking_prefers_after_cost_r_expectancy_across_instruments" in acceptance_tests_text
    assert "incomplete_admission_risk_cannot_promote_or_supply_press_evidence" in acceptance_tests_text
    assert "entry_projection_uses_historical_r_expectancy_times_current_stop_risk" in acceptance_tests_text
    assert "operator_growth_ranking_prompt_is_well_formed" in acceptance_tests_text
    assert "broker_aliases_share_learning_promotion_and_exposure_identity" in acceptance_tests_text
    assert "operator_observability_remains_responsive_during_slow_evidence_refresh" in acceptance_tests_text
    assert "late_completed_trading_model_result_is_single_use_and_kind_bound" in acceptance_tests_text
    assert "model_ready_requires_fresh_successful_generation" in acceptance_tests_text
    assert "operator_chat_preserves_north_star_account_truth_under_context_pressure" in acceptance_tests_text
    assert "Management handoff inspects the wrong account runtime" in red_team_text
    assert "Review pacing is mislabeled as an AI stand-down" in red_team_text
    assert "Generic JSON mode corrupts local trading decisions" in red_team_text
    assert "Bare ticket spelling silently erases a valid exact decision" in red_team_text
    assert "Chat reply source is hidden or misrepresented" in red_team_text
    assert "Low-exposure position cap silently starves Operator entries" in red_team_text
    assert "Stale or hallucinated account truth reaches owner chat" in red_team_text
    assert "Configured model or role label masks real capability" in red_team_text
    assert "PASS_BOUNDED_CAPACITY_RECOVERY" in sources_text
    assert "Position-capacity pressure evidence" in sources_text
    assert "Post-capacity Operator MT5 demo receipt" in sources_text
    assert "Direct local-model scale-in receipt" in sources_text
    assert "Active-account dual-chat truth proof" in sources_text
    assert "redteam-active-account-chat-truth-latest.json" in sources_text
    assert "North-star account priority" in operator_contracts_text
    assert "Position stop-risk context" in operator_contracts_text
    assert "UNAVAILABLE" not in ai_edge_text
    assert "AI edge layer unavailable from Python" not in ai_edge_text
