# CAS Forex Operations Runbook

This runbook is for operating the local CAS Forex stack on the owner laptop and
phone. It is operational guidance, not trading advice, legal advice, broker
advice, or a promise of profitable results.

## Health Checks

Use these surfaces before trusting the app state:

- API health: `http://127.0.0.1:8765/health`
- Forex API health: `http://127.0.0.1:8765/api/forex/health`
- Stack status: `http://127.0.0.1:8765/api/forex/stack-health/check`
- System health: `http://127.0.0.1:8765/api/forex/system-health/snapshot`
- Settings diagnostics: Security Posture, Professional Claims, Broker Symbol Diagnostics, and Operational Readiness

The UI production preview normally serves from `http://127.0.0.1:4173`.

## Process Topology

CAS Forex currently uses one stateful API owner process. The AI Operator,
dispatch loop, proof runner, route caches, and MT5 IPC cache are process-local.
LAN and phone clients share the same API worker; they do not require extra
workers.

Start the supported topology with:

```powershell
python scripts/run_api_server.py --host 0.0.0.0 --port 8765 --workers 1
```

The launcher refuses worker counts above one. An OS-held owner lease also
prevents a second API process from restoring the autonomous loops if the
wrapper is bypassed. Inspect current ownership at:

- Runtime topology: `http://127.0.0.1:8765/api/forex/runtime-topology`
- Settings: Runtime Process Topology

Do not launch `uvicorn --workers 2` for this app. Multi-worker scale-out remains
unsupported until autonomous control state and loop execution are moved to a
shared external runtime. On graceful shutdown, the owner process stops its
in-process loops without clearing the owner's persisted desired state, writes
a `STOPPED` topology packet, and releases the lease.

## Logs

Operational logs and traces are local files:

- API request trace: `runtime/api-request-trace.jsonl`
- Worker logs: `runtime/worker-logs/*.log`
- Operator audit: `evidence_runs/operator_audit/operator-audit.jsonl`
- Agent workflow events: `evidence_runs/agent_workflow_queue/*.jsonl`
- Terminal receipt and history evidence: `evidence_runs/terminal_*`

When investigating a failed action, preserve the relevant log and evidence
files before restarting processes.

## External Monitoring

For hosted or always-on operation, configure off-machine monitoring before
relying on the system unattended. The local app can expose health endpoints, but
an external monitor must be configured by the owner/deployment environment.

Health URLs to monitor:

- `/health`
- `/api/forex/health`
- `/api/forex/stack-health/check`
- `/api/forex/system-health/snapshot`

Environment variables recognized by the readiness report:

- Uptime monitor or heartbeat URL: `CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL`, `CAS_FOREX_UPTIME_MONITOR_URL`, `CAS_FOREX_HEALTHCHECKS_PING_URL`, or `HEALTHCHECKS_PING_URL`
- Error tracking DSN: `CAS_FOREX_ERROR_TRACKING_DSN` or `SENTRY_DSN`
- Off-screen critical alert webhook: `CAS_FOREX_ALERT_WEBHOOK_URL`, `CAS_FOREX_CRITICAL_WEBHOOK_URL`, or `CAS_FOREX_WEBHOOK_NOTIFICATION_URL`

Template file for hosted deployment handoff:

- `docs/operations/CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example`

These hooks can be supplied either through deployment env vars or through the
owner Settings surface / `POST /api/forex/external-monitoring/update` local
runtime override. Runtime overrides are stored as local encrypted envelopes and
reported only as masked hints.

The readiness report masks configured values. Do not commit real monitor URLs,
Sentry DSNs, or webhook URLs to the repo. Store them in the deployment
environment, the in-app encrypted runtime override, or a secret manager.

## Backup

Operator-critical state is backed up with `cas_forex.backup_restore`. The
backup archive includes the manifest plus selected state files such as strategy
leads, agent memory reports, event journals, push/webhook subscriptions, and
operator audit logs.

Recommended snapshot locations:

- `runtime/backups`
- `evidence_runs/backups`

Create a backup before large configuration changes, live-mode permission
changes, strategy imports, or cleanup work.

## Restore

Restore must be evaluated before writing files:

1. Use the restore evaluator to inspect what would be overwritten, restored, or skipped.
2. Confirm the snapshot path and manifest match the intended backup.
3. Restore only the required files when possible.
4. Reopen the app and verify Settings diagnostics, Stack Status, account reconciliation, and Operator state.

The restore primitive writes atomically and refuses paths outside the repo root.

## Rollback

Rollback means returning to a previous build and a known-good operator state:

1. Stop the active local API/UI preview processes.
2. Keep the current logs and evidence files for diagnosis.
3. Restore the previous build artifacts or rebuild the previous code revision.
4. Restore the selected backup snapshot after dry-run review.
5. Start the API and UI preview again.
6. Verify health, stack status, broker/account reconciliation, and Settings diagnostics before enabling automation.

For UI rollback, use the previous build output when available. If only source is
available, rebuild the previous revision with `npm --prefix ui run build` and
serve the production preview again.

## Build And Preview

After UI changes:

```powershell
npm --prefix ui run build
```

For a local production preview, serve `ui/dist` on the expected preview port
used by the stack runner.

## Emergency Operating Notes

Keep emergency controls visible in the app:

- Use the dashboard Emergency Stop button to latch auto-halt and stop the
  dispatch/WASTE automation loops.
- Treat Emergency Stop as a new-automation stop, not as a broker flatten
  command. Existing open positions and pending orders remain in the broker
  terminal unless a tested owner-confirmed close/cancel route is added.
- Use broker/terminal controls for urgent existing-position management.
- Refresh broker truth, account reconciliation, and auto-halt status after any
  terminal-side close, cancel, or modification.
- Preserve logs before and after emergency actions

Broker execution, fills, pricing, margin, account restrictions, deposits,
withdrawals, and platform availability remain broker-controlled.
