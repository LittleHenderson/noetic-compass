"""Builder tool (NOT sealed): every v5 edit to the package (constants, kit, run limits, tests, README, custodian procedure,
amendment A-R1W7-5 appended). Each edit is an exact once-only replacement; the log names every one. The precode sections
and amendments 1-4 of PREREGISTRATION_R1W7.md are not touched: the amendment supersedes them.

    python -X utf8 -B -I patch_v5.py <v5 package dir> <log json>
"""
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
LOG = Path(sys.argv[2]).resolve()
FIX = "f45a85706a9d8b9177e4b7279453d1538c12045d"
V4ZIP = "8602b1bc98b543e4551e766d9db540d22d6dbc690b788dbbce5c91e4b6c7b712"
log = []


def edit(rel, old, new):
    p = PKG / rel
    text = p.read_bytes().decode("utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{rel}: target not found exactly once: {old[:70]!r}")
    p.write_bytes(text.replace(old, new).encode("utf-8"))
    log.append({"file": rel, "old": old[:90], "new": new[:90]})


# ---- r1w7/common_w7.py
edit("r1w7/common_w7.py",
     "exactly as the code runs at commit dfc7158d (v3, the FIX FIRST round-2 build on thread head 974fe36c / PR #414; amendments A-R1W7-2 and A-R1W7-3)",
     "exactly as the code runs at commit f45a8570 (v5, the FIX FIRST round-3 build on thread head 1d2b390f / PR #425; amendments A-R1W7-2 to A-R1W7-5)")
edit("r1w7/common_w7.py", 'PACKAGE_VERSION = "v4"', 'PACKAGE_VERSION = "v5"')
edit("r1w7/common_w7.py",
     'HELM_CUT_COMMIT = "dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6"       # v3 (A-R1W7-3), unchanged in v4 (A-R1W7-4): FIX FIRST round 2, PR #416 (2 commits on 974fe36c, PR #414: wide brain ON by default)',
     'HELM_CUT_COMMIT = "%s"       # v5 (A-R1W7-5): FIX FIRST round 3 on c52\'s one unexplained ask, PR #425 (1 commit on thread head 1d2b390f); v3/v4 were dfc7158d' % FIX)
edit("r1w7/common_w7.py",
     'HELM_THREAD_BRANCH = "claude/helm-r1w7-chat-wave-packet-20261020 (PR #416 to claude/project-thread-pmbzd6)"',
     'HELM_THREAD_BRANCH = "claude/helm-r1w7-round3-fix-20261020 (PR #425 to claude/project-thread-pmbzd6)"')
edit("r1w7/common_w7.py", 'OWNER_LINE = "CHAT WAVE 2 at 1 USD"', 'OWNER_LINE = "CHAT WAVE 3 at 1 USD"')
edit("r1w7/common_w7.py",
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 and amendment A-R1W7-4, section 16); the approval record is written only after the owner signs"',
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-5, section 17); the approval record is written only after the owner signs"')
edit("r1w7/common_w7.py",
     'BANDS = {"REAL": (2_000_000_001, 2_001_000_000), "CONV": (2_002_000_001, 2_003_000_000),\n'
     '         "NOISE": (2_004_000_001, 2_005_000_000)}          # A-R1W7-4: above v3\'s 1,990-1,995 M and the continuity packet\'s proposed 1,996-1,999 M',
     'BANDS = {"REAL": (2_006_000_001, 2_007_000_000), "CONV": (2_008_000_001, 2_009_000_000),\n'
     '         "NOISE": (2_010_000_001, 2_011_000_000)}          # A-R1W7-5: above v4\'s 2,000-2,005 M (spent by X7v4 / c52); 1,996-1,999 M stays reserved for the continuity packet')
edit("r1w7/common_w7.py",
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; whole range)", 1,\n'
     '                1_999_000_000),)',
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; whole range)", 1,\n'
     '                2_005_000_000),)')

# ---- r1w7/custody_w7.py (exclusion lists: every list applies to both pools, as v4)
edit("r1w7/custody_w7.py",
     '                      "x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv")',
     '                      "x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv",\n'
     '                      "X7v4_c52_real", "X7v4_c52_conv")                  # A-R1W7-5: X7v4\'s ids (job c52)')

# ---- kit
edit("kit/run_r1w7.py",
     "HELM_CUT_COMMIT = 'dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6'   # v3 (A-R1W7-3), unchanged in v4 (A-R1W7-4)",
     "HELM_CUT_COMMIT = '%s'   # v5 (A-R1W7-5): FIX FIRST round 3, PR #425" % FIX)
edit("kit/run_r1w7.py",
     "              'test_helm_wide_alongside']   # the three pytest-style files (chat_nuance, memory, agentic_planner) are not unittest suites",
     "              'test_helm_wide_alongside', 'test_helm_cas_address', 'test_helm_units_note']   # v5: the two unittest files that\n"
     "              # entered the cut with the thread head (A-R1W7-5); the three pytest-style files (chat_nuance, memory, agentic_planner) are not unittest suites")
edit("kit/STAGE_R1W7.json", "cut at dfc7158d (v3, unchanged in v4)", "cut at f45a8570 (v5, FIX FIRST round 3)")
edit("RUN_LIMITS_R1W7.json", '"package_version": "v4"', '"package_version": "v5"')
edit("RUN_LIMITS_R1W7.json",
     "the owner's line to sign is 'CHAT WAVE at 1 USD' (PREREGISTRATION_R1W7.md section 8)",
     "the owner's line to sign is 'CHAT WAVE 3 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-5, section 17)")

# ---- tests
T = "tests_r1w7/test_units_w7.py"
edit(T, "        self.assertEqual(C.USED_RANGES[0][2], 1_999_000_000)", "        self.assertEqual(C.USED_RANGES[0][2], 2_005_000_000)")
edit(T,
     '        self.assertEqual(C.BANDS, {"REAL": (2_000_000_001, 2_001_000_000), "CONV": (2_002_000_001, 2_003_000_000),\n'
     '                                   "NOISE": (2_004_000_001, 2_005_000_000)})\n'
     '        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 2 at 1 USD")',
     '        self.assertEqual(C.BANDS, {"REAL": (2_006_000_001, 2_007_000_000), "CONV": (2_008_000_001, 2_009_000_000),\n'
     '                                   "NOISE": (2_010_000_001, 2_011_000_000)})          # A-R1W7-5\n'
     '        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 3 at 1 USD")')
edit(T, '        self.assertEqual(hc["files"], 161)', '        self.assertEqual(hc["files"], 164)                # v5: + helm_cas_address.py, test_helm_cas_address.py, test_helm_units_note.py')
edit(T,
     '                "X7_c51_real": 128, "X7_c51_conv": 64}                       # A-R1W7-4: X7\'s ids (job c51)',
     '                "X7_c51_real": 128, "X7_c51_conv": 64,                       # A-R1W7-4: X7\'s ids (job c51)\n'
     '                "X7v4_c52_real": 128, "X7v4_c52_conv": 64}                   # A-R1W7-5: X7v4\'s ids (job c52)')
edit(T,
     '        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv"):',
     '        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv", "X7v4_c52_real",\n'
     '                     "X7v4_c52_conv"):')
edit(T,
     '        self.assertEqual(d["blocks"]["X7_c51"]["lists"], ["X7_c51_real", "X7_c51_conv"])',
     '        self.assertEqual(d["blocks"]["X7_c51"]["lists"], ["X7_c51_real", "X7_c51_conv"])\n'
     '        self.assertEqual((len(d["lists"]["X7v4_c52_real"]), len(d["lists"]["X7v4_c52_conv"])), (128, 64))\n'
     '        self.assertEqual(d["blocks"]["X7v4_c52"]["lists"], ["X7v4_c52_real", "X7v4_c52_conv"])\n'
     '        self.assertEqual(len(set(d["lists"]["X7v4_c52_real"]) & set(d["lists"]["X7_c51_real"])), 0)   # c52 drew none of c51\'s')
edit(T,
     '        self.assertTrue(SR.blocked(2_000_000_000))\n        self.assertFalse(SR.blocked(2_000_000_001))',
     '        self.assertTrue(SR.blocked(2_000_000_000))\n        self.assertTrue(SR.blocked(2_000_000_001))             # v4\'s bands are spent (X7v4, job c52)\n'
     '        self.assertTrue(SR.blocked(2_005_000_000))\n        self.assertTrue(SR.blocked(2_006_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_006_000_001))')

# ---- README
edit("README_R1W7.md",
     "**v4 (amendment A-R1W7-4; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 2 at 1 USD`):**",
     "**v5 (amendment A-R1W7-5; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 3 at 1 USD`):** the v4 package "
     "ran as job c52 and the frozen reader said `PASS` / `CHAT_WAVE_NO_GAIN`: every hard gate held and one mark, K4 HONEST, was "
     "missed by exactly one unexplained ask (the same ask in the loop driven directly). The cause was found in the wide reader: an "
     "amount of a condition inside a batch or stock sentence (a temperature such as \"80 degrees Fahrenheit\") was read as an "
     "ingredient, so the brain waited for a batch where that \"ingredient\" ran out and asked at the question with every real lesson "
     "learned. FIX FIRST round 3 (PR #425, commit `f45a8570`): a condition amount is a note on the line before it, never an "
     "ingredient; one general rule, no special case; test class G fails on the old code and passes on the fix. v5 = the v4 package "
     "with `helm_now/` recut at `f45a8570` (164 files), block `X7v4_c52` on the exclusion list, bands 2,006 M / 2,008 M / 2,010 M "
     "and the new owner line; reader, recorder, fixture, marks, thresholds, arms and words unchanged. v4 is VOID_SUPERSEDED_BY_V5 "
     "for any further run (c52's record stands). "
     "**v4 (amendment A-R1W7-4; was: SEALED, ran as job c52, PASS / CHAT_WAVE_NO_GAIN; owner's line was `CHAT WAVE 2 at 1 USD`):**")
edit("README_R1W7.md",
     "| `helm_now/` | HELM's code under test: 161 files cut by `git show` from commit `dfc7158d` (v3; byte-identical in v4) (`SOURCE_CUT.json`; `helm_ui/` and `helm_hub/` are not cut) |",
     "| `helm_now/` | HELM's code under test: 164 files cut by `git show` from commit `f45a8570` (v5, FIX FIRST round 3; v3/v4 were 161 files at `dfc7158d`) (`SOURCE_CUT.json`; `helm_ui/` and `helm_hub/` are not cut) |")
edit("README_R1W7.md",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v4.zip>",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip>")

# ---- custodian procedure
CP = "contract/CUSTODIAN_PROCEDURE_R1W7.md"
edit(CP,
     "The line to sign is **`CHAT WAVE 2 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-4, section 16; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51 and must never bind a second zip).",
     "The line to sign is **`CHAT WAVE 3 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-5, section 17; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51 and the v4 line `CHAT WAVE 2 at 1 USD` by job c52; neither may bind a second zip).")
edit(CP,
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-4, section 16)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 2 at 1 USD\" + \":\" + <full sha256 of the sealed v4 zip, 64 lower-case hex> )",
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-5, section 17)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 3 at 1 USD\" + \":\" + <full sha256 of the sealed v5 zip, 64 lower-case hex> )")
edit(CP,
     "1,000,000; seed = band low + slot. Bands (v4): REAL 2,000,000,001-2,001,000,000; CONV 2,002,000,001-2,003,000,000; NOISE\n2,004,000,001-2,005,000,000; used table 1-1,999,000,000 whole (v3's bands were spent by X7; 1,996-1,999 M is reserved for the\ncontinuity packet); gap 1,000,000; slot stepping and STOP as wave 6.",
     "1,000,000; seed = band low + slot. Bands (v5): REAL 2,006,000,001-2,007,000,000; CONV 2,008,000,001-2,009,000,000; NOISE\n2,010,000,001-2,011,000,000; used table 1-2,005,000,000 whole (v3's bands were spent by X7, v4's by X7v4; 1,996-1,999 M stays\nreserved for the continuity packet); gap 1,000,000; slot stepping and STOP as wave 6.")
edit(CP,
     "and (v4, block `X7_c51`) X7's 128 REAL ids and 64 CONV pool ids from job c51.",
     "(v4, block `X7_c51`) X7's 128 REAL ids and 64 CONV pool ids from job c51, and (v5, block `X7v4_c52`) X7v4's 128 REAL ids and 64 CONV pool ids from job c52.")
edit(CP,
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v4.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v4 zip; the v3 zip `5063baba…` is VOID_SUPERSEDED_BY_V4 and the seal refuses it).",
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v5 zip; the v3 zip `5063baba…` and the v4 zip `8602b1bc…` are VOID_SUPERSEDED and the seal refuses them).")
edit(CP,
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v4_custody\\pkg\\` (never over the c51 custody folder `x7_custody\\`).",
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v5_custody\\pkg\\` (never over the c51 / c52 custody folders `x7_custody\\`, `x7v4_custody\\`).")

# ---- amendment A-R1W7-5
AMENDMENT = '''
## 17. Amendment A-R1W7-5 (v5, written BEFORE the v5 reseal; owner order 2026-10-20 "third chat round"; 2026-10-20)

**Why.** The v4 package (zip `%(v4)s`, freeze `948cf691…`,
HELM cut `dfc7158d`) ran on the host as job c52 (`RUN_RESULT_R1W7V4_C52.md`; reading `R1_W7_READING.json` sha256
`bcb2f372a4c9c1600d86ce17c96fe15fec6a0969324c33f9250706f6fd38dd8b`). The frozen reader said verdict `PASS`, word
`CHAT_WAVE_NO_GAIN`: every instrument row true, all 10 hard gates true (HG5 held: the c51 failure was the reader), five of
six marks true, **K4 HONEST false: `unexplained_asks_strict` 1** (the wave-6 rule also 1), the same count in LOOP_ON, so the
cause sat in the brain, not in the chat window. Under the frozen order of words a missed gain mark is `CHAT_WAVE_NO_GAIN`;
nothing was licensed. The owner ordered a third round. Line 4 of this document forbids re-reading c52's data; the c52 word
stands. **v4 is `VOID_SUPERSEDED_BY_V5`** for any further run (its c52 record stands as written).

**The cause (found on the laptop by program from the unit outputs, never from the sealed inputs or keys; the diagnosis
`K4_ITEM_DIAGNOSIS.md` beside the zip names the item by id only).** One real recipe carries, after an ingredient line, an
amount of a CONDITION — a temperature ("<number> degrees Fahrenheit") set off by commas. The wide reader
(`helm_wide_turn.split_lines` / `starts_line`) cut the sentence at that amount and `parse_line` bound the piece as an
ingredient named by the condition words. The brain admitted every batch with a five-name support set for a four-ingredient
recipe, learned all four real lessons exactly, recorded the stock (which carried the same fifth name), and at the question
asked for "one batch where <condition> ran out first": `UNDETERMINED_CLARIFY` with every lesson LEARNED and stock
STOCK_RECORDED, exactly the shape K4 counts. The other 16 asks on ANSWER-keyed items were all explained (18 items where no
lesson was admitted, 3 where one lesson was refused; counts in the diagnosis).

**What changed in HELM (commit `%(fix)s`, branch `claude/helm-r1w7-round3-fix-20261020`, PR #425
to the thread, 1 commit on thread head `1d2b390f`; FIX FIRST round 3).** `helm_wide_turn.py` only: a general rule,
`condition_fragment()` — an amount followed by a temperature / time / head-count / percentage noun (`CONDITION_NOUNS`, the
wide reader's own copy of the family in `helm_english_in.IGNORED_COUNT_NOUNS`; a bare `F` / `C` only when nothing follows
it, so "2 c flour" stays two cups of flour) is a NOTE on the ingredient line before it, never an ingredient line;
`starts_line` returns False for it; `split_lines` holds a leading condition piece for the first ingredient line;
`parse_line` asks `NO_NAME` when a whole line is only a condition. No special case for any item. `helm_brain_canonical.py`
is byte-identical to its base. `READER_VERSION` string unchanged (`test_helm_cas_address` pins the OFF-path trace bytes).
Test `test_helm_wide_alongside.G_ConditionPiecesAreNotIngredients` (3 tests, the author's own sentences in the same shape,
never the exam line): 3 of 3 fail on `1d2b390f`, 3 of 3 pass on the fix. Every `test_helm*.py` suite passes after.

**What changed in this package (v5). Exactly these, nothing else.**

1. **`helm_now/` recut at `%(fix)s`** by the contract's own rule (wave 6 v3's 159 files + every
   `helm_*.py` / `test_helm_*.py` at the commit, each by `git show`, never the working tree): **164 files** (v3/v4: 161).
   The three new files — `helm_cas_address.py` (imported by `helm_end_to_end_loop.py` since the "Build both" commit
   `9916d7da`, switch `CAS_ADDRESS` default OFF, byte-identical OFF path), `test_helm_cas_address.py`,
   `test_helm_units_note.py` — entered the thread between v4's cut and this one. `contract/HELM_CUT_R1W7.json` carries the
   commit and all 164 hashes; `helm_brain_canonical.py` = base `d4488f2a` `24df53c9…`. The host's HELM self-check
   (`kit/run_r1w7.py` `HELM_TESTS`) gains the two new unittest files (10 files).
2. **Exclusions:** `contract/EXCLUDE_R1W7_PRIOR_USED.json` gains block `X7v4_c52` = lists `X7v4_c52_real` (X7v4's 128 REAL
   ids) and `X7v4_c52_conv` (64 CONV pool ids), read by program from the custodian's seal record
   `x7v4_custody/X7_SEALED_20261021T050521Z.json` (ids only; no input, key or exam file opened). Every list applies to
   BOTH pools (A-R1W7-4 rule kept): 18 lists.
3. **Seed bands** (section 10 superseded again): REAL 2,006,000,001-2,007,000,000; CONV 2,008,000,001-2,009,000,000; NOISE
   2,010,000,001-2,011,000,000 (each 1,000,000 wide; below INT32_MAX 2,147,483,647). Used table 1-2,005,000,000 as one range
   (everything up to wave 6 v3; wave 7 v3 / c51 1,990-1,995 M; the continuity packet's reserved 1,996-1,999 M; wave 7 v4 /
   c52 2,000-2,005 M, spent by the X7v4 draw); gap 1,000,000; slot stepping and STOP as before.
4. **The owner's line** (section 8 superseded again): **`CHAT WAVE 3 at 1 USD`** (20 UTF-8 bytes; `CHAT WAVE at 1 USD`
   was consumed by c51's approval record, `CHAT WAVE 2 at 1 USD` by c52's `9e4058a9…`; neither may bind a second zip).
   Seed text `H = sha256(UTF-8("CHAT WAVE 3 at 1 USD" + ":" + <v5 zip sha256, 64 lower-case hex>))`, no trailing newline.
   Cap 1.00 USD; one attempt + one plumbing retry; expected about 0.01-0.02 USD.
5. Labels: `PACKAGE_VERSION` = `v5`; `RUN_LIMITS_R1W7.json` `package_version` and the line in `cost_cap_status`; the
   stage note; README; the custodian procedure; FROZEN re-derived from the constants (the kit test checks they agree);
   the tests that pin the bands, the line, the blocked table, the cut size and the exclusion lists.

**Unchanged (checked by the tests and the freeze):** the v4 reader (`r1w7.merge_r1w7 v2`, HG5 names a missing list), the
v4 recorder unit and fixture, every mark, threshold, arm, status word, exam size, instrument row and hard gate; the noise
sentences; the five neighbours by freeze; the practice pools; the scoring functions; the units and their commands.

**What this amendment does not do.** It does not re-read c52. It does not launch. It does not draw an exam. It licenses
nothing. Forecast: on c52's exam the one K4 miss is removed by the fix on the laptop (the item answers, `SUCCESS_EVALUATED`);
a fresh draw can still miss a mark on a shape no practice run has shown.
''' % {"v4": V4ZIP, "fix": FIX}

pre = PKG / "PREREGISTRATION_R1W7.md"
text = pre.read_bytes().decode("utf-8")
if "## 17. Amendment A-R1W7-5" in text:
    raise SystemExit("already amended")
if not text.endswith("\n"):
    text += "\n"
pre.write_bytes((text + AMENDMENT).encode("utf-8"))
log.append({"file": "PREREGISTRATION_R1W7.md", "appended": "## 17. Amendment A-R1W7-5"})
(PKG.parent / "AMENDMENT_A_R1W7_5.md").write_bytes(AMENDMENT.lstrip("\n").encode("utf-8"))

for rel in ("r1w7/common_w7.py", "r1w7/custody_w7.py", "kit/run_r1w7.py", "tests_r1w7/test_units_w7.py"):
    if b"\x08" in (PKG / rel).read_bytes():
        raise SystemExit("stray backspace byte in " + rel)
out = {"schema": "helm.r1w7.patch-log/1", "version": "v5", "edits": log,
       "files_sha256": {rel: hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
                        for rel in sorted({e["file"] for e in log})}}
LOG.write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps({"edits": len(log)}, indent=1))
