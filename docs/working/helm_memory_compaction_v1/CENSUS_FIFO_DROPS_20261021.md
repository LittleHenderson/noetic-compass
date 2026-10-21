# Census: does HELM's chat memory ever fill today? (DESIGN §8 step 1; OPEN_QUESTIONS Q2; 2026-10-21 PDT, laptop, 0 USD)

Owner's word (2026-10-21, verbatim): `“add them”; OPEN_QUESTIONS Q1–Q3 in one line (recommended: “build v1, rule capsules, census first”).` This is the census. Counts only. No code changed. No claim.

## 1. The rule being measured

`helm_memory.py` (thread head `0b9ce50a`): `HELMConversationalMemory(max_turns=50)` keeps the last 50 turns in working memory; when a 51st turn is recorded the oldest is dropped from working memory (`self.turns = self.turns[-self.max_turns:]`). Every turn is still appended to the session's JSONL ledger on disk. `WorkingMemoryContext.add_user_fact` caps `user_facts` at 20.

The STOP floor frozen in OPEN_QUESTIONS Q2: fewer than 8 dropped turns across the four sealed chat sessions means the squeeze does not matter yet.

## 2. What was counted

| Source | What it is | Sessions / files | Longest single session | Turns the FIFO dropped | `user_facts` cap reached |
|---|---|---|---|---|---|
| Wave 7 chat exams c51–c54 (spec §7.101, §7.104, §7.106, §7.108) | one fresh chat session per real recipe and per dialogue (PREREGISTRATION_R1W7 §2: "one fresh session per dialogue or recipe, one `handle_turn` per line") | 4 runs × (94 to 101 recipes + 64 dialogues) | dialogues: 3 to 5 turns + 2 inserted small-talk turns = **at most 7** (by the sealed design); recipes: one line per recipe line plus the question — **not counted here** (the run logs are in `Documents\Codex\2026-10-20\r1_wave7\`, which this session may not touch while job c55 runs) | **0 on every dialogue** (7 < 50); recipes **not counted** | **0** (the exams state no personal facts) |
| Laptop chat logs `sessions/*.jsonl` (not git-tracked; written 2026-10-18 by `helm_chat.py` test runs and six live `helm-session-*` runs) | the JSONL ledgers of 26 sessions, 344 records in all | 26 files | highest `turn_id` in any file: **8** (`test-session.jsonl`); the two files with more than 50 records (`test_seq_7turn.jsonl` 91, `test_seq_a.jsonl` 65) are one fixture appended by 13 repeated runs, each run starting a fresh memory (`turn_id` never above 7 and 5) | **0** (8 < 50) | **0**: 17 `USER_NARRATIVE` records in all, at most 1 per run |
| `helm_ui/sessions/` (the default session folder) | — | **0 files** | — | — | — |
| `HELM_DISTRIBUTION_PACKAGE/sessions/` | the same four test fixtures, shorter copies (7, 5, 3, 1 records) | 4 files | 7 | 0 | 0 |

## 3. Reading, by the frozen floor

- Dropped turns counted: **0** of a floor of 8. 🟥 **STOP_NOT_EXERCISED**: today's sessions never fill the 50-turn window, so the thing compaction replaces (the silent drop) has never happened in any recorded session.
- Gap in the census, stated plainly ⬜: the recipe sessions of c51–c54 were not counted. A recipe session is one line per recipe line plus one question; the wide brain refuses recipes of more than 10 ingredients (`MAX_INGREDIENTS = 10`), but a book line count above 50 cannot be ruled out from here. Anyone with read access to the run folders can close this gap in minutes: count lines per `handle_turn` session in each run's chat record and report the maximum.
- Found while counting, not fixed (no `helm_*.py` edit in this packet) 🟧: `add_user_fact` keeps the **first** 20 facts (`self.user_facts[:20]`), while its comment says "keep last 20". After 20 facts, every new one is silently discarded from working memory (the cube store still gets it). A one-line fix and a test belong to the build of v1, not here.

## 4. What this means for the owner's order "build v1, rule capsules, census first"

By the floor as frozen, build v1 **waits for the owner's word**. The designer's reading, offered and not decided: the census measures exams designed before any long conversation existed; every session was short on purpose. TEACH-1 itself is the first design with sessions longer than the budget (32 teaching turns against a budget of 12), so the squeeze is created by the test, not found in the past. The owner may (a) hold v1 until a long-session use exists, or (b) override the floor by word and let TEACH-1 be the first long session. Recommendation: (b), at 0 USD, with the `user_facts` slip fixed in the same build.

## 5. Claim state

Counts only, from files on this laptop and the sealed packet texts on the thread branch. Nothing run, nothing scored, no claim. The compaction design stays `PROPOSED`.
