# A4 independent first report: training and retention

Date: 2026-09-22 local. Immutable first-round submission; add later challenges separately.

**The six jobs used the same repeated teaching order and a constant 0.003 learning rate. Helm 2.0 actually used gradient clipping, but its warmup/cosine option was inactive. Saved answers establish both early and late training losses, plus separate losses after the retention interference interval. The records do not isolate a training mechanism that caused the official failure.**

## Scope and independence

I examined Helm 1.0 at `af0970cfa6d54a85aeb16e5a99a84d791ace59c0` and Helm 2.0-experimental at `20208c923d41c24614504d4ecc2b289ecb66eda8`, each at seeds 20260917, 20260918, and 20260919. The branch began at `59b1dd57e57648ab68c1cc26fbae95a957c20cd3`. Only this `agents/A4/` subtree was written.

No peer report or new conclusion was read. Exposure was not perfectly blind: the common directive mentions prior claims about the message loop and matching head; the controlling AGENTS file mentions prior lost runs; original learner comments discuss previous instability and proposed fixes. Those narratives guided locations to inspect, not accepted causes. I did not read BRAIN_LINEAGE/AUDIT_PACK or peer analyses: the current, narrower independent-investigation directive supplied the source-bound evidence and superseded broader instructions to run audits or edit lineage.

All checks were local stdlib record/source work. No Torch import, model initialization, neural checkpoint deserialization, prediction, training, GPU, cloud, installation, or paid API occurred. Checkpoint assertions below are about saved metadata and historical replay records, not a fresh tensor reconstruction.

## Evidence and active settings

`READ_FINGERPRINTS.json` binds all 300 artifacts read by the main probe to the common manifest. `SOURCE_FINGERPRINTS.json` records six source ZIP checks and 24 member comparisons against each job's `loaded_sources.json` after-record. All matched. `SOURCE_EXCERPTS.md` gives original member line numbers and hashes. The source paths below refer to members of the respective saved ZIP, not newer working-tree code.

| Control | What actually ran | Evidence |
|---|---|---|
| Initialization | Fresh registered random build per seed after practice-checkpoint checks. This was not continuation from a Helm 1 checkpoint. Saved same-seed double builds matched; all six records report distinct core starts across seeds and phase A completed before model seeding. Same-seed core identities match across versions, while whole-container identities differ. | `model_identity.json`; Helm 2 `cncm/typed_pointer_worker.py:859-904`; initial checkpoint metadata |
| Optimizer | AdamW; learning rate 0.003, weight decay 0.01, betas [0.9, 0.999], epsilon 1e-8; foreach/fused false. Float32 learned parameters. | Config design; sidecars; Helm 2 `pointer_learner.py:1735-1786` |
| Rate schedule | All 4,458 Helm 2 main/interference rows say `CONSTANT_AS_HELM_1_0` and 0.003. Helm 1's constant rate is source/config evidence; its rows do not log per-step rates. | Per-update rows; Helm 2 learner `1774-1780`, `1811-1835`; Helm 1 optimizer construction |
| Dormant rate option | Warmup 0.05, cosine floor 0.10 exist in Helm 2 source. The worker supplies only max_updates/max_core_calls/max_wall_seconds. The learner's exact-key guard also rejects an additional planned_main_updates key before the option reads it. Thus simply supplying the documented optional key would not work in this source. | Helm 2 worker `868-871`; learner `1754-1758`, `1774-1780` |
| Clipping | Helm 1 has no clip step. Helm 2 clips the global gradient norm to 1.0 before AdamW; it bound 264, 187, 230 main updates for the three seeds. None of the later 16 interference updates clipped. The recorded squared norms are **before** clipping. | All update rows; Helm 2 learner `1994-2008` |
| Freezing | Encoder unchanged in all five inspected sidecars per job. No learned container parameter was frozen: 46 Helm 1 / 48 Helm 2 parameter tensors; every main row reports gradients for all of them. A gradient being present does not mean it was nonzero. | Checkpoint scope; row gradient names/counts; learner `1717-1743` |
| Teaching order | 10 passes, 147 updates/pass, eight records/update, one of each kind, 358 unique trained records. The identical record order repeats on every pass and across all six jobs. No per-pass shuffle. | 8,820 main update/batch pairs; contract `210-248`, `285-311` |
| Loss | Raw slot mean → field mean → task/batch mean. Each kind has one eighth of each main batch at the task-mean level. Alphabet-log normalization is reporting only. Valid correspondence alternatives are combined with logsumexp. | Shared `learner.py:197-235`; pointer learner `1936-1986`; task/field arithmetic independently checked |
| Rehearsal | All eight training kinds recur each main update. No dedicated held-answer preservation or distillation term was found in the actual loss/update path. Held-world records do not enter these batches. | Recorded IDs, field losses, source loss path |
| Stopping/selection | All jobs completed exactly 1,470 main updates. Final means the fixed last main update, not the best development checkpoint or early stopping. Limits were 1,486 in the main learner, 600,000 core calls and 12,300 seconds. | Worker `1041-1086`; sidecar cursors; completed reports |
| Retention interval | After final main checkpoint: 16 further updates, 128 presentations, 64 definition and 64 context tasks, drawn from trained records; other kinds have no direct rehearsal during this interval. `retained` is cursor 1,486, distinct from `final` cursor 1,470. | Worker `1097-1145`; interference batches/updates; metadata |
| Restoration | Saved reports show same-process initial/final/retained prediction reload checks and two independent branches from prelast cursor 1,469 to final cursor 1,470. Global work is 1,488 updates because it includes both replay steps. Replays did not replace the original final checkpoint. | `replay_report.json`; worker `1157-1227`; checkpoint sidecars |

Record-order SHA256 (A4 JSON serialization of one pass's record lists): `037a5d63b59807db0ee95f9c10c2f795aa6681cf42d7e96157654bc8e51896ef`.

All 8,916 inspected main/interference rows contain finite raw loss, normalized loss and squared gradient norm. The source rejects nonfinite loss, gradients and post-step parameters. This contradicts calling these six completed jobs NaN-invalid. It does not prove that all updates were well conditioned, or that clipping preserved answers. Maximum main pre-clip squared norms for Helm 2 were 643.9685041870807, 603.4755832525864 and 766.0041152541118.

## Recorded loss and answer changes

The following held-world figures cover **all 127 held records**, including repeated questions and records excluded by the original gate. They are diagnostics, not a reconstruction of that gate. In particular, Helm 1 seed 20260919 lost a held record while retaining its historical pass label. Do not equate these broader record counts with gate failures.

| Version / seed | Mean raw batch loss, pass 1 → 10 | Held records correct, initial → final | Initially correct held records lost | Retention panel correct, before → after | Retention lost / gained records |
|---|---|---|---:|---|---|
| Helm 1 / 20260917 | 1.0565827313400658 → 0.574949407235715 | 9 → 84 | 0 | 93 → 93 / 96 | 0 / 0 |
| Helm 1 / 20260918 | 0.9522530092298008 → 0.48907629777083644 | 2 → 88 | 0 | 93 → 93 / 96 | 0 / 0 |
| Helm 1 / 20260919 | 0.9506639284972855 → 0.5026688000841083 | 5 → 81 | 1 | 87 → 87 / 96 | 1 / 1 |
| Helm 2 / 20260917 | 0.7188403258114415 → 0.30109502960830614 | 8 → 103 | 1 | 86 → 78 / 96 | 10 / 2 |
| Helm 2 / 20260918 | 0.8676923648507024 → 0.21974338093901233 | 0 → 105 | 0 | 93 → 93 / 96 | 0 / 0 |
| Helm 2 / 20260919 | 0.7417036671312893 → 0.23138435698620688 | 18 → 99 | 5 | 84 → 82 / 96 | 2 / 0 |

The unchanged Helm 1 retention total in seed 20260919 hides a lost answer and a gained answer. Total accuracy alone is insufficient to establish answer preservation.

The saved chronology narrows the training-loss timing:

- Helm 2 seed 20260917: reach record `typed-input-9373a9e1fb69dda6ed107b85aa1a6b6cce6e286881a9390ad31ba80d27508c0d`, query `typed-query-404166e8b8180ddc5758d193239cd0f8a5f91804f2f87bc6141ab9f782157005`, is correct initially and wrong at every recorded pass from 1 onward. Its answer changes from VIA world-4090…/n3 to DIRECT. The loss occurs within the first 147 updates, before retention interference.
- Helm 2 seed 20260919: four records share query `typed-query-369885551a553d5fa430a4f0389a1e547fb4b7a6234e85d2c9aace042f4fd46f`. All are correct at passes 0,1,2,4,6,8 and wrong at 10: VIA world-28f61…/n3 becomes VIA world-28f61…/n1. The observed transition is within updates 1,177–1,470, before retention interference. Full IDs and scores are retained in `SAVED_RECORD_ANALYSIS.json`.
- The remaining seed-20260919 held loss is query `typed-query-5850f9113bccb701f9bc1cd326758889b77cd0cb3f0a443181b9e1105c3f9e94`, already wrong by pass 1 in both Helm 1 and Helm 2. It must not automatically be counted as an official failure; gate scope is a separate question.

The seed-20260919 late losses coexist with mean raw loss falling from 0.24555260797347003 at pass 9 to 0.23138435698620688 at pass 10. There is no monotonic implication from average training loss to preserved answers.

Loss contributions also differ greatly by kind. At pass 10, Helm 1 correspondence loss is about 2.24139 for all seeds; Helm 2's saved values are 0.00035597802116171806, 0.000034509670166742234 and 0.00026559490127628355. Analogy remains about 1.51–1.54. These are recorded task losses, not proof of generalized reasoning or attribution of gains to one component. Full per-kind/pass values are in the analysis JSON.

## Interpretation, alternative, and disproof

**Established:** the rate-schedule option did not run; clipping did run; the original schedule repeatedly mixes every task kind; fixed endpoint selection can retain a worse individual answer; losses occurred at multiple times; later definition/context-only updates changed previously correct parts/reach answers in two Helm 2 seeds. Freezing every answer head, missing a whole task kind from main batches, an active warmup schedule, NaN-invalid main logs, and retention interference occurring before the final main answer are contradicted by these records.

**Leading explanation, still unproved:** shared-parameter optimization changes decision rankings while reducing the aggregate objective. Equal task exposure is not an answer-preservation constraint. Constant-rate updates without an explicit retention term are a plausible contributor, especially to the separate interference result. This does not identify a particular parameter, rate value, head, or message path as the cause of the original gate failure.

**Strongest alternative:** the failing answers reflect information/decoder/target limitations or chance correctness of the random model, so a different optimization setting would not reliably preserve them. Different whole-container starts and several simultaneous Helm 2 changes prevent treating this version comparison as an isolated training-control experiment. Clipping alone is plainly insufficient for perfect retention in the recorded jobs; it is not thereby shown ineffective.

The optimization explanation would be weakened if matched continuations reproduce the same errors despite much smaller verified updates, or if source-bound non-neural analysis proves the needed answers indistinguishable to the whole model. Conversely, improved retention under one matched intervention would support that intervention only; it would not explain unrelated historical errors.

## Smallest distinguishing next test — NOT RUN

For the **separate retention loss**, use Helm 2 seed 20260917 `final.pt` plus its saved optimizer/RNG state, exact source `20208c923d41c24614504d4ecc2b289ecb66eda8`, exact 16 interference batches and 96 retention records. Run three matched branches: unchanged 0.003 replay, 0.0003 rate, and zero-update evaluation control. Verify the unchanged branch reproduces the saved answers before interpreting the modified branch. Freeze decoding/data/weights at the start; change only rate, record answers and scores after each update. Prediction under update-size sensitivity: the lower-rate branch loses fewer of the ten previously correct records. Prediction under rate-insensitive structural/decoder limitation: the loss persists, or the matched replay cannot even reproduce the historical path. The zero-update branch should preserve all starting answers.

Proposed bound: two 16-update branches and three fixed 96-record evaluations plus per-step diagnostic scoring of the ten lost records; one GPU, no automatic retry, hard 30-minute/one-instance limit, fail on nonfinite values or replay mismatch. No launch or spend is authorized by this proposal; resource identity/cost must be fixed before any future run. This test concerns the later retention interval only. Explaining the original early/late main-training losses needs separately matched continuations or training from the initial checkpoint; there is no saved pass-8 tensor checkpoint in the frozen subject manifest to justify pretending a cheap pass-8 replay already exists.

Unknowns: per-example causal gradient interference; correct-answer margins between saved evaluation points; sensitivity to rate/rehearsal/order independently; whole-model representability; and whether improvements persist on fresh questions. No claim about any of these is licensed by lower loss or source comments.

## Execution accounting

The main probe ran twice and passed in 19.572126699989894 and 21.335677700000815 seconds using Python 3.14.0 at `C:/Python314/python.exe -B`, with UTF-8 and bytecode disabled. The second execution added explicit checks that every main batch has all eight kinds and saved score totals equal row totals. Three check functions × six subject cases = 18 distinct subject/function cases, executed twice (36 case executions); these are not 8,916 independent experiments. Each execution covered the same 8,820 main rows, 96 interference rows, 42 held-panel snapshots and 12 retention snapshots. Source identity checks covered six ZIPs and 24 members. Historical replay steps remain historical and are not counted as new executions. No semantic grader was rerun: saved grader rows were compared. Agent/tool dollar cost is unavailable; this report does not claim free work. Commands, inspection failures and output truncations are recorded in `COMMAND_LOG.md`.
