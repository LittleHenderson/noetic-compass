# Restart-safe storage for full learned-program candidates

The new `LearnedCandidateStore` saves a candidate and its learning-audit bytes
in a separate append-only SQLite database. Retrieval in a fresh Python process
repeats the full handoff checks using independently supplied trust anchors.
It does not load weights, execute a CJT, promote a skill or change the accepted
runtime. Every saved and retrieved candidate remains `UNQUALIFIED`.

This implements a further part of V05 durable procedural memory and V15 portable
components. V06 skill qualification, retention and behavioral rollback remain
open. The full vision is unchanged.

## Interface and evidence boundary

`cas_meta3/learned_store.py` provides:

- `LearnedCandidateStore(path).save(package, **handoff_inputs)`: calls the
  evidence-bound handoff first, then stores canonical package bytes, the five
  raw evidence inputs, handoff record and linked storage receipt.
- `LearnedCandidateStore(path).retrieve(expected_digest, **trust_inputs)`:
  opens the database read-only, checks schema and content hashes, and reruns
  the handoff using the stored raw evidence and external caller expectations.

The caller must supply compatibility, CJT permissions, parent/version,
inspection and stored-audit digests, source SHA, selected arm and case index.
The optional minimum learning gain defaults to one correct held-out task.
These inputs must not be inferred from untrusted database claims.

The store checks canonical content, append-only triggers, ordered receipts,
parent presence and immediate version continuity. Normal update/delete fails.
A changed audit cannot gain authority by rewriting its storage hash. An orphaned
child cannot hide its missing parent by rewriting the storage sequence.
This is not a claim of physical write-once media or protection against a process
that controls the caller's trusted code and all external trust anchors.

At most 64 candidates, 400 MiB of stored payloads and a 512 MiB database are
allowed. SQL lengths are checked before materializing blobs; each raw evidence
input is limited by the reader's 16 MiB ceiling and packages by 256 KiB.
No checkpoint weights or executable Python are stored as skills.

Child versions preserve the parent entry, but both are still candidates. Reading
an older candidate is not proof that a trained system can roll back without
losing protected capabilities. Non-root entries require a stored parent with
the preceding version and the same compatibility identity.

## Pure validation

The full META3 suite passed **565 tests**, zero failures/errors/skips, in
61.84 pytest seconds and 63.7363627 runner seconds. All 28 tested source/config
files and all 316 protected baseline files were unchanged. Neural/provider
imports were blocked. The only warning is an intentional duplicate-ZIP fixture.

Command, from this META3 directory:

```powershell
C:/Python314/python.exe -B tools/validate_local.py --output records/local_learned_store_002
```

Use a new record-directory name for another run. Exact command, source hashes,
environment, before/after identities, raw outputs and XML are retained there.

- Receipt SHA-256: `bfcf0e5c6c946afb1fe46a3b1bed2a587f9621623bd45cb5ee12228b17912d28`
- Stdout SHA-256: `4a37ca9f5dabf4bc7b50939c2d80b54a0c3d15869484d6373bf340a12254b459`
- XML SHA-256: `5902864463baccda00a09403a9b5ee4ad48e8e83c10fa8d1e26a765f38819ae0`

The earlier 560-test record is retained as `records/local_learned_store_001`.
The final run adds five checks, including missing-parent retrieval after a
rewritten sequence and externally anchored audit validation after a rewritten
storage receipt. The fresh-process test receives only the saved database and
separate caller trust inputs; it does not reconstruct an in-memory registry.

All learning evidence in these tests is synthetic. This proves data persistence
and repeated admission checks, not persistence of an actually learned skill.

## Next native gate

Finish the live v3 learning run and its frozen audits. If its actual executed
held-out results show positive CAS learning, pass a correct CAS action and real
audit bytes through this store, retrieve it in a fresh AWS process, and execute
it on new inputs and inside a new parent procedure. Independently check actual
outputs, retained capabilities, permissions and rollback before qualification.
A generic-control result must remain labeled generic, not CAS learning.

No extra AWS job, reservation or local neural work was used for this change.
The frozen v3 source and its evaluator remain unchanged.
