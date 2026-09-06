# Child-call preparation: source-grounded implementation draft

Status: **PROPOSED_ONLY — no code change, model load, training, native execution, reservation or launch.**

This is a bounded plan for the newly requested child-selection and input-binding experiment. V7 remains a checked partial campaign with a complete CAS **0/72** negative. This document does not change its source, results, accepted runtime, guard logic or baseline weights.

The current controlling charter must be read completely before behavior-changing implementation. This inspection read the CNCM AGENTS.md and the new user request; the attempted full charter read was truncated, so no complete charter review is claimed here.

## Exact existing parts to reuse

All paths below are under:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/`

- `cas_meta2/policy_v3.py:34` — `encode_batch`: existing lossless public input, observation pointer inputs and exact lexical copy spans.
- `cas_meta2/policy_v3.py:117` — `decode_with_telemetry(memory, batch, decoder_input_ids)`: next-token log probabilities, fixed/copy probabilities and copy gate, with no new neural head.
- `cas_meta2/policy_v3.py:162` — `build_matched_policies`: matched CAS/generic encoders and exactly copied shared initial decoder/binding/copy parameters.
- `cas_meta2/policy_v3.py:222` — `predict_public`: frozen grammar_v3 greedy rollout for the saved-model diagnostic.
- `cas_meta2/policy.py:88` — `encode_targets`: exact next-token shift and right padding.
- `cas_meta2/selection_v3.py:79` — `target_token_roles`: development-only role labels aligned to codec positions.
- `cas_meta2/grammar_v3.py` — `GrammarState`: the actual V7 syntax/scope state, bounds and EOS checks.
- `cas_meta2/features_v2.py`, `features_v3.py`, `codec.py` — unchanged tokenizer, lexical spans and action vocabulary.
- `cas_meta2/contrast_v7/train.py:190` — existing V7 checkpoint payload checks to reproduce in a small read-only loader. Its loader is a nested function, not an importable general checkpoint API.
- `cas_meta2/train_v3.py:156`, `:174` — deterministic CUDA setup and environment identity.
- `cas_meta2/curriculum_v3.py:176`, `:198` — public wording and checked fresh observations. Reuse their contracts; do not import a full dataset generator into a model worker.
- `cas_meta2/ir.py:228`, `curriculum.py:108`, `:113` — pure IR validation, native-topology checking and renaming-independent graph fingerprints.
- `cas_meta2/native.py:46`, `:305`, `:483` — accepted admission, native execution and actual task verifier. No change is proposed.

The frozen `loss_v3.weighted_training_loss` rejects zero weights on non-padding tokens. Do not silently feed it a new hole-only mask. A separate candidate-only, tested loss adapter is required if fixed scaffold tokens receive zero training loss.

## Stage 1: saved-model next-decision diagnostic

Use the V7 initial and selected checkpoints for both families. Read their tokenizer/config/source/checkpoint identities, then load weights only in the approved AWS CUDA worker. Never call the older v3 checkpoint loader on a v7 payload without explicitly validating the different schema.

Proposed fixed development cohort:

- The existing 24 training-probe tasks, reported as familiar training material.
- The existing 96 validation tasks, separately reported by depths 1, 2 and 3.
- No V7 final-test task, private-test target or new final-evaluation target.
- Four checkpoint arms, so 480 task/checkpoint rows. This is repeated observation of 120 tasks, not 480 independent tasks.
- Enumerate all relevant decision sites and record the actual per-role/depth denominators before GPU execution. Do not invent these counts from the number of tasks.

For reference tokens `t[0..L-1]`, where `t[0]` is BOS, the target at index `j >= 1` is predicted from `t[:j]` at decoder output index `j-1`. The last input token is not the token being scored. EOS is scored once; PAD is never a decision.

A single teacher-forced CUDA forward pass can score all correct-prefix sites. Use `model.eval()`, `torch.no_grad()`, the original input encoding and the unchanged model. Report separately:

1. Raw full-vocabulary top-1 and target NLL.
2. Top-1 after the actual grammar_v3 mask and, if reported, explicitly renormalized masked target NLL.
3. Whether the target token was legal at that prefix.
4. Binding, CALL-child, CALL-input, other RUN-input and parent/child RETURN roles. Do not combine all input sites into one unexplained count.

For the self-generated condition, use the unchanged `predict_public` rollout and save each emitted prefix/rejection. Reconstruct complete action tokens with the exact codec; rejected actions retain their actual `token_ids`. Replay/scoring must preserve the registered batch order and size, not silently change generation conditions.

**Do not compare the same token index after the two programs diverge.** Match a next-decision site only where its public procedure, instruction address, role and relevant value-definition context still correspond. The requested token must remain meaningful and legal in that generated state. If prior changes have changed the identity of the needed value, the intended child context, or the role, mark that site non-comparable rather than treating a gold token as a repair oracle.

For every reference decision opportunity, retain exactly one state:

- matched and correct;
- matched and wrong;
- not reached because generation stopped;
- role/instruction context changed;
- required value/child absent or illegal;
- ambiguous correspondence.

Publish correct/attempted matched-decision accuracy **and** matched/total-reference-opportunity coverage. Preserve the full opportunity denominator and all unmatched counts. Stratify matching sites by whether any preceding token differed. This may yield little comparable evidence after an early divergence; that is a result, not permission to insert gold prefixes.

This is a requested-program decision diagnostic. It does not define the optimal recovery action from an arbitrary wrong state, establish a neural root cause, or count assisted prefixes as autonomous task success. Keep literal-name matching as a labeled debugging measure; native task correctness remains renaming-independent and separately executed.

### Source-observed agreement and differences

- The one-token teacher-forcing shift is consistent with the greedy next-token call.
- Training and inference use the same model, observation-binding pointer and lexical-copy mixture.
- Training uses full-vocabulary normalized NLL under correct prefixes; inference takes grammar-masked argmax under generated prefixes. This is an actual distribution/objective difference, not evidence of an implementation defect.
- V7 uses grammar_v3, not the separate viability_v4 candidate.
- `encode_targets` and prediction both enforce the 256-token action bound without silent truncation; prediction reserves the final slot for EOS.
- No source evidence found here establishes a missing pointer, off-by-one target shift, or need to replace the CAS encoder.

## Stage 2: one child call with a supplied parent skeleton

The existing IR takes **one** procedure input named `arg`; do not invent a multi-argument native API.

A small supplied parent may create multiple available typed value references with fixed RUN steps. It then has one learned CALL. Additional fixed work may occur before or after the call so the returned value is not always the most recently created variable. Whether this supplies two genuinely different, usable inputs under the existing native fixture is an explicit construction gate below, not an established capability.

The model owns four explicit decisions:

1. Public observation binding, using BIND0/BIND1/BIND2 and the existing pointer.
2. Which familiar child from a public catalog to call.
3. Which in-scope, type-compatible available value to pass to that child.
4. Which available result the parent returns, including distractors.

The initial positive task should require the selected child's returned result to reach the parent result. The public source variable names, instruction placement and distractors vary, so this is not a constant `RETURN vN` target. Child bodies are familiar, explicitly supplied procedures using the existing A/B/C topology; their own body/return is supplied at this stage. Learning a child body's return is a separately declared later removal of scaffolding, not an unannounced fifth task.

The scaffold controller supplies legal instruction markers, declarations, fresh output names, scopes and selected catalog bodies. It must never choose the semantic child, input or returned value for the model. The same controller and candidate sets apply to both model families and the rule control. Fixed tokens appear in the decoder prefix; no new pointer or hidden representation is required.

**Reachability trap:** the actual IR rejects `UNREACHABLE_PROCEDURE`. A catalog containing several possible children cannot simply be included wholesale in an executable that calls only one. Compile only the predicted child's reachable catalog closure, determined from the prediction. All catalog options remain public before the choice. Never prune based on the correct task answer.

Before any GPU work, enumerate every legal child/input/return tuple for each development scaffold. Compile and run the existing pure codec, IR, scope, budget and native-topology checks on every tuple. This must show that the scaffold offers genuinely different legal answers and does not hide the right choice in an answer-dependent mask. Pure checks do not establish that every tuple survives native execution; the durable-distinct-^6 guard and all real runtime failures remain intact.

Some repeated A operations can produce numerically equal values while retaining distinct producing-operation identities. Report that property. The unchanged task verifier checks required dependencies as well as actual outputs, so provenance-only binding correctness remains a legitimate narrow diagnostic, but it is not enough to establish the requested transferable selection between meaningfully different inputs.

**Unresolved construction gate:** each scored scaffold needs at least two legal input choices whose effects are semantically distinguishable, and at least two child and return choices with nontrivial target variation. Two identical A(arg) results with different variable names do not meet that gate on their own. Nor does presenting A/B/C values when the topology mask leaves only one permitted edge. Measure candidate-set sizes before semantic scoring; do not count forced singleton decisions as learned accuracy.

The pure compiler/topology enumeration is necessary but not sufficient for that gate. A small development-only CUDA check must establish that at least two advertised input choices can execute under the unchanged contract and produce a meaningful controlled contrast. Original arg versus an accepted A Effect is a candidate to investigate, not an assumed solution: B(original observation) caused the saved guard failures, and the guard must remain intact. If the accepted single-argument fixture cannot supply this contrast without new semantics, stop at an explicitly unresolved curriculum-construction issue. Do not invent multi-input transport or disguise provenance-only variation as the stronger skill. Do not use private expected outcomes to filter a candidate's choices at inference.

### Candidate training adapter

Keep `policy_v3`, model dimensions and all accepted execution code unchanged. Build fresh matched CAS/generic candidate copies with common initialization. Do not overwrite or promote the accepted model or V7 candidates.

Use `encode_targets` and the existing normalized model log probabilities. A small candidate-only loss computes NLL at the four registered learned holes, with an exact positive hole count and zero contribution from forced scaffold tokens. Check this alignment in pure tests and a CUDA preflight. Document that this is a changed training objective, not the old 3:1 full-program loss.

Both families receive identical scaffold text, candidate ordering, batches, example order, epochs, optimizer settings and hole loss. The scaffold advances after each model choice, so later holes see earlier model choices at free evaluation. Teacher-forced validation is reported separately.

Proposed cap: 100 epochs, batch size 16, 192 training examples = 1,200 optimizer steps per family if all requested epochs finish. Early timeout remains incomplete, never an implied successful run. Checkpoints are selected only using the declared validation metric, not final task outcomes. Save initial, validation-selected and final candidate identities, plus before/after predictions.

## Proposed splits and actual novelty checks

These are planned counts, **not an assembled curriculum claim**:

- Train: 192 depth-2 examples.
- Validation: 64 depth-2 examples, split into 32 familiar-structure/new-input examples and 32 development-only unseen-combination examples.
- Final native evaluation: 48 fresh depth-2 examples: 24 familiar-structure/new-input and 24 unseen-combination examples.

Use separate construction-template pools for the validation and final unseen-combination groups. Each primitive child and required decision token must have positive training exposure, while the held-out composition of child/input/return/placement choices remains new. Keep minimal-pair siblings within the same split and record their shared group identity.

The familiar-structure group intentionally reuses a training structural fingerprint with new observation payloads, name assignments and presentation arrangements. Label it that way; it is not unseen-composition evidence. The unseen-combination group must remain disjoint by the existing renaming-independent graph fingerprint and a declared scaffold/decision-combination fingerprint. Disjoint numeric inputs alone are not enough.

The fixed output vocabulary is `main/p0..p15`, `arg/v0..v31`, `A/B/C/R`. Fresh names mean new assignments within supported names, plus fresh external labels/wording where the input tokenizer can represent them. Unsupported output identifiers are not silently added.

The old `contrast_v6.curriculum.validate` rejects every train/test graph overlap. It therefore cannot validate the new familiar-structure split unchanged. Add a narrow versioned split validator with explicit allowed overlaps and separate novelty claims; do not weaken the old checker.

Freeze all new final tasks before candidate tuning. Exclude the already opened V7 final graphs from the new final unseen-composition group. V7 validation may inform this development diagnosis but can never be relabeled as new final evidence. Fit any new tokenizer on training publics only.

## Native scoring and later stages

Execute the completed scaffold programs through the unchanged runtime, then `native.verify_task`. Score local decisions, admissible completion and actual complete-task correctness separately. Publish attempted denominators, first wrong decision, admission rejections, runtime failures and unknowns. Rules get the same public problem/catalog/scaffold, not private targets.

The existing v7 native coordinator is frozen around its prior manifest/arms and should not be edited to pretend the new experiment is V7. A small versioned coordinator can reuse accepted per-case execution/verification while using the newly declared count and bounded scheduling. Preserve partial rows on timeout.

Only after fresh depth-2 transfer is measured should a separate experiment remove scaffolding: choose call position, then multiple calls, then deeper nesting. Depth-3/depth-4 free composition and the full CASformer objective remain open.

## Bounded implementation and launch gates

Implementation scope is four small adapters and their tests, not a new model architecture:

1. Pure decision-site/correspondence extraction and read-only saved-checkpoint GPU diagnostic.
2. Pure public scaffold/catalog construction, compiler, exhaustive legal-tuple tests and split validator.
3. Existing-model scaffold rollout and hole-loss training adapter, with matched CUDA preflight.
4. Versioned sealing/native evaluation adapter and result rows.

First complete the charter read, freeze this implementation scope and actual dataset counts, then perform pure tests and a clean-checkout source/dependency check. A separate authorized CUDA diagnostic is next; it is not launched by this plan. Training follows only after diagnostic review and the already required launch process.

Parent-proposed reservations, not ledger mutations or current provider quotes:

- Saved-prefix diagnostic: at most **$4**, one approved non-T4 GPU instance, hard 3,600-second cap.
- Child-call candidate plus evaluation: at most **$7**, hard 7,200-second cap.
- Planning rate ceiling: $2.52/hour plus $1 ancillary allowance gives $3.52 and $6.04 respectively. Verify current AWS rate, capacity, exact job bounds and ledger before any reservation; reduce work or stop if the reservation cannot cover the registered job.
- Existing ledger observation: revision 11, $78 reserved, $322 unreserved, campaign cap $400. No new money is reserved here.

No automatic paid launch, deadline extension, core rewrite, guard removal, memory expansion, accepted-weight change or claim of learned capability follows this draft.
