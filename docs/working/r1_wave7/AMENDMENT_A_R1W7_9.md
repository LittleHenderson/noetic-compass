## 21. Amendment A-R1W7-9 (v8, written BEFORE the v8 reseal; the HELM cut moved to the reader v7.1 fix after v7's own practice reading; two changes, nothing else; 2026-10-21)

**Why.** The v7 package (zip `42c044a905f6101b97a95a440554fec2d8fa4dc16196dcbc44e484993054dfaa`, freeze `ce74ccff…`,
HELM cut `47440415`, amendments A-R1W7-7 and A-R1W7-8, line `CHAT WAVE 5 at 1 USD`) was sealed but is **VOID FOR LAUNCH**:
its own practice run from the seal (run9, `PRACTICE_READINGS_V7.json`, `CONV_PER_ITEM_FROZEN_RUN9_VS_RUN8.json`) read mark
K3 SAFE **false** on practice — X7_CONV `CHAT_ON` 59 right / **4 WRONG** / 1 undetermined, X7_NOISE `CHAT_ON` 59 / 4 / 1,
X7_CONV `LOOP_ON` 57 / 2 / 5 — where v6's run8 read 43 / 0 / 21. The four wrong were the `S1_WISDOM_STATED` items CV32, CV33,
CV34 and CV37: the stock sentence's clause named the held ingredient by a longer phrase ("the sifted flour" for a held
"flour") or a hyphenated form ("corn-starch" for "corn starch"); the v7 face reader read `FACE_UNREAD` or `NONE`; the stock
stayed recorded; and the question answered from it as if the clause had never been said — a wrong answer where the v6 reader
had asked. No approval record was written against v7, no exam was drawn from it, and its line was not consumed (SPEC 7.113).
The fix is reader **v7.1** (SPEC 7.113; PR #437, merged on the thread; thread head `b10da2cd` after PR #438, a hub change
that touches no HELM file): `helm_faces_in.py` v2.1 (in names-as-given mode the name slot allows up to three words before a
given name and resolves the phrase to the held name; a two-word name matches with a hyphen or a space either way; two held
names inside the phrase → `FACE_WHICH_INGREDIENT`) and `helm_wide_turn.py` reader `RB-W1 v7.1` (a clause the face reader
cannot read withdraws the named ingredient's amount from the wide stock on the wide path and on the licensed-recorded path
alike, so the next question asks for it instead of answering; v7's pending-ask mechanism is removed); `test_helm_reader_gap.py`
grows to 28 tests; `test_helm_cas_address.py` carries the recomputed OFF-path pin
`2c8ba0196921e42ab654cd850032ee5da0e5687b60b809e6cbfa337ea6a01a55` over the same machine-neutral canon. **v7 is
`VOID_SUPERSEDED_BY_V8`** for any launch (nothing of v7 is moved or deleted; its seed bands 2,024–2,029 M stay reserved and
were never drawn).

**What changed in this package (v8). Exactly these two, nothing else.**

1. **`helm_now/` recut at `b10da2cd2c78317f5983fa8460ac137c8034556b`** by the contract's rule (the v7 cut's 167 files + every
   `helm_*.py` / `test_helm_*.py` at the commit; `helm_test_pins.py` named explicitly; each by `git show`, never the working
   tree): **167 files, the same names as v7**; four files changed — `helm_wide_turn.py` `47994f77…` (reader `RB-W1 v7.1
   (2026-10-21)`), `helm_faces_in.py` `642451f2…` (v2.1), `test_helm_cas_address.py` `1c330d70…` (pin `2c8ba019…`),
   `test_helm_reader_gap.py` `cd523303…` (28 tests); every other file equal to v7's cut; `helm_brain_canonical.py` = base
   `d4488f2a` `24df53c9…`. `contract/HELM_CUT_R1W7.json` carries the commit and all 167 hashes. The wide reader's ask
   statuses are unchanged in kind (every one begins `CLARIFY`, so RB-W1T's `keys_rbw1t.is_asking` prefix rule counts it as an
   ask; checked by program, `ASK_PREFIX_CHECK_v8.json`); the reader's rules are not changed.
2. **Seed bands and labels.** Bands (section 10 superseded again): REAL 2,030,000,001-2,031,000,000; CONV
   2,032,000,001-2,033,000,000; NOISE 2,034,000,001-2,035,000,000 (each 1,000,000 wide; below INT32_MAX 2,147,483,647). Used
   table 1-2,029,000,000 as one range (everything up to v7's 2,024–2,029 M, which the void v7 seal reserved and never drew;
   the continuity packet's reserved 1,996–1,999 M and the talk packet's reserved 2,018–2,022 M inside it); gap 1,000,000; slot
   stepping and STOP as before. Labels: `PACKAGE_VERSION` = `v8`; the cut commit in `kit/run_r1w7.py` and the stage note;
   `RUN_LIMITS_R1W7.json`; README; the custodian procedure; FROZEN re-derived from the constants (the kit test checks they
   agree); the tests that pin the bands, the blocked table and the cut size.

**Kept exactly as v7 (checked by the tests and the freeze):** the host's HELM self-check list of **12 names** (`kit/run_r1w7.py`
`HELM_TESTS`; the A-R1W7-6 rule kept: the seal step runs exactly that list with the host's command form from a fresh extract and
records it in `TEST_COUNTS_R1W7_v8.json` under `host_exact_suite_list`); **amendment A-R1W7-7** as applied (the same one import
and one hook in `custody_w7.make_all`; the same measured effect on the practice draw, 6 of 128 items `NOT_SCORED`); the
exclusion list with block `X7v6_c54` as its last block (no exam was drawn since job c54, so nothing is added); **the owner's
line `CHAT WAVE 5 at 1 USD`** (20 UTF-8 bytes; A-R1W7-8 proposed it for v7, no approval record ever bound it to the v7 zip,
so it may bind the v8 zip and no other; whether it stands is the owner's word); seed text
`H = sha256(UTF-8("CHAT WAVE 5 at 1 USD" + ":" + <v8 zip sha256, 64 lower-case hex>))`, no trailing newline; cap 1.00 USD;
one attempt + one plumbing retry; the v4 reader (`r1w7.merge_r1w7 v2`), the v4 recorder unit and fixture, every mark,
threshold, arm, status word, exam size, instrument row and hard gate; the noise sentences; the five neighbours by freeze; the
practice pools; the scoring functions; the units and their commands.

**What this amendment does not do.** It does not re-read c54. It does not launch. It does not draw an exam. It licenses
nothing. Reader v7.1 is `ENGINEERED-NOT-VALIDATED` until a sealed draw. The practice run from the v8 seal (run10) is read
beside v7's run9 and v6's run8 in `PRACTICE_READINGS_V8.json`, every differing number with its cause; a WRONG dialogue
answer remaining on practice is a STOP (recorded, `FLAG_FOR_HUMAN_REVIEW`, HELM not changed in the seal). A fresh draw can still
miss a mark on a shape no practice run has shown.
