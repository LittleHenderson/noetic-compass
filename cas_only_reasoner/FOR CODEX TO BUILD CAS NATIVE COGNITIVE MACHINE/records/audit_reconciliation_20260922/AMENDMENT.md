# Audit amendment: source recovery and historical case reconciliation

Prepared 2026-09-22. This is an additive evidence amendment, not a replacement
acceptance run. No historical record, atlas, compiler, dataset, model or receipt
was changed. No training, inference, GPU workload or paid service was run.

Subject: `eb9985566bd11a89f485d627186ef0efa7177f02`.
Peer audit: `65ad300835c06f9feff154170cb8b103d5d13ffa`,
`records/audit_package_20260922/06_AUDIT_OF_THE_CODEX_AGENT.md`.
The exact peer document is retained in `inputs/PEER_AUDIT_65ad3008.md`.
Repository-relative paths below are rooted in
`cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`, unless stated
otherwise. `receipt_and_source_index.json` records exact commits, Git blob IDs,
byte counts, raw SHA-256 and separate LF SHA-256 for every inspected record.

## Findings that now change

1. **The original continuation attachment is recovered.** Both existing Downloads
   copies are 18,307 bytes and match raw SHA-256
   `76d7821ac2cb6e007df42c7143ab1a81aa22ef46e6a29c71e5bb42d40665d1f5`.
   A byte-identical copy is preserved as `inputs/RECOVERED_ORIGINAL_CONTINUATION.md`.
   This resolves the missing original attachment. It does not prove which bytes
   were present in either historical worktree. The peer-reported later copy
   beginning `cd86eaf8` was not found in the bounded search of 153 Markdown/text
   inputs. Its exact path and full fingerprint were not supplied in that audit.
   A content comparison with that later copy remains **unavailable**; no copy was
   recreated or edited to match either fingerprint. See `attachment_recovery.json`.

2. **The initial atlas failure was already disclosed.** At the audited commit,
   `records/rpa_ohm_atlas_20260922/VERIFICATION.md` explicitly describes
   `core_and_regression_tests.xml` as the initial 244-pass, 37-error, 1-failure run.
   Its Git blob is `cfd2670061214e14ba76615379643c40f07f178f`.
   The statement that the verification record hid this fifth XML is withdrawn.

3. **All 38 initial non-passing atlas cases have later passing records.** Exact
   `(classname, name-with-parameters)` matching finds all 37 errors and the one
   browser failure in later passing XMLs. None is still failing or absent from
   the final set. All 282 initial case IDs are present in the final union. The
   four final files contain 354 distinct cases across 115 test functions, with
   no overlapping IDs. Their 72 additional IDs are 64 existing Ohm-adapter
   cases, seven viewer cases, and one additional atlas-wrapper case. The initial
   failure is retained as history; it is not added to the final passed count or
   treated as an unresolved current failure. See `atlas_case_reconciliation.json`.

4. **The four adapter acceptance records are available.** The prior verification
   document failed to name them. The paths and fingerprints below remedy that
   omission. All 108 artifacts bound by their receipts match the retained bytes.
   Existing acceptance records were read, not recreated. Their bounded source
   families remain distinct; none is evidence of learned competence.

5. **289 PCBA cases have a retained later receipt.** They are a named subset of
   the later CAS-Ohm `lab312_tests.xml`, rather than a file with exactly 289 rows.
   The index identifies all 289 passing IDs across 87 functions, including 93
   adapter cases. This establishes that later validation. The original standalone
   289-case invocation still lacks its own retained raw receipt.

## Atlas chronology and source limits

| Record | Timestamp in retained XML, UTC−07:00 | Cases | Functions | Result |
|---|---|---:|---:|---|
| `core_and_regression_tests.xml` | 2026-09-22 01:14:51.224810 | 282 | 89 | 244 passed, 37 errors, 1 failure |
| `ohm_adapter_regression_tests.xml` | 2026-09-22 01:15:22.455951 | 64 | 21 | All passed |
| `legacy_view_regression_tests.xml` | 2026-09-22 01:15:40.761108 | 52 | 21 | All passed |
| `core_tests.xml` | 2026-09-22 01:16:28.940685 | 231 | 69 | All passed |
| `view_tests.xml` | 2026-09-22 01:21:08.342613 | 7 | 4 | All passed |

All 37 error messages identify `FileNotFoundError`. The browser failure belongs
to `tests.test_rpa_view::test_actual_browser_focus_layout_filter_injection_and_offline_behavior`.
The verification document records materializing the missing tracked compound
fixtures and retrying the owned browser with local WebSocket access. XML records
host `MSI`; the surrounding documentation identifies the Python environment.
The XML itself does not record an interpreter version or a per-run loaded-source
manifest. The amendment preserves that limit.

The final atlas snapshot is `5b3d713c5e7f2b2fc2959aaf776d0d80ca09d256`, committed
at 01:23:17 UTC−07:00 after those recorded runs. The five receipts are identical
there and at `eb998556`. Final product and test source fingerprints are indexed
at the atlas snapshot, before later recorded-Helm viewer changes. An exact
snapshot of every file loaded during the initial failed run is **unavailable**.
Case-ID and timestamp reconciliation proves what the retained reports record;
it does not silently invent that missing source manifest.

## Selected recorded-Helm scope: functions and cases

The 529 selected cases represent 193 test functions: 83 new cases across 39 new
functions and 446 existing cases across 154 existing functions. “New” means the
test source file was added by `eb998556` relative to its parent. Existing cases
remain useful regression protection. The 336 rows beyond one per function are
parameter-specific cases, not inherently duplicate executions.

| Selected file | Cases | Functions | Added at subject commit |
|---|---:|---:|---|
| `tests/test_rpa_recorded_helm.py` | 56 | 20 | Yes |
| `tests/test_rpa_recorded_helm_view.py` | 12 | 7 | Yes |
| `tests/test_rpa_ohm_view.py` | 7 | 4 | No |
| `tests/test_rpa_model.py` | 50 | 22 | No |
| `tests/test_rpa_scoped_compound.py` | 37 | 14 | No |
| `tests/test_rpa_view.py` | 15 | 7 | No |
| `tests/test_rpa_coordinates.py` | 89 | 23 | No |
| `tests/test_rpa_ohm_atlas.py` | 92 | 24 | No |
| `research/helm_cas_expression_lab/test_cas_ohm_connections.py` | 64 | 21 | No |
| `research/helm_cas_expression_lab/test_learner_q4.py` | 48 | 21 | No |
| `research/helm_cas_expression_lab/test_q4_followup.py` | 44 | 18 | No |
| `research/helm_cas_expression_lab/test_q4_preparation.py` | 15 | 12 | Yes |

The RPA groups have 422 individual historical XML case records. The Q4 log
`records/rpa_recorded_helm_20260922/q4_preparation/deterministic_tests_short_path.txt`
records “107 passed in 2.20s,” without individual IDs. A **new collection-only**
listing of the exact frozen three-file source supplies its 107 selected IDs and
51 functions. No tests were executed during that collection. It is explicitly
labeled `selected_q4_collection_NEW.*`; it is not a historical test receipt.
The earlier log named `deterministic_tests_final.txt` says 105 passed and is not
silently promoted to 107. See `selected_case_inventory.json` for every case ID,
the source hashes, provenance and matching receipt.

The peer audit reports 20 unloaded files: five needing `jsonschema`, fifteen
needing omitted modules. Its exact historical per-file list and collector output
were not found in the tracked audit package or bounded retained records. Those
details are **unavailable**, and the aggregates remain attributed to the peer.
No broad collection was launched to manufacture that old list. Likewise, the
peer's 2,691 collectible-case count is not independently reproduced here.
529/2,691 is a selected-case ratio, **not source-code coverage**.

The original verification maps 18 named acceptance items A01–A18, with the
learning-execution item A18 explicitly NOT_RUN. Test function and case counts
do not establish 529 independent requirements, or independent scientific
validation. Requirement coverage must be assessed from the stated checks and
their boundaries separately.

## The disputed 637 and 289 counts

The original PCBA verification explicitly gives the two-environment calculation:
622 Python 3.12 passes + 66 Python 3.14 passes − 51 repeated passes = 637.
Its retained Python 3.14 `legacy_dependency_recheck.xml` has all 66 passing IDs.
The original full Python 3.12 raw receipt and its 15 individual failed/error IDs
were not recovered. Therefore the earlier 637 union remains **not fully
verifiable case by case**; the incomplete evidence does not justify rejecting
the documented arithmetic solely by reading the 622-pass summary.

The retained later CAS-Ohm reports provide a separately dated check. Removing
64 new Ohm-connection cases and three new historical-compiler cases from the
638-case Python 3.12 file leaves 571 legacy cases. Their union with the 66-case
Python 3.14 file is exactly 637, with no overlap. The full later union is 704.
This is a **later recorded result**, not a recovered original run. The nesting
test source changed to compare the preserved compiler with the active compiler;
the other twelve legacy test files are byte-identical to the PCBA commit.
The index records the differing source identities instead of merging timelines.

The later 638-case receipt includes these PCBA counts:

| File | Passing cases |
|---|---:|
| `test_pcba_reader.py` | 126 |
| `test_pcba_component_adapter.py` | 93 |
| `test_pcba_book_cases.py` | 53 |
| `test_pcba_check.py` | 17 |
| Total | 289 |

All four test files match their source bytes at PCBA commit
`4345aa36ab056f9539cad3feb9207bba5356bef4`. Their later validation still does not
prove the missing original invocation. `lab_history_reconciliation.json` binds
every selected case, receipt, timestamp and source comparison.

## Acceptance record index

All paths and fingerprints below identify existing records at `eb998556`.

| Family | Path | Raw SHA-256 |
|---|---|---|
| Native runtime projection | `records/rpa_001/demo2/receipt.json` | `dcd8e3c99fdf0edd45f0e6ea56a6d9336fabac9761ac3056d29b223bf6339f62` |
| Compound runtime projection | `records/rpa_compound_001/acceptance_002/receipt.json` | `73bcedec7a2cdd3a761dcc55cef59049bf643645c1ad8dd810ea503fd264cd55` |
| Scoped projection/navigation | `records/rpa_scoped_001/acceptance_001/receipt.json` | `e7ccd47f85ae2ff86eff3395ec0a39bb0c204206cfacd47cffe100d257bd4283` |
| Authored cube projection/export | `records/rpa_cube_001/acceptance_001/receipt.json` | `b0550845a0e64653910bf8c17a5bd45011ca7068897c59608227b7ce6f50fe7c` |

Native binds 11 artifacts; compound 35; scoped 34; cube 28. All 108 match.
The native, compound and scoped records' 214 source entries also match their
receipt-introducing historical commits. The cube's 31 actual-import entries and
ten declared input entries also match its receipt-introducing commit. These 255
source entries are per-receipt checks, not necessarily 255 different files.
All checks are recorded in `acceptance_record_index.json`.
Presence and hash agreement establish record availability and byte custody;
the reconciliation did not re-execute runtime, semantic or browser acceptance.

## Findings that remain open or need narrower wording

- The claimed original three-failure backend run still has **no recovered raw
  receipt**. The later 56-case success and separate 11-pass/1-fail browser XML
  are available, but neither is that missing backend run.
- Two CLI entry points calling the same renderer show repeatability and entry
  point consistency. They are not independent rendering implementations.
- A fresh remote read finds `eb998556` published on
  `refs/heads/codex/helm-rpa-recorded-run-20260922`; `5b3d713c` is its ancestor.
  `publication_observation_NEW.json` records the current read. This corrects a
  present-tense “on no remote” claim; it does not prove publication timing when
  earlier statements were made.
- Key signatures establish agreement with the selected key, not the human
  ownership of an arbitrary key. The external owner-trust and execution gate
  remain separate. Nothing in this amendment grants training or spending.

## Reproduce this reconciliation

From this worktree's CNCM directory:

```powershell
& C:\Python314\python.exe -B records/audit_reconciliation_20260922/reconcile.py
```

This reads immutable Git records and regenerates only the additive reconciliation
JSON. The already retained NEW collection is read as a listing. To intentionally
make another **new collection-only** listing, use `--collect-selected`; it is
never labeled a historical execution. `--check-current-remote` records another
current remote observation. Neither option launches a model.

Assertions verify the 354-case atlas union, all 38 later passes, the 529/193 and
83/446 split, the later 637-case union, and the later 289 PCBA subset. Source and
receipt SHA-256 checks are retained in machine-readable indexes. Product tests
were not rerun merely to fill holes in historical evidence.
