# Approval record — CTT-1, the CAS-token transformer ("ears first")

This replaces the sign request (coordinator's custody addition, 2026-10-19). It quotes the owner's line and names the
final sealed package. It is written by the builder; it is a record of the owner's words, not a new signature.

**The owner's verbatim pre-approval (2026-10-19):**

`I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.`

- Source: `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, line 142 (file sha256 `8e96a4fae4e8698aeb8ca1d82fca0fa7822c3f289e5d36949a0422feffb40b58` when read, 2026-10-20T00:21Z). The coordinator's executable mapping there: CTT, one attempt + one plumbing retry, cap 8.00 USD, on the package sealed now; any change of scope, package or cap needs a new owner word.
- Line sha256: `2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00`.

**The sealed package this approval binds to:**

| Item | sha256 |
|---|---|
| `HELM_CTT_20261019_SOURCE_CTT.zip` | `3289755c154111ce41e44bf4d17f4f6bfa14e0dff1f91d287bd5b6c74a5453ec` |
| its `PACKAGE_FREEZE.json` | `4dd5fe867755d87836014c42a6b87083c63d48e46083b4d34e0266178ddf0ba2` |
| `HELM_CTT_DEPS_20261019.zip` (byte copies of the inputs) | `fc89054a6893a149301ee8504dbd325e7b46a75b0152d80622e4096cf06acd3f` |
| `PREREGISTRATION_CTT.precode.md` | `05c99a7ec6ed008374caf5c97e9fb19ba0d81521c3a7b7c7f6e65ca965ff0f18` |

**Cap:** 8.00 USD in total. **Attempts:** one attempt + one plumbing retry (a retry only if no model was scored, same
zip, same settings).

**Exam seed:** `sha256(UTF-8(owner line + ":" + 3289755c154111ce41e44bf4d17f4f6bfa14e0dff1f91d287bd5b6c74a5453ec))`,
computed by the custodian only.

**The short line the builder's brief named** (`APPROVE CTT: CAS-token transformer ears, sealed package 3289755c, one
attempt + one plumbing retry, cap $8.00.`) is shown here for reference only. Per the coordinator, the owner's
pre-approval above plus this hash is the approval; no re-paste is requested.

**Still required before the paid run (not money, not a new owner word):**
1. The human exam E-HUMAN-W: the owner writes 64 sentences, two other people write 32 sentences + 8 short dialogues
   each, from the custodian's sheets (`custody/CUSTODIAN_PROCEDURE_CTT.md`). Then the custodian seals it.
2. The custodian stages the exam carrier and the sealed-98 carrier to the host.
