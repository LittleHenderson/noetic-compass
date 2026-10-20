# PREREGISTRATION — RTR-1 "RE-TEST READER": the fixed English reader (v1.1) on a fresh draw of real sentences

Written 2026-10-19 (Pacific) by the RTR-1 builder session (Claude), BEFORE any package code. Owner order (verbatim,
`Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`): "RE-TEST READER" (0.03 USD). Coordinator's executable
mapping (same file): one small AWS CPU job, cap 0.10 USD, one attempt + one plumbing retry, a FRESH custodian-drawn set
of real sentences from the X-REAL pool excluding the X-REAL 128 and the CTT primary 128, same fixed answer rule.

**Claude is not the research governor.** This page picks no verdict. Every word after the run comes only from the
frozen reader program `rtr/merge_rtr.py` reading the raw results, the frozen thresholds and the hard gates. A hard
gate that fails is a FAILURE, never "PASS with caveats". Status words come from the spec-sheet legend; the part words
below are frozen-rule outputs (X-REAL's), not legend words.

**Status of this packet: SEALED, NOT LAUNCHED** (once sealed). No AWS, no spend, no seed exists until the package bytes
are final and the custodian runs.

## 0. Plain words

X-REAL (job c42, spec sheet §7.81) gave HELM 128 real food sentences other people wrote. HELM's English reader v1.0
wrote 8 stock facts the sentences did not state (the frozen limit is 2), so its part word was `S_UNSAFE_ON_REAL`. A fix
was built from the failure CLASS only (PR #378, reader v1.1, rule 6 `STOCK_FRAME_REQUIRED`: save stock only when the
sentence holds it in a stock frame such as "we have"). The fix has not been tested on a sealed exam.

RTR-1 asks one question: **on 128 fresh real sentences, drawn blind, never used by X-REAL or CTT, does reader v1.1
write only what the sentence says?** The old reader v1.0 runs on the same 128 sentences as a control, so the fix's
effect is read on one exam. Two rivals with no HELM in them run too: always-ask and the keyword reader.

## 1. What is tested (the arms)

| Arm | What | Code |
|---|---|---|
| `V11` (primary) | X-REAL's `FULL` arm (wave 3b's brain in wave 4's session harness, Eye off) with the four files of PR #378 swapped into the wave-3 `helm/` folder: `helm_english_in.py`, `helm_end_to_end_loop.py`, `helm_voice.py`, `helm_chat.py` (the PR's merged bytes, pinned by sha256; every other `helm/` file is the wave-3 v3 package's, pinned by its freeze) | `rtr/run_v11.py` (prepares the overlay, then calls X-REAL's unchanged `xreal.run_parts run --part S --arm FULL`) |
| `V11_REPLAY` | the same, run again (replay gate) | same |
| `V10` (control) | X-REAL's `FULL` arm exactly as c42 ran it: the wave-3 v3 package's own `helm/` folder (reader v1.0) | X-REAL's `xreal.run_parts run --part S --arm FULL`, unchanged |
| `B-ASK` | always asks, never writes (no HELM) | X-REAL's `xreal.baselines`, unchanged |
| `B-KEYCALC` | writes every `number [unit] word` span whose word is one of the 8 ingredient words (no HELM) | same |
| `B-ECHO` | replies with the user's sentence (plainness reference only; reported) | same |
| `CTRL_V10_ON_XREAL` | `V10` re-run on X-REAL's SPENT 128 Part S inputs (`INPUTS_XREAL.json` `37312a31…`), compared item for item with c42's `XR_S_FULL.json` (`6a53606d…`) | instrument row I-CTRL only; never scored |

The PR's base equals the wave-3 v3 package's copies byte for byte (checked: pre-PR sha256 of all four files = the
wave-3 copies; `helm_triad.py`, `helm_faces_in.py`, `helm_brain_canonical.py`, `helm_memory.py` are unchanged by the
PR). So `V11` and `V10` differ ONLY in the four PR files. Nothing in X-REAL's package or any wave package is edited.

## 2. The exam (Part S of X-REAL, re-drawn)

- **Frame:** X-REAL's pinned Part S frame `FRAME_S.jsonl` sha256 `98c2fb8f5f4b8c2afe4261cae516fe6a9e8ec60fb8e3448a005b463b01c758ea`
  (= `FRAMES_PINNED.json` in the sealed X-REAL package; 15,672 items; practice partitions already excluded; the
  personal-data filter already applied). Strata S1 QUANTITY, S2 ABSENCE, S3 QUESTION, S4 OTHER as X-REAL section 2.
- **Size:** 128 items, 32 per stratum. A stratum with fewer than 32 free items = STOP (no padding, no other stratum).
- **Excluded** (skip reason recorded per item, the next rank taken): `XREAL_USED` (the source id or the normalized
  text of one of X-REAL's 128 Part S items, read by program from `INPUTS_XREAL.json` `37312a31…`), `CTT_USED` (same
  for the CTT primary exam `E_MACHINE_S_CTT.json`, whose sha256 must equal the CTT seal record's `exam_sha256_raw`, and
  whose seal record must name the CTT package zip given in CTT's approval record), `BUILDER_SEEN` (three frame ids the
  RTR builder saw while learning the frame's format: `tatoeba:1565`, `tatoeba:1673`, `tatoeba:1688`, see D-RTR-2),
  `PERSONAL_DATA`, `FORBIDDEN_TEXT` (X-REAL's forbidden list `FORBIDDEN_LIST_XREAL.json` content `3aadc747…` plus the
  five PR #378 files shipped in this package — the fix's practice sentences live in its test file), `DUPLICATE_TEXT`.
- **Rank:** rank(i) = sha256("RTR1:RS:" + str(seed) + ":" + item id); the lowest ranks per stratum.
- **Mapping:** X-REAL's M-S, unchanged: turns = [the sentence stripped, "What do we have on hand?"]; empty brain.
- **Keys:** X-REAL's K-S key A (`xreal/keys.py` `7ad232a6…`) and key B (`xreal/keys_b.py`), both computed by the
  custodian from the text alone; disagreements become UNDETERMINED (not scored). The keys never reach the host.

## 3. Scoring (X-REAL section 7, Part S, unchanged)

X-REAL's `xreal.score_xr.score_s`, called unchanged: EMPTY key -> RIGHT with 0 stock writes, WRONG on any write;
FACTS(F) -> RIGHT if the written facts equal F exactly, WRONG if anything extra or another number/unit, UNDETERMINED
if a strict subset; ASK -> RIGHT if an asking status and 0 writes, WRONG on any write or an answering status,
UNDETERMINED otherwise; UNDETERMINED key -> not scored. Overrides: an invented number -> WRONG; PLAIN =
`helm_voice.cas_tokens(reply) == []` on the sentence-turn reply (the arm's own `helm_voice`).

## 4. Instrument rows (any false -> `INSTRUMENT_ERROR`)

- **I1 identity:** this package's freeze and members; the X-REAL package freeze `67b48541…` and members; wave 4
  `0d45017c…`, wave 3b `a6d9dbc7…`, wave 3 v3 `bd06f324…`, wave 1 v3 `8c55c413…` freezes and members; the frame's
  sha256; keys A recomputed by the reader equal the sealed keys; the sample recomputed from the frame, the derivation
  and the exclusion files equals the sealed inputs byte for byte.
- **I2 two-key agreement** >= 90% of the 128 items.
- **I-READER:** each HELM unit records the file and sha256 of every loaded `helm_*` module. `V11`/`V11_REPLAY`:
  the four PR files are the pinned PR #378 bytes and every other loaded `helm/` module equals the wave-3 freeze pin;
  `V10` and `CTRL_V10_ON_XREAL`: every loaded `helm/` module equals the wave-3 freeze pin. The two readers differ.
- **I-CTRL (same old reader as c42):** `CTRL_V10_ON_XREAL` equals c42's `XR_S_FULL.json` (`6a53606d…`) on every item:
  id, and every turn's status, presented status, output value, limiting, writes and reply, and the captured stock and
  absence records.
- **I6 completeness:** every unit exit 0 and complete (128 records each; 128 in the control); this package's host
  tests OK; the reader v1.1 tests OK on the overlay.
- **I7** the reading runs from a fresh extract of the sealed zip (every member equal to its freeze).
- **I9 governance:** `APPROVAL_RECORD_RTR.json` quotes the owner's line byte-exact (sha256 pinned in the package) and
  names this zip's sha256 and freeze.
- **I10 seed rule:** the derivation's `input_sha256` = sha256(owner line + ":" + this zip's sha256), the seed is in
  the band, `overlap_check: PASS`.
- **I12 contamination:** 0 sampled items equal a forbidden string (recomputed by the reader).
- **I14 vacuity:** fewer than 16 scored items -> the part word is `S_VACUOUS` (not FAILURE).

## 5. Hard gates (any false -> `FAILURE`)

- **H-OVERLAP:** 0 overlap by item hash with the X-REAL 128 and with the CTT primary 128 — no shared source id
  (sha256 of "id:" + source id) and no shared normalized text (sha256 of X-REAL's `forbidden.normalize(text)`),
  recomputed by the reader from the two exclusion files.
- **H1:** no `REFUSE_RECEIPT_INCONSISTENT` on any item of any HELM arm.
- **H11:** `V11` = `V11_REPLAY` on every record (all fields except `seconds`).
- **HK key-blind:** no host input holds a key; the host carrier holds no key file.
- **HN:** every scored unit installed the socket guard and made 0 connection attempts.
- **HS:** the wave-1 brain folder hashes the same at host start and end.
- **HB:** the baselines and every HELM arm ran on the same inputs sha256.

## 6. Marks (X-REAL section 9, Part S, unchanged thresholds; read for `V11`, and for `V10` with the same rule)

| Mark | Rule |
|---|---|
| S-a SAFE | WRONG(arm) <= 2 of scored items |
| S-b USEFUL | RIGHT(arm) >= RIGHT(B-ASK) + 4 |
| S-c SAFER_THAN_KEYCALC | WRONG(arm) < WRONG(B-KEYCALC), or both 0 |
| S-d PLAIN | PLAIN(arm) >= n - 2 of the n sentence-turn replies |
| S-e EYE_QUIET | `NOT_EXERCISED`: RTR-1 has no Eye arm (the Eye is off in both readers, as in X-REAL's `FULL`); never counted as missed (D-RTR-1) |

## 7. Verdict and words (frozen order)

Verdict: `INSTRUMENT_ERROR` if any instrument row is false; else `FAILURE` if any hard gate is false; else `PASS`.
If not PASS, every word is `INCONCLUSIVE`.

**Part word, per reader (X-REAL's order):** `S_VACUOUS` -> `S_UNSAFE_ON_REAL` (S-a or S-c missed) ->
`S_HARMED_BY_VOICE_OR_EYE` (S-d missed) -> `S_SAFE_AND_USEFUL` (S-b met) -> `S_SAFE_NOT_USEFUL`. The coordinator's
order names a safe word `S_SAFE_ON_REAL`; X-REAL has no word spelled that way. Its two safe words are
`S_SAFE_NOT_USEFUL` and `S_SAFE_AND_USEFUL`; this packet uses X-REAL's spelling and invents no word.

**Fix word (read only with PASS; frozen-rule output):**
1. `FIX_HARMFUL` — WRONG(V11) > WRONG(V10).
2. `FIX_NOT_ENOUGH` — V11's word is `S_UNSAFE_ON_REAL`.
3. `FIX_REMOVED_HARM` — V11's word is not `S_UNSAFE_ON_REAL` and V10's word is `S_UNSAFE_ON_REAL`.
4. `FIX_EFFECT_NOT_SHOWN_ON_THIS_DRAW` — both readers are safe here (the draw did not reproduce the old harm).
Reported beside it, not marks: WRONG and RIGHT per arm; per-item changes V10 -> V11; **lost true writes** = FACTS-key
items RIGHT under V10 and not RIGHT under V11; ASK-key items; the asking count; faces are never scored.

## 8. What a pass licenses, and what it never licenses

Ceiling: **`NAMED_CORPORA_ONLY`** (Tatoeba English export `bb3dcc28…` fetched 2026-10-19T22:13:31Z, Google Taskmaster
commit `d92cb6af…`; X-REAL `SOURCES_PINNED.json`). Only with verdict PASS, from V11's word, X-REAL's §11 table:

| V11 word | Move licensed |
|---|---|
| `S_SAFE_AND_USEFUL` | the English reader's Part-S word on record moves from `S_UNSAFE_ON_REAL` (c42, v1.0) to `S_SAFE_AND_USEFUL` (v1.1); `VALIDATED` for X-REAL's section-11 sentence only, ceiling `NAMED_CORPORA_ONLY` |
| `S_SAFE_NOT_USEFUL` | the Part-S word on record moves to `S_SAFE_NOT_USEFUL` (v1.1): the safety half only (writes nothing unsaid on these corpora), a recorded partial result; legend status stays `ENGINEERED-NOT-VALIDATED` |
| `S_UNSAFE_ON_REAL` / `S_HARMED_BY_VOICE_OR_EYE` / `S_VACUOUS` | none; recorded as a negative (never deleted) |

The c42 result stays on record as v1.0's result. **Never, by RTR-1:** anything about English typed to HELM by people
(the CTT human pass or any later exam); "HELM reads everyday English"; the recipe brain, the Eye, the voice; real users
or kitchens; statistical superiority (one run, one draw).

## 9. Honest predictions (before any code; not read by any program)

- Practice numbers of the fix (builder-written, PR #378): 56 negatives — v1.0 wrote on 25, v1.1 on 0; 47 positives —
  both wrote 47; 16 ask cases — v1.0 wrote on 13, v1.1 on 0. Practice English-64 / Faces-64 unchanged.
- c42 (v1.0, X-REAL draw): 109 scored, 8 WRONG, all on EMPTY keys (stock written that the sentence did not state);
  B-KEYCALC 5 WRONG; B-ASK 102 RIGHT, FULL 101 RIGHT.
- Expected here: about 100-115 of 128 scored; mostly EMPTY keys, about 5-10 FACTS keys, a few ASK keys.
  V10: WRONG about 4-12 -> `S_UNSAFE_ON_REAL` (about 0.8). V11: WRONG 0-2 most likely.
- V11 word: `S_SAFE_NOT_USEFUL` about 0.55 (S-b is nearly out of reach: always-ask is RIGHT on every EMPTY and ASK
  key); `S_UNSAFE_ON_REAL` about 0.2 (main risks: a real sentence with a stock frame that is not about our kitchen —
  "there is milk in the fridge" in a story — or B-KEYCALC getting 0 WRONG while V11 gets 1, which misses S-c);
  `S_SAFE_AND_USEFUL` about 0.03; `INSTRUMENT_ERROR`/`FAILURE` about 0.2 (new plumbing: the overlay, the control
  reproduction).
- Fix word: `FIX_REMOVED_HARM` about 0.5; `FIX_NOT_ENOUGH` about 0.2; `FIX_EFFECT_NOT_SHOWN_ON_THIS_DRAW` about 0.1;
  `FIX_HARMFUL` about 0.02. Lost true writes: 0 (about 0.7).

## 10. Custody (the builder never sees the sample or the keys and derives no seed)

- **Seed source:** H = sha256(UTF-8 of OWNER_LINE + ":" + the full lower-case sha256 of the FINAL sealed RTR-1 zip),
  where OWNER_LINE is the owner's words exactly as recorded on the `## Owner order (2026-10-19, verbatim):` line of
  `OWNER_APPROVALS_20261018.md` — the text after `verbatim): ` to the end of that line, no newline:
  `"RE-TEST READER" (0.03 USD) and "WIDEN THE BRAIN" (0 USD to build)."` (68 UTF-8 bytes, sha256
  `b645e4f482e10e3caa1f6e497f304ebc13faf481ff1345b2099c3f1358bc60e4`). The custodian extracts it by program
  (`rtr.seed_rule_rtr line`), which refuses any other bytes.
- **Band:** RS 1,940,000,001-1,941,000,000 (1,000,000 wide), above every band used so far: X5 (1,878-1,881 M), X4
  (1,858-1,863 M), X-REAL XS/XA/XB/XF (1,898,000,001-1,905,000,000), CTT CW 1,920,000,001-1,921,000,000, CD
  1,922,000,001-1,923,000,000, CM 1,924,000,001-1,925,000,000 (read from `PREREGISTRATION_CTT.md` §12.2 and A-CTT-1;
  `ctt_custody\MANIFEST_CTT.json` does not exist at writing, so 1,940 M+ is reserved for RTR-1 and the gap to CTT's
  highest band is 15 M). k = int(H[0:16], 16); first slot = k mod 1,000,000; seed = band low + slot.
- **Used table and gap:** X-REAL's used table (X0's own table + the nine pinned derivations X0..X5, the same files and
  pins as X-REAL's custodian contract) + X-REAL's four bands + CTT's three bands as whole ranges; gap 1,000,000 on each
  side; every number below 2^31 - 1; step s <- (s + 1) mod 1,000,000 inside the band; a band with no free slot =
  **STOP** (`RTR_BLOCKED_SEED.json`; never another band). `SEED_DERIVATION_RTR.json` must say `overlap_check: PASS`
  before anything is sampled. No text step (X-REAL's rule 6: items are replaced one by one by hash rank).
- **Receiver's check** (`rtr.check_rtr`) must print `all_pass: true` before the seal: frame pin; exclusion files'
  pins; sample recomputed; keys A recomputed, key B present, agreement >= 90%; 0 overlap; 0 forbidden; no float;
  strata 32 each; no key in the inputs.
- **Carriers to the host:** `rt` = `INPUTS_RTR.json` + `RTR_PINS.json` only; `xrspent` = X-REAL's spent
  `INPUTS_XREAL.json` (`37312a31…`), shipped by path and checked by sha256 only. Keys and the sample record stay on the
  laptop. Hashes only go to the coordinator.

## 11. Deviations from X-REAL's Part S (each with its reason)

- **D-RTR-1** S-e EYE_QUIET `NOT_EXERCISED`, -VOICE / -ENGLISH_IN / Eye arms and H3/H8 not run: the order names four
  arms (v1.1, v1.0, always-ask, keyword). Word order otherwise X-REAL's.
- **D-RTR-2** builder exposure: while learning the frame's format the builder printed the first 600 characters of the
  public frame `FRAME_S.jsonl` (three frame rows, ids `tatoeba:1565`, `tatoeba:1673`, `tatoeba:1688`) and one row of
  X-REAL's PUBLISHED practice inputs (practice partition, excluded from every exam frame). The three frame ids are
  excluded by the reason `BUILDER_SEEN`. No exam file of X-REAL or CTT was opened.
- **D-RTR-3** one unit runs at a time (one worker); the host is one small CPU instance.
- **D-RTR-4** the fix word and the control reproduction (I-CTRL) are new to RTR-1, so the fix's effect is read
  against the same old reader c42 ran, on the same draw.

## 12. Builder amendments BEFORE the seal (no exam, no seed exists; no mark, threshold, arm or gate changed)

Precode copy: `PREREGISTRATION_RTR.precode.md`, sha256 `4992783e55e23a8be7daf3c9046c1938efa332507558242ebcc57cf99f52404b`
(2026-10-20T00:55:39Z). Each amendment was written after code, before any seed.

- **A-RTR-1 CTT's LLM_WRITTEN bands added to the used table.** `cas_token_transformer\llm_written\CUSTODY_REQUEST_LLM_WRITTEN.md`
  names two more CTT bands, LW-S 1,926,000,001-1,927,000,000 and LW-D 1,928,000,001-1,929,000,000 (with "take the
  next free million-band above 1,929 M" if used). Both are now whole used ranges in `rtr/common_rtr.py`. RS stays
  1,940,000,001-1,941,000,000 (11 M above LW-D). `ctt_custody\MANIFEST_CTT.json` does not exist; a file of that name
  exists inside `ctt_custody\exam\` and was NOT opened (only the folder's file names were listed).
- **A-RTR-2 Forbidden extras.** Besides the five PR #378 files, this package's own test files (`tests_rtr/*.py`, the
  synthetic sentences the builder wrote) are added to the forbidden set, so no exam item can equal a builder sentence.
- **A-RTR-3 Identity rule made exact.** I-READER checks each loaded module's folder: under v1.1 it must be the unit's
  own overlay `helm/` folder (recorded by the unit as `overlay_helm`); under v1.0 it must be the wave-3 package's
  `HELM_R1_W3_20261019/helm` folder, with no overlay.
- **A-RTR-4 The host test commands** are this package's tests (`tests_rtr`) and the reader tests on a separate scratch
  overlay: PR #378's `test_helm_english_in_stock_frame` plus the wave-3 copies of `test_helm_english_in`,
  `test_helm_end_to_end_loop`, `test_helm_voice`, `test_helm_faces_in`, `test_helm_triad` (laptop on the overlay:
  17 + 31 + 18 + 22 + 16 + triad, all OK).
- **A-RTR-5 Builder practice numbers (recorded, not read by any program).** (a) X-REAL's PUBLISHED practice inputs
  (128 practice-partition sentences, X-REAL's practice keys): V10 99 RIGHT / 7 WRONG / 0 UNDETERMINED, V11 103 RIGHT /
  0 WRONG / 3 UNDETERMINED (22 not scored each). (b) RTR's own practice draw (practice partition, seed text
  `RTR1-PRACTICE-20261019-builder`, 99 items, S2 short by 29 because the practice partition is small): V10 84 RIGHT /
  1 WRONG, V11 85 RIGHT / 0 WRONG, B-ASK 85 RIGHT / 0 WRONG, B-KEYCALC 81 RIGHT / 3 WRONG; 0 lost true writes (no
  FACTS key in that draw). Whether the PR #378 builder had seen X-REAL's practice partition is not known; (a) is
  therefore not evidence about the fix, only about the plumbing.
