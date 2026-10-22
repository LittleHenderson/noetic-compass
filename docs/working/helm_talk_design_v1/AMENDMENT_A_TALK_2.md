
## Amendment A-TALK-2 (2026-10-22 PDT) — build v1 of the talk layer's 0 USD pieces: small talk, questions about HELM, off-topic talk (M10), honest "I don't know", and asking from what HELM knows (Q5); written before any code

Status: appended after A-TALK-1 (`f9b6563b…`); nothing above is edited. It specifies a BUILD behind two new switches, both OFF by default. It trains nothing, runs no exam, licenses nothing; every part stays `ENGINEERED-NOT-VALIDATED`. 0 USD (laptop). The owner writes nothing (A-TEACH2-17); the operator writes this.

**The owner's words (the button, verbatim, 2026-10-22):** "Yes: use the recommended answers to the ear-and-mouth questions (Q1 a synthetic only, Q2 a one CTT two tags, Q3 a AI-family raters, Q4 a cap 4 USD later, Q5 a asking-from-what-HELM-knows next) and start the 0 USD talk pieces, amendment first, test-first." Recorded in `docs/working/helm_ear_mouth_training_v1/OPEN_QUESTIONS.md`.

**What HELM does today, measured by reading `helm_chat.py` at this branch's base (3100636f).** A greeting gets a 3-sentence pitch naming "software engineering, code synthesis, testing, git workflows, or recipe calculations" (recipe-speak on a small-talk turn: M2 broken). "Thanks" and any other line no branch claims gets "I don't have verified data on that in my system, so I won't guess without evidence…" (not how a person talks). A personal line ("my sister …") is kept word for word but answered "Noted. You told me: "…". I've added that…" with no question back (M10 step 3 missing). A feeling is kept as "You shared feeling down: <line>" (not verbatim; M10 step 2 broken) with a canned reply.

### B1. Two switches
- `HELM_TALK` (default OFF). OFF = today's chat byte for byte. ON = B2–B5.
- `HELM_TALK_ASK` (default OFF; works only with `HELM_TALK` ON). ON = B6.

### B2. Which lines the talk layer takes (HELM_TALK ON)
The chat's earlier branches keep their order and their lines: commands, a refresh answer, the session summary, the memory questions (recall, count, "what do you know about me"), explanation requests, **recipe turns** (`loop.wants_turn`), preferences, humour, inventory questions, study requests and agentic goals are unchanged. The talk layer takes, in this order:
1. **The answer to its own question (B6),** when the previous turn asked one.
2. **SMALL** — the line, lower-cased and stripped of punctuation, is a greeting, a thanks, a goodbye-free pause or a check-in from the frozen list `SMALL_RX` (hi / hello / hey / good morning / good afternoon / good evening / how are you / how's it going / what's up / thanks / thank you / ok / okay / cool / got it / sounds good / one sec / hold on / never mind, with up to three trailing words). Reply: one line from the frozen `SMALL_REPLIES` by kind (greeting, thanks, how-are-you, pause). Nothing is saved: no user fact, no stock, no cube.
3. **SELF** — a question about HELM itself, frozen list `SELF_RX` (are you a person / human / robot / bot / ai; who are you; what are you; what can you do; how do you work; do you remember; do you forget; can you remember). Reply: one truthful line from `SELF_REPLIES` (what HELM keeps in this chat and what it cannot do), no claim of an ability it lacks. Nothing saved.
4. **OFF** — a statement (no "?", not opening with a question word) that the earlier branches did not take, **including the lines today's personal-narrative and affect branches take** (with HELM_TALK ON those two branches yield to the talk layer). Reply = M10 (A-TALK-1 §3): (a) one reaction line from `OFF_REACT` chosen by cue words (a worry/strain cue, a good-news cue, else neutral); (b) the line kept **verbatim** in `user_facts` (the existing 20-item list); (c) one question: B6's question when that switch is on and the line names something HELM holds, else one question from `OFF_QUESTIONS` filled with one word of the person's own line (B4).
5. **WORLD** — a question no earlier branch took. Reply: "I don't know that. Nobody has told me about it." (carries the voice's `nodata` marker "don't know"). Nothing saved.
Intents recorded: SMALL and OFF as `GENERAL_CONVERSATION`, SELF and WORLD as `GENERAL_KNOWLEDGE_INQUIRY` (the existing plain intents, so the cube oscillation's observer still sees them), with `entities["talk"]` = the kind. The talk layer never calls the old cube-store turn processor, so no cube is written by a talk turn.

### B3. The guards on every talk reply (program checks; a reply that fails one is replaced by the safe line "Thanks for telling me." and the failure is logged)
- M1: `helm_voice.cas_tokens(reply) == []`.
- M2: the frozen `RECIPE_SPEAK_RX` (the talk packet's list, A-TALK-1 / TEACH readers) does not match, except a word the person typed in this line.
- M7: `helm_voice.sentence_count(reply)` is 1 to 3; no line starts with "-" or "Status".
- Opinion: the frozen `OPINION_RX` (I think / I believe / I feel that / I like / I love / I hate / in my opinion / that's (good|bad|great|terrible|wrong|right) / you should) does not match.
- OFF only: exactly one "?"; every content word of the question is a word of the person's words this session, a name HELM holds (a cube thing, a stock name) or the template vocabulary.

### B4. The one-word question for an OFF line (no parsing beyond word lists)
The word is the person's first capitalised word that is not the line's first word, not a month and not "I"; else the longest content word of the line (the compactor's own `content_words`) that is not a feeling word; ties by first appearance. Templates (`OFF_QUESTIONS`, one chosen by the line's word count, so a replay is exact): "What's going on with {w}?" / "How is {w} going?" / "What happened with {w}?". No word found: "What happened next?"

### B5. What the switch never changes
Recipe turns, the brain, the voice's receipt guard, stock, the cube oscillation, memory compaction, the Eye, agentic goals. A talk reply is printed and recorded exactly like today's replies.

### B6. Asking from what HELM knows (HELM_TALK_ASK ON; Q5)
- **When:** on an OFF or SMALL line that names something HELM holds: (i) a cube thing — a `thing_<name>` node in the cube store that has a current branch (the newest per source, target and kind), named by its name in the line; or (ii) a stock name the brain holds an amount for, named in the line. The first such thing in the line is chosen; cube things before stock.
- **The question:** cube: "You told me {Thing}, {kind}, {Target}{: amount}. Is that still right?" (the cube oscillation's own answer phrase); stock: "You told me we have {amount} of {name}. Is that still right?" (the voice's `say_amount`). For an OFF line it replaces B4's question (one "?" in the reply); for a SMALL line it follows the small-talk reply.
- **The answer (the next line only):** a yes from the frozen `YES_RX` (yes / yeah / yep / right / correct / that's right / still right) → cube: the thing's cube gets a new revision with provenance `CHECKED` and an Atlas FACT node (the existing `CubeOsc.confirm`), reply "Thanks, I'll keep that as checked."; stock: no write, reply "Good, I'll keep it as it is." A no from `NO_RX` (no / nope / not anymore / that's wrong / it changed) → no write, reply "Okay. Tell me what it is now and I'll update it." Anything else → no write, the line is handled as a normal turn.
- Never asked twice about the same thing in one session; at most one question per turn.

### B7. Tests first (written and failing before the code)
Switch OFF leaves every reply of a fixed sample identical; each B2 kind with ON; each guard (a forced failing reply falls back); M10's three parts on an OFF line; nothing saved on SMALL/SELF/WORLD; verbatim keeping on OFF (including a feeling line); B4's word choice and replay determinism; B6: a held cube thing named → the question; "yes" → `CHECKED`; "no" → nothing written; a stock name → the stock question; never twice; HELM's existing suites stay green.

### B8. Measured, not claimed
A builder's sample set (lines written by the operator for this build, labelled `BUILDER_SAMPLE`, never exam text): per kind, the reply with HELM_TALK OFF and ON, counted for M1, M2, M7, opinion, one question back, kept verbatim, nothing saved. These are facts about the builder's own lines; they license nothing. The exam that could earn a word is the talk packet's (`TALK EXAM at 1 USD`, AI-written, keyed, sealed), not run here.

### B9. Not in this build
The ear's `NOTHING_TO_SAVE` output and its retraining (`TALK TRAIN`, now inside the Q4 job capped at 4 USD), the trained mouth (Part M), tone from the C-domain states, an exam, any opinion or outside knowledge. HELM has no large language model inside; every talk reply is a template plus the person's own words or HELM's stored records.
