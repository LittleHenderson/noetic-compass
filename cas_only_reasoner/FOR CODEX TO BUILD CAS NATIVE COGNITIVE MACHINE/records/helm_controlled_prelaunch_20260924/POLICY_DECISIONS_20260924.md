# Codex decisions for the reader, spending gate and HSET-2 — 2026-09-24

These are prospective policy decisions under the owner's six-item assignment and standing authority. They resolve
Claude's pending design questions; they do not claim technical readiness or authorize bypassing a missing gate.
C remains selected, B remains the stronger fresh-control design, the ceiling remains $60, Claude remains the runner
and custodian, and Q4 stays separate. No protected key, answers, selection secrets or sealed result was read here.

## Review outcomes and exact sources

- Reader `d5414964314475e2b13a49595fd54a3d7fee017c`: the core state-plus-panel decision conforms, but
  **CHANGES_REQUIRED_BEFORE_P1B**. See [source findings](READER_STATIC_REVIEW_20260924.md).
- Spending gate `4e292912a1efe0a85312574a69291a1af5af5427`, Claude review
  `6ba8ec1ce8a7d83c88cb9f9e59e52f2b1c1476a6`, integration `0618c72fa0f3e54482321a438968f44cdc481c54`:
  **CHANGES_REQUIRED_BEFORE_ADMISSION**. See [source findings](SPEND_STATIC_REVIEW_20260924.md).
  The route reader's revised identity/cleanup checks are source-conformant within its metadata trust assumptions.
  The previous public P1a result remains accepted in its recorded scope; this is not a new runtime verification.
- HSET builder review `bd960bc1ae351f9cf653fd865a9a9996e3c3aa75`: decisions D1-D4 are fixed in the single
  [A2.7 specification](../helm_eval_design_20260923/EVALUATION_DESIGN_v0_4.md). Builder conformance and final counts
  remain pending. Register FRONTIER_FALLBACK and the flags tie-break, use same-side DEV decoys/targets but A1's
  dedicated filler pool, and retain all floors and NOT_TESTABLE outcomes. Do not promise learned path following.

All new reviews here are static public source inspection, Git byte/hash comparison and document checks. Claude's
reported tests are attributed to Claude, not rerun by Codex. No project tests, models, builds or AWS jobs ran here.

## Reproduction decisions: R3-A through R3-I, V4-A and builder 9.6/10.6

**R3-A / V4-A: hashes flow in one direction.** Use this order:

1. Immutable source and data leaves: worker/model/adapter/checker/decoder/probe/reader/admission-writer/spending-gate
   code, public panel and reference artifacts, initialization recipe, environment lock, comparator/statistical
   rules, package recipes and job limits. Resolve their exact Git objects and content hashes.
2. Acceptance receipts for those leaves. P1b tests the reader rule and source; it cannot require a final packet
   that in turn requires its own acceptance receipt. Record the preliminary policy pins it actually used.
3. Execution manifest binds leaves and receipts. The final launch request binds that manifest and the required
   policy/plan documents. A frozen packet index may bind the request and leaves; it never contains its own hash.
4. A committed policy-pins sidecar and technical-admission envelope bind the final packet, manifest and policy,
   plus fresh per-attempt spending admission. They are downstream of the packet, never inputs hashed inside it.
5. Runtime receipts bind the immutable admission and actual artifacts/environment. Append evidence; do not rewrite
   the freeze, admission, result or prior attempts, including through merge resolutions.

Remove upstream `control_admission_sha256`, `repaired_admission_sha256` and self-referential
`frozen_launch_packet_sha256` from the manifest's required final-freeze inputs. Replace them with admission-writer
source/rules pins and package/configuration hashes. Downstream records carry the actual admission/packet hashes.
Separate nonlaunch preparation from ADMITTED execution: a preparation command may write candidate immutable
package/configuration records with launch disabled; it must not reserve, call RunInstances or require a fabricated
launch-enabled flag. Actual admission occurs only after all prerequisite validation. A receipt-commit pin may
follow content hashing in a later commit; no document tries to contain its own commit ID or hash.

**R3-B / 9.6-3,4: validity comes first.** Only an exact plain `ValueError` whose FULL message is a historical
POINTER_/TYPED_ refusal code from an explicit allowlist extracted from the pinned public historical source is a
model refusal record. Publish the allowlist and its source hash before acceptance. Validate the full message
before truncating its display. Other exceptions, added prose/newlines, CUDA/OOM failures and grader/record faults
are invalid evidence, not fallback-eligible model differences. A registered refusal may differ from the reference
answer and count as an output difference only when the entire evidence package is otherwise valid. Missing-key or
dtype changes must be reported as observed state differences; if the historical loader cannot produce a complete
valid panel, the decision is ADMISSION_INVALID_STOP, not a valid mismatch. Do not relax the loader or skip records.

**R3-C:** changed-buffer is VACUOUS only after the pinned restored architecture is shown to have exactly zero
persistent buffers. Print that count and the reason. Any buffer present requires a real changed-buffer case;
VACUOUS is not evidence that altered buffers were tested. Preserve the complete state-key inventory requirement.

**R3-D:** starting-state identity is matched training configuration. A wrong initialization is INVALID before the
first optimizer update, never a mismatch that buys fallback B. Continuation-state comparisons remain separate.

**R3-E:** re-pin to this reviewed amendment revision after implementing its decisions. Currency means exact,
reviewed deciding blobs, not every moving coordination note or branch tip. The closure includes the final plan,
launch request, policies, manifest, public panel/reference, model/worker/checker/decoder/adapter/probe sources,
reader/recompute/common AND preparation/admission writer, environment/data/package recipes, spend rules and
acceptance receipts. Publish the closure; any change to a deciding member requires prospective review and affected
acceptance checks. A later commentary-only commit does not invalidate unchanged leaf hashes. Excluding the
policy-pins sidecar from the reader code digest is acceptable only because its exact bytes are separately bound
by the immutable downstream admission. It must never be an unpinned mutable override.

**R3-F:** Claude's reviewed spending program writes the record from pinned attempt receipts, provider/cleanup
records, applicable resource rates and bounded ancillary/storage allowances. The runner does not type a total.
Recompute under the same single-writer admission lock immediately before each RunInstances attempt and verify all
source/receipt/state hashes are unchanged. The snapshot-to-launch window is at most five minutes and single use;
expiry, another attempt, a state/input change or loss of lock requires a fresh check. A timestamp-shaped string
alone is insufficient. The attempt record binds the recomputed inventory hash, gate version, cap, remaining
mandatory reserve, cumulative upper bound, stop count and launch identity. No acknowledged bus message substitutes
for this admission; no receipt-only historical reconstruction substitutes for a prelaunch gate.

**R3-G:** fetch the declared receipt branch, resolve the receipt commit and require it to be reachable from that
freshly fetched tip. It need not equal the tip. Resolve every pinned owner/policy/source/review object as well;
unavailable objects/fetch failures cause a recoverable TOOL_STOP before evaluation, not a fabricated study verdict.
Require the same exact frozen blobs across subsequent relevant history, including merge commits. Git chronology is
an audit record, not independent proof of wall-clock time; also bind freeze/admission and provider start records.
An unpushed alternative evidence history is not admissible.

**R3-H:** use scoped verdicts: SOURCE_CONFORMANCE_PASS or CHANGES_REQUIRED, plus unresolved findings and their
execution consequence. The historical NO_BLOCKER_OR_MAJOR_FINDING_OPEN receipt is preserved but does not establish
launch readiness. Review receipts must resolve a pushed reviewed commit and bind the complete code closure,
including the preparation writer, plus a reviewer identity/provenance record. Different strings do not establish
independence; keep EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT and builder/checker attribution explicit.

**R3-I / 9.6-8: environment-lock schema.** Claude implements a strict versioned `helm.reproduction-environment/1`
JSON receipt with: `schema`, `status`, `source_commit`, `image` (provider, region, AMI ID or immutable container
digest), `runtime` (Python implementation/exact version, OS/kernel/machine architecture), `accelerator` (instance
type, exact GPU model, compute capability, driver version), `libraries` (exact torch build, CUDA runtime, cuDNN,
and complete wheel/package name-version-SHA256 manifest), `numerics` (dtype, deterministic settings, TF32 flags,
matmul precision, seeds, thread counts and all prediction-affecting environment variables), and `comparison`
(explicit required-equal field paths and explicit diagnostic-only field paths with reasons). No secrets belong in
this receipt. Unknown, duplicate, null or missing required fields refuse admission. Versions must be parsed and
compared against observed runtime, not merely hashed or presence-checked. Numerical/software/library/image fields
above are required-equal by default; only hardware instance IDs, paths, elapsed time and other declared
non-predictive envelope fields are diagnostic. This decision selects a format, not invented values. Freeze actual
values from public historical records and the reviewed reproducible package before P1b. Any historical value that
cannot be established remains an explicit blocker; do not silently accept the current machine's value instead.

**Remaining builder 9.6 answers:**

- P1b must use the admitted historical RTX PRO 4500/g7 environment. P1a's T4 route check remains separate. Do not
  bypass T4_NOT_ADMITTED. Claude must return a priced, bounded P1b launcher/package and revised complete envelope
  before paying for it; the former T4 $2 slot is not an accepted g7 budget.
- Use the historical learner route for the reproduction panel. Keep the common-adapter equivalence prerequisite
  and its exact public P1a scope visible; this does not make the historical route adequate for larger HSET packets.
- Select the existing 564-record public course panel, including its 127 held-back PUBLIC course records. Do not
  add the 59-record DEV panel to the deciding panel. Freeze manifest/order/hash and all decoded slot decisions as
  part of the full decoded answer. No protected HSET content enters it. Its final manifest pin is still required.
- Our amended plan is the deciding plan, identified by exact blob hash in the downstream freeze. An integration
  copy of the older held plan is not a substitute. No P1b launcher is yet accepted.
- Fallback B is conditional on valid mismatch, a complete prospective B admission and available money. It is not
  currently funded by the reported envelope. Invalid evidence never triggers it. Do not switch the selected option.
- Acceptance requires the frozen expected verdict/status for each of all eleven cases and comparison with the
  independently derived observed fields; a producer's `pass: true` is insufficient. Cover both new static findings
  (full error validation and merge-edited evidence) and the other reader gaps before AWS acceptance.

## Spending decisions: Q1-Q9

**Q1 — S1 capacity refusal:** accept the narrow *accounting rule*, conditional on the pinned provider failure,
zero retries, no instance/volume left and full temporary-resource cleanup being evidenced for that same attempt.
Charge the conservative elapsed-time compute allowance plus $1.48 ancillary and $0.10 retained-service allowance,
rounded upward, rather than charging an unused maximum runtime. This is not proof that the invoice equals that
number, and not a general waiver of an unknown instance identity. Preserve the launcher's historical uncertainty
flag and record exactly which provider evidence resolves it. Missing, conflicting or stale cleanup evidence blocks
new admission; never reuse this exception for an ambiguous launched job. S1's canonical $15 booking remains intact.

**Q2 — money versus bookkeeping:** $60 caps study charges, conservatively bounded across all attempts and required
remaining work. The $15 fixed ledger bookings are bookkeeping reservations, not invoices and not evidence of lower
cost. C's $90 and B's $120 booking proposals do not raise the $60 spending ceiling. Never refund/rewrite the two
existing bookings or hand-edit generated ledger state. The canonical campaign cap must also pass independently.

**Q3/Q6 — the $30 stop:** count every main training attempt that actually starts an instance, including a failed
or repeated seed; no success-only reset. Smoke and nontraining prerequisites do not increment that count but their
costs remain in cumulative study spend. The normal third main attempt is M3 after M1 OFF17 and M2 ON17. Before
admitting attempt three or any later main attempt, stop when cumulative spend upper bound is >= $30. A refused
RunInstances call proven to have created no instance does not increment training starts, but remains a cost/attempt
record. An uncertain start blocks rather than reducing the count. Extra attempts cannot evade the trigger by using
new IDs or the same slot.

**Q4 — limit violation:** a job exceeding any admitted money/time/resource/update limit stops further study
admissions even if cleanup later succeeds. Preserve its outputs, true costs, losses and limit-breach status; finish
cleanup and review the failure. Do not merely count the bill and continue the planned study, or loosen a limit to
make its result eligible. This includes INVALID study evidence, not just CLEANUP_UNCONFIRMED. A prelaunch tool
failure with proved no instance can be corrected prospectively without manufacturing a study outcome.

**Q5 — M1-M6 prerequisites:** the current listed conditions are necessary but incomplete. Every main slot, including
M1, also requires P2's actual custodian feasibility/exposure receipt with a testable primary claim and supported
inference assumptions; corrected mechanism validation; all eighteen checkpoint checks enumerated; both-arm route
acceptance; the frozen source/data/starting values/worker/checker/environment; reader AWS acceptance; reviewed E1;
complete all-services reserves; and the current single-use technical and spending admissions. M2-M4 require M1's
completed valid reproduction verdict, not merely that M1 was admitted first. Under C that verdict must reproduce;
under a predeclared funded B path a valid mismatch can change control provenance. M5/M6 require that valid-mismatch
predicate, reviewed B admissions and funding within $60, not a new owner approval token. No inference may be made
from a status label without opening and checking its bound public receipts. Money and technical gates both run.

**Q7 — cancellation:** a never-admitted, never-launched slot may receive an append-only CANCELLED_NOT_LAUNCHED
record, with evidence that it has no attempt/resources. It is never deleted. Cancelling optional B slots can release
their optional reserve. Cancelling a mandatory slot makes the registered comparison COMPARISON_INCOMPLETE and
blocks main admissions; it cannot free mandatory money for another main job while claiming a complete plan. Preserve
E1/cleanup reserve. An admitted-but-unused attempt is a distinct expired admission, not falsely 'never admitted'.

**Q8 — source and cleanup:** bind admitted source, bundle, worker and checker hashes for watched and training slots.
Wrong source makes its scientific result invalid and blocks new study jobs. Cleanup must still inspect the actual
launched instance and resources: a source mismatch must not prevent their safe cleanup or hide their true cost.
Reconcile both HEAD and disk attempt identities, all source prefixes and reused job IDs/paths. Receipt omission is
not safe just because an honest runner would normally list it. Fix known L before claiming fail-closed coverage.

**Q9 — retry windows:** one admission authorizes one RunInstances attempt only. No manual retry, even inside its
window. Preserve and close that attempt, confirm cleanup and account for its costs. A retry needs a new immutable
attempt row and fresh review/admission including replacement cap and all remaining mandatory work. If the frozen
schema cannot express this, retries are forbidden until a prospectively reviewed schema revision exists. That is
implementation preparation, not permission to change statistical rules after a result. The five-minute window in
R3-F replaces the proposed reusable lifetime; source-at-HEAD scripts must accept the admitted immutable source.
An expired unused admission may be closed with proof of no launch and reissued; never rewrite it as PLANNED.

## Envelope consequences and next Claude handoff

The reported $5.44 spent upper bound and $57.08 C bound are Claude's current program output, not an invoice or an
accepted complete final envelope. $57.08 leaves $2.92 before any omitted cost or g7 P1b change. Conservatively
include the already flagged earlier preparation amount $1.9180 pending owner resolution of scope: this arithmetic
alone gives $58.998 (round upward to $59.00), leaving $1.002 (at most $1.00 on cent bounds), not about $0.50.
Other charges could reduce that further; none may be hidden. The existing escalation remains open, but preparation
can proceed with inclusion without requiring an owner response now. Do not exclude these charges merely to fit.

Retained evidence is not free. The plan's accounting horizon was execution plus 30 days after E1; the new gate's
$0.10/job formula claims 12 months. Keep both assumptions visible and reconcile object sizes, transfer, request
charges, duration and ongoing retention before final freeze. Report ongoing charges beyond the bound. No automatic
permanent deletion, security change or expanded ceiling is authorized here. Existing retention/escalation records
remain. Price P1b on g7 and E1's real scope, keep cleanup/readout reserves, then recompute job count, estimates and
worst-case admission bounds. Do not call $57.08 the final maximum or the historical hybrid $51.58 an expected bill.

Claude should implement the reader and per-attempt gate corrections, fold A2.7 into its builder, publish public
conformance/throwaway feasibility receipts and return exact pushed commits. Codex will review those bounded changes.
No duplicate reader, builder, watcher, runner or protected-test copy was created. Main launch remains disabled.
