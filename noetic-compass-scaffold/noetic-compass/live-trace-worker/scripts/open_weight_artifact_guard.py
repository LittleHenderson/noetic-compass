"""Fail-closed identity guard for auxiliary open-weight model loaders.

The auxiliary research commands are intentionally separate from the hosted
worker's application loader.  They must nevertheless obey the same basic
identity boundary: an immutable repository revision, no remote model code, and
an exact local snapshot whose bytes were verified before Transformers parses
anything in that snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any


MANIFEST_SCHEMA_VERSION = "cas_harness_open_weight_artifact_manifest.v1"
_COMMIT_SHA_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_MAX_MANIFEST_BYTES = 8 * 1024 * 1024
_MAX_INDEX_BYTES = 64 * 1024 * 1024
_MAX_ARTIFACTS = 10_000
_REQUIRED_TOKENIZER_FILENAMES = frozenset(
    {
        "tokenizer.json",
        "tokenizer_config.json",
        "tokenizer.model",
        "spiece.model",
        "vocab.json",
    }
)


class ArtifactPolicyError(RuntimeError):
    """The caller did not supply an exact, immutable local model snapshot."""


@dataclass(frozen=True)
class VerifiedArtifact:
    path: str
    sha256: str
    byte_count: int

    def evidence(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
        }


@dataclass(frozen=True)
class VerifiedModelArtifacts:
    """Identity evidence returned only after the complete snapshot verifies."""

    manifest_path: Path
    manifest_sha256: str
    model_root: Path
    model_id: str
    model_revision: str
    artifact_count: int
    artifact_set_sha256: str
    artifacts: tuple[VerifiedArtifact, ...]

    def evidence(self, *, post_load_reverified: bool = False) -> dict[str, Any]:
        return {
            "manifest_path": str(self.manifest_path),
            "manifest_sha256": self.manifest_sha256,
            "artifact_count": self.artifact_count,
            "artifact_set_sha256": self.artifact_set_sha256,
            "artifacts": [artifact.evidence() for artifact in self.artifacts],
            "all_artifacts_hash_verified": True,
            "verification_timing": (
                "pre_parse_and_post_load"
                if post_load_reverified
                else "pre_parse_only"
            ),
            "post_load_reverified": post_load_reverified,
            "snapshot_mutability_control": (
                "PRE_PARSE_AND_POST_LOAD_FULL_REHASH"
                if post_load_reverified
                else "PRE_PARSE_FULL_REHASH_ONLY"
            ),
            "durable_snapshot_immutability_established": False,
            "caller_manifest_trust_root_established": False,
            "toctou_reversion_resistance": "OPEN",
            "symlinks_junctions_and_hardlinks_rejected": True,
            "model_source": "verified_local_snapshot",
            "local_files_only": True,
            "trust_remote_code": False,
            "use_safetensors": True,
        }


def require_commit_revision(value: Any, *, field_name: str = "model_revision") -> str:
    """Return an exact lowercase Git commit SHA or fail closed."""

    if not isinstance(value, str) or _COMMIT_SHA_RE.fullmatch(value) is None:
        raise ArtifactPolicyError(
            f"{field_name} must be a full 40-character lowercase commit SHA."
        )
    return value


def require_sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ArtifactPolicyError(
            f"{field_name} must be exactly 64 lowercase hexadecimal characters."
        )
    return value


def verify_open_weight_artifact_manifest(
    *,
    manifest_path: Path | str | None,
    expected_manifest_sha256: str | None,
    model_id: str,
    model_revision: str | None,
    trust_remote_code: bool,
) -> VerifiedModelArtifacts:
    """Verify the exact local snapshot before any model parser/loader runs.

    The manifest is deliberately caller supplied.  Its ``model_root`` must be
    a link-free, fully enumerated materialized directory: every regular file
    must be declared and no undeclared file may be present. This rejects common
    mutable-cache aliases but does not establish durable immutability or close
    an ABA mutate-and-restore race; the returned evidence labels that gap OPEN.
    """

    revision = require_commit_revision(model_revision)
    if trust_remote_code is not False:
        raise ArtifactPolicyError("trust_remote_code must be exactly false.")
    if not isinstance(model_id, str) or not model_id.strip() or model_id != model_id.strip():
        raise ArtifactPolicyError("model_id must be a non-empty, whitespace-free-boundary string.")
    if manifest_path is None:
        raise ArtifactPolicyError("A caller-supplied model artifact manifest is required.")
    expected_manifest_sha256 = require_sha256(
        expected_manifest_sha256,
        field_name="caller-supplied model artifact manifest SHA-256",
    )

    requested_manifest_path = Path(manifest_path)
    if _is_link_like(requested_manifest_path):
        raise ArtifactPolicyError("The model artifact manifest may not be a symlink or junction.")
    try:
        resolved_manifest_path = requested_manifest_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ArtifactPolicyError("The model artifact manifest does not exist.") from exc
    if not resolved_manifest_path.is_file():
        raise ArtifactPolicyError("The model artifact manifest is not a regular file.")

    raw_manifest = _read_bounded_manifest(resolved_manifest_path)
    manifest_sha256 = hashlib.sha256(raw_manifest).hexdigest()
    if manifest_sha256 != expected_manifest_sha256:
        raise ArtifactPolicyError("The model artifact manifest SHA-256 does not match the caller binding.")
    payload = _strict_json_loads(raw_manifest)
    _require_exact_keys(
        payload,
        {"schema_version", "model_id", "model_revision", "model_root", "artifacts"},
        label="manifest",
    )
    if payload["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ArtifactPolicyError(
            f"manifest.schema_version must equal {MANIFEST_SCHEMA_VERSION!r}."
        )
    if payload["model_id"] != model_id:
        raise ArtifactPolicyError("manifest.model_id does not match the requested model_id.")
    if payload["model_revision"] != revision:
        raise ArtifactPolicyError(
            "manifest.model_revision does not match the requested immutable revision."
        )

    model_root_text = payload["model_root"]
    if (
        not isinstance(model_root_text, str)
        or not model_root_text.strip()
        or model_root_text != model_root_text.strip()
    ):
        raise ArtifactPolicyError("manifest.model_root must be a non-empty path string.")
    unresolved_root = Path(model_root_text)
    if not unresolved_root.is_absolute():
        unresolved_root = resolved_manifest_path.parent / unresolved_root
    if _is_link_like(unresolved_root):
        raise ArtifactPolicyError("manifest.model_root may not be a symlink or junction.")
    try:
        model_root = unresolved_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ArtifactPolicyError("manifest.model_root does not exist.") from exc
    if not model_root.is_dir():
        raise ArtifactPolicyError("manifest.model_root is not a directory.")

    artifacts = payload["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise ArtifactPolicyError("manifest.artifacts must be a non-empty list.")
    if len(artifacts) > _MAX_ARTIFACTS:
        raise ArtifactPolicyError(
            f"manifest.artifacts exceeds the {_MAX_ARTIFACTS}-file safety limit."
        )

    expected: dict[str, tuple[str, int]] = {}
    for index, artifact in enumerate(artifacts):
        label = f"manifest.artifacts[{index}]"
        _require_exact_keys(artifact, {"path", "sha256", "byte_count"}, label=label)
        relative_path = _require_relative_artifact_path(artifact["path"], label=f"{label}.path")
        digest = artifact["sha256"]
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise ArtifactPolicyError(f"{label}.sha256 must be 64 lowercase hex characters.")
        byte_count = artifact["byte_count"]
        if type(byte_count) is not int or byte_count < 1:
            raise ArtifactPolicyError(f"{label}.byte_count must be a positive integer.")
        if relative_path in expected:
            raise ArtifactPolicyError(f"Duplicate artifact path: {relative_path!r}.")
        expected[relative_path] = (digest, byte_count)

    _require_minimum_model_inputs(expected)
    actual_paths = _enumerate_materialized_files(model_root)
    expected_paths = set(expected)
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)[:8]
        unexpected = sorted(actual_paths - expected_paths)[:8]
        raise ArtifactPolicyError(
            "Model snapshot file set does not exactly match the manifest "
            f"(missing={missing}, unexpected={unexpected})."
        )

    canonical_records: list[dict[str, Any]] = []
    verified_records: list[VerifiedArtifact] = []
    for relative_path in sorted(expected):
        expected_digest, expected_bytes = expected[relative_path]
        artifact_path = model_root.joinpath(*PurePosixPath(relative_path).parts)
        if _is_link_like(artifact_path):
            raise ArtifactPolicyError(
                f"Model artifact {relative_path!r} may not be a symlink or junction."
            )
        digest, byte_count = _hash_stable_regular_file(artifact_path, relative_path)
        if digest != expected_digest:
            raise ArtifactPolicyError(f"Model artifact SHA-256 mismatch: {relative_path!r}.")
        if byte_count != expected_bytes:
            raise ArtifactPolicyError(f"Model artifact byte_count mismatch: {relative_path!r}.")
        canonical_records.append(
            {"path": relative_path, "sha256": digest, "byte_count": byte_count}
        )
        verified_records.append(
            VerifiedArtifact(
                path=relative_path,
                sha256=digest,
                byte_count=byte_count,
            )
        )

    _validate_safetensors_indexes(model_root, expected)

    artifact_set_bytes = json.dumps(
        canonical_records,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return VerifiedModelArtifacts(
        manifest_path=resolved_manifest_path,
        manifest_sha256=manifest_sha256,
        model_root=model_root,
        model_id=model_id,
        model_revision=revision,
        artifact_count=len(canonical_records),
        artifact_set_sha256=hashlib.sha256(artifact_set_bytes).hexdigest(),
        artifacts=tuple(verified_records),
    )


def reverify_open_weight_artifacts_after_load(
    verified: VerifiedModelArtifacts,
) -> VerifiedModelArtifacts:
    """Rehash the complete snapshot after Transformers finishes loading it."""

    rechecked = verify_open_weight_artifact_manifest(
        manifest_path=verified.manifest_path,
        expected_manifest_sha256=verified.manifest_sha256,
        model_id=verified.model_id,
        model_revision=verified.model_revision,
        trust_remote_code=False,
    )
    if rechecked != verified:
        raise ArtifactPolicyError(
            "Model artifact identity changed between pre-parse verification and load completion."
        )
    return rechecked


def _read_bounded_manifest(path: Path) -> bytes:
    try:
        stat_result = path.stat()
        size = stat_result.st_size
    except OSError as exc:
        raise ArtifactPolicyError("Could not stat the model artifact manifest.") from exc
    if getattr(stat_result, "st_nlink", 1) != 1:
        raise ArtifactPolicyError("The model artifact manifest may not be hard-linked.")
    if size < 1 or size > _MAX_MANIFEST_BYTES:
        raise ArtifactPolicyError(
            f"Model artifact manifest must be 1..{_MAX_MANIFEST_BYTES} bytes."
        )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ArtifactPolicyError("Could not read the model artifact manifest.") from exc
    if len(raw) != size:
        raise ArtifactPolicyError("Model artifact manifest changed while it was read.")
    return raw


def _strict_json_loads(raw: bytes) -> dict[str, Any]:
    def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ArtifactPolicyError(f"Duplicate JSON key in artifact manifest: {key!r}.")
            out[key] = value
        return out

    def reject_constant(value: str) -> Any:
        raise ArtifactPolicyError(f"Non-finite JSON constant is forbidden: {value}.")

    try:
        decoded = raw.decode("utf-8")
        payload = json.loads(
            decoded,
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_constant,
        )
    except ArtifactPolicyError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactPolicyError("Model artifact manifest must be strict UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise ArtifactPolicyError("Model artifact manifest root must be an object.")
    return payload


def _require_exact_keys(value: Any, required: set[str], *, label: str) -> None:
    if not isinstance(value, dict):
        raise ArtifactPolicyError(f"{label} must be an object.")
    observed = set(value)
    if observed != required:
        missing = sorted(required - observed)
        extra = sorted(observed - required)
        raise ArtifactPolicyError(
            f"{label} keys must match exactly (missing={missing}, extra={extra})."
        )


def _require_relative_artifact_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ArtifactPolicyError(f"{label} must be a non-empty canonical path string.")
    if "\\" in value:
        raise ArtifactPolicyError(f"{label} must use forward slashes.")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or value != parsed.as_posix():
        raise ArtifactPolicyError(f"{label} must be a canonical relative POSIX path.")
    if any(part in {"", ".", ".."} for part in parsed.parts):
        raise ArtifactPolicyError(f"{label} may not contain empty, dot, or parent segments.")
    if parsed.parts and ":" in parsed.parts[0]:
        raise ArtifactPolicyError(f"{label} may not contain a drive-qualified path.")
    return value


def _require_minimum_model_inputs(expected: dict[str, tuple[str, int]]) -> None:
    if "config.json" not in expected:
        raise ArtifactPolicyError("The exact model snapshot must include root-level config.json.")
    if not any(path.endswith(".safetensors") for path in expected):
        raise ArtifactPolicyError("The exact model snapshot must include safetensors weights.")
    if not {"model.safetensors", "model.safetensors.index.json"}.intersection(expected):
        raise ArtifactPolicyError(
            "The exact model snapshot must include root-level model.safetensors or its standard index."
        )
    if set(expected).isdisjoint(_REQUIRED_TOKENIZER_FILENAMES):
        raise ArtifactPolicyError("The exact model snapshot must include root-level tokenizer inputs.")


def _enumerate_materialized_files(model_root: Path) -> set[str]:
    files: set[str] = set()
    try:
        descendants = model_root.rglob("*")
        for path in descendants:
            relative = path.relative_to(model_root).as_posix()
            if _is_link_like(path):
                raise ArtifactPolicyError(
                    f"Model snapshot contains a symlink or junction: {relative!r}."
                )
            if path.is_dir():
                continue
            if not path.is_file():
                raise ArtifactPolicyError(
                    f"Model snapshot contains a non-regular filesystem entry: {relative!r}."
                )
            files.add(relative)
            if len(files) > _MAX_ARTIFACTS:
                raise ArtifactPolicyError(
                    f"Model snapshot exceeds the {_MAX_ARTIFACTS}-file safety limit."
                )
    except ArtifactPolicyError:
        raise
    except OSError as exc:
        raise ArtifactPolicyError("Could not enumerate the exact model snapshot.") from exc
    return files


def _validate_safetensors_indexes(
    model_root: Path,
    expected: dict[str, tuple[str, int]],
) -> None:
    index_paths = [
        relative_path
        for relative_path in expected
        if PurePosixPath(relative_path).name == "model.safetensors.index.json"
    ]
    if len(index_paths) > 1:
        raise ArtifactPolicyError("The model snapshot contains multiple safetensors indexes.")
    if not index_paths:
        if sum(path.endswith(".safetensors") for path in expected) != 1:
            raise ArtifactPolicyError(
                "A snapshot with multiple safetensors files requires one standard index."
            )
        return

    index_relative_path = index_paths[0]
    index_path = model_root.joinpath(*PurePosixPath(index_relative_path).parts)
    expected_digest, expected_bytes = expected[index_relative_path]
    if expected_bytes > _MAX_INDEX_BYTES:
        raise ArtifactPolicyError(
            f"Safetensors index exceeds the {_MAX_INDEX_BYTES}-byte safety limit."
        )
    try:
        raw_index = index_path.read_bytes()
    except OSError as exc:
        raise ArtifactPolicyError("Could not read the verified safetensors index.") from exc
    if len(raw_index) != expected_bytes or hashlib.sha256(raw_index).hexdigest() != expected_digest:
        raise ArtifactPolicyError("Safetensors index changed before validation.")
    index = _strict_json_loads(raw_index)
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        raise ArtifactPolicyError("Safetensors index requires a non-empty weight_map object.")
    referenced_shards: set[str] = set()
    for tensor_name, raw_shard_path in weight_map.items():
        if not isinstance(tensor_name, str) or not tensor_name:
            raise ArtifactPolicyError("Safetensors index tensor names must be non-empty strings.")
        shard_path = _require_relative_artifact_path(
            raw_shard_path,
            label=f"safetensors weight_map[{tensor_name!r}]",
        )
        if not shard_path.endswith(".safetensors"):
            raise ArtifactPolicyError("Safetensors index may reference only .safetensors files.")
        if shard_path not in expected:
            raise ArtifactPolicyError(
                f"Safetensors index references an unverified artifact: {shard_path!r}."
            )
        referenced_shards.add(shard_path)
    declared_shards = {path for path in expected if path.endswith(".safetensors")}
    if referenced_shards != declared_shards:
        raise ArtifactPolicyError(
            "Safetensors index references must exactly cover declared weight shards."
        )


def _hash_stable_regular_file(path: Path, relative_path: str) -> tuple[str, int]:
    try:
        before = path.stat()
        if not path.is_file():
            raise ArtifactPolicyError(f"Model artifact is not a regular file: {relative_path!r}.")
        if getattr(before, "st_nlink", 1) != 1:
            raise ArtifactPolicyError(
                f"Model artifact may not be hard-linked: {relative_path!r}."
            )
        digest = hashlib.sha256()
        byte_count = 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                byte_count += len(chunk)
        after = path.stat()
    except ArtifactPolicyError:
        raise
    except OSError as exc:
        raise ArtifactPolicyError(f"Could not hash model artifact: {relative_path!r}.") from exc
    identity_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field, None) != getattr(after, field, None) for field in identity_fields):
        raise ArtifactPolicyError(f"Model artifact changed while hashing: {relative_path!r}.")
    if getattr(after, "st_nlink", 1) != 1:
        raise ArtifactPolicyError(
            f"Model artifact became hard-linked while hashing: {relative_path!r}."
        )
    return digest.hexdigest(), byte_count


def _is_link_like(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        return bool(is_junction()) if callable(is_junction) else False
    except OSError as exc:
        raise ArtifactPolicyError(f"Could not inspect filesystem identity for {os.fspath(path)!r}.") from exc
