# AUDIT PACKAGE — everything needed to audit the council's work independently

**Prepared:** 2026-10-16, by the DeepSeek council session, at the owner's order: *"GIVE ME EVERYTHING
CODEX WILL NEED TO DO A COMPLETE AUDIT. EVERYTHING."*

**Auditor:** you are the independent check. Nothing below asks you to trust a summary. Every claim is
paired with the artefact that settles it and the exact command that re-runs it.

---

## 0. Read this first: the auditor's standing orders

From the project's own handoff and `CLAUDE.md`. These are not suggestions.

1. **You are NOT the research governor.** One model may not be architect, protocol-owner,
   decision-maker, executor, auditor and grader. You may audit. You may not promote a claim.
2. **A failed hard gate is a `FAILURE`**, never "PASS with caveats".
3. **Never delete a negative.** Disconfirmations are load-bearing assets.
4. **Claim status comes from a deterministic program reading**, never from prose — including this file.
5. **A status with no checkable artefact is not a status.** Refuse any claim you cannot re-run.
6. **Freeze before code.** One attempt per sealed package.
7. **Keep every number exact.** Never round, never paraphrase a metric.
8. **A name is not a reading.** Open the artefact; do not count its presence.
9. **`ok=None` blocks.** An unreadable reading never passes.
10. **Report in plain English.** Owner action items LAST, under the exact header `FOR WAKIL TO DO:`.

---

## 1. THE HONEST FRAME — what this session was, and what it was not

**The owner's goal, verbatim (2026-10-14):** *"Remember we are trying to replace and do better than the
traditional transformer that is currently the brain of HELM."* A 97-trained-parameter transformer to be
replaced by CAS recipes at 68 learned values.

**What this session actually did:** built **eight mechanism packages** with **212+ passing tests**, all
on copies, none inside HELM, none of it running as a brain.

**What it did NOT do:**
- It did **not** run anything inside HELM's runtime except the earlier wave-1 race (which is a separate,
  pre-existing line — see §5).
- It did **not** produce a brain that recurses. See §6, gap 1.
- It did **not** claim any performance result for anything it built. **Every package carries a claim
  ceiling of `MECHANISM ONLY`.** If any of them is quoted as a result, that is a misquotation.

**The single most useful thing you can check first:** does each package's README claim ceiling match
what the package actually proves? That is where inflation would hide.

---

## 2. THE INVENTORY — everything produced, where it is, how to verify it

**Repo:** `C:\Users\wakil\OneDrive\Desktop\tksCAS`
**Branch:** `claude/project-thread-pmbzd6` (never master)
**Working tree used:** `D:\tksCAS-worktrees\docs-r1w1-wave1-20261016`
**Council records live at:** `docs/working/noetic_council/`

| # | package | path (under `docs/working/noetic_council/`) | tests | claim ceiling in its own README |
|---|---|---|---|---|
| 1 | continuity + real atlas | `continuity_build_v4/` | **50** | `MECHANISM ONLY. S0 ANCHORS TO THE REAL ATLAS MODEL AT COMMIT eb998556; THIS BUILD ADDS NO ATLAS OF ITS OWN. NO LANGUAGE PASSED ACROSS IT.` |
| 2 | D/W/P recursion | `dwp_engine_v2/` | **33** | `MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.` |
| 3 | the loop + real gate | `the_loop_v3/` | **35** | `MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM.` |
| 4 | return address | `return_address/` | **27** | `MECHANISM ONLY. NO CIRCUIT USES THIS YET.` |
| 5 | faculties | `faculties/` | **37** | `MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.` |
| 6 | language | `language/` | **30** | `CONTROLLED ENGLISH ONLY. NOT NOT CONVERSATION. FORM ONLY, NO MEANING CLAIM.` (see §7, defect D1) |

**Re-run everything in one pass** (from the working tree):
```
foreach ($p in @("continuity_build_v4","dwp_engine_v2","the_loop_v3","return_address","faculties","language")) {
  Push-Location "docs\working\noetic_council\$p"
  & "C:\Python314\python.exe" -B test_all.py 2>&1 | Select-String -Pattern "TOTAL|RESULT"
  Pop-Location
}
```
**Also run the language demo** — it is the only place real English output exists:
```
cd docs\working\noetic_council\language
C:\Python314\python.exe -X utf8 -B demo.py
```

**Two packages are being wired as you read this** and may or may not be present:
`faculties_v2/` and `language_v2/` — the Unity Eye and `RESTART_FALLBACK`. **If absent, they are
unfinished; do not report them as done.**

---

## 3. THE CLAIMS REGISTER — each claim, its evidence, and how to falsify it

Check each one. A claim with no re-runnable evidence is to be **withdrawn**, not softened.

| claim | evidence | how to falsify |
|---|---|---|
| The real atlas model is bound at S0, not a stand-in | `continuity_build_v4/real_atlas/PROVENANCE.md` records branch, commit `eb9985566bd11a89f485d627186ef0efa7177f02`, sha256 per file; the adapter re-hashes on import | change one byte of a file in `real_atlas/` and run the suite — it must fail |
| The stand-in atlas is deleted, not merely unused | a test asserts `atlas.py` is absent, unimportable, and that a duck-typed imitation is refused | recreate `atlas.py` and run — must fail |
| Glue-back is the real model's decision, not the build's | a test substitutes the real `compatibility()` and `certify_overlap()` | replace one with a stub and run — must fail |
| The ASOM gauge cannot gate | the gate request object has **no field** for the label; 480-turn matrix run computed vs forced to all five labels; identical verdicts | add a label field to the request and let the gate read it — must fail |
| A block at depth 12 is deadlock; depth 13 unreachable | exhaustive proof over depths 0–12; **67,108,864 policies** | set `HORIZON` to 13 and run — must fail |
| The Desire loop is bounded at 12 and never touches depth | `DESIRE_BOUND = 12`; 13th cycle refused as `DESIRE_BOUND_EXHAUSTED`, never a deadlock word | set `DESIRE_BOUND` to 13 and run — must fail |
| A dirty child invalidates every ancestor | walk to root; clean siblings unaffected | stop propagation at the first ancestor — must fail |
| A thread returns only with a strictly newer Bias | equal, older, cancelled, duplicate, mismatched-call all refused with distinct words | allow an equal Bias — must fail |
| No root shortcut | `to_root()` returns a **different type** with no call id that refuses to be a destination | make it return a return path — must fail |
| Imagined evidence cannot verify | `RealEvidence` and `ImaginedEvidence` are sibling types; the verifier refuses before calling the checker, and a test instruments the checker to prove **zero calls** | make `ImaginedEvidence` inherit `RealEvidence` — must fail |
| `1/3` round-trips exactly and is never a decimal | `numbers.py`; a decimal request returns `LOSSY_CONVERSION_REFUSED` | allow a decimal render of a non-terminating fraction — must fail |
| The invented-word cheat is caught | a fake grammar with a made-up Noetic "Blend" passes its own round trip; the independent validator reports `UNKNOWN_NOETIC` | remove the independent validator — must fail |
| Wordings per content: min 12, median 24, max 24 | printed by `test_all.py` | recount from the output yourself |

---

## 4. THE DEFECTS I ALREADY KNOW ABOUT — audit these first, they are the honest ones

**D1 — a claim ceiling has a typo.** Package 6's ceiling reads `CONTROLLED ENGLISH ONLY. NOT NOT
CONVERSATION.` — a doubled "NOT". Cosmetic, but it is a defect in a statement about claims, so it must
be fixed rather than excused.

**D1b — `faculties_v2` FAILS its own suite and must not be trusted.** The Unity Eye plus
`RESTART_FALLBACK` wiring reports **44 of 48** with `PYTHONHASHSEED=0` and **45 of 48** unseeded — and
**two runs of identical bytes produced different failure sets.** That is a **reproducibility failure**,
which breaks `H3_replay`. The test meant to prove the eye cannot write dies on a `NameError` before it
asserts anything. **Treat that package as unfinished. Do not read its pass count as a pass.**

**D2 — a test that asserted the opposite of a ruling was deleted.** `desire_loop_1000_iterations_depth_stays_0`
asserted a 1000-cycle loop is legal. The owner's ruling made that false. It was replaced by
`desire_bound_is_exactly_12_each_way`. **Verify the replacement actually tests what it claims** and that
nothing else was lost with it.

**D3 — the language build duplicates an existing parser.** A prior CCE parser exists at
`2026-10-14\lm_t1\cce.py`. The session built a **fresh** one instead of reusing it. The justification is
that the new one adds the fraction ruling, tap/inject and the independent validator — but this is the
same "build parallel instead of reuse" failure the project's own vision forbids (`Do not create a
parallel memory framework, RPA build or roadmap`). **Reconcile or record the duplication as debt.**

**D4 — the alias-wide fallback is missing from the language build.** The spec says free English is read
in `ALIAS-WIDE` mode, measured at **233 of 439** rows against strict CCE's **0 of 439**. The build has
the alias *word lists* but **not the wider reader.** So the language layer reads **none** of free
English. This is the single biggest functional gap in package 6.

**D5 — module docstrings are not covered by any test.** Putting a stale claim in a module docstring
leaves the suite green. Only the README is tied to the constant.

**D6 — several numbers are the owner's rulings, not canonical.** `HORIZON = 12` and `DESIRE_BOUND = 12`
are marked in the source as *"THE OWNER'S RULING OF 2026-10-16, NOT DERIVED FROM CANON"*. The book says
5. **Do not report these as canon.**

---

## 5. THE SEPARATE, PRE-EXISTING LINE — wave 1 (do not confuse it with the above)

Wave 1 is a **closed, passed result** and is **not** part of the eight packages.

- Reading: `R1_W1_READING.json`, **30,931 bytes**, sha256 **`9b1dfdd88568012cabbcfa6d00e97c15dee07d445dfa5daff8be185975f4cf3a`**, byte-identical at `...\R1_W1_RESULT_20261016\` and `...\r1w1_reader\HELM_R1_W1_20261015\`.
- Verdict `PASS`, headline `R1_BEATS_GB3`, claim licensed `true`, ceiling `SYNTHETIC_ONLY`.
- 7 hard gates hold (`H1_receipts` … `H7_budgets`), 8 instrument rows hold (`I1` … `I8`).
- Panel sums `SUM_A1 32`, `SUM_T 9`, `SUM_TPLUS 17/2`. `margin` 4. Achieved gaps 23 and 47/2.
- **The launch already happened** (`2026-10-16T17:02:07Z`, `R1_W1_HOST.json` 2,858,582 bytes). **Do not launch it again** — it would burn the $9.50 hold and break one-attempt-per-package.
- Spec-sheet section **§7.47** records it. The auditor should verify every one of those claims against the JSON.

---

## 6. THE GAPS — what is missing from the brain, which the audit should confirm or refute

1. **Nothing actually recurses.** The gate **names** a repair and a flatten; it performs neither. No
   engine spawns a child. The loop runs one turn on a caller-supplied cause. **Continuity of thought
   across a real recursion has never been exercised.**
2. **The 40 Elements are never APPLIED to a station point.** **CORRECTION:** `validate_profile40` **IS**
   called, at `rpa_model.py:185`. An earlier version of this file said "nothing calls it" and that was
   **FALSE**. The true gap is narrower and still real: every node in the builds gets `profile40=None`
   (`test_all.py:897-916`), so the profile is validated when present but never populated.
3. **The atlas can be bound but not walked** — `rpa_ohm_atlas.py` needs `rpa_coordinates.py`, not copied.
4. **The Bias is a toy** versus the real `BiasState` (readiness axes, operating region, rpm state, bias paths).
5. **No learning at all** — no witnessed-ratio writer, no growth, no pruning.
6. **Memory fading (M1) is not built** — only the fallback-policy test package (`768` rows, nothing scored).
7. **One lacunarity state cannot occur.** **CORRECTION:** three of the four states **are** computed over 200
   cells (`roundtrip.py:302-309`). An earlier version of this file said all four were unwired and that was
   **FALSE**. Only `NO_EVIDENCE` is unreachable in the current build.
8. **The Unity Eye and `RESTART_FALLBACK` were never used** until this session's last act.

---

## 7. THE TRAPS — mistakes made here, so they are not repeated

1. **A name is not a reading.** The session's own gate check found `TEST_PLAN_HELM_R1.md` and
   `INTEGRATION_MANIFEST.md` and **discarded them as "mentions that are not approvals" without opening
   them.** Both were the plan for the work being done.
2. **Fabricated self-criticism.** Four times the session told the owner its own record was defective
   when, on opening the artefact, the record was right. **A false accusation is the same failure as a
   false positive reading.**
3. **A parallel build.** A stand-in atlas was built; the vision forbids it. Corrected, but check nothing
   else was built in parallel.
4. **A one-line replace on a two-line constant.** The claim ceiling is a string wrapped over two source
   lines, so a one-line find-and-replace broke a test. **Read how a test derives its expectation before
   editing what it checks.**
5. **Verifying where work happened instead of where it was recorded.** The return-address build passed
   in its own folder and failed from the merged branch, because its `real_atlas/` subfolder was never
   committed. **Always verify from the merged record.**
6. **Trusting a stale runbook.** A runbook written before a launch said "step 4, launch" long after the
   launch had happened seven times.

---

## 8. WHAT IS GENUINELY NOT VERIFIED — do not let anything imply otherwise

- **No package has run inside HELM.** Every ceiling says so.
- **No package has performed a real recursion, a real return, or a real repair.** They test the rules.
- **The language reads no free English** (defect D4).
- **The 40 Elements have never been applied** to a single station point.
- **No performance claim of any kind** is made for any of the eight packages. The only performance claim
  in this whole record is wave 1's, and it is separate and pre-existing.
- **The eye and the fit-start fallback** were wired last and were never used before that.

---

## 9. HOW TO REPORT BACK

For each of §3's claims: `CONFIRMED` / `REFUTED` / `COULD NOT VERIFY`, with the command you ran and its
output. For each of §4's defects: still present or fixed. For each of §6's gaps: real or not. Then:

- **The single weakest component** by the Limiting Reagent rule — lowest yield against requirement — with
  the arithmetic shown.
- **Any violation of canon or protocol** found, named plainly with the rule broken.
- **The one thing that most needs the owner.**

**Do not soften a disagreement. Do not average a failure into a pass. Do not accept this file's word
for anything you have not run.**
