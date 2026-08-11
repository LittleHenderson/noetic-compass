"""No-side-effect failover and structured-output proof for Gemma 4 31B Cloud."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.config import config as default_config
from cas_forex.model_provider import ModelProvider, build_provider_chain


DEFAULT_OUTPUT = REPO_ROOT / "runtime" / "redteam-gemma4-backup-latest.json"
EXPECTED_STATUS = "CAS_GEMMA4_BACKUP_READY"
EXPECTED_ACTION = "STAND_DOWN"
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": [EXPECTED_STATUS]},
        "action": {"type": "string", "enum": [EXPECTED_ACTION]},
        "orders": {"type": "array", "maxItems": 0},
    },
    "required": ["status", "action", "orders"],
    "additionalProperties": False,
}


def _cloud_model(model: str) -> str:
    token = str(model or "").strip()
    if token.endswith(":cloud") or token.endswith("-cloud"):
        return token
    if ":" in token:
        family, tag = token.rsplit(":", 1)
        return f"{family}:{tag}-cloud"
    return f"{token}:cloud"


def _probe_once(
    provider: ModelProvider,
    *,
    timeout: float,
) -> dict[str, Any]:
    result = provider.generate(
        (
            "This is a text-only capability probe. Return the schema exactly with "
            f"status={EXPECTED_STATUS}, action={EXPECTED_ACTION}, and orders=[]. "
            "Do not propose, place, modify, or close a trade."
        ),
        (
            "You are the CAS Forex backup reasoning model capability probe. "
            "Return only the requested JSON object."
        ),
        request_kind="backup_capability_probe",
        model_role="fast",
        request_timeout=timeout,
        max_attempts=2,
        max_output_tokens=128,
        response_format=RESPONSE_SCHEMA,
    )
    raw_text = str(result.get("text") or "").strip()
    parsed: dict[str, Any] | None = None
    parse_error: str | None = None
    try:
        candidate = json.loads(raw_text)
        if isinstance(candidate, dict):
            parsed = candidate
        else:
            parse_error = "response JSON is not an object"
    except json.JSONDecodeError as exc:
        parse_error = f"JSONDecodeError: {exc}"
    return {
        "ok": bool(result.get("ok")),
        "provider": result.get("provider"),
        "provider_label": result.get("provider_label"),
        "model_ref": result.get("model_ref"),
        "model_backend": result.get("model_backend"),
        "model_role": result.get("model_role"),
        "requested_model_role": result.get("requested_model_role"),
        "failover": bool(result.get("failover")),
        "switch_reason": result.get("switch_reason"),
        "provider_attempts": result.get("attempts") or [],
        "response": raw_text,
        "parsed_response": parsed,
        "parse_error": parse_error,
        "error": result.get("error"),
    }


def _probe(
    provider: ModelProvider,
    *,
    timeout: float,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for _ in range(3):
        attempt = _probe_once(provider, timeout=timeout)
        attempts.append(attempt)
        parsed = attempt.get("parsed_response")
        if (
            attempt.get("ok")
            and attempt.get("provider") == "gemma4-backup"
            and isinstance(parsed, dict)
            and parsed.get("status") == EXPECTED_STATUS
            and parsed.get("action") == EXPECTED_ACTION
            and parsed.get("orders") == []
        ):
            break
    selected = dict(attempts[-1])
    selected["attempt_count"] = len(attempts)
    selected["attempts"] = attempts
    return selected


def build_report(
    *,
    base_url: str,
    model: str,
    timeout: float,
    base_config: Any = default_config,
) -> dict[str, Any]:
    model_ref = _cloud_model(model)
    runtime_config = replace(
        base_config,
        ai_operator_gemma_backup_enabled=True,
        ai_operator_gemma_backup_transport="ollama_cloud",
        ai_operator_gemma_backup_model=model_ref,
        ai_operator_gemma_backup_ollama_base_url=base_url,
    )
    fast_chain = build_provider_chain(runtime_config, model_role="fast")
    pro_chain = build_provider_chain(runtime_config, model_role="pro")
    fast_names = [row.name for row in fast_chain]
    pro_names = [row.name for row in pro_chain]

    # The first rung intentionally points at a closed localhost port. That
    # creates a bounded, no-network-side-effect DeepSeek transport failure and
    # exercises the real ModelProvider failover into the live Gemma cloud rail.
    probe_config = replace(
        runtime_config,
        ai_operator_deepseek_enabled=True,
        ai_operator_deepseek_transport="direct",
        ai_operator_deepseek_api_key="capability-probe-placeholder",
        ai_operator_deepseek_base_url="http://127.0.0.1:1",
        ai_operator_primary_api_key=None,
        ai_model_backend="",
    )
    with TemporaryDirectory(prefix="cas-gemma4-proof-") as temp_dir:
        temp = Path(temp_dir)
        provider = ModelProvider(
            probe_config,
            state_path=temp / "model-provider-state.json",
            events_path=temp / "model-provider-events.jsonl",
        )
        probe = _probe(provider, timeout=timeout)

    parsed = probe.get("parsed_response")
    provider_attempts = probe.get("provider_attempts")
    first_attempt = (
        provider_attempts[0]
        if isinstance(provider_attempts, list) and provider_attempts
        else {}
    )
    checks = {
        "fast_chain_places_gemma_after_flash": (
            len(fast_names) >= 2
            and fast_names[0] == "deepseek-flash"
            and fast_names[1] == "gemma4-backup"
        ),
        "pro_chain_places_gemma_after_pro_and_flash": (
            len(pro_names) >= 3
            and pro_names[:3]
            == ["deepseek-pro", "deepseek-flash", "gemma4-backup"]
        ),
        "gemma_model_ref_is_exact": model_ref == "gemma4:31b-cloud",
        "deepseek_failure_was_exercised": (
            isinstance(first_attempt, dict)
            and first_attempt.get("provider") == "deepseek-flash"
            and first_attempt.get("ok") is False
        ),
        "gemma_application_generation_succeeded": bool(
            probe.get("ok") and probe.get("provider") == "gemma4-backup"
        ),
        "automatic_failover_recorded": bool(probe.get("failover")),
        "structured_response_is_exact": bool(
            isinstance(parsed, dict)
            and parsed.get("status") == EXPECTED_STATUS
            and parsed.get("action") == EXPECTED_ACTION
            and parsed.get("orders") == []
            and set(parsed) == {"status", "action", "orders"}
        ),
        "backup_role_is_reported": probe.get("model_role") == "backup",
        "requested_fast_role_is_preserved": (
            probe.get("requested_model_role") == "fast"
        ),
    }
    passed = all(checks.values())
    report: dict[str, Any] = {
        "report_kind": "cas_forex_redteam_gemma4_backup",
        "status": (
            "PASS_GEMMA4_BACKUP_CAPABILITY"
            if passed
            else "FAIL_GEMMA4_BACKUP_CAPABILITY"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "transport": "ollama_cloud",
        "base_url": base_url,
        "model_ref": model_ref,
        "configured_chains": {
            "fast": fast_names,
            "pro": pro_names,
        },
        "probe": probe,
        "invariant_checks": checks,
        "broker_touched": False,
        "orders_placed": False,
        "money_moved": False,
        "settings_changed": False,
        "claim_boundary": (
            "This proves that a bounded failure at the first model rung reaches "
            "Gemma 4 31B Cloud through the real CAS ModelProvider path and that "
            "Gemma returns the required no-order JSON schema. It issued no broker "
            "order, moved no money, changed no dial, and does not prove trading "
            "profitability or live-money readiness."
        ),
    }
    canonical = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    report["event_hash"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="gemma4:31b-cloud")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(
        base_url=args.base_url,
        model=args.model,
        timeout=args.timeout,
    )
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS_GEMMA4_BACKUP_CAPABILITY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
