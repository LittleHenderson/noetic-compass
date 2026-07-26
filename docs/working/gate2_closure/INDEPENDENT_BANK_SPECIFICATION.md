# Independently-Authored Evaluation Bank — specification

**Purpose:** break the shared-authorship deadlock that killed four instruments. This is the only
artifact that can support an external A/B claim about definition quality. Required whether v5 passes
or fails.

---

## 1. The problem it solves, precisely

Every evaluation bank in this repository was written by this project, from the same source material as
the definitions under test. That produces an inescapable bind:

- **Leave the vocabulary in** → the task is solvable by word overlap. Measured: a bag-of-words matcher
  scored `0.4851` against the model's `0.1474`, and **39 of 40 concepts carry a word appearing in only
  that concept's definition.**
- **Mask the vocabulary out** → both arms collapse to chance, and the instrument cannot distinguish
  "one arm had nothing but vocabulary" from "masking destroyed genuine meaning."

Measured ceiling on any bank-free workaround: **46.2%** of a cell's own vocabulary already sits in its
row and column siblings (median `44.7%`, max `77.8%`; 38 of 40 cells above 25%). No composition rule
avoids that channel.

**A bank whose authors never saw either definition set removes the bind at the root.** Vocabulary
overlap becomes incidental rather than structural, and no masking is needed — so no signal is destroyed.

## 2. Hard requirements

| # | Requirement | Why |
|---|---|---|
| R1 | Authors have **never seen** the TKS definitions, the compact CAS definitions, or any existing bank | The entire point. One leaked document voids the bank. |
| R2 | Authors are given the **concept, not the wording** — elicited by example and discussion, never by handing over a definition | Handing over text reintroduces the leak in one step |
| R3 | **Both** definition sets stay hidden from authors throughout | Otherwise the bank is biased toward whichever they saw |
| R4 | Items are **natural language descriptions of situations**, not restatements of definitions | A restatement is a paraphrase; a situation is a test |
| R5 | Each item is labelled with exactly one of the 40 concepts, by its author | Labels must come from understanding, not from matching |
| R6 | **Minimum 2 independent labellers** per item; disagreements discarded, not adjudicated | Adjudication imports the adjudicator's reading |
| R7 | Target **>= 400 unique items** (10 per concept), no duplication | v1–v4's effective-n failures. 5,920 duplicated rows were really 80. |
| R8 | Vocabulary overlap with **both** definition sets measured and reported **before** any model run | If overlap is high anyway, the bank has failed R1–R4 and must not be used |

## 3. Elicitation protocol (satisfies R2 without leaking wording)

For each of the 40 concepts, the briefing pack contains:

1. The concept's **structural position only** — its Noetic and its World, named but not defined
   (e.g. *"the 'Female' role in the 'Mental' world"*).
2. **Three to five worked examples** of situations that do and do not exemplify it, written by the
   owner *without* quoting either definition set.
3. **No definition text from any arm.** Not TKS, not compact CAS, not the canon.

Authors then write situations from their own understanding. This is why R2 matters: they must reach
the concept, not copy a sentence.

## 4. Acceptance gate — the bank must pass BEFORE it is used

Run and report, before any model touches it:

- **Surface separability**: char-ngram, word-hash, and length baselines under grouped CV must all sit
  near chance (`<= 0.10` for a 40-way task where chance is `0.025`). If a bag of words can label the
  bank, the bank is contaminated.
- **Vocabulary overlap**: mean fraction of each item's content words appearing in the matching concept's
  definition, computed **separately for TKS and compact CAS**. Report both. A large asymmetry means the
  bank favours one arm and must be rejected.
- **Inter-labeller agreement**: report raw agreement and the discard rate from R6.
- **Admissibility**: `research/reconciled/experiment_admissibility.py` must return admissible —
  no row duplication, effective n equal to unique item count.

A bank failing any of these is rejected, not repaired. Repairing it against a measured failure is how
contamination gets laundered.

## 5. What it enables, and what it still will not

**Enables:** the genuine Gate 2 item 4 comparison — do TKS definitions outperform compact CAS at
identifying situations, judged on items neither set could have contaminated. Both arms score on
identical items with identical protocol; the only difference is the definition text.

**Still will not license:** any claim about human comprehension, any claim beyond the tested model, any
cross-architecture or universality claim, or a product `ACCEPT`.

## 6. Cost and the owner-action item

Days, not hours, and it needs people outside the project. **The rate-limiting step is finding authors
who satisfy R1** — anyone who has read the spec sheets, the book manuscript, or the marketing material
is disqualified.

**This is an owner-action item.** I can write the briefing pack, the elicitation template, and the
acceptance-gate script. I cannot supply independent authors.

## 7. Status

`SPECIFIED / NOT STARTED / NO AUTHORS IDENTIFIED`

Running in parallel with v5 per owner direction, not sequenced behind it.
