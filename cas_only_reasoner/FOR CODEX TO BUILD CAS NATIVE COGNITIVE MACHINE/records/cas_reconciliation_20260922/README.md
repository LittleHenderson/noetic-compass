# CAS audit reconciliation and diagnostic repair — 2026-09-22

The bounded repair is complete. The working compiler and atlas are preserved.
The audit has an additive amendment, and the shared exact-arithmetic core is a
proposal, not a silently substituted implementation. Fresh Helm preparation and
a retained-record replay are complete; **Q4 neural execution remains NOT_RUN**.

## Source identities and separate worktrees

Integration started from the completed atlas/recorded-Helm commit
`eb9985566bd11a89f485d627186ef0efa7177f02` on
`codex/cas-reconcile-20260922`. The original worktrees were not edited.

- Diagnostic editing branch: `codex/ohm-invalid-numbers-20260922`,
  source commit `9e2e3a8a46d375a7d008e487b7d59aa9aa2d53e5`,
  integrated as `34b0d982`.
- Evidence editing branch: `codex/evidence-reconcile-20260922`,
  source commit `4dcdfe60e24331fa9f15c17f01708f5b271b9f7e`,
  integrated as `2ab01f53482b09338483b447f3bf2cb88466d2f8`.
- Peer audit reviewed: `65ad300835c06f9feff154170cb8b103d5d13ffa`.
  The earlier independent audit remains at
  `0922f339a2e8e4188c05ec882c552ffbd747fd77`.

`../../docs/CAS_SHARED_MODULE_INVENTORY_20260922.json` inventories 21 selected
shared components across four explicit revisions, including tracked files absent
from sparse checkouts. It records responsibilities, public entry points, recent
changes, dependency scope, Git blobs and SHA-256. Repository-wide related Python
discovery finds 185 files in the integrated source revision. This is source
discovery, not a live production import trace.

## Diagnostic repair

The older `api/cas_ohm/quantifiers.py` now rejects non-finite tolerances,
conversion overflow and unrepresentable prediction/residual results. Unusable
observations and zero/inconsistent interval denominators produce intentional
censoring. Exact maturity/trend comparisons and saved values agree independently
of global Decimal precision. Optional exact-threshold metadata preserves the
value used for comparisons while retaining existing float fields.

Numeric policy is `cas-ohm-diagnostic-numeric/0.2.0`. All eleven existing
public function signatures and previous exports remain available. Calibration,
observation provenance, eligibility and non-identifying residual semantics remain
separate from arithmetic. The prototype is not scientifically validated.

Diagnostic source SHA-256:
`418e77a091cd9c68ada54016c15f762b836bb3c998a8080f5e2678a8291537f9`.

The separate repair evidence is in `../ohm_numeric_repair_20260922/`. Its 203
cases / 70 functions comprise 39 original, twelve existing peer guards and 152
new cases across nineteen new functions. Newly executed comparisons against old
code retain 117 base failures and 92 peer failures; every such ID passes with
the repaired code. These are fresh comparisons, not invented historical runs.

An independent review found one intermediate allocation-order problem:
a Fraction could be constructed before an extreme Decimal threshold was
rejected. Validation now happens first; a sentinel regression checks the order
without allocating a huge integer. Remaining type/calibration/eligibility limits
are explicitly listed in `api/cas_ohm/NUMERIC_POLICY.md`.

## Audit amendment and historical limits

Read `../audit_reconciliation_20260922/AMENDMENT.md` and its machine-readable
indexes for paths, fingerprints, timestamps and case-by-case evidence.

- The original 18,307-byte handoff is recovered exactly:
  `76d7821ac2cb6e007df42c7143ab1a81aa22ef46e6a29c71e5bb42d40665d1f5`.
- The initial atlas failure was already disclosed. All 38 initial nonpasses
  appear as later passes; final union **354 cases / 115 functions**.
- The later recorded-Helm selection is **529 cases / 193 functions**:
  83 new cases / 39 new functions, and 446 existing cases / 154 functions.
  The historical Q4 log provides a 107-pass summary; its detailed case listing
  is explicitly a new collect-only record, not a replacement old receipt.
- Four actual adapter acceptance records are indexed. All 108 bound artifacts
  and 255 historical source-entry checks match. This establishes availability
  and byte identity; their scientific or runtime acceptance was not rerun here.
- Later retained receipts support 289 PCBA cases / 87 functions and a separate
  later 637-case legacy union. The original standalone 289/full 637 receipts,
  original three-failure backend receipt, exact historical list of twenty
  uncollected files and the `cd86eaf8...` later attachment copy remain unavailable.

Two calls to the same renderer establish consistency, not independent
implementation. Present remote ancestry does not prove historical publication
timing. No case-selection percentage is described as source-code coverage.

## New integrated verification

| Group | Functions | Cases | Outcome |
| --- | ---: | ---: | --- |
| Diagnostic and compiler interfaces | 140 | 517 | PASS |
| Retained Helm, design atlas and Ohm connections | 65 | 212 | PASS |
| Deterministic Q4 preparation | 51 | 107 | PASS |
| Distinct selected total | 256 | 836 | PASS; no failures, errors or skips |

Of these, **152 cases / 19 functions are newly authored**; **684 cases / 237
functions already existed**, including twelve imported peer guards. Relative to
the integration base alone, 164 cases / 31 functions are added, because that base
did not yet contain the twelve peer guards. The separate 203-case diagnostic run
overlaps this 836-case total and is not added again.

All ten selected test files loaded. The tracked filename census lists 1,044
other `test_*.py` files as not selected; it does not assert they all form one
runnable suite. This is distinct from the peer's unavailable historical twenty
uncollected-file list. `TEST_SCOPE.json` records names, counts and all case joins.

The first integrated attempt had 778 passes and 58 setup errors because this
audit runner omitted the parent temporary directory. All 58 exact IDs pass in
the final retry. Initial XML/logs and the initial runner are retained. No product
source was changed to resolve that setup error. One unknown `asyncio_mode`
configuration warning remains in the numeric group with unrelated plugins off.

From this integration checkout's CNCM directory, the executed final command was:

```powershell
& 'C:\Python314\python.exe' -B records/cas_reconciliation_20260922/run_integration_checks.py --out records/cas_reconciliation_20260922/final
```

The runner records exact subprocess commands, environments, selected source
hashes, timestamps, functions, cases and outcomes. Existing receipt paths refuse
overwrite. Any repeat needs a new subdirectory, for example `repeat_002`.

## Preserved working atlas and resumed Helm preparation

A fresh replay produced `workbench/helm.json` and `workbench/helm.html` with
the same exact bytes as the retained viewer. Document SHA-256:
`088b1d4f83d5533003860d028c6247ed88a03b620021ff64421a61a6fa166271`.
The HTML SHA-256 remains
`34ce37a286b02da2324276e4492d2cf836a999d41e57a51d3d54a6b291298405`.
`fresh_replay.json` binds this newly executed check.

This shows Helm 2.0-experimental revision 1470's saved correct and wrong answers,
not Q4 inference. The full historical development score remains 2/59; two chosen
examples are not a 50% benchmark. Native, compound, scoped, cube, declared-design
and Helm families keep their distinct identities. Missing profiles and Ohm
measurements remain missing. The 12/4/3 design does not become a measured answer.

Fresh metadata-only Q4 preparation is in `q4_preparation/`. Its new canonical
plan SHA-256 is
`a3f5a8b30ac80ee820a85e301802effd77552da2e5fb3b1fb71e96d4a3496863`;
raw plan file SHA-256 is
`2a462db570a4fa3676b339054f0db36119f6f93040a0e4ef796f0c47fb9cdd48`.
It binds the integration checkout and existing dependency copy. The old
absolute-path plan remains unchanged. Metadata validation passed without
importing Torch, probing CUDA or creating the proposed neural output.

Execution remains gated by applicable owner resource permission and an
independently established owner trust anchor outside job-controlled settings.
The code verifies a supplied key/signature; it cannot establish human ownership
of an arbitrary key. No key, signature, approval, inference, training or spending
was created here. The prepared R1 smoke does not complete T15 operation learning,
trained R2, benefit evaluation or fresh-process neural reload.

## Shared core proposal and next command

`../../docs/CAS_OHM_SHARED_CORE_PROPOSAL_20260922.md` proposes one bounded,
dependency-free exact core with separate compiler and diagnostic interfaces.
It preserves each admitted numeric contract, signed residuals, source provenance,
calibration obligations, display policy, public entry points and frozen evidence.
Implementation is deferred as requested; compiler/source-distribution hashes
remain unchanged.

The next safe command verifies saved evidence without creating a new run:

```powershell
& 'C:\Python314\python.exe' -B records/cas_reconciliation_20260922/verify_bundle.py
```

`BUNDLE_MANIFEST.json` lists every new acceptance/evidence artifact's repository
path, byte count and raw SHA-256, plus the protected compiler/atlas identities.
The two component manifests retain their own source bindings. These are
engineering integrity checks, not acceptance of a complete cognitive machine.
