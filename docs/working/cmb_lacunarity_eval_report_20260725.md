# CMB Lacunarity Detection — Eval Report

Generated: `2026-07-26T06:46:00.987904+00:00`
Reviewer identity: `claude_opus5_local_reviewer_20260725`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Result: `PASS`
Cases passed: `42/42`
 - Section A, 40-cell structural absence detection: `19/19`
 - Section B, shipped gap-map detector, behavioural: `12/12`
 - Section C, published Chapter 21 parts and parameter gates: `11/11`
Unenforced properties found: `7`

## What This Run Claims

Exactly one thing: **that absence over the 40-cell cognitive state universe is
detectable, with working negative controls, using the real CAS compiler's
meta-set layer** — and, separately, that the shipped 10-operator / 4-domain /
7-drive gap-map detector runs and behaves as specified except where noted below.

Every Section A case is run through the real CAS compiler at
`noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`.
Deliberate-gap cases assert the exact missing-cell set **by identity**, not by
count. False-positive cases assert that complete 40-cell banks — in two
orderings — produce zero lacunae and satisfy both `CoverOf` and `PartitionOf`.
Section B is real execution of `api/pipeline/lacunarity.py` and of its Rust
source of truth via `cargo test`. Section C runs the published Chapter 21
capacitor cells through the real PCBA parser and CAS-leaf compiler.

## Out Of Scope, Deliberately

**Out of scope, deliberately. There is no memory board in the loop, because none
exists.** This run does not read charge off a capacitor, does not exercise the
~0.05 lacunarity threshold, does not exercise the leakage decay schedule, and
does not distinguish a never-written cell from a charged-then-leaked one — the
write-history mechanism Chapter 21 line 227 attributes to the board is **not
implemented anywhere in this repository**, so that half of the claim could not be
tested at all. Not partially. Not by proxy.

This run also does **not** use the shipped gap-map detector
(`cas-engine/src/scoring/lacunarity.rs` and its Python mirror) as evidence for
the chapter's 40-cell claim. That detector works at 10-operator / 4-domain /
7-drive granularity and reports "absent" as *below a 4.0 threshold on a 0–10
scale*, which is a materially weaker notion than the chapter's "empty".
Substituting it for the claimed instrument would be substituting a coarser
instrument for the claimed one.

Section A is **structural**: it tests set-completeness over the 40-state
universe. It is a real execution of a real compiler, but the thing being
executed is set algebra, not a board reading charge off forty capacitors.
Section B is **behavioural**: a real absence detector really runs on real
vectors. The report never lets the first stand in for the second, and the
`test_level` field on every JSONL record records which is which.

Nothing here licenses a claim about deployed behaviour, about measured
retrieval, or about a system's actual accumulated experience. Chapter 21's own
Honesty callout (line 217) already scopes every charge and leakage number as
arithmetic on chosen parameters rather than telemetry, and this run does not
change that.

## Pass/Fail Thresholds

- Section A pass rate must be `1.0`: every deliberate gap identified by exact
  cell identity, every complete bank producing zero lacunae, every malformed
  bank rejected rather than silently registering an absence.
- Section B pass rate must be `1.0`.
- Section C pass rate must be `1.0`: every published Chapter 21 cell compiles
  clean and every out-of-range `leakage` is rejected.
- Gap probes are findings, never passes. They do not contribute to the result.

## Section A — 40-Cell Structural Absence Detection (real CAS compiler)

| Case | Category | Level | Expected | Observed | Passed |
|---|---|---|---|---|---:|
| `cmb_universe_cardinality_is_40` | `universe_integrity` | structural | \|States\| = 40 | \|States\| = 40 | `true` |
| `cmb_complete_bank_covers` | `false_positive_complete_bank` | structural | accepted | accepted | `true` |
| `cmb_complete_bank_covers_reversed` | `false_positive_complete_bank` | structural | accepted | accepted | `true` |
| `cmb_complete_bank_zero_lacunae` | `false_positive_complete_bank` | structural | lacuna set = [] | lacuna set = [] | `true` |
| `cmb_complete_bank_partitions` | `false_positive_complete_bank` | structural | accepted | accepted | `true` |
| `cmb_single_cell_gap_p3_identity` | `deliberate_gap` | structural | lacuna set = ['P3'] | lacuna set = ['P3'] | `true` |
| `cmb_single_cell_gap_p3_cover_fails` | `deliberate_gap` | structural | rejected, error names missing ['P3'] | rejected, names_p3=True | `true` |
| `cmb_39_cell_bank_partition_fails` | `deliberate_gap` | structural | rejected | rejected | `true` |
| `cmb_whole_domain_gap_p_identity` | `deliberate_gap` | structural | lacuna set = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9'] | lacuna set = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9'] | `true` |
| `cmb_whole_domain_gap_p_cover_fails` | `deliberate_gap` | structural | rejected naming P0..P9 | rejected | `true` |
| `cmb_whole_noetic_gap_6_identity` | `deliberate_gap` | structural | lacuna set = ['C6', 'E6', 'O6', 'P6'] | lacuna set = ['C6', 'E6', 'O6', 'P6'] | `true` |
| `cmb_chapter21_worked_bank_lacunae` | `deliberate_gap` | structural | cardinality 36; all P cells except P3 present | cardinality 36; p_pattern_ok=True | `true` |
| `cmb_membership_charged_cells` | `per_cell_assertion` | structural | holds=True for P3,E6,C8,E2 | P3:holds=True, E6:holds=True, C8:holds=True, E2:holds=True | `true` |
| `cmb_membership_gap_cells` | `per_cell_assertion` | structural | holds=True for P0,P9,C0,O9 | P0:holds=True, P9:holds=True, C0:holds=True, O9:holds=True | `true` |
| `cmb_bank_subset_of_universe` | `per_cell_assertion` | structural | holds=True | holds=True | `true` |
| `cmb_typo_domain_not_a_lacuna` | `negative_control` | structural | rejected | rejected | `true` |
| `cmb_out_of_range_noetic_not_a_lacuna` | `negative_control` | structural | rejected | rejected | `true` |
| `cmb_partition_duplicate_cell_rejected` | `negative_control` | structural | rejected | rejected | `true` |
| `cmb_cross_type_family_rejected` | `negative_control` | structural | rejected | rejected | `true` |

## Section B — Shipped Absence Detector (behavioural)

| Case | Category | Level | Expected | Observed | Passed |
|---|---|---|---|---|---:|
| `gapmap_all_high_no_false_gaps` | `false_positive_detector` | behavioural | three empty lists + 'No significant gaps detected' | ops=[] doms=[] drvs=[] void='No significant gaps detected' | `true` |
| `gapmap_absent_operators_exact` | `deliberate_gap` | behavioural | absent_operators == [3, 6] | absent_operators == [3, 6] | `true` |
| `gapmap_absent_domain_exact` | `deliberate_gap` | behavioural | absent_domains == ['P'] | absent_domains == ['P'] | `true` |
| `gapmap_absent_drives_exact` | `deliberate_gap` | behavioural | absent_drives == [2, 4, 6] | absent_drives == [2, 4, 6] | `true` |
| `gapmap_drive_void_silent_at_three` | `reporting_threshold` | behavioural | largest_void does not start with 'Drive void' | largest_void = '0 operator(s), 0 domain(s), 3 drive(s) below threshold' | `true` |
| `gapmap_drive_void_fires_at_four` | `reporting_threshold` | behavioural | largest_void starts with 'Drive void' | largest_void = 'Drive void: 4 motivational drives absent (Unity, Wisdom, Connection, Structure)' | `true` |
| `gapmap_operator_threshold_strictly_exclusive` | `reporting_threshold` | behavioural | absent_operators == [1] | absent_operators == [1] | `true` |
| `gapmap_monotone_in_absence` | `invariant` | behavioural | absent set non-decreasing across the sweep | monotone=True | `true` |
| `gapmap_uses_canonical_noetic_names` | `canonical_naming` | behavioural | largest_void names ['Idea', 'Mind', 'Positive', 'Negative', 'Above/Cause'] | largest_void = 'Critical operator void: 5 operators absent (Idea, Mind, Positive, Negative, Above/Cause)' | `true` |
| `gapmap_short_domain_list_no_false_negative` | `robustness` | behavioural | absent_domains reports the 2 unsupplied domains | absent_domains=['E', 'O'] void='Domain void: 2 processing domains inactive (E, O)' | `true` |
| `gapmap_short_drive_list_no_crash` | `robustness` | behavioural | no exception | raised=False  | `true` |
| `rust_lacunarity_unit_tests_pass` | `shipped_detector` | behavioural | cargo reports 0 failed | test result: ok. 15 passed; 0 failed | `true` |

## Section C — Published Chapter 21 Parts And Parameter Gates

| Case | Category | Level | Expected | Observed | Passed |
|---|---|---|---|---|---:|
| `cmb_published_cell_p3` | `published_bom` | structural | accepted | accepted | `true` |
| `cmb_published_cell_e6` | `published_bom` | structural | accepted | accepted | `true` |
| `cmb_published_cell_c8` | `published_bom` | structural | accepted | accepted | `true` |
| `cmb_leakage_lower_boundary` | `parameter_gate` | structural | accepted | accepted | `true` |
| `cmb_leakage_upper_boundary` | `parameter_gate` | structural | accepted | accepted | `true` |
| `cmb_leakage_datasheet_nominal_max` | `parameter_gate` | structural | accepted | accepted | `true` |
| `cmb_leakage_above_range_rejected` | `parameter_gate` | structural | rejected | rejected | `true` |
| `cmb_leakage_negative_rejected` | `parameter_gate` | structural | rejected | rejected | `true` |
| `cmb_leakage_nan_rejected` | `parameter_gate` | structural | rejected | rejected | `true` |
| `cmb_leakage_inf_rejected` | `parameter_gate` | structural | rejected | rejected | `true` |
| `cmb_reference_circuit_crc_clean` | `shipped_design` | structural | 0 CRC errors | 0 CRC errors | `true` |

## Failures Observed

None.

## Unenforced Properties

These are properties the book's prose leans on that the toolchain does not
enforce, or mechanisms the book describes that do not exist. They are recorded
as findings, never as passes. Each carries its disposition.

### `cmb_scan_statement_not_implemented`

Chapter 21 line 178 is the ONLY code expression of the lacunarity claim: `scan lacunarity: bank where charge < 0.05 -> lacuna_report;`. Run it through both toolchains.

- Hoped `accepted`, observed `rejected by both`.
- Evidence: `{"statement": "scan lacunarity: bank where charge < 0.05 -> lacuna_report;", "cas_compiler": "parsing@15: unexpected token ':'", "pcba_parser": "Expected Component< ... > syntax"}`
- **Disposition:** RECORDED AS A GAP, NOT WAIVED. The mechanism the chapter publishes does not exist in any parser in this repository, so the lacunarity claim could not be tested at the level the receipt asks for. This is not a defect in the toolchain and not a false claim about shipped tooling --- Appendix C line 8 already discloses that the CAS compiler is a design in the implementation-blueprint roadmap, and Chapter 21 makes no compile claim. It IS an internal-consistency defect between Chapter 21 / Appendix D and Appendix C: see the next probe. Section A of this run substitutes set-completeness detection over the 40-state universe, which is a DIFFERENT and weaker property, and the report says so.

### `cmb_scan_absent_from_book_grammar`

Appendix C is the book's own CCDL language reference. Check whether the `scan` statement form used in Chapter 21 line 178 and Appendix D line 460 appears in the reserved-word list, in either `circuit_item` EBNF production, or anywhere in Appendix C at all.

- Hoped `present in Appendix C`, observed `reserved_words=False, circuit_item_ebnf=False, occurrences_anywhere_in_appendix_c=3`.
- Evidence: `{"reserved_block": "circuit  board  input  output  node  cjt  feedback  probe  layer  via  let", "circuit_item_productions": ["circuit_item  ::= io_decl | node_decl | component_decl | feedback_decl | probe_decl | let_decl", "circuit_item   ::= io_decl | node_decl | cjt_decl | component_decl\n                 | feedback_decl | probe_decl | let_decl"], "scan_occurrences_in_appendix_c": 3}`
- **Disposition:** BOOK DEFECT, FLAGGED FOR CORRECTION. Chapter 21 line 178 and Appendix D lines 422/459-460 publish a statement form the book's own grammar does not admit; the same is true of the surrounding `charge`, `select`, `discharge`, `refresh` and `decode` lines in the Chapter 21 listing. Recommended fix: either add these statement forms to the Appendix C reserved words and EBNF, or annotate the Chapter 21 listing as pseudo-CCDL beyond the Appendix C grammar. This run does not close that defect. Noted in passing while extracting the evidence, and offered as an observation rather than a lacunarity finding: Appendix C states the `circuit_item` production twice (lines 129 and 492) and the two statements differ --- the first omits `cjt_decl`. Neither admits `scan`.

### `cmb_write_history_absent`

Chapter 21 line 227 (Bench Note) and line 275 (Failure Modes, Detection column) state in the present tense that the board separates a true lacuna from a faded memory 'by tracking whether the cell has ever been written'. Search the cognitive-memory code paths for any per-cell write-history or never-written flag.

- Hoped `a per-cell write-history mechanism exists`, observed `absent: 17 hits across 3 files, all unrelated (settings.py, backup_restore.py, economic_calendar_feed.py)`.
- Evidence: `{"terms": ["ever_written", "write_history", "never_written", "was_written", "write_count", "written_at"], "total_hits": 17, "hit_files": ["cas-forex/api/routes/settings.py", "cas-forex/cas_forex/backup_restore.py", "cas-forex/cas_forex/economic_calendar_feed.py"], "hits_by_term": {"ever_written": [], "write_history": [], "never_written": [], "was_written": [], "write_count": ["cas-forex/cas_forex/backup_restore.py:74: overwrite_count: int", "cas-forex/cas_forex/backup_restore.py:317: overwrite_c`
- **Disposition:** BOOK OVERCLAIM --- THE MAIN FINDING OF THIS RUN, NOT WAIVED. No write-history mechanism exists: not in the chapter's own CCDL build (lines 146-183 declare no written flag and no second output), not in the datasheet (lines 257-266 list no write-history parameter), not in Appendix C, and not in code. Every hit returned by this search is unrelated (backup_restore.py overwrite counters, economic_calendar_feed.py cache timestamps, api/routes/settings.py). The empty-vs-leaked separation is the hardest and most important false-positive control an absence detector can have, and it cannot be tested, cannot be partially tested, and cannot be approximated here. Recommended fix: rewrite Chapter 21 line 227 as a design requirement ('a CMB must record, per cell, whether it has ever been written; the listing above does not yet do so') and either add the state to the CCDL listing or say plainly that it is absent. Line 275's Detection column instructs the reader to use a facility the board does not provide and needs the same treatment.

### `cmb_lacunarity_threshold_constant_absent`

Chapter 21 line 266 datasheet: 'Lacunarity threshold | --- | ~0.05 | Charge floor below which a cell is reported empty.' Search code for that constant or any `lacuna_report` terminal.

- Hoped `a ~0.05 charge-floor constant exists`, observed `absent: 1 hit(s), none a charge floor`.
- Evidence: `{"hits": {"lacunarity[_ ]?threshold": ["cas-forex/cas_forex/harvester.py:191: sig.conditions = {\"lacunarity_threshold\": 1.5, \"loss_count\": len(high_lac)}"], "lacuna_report": [], "charge\\s*<\\s*0\\.05": []}}`
- **Disposition:** RECORDED AS A GAP, NOT WAIVED. The ~0.05 threshold exists only as a number in the book's datasheet. Nothing in code reads charge and compares it to a floor, so the threshold's behaviour --- including the boundary cases an eval would normally pin down --- was not exercised by this run at all. The single hit is unrelated: `cas_forex/harvester.py:191` sets a forex-domain `lacunarity_threshold` of 1.5 over (symbol x timeframe x regime) cells. Same word, different universe. Listed so a later reader does not mistake it for CMB machinery --- the same caution applies to `cas_forex/nested_lacunarity.py`, `regime_sim.py` and `forecast/integrity.py`, none of which detect cognitive-state absence.

### `cmb_capacitor_bank_absent`

Chapter 21 builds its whole claim on 'a bank of 40 capacitors, one per cognitive state', each holding charge and leaking. Search for any object that instantiates 40 cells and holds per-cell charge.

- Hoped `a 40-cell capacitor bank exists`, observed `absent: 0 hits; the shipped CMB is 2 CJT expressions and 1 via`.
- Evidence: `{"hits": {"capacitor_bank": [], "CapacitorBank": [], "class\\s+\\w*Bank\\b": []}, "shipped_cmb_cjts": ["name=None cause='experience' bias='^1^C_{F2}|A' effect='^5^E_{F4}|f' beta=1.0 saturation=None cutoff=None region=<CjtRegion.UNKNOWN: 'unknown'>", "name=None cause='^5^E_{F4}|f' bias='^7^C_{F6}|A' effect='^5^E_{F4}|f' beta=1.0 saturation=None cutoff=None region=<CjtRegion.UNKNOWN: 'unknown'>"]}`
- **Disposition:** RECORDED AS A GAP, NOT WAIVED. `cas_forex/ccb_designs.py:76 build_cmb()` is the CMB that exists in code: two CJT expressions and one address-decode via. There is no bank to scan, no charge, and no leakage decay loop, so every behavioural statement in Chapter 21 about charge levels is unreachable at any effort level short of building the board. A further blocker for whoever builds it: `cas-engine/src/ontology/states.rs` `CognitiveStateVector::from_slice` rejects any component <= 0 with `NonPositiveProbability` (open-simplex Correction 4), so the engine's canonical 40-dimensional state object CANNOT represent an empty cell. A charge-vector type that permits zeros does not exist, and the book never says so.

### `cmb_refresh_oscillator_no_cas_leaf`

Chapter 21 line 131/172 publishes the refresh oscillator `Oscillator< Phi< select_cell, discharge_partial, recharge >, frequency=0.0001 >`. Under the CSB run's own false-positive convention every published BOM line must compile clean.

- Hoped `accepted`, observed `parses=True, compiles_clean=False`.
- Evidence: `{"expression": "Oscillator< Phi< select_cell, discharge_partial, recharge >, frequency=0.0001 >", "parse": "kind=oscillator params={'frequency': 0.0001}", "compile": "valid=False checked_leaves=0 reason=No compiler-checkable CAS expressions found in PCBA component."}`
- **Disposition:** RECORDED AS A GAP, NOT WAIVED, AND NOT COUNTED AS A PASS. The line parses but yields valid=False from `compile_pcba_component_expression` because its `Phi<...>` holds bare identifiers (`select_cell`, `discharge_partial`, `recharge`) rather than CAS states, so there is no compiler-checkable CAS leaf. Two candidate fixes, both for the book rather than the toolchain: express the trajectory in CAS states (e.g. `Phi< ^1^C, ^5^E, ^7^C >`), or annotate the line as pseudo-CCDL. Related and recorded here so a later reader does not trip on it: the Chapter 21 line 74 encoder trajectory `Phi< ^8^C_{F2}|A, ^6^E_{F4}|A, ... >` uses the book-CCDL comma form, while the shipped CAS compiler's fractal literal is colon-separated Noetic indices (`Φ⟨8:6:3:9⟩`). The book is internally consistent with Appendix C line 518; the divergence is between book-CCDL and the shipped compiler.

### `cmb_datasheet_leakage_range_not_enforced`

The Chapter 21 datasheet (line 261) gives cell leakage a nominal range of 0.0 - 0.5 /unit time. Check whether a value outside that nominal range is gated.

- Hoped `rejected`, observed `accepted`.
- Evidence: `{"expression": "Capacitor< ^3^P_{F7}|f, C=200, leakage=0.9 >", "detail": "kind=capacitor params={'C': 200, 'leakage': 0.9}"}`
- **Disposition:** ACCEPTED AS A LIMIT. `pcba_syntax._validate_params` gates `leakage` to [0, 1], which is the correct hard bound; the datasheet's 0.0-0.5 is a nominal design range, not a hard limit, and a capacitor on another board may legitimately sit above it. Recorded so that no reader mistakes the passing parameter-gate cases in Section C for enforcement of the datasheet's nominal range --- they are not.

## Receipt Recommendation

`cmb_lacunarity_eval_pass` should **not** be signed off this run as though it
closed the Chapter 21 claim. The evidence here covers set-completeness detection
over the 40-state universe and the behaviour of a coarser shipped detector; it
does not cover the memory board's charge-threshold scan and does not touch the
empty-vs-leaked separation at all. That is consistent with the already-signed
`cmb_claim_review_signed`, which approves the CMB "as an architectural
description, explicitly not as a measured retrieval or lacunarity result."

The recommended disposition is to leave the receipt **open** and publish this run
as a scoped structural artifact with its gaps dispositioned in the book. If it is
signed at all, the `signed_reason` must state that the evidence covers
set-completeness detection over the 40-state universe and explicitly not the
board's charge-threshold scan or its never-written/leaked separation.

## Mitigations And Limits

- The allowed claim is limited to what this artifact observed.
- This evidence does not unlock live trading and is not a broker `ACCEPT` path.
- This evidence does not support behavioural, legal, governance, privacy, or
  human-factors claims about the CMB.
- No failing case in this run was closed by weakening the case. The failures and
  gaps are reported as they were observed.

## Raw Evidence

- Path: `docs\working\cmb_lacunarity_eval_raw_20260725.jsonl`
- SHA-256: `9778518bfe677b7df90d2bd6a00be3969dc0cca9f308361dedd06d0c3633efef`
- JSONL records: `49` (`42` cases, `7` gap probes)
