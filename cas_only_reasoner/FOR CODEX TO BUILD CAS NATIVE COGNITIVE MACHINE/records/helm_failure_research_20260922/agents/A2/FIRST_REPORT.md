# A2 independent first report — structure and information flow

Date: 2026-09-22. Immutable first-round submission. Follow-ups must be separate files.

The two studied versions have different local message paths, but both have a source-insensitive analogy scorer. Helm1 also gives every source node the same correspondence scores. Its actual decoder nevertheless selects complete bijections. These are source/record findings, not an explanation of the exact Helm2 gate losses.

## Question, subjects and independence

Question: What information enters the studied Helm versions, what reaches their answer components, and can differing required answers become indistinguishable along those paths?

- Helm1 training source: `af0970cfa6d54a85aeb16e5a99a84d791ace59c0`.
- Helm2 studied source: `20208c923d41c24614504d4ecc2b289ecb66eda8`.
- Saved records: both versions, seeds `20260917`, `20260918`, `20260919`; `course_p00_predictions.json` and `course_p10_predictions.json` for each. These course diagnostics are not a fresh hidden evaluation and are not the original pass-rule reconstruction.
- Own worktree: `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-a2`.
- Own branch: `codex/helm-failure-a2-20260922`. Initial HEAD: `59b1dd57e57648ab68c1cc26fbae95a957c20cd3`. Initial status was clean. All new files are under this report's `agents/A2` directory.

No peer first report or new peer conclusion was read. Historical narrative exposure occurred in the shared directive, workspace report, root `CLAUDE.md`, own CNCM `AGENTS.md`, and the studied source's comments/docstrings. Those comments assert causes concerning frozen messages, reach information and correspondence. I treated them as claims to check. Some are too strong when the complete answer path is inspected. The broad audit/lineage workflow was not expanded; the present read-only research scope controls. No production tracker or lineage was changed.

## Evidence identity

The manifest's two source ZIP hashes were verified before extraction and again in the diagnostic suite:

| Source | Source ZIP SHA256 | `pointer_learner.py` SHA256 |
|---|---|---|
| Helm1 | `18064398ce49869da9cd2fcf67592ee00365d6f04d9571e4f63ba3d29a798f71` | `e0fe6dc8b523bc65eaaf0c7b287ee1d931db591180e2c19eaa3f8fdce687c6c2` |
| Helm2 | `c42370c4941384c852feda33303dd70a01e956d28953cf07dd1b981220f31ed8` | `21dabd21bb2909ff5990e2b11fd45b75558dce82992c34edfe12f8f556cd5084` |

Saved source-package paths are in `source_copy_manifest.json`. All source copies retain exact original bytes. There are 18 verified member copies, including both versions of inputs, contract, learner, worker, slots, checker, course, source and focal modules. Supplemental identities are in `supplemental_source_manifest.json`.

`pointer_inputs.py` is identical in both packages, SHA256 `ba920d9e65e20b96dd0614a7131a80b9b87dd9918cb07d94ec5ebb4b628d0ecd`. `pointer_contract.py` is identical, SHA256 `70be7ae7b7b3dbefd6a5d168b04ab7394718d7456a264614236d31b0c9c09b3d`. `slots.py` is identical, SHA256 `3d79db262708264dcd77cd7fb0296e7683849b5967b82d72fd3c51ab85f74487`. The identical checker is SHA256 `57ac0a9f78c46999fac444fc974d3c1b718435b583cbc48701be74c56efa971e`.

The course is manifest-bound to SHA256 `cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987`. It contains 64 worlds and 564 unique registry records. Every saved prediction artifact read by the diagnostic suite was verified against its manifest hash; exact paths, hashes and byte counts are in `probe_results.json` under `verified_artifacts`.

Source citations below name the copy under `source_copies/helm1/` or `source_copies/helm2/`; their line numbers are the historical package's original line numbers, not current integration code.

## Actual computation

| Stage | Checked implementation and information carried |
|---|---|
| Reader | Both `pointer_inputs.py:203-249,339-421`: node references become sorted local positions; directed `contains` is preserved; declared-whole and ordered participant-list flags are preserved; whole/part question marks and focus/target flags are preserved. Node label text is omitted. The rank-feature switch is false (`pointer_contract.py:896`), but participant list rank and question node rank still enter. This is not an absence of every position cue. |
| World scope | `pointer_inputs.py:384-392`: world-choice questions keep all worlds; other questions keep focus, plus correspondence target. `course.py:285-292` creates the public packet from the saved course. |
| Raw graph features | Helm1 learner `883-946`; Helm2 `979-1042`: 8 base features plus 5-way in-degree and 5-way out-degree one-hot blocks, normalized per row. The base features include a zero primary-label column in the active branch and a constant bias column. Degrees are capped at 4. |
| Local state | Helm1 `993-1049`: initial state is encoded raw features. Every round recomputes the message input from raw features and their adjacency aggregates; updated neighbor states are never used. Helm2 `1091-1156`: each round instead aggregates current hidden states through a new shared state encoder. Both use 8 shared rounds and normalized residual updates. The code's parent/child variable labels are reversed relative to `A[source,target]=1`; both directions are present. |
| Query | Helm1 `949-965,1195-1213`; Helm2 `1045-1061,1303-1321`: kind/rule one-hots, whole and part ranks (or -1), target-present and world-count scalars. The two named node states are added to the encoded query when present. |
| Pool | Helm1 `1215-1250`; Helm2 `1323-1358`: node-state mean, max, learned attention sum and four scalars go through a projection. Those scalars use normalized zero-in-degree and zero-out-degree feature columns, summed and divided by count. They are not full degree histograms or raw degree sums. |
| Text | Helm1 `1080-1129`; Helm2 `1187-1236`: declaration token IDs are remapped to sorted positions within each field's current reading vocabulary, deduplicated and summed through a field table. Token order and repetition are lost. For role questions, the separate prefix tagger supplies role indicators (`helm1:617-643`; Helm2 `639-665,1874-1875`). This is a controlled-language path, not general excerpt understanding. |
| Answer components | Node membership reads node state plus query; whole/VIA choices use a node/query dot product; edges read two node states plus the actual adjacency bit. Role answers receive indicators, query, focus pool and role embedding. Correspondence mode reads query plus focus and target pools. World-choice scores read two query/candidate dot products, candidate flags and the candidate declaration embedding. |

The executable syntax trees of `_graph_blocks`, `_query_vector`, `_encode_query`, `_pooled_worlds`, `_world_scores`, and `_declaration_embeddings` are identical between the two saved learners after removing docstrings. Exact line ranges are in `probe_results.json`.

## Findings and their limits

### 1. The frozen local message input is real, but it is not a whole-model one-hop theorem

Helm1's round input for a node depends on that node's raw row and its immediate neighbors' raw rows. It is constant over rounds for a fixed packet and fixed weights. Hidden states themselves still change through repeated residual updates. Raw rows already contain degrees, which summarize adjacency, so even “one hop” needs the qualification “of raw feature rows.”

The symbolic provenance probe on `0->1->2->3` gives node 0 raw-row dependencies `{0,1}` after every Helm1 round. Helm2 can reach `{0,1,2,3}` by round 3. This is possible information flow, not a measurement of learned weights using it.

Whole-model answers may also read all node states through pooling, two marked node states through the query, and raw adjacency through the edge component. Therefore the local result does not prove that every multi-edge answer is impossible. It also cannot explain the studied Helm2 gate losses by itself: the studied Helm2 code already aggregates updated states.

### 2. Both versions have a source-insensitive analogy comparison path

All 70 saved course analogy records have empty node arguments. Their query vector is constant for the fixed 64-world bank. `_encode_query` consequently adds no source-node state. `_world_scores` does not concatenate, compare, or otherwise consume the focus-world pool or focus-domain embedding. For a fixed non-focus candidate it reads only that candidate's independent graph state, candidate domain embedding, fixed query and fixed flags. Changing the focus leaves the candidate score unchanged unless that candidate itself becomes focus. The declaration vocabulary is also unchanged because the same bank is retained.

This is verified in the original saved scores: in every one of the 12 initial/final artifacts, all 64 non-focus candidate columns have exact saved score range `0.0` across the 70 analogy questions. No new predictions were generated. Independently applying the pinned isomorphism-plus-different-domain rule to these saved course answers gives 16/70 final correct for all six runs. That is a diagnostic recomputation, not a new certificate or a claim about the gate population.

A concrete impossibility witness is saved in full in `probe_results.json`:

- `typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e`, focus `world-71465a4148d1fa5896981052d1f7e8f7213a6d49db89a7b098628bf25f97c8b6`.
- `typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a`, focus `world-3828c653000bc7e59b653d131544dfef39fbd7d530ec52593fc4bc9f279c7796`.

Both focus worlds have four nodes and the grammatical domain, but different directed graph structures. Each has 9 accepted candidate worlds; the two accepted sets are disjoint. Neither source is in either accepted set. Every candidate needed for either correct answer is non-focus in both questions, so its relative ranking cannot change. A deterministic shared ranking cannot choose from both disjoint sets. This establishes a limitation of the actual analogy scoring/selection path for these cases, not merely a local message limitation.

The complete input objects and all logits are not claimed identical: focus flags change the two focus rows. The indistinguishability is the relative scoring of candidates that could give correct answers, which is sufficient for this contradiction. The checker accepts every valid world, not one preferred target (`checker.py:213-237`). The probe checks both complete accepted sets.

### 3. Helm1 cannot learn source-specific correspondence ranking, but its decoder can output a bijection

Helm1 `pointer_learner.py:1364-1366` sends every mapping slot through the same target-node scores, without its source node. Across all 88 correspondence questions in each of its six initial/final files, every source row is exactly equal. Helm2's source/target bilinear scores are different across source rows in all 88 cases in each of its six files (`helm2:1373-1422,1549-1557`).

The actual shared decoder enumerates syntactic bijections and sums all selected pair scores (`slots.py:96-113,259-296`). Thus Helm1 can output a bijection. With identical source rows, every complete permutation has the same score in exact arithmetic: every target is used once. There is no learned distinction among such mappings. Floating-point addition order can introduce tiny tie noise; it does not supply the missing source-conditioned evidence. The source comment saying the only possible output is every source choosing the same target describes independent per-row choice, not this decoder.

In Helm2 the bilinear term introduces source-specific evidence. Three rounds of Sinkhorn row/column normalization do not change the conditional distribution over complete bijections in exact arithmetic: each candidate sum loses the same sum of row constants plus column constants, then the mapping normalizer cancels it. The bounded algebra probe covers 2x2, 3x3 and 4x4 matrices (32 total permutations), with maximum log-probability discrepancy `3.552713678800501e-15`. This concerns the current joint decoder. It is not a general claim that Sinkhorn never matters, and it does not establish what caused the learned improvement.

### 4. Helm1 reach modes already receive pair information indirectly

Helm1's ABSENT/DIRECT component reads `[query, world_pool, degree_terms]` (`1265-1281`). Its query already contains both marked node states and their distinct raw rank fields (`949-965,1195-1213`); the node features also contain separate whole/part marks. Therefore “the head never saw either node” is too strong. Helm2 additionally concatenates the two ordered node states (`1424-1466`), which gives a clearer direct path. Whether that added path caused better or worse recorded reach answers is unproved. This first round did not conduct an exhaustive reach-collision search or load weights.

## Leading explanation, alternative and disproof

For persistent analogy weakness, the leading structural explanation is the missing source-world comparison in `_world_scores`. Optimization quality can change a global candidate preference, but cannot resolve the demonstrated conflicting requirements with this input path. The strongest alternative was a hidden source-dependent path through query encoding, world batching, declaration indexing, or decoding. The executable trace and exact saved score equality contradict that alternative within the fixed-bank course scope.

Evidence that would disprove this finding: a manifest-bound studied prediction file with differing scores for the same candidate while it is non-focus under two otherwise matched analogy questions; or an executed source path that carries focus structure/domain into those scores. Newer source would not disprove a finding about these versions.

For Helm2's exact pass-rule losses, no leading causal explanation is licensed by A2's checks. A plausible alternative to any architecture-only story is the combined effect of changed optimization, initialization and coupled updates. Those factors changed together; a larger representable function class does not guarantee retained correct answers. A1/A4 and the later conference must connect the exact failing records to evidence before assigning a cause.

## Smallest discriminating next tests

1. **Permitted record challenge:** independently read the two witness records and one source-bound final score file; confirm both complete accepted sets, candidate symbol ordering and every shared valid-candidate score. Expected result under the missing-source explanation: fixed relative order despite disjoint required sets. Under a hidden source-sensitive path: at least one required candidate score/ranking changes. This check should be reproduced independently rather than reusing this probe's functions. It need not load a model.
2. **NOT RUN, requires neural-execution authorization:** on the exact studied Helm2 checkpoint for seed `20260918`, keep the 64-world bank and parameters fixed and run the two witness analogy queries, recording the 21-value raw query, encoded query, candidate logits and focus/target pools. Expected missing-source result: equal query and equal non-focus candidate logits; a real source-dependent alternative predicts a difference. This is two forwards only, no training, source `20208c923d41c24614504d4ecc2b289ecb66eda8`, checkpoint identity from the common manifest, deterministic evaluation, stop after two forwards or any nonfinite value. Do not substitute current integration code. This is optional confirmation; saved scores already supply the relevant observation.

A repair trial that adds explicit focus graph/domain comparison would need matched initialization/training and a separately planned fresh test set. It is not authorized or performed here. It should not be sold as the cure for the historical gate losses.

## Execution and scope accounting

The decisive suite ran once, exit code 0, status `PASS`, in `0.6469044000114081` seconds on Python `3.14.0`, standard library only. `COMMAND_LOG.md` records the actual commands, failed inspections and output receipts. No Torch import, checkpoint deserialization, neural initialization, inference, training, GPU, cloud call, package installation or paid API occurred. Costs for native agent/tool use are unavailable, so no zero-cost claim is made.

- **Test functions:** 5, all executed once. **Repeat suite executions:** 0.
- **Source cases:** 2 ZIPs, 18 member copies, 6 unchanged-function comparisons.
- **Symbolic case:** one four-node path, observed at 8 steps per version; these are not 16 independent experiments.
- **Data cases:** 64 world structures and 70 analogy records; 2 existing records selected as a contradiction witness. No fresh evaluation claim.
- **Saved outputs:** 12 files containing 6,768 predictions; selected checks use 840 analogy and 1,056 correspondence prediction instances. The same records across seeds/checkpoints are repeated record observations, not independent input cases.
- **Algebra cases:** 3 matrix sizes, 32 permutations in each compared condition. No trained model evaluated.
- **Unexecuted:** all neural/causal intervention proposals; exhaustive collisions across other task families; independent final judgment.

Probe SHA256: `158f8c93c767526071dda79f2f1c4c98ddcd6eb5f737d547c43ec315ffcb1baa`.
Result SHA256: `24368d85b58e0af2970e753cf0e89d6a4ac7ff7beef6bfe424aa22ab1955b7cf`.

Unknowns remain: actual learned feature use, exact cause of each lost gate answer, the effect of individually changing each Helm2 component, and transfer after a repaired analogy head. These source and record findings do not alter either historical label.
