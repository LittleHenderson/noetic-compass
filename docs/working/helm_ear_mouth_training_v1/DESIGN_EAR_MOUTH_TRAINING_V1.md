# DESIGN — training HELM's ear and mouth from confirmed cubes plus the SDG (v1, design only, 2026-10-22 PDT)

Status: DESIGN ONLY. 0 USD. Nothing built, trained or run. Claim status of every part: `PROPOSED`. Nothing here is a
result. The owner's words (verbatim, 2026-10-22): "Design ear and mouth training from confirmed cubes plus the SDG".
The owner writes nothing (A-TEACH2-17): every choice below is offered as buttons; a click is the approval.

## 0. In plain words

- **The ear** reads what the person says into a fact (a cube reading: thing, what about it, value, what it replaces).
  Today it is the CTT, HELM's 9.6-million-parameter translator, being retrained on made-up worlds (CUBE TRAIN).
- **The mouth** says a fact back in plain English. Today it is fixed templates (`helm_voice.py`, `phrasebook.json`, and
  the cube say-back). Nothing about it has been trained.
- **A confirmed cube** is a fact the person said "yes" to when HELM read it back (provenance `CHECKED`). It is the
  best teaching material HELM can get: the person's own words, with a meaning the person agreed to.
- **The SDG** (the made-up-world generator) gives volume and a known truth for every line.
- **The idea:** every confirmed cube becomes two lessons — an EAR lesson (the person's own line → the confirmed
  reading) and a MOUTH lesson (the confirmed reading → a natural line that says exactly that) — mixed with SDG lessons
  so the models see far more examples than one conversation gives. The ear and the mouth then check each other: a
  mouth line is kept only if the ear reads it back to the same fact. This is the same loop as the cube oscillation's
  say-back, now used for training.

## 1. What already exists and is reused (no second model, no second parser)

| Part | Where | Used for |
|---|---|---|
| CTT model (encoder-decoder, copy head, 8,349 tokens) | `HELM_CTT_20261019\helm_cas_translator\model.py` | both directions: a direction tag on the input |
| CUBE TRAIN rows and the AI-written stratum | `docs/working/helm_cube_oscillation_v1/cube_train/` | SDG ear rows; the keyed AI lines become mouth targets too |
| Reading format and adapter | `helm_cube_osc.target_string` / `reading_from_ctt` | the ear's target; the mouth's input |
| Say-back renderer | `helm_cube_osc.say_back` | the mouth's floor (what a trained mouth must beat) |
| Voice templates and rules M1–M10 | `helm_voice.py`, `phrasebook.json`, talk packet §7.110 | the mouth's baseline and its hard rules |
| Cube store, provenance `CHECKED`, cold copies | `docs/working/noetic_council/cube_store/`, `helm_memory_compact.py` | where confirmed cubes and the person's own lines come from |

The mouth is the CTT run in the other direction (`<SAY>` tag: reading in, English out), as `INTENT_MOUTH_TRANSFORMER`
and AMENDMENT_A_TALK_1 Part M intend. One model, one vocabulary, two tags (`<CUBE>` = ear, `<SAY>` = mouth).

## 2. Where the lessons come from

### 2.1 Confirmed cubes (the person's own words)
A lesson is harvested from a cube branch only when ALL hold:
1. its thing's cube is `CHECKED` (the person said yes to the read-back or to a refresh question), and the branch is
   the CURRENT one for its (target, kind) (a later correction supersedes it; the old one is never a lesson);
2. the person's original line for that branch (its `provenance_refs` turn) is fetched and its fingerprint matches
   (`EXACT`; a rebuilt, held or unreachable line is never a lesson);
3. the reading the adapter makes from the stored target equals the reading the person confirmed;
4. the line passes the copy rule (every target word is a word of the line).
Each harvested cube gives: EAR row `(<CUBE> person's line → target_string(reading))`, MOUTH row
`(<SAY> target_string(reading) → person's line)`. Lessons carry their source (`CONFIRMED`), the session, the turn.

### 2.2 The SDG (volume and truth)
The CUBE TRAIN row builder (generator truth, FACT / FIX / TRAP / SAYBACK / NONE) gives the ear rows. For the mouth,
the same truth readings paired with (a) the keyed AI-written lines of the CUBE TRAIN stratum (1,500 lines by three
families, kept only where two other families keyed the truth) and (b) new AI-written paraphrases written for this
purpose by the same three families, keyed the same way. The mouth never learns from the say-back template itself
(that is the floor it must beat), only from lines written to sound like a person.

### 2.3 The mix
Per training batch: SDG ear 4 : confirmed ear 1 : SDG mouth 3 : confirmed mouth 1 : kept CAS-record rows 1 (so the
old skill stays). Confirmed lessons are few at first; they are repeated at most 4 times per epoch, never more, so the
model does not memorise one person. A person's (or a synthetic world's) lessons are held out whole: 20 % of sessions
never train, they test.

## 3. The mouth's hard rules (it may choose words, never facts)

- **No new fact:** every name, number and month in a mouth line is in the reading; nothing else of those kinds
  (checked by rule; the copy head points at the reading's words).
- **Round trip:** the ear (three copies, unanimous) reads the mouth's line back to the same reading; otherwise the
  line is not used and HELM falls back to the say-back template (never says nothing, never guesses).
- **M1–M10** of the talk packet: no CAS token, no recipe-speak on a non-recipe turn, exact amounts only through
  `say_amount`, honest unknowns, one to three sentences.
- **Never changes an answer:** the mouth renders a fact the brain already decided (HG7 of §7.110); it chooses nothing.

## 4. The ear's rules (unchanged from CUBE TRAIN)

Copy rule, `NONE` when no fact, unanimous vote of three copies, the brain-side check and the say-back rounds stay in
charge of what is kept. Confirmed lessons add the person's real phrasing; they never let the ear skip a round.

## 5. Exams and gates (to be pre-registered before any code)

**Ear v2** (after CUBE TRAIN): the CUBE TRAIN gates (no invented word; confident wrong ≤ 1 % SDG, ≤ 2 % AI-written;
right ≥ 40 % / 25 %; the old skill kept) plus **G-CONFIRMED**: on held-out confirmed lessons, unanimous-right ≥ the
v1 ear's, and 0 confident wrong.
**Mouth v1:** G-NO-NEW-FACT = 0 lines with a name, number or month not in the reading; G-ROUNDTRIP ≥ 95 % of held-out
readings re-read to the same reading by the v1 ear; G-NO-CAS = 0 CAS tokens; mark **SOUNDS-HUMAN**: blind raters from
the three AI families (the owner writes nothing; labelled `AI_RATED`) prefer the mouth's line to the say-back template
on ≥ 60 % of held-out pairs, and to `helm_voice` templates on ≥ 50 %; **VARIED**: at least 3 distinct wordings per
reading over 5 samples. Words: `MOUTH_EARNED_KEEP` / `MOUTH_NO_GAIN` / `MOUTH_HARMED` (any new fact) / `INCONCLUSIVE`.

## 6. Order and cost (each paid step is its own owner choice)

1. Finish CUBE TRAIN and TEACH-2 (in progress): the v1 ear, and a sealed exam that produces confirmed cubes in
   synthetic chats.
2. Harvest confirmed lessons from TEACH-2's synthetic chats (laptop, 0 USD), plus the new AI paraphrases (CLIs and
   helper agents, 0 USD).
3. One GPU job trains ear v2 and mouth v1 together (g5.xlarge, about 2–3 USD; cap proposed 4 USD).
4. Read by a frozen reader; if `MOUTH_EARNED_KEEP`, the mouth is wired behind its own switch, default OFF.

## 6b. Additions from the owner's side chat (2026-10-22, pasted into the main chat)

1. **The trap, written as a rule.** A label must come from somewhere independent of the model being trained and of
   HELM's own rule reader: the generator's truth, two other model families' keys, or the person's confirmation
   (`CHECKED`). A cube whose reading came from the rule reader and was never confirmed is never a label. Every lesson
   records which proposer produced the reading (CTT copies, rule reader, AI keyers); results are reported split by it,
   so a lesson set that only mirrors the rule reader would show.
2. **More sentences per confirmed cube.** Besides the person's own line, the three AI families write up to 4 fresh
   paraphrases of each confirmed reading (keyed the same way: kept only when the two other families read back the same
   fact). This gives varied phrasing for the ear (the biggest current gap) and natural targets for the mouth.
3. **A tone tag for the mouth.** The mouth's input is the reading plus a tone tag: the turn's CAS state (one of the 40)
   and Register (`|T`, `|A`, `|f`, `|E`), from HELM's own reading of the conversation, never from the model. Lessons get
   their tag from the person's line (confirmed lessons) or from the writer brief (paraphrases written to a requested
   tone). The tag may change the words, never the facts (§3). Owner's intent on record: "I WANT A TRANSFORMER TRAINED ON
   THE 40 ELEMENTS BECAUSE THAT CAN CONTRIBUTE TO THE NUANCE HUMAN LIKE TONE" (INTENT_MOUTH_TRANSFORMER).
4. **The analogy side.** When a person has taught an analogy (the cube's `face_3`), the mouth may use it, quoted from
   the face; while `face_3` is `unknown`, the mouth never makes one up (the schema's rule).
5. **Asking from what HELM knows (needs no training).** The cube store's three questions (`LIST_PARTS`,
   `FIND_SHARED_PART`, `REACHED_VIA`) supply real questions: when the person mentions a thing, HELM can ask about a
   stored fact of it ("Did the Oxley line still run nine buses in October?"). The person's answer confirms, corrects
   or adds a cube, and so makes new confirmed lessons. A separate small design, behind its own switch.
6. **Reading and correction, not new primitives.** The tone tag uses the existing 40 states and 4 Registers; nothing
   new is added to the CAS ontology.

## 7. What this design does not decide (OPEN_QUESTIONS.md)

Whether confirmed cubes from REAL conversations may ever become lessons (privacy; the default is synthetic only),
whether ear and mouth share one model, who rates "sounds human", and the GPU cap.
