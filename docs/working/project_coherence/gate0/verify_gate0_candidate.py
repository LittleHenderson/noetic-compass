#!/usr/bin/env python3
"""Fail-closed verifier for the Project Coherence Gate 0 candidate package.

This verifier checks identity, structure, conservative status, source coverage,
and the compiler line-ending receipt.  It does not review mathematics, accept
the charter, license a claim, or approve disclosure.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


GATE0_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
PHASE0_DIR = REPO_ROOT / "docs" / "working" / "project_coherence"

AUTHORITY_FILE = "STANDING_EXECUTION_AUTHORITY_RECEIPT_v0.1.json"
COMPILER_FILE = "COMPILER_IDENTITY_NORMALIZATION_RECEIPT_v0.1.json"
FREEZE_FILE = "BASELINE_FREEZE_CANDIDATE_v0.1.json"
CLOSURE_FILE = "GATE0_CLOSURE_MATRIX_v0.1.json"
MANIFEST_FILE = "GATE0_ARTIFACT_MANIFEST_v0.1.json"
TERM_CENSUS_FILE = "term_census/GATE0_LOAD_BEARING_TERM_CENSUS_v0.1.json"
TERM_CENSUS_AUDIT_FILE = "term_census/GATE0_TERM_CENSUS_AUDIT_v0.1.md"
TERM_CENSUS_VERIFIER_FILE = "term_census/verify_gate0_term_census.py"

SOURCE_MATRIX = PHASE0_DIR / "CANONICAL_SOURCE_AUTHORITY_MATRIX_v0.1.json"
SYMBOL_REGISTRY = PHASE0_DIR / "SYMBOL_AND_TERMINOLOGY_REGISTRY_v0.1.json"

SHA256_RE = re.compile(r"[A-F0-9]{64}")


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> Any:
    require(path.is_file(), f"missing JSON artifact: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse {path}: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def require_sha256(value: Any, label: str) -> str:
    require(isinstance(value, str) and SHA256_RE.fullmatch(value), f"{label}: invalid uppercase SHA-256")
    return value


def unique_ids(records: Iterable[dict[str, Any]], label: str) -> set[str]:
    ids: list[str] = []
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"{label}[{index}] is not an object")
        value = record.get("id")
        require(isinstance(value, str) and value, f"{label}[{index}] has no id")
        ids.append(value)
    require(len(ids) == len(set(ids)), f"{label} contains duplicate ids")
    return set(ids)


def verify_bound_file(record: dict[str, Any], root: Path, label: str) -> Path:
    raw_path = record.get("path")
    require(isinstance(raw_path, str) and raw_path, f"{label}: path missing")
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    require(path.is_file(), f"{label}: source missing at {path}")
    expected_hash = require_sha256(record.get("sha256"), label)
    require(sha256_file(path) == expected_hash, f"{label}: SHA-256 mismatch")
    expected_bytes = record.get("bytes")
    if expected_bytes is not None:
        require(path.stat().st_size == expected_bytes, f"{label}: byte-size mismatch")
    return path


def verify_manifest() -> None:
    manifest = load_json(GATE0_DIR / MANIFEST_FILE)
    require(manifest.get("document_status") == "CANDIDATE / NOT FROZEN", "manifest status is not fail-closed")
    records = manifest.get("artifacts")
    require(isinstance(records, list) and records, "manifest has no artifacts")
    names = {record.get("path") for record in records}
    expected = {
        AUTHORITY_FILE,
        COMPILER_FILE,
        FREEZE_FILE,
        CLOSURE_FILE,
        TERM_CENSUS_FILE,
        TERM_CENSUS_AUDIT_FILE,
        TERM_CENSUS_VERIFIER_FILE,
        Path(__file__).name,
    }
    require(names == expected, f"manifest artifact set mismatch: expected {sorted(expected)}, got {sorted(names)}")
    for record in records:
        verify_bound_file(record, GATE0_DIR, f"manifest:{record.get('path')}")


def verify_standing_authority(document: dict[str, Any]) -> None:
    require("NONCRYPTOGRAPHIC" in document.get("artifact_status", ""), "standing authority lacks noncryptographic status")
    source = document.get("authorization_source")
    require(isinstance(source, dict), "standing authority has no source record")
    require(source.get("kind") == "UNHASHED_INTERACTIVE_CONVERSATION", "standing authority overstates source durability")
    require(source.get("speaker_identity_independently_verified") is False, "standing authority overstates identity verification")
    require(source.get("verbatim_quote_recorded_here") is False, "standing authority unexpectedly claims a verbatim quote")
    authorized = document.get("authorizes")
    defaults = document.get("mandatory_defaults")
    interrupts = document.get("interrupt_only_for")
    exclusions = document.get("does_not_authorize_or_establish")
    require(isinstance(authorized, list) and len(authorized) >= 5, "standing authority scope is incomplete")
    require(isinstance(defaults, list) and len(defaults) >= 6, "standing authority defaults are incomplete")
    require(isinstance(interrupts, list) and len(interrupts) >= 5, "standing authority interrupt boundary is incomplete")
    require(isinstance(exclusions, list) and len(exclusions) >= 5, "standing authority exclusions are incomplete")
    joined = " ".join(exclusions).lower()
    for required in ("final freeze", "public release", "peer review", "cryptographic", "product claim"):
        require(required in joined, f"standing authority exclusions omit {required!r}")
    effect = document.get("gate_effect")
    require(isinstance(effect, dict), "standing authority has no gate effect")
    require(effect.get("gate0_freeze") == "NOT ESTABLISHED", "standing authority silently freezes Gate 0")
    require(effect.get("product_claim_effect") == "NONE", "standing authority mutates product claims")


def resolve_phase0_source(record: dict[str, Any]) -> Path:
    raw = record.get("path")
    require(isinstance(raw, str) and raw, f"source {record.get('id')}: path missing")
    kind = record.get("path_kind")
    if kind == "repository_relative":
        return REPO_ROOT / raw
    require(kind == "external_absolute", f"source {record.get('id')}: invalid path_kind")
    path = Path(raw)
    require(path.is_absolute(), f"source {record.get('id')}: external path is not absolute")
    return path


def verify_phase0_sources(source_matrix: dict[str, Any]) -> set[str]:
    records = source_matrix.get("sources")
    require(isinstance(records, list) and len(records) == 25, "source matrix must contain 25 records")
    source_ids = unique_ids(records, "source records")
    static_count = 0
    for record in records:
        path = resolve_phase0_source(record)
        require(record.get("availability") == "present", f"source {record['id']}: unexpected availability")
        require(path.is_file(), f"source {record['id']}: missing at {path}")
        if record.get("verify_hash"):
            expected = require_sha256(record.get("sha256"), f"source {record['id']}")
            require(sha256_file(path) == expected, f"source {record['id']}: SHA-256 mismatch")
            if record.get("bytes") is not None:
                require(path.stat().st_size == record["bytes"], f"source {record['id']}: byte-size mismatch")
            static_count += 1
        else:
            require(record.get("sha256") is None, f"source {record['id']}: mutable source carries frozen hash")
    require(static_count == 24, f"expected 24 static source hashes, got {static_count}")
    return source_ids


def verify_freeze_candidate(document: dict[str, Any], source_ids: set[str]) -> None:
    status = document.get("document_status", "")
    require("NOT FROZEN" in status and "NOT OWNER-ACCEPTED" in status, "freeze candidate status is too strong")
    for record in document.get("evidence_inputs", []):
        verify_bound_file(record, REPO_ROOT, f"evidence:{record.get('path')}")
    for record in document.get("external_authority_inputs", []):
        verify_bound_file(record, REPO_ROOT, f"external-authority:{record.get('source_id')}")

    groups = document.get("baseline_groups")
    require(isinstance(groups, list) and groups, "freeze candidate has no baseline groups")
    unique_ids(groups, "baseline groups")
    memberships: list[str] = []
    for group in groups:
        members = group.get("member_source_ids")
        require(isinstance(members, list) and members, f"group {group['id']}: no members")
        require(isinstance(group.get("authority_policy"), str) and group["authority_policy"], f"group {group['id']}: authority policy missing")
        require(isinstance(group.get("identity_policy"), str) and group["identity_policy"], f"group {group['id']}: identity policy missing")
        require(group.get("candidate_treatment", "").endswith("IF_CANDIDATE_ACCEPTED"), f"group {group['id']}: treatment is not conditional")
        memberships.extend(members)
    require(len(memberships) == len(set(memberships)), "a source belongs to multiple baseline groups")
    require(set(memberships) == source_ids, "baseline groups do not cover exactly the 25 Phase 0 sources")

    variants = document.get("variant_sets")
    require(isinstance(variants, list) and len(variants) >= 6, "freeze candidate lacks required variant sets")
    variant_ids = unique_ids(variants, "variant sets")
    required_variants = {
        "VARIANT-TKS74-REGISTERED-VS-UNREGISTERED-EDITIONS",
        "VARIANT-OWNER-40-28-D3DA-VS-A124",
        "VARIANT-CAS77-LF-VS-CRLF",
        "VARIANT-COMPILER-LF-VS-CRLF",
        "VARIANT-PCBA-HASH-VS-INTERNAL-LABEL",
        "VARIANT-HARNESS-HISTORICAL-VS-LIVE",
    }
    require(required_variants <= variant_ids, "freeze candidate lacks a required variant policy")

    cas77_repo = REPO_ROOT / "docs" / "CAS_FOUNDATIONAL_CLARIFICATIONS.md"
    cas77_registered = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\CAS_FOUNDATIONAL_CLARIFICATIONS.md")
    require(cas77_repo.is_file() and cas77_registered.is_file(), "CAS v7.7 normalization sources are missing")
    repo_bytes = cas77_repo.read_bytes()
    registered_bytes = cas77_registered.read_bytes()
    require(repo_bytes.replace(b"\r\n", b"\n") == registered_bytes, "CAS v7.7 LF/CRLF relation no longer reproduces")
    require(sha256_bytes(repo_bytes) == "8791980E0F4F7D95BA325175FB200A980AC803120EA2EFD3586DA06832A35018", "CAS v7.7 raw checkout hash drift")
    require(sha256_bytes(registered_bytes) == "CDA85C03273C47F7DF9AC53258920B95BA7B3B2007B0E760856A67497F661880", "CAS v7.7 registered hash drift")

    raw_variant = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\tks_owner_locked_definitions_20260603.json")
    require(raw_variant.is_file(), "D3DA owner payload is missing")
    require(sha256_file(raw_variant) == "D3DAC0EF5C94CCD768DA0F18987846D8D0C0FA0B366E13DCCC49C82252D2FC12", "D3DA owner payload hash drift")

    effect = document.get("candidate_effect")
    require(isinstance(effect, dict), "freeze candidate has no effect record")
    require(effect.get("final_canon_freeze") == "OPEN", "freeze candidate silently closes canon")
    require(effect.get("product_claim_effect") == "NONE", "freeze candidate mutates product claims")
    require(effect.get("public_disclosure") == "NOT AUTHORIZED", "freeze candidate authorizes disclosure")


def git_blob(commit: str, path: str) -> bytes:
    try:
        return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=REPO_ROOT)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(f"cannot read Git blob {commit}:{path}: {exc}") from exc


def git_text(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=REPO_ROOT).decode("ascii").strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(f"git {' '.join(args)} failed: {exc}") from exc


def verify_compiler_receipt(document: dict[str, Any]) -> None:
    require(document.get("candidate_disposition") == "RESOLVED_BY_REPRODUCIBLE_TEXT_NORMALIZATION", "compiler receipt disposition mismatch")
    registered = document.get("registered_identity")
    observed = document.get("observed_working_tree_identity")
    normalization = document.get("normalization")
    require(isinstance(registered, dict) and isinstance(observed, dict) and isinstance(normalization, dict), "compiler receipt is incomplete")
    path = registered.get("git_path")
    commit = registered.get("git_commit")
    require(isinstance(path, str) and isinstance(commit, str), "compiler receipt Git identity missing")
    registry_blob = git_blob(commit, path)
    baseline_blob = git_blob("5a7fdb636d0be5939fbb6b079feb7c404c83236a", path)
    expected = require_sha256(registered.get("registry_sha256"), "registered compiler")
    require(sha256_bytes(registry_blob) == expected, "registry commit compiler SHA-256 mismatch")
    require(len(registry_blob) == registered.get("bytes"), "registry commit compiler byte-size mismatch")
    require(baseline_blob == registry_blob, "Phase 0 baseline compiler Git blob differs from registry commit")
    require(git_text("rev-parse", f"{commit}:{path}") == registered.get("git_blob_oid_sha1"), "registry compiler Git blob OID mismatch")
    require(git_text("rev-parse", f"5a7fdb636d0be5939fbb6b079feb7c404c83236a:{path}") == registered.get("git_blob_oid_sha1"), "Phase 0 compiler Git blob OID mismatch")

    crlf_reconstruction = registry_blob.replace(b"\n", b"\r\n")
    raw_expected = require_sha256(observed.get("sha256"), "observed compiler")
    require(sha256_bytes(crlf_reconstruction) == raw_expected, "compiler CRLF reconstruction SHA-256 mismatch")
    require(len(crlf_reconstruction) == observed.get("bytes"), "compiler CRLF reconstruction byte-size mismatch")
    require(crlf_reconstruction.count(b"\r\n") == observed.get("crlf_sequences"), "compiler CRLF count mismatch")
    require(registry_blob.count(b"\r") == 0, "registered compiler blob unexpectedly contains CR bytes")
    require(normalization.get("normalized_sha256") == expected, "compiler normalized hash does not equal registry hash")
    require(normalization.get("normalized_bytes_equal_registered_git_blob") is True, "compiler receipt does not assert exact normalized identity")

    external = Path(observed.get("absolute_path", ""))
    if external.is_file():
        external_bytes = external.read_bytes()
        require(sha256_bytes(external_bytes) == raw_expected, "current external compiler raw hash drift")
        require(external_bytes.replace(b"\r\n", b"\n") == registry_blob, "current external compiler no longer normalizes to registered blob")

    boundary = " ".join(document.get("claim_boundary", [])).lower()
    for required in ("compiler correctness", "empirical validity", "does not amend"):
        require(required in boundary, f"compiler receipt boundary omits {required!r}")


def verify_authority_inputs(freeze: dict[str, Any]) -> None:
    records = {record["source_id"]: record for record in freeze.get("external_authority_inputs", [])}
    registry_path = Path(records["SRC-SEMANTIC-AUTHORITY-REGISTRY-20260720"]["path"])
    receipt_path = Path(records["SRC-SEMANTIC-AUTHORITY-RECEIPT-20260724"]["path"])
    registry = load_json(registry_path)
    receipt = load_json(receipt_path)
    require(registry.get("status") == "OWNER_SIGNED_SEMANTIC_AUTHORITY_REGISTRY", "semantic registry internal status mismatch")
    require(len(registry.get("sources", [])) == 20, "semantic registry source count mismatch")
    require(len(registry.get("known_conflicts", [])) == 12, "semantic registry conflict count mismatch")
    require(len(registry.get("claim_bearing_precedence", [])) == 8, "semantic registry precedence count mismatch")
    require(len(registry.get("required_run_bindings", [])) == 25, "semantic registry run-binding count mismatch")
    require(len(registry.get("future_agent_rules", [])) == 7, "semantic registry future-rule count mismatch")
    approval = registry.get("owner_approval")
    require(isinstance(approval, dict), "semantic registry has no owner approval record")
    require("not a cryptographic or legal signature" in approval.get("signature_kind", "").lower(), "semantic registry overstates signature")
    require("Licenses no empirical claim" in approval.get("scope_note", ""), "semantic registry approval lacks empirical-claim boundary")
    require(receipt.get("approved") is True, "semantic approval receipt is not approved")
    require(len(receipt.get("does_not_approve", [])) >= 3, "semantic approval receipt lacks exclusions")
    require("NOT a cryptographic signature" in receipt.get("signature_kind", ""), "semantic receipt overstates signature")


def verify_term_registry() -> None:
    document = load_json(SYMBOL_REGISTRY)
    entries = document.get("entries")
    require(isinstance(entries, list) and len(entries) == 24, "starter term registry must contain 24 entries")
    unique_ids(entries, "term entries")
    fields = {"id", "canonical_name", "semantic_type", "version_scope", "source_refs", "aliases_allowed", "migration_policy"}
    for entry in entries:
        missing = fields - set(entry)
        require(not missing, f"term {entry.get('id')}: missing fields {sorted(missing)}")
        require(isinstance(entry["source_refs"], list) and entry["source_refs"], f"term {entry['id']}: source refs missing")
        require(isinstance(entry["aliases_allowed"], list), f"term {entry['id']}: aliases_allowed is not a list")


def verify_term_census() -> None:
    document = load_json(GATE0_DIR / TERM_CENSUS_FILE)
    completeness = document.get("completeness")
    require(isinstance(completeness, dict), "term census completeness record missing")
    require(completeness.get("imported_registered_entries") == 24, "term census starter import count drift")
    require(completeness.get("term_group_count") == 49, "term census group count drift")
    require(completeness.get("enumerated_group_member_count") == 695, "term census member count drift")
    require(completeness.get("conflict_guard_count") == 14, "term census conflict count drift")
    require(completeness.get("coverage_class_count") == 13, "term census coverage count drift")
    require(
        completeness.get("closure_effect", "").startswith("Supplies technical evidence"),
        "term census overstates Gate 0 closure",
    )
    completed = subprocess.run(
        [sys.executable, str(GATE0_DIR / TERM_CENSUS_VERIFIER_FILE)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    require(
        completed.returncode == 0 and "PASS Gate0 term census" in completed.stdout,
        f"term census verifier failed:\n{completed.stdout}{completed.stderr}",
    )


def verify_closure_matrix(document: dict[str, Any], source_matrix: dict[str, Any]) -> None:
    require(document.get("overall_status") == "OPEN", "Gate 0 closure matrix is not OPEN")
    require("NOT FROZEN" in document.get("document_status", ""), "Gate 0 closure matrix is not explicitly NOT FROZEN")
    criteria = document.get("criteria")
    require(isinstance(criteria, list) and len(criteria) == 6, "Gate 0 must contain exactly six charter criteria")
    unique_ids(criteria, "Gate 0 criteria")
    allowed = {"OPEN", "PARTIAL", "EVIDENCE_COMPLETE_PENDING_ACCEPTANCE"}
    for criterion in criteria:
        require(criterion.get("status") in allowed, f"criterion {criterion['id']}: invalid or premature status")
        require(criterion.get("responsible_role"), f"criterion {criterion['id']}: responsible role missing")
        require(criterion.get("next_action"), f"criterion {criterion['id']}: next action missing")
    require(not any(item.get("status") == "SATISFIED_AND_ACCEPTED" for item in criteria), "candidate matrix prematurely accepts a criterion")
    term_criterion = next(
        item for item in criteria if item["id"] == "G0-CRITERION-INITIAL-TERM-COVERAGE"
    )
    require(term_criterion["status"] == "PARTIAL", "term census prematurely closed its criterion")
    require(
        any("695 members" in item for item in term_criterion["evidence"]),
        "closure matrix does not bind the completed term census",
    )

    upstream_conflicts = source_matrix.get("unresolved_conflicts")
    require(isinstance(upstream_conflicts, list) and len(upstream_conflicts) == 14, "upstream source matrix must contain 14 conflicts")
    upstream_ids = unique_ids(upstream_conflicts, "upstream conflicts")
    dispositions = document.get("conflict_dispositions")
    require(isinstance(dispositions, list) and len(dispositions) == 14, "Gate 0 must disposition all 14 conflicts")
    disposition_ids = unique_ids(dispositions, "conflict dispositions")
    require(disposition_ids == upstream_ids, "Gate 0 conflict dispositions do not exactly cover upstream conflicts")
    for item in dispositions:
        require(item.get("blocks_research_continuation") is False, f"conflict {item['id']}: conservative continuation unexpectedly blocked")
        require(item.get("responsible_role"), f"conflict {item['id']}: responsible role missing")
        require(item.get("closure_action"), f"conflict {item['id']}: closure action missing")
        require(isinstance(item.get("human_decision_required"), bool), f"conflict {item['id']}: human decision flag missing")
    compiler = next(item for item in dispositions if item["id"] == "CONFLICT-ACTIVE-COMPILER-DRIFT")
    require(compiler.get("candidate_status") == "RESOLVED_BY_REPRODUCIBLE_TEXT_NORMALIZATION", "compiler conflict was not technically resolved")
    require(compiler.get("blocks_final_gate0_freeze") is False, "compiler line endings still block final freeze")

    deferred = document.get("deferred_human_decisions")
    require(isinstance(deferred, list) and deferred, "Gate 0 has no deferred human decisions")
    require(all(item.get("ask_now") is False for item in deferred), "Gate 0 candidate contains an immediate routine question")
    effect = document.get("gate_effect")
    require(isinstance(effect, dict), "Gate 0 has no gate effect")
    require(effect.get("gate0_closure") == "OPEN", "Gate 0 candidate silently closes the gate")
    require(effect.get("baseline_freeze") == "CANDIDATE_ONLY", "Gate 0 candidate silently freezes baselines")
    require(effect.get("product_claim_effect") == "NONE", "Gate 0 candidate mutates product claims")
    require(effect.get("public_disclosure") == "NOT AUTHORIZED", "Gate 0 candidate authorizes public disclosure")


def main() -> int:
    verify_manifest()
    authority = load_json(GATE0_DIR / AUTHORITY_FILE)
    compiler = load_json(GATE0_DIR / COMPILER_FILE)
    freeze = load_json(GATE0_DIR / FREEZE_FILE)
    closure = load_json(GATE0_DIR / CLOSURE_FILE)
    source_matrix = load_json(SOURCE_MATRIX)

    verify_standing_authority(authority)
    source_ids = verify_phase0_sources(source_matrix)
    verify_freeze_candidate(freeze, source_ids)
    verify_authority_inputs(freeze)
    verify_compiler_receipt(compiler)
    verify_term_registry()
    verify_term_census()
    verify_closure_matrix(closure, source_matrix)

    print("Project Coherence Gate 0 candidate verification: PASS")
    print("  Phase 0 source records: 25 (24 static hashes verified; 1 mutable authority present)")
    print("  Baseline authority groups: 9 (all 25 source records covered exactly once)")
    print("  Term census: PASS (24 starter records; 49 groups; 695 members; 14 conflicts retained)")
    print("  Conflict dispositions: 14 (compiler line-ending identity technically resolved; other actions retained)")
    print("  Gate 0 criteria: 6 (overall OPEN; candidate NOT FROZEN)")
    print("This PASS is structural and identity-focused only; it is not canon acceptance, peer review, proof verification, empirical validation, product licensing, or disclosure approval.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"Project Coherence Gate 0 candidate verification: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
