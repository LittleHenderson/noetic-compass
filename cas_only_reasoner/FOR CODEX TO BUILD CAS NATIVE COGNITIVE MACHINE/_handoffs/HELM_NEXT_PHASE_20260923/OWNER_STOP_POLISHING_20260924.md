# Owner direction 2026-09-24: stop polishing, start running

Label: `CLAUDE_BUILT_CLAUDE_CHECKED`. Claude classified the six items and built the launch records. No independent
reviewer checked this file. It transcribes the owner's words; it is not an owner signature.

## The owner's direction, verbatim

```
OWNER DIRECTION — 2026-09-24. Stop polishing, start running. Applies to Claude and Codex.

We can only chase our tail so much before we see what we have. Real results now.

1. REVIEW RULE, from now on:
   - A finding may hold a launch ONLY if it would make the result wrong, unreadable,
     unsafe for the secret test, or over budget. Call those BLOCKER or MAJOR.
   - Everything else (MINOR, NOTE, wording, record-keeping) is written down and fixed
     later. It never holds a launch.
   - One review round per item: builder fixes, one check, then launch. No new rounds
     for minor points.

2. HELM MAIN TRAINING (HELM-REPAIR-CONTROLLED-1): launch today.
   - Settle the 6 held items now. For each item, write one line: MUST-FIX-BEFORE-LAUNCH
     or RECORD-AND-CONTINUE. The default is RECORD-AND-CONTINUE.
   - Fix only the MUST-FIX items, then launch: 3 repaired runs plus the old-Helm re-run,
     inside my $60 limit, with the existing stop rules.
   - Do not pre-solve the backup plan. If the backup is needed and would go over $60,
     stop at that point and ask me then.

3. Q4 A-versus-B: fix the one remaining small item, no further review round, launch on
   AWS inside the $5 limit.

4. Everything else (HSET-2, the old-Helm re-run polish, bigger-puzzle provisional
   pieces) must not delay items 2 and 3.

5. When results come in, tell me in plain words:
   - what trained;
   - what it shows;
   - what it does NOT show;
   - what it cost.
   Keep the honesty labels (who built it, who checked it). But results first, and no
   new paperwork before the runs.
```

Earlier launch yes (plan section 0): "YES to launching the side-by-side training of the repaired Helm. You approved
up to $60."

## The six held items (`OWNER_HEADSUP_PLAN_REVIEW_20260924.md`), one line each

Training reads no secret-test material. So an item holds the launch only if training would fail to save something
that cannot be regenerated later without retraining.

1. **Option C rationale — RECORD-AND-CONTINUE.** Wording only: one reproduced seed says nothing about seeds 20260918
   and 20260919; the results report says so in plain words.
2. **File vs learned-state vs output identity — RECORD-AND-CONTINUE.** Codex's REPRODUCTION_POLICY.json (bc46b36e)
   already fixes the rule at zero tolerance; freezing it before the result is MF-2; it is never loosened after a
   mismatch.
3. **"No regression" wording — RECORD-AND-CONTINUE.** Used only when reading; the exact sentence is settled in writing
   before anyone opens the comparison numbers; losses and old-gate crossings are always reported.
4. **HSET-2 details and informative-case counts — RECORD-AND-CONTINUE.** Training reads no HSET material; the counts
   and rules are printed before any model is scored on HSET-2, not before training (a disclosed departure from the
   heads-up, per item 4 of this direction); A1, the protected splits and every NOT_TESTABLE result stay untouched.
5. **Larger-question route, bound versions, 1,488 updates, 18 checkpoint files — RECORD-AND-CONTINUE.** Versions are
   bound (repaired 3df31d96, inputs 57ac0be5...; unchanged package c42370c4..., equal to Helm 2.0);
   1,488 = 1,470 main + 16 interference + 2 replay in both arms; file names are confirmed after each seed.
6. **One complete launch request — RECORD-AND-CONTINUE.** This direction replaces the approval gate; Codex's fuller
   pieces (R3-F spend admission, R3-I environment lock) are recorded for later; the unchanged arm's missing launch
   path was MF-1.

## MUST-FIX items and their state

- **MF-1 (BLOCKER), DONE.** Unchanged-arm launch writer
  `records/typed_pointer_001/admission_unchanged_repro_001/write_launch_under_owner_direction.py`, commit `1d16cd04`
  on `claude/helm-unchanged-repro-20260924`. It reuses the admission writer unchanged. It ran: exit 0; recheck passed.
- **MF-2 (MAJOR), DONE for both arms.** Launch records were committed and pushed before any launch:
  - repaired: `afccbcb9` on `claude/helm-on-launch-20260924`; `seeds/study.json` sha256
    `c0d65ce8d1e040c3631ef5148fff4a3934a79ff74ba4f48d8a634380b78e904d`; package_3df31d96 archive
    `0020c28080c2c9432ff5b627e14db5c3fbe433b0b1397d454d4ee0637ba23377`;
  - unchanged: `3344ae5d` on `claude/helm-unchanged-repro-20260924`; `frozen/study.json` sha256
    `60140ae0587e983120f37cb3499ecdc19e59f23cc0363520b2814e9e413f8a12`; execution admission recorded as it is,
    `NOT_READY`.
- **MF-3 (MAJOR), coordinator's hand check before each job.** Full measured spend S starts at $7.36. Before every job
  S + $15.00 <= $60.00. Before repaired seeds 20260918 and 20260919 also S <= $30.00. Otherwise stop and report.

Order: repaired 20260917, 20260918, 20260919, then unchanged 20260917. One machine at a time. No automatic retries.
Never `run_on_study.py --execute`. The backup (unchanged seeds 20260918/19) is not pre-solved.
