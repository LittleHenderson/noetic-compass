# A6 immutable first report — 2026-09-22

Helm 2.0 failed the original study rule because **one of three seeds** failed the primary statistical test. Two seeds lost one previously correct question, but only seed 20260919 failed. The directive's historical summary conflates those two facts. This result does not identify why training changed the answers.

## Question and scope

Independently reconstruct the decisive recorded pass/fail arithmetic, then independently check the lost answers against their declared graphs. Subjects: Helm 1.0 source `af0970cfa6d54a85aeb16e5a99a84d791ace59c0`; Helm 2.0 experimental source `20208c923d41c24614504d4ecc2b289ecb66eda8`; seeds 20260917, 20260918, 20260919. The worktree started clean at `59b1dd57e57648ab68c1cc26fbae95a957c20cd3` on `codex/helm-failure-a6-20260922`.

I read the common directive, handoff, boundaries, workspace report, manifest, local CLAUDE.md and CNCM AGENTS.md. Historical opinions encountered: the directive's two-failed-seed claim and comments about frozen messages, matching heads, simple baselines, and repeated structures; grader comments also discuss flag-copy and rank shortcuts. None was treated as an established mechanism. No peer report was read before this report.

## Recorded result independently reconstructed

| Version | Seed | Wrong to right | Right to wrong | Exact one-sided p | Primary test |
|---|---:|---:|---:|---:|---|
| Helm 1.0 | 20260917 | 10 | 0 | 1/1024 | Pass |
| Helm 1.0 | 20260918 | 12 | 0 | 1/4096 | Pass |
| Helm 1.0 | 20260919 | 11 | 0 | 1/2048 | Pass |
| Helm 2.0 | 20260917 | 11 | 1 | 13/4096 | Pass |
| Helm 2.0 | 20260918 | 12 | 0 | 1/4096 | Pass |
| Helm 2.0 | 20260919 | 7 | 1 | 9/256 | **Fail** |

All rows exactly match their saved gate readings. The frozen rule requires more gains than losses, p <= 1/100, gains across at least two question kinds and two worlds, and passage in all three seeds. The kind/world conditions pass in all six cases. This is **not a rule forbidding any loss**. For seed 20260919, 9/256 = 0.03515625 exceeds 0.01. Holding its seven gains fixed but retaining the lost question would give 1/128 = 0.0078125. That is an arithmetic counterfactual, not a model intervention or a rewritten result.

The saved Helm 1.0 label remains `LEARNS_NEW_WORLDS`; Helm 2.0 remains `NO_TRANSFER_TO_NEW_WORLDS`. Both saved gate records contain no taken VOID paths; this narrow reconstruction does not rerun the full integrity chain or issue certification.

## Raw answer cross-check

- Seed 20260917: query `typed-query-404166e8b8180ddc5758d193239cd0f8a5f91804f2f87bc6141ab9f782157005`, one input record. The unique directed path is world `4090ec...` `/n1 -> /n3 -> /n0`. Initial answer `VIA /n3` is correct; final answer `DIRECT` is wrong. This seed still passes.
- Seed 20260919: query `typed-query-369885551a553d5fa430a4f0389a1e547fb4b7a6234e85d2c9aace042f4fd46f`, four input records for the same question. The unique directed path is world `28f61f...` `/n2 -> /n3 -> /n0`. All four initial answers say `VIA /n3`; all four final answers say `VIA /n1`. Under `bfs_immediate_predecessor_lexical_v1`, `/n3` is required. This is one question loss, not four independent question losses.

The full world IDs, edges, queries, raw answers, score records and source locations are retained in `lost_answers.json` and `reach_verification.json`. The displayed path abbreviations above are labels only; raw identifiers are unmodified in those records.

## Independence, evidence and limits

`reconstruct.py` imports only Python standard-library modules. It groups saved per-record correctness into questions using the public course registry, and enumerates all fair-coin bit patterns to calculate the exact tail probability. It does **not** import or call the historical grader or its combination-sum function. The 18-question population is reused from the saved gate and is not independently re-derived from exclusion rules. Correctness for the other 16 population questions is reused from saved scoring.

`verify_lost_reach.py` independently enumerates simple directed paths from the raw declared graphs. It checks both lost questions across five saved input records. Each case has one unique path, so lexical tie rules cannot change the answer. It reads frozen checker text to document semantics but never executes that implementation.

All consumed original JSONs are checked against manifest SHA256 and size before interpretation. `reconstruction.json` records 20 unique original-file fingerprints. Grader SHA256: `d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d`. Exact grader lines: 112–114 (thresholds), 283–338 (arithmetic and decision), 740–764 (record merge), 1045–1078 (checkpoint/question aggregation). `source_lines.txt` preserves them. Frozen checker member SHA256: `57ac0a9f78c46999fac444fc974d3c1b718435b583cbc48701be74c56efa971e`; member lines 129–153 define reach. Its ZIP is independently hash-checked and listed in `reach_verification.json`.

Executed: two diagnostic scripts once each, zero dedicated test functions, six version/seed cases, 108 question-transition cases comprising 330 input-record pairs, plus five lost-answer record checks representing two questions. The two scripts took 0.279639700005646 and 0.099884800001746 seconds internally. There were no repeats, failed assertions or nonzero process exits. Early exploratory displays were truncated; bounded follow-up reads recovered the needed fields. No Torch, neural checkpoint load, model initialization, inference, training, GPU, cloud, paid API, install or allowance expansion ran.

## Challenge and next test

Leading explanation for the official label: seed 20260919's seven gains and one genuine reach loss fail the frozen probability threshold. Strongest alternative: a population, grouping or semantic scoring error produced the label. Independent regrouping and path checks reject that alternative for the two losses; frozen-population derivation and every other semantic score remain outside this narrow check. A different manifest-bound population, a correct alternate reach answer under the frozen rule, or inconsistent record-to-question mapping would disprove or narrow the conclusion.

Smallest next discrimination, **NOT RUN in this first report**: use the five already saved prediction records and their slot scores to compare selected candidates against the frozen decoder's ordering rule. A selected candidate violating that ordering supports a decoding discrepancy; a correctly selected but wrong highest-scoring candidate supports changed learned scores. The latter still would not isolate architecture, curriculum or optimizer causes. New model interventions needed for those causes are proposals only and remain NOT RUN.

