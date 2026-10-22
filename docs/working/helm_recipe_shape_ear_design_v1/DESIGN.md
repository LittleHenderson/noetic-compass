# Recipe-shape proposer ear — DESIGN (v1, 2026-10-20 PDT). Design only; nothing built or run.

## 0. The idea in one paragraph

Today a recipe sentence reaches the wide brain only if the deterministic wide reader (`helm_wide_turn.py` v5) can
split it into lines and bind each line to an amount, a unit and a name. Wave 6 showed what happens at the edge of that
reader: one line, "1 teaspoon of cream tartar, and half as much soda", became a made-up ingredient and cost the whole
wave its mark (§7.93, K4). The fix was a hand-written rule. Every such shape will need another rule. This design puts
a learned proposer at that door: when the wide reader would ask, the ear proposes a **shape**: a list of lines, each
line's role (stock, batch, ran-out, face, purpose, restatement, relative-amount bundle), the spans of the user's own
sentence that hold the amount, the unit and the name, and which dish the sentence is about. The ear emits **pointers
into the sentence, never digits and never names**. A deterministic filler copies the spans; the wide reader's own
binder, unit table, fraction parser, receipt and memory check then run exactly as today. If anything fails, HELM asks
the question it asks today. If the proposal would write (a batch, a stock line), it is read back first and written only
on a yes.

## 1. Hard boundary (owner ruling 2026-10-19, kept whole)

The ear shares **no parameters, no store, no receipt and no file** with the brain. Concretely:
- the ear's process may read the user's sentence and the brain's PUBLIC vocabulary (dish names and ingredient names the
  brain already holds, as a plain list) and nothing else; it never opens the book, a lesson, a receipt or an exam;
- the ear's output is a JSON shape with span pointers; it contains no number and no name token (the output vocabulary
  holds none; a pointer to a span that is not in the sentence is a refusal);
- the brain's write path is unchanged: `WideRecipeBook` admits a batch only through its own receipt and memory check;
  the ear cannot call `admit`; it hands the shape to the same `parse_line`/`bind_name` path the reader uses;
- the write-audit of CTT (A-CTT-2 rule) applies to the ear's process: no file writes outside its own temp folder and
  the audit log; no sockets; no process starts.

## 2. What the ear proposes (the SHAPE schema, deterministic, versioned `shape/1`)

```
{"dish": ⟦span⟧ | KNOWN:<index into the public dish list> | ASK,
 "lines": [
   {"role": STOCK | BATCH_INGREDIENT | RAN_OUT | MADE | FACE | PURPOSE | RESTATEMENT | RELATIVE_BUNDLE | NOTE | ASK,
    "amount": ⟦span⟧ | NONE,  "unit": ⟦span⟧ | NONE,  "name": ⟦span⟧ | KNOWN:<index>,
    "relative_to": <line index> | NONE,  "ratio_word": ⟦span⟧ | NONE}
 ],
 "turn": TEACH | STOCK | QUESTION | OTHER}
```
- A span is `[start, end)` over the user's sentence in characters; the filler copies the text verbatim.
- `KNOWN:<index>` points into the public name list the brain exposes; the filler copies the name from that list.
- `RELATIVE_BUNDLE` reproduces reader v5's one exact bundle form ("A, and half as much B" = one line, ratio r); any
  other relative form the brain does not hold stays an `AMOUNT_RELATIVE` question, exactly as in v5.
- `NOTE` is a span the ear says carries nothing the brain can use; the reader's rule 6 (STOCK_FRAME_REQUIRED) and the
  faces reader still decide; a `NOTE` never suppresses a question the deterministic path would ask.

## 3. Where it sits (reader first, ear second, brain decides)

1. The wide reader v5 runs. If it reads the turn (no question), its reading stands; the ear is **not called**.
2. If the reader would ask (`UNREAD_CLAUSE`, `UNIT_KIND_MISMATCH`, `AMOUNT_RELATIVE`, `CLARIFY_ENGLISH_UNKNOWN_PRODUCT`,
   `CLARIFY_WIDE_UNSETTLED_SAME_NAME`, or a split failure), the ear proposes a shape.
3. The filler builds candidate lines from the spans. The reader's own `parse_line`, unit table, fraction parser and
   `bind_name` run on them. Any parse failure = the original question, unchanged.
4. If the shape would **write** (a STOCK turn or a TEACH turn), HELM reads it back in plain words, built by the existing
   voice from the parsed lines ("Just to check: 1 teaspoon of cream of tartar, and half as much soda, as one line?"),
   and writes only on a yes. A QUESTION turn may go ahead; its answer sentence states what was understood.
5. The brain's receipt and memory check decide admission as today. A refused batch is refused the same way.
6. **Agreement rule (from CTT-2R, §7.95):** three independently trained copies of the ear must give the byte-identical
   shape, or HELM asks. This is the one lesson c49 taught: without the rule the copies made 0 / 5 / 5 confident wrong
   proposals; with it, 0. The rule is part of the design, not an option.
7. Session cap: at most 2 ear offers per dialogue; silent after a no (CTT-2R's rule, kept).

## 4. Why shape and not amounts (and not "whole CAS expressions" yet)

- Amounts: the brain's whole licence rests on "never invents an amount". A model that emits digits would be the old
  transformer brain by another door (GB3 lost to the recipe brain, §7.47). So the output vocabulary has no digits.
- Whole CAS expressions (compound states, registers, nesting): the spec sheet's settled negative §10.1 says text rendered
  from our own templates is not a reading corpus, and the only human-labelled CAS text agrees at the ^1 level only
  (§7.23). Until an outside human-labelled corpus exists, a transformer over full expressions would learn our
  templates. This packet therefore stays on recipe sentences, where real public text exists (the X-REAL frames:
  Gutenberg cookbooks, Wikibooks, 13,686 real recipes from the shape survey) and the keys come from frozen rules.
- The CAS content of a recipe sentence the ear may tag is limited to what the brain already holds: the dish (an Ω), the
  ingredients (the X_i of Θ(Ω)), the ran-out ingredient (the limiting reagent L), faces and purposes (the triad words
  the faces reader already reads). No Noetic, Domain or Register tags are proposed by the ear in v1.

## 5. Training data (all from existing, pinned, public or self-made sources; no new downloads)

| Source | Rows (approx.) | Key | Use |
|---|---|---|---|
| X-REAL recipe frames (Gutenberg, Wikibooks; `x_real/frames/`, pinned by sha256) | 13,686 recipes, about 100,000 ingredient lines | the frozen wide reader v5 where it reads cleanly (shape = its own parse) | TRAIN / VAL, split by recipe id; the reader's clean parses are the silver keys |
| Lines the reader v5 refuses (`UNREAD_CLAUSE`, `AMOUNT_RELATIVE`, split failures) | unknown until counted; the census is step 1 of the test plan | NO key; held out as the "gap" stratum for the exam | never trained on; the custodian draws the exam from here |
| LLM-written kitchen turns (the CTT-2R Part K recipe, custodian-only pool) | 128 + 16 dialogues per draw | frozen rules | a second exam label `LLM_WRITTEN`, as in §7.95 |
| SDG renderings | — | — | **not used** (settled negative §10.1) |

The silver keys are the reader's own parses, so the ear can only learn to reproduce the reader where the reader is
right, plus whatever generalises to the refused lines. That is the whole bet, written down: **if the ear reads the
refused lines no better than a copy-closest rival, it earns nothing** (test plan, arm A2E).

## 6. Size (Capacity Rules v0.1: a job for every parameter)

Same shell as CTT (encoder-decoder, 9,585,566 parameters, grammar-locked decoding) with the output grammar replaced by
the `shape/1` schema and the pointer vocabulary (span start/end over 256 positions, role tokens, `KNOWN:` indices up to
the public list size, at most 10 lines by the brain's `MAX_INGREDIENTS`). No new parameter family is added; the
decoder's output head shrinks (no digit, no name tokens). Three trained copies from three recorded seeds, one twin at
about a quarter size (as A5 in CTT), untrained controls from recorded seeds. Expected GPU time about one g5.xlarge
hour per copy, inside a cap the owner sets later.

## 7. What a pass would license, and what it would not

Licensed, only with the frozen reader's word `EAR_SHAPE_EARNED_KEEP` on a custodian-sealed exam: "On real recipe lines
the wide reader v5 cannot read, the three-copy shape ear, offering only agreed shapes and only after a yes, let the wide
brain learn [n] more recipes fully with 0 wrong lessons and 0 wrong answers, and beat a no-learning copy-closest rival
under the same rule by [m]." NOT licensed: amounts; names; anything the reader already reads; real kitchens or cooks;
whole CAS expressions; Noetics, Domains, Registers; the ear without the vote; any effect on the licensed reference brain.

## 8. Honest limits, stated before any data

- The silver keys are a program's parses, not a person's reading. A reader defect becomes a training defect (the K4
  lesson). Mitigation: the exam keys are frozen rules on the gap stratum, never the reader's parses.
- The agreement rule is silent on most ask-turns (80 of 109 in c49). The gain is bounded by agreement, by design.
- c49 also found reader v1.1 saving 3 wrong readings on AI-written singles. A shape ear sits behind the wide reader v5,
  a different program, but the same class of defect is possible: the test plan carries a reader-wrong count as a
  reported row and a hard gate on wrong lessons.
- One draw, one run: no statistical claim.
