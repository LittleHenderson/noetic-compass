# R repair path: read-only source and exported-record review

Review scope: source text and the AWS export's JSON only. No SQLite connection, tensor decoding, model execution, provider call, or accepted-source edit was performed by this review. **No repair attempt is claimed here.**

## Bound evidence

- Original qualification job: `cas-meta2-20260906155525-195f5ad8`.
- Original result ZIP: `39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f` (893,323 bytes).
- Failed member: `qualification/cases/case_00/candidate_03/native.db`; SHA256 `41e3d9636cc9ffc026a87ca4bae3901cbf58dcff3c17039229c742f8898f14b2` (1,523,712 bytes).
- [AWS inspection result ZIP](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_native_failure_inspection_v8_001/execution_001/lifecycle/cloud_artifacts.zip>): SHA256 `fe2a65efe0dc9119ffdc29cf5931e5e6b550774471747e4634dd53ce510862b3` (127,026 bytes), independently rehashed for this review.
- Its `inspection/export.json`: SHA256 `1e6f587b1f7f3a548e52eb2064edc57b49ad836409e56f02ba7af67769672565` (1,422,416 bytes).
- Exported source documents used for the producer/consumer chain were checked against their stored `payload_sha256`. This verifies the exported document bytes, not another native/SQLite replay.

## What actually happened

The first five native ticks accepted one Effect each. The sixth tick requested repair and published no Effect:

| Tick | CJT | Input came from | Actual label | Stored outcome |
| --- | --- | --- | --- | --- |
| 1 | A | Observation | L1 | ACCEPT |
| 2 | B | A | L3 | ACCEPT |
| 3 | C | B | L2 | ACCEPT |
| 4 | R | C | L1 | ACCEPT |
| 5 | C | R at tick 4 | L2 | ACCEPT |
| 6 | R | C at tick 5 | L0 | REPAIR / SEMANTIC_OFF_AXIS; expected L1 |

Thus the later `R → C → R` sequence is real producer/consumer linkage, not merely names in a proposed program.

At tick 6, R used Bias version 1. Its committed successor is version 2 with OPEN repair `repair-3295d0e50cc47ac2f23bb183`, exact subgoal `cause-6887f4b6a53020e465d7f15d`, eligible tick 7, budget 4 and consumed 1.

Custody detail: the exported `causes` table contains the six executed Causes, not the full unexecuted RPM_SUBGOAL. Its ID is bound by the repair frame. A copy-based diagnostic must reconstruct that Cause with the frozen `open_repair` function and the retained tick-6 Cause, candidate, verifier receipt and pre-tick R Bias, then require the same frame digest and subgoal ID. This is deterministic reconstruction to check, not a claim that an uncaptured Cause or caller stack was recovered.

**This is not a demonstrated readiness shortage.** The exported final R and C states have Desire, Wisdom and Power all `SUFFICIENT`, each score 1,000,000, and `unmet_prerequisites=[]`. Both are ACTIVE/STABLE. `repair.py:87` selects `first_unmet or WISDOM`; WISDOM is therefore the default axis here, not proof that the system discovered missing Wisdom.

## Where L1 came from, and the two separate gaps

1. **Authored expectation versus actual output.** `native.py:26` fixes R's expected label to L1 for every invocation. The original META-0 example authors L1 for its particular R repair call; it does not prove “R returns L1 for all inputs and histories.” The new curriculum explicitly calls these labels fixture expectations *if accepted*. Persistent recurrent Bias is reused and updated after accepted calls; it is not reset for each invocation. The later input also differs. This record does not isolate which factor caused L0.
2. **Missing wrapper continuation.** The generated single-RUN wrapper contains only R, with no `repair` or `resume_expected`. The accepted META-0 executor already knows how to suspend, call a declared repair procedure, return and resume. Without that declaration it raises `NATIVE_RESULT_NOT_RETURNABLE`. That explains why this wrapper stopped; it does not establish that a handler would cure the L0/L1 mismatch.

Changing the target to the observed L0, weakening the verifier, resetting Bias, or dropping R_CR would not demonstrate the requested L1 task. Preserve the refused qualification and its denominator.

## Smallest supported next actions, still conditional

1. **Separate repair-aware native diagnostic, with an honest boundary.** On an authorized AWS candidate copy of the exact failed image, attempt only the already supported reserved round trip: C processes the exact RPM_SUBGOAL at tick 7 with the predeclared C expectation L2; if accepted, R consumes that retained C Effect at tick 8, with the original repair ID and the intended expectation L1. C is the distinct bidirectional R↔C node supported by the frozen topology and repair eligibility rules. Both steps must independently ACCEPT, and R must close the original repair. If either fails, retain that failure. A database-copy diagnostic does **not** reconstruct the missing outer caller stack or prove a complete task return.
2. **Only after evidence supports that path, integrate a new candidate wrapper and audit.** Use the existing accepted compiler/executor repair fields, permit C as well as R within the caller's existing authority, and declare bounded multistep accounting and documentary checks. Keep the accepted runtime, verifier, source and weights unchanged. Retest all four candidate choices and the full task result under a separately frozen qualification contract; do not silently mark the old run qualified.

Why step 2 is not a one-line handler fix:

- `NativeBackend.execute` currently gives the META-0 kernel exactly one planned tick's budget, `max_depth=2`, and `max_steps=4`; it requires exactly one CHARGE and NATIVE event, and exactly one additional native trace.
- The accepted repair branch needs its rejected R tick, a repair C tick, and resumed R tick, with real charges and the exact waiting/return address.
- `native._stored` and `stored.verify_stored_composition` currently require one published Effect per native trace; the rejected repair-opening trace has none.
- The stored auditor replays the exact selected program and its native events. Extra repair ticks cannot be hidden, renamed as a single tick, omitted from costs, or inserted while claiming the old exact graph and 110-tick qualification schedule.
- The accepted runtime reserves the next two global ticks for the exact subgoal and resume; it permits one OPEN repair globally. A failed repair subgoal or failed resume is not an automatic retry or recursive repair success.

Running C in repair would transform the rejected R candidate's payload and, if accepted, supply a new input to resumed R. It is not a proven no-op, but there is no present evidence that it returns R to L1. The persistent R model weights remain fixed; merely adding control flow does not teach R the desired response.

## Frozen source identities and line references

All 12 files below were rehashed and matched the qualification source manifest for worker commit `b61b011c3d53ae49a1f7f988397df632e95e82a6`. Source ZIP SHA256: `d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3`; root manifest SHA256: `a19590941a53a7c3aa0a343501a7330ea5f89e56f10454ad82603eb4c6d0b69d`. This is a byte-identity statement, not a new execution test.

| File | Relevant lines | SHA256 |
| --- | --- | --- |
| [CAS_META_2_COMPOSITION/cas_meta2/native.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/native.py>) | 26; 185–226; 417–419; 507–542 | `16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512` |
| [CAS_META_2_COMPOSITION/cas_meta2/stored.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/stored.py>) | 219–221; 260–264; 297–311 | `b2d522c2387361fa979d69c6d5258927f61deacb108345581902e40d4246a435` |
| [CAS_META_2_COMPOSITION/cas_meta2/child_curriculum_v8.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/child_curriculum_v8.py>) | 1–5; 28–31; 73–74; 124–138 | `dc764d36754599b627c14a19876fdd57a30ca781e178f50e29e7ed232ba79c7d` |
| [CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py>) | 23–29; 85–142 | `0038db2ed122e7d1ccb312771e0ea14388ee8564d3ffaa9a9f6c7316c6eb1735` |
| [CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/executor.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/executor.py>) | 273–280; 313–349; 352–376 | `4570dec76d8f204c7fccb3d54a71b917b160da072322acb609fc8730ce4fa9df` |
| [CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/compiler.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/compiler.py>) | 223–234; 245–278 | `49f7f917e97b8748237034e4c920d7fcd21ae1d705ab2b73d14e47a69589eb78` |
| [CASFORMER_v0_3_META_LOGIC_WIP/programs/fixed_chain.json](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CASFORMER_v0_3_META_LOGIC_WIP/programs/fixed_chain.json>) | 1–76 | `c8f9207ae25c77b6d179118d460334cb3ba78676a0c35d64af6e05949c7b1687` |
| [CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py>) | 549–674; 737–795; 871–905; 937–975 | `5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187` |
| [CAS_CJT_TRANSFORMER_v0_2/cas_cjt/state.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/state.py>) | 452–559 | `5be617d5e3dc2f9590076ac07f1b0325ce9bf5465b7766315a3322f390b94240` |
| [CAS_CJT_TRANSFORMER_v0_2/cas_cjt/repair.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/repair.py>) | 64–87; 100–167; 199–260 | `49108e6d1bdd9d566a9243a409073544a798ea6c9277787f292e7376449e1a75` |
| [CAS_CJT_TRANSFORMER_v0_2/cas_cjt/verifier.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/verifier.py>) | 285–340 | `c1604059580a553e131233ecdbb5b1de8439edbba03865f7985a71b0dfdfb736` |
| [CAS_CJT_TRANSFORMER_v0_2/cas_cjt/control.py](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/control.py>) | 214–229; 261; 398–405 | `fee2b8386feb5ad8b27f95c916a7632d4e6d6fa5365091ec2d2ef3eeb9e46804` |

Conclusion: the independent verifier caught an actual authored-target mismatch and opened a real native repair. A repair-capable wrapper and a demonstrated successful repair are both missing from this particular task path. Learning remains gated until the full qualification is measured under a valid, explicitly declared contract.
