# Independent book and owner-record audit

Audited snapshot: `626cc84b574e60217a103b72d2f09388d7aa5e34`.
Canon pin: `d50abbbcbeb6ff0e8cca3d30a8fc3df62fe03454`.
This is a read-only audit of the other agent's work, not an acceptance record or a new owner ruling.
No book, compiler, model, owner decision, or original evidence was changed.

**Result:** seven of the nine assigned claims reproduce. Two are only partly verifiable:
BOOK-6 needs an unretained pre-fix working copy; GOV-3 needs the original owner chat to establish
authenticity. Four additional findings are retained in `findings.json`; three affect book
meaning or numerical interpretation and one fixes an evidence citation.

## Reproduction

From the CN directory in the audit worktree:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
& C:\Python314\python.exe -B records\peer_audit_20260922\book\probe_book.py
```

Observed exit status: **0**. The script uses only Python's standard library, local Git reads,
Boolean arithmetic, and rational arithmetic. It writes only `book_probe.json` beside itself.
No model, GPU, cloud job, training, or inference is involved. This is a source/evidence check,
not an additional count of product unit tests.

The raw JSON retains every invoked Git command, exit code, repository identity, all eight
cross-repository hashes, both listing enumerations, and exact source lines. Historical content
comes from Git objects rather than mutable working copies. The checkout's current line endings
are recorded separately and are not treated as historical proof.

## Assigned claims

| Claim | Verdict | Independent result |
|---|---|---|
| BOOK-1 | REPRODUCES | All eight changed files at d50abbbc equal main-repository eb3c9b1e after LF normalization; all sixteen manifest hashes match. No book file changed from d50abbbc to frozen 626cc84b. |
| BOOK-2 | REPRODUCES | True diff: 202 insertions, 95 deletions, eight files. The earlier commit really reports 1765/1658. There are 39 top-level Markdown files plus one under build; the Git pathspec prints 40. The pre-handover checker already disclosed this count caveat. |
| BOOK-3 | REPRODUCES | The old prose says XOR detects both-active; its own truth-table column says inputs differ. Independent two-input truth table gives XOR(false for true,true), AND(true for true,true). The correction is justified. |
| BOOK-4 | REPRODUCES | Before OD-A: Chapter 10:278 already declares gate dissonance; Chapter 14:80 and :326 already use the gate statement. The original claim was false; the correction is correct. |
| BOOK-5 | REPRODUCES | Before OD-A, Chapter 10:278 uses gate; Appendix E:327 uses xor for the matching example. At canon, both use gate conflict: AND. |
| BOOK-6 | UNVERIFIABLE | Final Appendix A:137 and Appendix B:374 are corrected. The intermediate owner-edited pre-fix text and exclusive authorship attribution cannot be reconstructed from the supplied evidence. The previous committed NOT line is :372; :374 there is XOR. This limitation was already disclosed in the pre-handover report. |
| BOOK-7 | REPRODUCES | Exactly 58 listing blocks and 42 distinct names, at both dbb388ee and d50abbbc, using the published anchored regex. All matches with file/line are retained. |
| BOOK-8 | REPRODUCES | The two acknowledged CJT/op-amp sentences remain at Chapter 10:322 and Appendix B:65, against the edited differential-stage description. They were reported, not repaired. |
| GOV-3 | UNVERIFIABLE | OD-9 and OD-10 exist with the stated words; the prior refusal exists, but in CODEX_CONTINUATION_20260921.md:53–55. Neither the named verification file nor its packaged copy contains the quote. Original owner chat was not supplied, so the agent-written record cannot authenticate itself. |

“UNVERIFIABLE” does not mean the owner's words are false. It marks what the available
evidence cannot independently establish. The audit grants no new authority from those records.

## New findings

**BOOK-AUDIT-1 — P2: incomplete breakdown correction.** At canon Appendix B:59, an involution
flip occurs only when an explicit rule is declared. Appendix A:40 and :121, Appendix C:549,
Chapter 3:101 and :103, and Glossary:47–48 still describe it as the automatic meaning of breakdown.
These cannot all supply the same checking or teaching rule. OD-A introduced the conditional rule
without reconciling the old unconditional rules. This is separate from the two disclosed op-amp
sentences. Reconcile the canon or publish explicit precedence before claiming a unique runtime rule.

**BOOK-AUDIT-2 — P2: gate arity is unresolved.** Appendix C:447 says NOT takes one input and
all other gates take two or more. Chapter 10:115–116 and Appendix B:389–390 say XOR and XNOR take
two inputs. The old XOR ambiguity survives and the new XNOR definition inherits it. A three-input
XOR interpreted as parity also differs from “exactly one” on three true flags. Specify arity and
truth function before implementing a variadic behavior. This does not invalidate the corrected
two-input XOR/AND example.

**BOOK-AUDIT-3 — P2: exact and observed gain claims exceed the example.** Chapter 16:211
calls the gain exactly 3 and “observed,” regardless of whether forward gain is 12 or 10. The chapter's
own formula A/(1+Aβ), at β=0.333, gives **2.401921537229784** for 12 and
**2.3094688221709005** for 10. Including the displayed 1.5 evaluation stage gives forward gain 18
and **2.5736345438947668**, still not 3. Even the infinite-gain limit at 0.333 is
3.003003003003003; with exact 1/3 and finite A=12 the result is 2.4. These are formula calculations,
not a model simulation or observation. Chapter 16 is byte-unchanged by OD-A, so this is a pre-existing
book defect discovered during the audit, not an agent-introduced regression. Label the limiting
approximation and remove any implication of retained measured evidence.

**BOOK-AUDIT-4 — P3: incorrect evidence pointer.** GOV-3 and OD-9's note point at
records/continuation_20260921/VERIFICATION.md. The quoted refusal is actually at
CODEX_CONTINUATION_20260921.md:53–55. Correct the citation so the audit can reproduce it; preserve
the distinction between a recorded assertion and independently available owner words.

The first three are absent from the package's self-correction list. The citation problem is
also absent. This audit does not claim to exhaust all errors in the complete book.

## Boundaries and disclosed problems

The eight-file canon comparison, real diff size, listing count, XOR correction, and gate-prefix
self-correction are sound. The already acknowledged op-amp sentences remain unresolved.
The intermediate-copy limit on BOOK-6 and the 39-versus-40 pathspec caveat were already visible in
05_PRE_HANDOVER_RECHECK.json and are not counted as new discoveries.

No production source was fixed during this audit. The next action is to review these findings
alongside the compiler and CAS-Ohm checks, then make scoped corrections with tests appropriate
to any behavior change. These book checks neither prove nor disprove a learned Helm result.
