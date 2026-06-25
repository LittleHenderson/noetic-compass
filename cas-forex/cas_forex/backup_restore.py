"""Backup and restore primitive for operator-critical CAS Forex state.

Produces a single ZIP snapshot of operator-critical files (strategy leads,
agent memory reports, event journals, push/webhook subscriptions, operator
audit). Provides a destructive restore helper that defaults to dry-run.

Safety guarantees:
- create_backup never raises; failures return an empty manifest with
  file_count=0 and an error sentinel in the snapshot_path field.
- evaluate_restore is read-only and never writes.
- execute_restore writes atomically (temp + os.replace per file) and
  refuses to write outside repo_root (action='SKIPPED_OUT_OF_ROOT').
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


DEFAULT_BACKUP_FILES: tuple[str, ...] = (
    "strategy_leads.json",
    # Memory + event journals (globbed)
    "evidence_runs/agent_memory/*-report.json",  # latest only (mtime)
    "evidence_runs/agent_workflow_queue/agent-events.jsonl",
    "evidence_runs/agent_workflow_queue/agent-events-mt5-demo.jsonl",
    "evidence_runs/push_subscriptions/subscriptions.jsonl",
    "evidence_runs/webhook_subscriptions/subscriptions.jsonl",
    "evidence_runs/operator_audit/operator-audit.jsonl",
)


_MANIFEST_NAME = "manifest.json"
_BACKUP_PREFIX = "cas-forex-backup-"
_BACKUP_SUFFIX = ".zip"
_ERROR_SNAPSHOT_SENTINEL = ""


@dataclass(frozen=True)
class BackupManifest:
    snapshot_id: str
    created_at_iso: str
    repo_root: str
    snapshot_path: str
    file_count: int
    total_bytes: int
    files: tuple[Mapping[str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RestoreOperation:
    file_path: str
    action: str
    backup_sha256: str | None
    current_sha256: str | None
    backup_bytes: int | None
    current_bytes: int | None


@dataclass(frozen=True)
class RestoreResult:
    snapshot_path: str
    dry_run: bool
    operations: tuple[RestoreOperation, ...]
    restored_count: int
    overwrite_count: int
    skipped_count: int
    missing_count: int
    error_message: str | None


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_files(repo_root: Path, file_patterns: Sequence[str]) -> list[Path]:
    """Resolve glob patterns into a list of concrete file paths.

    For globs whose pattern basename ends with '-report.json', only the
    most-recent by mtime is returned (assumes latest is canonical). For
    other patterns, all matches are returned.
    """
    out: list[Path] = []
    for pat in file_patterns:
        matches = sorted(repo_root.glob(pat))
        matches = [m for m in matches if m.is_file()]
        if not matches:
            continue
        basename = Path(pat).name
        if basename.endswith("-report.json") and "*" in pat:
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            out.append(matches[0])
        else:
            out.extend(matches)
    # de-dup while preserving order
    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in out:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        deduped.append(p)
    return deduped


def _timestamp_for(now: datetime) -> str:
    return now.strftime("%Y%m%dT%H%M%SZ")


def _empty_manifest(repo_root: Path, snapshot_path: str, now: datetime) -> BackupManifest:
    iso = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    snapshot_id = _sha256_bytes(iso.encode("utf-8") + b"|empty")[:16]
    return BackupManifest(
        snapshot_id=snapshot_id,
        created_at_iso=iso,
        repo_root=str(repo_root),
        snapshot_path=snapshot_path,
        file_count=0,
        total_bytes=0,
        files=tuple(),
    )


def create_backup(
    *,
    repo_root: Path,
    snapshot_dir: Path,
    file_patterns: Sequence[str] = DEFAULT_BACKUP_FILES,
    now: datetime | None = None,
) -> BackupManifest:
    """Glob each pattern relative to repo_root, snapshot into a ZIP.

    Atomic-ish: write temp then rename. Never raises; on error returns an
    empty manifest with snapshot_path=_ERROR_SNAPSHOT_SENTINEL.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    iso = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    repo_root = Path(repo_root)

    try:
        snapshot_dir = Path(snapshot_dir)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        ts = _timestamp_for(now)
        snapshot_path = snapshot_dir / f"{_BACKUP_PREFIX}{ts}{_BACKUP_SUFFIX}"
    except Exception:
        return _empty_manifest(repo_root, _ERROR_SNAPSHOT_SENTINEL, now)

    try:
        files = _resolve_files(repo_root, list(file_patterns))
    except Exception:
        return _empty_manifest(repo_root, _ERROR_SNAPSHOT_SENTINEL, now)

    file_entries: list[dict[str, str | int]] = []
    total_bytes = 0
    file_payloads: list[tuple[str, bytes]] = []

    for path in files:
        try:
            rel = path.resolve().relative_to(repo_root.resolve())
        except Exception:
            # File outside repo_root — skip
            continue
        try:
            data = path.read_bytes()
        except Exception:
            continue
        rel_str = rel.as_posix()
        sha = _sha256_bytes(data)
        file_entries.append(
            {
                "relative_path": rel_str,
                "sha256": sha,
                "bytes": len(data),
            }
        )
        total_bytes += len(data)
        file_payloads.append((rel_str, data))

    # Empty result — still produce a valid ZIP for consistency.
    snapshot_id_seed = iso + "|" + str(len(file_entries)) + "|" + str(total_bytes)
    for ent in file_entries:
        snapshot_id_seed += "|" + ent["relative_path"] + ":" + ent["sha256"]
    snapshot_id = _sha256_bytes(snapshot_id_seed.encode("utf-8"))[:16]

    manifest_payload = {
        "snapshot_id": snapshot_id,
        "created_at_iso": iso,
        "repo_root": str(repo_root),
        "file_count": len(file_entries),
        "total_bytes": total_bytes,
        "files": file_entries,
    }

    # Write to a temp file in snapshot_dir, then os.replace into final path
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=_BACKUP_PREFIX, suffix=".zip.tmp", dir=str(snapshot_dir)
    )
    try:
        os.close(tmp_fd)
        try:
            with zipfile.ZipFile(tmp_name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    _MANIFEST_NAME,
                    json.dumps(manifest_payload, indent=2, sort_keys=True),
                )
                for rel_str, data in file_payloads:
                    zf.writestr(rel_str, data)
            os.replace(tmp_name, snapshot_path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except Exception:
                pass
            return _empty_manifest(repo_root, _ERROR_SNAPSHOT_SENTINEL, now)
    except Exception:
        try:
            os.unlink(tmp_name)
        except Exception:
            pass
        return _empty_manifest(repo_root, _ERROR_SNAPSHOT_SENTINEL, now)

    return BackupManifest(
        snapshot_id=snapshot_id,
        created_at_iso=iso,
        repo_root=str(repo_root),
        snapshot_path=str(snapshot_path),
        file_count=len(file_entries),
        total_bytes=total_bytes,
        files=tuple(file_entries),
    )


def _read_manifest_from_zip(zf: zipfile.ZipFile) -> dict:
    with zf.open(_MANIFEST_NAME, "r") as f:
        return json.loads(f.read().decode("utf-8"))


def list_backups(snapshot_dir: Path) -> list[BackupManifest]:
    """Read all cas-forex-backup-*.zip; return manifests sorted DESC by created_at."""
    snapshot_dir = Path(snapshot_dir)
    if not snapshot_dir.exists():
        return []
    results: list[BackupManifest] = []
    for path in sorted(snapshot_dir.glob(f"{_BACKUP_PREFIX}*{_BACKUP_SUFFIX}")):
        try:
            with zipfile.ZipFile(path, "r") as zf:
                payload = _read_manifest_from_zip(zf)
        except Exception:
            continue
        files = tuple(payload.get("files", ()))
        results.append(
            BackupManifest(
                snapshot_id=str(payload.get("snapshot_id", "")),
                created_at_iso=str(payload.get("created_at_iso", "")),
                repo_root=str(payload.get("repo_root", "")),
                snapshot_path=str(path),
                file_count=int(payload.get("file_count", len(files))),
                total_bytes=int(payload.get("total_bytes", 0)),
                files=files,
            )
        )
    results.sort(key=lambda m: m.created_at_iso, reverse=True)
    return results


def _safe_target_path(repo_root: Path, rel: str) -> Path | None:
    """Return resolved target path if inside repo_root, else None."""
    try:
        repo_resolved = repo_root.resolve()
        candidate = (repo_root / rel).resolve()
    except Exception:
        return None
    # Check candidate is inside repo_resolved
    try:
        candidate.relative_to(repo_resolved)
    except ValueError:
        return None
    return candidate


def evaluate_restore(
    *,
    snapshot_path: Path,
    repo_root: Path,
) -> RestoreResult:
    """Plan a restore — read-only, dry_run=True."""
    snapshot_path = Path(snapshot_path)
    repo_root = Path(repo_root)
    try:
        zf = zipfile.ZipFile(snapshot_path, "r")
    except Exception as exc:
        return RestoreResult(
            snapshot_path=str(snapshot_path),
            dry_run=True,
            operations=tuple(),
            restored_count=0,
            overwrite_count=0,
            skipped_count=0,
            missing_count=0,
            error_message=f"cannot open snapshot: {exc}",
        )
    try:
        try:
            payload = _read_manifest_from_zip(zf)
        except Exception as exc:
            return RestoreResult(
                snapshot_path=str(snapshot_path),
                dry_run=True,
                operations=tuple(),
                restored_count=0,
                overwrite_count=0,
                skipped_count=0,
                missing_count=0,
                error_message=f"missing manifest: {exc}",
            )

        ops: list[RestoreOperation] = []
        overwrite = 0
        skipped = 0
        missing = 0
        for entry in payload.get("files", []):
            rel = str(entry.get("relative_path", ""))
            backup_sha = str(entry.get("sha256", "")) or None
            backup_bytes = int(entry.get("bytes", 0))
            target = _safe_target_path(repo_root, rel)
            if target is None:
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="SKIPPED_OUT_OF_ROOT",
                        backup_sha256=backup_sha,
                        current_sha256=None,
                        backup_bytes=backup_bytes,
                        current_bytes=None,
                    )
                )
                skipped += 1
                continue
            if not target.exists():
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="WOULD_RESTORE_NEW",
                        backup_sha256=backup_sha,
                        current_sha256=None,
                        backup_bytes=backup_bytes,
                        current_bytes=None,
                    )
                )
                missing += 1
                continue
            try:
                current_sha = _sha256_file(target)
                current_bytes = target.stat().st_size
            except Exception:
                current_sha = None
                current_bytes = None
            if current_sha == backup_sha:
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="SKIPPED_UNCHANGED",
                        backup_sha256=backup_sha,
                        current_sha256=current_sha,
                        backup_bytes=backup_bytes,
                        current_bytes=current_bytes,
                    )
                )
                skipped += 1
            else:
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="WOULD_OVERWRITE",
                        backup_sha256=backup_sha,
                        current_sha256=current_sha,
                        backup_bytes=backup_bytes,
                        current_bytes=current_bytes,
                    )
                )
                overwrite += 1
        return RestoreResult(
            snapshot_path=str(snapshot_path),
            dry_run=True,
            operations=tuple(ops),
            restored_count=0,
            overwrite_count=overwrite,
            skipped_count=skipped,
            missing_count=missing,
            error_message=None,
        )
    finally:
        zf.close()


def execute_restore(
    *,
    snapshot_path: Path,
    repo_root: Path,
    only_files: Sequence[str] | None = None,
) -> RestoreResult:
    """Destructive restore — writes backed-up bytes back into repo_root.

    Atomic per file (temp + os.replace). Refuses to write outside repo_root.
    """
    snapshot_path = Path(snapshot_path)
    repo_root = Path(repo_root)
    try:
        zf = zipfile.ZipFile(snapshot_path, "r")
    except Exception as exc:
        return RestoreResult(
            snapshot_path=str(snapshot_path),
            dry_run=False,
            operations=tuple(),
            restored_count=0,
            overwrite_count=0,
            skipped_count=0,
            missing_count=0,
            error_message=f"cannot open snapshot: {exc}",
        )
    try:
        try:
            payload = _read_manifest_from_zip(zf)
        except Exception as exc:
            return RestoreResult(
                snapshot_path=str(snapshot_path),
                dry_run=False,
                operations=tuple(),
                restored_count=0,
                overwrite_count=0,
                skipped_count=0,
                missing_count=0,
                error_message=f"missing manifest: {exc}",
            )

        only_set: set[str] | None = (
            set(only_files) if only_files is not None else None
        )

        ops: list[RestoreOperation] = []
        restored = 0
        overwrite = 0
        skipped = 0
        missing = 0

        for entry in payload.get("files", []):
            rel = str(entry.get("relative_path", ""))
            backup_sha = str(entry.get("sha256", "")) or None
            backup_bytes = int(entry.get("bytes", 0))

            if only_set is not None and rel not in only_set:
                # not in scope — record nothing for this entry (skipped silently)
                continue

            target = _safe_target_path(repo_root, rel)
            if target is None:
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="SKIPPED_OUT_OF_ROOT",
                        backup_sha256=backup_sha,
                        current_sha256=None,
                        backup_bytes=backup_bytes,
                        current_bytes=None,
                    )
                )
                skipped += 1
                continue

            # Read backup bytes
            try:
                with zf.open(rel, "r") as src:
                    data = src.read()
            except Exception as exc:
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="SKIPPED_READ_ERROR",
                        backup_sha256=backup_sha,
                        current_sha256=None,
                        backup_bytes=backup_bytes,
                        current_bytes=None,
                    )
                )
                skipped += 1
                continue

            # Determine pre-action state
            current_existed = target.exists()
            current_sha = None
            current_bytes_val = None
            if current_existed:
                try:
                    current_sha = _sha256_file(target)
                    current_bytes_val = target.stat().st_size
                except Exception:
                    pass
                if current_sha == backup_sha:
                    ops.append(
                        RestoreOperation(
                            file_path=rel,
                            action="SKIPPED_UNCHANGED",
                            backup_sha256=backup_sha,
                            current_sha256=current_sha,
                            backup_bytes=backup_bytes,
                            current_bytes=current_bytes_val,
                        )
                    )
                    skipped += 1
                    continue

            # Atomic write: temp file in target's parent, then os.replace
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp_fd, tmp_name = tempfile.mkstemp(
                    prefix=".restore-", suffix=".tmp", dir=str(target.parent)
                )
                try:
                    with os.fdopen(tmp_fd, "wb") as out:
                        out.write(data)
                    os.replace(tmp_name, target)
                except Exception:
                    try:
                        os.unlink(tmp_name)
                    except Exception:
                        pass
                    raise
            except Exception as exc:
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="SKIPPED_WRITE_ERROR",
                        backup_sha256=backup_sha,
                        current_sha256=current_sha,
                        backup_bytes=backup_bytes,
                        current_bytes=current_bytes_val,
                    )
                )
                skipped += 1
                continue

            if current_existed:
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="RESTORED_OVERWRITE",
                        backup_sha256=backup_sha,
                        current_sha256=current_sha,
                        backup_bytes=backup_bytes,
                        current_bytes=current_bytes_val,
                    )
                )
                overwrite += 1
            else:
                ops.append(
                    RestoreOperation(
                        file_path=rel,
                        action="RESTORED_NEW",
                        backup_sha256=backup_sha,
                        current_sha256=None,
                        backup_bytes=backup_bytes,
                        current_bytes=None,
                    )
                )
                missing += 1
            restored += 1

        return RestoreResult(
            snapshot_path=str(snapshot_path),
            dry_run=False,
            operations=tuple(ops),
            restored_count=restored,
            overwrite_count=overwrite,
            skipped_count=skipped,
            missing_count=missing,
            error_message=None,
        )
    finally:
        zf.close()


def manifest_to_dict(m: BackupManifest) -> dict:
    return asdict(m)


def result_to_dict(r: RestoreResult) -> dict:
    return asdict(r)


__all__ = [
    "DEFAULT_BACKUP_FILES",
    "BackupManifest",
    "RestoreOperation",
    "RestoreResult",
    "create_backup",
    "list_backups",
    "evaluate_restore",
    "execute_restore",
    "manifest_to_dict",
    "result_to_dict",
]
