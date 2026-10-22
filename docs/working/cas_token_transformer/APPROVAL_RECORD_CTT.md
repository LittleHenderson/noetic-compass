# Approval record — CTT-1, the CAS-token transformer ("ears first") — v3 (amendments A-CTT-1 and A-CTT-2)

This record quotes the owner's line and names the package and the exam-seed hash. The builder wrote it; it records
the owner's words and is not a new signature. It supersedes the v1 (`3289755c…`, never launched) and v2
(`83bfa752…`, job c43 stopped in preflight) records.

**The owner's verbatim pre-approval (2026-10-19):**

`I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.`

- Source: `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, line 142; line sha256
  `2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00`. The coordinator's mapping there: one attempt + one plumbing retry,
  cap 8.00 USD; any change of scope, package or cap needs a new owner word (so whether this v3 package needs one is
  the coordinator's / owner's call).

| Role | Item | sha256 |
|---|---|---|
| **PACKAGE (the code that runs)** | `HELM_CTT_20261019_SOURCE_CTT.zip` v3 | `f280633da498466fe713b33d37fe90db221bc3dbf4ce9fe69538460be82cee31` |
| package freeze | `PACKAGE_FREEZE.json` | `24f8971865f6d88f932a75ab400c9af593a04440e157ae67710906e3cfb5499c` |
| deps (unchanged) | `HELM_CTT_DEPS_20261019.zip` | `fc89054a6893a149301ee8504dbd325e7b46a75b0152d80622e4096cf06acd3f` |
| **EXAM-SEED hash** | the v2 zip the two exams were drawn from | `83bfa752cb109383783614fdb9341b9b4c87349baa40c436141927485f92f7ec` |
| sealed exam (primary) | E-MACHINE-S manifest | `12061e67347e73b0753ba705a3dd7f5bd5c7bc3312d1c7b4125400550ed0ecf4` |
| sealed exam (second pass) | manifest | `be3895ff25fa58e39f1e3aa9f0c6f10a129b4dd6667aca9b4adfe5992a22ce61` |
| preregistration (with sections 17 and 18) | `PREREGISTRATION_CTT.md` | `00027ddfb90cdb19b017a57995de894022cc2ac0971432b443a92223f50ce3fe` |

**Exam seed:** `sha256(UTF-8(owner line + ":" + 83bfa752cb109383783614fdb9341b9b4c87349baa40c436141927485f92f7ec))`. Both exams were drawn blind before v3 existed and stay
valid; the builder holds only their hashes. The frozen reader, the host runners (`--exam-seed-zip-sha256`) and the
custody tools check the seed against this EXAM-SEED hash, not against the running zip.

**Cap:** 8.00 USD in total; 0.21 USD spent (job c43). **Attempts:** one attempt + one plumbing retry for v3.

**Amendment A-CTT-2:** the translator's write-audit allows its own audit log, the null device, its own temporary
folder and the torch / CUDA caches; any write under the brain, wave packages, store, receipts, exams, data or
weights still fails; a missing audit still fails. No mark, arm, threshold, data or model change.
