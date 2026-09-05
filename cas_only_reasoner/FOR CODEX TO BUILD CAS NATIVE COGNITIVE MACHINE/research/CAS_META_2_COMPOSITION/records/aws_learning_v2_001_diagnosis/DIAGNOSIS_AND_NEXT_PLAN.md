# Learning-v2: saved-data diagnosis and proposed next build

## Bottom line and evidence boundary

The completed packet reports CAS 0/72, generic 0/72 and rule 72/72 task successes.
The learned models show a smaller, real validation improvement, but have not
learned reliable nested-program synthesis. The selected CAS checkpoint generated
13/48 exact validation programs and bindings; the generic checkpoint generated
14/48. Both selected checkpoints generated **0/16 depth-3 validation programs**.

These are post-completion checks of saved data, not a successful release audit.
The outer inspector currently reports `CAS_META_2_V2_PACKET_EVIDENCE_MISMATCH`
because of `gpu_preflight_v2:V2_PREFLIGHT_MEMORY_CLEANUP_UNCONFIRMED`. It verified
archive safety and included bytes, but did not accept the completed-run evidence.
The stored semantic auditor therefore stopped at `SUCCESSFUL_FULL_INSPECTION_REQUIRED`
and reports `CAS_META_2_V2_STORED_PACKET_AUDIT_REJECTED`. Its failure occurs before
semantic replay; a false unchanged-files flag there is not evidence that this
diagnosis changed extracted files. This diagnosis reads the original ZIP only.

The preflight saved 68,157,440 allocated CUDA bytes after cleanup, versus 0 before,
and 96,468,992 reserved bytes after cleanup. Its own PASSED label does not close
that gate. Do not weaken the gate or call this packet fully verified.

## Exact bindings

- Frozen experiment source: `410bce98307a5644db51928459b73391c7066b72`.
- Job: `cas-meta2-20260905214620-cfdbb893`.
- Packet SHA-256: `0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93`.
- Original predictions SHA-256: `f606f38ef76595cde2c044e23b0f9fb84c4c9e16032c0b1b76111cfad14c891f`.
- Stored private test SHA-256: `c0e8f2c7a6562f031810bafdfe22e36131eb30a336ec3fc3923c44bd2c0d5cb3`.
- Outer inspection receipt SHA-256: `4fb60dc51248b2c75dbd2bf2c0f278e95fc29c7612b792e6b7e82a79936fd2a9`.
- Full member index SHA-256: `fa95375d180d645dc829bd558cd3672e7bed77627bae9a112de161252a39fc0e`.
- Stored-audit receipt SHA-256: `4a39e8183714f9fd7de914aa4803e58bff6038593dd6c73f41c7f363faff83e0`.
- Final diagnostic receipt SHA-256: `57c97c6bedaa55cc61610bf1854d6490ee15345143b9c0dd081e426e77f21f73`.

`diagnostic_receipt_final.json` contains hashes and byte counts for all 51 saved
members read by the final script, their canonical index digest, the script hash,
the pure codec hash, and the two external failed-gate receipt hashes. It checks
the predictions seal, all stored public-input bindings, and exact agreement
between sealed actions and the evaluation record before comparing outputs to
stored targets. The earlier `diagnostic_receipt.json` and
`diagnostic_receipt_bound.json` are retained intermediate diagnostics; the final
receipt is the current one.

No checkpoint was loaded, no model was run, no AWS call was made, no fresh
holdout was constructed, and no experiment behavior was edited. Ten synthetic
pure-data unit tests passed. They test this diagnostic's comparisons, not model
capability or native execution.

## What the records actually show

| Saved result | CAS | Generic |
| --- | ---: | ---: |
| Selected epoch | 40 | 60 |
| Exact free-generated validation action | 13/48 | 14/48 |
| Depth 1 validation | 10/16 | 12/16 |
| Depth 2 validation | 3/16 | 2/16 |
| Depth 3 validation | 0/16 | 0/16 |
| Teacher-forced validation token accuracy | 95.62% | 95.81% |
| Test decoded by codec | 17/72 | 19/72 |
| Test admitted and executed | 3/72 | 7/72 |
| Recorded native test task success | 0/72 | 0/72 |

The initial models generated no exact validation actions. At the saved generation
checkpoints, CAS never produced a correct depth-3 validation program. Generic
produced one at epoch 90, which was not the selected checkpoint. This is not
just an unexpectedly hard depth-4 test: depth-3 validation already exposed the
missing skill, and both selected models also failed all 24 same-depth test cases.

The test decode rejection reasons are:

| First reported reason | CAS | Generic |
| --- | ---: | ---: |
| Duplicate procedure declaration | 38 | 31 |
| Missing called procedure | 6 | 10 |
| Call cycle | 8 | 6 |
| Noncanonical definition order | 2 | 0 |
| Other syntax/unbound-reference errors | 1 | 6 |
| Decoded action | 17 | 19 |

Of those decoded actions, 14 CAS and 12 generic programs were then rejected
because they contained unreachable procedures. Every admitted program was wrong;
they changed operation choices, data references, step counts or returns. For
example, admitted generic case 7 changed a child C operation into B, its input
reference, and its caller's final return from the last child result to an earlier
B result. Its syntax was valid; a syntax mask alone would not correct that.

All three admitted CAS cases are the three members of one matched triplet, not
three independent graph successes. None is task-correct.

Both trained arms emitted the correct initial observation-binding token on
72/72 test problems. This is a **diagnostic token comparison**, not replacement
of the official task-binding score: the official verifier rejects incomplete
actions and reports only 3/72 CAS and 7/72 generic binding successes.

The earliest differing token is usually already a substantive program choice:
CAS first differs at the RUN target on 22 cases, an input reference on 14, the
step kind on 10, a call target on 6, and the final return value on 2. Generic's
corresponding counts are 27, 16, 11, 1 and 3. Some remaining first errors are
missing/extra steps at a return boundary or incorrect procedure names. This is
not solely a late missing delimiter. Median exact prefixes are 39 CAS and 38
generic tokens; target lengths are 83–111, well inside the 256-token bound.

Training continued for all 100 epochs. CAS training token loss fell from 2.55 to
0.0116; generic from 2.56 to 0.0093. After the selected checkpoints, validation
loss rose from 0.1147 to 0.2366 for CAS and 0.1456 to 0.2256 for generic. That is
consistent with increasing training fit without better generalization. There
are no saved free-generated *training-split* outputs to establish whether full
training programs could be reproduced without teacher forcing.

CAS has 175,595 active parameters and generic 175,635: a difference of 40,
approximately 0.0228%. Both received 4,800 optimizer steps. Saved training-step
time is 632.97 seconds CAS and 84.75 seconds generic; shared training/validation
wall time is 881.96 seconds. Full campaign time is 2,637.67 seconds. Parameter
matching is not compute matching, and this result establishes no CAS advantage.

## Proposed next build — not yet implemented or approved to launch

Keep the full goal: generate a new nested program and bindings from the problem,
then run the unchanged native executor and check all outputs and dependencies.
Do not replace generation with choosing a fixed program, flatten CALLs, relax
correctness, or use the rule answer when the model fails.

1. **Build a pure incremental grammar state first.** It tracks generated
   declarations, canonical ordering, local available variables, pending calls,
   call edges, scope, and fixed length limits. Its mask uses only the generated
   prefix and published IR rules—not task targets, expected dependencies,
   private labels or rule-parser output. Dead ends remain counted failures.
   Every old admitted program must round-trip unchanged. Invalid/mutated cases
   must still fail, including valid syntax with wrong semantic choices. This
   supplies structure, not the correct answer.

2. **Add learned symbol/reference copying.** Keep the full public problem and
   lossless tokenizer. Give the same autoregressive decoder in CAS and generic
   models a learned pointer over exact public symbol occurrences (`p#`, `v#`,
   `arg`, CJT names), aggregating identical spellings. The model still decides
   which operation, callee, input and return to emit. A lexical span inventory
   may locate names; it must not parse the task into the answer. The fixed output
   vocabulary remains available for structural decisions. This directly targets
   the observed name/reference errors while preserving arbitrary composition.

3. **Weight meaningful decisions, not just punctuation.** Predeclare a bounded
   3:1 loss weight for operation/callee/reference/return choices versus structural
   tokens, with ordinary next-token supervision. Keep all weights fixed before
   fresh holdouts exist. Report per-role accuracy and free-generated programs;
   do not interpret high token accuracy as task success. This ratio is a proposed
   design choice, not a proven optimum or a value fitted to private answers.

4. **Use all four neural arms under the same rules.** CAS trained/untrained and
   generic trained/untrained get the identical grammar, pointer architecture,
   public information and decoding constraints. Keep the same rule arm solely
   as a separately reported control. Match active parameters within 1%, share
   common initial weights, and check real task-loss gradients. If a grammar-only
   ablation is affordable, evaluate it on development data first; never present
   fewer syntax rejections as evidence of learned semantic composition.

5. **Select checkpoints using depth-aware free generation.** Proposed ranking:
   maximize the worst depth-stratum exact-action rate, then the macro-average
   rate, then joint correctness, then lower validation loss with an early tie
   break. Save every generated validation action and per-depth/role results.
   Also save a fixed training-only free-generation probe so future diagnosis can
   distinguish failure to fit full programs from failure to generalize.

6. **Make a fresh, larger training curriculum without making evaluation easier.**
   Proposed cap: 3,072 unique training graphs (1,024 each at depths 1–3), 96
   validation tasks (32 each), and the same 72-test paired design: 24 same-depth,
   24 wording-shift, 24 nonempty depth-4 calls. Keep topology A→B→C, real work in
   every frame, earlier-reference reuse, exact output/dependency checks, the
   existing IR/codec, and limits of 15 native RUNs/256 action tokens/1,024 input
   tokens. Verify graph capacity rather than silently lowering counts. Use a
   new preregistered seed and exclude every graph exposed in the old experiments
   and this diagnosis. Keep all fresh private labels sealed until predictions.

7. **Bound the next run before launch.** Start from d=64, 2 encoder layers,
   batch 16, at most 60 epochs: 11,520 updates per trained arm at 3,072 examples.
   That is 2.4 times this run's update count. The old per-step measurements give
   only a rough lower-order planning estimate; pointer and grammar overhead must
   be measured in a separate AWS smoke. Keep a 6,600-second full-job deadline,
   reserve evaluation time, save partial checkpoints/receipts on timeout, and
   recheck worst-length GPU allocation and *actual* post-cleanup allocation.
   Use the approved non-T4 AWS GPU and a root-verified reservation within the
   remaining shared $400 cap; this proposal authorizes no spend.

The pure grammar is the safe first implementation step while the separate
memory experiment proceeds. Neural changes and a new paid launch require root
review. Success still means correct new programs executed through the existing
machine, not merely more syntactically accepted outputs.
