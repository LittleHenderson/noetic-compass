# Claude's reference rescorer: run log (2026-09-23)

**What this is.** A reference implementation of the frozen grader's historical rule:
`records/typed_pointer_001/trusted_rescore_reference_claude_v0_3.py` (LF sha256
`39175b3935a4ed7064c2237d8b87db936aa79137d10a9c88b76d1aaacea900e1`).

**What it is NOT.** It is not the active tool. The active `trusted_rescore.py` is back at its original 0.2
bytes (LF sha256 `8e9a751a15358043b8d1bbc7428fd0e475325174e58fe9e00ec5297cbdd5953a`), and repairing it is Codex's
job. After the restore, the active tool's own tests were run:
`pytest records/typed_pointer_001/test_trusted_rescore.py` -> **19 passed, 9 skipped** (the slow tests, skipped
by design), 32.46 s.

**Limits, all non-neural.** Local CPU. No model. No network. No cost. At most 30 minutes per step.

| Step | Started (PDT) | Result |
|---|---|---|
| Write 0.3 anchor, Helm 1.0 | 01:10:12 | **done**: `trust_anchor_helm1_certified.v0_3.json`, LF sha256 prefix `5e5b061896afcc7d` |
| Write 0.3 anchor, Helm 2.0-exp | 01:17:33 | **done**: `trust_anchor_helm2_experimental_20208c92.v0_3.json`, LF sha256 prefix `f16f17810f46688f` |
| Full rescore, Helm 1.0 (3,384 predictions) | 01:25:24 | **STOPPED at the 30-minute limit** (`timeout` exit 124); no reading written |
| Full rescore, Helm 2.0-exp | 01:55:25 | **STOPPED at the 30-minute limit** (`timeout` exit 124); no reading written |

**What the anchors changed.** Each 0.3 anchor differs from its preserved 0.2 anchor in exactly four fields:
`pass_rule`, `schema`, `tool` and `written`. Every pinned identity is identical: study, grader, checker code
closure, prediction hashes, population, record ids, course digest and checker profile.

**About the tool path.** The anchors' `tool.path` says `trusted_rescore.py`, because they were written before
the rename. Their `tool.pin.sha256_lf` equals the reference file's hash above.

**File-only checks of the reference copy against both 0.3 anchors (`--safe-only`, seconds).** Every file
check PASSED, including `PASS_RULE_IDENTITY`. The checker was not imported.

**The rule, verified another way (`RESCORE_RULE_REPLAY.json`).**
- **The inputs.** The committed 0.2 readings hold the checker-derived gained/lost counts, the improved kinds
  and the improved worlds for every run. They were re-checked from raw predictions: 3,384 per study,
  0 disagreements with the stored scoring rows.
- **The replay.** The 0.3 rule was applied to those numbers and compared with the frozen grader's
  `gate_reading.json`.
- **Result: all six runs, and both labels, agree.** Helm 1.0 is pass, pass, pass. Helm 2.0-exp is **pass**
  (11/1, p 13/4096), pass (12/0, p 1/4096), fail (7/1, p 9/256). Every run improved 3 kinds and 5 worlds.
- **The old rule.** The 0.2 rule printed Helm 2.0 run 20260917 as failed. That was the recorded error.

**Open.** No full end-to-end rescore by the 0.3 reference has completed. On this laptop, one study needs more
than 30 minutes; the 2026-09-21 AWS job took 41.9 minutes for both studies. The active tool's repaired readings
are Codex's to produce. Claude will check them against section 4 of `COORDINATION_CLAUDE.md` and against
`RESCORE_RULE_REPLAY.json`.
