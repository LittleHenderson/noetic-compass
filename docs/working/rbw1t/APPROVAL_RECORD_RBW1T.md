# APPROVAL RECORD — RB-W1T v3 (second sealed test of the wide recipe brain)

Machine copy: `APPROVAL_RECORD_RBW1T.json` (sha256 `954c7364efeedd61fc92e2869bdff2a5588b6aea0271bf9f99a88dac30e852ab`). The owner pre-approved this test, so no sign line is
asked for. v3 follows amendment A-RBW1T-2 (PREREGISTRATION_RBW1T.md section 19): the build under test is RB-W1 v3
(merge `65b862828399e59d6886df128aebb31bf4704d93`, the dish-name / line-splitting fix); the v2 exam (job c46) is spent;
marks, arms and thresholds are unchanged.

| Item | Value |
|---|---|
| Owner's line (verbatim, as pinned) | `WIDE TEST 2 at 1 USD` |
| UTF-8 bytes (by program) | 20 |
| sha256 of the line (by program) | `fd82691eff719a757cca296740faf5e9baf02bc8582b6650193bddb9b0878b8b` |
| Where recorded | `Documents/Codex/2026-10-18/OWNER_APPROVALS_20261018.md`, heading "Owner pre-approval (2026-10-19 evening, verbatim)" |
| Package zip (v3) | `HELM_RBW1T_20261019_SOURCE_RBW1T.zip`, sha256 `3a8ae37eb51c18414bfa83a71b9079dd7ec2282bec6ba3952d86ac0454f0e967` |
| Package freeze (v3) | `PACKAGE_FREEZE.json`, sha256 `04eef88645acbd0c89de9e6e914d8faf2896939769e11f4d4c93f2dfc12e84f4` |
| Cap | **1.00 USD** for both tries together |
| Attempts | one scored attempt + one plumbing retry (only if no scored unit started; same zip, same carrier) |
| Seed source | sha256 of the UTF-8 bytes of `WIDE TEST 2 at 1 USD` + `:` + the full v3 zip sha256 above (no trailing newline); band RW2 1,952,000,001-1,953,000,000 |
| Supersedes | v2 zip `7c04a408…` SPENT_BY_C46 (its record kept as `v2_spent_APPROVAL_RECORD_RBW1T.json`) |

**The line's form, stated.** The approvals file shows the line inside the owner's own quote marks. The pinned 20-byte
form, without the quote marks, is the one used here and in the seed rule. The record pins its bytes and hash, so the
seed cannot drift.

Any change of scope, package or cap needs a new owner word. The builder did not compute the seed; the custodian's
sealed program does.
