#!/usr/bin/env python3
"""Read-only, fail-closed intake for external Stage C prerequisite evidence.

This command reconstructs the already-defined Stage C factory context from one
canonical locator and exact local artifact files.  It does not create evidence,
grant authority, contact a provider, consume a nonce, or write an output file.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
from typing import Any, Mapping, Sequence

# A read-only CLI must not leave import cache files beside repository sources.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import (  # noqa: E402
    canonical_json_bytes,
    canonical_sha256,
    load_json_object,
)
from cas_harness_v2._validation import (  # noqa: E402
    ArtifactRef,
    SchemaValidationError,
    expect_keys,
    expect_list,
    expect_sha256,
    parse_artifact_ref,
)
from cas_harness_v2.artifacts import EvidenceBytes, EvidenceFile  # noqa: E402
from cas_harness_v2.diagnostic_prompt_context_inventory import (  # noqa: E402
    STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE,
    StageCPromptContextReplayBundle,
    load_stagec_prompt_context_inventory,
)
from cas_harness_v2.diagnostic_prompt_context_provenance import (  # noqa: E402
    SOURCE,
    STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE,
    STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    load_stagec_prompt_context_node,
    load_stagec_prompt_context_provenance,
)
from cas_harness_v2.diagnostic_stagec_prerequisite_admission import (  # noqa: E402
    StageCPrerequisiteFactoryContext,
    build_stagec_prerequisite_factory_context,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    DIAGNOSTIC_CASE_COUNT,
    DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    load_diagnostic_split_inventory,
    load_stagec_capture_request,
)


CONTEXT_LOCATOR_SCHEMA = (
    "cas_harness_v2.stagec_prerequisite_context_locator.v1"
)
CONTEXT_LOCATOR_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prerequisite-context-locator+json"
)
REPORT_SCHEMA = "cas_harness_v2.stagec_prerequisite_external_cli_report.v1"
REPORT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prerequisite-external-cli-report+json"
)
FAIL_CLOSED_STATUS = "FAIL_CLOSED_NON_AUTHORITY"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_LOCATOR = 3
EXIT_CONTEXT = 4
EXIT_SNAPSHOT = 5
EXIT_BINDING = 6

_LOCATOR_KEYS = {
    "schema_version",
    "split_inventory",
    "prompt_context_inventory",
    "external_prerequisite_locator",
    "model_identity_sha256",
    "capture_profile_sha256",
    "members",
}
_MEMBER_KEYS = {"artifact", "relative_path"}
# The external library requires its fixed locator plus the exact 4 carrier and
# 12 dependency files.  The outer context locator binds all 17 as ordinary,
# stable members; no manifest is synthesized or written by this command.
_EXTERNAL_ARTIFACT_COUNT = 17
MAXIMUM_INPUT_FILE_BYTES = 2_000_000
_RELATIVE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_DOS_DEVICE_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


class IntakeCLIError(ValueError):
    """A deterministic, redacted intake failure."""

    def __init__(self, code: str, exit_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.exit_code = exit_code


@dataclass(frozen=True, slots=True)
class _Arguments:
    locator: Path
    owner_intake: Path | None
    admission: Path | None


@dataclass(frozen=True, slots=True)
class _Member:
    reference: ArtifactRef
    relative_path: str
    source: EvidenceFile
    raw_bytes: bytes


@dataclass(frozen=True, slots=True)
class _Reconstructed:
    context: StageCPrerequisiteFactoryContext
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...]
    external_members: tuple[_Member, ...]
    external_locator: ArtifactRef
    locator_sha256: str
    locator_byte_length: int
    context_artifact_count: int
    member_count: int


def _ref_value(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _parse_arguments(argv: Sequence[str]) -> _Arguments:
    values: dict[str, str] = {}
    index = 0
    allowed = {"--locator", "--owner-intake", "--admission"}
    while index < len(argv):
        option = argv[index]
        if option not in allowed or option in values or index + 1 >= len(argv):
            raise IntakeCLIError("INVALID_ARGUMENTS", EXIT_USAGE)
        value = argv[index + 1]
        if not value or value.startswith("--"):
            raise IntakeCLIError("INVALID_ARGUMENTS", EXIT_USAGE)
        values[option] = value
        index += 2
    if "--locator" not in values:
        raise IntakeCLIError("LOCATOR_REQUIRED", EXIT_USAGE)
    owner = values.get("--owner-intake")
    admission = values.get("--admission")
    if (owner is None) != (admission is None):
        raise IntakeCLIError("BINDING_INPUT_PAIR_REQUIRED", EXIT_USAGE)
    return _Arguments(
        locator=_absolute_local_input_path(values["--locator"]),
        owner_intake=None if owner is None else _absolute_local_input_path(owner),
        admission=None if admission is None else _absolute_local_input_path(admission),
    )


def _absolute_local_input_path(value: str) -> Path:
    """Reject ambient-CWD, UNC/device, and mapped-network input before access."""

    if type(value) is not str or not value or "\x00" in value:
        raise IntakeCLIError("ABSOLUTE_LOCAL_PATH_REQUIRED", EXIT_USAGE)
    normalized_slashes = value.replace("/", "\\")
    if normalized_slashes.startswith("\\\\"):
        raise IntakeCLIError("ABSOLUTE_LOCAL_PATH_REQUIRED", EXIT_USAGE)
    path = Path(value)
    if not path.is_absolute():
        raise IntakeCLIError("ABSOLUTE_LOCAL_PATH_REQUIRED", EXIT_USAGE)
    if os.name == "nt":
        import ctypes

        # GetDriveTypeW performs no file open.  Only explicitly local Windows
        # volume types are admitted; DRIVE_REMOTE and unresolved roots close.
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor))
        if drive_type not in {2, 3, 5, 6}:  # removable, fixed, CD-ROM, RAM disk
            raise IntakeCLIError("ABSOLUTE_LOCAL_PATH_REQUIRED", EXIT_USAGE)
    return path


def _snapshot_evidence_file(source: EvidenceFile) -> bytes:
    """Return one exact, fixed-bound snapshot through the sole evidence API."""

    if type(source) is not EvidenceFile or source.byte_length > MAXIMUM_INPUT_FILE_BYTES:
        raise SchemaValidationError("stable file exceeds the closed intake byte bound")
    result = source.snapshot_bytes(maximum_byte_count=MAXIMUM_INPUT_FILE_BYTES)
    if type(result) is not EvidenceBytes or type(result.raw_bytes) is not bytes:
        raise SchemaValidationError("stable file snapshot has the wrong exact type")
    return result.raw_bytes


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    snapshot, value = load_json_object(raw)
    if snapshot != canonical_json_bytes(value):
        raise SchemaValidationError(f"{label} is not canonical JSON")
    return value


def _safe_relative_path(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 512
        or "\x00" in value
        or "\\" in value
    ):
        raise SchemaValidationError("member relative_path is not canonical POSIX text")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or value != candidate.as_posix()
        or any(part in ("", ".", "..") for part in candidate.parts)
        or any(":" in part for part in candidate.parts)
        or any(_RELATIVE_SEGMENT.fullmatch(part) is None for part in candidate.parts)
        or any(part.endswith(".") for part in candidate.parts)
        or any(
            part.split(".", 1)[0].upper() in _DOS_DEVICE_BASENAMES
            for part in candidate.parts
        )
    ):
        raise SchemaValidationError("member relative_path escapes its locator directory")
    return value


def _require_media(reference: ArtifactRef, media_type: str, label: str) -> ArtifactRef:
    if reference.media_type != media_type:
        raise SchemaValidationError(f"{label} has the wrong exact media type")
    return reference


def _member_for(
    members: Mapping[str, _Member],
    reference: ArtifactRef,
    *,
    media_type: str | None = None,
) -> _Member:
    member = members.get(reference.artifact_id)
    if member is None or member.reference != reference:
        raise SchemaValidationError("an exact referenced artifact is missing")
    if media_type is not None:
        _require_media(reference, media_type, reference.artifact_id)
    return member


def _parse_ref_list(value: object, path: str) -> tuple[ArtifactRef, ...]:
    items = expect_list(value, path, nonempty=True)
    return tuple(parse_artifact_ref(item, f"{path}[{index}]") for index, item in enumerate(items))


def _load_locator(locator_path: Path) -> tuple[
    dict[str, Any],
    tuple[_Member, ...],
    str,
    int,
]:
    locator_source = EvidenceFile.from_path(
        "stagec-prerequisite-context-locator-input",
        locator_path,
        maximum_byte_count=MAXIMUM_INPUT_FILE_BYTES,
    )
    locator_raw = _snapshot_evidence_file(locator_source)
    value = _canonical_object(locator_raw, "Stage C context locator")
    expect_keys(value, required=_LOCATOR_KEYS, path="$")
    if value["schema_version"] != CONTEXT_LOCATOR_SCHEMA:
        raise SchemaValidationError("wrong Stage C context-locator schema")
    expect_sha256(value["model_identity_sha256"], "$.model_identity_sha256")
    expect_sha256(value["capture_profile_sha256"], "$.capture_profile_sha256")
    split_ref = parse_artifact_ref(value["split_inventory"], "$.split_inventory")
    prompt_ref = parse_artifact_ref(
        value["prompt_context_inventory"],
        "$.prompt_context_inventory",
    )
    external_locator_ref = parse_artifact_ref(
        value["external_prerequisite_locator"],
        "$.external_prerequisite_locator",
    )
    from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE,
    )

    _require_media(split_ref, DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE, "split root")
    _require_media(
        prompt_ref,
        STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE,
        "prompt-context root",
    )
    _require_media(
        external_locator_ref,
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE,
        "external-prerequisite locator root",
    )

    member_values = expect_list(value["members"], "$.members", nonempty=True)
    parsed: list[tuple[ArtifactRef, str]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_content: dict[tuple[str, int], str] = {}
    for index, item in enumerate(member_values):
        if type(item) is not dict:
            raise SchemaValidationError(f"$.members[{index}] must be an exact object")
        expect_keys(item, required=_MEMBER_KEYS, path=f"$.members[{index}]")
        reference = parse_artifact_ref(item["artifact"], f"$.members[{index}].artifact")
        relative_path = _safe_relative_path(item["relative_path"])
        folded = relative_path.casefold()
        if reference.artifact_id in seen_ids:
            raise SchemaValidationError("locator contains a duplicate artifact identifier")
        if folded in seen_paths:
            raise SchemaValidationError("locator contains duplicate or case-colliding paths")
        content_key = (reference.sha256, reference.byte_length)
        if content_key in seen_content:
            raise SchemaValidationError("locator clones content under another artifact identifier")
        seen_ids.add(reference.artifact_id)
        seen_paths.add(folded)
        seen_content[content_key] = reference.artifact_id
        parsed.append((reference, relative_path))
    if [item[0].artifact_id for item in parsed] != sorted(seen_ids):
        raise SchemaValidationError("locator member table is not in canonical artifact-ID order")
    if (
        split_ref.artifact_id not in seen_ids
        or prompt_ref.artifact_id not in seen_ids
        or external_locator_ref.artifact_id not in seen_ids
    ):
        raise SchemaValidationError("locator root refs are absent from its exact member table")

    base = locator_source.path.parent
    locator_casefold = str(locator_source.path).casefold()
    sources: list[tuple[ArtifactRef, str, EvidenceFile]] = []
    for reference, relative_path in parsed:
        path = base.joinpath(*PurePosixPath(relative_path).parts)
        if str(path.absolute()).casefold() == locator_casefold:
            raise SchemaValidationError("locator cannot also be an artifact member")
        source = EvidenceFile.from_path(
            reference.artifact_id,
            path,
            maximum_byte_count=MAXIMUM_INPUT_FILE_BYTES,
        )
        if source.sha256 != reference.sha256 or source.byte_length != reference.byte_length:
            raise SchemaValidationError("artifact file differs from its locator reference")
        sources.append((reference, relative_path, source))

    members = tuple(
        _Member(
            reference=reference,
            relative_path=relative_path,
            source=source,
            raw_bytes=_snapshot_evidence_file(source),
        )
        for reference, relative_path, source in sources
    )
    if not locator_source.verify_current() or any(
        not member.source.verify_current() for member in members
    ):
        raise SchemaValidationError("locator input changed during snapshot")
    return value, members, locator_source.sha256, locator_source.byte_length


def reconstruct_context(locator_path: Path) -> _Reconstructed:
    """Reconstruct context and isolate one fixed locator plus exact 4+12 inputs."""

    value, member_tuple, locator_sha, locator_length = _load_locator(locator_path)
    members = {member.reference.artifact_id: member for member in member_tuple}
    split_ref = parse_artifact_ref(value["split_inventory"], "$.split_inventory")
    prompt_ref = parse_artifact_ref(
        value["prompt_context_inventory"],
        "$.prompt_context_inventory",
    )
    external_locator_ref = parse_artifact_ref(
        value["external_prerequisite_locator"],
        "$.external_prerequisite_locator",
    )

    split_member = _member_for(
        members,
        split_ref,
        media_type=DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    )
    split_value = _canonical_object(split_member.raw_bytes, "diagnostic split inventory")
    ordered_cases = expect_list(split_value.get("ordered_cases"), "$.ordered_cases", nonempty=True)
    if len(ordered_cases) != DIAGNOSTIC_CASE_COUNT:
        raise SchemaValidationError("split does not contain exact Stage C case cardinality")
    capture_refs: list[ArtifactRef] = []
    for index, case in enumerate(ordered_cases):
        if type(case) is not dict:
            raise SchemaValidationError("split ordered case is not an exact object")
        capture_ref = parse_artifact_ref(
            case.get("capture_request"),
            f"$.ordered_cases[{index}].capture_request",
        )
        _require_media(capture_ref, STAGEC_CAPTURE_REQUEST_MEDIA_TYPE, "capture request")
        capture_refs.append(capture_ref)
    if len({item.artifact_id for item in capture_refs}) != DIAGNOSTIC_CASE_COUNT:
        raise SchemaValidationError("capture-request closure is not exact and unique")
    captures = tuple(
        load_stagec_capture_request(
            reference,
            _member_for(
                members,
                reference,
                media_type=STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
            ).raw_bytes,
        )
        for reference in capture_refs
    )
    split = load_diagnostic_split_inventory(
        split_member.raw_bytes,
        capture_requests=captures,
    )
    if split.artifact_ref != split_ref:
        raise SchemaValidationError("split root reference differs from strict replay")

    prompt_member = _member_for(
        members,
        prompt_ref,
        media_type=STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE,
    )
    prompt_value = _canonical_object(
        prompt_member.raw_bytes,
        "Stage C prompt-context inventory",
    )
    ordered_contexts = expect_list(
        prompt_value.get("ordered_contexts"),
        "$.ordered_contexts",
        nonempty=True,
    )
    if len(ordered_contexts) != DIAGNOSTIC_CASE_COUNT:
        raise SchemaValidationError("prompt-context inventory has the wrong row count")

    bundles: list[StageCPromptContextReplayBundle] = []
    context_ids = {split_ref.artifact_id, prompt_ref.artifact_id}
    context_ids.update(item.artifact_id for item in capture_refs)
    node_cache: dict[str, Any] = {}
    for index, (row, capture) in enumerate(zip(ordered_contexts, captures, strict=True)):
        if type(row) is not dict:
            raise SchemaValidationError("prompt-context row is not an exact object")
        row_capture = parse_artifact_ref(
            row.get("capture_request"),
            f"$.ordered_contexts[{index}].capture_request",
        )
        if row_capture != capture.artifact_ref:
            raise SchemaValidationError("prompt-context row capture order drifted")
        provenance_ref = parse_artifact_ref(
            row.get("prompt_context_provenance"),
            f"$.ordered_contexts[{index}].prompt_context_provenance",
        )
        _require_media(
            provenance_ref,
            STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE,
            "prompt-context provenance",
        )
        provenance_member = _member_for(members, provenance_ref)
        provenance_value = _canonical_object(
            provenance_member.raw_bytes,
            "Stage C prompt-context provenance",
        )
        if parse_artifact_ref(
            provenance_value.get("capture_request"),
            "$.capture_request",
        ) != capture.artifact_ref:
            raise SchemaValidationError("provenance capture request drifted")
        node_refs = _parse_ref_list(
            provenance_value.get("ordered_node_closure"),
            "$.ordered_node_closure",
        )
        nodes: list[Any] = []
        source_refs: list[ArtifactRef] = []
        for node_ref in node_refs:
            _require_media(node_ref, STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE, "prompt node")
            node = node_cache.get(node_ref.artifact_id)
            if node is None:
                node_member = _member_for(members, node_ref)
                node = load_stagec_prompt_context_node(node_ref, node_member.raw_bytes)
                node_cache[node_ref.artifact_id] = node
            elif node.artifact_ref != node_ref:
                raise SchemaValidationError("one prompt node ID binds conflicting refs")
            nodes.append(node)
            context_ids.add(node_ref.artifact_id)
            if node.operation == SOURCE:
                if node.source_artifact is None:
                    raise SchemaValidationError("SOURCE node has no exact source ref")
                source_refs.append(node.source_artifact)
        source_bodies: list[tuple[ArtifactRef, bytes]] = []
        seen_source_ids: set[str] = set()
        for source_ref in source_refs:
            if source_ref.artifact_id in seen_source_ids:
                continue
            _require_media(source_ref, STAGEC_PROMPT_SOURCE_MEDIA_TYPE, "prompt source")
            source_member = _member_for(members, source_ref)
            source_bodies.append((source_ref, source_member.raw_bytes))
            seen_source_ids.add(source_ref.artifact_id)
            context_ids.add(source_ref.artifact_id)
        provenance = load_stagec_prompt_context_provenance(
            provenance_member.raw_bytes,
            capture_request=capture,
            ordered_nodes=tuple(nodes),
            source_bodies=tuple(source_bodies),
        )
        if provenance.artifact_ref != provenance_ref:
            raise SchemaValidationError("provenance ref differs from strict replay")
        row_root = parse_artifact_ref(row.get("root_node"), f"$.ordered_contexts[{index}].root_node")
        if provenance.root_node != row_root:
            raise SchemaValidationError("prompt-context row root differs from provenance")
        context_ids.add(provenance_ref.artifact_id)
        bundles.append(
            StageCPromptContextReplayBundle(
                provenance=provenance,
                ordered_nodes=tuple(nodes),
                source_bodies=tuple(source_bodies),
            )
        )

    replay_bundles = tuple(bundles)
    prompt_inventory = load_stagec_prompt_context_inventory(
        prompt_member.raw_bytes,
        split_inventory=split,
        replay_bundles=replay_bundles,
    )
    if prompt_inventory.artifact_ref != prompt_ref:
        raise SchemaValidationError("prompt inventory root differs from strict replay")
    context = build_stagec_prerequisite_factory_context(
        split_inventory=split,
        prompt_inventory=prompt_inventory,
        replay_bundles=replay_bundles,
        model_identity_sha256=value["model_identity_sha256"],
        capture_profile_sha256=value["capture_profile_sha256"],
    )

    external = tuple(member for member in member_tuple if member.reference.artifact_id not in context_ids)
    if len(external) != _EXTERNAL_ARTIFACT_COUNT:
        raise SchemaValidationError(
            "locator does not isolate one external locator plus exact 4+12 closure"
        )
    if len(context_ids) + len(external) != len(member_tuple):
        raise SchemaValidationError("locator has missing or extra artifact members")
    external_locator_member = _member_for(members, external_locator_ref)
    if external_locator_member not in external:
        raise SchemaValidationError("external locator root overlaps the context closure")
    from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME,
    )

    if (
        external_locator_member.relative_path
        != STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME
    ):
        raise SchemaValidationError("external locator root does not use its fixed path")
    if any(not member.source.verify_current() for member in member_tuple):
        raise SchemaValidationError("an artifact mutated during context reconstruction")
    return _Reconstructed(
        context=context,
        replay_bundles=replay_bundles,
        external_members=external,
        external_locator=external_locator_ref,
        locator_sha256=locator_sha,
        locator_byte_length=locator_length,
        context_artifact_count=len(context_ids),
        member_count=len(member_tuple),
    )


def _external_source(reconstructed: _Reconstructed) -> object:
    """Adapt locator members to the external-intake library's exact source type."""

    from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME,
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE,
    )

    by_id = {
        member.reference.artifact_id: member
        for member in reconstructed.external_members
    }
    manifest = by_id.get(reconstructed.external_locator.artifact_id)
    if (
        manifest is None
        or manifest.reference != reconstructed.external_locator
        or manifest.reference.media_type
        != STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE
        or manifest.relative_path
        != STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME
    ):
        raise SchemaValidationError("the fixed external locator member is not exact")
    return {
        member.relative_path: member.source
        for member in reconstructed.external_members
    }


def _load_snapshot(reconstructed: _Reconstructed) -> object:
    from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (
        load_stagec_external_prerequisite_snapshot,
    )

    snapshot = load_stagec_external_prerequisite_snapshot(
        _external_source(reconstructed),
        context=reconstructed.context,
    )
    expected = {member.reference for member in reconstructed.external_members}
    actual = {
        getattr(snapshot, "manifest_artifact_ref"),
        *(item.artifact_ref for item in getattr(snapshot, "roles")),
    }
    if actual != expected:
        raise SchemaValidationError(
            "library snapshot ref set differs from the outer exact member table"
        )
    if getattr(snapshot, "manifest_artifact_ref") != reconstructed.external_locator:
        raise SchemaValidationError(
            "library snapshot locator differs from the exact outer root ref"
        )
    return snapshot


def _load_binding(
    reconstructed: _Reconstructed,
    snapshot: object,
    *,
    owner_intake_raw: bytes,
    admission_raw: bytes,
) -> object:
    from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (
        load_stagec_external_prerequisite_binding,
    )

    return load_stagec_external_prerequisite_binding(
        snapshot,
        intake_bytes=owner_intake_raw,
        admission_bytes=admission_raw,
        replay_bundles=reconstructed.replay_bundles,
        context=reconstructed.context,
    )


def _optional_input(path: Path, artifact_id: str) -> bytes:
    return _snapshot_evidence_file(
        EvidenceFile.from_path(
            artifact_id,
            path,
            maximum_byte_count=MAXIMUM_INPUT_FILE_BYTES,
        )
    )


def _failure(code: str, exit_code: int) -> dict[str, object]:
    return {
        "schema_version": REPORT_SCHEMA,
        "status": FAIL_CLOSED_STATUS,
        "exit_code": exit_code,
        "authority": "NON_AUTHORITY",
        "failure": {"code": code, "details": "REDACTED"},
        "side_effects": {
            "files_written": 0,
            "network_requests": 0,
            "provider_actions": 0,
            "nonces_created_or_consumed": 0,
        },
    }


def _success(
    reconstructed: _Reconstructed,
    *,
    snapshot: object,
    binding: object | None,
) -> dict[str, object]:
    from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE,
    )

    external_refs = tuple(item.artifact_ref for item in getattr(snapshot, "roles"))
    closure = canonical_sha256(
        {
            "domain": "cas_harness_v2.stagec_external_prerequisite_locator_closure.v1",
            "ordered_artifacts": [_ref_value(reference) for reference in external_refs],
        }
    )
    snapshot_report_raw = getattr(snapshot, "report_raw_bytes")
    snapshot_report = _canonical_object(
        snapshot_report_raw,
        "external prerequisite snapshot report",
    )
    snapshot_report_ref = getattr(snapshot, "report_artifact_ref")
    binding_requested = binding is not None
    binding_value: dict[str, object] = {
        "requested": binding_requested,
        "loaded": binding_requested,
        "semantics": "CALLER_SUPPLIED_BYTES_ONLY" if binding_requested else "NOT_REQUESTED",
    }
    if binding is not None:
        binding_report = _canonical_object(
            getattr(binding, "report_raw_bytes"),
            "external prerequisite binding report",
        )
        binding_value["report"] = _ref_value(getattr(binding, "report_artifact_ref"))
        binding_value["status"] = binding_report["status"]
    return {
        "schema_version": REPORT_SCHEMA,
        "status": snapshot_report["status"],
        "exit_code": EXIT_OK,
        "authority": "NON_AUTHORITY",
        "gate_status": snapshot_report["authority"],
        "external_trust_authentication": snapshot_report[
            "external_trust_authentication"
        ],
        "runtime_authorization": snapshot_report["runtime_authorization"],
        "context": {
            "target_binding_sha256": reconstructed.context.target_binding_sha256,
            "capture_request_count": len(reconstructed.context.split_inventory.capture_requests),
            "replay_bundle_count": len(reconstructed.replay_bundles),
            "context_artifact_count": reconstructed.context_artifact_count,
            "member_count": reconstructed.member_count,
            "locator_sha256": reconstructed.locator_sha256,
            "locator_byte_length": reconstructed.locator_byte_length,
        },
        "snapshot": {
            "loaded": True,
            "report": _ref_value(snapshot_report_ref),
            "candidate_count": 4,
            "dependency_count": 12,
            "artifact_count": len(external_refs),
            "locator_closure_sha256": closure,
            "semantics": "STRUCTURAL_REPLAY_ONLY",
        },
        "binding": binding_value,
        "side_effects": {
            "files_written": 0,
            "network_requests": 0,
            "provider_actions": 0,
            "nonces_created_or_consumed": 0,
        },
    }


def _emit(report: Mapping[str, object]) -> None:
    sys.stdout.write(canonical_json_bytes(dict(report)).decode("utf-8") + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    if not sys.flags.isolated or not sys.flags.dont_write_bytecode:
        _emit(_failure("ISOLATED_READ_ONLY_RUNTIME_REQUIRED", EXIT_USAGE))
        return EXIT_USAGE
    try:
        arguments = _parse_arguments(tuple(sys.argv[1:] if argv is None else argv))
    except IntakeCLIError as exc:
        _emit(_failure(exc.code, exc.exit_code))
        return exc.exit_code
    try:
        reconstructed = reconstruct_context(arguments.locator)
    except Exception:
        _emit(_failure("CONTEXT_LOCATOR_OR_REPLAY_REJECTED", EXIT_CONTEXT))
        return EXIT_CONTEXT
    try:
        snapshot = _load_snapshot(reconstructed)
    except Exception as exc:
        error_code = getattr(exc, "error_code", "EXTERNAL_PREREQUISITE_SNAPSHOT_REJECTED")
        _emit(_failure(error_code, EXIT_SNAPSHOT))
        return EXIT_SNAPSHOT
    binding_requested = arguments.owner_intake is not None
    binding: object | None = None
    if binding_requested:
        assert arguments.owner_intake is not None and arguments.admission is not None
        try:
            owner_raw = _optional_input(arguments.owner_intake, "stagec-owner-intake-cli-input")
            admission_raw = _optional_input(arguments.admission, "stagec-admission-cli-input")
            binding = _load_binding(
                reconstructed,
                snapshot,
                owner_intake_raw=owner_raw,
                admission_raw=admission_raw,
            )
        except Exception as exc:
            error_code = getattr(exc, "error_code", "EXTERNAL_PREREQUISITE_BINDING_REJECTED")
            _emit(_failure(error_code, EXIT_BINDING))
            return EXIT_BINDING
    try:
        report = _success(reconstructed, snapshot=snapshot, binding=binding)
    except Exception:
        _emit(_failure("SUCCESS_REPORT_RECONSTRUCTION_REJECTED", EXIT_SNAPSHOT))
        return EXIT_SNAPSHOT
    _emit(report)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
