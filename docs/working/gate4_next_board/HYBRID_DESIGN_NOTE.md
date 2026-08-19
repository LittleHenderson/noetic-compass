# Design note — SDG plans the path, a real model writes the turns (2026-08-19)

**Status: DESIGN ONLY. Not built, not run, not preregistered.** Written while the SDG-wiring
workflow was still editing `next_board_test.py` and `PREREG_NEXT_BOARD_V1.md`; deliberately
kept in a separate file so it cannot collide with those edits (an earlier smoke run was
voided exactly that way — the script was rewritten mid-run at 11:44).

## Finding 1 — SDG's multi-turn output is TEMPLATE-RENDERED, and unusable as a reading corpus

`cas-synthetic/generator/multi_turn/conversation_generator.py::_render_turn` is pure
`rng.choice(...)` over fixed tuples. **No model is called.** The full assistant pools:

| TurnType | Templates (verbatim, complete) |
|---|---|
| `ACK` | "Got it." / "Okay -- I'm with you." |
| `MIRROR` | "If I'm hearing you, the structural reading is {cas}." / "What's landing for me is {cas}. Does that fit?" |
| `CLARIFY` | "Walk it back -- what's closer to your felt sense?" / "Help me anchor this: which part lands hardest?" |
| `EMPATHIZE` | "That sounds like a lot." / "Yeah. That's heavy." |
| `ANSWER` | "The reading I'd stand behind is {cas}." / "Best fit I can give is {cas}." |
| `PLAN` | one template |
| `REFUSE` | one template |
| `REFUSE_CLAIM` | one template |
| `CLOSE` | "Thanks for walking through that." / "Take care." |

**Why this kills it as a corpus for board reading, three ways:**
1. **Surface-separable by construction.** One or two fixed strings per class means a char or
   word n-gram classifier recovers the class at ~100%. Under the preregistered kill rule — a
   surface-control win on template text kills the calibration claim — this design fails itself.
2. **Not model output.** These are 2-15 word fragments. No model emits "Got it." as a whole
   turn. A lens validated on these has been validated on *the templates*, and carries no
   information about model behaviour.
3. **Contains `{cas}` placeholders** — the answer is literally interpolated into the text.

**Verdict: do NOT use SDG-rendered text as the corpus.** This is not a repairable parameter
choice; the template pool IS the artifact.

## Finding 2 — the ADMISSIBILITY GRAPH is the real asset, and it transfers

What SDG genuinely provides is a **validated dialog-act plan**: a turn-type vocabulary, an
admissibility graph constraining which type may follow which, and sampling weights.

Turn types: `OPEN`, `ACK`, `MIRROR`, `CLARIFY`, `EMPATHIZE`, `ANSWER`, `PLAN`, `REFUSE`,
`REFUSE_CLAIM`, `REPAIR`, `CLOSE`.

Weights (`_TURN_TYPE_WEIGHTS`, deliberately biased toward MIRROR/ANSWER/REPAIR to exercise
the repair surface): `ACK 0.5`, `MIRROR 1.5`, `CLARIFY 1.0`, `EMPATHIZE 0.7`, `ANSWER 1.5`,
`PLAN 0.4`, `REFUSE 0.1`, `REFUSE_CLAIM 0.2`, `REPAIR 1.2`, `OPEN 0.6`, `CLOSE 0.0`
(closed deliberately, never sampled).

`generate_dialog_path(seed, target_turns)` walks the graph deterministically from a seed.

## The hybrid

**SDG plans. A real model writes.**

1. **Plan** — build a path through the SDG admissibility graph, but FORCE transition variety
   instead of sampling: consecutive turns are deliberately different types, so corpus
   persistence is broken by construction. Record the realised transition matrix.
2. **Realise** — for each planned turn type, instruct a real model to produce that turn in
   natural prose, on a real topic, WITHOUT naming the type in the output. The prescribed type
   is the ground-truth label; the model supplies the surface.
3. **Read** — blind readers label boards from the prose alone, as now.
4. **Score** — ground-truth accuracy (prescribed vs consensus read) + the full surface battery.

**What this buys:** forced variety AND ground truth, WITHOUT template leakage — the two
things the API corpus and the SDG corpus each half-solved.

## The assumption the hybrid rests on, and how to test it cheaply FIRST

**Can a real model reliably produce a PRESCRIBED turn type?** If it cannot, the hybrid has no
ground truth either and is no better off than the API corpus.

This is testable for a few dollars before building anything: prescribe N turns across the
type vocabulary, generate them, and have blind readers recover the type. If recovery is at
chance, the hybrid is dead and should be abandoned rather than built. **Run this compliance
check before writing the hybrid corpus stage.**

## Open risks
- The turn-type -> board mapping is still OURS, not the framework's (same disclosure as
  PREREG section 3 makes for the sequencing claim).
- An instruction-following model told to "write a PLAN turn" may produce stylised text that is
  *also* surface-separable. The word-unigram control must be run against the ground-truth
  task, not only the sequential one.
- Ground truth is the *prescribed* type, not a verified property of the text. A model can be
  instructed to write a PLAN and produce something else; the compliance check above measures
  exactly that gap, and it should be reported, not assumed away.
