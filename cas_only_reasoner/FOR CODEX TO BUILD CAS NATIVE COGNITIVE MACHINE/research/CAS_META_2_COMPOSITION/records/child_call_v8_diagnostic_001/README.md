# Saved-model prefix diagnostic

This package tests what the saved V7 models already know. It does not train them.
Correct prefixes supply part of the solution, so their scores are assisted
diagnostics, not autonomous task success. V7 remains CAS **0/72** on its final
unfamiliar tasks. No accepted model, executor, guard or V7 source is changed.

The main agent completed the required charter read once, through its final
character, before implementation. The charter's SHA256 is
`a72312231bfb346dc4895b1a0963e0c255d26b707c8a4fbc94d90ac52979dfea`.

## Scope and denominators

The data contains the exact 24 registered V7 training probes and 96 validation
tasks. Four checkpoints produce 480 task/checkpoint rows over **120 distinct
tasks**, not 480 independent tasks. No V7 final tasks enter this diagnostic.

| Decision role | Training probes | Validation | Per checkpoint |
| --- | ---: | ---: | ---: |
| Observation binding | 24 | 96 | 120 |
| Child selection | 64 | 256 | 320 |
| CALL input | 64 | 256 | 320 |
| Other RUN input | 240 | 912 | 1,152 |
| Parent return | 24 | 96 | 120 |
| Child return | 48 | 192 | 240 |
| Total | 464 | 1,808 | 2,272 |

This is 9,088 checkpoint/opportunity rows. The full reference streams contain
9,728 next-token targets per checkpoint, including structural tokens and one
EOS per task. BOS and padding are not predictions. Training probes have eight
tasks at each depth 1/2/3; validation has 32 at each depth. The 16 nested probes
are call-target contrast pairs, not a balanced sample of all binding lessons.
Of the 2,272 reference sites, 360 RUN-input sites have only one grammatical
option; 1,912 have multiple options. Multiple grammatical options do not by
themselves prove numerically or semantically different execution outcomes.

## Implementation

- `bundle.py` copies a strictly allowed development-only panel and checkpoint
  bytes, validates their identities, and counts the reference decisions.
- `sites.py` identifies static procedure/instruction sites and compares their
  value-definition context. It preserves missing, changed, illegal and
  ambiguous opportunities. Pure output renaming is separate from literal
  token agreement; no general semantic-equivalence claim follows.
- `gpu.py` loads saved weights only on the admitted AWS CUDA path. It uses the
  existing public encoder, copy/binding machinery, decoder and grammar.
  It scores token `j` from preceding tokens `[:j]`, at output index `j-1`.
  It observes unchanged greedy generation without supplying its gold target.

Report raw full-vocabulary top-1/NLL separately from grammar-masked top-1 and
renormalized NLL. Report one-option grammar decisions separately from genuine
choices. For self-generated prefixes, report comparable/total coverage as well
as correct/comparable accuracy. Changed contexts are not silently given the
reference answer or counted as ordinary matched mistakes.

## Local preparation and checks

The combined local check passed **313 tests and 5 subtests**, with neural and
provider imports blocked. Raw output and source-before/source-after hashes are
in `checks_002`. The first combined attempt (`checks_001`) stopped before test
collection because isolated Python could not locate pytest. The test bootstrap
now records that library path explicitly without enabling user-site startup
hooks. Both attempts are retained.

The working directory for the commands below is:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION`

Run these commands from that directory. Choose unused output directories for
reruns; the tools refuse overwrites. They perform no neural work.

```powershell
python -B -m cas_meta2.diagnostic_v8.bundle prepare --extraction-root records/prototype_v7_partial_review_001/extracted_001 --output records/child_call_v8_diagnostic_001/bundle_001
python -B tools/check_prefix_diagnostic_v8.py records/child_call_v8_diagnostic_001/checks_001
python -B tools/package_prefix_diagnostic_v8.py --v7-source-archive records/aws_prototype_v7_source_001 --output records/child_call_v8_diagnostic_001/source_001
```

The source packager requires every new source byte to be committed. It compares
all 603 frozen source files with the original V7 archive and commit, including
316 protected baseline files, and copies their bytes unchanged. The resulting
receipt binds the new code commit and archive digest. It is not a launch receipt.

The existing bundle can be checked again without creating or overwriting files:

```powershell
python -B -m cas_meta2.diagnostic_v8.bundle validate --bundle records/child_call_v8_diagnostic_001/bundle_001 --manifest-sha256 b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629
```

The generated development manifest identifies all four checkpoints, source
metadata, exact task ordering and file digests. The source archive and the
development bundle are separate; both are required for GPU execution. The
original saved packet must remain available to reconstruct the bundle. Do not
treat an absent packet or checkpoint as a successful clean-checkout rerun.

Preparation tests also need that pinned extraction and its sibling
`extraction_receipt.json`. Set `CAS_META2_V8_TEST_EXTRACTION` to its full path
when using a separate clean checkout. The source archive alone is not all the
test input data; missing inputs are errors, not skipped passing tests.

The optional pure `tools/replay_prefix_panel_v8.py` checks the matcher against
all 480 saved development-action rows. It is not a new model evaluation.
Complete actions are canonically serialized and explicitly not labeled as raw
emitted token evidence. Its receipt retains all 9,088 reference opportunities.
Use `offline_replay_002` for source-bound replay evidence: it checks source
hashes before and after execution. The earlier `offline_replay_001` recorded
only ending hashes and is preserved, not used to establish that stronger claim.

## AWS execution and launch boundary

Do not run model code on the laptop. The pure test entry point blocks neural
and provider imports. `python -m cas_meta2.diagnostic_v8.gpu --help` describes
the worker arguments without loading torch. The worker requires externally
pinned source, development, plan and reservation identities plus the matching
live AWS instance identity. A supplied string is not proof of an AWS launch.

The worker command, after a separate authorized launch supplies the exact job
and externally pinned plan, is:

```text
python -B -m cas_meta2.diagnostic_v8.gpu --bundle BUNDLE_DIRECTORY --output NEW_RUN_DIRECTORY --job REGISTERED_JOB --manifest-sha256 b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629 --plan REGISTERED_PLAN_JSON --plan-sha256 REGISTERED_PLAN_SHA256
```

These uppercase names denote required launch inputs, not existing provider
receipts. The worker also requires `CAS_META2_RUN_PREFIX_DIAGNOSTIC=1` and the
same job in `CAS_META2_AWS_JOB_ID`. `NEW_RUN_DIRECTORY` must be below the
extracted package's `research/CAS_META_2_COMPOSITION/runs` directory.

On a separately authorized AWS Linux worker, install the source archive's
unchanged `requirements-gpu.txt` direct pins, torch 2.11.0 from the CUDA 12.8
index, and its two bundled CAS wheels. Preserve the resolved installation
reports. The source archive's `launch_manifest.json` records their paths and
the three required Python package roots; `prefix_source_manifest.json` binds
this new diagnostic separately. **Do not invoke the old V7 launcher.** It would
run a different experiment.

The worker is a diagnostic entry point, not an EC2 provisioning or billing
controller. Before launch, the parent process must verify the canonical ledger
and its history, reserve the exact source/job/resource plan, verify current
price/capacity, enforce an independent instance shutdown deadline, and collect
outputs even after failure. Worker checks of copied reservation evidence bind
the inputs; they do not replace those parent duties or grant user approval.

Proposed diagnostic ceiling: **$4**, one `g7.2xlarge`, RTX PRO 4500, no T4,
no retries, at most 3,600 seconds of instance lifetime and at most 1,800 seconds
inside the diagnostic worker. The previous planning rate of $2.52/hour plus
$1 ancillary allowance gives $3.52. This is not a current quote or an invoice.
The proposed later training/evaluation ceiling is separately **$7**; it does
not start automatically after this diagnostic.

No new reservation or launch is made by preparation. The previously checked
ledger is revision 11: $78 reserved, $322 unreserved, within the inclusive $400
cap. Re-check the live canonical ledger before any later booking.

## Remaining work and claim limits

Pure checks establish data handling, alignment rules and refusal behavior, not
actual CUDA execution or learned capability. The first AWS execution must
verify the recorded checkpoint payloads, captured-generation agreement,
numerical settings, deadline handling, result coverage and unchanged weights.
No new model score exists until that execution is completed and receipted.

No new grammar intervention is included. The later one-child-call lesson stays
separate: before training, demonstrate at least two meaningful legal input
alternatives using the unchanged runtime/verifier. Different names on equal
`A(arg)` values or a mask leaving only one option do not prove that skill.
The proposed small repair contrast must keep the durable-distinct-`^6` guard.
Fresh depth-2 evaluation and later removal of scaffolding remain future work.
