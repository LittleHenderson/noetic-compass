# META-3 checkout mismatch — closed

Recorded on 2026-09-06.

The owner-supplied auditor update closes the historical mismatch at
`63f5b4210cc4df179193a5b5e3489ff48d79b3dd` as checkout-induced line-ending
conversion. The claims that these thirteen failures demonstrated defective
evidence guards or missing committed baseline files are withdrawn.

## Evidence and attribution

The supplied auditor account reports a same-machine, same-commit, unchanged-code
comparison: converted checkout **518 passed / 13 failed**; byte-preserving
checkout **531 passed**. This account identifies the original environment cause.
It is not a new experiment performed by this builder. The auditor's raw new
logs and individual changed-file hashes were not attached to this update.

The supplied update is retained at:

`C:/Users/wakil/.codex/attachments/da33eb45-2c90-4270-9498-c294d7c9cb9e/pasted-text.txt`

SHA256: `dba0d1923429212b93484a290699f86a5dc47593bde76f977d45ea0415941f2e`.

Our separate, already-retained byte-preserving reproduction also reports
**531 passed, 1 intentional duplicate-ZIP warning**. All thirteen named
assertions passed individually within that 531-test run, not in addition to it.
All **316** protected files matched both their Git objects and the manifest
before and after. Seven saved rejection receipts show that the six malformed
record checks and the wrong-sidecar check were reached and rejected their
inputs. This independent evidence supports the tested implementation; the
owner-supplied comparison above supplies the historical causal explanation.

Independent receipt: sibling directory
`historical_per_case_reconciliation_002/receipt.json`, SHA256
`49d4f88227218680efb2623c3a222fd79d4fcc47245314476ce3fcb4ecd9c230`.

## Corrected interpretation

Line-ending conversion changed protected bytes. The exact-byte identity check
therefore refused fixture construction before the intended rejection checks.
The two original full tracebacks establish that order directly. The other
eleven original cases do not have individual original tracebacks in the local
record; their assertions were independently rerun and passed. The auditor's
same-commit comparison closes the overall checkout mismatch without inventing
missing original per-case traces.

Earlier reports and raw records remain unchanged. Their then-open environment
question is superseded by this dated closure, not silently rewritten. No
checker logic, accepted hash, model, executor, or historical commit changed.

## Reproduction rule

Obtain the repository with its required history and sibling research packages.
For the historical source, use a new byte-preserving checkout; do not reuse a
checkout already converted by Git:

```powershell
git -c core.autocrlf=false clone --no-checkout REPOSITORY NEW_DIRECTORY
git -C NEW_DIRECTORY -c core.autocrlf=false checkout --detach 63f5b4210cc4df179193a5b5e3489ff48d79b3dd
```

`REPOSITORY` and `NEW_DIRECTORY` are user-selected paths, not literal targets.
The required historical dependency object
`b5f1718e63a2b5cf72b4b606d513d0524b9226ac` must also be present.
Do not regenerate accepted hashes from converted files.

Before functional tests, run the existing reconciliation wrapper's `snapshot`
check against the historical META-3 directory. It verifies the exact commit,
clean tracked files, committed manifest, and each protected file's Git bytes,
working bytes, size and SHA256. The wrapper's full run already performs this
check before launching the unchanged historical validator and again afterward.
Its exact command, environment and raw outputs remain in the independent
receipt named above. Reproductions must use new output directories.

For future source checkouts, the separate research-level checkout-policy change
disables conversion only for the 316 explicitly listed manifest-bound paths,
including source files. The other 287 v7 inputs already have conversion disabled.
It does not disable readable diffs or change accepted hashes. The main agent
independently repeated the policy checks: five pure tests and six rejection
subtests passed; all 603 source files matched local, Git and archive bytes.
The receipt is in META2 `records/hash_bound_checkout_policy_001/checks_002.json`,
SHA256 `5244c6131a0f78e058e3791247464770f9bacde8cd92a9d39244ab7e333618e2`.
That directory's README gives the explicit pre-test manifest-gate command.

## Current experiment remains separate

No retraining, launch, source change, scoring change, deadline extension, merge,
or model promotion follows from this closure. The current v7 source remains
`42f9164754312f12850d9b8789c062fa7fb8069f`.
The earlier 24/24 familiar-program fit and the earlier held-out CAS 0/72 result
remain separate evidence. This checkout correction changes neither score.
