# Larger-question route and checkpoint protocol

Status: **NOT_READY — preparation only; no new launch is authorized.** This protocol describes the evidence needed before a new main comparison. It does not turn the existing source review into a device result. Q4 remains separate.

The exact source and public receipt pins are in `EXECUTION_MANIFEST.json`. The source snapshots are integration `197caa322d20ae6830928b20c5b16933e93cd00d`, builder `cc68d8b326ea772a7d93871e843a9bbacb4cee0e`, and observed launch records `1fcc15e5fe0183da4572741e4efa675698640ab5`. The observed smoke uses source `3df31d965bb2eabb168ae7efbf03300a1a1144d7`; its package is **not** the final main-training package. No checkpoint was deserialized, model or test executed, package built, protected file opened, or cloud job launched during this preparation.

## What the source already supports

Both arms can use one inference adapter: `research/CAS_META_2_COMPOSITION/eval_paths/larger_question_learner.py::predict_packet`. It accepts a bare pointer container. Historical OFF checkpoints load strictly into an OFF container; fresh repaired checkpoints require an ON container with the five added analogy-head tensors. The caller must put the model in evaluation mode. This entry point requires CUDA and uses `torch.no_grad()`.

The packet follows the same sequence in both arms: route selection, slot compilation, public input reading, `GraphForward`, head logits, decoding and answer assembly. Grading is a separate step. Neither the checker nor reference answers enter inference.

The route is determined from **every world in the packet's bank**:

| Packet scope | Slot compiler and grader | Required interpretation |
|---|---|---|
| All worlds have at most four nodes | Frozen `slots.py` and `checker.py` | Historical route remains unchanged. |
| Largest world has five or six nodes; all degrees are at most four | Accepted `slots_v2.py` and `checker_v2.py` | Same packets, answer options and scoring contract for both arms. |
| Any world has at least seven nodes, or any node degree exceeds four | Named refusal before model forward | Unsupported input, not a learned wrong answer. |
| Accepted checker refuses its target bounds | Named checker scope refusal | Retain the refusal and report the denominator; do not quietly count it as a model error or drop it. |

This adapter is outside the training input inventory. It does not teach either arm new examples. Its twelve protected source hashes all match the observed smoke source `3df31d96`; this was checked by reading and hashing Git blobs. That source match does not establish GPU acceptance.

## Demonstration required before the main comparison

The existing script is `eval_paths/t4_larger_question_checks.py`. Its source review at the builder snapshot is **CHANGES_REQUIRED**, and the review explicitly records all four device checks as **NOT RUN**. The main defect is an estimated 3,600–5,000 seconds of work against a 3,600-second limit, with the subclass check last and no partial record for an interrupted check. Treat the estimate as a preparation concern, not a measured timeout.

Before executing that prerequisite, revise and review its schedule, bounded wall time, checkpointed progress and receipt aggregation. A partial check must remain INCOMPLETE, never PASS. Any proposed extra AWS allowance belongs in the complete launch request; this document grants none.

The public fixture file is already pinned: 41 fixtures, consisting of 37 gradable questions and four expected refusals. Its SHA-256 is `7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3`. They cover five- and six-node questions, the eight kinds, both reach rules, matching and nonmatching pairs, and named scope refusals. These are public plumbing fixtures. Their shapes remain excluded from HSET-2 TEST under amendment A1; fixture accuracy cannot support a held-out learning claim.

The acceptance receipt must report all four checks, with exact source, fixture, checkpoint and environment identities:

1. **Old-packet preservation.** On all six historical checkpoints (initial and final for each of three seeds), compare all 564 course packets between the old steps and the adapter. Require equal route, slot plan, float32 logit bits, scores, decisions and answers: 3,384 packet comparisons. Retain per-checkpoint digests.
2. **Larger questions through both layouts.** Send the same 37 gradable fixtures through the three historical OFF finals, a fresh OFF container and a fresh ON container. Require read → forward → decode → grade without an interface or scope error; record the route, slot-plan identity, grader receipt identity, output schema and named errors. Do not report this as an accuracy experiment. The accepted slot plan and grader must be common to both arms.
3. **Refusal before inference.** For fresh OFF and ON containers, all four refusal fixtures must produce the declared reason with zero calls to `GraphForward`.
4. **Full learner route.** The original learner and inference subclass, constructed from the same seed, must have equal starting state and predictions on all 564 course questions. The subclass must process all 37 gradable fixtures, refuse all four out-of-scope fixtures without changing counters, and refuse both training entry points. The original learner's six-node correspondence refusal is expected. The existing check uses ON; it must not be presented as a full-learner OFF check.

The study evaluation uses the common **bare-container** entry point from check 2. If the final study reader instead selects the subclass, extend its acceptance to both arms before approval. Every final trained checkpoint must additionally pass the same public route/schema checks before its HSET-2 predictions are accepted. This later check is an evaluation admission check, not permission to tune the model after TEST.

The final evaluation package must enforce source pins at its own entry point, including grading-only invocations. Import-time verification in the learner alone is insufficient when a caller can bypass that import.

## Training and starting-state contract

The retained option C has **four new main jobs**: three repaired runs plus one fresh unchanged reproduction run at seed `20260917`. It reuses the historical unchanged controls at seeds `20260918` and `20260919`. A successful reproduction supports only seed `20260917` and that setup; it does not prove either reused control would reproduce. Option B is the stronger fresh-control comparison. Its conditional fallback adds fresh unchanged runs at seeds `20260918` and `20260919`, for six main jobs maximum, under the valid-mismatch rule in `REPRODUCTION_POLICY.md` and only within a later approved job and spending envelope. Invalid evidence stops admission; it does not authorize fallback.

Use the same course, tokenizer, schedule, optimizer settings and environment for every fresh run. The historical package and receipt pins remain references. A fresh OFF admission and repaired main package still need to be built and frozen. Preserve the historical-control limitation even if every C admission requirement passes.

The course SHA-256 is `cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987`. The course only teaches worlds of at most four nodes. HSET-2 therefore measures transfer to larger questions. It does not evaluate a new six-node lesson course.

Pin the initialization recipe, expected state references and initialization prerequisite receipt before launch. Each fresh main job must capture its actual `initial.pt` file hash and independently recomputed learned-state, encoder, optimizer and RNG identities **before its first optimizer update**. For each seed, all 48 shared tensors must equal the corresponding historical initial tensors exactly. Compare fresh OFF and repaired ON directly where a fresh control exists: seed `20260917` in C and all three seeds only if B runs. The five ON-only tensors use head seed `20260923` and must equal the predeclared head-state reference and one another across repaired runs. Seeding declarations and the historical three-core-tensor identity are insufficient proof. Any mismatch follows the separately frozen identity policy; it cannot be relaxed after inspection.

The JSON manifest contains all six historical checkpoint file hashes and the state identities from their public metadata receipts. It separately lists four base-C future initial records as `PENDING_RUNTIME` and two conditional fallback records as `PENDING_RUNTIME_IF_FALLBACK`. Future file hashes are normally unknown before model construction. Their absence alone does not block launch; missing frozen source/package/environment, expected-state references, acceptance rules or prerequisite receipts do. Capture and validate the actual initial state before the first optimizer update, then append immutable receipts. Never copy historical identities into a field presented as freshly measured evidence.

## Why the allowance is 1,488 updates

Both arms use ten passes of 147 updates, so the primary model receives **1,470 main updates**. `final.pt` is saved immediately afterward, before interference. It is the sole proposed primary HSET-2 endpoint.

The worker then performs 16 interference updates on trained records and saves `retained.pt`. Two separate replay branches each restore `prelast.pt` and repeat the final main update to compare with `final.pt`. Thus the job accounts for **1,470 + 16 + 2 = 1,488 optimizer updates**. The two replay steps are not accumulated into the primary final model. The main-plus-interference trajectory itself reaches 1,486 updates.

`retained.pt`, replay results and intermediate checkpoints are diagnostics with their own labels. None can replace `final.pt` because it scored better on TEST.

Source evidence: `cncm/typed_pointer_worker.py:1079` saves the main final; lines 1115–1142 handle interference; lines 1203–1228 handle replay; lines 1816–1828 account for the total. `practice_contract.py:57–60` declares the extra update counts.

## What the eighteen checks mean

Preregistration amendment A5 names six repaired checkpoints per seed:

| Checkpoint | Main updates |
|---|---:|
| `pass_01.pt` | 147 |
| `evidence/main_checkpoint_0294.pt` | 294 |
| `evidence/main_checkpoint_0588.pt` | 588 |
| `evidence/main_checkpoint_0882.pt` | 882 |
| `evidence/main_checkpoint_1176.pt` | 1,176 |
| `final.pt` | 1,470 |

Six checkpoints across three repaired seeds make **18 mechanism checks**. They are not 18 training jobs or 18 opportunities to select a TEST winner. Preserve every pass, failure and invalid reading. The historical A5 labels and evidence remain intact.

The v0.2 probe has an unresolved normalization flaw: changing one candidate changes the mean and standard deviation used to score the other candidates. Apparent bystander coupling can therefore occur even when their raw scores stay fixed. A corrected, preregistered admission rule and its independent-candidate control must be frozen before using this probe for a new mechanism claim. Report the old v0.2 reading separately; do not rewrite it as if the corrected rule had always applied. A failed mechanism check must not hide non-analogy regression evidence.

These 18 mechanism checks are also distinct from the worker's earlier practice-checkpoint restoration checks, which compare the registered core sub-block before the pointer learner is seeded.

## Remaining evidence before final launch approval

- Actual HSET-2 informative-case counts and feasibility receipt, under the final threshold, grouping and multiple-claim rules. No actual HSET-2 build/count receipt was found in the bounded reviewed trees; the design's throwaway-salt numbers are not substitutes. Preserve A1, protected splits and all NOT_TESTABLE cells.
- Reviewed and passing AWS route checks above, including a complete receipt rather than selected successful stages.
- Corrected probe admission and source pins.
- Main OFF and ON package identities, admission records, final evaluation reader and package, full resolved dependency/environment lock and bounded job request.
- A complete spending and cleanup request, including four main C jobs, two conditional fresh-control fallback jobs, prerequisites, post-training evaluation, retained storage and explicit maximum charges. The proposed total envelope has two already-booked smoke attempts, one T4 public route/reader/probe prerequisite, one CPU HSET build, four C main jobs and one G7 readout job: **nine attempts in total, seven future jobs**. B fallback adds two jobs: **eleven attempts maximum, nine future jobs**. This count is a proposed envelope; runtime and cost feasibility still need proof. The readout covers eighteen repaired mechanism probes, three control finals plus three repaired finals, and H1/H2. The observed smoke's result is not inferred from its admission record.

Until these exist, the JSON remains **NOT_READY**, `launch_enabled` remains false, and no main comparison should be presented as ready for final approval.
