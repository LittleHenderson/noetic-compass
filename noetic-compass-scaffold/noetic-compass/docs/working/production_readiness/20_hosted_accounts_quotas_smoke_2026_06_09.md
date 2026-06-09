# Hosted Accounts + Quotas Smoke Runbook - 2026-06-09

Purpose: run black-box hosted smoke checks after deploying a launch candidate with:

- `NC_ACCOUNTS_ENABLED=true`
- `NC_QUOTAS_ENABLED=true`
- durable account/session/state stores installed

These scripts are intentionally honest. They do not create the first operator/admin account and they do not pretend a disabled-account check passed when no hosted admin-disable route exists.

## Account-Mode Smoke

Dry run:

```powershell
python scripts/hosted_account_mode_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token "<OPERATOR_OR_ADMIN_ACCOUNT_MODE_JWT>" `
  --mint-secret "<NC_AUTH_MINT_SECRET>" `
  --dry-run
```

Core account/session smoke:

```powershell
python scripts/hosted_account_mode_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token "<OPERATOR_OR_ADMIN_ACCOUNT_MODE_JWT>" `
  --mint-secret "<NC_AUTH_MINT_SECRET>"
```

Expected current behavior if no admin-disable endpoint has shipped:

- invite create/redeem/login runs first
- durable `jti` is checked on operator and redeemed member tokens
- logout revocation is checked
- admin revoke is checked if `/auth/sessions/{jti}/revoke` exists
- final exit is nonzero with a clear disabled-account blocker

To run the rest as a scaffold while the admin-disable route is still missing:

```powershell
python scripts/hosted_account_mode_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token "<OPERATOR_OR_ADMIN_ACCOUNT_MODE_JWT>" `
  --mint-secret "<NC_AUTH_MINT_SECRET>" `
  --allow-missing-disabled-account-check
```

Once a hosted disable route exists, wire it explicitly:

```powershell
python scripts/hosted_account_mode_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token "<OPERATOR_OR_ADMIN_ACCOUNT_MODE_JWT>" `
  --mint-secret "<NC_AUTH_MINT_SECRET>" `
  --disable-account-endpoint "/accounts/{account_id}/disable" `
  --disable-account-method POST
```

Optional audit/evidence ownership smoke:

```powershell
python scripts/hosted_account_mode_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token "<OPERATOR_OR_ADMIN_ACCOUNT_MODE_JWT>" `
  --mint-secret "<NC_AUTH_MINT_SECRET>" `
  --allow-missing-disabled-account-check `
  --check-audit-evidence
```

Optional anchor RBAC scaffold:

```powershell
python scripts/hosted_account_mode_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token "<OPERATOR_OR_ADMIN_ACCOUNT_MODE_JWT>" `
  --mint-secret "<NC_AUTH_MINT_SECRET>" `
  --allow-missing-disabled-account-check `
  --check-audit-evidence `
  --check-anchor
```

Anchor note: the scaffold expects member anchor to return `403`. A same-tenant operator/admin may then reach route-level behavior such as `200`, `404`, or `409` depending on whether the produced trace is anchorable and whether Object Lock is configured.

## Quota Smoke

Dry run:

```powershell
python scripts/hosted_quota_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token "<ACCOUNT_MODE_JWT_TO_METER>" `
  --dry-run
```

Run until the tenant hits quota:

```powershell
python scripts/hosted_quota_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token "<ACCOUNT_MODE_JWT_TO_METER>" `
  --max-attempts 105
```

Pass condition:

- `POST /api/cas-harness/audit/session` returns HTTP `429`
- response JSON has `detail.error == "quota_exceeded"`

If the script creates `--max-attempts` audit sessions without a `quota_exceeded` response, quota enforcement is not proven. Likely causes:

- `NC_QUOTAS_ENABLED` is off
- quota route wiring is absent from the deployed branch
- tenant cap is higher than `--max-attempts`
- deployed candidate does not include the quota branch

## Bootstrap Boundary

Hosted account-mode smoke requires an existing operator/admin/owner identity. If no `--bearer-token` or `--operator-username` plus `--mint-secret` is supplied, the script fails before pretending it can bootstrap the first privileged account through public routes.

## Claim Language

These smokes prove hosted product readiness only for the checked flows. They do not convert any research packet to customer-production `ACCEPT`. Pythia-160M remains `FLAG_FOR_HUMAN_REVIEW`; unresolved paid/billing/compliance items remain `OPEN`.
