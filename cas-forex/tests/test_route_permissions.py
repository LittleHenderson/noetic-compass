from __future__ import annotations

import json

import pytest

from cas_forex import owner_auth, route_permissions


@pytest.fixture(autouse=True)
def _isolated_owner_auth(tmp_path, monkeypatch):
    monkeypatch.delenv("CAS_FOREX_OWNER_TOKEN", raising=False)
    monkeypatch.delenv("CAS_FOREX_CLOUD_MODE", raising=False)
    owner_auth.set_auth_path_for_tests(tmp_path / "owner-auth.json")
    yield
    owner_auth.set_auth_path_for_tests(None)


def _decision(method: str, path: str, *, host: str = "127.0.0.1", headers=None) -> dict:
    return route_permissions.evaluate_route_permission(
        method=method,
        path=path,
        client_host=host,
        headers=headers or {},
    )


def test_loopback_owner_can_reach_live_sensitive_dispatch_route():
    decision = _decision("POST", "/api/forex/order-dispatch/manual")

    assert decision["allowed"] is True
    assert decision["role_key"] == "local_owner_loopback"
    assert decision["required_permission"] == "submit_order"
    assert decision["route_category"] == "manual_order_dispatch"
    assert decision["money_or_live_sensitive"] is True
    assert decision["typed_confirmation_required"] is True

    management = _decision("POST", "/api/forex/ai-hedge-management/execute")
    assert management["allowed"] is True
    assert management["required_permission"] == "submit_order"
    assert management["route_category"] == "ai_hedge_management_execution"
    assert management["money_or_live_sensitive"] is True
    assert management["typed_confirmation_required"] is True


def test_unpaired_offbox_browser_cannot_mutate_owner_or_order_routes():
    live_enable = _decision("POST", "/api/forex/live-enable/update", host="10.0.0.44")
    order = _decision("POST", "/api/forex/order-dispatch/run", host="10.0.0.44")

    assert live_enable["allowed"] is False
    assert live_enable["role_key"] == "browser_viewer_unpaired"
    assert live_enable["required_permission"] == "arm_live_authority"
    assert order["allowed"] is False
    assert order["required_permission"] == "submit_order"


def test_paired_owner_device_can_request_gated_money_routes_but_not_loopback_pairing():
    owner_auth.set_lan_mode(True)
    token = owner_auth.current_token()
    assert token
    headers = {"X-CAS-Owner-Token": token}

    payout = _decision(
        "POST",
        "/api/forex/money-movement/payout",
        host="10.0.0.44",
        headers=headers,
    )
    pairing = _decision(
        "GET",
        "/api/forex/owner-auth/pairing",
        host="10.0.0.44",
        headers=headers,
    )

    assert payout["allowed"] is True
    assert payout["role_key"] == "paired_owner_device"
    assert payout["required_permission"] == "move_money"
    assert payout["typed_confirmation_required"] is True
    assert pairing["allowed"] is False
    assert pairing["required_permission"] == "pair_device"
    assert pairing["loopback_only"] is True


def test_public_shell_and_health_stay_available_without_pairing():
    shell = _decision("GET", "/", host="10.0.0.44")
    health = _decision("GET", "/health", host="10.0.0.44")

    assert shell["allowed"] is True
    assert shell["required_permission"] == "view_public_shell"
    assert health["allowed"] is True
    assert health["required_permission"] == "view_health"


def test_preview_proxy_uses_forwarded_phone_role_for_permission_checks():
    decision = _decision(
        "POST",
        "/api/forex/live-enable/update",
        host="127.0.0.1",
        headers={"X-Forwarded-For": "10.0.0.44"},
    )

    assert decision["allowed"] is False
    assert decision["role_key"] == "browser_viewer_unpaired"
    assert decision["required_permission"] == "arm_live_authority"


def test_policy_report_is_safe_to_expose_and_covers_sensitive_routes():
    token = owner_auth.get_or_create_token()

    report = route_permissions.build_route_permission_policy_report()
    payload = json.dumps(report, sort_keys=True)

    assert report["report_kind"] == "cas_forex_route_permission_policy"
    assert report["status"] == "OK"
    assert report["enforcement"] == "api.middleware.owner_auth_gate"
    assert report["permission_count"] >= 10
    assert report["route_rule_count"] >= 20
    assert report["money_or_live_sensitive_rule_count"] >= 6
    assert report["loopback_only_rule_count"] >= 3
    assert token not in payload
    assert "submit_order" in payload
    assert "move_money" in payload


def test_policy_report_flags_unknown_default_mutations_when_inventory_is_supplied():
    report = route_permissions.build_route_permission_policy_report(
        route_inventory=[
            {"path": "/api/forex/unknown-owner-action", "methods": ["POST"]},
            {"path": "/api/forex/known-read", "methods": ["GET"]},
        ]
    )

    assert report["status"] == "ATTENTION"
    assert report["route_inventory_available"] is True
    assert report["default_mutation_route_count"] == 1
    assert report["default_mutation_routes"] == [
        {
            "method": "POST",
            "path": "/api/forex/unknown-owner-action",
            "permission": "change_owner_controls",
            "category": "owner_mutation",
        }
    ]


def test_current_fastapi_app_has_no_default_mutation_routes():
    from api.server import app

    inventory = [
        {
            "path": str(getattr(route, "path", "")),
            "methods": sorted(str(method).upper() for method in (getattr(route, "methods", None) or [])),
        }
        for route in app.routes
        if getattr(route, "path", None)
    ]
    report = route_permissions.build_route_permission_policy_report(route_inventory=inventory)

    assert report["status"] == "OK"
    assert report["route_inventory_available"] is True
    assert report["default_mutation_route_count"] == 0
    assert report["default_mutation_routes"] == []
