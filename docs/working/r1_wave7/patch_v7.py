"""Builder tool (NOT sealed): every v7 LABEL edit to the package (constants, kit, run limits, tests, README, custodian
procedure). Each edit is an exact once-only replacement; the log names every one. The precode sections and amendments 1-6
of PREREGISTRATION_R1W7.md are not touched; amendments A-R1W7-7 and A-R1W7-8 are appended by append_amendments_v7.py.
Amendment A-R1W7-7's code change (multi_qty_w7.py, its test, the custody hook) is applied by apply_amendment_7.py, not here.

    python -X utf8 -B -I patch_v7.py <v7 package dir> <log json>
"""
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
LOG = Path(sys.argv[2]).resolve()
CUT = "4744041503ca6feb044afa05cbb380533de2fcfe"
V6ZIP = "387577deac79d8b395e1e3245cd3bb1bdddb20b0b21b86f1078e7a0cd20442f8"
HOST_LIST = ("test_helm_brain_wide, test_helm_end_to_end_loop, test_helm_english_in, test_helm_english_in_stock_frame, "
             "test_helm_voice, test_helm_faces_in, test_helm_triad, test_helm_wide_alongside, test_helm_cas_address, "
             "test_helm_units_note, test_helm_pin_hygiene, test_helm_reader_gap")
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
     "exactly as the code runs at commit ad4fde73 (v6, the round-4 build on thread head 5f07c5d7 / PR #429; amendments A-R1W7-2 to A-R1W7-6)",
     "exactly as the code runs at commit 47440415 (v7, the reader-gap build, thread head = PR #435 merged; amendments A-R1W7-2 to A-R1W7-8)")
edit("r1w7/common_w7.py", 'PACKAGE_VERSION = "v6"', 'PACKAGE_VERSION = "v7"')
edit("r1w7/common_w7.py",
     'HELM_CUT_COMMIT = "ad4fde734257cfd5e94ff1b54b8891df9d2e3003"       # v6 (A-R1W7-6): round 4, machine-neutral test pins second pass, PR #429 (1 commit on thread head 5f07c5d7; the hash is unchanged by a merge); v5 was f45a8570, v3/v4 dfc7158d',
     'HELM_CUT_COMMIT = "%s"       # v7 (A-R1W7-8): the reader-gap build (SPEC 7.111, PR #435 merged = thread head); v6 was ad4fde73, v5 f45a8570, v3/v4 dfc7158d' % CUT)
edit("r1w7/common_w7.py",
     'HELM_THREAD_BRANCH = "claude/helm-pin-hygiene-2-20261021 (PR #429 to claude/project-thread-pmbzd6, open at the seal)"',
     'HELM_THREAD_BRANCH = "claude/project-thread-pmbzd6 (thread head 47440415 = merge of PR #435, the reader-gap build)"')
edit("r1w7/common_w7.py", 'OWNER_LINE = "CHAT WAVE 4 at 1 USD"', 'OWNER_LINE = "CHAT WAVE 5 at 1 USD"')
edit("r1w7/common_w7.py",
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-6, section 18); the approval record is written only after the owner signs"',
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-8, section 20); the approval record is written only after the owner signs"')
edit("r1w7/common_w7.py",
     'BANDS = {"REAL": (2_012_000_001, 2_013_000_000), "CONV": (2_014_000_001, 2_015_000_000),\n'
     '         "NOISE": (2_016_000_001, 2_017_000_000)}          # A-R1W7-6: above v5\'s 2,006-2,011 M (spent by X7v5 / c53); 1,996-1,999 M stays reserved for the continuity packet',
     'BANDS = {"REAL": (2_024_000_001, 2_025_000_000), "CONV": (2_026_000_001, 2_027_000_000),\n'
     '         "NOISE": (2_028_000_001, 2_029_000_000)}          # A-R1W7-8: above v6\'s 2,012-2,017 M (spent by X7v6 / c54) and the talk packet\'s reserved 2,018-2,022 M; 1,996-1,999 M stays reserved for the continuity packet')
edit("r1w7/common_w7.py",
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; wave 7 v5 / c53 bands 2,006,000,001-2,011,000,000; whole range)", 1,\n'
     '                2_011_000_000),)',
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; wave 7 v5 / c53 bands 2,006,000,001-2,011,000,000; wave 7 v6 / c54 bands "\n'
     '                "2,012,000,001-2,017,000,000; the talk packet\'s proposed 2,018,000,001-2,022,000,000; whole range)", 1,\n'
     '                2_023_000_000),)')

# ---- r1w7/custody_w7.py (exclusion lists: every list applies to both pools, as v4 / v5 / v6)
edit("r1w7/custody_w7.py",
     '                      "X7v5_c53_real", "X7v5_c53_conv")                  # A-R1W7-6: X7v5\'s ids (job c53)',
     '                      "X7v5_c53_real", "X7v5_c53_conv",                  # A-R1W7-6: X7v5\'s ids (job c53)\n'
     '                      "X7v6_c54_real", "X7v6_c54_conv")                  # A-R1W7-8: X7v6\'s ids (job c54)')

# ---- kit
edit("kit/run_r1w7.py",
     "HELM_CUT_COMMIT = 'ad4fde734257cfd5e94ff1b54b8891df9d2e3003'   # v6 (A-R1W7-6): round 4, machine-neutral test pins (second pass), PR #429",
     "HELM_CUT_COMMIT = '%s'   # v7 (A-R1W7-8): the reader-gap build, thread head (PR #435 merged)" % CUT)
edit("kit/run_r1w7.py",
     "              'test_helm_pin_hygiene']   # entered the cut with the thread head (A-R1W7-5); v6 (A-R1W7-6): + the pin-hygiene regression\n"
     "              # suite (11 names); the three pytest-style files (chat_nuance, memory, agentic_planner) are not unittest suites",
     "              'test_helm_pin_hygiene',   # entered the cut with the thread head (A-R1W7-5); v6 (A-R1W7-6): + the pin-hygiene regression\n"
     "              'test_helm_reader_gap']    # suite (11 names); v7 (A-R1W7-8): + the reader-gap suite (12 names); the three pytest-style\n"
     "              # files (chat_nuance, memory, agentic_planner) are not unittest suites")
edit("kit/STAGE_R1W7.json", "cut at ad4fde73 (v6, round 4: machine-neutral test pins)", "cut at 47440415 (v7, the reader-gap build)")
edit("RUN_LIMITS_R1W7.json", '"package_version": "v6"', '"package_version": "v7"')
edit("RUN_LIMITS_R1W7.json",
     "the owner's line to sign is 'CHAT WAVE 4 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-6, section 18)",
     "the owner's line to sign is 'CHAT WAVE 5 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-8, section 20)")

# ---- tests
T = "tests_r1w7/test_units_w7.py"
edit(T, "        self.assertEqual(C.USED_RANGES[0][2], 2_011_000_000)", "        self.assertEqual(C.USED_RANGES[0][2], 2_023_000_000)")
edit(T,
     '        self.assertEqual(C.BANDS, {"REAL": (2_012_000_001, 2_013_000_000), "CONV": (2_014_000_001, 2_015_000_000),\n'
     '                                   "NOISE": (2_016_000_001, 2_017_000_000)})          # A-R1W7-6\n'
     '        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 4 at 1 USD")',
     '        self.assertEqual(C.BANDS, {"REAL": (2_024_000_001, 2_025_000_000), "CONV": (2_026_000_001, 2_027_000_000),\n'
     '                                   "NOISE": (2_028_000_001, 2_029_000_000)})          # A-R1W7-8\n'
     '        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 5 at 1 USD")')
edit(T,
     '        self.assertEqual(hc["files"], 166)                # v5: 164; v6 (A-R1W7-6): + helm_test_pins.py (named explicitly), test_helm_pin_hygiene.py',
     '        self.assertEqual(hc["files"], 167)                # v6: 166; v7 (A-R1W7-8): + test_helm_reader_gap.py')
edit(T,
     '                "X7v5_c53_real": 128, "X7v5_c53_conv": 64}                   # A-R1W7-6: X7v5\'s ids (job c53)',
     '                "X7v5_c53_real": 128, "X7v5_c53_conv": 64,                   # A-R1W7-6: X7v5\'s ids (job c53)\n'
     '                "X7v6_c54_real": 128, "X7v6_c54_conv": 64}                   # A-R1W7-8: X7v6\'s ids (job c54)')
edit(T,
     '        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv", "X7v4_c52_real",\n'
     '                     "X7v4_c52_conv", "X7v5_c53_real", "X7v5_c53_conv"):',
     '        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv", "X7v4_c52_real",\n'
     '                     "X7v4_c52_conv", "X7v5_c53_real", "X7v5_c53_conv", "X7v6_c54_real", "X7v6_c54_conv"):')
edit(T,
     '        self.assertEqual(len(set(d["lists"]["X7v5_c53_real"]) & (set(d["lists"]["X7_c51_real"]) | set(d["lists"]["X7v4_c52_real"]))), 0)   # c53 drew none of c51\'s or c52\'s',
     '        self.assertEqual(len(set(d["lists"]["X7v5_c53_real"]) & (set(d["lists"]["X7_c51_real"]) | set(d["lists"]["X7v4_c52_real"]))), 0)   # c53 drew none of c51\'s or c52\'s\n'
     '        self.assertEqual((len(d["lists"]["X7v6_c54_real"]), len(d["lists"]["X7v6_c54_conv"])), (128, 64))\n'
     '        self.assertEqual(d["blocks"]["X7v6_c54"]["lists"], ["X7v6_c54_real", "X7v6_c54_conv"])\n'
     '        self.assertEqual(len(set(d["lists"]["X7v6_c54_real"]) & (set(d["lists"]["X7_c51_real"]) | set(d["lists"]["X7v4_c52_real"]) | set(d["lists"]["X7v5_c53_real"]))), 0)   # c54 drew none of c51\'s, c52\'s or c53\'s')
edit(T,
     '        self.assertTrue(SR.blocked(2_011_000_000))\n        self.assertTrue(SR.blocked(2_012_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_012_000_001))',
     '        self.assertTrue(SR.blocked(2_011_000_000))\n        self.assertTrue(SR.blocked(2_012_000_000))\n'
     '        self.assertTrue(SR.blocked(2_012_000_001))             # v6\'s bands are spent (X7v6, job c54)\n'
     '        self.assertTrue(SR.blocked(2_017_000_000))\n        self.assertTrue(SR.blocked(2_018_000_001))             # the talk packet\'s reservation\n'
     '        self.assertTrue(SR.blocked(2_022_000_000))\n        self.assertTrue(SR.blocked(2_023_000_000))\n'
     '        self.assertTrue(SR.blocked(2_024_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_024_000_001))')

# ---- README
edit("README_R1W7.md",
     "**v6 (amendment A-R1W7-6; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 4 at 1 USD`):**",
     "**v7 (amendments A-R1W7-7 and A-R1W7-8; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 5 at 1 USD`):** the v6 "
     "package ran as job c54 and the frozen reader said `PASS` / `CHAT_WAVE_NO_GAIN`: the first run of the four with a clean instrument "
     "end to end (8 of 8 instrument rows, 10 of 10 hard gates, HELM's 11-file suite OK on the host), 5 of 6 marks true, K4 missed by "
     "2 unexplained asks on real recipes (the same 2 in the loop driven directly). The per-item diagnosis (SPEC 7.109, no exam text) found "
     "both asks to be one book line holding two amounts (\"6 cloves, 12 peppercorns\" in shape): the frozen key keeps the line as one "
     "lesson about the first ingredient, the wide reader reads two, and the untaught second one makes the brain ask honestly. v7 = the v6 "
     "package with four changes and nothing else: (1) `helm_now/` recut at thread head `47440415` (the reader-gap build, SPEC 7.111, "
     "PR #435 merged: `helm_wide_turn.py` reader `RB-W1 v7` reads a stock sentence's face or purpose clause, `helm_faces_in.py` v2 takes "
     "any bound name, the wide question applies faces as the licensed triad does, the past-tense lesson paraphrase reads; new "
     "`test_helm_reader_gap.py`, 26 tests; OFF-path pin `83f96a4a…`): **167 files** (v6: 166; + `test_helm_reader_gap.py`; "
     "`helm_wide_turn.py`, `helm_faces_in.py`, `test_helm_cas_address.py`, `test_helm_wide_alongside.py` changed; every other file equal "
     "to v6's cut; `helm_brain_canonical.py` = base `24df53c9…`); (2) the host's HELM list grown to **12 names** (+ `test_helm_reader_gap`), "
     "run from the seal under the A-R1W7-6 rule (`TEST_COUNTS_R1W7_v7.json`, `host_exact_suite_list`); (3) **amendment A-R1W7-7** (the "
     "custodian's MULTI_QTY rule, the owner's \"Yes to D6\"): `r1w7/multi_qty_w7.py` + `tests_r1w7/test_multi_qty_w7.py` + one import "
     "and one hook in `custody_w7.make_all` (`\"keys\": [MQ.apply(K.key_item(it), it[\"raw_lines\"], ns.XG) for it in real_items]`), "
     "applied by `apply_amendment_7.py` before the freeze: a raw book line carrying a second amount after a separator marks the recipe "
     "not representable (`line<i>:MULTI_QTY`), so it scores `NOT_SCORED`; measured on the practice draw: 6 of 128 items (5 percent), "
     "all ANSWER-keyed and representable before, become `NOT_SCORED`; the frozen key package is not edited; the reader's rules are not "
     "changed; (4) **amendment A-R1W7-8**: block `X7v6_c54` on the exclusion list, bands 2,024 M / 2,026 M / 2,028 M (used table "
     "1-2,023,000,000; 1,996-1,999 M reserved for the continuity packet, 2,018-2,022 M for the talk packet) and the new owner line. "
     "Reader (`merge_r1w7 v2`), recorder, fixture, marks, thresholds, arms and status words unchanged. v6 is VOID_SUPERSEDED_BY_V7 for any "
     "further run (c54's record stands). "
     "**v6 (amendment A-R1W7-6; was: SEALED, ran as job c54, PASS / CHAT_WAVE_NO_GAIN with a clean instrument and K4 missed by 2 asks; owner's line was `CHAT WAVE 4 at 1 USD`):**")
edit("README_R1W7.md",
     "| `helm_now/` | HELM's code under test: 166 files cut by `git show` from commit `ad4fde73` (v6, round 4: machine-neutral test pins; the rule now names `helm_test_pins.py` explicitly; v5 was 164 files at `f45a8570`, v3/v4 161 at `dfc7158d`) (`SOURCE_CUT.json`; `helm_ui/` and `helm_hub/` are not cut) |",
     "| `helm_now/` | HELM's code under test: 167 files cut by `git show` from commit `47440415` (v7, the reader-gap build; v6 was 166 files at `ad4fde73`, v5 164 at `f45a8570`, v3/v4 161 at `dfc7158d`) (`SOURCE_CUT.json`; `helm_ui/` and `helm_hub/` are not cut) |")
edit("README_R1W7.md",
     "| `r1w7/score_w7.py`, `merge_r1w7.py` | the frozen reader:",
     "| `r1w7/multi_qty_w7.py` | A-R1W7-7: the custodian's MULTI_QTY rule (a raw book line with a second amount after a separator makes the recipe not representable); applied once in `custody_w7.make_all` to the real keys; the frozen key package is untouched |\n"
     "| `r1w7/score_w7.py`, `merge_r1w7.py` | the frozen reader:")
edit("README_R1W7.md",
     "HELM's own suites that run on the host are the ELEVEN unittest files named in `kit/run_r1w7.py` `HELM_TESTS`, in this order: "
     "test_helm_brain_wide, test_helm_end_to_end_loop, test_helm_english_in, test_helm_english_in_stock_frame, test_helm_voice, test_helm_faces_in, test_helm_triad, test_helm_wide_alongside, test_helm_cas_address, test_helm_units_note, test_helm_pin_hygiene",
     "HELM's own suites that run on the host are the TWELVE unittest files named in `kit/run_r1w7.py` `HELM_TESTS`, in this order: " + HOST_LIST)
edit("README_R1W7.md",
     "<scratch copy of helm_now/> <the eleven names>` from inside the scratch copy",
     "<scratch copy of helm_now/> <the twelve names>` from inside the scratch copy")
edit("README_R1W7.md",
     "`TEST_COUNTS_R1W7_v6.json` (`host_exact_suite_list`), asserting the list equals the sealed kit's `HELM_TESTS`.",
     "`TEST_COUNTS_R1W7_v7.json` (`host_exact_suite_list`), asserting the list equals the sealed kit's `HELM_TESTS`.")
edit("README_R1W7.md",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v6.zip>",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v7.zip>")

# ---- custodian procedure
CP = "contract/CUSTODIAN_PROCEDURE_R1W7.md"
edit(CP,
     "The line to sign is **`CHAT WAVE 4 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-6, section 18; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51, the v4 line `CHAT WAVE 2 at 1 USD` by job c52 and the v5 line `CHAT WAVE 3 at 1 USD` by job c53; none may bind a second zip).",
     "The line to sign is **`CHAT WAVE 5 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-8, section 20; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51, the v4 line `CHAT WAVE 2 at 1 USD` by job c52, the v5 line `CHAT WAVE 3 at 1 USD` by job c53 and the v6 line `CHAT WAVE 4 at 1 USD` by job c54; none may bind a second zip).")
edit(CP,
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-6, section 18)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 4 at 1 USD\" + \":\" + <full sha256 of the sealed v6 zip, 64 lower-case hex> )",
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-8, section 20)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 5 at 1 USD\" + \":\" + <full sha256 of the sealed v7 zip, 64 lower-case hex> )")
edit(CP,
     "1,000,000; seed = band low + slot. Bands (v6): REAL 2,012,000,001-2,013,000,000; CONV 2,014,000,001-2,015,000,000; NOISE\n2,016,000,001-2,017,000,000; used table 1-2,011,000,000 whole (v3's bands were spent by X7, v4's by X7v4, v5's by X7v5; 1,996-1,999 M stays\nreserved for the continuity packet); gap 1,000,000; slot stepping and STOP as wave 6.",
     "1,000,000; seed = band low + slot. Bands (v7): REAL 2,024,000,001-2,025,000,000; CONV 2,026,000,001-2,027,000,000; NOISE\n2,028,000,001-2,029,000,000; used table 1-2,023,000,000 whole (v3's bands were spent by X7, v4's by X7v4, v5's by X7v5, v6's by X7v6; 1,996-1,999 M stays\nreserved for the continuity packet and 2,018-2,022 M for the talk packet); gap 1,000,000; slot stepping and STOP as wave 6.")
edit(CP,
     "and (v6, block `X7v5_c53`) X7v5's 128 REAL ids and 64 CONV pool ids from job c53.",
     "(v6, block `X7v5_c53`) X7v5's 128 REAL ids and 64 CONV pool ids from job c53, and (v7, block `X7v6_c54`) X7v6's 128 REAL ids and 64 CONV pool ids from job c54.")
edit(CP,
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v6.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v6 zip; the v3 zip `5063baba…`, the v4 zip `8602b1bc…` and the v5 zip `4b54a077…` are VOID_SUPERSEDED and the seal refuses them).",
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v7.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v7 zip; the v3 zip `5063baba…`, the v4 zip `8602b1bc…`, the v5 zip `4b54a077…` and the v6 zip `387577de…` are VOID_SUPERSEDED and the seal refuses them).")
edit(CP,
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v6_custody\\pkg\\` (never over the c51 / c52 / c53 custody folders `x7_custody\\`, `x7v4_custody\\`, `x7v5_custody\\`).",
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v7_custody\\pkg\\` (never over the c51 / c52 / c53 / c54 custody folders `x7_custody\\`, `x7v4_custody\\`, `x7v5_custody\\`, `x7v6_custody\\`).")

for rel in ("r1w7/common_w7.py", "r1w7/custody_w7.py", "kit/run_r1w7.py", "tests_r1w7/test_units_w7.py", "README_R1W7.md",
            "contract/CUSTODIAN_PROCEDURE_R1W7.md", "kit/STAGE_R1W7.json", "RUN_LIMITS_R1W7.json"):
    if b"\x08" in (PKG / rel).read_bytes():
        raise SystemExit("stray backspace byte in " + rel)
out = {"schema": "helm.r1w7.patch-log/1", "version": "v7", "edits": log,
       "files_sha256": {rel: hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
                        for rel in sorted({e["file"] for e in log})}}
LOG.write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps({"edits": len(log)}, indent=1))
