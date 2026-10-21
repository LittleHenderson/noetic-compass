# HELM continuity of thought — design v1: the station path wired into the live chat behind one switch (2026-10-20 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Every mechanism named here keeps its claim status `ENGINEERED-NOT-VALIDATED` (built and tested on its own; no result about HELM's behaviour). No claim moves by this document.

Owner's order (2026-10-20): "continuity packet". Owner's idea, verbatim (2026-10-15, about 4:40 AM Pacific): "THE LANGUAGE PORTION SHOULD MOVE ACROSS THE a RPA's CJTs it's bias, the bias asom, the RPM AND THE NEXT RPA AND OR CJT or the next RPA and soon on to create a continuity of thought or follow a continuity of thought ... LIKE INTERRUPTING A PERSON WHILE THEY DEEP IN THOUGHT OR ASKING SOMEONE TO THINK ABOUT SOMETHING". Owner ruling (2026-10-15, about 12:30 PM PDT): "RPA IS ATLAS I MEANT ATLAS" (spec sheet §7.35 tail).

## 0. Plain words first

Today HELM thinks in one pass. A line comes in, the loop walks it through its stations in one go, and a reply comes out. Nothing is left "in progress" between lines. So HELM cannot be interrupted, because there is nothing to interrupt, and it cannot pick a thought back up, because no thought is ever put down.

This design adds one thing: a **thread**. A thread is a thought that is still going: it has a start place in the Atlas (the map HELM keeps of what it knows and what is possible), it has walked some stations, and it has steps left. When a person types a line while a thread is open, the thread is **cut** at the station boundary it is on, the line is answered exactly as today, and afterwards the thread is picked up again **by its coordinate** (a six-field return address), never by remembering "what was I doing". If the line changed a fact the thread relied on, the thread is marked dirty and started afresh, honestly, rather than resumed.

The whole thing sits behind **one switch, default OFF**. OFF means today's HELM, byte for byte in what it writes.

Terms used on this page, each defined once:
- **Station**: one step of HELM's thought path. S0 is the Atlas anchor; S1 the trigger (which recipe the line calls up); S2 the Bias read (the working memory: this session's verified stock and learned requirements); S3 the arrival (the yield and the limiting reagent: the ingredient that runs out first); S4 the ASOM readout (a label that is recorded and never consulted; the loop v3 proves it cannot gate); S5 the RPM gate (HELM's one gate: proceed, repair, or refuse, with the disengage ladder when it cannot proceed); S6 the next station (the reply, or the next Atlas entry).
- **Atlas**: the Recursive Possibility Atlas, HELM vision ability 6, the real model bound by `continuity_build_v4` at commit `eb998556` (`stations.bind_s0_to_atlas`). "RPA" means this and nothing else (owner ruling above).
- **Return address**: the exact place a suspended thought returns to. Six fields, every one required (`return_address/address.py`: `episode`, `branch`, `snapshot_digest`, `bias_version`, `call_id`, `parent_call_id`). A partial match is refused (`INEXACT_ADDRESS`); there is no "nearest".
- **Bias**: the loop's working memory (`the_loop_v3/bias.py`): a versioned, frozen-snapshot store of facts. Every write bumps its version. In the live loop today this is `self.stock` plus `self.bias_version`.
- **Receipt**: the record a saved fact or a crossing leaves behind, with a sha256 fingerprint, chained so a later reader can check it.
- **Digest**: a sha256 fingerprint of a thing's bytes or canonical JSON.

## 1. What exists today and what each piece is allowed to claim

| Piece | Where | What it does | Claim status |
|---|---|---|---|
| The live loop | `helm_end_to_end_loop.py` (`HELMEndToEndLoop.process_turn`, `wants_turn`, `_emit`, `_finish`) | one line in, one reply out; stations are trace rows; the wide brain ON by default (§7.56); the RPM gate and repair performer called inside `_run_request` (fix C, §7.49 update) | `ENGINEERED-NOT-VALIDATED`; the licensed brain inside it keeps its own license |
| The chat | `helm_chat.py` (`HELMConversationalSession.handle_turn`, `_speak`) | memory, intent routing, everyday-English voice, session log; hands a line to the loop when `loop.wants_turn` says so | `ENGINEERED-NOT-VALIDATED`; wave 7 (§7.98) is sealed to score it, not launched |
| The loop v3 | `docs/working/noetic_council/the_loop_v3/` (`loop.Loop.turn`: READ_BIAS, PROPOSE, OBSERVE, GATE, DISENGAGE_OR_CONTINUE; `rpm_gate.py`, `asom.py`, `bias.py`, `disengage.py`) | one turn in five stages, the real gate, the ladder; 35 tests written | `ENGINEERED-NOT-VALIDATED`; "MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM." |
| The return address | `docs/working/noetic_council/return_address/` (`address.ReturnAddress`, `stack.ReturnStack.suspend / resume / finish / cancel`, `dirty.mark_dirty / invalidate_ancestors`, `atlas_binding.glue_back`) | the rules for suspending and resuming an exact thread; 27 tests written | `ENGINEERED-NOT-VALIDATED`; "MECHANISM ONLY. NO CIRCUIT USES THIS YET." |
| Continuity v4 | `docs/working/noetic_council/continuity_build_v4/` (`stations.bind_s0_to_atlas`, `make_crossing`, `continuity.ContinuityPath`, `provenance.classify` FOLLOWED / CREATED / ATTEMPTED, `disengage.run_ladder`) | the station path as data: points per crossing, the S0 anchor on the real Atlas, seams, provenance words; 50 tests, 50 passed on disk | `ENGINEERED-NOT-VALIDATED`; "MECHANISM ONLY. S0 ANCHORS TO THE REAL ATLAS MODEL AT COMMIT eb998556; THIS BUILD ADDS NO ATLAS OF ITS OWN. NO LANGUAGE PASSED ACROSS IT." |

What the record says about them together (§7.48): nine mechanisms, "mechanisms built; brain integration missing" (Codex audit, 2026-10-17). Queue row 15, one live end-to-end trace through Atlas anchor -> proposal under Bias -> ASOM readout -> RPM gate -> next station, is still TODO. LM-T4 (§7.35) carried language station by station but with the superseded reading of S0, so no claim that language crossed an Atlas is licensed, and mark CONT-3 (provenance keys) failed at 99.92%.

Nothing in this packet changes any of those words.

## 2. The switch

- Name: `HELM_CONTINUITY` (environment variable). Function `helm_continuity.continuity_on(flag=None)`.
- **Default OFF.** ON only by `HELM_CONTINUITY` = `1` / `ON` / `TRUE` / `YES`, or the loop built with `continuity=True`. Off-words `0` / `OFF` / `FALSE` / `NO` are honoured too, so the switch reads like `HELM_WIDE_BRAIN` (spelled in both places, not imported, so an OFF loop never imports the module; a test pins the two tuples equal).
- OFF: `helm_continuity` is never imported; `helm_end_to_end_loop.py` and `helm_chat.py` run today's code path; every trace row, receipt and receipt hash is byte-identical to the pre-change code (pinned by a fixture test, as `CAS_ADDRESS` OFF is pinned to `56f356ea…`).
- ON: the hooks in section 4 run. Routing (`wants_turn`), the readers, the brain, the voice and the store are untouched; the thread book only records, suspends and resumes.

Why default OFF: the chat is about to be scored for the first time (wave 7, §7.98). A new part is not allowed to be on by default before it has earned a word on a sealed exam (the rule every part in waves 2 to 6 followed).

## 3. What a thread is, as data

One record per thread, schema `thread/1`, written as canonical JSON (sorted keys, no spaces) so its digest is stable:

| Field | Type | Meaning | Comes from |
|---|---|---|---|
| `thread_id` | 16 hex | `sha256(episode + ":" + str(open_tick) + ":" + opening_line)[:16]` | the hook that opens it |
| `episode` | text | the chat session id (`HELMConversationalMemory.session_id`) or the loop's own id when driven directly | chat / loop |
| `anchor` | object | S0: `{node_id, atlas_digest, sort}` from `stations.bind_s0_to_atlas(real_atlas, node_id)` | continuity v4 |
| `return_address` | object | the six fields of `address.ReturnAddress`; `parent_call_id` is `null` only on a root thread and must be written out | return address |
| `opening` | object | `{tick, line_sha256, loop_status}` of the turn that opened the thread; the line itself is not stored in the record (the chat's session log has it) | loop |
| `crossings` | list | one entry per station crossed: `{station, tick, point or "FORM_GAP", pointer, provenance}` where `provenance` is FOLLOWED / CREATED / ATTEMPTED (`provenance.classify`) | continuity v4 |
| `cited_facts` | list | the Bias keys the thread's proposal cites (loop v3 `Proposal.cites`), each with the version it was read at | loop v3 |
| `remaining_work` | list | ordered named steps still to do, e.g. `["S5:recheck_gate", "S6:reply"]`; never empty while the thread is OPEN | return address `stack.Thread.remaining_work` |
| `bias_version_at_suspend` | integer | the Bias version when the thread was last suspended | loop |
| `brain_digest_at_suspend` | 64 hex | sha256 of the brain's recipe book bytes plus the canonical JSON of `self.stock` at suspend | loop |
| `state` | word | OPEN / WAITING / FINISHED / CANCELLED / DIRTY / INVALID (the `stack.Thread` states, no new ones) | return address |
| `receipts` | list | the thread's event chain: each `{event, seq, sha256}` where the sha256 covers the previous entry's sha256 plus this event's canonical JSON; the first carries 64 zeros | return address `ReturnStack.receipt()` |
| `thread_digest` | 64 hex | sha256 of the record's canonical JSON with `receipts` and `thread_digest` removed | the thread book |

The book that holds threads (`helm_continuity.ThreadBook`) keeps: one `ReturnStack`, one `ContinuityPath` per thread, the Atlas handle, and a dict `threads` by `thread_id`. It is in memory for the session and written to the session log folder (`HELM_SESSION_DIR`, as the chat's own log) as `threads.jsonl`, one line per state change. Nothing of it goes into the cube store: **a thread never writes a fact until it finishes through the gate** (the write is the gate's, as today).

### 3a. Where threads come from in the live loop

A thread opens only when a turn ends with work left. In today's loop that is exactly one of:

1. The turn ends `WAIT_FOR_USER` (a `CLARIFY_*` status: the reader or the gate asked a named question). Remaining work: `["S5:recheck_gate", "S6:reply"]`; `cited_facts` = the slot named in the question plus the stock the request read.
2. The gate at S5 says `REPAIR` and the repair performer opens a child (`repair_performer/actor.py`). The parent thread's remaining work is `["S5:await_child:<call_id>", "S5:recheck_gate", "S6:reply"]`; the child is its own thread, `child_of(parent_address, call_id)`.

A turn that ends `DONE` or `STOP` opens no thread (its path is recorded as a FINISHED thread with no remaining work, for the record only). So with the switch ON, HELM answers every line exactly as today; the only new behaviour is what happens when a later line lands on an OPEN thread.

### 3b. "Interrupted"

A thread is interrupted when a chat turn arrives (a non-empty line that is not one of the chat's commands `exit` / `quit` / `q` / `help` / `dials` / `history` / `mode`) while a thread is OPEN. It does not matter whether the line is for the loop (a stock line, a question) or not (small talk, a memory question): every line interrupts. The interruption is one bounded act, the **cut**:

- the thread stops at the station boundary it is on (crossings are atomic; the one in progress completes, the next does not start);
- `ReturnStack.suspend(address, bias_version, payload, remaining_work=...)` writes the suspend record; the thread is WAITING;
- the chat turn then runs today's path, untouched.

The cut costs one record write and no station work, so the conversation does not wait on the thread (mark CUT in the exam measures exactly this, and can fail).

### 3c. "Resume by return address"

After the chat turn's reply has been printed (never before), the book looks at the WAITING threads:

1. **Stale check.** For each `cited_facts` entry, the current Bias value and version are read. If any cited fact changed since `bias_version_at_suspend`, the thread is `mark_dirty(reason)` and `invalidate_ancestors` runs (return address rule 5, Theorem 27.3: a dirty child invalidates the chain above it). A dirty thread is not resumed; if the opening request is still answerable it is re-opened as a **new** thread with a new anchor and a new address, and the record says `RESTARTED_DIRTY`. This is the honest behaviour and the exam checks it (gate H7).
2. **Slot check.** If the thread's remaining work begins with `S5:recheck_gate` and the chat turn did not fill the named slot, the thread stays WAITING (no work, no reply).
3. **Resume.** Otherwise `ReturnStack.resume(address, returned_bias_version=current, payload)` with the **exact** six-field address from the record. The stack refuses an inexact address, a cancelled or finished thread, or a Bias that is older than the one at suspend. On success the thread runs its `remaining_work` in order from the saved station, writes each crossing to its `ContinuityPath` with provenance FOLLOWED (the pointer existed before this tick), and finishes through the gate as today. The reply of a resumed thread is the loop's normal reply for that request.

"By coordinate, never by memory" means: the resume point comes from the address record and nowhere else. The book never reads the chat's memory (`helm_memory`), never reads the last line of chat, never searches for "the thread that looks like this one". A thread id, a nearest address or a root shortcut are refused by the return-address package (`NO_SUCH_THREAD`, `INEXACT_ADDRESS`, `NO_ROOT_SHORTCUT`). Two open threads are told apart by address alone (family F-D in the exam).

### 3d. "Cut when conversation starts"

The cut is the rule in 3b applied at the first moment a line is known to exist: the top of `handle_turn` in the chat, and the top of `process_turn` in the loop (for a loop driven directly). After the cut, no crossing carrying the thread's `thread_id` may be written until the reply for that line has been returned. The exam's mark CUT counts crossings with a thread id inside each chat-turn window `[tick_in, tick_reply]`; the number must be 0. Unlike wave 3's H14 (§7.69, open question 2: awake ticks never carried the counted key, so the check read 0 by construction), here every crossing carries `thread_id` and `tick`, and the window is the chat turn's own, so an implementation that forgets to cut shows up as a non-zero count.

Idle advance (a thread moving on its own between lines, as the drive loop does on idle ticks) is **not** in v1. A thread advances only inside the turn that opened it and on resume. The exam harness, not the chat, drives the stations one at a time (`ThreadBook.idle_tick()`, test-only) so that an interruption can land between stations. Whether the chat gets idle advance later is the owner's (OPEN_QUESTIONS Q5).

## 4. Exactly which functions get a hook, and what each hook does

One new module, two hooked files, no other `.py` touched.

### 4a. New module `helm_continuity.py` (the only place the rules live)

- `CONTINUITY_OFF_WORDS = ("0", "OFF", "FALSE", "NO")`, `CONTINUITY_ON_WORDS = ("1", "ON", "TRUE", "YES")`, `continuity_on(flag=None) -> bool` (default False).
- `class ThreadBook(loop)`: holds the `ReturnStack`, the Atlas handle (`continuity_build_v4.atlas_adapter`), `threads`, the session log path. Methods: `cut(tick)`, `open_from_result(result, tick)`, `after_reply(tick)` (stale check, slot check, resume), `idle_tick()` (test-only, one crossing), `digest()`, `records()`.
- `strip_thread_fields(rows)`: removes `thread_id`, `thread_station` from trace rows before the receipt hash, so the hash is identical ON and OFF (the `cas_address` precedent).
- Imports the three packages from `docs/working/noetic_council/` by path, the way the loop already imports `the_loop_v3/rpm_gate.py` and `repair_performer/actor.py`.

### 4b. `helm_end_to_end_loop.py`

| Function | Hook (ON only; OFF runs today's line) | Lines added (estimate) |
|---|---|---|
| `HELMEndToEndLoop.__init__` | after the wide switch block: `self.continuity = None`; if `continuity is True or (continuity is None and env says on)`: `import helm_continuity; self.continuity = helm_continuity.ThreadBook(self)`. OFF never imports. | 6 |
| `process_turn` | first line: `if self.continuity is not None: self.continuity.cut(tick)`. Last line (both the wide and the licensed path return through here): `if self.continuity is not None: self.continuity.open_from_result(result, tick)`. No change to what the turn returns. | 4 |
| `_emit` | when `self.continuity is not None` and a thread is running, add `thread_id` and `thread_station` to the row. The receipt hash in `_finish` is computed over rows with those two fields stripped (same pattern as the CAS address). | 3 |
| `_finish` | the stripping call above. | 1 |
| `wants_turn` | **no hook.** Routing never changes. | 0 |

### 4c. `helm_chat.py`

| Function | Hook (ON only) | Lines added (estimate) |
|---|---|---|
| `handle_turn` | after the command branch (`exit` / `help` / `dials` / `history` / `mode` return early and do not interrupt): `book = getattr(self.loop, "continuity", None); if book: book.cut(self.turn_count + 1)`. At the very end of the function, after every `record_turn` path has printed its reply: `if book: book.after_reply(self.turn_count)`. The second hook is placed by wrapping the body in a `try/finally` so every early `return` still reaches it. | 6 |
| `_speak` | **no hook** in v1. Whether a resumed thread says "Picking up where I left off" is the owner's (Q6). | 0 |

### 4d. Tests that come with the build (not with this packet)

- OFF: `helm_continuity` not imported in a fresh process; a 13-turn fixture's trace rows and receipts hash to the pinned pre-change sha256.
- ON: receipt hash identical to OFF on the same fixture; every row with a thread has `thread_id`; a thread's `thread_digest` is stable across a save/load of `threads.jsonl`.
- Resume refuses: an address with one field changed; a cancelled thread; an older Bias; a root shortcut.
- Dirty: a cited fact changed by the interrupting line marks the thread DIRTY and the chain INVALID; the restart is a new thread.
- Cut: a thread with three remaining stations, interrupted by a small-talk line, writes 0 crossings between the line and the reply, and finishes after.
- The chat's early returns (summary, memory recall, explanation) still reach `after_reply`.

## 5. The sequencing rule against wave 7 (§7.98)

**Chosen: this wiring does NOT land in `helm_end_to_end_loop.py` or `helm_chat.py` before the wave 7 chat test (sealed v3 on HELM cut `dfc7158d`, zip `5063baba…`) has run and been scored and its section is on the spec sheet.**

Why, plainly:

1. Wave 7 is the first sealed exam of the chat window. Its claim sentence is about "HELM's live chat ... as shipped". If the chat files change on the thread branch between the seal and the reading, the sheet would have to say "the chat that was scored is not the chat at head", and the two FIX FIRST rounds (§7.98) show the chat files are where defects hide. One change at a time keeps the reading clean.
2. The sealed package is self-contained (`helm_now/`, 161 files cut by `git show` from `dfc7158d`), so a branch change cannot alter what the host runs. The risk is not to the exam's bytes; it is to what the result may be said to describe, and to the operators' attention while c51 is pending.
3. Honest note on "byte-identical": at today's head `81098868` the cut is already not byte-identical for `helm_end_to_end_loop.py` (cut `5a63391b…`, head `909ddbf1…`; PR #417 "BUILD BOTH" added the CAS address lines), `helm_wide_turn.py` and `helm_brain_wide.py`. `helm_chat.py` is still identical (`3076128f…`). So "keep the cut byte-identical for the files it pins" is no longer achievable for the loop file by any choice made here; what this packet can still protect is `helm_chat.py` and the rule of not adding a third departure before the reading.
4. If the owner wants the wiring sooner, the only form allowed before the reading is a **wrapper**: `helm_chat_continuity.py` subclassing `HELMConversationalSession` and wrapping `loop.process_turn` by attribute assignment (the recorder pattern wave 7 itself uses, D-W7-4), touching neither pinned file, with a test that pins `helm_chat.py` to `3076128f…`. That form is second-best (two chat entry points) and is offered as Q1, not chosen.

## 6. What this design does not do

- It does not make HELM think between lines (no idle advance in v1).
- It does not change any reply HELM gives today when the switch is OFF, and with the switch ON it changes a reply only where a resumed thread answers a question that today would need to be asked again.
- It does not use the chat's memory, the last line of chat, or any similarity to find a thread.
- It does not move any claim. Every status word above stays as the record has it.
- It does not run anything. The exam that would earn a word is `PREREGISTRATION_CONTINUITY_V1.precode.md` beside this file, and it waits on the owner's picks in `OPEN_QUESTIONS.md`.
