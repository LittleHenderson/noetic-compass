# A2 acceptance audit — research/cas_closed_loop_1 @ aa600668 (read-only; pytest NOT run; nothing marked PASSED)

## Execution status as recorded in the repo
- Last executed suite: **43 cases at 8f55cc3a** (STATUS.json L5-12, pre-amendment adapter) + 4 artifact cases (L61-67). STATUS.json was last touched at 318b22ad and is stale.
- Amended suite (57 scientific, f6253e1a; +4 launcher, 3a4d23f0): **NOT_RUN** in any tracked record (CHANGELOG.md L13-14; job a227f8 focused_tests NO_RECEIPT; job 59bae1 execute_authorized=false). Scientific source at aa600668 is byte-identical to f6253e1a (blob ids equal for all 12 lane files).
- AWS jobs: 47cef2 (318b22ad, 47 tests) STOPPED_UNACCEPTED; a227f8 (f6253e1a, 57) FAILED_BOOTSTRAP_UNACCEPTED; 59bae1 (3a4d23f0, 61) PREPARED_NOT_AUTHORIZED_FOR_RETRY.
- Untracked working tree (not at HEAD): claude_lead_20260927/run_20260927T045459Z ran the 61 cases at aa600668 on Python 3.11: 56 passed / 5 failed (3 NameError, 2 boto3 missing); status FAILED. Cited only as corroboration.

## Per-test classification (36 ids) — counts: COVERED_BY_TEST 12, PARTIAL 15, EVIDENCE_ONLY 1, NOT_APPLICABLE_YET 8
| AT | Class | Principal artifact (file:line) |
|---|---|---|
| AT01 | PARTIAL | SOURCE_BINDINGS.json L4-9; native_step_adapter.py admission_for L99-129; test_native_step_adapter.py L248-252, L233-239; partial_git_probe.json (f6253e1a). Discrepancy: 'missing' objects 348638c9/2636bbb6 resolve in this clone |
| AT02 | PARTIAL | test_artifacts.py L7-8, L11-18, L21-28(new), L31-34; check_artifacts.py L12-50; Helm/Q4 untouched = declarations only |
| AT03 | PARTIAL | receipt fields native_step_adapter.py L381-386; control.py L91-94; tests A L31, L50, L80/88; C L197-200 — ASOM never ELIGIBLE |
| AT04 | COVERED | grant/admission refusals N L79-91, L269-281; A L53-58, L61-66, L242-252, L233-239; C L58-65 |
| AT05 | COVERED* | A L69-88, L91-98, L170-193, L219-230, L255-270, L282-302, L305-308 — *L282-302 hits NameError |
| AT06 | COVERED | control.py L28-38, L75-77; C test_supported_boards... L76-84 |
| AT07 | PARTIAL | C L39-41 (12/4, 12/6), L44-47 (0/NaN/Inf/neg, bare ValueError); no overflow/scale-mismatch case |
| AT08 | EVIDENCE_ONLY | control.py L94-95 residual None; no test references residual |
| AT09 | COVERED | A L24-31, L34-37, L263-270; C L68-73 |
| AT10 | PARTIAL | C L100-115, L205-207; overhead only recorded (N L361-362); NATIVE_BUDGET_INCREASED guard N L344-349 untested |
| AT11 | COVERED | A L40-50, L146-167(new), L204-209(new), L170-193(new); N L290-310 |
| AT12 | PARTIAL | C L50-55, L87-97, L208-212; no large-V cap test; control.py L75-81 |
| AT13 | PARTIAL | N L86-87, L60-66; A L53-58, L196-201(new); shares/scaling not in profile |
| AT14 | PARTIAL | N L323-343; A L45-48; C L131-136, L141; no diagnosis path exists |
| AT15 | COVERED* | N L31-35, L199-257; A L101-124, L127-143(new, NameError); C L134-139, L207; atlas address binding absent (N L253) |
| AT16 | COVERED | C L100-115, L202-212 |
| AT17 | PARTIAL | C L87-97 (reason asserted as set membership only) |
| AT18 | COVERED | C L186-200, L174-177; run_closed_loop.py effect_check L46-57 |
| AT19 | COVERED | C L110-111, L205-207; A L69-88, L219-230 |
| AT20 | COVERED+EVID | C L125-141, L144-151; evidence/journal.json 18-tick chain; result.json '3'/12/18 (produced at 8f55cc3a) |
| AT21 | PARTIAL | C L87-97, L205-207; no subgoal/replay budget-monotonicity test |
| AT22 | COVERED | C L144-151, L164-184, L202-212; run_closed_loop.py replay L100-139 |
| AT23 | COVERED | C L125-129, L68-73, L100-115, L87-97; A L233-239, L248-252, L196-201, L212-216 |
| AT24 | PARTIAL | C L140-141; replay L118-121; hypothetical edges untested here |
| AT25 | PARTIAL | A L91-98; N L253-257; no focus/recenter operation exists |
| AT26 | PARTIAL | A L93; replay per-event rows L129-132; no equal-totals counterexample |
| AT27 | PARTIAL | C L154-161; replay L103-132; A L255-260, L282-302(NameError), L305-308; T L11-28; no wrong-version case |
| AT28-AT32 | NOT_APPLICABLE_YET | T08-T10 not started; pilot refused (STATUS.json L81; run_closed_loop.py L158-159) |
| AT33 | NOT_APPLICABLE_YET | pilot absent; engineering-lane EVIDENCE_ONLY: jobs/*/freeze.json, execution.json, proposal_admission.json; launch.py L215-222, L289 |
| AT34 | NOT_APPLICABLE_YET | worker.py L133-134 analog; failure_review.json NO_RECEIPT recorded |
| AT35 | NOT_APPLICABLE_YET | engineering-lane EVIDENCE_ONLY: execution.json cleanup 13 PASS, billing null (both jobs) |
| AT36 | PARTIAL | REPORT.md L63-71; STATUS.json L15-19, L31-60 (stale); C L127-129 asserts UNMEASURED/None; T12 final report absent |

## (1) First acceptance gap in dependency order
- **Strict: AT03** (T02). T01 (AT01/AT02) has a tracked execution against source identical to aa600668: a227f8/partial_git_probe.json ran check_artifacts.py --git-ref f6253e1a (EXACT_BYTES_VERIFIED, 108 runtime paths, 43 source paths). Everything from AT03 on depends on the 57-case suite, which has no tracked run against f6253e1a/aa600668 (STATUS.json L69 tested_implementation_commit=8f55cc3a; a227f8 NO_RECEIPT; 59bae1 not authorized).
- **First demonstrable defect: AT05 (also AT15, AT27).** test_native_step_adapter.py never imports `TerminalStatus` at module level (imports L2-13; function-local import only at L102) but uses it at L138/L142 and L285 → 3 cases fail with NameError as written. These are the owner-named 'no-frame return_identity' and 'state-bound work join' regressions. worker.py L133 demands zero failures, so the 61-case Lane-A protocol cannot pass at aa600668 even after the S3 transport fix.
- Documentary discrepancy before AT03: AT01 'missing_from_live_repository' claim (SOURCE_BINDINGS.json L6-9, DECISIONS.md L3-7) is contradicted in this clone.

## (2) Case counts (static, from parametrize decorators)
test_native_step_adapter.py 23 fn / **30** cases; test_closed_loop.py 12 / **22**; test_artifacts.py 4 / **5**; test_launch_transport.py 4 / **4** → 57 scientific + 4 launcher = **61**, matching README.md L103, CHANGELOG.md L12-13, 59bae1 freeze.json. Historical: 8f55cc3a = 21+22 = 43 (+4 artifact = 47, package.py L69 floor); f6253e1a = 57.

## (3) RETURN_ADDRESS_TEST_MAP.json gaps
Map exists only on origin/codex/cas-closed-loop-1 (not at HEAD). All 10 mapped upstream functions exist there and at 8182ad52 (sha256 prefixes match) but none is at HEAD nor in the 61-case suite (worker.py L123-127). Required `new_adapter_case_needed`: 0/10 present; 3 partial analogs (event/address association → replay L118-128; tampered replay → C L154-161; exact frame/snapshot → SUSPENSION_EVENT_NOT_UNIQUE N L221-222, untested); 7 absent (frame→node address, wrong atlas address, repeated view event, address chain across restart, budget-from-snapshot, equal-profile merge, layout/recentering). Root cause: no atlas address exists (atlas_binding None, N L253).
