# HANDOFF — CAS Harness, 2026-08-19 (Claude -> Codex)

Branch `codex/cascompass-legal-live-source`. Everything below is committed and pushed.

## 0. READ FIRST — MANDATORY
`docs/CAS_HARNESS_SPEC_SHEET.md` (38,000 words, 37 capability rows) is the LIVING master record.
`CLAUDE.md` mandates: read it before ANY harness work; update it IN THE SAME COMMIT AS ANY RESULT.
Use only its own status vocabulary. Never delete a negative. Never upgrade a status without an
artifact path. Numbers exact. Dated change-log row every edit.
(Claude violated this six times on 2026-08-19 and needed a catch-up pass. Do not repeat.)

## 1. THE RECURRING FAILURE — most useful thing to know
EVERY failed experiment failed the same way: A TEST THAT COULD NOT LOSE.
- Atlas rev 0.3: judged a part by the same direction used to find it, hooks still installed.
- Next-board test: follow-ups drawn WITHOUT replacement manufactured the dependence under test.
- SDG corpus: raw character LENGTH predicted the label at 1.0000.
- Weld v1: 4 fatals, all true-by-construction; the matched control's real null was exactly 0.
MITIGATION THAT WORKS: adversarial review BEFORE every spend. Caught 3 fatals on atlas rev 0.3,
2 on rev 0.4, 3 on next-board, 4 on weld v1 — about one dollar spent to kill four bad runs.
WHEN YOU BUILD A CONTROL, PROVE IT CAN FAIL. Compute its true chance rate. If it is 0, it is not
a control.

## 2. WHAT IS DEAD — do not re-attempt
- CAS-PCBA parts inside model weights: NULL @1b, GREY @2.8b, GREY @20B. Rail engagement
  0.469 -> 0.500 -> 0.000 -> 0.170 across four attempts. BOTH sanity checks PASS at 20B
  (MEM p=0.04, CHECK p=0.04) so the instrument is proven and the construct still fails.
  Line CLOSED, spec sheet section 6.7.
- CAS involution pairs geometrically opposite: DISCONFIRMED. CAS pairing ranks 14/14 LEAST
  antipodal on all 43 real layers; centroid cosine POSITIVE +0.32..+0.61.
- Next-board prediction: smoke REJECTED. Persistence 0.5238 beat Markov 0.5079; within-conversation
  shuffle p=0.4279. Conversations are STICKY.
- SDG multi-turn output as a reading corpus: TEMPLATE-rendered, no model called. 38 distinct
  strings; char/word/LENGTH each score 1.0000. Not repairable — the template pool IS the artifact.
- Board-change detection v1: both claims VACUOUS, Gate 0 FAILED. B0 share 0.7325 vs a 0.40 ceiling
  — the 6-code taxonomy yielded TWO live categories on natural conversation.

## 3. WHAT WORKS (validated, artifact-backed, with honest caveats)
- eta->epsilon bridge: +1.412 @20B 40E, 6 model points / 3 families. STATUS IS REAL + OPEN — its
  pre-registered stance-matched control was NEVER RUN, so "a CAS prefix beats a non-CAS prefix"
  is NOT established.
- Subspace ablation: 95.6% -> 66.9%, "107x SNR" — but the closure gate was MISSED ON BOTH
  DISJUNCTS (28.7277pp vs >=30; 66.897% vs <=65%) and 107x is the random MAX (421.97x vs mean).
  Never cite as certification. THERE IS NO ACCEPT ANYWHERE IN THE HARNESS RECORD.
- Drive-local eraser steering: +0.84 p<1e-14 cross-architecture. GLOBAL steering FALSIFIED.
- Output lens: parts 0.610 vs 0.400 null (+0.210); WIRING 0.244 vs 0.052 (~4.7x chance); circuit
  beat single-cell 0.62 vs 0.53. The strongest signal in the project is RELATIONAL, not per-part.
- RPM compiler loop: noetic-compass-scaffold/noetic-compass/rpm_compiler_loop_demo.py, exit 0 on
  real modules. Gaps: string correctors N/W/F/P only; E/S/A raise DeferredAxisError; no auto
  axis->repair dispatcher.
- CAS-Ohm quantifiers: api/cas_ohm/, 39/39 tests. delta_current (identifies_mechanism=False),
  r_hidden (censors at zero-compatible i_obs), maturity_q4 (half-open 2.5/5/7.5 on the
  pre-rounding Decimal). PROPOSED INSTRUMENT — never run against a real I_obs.
- WELD v2: docs/working/gate5_weld/cas_weld_loop_v2.py, LOOP_FALSIFIABLE_AND_HELD. 6 cases, 3 fail
  on purpose; MISLOCALIZATION PROPAGATES TO FAILURE. Control chance rate 1/7 = 0.142857,
  empirically 0.1490 over 2000 draws. ONE axis (A, numeric plane), TWO criteria. J1 (text->CAS),
  J2 (expression->epsilon prefix) and stage 5 are ABSENT, not stubbed.

## 4. OPEN — ranked
1. THE SIX-AXIS BUG BLAST RADIUS — do this first, it is a correctness bug in shipped code.
   Commit f799fe98 fixed _DOMAIN_RE in cas-native/belief/inversion_gate.py: the \b after [PCEO]
   could never match a drive-tagged literal because underscore is a word character, so AXIS W WAS
   DEAD. Every consumer of run_inversion_scan (belief_store.py, data/verifier.py,
   api/routes/mode7.py) has been running a SIX-axis scan whenever an expression carried a drive
   tag. Audit those consumers and any stored verdicts.
2. J1 / J2 — the two joints the weld still lacks. Without them the loop cannot reach a model.
3. detect_pathway_inversion gap — misses any prerequisite inversion whose unsatisfied stage stays
   above 0.5 (A0=0.55 under D=0.80 reads clean).
4. CAS-specificity stays GREY everywhere. Needs a matched-taxonomy control. Do not claim it.
5. Set-valued boards scored by Jaccard against a rate-preserving shuffled null — the successor the
   pilot's own B0/kappa failures point to (PREREG_BOARD_CHANGE_V1 section 16.4). NOT preregistered.

## 5. INFRASTRUCTURE
- H200 pod: q2oqlooejhin7s-64410af4@ssh.runpod.io -i ~/.ssh/id_ed25519. 139.8 GiB, venv
  /workspace/atlas-venv/bin/python. 20B fp32 FITS (76.6 GiB) — that is why bf16 (D33) and its
  calibration (D34) were WITHDRAWN under D57. gpt-neox-20b pinned
  c292233c833e336628618a88a648727eb3dff0a7. Old A40 pod w0pjqx3ndaxfkg was disk-quota dead at 52G;
  everything valuable was rescued.
- SSH transfer that works: tr -d '\r' < script | ssh -tt host   (plain ssh host "cmd" HANGS).
  Files: tar+gzip+base64 tagged @@ per line, grep -o '@@[A-Za-z0-9+/=]*', drop <20-char fragments,
  verify sha256 on BOTH ends.
- Pod bootstrap gotchas (all encoded in component_atlas_v0/bootstrap_20b_pod.sh): ensurepip (the
  venv had no pip and no sklearn); HF_HUB_CACHE not HF_HOME alone (the cache layout is FLAT);
  max_workers=3 (8 workers + anon rate limit wedges the download); setsid + </dev/null (nohup dies
  with the SSH session); A REAL 1G WRITE PROBE — the network FS reported 204T free while a per-pod
  quota blocked every write; accelerate is required for device_map.
- Blind LLM bank: docs/working/gate2_closure/independent_bank/providers.py, keys in
  ~/.cas_llm_keys.env. Four providers verified blind to TKS/CAS. GLM NEEDS semaphore=1 AND A ~7s
  INTERVAL or it 429-death-spirals; it also returns finish_reason=length on about a third of reader
  calls even at max_tokens=20000 — budget repair rounds.
- REASONING MODELS BILL THINKING TOKENS AGAINST max_tokens AND NEVER RETURN THEM. This cost a whole
  pilot: at max_tokens=800 three of four generators were mute. Generation needs >=4000.

## 6. PRESERVED FROM RETIRED PODS (twice, flagship artifacts existed in exactly ONE place)
6269147d eta->epsilon bridge scripts; da425f09 Stage-9 40E scripts including the verifier;
bfa3ad48 W0 prompt-injection bank (640 scenarios). STILL SINGLE-COPY OFF-REPO: the 8,320-scenario
40E fixture and the 4.16 GB NPZ, on D:/tksCAS-archive only.

## 7. LOOSE END
Workflow wf_6f334154-903 (SDG wiring) never reported. It was superseded by the finding that SDG is
template-rendered. DO NOT RESUME IT — the line is dead.
