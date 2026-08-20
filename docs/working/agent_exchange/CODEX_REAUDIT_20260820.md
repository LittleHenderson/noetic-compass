# Codex re-audit of the 2026-08-19 Board / WELD handoff

**Audit date:** 2026-08-20

**Inherited commit:** `34442035c69e7feccd6c3b67447568776fe3528f`

**Audit verdict:** `NO-GO AS CLAIMED`

**Scientific status:** no new validated model capability; no Gate-5 closure

## Bottom line

The inherited work contains useful engineering and some correctly computed
descriptive results. It does **not** support its headline conclusions that the
Board taxonomy is dead for natural conversation, that more data cannot change
the result, or that WELD v2 is validated. Those statements exceed the frozen
protocols and the evidence.

The defensible ceiling is:

- Board v1 pilot: `VACUOUS / EXACT-CORPUS FIT FAILURE / NOT A STOP SIGNAL`.
- WELD v2: `REAL / ENGINEERED / NOT_VALIDATED` on one synthetic numeric axis.
- drive-tag regex change: a real fix for domain markers immediately followed by
  `_`, with a narrower blast radius than the handoff claimed.
- model-facing J1/J2/Stage-5 abilities: `NOT_RUN`.

## What reproduced

Independent recomputation reproduced the Board pilot's panel kappas, `138/26`
class split, change F1 `0.264706`, MCC `0.043776`, permutation `p=0.64036`,
and all reported input hashes. The exact pilot corpus has Board `B0` on
`115/157` admitted rows; this remains stable under missing-label imputations.

The drive-tag regex repair correctly recovers domain markers such as
`^E_{F5}` and `^C_{F5}`. The belief tests remained green. The WELD v2 default
script also reproduces its recorded six cases against the installed scanner.

These positives are narrow. They do not rescue the scientific or validation
claims below.

## Board v1 blocking findings

1. The full `generate` and `label` stages are unreachable. The CLI rejects all
   non-smoke/non-pilot stages other than `analyze`.
2. The corpus builder hardcodes `60N+20S` and only 80 unique seeds, while the
   pilot's own spend rule selected `72N`; no additional blind prompt bank or
   allocation exists.
3. Failed repair results enter the done set, while operation keys omit the
   repair round/attempt. A failed first repair can therefore suppress the
   permitted second repair.
4. Provider evidence omits the complete attempt lineage, request IDs, resolved
   response model, raw-response hashes, usage, and trustworthy timestamps.
5. Claim 2 permutes outcomes against fixed predictions instead of refitting the
   learner for every null draw.
6. The 16-conversation pilot deliberately enriches Stratum N, has no Stratum S,
   and uses scripted continuers. It cannot establish a result about ordinary
   natural conversation. The preregistration explicitly says pilot `VACUOUS`
   is not a stop signal.

Therefore `v1 DEAD`, `taxonomy does not fit natural conversation`, and `more
data will not move it` are not licensed. The exact-corpus Board collapse is a
real design warning, not a population conclusion.

## WELD v2 blocking findings

1. The purported preregistration, runner, expected outcomes, report, and stdout
   first appear in the same commit. There is no prior immutable outcome-blind
   protocol.
2. Expected outcomes are embedded in the runner and determine success. The
   empirical random result is reported but does not affect the verdict.
3. The actor can read mutable ground truth directly; the advertised read log
   and one-parameter function signature do not enforce blindness.
4. NEG-3 changes the localizer implementation. It is not a failing input passed
   through the same fixed pipeline.
5. The ambient `cas_engine` binary is not bound by path, bytes, version, or
   source identity. Python duplicates Rust decision thresholds, so drift changes
   what the report says fired.
6. The random comparator receives less information and fewer adaptive calls
   than the primary method. It is not a matched outcome-bearing control.

WELD v2 is a useful engineered unit demonstration. It is not a pre-registered
validation result.

## Regex and persistence correction

The old regex missed a domain marker when the domain letter was immediately
followed by `_`; it did **not** make axis W impossible on every expression that
merely contained a drive tag. Direct `run_inversion_scan` production use is in
the belief store. The verifier and Mode-7 route use separate parsers, so the
claimed three-consumer blast radius was false.

A read-only audit of the default belief database found 21 of 30 stored rows
whose W-axis payload differed after recomputation. None of the 30 current
overall verdicts flipped because affected records contained only one domain.
The old schema stored no scanner version and could not detect stale rows.

The successor branch adds a scanner-version column, atomic stale-row migration
on store open, and a Unicode-aware marker boundary. The live default database
was inspected read-only; it was never opened through the mutating store path or
migrated during testing.

## Additional model-path findings

- The current live worker is explicitly a stub/fake and is not evidence of a
  real model path.
- The inherited 40E evaluator selected the best layer using the test set.
- The inherited open-weight shard discarded neuron identity and activation
  sign, then treated absolute top-k magnitudes as though they were the registered
  full hidden vector.
- The eta/epsilon bridge selected layers using a test metric and imported a
  helper that did not exist on this branch.
- The exact Stage-9 fixture uses registered `metadata.split` and
  `metadata.counterfactual_pair_id`; resampling normalized prompt text is not a
  faithful replay.

The corrective pass closed the direct test-set layer-selection leak, unsafe
NPZ prompt unpickling, zero-scenario success path, layer truncation, lossy
readout overclaim, forged runtime-feature declaration, and forged self-hashed
execution-plan claims. Those are model-free engineering fixes, not model
evidence.

Remaining system boundary after the first corrective pass:

1. The historical 40E capture's metadata has `model_revision: null`. Editing
   that metadata later cannot create missing capture-time provenance. The
   historical artifact must remain `MODEL_REVISION_UNAVAILABLE / NOT PACKET
   ELIGIBLE`; a future run needs a pre-capture model/config/tokenizer/weight
   receipt.
2. The interpretability adapter and the open-weight worker were still separate
   implementations. Until the worker consumes and re-verifies the exact
   adapter plan and hook paths, the combined ability is `NOT_WIRED`.
3. Evaluator and shard schema versions had not changed despite materially new
   admission, split, null and proof semantics. Downstream consumers therefore
   could not distinguish old from corrected artifacts.
4. The shard wrote a truthful failure payload but returned process exit 0.
   Without a real, tested supervisor proving it rejects that payload, the
   system-level fail-closed claim was unproved.

The offline corrective implementation now closes those four software defects,
without upgrading the evidence. Evaluator schema `v3` pins the exact historical
metadata digest and model ID and permanently emits
`MODEL_REVISION_UNAVAILABLE / NOT_PACKET_ELIGIBLE` for those bytes; a 40-hex
value inserted into a modified copy is rejected. Worker schema `v2` requires,
re-verifies, and consumes the adapter plan's exact selected MLP hook paths and
records the adapter-plan, model/config/structural-weight, tokenizer, scenario,
prompt, token, capture-source, and dependency identities that it can actually
observe. It still says explicitly that loaded weight values and tokenizer-file
bytes are not attested. Schema allowlists reject the intermediate semantics,
unconverged logistic fits fail closed, and a failed/rejected shard exits
nonzero. The 4.16-GB NPZ is materialized from one open handle, hashed before and
after parsing, and rejected if its digest, descriptor, or path identity changes.
No post-hoc metadata edit is accepted as historical provenance, and none of
these offline tests is a model run.

Final hostile-consumer correction: the merger admits **no current readout
schema**. Legacy `v1` has no available canonical artifact/digest binding, while
the current `v3` producer is permanently non-packet-eligible for the historical
capture; both are rejected until a separately reviewed future schema and
pre-capture receipt exist. Optional causal/control/bridge JSON is `unverified`,
never `present`, until each tier has its own strict validator. JSON duplicate
keys and non-finite numbers are rejected. JSON parse/hash uses one in-memory
byte snapshot; the shard likewise binds scenario parse/hash to one snapshot and
requires a non-empty, unique, allowlisted, method/output-consistent contract.
Distributed schemas reject a `completed` worker with errors, missing outputs,
or an inexact produced-output set, and reject a `complete` merge with gaps or
identity/contract mismatches. These are admission guards, not a new
orchestration layer.

A fresh post-fix hostile replay returned `P0=0 / P1=0` for this deliberately
blocked engineering boundary: 85 focused checks and 28 direct hostile cases
passed. Forged tiny v3, empty v1, empty optional proofs, duplicate/non-finite
JSON, empty shard contracts, and false-complete worker/merge objects all fail
closed. This is a GO only for `NOT_PACKET_ELIGIBLE / NOT_RUN`; the merger admits
zero schemas, loaded weight/tokenizer bytes are unproved, and there is no
provider/model/Evidence-Packet readiness claim.

## Corrective successor boundary

The isolated successor branch repairs the bounded mechanics above and adds
offline Board-v2 and WELD-v3 design packages. No provider, model, GPU, AWS, or
scientific experiment was run. Candidate successors remain `ENGINEERED /
NOT_RUN / NOT_VALIDATED` until their own hostile audits, external authority,
and real evidence requirements are satisfied.

### WELD v3 final offline audit

The WELD-v3 successor passed a fresh offline correctness audit for its narrow
scaffold claim: `P0=0 / P1=0 / P2=2`, 21/21 tests. The exact 18-file,
133,439-byte package has sorted-manifest SHA-256
`9243bc7e0b4c6e1ceedfdfe7ee163030e5ac505a05f93dc4e351c560e4573bae`.
It rejects zero-invocation receipts, post-seal actor-receipt mutation,
low-diversity commitment material, the tested Python-as-Rust relabel, and
structural/numeric/boolean/token information mismatches. It checks frozen
bytes before the truth path. Production adjudication is deliberately blocked
until a trusted external-anchor verifier exists.

This is a **narrow engineering GO and a production/scientific NO-GO**.
Invocation rows remain validated records rather than independent OS execution
attestations. External custody, entropy provenance, Rust build identity and
anchor authenticity are not proved. Two P2 test gaps remain: no dedicated
committed test for the unconditional production block, and no adjudicator-side
test devoted specifically to frozen-hash-before-truth ordering.

### Board v2 first hostile audit

The first Board-v2 successor was **NO-GO as an acceptance-ready design** even
though its supplied suite passed 28/28. Exact audited identity was
`43726a99820a6c9dd42e8de887cf9f2bf9e9ab5517e635d4502d6d340ffe1d2d`
over 26 files. Independent temp-only probes demonstrated:

- all 920 turns could be admitted and sealed with a bogus raw provider request
  unrelated to the frozen prompt or conversation history;
- direct state transitions could reach `ANALYSIS_COMPLETE` with empty evidence;
- Claim 2 accepted one trial and a static predictor that never refit while
  asserting `refit_on_every_permuted_outcome=true`;
- caller-injected clocks/verifier callbacks, fake commit/remote declarations,
  caller-declared zero cost with nonzero usage, arbitrary HTTPS origins,
  secret-bearing headers, and normalized historical prompt reuse were admitted;
- label aliases/items were not derived from and frozen against the actual
  sealed corpus.

Genuine controls also survived: direct append stayed audit-only; wrong
run/protocol/plan bindings and frozen-plan mutation rejected; declared
attempt/cost ceilings, finish/error/raw-response checks, repair lineage,
pre-seal label chronology, response extraction and hash-chain integrity worked.
The package was retained only as `DESIGN_ONLY / INERT`; it was not authorized
or run. A revised offline successor must re-enter hostile audit before any
higher status.

### Board v2 corrected successor re-audit

The corrected successor re-entered independent hostile audit at exact
cache-excluded package identity
`8878a960f6881575d6a0d688579b0ef4f32f606018a6fc0203735f861ae0fdac`
(27 files, 263,500 content bytes; 2,740-byte canonical manifest stream).
Three independent executions of those exact candidate bytes passed the full
offline suite: 35/35 in 179.79 seconds, 35/35 in 178.14 seconds, and 35/35 in
164.85 seconds. A separate compact hostile matrix passed 22/22 with zero
bypasses.

The corrected design rejects bogus turn-0 requests, forged prior-assistant
history, direct phase skips, attempted use of the internal transition sentinel,
production authorization or admission, injected clocks/verifiers, Claim-2
trial/seed/predictor/learner overrides, caller-declared zero cost, unrelated
provider origins, secret-bearing headers, and normalized historical-prompt
reuse. The 80 exact and 80 normalized v1 fingerprints independently rebuild
from their cited historical sources. Claim 2 mechanically performs 1,001 fits
for its fixed 1,000-trial null and remains explicitly
`NOT_CLAIM_ELIGIBLE_UNTIL_SEALED_LABEL_GATE0_BINDING`.

Verdict: **GO only to retain the exact package as `DESIGN_ONLY / INERT /
NOT_AUTHORIZED / NOT_RUN / NOT_VALIDATED`**. Production and scientific
execution remain intentional NO-GO. The package has no authored 92-prompt
plan, remotely observed clean-tree lock, trusted authority/clock, provider or
billing adapter, sealed-corpus-derived label manifest, completed labels, Gate
0, or claim-bearing analysis path. No provider, model, network, GPU, or
scientific run occurred.

Gate 5 remains `OPEN / KEEP_OPEN`. Stage C remains
`DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED`. The scientific corpus remains
`0 / 960`.
