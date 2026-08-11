"""Read-only security posture report for CAS Forex.

The app can run on a laptop and be reached from a phone, so the owner needs one
place that answers: what secrets exist, where are they stored, what is browser
visible, and what protects off-box API access. This report exposes only presence
and masked hints. It never returns raw tokens, passwords, or API keys.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from cas_forex.managed_secret_store import build_managed_secret_store_report
from cas_forex.route_permissions import build_route_permission_policy_report


REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIM_BOUNDARY = (
    "Security posture is a read-only diagnostic. It reports secret presence, "
    "browser exposure policy, owner-auth state, git-ignore coverage, and "
    "configuration attention items. It never returns raw broker passwords, API "
    "keys, owner tokens, payment keys, or bank/card values, and it does not "
    "authorize trading or money movement."
)


SECRET_FIELDS = (
    ("mt5_password", "MT5 password", "config/env/.env", "broker execution credential"),
    ("payment_api_key", "Payment provider API key", "runtime encrypted live-enable override or config/env/.env", "money movement provider credential"),
    ("oanda_api_key", "OANDA API key", "config/env/.env", "market data / broker API credential"),
    ("timegpt_api_key", "TimeGPT API key", "config/env/.env", "forecast provider credential"),
    ("ai_model_api_key", "AI model API key", "config/env/.env", "research model credential"),
    ("ai_operator_primary_api_key", "AI Operator primary API key", "runtime encrypted operator secret store or config/env/.env", "operator model credential"),
    ("ai_operator_deepseek_api_key", "DeepSeek Operator API key", "runtime encrypted operator secret store or config/env/.env", "Flash/Pro operator model credential"),
)

BROWSER_STORAGE_POLICY = (
    {
        "key": "cas_forex_owner_token",
        "contains_secret": True,
        "purpose": "Owner pairing token for off-box browser/phone requests.",
        "scope": "browser localStorage after owner pairing only",
    },
    {
        "key": "cas_forex_api_base",
        "contains_secret": False,
        "purpose": "API base URL for laptop/phone routing.",
        "scope": "browser localStorage",
    },
    {
        "key": "cas_forex_last_successful_api_base",
        "contains_secret": False,
        "purpose": "Sticky API base used after successful requests.",
        "scope": "browser localStorage",
    },
)


def build_security_posture_report(config: Any = None) -> dict[str, Any]:
    cfg = _resolve_config(config)
    owner_auth = _owner_auth_section()
    secrets = _secret_inventory(cfg)
    managed_store = build_managed_secret_store_report(cfg)
    ignore = _ignore_coverage()
    browser = _browser_exposure_section()
    permissions = _permission_surface(cfg)
    route_policy = build_route_permission_policy_report()
    role_model = _role_permission_model(
        owner_auth=owner_auth,
        permissions=permissions,
        route_policy=route_policy,
    )
    attention = _attention_items(
        owner_auth=owner_auth,
        secrets=secrets,
        ignore=ignore,
        permissions=permissions,
        role_model=role_model,
        managed_store=managed_store,
    )
    return {
        "report_kind": "cas_forex_security_posture",
        "status": "ATTENTION" if attention else "OK",
        "attention_items": attention,
        "owner_auth": owner_auth,
        "browser_exposure": browser,
        "managed_secret_store": managed_store,
        "server_secret_inventory": secrets,
        "ignore_coverage": ignore,
        "permission_surface": permissions,
        "role_permission_model": role_model,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config
    from cas_forex.live_enable_control import apply_live_enable_overrides

    try:
        return apply_live_enable_overrides(default_config)
    except Exception:
        return default_config


def _owner_auth_section() -> dict[str, Any]:
    from cas_forex import owner_auth

    token = owner_auth.current_token()
    auth_store = owner_auth.auth_store_status()
    auth_secret_storage = (
        auth_store.get("secret_storage")
        if isinstance(auth_store.get("secret_storage"), Mapping)
        else {}
    )
    env_token_present = bool(os.environ.get("CAS_FOREX_OWNER_TOKEN"))
    return {
        "cloud_mode": bool(owner_auth.cloud_mode()),
        "lan_mode_enabled": bool(owner_auth.lan_mode_enabled()),
        "owner_token_present": bool(token),
        "owner_token_hint": owner_auth.mask_token(token),
        "owner_token_runtime_store_encrypted_at_rest": bool(
            token and not env_token_present and auth_store.get("at_rest_encrypted")
        ),
        "owner_token_runtime_secret_storage": dict(auth_secret_storage),
        "owner_token_env_source_present": env_token_present,
        "loopback_trusted_when_not_cloud": True,
        "off_box_requires_lan_and_owner_token": not bool(owner_auth.cloud_mode()),
        "cloud_requires_owner_token_for_all_api": bool(owner_auth.cloud_mode()),
        "full_token_route_loopback_only": "/api/forex/owner-auth/pairing",
        "state_route_masks_token": "/api/forex/owner-auth/state",
        "claim_boundary": owner_auth.CLAIM_BOUNDARY,
    }


def _secret_inventory(config: Any) -> list[dict[str, Any]]:
    from cas_forex import operator_secrets
    from cas_forex.live_enable_control import build_authorization_report
    from cas_forex.push_delivery_control import build_push_delivery_backend_report

    operator_primary = operator_secrets.get_secret("primary_api_key")
    operator_deepseek = operator_secrets.get_secret("deepseek_api_key")
    operator_store = operator_secrets.store_status()
    operator_secret_storage = (
        operator_store.get("secret_storage")
        if isinstance(operator_store.get("secret_storage"), Mapping)
        else {}
    )
    owner = _owner_auth_section()
    auth_report = _safe_dict(lambda: build_authorization_report(config))
    provider = auth_report.get("provider") if isinstance(auth_report.get("provider"), Mapping) else {}
    live_secret_storage = auth_report.get("secret_storage") if isinstance(auth_report.get("secret_storage"), Mapping) else {}
    rows: list[dict[str, Any]] = []
    for attr, label, storage, purpose in SECRET_FIELDS:
        value = getattr(config, attr, None)
        configured = bool(str(value or ""))
        source = storage
        hint = _mask(value)
        runtime_override_set = False
        runtime_secret_store_set = False
        plaintext_config_source_present = False
        if attr == "payment_api_key":
            configured = bool(provider.get("payment_api_key_set")) or configured
            runtime_override_set = bool(provider.get("payment_api_key_runtime_override_set"))
            plaintext_config_source_present = bool(provider.get("payment_api_key_config_set")) or bool(str(value or ""))
            source = str(provider.get("payment_api_key_storage") or "runtime encrypted live-enable override or config/env/.env")
            hint = ""
        if attr in {
            "ai_operator_primary_api_key",
            "ai_operator_deepseek_api_key",
        }:
            runtime_value = (
                operator_primary
                if attr == "ai_operator_primary_api_key"
                else operator_deepseek
            )
            runtime_secret_store_set = bool(runtime_value)
            plaintext_config_source_present = bool(str(value or ""))
            if runtime_secret_store_set:
                configured = True
                source = "runtime encrypted operator secret store"
                hint = operator_secrets.mask(runtime_value)
            elif plaintext_config_source_present:
                source = "config/env/.env"
        rows.append(
            {
                "key": attr,
                "label": label,
                "configured": configured,
                "masked_hint": hint if configured else "",
                "storage": source,
                "runtime_secret_storage": (
                    dict(live_secret_storage)
                    if attr == "payment_api_key"
                    else dict(operator_secret_storage)
                    if attr in {
                        "ai_operator_primary_api_key",
                        "ai_operator_deepseek_api_key",
                    }
                    else {}
                ),
                "runtime_override_encrypted_at_rest": (
                    bool(runtime_override_set and live_secret_storage.get("at_rest_encrypted"))
                    if attr == "payment_api_key"
                    else False
                ),
                "runtime_override_set": runtime_override_set,
                "runtime_secret_store_set": runtime_secret_store_set,
                "runtime_secret_store_encrypted_at_rest": (
                    bool(runtime_secret_store_set and operator_store.get("at_rest_encrypted"))
                    if attr in {
                        "ai_operator_primary_api_key",
                        "ai_operator_deepseek_api_key",
                    }
                    else False
                ),
                "plaintext_config_source_present": plaintext_config_source_present,
                "browser_exposed": False,
                "plaintext_local_storage": (
                    plaintext_config_source_present
                    if attr in {
                        "payment_api_key",
                        "ai_operator_primary_api_key",
                        "ai_operator_deepseek_api_key",
                    }
                    else True
                ),
                "purpose": purpose,
            }
        )
    rows.append(
        {
            "key": "owner_token",
            "label": "Owner pairing token",
            "configured": owner["owner_token_present"],
            "masked_hint": owner["owner_token_hint"],
            "storage": "runtime encrypted owner-auth store or CAS_FOREX_OWNER_TOKEN",
            "runtime_secret_storage": owner.get("owner_token_runtime_secret_storage", {}),
            "runtime_secret_store_set": bool(owner["owner_token_present"] and not owner.get("owner_token_env_source_present")),
            "runtime_secret_store_encrypted_at_rest": bool(owner.get("owner_token_runtime_store_encrypted_at_rest")),
            "plaintext_config_source_present": bool(owner.get("owner_token_env_source_present")),
            "browser_exposed": True,
            "plaintext_local_storage": bool(owner.get("owner_token_env_source_present")),
            "purpose": "Authenticates paired phone/browser API requests.",
        }
    )
    push_backend = _safe_dict(lambda: build_push_delivery_backend_report())
    push_private_key = (
        push_backend.get("vapid_private_key")
        if isinstance(push_backend.get("vapid_private_key"), Mapping)
        else {}
    )
    push_secret_storage = (
        push_backend.get("secret_storage")
        if isinstance(push_backend.get("secret_storage"), Mapping)
        else {}
    )
    push_private_source = str(push_private_key.get("source") or "unset")
    rows.append(
        {
            "key": "web_push_vapid_private_key",
            "label": "Web Push VAPID private key",
            "configured": bool(push_private_key.get("configured")),
            "masked_hint": str(push_private_key.get("masked_value") or ""),
            "storage": "runtime encrypted push delivery override or config/env/.env",
            "runtime_secret_storage": dict(push_secret_storage),
            "runtime_override_encrypted_at_rest": bool(
                push_private_source == "runtime_override"
                and push_secret_storage.get("at_rest_encrypted")
            ),
            "runtime_override_set": push_private_source == "runtime_override",
            "runtime_secret_store_set": False,
            "runtime_secret_store_encrypted_at_rest": False,
            "plaintext_config_source_present": push_private_source == "env",
            "browser_exposed": False,
            "plaintext_local_storage": push_private_source == "env",
            "purpose": "Signs browser push notifications for off-screen delivery.",
        }
    )
    return rows


def _ignore_coverage() -> dict[str, Any]:
    gitignore = REPO_ROOT / ".gitignore"
    dockerignore = REPO_ROOT / ".dockerignore"
    git_patterns = _ignore_patterns(gitignore)
    docker_patterns = _ignore_patterns(dockerignore)
    return {
        "gitignore_present": gitignore.exists(),
        "dockerignore_present": dockerignore.exists(),
        "env_file_exists": (REPO_ROOT / ".env").exists(),
        "env_ignored_by_git": _pattern_present(git_patterns, ".env"),
        "evidence_runs_ignored_by_git": _pattern_present(git_patterns, "evidence_runs/"),
        "runtime_ignored_by_git": _pattern_present(git_patterns, "runtime/"),
        "evidence_runs_ignored_by_docker": _pattern_present(docker_patterns, "evidence_runs/"),
        "runtime_ignored_by_docker": _pattern_present(docker_patterns, "runtime/"),
        "operator_secret_store_path": "runtime/operator-secrets.json",
        "owner_auth_store_path": "runtime/owner-auth.json",
        "live_enable_override_store_path": "runtime/live-enable-overrides.json",
        "push_delivery_override_store_path": "runtime/push-delivery-overrides.json",
        "push_subscription_store_path": "evidence_runs/push_subscriptions/subscriptions.jsonl",
        "webhook_subscription_store_path": "evidence_runs/webhook_subscriptions/subscriptions.jsonl",
    }


def _browser_exposure_section() -> dict[str, Any]:
    return {
        "frontend_secret_policy": (
            "The browser stores the owner pairing token only after pairing. Broker "
            "passwords, model API keys, payment keys, and MT5 credentials stay on "
            "the API side and are reported only as presence/masked hints."
        ),
        "browser_storage_keys": list(BROWSER_STORAGE_POLICY),
        "secrets_forbidden_in_frontend": [
            "mt5_password",
            "payment_api_key",
            "oanda_api_key",
            "timegpt_api_key",
            "ai_model_api_key",
            "ai_operator_primary_api_key",
            "ai_operator_deepseek_api_key",
        ],
    }


def _permission_surface(config: Any) -> dict[str, Any]:
    return {
        "live_mode": bool(getattr(config, "live_mode", False)),
        "paper_trading": bool(getattr(config, "paper_trading", True)),
        "prefer_mt5": bool(getattr(config, "prefer_mt5", False)),
        "mt5_login_present": bool(int(getattr(config, "mt5_login", 0) or 0)),
        "mt5_password_present": bool(str(getattr(config, "mt5_password", "") or "")),
        "mt5_server_present": bool(str(getattr(config, "mt5_server", "") or "")),
        "owner_enable_live_trading": bool(getattr(config, "owner_enable_live_trading", False)),
        "live_trading_licensed": bool(getattr(config, "live_trading_licensed", False)),
        "mt5_treat_account_as_demo": bool(getattr(config, "mt5_treat_account_as_demo", False)),
        "payment_provider_present": bool(str(getattr(config, "payment_provider", "") or "")),
        "payment_api_key_present": bool(str(getattr(config, "payment_api_key", "") or "")),
        "payout_destination_present": bool(str(getattr(config, "payout_destination_id", "") or "")),
        "payout_destination_allowlisted": bool(getattr(config, "payout_destination_allowlisted", False)),
    }


def _role_permission_model(
    *,
    owner_auth: Mapping[str, Any],
    permissions: Mapping[str, Any],
    route_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Explicit single-owner permission model for the local app.

    CAS Forex is not a multi-tenant SaaS app today, but a professional trading
    surface still needs principal boundaries. This reports the boundaries that
    already exist so the owner can see what loopback, paired devices, the AI
    operator, broker bridge, and support-style diagnostics may do.
    """
    live_armed = bool(permissions.get("owner_enable_live_trading")) and bool(
        permissions.get("live_trading_licensed")
    )
    owner_token_present = bool(owner_auth.get("owner_token_present"))
    lan_or_cloud = bool(owner_auth.get("lan_mode_enabled")) or bool(owner_auth.get("cloud_mode"))
    roles = [
        {
            "role_key": "local_owner_loopback",
            "label": "Local Owner Loopback",
            "principal_type": "human_owner",
            "authentication": "PC loopback request; full pairing token route is loopback-only.",
            "can_view_dashboard": True,
            "can_pair_device": True,
            "can_rotate_owner_token": True,
            "can_change_owner_controls": True,
            "can_change_ai_dials": True,
            "can_arm_live_authority": True,
            "can_submit_live_order": live_armed,
            "can_move_money": bool(permissions.get("payment_api_key_present")),
            "can_read_raw_secrets": False,
            "can_run_broker_emergency": True,
            "requires_typed_confirmation_for_money_or_live": True,
            "enforcement": [
                "loopback-only owner-auth routes",
                "owner live-enable gates",
                "typed confirmation for live/money actions",
                "backend risk and broker gates",
            ],
        },
        {
            "role_key": "paired_owner_device",
            "label": "Paired Owner Device",
            "principal_type": "human_owner_device",
            "authentication": "LAN/cloud request with owner token.",
            "can_view_dashboard": bool(owner_token_present and lan_or_cloud),
            "can_pair_device": False,
            "can_rotate_owner_token": False,
            "can_change_owner_controls": bool(owner_token_present and lan_or_cloud),
            "can_change_ai_dials": bool(owner_token_present and lan_or_cloud),
            "can_arm_live_authority": bool(owner_token_present and lan_or_cloud),
            "can_submit_live_order": bool(owner_token_present and lan_or_cloud and live_armed),
            "can_move_money": bool(owner_token_present and lan_or_cloud and permissions.get("payment_api_key_present")),
            "can_read_raw_secrets": False,
            "can_run_broker_emergency": bool(owner_token_present and lan_or_cloud),
            "requires_typed_confirmation_for_money_or_live": True,
            "enforcement": [
                "owner token middleware for off-box requests",
                "pairing/rotate remain loopback-only",
                "typed confirmation for live/money actions",
            ],
        },
        {
            "role_key": "browser_viewer_unpaired",
            "label": "Unpaired Browser Viewer",
            "principal_type": "browser",
            "authentication": "No owner token.",
            "can_view_dashboard": not bool(owner_auth.get("cloud_mode")),
            "can_pair_device": False,
            "can_rotate_owner_token": False,
            "can_change_owner_controls": False,
            "can_change_ai_dials": False,
            "can_arm_live_authority": False,
            "can_submit_live_order": False,
            "can_move_money": False,
            "can_read_raw_secrets": False,
            "can_run_broker_emergency": False,
            "requires_typed_confirmation_for_money_or_live": True,
            "enforcement": ["owner token required off-box", "sensitive routes reject unpaired requests"],
        },
        {
            "role_key": "ai_operator_system",
            "label": "AI Operator System",
            "principal_type": "system_agent",
            "authentication": "In-process operator runner.",
            "can_view_dashboard": True,
            "can_pair_device": False,
            "can_rotate_owner_token": False,
            "can_change_owner_controls": False,
            "can_change_ai_dials": True,
            "can_arm_live_authority": False,
            "can_submit_live_order": False,
            "can_move_money": False,
            "can_read_raw_secrets": False,
            "can_run_broker_emergency": False,
            "requires_typed_confirmation_for_money_or_live": True,
            "enforcement": [
                "owner-fenced AI control surface",
                "dial bounds",
                "anti-impulse cooldown reporting",
                "no live-enable or money movement route in tool manifest",
            ],
        },
        {
            "role_key": "broker_bridge_system",
            "label": "Broker Bridge System",
            "principal_type": "system_adapter",
            "authentication": "Local MT4/MT5 terminal plus configured credentials.",
            "can_view_dashboard": False,
            "can_pair_device": False,
            "can_rotate_owner_token": False,
            "can_change_owner_controls": False,
            "can_change_ai_dials": False,
            "can_arm_live_authority": False,
            "can_submit_live_order": live_armed,
            "can_move_money": False,
            "can_read_raw_secrets": False,
            "can_run_broker_emergency": live_armed,
            "requires_typed_confirmation_for_money_or_live": True,
            "enforcement": [
                "runtime gates checked before order_send",
                "MT5 permission diagnostics",
                "broker symbol and contract validation",
                "order attempt audit and idempotency",
            ],
        },
        {
            "role_key": "support_diagnostics",
            "label": "Support Diagnostics",
            "principal_type": "read_only_support_export",
            "authentication": "No interactive support role is implemented.",
            "can_view_dashboard": False,
            "can_pair_device": False,
            "can_rotate_owner_token": False,
            "can_change_owner_controls": False,
            "can_change_ai_dials": False,
            "can_arm_live_authority": False,
            "can_submit_live_order": False,
            "can_move_money": False,
            "can_read_raw_secrets": False,
            "can_run_broker_emergency": False,
            "requires_typed_confirmation_for_money_or_live": True,
            "enforcement": ["share read-only diagnostics instead of raw credentials"],
        },
    ]
    gaps: list[str] = []
    if lan_or_cloud and not owner_token_present:
        gaps.append("Off-box access is enabled but no owner token is present.")
    if live_armed and not owner_token_present and lan_or_cloud:
        gaps.append("Live authority is armed while off-box owner-token protection is incomplete.")
    return {
        "report_kind": "cas_forex_role_permission_model",
        "status": "ATTENTION" if gaps else "OK",
        "authorization_model": "single_owner_local_app_with_owner_token_for_off_box_access",
        "mfa_status": "PARTIAL_LOCAL_CHALLENGE",
        "mfa_detail": (
            "CAS Forex uses owner admission plus route-level typed confirmation "
            "for live/money actions. Full TOTP/WebAuthn MFA is not implemented yet."
        ),
        "live_action_second_factor": {
            "status": "ENFORCED_BY_TYPED_CONFIRMATION",
            "factors": [
                "local loopback physical access or off-box owner-token pairing",
                "route-level typed confirmation for live, broker emergency, and money-impact actions",
            ],
            "not_implemented": ["TOTP", "WebAuthn/passkey challenge"],
            "claim_boundary": (
                "This is a local second-confirmation posture, not a full "
                "standards-based MFA implementation."
            ),
        },
        "mfa_hardening_backlog": [
            "Add TOTP or WebAuthn/passkey challenge before enabling live-money authority in shared or cloud deployments."
        ],
        "roles": roles,
        "route_permission_policy": dict(route_policy),
        "gaps": gaps,
        "claim_boundary": (
            "The role permission model is a read-only security map. It does not "
            "grant permissions, return raw secrets, authorize trading, or move money."
        ),
    }


def _attention_items(
    *,
    owner_auth: Mapping[str, Any],
    secrets: list[Mapping[str, Any]],
    ignore: Mapping[str, Any],
    permissions: Mapping[str, Any],
    role_model: Mapping[str, Any],
    managed_store: Mapping[str, Any],
) -> list[str]:
    items: list[str] = []
    for item in managed_store.get("attention_items") or []:
        items.append(str(item))
    if managed_store.get("status") == "ATTENTION" and not managed_store.get("attention_items"):
        items.append(str(managed_store.get("detail") or "Managed secret store needs attention."))
    if bool(owner_auth.get("lan_mode_enabled")) and not bool(owner_auth.get("owner_token_present")):
        items.append("LAN mode is enabled but no owner token is present.")
    if not bool(ignore.get("env_ignored_by_git")):
        items.append(".env is not covered by .gitignore.")
    if not bool(ignore.get("evidence_runs_ignored_by_git")):
        items.append("evidence_runs/ is not covered by .gitignore.")
    if not bool(ignore.get("runtime_ignored_by_git")):
        items.append("runtime/ is not covered by .gitignore.")
    if not bool(ignore.get("evidence_runs_ignored_by_docker")):
        items.append("evidence_runs/ is not covered by .dockerignore.")
    if not bool(ignore.get("runtime_ignored_by_docker")):
        items.append("runtime/ is not covered by .dockerignore.")
    if bool(permissions.get("owner_enable_live_trading")) and not bool(permissions.get("mt5_password_present")):
        items.append("Live-trading owner switch is enabled but MT5 password is not configured.")
    if bool(permissions.get("mt5_treat_account_as_demo")):
        items.append("MT5_TREAT_ACCOUNT_AS_DEMO is enabled; confirm the connected MT5 account is truly demo/paper.")
    for gap in role_model.get("gaps") or []:
        items.append(str(gap))
    for row in secrets:
        if row.get("configured") and row.get("browser_exposed") and row.get("key") != "owner_token":
            items.append(f"{row.get('key')} is marked browser-exposed; this should not happen.")
    return items


def _ignore_patterns(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        return {
            line.strip().replace("\\", "/")
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
    except OSError:
        return set()


def _safe_dict(builder: Any) -> dict[str, Any]:
    try:
        value = builder()
    except Exception:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            converted = to_dict()
        except Exception:
            return {}
        return dict(converted) if isinstance(converted, Mapping) else {}
    return {}


def _pattern_present(patterns: set[str], target: str) -> bool:
    normalized = target.strip().replace("\\", "/").rstrip("/") + ("/" if target.endswith("/") else "")
    variants = {normalized, normalized.rstrip("/"), f"/{normalized.rstrip('/')}", f"{normalized.rstrip('/')}/*"}
    return any(pattern.rstrip("/") in {v.rstrip("/") for v in variants} for pattern in patterns)


def _mask(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    tail = text[-4:] if len(text) >= 4 else "****"
    return f"...{tail}"


def _safe_dict(fn) -> dict[str, Any]:
    try:
        value = fn()
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}
