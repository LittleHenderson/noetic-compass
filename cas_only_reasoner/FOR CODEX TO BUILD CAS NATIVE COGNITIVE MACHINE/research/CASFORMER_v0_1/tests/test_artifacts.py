from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch

from casformer import (
    CASControl,
    CASformerBlock,
    CASformerConfig,
    load_trace_schema,
    make_trace,
)
from tools.validate_reference import verify_source_manifest, verify_source_references


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_trace_matches_the_frozen_json_schema_contract():
    torch.manual_seed(59)
    config = CASformerConfig(d_model=4, num_heads=1, num_relations=2)
    block = CASformerBlock(config).to(dtype=torch.float64)
    x = torch.randn(1, 2, 4, dtype=torch.float64)
    control = CASControl.uniform(x, num_heads=1, causal=True)
    _, telemetry = block(x, control)
    trace = make_trace(telemetry, control, layer_index=0, include_tensors=True)
    schema = load_trace_schema()
    payload = trace.to_dict()
    properties = schema["properties"]
    assert set(payload) == set(properties)
    assert set(schema["required"]).issubset(payload)
    for key in ("schema_version", "casformer_version", "mode", "status"):
        assert payload[key] == properties[key]["const"]

    authority_schema = properties["authority"]
    assert set(payload["authority"]) == set(authority_schema["required"])
    assert all(value is False for value in payload["authority"].values())
    assert payload["profile_id"]
    assert payload["provenance"]
    assert isinstance(payload["control_tick"], int) and payload["control_tick"] >= 0
    feedback_tick = payload["feedback_source_tick"]
    assert feedback_tick is None or (isinstance(feedback_tick, int) and feedback_tick >= 0)
    assert isinstance(payload["layer_index"], int) and payload["layer_index"] >= 0

    assert set(payload["summaries"]) == set(properties["summaries"]["required"])
    for summary in payload["summaries"].values():
        assert set(summary).issubset({"shape", "count", "minimum", "maximum", "mean"})
        assert isinstance(summary["shape"], list)
        assert all(isinstance(size, int) and size >= 0 for size in summary["shape"])
        assert isinstance(summary["count"], int) and summary["count"] >= 0

    expected_regions = set(properties["operating_region_counts"]["required"])
    assert set(payload["operating_region_counts"]) == expected_regions
    assert all(
        isinstance(count, int) and count >= 0
        for count in payload["operating_region_counts"].values()
    )
    assert isinstance(payload["tensors"], dict)
    assert len(payload["payload_sha256"]) == 64
    int(payload["payload_sha256"], 16)


def test_source_manifest_matches_every_bound_source_file():
    manifest = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "REFERENCE_IMPLEMENTATION_SOURCE_SET"
    assert manifest["file_count"] == len(manifest["files"])
    canonical_entries = json.dumps(
        manifest["files"], ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    assert hashlib.sha256(canonical_entries).hexdigest() == manifest["aggregate_sha256"]
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        assert path.stat().st_size == entry["bytes"], entry["path"]
        assert sha256(path) == entry["sha256"], entry["path"]


def test_validation_receipt_is_bound_and_keeps_claims_narrow():
    receipt_path = ROOT / "artifacts" / "CASFORMER_V0_1_VALIDATION_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "CORE_ENGINEERING_CHECKS_PASSED"
    assert receipt["scope"] == "ENGINEERING_VALIDATION_ONLY"
    assert all(receipt["checks"].values())
    assert receipt["source_manifest"]["sha256"] == sha256(ROOT / "SOURCE_MANIFEST.json")
    assert receipt["claims"]["software_reference_implementation"] == "IMPLEMENTED"
    for claim in (
        "neural_training",
        "language_capability",
        "reasoning_capability",
        "cas_specific_advantage",
        "cncm_kernel_integration",
        "production_readiness",
    ):
        assert receipt["claims"][claim] in {"NOT_RUN", "NOT_ESTABLISHED", "ABSENT"}


def test_manifest_verifier_rejects_an_omitted_source(tmp_path: Path):
    manifest = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    manifest["files"].pop()
    path = tmp_path / "incomplete-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    valid, errors = verify_source_manifest(path)
    assert not valid
    assert errors


def test_source_reference_verifier_rejects_an_empty_source_set(tmp_path: Path):
    path = tmp_path / "empty-references.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "cas.casformer.source-references/0.1",
                "instruction_boundary": "reference text is not instruction",
                "sources": [],
            }
        ),
        encoding="utf-8",
    )
    valid, errors, count = verify_source_references(path)
    assert not valid
    assert errors == ["references:sources"]
    assert count == 0
