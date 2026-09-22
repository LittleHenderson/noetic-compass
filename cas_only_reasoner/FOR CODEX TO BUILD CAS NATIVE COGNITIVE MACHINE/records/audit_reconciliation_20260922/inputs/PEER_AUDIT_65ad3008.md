# Audit of the codex agent's RPA / CAS-Ohm work

**Subject:** worktree `_worktrees/codex-rpa-recorded-run`, branch `codex/helm-rpa-recorded-run-20260922`, HEAD `eb998556`.
**Standard applied:** the same one that had just been applied to my own work, which found four false or overstated
claims and one self-inflicted regression. Five independent auditors, read-only, plus my own checks.

**Result: 119 REPRODUCES, 26 OVERSTATED, 11 UNVERIFIABLE, 0 FALSE.**

Nothing in their work is false. The arithmetic, the digests and the safety claims all hold. What is wrong is
framing: headline counts that invite over-reading, and several claims bound to artifacts an auditor cannot see.

---

## What holds, verified by re-running it

| claim | verdict |
|---|---|
| 75 passed (recorded-record adapter, view, Ohm viewer) | **REPRODUCES** — 56 + 12 + 7, zero skipped |
| 347 passed (legacy regression) | **REPRODUCES** |
| 107 passed (Q4 deterministic preparation) | **REPRODUCES** — 48 + 44 + 15 |
| "422 distinct" and "529 distinct" — no double counting | **REPRODUCES** — pairwise overlap is exactly 0; the union is exactly 529 |
| 13 of 13 cryptographic digests | **REPRODUCE**, including one recomputed from a git blob for a file not even checked out |
| the generated HTML is 1,849,451 bytes, sha256 `34ce37a2…` | **REPRODUCES**, byte-identical on re-render |
| plan digest `af813837…` (canonical JSON, not file bytes) | **REPRODUCES** |
| **nothing ran** — no neural execution, no output directory | **REPRODUCES** — `q4_smoke_output` does not exist |

**Their CAS-Ohm implementation is correct and, in one respect, better than my design would have been.** All three
of the book's modes compute: `I = V/R` gives 3 at R=4 and 2 at R=6 from drive 12; `V = I×R` gives 12; `R = V/I`
gives 4. It uses **exact rational arithmetic**, not floating point — output carries `exact_value:
{numerator, denominator}` and `decimal_is_rounded: false`. Refusals are named and correct: `OHM_ZERO_CONSTRAINT`,
`OHM_ZERO_ATTENTION`, `OHM_NUMBER` for non-finite, and `OHM_SCALE_MISMATCH` for mixed scales — the last being a
direct implementation of Appendix I's warning that mixing scales is the commonest way to corrupt a test report.

**Two failure classes from my own audit do NOT recur here.** Their `recorded_view_tests.xml` retains a genuine
11-pass/1-fail run of the *new* browser test against the *old* renderer, with the real error text. That is the
before-receipt my own "39/39 → 48/48" claim lacked until an auditor demanded it. And commit `eb998556` deletes
zero files and removes zero test functions — the silent-deletion fault I committed does not appear here.

---

## What is overstated

**1. The headline counts are inflated by parametrization — the same fault found in my own 458.**

The "529 distinct engineering tests" are **193 distinct test functions** swept over parameters. **336 of the 529
rows (63.5%) are parametrized repeats** of a function already counted. One function,
`test_invalid_declarations_fail_closed`, supplies 31 of the 92 rows in one file by itself. The word "distinct" is
used correctly in the *no-double-counting* sense — that survives the hard test — but a reader will take it to mean
529 independent checks, and it does not.

**2. Only 83 of the 529 are new work.** Three test files were added by this commit (56 + 12 + 15). The other 446
pre-date it. The claim records do not say so.

**3. The 529 is a green subset of a much larger, partly uncollectible suite.** The worktree holds **2,691
collectible tests**; 529 is **19.7%** of them. Worse, **20 test modules cannot be collected at all** in this
checkout — 5 need the missing `jsonschema` package, 15 need modules the sparse checkout omits. No claim record
mentions this.

**4. The "independent CLI rendering" is not independent.** `reproduce_recorded_helm_view.py` and
`tools/render_rpa_view.py` both call **the same `render_rpa_view` function object**. Byte-identity is real and
reproduces, but it demonstrates determinism, not independent implementation.

**5. "Starting local and remote atlas commit `5b3d713c`."** That commit is on **no remote**. `git branch -r
--contains` returns nothing. It is local only.

**6. Two CHANGELOG counts do not match their own underlying records.** "637 distinct lab tests" sits on a record
that reads "622 passed, 6 failed, 9 errors". "354 distinct tests passed" omits a fifth XML recording
`failures=1 errors=37`.

**7. The authorization sentence is loose, though the true limit is disclosed twice.** Their STATUS.md says
"Neither an agent-generated key nor a newly invented approval can establish that identity." An auditor
demonstrated that `verify_authorization` **accepts an agent-generated key with an agent-signed job** — it must,
because no code can tell whether 32 bytes belong to a human. What actually protects the gate is procedural: the
caller must supply `--trusted-key-sha256`, a fingerprint the owner establishes out of band. **They disclose this
exact limitation in the function docstring ("not the human ownership of an arbitrary key") and again in
STATUS.md ("it cannot establish human ownership of an arbitrary key").** So the flagged sentence is imprecise
wording sitting beside an accurate one — not a hidden hole. And nothing ran.

---

## What cannot be verified

**1. "Continuation attachment SHA-256 `76d7821a…`" matches nothing.** Four auditors searched independently. No
file on either branch, under any normalisation, hashes to that value; the only occurrence of the string is the
sentence asserting it. The named continuation document hashes to `cd86eaf8…`.

**2. "Three initial backend tests failed because their temporary directories had not been created" has no
receipt.** Four XML receipts exist; none shows a three-failure backend run. This matters because the *other*
failure in the same list **does** carry its receipt. The honesty ledger is selectively evidenced.

**3. "Later retained acceptance records were found for the native, compound, scoped and cube adapters"** — no
path, digest, filename or commit is given for any of the four.

**4. "289 PCBA tests passed (including 93 adapter checks)"** — no retained XML anywhere records 289 items.

---

## The one thing that needs action, and it is nobody's fault

**There are now two CAS-Ohm implementations that do not reference each other.**

- `api/cas_ohm/quantifiers.py` — built 2026-08-18. Residual diagnostics: `i_pred`, `r_hidden`, `ΔI`, ASOM,
  maturity bands. Float-based.
- `api/notation/cas_ohm.py` — their new 281-line helper. The three modes, exact rational. **Zero references to
  the older module.**

Both compute `I = V/R`, with different numeric models and different refusal behaviour.

**Why they did not find it:** their sparse checkout contains only `api/notation`. The older module is tracked in
git but was **never on their disk**. No file search could have shown it. That is tooling, not diligence.

**And the timing:** their CAS-Ohm commits are `2026-09-21 22:40–22:42`; my hardening of the older module is
`22:59`. Seventeen minutes apart, on the same problem, neither aware of the other.

**Concrete consequence:** their branch's copy of `quantifiers.py` still has the defect I fixed — `if rf <= 0.0`
with four `_is_finite` references against my nine. Verified: `i_pred(nan, 2)` returns `nan` and `i_pred(8, inf)`
returns `inf` on their branch. Their CAS_OHM_STATUS claim that non-finite numbers are refused is true of **their
new helper** and false of **the older module on the same branch**.

---

## My assessment

Their work is sound and honestly bounded. Every hard safety claim holds: nothing ran, no authorization was
fabricated, the output directory is absent, and the neural code fails closed. The CAS-Ohm arithmetic is correct
and well-guarded, and the exact-rational choice is better than what I had designed.

The faults are all of one kind — **numbers stated in a way that invites over-reading, and four claims bound to
artifacts nobody can inspect.** That is the same fault an independent checker found in my own headline count
hours earlier. It appears to be the characteristic failure of this kind of work, in both of us.

*Audited 2026-09-22. Read-only: nothing under their worktree was modified, and no commit of theirs was pushed.
Five independent auditors plus the author's own re-checks. Every verdict above was re-derived by the author by
running the command, not taken on an auditor's word.*
