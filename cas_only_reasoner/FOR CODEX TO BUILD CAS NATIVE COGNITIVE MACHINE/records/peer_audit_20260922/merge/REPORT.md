# Independent merge/compiler audit

Frozen subject: `626cc84b574e60217a103b72d2f09388d7aa5e34`.
Merge: `078d00edc85fe97570b6aa3c4ea47b0ad2dad248`; parents `d50abbbc` and `04547c55`.
Audited sources were not edited. All probes use source bytes read directly from Git. No learner, GPU, or cloud path ran.

## Confirmed new finding — P2: four more passing tests were dropped

The merge also removed four functions from
`noetic-compass-scaffold/noetic-compass/tests/test_notation_compiler_nesting_and_defects.py`.
The deletion location in the frozen file is immediately before line270. Their original left-parent lines were270,277,285,290.

| Original function | Behavior protected |
|---|---|
| `test_review_a_deep_flat_chain_fails_cleanly_and_still_serialises` | A1000-term flat chain fails cleanly, drops the deep AST, and its error artifact still serializes. |
| `test_review_fn_names_are_not_reserved_but_let_names_and_parameters_are` | Legal functions named `f` and `Noetics`; reserved let/parameter names; exact malformed numeric-binding error. |
| `test_review_no_cross_domain_warning_when_a_side_has_no_known_domain_at_typecheck` | A same-Domain function-call nesting does not raise a false warning. |
| `test_review_the_worlds_warning_comes_from_the_alias_not_from_the_word` | An emergent result named `Worlds` does not trigger the alias warning. |

**Observed: all four original test bodies pass at the merge and at the frozen head:8/8 invocations.**
They remain absent from the frozen suite. Other tests overlap the generic same-Domain/negative-binding cases, but do not preserve the flat-chain serialization, `fn Noetics` positive case, numeric binding diagnostic, or `Worlds` label guard.

This is lost protection, not evidence that those behaviors currently fail. Restore the four guards and correct the audit's incomplete account of the deletions. The three already disclosed help-text guards were genuinely restored; these four were not.

## What the full merge comparison established

- The union of both parents' tracked paths has **0 missing paths** at the merge and **0 missing paths** at the frozen head. MERGE-3 is literally true about files; it does not prove their contents survived.
- Every Python file changed on the left branch was parsed into function inventories. Only the two test files lose top-level functions: seven originally dropped; three now restored; four still missing.
- The entire compiler diff from left parent to merge was read. It preserves the left branch's behavior while adding Drive Register labels, runtime warning propagation, improved identifier boundaries, and conservative full-word repetition. No further removed production behavior was identified.
- Lab test changes preserve their functions and update compiler/data pins; one additional exporter-negative test was added. Help-text changes replace obsolete Foundation wording with the chosen source. Book changes and the left branch's unique governance records survive.
- The original99-test compiler file is unchanged from merge base `c3855275`.
- The Q3v0.5 manifest conflict selects different historical compiler/export pins under the same path. This deserves precise provenance, but intentional branch selection, retrievable parent history and later data versions are not by themselves a new broken-pin defect.

## Rechecked claims

The corrected compiler comparison reproduces: labels preserve `|A`, cross-Domain warnings reach function/builtin paths, and a nonrepeating two-term word is left unclassified. Both compilers reject the old demo files and accept the fixed files; the files were the variable. `P1_count`/`F2_total` already failed before the author's compiler commit.

The old function example already emitted an any-typed-contract warning. Its reported “no warning” must be read as **no cross-Domain warning**.

Original canon-guard source was executed with its original parameter rows against the merged help files (each checked byte-identical to the frozen help file): **9 functions,454 passed,0 failed**. This validates MERGE-5's disclosed historical loss independently of the current639-test parent run.

The historical “I checked before merging” claim remains unverifiable. A current rerun cannot establish when an earlier run happened.

The withdrawn set-contents behavior is absent: equal-content sets bound to `Alpha` and `Beta` remain distinct as elements; text `"Alpha"` can still match the named set. This is the disclosed limitation, not a newly discovered regression.

## Open-question qualification

The compiler reports N1–N13 and preserves explicit open-question IDs in tested results. It nevertheless calculates under provisional readings: first term innermost, identity terms removed, alternating^2/^3 word classed as stabilizing while taggingN6. Therefore GOV-4's “rather than choosing” is too broad; the defensible statement is “it exposes the selected provisional reading and the unresolved questions.”

A qualified observation at compiler.py:1085: mixed-axis detection ignores `drive_register`. `^2^C_{F2|T} ∘ ^3^C_{F2|A}` preserves the differing Drive Registers but omitsN8, reports `stabilizing`, and reduces to `^0^C`. This is shared by both parents, not a merge regression. Whether N8 must cover both Register positions requires precise canon scope; this audit does not declare the semantic answer wrong.

## Reproduction and evidence

From this worktree's CN directory, PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
& C:/Python314/python.exe -B records/peer_audit_20260922/merge/audit_merge.py
```

- `merge_results.json`: complete tree/function inventory, source hashes, Python identity,110 compiler probes,8 dropped-test invocations,454 original canon cases, and8 demo/compiler combinations.
- `original_test_nesting_d50abbbc.py.txt` and `original_test_canon_7f32129d.py.txt`: retained original source, unmodified.
- `run_receipt.txt`: successful command output.
- `claim_verdicts.json`: structured MERGE-1 throughMERGE-5 and GOV-4/GOV-5 verdicts.

An initial exploratory numeric-set probe was rejected by the language's set type rule; it remains in the evidence as `invalid_numeric_set_probe`. The valid Noetic-set probes establish the withdrawal. The main compiler/lab suites are run separately by the parent auditor and are not double-counted here.
