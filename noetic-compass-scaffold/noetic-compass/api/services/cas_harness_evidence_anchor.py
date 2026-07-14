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
from urllib.parse import parse_qs, quote, unquote, urlparse

from api.services.cas_harness_retention_disclosure import (
    _issue_live_s3_object_lock_receipt,
    evaluate_object_lock_receipt,
    require_stable_object_lock_receipt_attestation_key,
    runtime_object_lock_policy_target,
)


AnchorStatus = str


def anchor_hash_log_entry(
    *,
    trace_id: str,
    hash_log_entry: Mapping[str, Any],
    packet_path: Path | str,
    hash_log_path: Path | str,
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
    packet_path: Path | str,
    hash_log_path: Path | str,
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
                "content-sha256": hashlib.sha256(body).hexdigest(),
            },
        }
        object_lock = _object_lock_config()
        if object_lock["error"]:
            return _s3_failed(manifest, object_lock["error"])
        object_lock_mode = object_lock["mode"]
        retention_days = object_lock["retention_days"]
        retention_requested_at = None
        retain_until = None
        if object_lock_mode and retention_days:
            require_stable_object_lock_receipt_attestation_key()
            retention_requested_at = datetime.now(UTC).replace(microsecond=0)
            retain_until = retention_requested_at + timedelta(days=retention_days)
            put_kwargs["ObjectLockMode"] = object_lock_mode
            put_kwargs["ObjectLockRetainUntilDate"] = retain_until
            put_kwargs["ContentMD5"] = base64.b64encode(hashlib.md5(body).digest()).decode("ascii")
            put_kwargs["Metadata"].update(
                {
                    "retention-mode": object_lock_mode,
                    "retention-days": str(retention_days),
                    "retention-requested-at": retention_requested_at.isoformat(),
                    "retention-requested-until": retain_until.isoformat(),
                }
            )
        response = client.put_object(**put_kwargs)
    except Exception as exc:
        return _s3_failed(manifest, f"S3 anchor write failed: {type(exc).__name__}: {exc}")

    version_id = _string(response.get("VersionId")) if isinstance(response, Mapping) else None
    if object_lock_mode and not version_id:
        return _s3_failed(
            manifest,
            "S3 Object Lock anchor write did not return a VersionId; exact-version verification is impossible.",
        )

    encoded_key = quote(key, safe="/")
    version_suffix = (
        f"?versionId={quote(version_id, safe='')}" if version_id else ""
    )
    return {
        "status": "anchored",
        "mode": "s3",
        "anchor_uri": f"s3://{bucket}/{encoded_key}{version_suffix}",
        "bucket": bucket,
        "key": key,
        "version_id": version_id,
        "etag": _string(response.get("ETag")) if isinstance(response, Mapping) else None,
        "manifest_sha256": _sha256_json(manifest),
        "anchored_at": _string(manifest.get("anchored_at")),
        "object_lock_mode": object_lock_mode or None,
        "retention_requested_at": (
            retention_requested_at.isoformat() if retention_requested_at else None
        ),
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
    version_id = _string(anchor.get("version_id"))
    anchor_uri = _string(anchor.get("anchor_uri"))
    expected_manifest_hash = _string(anchor.get("manifest_sha256"))
    if not bucket or not key or not expected_manifest_hash or not anchor_uri:
        return _anchor_check(
            expected_manifest_hash,
            None,
            False,
            "S3 anchor receipt is missing anchor_uri, bucket, key, or manifest_sha256",
        )
    parsed_uri = urlparse(anchor_uri)
    try:
        uri_query = parse_qs(
            parsed_uri.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError:
        uri_query = {}
    expected_query = {"versionId": [version_id]} if version_id else {}
    if (
        parsed_uri.scheme != "s3"
        or parsed_uri.netloc != bucket
        or unquote(parsed_uri.path.lstrip("/")) != key
        or uri_query != expected_query
        or bool(parsed_uri.fragment)
    ):
        return _anchor_check(
            expected_manifest_hash,
            None,
            False,
            "S3 anchor_uri is not an exact s3:// object-version receipt",
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

    expected_object_lock_mode = _string(anchor.get("object_lock_mode"))
    get_kwargs: dict[str, Any] = {"Bucket": bucket, "Key": key}
    if version_id:
        get_kwargs["VersionId"] = version_id
    elif expected_object_lock_mode:
        return _anchor_check(
            expected_manifest_hash,
            None,
            False,
            "S3 Object Lock anchor receipt is missing VersionId; exact-version re-read was refused",
        )

    try:
        client = boto3.client("s3", **client_kwargs)
        response = client.get_object(**get_kwargs)
        body = response["Body"].read()
    except Exception as exc:
        return _anchor_check(
            expected_manifest_hash,
            None,
            False,
            f"S3 anchor object re-read failed: {type(exc).__name__}: {exc}",
        )

    actual_manifest_hash = hashlib.sha256(body).hexdigest()
    object_lock_verification = None
    if expected_object_lock_mode:
        head_kwargs = {"Bucket": bucket, "Key": key, "VersionId": version_id}
        try:
            head = client.head_object(**head_kwargs)
        except Exception as exc:
            failed_verification = evaluate_object_lock_receipt(
                expected={
                    "bucket": bucket,
                    "key": key,
                    "version_id": version_id,
                    "content_sha256": expected_manifest_hash,
                    "mode": expected_object_lock_mode,
                    "retention_days": anchor.get("retention_days"),
                    "requested_at": anchor.get("retention_requested_at"),
                    "retain_until": anchor.get("object_lock_retain_until"),
                },
                observed={
                    "bucket": bucket,
                    "key": key,
                    "get_version_id": response.get("VersionId"),
                    "head_version_id": None,
                    "content_sha256": actual_manifest_hash,
                    "mode": None,
                    "retain_until": None,
                    "reread_verified": False,
                },
            )
            return _anchor_check(
                expected_manifest_hash,
                actual_manifest_hash,
                False,
                f"S3 Object Lock metadata re-read failed: {type(exc).__name__}: {exc}",
                object_lock_verification=failed_verification.to_dict(),
            )
        metadata_expectation, metadata_error = _s3_anchor_metadata_expectation(
            head,
            expected_content_hash=expected_manifest_hash,
        )
        local_requested_at = _aware_datetime(anchor.get("retention_requested_at"))
        local_requested_until = _aware_datetime(
            anchor.get("object_lock_retain_until")
        )
        local_days = anchor.get("retention_days")
        local_metadata_match = bool(
            metadata_expectation is not None
            and expected_object_lock_mode == metadata_expectation["mode"]
            and isinstance(local_days, int)
            and not isinstance(local_days, bool)
            and local_days == metadata_expectation["retention_days"]
            and local_requested_at == metadata_expectation["requested_at"]
            and local_requested_until
            == metadata_expectation["requested_retain_until"]
        )
        if not local_metadata_match:
            failure_expected = metadata_expectation or {
                "mode": expected_object_lock_mode,
                "retention_days": local_days,
                "requested_at": local_requested_at,
                "requested_retain_until": local_requested_until,
            }
            failed_verification = evaluate_object_lock_receipt(
                expected={
                    "bucket": bucket,
                    "key": key,
                    "version_id": version_id,
                    "content_sha256": expected_manifest_hash,
                    "mode": failure_expected.get("mode"),
                    "retention_days": failure_expected.get("retention_days"),
                    "requested_at": failure_expected.get("requested_at"),
                    "retain_until": failure_expected.get("requested_retain_until"),
                },
                observed={
                    "bucket": bucket,
                    "key": key,
                    "get_version_id": response.get("VersionId"),
                    "head_version_id": head.get("VersionId"),
                    "content_sha256": actual_manifest_hash,
                    "mode": head.get("ObjectLockMode"),
                    "retain_until": head.get("ObjectLockRetainUntilDate"),
                    "reread_verified": False,
                },
            )
            detail = metadata_error or (
                "stored anchor retention fields do not match authoritative S3 "
                "request metadata"
            )
            return _anchor_check(
                expected_manifest_hash,
                actual_manifest_hash,
                False,
                f"S3 Object Lock request metadata verification failed: {detail}",
                object_lock_verification=failed_verification.to_dict(),
            )
        assert metadata_expectation is not None
        # Trusted issuer boundary: response/head are direct exact-VersionId S3
        # SDK reads from this verification attempt, not serialized packet facts.
        object_lock_verification = _issue_live_s3_object_lock_receipt(
            expected={
                "bucket": bucket,
                "key": key,
                "version_id": version_id,
                "content_sha256": expected_manifest_hash,
                "mode": metadata_expectation["mode"],
                "retention_days": metadata_expectation["retention_days"],
                "requested_at": metadata_expectation["requested_at"],
                "retain_until": metadata_expectation["requested_retain_until"],
            },
            observed={
                "bucket": bucket,
                "key": key,
                "get_version_id": response.get("VersionId"),
                "head_version_id": head.get("VersionId"),
                "content_sha256": actual_manifest_hash,
                "mode": head.get("ObjectLockMode"),
                "retain_until": head.get("ObjectLockRetainUntilDate"),
                "reread_verified": True,
            },
        )

    if actual_manifest_hash != expected_manifest_hash:
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            False,
            "S3 anchor object hash does not match packet manifest_sha256",
            object_lock_verification=(
                object_lock_verification.to_dict()
                if object_lock_verification is not None
                else None
            ),
        )

    try:
        manifest = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            False,
            f"S3 anchor manifest is not valid canonical JSON: {exc}",
            object_lock_verification=(
                object_lock_verification.to_dict()
                if object_lock_verification is not None
                else None
            ),
        )
    if not isinstance(manifest, Mapping):
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            False,
            "S3 anchor manifest is malformed",
            object_lock_verification=(
                object_lock_verification.to_dict()
                if object_lock_verification is not None
                else None
            ),
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
            object_lock_verification=(
                object_lock_verification.to_dict()
                if object_lock_verification is not None
                else None
            ),
        )

    if expected_object_lock_mode:
        assert object_lock_verification is not None
        if not object_lock_verification.verified:
            return _anchor_check(
                expected_manifest_hash,
                actual_manifest_hash,
                False,
                (
                    "S3 anchor bytes were re-read, but the exact Object Lock receipt failed: "
                    + "; ".join(object_lock_verification.failure_reasons)
                ),
                object_lock_verification=object_lock_verification.to_dict(),
            )
        return _anchor_check(
            expected_manifest_hash,
            actual_manifest_hash,
            True,
            (
                "S3 anchor object was re-read at the exact stored version; its manifest commits "
                "to this packet hash and hash-log entry, and the structured Object Lock receipt matched"
            ),
            object_lock_verification=object_lock_verification.to_dict(),
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


def _anchor_check(
    expected: str | None,
    actual: str | None,
    match: bool,
    notes: str,
    *,
    object_lock_verification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "artifact": "merged_packet_external_anchor",
        "expected": expected,
        "actual": actual,
        "match": match,
        "notes": notes,
    }
    if object_lock_verification is not None:
        result["object_lock_verification"] = dict(object_lock_verification)
    return result


def _anchor_mode() -> AnchorStatus:
    return os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "disabled").strip().lower() or "disabled"


def _object_lock_config() -> dict[str, Any]:
    target = runtime_object_lock_policy_target()
    if not target.configured:
        return {"mode": None, "retention_days": None, "error": None}
    return {
        "mode": target.mode if target.valid else None,
        "retention_days": target.retention_days if target.valid else None,
        "error": target.error,
    }


def _s3_anchor_metadata_expectation(
    head: Mapping[str, Any],
    *,
    expected_content_hash: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Recover immutable write-request facts from authoritative S3 metadata."""

    metadata = head.get("Metadata")
    if not isinstance(metadata, Mapping):
        return None, "S3 response is missing object request metadata"
    content_hash = _string(metadata.get("content-sha256"))
    mode = _string(metadata.get("retention-mode"))
    days_text = _string(metadata.get("retention-days"))
    requested_at = _aware_datetime(metadata.get("retention-requested-at"))
    requested_until = _aware_datetime(metadata.get("retention-requested-until"))
    if content_hash != expected_content_hash:
        return None, "S3 request metadata does not bind the manifest content hash"
    if mode not in {"GOVERNANCE", "COMPLIANCE"}:
        return None, "S3 request metadata has no valid Object Lock mode"
    if days_text is None or not days_text.isdigit() or int(days_text) < 1:
        return None, "S3 request metadata has no positive retention_days"
    retention_days = int(days_text)
    if requested_at is None or requested_until is None:
        return None, "S3 request metadata has no timezone-aware request boundary"
    if requested_until < requested_at + timedelta(days=retention_days):
        return None, "S3 request metadata is shorter than the full retention window"
    return (
        {
            "mode": mode,
            "retention_days": retention_days,
            "requested_at": requested_at,
            "requested_retain_until": requested_until,
        },
        None,
    )


def _aware_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _datetime_text(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return _string(value)


def _safe(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").replace(":", "_")


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
