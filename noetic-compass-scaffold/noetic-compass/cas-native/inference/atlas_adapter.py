"""Thin Idea Atlas adapter — POST predict_cas output to the shipped /idea_atlas API.

The shipped Idea Atlas (api/routes/idea_atlas.py + dashboard/src/components/IdeaAtlas/)
is the production surface. This adapter is the Python-side bridge that takes a
predict_cas output and registers it as an Idea in that live system.

When the API server is reachable: POST to /idea_atlas/ideas (real persistence,
real similarity-edge computation, real dashboard render).

When the API server is NOT reachable (local dev without the API up): fall back to
a local JSONL log at ~/.cas-native/atlas_local.jsonl so the user can inspect
what would have been posted, and replay it when the API comes up.

Auth: the live route requires JWT. We read NC_DEV_JWT from env if set; otherwise
the adapter operates in local-only mode and prints a clear message.

This adapter is the user-visible "/atlas" REPL surface. It does NOT maintain a
parallel atlas data model — the cas-native/atlas/ scaffold is reused only for
its conversion utilities; persistence + edge computation belong to the live API.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


# Default API base. Overridable via NC_ATLAS_API_BASE env var.
DEFAULT_API_BASE = "http://127.0.0.1:8000"

# Local fallback log when API is unreachable.
LOCAL_FALLBACK_PATH = Path.home() / ".cas-native" / "atlas_local.jsonl"


@dataclass
class AtlasPostResult:
    posted_to_api: bool
    idea_id: str | None
    cas_expression: str | None
    dashboard_url: str | None
    fallback_path: Path | None
    error: str | None


def _resolve_api_base() -> str:
    return os.environ.get("NC_ATLAS_API_BASE", DEFAULT_API_BASE).rstrip("/")


def _resolve_jwt() -> str | None:
    token = os.environ.get("NC_DEV_JWT") or os.environ.get("NC_API_JWT")
    return token.strip() if token else None


def _build_cas_expression_from_prediction(prediction: dict[str, Any]) -> str:
    """Build a CAS expression string from a 12-key prediction dict.

    Best-effort. The prediction has keys like noetic, domain, drive, register,
    plus structural flags. Compose into the canonical `^n^D_{Fk}|R` form.
    """
    noetic = prediction.get("noetic", "^0")
    domain = prediction.get("domain", "C")
    drive = prediction.get("drive", "F1")
    register = prediction.get("register")

    if not noetic.startswith("^"):
        noetic = f"^{noetic}"

    expr = f"{noetic}^{domain}_{{{drive}}}"
    if register and register != "neutral":
        expr += f"|{register}"
    return expr


def _save_local_fallback(payload: dict[str, Any]) -> Path:
    LOCAL_FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        **payload,
        "logged_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    with LOCAL_FALLBACK_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return LOCAL_FALLBACK_PATH


def post_prediction(prompt: str, prediction: dict[str, Any]) -> AtlasPostResult:
    """Send a predict_cas output to the live Idea Atlas, or fall back locally.

    prompt: the user's original text input.
    prediction: the 12-key dict from predict_cas.predict.

    Returns AtlasPostResult describing what happened.
    """
    cas_expression = _build_cas_expression_from_prediction(prediction)
    payload = {
        "text": prompt,
        "cas_expression": cas_expression,
    }

    api_base = _resolve_api_base()
    jwt = _resolve_jwt()

    if not HAS_HTTPX:
        path = _save_local_fallback({"prompt": prompt, "prediction": prediction, "reason": "httpx not installed"})
        return AtlasPostResult(
            posted_to_api=False,
            idea_id=None,
            cas_expression=cas_expression,
            dashboard_url=None,
            fallback_path=path,
            error="httpx not installed; logged to local fallback",
        )

    if not jwt:
        path = _save_local_fallback({"prompt": prompt, "prediction": prediction, "reason": "no JWT (set NC_DEV_JWT)"})
        return AtlasPostResult(
            posted_to_api=False,
            idea_id=None,
            cas_expression=cas_expression,
            dashboard_url=None,
            fallback_path=path,
            error="no JWT in env (set NC_DEV_JWT or NC_API_JWT); logged to local fallback",
        )

    try:
        with httpx.Client(base_url=api_base, timeout=5.0) as client:
            resp = client.post(
                "/idea_atlas/ideas",
                json=payload,
                headers={"Authorization": f"Bearer {jwt}"},
            )
        if resp.status_code in (200, 201):
            data = resp.json()
            idea_id = data.get("id")
            return AtlasPostResult(
                posted_to_api=True,
                idea_id=idea_id,
                cas_expression=cas_expression,
                dashboard_url=f"{api_base}/dashboard/atlas?focus={idea_id}",
                fallback_path=None,
                error=None,
            )
        path = _save_local_fallback({
            "prompt": prompt,
            "prediction": prediction,
            "reason": f"HTTP {resp.status_code}",
            "response_body": resp.text[:500],
        })
        return AtlasPostResult(
            posted_to_api=False,
            idea_id=None,
            cas_expression=cas_expression,
            dashboard_url=None,
            fallback_path=path,
            error=f"API returned HTTP {resp.status_code}; logged to local fallback",
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        path = _save_local_fallback({
            "prompt": prompt,
            "prediction": prediction,
            "reason": f"connection error: {exc.__class__.__name__}",
        })
        return AtlasPostResult(
            posted_to_api=False,
            idea_id=None,
            cas_expression=cas_expression,
            dashboard_url=None,
            fallback_path=path,
            error=f"API unreachable at {api_base} ({exc.__class__.__name__}); logged to local fallback",
        )


def list_local_fallback() -> list[dict[str, Any]]:
    """Read all locally-buffered atlas posts (when API was unreachable)."""
    if not LOCAL_FALLBACK_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    with LOCAL_FALLBACK_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def replay_local_fallback() -> list[AtlasPostResult]:
    """Try to POST every locally-buffered record to the API.

    On success, the local fallback file is rewritten to contain only
    still-failing records. Returns one AtlasPostResult per attempted record.
    """
    if not LOCAL_FALLBACK_PATH.exists():
        return []
    pending = list_local_fallback()
    results: list[AtlasPostResult] = []
    still_pending: list[dict[str, Any]] = []
    for rec in pending:
        prompt = rec.get("prompt", "")
        prediction = rec.get("prediction", {})
        if not prompt or not prediction:
            still_pending.append(rec)
            continue
        result = post_prediction(prompt, prediction)
        results.append(result)
        if not result.posted_to_api:
            still_pending.append(rec)
    LOCAL_FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_FALLBACK_PATH.open("w", encoding="utf-8") as fh:
        for rec in still_pending:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return results
