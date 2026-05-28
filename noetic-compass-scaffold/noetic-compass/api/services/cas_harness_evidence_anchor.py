"""External anchoring for CAS Harness Evidence Packet hash-log entries.

The local packet store is durable across process restarts, but it is still
same-host storage. This module records whether each hash-log entry was also
anchored to an external target. It never marks anchoring as successful unless
the target write succeeds.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


AnchorStatus = str


def anchor_hash_log_entry(
    *,
    trace_id: str,
    hash_log_entry: Mapping[str, Any],
    packet_path: Path,
    hash_log_path: Path,
) -> dict[str, Any]:
    """Anchor one hash-log entry according to environment configuration."""

    mode = _anchor_mode()
    manifest = _anchor_manifest(
        trace_id=trace_id,
        hash_log_entry=hash_log_entry,
        packet_path=packet_path,
        hash_log_path=hash_log_path,
    )
    if mode == "disabled":
        return {
            "status": "disabled",
            "mode": "disabled",
            "reason": "CAS_HARNESS_EVIDENCE_ANCHOR_MODE is disabled or unset.",
            "manifest_sha256": _sha256_json(manifest),
        }
    if mode == "local":
        return _anchor_local(manifest)
    if mode == "s3":
        return _anchor_s3(manifest)
    return {
        "status": "failed",
        "mode": mode,
        "reason": f"Unsupported CAS_HARNESS_EVIDENCE_ANCHOR_MODE: {mode}.",
        "manifest_sha256": _sha256_json(manifest),
    }


def verify_anchor(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the packet's external anchor, if one is declared."""

    hashes = packet.get("hashes")
    if not isinstance(hashes, Mapping):
        return _anchor_check(None, None, False, "packet hashes block is missing")
    anchor = hashes.get("external_anchor")
    if not isinstance(anchor, Mapping):
        return _anchor_check(None, None, False, "packet has no external_anchor declaration")

    status = anchor.get("status")
    if status == "disabled":
        return _anchor_check("disabled", "disabled", True, "external anchoring was explicitly disabled")
    if status == "failed":
        return _anchor_check("anchored", "failed", False, _string(anchor.get("reason")) or "anchor write failed")
    if status != "anchored":
        return _anchor_check("anchored", _string(status), False, "anchor status is not anchored")

    mode = anchor.get("mode")
    if mode == "local":
        return _verify_local_anchor(packet, anchor)
    if mode == "s3":
        return _verify_s3_anchor(packet, anchor)
    return _anchor_check("anchored", _string(mode), False, "anchor mode is not verifiable")


def _anchor_manifest(
    *,
    trace_id: str,
    hash_log_entry: Mapping[str, Any],
    packet_path: Path,
    hash_log_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "cas_harness_evidence_anchor.v1",
        "trace_id": trace_id,
        "audit_id": hash_log_entry.get("audit_id"),
        "packet_without_hashes_sha256": hash_log_entry.get("packet_without_hashes_sha256"),
        "hash_log_entry_sha256": hash_log_entry.get("entry_sha256"),
        "hash_log_previous_entry_sha256": hash_log_entry.get("previous_entry_sha256"),
        "packet_store_path": str(packet_path),
        "hash_log_path": str(hash_log_path),
        "anchored_at": datetime.now(UTC).isoformat(),
    }


def _anchor_local(manifest: Mapping[str, Any]) -> dict[str, Any]:
    target_dir = Path(
        os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_LOCAL_DIR")
        or os.environ.get("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", "")
        or "."
    )
    trace_id = _string(manifest.get("trace_id")) or "unknown"
    entry_hash = _string(manifest.get("hash_log_entry_sha256"))
    if not entry_hash:
        return {
            "status": "failed",
            "mode": "local",
            "reason": "hash_log_entry_sha256 missing from anchor manifest.",
            "manifest_sha256": _sha256_json(manifest),
        }

    path = target_dir / "anchors" / _safe(trace_id) / f"{entry_hash}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _canonical_json(manifest)
    try:
        with path.open("x", encoding="utf-8") as fh:
            fh.write(body)
    except FileExistsError:
        existing = path.read_text(encoding="utf-8")
        if existing != body:
            return {
                "status": "failed",
                "mode": "local",
                "reason": "local anchor already exists with different content.",
                "manifest_sha256": _sha256_json(manifest),
                "anchor_uri": str(path),
            }
    except OSError as exc:
        return {
            "status": "failed",
            "mode": "local",
            "reason": f"local anchor write failed: {exc}",
            "manifest_sha256": _sha256_json(manifest),
            "anchor_uri": str(path),
        }

    return {
        "status": "anchored",
        "mode": "local",
        "anchor_uri": str(path),
        "manifest_sha256": _sha256_json(manifest),
        "anchored_at": _string(manifest.get("anchored_at")),
    }


def _anchor_s3(manifest: Mapping[str, Any]) -> dict[str, Any]:
    bucket = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "").strip()
    if not bucket:
        return _s3_failed(manifest, "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET is required.")
    entry_hash = _string(manifest.get("hash_log_entry_sha256"))
    trace_id = _string(manifest.get("trace_id")) or "unknown"
    if not entry_hash:
        return _s3_failed(manifest, "hash_log_entry_sha256 missing from anchor manifest.")

    prefix = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX", "cas-harness/evidence-anchors").strip("/")
    key = f"{prefix}/{_safe(trace_id)}/{entry_hash}.json" if prefix else f"{_safe(trace_id)}/{entry_hash}.json"
    body = _canonical_json(manifest).encode("utf-8")

    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError:
        return _s3_failed(manifest, "boto3 is not installed; S3 anchoring could not run.")

    client_kwargs: dict[str, Any] = {}
    region = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION", "").strip()
    if region:
        client_kwargs["region_name"] = region

    try:
        client = boto3.client("s3", **client_kwargs)
        put_kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "Body": body,
            "ContentType": "application/json",
            "Metadata": {
                "trace-id": trace_id,
                "hash-log-entry-sha256": entry_hash,
                "packet-without-hashes-sha256": _string(manifest.get("packet_without_hashes_sha256")) or "",
            },
        }
        object_lock = _object_lock_config()
        if object_lock["error"]:
            return _s3_failed(manifest, object_lock["error"])
        object_lock_mode = object_lock["mode"]
        retention_days = object_lock["retention_days"]
        retain_until = None
        if object_lock_mode and retention_days:
            retain_until = datetime.now(UTC) + timedelta(days=retention_days)
            put_kwargs["ObjectLockMode"] = object_lock_mode
            put_kwargs["ObjectLockRetainUntilDate"] = retain_until
            put_kwargs["ContentMD5"] = base64.b64encode(hashlib.md5(body).digest()).decode("ascii")
        response = client.put_object(**put_kwargs)
    except Exception as exc:
        return _s3_failed(manifest, f"S3 anchor write failed: {type(exc).__name__}: {exc}")

    return {
        "status": "anchored",
        "mode": "s3",
        "anchor_uri": f"s3://{bucket}/{key}",
        "bucket": bucket,
        "key": key,
        "etag": _string(response.get("ETag")) if isinstance(response, Mapping) else None,
        "manifest_sha256": _sha256_json(manifest),
        "anchored_at": _string(manifest.get("anchored_at")),
        "object_lock_mode": object_lock_mode or None,
        "object_lock_retain_until": retain_until.isoformat() if retain_until else None,
        "retention_days": retention_days,
    }


def _verify_local_anchor(packet: Mapping[str, Any], anchor: Mapping[str, Any]) -> dict[str, Any]:
    uri = _string(anchor.get("anchor_uri"))
    if not uri:
        return _anchor_check("anchored", None, False, "local anchor_uri is missing")
    try:
        manifest = json.loads(Path(uri).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return _anchor_check("anchored", None, False, f"local anchor read failed: {exc}")
    if not isinstance(manifest, Mapping):
        return _anchor_check("anchored", None, False, "local anchor manifest is malformed")

    expected_manifest_hash = _string(anchor.get("manifest_sha256"))
    actual_manifest_hash = _sha256_json(manifest)
    packet_hash = _string((packet.get("hashes") or {}).get("packet_without_hashes_sha256")) if isinstance(packet.get("hashes"), Mapping) else None
    entry_hash = _string((packet.get("hashes") or {}).get("hash_log_entry_sha256")) if isinstance(packet.get("hashes"), Mapping) else None
    match = (
        expected_manifest_hash == actual_manifest_hash
        and manifest.get("packet_without_hashes_sha256") == packet_hash
        and manifest.get("hash_log_entry_sha256") == entry_hash
    )
    return _anchor_check(
        expected_manifest_hash,
        actual_manifest_hash,
        match,
        "local anchor manifest commits to this packet hash and hash-log entry",
    )


def _verify_s3_anchor(packet: Mapping[str, Any], anchor: Mapping[str, Any]) -> dict[str, Any]:
    bucket = _string(anchor.get("bucket"))
    key = _string(anchor.get("key"))
    expected_manifest_hash = _string(anchor.get("manifest_sha256"))
    if not bucket or not key or not expected_manifest_hash:
        return _anchor_check(
            expected_manifest_hash,
            None,
            False,
            "S3 anchor receipt is missing bucket, key, or manifest_sha256",
        )

    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError:
        return _anchor_check(
            expected_manifest_hash,
            None,
            False,
            "boto3 is not installed; S3 anchor object could not be re-read",
        )

    client_kwargs: dict[str, Any] = {}
    region = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION", "").strip()
    if region:
        client_kwargs["region_name"] = region

    try:
        client = boto3.client("s3", **client_kwargs)
        response = client.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read()
    except Exception as exc:
        return _anchor_check(
            expected_manifest_hash,
            None,
            False,
            f"S3 anchor object re-read failed: {type(exc).__name__}: {exc}",
        )

    actual_manifest_hash = hashlib.sha256(body).hexdigest()
    if actual_manifest_hash != expected_manifest_hash:
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            False,
            "S3 anchor object hash does not match packet manifest_sha256",
        )

    try:
        manifest = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            False,
            f"S3 anchor manifest is not valid canonical JSON: {exc}",
        )
    if not isinstance(manifest, Mapping):
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            False,
            "S3 anchor manifest is malformed",
        )

    hashes = packet.get("hashes")
    packet_hash = _string(hashes.get("packet_without_hashes_sha256")) if isinstance(hashes, Mapping) else None
    entry_hash = _string(hashes.get("hash_log_entry_sha256")) if isinstance(hashes, Mapping) else None
    manifest_match = (
        manifest.get("packet_without_hashes_sha256") == packet_hash
        and manifest.get("hash_log_entry_sha256") == entry_hash
    )
    if not manifest_match:
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            False,
            "S3 anchor object was re-read, but its manifest does not commit to this packet hash and hash-log entry",
        )

    expected_object_lock_mode = _string(anchor.get("object_lock_mode"))
    if expected_object_lock_mode:
        try:
            head = client.head_object(Bucket=bucket, Key=key)
        except Exception as exc:
            return _anchor_check(
                expected_manifest_hash,
                actual_manifest_hash,
                False,
                f"S3 anchor object was re-read, but Object Lock metadata check failed: {type(exc).__name__}: {exc}",
            )
        actual_object_lock_mode = _string(head.get("ObjectLockMode"))
        retain_until = head.get("ObjectLockRetainUntilDate")
        retain_until_text = _datetime_text(retain_until)
        if actual_object_lock_mode != expected_object_lock_mode:
            return _anchor_check(
                expected_manifest_hash,
                actual_manifest_hash,
                False,
                (
                    "S3 anchor object was re-read, but Object Lock mode did not match: "
                    f"expected {expected_object_lock_mode}, got {actual_object_lock_mode or 'none'}"
                ),
            )
        if not _retain_until_is_future(retain_until):
            return _anchor_check(
                expected_manifest_hash,
                actual_manifest_hash,
                False,
                (
                    "S3 anchor object was re-read, but Object Lock retention is missing or expired: "
                    f"{retain_until_text or 'none'}"
                ),
            )
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            True,
            (
                "S3 anchor object was re-read, its manifest commits to this packet hash and hash-log entry, "
                f"and Object Lock {expected_object_lock_mode} retention is active until {retain_until_text}"
            ),
        )

    return _anchor_check(
        expected_manifest_hash,
        actual_manifest_hash,
        True,
        "S3 anchor object was re-read and its manifest commits to this packet hash and hash-log entry; Object Lock was not requested",
    )


def _s3_failed(manifest: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "mode": "s3",
        "reason": reason,
        "manifest_sha256": _sha256_json(manifest),
    }


def _anchor_check(expected: str | None, actual: str | None, match: bool, notes: str) -> dict[str, Any]:
    return {
        "artifact": "merged_packet_external_anchor",
        "expected": expected,
        "actual": actual,
        "match": match,
        "notes": notes,
    }


def _anchor_mode() -> AnchorStatus:
    return os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "disabled").strip().lower() or "disabled"


def _object_lock_config() -> dict[str, Any]:
    mode_raw = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "").strip()
    days_raw = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "").strip()
    if not mode_raw and not days_raw:
        return {"mode": None, "retention_days": None, "error": None}

    mode = mode_raw.upper()
    if mode not in {"GOVERNANCE", "COMPLIANCE"}:
        return {
            "mode": None,
            "retention_days": None,
            "error": (
                "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE must be "
                "GOVERNANCE or COMPLIANCE when Object Lock retention is configured."
            ),
        }
    if not days_raw.isdigit() or int(days_raw) < 1:
        return {
            "mode": None,
            "retention_days": None,
            "error": "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS must be a positive integer when Object Lock mode is configured.",
        }
    return {"mode": mode, "retention_days": int(days_raw), "error": None}


def _datetime_text(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return _string(value)


def _retain_until_is_future(value: Any) -> bool:
    if isinstance(value, datetime):
        return value.astimezone(UTC) > datetime.now(UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed.astimezone(UTC) > datetime.now(UTC)
    return False


def _safe(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").replace(":", "_")


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
