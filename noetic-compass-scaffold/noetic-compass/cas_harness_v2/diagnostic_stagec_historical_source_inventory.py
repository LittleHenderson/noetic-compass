"""Deterministic, non-authority inventory of one retained historical W0 bank.

The caller must supply the exact retained bytes.  This module performs no
filesystem, network, provider, or process access.  It validates only the
historical source-material structure and emits aggregate counts and explicit
Stage C gaps.  It never returns or serializes prompt bodies and never promotes
the historical material into Stage C evidence.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any

from ._strict_json import canonical_json_bytes, freeze_json, sha256_bytes
from ._validation import ArtifactRef


HISTORICAL_W0_SOURCE_BYTE_LENGTH = 4_762_046
HISTORICAL_W0_SOURCE_SHA256 = (
    "ECC50EFB1D3BE25BC665FE7A1E04BF30632C0E1D1FACDF2F1885922D6BB8F164"
)
HISTORICAL_W0_SOURCE_SCHEMA = "cas_harness_hidden_prompt_injection_bank.v1"
HISTORICAL_W0_SUMMARY_SCHEMA = (
    "cas_harness_hidden_prompt_injection_bank.v1.summary"
)
HISTORICAL_W0_RAW_ROW_COUNT = 2_560
HISTORICAL_W0_PROMPT_GROUP_ID_COUNT = 320
HISTORICAL_W0_UNIQUE_PROMPT_COUNT = 320
HISTORICAL_W0_COLLAPSED_PAIR_COUNT = 160
HISTORICAL_W0_SAMPLES_PER_PROMPT = 8

STAGEC_REQUIRED_GROUP_COUNT = 320
STAGEC_REQUIRED_ROW_COUNT = 960
STAGEC_HISTORICAL_SOURCE_GAP_SCHEMA = (
    "cas_harness_v2.stagec_historical_source_gap_inventory.v1"
)
STAGEC_HISTORICAL_SOURCE_GAP_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-historical-source-gap-inventory+json"
)
STAGEC_HISTORICAL_SOURCE_GAP_INVENTORY_ID = (
    "stagec-historical-w0-source-gap-inventory-v1"
)

_ROOT_KEYS = {"created_at", "scenarios", "schema_version", "summary"}
_SUMMARY_KEYS = {
    "claim",
    "domain_distribution",
    "encoding_distribution",
    "exact_prompt_group_count",
    "expansion_round_distribution",
    "expansion_rounds",
    "expected_behavior_distribution",
    "next_step",
    "payload_class_count",
    "payload_class_distribution",
    "prompt_group_count",
    "prompt_injection_status_distribution",
    "samples_per_prompt",
    "scenario_count",
    "schema_version",
}
_ROW_KEYS = {
    "campaign_role",
    "claim_ceiling",
    "domain",
    "encoding",
    "expansion_round",
    "expected_behavior",
    "expected_cas_axes",
    "id",
    "label",
    "match_contract",
    "payload_class",
    "prompt",
    "prompt_group_id",
    "prompt_injection_status",
    "prompt_sha256",
    "protected_asset",
    "target_enabled_predicate",
    "target_operator",
    "target_prompt_injection_status",
}
_AXIS_KEYS = {"domain", "operator"}
_CARRIERS = {"base64", "url"}
_PAYLOAD_CLASSES = {
    "credential_secret_boundary",
    "harmful_action_boundary",
    "private_data_boundary",
    "system_instruction_boundary",
    "tool_authority_boundary",
}
_DOMAINS = {"C", "E", "O", "P"}
_STATUSES = {"ABSENT", "PRESENT"}
_EXPECTED_BEHAVIOR = {"ABSENT": "COMPLIED", "PRESENT": "REFUSED"}
_EXPECTED_PREDICATE = {
    "ABSENT": "prompt_injection_absent",
    "PRESENT": "prompt_injection_present",
}
_EXPECTED_OPERATOR = {"ABSENT": "^2", "PRESENT": "^3"}
_LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class StageCHistoricalSourceInventoryError(ValueError):
    """The exact historical source material failed closed."""


@dataclass(frozen=True, slots=True)
class StageCHistoricalSourceGapInventoryArtifact:
    """Immutable canonical aggregate; it deliberately retains no source rows."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    source_sha256: str
    source_byte_length: int
    source_raw_row_count: int
    source_prompt_group_id_count: int
    source_unique_prompt_count: int
    source_collapsed_pair_count: int
    payload: MappingProxyType

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=STAGEC_HISTORICAL_SOURCE_GAP_INVENTORY_ID,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_HISTORICAL_SOURCE_GAP_MEDIA_TYPE,
        )


def _fail(message: str) -> None:
    raise StageCHistoricalSourceInventoryError(message)


def _duplicate_safe_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("historical source JSON contains a duplicate object key")
        result[key] = value
    return result


def _forbid_float(_value: str) -> None:
    _fail("historical source JSON forbids floating-point numbers")


def _forbid_constant(_value: str) -> None:
    _fail("historical source JSON forbids non-finite constants")


def _bounded_int(value: str) -> int:
    if len(value.lstrip("-")) > 12:
        _fail("historical source JSON integer exceeds its bound")
    return int(value)


def _exact_object(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{path} must be an exact object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], path: str) -> None:
    if set(value) != expected:
        _fail(f"{path} must contain the exact historical field set")


def _exact_list(value: Any, path: str) -> list[Any]:
    if type(value) is not list:
        _fail(f"{path} must be an exact array")
    return value


def _exact_string(value: Any, path: str, *, maximum: int = 40_000) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        _fail(f"{path} must be a bounded non-empty exact string")
    if "\x00" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        _fail(f"{path} contains a forbidden Unicode scalar")
    return value


def _exact_int(
    value: Any,
    path: str,
    *,
    minimum: int = 0,
    maximum: int = 10_000,
) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        _fail(f"{path} must be an exact bounded integer")
    return value


def _exact_enum(value: Any, allowed: set[str], path: str) -> str:
    result = _exact_string(value, path, maximum=128)
    if result not in allowed:
        _fail(f"{path} is outside the closed historical enum")
    return result


def _exact_counter(
    value: Any,
    expected: Counter[Any],
    path: str,
) -> None:
    obj = _exact_object(value, path)
    expected_keys = {str(key) for key in expected}
    _exact_keys(obj, expected_keys, path)
    for key, count in expected.items():
        observed = _exact_int(obj[str(key)], f"{path}.{key}")
        if observed != count:
            _fail(f"{path} disagrees with the historical rows")


def _strict_load_historical_source(snapshot: bytes) -> dict[str, Any]:
    try:
        text = snapshot.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_safe_object,
            parse_float=_forbid_float,
            parse_int=_bounded_int,
            parse_constant=_forbid_constant,
        )
    except StageCHistoricalSourceInventoryError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise StageCHistoricalSourceInventoryError(
            "historical source bytes are not strict JSON"
        ) from exc
    return _exact_object(value, "$source")


def _validate_summary(
    value: Any,
    *,
    domain_counts: Counter[str],
    carrier_counts: Counter[str],
    round_counts: Counter[int],
    behavior_counts: Counter[str],
    payload_counts: Counter[str],
    status_counts: Counter[str],
) -> None:
    summary = _exact_object(value, "$source.summary")
    _exact_keys(summary, _SUMMARY_KEYS, "$source.summary")
    if _exact_string(summary["schema_version"], "$source.summary.schema_version") != (
        HISTORICAL_W0_SUMMARY_SCHEMA
    ):
        _fail("$source.summary.schema_version is not the retained schema")
    _exact_string(summary["claim"], "$source.summary.claim")
    _exact_string(summary["next_step"], "$source.summary.next_step")
    exact_scalars = {
        "exact_prompt_group_count": HISTORICAL_W0_PROMPT_GROUP_ID_COUNT,
        "expansion_rounds": 4,
        "payload_class_count": len(_PAYLOAD_CLASSES),
        "prompt_group_count": HISTORICAL_W0_PROMPT_GROUP_ID_COUNT,
        "samples_per_prompt": HISTORICAL_W0_SAMPLES_PER_PROMPT,
        "scenario_count": HISTORICAL_W0_RAW_ROW_COUNT,
    }
    for field, expected in exact_scalars.items():
        if _exact_int(summary[field], f"$source.summary.{field}") != expected:
            _fail(f"$source.summary.{field} is not the retained value")
    _exact_counter(
        summary["domain_distribution"], domain_counts, "$source.summary.domain_distribution"
    )
    _exact_counter(
        summary["encoding_distribution"],
        carrier_counts,
        "$source.summary.encoding_distribution",
    )
    _exact_counter(
        summary["expansion_round_distribution"],
        round_counts,
        "$source.summary.expansion_round_distribution",
    )
    _exact_counter(
        summary["expected_behavior_distribution"],
        behavior_counts,
        "$source.summary.expected_behavior_distribution",
    )
    _exact_counter(
        summary["payload_class_distribution"],
        payload_counts,
        "$source.summary.payload_class_distribution",
    )
    _exact_counter(
        summary["prompt_injection_status_distribution"],
        status_counts,
        "$source.summary.prompt_injection_status_distribution",
    )


def _validate_historical_structure(source: dict[str, Any]) -> None:
    _exact_keys(source, _ROOT_KEYS, "$source")
    if _exact_string(source["schema_version"], "$source.schema_version") != (
        HISTORICAL_W0_SOURCE_SCHEMA
    ):
        _fail("$source.schema_version is not the retained historical schema")
    _exact_string(source["created_at"], "$source.created_at", maximum=64)
    rows = _exact_list(source["scenarios"], "$source.scenarios")
    if len(rows) != HISTORICAL_W0_RAW_ROW_COUNT:
        _fail("$source.scenarios must contain exactly 2,560 historical rows")

    row_ids: set[str] = set()
    prompt_bodies: set[str] = set()
    prompt_hashes: set[str] = set()
    group_rows: Counter[str] = Counter()
    group_signatures: dict[str, tuple[str, str, str, int, str]] = {}
    collapsed_pairs: dict[str, set[str]] = {}
    collapsed_signatures: dict[str, tuple[str, str, int, str]] = {}
    domain_counts: Counter[str] = Counter()
    carrier_counts: Counter[str] = Counter()
    round_counts: Counter[int] = Counter()
    behavior_counts: Counter[str] = Counter()
    payload_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()

    for index, item in enumerate(rows):
        path = f"$source.scenarios[{index}]"
        row = _exact_object(item, path)
        _exact_keys(row, _ROW_KEYS, path)
        row_id = _exact_string(row["id"], f"{path}.id", maximum=256)
        if row_id in row_ids:
            _fail("historical row ids must be unique")
        row_ids.add(row_id)
        group_id = _exact_string(
            row["prompt_group_id"], f"{path}.prompt_group_id", maximum=256
        )
        status = _exact_enum(
            row["prompt_injection_status"], _STATUSES, f"{path}.prompt_injection_status"
        )
        carrier = _exact_enum(row["encoding"], _CARRIERS, f"{path}.encoding")
        payload_class = _exact_enum(
            row["payload_class"], _PAYLOAD_CLASSES, f"{path}.payload_class"
        )
        domain = _exact_enum(row["domain"], _DOMAINS, f"{path}.domain")
        expansion_round = _exact_int(
            row["expansion_round"], f"{path}.expansion_round", maximum=3
        )
        prompt = _exact_string(row["prompt"], f"{path}.prompt")
        try:
            computed_prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        except UnicodeEncodeError as exc:
            raise StageCHistoricalSourceInventoryError(
                f"{path}.prompt is not strict UTF-8"
            ) from exc
        prompt_sha = _exact_string(
            row["prompt_sha256"], f"{path}.prompt_sha256", maximum=64
        )
        if not _LOWER_SHA256_RE.fullmatch(prompt_sha) or prompt_sha != computed_prompt_sha:
            _fail(f"{path}.prompt_sha256 does not bind its prompt bytes")
        prompt_bodies.add(prompt)
        prompt_hashes.add(prompt_sha)

        behavior = _exact_enum(
            row["expected_behavior"], {"COMPLIED", "REFUSED"}, f"{path}.expected_behavior"
        )
        label = _exact_enum(row["label"], {"COMPLIED", "REFUSED"}, f"{path}.label")
        if behavior != _EXPECTED_BEHAVIOR[status] or label != behavior:
            _fail(f"{path} behavior and label do not match historical status")
        predicate = _exact_string(
            row["target_enabled_predicate"], f"{path}.target_enabled_predicate", maximum=64
        )
        operator = _exact_enum(
            row["target_operator"], {"^2", "^3"}, f"{path}.target_operator"
        )
        target_status = _exact_enum(
            row["target_prompt_injection_status"],
            _STATUSES,
            f"{path}.target_prompt_injection_status",
        )
        if (
            predicate != _EXPECTED_PREDICATE[status]
            or operator != _EXPECTED_OPERATOR[status]
            or target_status != status
        ):
            _fail(f"{path} target fields do not match historical status")
        axes = _exact_object(row["expected_cas_axes"], f"{path}.expected_cas_axes")
        _exact_keys(axes, _AXIS_KEYS, f"{path}.expected_cas_axes")
        if (
            _exact_enum(axes["domain"], _DOMAINS, f"{path}.expected_cas_axes.domain")
            != domain
            or _exact_enum(
                axes["operator"], {"^2", "^3"}, f"{path}.expected_cas_axes.operator"
            )
            != operator
        ):
            _fail(f"{path}.expected_cas_axes does not match the row")
        for field in (
            "campaign_role",
            "claim_ceiling",
            "match_contract",
            "protected_asset",
        ):
            _exact_string(row[field], f"{path}.{field}")

        suffix = f"_{status.lower()}"
        if not group_id.endswith(suffix):
            _fail(f"{path}.prompt_group_id does not retain its status suffix")
        collapsed_id = group_id[: -len(suffix)]
        if not collapsed_id:
            _fail(f"{path}.prompt_group_id has an empty collapsed pair id")
        signature = (prompt, status, carrier, expansion_round, payload_class)
        prior_group_signature = group_signatures.setdefault(group_id, signature)
        if prior_group_signature != signature:
            _fail("one historical prompt_group_id has inconsistent rows")
        collapsed_signature = (carrier, payload_class, expansion_round, domain)
        prior_collapsed_signature = collapsed_signatures.setdefault(
            collapsed_id, collapsed_signature
        )
        if prior_collapsed_signature != collapsed_signature:
            _fail("one historical PRESENT/ABSENT pair has inconsistent metadata")
        collapsed_pairs.setdefault(collapsed_id, set()).add(status)
        group_rows[group_id] += 1
        domain_counts[domain] += 1
        carrier_counts[carrier] += 1
        round_counts[expansion_round] += 1
        behavior_counts[behavior] += 1
        payload_counts[payload_class] += 1
        status_counts[status] += 1

    if len(row_ids) != HISTORICAL_W0_RAW_ROW_COUNT:
        _fail("historical row-id count is not exactly 2,560")
    if len(group_rows) != HISTORICAL_W0_PROMPT_GROUP_ID_COUNT:
        _fail("historical prompt_group_id count is not exactly 320")
    if set(group_rows.values()) != {HISTORICAL_W0_SAMPLES_PER_PROMPT}:
        _fail("each historical prompt_group_id must contain exactly eight rows")
    if (
        len(prompt_bodies) != HISTORICAL_W0_UNIQUE_PROMPT_COUNT
        or len(prompt_hashes) != HISTORICAL_W0_UNIQUE_PROMPT_COUNT
    ):
        _fail("historical unique-prompt count is not exactly 320")
    if len(collapsed_pairs) != HISTORICAL_W0_COLLAPSED_PAIR_COUNT:
        _fail("historical collapsed PRESENT/ABSENT pair count is not exactly 160")
    if any(statuses != _STATUSES for statuses in collapsed_pairs.values()):
        _fail("every historical collapsed pair must contain PRESENT and ABSENT")
    if set(carrier_counts) != _CARRIERS:
        _fail("historical carriers must be exactly base64 and url")
    if set(payload_counts) != _PAYLOAD_CLASSES:
        _fail("historical payload classes must be the exact retained five")
    _validate_summary(
        source["summary"],
        domain_counts=domain_counts,
        carrier_counts=carrier_counts,
        round_counts=round_counts,
        behavior_counts=behavior_counts,
        payload_counts=payload_counts,
        status_counts=status_counts,
    )


def inventory_stagec_historical_w0_source_material(
    raw_source_bytes: bytes,
) -> StageCHistoricalSourceGapInventoryArtifact:
    """Validate the exact retained W0 bytes and emit only a Stage C gap report."""

    if type(raw_source_bytes) is not bytes:
        _fail("raw_source_bytes must be exact immutable bytes")
    if len(raw_source_bytes) != HISTORICAL_W0_SOURCE_BYTE_LENGTH:
        _fail("raw_source_bytes has the wrong retained byte length")
    source_sha256 = sha256_bytes(raw_source_bytes)
    if source_sha256 != HISTORICAL_W0_SOURCE_SHA256:
        _fail("raw_source_bytes does not match the retained SHA-256 identity")
    source = _strict_load_historical_source(raw_source_bytes)
    _validate_historical_structure(source)

    payload = {
        "schema_version": STAGEC_HISTORICAL_SOURCE_GAP_SCHEMA,
        "inventory_id": STAGEC_HISTORICAL_SOURCE_GAP_INVENTORY_ID,
        "classification": {
            "scope": "STRUCTURE_ONLY",
            "source_material_status": "SYNTHETIC_SOURCE_MATERIAL",
            "authority": "NON_AUTHORITY",
            "evidence_relabeling": "FORBIDDEN",
            "prompt_body_emission": "FORBIDDEN",
        },
        "historical_source_material": {
            "schema_version": HISTORICAL_W0_SOURCE_SCHEMA,
            "sha256": source_sha256,
            "byte_length": len(raw_source_bytes),
            "raw_row_count": HISTORICAL_W0_RAW_ROW_COUNT,
            "prompt_group_id_count": HISTORICAL_W0_PROMPT_GROUP_ID_COUNT,
            "unique_prompt_count": HISTORICAL_W0_UNIQUE_PROMPT_COUNT,
            "collapsed_present_absent_pair_count": (
                HISTORICAL_W0_COLLAPSED_PAIR_COUNT
            ),
            "samples_per_unique_prompt": HISTORICAL_W0_SAMPLES_PER_PROMPT,
            "observed_variants": ["ABSENT", "PRESENT"],
            "observed_carriers": ["base64", "url"],
            "observed_payload_classes": sorted(_PAYLOAD_CLASSES),
        },
        "stagec_admission": {
            "status": "NOT_ESTABLISHED",
            "admitted_group_count": 0,
            "admitted_row_count": 0,
            "required_group_count": STAGEC_REQUIRED_GROUP_COUNT,
            "required_row_count": STAGEC_REQUIRED_ROW_COUNT,
            "source_rows_are_stagec_evidence": False,
        },
        "stagec_gaps": {
            "missing_clean_null_count": 160,
            "missing_additional_group_count": 160,
            "missing_carriers": ["plaintext", "unicode"],
            "source_to_stagec_group_mapping": "ABSENT",
            "split_assignment": "ABSENT",
            "double_adjudication": "ABSENT",
            "preexecution_drc": "ABSENT",
            "trusted_storage_and_readback": "ABSENT",
            "external_source_authentication": "ABSENT",
        },
        "boundary": {
            "stagec_corpus": "NOT_AUTHORED",
            "stagec_corpus_freeze": "NOT_ESTABLISHED",
            "execution_authority": "NOT_GRANTED",
            "scientific_conclusion": "NOT_ESTABLISHED",
            "license": "NOT_GRANTED",
            "disclosure": "HELD",
        },
    }
    report_raw = canonical_json_bytes(payload)
    return StageCHistoricalSourceGapInventoryArtifact(
        raw_bytes=report_raw,
        sha256=sha256_bytes(report_raw),
        byte_length=len(report_raw),
        source_sha256=source_sha256,
        source_byte_length=len(raw_source_bytes),
        source_raw_row_count=HISTORICAL_W0_RAW_ROW_COUNT,
        source_prompt_group_id_count=HISTORICAL_W0_PROMPT_GROUP_ID_COUNT,
        source_unique_prompt_count=HISTORICAL_W0_UNIQUE_PROMPT_COUNT,
        source_collapsed_pair_count=HISTORICAL_W0_COLLAPSED_PAIR_COUNT,
        payload=freeze_json(payload),
    )


__all__ = [
    "HISTORICAL_W0_SOURCE_BYTE_LENGTH",
    "HISTORICAL_W0_SOURCE_SHA256",
    "HISTORICAL_W0_SOURCE_SCHEMA",
    "HISTORICAL_W0_RAW_ROW_COUNT",
    "HISTORICAL_W0_PROMPT_GROUP_ID_COUNT",
    "HISTORICAL_W0_UNIQUE_PROMPT_COUNT",
    "HISTORICAL_W0_COLLAPSED_PAIR_COUNT",
    "STAGEC_REQUIRED_GROUP_COUNT",
    "STAGEC_REQUIRED_ROW_COUNT",
    "STAGEC_HISTORICAL_SOURCE_GAP_SCHEMA",
    "STAGEC_HISTORICAL_SOURCE_GAP_MEDIA_TYPE",
    "StageCHistoricalSourceGapInventoryArtifact",
    "StageCHistoricalSourceInventoryError",
    "inventory_stagec_historical_w0_source_material",
]
