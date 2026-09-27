# Q1-Codex packet 1 handoff

Author: Q1-Codex, actual thread 01a0e385-db6e-7a71-beca-f6ef3a6c5e04, /root on MSI.
Local isolated repository: C:/Users/wakil/HELM-Q1/q1-offline-20260927.
Dedicated private transport: LittleHenderson/noetic-compass, branch
codex/helm-q1-offline-20260927. This branch starts from an empty repository and
contains no incumbent history. It is not based on or assigned to PR #245.

Exact branch link:
https://github.com/LittleHenderson/noetic-compass/tree/codex/helm-q1-offline-20260927

## Delivered source

- helm_quantum/contracts.py: four immutable records, admitted binding and limits.
- helm_quantum/admission.py and wire.py: synthetic admission, strict JSON, expiry.
- helm_quantum/classical.py: supplied helper reused; exhaustive, structured/pruned,
  and bounded seeded uniform search; separate proof/no-sample statuses.
- helm_quantum/verifier.py: independent direct behavior over all four inputs.
- helm_quantum/eligibility.py, backends/base.py, backends/offline.py: mode routing,
  backend protocol and unconditional no-submission implementation.
- helm_quantum/__main__.py: real fresh-process CLI; tests/test_cli.py uses it.
- schemas/: complete structural JSON descriptions; trusted admission still required.
- fixtures/public/q1-mod4.json: the compiler's public specification, no solved IDs.
- tests/: 43 authored test methods; none collected or executed by Q1-Codex.

Source hashes are in evidence/SOURCE_HASHES.json. The supplied input manifests
matched 21/21 handoff and 13/13 original entries, including sizes. The vendored
helper SHA256 is 6731ecd9298e40e0f9943a968b8c225fefe66c9baffccdfdc94493b9cb343adb.
Only standard-library Python >=3.10 is required; no packages were installed.

## Handoff to each lead

Q1-Claude: accept coordination/FILE_LEASES.md in coordination/claude/. Implement
helm_quantum/compiler/, tests/compiler/ and semantics/ in your own isolated copy.
Use the public specification and current QuantumProblem. Do not import the
classical evaluator/reference receipts to construct or tune the oracle. First
return: reversible primitives/predicate, source identity and a finite resource
model. No simulator or provider execution is authorized by this handoff.

Q1-DeepSeek: accept the lease in coordination/deepseek/. Put independent probes
in review/. Check actual constructors, replace/from_dict/from_json, copied/fake
admissions, each return field, scorer/limit forgery, independent semantics,
mode non-mutation and all zero-submission paths. Distinguish static findings
from executed probes. Preserve author attribution; Codex fixes Codex files.

New ChatGPT-Q1 manager: write only coordination/manager/. Confirm each lead's
actual access, session ID, ACK and START separately. The Git issue is the Q1
message location; it does not wake a model. DeepSeek and manager local ACKs were
read; their actual remote access and Claude's ACK remain unconfirmed. Do not post
as another lead or repurpose the old queues.

## Execution evidence and exact next test packet

MSI performed file inspection, manifest hashing, static Python/JSON parsing and
Git preparation/publication only. New tests: 43 authored, 0 collected/executed,
0 passes/failures/skips, 43 NOT_RUN. Supplied tests: 22 NOT_RUN in this session.
The historic 22/22 helper result belongs to the package's original Linux receipt.
DeepSeek separately reports 42 local passes against earlier uncommitted files;
these were outside the AWS-only venue rule and do not validate this final source.
See coordination/codex/REVIEW_RESPONSE.md for attributed source fixes and limits.

Commands from the Q1 root on an already-authorized AWS runner:

```sh
python -m helm_quantum inventory --read-only
python -m helm_quantum baseline --mode disabled
python -m helm_quantum validate --fixture q1-mod4
python -m unittest discover -s input_package/original_package/tests -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

No runner is currently identified for Q1. Before execution, record the existing
runner/instance, source commit, existing grant, free capacity and concurrency,
one CPU, an outer 60-second test timeout, an enforced process memory cap of at
least 256 MiB, zero incremental spend and cleanup of Q1 scratch files only. The
64 MiB contract field is a requested search working-memory envelope, not proof
of Python interpreter RSS. This is a proposed test envelope, not a cloud grant.
Do not borrow incumbent environments, budgets or jobs.

Q0 remains open: no live HELM baseline, profile, runtime/checkpoint or host
admission was imported. Minimum host handoff needed later: approved public
snapshot/RPM-return/verifier/retention interface exports with exact file hashes.
Research candidates are not retained; no actual parent was resumed.

Next concrete deliverable: a commit-bound execution receipt for the two suites
plus DeepSeek's independent probe findings. Claude's predicate/resource packet
can be authored in parallel in its separate lease. Next Codex implementation is
the reviewed compiler adapter; quantum submission stays disabled.
