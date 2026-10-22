# CAS-RPA atlas integration — verification, 2026-09-22

The requested local integration is implemented: a fixed declared present,
39 coordinates from explicit profiles, nested navigation and exact addresses,
restorable inspection views, and checked CAS-Ohm calculations in the same atlas.

Open [the atlas](demo/atlas.html). Use [the guide](../../docs/CAS_RPA_OHM_ATLAS_20260922.md)
for reproduction, navigation and scope. The supplied present and profiles are
declared examples. No live Helm measurement, board execution or model control
was performed.

## Executed tests

All four final runs passed, with no skips: **354 distinct tests**.

| Test run | Passed | Evidence |
| --- | ---: | --- |
| Coordinate mathematics, checked atlas wrapper, existing atlas model | 231 | core_tests.xml |
| Existing scoped navigation and native viewer, including Chrome | 52 | legacy_view_regression_tests.xml |
| Existing PCBA/compiler Ohm connections | 64 | ohm_adapter_regression_tests.xml |
| New renderer and real Chrome interactions | 7 | view_tests.xml |

The new implementation accounts for 188 of these tests: 89 coordinates,
92 wrapper, and 7 viewer tests. The remaining 166 cover existing behavior.

The browser checks exercised direct JSON and URI lookup, nested containment,
return breadcrumbs, all three layouts, zoom, independent reference arithmetic,
exact zero at the reference, inverse recovery, incompatible-basis refusal,
unassigned profiles, the extreme-profile normalization regression, and the
exact displayed attention values 3 and 2. They tested hostile labels as inert
text, an actual bookmark reload, invalid-view rejection without state changes,
390-pixel page width, unchanged source data, no page script exceptions, and no
HTTP(S) requests by the page.

The repro command also completed its own deterministic checks. Its exact
outputs, navigation trace, coordinates, source hashes and boundaries are in
demo/verification.json; demo/hashes.json binds the four generated artifacts.
It does not label those checks as browser or pytest results.

Final desktop Flower/Coordinates and 390-pixel mobile screenshots are under
browser_qa/. They were visually inspected. browser_qa/browser_proof.json binds
their hashes, view states and the final HTML hash:
fd7eb404184cfdef6639fb05037a60955f08f7941073d0a1cb9abfa269158153.
The capture observed zero page exceptions and zero external requests.
Final visual review also tightened quantity-card wrapping and displayed the
fixture status as "declared present" while retaining the exact source enum.
All seven viewer tests and the screenshot capture passed again afterward;
these repeat checks are not counted as additional tests.

## Failures found and resolved

The retained core_and_regression_tests.xml is the initial failed setup run:
244 passed, 37 errors from a sparse-checkout fixture directory not yet present,
and one legacy browser failure because the sandbox blocked its local WebSocket.
The missing tracked records/rpa_compound_001 files were materialized, and the
local owned-browser check was rerun with tool-level access. The final results
are the four files above; the failed initial run is not counted as extra tests.

Integration review found and corrected a list/dictionary receipt join, missing
profile-basis refusal in the browser, reversed outgoing containment wording,
and an inverse-normalization rounding gap. A skewed valid profile now exercises
the explicit 2e-15 normalization limit with compensated summation.

Independent review also found the decoder could convert a huge integer before
checking its budget when the host integer guard was disabled. The wrapper now
bounds the token before conversion; its regression restores the host policy.
The real mobile run exposed overflow from a long inert label; the banner now
allows wrapping. All seven viewer checks passed after that fix.

The actual tools/render_rpa_view.py CLI was also executed against the new atlas
JSON and wrote the expected HTML after making its direct-script import explicit.
No dependencies were installed and no neural workload was run.

## Source and scope

Atlas PDF SHA-256:
e1acd28bbdc91e5b33e1f29f2610e75b80960dc55b6907b1dc34311a3a6386ab.
Pages 6, 7, 20, 21 and 22 were extracted, rendered and visually inspected.
Their retained text and images are in source_pages/.

The active compiler and CAS-Ohm helper stayed byte-identical to the prior work:

- compiler.py: 9910a381a9eaba7f75cae8f325867bfe28766676d28b84a09b15e1bf9c10f79e
- cas_ohm.py: 20cc15753b43115478c524b00cd015661b225cc57b3f686cdba824e4c2f67afb

The original native atlas model/adapters, runtime schemas, PCBA/Ohm code,
frozen datasets, source pins and Rust engine were not changed. The existing
renderer adds only a separate checked-document dispatch and matching CLI help.
No full scientific acceptance, deployment or complete cognitive-machine claim
follows from these engineering checks.
