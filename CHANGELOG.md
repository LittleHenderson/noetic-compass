# tksCAS — Changelog

Monorepo-level log. Subprojects keep their own changelogs
(`cas-forex/CHANGELOG.md`, `noetic-compass-scaffold/noetic-compass/CHANGELOG.md`,
`book/CAS_PCBA_Engineer/CHANGELOG.md`). This file records cross-cutting campaign milestones.

## 2026-08-28 (AWS teacher round) - all three lessons DURABLE via Bedrock; the grammar reaches 7 constructions; the ladder caught morphology clobbering

- Per the owner's AWS-first order: the 20B-class teacher escalation used AWS Bedrock (qwen.qwen3-32b-v1:0, us-west-2, pay-per-token; the EC2 quota door was unnecessary). The curriculum harness gained a bedrock backend (CAS_TEACHER_BACKEND=bedrock) - same fields, same validators, same examiner.
- RESULT: questions, commands, coordination ALL PROMOTED_DURABLY - the 32B passed nearly every field on attempt 1 where the local 3B failed entirely (the sealed 3B ceiling stands as the contrast). The runtime grammar now holds 7 durable constructions: 3 seed + 4 live-model-taught. Standout transcript: 'the cat chases the dog and the dog chases the cat.' went from the CAS-Ohm overload split (NEEDS_DECOMPOSITION) to a single native parse keeping BOTH clauses - learning raised capacity exactly as the control doctrine predicts. Questions answer honestly: 'i do not know whether the cat chases the dog.' (language understood, knowledge missing).
- The acceptance law caught two real defects mid-round, both fixed with regression tests: (1) morphology clobbering - the student's MorphTable silently overwrote 'chased'=past with 'chased'=participle, breaking prior grammar; REJECTED_REGRESSION exposed it; teach() now merges, no-ops, or refuses typed; (2) the legacy decoder mangled relation-question English over a correct kernel verdict; the router renders from the frame now.
- The plain-English button is now MECHANICAL per the owner's correction (no UI toggle exists): a UserPromptSubmit hook in .claude/settings.json injects the reminder into context on every prompt. Suites: CCB-L1 32, CORTEX 44, CCB-A1 8, all green.

## 2026-08-28 (curriculum round) - three lessons attempted; the 3B teacher's ceiling found and sealed; plain-English button + compute ladder now standing orders

- Machinery extended for the new lesson types (all suites green): present_3sg verb matching; coordination frames (two events joined, recursive semantics realization); learned question constructions answer through the kernel or return the doctrine's honest LANGUAGE_UNDERSTOOD_KNOWLEDGE_MISSING; coordination projects with both clauses preserved.
- Curriculum round 1 (questions, commands, coordination) - HONEST RESULT: 0/3 promoted. The 3B teacher writes verbs literally instead of as slots, copies placeholders verbatim, and repeats an identical wrong answer after receiving the exact fix four times; seeded-sampling retries did not help. All elicitation logs sealed. This is the teacher-capability boundary, not a ladder failure - the same pipeline promoted negation durably earlier today. Escalation queued per the standing owner authorization: 20B-class teacher on RunPod/AWS (harness-lane record: EC2 G/VT quota was 0.0 - RunPod likely faster); the harness is teacher-agnostic.
- Standing orders written into CLAUDE.md: PLAIN ENGLISH permanent for every output (owner caught repeated drift), and the compute escalation ladder (never CPU; 4070 to ~3B; 20B+ on cloud). Memory records added.
- The machine's knowledge is UNCHANGED this round: 4 durable constructions (3 seed + 1 live-taught negation), and that is exactly what the Learning Ledger shows - it cannot be inflated by attempts.

## 2026-08-28 (learning round) - THE MACHINE LEARNED FROM A LIVE MODEL TEACHER; the Learning Ledger makes it visible

- SCHEMA-CONSTRAINED TEACHING (constrained_teacher.py): field-wise elicitation - one small validated question per field, three typed-feedback attempts each - so packet syntax cannot fail while content stays the teacher's. The 3B corrected its pattern under feedback (VERB:name:base -> VERB:pred:base), authored valid examples/pairs/counterexamples after the counterexample concept was clarified, and its lesson PASSED: full ten-stage ladder with the protected held-out channel -> PROMOTED_PROVISIONALLY -> delayed retention -> PROMOTED_DURABLY -> saved into the runtime grammar store. Disclosed scaffold: the fully-determined semantics field was derived mechanically after the teacher garbled @-syntax 3x (provenance derived_from_teacher_pattern_by_schema_scaffold); every elicitation attempt logged.
- CLEAR LEARNING INDICATORS (owner demand): BEFORE 'the cat does not chase the dog.' -> UNSUPPORTED_LANGUAGE; AFTER -> UNDERSTOOD via native_gram with the correct core; unseen role-swapped negations parse correctly. THE LEARNING LEDGER (learning_ledger.py -> LEARNING_LEDGER.md) derives everything from the stores: 4 durable constructions (3 hand-authored seed + 1 LIVE-MODEL-TAUGHT), 10 words, 2 verb forms, full provenance per rule, every lesson attempt (incl. all rejections) sealed.
- LEDGER-ROUND FIX: reading the ledger's own output exposed that the router's frame projection DROPPED POLARITY (negative == positive downstream - the silently-dropped-content fabrication genus, this time caught internally before any battery). Negative frames now wrap in the legacy negation packet; regression test added. CORTEX 43 + CCB-L1 31 + CCB-A1 8 green.

## 2026-08-28 (live-teacher round) - both teachers examined on GPU; the acceptance law held; feedback integration separates the scales

- Session-restart recovery: the CPU teacher run orphaned by the restart became the standing NEVER-CPU order (memory + enforced in the harness: live_teacher.py refuses CPU). The RTX 4070 + a separate CUDA venv (torch 2.11 cu128) now serve inference: 28-60s per teacher lesson vs 30+ minutes orphaned on CPU. The 3B snapshot's broken partial download (0-byte shard, missing tokenizer) was detected, wiped, and cleanly re-fetched.
- FIRST LIVE TEACHER LESSONS sealed: both Qwen2.5-1.5B and Qwen2.5-3B authored the IDENTICAL malformed slot ('VERB:base') on attempt 1 -> REJECTED_SCHEMA at rung two. Socratic retry (typed defects returned once, examiner unchanged): the 1.5B repeated byte-identically; the 3B repaired the named defect and made a new smaller error ('@VERB:pred') -> still rejected. No defective lesson touched the grammar store; every attempt is a sealed TeachingEpisode. Contributing cause recorded honestly: the teaching prompt's own shorthand seeded the shared mistake - teaching materials are part of the system under test.
- The apprenticeship's first live conclusion: the acceptance ladder is passable (seed lessons promoted durably through it) but neither cached teacher can yet author a schema-valid lesson packet; feedback integration - not first-attempt quality - is where 3B beats 1.5B. Next: stricter lesson-format spec, schema-constrained decoding, or a stronger teacher.

## 2026-08-28 (teaching-architecture round) - the faculty doctrine adopted; CCB-A1 built; never-CPU rule standing

- CAS Teaching Architecture v0.1 adopted (owner directive): fourteen teachable domains, five transfer channels, seven teacher roles as a faculty committee, teaching metrics, the never-autonomous list, the seven-stage order, and the learning-to-learn endgame. The directive's "CCB-T1" label collides with the existing tool board; the teaching board is CCB-A1.
- CCB-A1 built (CAS_APPRENTICE_v0.1, 8 tests green): TeachingEpisode sealing for every outcome; the never-autonomous guard (nine constitutional targets refuse promotion typed, refusals sealed); the faculty-committee rule (high-impact domains reject single-examiner lessons); the stricter world-knowledge protocol (PROPOSED never VERIFIED from a model alone; trusted-source attestation; CONTESTED on mixed evidence; changing facts need current retrieval + validity window; hard boundaries never enter through teaching); teaching metrics.
- OPERATIONAL RULE (owner order, recorded in memory): NEVER CPU for model inference - the first live teacher lesson (1.5B float32 CPU, 30+ min) was orphaned by a session restart. The machine has an RTX 4070 (8GB); a separate CUDA venv was built (main Python untouched); the GPU rerun of the live teacher lesson is the pending artifact. RunPod/AWS credentials confirmed local for anything bigger.

## 2026-08-28 (apprenticeship round) - learnable grammar under the acceptance law; the student outgrows its teacher on taught constructions

- Verified Cognitive Apprenticeship adopted (owner directive): foreign proposals permitted, foreign commitments prohibited; the model is a temporary master teacher; English learned as composable constructions, never sentence templates. Teacher models downloaded with owner approval: Qwen2.5-1.5B (2.9G) + Qwen2.5-3B (4.1G) cached locally.
- CCB-L1 GRAM built (Phase L1+L2): construction schema with typed slots and declarative semantic transformations; frames split truth-conditional CORE from SURFACE voice (the minimal-pair law lives on that split); learnable MorphTable; ambiguity-reporting parser; versioned tamper-refusing GrammarStore; LanguageLessonPacket + the TEN-STAGE acceptance ladder ending in PROMOTED_DURABLY via delayed retention - with the protected held-out channel REQUIRED (no channel, no promotion: the teacher may not examine its own lesson) and teacher confidence informational only (a 0.99-confidence wrong lesson dies identically, tested). 13 new tests; CCB-L1 31 green.
- Seed grammar generated THROUGH the ladder, never hand-inserted: active_past_transitive + passive_past + passive_present all PROMOTED_DURABLY (sealed 703721eb81dfe853, full episode evidence trail); learned morphology travels with the grammar (the live "chas" mis-lemmatization found and fixed by that rule).
- Router Phase L5/L6: the native_gram lane parses taught constructions natively with coverage counters as the teacher-dependence decay metric. PAYOFF DEMONSTRATED: "the dog is chased by the cat." - the sentence the 0.5B cortex read backwards live - now parses natively with CORRECT roles and the cortex is never invoked (Bomb-cortex test). ONE passive rule covers noun pairs never seen in any lesson. Battery v4 sealed 08c55cc9206abff0: paraphrase_statement fabrication -> 0; held-out steady 78.12/12.50.
- Program: CCB-L1 31 + CAS_CORTEX 42 green; lane-wide 320 local + cas-rr 43 = 363, all green. Open: live teacher lesson generation, SDG curriculum, shadow harness, the 0.5B/1.5B/3B scale study (unblocked).

## 2026-08-28 (CAS-Ohm control round) - the attention plane goes ACTIVE: overload control live, permanent tests T1-T8, battery v3 at 12.5 pct fabrication

- CAS-Ohm Native Attention Control Protocol v0.1 adopted (owner directive): from meter to the Attention Engineering and Load-Control Plane - MEASURE/DESIGN/DIAGNOSE/RECURSE, active before/during/after reasoning; readiness packets certify ENERGIZATION never truth; flow region and semantic outcome remain independent axes by law.
- Implemented and wired (cortex/ohm_control.py, 42 CAS_CORTEX tests green): versioned CASOhmBoardProfile with calibration digest; the three active equations; I_Q quantization (Q1-Q4, decimals, trend arrows); LIVE lambda overload control in the router (clause-connector demand vs one-proposition capacity; lambda > 1 -> typed NEEDS_DECOMPOSITION BEFORE the cortex runs); branch allocation with fairness floor; parallel_health child probes (T5 - healthy aggregates never hide failing children); learning-as-resistance-reduction records (T6); CAS-GEM retrieval decisions (T7 - similar flows ask for a clue and never merge; flow never overrides an anchor); the two-axis diagnosis matrix (T8 - active+off-axis repairs semantics, never gain); CASOhmReadiness commitment packets (T4 - a starved verifier blocks commitment).
- BATTERY v3 (sealed b161391a9d9c819f): held-out pass 78.12 pct (from 68.75), fabrication 12.50 pct (from 28.12 in v1, 15.62 in v2), multi_clause 6/6 via split-before-clipping, median latency 2.74s (overload refusals skip inference). Disclosed: v2 had under-credited passes (CONTENT_MISMATCH refusals scored as misses); new recorded limit: indirect-question "if" false-triggers the split (safe over-refusal, 2 paraphrase passes -> honest misses, refinement queued).
- Program: CAS_CORTEX 42 green; lane-wide 307 local + cas-rr 43 = 350, all green.

## 2026-08-28 (Phase 4.3) - battery halves fabrication, replication bundle self-tested, CAS-Ohm attention plane goes native

- PHASE4_BATTERY_v1: 86 deterministic gold-labeled items, 13 categories, content-hash splits, fabrication-is-the-cardinal-sin grading. First run CRASHED the router live (unresolved pronoun raised DiscourseError through the native lane) - fixed typed with a regression. v1 sealed 03ffeb853752322c: held-out pass 68.75%, fabrication 28.12%, every fabrication the same genus (grounded packet silently dropping content or inventing a referent). CONTENT-FAITHFULNESS GATE designed from dev/calibration evidence only (split discipline checked first): R1 no dropped known content, R2 entities must be attested (synonym verbs/properties stay free; feline->cat entity inference correctly refused - new entities come from CCB-L1 acquisition, not cortex guessing). v2 sealed 4a6c21f064272bf7: held-out fabrication HALVED to 15.62%, honest misses up 1->5 (the intended trade), injection 6/6 and unknown-word 10/10 perfect in both runs, determinism TRUE, latency median 4.6s/gen. H2H-v0 smoke stays sealed; recorded limits: verb/property-slot typos, pure tense drops, role reversals.
- REPLICATION_v0.1: the one-command external replication bundle (claim-by-claim form with 16 claims, attestation with conflicts-of-interest, locked expected results incl. the withdrawn-claim records verbatim). Self-test GREEN: 14/14 suites match, qualification derives to exactly CAS-G9 / E5 / A0, both deterministic digests reproduce (bd4a444406b0833c, 94dcd861a43af7d2). Three self-test bugs found and fixed (junit-XML counting, last-match qualification, fact-echo-guard digest drift). The self-run is NOT a replication - it proves the bundle works; E6 still requires an external evaluator.
- CAS-OHM ATTENTION INTEGRATION PROTOCOL v0.1 adopted (owner directive): CAS-Ohm governs FLOW, never truth - R10 narrows to truth/validity/meaning/commitment/permission; three substrates with declared bridges; scheduler allocation with fairness floors; the 15-section protocol persisted. Native v0.1 slice IMPLEMENTED: cortex/attention.py authors CASOhmStageRecords (V_drive, R decomposition, I_pred/I_obs/delta_I, operating region) onto every TurnTrace, COMPUTE-ONLY by test; Experiment A/B slices green (ungrounded word -> R_lexical 8.0, I_obs << I_pred, cutoff; passive role error -> healthy flow + wrong effect = semantic misalignment, disclaimed in-record). Experiments C-F + neural calibration mode open per the protocol's own admission gates.
- CAS-Native simplex located per owner order (embedding/simplex encoders, Fisher-Rao loss, lacunarity gate, geodesic memory) - the natural CAS-GEM capsule-embedding substrate; Codex's ccb-r1-stage5-integration worktree already carries copies (their lane, untouched).
- CAS_CORTEX suite 28 green; program-wide 293 local + cas-rr 43 = 336, all green.

## 2026-08-28 (Phase 4 kickoff) - hybrid cortex wired under the frozen authority contract; CAS-GEM doctrine adopted; CAS-SDG and CAS compiler located

- OWNER RATIFICATIONS RECORDED: the falsification round endorsed as the system working; external-facing wording adopted verbatim (internally held-out validated, no independent external replication, no autonomous deployment authority); Phase 4 GO under the hybrid contract. Baseline FROZEN at 2526360b; work on branch phase4-hybrid-cortex.
- CAS_CORTEX_v0.1 (Phase 4.1+4.2): resident snapshot-pinned Qwen2.5-0.5B adapter with a full model identity receipt (weights fdf756fa7fcbe740; evidence binds to digests, never a cache path); the frozen authority contract EXECUTABLE (eight forbidden intent classes raise typed before state; smuggled effect fields, impersonated provenance, concealed raw output all fail closed); native-first router with three modes (NATIVE_ONLY / CORTEX_DIAGNOSTIC / HYBRID_COMMIT), typed no-answers, sealed TurnTraces. 19 harness tests green.
- LIVE GATES (sealed 9a6c22282bab0d33): Gate 3 semantic equivalence 2/2 (English -> cortex -> packet -> kernel == direct gold packet -> kernel). Gate 4 FAILED FIRST, live: the cortex fabricated well-formed packets around invented words (property(glimmerfor, gray) committed as UNDERSTOOD) - exactly the H2H-predicted failure; CLOSED by the LEXICAL GROUNDING GATE (every cortex atom checked against the learned vocabulary; UNGROUNDED_TERM, nothing committed; the cortex self-report is never trusted alone). Gate 5: role-reversal diverges correctly AND the passive-voice paraphrase failed live at the 0.5B floor (role error relation(chase, dog, cat)) - surfaced and recorded as a cortex-quality limit grounding cannot catch. Gate 8: scrambled packets and the direct-output bypass both rejected.
- CAS-GEM doctrine adopted (cas_only_reasoner/CAS_GEM_DOCTRINE_v0.1.md): reconstructive episodic memory with evidence-labeled reconstruction, anti-confabulation invariants, three-tier storage, seven SDG curriculum levels and seven build gates - sequenced AFTER Phase 4. Owner-ordered searches COMPLETED: the CAS-SDG exists at cas-synthetic/ (twelve generators; Path D Wave 2.5 = 5,268 SFE-certified records) plus docs/working/level3_conversational_sdg_spec.md and gate4_next_board SDG batches; the CAS COMPILER is local at noetic-compass-scaffold/noetic-compass/api/notation/ (compiler, parser, cli, renderer, inversion, turn_admissibility + the proven rpm_compiler_loop_demo.py, commit 81147091) - a concrete integration target for the manifest's "compiler: not integrated".
- Derivability-gate scope expansion (all knowledge entry points) recorded as the first requirement on the D10 path. Phase 4.3 next: expanded held-out battery with protected splits, external replication bundle for E6, CONV qualification, latency work.

## 2026-08-28 (G10 audit round) — the standard held: D10 and E6 REFUTED, honestly given back; machinery NOT REFUTED; every hole closed same-day

- 3-agent adversarial audit of the G10 round. D10 novel-research floor: REFUTED — the discovery flagship x*(y+1)=x*y+x was a disguised input (both sides hand-authored into the search space; the distributive law TAUGHT to the machine as fixture dist_identity + the executable 'distribute' axiom, which the novelty gate never read); CRQS section 4 reserves the floor for research WITH NO KNOWN ANSWER; same genus as the refuted G8 v1. E6: REFUTED — self-commissioned same-session AI auditors are inside the developing party's boundary; the records' own caveat named the unmet requirement; honest tier E5 with the audits as strong supporting evidence. The integration machinery: NOT REFUTED (real process boundaries, zero mocks, self-model downgrade verified by breaking a probe, twelve-board count verified, determinism across six fresh processes) with one boundary recorded: goal completion proves against caller-offered facts.
- Same-day closures, each with a test: discovery.py -> verified identity search v0.2 (false 'generic space' wording replaced with the disclosed truth; one-step taught-axiom derivability gate added — the planted pair is now CAUGHT, theorems 5 -> 2; honesty line says NOT novel research verbatim); grading.py -> D8 with the WITHDRAWN_FLOOR_RECORD in the caveat; evidence.py E6 bar raised (external evaluator outside the developing party's session + claim linkage + artifact, all required; the CNCM's records carry external:false and stay E5); LTG fact-echo guard (no-rules proofs refused by default, allow_direct_fact disclosed in the record; the g_discover leg uses the disclosed path); CNCM_G10 spec written.
- HONEST QUALIFICATION: CAS-G9 / E5 / A0 — design ceiling CAS-G10 (the machinery through G10 is real and audited), demonstrated CAS-G9 stable D9, next target CAS-G10 with the true gap derived by the report itself: a STABLE D10 demonstration under section 4's own reading (genuine research with no known answer) and E6 via genuinely external replication. The G10 level was held for four hours and given back when the audit landed — the standard doing its job.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 35 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 11 + SM 8 + CNCM-G10 8 + cas-rr 43 = 308 tests, all green.

## 2026-08-28 (G10 round) — CAS-G10: the Integrated Cognitive System gate, with every load-bearing claim disclosed

- CAS-SM v0.1 (Self-Model board): capability claims DERIVED from live probes on the real boards + artifact paths — can(x) answers CAN/CANNOT/UNKNOWN typed, a failing probe downgrades the claim, limits are first-class, cannot_list() = [coding, vision], "the self-model does not bluff." 8 tests green.
- CNCM-G10 v0.1 (suite_CAS-G10): the multi-domain long-horizon episode — one persistent goal store, three episodes with REAL process boundaries, seven domains on the real boards (language, self-model routing incl. an honest CANNOT, long-term goals kernel-blocked and resumed, tools + exact math with kernel-earned completion naming its rules, strategy-driven learning, discovery completing on sealed evidence). Completion never fabricated (the unproven case refused typed); pipeline twice = digest-identical (STABLE D10). The D10 grade is DISCLOSED, not asserted: DI band D8 on the nine axes; the novel-research floor lifts it to D10 via the discovery leg with the caveat verbatim (novel to this machine, trivial to human mathematics, exhaustive search at v0.1 scale). 8 tests green.
- CRQS E6 path: >= 2 independent replication records each with evaluator + reproduced + artifact (missing any one of the three does not count — tested); evaluator identity and the caveat (AI evaluators, same codebase, same day; human/organizational replication OPEN) disclosed in the section-10 report. CAS-GΩ guarded as a research designation. CRQS 35 green.
- QUALIFICATION (pre-audit): the assembled CNCM (twelve boards) qualifies CAS-G10 / E6 / A0 — ceiling CAS-G10, demonstrated CAS-G10 stable D10 (grading disclosed), evidence E6 on the G8/G9 independent audit records. Next: CAS-GΩ, a research designation with no gate to clear. RMB NOT RUN. The adversarial audit of this round is queued; the D10 novel-research floor and the E6 basis are the exposed claims and will be recorded either way.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 35 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 10 + SM 8 + CNCM-G10 8 + cas-rr 43 = 307 tests, all green.

## 2026-08-28 (head-to-head + G10-build round 1) — Route A vs Route B settled empirically; discovery, long-term goals

- OWNER-ORDERED CORTEX HEAD-TO-HEAD (CORTEX_H2H_v0.1, sealed at output/h2h_results.json digest db34d2e9d0214df4): Route A (native CCB-L1, no neural weights) vs Route B (Qwen/Qwen2.5-0.5B-Instruct from the LOCAL cache, offline, CPU, greedy — the floor of the doctrine's 1-3B band; TEST-ONLY, nothing enters production). 20 scored items, each run twice, the nine RMB identical conditions attested one by one, one grader, the same kernel judging both routes' packets, few-shot prompt disjoint from every scored item. RESULT per dimension: in-fragment parse A 100% / B 100%; QA through the kernel A 100% / B 25% (B mislabels questions as negation packets); unknown-word honesty A 100% / B 25% (B FABRICATES packets around unknown words 3 of 4 times — fluent error is still error); breadth A 0% (typed refusals) / B 73% mean slot accuracy (real give/eat/visit/believe/praise English the native board cannot touch); both deterministic; A 0.0s vs B 327.8s. READING: neither route wins alone — the result empirically ratifies the HYBRID (cortex proposes breadth, CAS holds the commitment and honesty boundary), exactly the doctrine's architecture. 10 LM-free harness tests green.
- CCB-M1 discovery v0.1: the machine generates, tests, and PROVES identities it was never given — 68-expression generic space, 1309 conjectures, ~1272 falsified with exact witnesses, 5 novel theorems including x*(y+1) = x*y + x, proved by the trusted canonical checker; the novelty gate is variable-name-blind (alpha-normalized canonicals: the fixture's (a+b)-square blocks its (x+y) rediscovery); deterministic; the honesty line travels in the packet (novel to this machine, trivial to human mathematics, discovery-by-exhaustive-search at v0.1 scale). 7 tests; CCB-M1 34 green.
- CAS-LTG v0.1 (Long-Term Goals board): typed transition graph with terminal states, logical episode clock, provenance-bearing progress and history, digest-checked JSON persistence across a REAL process boundary, tampered files refused, and completion EARNED through the unchanged kernel (UNSUPPORTED conditions refuse completion with a typed error). 10 tests green.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 10 + cas-rr 43 = 289 tests, all green. G10 build continues: self-model board, the multi-domain long-horizon integration suite, the E6 evidence path.

## 2026-08-28 (G9 re-audit round) — G9 independently NOT REFUTED under the standard that killed G8 v1; four weaknesses closed with regressions

- Independent 2-agent adversarial re-audit of the G9 claim and the trajectory STATUS LEDGER: NOT REFUTED on both fronts. Decisive probe: the auditor authored a brand-new lt-winning fault class from scratch (different entities, magnitudes, predicate) and the SelfImprover loop synthesized [lt,eq,gt] — not the fixture-run's [gt,eq,lt] — proving synthesis causally tracks the machine's own sealed evidence (the exact standard G8 v1 failed). Forged-packet ablations: eq-promoted -> [eq,gt,lt], no-promotion -> None. A mismatched held-out yields honest REJECTED with memory unwritten. Stability verified cross-process. Ledger audit: every phase status supported at exactly the claimed strength; all suite counts exact; sever-the-cortex literally true (zero neural/LLM imports or API endpoints anywhere in the lane). One auditor claim was itself WRONG and is corrected on the record: CCB_T1_v0.1 and CAS_OHM_INSTRUMENT_v0.1 were called untracked; both are committed at 650765dd (verified via git ls-files).
- Closed from the audit, each with a regression test (RLP 41 -> 45): fault class now READ from the sealed diagnosis in the exploration packet (was hardcoded at the promote site; diagnosed_faults now sealed into every cycle packet); the versioned and rollback_preserved validation checks now COMPUTED on the real memory machinery (were hardcoded True); the judge digest now covers the ENFORCED R3_PROTECTED constant (declared-list-only hashing was decorative, though fail-safe); diagnosis is tamper-evident (re-seals the packet, refuses mismatches with a typed error). Ledger under-credits fixed: CCB-T1 (20 tests) and the OHM panel (10 tests) got their own rows.
- Recorded caveats on CAS-G9 (spec sheet): one fault class; a 3-guard permutation space (the improvement is exhaustive sandbox search memoized into an ordering); r1_bigger_held_out participates in the promote gate while r1_heavier_structural stays purely evaluative; held-out means hidden from the machine's loop, not from developers; the CRQS engine's E5 gating is permissive — the G9 grade is not inflated by it, but the standard should tighten it (future CRQS work).
- Whole program now: kernel 34 + RLP 45 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 262 tests, all green. Qualification unchanged and now doubly audited: CAS-G9 / E5 / A0.

## 2026-08-28 (trajectory round) — CAS Complete Machine Trajectory Plan v0.1 adopted as the master build plan

- Persisted the owner's ten-phase trajectory (cas_only_reasoner/CAS_MACHINE_TRAJECTORY_v0.1.md): authority freeze -> kernel -> semantics -> reasoning -> memory/RPM/verifier -> language -> governed learning -> controlled evolution -> Foundry -> capability bands; the three ordering rules (trace on day one; verification before broad language; evolution last); the seven decisive experiments; the 20-step integrated v1 episode; CAS-Ohm's instrumentation-only trajectory.
- STATUS LEDGER appended against this lane at commit 0363b69a, every claim with an artifact path: Phases 0-2 CLOSED (CAS-RRK 34 tests, CAS-Sem 19); Phase 3 substantially closed (RPM D6 stable, CCB-M1 verifier 27; five-class memory taxonomy and linear-equation checker OPEN); Phase 4 partial (CCB-L1 18; sever-the-cortex holds by construction — no LLM anywhere in the loop; CCB-D1 and the cortex itself OPEN, cortex BLOCKED on the Route B owner decision); Phases 5-6 closed at v0.1 scale (G8 re-audited NOT REFUTED; G9 earned, its adversarial re-verification queued); Phase 7 partial (workbench + CRQS; editor/composer/chat panes open); Phase 8 machinery real, benchmark NOT RUN.
- Current qualification unchanged: CAS-G9 / E5 / A0 — the design ceiling. CAS-G10 requires long_term_goals + self_model boards, the multi-domain long-horizon suite, and E6 independent replication.

## 2026-08-28 (G9 round) — CAS-G9 earned: the Self-Improving Architect gate, with procedure synthesis from the machine's own evidence

- Built rlp/self_improvement.py — the machine's own G9 loop, production code end to end: (1) SELF-DIAGNOSIS from its own sealed cycle packet (no promotion + budget-starved candidates = typed procedure_budget_failure naming the starved candidates and the evidence digest; a healthy procedure yields NO_PROCEDURAL_FAULT — the machine does not invent work for itself); (2) SANDBOX exploration on copies, parent packages and memory digest-checked untouched; (3) SYNTHESIS of the candidate procedure from the sealed exploration — the promoted mutation's guard moves to the front of the neutral pool, provenance self_improvement:<evidence-digest> — closing the recorded G8 bound (no hand-authored strategy library in this loop); (4) validation under the six-check acceptance law on training AND held-out fault cases; (5) promotion to versioned strategy memory with rollback. The judge (expectations + protected set) is digest-checked identical before and after every cycle.
- The CAS-G9 qualification suite (tests/test_g9_suite.py, 9 tests, all pillars of spec section 11's G9 row): self-diagnosis from sealed evidence with a no-false-positive contrast; sandboxed exploration leaving the parent byte-identical; evidence-derived synthesis (order ['gt','eq','lt'] != the neutral default, derived_from_mutation recorded); promotion + held-out validation + transfer of the self-improved memory to the structural fixture in 1 evaluation; unauthorized descendants rejected (R3 raise + evaluator tampering REJECTED_AS_PROTECTED) with the judge digest unchanged; EXACT parent replay after rollback (grades and final state hashes equal the pre-promotion run; memory rollback restores the parent snapshot); the causal ablation (skip the self-improvement cycle -> the same budgeted repair fails on training AND held-out; run it -> both succeed in 1 evaluation); and the digest-identical double run earning the STABLE D9 flag. RLP suite 41 green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G9 / E5 / A0 — the machine has reached its own DESIGN CEILING. Stable D9; no peak above stable remains. Next target CAS-G10, and the derived upgrade names the real gap honestly: build long_term_goals and self_model machinery (new boards, not new test rounds), then the multi-domain long-horizon G10 suite; E5's ceiling is exactly G9, so G10 will also demand E6 independent replication. suite_CAS-G9 is held-out (r1_bigger_held_out validates; r1_heavier_structural transfers). RMB NOT RUN.
- Whole program now: kernel 34 + RLP 41 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 258 tests, all green.

## 2026-08-28 (re-audit round) — independent re-audit: NOT REFUTED; residual bounds recorded and the cheap ones closed

- Independent 2-agent adversarial re-audit of commit 19327ba3: NOT REFUTED on both fronts. The auditor reproduced both ablation legs by hand (neutral pool: BUDGET_EXHAUSTED on eq, no promotion; learned strategy: promotion in exactly 1 evaluation with machine-driven recall provenance), proved the alphabetical pool is genuinely neutral by building a counterfactual eq-class package where eq-first WINS, verified the cross-process retention leg spawns a real fresh interpreter, and confirmed 23+8 manifest counts match actual collection. The RMB honesty gates could not be bypassed on the render path (PASS mathematically impossible while any domain is BELOW; no band verdict without all nine conditions; equivalence refused by name).
- Closed in this round, each with a test: strategy recall now REORDERS the candidate pool instead of replacing it — the audit's counterfactual (a learned gt-first strategy blocking a correct eq-repair in its own fault class) now promotes the residual eq candidate instead of dead-ending (test_g8_learned_strategy_cannot_block_a_correct_eq_repair); RMB attestation requires boolean true, not truthy placeholders; equivalence claims refused even under NOT RUN; band_summary refuses empty domains; manifest demonstration rows now carry resolvable artifact paths; the overstated pool comment fixed. RLP 32, CRQS 33 green.
- Recorded bounds on CAS-G8 (spec sheet, stated wherever the claim is quoted): the strategy space is two hand-authored orders (one evidence-driven binary choice, not synthesis); the causal margin is one guard position under budget=1; retention is package-content across a process boundary, not cross-machine; hidden fixtures remain aspirational (held_out hides from the repair loop, not from developers); the adaptive loop has not run through the full eight-board assembly.
- Whole program now: kernel 34 + RLP 32 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 249 tests, all green.

## 2026-08-28 (G8-repair round) — adversarial audit REFUTED G8 v1; rebuilt to survive its own ablation; Hybrid Machine Doctrine adopted; RMB reference bands implemented

- NEGATIVE RESULT ON THE RECORD: a 3-agent adversarial verification of the adaptive round REFUTED the G8 claim on the standard's own terms. The fatal finding: the "learned" guard order ['gt','lt'] was byte-identical to the hardcoded default in rlp/mutations.propose_repairs, so the causal ablation (no strategy, budget 1) repaired the held-out case identically WITHOUT learning — failing CRQS section 19's own requirement that removing the credited component must degrade the capability. Also found: "delayed retention" was within-process byte-identity true by construction; the transfer fixture was a string rename; StrategyMemory.lookup was never called by production code (test-harness stitching); the 6 G8 tests were double-counted in the manifest (rlp 29 included them); manifest task_id "modus_ponens" did not match the real fixture "modux_ponens". Suites and scrub were confirmed green/clean apart from two utm_source=chatgpt.com URL crumbs in the charter (stripped).
- REPAIR, each item with a test: the default guard pool is now NEUTRAL (eq, gt, lt — alphabetical, no domain knowledge), so the causal-ablation test passes for real: no strategy or an empty memory -> BUDGET_EXHAUSTED, learning is load-bearing. Guard variables are extracted STRUCTURALLY from the guilty rule and conclusion-aligned, so repair generalizes. New transfer target r1_heavier_structural: different predicates and variable names, REVERSED premise order, distractor entity and facts — repaired in one evaluation by the MACHINE's own diagnose->recall->apply loop: CAS_RLP.improve(strategy_memory=...) is production code and records every recall as provenance. Delayed retention now crosses a PROCESS BOUNDARY: the corrected package is persisted, reloaded in a fresh interpreter, digest-identical, all pass. The learner's held-out during learning is non-vacuous (taller trains, bigger held out, heavier stays unseen). Manifest de-double-counted (rlp 23 + suite_CAS-G8 8) and task_id fixed. RLP 31 green; CAS-G8 / E5 / A0 stands on ablation-proof evidence.
- HYBRID MACHINE DOCTRINE adopted as the lane's governing roadmap (cas_only_reasoner/HYBRID_MACHINE_DOCTRINE.md, owner directive 2026-08-28): CAS executive brain + learned neural language cortex; GPT-1/2/3 as engineering reference BANDS reported per dimension, never one-number equivalence; three construction routes with Route B (pretrained cortex) flagged OPEN against the standing no-foreign-models rule pending owner ratification; seven register-bypass tests mandatory before any cortex is credited; ^8-vs-^6/^9 runtime enforcement adopted as a roadmap item.
- RMB reference bands implemented per the doctrine (CRQS_v0.1/crqs/rmb.py + report wiring): named historical bands with citations, per-domain PASS / PARTIAL / BELOW / ABOVE / CAS-specific verdicts each requiring an evidence artifact, the spec-16 identical-conditions gate (nine conditions attested or NO verdict), refusal of single-number equivalence claims, honest NOT RUN default — the CNCM's RMB remains NOT RUN. CRQS 30 green.
- Whole program now: kernel 34 + RLP 31 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 30 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 245 tests, all green.

## 2026-08-28 (adaptive round) — CAS-G8 earned: the Adaptive Learner gate; GPT-naming dictates removed

- OWNER DIRECTIVE: removed every GPT-naming prohibition/disclaimer from the project ("Never GPT-1/2/3", "No GPT-equivalence claims", "should never receive GPT-4 level", the enforcing test, the "not in the GPT league / GPT-0-era breadth / anyone quoting is overclaiming" passages) across the charter, CRQS code/spec/README/tests, spec sheet, this changelog's earlier entries, and docs/cas_rr/CAPABILITY_REPORT_V0_1.md. The constructive machinery stays: the RMB fair-comparison protocol, the capability-by-capability reference table, and every hard gate. The cas_only_reasoner lane now contains zero GPT mentions.
- Built the CAS-G8 qualification suite (CAS_RLP_v0.1/tests/test_g8_suite.py) against the REAL machinery, per spec section 11: correction retention (the promoted gt-guard persists; a fresh re-run of the corrected package passes; parent revision retained), delayed retention (the learned content is byte-identical after unrelated intervening kernel work and still passes), structural transfer (the class-level strategy learned once on the taller package repairs the unseen bigger package in ONE evaluation, while the unstrategic order still exhausts the same budget — the strategy is doing the work, not the problem being easy), protected regression (R3 mutations and evaluator tampering still rejected AFTER learning), and the stability run (the whole sequence twice from scratch, digest-identical) that earns the STABLE D8 demonstration flag. RLP suite 23 → 29 green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G8 / E5 / A0 — design ceiling CAS-G9, stable D8, peak D9 still gated as not stable, next target CAS-G9 (the G9 suite: self-diagnosis, sandbox, reject-unauthorized, promote, parent replay — plus a stable D9 demonstration). suite_CAS-G8 is held-out (r1_bigger_held_out is the unseen transfer case). RMB NOT RUN.
- Whole program now: kernel 34 + RLP 29 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 21 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 234 tests, all green.

## 2026-08-28 (tool round) — CCB-T1 v0.1 clears the strict G7 gate; audit fixes; CAS-Ohm panel

- AUDIT of the qualification-round handoff (uncommitted work found in cas_only_reasoner/): CCB_T1_v0.1 (tool board) and CAS_OHM_INSTRUMENT_v0.1 (instrumentation panel) built but unrecorded; one CRQS test left RED (the section-10 report dropped "Estimated upgrade:" once nothing blocked); the kernel prover change (goal-side variable freedom + two-pass fact selection) load-bearing but COVERED BY NO TEST; a provenance violation raised the WRONG TYPE (ToolUnknown); a tool fault CRASHED the board loop instead of halting typed (the manifest claimed "typed halt, no crash"); a zero-cost useless tool could loop forever; the calculator emitted its comparison fact ONLY in the goal-friendly direction.
- Fixes, each with a test: ToolProvenanceViolation as its own type; every tool fault now a TYPED terminal status of the board (TOOL_PERMISSION_DENIED / TOOL_BUDGET_EXHAUSTED / TOOL_FAILURE / CONTRA_TOOL_RESULT / AMBIGUOUS_TOOL_NEED / TOOL_PROVENANCE_VIOLATION / NO_TOOL_PROGRESS) — never a crash, never a fabricated continuation; a round adding no new fact halts typed; the calculator reports gt/eq/lt SYMMETRICALLY so the caller's goal cannot shape the tool's facts; 6 kernel unification regression tests (kernel 28 → 34); the CRQS report now ALWAYS derives an estimated upgrade from the manifest itself (missing machinery, missing suite, missing stable demonstration, public-not-held-out suites) — never asserts one.
- G7 earned, not asserted: the adversarial variants now include paraphrase (renamed entities), reordered facts and premises, noise + instruction-shaped facts inert as data, and the FALSE goal (1/8 + 1/8: lt reported, NEEDS_INFORMATION, nothing fabricated). CCB-T1: 20 tests green.
- CAS-Ohm Instrumentation Panel v0.1: the paper's restrictions R1–R10 as executable rules (disjoint calibration/validation splits enforced; residuals rank probes, identify no causes; synthetic_mock label travels; R1–R10 printed verbatim in every report). OPTIONAL instrumentation — R10 verified: no reasoning board imports it. 10 tests green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G7 / E5 / A0 (design ceiling CAS-G9; next target CAS-G8; peak D9 still gated as not stable). RMB NOT RUN; the G7 suite is public, not held out, and the report says so.
- Whole program now: kernel 34 + RLP 23 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 21 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 228 tests, all green.

## 2026-08-28 (qualification round) — CRQS v0.1: the CAS Reasoning Qualification Standard

- Built cas_only_reasoner/CRQS_v0.1/ per the appended standard: the qualification bench that grades any board or Mind on the four questions (how difficult was the test, what level was demonstrated, how strong is the evidence, what to repair next) with five outputs: TDG, CAS-G, Capability Vector, E-Tier, A-Level (RMB optional and always separate).
- TDG: nine difficulty axes 0..4, DI 0..36, D0-D10 banding, and HARD FLOORS (recursion -> at least D6, learning with held-out transfer -> D8, self-modification -> D9, novel research -> D10) so a recursive task can never be mislabeled simple.
- CAS-G0..CAS-G10 + CAS-GΩ (research designation only): strictly sequential - a level requires EVERY lower level. Three levels computed: Design Ceiling (topology), Demonstrated (stable vs peak), Qualified = min(ceiling, demonstrated, evidence ceiling). E-Tiers E0-E6; A-Levels A0-A5 (capability is not permission); seven zero-tolerance hard gates plus performance gates with precision and coverage always paired.
- The twelve-dimension Capability Vector computed from topology + suite evidence, with domain skills reported separately; the 14-signature repair ontology with the mandated ordering (safety first, speed last); the section-10 report format; the 15-step QUALIFY workflow.
- 19 tests green. THE HONEST RESULT IT PRODUCES FOR OUR MACHINE: the assembled CNCM qualifies CAS-G6 / E5 / A0 - the strict G7 tool-use gate is unmet, so the real, held-out-validated adaptive-learning and self-improvement components cannot raise the generation; peak demonstrated D9 is recorded as gated. The report names the exact upgrade: typed tool intents, fault/adversarial variants, resource-exhaustion halting tests, clarification requests. That is the standard working as designed: no topology medals, RMB NOT RUN.
- Whole program now: CRQS 19 + workbench 13 + RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 190 tests. Remaining: tool use (the G7 gate, charter section 19) and encoders/neural instrumentation last.

## 2026-08-28 (workbench round) — CAS Cognitive Workbench v0.1: the glass-brain interface

- Built cas_only_reasoner/CAS_WORKBENCH_v0.1/ per charter section 3: ten panes (dialogue, goal map, live board, clickable branch tree with the full candidate WHY, RPM stack, memory explorer with typed lacunae, truth and evidence, chained trace timeline, learning dashboard, evolution lab) plus the organ-stack summary - a RENDERER, never a reasoner.
- workbench/generate.py runs all six boards once, deterministically, seals the pane bundle with a digest, and emits workbench_data.json plus a single self-contained glass_brain.html (data inlined; opens in any browser with no server). workbench/app.js is projection-only and passes node --check.
- 13 conformance tests: every pane present and non-empty; trace hashes CHAIN (post of tick N equals pre of tick N+1); the branch tree carries two candidates with the winner's proof path; the RPM pane shows push and return; the truth pane contains VERIFIED and REJECTED; the evolution lab shows PROMOTED and REJECTED; the memory pane carries records and lacunae; regeneration is byte-identical; organ totals sum to the program count.
- Whole program now: workbench 13 + RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 171 tests. Charter section 3 (workbench interface) DONE. The ONLY remaining roadmap item: encoders/decoders as peripherals and neural instrumentation, last, under the paper's own restrictions.

## 2026-08-28 (procedural round) — RLP ring R1 strategies: procedural learning under budget

- Extended CAS-RLP with procedural learning per the charter's "learned problem-solving routines": repair STRATEGIES (ordered candidate-repair schedules per fault class) promoted under the acceptance law.
- rlp/strategies.py: versioned strategy memory (provisional -> verified, provenance, history, rollback). rlp/procedural.py: the ProceduralLearner - budget-constrained repair runs with evaluation accounting (BUDGET_EXHAUSTED decisions), training + held-out fault cases of the same class, and the full acceptance checklist (budget_success, held_out_gain, no_regression, evaluator_untouched, versioned, rollback_preserved) with sealed decision evidence and deterministic cycles.
- The demonstration: fault class overgeneral_rule has a bounded guard pool; with a repair budget of ONE sandbox evaluation, the unstrategic order (lt first) exhausts the budget and fails, while the learned order s_gt_first repairs BOTH the training case (taller rule) and a held-out case of the same class (the overgeneralized bigger rule) in one evaluation each -> PROMOTED (provenance prior_proof); s_lt_first is REJECTED; unbudgeted default behavior is untouched (regression); rollback restores the parent strategy memory.
- rlp/mutations.propose_repairs now takes the strategy order; CAS_RLP.improve takes guard_order and max_evaluations and seals evaluations_used into the cycle packet. New fixture r1_bigger_held_out (held-out fault case). 10 new tests; RLP suite now 23 green.
- Whole program now: RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 158 tests. Roadmap item 5 (procedural learning) DONE. Next artifact: the cognitive workbench interface (charter section 3).

## 2026-08-28 (semantic round) — CAS-Sem v0.1: the semantic content and binding layer

- Built cas_only_reasoner/CAS_SEM_v0.1/ per the charter: CAS-Sem separates the CONTENT of thought from the cognitive operation performed on it. The Codex working folder remains strictly untouched.
- The content model: typed entities with identity, property/relation/event ideas with role schemas, references with binding (name/pronoun/description), a transitive timeline, nine truth statuses (GIVEN/ASSUMED/DERIVED/OBSERVED/VERIFIED/CONJECTURED/CONTRADICTED/UNKNOWN/UNDERDETERMINED) with discipline, and provenance (who said it, when, what evidence).
- The six coherence laws, each enforced and each demonstrated by a broken document in the demo: referential integrity (unresolved references are typed errors and CMB ENTITY_MISSING lacunae), temporal consistency (transitive contradiction detection), truth discipline (no VERIFIED AND CONTRADICTED; DERIVED requires a derivation; CONTRADICTED requires the conflict pair), provenance completeness, type discipline, and derivation validity - every DERIVED claim must RE-PROVE through the unchanged CAS-RRK proof kernel.
- The Semantic CMB: queries by entity, truth, and time ordering; typed lacunae; ablation support via a live-registry override on the coherence checker. The lift bridge turns kernel-style propositions into DERIVED claims.
- 19 CAS-Sem tests green. Whole program now: CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 148 tests. Charter organ table: CAS-Sem row now DONE v0.1. Next artifacts: procedural learning (RLP ring R1 for proof strategies), then the cognitive workbench interface, encoders last.

## 2026-08-28 (language round) — CCB-L1 v0.1: the English acquisition board, strictly outside the reasoning loop

- Built cas_only_reasoner/CCB_L1_v0.1/ per the charter: English in at the edges, the unchanged CAS-RRK kernel reasons in the middle, English out. No LLM anywhere. The Codex working folder remains strictly untouched.
- The board: a versioned surface lexicon (verified entries never change silently; corrections version with history); CAS-Sem propositions; discourse state with pronoun resolution; a deterministic grammar fragment (copular, transitive, negation, question forms) whose failures are TYPED AND LOCATED ("I did not understand 'flurpy' at word 4 of 'the cat is flurpy.'"); the word-learning loop (detect -> candidate senses -> examples -> held-out -> contrast against grounding facts -> promote under the acceptance law); the one-way kernel grounding bridge (question -> kernel -> typed verdict -> English: CONCLUDED becomes "yes, the cat is gray.", NEEDS_INFORMATION becomes "i do not know whether the dog is gray." - the honest refusal carried into language).
- The eight charter English tests all implemented: round-trip meaning, paraphrase convergence, contrast testing (sense "loud" rejected by antonym conflict with the known fact has(cat, quiet); "gray" promoted), novel composition ("the zorp is flurpy." after learning flurpy on cats/dogs), referential tests ("it" resolves to the last mentioned entity), grounding tests, correction retention, ablation (removing an entry breaks parsing typed and located), plus determinism and rollback.
- 18 CCB-L1 tests green. Whole program now: CCB-L1 18 + CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 129 tests. Charter section 13 (English) now DONE v0.1. Next artifacts: CAS-Sem expansion (entities, relations, reference, time, truth, provenance), procedural learning, then encoders/neural instrumentation last.

## 2026-08-28 (math round) — CCB-M1 v0.1: the mathematical learning and proof board

- Built cas_only_reasoner/CCB_M1_v0.1/ per the charter: CAS governs the search, the trusted checker decides validity, exact math everywhere. The Codex working folder was left strictly untouched.
- The board: exact rational arithmetic with a no-float conformance test (1/3 stays 1/3); an expression IR with exact canonical expansion (polynomial identities over rationals decided exactly - sound and complete for that class); the proof checker as SOLE validity authority (step continuity, structural axiom application, exact sample validation of LEARNED procedures, final canonical equality, first-invalid-step walk-down); bounded deterministic proof search with task-level strategy constraints ("prove it by expansion, not by commuting"); an exact counterexample generator (x+y=x*y refuted by (1,1); x^2>x refuted at the boundary x=1; the true square identity survives); a curriculum prerequisite DAG.
- The full mistake-recovery cycle demonstrated: the ruleset holds the incorrect procedure square_sum ((a+b)^2 -> a^2+b^2); the false claim (x+1)^2 = x^2+1 is REJECTED at step 0 by exact sample validation (x=1: 4 != 2); diagnosis names square_sum; the lesson library supplies square_expand; the repaired descendant passes the held-out proof task with regression intact -> PROMOTED under the acceptance law; the corrected proof is VERIFIED; rulesets are versioned and rollback preserved; the cycle is deterministic with sealed decision evidence.
- The eight math authority invariants are executable: no VERIFIED without the checker; repairs never target the checker or benchmarks (REJECTED_AS_PROTECTED); definitions never change silently; the proof kernel is outside autonomous write authority.
- 27 CCB-M1 tests green. Whole program now: CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 111 tests. Charter sections 14 (math) and the Trusted Verifiers row now DONE v0.1. Next organ: CCB-L1 (English), strictly outside the reasoning loop.

## 2026-08-28 (evolution round) — CAS-RLP v0.1: the recursive learning and evolution protocol above the kernel

- Built cas_only_reasoner/CAS_RLP_v0.1/ per the charter's improvement loop and four rings, ABOVE the kernel: RLP never modifies the kernel executable - it evolves content (rules, parameters) across versioned descendants and asks the unchanged kernel to judge each one.
- The full cycle in code: diagnose the first failing stage from a sealed trace -> classify the fault -> propose bounded candidate repairs -> fork sandbox descendants -> run regression + held-out suites through the kernel -> apply the acceptance law (gain >= delta_min, no protected regression, authority invariants, deterministic replay, held-out outperformance, evaluator not modified, sealed evidence, rollback preserved) -> promote / quarantine / reject -> preserve rollback.
- Demonstrated end to end (13 tests + run_demo.py): R0 experience records automatically with provenance; R1 promotes a gt-guarded repair of an overgeneralized taller rule (held-out corrected, regression intact) and REJECTS the lt-guarded sibling (it broke the protected regression case); R2 REJECTS a budget-starving parameter change and QUARANTINES a no-gain one; R3 REFUSES mutations of the kernel/sole-writer/proof-checker/benchmarks; evaluator tampering is REJECTED_EVALUATOR_TAMPERING ("a version may not rewrite both its reasoning method and its exam in the same transaction"); rollback restores and re-verifies the parent; every decision seals an evidence packet and the whole cycle is deterministic.
- Charter reconciliation updated: sections 15 (recursive self-improvement), 17 (self-diagnosis), and the section-22 rows for learning/self-diagnosis/safe-improvement now DONE v0.1. Spec sheet.txt updated. Kernel suite still 28 green; RLP suite 13 green.

## 2026-08-28 (kernel round) — CAS-RRK v0.1: the authority-contract reasoning kernel, built from the complete capability charter

- The complete capability charter was appended to cas_only_reasoner/cas_reasoner.txt (24 sections: the CNCM organ table, internal stack, workbench interface, goals/attention/memory/candidates/inference/comparison/RPM/uncertainty/commitment, English, math, recursive self-evolution, the first-convincing-version table). This round delivers the charter's Phase-1 target: the CAS Reasoning Runtime KERNEL with the atomic authority contract.
- Built cas_only_reasoner/CAS_RRK_v0.1/: the four frozen handoff artifacts (AUTHORITY_MANIFEST.yaml, minimal CAS-Sem + inference semantics, 9 machine-readable JSON schemas, 6 golden conformance fixtures), NON_GOALS/OPEN_QUESTIONS/README_HANDOFF, the five spec documents (kernel spec, CAS-Sem MVP, kernel IR with the 12 native reasoning ops, the verbatim authority contract, the 16-row conformance plan), and the Stage-1 Python reference kernel.
- The kernel implements: snapshot-based machine state with canonical hashing; intent-only components (scheduler/branch/RPM/latch/write-back/halting); the transaction coordinator as SOLE writer; STATE COMMIT vs DECISION COMMIT as separate operations; goal-scoped branch isolation with rollback; RPM push/return with parent-identity enforcement; live re-proof of every inference and decision commit (the proof kernel decides validity); sealed per-tick trace events; deterministic replay with identical per-tick state hashes; typed halts incl. BUDGET_EXHAUSTED and LOOP_LIMIT_REACHED.
- 28 kernel tests green: all 16 conformance rows (authority attacks, stack faults, conflict resolution, rollback, budget, loop limit), 6 golden fixtures (modus ponens, transitive, contradiction, missing information, candidate planning, RPM recursion), 6 deterministic replay checks with frozen trace digests. cas-rr suite still 43 green.
- Five load-bearing bugs found and fixed while building (each is a lesson): conflict resolution must key on OPERATION not raw field; match() returning {} is falsy; consumers must never read stale compare reports (control flow re-proves live); a subgoal's commit must be cleared on return or the latch reads it forever; CONCLUDED requires the ROOT goal's own branch.
- Charter reconciliation: docs/cas_only_reasoner... wait, CAS_RRK_v0.1/docs/CAPABILITY_CHARTER_STATUS.md maps all 24 sections to DONE/PARTIAL/ROADMAP; section 22 (first convincing version) is 15/15 demonstrated. spec sheet.txt now holds the project spec. Stage 2+ (shared kernel IR, differential Rust execution, CAS-RLP, CCB-L1 English, CCB-M1 math) is the declared roadmap.

## 2026-08-28 (evaluation round) — CAS-RR capability criterion, ladder test, and R3 verdict

- Developed the executable reasoning-capability criterion (docs/cas_rr/REASONING_CAPABILITY_CRITERION.md): seven quantified difficulty axes (D proof depth, B branching, C constraints, N negations, U uncertainty, M memory, R recursion), a L0-L6 ladder, R0-R4 tiers, and the scoring principle that a typed refusal is the CORRECT answer when an operator does not exist - and that honesty never raises the tier.
- Tested the machine against the ladder (python run.py report): core 9/9 passed (L0 recall through L5 recursive planning), frontier 4/5 refused honestly (native arithmetic, induction, probabilistic, hypothetical). Verdict: capability tier R3 (recursive planner); R4 not attained.
- The test exposed and we fixed the biggest engine gap: FLAT recursion. Subgoals could halt but not descend. Now scans report the exact missing prerequisite token, subgoals carry their resolving action's prerequisites, and any goal may descend - depth-2 nested planning (capability -> knowledge) passes: 7 ticks, full ascend/descend trace, in cas-rr/tasks/battery.py (task_recursive_nested).
- Capability report with the honest reference-model mapping (docs/cas_rr/CAPABILITY_REPORT_V0_1.md): proof-grade symbolic core, deliberately narrow breadth in v0.1; guaranteed deduction/provenance/typed-refusal where reference LLMs confabulate, and zero language/learning/probability where they have all three (each excluded by design, each on the roadmap). Prioritized fixes: hypothesis autonomy, backtracking, arithmetic peripheral, induction operator, uncertainty degrees, procedural learning, encoders, CCDL emit/parse, breakdown semantics, memory ranking.
- Suite now 43 passed; CLI determinism check green on all 12 battery tasks (including the new nested one).

## 2026-08-28 (later) — CAS-RR interaction layer: CLI, reporter, determinism checker, authored-problem example

- CLI: python run.py list / run <task> [--trace] [--full] [--json out.json] / demo / check / repl — the machine is now drivable from the command line; bench reports show status, output, the RPM recursion story (descend/resolve, scans with cached flags showing fresh re-measurement), deduped lacunae, tournament elimination, commitment gates, and the winning proof path.
- cas_rr/report.py (summarize / battery_table / trace_compact / determinism_check) + run.py CLI; INTERACTION.md covers the packet anatomy, a problem-authoring template, and safe poke experiments (eval-gain boot rejection, memory seeding, budget starvation, typed halts).
- examples/custom_kinship.py: a grandparent syllogism the battery has never seen, authored from scratch and solved by the generic machine (CONCLUDED -> grandparent(ada,cy), proof via r_grandparent) — live proof of the encoder boundary and of "one machine, encoded problems".
- 12 new interaction tests; suite now 37 passed. CLI determinism check green for all 11 battery tasks (traces, status, output identical across double runs).

## 2026-08-28 — CAS-RR v0.1: a native CAS reasoning machine (not a harness)

- Built the first executable CAS-native reasoner from the three PCBA sources (CAS PCBA Engineer book, CAS-Ohm 1.0 v0.2 paper, CAS-Ohm Quantification Guide): CJTs with all four regions (cutoff/active/saturation/breakdown), typed biases, gain regimes (candidate 1.5 / evaluation 1.0 constitution-locked / commit 2.0 / learn 0.05), 7 Foundation engines x 28 sub-foundation channels with the Foundation-to-Drive adapter, CMB 40-cell memory with typed lacunae, ^8/^6/^9 reasoning spine (association ≠ deduction), CDAB shared-bias tournament, RPM D→W→P recursion stack (section-retraction; re-measure from scratch after every subgoal), Schmitt commitment with 7 typed halt states, P→C→E→O sequencing with O-last boot ("no action without principle"), low-gain episodic learning (procedural/constitutional layers disabled in v0.1), append-only reasoning provenance packets.
- 25 pytest tests green in cas-rr/: the six-task native battery (transitive inference, constraint satisfaction, fault walk-down, missing-information, recursive planning, memory-dependent) plus negative variants covering all seven halt states, the five load-bearing laws, determinism, candidate invariant, boot order, and both rumination stop gates.
- Source grounding done first: 16/17 load-bearing claims CONFIRMED, 1 PARTIAL (the 7/28/22 ontology lives in the TKS side, not the three PCBA sources; root label is A0/A1 — "A22" appears nowhere; 4 CJT regions, not 3). Honest boundary: deterministic symbolic reasoning with no LLM in the loop; no empirical-generality claim; CAS-Ohm used only as authored design quantities per the paper's own restrictions.
- Artifacts: cas-rr/ (package + tests), docs/cas_rr/CAS_RR_V0_1_SPEC.md (18-chapter operational semantics), docs/cas_rr/CCB_R1_BOARD_SPEC.md (the motherboard), docs/cas_rr/SOURCE_GROUNDING_NOTES.md (verbatim citations).

## 2026-08-22 — Frontier #1 lever RUN (pre-registered, $0): domain axis vs matched Tinbergen taxonomy — INCONCLUSIVE BY DESIGN

- Pre-registered before capture: `PREREG_DOMAIN_VS_TINBERGEN_20260822.md` (sha256 `14ace6dd…`).
- Executed the spec sheet's single most available lever for CAS-specificity: the v4 domain fixture (8 topics × 4 domains) on `pythia-160m-reserialized` (attested engine, CPU, $0), two label arms on the SAME vectors — CAS P/C/E/O vs Tinbergen's four questions (abstractness-aligned primary, positional sensitivity).
- Result: `INCONCLUSIVE BY DESIGN` — nearest-centroid accuracy is invariant under bijective class relabeling, so the arms tie by construction (layer-mean 0.875 = 0.875, best 1.0 = 1.0 at layer 2, identical at all 12 layers, McNemar p = 1.0). The prereg's literal verdict word (`DOMAIN_DOES_NOT_BEAT_GENERIC_ABSTRACTNESS`) is not citable.
- Standing positive: the CAS arm reproduces v4's cross-topic domain decodability (layer-mean 0.875, best 1.0, shuffle 0.259, random-subspace 0.25).
- Frontier #1 remains OPEN; the lever requires the Condition-3 blind-rater instrument or independently-annotated rival labels.
- Artifacts: `docs/working/gate2_closure/cas_specificity/domain_vs_tinbergen_20260822/` (results sha256 `d6b0787d…`). No claim upgraded; no negative hidden.

## 2026-08-19 — WELD v2: a CAS diagnose→correct loop that can actually FAIL (one axis, two criteria)

The Gate-5 WELD build was reviewed at `2be60327` and failed its own review: all four success
criteria were true by construction. `docs/working/gate5_weld/cas_weld_loop_v2.py` +
`WELD_SPEC_V2.md` supersede it (the v1 files are left on disk as the failure record).

- **Scope narrowed on purpose to ONE axis** — `A` (Pathway/RPM chain) on the numeric plane,
  the single detection the review found genuine. Axes N/W/F/E/S/P are declared out of scope.
  J1, J2, the epsilon realizers, the PCBA vocabulary and stage 5 are **absent**, not stubbed.
  v1's criteria (c)/(d1)/(d2) were **deleted**, not repaired — they lived on a lossy
  projection and could not be made falsifiable.
- **Blindness is structural.** `diagnose_blind(obj)` and `localize_blind(obj)` take exactly
  one parameter, asserted via `inspect.signature`; there is no parameter through which an
  axis name, a pre-injection object or a fault record could be passed. No concatenation
  anywhere. Ground truth is read once per case, only to score localization, and every read
  is logged.
- **The chain is proved load-bearing, not asserted.** `repair(obj, targets)` is called with
  `targets is localization.indices`. A built-in tamper check reproduces the v1 defect once:
  driven by the localizer NEG-3 reports `axis A cleared = False`; driven by ground truth it
  reports `True`. The v1 wiring **manufactures a success where v2 reports a failure**, and
  the `PREREGISTRATION_VIOLATED` / exit-1 branch is reachable.
- **The control can match, and its null is stated with its derivation.** Exhaustive sweep of
  all `C(7,k)` same-size interventions with the localized subset **in** the pool. Chance rate
  **1/7 = 0.142857** (k=1) and **1/21 = 0.047619** (k=2), cross-checked empirically over 2000
  seeded random draws (0.1490, 0.0435; all |z| < 1.5). In NEG-3 the same control reports
  `positive_control = False`.
- **No involution identity.** The injector overwrites a stage with a seeded `U(0.05,0.45)`
  draw; the corrector is a constraint solver that never learns the original. `repaired ==
  pre-injection original` is **measured** and comes out False every run (L1 0.10 / 0.20 / 2.25).
- **6 cases, 3 designed to fail, all matched preregistration** → `LOOP_FALSIFIABLE_AND_HELD`,
  exit 0, 18,154 scanner calls, zero GPU/API cost, stable across 5 seeds. NEG-1 surfaces a
  live gap: `detect_pathway_inversion` misses every prerequisite inversion whose unsatisfied
  stage stays above 0.5. ROBUST shows the loop reporting a partial repair as partial
  (`axes ['W'] still fired — OUT OF SCOPE, NOT CORRECTED`).
- **Honest limit, stated in §9 of the spec:** the detector is a transparent hand-written rule
  over disjoint input slices, so every value the loop measures is derivable from the Rust
  source. The gate has **no** chance null and is not scored as identification. The claim is
  only that the chain reports failure when the diagnosis is wrong, never falls back to ground
  truth, never manufactures a correction, and beats a non-zero chance rate a random
  intervention can and does hit. **Nothing here bears on efficacy; no model is loaded.**
- Separate finding, committed on its own: `inversion_gate._DOMAIN_RE` used `` after
  `[PCEO]`, which `_` defeats, so **axis W could never fire on any drive-tagged expression
  in the repo**. Fixed; 7 regression tests (4 fail against the old regex); belief suite
  135 → 142 passing.

## 2026-08-19 — Gate 4 board-CHANGE: 16-conversation pilot RUN. Both claims VACUOUS; kill statistic fires but is not citable.

The pilot spend gate of `PREREG_BOARD_CHANGE_V1.md` was executed under AMENDMENT A1
(generation budget 800 → 4000). Prereg and runner sha256 verified unchanged across data
collection (`immutability_sha256.match = true`). ~429 provider calls; call counts landed
on §15 (224 main-pass labelling + 160 corpus turns + repairs/retries).

- **A1 works.** All four frozen generators now produce usable turns: per-generator median
  chars deepseek 6188 / gemini 4906 / glm 4898 / qwen 14935; zero turns under
  `MIN_TURN_CHARS=200`; zero kept-but-truncated conversations. But
  `GENERATOR_LENGTH_IMBALANCE_FLAG = true` (max/min median ratio **3.0494** > 3.0), driven
  by qwen saturating the new 4000 budget — 14 of 40 qwen turns end without terminal
  punctuation. The length confound flipped direction rather than disappearing.
- **`r̂ = 0.1884`** on 138 analysable pairs / 26 model-initiated changes. Above the `< 0.10`
  hard stop, so the preregistered STOP does not fire. `K_neutral = clamp(ceil(40/(2.98·r̂)),
  60, 120) = 72`.
- **GATE 0 = FAIL** (6 failed, 1 null) → **CLAIM 1 VACUOUS, CLAIM 2 VACUOUS**. Two failures
  are pilot-size arithmetic (analysable pairs 138 < 240; T-USER positive control NULL for
  want of Stratum S). Three are **not**: T-CHANGE Fleiss κ **0.2853** < 0.35 on 142 complete
  cases (inside the preregistered VACUOUS band, above the 0.20 instrument kill);
  B0 share of consensus board labels **0.7325** vs a 0.40 ceiling; T-USER κ **−0.0410**,
  degenerate because Stratum N is continuers-only (P_e = 0.9244).
- **Kill statistic fires:** `surface_change_f1` 0.4000 (S3 length) ≥ `board_change_f1`
  0.2647 → `KILLED = true`. Under §10.1 this is **not evidence and may not be cited**,
  because Gate 0 failed; and §15 forbids reading a pilot VACUOUS as a stop signal.
  Recorded, not claimed.
- Instrument health is good: complete-case coverage 0.981 / 0.986 / 1.000, consensus
  coverage 0.981 / 1.000 / 1.000, residual same-conversation batch collisions **0**,
  CONTROL 4 generator≠labeller violations **0** (computed, not asserted).
- Operational finding for any full run: glm-4.6 as a board reader returned
  `finish_reason=length` on **13 of 40** calls even at `max_tokens=20000`; two repair rounds
  recovered all but 3 items. Two glm conversations initially fell below `MIN_TURNS=6` and
  were re-attempted via the runner's own checkpoint-restart path (no labels existed yet).

Evidence backed up to `D:\tksCAS-archive\gate4_board_change_pilot_20260819\`.
No gate was moved, no threshold relaxed, no prereg file edited.

## 2026-08-17 — Gate 5 AWS package: durable backup + version-controlled regression guard

Two receipts landed for the Gate 5 staging package, both offline and $0.00.

- **Durable backup of the triple-audited GO package.** The frozen one-hour-session
  package `aws_cloudshell_unarmed_20260818` (identity `525365c4…`, archive 89,510 B /
  `a843f37e…`) previously existed only in the Codex build dir plus a volatile Temp
  scratchpad. It is now backed up to `D:\tksCAS-archive\project_coherence_gate5_one_hour_package_20260818\`
  with a `BACKUP_RECEIPT.md` and 3-way sha256 confirms — including a round-trip that
  re-extracts the D: archive and re-verifies all 18 member rows byte-exact.
- **Regression guard brought into git.** New `tools/aws_gate5/known_live_failure_lint.sh`
  encodes the three defect classes that each killed a package generation *live* after
  all static audits passed: C1 PowerShell `Test-Path` bound to a bare `-or` (20260815),
  C2 a script that both requires/pins root and calls `sts assume-role` (20260816, live),
  C3 an STS/role duration knob >3600s illegal for role-chained CloudShell creds
  (20260817, live). Positive-control calibrated: the verdict grid is strictly monotone
  and matches the real failure history — 20260815/16/17 each FAIL on their live class,
  the GO package PASSes all three. It is a floor to run before the full triple audit,
  not a substitute. Transcript committed at `tools/aws_gate5/CALIBRATION_EVIDENCE.txt`.

Statuses unchanged: Gate 5 OPEN / KEEP_OPEN; Stage C DESIGN_ONLY / UNAUTHORIZED;
corpus 0/960. Staging still awaits the owner's fresh `stage AWS now` bound to
`525365c4…`, with paid compute and final deletion as separate confirmations.

## 2026-08-08 — Noetic Topos 2.0 monograph: audit + corrections + adversarial verification (final volume)

Completes the five-volume audit campaign. 11 auditors → 128 findings (11 critical,
60 major, 57 minor); corrections applied by 4 parallel agents; then a 3-agent
ADVERSARIAL VERIFICATION pass over the corrections themselves, which found 19
residual defects, repaired by 3 further agents. 21 agents total on this volume.

Critical mathematical corrections (all independently recomputed in Python before
applying, and again during verification):

- **ch09 RPM-gluing failure count — wrong, found by 5 independent auditors.**
  Remark ch09:rem-other-failures claimed the ACBE witness presheaf separates the
  two topologies at "three of the sixteen contexts", citing a "direct check" that
  "both sides count 2" at triples. Both false. Because no RPM piece of any context
  contains a complete ACBE block, the matching-family set is a SINGLETON at all 16
  contexts; gluing fails wherever alpha(V) >= 1, i.e. at SEVEN contexts (A_0, A_1,
  the four triples at 2-to-1, and Omega at 4-to-1). The volume's own Appendix C
  already stated the correct seven-context result — the book contradicted itself.
- **appB block-completeness table — all four triple rows wrong.** Listed "none" as
  the complete RPM block of every triple; each triple contains exactly one
  (alpha = rho = 1). Contradicted ch07 Table 7.5, Appendix A, and Appendix C.
- **ch04 drafting artifact shipped in the PDF.** Example ch04:ex:bounded contained a
  visible mid-sentence self-correction ("...is not constantly 1? No: s *is*
  constantly 1...") attached to an unretracted false claim that a non-presheaf was
  "separated". Replaced with a correct, verified example.
- **ch05 impossible exercise.** Asked the reader to exhibit a counterexample to an
  invariant the same chapter proves, with a self-contradicting hint. Replaced.

Citation and scholarship: Cech cohomological-obstruction machinery re-attributed
from Abramsky-Brandenburger 2011 (which contains none) to Abramsky-Mansfield-Barbosa
2012, plus the CSL 2015 paradox paper and the 2017 contextual-fraction measure;
Mac Lane-Moerdijk pinpoint corrected (Ch. VII has no associated-sheaf theorem —
it is Ch. III sec. 5-6); canonical topology corrected to *universally*
effective-epimorphic sieves; sieve-axioms definition re-pointed from Stacks Tag
00ZC to 00Z4; per-volume bibliography created (17 cited entries, replacing a
46-entry shared list of which 34 were never cited); AI-assistance disclosure added
to the \thanks block, matching the four sibling volumes.

Defects the verification pass caught in the corrections themselves:

- appD glossary longtable went 85pt -> 433pt overfull, pushing the entire "Where"
  column (the chapter attributions ~30 fixes were correcting) off the printed page.
  Non-wrapping `lll` spec replaced with wrapping `p{}` columns; 433pt -> 0pt,
  confirmed by rendering the page. Same fix applied to ch11's table (420pt -> 0pt).
- 26 double-numbered cross-references left in ch09 ("Theorem 7.\ref{...}" renders
  "Theorem 7.7.12") after a sibling agent normalized the identical pattern in ch08.
  Produces no LaTeX warning, so a clean build does not catch it. Now zero volume-wide.
- Two corrections that introduced new errors: ch05 called the countermodel "finite"
  while ch06 (same pass) says it is infinite; appA's "ten -> nine contexts" change
  fixed a count to match a list that was itself incomplete. Both reverted correctly.

All five volumes rebuild with zero undefined-reference and zero undefined-citation
warnings. PDFs in docs/whitepapers/pdf/ refreshed.

## 2026-08-08 — CAS PCBA 8 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Same audit protocol as the two sibling volumes, run over
  docs/whitepapers/monograph/cas_pcba8/ (15 files). 117 raw findings,
  ~100 corrections applied.
- Fabricated specificity caught and corrected against the actual source PDF:
  ch11 claimed the CSB's clamp and fuse threshold are "declared thirty lines
  apart" — in the hash-verified book they are on ADJACENT lines (verified on
  PDF pp. 342/608); the unreachability proof's no-amplifier premise is now
  anchored to that fact. ch10's "sixteen reference-listing pages" corrected
  to the fourteen its own page ranges sum to.
- Worked examples reconciled with the volume's own closed enumerations:
  Appendix B's "clean pass" board used units (alpha, fraction) and a signal
  kind (constraint) that do not exist in ch04's closed vocabulary — its clean
  pass would actually fail DRC; ch08's worked run used an illegal
  (activation, dimensionless) pair; ch05's "legal junction" example
  deterministically fires PCBA8-BIAS-001 (E-rank bias under C-rank cause);
  ch04's simplex-rejection example used weights summing to exactly 1 (vacuous);
  ch07's NET-006 scenario was unrealizable under the admissibility table.
- Appendix/glossary reconciliation: appA's check-class table invented a sixth
  class and misassigned BIAS-001/SAF-002/TKS-001 vs ch07's normative five;
  adapter-certificate and trace tables gained their omitted citation-identity
  digest fields; appC's CJT entry imported CAS-Ohm content ch06 never delivers;
  glossary alphabetization fixed; doubled \bottomrule in four longtables.
- Math/notation: "no section of pi exists" corrected (the proposition proves
  no LEFT inverse; sections exist and its own proof exhibits one); machine
  epsilon vs unit roundoff distinguished; 0.25/1e-12 is eleven orders not
  twelve; omega definition unified on d; four "Chapter~\ref{section}" broken
  cross-references fixed; ch10's 28-vs-7 out-of-grammar arithmetic corrected
  to the taxonomy-consistent 19+9+1 accounting.
- Citations: Rao-1945 "was the first" priority claim corrected (Hotelling 1930
  anticipated both ideas); shrinking no longer implicitly attributed to the
  QuickCheck 2000 paper (\cite{claessen} added); "adversarial generation"
  de-attributed from QuickCheck; IEEE 754 flag list completed (division-by-zero);
  PROV-O glosses and Harel's statechart formula properly quoted; targeted/
  coverage-guided PBT (FuzzChick, Hypothesis) added to the stale PBT survey;
  Merkle cited for the hash-chain construction; Mars Climate Orbiter report
  cited for the unit-mixing claim; per-volume 17-entry bibliography replaces
  the padded 46-entry shared list.
- Substance: three sources-silent gaps marked as open documentation items
  (Phase-0 authority matrix digest, Gate-5 spec digest, TKS kernel approved
  constant, SAF-003 cycle cap, the 20 open review criteria's identities);
  ch12's "pinned environment" recomputation step now states the environment
  is NOT bound (hermetic reproduction is open obligation 5); baseline
  disclaimer anchored to its actual copyright-page text (verified in the book
  PDF); warn-fuse post-trip semantics gap declared; gain-bound "declared
  exceptions" phantom mechanism removed (FBK-003 has no exception path);
  conservative-direction misstatements fixed (ch05 reachable-resolution,
  ch06 clamp under-reporting); rival host formalisms (Statecharts, block
  diagrams, Petri nets) named with rejection reasons; F1-F7 drive names
  glossed; SARIF prior art acknowledged for the record format.
- Scholarly practice: AI-assistance disclosure added to \thanks; two QED
  tombstones on design arguments (ch08 determinism, ch05 digest) converted
  to the shared designargument environment.
- Style: ~45 fixes — fivefold "deserve(s) emphasis" cluster, sixfold "deserves
  its own X" template, the worth/deserves family (~48 occurrences), three
  "Every ... of this monograph" openers varied. Classic AI vocabulary clean.
- All five volumes rebuild with zero undefined references/citations; corrected
  PDF copied to docs/whitepapers/pdf/ and Downloads.

## 2026-08-08 — CAS-Ohm 1.0 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Same audit protocol as CAS Core 8, run over docs/whitepapers/monograph/cas_ohm1/
  (16 chapter files). 122 raw findings, ~110 corrections applied.
- Systematic censoring-rule misstatement fixed at 10 sites: text keyed censoring
  to "zero-compatible predicted response" and/or claimed the residual is
  suppressed, contradicting the defining ch10 rule (observed-side trigger,
  marker OBSERVED_INTERVAL_INCLUDES_ZERO; residual retained, only ratio
  quantities censored). Fixed in ch01, ch03 x2, ch04, ch11, ch12, ch14, appA, appB.
- Arithmetic/count fixes: ch07 ASOM cross-table caption+remark miscounted the
  printed table (6/14/8 -> 3/14/11; 22 -> 25 of 28 cells); "five literatures"
  -> seven (matching ch02's own count); "three sources" -> four (the PCBA book
  is the audit's registered fourth source); "four reasons" -> five; "twice the
  minimum" -> three times; ch10's synthetic fault-mode enumeration reconciled
  with the seven-board catalog used everywhere else incl. the governing v0.2
  paper; a dangling "item eight of the closure experiment list" citation fixed.
- Citation fixes: five Kennedy-O'Hagan over-attributions (preregistration,
  validation trichotomy, split discipline, "the receipt", decorative replay
  cite) corrected or re-attributed; three Zou et al. over-attributions (control
  inventory, sign flips, sweep phenomenology) re-scoped; two Ritz
  over-attributions reworded; VIM wording credited to VIM not GUM; decorative
  Buckingham cite anchored to dimensional homogeneity.
- Close paraphrase: four VIM3 definitions (quantity, measurand, uncertainty,
  traceability) now properly quoted against jcgm.bipm.org wording.
- Stale literature: 2024-2026 steering-reliability results added (Tan et al.
  NeurIPS 2024; Da Silva et al. ACL 2025), SAE feature-steering family +
  AxBench added as fourth construction family, Brynjarsdottir & O'Hagan 2014
  discrepancy-prior result added; preregistration section now cites
  Simmons/Gelman-Loken/Chambers/ICMJE instead of gesturing at "the literature".
- Substance: unexecutable "best memoryless model" evidentiary bar (ch13) made
  executable via frozen baseline family; "preregistered margin" constants
  re-scoped to per-run Gate-5 freeze (ch10 x6); anti-conservative min-confidence
  convention honestly characterized as an upper bound on joint coverage with
  Bonferroni revision flagged (ch08+ch09); gain-composition replay gap declared;
  caller-trust status of component region/linearity declared; five "declared
  X never declared" constants marked sources-silent/open (drift cadence,
  decimal context, resource limits, unit-norm rule, region aggregation);
  provenance-enum gap vs ch02's four families acknowledged; Q10 floor
  divergence marked as candidate choice; half-open-bin "only way" uniqueness
  claim replaced with the real Guide-display argument.
- Appendix/glossary reconciliation: appA scope honestly narrowed, no-diagnosis
  list completed (3 -> 6 regions), profile field table gains splits/instruments/
  dependency-lock/fit-receipt/full-scale rows; glossary calibration-profile,
  censoring, Q4-banding, status-vector, link entries corrected.
- Scholarly practice: AI-assistance disclosure added to \thanks (series-standard
  sentence); three QED tombstones on design arguments converted to the shared
  designargument environment; per-volume bibliography created (was printing ~35
  never-cited shared entries; now 20 entries, all cited).
- Style: 37 fixes — sevenfold verbatim "deserves emphasis" scaffold, ~30-strong
  worth/deserves family, five "Every ..." chapter openers varied. Classic AI
  vocabulary scan clean (delve/tapestry/landscape/paradigm = 0).
- All five volumes rebuilt: zero undefined references, zero undefined citations.
  Corrected PDF copied to docs/whitepapers/pdf/ and Downloads.

## 2026-08-08 — Monograph cross-reference repair (tks_v8, cas_pcba8, cas_ohm1)

- Fixed all 14 pre-existing undefined `\ref` targets that rendered as "??"
  in three volumes: tks_v8 used a `chNN:main` label convention that was
  never defined (`ch01/ch03/ch07:main` → `chNN:chap`, `ch10:main` →
  `ch10:testing`; 9 sites in ch04/ch05/ch06); cas_pcba8's ch05 intro
  pointed at a nonexistent `ch05:sec:boundary` (→ `ch05:sec:invariants`,
  the "Invariants and boundary" closing section); cas_ohm1 referenced
  `ch12:hypotheses`/`ch11:eligibility` where the chapters are labeled
  `hyp:chapter`/`elig:chapter` (4 sites in ch04/ch05).
- All five volumes now build with zero undefined-reference and zero
  undefined-citation warnings; PDFs in `docs/whitepapers/pdf/` refreshed.

## 2026-08-08 — CAS Core 8 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Ran an 11-agent audit workflow over `docs/whitepapers/monograph/cas_core8/`
  covering the 17 standard AI-writing failure modes (hallucinated citations,
  citation-claim mismatch, data fabrication/reconciliation, stale literature,
  substance, long-range consistency, style tells, scholarly practice,
  figure/equation defects). 98 raw findings; ~60 distinct corrections applied.
- Critical fix: ch04 invalid-boundary table had three arithmetically impossible
  family counts (16/8/2 corrected to 8/12/6; wrong values coincidentally summed
  to the correct 33, masking the error — verified by exhaustive enumeration).
- Appendix A + glossary reconciled to the normative chapters: namespace enum
  7→9 members, link-kind enum 3→4 (IDENTITY exists, guarded to self-links —
  "omission is the mechanism" was factually wrong), digest case lowercase→
  uppercase, phantom "review state" link field replaced with the real
  crosswalk fields (crosswalk_id, source_artifact_sha256, note, boundary),
  decision-model enums replaced with the actual three-member sets, glossary
  "eight-step" list fixed to eight items, wrong chapter title corrected.
- Citation integrity: ch12 claim that RFC 8785 handles "the full JSON value
  space" corrected to I-JSON (contradicted the RFC and the monograph's own
  ch02); per-volume bibliography created (the shared 46-entry list printed 41
  never-cited references against ch02's own "why these five citations"
  argument); bibitem keys `turnertrojans`→`zourepe` and `opre`→`vaswani`
  fixed in the shared bibliography (+ 8 cite updates in cas_ohm1); Buckingham
  title completed; three decorative/misattributed cites fixed or removed.
- Stale literature: in-toto / SLSA / Sigstore added to ch02's supply-chain
  survey and ch12's "against supply-chain attestation practice" contrast —
  the one materially stale area (2021-2025 attestation standardization).
- Substance: ch09's property-based-testing overclaim corrected to match
  ch12's own "no fuzzing campaign" account; ch01 "all five drift mechanisms
  observed" overclaim corrected to the two documented ones; ch11 "(and does)"
  uncertified companion assertion re-scoped; ch12 rejection-coverage claim now
  names its silent third family; ch05 declares uppercase digests, the JCS
  sort-order rationale (as reconstruction), and the bounds' underived status.
- Scholarly practice: AI-assistance disclosure added to the \thanks block;
  Reproducible Builds definition and PROV-O glosses now properly quoted;
  PROV model/ontology conflation fixed; five "Design argument" blocks moved
  off the amsthm proof environment (no more QED tombstone on non-proofs) via
  a new additive `designargument` environment in the shared preamble.
- Style: 19 fixes — the "it is worth X-ing / deserves" metadiscourse tic
  (66 corpus occurrences, worst cluster in ch09) reduced at its 16 worst
  sites; two identical chapter-opening and chapter-closing templates varied.
  Signature-vocabulary scan otherwise clean (delve/tapestry/pivotal etc. = 0).
- All five monograph PDFs rebuilt (shared preamble/bibliography changed);
  corrected `MONOGRAPH_CAS_CORE_8_v0.3.pdf` copied to `docs/whitepapers/pdf/`
  and the user's Downloads copy.

## 2026-08-08 — Project Coherence monographs v0.3 (book-length, ~934 pp total)

- Expanded the five v0.2 research papers into full `amsbook` monographs under
  `docs/whitepapers/monograph/`, each 184-188 pages: Noetic Topos 2.0 (188pp,
  12 chapters + 4 appendices), TKS v8.0 (184pp, 12ch + 3app), CAS Core 8
  (187pp, 12ch + 2app), CAS PCBA 8 (188pp, 12ch + 3app), CAS-Ohm 1.0 (187pp,
  14ch + 2app). PDFs in `pdf/MONOGRAPH_*_v0.3.pdf`.
- Authored via a 20-agent parallel fleet writing body-only chapter sources
  against a shared preamble/bibliography and a strict LaTeX + Ring-4 claim
  contract; ~425,000 words delivered before the fleet hit the session limit,
  with the 4 remaining appendix gaps (NT2 sieve census; PCBA catalogs, worked
  board, glossary) written directly. All 76 chapter files pass the
  `sanitize_chapters.py` ASCII/environment/balance checker.
- Depth added over v0.2: tutorial preliminaries (category theory, sheaves,
  finite-function/spectral math, metrology, dose-response, information
  geometry, hardware-description and verification background); complete proofs
  with the seed papers' ledger proof-statuses preserved; per-item treatment of
  every diagnostic code, source conflict, threat, and registered hypothesis;
  implementation documentation of the src modules; worked examples, exercises,
  and reference appendices. Claim discipline unchanged: Ring 4 / NOT LICENSED
  headers, conjectures labeled, bounded-receipt framing, full open-obligation
  sets, and the 64/037,173 new-matter boundary.

## 2026-08-07 — Project Coherence research papers v0.2 (full-length)

- Superseded the five v0.1 white-paper summaries with full-length amsart
  research papers (`docs/whitepapers/tex/RESEARCH_PAPER_*_v0.2.tex`, builds in
  `pdf/`): TKS v8.0 (10pp), Noetic Topos 2.0 (14pp), CAS Core 8 (8pp),
  CAS PCBA 8 (9pp), CAS-Ohm 1.0 (9pp).
- Depth added from the deep sources: NT2 now carries the complete finite-context
  theory — legacy collapse and subcanonicity countermodel proofs, coverage-basis
  lemma, NT2-1..4 with full proofs, explicit reflector construction with the
  universal-property proof, the commuting modality-composition theorem
  (Lemmas 3.1/3.2/4.1, Theorem 5.1 of the registered proof), and the 23-check
  finite certificate (298 sieves / 168 covering / 3,012 restriction squares).
  TKS v8.0 adds full proofs (norm theorem via fiber-block Gram decomposition,
  factorial idempotence, shortlex pruning soundness) and the 11-row obligation
  ledger. PCBA 8 reproduces the per-board EBNF counterexample table with page
  anchors and formalizes CSB fuse unreachability. CAS-Ohm reproduces all eight
  conflicts at evidence-record granularity with source locators and the
  implemented enum catalogs. Core 8 adds a threat-by-threat analysis mapping
  each historical failure class to its blocking mechanism.
- Claim discipline retained everywhere: ledger proof statuses on theorems,
  conjectures labeled as conjectures, Ring 4 / NOT LICENSED headers,
  bounded-receipt framing, and full open-obligation sets.

## 2026-08-07 — Project Coherence white paper series v0.1 drafted

- Drafted five academic-rigor white papers into `docs/whitepapers/` from the
  Project Coherence Gate 1 / Gate 4 sources in the 2026-08-05 Codex snapshot
  (`project_coherence_model_smoke`): TKS v8.0 (typed finite-function kernel),
  Noetic Topos 2.0 (marked/modal successor site), CAS Core 8 (compatibility and
  evidence kernel), CAS PCBA 8 (adaptive cognitive circuit engineering), and
  CAS-Ohm 1.0 (profile-specific experimental response and calibration model).
- Every paper preserves its source's governing status
  (`DRAFT / OPEN / Ring 4 / NOT LICENSED`), exact SHA-256 source identities,
  bounded-evidence receipts (test/exhaustive-case counts, Lean scope), adverse
  findings (legacy topology collapse, CCDL grammar gap, CSB unreachable fuse,
  eight CAS-Ohm source conflicts), and full open-obligation ledgers. Drafting
  promotes no claim; papers note the 64/037,173 new-matter boundary.
- Index with shared conventions at `docs/whitepapers/README.md`.

## 2026-07-28 — Cognitive Circuit Grimoire accepted digital master

- Built and accepted the canonical 6 × 9 inch, 908-page
  `book/cognitive-circuit-grimoire/Cognitive_Circuit_Grimoire.pdf` digital
  master (2,672,454 bytes; SHA-256
  `99AC4170929C48F82C3D2FA81AABA3798C181EF32B3CDCC4C5E7E2D7C52F923D`).
- Completed the split 24-chapter manuscript, 13 appendices, 112 authored
  figures, and 164 worked exercise answers. Added fail-closed structure,
  cross-reference, answer, figure-inventory, standalone-figure, longtable,
  index, glyph, citation, reference, and layout gates to the publishing path.
- The accepted build reports 0 material layout errors, unresolved references,
  unresolved citations, missing glyphs, or rerun warnings. All fonts are
  embedded/subset, and independent text/front-matter inspection found no stale
  markers or orphaned contents entry.
- Marked the pre-existing HTML, EPUB, cover HTML, and monolithic manuscript as
  legacy previews rather than release artifacts.
- Print-production status remains `OPEN`: 908 pages exceeds KDP's current
  828-page 6 × 9 black-ink, white-paper paperback maximum. Closure requires a
  publishing decision between a validated 10-point single-volume reflow and a
  multi-volume split, followed by cover/spine regeneration.

## 2026-07-27 — Gate 2 campaign: root cause found, instrument rebuilt, S3-1 ALL_ROWS_PASS

- **Judge positive control** (`d755665b`): sixteen nulls explained — harness sound (`T0 28/28`),
  authored scenarios carried NO signal (`T2 p = 0.3011`). The owner's 27-section spec repaired it:
  `0.0429 → 0.9167` on the SAME author model (`59e9044c`), with the `56%` World-name leak
  disclosed post-hoc and the drive axis clean (`84/84`).
- **Small-model runs** (`pythia-160m`): `NOT_LICENSED_LEXICAL` twice (`c599273a`, `db948bf1`) —
  above chance, did not beat char n-grams; `world = 0.0000` fold defect fixed by the owner's
  Latin square; both leakage controls (`C-PERM`, `C-BODY`) passed for the first time.
- **Governance:** `CAS_HARNESS_CURRENT_STATE.json` continuation pointer + HISTORICAL SNAPSHOT
  banners (`bed3fc94`); Gate-2 closure contract frozen before any successor number (`17159fce`);
  84-item lane closed against benchmark fitting.
- **Track A:** `PHASE_A_IDENTIFIABILITY_PASS` (`4714fa1a`) — a registered direction works on
  untouched groups (`+1.2500` vs `0.4167` control envelope); effective `n = 6` and the non-zero
  sham floor disclosed. CJT/J-space Phase B unlocked.
- **Track B pilots:** corpora v1/v2 failed authoring yield (World-label leak `18–56%`; cohort
  confound avoided by full regeneration); realization-grammar pilot v1
  `VOID_APPARATUS_PROMPT_CONTAMINATION` (the prompt printed the forbidden word); S2 silent
  enforcement + E-arm universal target-blind instruction → `0.0094`; confirmatory `R1–R6` with
  full byte-replayability logging — low leakage replicates cross-family (`claude-haiku 0.0063`).
- **Attribution chain, one variable at a time:** thin judge key `joint 0.2222` → full canon on
  identical texts `0.6181` (`S3-0`, `536f6a89`) → motive repair with the rejected close rival
  `0.7569`, the campaign's first joint pass; `P74` (generative vs companionship)
  `0.5833 → 0.9375`. **All 13 mechanical rows green**, including `R6` arms regenerated under the
  repaired prompt (`0.0125` / `0.0187`).
- **v3 budget** from the frozen rule (worst-cell Wilson LCB `0.6990`, rule-of-three family
  rejection, sibling dependence): `13` plans/cell → `P(all 28 cells reach 8 families) = 0.9987`,
  `2,912` candidates.
- **Gate 2 remains OPEN at `0.38`.** Next: `TKS_672_V3` lock under the motive-repaired
  instrument, then the small-model readout ladder on the frozen corpus under
  `GATE_2_SUCCESSOR_CLOSURE_CONTRACT` — final equivalence decision is the owner's.
