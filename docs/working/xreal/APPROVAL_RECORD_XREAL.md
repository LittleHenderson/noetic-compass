# Approval record: HELM-R1 X-REAL (v2 final seal), 2026-10-19 Pacific

Written by the X-REAL builder from the owner-evidence file; it replaces `OWNER_SIGN_REQUEST_X_REAL.md` (now kept as
`v1_void_OWNER_SIGN_REQUEST_X_REAL.md`, VOID: its package `c275daed…` was superseded before anyone signed).

**The owner's words (2026-10-19, verbatim, as recorded in `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`):**

> I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.

- Line bytes: 121 UTF-8 bytes (three spaces after the colon), sha256
  `2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00`.
- Executable mapping (the coordinator's operational rule, written in the same file before this seal): X-REAL, one
  attempt + one plumbing retry, **cap 1.00 USD**; approval record = this verbatim line + the final sealed package
  sha256; any change of scope, package or cap needs a new owner word.

**The package this record binds (final; no further change):**

| Item | Value |
|---|---|
| Zip | `HELM_XREAL_20261019_SOURCE_XREAL.zip`, sha256 `a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249` |
| `PACKAGE_FREEZE.json` | sha256 `67b485415078ca11c5c3d984cd3f82a6a1ab1f111efc9ce2a619d3c136c8006d` (53 members) |
| Source pins | `SOURCES_PINNED.json` `24cfb0d17c0cea0602a907e5b4537fbace8fd01e4d1ebddbb4530b5da659fbdd` (a freeze member) |
| Cap / attempts | 1.00 USD; one scored attempt + at most one plumbing retry |

**Exam seed source (A-XR-18):** sha256 of the UTF-8 bytes of
`<the owner's line above, verbatim>` + `:` + `a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249`.
The custodian runs `xreal.seed_rule_xreal --line-file <line> --zip <this zip>` (it hashes the zip itself) and
`custody_xr seal --zip <this zip>`; both refuse any other zip.

**For the reader's `MERGE_INPUT_XREAL.json` `approval` field:** `owner_line_verbatim` (the line above),
`owner_line_sha256` `2a8a6f86…6e00`, `package_zip_sha256` `a9b4c954…c249`, `package_freeze_sha256` `67b48541…006d`,
`cap_usd` 1.00, `attempts` "one scored + one plumbing retry", `superseded_by` null.

**What changed from v1 (coordinator decision, operational):** both recipe parts were rebuilt so they are not vacuous —
a second recipe is paired only if it holds ALL of the first recipe's ingredients in the same units, and the brain is
taught one witnessed lesson per ingredient with the others in surplus (twice their listed amount), so each lesson has
one ingredient that runs out first. On the published practice seed, 64 of 64 drawn R-REBOUND recipes have an
answerable key; on 16 practice recipes, 15 had every ingredient learned (the 16th uses 1/3, which the brain cannot hold
exactly). The sentence part and the fault part are unchanged.

**Status:** sealed, NOT LAUNCHED, no ledger hold. Next: the custodian (`xr_contract/XREAL_CUSTODIAN_CONTRACT.md`), then
one m6i.xlarge run per `LAUNCH_BRIEF_XREAL_20261019.md`.
