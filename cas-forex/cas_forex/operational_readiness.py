"""Read-only production operations readiness report for CAS Forex.

The app already has stack-health and backup primitives. This report gives the
owner one place to see whether the operational basics are present: health
surfaces, logs, backup snapshots, runbooks, build artifacts, and rollback
instructions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from cas_forex.backup_restore import list_backups
from cas_forex.external_monitoring import build_external_monitoring_readiness


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATIONS_RUNBOOK = Path("docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md")
MOBILE_RUNBOOK = Path("docs/MOBILE_APP.md")
DISCLOSURE_DRAFT = Path("docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md")
TRACE_PATH = Path("runtime/api-request-trace.jsonl")
WORKER_LOG_DIR = Path("runtime/worker-logs")
BACKUP_DIRS = (Path("runtime/backups"), Path("evidence_runs/backups"))

CLAIM_BOUNDARY = (
    "Operational readiness is a read-only production-operations diagnostic. "
    "It reports whether health, logging, backup, runbook, build, and rollback "
    "evidence exists. It does not restart processes, restore backups, place "
    "orders, close positions, move money, or authorize live trading."
)


def build_operational_readiness_report(
    root: Path | str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    notification_readiness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    backups = _backup_inventory(base)
    runbook_text = _read_text(base / OPERATIONS_RUNBOOK)
    external_monitoring = build_external_monitoring_readiness(
        base,
        env=env,
        notification_readiness=notification_readiness,
    )
    checks = [
        _paths_check(
            base,
            "health_surfaces",
            "Health Surfaces",
            [
                Path("api/routes/system_health.py"),
                Path("api/routes/stack_health.py"),
                Path("cas_forex/system_health_monitor.py"),
                Path("cas_forex/stack_health_check.py"),
            ],
            "System and stack health endpoints are present.",
            "Add API/system-health and API/stack-health route coverage.",
        ),
        _file_or_parent_check(
            base,
            "request_trace",
            "Request Trace",
            TRACE_PATH,
            "API request tracing path exists or can be created under runtime/.",
            "Create runtime/ or let the API write its first request trace.",
        ),
        _log_dir_check(base),
        _paths_check(
            base,
            "backup_restore_primitive",
            "Backup/Restore Primitive",
            [Path("cas_forex/backup_restore.py"), Path("tests/test_backup_restore.py")],
            "Backup/restore primitive and regression tests are present.",
            "Add tested backup/restore primitives for operator-critical state.",
        ),
        _backup_snapshot_check(backups),
        _paths_check(
            base,
            "operations_runbook",
            "Operations Runbook",
            [OPERATIONS_RUNBOOK],
            "Operations runbook exists.",
            "Create docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md.",
        ),
        _runbook_section_check(
            "rollback_runbook",
            "Rollback Instructions",
            runbook_text,
            ("rollback", "previous build", "restore"),
            "Runbook includes rollback and restore guidance.",
            "Add rollback, previous-build, and restore instructions to the operations runbook.",
        ),
        _paths_check(
            base,
            "phone_runbook",
            "Phone/Web Runbook",
            [MOBILE_RUNBOOK],
            "Phone/web startup and verification runbook exists.",
            "Keep docs/MOBILE_APP.md available for laptop and phone startup.",
        ),
        _paths_check(
            base,
            "risk_disclosure_draft",
            "Risk Disclosure Draft",
            [DISCLOSURE_DRAFT],
            "Risk and AI disclosure draft exists.",
            "Create the disclosure draft before public-facing release.",
        ),
        _paths_check(
            base,
            "production_ui_build",
            "Production UI Build",
            [Path("ui/dist/index.html")],
            "Production UI build artifact exists.",
            "Run npm --prefix ui run build before serving the production preview.",
        ),
        _external_monitoring_check(external_monitoring),
    ]
    attention = [check for check in checks if check["status"] != "OK"]
    top_attention_items = [str(check["detail"]) for check in attention if str(check.get("detail") or "").strip()][:6]
    return {
        "report_kind": "cas_forex_operational_readiness",
        "status": "OK" if not attention else "ATTENTION",
        "ok_count": sum(1 for check in checks if check["status"] == "OK"),
        "attention_count": len(attention),
        "checks": checks,
        "attention_items": [check["detail"] for check in attention],
        "top_attention_items": top_attention_items,
        "next_action": (
            "Operational readiness checks pass."
            if not attention
            else str(top_attention_items[0])
        ),
        "backup_inventory": backups,
        "external_monitoring": external_monitoring,
        "runbook_path": OPERATIONS_RUNBOOK.as_posix(),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _paths_check(
    base: Path,
    key: str,
    label: str,
    paths: Iterable[Path],
    ok_detail: str,
    missing_detail: str,
) -> dict[str, Any]:
    rows = [{"path": path.as_posix(), "present": (base / path).exists()} for path in paths]
    missing = [row["path"] for row in rows if not row["present"]]
    return {
        "key": key,
        "label": label,
        "status": "OK" if not missing else "MISSING",
        "detail": ok_detail if not missing else missing_detail,
        "evidence": rows,
        "missing_paths": missing,
    }


def _file_or_parent_check(
    base: Path,
    key: str,
    label: str,
    path: Path,
    ok_detail: str,
    missing_detail: str,
) -> dict[str, Any]:
    file_present = (base / path).exists()
    parent_present = (base / path.parent).exists()
    return {
        "key": key,
        "label": label,
        "status": "OK" if file_present or parent_present else "ATTENTION",
        "detail": ok_detail if file_present or parent_present else missing_detail,
        "evidence": [
            {"path": path.as_posix(), "present": file_present},
            {"path": path.parent.as_posix(), "present": parent_present},
        ],
        "missing_paths": [] if file_present or parent_present else [path.parent.as_posix()],
    }


def _log_dir_check(base: Path) -> dict[str, Any]:
    log_dir = base / WORKER_LOG_DIR
    logs = sorted((p for p in log_dir.glob("*.log") if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True) if log_dir.exists() else []
    return {
        "key": "worker_logs",
        "label": "Worker Logs",
        "status": "OK" if logs else "ATTENTION",
        "detail": (
            f"Worker log directory has {len(logs)} log file(s)."
            if logs
            else "No worker log files found yet; background worker runs will create runtime/worker-logs/*.log."
        ),
        "evidence": [
            {"path": WORKER_LOG_DIR.as_posix(), "present": log_dir.exists(), "log_count": len(logs)},
            *[
                {"path": str(path.relative_to(base)).replace("\\", "/"), "present": True}
                for path in logs[:3]
            ],
        ],
        "missing_paths": [] if logs else [WORKER_LOG_DIR.as_posix()],
    }


def _backup_inventory(base: Path) -> dict[str, Any]:
    snapshots: list[dict[str, Any]] = []
    dirs: list[dict[str, Any]] = []
    for rel_dir in BACKUP_DIRS:
        full = base / rel_dir
        exists = full.exists()
        dirs.append({"path": rel_dir.as_posix(), "present": exists})
        if not exists:
            continue
        for manifest in list_backups(full):
            snapshots.append(
                {
                    "snapshot_id": manifest.snapshot_id,
                    "created_at_iso": manifest.created_at_iso,
                    "snapshot_path": _relative_or_string(base, Path(manifest.snapshot_path)),
                    "file_count": manifest.file_count,
                    "total_bytes": manifest.total_bytes,
                }
            )
    snapshots.sort(key=lambda item: str(item.get("created_at_iso") or ""), reverse=True)
    return {
        "snapshot_count": len(snapshots),
        "latest_snapshot": snapshots[0] if snapshots else None,
        "snapshot_dirs": dirs,
        "snapshots": snapshots[:5],
    }


def _backup_snapshot_check(backups: dict[str, Any]) -> dict[str, Any]:
    count = int(backups.get("snapshot_count") or 0)
    latest = backups.get("latest_snapshot") if isinstance(backups.get("latest_snapshot"), dict) else None
    return {
        "key": "backup_snapshots",
        "label": "Backup Snapshots",
        "status": "OK" if count > 0 else "ATTENTION",
        "detail": (
            f"{count} backup snapshot(s) found; latest {latest.get('created_at_iso')}."
            if latest
            else "No operator-state backup snapshots found in runtime/backups or evidence_runs/backups."
        ),
        "evidence": backups.get("snapshot_dirs", []),
        "missing_paths": [] if count > 0 else [path.as_posix() for path in BACKUP_DIRS],
    }


def _external_monitoring_check(report: dict[str, Any]) -> dict[str, Any]:
    attention = int(report.get("attention_count") or 0)
    return {
        "key": "external_monitoring",
        "label": "External Monitoring",
        "status": "OK" if report.get("status") == "OK" else "ATTENTION",
        "detail": (
            "External uptime, error tracking, and alert hooks are configured."
            if report.get("status") == "OK"
            else report.get("next_action")
            or "External uptime/error monitoring needs deployment configuration."
        ),
        "evidence": [
            {"report_kind": report.get("report_kind"), "status": report.get("status")},
            {"health_endpoints": report.get("health_endpoints", [])},
        ],
        "missing_paths": [],
        "missing_terms": [f"{attention} external monitoring attention item(s)"] if attention else [],
    }


def _runbook_section_check(
    key: str,
    label: str,
    text: str,
    required_terms: tuple[str, ...],
    ok_detail: str,
    missing_detail: str,
) -> dict[str, Any]:
    lowered = text.lower()
    missing_terms = [term for term in required_terms if term not in lowered]
    return {
        "key": key,
        "label": label,
        "status": "OK" if text and not missing_terms else "MISSING",
        "detail": ok_detail if text and not missing_terms else missing_detail,
        "evidence": [{"term": term, "present": term not in missing_terms} for term in required_terms],
        "missing_paths": [] if text else [OPERATIONS_RUNBOOK.as_posix()],
        "missing_terms": missing_terms,
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _relative_or_string(base: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except OSError:
        return str(path)
    except ValueError:
        return str(path)
