from __future__ import annotations

import builtins
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
)
import cas_harness_v2.diagnostic_stagec_historical_source_inventory as inventory_module  # noqa: E402
from cas_harness_v2.diagnostic_stagec_historical_source_inventory import (  # noqa: E402
    HISTORICAL_W0_COLLAPSED_PAIR_COUNT,
    HISTORICAL_W0_PROMPT_GROUP_ID_COUNT,
    HISTORICAL_W0_RAW_ROW_COUNT,
    HISTORICAL_W0_SOURCE_BYTE_LENGTH,
    HISTORICAL_W0_SOURCE_SHA256,
    HISTORICAL_W0_UNIQUE_PROMPT_COUNT,
    STAGEC_HISTORICAL_SOURCE_GAP_MEDIA_TYPE,
    STAGEC_HISTORICAL_SOURCE_GAP_SCHEMA,
    StageCHistoricalSourceInventoryError,
    inventory_stagec_historical_w0_source_material,
)


RETAINED_BLOB_SPEC = (
    "349465d:noetic-compass-scaffold/noetic-compass/live-trace-worker/"
    "scenarios/hidden_prompt_injection_bank_large_v1_20260617.json"
)
FROZEN_GAP_REPORT_SHA256 = (
    "B33B45D1D64099A0CB4E954B1EB8EF08876BA20C273983B9AFC4F0DEBC3F2C41"
)
FROZEN_GAP_REPORT_BYTE_LENGTH = 1_647

PAYLOAD_CLASSES = (
    "credential_secret_boundary",
    "harmful_action_boundary",
    "private_data_boundary",
    "system_instruction_boundary",
    "tool_authority_boundary",
)
PAYLOAD_DOMAINS = {
    "credential_secret_boundary": "P",
    "harmful_action_boundary": "O",
    "private_data_boundary": "E",
    "system_instruction_boundary": "P",
    "tool_authority_boundary": "C",
}


def _synthetic_shape_source() -> bytes:
    """Build only harmless placeholders with the retained aggregate shape."""

    rows = []
    for pair_number in range(HISTORICAL_W0_COLLAPSED_PAIR_COUNT):
        payload_class = PAYLOAD_CLASSES[pair_number % len(PAYLOAD_CLASSES)]
        domain = PAYLOAD_DOMAINS[payload_class]
        carrier = "base64" if pair_number % 2 == 0 else "url"
        expansion_round = pair_number % 4
        for status in ("PRESENT", "ABSENT"):
            behavior = "REFUSED" if status == "PRESENT" else "COMPLIED"
            operator = "^3" if status == "PRESENT" else "^2"
            predicate = (
                "prompt_injection_present"
                if status == "PRESENT"
                else "prompt_injection_absent"
            )
            group_id = f"synthetic_shape_{pair_number:03d}_{status.lower()}"
            prompt = (
                "Synthetic non-authority source placeholder "
                f"{pair_number:03d} {status}."
            )
            prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            for seed in range(8):
                rows.append(
                    {
                        "campaign_role": "synthetic_shape_only",
                        "claim_ceiling": "Non-authority test shape only.",
                        "domain": domain,
                        "encoding": carrier,
                        "expansion_round": expansion_round,
                        "expected_behavior": behavior,
                        "expected_cas_axes": {
                            "domain": domain,
                            "operator": operator,
                        },
                        "id": f"{group_id}_seed_{seed:02d}",
                        "label": behavior,
                        "match_contract": "Synthetic shape-only pair.",
                        "payload_class": payload_class,
                        "prompt": prompt,
                        "prompt_group_id": group_id,
                        "prompt_injection_status": status,
                        "prompt_sha256": prompt_sha256,
                        "protected_asset": "Synthetic placeholder asset.",
                        "target_enabled_predicate": predicate,
                        "target_operator": operator,
                        "target_prompt_injection_status": status,
                    }
                )
    summary = {
        "claim": "OPEN / NOT LICENSED synthetic test shape.",
        "domain_distribution": {"C": 512, "E": 512, "O": 512, "P": 1024},
        "encoding_distribution": {"base64": 1280, "url": 1280},
        "exact_prompt_group_count": 320,
        "expansion_round_distribution": {
            "0": 640,
            "1": 640,
            "2": 640,
            "3": 640,
        },
        "expansion_rounds": 4,
        "expected_behavior_distribution": {"COMPLIED": 1280, "REFUSED": 1280},
        "next_step": "No action; shape-only unit fixture.",
        "payload_class_count": 5,
        "payload_class_distribution": {
            payload_class: 512 for payload_class in PAYLOAD_CLASSES
        },
        "prompt_group_count": 320,
        "prompt_injection_status_distribution": {"ABSENT": 1280, "PRESENT": 1280},
        "samples_per_prompt": 8,
        "scenario_count": 2560,
        "schema_version": "cas_harness_hidden_prompt_injection_bank.v1.summary",
    }
    value = {
        "created_at": "2026-06-18T00:04:28+00:00",
        "scenarios": rows,
        "schema_version": "cas_harness_hidden_prompt_injection_bank.v1",
        "summary": summary,
    }
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


@pytest.fixture(scope="module")
def synthetic_source() -> bytes:
    return _synthetic_shape_source()


@pytest.fixture(scope="module")
def retained_source() -> bytes:
    """Caller-only recovery: no production path reads Git or a filesystem."""

    try:
        completed = subprocess.run(
            ["git", "show", RETAINED_BLOB_SPEC],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        pytest.skip("retained Git blob is unavailable in this checkout")
    return completed.stdout


def _accept_fixture_identity(monkeypatch: pytest.MonkeyPatch, raw: bytes) -> None:
    monkeypatch.setattr(
        inventory_module, "HISTORICAL_W0_SOURCE_BYTE_LENGTH", len(raw)
    )
    monkeypatch.setattr(
        inventory_module, "HISTORICAL_W0_SOURCE_SHA256", sha256_bytes(raw)
    )


def _mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def test_exact_retained_identity_and_frozen_gap_report(
    retained_source: bytes,
) -> None:
    assert len(retained_source) == HISTORICAL_W0_SOURCE_BYTE_LENGTH
    assert sha256_bytes(retained_source) == HISTORICAL_W0_SOURCE_SHA256
    artifact = inventory_stagec_historical_w0_source_material(retained_source)
    assert artifact.sha256 == FROZEN_GAP_REPORT_SHA256
    assert artifact.byte_length == FROZEN_GAP_REPORT_BYTE_LENGTH
    assert artifact.raw_bytes == canonical_json_bytes(json.loads(artifact.raw_bytes))
    assert artifact.artifact_ref.media_type == STAGEC_HISTORICAL_SOURCE_GAP_MEDIA_TYPE
    assert artifact.artifact_ref.verify_bytes(artifact.raw_bytes)
    assert artifact.source_raw_row_count == HISTORICAL_W0_RAW_ROW_COUNT
    assert artifact.source_prompt_group_id_count == HISTORICAL_W0_PROMPT_GROUP_ID_COUNT
    assert artifact.source_unique_prompt_count == HISTORICAL_W0_UNIQUE_PROMPT_COUNT
    assert artifact.source_collapsed_pair_count == HISTORICAL_W0_COLLAPSED_PAIR_COUNT


def test_report_is_explicitly_non_authority_and_admits_zero_stagec_rows(
    synthetic_source: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_fixture_identity(monkeypatch, synthetic_source)
    artifact = inventory_stagec_historical_w0_source_material(synthetic_source)
    assert artifact.payload["schema_version"] == STAGEC_HISTORICAL_SOURCE_GAP_SCHEMA
    assert artifact.payload["classification"] == {
        "scope": "STRUCTURE_ONLY",
        "source_material_status": "SYNTHETIC_SOURCE_MATERIAL",
        "authority": "NON_AUTHORITY",
        "evidence_relabeling": "FORBIDDEN",
        "prompt_body_emission": "FORBIDDEN",
    }
    assert artifact.payload["stagec_admission"] == {
        "status": "NOT_ESTABLISHED",
        "admitted_group_count": 0,
        "admitted_row_count": 0,
        "required_group_count": 320,
        "required_row_count": 960,
        "source_rows_are_stagec_evidence": False,
    }
    assert artifact.payload["boundary"]["stagec_corpus"] == "NOT_AUTHORED"
    assert artifact.payload["boundary"]["execution_authority"] == "NOT_GRANTED"


def test_exact_aggregate_source_shape_and_stagec_gaps_are_reported(
    synthetic_source: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_fixture_identity(monkeypatch, synthetic_source)
    payload = inventory_stagec_historical_w0_source_material(
        synthetic_source
    ).payload
    source = payload["historical_source_material"]
    assert source["raw_row_count"] == 2_560
    assert source["prompt_group_id_count"] == 320
    assert source["unique_prompt_count"] == 320
    assert source["collapsed_present_absent_pair_count"] == 160
    assert source["observed_variants"] == ("ABSENT", "PRESENT")
    assert source["observed_carriers"] == ("base64", "url")
    assert source["observed_payload_classes"] == tuple(sorted(PAYLOAD_CLASSES))
    assert payload["stagec_gaps"] == {
        "missing_clean_null_count": 160,
        "missing_additional_group_count": 160,
        "missing_carriers": ("plaintext", "unicode"),
        "source_to_stagec_group_mapping": "ABSENT",
        "split_assignment": "ABSENT",
        "double_adjudication": "ABSENT",
        "preexecution_drc": "ABSENT",
        "trusted_storage_and_readback": "ABSENT",
        "external_source_authentication": "ABSENT",
    }


def test_report_never_retains_or_emits_prompt_bodies(
    synthetic_source: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_fixture_identity(monkeypatch, synthetic_source)
    source = json.loads(synthetic_source)
    prompt_bodies = {row["prompt"] for row in source["scenarios"]}
    artifact = inventory_stagec_historical_w0_source_material(synthetic_source)
    assert not hasattr(artifact, "source_bytes")
    assert not hasattr(artifact, "rows")
    for prompt in prompt_bodies:
        assert prompt.encode("utf-8") not in artifact.raw_bytes


def test_report_and_nested_payload_are_immutable(
    synthetic_source: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_fixture_identity(monkeypatch, synthetic_source)
    artifact = inventory_stagec_historical_w0_source_material(synthetic_source)
    with pytest.raises(FrozenInstanceError):
        artifact.source_raw_row_count = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        artifact.payload["schema_version"] = "forged"  # type: ignore[index]
    with pytest.raises(TypeError):
        artifact.payload["stagec_gaps"]["missing_clean_null_count"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "value",
    [b"", bytearray(b"x"), memoryview(b"x"), "not-bytes"],
)
def test_only_exact_known_immutable_bytes_are_accepted(value: object) -> None:
    with pytest.raises(StageCHistoricalSourceInventoryError):
        inventory_stagec_historical_w0_source_material(value)  # type: ignore[arg-type]


def test_same_length_source_digest_mismatch_fails_before_parsing(
    synthetic_source: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_fixture_identity(monkeypatch, synthetic_source)
    mutated = bytes([synthetic_source[0] ^ 1]) + synthetic_source[1:]
    with pytest.raises(StageCHistoricalSourceInventoryError, match="SHA-256"):
        inventory_stagec_historical_w0_source_material(mutated)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: value.__setitem__("extra", 1), "exact historical field set"),
        (
            lambda value: value["scenarios"][0].__setitem__(
                "prompt_sha256", "0" * 64
            ),
            "does not bind its prompt bytes",
        ),
        (
            lambda value: value["scenarios"][0].__setitem__("encoding", "plaintext"),
            "closed historical enum",
        ),
        (
            lambda value: value["scenarios"][0].__setitem__(
                "expansion_round", True
            ),
            "exact bounded integer",
        ),
        (
            lambda value: value["summary"].__setitem__("scenario_count", 2_559),
            "not the retained value",
        ),
    ],
)
def test_strict_historical_schema_fails_closed_after_identity_check(
    synthetic_source: bytes,
    monkeypatch: pytest.MonkeyPatch,
    change,
    message: str,
) -> None:
    mutated = _mutate(synthetic_source, change)
    _accept_fixture_identity(monkeypatch, mutated)
    with pytest.raises(StageCHistoricalSourceInventoryError, match=message):
        inventory_stagec_historical_w0_source_material(mutated)


def test_public_path_has_no_io_provider_process_or_caller_callback(
    synthetic_source: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_fixture_identity(monkeypatch, synthetic_source)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external effect")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    artifact = inventory_stagec_historical_w0_source_material(synthetic_source)
    assert artifact.payload["stagec_admission"]["admitted_row_count"] == 0

    class HostileBytes(bytes):
        def __len__(self):
            raise AssertionError("caller-controlled callback invoked")

    with pytest.raises(StageCHistoricalSourceInventoryError, match="exact immutable bytes"):
        inventory_stagec_historical_w0_source_material(HostileBytes(b"x"))
