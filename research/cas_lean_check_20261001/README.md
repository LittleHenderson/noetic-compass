# Lean check of the CAS compiler (2026-10-01)

**Owner request (2026-10-01):** "use LEAN (https://lean-lang.org/) to check the logic of CAS programming
language / THE LATEST CAS COMPILER".

**What was checked:** `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py` at commit `8a3555b8`
(git blob `439c4908df2718a3ca1e1ff40bda63020cf71efa`, 6,415 lines). This is the newest compiler on any branch:
no commit after `8a3555b8` touches the file. Both of its arithmetic paths were checked: the Python fallback, and
the Rust engine `cas_engine` (built from `cas-engine/` at the same commit).

**Tool:** Lean 4.19.0 (Lake 5.0.0), core library only (no Mathlib). Everything ran on AWS (see "Cloud job").

## How the check works

1. **A Lean copy of the rules.** `lean/CasCheck/Core.lean` and `lean/CasCheck/Nesting.lean` copy the
   compiler's rules line by line: `∘`, `×`, `÷`, `->`, `+`, `-`, the involution pairs, state numbering,
   the Nesting Operator's canonical form (`_nesting_reduce`) and the Dual Cancellation criterion
   (`_nesting_criterion`).
2. **Is the copy faithful?** `export_compiler_facts.py` runs **68,311 real CAS programs** through the real
   `compile_expression`, and `lean/CasCheck/Differential.lean` compares every answer with the Lean copy:
   all 100 Noetic pairs for `*`, `/`, `∘` and `compose(...)`; all 1,600 state pairs for `->`; the Domain rules of
   `*` and `/`; `+` on all 100 pairs; `x - x` on all 40 states; 10 set facts; and **every** nested `∘` word of
   2 to 5 terms over a 9-letter alphabet (66,420 words).
3. **What do the rules imply?** `lean/CasCheck/Laws.lean`, `Nesting.lean` and `Bounded.lean` prove laws about
   the copy.

## Results

Claim states: **PROVED** = Lean's kernel checked it (for every case listed, or for every number / every word
length when marked "general"). **BOUNDED** = checked for every word up to the stated size by compiled code
(`native_decide`). **MATCHED** = the Lean copy agreed with the real compiler on every record.

### The copy matches the real compiler — MATCHED

| Record kind | Records | Agree (Python path) | Agree (Rust path) |
|---|---:|---:|---:|
| `*`, `∘`, `compose`, `/` on Noetic pairs | 100 | 100 | 100 |
| `->` on state pairs | 1,600 | 1,600 | 1,600 |
| Domain rule of `*` / of `/` | 16 / 16 | 16 / 16 | 16 / 16 |
| `+` dominant state | 100 | 100 | 100 |
| `x - x` | 40 | 40 | 40 |
| set facts (`|States|` = 40 ...) | 10 | 10 | 10 |
| alphabet letters as the compiler reads them | 9 | 9 | 9 |
| nested words, 2-4 terms | 7,371 | 7,371 | 7,371 |
| nested words, 5 terms | 59,049 | 59,049 | 59,049 |

The Python-path and Rust-path answer files are byte-identical. Reports: `results/cascheck_report.txt`,
`results/cascheck_rust_report.txt`. The comparison theorems (`DiffTheorems.lean`) build.

### Laws that hold — PROVED

- `∘` is closed, commutative and associative; `^0` is its identity (general proofs for the first three).
- The involution undoes itself; the self-duals are exactly `^0 ^1 ^4 ^7`; the pairs are exactly 2↔3, 5↔6, 8↔9.
- Each (Domain, Noetic) has one state index 0..39 and back (general proof).
- Correction 1 of CLAUDE.md holds: `^0` admits a move only from a state to itself (general proof).
- `×` never ascends a Domain; when both bracketings of a `×` chain compile, they agree.
- **Nesting canonical form, surfacing-member-first reading: well defined for words of ANY length**
  (`normal_form_unique_ordered`, general proof). Cancel the pairs in any order; when nothing more cancels,
  you are at the compiler's canonical form.
- BOUNDED (all 66,429 words of 1-5 terms): the canonical form never contains a pair that still cancels; the
  Dual Cancellation criterion's greedy pairing never misses a full pairing that exists, in all three readings.

### Findings — PROVED (facts about the code; not rulings on the theory)

| Id | Finding |
|---|---|
| B1 | The `admissible` flag of `->` is vacuous for 36 of 40 targets: it can be false only when the target is a `^0` state. The check passes the target's own Noetic, so `target % 10 == operator` always holds. |
| B2 | `∘`, `×` and `compose` never cancel a dual pair (`^2∘^3 = ^5`, `^5∘^6 = ^1`, `^8∘^9 = ^7`), but `÷` cancels every dual pair to `^0`. Under `∘`, what undoes `^8` is `^2`, not its dual `^9`. |
| B3 | `÷` is commutative: `^a ÷ ^b = ^b ÷ ^a`. |
| B4 | `÷` does not undo `×`, and `^0` is not neutral for `÷`: `^4 ÷ ^0 = ^2`. |
| B5 | The involution does not respect `∘`: `inv(a ∘ b) = inv(b) ∘ inv(a)` holds for only 46 of 100 pairs. |
| B6 | `+` depends on the written order on a tie: `(^2^C + ^3^C) × ^5^C = ^7`, `(^3^C + ^2^C) × ^5^C = ^8`. |
| B7 | `-` has no zero: `x - x` returns `x`. |
| B8 | **Found by Lean** (I first wrote associativity as a law; the kernel showed it false): whether a `×` chain compiles depends on the brackets. `(^1^E × ^1^C) × ^1^O` is refused, `^1^E × (^1^C × ^1^O)` compiles. Of 64 Domain triples: 20 vs 30 accepted, 10 disagree. |
| N-A | Nesting canonical form, either-order reading: **not unique**. `^2^C|T ∘ ^3^C ∘ ^2^C|f` can end on either `^2^C`; the compiler reports one. 542 of 66,429 words (1-5 terms) have two or more either-order forms. |
| R1 | Rust path: the compiler passes `explicit_drive or 4` as the drive, but `explicit_drive` is a true/false flag, so `^2^C_{F2}` reaches Rust as F1; Rust's result drive is stored back into that flag field. No tested output changes (the visible drive comes from `drive_weights`). Rust errors are caught and silently replaced by the Python fallback. Probe: `results/rust_probe.json`. |

### Independent review

See "Review verdicts" below (filled in after the adversarial review).

## What the axioms say

`lean/Axioms.lean` prints the axioms of every theorem (`results/axioms.txt`). No proof uses `sorryAx`
(an unfinished proof). Law and finding proofs use only Lean's standard axioms (`propext`, `Quot.sound`,
`Classical.choice`) or none. Only the BOUNDED checks and the comparison theorems use `Lean.ofReduceBool`
(they trust Lean's compiled code as well as its kernel).

## Do not over-read

- The Lean copy covers the rules listed above. It does not cover the parser's full grammar, the type checker's
  other rules, register Rule 4, production semantics (v7.6), RPM, CAS-Ohm calls, or the set meta-logic beyond
  ten facts. See "Not covered" below.
- BOUNDED and MATCHED nesting results cover a 9-letter alphabet and up to 5 terms. The general proof
  (`normal_form_unique_ordered`) is the only nesting result for every length.
- A finding is a fact about the code. Whether the code or the documents should change is the owner's decision.

## Reproduce

On a Linux machine with elan, Python 3.10+ and this branch checked out:

```bash
python3 research/cas_lean_check_20261001/export_compiler_facts.py --nc noetic-compass-scaffold/noetic-compass --out research/cas_lean_check_20261001/lean
cd research/cas_lean_check_20261001/lean && lake build && ./.lake/build/bin/cascheck nest5.txt && lake env lean Axioms.lean
```

Rust path: build `cas-engine` with `maturin build --release`, install the wheel, then run the exporter with
`--engine rust` and `cascheck core:rust_core.txt nest:rust_nest24.txt nest:rust_nest5.txt`.

## Cloud job

- **Source:** branch `claude/cas-lean-check-20261001` (from `8a3555b8`), files pushed by `scp`.
- **Purpose:** build and run the Lean check; build the Rust engine; run the compiler 2 × 68,311 times.
- **Machine:** one `c7i.xlarge`, `us-west-2a`, instance `i-0f6ebdb8b27a89939`, launched 2026-10-02 01:49 UTC
  (2026-10-01 local), on-demand 0.1785 USD/hour.
- **Limits:** OS power-off after 180 minutes, power-off destroys the machine; ceiling 1.00 USD (owner "yes", 2026-10-01).
- **Cleanup:** `aws/box.py teardown` (machine, key pair, security group, local key). Record: `aws/box_record.json`.
