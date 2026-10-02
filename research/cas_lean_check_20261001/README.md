# Lean check of the CAS compiler (2026-10-01)

**Owner request (2026-10-01):** "use LEAN (https://lean-lang.org/) to check the logic of CAS programming
language / THE LATEST CAS COMPILER".

**What was checked:** `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py` at commit `8a3555b8`
(git blob `439c4908df2718a3ca1e1ff40bda63020cf71efa`, 6,415 lines). This is the newest compiler on any branch:
no commit after `8a3555b8` touches the file. Both of its arithmetic paths were checked: the Python fallback, and
the Rust engine `cas_engine` (built from `cas-engine/` at the same commit with maturin 1.15.0, rustc 1.99.0).

**Tool:** Lean 4.19.0 (Lake 5.0.0), core library only (no Mathlib). Everything heavy ran on AWS ("Cloud job").

## How the check works

1. **A Lean copy of the rules.** `lean/CasCheck/Core.lean` and `lean/CasCheck/Nesting.lean` copy the
   compiler's rules: `∘`, `×`, `÷`, `->`, `<-`, `<->`, `+`, `-`, the involution pairs, state numbering, the
   Nesting Operator's canonical form (`_nesting_reduce`) and the Dual Cancellation criterion (`_nesting_criterion`).
2. **Is the copy faithful?** `export_compiler_facts.py` compiles **76,611 real CAS programs** with the real
   `compile_expression`, giving **76,311 answer records**. `lean/CasCheck/Differential.lean` compares every record
   with the Lean copy. This was done twice: once on the Python fallback, once with the Rust engine installed.
3. **What do the rules imply?** `lean/CasCheck/Laws.lean`, `Nesting.lean` and `Bounded.lean` prove laws about the copy.
4. **Independent review.** 23 read-only reviewers tried to refute each finding (one code reader and one
   document reader for each of B1-B8, N-A, R1 and the nesting law, plus a coverage critic). The examples listed
   at the end of section 3 were then run on the real compiler, on both engines (`probe_review_claims.py`,
   `results/review_claims_probe_*.json`). A few review statements remain code reading only; they are marked
   "(read)" below. Verdicts: `results/review_verdicts_20261001.json`. A second pair of reviewers then
   fact-checked this README against the evidence; their corrections are applied.

Claim words used below:
- **PROVED**: Lean's kernel checked it, for every case listed, or for every number / every word length when
  marked "general".
- **BOUNDED**: checked for every word up to the stated size by compiled code (`native_decide`).
- **MATCHED**: the Lean copy agreed with the real compiler on every record.
- **RAN**: the real compiler produced this output on both engines; not modelled in Lean.

## 1. The Lean copy matches the real compiler — MATCHED

| Record kind | Records | Agree, Python path | Agree, Rust path |
|---|---:|---:|---:|
| `*`, `∘`, `compose`, `/` on Noetic pairs (Domain C) | 100 | 100 | 100 |
| `->` on every ordered state pair | 1,600 | 1,600 | 1,600 |
| `<-` on every ordered state pair | 1,600 | 1,600 | 1,600 |
| `<->` on every ordered state pair | 1,600 | 1,600 | 1,600 |
| `*` on every ordered state pair (Noetic and Domain) | 1,600 | 1,600 | 1,600 |
| `/` on every ordered state pair | 1,600 | 1,600 | 1,600 |
| `x - y` on every ordered state pair | 1,600 | 1,600 | 1,600 |
| Domain rule of `*` / of `/` | 16 / 16 | 16 / 16 | 16 / 16 |
| `+` dominant state, Noetic pairs | 100 | 100 | 100 |
| `x - x` | 40 | 40 | 40 |
| set facts (`|States|` = 40 ...) | 10 | 10 | 10 |
| alphabet letters as the compiler reads them | 9 | 9 | 9 |
| nested `∘` words, 2-4 terms (all, 9-letter alphabet) | 7,371 | 7,371 | 7,371 |
| nested `∘` words, 5 terms (all) | 59,049 | 59,049 | 59,049 |
| **Total** | **76,311** | **76,311** | **76,311** |

The Python-path and Rust-path answers are identical record by record, all 76,311
(`results/python_vs_rust_records.json`; the 5-term files are also byte-identical). The Rust engine really runs: it answered all
1,000 valid `×` and 400 valid `÷` grid cases, and raised only where Python also refuses (600 Domain ascents,
1,200 cross-Domain divisions), so those programs fail on both paths (`results/rust_probe.json`).
Reports: `results/cascheck_report.txt`, `results/cascheck_rust_report.txt`.

## 2. Laws that hold — PROVED

- The digit rule `(a + b) % 10` is closed, commutative and associative, with `^0` as identity (general proofs
  for the first three). This is the rule behind `×`, `compose(...)` and the legacy `composed_operator` field of
  `∘`. It is NOT a law of the whole `∘` result: its nesting canonical form depends on order (see B2).
- The involution undoes itself; the self-duals are exactly `^0 ^1 ^4 ^7`; the pairs are exactly 2↔3, 5↔6, 8↔9.
- Each (Domain, Noetic) has one state index 0..39 and back (general proof).
- The D0 clause of CLAUDE.md Correction 1 holds: `^0` admits a move only from a state to itself (general
  proof). The other clause, a working admissibility guard before every operator use, does not hold (B1).
- `×` never ascends a Domain. When both bracketings of a `×` chain compile, they give the same Domain and Noetic.
- **Nesting canonical form, surfacing-member-first reading: well defined for words of ANY length**
  (`normal_form_unique_ordered`, general proof, kernel only). After the `^0` terms are dropped, cancel the pairs
  in any order; when nothing more cancels, you are at the Lean copy's canonical form. The copy matched the
  compiler's `canonical_form.surfacing_member_first` on every word of 2-5 terms over the alphabet; for longer
  words, the link to compiler.py rests on reading the code.
- **Nesting canonical form, either-order reading, terms WITHOUT labels: also well defined for every length**
  (`normal_form_unique_either_unlabelled`, general proof, kernel only). This is the setting of the patent text's
  and the Rust engine's "Every fractal has a unique canonical form" (`cas-engine/src/fractals/simplification.rs`,
  bare digits). On that setting the claim holds. It fails once Register labels are carried (finding N-A).
- BOUNDED, all 66,429 words of 1-5 terms over the alphabet `^2^C ^3^C ^2^C|f ^3^E ^8^C ^9^C ^6^C ^0^C ^3^C_{F2}`:
  the canonical form never keeps a pair that still cancels; the compiler's either-order answer is always one of
  the normal forms; with labels removed every word has exactly one either-order form; and the greedy Dual
  Cancellation pairing reports `met` correctly in all three readings (it never misses a full pairing that exists).
  This says nothing about WHICH pairs greedy reports in `resolved`. (`W5_count` only pins the word count.)

## 3. Findings — facts about the code, not rulings on the theory

No reviewer refuted any finding. 16 of the 22 verdicts were CONFIRMED and 6 were PARTLY_CONFIRMED: both
reviewers of B2 and of B6, and one reviewer each of B3 and B7, corrected my first wording, and those
corrections are applied below. B9 came from the coverage critic and has no reviewer pair; it was then proved
and run. Severity is the reviewers' (MAJOR = a check or law users would rely on silently fails; MINOR =
surprising but contained); B9's severity is mine.

| Id | Finding | Status | Severity |
|---|---|---|---|
| B1 | The `admissible` flag of `->` is vacuous: it can be false only when the target is a `^0` state, because the check is handed the target's own Noetic. Same defect in `<-` (flag = left state is not `^0`, or same state) and `<->` (both not `^0`, or same state). Nothing in the compiler reads the flag (read). Reviewers add: the same calling pattern makes the Rust engine's `AdmissibilityViolation` guard unreachable in `multiply_states`, `divide_states` and the Rust language `->` (read). | PROVED: all 1,600 pairs for all three arrows; general proof for `->` and `<-` + MATCHED (all three arrows) | MAJOR |
| B2 | The digit rule `(a+b) mod 10` never cancels a dual pair (`^8∘^9 = ^7`); it drives `×`, `compose`, and the legacy `composed_operator` of `∘`. `÷` cancels every dual pair to `^0`. The same `∘` result also carries `nesting.canonical_form`, which DOES cancel `^8^C ∘ ^9^C` to `^0^C`, so one value reports two answers. Already recorded 2026-09-21 and pinned by tests; conflicts with the book's `(CO-8 ∘ CO-9) ↔ CO-0`. | PROVED + MATCHED | MINOR |
| B3 | The Noetic of `^a ÷ ^b` equals that of `^b ÷ ^a` for every pair. The reported drive does depend on order (left wins a tie): `^2^C_{F2} / ^7^C_{F5}` reports F2, the reverse F5. | PROVED + MATCHED; drive part RAN | MINOR |
| B4 | `^a ÷ ^0 = ^(a//2)`, so `^0` is neutral for `÷` only at `a = 0`. `÷` undoes `×` only for some pairs. | PROVED + MATCHED | MINOR |
| B5 | The involution respects the digit rule for only 46 of 100 pairs: `inv(^2∘^2) = ^4`, `inv ^2 ∘ inv ^2 = ^6`. The language has no involution operation, so no output is wrong; it matters for the axis-N inversion engine. | PROVED | NOTE/MINOR |
| B6 | **Corrected after review.** On a tie, `+` keeps the first-written state as dominant: the two spellings of `^a^C + ^b^C` disagree for 90 of 100 Noetic pairs. The type checker refuses a `+` result as an operand of `×`: `(^2^C + ^3^C) * ^5^C` does not compile (RAN; my first wording said otherwise). Reviewers say `÷`, `∘` and `compose` refuse it too (read). The tie still leaks: `^2^C + ^3^E -> ^5^C` reports `domain_descent_ok` true, the reverse false; `fractal(^2^C + ^3^C, ^5^C)` gives CO-7, the reverse CO-8; through `let x: any = ...`, `x * ^5^C` gives `^7^C` vs `^8^C`. Three-term sums depend on brackets: `^1^C + ^2^C + ^3^C` is dominated by `^3^C`, `^1^C + (^2^C + ^3^C)` by `^1^C`. Documents call `+` commutative and associative. | PROVED (tie, 90/100) + MATCHED (100 pairs) + RAN (leaks) | MINOR |
| B7 | `-` has no zero, and on two single states `x - y` always returns `x`'s weights (all 1,600 pairs). The result also drops Register labels: `^3^C|A - ^3^C|A` gives plain `^3^C`. | PROVED (general) + MATCHED (1,600 pairs) + RAN | MINOR |
| B8 | Whether a `×` chain compiles depends on the brackets (refused at execution): `(^1^E × ^1^C) × ^1^O` refused, `^1^E × (^1^C × ^1^O)` gives `^3^O`; the unbracketed chain is refused. Left grouping accepted for 20 of 64 Domain triples, right for 30, 10 disagree. When both compile, the reported drive can still differ: F3 vs F1 for `(^1^P_{F1}*^1^C_{F2})*^1^E_{F3}` vs `^1^P_{F1}*(^1^C_{F2}*^1^E_{F3})`. Found when Lean refuted the associativity law I first wrote. Documents call `×` a monoid. | PROVED + RAN | MINOR |
| B9 | **New from review.** `-` can leave a weight of exactly 0: `(^1^C + ^2^C) - ^1^C` gives `{11: 0.0, 12: 1.0}`. CLAUDE.md Correction 4 requires every weight to be above 0. | PROVED + RAN | MINOR |
| N-A | Either-order nesting canonical form is **not unique when terms carry Register labels**. Lean example: `^2^C|T ∘ ^3^C ∘ ^2^C|f` can end on `^2^C|f` or on `^2^C|T` (PROVED in the Lean copy). Matched example: `^2^C ∘ ^3^C ∘ ^2^C|f` can end on `^2^C|f` or `^2^C`, and the compiler reports `^2^C|f`. The `cascheck` program counts 542 of 66,429 words with two or more either-order forms (compiled-program output, not a theorem). Without labels the form is unique (PROVED, general), so the forms differ only in the label (short argument, not a Lean theorem). Also `agreed` compares positions, not labels: `^3^C ∘ ^2^C ∘ ^3^C` prints `^3^C` under both readings yet reports `agreed` false (RAN). | PROVED + MATCHED + RAN | MINOR |
| R1 | Rust route: the compiler passes `explicit_drive or 4` as the drive (read: compiler.py line 5193), but `explicit_drive` is a true/false flag: a fresh `^2^C_{F2}` holds `True` (RAN), Rust given `True, True` returns drive 1 = F1 (RAN), and after one `×` the flag holds `1` (RAN). Reviewers add, by reading: no output changes because the visible drive comes from `drive_weights`, so Rust's documented drive rules (e.g. inversion pair → F4) never reach users; and any Rust error is silently replaced by the Python fallback (`except (ValueError, Exception): pass`). The code calls this route "formally verified". | RAN in part (`results/rust_probe.json`) + read | MINOR |

Other facts the review raised and the real compiler confirmed (RAN, both engines; `results/review_claims_probe_*.json`):

- **v7.7 emergent result.** `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω` compiles to state **P9** carrying the label
  `^3^P|Ω`, because `×` adds the digits (3+3+3 = 9). The two-term `(^3^P|A * ^3^P|f) = fused` gives P6.
- **Co-presence drops the Registers.** `^3^P|A + ^3^P|f` gives plain P3 with no Register. (The `|⟨…⟩` form was
  not run; the code keeps a `register_set` key for it, so the two forms probably still differ.)
- **Type checker vs run time.** `(^1^P + ^1^E) -> ^1^C` is refused ("E cannot descend to C": the checker reads the
  alphabetically first Domain of a sum). `(^1^O + ^1^C) -> ^1^C` compiles and reports `domain_descent_ok` false.
  `(^1^P * ^1^C) / ^1^P` passes the type checker and fails at execution. `(^2^C + F_1) -> ^3^C` fails at execution.
- **RPM.** `RPM(^2^C_{F2})` reports completeness 1.0 with a fixed chain text; no prerequisite is checked.
- **Sets and literals.** `^2 ∈ States` holds, but `StateSet{^2}` is refused. A bare `^2` is state P2.
  In `^2|T^C_{F2}|A` the second Register replaces the first (result has Register A only).
- **Chained arrows** `^1^P -> ^1^C -> ^1^E` never compile.

## 4. What the axioms say

The Lean files declare 69 theorems. `lean/Axioms.lean` prints the axioms of 64 of them
(`results/axioms.txt`). The other 5 are helper lemmas (`cancels_ordered_spec`, `cancels_either_spec`,
`step_labelFree`, `foldl_labelFree`, `reach_labelFree`); each is used by a printed theorem, and Lean's axiom
list includes everything a theorem uses, so they are covered. No proof uses `sorryAx` (an unfinished proof).
55 printed theorems use only Lean's standard axioms (`propext`, `Quot.sound`, `Classical.choice`) or none.
9 use `Lean.ofReduceBool`, so they trust Lean's compiled code as well as its kernel: six BOUNDED checks
(one of them, `W5_count`, only pins the word count), the two comparison theorems, and
`compiler_was_python_fallback` (which only checks the engine label of the saved data).

## 5. Not covered — do not over-read

From the coverage critic, ranked by how much a user relies on it:

1. **The grammar.** Only a few spellings were run (`^a^D`, `*`, `/`, `∘`, `compose`, `->`, `<-`, `<->`, `+`, `-`,
   `_{F2}`, `|f`). Aliases (`×` `÷` `·` `→` `CO-n` `C2` `F_2` `|⟨…⟩`) were not compared token by token.
2. **Compound states.** `+` with three or more terms, weights after normalisation, and how later operators read
   compound states are only spot-checked (RAN), not modelled.
3. **Type checker vs run time** as a law ("if it type-checks, it runs") — counterexamples RAN above; not modelled.
4. **The rest of the nesting block**: `orbit_class`, the open-question ids N1-N13, `unpartnered_landing`,
   `readings_agree`, the legacy `domain` field, nesting of compound states, `Phi<...>`, `fractal(...)`.
5. **Drives and RPM**, **Registers / Rule 4 / emergent results** beyond the RAN examples, **sets and
   meta-logic** beyond ten numbers, **v7.6 production semantics** (parsed only, never computed by the compiler),
   **CAS-Ohm calls**, `turn_admissibility.py`, `inversion.py`.

Also:
- BOUNDED and MATCHED nesting results cover a 9-letter alphabet (no `^1 ^4 ^5 ^7`, Domains C and E, Drive F2)
  and up to 5 terms. Only `normal_form_unique_ordered` and `normal_form_unique_either_unlabelled` hold for
  every length.
- A finding is a fact about the code. Whether the code, the documents or the book should change is the owner's
  decision.

## Reproduce

On a Linux machine with elan, Python 3.10+ and this branch checked out:

```bash
python3 research/cas_lean_check_20261001/export_compiler_facts.py --nc noetic-compass-scaffold/noetic-compass --out research/cas_lean_check_20261001/lean
cd research/cas_lean_check_20261001/lean && lake build && ./.lake/build/bin/cascheck nest5.txt && lake env lean Axioms.lean
```

Rust path: build `cas-engine` with `maturin build --release`, install the wheel in a venv, run the exporter with
`--engine rust`, then `cascheck core:rust_core.txt nest:rust_nest24.txt nest:rust_nest5.txt`.
Review probe: `python3 probe_review_claims.py <noetic-compass dir> <out.json>` with each Python.

## Cloud job

- **Source:** branch `claude/cas-lean-check-20261001` (from `8a3555b8`), files copied by `scp`.
- **Purpose:** build and run the Lean check; build the Rust engine; compile the 76,611 programs on each engine;
  run the review probes.
- **Machine:** one `c7i.xlarge`, `us-west-2a`, instance `i-0f6ebdb8b27a89939`, on-demand 0.1785 USD/hour.
- **Time:** launched 2026-10-02 01:49:42 UTC, torn down 02:32:25 UTC (about 43 minutes, about 0.13 USD).
- **Limits:** OS power-off after 180 minutes, power-off destroys the machine; ceiling 1.00 USD (owner "yes", 2026-10-01).
- **Cleanup:** `aws/box.py teardown` removed the machine, its key pair, its security group and the local key.
  A read-only AWS check at 2026-10-02 02:43:44 UTC shows the instance terminated and no `cas-lean-check`
  instance, key pair, security group or volume left (`results/aws_teardown_check.json`).
  Record: `aws/box_record.json`.
