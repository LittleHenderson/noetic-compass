from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from api.routes import settings as settings_route
from cas_forex import live_enable_control, operator_secrets, owner_auth, push_delivery_control
from cas_forex.security_posture import build_security_posture_report
from ui_contract import assert_panel_wired


REPO_ROOT = Path(__file__).resolve().parents[1]


def _config(**overrides):
    data = {
        "live_mode": True,
        "paper_trading": False,
        "prefer_mt5": True,
        "mt5_login": 1000694,
        "mt5_password": "MT5_SUPER_SECRET_1234",
        "mt5_server": "HUGOSWAY-DEMO",
        "owner_enable_live_trading": True,
        "live_trading_licensed": True,
        "mt5_treat_account_as_demo": True,
        "payment_provider": "stripe",
        "payment_api_key": "PAYMENT_SECRET_9876",
        "payout_destination_id": "dest_test",
        "payout_destination_allowlisted": False,
        "oanda_api_key": "OANDA_SECRET_5555",
        "timegpt_api_key": "TIMEGPT_SECRET_1111",
        "ai_model_api_key": "MODEL_SECRET_2222",
        "ai_operator_primary_api_key": "",
        "ai_operator_deepseek_api_key": "",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_security_posture_masks_secret_material_and_reports_permissions(tmp_path, monkeypatch):
    monkeypatch.delenv("CAS_FOREX_OWNER_TOKEN", raising=False)
    monkeypatch.delenv("CAS_FOREX_CLOUD_MODE", raising=False)
    owner_auth.set_auth_path_for_tests(tmp_path / "owner-auth.json")
    operator_secrets.set_secrets_path_for_tests(tmp_path / "operator-secrets.json")
    try:
        operator_secrets.set_secret("primary_api_key", "OPERATOR_SECRET_9999")
        operator_secrets.set_secret("deepseek_api_key", "DEEPSEEK_SECRET_8888")
        owner_auth.set_lan_mode(True)
        owner_token = owner_auth.current_token()
        assert owner_token

        report = build_security_posture_report(_config())
    finally:
        owner_auth.set_auth_path_for_tests(None)
        operator_secrets.set_secrets_path_for_tests(None)

    payload = json.dumps(report, sort_keys=True)
    for raw_secret in (
        "MT5_SUPER_SECRET_1234",
        "PAYMENT_SECRET_9876",
        "OANDA_SECRET_5555",
        "TIMEGPT_SECRET_1111",
        "MODEL_SECRET_2222",
        "OPERATOR_SECRET_9999",
        "DEEPSEEK_SECRET_8888",
        owner_token,
    ):
        assert raw_secret not in payload

    assert report["report_kind"] == "cas_forex_security_posture"
    assert report["owner_auth"]["lan_mode_enabled"] is True
    assert report["owner_auth"]["owner_token_present"] is True
    assert report["owner_auth"]["owner_token_runtime_store_encrypted_at_rest"] is True
    assert report["owner_auth"]["owner_token_env_source_present"] is False
    assert report["managed_secret_store"]["report_kind"] == "cas_forex_managed_secret_store"
    assert report["managed_secret_store"]["server_side_only"] is True
    assert report["managed_secret_store"]["raw_secret_returned"] is False
    assert report["managed_secret_store"]["runtime_secret_envelope"]["at_rest_encrypted"] is True
    assert report["permission_surface"]["live_mode"] is True
    assert report["permission_surface"]["mt5_password_present"] is True
    assert report["permission_surface"]["mt5_treat_account_as_demo"] is True
    assert any("MT5_TREAT_ACCOUNT_AS_DEMO" in item for item in report["attention_items"])
    role_model = report["role_permission_model"]
    assert role_model["report_kind"] == "cas_forex_role_permission_model"
    assert role_model["authorization_model"] == "single_owner_local_app_with_owner_token_for_off_box_access"
    assert role_model["mfa_status"] == "PARTIAL_LOCAL_CHALLENGE"
    assert role_model["live_action_second_factor"]["status"] == "ENFORCED_BY_TYPED_CONFIRMATION"
    assert "route-level typed confirmation" in " ".join(role_model["live_action_second_factor"]["factors"])
    assert "TOTP" in role_model["live_action_second_factor"]["not_implemented"]
    assert role_model["mfa_hardening_backlog"]
    route_policy = role_model["route_permission_policy"]
    assert route_policy["report_kind"] == "cas_forex_route_permission_policy"
    assert route_policy["status"] == "OK"
    assert route_policy["enforcement"] == "api.middleware.owner_auth_gate"
    assert route_policy["money_or_live_sensitive_rule_count"] >= 6
    assert route_policy["loopback_only_rule_count"] >= 3
    assert "default_mutation_route_count" in route_policy
    assert "coverage_status" in route_policy
    roles = {row["role_key"]: row for row in role_model["roles"]}
    assert roles["local_owner_loopback"]["can_pair_device"] is True
    assert roles["local_owner_loopback"]["can_read_raw_secrets"] is False
    assert roles["paired_owner_device"]["can_rotate_owner_token"] is False
    assert roles["ai_operator_system"]["can_change_ai_dials"] is True
    assert roles["ai_operator_system"]["can_submit_live_order"] is False
    assert roles["broker_bridge_system"]["can_submit_live_order"] is True
    assert roles["support_diagnostics"]["can_move_money"] is False

    inventory = {row["key"]: row for row in report["server_secret_inventory"]}
    assert inventory["mt5_password"]["configured"] is True
    assert inventory["mt5_password"]["browser_exposed"] is False
    assert inventory["payment_api_key"]["configured"] is True
    assert inventory["payment_api_key"]["runtime_override_set"] is False
    assert inventory["payment_api_key"]["runtime_override_encrypted_at_rest"] is False
    assert inventory["payment_api_key"]["plaintext_config_source_present"] is True
    assert inventory["payment_api_key"]["plaintext_local_storage"] is True
    assert inventory["ai_operator_primary_api_key"]["configured"] is True
    assert inventory["ai_operator_primary_api_key"]["storage"] == "runtime encrypted operator secret store"
    assert inventory["ai_operator_primary_api_key"]["runtime_secret_store_set"] is True
    assert inventory["ai_operator_primary_api_key"]["runtime_secret_store_encrypted_at_rest"] is True
    assert inventory["ai_operator_primary_api_key"]["plaintext_config_source_present"] is False
    assert inventory["ai_operator_primary_api_key"]["plaintext_local_storage"] is False
    assert inventory["ai_operator_deepseek_api_key"]["configured"] is True
    assert inventory["ai_operator_deepseek_api_key"]["storage"] == "runtime encrypted operator secret store"
    assert inventory["ai_operator_deepseek_api_key"]["runtime_secret_store_set"] is True
    assert inventory["ai_operator_deepseek_api_key"]["runtime_secret_store_encrypted_at_rest"] is True
    assert inventory["ai_operator_deepseek_api_key"]["plaintext_config_source_present"] is False
    assert inventory["ai_operator_deepseek_api_key"]["plaintext_local_storage"] is False
    assert inventory["owner_token"]["browser_exposed"] is True
    assert inventory["owner_token"]["runtime_secret_store_set"] is True
    assert inventory["owner_token"]["runtime_secret_store_encrypted_at_rest"] is True
    assert inventory["owner_token"]["plaintext_local_storage"] is False
    assert inventory["web_push_vapid_private_key"]["configured"] is False


def test_security_posture_reports_encrypted_runtime_payment_key(tmp_path):
    path = tmp_path / "live-enable-overrides.json"
    live_enable_control.set_live_enable_override_store_for_tests(path)
    try:
        live_enable_control.set_live_enable_overrides(
            payment_provider="wise",
            payment_api_key="PAYMENT_RUNTIME_SECRET_123",
            payout_destination_id="dest-runtime",
        )
        report = build_security_posture_report(
            _config(payment_provider="", payment_api_key="", payout_destination_id="")
        )
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)

    payload = json.dumps(report, sort_keys=True)
    assert "PAYMENT_RUNTIME_SECRET_123" not in payload

    inventory = {row["key"]: row for row in report["server_secret_inventory"]}
    payment = inventory["payment_api_key"]
    assert payment["configured"] is True
    assert payment["storage"] == "runtime encrypted envelope"
    assert payment["runtime_override_set"] is True
    assert payment["runtime_override_encrypted_at_rest"] is True
    assert payment["plaintext_config_source_present"] is False
    assert payment["plaintext_local_storage"] is False
    assert payment["runtime_secret_storage"]["at_rest_encrypted"] is True


def test_security_posture_ignore_coverage_matches_repo_contract():
    report = build_security_posture_report(_config(mt5_treat_account_as_demo=False))
    ignore = report["ignore_coverage"]

    assert ignore["gitignore_present"] is True
    assert ignore["env_ignored_by_git"] is True
    assert ignore["evidence_runs_ignored_by_git"] is True
    assert ignore["runtime_ignored_by_git"] is True
    assert ignore["evidence_runs_ignored_by_docker"] is True
    assert ignore["runtime_ignored_by_docker"] is True
    assert ignore["push_delivery_override_store_path"] == "runtime/push-delivery-overrides.json"
    assert ignore["push_subscription_store_path"] == "evidence_runs/push_subscriptions/subscriptions.jsonl"
    assert ignore["webhook_subscription_store_path"] == "evidence_runs/webhook_subscriptions/subscriptions.jsonl"


def test_security_posture_reports_runtime_vapid_private_key(tmp_path, monkeypatch):
    push_delivery_control.set_override_path_for_tests(tmp_path / "push-delivery-overrides.json")
    monkeypatch.setattr(
        push_delivery_control,
        "probe_push_delivery_backend",
        lambda: {"available": True, "package": "pywebpush", "version": "2.3.0"},
    )
    try:
        push_delivery_control.set_push_delivery_overrides(
            vapid_private_key="PRIVATE_KEY_0987654321",
        )
        report = build_security_posture_report(_config())
    finally:
        push_delivery_control.clear_push_delivery_overrides()
        push_delivery_control.set_override_path_for_tests(None)

    payload = json.dumps(report, sort_keys=True)
    assert "PRIVATE_KEY_0987654321" not in payload
    inventory = {row["key"]: row for row in report["server_secret_inventory"]}
    vapid_private = inventory["web_push_vapid_private_key"]
    assert vapid_private["configured"] is True
    assert vapid_private["runtime_override_set"] is True
    assert vapid_private["runtime_override_encrypted_at_rest"] is True
    assert vapid_private["plaintext_config_source_present"] is False
    assert vapid_private["plaintext_local_storage"] is False


def test_security_posture_route_is_cache_first_and_read_only(monkeypatch):
    captured: dict[str, object] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "builder_callable": callable(builder),
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(settings_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(settings_route.get_security_posture())

    assert captured == {
        "key": "settings_security_posture",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_security_posture"
    assert body["status"] == "WARMING"
    assert body["role_permission_model"]["status"] == "WARMING"
    assert body["role_permission_model"]["route_permission_policy"]["status"] == "WARMING"
    assert "raw" in body["claim_boundary"]


def test_settings_ui_exposes_security_posture_panel():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")

    assert_panel_wired("SecurityPosturePanel")
    # Moved to components/settings/SecurityPosturePanel.tsx in the settings decomposition (slice 2).
    extracted_securityposturepanel = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "SecurityPosturePanel.tsx").read_text(encoding="utf-8")
    assert "fetchSecurityPosture" in extracted_securityposturepanel
    assert "Browser Secret Policy" in extracted_securityposturepanel
    assert "Role Permission Model" in extracted_securityposturepanel
    assert "Managed Secret Store" in extracted_securityposturepanel
    assert "managed_secret_store" in (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    assert "MFA Status" in extracted_securityposturepanel
    assert "Live Action 2nd Factor" in extracted_securityposturepanel
    assert "Route Permission Policy" in extracted_securityposturepanel
    assert "Default Mutations" in extracted_securityposturepanel
    assert "default_mutation_route_count" in extracted_securityposturepanel
    assert "coverage_status" in extracted_securityposturepanel
    assert "route_permission_policy" in extracted_securityposturepanel
    assert "route_permission_policy" in (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    assert "mfa_hardening_backlog" in extracted_securityposturepanel
    assert "can_submit_live_order" in extracted_securityposturepanel
    assert "Security posture is read-only and never returns raw secrets." in extracted_securityposturepanel
