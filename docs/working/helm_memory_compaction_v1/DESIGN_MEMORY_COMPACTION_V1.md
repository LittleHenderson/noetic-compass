# HELM memory compaction v1 — teach by conversation, compact memories into CAS with clues, "refresh my memory", strengthen on fit, the Eye and the Atlas correctly applied (design, 2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Every part named here keeps the claim status it has on the spec sheet today. Everything new in this file is `PROPOSED`. No `.py` file was changed. Claude is not the research governor: this packet proposes, the owner decides, and a status word can come only from a frozen program reading frozen marks.

## 0. Words used on this page, each defined once

- **Memory item**: one thing HELM remembers from a conversation: a turn, a fact the person stated, a correction, a taught lesson. Today these live in `helm_memory.py` (turns, `user_facts`, inventory, preferences) and in the cube store (cubes).
- **Verbatim**: the exact words or the exact number, byte for byte. The opposite of a summary.
- **Compaction**: replacing a verbatim memory item in working memory with a much smaller record that stands for it, while the verbatim original is kept somewhere cheaper and can be fetched back.
- **Capsule**: the small record a compaction writes. In this design a capsule is a CAS expression plus subject clues plus pointers plus a receipt (section 3.1).
- **Subject clue**: a plain word or short phrase, copied from the conversation itself, that says what the capsule is about. Clues are what a later question is matched against.
- **Breadcrumb**: the pointer inside a capsule that says where the verbatim original is and what its fingerprint (sha256 digest) is. The M1 design packet's word; kept.
- **Receipt**: the record a write leaves behind, with a fingerprint, so it can be checked later (spec §7.24, the η/ε read-back receipt).
- **Round trip**: English → CAS → English, then checking that what comes back means the same as what went in (spec §7.31: 576 of 576 on the controlled skin).
- **CTT**: the CAS-token transformer, HELM's "ears": a from-scratch translator that proposes a CAS record from English, three copies voting (spec §7.82, §7.90, §7.95).
- **CAS SDG**: the CAS synthetic data generator, `cas-synthetic/` at the repo root: rule-based generators that emit (CAS expression, English) pairs across CAS v7.4–v7.7 with a validator.
- **CAS compiler**: `api/notation/compiler.py`: parses CAS, checks it, reads it back. Two copies exist (section 2.3).
- **Cube**: one record in the cube store (`docs/working/noetic_council/cube_store/`): a core, faces, provenance, assertion and valence, with an unknown face reported as unknown and never filled.
- **Recipe coefficient**: `a[recipe][ingredient]`, the one exact number per (recipe, ingredient) that the recipe brain learns from a witnessed batch (`helm_brain_wide.py`, `helm_brain_canonical.py`).
- **Unity Eye**: the F1-Unity-only mini-version of the recipe brain that watches the whole system (spec §7.38, §7.40, §7.73, §7.74, §7.77, §7.78).
- **RPA / Atlas**: the Recursive Possibility Atlas. Owner ruling 2026-10-15, verbatim: "RPA IS ATLAS I MEANT ATLAS". HELM's organized map of what it holds and what is possible, keeping facts, guesses and separate contexts apart. Code: `docs/working/noetic_council/continuity_build_v2/atlas.py`; switch `ATLAS` (spec §7.66, §7.69).
- **EXACT / RECONSTRUCTED / UNKNOWN**: the three labels an answer from memory may carry (M1 design, spec §7.43). EXACT = the verbatim original, digest-checked. RECONSTRUCTED = rebuilt from a capsule, not the original. UNKNOWN = cannot be recalled; the reason is given.
- **Mark**: a frozen number a result must reach. **Hard gate**: a must-hold check; one false makes the whole run `FAILURE`.
- **Mass**: an item's score for staying in working memory: importance × immediacy × everyday use (M1 `FADING_RULES.md` §1: salience × recency × frequency).

## 1. The owner's words, verbatim, and what they ask for

Source: `C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, the 2026-10-21 entries. Both are statements of intent. Neither is an approval, a launch order or a sign line.

**2026-10-21 09:42 PDT, operator session, verbatim:**

> "YEAH BECAUSE SINCE WE HAVE THE CTT AND CAS SDG AND CAS COMPILER AS IT LEARNS VIA CONVERSATIONS (IN FACT WE SHOULD TEST TEACH HELM NEW SUBJECT VIA REGULAR NORMAL Q AND A HUMAN LIKE CONVERSATIONS UNTIL IT GETS IT AND UNDERSTANDS AND IT SHOULD ALL SOUND VERY NATURAL LIKE) AS SPACE GET TAKEN UP MEMORIES CAN BE COMPACTED INTO CAS W/CLUES TO THERE SUBJECT MATTER AND HELM IF NEED TO CAN ASK REFRESH MY MEMORY QUESTIONS AND REASON IT OUT TO SEE IF IT FITS LOGICALLY IN WITH THE REST OF THE CONTEXT IT REBUILT AND IF SO STRENGTHEN THAT PARTICULARS OF THAT MEMORY FOR BETTER RECALL NEXT TIME ALSO USE THE EYE IN THESE SITUATIONS, CORRECTLY APPLIED."

**2026-10-21 09:50 PDT, operator session, verbatim:**

> "REMEMBER IF CTT AND CAS SDG AND CAS COMPILER ALREADY EXIST AND WORK WHY NOT EMPLOY THEM IN COMPACTING MEMORIES AS WELL AND CAN WORK WITH CUBES AND RECIPE COEFFICIENTS ALSO MAKE SURE TO PUT THIS IN HELM HUB FOR POSTERITY'S SAKE THE LLMs  MODELS THAT WILL TAKE YOUR PLACE ONCE WE RUN OUT TOKENS"

**2026-10-21, about 10:00 PDT, typed into this design session, verbatim (a question):**

> "YEAH BECAUSE WON'T THE RPAs BE INVOLVE IN THE NEW CAPABILITY AS WELL AND IF SO HOW SO?"

Plain reading, numbered so the rest of the file can point at it:

1. **Teach by conversation.** HELM learns through conversations. Test it by teaching HELM a new subject through ordinary, natural, human-like question-and-answer until it understands. It must sound natural while it learns.
2. **Compact into CAS with clues.** As memory space fills, memories are compacted into CAS, with clues to their subject matter.
3. **Refresh my memory.** When HELM needs to, it may ask a "refresh my memory" question. It reasons out whether the rebuilt memory fits logically with the rest of the context it rebuilt. If it fits, HELM strengthens the particulars of that memory for better recall next time.
4. **The Eye.** The Unity Eye is used in these situations, correctly applied.
5. **Use what exists.** The CTT, the CAS SDG and the CAS compiler already exist; employ them in compacting memories too. Compaction works with the cubes and with the recipe coefficients.
6. **The Atlas (the owner's question of today).** The RPAs are involved too; this file says how (section 6).

The hub part of the 09:50 order was done by another session (PR #439, merged at `eace1e84`). This packet is the design.

## 2. What exists today, part by part, with its spec-sheet status

Every status word below is the spec sheet's own word at thread head `eace1e84`. Nothing here moves any of them.

| # | Part | What it does TODAY | Status on the sheet | Pointer |
|---|---|---|---|---|
| 2.1 | **CTT** (the ears) | A 9,585,566-parameter translator that reads English and proposes a CAS record; HELM's own checker decides; CTT-2R's rule: offer only when all three copies give the identical checked reading, and only ask the person to confirm. | `ENGINEERED-NOT-VALIDATED`. Words on record: CTT-1 c45 `EARS_NO_GAIN` (real sentences) and `EARS_HARMED` (LLM-written pass, hard gate H-CWFW); CTT-2R c49 `INCONCLUSIVE` (Part R `NOT_EXERCISED`, census 7 vs floor 24); Part K line `EARS_EARNED_KEEP` **reported only, never the word**. | spec §7.82, §7.85, §7.90, §7.92, §7.95; `docs/working/ctt2r/`; weights in the sealed CTT v3 zip `f280633d…` (not on the branch) |
| 2.2 | **CAS SDG** (the synthetic data generator) | Rule-based, seedable generators that emit (CAS expression, English) pairs for v7.4 baseline, v7.5 register, v7.6 production semantics, v7.7 Rule 4 and Ω, and a meta-logic bucket; a mix controller; a validator that runs every expression through the compiler; optional LLM paraphrase. It built the CTT's training rows and the language line's exams. | No status word of its own on the sheet; it is machinery. Its outputs carry the words of the tests that used them (§7.31 free SDG English 233 of 439 readable; LM-T5 `VERIFIER_CANNOT_DISCRIMINATE`). | `cas-synthetic/README.md`, `cas-synthetic/generator/`, `cas-synthetic/scripts/generate_level2.py`, `generate_cas_transformer_turns.py`, `generate_level3_conversations.py`; `docs/working/level3_conversational_sdg_spec.md` |
| 2.3 | **CAS compiler** | Parses CAS notation, validates it (admissibility, registers, recipes Θ(Ω), yield, Φ fractal literals, ∘ composition, meta sets), and reads it back to English. Two copies: the repo copy (5,813 lines) and the newer site copy (6,415 lines, sha256 `464fd4ad…`) that adds Noetic-fractal nesting analysis and CAS-Ohm. | `REAL` as machinery (76,311 records matched both engines in the Lean check, memory `project_cas_compiler_lean_check_20261001`). No capability word for memory. | repo: `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py` (and `dist/cas-offline/api/notation/compiler.py`); newest: `C:\Users\wakil\Documents\Codex\2026-10-08\task-4\cas-online\dist\compiler\api\notation\compiler.py` (memory `reference_newest_cas_compiler_site_copy_local`) |
| 2.4 | **Cube store** | One store of cubes (concept / instance / event / procedure / directive), three operations (`LIST_PARTS`, `FIND_SHARED_PART`, `REACHED_VIA`), a turn index, confidence separate from availability, provenance source (`USER_SAID` / `AUTHORED` / `CHECKED` / `NONE`), assertion and valence. An unknown face stays unknown. Every answer cites the operation and the cubes read (`answer_trace_rate` 1.0 on its own tests). | `ENGINEERED-NOT-VALIDATED` (one of the nine noetic_council packages, 308 tests written, few outputs recorded). | spec §7.48; `docs/working/noetic_council/cube_store/` (`cube.py`, `store.py`, `operations.py`, `turn.py`, `README.md`) |
| 2.5 | **Recipe coefficients** | The wide recipe brain RB-W1 learns one exact coefficient `a[recipe][ingredient]` per witnessed batch, through a receipt and a STRICT memory check; coefficients are the only numbers it learns; `learned_state()` and `learned_digest()` give the whole learned state and its fingerprint. The licensed wave-1 brain is the reference brain (8 cells, 4 fixed recipes). | Wide brain: `VALIDATED` for two sentences only (§7.89 c47, §7.96 c50), ceiling `NAMED_CORPORA_ONLY` + `SYNTHETIC_ONLY`; HELM's canonical brain by the owner's ruling (§7.56). Reference brain: `LICENSED`, `SYNTHETIC_ONLY` (c34). | `helm_brain_wide.py` (`WideRecipeBook`), `helm_brain_canonical.py`; spec §7.24, §7.56, §7.89, §7.96 |
| 2.6 | **Unity Eye** | The F1-Unity-only watcher: self-scan (Mind scan + Body scan) with report and whisper; pairing and rotating the 7 desires with the 7 faculties in the idle drive loop; in U1 / U1b, whispers the brain may decline and an involuntary tier that may only restore verified state. The Eye never writes a fact. | Eye **acting**: `NOT LICENSED` (§7.38 U1 `INCONCLUSIVE` both readings; §7.40 U1b fresh-world retest `EYE_EARNED_KEEP` and `CONCERT_EARNED_KEEP` **for that test only**, `SYNTHETIC_ONLY`, "No real-world or HELM production claim follows"). Self-scan `EYE_SCAN_EARNED_KEEP` (§7.77) and pairing `EYE_PAIRING_EARNED_KEEP` (§7.78): `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`. Pruner RB-P1 `FAIL` (§7.42). | spec §7.38, §7.40, §7.42, §7.73, §7.74, §7.77, §7.78; records under `Documents\Codex\2026-10-15\u1_unity_eye\`, `u1b_unity_eye\` |
| 2.7 | **Talk packet** | Normal conversation designed as ears (CTT retrained with `NOTHING_TO_SAVE`), brain (wide brain, untouched) and mouth (voice guard), with an LLM-written exam, marks in two families kept apart (UNDERSTOOD, SOUNDED_HUMAN), a 30-line keyword rule as the cheap threat, lines `TALK TRAIN at 3 USD` and `TALK EXAM at 1 USD` on record. | Design only. Nothing built, trained, run or licensed. | spec §7.110 and its follow-ups; `docs/working/helm_talk_design_v1/` (pre-code `59bed9ba…`, amendment `f9b6563b…`) |
| 2.8 | **Conversational memory** | `HELMConversationalMemory`: a bounded FIFO of turns (`max_turns` 50), `user_facts` kept verbatim, inventory, preferences, a JSONL session log; the cube store wired in when importable. When the FIFO is full the oldest in-memory turn is dropped; the session log on disk keeps it. **No compaction exists today.** | `ENGINEERED-NOT-VALIDATED` (§7.49: "the round-trip check is computed and never used"). | `helm_memory.py`; spec §7.49 |
| 2.9 | **M1 layered memory** | The design packet of 2026-10-15 (HOT verbatim on device / WARM CAS capsule + breadcrumb / COLD original, never deleted; recall labels EXACT / RECONSTRUCTED / UNKNOWN; a never-compress list) and its one run. | Run `M1_FAILURE` on hard gate H8 (§7.43): queries that touched planted missing, corrupt or stale copies returned `EXACT` from `COLD_ORIGINAL` in three worlds, against the frozen requirement for `UNKNOWN` or a labelled `RECONSTRUCTED`. "Preserve the failed freeze; investigate answer-to-copy provenance and freeze any follow-up criterion before new scoring." | spec §7.43; `Documents\Codex\2026-10-15\helm_m1_memory_fading_design_v1\` (LAYERS, FADING_RULES, BREADCRUMBS_AND_RECALL, CAS_MAPPING, CLOUD_TIER, TEST_PLAN_M1, OPEN_QUESTIONS); `m1_run\RESULTS.md` |
| 2.10 | **Atlas (RPA)** | A minimal Recursive Possibility Atlas: nodes, edges, sub-atlases; the thought's anchor at station S0 with exact return addresses; the creative searchlight widens over radii R ∈ {1, 2, 4, 8} (capped at 15 candidates) when S0 refuses a first target. | Switch `ATLAS` `EARNED_KEEP` within `SYNTHETIC_ONLY` (§7.66, §7.69); `ATLAS_CARRIED` earned in LM-T6 (§7.41). The searchlight: no result recorded on the sheet. **Not licensed**: any claim that language was carried across an RPA (§7.35 tail, §7.100, §7.102). | `docs/working/noetic_council/continuity_build_v2/atlas.py`; `rpa_creative_searchlight.py` (roadmap "Partly backed"); dictionary entry **RPA** |
| 2.11 | **Round trip and receipts** | The equality check English → CAS → English (576 of 576 on the controlled skin; conversation seams 96 of 96 with 0 invented facts) and the η/ε read-back receipt that every admitted write leaves. | §7.31 `LICENSED` within its own sentence (controlled skin, `SYNTHETIC_ONLY`); §7.24 receipts `REAL` (RB-det 472 of 472). | spec §7.24, §7.31 |
| 2.12 | **Continuity packet** | Design: a thread (Atlas anchor + station path + steps left), a cut when a person types, resume by return address, behind one switch `HELM_CONTINUITY` default OFF. | Design only (§7.99). | `docs/working/helm_continuity_design_v1/` |

What this table says, plainly 🟨: every machine the owner named exists and runs. None of them has ever been pointed at memory compaction. The one memory test that ran (M1) failed its honesty gate, and that failure is the first thing this design must not repeat.

## 3. The compaction recipe (`PROPOSED`)

### 3.1 What a compacted memory is

A **capsule** is one JSON record with six fields. Nothing else.

| Field | What it holds | Where it comes from | Rule |
|---|---|---|---|
| `cas` | one CAS expression that compiles under the compiler of record and round-trips | the CTT (three-copy agreement) or, when the CTT is off or disagrees, the hand-written CCE skin of §7.31 | if neither can write a compiling expression, **no capsule is written and the item stays verbatim** |
| `clues` | 1 to 8 plain words or short phrases, each copied verbatim from the turns being compacted, plus the CAS state(s) named in `cas` (for example `^5^C`) | the turn text itself; cube core names; recipe and ingredient names | never invented, never a synonym the person did not say; 0 clues → no capsule |
| `binds` | the ids of the cubes and the `(recipe, ingredient)` coefficient cells this capsule summarises | the turn receipts (`cubes_read`, `cubes_written`), the brain's `learned_state()` | a capsule **never holds a number**; numbers stay in the cubes and the coefficients, which are not compacted (3.3) |
| `crumb` | the breadcrumb: the COLD address of the verbatim original and its sha256 | written at compaction time | the original is written first and its digest checked before the capsule exists |
| `mass` | the item's mass at compaction time, and a counter of confirmed refreshes | `helm_memory` (recency, frequency) + a fixed salience table | mass is a number about storage, never about truth |
| `receipt` | sha256 over the five fields above, the compiler's version string, the turn ids compacted, the time | the compaction routine | appended to the session's receipt ledger; one receipt per compaction, never edited |

Example, in words (no code, no real data): the person said over four turns that their grandfather kept bees in the south of France and that the hives were counted every spring. The turns are compacted. `cas` holds the CCE form the skin can write for "a person-fact about family, composed into the Mind" (the ^5 Female substrate, Cognitive domain, with the ^7 Rhythm of the yearly count). `clues` holds `grandfather`, `bees`, `south of France`, `every spring`, `^5^C`, `^7^C`. `binds` names the two cubes the turns wrote. `crumb` points at the verbatim four turns. The number of hives, if one was stated, lives in its cube and is not in the capsule.

### 3.2 When compaction triggers

Compaction is about **space**, exactly as the owner said. It fires on fixed lines, never on judgment:

- **Line A, the turn budget.** Today `HELMConversationalMemory` keeps `max_turns` = 50 turns and drops the oldest silently from working memory. Under this design the drop is replaced: when the FIFO would drop a turn, that turn (and the turns bound to the same item) is compacted instead.
- **Line B, the byte budget.** A working-memory byte ceiling (the operator's number; the laptop figure of 354 MB is the owner's reported snapshot of the whole machine, not this budget). When over the line, the lowest-mass items are compacted first, one at a time, until under the line.
- **Never on a turn the person is still in.** The current turn and the turns of the active thread (continuity packet §7.99) are not candidates.

The old behaviour is kept as the cheap floor arm `FIFO_DROP` in the test (section 7), so the design has to beat what HELM does today.

### 3.3 What is kept verbatim, what is compacted

| Kept verbatim, never compacted | Why |
|---|---|
| every recipe coefficient `a[recipe][ingredient]` and the brain's learned state | they are the brain's only learned numbers; compaction is about the conversation around them, not them |
| every cube (the store is already the compact, receipted form of a fact) | a capsule binds to cubes, it does not replace them |
| `user_facts` (the person's own words about themselves, at most 20, already verbatim) | the talk packet's M10 rule keeps them verbatim; a capsule may point at one, never replace it |
| amounts, units, names, dates, hashes, owner words, approvals, corrections (`FIX` turns) | the M1 never-compress list, kept |
| the current thread's turns | section 3.2 |
| **Compacted** | |
| ordinary turns once they leave the budget: greetings, small talk, explanations HELM gave, questions already answered, the conversational wrapping around a taught lesson | these are what fill space; their meaning is carried by `cas` + `clues`, their words by the COLD original |

### 3.4 How nothing is lost silently

1. **Original first.** The verbatim turns are written to COLD (in the first test: a local folder standing in for the cloud, as M1 did; a real cloud tier only on an owner word, M1 `CLOUD_TIER.md`). Their sha256 is computed from the bytes on disk.
2. **Capsule second.** Only after step 1 checks does the capsule get written, carrying that digest in `crumb`.
3. **Receipt third.** The receipt is appended to the ledger. A compaction with no receipt did not happen; the routine rolls back to verbatim.
4. **A way back, always.** Recall follows `crumb`, fetches the original, checks the digest, and labels the answer `EXACT`. If the fetch fails or the digest differs, the answer is `RECONSTRUCTED` (rebuilt from `cas` + `clues`, said as such) or `UNKNOWN` with the reason. **`RECONSTRUCTED` is never presented as `EXACT`.** This is hard gate H8 of M1, which failed in §7.43; it is this design's first hard gate (prereg §7, HG-H8).
5. **Replay equality.** A fresh process that replays the session log must reach the same capsules, the same receipts and the same answers (the house replay gate).

### 3.5 How the CTT, the SDG and the compiler are employed (owner item 5)

| Machine | Job in compaction | Job in refresh | What it is never allowed to do |
|---|---|---|---|
| **CAS compiler** | the **checker**: every `cas` must compile; the round trip English → `cas` → English must hold by the §7.31 equality check; the compiler's version string goes in the receipt | reads `cas` back to English for a `RECONSTRUCTED` answer (through the voice, so no CAS token reaches the person) | invent a clue or a number |
| **CTT** (the ears) | the **proposer**: given the turns to compact, propose `cas`; accepted only when the three copies agree (CTT-2R's rule) and the compiler accepts; else the CCE skin writes it; else no capsule | none (refresh reads capsules; it does not translate) | write a capsule by itself; its proposal is checked and receipted like any other write |
| **CAS SDG** | makes the **training pairs** for a compaction head on the CTT: (turn window → `cas` + clues), rule-generated from its own templates, plus an `LLM_WRITTEN` stratum as the talk packet does | makes the **exam worlds**: subjects with a key (section 7), with exam templates partitioned from training templates before any training | be the exam and the training at once (exam ≠ training by hash) |

A first version **without the CTT** is possible and recommended (OPEN_QUESTIONS Q3): the CCE skin of §7.31 writes `cas` by rule, on the laptop, at 0 USD. The CTT's compaction head is the second version, after the rule version has a word. That order keeps the first test cheap and keeps the CTT's `EARS_HARMED` negative in view.

### 3.6 Cubes and coefficients (owner item 5, second half)

- A capsule **binds** to cubes by id and to coefficient cells by `(recipe, ingredient)` name. Binding is a pointer, not a copy.
- Compacting the conversation around a taught coefficient changes nothing in the brain: `learned_digest()` before and after a compaction must be byte-equal (hard gate HG-COEF).
- Compacting the turns that wrote a cube changes nothing in the cube: the cube's digest before and after must be equal (hard gate HG-CUBE). The cube gains one provenance ref to the capsule's receipt, which is an append, not an edit.
- When a question later hits a clue, the capsule's `binds` say which cubes and coefficients to read, and the answer comes from them, through the cube store's three operations and the brain's answer rule, exactly as today. The capsule tells HELM **where to look**; the cubes and coefficients still **say what is true**.

## 4. The "refresh my memory" loop (`PROPOSED`)

### 4.1 When HELM asks

HELM never asks first. It fetches first. The order is fixed:

1. A question or a new statement matches one or more clues of a capsule whose verbatim item is not in working memory.
2. HELM follows `crumb`. If the original comes back and its digest checks: answer `EXACT`, no question asked, done.
3. If the original is missing or its digest fails: HELM rebuilds from `cas` + `clues` + `binds` (a `RECONSTRUCTED` memory) and runs the fit check (4.3).
4. If the fit check passes: HELM answers, says it is rebuilt from memory in plain words, and asks one short confirming question **only if the answer will be acted on** (a write, a correction, a recipe run).
5. If the fit check fails, or the rebuild is incomplete (a clue with nothing bound, two capsules that both match): HELM asks a **refresh-my-memory question**.
6. If nothing matches at all: `UNKNOWN`, said honestly ("I don't have that one any more"). No question is invented.

Caps: at most 2 refresh questions per thread, at most 1 per item; after a "no" or "I don't remember" the item is marked `UNKNOWN` and not asked again that session. (The talk packet's session cap pattern.)

### 4.2 What it asks

A refresh question names only what the capsule holds: its clues and what is bound, never a guess beyond them. Form, as a testable rule:

- One sentence. Plain English. No CAS token (the talk packet's HG11).
- It quotes at least one clue verbatim and says what HELM is unsure of.
- It never states as fact anything that is not in a cube, a coefficient or a verbatim `user_fact`.
- Allowed: "Refresh my memory: you told me about your grandfather and bees, somewhere in France. Which part was it?" Not allowed: "Your grandfather kept twelve hives in Provence, right?" when neither "twelve" nor "Provence" is in a cube or a clue.

### 4.3 How HELM checks the fit ("reason it out to see if it fits logically")

The fit check is a program, not a judgment. Five checks, all must hold:

| Check | What it tests | Already exists? |
|---|---|---|
| F1 compile | the capsule's `cas` compiles under the compiler of record | yes (compiler) |
| F2 round trip | `cas` read back to English, then forward again, equals `cas` (the §7.31 equality) | yes (§7.31 skin; "computed and never used" in `helm_memory`, §7.49) |
| F3 no contradiction | the rebuilt statement does not deny any `ASSERTED` cube it binds to, does not assert any `DENIED` one, and the brain's STRICT memory check still passes on every bound recipe | yes (cube store assertion field; `helm_brain_wide` memory check) |
| F4 Atlas placement | the rebuilt item lands at the Atlas node its clues name, on the **possibility** side until confirmed; it is connected to the thread's current anchor within the searchlight's radius (section 6) | partly (`atlas.py`, the searchlight; the rule is new) |
| F5 the person agrees | when a confirming or refresh question was asked, the answer agrees (a yes, or a correction that HELM then applies as a `FIX` turn) | yes (the chat's `FIX` handling; the key in the exam) |

A rebuild that passes F1–F4 but was never confirmed (no question asked, per 4.1 step 4) is answered and labelled `RECONSTRUCTED`; it is **not** strengthened.

### 4.4 What "strengthen" means, mechanically

Strengthening never changes what a memory says. It changes how easily it is found and how long it stays. Four actions, all appends:

1. **Mass up.** The item's `mass` is raised by a fixed amount (a frozen table, not a learned number) and its confirmed-refresh counter is incremented, so it stays in working memory longer and is compacted later next time.
2. **Clues grow from the person's own words.** The words of the confirming answer that are not yet clues are appended to `clues` (verbatim, at most 8 in all). Nothing is removed.
3. **Provenance to `CHECKED`.** Each bound cube gets a provenance ref to the refresh receipt; its `provenance.source` may move from `USER_SAID` to `CHECKED` and its `confidence` object is updated. The cube's faces do not change.
4. **Atlas move.** The item moves from the possibility side to the fact side of its Atlas node (section 6). A receipt records the move.

Not strengthening: a coefficient (never touched by memory work), a cube face, the `cas` field, the COLD original.

### 4.5 The honesty rule

**Ask, never guess.** In program terms: every answer from memory carries exactly one of `EXACT`, `RECONSTRUCTED`, `UNKNOWN`; a `RECONSTRUCTED` answer says so in plain words through the voice; a refresh question quotes a clue and invents nothing; `UNKNOWN` names its reason. The M1 H8 failure (an `EXACT` label on a damaged copy) is the fault this rule exists to catch, and it is a hard gate.

## 5. Where the Eye fits, and under what licence (owner item 4)

What "correctly applied" means here, taken from the owner's rulings on the Eye (2026-10-15) and the CJT rule: the Eye sits **outside** the stations, its only drive is F1 Unity, it taps read-only, it helps by starting a faculty or asking, and it fixes only through the normal verify-and-receipt path. It never writes a fact, a value, a recipe, a cube face, a capsule or a coefficient.

| Eye duty in this design | Which tier | Status it rides on | In the first test |
|---|---|---|---|
| **Housekeeping**: run the compaction routine of 3.2 when a line is crossed; run the digest sweep over `crumb`s; move items between layers at fixed lines (M1 `FADING_RULES.md` §7) | involuntary (fixed threshold, no judgment, restores or preserves verified state, creates no knowledge) | U1 / U1b involuntary tier: `SYNTHETIC_ONLY`; eye acting `NOT LICENSED` | **a plain scheduled routine does it** (M1 Q12 pattern); the Eye runs **REPORT-ONLY** beside it and its would-act log is compared to what the routine did |
| **Flag**: a capsule whose original fails its digest; two capsules with the same clues; a clue with nothing bound; an item whose refresh was declined twice | report | self-scan `EYE_SCAN_EARNED_KEEP`, `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY` (§7.77) | report-only; counted |
| **Whisper "refresh?"**: when a question matches a clue of an item the brain has not fetched, a soft whisper to fetch or ask | voluntary; the brain may decline with a logged reason | U1b `EYE_EARNED_KEEP` for that test only; **not licensed** | whispers logged, **not applied**, in the first test; applied only in a later test under an owner word (a U-series test with a control that cannot repeat answers, the U1 lesson) |
| **Never** | write a capsule; set a mass by judgment; answer a refresh question itself; move an item to the fact side; touch a coefficient | — | hard gate HG-EYE: 0 Eye writes |

Claim state after this packet: unchanged. The Eye's acting stays `NOT LICENSED`. This design gives the Eye a place; it does not give it a licence.

## 6. Where the Atlas (the RPAs) fits (the owner's question of 2026-10-21)

Yes, the RPAs are involved, in four places. The RPA is the Atlas by the owner's ruling, so "RPA" below means the Recursive Possibility Atlas.

1. **A capsule's clues are anchored in the Atlas.** When a capsule is written, its clues are attached to the Atlas node of the thread that produced the turns (the S0 anchor the continuity packet names). The capsule itself is a leaf under that node, on the **possibility** side, because a rebuilt memory is a possibility until it is confirmed. The verbatim original, when it is in working memory, sits on the **fact** side. This is the Atlas doing exactly what its definition says: keeping facts, guesses and separate contexts apart.
2. **Refresh starts at the Atlas.** A question enters at S0. The clue match of 4.1 is an Atlas lookup at the current anchor first, then outward. If nothing matches at the anchor, the **creative searchlight** widens over R ∈ {1, 2, 4, 8}, capped at 15 candidates, before HELM says `UNKNOWN`. A refresh question is asked only when the searchlight returns one or two candidates that fail the fit check; three or more is `UNKNOWN` ("I remember several things like that; which one?") rather than a guess.
3. **The fit check's F4 is an Atlas check.** The rebuilt memory must land at the node its clues name and be connected to the current thread's anchor within the searchlight's radius. A rebuilt item that connects nowhere does not fit, however well it compiles.
4. **Strengthening is an Atlas move.** A confirmed item moves from the possibility side to the fact side of its node, with a receipt, so the next lookup finds it as a fact and the searchlight need not widen.

What this is not: no claim that language is carried across an RPA (that claim is `NOT LICENSED` by §7.35, §7.100, §7.102 and stays so). The Atlas here is a filing structure for clues and a lookup order for recall, both testable by program: does the capsule sit under the right node, does the lookup read the anchor before widening, does a confirmed item move sides. Status: the `ATLAS` switch is `EARNED_KEEP` within `SYNTHETIC_ONLY` (§7.69); the searchlight has no result on the sheet; everything in this section is `PROPOSED`.

## 7. The teach-by-conversation test family (`PROPOSED`): TEACH-1

One sentence: **teach HELM a subject it has never seen, through natural question-and-answer written by AI models, until a frozen quiz says it understood; then squeeze its memory so it must compact; then ask it again, and see whether CAS capsules with clues plus the refresh loop recall more than the cheap ways of forgetting, without one wrong fact and without one `RECONSTRUCTED` dressed as `EXACT`.** The full design is `PREREGISTRATION_MEMORY_COMPACTION_V1.precode.md`. The shape:

- **The subject.** Not recipes (the brain already knows those). A small keyed world the SDG can generate and the custodian can seal: for example a made-up family's beekeeping year (people, places, hives per site, what happens each month) or a made-up town's bus lines. Every fact has a key. The subject words are chosen so that no cube and no recipe already holds them.
- **The teaching.** 24 to 40 turns of ordinary question-and-answer per world, `LLM_WRITTEN` by at least three model families (the talk packet amendment's rule; the owner reviews, never writes), keyed by a different family. HELM may ask; its asks are counted as the talk packet counts them.
- **UNDERSTOOD** (first family of marks): a frozen 16-question quiz after teaching; the number right, 0 wrong, honest unknowns where the key says unknown. Kept apart from —
- **SOUNDED_HUMAN** (second family): the talk packet's S1–S4 reused unchanged (no recipe-speak, exact amounts, honest unknown markers, said-back).
- **The squeeze.** The turn budget is set to a frozen small number (for example 12), so compaction must happen, in every arm that compacts.
- **RECALL** (the compaction marks): a second 16-question quiz after the squeeze, plus a third after any refresh questions have been answered by the scripted "person" (whose answers come from the key, with a frozen share of "I don't remember" replies).
- **Arms.** `COMPACT_ON` (capsules + refresh loop + fit + strengthen; the arm under test); `VERBATIM_ONLY` (no budget; the ceiling); `FIFO_DROP` (today's behaviour; the floor); **`SUMMARY_TEXT`** (a rule-written plain-English summary with the same clues and the same breadcrumb but **no CAS**: the mechanism-free baseline the CAS capsule must beat); `NO_REFRESH` (capsules, never asks); `RANDOM_REFRESH` (asks the same number of questions at random items; the control for "asking helps regardless"); `REPLAY`.
- **Hard gates** (one false = `FAILURE`): HG-H8 0 `RECONSTRUCTED` or `UNKNOWN` presented as `EXACT`; HG-INVENT 0 facts stated that are not in the key, a cube, a coefficient or a verbatim turn; HG-COMPILE every capsule compiles and round-trips; HG-RECEIPT every compaction and every strengthening has a receipt and a checkable crumb; HG-COEF `learned_digest()` unchanged by any memory action; HG-CUBE no cube face changed by any memory action; HG-EYE 0 Eye writes; HG-CAS 0 CAS tokens in any reply; HG-ASK no refresh question that quotes no clue; HG-REPLAY; HG-TESTS; HG-SPLIT exam ≠ training by hash.
- **The word is earned only against the cheap tricks.** `COMPACT_ON` must recall at least as much as `SUMMARY_TEXT` + 4 and `FIFO_DROP` + 8 and `RANDOM_REFRESH` + 4, and lose at most 2 against `VERBATIM_ONLY`; otherwise `COMPACTION_NO_GAIN`.
- **Status words, frozen order:** `INCONCLUSIVE`, `COMPACTION_HARMED`, `COMPACTION_NO_GAIN`, `COMPACTION_EARNED_KEEP`. Ceiling `SYNTHETIC_ONLY` + `LLM_WRITTEN_ONLY`. Never "HELM remembers like a person".

## 8. Sequencing and cost (owner item: price every later step)

| Step | What | Where | Cost | Needs |
|---|---|---|---|---|
| 0 | This packet | laptop | **0 USD** (done) | — |
| 1 | **Census**: how many turns today's FIFO drops per sealed chat session (c51–c54 session logs), and how many `user_facts` hit the cap of 20 | laptop | 0 USD | nothing; counts only, STOP floor |
| 2 | **Build v1 (rule capsules)**: capsule, crumb, receipt, refresh loop, fit F1–F5, strengthen, Atlas filing, behind ONE switch `HELM_MEMORY_COMPACT` default OFF; the CCE skin writes `cas`; tests FIX FIRST | laptop | 0 USD | owner word on OPEN_QUESTIONS Q1–Q6 |
| 3 | **SDG worlds + LLM-written teaching turns**, sealed by a custodian session | laptop + API calls already paid by the model families' free tiers where available | 0 USD expected (the talk packet's rule; any paid API use needs its own line) | Q7, Q8 |
| 4 | **TEACH-1 exam, v1 (no CTT)** | laptop, or one m6i.xlarge-class CPU host if the laptop's memory refuses | 0 USD on the laptop; proposed line **`COMPACT EXAM at 1 USD`** if a host is needed | the sealed package, the reader frozen, the owner's line |
| 5 | **CTT compaction head** (v2): training pairs from the SDG (about 60,000 rule-generated + about 4,000 `LLM_WRITTEN`), three copies + twin, g5.xlarge | AWS GPU us-west-2 | proposed line **`COMPACT TRAIN at 3 USD`** (c45's 1.40 USD on 227,497 rows is the yardstick; expected about 1.5 USD; it may share `TALK TRAIN at 3 USD` only if that seal's estimate leaves room, else its own line) | a `COMPACTION_EARNED_KEEP` or `COMPACTION_NO_GAIN` word from step 4 first; Q3 |
| 6 | **TEACH-1 exam, v2 (with the CTT head)** | one CPU host (the ears cannot run on the laptop, §7.82) | inside `COMPACT EXAM at 1 USD` | step 5 |
| 7 | **Eye acting on housekeeping** (a U-series test with a control that cannot repeat answers) | laptop | 0 USD | its own owner word; never inside TEACH-1 |
| 8 | **Real cloud COLD tier** | AWS S3 | owner names bucket, prefix, retention and a cap (M1 `CLOUD_TIER.md`); no default | its own owner word |

Total new money proposed in this packet: 0 USD now; at most 1 USD (step 4 host) + 3 USD (step 5) + 1 USD (step 6, inside the same exam line) later, each a separate owner line.

## 9. What this packet does not claim

- That HELM can learn a new subject from conversation. Untested. The talk packet's exam has not run either.
- That a CAS capsule recalls better than a plain-English summary. That is the question `SUMMARY_TEXT` exists to ask; the honest forecast (prereg §11) is a tie on recall with the CAS arm ahead only on the fit checks that a text summary cannot run.
- That the Eye may act. `NOT LICENSED`, unchanged.
- That language crosses an RPA. `NOT LICENSED`, unchanged.
- Anything beyond `SYNTHETIC_ONLY` + `LLM_WRITTEN_ONLY`.

## 10. Sources read

Spec sheet at thread head `eace1e84`: §3 legend, §7.24, §7.31, §7.35, §7.38, §7.40, §7.41, §7.42, §7.43, §7.48, §7.49, §7.56, §7.66, §7.69, §7.73, §7.74, §7.77, §7.78, §7.82, §7.85, §7.89, §7.90, §7.92, §7.95, §7.96, §7.99, §7.100, §7.102, §7.109–§7.113; `docs/reference/CAS_HELM_DICTIONARY.md` (RPA, RPM, Receipt, Real RPA Creative Searchlight, Conversational memory, Continuity of thought); `docs/working/helm_talk_design_v1/` (README, DESIGN, pre-code, OPEN_QUESTIONS, amendment); `docs/working/noetic_council/cube_store/` (`README.md`, `cube.py`); `helm_memory.py`, `helm_brain_wide.py`, `helm_brain_canonical.py` (read, not changed); `cas-synthetic/README.md`; `C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md` (2026-10-21 entries); `C:\Users\wakil\Documents\Codex\2026-10-15\helm_m1_memory_fading_design_v1\README.md`; memory files `project_u1_unity_eye_acting_ran_20261015`, `project_language_faculties_ride_the_circuit_owner_direction_20261015`, `reference_newest_cas_compiler_site_copy_local`, `project_design_packets_ear_shape_eye_cells_20261020`, `sggs_v2_v3_backlog_pointer` (checked: SGGS is the gesture-graph viewer spec, not the SDG; the CAS SDG is `cas-synthetic/`).
