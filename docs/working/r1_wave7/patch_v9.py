"""Builder tool (NOT sealed): every v9 LABEL edit to the package (constants, custody exclusion names, kit, run limits, tests,
README, custodian procedure). Each edit is an exact once-only replacement; the log names every one. The precode sections and
amendments 1-9 of PREREGISTRATION_R1W7.md are not touched; amendment A-R1W7-10 is appended by append_amendment_10.py. Amendment
A-R1W7-7's code (multi_qty_w7.py, its test, the custody hook) is already in the v8 extract this package starts from; it is
checked, not re-applied. The exclusion block X7v8_c55 (c55's ids) is added by add_x7_exclusions_v9.py; this tool names the two
new lists in custody_w7.REAL_EXCLUDE_LISTS and in the tests.

    python -X utf8 -B -I patch_v9.py <v9 package dir> <log json>
"""
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
LOG = Path(sys.argv[2]).resolve()
CUT = "55cda1e21f7e6ea0048fe2faf7e90f23e4ec9525"
V8CUT = "b10da2cd2c78317f5983fa8460ac137c8034556b"
V8ZIP = "e88b125e3079f0fa79045fec888d4e862a5a742cf82010de6872bdc621f865c7"
log = []


def edit(rel, old, new):
    p = PKG / rel
    text = p.read_bytes().decode("utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{rel}: target not found exactly once: {old[:70]!r}")
    p.write_bytes(text.replace(old, new).encode("utf-8"))
    log.append({"file": rel, "old": old[:90], "new": new[:90]})


# ---- A-R1W7-7 must already be in the tree (the v8 extract carries it); checked, never re-applied
cu = (PKG / "r1w7" / "custody_w7.py").read_text(encoding="utf-8")
if cu.count('"keys": [MQ.apply(K.key_item(it), it["raw_lines"], ns.XG) for it in real_items]') != 1 or \
        not (PKG / "r1w7" / "multi_qty_w7.py").is_file() or not (PKG / "tests_r1w7" / "test_multi_qty_w7.py").is_file():
    raise SystemExit("A-R1W7-7 is not in the tree this package starts from")
# ---- the exclusion block must already be in the contract (add_x7_exclusions_v9.py runs first)
ex = json.loads((PKG / "contract" / "EXCLUDE_R1W7_PRIOR_USED.json").read_text(encoding="utf-8"))
if "X7v8_c55" not in ex["blocks"] or len(ex["lists"]["X7v8_c55_real"]) != 128 or len(ex["lists"]["X7v8_c55_conv"]) != 64:
    raise SystemExit("block X7v8_c55 is not in the contract yet: run add_x7_exclusions_v9.py first")

# ---- r1w7/common_w7.py
edit("r1w7/common_w7.py",
     "exactly as the code runs at commit b10da2cd (v8, the reader v7.1 fix, thread head = PR #437 merged; amendments A-R1W7-2 to A-R1W7-9)",
     "exactly as the code runs at commit 55cda1e2 (v9, the reader v7.2 fix, thread head = PR #447 merged; amendments A-R1W7-2 to A-R1W7-10)")
edit("r1w7/common_w7.py", 'PACKAGE_VERSION = "v8"', 'PACKAGE_VERSION = "v9"')
edit("r1w7/common_w7.py",
     'HELM_CUT_COMMIT = "%s"       # v8 (A-R1W7-9): the reader v7.1 fix (SPEC 7.113, PR #437 merged; thread head after PR #438); v7 was 47440415, v6 ad4fde73, v5 f45a8570, v3/v4 dfc7158d' % V8CUT,
     'HELM_CUT_COMMIT = "%s"       # v9 (A-R1W7-10): the reader v7.2 fix (SPEC 7.117, PR #447 merged = thread head); v8 was b10da2cd, v7 47440415, v6 ad4fde73, v5 f45a8570, v3/v4 dfc7158d' % CUT)
edit("r1w7/common_w7.py",
     'HELM_THREAD_BRANCH = "claude/project-thread-pmbzd6 (thread head b10da2cd = merge of PR #438, after PR #437, the reader v7.1 fix)"',
     'HELM_THREAD_BRANCH = "claude/project-thread-pmbzd6 (thread head 55cda1e2 = merge of PR #447, the reader v7.2 fix)"')
edit("r1w7/common_w7.py", 'OWNER_LINE = "CHAT WAVE 5 at 1 USD"', 'OWNER_LINE = "CHAT WAVE 6 at 1 USD"')
edit("r1w7/common_w7.py",
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-9, section 21; the line is unchanged from A-R1W7-8 and was never bound to the void v7 zip); the approval record is written only after the owner signs"',
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-10, section 22; the v8 line CHAT WAVE 5 at 1 USD was consumed by job c55); the approval record is written only after the owner signs"')
edit("r1w7/common_w7.py",
     'BANDS = {"REAL": (2_030_000_001, 2_031_000_000), "CONV": (2_032_000_001, 2_033_000_000),\n'
     '         "NOISE": (2_034_000_001, 2_035_000_000)}          # A-R1W7-9: above v7\'s 2,024-2,029 M (reserved by the void v7 seal, never drawn); 1,996-1,999 M stays reserved for the continuity packet, 2,018-2,022 M for the talk packet',
     'BANDS = {"REAL": (2_036_000_001, 2_037_000_000), "CONV": (2_038_000_001, 2_039_000_000),\n'
     '         "NOISE": (2_040_000_001, 2_041_000_000)}          # A-R1W7-10: above v8\'s 2,030-2,035 M (spent by X7v8 / c55); 1,996-1,999 M stays reserved for the continuity packet, 2,018-2,022 M for the talk packet')
edit("r1w7/common_w7.py",
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; wave 7 v5 / c53 bands 2,006,000,001-2,011,000,000; wave 7 v6 / c54 bands "\n'
     '                "2,012,000,001-2,017,000,000; the talk packet\'s proposed 2,018,000,001-2,022,000,000; wave 7 v7 bands "\n'
     '                "2,024,000,001-2,029,000,000 (reserved by the void v7 seal, never drawn); whole range)", 1,\n'
     '                2_029_000_000),)',
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; wave 7 v5 / c53 bands 2,006,000,001-2,011,000,000; wave 7 v6 / c54 bands "\n'
     '                "2,012,000,001-2,017,000,000; the talk packet\'s proposed 2,018,000,001-2,022,000,000; wave 7 v7 bands "\n'
     '                "2,024,000,001-2,029,000,000 (reserved by the void v7 seal, never drawn); wave 7 v8 / c55 bands "\n'
     '                "2,030,000,001-2,035,000,000; whole range)", 1,\n'
     '                2_035_000_000),)')

# ---- r1w7/custody_w7.py (exclusion lists: every list applies to both pools, as v4 / v5 / v6 / v7 / v8)
edit("r1w7/custody_w7.py",
     '                      "X7v6_c54_real", "X7v6_c54_conv")                  # A-R1W7-8: X7v6\'s ids (job c54)',
     '                      "X7v6_c54_real", "X7v6_c54_conv",                  # A-R1W7-8: X7v6\'s ids (job c54)\n'
     '                      "X7v8_c55_real", "X7v8_c55_conv")                  # A-R1W7-10: X7v8\'s ids (job c55)')

# ---- kit
edit("kit/run_r1w7.py",
     "HELM_CUT_COMMIT = '%s'   # v8 (A-R1W7-9): the reader v7.1 fix, thread head (PR #437 merged, then PR #438)" % V8CUT,
     "HELM_CUT_COMMIT = '%s'   # v9 (A-R1W7-10): the reader v7.2 fix, thread head (PR #447 merged)" % CUT)
edit("kit/STAGE_R1W7.json", "cut at b10da2cd (v8, the reader v7.1 fix)", "cut at 55cda1e2 (v9, the reader v7.2 fix)")
edit("RUN_LIMITS_R1W7.json", '"package_version": "v8"', '"package_version": "v9"')
edit("RUN_LIMITS_R1W7.json",
     "the owner's line to sign is 'CHAT WAVE 5 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-9, section 21; unchanged from A-R1W7-8, never bound to the void v7 zip)",
     "the owner's line to sign is 'CHAT WAVE 6 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-10, section 22; the v8 line 'CHAT WAVE 5 at 1 USD' was consumed by job c55)")

# ---- tests
T = "tests_r1w7/test_units_w7.py"
edit(T, "        self.assertEqual(C.USED_RANGES[0][2], 2_029_000_000)", "        self.assertEqual(C.USED_RANGES[0][2], 2_035_000_000)")
edit(T,
     '        self.assertEqual(C.BANDS, {"REAL": (2_030_000_001, 2_031_000_000), "CONV": (2_032_000_001, 2_033_000_000),\n'
     '                                   "NOISE": (2_034_000_001, 2_035_000_000)})          # A-R1W7-9\n'
     '        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 5 at 1 USD")',
     '        self.assertEqual(C.BANDS, {"REAL": (2_036_000_001, 2_037_000_000), "CONV": (2_038_000_001, 2_039_000_000),\n'
     '                                   "NOISE": (2_040_000_001, 2_041_000_000)})          # A-R1W7-10\n'
     '        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 6 at 1 USD")')
edit(T,
     '        self.assertEqual(hc["files"], 167)                # v6: 166; v7 (A-R1W7-8): + test_helm_reader_gap.py; v8 (A-R1W7-9): the same 167 names, four files changed',
     '        self.assertEqual(hc["files"], 167)                # v6: 166; v7 (A-R1W7-8): + test_helm_reader_gap.py; v8 / v9 (A-R1W7-9 / A-R1W7-10): the same 167 names, four then five files changed')
edit(T,
     '                "X7v6_c54_real": 128, "X7v6_c54_conv": 64}                   # A-R1W7-8: X7v6\'s ids (job c54)',
     '                "X7v6_c54_real": 128, "X7v6_c54_conv": 64,                   # A-R1W7-8: X7v6\'s ids (job c54)\n'
     '                "X7v8_c55_real": 128, "X7v8_c55_conv": 64}                   # A-R1W7-10: X7v8\'s ids (job c55)')
edit(T,
     '        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv", "X7v4_c52_real",\n'
     '                     "X7v4_c52_conv", "X7v5_c53_real", "X7v5_c53_conv", "X7v6_c54_real", "X7v6_c54_conv"):',
     '        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv", "X7v4_c52_real",\n'
     '                     "X7v4_c52_conv", "X7v5_c53_real", "X7v5_c53_conv", "X7v6_c54_real", "X7v6_c54_conv",\n'
     '                     "X7v8_c55_real", "X7v8_c55_conv"):')
edit(T,
     '        self.assertEqual(len(set(d["lists"]["X7v6_c54_real"]) & (set(d["lists"]["X7_c51_real"]) | set(d["lists"]["X7v4_c52_real"]) | set(d["lists"]["X7v5_c53_real"]))), 0)   # c54 drew none of c51\'s, c52\'s or c53\'s',
     '        self.assertEqual(len(set(d["lists"]["X7v6_c54_real"]) & (set(d["lists"]["X7_c51_real"]) | set(d["lists"]["X7v4_c52_real"]) | set(d["lists"]["X7v5_c53_real"]))), 0)   # c54 drew none of c51\'s, c52\'s or c53\'s\n'
     '        self.assertEqual((len(d["lists"]["X7v8_c55_real"]), len(d["lists"]["X7v8_c55_conv"])), (128, 64))\n'
     '        self.assertEqual(d["blocks"]["X7v8_c55"]["lists"], ["X7v8_c55_real", "X7v8_c55_conv"])\n'
     '        older = {i for k, v in d["lists"].items() if not k.startswith("X7v8_c55") for i in v}\n'
     '        self.assertEqual(len((set(d["lists"]["X7v8_c55_real"]) | set(d["lists"]["X7v8_c55_conv"])) & older), 0)   # c55 drew none of any older list (0-overlap)')
edit(T,
     '        self.assertTrue(SR.blocked(2_029_000_000))\n'
     '        self.assertTrue(SR.blocked(2_030_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_030_000_001))',
     '        self.assertTrue(SR.blocked(2_029_000_000))\n'
     '        self.assertTrue(SR.blocked(2_030_000_000))\n'
     '        self.assertTrue(SR.blocked(2_030_000_001))             # v8\'s bands are spent (X7v8, job c55)\n'
     '        self.assertTrue(SR.blocked(2_035_000_000))\n'
     '        self.assertTrue(SR.blocked(2_036_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_036_000_001))')

# ---- README
edit("README_R1W7.md",
     "**v8 (amendment A-R1W7-9; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 5 at 1 USD`, unchanged from v7 and never bound to the v7 zip):**",
     "**v9 (amendment A-R1W7-10; status: SEALED, NOT LAUNCHED; waits for the owner's own typed line `CHAT WAVE 6 at 1 USD`):** the v8 "
     "package ran as job c55 and the frozen reader said `PASS` / `CHAT_WAVE_HARMED`: every instrument row and hard gate true, K4 HONEST "
     "true at last (0 unexplained asks), but K3 SAFE false — 2 wrong dialogue answers (the same 2 in the loop driven directly) and 1 wrong "
     "lesson on a real recipe. The per-item replay (SPEC 7.116, 7.117; names hashed, no exam text) found two mechanisms, not accidents: "
     "(1) a face-shaped clause about an ingredient the brain did not hold (one named by a plural/spelling form the matcher did not reach, "
     "one sharing nothing with a held name) was read as not-a-face, the stock stayed, and the question answered the raw yield; (2) a measure "
     "phrase after a separator (\"a dash of X\") was folded into the line before it as a note, so X's running-out was resolved onto that "
     "line's ingredient and a wrong amount was learned. The fix is reader v7.2 (SPEC 7.117, PR #447 merged = thread head `55cda1e2`): "
     "`helm_faces_in.py` v2.2 (an unheld subject in a face-shaped clause asks: `FACE_UNKNOWN_INGREDIENT` / `FACE_UNKNOWN_PRODUCT`; `-oes` / "
     "`-ves` / `-o` / `-f` / `-fe` forms), `helm_wide_turn.py` reader `RB-W1 v7.2` (the wide question holds its answer under `wide_face_block` "
     "until the stock is restated; a measure phrase after a separator is its own line; a ran-out phrase resolves through a line's own words "
     "only); `test_helm_reader_gap.py` 35 tests (7 new, 5 failing on v7.1); `test_helm_brain_wide.py` one exact-shape test gains the `own` "
     "key; the OFF-path pin is now `79e4914a561851d2cd19d04902f38e869787e36db0e984302bbbc6c434fa698c`. v9 = the v8 package with exactly "
     "three changes and nothing else: (1) `helm_now/` recut at thread head `55cda1e2` (the same 167 names; five files changed: "
     "`helm_wide_turn.py`, `helm_faces_in.py`, `test_helm_brain_wide.py`, `test_helm_cas_address.py`, `test_helm_reader_gap.py`; every other "
     "file equal to v8's cut; `helm_brain_canonical.py` = base `24df53c9…`); (2) block `X7v8_c55` on the exclusion list (c55's 128 REAL ids "
     "and 64 CONV pool ids, 0 overlap with every older list); (3) **amendment A-R1W7-10**: fresh seed bands 2,036 M / 2,038 M / 2,040 M "
     "(used table 1-2,035,000,000; v8's 2,030-2,035 M spent by c55) and the new owner line. The host's list stays 12 names (run from the "
     "seal, `TEST_COUNTS_R1W7_v9.json`); A-R1W7-7 stays applied (the same hook; the same 6 of 128 practice recipes `NOT_SCORED`); reader, "
     "recorder, fixture, marks, thresholds, arms and status words unchanged. v8 is VOID_SUPERSEDED_BY_V9 for any further run (c55's record "
     "stands). "
     "**v8 (amendment A-R1W7-9; was: SEALED, ran as job c55, PASS / CHAT_WAVE_HARMED with a clean instrument and K3 missed by 2 wrong answers and 1 wrong lesson; owner's line was `CHAT WAVE 5 at 1 USD`):**")
edit("README_R1W7.md",
     "| `helm_now/` | HELM's code under test: 167 files cut by `git show` from commit `b10da2cd` (v8, the reader v7.1 fix; v7 was the same 167 names at `47440415`, v6 166 files at `ad4fde73`, v5 164 at `f45a8570`, v3/v4 161 at `dfc7158d`)",
     "| `helm_now/` | HELM's code under test: 167 files cut by `git show` from commit `55cda1e2` (v9, the reader v7.2 fix; v8 was the same 167 names at `b10da2cd`, v7 at `47440415`, v6 166 files at `ad4fde73`, v5 164 at `f45a8570`, v3/v4 161 at `dfc7158d`)")
edit("README_R1W7.md",
     "`TEST_COUNTS_R1W7_v8.json` (`host_exact_suite_list`), asserting the list equals the sealed kit's `HELM_TESTS`.",
     "`TEST_COUNTS_R1W7_v9.json` (`host_exact_suite_list`), asserting the list equals the sealed kit's `HELM_TESTS`.")
edit("README_R1W7.md",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v8.zip>",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip>")

# ---- custodian procedure
CP = "contract/CUSTODIAN_PROCEDURE_R1W7.md"
edit(CP,
     "The line to sign is **`CHAT WAVE 5 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-9, section 21; the line is the one A-R1W7-8 proposed for v7 and was never bound to the void v7 zip, so it may bind the v8 zip; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51, the v4 line `CHAT WAVE 2 at 1 USD` by job c52, the v5 line `CHAT WAVE 3 at 1 USD` by job c53 and the v6 line `CHAT WAVE 4 at 1 USD` by job c54; none may bind a second zip).",
     "The line to sign is **`CHAT WAVE 6 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-10, section 22; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51, the v4 line `CHAT WAVE 2 at 1 USD` by job c52, the v5 line `CHAT WAVE 3 at 1 USD` by job c53, the v6 line `CHAT WAVE 4 at 1 USD` by job c54 and the v8 line `CHAT WAVE 5 at 1 USD` by job c55; none may bind a second zip).")
edit(CP,
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-9, section 21)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 5 at 1 USD\" + \":\" + <full sha256 of the sealed v8 zip, 64 lower-case hex> )",
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-10, section 22)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 6 at 1 USD\" + \":\" + <full sha256 of the sealed v9 zip, 64 lower-case hex> )")
edit(CP,
     "1,000,000; seed = band low + slot. Bands (v8): REAL 2,030,000,001-2,031,000,000; CONV 2,032,000,001-2,033,000,000; NOISE\n2,034,000,001-2,035,000,000; used table 1-2,029,000,000 whole (v3's bands were spent by X7, v4's by X7v4, v5's by X7v5, v6's by X7v6; v7's 2,024-2,029 M are\nreserved by the void v7 seal and were never drawn; 1,996-1,999 M stays reserved for the continuity packet and 2,018-2,022 M for the talk packet); gap 1,000,000; slot stepping and STOP as wave 6.",
     "1,000,000; seed = band low + slot. Bands (v9): REAL 2,036,000,001-2,037,000,000; CONV 2,038,000,001-2,039,000,000; NOISE\n2,040,000,001-2,041,000,000; used table 1-2,035,000,000 whole (v3's bands were spent by X7, v4's by X7v4, v5's by X7v5, v6's by X7v6, v8's by X7v8; v7's 2,024-2,029 M are\nreserved by the void v7 seal and were never drawn; 1,996-1,999 M stays reserved for the continuity packet and 2,018-2,022 M for the talk packet); gap 1,000,000; slot stepping and STOP as wave 6.")
edit(CP,
     "(v6, block `X7v5_c53`) X7v5's 128 REAL ids and 64 CONV pool ids from job c53, and (v7, block `X7v6_c54`) X7v6's 128 REAL ids and 64 CONV pool ids from job c54.",
     "(v6, block `X7v5_c53`) X7v5's 128 REAL ids and 64 CONV pool ids from job c53, (v7, block `X7v6_c54`) X7v6's 128 REAL ids and 64 CONV pool ids from job c54, and (v9, block `X7v8_c55`) X7v8's 128 REAL ids and 64 CONV pool ids from job c55.")
edit(CP,
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v8.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v8 zip; the v3 zip `5063baba…`, the v4 zip `8602b1bc…`, the v5 zip `4b54a077…`, the v6 zip `387577de…` and the v7 zip `42c044a9…` are VOID_SUPERSEDED and the seal refuses them).",
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v9 zip; the v3 zip `5063baba…`, the v4 zip `8602b1bc…`, the v5 zip `4b54a077…`, the v6 zip `387577de…`, the v7 zip `42c044a9…` and the v8 zip `e88b125e…` are VOID_SUPERSEDED and the seal refuses them).")
edit(CP,
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v8_custody\\pkg\\` (never over the c51 / c52 / c53 / c54 custody folders `x7_custody\\`, `x7v4_custody\\`, `x7v5_custody\\`, `x7v6_custody\\`; no v7 custody folder exists, v7 was never drawn).",
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v9_custody\\pkg\\` (never over the c51 / c52 / c53 / c54 / c55 custody folders `x7_custody\\`, `x7v4_custody\\`, `x7v5_custody\\`, `x7v6_custody\\`, `x7v8_custody\\`; no v7 custody folder exists, v7 was never drawn).")

for rel in ("r1w7/common_w7.py", "r1w7/custody_w7.py", "kit/run_r1w7.py", "tests_r1w7/test_units_w7.py", "README_R1W7.md",
            "contract/CUSTODIAN_PROCEDURE_R1W7.md", "kit/STAGE_R1W7.json", "RUN_LIMITS_R1W7.json"):
    if b"\x08" in (PKG / rel).read_bytes():
        raise SystemExit("stray backspace byte in " + rel)
out = {"schema": "helm.r1w7.patch-log/1", "version": "v9", "edits": log,
       "a_r1w7_7_checked_present_not_reapplied": True, "x7v8_c55_block_checked_present": True,
       "files_sha256": {rel: hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
                        for rel in sorted({e["file"] for e in log})}}
LOG.write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps({"edits": len(log)}, indent=1))
