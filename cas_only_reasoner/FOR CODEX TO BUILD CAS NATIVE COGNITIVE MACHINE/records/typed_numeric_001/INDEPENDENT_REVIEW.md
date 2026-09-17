# Independent source review: typed numerical candidate

Status: **SOURCE_REVIEW_COMPLETE; NUMERICAL_ACCEPTANCE_OPEN**.

The bounded review found one concrete construction defect in a draft learner: the registered merge matrix was required to have the wrong shape. The owner corrected it before any numerical run. No remaining material source-level blocker was found in the inspected components. This is not a CUDA acceptance result, a complete executable worker, a launch approval, or evidence of improved learning.

## Scope and authorship

Reviewer: `/root/cube_bridge_review`. The six new runtime modules below were authored by other agents: root owns the source loader and worker contract; `/root/viewer_validation` owns binding and encoder; `/root/cube_bridge_build` owns learner and loss plan. The reviewer made no changes to them or their tests. The reviewer did author the earlier frozen semantic checker and tokenizer tests, so this review is not an independent reimplementation or independent validation of all inherited semantics.

This review used source reads, standard-library JSON/hash inspection of the retained public course and tokenizer, and text extraction from a pinned wheel. It did not import or execute project numerical modules, tensors, a model, providers, or the wheel. It did not read retained private target files or construct main targets. No tests were rerun by this reviewer. Owner-reported narrow test passes are separate evidence; the root's guarded combined validation receipt must supply the final test closure.

## Exact inspected sources

Paths are relative to the inner CNCM worktree. These exact bytes were reread immediately before this record was written.

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `cncm/typed_source_attestation.py` | 5781 | `2b5758c9d0cae9a42c9566d2a529619ff00c6ba0e7b9918f251de58507874225` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/worker_contract.py` | 9765 | `02b0a56975bddc93560a1f3f4086c9c4eb3f914f7b912b2b7be24e0b441765f2` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/binding.py` | 11165 | `5db99005d6df1b26988b6cb9ed78e57d020bafb78647626d826cae01add572dc` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/encoder.py` | 15266 | `a5dcc50a4cfde6fed16f952b40bb98f2e87d24f3d40e117f8ef96507c57434ef` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/loss_plan.py` | 10441 | `df950e3dadd86de136c5f6fc5a2d4dcfdc033550ee92061a9f073e3b17c722ce` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/learner.py` | 26674 | `9bcbb44e5fc104aa9204edcfdc8c203ecdce55e48c79211182d5b988b1cc635f` |

## Source loading and material admission

- `typed_source_attestation.py:37–118` compiles manifest-verified source bytes directly with `dont_inherit=True, optimize=0`. It refuses pre-existing owned imports, reloads, missing/ambiguous source membership, unsafe manifest paths, and source changes. Its snapshot joins actual loaded module objects, loader/spec origins, manifest rows and current source bytes. It does not load owned `.pyc` files.
- This remains a component. A caller must independently pin the standalone bootstrap and manifest, install it before any `cncm`/`cas_meta2` import in a fresh process, use an import-and-call entrypoint, and retain the resulting snapshots. The custom loader supplies `exec_module`, not `get_code` for `runpy.run_module`. Wheel origin and loaded vendor source checks remain separate. These hashes establish byte consistency under the process boundary, not authenticity of a host or operating system.
- `worker_contract.py:68–130` pins the actual accepted course and tokenizer, verifies the exact ALT schedule, and projects learner packets through `course.model_packet`. The full course archive contains audit lineage; it must never be passed wholesale to the learner. `validate_course` is deliberately excluded from this public projection path because it invokes semantic checking.
- Independently read course: `records/typed_course_001/checks_002/public_course.json`, 4,165,195 bytes, SHA-256 `cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987`. It fits the 4 MiB member cap by 29,109 bytes. Its 160 flattened batches exactly equal its 1,152 presentation rows and cover 564 unique registry records. Presentation kind counts are definition 80, context 80, analogy 80, correspondence 208, parts 213, reach 315, edge account 80, role set 96.
- Independently read tokenizer: `records/typed_interface_001/checks_002/training_tokenizer.json`, 447,140 bytes, SHA-256 `bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c`. It declares 564 training frame digests and a 32,768-token cap. All five embedded tokenizer/frame source file byte-length/hash pins match current files. Its fit-scope statement remains a runner-custody claim; a tokenizer cannot independently prove that a caller never supplied evaluation material.
- The exact AdamW declaration is learning rate 0.003, weight decay 0.01, betas [0.9, 0.999], epsilon 1e-8, `foreach=False`, `fused=False`. The new end-to-end worker, bootstrap invocation, launcher, committed package and live admission path are still pending. `launch_enabled=False` remains in this component's design.

## Concrete defect found and corrected

The draft learner required all three matrices to be (64,64), which would reject the actual registered operation. Reading the pinned wheel's `cas_cjt/neural.py:115–126` shows that `_DecomposeTransform` constructs left/right as d-to-d and merge as 2d-to-d.

The held `learner.py:25–26,84–86` now requires `left.weight=(64,64)`, `right.weight=(64,64)`, and `merge.weight=(64,128)`: 16,384 trainable scalar weights in total. The owner added a pure AST regression against the exact wheel source, without importing it. This finding came from source inspection, not a failed GPU run.

Wheel: `research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/cas_neural_cjt-0.2.0-py3-none-any.whl`, SHA-256 `6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9`. The extracted `cas_cjt/neural.py` source pin in the regression is `03521d2b17311680fd91cde7076e4bf5b38393f0d6db115d47be20f63413fc96`.

## Encoder, inference and correction boundaries

- `binding.py:136–172` requires each row's decoded tokens to equal its exact frame fragment, includes LF separators and START/END markers, and requires the flattened rows to equal the original full sequence. Scope, ordinal and position are inside each signed-permutation domain. There is no truth-based pruning of bank worlds, graph edges, roles or correspondence candidates. Distinct recipes do not prove collision-free floating-point representations.
- `encoder.py` separates token, readout and public field-query domains; checks the role allocation bound before map expansion; retains bounded caches tied to exact packet/plan/tokenizer/profile identities; returns clones of cached vectors; and validates actual frozen row bytes at full verification boundaries. Fresh construction validates the pure expected identity before touching caller torch. Normalization refuses zero or nonfinite norms. Restore validates caller-pinned identity, exact CPU row metadata/bytes and the current tokenizer/profile before moving rows to the requested CUDA device.
- `learner.py:123–194` predicts only from public packets and fixed slot plans, calls the inherited recurrent loop with an identity cast to retain autograd, and uses fresh state per slot. There is no target argument to `predict`, private loss import on that method's path, best-depth selection, or semantic answer repair.
- `learner.py:238–288` checks the durable batch file against exact retained public bytes and the caller SHA before iterating private target objects. It checks that model bytes have not changed since staging. The private checker independently reconstructs supplied targets in `loss_plan.compile_loss_plan`; it does not accept a merely resealed assertion as target authority. This sequencing constrains these APIs; it does not prove that no other host code accessed targets earlier. The worker must derive main targets only after its exact prediction seal.
- The loss uses raw field means, task means and batch means for gradients. Alphabet-size normalization is reporting only. Membership fields include positive and negative slots. Correspondence is one normalized hierarchical whole-candidate valid-set loss over all syntactic bijections plus NO_MATCH, not independent mapping marginals. Ambiguous role [5,6] remains one exact multi-hot set, not a choice of singleton labels. Forced singleton fields are counted separately and have zero loss.

## Checkpoint and budget limits

`learner.py:295–364` exports model, AdamW, frozen encoder, Python/CPU/CUDA RNG state, named parameter order, run identity, counters and cursor. Restore requires a caller file hash, uses `weights_only=True` on CPU, validates typed tensor-byte identities, loads model state strictly, checks restored optimizer values and restores RNG. This is a source-level contract for same-process reconstruction. No checkpoint has been numerically restored under this candidate, and fresh-process restart remains unproved.

The inherited `graph_teaching/real_framework.py:59–83` accepts a `seed` argument but does not seed torch. The pending worker must explicitly seed torch and relevant CUDA generators before fresh framework construction and retain the resulting initial/RNG identities. Merely passing `seed=20260916` does not establish deterministic initialization.

The admitted main schedule declares 160 updates and 1,152 presentations. Two separate validation replay branches may perform one update each, for a global cap of 162. Restored learners inherit historical counters, so the worker must count replay **deltas**, not sum their lifetime counters. Additional exposures, forward calls, backward calls and time must remain separate from the main course.

Derived planning arithmetic: 2,598 registry slots × depth 8 × initial/final prediction = 41,568 core calls; plus 17,178 main training calls = **58,746 base core calls**, before reload, separation, cache and replay checks. These are not observed GPU counts. The source review does not prove completion within the declared 1,800-second worker limit or the planned $7 reservation.

Full frozen-row verification transfers and hashes about 1 MiB per packet; direct per-slot cache checks can re-encode a full roughly 27,000-token packet repeatedly. Row permutation construction, source/profile checks, semantic correction, backward work, checkpoint I/O and validation also cost time. The worker must measure this overhead and fail honestly on incomplete coverage, without reducing the full course or silently skipping checks.

## Gates still open

1. Exact committed source/package admission, standalone bootstrap invocation, loaded project and wheel attestation, and an executable end-to-end worker/launcher.
2. Actual CUDA construction, finite/nonzero row and packet norms, public scope-change separation, full-coverage cache/direct equality and exact frozen-row preservation.
3. Scalar/tensor loss agreement, finite gradients, permitted parameter changes, all 160 committed main updates and measured work/exposure counters.
4. Caller-pinned initial/final checkpoints, numerical restoration and next-step replay parity with the two replay deltas charged separately.
5. Durable prediction seals, private scoring joins, complete artifact delivery and truthful failure retention.
6. Any authorized cloud job's fresh pricing/budget admission, bounded lifecycle and independently observed current-job cleanup. No provider action occurred in this review.

This candidate remains an exposed-training-course engineering acceptance design. It does not establish held-out transfer, retention, learning-speed advantage, multiseed evidence, ordinary-DAG superiority, or resolution of the earlier negative 0/3 result.
