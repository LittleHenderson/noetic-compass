# APPROVAL RECORD — RB-W1T v2 (sealed test of the wide recipe brain)

Machine copy: `APPROVAL_RECORD_RBW1T.json` (sha256 `3a223136c0b6ec58a3a607ade490ad6c8b11fadb60a658a5b26c10422d754a40`). The owner pre-approved the test, so no sign line is asked
for. v2 replaces v1 (`b50f4ca4…`, VOID_SUPERSEDED_BY_V2, never launched, no seed drawn) after the coordinator's "FIX
FIRST" decision (routing and learning fixes; marks unchanged).

| Item | Value |
|---|---|
| Owner's line (verbatim, as pinned) | `WIDE TEST at 1 USD` |
| UTF-8 bytes (by program) | 18 |
| sha256 of the line (by program) | `759046548efa99a177ce6286d69c825b9bc5c09d7ac57c3f21fd3379d9d8ed8e` |
| Where recorded | `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, heading "Owner pre-approval (2026-10-19, verbatim)" |
| Package zip (v2) | `HELM_RBW1T_20261019_SOURCE_RBW1T.zip`, sha256 `7c04a40855b81c6bfc5c1a44fc4486e112fcc4bf16bc37b1e84d7b457c6b009e` |
| Package freeze (v2) | `PACKAGE_FREEZE.json`, sha256 `b22690ced5a257ec964160103a28c03cea1d5730a0d006fb22c758a1be3d5ed9` |
| Cap | **1.00 USD** for both tries together |
| Attempts | one scored attempt + one plumbing retry (only if no scored unit started; same zip, same carrier) |
| Seed source | sha256 of the UTF-8 bytes of `WIDE TEST at 1 USD` + `:` + the full v2 zip sha256 above (no trailing newline); band RW 1,950,000,001-1,951,000,000 |

**The line's form, stated.** The approvals file shows the line inside the owner's own quote marks with a trailing
period (`"WIDE TEST at 1 USD".`). The pinned 18-byte form, without the quote marks and the period, is the one used here
and in the seed rule. The record pins its bytes and hash, so the seed cannot drift.

Any change of scope, package or cap needs a new owner word. The builder did not compute the seed; the custodian's
sealed program does.
