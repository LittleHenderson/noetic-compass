#!/usr/bin/env python3
"""Fail-closed structural verifier for the Project Coherence Phase 0 package."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE_DIR = REPO_ROOT / "docs" / "working" / "project_coherence"

JSON_FILES = {
    "sources": "CANONICAL_SOURCE_AUTHORITY_MATRIX_v0.1.json",
    "symbols": "SYMBOL_AND_TERMINOLOGY_REGISTRY_v0.1.json",
    "migration": "INITIAL_MIGRATION_MATRIX_v0.1.json",
    "theorem_schema": "THEOREM_RECORD.schema.json",
    "claim_schema": "CLAIM_RECORD.schema.json",
    "theorem_ledger": "THEOREM_LEDGER_v0.1.json",
    "claim_ledger": "CLAIM_LEDGER_v0.1.json",
    "quarantine": "PROVISIONAL_TRANSFER_QUARANTINE_v0.1.json",
}

REQUIRED_MARKDOWN = [
    "README.md",
    "PROJECT_COHERENCE_MASTER_CHARTER_v0.1.md",
    "MATHEMATICAL_RED_TEAM_REPORT_v0.1.md",
    "LITERATURE_AND_TRANSFER_AUDIT_v0.1.md",
    "OPEN_VS_HELD_BOUNDARY_v0.1.md",
    "CHANGELOG.md",
]

REVIEW_STATES = {"UNASSESSED", "IN_REVIEW", "REVIEWED"}
MIGRATION_DISPOSITIONS = {
    "UNASSESSED",
    "IN_REVIEW",
    "INHERITED",
    "CLARIFIED",
    "CORRECTED",
    "CONDITIONAL",
    "DOWNGRADED",
    "DEPRECATED",
    "REFUTED",
    "REPLACED",
}
PROOF_STATUSES = {
    "NOT_APPLICABLE",
    "PROOF_REQUIRED",
    "PROOF_GAP",
    "INFORMAL_PROOF_PRESENT",
    "PROVED",
    "FORMALLY_VERIFIED",
    "STANDARD_RESULT_CITED",
    "COUNTEREXAMPLE_PRESENT",
    "INDEPENDENT_REPLICATION_REQUIRED",
}
NOVELTY_STATUSES = {
    "STANDARD_RESULT",
    "STANDARD_SPECIALIZATION",
    "FRAMEWORK_COUPLING",
    "CANDIDATE_NEW_RESULT",
    "NOVELTY_UNASSESSED",
}
PRODUCT_CLAIM_STATUSES = {"LICENSED", "NOT LICENSED", "OPEN"}


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> Any:
    require(path.is_file(), f"missing JSON artifact: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def unique_ids(records: Iterable[dict[str, Any]], label: str) -> set[str]:
    values: list[str] = []
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"{label}[{index}] is not an object")
        value = record.get("id")
        require(isinstance(value, str) and value, f"{label}[{index}] has no id")
        values.append(value)
    require(len(values) == len(set(values)), f"duplicate id in {label}")
    return set(values)


def check_document_status(document: dict[str, Any], label: str) -> None:
    status = document.get("document_status")
    require(isinstance(status, str), f"{label} has no document_status")
    require("OPEN" in status, f"{label} is not OPEN")
    require("NOT FROZEN" in status, f"{label} is not explicitly NOT FROZEN")


def resolve_source_path(record: dict[str, Any]) -> Path:
    raw = record.get("path")
    require(isinstance(raw, str) and raw, f"source {record.get('id')} has no path")
    kind = record.get("path_kind")
    if kind == "repository_relative":
        return REPO_ROOT / Path(raw)
    if kind == "external_absolute":
        path = Path(raw)
        require(path.is_absolute(), f"source {record.get('id')} path is not absolute")
        return path
    raise VerificationError(f"source {record.get('id')} has unknown path_kind {kind!r}")


def verify_sources(document: dict[str, Any]) -> tuple[set[str], int]:
    check_document_status(document, "source matrix")
    records = document.get("sources")
    require(isinstance(records, list) and records, "source matrix has no sources")
    source_ids = unique_ids(records, "sources")
    verified = 0
    for record in records:
        source_id = record["id"]
        require(record.get("availability") in {"present", "unavailable"}, f"{source_id}: invalid availability")
        path = resolve_source_path(record)
        if record["availability"] == "present":
            require(path.is_file(), f"{source_id}: present source missing at {path}")
        if record.get("verify_hash"):
            expected = record.get("sha256")
            require(isinstance(expected, str) and re.fullmatch(r"[A-F0-9]{64}", expected), f"{source_id}: invalid SHA-256")
            actual = sha256_file(path)
            require(actual == expected, f"{source_id}: SHA-256 mismatch: expected {expected}, got {actual}")
            expected_bytes = record.get("bytes")
            if expected_bytes is not None:
                require(path.stat().st_size == expected_bytes, f"{source_id}: byte-size mismatch")
            verified += 1
        else:
            require(record.get("sha256") is None, f"{source_id}: unverified mutable source must not carry a frozen SHA-256")

    required_ids = {
        "SRC-SEMANTIC-AUTHORITY-REGISTRY-20260720",
        "SRC-TKS74-MASTER-TEX",
        "SRC-TKS74-FULL-BEAUTIFUL-TEXT",
        "SRC-TKS74-REVIEW-CORRECTIONS",
        "SRC-NOETOPOS-CONSERVATIVE-TEX-REGISTERED",
        "SRC-CAS77-NORMATIVE-REGISTERED",
        "SRC-PCBA-ENGINEER-20260726",
        "SRC-CAS-OHM-GUIDE-01",
        "SRC-HARNESS-16-HISTORICAL",
        "SRC-HARNESS-PRODUCTION-TODO-LIVE",
        "SRC-TEN-ADVANCES-PRIMARY",
        "SRC-ACTIVE-COMPILER-CURRENT",
    }
    require(required_ids <= source_ids, f"source matrix lacks required IDs: {sorted(required_ids - source_ids)}")
    conflicts = document.get("unresolved_conflicts")
    require(isinstance(conflicts, list), "source matrix has no unresolved_conflicts")
    unique_ids(conflicts, "unresolved_conflicts")
    require(len(conflicts) >= 14, "source matrix must retain the twelve signed-registry conflicts plus local integrity conflicts")
    return source_ids, verified


def verify_symbols(document: dict[str, Any], source_ids: set[str]) -> int:
    check_document_status(document, "symbol registry")
    entries = document.get("entries")
    require(isinstance(entries, list) and entries, "symbol registry has no entries")
    ids = unique_ids(entries, "symbol entries")
    exact_noetics = {
        "TERM-NOETIC-0": ("Idea", "All things in and outside the Mind."),
        "TERM-NOETIC-1": ("Mind", "Various degrees of awareness that processes, stores, outputs, and intakes Ideas."),
        "TERM-NOETIC-2": ("Positive", "An Idea the Mind has an affinity for and is attracted toward."),
        "TERM-NOETIC-3": ("Negative", "An Idea the Mind is adverse to and repelled by."),
        "TERM-NOETIC-4": ("Vibration", "The degree to which an Idea resonates with the Mind, its impression."),
        "TERM-NOETIC-5": ("Female", "A Mind impregnated with an Idea, the Ideas a Mind is composed of."),
        "TERM-NOETIC-6": ("Male", "An Idea impregnated with another Idea, the Ideas an Idea is composed of."),
        "TERM-NOETIC-7": ("Rhythm", "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it."),
        "TERM-NOETIC-8": ("Above/Cause", "An Idea that triggers a different Idea than itself to come to Mind."),
        "TERM-NOETIC-9": ("Below/Effect", "The Idea brought to Mind by an Above/Cause trigger."),
    }
    require(set(exact_noetics) <= ids, "symbol registry does not contain all ten canonical Noetics")
    by_id = {entry["id"]: entry for entry in entries}
    for term_id, (name, definition) in exact_noetics.items():
        require(by_id[term_id].get("canonical_name") == name, f"{term_id}: canonical name drift")
        require(by_id[term_id].get("definition") == definition, f"{term_id}: verbatim definition drift")
        require(by_id[term_id].get("migration_policy") == "PRESERVE_VERBATIM", f"{term_id}: invalid migration policy")
    for entry in entries:
        refs = entry.get("source_refs")
        require(isinstance(refs, list) and refs, f"{entry['id']}: missing source refs")
        unknown = set(refs) - source_ids
        require(not unknown, f"{entry['id']}: unknown source refs {sorted(unknown)}")
    required_distinctions = {
        "TERM-TKS-WORLD",
        "TERM-CAS-DOMAIN",
        "TERM-CAS-REGISTER",
        "TERM-TKS-F28",
        "TERM-CAS-DRIVES",
        "TERM-RPM-COMPUTATION",
        "TERM-RPM-SECTION-RETRACTION",
        "TERM-CAS-OHM-FIELD-KINDS",
    }
    require(required_distinctions <= ids, "symbol registry lacks a required typed distinction")
    return len(entries)


def verify_migration(document: dict[str, Any], source_ids: set[str]) -> int:
    check_document_status(document, "migration matrix")
    entries = document.get("entries")
    require(isinstance(entries, list) and entries, "migration matrix has no entries")
    ids = unique_ids(entries, "migration entries")
    for entry in entries:
        require(entry.get("review_state") in {"UNASSESSED", "IN_REVIEW"}, f"{entry['id']}: Phase 0 review state is too strong")
        require(entry.get("migration_disposition") in {"UNASSESSED", "IN_REVIEW"}, f"{entry['id']}: Phase 0 disposition is prematurely decided")
        require(entry.get("proof_status") in PROOF_STATUSES, f"{entry['id']}: invalid proof status")
        require(entry.get("current_admission_ring") == 4, f"{entry['id']}: initial migration item escaped Ring 4")
        refs = entry.get("source_refs")
        require(isinstance(refs, list) and refs, f"{entry['id']}: missing source refs")
        unknown = set(refs) - source_ids
        require(not unknown, f"{entry['id']}: unknown source refs {sorted(unknown)}")
    required = {
        "MIG-TKS74-BLANKET-INHERITANCE",
        "MIG-RPM-TYPE-SPLIT",
        "MIG-DETERMINISTIC-HILBERT-LIFT",
        "MIG-OCCUPATION-PROJECTOR-ERRATA",
        "MIG-SPECTRAL-MVR-ERRATA",
        "MIG-NOETOPOS-COVERAGE-REDUCTION",
        "MIG-NOETOPOS-SUBCANONICITY",
        "MIG-PROBABILISTIC-GLUING",
        "MIG-PROJECTOR-CAPACITY-BOUND",
        "MIG-CAS-OHM-MEASUREMENT-TYPES",
        "MIG-HARNESS-HISTORICAL-CURRENT",
        "MIG-COMPILER-REGISTRY-DRIFT",
    }
    require(required <= ids, f"migration matrix lacks required entries: {sorted(required - ids)}")
    return len(entries)


def enum_values(schema: dict[str, Any], property_name: str) -> set[Any]:
    properties = schema.get("properties")
    require(isinstance(properties, dict), "schema has no properties")
    prop = properties.get(property_name)
    require(isinstance(prop, dict), f"schema property {property_name} missing")
    values = prop.get("enum")
    require(isinstance(values, list), f"schema property {property_name} has no enum")
    return set(values)


def verify_schemas(theorem: dict[str, Any], claim: dict[str, Any]) -> None:
    require(theorem.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "theorem schema draft mismatch")
    require(claim.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "claim schema draft mismatch")
    require(enum_values(theorem, "migration_disposition") == MIGRATION_DISPOSITIONS, "theorem migration enum drift")
    require(enum_values(theorem, "proof_status") == PROOF_STATUSES, "theorem proof enum drift")
    require(enum_values(theorem, "novelty_status") == NOVELTY_STATUSES, "theorem novelty enum drift")
    require(enum_values(claim, "product_claim_status") == PRODUCT_CLAIM_STATUSES, "claim product-status enum drift")
    require(enum_values(claim, "review_state") == REVIEW_STATES, "claim review-state enum drift")
    require(enum_values(claim, "admission_ring") == {3, 4}, "empirical/product claims may only use Rings 3 or 4")


def verify_record_against_schema(record: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    required = schema.get("required")
    properties = schema.get("properties")
    require(isinstance(required, list) and isinstance(properties, dict), f"{label}: malformed record schema")
    missing = set(required) - set(record)
    require(not missing, f"{label}: missing required fields {sorted(missing)}")
    unexpected = set(record) - set(properties)
    require(not unexpected, f"{label}: unexpected fields {sorted(unexpected)}")
    for field, spec in properties.items():
        if field in record and isinstance(spec, dict) and isinstance(spec.get("enum"), list):
            require(record[field] in spec["enum"], f"{label}: invalid {field}={record[field]!r}")


def verify_theorem_ledger(
    document: dict[str, Any], schema: dict[str, Any], source_ids: set[str]
) -> set[str]:
    check_document_status(document, "theorem ledger")
    records = document.get("records")
    require(isinstance(records, list) and records, "theorem ledger has no records")
    theorem_ids = unique_ids(records, "theorem records")
    for record in records:
        label = record["id"]
        verify_record_against_schema(record, schema, label)
        require(record.get("review_state") in {"UNASSESSED", "IN_REVIEW"}, f"{label}: review state is premature")
        require(record.get("migration_disposition") in {"UNASSESSED", "IN_REVIEW"}, f"{label}: disposition is premature")
        require(record.get("admission_ring") == 4, f"{label}: initial theorem record escaped Ring 4")
        unknown_sources = set(record.get("source_refs", [])) - source_ids
        require(not unknown_sources, f"{label}: unknown source refs {sorted(unknown_sources)}")
    for record in records:
        unknown_dependencies = set(record.get("dependencies", [])) - theorem_ids
        require(not unknown_dependencies, f"{record['id']}: unknown theorem dependencies {sorted(unknown_dependencies)}")
    required_ids = {
        "THM-NOE-ACBE-RPM-TRIVIAL-COVERS",
        "THM-LIFT-NORM-FIBER-FORMULA",
        "THM-LIFT-OCCUPATION-COUNTEREXAMPLE",
        "THM-NOE-NONSUBCANONICAL-COUNTERMODEL",
        "THM-PROJECTOR-CAPACITY-CAS-TRANSFER",
    }
    require(required_ids <= theorem_ids, f"theorem ledger lacks required red-team records: {sorted(required_ids - theorem_ids)}")
    return theorem_ids


def verify_claim_ledger(
    document: dict[str, Any], schema: dict[str, Any], source_ids: set[str], theorem_ids: set[str]
) -> int:
    check_document_status(document, "claim ledger")
    records = document.get("records")
    require(isinstance(records, list) and records, "claim ledger has no records")
    unique_ids(records, "claim records")
    for record in records:
        label = record["id"]
        verify_record_against_schema(record, schema, label)
        require(record.get("review_state") in {"UNASSESSED", "IN_REVIEW"}, f"{label}: review state is premature")
        require(record.get("product_claim_status") == "NOT LICENSED", f"{label}: initial claim must remain NOT LICENSED")
        require(record.get("admission_ring") == 4, f"{label}: initial claim escaped Ring 4")
        require(not record.get("evidence_packets"), f"{label}: no Phase 0 evidence packet may be implied")
        unknown_sources = set(record.get("source_refs", [])) - source_ids
        require(not unknown_sources, f"{label}: unknown source refs {sorted(unknown_sources)}")
        unknown_theorems = set(record.get("theorem_refs", [])) - theorem_ids
        require(not unknown_theorems, f"{label}: unknown theorem refs {sorted(unknown_theorems)}")
    return len(records)


def verify_quarantine(document: dict[str, Any], source_ids: set[str]) -> int:
    check_document_status(document, "transfer quarantine")
    source = document.get("source")
    require(isinstance(source, dict), "quarantine has no source record")
    require(source.get("source_ref") == "SRC-TEN-ADVANCES-PRIMARY", "quarantine source ref mismatch")
    require(source.get("source_ref") in source_ids, "quarantine references an unknown source")
    require(source.get("peer_review_status") == "OPEN", "manuscript peer-review status must remain OPEN")
    items = document.get("items")
    require(isinstance(items, list) and len(items) == 10, "quarantine must contain exactly ten chapter records")
    unique_ids(items, "quarantine items")
    require({item.get("chapter") for item in items} == set(range(1, 11)), "quarantine chapters must be 1 through 10")
    for item in items:
        require(item.get("admission_ring") == 4, f"{item['id']}: transfer escaped Ring 4")
        require(item.get("admission_status") == "OPEN", f"{item['id']}: admission status must remain OPEN")
        require(item.get("product_claim_status") == "NOT LICENSED", f"{item['id']}: product claim must remain NOT LICENSED")
        require(item.get("transfer_status") == "QUARANTINED", f"{item['id']}: transfer must remain quarantined")
        require(item.get("proof_status") in PROOF_STATUSES, f"{item['id']}: invalid proof status")
        require(item.get("novelty_status") in NOVELTY_STATUSES, f"{item['id']}: invalid novelty status")
    chapter_two = next(item for item in items if item["chapter"] == 2)
    require("intertwining" in chapter_two.get("critical_gap", "").lower(), "projector capacity gap does not record the intertwining hypothesis")
    return len(items)


def verify_markdown() -> None:
    for name in REQUIRED_MARKDOWN:
        path = PHASE_DIR / name
        require(path.is_file(), f"missing Markdown artifact: {path}")
    charter = (PHASE_DIR / "PROJECT_COHERENCE_MASTER_CHARTER_v0.1.md").read_text(encoding="utf-8")
    require("Document status: `DRAFT / OPEN / NOT FROZEN`" in charter, "charter is not fail-closed")
    require("Status: `OPEN`" in charter, "Gate 0 is not OPEN")
    require("Freezing the charter is a material program decision" in charter, "charter freeze procedure is missing")
    require("UNTRUSTED_RESEARCH_INPUT" in charter, "charter does not classify the Ten Advances source")
    boundary = (PHASE_DIR / "OPEN_VS_HELD_BOUNDARY_v0.1.md").read_text(encoding="utf-8")
    require("FLAG_FOR_HUMAN_REVIEW" in boundary and "NOT LEGAL ADVICE" in boundary, "open-vs-held draft lacks its human-review boundary")


def main() -> int:
    documents = {name: load_json(PHASE_DIR / filename) for name, filename in JSON_FILES.items()}
    source_ids, verified_hashes = verify_sources(documents["sources"])
    symbol_count = verify_symbols(documents["symbols"], source_ids)
    migration_count = verify_migration(documents["migration"], source_ids)
    verify_schemas(documents["theorem_schema"], documents["claim_schema"])
    theorem_ids = verify_theorem_ledger(documents["theorem_ledger"], documents["theorem_schema"], source_ids)
    claim_count = verify_claim_ledger(documents["claim_ledger"], documents["claim_schema"], source_ids, theorem_ids)
    quarantine_count = verify_quarantine(documents["quarantine"], source_ids)
    verify_markdown()
    print("Project Coherence Phase 0 verification: PASS")
    print(f"  source records: {len(documents['sources']['sources'])} ({verified_hashes} static hashes verified)")
    print(f"  symbol records: {symbol_count}")
    print(f"  migration records: {migration_count}")
    print(f"  theorem records: {len(theorem_ids)}")
    print(f"  claim records: {claim_count} (all NOT LICENSED)")
    print(f"  quarantined manuscript chapters: {quarantine_count}")
    print("  charter state: DRAFT / OPEN / NOT FROZEN")
    print("This PASS is structural only; it is not proof, peer review, empirical validation, product acceptance, or disclosure approval.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"Project Coherence Phase 0 verification: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
