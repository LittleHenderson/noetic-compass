"""Read-only no-bypass launch gate for CAS Forex.

This module does not execute tests. It statically reports whether the repo has
the source files and regression coverage that prove sensitive actions cannot
bypass the protected dispatch, risk, live, owner, and money-movement gates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_bypass_launch_gate"

CLAIM_BOUNDARY = (
    "Bypass launch gate is a read-only static evidence report. It does not run "
    "pytest, place orders, close positions, move money, change settings, expose "
    "secrets, authorize live trading, or prove broker profitability."
)


_CHECKS: tuple[dict[str, Any], ...] = (
    {
        "check_id": "route_permission_sensitive_routes",
        "invariant": "Off-box or unpaired browser requests cannot mutate owner authority, submit orders, or move money.",
        "enforcement": "api.server owner-auth middleware plus cas_forex.route_permissions policy",
        "evidence": (
            "cas_forex/route_permissions.py",
            "api/server.py",
            "tests/test_route_permissions.py",
        ),
        "required_terms": {
            "tests/test_route_permissions.py": (
                "test_unpaired_offbox_browser_cannot_mutate_owner_or_order_routes",
                "test_preview_proxy_uses_forwarded_phone_role_for_permission_checks",
                "submit_order",
                "move_money",
            ),
            "api/server.py": ("evaluate_route_permission",),
        },
    },
    {
        "check_id": "single_order_dispatch_chokepoint",
        "invariant": "Broker-bound order attempts flow through order_dispatch and execution_guard before a bridge can be touched.",
        "enforcement": "cas_forex.order_dispatch dispatch_intent(s) calls execution_guard.guarded_place_order",
        "evidence": (
            "cas_forex/order_dispatch.py",
            "cas_forex/execution_guard.py",
            "tests/test_order_dispatch.py",
            "tests/test_execution_guard.py",
        ),
        "required_terms": {
            "cas_forex/order_dispatch.py": ("guarded_place_order", "execution_guard"),
            "cas_forex/execution_guard.py": ("def guarded_place_order", "bridge.execute_order"),
            "tests/test_order_dispatch.py": ("dispatched_to_bridge",),
            "tests/test_execution_guard.py": ("test_guarded_place_order_blocks_and_does_not_touch_bridge",),
        },
    },
    {
        "check_id": "edge_pass_fresh_one_use_bound",
        "invariant": "PASS tokens are fresh, matching, and consumed once before broker dispatch.",
        "enforcement": "cas_forex.edge_authorization at the execution_guard chokepoint",
        "evidence": (
            "cas_forex/edge_authorization.py",
            "cas_forex/execution_guard.py",
            "tests/test_edge_authorization.py",
        ),
        "required_terms": {
            "cas_forex/edge_authorization.py": ("_CONSUMED", "already consumed", "geometry"),
            "tests/test_edge_authorization.py": (
                "test_require_refuses_stale_token",
                "test_require_refuses_geometry_divergence",
                "test_chokepoint_consumes_authorized_pass",
            ),
        },
    },
    {
        "check_id": "fresh_broker_truth_before_real_dispatch",
        "invariant": "A real broker bridge cannot be touched without fresh broker-truth readiness and explicit live risk telemetry.",
        "enforcement": "execution_guard action-time broker-truth and live-risk snapshot gates",
        "evidence": (
            "cas_forex/execution_guard.py",
            "cas_forex/broker_truth_monitor.py",
            "tests/test_execution_guard.py",
        ),
        "required_terms": {
            "cas_forex/execution_guard.py": (
                "_require_fresh_broker_truth_for_real_dispatch",
                "_require_real_risk_snapshot",
            ),
            "tests/test_execution_guard.py": (
                "test_guarded_place_order_real_dispatch_requires_fresh_broker_truth",
                "test_guarded_place_order_real_dispatch_requires_live_risk_snapshot",
            ),
        },
    },
    {
        "check_id": "manual_live_order_typed_confirmation",
        "invariant": "A boolean confirm flag alone cannot start a live manual order; the owner must type the live-order phrase.",
        "enforcement": "api.routes.order_dispatch manual-order route confirmation phrase",
        "evidence": (
            "api/routes/order_dispatch.py",
            "tests/test_order_dispatch_route.py",
            "ui/src/components/TradingWindow.tsx",
        ),
        "required_terms": {
            "api/routes/order_dispatch.py": ("LIVE_ORDER_CONFIRM_PHRASE", "confirm_phrase"),
            "tests/test_order_dispatch_route.py": ("test_manual_order_live_authorized_requires_typed_confirmation",),
            "ui/src/components/TradingWindow.tsx": ("journal_reason",),
        },
    },
    {
        "check_id": "manual_order_anti_impulse_before_quote",
        "invariant": "Manual orders require an anti-impulse journal before quote lookup or dispatch.",
        "enforcement": "api.routes.order_dispatch blocks missing journal before market-data lookup",
        "evidence": (
            "api/routes/order_dispatch.py",
            "ui/src/components/TradingWindow.tsx",
            "tests/test_order_dispatch_route.py",
        ),
        "required_terms": {
            "tests/test_order_dispatch_route.py": (
                "test_manual_order_requires_anti_impulse_journal_before_quote_or_dispatch",
                "quote lookup should not run without journal",
            ),
            "ui/src/components/TradingWindow.tsx": ("not revenge/FOMO trading",),
        },
    },
    {
        "check_id": "money_movement_requires_owner_gates",
        "invariant": "Payout or withdrawal execution requires owner-gated provider setup, destination allowlist, transfer caps, master kill clear, and receipt/ledger evidence.",
        "enforcement": "runtime payout gate plus money-movement engine hard blocks and verified-profit sweep recovery",
        "evidence": (
            "cas_forex/runtime_gates.py",
            "cas_forex/verified_profit_sweep.py",
            "cas_forex/money_movement.py",
            "tests/test_payment_providers.py",
            "tests/test_verified_profit_sweep.py",
        ),
        "required_terms": {
            "cas_forex/runtime_gates.py": ("outflow destination allowlisted", "payment provider configured"),
            "cas_forex/money_movement.py": (
                "_money_movement_kill_switch_active",
                "master kill switch",
                "provider_touched",
                "event_hash",
                "ledger_entry",
                "before_after_balance_snapshot",
            ),
            "tests/test_payment_providers.py": (
                "test_master_kill_blocks_real_provider_before_call",
                "test_authorized_outflow_rejects_unallowlisted_destination_before_provider_call",
                "test_authorized_outflow_rejects_amount_cap_before_provider_call",
                "test_authorized_real_payout_produces_real_money_ledger_event",
            ),
            "tests/test_verified_profit_sweep.py": (
                "test_confirmed_sweep_still_blocks_when_payout_gate_not_authorized",
                "test_confirmed_authorized_sweep_is_idempotent",
            ),
        },
    },
    {
        "check_id": "snapshot_routes_read_only",
        "invariant": "Snapshot and mirror routes do not import or call broker order-send functions.",
        "enforcement": "MT5/account/movement routes remain observational; dispatch belongs to order_dispatch",
        "evidence": (
            "api/routes/mt5_live.py",
            "api/routes/movement.py",
            "cas_forex/mt5_live.py",
            "ui/src/pages/WindowsPage.tsx",
        ),
        "required_terms": {
            "api/routes/mt5_live.py": ("refresh", "account"),
            "api/routes/movement.py": ("snapshot",),
            "cas_forex/mt5_live.py": ("claim_boundary", "execution_path_note"),
            "ui/src/pages/WindowsPage.tsx": ("READ-ONLY MIRROR", "claim_boundary", "execution_path_note"),
        },
        "forbidden_terms": {
            "api/routes/mt5_live.py": ("order_send", "guarded_place_order", "dispatch_intent"),
            "api/routes/movement.py": ("order_send", "guarded_place_order", "dispatch_intent"),
        },
    },
)


def build_bypass_launch_gate_report(root: Path | str | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    checks = [_build_check(base, spec) for spec in _CHECKS]
    ok_count = sum(1 for check in checks if check["status"] == "OK")
    attention_count = len(checks) - ok_count
    return {
        "report_kind": REPORT_KIND,
        "status": "OK" if attention_count == 0 else "ATTENTION",
        "launch_gate_status": "PASS" if attention_count == 0 else "BLOCK_RELEASE",
        "check_count": len(checks),
        "ok_count": ok_count,
        "attention_count": attention_count,
        "checks": checks,
        "top_attention_items": [
            check["next_action"] for check in checks if check["status"] != "OK"
        ][:8],
        "release_policy": (
            "Treat ATTENTION as a release blocker for any real-money or public "
            "launch path until the missing evidence or forbidden route coupling "
            "is resolved."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _build_check(base: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    evidence_refs = list(spec.get("evidence", ()))
    present_refs = [ref for ref in evidence_refs if _path_exists(base, ref)]
    missing_refs = [ref for ref in evidence_refs if ref not in present_refs]

    required_terms = _missing_required_terms(base, spec.get("required_terms", {}))
    forbidden_hits = _forbidden_term_hits(base, spec.get("forbidden_terms", {}))
    status = "OK" if not missing_refs and not required_terms and not forbidden_hits else "ATTENTION"
    next_action = "Keep this no-bypass invariant regression-tested."
    if status != "OK":
        next_action = (
            "Restore missing no-bypass evidence, required test/source terms, "
            "or remove forbidden broker-execution coupling from read-only routes."
        )

    return {
        "check_id": str(spec.get("check_id", "unknown_check")),
        "status": status,
        "invariant": str(spec.get("invariant", "")),
        "enforcement": str(spec.get("enforcement", "")),
        "evidence_refs": evidence_refs,
        "present_evidence_refs": present_refs,
        "missing_evidence_refs": missing_refs,
        "missing_required_terms": required_terms,
        "forbidden_term_hits": forbidden_hits,
        "next_action": next_action,
    }


def _path_exists(base: Path, ref: str) -> bool:
    return (base / ref.split(":", 1)[0]).exists()


def _read_text(base: Path, ref: str) -> str:
    path = base / ref.split(":", 1)[0]
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _missing_required_terms(base: Path, required: Mapping[str, Iterable[str]]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for ref, terms in required.items():
        text = _read_text(base, ref)
        for term in terms:
            if str(term) not in text:
                missing.append({"path": ref, "term": str(term)})
    return missing


def _forbidden_term_hits(base: Path, forbidden: Mapping[str, Iterable[str]]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for ref, terms in forbidden.items():
        text = _read_text(base, ref)
        for term in terms:
            if str(term) in text:
                hits.append({"path": ref, "term": str(term)})
    return hits


__all__ = ["REPORT_KIND", "build_bypass_launch_gate_report"]
