# Reviews of the HSET-2 build, and the builder's disposition of each finding (`CLAUDE_BUILT_CLAUDE_CHECKED`)

**What was reviewed.** The HSET-2 build at commit `853e645d7b5da5551257c4271e10c90b5fdb254e` (branch
`claude/hset2-build-20260924`): `hset2_build.py`, its tests and the AWS job in `../hset2_aws_job/`.

**Who.** Two independent reviewers (Claude sub-agents) found the problems. The coordinator's workflow passed their
findings to the builder as one list. The builder is Claude, the temporary builder while Codex is away. The builder wrote
every disposition below and checked its own fixes. No independent reviewer has read the fixes yet.

**What this is not.**
- No model was loaded, trained or run. Nothing here is a result about Helm.
- No real salt was used. The HSET-2 salt does not exist yet. The sealed build has not run.
- Every number below comes from THROWAWAY salts (made from public strings) or from the public stage 0.

## 0. The short version

- **Two BLOCKERs** were real. In each, a rule that learns nothing could pass a claim. I reproduced both reviewers'
  numbers exactly on their own throwaway salts.
- **I added the missing bars in code (option (a) of each finding).** A new bar can only make a claim harder to pass.
  The design text does not have them yet. So the change is written below as **Amendment A2, PROPOSED**. The designer
  or the owner must accept A2, or choose option (b), **before the HSET-2 salt is made**. The builder does not decide
  this. Adding a bar after the sealed build prints W would be a post-hoc change.
- **What the owner must hear now** (section 3):
  - `REACH_3_STEP_TRANSFER_6` could carry a claim in only **14 of 21** throwaway salts. It will read `NOT_TESTABLE`
    about 1 time in 3.
  - `REACH_4_STEP_TRANSFER_6` could carry a claim in **0 of 21** throwaway salts (binding W 0 to 5).
  - `ANALOGY_BEYOND_DEGREE_6` could carry a claim in **19 of 21** throwaway salts (binding W 9 to 19).
  - The correspondence claims do not change in practice.
- **Nine MINORs.** Seven are fixed. One (F9, tool pinning) is fixed except one pin that the coordinator must fill in
  before launch; the launcher refuses until then. One (F3, the DEV decoy pool) is a reading I kept; the owner should
  confirm it.
- **Tests:** 24 of 24 pass (21 fast, 2 end-to-end, 1 slow).

| # | Severity | Finding in one line | Disposition |
|---|---|---|---|
| F1 | BLOCKER | A per-candidate "guess by degree, then check" rule passes the analogy claim | Bars added in code; design text = proposed A2; owner or designer decides before the salt |
| F2 | BLOCKER | A root-count fallback after two-hop passes the 3-step reach claim | Bars added in code (also the three-hop form for the 4-step claim); proposed A2; decide before the salt |
| F3 | MINOR | DEV decoys come from the whole DEV side, not only `DEV_DECOYS_6` | Reading kept (it mirrors TEST); both sets of counts printed; owner to confirm |
| F4 | MINOR | Reach packets keep the frozen bank unrelabelled | The rule is written into the plan and into proposed A2 |
| F5 | MINOR | Two printed custody checks cannot fail | Fixed: every printed value is now counted from the sets |
| F6 | MINOR | In real mode an uncaught exception's text reaches `build.log` | Fixed: wrapped; the traceback goes to the sealed folder only |
| F7 | MINOR | Committing the launch pins would break two tests | Fixed: the tests pass with or without the pins; a missing salt file is a clean refusal |
| F8 | MINOR | (same as F6, from the second reviewer) | Fixed with F6 |
| F9 | MINOR | Unpinned third-party code runs while both salts are on disk | Fixed except one coordinator pin: tools pinned and installed before the salts arrive |
| F10 | MINOR | Two real-mode paths run for the first time in the paid build | Fixed: the smoke re-measures the trained states; the TEST_NEW_5 digest is checked before any item |
| F11 | MINOR | Throwaway outputs look like DEV feedback but hold forbidden 5-node classes | Fixed: renamed `THROWAWAY_*`, role `THROWAWAY_NOT_DEV`, refused inside a git tree; old copies listed for the owner |

**Numbering.** F1 to F11 follow the order in which the findings arrived. From the path style in each finding, F1 to F6
seem to come from one reviewer and F7 to F11 from the other. That split is my inference.

## 1. The findings as the reviewers wrote them, with my disposition

### F1. BLOCKER: a rule that learns nothing passes `ANALOGY_BEYOND_DEGREE_6`

**Reviewer's summary.** "A rule that learns nothing passes ANALOGY_BEYOND_DEGREE_6 in 6 of 6 throwaway salts. It is the
analogy form of the bar that correspondence already has (DEGREE_GUESS_THEN_CHECK), and it is not registered for
analogy."

**Reviewer's scenario.** The rule looks at each other-domain candidate that has the focus's joint degree list, in alias
order. For each one it makes one guess: sort nodes by (in, out, rank). It checks every edge. It answers the first
candidate that passes, and otherwise NO_MATCH. On the NO_MATCH twin no check can pass, so it is always right there.
With throwaway salts sha256('HSET-2-THROWAWAY-SALT|REVIEWER-a<i>|hset2'), i = 5, 7, 8, 9, 12, 16: TEST_NEW_6/ANALOGY had
24, 22, 23, 26, 25 and 19 clusters; the binding registered bar `FLAG_ANCHOR` had W = 24, 21, 22, 26, 25, 18; this rule
had W = 15, 12, 11, 13, 16, 9. Treated as a model it beats every registered analogy bar in every salt (b = 9 to 13,
c = 0 to 1, worst p = 0.00195). DEV_NEW_6 passes too. The strictly one-guess variant (check only the first same-degree
candidate) gets only about 1 cluster right. So the claim hinges on how the s6 line ("may make one guess and check it")
applies to a bank of candidates. The design does not say.

**Reviewer's fix.** A design decision before the salt: (a) register an analogy `DEGREE_GUESS_THEN_CHECK` (optionally
also the whole-anchored form, W 12 to 17), re-print the ranges, and tell the owner the binding W becomes about 9 to 16
and fell below 10 in 1 of 6 salts; or (b) write into s6 that a bank comparator may make only one guess in total, and say
why the analogy claim is then weaker than the correspondence claim.

**Disposition: bars added in code (option (a)); the design decision stays with the designer or owner.**
- **Reproduced exactly.** On the reviewer's six seeds my build gives the same clusters (24, 22, 23, 26, 25, 19), the
  same `FLAG_ANCHOR` W (24, 21, 22, 26, 25, 18) and the same rule W (15, 12, 11, 13, 16, 9).
- **What I registered.** The same one-guess family for both bank kinds. Each makes ONE guess per candidate and ONE
  check. None searches.
  - `DEGREE_GUESS_THEN_CHECK`: no node anchored; sort by (in-degree, out-degree, rank). The reviewer's rule.
  - `WHOLE_ANCHOR_GUESS_THEN_CHECK`: the declared whole mapped to the declared whole first. The reviewer's optional
    form. On their seeds it gives W 17, 12, 14, 14, 16, 13 (their "12 to 17").
  - `FLAG_ANCHOR_GUESS_THEN_CHECK`: the whole and both participants mapped first. This mirrors the correspondence bar
    of the same name. Under fresh flags it is weak (W 19 to 28); it costs nothing.
  - For analogy each rule answers the first same-degree other-domain candidate, in alias order, whose one guess passes
    the check, else NO_MATCH.
  - For correspondence I added only `WHOLE_ANCHOR_GUESS_THEN_CHECK`, to complete the same family. There it was lower
    than the degree guess in 1 of 16 salts, by 1 cluster (seed `REVIEWER-a5`: 33 against 34).
- **Why option (a) in code.** It only adds bars. It can never let a claim pass that would fail without it. If the
  designer chooses (b), the three analogy bars are removed from `ANALOGY_COMPARATORS` in one line, before the salt.
- **Option (b) measured, for the owner's choice.** "One guess in total" (check only the first same-degree
  other-domain candidate) has W 18 / 23.0 / 27 over 21 salts, about the same as `FLAG_ANCHOR`. So under (b) the
  analogy claim would only show "beats a rule that makes one guess in total". A rule that checks each same-degree
  candidate once would still pass it. That is the weakness the reviewer named.
- **Where.** `hset2_build.py`: `GUESS_ANCHORS`, `one_guess`, `analogy_payloads`, `correspondence_payloads`,
  `A2_BARS`. Tests: `test_analogy_comparators` (a partner that one guess finds; a partner numbered so that the one
  degree guess breaks an edge, which the rules must then miss), `test_correspondence_comparators`.

### F2. BLOCKER: a rule that learns nothing passes `REACH_3_STEP_TRANSFER_6`

**Reviewer's summary.** "A rule that learns nothing passes REACH_3_STEP_TRANSFER_6 on both TEST reach cells in 6 of 6
throwaway salts. It never follows a path longer than 2 steps. It uses a count of roots plus a fixed rank fallback."

**Reviewer's scenario.** Answer DIRECT if the part is a child of the whole. Otherwise use two-hop. Otherwise, if the
shape has exactly one root (read off the joint degree list), answer VIA the lowest-rank child (first-child rule) or VIA
the lowest-rank parent of the part (BFS rule). Otherwise answer ABSENT. It works because balanced cells can only take
ABSENT clusters from multi-root shapes: in a single-root shape every node is reachable. On the same 6 salts:
REACH_FIRST_DIRECT two-hop W = 33, 37, 33, 30, 34, 34 and this rule W = 16, 20, 14, 13, 19, 19; REACH_BFS two-hop
W = 33, 38, 32, 27, 36, 35 and this rule W = 11, 16, 9, 8, 15, 12. As a model against two-hop, b = 15 to 23 and c = 0.
It passes every 3-step bar in 12 of 12 cell-runs; worst p 7.7e-05, against DEGREE_RULE. The same class of problem as
review M4.

**Reviewer's fix.** A design decision before the salt: (a) register a `SINGLE_ROOT_FALLBACK` bar for the 3-step claim
in both rule variants (the BFS 3-step W fell below 10 in 2 of 6 salts, so tell the owner the claim will often read
`NOT_TESTABLE`); or (b) re-scope and rename the claim so it no longer says it shows 3-step path following.

**Disposition: bars added in code (option (a)); the design decision stays with the designer or owner.**
- **Reproduced exactly.** On the reviewer's six seeds: two-hop W 33, 37, 33, 30, 34, 34 and 33, 38, 32, 27, 36, 35;
  the rule W 16, 20, 14, 13, 19, 19 and 11, 16, 9, 8, 15, 12.
- **What I registered.**
  - `SINGLE_ROOT_FALLBACK`: the reviewer's rule, in both rule variants. It is a bar of both reach claims.
  - `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP`: the same fallback after the three-hop answer. **The reviewers did not ask
    for this one.** The 4-step claim has the same gap one step deeper: this rule drops the 4-step W from 2 to 12 (three-hop
    alone) to 0 to 5. Like three-hop, it is **not** a bar of the 3-step claim, because it follows a 3-step path.
  - The build now prints, per reach cell, the primary clusters by state and by root count
    (`primary_by_state_single_root_shape`). This shows the leak the rule uses.
- **Option (b) measured, for the owner's choice.** Without the fallback, the binding 3-step bar stays two-hop:
  W 25 to 40 (first-child) and 25 to 43 (BFS) over 21 salts. The claim would then be testable, but its name must not
  say it shows 3-step path following.
- **Where.** `hset2_build.py`: `single_root_fallback_payload`, `extra_reach_payloads`, `BUILT_ON_THREE_HOP`,
  `summarise_reach_cell`. Test: `test_single_root_fallback_rules` (one root, two roots, the BFS lowest-rank parent that
  is not on the path, and the claim's bar lists).

### F3. MINOR: DEV decoys come from the whole DEV side

**Reviewer.** DEV_6 decoys and NO_MATCH targets are drawn from the whole DEV side (DEV_NEW_6 plus DEV_DECOYS_6). Design
s5.4 says "using DEV_DECOYS_6". One DEV_NEW_6 focus can serve as another focus's decoy. Everything involved is public,
so custody is not affected. The counts match the review (27 analogy foci in 18 groups; 52 correspondence foci in 35
groups). Fix: confirm the reading in the design or plan, or restrict the pool to DEV_DECOYS_6 and re-print the DEV
counts.

**Disposition: reading kept; the owner should confirm it.** Reasons:
- "DEV_6 items follow the same recipes". The TEST recipe takes decoys from the whole TEST side, other TEST foci
  included (s5.2: "in its degree group on the TEST side"). The whole DEV side is the exact mirror.
- The delta review's own DEV counts (27 foci, 18 groups; 52) were made this way.
- A1 D3 (fillers from `DEV_DECOYS_6`) is followed as written.
- **Both readings, counted from the stage-0 files:** whole DEV side (built): analogy **27 foci in 18 groups**,
  correspondence **52 foci in 35 groups**. `DEV_DECOYS_6` only: analogy **22 foci in 16 groups**, correspondence
  **43 foci in 31 groups**.
- The proposed A2 text below states the reading so the design says it.

### F4. MINOR: reach packets keep the frozen 64-world bank unrelabelled

**Reviewer.** Only the focus is relabelled (builder choice 12). Helm's reader reads only the focus world for reach
(`pointer_inputs`: `WORLD_CHOICE_KINDS` excludes reach), so there is no effect on the model or any comparator. It
differs from the letter of s5. Fix: add one line saying s5's relabel-every-world rule applies to bank kinds.

**Disposition: written into the plan** (`BUILDER_REPORT_HSET2.md`, choice 12) **and into proposed A2.** No code change.

### F5. MINOR: two printed custody checks cannot fail

**Reviewer.** `derive()` sets WITHHELD_5 by a formula and `check_withheld_5` then asserts the same formula. The printed
`public_excluded_in_test_new_5: 0` and `withheld_excludes_dev_test_public: True` are constants. The real guards work
(`CUSTODY_BREACH`, the 6-node disjointness exit). Fix: compute the printed values from the sets, or label them.

**Disposition: fixed.**
- New `disjointness_measured` counts every printed value from the sets (for example `len(set(test5) & excluded)`).
  Its label says the build exits before the print if a required value fails.
- `check_withheld_5` now checks WITHHELD_5 as a partition (it meets none of DEV_NEW_5, TEST_NEW_5 and PUBLIC_EXCLUDED,
  and the four together cover all 267 classes), not by the same formula. Its docstring says honestly that in the
  build it guards only against a later edit.
- The 6-node exit also checks DEV side against TEST side and DEV_NEW_6 on the DEV side.
- Tests: `test_disjointness_is_counted_not_constant` (a hand-made breach shows as non-zero counts); the end-to-end test
  requires every required count to be 0.

### F6 and F8. MINOR: an uncaught exception in real mode could publish TEST details

**Reviewer (F6).** Per-item errors are cut to their type for secret splits, but an exception outside that handling is
not (for example a `KeyError` on a class key in `derive()`, or an `AssertionError`). Its message would go into
`out/build.log`, which the machine uploads with the public results. Fix: in real mode wrap `main()`; the full traceback
only to `--out-sealed`; only the exception type to the public log.

**Reviewer (F8).** The same gap, seen from the job side: the build's stderr goes to `out/build.log`, whose last 40 lines
go into `job.log` and `progress.log`. No current code path was found that leaks. A hygiene gap, not an observed leak.

**Disposition: fixed.**
- `main()` now parses the arguments and calls `_run()`. In real mode any exception other than the build's own
  `SystemExit` refusal codes is caught. Its full traceback is written to `--out-sealed/build_traceback.txt`. The only
  public text is `BUILD_FAILED_UNCAUGHT: <type> (full traceback written to the sealed output only)`.
- The build's own refusal messages were checked by hand: none names a class, item or world; they print counts, file
  names and fixed codes.
- `watch.py` already copies every file in `sealed_out/` (such as `build_traceback.txt`) to the archive only.
- Throwaway mode is not wrapped, on purpose: nothing in it is secret, and full tracebacks help debugging.
- Test: `test_sealed_mode_hides_uncaught_exception_text` (a raised `KeyError` carrying a class-key-like string: the
  public message holds only the type; the sealed traceback holds the text; refusals pass through unchanged).

### F7. MINOR: the required pre-launch commit breaks two passing tests

**Reviewer.** Committing `HSET2_SALT_SHA256` and `EXPECTED_TEST5_SHAPES_DIGEST` (JOB_LIMITS steps 2 and 3) makes
`test_real_mode_refusals` and `test_launcher_limits_and_pins` fail: they assert the pins are None, and the first refusal
case would reach `pathlib.Path('x').read_text()` and raise `FileNotFoundError`. So the coordinator would commit red
tests or edit tests at launch time without review. Fix: make both tests work either way; with the pin set, use a
throwaway 64-hex salt file and assert the refusal; allow None or 64-hex; make a missing or unreadable salt file a clean
`REFUSED:`.

**Disposition: fixed.**
- `resolve_salts` turns a missing or unreadable salt file into `REFUSED: the <name> salt file cannot be read (<type>)`.
  It also refuses an `--expect-test5-shapes-digest` that is not 64 lowercase hex characters.
- `test_real_mode_refusals` writes a throwaway 64-hex salt file into `tmp_path`. If the real pin is None it checks the
  "not committed yet" refusal. In every case it then sets a THROWAWAY pin (monkeypatch) and checks the wrong-salt,
  missing-file, bad-digest and missing-argument refusals. No real salt is read.
- `test_launcher_limits_and_pins` accepts each pin as None or 64 hex (`HSET2_SALT_SHA256`,
  `EXPECTED_TEST5_SHAPES_DIGEST`, and the new `UV_TARBALL_SHA256`).

### F9. MINOR: unpinned third-party code runs as root while both salts are on disk

**Reviewer.** The bundle, with `sealed/salt_hset1a.hex` and `sealed/salt_hset2.hex`, is extracted first. Then
`curl https://astral.sh/uv/install.sh | sh` and `uv python install 3.14` run with no pinned version and no checksum.
A compromised installer or Python download could read the salts and send them out. Inherited from HSET-1A and HSET-1B.
Fix: pin the uv release and check its sha256; pin the exact Python patch version (3.14.0) and check the download's
sha256; record both in `env.txt` and the anchors; optionally delete `pkg/sealed` after the build reads the salts.

**Disposition: fixed, with one pin left for the coordinator.**
- **Order.** The machine now installs and checks its tools **before** it downloads the bundle. No salt is on the disk
  while any third-party installer runs.
- **uv.** No install script. The machine downloads the uv release tarball for a pinned version (`UV_VERSION = "0.12.7"`,
  the uv the laptop has) straight from its GitHub release, and checks it against `UV_TARBALL_SHA256`. It then checks
  that `uv --version` reports that version.
- **Python.** `PYTHON_VERSION = "3.14.0"` (the laptop tests used 3.14.0). The machine checks the venv reports exactly
  that. uv checks the Python download against the checksums listed inside that uv release. **I did not verify that uv
  behaviour myself** on the machine; the recorded hashes below make any change visible afterwards.
- **Recorded.** `env.txt` records the uv version, the tarball sha256 (and its pin), the uv binary sha256, the Python
  binary path and its sha256. The launcher's `anchors.json` records the tool versions and the pin.
- **Salts removed.** `pkg/sealed` is deleted right after the build exits, and again in the exit handler.
- **Script size checked.** The longer machine script, rendered with fake links, is 8,930 bytes with 650-character
  links and 12,930 with 1,650, under the 16,000-byte user-data limit that `launch.py` enforces.
- **Left for the coordinator.** `UV_TARBALL_SHA256` is None. I did not download anything to get it (a download needs the
  owner's permission, and it is a launch step). The launcher refuses while it is None. JOB_LIMITS.md says where to get
  it.
- **Not changed.** Outbound traffic stays open during the build: the machine must upload its results through the
  presigned links. The build interpreter still comes from the internet, now pinned and hash-checked through uv.

### F10. MINOR: some real-mode code paths run for the first time in the paid build

**Reviewer.** The trained-answer-state re-measurement (158 frozen-checker targets) runs only in real mode; neither the
e2e test nor the AWS smoke runs it. The TEST_NEW_5 digest check runs only after every item is built. A defect there
would stop the paid run late and spend the one-launch record. Fix: run the re-measurement in throwaway mode too, at
least in the AWS smoke; move the digest check to right after `split_five`.

**Disposition: fixed.**
- New flag `--remeasure-trained-states` runs the re-measurement in throwaway mode. The AWS smoke passes it. Real mode
  always runs it.
- The re-measurement now runs **first**, right after the bank check and before stage 0 and the splits. It reads no
  salt.
- `derive()` takes `expect_test5_digest` and checks it right after `split_five`, before any item is built.
- Checked: `test_trained_answer_states_remeasured` (slow group, 95.56 s: 70 MATCH and 88 MAPPING, equal to the pinned
  record); a command-line throwaway run with the flag (re-measured, equal; `build_ok`);
  `test_test5_digest_is_checked_before_any_item_is_built` (a wrong digest stops `derive` with no item built; the right
  one passes).

### F11. MINOR: throwaway outputs look like DEV feedback but hold forbidden 5-node classes

**Reviewer.** Throwaway runs build DEV_NEW_5 items from a throwaway 5-node split. About 3 in 4 of those "DEV" classes
are real TEST_NEW_5 or WITHHELD_5 classes, which the design forbids to all development. The files carry the real names
(`HSET2_CELLS_PUBLIC.json`) and the role `DEVELOPMENT_FEEDBACK`. `--out-public` is not refused inside a git work tree.
Fix: name the outputs `THROWAWAY_*` and set every cell role to `THROWAWAY_NOT_DEV`; refuse `--out-public` inside a git
tree in throwaway mode; or leave DEV_NEW_5 cells out. The owner decides about the existing scratchpad copies; do not
delete them.

**Disposition: fixed.**
- Throwaway outputs are now `THROWAWAY_HSET2_CELLS_NOT_DEV.json`, `THROWAWAY_HSET2_BUILD_SUMMARY.json` and
  `THROWAWAY_HSET2_SEALED_TEST.json`. Every cell's role is `THROWAWAY_NOT_DEV`. The summary carries a
  `throwaway_warning`.
- Throwaway mode refuses `--out-public` inside a git work tree (it already refused `--out-sealed` there).
- Real-mode names and roles are unchanged.
- **Existing copies, for the owner (not opened, not deleted).** Old throwaway outputs with the real-looking names sit in
  the session scratchpad, in these folders: `e2e_an/`, `e2e_co/`, `run1/`, `t_analogy/`, `t_correspondence/` (each has
  `public/HSET2_CELLS_PUBLIC.json`, `public/HSET2_BUILD_SUMMARY.json` and `sealed_throwaway/HSET2_SEALED_TEST.json`).
  The scratchpad is `C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/`.
  Nothing from them is committed.

## 2. Proposed Amendment A2 (the builder's text; NOT agreed)

The designer or the owner accepts this, edits it, or chooses option (b) of F1 and F2, **before the HSET-2 salt is
made**. The code already follows this text. Every bar it adds only makes a claim harder to pass.

- **s6, reach, add:** `SINGLE_ROOT_FALLBACK` (DIRECT if the part is a child of the whole; else the two-hop answer; else,
  if the shape has exactly one root, VIA the lowest-rank child of the whole under the first-child rule, or VIA the
  lowest-rank parent of the part under the BFS rule; else ABSENT) and `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP` (the same,
  with the three-hop answer in place of two-hop).
- **s6, analogy, add:** `DEGREE_GUESS_THEN_CHECK`, `WHOLE_ANCHOR_GUESS_THEN_CHECK`, `FLAG_ANCHOR_GUESS_THEN_CHECK`. For
  each same-degree other-domain candidate, in alias order: one guess (none anchored / the declared whole anchored / the
  whole and both participants anchored; the other nodes paired after sorting by (in-degree, out-degree, rank)), then one
  check of every edge. Answer the first candidate that passes; else NO_MATCH.
- **s6, correspondence, add:** `WHOLE_ANCHOR_GUESS_THEN_CHECK` (the declared whole mapped first, then guess by degree,
  then check).
- **s6, "The line", replace with:** "A comparator may make one guess and check it. In a bank question it may do this
  once for each candidate that passes the cheap degree test, and answer the first that passes. It may not search. Exact
  search is the ceiling."
- **s7.1:** `REACH_3_STEP_TRANSFER_6` bars = every registered reach comparator **except the two built on three-hop**
  (`THREE_HOP_FIRST_CHILD`, `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP`). `REACH_4_STEP_TRANSFER_6` bars = all of them.
- **s5, presentations, add:** "The relabel-every-world rule applies to the bank kinds (analogy, correspondence).
  Reach, parts and edge-account packets keep the frozen 64-world training bank unchanged, as HSET-1A and HSET-1B did.
  Helm's reader reads only the focus world for those kinds, and only the focus is relabelled." (F4)
- **s5.4, add:** "DEV_6 decoys and NO_MATCH targets come from the focus's degree group on the whole DEV side
  (DEV_NEW_6 and DEV_DECOYS_6), as TEST items take them from the whole TEST side. Fillers come from DEV_DECOYS_6
  (A1 D3)." (F3; the owner confirms, or asks for `DEV_DECOYS_6` only: 22 and 43 DEV foci instead of 27 and 52.)
- **Tell the owner before the salt:** the numbers of section 3.

## 3. What the owner must hear now (throwaway salts only)

**How measured.** The builder's own `derive` and comparators through `hset2_throwaway_ranges.fast_rows`, which compares
each comparator directly with the independent gold. The real build requires checker v2 to agree with exactly that on
every packet. I checked the agreement again for the new bars (section 4).
- Seeds for analogy and reach (21): `REVIEWER-a5`, `-a7`, `-a8`, `-a9`, `-a12`, `-a16` (the reviewer's), `tiny-9` to
  `tiny-19` without `tiny-13`, and `reach-4`, `-5`, `-6`, `-7`, `-9`. Each seed gives two throwaway salts by the
  builder's rule. Seeds `reach-0` to `reach-3` and `reach-8` were refused with `CUSTODY_BREACH`: their throwaway
  TEST_NEW_5 held a PUBLIC_EXCLUDED class, which the build correctly refuses.
- Seeds for correspondence (16): the same without the `reach-*` seeds.
- min / mean / max over seeds.

| Cell and claim | Before A2 (binding bar: W) | With A2 (binding bar: W) | Can carry a claim with A2 |
|---|---|---|---|
| `TEST_NEW_6/ANALOGY` | `FLAG_ANCHOR`: 17 / 23.0 / 27 | `DEGREE_GUESS_THEN_CHECK`: **9 / 13.9 / 19** | **19 of 21** (W 9 in `REVIEWER-a16` and `reach-9`) |
| `TEST_NEW_6/REACH_FIRST_DIRECT`, 3-step | two-hop: 25 / 32.5 / 40 | `SINGLE_ROOT_FALLBACK`: **9 / 16.0 / 22** | 20 of 21 (W 9 in `reach-5`) |
| `TEST_NEW_6/REACH_BFS`, 3-step | two-hop: 25 / 33.5 / 43 | `SINGLE_ROOT_FALLBACK`: **6 / 11.4 / 20** | **14 of 21** |
| `REACH_3_STEP_TRANSFER_6` (both cells) | testable 21 of 21 | | **14 of 21** |
| Both reach cells, 4-step | three-hop: 2 / 7.1 / 11 and 2 / 7.1 / 12 | `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP`: **0 / 2.0 / 5** and **0 / 1.6 / 4** | **0 of 21** |
| `TEST_NEW_6/CORRESPONDENCE` | `DEGREE_GUESS_THEN_CHECK`: 19 / 28.5 / 34 | the same; `WHOLE_ANCHOR_...` is 1 lower in 1 of 16 | 16 of 16 |
| `TEST_NEW_5/CORRESPONDENCE` | `DEGREE_GUESS_THEN_CHECK`: 14 / 20.8 / 26 | the same (`WHOLE_ANCHOR_...` 19 / 25.9 / 32, never lower) | 16 of 16 |

More detail:
- **Analogy.** Clusters 19 / 24.0 / 29; degree groups 15 / 17.0 / 20. W of the other A2 bars: whole-anchored
  10 / 15.9 / 21; flag-anchored 19 / 23.3 / 28. The distractor half's binding W: 2 / 6.1 / 10; the other half's:
  5 / 7.7 / 11 (diagnostic only, A1 D5).
- **Reach, 3-step.** Distinct shapes behind the binding W: 8 / 12.9 / 18 (first-child), 6 / 8.8 / 13 (BFS). Primary
  clusters per state k: 95 / 110.0 / 122 and 102 / 121.3 / 138.
- **Reach, 4-step.** Before A2 this claim could carry in 3 of 30 throwaway salts (the earlier report), and in 4 of
  these 21 (three-hop W at least 10 in both cells: `REVIEWER-a7`, `tiny-10`, `tiny-12`, `tiny-16`). With A2 it could
  carry in 0 of 21. It stays registered and reported, and is never dropped.
- **DEV (public, the same in every seed).** Analogy: 27 foci, 18 groups, binding W **15** (`DEGREE_GUESS_THEN_CHECK`;
  it was 26 under `FLAG_ANCHOR`). Reach first-child: 3-step W **23**, 4-step W **2**. Reach BFS: 3-step W **14**,
  4-step W **1**. Correspondence-6: 52 foci, W 32 (whole-anchored 39).

**What this means, in plain words.**
- A model can now pass the analogy claim only by beating a rule that tries one degree-sorted guess on every candidate.
  In about 1 salt in 10 the cell will have too few clusters where that rule fails, and the claim reads `NOT_TESTABLE`.
- The 3-step reach claim will read `NOT_TESTABLE` about 1 time in 3, mostly because the BFS cell leaves too few
  clusters where the fallback rule fails.
- The 4-step reach claim will read `NOT_TESTABLE`.
- None of these numbers is about Helm. They say how much room the test leaves above the cheap rules.

## 4. Checks run by the builder

- **Tests: 24 of 24 pass.** Fast group 21 passed (49.11 s; again after later edits: 130.84 s, and on the final files
  110.50 s, the laptop at 100% CPU from other programs). End-to-end group 2 passed (160.91 s). Slow group 1 passed
  (95.56 s). One more end-to-end run on the final files stopped at my 290 s time limit because of that load; it did
  not fail. The only builder change after the passing end-to-end run is whitespace in two lines; the file's syntax tree
  is identical with and without it (checked).
- **The process pool path, run locally for the first time.** A command-line throwaway build with `--processes 2`
  (`--limit-foci 1`, seed `tiny-9`): `build_ok`, 68 items, evaluation 78.7 s, 126.0 s in all. One worker holds about
  81 MB.
- **The smoke's re-measurement flag through the command line** (`--only correspondence --limit-foci 1
  --remeasure-trained-states`): `build_ok`; re-measured and equal (88 MAPPING).
- **Fast path against checker v2, including every new bar.** Analogy: 36 items, 972 verdicts, 0 disagreements.
  Correspondence: 64 items, 384 verdicts, 0 disagreements. Reach: 5 items, 55 verdicts, 0 disagreements (only 5,
  because reach packets took 5 to 24 s each on the loaded laptop today). The end-to-end test also requires checker v2 to
  agree with direct comparison on every item of the tiny build, new bars included.
- `pyflakes` is clean on all changed Python files. The machine script passes `bash -n`.
- **Not done.** No new adversarial search for further cheap rules. The two reviewers' search was not exhaustive, and
  neither is mine. A fresh review of the fixes is still needed before any paid run (design s9 step 1).

## 5. Open for the owner or designer (decisions the builder does not make)

1. **Amendment A2**: accept, edit, or choose option (b) of F1 and/or F2. Before the salt is made.
2. **The DEV decoy pool reading** (F3): whole DEV side (built) or `DEV_DECOYS_6` only.
3. **The old throwaway copies** in the scratchpad (F11): keep or remove. The builder deleted nothing.
4. **`UV_TARBALL_SHA256`** (F9): the coordinator fills it in before launch; the launcher refuses until then.

## EXPOSURE (every file outside my working copy that I opened, this session)

- **The pinned CNCM tree `785c9bd1`** (branch `claude/helm-builder-continuation-20260923`), written from git objects by
  `launch.py --materialize-tree` into a new folder of the session scratchpad (`hset2_fix/tree/`, 1,186 files, tree digest `fe2eaa17...`). The builder, tests and scratch
  scripts import code from it and load the public course, the tokenizer and the development material through the
  frozen loaders. I did not open any file of it by hand except by `grep` of `typed_teaching/source.py` for
  "participants" and "declared_whole" (3 lines). The tree also holds `records/typed_course_001/checks_002/private_targets.json`;
  neither I nor my programs opened it.
- **My scratch scripts and their outputs** in `hset2_fix/` of the scratchpad: `measure_a2.py`,
  `fastpath_vs_checker.py`, the `m_*.json` and `r_*.json` range files, and throwaway build outputs (`cli_pool/`,
  `cli_remeasure/`, pytest folders `pt_*`). All made with throwaway salts. Not committed.
- **Directory listings only** (names and sizes, not contents) of the session scratchpad. They showed other agents'
  files and the old throwaway output folders named in F11. I did not open them.
- **Process list and memory** of the laptop (PowerShell `Get-Process`, free memory), to explain slow timings.
- **Not opened:** any `*_eval.jsonl`; any sealed file or folder except my own throwaway outputs; anything under
  `D:/tksCAS-archive/`; any `salt.hex`; S3 or AWS; the meta1 budget ledger; any `results/` or `results_attempt1/`
  folder; Claude transcripts. No real salt was used. Nothing was downloaded.

## Verification of 1520e17cf7972f02578ceb3c255de9cae1546d44 (fresh verifier; `CLAUDE_BUILT_CLAUDE_CHECKED`)

**Who and what.** A fresh verifier: a Claude sub-agent that did not write the build or its fixes. Claude is both the
temporary builder and the checker while Codex is away, so this is not an outside custodian. I read the diff from
`853e645d` to `1520e17c`, re-ran the tests and one throwaway build, and looked for close cousins of the two BLOCKER
rules. No model was loaded. No real salt was used. Every number below comes from THROWAWAY salts made from public
strings. Nothing ran on AWS.

**Verdict: `CHANGES_REQUIRED`.**
- F1 (analogy) is fixed correctly. As far as my checks reach, it is also complete.
- F2 (reach) is fixed as the reviewer asked, but it is not complete. A close cousin of the same rule still passes
  `REACH_3_STEP_TRANSFER_6` (finding V-1 below). It is the same class of problem, so it stays a BLOCKER until the
  designer or owner decides it, before the salt is made.
- The nine MINOR fixes hold. I found no new BLOCKER or MAJOR problem in the code changes.

### V.1 What I re-ran

- **The pinned tree.** Written again by `launch.py --materialize-tree` into my scratchpad: 1,186 files, tree digest
  `fe2eaa174b6d7265bcb78de25a13b6898a158ee808bfaf87a419c3ff10190db6`. This is the same digest the builder got.
- **Tests, one group at a time: 24 of 24 pass.** Fast group: 21 passed (35.96 s). End-to-end group: 2 passed (147.25 s).
  Slow group: 1 passed (91.03 s).
- **One command-line throwaway build.** Seed `VERIFIER-1520-a1`, `--limit-foci 1 --processes 2`.
  - `build_ok: true`, 72 items, every problem count 0. Evaluation 79.8 s; 124.4 s in all.
  - The outputs are `THROWAWAY_HSET2_BUILD_SUMMARY.json`, `THROWAWAY_HSET2_CELLS_NOT_DEV.json` and
    `THROWAWAY_HSET2_SEALED_TEST.json`. All 15 cells have the role `THROWAWAY_NOT_DEV`.
  - Every printed disjointness count is 0.
  - `registered_comparators_digest` is `1a233f311ac4585149600a7812748aa33ac27253640db22c8931dcfae0f8de17`. The 3-step
    reach bars leave out exactly `THREE_HOP_FIRST_CHILD` and `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP`.
- **The builder's section 3 numbers, measured again** on the same 21 seeds, with the builder's own `derive`,
  `fast_rows` and cell summaries (imported, not copied):
  - Analogy: binding W 9 / 13.9 / 19 (`DEGREE_GUESS_THEN_CHECK`); testable in 19 of 21. The same as the builder's.
  - Reach 3-step, `SINGLE_ROOT_FALLBACK` W: first-child 9 / 16.0 / 22 (20 of 21), BFS 6 / 11.4 / 20 (14 of 21). The
    claim is testable in 14 of 21. The same as the builder's.
  - On the reviewer's six seeds, `SINGLE_ROOT_FALLBACK` W is 16, 20, 14, 13, 19, 19 (first-child) and 11, 16, 9, 8,
    15, 12 (BFS). These are exactly the reviewer's numbers.
  - Not measured again by me: the 4-step numbers, correspondence, and DEV.

### V.2 F1 (analogy): fixed

- The reviewer's rule is registered as `DEGREE_GUESS_THEN_CHECK`, with a whole-anchored form and a flag-anchored form.
- `one_guess` takes `participants[0]` as the declared whole. `source.py` at `785c9bd1` requires exactly that
  (`TYPED_SOURCE_WHOLE_REF`).
- **Close cousins**, each treated as a model against every registered analogy bar, over 21 throwaway salts:

| Cousin | Guesses per candidate | Passes the claim | W if it were a bar |
|---|---|---|---|
| degree sort, ties broken by reverse rank | 1 (inside the line) | 0 of 21 | 9 / 13.9 / 19 (it makes the same pairs as the registered rule) |
| degree sort, ties broken by the declared flags, then rank | 1 (inside the line) | 0 of 21 | 7 / 12.5 / 17 |
| the degree guess OR the whole-anchored guess | 2 (outside the line) | 0 of 21 | 8 / 13.6 / 19 |
| any of the three registered guesses | 3 (outside the line) | 0 of 21 | 8 / 13.3 / 19 |

- **Note N1 (not a blocker).** The flags tie-break gives the same pairs in both presentations, because the flags do not
  change between them. So it does not pay the two-presentation penalty. It came closest to passing: b = 9, c = 2
  (p 0.033) on `REVIEWER-a5`, and b = 5, c = 0 (p 0.031) on `reach-7`, both against `DEGREE_GUESS_THEN_CHECK`. The
  designer may register it as a bar at no cost. The binding W would then fall a little.

### V.3 F2 (reach): the named rule is closed, but a cousin still passes

**Finding V-1 (BLOCKER).** A rule that learns nothing still passes `REACH_3_STEP_TRANSFER_6` after A2. It never follows
an edge more than 2 steps from the whole.

**The rule.** I call it `FRONTIER_FALLBACK`.
- Take the registered two-hop answer: DIRECT if the part is a child of the whole; else VIA a child of the whole with an
  arrow to the part.
- If that answer is ABSENT: answer VIA when (i) some node exactly two steps from the whole has at least one child, and
  (ii) the part has at least one parent. Otherwise answer ABSENT.
- The via. First-child rule: the whole's child with the most children (ties: lowest rank). BFS rule: among the part's
  parents that have a parent themselves, the one with the most parents (ties: lowest rank).
- It reads node degrees (the joint degree list) and the part's parents, as `SINGLE_ROOT_FALLBACK` already does. It
  never looks at where a third edge goes.

**Measured** (throwaway salts; the builder's own `derive`, `fast_rows` and `summarise_reach_cell`):
- I fixed the rule after looking at one seed (`REVIEWER-a5`). The other 20 seeds were held out.
- It passes both TEST reach cells in 6 of the reviewer's 6 seeds. It passes in 16 of the builder's 21 seeds (which
  include the reviewer's six).
- In the 14 salts where the 3-step claim is testable at all, it passes in 11. The worst p among its passes is 0.0078.
- Against `SINGLE_ROOT_FALLBACK`: b = 5 to 22, c = 0 to 6.
- If it were registered as a bar, its W would be 1 / 3.4 / 6 (first-child) and 0 / 1.1 / 2 (BFS). The 3-step claim
  would then read `NOT_TESTABLE` in 21 of 21 salts.
- Checker v2, on the real packets, agreed with the direct comparison on 24 of 24 items, for this rule and for
  `SINGLE_ROOT_FALLBACK` (seed `REVIEWER-a5`; both presentations of 6 clusters per cell where `SINGLE_ROOT_FALLBACK`
  is wrong).

**Why it works.**
- Most clusters that `SINGLE_ROOT_FALLBACK` gets wrong are VIA clusters in shapes with two or more roots. On
  `REVIEWER-a5` that is 10 of its 16 first-child errors and 10 of its 11 BFS errors (in each cell, 9 at distance 3 and
  1 at distance 4). There the whole reaches the part in 3 steps, but the root count says nothing.
- The question "does the whole's 2-step frontier still have outgoing edges?" separates those clusters from the ABSENT
  ones.
- Two controls, on 5 of the reviewer's seeds:
  - The root-count state with this rule's via choice fails in 5 of 5. So the frontier test is what matters.
  - A strict cousin that never looks at a 2-step node (it asks only whether some child of the whole has a child)
    passes the BFS cell in 4 of 5 but fails the first-child cell in 5 of 5. So it does not pass the claim.

**What the finding hinges on.** The rule reads whether a node two steps out has any child. So it knows that a third
step exists somewhere. It does not know where that step goes, and it never checks that it reaches the part. If the
designer counts this as "following a 3-step path", the finding falls away. The claim text should then say so.

**Fix.** This is a design decision, made before the salt. It is not a code fix alone. Choose one:
- (a) Register `FRONTIER_FALLBACK` (the text above) as a bar of `REACH_3_STEP_TRANSFER_6`. Tell the owner the claim
  will then read `NOT_TESTABLE` in about every salt (W 0 to 6).
- (b) Declare `REACH_3_STEP_TRANSFER_6` `NOT_TESTABLE` now, as the 5-node reach claims are. Or rename it to what it can
  show (it beats two-hop and root-count rules), and write that a 2-step frontier rule would also pass it.
- (c) Change the reach cell so that the 2-step view cannot predict the state. For example, balance VIA clusters at
  distance 3 against ABSENT clusters with the same 2-step frontier. Then measure the ranges again.

**The root cause.** The bar list names single rules. Each review closes one rule, and the next cousin passes. Reach
has now shown this three times (M4, then F2, now V-1). A bar defined by a declared view would stop it: the best answer
available from the nodes within 2 steps of the whole, the part's parents, every node's joint degree and the ranks,
chosen on the cell as `BEST_FIXED_POSITION` is. That is a design change, and the designer decides it.

### V.4 The MINOR fixes hold

- **F5.** The printed disjointness is counted from the sets. In my run every count is 0.
  - Note N2 (cosmetic). Two counts, `withheld_6_meets_test_new_6` and
    `test_side_not_covered_by_test_new_6_and_withheld_6`, are 0 by construction, and no exit guards them. The label
    "the build exits before this print if a required value fails" is true for every other count.
- **F6 and F8.** Real mode wraps `_run`. Only the exception type reaches the public log (test passes).
  - The wrapper lets the build's own `SystemExit` messages through. I read every formatted one in `hset2_build.py`,
    `hset2_stage0_public.py`, `hset1a_build.py`, `hset1b_build.py`, `hset_worlds.py` and `oracle_isomorphism.py`.
    None names a class, an item or a world.
  - The imported CNCM modules (`typed_teaching`, `eval_paths`) call `sys.exit` only under `__main__`.
- **F7.** The refusal test and the launcher test pass with the pins unset. The paths that follow a committed pin run
  under a throwaway pin.
- **F9.** The machine fetches the tools, checks their hash and checks their versions before the bundle arrives.
  `pkg/sealed` is removed after the build and again in the exit handler. `UV_TARBALL_SHA256` is still None, so the
  launcher refuses; that is a pre-launch step. Not verified by me or by the builder: that uv checks the Python download.
- **F10.** The smoke passes `--remeasure-trained-states`. The slow test re-measured 70 MATCH and 88 MAPPING. `derive`
  checks the TEST_NEW_5 digest right after `split_five` (test passes).
- **F11.** Throwaway names and roles are as described. A throwaway `--out-public` inside a git work tree is refused
  (test passes).
- **F3, F4.** Owner decisions. Nothing to verify in code.

### V.5 Before the salt

1. The designer or owner decides V-1 (option a, b or c), together with the A2 decision (JOB_LIMITS step 1a).
2. Optional: register the flags tie-break as an analogy bar (N1).
3. After any change to the bars: print the ranges again, and have the change reviewed again.

### EXPOSURE (this verification)

- **The pinned CNCM tree `785c9bd1`.** Written from git objects by `launch.py --materialize-tree` into
  `verify_1520/tree/` of the session scratchpad (1,186 files, digest `fe2eaa17...`).
  - The tests, the build and my probes imported code from it. They loaded the public course, the tokenizer and the
    development material through the frozen loaders.
  - I opened no file of it by hand. I searched its `cas_meta2/typed_teaching/` and `eval_paths/` folders for
    `SystemExit`, `sys.exit` and `private_targets` (the last had no match). I searched its whole `research/` folder for
    `private_targets` (names of matching `.py` files only).
  - Neither I nor my programs opened `records/typed_course_001/checks_002/private_targets.json`. The imported packages
    never name it.
- **Git objects of commit `785c9bd1`** (branch `claude/helm-builder-continuation-20260923`), by `git show`:
  `typed_teaching/source.py` (a search for "participants" and "declared_whole", and lines 195 to 250) and
  `typed_teaching/pointer_contract.py` (a search for "private" and "load_material").
- **My scratch files** in `verify_1520/` of the session scratchpad: `probe_reach.py`, `probe_analogy.py`,
  `check_v4_checker.py`, `verification_section.md` (this text, before it was appended here), their `r_*.json`,
  `r2_*.json` and `a_*.json` outputs and logs, the pytest folders `pt_*`, and my throwaway build `cli_a1/` (including
  `sealed_throwaway/THROWAWAY_HSET2_SEALED_TEST.json`, which I made with a throwaway salt). Not committed.
- **One file under `C:/Users/wakil/.claude/projects/`.** The tool harness saved the output of my own `git diff` of
  `hset2_build.py` (`853e645d` to `1520e17c`) as `.../5e8709f4-3151-444f-939b-317c01bc3568/tool-results/b1qn7akvd.txt`,
  and I read it back. It holds only that diff. It is not a transcript. I list it because its folder is on the
  forbidden list.
- **Laptop state:** free memory and the process list (PowerShell), `python --version`, `uv --version`.
- **Not opened:** any `*_eval.jsonl`; any sealed file or folder except my own throwaway output; anything under
  `D:/tksCAS-archive/`; any `salt.hex`; S3 or AWS; the meta1 budget ledger; any `results/` or `results_attempt1/`
  folder; the builder's scratch files and the old throwaway output folders named in F11; Claude transcripts. No real
  salt was used. Nothing was downloaded.

## Conformance to Codex A2 (PROPOSED) (the temporary builder, 2026-09-24; `CLAUDE_BUILT_CLAUDE_CHECKED`)

**What this is.** The builder's throwaway measurements after this round's changes. The changes themselves are in
`BUILDER_REPORT_HSET2.md`, section "Conformance round, 2026-09-24". In short:
- Codex's proposed A2.1: the families `FIXED_POSITION_1` to `_7` and `STATUS_BY_COUNT_0` to `_8` are bars, and no bar
  is tuned on TEST any more.
- Codex's proposed A2.2 and A2.4: degree-group and shared-shape-component views, and the feasibility table.
- Finding V-1: `FRONTIER_FALLBACK` is a bar of both reach claims (switch `REGISTER_FRONTIER_FALLBACK`, on).
- Note N1: `FLAGS_TIEBREAK_GUESS_THEN_CHECK` is an analogy bar (switch `REGISTER_FLAGS_TIEBREAK_GUESS`, on).
- The bar-set digest is now `cf88cebafa9169964aff041d3c1bcb652b2067b86854befc253dd452291c78af` (it was `1a233f31...`).

**What this is not.** No independent reviewer has read this round. No model was run. Nothing here is a result about
Helm. Every salt is a THROWAWAY salt made from a public string. Codex's A2 is not agreed; the design owner decides.

**How measured.**
- `hset2_throwaway_ranges.py`: the builder's own `derive`, comparators and cell summaries, with `--only analogy`, and
  with `--only reach --splits TEST_NEW_6`. It compares each rule directly with the independent gold. Checker v2
  agreed with that direct comparison on every verdict checked this round (1,260 analogy and 288 reach verdicts,
  0 disagreements; builder report C.3).
- **Seeds: all 21 measured, none left out, none refused:** `REVIEWER-a5`, `-a7`, `-a8`, `-a9`, `-a12`, `-a16`;
  `tiny-9` to `tiny-19` without `tiny-13`; `reach-4`, `-5`, `-6`, `-7`, `-9`.
- DEV (public; the same in every seed): analogy in every run; reach once (seed `tiny-9`, `--splits DEV_NEW_6`).
- **Not measured again this round:** the correspondence cells, and the effect of the proposed T5 rule on these ranges.
- Run time, one process: analogy 28.8 s for all 21 seeds; reach 76.6 s and 81.5 s (two batches, 11 and 10 seeds).
- min / mean / max over the 21 seeds. "c / g / k" means clusters / degree groups / shared-shape components.
- **Cross-checks with earlier, separate scripts.** The new code reproduces, over the same 21 seeds:
  `DEGREE_GUESS_THEN_CHECK` W 9 / 13.9 / 19 and `SINGLE_ROOT_FALLBACK` W 9 / 16.0 / 22 and 6 / 11.4 / 20 (section 3);
  the N1 rule's W 7 / 12.5 / 17 (section V.2); `FRONTIER_FALLBACK` W 1 / 3.4 / 6 and 0 / 1.1 / 2 (section V.3).

### A. Analogy, `TEST_NEW_6/ANALOGY` (both switches on)

| Number | min / mean / max | Can carry (W >= 10) |
|---|---|---|
| Units c / g / k | 19 / 24.0 / 29; 15 / 17.0 / 20; 9 / 14.9 / 18 | components >= 10 in 20 of 21 (`tiny-18` has 9) |
| Binding W, original view | **7 / 12.2 / 16** | 17 of 21 |
| Binding W, degree-group view | **7 / 9.7 / 12** | 13 of 21 |
| Binding W, component view | **6 / 8.9 / 11** | 9 of 21 |
| The original floor (clusters, W and groups >= 10) | | **17 of 21** (19 of 21 before N1) |
| Every A2.4 floor (the confirmatory claim) | | **9 of 21** |

- **Binding bars.** `DEGREE_GUESS_THEN_CHECK` or `FLAGS_TIEBREAK_GUESS_THEN_CHECK` in every view. In the component
  view `WHOLE_ANCHOR_GUESS_THEN_CHECK` is the named binding bar in some seeds.
- **Each rule's W, original / group / component view:** N1's `FLAGS_TIEBREAK_GUESS_THEN_CHECK` 7 / 12.5 / 17,
  7 / 9.9 / 13, 6 / 9.1 / 11. `DEGREE_GUESS_THEN_CHECK` 9 / 13.9 / 19, 7 / 10.6 / 13, 6 / 9.6 / 12. `FLAG_ANCHOR`
  17 / 23.0 / 27, 14 / 16.4 / 20, 8 / 14.3 / 18.
- **The A2.1 families never bind.** Every member (`FIXED_POSITION_1` to `_7`, `FIXED_ALIAS_W0` to `W7`,
  `STATUS_BY_COUNT_0` to `_8`) is wrong on every cluster in every seed, TEST and DEV. The twin design causes this. A
  fixed position always names a world, so it fails the NO_MATCH twin. The list E has the same length in both twins
  (the profiles are equal), so a count rule gives the same kind of answer in both twins and fails one of them.
- **Why the A2.4 floors fail in 12 of 21 seeds** (the build prints each reason): the component view's binding W is
  below 10 in 12 seeds; the group view's in 8; the original view's in 4; and `tiny-18` has only 9 components.
- **Per seed, binding W original / group / component:** `REVIEWER-a5` 8/7/7, `-a7` 11/11/10, `-a8` 7/7/6, `-a9` 11/8/8,
  `-a12` 16/11/11, `-a16` 8/8/8; `tiny-9` 16/11/11, `-10` 13/12/10, `-11` 13/9/9, `-12` 12/11/10, `-14` 10/7/6,
  `-15` 12/10/9, `-16` 16/12/11, `-17` 13/10/10, `-18` 14/10/7, `-19` 12/10/8; `reach-4` 13/12/11, `-5` 12/9/8,
  `-6` 16/11/11, `-7` 14/11/8, `-9` 9/7/7.
- **If N1 were switched off** (the same runs, binding over the other bars): W 9 / 13.9 / 19 original (>= 10 in 19 of
  21), 7 / 10.6 / 13 group (14 of 21), 6 / 9.4 / 12 component (10 of 21); every A2.4 floor met in 10 of 21.
- **DEV (public):** 27 / 18 / 14 units; binding W 15 / 10 / 10 (`DEGREE_GUESS_THEN_CHECK`); the N1 rule 15 / 11 / 10.
  The A2.4 floors are met on DEV (printed only; DEV carries no claim).

### B. Reach, both TEST cells (both switches on)

| Cell and claim | Units c / g / k | Binding W original / group / component | Binding bar | Can carry |
|---|---|---|---|---|
| `REACH_FIRST_DIRECT`, 3-step | 285 / 330.1 / 366; 45 / 48.4 / 54; the same as g | **1 / 3.4 / 6; 1 / 3.3 / 6; 1 / 3.3 / 6** | `FRONTIER_FALLBACK` | 0 of 21 |
| `REACH_BFS`, 3-step | 306 / 364.0 / 414; 45 / 48.6 / 54; the same as g | **0 / 1.1 / 2; 0 / 1.0 / 2; 0 / 1.0 / 2** | `FRONTIER_FALLBACK` | 0 of 21 |
| `REACH_FIRST_DIRECT`, 4-step | as above | 0 / 1.7 / 3; 0 / 1.4 / 3; 0 / 1.4 / 3 | `FRONTIER_FALLBACK` or `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP` | 0 of 21 |
| `REACH_BFS`, 4-step | as above | 0 / 0.8 / 2; 0 / 0.6 / 2; 0 / 0.6 / 2 | the same two | 0 of 21 |

- **`REACH_3_STEP_TRANSFER_6` reads `NOT_TESTABLE` in 21 of 21 throwaway salts, in every view.** So does
  `REACH_4_STEP_TRANSFER_6`.
- For reach, components equal degree groups, because the focus is the only listed packet role (builder report,
  T2).
- **If FRONTIER were switched off** (the same runs; the binding bar is then `SINGLE_ROOT_FALLBACK` in every view):
  - 3-step, first-child: W 9 / 16.0 / 22 original (>= 10 in 20 of 21); 7 / 10.2 / 16 group (12 of 21).
  - 3-step, BFS: W 6 / 11.4 / 20 original (14 of 21); 5 / 7.4 / 10 group (1 of 21).
  - Both cells at W >= 10: original view **14 of 21** (as section 3); group view **1 of 21**; component view 1 of 21.
    For reach the group and component floors are printed, not binding (A2.4 binds them only for the confirmatory
    analogy claim).
  - 4-step: 0 of 21 in every view.
- **DEV (public, seed `tiny-9`):** first-child 357 clusters in 43 groups (= components); 3-step binding W 4 / 3 / 3
  (`FRONTIER_FALLBACK`); 4-step 2 / 2 / 2 (`SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP`). BFS 375 clusters in 43 groups;
  3-step 3 / 2 / 2; 4-step 1 / 1 / 1.

### C. The exact power grid, an excerpt

The build prints the grid for every unit count that occurs. Power here is the chance that the sign test passes, given
d units where the model and the bar differ, if the model wins each of them with probability q. The sums are exact;
they are rounded here to 4 places. This is a sensitivity calculation, not a forecast of any model.

| d | smallest winning B | q = 0.60 | q = 0.70 | q = 0.80 | q = 1.00 |
|---|---|---|---|---|---|
| 6 | none | 0 | 0 | 0 | 0 |
| 7 | 7 | 0.0280 | 0.0824 | 0.2097 | 1 |
| 10 | 10 | 0.0060 | 0.0282 | 0.1074 | 1 |
| 12 | 11 | 0.0196 | 0.0850 | 0.2749 | 1 |
| 17 | 14 | 0.0464 | 0.2019 | 0.5489 | 1 |
| 20 | 16 | 0.0510 | 0.2375 | 0.6296 | 1 |

### D. What this means, in plain words

- **Analogy.** With every bar and both added views, the confirmatory analogy claim could be tested in about 9 of 21
  throwaway salts. The limit is the component view: after grouping, there are often fewer than 10 units where the best
  cheap rule fails.
- **Even when it can be tested, the margin is thin.** With 10 informative units, a model has to win all 10. A model
  that wins each such unit with probability 0.8 would pass only about 1 time in 9 (0.1074).
- **Reach, 3 steps.** With `FRONTIER_FALLBACK` registered, the claim reads `NOT_TESTABLE` in every throwaway salt.
  Without it, the original view is testable in 14 of 21 salts, but the group view in only 1 of 21.
- **Reach, 4 steps.** `NOT_TESTABLE` in every salt and every view.
- None of these numbers is about Helm. They say how much room the test leaves above the cheap rules.

### E. Checks

- Tests: 28 run, 28 passed (fast 26 of 26, 28.06 s; end-to-end 2 of 2, 96.11 s; both on the final files). The slow
  test was not run; its code path did not change.
- Checker v2 against direct comparison, every new bar: analogy 36 items, 1,260 verdicts; reach 24 items (12 where
  `FRONTIER_FALLBACK` answers VIA), 288 verdicts; **0 disagreements**.
- `pyflakes` clean. The stage-0 files and `PUBLIC_EXCLUDED_v1.json` are unchanged (same LF sha256 as before).
- **Not done:** no new search for further cheap rules. Each review so far has found one more rule; this round only
  registered the two already named. A fresh independent review is needed before any paid run.

### EXPOSURE

The same as the builder report's EXPOSURE for this round (`BUILDER_REPORT_HSET2.md`, "Conformance round,
2026-09-24"). No real salt was used or made. Nothing was downloaded. Nothing ran on AWS.

## Review of 4c402209ef06c2a78ebabdcc801ea212c81fa1c0 (`CLAUDE_BUILT_CLAUDE_CHECKED`): `CHANGES_REQUIRED`, and the builder's dispositions

**Who.** The reviewer is a Claude sub-agent. The coordinator's workflow passed its verdict and findings to the builder.
Claude is both the temporary builder and the checker while Codex is away, so this is not an outside custodian review.
The review text was not in this file before; it is recorded below as it reached the builder. The builder (Claude, the
temporary builder) wrote every disposition and checked its own fixes. No independent reviewer has read the fixes yet.

**What this is not.** No model was loaded or run. No real salt exists, and none was made. Every number comes from
THROWAWAY salts (made from public strings) or from public files. Nothing ran on AWS. Nothing here is a result about Helm.

### R.0 The reviewer's verdict, as delivered

"The code follows Codex's proposed A2.1, A2.2 and A2.4 text and tasks T1 to T6 in almost every point I checked. No bar
was dropped, A1 is intact, and no protected detail reaches the public output. Four things still need the design
owner's decision, or a small code fix, before the HSET-2 salt is made. The most important: an unregistered no-learning
one-guess rule, cheaper than the 'one hop' the scope sentence admits, passes ANALOGY_BEYOND_DEGREE_6 in 2 of 21
throwaway salts. REACH_3_STEP_TRANSFER_6 cannot be passed by any rule: it reads NOT_TESTABLE in 21 of 21 salts."

### R.1 Short version

- **One MAJOR.** It is a design choice (a new bar, or a new claim wording). The builder does not make it. It is recorded
  as an open question, here and in the build's own output. No bar was added.
- **Three MINORs.** All three are fixed in code:
  - D1 is now one constant with one value per option.
  - The HSET-1A power grid is now computed exactly at the group and component levels.
  - Both-arm packet-route acceptance is now printed as a named check that is still required.
- **Three NOTEs.** One is fixed in code: the confirmatory claim now carries its two status words. One stays an open
  question (the reach components). One needs no change (the A2.1 families never bind).
- **Under the default settings no bar changed.** Every claim has exactly the same bars as at `4c402209`. I checked this
  by loading that commit's module beside the new one. The bar-set digest still changed, because the record now
  stores D1 as one value per option.
- **Tests:** fast group 29 of 29 passed; end-to-end group 2 of 2 passed.

| # | Severity | Finding in one line | Disposition |
|---|---|---|---|
| R1 | MAJOR | An unregistered one-guess rule (degree, whole-child, flags) passes `ANALOGY_BEYOND_DEGREE_6` in 2 of 21 throwaway salts | Design choice: open question for the design owner; recorded in the build output; no bar added |
| R2 | MINOR | `REGISTER_FRONTIER_FALLBACK = False` records "drop the bar", not D1 option (b) | Fixed: `D1_FRONTIER_DECISION` = `a` / `b_not_testable` / `b_rename` / `c` |
| R3 | MINOR | The power grid is computed only at the cluster level; tiny powers print as 0 | Fixed: exact group and component power under the HSET-1A model; 12 significant digits printed |
| R4 | MINOR | "Both-arm packet-route acceptance" is not printed and not listed as open | Fixed: `both_arm_packet_route_acceptance: NOT_YET_CHECKED`, with the check still required; open question |
| R5 | NOTE | For reach, components equal degree groups (the training bank is not a packet role) | Kept; open question for the design owner (unchanged) |
| R6 | NOTE | The A2.1 families never bind under the twin design | No change; the owner is told (below) |
| R7 | NOTE | The confirmatory claim's row has no field for `MECHANISM_GATE_OPEN` or `INFERENCE_ASSUMPTIONS_UNSUPPORTED` | Fixed: both status fields added; whether the assumptions hold stays open |

### R.2 The findings as the reviewer wrote them, with my disposition

#### R1. MAJOR: an unregistered one-guess rule passes `ANALOGY_BEYOND_DEGREE_6`

**Reviewer's summary.** "A no-learning rule that is not registered still passes ANALOGY_BEYOND_DEGREE_6 with every new
bar in place. It is the registered N1 flags tie-break guess plus one extra sort key per node: is this node a child of
the declared whole? It makes one guess per same-degree, other-domain candidate, checks it once, and never searches, so
it sits inside the design's own line. Stronger rules of the same kind pass far more often."

**Reviewer's scenario.** Throwaway salts only, with the builder's own `derive`, `fast_rows` and `summarise_bank_cell`,
each rule treated as a model against all 35 registered analogy bars.
- The rule `WHOLE_CHILD_FLAG_GUESS` sorts nodes by (in-degree, out-degree, child-of-the-declared-whole, flag position,
  rank). It passes the base claim in 2 of 21 salts: `tiny-9` (b = 9, c = 0, worst p 0.001953) and `tiny-11` (b = 9,
  c = 0, worst p 0.001953).
- In `tiny-9` it also passes the group view (B = 7, C = 0, p = 1/128) and the component view (B = 7, C = 0). `tiny-9`
  meets every A2.4 floor, so the rule would clear the bar part of `REPAIR_IMPROVES_ANALOGY_6` there.
- Sorting by distance from the declared whole passes the base claim in 7 of 21 salts.
- Sorting by the design's printed diagnostic signature (in, out, descendants, ancestors) passes in 16 of 21.
- A one-hop colour guess passes in every testable salt (17 of 17), and gets every cluster right in 19 of 21.
- Checker v2 agreed with the reviewer's direct comparison on all 36 verdicts graded on real `tiny-9` packets.
- Cost of simply registering the whole-child rule: the original floor would hold in 3 of 21 salts, and every A2.4 floor
  in 0 of 21.
- So the scope sentence ("cannot tell full structural comparison from one hop of neighbour-degree matching")
  overstates the least a passing model must do.

**Reviewer's fix.** The design owner decides, before the salt: (a) register the whole-child rule, and tell the owner the
confirmatory claim then reads NOT_TESTABLE in every throwaway salt; or (b) widen the scope sentence to say a pass may
come from a single guess keyed on degree, the declared flags and the declared whole's children or distances; or (c)
define the analogy bar by a declared view (the best one-guess ordering from a named feature set). "Nothing in the code
needs changing until that choice is made."

**Disposition: a design choice. Recorded as an open question. No bar added.**
- Adding a bar and changing the scope sentence are both design decisions. The coordinator's instruction for this round
  gives them to the design owner. The builder did not choose among (a), (b) and (c).
- **Recorded in the build's own output**, so no reader of a summary can miss it: a new field
  `open_design_question_before_the_salt` on the `ANALOGY_BEYOND_DEGREE_6` row and on the `REPAIR_IMPROVES_ANALOGY_6`
  row (constant `OPEN_ANALOGY_SCOPE_QUESTION` in `hset2_build.py`). It states the rule, the reviewer's numbers and the
  three options. It changes no bar, floor or status.
- **Not re-measured by the builder.** The reviewer's numbers above are the reviewer's. I did not write or run the
  whole-child rule.
- If the owner chooses (a), the rule can be added behind a switch, as N1's rule was, with its W printed while it is off.

#### R2. MINOR: the D1 switch could not record option (b)

**Reviewer's summary.** "Setting REGISTER_FRONTIER_FALLBACK to False records none of D1's three options. It removes
FRONTIER_FALLBACK from both reach claims' bars, but leaves REACH_3_STEP_TRANSFER_6 under its old name and able to read
testable. So the switch records only '(a) keep' or 'drop the bar'. It does not record (b) NOT_TESTABLE/renamed, as T4
asked."

**Reviewer's scenario.** Someone chooses D1 (b) and flips the constant to False. The 3-step claim then carries a claim
again in 14 of 21 throwaway salts (without FRONTIER the binding W is 9 / 16.0 / 22 for first-child and 6 / 11.4 / 20
for BFS), while a known no-learning rule that passes it (V-1) is only a printed diagnostic. That is the state V-1 calls
a BLOCKER, under the original claim name.

**Reviewer's fix.** Make False mean D1 (b), or replace the boolean with one D1 constant taking 'a' / 'b_not_testable' /
'b_rename' / 'c', where every value except 'a' changes the claim's status or name, and put it in the digest.

**Disposition: fixed, with the reviewer's second form.** `REGISTER_FRONTIER_FALLBACK` is replaced by one constant,
`D1_FRONTIER_DECISION` (default `"a"`). Each value is written in `D1_OPTIONS`, recorded in `registered_comparators()`
(with its meaning) and so in the digest.

| Value | 3-step claim | `FRONTIER_FALLBACK` | Bar-set digest (N1 on) |
|---|---|---|---|
| `a` (default) | `REACH_3_STEP_TRANSFER_6`, floor as measured | bar of both reach claims | `14be05d5a0845e52a194628974fd0bfd6763b0fc0b1e1e96dfe3dd779671edfd` |
| `b_not_testable` | `REACH_3_STEP_TRANSFER_6`, `NOT_TESTABLE` before any build, whatever its floor says; the floor is still printed (`floor_result_before_the_D1_declaration`) | bar of both reach claims | `42928c8681b59064ed5feb200a4072171c580147f7c73927c2e156bb1fd94bb9` |
| `b_rename` | renamed `REACH_BEYOND_TWO_HOP_AND_ROOT_COUNT_6` (a PROPOSED name), with a scope note that it does NOT show 3-step path following and that `FRONTIER_FALLBACK` would pass it | printed for the renamed claim as `computed_not_registered_W` (every view); bar of the 4-step claim | `f24cbbc878a08ef6a5750e3043e7898bbb23623d835926459efc3271e8a45781` |
| `c` | the build refuses before it reads anything: rebalancing needs its own amendment and code | - | - |

- An unknown value is refused too.
- **`FRONTIER_FALLBACK` stays a bar of `REACH_4_STEP_TRANSFER_6` under every value.** The old `False` took it off both
  claims. So every new value has at least the bars of the old `False`, claim by claim (checked by script).
- **Under the default, the bars did not change.** I loaded the `4c402209` module beside the new one: the analogy,
  correspondence, 3-step and 4-step bar lists are identical. The digest changed from
  `cf88cebafa9169964aff041d3c1bcb652b2067b86854befc253dd452291c78af` to
  `14be05d5a0845e52a194628974fd0bfd6763b0fc0b1e1e96dfe3dd779671edfd` because the record's shape changed (the D1 value
  and its meaning, and per-claim lists). With N1 switched off (and D1 `a`) the digest would be
  `47a7777b481a47a5b28730432744cd405878e8cf736e0ad590f2449bfea9b8e8`.
- **Checked.** `test_d1_switch_records_every_option` (every value: names, bars, digests all different, the refusals of
  `c` and of an unknown value, also through `main`). `test_d1_options_in_the_reach_cell_summary` (the reach cell
  summary under `a`, `b_not_testable` and `b_rename`, on a tiny throwaway build). Two command-line throwaway builds,
  `--only reach --limit-foci 2`, seed `tiny-9`, one with `b_not_testable` and one with `b_rename`: both `build_ok`, the
  claims table as in the table above. (At 2 foci the reach cells have no primary clusters, so every reach floor fails
  anyway; the runs check the wiring, not the numbers.)

#### R3. MINOR: the power grid at the group and component levels

**Reviewer's summary.** "A2.4 asks for the HSET-1A power grid to be recomputed separately at the cluster, group and
component levels. The build recomputes it only at the cluster level. Both other levels are labelled
NOT_IDENTIFIED_FROM_RAW_ACCURACY with no reason given."

**Reviewer's scenario.** Under HSET-1A's model (the model wins each bar-wrong cluster with probability q_win and keeps
each bar-right cluster with probability q_keep, independently), and given the bar's per-cluster results in each group
(known before any model is read), each group's and component's sign probability can be computed exactly. So the power
is identified, and A2.4's escape clause does not apply as written. Also, the exact power sums were printed only as
6-place floats, so very small powers print as 0.

**Reviewer's fix.** Add an exact calculation over units under the HSET-1A settings and print its assumptions, or write
down why that model does not identify group-sign power. Print the exact fractions, or more digits.

**Disposition: fixed.**
- **New block per view, `exact_power_under_hset1a_model`,** in every feasibility row (every cell, and each reach claim).
  For each view it uses that view's binding bar. It gives the HSET-1A settings: uniform model accuracy (bar accuracy
  +0.10, +0.20, +0.30, capped at 1, and 1.0) and never-loses fractions 0.5, 0.75, 1.0.
- **How it is computed.** Each unit's chance of a win, a loss and a tie is summed exactly over its clusters' outcomes.
  Integer arithmetic is used, with one common denominator. Then the chance of "B > C and exact tail <= 1/100" is summed
  exactly over units. The printed assumptions are in `power_assumptions` (constant `POWER_ASSUMPTIONS`).
- **One honest limit, printed.** In the group and component views a pass also needs a positive overall accuracy
  difference. This sum does not condition on it. So there the value is an **upper bound** on the pass chance. It is
  exact when q_keep = 1 (the never-loses rows: no cluster can lose, so 7 or more wins mean a positive overall
  difference). It is also exact in the original cluster view.
- **Shortcut.** If fewer than 7 units have a bar-wrong cluster, no sign test can pass (it needs at least 7 wins), and
  every value is exactly 0 (`EXACT_ZERO`).
- **Guard.** A component that would need more than 200,000 enumeration states is reported as `NOT_COMPUTED_TOO_LARGE`,
  not computed. It did not happen in any throwaway run.
- **The words `NOT_IDENTIFIED_FROM_RAW_ACCURACY` stay, with the reason.** Raw accuracy alone does not fix group signs.
  Under the HSET-1A per-cluster model it is identified, and the exact block gives it.
- **More digits.** Every exact power now also prints to 12 significant digits (`value_12_significant_digits`). The
  conditional sign-power grid gets one extra list per q, `by_discordant_count_12_significant_digits` (its value depends
  only on d and q).
- **Checked** (`test_exact_view_power_under_the_hset1a_model`):
  - the original cluster view equals HSET-1A's `power_given_bar` for every setting (to 6 places);
  - a hand count, 176/1024, for 10 never-losing groups;
  - a brute-force sum over every one of 2,048 cluster outcomes, for groups and for components, at one uniform and one
    never-loses setting. That case includes a two-group component, mixed group sizes and a power below 0.01;
  - the exact zero when fewer than 7 units can be won.

**Measured on throwaway salts** (`TEST_NEW_6/ANALOGY`, all 21 seeds of the last round, none refused; one process,
48.3 s; min / mean / max over seeds). Each view uses its own binding bar, so "bar accuracy + 0.20" means a slightly
different q in each view. Group and component values under uniform accuracy are upper bounds.

| Setting | Original clusters | Degree groups | Shared-shape components |
|---|---|---|---|
| uniform, bar accuracy + 0.10 | 0.002337 / 0.003369 / 0.005846 | 0.0006934 / 0.002263 / 0.005215 | 0 / 0.002359 / 0.006329 |
| uniform, bar accuracy + 0.20 | 0.02169 / 0.03862 / 0.07939 | 0.008036 / 0.0235 / 0.07939 | 0 / 0.02064 / 0.04755 |
| uniform, bar accuracy + 0.30 | 0.1194 / 0.2611 / 0.9056 | 0.04795 / 0.169 / 0.9056 | 0 / 0.1203 / 0.4895 |
| never loses, wins 0.50 (exact) | 0.007812 / 0.4161 / 0.7728 | 0.007812 / 0.2734 / 0.5929 | 0 / 0.2083 / 0.5382 |
| never loses, wins 0.75 (exact) | 0.1335 / 0.8416 / 0.9984 | 0.1335 / 0.7162 / 0.9841 | 0 / 0.6087 / 0.9737 |
| never loses, wins 1.00 (exact) | 1 / 1 / 1 | 1 / 1 / 1 | 0 / 0.9048 / 1 |

- The component view is exactly 0 in 2 of 21 salts (component W 6, fewer than 7).
- **In plain words.** Suppose a model is right on every cluster the bar gets right, and wins 3 of every 4 clusters the
  bar gets wrong. Then it passes the component view with a chance of about 0.61 on average over these salts, and never
  more than 0.97. A model that is only 0.20 more accurate than the bar everywhere passes it with a chance of at most
  about 0.05.
- These are sensitivity numbers under an assumed model, not a forecast about Helm.

#### R4. MINOR: both-arm packet-route acceptance

**Reviewer's summary.** "A2.4's list of required prints includes 'both-arm packet-route acceptance'. The build does not
print it and does not list it as open. It checks the packet route only against the pinned 785c9bd1 tree."

**Reviewer's scenario.** The unchanged arm is the historical 20208c92 source (named plan d015d58e). If that reader
rejects, or reroutes, a 6-node HSET-2 packet, the repaired-versus-unchanged comparison would fail at scoring time, after
the paid build.

**Reviewer's fix.** Add a field to the feasibility block (for example `both_arm_packet_route_acceptance:
NOT_YET_CHECKED`) that names the check still required, and add it to the open questions for the custodian build.

**Disposition: fixed.** The feasibility block now has `both_arm_packet_route_acceptance`:
- state `NOT_YET_CHECKED`;
- what this build checks: the repaired arm only (every packet passes the frozen validator, the LARGER route and Helm's
  input reader of the pinned tree);
- what is still required: the unchanged arm's reader, from the historical `20208c92` source (named plan `d015d58e`, as
  the reviewer wrote), must accept and route every HSET-2 packet the same way, run by the custodian build or its scorer
  on the same packets;
- `A2.4: a missing receipt is a pretraining blocker`.

The builder did not run the unchanged arm's reader. That source is not in the pinned tree. Open question 4 below.

#### R5. NOTE: reach components equal degree groups

**Reviewer.** "For reach, the build treats the frozen 64-world training bank as outside 'every packet role', so for
reach the components equal the degree groups. Read literally, A2.2 would join every reach group into 1 component. This
only affects reach component floors, which are printed but do not bind, and the reach claims already read NOT_TESTABLE.
The builder lists it as open question 6." Fix: the design owner confirms this reading in the A2 text, or accepts 1
reach component.

**Disposition: kept; open question 5 below.** No code change.

#### R6. NOTE: the A2.1 families never bind

**Reviewer.** "The A2.1 families are implemented correctly but add no protection. Under the twin design, every
FIXED_POSITION_j, FIXED_ALIAS_Wk and STATUS_BY_COUNT_m is wrong on every cluster, so its W equals the cluster count and
it can never be the binding bar. A fixed position always names a world, so it fails the NO_MATCH twin. The list E has
the same length in both twins, so a count rule gives the same kind of answer in both and fails one of them." Fix: none
needed; the owner should know these bars never bind.

**Disposition: no change.** For the owner: all 24 family bars (`FIXED_POSITION_1` to `_7`, `FIXED_ALIAS_W0` to `W7`,
`STATUS_BY_COUNT_0` to `_8`) are registered, and they cost nothing. But with the MATCH / NO_MATCH twins they can never
be the bar that decides a claim.

#### R7. NOTE: the confirmatory claim's status words

**Reviewer.** "inference_assumptions stays OPEN_FOR_THE_BUILDER_SCORER_REVIEW. The REPAIR_IMPROVES_ANALOGY_6 row has no
field for MECHANISM_GATE_OPEN or INFERENCE_ASSUMPTIONS_UNSUPPORTED, although STATISTICAL_POLICY.json records the
mechanism state as MECHANISM_GATE_OPEN." Harmless now, because no model has been read. The reviewer's observation, not
a ruling: the way items are sampled does not by itself make the groups independent (shared fillers join groups; all
TEST foci come from one salted draw without replacement), and it does not make the paired signs exchangeable. So unless
the owner accepts the components as the unit of independence, A2.2's default would be INFERENCE_ASSUMPTIONS_UNSUPPORTED.
Fix: the future scorer must carry these two status words; the design owner or the scorer review states whether the
assumptions hold.

**Disposition: fixed in the record; the ruling stays open.**
- The `REPAIR_IMPROVES_ANALOGY_6` row now has two new fields:
  - `inference_assumptions_status`: state `OPEN_FOR_THE_BUILDER_SCORER_REVIEW`; if not supported,
    `INFERENCE_ASSUMPTIONS_UNSUPPORTED`.
  - `mechanism_gate_status`: state `MECHANISM_GATE_OPEN`, read from `STATISTICAL_POLICY.json` at `f287f965`. The
    builder read this state; it did not decide it.
- It also has a new list, `status_words_the_scorer_must_use`: `NOT_TESTABLE`, `INFERENCE_ASSUMPTIONS_UNSUPPORTED`,
  `MECHANISM_GATE_OPEN`.
- The reviewer's observation is printed in the top-level `inference_assumptions` block as
  `review_observation_not_a_ruling`.
- The builder does not rule on whether the assumptions hold (open question 3).

### R.3 Checks run by the builder

- **Tests: 31 of 31 run, 31 passed.**
  - Fast group: 29 of 29 (68.77 s on the final files; an earlier run, 36.47 s).
  - End-to-end group: 2 of 2 (122.05 s on the final files; an earlier run, 60.54 s).
  - Both with one process.
- **Not run: the slow group** (1 test, the trained-state re-measurement). Its code path did not change.
- New tests: `test_d1_switch_records_every_option`, `test_d1_options_in_the_reach_cell_summary`,
  `test_exact_view_power_under_the_hset1a_model`.
- Changed tests: `test_frontier_fallback_rules` (its switch part moved to the D1 test),
  `test_sign_tail_and_conditional_power_exact` (12 significant digits), `test_tiny_end_to_end` (the exact power block
  in every row and view, the packet-route field, the D1 record, the status words, the open analogy question).
- **Bars unchanged under the default.** Checked by loading `4c402209`'s module beside the new one (above).
- **Checker v2.** This round adds no bar, so there is no new bar to grade. The end-to-end test still requires checker
  v2 to equal the direct comparison on every item of the tiny build, every registered bar included. It passed.
- **Two command-line throwaway builds** under `b_not_testable` and `b_rename` (R2): both `build_ok`, every problem count
  0. They took 231.4 s and 228.5 s, of which evaluation was 197.3 s and 166.7 s.
- `pyflakes` is clean on the three changed Python files. The stage-0 files, `PUBLIC_EXCLUDED_v1.json`,
  `hset2_stage0_public.py` and `PROPOSED_T5_OLDER_PUBLIC_TEST_SIDE.json` are unchanged.
- **Files changed** (LF sha256):
  - `hset2_build.py` `a21d022bfc9a8b851dbea23b3f96c79d4cd1ff3c8b5f5cb2e70a9448d7c037ba`
  - `test_hset2.py` `997345c922e5184db55b99b08eba60592e0081ea83cf61bf9bdaade2242ad4af`
  - `hset2_throwaway_ranges.py` `6d4bf43158642bcee275d1e49e4746a05eb5af05e3c4b32b99ecec7b01a7f917` (it also prints
    the exact power per view)
  - this file, and `BUILDER_REPORT_HSET2.md` (a short fix-round note)
- **Not done.** No new search for further cheap rules. This round did not re-measure the reach ranges or correspondence.
  A fresh independent review is still needed before any paid run.

### R.4 Open for the design owner (decisions the builder does not make), before the salt

1. **R1, the analogy scope.** Choose (a) register `WHOLE_CHILD_FLAG_GUESS` (the confirmatory claim then reads
   `NOT_TESTABLE` in every throwaway salt), (b) widen the scope sentence, or (c) define the analogy bar by a declared
   view.
2. **D1.** Choose `D1_FRONTIER_DECISION`: `a` (the default; the 3-step claim reads `NOT_TESTABLE` in 21 of 21 throwaway
   salts), `b_not_testable`, `b_rename` (and approve or change the proposed name), or `c` (needs its own amendment).
3. **Inference assumptions** (Codex A2.2, R7): state whether the components are accepted as the unit of independence.
   If not, the confirmatory claim's status would be `INFERENCE_ASSUMPTIONS_UNSUPPORTED`.
4. **Both-arm packet-route acceptance** (R4): the custodian build or its scorer must run the unchanged arm's reader
   (`20208c92`, plan `d015d58e`) over the same HSET-2 packets and attach the receipt.
5. **The reach reading of components** (R5): confirm that the frozen training bank is not a packet role, or accept 1
   reach component.
6. **The earlier open questions still stand**: Codex A2 and the builder's A2 (accept, edit or reject); note N1's
   switch; the T5 `PUBLIC_EXCLUDED` v2 rule; the DEV decoy pool reading; `UV_TARBALL_SHA256` (the coordinator, before
   launch).
7. **A fresh independent review** of this round before any paid run. This round is `CLAUDE_BUILT_CLAUDE_CHECKED`.

### EXPOSURE (this fix round: every file outside my working copy that I opened)

- **The pinned CNCM tree `785c9bd1`.** Written from git objects by `launch.py --materialize-tree` into `a2fix/tree/` of
  the session scratchpad (1,186 files, tree digest
  `fe2eaa174b6d7265bcb78de25a13b6898a158ee808bfaf87a419c3ff10190db6`, the same as before).
  - The tests, the build and my scripts imported code from it. They loaded the public course, the tokenizer and the
    development material through the frozen loaders.
  - I opened no file of it by hand.
  - Neither I nor my programs opened `records/typed_course_001/checks_002/private_targets.json`.
- **Codex's branch, read-only.** A `git fetch` of `codex/helm-controlled-prelaunch-20260924`. Then `git show` of
  commit `f287f965` for `EVALUATION_DESIGN_v0_4.md` (a search, then lines 195 to 210 and 354 to 460) and
  `records/helm_controlled_prelaunch_20260924/STATISTICAL_POLICY.json` (its inference and mechanism fields, through a
  pipe).
  - Copies went to the Git Bash `/tmp` folder, outside every repository: `ed04_codex_r2.md` (the design text) and
    `stat_policy_r2.json` (the policy file).
  - No checkout.
- **This working copy's own history.** `git show` of `hset2_build.py` at `4c402209`, written to `a2fix/old4c40/` of
  the scratchpad, to compare the bar sets.
- **My scratch files** in `a2fix/` of the session scratchpad. Not committed:
  - scripts: `compare_bars.py`, `d1_cli.py`, `review_section.md` (this text, before it was appended here);
  - the range output `r_analogy_power.json`;
  - the two throwaway builds `d1_cli_b_not_testable/` and `d1_cli_b_rename/`;
  - the pytest folders `pt_new1`, `pt_fast1`, `pt_e2e1`, `pt_fast_final`, `pt_e2e_final`.
  - Every throwaway build here, including its `sealed_throwaway/THROWAWAY_HSET2_SEALED_TEST.json`, was made with a
    throwaway salt.
- **Laptop state:** free memory and the Python process list (PowerShell).
- **Not opened:**
  - any `*_eval.jsonl`;
  - any sealed file or folder, except my own throwaway outputs;
  - anything under `D:/tksCAS-archive/`;
  - any real salt, S3 or AWS;
  - the meta1 ledger; any `results/` folder; `private_targets.json`;
  - the reviewer's scratch files; Claude transcripts.
- No real salt was used or made. Nothing was downloaded. Nothing ran on AWS.
