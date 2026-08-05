#!/usr/bin/env python3
"""Verify Noetic Topos 2.0 Gate 1 research artifacts."""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = (
    ROOT / "docs" / "working" / "project_coherence" / "gate1" / "noetic_topos2"
)
THEOREM_SCHEMA_PATH = (
    ROOT / "docs" / "working" / "project_coherence" / "THEOREM_RECORD.schema.json"
)
MODALITY_DIR = ARTIFACT_DIR / "modality_composition"
MODALITY_VERIFIER = MODALITY_DIR / "verify_modality_composition.py"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.noetic_topos2.finite_site import check_reference_model  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def resolve_source(source: dict[str, Any]) -> tuple[Path, str]:
    locator = source.get("portable_locator")
    require(isinstance(locator, dict), "source lacks a portable locator")
    kind = locator.get("kind")
    if kind == "REPOSITORY_PATH":
        path = (ROOT / locator["path"]).resolve()
        require(path.is_relative_to(ROOT.resolve()), "repository source escapes the root")
        return path, "repository"
    require(kind == "CONFIGURABLE_BASELINE_ROOT", f"unknown source locator: {kind}")
    configured_root = os.environ.get(locator["environment_variable"])
    if configured_root:
        return (Path(configured_root) / locator["relative_path"]).resolve(), "configured"
    bundle_path = locator.get("content_addressed_bundle_path")
    if bundle_path:
        return (ROOT / bundle_path).resolve(), "bundle"
    require(locator.get("bundle_status") == "OPEN", "missing bundle was not kept OPEN")
    return Path(source["local_provenance_path"]), "local-only"


SUPPORTED_SCHEMA_KEYS = {
    "$schema",
    "$id",
    "title",
    "type",
    "additionalProperties",
    "required",
    "properties",
    "allOf",
    "if",
    "then",
    "enum",
    "const",
    "pattern",
    "minLength",
    "minItems",
    "items",
    "format",
}


def require_supported_schema(schema: dict[str, Any], path: str = "$schema") -> None:
    """Fail closed if the canonical schema uses a keyword this verifier ignores."""

    unknown = set(schema) - SUPPORTED_SCHEMA_KEYS
    require(not unknown, f"unsupported theorem-schema keyword(s) at {path}: {sorted(unknown)}")
    for name, child in schema.get("properties", {}).items():
        require_supported_schema(child, f"{path}.properties.{name}")
    if isinstance(schema.get("items"), dict):
        require_supported_schema(schema["items"], f"{path}.items")
    for keyword in ("allOf",):
        for index, child in enumerate(schema.get(keyword, [])):
            require_supported_schema(child, f"{path}.{keyword}[{index}]")
    for keyword in ("if", "then"):
        if isinstance(schema.get(keyword), dict):
            require_supported_schema(schema[keyword], f"{path}.{keyword}")


def instance_has_type(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    raise AssertionError(f"unsupported JSON-schema type: {expected}")


def schema_errors(instance: Any, schema: dict[str, Any], path: str = "$record") -> list[str]:
    """Validate the subset used by THEOREM_RECORD.schema.json without dependencies."""

    errors: list[str] = []
    declared_types = schema.get("type")
    if declared_types is not None:
        expected_types = declared_types if isinstance(declared_types, list) else [declared_types]
        if not any(instance_has_type(instance, item) for item in expected_types):
            return [f"{path}: expected type {expected_types}, got {type(instance).__name__}"]

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not in {schema['enum']!r}")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than minLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: string does not match {schema['pattern']!r}")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(instance.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{path}: invalid date-time")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: array is shorter than minItems")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(schema_errors(item, item_schema, f"{path}[{index}]"))

    if isinstance(instance, dict):
        required = set(schema.get("required", []))
        for key in sorted(required - set(instance)):
            errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in sorted(set(instance) - set(properties)):
                errors.append(f"{path}: unexpected property {key!r}")
        for key, child_schema in properties.items():
            if key in instance:
                errors.extend(schema_errors(instance[key], child_schema, f"{path}.{key}"))

    for clause in schema.get("allOf", []):
        condition = clause.get("if")
        if condition is None or not schema_errors(instance, condition, path):
            if isinstance(clause.get("then"), dict):
                errors.extend(schema_errors(instance, clause["then"], path))
    return errors


OBLIGATION_RECORD_KEYS = {
    "id",
    "version",
    "title",
    "obligation_kind",
    "statement",
    "source_refs",
    "object_types",
    "assumptions",
    "dependencies",
    "review_state",
    "resolution_status",
    "admission_ring",
    "acceptance_criteria",
    "evidence_artifacts",
    "claim_boundary",
    "reviewers",
}


def validate_obligation_record(record: dict[str, Any], index: int) -> None:
    path = f"obligation[{index}]"
    require(set(record) == OBLIGATION_RECORD_KEYS, f"{path} keys are not fail-closed")
    require(
        re.fullmatch(r"OBL-[A-Z0-9][A-Z0-9._-]*", record["id"]) is not None,
        f"{path} has invalid obligation ID",
    )
    for key in ("version", "title", "obligation_kind", "statement", "claim_boundary"):
        require(isinstance(record[key], str) and record[key], f"{path}.{key} is empty")
    for key in (
        "source_refs",
        "object_types",
        "assumptions",
        "dependencies",
        "acceptance_criteria",
        "evidence_artifacts",
        "reviewers",
    ):
        require(isinstance(record[key], list), f"{path}.{key} is not an array")
        require(
            all(isinstance(value, str) and value for value in record[key]),
            f"{path}.{key} contains a non-string or empty value",
        )
    require(record["source_refs"], f"{path} has no source reference")
    require(record["acceptance_criteria"], f"{path} has no acceptance criteria")
    require(record["review_state"] in {"IN_REVIEW", "UNASSESSED"}, f"{path} review state")
    require(record["resolution_status"] == "OPEN", f"{path} is not OPEN")
    require(record["admission_ring"] == 4, f"{path} escaped Ring 4")


def main() -> int:
    theorem_path = ARTIFACT_DIR / "NOETIC_TOPOS_2_THEOREMS_v0.1.json"
    obligation_path = ARTIFACT_DIR / "NOETIC_TOPOS_2_PROOF_OBLIGATIONS_v0.1.json"
    certificate_path = ARTIFACT_DIR / "FINITE_MODEL_CERTIFICATE_v0.1.json"
    source_path = ARTIFACT_DIR / "SOURCE_VERIFICATION_v0.1.json"
    spec_path = ARTIFACT_DIR / "NOETIC_TOPOS_2_SPEC_v0.1.md"
    for path in (
        theorem_path,
        obligation_path,
        certificate_path,
        source_path,
        spec_path,
        THEOREM_SCHEMA_PATH,
        MODALITY_DIR / "MODALITY_COMPOSITION_PROOF_v0.1.md",
        MODALITY_DIR / "MODALITY_COMPOSITION_CERTIFICATE_v0.1.json",
        MODALITY_VERIFIER,
    ):
        require(path.is_file(), f"missing artifact: {path}")

    theorem_ledger = json.loads(theorem_path.read_text(encoding="utf-8"))
    obligation_ledger = json.loads(obligation_path.read_text(encoding="utf-8"))
    theorem_schema = json.loads(THEOREM_SCHEMA_PATH.read_text(encoding="utf-8"))
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    source_record = json.loads(source_path.read_text(encoding="utf-8"))
    model = check_reference_model()

    require(model["all_required_checks_pass"] is True, "finite model check failed")
    require(
        model["singleton_unmarked_families_coincide"] is True
        and model["singleton_marked_covers_distinct"] is True,
        "mark identity is not preserved when bare pullback families coincide",
    )
    require(
        model["marked_cover_roundtrip_stable"] is True
        and model["marked_pullbacks_bind_parent_provenance"] is True
        and model["marked_pullbacks_preserve_topology_family"] is True,
        "marked-cover serialization or pullback provenance failed",
    )
    require(
        model["joint_refinement_is_four_singletons"] is True
        and model["joint_refinement_retains_both_parent_digests"] is True
        and model["marked_derived_records_resolve"] is True,
        "ACBE/RPM join lost its two-parent derivation",
    )
    require(certificate["expected_result"] == model, "certificate/model mismatch")
    resolution_modes: list[str] = []
    for source in source_record["sources"]:
        source_file, resolution_mode = resolve_source(source)
        resolution_modes.append(resolution_mode)
        require(source_file.is_file(), f"missing governing source: {source_file}")
        payload = source_file.read_bytes()
        require(
            hashlib.sha256(payload).hexdigest().upper() == source["sha256_raw"],
            f"raw source hash drift: {source_file}",
        )
        if "sha256_lf_normalized" in source:
            normalized = payload.replace(b"\r\n", b"\n")
            require(
                hashlib.sha256(normalized).hexdigest().upper()
                == source["sha256_lf_normalized"],
                f"normalized source hash drift: {source_file}",
            )
    require(
        theorem_ledger["document_status"]
        == "DRAFT / GATE 1 RESEARCH CANDIDATE / NOT LICENSED",
        "unsafe theorem-ledger status",
    )
    require(
        set(theorem_ledger)
        == {"schema_version", "record_schema", "document_status", "as_of", "records"},
        "theorem-ledger envelope drift",
    )
    require(
        (ARTIFACT_DIR / theorem_ledger["record_schema"]).resolve()
        == THEOREM_SCHEMA_PATH.resolve(),
        "theorem ledger does not bind the canonical theorem-record schema",
    )
    require_supported_schema(theorem_schema)
    records = theorem_ledger["records"]
    require(len(records) >= 6, "too few theorem records")
    for index, record in enumerate(records):
        errors = schema_errors(record, theorem_schema, f"theorem[{index}]")
        require(not errors, "theorem schema failure:\n  " + "\n  ".join(errors))
    ids = [record["id"] for record in records]
    require(len(ids) == len(set(ids)), "duplicate theorem IDs")
    require(all(item.startswith("THM-") for item in ids), "non-theorem record in theorem ledger")
    require(
        all(record["admission_ring"] == 4 for record in records),
        "a Gate 1 theorem escaped Ring 4",
    )
    require(
        all(record["review_state"] != "REVIEWED" for record in records),
        "internal finite checks were mislabeled as completed review",
    )
    require(
        any(record["proof_status"] == "PROOF_REQUIRED" for record in records),
        "open proof obligations are not visible",
    )
    modality_record = next(
        record for record in records if record["id"] == "THM-NT2-MODALITY-COMPOSITION"
    )
    require(
        modality_record["statement_kind"] == "THEOREM"
        and modality_record["proof_status"] == "INFORMAL_PROOF_PRESENT"
        and modality_record["review_state"] == "IN_REVIEW"
        and "PSh(L,Set)" in modality_record["claim_boundary"],
        "finite-context modality result is missing or over-scoped",
    )
    poisoned = dict(records[0])
    poisoned["product_claim_status"] = "NOT LICENSED"
    require(
        schema_errors(poisoned, theorem_schema),
        "theorem schema did not reject a forbidden additional property",
    )
    missing_required = dict(records[0])
    missing_required.pop("version")
    require(
        schema_errors(missing_required, theorem_schema),
        "theorem schema did not reject a missing required property",
    )

    require(
        set(obligation_ledger) == {"schema_version", "document_status", "as_of", "records"},
        "proof-obligation ledger envelope drift",
    )
    require(
        obligation_ledger["document_status"]
        == "DRAFT / GATE 1 RESEARCH CANDIDATE / NOT LICENSED",
        "unsafe proof-obligation-ledger status",
    )
    obligations = obligation_ledger["records"]
    require(obligations, "proof-obligation ledger is empty")
    for index, record in enumerate(obligations):
        validate_obligation_record(record, index)
    obligation_ids = [record["id"] for record in obligations]
    require(len(obligation_ids) == len(set(obligation_ids)), "duplicate obligation IDs")
    require(not set(ids) & set(obligation_ids), "theorem/obligation ID collision")
    spec_text = spec_path.read_text(encoding="utf-8")
    require("E_amb = PSh(C x L)" in spec_text, "ambient modal topos is not explicit")
    require("E_res = Sh(C x L, J_res)" in spec_text, "resolved subtopos is not explicit")
    require(
        "NoeTop_2 := E_amb" in spec_text
        and "NoeSystem_2 =" in spec_text
        and "not itself a topos or category" in spec_text,
        "underlying topos and structured research package are conflated",
    )
    require(
        "restrict to identity" in spec_text,
        "modalities are misleadingly described as nontrivial on the resolved subtopos",
    )
    require(
        any(record["id"] == "THM-NT2-RESOLVED-MODALITIES-IDENTITY" for record in records),
        "resolved-modality identity theorem record is missing",
    )
    require(
        any(
            record["id"] == "OBL-NT2-CROSS-CONTEXT-SEMANTICS"
            for record in obligations
        ),
        "the four-independent-channel expressivity boundary is missing",
    )
    require(
        "four independent legacy channels" in spec_text
        and "not yet a substantively rich" in spec_text,
        "the discrete resolved-product limitation is not explicit",
    )
    require(
        "parent-cover digests" in spec_text and "canonical JSON" in spec_text,
        "provenance-bearing marked-cover contract is not explicit",
    )
    require(
        "Deserialization of a derived record requires a parent" in spec_text
        and "complete acyclic parent" in spec_text,
        "derived cover records are not required to resolve their provenance DAG",
    )
    require(
        "Typed observational covers" in spec_text
        and "remain `OPEN`" in spec_text,
        "v0.1 overclaims observational/product-site provenance support",
    )
    require(
        "natural isomorphism" in spec_text
        and "bit-for-bit serialization" in spec_text,
        "categorical and strict serialization round trips are conflated",
    )

    modality_run = subprocess.run(
        [sys.executable, str(MODALITY_VERIFIER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    modality_output = modality_run.stdout + modality_run.stderr
    require(
        modality_run.returncode == 0
        and "MODALITY_COMPOSITION_VERIFICATION: PASS" in modality_output
        and "product-site lift remains OPEN" in modality_output,
        f"finite-context modality verification failed:\n{modality_output}",
    )

    print("Noetic Topos 2.0 Gate 1 verification passed")
    print(f"  contexts checked: {model['context_count']}")
    print(f"  theorem records: {len(records)}")
    print(f"  proof-obligation records: {len(obligations)} (all OPEN)")
    print(f"  governing sources verified: {len(source_record['sources'])}")
    print(f"  source resolution modes: {', '.join(resolution_modes)}")
    print("  ACBE/RPM witnesses: distinct and non-identity on the ambient topos")
    print("  marked covers: strict JSON, parent-bound pullbacks, two-parent join")
    print("  resolved-product limitation: explicit and OPEN")
    print("  finite-context modality composition: internal proof + exhaustive PASS")
    print("  theorem schema: exact / additionalProperties false")
    print("  all records: Ring 4 / document NOT LICENSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"Noetic Topos 2.0 Gate 1 verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
