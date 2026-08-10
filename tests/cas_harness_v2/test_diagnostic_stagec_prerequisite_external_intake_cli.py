from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes  # noqa: E402
from cas_harness_v2._validation import ArtifactRef  # noqa: E402
from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (  # noqa: E402
    STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS,
    STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME,
    STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE,
    STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_SCHEMA,
    STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER,
)
from scripts import import_project_coherence_stagec_prerequisites as cli  # noqa: E402
from test_diagnostic_stagec_prerequisite_admission import build_fx  # noqa: E402


SCRIPT = ROOT / "scripts" / "import_project_coherence_stagec_prerequisites.py"


def _rv(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _ref(artifact_id: str, raw: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=media_type,
    )


def _external_manifest_ref(raw: bytes) -> ArtifactRef:
    digest = sha256_bytes(raw)
    return _ref(
        f"stagec-external-locator-{digest.lower()}",
        raw,
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE,
    )


@dataclass(frozen=True)
class Materialized:
    root: Path
    locator: Path
    external_manifest: Path
    intake: Path
    admission: Path
    target_binding_sha256: str


def _external_role_bodies(fx: object) -> dict[str, tuple[ArtifactRef, bytes]]:
    result: dict[str, tuple[ArtifactRef, bytes]] = {
        "detector_drc": (fx.drc.artifact_ref, fx.drc.raw_bytes),
        "frozen_corpus": (fx.corpus.artifact_ref, fx.corpus.raw_bytes),
        "trusted_storage": (fx.storage.artifact_ref, fx.storage.raw_bytes),
        "execution_authorization": (
            fx.authorization.artifact_ref,
            fx.authorization.raw_bytes,
        ),
    }
    for name, pair in zip(
        ("drc_profile", "detector_ruleset", "known_fault_fixture"),
        fx.drc.artifact_bodies,
        strict=True,
    ):
        result[name] = pair
    for name, pair in zip(
        ("corpus_rows", "adjudication", "split_assignment", "surface_bundle"),
        fx.corpus.artifact_bodies,
        strict=True,
    ):
        result[name] = pair
    for name, pair in zip(
        (
            "object_lock_receipt",
            "readback_receipt",
            "trusted_time_receipt",
            "verifier_identity",
        ),
        fx.storage.artifact_bodies,
        strict=True,
    ):
        result[name] = pair
    result["authorization_instrument"] = fx.authorization.artifact_bodies[0]
    assert tuple(name for name in STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER) == tuple(
        name for name in STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER if name in result
    )
    return result


def _materialize(root: Path) -> Materialized:
    fx = build_fx()
    members: dict[str, tuple[ArtifactRef, bytes, str]] = {}

    def add(reference: ArtifactRef, raw: bytes, relative_path: str) -> None:
        existing = members.get(reference.artifact_id)
        if existing is not None:
            assert existing[:2] == (reference, raw)
            return
        members[reference.artifact_id] = (reference, raw, relative_path)

    add(
        fx.split.artifact_ref,
        fx.split.raw_bytes,
        f"context/{fx.split.artifact_ref.artifact_id}.json",
    )
    for request in fx.split.capture_requests:
        add(
            request.artifact_ref,
            request.raw_bytes,
            f"context/{request.artifact_ref.artifact_id}.json",
        )
    add(
        fx.prompt_inventory.artifact_ref,
        fx.prompt_inventory.raw_bytes,
        f"context/{fx.prompt_inventory.artifact_ref.artifact_id}.json",
    )
    for bundle in fx.bundles:
        add(
            bundle.provenance.artifact_ref,
            bundle.provenance.raw_bytes,
            f"context/{bundle.provenance.artifact_ref.artifact_id}.json",
        )
        for node in bundle.ordered_nodes:
            add(
                node.artifact_ref,
                node.raw_bytes,
                f"context/{node.artifact_ref.artifact_id}.json",
            )
        for reference, raw in bundle.source_bodies:
            add(reference, raw, f"context/{reference.artifact_id}.txt")

    role_bodies = _external_role_bodies(fx)
    external_artifacts: dict[str, dict[str, object]] = {}
    for ordinal, role in enumerate(STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER, start=1):
        reference, raw = role_bodies[role]
        relative_path = f"external/{ordinal:02d}-{role}.json"
        external_artifacts[role] = {
            "relative_path": relative_path,
            "artifact_ref": _rv(reference),
        }
        add(reference, raw, relative_path)
    external_manifest_raw = canonical_json_bytes(
        {
            "schema_version": STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_SCHEMA,
            "target_binding_sha256": fx.context.target_binding_sha256,
            "artifacts": external_artifacts,
        }
    )
    external_manifest_ref = _external_manifest_ref(external_manifest_raw)
    add(
        external_manifest_ref,
        external_manifest_raw,
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME,
    )

    for _, raw, relative_path in members.values():
        destination = root.joinpath(*relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)

    locator_value = {
        "schema_version": cli.CONTEXT_LOCATOR_SCHEMA,
        "split_inventory": _rv(fx.split.artifact_ref),
        "prompt_context_inventory": _rv(fx.prompt_inventory.artifact_ref),
        "external_prerequisite_locator": _rv(external_manifest_ref),
        "model_identity_sha256": fx.context.model_identity_sha256,
        "capture_profile_sha256": fx.context.capture_profile_sha256,
        "members": [
            {"artifact": _rv(reference), "relative_path": relative_path}
            for reference, _, relative_path in (
                members[artifact_id] for artifact_id in sorted(members)
            )
        ],
    }
    locator = root / "stagec_context_locator.v1.json"
    locator.write_bytes(canonical_json_bytes(locator_value))
    caller = root / "caller"
    caller.mkdir()
    intake = caller / "owner-intake.json"
    admission = caller / "admission.json"
    intake.write_bytes(fx.intake.raw_bytes)
    admission.write_bytes(fx.admission.raw_bytes)
    return Materialized(
        root=root,
        locator=locator,
        external_manifest=root / STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME,
        intake=intake,
        admission=admission,
        target_binding_sha256=fx.context.target_binding_sha256,
    )


@pytest.fixture(scope="module")
def materialized(tmp_path_factory: pytest.TempPathFactory) -> Materialized:
    return _materialize(tmp_path_factory.mktemp("stagec-external-cli"))


def _run(*arguments: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(SCRIPT), *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.stderr == ""
    assert completed.stdout.count("\n") == 1
    report = json.loads(completed.stdout)
    assert completed.stdout.encode("utf-8") == canonical_json_bytes(report) + b"\n"
    assert "nonce_b64url" not in completed.stdout
    assert "absolute_path" not in completed.stdout
    return completed, report


def _tree_digest(root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    )


def test_isolated_success_is_canonical_redacted_and_read_only(
    materialized: Materialized,
) -> None:
    before = _tree_digest(materialized.root)
    completed, report = _run("--locator", str(materialized.locator))
    after = _tree_digest(materialized.root)
    assert completed.returncode == cli.EXIT_OK
    assert before == after
    assert report["schema_version"] == cli.REPORT_SCHEMA
    assert report["status"] == STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS
    assert report["external_trust_authentication"] == "NOT_ESTABLISHED"
    assert report["runtime_authorization"] == "NOT_GRANTED_BY_IMPORTER"
    assert report["gate_status"] == {
        "corpus_status": "NOT FROZEN",
        "disclosure": "HELD",
        "execution_authority": "UNAUTHORIZED",
        "experiment": "NOT_STARTED",
        "gate_5": "OPEN",
        "gate_5_disposition": "KEEP_OPEN",
        "license": "NOT LICENSED",
        "stage_c": "DESIGN_ONLY",
    }
    assert report["context"]["capture_request_count"] == 480
    assert report["snapshot"]["artifact_count"] == 16
    assert report["side_effects"] == {
        "files_written": 0,
        "network_requests": 0,
        "nonces_created_or_consumed": 0,
        "provider_actions": 0,
    }


def test_optional_binding_replays_only_caller_supplied_bytes(
    materialized: Materialized,
) -> None:
    completed, report = _run(
        "--locator",
        str(materialized.locator),
        "--owner-intake",
        str(materialized.intake),
        "--admission",
        str(materialized.admission),
    )
    assert completed.returncode == cli.EXIT_OK
    assert report["binding"]["requested"] is True
    assert report["binding"]["loaded"] is True
    assert report["binding"]["semantics"] == "CALLER_SUPPLIED_BYTES_ONLY"
    assert report["binding"]["status"] == STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS


def test_nonisolated_direct_invocation_fails_before_evidence_intake() -> None:
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--locator", "never-read.json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == cli.EXIT_USAGE
    assert completed.stderr == ""
    assert completed.stdout.count("\n") == 1
    report = json.loads(completed.stdout)
    assert completed.stdout.encode("utf-8") == canonical_json_bytes(report) + b"\n"
    assert report["failure"]["code"] == "ISOLATED_READ_ONLY_RUNTIME_REQUIRED"


@pytest.mark.parametrize("replacement", ["../escape.json", "external/file.json:ads", "CON.json"])
def test_context_locator_rejects_escape_ads_and_dos_aliases(
    materialized: Materialized,
    replacement: str,
) -> None:
    original = materialized.locator.read_bytes()
    value = json.loads(original)
    value["members"][0]["relative_path"] = replacement
    materialized.locator.write_bytes(canonical_json_bytes(value))
    try:
        completed, report = _run("--locator", str(materialized.locator))
        assert completed.returncode == cli.EXIT_CONTEXT
        assert report["failure"]["code"] == "CONTEXT_LOCATOR_OR_REPLAY_REJECTED"
    finally:
        materialized.locator.write_bytes(original)


def test_noncanonical_locator_drift_fails_closed(materialized: Materialized) -> None:
    original = materialized.locator.read_bytes()
    materialized.locator.write_bytes(original + b"\n")
    try:
        completed, report = _run("--locator", str(materialized.locator))
        assert completed.returncode == cli.EXIT_CONTEXT
        assert report["status"] == cli.FAIL_CLOSED_STATUS
    finally:
        materialized.locator.write_bytes(original)


def test_context_locator_rejects_case_colliding_member_paths(
    materialized: Materialized,
) -> None:
    original = materialized.locator.read_bytes()
    value = json.loads(original)
    value["members"][0]["relative_path"] = value["members"][1][
        "relative_path"
    ].swapcase()
    materialized.locator.write_bytes(canonical_json_bytes(value))
    try:
        completed, report = _run("--locator", str(materialized.locator))
        assert completed.returncode == cli.EXIT_CONTEXT
        assert report["failure"]["details"] == "REDACTED"
    finally:
        materialized.locator.write_bytes(original)


def test_library_failure_code_is_preserved_with_redacted_details(
    materialized: Materialized,
) -> None:
    outer_original = materialized.locator.read_bytes()
    external_original = materialized.external_manifest.read_bytes()
    external_value = json.loads(external_original)
    external_value["target_binding_sha256"] = "C" * 64
    external_changed = canonical_json_bytes(external_value)
    changed_ref = _external_manifest_ref(external_changed)
    outer_value = json.loads(outer_original)
    old_manifest_id = outer_value["external_prerequisite_locator"]["artifact_id"]
    outer_value["external_prerequisite_locator"] = _rv(changed_ref)
    for member in outer_value["members"]:
        if member["artifact"]["artifact_id"] == old_manifest_id:
            member["artifact"] = _rv(changed_ref)
            break
    outer_value["members"].sort(key=lambda item: item["artifact"]["artifact_id"])
    materialized.external_manifest.write_bytes(external_changed)
    materialized.locator.write_bytes(canonical_json_bytes(outer_value))
    try:
        completed, report = _run("--locator", str(materialized.locator))
        assert completed.returncode == cli.EXIT_SNAPSHOT
        assert report["failure"] == {
            "code": "MANIFEST_TARGET_MISMATCH",
            "details": "REDACTED",
        }
    finally:
        materialized.external_manifest.write_bytes(external_original)
        materialized.locator.write_bytes(outer_original)


def test_argument_failures_have_closed_distinct_exit_code() -> None:
    completed, report = _run()
    assert completed.returncode == cli.EXIT_USAGE
    assert report["failure"]["code"] == "LOCATOR_REQUIRED"
    completed, report = _run(
        "--locator",
        "unused.json",
        "--owner-intake",
        "unpaired.json",
    )
    assert completed.returncode == cli.EXIT_USAGE
    assert report["failure"]["code"] == "BINDING_INPUT_PAIR_REQUIRED"
    for unsafe in ("relative-locator.json", r"\\server\share\locator.json"):
        completed, report = _run("--locator", unsafe)
        assert completed.returncode == cli.EXIT_USAGE
        assert report["failure"]["code"] == "ABSOLUTE_LOCAL_PATH_REQUIRED"
