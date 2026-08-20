"""Exact-byte identity for one local Hugging Face model snapshot.

The Hugging Face cache represents snapshot files as symlinks into a model-local
``blobs`` directory.  Those file symlinks are accepted only when their resolved
targets remain beneath the explicitly supplied model-storage root.  Directory
reparse points, nested files, executable formats, PyTorch pickle weights, and
targets outside the storage root are rejected before any model code is loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Iterable


_REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")
_SAFE_ROOT_FILES = frozenset(
    {
        "added_tokens.json",
        "config.json",
        "generation_config.json",
        "merges.txt",
        "model.safetensors",
        "model.safetensors.index.json",
        "preprocessor_config.json",
        "special_tokens_map.json",
        "spiece.model",
        "tokenizer.json",
        "tokenizer.model",
        "tokenizer_config.json",
        "vocab.json",
    }
)
_TOKENIZER_FILES = frozenset(
    {
        "added_tokens.json",
        "merges.txt",
        "special_tokens_map.json",
        "spiece.model",
        "tokenizer.json",
        "tokenizer.model",
        "tokenizer_config.json",
        "vocab.json",
    }
)


@dataclass(frozen=True)
class LocalModelSnapshot:
    model_id: str
    revision: str
    snapshot_root: Path
    model_storage_root: Path

    def validate(self) -> None:
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("model_id must be non-empty")
        if not isinstance(self.revision, str) or not _REVISION_RE.fullmatch(
            self.revision
        ):
            raise ValueError("revision must be a pinned lowercase 40-64 hex identity")
        for label, value in (
            ("snapshot_root", self.snapshot_root),
            ("model_storage_root", self.model_storage_root),
        ):
            if not isinstance(value, Path) or not value.is_absolute():
                raise ValueError(f"{label} must be an absolute local path")


@dataclass(frozen=True)
class SnapshotFile:
    relative_path: str
    byte_count: int
    sha256: str
    resolved_relative_to_storage: str
    link_kind: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "resolved_relative_to_storage": self.resolved_relative_to_storage,
            "link_kind": self.link_kind,
        }


@dataclass(frozen=True)
class SnapshotAttestation:
    model_id: str
    revision: str
    snapshot_root: str
    model_storage_root: str
    config_sha256: str
    weights_manifest_sha256: str
    tokenizer_manifest_sha256: str
    tree_manifest_sha256: str
    files: tuple[SnapshotFile, ...]
    identity_binding_status: str
    claim_boundary: str = (
        "LOCAL MODEL FILE BYTES AND SNAPSHOT TOPOLOGY ATTESTED. NOT EXTERNAL "
        "AUTHENTICATION, SCIENTIFIC VALIDATION, OR PACKET ELIGIBILITY."
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "snapshot_root": self.snapshot_root,
            "model_storage_root": self.model_storage_root,
            "config_sha256": self.config_sha256,
            "weights_manifest_sha256": self.weights_manifest_sha256,
            "tokenizer_manifest_sha256": self.tokenizer_manifest_sha256,
            "tree_manifest_sha256": self.tree_manifest_sha256,
            "files": [item.to_dict() for item in self.files],
            "identity_binding_status": self.identity_binding_status,
            "claim_boundary": self.claim_boundary,
        }


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def attest_local_snapshot(snapshot: LocalModelSnapshot) -> SnapshotAttestation:
    """Hash and structurally verify one local-only model snapshot."""

    snapshot.validate()
    snapshot_root = snapshot.snapshot_root.resolve(strict=True)
    storage_root = snapshot.model_storage_root.resolve(strict=True)
    if not snapshot_root.is_dir() or not storage_root.is_dir():
        raise ValueError("snapshot and storage roots must be directories")
    if not _is_relative_to(snapshot_root, storage_root):
        raise ValueError("snapshot_root must resolve beneath model_storage_root")
    if snapshot.snapshot_root.name != snapshot.revision:
        raise ValueError("snapshot directory name must equal the pinned revision")
    if snapshot.snapshot_root.parent.name != "snapshots":
        raise ValueError("snapshot_root must be directly beneath a snapshots directory")
    storage_name = snapshot.model_storage_root.name
    if storage_name.startswith("models--"):
        expected_model_id = "/".join(storage_name[len("models--") :].split("--"))
        if snapshot.model_id != expected_model_id:
            raise ValueError("model_id does not match the Hugging Face cache directory")
        identity_binding_status = "HF_CACHE_MODEL_ID_AND_REVISION_PATH_BOUND"
    else:
        identity_binding_status = "DECLARED_MODEL_ALIAS_REVISION_DIRECTORY_BOUND"
    _require_plain_directory_chain(snapshot.snapshot_root, snapshot.model_storage_root)

    rows: list[SnapshotFile] = []
    casefold_names: set[str] = set()
    for logical in _iter_snapshot_files(snapshot.snapshot_root):
        relative = logical.relative_to(snapshot.snapshot_root)
        if len(relative.parts) != 1:
            raise ValueError(f"nested snapshot entries are not admitted: {relative}")
        name = relative.as_posix()
        folded = name.casefold()
        if folded in casefold_names:
            raise ValueError(f"case-insensitive duplicate snapshot entry: {name}")
        casefold_names.add(folded)
        if not _is_allowed_model_file(name):
            raise ValueError(f"snapshot file is not on the local-safe allowlist: {name}")

        link_stat = logical.lstat()
        is_link = stat.S_ISLNK(link_stat.st_mode)
        if _is_reparse_point(link_stat) and not is_link:
            raise ValueError(f"non-symlink reparse file is forbidden: {name}")
        resolved_before = logical.resolve(strict=True)
        if not _is_relative_to(resolved_before, storage_root):
            raise ValueError(f"snapshot file resolves outside model storage: {name}")
        if not resolved_before.is_file():
            raise ValueError(f"snapshot entry is not a regular file: {name}")
        digest, byte_count = _hash_stable_file(resolved_before)
        resolved_after = logical.resolve(strict=True)
        if resolved_after != resolved_before:
            raise ValueError(f"snapshot link target changed while hashing: {name}")
        rows.append(
            SnapshotFile(
                relative_path=name,
                byte_count=byte_count,
                sha256=digest,
                resolved_relative_to_storage=resolved_before.relative_to(
                    storage_root
                ).as_posix(),
                link_kind="MODEL_LOCAL_FILE_SYMLINK" if is_link else "PLAIN_FILE",
            )
        )

    rows.sort(key=lambda item: item.relative_path.encode("utf-8"))
    if not rows:
        raise ValueError("model snapshot is empty")
    by_name = {item.relative_path: item for item in rows}
    if "config.json" not in by_name:
        raise ValueError("model snapshot must contain config.json")
    weight_rows = [item for item in rows if item.relative_path.endswith(".safetensors")]
    if not weight_rows:
        raise ValueError("model snapshot must contain at least one safetensors weight file")
    tokenizer_rows = [item for item in rows if item.relative_path in _TOKENIZER_FILES]
    if not tokenizer_rows:
        raise ValueError("model snapshot must contain tokenizer files")

    weights_manifest_sha256 = _rows_digest(weight_rows)
    tokenizer_manifest_sha256 = _rows_digest(tokenizer_rows)
    tree_manifest_sha256 = _rows_digest(rows)
    return SnapshotAttestation(
        model_id=snapshot.model_id,
        revision=snapshot.revision,
        snapshot_root=str(snapshot.snapshot_root),
        model_storage_root=str(snapshot.model_storage_root),
        config_sha256=by_name["config.json"].sha256,
        weights_manifest_sha256=weights_manifest_sha256,
        tokenizer_manifest_sha256=tokenizer_manifest_sha256,
        tree_manifest_sha256=tree_manifest_sha256,
        files=tuple(rows),
        identity_binding_status=identity_binding_status,
    )


def require_same_attestation(
    expected: SnapshotAttestation, observed: SnapshotAttestation
) -> None:
    if expected.to_dict() != observed.to_dict():
        raise RuntimeError("local model snapshot changed after its initial attestation")


def _iter_snapshot_files(root: Path) -> Iterable[Path]:
    for current_text, dir_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_text)
        for directory_name in dir_names:
            directory = current / directory_name
            info = directory.lstat()
            if stat.S_ISLNK(info.st_mode) or _is_reparse_point(info):
                raise ValueError(f"snapshot directory links/reparse points are forbidden: {directory}")
        for file_name in file_names:
            yield current / file_name


def _is_allowed_model_file(name: str) -> bool:
    if name in _SAFE_ROOT_FILES:
        return True
    return name.startswith("model-") and name.endswith(".safetensors")


def _rows_digest(rows: Iterable[SnapshotFile]) -> str:
    payload = [item.to_dict() for item in rows]
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def _hash_stable_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        before = os.fstat(handle.fileno())
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(handle.fileno())
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if before_identity != after_identity:
        raise ValueError(f"file changed while hashing: {path}")
    if before.st_size <= 0:
        raise ValueError(f"empty model file is forbidden: {path}")
    return digest.hexdigest().upper(), int(before.st_size)


def _require_plain_directory_chain(path: Path, stop: Path) -> None:
    current = path
    stop_resolved = stop.resolve(strict=True)
    while True:
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or _is_reparse_point(info):
            raise ValueError(f"directory link/reparse point is forbidden: {current}")
        if current.resolve(strict=True) == stop_resolved:
            return
        parent = current.parent
        if parent == current:
            raise ValueError("model storage root is not an ancestor of snapshot_root")
        current = parent


def _is_reparse_point(value: os.stat_result) -> bool:
    attributes = getattr(value, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & flag)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
