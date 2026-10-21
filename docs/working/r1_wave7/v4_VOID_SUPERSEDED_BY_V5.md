# v4 of the wave 7 CHAT WAVE package is VOID_SUPERSEDED_BY_V5 (2026-10-20)

- The v4 zip `HELM_R1_W7_20261020_SOURCE_R1W7_v4.zip` (sha256 `8602b1bc98b543e4551e766d9db540d22d6dbc690b788dbbce5c91e4b6c7b712`,
  freeze `948cf6913963f5fe06ab87b46e2ebcf03c3f541433877e04bda666d6e429f072`) stays exactly where it is: job c52's record
  (`run_c52_r1w7v4_20261020/RUN_RESULT_R1W7V4_C52.md`, reading `bcb2f372...`) points at it and that record stands as written
  (verdict `PASS`, word `CHAT_WAVE_NO_GAIN`, K4 missed by one unexplained ask, nothing licensed). Nothing here was deleted,
  moved or renamed.
- v4 must never be shipped, sealed by a custodian, or scored again: the owner's v4 line `CHAT WAVE 2 at 1 USD` was consumed by
  c52's approval record (`approval_v4/APPROVAL_RECORD_R1W7.json` `9e4058a9...`), v4's seed bands 2,000-2,005 M were spent by
  the X7v4 draw, and v4's HELM cut `dfc7158d` carries the wide-reader fault that produced the K4 miss (amendment A-R1W7-5).
- The package for the third round the owner ordered ("third chat round") is **v5**:
  `HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip` sha256 `4b54a077e4b2963301451c6eb78836a32d9797460cd8143d3cf2f9efdc1a7cf8`,
  freeze `PACKAGE_FREEZE_R1W7_v5.json` `8cc543d2102951c79e897f478bc31781e87c511d0a24be54cbf92611ce2bbfd1`, built in
  `build_v5\` from a fresh extract of v4 (`build_v5\extract_v4\`, never edited), HELM cut `f45a8570` (FIX FIRST round 3,
  PR #425). v5 is SEALED, NOT LAUNCHED; it waits for the owner's new line `CHAT WAVE 3 at 1 USD`.
