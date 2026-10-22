# PIN TEST DIAGNOSIS — why `test_off_is_byte_identical_to_the_pre_change_code` failed on the c53 host (wave 7 round 4, 2026-10-21, laptop, 0 USD)

Plainly: the test hashed a bundle of records that contains the folder path of the licensed brain. The laptop and the host
keep that brain in different folders, so the hash differed. Nothing in HELM's behaviour differed. The second-pass fix
(commit `ad4fde73`) hashes the records with that path, and the two receipt values that depend on it, cut out; the hash is
then the same on every machine, which was checked here five ways.

## 1. The failure on record (job c53, v5 package, HELM cut `f45a8570`)

- Host: Ubuntu 24.04.5, Python 3.12.3, `/opt/helm-shared-r2/`. HELM's own suite (10 unittest files, one process):
  `Ran 236 tests in 2.701s`, `FAILED (failures=1, skipped=2)`.
- The one failure: `test_helm_cas_address.C_LoopStamps.test_off_is_byte_identical_to_the_pre_change_code`,
  `'6bf323adcde8e01391125280f0f88ec6cb94b9e5ef2baff2a3b45c7f778e9606' != '56f356ea7302a80fd7073c6b76335fb7453ee32ac2950e1c2e4a1cf18b64acc8'`.
- The same test passes on this laptop (Windows 11, Python 3.14.0) on the same cut. Reader verdict `INSTRUMENT_ERROR` /
  `INCONCLUSIVE` (instrument row I6 `suites_ok` false); all 10 hard gates and all six marks true as facts.

## 2. First-pass finding by the v6 builder (program diff, laptop)

Tool: a script that runs the test's own `fixture_records()` with the switches OFF, writes the canonical JSON, and compares
two runs leaf by leaf (`dump_fixture.py`, `reproduce_host_hash.py`, `neutral_leaf_diff.py`; builder scratch).

1. Suspect scan of the canonical records (74,550 bytes): 0 CRLF, 0 `win32` / `linux` words, 0 Python version strings,
   0 object reprs, 0 Fraction reprs; 2 strings that are absolute paths, both the licensed brain folder
   (`trace[17].brain.brain_dir`, `trace[35].brain.brain_dir`, the value `helm_brain_canonical.load_package` returns as
   `brain_dir`, line 150 / 177 / 221 of that byte-identical file).
2. The same brain at another laptop folder (the wave-7 deps copy) changes **exactly 6 leaves**: the 2 `brain_dir` values and
   4 `receipt_hash` values (2 distinct: `results[2]` = `trace[25]`, `results[4]` = `trace[43]`). The receipt hash is the
   loop's `_h16({"status", "records", "message"})` over the turn's records, which include the brain row with the path.
   So the path reaches the hash twice: directly, and through two receipts computed inside the loop.
3. Exact reproduction: making `load_package` report the host's folder string
   `/opt/helm-shared-r2/sources/w1/HELM_R1_W1_20261015` (from c53's `R1_W7_HOST.json`) while loading the real folder gives
   **`6bf323ad…` exactly** — on the v5 cut `f45a8570` and on base `159c7d2b`. Reporting the laptop's default folder
   `C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3` gives `56f356ea…` on both.
   Conclusion: the host's OFF path WAS byte-identical to the pre-change code; the stored pin was one machine's value.
   Not the platform, not the Python version, not line endings.

## 3. The peer's first pass, `3dae274f` (branch `claude/helm-pin-hygiene-20261021`, PR #428, merged as thread head `5f07c5d7`): INSUFFICIENT

- What it did: `helm_test_pins.neutral()` replaced an absolute path by `<path>/<last component>`; new pin `632bffc0…`;
  `test_helm_pin_hygiene.py` (7 tests) varied the session folder and the working directory.
- All 15 files passed on the laptop (unittest 243, pytest-style 20). `helm_brain_canonical.py` = base `24df53c9…`;
  `helm_wide_turn.py` and `helm_end_to_end_loop.py` byte-identical to `f45a8570`.
- But by the same diff, **6 leaves still differed after `neutral()`** between the laptop folder and the host folder:
  the last components differ (`HELM_R1_W1_20261015_v3` vs `HELM_R1_W1_20261015`), and the 4 receipt hashes are computed
  inside the loop over the raw path, which no test-side canonicaliser can undo. Hashes: laptop default `632bffc0…` (= the
  pin), host path reported **`d2e5fb18843023ee32b47490f3cfa4d056d58b5af3fc017d1ac7330441be843e`**, deps folder
  `4c1146bb…`; even with the same last component under another parent, 4 leaves (the receipts) still differed.
  `offending()` reported nothing in any case; the hygiene test never varied the brain folder, which is why it passed.
- Reported to the coordinator as a STOP (forecast: I6 false again on the host, with `d2e5fb18…`).

## 4. The peer's second pass, `ad4fde73` (branch `claude/helm-pin-hygiene-2-20261021`, PR #429, 1 commit on thread head `5f07c5d7`): VERIFIED

- What it does: `helm_test_pins.STRIP_LEAVES = ("brain_dir", "receipt_hash")`; `neutral()` replaces those leaves by
  `<stripped:NAME>` and any other absolute path by `<path>/<last component>`; `test_helm_cas_address.py` hashes through it,
  pin `312ddfd687f73182be524acc64f0829d67d11c29ba9546915f344998927abf64`; `test_helm_pin_hygiene.py` (9 tests) now copies
  the licensed brain to `<temp>/sources/w1/HELM_R1_W1_20261015` and demands the same pin, and tests the strip rule.
- Verified here (every case the pin `312ddfd6…`):
  1. host folder string reported (`/opt/helm-shared-r2/sources/w1/HELM_R1_W1_20261015`);
  2. laptop default folder string reported (`…\HELM_R1_W1_20261015_v3`);
  3. the deps folder for real (`…\r1_wave7\deps\HELM_R1_W1_20261015`, nothing patched);
  4. a copy of the brain under another parent for real (`<scratch>\copyparent\sources\w1\HELM_R1_W1_20261015`);
  5. the laptop default folder for real.
  Leaf diff of `neutral()` output, laptop folder vs host folder: **0 differing leaves**; `offending()` empty for both.
- `helm_brain_canonical.py` sha256 `24df53c9b3abeeafa2c38a0d8aa808537055ab29a7eaffd235031cbfb430980a` (= base);
  `helm_wide_turn.py`: empty diff against the round-3 fix `f45a8570`; `helm_end_to_end_loop.py`: empty diff against `5f07c5d7`.
- Suites on `ad4fde73`, one process each (host loader form, `python -X utf8 -B -I`): brain_wide 54, cas_address 17,
  end_to_end_loop 18, english_in 37, english_in_stock_frame 17, faces_in 16, pin_hygiene 9, triad 15, units_note 15,
  voice 22, wide_alongside 25 — all OK (245); pytest-style (`python -X utf8 -B -m pytest`, pytest 9.0.2 in the user site):
  agentic_planner 8, chat_nuance 8, memory 4 passed. The host's exact command form (11 names, one process, scratch copy,
  `HELM_SESSION_DIR` inside the scratch, `HELM_CANONICAL_BRAIN_DIR` = the deps wave-1 folder): `Ran 245 tests in 5.933s`,
  `OK (skipped=1)` (the one skip is `test_licensed_files_untouched`, "base commit not reachable in this checkout", as on c53).
- What is NOT claimed: no Linux run happened on the laptop. The host-path case above is an emulation that reproduced
  c53's exact failing hash on the old code, which is the evidence that it models the host faithfully.

## 5. The v6 builder's own withdrawn attempt (for the record)

Before the coordinator's change of plan, the builder had committed a different fix (`62d559a8`: pin keyed by brain folder,
laptop and host values from base `159c7d2b`, skip-with-print elsewhere) and opened PR #427. It was withdrawn and PR #427
closed; no HELM code from it is used. Its root-cause work (section 2) stands and is the basis of this diagnosis.

## 6. What v6 does with this

The v6 cut is `ad4fde73` (166 files; the cut rule names `helm_test_pins.py` explicitly). The host's HELM list gains
`test_helm_pin_hygiene` (11 names). The seal step runs exactly that list with the host's command form from a fresh extract
and records it under `host_exact_suite_list` in `TEST_COUNTS_R1W7_v6.json` (amendment A-R1W7-6, section 18 of the
package's preregistration).
