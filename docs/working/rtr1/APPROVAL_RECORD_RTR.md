# Approval record: RTR-1 "RE-TEST READER", 2026-10-19 Pacific

Written by the RTR-1 builder from the owner-evidence file. It quotes the owner; it is not an owner signature.

**The owner's words (2026-10-19, verbatim, as recorded in `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`,
on the line starting `## Owner order (2026-10-19, verbatim):`, the text after `verbatim): ` to the end of the line):**

> "RE-TEST READER" (0.03 USD) and "WIDEN THE BRAIN" (0 USD to build)."

- Line bytes: 68 UTF-8 bytes, sha256 `b645e4f482e10e3caa1f6e497f304ebc13faf481ff1345b2099c3f1358bc60e4`. Extracted
  by program (`rtr.seed_rule_rtr line`), never typed. Only the "RE-TEST READER" part applies to this package.
- Executable mapping (the coordinator's, same file): fresh custodian draw from the X-REAL pool excluding the X-REAL 128
  and the CTT primary 128; same fixed answer rule; one small AWS CPU job; **cap 0.10 USD** (expected about 0.03); one
  attempt + one plumbing retry; seed source = sha256(this verbatim owner line + ":" + the package zip sha256).

**The package this record binds (final; no further change):**

| Item | Value |
|---|---|
| Zip | `HELM_RTR1_20261019_SOURCE_RTR1.zip`, sha256 `e201feb6e5fd4eaf1d9b9060ed100a9db6150257c2d0b64d230ad81c4042f7a8` |
| `PACKAGE_FREEZE.json` | sha256 `6a622106aa1a57c23ec5ad03f8f687fd20653772413404cb9eda3b57aa956cf3` (27 members) |
| Preregistration | `PREREGISTRATION_RTR.md` (a member); precode sha256 `4992783e55e23a8be7daf3c9046c1938efa332507558242ebcc57cf99f52404b` |
| Cap / attempts | 0.10 USD; one scored attempt + at most one plumbing retry |

**Exam seed source:** sha256 of the UTF-8 bytes of `<the owner's line above, verbatim>` + `:` +
`e201feb6e5fd4eaf1d9b9060ed100a9db6150257c2d0b64d230ad81c4042f7a8`. The custodian runs `rtr.seed_rule_rtr derive
--zip <this zip>` (it hashes the zip itself) and `rtr.custody_rtr seal --zip <this zip>`; both refuse any other zip
or line. The machine-readable copy is `APPROVAL_RECORD_RTR.json` (the reader's I9 reads it).

**Status:** sealed, NOT LAUNCHED, no ledger hold. Next: the custodian (`CUSTODIAN_PROCEDURE_RTR.md`), then one small
CPU host per `LAUNCH_BRIEF_RTR.md`. Any change of scope, package or cap needs a new owner word.
