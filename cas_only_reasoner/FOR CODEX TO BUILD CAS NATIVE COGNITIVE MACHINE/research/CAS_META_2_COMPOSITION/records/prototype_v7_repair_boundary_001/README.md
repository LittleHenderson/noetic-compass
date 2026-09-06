# V7 repair-boundary diagnosis

The recorded guard refusal is consistent with the accepted contract: **B has no distinct permitted repair round trip in the frozen topology.** Nothing found here justifies removing the guard. A full development CUDA reproduction of the semantic mismatch has **not** run.

## What the saved evidence establishes

The five failures were independently traced to the following next sealed operations in the already-checked partial-native receipt:

| Case | Candidate | Previously committed RUNs | Next sealed RUN | Input |
| --- | --- | ---: | --- | --- |
| 19 | CAS trained | 3 | B, node 3, frame 1 | Original observation (-1) |
| 32 | Generic trained | 9 | B, node 9, frame 4 | Original observation (-1) |
| 51 | Generic trained | 1 | B, node 1, frame 1 | Original observation (-1) |
| 66 | Generic trained | 3 | B, node 3, frame 1 | Original observation (-1) |
| 71 | Generic trained | 2 | B, node 2, frame 1 | Original observation (-1) |

This is the next operation in the sealed program after its verified committed prefix, not a newly observed failed-tick trace. All five selected the original observation for B instead of an accepted A Effect at that point. The failed candidate tensor and verifier receipt were not committed and are unavailable. In case 32, earlier committed steps already differed from the reference; this is not claimed to be each trajectory's first wrong decision.

The topology in the source fixture and recorded runtime identity is A -> B -> C <-> R. The repair predicate requires a distinct ^6 partner with an allowed edge in **both** directions, plus admitted operation, durable permissions, publication authority, readiness and suitable operating region. B -> C exists but C -> B does not; A -> B exists but B -> A does not. Thus B cannot have a viable repair partner even if every other eligibility condition is favorable.

## Source-backed interpretation

Eight read-only source files are byte-checked against the original V7 archive and SHA-256 pins in check.py.

- cas_cjt/runtime.py:549-591 implements _viable_repair_cjts. Lines 937-945 refuse the REPAIR branch when that set is empty.
- cas_meta/fixture.py:26-31 provides the same four directed edges found in the saved runtime identity.
- cas_cjt/network.py:97-100 performs the directed edge lookup. A multi-hop path is not accepted as a direct repair round trip.
- cas_meta2/curriculum.py:66-105 permits an original observation as a RUN input; it enforces an inter-CJT edge only when a previous Effect is the input.
- cas_meta2/native.py:208-220 creates a single-RUN wrapper with expected B symbol L3 and no opposite or repair procedure.
- cas_meta/compiler.py:231 defaults the absent opposite symbol to None. cas_meta/executor.py:314-318 passes these expectations to inference_tick.
- cas_cjt/verifier.py:326-340 classifies a content mismatch with no opposite target as OFF_AXIS/REPAIR. Runtime preparation raises the guard error before committing that tick.

Accordingly, **the exception implies a repair request reached the guard; the frozen topology explains why the refusal is correct.** The exact failed decoded symbol is not recoverable from these records. Whether a different binding alone avoids the semantic mismatch in a fresh development fixture remains a CUDA test, not an offline result.

Admission is not a guarantee that every selected input will produce its expected symbol. This is a post-admission refusal, not a pre-execution grammar rejection, and not evidence that the repair guard is defective.

## Minimal executed development fixture

Run from CAS_META_2_COMPOSITION:

```powershell
C:/Python314/python.exe -B records/prototype_v7_repair_boundary_001/check.py
```

The saved run exited **0**. It checks **11 predicate/guard cases**, not 11 native executions:

- Four exact-source viability calls on synthetic, otherwise fully eligible state: A=none, B=none, C=R, R=C.
- Two exact-source guard refusals for A and B.
- Two guard continuations for C and R (passing this guard does not open or close a native repair).
- A one-way A -> B development graph refuses repair; adding B -> A in the **synthetic fixture only** makes B eligible; quarantining B removes that eligibility again.

The script extracts only the named predicate, edge-lookup method, exception class and exact guard body from pinned source via Python's syntax tree. It does **not** import or construct the runtime. State objects are deliberately synthetic. The full operation contract, tensors, publication transaction, repair/resume state machine and neural execution are not exercised.

It also checks the five saved next-operation witnesses and rechecks all eight source files and the original audit receipt after the pure checks. The output is receipt_001.json; command_capture_001.json records the actual command result. No checkpoint was loaded, no SQLite database was opened, and no provider call was made.

## Small remaining CUDA test — prepared scope, not launched

Use only training/development inputs, a fresh disposable native database and the existing AWS CUDA bridge. Keep accepted weights, topology and guard unchanged. Do not replay opened V7 test cases as new evaluation data.

1. Run a small parent A(arg) -> v0 and a child B(arg) using the original parent argument. Record the B expectation, decoded symbol, exact input identity, source/model identity, guard result and database head before/after the rejected tick.
2. In a separate fresh database, change only the call binding to the accepted A Effect v0. Compare the actual outcome using the unchanged verifier. Do not assume that every development input reproduces the original mismatch; label a non-reproducing input honestly.
3. For an unconditional contract control, use the established development input from cas_meta/fixture.py and a separately authored nonmatching B expectation after observing its symbol in a read-only CUDA proposal probe. Label this **forced semantic mismatch**, not learned failure or independent task correctness. The existing topology must still refuse B repair without committing the failed tick.
4. Retain the existing accepted C/R repair-and-resume fixture as a positive control. The v0.2 tests/test_repair_bounds.py fixture explicitly supplies A -> B and B -> A for its positive repair-opening tests; those tests import neural code and were deliberately not run on this laptop.

This proposed control changes only disposable test expectations, not the runtime or any accepted model. It requires the parent's registered CUDA diagnostic and explicit bounded budget process. **No paid launch is authorized by this record.** A full end-to-end reproduction remains open; no core defect has been demonstrated.

## Claim boundary

V7 remains CAS 0/72 with five recorded post-admission failures across candidates. This diagnosis does not change scores, traces, runtime behavior, checkpoint identities or old evidence. It proves the narrow pure guard behavior under the saved topology, not general repair capability, neural learning or runtime completeness.

