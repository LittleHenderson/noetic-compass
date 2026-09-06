# Independent JSON-only B/R review

Result: the saved evidence supports the narrow component-execution claims. It does not establish a task-conditioned correct versus wrong input choice.

Job: `cas-meta2-20260906150012-7c9f6d00`.

## Inputs and scope

Reviewed `execution_001/cloud_artifacts.zip` and `analysis_001` in the parent record directory. Archive SHA-256: `3cd1806649e0cd357d37391b805c64f928f0b5615aea524f8d84332f77aa735a`; size: 1,502,016 bytes. The three analysis files match `analysis_001/receipt.json`; summary SHA-256: `bdf3bfa30544e75dafebdaf90090bad184ae4df68e98bc637abaef8e6df78e7e`.

Independent standard-library checks verified the 45 indexed JSON/text members against the collection index, all 46 JSON/text members including that index against the analysis hash map, and the complete 50-member name set. The four database members were not opened or read individually. No native/model imports, tensors, SQLite connections, or provider calls were used. This is a check of saved evidence, not a native rerun.

## Supported claims

- **Six distinct committed native ticks.** `construction/construction_receipt.json` has four ordinary prelude results, A/B/C/R, followed by one C result per arm. Each `construction/arm_{B,R}/result.json.after_recovery.traces` contains ticks 1–5; its first four complete trace objects exactly equal `construction/preclose_witness.json.recovery.traces`. Their union has six trace IDs, not ten. All six are sealed, have one `ACCEPT` verifier receipt, and contain no model intents, repair frames, or repair outcomes. Lifecycle worker receipt records exit code 0 and `BR_COMPONENT_EXECUTED`.
- **Same recorded starting state.** The preclose, B-before and R-before witness files are byte-identical, SHA-256 `e93d887f940076dc6aa6d69f1085ca742521d4c8c1f62721a2289d8bb7562bee`. `analysis_001/summary.json.analysis.before_state_comparison.checks` contains `preclose_self`, `preclose_to_B`, `preclose_to_R`, and `B_to_R`: all `ok=true`, no reasons. These are four checks, not four independent experiments. Every CJT has empty `rpm.open_repair_ids`, empty `memory.repair_frame_ids`, and null `rpm.suspended_parent_cause_id`. The event sequence records both restored states checked before either arm ran.
- **Compute accounting.** Each of the six native receipts charges 72 policy units: 288 for the shared prelude and 72 per arm, 432 total. Both arms report 8,120 remaining from 8,192. These are policy-accounting units, not FLOPs or GPU kernel counts. Saved forward-call counters are 108 for the prelude and 27 per arm.
- **Different numbers, same decoded result.** Each arm is `ACCEPTED`, with `same_fixed_expectation="L2"`; both output contents are `DECOMPOSITION_SIGNAL`, operation `^6`, symbol `L2`. Recomputing the maximum absolute difference from the eight saved JSON numbers gives exactly `5.323855634742358e-05`. Serializing those numbers as float32 independently matches each output's recorded payload SHA-256. Both arm result objects exactly match the construction receipt copies.
- **Unchanged recorded model/source identities.** Both post-arm runtime identities exactly equal the preclose identity, including model digest `76a9bcbce5ffdec4c2dbc9d8ea9958a268dcebf3775f53dd6058a72086709528` and parameter-byte digest `7a512eadbd8ef265f03f965a28422112651bdf0c0bd1949d56626ba89f76c3d5`. All six traces retain that model digest. All 38 observed import-source hashes map uniquely to matching entries in the registered source manifest. Source-before and source-after receipts both report 630 verified files at worker `d047540a635ecccdd2cfd4d96ee3b43da59f7ce7` and manifest `7d5fdf331e74638b5cd1ecf9fca2c4a5ae3610aa562014decc5c03e4ca29944f`. The manifest retains accepted baseline `0917267b1354e5d036263eaa6ba9a7197eafb776`, its 316-file identity and baseline-manifest digest `476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0`. This JSON review does not independently rehash the original accepted checkout or installed runtime bytes.

## Limits that must remain explicit

Neither B nor R is demonstrated to be a wrong choice under the fixed L2 verifier: both pass. No task-conditioned target, learning result, generalization result, or full-program continuation was established. The intervention changes the whole committed reference, including payload, producer, provenance and age; it is not a payload-only ablation. B was published at tick 2, age 3 at comparison tick 5; R at tick 4, age 1.

The pure witness checks correctly retain `native_verified=false` and `outer_ownership_verified=false`. Empty outer frames and zero outer executors remain explicit construction assertions, not independently proven process absence. Parent cleanup and final cost/provider receipts are outside this review. No contradictory JSON evidence or unsupported claim was found in the saved narrow analysis when these limits are preserved.
