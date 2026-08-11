"""No-side-effect capability proof for the tiered DeepSeek V4 routes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "runtime" / "redteam-deepseek-v4-role-routing-latest.json"


def _cloud_model(model: str) -> str:
    token = str(model or "").strip()
    return token if token.endswith(":cloud") else f"{token}:cloud"


def _generate_once(
    base_url: str,
    *,
    model: str,
    expected: str,
    timeout: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(
            {
                "model": model,
                "prompt": f"Return only the exact ASCII token {expected}",
                "stream": False,
                # Match the application adapter. Hidden reasoning can otherwise
                # consume the tiny output budget and leave a truncated marker.
                "think": False,
                "keep_alive": "30m",
                "options": {"temperature": 0, "num_predict": 96},
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        body = json.loads(response.read().decode("utf-8"))
    text = str(body.get("response") or "").strip()
    return {
        "http_status": int(response.status),
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "model_ref": str(body.get("model") or model),
        "response": text,
        "expected": expected,
        "matched": text == expected,
        "done": bool(body.get("done")),
        "done_reason": body.get("done_reason"),
    }


def _generate(
    base_url: str,
    *,
    model: str,
    expected: str,
    timeout: float,
) -> dict[str, Any]:
    """Require an exact marker while tolerating one transient formatting miss."""

    attempts: list[dict[str, Any]] = []
    for _ in range(3):
        result = _generate_once(
            base_url,
            model=model,
            expected=expected,
            timeout=timeout,
        )
        attempts.append(result)
        if result.get("matched"):
            break
    selected = dict(attempts[-1])
    selected["attempt_count"] = len(attempts)
    selected["attempts"] = attempts
    return selected


def build_report(
    *,
    base_url: str,
    flash_model: str,
    pro_model: str,
    timeout: float,
) -> dict[str, Any]:
    flash_ref = _cloud_model(flash_model)
    pro_ref = _cloud_model(pro_model)
    probes: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for role, model, expected in (
        ("fast", flash_ref, "CAS_FLASH_READY"),
        ("pro", pro_ref, "CAS_PRO_READY"),
    ):
        try:
            probes[role] = _generate(
                base_url,
                model=model,
                expected=expected,
                timeout=timeout,
            )
        except Exception as exc:  # exact transport failure is evidence.
            errors[role] = f"{type(exc).__name__}: {exc}"

    checks = {
        "flash_generation_succeeded": bool(
            probes.get("fast", {}).get("http_status") == 200
            and probes.get("fast", {}).get("done")
            and probes.get("fast", {}).get("matched")
        ),
        "pro_generation_succeeded": bool(
            probes.get("pro", {}).get("http_status") == 200
            and probes.get("pro", {}).get("done")
            and probes.get("pro", {}).get("matched")
        ),
        "role_models_are_distinct": flash_ref != pro_ref,
        "flash_role_model_is_exact": flash_ref == "deepseek-v4-flash:cloud",
        "pro_role_model_is_exact": pro_ref == "deepseek-v4-pro:cloud",
    }
    passed = all(checks.values()) and not errors
    report: dict[str, Any] = {
        "report_kind": "cas_forex_redteam_deepseek_v4_role_routing",
        "status": "PASS_DEEPSEEK_V4_ROLE_CAPABILITY" if passed else "FAIL_DEEPSEEK_V4_ROLE_CAPABILITY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "transport": "ollama_cloud",
        "base_url": base_url,
        "role_routes": {
            "fast": {"request_class": "continuous", "model_ref": flash_ref},
            "pro": {"request_class": "high_consequence", "model_ref": pro_ref},
        },
        "probes": probes,
        "errors": errors,
        "invariant_checks": checks,
        "broker_touched": False,
        "orders_placed": False,
        "money_moved": False,
        "settings_changed": False,
        "claim_boundary": (
            "This proves request-time text generation for the two exact Ollama Cloud "
            "model references. It issued no broker order, moved no money, changed no "
            "dial, and does not prove trading profitability or live-money readiness."
        ),
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    report["event_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--flash-model", default="deepseek-v4-flash")
    parser.add_argument("--pro-model", default="deepseek-v4-pro")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(
        base_url=args.base_url,
        flash_model=args.flash_model,
        pro_model=args.pro_model,
        timeout=args.timeout,
    )
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS_DEEPSEEK_V4_ROLE_CAPABILITY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
