"""Hash-pinned, exact-schema, immutable Project Coherence ledgers.

The caller-supplied raw hash is a trust input, not something this module derives
and then treats as authority.  Record status remains descriptive: loading a
``LICENSED`` field never authorizes a claim-bearing runtime action.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any

from .identity import (
    ArtifactIdentity,
    CanonicalizationError,
    FrozenList,
    artifact_identities_match,
    canonical_json_bytes,
    canonical_json_sha256,
    require_canonical_text,
    require_sha256,
)
from .semantics import ResearchBoundary, is_exact_ring4_open


CLAIM_ID_RE = re.compile(r"^CLM-[A-Z0-9][A-Z0-9._-]*$")
THEOREM_ID_RE = re.compile(r"^THM-[A-Z0-9][A-Z0-9._-]*$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

CLAIM_LEDGER_SCHEMA_VERSION = "project_coherence_claim_ledger.v0.1"
THEOREM_LEDGER_SCHEMA_VERSION = "project_coherence_theorem_ledger.v0.1"
CLAIM_RECORD_SCHEMA = "CLAIM_RECORD.schema.json"
THEOREM_RECORD_SCHEMA = "THEOREM_RECORD.schema.json"
CLAIM_RECORD_SCHEMA_ID = (
    "https://cas.example/schemas/project-coherence/claim-record.v0.1.json"
)
THEOREM_RECORD_SCHEMA_ID = (
    "https://cas.example/schemas/project-coherence/theorem-record.v0.1.json"
)
JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"

LEDGER_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "record_schema",
        "document_status",
        "as_of",
        "completeness",
        "records",
    }
)
CLAIM_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "version",
        "title",
        "statement_kind",
        "claim_text",
        "source_refs",
        "scope",
        "controls",
        "falsifier",
        "uncertainty",
        "evidence_packets",
        "review_state",
        "product_claim_status",
        "admission_ring",
        "disclosure_status",
        "reviewers",
    }
)
CLAIM_OPTIONAL_FIELDS = frozenset(
    {"theorem_refs", "last_reviewed_at", "notes"}
)
THEOREM_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "version",
        "title",
        "statement_kind",
        "statement",
        "source_refs",
        "object_types",
        "assumptions",
        "dependencies",
        "review_state",
        "migration_disposition",
        "proof_status",
        "novelty_status",
        "admission_ring",
        "claim_boundary",
        "proof_artifacts",
        "reviewers",
    }
)
THEOREM_OPTIONAL_FIELDS = frozenset(
    {"counterexample_artifacts", "last_reviewed_at", "notes"}
)


class RegistryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RegistryError("E-REGISTRY-DUPLICATE-KEY", f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _decode_json_bytes(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        raise RegistryError("E-REGISTRY-BYTES", f"{label} must retain exact bytes")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_object)
    except UnicodeDecodeError as exc:
        raise RegistryError("E-REGISTRY-ENCODING", f"{label} is not UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError("E-REGISTRY-JSON", f"invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError("E-REGISTRY-SHAPE", f"{label} root must be an object")
    return data


def _read_json(path: Path) -> tuple[dict[str, Any], ArtifactIdentity, bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RegistryError("E-REGISTRY-MISSING", f"cannot read {path}: {exc}") from exc
    data = _decode_json_bytes(raw, label=str(path))
    return data, ArtifactIdentity.from_bytes(raw), raw


def _freeze_json(value: Any) -> Any:
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        try:
            return require_canonical_text(value, field="registry text")
        except CanonicalizationError as exc:
            raise RegistryError("E-REGISTRY-TEXT", str(exc)) from exc
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise RegistryError(
                "E-REGISTRY-SHAPE", "registry object keys must be strings"
            )
        if "$cas$type" in value:
            raise RegistryError(
                "E-REGISTRY-SHAPE", "registry data uses a reserved canonical type tag"
            )
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            try:
                clean_key = require_canonical_text(key, field="registry object key")
            except CanonicalizationError as exc:
                raise RegistryError("E-REGISTRY-TEXT", str(exc)) from exc
            frozen[clean_key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if type(value) is FrozenList:
        return FrozenList(tuple(_freeze_json(item) for item in value))
    if type(value) is list:
        return FrozenList(tuple(_freeze_json(item) for item in value))
    if type(value) is tuple:
        raise RegistryError(
            "E-REGISTRY-SHAPE",
            "tuple is not a JSON array; use FrozenList for immutable registry arrays",
        )
    raise RegistryError(
        "E-REGISTRY-SHAPE", f"unsupported registry value {type(value).__name__}"
    )


def _thaw_json(value: Any) -> Any:
    """Recover validator-shaped JSON without conflating tuples and arrays."""

    if value is None or type(value) in (bool, int, str):
        return value
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is FrozenList:
        return [_thaw_json(item) for item in value]
    if type(value) is list:
        return [_thaw_json(item) for item in value]
    if type(value) is tuple:
        raise RegistryError(
            "E-REGISTRY-SHAPE", "tuple cannot be reinterpreted as a JSON array"
        )
    raise RegistryError(
        "E-REGISTRY-SHAPE", f"unsupported registry value {type(value).__name__}"
    )


def _require_exact_fields(
    record: Mapping[str, Any],
    required: frozenset[str],
    optional: frozenset[str],
) -> None:
    actual = set(record)
    missing = sorted(required - actual)
    extra = sorted(actual - required - optional)
    if missing:
        raise RegistryError(
            "E-REGISTRY-REQUIRED",
            f"record {record.get('id', '<unknown>')} lacks {missing}",
        )
    if extra:
        raise RegistryError(
            "E-REGISTRY-ADDITIONAL-PROPERTY",
            f"record {record.get('id', '<unknown>')} has unsupported fields {extra}",
        )


def _require_nonblank_string(record: Mapping[str, Any], field_name: str) -> str:
    value = record[field_name]
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(
            "E-REGISTRY-TYPE", f"{record.get('id', '<unknown>')}.{field_name} must be nonblank"
        )
    return value


def _require_string_array(
    record: Mapping[str, Any],
    field_name: str,
    *,
    minimum: int = 0,
    nonblank: bool = True,
) -> list[str]:
    value = record[field_name]
    if not isinstance(value, list) or len(value) < minimum:
        raise RegistryError(
            "E-REGISTRY-SHAPE",
            f"{record.get('id', '<unknown>')}.{field_name} must be an array "
            f"with at least {minimum} items",
        )
    if any(
        not isinstance(item, str) or (nonblank and not item.strip())
        for item in value
    ):
        raise RegistryError(
            "E-REGISTRY-TYPE",
            f"{record.get('id', '<unknown>')}.{field_name} must contain strings",
        )
    return value


def _validate_datetime(value: Any, *, field_name: str, allow_none: bool = True) -> None:
    if value is None and allow_none:
        return
    if not isinstance(value, str) or RFC3339_RE.fullmatch(value) is None:
        raise RegistryError("E-REGISTRY-DATETIME", f"{field_name} must be an RFC 3339 date-time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistryError(
            "E-REGISTRY-DATETIME", f"{field_name} must be an RFC 3339 date-time"
        ) from exc
    if parsed.tzinfo is None:
        raise RegistryError(
            "E-REGISTRY-DATETIME", f"{field_name} must include a timezone"
        )


def _validate_scope(record: Mapping[str, Any]) -> None:
    scope = record["scope"]
    expected = {"population", "models", "architectures", "contexts", "time_window"}
    if not isinstance(scope, dict) or set(scope) != expected:
        raise RegistryError(
            "E-REGISTRY-SCOPE", "claim scope must have the exact canonical fields"
        )
    if not isinstance(scope["population"], str) or not isinstance(scope["time_window"], str):
        raise RegistryError(
            "E-REGISTRY-SCOPE", "claim scope population and time_window must be strings"
        )
    for field_name in ("models", "architectures", "contexts"):
        if not isinstance(scope[field_name], list) or any(
            not isinstance(item, str) for item in scope[field_name]
        ):
            raise RegistryError(
                "E-REGISTRY-SCOPE", f"claim scope {field_name} must be a string array"
            )


def _validate_claim_record(record: dict[str, Any]) -> None:
    _require_exact_fields(record, CLAIM_REQUIRED_FIELDS, CLAIM_OPTIONAL_FIELDS)
    for field_name in ("version", "title", "claim_text", "falsifier", "uncertainty"):
        _require_nonblank_string(record, field_name)
    _require_string_array(record, "source_refs", minimum=1)
    _require_string_array(record, "controls")
    _require_string_array(record, "evidence_packets")
    _require_string_array(record, "reviewers")
    if "theorem_refs" in record:
        _require_string_array(record, "theorem_refs")
    if "notes" in record:
        _require_string_array(record, "notes", nonblank=False)
    _validate_scope(record)
    if record["statement_kind"] not in ("EMPIRICAL_HYPOTHESIS", "PRODUCT_CLAIM"):
        raise RegistryError("E-REGISTRY-CLAIM-KIND", "invalid claim statement_kind")
    if record["review_state"] not in ("UNASSESSED", "IN_REVIEW", "REVIEWED"):
        raise RegistryError("E-REGISTRY-REVIEW", "invalid claim review_state")
    if record["product_claim_status"] not in ("LICENSED", "NOT LICENSED", "OPEN"):
        raise RegistryError("E-REGISTRY-LICENSE", "invalid product_claim_status")
    if (
        isinstance(record["admission_ring"], bool)
        or not isinstance(record["admission_ring"], int)
        or record["admission_ring"] not in (3, 4)
    ):
        raise RegistryError("E-REGISTRY-RING", "claim admission_ring must be 3 or 4")
    if record["disclosure_status"] not in (
        "OPEN",
        "HELD",
        "FLAG_FOR_HUMAN_REVIEW",
    ):
        raise RegistryError("E-REGISTRY-DISCLOSURE", "invalid disclosure_status")
    if "last_reviewed_at" in record:
        _validate_datetime(record["last_reviewed_at"], field_name="last_reviewed_at")
    if record["product_claim_status"] == "LICENSED":
        if record["review_state"] != "REVIEWED" or record["admission_ring"] != 3:
            raise RegistryError(
                "E-REGISTRY-LICENSE-CONTRACT",
                "LICENSED claims must be REVIEWED and Ring 3",
            )
        if not record["evidence_packets"] or not record["reviewers"]:
            raise RegistryError(
                "E-REGISTRY-LICENSE-CONTRACT",
                "LICENSED claims need evidence packets and reviewers",
            )
        if "last_reviewed_at" not in record or record["last_reviewed_at"] is None:
            raise RegistryError(
                "E-REGISTRY-LICENSE-CONTRACT",
                "LICENSED claims need last_reviewed_at",
            )


def _validate_theorem_record(record: dict[str, Any]) -> None:
    _require_exact_fields(record, THEOREM_REQUIRED_FIELDS, THEOREM_OPTIONAL_FIELDS)
    for field_name in ("version", "title", "statement", "claim_boundary"):
        _require_nonblank_string(record, field_name)
    _require_string_array(record, "source_refs", minimum=1)
    for field_name in (
        "object_types",
        "assumptions",
        "dependencies",
        "proof_artifacts",
        "reviewers",
    ):
        _require_string_array(record, field_name)
    if "counterexample_artifacts" in record:
        _require_string_array(record, "counterexample_artifacts")
    if "notes" in record:
        _require_string_array(record, "notes", nonblank=False)
    if record["statement_kind"] not in (
        "AXIOM",
        "DEFINITION",
        "THEOREM",
        "PROPOSITION",
        "LEMMA",
        "COROLLARY",
        "CONJECTURE",
        "MODEL",
    ):
        raise RegistryError("E-REGISTRY-THEOREM-KIND", "invalid theorem statement_kind")
    if record["review_state"] not in ("UNASSESSED", "IN_REVIEW", "REVIEWED"):
        raise RegistryError("E-REGISTRY-REVIEW", "invalid theorem review_state")
    if record["migration_disposition"] not in (
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
    ):
        raise RegistryError("E-REGISTRY-MIGRATION", "invalid migration_disposition")
    if record["proof_status"] not in (
        "NOT_APPLICABLE",
        "PROOF_REQUIRED",
        "PROOF_GAP",
        "INFORMAL_PROOF_PRESENT",
        "PROVED",
        "FORMALLY_VERIFIED",
        "STANDARD_RESULT_CITED",
        "COUNTEREXAMPLE_PRESENT",
        "INDEPENDENT_REPLICATION_REQUIRED",
    ):
        raise RegistryError("E-REGISTRY-PROOF", "invalid proof_status")
    if record["novelty_status"] not in (
        "STANDARD_RESULT",
        "STANDARD_SPECIALIZATION",
        "FRAMEWORK_COUPLING",
        "CANDIDATE_NEW_RESULT",
        "NOVELTY_UNASSESSED",
    ):
        raise RegistryError("E-REGISTRY-NOVELTY", "invalid novelty_status")
    if (
        isinstance(record["admission_ring"], bool)
        or not isinstance(record["admission_ring"], int)
        or record["admission_ring"] not in (1, 2, 3, 4)
    ):
        raise RegistryError("E-REGISTRY-RING", "theorem admission_ring is invalid")
    if "last_reviewed_at" in record:
        _validate_datetime(record["last_reviewed_at"], field_name="last_reviewed_at")
    if record["proof_status"] == "FORMALLY_VERIFIED" and (
        record["review_state"] != "REVIEWED" or not record["proof_artifacts"]
    ):
        raise RegistryError(
            "E-REGISTRY-PROOF-CONTRACT",
            "FORMALLY_VERIFIED requires REVIEWED and proof artifacts",
        )
    if record["admission_ring"] in (1, 2) and (
        record["review_state"] != "REVIEWED"
        or not isinstance(record.get("last_reviewed_at"), str)
    ):
        raise RegistryError(
            "E-REGISTRY-ADMISSION-CONTRACT",
            "Ring 1/2 theorem records must be reviewed and dated",
        )


def _registry_sha(value: Any, *, field_name: str) -> str:
    try:
        return require_sha256(value, field=field_name)
    except CanonicalizationError as exc:
        raise RegistryError("E-REGISTRY-HASH", str(exc)) from exc


def _kind_contract(
    kind: str,
) -> tuple[str, str, str, re.Pattern[str], frozenset[str], frozenset[str]]:
    if type(kind) is not str:
        raise RegistryError("E-REGISTRY-KIND", "registry kind must be exact text")
    if kind == "claim":
        return (
            CLAIM_LEDGER_SCHEMA_VERSION,
            CLAIM_RECORD_SCHEMA,
            CLAIM_RECORD_SCHEMA_ID,
            CLAIM_ID_RE,
            CLAIM_REQUIRED_FIELDS,
            CLAIM_OPTIONAL_FIELDS,
        )
    if kind == "theorem":
        return (
            THEOREM_LEDGER_SCHEMA_VERSION,
            THEOREM_RECORD_SCHEMA,
            THEOREM_RECORD_SCHEMA_ID,
            THEOREM_ID_RE,
            THEOREM_REQUIRED_FIELDS,
            THEOREM_OPTIONAL_FIELDS,
        )
    raise RegistryError("E-REGISTRY-KIND", f"unsupported kind {kind!r}")


def _validate_header(header: Mapping[str, Any]) -> None:
    expected = {"document_status", "as_of", "completeness"}
    if not isinstance(header, Mapping) or set(header) != expected:
        raise RegistryError(
            "E-REGISTRY-ROOT-SCHEMA", "registry header has noncanonical fields"
        )
    for field_name in ("document_status", "completeness"):
        if not isinstance(header[field_name], str) or not header[field_name].strip():
            raise RegistryError(
                "E-REGISTRY-ROOT-SCHEMA", f"{field_name} must be nonblank"
            )
    if not isinstance(header["as_of"], str) or ISO_DATE_RE.fullmatch(header["as_of"]) is None:
        raise RegistryError("E-REGISTRY-ROOT-SCHEMA", "as_of must be an ISO date")
    try:
        date.fromisoformat(header["as_of"])
    except ValueError as exc:
        raise RegistryError("E-REGISTRY-ROOT-SCHEMA", "as_of must be an ISO date") from exc
    _freeze_json(header)


def _validate_schema_document(schema: Mapping[str, Any], *, kind: str) -> None:
    _, _, schema_id, _, required_fields, optional_fields = _kind_contract(kind)
    if not isinstance(schema, Mapping):
        raise RegistryError("E-REGISTRY-SCHEMA", "record schema root must be an object")
    if schema.get("$schema") != JSON_SCHEMA_DRAFT or schema.get("$id") != schema_id:
        raise RegistryError("E-REGISTRY-SCHEMA", "record schema authority is not canonical")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise RegistryError("E-REGISTRY-SCHEMA", "record schema must be a closed object")
    required = schema.get("required")
    properties = schema.get("properties")
    if (
        not isinstance(required, list)
        or any(not isinstance(item, str) for item in required)
        or len(required) != len(set(required))
        or set(required) != set(required_fields)
        or not isinstance(properties, Mapping)
        or any(not isinstance(key, str) for key in properties)
        or set(properties) != set(required_fields | optional_fields)
    ):
        raise RegistryError(
            "E-REGISTRY-SCHEMA", "record schema fields do not match the embedded contract"
        )
    if not isinstance(schema.get("allOf"), list) or not schema["allOf"]:
        raise RegistryError(
            "E-REGISTRY-SCHEMA", "record schema is missing its conditional contracts"
        )
    _freeze_json(schema)


@dataclass(frozen=True, slots=True)
class RegistryRecord:
    kind: str
    record_id: str
    version: str
    payload: Mapping[str, Any]
    record_sha256: str
    boundary: ResearchBoundary = field(default_factory=ResearchBoundary.ring4_open)

    def __post_init__(self) -> None:
        if type(self) is not RegistryRecord:
            raise RegistryError(
                "E-REGISTRY-RECORD", "RegistryRecord subclasses are not accepted"
            )
        _, _, _, id_pattern, _, _ = _kind_contract(self.kind)
        if not isinstance(self.payload, Mapping):
            raise RegistryError("E-REGISTRY-RECORD", "record payload must be a mapping")
        raw_payload = _thaw_json(self.payload)
        if not isinstance(raw_payload, dict):
            raise RegistryError("E-REGISTRY-RECORD", "record payload must be a JSON object")
        if type(self.record_id) is not str or id_pattern.fullmatch(self.record_id) is None:
            raise RegistryError("E-REGISTRY-ID", f"invalid {self.kind} id {self.record_id!r}")
        if type(self.version) is not str or not self.version.strip():
            raise RegistryError("E-REGISTRY-VERSION", "record version must be nonblank")
        try:
            require_canonical_text(self.version, field="record version")
        except CanonicalizationError as exc:
            raise RegistryError("E-REGISTRY-VERSION", str(exc)) from exc
        if raw_payload.get("id") != self.record_id or raw_payload.get("version") != self.version:
            raise RegistryError("E-REGISTRY-IDENTITY", "record identity does not match payload")
        if self.kind == "claim":
            _validate_claim_record(raw_payload)
        else:
            _validate_theorem_record(raw_payload)
        frozen = _freeze_json(raw_payload)
        object.__setattr__(self, "payload", frozen)
        object.__setattr__(
            self,
            "record_sha256",
            _registry_sha(self.record_sha256, field_name="record_sha256"),
        )
        if canonical_json_sha256(frozen) != self.record_sha256:
            raise RegistryError("E-REGISTRY-RECORD-HASH", "record payload digest mismatch")
        if not is_exact_ring4_open(self.boundary):
            raise RegistryError(
                "E-REGISTRY-BOUNDARY", "registry views must remain Ring 4 / OPEN / NOT LICENSED"
            )

    def verify_integrity(self) -> bool:
        if type(self) is not RegistryRecord or not is_exact_ring4_open(self.boundary):
            raise RegistryError("E-REGISTRY-RECORD", "record type or boundary changed")
        raw_payload = _thaw_json(self.payload)
        if not isinstance(raw_payload, dict):
            raise RegistryError("E-REGISTRY-RECORD", "record payload is not an object")
        if raw_payload.get("id") != self.record_id or raw_payload.get("version") != self.version:
            raise RegistryError("E-REGISTRY-IDENTITY", "record identity changed")
        if self.kind == "claim":
            _validate_claim_record(raw_payload)
        elif self.kind == "theorem":
            _validate_theorem_record(raw_payload)
        else:
            raise RegistryError("E-REGISTRY-KIND", "record kind changed")
        if canonical_json_sha256(_freeze_json(raw_payload)) != self.record_sha256:
            raise RegistryError("E-REGISTRY-RECORD-HASH", "record payload digest changed")
        return True

    def to_dict(self) -> dict[str, Any]:
        RegistryRecord.verify_integrity(self)
        return {
            "kind": self.kind,
            "record_id": self.record_id,
            "version": self.version,
            "payload": self.payload,
            "record_sha256": self.record_sha256,
            "boundary": self.boundary.to_dict(),
        }


def _parse_registry_records(kind: str, raw_records: Any) -> tuple[RegistryRecord, ...]:
    if not isinstance(raw_records, list):
        raise RegistryError("E-REGISTRY-RECORDS", "records must be an array")
    parsed: list[RegistryRecord] = []
    for index, record in enumerate(raw_records):
        if not isinstance(record, dict):
            raise RegistryError("E-REGISTRY-RECORD", f"record {index} must be an object")
        if kind == "claim":
            _validate_claim_record(record)
        else:
            _validate_theorem_record(record)
        try:
            record_sha256 = canonical_json_sha256(record)
        except CanonicalizationError as exc:
            raise RegistryError("E-REGISTRY-TEXT", str(exc)) from exc
        parsed.append(
            RegistryRecord(
                kind=kind,
                record_id=record.get("id"),
                version=record.get("version"),
                payload=record,
                record_sha256=record_sha256,
            )
        )
    return tuple(parsed)


def _registry_records_match(
    supplied: tuple[RegistryRecord, ...], expected: tuple[RegistryRecord, ...]
) -> bool:
    if type(supplied) is not tuple or len(supplied) != len(expected):
        return False
    for left, right in zip(supplied, expected):
        if type(left) is not RegistryRecord:
            return False
        RegistryRecord.verify_integrity(left)
        if not (
            left.kind == right.kind
            and left.record_id == right.record_id
            and left.version == right.version
            and left.record_sha256 == right.record_sha256
            and canonical_json_sha256(left.payload)
            == canonical_json_sha256(right.payload)
            and is_exact_ring4_open(left.boundary)
        ):
            return False
    return True


@dataclass(frozen=True, slots=True)
class RecordRegistry:
    kind: str
    schema_version: str
    record_schema: str
    identity: ArtifactIdentity
    pinned_raw_sha256: str
    schema_identity: ArtifactIdentity
    pinned_schema_raw_sha256: str
    schema_document: Mapping[str, Any]
    schema_document_sha256: str
    header: Mapping[str, str]
    records: tuple[RegistryRecord, ...]
    ledger_bytes: bytes = field(repr=False)
    schema_bytes: bytes = field(repr=False)
    boundary: ResearchBoundary = field(default_factory=ResearchBoundary.ring4_open)

    def __post_init__(self) -> None:
        if type(self) is not RecordRegistry:
            raise RegistryError(
                "E-REGISTRY-TYPE", "RecordRegistry subclasses are not accepted"
            )
        expected_version, expected_record_schema, _, _, _, _ = _kind_contract(self.kind)
        if (
            type(self.schema_version) is not str
            or type(self.record_schema) is not str
            or self.schema_version != expected_version
            or self.record_schema != expected_record_schema
        ):
            raise RegistryError("E-REGISTRY-SCHEMA", "registry schema identifiers are not canonical")
        if type(self.identity) is not ArtifactIdentity:
            raise RegistryError("E-REGISTRY-IDENTITY", "registry needs an ArtifactIdentity")
        if type(self.ledger_bytes) is not bytes:
            raise RegistryError("E-REGISTRY-BYTES", "registry needs exact ledger bytes")
        object.__setattr__(
            self,
            "pinned_raw_sha256",
            _registry_sha(self.pinned_raw_sha256, field_name="pinned_raw_sha256"),
        )
        if type(self.schema_identity) is not ArtifactIdentity:
            raise RegistryError("E-REGISTRY-SCHEMA", "record schema needs an ArtifactIdentity")
        if type(self.schema_bytes) is not bytes:
            raise RegistryError("E-REGISTRY-BYTES", "registry needs exact schema bytes")
        object.__setattr__(
            self,
            "pinned_schema_raw_sha256",
            _registry_sha(
                self.pinned_schema_raw_sha256, field_name="pinned_schema_raw_sha256"
            ),
        )
        raw_schema = _thaw_json(self.schema_document)
        _validate_schema_document(raw_schema, kind=self.kind)
        frozen_schema = _freeze_json(raw_schema)
        object.__setattr__(self, "schema_document", frozen_schema)
        object.__setattr__(
            self,
            "schema_document_sha256",
            _registry_sha(self.schema_document_sha256, field_name="schema_document_sha256"),
        )
        raw_header = _thaw_json(self.header)
        _validate_header(raw_header)
        object.__setattr__(self, "header", _freeze_json(raw_header))
        if type(self.records) is not tuple or any(
            type(record) is not RegistryRecord for record in self.records
        ):
            raise RegistryError("E-REGISTRY-RECORDS", "records must be an immutable typed tuple")
        identities: set[tuple[str, str]] = set()
        for record in self.records:
            if record.kind != self.kind:
                raise RegistryError(
                    "E-REGISTRY-KIND", "registry contains a record of a different kind"
                )
            key = (record.record_id, record.version)
            if key in identities:
                raise RegistryError(
                    "E-REGISTRY-DUPLICATE-RECORD",
                    f"duplicate record identity {record.record_id}@{record.version}",
                )
            identities.add(key)
        if not is_exact_ring4_open(self.boundary):
            raise RegistryError(
                "E-REGISTRY-BOUNDARY", "registry artifacts must remain Ring 4 / OPEN / NOT LICENSED"
            )
        RecordRegistry.verify_raw_bindings(self)

    def verify_raw_bindings(self) -> bool:
        """Reconstruct every parsed view from retained exact ledger/schema bytes."""

        if type(self) is not RecordRegistry:
            raise RegistryError("E-REGISTRY-TYPE", "registry type changed")
        if (
            type(self.kind) is not str
            or type(self.schema_version) is not str
            or type(self.record_schema) is not str
            or type(self.pinned_raw_sha256) is not str
            or type(self.pinned_schema_raw_sha256) is not str
            or type(self.schema_document_sha256) is not str
        ):
            raise RegistryError("E-REGISTRY-TYPE", "registry primitive types changed")
        if type(self.ledger_bytes) is not bytes or type(self.schema_bytes) is not bytes:
            raise RegistryError("E-REGISTRY-BYTES", "retained raw bytes are missing")
        ledger_identity = ArtifactIdentity.from_bytes(self.ledger_bytes)
        schema_identity = ArtifactIdentity.from_bytes(self.schema_bytes)
        if not artifact_identities_match(ledger_identity, self.identity):
            raise RegistryError(
                "E-REGISTRY-RAW-BINDING", "ledger bytes do not match registry identity"
            )
        if not artifact_identities_match(schema_identity, self.schema_identity):
            raise RegistryError(
                "E-REGISTRY-SCHEMA-RAW-BINDING",
                "schema bytes do not match schema identity",
            )
        if ledger_identity.raw_sha256 != self.pinned_raw_sha256:
            raise RegistryError(
                "E-REGISTRY-HASH", "ledger bytes do not match the external expected pin"
            )
        if schema_identity.raw_sha256 != self.pinned_schema_raw_sha256:
            raise RegistryError(
                "E-REGISTRY-SCHEMA-HASH",
                "schema bytes do not match the external expected pin",
            )

        data = _decode_json_bytes(self.ledger_bytes, label="retained ledger bytes")
        schema = _decode_json_bytes(self.schema_bytes, label="retained schema bytes")
        expected_version, expected_record_schema, _, _, _, _ = _kind_contract(self.kind)
        if set(data) != LEDGER_ROOT_FIELDS:
            raise RegistryError(
                "E-REGISTRY-ROOT-SCHEMA", "retained ledger root fields are not canonical"
            )
        if (
            data.get("schema_version") != expected_version
            or data.get("record_schema") != expected_record_schema
            or self.schema_version != expected_version
            or self.record_schema != expected_record_schema
        ):
            raise RegistryError(
                "E-REGISTRY-SCHEMA", "retained ledger schema identifiers changed"
            )
        _validate_schema_document(schema, kind=self.kind)
        expected_header = {
            "document_status": data["document_status"],
            "as_of": data["as_of"],
            "completeness": data["completeness"],
        }
        _validate_header(expected_header)
        supplied_header = _thaw_json(self.header)
        if canonical_json_bytes(supplied_header) != canonical_json_bytes(expected_header):
            raise RegistryError(
                "E-REGISTRY-RAW-BINDING", "header does not reconstruct from ledger bytes"
            )
        supplied_schema = _thaw_json(self.schema_document)
        if canonical_json_bytes(supplied_schema) != canonical_json_bytes(schema):
            raise RegistryError(
                "E-REGISTRY-SCHEMA-RAW-BINDING",
                "schema document does not reconstruct from schema bytes",
            )
        expected_schema_sha256 = canonical_json_sha256(_freeze_json(schema))
        if self.schema_document_sha256 != expected_schema_sha256:
            raise RegistryError(
                "E-REGISTRY-SCHEMA-HASH", "canonical schema digest changed"
            )
        expected_records = _parse_registry_records(self.kind, data["records"])
        if not _registry_records_match(self.records, expected_records):
            raise RegistryError(
                "E-REGISTRY-RAW-BINDING", "records do not reconstruct from ledger bytes"
            )
        if not is_exact_ring4_open(self.boundary):
            raise RegistryError("E-REGISTRY-BOUNDARY", "registry boundary changed")
        return True

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        kind: str,
        expected_raw_sha256: str,
        expected_schema_raw_sha256: str,
        schema_path: str | Path | None = None,
    ) -> "RecordRegistry":
        expected_version, expected_record_schema, _, _, _, _ = _kind_contract(kind)
        expected = _registry_sha(expected_raw_sha256, field_name="expected_raw_sha256")
        expected_schema = _registry_sha(
            expected_schema_raw_sha256, field_name="expected_schema_raw_sha256"
        )
        ledger_path = Path(path)
        data, identity, ledger_bytes = _read_json(ledger_path)
        if identity.raw_sha256 != expected:
            raise RegistryError(
                "E-REGISTRY-HASH",
                f"raw SHA-256 {identity.raw_sha256} does not match {expected}",
            )
        if set(data) != LEDGER_ROOT_FIELDS:
            missing = sorted(LEDGER_ROOT_FIELDS - set(data))
            extra = sorted(set(data) - LEDGER_ROOT_FIELDS)
            raise RegistryError(
                "E-REGISTRY-ROOT-SCHEMA",
                f"registry root mismatch; missing={missing}, extra={extra}",
            )
        if data["schema_version"] != expected_version or data["record_schema"] != expected_record_schema:
            raise RegistryError("E-REGISTRY-SCHEMA", "registry schema identifiers are not canonical")
        header = {
            "document_status": data["document_status"],
            "as_of": data["as_of"],
            "completeness": data["completeness"],
        }
        _validate_header(header)

        selected_schema_path = (
            Path(schema_path) if schema_path is not None else ledger_path.parent / expected_record_schema
        )
        schema_document, schema_identity, schema_bytes = _read_json(selected_schema_path)
        if schema_identity.raw_sha256 != expected_schema:
            raise RegistryError(
                "E-REGISTRY-SCHEMA-HASH",
                f"schema raw SHA-256 {schema_identity.raw_sha256} does not match {expected_schema}",
            )
        _validate_schema_document(schema_document, kind=kind)

        parsed = _parse_registry_records(kind, data["records"])
        return cls(
            kind=kind,
            schema_version=expected_version,
            record_schema=expected_record_schema,
            identity=identity,
            pinned_raw_sha256=expected,
            schema_identity=schema_identity,
            pinned_schema_raw_sha256=expected_schema,
            schema_document=schema_document,
            schema_document_sha256=canonical_json_sha256(schema_document),
            header=header,
            records=parsed,
            ledger_bytes=ledger_bytes,
            schema_bytes=schema_bytes,
        )

    def resolve(self, record_id: str, *, version: str | None = None) -> RegistryRecord:
        RecordRegistry.verify_raw_bindings(self)
        matches = [
            record
            for record in self.records
            if record.record_id == record_id
            and (version is None or record.version == version)
        ]
        if not matches:
            raise RegistryError(
                "E-REGISTRY-NOT-FOUND",
                f"no {self.kind} record for {record_id}" + (f"@{version}" if version else ""),
            )
        if len(matches) != 1:
            raise RegistryError(
                "E-REGISTRY-AMBIGUOUS",
                f"{record_id} has multiple versions; an exact version is required",
            )
        return matches[0]

    def to_dict(self) -> dict[str, Any]:
        RecordRegistry.verify_raw_bindings(self)
        return {
            "kind": self.kind,
            "schema_version": self.schema_version,
            "record_schema": self.record_schema,
            "identity": self.identity.to_dict(),
            "pinned_raw_sha256": self.pinned_raw_sha256,
            "schema_identity": self.schema_identity.to_dict(),
            "pinned_schema_raw_sha256": self.pinned_schema_raw_sha256,
            "schema_document": self.schema_document,
            "schema_document_sha256": self.schema_document_sha256,
            "header": self.header,
            "records": [record.to_dict() for record in self.records],
            "boundary": self.boundary.to_dict(),
        }


def claim_is_licensed(record: RegistryRecord) -> bool:
    """Return descriptive ledger status only; this never authorizes an action."""

    if type(record) is not RegistryRecord or record.kind != "claim":
        return False
    RegistryRecord.verify_integrity(record)
    payload = record.payload
    return bool(
        payload.get("product_claim_status") == "LICENSED"
        and payload.get("review_state") == "REVIEWED"
        and payload.get("admission_ring") == 3
        and payload.get("evidence_packets")
        and payload.get("reviewers")
        and isinstance(payload.get("last_reviewed_at"), str)
    )
