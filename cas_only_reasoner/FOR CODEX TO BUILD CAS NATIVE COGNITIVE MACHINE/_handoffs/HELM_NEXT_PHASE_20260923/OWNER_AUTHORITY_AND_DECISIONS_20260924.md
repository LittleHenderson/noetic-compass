# Owner grant of decision authority (2026-09-24, verbatim) and the decisions taken under it

## The owner's words, exactly

> go with your recommendation on the Q4 next step ....YOU HAVE MY AUTHORITY TO MAKE THE FOLLOWING DECISIONS ON THE
> FOLLOWING ISSUES:Protected-copy cleanup: which items of the proposal to carry out. Nothing gets deleted without
> your yes.
> Archive access: limiting the sealed archive folders to your own account is a security setting, so you would
> change it yourself.
> Next Q4 step, given the diagnosis: a lessons comparison (A versus B) needs a dollar limit from you. Changing Q4's
> design needs your go-ahead, because your directive allows an architecture change only when justified.

**Recorded by:** the Claude coordinator (`transcribed_by_agent: true`, `is_owner_signature: false`). Each decision
below cites this grant.

**Standing limit that still applies.** Claude's operating rules forbid it to permanently delete data or to change
security settings, even with the owner's authority. So every cleanup action below is reversible, and the access
change is handed back to the owner as exact commands.

## Decisions: protected-copy cleanup (items of `PROTECTED_COPY_INVENTORY_20260924.md` section 4)

| Item | Decision | How |
|---|---|---|
| 1. Test-run leftovers | **Yes, as a reversible move, not a deletion** | Each of the 1,460 files whose bytes equal a committed Q3 protected file is moved out of the 5 test-run folders. They go into `D:/tksCAS-archive/quarantine_protected_duplicates_20260924/`, keeping their relative paths. Every file is sha256-checked three times before its original is removed. Nothing else in those folders is touched. The folders are untracked by both repositories (checked: 0 tracked files) |
| 2. Builder working copy | **Yes** | `D:/tksCAS-worktrees/helm-builder` becomes a partial checkout that excludes `*sealed*` and `*_eval.jsonl`. The files stay in git and can be checked out again at any time |
| 3. Idle C: working copies | **Deferred to Codex's return (2026-09-28)** | They are Codex's working copies. One owner per working copy. The proposal stands for Codex to act on |
| 4. Failed 115-byte HSET-1A tarball | **No action** | It holds no test. Keeping it costs nothing |
| 5. Second copy of the sealed archive | **Yes** | `D:/tksCAS-archive/hset1a_sealed_20260923/` and `hset1b_sealed_20260923/` are uploaded to `s3://cas-harness-runpod-92754088/sealed-archive-backup/20260924/`, with S3-verified SHA-256 checksums. That bucket is private, versioned and encrypted. The HSET-2 archive follows the same rule when it exists |
| 6. Access to the sealed archive folders | **Restrict to the owner's own account (`wakil`) and SYSTEM** | Claude does not change security settings, so the owner runs the commands Claude hands over |

## Decisions: the next Q4 step (Q4-SDG-1)

**The recommendation, now decided.** Keep Q4's current architecture for the next run, as the directive requires ("no
architecture change unless justified"). Run the directive's A-versus-B comparison so that its result decides, by a
rule frozen in advance, whether an architecture change is justified.

- **Arms.**
  - A = the existing family-G teaching.
  - B = the new CAS SDG lessons (families A to C; family D is not used yet).
  - Same model, same loss, same practice budget.
  - 3 seeds per arm, on seeds declared before launch.
- **Measured at fixed checkpoints, per arm and seed:** the error panel's input-use measures (one-field edit
  sensitivity; distinct outputs; summary similarity), plus exact-tree and per-slot scores on the shared panels.
  Evaluation cost is inside the job.
- **The rule that decides an architecture change,** frozen in the spec before launch. If neither arm shows input
  use at the final checkpoint, an architecture change is **justified** by the program's reading. It is then
  designed as a separately named, reviewed arm, and never mixed into A or B.
- **Dollar ceiling: $5.00** for the A-versus-B job, including its pinned data build on the machine.
  - One GPU machine at a time; no automatic retries.
  - Expected cost is under $1: a 70,818-parameter model, and the diagnostic's forward and backward passes took
    26.7 s.
- **Before launch:**
  - the fresh review's open spec items are fixed: M1 (a frozen pass/fail rule and pre-set seeds), M2 (a shared
    panel that favours neither arm) and A1 (the compiler engine pinned for the build);
  - the A-versus-B runner is built and reviewed;
  - the protected examination stays out of every feedback loop.
- **Not decided here:**
  - any use of the protected examination, which still needs a pre-registered arm and the owner's approval;
  - the shape of any future architecture change.
