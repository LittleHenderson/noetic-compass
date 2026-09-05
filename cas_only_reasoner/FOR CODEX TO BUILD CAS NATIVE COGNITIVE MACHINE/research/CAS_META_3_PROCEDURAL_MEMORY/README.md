# CAS-META-3: a bounded procedural-memory candidate

This is a separate experiment for saving and reusing one typed CJT procedure.
It does not change the accepted executor, the saved META2 learning experiment,
or any baseline weights. It is not yet a learned or qualified skill system.

The AWS native-reuse demonstration has now passed both the source-bound packet
inspection and the unchanged stored semantic audit. A separate reader retrieved
one saved procedure after the writer exited; the native caller used it twice
and returned the first B result. All six native traces across three databases
were checked, and five package/scope rejection checks passed. Cloud cleanup was
independently verified. See [the recorded result](records/aws_native_demo_001/RESULT.md)
for exact source, packet, audit, and budget identities. This is a bounded memory
reuse result: `learning_performed=false`, `qualification_status=UNQUALIFIED`.

Original storage/link receipt: `records/local_candidate_001/receipt.json` records **72
passing pure tests**, all 316 protected files unchanged, and the three META2
dependency hashes checked against the actual frozen Git objects. Neural imports
were blocked. This is not native execution or a learning result.

Earlier pure integration receipt: `records/local_native_demo_002/receipt.json`
records **364 passing pure tests**, no failures/errors/skips, all 316 protected
files unchanged, and unchanged source hashes across the run. Neural and
provider imports were blocked. The one warning is from the intentional
duplicate-ZIP rejection fixture. This includes synthetic audit and fake-provider
checks; it is not a cloud native-reuse result.

## The narrow question

Can a caller save a procedure, close the process, retrieve exactly that procedure
in a fresh process, and link it into a new parent program without expanding its
permissions?

The first package contains only `B(arg) -> v0`, with an accepted A Effect as its
input and an accepted B Effect as its output. A fixed parent runs A and then
calls that saved B procedure twice. Both calls use the earlier A result; the
parent returns the first B result. This exercises distinct calls, named values,
and an explicit return without adding a new opcode or compiler.

## Boundaries

- The SQLite registry stores canonical JSON data, not Python or model weights.
- The caller supplies the expected package hash, compatibility identity, and
  allowed CJTs. A package cannot grant itself permission.
- Storage and link receipts always say `UNQUALIFIED`. A hash or a successful
  retrieval does not establish task correctness or learning.
- The registry has no update, delete, promote, or execute API. New versions use
  new content hashes. This is an application-level storage rule, not a claim
  that an external administrator cannot replace the database.
- The package address identifies reusable content. It is not an execution ID,
  a native memory reference, an oscillatory phase, or a new source of authority.
- Retrieval in a fresh process is distinct from resuming an interrupted native
  call. The latter is not implemented by this candidate.
- No Noetic meanings, Foundation meanings, pulsation, lifelong learning,
  automatic skill selection, or general-purpose program generation are added.

## Source boundaries

The pure META2 IR and action codec are pinned by file-byte checks to source from
commit `b5f1718e63a2b5cf72b4b606d513d0524b9226ac`. The protected native executor
baseline is `0917267b1354e5d036263eaa6ba9a7197eafb776`. The registry does not
import the native executor or a neural library.

Current source:

- `cas_meta3/registry.py`: strict package checks, append-only installation, and
  read-only retrieval with a chain of storage receipts.
- `cas_meta3/linker.py`: the fixed parent program and a structural link receipt.
- `tests/test_registry.py`: storage, rejection, and process-restart checks.
- `tests/test_linker.py`: linking, named-value reuse, caller scope, and unchanged
  META2 action-admission checks.
- `tools/validate_local.py`: syntax, protected-byte, and pure test receipts.

## Local checks

From this directory, run:

```powershell
C:/Python314/python.exe -B tools/validate_local.py --output records/local_audit_rerun
```

The output directory must be new. The test process refuses imports of Torch,
TensorFlow, JAX, and CASformer. These checks run no models or tensors. Fixtures
use synthetic compatibility hashes; those hashes are not native qualification.
Temporary test files stay in a short `_tmp/meta3-*` directory under the CNCM
homebase. The receipt records its exact path; short paths avoid a Windows Python
startup problem seen with a deeply nested `TEMP` directory.

## Separate AWS execution gate

The separate AWS-only demonstration bound one package to the actual frozen
model, software, contracts, topology, and published schema. Its fresh reader
retrieved the package, and the linked parent ran through the unchanged runtime.
All three candidate outputs matched the separately executed reference. Five
invalid package/scope requests were rejected before candidate/probe construction;
the earlier reference run already existed. The packet and stored semantic audits
passed, with all 316 protected file hashes checked. See `NATIVE_DEMO.md` for the
contract and [the result](records/aws_native_demo_001/RESULT.md) for its receipts.

The launcher uses the existing single META2 campaign ledger and the owner's
$400 total cap; it has no separate spending authority. No T4 or local neural
work is permitted. The accepted learning experiment and executor are unchanged.
After this job, the shared ledger records $32 reserved and $368 unreserved;
these are reservations against the $400 cap, not an AWS invoice.

## Evidence interpretation

The pure tests and bounded native demonstration do not show that CASformer
learns which skill to store, retrieves a useful skill from a problem, gains
CAS-specific advantage, or implements the complete cognitive-machine vision.
