# APPROVAL RECORD — RB-W1T (sealed test of the wide recipe brain)

Machine copy: `APPROVAL_RECORD_RBW1T.json` (sha256 `97fb18aeb54b731943f9e32ce326047801b3835bf87af9c5eb961787f2cf0045`).
This replaces the sign request: the owner pre-approved the test, so no new sign line is asked for.

| Item | Value |
|---|---|
| Owner's line (verbatim) | `WIDE TEST at 1 USD` |
| UTF-8 bytes (by program) | 18 |
| sha256 of the line (by program) | `759046548efa99a177ce6286d69c825b9bc5c09d7ac57c3f21fd3379d9d8ed8e` |
| Where recorded | `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, heading "Owner pre-approval (2026-10-19, verbatim)" |
| Package zip | `HELM_RBW1T_20261019_SOURCE_RBW1T.zip`, sha256 `b50f4ca42178d4c43e43945267cc980aebd05a10f8e0d932d00e3eabd4495809` |
| Package freeze | `PACKAGE_FREEZE.json`, sha256 `fadf08f6faf13ebcdb633b7894ebe515838465c52a90c51f6507f2371a28f8b1` |
| Cap | **1.00 USD** for both tries together |
| Attempts | one scored attempt + one plumbing retry (only if no scored unit started; same zip, same carrier) |
| Seed source | sha256 of the UTF-8 bytes of `WIDE TEST at 1 USD` + `:` + the full zip sha256 above (no trailing newline); band RW 1,950,000,001-1,951,000,000 |

**One reading, stated.** The approvals file writes the line inside its own quotes as `"WIDE TEST at 1 USD".` (the
owner's quote marks and a period). The coordinator's message names the verbatim line as `WIDE TEST at 1 USD`; that is
the line used here and in the seed rule. The record pins its bytes and hash, so the seed cannot drift.

Any change of scope, package or cap needs a new owner word. The builder did not compute the seed; the custodian's
sealed program does.
