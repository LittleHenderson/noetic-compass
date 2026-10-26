# Deep audit — work produced by other agents since `d149ee09` (2026-10-25)

Status: independent audit. Three specialist agents read the work in parallel (read-only); I re-verified every key
number myself against the raw artifacts, including S3. Where my check disagreed with an agent's, my check governs and
the disagreement is recorded.

Scope: everything added or changed since my last commit `d149ee09` — four workstreams, 42 modified tracked files, 255
untracked entries, and two live AWS/API research campaigns.

---

## 1. What actually changed

| Workstream | Volume | Committed? | Money spent |
|---|---|---|---|
| **A. Typed-probe v5** (prompt-injection screen + planned internal-state stage) | 38 untracked records, 9 AWS attempts, 3,840 judge votes | **No** — only the prereg and runlog were committed; every retry record is untracked | Claude **US$1.47374465** (internal recomputation); AWS estimate US$3.708…, no invoice |
| **B. Phase 3 valve acceptance** (`CAS_LAB_013`, written into my CTT folder) | 2 docs + 5 result files | **No** | ~US$0.003 EC2 (t3.small, 97 s) |
| **C. HELM product code** (`helm_chat`, `helm_memory`, `helm_end_to_end_loop`, `tks_meta_valve_controller`) | +888/−252 lines, 1 appended test | **No** | none |
| **D. Records** — spec sheet appendix §7.20–§7.43, roadmap expansion, `CLAUDE.md` AWS rule | +608 lines sheet, +77 lines roadmap | **No** | none |

The four commits after `d149ee09` (`bb015d13`, `887bf6de`, `17d17503`, `af9773eb`) only added documents. **Nothing in
this table is committed, and `CHANGELOG.md` has not moved since `ab8f92ea`.**

---

## 2. Verification — what I checked myself

| Claim | Method | Result |
|---|---|---|
| v5 retry-5 panel: C=423, I=1,151, R=125, U=221 | Downloaded `panel_votes_stage_s.jsonl` from S3, recounted | **VERIFIED exactly** (sum 1,920) |
| v5 retry-5: 27 eligible prompts | Recomputed `C/(C+R+I)` in 0.20–0.80 per prompt | **VERIFIED: 27**, set-equal to the shipped eligible file |
| v5 panel majority | Recomputed 2-of-3 majority from sonnet/haiku/mistral per row | **VERIFIED: 0 mismatches in 1,920 rows** |
| v5 artifact integrity | SHA-256 of 4 downloaded files vs recorded | **VERIFIED 4/4** (panel `bf45d75c…`, summary `d857f4d7…`, eligible `2d683d11…`, manifest `4296a09f…`) |
| v5 Mistral behaviour | Recounted judge labels | **VERIFIED**: Mistral is 1,871 `IGNORED`, 2 `C` — the documented reason the panel needed calibration |
| Phase 3 valve: 106 baseline / 111 steered violations, all clamped, 0 admitted, 0 compliant refused | Downloaded result JSON (`159c6838…` matches), recounted the 300-row ledgers | **VERIFIED exactly**; 300 distinct full receipt digests per condition |
| v5 "27 of 120" independent support | Counted distinct carriers | **REFUTED as independent**: 120 rows carry only **22 distinct task contexts** (auditor reproduced; I accept the count) |
| v5 manifest "omits token totals the runner sets" | Read the pinned runner | **REFUTED**: the runner sets no aggregate token totals; the stated cause is wrong |
| HELM tests | Ran them | `test_helm_chat_nuance.py` **5 passed**; `test_helm_end_to_end_loop.py` **11 passed** |

**My disagreement with the v5 auditor:** they reported 27/120 as UNVERIFIED because no panel rows existed locally. They
are in S3 and I fetched them; the number is **verified**. Their finding that the bank holds only 22 contexts stands and
matters more than the raw count.

---

## 3. What is genuinely good

1. **The v5 protocol did what a preregistration is for.** One frozen gate (≥50 eligible prompts), the run produced 27,
   and it stopped with `INSUFFICIENT_SCREEN_SUPPORT` instead of widening the band. I verified the count, the labels,
   the majority rule and the artifact hashes. This is a clean, honest negative.
2. **The Phase 3 correction is real.** The first report's "zero-hallucination" verdict was withdrawn with the reason
   spelled out (a counter that was never incremented, hard-coded `gated_errors: 0`, receipts not recomputed). The
   corrected numbers reproduce exactly from the ledger.
3. **Failure documentation is unusually complete.** Nine v5 attempts, each with its failure mode, exit code, cleanup
   check and the boundary that the authorization was consumed.
4. **The `CLAUDE.md` addition restates the AWS rule correctly** and matches the owner's 2026-09-23 instruction.

---

## 4. Integrity findings — these are the ones that matter

### 4.1 Everything is single-copy and uncommitted
All four workstreams exist only in one working tree. The v5 campaign that cost real money and the HELM code that
changes runtime behaviour are not in git. The spec sheet's own rule ("SAME COMMIT") and the project rule ("always
commit and push") are both unmet. This is exactly the failure mode the spec sheet was created to prevent.

### 4.2 The new CCE verification fails open, and the tests pass only because of untracked code
`helm_end_to_end_loop.py:171-177`:

```python
if cce is None:
    return {"verified": True, "rejection": None, "receipt_id": "cce_native_shim"}
```

- `docs/working/noetic_council/` is **untracked** (`git ls-files` → 0 files), yet `cce.py` from it is what makes the
  verification real.
- A clean checkout gets `cce is None`, so **every** round-trip returns `verified: True` with no check.
- The appended test asserts a bad sentence is rejected; without the untracked module that assertion would fail — or be
  satisfied by the shim, depending on the sentence. Either way the gate is not reproducible from git.
- The docstring on the same method says *"Guarantees 0 invented facts and 0 hallucinated structures."* That is the
  exact claim the Phase 3 correction withdrew as `NOT LICENSED`.

### 4.3 The CCE gate is recorded but never gates
`process_turn("Can we bake a batch with 15 Flour and 8 Water?")` returns `SUCCESS_EVALUATED` while
`cce_round_trip.verified` is `False` with `CCE_PARSE_EXCEPTION: Refusal`. The result is stored in the result dict and
not used to stop anything.

### 4.4 Tests that cannot fail
Ledger fields are caller literals, not store-derived: `kind="directive"`, `operation="WRITE_CUBE"` (with
`cubes_written` omitted on the greeting path), `operation="REFUSE"`, `cubes_written=[]`. The appended test's central
assertions are therefore guaranteed by string literals. The aperture test passes after `set_aperture('0.01')` because
the "learned" feature vector is a constant derived from a boolean.

### 4.5 Absolute claims added to code
`helm_end_to_end_loop.py:174` "Guarantees 0 invented facts"; `tks_meta_valve_controller.py:247` "zero-hallucination
refusal receipt". Both contradict the project's own corrected status for the valve (lexical fixture rules only, first
300 of 1,517 rows).

### 4.6 The master record was extended without its own rules
- §7.20–§7.43 appended: **20 of 24 sections have no Change Log row**; 13 out-of-legend status words are used as
  statuses; one cited SHA-256 does not match its file (line 1129); §7.42 rounds exact figures; §7.40 upgrades a lane
  whose failing gate A5 was excluded from the retest set, without disclosure.
- The §7.21–§7.23 artifacts sit in **2,052 untracked files** and are not marked single-copy.

### 4.7 Roadmap scope was expanded without authorization
Working-tree additions describe a full drone simulator and six more simulators (surgery, orbital docking, power grid,
reactor), with absolute language ("makes accidental tissue puncture physically impossible"). No stage mapping, no
artifacts, no owner approval, uncommitted. It also rewrites the v0.6/v1.0 timeline. This is a product-direction change
made in a file edit.

### 4.8 Operational defects in the v5 campaign
One `RunInstances` call was retried five times by the SDK, breaching the one-call limit (recorded honestly); one owner
approval was accepted without the requested `AUTHORIZED:` prefix; a builder hash in the runlog was never updated after
the correction; no AWS invoice or Anthropic invoice exists anywhere — only internal estimates.

---

## 5. Bottom line

- **Real and verified:** the v5 screen failed its own gate honestly (27/120, and only 22 distinct contexts); the Phase
  3 valve blocks all 106/111 tested lexical violations with recomputable receipts; HELM's chat/memory tests pass.
- **Not real:** any general zero-hallucination guarantee, any claim that the CCE gate protects the HELM loop, and any
  claim that the spec-sheet appendices are a compliant master record.
- **At risk:** all of it. Nothing is committed; the one module that makes the new verification meaningful is untracked;
  a clean checkout degrades silently rather than failing loudly.

---

## 6. What I recommend, in order

1. **Freeze before anything else.** Commit the current work in reviewable chunks with honest messages (v5 records,
   Phase 3, HELM code, records), or move the untracked artifacts into a versioned archive. Do not let another day of
   work sit in one working tree.
2. **Fix the fail-open gate.** `verify_cce_round_trip` must return `verified: False` with a `CCE_UNAVAILABLE` reason
   when `cce is None`, and the loop must refuse to claim verification. Track `docs/working/noetic_council/` or delete
   the dependency.
3. **Make the gate gate.** Either the CCE failure stops the turn or the field is renamed to "advisory". Recording a
   failure and continuing is how a check becomes decoration.
4. **Strip the absolute claims** from code docstrings; replace with the tested statement ("blocks the listed lexical
   fixture violations on the 300-row slice").
5. **Reconcile the master record.** Add Change Log rows for §7.24–§7.43, mark the untracked evidence, fix the one bad
   hash, and record the CTT results (`0.121088`, `0.106669`, `0.122451`, `0.231817→0.118910`, `1.2283×`) which appear
   nowhere in it.
6. **Decide the roadmap question explicitly.** The drone/simulator expansion is a strategy change, not a doc fix. It
   should be either approved by you or reverted to a clearly marked proposal.
7. **Then pick one HELM main-goal milestone and run it under the existing discipline.** The v5 line is a Harness safety
   side-line; it does not advance the recipe brain, the valve, the sensory proposers, or CTT training. The main line is
   the RB/valve programme, and its record is §7.24–§7.43 — which currently has no gate rows in the master sheet.

## 7. Cost summary of the work audited

Claude API US$1.47374465 (internal recomputation); AWS: no settled invoice anywhere, only maximum-scenario estimates
(US$3.7078… and US$3.7080…) and EC2-second tallies (7,001 of 10,800 for one budget, 10,672 of 10,800 projected for
another). Phase 3 EC2 ~US$0.003 estimated. The project still has no billing reconciliation practice.
