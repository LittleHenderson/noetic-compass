"""Builder tool (NOT sealed): every v8 LABEL edit to the package (constants, kit, run limits, tests, README, custodian
procedure). Each edit is an exact once-only replacement; the log names every one. The precode sections and amendments 1-8
of PREREGISTRATION_R1W7.md are not touched; amendment A-R1W7-9 is appended by append_amendment_9.py. Amendment A-R1W7-7's
code (multi_qty_w7.py, its test, the custody hook) is already in the v7 extract this package starts from; it is checked,
not re-applied. The exclusion list is not touched (no exam was drawn since c54: block X7v6_c54 stays the last block).

    python -X utf8 -B -I patch_v8.py <v8 package dir> <log json>
"""
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
LOG = Path(sys.argv[2]).resolve()
CUT = "b10da2cd2c78317f5983fa8460ac137c8034556b"
V7CUT = "4744041503ca6feb044afa05cbb380533de2fcfe"
V7ZIP = "42c044a905f6101b97a95a440554fec2d8fa4dc16196dcbc44e484993054dfaa"
log = []


def edit(rel, old, new):
    p = PKG / rel
    text = p.read_bytes().decode("utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{rel}: target not found exactly once: {old[:70]!r}")
    p.write_bytes(text.replace(old, new).encode("utf-8"))
    log.append({"file": rel, "old": old[:90], "new": new[:90]})


# ---- A-R1W7-7 must already be in the tree (the v7 extract carries it); checked, never re-applied
cu = (PKG / "r1w7" / "custody_w7.py").read_text(encoding="utf-8")
if cu.count('"keys": [MQ.apply(K.key_item(it), it["raw_lines"], ns.XG) for it in real_items]') != 1 or \
        not (PKG / "r1w7" / "multi_qty_w7.py").is_file() or not (PKG / "tests_r1w7" / "test_multi_qty_w7.py").is_file():
    raise SystemExit("A-R1W7-7 is not in the tree this package starts from")

# ---- r1w7/common_w7.py
edit("r1w7/common_w7.py",
     "exactly as the code runs at commit 47440415 (v7, the reader-gap build, thread head = PR #435 merged; amendments A-R1W7-2 to A-R1W7-8)",
     "exactly as the code runs at commit b10da2cd (v8, the reader v7.1 fix, thread head = PR #437 merged; amendments A-R1W7-2 to A-R1W7-9)")
edit("r1w7/common_w7.py", 'PACKAGE_VERSION = "v7"', 'PACKAGE_VERSION = "v8"')
edit("r1w7/common_w7.py",
     'HELM_CUT_COMMIT = "%s"       # v7 (A-R1W7-8): the reader-gap build (SPEC 7.111, PR #435 merged = thread head); v6 was ad4fde73, v5 f45a8570, v3/v4 dfc7158d' % V7CUT,
     'HELM_CUT_COMMIT = "%s"       # v8 (A-R1W7-9): the reader v7.1 fix (SPEC 7.113, PR #437 merged; thread head after PR #438); v7 was 47440415, v6 ad4fde73, v5 f45a8570, v3/v4 dfc7158d' % CUT)
edit("r1w7/common_w7.py",
     'HELM_THREAD_BRANCH = "claude/project-thread-pmbzd6 (thread head 47440415 = merge of PR #435, the reader-gap build)"',
     'HELM_THREAD_BRANCH = "claude/project-thread-pmbzd6 (thread head b10da2cd = merge of PR #438, after PR #437, the reader v7.1 fix)"')
edit("r1w7/common_w7.py",
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-8, section 20); the approval record is written only after the owner signs"',
     'OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-9, section 21; the line is unchanged from A-R1W7-8 and was never bound to the void v7 zip); the approval record is written only after the owner signs"')
edit("r1w7/common_w7.py",
     'BANDS = {"REAL": (2_024_000_001, 2_025_000_000), "CONV": (2_026_000_001, 2_027_000_000),\n'
     '         "NOISE": (2_028_000_001, 2_029_000_000)}          # A-R1W7-8: above v6\'s 2,012-2,017 M (spent by X7v6 / c54) and the talk packet\'s reserved 2,018-2,022 M; 1,996-1,999 M stays reserved for the continuity packet',
     'BANDS = {"REAL": (2_030_000_001, 2_031_000_000), "CONV": (2_032_000_001, 2_033_000_000),\n'
     '         "NOISE": (2_034_000_001, 2_035_000_000)}          # A-R1W7-9: above v7\'s 2,024-2,029 M (reserved by the void v7 seal, never drawn); 1,996-1,999 M stays reserved for the continuity packet, 2,018-2,022 M for the talk packet')
edit("r1w7/common_w7.py",
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; wave 7 v5 / c53 bands 2,006,000,001-2,011,000,000; wave 7 v6 / c54 bands "\n'
     '                "2,012,000,001-2,017,000,000; the talk packet\'s proposed 2,018,000,001-2,022,000,000; whole range)", 1,\n'
     '                2_023_000_000),)',
     'USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "\n'
     '                "1,990,000,001-1,995,000,000; the continuity packet\'s proposed 1,996,000,001-1,999,000,000; wave 7 v4 / c52 bands "\n'
     '                "2,000,000,001-2,005,000,000; wave 7 v5 / c53 bands 2,006,000,001-2,011,000,000; wave 7 v6 / c54 bands "\n'
     '                "2,012,000,001-2,017,000,000; the talk packet\'s proposed 2,018,000,001-2,022,000,000; wave 7 v7 bands "\n'
     '                "2,024,000,001-2,029,000,000 (reserved by the void v7 seal, never drawn); whole range)", 1,\n'
     '                2_029_000_000),)')

# ---- kit
edit("kit/run_r1w7.py",
     "HELM_CUT_COMMIT = '%s'   # v7 (A-R1W7-8): the reader-gap build, thread head (PR #435 merged)" % V7CUT,
     "HELM_CUT_COMMIT = '%s'   # v8 (A-R1W7-9): the reader v7.1 fix, thread head (PR #437 merged, then PR #438)" % CUT)
edit("kit/STAGE_R1W7.json", "cut at 47440415 (v7, the reader-gap build)", "cut at b10da2cd (v8, the reader v7.1 fix)")
edit("RUN_LIMITS_R1W7.json", '"package_version": "v7"', '"package_version": "v8"')
edit("RUN_LIMITS_R1W7.json",
     "the owner's line to sign is 'CHAT WAVE 5 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-8, section 20)",
     "the owner's line to sign is 'CHAT WAVE 5 at 1 USD' (PREREGISTRATION_R1W7.md section 8 as superseded by A-R1W7-9, section 21; unchanged from A-R1W7-8, never bound to the void v7 zip)")

# ---- tests
T = "tests_r1w7/test_units_w7.py"
edit(T, "        self.assertEqual(C.USED_RANGES[0][2], 2_023_000_000)", "        self.assertEqual(C.USED_RANGES[0][2], 2_029_000_000)")
edit(T,
     '        self.assertEqual(C.BANDS, {"REAL": (2_024_000_001, 2_025_000_000), "CONV": (2_026_000_001, 2_027_000_000),\n'
     '                                   "NOISE": (2_028_000_001, 2_029_000_000)})          # A-R1W7-8',
     '        self.assertEqual(C.BANDS, {"REAL": (2_030_000_001, 2_031_000_000), "CONV": (2_032_000_001, 2_033_000_000),\n'
     '                                   "NOISE": (2_034_000_001, 2_035_000_000)})          # A-R1W7-9')
edit(T,
     '        self.assertEqual(hc["files"], 167)                # v6: 166; v7 (A-R1W7-8): + test_helm_reader_gap.py',
     '        self.assertEqual(hc["files"], 167)                # v6: 166; v7 (A-R1W7-8): + test_helm_reader_gap.py; v8 (A-R1W7-9): the same 167 names, four files changed')
edit(T,
     '        self.assertTrue(SR.blocked(2_023_000_000))\n'
     '        self.assertTrue(SR.blocked(2_024_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_024_000_001))',
     '        self.assertTrue(SR.blocked(2_023_000_000))\n'
     '        self.assertTrue(SR.blocked(2_024_000_000))\n'
     '        self.assertTrue(SR.blocked(2_024_000_001))             # v7\'s bands are reserved by the void v7 seal (never drawn)\n'
     '        self.assertTrue(SR.blocked(2_029_000_000))\n'
     '        self.assertTrue(SR.blocked(2_030_000_000))             # the gap\n'
     '        self.assertFalse(SR.blocked(2_030_000_001))')

# ---- README
edit("README_R1W7.md",
     "**v7 (amendments A-R1W7-7 and A-R1W7-8; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 5 at 1 USD`):**",
     "**v8 (amendment A-R1W7-9; status: SEALED, NOT LAUNCHED; waits for the owner's line `CHAT WAVE 5 at 1 USD`, unchanged from v7 and "
     "never bound to the v7 zip):** v7 was VOID FOR LAUNCH on its own practice reading (`PRACTICE_READINGS_V7.json`): the v7 reader turned 4 "
     "honest asks into 4 wrong dialogue answers (CV32, CV33, CV34, CV37, all `S1_WISDOM_STATED`), because the clause named the held ingredient "
     "by a longer or hyphenated phrase, the face read `FACE_UNREAD` or `NONE`, and the question answered from the recorded stock as if the "
     "clause were unsaid. The fix is reader v7.1 (SPEC 7.113, PR #437 merged on the thread): `helm_faces_in.py` v2.1 (a longer-phrase name slot "
     "resolved to the held name; hyphen and space variants of a two-word name; two held names inside the phrase → `FACE_WHICH_INGREDIENT`) and "
     "`helm_wide_turn.py` reader `RB-W1 v7.1` (an unread clause withdraws the named ingredient's stock on both paths, so the question asks); "
     "`test_helm_reader_gap.py` 28 tests; the OFF-path pin is now `2c8ba0196921e42ab654cd850032ee5da0e5687b60b809e6cbfa337ea6a01a55`. v8 = the "
     "v7 package with exactly two changes and nothing else: (1) `helm_now/` recut at thread head `b10da2cd` (the same 167 names; four files "
     "changed: `helm_wide_turn.py`, `helm_faces_in.py`, `test_helm_cas_address.py`, `test_helm_reader_gap.py`; every other file equal to v7's "
     "cut; `helm_brain_canonical.py` = base `24df53c9…`); (2) **amendment A-R1W7-9**: fresh seed bands 2,030 M / 2,032 M / 2,034 M (used table "
     "1-2,029,000,000; v7's 2,024-2,029 M reserved by the void seal, never drawn) and the labels. The host's list stays 12 names (run from the "
     "seal, `TEST_COUNTS_R1W7_v8.json`); A-R1W7-7 stays applied (the same hook; the same 6 of 128 practice recipes `NOT_SCORED`); block "
     "`X7v6_c54` stays the last exclusion block (no exam was drawn since c54); reader, recorder, fixture, marks, thresholds, arms and status "
     "words unchanged. v7 is VOID_SUPERSEDED_BY_V8. "
     "**v7 (amendments A-R1W7-7 and A-R1W7-8; was: SEALED, then VOID FOR LAUNCH on its own practice finding; its line was never bound):**")
edit("README_R1W7.md",
     "| `helm_now/` | HELM's code under test: 167 files cut by `git show` from commit `47440415` (v7, the reader-gap build; v6 was 166 files at `ad4fde73`, v5 164 at `f45a8570`, v3/v4 161 at `dfc7158d`)",
     "| `helm_now/` | HELM's code under test: 167 files cut by `git show` from commit `b10da2cd` (v8, the reader v7.1 fix; v7 was the same 167 names at `47440415`, v6 166 files at `ad4fde73`, v5 164 at `f45a8570`, v3/v4 161 at `dfc7158d`)")
edit("README_R1W7.md",
     "`TEST_COUNTS_R1W7_v7.json` (`host_exact_suite_list`), asserting the list equals the sealed kit's `HELM_TESTS`.",
     "`TEST_COUNTS_R1W7_v8.json` (`host_exact_suite_list`), asserting the list equals the sealed kit's `HELM_TESTS`.")
edit("README_R1W7.md",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v7.zip>",
     "--zip <HELM_R1_W7_20261020_SOURCE_R1W7_v8.zip>")

# ---- custodian procedure
CP = "contract/CUSTODIAN_PROCEDURE_R1W7.md"
edit(CP,
     "The line to sign is **`CHAT WAVE 5 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-8, section 20; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51, the v4 line `CHAT WAVE 2 at 1 USD` by job c52, the v5 line `CHAT WAVE 3 at 1 USD` by job c53 and the v6 line `CHAT WAVE 4 at 1 USD` by job c54; none may bind a second zip).",
     "The line to sign is **`CHAT WAVE 5 at 1 USD`** (20 UTF-8\nbytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-9, section 21; the line is the one A-R1W7-8 proposed for v7 and was never bound to the void v7 zip, so it may bind the v8 zip; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51, the v4 line `CHAT WAVE 2 at 1 USD` by job c52, the v5 line `CHAT WAVE 3 at 1 USD` by job c53 and the v6 line `CHAT WAVE 4 at 1 USD` by job c54; none may bind a second zip).")
edit(CP,
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-8, section 20)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 5 at 1 USD\" + \":\" + <full sha256 of the sealed v7 zip, 64 lower-case hex> )",
     "## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-9, section 21)\n\n    H = sha256( UTF-8 bytes of  \"CHAT WAVE 5 at 1 USD\" + \":\" + <full sha256 of the sealed v8 zip, 64 lower-case hex> )")
edit(CP,
     "1,000,000; seed = band low + slot. Bands (v7): REAL 2,024,000,001-2,025,000,000; CONV 2,026,000,001-2,027,000,000; NOISE\n2,028,000,001-2,029,000,000; used table 1-2,023,000,000 whole (v3's bands were spent by X7, v4's by X7v4, v5's by X7v5, v6's by X7v6; 1,996-1,999 M stays\nreserved for the continuity packet and 2,018-2,022 M for the talk packet); gap 1,000,000; slot stepping and STOP as wave 6.",
     "1,000,000; seed = band low + slot. Bands (v8): REAL 2,030,000,001-2,031,000,000; CONV 2,032,000,001-2,033,000,000; NOISE\n2,034,000,001-2,035,000,000; used table 1-2,029,000,000 whole (v3's bands were spent by X7, v4's by X7v4, v5's by X7v5, v6's by X7v6; v7's 2,024-2,029 M are\nreserved by the void v7 seal and were never drawn; 1,996-1,999 M stays reserved for the continuity packet and 2,018-2,022 M for the talk packet); gap 1,000,000; slot stepping and STOP as wave 6.")
edit(CP,
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v7.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v7 zip; the v3 zip `5063baba…`, the v4 zip `8602b1bc…`, the v5 zip `4b54a077…` and the v6 zip `387577de…` are VOID_SUPERSEDED and the seal refuses them).",
     "1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v8.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`\n   (the v8 zip; the v3 zip `5063baba…`, the v4 zip `8602b1bc…`, the v5 zip `4b54a077…`, the v6 zip `387577de…` and the v7 zip `42c044a9…` are VOID_SUPERSEDED and the seal refuses them).")
edit(CP,
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v7_custody\\pkg\\` (never over the c51 / c52 / c53 / c54 custody folders `x7_custody\\`, `x7v4_custody\\`, `x7v5_custody\\`, `x7v6_custody\\`).",
     "e.g. `Documents\\Codex\\2026-10-20\\r1_wave7\\x7v8_custody\\pkg\\` (never over the c51 / c52 / c53 / c54 custody folders `x7_custody\\`, `x7v4_custody\\`, `x7v5_custody\\`, `x7v6_custody\\`; no v7 custody folder exists, v7 was never drawn).")

for rel in ("r1w7/common_w7.py", "kit/run_r1w7.py", "tests_r1w7/test_units_w7.py", "README_R1W7.md",
            "contract/CUSTODIAN_PROCEDURE_R1W7.md", "kit/STAGE_R1W7.json", "RUN_LIMITS_R1W7.json"):
    if b"\x08" in (PKG / rel).read_bytes():
        raise SystemExit("stray backspace byte in " + rel)
out = {"schema": "helm.r1w7.patch-log/1", "version": "v8", "edits": log,
       "a_r1w7_7_checked_present_not_reapplied": True,
       "files_sha256": {rel: hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
                        for rel in sorted({e["file"] for e in log})}}
LOG.write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps({"edits": len(log)}, indent=1))
