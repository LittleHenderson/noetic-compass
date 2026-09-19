# Input defect of the old machine — measured

> Produced 2026-09-19 by a read-only $0 sub-agent (pure Python, no torch) for the pointer-machine design.
> Scripts and raw outputs: `measurements/input_defect/` (the 53 MB `build2.pkl` cache was not kept; `build2.py` rebuilds it in ~556 s).
> Paths inside refer to the session scratch folder where it ran; the copies are here.

VERDICT: PARTLY. The part about transfer is CONFIRMED by measurement for the four per-bit kinds. The stated reason is too strong as worded. Half of each held input is almost identical to trained inputs. The half that is truly new is the slot query hash, and the same failure happens for any never-seen slot name, including new slot names inside trained worlds.

ARTIFACTS (all under C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner\12c87ae7-c1f0-44b3-9b95-de65d5efbd48\scratchpad\understand\defect2\)
- enc_rebuild.py: copied from ..\defect\. I re-checked it line by line against encoder.py:154-164 (packet) and encoder.py:202-212 (slot). It is faithful and float64.
- build2.py → build2_out.txt and build2.pkl: all 564 packets, 2598 slots, 556.1 s.
- analyze2.py → analyze2_out.txt and analyze2_summary.json: measurements (a) to (e), a same-world calibration, and a leave-5-trained-worlds-out control.
- analyze2b.py → analyze2b_out.txt: held-world aliases, spec counts, a random-query null for (e), and a seen-spec vs unseen-spec split.
- check_alias_hits.py → check_alias_hits_out.txt.
- The earlier attempt's defect\build.py never wrote build.pkl (it was cut off). build2.py replaces it. dm_cache.pkl was not used.
- Pure Python, standard library plus the project's pure modules. No torch. $0. No repo edits.

GATE (MEASURED)
- projection sha256 4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9, shape [3829,64]: MATCH.
- readout sha256 14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667, shape [90,64]: MATCH.
- Split: held 127, trained 358, excluded 79 (total 564).

STRUCTURE (READ)
- Every packet includes every bank world:
  - course.py:86-87 builds `_public` with all bank worlds.
  - input_frames.py:256-279 writes one WORLD row per world.
  - input_frames.py:159-161 assigns aliases W0..W63 by sorted world_id, so the aliases are the same in every packet.
- Packet vector = unit(sum of unit rows / sqrt n), encoder.py:159-164.
- Slot input = normalize((packet + query)/sqrt 2), encoder.py:202-212.
- The query vector is a hash, not a sum of token rows:
  - row_bytes, binding.py:198-202: sha256 of the canonical [ROW_ALGORITHM, seed, 64, domain], 64 bits, each ±0.125.
  - The spec holds kind, field, group, scope alias and coordinates written "Wk/Nj", binding.py:226-232.
- A slot's scope is the focus world unless given otherwise, slots.py:77-78.

(a) Worlds per packet and row make-up (MEASURED, all 564)
- 64 worlds and 64 WORLD rows in every packet.
- Rows per packet: 73 (180 packets) or 76 (384 packets).
- Distinct row byte-keys across the 564 packets:

| Row type | Distinct keys | Meaning |
|---|---|---|
| FORMAT, ALIASES, POLICY | 1 each | same in every packet |
| WORLD | 64 | the same 64 rows in every packet |
| SOURCE | 24 | one per focus world |
| BINDINGS | 564 | content-free sha256 digests, unique per packet |
| RECORD | 564 | question-specific |
| QUERY | 316 | question-specific |
| SUPPORT | 904 (of 1152 rows) | question-specific |

- The shared block (FORMAT + ALIASES + POLICY + 64 WORLD = 67 rows) is byte-identical in all 564 packets: 1 distinct block. This includes the 5 held worlds' own WORLD rows, so they appear in every trained packet.
- Question-specific rows (RECORD + QUERY + SUPPORT) per packet: 2 (180 packets) or 5 (384 packets).
  - Share of rows: min 0.027397, median 0.065789, max 0.065789.
  - Share of tokens: min 0.011065, median 0.039432, max 0.048997.

(b) Cosine between packet vectors (MEASURED, all 158766 pairs)

| Pair group | n | min | median | max |
|---|---|---|---|---|
| Same focus world | 6444 | 0.942261 | 0.965208 | 0.999755 |
| — same question | 557 | 0.967154 | 0.998163 | 0.999755 |
| — different question | 5887 | 0.942261 | 0.963736 | 0.999655 |
| Different focus world | 152322 | 0.939479 | 0.965658 | 0.999492 |
| Held packet → nearest trained packet | 127 | 0.997695 | 0.999065 | 0.999467 |
| Trained packet → nearest other trained | 358 | 0.990379 | 0.999254 | 0.999755 |

- Norm of the course-mean packet vector: 0.983943 (1.0 would mean all packets identical).
- After removing that mean, the centred cosine does not separate focus worlds: same-focus median −0.093756, different-focus median −0.088831.

(c) Squared-norm shares (MEASURED)
- Additive share = <s_C, s>/|s|². The shares add up to 1 across categories.

| Category | Additive share: min / median / max | Own share \|s_C\|²/\|s\|²: min / median / max |
|---|---|---|
| Shared 67-row block | 0.857210 / 0.917762 / 0.955828 | — |
| Question rows | 0.000656 / 0.053518 / 0.116107 | 0.013677 / 0.041970 / 0.053570 |
| BINDINGS | median 0.014985 | — |
| SOURCE | median 0.003704 | — |
| START/END markers | median 0.013271 | — |

- Cosine between the question-row sum and the packet vector: median 0.276008.
- Inside the slot input enc: the query q's additive share is exactly 0.500000 for all 2598 slots. The question frame rows' share is median 0.032852 (min −0.018869, max 0.092127).

(d) Query vectors (MEASURED)
- Slots: held 617, trained 1665, excluded 316.
- There are 722 distinct trained specs, giving 722 distinct trained query vectors.
- Held slots whose exact spec, or identical vector, occurs among trained slots: 0 of 617.
- Held world aliases: W10, W17, W35, W49, W6.
  - Trained slots scoped to a held world: 0.
  - The 149 trained specs that mention a held alias do so only inside answer-symbol lists: context setting_ref 41, definition kind_ref 36, definition function_ref 36, analogy world_id 36.

| Comparison (max cosine per slot) | n | min | median | max |
|---|---|---|---|---|
| Held → any trained query | 617 | 0.312500 | 0.375000 | 0.562500 |
| Trained → any other trained query | 1665 | 0.312500 | 1.000000 | 1.000000 |
| Trained → a different trained vector | 1665 | 0.281250 | 0.375000 | 0.500000 |
| Control: 500 seeded random ±1/8 vectors → trained | 500 | 0.281250 | 0.375000 | 0.531250 |

- 90.0901% of trained slots have an identical query vector in another trained slot.
- Full input enc, per-bit-kind slots only:

| Comparison (max cosine of enc) | n | min | median | max |
|---|---|---|---|---|
| Held → any trained slot | 412 | 0.614490 | 0.691833 | 0.781626 |
| Trained → any other trained slot | 1152 | 0.612071 | 0.998809 | 0.999827 |
| Trained → other packet AND different spec | 1152 | 0.597306 | 0.690344 | 0.792557 |

(e) Per-bit linear probes: fit on trained-world slots, tested on held-world slots (MEASURED)
- Method: closed-form ridge least squares (targets ±1, unregularised bias) on enc = unit(p+q), with Gaussian elimination.
- Columns:
  - "enc λ" is the regularisation strength, shown as train/held accuracy.
  - "LDA" is the published estimator from measure_binding_variants.py:153-183.
  - "Majority" is the held majority-class rate.
  - "q-blind ceiling" is the best possible for any rule that gives one answer per packet.

| Kind | Train/held slots | enc λ=1e-3 | enc λ=0.1 | enc λ=1 | enc λ=10 | LDA enc | Majority | q-blind ceiling |
|---|---|---|---|---|---|---|---|---|
| parts | 171 / 36 | 97.6608 / 47.2222 | 97.0760 / 44.4444 | 94.1520 / 58.3333 | 76.6082 / 44.4444 | 96.4912 / 44.4444 | 52.7778 | 52.7778 |
| context | 156 / 68 | 100.0000 / 64.7059 | 98.7179 / 64.7059 | 96.7949 / 60.2941 | 78.8462 / 75.0000 (constant) | 98.0769 / 61.7647 | 75.0000 | 75.0000 |
| role_set | 180 / 36 | 83.3333 / 77.7778 | — | 80.5556 / 83.3333 | — | 79.4444 / 52.7778 | 83.3333 | 83.3333 |
| edge_account | 645 / 272 | 85.2713 / 68.7500 | — | 82.0155 / 73.8971 | 79.6899 / 80.1471 (constant) | 79.8450 / 52.2059 | 80.1471 | 80.1471 |

- Other held readers:
  - 1-NN held: parts 63.8889, context 55.8824, role_set 72.2222, edge 65.4412.
  - Lookup memoriser: key coverage 0.0000% for every kind, so it always falls back to the majority.
- Null test: the trained fit is kept fixed and each held query is replaced by a fresh random ±1/8 vector, 300 draws (1-NN: 50 draws).
  - Every observed held accuracy lies inside the null. P(null ≥ observed) ranges from 0.1633 to 0.9833.
  - parts 1-NN 63.8889: P = 0.2200. parts ridge λ=1 58.3333: P = 0.3500.
  - Nothing beats the majority beyond chance.
- Capacity note: distinct trained specs are parts 71, context 71, role_set 114, edge_account 269.
  - Specs carrying both labels across records: 0, 0, 28, 0.
  - So the high train accuracy is memorising hash codes.

Comparison with the published 96.3758% (MEASURED + READ)
- READ: 96.3758% is the context probe on q alone (LDA), BINDING_VARIANTS_RESULT.md:111. The enc LDA figure there was 94.2490%.
- READ: its folds were prediction index % 5 (measure_binding_variants.py:242), so records sharing a question can fall in different folds.
- MEASURED, my same-world 5-fold (record index % 5): slot counts match exactly (207 / 267 / 216 / 1029).
  - context: q LDA 94.8475, q ridge 95.5815, enc LDA 93.3725, lookup 98.9091, constant 78.6802.
- MEASURED, the same same-world folds split by whether the test slot's exact spec was seen in training:

| Kind | Seen spec: n, enc / q | Unseen spec: n, enc / q, majority |
|---|---|---|
| parts | 148, 100.0000 / 100.0000 | 59, 59.3220 / 61.0169, 61.0169 |
| context | 255, 96.8627 / 97.6471 | 12, 50.0000 / 50.0000, 75.0000 |
| role_set | — | 132, 71.9697 / –, 81.8182 |
| edge_account | — | 64, 78.1250 / –, 81.2500 |

- MEASURED control: leave out 5 trained worlds (10 draws), fit on the remaining trained-world slots, test on the left-out worlds.

| Kind | ridge enc test | Test majority |
|---|---|---|
| parts | 52.4241 | 62.1696 |
| context | 66.1184 | 78.8967 |
| role_set | 62.3988 | 80.7381 |
| edge_account | 72.6910 | 79.4534 |

- So any unseen world fails, not just the 5 held ones.

VERDICT DETAIL
- CONFIRMED (MEASURED, per-bit kinds): no transfer to held worlds.
  - Every probe is at or below the held majority rate, and within the random-query null.
  - For all four kinds, the q-blind ceiling equals the majority exactly.
  - Held accuracy 47.2222–64.7059 compares with 96.3758 same-world. That same-world figure comes only from exact-spec recall (seen 96.8627–100.0000 vs unseen 50.0000–61.0169).
- REFUTED as worded, "cannot relate to anything it learned" (MEASURED):
  - The packet half of the input is almost identical to trained inputs (nearest trained packet cosine median 0.999065). The held worlds' WORLD rows are in every trained packet.
  - But that half is nearly constant across the course (shared block additive share median 0.917762) and constant within a question, so it cannot tell PRESENT slots from ABSENT slots.
  - The only part that changes from slot to slot is q: exactly 0.5 of the squared norm, a sha256 code that is new for every held slot (max cosine median 0.375, the same as random).
- Corrected statement (MEASURED + INFERRED): slot identity enters only as an opaque hash of its name. Learning a per-bit answer means memorising that hash. Any never-seen name gets chance, whether it sits in a new world or a trained one. Held worlds just guarantee that every name is new.
- INFERRED, not measured: "impossible for ANY learner, ALL kinds". It follows from the hash construction (binding.py:198-202) plus the q-blind ceiling. What stays possible is input-blind priors from the packet's question-kind content, such as the published reach → DIRECT gain. That is not transfer of world knowledge.
