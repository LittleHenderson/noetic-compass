"""Bind an agent transcription of live user permission to one validated Q4 plan.

This verifies recorded bytes and scope, not a person's identity. The calling
agent must have received the actual instruction in its live conversation.
It must not infer permission from an arbitrary local file. No key or signature
is created or claimed here; the separate signed-authorization contract remains.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from q3_load import strict_loads
from q4_checkpoint import canonical, digest


SCHEMA = "helm-cas-expression-lab.q4-conversation-authorization/0.1"
MODE = "EXPLICIT_USER_CONVERSATION"
IDENTITY_VERIFICATION = "LIVE_CONVERSATION_NOT_CRYPTOGRAPHIC"
USER_AUTHORIZATION_QUOTE = (
    "I HEREBY GIVE YOU COMPLETE AND TOTAL AUTHORIZATION FOR THIS AND ANY FUTURE RUNS "
    "REGARDING THIS PROJECT OR ANY OF OUR RESEARCH AND DEVELOPMENT CONCERN AI, LLMS."
)
MAX_RECORD_BYTES = 32768


class ConversationAuthorizationError(ValueError):
    """The recorded conversation permission cannot be used for this plan."""


def _require(condition, reason):
    if not condition:
        raise ConversationAuthorizationError("CONVERSATION_AUTHORIZATION_INVALID: " + reason)


def verify_conversation_authorization(plan, path, expected_sha256) -> dict:
    """Check one transcript record against its caller-pinned digest and plan.

The supervisor and worker must each call validate_plan before this function.
The digest is an integrity anchor supplied by the live caller, not proof that
the record was independently signed by the user. There is no invented expiry.
"""
    _require(type(expected_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None,
             "expected raw record SHA-256 required")
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_RECORD_BYTES + 1)
    except (OSError, TypeError, ValueError) as error:
        raise ConversationAuthorizationError("CONVERSATION_AUTHORIZATION_UNAVAILABLE") from error
    _require(len(raw) <= MAX_RECORD_BYTES, "record exceeds byte limit")
    _require(digest(raw) == expected_sha256, "record SHA-256 mismatch")
    try:
        record = strict_loads(raw, "conversation authorization")
    except ValueError as error:
        raise ConversationAuthorizationError("CONVERSATION_AUTHORIZATION_INVALID: malformed JSON") from error
    _require(type(record) is dict and set(record) == {"schema", "plan_sha256", "provenance", "execution_scope"},
             "record fields")
    _require(record["schema"] == SCHEMA, "schema")
    _require(type(plan) is dict, "plan must be an object")
    try:
        plan_sha256 = digest(canonical(plan))
    except (TypeError, ValueError, UnicodeError) as error:
        raise ConversationAuthorizationError("CONVERSATION_AUTHORIZATION_INVALID: noncanonical plan") from error
    _require(record["plan_sha256"] == plan_sha256, "plan SHA-256 mismatch")

    provenance = record["provenance"]
    _require(type(provenance) is dict and set(provenance) == {
        "source_role", "source", "source_reference", "recorded_by", "captured_at_utc",
        "user_quote", "user_quote_sha256"}, "provenance fields")
    _require(provenance["source_role"] == "user" and provenance["source"] == "CURRENT_CODEX_CONVERSATION"
             and provenance["recorded_by"] == "CODEX_AGENT_TRANSCRIPTION", "live user transcription required")
    _require(type(provenance["source_reference"]) is str
             and 0 < len(provenance["source_reference"].strip()) <= 2048, "source reference required")
    _require(provenance["user_quote"] == USER_AUTHORIZATION_QUOTE, "user quote differs from live instruction")
    quote_sha256 = digest(USER_AUTHORIZATION_QUOTE.encode("utf-8"))
    _require(provenance["user_quote_sha256"] == quote_sha256, "user quote SHA-256 mismatch")
    try:
        captured = datetime.fromisoformat(provenance["captured_at_utc"].replace("Z", "+00:00"))
        _require(captured.tzinfo is not None and captured.utcoffset() is not None
                 and captured <= datetime.now(timezone.utc), "capture timestamp must be aware and nonfuture")
    except (AttributeError, TypeError, ValueError) as error:
        raise ConversationAuthorizationError("CONVERSATION_AUTHORIZATION_INVALID: capture timestamp") from error

    scope = record["execution_scope"]
    _require(type(scope) is dict and set(scope) == {"task", "device", "max_updates", "max_wall_seconds", "no_retries"},
             "execution scope fields")
    _require(scope["task"] == plan.get("task") == "T14_R1_G_ENGINEERING_SMOKE", "task scope")
    _require(type(scope["device"]) is str and scope["device"] == plan.get("device")
             and re.fullmatch(r"cuda:[0-9]+", scope["device"]) is not None, "CUDA device scope")
    for key, limit in (("max_updates", 128), ("max_wall_seconds", 1800)):
        _require(type(scope[key]) is int and type(plan.get(key)) is int
                 and 1 <= scope[key] <= limit and scope[key] == plan[key], key + " scope")
    _require(scope["no_retries"] is True and plan.get("resume") is False, "no retries or resume")
    return {"mode": MODE, "record_sha256": expected_sha256, "plan_sha256": plan_sha256,
            "user_quote_sha256": quote_sha256, "identity_verification": IDENTITY_VERIFICATION}
