# DECLARED_CONSTRAINT_RESULT — enforcing a constraint the packet already declares lifts `context` from 0.0000% to 32.6190%

> **FLAG_FOR_HUMAN_REVIEW — audit 2026-09-18 (`AUDIT_ROUNDS_32_33_RESULT.md` §2.3).** With the same count rule, a RANDOM choice of three participants scores `163.5/420 = 38.9286%`; the machine's margin ranking scores `137/420 = 32.6190%`. The ranking AUC is `0.466862`, below 0.5 in all six runs, and 78 of the 137 correct answers are forced by the count alone (3 slots, 3 true). The lift below is the count rule plus `setting_ref` held at the truth; it is **not** evidence that the machine's scores rank well. The figure `60.9863%` is true positives over all slots (`977/1602`), not per-bit accuracy. No significance test was run (57 unique questions per run).

**Round 32. The first fix measured to work on the trained machine's own recorded scores.**
**$0.00. Pure standard library. No torch, no GPU, no model, no training, no new run.**

Script: `measure_declared_cardinality.py`. Raw output: `declared_cardinality.txt`.

---

## 1. The observation

Rounds 31/32 measured what each field of an answer is worth by giving it the truth and re-assembling:

```
context   + participant truth   75.7143%   (+71.4286)
context   + setting_ref truth    4.2857%   (+0.0000)
```

**`context`'s entire bit-level deficit is its four participant bits**, and the recorded decoder
decides them with an independent `max` per slot and knows no constraint at all.

**But the packet declares the constraint.** `answers.answer_space` sets
`participants_basis = PRIMARY_AUTHORED_LABELS_FIRST_THREE` for every world, and
`checker._derive_values` reads the answer as `sorted(focus["declarations"]["participants"])`. The
`context` slots are that world's four nodes. Measured over all 420 `context` questions in six runs,
the truth cardinality is **exactly 3, every time**.

**So the answer is not four free bits. It is a choice of which one node is absent.** The composer was
never told.

## 2. The measurement

From the recorded per-slot score table, two decoders, both assembled with the project's own
`slots.assemble_answer` and compared to the project's own derived truth:

- **independent** — argmax each participant slot on its own. This is the run's own rule.
- **top-3** — force exactly three PRESENT, taking the three highest `PRESENT − ABSENT` margins, and
  the rest ABSENT. The `k` comes from the packet's own declared basis, not from the answer.

`setting_ref` is set to the truth in both arms, so the participant bits are isolated.

## 3. The result — six for six

| run | q | bits, independent | **bits, top-3** | exact, independent | **exact, top-3** |
|---|---|---|---|---|---|
| 20260917_a | 70 | 39.7004% | **62.1723%** | 0.0000% | **37.1429%** |
| 20260917_m | 70 | 39.3258% | **63.2959%** | 0.0000% | **41.4286%** |
| 20260918_a | 70 | 38.5768% | **61.0487%** | 0.0000% | **32.8571%** |
| 20260918_m | 70 | 40.0749% | **61.0487%** | 0.0000% | **32.8571%** |
| 20260919_a | 70 | 41.5730% | **59.1760%** | 0.0000% | **25.7143%** |
| 20260919_m | 70 | 40.8240% | **59.1760%** | 0.0000% | **25.7143%** |
| **ALL SIX** | **420** | **40.0125%** | **60.9863%** | **0.0000%** | **32.6190%** |

**Per slot: +20.9738 points. Per answer: 0.0000% → 32.6190%, in every one of the six runs.**

## 4. Why it works, and why it matters

The machine's *threshold* on the participant bits is badly calibrated — it over-asserts PRESENT, and
at 40.0125% per bit it sits 38.6392 points below the 78.6517% a constant answer earns. But its
**ranking** is much better than its threshold: ordered by margin, the truly-absent node lands outside
the top three 60.9863% of the time instead of 40.0125%.

**Enforcing the declared cardinality converts an absolute-threshold problem into a ranking problem,
and the machine's ranking is far better than its threshold.**

**This is structural and free.** No new information path, no new capacity, no weights, no encoder
change. The constraint is a field of the packet the machine already receives, and `score_decisions`
never reads it.

**And it is the first fix in this record that works on the trained machine's own scores.** Round 30's
fitted readout was a substituted, hypothetical readout that cost more than it gained overall. This
uses the recorded scores exactly as the run produced them, and it is six-for-six.

## 5. It revives round 26's thesis in a corrected form

- **Round 26** found the architecture composes jointly for exactly one kind and independently for the
  other seven, and proposed extending the joint branch.
- **Round 27** refused that: three of four binary kinds read their own bits at or below chance, and a
  composer cannot compose what was never read.
- **Round 32 corrects the correction.** There *is* something for the composer to do — not a joint
  likelihood, but a **declared constraint**. The bits were at chance *as thresholds*; the same scores
  are well above chance *as rankings*, and a declared cardinality is what converts one into the other.

**The generalisation is immediate, and it is architectural.** Every kind carries declared structure
the composer ignores:

| kind | declared structure, already in the packet | enforced by the composer? |
|---|---|---|
| `context` | participants are the first three primary labels — exactly 3 of 4 | **no — this record** |
| `edge_account` | the answer is the focus world's `contains`, whose size is declared per world | no |
| `parts` | direct targets of the supplied `whole` | no |
| `role_set` | `ALL_AND_ONLY_SOURCE_GROUNDED_FOCAL_ROLES` | no |
| `definition` | `FOCUS_WORLD_DECLARATION_IDENTITY` — one world's declaration, not three free choices | no |

**The architecture already declares, per kind, what a legal answer is. Nothing reads it.** That is
exactly the shape of the payoff the objective points at: the capability is latent in the declared
structure and is simply unused.

## 6. A design flaw this file caught in itself

The first version held `setting_ref` at the machine's own choice and read **0.0000% for every arm in
all six runs**. A 0.0000% reading is the same signature that exposed the round-32 edge-direction bug,
so it was treated as a contradiction: `context` has *two* fields, and with `setting_ref` wrong no
participant decoding can produce a correct answer, so the arm was measuring nothing.

Fixed by holding `setting_ref` at the truth, which is what §3 reports. **Both arms are printed in the
artifact**, so the confound is visible rather than smoothed away.

**Standing practice, now used twice in one round: an impossible reading is a bug report about your
own instrument before it is a finding about the machine.**

## 7. Claim status

- **REAL, measured:** §3's table, from the recorded score table in six runs, scored through the
  project's own `assemble_answer` against the project's own derived truth, six-for-six.
- **REAL:** the truth cardinality is exactly 3 in all 420 `context` questions.
- **NOT LICENSED:** that a run would score 32.6190%. `setting_ref` is **given the truth** in that
  arm — the machine's own `setting_ref` accuracy is 0.0000% on these questions, so the fix as
  measured is worth nothing until that field is also read. **Two things are needed, not one.**
- **NOT LICENSED:** that the same trick helps `edge_account`, `parts`, `role_set` or `definition`.
  The declared structures differ and none has been tried.
- **NOT LICENSED:** any change to `score_decisions`. It is the run's own decoder and this record does
  not touch it.
