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
