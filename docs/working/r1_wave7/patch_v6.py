"""Builder tool (NOT sealed): every v6 edit to the package (constants, kit, run limits, tests, README, custodian procedure,
amendment A-R1W7-6 appended). Each edit is an exact once-only replacement; the log names every one. The precode sections
and amendments 1-5 of PREREGISTRATION_R1W7.md are not touched: the amendment supersedes them.

    python -X utf8 -B -I patch_v6.py <v6 package dir> <log json>
"""
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
LOG = Path(sys.argv[2]).resolve()
FIX = "ad4fde734257cfd5e94ff1b54b8891df9d2e3003"
V5ZIP = "4b54a077e4b2963301451c6eb78836a32d9797460cd8143d3cf2f9efdc1a7cf8"
HOST_LIST = ("test_helm_brain_wide, test_helm_end_to_end_loop, test_helm_english_in, test_helm_english_in_stock_frame, "
             "test_helm_voice, test_helm_faces_in, test_helm_triad, test_helm_wide_alongside, test_helm_cas_address, "
             "test_helm_units_note, test_helm_pin_hygiene")
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
     "exactly as the code runs at commit f45a8570 (v5, the FIX FIRST round-3 build on thread head 1d2b390f / PR #425; amendments A-R1W7-2 to A-R1W7-5)",
     "exactly as the code runs at commit ad4fde73 (v6, the round-4 build on thread head 5f07c5d7 / PR #429; amendments A-R1W7-2 to A-R1W7-6)")
edit("r1w7/common_w7.py", 'PACKAGE_VERSION = "v5"', 'PACKAGE_VERSION = "v6"')
edit("r1w7/common_w7.py",
     'HELM_CUT_COMMIT = "f45a85706a9d8b9177e4b7279453d1538c12045d"       # v5 (A-R1W7-5): FIX FIRST round 3 on c52\'s one unexplained ask, PR #425 (1 commit on thread head 1d2b390f); v3/v4 were dfc7158d',
     'HELM_CUT_COMMIT = "%s"       # v6 (A-R1W7-6): round 4, machine-neutral test pins second pass, PR #429 (1 commit on thread head 5f07c5d7; the hash is unchanged by a merge); v5 was f45a8570, v3/v4 dfc7158d' % FIX)
edit("r1w7/common_w7.py",
     'HELM_THREAD_BRANCH = "claude/helm-r1w7-round3-fix-20261020 (PR #425 to claude/project-thread-pmbzd6)"',
     'HELM_THREAD_BRANCH = "claude/helm-pin-hygiene-2-20261021 (PR #429 to claude/project-thread-pmbzd6, open at the seal)"')
edit("r1w7/common_w7.py", 'OWNER_LINE = "CHAT WAVE 3 at 1 USD"', 'OWNER_LINE = "CHAT WAVE 4 at 1 USD"')
edit("r1w7/common_w7.py",
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-5, section 17); the approval record is written only after the owner signs"',
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-6, section 18); the approval record is written only after the owner signs"')
edit("r1w7/common_w7.py",
     'BANDS = {"REAL": (2_006_000_001, 2_007_000_000), "CONV": (2_008_000_001, 2_009_000_000),\n'
     '         "NOISE": (2_010_000_001, 2_011_000_000)}          # A-R1W7-5: above v4\'s 2,000-2,005 M (spent by X7v4 / c52); 1,996-1,999 M stays reserved for the continuity packet',
     'BANDS = {"REAL": (2_012_000_001, 2_013_000_000), "CONV": (2_014_000_001, 2_015_000_000),\n'
     '         "NOISE": (2_016_000_001, 2_017_000_000)}          # A-R1W7-6: above v5\'s 2,006-2,011 M (spent by X7v5 / c53); 1,996-1,999 M stays reserved for the continuity packet')
edit("r1w7/common_w7.py",
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; whole range)", 1,\n'
     '                2_005_000_000),)',
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; wave 7 v5 / c53 bands 2,006,000,001-2,011,000,000; whole range)", 1,\n'
     '                2_011_000_000),)')

# ---- r1w7/custody_w7.py (exclusion lists: every list applies to both pools, as v4 / v5)
edit("r1w7/custody_w7.py",
     '                      "X7v4_c52_real", "X7v4_c52_conv")                  # A-R1W7-5: X7v4\'s ids (job c52)',
     '                      "X7v4_c52_real", "X7v4_c52_conv",                  # A-R1W7-5: X7v4\'s ids (job c52)\n'
     '                      "X7v5_c53_real", "X7v5_c53_conv")                  # A-R1W7-6: X7v5\'s ids (job c53)')

# ---- kit
edit("kit/run_r1w7.py",
     "HELM_CUT_COMMIT = 'f45a85706a9d8b9177e4b7279453d1538c12045d'   # v5 (A-R1W7-5): FIX FIRST round 3, PR #425",
     "HELM_CUT_COMMIT = '%s'   # v6 (A-R1W7-6): round 4, machine-neutral test pins (second pass), PR #429" % FIX)
edit("kit/run_r1w7.py",
     "              'test_helm_wide_alongside', 'test_helm_cas_address', 'test_helm_units_note']   # v5: the two unittest files that\n"
     "              # entered the cut with the thread head (A-R1W7-5); the three pytest-style files (chat_nuance, memory, agentic_planner) are not unittest suites",
     "              'test_helm_wide_alongside', 'test_helm_cas_address', 'test_helm_units_note',   # v5: the two unittest files that\n"
     "              'test_helm_pin_hygiene']   # entered the cut with the thread head (A-R1W7-5); v6 (A-R1W7-6): + the pin-hygiene regression\n"
     "              # suite (11 names); the three pytest-style files (chat_nuance, memory, agentic_planner) are not unittest suites")
edit("kit/STAGE_R1W7.json", "cut at f45a8570 (v5, FIX FIRST round 3)", "cut at ad4fde73 (v6, round 4: machine-neutral test pins)")
edit("RUN_LIMITS_R1W7.json", '"package_version": "v5"', '"package_version": "v6"')
edit("RUN_LIMITS_R1W7.json",
     "the owner's line to sign is 'CHAT WAVE 3 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-5, section 17)",
     "the owner's line to sign is 'CHAT WAVE 4 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-6, section 18)")

# ---- tests
T = "tests_r1w7/test_units_w7.py"
edit(T, "        self.assertEqual(C.USED_RANGES[0][2], 2_005_000_000)", "        self.assertEqual(C.USED_RANGES[0][2], 2_011_000_000)")
edit(T,
     '        self.assertEqual(C.BANDS, {"REAL": (2_006_000_001, 2_007_000_000), "CONV": (2_008_000_001, 2_009_000_000),\n'
     '                                   "NOISE": (2_010_000_001, 2_011_000_000)})          # A-R1W7-5\n'
     '        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 3 at 1 USD")',
     '        self.assertEqual(C.BANDS, {"REAL": (2_012_000_001, 2_013_000_000), "CONV": (2_014_000_001, 2_015_000_000),\n'
     '                                   "NOISE": (2_016_000_001, 2_017_000_000)})          # A-R1W7-6\n'
     '        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 4 at 1 USD")')
edit(T,
     '        self.assertEqual(hc["files"], 164)                # v5: + helm_cas_address.py, test_helm_cas_address.py, test_helm_units_note.py',
     '        self.assertEqual(hc["files"], 166)                # v5: 164; v6 (A-R1W7-6): + helm_test_pins.py (named explicitly), test_helm_pin_hygiene.py')
edit(T,
     '                "X7v4_c52_real": 128, "X7v4_c52_conv": 64}                   # A-R1W7-5: X7v4\'s ids (job c52)',
     '                "X7v4_c52_real": 128, "X7v4_c52_conv": 64,                   # A-R1W7-5: X7v4\'s ids (job c52)\n'
     '                "X7v5_c53_real": 128, "X7v5_c53_conv": 64}                   # A-R1W7-6: X7v5\'s ids (job c53)')
edit(T,
     '        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv", "X7v4_c52_real",\n'
     '                     "X7v4_c52_conv"):',
     '        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv", "X7v4_c52_real",\n'
     '                     "X7v4_c52_conv", "X7v5_c53_real", "X7v5_c53_conv"):')
edit(T,
     '        self.assertEqual(len(set(d["lists"]["X7v4_c52_real"]) & set(d["lists"]["X7_c51_real"])), 0)   # c52 drew none of c51\'s',
     '        self.assertEqual(len(set(d["lists"]["X7v4_c52_real"]) & set(d["lists"]["X7_c51_real"])), 0)   # c52 drew none of c51\'s\n'
     '        self.assertEqual((len(d["lists"]["X7v5_c53_real"]), len(d["lists"]["X7v5_c53_conv"])), (128, 64))\n'
     '        self.assertEqual(d["blocks"]["X7v5_c53"]["lists"], ["X7v5_c53_real", "X7v5_c53_conv"])\n'
     '        self.assertEqual(len(set(d["lists"]["X7v5_c53_real"]) & (set(d["lists"]["X7_c51_real"]) | set(d["lists"]["X7v4_c52_real"]))), 0)   # c53 drew none of c51\'s or c52\'s')
edit(T,
     '        self.assertTrue(SR.blocked(2_005_000_000))\n        self.assertTrue(SR.blocked(2_006_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_006_000_001))',
     '        self.assertTrue(SR.blocked(2_005_000_000))\n        self.assertTrue(SR.blocked(2_006_000_000))\n'
     '        self.assertTrue(SR.blocked(2_006_000_001))             # v5\'s bands are spent (X7v5, job c53)\n'
     '        self.assertTrue(SR.blocked(2_011_000_000))\n        self.assertTrue(SR.blocked(2_012_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_012_000_001))')

# ---- README
edit("README_R1W7.md",
     "**v5 (amendment A-R1W7-5; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 3 at 1 USD`):**",
     "**v6 (amendment A-R1W7-6; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 4 at 1 USD`):** the v5 package "
     "ran as job c53 and the frozen reader said `INSTRUMENT_ERROR` / `INCONCLUSIVE`: all 10 hard gates and all six marks were true as "
     "facts, but instrument row I6 (`suites_ok`) was false because one HELM unit test failed on the Linux host "
     "(`test_helm_cas_address.C_LoopStamps.test_off_is_byte_identical_to_the_pre_change_code`: the OFF records hashed `6bf323ad…` "
     "against one stored laptop value `56f356ea…`). The cause, proven on the laptop (`PIN_TEST_DIAGNOSIS.md` beside the zip): the "
     "only machine-bound value in the hashed records is the absolute path of the wave-1 brain folder, which the loop writes into "
     "two brain trace rows and two turn receipts hash over; the host's hash is reproduced exactly on the laptop by reporting the "
     "host's path, on base `159c7d2b` too, so the host's OFF path was byte-identical to the pre-change code. Round 4 (PR #429, "
     "commit `ad4fde73`, on the thread head `5f07c5d7`; a first pass `3dae274f` / PR #428 was found insufficient by the builder's "
     "diff and superseded): the tests hash records through `helm_test_pins.canon`, which strips the `brain_dir` and `receipt_hash` "
     "leaves and neutralises absolute paths; new pin `312ddfd6…`; `test_helm_pin_hygiene.py` (9 tests) refuses any record pin that "
     "bypasses it and proves the pin invariant to the brain folder. v6 = the v5 "
     "package with `helm_now/` recut at `ad4fde73` (166 files: + `helm_test_pins.py`, named explicitly in the cut rule, and "
     "`test_helm_pin_hygiene.py`; `test_helm_cas_address.py` changed; every other file equal to v5's cut), block "
     "`X7v5_c53` on the exclusion list, bands 2,012 M / 2,014 M / 2,016 M and the new owner line; reader, recorder, fixture, marks, "
     "thresholds, arms and words unchanged. **New rule (A-R1W7-6):** the seal step runs EXACTLY the host's suite list with the "
     "host's command form from a fresh extract of the sealed zip and records the list, the command and the counts in "
     "`TEST_COUNTS_R1W7_v6.json` under `host_exact_suite_list`, asserting the list equals `kit/run_r1w7.py` `HELM_TESTS` in the "
     "extract (what the stage plan runs). v5 is VOID_SUPERSEDED_BY_V6 for any further run (c53's record stands). "
     "**v5 (amendment A-R1W7-5; was: SEALED, ran as job c53, INSTRUMENT_ERROR / INCONCLUSIVE on the pin test alone; owner's line was `CHAT WAVE 3 at 1 USD`):**")
edit("README_R1W7.md",
     "| `helm_now/` | HELM's code under test: 164 files cut by `git show` from commit `f45a8570` (v5, FIX FIRST round 3; v3/v4 were 161 files at `dfc7158d`) (`SOURCE_CUT.json`; `helm_ui/` and `helm_hub/` are not cut) |",
     "| `helm_now/` | HELM's code under test: 166 files cut by `git show` from commit `ad4fde73` (v6, round 4: machine-neutral test pins; the rule now names `helm_test_pins.py` explicitly; v5 was 164 files at `f45a8570`, v3/v4 161 at `dfc7158d`) (`SOURCE_CUT.json`; `helm_ui/` and `helm_hub/` are not cut) |")
edit("README_R1W7.md",
     "HELM's own suites that run on the host are the eight unittest files wave 6 ran (`test_helm_chat_nuance.py`,\n"
     "`test_helm_memory.py` and `test_helm_agentic_planner.py` are pytest-style and are carried in the cut but not run as unittest suites).",
     "HELM's own suites that run on the host are the ELEVEN unittest files named in `kit/run_r1w7.py` `HELM_TESTS`, in this order: "
     + HOST_LIST + " (`test_helm_chat_nuance.py`, `test_helm_memory.py` and `test_helm_agentic_planner.py` are pytest-style and are "
     "carried in the cut but not run as unittest suites). The host's command form is `python -X utf8 -B -I -c <HELM_LOADER> "
     "<scratch copy of helm_now/> <the eleven names>` from inside the scratch copy, with `HELM_SESSION_DIR` inside the scratch and "
     "`HELM_CANONICAL_BRAIN_DIR` = the wave-1 package folder. **Rule since v6 (A-R1W7-6):** the seal step runs exactly that list "
     "with that command form from a fresh extract of the sealed zip and records list, command and counts in "
     "`TEST_COUNTS_R1W7_v6.json` (`host_exact_suite_list`), asserting the list equals the sealed kit's `HELM_TESTS`.")
edit("README_R1W7.md",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip>",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v6.zip>")

# ---- custodian procedure
CP = "contract/CUSTODIAN_PROCEDURE_R1W7.md"
edit(CP,
     "The line to sign is **`CHAT WAVE 3 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-5, section 17; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51 and the v4 line `CHAT WAVE 2 at 1 USD` by job c52; neither may bind a second zip).",
     "The line to sign is **`CHAT WAVE 4 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-6, section 18; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51, the v4 line `CHAT WAVE 2 at 1 USD` by job c52 and the v5 line `CHAT WAVE 3 at 1 USD` by job c53; none may bind a second zip).")
edit(CP,
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-5, section 17)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 3 at 1 USD\" + \":\" + <full sha256 of the sealed v5 zip, 64 lower-case hex> )",
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-6, section 18)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 4 at 1 USD\" + \":\" + <full sha256 of the sealed v6 zip, 64 lower-case hex> )")
edit(CP,
     "1,000,000; seed = band low + slot. Bands (v5): REAL 2,006,000,001-2,007,000,000; CONV 2,008,000,001-2,009,000,000; NOISE\n2,010,000,001-2,011,000,000; used table 1-2,005,000,000 whole (v3's bands were spent by X7, v4's by X7v4; 1,996-1,999 M stays\nreserved for the continuity packet); gap 1,000,000; slot stepping and STOP as wave 6.",
     "1,000,000; seed = band low + slot. Bands (v6): REAL 2,012,000,001-2,013,000,000; CONV 2,014,000,001-2,015,000,000; NOISE\n2,016,000,001-2,017,000,000; used table 1-2,011,000,000 whole (v3's bands were spent by X7, v4's by X7v4, v5's by X7v5; 1,996-1,999 M stays\nreserved for the continuity packet); gap 1,000,000; slot stepping and STOP as wave 6.")
edit(CP,
     "(v4, block `X7_c51`) X7's 128 REAL ids and 64 CONV pool ids from job c51, and (v5, block `X7v4_c52`) X7v4's 128 REAL ids and 64 CONV pool ids from job c52.",
     "(v4, block `X7_c51`) X7's 128 REAL ids and 64 CONV pool ids from job c51, (v5, block `X7v4_c52`) X7v4's 128 REAL ids and 64 CONV pool ids from job c52, and (v6, block `X7v5_c53`) X7v5's 128 REAL ids and 64 CONV pool ids from job c53.")
edit(CP,
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v5 zip; the v3 zip `5063baba…` and the v4 zip `8602b1bc…` are VOID_SUPERSEDED and the seal refuses them).",
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v6.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v6 zip; the v3 zip `5063baba…`, the v4 zip `8602b1bc…` and the v5 zip `4b54a077…` are VOID_SUPERSEDED and the seal refuses them).")
edit(CP,
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v5_custody\\pkg\\` (never over the c51 / c52 custody folders `x7_custody\\`, `x7v4_custody\\`).",
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v6_custody\\pkg\\` (never over the c51 / c52 / c53 custody folders `x7_custody\\`, `x7v4_custody\\`, `x7v5_custody\\`).")

# ---- amendment A-R1W7-6
AMENDMENT = (Path(__file__).resolve().parent / "AMENDMENT_A_R1W7_6_BODY.md").read_bytes().decode("utf-8") % {"v5": V5ZIP, "fix": FIX}

pre = PKG / "PREREGISTRATION_R1W7.md"
text = pre.read_bytes().decode("utf-8")
if "## 18. Amendment A-R1W7-6" in text:
    raise SystemExit("already amended")
if not text.endswith("\n"):
    text += "\n"
pre.write_bytes((text + AMENDMENT).encode("utf-8"))
log.append({"file": "PREREGISTRATION_R1W7.md", "appended": "## 18. Amendment A-R1W7-6"})
(PKG.parent / "AMENDMENT_A_R1W7_6.md").write_bytes(AMENDMENT.lstrip("\n").encode("utf-8"))

for rel in ("r1w7/common_w7.py", "r1w7/custody_w7.py", "kit/run_r1w7.py", "tests_r1w7/test_units_w7.py", "README_R1W7.md",
            "contract/CUSTODIAN_PROCEDURE_R1W7.md", "PREREGISTRATION_R1W7.md"):
    if b"\x08" in (PKG / rel).read_bytes():
        raise SystemExit("stray backspace byte in " + rel)
out = {"schema": "helm.r1w7.patch-log/1", "version": "v6", "edits": log,
       "files_sha256": {rel: hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
                        for rel in sorted({e["file"] for e in log})}}
LOG.write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps({"edits": len(log)}, indent=1))
