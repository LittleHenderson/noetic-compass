# Build v2 record — HELM cube oscillation behind `HELM_CUBE_OSC` (default OFF), FIX FIRST, 0 USD (2026-10-21 PDT, laptop)

Owner's words (2026-10-21, verbatim): "1.A, 2.A, 3.A.(WE MAY NEED MORE THAN 3 ROUNDS SO JUST KEEP THAT IN MIND), 4.A,5.A
FOR TEST THEN C FOR REAL LIFE, 6.A,7.A, 8.CUBE EXAM at 1 USD"; then, offered a separate session for the build, "Do it here".

Claim state: **`ENGINEERED-NOT-VALIDATED`.** Built and unit-tested on the laptop. Nothing trained, nothing scored, no
exam drawn. The build specification was frozen before any code: A-TEACH2-2 (`ec3d65fc…`, commit `eb4c9520`) and
A-TEACH2-3 (`fdf912d2…`, commit `f19c66c4`).

## 1. What was built (commit `0cf970a0`)

| File | Change |
|---|---|
| `helm_cube_osc.py` | new: the rule reader (B2, with A-TEACH2-3's first-word rule); the proposer interface and a test-only `StandInProposer` (**not the CTT**, `is_ctt = False`); the round (unanimous proposal → brain-side check → plain say-back → re-read); keep after 2 agreeing rounds in ≤ 3; shadow rounds 4–6 reported, never stored; one cube per (thing, slot), corrections as new revisions with the history kept; the Atlas endpoint (`thing:<x>` CONTEXT, `cube:<id>:r<n>` POSSIBILITY, `fact:…` on confirmation); current-value answers (`EXACT` only while the person's line is fetchable); the fading ladder S0 → S1 → S2 every 4 turns with exact-fraction mass; arms OSC, ONE_READER, CTT_ONLY, TABLE, TABLE_OSC, ONE_STEP_FADE |
| `helm_memory.py` | the switch: `cube_osc` is `None` when OFF; a per-turn hook on the ON path only |
| `helm_chat.py` | the memory-recall branch asks the cube oscillator first, only when ON |
| `test_helm_cube_osc.py` | new, 38 tests |

## 2. FIX FIRST record (Python 3.14.0, pytest)

| Step | `test_helm_cube_osc.py` |
|---|---|
| (a) module absent | collection error |
| (b) module built | **1 failed, 36 passed**: the byte test (below) |
| (c) S2 record made lean; the byte test rewritten to pin the measured truth; the chat test added | **38 passed** |

Every HELM suite, both switches OFF, committed tree: **392 passed** (the 335 before + 38 new + 19 from the merged
EYE-ACT-1 work on the thread). With `HELM_CUBE_OSC=1` forced, the three memory suites: 76 passed, 1 failed, and that
failure is by design: `test_helm_memory_compact.py::test_off_path_is_todays_fifo` checks the OFF path of
compaction, but turning cube oscillation ON attaches the v1 compactor (the ladder's S1 is v1's capsule).

## 3. The measured finding: fading costs space on short lines (reported to the owner as a decision)

On a 72-line practice chat (lines 31–105 bytes), budget 6:

| Item | Bytes (median) |
|---|---|
| a person's line | **31** |
| an S1 capsule (v1's record: CAS sentence and notation, clues, binds, breadcrumb with the cold path, mass, receipt, Atlas address) | **813** (the breadcrumb alone 321) |
| an S2 record before D-BUILD-3 | 592 |
| an S2 record, lean (D-BUILD-3) | **363** |
| working memory at the end | **49,863**, against **2,238** for never forgetting |

In plain words, each faded memory carries its fingerprint, receipt and cold-copy address, so that HELM can prove a
memory was not changed. For short sentences that proof is many times bigger than the sentence. The design goal "to
save space" (owner item O5) is not met by this record format. The mark S-SPACE of TEACH-2 (≤ ½ of VERBATIM_ONLY's
bytes) would fail by a wide margin, and TEACH-1's compaction had the same property, unmeasured until now. Options for
the owner, none taken here: fade several lines together under one capsule, breadcrumb and receipt; shorten
fingerprints; count space differently. Each is a design change that needs the owner's word and an amendment before
TEACH-2 is sealed.

## 4. Build deviations (recorded, small)

- **D-BUILD-1.** "replaces X" is read as a replaced value, and "replaces" is a discourse word, so that B4's own
  say-back line ("… This replaces eight.") reads back to the same reading. Found by the round tests.
- **D-BUILD-2.** "one" is not a value number word (it is also a pronoun: "One more thing: …").
- **D-BUILD-3.** The S2 breadcrumb keeps the capsule id, the cold copy's sha256 and the turn ids; the cold path is
  rebuilt from the capsule id and the cold folder.
- **Not wired yet:** a refresh confirmation in the chat does not yet call `confirm` on the bound cubes (the function and
  its test exist); the real CTT adapter (with the retraining step).

## 5. Cost

0 USD. Laptop only. Nothing trained; no GPU; no host.
