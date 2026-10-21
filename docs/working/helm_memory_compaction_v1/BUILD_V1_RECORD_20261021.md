# Build v1 record — HELM memory compaction behind `HELM_MEMORY_COMPACT` (default OFF), FIX FIRST, 0 USD (2026-10-21 PDT, laptop)

Owner's word (2026-10-21, verbatim, the button the owner pressed in the design session): "Override the census floor. Start build v1 of memory compaction now: rule capsules, behind HELM_MEMORY_COMPACT default OFF, FIX FIRST tests, 0 USD, and fix the user_facts [:20] slip with a test in the same build." Then "Do it here".

Claim state: **`ENGINEERED-NOT-VALIDATED`.** Built and unit-tested on the laptop. Nothing scored. No sealed exam has run. TEACH-1 (pre-code sha256 `7eef0edc…`) is the exam that could earn a word. The pre-code is not edited.

## 1. What was built

| File | Change | Lines |
|---|---|---|
| `helm_memory_compact.py` | new: capsule writer, cold store, breadcrumb, receipts, housekeeping, fetch-first recall, searchlight over the Atlas, fit check F1–F4, refresh question with caps, answer (F5) and strengthening, Eye report-only | 1 module |
| `helm_memory.py` | the switch (`compactor` is `None` when OFF: today's FIFO drop, byte for byte); turn ids keep counting when ON; `user_facts` keeps the **last** 20 (was `[:20]`, the first 20) | +17 / −2 |
| `helm_chat.py` | the memory-recall branch asks the compactor **only when the switch is ON** (EXACT / "I don't have your exact words any more" + rebuilt / unknown with a refresh or which-one question) | +15 |
| `test_helm_memory_compact.py` | new, 28 tests | — |
| `test_helm_memory.py` | +1 test (`test_user_facts_keeps_the_last_twenty`) | — |

Frozen numbers in the module (not learned, not tuned): `ACTIVE_TAIL = 2`, `MAX_CLUES = 8`, `MIN_CLUE_LETTERS = 4`, `REFRESH_CAP_PER_THREAD = 2`, `REFRESH_CAP_PER_ITEM = 1`, `MASS_STEP = 1`, `SEARCHLIGHT_RADII = (1, 2, 4, 8)`, `SEARCHLIGHT_CAP = 15`, `CAPSULES_PER_THREAD_NODE = 8`, `WHICH_ONE_AT = 3`, domain `C`.

How the three existing machines are used (DESIGN §3.5): the **compiler** (`noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`, `compile_expression(...).valid`) is the checker of every capsule's CAS notation (F1); the **CCE skin** (`docs/working/noetic_council/language_v3/cce.py`: `parse`, `render`, `normalize`) writes and round-trips the capsule's sentence (F2); the **Atlas** (`docs/working/noetic_council/continuity_build_v2/atlas.py`, `Atlas(max_depth=1)`, kinds `CONTEXT` / `POSSIBILITY` / `FACT`) files capsules and orders the lookup (F4). The **CTT** is not in v1 (OPEN_QUESTIONS Q3, the owner's "rule capsules"). The **CAS SDG** is not used in the build; it is the exam's world generator.

What the capsule sentence looks like (from the smoke run below): `you are composed of "grandfather kept bees south france".` → notation `^5^C`; `you intake "hives counted spring".` → `^1^C`. The frame is picked by the turn's intent (`FRAME_BY_INTENT`): narrative → ^5, affect / humour → ^4, preference → ^2 (^3 when the valence is negative), inventory / recipe → ^1 `store`, everything else → ^1 `intake`. Several frames in one capsule join with `+` (co-presence, Clarification 10).

## 2. FIX FIRST record (counts, laptop, Python 3.14.0, pytest 9.0.2)

| Step | `test_helm_memory_compact.py` | Note |
|---|---|---|
| (a) module absent, thread-head `helm_memory.py` | **collection error** (`ImportError`) | the tests existed before the module |
| (b) module present, `helm_memory.py` not yet wired | **14 failed, 14 passed** | |
| (c) wired; three test expectations corrected (two of mine were wrong about how many turns leave an 8-turn window on a budget of 6, and when to take the cube digest); one real defect fixed (the store's `get_cube` returns a view copy, so provenance must be set on the stored node) | **28 passed** | |

`test_helm_memory.py::test_user_facts_keeps_the_last_twenty` on the thread head's module (imported from `git show`): `len 20, first 'fact number 1', last 'fact number 20'` → **fails**; on the fix: passes.

## 3. Every HELM suite, switch OFF (the default)

`python -m pytest test_helm_*.py -q` with `HELM_MEMORY_COMPACT` unset: **322 passed** (the 294 on the thread head plus the 28 new and the 1 new memory test; counts from the run on the committed tree). One test, `test_helm_triad.py::test_15_sealed_package_untouched`, fails on any uncommitted change to `helm_chat.py` by design and passes on the committed tree. With the switch ON, `test_helm_memory_compact.py` + `test_helm_memory.py`: 33 passed.

OFF path: `compactor` is `None`; `record_turn` keeps `turn_id = len(self.turns) + 1` and the FIFO trim exactly as before; `helm_chat` never calls the compactor. The one deliberate OFF-path change is the `user_facts` cap (`[-20:]`), ordered by the owner.

## 4. Smoke run of the live chat, switch ON (`HELM_MEMORY_COMPACT=1`, budget set to 6 turns, session folder in the scratchpad)

Typed: four bee sentences, four unrelated lines, then "Do you remember what I said about my grandfather?"; then the first capsule's cold copy was deleted and the same question asked again.

- Capsules written: **3**; receipts **3**; Eye writes **0**; Eye report kinds: `UNBOUND_CLUE` (capsules whose turns wrote no cube: the chat's classifier kept only the first bee sentence as a user fact and answered the other three with its "no verified data" line, a chat-side behaviour outside this build).
- Capsule 1: `^5^C`, `you are composed of "grandfather kept bees south france".`, clues `grandfather, kept, bees, south, france`, side `possibility`. Capsule 2: `^1^C`, `you intake "hives counted spring".`, clues `hives, counted, spring`.
- Recall before and after the deletion: "Yes, absolutely: My grandfather kept bees in the south of France." Both times the answer came from `user_facts`, which are verbatim and never compacted (DESIGN §3.3), so the compactor was not consulted. The compactor's own fetch-first path (EXACT, RECONSTRUCTED with a clue-quoting question, UNKNOWN with the which-one question) is exercised by the 28 tests, not by this smoke.
- A stray untracked file `math_utils.py` appeared in the worktree during the later full-suite run; see §5 (the agentic executor's test, not this build).

## 5. Findings kept, not fixed here

- `helm_memory.record_turn` with the switch OFF numbers turns by position (`len(self.turns) + 1`), so after a FIFO drop ids repeat. Kept as is on the OFF path (pinned behaviour). The ON path counts.
- The chat's "no verified data" reply swallowed three of four narrative sentences in the smoke, so only one became a cube and a `user_fact`. That is the chat's intent classifier (spec §7.49 territory), not memory.
- `math_utils.py` appeared untracked in the worktree at 11:03:10, during the full-suite run, written by the agentic executor's own test (`test_helm_agentic_planner.py` names it; `helm_agentic_executor.py` writes it into its workspace root). Not from this build, not from the chat smoke; deleted, not committed.

## 6. Cost

0 USD. Laptop only. No AWS, no GPU, no cloud tier. No new owner line asked for.
