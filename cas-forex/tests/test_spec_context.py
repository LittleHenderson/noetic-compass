from __future__ import annotations

import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex import spec_context
from ui_contract import assert_panel_wired


def _cell(ref: str, text: str) -> str:
    return (
        f'<c r="{ref}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'
    )


def _sheet(rows: list[list[str]]) -> str:
    xml_rows: list[str] = []
    for row_idx, row in enumerate(rows, start=1):
        cells = []
        for col_idx, value in enumerate(row):
            col = chr(ord("A") + col_idx)
            cells.append(_cell(f"{col}{row_idx}", value))
        xml_rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        "</worksheet>"
    )


def _write_minimal_xlsx(path: Path) -> None:
    sheets = {
        "sheet1.xml": ("Cover", [["Field", "Value"], ["Primary objective", "Grow balance"], ["Token", "cas_owner_token=abc123&secret-token"]]),
        "sheet2.xml": ("AI Operator Chat", [["Area", "Spec"], ["Autonomous authority", "Operator may trade and move configured money inside owner-delegated gates"]]),
        "sheet3.xml": ("Evidence Status", [["Gate", "Current", "Status"], ["Phone proof", "false", "PENDING"], ["APK proof", "false", "PENDING"]]),
        "sheet4.xml": ("Owner Runbook", [["Step", "Action", "Command"], ["3", "Run live watcher", "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"]]),
    }
    workbook_sheets = []
    rels = []
    for idx, (file_name, (name, _rows)) in enumerate(sheets.items(), start=1):
        workbook_sheets.append(f'<sheet name="{name}" sheetId="{idx}" r:id="rId{idx}"/>')
        rels.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/{file_name}"/>'
        )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rIdWorkbook" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{"".join(workbook_sheets)}</sheets>'
            "</workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{"".join(rels)}'
            "</Relationships>",
        )
        for file_name, (_name, rows) in sheets.items():
            zf.writestr(f"xl/worksheets/{file_name}", _sheet(rows))


def test_spec_context_snapshot_from_xlsx_is_redacted_and_writes_artifacts(tmp_path):
    source = tmp_path / "spec.xlsx"
    _write_minimal_xlsx(source)

    snapshot = spec_context.write_snapshot(source, output_dir=tmp_path / "out")
    serialized = json.dumps(snapshot, sort_keys=True)

    assert snapshot["report_kind"] == "cas_forex_spec_context_snapshot"
    assert snapshot["version"].startswith("spec-")
    assert snapshot["generated_at"]
    assert snapshot["source"]["sha256"]
    assert snapshot["snapshot_hash_sha256"]
    assert len(snapshot["sheets"]) == 4
    assert "CAS Forex Spec Context" in snapshot["assistant_context_markdown"]
    assert "CAS Forex Operator Constitution" in snapshot["operator_constitution_markdown"]
    assert "AI Hedge Intelligence Layer" in snapshot["assistant_context_markdown"]
    assert "AI Hedge Intelligence Layer" in snapshot["operator_constitution_markdown"]
    assert "sustainable realized net account growth" in snapshot["operator_constitution_markdown"]
    assert "select_exact_broker_grid_lot_size" in snapshot["operator_constitution_markdown"]
    assert "0.01 is a broker floor, not a permanent lot-size policy" in snapshot["operator_constitution_markdown"]
    assert "conviction cannot substitute" in snapshot["operator_constitution_markdown"]
    assert "broker-valued after-cost R expectancy" in snapshot["operator_constitution_markdown"]
    assert "without per-add human confirmation" in snapshot["operator_constitution_markdown"]
    assert snapshot["ai_hedge_intelligence_layer"]["status"] == "SPECIFIED_GOVERNED_LAYER"
    assert snapshot["autonomous_execution_correction"]["version"] == "2026-07-09-AUTONOMOUS-EXECUTION-CORRECTION"
    assert snapshot["autonomous_execution_correction"]["human_in_loop"]["per_order_required"] is False
    assert "live authority is still pending" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["paper_learning_continuity"]
    assert "set_take_profit" in snapshot["autonomous_execution_correction"]["autonomous_trading_authority"]["allowed_actions"]
    assert "stale_broker_truth" in snapshot["autonomous_execution_correction"]["hard_blocks"]
    assert "authority_model" in snapshot["autonomous_execution_correction"]
    assert "normal_live_operation" in {
        row["level"] for row in snapshot["autonomous_execution_correction"]["authority_model"]["human_involvement_levels"]
    }
    assert "receipt_or_rejection_reason" in snapshot["autonomous_execution_correction"]["required_logs_and_evidence"]
    assert "current MT5 account snapshot" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["active_account_source_precedence"]
    assert "price P&L" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["after_cost_growth_measurement"]
    assert "non-optional priority" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["operator_north_star_context_precedence"]
    assert "operator_context_compaction_drops_active_account_cost_truth" in snapshot[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "pre_cost_winner_compounded_while_net_losing" in snapshot[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "position_decision_reused_after_account_or_cost_state_changed" in snapshot[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "deposit_or_withdrawal_counted_as_trading_profit" in snapshot[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "stale_or_other_account_growth_baseline_used" in snapshot[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "balance_baseline_claimed_without_full_deal_ledger_tie" in snapshot[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    for hard_block in (
        "out_of_order_outcomes_drive_recent_loss_logic",
        "cross_timeframe_outcomes_pooled_for_adaptation",
        "win_rate_ranked_ahead_of_after_cost_expectancy",
        "pooled_profit_promotes_unprofitable_behavior_group",
        "historical_lot_size_confounds_strategy_edge",
        "operator_conviction_substitutes_for_missing_sizing_ref",
        "position_prompt_negates_after_cost_ranking",
        "position_action_hides_immediate_realization_effect",
        "route_timeframe_lost_before_outcome_learning_join",
        "stored_pre_trade_risk_used_without_broker_contract_recalculation",
        "per_lot_dollars_compared_across_instruments_as_edge",
        "incomplete_admission_risk_promotes_behavior",
        "malformed_prompt_assembly_obscures_growth_ranking",
        "broker_alias_fragmentation_hides_outcomes_or_exposure",
        "observational_poll_blocks_operator_chat_or_execution_control",
    ):
        assert hard_block in snapshot["autonomous_execution_correction"]["hard_blocks"]
    assert "degraded_paper_fallback_opens_new_exposure_after_daily_realized_loss_cap" in snapshot[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "execution_guard.py checks it again" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["daily_realized_loss_cap_enforcement"]
    assert "after-cost expectancy" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["exact_group_after_cost_learning"]
    assert "broker tick size" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["historical_admission_risk_reconstruction"]
    assert "canonical CAS instrument" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["canonical_broker_alias_market_identity"]
    assert "single-flight cache" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["non_blocking_operator_observability"]
    trading_model_contract = snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["non_blocking_trading_model_decisions"]
    assert "exactly once" in trading_model_contract
    assert "same decision kind" in trading_model_contract
    assert "RAM or VRAM capacity" in trading_model_contract
    hard_blocks = snapshot["autonomous_execution_correction"]["hard_blocks"]
    assert "failed_or_stale_model_capability_reported_as_ready" in hard_blocks
    assert (
        "configured_gemma_backup_label_masks_missing_failover_capability"
        in hard_blocks
    )
    assert (
        "structured_model_output_fence_or_commentary_breaks_action_json"
        in hard_blocks
    )
    assert "late_completed_model_decision_discarded_without_single_use_delivery" in hard_blocks
    assert "late_model_result_delivered_to_different_decision_kind" in hard_blocks
    acceptance_names = {
        row["name"]
        for row in snapshot["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "late_completed_trading_model_result_is_single_use_and_kind_bound" in acceptance_names
    assert "model_ready_requires_fresh_successful_generation" in acceptance_names
    assert (
        "gemma4_31b_cloud_backup_is_capability_probed_and_failover_bound"
        in acceptance_names
    )
    assert "gemma4:31b-cloud" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["gemma4_large_model_backup"]
    assert "after-cost R expectancy" in snapshot["operator_constitution_markdown"]
    assert "full MT5 deal" in snapshot["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["reconciled_cashflow_adjusted_realized_growth"]
    assert "Acceptance Tests" in snapshot["assistant_context_markdown"]
    assert "adaptive trading edge engine" in snapshot["ai_hedge_intelligence_layer"]["thesis"]
    assert "create and maintain edge" in snapshot["ai_hedge_intelligence_layer"]["edge_role"]
    assert "score_edge" in snapshot["ai_hedge_intelligence_layer"]["allowed_operator_edge_decisions"]
    assert "trade_management_intelligence" in {
        row["key"] for row in snapshot["ai_hedge_intelligence_layer"]["layers"]
    }
    assert "trading_edge_intelligence" in {
        row["key"] for row in snapshot["ai_hedge_intelligence_layer"]["layers"]
    }
    assert "Run live watcher" in snapshot["operator_constitution_markdown"]
    assert "cas_owner_token=abc123" not in serialized
    assert "secret-token" not in serialized
    assert "REDACTED" in serialized
    assert Path(snapshot["written_paths"]["json"]).exists()
    assert Path(snapshot["written_paths"]["markdown"]).exists()
    assert Path(snapshot["written_paths"]["operator_constitution"]).exists()


def test_google_sheet_url_is_converted_to_xlsx_export_url():
    url = "https://docs.google.com/spreadsheets/d/abc123/edit?usp=drivesdk&gid=456"
    assert spec_context._google_sheet_export_url(url) == (  # noqa: SLF001
        "https://docs.google.com/spreadsheets/d/abc123/export?format=xlsx&gid=456"
    )


def test_spec_context_status_report_exposes_chat_surfaces(tmp_path, monkeypatch):
    source = tmp_path / "spec.xlsx"
    out = tmp_path / "runtime" / "spec_context"
    _write_minimal_xlsx(source)
    monkeypatch.setenv(spec_context.DEFAULT_SOURCE_ENV, str(source))
    monkeypatch.setattr(spec_context, "DEFAULT_SNAPSHOT_DIR", out)
    monkeypatch.setattr(spec_context, "DEFAULT_JSON_PATH", out / "spec_context.json")
    monkeypatch.setattr(spec_context, "DEFAULT_MARKDOWN_PATH", out / "spec_context.md")
    monkeypatch.setattr(spec_context, "DEFAULT_OPERATOR_PATH", out / "operator_constitution.md")

    report = spec_context.build_status_report()

    assert report["report_kind"] == "cas_forex_spec_context_status"
    assert report["status"] == "OK"
    assert report["available"] is True
    assert report["source_found"] is True
    assert report["snapshot_stale"] is False
    assert report["assistant_prompt_available"] is True
    assert report["operator_prompt_available"] is True
    assert report["assistant_context_chars"] > 0
    assert report["operator_constitution_chars"] > 0
    assert report["ai_hedge_intelligence_layer"]["status"] == "SPECIFIED_GOVERNED_LAYER"
    assert report["autonomous_execution_correction"]["status"] == "GOVERNING_REPLACEMENT_LANGUAGE"
    assert report["autonomous_execution_correction"]["human_in_loop"]["per_configured_money_movement_required"] is False
    assert "master_kill_blocks_all_side_effects" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "live_pending_keeps_paper_learning_active" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "broker_tick_value_risk_cap_blocks_understated_index_order" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "open_position_stop_risk_reaches_operator_and_ui" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "sunday_reopen_and_tick_freshness_are_not_conflated" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "interrupted_demo_order_receipt_recovers_without_retry" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "dispatch_status_reports_running_while_rich_diagnostics_refresh" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "assistant_and_operator_answer_compounding_without_timeout_or_navigation_misroute" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "exhausted_claude_budget_uses_working_local_operator_model" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "daily_realized_loss_cap_blocks_model_and_degraded_fallback_entries" in {
        row["name"] for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "sunday_reopen_falsely_forced_closed" in report[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "broker_demo_execution_left_unfinalized_after_exact_history_match" in report[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "model_approval_bypasses_daily_realized_loss_cap" in report[
        "autonomous_execution_correction"
    ]["hard_blocks"]
    assert "ordinary Operator chat" in report["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]["open_position_stop_risk_insight"]
    controls = report["autonomous_execution_correction"][
        "correct_interpretation_of_existing_controls"
    ]
    assert "M1 and M5" in controls["adaptive_entry_timeframe_authority"]
    assert "research inputs only" in controls["fresh_micro_scalp_execution"]
    assert "no emission key" in controls["pre_emission_quote_truth"]
    names = {
        row["name"]
        for row in report["autonomous_execution_correction"]["acceptance_tests"]
    }
    assert "m1_m5_fresh_micro_scalp_reaches_operator_dispatch" in names
    assert "timeframe_scans_rotate_without_cross_cache_starvation" in names
    assert "closed_quote_cannot_consume_route_identity" in names
    assert "current_mt5_account_truth_replaces_stale_verifier_across_cockpit" in names
    assert "secondary_simulator_never_masquerades_as_active_mt5_account" in names
    assert "open_pnl_and_growth_measurement_include_reported_carry_costs" in names
    assert "mt5_cashflow_adjusted_realized_growth_reconciles_to_balance" in names
    assert "recent_outcome_logic_uses_chronological_broker_closes" in names
    assert "learning_groups_rank_after_cost_expectancy_before_win_rate" in names
    assert "adaptation_promotion_requires_exact_profitable_behavior_group" in names
    assert "operator_chat_preserves_north_star_account_truth_under_context_pressure" in names
    assert "operator_approval_requires_explicit_sizing_ref" in names
    assert "learning_ranking_normalizes_historical_lot_size" in names
    assert "dispatch_retains_timeframe_for_outcome_learning" in names
    assert "position_prompt_preserves_after_cost_ranking_and_origin" in names
    assert "management_actions_expose_immediate_growth_effect" in names
    assert "historical_admission_risk_recomputed_from_broker_tick_contract" in names
    assert "learning_ranking_prefers_after_cost_r_expectancy_across_instruments" in names
    assert "incomplete_admission_risk_cannot_promote_or_supply_press_evidence" in names
    assert "entry_projection_uses_historical_r_expectancy_times_current_stop_risk" in names
    assert "operator_growth_ranking_prompt_is_well_formed" in names
    assert "broker_aliases_share_learning_promotion_and_exposure_identity" in names
    assert "operator_observability_remains_responsive_during_slow_evidence_refresh" in names
    assert "scale_in_requires_net_profit_after_reported_open_costs" in names
    assert "position_decision_cache_invalidates_on_account_or_pnl_change" in names
    assert "scale_in_authorization_rechecks_parent_profit_and_geometry" in names
    assert "close_partial" in report["ai_hedge_intelligence_layer"]["allowed_trade_intents"]
    assert "set_take_profit" in report["ai_hedge_intelligence_layer"]["allowed_trade_intents"]
    assert report["sheet_count"] == 4
    assert report["refresh_command"] == "python scripts/refresh_spec_context.py"
    assert "floating_assistant" in report["surfaces"]
    assert "ai_operator" in report["surfaces"]
    assert "autonomously trade" in report["claim_boundary"]
    assert "cannot bypass runtime gates" in report["claim_boundary"]


def test_autonomous_execution_yaml_stays_in_sync_with_runtime_spec_context():
    assert spec_context.AUTONOMOUS_EXECUTION_CORRECTION_YAML_PATH.exists()

    yaml_payload = yaml.safe_load(
        spec_context.AUTONOMOUS_EXECUTION_CORRECTION_YAML_PATH.read_text(encoding="utf-8")
    )
    normalized_yaml = spec_context._normalize_autonomous_execution_correction_payload(yaml_payload)  # noqa: SLF001

    assert normalized_yaml["status"] == "GOVERNING_REPLACEMENT_LANGUAGE"
    assert normalized_yaml["authority_model"]["owner_delegated_authority_envelope"][1] == "mode: paper, demo, live"
    assert normalized_yaml == spec_context.autonomous_execution_correction()


def test_ensure_snapshot_refreshes_when_cached_source_differs_from_latest_workbook(tmp_path, monkeypatch):
    canonical_source = tmp_path / "canonical.xlsx"
    stale_source = tmp_path / "stale.xlsx"
    _write_minimal_xlsx(canonical_source)
    _write_minimal_xlsx(stale_source)
    out = tmp_path / "runtime" / "spec_context"

    stale_snapshot = spec_context.write_snapshot(stale_source, output_dir=out)
    assert stale_snapshot["source"]["path_or_url"] == str(stale_source)

    monkeypatch.setattr(spec_context, "_find_latest_workbook", lambda: canonical_source)

    refreshed = spec_context.ensure_snapshot(output_dir=out)

    assert refreshed is not None
    assert refreshed["source"]["path_or_url"] == str(canonical_source)


def test_spec_context_status_route_serves_current_snapshot_directly(monkeypatch):
    current = {
        "report_kind": "cas_forex_spec_context_status",
        "status": "OK",
        "available": True,
        "version": "spec-current",
        "assistant_prompt_available": True,
        "operator_prompt_available": True,
    }
    monkeypatch.setattr(
        settings_route,
        "build_spec_context_status_report",
        lambda: dict(current),
    )

    import asyncio

    body = asyncio.run(settings_route.get_spec_context())

    assert body == current


def test_spec_context_settings_ui_and_trace_skip_are_wired():
    repo = Path(__file__).resolve().parents[1]
    settings_page = (repo / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (repo / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("SpecContextPanel")
    # These panels moved to components/settings/SpecContextPanel.tsx in the settings decomposition.
    extracted_panel = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "SpecContextPanel.tsx").read_text(encoding="utf-8")
    assert "Spec Context" in extracted_panel
    assert "AI Operator Edge" in extracted_panel
    assert "Edge Decisions" in extracted_panel
    assert "Allowed Intents" in extracted_panel
    assert "Hard Boundaries" in extracted_panel
    assert "fetchSpecContextStatus" in extracted_panel
    assert "SpecContextStatusReport" in api_client
    assert "AiHedgeIntelligenceLayer" in api_client
    assert "ai_hedge_intelligence_layer" in api_client
    assert "AutonomousExecutionCorrection" in api_client
    assert "autonomous_execution_correction" in api_client
    assert "Autonomous Correction" in extracted_panel
    assert '"/settings/spec-context"' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/spec-context") is False
