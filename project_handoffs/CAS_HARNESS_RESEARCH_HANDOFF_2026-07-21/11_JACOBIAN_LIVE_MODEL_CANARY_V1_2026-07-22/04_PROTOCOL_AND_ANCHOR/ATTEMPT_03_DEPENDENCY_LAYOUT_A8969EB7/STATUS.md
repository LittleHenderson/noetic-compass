# Attempt 3 pre-execution supersession status

Controlling status:

RFC3161_ANCHOR_VERIFIED / SUPERSEDED_PRE_EXECUTION_BYTECODE_GUARD_DEFECT / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED

Attempt 3 was successfully RFC3161-anchored, but it was never executed. A
prelaunch code audit found that the frozen seccomp wrapper invokes its execve
child with Python -I but without Python -B. The runner verifies the exact
15-file dependency root and then imports torch, transformers, and jlens.
Without child -B, those imports may generate jlens/__pycache__/*.pyc after the
root is verified. The outer interpreter's -B flag does not survive execve, and
-I ignores PYTHON* environment fallbacks.

Running this anchored identity would therefore risk corrupting the evidence
root after verification. The verifier was not weakened and no ad hoc
permission or read-only filesystem workaround was accepted. Attempt 3 is
superseded before official wrapper launch. Corrected code requires a new
commit, tree, bundle, PRE, protocol, nonce, RFC3161 query, anchor, and run ID.
Do not execute or reuse this Attempt 3 identity.

## Retained anchored identity

- Fresh run ID: jlcv1-rfc3161-cfbe168004fb3677b3f7be08c3c15d87577fa75b554d4c93391d758d23015af3
- Frozen commit: a8969eb71c6d3e5c43d7ee2b7c7d4aa90dd70fc0
- Frozen tree: cce2d477bb0f423ee6a2669ee680eaac7b999322
- Research pod at final recovery recheck: zp2s9pscgncn0b
- Production pod: hilj2rzs54gi06, not used or changed
- PRE main SHA-256: a728ba85f813cf936ef55c5d8fd544551994b97f755d5946487a7e9be3ddefd0
- Protocol SHA-256: e5f6f8c527d6e9cc788853334b49108d036c7a6d867f6e882d0a57bae71497ef
- Anchor-payload SHA-256: 8da22f257d0e799f08f7c543f391a6663879d1258f587dc5d1e473136bb13dc4
- RFC3161 query: 104 bytes, SHA-256 9f5bbed1764fb69ed5aac28f8db8bbaa168b668e65eca5a7af8d87c02bbc6291
- RFC3161 response: 6034 bytes, SHA-256 30b71774bb4b09e3889305e0f336d176dc57e6272e4943834b46e21da55411ea
- Verified timestamp: Jul 22 22:14:54 2026 GMT
- Anchor-receipt SHA-256: e7e1ba29411a36e7f655b1ba3047f80c77bb12c222305fb25940c7837c8ae15c
- Launch-path mapping SHA-256: ae77feb5a3e403b8f248b8f568d710629be7a3113867dc397d992cbe7fed9d94
- Launch-config SHA-256: 903600dbcb0bb213f896067d32938226be3fe6d7a60afcde2d222b320159a148

## Execution absence and exact recovery

The final remote audit at 2026-07-22T22:37:24.252993955Z and recheck at
2026-07-22T22:48:22.264526424Z found:

- zero official output entries;
- zero runlog entries;
- zero environment_post entries;
- no matching official process;
- no wrapper, model, or CUDA execution;
- clean repository state at the frozen commit and tree;
- exactly 15 dependency files with no links, special entries, __pycache__, or
  .pyc residue;
- 21 of 21 remote control files exactly matching their local SHA-256 values;
- unchanged PRE host and A40 identity, with zero GPU memory use and zero GPU
  utilization.

No POST capture, producer receipt, or receiver receipt exists for Attempt 3,
and none was fabricated.

The exact recovery is retained beside this directory under
ATTEMPT_03_REMOTE_RECOVERY_A8969EB7. Remote/local archive SHA-256 values match:

- official attempt: 84b2fd846d371ccbb6a7c020f778615a66862f8c65c5dabe27fb969e3a406a9f;
- dependency bundle: ed16af7ae5a1ac8d61c6d3e83cf946a8cb3669c10f0f679fb2351965d5922bb8;
- model snapshot: 10c55e36459311f24ac0e6d69793f5873b460fbf4da9c78ba0b202afa4ad35f6.

The three normalized materialized inventories matched with zero differences.
The corrected final remote record index verified 22 of 22 recovered records.
The research pod was intentionally not stopped by the recovery task. The
production pod was not touched.

## Historical pre-anchor checkpoint

- Query Base64: MGYCAQEwMTANBglghkgBZQMEAgEFAAQgjaIvJX0OeZ8I98VD85GmZjh50SWPWH3F0eRzE2uxPcQGCWCGSAGG/WwHAQIgFv1Rr48Kw45sOgxqPs0Xin3B8k/m51J6hAE4FeT/shUBAf8=

At the historical checkpoint represented by the original version of this file,
the query had not yet been transmitted. Attempt 1 and Attempt 2 approvals did
not authorize those fresh bytes. The owner later explicitly approved this
exact 104-byte query, it was sent once, and the response and anchor receipt
verified as recorded above.

Read-only continuity check at 2026-07-22T21:44:59.9420053+00:00: live boot
and machine hashes matched PRE; hostname/GPU UUID/driver/memory were unchanged;
GPU utilization and memory use were zero; official output remained empty; and
the remote runner-tool and network-plan hashes still matched. At that
checkpoint the query remained valid and unsent.

After the same missing-authorization condition persisted through three
consecutive goal turns, a final read-only check at
2026-07-22T21:46:38.8678816+00:00 again matched every bound live identity and
control hash. At that historical checkpoint only, the workflow was
BLOCKED_WAITING_USER_AUTHORIZATION. That authorization blocker was later
resolved; the current blocker is the pre-execution bytecode guard defect.

Historical approval wording, later supplied:

I approve sending the exact 104-byte RFC3161 query with SHA-256
9f5bbed1764fb69ed5aac28f8db8bbaa168b668e65eca5a7af8d87c02bbc6291
to DigiCert.

## Required next action

Version the wrapper so its execve child includes Python -B. Make the runner fail
closed unless sys.dont_write_bytecode is true. Add regression coverage proving
that official imports leave the exact 15-file dependency root unchanged.
Freeze a corrected commit, tree, bundle, and manifest, then perform a fresh
Attempt 4 PRE/protocol/RFC3161 ceremony. Attempt 3 cannot authorize corrected
code.

No model execution, CUDA initialization, steering, ablation, prompt-injection
detection, joined CJT/J-Space/RPM/CAS-Ohm experiment, universality result, or
300B result occurred. Scientific conclusion is NO_SCIENTIFIC_CONCLUSION,
verdict is NONE, and claim status remains NOT_LICENSED.
