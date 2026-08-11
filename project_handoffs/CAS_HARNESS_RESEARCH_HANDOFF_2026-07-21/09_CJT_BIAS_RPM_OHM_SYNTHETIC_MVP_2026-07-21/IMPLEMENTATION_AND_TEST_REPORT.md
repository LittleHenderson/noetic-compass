# Implementation and Test Report

## Outcome

Commit `25053461c94de23850da7f9c853c420aab1bae62` implements a CPU-only
deterministic recovery harness for CJT, commanded synthetic Bias, corrected
RPM, and CAS-Ohm candidate quantities. It is quarantined from production
evidence and verdict paths.

Implemented controls include exact 9/3/3 prompt-group splits with two
split-specific seeds, separate response/derivative/direct-equivalence/RPM
blocks, eight curve competitors, signed and Fisher-Rao quantities, Cause-hold
and denominator/stability gates, separate CJT and RPM states, paired RPM
controls, exact stop topologies, estimator/truth separation, strict recomputing
schemas, complete-bundle verification, CPython and six-distribution
provenance, and atomic no-overwrite receipt publication.

| Check | Result |
|---|---:|
| Focused recovery/CLI | `62 passed` |
| Full worker suite post-commit | `418 passed in 100.32s` |
| Production quarantine post-commit | `96 passed in 2.52s` |
| Independent byte-drift review | zero drift |
| Real isolated CLI | exit 0; receipt reopened |
| Fresh complete-bundle clone and documented rerun | clean exact commit; exit 0; identical nested report hash |

The real run used seed `20260721`, 1,000 bootstrap replicates, wall time
`60.0832988` seconds, and Python `tracemalloc` peak
`111.597185134888` MB. That is not process RSS or native NumPy peak memory.

## Retained operational failure

The first system `python -I` command failed closed with
`annotated-types has no importable top-level module` because the pinned
packages were only in the user site that isolation disables. It wrote no
receipt. The implementation did not change. A dedicated CPython 3.14 virtual
environment was installed from the exact lock; the unchanged commit/bundle
then succeeded. Never fix this by weakening `-I`.

## Boundary

Three evaluation clusters and intercept-only stochastic variation do not prove
interval coverage, type-I error, or power. Raw observations are not attached.
Provenance is self-hashed/unattested. The complete Python stdlib/extension
closure and Windows parent-directory-fsync crash durability are not proven.
The only successful label is `SYNTHETIC_HARNESS_MVP_PASS` for planted-data
plumbing.
