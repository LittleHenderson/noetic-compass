# Audit package — work done 2026-09-21 on the CAS compiler, the PCBA book canon, and CAS-Ohm

**You are the auditor. Your job is to find what is wrong.** This package is built so you can check every
claim by running something, not by trusting a summary. Where I cannot give you a way to check a claim, I say so
and mark it unverifiable.

Prepared by: Claude (Anthropic), working as an agent in the owner's repository.
Handed over by the owner for third-party scrutiny.

---

## What you are auditing

Eight commits on branch `research/helm-3.0-cas-lab`, oldest first:

| commit | what it claims to do |
|---|---|
| `7f32129d` | gave the CAS compiler the canon book's meaning of the nesting operator; fixed eight measured defects; clarified `Worlds` without changing it; fixed help-text naming slips |
| `8febba71` | recorded two owner rulings as artifacts (OD-9, OD-10) |
| `dbb388ee` | a brief arguing which of two PCBA book texts should be canon |
| `0fc6bb30` | committed the book edits (owner decision OD-A) |
| `d50abbbc` | fixed line endings the previous commit broke — **this is the canon pin** |
| `078d00ed` | merged a second agent's branch, taking their compiler over mine |
| `f46d34cb` | **corrected a false claim I had already published** |
| `86ba3d75` | closed a hole in CAS-Ohm's `i_pred`: 39/39 → 48/48 |

HEAD is `86ba3d75431c56147f229f24794805a3d8504f76`.

Plus `a4b2e0d7` (2026-09-22): r_hidden hardened the same way, after the pre-handover re-check found the defect was still live one function over. HEAD is now `a4b2e0d7`.

**The full dated list matters.** Seven further commits carry the date 2026-09-21 on this same line, including
`c3855275` (15:30) — which is the baseline every diff in `03_REPRODUCE.md` is taken against — and `a32d05c8` (15:28),
plus the six from the second agent that the merge brought in (`0c4eb7da`, `8feed0cf`, `8c409a28`, `a5956609`,
`5f6c1231`, `04547c55`). Get the whole picture with:

```
git log --format='%h %ad %s' --date=format:'%Y-%m-%d %H:%M' c3855275~1..HEAD
```

**A pointer that will mislead you if you use it.** The second agent's worktree directory has moved on — it is now at
`5b3d713c` on branch `codex/helm-cas-rpa-atlas-20260922`, not the state that was merged. Use the commit `04547c55`,
never the directory path.

**Four agents already re-ran these claims before you got them** (`05_PRE_HANDOVER_RECHECK.json`). They found one claim
FALSE, three OVERSTATED, one UNVERIFIABLE, and one live defect that I had missed. All are corrected, and all are listed
in `04_WHAT_I_GOT_WRONG.md`. **Treat that as a floor, not as reassurance** — they found all of it in under an hour, and
every error was mine.

---

## Read these two files before anything else

1. **`04_WHAT_I_GOT_WRONG.md`** — the mistakes I made and corrected, in my own words. Read it first, because the
   most useful thing you can do is check whether that list is *complete*. If you find an error I did not
   self-report, that is the highest-value finding in this audit.
2. **`01_CLAIMS_TO_CHECK.json`** — every factual claim, each with the exact command that tests it and the result
   I say you will get. Work through it and record where you disagree.

Then: `02_MANIFEST.json` (digests), `03_REPRODUCE.md` (environment and commands), `diffs/` (what actually
changed), `05_PRE_HANDOVER_RECHECK.json` (four independent agents re-ran my claims before this package was
built — including their disagreements with me).

---

## Six things to be suspicious about

I am the author. These are the places where an author's account is least reliable, so start here.

1. **Test counts.** I quote 639 (was 458 before three deleted guards were restored), 348, 51/51, 99. Counts are easy to state and easy to get wrong. Re-run them.
   Note that two of the suites need `TEMP` and `TMP` pointed **outside** the repository or they refuse to run.
2. **"Nothing else changed."** I claim my CAS-Ohm fix changed only the non-finite cases. That is a claim about
   everything I did *not* test. Try to find a behaviour I altered without noticing.
3. **My self-correction.** I published a false claim about the `gate` naming clash and then corrected it.
   Check the *correction* as hard as the original — a wrong correction is worse than the original error.
4. **The comparison that decided the merge.** I concluded another agent's compiler was better than mine on five
   points and merged on that basis. I had an interest in that comparison being tidy. Re-run it.
5. **Digests.** Every digest here is taken over LF-normalised bytes. If you take raw digests you will see
   differences that are only line endings — I made exactly that mistake mid-work (see `04`). Use the stated
   convention or you will find phantom edits.
6. **The line between calculated and measured.** CAS-Ohm computes design-time predictions. Nothing in this work
   measures a running model. If you find any place where a calculated number is presented as an observation,
   that is a serious finding.

---

## What this work does NOT claim

Stated plainly so you can hold me to it:

- **No model was run.** No training, no inference, no GPU, no CPU inference, no cloud job, no money spent.
  Everything here is symbolic code, text and tests. If you find evidence otherwise, report it.
- **CAS-Ohm is not connected to the compiler yet.** The module exists and is hardened; the connection is
  designed but not built. Any claim that the compiler can compute CAS-Ohm today would be false.
- **Nothing here is validated against a live model.** The book itself says these are "design scores,
  calibration values, or observed ratings," never "a voltmeter reading from a brain or a language model."
- **The PCBA board reader is not built.** Two specifications exist; no code.
- **I am not the research governor.** Owner decisions are recorded in `OWNER_DECISIONS_20260921.json`. Where a
  decision is unmade, the work is supposed to report it as open rather than choose. Check whether it does.

---

## The standard I was working to

The owner's standing rules, so you can judge the work against them rather than against your own defaults:

- Plain English in every report; every literal exact; claim states kept separate.
- A failed hard check is a FAILURE, never a "pass with caveats".
- Owner approval must be an executable record, not an agent's prose. (A second agent enforced this against me
  during the work — see `04`.)
- Never delete a negative result.
- No neural workload on a local CPU; cloud GPU for anything claim-bearing.
- One source-owning agent per branch; never push another agent's unpushed commits.

---

## How to report

For each claim: state the command you ran, what you observed verbatim, and one of
**REPRODUCES / FALSE / OVERSTATED / UNVERIFIABLE**.

Please also answer these three:

1. Is `04_WHAT_I_GOT_WRONG.md` complete, or did I miss one?
2. Is any claim stated with more confidence than its evidence supports?
3. Is there anywhere a calculated value could be mistaken for a measured one?
