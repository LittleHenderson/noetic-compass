# Owner decision D-1: build a new checker version (2026-09-23)

**The owner's words, verbatim,** in the live Claude Code conversation on 2026-09-23:

> D-1 approved: build the new checker version

- **What kind of record this is.** It is an agent-recorded transcription of the owner's chat message. It is not
  a cryptographic signature, and it is recorded the same way as `docs/OWNER_RUN_AUTHORIZATION_20260922.md`.
- **What it approves.** Decision D-1 of `records/helm_eval_design_20260923/EVALUATION_DESIGN_v0_2.md`,
  section 2: a **new, separately named checker version**, with a raised isomorphism bound, so that Stage 2
  (analogy and correspondence on structures of 5 or more nodes) can be built and scored.
- **What it does not change.**
  - The frozen checker, its profile digest, the frozen grader, the historical labels and every receipt stay as
    they are.
  - The new version is never called "frozen".
  - It does not re-score any historical run.

**Ownership, under the owner's coordination note of 2026-09-23 ("each changed file and each experiment should
have one clearly assigned owner"):**
- **Builder:** Codex.
- **Independent checker:** Claude.

The build specification and the acceptance tests are in `D1_CHECKER_V2_SPEC_AND_ACCEPTANCE.md`, beside this file.
