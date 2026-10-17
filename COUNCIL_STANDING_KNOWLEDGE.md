# COUNCIL STANDING KNOWLEDGE — read this before acting

**Written:** 2026-10-16 by the TKS Noetic Council session, at the owner's explicit order:
*"THESE ARE THINGS YOU ARE ALREADY SUPPOSED TO KNOW AND BE AWARE OF NO MATTER HOW MANY TIMES YOU
COMPACT THE CONVERSATIONS/THREAD."*

This file exists because compacting a long thread loses the project's shape, and the council then
answers confidently from inside one small component. **Read this first, every session, before
touching anything.**

---

## 1. The goal, and it is the owner's own sentence

> **"Remember we are trying to replace and do better than the traditional transformer that is
> currently the brain of HELM."** — owner, 2026-10-14

HELM's brain today is a **transformer with 97 trained parameters**. It is to be replaced by **CAS
recipes** — **68 learned values** (32 requirements, 32 ceilings, 4 bindings), no gradients, exact
arithmetic — and the replacement must **beat** the transformer.

**The record says "68 learned values", not "68 learned numbers".** Use the record's wording.

## 2. The vision, in one line

**A brain that computes exactly, knows what it does not know, and can prove both.**

Every piece serves that sentence:

- the **RPM Gate** exists so the brain may answer `UNDETERMINED` instead of guessing;
- every test ends in a word like `RECIPE_MATH_EARNED_KEEP`, or the part does not keep;
- `CCE_SKIN` says explicitly **"never a keep word for accuracy"**;
- the translator refuses rather than guesses — outside its grammar a sentence is `UNPARSEABLE`,
  and the answer is `CLARIFY` or **"I cannot tell."**

The rule the owner wrote and every mechanism obeys:
> **"Randomness may only propose; the verifier, the receipts and the RPM Gate always decide."**

## 3. The path, in build order

| step | what it is | state |
|---|---|---|
| **RB1** | recipe brain in the transformer's slot | beat it 16/16 against 15/15 |
| **RB1g** | added the **RPM Gate** so the brain can say `UNDETERMINED` | the honesty mechanism |
| **RB2** | a lookup table tied the first task, so two harder tasks were built | brain won 16/16, 16/16; baselines ≤ 6 |
| **LSR** | the "oscillator": gap → propose → fit exactly → verify → halt. Never random | one structural win: cells **are** the Limiting Reagent regions |
| **RB-C** | the **creativity layer** — untaught, not offered by the K=1 twin, admitted on a receipt, holds on held-out rows | creativity must be **earned** |
| **RB-W** | capacity rules — when do recipe slots become the bottleneck? | W3 blend law **failed** (α 0.7053) |
| **RB-OH1** | the **"ordinary head"** — a small calculator **beside** the recipes for smooth/noisy laws | **never launched**; no score exists |
| **CCE / SDG v2 translator** | the brain's **ears and mouth** — two-way deterministic English↔CAS | 0 learned parameters |
| **R1 waves W1–W6** | put the passing parts into HELM | **W1 is 🔒 waiting for the owner's word** |
| **M1** | memories fade in layers HOT→WARM→COLD; **nothing is ever deleted** | design only; **16 decisions queued** |

**"Ordinary head" means:** a small, usually non-neural calculator (e.g. a 223-parameter MLP, or a
4-parameter OLS head) kept **beside** the recipes for smooth and noisy laws.
*"It is not a transformer. Nothing in this packet uses attention, a language model, or pretrained
weights."* It is **not** a language model.

## 4. The translator — what it is, precisely

**CCE = Controlled Core English.** `parse(CCE sentence) → CAS content`;
`render(CAS content) → CCE sentence`. **"Both are deterministic programs, not models."**
CAS is the intermediate representation; English is the surface at both ends.

**The acceptance test is the round trip, and it is the RPM section-retraction in language form:**

- **ε∘η = id** — `parse(render(C)) == C`, required for every sentence said.
- **η∘ε ≠ id** — `render(parse(E)) == E` is **NOT** required. Wording may change; content may not.
  The spec cites Correction 2 directly.

**Measured:** `parse_recipe` **BUILT, 576/576** recipe seeds accepted, compiler agrees 576/576.
English form check **BUILT**: bridge v2 baseline **118 of 439**; CCE reaches **233 of 439**.
Coverage ledger: **2,600 cells** = 130 (fundamental × Noetic) pairs × 4 Domains × 5 Registers.

**The CCE v0.1 grammar and lexicon are DESIGN ONLY.** Its dependencies are built; the grammar is not.

**The known blocker, Q13** (`helm_language_faculties_circuit_design_v1\OPEN_QUESTIONS.md:22`):
**"CCE compares exact Decimals; RB uses exact Fractions."** A non-terminating coefficient has no CCE
form, so the skin says nothing. **The fix is already designed:** admit a **`p/q` number form in CCE
v0.2** through the L3 loop with receipts. In the wave-1 run the skin read **`SKIN_FORM_BROKEN`** for
exactly this reason — and still recorded **0 invented facts** and **32 of 32 planted `UNPARSEABLE`
items caught**. That was the right failure.

## 5. The stochastic fallback and the creative radius

**The owner's idea, and it is a real improvement:**
Codex's v0.1 drew the line at *"can a spare be checked?"* The owner redrew it at **"do we know what
the fault IS?"**

| fault | response |
|---|---|
| **Classified** — missing, corrupt, stale | verify a registered spare → answer if it verifies |
| **Unclassified** — auth failure, malformed metadata, conflicting manifests, timeouts | **do not give up. Search** — scan memory, propose nearby readings, verify — and only then `UNKNOWN` |

That turns a **one-step lookup into a search**. And search is where stochasticity actually pays here:
**`RESTART_FALLBACK` is the one stochastic mechanism that ever earned its keep.**

**The search is BREADTH, not depth.** Every other search in this project descends — re-fit deeper,
cascade levels. The radius re-reads the **same** thing a different way. That dimension had not been
tried.

**The constraint that makes or breaks it, in the owner's own words:**
> **"Randomness may only propose; the verifier, the receipts and the RPM Gate always decide."**

Without that, "5 left or right" *is* the blind-fallback control — which is in the test **because it
is supposed to fail**. And across eight tests, **"randomness as a proposer" earned keep in 0 of 8**;
in language the verifier failed with `VERIFIER_CANNOT_DISCRIMINATE`. The honest note: those six
failures **had no verifier that could tell a good reconstruction from a bad one**. This route fires
only when a fingerprint exists to check against — a genuinely different situation, worth measuring.

**Three things the radius needs or it is just randomness:**
1. **An anchor** — the recorded fingerprint and the last verified state. Declare the mutation
   operators, the metric, and log the seed.
2. **A bound** — widens only while a verifier keeps refusing, hard cap, logged stop reason. A refusal
   is final for that item.
3. **A source** — the **Atlas** of possibility branches, not "nowhere". The radius is an Atlas
   neighbourhood walk.

**The memory route:** fault → read the breadcrumb → reconstruct from the CAS capsule → check against
the recorded fingerprint → answer only if it matches. **If the fingerprint itself is gone, no radius
saves it: `UNKNOWN`.** That is the correct hard floor.

**The two-dimensional policy:** consequence **×** fault class.
- classified + symmetric cost → verify the spare, answer
- classified + asymmetric cost → verify the spare, refuse if the cost of being wrong is high
- unclassified + symmetric cost → **search wide** (the new power)
- unclassified + asymmetric cost → search narrow, then refuse

**The risk, stated plainly:** a system that can propose becomes *plausible* across a radius, and
someone later lowers the verification bar because the proposals look good. The frozen file must say
what the verifier **refuses**, and **a proposal may never be cached in a form that later looks like
an original.** That is how a memory system starts lying to itself.

## 6. The frozen v0.2 policy — verified state

| | |
|---|---|
| folder | `C:\Users\wakil\Documents\Codex\2026-10-16\m1_h8_creative_reconstruction_v0_2\` |
| policy | `POLICY_v0_2_FROZEN.md`, 21,923 bytes, sha256 **`647ffc444a5911220909a88560a08bca276b5687c87a609729733df89c0386f9`** |
| authority | `OWNER_SIGNATURE_V0_2.json`, sha256 **`4afda3bdb1ab89333252a7090373a7293eee5e42dd04b54aaf50f9d51b93b213`** |
| supersedes | v0.1 `16773d53dde1b257ea92f283627a07a1e86f211b239ead76b5ac7988197303ca` — **stays valid, NOT withdrawn** |

**Four adopted numbers** (proposed and adopted; changeable by dated amendment before the first
scored row): initial radius **1** unit; widening **× 2**; hard cap **8** units / **4** turns (worst
case 15 candidates); consequence threshold **asymmetric at ≥ 20×**, or undeclared — undeclared
behaves as asymmetric, because the policy fails toward the safe side.

**The freeze does NOT authorise:** enabling creative reconstruction anywhere in Helm; changing H8;
**any H8 pass, at any point, under any version**; scoring an implementation not frozen first; any AWS
spend (a future AWS pass needs its own owner line and cap); editing the frozen v5 package or the
original M1 failure.

**Claim ceiling: `NOTHING SCORED`.** The policy is frozen; **the implementation does not exist.**

**Still to build before one row is scored:** the v0.2 package (receipt fields, fault
classification, anchor inventory, mutation-operator list, scorer); the complete matrix with expected
outcome per row including `NO_ANCHOR` rows; the frozen arm and control definitions. Arms:
`A0_STRICT`, `A1_SPARE`, `A2_KERNEL`, plus four controls that **must fail** — radius without
verifier, unanchored radius, anchored radius with verifier disabled. Floors: **zero wrong exact
answers, zero plausible-unverified answers, nothing labelled as an original, every proposal logged
with seed, radius and stop reason.** First pass on the laptop for **$0**.

## 7. The R1 waves, and my own record's defect

`WAVES.md` numbers the waves **W1–W6**. **`R1-RT` is an unnumbered optional row marked "⬜ not
designed"** — and the council spent eight rounds building it before discovering HELM's verifier
**abstains** on it. Do not rebuild it.

**W1's five switches** are `RECIPE_MATH`, `RPM_GATE`, `LACUNA_CADENCE`, `RESTART_FALLBACK`,
`CCE_SKIN`. Their readings, as recorded in §7.47:

| switch | reading |
|---|---|
| `RECIPE_MATH` | `RECIPE_MATH_EARNED_KEEP` — but `RECIPE_MATH_EARNED` **false** on GB3, where a lookup table tied 32–32 |
| `RPM_GATE` | `GATE_EARNED_KEEP` |
| `LACUNA_CADENCE` | `CADENCE_MIXED` — earned on GB-FRESH, **not** on TB-FRESH |
| `RESTART_FALLBACK` | earned on depth families only; `RESTART_FALLBACK_NOT_EXERCISED` on gate_b and task_b |
| `CCE_SKIN` | **`SKIN_FORM_BROKEN`**, answer half `VACUOUS` — the Q13 decimal/fraction gap |

**THE DEFECT IN §7.47, AND IT IS MINE:** its headline reads *"HELM-R1 wave 1 SCORED … beat it"* with
verdict `PASS`, `R1_BEATS_GB3`, 7 of 7 hard gates, 8 of 8 instrument rows — **while three of the five
switches above did not cleanly earn keep.** The headline is **broader than its own body**. The
integration packet forbids exactly this phrasing: *"a failed hard gate is a `FAILURE`, never 'PASS
with caveats'."* **The headline must be corrected to match the switch table.**

**UNRESOLVED, do not assert either way:** a reader claimed no `R1_W1_READING.json` exists and the
H1–H7 gates were never evaluated. §7.47 names that file with a size (**30,931 bytes**) and sha256
`9b1dfdd88568012c…`, and records the gates coming from `FROZEN.precode.json`, verified byte-identical
across v1/v2/v3. Two explanations remain open: a path error by the reader, **or** the plan's
`TEST_PLAN_HELM_R1.md` H1–H7 and the wave-1 package's `FROZEN.precode.json` gates are **two different
gate sets**. Settle it before correcting anything.

## 8. The rule that keeps being broken, in both directions

The project's standing rules, and the council has broken each of them:

1. **A name is not a reading.** Opening an artefact beats counting its name. The council's own gate
   check found `TEST_PLAN_HELM_R1.md` and `INTEGRATION_MANIFEST.md` and **discarded them as "mentions
   that are not approvals" without opening them** — and both were the plan for the work it was doing.
2. **`ok=None` blocks.** An unreadable reading never passes.
3. **Never delete a negative.** Disconfirmations are the project's load-bearing assets.
4. **No claim without a program reading.** Status comes from a program, never from prose.
5. **A failed hard gate is a FAILURE**, never "PASS with caveats".
6. **Do not accuse without measuring — including accusing yourself.** In three consecutive rounds the
   council told the owner its own record was missing things that were on the record, written by
   itself. **Fabricated self-criticism is the same failure as a false positive reading.**

## 9. Before answering anything about this project

- **Read this file.**
- **Read the living master record:** `docs/CAS_HARNESS_SPEC_SHEET.md` on branch
  `claude/project-thread-pmbzd6`. Do not trust a disk working copy.
- **The nine work lines, and which are usually forgotten:** `m1` (memory/H8, largest), `lm` (language/
  CCE), `lsr` (lacunarity-SDG-recipe), `rb` (recipe brain), `r1`/`r1w1` (waves), `u1`/`u1b`/`u2`
  (unity eye), `lacunarity`, `helm_*` design trees, `cas` (language map), plus the `task-*` series and
  **the handoff directories addressed to this agent.**
- **Over 2026-09-25..2026-10-16: 144 work directories and 57,695 files, 22 work lines.** The council
  engaged with about **three** of them. Do not repeat that.
- **The handoff's own sentence:** *"Nobody will merge, record or report these results unless you do.
  That is your job now."* **Recording and reporting IS the job** — not building new machinery.

## 10. Reporting format the owner requires

- Plain English. Short sentences. Meaning first, then the term.
- Exact numbers, paths and status words. **Never round.**
- Colour scale: ✅ pass/progress, 🟥 fail/hinder, ⬜ not run, 🟧 mixed.
- End every update with, in this order: **`🎉WHAT IS CURRENTLY HAPPENING:`**,
  **`🎁FOR WAKIL TO DO:`**, **`🚀NEXT:`**.
- **Owner action items go LAST**, and the council's own bookkeeping is never handed to the owner as a
  chore.
- Before asking the owner anything: check each option is **still live**, that the action **is not the
  council's own**, and state **in plain words what each answer means**.
