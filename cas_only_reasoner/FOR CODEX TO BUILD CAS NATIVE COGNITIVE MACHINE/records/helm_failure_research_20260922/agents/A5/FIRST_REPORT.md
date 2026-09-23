# A5 immutable first report — answer selection and comparisons

Scope: analogy and correspondence in the six original Helm jobs. Helm 1.0 source is af0970cfa6d54a85aeb16e5a99a84d791ace59c0; Helm 2.0 source is 20208c923d41c24614504d4ecc2b289ecb66eda8. Seeds: 20260917, 20260918, 20260919. This report does not replace the historical pass/fail rule or explain its retention gate.

## Main findings

The actual decoder already enforces one-to-one matching. Helm 1.0's correspondence scores cannot distinguish complete permutations: each source node receives the same target-score row. Helm 2.0 removes that specific restriction with pair-dependent scores and correctly answers all 20 held correspondence records in every seed. Both versions still answer 0/17 held analogy records correctly. Their analogy mistakes cannot be repaired by changing the exact-tie winner: no correct world is among any final top ties.

| Saved population, each seed | Helm 1.0 analogy | Helm 2.0 analogy | Helm 1.0 correspondence | Helm 2.0 correspondence |
|---|---:|---:|---:|---:|
| Full public registry, course_p10 | 16/70 | 16/70 | 7/88 | 88/88 |
| Held records, restored final.pt | 0/17 | 0/17 | 0/20 | 20/20 |

These are six distinct trained runs evaluated on shared questions, not six independent datasets. The 88 correspondence records are the full registry, not 88 exclusively taught examples. Results reconstruct 2,118 saved selected-family occurrences across initial, final and held-final phases, representing 158 unique records. Every reconstructed decoder choice matches its saved answer, and every independent edge/domain correctness check agrees with the saved checker.

## Registered comparisons

Before calculation, methods and competing predicted outcomes were committed in PREREGISTRATION.md at **32b7acc603765730a4df596de62cc1fbc4f93a53**, timestamp **2026-09-23T06:00:51.5644549Z**. The local date was September 22. These methods use public graphs/domain strings only; saved labels are used afterward for assessment.

| Method | Analogy full / held | Correspondence full / held |
|---|---:|---:|
| Lexical first different-domain world / equal-rank node pairing | 12/70; 4/17 | 7/88; 0/20 |
| Directed degree comparison, lexical first surviving answer | 70/70; 17/17 | 80/88; 12/20 |
| Exact directed-edge-preserving permutation search | 70/70; 17/17 | 88/88; 20/20 |

The simple degree method solves the selected analogy cases but does not fully solve correspondence. Exact structural comparison solves both on this small public bank. This establishes available inexpensive comparators, not learned performance, fresh transfer, or a new compiler feature. It does not establish that Helm actually uses a name shortcut. Full-registry analogy questions accept either six or nine worlds; held correspondence questions accept one mapping in 16 cases and two in four cases. Evaluation correctly accepts all alternatives.

## Source trace and decisive checks

Paths below are ZIP members under `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/`, unless noted otherwise. SOURCE_PROVENANCE.json preserves exact line excerpts and hashes. Every source.zip, config and loaded_sources record for all six jobs was checked against the manifest. Config source_sha and seven relevant loaded-module hashes per run match the actual ZIP source.

- `slots.py:94-101`: analogy candidates are NO_MATCH plus every bank world; correspondence has a mode slot and all target-node options for every source node. `answers.py:285-304` enumerates NO_MATCH plus every syntactic bijection, at most four nodes. Candidate construction uses node inventories, not correct graph mappings.
- `slots.py:259-296`: correspondence scores the sum across each complete assignment, normalizes over all assignments, adds the MAPPING mode probability, then compares with NO_MATCH. It never decodes independent row maxima. First candidate wins exact ties; NO_MATCH is first, followed by lexical permutations. `answers.py:205-221` checks source coverage and target bijection. All saved MAPPING answers checked are bijections; no duplicate-target explanation applies to them.
- `checker.py:200-237`: correspondence accepts every exact directed-edge isomorphism; analogy accepts every isomorphic world from a different declared domain. `checker.py:243-268` forms the complete admissible set. The independent probe reimplements edge equality and domain inequality without importing the checker, but necessarily tests the same specification.
- H1 `pointer_learner.py:1252-1265,1364-1366`: mapping_target calls the same target node/query dot product without a source-node term. Every inspected H1 matrix has identical rows. At final evaluation, all complete mappings tie exactly; lexical rank pairing explains the recorded 7/88 full and 0/20 held results. All 20 held mistakes have a correct mapping among the top ties. This is an established score restriction, not proof that no alternative decoder could use extra graph information.
- H2 `pointer_learner.py:1373-1422,1549-1561`: the matrix is source-state/target-state bilinear scoring, followed by three log-domain row/column normalizations. None of the H2 final matrices has identical rows; final mappings have a unique top candidate. H2 initial independent row maxima would duplicate targets in 70/88, 73/88, 70/88 records by seed, although the actual whole-assignment decoder remains syntactically valid. Soft normalization alone must not be substituted for that decoder.
- Analogy H2 `pointer_learner.py:1484-1516` and H1 `:1300-1331`: learned world scores consume query/candidate dot products, flags and declaration embeddings. NO_MATCH receives zero. Actual output is argmax over all candidates. For held-final records, the best valid candidate's strict score rank lies between 10 and 29 for H1 and between 13 and 32 for H2, depending on seed/question. Every final analogy record has a top tie, but none of the wrong top ties includes a valid answer. Thus lexical tie changes cannot fix these observed analogy errors; the learned ranking must change or explicit structural comparison must be added.
- `cncm/typed_pointer_worker.py` H2 `:1487-1490` restores final.pt and evaluates held packets as ablation_baseline. The matching H1 excerpt is in SOURCE_PROVENANCE.json. This identifies the held-final population rather than assuming heldback_p08 was final.

### What Sinkhorn can and cannot explain here

For a complete bijection pi, let T(pi)=sum_i S[i,pi(i)]. Any log row/column normalization replaces S[i,j] by S[i,j]-r[i]-c[j]. Then T'(pi)=T(pi)-sum_i r[i]-sum_j c[j]. The subtracted quantity is the same for every bijection, so both permutation rankings and normalized whole-permutation probabilities are unchanged in exact arithmetic. The decoder's NO_MATCH versus best-mapping comparison is unchanged too when mode logits are fixed.

The preregistered 12 finite-matrix cases (n=2,3,4; zero, column-only, identity-preference and asymmetric matrices) confirmed this, with maximum probability difference **5.551115123125783e-16**, below 1e-12. Therefore the addition of Sinkhorn normalization alone cannot explain a changed complete-assignment decision under these algebraic conditions. The bilinear pair scores can distinguish mappings, unlike H1's repeated rows. This does not isolate causes of trained improvement: other model changes, optimization and floating-point training effects were not held fixed. No Torch, automatic differentiation, model initialization, checkpoint load or neural execution occurred.

The registered mode-first alternative changes no final correspondence answer in either version. It changes 88 initial H1 seed-20260918 decisions, recovering only seven full-registry answers; it cannot resolve the H1 structural ties. It changes 18 initial H2 seed-20260917 decisions and recovers none. This is historical diagnostic evidence, not permission to replace the frozen decoder or grader.

## Interpretation and remaining alternatives

**Leading bounded explanation:** H1 correspondence failure is directly explained by source-independent mapping rows plus lexical selection. H2 learned scores overcome that restriction on these recorded questions. Analogy failure is a learned-score ordering failure at the final selector, despite correct options being present and simple public structural methods succeeding.

**Strongest alternative for the unresolved analogy cause:** the ranking may reflect missing/ineffective focus information, representation collisions, or an optimization/training problem. Saved score order alone cannot separate those causes. Candidate construction, rejection of valid alternatives and exact-tie policy are contradicted as explanations for the inspected analogy failures.

**Disproof conditions:** a manifest-bound H1 row with different source-dependent target scores would falsify the repeated-row finding; a saved final analogy error with a valid maximum-score candidate would falsify the no-tie-repair finding; either a source identity mismatch or independent decoder/checker mismatch would invalidate the corresponding reconstruction. None was found in the selected scope. A new graph where the degree shortcut fails would limit its reach without contradicting its measured success here.

**Smallest remaining discriminating test:** freeze one failed analogy question and a minimally changed focus graph whose valid analogy class differs while the candidate bank stays fixed. Compare the actual source's focus-dependent scorer inputs before new compute. If source analysis proves those inputs identical, that supports an information-path limitation; if they can differ, a separately authorized frozen-checkpoint, paired-input neural test would distinguish actual insensitivity from an available but unlearned distinction. Predicted results and graph identities must be registered before that test. It was **NOT RUN**. For attribution of H2 correspondence gains, a matched pair-score versus normalization ablation is still unrun; the algebra already removes normalization-only decoding as an explanation in exact arithmetic.

No fresh hidden cases, new model run, official gate rerun, causal training ablation or generalization claim is included. Historical labels remain unchanged. No peer first report was read. Prior exposure is disclosed in the preregistration: the common historical narrative and original source comments included causal opinions and earlier counts; this report verifies them where tested rather than claiming a blind investigation.

## Evidence, commands and counts

- `probe.py`: SHA256 6334f978e2782329216b6fff43f58a49c7dfba13e82a8a73a4049d0cea1b02b9.
- `RESULTS.json`: SHA256 1b0ab4c1f87afc54159693720c80a6f0bd254ee067d6cc29487e3a31b645d5cb; row-level decisions, valid ranks, ties and alternative outcomes.
- `SOURCE_PROVENANCE.json`: SHA256 f82d2f1390ef274026e09fd0561ddb20aea09fce80aed862e1f746ea36c954eb.
- H1 pointer source: e0fe6dc8b523bc65eaaf0c7b287ee1d931db591180e2c19eaa3f8fdce687c6c2. H2 pointer source: 21dabd21bb2909ff5990e2b11fd45b75558dce82992c34edfe12f8f556cd5084. Shared slots source: 3d79db262708264dcd77cd7fb0296e7683849b5967b82d72fd3c51ab85f74487.
- `CONSUMED_FILES.json` records hashes of all 37 graph/prediction/scoring inputs; provenance adds the 18 source/config/loaded-record inputs. `SUMMARY.json` is a compact machine-readable table.
- Formal pytest test functions: **0**. Substantive checks: saved-decoder/semantic reconstruction and the algebra property, plus six registered simple comparison methods. The algebra property runs inline, so RESULTS.json's `algebra_property_function: 1` means one property check, not a named test function. Unique graph-task records: **158** (70 analogy, 88 correspondence), including **37** held records. Saved-record occurrences: **2,118**. Algebra input cases: **12**, covering 128 enumerated assignments per before/after side. Complete substantive probe executions: **1**; repeat executions: **0**. Provenance-helper executions: **1**. Main probe elapsed **0.7492723000032129 seconds**.
- Both scripts ran with C:/Python314/python.exe -B, PYTHONDONTWRITEBYTECODE=1, PYTHONIOENCODING=utf-8 and explicit A5 workdir. Exit codes **0**. No diagnostic assertion failed. Discovery encountered two harmless missing-manifest-key PowerShell errors and some output truncation; corrected structured reads succeeded. One discovery command misspelled the encoding variable; the substantive probes set it correctly. COMMANDS.md preserves the reproducible commands and tool-output IDs.
