# CNCM AUDIT MANIFEST v0.1

Scope: the learning accomplishments on branch `phase4-hybrid-cortex`,
head commit `7b7c19c9`. Every path below is relative to
`cas_only_reasoner/`. Baseline frozen at `2526360b`.

How to verify anything here in one command per lane:

```bash
cd <LANE> && python -m pytest tests -q
```

The stores are digest-checked JSON: tampering trips a typed refusal
on load, so the store files are self-authenticating evidence.

---

## 1. WHAT IT WAS TAUGHT / WHAT IT LEARNED

"Taught" = what a live teacher model presented. "Learned" = what
passed the acceptance ladder, is durably promoted in a persistent
store, and is demonstrable live. In this machine the two are the
same set by construction: nothing is "learned" (promoted) that did
not survive the frozen examiner.

Three languages. Mathematics (24/24 episodes) and Python (7/7
episodes) were taught entirely by AWS Bedrock `qwen.qwen3-32b-v1:0`
on `bedrock:us-west-2` (with a `deepseek.v3-v1:0` critic on one
committee lesson). English is mixed provenance: 27 of the 36
constructions were taught by a live model teacher (26 by the Bedrock
32B; 1, `negated_present_transitive`, by local
`Qwen/Qwen2.5-3B-Instruct`); the other 9 came from seed/curriculum
teaching episodes, not a live model (see
`CAS_APPRENTICE_v0.1/output/LEARNING_LEDGER.md` §2 and §4):

| Language | What, exactly | Scope (honest) | Durable count |
|---|---|---|---|
| **English (natural language)** | a construction grammar: plural/negation/passive/questions/coordination/disjunction/relative clauses/possessives/locatives/comparatives/quantifiers/temporal/why-questions/commands/pronoun resolution/prohibitions + class rules + the math and wh bridges | a **controlled, small vocabulary** (~30 words), NOT broad English | **36 constructions** |
| **Mathematics (CAS-Math, a formal language)** | MATH-L0..L10: counting, comparison, the four operations, fractions, algebra/distribution, linear equations, functions, coordinate geometry, calculus (derivatives/integrals/sequences), 2×2 matrices, probability, statistics, formal axioms, proof search, conjecture discovery | the **exact-rational / polynomial fragment**; transcendental trig/analysis is out of scope, disclosed | **24 skills** |
| **Python (programming)** | CODE-L0..L4: read/trace, pure functions, control flow, contracts/testing, debugging/repair | a **pure-function sandboxed subset** (no attributes, no imports); JSON-Schema / CAS-KIR / TypeScript / Rust from the goal's sequence are NOT yet taught | **7 procedures** |

It was NOT taught: broad conversational English, transcendental
mathematics, or any language beyond Python (JSON Schema, CAS/CCDL,
TypeScript, Rust remain future work per PROGRAMMING LESSON.txt).

---

## 2. AUDIT CLAIMS + THE FILES TO VERIFY THEM

Each claim lists: **[M]** machinery/source, **[E]** sealed live
evidence, **[T]** the test that locks it, **[S]** the persistent
store or ledger.

### TYPE A — NATURAL LANGUAGE (CCB-L1 apprenticeship)

**A1. 36 English constructions are durably promoted, each with
provenance and a rollback path.**
- [S] `CCB_L1_v0.1/fixtures/seed_grammar.json` (36 rules, revision 36, `store_digest`)
- [S] `CAS_APPRENTICE_v0.1/output/LEARNING_LEDGER.md` (derived entirely from the stores)
- [M] `CCB_L1_v0.1/lang/constructions.py`, `CCB_L1_v0.1/lang/apprentice.py`

**A2. Learning is real: unseen sentences parse to the exact meaning
(before UNSUPPORTED → after UNDERSTOOD), never memorized.**
- [E] `CAS_APPRENTICE_v0.1/output/curriculum_qwen.qwen3-32b-v1_0_*.json` (9 sealed episodes: before/after transcripts, held-out cases) plus `CAS_APPRENTICE_v0.1/output/curriculum_round1.json` (the round-1 curriculum episode)
- [T] `CAS_CORTEX_v0.1/tests/test_cortex_gates.py::test_runtime_canary_no_construction_forgotten` (33 family probes)
- [S] `CAS_APPRENTICE_v0.1/output/LEARNING_LEDGER.md` §3 (live unseen-sentence check at generation)

**A3. A live model teacher's defective lessons are REJECTED by the
ten-stage acceptance ladder (teacher confidence grants nothing).**
- [M] `CCB_L1_v0.1/lang/apprentice.py` (`learn()` ten stages)
- [E] `CAS_APPRENTICE_v0.1/output/reconstruction_curriculum_overwrite_20260828.json` (`REJECTED_POSITIVE_EXAMPLES`, `REJECTED_REGRESSION`) and `CAS_APPRENTICE_v0.1/output/live_teacher_episode_qwen2_5-*.json` (`REJECTED_SCHEMA` x6, sealed pass-or-fail)
- [T] `CAS_APPRENTICE_v0.1/tests/test_apprentice_board.py`

**A4. The first LIVE MULTI-TEACHER COMMITTEE lesson: a second model
(deepseek) reviews and votes; any reject blocks, typed.**
- [M] `CAS_APPRENTICE_v0.1/apprentice/board.py` (committee validation, HIGH_IMPACT_DOMAINS)
- [E] `CAS_APPRENTICE_v0.1/output/committee_LIVE_L028_committee_prohibition.json`
- [T] `CAS_APPRENTICE_v0.1/tests/test_apprentice_board.py` (committee composition/reject-blocks tests)

**A5. Morphology is conservative — an unknown verb form REFUSES
rather than inventing a lemma (the 'carrie' defect, closed).**
- [M] `CCB_L1_v0.1/lang/constructions.py` (`MorphTable.analyze`, `known_base` guard)
- [S] `CCB_L1_v0.1/fixtures/seed_morphology.json`
- [T] `CCB_L1_v0.1/tests/test_apprenticeship.py`, `CCB_L1_v0.1/tests/test_roundtrip.py`

### TYPE B — CONVERSATION (CCB-D1, CONV v0.1 + v0.2)

**B1. The machine remembers what the user asserted and answers with
the source preserved, never laundered into verified knowledge.**
- [M] `CCB_D1_v0.1/dialogue/board.py`, `CCB_D1_v0.1/dialogue/intents.py`, `CCB_D1_v0.1/dialogue/assertions.py`
- [D] `CCB_D1_v0.1/CONV_ACCEPTANCE_LAW_v0.1.md` (the frozen law, owner-verbatim)
- [T] `CCB_D1_v0.1/tests/test_conv_battery.py` (20 goal rows + the cardinal invariant)

**B2. Acknowledgment happens ONLY after an atomic commit; a store
fault yields a typed failure, never a fake "remembered".**
- [M] `CCB_D1_v0.1/dialogue/intents.py` (`TransactionCoordinator`)
- [T] `CCB_D1_v0.1/tests/test_conv_battery.py::test_store_fault_is_typed_and_never_fake_acknowledged` and `::test_acknowledgment_iff_committed_record`

**B3. DERIVED common ground (CONV v0.2): "given the two things you
told me, yes, Milo is an animal" with the full premise chain, no
symmetry, no free transitivity, never verified.**
- [M] `CCB_D1_v0.1/dialogue/board.py` (`derive_is_a`, `matching_class_facts`)
- [T] `CCB_D1_v0.1/tests/test_conv_derived.py` (Milo derivation, two-hop, no-symmetry, distinct-from-verified)

**B4. Corrections supersede (never delete); unmarked contradictions
ASK; retraction keeps the audit record.**
- [M] `CAS_CORTEX_v0.1/cortex/router.py` (`_correction_turn`, `_polar_response_turn`, `_retraction_turn`)
- [T] `CCB_D1_v0.1/tests/test_conv_audit_regressions.py`, `CCB_D1_v0.1/tests/test_conv_derived.py`

**B5. The CONV adversarial audit: 10 confirmed findings, all fixed
and regression-locked (the negatives are load-bearing).**
- [T] `CCB_D1_v0.1/tests/test_conv_audit_regressions.py` (one named test per finding)
- [ref] `spec sheet.txt` → "CONV ADVERSARIAL AUDIT" section

### TYPE C — MATHEMATICS (CAS_MATH_LADDER, MATH-L0..L10)

**C1. 24 skills durably promoted L0→L10, every one taught live;
before-probe CANNOT, after SOLVED.**
- [S] `CAS_MATH_LADDER_v0.1/fixtures/math_skills.json` (24 skills, revision 24)
- [E] `CAS_MATH_LADDER_v0.1/output/math_lesson_*.json` (24 sealed episodes)
- [S] `CAS_MATH_LADDER_v0.1/output/MATH_LEARNING_LEDGER.md` (24/24 live unseen PASS)

**C2. The examiner is EXACT and independent: derivatives graded by
re-derivation, integrals differentiate back or refuse, solutions
verified by substitution into the original.**
- [M] `CAS_MATH_LADDER_v0.1/mathschool/ladder.py`, `.../advanced.py`, `.../student.py`
- [D] `CAS_MATH_LADDER_v0.1/MATH_ACCEPTANCE_LAW_v0.1.md`
- [T] `CAS_MATH_LADDER_v0.1/tests/test_math_ladder.py::test_full_ladder_promotes_l0_through_l10`

**C3. The counterexample generator ATTACKS: a false rule dies with an
exact witness; a "common mistake" that is true is a typed defect.**
- [M] `CAS_MATH_LADDER_v0.1/mathschool/sdg.py` (`attack_equation`, `verify_identity`)
- [T] `CAS_MATH_LADDER_v0.1/tests/test_math_ladder.py::test_false_rewrite_rule_killed_by_counterexample`, `::test_true_statement_offered_as_mistake_is_rejected`

**C4. L9 proof search over the student's OWN promoted rules, every
step independently re-verified; false-schema steps rejected.**
- [M] `CAS_MATH_LADDER_v0.1/mathschool/advanced.py` (`prove_equal`, `examiner_verify_proof`)
- [T] `CAS_MATH_LADDER_v0.1/tests/test_math_ladder.py::test_proof_steps_cannot_smuggle_false_schemas`

**C5. L10 discovery: nine identities discovered & proved novel-to-
library, 22 refuted with exact witnesses; unproved = CONJECTURE.**
- [M] `CAS_MATH_LADDER_v0.1/mathschool/advanced.py` (`discovery_round`, `examiner_verify_discovery`)
- [E] `CAS_MATH_LADDER_v0.1/output/math_lesson_conjecture_discovery.json`
- [T] `CAS_MATH_LADDER_v0.1/tests/test_math_ladder.py::test_discovery_examiner_rejects_non_novel_and_false_claims`

### TYPE D — PROGRAMMING (CCB-P1, CODE-L0..L4)

**D1. 7 Python procedures durably promoted, taught live under
compiler-and-test authority; before CANNOT, after SOLVED.**
- [S] `CCB_P1_v0.1/fixtures/code_procedures.json` (7 procedures, revision 7)
- [E] `CCB_P1_v0.1/output/code_lesson_*.json` (7 sealed episodes)
- [M] `CCB_P1_v0.1/codeboard/ladder.py`

**D2. The SANDBOX refuses forbidden effects BEFORE execution (file
write, network, import, introspection) — the crown-jewel security.**
- [M] `CCB_P1_v0.1/codeboard/sandbox.py` (`static_gate`, whitelisted builtins, step budget)
- [T] `CCB_P1_v0.1/tests/test_code_battery.py` (file-write / network rows), `CCB_P1_v0.1/tests/test_code_audit_regressions.py::test_generator_frame_walk_escape_refused_before_execution`

**D3. The PCBA walk-down finds the FIRST failing state (step, line,
variable, both values); repair is MINIMAL (one line, whole-battery
verified).**
- [M] `CCB_P1_v0.1/codeboard/tracer.py` (`first_divergence`), `.../repair.py`
- [T] `CCB_P1_v0.1/tests/test_code_battery.py::test_off_by_one_first_incorrect_iteration_located`, `::test_wrong_variable_mutation_located_by_name`, `::test_minimal_patch_and_regression`

**D4. Teacher confidence is not correctness: broken teacher code is
rejected, a memorizing lookup table is refused, evaluator-tampering
packets are refused.**
- [M] `CCB_P1_v0.1/codeboard/packets.py`, `.../spec.py` (`memorization_defects`)
- [T] `CCB_P1_v0.1/tests/test_code_battery.py::test_teacher_broken_code_rejected_despite_confidence`, `::test_test_tampering_is_evaluator_contamination`, `CCB_P1_v0.1/tests/test_code_audit_regressions.py::test_memorizing_lookup_table_refused`

**D5. The CCB-P1 adversarial audit: 10 confirmed findings (7 cardinal,
incl. a full sandbox escape), all fixed and regression-locked.**
- [T] `CCB_P1_v0.1/tests/test_code_audit_regressions.py` (one named test per sandbox/authority finding)
- [ref] `spec sheet.txt` → "CCB-P1 / CONV v0.2 ADVERSARIAL AUDIT" section

---

## 3. WHOLE-PROGRAM RECEIPT

18 lanes, **440 local tests, 0 failures** (2026-08-29). To reproduce
the full sweep:

```bash
cd cas_only_reasoner
for d in CAS_RRK_v0.1 CAS_RLP_v0.1 CCB_M1_v0.1 CCB_L1_v0.1 CAS_SEM_v0.1 CAS_WORKBENCH_v0.1 CRQS_v0.1 CCB_T1_v0.1 CAS_OHM_INSTRUMENT_v0.1 CORTEX_H2H_v0.1 CAS_LTG_v0.1 CAS_SM_v0.1 CNCM_G10_v0.1 CAS_CORTEX_v0.1 CAS_APPRENTICE_v0.1 CCB_D1_v0.1 CAS_MATH_LADDER_v0.1 CCB_P1_v0.1; do (cd "$d" && python -m pytest tests -q); done
```

The living master record with every claim's status and every
disconfirmed result is `spec sheet.txt`. Disclosed residual limits
(programming): OS-level memory/CPU isolation and an unpredictable
external held-out oracle are the honest ceilings of a fully
in-process, fully-public-seed examiner.
