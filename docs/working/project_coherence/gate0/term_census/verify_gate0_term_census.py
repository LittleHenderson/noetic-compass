#!/usr/bin/env python3
"""Verify the bounded Gate0 load-bearing term census.

This checker validates source hashes, registry import completeness, closed-family
cardinalities, exact payload members, variant-difference labels, conflict guards,
and required coverage classes.  It does not adjudicate semantic conflicts.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CENSUS_PATH = HERE / "GATE0_LOAD_BEARING_TERM_CENSUS_v0.1.json"

ALLOWED_CLASSIFICATIONS = {
    "REGISTERED",
    "PROPOSED_ADD",
    "TYPED_VARIANT",
    "EXPLICITLY_OUT_OF_SCOPE",
}
REQUIRED_COVERAGE = {
    "notation",
    "relation_kinds",
    "algebra_profiles",
    "acquisition_variants",
    "worlds",
    "elements",
    "foundations",
    "paths",
    "dynamics",
    "evidence",
    "measurement_fields",
    "implementation_schema",
    "formal_topos",
}
REQUIRED_CONFLICT_GUARDS = {
    "CG-WORLD-DOMAIN-REGISTER",
    "CG-ELEMENT-INDEXING",
    "CG-OWNER-PAYLOADS",
    "CG-RICH-28-PROVENANCE",
    "CG-ACQUISITION-VOCABULARY",
    "CG-FOUNDATION-DRIVE",
    "CG-RPM-HOMONYMY",
    "CG-ALGEBRA-PROFILES",
    "CG-EVIDENCE-KINDS",
    "CG-NOETIC-TOPOS-CLAIM-SCOPE",
    "CG-SUBCANONICITY-STATUS",
    "CG-OMEGA-COLLISION",
    "CG-PCBA-ADDRESS",
    "CG-COMPILER-WORLDS-ALIAS",
    "CG-CAS-OHM-SCALE-UNITS",
    "CG-CAS-OHM-GAIN-NETWORK-PROFILES",
    "CG-CAS-OHM-ASOM-AXES",
    "CG-PCBA-GRAMMAR-COVERAGE",
    "CG-PCBA-CSB-SAFETY-SEMANTICS",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def resolve_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    try:
        census = load_json(CENSUS_PATH)
    except Exception as exc:  # pragma: no cover - diagnostic path
        print(f"FAIL: cannot load {CENSUS_PATH}: {exc}", file=sys.stderr)
        return 1

    check(
        census.get("schema_version") == "gate0_load_bearing_term_census.v0.1",
        "unexpected census schema_version",
    )
    check(
        "NOT CANON FREEZE" in census.get("document_status", ""),
        "document_status must preserve the not-canon-freeze boundary",
    )

    sources = census.get("source_snapshot", [])
    source_ids = [source.get("source_id") for source in sources]
    check(len(source_ids) == len(set(source_ids)), "duplicate source_snapshot IDs")
    source_by_id = {source["source_id"]: source for source in sources if source.get("source_id")}
    source_paths: dict[str, Path] = {}
    verified_hashes = 0
    for source in sources:
        source_id = source.get("source_id", "<missing>")
        for field in ("path", "sha256", "authority_status", "verify_hash"):
            check(field in source, f"{source_id}: missing source field {field}")
        if "path" not in source:
            continue
        path = resolve_path(source["path"])
        source_paths[source_id] = path
        check(path.is_file(), f"{source_id}: source file missing: {path}")
        if path.is_file() and source.get("verify_hash"):
            actual = sha256(path)
            expected = str(source.get("sha256", "")).upper()
            check(actual == expected, f"{source_id}: SHA-256 {actual} != {expected}")
            verified_hashes += 1

    registry_source = source_by_id.get("SRC-PHASE0-SYMBOL-REGISTRY")
    check(registry_source is not None, "missing Phase0 symbol-registry snapshot")
    registry = load_json(source_paths["SRC-PHASE0-SYMBOL-REGISTRY"])
    registry_entries = registry.get("entries", [])
    registry_ids = [entry.get("id") for entry in registry_entries]
    imported = census.get("imported_registry", {})
    imported_ids = imported.get("entry_ids", [])
    check(imported.get("classification") == "REGISTERED", "registry import not REGISTERED")
    check(len(registry_ids) == 24, f"starter registry has {len(registry_ids)} entries, expected 24")
    check(imported_ids == registry_ids, "registry import must match all starter entries in order")
    required_registry_metadata = {
        "semantic_type",
        "version_scope",
        "source_refs",
        "aliases_allowed",
        "forbidden_aliases",
        "migration_policy",
    }
    for entry in registry_entries:
        missing = required_registry_metadata - set(entry)
        check(not missing, f"{entry.get('id')}: missing registry metadata {sorted(missing)}")

    semantic_classes = set(census.get("semantic_classes", []))
    groups = census.get("term_groups", [])
    group_ids = [group.get("group_id") for group in groups]
    check(len(group_ids) == len(set(group_ids)), "duplicate group IDs")
    group_by_id = {group["group_id"]: group for group in groups if group.get("group_id")}
    term_ids: list[str] = []
    classification_counts = Counter()
    template_pattern = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
    required_group_fields = {
        "group_id",
        "group_label",
        "classification",
        "semantic_class",
        "version_scope",
        "source_locations",
        "source_location_templates",
        "registry_refs",
        "aliases_allowed",
        "aliases_forbidden",
        "migration_policy",
        "members",
        "notes",
    }

    def validate_locations(owner: str, locations: list[dict[str, Any]]) -> None:
        for index, location in enumerate(locations):
            source_id = location.get("source_id")
            check(source_id in source_by_id, f"{owner}: location {index} has unknown source {source_id}")
            check(bool(location.get("locator_kind")), f"{owner}: location {index} lacks locator_kind")
            check(bool(location.get("locator")), f"{owner}: location {index} lacks locator")

    for group in groups:
        group_id = group.get("group_id", "<missing>")
        missing = required_group_fields - set(group)
        check(not missing, f"{group_id}: missing group fields {sorted(missing)}")
        classification = group.get("classification")
        check(classification in ALLOWED_CLASSIFICATIONS, f"{group_id}: invalid classification")
        check(group.get("semantic_class") in semantic_classes, f"{group_id}: invalid semantic class")
        check(bool(group.get("version_scope")), f"{group_id}: empty version_scope")
        check(bool(group.get("migration_policy")), f"{group_id}: empty migration_policy")
        check(isinstance(group.get("aliases_allowed"), list), f"{group_id}: aliases_allowed not list")
        check(isinstance(group.get("aliases_forbidden"), list), f"{group_id}: aliases_forbidden not list")
        if classification == "REGISTERED":
            refs = group.get("registry_refs", [])
            check(bool(refs), f"{group_id}: REGISTERED group lacks registry_refs")
            for ref in refs:
                check(ref in registry_ids, f"{group_id}: unknown registry ref {ref}")
        locations = group.get("source_locations", [])
        templates = group.get("source_location_templates", [])
        check(bool(locations or templates), f"{group_id}: no source location")
        validate_locations(group_id, locations)
        validate_locations(group_id, templates)
        members = group.get("members", [])
        check(bool(members), f"{group_id}: empty member list")
        for member in members:
            term_id = member.get("term_id")
            check(bool(term_id), f"{group_id}: member lacks term_id")
            check(bool(member.get("term")), f"{group_id}/{term_id}: member lacks term")
            check("symbol" in member, f"{group_id}/{term_id}: member lacks symbol")
            if term_id:
                term_ids.append(term_id)
            classification_counts[classification] += 1
            for template in templates:
                for field in template_pattern.findall(template.get("locator", "")):
                    check(field in member, f"{group_id}/{term_id}: locator template needs {field}")

    duplicates = [term_id for term_id, count in Counter(term_ids).items() if count > 1]
    check(not duplicates, f"duplicate term IDs: {duplicates[:10]}")
    check(
        sum(classification_counts.values()) == len(term_ids),
        "classification count does not equal term count",
    )
    recorded_counts = census.get("completeness", {}).get("member_classification_counts", {})
    check(dict(classification_counts) == recorded_counts, "recorded classification counts are stale")
    check(
        census.get("completeness", {}).get("term_group_count") == len(groups),
        "recorded term_group_count is stale",
    )
    check(
        census.get("completeness", {}).get("enumerated_group_member_count") == len(term_ids),
        "recorded enumerated_group_member_count is stale",
    )

    for group_id, expected in census.get("expected_closed_family_counts", {}).items():
        check(group_id in group_by_id, f"expected-count group absent: {group_id}")
        if group_id in group_by_id:
            actual = len(group_by_id[group_id].get("members", []))
            check(actual == expected, f"{group_id}: {actual} members != {expected}")

    coverage = census.get("coverage_map", [])
    coverage_classes = {entry.get("coverage_class") for entry in coverage}
    check(coverage_classes == REQUIRED_COVERAGE, "coverage classes differ from required bounded set")
    mapped_groups: set[str] = set()
    for entry in coverage:
        for group_id in entry.get("group_ids", []):
            check(group_id in group_by_id, f"coverage map references unknown group {group_id}")
            mapped_groups.add(group_id)
    nonexcluded = {
        group["group_id"]
        for group in groups
        if group.get("classification") != "EXPLICITLY_OUT_OF_SCOPE"
    }
    check(not (nonexcluded - mapped_groups), f"unmapped admitted groups: {sorted(nonexcluded - mapped_groups)}")

    guard_ids = {guard.get("guard_id") for guard in census.get("conflict_guards", [])}
    check(guard_ids == REQUIRED_CONFLICT_GUARDS, "conflict-guard set is incomplete or unexpected")
    check(
        census.get("completeness", {}).get("conflict_guard_count") == len(guard_ids),
        "recorded conflict_guard_count is stale",
    )
    for guard in census.get("conflict_guards", []):
        check(guard.get("status") == "OPEN_PRESERVED", f"{guard.get('guard_id')}: status not OPEN_PRESERVED")
        check(bool(guard.get("forbidden_collapse")), f"{guard.get('guard_id')}: missing collapse guard")
        check(bool(guard.get("required_future_action")), f"{guard.get('guard_id')}: missing future action")
        validate_locations(guard.get("guard_id", "<guard>"), guard.get("source_locations", []))

    # Closed source families: exact member identities and variant-difference labels.
    raw_owner = load_json(source_paths["owner_raw_40_28_workspace"])
    deployed_owner = load_json(source_paths["SRC-TKS-OWNER-LOCK-20260603"])
    owner40 = group_by_id["G-TKS-ELEMENTS-OWNER-VARIANTS"]["members"]
    check(len(raw_owner["tks_40_elements"]) == len(deployed_owner["tks_40_elements"]) == 40, "owner Element payload count")
    for member in owner40:
        raw = raw_owner["tks_40_elements"][member["workspace_index"]]
        deployed = deployed_owner["tks_40_elements"][member["deployed_index"]]
        check(raw.get("code") == deployed.get("code") == member["symbol"], f"{member['term_id']}: owner Element code mismatch")
        relation = "IDENTICAL" if raw.get("definition") == deployed.get("definition") else "DIFFERS"
        check(relation == member.get("definition_relation"), f"{member['term_id']}: wrong definition_relation")
    actual_element_diffs = {m["symbol"] for m in owner40 if m["definition_relation"] == "DIFFERS"}
    check(len(actual_element_diffs) == 20, f"owner Element difference count {len(actual_element_diffs)} != 20")

    owner28 = group_by_id["G-TKS-F28-OWNER-VARIANTS"]["members"]
    check(len(raw_owner["tks_28_foundations"]) == len(deployed_owner["tks_28_foundations"]) == 28, "owner Foundation payload count")
    for member in owner28:
        raw = raw_owner["tks_28_foundations"][member["workspace_index"]]
        deployed = deployed_owner["tks_28_foundations"][member["deployed_index"]]
        check(raw.get("code") == deployed.get("code") == member["symbol"], f"{member['term_id']}: owner Foundation code mismatch")
        relation = "IDENTICAL" if raw.get("definition") == deployed.get("definition") else "DIFFERS"
        check(relation == member.get("definition_relation"), f"{member['term_id']}: wrong definition_relation")
    actual_foundation_diffs = {m["symbol"] for m in owner28 if m["definition_relation"] == "DIFFERS"}
    check(len(actual_foundation_diffs) == 8, f"owner Foundation difference count {len(actual_foundation_diffs)} != 8")

    normalized_elements = load_json(source_paths["normalized_elements_40"])
    census_elements = group_by_id["G-TKS-ELEMENTS-NORMALIZED"]["members"]
    check(len(normalized_elements) == len(census_elements) == 40, "normalized Element count")
    for member in census_elements:
        source = normalized_elements[member["source_index"]]
        check(source.get("symbol") == member["symbol"], f"{member['term_id']}: normalized symbol mismatch")
        check(source.get("name") == member["term"], f"{member['term_id']}: normalized name mismatch")

    normalized_rich = load_json(source_paths["normalized_subfoundations_28_defs"])
    census_rich = group_by_id["G-TKS-F28-RICH-NORMALIZED"]["members"]
    check(len(normalized_rich) == len(census_rich) == 28, "rich 28 count")
    for member in census_rich:
        source = normalized_rich[member["source_index"]]
        check(source.get("id") == member["symbol"], f"{member['term_id']}: rich-28 ID mismatch")
        check(source.get("name") == member["term"], f"{member['term_id']}: rich-28 name mismatch")

    normalized_acq = load_json(source_paths["normalized_acquisitions_22"])
    census_acq = group_by_id["G-TKS-ACQUISITIONS-NORMALIZED"]["members"]
    check(len(normalized_acq) == len(census_acq) == 22, "normalized Acquisition count")
    for member in census_acq:
        source = normalized_acq[member["source_index"]]
        check(source.get("id") == member["symbol"], f"{member['term_id']}: Acquisition ID mismatch")
        check(source.get("name") == member["term"], f"{member['term_id']}: Acquisition name mismatch")
        check(source.get("type") == member["acquisition_type"], f"{member['term_id']}: Acquisition type mismatch")
    v74_acq_symbols = {m["symbol"] for m in group_by_id["G-TKS-ACQUISITIONS-V74"]["members"]}
    expected_v74 = {"A0"} | {f"{prefix}{index}" for prefix in "DWP" for index in range(1, 8)}
    check(v74_acq_symbols == expected_v74, "v7.4 Acquisition family is incomplete")

    expected_asom = {
        "A": ("ASOM-ALIGNED", "ASOM Aligned region"),
        "S": ("ASOM-STARVED", "ASOM Starved region"),
        "O": ("ASOM-OVERSATURATED", "ASOM Oversaturated region"),
        "M": ("ASOM-MISALIGNED", "ASOM Misaligned region"),
    }
    actual_asom = {
        member["symbol"]: (member["term_id"], member["term"])
        for member in group_by_id["G-CAS-OHM-TYPED-CROSSWALKS"]["members"]
        if member["symbol"] in expected_asom
    }
    check(
        actual_asom == expected_asom,
        "CAS-Ohm ASOM expansion differs from the guide/addendum definitions",
    )

    cjtq_members = group_by_id["G-CJTQ-RECORD-SCHEMA"]["members"]
    check(
        [member.get("field_index") for member in cjtq_members]
        == list(range(len(cjtq_members))),
        "CJT-Q field indices are not contiguous and ordered",
    )
    required_cjtq_fields = {
        "R_resource",
        "R_known",
        "R_hidden",
        "I_raw",
        "I_FS",
        "lambda",
        "relative_error",
        "uncertainty",
        "sample_size",
        "raw_artifact_refs",
        "field_lineage",
        "field_measurement_status",
        "unit_profile",
        "ifs_method",
        "semantic_outcome",
        "missing_or_censored_reason",
        "calibration_profile_sha256",
    }
    actual_cjtq_fields = {member.get("symbol") for member in cjtq_members}
    check(
        required_cjtq_fields <= actual_cjtq_fields,
        "CJT-Q schema omits audited measurement, lineage, unit, or censoring fields",
    )

    normalized_index = load_json(source_paths["normalized_canon_index"])
    check("canon_subfoundations_28_defs.json" not in normalized_index.get("files", []), "rich 28 unexpectedly indexed; census status needs review")
    check("canon_elements_40.json" in normalized_index.get("files", []), "elements file absent from normalized index")
    check("canon_acquisitions_22.json" in normalized_index.get("files", []), "acquisitions file absent from normalized index")

    authority_registry = load_json(source_paths["SRC-SEMANTIC-AUTHORITY-REGISTRY-20260720"])
    census_bindings = [m["symbol"] for m in group_by_id["G-REQUIRED-RUN-BINDINGS"]["members"]]
    check(census_bindings == authority_registry.get("required_run_bindings"), "run-binding census differs from owner registry")

    compiler_path = source_paths["SRC-ACTIVE-COMPILER-CURRENT"]
    compiler_text = compiler_path.read_text(encoding="utf-8")
    check('"Worlds": "Domains"' in compiler_text, "compiler Worlds alias no longer present; census conflict needs review")
    canonical_lf = compiler_path.read_bytes().replace(b"\r\n", b"\n")
    canonical_lf_sha = hashlib.sha256(canonical_lf).hexdigest().upper()
    registry_compiler = next(
        source for source in authority_registry.get("sources", [])
        if source.get("id") == "active_python_notation_compiler"
    )
    check(
        canonical_lf_sha == str(registry_compiler.get("sha256", "")).upper(),
        "compiler LF-normalized hash differs from owner registry",
    )
    forbidden_alias_group = group_by_id["G-COMPILER-WORLDS-ALIAS-CONFLICT"]
    check(
        "Worlds\u2192Domains" in forbidden_alias_group.get("aliases_forbidden", []),
        "compiler Worlds alias is not explicitly forbidden",
    )

    check(
        {"TERM-RPM-COMPUTATION", "TERM-RPM-SECTION-RETRACTION"} <= set(imported_ids),
        "the two RPM registry identities are not both imported",
    )
    check(
        "\u03a9_noe subobject classifier" in group_by_id["G-CAS-PRODUCTION-SEMANTICS"].get("aliases_forbidden", []),
        "production Î© collision guard missing",
    )

    if failures:
        print(f"FAIL Gate0 term census ({len(failures)} issue(s)):", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1

    print(
        "PASS Gate0 term census: "
        f"{len(imported_ids)} starter entries; {len(groups)} groups; {len(term_ids)} members; "
        f"{len(sources)} source hashes; {len(guard_ids)} preserved conflicts; "
        f"{len(coverage_classes)} coverage classes; "
        f"owner diffs 40={len(actual_element_diffs)}, 28={len(actual_foundation_diffs)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
