# Gate 2 Item 2 — Withdrawn-`ACCEPT` Root-Cause Report

## Status block

| Field | Value |
|---|---|
| **Closes** | **Not item 2.** This closes exactly one of item 2's two clauses: clause 1, "Complete the withdrawn-`ACCEPT` root-cause report without conflating defects" (`docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:192-197`). Clause 2 — "tombstone every packet/read/share/export/anchor path and add regression tests preventing revival" — is **open** and is a code-landing task. Item 2 stays open. See F.2. |
| **Gate 2 definition** | "small-model semantic authority, matched controls, uncertainty, claims reconciliation, and withdrawn-`ACCEPT` root cause close" → `0.46` (`docs/working/cas_harness_production_todo.md:954`) |
| **Date** | 2026-07-24 |
| **Report claim state** | `accepted` — this is a reconstruction from retained artifacts, not a new experiment. No number in it was produced by a run performed for this report. |
| **Subject claim state** | `withdrawn` — **at least** two Stage 9 40E Evidence Packets emitted `verdict: ACCEPT`; the two in the registry were both withdrawn 2026-06-03; effective verdict `FLAG_FOR_HUMAN_REVIEW`. The hedge is the project's own: adjudication row 1.2 says "**At least** two machine packets and derivative claims were affected" (`docs/working/CAS_HARNESS_AUDIT_REMEDIATION_20260719.md:26`, quoted in full at C.6). Completeness of the withdrawn set is `unavailable` — see G.3. |
| **Remedy claim state** | `open` — the withdrawal tombstone is designed and tested but **not deployed anywhere**. Two named regressions (RT-02, RT-05) remain `open`. See Section F. |
| **Does this report close item 2?** | **No.** It delivers the report half. The tombstone-and-regression-test half is a code-landing task that has not landed. See Section F.2. |

### Explicit claim-state line

> The withdrawal is `accepted` and recorded. The historical forensic bytes (`historical_packet.sha256`) are `real` and independently hash-verified in this pass; the registry's canonical fingerprint arrays — the digests `runtime_policy` actually binds on — are `accepted`, read but **not** recomputed (C.5.1). Uniqueness / CAS-specificity is `OPEN / NOT LICENSED`. Per-customer production `ACCEPT` is `NOT LICENSED`. The tombstone registry is `open` (built, tested, **not landed**). The deployed-revival and anonymous-share-bypass regressions are `open`. **No standing `ACCEPT` exists anywhere in the project record.**

---

### BOXED NOTE 1 — do not conflate with the W0 licence withdrawal

> This report concerns the **Stage 9 40E Evidence Packet `ACCEPT` withdrawal of 2026-06-03**.
>
> It is **a different record** from the withdrawal documented in
> `.claude/worktrees/integration/noetic-compass-scaffold/noetic-compass/docs/working/hidden_prompt_injection_w0_license_withdrawn_20260618.md`:
>
> | | This report | The W0 licence withdrawal |
> |---|---|---|
> | Date | 2026-06-03 | 2026-06-18 (`:3`) |
> | Subject | Stage 9 40E Evidence Packet verdict | `internal_w0_prompt_injection_detection` licence |
> | Model | GPT-NeoX-20B, Pythia-160M | Qwen2.5-1.5B layer 18 |
> | Mechanism | candidate-only cover stamped `verified` | character n-gram surface control **beat** the hidden state: hidden BA `0.897` vs char n-gram text `0.925 / 0.931` dedup (`:17-19`) |
> | Outcome | verdict → `FLAG_FOR_HUMAN_REVIEW` | licence → `OPEN / NOT LICENSED` (`:4`) |
>
> Different subject, different date, different mechanism, different failure surface. **Never merge them into one narrative.**

### BOXED NOTE 2 — the 2026-07-24 prompt-injection experiments are out of scope

> Four prompt-injection experiments were run earlier on 2026-07-24 against a self-authored paraphrase of Gate 2. Prompt-injection detection is **Gate 3** (`docs/working/cas_harness_production_todo.md:955`). Those experiments are honest and preserved, they carry **no Gate 2 credit**, and they are **not cited as evidence anywhere in this report**.

### BOXED NOTE 3 — the Condition-3 GREY is a comparator result, not a withdrawal

> The 2026-06-03 Condition-3 matched-taxonomy comparator returned `GREY` (Section B, B2). A `GREY` comparator verdict is **an experimental result that contributed to the withdrawal decision**. It is not itself a withdrawal, and must not be counted as a third withdrawn artifact.

---

## Section A — Original verdict logic, the record, and the absent uniqueness/MTC gate

**Claim state of this section: `real` (mechanism reproduced from git objects and on-disk bytes this pass).**

### A.1 The producer defect — a class-count test standing in for a control proof

The Stage 9 40E packet merger decided whether a `control_proof` chip was `verified` in `_control_chip_status`. Pre-fix logic, recovered from the diff hunk `@@ -643,7 +643,25 @@` of commit `337d0c29b0822228dbfbb35dfc9873ca69453f1d`:

```python
if isinstance(class_count, int) and class_count >= 40:
    return "verified"
```

File: `live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py`, function `_control_chip_status`.

That is the entire mechanism. **Counting 40 cover classes was treated as proof that a matched control had been run and passed.** No check existed on whether the cover report claimed validation, or whether any matched ablation had executed at all.

The cover report actually consumed declares its own status plainly. In
`C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass/docs/working/gpt_neox_20b_stage9_original_40e_neuron_covers_top8_20260528T0210Z.json`:

- `:36989` — `"class_count": 40`
- `:37051` — `"status": "candidate_cover_discovery_completed"`

A report whose own status string contains the word **candidate** satisfied the `>= 40` test and was stamped `verified`.

The post-fix logic (same commit) inverts the default to `present` and requires the cover report to affirmatively declare validation, rejecting any status containing `"candidate"` and admitting only `matched_ablation_validated`, `control_validation_completed`, or `controls_validated`.

Correcting commit: `337d0c29b0822228dbfbb35dfc9873ca69453f1d`, dated **2026-06-03**, subject *"fix(evidence): anchor Pythia-160M Stage 9 packet honestly as FLAG, not ACCEPT"* (verified by `git log -1 --format='%H %ad %s' --date=short`).

### A.2 The uniqueness / MTC gate was ABSENT, not weak

This distinction is load-bearing and was verified directly rather than inferred.

Commit `24e15a9b5f7c4632246dd14d9cf261d0c32bc5d7`, dated **2026-06-03**, subject *"fix(evidence): require uniqueness proof for Stage 9 accept"*, touches 5 files: `+356 insertions, -1 deletion`.

Occurrence counts for `UNIQUENESS_STATUSES|_uniqueness_gate` in `live-trace-worker/scripts/build_stage9_40e_verifier_report.py`:

| Revision | Occurrences |
|---|---:|
| `24e15a9b^` (immediately before) | **0** |
| `24e15a9b` (immediately after) | **8** |

Occurrences of `uniqueness` in `live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py` at `24e15a9b^`: **0**.

The symbols `PASSING_UNIQUENESS_STATUSES`, `FAILING_UNIQUENESS_STATUSES`, and `_uniqueness_gate` are introduced by that commit as `+` lines. **At the time both `ACCEPT` verdicts were emitted, no uniqueness or matched-taxonomy gate existed in either the verifier report builder or the packet merger.** The gate did not fail; there was nothing to fail.

The commit's own CHANGELOG entry states the resulting tri-state design: uniqueness proof present-and-passed permits `ACCEPT`; missing keeps the report at `FLAG_FOR_HUMAN_REVIEW`; explicitly failed returns `SUPPRESS`.

### A.3 The two affected records

Both hashes below were **recomputed independently in this pass** and match the values recorded in the withdrawal registry exactly.

**Record 1 — GPT-NeoX-20B**

| Field | Value |
|---|---|
| `trace_id` | `stage9-40e-original-baseline-readout-20260527` (packet `:507`, `:584`) |
| Model | `EleutherAI/gpt-neox-20b` (packet `:184`, `:204`, `:481`) |
| Packet | `C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass/docs/working/gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json` |
| Verdict | `"verdict": "ACCEPT"` at `:508` (also `:522`, `:576`) |
| Packet sha256 | `2b402931b35f7527d0baf76467a9812d7c8d9da232688c2a106238b5b5c7cf6d` |
| Verifier report | `..._verifier_report_20260528T0455Z.json`, `"verdict": "ACCEPT"` at `:26` |
| Report sha256 | `79d140f0d5028578d8c776eb6069cbad53a4733e0553004aa9ecb8366374a5f0` |
| Claim state | `withdrawn` |

**Record 2 — Pythia-160M**

| Field | Value |
|---|---|
| `trace_id` | `pythia-160m-stage9-40e-readout-20260531` (`:500`, `:577`) |
| Path | `docs/working/pythia160m_gate1/pythia160m_stage9_40e_evidence_packet.json` |
| Pre-fix revision | `18dc6236a193e43097129819f688269c0c25a0be` |
| Pre-fix verdict | `"verdict": "ACCEPT"` at `:499` (also `:513`, `:567`) |
| Pre-fix sha256 | `0af6964f9446e61376530ff9f3d305540f6eaed709e29fbfa2d02cf37e706f4e` |
| Corrected verdict (on disk) | `"verdict": "FLAG_FOR_HUMAN_REVIEW"` at `:501` (also `:515`, `:569`) |
| Corrected sha256 | `64a9de4d56ce0bee14ca8108cf97b92df23ad11ca4d4784ac0cbaf4ad0788c87` |
| Claim state | `withdrawn` |

### A.4 New finding this pass — the `ACCEPT` appeared only in the third packet revision

This was not in the material handed to me and materially sharpens the causal account. Three GPT-NeoX packet revisions are retained side by side in the same directory:

| Packet revision | Verdict | Line |
|---|---|---:|
| `..._evidence_packet_20260527.json` | `FLAG_FOR_HUMAN_REVIEW` | 261 |
| `..._evidence_packet_20260528T0215Z.json` | `FLAG_FOR_HUMAN_REVIEW` | 401 |
| `..._evidence_packet_20260528T0455Z.json` | **`ACCEPT`** | 508 |

The neuron-cover report is timestamped `20260528T0210Z` — between revisions 1 and 2, and before revision 3.

**Reading, stated with its uncertainty:** the packet was `FLAG_FOR_HUMAN_REVIEW` through two revisions and flipped to `ACCEPT` only in the revision that merged the candidate cover report. This is consistent with, and localizes, the `_control_chip_status` defect in A.1. It is a **strong ordering inference from retained artifacts**, not a recovered execution log. The command line that produced revision 3 was not located this pass — see Section G.

### A.5 Contributing factors, verbatim from the withdrawal registry

From `docs/working/evidence_packet_withdrawals_20260719.json` (readable only as a git object in commit `846ee041`; see Section C.5):

Record 1 (`stage9-40e-original-baseline-readout-20260527`):
- "candidate-only control_proof was stamped verified"
- "the 20B 40E causal result missed its pre-registered absolute gate but the verifier used a different signal-to-noise guard"
- "the decision was not bound to an immutable policy/preregistration hash"

Record 2 (`pythia-160m-stage9-40e-readout-20260531`):
- "candidate-only control_proof was stamped verified"
- "the same trace id was retained when the packet was regenerated with the corrected FLAG_FOR_HUMAN_REVIEW disposition"
- "a previously stored anchor can contain the superseded ACCEPT bytes"

The second factor on record 2 is a live hazard, not history: **the corrected packet reuses the withdrawn packet's `trace_id`.** Identity alone cannot distinguish the withdrawn artifact from its correction; only content fingerprints can. Any future replay or re-anchor that mints packets under these trace IDs risks re-materializing the withdrawn artifact class under a fresh-looking identity.

### A.6 Date precision — three values, none asserted over the others

The emission date of the GPT-NeoX `ACCEPT` is not stated identically across artifacts. All three retained values:

| Source | Value |
|---|---|
| `trace_id` suffix | `20260527` |
| Packet filename timestamp | `20260528T0455Z` |
| Summary prose (`docs/working/cas_harness_synopsis_20260630.md:137`) | `2026-05-28` |

These are mutually consistent with a run executed 2026-05-27 and a packet written 2026-05-28. **No commit introducing the packet was located in this pass.** All three values are recorded; none is asserted as *the* date.

---

## Section B — The later evidence that forced withdrawal

**Claim state of this section: every item below is `real` and `negative`. None of it supports any claim. It is recorded solely as the evidence that made the `ACCEPT` unsupportable.**

Withdrawal date: **2026-06-03**.

### B1 — The `control_proof` was candidate cover discovery only

Commit `337d0c2` records that `control_proof` is candidate cover discovery only, matched-ablation not run, and therefore recorded-but-not-verified. Corroborated on disk by the cover report's own `"status": "candidate_cover_discovery_completed"` (A.1). Claim state: `real`.

### B2 — Condition-3 blind matched-taxonomy comparator returned `GREY`

`docs/working/cas_harness_production_todo.md:17907`, dated 2026-06-03, GPT-NeoX-20B on the replacement H200 pod:

- Result `GREY` (`pass: false`, `grey: true`, `falsify: false`, `blocked: false`)
- CAS passed hidden-readout-over-text and flat-lacunarity gates
- **Failed** the preregistered matched-readout margin against the coherent NC40 control
- CAS accuracy `0.5347222222222222` versus NC40 accuracy `1.0`
- Observed margin `-46.52777777777778pp` against a required `+5pp`
- Archived: `D:\tksCAS-archive\condition3_mtc_comparator_20260603\`

The same line records: "Pythia-160M remains `FLAG_FOR_HUMAN_REVIEW`; uniqueness remains open." Claim state: `real`, negative.

### B3 — Earlier archived Condition-3 MTC also failed comparative specificity

`docs/working/cas_harness_production_todo.md:17469`: the archived Condition-3 MTC result is GPT-NeoX-20B, not Pythia-160M, and "it failed CAS comparative specificity (`cas_element` hidden acc about 6.53% while matched controls were about 84.72%)." The same line instructs: "Do not use that archived MTC result as Pythia uniqueness proof." Claim state: `real`, negative.

### B4 — The 20B 40E causal ablation MISSED its pre-registered gate

`docs/working/cas_harness_synopsis_20260630.md:101`:

- 40-Element at GPT-NeoX-20B drops **95.625% → 66.897%**, a **28.73 pp** drop
- Random-matched controls: `0.068 pp` mean — a 107× signal-to-noise ratio
- Pre-registered gate: **≥30 pp drop / ≤65% floor**
- "**narrowly missed** by 1.27–1.90 pp and documented openly as a near-miss (not a pass)"

This matches the registry's contributing factor verbatim: the causal result missed its pre-registered absolute gate, but the pre-fix verifier applied a different signal-to-noise guard. **The threshold is quoted exactly as pre-registered and is not reinterpreted here.** A 107× signal-to-noise ratio is a real measurement; it is not the pre-registered criterion, and substituting it for the criterion is precisely the defect. Claim state: `real`, near-miss, **not a pass**.

### B5 — Correct discipline applied: real positive ablation evidence still did not restore `ACCEPT`

`docs/working/cas_harness_production_todo.md:17898`, dated 2026-06-03 — Pythia-160M activation-level matched ablation computed from the archived `.npz` without rerunning the model:

- Label-specific cover drop `0.054762` versus wrong-cover drop `0.003572`
- Random-control max drop `0.005953`
- Union cover drop `0.108334` versus union random-control max `0.0`
- Archived: `D:\tksCAS-archive\pythia160m_activation_cover_ablation_20260603\`
- Recorded conclusion: "This does not make the WORM-retained packet `ACCEPT`; uniqueness/MTC remains open."

This is the discipline working as intended: genuinely positive, cleanly controlled ablation numbers were still held insufficient because the *specific* missing proof — matched-taxonomy/uniqueness — remained missing. Claim state: `real`, positive, **and explicitly insufficient**.

### B6 — The corrections that landed

| Commit | Date | Effect |
|---|---|---|
| `337d0c29b0822228dbfbb35dfc9873ca69453f1d` | 2026-06-03 | Producer fix: candidate-status cover reports can no longer be stamped `verified` |
| `24e15a9b5f7c4632246dd14d9cf261d0c32bc5d7` | 2026-06-03 | Adds the tri-state uniqueness gate to **both** the verifier report builder and the packet merger |

Recorded at `docs/working/cas_harness_production_todo.md:17897`: "hardened the Stage 9 40E `ACCEPT` gate so matched-ablation/control evidence alone cannot mint final `ACCEPT`; explicit matched-taxonomy/uniqueness proof is now required by both the verifier report builder and packet merger."

**Resulting effective verdict for both traces: `FLAG_FOR_HUMAN_REVIEW`.**

Public-facing statement of the same fact, `docs/working/cas_harness_synopsis_20260630.md:137`: "No `ACCEPT` verdict stands in the entire project record." And `docs/working/cas_harness_executive_summary_20260630.md:20`: "No standing `ACCEPT` verdict exists."

---

## Section C — The candidate-only revival and anonymous-share bypass regressions

**Claim state of this section: both findings are `open`. Both were verified line-exact against live code in this pass.**

Discovery: 2026-07-19 PDT / 2026-07-20 UTC.
Discovery artifact: `C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass/docs/working/CAS_HARNESS_REDTEAM_REAUDIT_20260719.md`.

This section answers the question the roadmap item poses: **how did a withdrawn claim become reachable again, and by which path?**

### C.1 RT-02 — CRITICAL: the deployed system can revive the withdrawn `ACCEPT`

Finding at `:96-116`; dashboard row at `:68` reads: "Protected/live master can still revive a withdrawn GPT-NeoX `ACCEPT` after valid WORM anchoring."

**The path, verified against the live working clone this pass:**

1. `api/routes/cas_harness_audit.py:209` — `REFERENCE_TARGET_EVIDENCE_PACKET_TRACE_ID = "stage9-40e-original-baseline-readout-20260527"`. The deployed reference target **is** the withdrawn trace. Verified at `:209` in both the live working clone and protected master `81b5c18bd83e1f01ccd398dcad3865a674335b7f`; `:207` is `REFERENCE_TARGET_MODEL_ID = "EleutherAI/gpt-neox-20b"` and `:208` is `REFERENCE_TARGET_PROVIDER`. **Correction of record:** an earlier revision of this report cited `:207`, inherited verbatim from the red-team's `#L207` permalink at `CAS_HARNESS_REDTEAM_REAUDIT_20260719.md:103`. The substantive claim was and is true; the line number was copied rather than checked, which is exactly the failure mode G.9 warns about. Line numbers below are re-derived, not inherited.
2. `api/routes/evidence.py:508` — `_STAGE9_40E_ORIGINAL_TRACE_ID = "stage9-40e-original-baseline-readout-20260527"`; `:509-511` — `_STAGE9_40E_ORIGINAL_PACKET_FILENAME = "gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json"`. That trace maps to the `ACCEPT`-bearing packet file.
3. `api/routes/evidence.py:624-641` — `public_stage9_40e_packet_payload_for_trace` applies `_stage9_40e_review_projection` **only when `_stage9_40e_packet_is_worm_retained(anchored)` is false**. Its own docstring states the rule: a normal read "must not expose that as the packet's active verdict *unless the packet has a persisted, re-verifiable WORM/Object-Lock anchor*."
4. `api/services/cas_harness_evidence_withdrawals.py` — **does not exist** in the live working clone (`ls`: No such file or directory), and `git ls-tree` over protected master `81b5c18bd83e1f01ccd398dcad3865a674335b7f` returns **0** matches.

**The inversion:** the downgrade is conditioned on the *absence* of WORM proof. WORM anchoring is a durability guarantee — it proves bytes were retained unaltered. It is not a semantic guarantee, and it says nothing about whether the verdict inside those bytes was ever earned. Because deployed master has no withdrawal registry to consult, **successfully anchoring the packet removes the only thing suppressing its `ACCEPT`.** The safety property is strongest exactly when the artifact is least verified, and disappears once the artifact is well-retained.

**Two facts recorded explicitly, and not softened in either direction — the same disclosure RT-05 receives in C.3:** (a) **RT-02 was not demonstrated by execution.** Nothing in this pass anchored a packet, minted a WORM receipt, or observed an `ACCEPT` surface from a deployed read. The finding is a *code-reading* inference over the four steps above — each step's bytes verified, the composition asserted. It is corroborated by the red-team's independent reading at `CAS_HARNESS_REDTEAM_REAUDIT_20260719.md:107` ("Once a valid WORM receipt exists, the raw `ACCEPT` can surface again because deployed master has no withdrawal registry"), which is a second reading, not a reproduction. (b) **The reachability precondition is asserted, not cited.** That *some actor could actually obtain a valid WORM/Object-Lock anchor for this packet on deployed master* is not traced here to any anchoring-permission, credential, or authorization path. The downstream half — that once such an anchor exists the projection no longer fires — is verified at step 3. Whoever lands the tombstone should treat the precondition as an open question worth its own check, not as established.

Claim state: `open`. Recorded as **P0** at `docs/working/cas_harness_production_todo.md:2258-2261`.

### C.2 RT-02's own statement of what the candidate registry does *not* cover

Quoted from `:110-113`, the candidate registry is "necessary, but incomplete":

- "normal Evidence Packet reads and new-anchor paths consult it;"
- "anonymous Evidence Packet shares do not;"
- "the offline Stage 9/40E report builder does not consult it;"
- "it is a targeted recall for known fingerprints, not a general semantic re-verification of every legacy `ACCEPT`."

The fourth bullet is the one most easily lost. **The registry contains exactly 2 records.** No artifact was found in this pass establishing that only two legacy `ACCEPT` packets ever existed. The set of withdrawn traces is itself of unproven completeness — see Section G.

### C.3 RT-05 — HIGH: the candidate fix's own anonymous-share path bypasses it

Finding at `:152-161`. Red-team's own citation: `api/services/evidence_shares.py:379-407` and `api/routes/evidence_shares.py:221-241`.

**Verified line-exact this pass, in the live clone:**

- `api/services/evidence_shares.py:342` — `def fetch_shared_packet(`
- `:379-383` — loads via `self.repository.load_packet_with_content_sha256(...)`
- `:403-407` — comment "The repository returns a fresh JSON mapping. Nothing in this path writes packet bytes or changes the packet mapping." then `return packet`
- `:128` — `def create_share(` — likewise applies no projection
- `api/routes/evidence_shares.py:206` — `@router.get("/shared/{share_id}")`, `def fetch_shared_evidence_packet(...)`, docstring: "Anonymous packet fetch with one deliberately non-leaky negative response."

Additionally verified: at candidate commit `846ee041`, `api/services/evidence_shares.py` contains **0** occurrences of `withdraw` (case-insensitive), and does not appear among the 6 non-test modules importing `cas_harness_evidence_withdrawals`.

The red-team's plain-English framing (`:155`): "the main records desk stamps a report 'recalled,' but the public photocopy window hands out the unstamped original."

**Two facts recorded explicitly, and not softened in either direction:** no affected live share was proven, and the candidate code is not deployed. RT-05's own conclusion nevertheless stands: "The defect nevertheless means the candidate fix cannot be merged as complete."

**Required fix, verbatim from `:159`:** "validate the raw stored-byte hash first, then apply the withdrawal projection at share creation and retrieval. Cover withdrawn fingerprints, corrected fingerprints, unknown variants, wrapped packets, and already-created shares."

Claim state: `open`. Recorded as **P0** jointly with RT-02 at `docs/working/cas_harness_production_todo.md:2258-2261`.

### C.4 RT-06 — a live contradiction that will fight the fix

Finding at `:163-171`. `scripts/verify_evidence_anchor_deployed.py:207-226` **still requires an `ACCEPT`**, and `docs/DEPLOYMENT.md` still instructs operators to run it, while the candidate policy forces the same fragment to `FLAG`. Its tests pass "because they preserve the stale expectation."

Recorded here because it is a direct hazard to landing item 2: **tombstoning without fixing RT-06 will break documented deployment verification — creating pressure to "fix" it by relaxing the tombstone.** Required fix per `:171`: separate "WORM write/readback works" from "the scientific verdict is accepted."

### C.5 The tombstone exists, and is not deployed

| Property | Verified value |
|---|---|
| Registry module | `noetic-compass-scaffold/noetic-compass/api/services/cas_harness_evidence_withdrawals.py` |
| Sidecar | `noetic-compass-scaffold/noetic-compass/docs/working/evidence_packet_withdrawals_20260719.json` |
| Tests | `noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_evidence_withdrawals.py` |
| Adjudication doc | `docs/working/CAS_HARNESS_AUDIT_REMEDIATION_20260719.md` — **note: not scaffold-prefixed**, unlike the three above |
| Reachable in | commit `846ee041d32944d606d8555cc015f701ec5b94c9`, dated 2026-07-19, subject *"fix: fail closed CAS audit evidence and scaling"*, branch `codex/audit-remediation-20260719` |
| Readable from | `C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/integration` (git objects only — **not checked out**) |
| On protected master `81b5c18b…` | **absent** (`git ls-tree \| grep -c` → `0`) |
| On `origin/master` | **absent** (`0`) |
| In live working clone | **absent** (`ls` → No such file or directory) |
| On GitHub | neither commit, branch, nor PR (`docs/working/cas_harness_production_todo.md:2254-2256`) |

Registry contents, verified: `"schema_version": "cas_harness_evidence_packet_withdrawal_registry.v1"`, **exactly 2 records**, both `"original_verdict": "ACCEPT"` → `"effective_verdict": "FLAG_FOR_HUMAN_REVIEW"`, both `"reason_code": "candidate_control_proof_misclassified"`, both `"withdrawn_on": "2026-06-03"`.

Per-record `runtime_policy`, verbatim:

```
"public_reads":         "PROJECT_AS_FLAG_FOR_HUMAN_REVIEW",
"audit_decisions":      "PROJECT_AS_FLAG_FOR_HUMAN_REVIEW",
"new_anchor_writes":    "REFUSE_UNLESS_RECOGNIZED_CORRECTED_FLAG",
"existing_worm_anchor": "DOES_NOT_RESTORE_WITHDRAWN_VERDICT"
```

The last line is the direct answer to RT-02. It is written, tested, and **not running anywhere.**

#### C.5.1 Two hash families — only one of them was recomputed this pass

The registry binds by `trace_id` **and** by content fingerprint — the design response to the trace-ID reuse named in A.5. But it carries **two distinct families of digest**, and this report verified only the first. Conflating them would overstate what was checked, so they are separated here.

**Family 1 — raw-file forensic digests, under `historical_packet.sha256`. `real`, independently recomputed this pass, exact match.**

| Record | `historical_packet.path` | `historical_packet.sha256` | Recomputed |
|---|---|---|---|
| 1 — GPT-NeoX-20B | `docs/working/gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json` | `2b402931b35f7527d0baf76467a9812d7c8d9da232688c2a106238b5b5c7cf6d` | **match** |
| 2 — Pythia-160M | `docs/working/pythia160m_gate1/pythia160m_stage9_40e_evidence_packet.json` @ `18dc6236…` | `0af6964f9446e61376530ff9f3d305540f6eaed709e29fbfa2d02cf37e706f4e` | **match** |

**Family 2 — canonical fingerprints, the arrays `runtime_policy` actually binds on. `accepted` — read from the registry, NOT recomputed this pass.**

| Record | `withdrawn_packet_canonical_sha256` | `recognized_corrected_packet_canonical_sha256` |
|---|---|---|
| 1 — GPT-NeoX-20B | `["b5f3635f2636cca4ec6e72af143c938f5c1f8d581d62ceaa20dc3c3bfb58c099"]` | `[]` — **empty** |
| 2 — Pythia-160M | `["6c2b7918738064c3e91134a85012c51e666cdcd2569946d544a73bf0df2cd0bb"]` | `["e84f21d401e53ce9b9e97d499e3964854c2098191c2d6813b5674086a9389c38"]` |

`b5f3635f…`, `6c2b7918…`, and `e84f21d4…` were **not** independently recomputed. Reproducing them requires re-executing the registry's packet canonicalization (each record also carries the same value under `historical_packet.canonical_packet_without_hashes_sha256`), which this pass did not do. **So: the forensic bytes are verified; the fingerprints the runtime policy matches on are recorded-but-not-reproduced.** An earlier revision of this report attached "match my independent recomputation exactly" to the fingerprint arrays while quoting Family-1 values — that sentence claimed verification of the binding mechanism it had not performed, and is corrected here.

#### C.5.2 Two asymmetries between the records, material to the fix

- **Record 1's `recognized_corrected_packet_canonical_sha256` is an empty array.** No recognized corrected packet exists for the GPT-NeoX trace. Combined with `new_anchor_writes: "REFUSE_UNLESS_RECOGNIZED_CORRECTED_FLAG"`, the policy therefore refuses **every** new anchor write for that trace — there is no fingerprint that could satisfy the exception. That is fail-closed and correct, but it is a stricter runtime behaviour than "refuse unless corrected," and anyone landing the tombstone should expect it rather than read it as a bug.
- **Record 2's `correcting_commits` lists only `337d0c29b0822228dbfbb35dfc9873ca69453f1d`.** Record 1 lists both `337d0c29…` and `24e15a9b5f7c4632246dd14d9cf261d0c32bc5d7`. The B6 table above states both commits landed on 2026-06-03 and describes what each does; it should not be read as a claim that the registry attributes both commits to both records. It does not.

### C.6 The adjudication record, verbatim

`docs/working/CAS_HARNESS_AUDIT_REMEDIATION_20260719.md:26` (inside commit `846ee041`):

> | 1.2 withdrawn ACCEPT | CONFIRMED historical verifier defect plus live artifact risk | CRITICAL | Candidate control discovery was misclassified as validated proof. At least two machine packets and derivative claims were affected. Correcting commits `337d0c2` and `24e15a9b` exist. A machine-readable withdrawal tombstone is required so the historical GPT-NeoX packet can never be re-anchored or displayed as ACCEPT. No standing ACCEPT exists. |

Note the project's own hedge: "**At least** two machine packets and derivative claims were affected."

---

## Section D — TOMBSTONE TABLE

One row per packet / read / share / export / anchor path.

**Legend.** *Tombstone*: `candidate-only` = withdrawal projection implemented in commit `846ee041` but **not deployed anywhere**; `NONE` = no projection exists in any tree. *Regression test*: names an existing test, or `unavailable` — meaning the test does not exist to be cited. **No row anywhere is marked "deployed," because the tombstone has not landed.**

**Revision stamp (required by G.9).** Unless a row says otherwise, **every source and test line number in this table indexes commit `846ee041d32944d606d8555cc015f701ec5b94c9`** — written `@846ee041` in the table. Section C by contrast cites the **live working clone** for the deployed-code findings (`evidence.py:624-641`, `cas_harness_audit.py:209`, `evidence_shares.py:342-407`). The two sets are not interchangeable: `evidence.py:643 @846ee041` is the withdrawal branch that does not exist in the live clone at all. Where a number happens to hold in both trees, the row says so — rows 11-14 were checked at `846ee041` **and** in the live clone and are identical in both, which is expected, since those files are exactly the ones `846ee041` did not touch (that is RT-05).

| # | Path / surface | Tombstone? | Regression test? | Exact test that must be added if absent |
|---|---|---|---|---|
| 1 | `api/routes/evidence.py:643-648 @846ee041` — withdrawal branch inside `public_stage9_40e_packet_payload_for_trace`, reached by public packet read `GET /evidence/{trace_id}` (route handler `:1450-1451 @846ee041`) | candidate-only | `tests/test_evidence_routes.py::test_evidence_get_stage9_20b_packet_public_read_enforces_withdrawal` (`:99`); `::test_evidence_get_withdrawn_packet_stays_flag_with_existing_anchor_receipt` (`:126`) | — (must be re-run post-landing) |
| 2 | `api/routes/evidence.py:1563 @846ee041` (`withdrawal_blocking_new_anchor`) — new anchor write `POST /evidence/{trace_id}/anchor` → HTTP 409 `packet_withdrawn` | candidate-only | `tests/test_evidence_routes.py::test_evidence_anchor_allows_corrected_flag_packet_and_rejects_withdrawn_accept` (`:729`) | — |
| 3 | `api/services/cas_harness_static_evidence_anchor.py:79 @846ee041` — static anchor store write | candidate-only | `tests/test_cas_harness_static_evidence_anchor.py::test_withdrawn_accept_variant_is_refused_before_any_store_write` (`:112`) | — |
| 4 | `api/services/cas_harness_verdict_runner.py:81 @846ee041` — final verdict runner | candidate-only | `tests/test_cas_harness_verdict_runner.py::test_withdrawn_trace_cannot_be_reactivated_by_accept_and_worm_proof` (`:135`) | — |
| 5 | `api/services/cas_harness_verifier_decision_adapter.py:105 @846ee041` — packet → verifier decision | candidate-only | `tests/test_cas_harness_verifier_decision_adapter.py::test_withdrawn_historical_stage9_accept_is_forced_to_human_review` (`:213`); `::test_superseded_pythia_accept_trace_is_forced_to_human_review` (`:226`); `::test_candidate_only_stage9_control_cannot_accept_under_a_new_trace` (`:238`) | — |
| 6 | `api/routes/cas_harness_audit.py:2995,2999,3001 @846ee041` — audit payload + run route | candidate-only | `tests/test_cas_harness_audit.py::test_reference_target_uses_corrected_withdrawn_trace_and_stays_review_only` (`:1328`); `::test_reference_target_trace_from_public_alpha_console_stays_review_only` (`:1396`); `::test_run_route_enforces_withdrawal_for_bundled_stage9_40e_accept` (`:1497`); `::test_run_route_never_reactivates_withdrawn_gpt_accept_when_worm_anchored` (`:1545`); `::test_run_route_never_reactivates_superseded_pythia_accept_from_anchor` (`:1593`) | — |
| 7 | `scripts/anchor_stage9_40e_packet.py:111 @846ee041` — CLI anchor | candidate-only | `tests/test_anchor_stage9_40e_packet.py::test_cli_refuses_bundled_withdrawn_accept_before_anchor` (`:15`); `::test_cli_refuses_superseded_pythia_accept_variant_before_anchor` (`:36`) | — |
| 8 | `atlas-viewer/src/components/audit/AuditVerdictExplainer.tsx` — UI verdict explainer | candidate-only | `AuditVerdictExplainer.test.tsx` — `it('explains a withdrawn ACCEPT as fail-closed even when historical proof was present')` | — |
| 9 | `atlas-viewer/src/pages/AuditConsolePage.tsx` — UI console default target | candidate-only | `AuditConsolePage.test.tsx` — `it('loads the corrected Stage 9 Pythia packet and explains the withdrawal')` | — |
| 10 | `api/services/cas_harness_evidence_withdrawals.py @846ee041` — the registry itself + forensic-byte integrity | candidate-only | `tests/test_cas_harness_evidence_withdrawals.py` — **7 tests** (`:54`, `:63`, `:91`, `:124`, `:140`, `:158`, `:174`), incl. `test_historical_accept_artifacts_remain_byte_identical_for_forensics`, `test_anchor_wrapper_cannot_escape_trace_scoped_withdrawal`, `test_unknown_or_accept_variant_of_pythia_trace_fails_closed` | — |
| 11 | `api/services/evidence_shares.py:128` `create_share` (identical at `@846ee041` and in the live clone) | **NONE** | `unavailable` | `test_create_share_refuses_or_projects_withdrawn_packet` — assert a share created for either withdrawn trace either fails closed or stores the projected `FLAG_FOR_HUMAN_REVIEW` view. Must cover: withdrawn fingerprints, corrected fingerprints, unknown variants, wrapped packets. |
| 12 | `api/services/evidence_shares.py:342-407` `fetch_shared_packet` (identical at `@846ee041` and in the live clone) | **NONE** | `unavailable` | `test_fetch_shared_packet_applies_withdrawal_projection_after_hash_validation` — assert stored-byte hash is validated **first**, then the projection is applied, so the returned payload never carries `ACCEPT`. Must cover already-created shares. |
| 13 | `api/routes/evidence_shares.py:206-241` `GET /shared/{share_id}` (anonymous; route at `:206`, handler `:207` — identical at `@846ee041` and in the live clone) | **NONE** | `unavailable` | `test_anonymous_shared_packet_endpoint_never_serves_withdrawn_accept` — HTTP-level assertion on the anonymous route; response body must contain no `ACCEPT` for either withdrawn trace. |
| 14 | `api/routes/evidence_shares.py` — create (`:114-119`), metadata (`:151-155`), revoke (`:178-182`) (identical at `@846ee041` and in the live clone) | **NONE** | `unavailable` | `test_share_lifecycle_routes_enforce_withdrawal` — one test per verb; metadata must not leak a withdrawn verdict string. |
| 15 | `live-trace-worker/scripts/build_stage9_40e_verifier_report.py` — offline verifier report builder | **NONE** | `unavailable` | `test_offline_verifier_report_builder_refuses_withdrawn_trace` — builder must consult the registry and refuse (or emit `FLAG_FOR_HUMAN_REVIEW`). Verified at `846ee041`: contains `PROTECTED_FORENSIC_OUTPUTS` (2 occurrences) but **0** withdrawal references. |
| 16 | `live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py` — packet merger | **NONE** | `unavailable` | `test_packet_merger_refuses_to_regenerate_withdrawn_trace_as_accept` — carries the `337d0c2` producer fix and the `24e15a9b` uniqueness gate, but does not consult the withdrawal registry. |
| 17 | `api/services/cas_harness_merged_evidence_packets.py` — fleet merged-packet writer | **NONE** | `unavailable` | `test_merged_packet_writer_projects_withdrawn_component_verdicts` |
| 18 | `api/services/cas_harness_evidence_anchor.py` — second anchor service | **NONE** | `unavailable` | `test_second_anchor_service_refuses_withdrawn_packet` — does not import the withdrawals module at `846ee041`. |
| 19 | `api/services/cas_harness_evidence_object_store.py` — object-store load/store | **NONE** | `unavailable` | `test_object_store_load_marks_withdrawn_packets` — the lowest-level read; the share path reaches packets through here. |
| 20 | `api/routes/evidence.py:1469-1474 @846ee041` — `POST /evidence/{trace_id}/verify` (decorator `:1469`, path literal `"/{trace_id}/verify"` `:1470`, handler `async def verify_evidence_packet` `:1474`) | **NONE** | `unavailable` | `test_verify_endpoint_reports_withdrawn_status_for_withdrawn_trace` — **not named by RT-02**; identified independently as an uncovered packet-bearing read surface. **Citation corrected:** an earlier revision gave `:1458-1463`, which falls inside the `GET /{trace_id}` handler (`:1450-1451 @846ee041`) — i.e. row 1's *already-covered* surface, which would have destroyed this row's entire point. The verify endpoint is a genuinely distinct and genuinely uncovered surface; only the line numbers were wrong. |
| 21 | `scripts/verify_evidence_anchor_deployed.py:207-226` — deployment verifier | **contradicts** the tombstone (RT-06) | **9 tests exist and encode the stale expectation** — red-team table `:359`: "Deployment-verifier tests \| 9 passed \| Tests encode stale requirement for unverified worker `ACCEPT`" | `test_deployment_verifier_requires_flag_not_accept_for_unverified_fragment` — and the stale assertion must be **removed**, not preserved. This is the one row where existing tests are a liability rather than an absence. |
| 22 | `api/routes/export.py:24-25 @846ee041` — `GET /assessments/export` | **N/A** | N/A | **None required.** Verified: exports saved *assessments* for an authenticated API key, not Evidence Packets. Recorded so the roadmap's "export" term is answered, not silently dropped. |
| 23 | General semantic revalidation of every legacy `ACCEPT` packet | **NONE** | `unavailable` | `test_unregistered_legacy_accept_packet_fails_closed_by_default` — a default-deny rule. RT-02 `:113`: the registry is "a targeted recall for known fingerprints, not a general semantic re-verification of every legacy `ACCEPT`." |
| 24 | Cross-path recall (all surfaces, one trace) | **NONE** | `unavailable` | `test_withdrawn_trace_is_unreachable_as_accept_across_every_surface` — parametrized over read, share, export, offline report, verify, and anchor. Red-team table `:358`: "Each subsystem passes separately; **no cross-path recall test**." |

**Tally, derived by counting the rows rather than estimated.**

- **Rows 1-10 — covered `candidate-only`: 10 paths, exactly 24 named tests** (2 + 1 + 1 + 1 + 3 + 5 + 2 + 1 + 1 + 7 = 24). All 24 exist at the cited lines at `@846ee041`, and none of them exists in any deployed tree. An earlier revision said "~22 tests"; the number is exactly derivable from the rows and is 24.
- **Rows 11-21 + 23-24 — uncovered: 13 paths, 0 withdrawal regression tests.** One qualification, which the earlier "0 tests" phrasing wrongly flattened: **row 21 is not an absence, it is a contradiction.** Nine tests do exist there and they *pass by asserting the stale `ACCEPT` requirement* (red-team `:359`). Rows 11-20 and 23-24 (12 paths) have zero tests of any kind on the withdrawal question; row 21 has nine that must be corrected rather than added to.
- **Row 22 — `N/A` with reason** (exports carry assessments, not Evidence Packets).

---

## Section E — Regression tests: what exists, and the load-bearing caveat

**Every test named in rows 1-10 lives only in unmerged commit `846ee041`, which GitHub does not have** (`docs/working/cas_harness_production_todo.md:2254-2256`: "GitHub has neither commit, branch, nor PR").

> **The deployed system currently has zero withdrawal regression coverage.** Not weak coverage. Zero. The withdrawals module is absent from protected master `81b5c18b`, from `origin/master`, and from the live working clone.

Verified module import graph at `846ee041` — exactly 6 non-test modules import `cas_harness_evidence_withdrawals`:

```
api/routes/cas_harness_audit.py
api/routes/evidence.py
api/services/cas_harness_static_evidence_anchor.py
api/services/cas_harness_verdict_runner.py
api/services/cas_harness_verifier_decision_adapter.py
scripts/anchor_stage9_40e_packet.py
```

`api/services/evidence_shares.py` is **not** among them. That absence is RT-05.

### Test-count evidence is `accepted`, not reproduced

These figures were read from the project record. **They were not re-executed in this pass**, and do not meet the Gate 2 exit clause's requirement of "independently reproducible raw evidence":

| Source | Figure |
|---|---|
| `docs/working/cas_harness_production_todo.md:2348-2352` | API/service suite: **2,857 passed, 11 skipped, 3 expected failures, 0 failed**; offline probe-worker tree: **240 passed**; withdrawal/verdict Audit Console: **30 passed** |
| Red-team table `:356-358` | **121 passed** (withdrawal/planner/feasibility/distributed-audit/dependency-readiness) — "Does not cover anonymous-share withdrawal bypass"; **19 passed** account/anonymous-scope; **18 passed** share+withdrawal — "no cross-path recall test" |

The 121-passed row is the sharpest statement available of the gap: the withdrawal suite is green **and** does not test the bypass.

### Forensic-byte immutability is load-bearing and currently unprotected

`test_historical_accept_artifacts_remain_byte_identical_for_forensics` pins the historical packets' bytes. My independent recomputation confirms the GPT-NeoX packet still hashes to `2b402931…` — the chain is intact today.

**Any pass that "tidies," regenerates, or lets the offline report builder overwrite these packets destroys the forensic chain.** The `PROTECTED_FORENSIC_OUTPUTS` guard in `build_stage9_40e_verifier_report.py` exists for exactly this — and it is also unmerged, so **the protection is currently absent from the live tree.**

---

## Section F — Status ledger and what this report does NOT establish

### F.1 Claim states

| Item | Claim state |
|---|---|
| The withdrawal itself | `accepted` — recorded across summaries, todo, adjudication row 1.2 |
| Historical forensic bytes (`historical_packet.sha256`) | `real` — the four raw-file digests independently recomputed this pass, match the registry exactly (C.5.1, Family 1) |
| Registry canonical fingerprints (`*_canonical_sha256` arrays) | `accepted` — read from the registry, **not** recomputed; reproducing them needs the packet canonicalization re-executed (C.5.1, Family 2) |
| Producer defect + absent uniqueness gate (Section A) | `real` — reproduced from git objects |
| Section B evidence | `real`, and **negative**; supports nothing |
| Tombstone registry design | `real` but **NOT DEPLOYED** → `open` |
| RT-02 deployed revival | `open` (P0 / CRITICAL) — established by **code reading, not execution**; the reachability precondition (that a valid WORM anchor is actually obtainable for this packet on deployed master) is asserted, not cited (C.1) |
| RT-05 anonymous-share bypass | `open` (P0 / HIGH) |
| RT-06 deployment-verifier contradiction | `open` (HIGH) |
| Uniqueness / CAS-specificity | `OPEN / NOT LICENSED` |
| Per-customer production `ACCEPT` | `NOT LICENSED` |
| Standing `ACCEPT` anywhere in the record | **none exists** |
| Test counts in Section E | `accepted` — recorded, not reproduced |

### F.2 Item 2 is NOT closed by this report

The roadmap item has two halves (`:192-197`):

1. "Complete the withdrawn-`ACCEPT` root-cause report without conflating defects" — **this document.**
2. "Tombstone every packet/read/share/export/anchor path and add regression tests preventing revival" — **not done.**

Half 2 is a **code-landing task on a tree GitHub does not have.** Thirteen paths in Section D carry no tombstone and no test. Two P0 regressions remain open. **A completed report must not be recorded as a completed item.**

Closing item 2 requires, at minimum: land the tombstones (including the RT-05 share-path projection and the RT-06 deployment-verifier correction), add the Section D rows 11-21 and 23-24 tests, and re-run the suites as independently reproducible evidence.

### F.3 Threshold integrity

No threshold in this report was reinterpreted, weakened, or restated. The pre-registered causal gate is quoted exactly as written (**≥30 pp drop / ≤65% floor**, missed by 1.27–1.90 pp). The pre-registered comparator margin is quoted exactly (**+5pp** required, `-46.52777777777778pp` observed). **No criterion was rewritten after outcomes were known** — indeed the record shows the opposite discipline in B5, where real positive ablation numbers were held insufficient because the specific required proof was still missing.

### F.4 Constraint on Gate 2 item 8

Item 8 replays saved fixtures through the live Evidence Packet path. Because both withdrawn traces are **reused identities** (A.5), item 8 must run **only after item 2's tombstones land**, and must assert that every replayed packet resolves to `FLAG_FOR_HUMAN_REVIEW` — **never a fresh verdict**.

The hazard behind that constraint is **analysis, flagged as such**: "replaying before the tombstones land risks re-materializing the withdrawn artifact class under a fresh-looking identity" is this report's inference, not a quoted finding. What it rests on is quoted and verified — the registry's own record-2 contributing factors, "the same trace id was retained when the packet was regenerated with the corrected FLAG_FOR_HUMAN_REVIEW disposition" and "a previously stored anchor can contain the superseded ACCEPT bytes" (`docs/working/evidence_packet_withdrawals_20260719.json`, quoted verbatim in A.5). The inference from those two facts to the replay hazard is mine. Claim state: `open` (a precaution to observe), not `real` (a measured outcome).

---

## Section G — What is still unknown

Every entry is `unavailable`, with what was searched. **Nothing below was filled in by inference.**

1. **Exact original-emission date of the GPT-NeoX `ACCEPT`** — `unavailable` as a single authoritative value. Three retained values recorded in A.6 (`20260527` / `20260528T0455Z` / `2026-05-28`). Searched: packet contents, filename timestamps, summary prose. **No commit introducing the packet was located.**

2. **The command invocation that produced packet revision 3** (`20260528T0455Z`, the one bearing `ACCEPT`) — `unavailable`. The three-revision ordering in A.4 is inferred from retained artifacts and file timestamps, not from a recovered execution log. Searched: the packet directory listing and the cover-report timestamp.

3. **Completeness of the withdrawn set** — `unavailable`. The registry holds exactly 2 records; the adjudication says "**at least** two machine packets and derivative claims were affected." **No artifact was found establishing that only two legacy `ACCEPT` packets ever existed.** RT-02 `:113` states the registry is a targeted recall, not a general revalidation. Any claim of completeness would be fabricated.

4. **Which derivative claims were affected** — `unavailable`. Row 1.2 says "derivative claims were affected" without enumerating them. No enumeration was located in `docs/working/` or `project_handoffs/`.

5. **Any live/deployed re-verification after 2026-07-20** — `unavailable`. This pass was read-only over local sources; no network verification was performed. The most recent recorded provider binding is `2026-07-20T05:23:07Z` (`docs/working/cas_harness_production_todo.md:2251-2256`, service `srv-d9bijbjtqb8s73cn4n20`, deploy `dep-d9cei8d8nd3s738mism0`, commit `81b5c18b…`). Anything after that date is `unavailable`.

6. **Any artifact changing the RT-02 / RT-05 dispositions after 2026-07-20** — `unavailable`; none found. Searched: `grep -rn` over `docs/working/` and `project_handoffs/` for withdraw / WITHDRAWN / ACCEPT / uniqueness / MTC / candidate-only / revival / anonymous-share / bypass / tombstone / packet; `git log --all` in both the tksCAS repo and the noetic-compass clone; `.claude/worktrees/` enumeration. **Both findings remain `open`.**

7. **Whether any live anonymous share of a withdrawn packet was ever created** — `unavailable`. RT-05 `:157` states no affected live share was proven. Determining this requires live object-store inspection, which was not performed and is not authorized by this task.

8. **`docs/working/pythia160m_gate1/` scope correction** — the directory does **not** exist in the tksCAS repo: `ls` returns "No such file or directory" and `git ls-files | grep -c pythia160m_gate1` returns `0`. It **does** exist at `C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass/docs/working/pythia160m_gate1/`. **Any statement that this directory "does not exist" is true of the tksCAS repo only** and must carry that scope, or it reads as a stronger absence than the evidence supports.

9. **Path-ambiguity hazard** — four trees hold near-identical code: `C:/Users/wakil/OneDrive/Desktop/tksCAS`, `.../.claude/worktrees/integration/…`, `C:/Users/wakil/CAS-Harness-Run/…`, and `D:/tksCAS-archive/`. Path prefixes differ **within a single commit**: at `846ee041` the registry module is scaffold-prefixed (`noetic-compass-scaffold/noetic-compass/api/services/…`) while the adjudication doc is not (`docs/working/CAS_HARNESS_AUDIT_REMEDIATION_20260719.md`). This cost a failed lookup during this pass. Every citation in this report carries its absolute root or its exact in-commit path for that reason.

---

## Sources

Every file consulted in producing this report. Absolute roots given; `R1`/`R2`/`R3` abbreviate the three trees.

- `R1` = `C:/Users/wakil/OneDrive/Desktop/tksCAS`
- `R2` = `C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass`
- `R3` = `C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/integration` (git object store; commit `846ee041` read via `git show`)

**Controlling text and project record (`R1`)**
- `R1/docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md` — `:192-197` item 2, `:217-220` exit clause
- `R1/docs/working/cas_harness_production_todo.md` — `:954`, `:2251-2256`, `:2258-2261`, `:2274-2276`, `:2305-2320`, `:2345-2352`, `:17413`, `:17469`, `:17896`, `:17897`, `:17898`, `:17907`
- `R1/docs/working/cas_harness_synopsis_20260630.md` — `:97`, `:99`, `:101`, `:137`
- `R1/docs/working/cas_harness_executive_summary_20260630.md` — `:20`
- `R1/docs/working/gate2_closure/item2_withdrawn_accept_evidence_index_20260724.json` — gathering index (all load-bearing entries re-verified independently)

**Historical packets and forensic bytes (`R2`)**
- `R2/docs/working/gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json` — `:184`, `:204`, `:481`, `:507-508`, `:522`, `:576`, `:584`; sha256 recomputed
- `R2/docs/working/gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0215Z.json` — `:401`
- `R2/docs/working/gpt_neox_20b_stage9_original_40e_evidence_packet_20260527.json` — `:261`
- `R2/docs/working/gpt_neox_20b_stage9_original_40e_verifier_report_20260528T0455Z.json` — `:26`; sha256 recomputed
- `R2/docs/working/gpt_neox_20b_stage9_original_40e_neuron_covers_top8_20260528T0210Z.json` — `:36989`, `:37051`
- `R2/docs/working/pythia160m_gate1/pythia160m_stage9_40e_evidence_packet.json` — `:500-501`, `:515`, `:569`; sha256 recomputed
- Same path at git revision `18dc6236a193e43097129819f688269c0c25a0be` — `:499`, `:513`, `:567`; sha256 recomputed from the git object

**Correcting commits (`R2` git history)**
- `337d0c29b0822228dbfbb35dfc9873ca69453f1d` — diff of `live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py`, hunk `@@ -643,7 +643,25 @@`
- `24e15a9b5f7c4632246dd14d9cf261d0c32bc5d7` — `--stat`, full diff, and before/after symbol counts in `build_stage9_40e_verifier_report.py` and `merge_stage9_40e_evidence_packet.py`

**Live deployed code (`R2` working clone)**
- `R2/api/routes/cas_harness_audit.py` — `:209` (`REFERENCE_TARGET_EVIDENCE_PACKET_TRACE_ID`; also confirmed at `:209` on protected master `81b5c18b…`. Not `:207`, which is `REFERENCE_TARGET_MODEL_ID` — see the correction of record in C.1)
- `R2/api/routes/evidence.py` — `:506-511`, `:620-650`
- `R2/api/services/evidence_shares.py` — `:128`, `:342`, `:377-383`, `:403-407`
- `R2/api/routes/evidence_shares.py` — `:204-212`
- `R2/api/services/cas_harness_evidence_withdrawals.py` — **verified absent**

**Red-team re-audit (`R2`)**
- `R2/docs/working/CAS_HARNESS_REDTEAM_REAUDIT_20260719.md` — `:68`, `:96-116` (RT-02, incl. `:103` the `#L207` permalink whose off-by-2 this revision corrects, `:107` the independent WORM-revival reading, `:110-113` the registry's own coverage limits), `:152-161` (RT-05, incl. `:155`, `:157`, `:159`), `:163-171` (RT-06), `:354-360` (verification table: `:356` 121 passed, `:357` 19 passed, `:358` 18 passed / no cross-path recall, `:359` 9 passed / stale `ACCEPT` expectation)

**Candidate remediation commit `846ee041d32944d606d8555cc015f701ec5b94c9` (via `R3`)**
- `docs/working/CAS_HARNESS_AUDIT_REMEDIATION_20260719.md` — `:25-26` (row 1.2)
- `noetic-compass-scaffold/noetic-compass/docs/working/evidence_packet_withdrawals_20260719.json` — `schema_version`; both records; full `runtime_policy` (identical across both records); `historical_packet.{path,sha256,git_blob_sha1,git_revision,canonical_packet_without_hashes_sha256}`; `withdrawn_packet_canonical_sha256` and `recognized_corrected_packet_canonical_sha256` arrays (record 1's corrected array is empty); `correcting_commits` (record 1 lists two commits, record 2 lists one). Family-1 digests recomputed; Family-2 digests read only — see C.5.1
- `noetic-compass-scaffold/noetic-compass/api/services/cas_harness_evidence_withdrawals.py` — existence + import graph
- `noetic-compass-scaffold/noetic-compass/api/services/evidence_shares.py` — 0 withdrawal references
- `noetic-compass-scaffold/noetic-compass/api/routes/export.py` — `:24-25`
- `noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/build_stage9_40e_verifier_report.py` — `PROTECTED_FORENSIC_OUTPUTS` present, 0 withdrawal references
- Tests: `tests/test_cas_harness_evidence_withdrawals.py` (`:54,63,91,124,140,158,174`); `tests/test_evidence_routes.py` (`:99,126,729`); `tests/test_cas_harness_static_evidence_anchor.py` (`:112`); `tests/test_cas_harness_verdict_runner.py` (`:135`); `tests/test_cas_harness_verifier_decision_adapter.py` (`:213,226,238`); `tests/test_anchor_stage9_40e_packet.py` (`:15,36`); `tests/test_cas_harness_audit.py` (`:1328,1396,1497,1545,1593`)
- `git ls-tree` over `81b5c18bd83e1f01ccd398dcad3865a674335b7f` and `origin/master` — registry absent from both

**Non-conflation reference (`R3` working tree)**
- `R3/noetic-compass-scaffold/noetic-compass/docs/working/hidden_prompt_injection_w0_license_withdrawn_20260618.md` — `:4`, `:9`, `:17-19`, `:33`, `:51`, `:115`
