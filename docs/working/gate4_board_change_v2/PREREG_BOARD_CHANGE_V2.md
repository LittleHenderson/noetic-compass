# PREREG — BOARD CHANGE TEST, v2

**Status: `DESIGN_ONLY / INERT / NOT AUTHORIZED / NOT RUN / NOT VALIDATED`.**  
**Protocol:** `board-change-v2`  
**Historical predecessor:** v1 result commit `18be4f05b2cf06ffe461bf68b32c48fabfb6510b`.

This protocol is prospective. It contains no v2 prompt plan, corpus, label, prediction,
provider receipt, or result. It preserves the v1 pilot as immutable historical evidence and
uses only its preregistered sizing output, `K_neutral=72`.

## 1. Claims

**Claim 1 — retrospective detection.** Given two consecutive assistant turns, does the
indicator that their consensus board labels differ detect a blind T-CHANGE panel's `CHANGE`
label better than surface and trivial controls?

**Claim 2 — prospective early warning.** Among pairs where a blind T-USER panel says the
second user message did not ask for a different kind of response, does the board label at
turn N predict a T-CHANGE at N+1 better than turn-N surface, trivial, user-move, turn-position,
generator, and within-conversation permutation controls?

Claim 1 never licenses Claim 2. User-induced Claim-2 results are descriptive and license
nothing.

## 2. Frozen corpus shape

- 72 neutral Stratum-N conversations and 20 shifting Stratum-S conversations.
- 92 fresh seed prompts, with no exact or normalized duplicates and no v1 seed reuse.
- 10 assistant turns per conversation, exactly: 920 assistant turns total.
- 9 transitions per conversation: 828 total, comprising 648 N and 180 S transitions.
- Four generators in a fixed rotation; each receives exactly 18 N and 5 S conversations.
- Three blind readers per item from the same four-model panel, excluding the generator for
  assistant-output tasks.

The 72N choice came from the v1 prospective resize formula before the v2 corpus exists:
`ceil(40 / (2.98 × 0.1884)) = 72`. This does not guarantee 40 changes. If fewer than 40
model-initiated changes or 150 model-initiated analysable pairs remain, Claim 2 is `VACUOUS`.

No v1 conversation or label enters v2. The prompt plan must be authored blind, frozen in
`prompt_plan_v2.json`, committed with the protocol, and remotely observed before the first
generation attempt. This implementation agent is ineligible to author it because it has
seen the taxonomy and v1 results.

## 3. Generation and label protocol

The frozen model roster remains:

- `gemini-2.5-flash`
- `deepseek-v4-pro`
- `qwen3.8-max`
- `glm-4.6`

Generation is sequential within a conversation and parallel only across conversations.
Generation uses temperature `0.7` and `max_tokens=4000`, carrying v1 amendment A1 forward
prospectively. Label calls use temperature `0`, `max_tokens=16000`, and `20000` for GLM.

Every conversation must produce all 10 accepted turns. V2 does not truncate a conversation,
drop it, replace its seed, swap its provider, or silently shrink the registered sample. An
exhausted operation halts the run.

Reader tasks and views remain:

- T-BOARD: one assistant turn, six codes B1–B5/B0;
- T-CHANGE: two assistant turns, `CHANGE`/`SAME`;
- T-USER: two user turns, `DIFFERENT-KIND`/`SAME-KIND`.

Main batch sizes are 6, 4, and 12 respectively. A response is accepted only with a 2xx
provider response, a terminal `stop`, answer-body JSON, exact alias-id set equality, one
allowed label per id, and no fabricated id. Rejected output produces zero labels.

Transport attempts for one logical call are numbered. A retry must point to the immediately
previous attempt record. Label repair rounds are separately identified as `main`,
`repair-1`, and `repair-2`; the repair round is part of the operation id. Only an `accepted`
attempt completes an operation. A `finish_length`, parse failure, id mismatch, incomplete id
set, timeout, or 429 never enters the completed set.

## 4. Chronology and state machine

The registered future production path is:

`DRAFT → PROTOCOL_FROZEN → FULL_RUN_AUTHORIZED → GENERATING → GENERATION_COMPLETE → CORPUS_SEALED → LABELING → LABELS_COMPLETE → GATE0_COMPLETE → ANALYSIS_COMPLETE`.

`HALTED` is terminal. There is no resume from a mutated protocol, replaced prompt plan, or
changed sealed corpus under the same run id.

`PROTOCOL_FROZEN` requires byte verification of this preregistration, runner, core, schemas,
and the 92-row prompt plan against `protocol_lock_v2.json`. The lock names the exact Git
commit and a remotely observed ref.

`FULL_RUN_AUTHORIZED` requires a one-use artifact bound to the protocol-lock hash, prompt-plan
hash, run id, scope `FULL_72N_20S`, expiry, provider-attempt ceiling, and cost ceiling. Its
exact claims must carry an allowlisted detached signature verified against an external trust
registry and a non-revoked key/receipt at the trusted observation time. A self-declared JSON
file, backdated receipt older than 15 minutes, or shape validation alone grants no authority.
This offline runner has no pinned verifier, trusted clock, clean-HEAD observer, remote-ref
observer, or authenticated billing verifier. None can be supplied as a callback. Therefore
authorization remains explicitly impossible and the production state stops at
`PROTOCOL_FROZEN` (or `HALTED`). Offline regressions use separate `MOCK_TEST_ONLY` phases:
`MOCK_RUN_AUTHORIZED → MOCK_GENERATING → MOCK_GENERATION_COMPLETE →
MOCK_CORPUS_SEALED → MOCK_LABELING`. Mock receipts never authorize `FULL`.

`GENERATION_COMPLETE` requires one accepted evidence-bound operation for all 920 turns.
Before any label call, v2 canonicalizes the 92 conversations, hashes every row and the whole
corpus, writes `corpus_seal.json`, and transitions to `CORPUS_SEALED`. Every label attempt
then names that exact corpus hash. If any label attempt predates the seal, the run is not
prospective and sealing fails.

## 5. Provider provenance

Every attempt, including errors and retries, records immutable hash-chained fields:

- operation id, attempt number, preceding attempt id, repair round, and disposition;
- provider, exact allowlisted HTTPS origin and chat path, requested model, and resolved
  response model;
- provider request id and provider-created time, each explicitly `present` or `unavailable`;
- exact request body, raw response body, and response headers as content-addressed artifacts;
- SDK name/version, local start/end UTC, HTTP status, finish reason, token usage, and error;
- protocol-lock, prompt-plan, and (for labels) corpus-seal hashes.

Every accepted mock row additionally binds the immutable frozen-bundle hash, mock
authorization event, phase-start event, admission time, and mechanically derived mock cost.
Nonzero usage cannot have zero derived cost. Mock usage/rates are explicitly unauthenticated
and not billing evidence; a future production path requires authenticated usage and pricing
receipts and remains unavailable here. Direct/imported rows
are recorded only as `AUDIT_ONLY_UNTRUSTED_NEVER_ACCEPTABLE` in a separate ledger and can
never satisfy generation or labeling completion.

Raw evidence is stored outside the ledger; the ledger stores its relative path, byte count,
and SHA-256. Accepted attempts require the request, response, and header artifacts and a
resolved response model. API keys, authorization headers, query credentials, and secret
environment values are forbidden from evidence. Secret-bearing request/header keys and
Bearer/key-shaped values fail closed before acceptance.

An accepted generation request body must be canonical JSON exactly equal to the frozen
model, temperature `0.7`, `max_tokens=4000`, current frozen seed/follow-up, and the complete
alternating history reconstructed from earlier accepted raw responses. A bogus or partial
message list cannot enter the ledger.

An accepted generation response must resolve a declared JSON pointer inside the hash-checked
raw response to the exact assistant text later sealed in the corpus. An accepted label
response must resolve to answer-body JSON whose alias-id set exactly equals the frozen alias
map, with one allowed label per id and an exact parsed-label hash. `length`, `error`, missing
content, fabricated ids, duplicate ids, or post-hoc text never count as accepted work.

## 6. Analysis and controls

All fitted predictors use grouped leave-one-conversation-out evaluation. Claim-1 surface
arms read both turns: character 3–5 grams, word unigrams, length/delta, and pair distance.
Claim-2 surface arms read turn N only: character 3–5 grams, word unigrams, and length.
User move, turn position, generator identity, base-rate strategies, generator/reader
separation, and reader dispersion remain mandatory controls. Uncomputable controls are
`null`, never `true`, and make the applicable claim `VACUOUS`.

Claim 2 P1 is frozen as `b_N` only with logistic regression `C=1.0`, `max_iter=500`,
`random_state=42`, evaluated leave-one-conversation-out. The hyperparameter is fixed rather
than tuned after data.

### Corrected permutation null

For each of 1,000 trials, v2:

1. permutes the binary T-CHANGE outcome inside each conversation;
2. keeps features and conversation groups fixed;
3. rebuilds every leave-one-conversation-out training fold;
4. refits a fresh P1 learner on the permuted training outcomes;
5. predicts each held-out conversation; and
6. scores F1 against that trial's permuted held-out outcomes.

The claim-bearing entrypoint accepts only the registered P1 learner, 1,000 trials, and seed
`0`; caller-selected predictors, learner ids, trial counts, and seeds fail closed. It also
checks every prediction is binary. Precomputed real-outcome predictions cannot be supplied
to this API. The output records
`null_refit_invocations=1000`, every permuted-label-vector hash, the complete null score
array, mean, p95, p99, and empirical p. Claim 1's board-change indicator fits no learner and
therefore retains the deterministic fixed-prediction block null.

Until a completed label manifest, admitted labels, and Gate 0 are mechanically bound to the
analysis input, this package marks the result
`NOT_CLAIM_ELIGIBLE_UNTIL_SEALED_LABEL_GATE0_BINDING`. It is not a scientific Claim-2 result.

## 7. Gates

Gate 0 retains the v1 thresholds:

- κ: board ≥0.35, change ≥0.35, user ≥0.30;
- at least 60 complete cases per task and complete-case coverage ≥0.60;
- consensus coverage: board ≥0.70, change ≥0.75, user ≥0.75;
- B0 share ≤0.40;
- residual same-conversation batch collisions =0;
- at least 240 analysable pairs; and
- Stratum-S T-USER positive-control rate ≥0.50.

Claim 1 retains 0.05 margins over the strongest surface, trivial, and user-move controls;
MCC and its cluster-bootstrap fifth percentile must exceed zero; permutation p<0.05 and real
F1>null p95. Turn-position or generator margins below 0.05 downgrade the result.

Claim 2 requires at least 40 model-initiated changes and 150 model-initiated pairs; 0.10
margins over strongest turn-N surface, trivial, user-move, turn-position, and generator
controls; MCC and its cluster-bootstrap fifth percentile above zero; and the corrected
refit permutation p<0.01 with real F1>null p99.

Verdicts remain `VACUOUS`, `REJECTED`, `PARTIAL`, `HOLDS`, or `NULL`. `HOLDS` is the ceiling
and means present only on this enriched output-space fixture against these controls. It is
not `VALIDATED` and is not CAS-specific without a separately preregistered matched-taxonomy
control and independent replication.

## 8. Claim ceiling

This is an output-reading experiment, not an internal-model experiment. It cannot establish
hidden-state analysis, layer localization, pre-output trajectories, pre-speech interception,
architecture or semantic-circuit discovery, ablation, causal steering, prompt-injection
detection, hallucination detection, reasoning-break detection, or adapter generation.

## 9. Amendment rule

No claim-bearing v2 file may change after `PROTOCOL_FROZEN`. A defect found before the first
provider call requires a new lock and new run id. A defect found after any provider call
halts this run; it cannot be repaired in place. Results, report, and master-spec status must
be committed together when a real run eventually completes.
