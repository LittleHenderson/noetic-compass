# U1c — open questions for the owner

Status: DESIGN ONLY. Each question is a real research or money choice. Each has my recommended answer first, then one sentence on why. Nothing here is approved until you type your own line. The operator never writes or signs a line for you, and a line relayed by another agent is not approval.

**Must be answered before anything is frozen:** Q2 and Q5. (Q4, Q6-Q11, Q13, Q14 are also written into the preregistration; if you change them, the file changes before you name its sha256.)

---

**Q1. Scope.** Recommended: **yes, replicate U1b exactly on the RB2c brain now; test the eye on the canonical wide brain (RB-W1) or the live loop later as its own test, EYE-ACT-1 (spec 7.122, PR #454; named U1d in the first draft).**
Why: a wide-brain eye test needs a new eye adapter, new faults, new answer keys and a new reader, and bundling it would put this clean replication at risk.

**Q2. Seeds: commit-then-reveal.** Recommended: **yes.** Before any code exists, you pick a secret of at least 4 random words (letters and digits, single spaces, at least 20 characters), compute its fingerprint privately, and type only the fingerprint. After the package is sealed and you have seen its fingerprint, you type the run line and reveal the secret. The worlds come from your secret plus the package fingerprint.
Why: it is the only rule under which neither Claude (who cannot know the secret before the seal) nor you (locked in before the package exists) can steer the worlds; with "your line + package fingerprint" alone, the builder could make many candidate packages and keep the one whose worlds it liked.
- If you say no: the fallback is "your run line + package fingerprint". The design then says plainly that the builder-picked-worlds gap is NOT closed, and the licensed sentence drops that claim.
- Keep the secret off this laptop until the reveal (paper or phone). Claude runs on this laptop and could in principle read files or its terminal panel; a promise not to look is not a mechanism.
- To compute the fingerprint, you can use a phone app, or paste this into a PowerShell window you open yourself (not Claude's terminal panel). It reads the secret without saving it and prints only the line to type:

```powershell
& {
  $s = Read-Host 'U1c secret (4+ random words; not saved)'
  $n = $s.Trim()
  if ($n -notmatch '^[A-Za-z0-9]+( [A-Za-z0-9]+){3,}$' -or $n.Length -lt 20) {
    Write-Output 'Not accepted: use 4 or more words, letters and digits only, single spaces, at least 20 characters.'
    return
  }
  $b = [Text.Encoding]::ASCII.GetBytes($n)
  $h = -join ([Security.Cryptography.SHA256]::Create().ComputeHash($b) | ForEach-Object { $_.ToString('x2') })
  Write-Output ('Type this in chat:  U1C COMMIT ' + $h)
  $s = $null; $n = $null
  return
}
```

**Q3. Custodian.** Recommended: **accept a separate Claude session as the custodian**, which builds the used-seed table, runs the limited text scan, freezes the allowed slots, and writes its own seed derivation from the frozen text without reading the builder's program.
Why: it is the Q8/Q9 precedent and catches builder bugs by an independent derivation; it is disclosed that the custodian is not a person, and with commit-then-reveal the custodian cannot steer the seeds either.

**Q4. Re-running part of U1b's inputs to prove the port.** Recommended: **PREFIX-722**: re-run U1b's world build, calibration and the first 722 of U1b's 1,544 items (all 7 arms on every scored dialogue and on draw 100), only to compare answers; no reading of record, nothing merged with U1b.
Why: it is the smallest slice that tests all 7 arms on Linux before any fresh world is scored, at about +0.02 USD of waiting time; your memory note says U1b is never re-run, so this needs your word.
- Other choices: FULL (all 1,544 items; about +0.04 USD; also checks the whole reading) or NONE (no port proof; the licensed sentence then drops every port claim, and fresh worlds could be spent on a broken port).

**Q5. Port strictness.** Recommended: **zero tolerance**: every compared field must match, except timing fields, and the list of excluded fields is fixed before the seal by a build test that runs the same fixture worlds twice on the host; the run may NOT continue when answers match but other fields differ ("PORT_ANSWERS_EQUAL").
Why: deciding this after seeing results would be a choice made with the numbers in hand, and zero tolerance keeps "U1b's instrument, unchanged" literally true.

**Q6. Interpreter.** Recommended: **the host's system Python `/usr/bin/python3.12` (CPython 3.12.3)**, recorded by identity, with a check that every loaded module comes from the standard library or the package.
Why: no download is needed, the math library is the host's glibc whichever Python is used, and the venv Python on the image carries torch and numpy that could shadow U1b's own module names.
- Other choices: a pinned CPython 3.14.0 build (U1b's version; needs a download, which needs your yes) or `/opt/pytorch/bin/python` (run-proven on c48-c56, but the shadowing risk above).

**Q7. The fair rival A7.** Recommended: **yes, run A7**, built as the eye's own unchanged automatic-repair code (same routines, same timing, same budget) with its reading-driven whispers replaced by one scripted "re-fit this junction" message, at volume 1/4, read by its own program, never able to change the main word.
Why: without a fair rival the eye's "keep" over the checklist is close to built in (the checklist cannot re-fit and has no budget), and the house rule asks to beat the cheapest method without the mechanism; my forecast is that A7 matches the eye (about 0.65), which is exactly what you should see before acting mode is trusted.
- Other choices: A7's volume = the eye's learned calibration volume (borrows one number from the eye); or rebuild the checklist on the eye's timing in new code (more new code, more room for unfairness).

**Q8. What a pass licenses (claim status).** Recommended: **if U1c replicates and A7 reads `EYE_BEATS_A7` or `EYE_TIES_A7_FEWER_INTERRUPTIONS`, the bounded sentence may carry VALIDATED and Eye ACTING may move off NOT LICENSED for that sentence only; in every other case the sentence carries ENGINEERED-NOT-VALIDATED and Eye ACTING stays NOT LICENSED.**
Why: every planted-fault eye result so far carries ENGINEERED-NOT-VALIDATED (§7.73, §7.74, §7.77, §7.78), and without a fair rival a replication shows only that the construction holds on fresh worlds, not that the eye's sight beats a plain rule.

**Q9. What counts as "replicated".** Recommended: **words only**: replicated means READ with both keep words again; the counts (FIX, FALSE, WORSE) are shown side by side but not scored; the old single "PARTLY" word is replaced by words that name which keep word failed, plus a REVERSAL flag if the checklist matched or beat the eye.
Why: U1b's count margins are built in (A6 cannot fix the 20 misaligned junctions; the FALSE counts look set by the schedule), so count thresholds would add little, and a "PARTLY" word could hide a reversal.

**Q10. The outer gate set.** Recommended: **all 16 outer gates** (custody, seed, freshness, worlds-used, same-code, no-patch, host, modules, port-early, port, memory, opened-files, lanes, window, U1b-untouched, reader-replay), each turning the main word into `U1C_INCONCLUSIVE` if it fails.
Why: each closes a specific way the run could look valid while not being U1b's instrument on unpicked worlds; together they add 16 checks to U1b's 39.

**Q11. What to drop first if the host is slow.** Recommended: **first cut lane P to its 722-item prefix, then drop A7, then stop before any fresh world.**
Why: A7 is the only fair rival, while lane P beyond the prefix is an instrument extra; the first draft had this order reversed.

**Q12. If the port check fails.** Recommended: **stop, record the portability negative, and decide the next step after seeing which file or item differed.** The next step would then be one of: a Windows EC2 host running U1b's exact stack (a new kit; Windows licence price not checked) or edited Linux copies under a new freeze.
Why: the cause decides the fix, and either fix is a new freeze that needs your word anyway.

**Q13. Instance, window and cap.** Recommended: **Option A: one m6i.xlarge, 240-minute window, cap 4.00 USD** (expected about 0.26 USD for the run at the only recorded speed ratio).
Why: it is the current run-proven kit, the two lanes keep the laptop's controller up for the shortest time, and the 240-minute window still finishes if the host is up to about 2.75 times slower than the laptop.
- Other choices: Option B, m6i.large in sequence (about 0.16 USD expected; about 14 minutes longer; A7 dropped on a slow host); Option C, full port proof first (about 0.48 USD; needs Q4 = FULL); or a 180-minute window with cap 3.00 USD (covers up to about 2.15 times slower).

**Q14. Build tests on AWS before the seal.** Recommended: **up to 3 small jobs (30, 20 and 10 minute windows) under one 1.00 USD line**, expected 0.06-0.13 USD; any further job needs a new line.
Why: they settle the interpreter, paths, the open-file audit, the memory gate, the timer chain, the determinism of whole items and A7's behaviour before any fresh world exists, and the laptop is too short of memory to do this work.

**Q15. Attempts.** Recommended: **one scored attempt plus at most one plumbing retry with the same package and seeds (only if no scored fresh-world part started); any change inside the package needs a new secret commitment, a new line and new seeds; at most 2 launches and 3 sealed packages in total for U1c.**
Why: it caps how many times seeds can be drawn, so a run cannot be repeated until it reads well, and every attempt's outcome is reported next to the result.

**Q16. Your 2026-10-21 line "run U1b".** Recommended: **treat it as answered by the verification already done on PR #442 (121 of 121 files re-hashed equal; the frozen reader replayed byte-identically), and treat today's request as the separate U1c.**
Why: U1b had already run on 2026-10-15, and re-running it would break the "never re-run U1b" rule; PR #442 still shows this question as open, so your word closes it.

**Q17. Your forecasts.** Recommended: **optional: if you or the coordinator want to give forecasts, give them before the freeze; they are frozen before code next to mine.**
Why: U1b's coordinator field read "none relayed", and forecasts written after results are worth nothing.

---

## Proposed owner lines (patterns only; you compose and type your own)
1. Answers: `U1C ANSWERS: all as recommended` (or name changes, for example `U1C ANSWERS: as recommended, except Q4 FULL`).
2. Commitment (from Q2): `U1C COMMIT <the 64-character fingerprint>`.
3. After the preregistration is final: `U1C PREREG <its full 64-character sha256> BUILD TESTS at 1 USD, RUN CAP 4 USD`.
4. After the package is sealed and you have seen its fingerprint, the precode and addendum fingerprints and the cost: `RUN U1C at 4 USD zip <first 8 characters of the package fingerprint>`, and in the same or the next message: `U1C SECRET <your words>`.

Line 4's exact text is normalized (Unicode NFC, outer spaces removed), shown back to you as a byte count and a fingerprint, and recorded with your confirming reply.
