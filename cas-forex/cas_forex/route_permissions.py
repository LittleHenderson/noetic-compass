"""Deterministic route-permission policy for CAS Forex.

Owner auth answers "may this caller reach the API at all?" This module answers
"which role and permission does this route require?" The policy is intentionally
small and explicit so sensitive trading, broker, and money routes are visible in
one testable place instead of only being implied by UI buttons.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Mapping

from cas_forex import owner_auth


REPORT_KIND = "cas_forex_route_permission_policy"
CLAIM_BOUNDARY = (
    "Route permissions classify HTTP routes and enforce role-level access after "
    "owner admission. They do not authorize live trading, skip typed "
    "confirmation, bypass runtime gates, expose raw secrets, place orders, close "
    "positions, or move money."
)


PERMISSION_DEFINITIONS: dict[str, str] = {
    "view_public_shell": "Load the static web shell before pairing.",
    "view_health": "Read liveness and readiness probes.",
    "view_dashboard": "Read dashboard, account, strategy, audit, and diagnostic state.",
    "view_diagnostics": "Read or generate local diagnostic/support artifacts.",
    "pair_device": "Read the full owner token pairing packet from loopback only.",
    "change_lan_access": "Enable or disable authenticated LAN access from loopback only.",
    "rotate_owner_token": "Rotate the owner token from loopback only.",
    "change_owner_controls": "Change non-money owner controls and local operating state.",
    "change_ai_dials": "Change AI/operator settings, guidance, or bounded CAS dials.",
    "change_risk_controls": "Change risk caps and anti-impulse guarded risk settings.",
    "arm_live_authority": "Arm or disarm live-money authority switches.",
    "submit_order": "Request an order-dispatch route; runtime gates still decide.",
    "move_money": "Request deposit, withdrawal, payout, or sweep routes.",
    "run_broker_emergency": "Request close/cancel emergency broker actions.",
    "execute_owner_command": "Execute a brokered owner command after preview and confirmation.",
    "chat_with_operator": "Send an owner message to the AI operator/assistant.",
    "run_local_backup": "Create local diagnostic or backup artifacts.",
}


_PUBLIC_PERMISSIONS = frozenset({"view_public_shell", "view_health"})
_OWNER_PERMISSIONS = frozenset(PERMISSION_DEFINITIONS)
_PAIRED_OWNER_PERMISSIONS = _OWNER_PERMISSIONS - {
    "pair_device",
    "change_lan_access",
    "rotate_owner_token",
}


ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "local_owner_loopback": {
        "label": "Local Owner Loopback",
        "principal_type": "human_owner",
        "authentication": "PC loopback request; no owner token required outside cloud mode.",
        "permissions": sorted(_OWNER_PERMISSIONS),
    },
    "paired_owner_device": {
        "label": "Paired Owner Device",
        "principal_type": "human_owner_device",
        "authentication": "LAN/cloud request with a valid owner token.",
        "permissions": sorted(_PAIRED_OWNER_PERMISSIONS),
    },
    "browser_viewer_unpaired": {
        "label": "Unpaired Browser Viewer",
        "principal_type": "browser",
        "authentication": "No owner token.",
        "permissions": sorted(_PUBLIC_PERMISSIONS),
    },
    "ai_operator_system": {
        "label": "AI Operator System",
        "principal_type": "system_agent",
        "authentication": "In-process worker, not an HTTP browser role.",
        "permissions": sorted({"view_dashboard", "change_ai_dials", "chat_with_operator"}),
    },
    "broker_bridge_system": {
        "label": "Broker Bridge System",
        "principal_type": "system_adapter",
        "authentication": "Local MT4/MT5 adapter behind runtime gates.",
        "permissions": sorted({"submit_order", "run_broker_emergency"}),
    },
    "support_diagnostics": {
        "label": "Support Diagnostics",
        "principal_type": "read_only_support_export",
        "authentication": "No interactive support login is implemented.",
        "permissions": sorted({"view_diagnostics"}),
    },
}

_ROUTE_INVENTORY_PROVIDER: Callable[[], Iterable[Mapping[str, Any]]] | None = None


@dataclass(frozen=True)
class RoutePermissionRule:
    methods: tuple[str, ...]
    permission: str
    category: str
    path: str | None = None
    prefix: str | None = None
    loopback_only: bool = False
    money_or_live_sensitive: bool = False
    typed_confirmation_required: bool = False
    default_rule: bool = False
    note: str = ""

    def matches(self, method: str, path: str) -> bool:
        normalized_method = str(method or "").upper()
        if "*" not in self.methods and normalized_method not in self.methods:
            return False
        normalized_path = str(path or "")
        if self.path is not None:
            return normalized_path == self.path
        if self.prefix is not None:
            return normalized_path.startswith(self.prefix)
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "methods": list(self.methods),
            "path": self.path,
            "prefix": self.prefix,
            "permission": self.permission,
            "category": self.category,
            "loopback_only": self.loopback_only,
            "money_or_live_sensitive": self.money_or_live_sensitive,
            "typed_confirmation_required": self.typed_confirmation_required,
            "default_rule": self.default_rule,
            "note": self.note,
        }


_ROUTE_RULES: tuple[RoutePermissionRule, ...] = (
    RoutePermissionRule(("GET", "HEAD"), "view_health", "health", path="/health"),
    RoutePermissionRule(("GET", "HEAD"), "view_health", "health", prefix="/api/forex/health"),
    RoutePermissionRule(
        ("GET", "HEAD"),
        "pair_device",
        "owner_token_pairing",
        path="/api/forex/owner-auth/pairing",
        loopback_only=True,
        note="Full owner token is only served to the local PC.",
    ),
    RoutePermissionRule(
        ("POST",),
        "change_lan_access",
        "owner_network_access",
        path="/api/forex/owner-auth/lan-mode",
        loopback_only=True,
        note="LAN access can only be armed from loopback.",
    ),
    RoutePermissionRule(
        ("POST",),
        "rotate_owner_token",
        "owner_token_rotation",
        path="/api/forex/owner-auth/rotate",
        loopback_only=True,
        note="Token rotation unpairs devices and is loopback-only.",
    ),
    RoutePermissionRule(("GET", "HEAD"), "view_dashboard", "owner_auth_state", prefix="/api/forex/owner-auth"),
    RoutePermissionRule(
        ("POST",),
        "arm_live_authority",
        "live_authority",
        prefix="/api/forex/live-enable",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(
        ("POST",),
        "submit_order",
        "order_dispatch",
        prefix="/api/forex/order-dispatch/run",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(
        ("POST",),
        "submit_order",
        "manual_order_dispatch",
        prefix="/api/forex/order-dispatch/manual",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(
        ("POST",),
        "change_owner_controls",
        "order_attempt_reconciliation",
        prefix="/api/forex/order-dispatch/audit/reconcile-unresolved",
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(
        ("POST",),
        "submit_order",
        "live_order_handoff",
        prefix="/api/forex/live-order-dry-run",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(
        ("POST",),
        "submit_order",
        "dispatch_loop",
        prefix="/api/forex/dispatch-loop/start",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(("POST",), "change_owner_controls", "dispatch_loop", prefix="/api/forex/dispatch-loop/stop"),
    RoutePermissionRule(
        ("POST",),
        "submit_order",
        "waste_loop_live_runner",
        prefix="/api/forex/waste-loop-control/start",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(("POST",), "change_owner_controls", "waste_loop_control", prefix="/api/forex/waste-loop-control"),
    RoutePermissionRule(
        ("POST",),
        "run_broker_emergency",
        "broker_emergency",
        prefix="/api/forex/broker-emergency",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(
        ("POST",),
        "move_money",
        "money_movement",
        prefix="/api/forex/money-movement",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(("POST",), "change_risk_controls", "risk_control", prefix="/api/forex/risk-control"),
    RoutePermissionRule(("POST",), "change_ai_dials", "ai_control_authority", prefix="/api/forex/ai-control-authority"),
    RoutePermissionRule(("POST",), "chat_with_operator", "operator_chat", prefix="/api/forex/ai-operator/chat"),
    RoutePermissionRule(("POST",), "change_ai_dials", "operator_control", prefix="/api/forex/ai-operator"),
    RoutePermissionRule(("DELETE",), "change_ai_dials", "operator_guidance", prefix="/api/forex/ai-operator/guidance"),
    RoutePermissionRule(
        ("POST",),
        "submit_order",
        "ai_hedge_management_execution",
        prefix="/api/forex/ai-hedge-management/execute",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
        note="Confirmed management of existing broker positions; no new exposure intent.",
    ),
    RoutePermissionRule(("POST",), "chat_with_operator", "assistant_chat", prefix="/api/forex/assistant/chat"),
    RoutePermissionRule(("POST",), "change_owner_controls", "owner_control", prefix="/api/forex/settings/owner-control"),
    RoutePermissionRule(("POST",), "run_local_backup", "local_backup", prefix="/api/forex/settings/operator-backup"),
    RoutePermissionRule(
        ("POST",),
        "change_owner_controls",
        "legal_review_control_update",
        prefix="/api/forex/settings/legal-review-control/update",
        typed_confirmation_required=True,
        note="Writes owner-supplied qualified-counsel review metadata; no broker execution authority.",
    ),
    RoutePermissionRule(
        ("POST",),
        "change_owner_controls",
        "legal_review_control_reset",
        prefix="/api/forex/settings/legal-review-control/reset",
        note="Resets local counsel-review metadata; no broker execution authority.",
    ),
    RoutePermissionRule(
        ("POST",),
        "execute_owner_command",
        "owner_command",
        prefix="/api/forex/owner-command/execute",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(("POST",), "execute_owner_command", "owner_command_preview", prefix="/api/forex/owner-command"),
    RoutePermissionRule(
        ("POST",),
        "run_broker_emergency",
        "auto_halt",
        prefix="/api/forex/auto-halt/emergency-stop",
        money_or_live_sensitive=True,
        typed_confirmation_required=True,
    ),
    RoutePermissionRule(("POST",), "change_owner_controls", "auto_halt", prefix="/api/forex/auto-halt"),
    RoutePermissionRule(("POST",), "change_owner_controls", "broker_control", prefix="/api/forex/broker-control"),
    RoutePermissionRule(("POST",), "change_owner_controls", "mt4_bridge_control", prefix="/api/forex/mt4-bridge"),
    RoutePermissionRule(("POST",), "view_diagnostics", "mt5_live_refresh", prefix="/api/forex/mt5/refresh"),
    RoutePermissionRule(("POST",), "change_owner_controls", "proof_control", prefix="/api/forex/proof-control"),
    RoutePermissionRule(("POST",), "change_owner_controls", "live_pilot", prefix="/api/forex/live-pilot"),
    RoutePermissionRule(("POST",), "change_owner_controls", "live_recovery", prefix="/api/forex/live-recovery"),
    RoutePermissionRule(("POST",), "change_owner_controls", "broker_reality", prefix="/api/forex/broker-reality"),
    RoutePermissionRule(("POST",), "change_owner_controls", "mobile_verification", prefix="/api/forex/mobile"),
    RoutePermissionRule(("POST",), "change_ai_dials", "strategy_development", prefix="/api/forex/strategy-dev-actions"),
    RoutePermissionRule(("POST",), "change_ai_dials", "forex_fury_paper_promotion", prefix="/api/forex/forex-fury-promote/promote"),
    RoutePermissionRule(
        ("POST",),
        "change_owner_controls",
        "terminal_receipt_recovery_archive",
        prefix="/api/forex/strategy/terminal-receipt-recovery-packet/archive-stale",
        typed_confirmation_required=True,
        note="Owner cleanup of stale local terminal-receipt rows; no broker execution authority.",
    ),
    RoutePermissionRule(
        ("POST",),
        "run_local_backup",
        "terminal_receipt_recovery_refresh",
        prefix="/api/forex/strategy/terminal-receipt-recovery-packet/refresh-chain",
        note="Local evidence refresh chain; no broker execution authority.",
    ),
    RoutePermissionRule(("POST",), "change_owner_controls", "account_review", prefix="/api/forex/account/apply-broker-sync-risk-review"),
    RoutePermissionRule(("*",), "change_ai_dials", "timeframe_preferences", prefix="/api/forex/timeframes"),
    RoutePermissionRule(("POST",), "view_diagnostics", "notifications", prefix="/api/forex/notifications/test-push"),
    RoutePermissionRule(("POST",), "change_owner_controls", "notifications", prefix="/api/forex/notifications"),
    RoutePermissionRule(("POST",), "view_diagnostics", "webhook_notifications", prefix="/api/forex/webhook-notifications/test"),
    RoutePermissionRule(("POST",), "change_owner_controls", "webhook_notifications", prefix="/api/forex/webhook-notifications"),
    RoutePermissionRule(("POST",), "change_owner_controls", "external_monitoring", prefix="/api/forex/external-monitoring"),
    RoutePermissionRule(("POST",), "view_diagnostics", "operator_audit", prefix="/api/forex/operator-audit/record"),
    RoutePermissionRule(("POST",), "change_owner_controls", "broker_truth_monitor_control", prefix="/api/forex/broker-truth-monitor/start"),
    RoutePermissionRule(("POST",), "change_owner_controls", "broker_truth_monitor_control", prefix="/api/forex/broker-truth-monitor/stop"),
    RoutePermissionRule(("POST",), "view_diagnostics", "broker_truth_monitor_run_once", prefix="/api/forex/broker-truth-monitor/run-once"),
    RoutePermissionRule(
        ("POST",),
        "change_owner_controls",
        "broker_truth_monitor_supervisor_recovery",
        prefix="/api/forex/broker-truth-monitor/supervisor/recover",
        typed_confirmation_required=True,
        note="Clears only stale/stop-requested monitor leases after owner confirmation.",
    ),
)


_DEFAULT_READ_RULE = RoutePermissionRule(
    ("GET", "HEAD"),
    "view_dashboard",
    "read_only_api",
    prefix="/api/",
    default_rule=True,
    note="Default read-only API route.",
)
_DEFAULT_MUTATION_RULE = RoutePermissionRule(
    ("*",),
    "change_owner_controls",
    "owner_mutation",
    prefix="/api/",
    default_rule=True,
    note="Default API mutation route until given a more specific rule.",
)
_PUBLIC_SHELL_RULE = RoutePermissionRule(
    ("GET", "HEAD"),
    "view_public_shell",
    "public_web_shell",
    prefix="/",
    default_rule=True,
    note="The static shell can load before token pairing; API calls remain gated.",
)
_OPTIONS_RULE = RoutePermissionRule(
    ("OPTIONS",),
    "view_health",
    "cors_preflight",
    prefix="/",
    default_rule=True,
    note="CORS preflight carries no owner token and has no side effect.",
)


def resolve_http_role(
    *,
    method: str,
    client_host: str | None,
    path: str,
    headers: Mapping[str, str] | None = None,
) -> str:
    """Resolve the HTTP principal role without exposing any secret material."""
    del method, path
    request_headers = headers or {}
    if owner_auth.cloud_mode():
        if owner_auth.verify_token(owner_auth.extract_token(request_headers)):
            return "paired_owner_device"
        return "browser_viewer_unpaired"
    effective_host = owner_auth.effective_client_host(client_host, request_headers)
    if owner_auth.request_is_loopback(effective_host):
        return "local_owner_loopback"
    if owner_auth.lan_mode_enabled() and owner_auth.verify_token(owner_auth.extract_token(request_headers)):
        return "paired_owner_device"
    return "browser_viewer_unpaired"


def classify_route(method: str, path: str) -> RoutePermissionRule:
    normalized_method = str(method or "").upper()
    normalized_path = str(path or "")
    if normalized_method == "OPTIONS":
        return _OPTIONS_RULE
    for rule in _ROUTE_RULES:
        if rule.matches(normalized_method, normalized_path):
            return rule
    if _is_public_web_shell_request(normalized_method, normalized_path):
        return _PUBLIC_SHELL_RULE
    if normalized_method in {"GET", "HEAD"}:
        return _DEFAULT_READ_RULE
    return _DEFAULT_MUTATION_RULE


def evaluate_route_permission(
    *,
    method: str,
    path: str,
    client_host: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a safe allow/deny decision for one HTTP request."""
    rule = classify_route(method, path)
    role_key = resolve_http_role(method=method, client_host=client_host, path=path, headers=headers or {})
    role = ROLE_DEFINITIONS.get(role_key, ROLE_DEFINITIONS["browser_viewer_unpaired"])
    permissions = set(role.get("permissions") or [])

    if rule.loopback_only and role_key != "local_owner_loopback":
        allowed = False
        reason = "route is loopback-only"
        denied_status = 403
    elif rule.permission in permissions:
        allowed = True
        reason = "role has required permission"
        denied_status = 200
    else:
        allowed = False
        reason = "role lacks required permission"
        denied_status = 403

    return {
        "report_kind": "cas_forex_route_permission_decision",
        "allowed": allowed,
        "http_status_if_denied": denied_status,
        "reason": reason,
        "method": str(method or "").upper(),
        "path": str(path or ""),
        "role_key": role_key,
        "role_label": str(role.get("label") or role_key),
        "required_permission": rule.permission,
        "route_category": rule.category,
        "loopback_only": rule.loopback_only,
        "money_or_live_sensitive": rule.money_or_live_sensitive,
        "typed_confirmation_required": rule.typed_confirmation_required,
        "default_rule": rule.default_rule,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def set_route_inventory_provider(
    provider: Callable[[], Iterable[Mapping[str, Any]]] | None,
) -> None:
    """Register the API app's route inventory provider.

    The policy module deliberately avoids importing the FastAPI app. The server
    injects an inventory provider after all routes are registered so this
    report can prove actual route coverage without creating an import cycle.
    """

    global _ROUTE_INVENTORY_PROVIDER
    _ROUTE_INVENTORY_PROVIDER = provider


def build_route_permission_policy_report(
    route_inventory: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read-only policy report for security posture and professional readiness."""
    route_rules = [rule.to_dict() for rule in _ROUTE_RULES]
    sensitive_rules = [rule for rule in _ROUTE_RULES if rule.money_or_live_sensitive]
    loopback_only_rules = [rule for rule in _ROUTE_RULES if rule.loopback_only]
    coverage = _route_policy_coverage(route_inventory)
    permissions = [
        {"permission": key, "description": value}
        for key, value in sorted(PERMISSION_DEFINITIONS.items())
    ]
    roles = [
        {
            "role_key": key,
            "label": value.get("label"),
            "principal_type": value.get("principal_type"),
            "authentication": value.get("authentication"),
            "permissions": list(value.get("permissions") or []),
        }
        for key, value in ROLE_DEFINITIONS.items()
    ]
    status = "ATTENTION" if coverage.get("default_mutation_route_count", 0) else "OK"
    return {
        "report_kind": REPORT_KIND,
        "status": status,
        "enforcement": "api.middleware.owner_auth_gate",
        "authorization_model": "owner_auth_admission_plus_route_permission_policy",
        "default_read_permission": _DEFAULT_READ_RULE.permission,
        "default_mutation_permission": _DEFAULT_MUTATION_RULE.permission,
        "route_inventory_available": coverage["route_inventory_available"],
        "route_inventory_count": coverage["route_inventory_count"],
        "default_classified_route_count": coverage["default_classified_route_count"],
        "default_mutation_route_count": coverage["default_mutation_route_count"],
        "default_mutation_routes": coverage["default_mutation_routes"],
        "coverage_status": coverage["coverage_status"],
        "permission_count": len(PERMISSION_DEFINITIONS),
        "role_count": len(ROLE_DEFINITIONS),
        "route_rule_count": len(route_rules),
        "money_or_live_sensitive_rule_count": len(sensitive_rules),
        "loopback_only_rule_count": len(loopback_only_rules),
        "permissions": permissions,
        "roles": roles,
        "route_rules": route_rules,
        "default_rules": [
            _PUBLIC_SHELL_RULE.to_dict(),
            _OPTIONS_RULE.to_dict(),
            _DEFAULT_READ_RULE.to_dict(),
            _DEFAULT_MUTATION_RULE.to_dict(),
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _route_policy_coverage(route_inventory: Iterable[Mapping[str, Any]] | None) -> dict[str, Any]:
    inventory = list(_iter_route_inventory(route_inventory))
    if not inventory:
        return {
            "route_inventory_available": False,
            "route_inventory_count": 0,
            "default_classified_route_count": 0,
            "default_mutation_route_count": 0,
            "default_mutation_routes": [],
            "coverage_status": "NO_ROUTE_INVENTORY",
        }

    default_routes: list[dict[str, Any]] = []
    default_mutations: list[dict[str, Any]] = []
    for item in inventory:
        path = str(item.get("path") or "")
        for method in _methods(item.get("methods")):
            if method == "OPTIONS":
                continue
            rule = classify_route(method, path)
            if not rule.default_rule:
                continue
            row = {
                "method": method,
                "path": path,
                "permission": rule.permission,
                "category": rule.category,
            }
            default_routes.append(row)
            if method not in {"GET", "HEAD"}:
                default_mutations.append(row)
    return {
        "route_inventory_available": True,
        "route_inventory_count": sum(len(_methods(item.get("methods"))) for item in inventory),
        "default_classified_route_count": len(default_routes),
        "default_mutation_route_count": len(default_mutations),
        "default_mutation_routes": default_mutations,
        "coverage_status": "OK" if not default_mutations else "DEFAULT_MUTATIONS_PRESENT",
    }


def _iter_route_inventory(route_inventory: Iterable[Mapping[str, Any]] | None) -> Iterable[Mapping[str, Any]]:
    if route_inventory is not None:
        yield from route_inventory
        return
    if _ROUTE_INVENTORY_PROVIDER is None:
        return
    try:
        yield from _ROUTE_INVENTORY_PROVIDER()
    except Exception:
        return


def _methods(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.upper()]
    try:
        return sorted({str(method).upper() for method in value or [] if str(method).strip()})
    except TypeError:
        return []


def _is_public_web_shell_request(method: str, path: str) -> bool:
    return method in {"GET", "HEAD"} and not str(path or "").startswith("/api/")


__all__ = [
    "CLAIM_BOUNDARY",
    "PERMISSION_DEFINITIONS",
    "REPORT_KIND",
    "ROLE_DEFINITIONS",
    "RoutePermissionRule",
    "build_route_permission_policy_report",
    "classify_route",
    "evaluate_route_permission",
    "resolve_http_role",
    "set_route_inventory_provider",
]
