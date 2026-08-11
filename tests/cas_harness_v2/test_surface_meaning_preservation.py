from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from cas_harness_v2 import surface_meaning_preservation as surface_module
from cas_harness_v2._strict_json import canonical_json_bytes
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.surface_meaning_preservation import (
    CHARACTER_OVERLAP,
    EMBEDDING_OVERLAP,
    MEANING_BEARING,
    MeaningPreservationCellInput,
    SurfaceGateCellInput,
    TEXT_OVERLAP,
    TOKEN_OVERLAP,
    TOOL,
    VOCABULARY_DEPENDENT,
    build_meaning_preservation_receipt,
    build_semantic_gate_profile,
    build_surface_gate_receipt,
    load_meaning_preservation_receipt,
    load_semantic_gate_profile,
    load_surface_gate_receipt,
    replay_meaning_preservation_receipt,
    replay_semantic_gate_profile,
    replay_surface_gate_receipt,
)


def _ref(name: str, *, body: bytes | None = None, media: str = "application/test") -> ArtifactRef:
    payload = body if body is not None else (name + "\n").encode()
    return ArtifactRef(name, hashlib.sha256(payload).hexdigest().upper(), len(payload), media)


def _profile(**changes):
    kwargs = {
        "profile_id": "semantic-gate-profile-001",
        "definition_ref": _ref("definitions"),
        "crosswalk_ref": _ref("crosswalk"),
        "rubric_ref": _ref("rubric"),
        "power_plan_ref": _ref("power-plan"),
        "blind_assignment_ref": _ref("blind-assignment"),
        "independent_evaluator_ref": _ref("independent-evaluator"),
        "rater_refs": (_ref("rater-1"), _ref("rater-2")),
        "max_surface_overlap_ppm": {
            TEXT_OVERLAP: 200_000,
            CHARACTER_OVERLAP: 250_000,
            TOKEN_OVERLAP: 225_000,
            EMBEDDING_OVERLAP: 300_000,
        },
        "min_length_ratio_ppm": 800_000,
        "max_length_ratio_ppm": 1_200_000,
        "min_meaning_score_ppm": 800_000,
        "max_vocabulary_dependence_ppm": 200_000,
        "max_rater_spread_ppm": 100_000,
    }
    kwargs.update(changes)
    return build_semantic_gate_profile(**kwargs)


def _surface_cells() -> tuple[SurfaceGateCellInput, ...]:
    return (
        SurfaceGateCellInput(
            1,
            "surface-cell-001",
            _ref("prompt-001"),
            _ref("source-map-001"),
            TOOL,
            "priority-override",
            MEANING_BEARING,
            100_000,
            100_000,
            100_000,
            200_000,
            1_000_000,
            True,
            True,
            True,
            True,
        ),
        SurfaceGateCellInput(
            2,
            "surface-cell-002",
            _ref("prompt-002"),
            _ref("source-map-002"),
            TOOL,
            "encoded-injection",
            VOCABULARY_DEPENDENT,
            500_000,
            100_000,
            100_000,
            200_000,
            1_000_000,
            True,
            True,
            True,
            True,
        ),
    )


def _meaning_cells() -> tuple[MeaningPreservationCellInput, ...]:
    return (
        MeaningPreservationCellInput(
            1,
            "meaning-cell-001",
            "surface-cell-001",
            _ref("paraphrase-001"),
            _ref("paraphrase-provenance-001"),
            True,
            True,
            900_000,
            100_000,
            (900_000, 850_000),
        ),
        MeaningPreservationCellInput(
            2,
            "meaning-cell-002",
            "surface-cell-002",
            _ref("paraphrase-002"),
            _ref("paraphrase-provenance-002"),
            True,
            True,
            900_000,
            100_000,
            (900_000, 850_000),
        ),
    )


def _bundle():
    profile = _profile()
    surface = build_surface_gate_receipt(
        receipt_id="surface-receipt-001",
        profile=profile,
        protocol_ref=_ref("comparison-protocol"),
        roster_ref=_ref("comparison-roster"),
        cells=_surface_cells(),
    )
    meaning = build_meaning_preservation_receipt(
        receipt_id="meaning-receipt-001",
        profile=profile,
        surface_gate=surface,
        cells=_meaning_cells(),
    )
    return profile, surface, meaning


def test_round_trip_preserves_per_cell_results_without_aggregate_pass() -> None:
    profile, surface, meaning = _bundle()
    assert replay_semantic_gate_profile(profile) == profile
    assert replay_surface_gate_receipt(surface) == surface
    assert replay_meaning_preservation_receipt(meaning) == meaning
    surface_rows = surface.payload["cells"]
    meaning_rows = meaning.payload["cells"]
    assert surface_rows[0]["surface_eligible"] is True
    assert surface_rows[1]["surface_eligible"] is False
    assert surface_rows[1]["failed_axes"] == (TEXT_OVERLAP,)
    assert meaning_rows[0]["meaning_preserved"] is True
    assert meaning_rows[0]["eligible_for_narrow_claim"] is True
    assert meaning_rows[1]["meaning_preserved"] is True
    assert meaning_rows[1]["eligible_for_narrow_claim"] is False
    assert surface.payload["boundary"]["aggregate_verdict"] is None
    assert meaning.payload["boundary"]["aggregate_verdict"] is None


def test_loaders_require_exact_caller_bound_bytes() -> None:
    profile, surface, meaning = _bundle()
    assert load_semantic_gate_profile(
        profile.raw_bytes,
        profile_ref=profile.artifact_ref,
        definition_ref=profile.definition_ref,
        crosswalk_ref=profile.crosswalk_ref,
        rubric_ref=profile.rubric_ref,
        power_plan_ref=profile.power_plan_ref,
        blind_assignment_ref=profile.blind_assignment_ref,
        independent_evaluator_ref=profile.independent_evaluator_ref,
        rater_refs=profile.rater_refs,
    ) == profile
    assert load_surface_gate_receipt(
        surface.raw_bytes,
        receipt_ref=surface.artifact_ref,
        profile=profile,
        protocol_ref=surface.protocol_ref,
        roster_ref=surface.roster_ref,
        cells=surface.cells,
    ) == surface
    assert load_meaning_preservation_receipt(
        meaning.raw_bytes,
        receipt_ref=meaning.artifact_ref,
        profile=profile,
        surface_gate=surface,
        cells=meaning.cells,
    ) == meaning


@pytest.mark.parametrize(
    "change",
    (
        {"max_surface_overlap_ppm": {TEXT_OVERLAP: False, CHARACTER_OVERLAP: 1, TOKEN_OVERLAP: 1, EMBEDDING_OVERLAP: 1}},
        {"min_length_ratio_ppm": False},
        {"min_length_ratio_ppm": 2_000_000, "max_length_ratio_ppm": 1_000_000},
        {"rater_refs": (_ref("only-rater"),)},
    ),
)
def test_profile_rejects_type_threshold_and_rater_faults(change) -> None:
    with pytest.raises(SchemaValidationError):
        _profile(**change)


def test_profile_rejects_owner_and_content_aliases() -> None:
    with pytest.raises(SchemaValidationError, match="owner"):
        _profile(profile_id="definitions")
    same = _ref("same-role-ref")
    with pytest.raises(SchemaValidationError, match="reuses one artifact identity"):
        _profile(definition_ref=same, crosswalk_ref=same)
    shared = b"same dependency\n"
    with pytest.raises(SchemaValidationError, match="content"):
        _profile(definition_ref=_ref("definitions", body=shared), crosswalk_ref=_ref("crosswalk", body=shared))


def test_surface_rejects_missing_duplicate_and_out_of_order_cells() -> None:
    profile = _profile()
    cells = _surface_cells()
    protocol = _ref("comparison-protocol")
    roster = _ref("comparison-roster")
    with pytest.raises(SchemaValidationError, match="nonempty"):
        build_surface_gate_receipt(receipt_id="surface-empty", profile=profile, protocol_ref=protocol, roster_ref=roster, cells=())
    with pytest.raises(SchemaValidationError, match="contiguous"):
        build_surface_gate_receipt(receipt_id="surface-order", profile=profile, protocol_ref=protocol, roster_ref=roster, cells=(replace(cells[0], execution_ordinal=2),))
    with pytest.raises(SchemaValidationError, match="contiguous"):
        build_surface_gate_receipt(receipt_id="surface-duplicate", profile=profile, protocol_ref=protocol, roster_ref=roster, cells=(cells[0], replace(cells[1], cell_id=cells[0].cell_id)))


def test_surface_rejects_bool_as_integer_and_mutable_sequence() -> None:
    cell = _surface_cells()[0]
    with pytest.raises(SchemaValidationError):
        replace(cell, text_overlap_ppm=False)
    profile = _profile()
    with pytest.raises(SchemaValidationError, match="exact tuple"):
        build_surface_gate_receipt(receipt_id="surface-list", profile=profile, protocol_ref=_ref("comparison-protocol"), roster_ref=_ref("comparison-roster"), cells=list(_surface_cells()))  # type: ignore[arg-type]


def test_meaning_rejects_row_mixing_and_rater_substitution() -> None:
    profile, surface, _ = _bundle()
    rows = _meaning_cells()
    with pytest.raises(SchemaValidationError, match="mixed"):
        build_meaning_preservation_receipt(receipt_id="meaning-mixed", profile=profile, surface_gate=surface, cells=(replace(rows[0], surface_cell_id="surface-cell-002"), rows[1]))
    with pytest.raises(SchemaValidationError, match="mixed"):
        build_meaning_preservation_receipt(receipt_id="meaning-raters", profile=profile, surface_gate=surface, cells=(replace(rows[0], rater_scores_ppm=(900_000,)), rows[1]))


def test_semantic_and_vocabulary_failures_remain_visible_per_cell() -> None:
    profile, surface, _ = _bundle()
    rows = _meaning_cells()
    failed = build_meaning_preservation_receipt(
        receipt_id="meaning-failed",
        profile=profile,
        surface_gate=surface,
        cells=(replace(rows[0], independent_evaluator_score_ppm=799_999), replace(rows[1], vocabulary_dependence_ppm=200_001)),
    )
    assert tuple(row["meaning_preserved"] for row in failed.payload["cells"]) == (False, False)
    assert "overall_pass" not in failed.payload


def test_meaning_loader_rejects_cross_profile_surface_recomputation() -> None:
    _, surface, meaning = _bundle()
    loose = _profile(
        profile_id="semantic-gate-profile-loose",
        max_surface_overlap_ppm={
            TEXT_OVERLAP: 600_000,
            CHARACTER_OVERLAP: 250_000,
            TOKEN_OVERLAP: 225_000,
            EMBEDDING_OVERLAP: 300_000,
        },
    )
    value = json.loads(meaning.raw_bytes)
    value["profile_ref"] = surface_module._ref_value(loose.artifact_ref)
    value["cells"] = [
        surface_module._meaning_cell_value(cell, surface_cell, loose)
        for cell, surface_cell in zip(meaning.cells, surface.cells)
    ]
    raw = canonical_json_bytes(value)
    forged_ref = ArtifactRef(
        meaning.receipt_id,
        hashlib.sha256(raw).hexdigest().upper(),
        len(raw),
        meaning.artifact_ref.media_type,
    )
    with pytest.raises(SchemaValidationError, match="exact surface profile"):
        load_meaning_preservation_receipt(
            raw,
            receipt_ref=forged_ref,
            profile=loose,
            surface_gate=surface,
            cells=meaning.cells,
        )


def test_canonical_json_and_status_authority_forgery_reject() -> None:
    profile, surface, _ = _bundle()
    value = json.loads(surface.raw_bytes)
    value["status"]["authority"] = "AUTHORIZED"
    forged = canonical_json_bytes(value)
    forged_ref = ArtifactRef(surface.receipt_id, hashlib.sha256(forged).hexdigest().upper(), len(forged), surface.artifact_ref.media_type)
    with pytest.raises(SchemaValidationError):
        load_surface_gate_receipt(forged, receipt_ref=forged_ref, profile=profile, protocol_ref=surface.protocol_ref, roster_ref=surface.roster_ref, cells=surface.cells)
    pretty = json.dumps(json.loads(surface.raw_bytes), indent=2).encode()
    pretty_ref = ArtifactRef(surface.receipt_id, hashlib.sha256(pretty).hexdigest().upper(), len(pretty), surface.artifact_ref.media_type)
    with pytest.raises(SchemaValidationError, match="canonical"):
        load_surface_gate_receipt(pretty, receipt_ref=pretty_ref, profile=profile, protocol_ref=surface.protocol_ref, roster_ref=surface.roster_ref, cells=surface.cells)


def test_recursive_mutation_and_forged_reference_reject() -> None:
    profile, surface, _ = _bundle()
    with pytest.raises(SchemaValidationError, match="projections"):
        replay_semantic_gate_profile(
            replace(
                profile,
                max_surface_overlap_ppm=dict(profile.max_surface_overlap_ppm),
            )
        )
    forged_payload = MappingProxyType({**surface.payload, "status": dict(surface.payload["status"])})
    with pytest.raises(SchemaValidationError, match="frozen"):
        replay_surface_gate_receipt(replace(surface, payload=forged_payload))
    forged_ref = object.__new__(ArtifactRef)
    object.__setattr__(forged_ref, "artifact_id", "forged-ref")
    object.__setattr__(forged_ref, "sha256", "0" * 64)
    object.__setattr__(forged_ref, "byte_length", True)
    object.__setattr__(forged_ref, "media_type", "application/test")
    with pytest.raises(SchemaValidationError):
        replace(_surface_cells()[0], prompt_ref=forged_ref)


def test_source_has_no_execution_or_external_io_surface() -> None:
    path = Path(__file__).resolve().parents[2] / "src" / "cas_harness_v2" / "surface_meaning_preservation.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint({"requests", "httpx", "urllib", "socket", "subprocess", "torch", "runpod"})
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom)) for node in ast.walk(tree))
