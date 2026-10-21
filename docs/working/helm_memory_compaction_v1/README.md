# HELM memory compaction v1 — teach by conversation, compact memories into CAS with clues, "refresh my memory", strengthen on fit, the Eye and the Atlas correctly applied (design packet, 2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Every HELM part named here keeps its claim status on the spec sheet. Everything new is `PROPOSED`. No `.py` file was changed. The files changed outside this folder: `CHANGELOG.md` and the spec sheet (§7.115 and a §11 row).

## The owner's words this packet answers (both statements of intent, neither an approval)

- **2026-10-21 09:42 PDT**, verbatim: "YEAH BECAUSE SINCE WE HAVE THE CTT AND CAS SDG AND CAS COMPILER AS IT LEARNS VIA CONVERSATIONS (IN FACT WE SHOULD TEST TEACH HELM NEW SUBJECT VIA REGULAR NORMAL Q AND A HUMAN LIKE CONVERSATIONS UNTIL IT GETS IT AND UNDERSTANDS AND IT SHOULD ALL SOUND VERY NATURAL LIKE) AS SPACE GET TAKEN UP MEMORIES CAN BE COMPACTED INTO CAS W/CLUES TO THERE SUBJECT MATTER AND HELM IF NEED TO CAN ASK REFRESH MY MEMORY QUESTIONS AND REASON IT OUT TO SEE IF IT FITS LOGICALLY IN WITH THE REST OF THE CONTEXT IT REBUILT AND IF SO STRENGTHEN THAT PARTICULARS OF THAT MEMORY FOR BETTER RECALL NEXT TIME ALSO USE THE EYE IN THESE SITUATIONS, CORRECTLY APPLIED."
- **2026-10-21 09:50 PDT**, verbatim: "REMEMBER IF CTT AND CAS SDG AND CAS COMPILER ALREADY EXIST AND WORK WHY NOT EMPLOY THEM IN COMPACTING MEMORIES AS WELL AND CAN WORK WITH CUBES AND RECIPE COEFFICIENTS ALSO MAKE SURE TO PUT THIS IN HELM HUB FOR POSTERITY'S SAKE THE LLMs  MODELS THAT WILL TAKE YOUR PLACE ONCE WE RUN OUT TOKENS"
- **2026-10-21, about 10:00 PDT**, typed into the design session, a question: "YEAH BECAUSE WON'T THE RPAs BE INVOLVE IN THE NEW CAPABILITY AS WELL AND IF SO HOW SO?" Answered in DESIGN §6: yes, in four places (clues anchored at the Atlas node, refresh looks up the anchor first then widens by the searchlight, the fit check's F4 is an Atlas placement check, strengthening moves the item from the possibility side to the fact side).

Source of the first two: `C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`. The hub part of the 09:50 order was done by another session (PR #439).

## What this packet is, in plain words

HELM is taught a new subject by ordinary question-and-answer. As its working memory fills, the turns that leave the budget are not dropped (today's behaviour) but **compacted** into a **capsule**: one CAS expression that compiles and round-trips, up to 8 **clues** copied verbatim from the talk, pointers to the cubes and the recipe coefficients the turns touched, a **breadcrumb** to the verbatim original (kept in a cold copy, never deleted) with its sha256, and a **receipt**. Numbers never live in a capsule; they stay in the cubes and the coefficients, which are never compacted. When a later question matches a clue, HELM **fetches first** (the original, digest-checked, answered as `EXACT`); only if that fails does it rebuild from the capsule, run a five-part **fit check** (compiles, round-trips, contradicts nothing, lands at the right Atlas node, the person agrees), and ask one **refresh-my-memory** question that quotes a clue and invents nothing. A rebuilt memory that fits and is confirmed is **strengthened** by four appends (mass up, clues grow from the person's own words, cube provenance to `CHECKED`, Atlas move to the fact side). The **Eye** does the housekeeping as an involuntary tier in a later test; in the first test it runs report-only beside a plain routine, because its acting is `NOT LICENSED`. The **CTT** is the capsule proposer in v2; v1 uses the hand-written CCE skin at 0 USD. The **CAS SDG** makes the keyed subject worlds and the training pairs. The **compiler** is the checker everywhere.

The honesty rule is the first hard gate: a rebuilt memory is never presented as exact. That is the gate M1 failed (spec §7.43), and it is kept word for word.

## Files

| File | What |
|---|---|
| `README.md` | this page |
| `DESIGN_MEMORY_COMPACTION_V1.md` | the owner's words; every existing part with what it does today, its spec status and pointer (§2); the compaction recipe (§3); the refresh loop, fit check, strengthening and honesty rule (§4); the Eye's place and licence (§5); the Atlas's place (§6); the test family (§7); sequencing and the price of every later step (§8); what is not claimed (§9) |
| `PREREGISTRATION_MEMORY_COMPACTION_V1.precode.md` | the exam TEACH-1: gate answer, what is under test, seven arms (COMPACT_ON, VERBATIM_ONLY, FIFO_DROP, SUMMARY_TEXT, NO_REFRESH, RANDOM_REFRESH, REPLAY), SDG worlds with keys, LLM-written teaching turns, three quizzes, the squeeze (B = 12), scoring, 14 instrument rows, 12 hard gates, marks in four families kept apart (UNDERSTOOD, RECALL, REFRESH, SOUNDED_HUMAN), status words in frozen order, ceiling, forecast, seeds, cost |
| `PREREGISTRATION_MEMORY_COMPACTION_V1.precode.sha256` | the sha256 of the pre-code file |
| `OPEN_QUESTIONS.md` | the fourteen decisions that are the owner's, each with a recommendation and the cost of each option |

## The hash

`PREREGISTRATION_MEMORY_COMPACTION_V1.precode.md` sha256 **`7eef0edc7d342bb0438e4052db646528442badefa92d6bdf31e8485914073bf1`** (18,290 bytes, LF line endings). The pre-code is not edited after this; amendments are appended, dated and hashed on their own.

## The short version of the exam

- **Arms:** COMPACT_ON (under test), VERBATIM_ONLY (ceiling), FIFO_DROP (today's behaviour, the floor), **SUMMARY_TEXT** (a plain-English note with the same clues and breadcrumb, no CAS: the mechanism-free baseline the capsule must beat), NO_REFRESH, RANDOM_REFRESH (the control for asking), REPLAY.
- **Worlds:** 16 SDG-generated keyed subjects (24 facts each, 4 unknown-to-the-person), subject words disjoint from every recipe, ingredient and cube name; 32 `LLM_WRITTEN` teaching turns per world, keyed by a different model family; three 16-question quizzes (taught, squeezed, refreshed); turn budget 12.
- **Hard gates:** HG-H8 (0 rebuilt memories presented as exact), HG-INVENT, HG-COMPILE, HG-RECEIPT, HG-COEF (the brain's learned digest unchanged), HG-CUBE, HG-EYE (0 Eye writes), HG-CAS, HG-ASK (every refresh question quotes a clue), HG-REPLAY, HG-TESTS, HG-SPLIT.
- **Marks:** U1 taught ≥ 10 of 16 with 0 wrong (else the rest is `NOT_EXERCISED`); R1 +8 over FIFO_DROP, R2 +4 over SUMMARY_TEXT, R3 +4 over RANDOM_REFRESH, R4 at most −2 against VERBATIM_ONLY, R5 +2 over NO_REFRESH (reported); F1–F3 refresh and Atlas rows; S1–S4 from the talk packet.
- **Words, frozen order:** `INCONCLUSIVE`, `COMPACTION_HARMED`, `COMPACTION_NO_GAIN`, `COMPACTION_EARNED_KEEP`; labels `SYNTHETIC_ONLY`, `LLM_WRITTEN_ONLY`, `RULE_CAPSULES_V1`, `EYE_REPORT_ONLY`.
- **Honest forecast:** `COMPACTION_NO_GAIN` with 0 wrong is the most likely word, because a text note with the same clues and breadcrumb should tie a CAS capsule on recall; the CAS form's edge, if any, is in the fit checks a text note cannot run.
- **Money:** this packet 0 USD; census, build v1, worlds, turns and the laptop exam 0 USD; proposed later lines `COMPACT EXAM at 1 USD` (only if a CPU host is needed) and `COMPACT TRAIN at 3 USD` (v2, the CTT compaction head). Three separate owner decisions, none asked for today.

## Claim states, stated apart

- **REAL / existing machinery:** the compiler, the SDG, the cube store code, the receipts (§7.24), the round trip (§7.31 within its sentence).
- **ENGINEERED-NOT-VALIDATED:** the CTT (words on record `EARS_NO_GAIN`, `EARS_HARMED`, `INCONCLUSIVE`; Part K `EARS_EARNED_KEEP` reported only), the cube store as a HELM part (§7.48), the conversational memory (§7.49), the Eye's scan and pairing (§7.77, §7.78, `SYNTHETIC_ONLY`).
- **VALIDATED / LICENSED within their own sentences:** the wide brain (§7.89, §7.96), the reference brain (c34), the `ATLAS` switch (§7.69 `EARNED_KEEP`, `SYNTHETIC_ONLY`).
- **NOT LICENSED, unchanged:** the Eye's acting (§7.38, §7.40); any RPA-crossing claim (§7.35, §7.100, §7.102).
- **Negative kept:** M1 `M1_FAILURE` on H8 (§7.43).
- **PROPOSED:** everything in DESIGN §3–§8 and the whole pre-code.
- **Not touched:** `helm_*.py`, `test_helm_*.py`, the hub, `Documents/Codex/2026-10-20/r1_wave7/` (job c55 runs from there in another session).

## Sources read

Listed in `DESIGN_MEMORY_COMPACTION_V1.md` §10.
