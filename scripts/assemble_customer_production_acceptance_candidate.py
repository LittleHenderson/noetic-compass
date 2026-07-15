#!/usr/bin/env python3
"""Assemble one ephemeral customer-production ACCEPT candidate bundle.

The checked-in acceptance manifest remains ``OPEN``.  This command consumes an
externally pinned root-CI signed receipt, performs credential-free GETs against
the exact eight live gate authorities and the exact release-decision authority,
and builds a temporary candidate manifest.  It then invokes the existing
customer-production verifier in normal ``--live`` mode.  Only that verifier may
create the sanitized candidate bundle, and only after every receipt, hash,
freshness, protected-master, deployment, cross-gate, and release check passes.

The output directory must be outside the repository.  This command never
publishes an authority record, creates an approval, changes the checked-in
manifest, or dispatches the separate final ACCEPT workflow.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Iterable, Mapping

import verify_customer_production_acceptance as acceptance


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_CI_GATE = "root_ci_protected_deploy"
LIVE_ISSUER = "noetic-production-live"
LIVE_GATES = tuple(
    gate for gate in acceptance.REQUIRED_GATES if gate != ROOT_CI_GATE
)
LIVE_AUTHORITIES = (*LIVE_GATES, "release_decision")
CANDIDATE_SCHEMA_VERSION = "cas_harness_customer_production_candidate.v2"
FINAL_WORKFLOW = ".github/workflows/customer-production-accept.yml"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AssemblyError(RuntimeError):
    """The candidate could not be assembled without weakening a gate."""


@dataclass(frozen=True)
class PinnedReceipt:
    raw: bytes
    sha256: str
    issuer: str
    key_id: str


@dataclass(frozen=True)
class LiveAuthority:
    gate: str
    uri: str
    raw: bytes
    sha256: str


def _utc_seconds(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _strict_document(raw: bytes, label: str) -> Mapping[str, Any]:
    try:
        document = acceptance._loads_json(raw, label)
    except acceptance.ManifestLoadError as exc:
        raise AssemblyError(f"{label} is not strict JSON") from exc
    if not isinstance(document, Mapping):
        raise AssemblyError(f"{label} must be a JSON object")
    return document


def _timestamp(value: Any, label: str) -> datetime:
    errors: list[str] = []
    parsed = acceptance._timestamp(value, label, errors)
    if parsed is None:
        raise AssemblyError(errors[0] if errors else f"{label} is invalid")
    return parsed


def _require_exact_identity(
    document: Mapping[str, Any],
    *,
    gate: str,
    uri: str,
    expected_master_head: str,
    expected_deploy_id: str,
    verification_time: datetime,
) -> None:
    expected = {
        "schema_version": acceptance.EVIDENCE_SCHEMA_VERSION,
        "gate": gate,
        "environment": "public-production",
        "repository": acceptance.REPOSITORY,
        "master_head_sha": expected_master_head,
        "deploy_id": expected_deploy_id,
        "artifact_uri": uri,
    }
    for field, value in expected.items():
        if document.get(field) != value:
            raise AssemblyError(
                f"{gate} authority {field} does not match the pinned candidate identity"
            )
    artifact_hash = document.get("artifact_sha256")
    if not isinstance(artifact_hash, str) or SHA256_RE.fullmatch(artifact_hash) is None:
        raise AssemblyError(f"{gate} authority artifact_sha256 is invalid")

    event = _timestamp(document.get("event_at_utc"), f"{gate}.event_at_utc")
    observed = _timestamp(
        document.get("observed_at_utc"), f"{gate}.observed_at_utc"
    )
    if event > observed:
        raise AssemblyError(f"{gate} authority event is after its observation")
    if observed > verification_time:
        raise AssemblyError(f"{gate} authority observation is in the future")
    freshness_key = acceptance.GATE_FRESHNESS_KEYS.get(gate)
    if freshness_key is not None:
        maximum = acceptance.FRESHNESS_POLICY[freshness_key]
        if verification_time - event > timedelta(minutes=maximum):
            raise AssemblyError(
                f"{gate} authority event is stale; maximum age is {maximum} minutes"
            )
        if verification_time - observed > timedelta(minutes=maximum):
            raise AssemblyError(
                f"{gate} authority observation is stale; maximum age is {maximum} minutes"
            )

    safety_errors = acceptance._find_prohibited_fields(document, f"{gate}.document")
    safety_errors.extend(acceptance._scan_secret_shapes(document, f"{gate}.document"))
    if safety_errors:
        raise AssemblyError(f"{gate} authority failed the secret/PII safety scan")


def _exact_live_endpoint(gate: str) -> str:
    bindings = acceptance.LIVE_AUTHORITY_ENDPOINTS.get(gate)
    if not isinstance(bindings, Mapping) or set(bindings) != {LIVE_ISSUER}:
        raise AssemblyError(
            f"{gate} must have exactly one {LIVE_ISSUER} endpoint binding"
        )
    uri = bindings[LIVE_ISSUER]
    if not isinstance(uri, str):
        raise AssemblyError(f"{gate} live authority endpoint is invalid")
    return uri


def _fetch_live_authority(gate: str, uri: str) -> bytes:
    try:
        return acceptance._fetch_https(
            uri, frozenset({acceptance._origin(uri)})
        )
    except acceptance.ManifestLoadError as exc:
        raise AssemblyError(f"{gate} live authority fetch failed: {exc}") from exc


def _collect_live_authorities(
    *,
    expected_master_head: str,
    expected_deploy_id: str,
    verification_time: datetime,
    fetcher: Callable[[str, str], bytes] | None = None,
) -> dict[str, LiveAuthority]:
    fetch = fetcher or _fetch_live_authority
    authorities: dict[str, LiveAuthority] = {}
    for gate in LIVE_AUTHORITIES:
        uri = _exact_live_endpoint(gate)
        raw = fetch(gate, uri)
        if len(raw) > acceptance.MAX_EVIDENCE_BYTES:
            raise AssemblyError(f"{gate} live authority exceeds the evidence size limit")
        document = _strict_document(raw, f"{gate} live authority")
        _require_exact_identity(
            document,
            gate=gate,
            uri=uri,
            expected_master_head=expected_master_head,
            expected_deploy_id=expected_deploy_id,
            verification_time=verification_time,
        )
        authorities[gate] = LiveAuthority(
            gate=gate,
            uri=uri,
            raw=raw,
            sha256=_sha256(raw),
        )
    if set(authorities) != set(LIVE_AUTHORITIES):
        raise AssemblyError("the exact live authority set was not collected")
    return authorities


def _preflight_receipt_identity(
    receipt: Mapping[str, Any],
    *,
    expected_master_head: str,
    expected_deploy_id: str,
    verification_time: datetime,
) -> tuple[str, str]:
    expected = {
        "schema_version": acceptance.RECEIPT_SCHEMA_VERSION,
        "gate": ROOT_CI_GATE,
        "environment": "public-production",
        "repository": acceptance.REPOSITORY,
        "master_head_sha": expected_master_head,
        "deploy_id": expected_deploy_id,
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            raise AssemblyError(
                f"root-CI receipt {field} does not match the pinned candidate identity"
            )
    issuer = receipt.get("issuer")
    key_id = receipt.get("key_id")
    if not isinstance(issuer, str) or not issuer:
        raise AssemblyError("root-CI receipt issuer is invalid")
    if not isinstance(key_id, str) or not key_id:
        raise AssemblyError("root-CI receipt key_id is invalid")
    issued = _timestamp(receipt.get("issued_at_utc"), "root-CI receipt issued_at_utc")
    expires = _timestamp(
        receipt.get("expires_at_utc"), "root-CI receipt expires_at_utc"
    )
    if issued > verification_time:
        raise AssemblyError("root-CI receipt was issued in the future")
    if expires < verification_time:
        raise AssemblyError("root-CI receipt is expired")
    if expires < issued:
        raise AssemblyError("root-CI receipt expires before issuance")
    if expires - issued != timedelta(
        minutes=acceptance.ROOT_CI_RECEIPT_TTL_MINUTES
    ):
        raise AssemblyError(
            "root-CI receipt TTL must be exactly "
            f"{acceptance.ROOT_CI_RECEIPT_TTL_MINUTES} minutes"
        )
    evidence = receipt.get("evidence")
    if not isinstance(evidence, Mapping):
        raise AssemblyError("root-CI receipt evidence is invalid")
    if evidence.get("master_head_sha") != expected_master_head:
        raise AssemblyError("root-CI receipt evidence master_head_sha mismatches")
    if evidence.get("deploy_id") != expected_deploy_id:
        raise AssemblyError("root-CI receipt evidence deploy_id mismatches")
    if evidence.get("root_ci_schema_version") != acceptance.ROOT_CI_SCHEMA_VERSION:
        raise AssemblyError("root-CI receipt evidence schema marker mismatches")
    if evidence.get("artifact_uri") != receipt.get("subject_uri"):
        raise AssemblyError("root-CI receipt subject URI binding mismatches")
    if evidence.get("artifact_sha256") != receipt.get("subject_sha256"):
        raise AssemblyError("root-CI receipt subject SHA-256 binding mismatches")
    return issuer, key_id


def _load_pinned_root_receipt(
    *,
    receipt_path: Path,
    expected_receipt_sha256: str,
    expected_master_head: str,
    expected_deploy_id: str,
    verification_time: datetime,
    repo_root: Path,
) -> PinnedReceipt:
    if SHA256_RE.fullmatch(expected_receipt_sha256) is None:
        raise AssemblyError("root-CI receipt pin must be a lowercase SHA-256")
    try:
        raw = acceptance._read_bounded(receipt_path, "root-CI signed receipt")
    except acceptance.ManifestLoadError as exc:
        raise AssemblyError(str(exc)) from exc
    actual_hash = _sha256(raw)
    if actual_hash != expected_receipt_sha256:
        raise AssemblyError("root-CI signed receipt does not match its external SHA-256 pin")
    receipt = _strict_document(raw, "root-CI signed receipt")
    issuer, key_id = _preflight_receipt_identity(
        receipt,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        verification_time=verification_time,
    )

    try:
        trusted_issuers, registry_hash = acceptance._load_trusted_issuer_registry(
            repo_root
        )
    except acceptance.ManifestLoadError as exc:
        raise AssemblyError(f"trusted issuer registry is invalid: {exc}") from exc
    context = acceptance.ValidationContext(
        repo_root=repo_root,
        evidence_root=receipt_path.parent,
        verification_time=verification_time,
        generated_at=verification_time,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        repository_commit=expected_master_head,
        live=False,
        trusted_issuers=trusted_issuers,
        registry_sha256=registry_hash,
    )
    evidence = acceptance._validate_receipt(
        receipt,
        gate=ROOT_CI_GATE,
        issuer_name=issuer,
        key_id=key_id,
        context=context,
        path="$.candidate.root_ci_receipt",
    )
    if evidence is not None:
        acceptance._validate_root_ci(evidence, context)
    if context.errors:
        raise AssemblyError(
            "root-CI signed receipt failed authoritative validation: "
            + "; ".join(sorted(set(context.errors)))
        )
    return PinnedReceipt(
        raw=raw,
        sha256=actual_hash,
        issuer=issuer,
        key_id=key_id,
    )


def _load_open_template(repo_root: Path) -> dict[str, Any]:
    path = repo_root / acceptance.DEFAULT_MANIFEST
    try:
        manifest, _ = acceptance.load_manifest(path)
    except acceptance.ManifestLoadError as exc:
        raise AssemblyError(f"checked-in OPEN manifest is invalid: {exc}") from exc
    template = deepcopy(dict(manifest))
    product = template.get("product")
    gates = template.get("required_gates")
    if not isinstance(product, Mapping) or product.get("status") != "OPEN":
        raise AssemblyError("checked-in customer-production manifest must remain OPEN")
    if not isinstance(gates, Mapping) or any(
        not isinstance(gates.get(gate), Mapping)
        or gates[gate].get("status") != "OPEN"
        or gates[gate].get("evidence") is not None
        for gate in acceptance.REQUIRED_GATES
    ):
        raise AssemblyError("every checked-in customer-production gate must remain OPEN")
    return template


def _build_candidate_manifest(
    *,
    template: Mapping[str, Any],
    generated_at: datetime,
    receipt: PinnedReceipt,
    authorities: Mapping[str, LiveAuthority],
) -> dict[str, Any]:
    if set(authorities) != set(LIVE_AUTHORITIES):
        raise AssemblyError("candidate manifest requires the exact live authority set")
    manifest = deepcopy(dict(template))
    manifest["generated_at_utc"] = _utc_seconds(generated_at)
    required_gates: dict[str, dict[str, Any]] = {}
    for gate in acceptance.REQUIRED_GATES:
        if gate == ROOT_CI_GATE:
            reference = {
                "uri": "repo://receipts/root-ci-protected-deploy.json",
                "sha256": receipt.sha256,
                "authority": {
                    "mode": "signed_receipt",
                    "issuer": receipt.issuer,
                    "key_id": receipt.key_id,
                },
            }
        else:
            authority = authorities[gate]
            reference = {
                "uri": authority.uri,
                "sha256": authority.sha256,
                "authority": {
                    "mode": "live_https",
                    "issuer": LIVE_ISSUER,
                    "key_id": None,
                },
            }
        required_gates[gate] = {"status": "present", "evidence": reference}
    release = authorities["release_decision"]
    manifest["required_gates"] = required_gates
    manifest["product"] = {
        "name": "CAS Harness",
        "environment": "public-production",
        "status": "ACCEPT",
        "status_reason": (
            "Candidate assembled only from the pinned root-CI receipt and exact "
            "live public-production authorities; separate final workflow required."
        ),
        "release_decision": {
            "status": "ACCEPT",
            "evidence": {
                "uri": release.uri,
                "sha256": release.sha256,
                "authority": {
                    "mode": "live_https",
                    "issuer": LIVE_ISSUER,
                    "key_id": None,
                },
            },
        },
    }
    return manifest


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _run_verifier(
    *,
    repo_root: Path,
    manifest_path: Path,
    evidence_root: Path,
    output_dir: Path,
    expected_master_head: str,
    expected_deploy_id: str,
) -> Mapping[str, Any]:
    report_path = output_dir / "candidate-verification-report.json"
    command = [
        sys.executable,
        str(repo_root / "scripts/verify_customer_production_acceptance.py"),
        "--manifest",
        str(manifest_path),
        "--repo-root",
        str(repo_root),
        "--evidence-root",
        str(evidence_root),
        "--expected-master-head",
        expected_master_head,
        "--expected-deploy-id",
        expected_deploy_id,
        "--live",
        "--json",
        "--report-path",
        str(report_path),
        "--sanitized-bundle-path",
        str(output_dir),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AssemblyError(
            f"customer-production verifier could not run ({type(exc).__name__})"
        ) from exc
    report: Mapping[str, Any] | None = None
    if report_path.is_file():
        try:
            report = _strict_document(
                report_path.read_bytes(), "candidate verifier report"
            )
        except OSError as exc:
            raise AssemblyError("candidate verifier report could not be read") from exc
    if completed.returncode != 0 or not isinstance(report, Mapping):
        detail = ""
        if isinstance(report, Mapping) and isinstance(report.get("errors"), list):
            safe_errors = [
                str(item)[:500]
                for item in report["errors"][:5]
                if isinstance(item, str) and item
            ]
            if safe_errors:
                detail = ": " + "; ".join(safe_errors)
        raise AssemblyError(
            "authoritative live verifier rejected the candidate" + detail
        )
    if report.get("result") != "ACCEPT" or report.get("accepted") is not True:
        raise AssemblyError("authoritative live verifier did not return ACCEPT")
    if report.get("expected_master_head") != expected_master_head:
        raise AssemblyError("verifier report master SHA binding mismatches")
    if report.get("expected_deploy_id") != expected_deploy_id:
        raise AssemblyError("verifier report deployment binding mismatches")
    return report


def _outside_repository(path: Path, repo_root: Path) -> bool:
    resolved = path.resolve()
    repository = repo_root.resolve()
    return resolved != repository and repository not in resolved.parents


def assemble_candidate(
    *,
    repo_root: Path,
    receipt_path: Path,
    receipt_sha256: str,
    expected_master_head: str,
    expected_deploy_id: str,
    output_dir: Path,
    now: datetime | None = None,
    fetcher: Callable[[str, str], bytes] | None = None,
) -> Mapping[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    verification_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if acceptance.SHA1_RE.fullmatch(expected_master_head) is None:
        raise AssemblyError("expected master HEAD must be a lowercase 40-character SHA")
    if not isinstance(expected_deploy_id, str) or not expected_deploy_id.startswith(
        "dep-"
    ):
        raise AssemblyError("expected deploy ID must be a Render deployment ID")
    repository_commit = acceptance._repository_commit(repo_root)
    if repository_commit != expected_master_head:
        raise AssemblyError(
            "checked-out repository commit does not match expected protected master HEAD"
        )
    if not _outside_repository(output_dir, repo_root):
        raise AssemblyError("candidate output directory must be outside the repository")
    if output_dir.exists():
        raise AssemblyError("candidate output directory must not already exist")
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    receipt = _load_pinned_root_receipt(
        receipt_path=receipt_path.resolve(),
        expected_receipt_sha256=receipt_sha256,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        verification_time=verification_time,
        repo_root=repo_root,
    )
    authorities = _collect_live_authorities(
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        verification_time=verification_time,
        fetcher=fetcher,
    )
    template = _load_open_template(repo_root)
    manifest = _build_candidate_manifest(
        template=template,
        generated_at=verification_time,
        receipt=receipt,
        authorities=authorities,
    )

    created_output = False
    try:
        with tempfile.TemporaryDirectory(
            prefix="cas-customer-production-candidate-",
            dir=output_dir.parent,
        ) as temporary:
            staging = Path(temporary)
            manifest_path = staging / "customer-production-acceptance.json"
            receipt_target = staging / "receipts/root-ci-protected-deploy.json"
            _write_json(manifest_path, manifest)
            receipt_target.parent.mkdir(parents=True, exist_ok=True)
            receipt_target.write_bytes(receipt.raw)
            report = _run_verifier(
                repo_root=repo_root,
                manifest_path=manifest_path,
                evidence_root=staging,
                output_dir=output_dir,
                expected_master_head=expected_master_head,
                expected_deploy_id=expected_deploy_id,
            )
            created_output = output_dir.is_dir()
        if not created_output:
            raise AssemblyError("verifier did not create the candidate bundle")
        index_path = output_dir / "sanitized-bundle-index.json"
        if not index_path.is_file():
            raise AssemblyError("candidate sanitized-bundle index is missing")
        index = _strict_document(index_path.read_bytes(), "candidate bundle index")
        evidence_index = index.get("evidence")
        if not isinstance(evidence_index, Mapping):
            raise AssemblyError("candidate evidence index is invalid")
        expected_hashes = {
            ROOT_CI_GATE: receipt.sha256,
            **{gate: authority.sha256 for gate, authority in authorities.items()},
        }
        for gate, expected_hash in expected_hashes.items():
            entry = evidence_index.get(gate)
            if not isinstance(entry, Mapping) or entry.get("sha256") != expected_hash:
                raise AssemblyError(f"candidate bundle index hash mismatches for {gate}")
        metadata = {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "scope": "candidate_bundle_for_separate_final_workflow",
            "assembled_at_utc": _utc_seconds(verification_time),
            "repository": acceptance.REPOSITORY,
            "master_head_sha": expected_master_head,
            "deploy_id": expected_deploy_id,
            "root_ci_receipt_sha256": receipt.sha256,
            "live_authority_sha256": {
                gate: authorities[gate].sha256 for gate in LIVE_AUTHORITIES
            },
            "manifest_sha256": report.get("manifest_sha256"),
            "verifier_sha256": report.get("verifier_sha256"),
            "verification_result": "ACCEPT",
            "candidate_only": True,
            "authority_writes_performed": False,
            "approval_records_created": False,
            "final_workflow": FINAL_WORKFLOW,
            "final_workflow_dispatched": False,
            "final_release_effect": "none",
        }
        _write_json(output_dir / "candidate-assembly.json", metadata)
        return metadata
    except Exception:
        if output_dir.is_dir():
            shutil.rmtree(output_dir)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--root-ci-receipt", type=Path, required=True)
    parser.add_argument("--root-ci-receipt-sha256", required=True)
    parser.add_argument("--expected-master-head", required=True)
    parser.add_argument("--expected-deploy-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = assemble_candidate(
            repo_root=args.repo_root,
            receipt_path=args.root_ci_receipt,
            receipt_sha256=args.root_ci_receipt_sha256,
            expected_master_head=args.expected_master_head,
            expected_deploy_id=args.expected_deploy_id,
            output_dir=args.output_dir,
        )
    except AssemblyError as exc:
        print(f"customer-production candidate assembly failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
