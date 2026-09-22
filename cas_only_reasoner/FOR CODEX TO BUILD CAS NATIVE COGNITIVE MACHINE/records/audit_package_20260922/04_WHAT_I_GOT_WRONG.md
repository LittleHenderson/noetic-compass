# What I got wrong, in my own words

**Read this first.** The most valuable thing you can do as auditor is check whether this list is *complete*.
If you find a mistake I did not self-report, that is the strongest finding available in this audit.

Each entry gives the mistake, how it was caught, what it cost, and where the correction lives. None of these
were deleted or quietly amended — every one is still in the repository history.

---

## 1. A false claim I published, then corrected — the `gate` naming clash

**What I said** (in the OD-A brief `dbb388ee`, in commit message `0fc6bb30`, in the changelog, and to the owner
directly): the owner's uncommitted book edits made the `gate` prefix/leader clash *"reachable in a real
listing"*, and it was not reachable before.

**The truth:** it was already reachable in the committed book. `Chapter_10_Special_Purpose_Components.md:278`
already read `gate dissonance: XOR< attract, averse >;` (a component using the `gate` prefix) and
`Chapter_14_Power_Management.md` already carried two `gate … requires …` statements.

**How I got it wrong:** my search ran as a shell loop whose output was truncated by a broken pipe. The error
`sed: couldn't flush stdout: Permission denied` was printed in my own output and I read the short result as a
complete one. **A search that errors is not a search that found nothing.**

**Who caught it:** not me. An independent design agent, working read-only, contradicted my claim. I verified
their correction before accepting it.

**What it cost:** the OD-A recommendation itself was unaffected — in fact the true situation supports it more
strongly, because the edits fix a case where a chapter and its own answer key disagreed. But a false claim was
published in three places and told to the owner before it was caught.

**Correction:** commit `f46d34cb`. The original claim is struck through in the brief, not deleted.

---

## 2. I broke line endings across eight book files

**What happened:** committing the book canon fix, I copied files from the main checkout (which stores CRLF)
into a worktree that stores LF. Three of eight files had every line rewritten. The recorded diff was
**1,765 insertions / 1,658 deletions** instead of the true **202 / 95**.

**How I caught it:** the number was too big for the change I had made. I checked `git ls-files --eol` and found
`Appendix_E`, `CHANGELOG` and `Chapter_18` had become CRLF in the index.

**What it cost:** a noisy commit that was already pushed. I did not amend it — the repository rule here is never
to amend a pushed commit — so the fix is a follow-up.

**Correction:** commit `d50abbbc`, which is now the canon pin. All 39 book `.md` files are LF in index and
worktree; you can check with `git ls-files --eol -- book/CAS_PCBA_Engineer/*.md`.

**Consequence for you:** every digest in this package is taken over **LF-normalised bytes**. Raw digests will
show differences that are only line endings.

---

## 3. A regression I introduced into the compiler, caught by another agent

**What I did:** fixing a defect where reserved names were silently mis-bound, I made the rule too greedy. It
began refusing ordinary identifiers that merely *start* with a reserved prefix — `let P1_count = ^2^C` and
`let F2_total = ^2^C` were rejected, though both are legitimate names.

**How it was caught:** a second agent, working independently on the same unfinished code, wrote a better fix.
I found it only because the owner pointed me at their work and told me to check it.

**What it cost:** nothing shipped — my version was superseded in the merge `078d00ed` before it could matter.
But it was a real regression in code I had presented as finished.

**Correction:** the merge takes their compiler (`61ed5a45970459e4…`) over mine (`f1a44678438a65c3…`). My report
carries a banner naming the five points where theirs is better, including this one.

---

## 4. I presented an owner ruling as authorization when no artifact carried it

**What I did:** the owner gave a ruling about PCBA in conversation. I wrote it into a report and proceeded as
though the report established it.

**How it was caught:** a second agent read my report and refused it, correctly: *"the current owner-decision
file and this conversation do not corroborate it."* They treated my prose as unverified document content, not
authorization. That is exactly the rule the project has, and they enforced it against me.

**What it cost:** nothing downstream, but the governance rule exists precisely so that an agent cannot
manufacture authority by writing it down. I had done the thing the rule forbids.

**Correction:** commit `8febba71` records the ruling in the owner's own words as **OD-9**, with a note
explaining why the entry exists.

---

## 5. A change I built and then withdrew after review

**What I did:** changed set-element identity in the compiler so that a set used as an element was keyed by its
*contents* rather than its binding name. It looked like a clean fix.

**How it was caught:** an adversarial review agent showed it changed far more than I had claimed — it made a
typed set equal an untyped set with the same members, turned an untyped literal into a built-in, altered
`CoverOf` family sizes, and flipped `"CO-2" ∈ Noetics` from true to false.

**What I did about it:** withdrew it. The old behaviour is kept and pinned as a known limitation, and "set
identity" is now an open owner decision rather than a choice I made.

**Why it belongs here:** I had described this as a defect fix before I understood its reach.

---

## 6. Two earlier claims about the code, corrected during the work

- I told the owner the book's nesting operator *"does not exist in the code"* after checking only a small Rust
  function. The Python compiler has it. Corrected; the lesson recorded is to check the Rust engine, the Python
  compiler **and** cas-native before claiming code lacks a feature.
- I told the owner no PCBA or CCDL parser existed on disk. One does, in `cas-forex/cas_forex/pcba_syntax.py`.
  Corrected in the report and in the owner-decision record.

---

## 7. My strongest CAS-Ohm claim was wrong — I named the wrong dangerous value

**What I said:** that `i_pred(8.0, inf) -> 0.0` was *"the dangerous one"* because a zero flow *"reads downstream as a
starved path"*. The changelog went further and called it *"an ASOM classification produced from garbage"*.

**The truth:** there is no code path from a flow number to an ASOM label. `asom()` takes two enums;
`asom(0.0, Outcome.INTENDED)` returns `None`; `Region` is always supplied by the caller and no function in the module
derives one from a number. The changelog wording was **false**; the commit-message wording was **overstated**.

**And I picked the wrong value.** Measured through `delta_current`, the module's only numeric consumer of a flow:

| value fed in | residual | sign |
|---|---|---|
| a correct prediction, 2.0 | 0.0 | `WITHIN_TOLERANCE` |
| 0.0 — the one I called dangerous | 2.0 | `OVERSHOOT` |
| **nan** | **nan** | **`WITHIN_TOLERANCE`** |
| inf | -inf | `UNDERSHOOT` |

**NaN is the dangerous value**, because it reads as the same sign as a perfectly correct prediction. The `0.0` I
singled out is the *visible* one — an analyst would notice an OVERSHOOT. I had it backwards.

**How it was caught:** an independent checker, re-running my own claims before this package was handed over. I had
flagged the claim as possibly overstated in the package; the checker showed it was worse than that.

---

## 8. My fix was narrower than the principle I cited — a defect of the same class was still live

**What I did:** hardened `i_pred` and `r_total` against non-finite input, citing the monograph rule that an undefined
quantity is refused with a reason and never emitted.

**What I missed:** `r_hidden` never checked its drive argument. At the very commit that claimed to close the hole,
`r_hidden(v=nan, i_obs=2.0, r_known=2.0)` still returned `RHidden magnitude=nan`, and `v=inf` returned `magnitude=inf`.
`r_known` was guarded and `i_obs` was guarded; the drive was not.

**How it was caught:** the same independent re-check. Fixed now; the suite is 51/51.

**What it means for you as auditor:** two of us have now looked at this module for non-finite holes and each of us
missed something. **Look for a third function of the same class.**

---

## 9. A false statement in a commit message — "no test covered a non-finite input"

**What I said:** that all 39 tests passed because none covered a non-finite input.

**The truth:** the pre-fix test file already had `test_r_hidden_censors_non_finite`, passing `float("nan")` and
`float("inf")` as `i_obs` at lines 156 and 158. The accurate statement is: no test covered a non-finite input **to
`i_pred` or `r_total`**.

**Why it matters:** it makes the story *sharper*, not weaker. The module's author had already thought about non-finite
input and handled it by censoring in `r_hidden` — and then never carried that guard to the other two functions. I
described the gap as an oversight of the whole idea when it was a gap in applying an idea already present.

---

## 10. Two smaller overstatements

- **"NaN compares False against every operator."** Not quite: `nan != 0.0` returns `True`. Accurate: every *ordering and
  equality* operator, and `True` against `!=`. The conclusion is unaffected — `nan <= 0.0` is False, which is what let
  NaN through the guard.
- **"All 39 book .md files are LF in index and worktree."** True in the `helm3-lab` worktree; **false in the main
  repository**, where `core.autocrlf=true` leaves 24 CRLF files and one mixed in the working tree. I never said which
  repository. The committed blobs are identical either way.

---

## 11. A book finding I am reporting rather than fixing

Not a mistake in my reasoning, but a gap in the work, and it belongs on this list because the canon pin I committed
carries it.

The OD-A edits deliberately stopped calling the op-amp a CJT — both headings became *"Op-Amp — High-Gain Differential
Stage with Feedback"* and the datasheet body was rewritten. **Two sentences were missed and survive in the canon pin
`d50abbbc`:**

- `Chapter_10_Special_Purpose_Components.md:322` — *"**Op-Amp** is an ultra-high-gain CJT tamed by feedback"*
- `Appendix_B_Component_Datasheets.md:65` — *"The op-amp is a CJT with so much raw gain it must be tamed by feedback."*

The book now contradicts its own headings. I did **not** fix it: the owner approved a specific set of edits, and these
are two more of the same class found afterwards, in their book. Judge whether reporting rather than editing was right.

---
## What I believe is still uncertain, as of handover

Stated so you can test these rather than discover them:

- **A possible mismatch I flagged but did not resolve.** The CAS-Ohm module bands `I_Q` (attention flow) as
  `Q1–Q4`; the book's Appendix I bands `P_cap` (capability) as `M1–M4`. **Same cut points — 2.5 / 5 / 7.5 —
  different quantity, different names.** They may both be correct for different things. I did not settle it.
  The book itself warns about exactly this hazard for `β`: two dimensionless quantities that a unit check
  cannot tell apart.
- ~~The claim that `i_pred(8.0, inf) → 0.0` was "dangerous".~~ **RESOLVED — it was wrong.** See item 7 above.
- **Whether my CAS-Ohm fix changed anything I did not test.** I checked the cases I knew about. One gap has since been
  found and closed (item 8); assume there are more.
