"""Reproduce the bounded offline CAS-Ohm atlas and executable evidence.

No browser, training job, circuit runtime, or network service is started.
Run from a fresh Python process; verification.json records only checks performed
here, not pytest results, a browser audit, or general atlas acceptance.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOME = next((p for p in reversed(PROJECT_ROOT.parents)
             if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"), PROJECT_ROOT)
DEFAULT_OUT = PROJECT_ROOT / "records/rpa_ohm_atlas_20260922/demo"
ATLAS_PDF_SHA256 = "e1acd28bbdc91e5b33e1f29f2610e75b80960dc55b6907b1dc34311a3a6386ab"
MAX_SOURCE_BYTES = 2 * 1024 * 1024
FILENAMES = ("declaration.json", "atlas.json", "atlas.html", "verification.json", "hashes.json")


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _within_home(path):
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    candidate = candidate.resolve()
    _check(candidate.is_relative_to(HOME.resolve()), "output must remain inside the CNCM homebase")
    return candidate


def _json(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def _bounded_read(path, maximum=MAX_SOURCE_BYTES):
    with path.open("rb") as stream:
        body = stream.read(maximum + 1)
    _check(len(body) <= maximum, "source exceeds byte budget: " + str(path))
    return body


def _sources():
    relative = (
        "cncm/canonical.py", "cncm/model.py", "cncm/rpa_model.py", "cncm/rpa_coordinates.py",
        "cncm/rpa_ohm_atlas.py", "tools/render_rpa_view.py",
        "tools/render_rpa_ohm_view.py", "tools/reproduce_rpa_ohm_atlas.py",
        "research/helm_cas_expression_lab/cas_ohm_connections.py",
        "research/helm_cas_expression_lab/pcba_reader.py",
        "research/helm_cas_expression_lab/pcba_component_adapter.py",
        "research/helm_cas_expression_lab/pcba_check.py",
        "research/helm_cas_expression_lab/pinned_sources/compiler_pre_ohm_61ed5a45.py",
        "docs/CAS_RPA_MATHEMATICAL_REVIEW.md",
        "records/rpa_001/source_identity.json",
    )
    paths = {name: PROJECT_ROOT / name for name in relative}
    compiler_root = PROJECT_ROOT.parents[1] / "noetic-compass-scaffold/noetic-compass/api/notation"
    for name in ("compiler.py", "cas_ohm.py"):
        paths["repository/noetic-compass-scaffold/noetic-compass/api/notation/" + name] = compiler_root / name
    pages = PROJECT_ROOT / "records/rpa_ohm_atlas_20260922/source_pages"
    for page in (6, 7, 20, 21, 22):
        for extension in ("txt", "png"):
            name = "atlas_page_" + str(page) + "." + extension
            paths["records/rpa_ohm_atlas_20260922/source_pages/" + name] = pages / name
    return {name: {"bytes": len(body), "sha256_raw": sha256(body).hexdigest()}
            for name, path in sorted(paths.items()) for body in [_bounded_read(path)]}


def reproduce(out):
    """Build, verify, then write five bounded artifacts under the homebase."""
    target = _within_home(out)
    _check(not target.exists() or target.is_dir(), "output must be a directory")
    destinations = {name: target / name for name in FILENAMES}
    for path in destinations.values():
        _check(not path.is_symlink(), "artifact destination must not be a symlink")
        _within_home(path)
    before_sources = _sources()
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from cncm.canonical import canonical_json, digest
    from cncm import rpa_coordinates as coordinates
    from cncm import rpa_ohm_atlas as atlas_api
    from tools.render_rpa_view import render_rpa_view

    declaration = atlas_api.demo_declaration()
    labels = {
        "project": "CAS-Ohm design atlas",
        "board-r4": "Board · saved R=4 design",
        "stage-r4": "Stage · saved R=4 design",
        "resistor-r4": "Resistor · R=4",
        "calculation-r4": "Flow calculation · 12 / 4 = 3",
        "board-r6": "Board · hypothetical R=6",
        "stage-r6": "Stage · hypothetical R=6",
        "resistor-r6": "Resistor · R=6 alternative",
        "calculation-r6": "Flow calculation · 12 / 6 = 2",
        "note-unprofiled": "Note · no profile assigned",
    }
    for item in declaration["items"]:
        item["label"] = labels[item["node_id"]]
    document = atlas_api.build_ohm_atlas(declaration)
    canonical_before = canonical_json(document)
    _check(atlas_api.load_ohm_atlas(canonical_before) == document, "wire round-trip failed")
    atlas = atlas_api.validate_ohm_atlas(document)
    payload = atlas_api.view_payload(document)
    profiles = document["profiles"]
    reference = tuple(profiles["project"]["values"])
    alternative = tuple(profiles["board-r6"]["values"])
    zero = coordinates.centered_coordinates(reference, reference,
        profile_order=coordinates.CANONICAL_ORDER, reference_order=coordinates.CANONICAL_ORDER)
    _check(zero == (0.0,) * 39, "declared present does not map to the origin")
    z = coordinates.centered_coordinates(alternative, reference,
        profile_order=coordinates.CANONICAL_ORDER, reference_order=coordinates.CANONICAL_ORDER)
    recovered = coordinates.recover_profile(z, reference,
        reference_order=coordinates.CANONICAL_ORDER, output_order=coordinates.CANONICAL_ORDER)
    expected = tuple(float(value) for value in coordinates.validate_profile(alternative))
    relative_tolerance = coordinates.ROUND_TRIP_REL_TOL
    _check(all(math.isclose(a, b, rel_tol=relative_tolerance, abs_tol=coordinates.ROUND_TRIP_ABS_TOL)
               for a, b in zip(expected, recovered)), "coordinate inverse exceeded tolerance")
    reverse = coordinates.centered_coordinates(reference, alternative,
        profile_order=coordinates.CANONICAL_ORDER, reference_order=coordinates.CANONICAL_ORDER)
    _check(all(math.isclose(a, -b, rel_tol=0.0, abs_tol=coordinates.COORDINATE_ABS_TOL)
               for a, b in zip(z, reverse)), "reference change identity failed")
    alternate_order = coordinates.reorder_profile(alternative,
        source_order=coordinates.CANONICAL_ORDER, target_order=coordinates.DOMAIN_MAJOR_ORDER)
    _check(coordinates.reorder_profile(alternate_order, source_order=coordinates.DOMAIN_MAJOR_ORDER,
                                      target_order=coordinates.CANONICAL_ORDER) == alternative,
           "declared profile order round-trip failed")

    addresses = {}
    for node in atlas.nodes:
        address = atlas_api.exact_address(document, node.node_id)
        uri = atlas_api.address_text(address)
        _check(atlas_api.resolve_address(document, uri) == node, "address lookup failed: " + node.node_id)
        addresses[node.node_id] = {"address": address, "uri": uri}
    _check(addresses["resistor-r4"] != addresses["resistor-r6"], "saved versions collapsed")
    _check(profiles["board-r4"]["values"] == profiles["calculation-r4"]["values"] and
           addresses["board-r4"] != addresses["calculation-r4"], "equal profiles merged item identity")
    cursor = atlas_api.start_navigation(document)
    steps = [{"action": "start", "cursor": cursor}]
    for node_id in ("board-r4", "stage-r4", "resistor-r4"):
        cursor = atlas_api.enter_node(document, cursor, node_id)
        steps.append({"action": "enter", "node_id": node_id, "cursor": cursor})
    cursor = atlas_api.inspect_node(document, cursor, "calculation-r4")
    nested = atlas_api.navigation_view(document, cursor)
    _check(nested["breadcrumb"] == ["project", "board-r4", "stage-r4", "resistor-r4"],
           "nested breadcrumb differs from declared containment")
    steps.append({"action": "inspect", "node_id": "calculation-r4", "cursor": cursor})
    cursor = atlas_api.select_reference(document, cursor, "board-r6")
    ref_changed = atlas_api.navigation_view(document, cursor)
    steps.append({"action": "change_reference", "node_id": "board-r6", "cursor": cursor})
    _check(ref_changed["current_state_id"] == "project" and ref_changed["focus_node_id"] == "calculation-r4",
           "reference selection changed present or focus")
    _check(ref_changed["inspection"]["coordinate_report"]["round_trip"]["status"] == "WITHIN_DECLARED_TOLERANCE",
           "reference change inverse failed")
    cursor = atlas_api.inspect_node(document, cursor, "calculation-r6")
    steps.append({"action": "inspect_hypothetical_alternative", "node_id": "calculation-r6", "cursor": cursor})
    cursor = atlas_api.return_to(document, cursor, 0)
    steps.append({"action": "return_to_project", "cursor": cursor})
    _check(cursor["path"] == ["project"] and cursor["reference_node_id"] == "board-r6",
           "breadcrumb return changed the reference")
    _check(canonical_json(document) == canonical_before, "navigation mutated saved source")
    _check(payload["nodes"]["note-unprofiled"]["coordinate_report"]["status"] == "NOT_ASSIGNED",
           "unassigned profile was fabricated")

    results = {}
    for receipt in document["receipts"]:
        quantity = receipt["pcba"]["quantity_report"]
        expected_value = {"case-r4": "3", "case-r6": "2"}[receipt["case_id"]]
        _check(quantity["value"] == expected_value, "unexpected real compiler flow")
        _check(receipt["compiler"]["target"]["quantity_report"] == quantity,
               "PCBA/compiler result mismatch")
        _check(receipt["projection"]["nodes"][0]["quantity_report"] == quantity,
               "replayed projection result mismatch")
        results[receipt["case_id"]] = {
            "drive_literal": "12", "resistance_literal": receipt["pcba"]["resistance_literal"],
            "result": quantity["value"], "exact_value": quantity["exact_value"],
            "quantity_record_sha256": quantity["record_sha256"],
            "receipt_sha256": receipt["receipt_sha256"],
            "compiler_expression": receipt["compiler"]["observation"]["expression"],
            "implementation_sha256_lf": receipt["pcba"]["implementation_sha256_lf"],
            "measurement_status": quantity["measurement_status"],
        }

    page = render_rpa_view(document)
    _check("connect-src 'none'" in page and 'id="snapshot-data"' in page,
           "rendered artifact lacks offline data/CSP boundary")
    _check(canonical_json(document) == canonical_before, "renderer mutated saved source")
    _check(_sources() == before_sources, "implementation/source-page files changed during reproduction")
    identity = json.loads((PROJECT_ROOT / "records/rpa_001/source_identity.json").read_text(encoding="utf-8"))
    _check(any(row.get("sha256") == ATLAS_PDF_SHA256 for row in identity),
           "historical atlas PDF identity does not match the coordinate source")
    verification = {
        "schema_version": "cas.rpa.ohm-atlas-reproduction/0.1",
        "status": "PASS_EXECUTED_DETERMINISTIC_CHECKS",
        "document_sha256": document["document_sha256"],
        "checks": {
            "wire_decode_and_all_record_replay": True,
            "declared_present_maps_to_zero": True,
            "inverse_uses_actual_reference_and_round_trips": True,
            "reference_change_identity": True,
            "named_profile_order_permutation_round_trips": True,
            "all_exact_addresses_resolve": True,
            "same_profile_does_not_merge_identity": True,
            "saved_versions_remain_separate": True,
            "nested_containment_and_breadcrumb_return": True,
            "focus_and_reference_leave_present_and_source_unchanged": True,
            "unassigned_profile_remains_unassigned": True,
            "pcba_compiler_projection_quantity_equality": True,
            "renderer_dispatch_and_source_immutability": True,
            "source_hashes_unchanged_during_reproduction": True,
        },
        "mathematics": {
            "canonical_order": coordinates.CANONICAL_ORDER,
            "alternate_order": coordinates.DOMAIN_MAJOR_ORDER,
            "denominator_label": coordinates.DENOMINATOR_LABEL,
            "present_centered_coordinates": list(zero),
            "alternative_centered_coordinates": list(z),
            "changed_reference_coordinates": list(reverse),
            "recovered_alternative_profile": list(recovered),
            "max_absolute_round_trip_error": max(abs(a - b) for a, b in zip(expected, recovered)),
            "numerical_policy": coordinates.NUMERICAL_POLICY,
            "basis": profiles["project"]["basis"],
        },
        "source_reference": {
            "atlas_pdf_sha256": ATLAS_PDF_SHA256,
            "pdf_read_status": "HISTORICAL_IDENTITY_MATCHED_NOT_REOPENED_THIS_RUN",
            "pages": [6, 7, 20, 21, 22],
            "page_artifacts": "records/rpa_ohm_atlas_20260922/source_pages",
        },
        "addresses": addresses,
        "navigation": {"steps": steps, "present_before": "project", "present_after": "project",
                       "source_before_sha256": digest(document), "source_after_sha256": digest(document)},
        "ohm_calculations": results,
        "source_hashes": before_sources,
        "scope": {
            "test_suite_status": "NOT_RUN_BY_THIS_REPRODUCER",
            "browser_interaction_status": "NOT_RUN_BY_THIS_REPRODUCER",
            "present": "HOST_DECLARED_FIXTURE_NOT_MEASURED",
            "profiles": "EXPLICIT_DECLARED_EXAMPLE_VALUES",
            "runtime": "NOT_CONNECTED", "training": "NOT_RUN",
            "authority": "INSPECTION_ONLY",
        },
    }
    bodies = {"declaration.json": _json(declaration), "atlas.json": _json(document),
              "atlas.html": page.encode("utf-8"), "verification.json": _json(verification)}
    manifest = {
        "schema_version": "cas.rpa.ohm-atlas-artifacts/0.1",
        "document_sha256": document["document_sha256"],
        "files": {name: {"bytes": len(body), "sha256_raw": sha256(body).hexdigest()}
                  for name, body in sorted(bodies.items())},
        "manifest_self_hash": "OMITTED_TO_AVOID_SELF_REFERENCE",
    }
    bodies["hashes.json"] = _json(manifest)
    target.mkdir(parents=True, exist_ok=True)
    for name, body in bodies.items():
        path = destinations[name]
        _check(not path.is_symlink() and _within_home(path).is_relative_to(HOME.resolve()),
               "artifact destination changed")
        path.write_bytes(body)
        _check(path.read_bytes() == body, "artifact readback differs: " + name)
    return {"status": verification["status"], "output": str(target),
            "document_sha256": document["document_sha256"],
            "artifact_count": len(bodies), "authority": "INSPECTION_ONLY"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="artifact directory inside the CNCM homebase")
    args = parser.parse_args(argv)
    try:
        result = reproduce(args.out)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
