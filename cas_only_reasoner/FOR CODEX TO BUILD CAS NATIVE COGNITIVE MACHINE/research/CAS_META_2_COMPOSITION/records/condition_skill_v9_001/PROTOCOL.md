# Input-dependent two-condition learning pilot

This is a candidate-only learning experiment, not a replacement for the accepted
native model, a repair of the saved R_CR failure, or completion of the CNCM goal.
It follows the negative result bound to commit
`4f11fd91103db93189022b68db72b748ba766970`.

The owner has ruled that the historical 256 practice records may be included
in a future affected protocol only as deduplicated training/practice data, with
sealed, disjoint validation and test data. The executable safeguards are
recorded in `OWNER_256_RECORD_RULING.md`. This pilot uses a new synthetic
curriculum and does not append those historical records automatically.

## The skill

Given two labelled conditions, return which conditions hold. Each condition
contains its original integer value, limit, semantic slot, and requested
comparison (`at_least` or `at_most`). The two correct bits come from independent
integer comparisons. Bit 1 is the most significant bit:

| Bits | Class | Existing output symbol |
| --- | --- | --- |
| 00 | 0 | L0 |
| 01 | 1 | L1 |
| 10 | 2 | L2 |
| 11 | 3 | L3 |

This is one bounded experimental use of `DECOMPOSITION_SIGNAL`. It does not
redefine the Noetic meaning of `^6`, implement a general comparison/reasoning
engine, or claim natural-language understanding.

The eight model features are two rows of:
`[value/128, limit/128, slot, direction]`.
Slot is 1 or 2. Direction is +0.5 for `>=` and -0.5 for `<=`. Neither differences
nor answers, family IDs, task IDs, split names, or target-bearing wording enter
the features. Slot tags travel with rows, so physical row order is not identity.

The allowed public integer range is -15..15. Generated limits are -7..7 with
absolute margins 0..8. All 3,844 possible allowed single-row encodings have
distinct exact centered positive-affine signatures. That check prevents this
known input-normalization ambiguity; it does not establish neural learnability.

## The assembled dataset

Dataset: `dataset_001/manifest.json`.
Manifest SHA256:
`6b19020c4653aa535919f4af092020ad3650855bf7f58c6b550169af3d5468dd`.

The manifest was re-bound to the corrected builder sources. All six partition
files are byte-identical to the earlier manifest revision
`edaf3d6b4850aee0cae991a875dc899dec0ff9689aca1b7c23a6edfbce78eb09` bound at
commit `bc3cdc4b`; only the embedded builder-source hashes changed. The earlier
manifest revision is preserved in history and is not normalized or deleted.

| Split | Tasks | Atomic families | Each class |
| --- | ---: | ---: | ---: |
| Training | 1,536 | 1,366 | 384 |
| Validation | 384 | 317 | 96 |
| Fresh instances | 384 | 315 | 96 |
| Withheld direction pair | 384 | 322 | 96 |

There are 2,688 tasks and 2,320 families. The family key ignores physical order,
slot assignment, comparison direction, and which side of a threshold a value
lies on. A fixed family hash assigns the split. Related reversal/crossing
variants therefore cannot move between training, validation and testing.

Training and validation contain `(>=,>=)`, `(>=,<=)`, and `(<=,<=)`. Fresh-instance
testing uses those same direction pairs with new families. The second test uses
new families and the withheld `(<=,>=)` pair. It tests an unseen ordered pair of
queries, not unseen nested programs. Wording generalization is not tested.

Every class is balanced within each admitted direction pair. A constant class
predictor scores exactly 25% on each base split. Equality passes both comparison
directions; equality and one-unit margins receive separate reported counts.

## Candidate training and evaluation

Use a new CUDA-initialized seed-7 candidate with the original four-dimensional
NeuralCJT configuration/layout. Do not describe it as byte-identical to the
accepted CPU-seeded fixture. Save its untouched starting checkpoint.

Train only the selected `^6` operation's 64 parameters. Keep the CASformer
engine, recurrent-update head and other operations frozen. Compare with a
generic softmax-attention candidate using identical frozen projection weights
and the same initial 64-parameter operation transform. Both candidates receive
the same examples, order, optimization schedule and validation rule. The
generic path omits CAS-specific current/gating/nonlinearity, so this is declared
structural/parameter matching, not proof of an isolated CAS-Ohm causal effect.

The fixed intended schedule is 100 epochs, batch size 64, AdamW learning rate
0.003 and weight decay 0. Each family gets 2,400 optimizer steps, 4,800 total.
Choose each checkpoint by validation macro-accuracy, then validation cross-
entropy, keeping the earliest exact tie. Freeze both choices before test
prediction.

### Sealed target boundary

The learner stage reads only `train.json` and `validation.json` before the
sealed boundary. It never reads or hashes private test target files there:
`bundle.inspect_structure` validates the manifest declaration and builder-source
pins without touching any partition, and `read_partitions` reads only the
partitions it is explicitly given. Hash-reading private files is byte integrity
only and is never the boundary that proves targets stayed unopened.

Blind test predictions are saved with a hash-bound selection receipt first.
Only then does the evaluation stage open the public test files, save blind
predictions, and finally open the private target files for scoring. Each
partition is hash-checked against the frozen manifest immediately before it is
parsed.

Report untrained/trained CAS, untrained/trained generic, the integer rule and
constant predictors. Include both-bits correctness, each bit's correctness,
class counts, first wrong bit, equality/unit-margin slices, actual attempted
denominators, checkpoint identities and compute used. Exact-zero neural Effects
mean `NO_EFFECT`, not a free L0 answer.

## Deterministic adjudication

A frozen gate program (`train.adjudicate`) assigns the claim status; prose never
does. The vocabulary is `PASS`, `FAIL`, `EVIDENCE_INCOMPLETE`. The trainer-side
verdict is `EVIDENCE_INCOMPLETE` by design until the independent outer provider
receipt supplies its attestation and re-adjudicates.

### Metric definitions, denominators, and baselines

- **Joint accuracy** denominator: all attempted rows, including `NO_EFFECT`
  rows. Baseline: `0.25`, the balanced four-class constant predictor.
- **Per-bit accuracy** denominator: all attempted rows; `NO_EFFECT` is wrong
  for both bits. Baseline: `0.5`, chance for one ordinary binary decision.
  Per-bit gates are never compared against `0.25`.

`PASS` requires all of the following, evaluated programmatically:

- experiment status `COMPLETED_OFFLINE_CANDIDATE_EXPERIMENT`, selection sealed,
  test targets parsed;
- unchanged source identity with baseline, installed-wheel and candidate pins;
- constant baseline exactly `0.25` on validation and both test splits;
- integer rule exactly `1.0` on validation and both test splits;
- trained CAS and trained generic joint accuracy strictly above `0.25` on both
  test splits, and both per-bit accuracies strictly above `0.5`;
- trained joint accuracy strictly above untrained joint accuracy on both test
  splits, for each family (improvement through training, kept separate from
  exceeding the constant baseline);
- every evaluation control (row reversal, slot reassignment, both direction
  reversals, both threshold crossings) with joint accuracy exactly `1.0` for
  each trained family on each test split — both original and transformed
  answers correct, never invariance alone;
- exactly 2,400 steps per family;
- a matching independent provider attestation: account `807562639912`, region
  `us-west-2`, AMI `ami-0fbbd0facbc9e3cff`, one `g7.2xlarge` whose GPU name
  contains `RTX PRO 4500`, no T4, one visible GPU, torch `2.11.0+cu128`, CUDA
  `12.8`, an actual CUDA operation, zero automatic retries, the `$4.00`
  reservation, and a well-formed job label.

The overall verdict is a conjunction over all gates. Per-family gate rows,
initial-versus-trained observations, and every failed or missing gate are
reported separately and are never erased by the combined verdict. Both
families passing does not establish a CAS advantage; it establishes that both
met the registered criteria. Missing provider attestation prevents final
acceptance without turning recorded predictions into incorrect predictions.

`PASS` claims offline candidate learning only. It does not claim native
admission, repair, complete caller return, persistent Bias, composition, or a
CAS advantage over the matched control.

### Pre-run metric amendment

The earlier published wording required "both per-bit accuracies strictly above
0.25". Per the owner's pre-run clarification, per-bit gates now require
strictly above `0.5` (the binary baseline), trained-beats-untrained gates were
added, and denominators/baselines are defined above. The earlier adjudicator
and protocol revisions remain preserved in history (commits `9bfbeb27` and
earlier); nothing was silently rewritten. This amendment is bound by
`OWNER_METRIC_AMENDMENT.json` and happened before any training run. No
threshold changes are permitted after scores exist.

Evaluation-only controls: physical row reversal, slot reassignment, reversal of
each requested comparison, and crossing each value across its limit. At equality,
a reflected value does not cross; mark that explicitly. A control passes the
task claim only when both the original and transformed answers are correct.
Invariance alone is not enough, because a constant predictor can be invariant.

Each sample is an isolated, stateless lesson. There is no active caller whose
Bias is reset. This experiment does not test accumulated recurrent state.

## Native integration remains a separate required gate

The frozen runtime's `learning_tick` requires the current Effect to verify
ACCEPT before learning; it forbids learning during a reserved repair subgoal.
It admits a fixed bounded gradient-update policy and exact per-node scopes.
It does not admit arbitrary pretrained-checkpoint replacement, despite enum
names which might suggest otherwise.

The offline candidate trainer must not bypass that policy, install its weights
into an accepted database, change a target to match a prediction, or claim a
governed learning commit. A saved candidate is a research artifact. A later
admission design and real native execution/restart tests are required before
it becomes an accepted reusable CJT skill. Complete caller return and repair
remain required downstream gates. They are not redefined as classification.

The full goal remains a persistent, programmable, continually learning CNCM.
This pilot tests one missing component: whether a candidate neural operation
can acquire a checked, input-dependent transformation.

## Resource and reproduction boundary

All neural/tensor work must run on AWS CUDA, not the laptop, and not a T4.
The intended job is one g7.2xlarge, with a 600-second worker bound, 32 MiB worker
output bound, 3,600-second instance limit, scheduled termination, no automatic
retry, and one conservative $4 ledger reservation. A new source-bound launch
adapter must record actual AWS identity and enforce those limits before launch.
Linux, an environment flag and CUDA availability alone do not prove AWS execution.

This protocol creates no reservation and starts no job. The last checked
campaign ledger is revision 16: $98 reserved, $302 unreserved, $400 total cap.
The former 0/72 held-out and 24/24 familiar-program results remain separate.

Dataset reproduction from a clean source checkout into a fresh records directory:
`python -B -m cas_meta2.condition_skill_v9.bundle records/condition_skill_v9_001/dataset_002`.
It writes JSON only. The output parent must already exist; existing data is never
overwritten. Model and provider imports are unnecessary for this step.

Pure preparation checks:
`python -B tools/check_condition_skill_v9.py records/condition_skill_v9_001/checks_014`.
The guarded capture passed **375 tests and 24 subtests** covering data,
packaging, trainer admission, adjudication, the publication-packet verifier,
the resource plan, the source package builder, the remote worker, the launch
lifecycle, the AWS provider adapter, and the canonical budget integration. It
also confirmed unchanged tested source hashes and an unchanged campaign
ledger. These are preparation checks, not a neural training result. Earlier
local captures `checks_001` through `checks_013` are preserved and are not
deleted; `checks_014` is the receipt bound with this source state.

An independent read-only audit of the adapter is preserved in
`records/condition_skill_v9_001/audit_001/` (0 critical, 1 major, 6 minor,
7 info). The major reservation-ordering constraint was folded into the
provider contract (ledger append first, then the AWS-side step, exactly
once); the minor findings were resolved by the integrator except the frozen
trainer's attestation key set, which requires an owner-approved pre-run
amendment before any change.

The launch adapter's paid path remains inert until the exact request and
authority pair is hash-bound and the owner approval gates are met. The
protocol still creates no reservation and starts no job.

## Publication packet

`publication_packet.json` is byte-bound evidence generated and re-verified by
`tools/verify_condition_skill_v9_publication_packet.py`. The verifier checks
strict duplicate-key JSON, schema/type/path safety, exact changed-file coverage
of the bound source commit, source-commit ancestry, and byte-count/SHA-256/
Git-blob identity for every bound file. Packet bytes are LF-only by
construction; earlier packet revisions (including the CRLF revision bound at
commit `d8b63693`) are preserved in history and are never normalized.
