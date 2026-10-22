# Receipt tags + 28-cell Eye pairing — DESIGN (v1, 2026-10-20 PDT). Design only; nothing built or run.

## 1. Stage 1 — tags on receipts (deterministic, no learning, no model)

### 1.1 The address a receipt carries (schema `cas_address/1`)

```
{"foundation": F1..F7 | UNTAGGED,
 "domain":     P | C | E | O | UNTAGGED,
 "cell":       "<F><D>" (one of 28, e.g. F2C) | UNTAGGED,
 "register":   T | A | f | E | UNTAGGED,
 "pathway":    A0 | D1..D7 | W1..W7 | P1..P7 | UNTAGGED,
 "element":    "<Noetic><Domain>" (one of 40, e.g. ^8C) | UNTAGGED,
 "how":        the rule id that set each field}
```
Every field is set by a named rule or stays `UNTAGGED`. There is no default and no guess. `how` names the rule so a
reader can check it.

### 1.2 Where the tags come from (rules, in order; the first that applies sets the field)

- **Foundation:** as today (the item kind's Foundation in the synthetic world; the drive-loop filing rule).
- **Domain:** from what the item is about. Principled (P): a rule, a cap, a refusal reason, a guard. Cognitive (C): a
  reading, a lesson, a recipe coefficient, a plan step. Evaluative (E): a verdict, a mark, a receipt pass/fail, a
  whisper admitted or not. Operational (O): a stock line, a batch, a tool call, a file. Rule `DOM-1`: a receipt's
  `reason` word maps through a fixed table to one Domain; `DOM-2`: an item kind maps through the same table; else
  `UNTAGGED`.
- **Cell:** Foundation x Domain when both are set (`CELL-1`); else `UNTAGGED`.
- **Register:** `REG-1`: a faces sentence or a purpose clause carries `f`; a plan or a rule carries `A`; a stock or
  batch line carries `E`; a vision-level item (the roadmap, an owner ruling) carries `T`; else `UNTAGGED`.
- **Pathway:** `PATH-1`: only for items that are steps of an RPM chain the prerequisite planner already holds
  (A0 -> D_n -> W_n -> P_n); the planner names the node; everything else `UNTAGGED`.
- **Element:** `ELE-1`: only where an existing receipt already names a Noetic (the language layer's nested Noetics,
  the lexicon_v3 reading); Noetic x Domain; else `UNTAGGED`. No new Noetic classifier is written for this packet.

### 1.3 Where the tags live

- A new optional field `address` on every receipt and every filed backlog item. Old receipts stay valid: a missing
  field reads as all-`UNTAGGED`.
- The tags never enter a computed value, a coefficient, a verdict or the gate (same rule as the attention point in
  RB-I3). They are used only to FILE and to CHOOSE.
- Honest limit: in HELM's kitchen world most items land in a few cells (stock and batches are O, lessons C, verdicts E);
  the P cells and the T register may be nearly empty. The census in the test plan counts this before anything is sealed.

## 2. Stage 2 — the Eye pairs the 28 cells with the 7 faculties

### 2.1 The table (THE variable), unchanged in form

- 196 cells, one per (cell of the 28, faculty). Each holds T tries and S successes; score (S+1)/(T+2), exact Fraction;
  every cell starts 0/0 = 1/2. No answer key, no hand pairing, no random pairing (DeepSeek's two failure modes, verified).
- Learning rule identical to RB-I3: a verified success at (c, f) adds to T and S; a failure adds to T; nothing else moves
  a cell. Choice rule identical: exact best first, seeded alternative when stuck, the verifier decides. A failed faculty
  is never retried on one item; up to 7 tries then `CLOSED_NO_FIX`.
- **Back-off (new, deterministic):** an item filed `UNTAGGED` at the Domain level is paired at its Foundation row using
  the 7 x 7 table of RB-I3 (the four Domain cells of that Foundation pooled: sums of T and S). So the 28-cell Eye can
  never do worse than the 7 x 7 Eye on untagged items by construction; the gain, if any, must come from tagged items.
- Carries across the 32 sessions of one life; resets per world seed (as RB-I3).

### 2.2 Attention

- The point a lives on the open **28-simplex** (28 positive numbers summing to 1; Correction 4). Pull target per cell
  q_c = (n_c y_c + 1/256) / Σ (n_c open items filed at c; y_c = (s_c+1)/(t_c+2)); one Fisher-Rao geodesic step τ = 1/4
  per idle tick; focus = the live cell with the largest a_c. The plain count-ratio arm `EYE_RATIO` stays as the
  geometry's baseline (RB-I3 R1): if the step does not at least tie it, the geometry has not earned its place.
- A reported row projects a onto the 7 Foundations (sum over Domains) so the two tables can be compared on one picture.

### 2.3 What stays exactly the same

Whisper, report, gate (the Eye never writes; a whisper is a nudge through the normal gate); the conversation cut
(no faculty call and no attention step while in conversation, with the cut violator arm that must fail); the idle
exam machinery; the guard and canary; the 7 faculties; the verifier.

## 3. Stages 3 and 4 (named now, not designed)

- Stage 3: the 22 pathways x 7 faculties (154 cells) for items that are chain steps; baseline = stage 2.
- Stage 4: the 40 elements x 7 faculties (280 cells) only once an element tag exists on enough items (a Noetic reading
  on record, never a classifier written for the purpose); baseline = stage 3.
- The 4 Registers are an axis on every state (CAS v7.5), not a fifth set of things to pair; they ride as a tag and may
  be used as a tie-break in the choice rule (owner pick, OPEN_QUESTIONS Q3).

## 4. Why this is not just "more cells"

A 196-cell table needs about four times the evidence of a 49-cell table to separate good pairs from bad. Each new axis
therefore has to earn its place against the axis before it on the same planted backlog, or the finer table is only
noise with more rows. The back-off rule makes "no worse" true by construction; "better" must be measured.
