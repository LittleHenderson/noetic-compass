# F1 — saved complete reach-answer decoding

**Result: no decoder discrepancy, omitted correct candidate, nonfinite score or winning tie was found in the ten preregistered prediction instances.** Every saved choice follows the frozen complete-answer order. Both final mistakes are wrong score rankings: the correct complete answer is available but scores below the selected wrong answer. This supports F1's registered “Changed learned scores” outcome, without identifying a training or architecture cause.

F1 was registered in FOLLOWUP_PLAN.md at `259ed0be9f18be6c75f6a7166c71db42718c0538`, before outputs, and dispatched after the conference at integration `5c128a33`. Scope stayed at two lost reach questions, five original input records, p00 and p10 only, Helm2 source `20208c923d41c24614504d4ecc2b289ecb66eda8`. FIRST_REPORT.md is unchanged.

## Exact decoder

The frozen reach branch creates **one slot whose symbols each denote a complete answer**: ABSENT, DIRECT, then VIA_N0 through VIA_N3 in lexical node-reference order. ABSENT and DIRECT map to `via:null`; VIA_Ni maps to that node's full reference. All focus nodes are syntactically permitted, including semantically wrong choices. The actual selector takes the first maximum in the declared order. There is **no separate mode/VIA combination or normalization** for reach. The correspondence-only normalization must not be imported into this branch.

Original source.zip members, hash-checked for both subjects, establish this path: answers.py:135–169 gives the full node inventory; slots.py:54–60 establishes node aliases; :106–107 constructs the reach symbols; :243–249 checks score coverage and finite bounds; :283–296 selects; :344–348 assembles the answer. pointer_learner.py:1558–1564 concatenates ABSENT/DIRECT scores with VIA node scores into the same candidate vector. Exact source excerpts/hashes are in F1_RESULTS.json.

## Recorded scores and ranks

The correct answer is VIA_N3 for both questions. Ranks are among all six complete candidates; rank1 is best. Seed20260919's four presentations have identical listed values.

| Seed / phase | Presentations | Selected symbol | Selected raw score | Correct raw score | Correct rank | Winner minus correct |
|---|---:|---|---:|---:|---:|---:|
| 20260917 / p00 | 1 | VIA_N3 | 6.773494243621826 | 6.773494243621826 | 1 | 0 |
| 20260917 / p10 | 1 | DIRECT | 2.56620717048645 | -25.31268310546875 | 3 | 27.8788902759552 |
| 20260919 / p00 | 4 | VIA_N3 | 17.396583557128906 | 17.396583557128906 | 1 | 0 |
| 20260919 / p10 | 4 | VIA_N1 | 26.474693298339844 | 22.808488845825195 | 2 | 3.6662044525146484 |

The failing seed19's correct answer increases in absolute score yet loses its relative rank. Its final maximum is unique, with margin3.6662044525146484 over the runner-up. Seed17's final winner is unique with margin8.581420183181763 over its runner-up. Thus changing exact-tie handling cannot repair these recorded choices. Raw full score dictionaries, all candidate ranks, selected/assembled answers, exact record/query IDs and unique graph paths are preserved in F1_RESULTS.json.

## Method, counts and limits

`f1_saved_reach_decoder.py` independently translates the published ordering into a strict-improvement scan. It imports only Python standard-library modules; it does not call the original decoder, checker, learner or Torch. It reads original prediction files directly after SHA256/size verification. The previous A6 output supplies only the five preregistered record locators. Public-course graph paths independently reconfirm their semantic targets. Both source archives, all four endpoint files and the course are fingerprinted.

One substantive execution, exit0, Python3.14.0, elapsed0.13131100000464357 seconds; a115-second watchdog enforces the120-second limit. Zero formal test functions or repeat executions. Two unique questions, five input records, ten saved prediction instances, six complete candidates each, sixty finite bounded score entries. Five initial correct selections; five final wrong-ranked selections; zero decoder mismatches. No additional record comparisons or model predictions were run.

The selected candidates and their scores are fully checked within this scope; the model-generated logits themselves were not recomputed. Full packet/slot-plan digests, the whole integrity chain, other questions and intermediate checkpoints were not reconstructed. This does not prove a globally correct decoder, isolate why ranks changed, or license a neural repair. It rules out the preregistered missing-candidate, exact-tie and decoder-order explanations for these two observed losses.

Probe SHA256: `f74474cd66e496e90d19e17b008fab73ad0f8d5ccd51ee2b25fb823494df1235`.
Raw result SHA256: `8b7dc6da0d72a6a8051b894cd18becfa40fe7bfedc39548aa0106c9e234f68b5`.
