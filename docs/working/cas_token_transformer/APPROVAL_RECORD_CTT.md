# Approval record — CTT-1, the CAS-token transformer ("ears first") — v2 (amendment A-CTT-1)

This record quotes the owner's line and names the final sealed package. The builder wrote it. It records the owner's
words; it is not a new signature. It supersedes the v1 record of zip `3289755c…` (never launched).

**The owner's verbatim pre-approval (2026-10-19):**

`I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.`

- Source: `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, line 142. The coordinator's mapping there: CTT,
  one attempt + one plumbing retry, cap 8.00 USD; any change of scope, package or cap needs a new owner word.
- Line sha256: `2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00`.

**The sealed package this approval binds to (v2):**

| Item | sha256 |
|---|---|
| `HELM_CTT_20261019_SOURCE_CTT.zip` | `83bfa752cb109383783614fdb9341b9b4c87349baa40c436141927485f92f7ec` |
| its `PACKAGE_FREEZE.json` | `c07654e733f1633e90379eb91eb5c1472760402c19232c4e82829ac84de2f5af` |
| `HELM_CTT_DEPS_20261019.zip` | `fc89054a6893a149301ee8504dbd325e7b46a75b0152d80622e4096cf06acd3f` |
| `PREREGISTRATION_CTT.precode.md` | `05c99a7ec6ed008374caf5c97e9fb19ba0d81521c3a7b7c7f6e65ca965ff0f18` |
| `PREREGISTRATION_CTT.md` (with section 17, amendment A-CTT-1) | `8d16adecb0334c7e99a56e33754e10f48e6d9cdfe14de63c259d4c7061417485` |

**Cap:** 8.00 USD in total (the main run and, if it ever happens, the later human pass). **Attempts:** one attempt +
one plumbing retry.

**Amendment A-CTT-1 (coordinator, operational, before this reseal):** the primary status word is read from the
machine-side exam E-MACHINE-S (128 real sentences from X-REAL's frame, keyed by X-REAL's frozen rule, drawn blind by
the custodian). The human exam is an optional later pass against the same frozen weights, with its own status line;
it never changes the primary reading. Scope, arms, caps and thresholds unchanged.

**Exam seed:** `sha256(UTF-8(owner line + ":" + 83bfa752cb109383783614fdb9341b9b4c87349baa40c436141927485f92f7ec))`, computed by the custodian only.

**Still required before the paid run (no money, no owner word, no human writer):** the custodian draws and seals
E-MACHINE-S on the laptop (`custody/CUSTODIAN_PROCEDURE_CTT.md` section M) and stages it with the sealed-98 carrier.
