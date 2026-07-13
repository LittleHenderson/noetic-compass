from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.config import Settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _env_value(path: Path, key: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"(?m)^\s*- key: {re.escape(key)}\s*\r?\n\s+value:\s*([^#\r\n]+)",
        text,
    )
    assert match is not None, f"{key} missing from {path.name}"
    return match.group(1).strip().strip('"\'')


def test_private_canary_enables_only_bounded_quota_gate() -> None:
    canary = REPOSITORY_ROOT / "render.canary.yaml"
    production = REPOSITORY_ROOT / "render.yaml"

    assert _env_value(canary, "NC_DEPLOYMENT_PROFILE") == "accounts-canary"
    assert _env_value(canary, "NC_ACCOUNTS_ENABLED") == "true"
    assert _env_value(canary, "NC_QUOTAS_ENABLED") == "true"
    assert _env_value(canary, "NC_QUOTA_MONTHLY_AUDIT_LIMIT") == "2"
    assert _env_value(canary, "NC_BILLING_ENTITLEMENTS_ENABLED") == "false"
    assert _env_value(canary, "NC_BILLING_PROVIDER") == "null"
    assert _env_value(canary, "NC_FLEET_SERVICE_AUTH_ENABLED") == "false"

    canary_text = canary.read_text(encoding="utf-8")
    assert "- type: pserv" in canary_text
    assert "autoDeployTrigger: checksPass" in canary_text

    # The public Blueprint is a separate file and must remain dark.
    assert _env_value(production, "NC_ACCOUNTS_ENABLED") == "false"
    assert _env_value(production, "NC_QUOTAS_ENABLED") == "false"
    assert _env_value(production, "NC_BILLING_ENTITLEMENTS_ENABLED") == "false"
    assert _env_value(production, "NC_BILLING_PROVIDER") == "null"


def test_bounded_quota_limit_accepts_env_alias_and_range() -> None:
    configured = Settings(NC_QUOTA_MONTHLY_AUDIT_LIMIT="2")
    assert configured.quota_monthly_audit_limit == 2
    assert Settings().quota_monthly_audit_limit is None

    with pytest.raises(ValidationError):
        Settings(NC_QUOTA_MONTHLY_AUDIT_LIMIT="0")
    with pytest.raises(ValidationError):
        Settings(NC_QUOTA_MONTHLY_AUDIT_LIMIT="10001")
