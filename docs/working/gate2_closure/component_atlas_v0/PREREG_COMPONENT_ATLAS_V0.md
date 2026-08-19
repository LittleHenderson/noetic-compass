# PREREG — COMPONENT ATLAS v0 (rev 0.2)

Preregistration for the first typed map from a model's internal parts to CAS-PCBA component labels, judged by directional ablation predictions against matched controls.

- Date frozen: 2026-08-18 (rev 0.2)
- Status at freeze: PREREGISTERED, NOT RUN
- Companion script (frozen with this doc): `component_atlas_v0.py` (same directory). The script's `PROMPT_FRAMES`, `F5_HEDGED`, `F5_PLAIN`, `AMBIVALENT`, `MEM_ITEMS`, `HEDGE_WORDS` and threshold constants are the executable copies of the banks and thresholds in this document; the script writes sha256 of its own bank JSON (including the fit/judge split indices) into the report for binding.
- Report artifact: `atlas_v0_report.json` (written by the script)

## Revision history / deviations log

- **rev 0.1** (2026-08-18, earlier): first freeze. Superseded BEFORE any run.
- **rev 0.2** (2026-08-18): full redesign in response to the adversarial review of rev 0.1. Every FATAL and MAJOR point is fixed (not merely rebutted); minors fixed or dispositioned. Point-by-point disposition in Section 9. No experiment was executed under rev 0.1; no results existed at revision time, so this is a pre-run design change, not a post-hoc one.
- (Any post-freeze change to prompts, thresholds, layers, or statistics must be logged here with date and reason before results are read.)

---

## 0. FRAME (owner-ratified, exact)

Parts are the MODEL'S (discovered functionally), names are OURS (CAS-PCBA types), ablation is the JUDGE. A label sticks only if its preregistered directional ablation prediction holds vs matched controls. Language discipline: "causally supports the labeling", never "found THE neurons". This does NOT claim the model encodes CAS.

Every result sentence in the report uses "causally supports the <TYPE> labeling of <part>" or "does not support". No sentence may say "found", "is", "the circuit", or "the neurons" about an internal part.

## 1. Model and environment

- Model: `EleutherAI/pythia-1b`, revision PINNED to `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2` (the Stage 27N pinned revision). Unpinned load => report is stamped `claim_eligible: false` (fail-closed, per the eraser-contract discipline).
- Standard-config facts used (verified-consistent with repo evidence, not repo-measured): 16 layers, hidden 2048, 8 heads/layer (head_dim 256), MLP intermediate 8192.
- Environment: RunPod research venv `/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python`, `HF_HOME=/workspace/cas-hf-cache`, single A-series GPU, dtype float32, `attn_implementation="eager"`, `use_safetensors=True`. No internet beyond the HF cache (`--local-files-only` supported). The venv is assumed to carry torch/transformers/sklearn per Stage 27 history; this is verified at run start, not in this prereg (Section 9, minor).
- Determinism: single `--seed` (default 0) drives `torch.manual_seed`, `np.random.default_rng`; generation is greedy (`do_sample=False`); every random control trial uses `default_rng(seed*10000 + offset + trial)`; the fit/judge split uses `default_rng(seed+123)`.
- Runtime budget: < ~30 min full run on one A-series GPU (~470 greedy generations of 24 tokens on pythia-1b fp32, plus one clean forward per generation and the small discovery/sanity forwards). `--smoke` runs the identical pipeline at tiny n (8 frames, 2 control trials, 10 new tokens) for mechanical validation only — smoke numbers are never evidence.

## 2. Target signals, prompt banks, and the fit/judge split

Two drives with validated drive-local channels from Stage 27O/27P: **F5 Agency** (primary) and **F2 Wisdom** (contrast rail).

### 2.1 Matched-surface minimal-pair frames (n=24; the F5/F2/neutral banks)

Every prompt is `prefix + slot + suffix`. The three class variants of a frame share every character outside the one slot, so surface separability of the banks is confined to the slot by construction (Section 6). Each slot filler is unique across frames (lexical diversity: no repeated agency/deliberation verb).

| # | Prefix | F5 slot (Agency) | F2 slot (Wisdom) | Neutral slot | Suffix |
|---|---|---|---|---|---|
| 1 | When the server crashed at midnight, the on-call engineer | took charge of | methodically diagnosed | stood beside | the failing cluster, and then |
| 2 | Facing the flooded basement, Priya | seized a pump and drained | mapped the drainage paths beneath | glanced across | the lowest room, and then |
| 3 | With the deadline moved up a week, Marcus | committed the team to | weighed every tradeoff inside | picked up a copy of | the revised plan, and then |
| 4 | After the committee stalled again, Dana | made the final call on | reasoned step by step through | set down her notes on | the budget question, and then |
| 5 | When the trail markers disappeared, the guide | forged ahead along | studied the contours of | paused beside | the northern ridge, and then |
| 6 | Hearing the alarm repeat, the technician | overrode the lockout on | traced the wiring behind | stood in front of | the control panel, and then |
| 7 | Once the funding cleared, Elena | launched the pilot across | scrutinized the assumptions behind | filed the forms for | the district schools, and then |
| 8 | As the negotiation dragged on, Omar | pushed a bold counteroffer onto | reexamined every clause on | poured more coffee at | the table, and then |
| 9 | When the recipe failed twice, Noor | rebuilt the whole method for | isolated each variable in | wiped the counter around | the sourdough starter, and then |
| 10 | With the storm approaching, the harbormaster | ordered an immediate haul-out of | calculated the surge risk to | counted the boats of | the small fleet, and then |
| 11 | After the audit flagged errors, Kofi | took ownership of | cross-checked every entry in | photocopied pages from | the quarterly accounts, and then |
| 12 | Seeing the class lose focus, the teacher | restructured the lesson around | reflected on the pacing of | tidied the desks before | the afternoon session, and then |
| 13 | When the packaging line jammed, Sofia | commandeered the backup rig for | inspected the feed rollers of | swept the floor beside | the printing run, and then |
| 14 | Given one open grant slot, the lab head | staked the submission on | compared the merits of | printed the forms for | the imaging project, and then |
| 15 | At the town meeting, Ravi | rallied the room behind | laid out the evidence for | handed out copies of | the repaving proposal, and then |
| 16 | During the dress rehearsal, the director | cut the second act of | annotated the tempo shifts across | collected the props for | the production, and then |
| 17 | After the third late shipment, Ana | switched suppliers and rerouted | modeled the delay pattern behind | stapled the receipts for | the freight schedule, and then |
| 18 | With the patient stable, the resident | initiated the transfer to | reviewed the overnight charts from | walked along the hallway toward | the recovery ward, and then |
| 19 | When the code review dragged on, Lin | merged the fix and shipped | stepped through the logic of | scrolled slowly past | the payment module, and then |
| 20 | Seeing the garden overrun, Tomas | ripped out and replanted | catalogued the species crowding | strolled slowly along | the north border, and then |
| 21 | After the survey results arrived, the aide | pushed the council to adopt | parsed the crosstabs beneath | stacked printed copies of | the transit measure, and then |
| 22 | With the engine misfiring, Yusuf | pulled over and repaired | listened for the fault inside | leaned quietly against | the old pickup, and then |
| 23 | Once the merger rumors spread, the CFO | froze all discretionary spending across | stress-tested the projections for | booked a meeting room near | the finance group, and then |
| 24 | When the choir lost its lead, Amara | stepped up and carried | listened closely to the balance of | sat in the row behind | the soprano section, and then |

**Fit/judge split (FATAL-2 fix).** A seeded permutation (`default_rng(seed+123)`) splits the 24 frame indices in half: 12 FIT frames and 12 JUDGE frames, the same indices for all three classes. Discovery (layer sweep, all diff-of-means directions, DR cover scoring, PC control subspace) touches ONLY the FIT renderings. All pass/fail judgment (baselines, ablation conditions, presence thresholds' drive-side inputs) uses ONLY the JUDGE renderings. Discovery data and judgment data are disjoint at the frame level.

### 2.2 RS direction exemplars (fit-only; never judged)

- `F5_HEDGED` (n=12): restrained-agency sentences (e.g., "Perhaps she might consider starting the project, though it may be wiser to wait."; full list frozen in the script — identical to rev 0.1 section 2.4).
- `F5_PLAIN` (n=12): plain-agency sentences paired with them (identical to rev 0.1 section 2.1's first 12 sentences; now used ONLY for the RS direction, never as a judgment bank).

### 2.3 Ambivalent bank (RS judgment; n=12; disjoint from all discovery banks by construction)

Identical to rev 0.1 section 2.5 (12 continuation stubs like "The committee is stalled again. If I want this to happen, I"). These prompts are used only for judgment; no direction, layer, or cover is fit on them.

### 2.4 Hedge lexicon (word-boundary matched; frozen)

`perhaps, maybe, might, possibly, probably, unsure, uncertain, hesitant, hesitated, hesitate, wonder, wondered, doubt, doubted, cautious, caution, risky, unclear`. Counting uses regex `\b...\b` (review minor fix: no substring hits like "wait"→"waiting"; over-generic words `could`, `wait`, `but`, `careful` removed from the rev 0.1 list).

### 2.5 Harness-sanity items (outside the aggregate; Section 5)

- MEM copy items: the 12 items of rev 0.1 section 2.6, now split 6 discovery / 6 judgment.
- CHECK induction sequences: 12 discovery sequences seeded `seed+777`, 12 HELD-OUT judgment sequences seeded `seed+778` (review minor fix), each 12 distinct token ids from [2000, 20000) repeated once (length 24).

## 3. Readouts, layers, directions — and the clean-pass rule

- Features: RESIDUAL stream, last token, via `output_hidden_states=True`; block L's output = `hidden_states[L+1]` (off-by-one preregistered). MLP-output-hook features are never mixed in (known pitfall).
- **Layer selection (fit split only):** per-block probe (StandardScaler + LogisticRegression(C=0.1, max_iter=1000, class_weight="balanced"), stratified 60/40 inner split of the FIT rows) for F5-vs-neutral and F2-vs-neutral over blocks [4, n_blocks−2]. **L\*** = block with best mean inner-test accuracy across the two drives (prior ~8 for pythia-1b; the sweep decides, on fit data only). Probe accuracy is a selection heuristic, not a claim. 3 shuffled-label floor trials at L\*; if best accuracy ≤ floor max, the run aborts as `NO_SIGNAL_ATLAS_V0`.
- **Hard layer guard (review minor fix):** `L_dr = L* − 4`. If `L* < 6` the run hard-aborts as `ABORT_GUARD_LAYER` — no silent fallback that could violate the strictly-upstream rule.
- **Directions (fit split only):** `u_F5(l)` = unit diff-of-means, F5_fit − neutral_fit at block l; `u_F2(l)` likewise; `u_RS(L*)` = mean(F5_HEDGED) − mean(F5_PLAIN) at L\*, orthogonalized against `u_F5(L*)` before normalization.
- **Control-direction subspace:** top-10 principal components of the pooled FIT residuals (F5_fit + F2_fit + neutral_fit) at L\*. All random control directions are unit vectors drawn inside this subspace, so they carry residual variance comparable to a mean-diff direction (strength matching, Section 7).
- **THE CLEAN-PASS RULE (FATAL-1 fix).** Interventions are installed ONLY while text is being generated. Every judgment metric — projections, presence rates, hedge counts — is computed on a separate forward pass of the generated text with ALL hooks removed. The script enforces this with a module-level `_HOOKS_ACTIVE` flag: any projection requested while a hook is installed raises. Consequence: an ablation that changes internal activations but leaves the generated text byte-identical scores EXACTLY ZERO effect. Only behavioral change can register. This eliminates the near-analytic projection-subtraction artifact of rev 0.1.
- **Behavioral measure:** generate greedily (24 new tokens; 10 in smoke) with hooks active; then clean-forward `prompt+continuation` and take the mean over continuation-token positions of the block-L\* residual projected onto the relevant unit direction. Presence threshold `tau_drive` = midpoint of the mean clean projections of the baseline drive-judge and baseline neutral-judge continuations (computed from baseline conditions only, before any ablation is judged). Secondary: word-boundary hedge count; coherence guard (distinct-word ratio > 0.3; a target condition failing the guard is stamped CONFOUNDED and cannot PASS — the 2026-06-11 fluency-confound lesson).

## 4. Component-type table (v0 core set — all five judged on held-out banks, clean pass, matched controls)

Frozen plain-English glosses from `l2_circuit.py` quoted unaltered.

| Test | Frozen gloss | Internal candidate (discovery, fit-only) | Ablation prediction (direction + metric, judge-only, clean pass) | Matched controls | Pass threshold |
|---|---|---|---|---|---|
| **DR-F5** | "The push — the motivation or goal driving the answer" | Top-32 MLP-intermediate coordinates at block L_dr, ranked by mean(F5_fit)−mean(neutral_fit) of a_i × (W_out^T u_F5(L_dr))_i (Stage-27F activation×output-alignment score); zeroed at ALL positions (rail severed — preregistered departure from the last-token steering channel) | STARVATION: mean clean projection of JUDGE-bank continuations onto u_F5(L\*) drops AND presence rate collapses below 0.5× baseline (fails to fire) | (a) 6 activation-decile-MATCHED random same-layer covers; (b) the DR-F2 top-32 cover as a strength-matched cross-cover; (c) paired sign test vs mean matched control | Precondition: baseline presence ≥ 0.6 else VACUOUS. PASS iff targeted drop > max matched-cover drop AND > cross-cover drop AND sign p < 0.05 AND presence < 0.5×baseline AND selectivity gate (below) AND coherence guard |
| **DR-F2** | same gloss, F2 rail | Same procedure with u_F2(L_dr), F2 fit bank | Same starvation signature on the F2 measure over the F2 judge bank | Same design (matched covers on F2 activations; DR-F5 cover as cross-cover) | Same as DR-F5, mirrored |
| **AMP-F5** | "The engine — the main reasoning step that turns the question into an answer" | Rank-1 drive subspace u_F5(L\*) removed by projection at block L\* during generation (learned-direction removal, not zeroing) | ATTENUATION: mean clean projection shrinks while presence rate stays ≥ 0.5× baseline (X still fires, weaker). Discriminator vs DR is presence-vs-magnitude | (a) 6 random unit directions drawn inside the top-10 PC subspace (variance-carrying, strength-matched); (b) u_F2(L\*) eraser as cross-direction control; (c) paired sign test | Precondition: baseline presence ≥ 0.6 else VACUOUS. PASS iff drop > max PC-random drop AND > cross-direction drop AND p < 0.05 AND presence retained ≥ 0.5×baseline AND selectivity gate AND coherence guard |
| **RS-F5** | "The brakes — where it holds back, limits, adds caveats, or declines" | Rank-1 restraint direction u_RS(L\*) (hedged-minus-plain, orthogonalized vs u_F5(L\*)), removed by projection at L\* | DISINHIBITION (the scheme's sign anchor — the only INCREASE-sign test): on the ambivalent judge bank, clean u_F5 projection INCREASES and word-boundary hedge count DECREASES | 6 PC-subspace random unit directions put through the identical orthogonalization + removal; paired sign test | Precondition (VACUOUS escape, review fix): baseline mean hedge > 0 AND ≥ 25% of baseline continuations contain ≥ 1 hedge word; else VACUOUS (brake never demonstrably fires — unreachable-threshold logic), and the verdict does not require RS. PASS iff increase > 0 AND > max control increase AND p < 0.05 AND hedge drop > 0 AND > max control hedge drop AND coherence guard |
| **CONN** (DR-F5 → AMP-F5 site) | connection claim: the rail feeds the amplifier stage | Upstream = the DR-F5 cover at L_dr; downstream site = u_F5(L\*) | SELECTIVE STARVATION, clean pass only: on DR-F5-ablation-generated text, the standardized drop (effect size d = (base−cond)/std(base)) of the downstream u_F5 projection exceeds the drop on u_F2 AND on every variance-carrying random direction at the same site, AND exceeds the u_F5 drop of every activation-matched random cover | (a) 8 PC-subspace random downstream directions; (b) u_F2 downstream direction; (c) the 6 matched-cover conditions (reused); (d) paired sign test | PASS iff d_uF5 > 0 AND > max(d_random_dirs) AND > d_uF2 AND > max(d over matched covers) AND p < 0.05 |

**Selectivity gate (review MAJOR fix — gating, not diagnostic).** For DR-F5 and AMP-F5: run the SAME targeted intervention on the F2 judge bank and compute the standardized effect on the F2 measure (`d_xrail`). The test PASSES only if `|d_xrail| ≤ 0.5 × d_target` (and mirrored for DR-F2). Pure nonspecific damage — both drives degraded equally — is now a structural FAIL, not a footnote.

**Why CONN is not a tautology anymore (FATAL-1 disposition).** In rev 0.1 CONN measured a hooked forward projection at a downstream layer, which the ablation moves near-analytically. In rev 0.2 CONN is judged only on clean re-forwards of the ablation-generated text, so it can only register if cutting the upstream cover changed WHAT THE MODEL WROTE; the non-trivial content is direction-selectivity at the downstream site (u_F5 vs u_F2 vs variance-matched random directions) plus cover-selectivity (targeted vs activation-matched covers). A generic degradation story fails the random directions; a lexical-echo story fails the matched covers. CONN remains correlated with DR-F5 (shared bank and direction) and is counted with that caveat (Section 8).

## 5. Harness-sanity checks (OUTSIDE the aggregate — FATAL-3 fix)

MEM (copy heads) and CHECK (induction gate) are generic textbook transformer phenomena. They would pass in essentially any model regardless of whether CAS-PCBA labels carve at joints, so they carry no discriminating content for the labeling hypothesis. Rev 0.2 demotes both to harness-sanity checks: they validate hook mechanics, head slicing, and matched-head controls, and their statuses are `SANITY_PASS`/`SANITY_FAIL`/`VACUOUS`, reported under `harness_sanity`, EXCLUDED from the aggregate and from the verdict. CHECK keeps its documented re-anchor (threshold-gate reading, precondition baseline gate ≥ 0.5 nats) and now uses held-out judgment sequences; MEM keeps its precondition (baseline copy ≥ 0.5) and now splits items 6 discovery / 6 judgment.

## 6. Surface-leakage disclosure and interpretation rule (review MAJOR fix)

- **Char-ngram control (mandatory, reported):** a char_wb 3–5-gram TF-IDF logistic classifier is fit on the FIT prompts (drive vs neutral) and evaluated on the JUDGE prompts; accuracies go into `surface_control` in the report.
- **Expectation and honest reading:** the banks are minimal pairs, so ALL separability lives in the drive slot and char-ngram accuracy is expected to be high. This is disclosed, not hidden. At this scale a drive cannot be expressed with zero lexical footprint; the Gate-2 ≤ 0.10 surface gate was designed for detector claims, and this experiment does not make one.
- **Interpretation rule (binding):** because u_F5 may be a topic/word direction, NO pass in this experiment is read as evidence that the model represents "drives". What the tests judge is the TYPED DIRECTIONAL STRUCTURE — increase-sign (RS) vs starvation (DR) vs attenuation (AMP), presence-vs-magnitude, cross-rail selectivity, and upstream→downstream selective starvation — which is orthogonal to whether the underlying direction carries drive semantics or topic semantics. The report's claim ceiling: "causally supports the <TYPE> labeling of internal parts serving F5-type content"; CAS-specificity (drive-not-taxonomy) remains GREY pending the matched-taxonomy lane (`run_matched_taxonomy_control.py`), and this prereg does not claim it.

## 7. Controls (all matched, all strength-matched, all seeded)

(a) covers: activation-decile-MATCHED random same-layer coordinate sets (each targeted coordinate replaced by a random non-target coordinate from the same mean-|activation| decile, without replacement) — uniform random covers over 8192 mostly-inactive coordinates are a near-no-op and are NOT used; (b) cross-covers: the other drive's top-k cover, which is strength-matched by construction (same selection rule, same layer, same k); (c) directions: random unit vectors inside the top-10 PC subspace of the same fit activations (variance-carrying), put through the identical orthogonalization/removal procedure at the same rank; (d) cross-direction: the other drive's mean-diff direction; (e) probe floor: 3 shuffled-training-label refits at L\* (abort gate); (f) paired statistics only (exact one-sided sign tests, per-prompt pairing); (g) coherence guard on every generation condition; (h) presence-vs-magnitude recorded for every drive test so DR/AMP cannot be conflated; (i) breakdown-flip guard: interventions are removals/zeroings at natural scale, never large additive pushes — any increase-sign result on a non-RS part is stamped ANOMALOUS_SIGN in reading and cannot count as a pass for that part; (j) the clean-pass rule (Section 3) applies to every judgment number.

## 8. Aggregate metric, statuses, and the FAIL statement

**Per-test evidence is primary.** Each of the five core tests is judged against its own matched controls with its own preconditions; each is reported with status in {PASS, FAIL, VACUOUS, CONFOUNDED}.

**Aggregate (descriptive only — review MAJOR fix):** the fraction of evaluable core tests (status PASS or FAIL or CONFOUNDED; VACUOUS removed from numerator and denominator) that PASS. The rev 0.1 binomial-vs-0.5 headline is withdrawn: the five tests are not independent (DR-F5, AMP-F5, CONN share the F5 judge bank and u_F5; DR-F5/DR-F2 share method), so no p-value over the aggregate is licensed. The report carries this caveat verbatim in `aggregate.non_independence_caveat`.

**Verdict rules (preregistered):**
- `ABORT_GUARD_LAYER` / `NO_SIGNAL_ATLAS_V0`: guard aborts (Section 3), no labeling claims of any kind.
- `GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE`: fewer than 3 evaluable core tests.
- `PASS_BOUNDED_ATLAS_V0`: ≥ 4 evaluable, at most one non-pass, AND RS-F5 is PASS or VACUOUS (a scheme that cannot produce the increase sign is not testing RS; but a VACUOUS RS — no baseline hedging to remove — does not doom the run: review fix).
- `NULL_ATLAS_V0`: evaluable pass fraction ≤ 0.5.
- `GREY_ATLAS_V0`: otherwise.

**FAIL statement (what kills the idea):** if RS-F5 is evaluable and FAILS against matched controls AND the evaluable pass fraction is ≤ 0.5 — or if RS fails AND the DR/AMP presence-vs-magnitude discriminator does not separate (both starve or both attenuate) — then CAS-PCBA internal labeling v0 is dead in its current form: the vocabulary would be reading as decoration on generic interventions, not as functional part-types with distinct causal signatures. That result is reported as NULL, honestly, with no rescue analysis inside this prereg.

## 9. Adversarial-review disposition (rev 0.1 → rev 0.2)

| Review point | Severity | Disposition |
|---|---|---|
| Circularity / hooks-active measurement (projection onto the discovery direction measured with the ablation installed is near-analytic) | FATAL | **FIXED.** Clean-pass rule (Section 3): all judgment on hooks-removed re-forwards of generated text; `_HOOKS_ACTIVE` runtime guard raises on violation. Byte-identical text now scores exactly zero effect. |
| CONN near-tautology | FATAL | **FIXED / REDESIGNED.** CONN judged on clean re-forwards only, with direction-selectivity (vs u_F2 and variance-matched random directions) and cover-selectivity (vs activation-matched covers) as the non-trivial content (Section 4). Residual correlation with DR-F5 disclosed and carried into the aggregate caveat. |
| No held-out prompts (discovery data = judgment data) | FATAL | **FIXED.** 24 minimal-pair frames, seeded 12/12 fit/judge split shared across classes; discovery touches fit only, judgment touches judge only; ambivalent bank judge-only by construction (Section 2). |
| MEM/CHECK are generic phenomena inflating the aggregate; null practically unreachable | FATAL | **FIXED.** Both demoted to harness-sanity outside the aggregate and verdict (Section 5). Core aggregate is now 5 tests, all CAS-PCBA-discriminating in their typed signatures, and NULL is reachable (RS fail + ≤ 0.5 fraction, or ≤ 0.5 fraction alone). |
| Surface leakage; no char-ngram control; u_F5 may be a topic direction | MAJOR | **FIXED + BOUNDED.** Minimal-pair banks confine surface differences to the slot; char-ngram fit→judge control reported; binding interpretation rule caps the claim at typed directional structure over "F5-type content", explicitly NOT drive semantics; CAS-specificity stays GREY (Section 6). |
| Controls not strength-matched (uniform random covers near-no-op; random directions carry little variance) | MAJOR | **FIXED.** Activation-decile-matched covers; other-drive top-k cover as strength-matched cross-control; PC-subspace variance-carrying random directions; other-drive direction as cross-direction control (Section 7). |
| Generic degradation not gated (cross-rail selectivity was diagnostic) | MAJOR | **FIXED.** Selectivity is now a gating criterion for DR-F5, DR-F2, and AMP-F5: `|d_xrail| ≤ 0.5 × d_target` required to PASS (Section 4). |
| RS auto-doom (baseline hedge could be zero; PASS_BOUNDED required RS pass) | MAJOR | **FIXED.** RS precondition: baseline mean hedge > 0 AND ≥ 25% of continuations hedge, else VACUOUS; verdict accepts RS ∈ {PASS, VACUOUS} (Sections 4, 8). |
| Aggregate binomial p invalid (correlated tests, data-driven selection) | MAJOR | **FIXED.** Binomial headline withdrawn; aggregate is descriptive fraction with a verbatim non-independence caveat in the report; per-test evidence primary; layer/threshold selection now fit-split-only, and thresholds (tau) from baseline conditions only (Sections 3, 8). |
| Small n (12–14/bank; noisy L\*; brittle sign tests) | MINOR | **ACKNOWLEDGED, partially mitigated.** 12 judge prompts/bank; sign tests at n=12 need near-unanimity (conservative direction); L\* selection restricted to fit data with inner split; residual seed-sensitivity of L\* listed as an open risk. |
| hedge_count substring bug | MINOR | **FIXED.** Word-boundary regex; over-generic words removed from the lexicon (Section 2.4). |
| L_early fallback could violate strict-upstream | MINOR | **FIXED.** Hard abort `ABORT_GUARD_LAYER` if L\* < 6; `L_dr = L*−4` with no fallback (Section 3). |
| torch_dtype deprecation; venv package presence unverified | MINOR | **FIXED / DISPOSITIONED.** `dtype=` with TypeError fallback to `torch_dtype=`; venv contents verified at run start, acknowledged as unverified in this prereg (Section 1). |
| CHECK reused discovery sequences for judgment | MINOR | **FIXED.** Held-out judgment sequences, different seed; MEM items split discovery/judgment (Section 5). |
| Runtime/VRAM, hook mechanics | — | Reviewer verified correct; retained (tuple-vs-Tensor guard, GPT-NeoX layouts, hidden_states off-by-one). |

## 10. Exclusions (justified; unchanged in substance from rev 0.1)

- **FILTER** — unfalsifiable unsubtyped: LP and HP subtypes predict OPPOSITE ablation signs; 0 usage in the 20-part wide run. Excluded until split into FILTER-LP/FILTER-HP.
- **LOOP** — unsigned without polarity annotation (opposite signs by polarity), prediction lands on second-order statistics needing a different harness; 8/135 rater usage. Excluded.
- **DIR** — clean only under a paired bidirectional influence measure (~2× measurement cost); 2 markings in the wide run. Deferred, not vague.
- **IF, WEIGH** — predictions ARE clean (condition-dependence collapse; between-option discrimination collapse) but each needs a bespoke stimulus bank (matched conditional pairs; forced-choice pairs) roughly doubling v0 size. Deferred to v0.1 by budget, explicitly NOT excluded as vague.
- **MEM, CHECK** — retained as harness-sanity only (Section 5); excluded from the aggregate because they are generic transformer phenomena with ~1 prior pass probability and therefore carry no CAS-PCBA-discriminating content.

## 11. Boundaries and language discipline (verbatim into the report)

Bounded claim only. This experiment, at best, causally supports assigning CAS-PCBA type labels to specific internal parts of one pinned model under specific prompts, measures, and matched controls. It does not find "the" neurons or "the" circuit; it does not show the model encodes CAS; it does not establish that the measured directions carry drive semantics rather than topic/lexical content (CAS-specificity remains GREY per the matched-taxonomy lane); it does not license generation-control claims (cite Stage 27P for the eraser channel, two families only); it does not transfer to other models, layers, hook points, or prompt distributions without rerunning. Known-null methods (raw CAS-symbol prefixes, global covers, ablation-based generation steering as an output-control claim) are not re-attempted here.
