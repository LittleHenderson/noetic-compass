# Evidence custody and execution log

A0 applies the plain-english-mode and plain-english-tech-explainer skills for reporting.
The copied user directive and RESOURCE_AND_WRITE_BOUNDARIES control this investigation.

## Role worktree creation

A0 verified the research root, branch codex/helm-failure-research-20260922,
clean status and starting HEAD 59b1dd57e57648ab68c1cc26fbae95a957c20cd3.
A0 then sequentially created helm-failure-a1 through helm-failure-a7 under the
same _worktrees directory, branches codex/helm-failure-a1-20260922 through
codex/helm-failure-a7-20260922, all from that exact commit. For each role:

1. git worktree add --no-checkout -b <role-branch> <role-root> <starting-HEAD>
2. Four inherited sparse patterns piped to git -C <role-root> sparse-checkout set --no-cone --stdin.
3. git -C <role-root> checkout.
4. git rev-parse --show-toplevel; git branch --show-current; git rev-parse HEAD; git status --short.

All commands exited 0, every status was clean, branches and roots matched.
Only A0 performs worktree creation/integration; each role may commit only agents/A<n>/.
These are separate indexes/files sharing Git objects, not security boundaries.

## Root-provided independent custody checks

Root messages supplied these actual completed read-only check outcomes. A0 has not
independently rerun their commands; these are attributed messages, not invented local logs.

- Manifest SHA256 1ddf793e5cd6a77cdcc843b089c26b9a880f268ac556d22d40cdbb45e9874101.
- 642 raw fingerprint rows / 630 unique file paths, 724,161,768 bytes, re-read and SHA256
  verified; zero missing or mismatched files; 1.347 seconds. Scope excludes ZIP member replay
  and grader execution. Zero test functions, zero neural/model executions.
- All 540 manifest member rows from both source ZIPs were length/SHA256 checked;
  all three pinned grader git-show sources matched LF SHA256; zero mismatches; 0.243 seconds.
  Source was not imported and checkpoints were not deserialized.
- q4-live HEAD 4eb98682, reconcile HEAD 5f7111d5, helm3-lab HEAD 1eab89f1 all match
  WORKSPACE_SNAPSHOT and have clean status.
- Root's earlier expensive original mutable-workspace status check was interrupted by user
  steering. It did not complete, produced no preservation conclusion and made no mutation.

## Coordinator read failures

Initial discovery attempted USER_DIRECTIVE.md, which does not exist. Exit did not prevent
other reads. The correct copied directive is CODEX_HELM_FAILURE_RESEARCH_TEAM_20260922.md;
A0 then read it fully. Initial full manifest output was truncated; role prompts instruct
structured field selection. Neither issue changes evidence bytes or silently drops a seed.

## Independence and resource rules

First roles use fork_turns=none and receive common factual records plus role only.
The copied directive contains historical opinions; exposure is disclosed, not perfect blindness.
No new peer conclusions pass the first-report barrier before A1-A6 are saved and committed.
A0 integrates reports but does not supply the final judgment. Fresh A7 has no prior role.

Native inherited sessions use existing allowance; no dollar-cost claim. No paid product,
model override, credit reset, dependency install, GPU/cloud/model run or training is allowed.
Pure CPU probes: at most two concurrent; 120 seconds per probe. Root/A0 avoid third concurrent
probes while two investigators work. New neural causal tests remain proposals marked NOT RUN.

Root later completed original mutable-workspace status comparison: git status --porcelain --untracked-files=normal matched WORKSPACE_SNAPSHOT exactly, 138 entries (29 tracked and 109 untracked), same seven warnings, exit 0, 0.153s. This is status-list preservation only, not byte hashing of unrelated dirty files.
