# HELM multi-session behavioral evaluation — frozen plan (DRAFT v0.1, not yet frozen)

**Date:** 2026-10-06 PDT
**Serves:** directive `docs/directives/2026_10_06_helm_lasting_memory_and_restart_recovery.md` §4 (lines 67–82 of the plain-text copy) and §5 (lines 83–99); vision `docs/HELM_VISION_AND_ROADMAP.md` roadmap steps 3, 4 and 5.
**Extends:** `docs/working/revision_streams_contract_2026_10_06.md` (the Revision Streams contract; its §0 wording rules, §6 unit/balance/fingerprint discipline and §7 classes are inherited, not replaced).
**Status:** proposal. Nothing in this document grants merge, run, purchase, credential or outreach authority. It becomes "frozen" only when the artifacts in §7.3 are hashed and the manifest is committed; until then every number is a target and every sentence is editable with a dated amendment log entry (§11).
**Authors of record for this draft:** Claude (read-only drafter, this session). Implementation custody and evaluation custody are separated in §7; the drafter of this plan is on the implementation side and therefore must not hold the held-out seeds.

Code citations are to the working tree at `17dbe7321` (`git rev-parse HEAD` in `/home/user/noetic-compass`, which is PR 248's head `17dbe73` over base `4377a7d`).

---

## 0. Gate answer (vision §3), written before anything else

**Ability.** 3 (Retains), with 6 (Organizes with RPA) as a secondary comparison and 2 (Learns) only in the narrow composition sense of §4.6 below. Not 4, 5 or 7.

**Observable behavior, before/after on a named input.** On a frozen, generated event stream for seed *s* (held-out, custodian-drawn), split into five segments run in five fresh operating-system processes: a chain taught in session *k* makes `ASK(c0, ch)` answer YES in session *k+1* without being retaught (the untaught twin stream of the same seed answers GAP at the same position); a RETRACT or NEGATION of a link in session *k+1* makes that same ask answer GAP or INADMISSIBLE in session *k+1* and again in session *k+2*, with every dependent held conclusion withdrawn, before and after the process boundary; a FACT that promotes an earlier told guess changes a denial-backed NO into INADMISSIBLE, and its retraction changes it back.

**Control that lacks the mechanism.** Path P0, fresh recompute from the accepted event history (`revision.replay`, `controls.ctl_recompute`), which has no held state and no persistence beyond the log; the untaught twin stream, which lacks the teaching; for answer reuse, path P1 (walk-first), which lacks the record index; for RPA, path P2 (record-first with an ordinary keyed index), which lacks the atlas.

**Pass criterion and denominator.** Exact agreement with the custodian's independently computed expected answers on every deterministic probe of every seed (denominator: probes per world, as `scoring.py` counts them, `scripts/cas_rpu/scoring.py:3–6`); zero stale or unsupported fast-path answers (denominator: fast-path hits); zero cross-context answers (denominator: asks in a context with a name collision); zero guesses promoted without an accepted event (denominator: G-class probes); every acknowledged update recovered and every replayed update applied exactly once at every injected fault point (denominator: fault injections). The speed claim has its own criterion, §1.4.

**What it will not show.** It will not show permanent retention, neural learning, retention under failures outside the declared failure model, survival of storage or host failures the fault schedule does not inject, reading of open English, or that any path is faster than recomputing from the log on this family (fresh recompute measured at 0.043 ms per item against the organism's 0.86 ms, §3.4).

---

## 1. Hypotheses and exact claim wording

Every claim below is bounded by the control that lacks the mechanism (vision §2). The forbidden wordings of contract §0 apply: no "load-bearing" without "relative to the solver that lacks it", no "necessary", no "superior". A single counterexample blocks the affected claim (§5.4).

### 1.1 Retention (H-RET)

*Hypothesis.* An accepted fact, correction or retraction consumed in session *k* still determines the relevant answer in sessions *k+1 … 5*, each a fresh OS process, without being presented again, on every path P1–P3.

*Claim wording if it passes (and only this):* "On the held-out set of 20 seeds × 2 worlds × 5 sessions, every X-, D-, K-, N-late- and C-cross-class probe answered after a process boundary agreed with recompute-from-the-accepted-log, and every untaught twin probe answered GAP; 0 of *n* post-boundary answers were stale, unsupported or cross-context. This establishes retention across the sessions, restarts and injected faults listed in §4.9, relative to a solver with no persistence (P0 answers only because it re-reads the whole log) and relative to the untaught twin."

*Will not show.* Retention beyond five sessions; retention through faults not injected; that held state is cheaper than recompute (that is H-SPEED, separately); anything about neural state.

### 1.2 Reasoning and transfer (H-TRX) — narrow composition sense only

*Domain.* `leads_to` reachability over opaque two-letter tokens (`scripts/cas_rpu/revision.py:903–913`). A "lesson" under the current frozen contract is a chain segment given as FACTs. "Transfer" means a *new* query pair whose only route uses the retained segment plus links given later (T-compose), as opposed to re-asking the taught pair (T-exact).

*Hypothesis.* On T-compose probes, every path answers YES from the retained segment in a later session, the record-first paths log a *miss* (the pair was never asked, so no record exists) and fall back to derivation, and the untaught twin answers GAP.

*Claim wording if it passes:* "The retained chain segment was reused to answer *n* new compositions it had never been asked, against an untaught control that answered GAP on all *n*; record-first paths answered 0 of *n* T-compose probes from the index, so this reuse is derivation over retained facts, not exact-answer lookup."

*Will not show.* Transfer of rules, recipes or anything with variables (the grammar has none: `scripts/cas_rpu/events.py:33–38`); learning in the vision §2 sense beyond composition over a graph; generalization outside `leads_to`.

### 1.3 Cooperation (H-COOP) — declared out of scope for this run

The directive's cooperation outcome requires a second independently developed component exchanging a lesson through the CNCM interchange envelope (directive lines 97, 108–111). Vision §4 row 7 records that no DeepSeek owner is verified, conformance fixtures do not exist, and the polarity/negation-predicate difference is unreconciled. This plan therefore reserves the slot and makes no cooperation hypothesis. If fixtures and an owner are verified before freeze, a cooperation section is added by amendment (§11) with its own expected outcomes; otherwise the report states "cooperation: not tested" and nothing else.

### 1.4 Speed (H-SPEED)

*Declared repeated-query workload* `W-rep`: the held-out seed streams with knob `repeat_ratio = 0.5` (§3.3), default `StreamDifficulty(hops=3, distractors=4, probes_before=1, shadow=True, interleave=2)` (`revision.py:181–196`), default episode count per seed, both worlds.

*Hypothesis H-SPEED-reuse.* Total elapsed time for the entire five-session stream (§6.1 boundary) on P2 is at least 10% lower than on P1.
*Hypothesis H-SPEED-rpa.* Total elapsed on P3 is at least 10% lower than on P2.

*Statistic and interval, frozen.* Paired unit = one (seed, world) stream, 40 units. Each unit is run *R* = 7 times per path, with the 4 paths interleaved in a randomized order per repetition block (so drift affects paths equally); the per-unit measurement is the **median** of the 7 repetitions. Paired difference *dᵢ* = (T_baseline,i − T_candidate,i) / T_baseline,i. Estimate = mean of *dᵢ*. Interval = **bootstrap percentile 95% CI over the 40 paired units, 10 000 resamples, resampling seed 20261006**, computed by a script hashed into the manifest. Secondary (reported, not decisive): Wilcoxon signed-rank one-sided p-value and the Hodges–Lehmann median difference. The claim passes iff the point estimate ≥ 0.10 **and** the lower bootstrap bound > 0.

*Claim wording if it passes:* "On workload W-rep, P2 reduced total elapsed time relative to P1 by *x*% (bootstrap 95% CI [*l*, *u*], 40 paired units, 7 repetitions each, median per unit), on the machine and storage named in the manifest. This is an engineering threshold chosen to avoid celebrating timing noise; it is not a promised result and does not transfer to other workloads, which are reported in §6.6 even where they regress."

*Will not show.* That reuse is faster than fresh recompute (P0 is reported; it is expected to be the fastest on this family); that the gain holds at other repeat ratios, depths, update rates or state sizes (those are reported, not claimed); anything about correctness (a correctness-preserving result below 10% still supports H-RET and is reported as "retained behavior, speed target not met", directive line 93).

*Pre-registered expectation to be honest about.* PR 248 measured that the organism's repeat asks are not cheaper than first asks because `HypothesisBank.surface` walks every live proposition before a standing conclusion is hit (`docs/working/cas_rpu_revision_streams_2026_10_06.md` §5.4; `scripts/cas_rpu/organism.py:633` adds `len(self.ws.props)` on every ask). P1 therefore carries that walk on every repeat. A P2 gain, if any, comes from skipping the walk on a valid hit; a P3 gain over P2 has no mechanism predicted by the drafter, and a measured zero for H-SPEED-rpa is the expected result and will be reported as zero.

---

## 2. The four paths on identical work

All four paths consume the **same frozen event stream in the same order with the same split map**, in fresh OS processes at the same boundaries, under the same durability contract (the memory contract v1, roadmap step 2, which must exist before this plan freezes), on the same machine, in interleaved order. Anything not listed in a path's row is identical across rows and enforced by shared code (the discipline of `scripts/cas_rpu/ablations.py`: a declared `overrides` surface and a test that nothing else moved).

| path | id | what answers an ASK | what persists | what is rebuilt at session start | reported costs specific to it |
|---|---|---|---|---|---|
| Fresh recompute | **P0** | `controls.ctl_recompute` semantics (`scripts/cas_rpu/controls.py:321–378`): the accepted event log is replayed into the pair sets, then one BFS per ask. No held conclusions, no records. | the accepted event log only (journal, framed, checksummed) | the pair sets, from the whole log | **construction cost** (log open, verify, decode, replay into sets: time, bytes, events) and **replay cost** per query (BFS work units, time), separately (directive line 70) |
| Current walk-first | **P1** | the PR 248 `Organism` unchanged (`organism.py:432–513`): every ASK runs `processor.run_in` against the living workspace | the log, plus snapshots of the organism's accepted state as the memory contract defines them (not `Workspace.snapshot`, which is an inspection summary: `scripts/cas_rpu/workspace.py:482–488`) | the organism from snapshot + journal tail, or from the log alone when no snapshot is valid | the persistence plumbing added for this comparison, documented as the adaptation (directive line 71) |
| Record-first, no RPA | **P2** | a feature-flagged guarded positive-answer path: canonical query key → ordinary keyed index → full validation (§2.1) → answer with state version and trace; else fall back to P1's derivation and commit the record through the single writer | log, snapshots, and the record index (disposable: rebuildable from the log) | as P1, plus the index (rebuilt or validated) | hit / miss / reject / fallback counts with reasons; index size; rebuild work |
| Record-first, with RPA | **P3** | identical to P2 except candidate *location* goes through the atlas (RPA) instead of the keyed index; validation, persistence, fallback and commit code are the same functions | as P2, with the atlas in place of or alongside the index (disposable, rebuilt only after restore validation, directive line 20) | as P2, plus atlas rebuild | atlas size, branch count, rebuild work; everything P2 reports |

### 2.1 Validation every record-first answer must pass (P2 and P3 identical)

Taken from directive lines 36–40, binding on both paths with one shared implementation: canonicalize the query without changing meaning; bind context, branch, world mode, polarity and semantics version; reject unsupported English rather than convert it; read one committed state version; look up candidates (index or atlas); check commitment, context, provenance and every supporting fact and rule at current versions; preserve clean-route, disputed-route and INADMISSIBLE precedence (`Workspace.ask` alone is insufficient, directive line 38); validate against one pinned version (retry or pin if an update commits meanwhile); return with state version and support trace only after all checks pass; otherwise derive, verify support, commit. **Initially only a still-valid held positive is reused; denial, conflict, INADMISSIBLE and unknown stay on the derivation path** (directive line 34). Whole-context invalidation first; dependency-specific invalidation only after the first held-out run is clean (directive line 34; vision §5 step 4).

### 2.2 What each pairwise comparison supports, and only that

| comparison | attribution it supports | attribution it does not support |
|---|---|---|
| P0 vs custodian reference | persistence of the accepted log is correct (any disagreement is a log or replay defect, since P0 has no other state) | nothing about held state |
| P1 vs P0 | the cost of held-state reasoning versus replay on this family (design measurement, two different mechanisms); correctness agreement of the persisted organism with the log | not "incremental maintenance beats replay" (contract §12 C6) |
| P2 vs P1 | the value of answer reuse: correctness preserved or not; elapsed, latency, memory, disk, recovery deltas (directive line 91) | nothing about RPA |
| P3 vs P2 | the extra value of the atlas for locating records, everything else held constant (directive line 73) | nothing about RPA's value for explanation or branch organization unless §9.5 separately demonstrates it (directive line 93) |
| taught vs untaught twin (any path) | that the answer depends on the teaching, not on the query shape | nothing about which path retained it |

If P2 or P3 regresses updates, memory or recovery while speeding queries, the full tradeoff is reported (directive line 91).

---

## 3. The behavior suite

### 3.1 Size

**20 independent seeds × 5 successive sessions per seed = 100 sessions**, each session a fresh OS process, per path per world: 100 × 4 × 2 = 800 scored process launches for the main suite, plus the untaught twins (§3.3) and the fault schedule (§4.9). This is the directive's bounded coverage target (line 75), not proof of permanence.

### 3.2 What one "session" contains

A session is one OS process (`python -I <harness> --seed s --world w --path P --session k --store <dir>`) that, in this order and with phase timestamps written to its metrics file:

1. **Start**: interpreter start, imports, construct the engine for path P (measured here at 74 ms mean for `Organism()` from a cold interpreter, §3.4).
2. **Restore** (sessions 2–5; session 1 starts from an empty store with a declared genesis): open the newest compatible complete checkpoint, verify hash/schema/semantics/stream identity, replay committed later events once in order, rebuild or validate disposable indexes (P2 index, P3 atlas), compute the accepted-state digest and compare it with the declared reference for the acknowledged prefix, and **refuse to serve** if any check fails (directive lines 57–59). The restore-validation timestamp must precede the first answer's timestamp; the heartbeat's post-event audit does not count (directive line 40).
3. **Consume** its segment of the seed's event stream: for each event, bind identity (context, branch, world, polarity, semantics version), apply through the single writer, reach the declared durable boundary, acknowledge to the harness; for each ASK, answer with verdict, lacunae, contested keys, state version and support trace; after each event, report withdrawn keys and the heartbeat result exactly as `Organism.consume` does today (`organism.py:470–513`).
4. **Checkpoint**: at the segment's end (and at any mid-segment points the split map declares), snapshot from a pinned committed version into a temporary location, verify contents and hash, publish through an atomic manifest, retain the prior valid checkpoint (directive lines 55–56).
5. **Exit** normally, or be terminated by the fault schedule at a declared point (§4.9).

Session 1 is the teaching base and contains no cross-session probe. Sessions 2–5 each contain **at least one probe whose answer depends on state established in an earlier session**; a session with none would test nothing about retention and the generator refuses such a split (new code E-SS-001).

### 3.3 How a seed's stream is built and split

- The stream for seed *s* is a sequence of **episodes**. An episode is one item in the sense of `revision.py:951–1116` (`_draw_item`) or one of the new cross-session patterns of §4. Episodes within one **context** draw tokens without replacement from `AA..ZZ` (676 tokens, `revision.py:903–904`; ~15 tokens per default episode, so ≤ 45 episodes per context). Distractors come from spare nodes that no chain node reaches, so routes never form between episodes (`revision.py:1006–1017` docstring); the E-RS-006 fairness guard is run over the whole seed stream per context, not per episode.
- A seed stream carries **one instance of every variant** in the extended catalog (§4.10 lists them: 16 existing + the new ones), shuffled, with the cross-session variants placed so that their probes fall after boundaries. Target ≈ 30 episodes ≈ 450–500 events ≈ 90 probes per seed per world (extrapolated from 13.1 events and 2.2 probes per item at n = 40, §3.4). The exact episode count is fixed at freeze and recorded in the manifest. *Measured on landing (amendment log, 2026-10-06): 27 episodes, 385 events, 82 probes per seed per world.*
- **Split map**: five segments; boundaries fall between episodes except for the cross-session variants, which straddle by design. The map is part of the dataset's canonical form and therefore of its fingerprint. Ground truth never depends on the split: expected answers are `revision.replay` over the **whole concatenated stream per context** (`revision.py:626–646`), so the custodian computes them without knowing or caring where the boundaries fall. This is what makes the oracle independent of every persistence mechanism under test.
- **Paired worlds** are kept: `closed_world` never touches the rng (`revision.py:1170–1173`), so the open and closed streams of a seed are byte-identical in events. The W-class (world-mode change, §4.5) breaks that pairing and is therefore emitted as a **third, separately fingerprinted set**, never mixed into the paired sets.
- **Taught/untaught twins**: for every retention and transfer probe, the generator emits a twin stream where the teaching episode's FACTs are replaced by the same number of unrelated FACTs over the same drawn tokens, consuming the rng identically; the probe then expects GAP. Twins are fingerprinted with the primary and run on every path.
- **Workload knobs**, all emitted by `StreamDifficulty.canonical()` only when non-default so the pinned PR 248 fingerprints `e8d18e66…`/`ccc1f5c8…` are untouched (`revision.py:208–225`; pinned in `scripts/tests/test_cas_rpu_revision.py:574–599`): `repeat_ratio` (fraction of ASKs that re-ask a pair already asked in the same context with no intervening mutation on any of its routes, so a valid record exists), `update_rate` (fraction of non-ASK events that are RETRACT or NEGATION), `hops` (dependency depth), `episodes` (state size). The declared speed workload fixes `repeat_ratio = 0.5`; other values are the secondary workloads of §6.6.
- **Balance ceiling** (E-RS-007, `revision.py:144, 877–898`): kept at 60%, judged per class over all probes of the 20-seed set, in both worlds. Cross-session re-asks of a held conclusion are mostly YES; the balancing probes (sound-half YES, reverse-ask GAP) of `_draw_item` remain the mechanism and every new class carries one.
- **New generator entry point** `generate_session_set(seeds, difficulty, sessions=5, ...)` returning a `SessionSet` whose canonical form includes contexts, episodes, split map and twins; it must not change the output of `generate_revision_set` (pinned). Its `fingerprint()` uses the same SHA-256-over-canonical-JSON method (`revision.py:837–841`).

### 3.4 Feasibility estimate (measured 2026-10-06, this container; extrapolated to the target)

Measured on the development machine (Intel Xeon @ 2.80 GHz, 4 vCPU, 16 GB, ext4 on a virtual disk, Python 3.11.15), read-only probes with no persistence code in existence yet:

| measurement | value |
|---|---|
| `revision_experiment.py --quiet --n 8` (18 solvers, both worlds) | 0.24 s |
| `revision_experiment.py --quiet --n 40` | 0.79 s |
| import `organism` + `revision` + `controls` | 67 ms |
| fresh process: interpreter + imports + `Organism()` | 74 ms mean (64 ms min); bare interpreter 18 ms |
| generate n = 40 (one world) | 17 ms; 522 events; 89 probes; 13.1 events/item |
| organism, one fresh instance per item (n = 40) | 0.86 ms/item mean, 2.0 ms max; 65 µs/event; 265 µs/ASK mean, 488 µs p95 |
| `ctl_recompute` per item | 0.043 ms; oracle `replay` 0.040 ms |
| one organism over 522 concatenated events (unscored growth probe) | 0.09 s total; asks 291 µs → 774 µs as `len(ws.props)` grew 33 → 473; work 33 → 452 |
| peak RSS, whole n = 40 run in-process | 18.9 MB |

*Assumptions for the extrapolation (A1–A5, each to be replaced by a measurement in the pre-freeze dry run):*
A1 fsync on the target storage costs 2–10 ms per call (not measured here; the dominant unknown). A2 the memory layer adds at most 2× the in-memory compute per event excluding fsync. A3 a seed stream is ≈ 500 events, 100 per session, ≈ 90 probes per world. A4 a session's restore (snapshot read + verify + tail replay + digest + index rebuild) is ≤ 0.1 s at these sizes. A5 the organism's per-ask cost grows linearly with live propositions at ≈ 1.6 µs per proposition (from the growth probe), so at ≈ 2 500 propositions a P1 ask costs ≈ 4 ms.

*Per session* ≈ 0.08 s start + 0.1 s restore + 100 events × (0.3 ms compute + 5 ms fsync) + 0.02 s snapshot ≈ **0.75 s** (range 0.4–2.2 s across A1).

| component | launches | serialized time (A1 mid) |
|---|---|---|
| main suite: 100 sessions × 4 paths × 2 worlds | 800 | ≈ 10 min |
| untaught twins, same shape | 800 | ≈ 10 min |
| fault schedule (§4.9): 80 injections per path-world, each ≈ 3 sessions | ≈ 1 920 | ≈ 24 min |
| speed runs: 7 reps × 40 units × 4 paths × 5 sessions | 5 600 | ≈ 70 min (must be serialized; correctness runs may use 4 cores) |
| W-class third set and secondary workloads (§6.6), correctness + 1 timing rep | ≈ 1 600 | ≈ 20 min |
| **total** | ≈ 10 700 | **≈ 2.5 h serialized; ≈ 1.5–3 h wall with correctness runs parallel; ≈ 6 h if fsync is 20 ms** |

Memory is not a constraint (≈ 20–30 MB per process). Disk: ≤ 1 MB journal + snapshots per seed-world-path; ≤ 1 GB total including repetitions.

**Runtime feasibility is not confirmed by this estimate.** Before freezing, a dry run on development seeds only (never held-out) on the target AWS instance replaces A1–A5 with measurements and its cost is ledgered (§10).

### 3.5 What is lost if the suite is reduced

- **Fewer seeds.** Each variant has 20 instances per world. With 0 failures in *n*, the one-sided 95% Clopper–Pearson upper bound on the failure rate is 1 − 0.05^(1/n): 13.9% at n = 20, 25.9% at n = 10, 7.2% at n = 40. Halving the seeds roughly doubles the undetectable failure rate per variant. Fewer seeds also means fewer independent token draws, so the K-class name-collision coverage shrinks.
- **Fewer sessions.** Five sessions give four boundaries, enough for "teach / restart / retract / restart / re-assert / restart" and for "fault → recover → continue learning → restart again" (directive line 79). Three sessions give two boundaries: X-revive-across-restarts loses its third boundary and the continue-then-restart-again check cannot follow a fault at boundary 2 for the same seed.
- **Fewer repetitions.** Reducing R from 7 widens the bootstrap interval; reduce R before seeds if runtime forces a choice, and say so in the report before execution (directive line 75).

---

## 4. Coverage checklist

Each row names the directive requirement, the concrete stream pattern, the class (existing R/H/C/N where possible; new classes X, D, K, W, A, G, T, F only where the existing ones cannot express the requirement), which session the probe falls in, and whether the current contract already defines the expected answer. "Oracle" means `revision.replay` over the concatenated stream per context, unmodified; "contract v1" means the memory contract (roadmap step 2) must define the event or binding before the class can be frozen.

### 4.1 Unseen facts and queries; multi-step derived answers; delayed reuse
| requirement | pattern | class | sessions | expected from |
|---|---|---|---|---|
| unseen facts and queries | every episode's tokens are fresh per context; every ask in session k ≥ 2 that was not asked in sessions < k is "unseen" for the record index (must miss) | all | 2–5 | oracle |
| multi-step derived answers | backbone chain `hops ≥ 2` (E-RS-001) asked end to end; R-deep holds intermediates too | existing R/N | any | oracle |
| delayed reuse after unrelated activity | **X-delay**: teach chain in session 1; sessions 2–3 contain only unrelated episodes; probe `ASK(c0,ch)` in session 4 → YES; untaught twin → GAP | **X** (new) | 1 → 4 | oracle |

### 4.2 Corrections and retractions
| requirement | pattern | class | sessions | expected from |
|---|---|---|---|---|
| reversible corrections | **X-revive**: hold YES (s1), RETRACT L (s2) → GAP, FACT L (s3) → YES, probe again s4 → YES; also R-revive within a session | X / R-revive | 1–4 | oracle |
| transitive retractions | **X-deep**: hold `(c0,c_{i+1})` and `(c0,ch)` in s1; RETRACT L in s2 → both GAP, withdrawn column required on both; re-probe s3 | X / R-deep | 1–3 | oracle (§5 holding state, `revision.py:467–512`) |
| correction = retract + replace | **X-correct**: RETRACT L, FACT bypass legs (as C-bypassed's `with_bypass`) in s2 → YES via new route; dependents re-derived; s3 re-probe | X | 2–3 | oracle |
| old answers never escape through the faster path | every X probe after a mutation is also a record-first stale check: a P2/P3 hit on a record whose dependencies changed is failure category F5 (§5.2) | X, C | 2–5 | oracle + hit log |

### 4.3 Duplicates and conflicts
| requirement | pattern | class | sessions | expected from |
|---|---|---|---|---|
| duplicate events (stream level) | **D-restate**: the same FACT given twice as two events; later RETRACT once → GAP (`pos` is a set, `revision.py:426–429, 455–459`); a second RETRACT → REFUSED | **D** (new) | across a boundary | oracle |
| duplicate delivery (journal level) | **D-redeliver**: the harness re-delivers an acknowledged event with the same event ID after restart; the state must be unchanged and the answer identical; counted under exactly-once (§5.1) | F (fault schedule) | boundary | reference on acknowledged prefix |
| conflicting evidence, preserved with provenance | C-blocked, C-stale, and **C-cross**: hold YES s1, NEGATION L s2 → INADMISSIBLE with `contested = {L}` (rule 3, `revision.py:552–557`), restart, re-probe s3 → INADMISSIBLE; then RETRACT L (a contested given, ACCEPTED, contract §2) → GAP | C | 1–3 | oracle |
| conflict policy is not last-write-wins | C-cross's record after restart must still carry both polarities' evidence IDs in its support trace (§9.1 trace field) | C | 3 | trace inspection, deterministic |

### 4.4 Worlds, routes and absence
| requirement | pattern | class | sessions | expected from |
|---|---|---|---|---|
| open and closed world modes | every paired set runs in both worlds; closed differs only by UNKNOWN → NO (`revision.py:927–930`) | all | all | oracle |
| clean route | N-control, H-control, YES probes | existing | any | oracle |
| disputed route incl. INADMISSIBLE, direct and on-route | C-blocked (rule 3), C-stale, G-class step 4 (rule 1, denied conclusion with a sound chain) | C, G | any | oracle rules 1 and 3 |
| explicit denial does not automatically justify NO | G-class: NO under rule 4 only while no route exists; becomes INADMISSIBLE when a route is given | G | 2–4 | oracle |
| additions invalidating NO (closed) or UNKNOWN (open) | **N-late**: `ASK(c0,ch)` → GAP in s1 (record stored); FACT L in s2; `ASK` → YES in s2 and after restart in s3; record-first must show the absence-based record invalidated, never hit | N (extended) | 1–3 | oracle |

### 4.5 Changing rules, assumptions, contexts — require contract v1 first
| requirement | pattern | class | needs | expected from |
|---|---|---|---|---|
| changing rules / world-mode change as a dependency | **W-flip**: new event `WORLD(closed→open)` mid-stream; a NO held under closure must answer UNKNOWN with lacunae afterwards, and a record derived under closed must not answer after the flip. Today `closed_world` is a constructor flag (`organism.py:450`, `workspace.py:172`), so this needs an event kind and oracle support (`ledger.ask(..., closed_world)` already takes the mode per ask, `revision.py:539`). Emitted as a third set (§3.3) | **W** (new) | contract v1: WORLD event; rule/semantics version as a record dependency | oracle with per-ask mode |
| assumptions with explicit scope | **A-scope**: `ASSUME(L)` on branch *B*; `ASK` bound to *B* → YES; `ASK` bound to main → GAP; both survive restart; a record derived under *B* never answers in main. `Workspace.assume` exists and ASSUMPTION is ASSERTIVE (`workspace.py:256, 61`) but no event kind carries it (`events.py:33–38`) and the directive requires explicit scope before multi-session reuse (line 30) | **A** (new) | contract v1: ASSUME event with branch scope; oracle gets a branch overlay | oracle per branch |
| identically named entities in different contexts | **K-collide**: context *A* teaches `AA→BB→CC`; context *B* reuses the tokens `AA, BB, CC` with no chain; `ASK(AA,CC)` bound to *B* → GAP, bound to *A* → YES, before and after restart. `Event` has no context field today (`events.py:77–83`) and workspace keys are `s|rel|o` (`events.py:71`), so this needs identity binding (directive line 23); the implementation may use one engine per context or namespaced keys — the test checks behavior only | **K** (new) | contract v1: context identifier on events, records, snapshots | oracle run per context |

If contract v1 is not frozen with these bindings before the evaluation freeze, W, A and K are excluded and the report lists them as lost coverage with this paragraph.

### 4.6 Lessons, transfer and the taught/untaught control
| requirement | pattern | class | sessions | expected from |
|---|---|---|---|---|
| the same lesson through new instances or compositions | **T-compose**: segment `b→c→d` taught in s1; in s3 FACT `a→b` and `d→e` given, then `ASK(a,e)` → YES (never asked before: index miss required); untaught twin → GAP | **T** (new) | 1 → 3 | oracle |
| exact-answer lookup, for contrast | **T-exact**: `ASK(b,d)` in s1 (held) and again in s3 → YES; record-first expected to *hit* | T | 1 → 3 | oracle + hit log |
| taught vs untaught controls | twins for every X and T probe (§3.3) | X, T | as above | oracle |

### 4.7 Uncommitted guesses
| requirement | pattern | class | sessions | expected from |
|---|---|---|---|---|
| guesses on uncommitted branches; promotion only by an accepted event | H-bridge, H-refute, H-confirm (within session) and the **G-class probe of §8** (across sessions) | H, **G** (new) | 1–4 | oracle; §8 table frozen here |

### 4.8 Hypothesis firewall edge the oracle cannot score
E-RS-010 (`revision.py:704–722`) still applies: no HYPOTHESIS on a pair held or uncertain from an earlier YES. Cross-session variants must honor it over the concatenated stream, not per episode.

### 4.9 Recovery failure points (class F — a schedule, not a stream pattern)
Each injection is applied to one seed at one declared boundary, on every path, in both worlds; the 16 types rotate so each gets ≥ 5 injections per path-world (80 injections = 20 seeds × 4 boundaries). After every injection: a **recovery session** restores and is asked every probe pair that appeared in the acknowledged prefix (recovery probes, unscored for balance, scored for agreement), its accepted-state digest and support traces are compared with the custodian reference computed on **exactly the acknowledged prefix** (the set of event IDs for which the harness holds an acknowledgment), then the stream **continues** (the unacknowledged event is retried with its original ID, then the segment proceeds) and the **next boundary restarts again** (directive line 79).

| # | fault (directive lines 61–63) | mechanism | pass condition |
|---|---|---|---|
| F1/F2 | SIGKILL immediately before / after a commit boundary | harness kills on the process's phase marker | acknowledged prefix recovered exactly; unacknowledged event absent or complete, never partial |
| F3 | torn final journal frame | post-mortem truncation of the journal at *k* bytes into the last frame (deterministic) | torn tail detected and handled under the ack contract; no answer served from it |
| F4 | kill during snapshot write | marker inside snapshot write | previous verified checkpoint + journal recover; temp file ignored |
| F5/F6 | kill before / after manifest publication | markers around the atomic publish | either old or new checkpoint is used, never a mix |
| F7 | kill during replay | marker inside tail replay | restart recovers; replay is idempotent |
| F8 | same event delivered twice | harness re-sends an acked event ID | applied once (D-redeliver) |
| F9 | recovery interrupted and restarted | kill during restore, then restore again | second restore succeeds; no double application |
| F10 | out-of-order delivery | harness swaps two events' delivery order with correct sequence numbers | rejected or serialized explicitly as the contract declares; final state equals in-order |
| F11 | lost acknowledgment retry | harness drops the ack, retries with the same ID | exactly once |
| F12 | truncated log (older region) | truncate inside committed history | corruption quarantined and reported; serving stops; boundary lost is named — not skipped |
| F13 | corrupt snapshot bytes | flip bytes in the newest checkpoint | hash fails; previous checkpoint + journal used; if none, serving stops |
| F14 | missing index / atlas | delete the P2 index or P3 atlas files | rebuilt from accepted state without changing beliefs; rebuild work reported |
| F15 | incompatible schema version | bump the schema field in a copy | refused with a precise boundary; untouched copy preserved |
| F16 | full storage budget | quota or `RLIMIT_FSIZE` on the store | the limit is reported; no knowledge silently dropped; acknowledged prefix intact |

"Within the declared failure model" means exactly these injections on the declared filesystem; power loss, disk failure and host failure are not claimed (directive line 50).

### 4.10 Variant catalog to be frozen (names only; layouts in the generator)
Existing 16 (`revision.py:147–152`): R-simple, R-stale, R-deep, R-control, R-revive, H-bridge, H-refute, H-control, H-confirm, C-blocked, C-stale, C-bypassed, C-unrelated, N-gap, N-control, N-actionable.
New: X-delay, X-revive, X-deep, X-correct, X-hold (plain teach s_k / probe s_{k+1}); D-restate; C-cross; N-late; T-compose, T-exact; G-probe (§8); and, conditional on contract v1: W-flip, A-scope, K-collide. Each new variant carries one balancing probe and a diagnostic/control role, is admitted by `_admit` (`revision.py:1124–1149`: E-RS-005 in both worlds, E-RS-010, E-RS-006), and is redrawn on the `_REDRAW` codes (`revision.py:1121`).

---

## 5. Pass criteria

### 5.1 Zero-tolerance rules (directive line 81), with denominators
| rule | counted over (denominator) | measured how |
|---|---|---|
| zero unsupported or stale fast-path answers | every record-first **hit** (P2, P3), per world | a hit is stale if the oracle's answer at that position differs from the record, or if any dependency the record cites has a version other than the one validated; unsupported if the trace cites evidence not in the accepted log at that version |
| zero cross-context answers | every ASK in a context with a colliding name (K-class), all paths | answer must equal the oracle for the bound context |
| zero guessed facts promoted without acceptance | every G- and H-class probe, all paths | verdict equals oracle; a HYPOTHESIS cited as supporting evidence in a trace is a failure even when the verdict is right |
| exact agreement with independently computed expected answers on every deterministic case | every probe, every world, every path: verdict; contested set equality; lacuna bounds `required ⊆ reported ⊆ admissible`; withdrawn bounds (`scoring.py:12–15, 165–176`) | `score_item` unchanged (`scoring.py:179–258`); E-SC-001 on a skipped or invented probe is itself a failure, not an exclusion |
| every acknowledged update recovers within the declared failure model | every fault injection (§4.9) | recovered digest and recovery-probe answers equal the reference on the acknowledged prefix |
| every replayed update applies exactly once | every injection that redelivers or retries (F8, F9, F11) plus D-redeliver | accepted logical update count in recovered state equals acknowledged count; no answer differs from the reference |
| zero heartbeat faults on P1–P3 | every event | `Organism.faults` (`organism.py:703`) |

### 5.1a Which survival is claimed (owner decision 2026-10-06, items 1 and 3)

Two different tests, reported separately and never conflated: **(a)** the accepted state survives a clean process exit and a restart on the same machine; **(b)** it survives termination and replacement of the machine. The main suite's fresh-process sessions demonstrate (a). A claim of (b) requires the existing authorized storage arrangement to be identified, its survival verified by an actual replacement, and that run reported on its own. Every result sentence names (a) or (b).

Retention limits are set before the first run as conservative engineering defaults (bytes, events, branches; initial numbers in the memory contract), to be revised from measurements. Reaching a limit stops the run safely and is reported as a limit; it never silently discards accepted knowledge, and a run that hit a limit is reported as "stopped at limit", not as a pass.

### 5.2 Failure categories (the report counts each separately; a probe may fall into several)
F-A wrong verdict · F-B wrong contested set · F-C lacuna bound breach · F-D withdrawn bound breach · F-E stale fast-path answer · F-F unsupported fast-path answer · F-G cross-context answer · F-H guess cited or promoted without acceptance · F-I acknowledged update lost · F-J duplicate application · F-K restore validation false pass (digest matched reference but behavior differed, or served before validation) · F-L corruption skipped and served · F-M heartbeat fault · F-N harness or scoring error (E-SC-001/002, generator fault, timeout) · F-O refused/accepted disagreement on a non-ASK event (`Response.accepted` vs oracle `refused`, contract §6).

### 5.3 Confidence intervals for sampled accuracy
For every rate cell: Wilson score 95% interval with the denominator printed beside it (`Cell` keeps hits and total so 0/0 is unscored, never 100%: `scoring.py:265–284`). For a cell with zero failures, also print the one-sided 95% Clopper–Pearson upper bound 1 − 0.05^(1/n) on the failure rate, so "100%" is always read with its resolution. Accuracy intervals describe sampling resolution; they never relax a zero-tolerance rule.

### 5.4 The single-counterexample rule
One failure in any category of §5.1 **blocks the affected claim** (H-RET, H-TRX, H-SPEED-reuse or H-SPEED-rpa, as mapped in §9.3) and, for F-E/F-F/F-G/F-H, **disables the affected fast path** for the remainder of the run (directive line 136). The failing input, trace and store are preserved. The fix is made on development data only; a new code version is frozen (new commit hash, new manifest, §7.3); the custodian issues a **fresh held-out set** (new seeds) and the evaluation is rerun in full. The failed run's report is kept and linked; no example is ever removed from it (directive line 82). Average timing never offsets a correctness failure.

---

## 6. Measurement

### 6.1 End-to-end elapsed
`T_total(seed, world, path)` = wall clock from the harness launching session 1's process to the exit of session 5's process (including every restart the split map or fault schedule causes), measured by the harness with `time.perf_counter_ns`. It includes: deserializing the frozen events into `Event` objects (this family arrives already encoded as triples, `docs/working/cas_rpu_revision_streams_2026_10_06.md` §3; an optional English round trip through `encoder.encode(render(e))` is a separate diagnostic and is kept out of the memory claim, directive line 14), identity binding, updates, dependency checks, invalidation, queries, heartbeat audits, journal writes including fsync, snapshot write/verify/publish, process exit, interpreter start, reload, tail replay, index/atlas rebuild and pre-answer restore validation. Nothing is excluded by phase; phases are *also* timed individually in the per-session metrics file so the composition of the total is visible.

### 6.2 Latency distributions
Per path and world, separately for **queries** (ASK, from event receipt to answer with trace) and **updates** (non-ASK, from receipt to acknowledgment, fsync included): p50, p90, p99, max, and the count. Reported as tables and as the raw per-event arrays in the JSON artifact.

### 6.3 Memory, disk, bytes, reload, rebuild
Peak RSS per session process from `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` (per child, harness-side) and steady RSS as the median of `/proc/<pid>/status VmRSS` sampled every 50 ms over the second half of the session. On-disk sizes after each session: journal, snapshots (all retained), index, atlas (`os.stat`, summed). Cumulative bytes written: application-level bytes appended plus `/proc/<pid>/io write_bytes` at exit. Reload time: the restore phase (§3.2 step 2) split into open/verify, tail replay, rebuild, validate. Rebuild work: §6.4 units and time for F14 and for every session-start rebuild.

### 6.4 Common work units (one definition, every path)
The existing counters are **different currencies and remain diagnostics only**: a control counts adjacency entries expanded plus pairs filtered (`controls.py:25–30, 143–156`) and credits a memo hit with `work = 1` (`controls.py:343–345`); the organism counts `Workspace.ask` calls plus `len(ws.props)` at every ask, added unconditionally in `Organism._reason` (`organism.py:53, 633`; directive line 48). Neither is comparable across rows (PR 248 §5.4), and the organism's count overstates work a fast path would skip.

Proposed common unit, instrumented through one `WorkMeter` object injected into every path and incremented only at these points:
- `edges_examined` — +1 each time the status or existence of one positive-record pair (`s|leads_to|o` or `co_occurs`) is read while deciding a verdict, validating a record's support, or walking for lacunae. A BFS adjacency expansion, a `Workspace.ask` on a link, a record dependency check and an atlas-located record's support check each count their reads here.
- `rule_applications` — +1 per evaluation of a verdict rule 1–6 (`revision.py:546–569`; the runtime's equivalent in `run_in`), per derivation attempt, per cascade step on a mutation, and per record invalidation decision.
- `records_touched` — +1 per record read or written in the index or atlas (zero on P0 and P1 by construction).
Recorded per event; reported per path as totals and per-ask means for first asks and repeat asks (`_repeat_flags`, `revision_experiment.py:75–83`). The meter definition is hashed with the plan; a path that cannot be instrumented at these points reports "not instrumented" for that counter rather than a different count.

### 6.5 Warm and cold starts
**Cold**: the first session process after a checkpoint is published, started after `sync` and, where the environment permits, `echo 3 > /proc/sys/vm/drop_caches`; if not permitted, labelled "process-cold, cache-warm" in the report. **Warm**: a second consecutive process start with no intervening writes. Both reported for sessions 2–5 on every path.

### 6.6 Workloads
Declared speed workload W-rep (`repeat_ratio = 0.5`, defaults otherwise). Secondary, reported even where they regress (directive line 92): `repeat_ratio ∈ {0.0, 0.25, 0.75}`; `update_rate` × 2; `hops ∈ {2, 4}`; `episodes` × 2 (state size). Correctness is zero-tolerance on all of them; the speed claim is made on W-rep only.

### 6.7 Controls on the measurement
Identical inputs (fingerprints), seeds, split maps, machine (one instance; its type, AMI, kernel, CPU model and storage class in the manifest), storage path and filesystem, Python and package versions (`pip freeze` hash), measurement boundaries and harness commit. Paths run interleaved in a randomized order per repetition block; a run whose machine or software changed mid-run is void and rerun. CPU frequency scaling and other tenants are noted as uncontrolled.

---

## 7. Independence and custody

### 7.1 Development versus held-out
- **Development set**: seeds published in the repository (the PR 248 family seed 20261006 and any others the implementers choose), used for building, debugging and the dry run. Results on it are preparation, never evidence.
- **Held-out set**: 20 seeds drawn by the custodian from `os.urandom`, plus the custodian's own copy of the expected outcomes. Never seen by implementers before the code freeze. After a failure and fix, a *new* held-out set is drawn (§5.4).

### 7.2 The custodian (owner decision 2026-10-06, directive amendment log item 4)

The custodian need not be a human. A separately controlled evaluation agent or role holds the held-out seeds, the expected answers and their hashes. The requirement is that the builder and the learner cannot inspect or select against the final answers while the implementation is being improved: custody is a different session or process with its own transcript, it receives the frozen implementation hash before revealing anything, and it reveals seeds only after that hash is committed. This is **internal separation of responsibilities**, and the report describes it as exactly that; it is never described as an independent outside audit. The absence of a named human custodian does not stop code preparation.

### 7.3 What is hashed (the manifest)
| artifact | hash method | produced by |
|---|---|---|
| generator and oracle code: `scripts/cas_rpu/{events,revision,controls,scoring}.py` plus the new session-set module | git blob SHA of each file at the frozen commit | implementers |
| datasets: open, closed, W-set and twins for every seed | `StreamSet`/`SessionSet.fingerprint()` (`revision.py:837–841`); development fingerprints published, held-out fingerprints published by the custodian after reveal | both |
| expected outcomes per seed and world: `expectations`, `withdrawn`, `refused` (`revision.py:286–290`) in canonical JSON, plus the recovery-probe references per fault point | SHA-256 over `json.dumps(..., sort_keys=True, separators=(",", ":"))` | custodian |
| split maps and fault schedule assignment | included in the dataset canonical form | generator |
| seeds | development listed; held-out as a sealed commitment, then revealed | custodian |
| code versions | implementation commit SHA; memory contract version; schema version; engine version; harness commit SHA; `pip freeze` hash | implementers |
| pass criteria | SHA-256 of §5 of this document at freeze; this document's own commit SHA | both |
| work-meter definition and bootstrap script | file blob SHAs | implementers |
| environment | instance type, AMI id, kernel, CPU model, storage class and filesystem, Python version | whoever runs |
| **model and settings** | one line per operator who authored code or ran the evaluation: `model: unknown until verified`, `reasoning/intelligence setting: unknown until verified`, replaced only by that operator's own self-report before the run (directive line 116). The system under test calls no model (`scripts/tests/test_cas_rpu_sever.py`); this field is about the authors, and the report says so | each operator |

A scored run whose manifest hash does not match the committed manifest is void.

---

## 8. The guess probe (class G), frozen before any ablation runs

### 8.1 Purpose
PR 248's unmarked-guess ablation `abl_no_sweep` changed no scored cell (`docs/working/cas_rpu_revision_streams_2026_10_06.md` §5.3). The directive requires a probe where **admitting the guess as a fact would change a later answer**, with an unsupported tempting guess, a supported competing fact and a subsequent correction, and expected outcomes frozen before the run (line 46). Two different "guess" mechanisms are probed with one pattern: (i) a told HYPOTHESIS held as an uncommitted possibility in the memory layer (RPA entry or record), and (ii) `^8`'s own route guesses with the stage mark removed (`abl_no_sweep`).

### 8.2 Pattern (hops = 3; tokens drawn per context; L = (b, c) is the missing link)
Session k: `FACT(a,b)`, `FACT(c,d)`, `HYPOTHESIS(b,c)` [the tempting unsupported guess: with it, a→d would be YES], shadow `co_occurs(b,c)` when `shadow=True`, distractors; **step 1** `ASK(a,d)`; `NEGATION(a,d)` [the supported competing fact: an explicit given denial of the very conclusion the guess would license]; **step 2** `ASK(a,d)`. — *process boundary* — Session k+1: **step 3** `ASK(a,d)`; `FACT(b,c)` [the subsequent correction: the guess promoted by an accepted event]; **step 4** `ASK(a,d)`; `RETRACT(b,c)`; **step 5** `ASK(a,d)`. — *process boundary* — Session k+2: **step 6** `ASK(a,d)`; `RETRACT(b,c)` again [duplicate retract]. Balancing probes: `ASK(c,d)` → YES and `ASK(a,b)` → YES in session k, and `ASK(c,d)` → YES in session k+2 after the duplicate RETRACT (amended 2026-10-06: with the single probe the closed world is 5/7 NO, above the 60% ceiling).

### 8.3 Expected outcomes (from the oracle, `revision.py:539–591`; frozen here)
| step | correct (oracle) — open | correct — closed | if the guess were admitted as a fact (prediction for the promotion ablation) |
|---|---|---|---|
| 1 | UNKNOWN; `lacunae_required = {b\|leads_to\|c}`, `admissible = {a\|leads_to\|d, b\|leads_to\|c}` | NO (rule 5) | YES (route a→b→c→d) |
| NEGATION(a,d) | withdrawn: nothing required (pair untracked) | same | — |
| 2 | NO (rule 4: denied, no route) | NO | INADMISSIBLE, contested {a\|leads_to\|d} (rule 1) |
| 3 (after restart) | NO | NO | INADMISSIBLE |
| FACT(b,c) | `hyp.discard`; `pos.add` | same | — |
| 4 | INADMISSIBLE, contested {a\|leads_to\|d} (rule 1: sound chain, denied conclusion) | same | same |
| RETRACT(b,c) | ACCEPTED | same | — |
| 5 | NO | NO | NO if the admitted guess was consumed by the FACT; else INADMISSIBLE |
| 6 (after restart) | NO | NO | as 5 |
| RETRACT(b,c) again | REFUSED (oracle `revision.py:455–459`; organism E-ORG-002) | same | — |

Record-first requirements inside the same table: the step-2 record (NO, denial-backed, dependencies: `neg(a,d)`, absence of any route at version v) must be **dirty** after `FACT(b,c)` and never hit at step 4 (an addition invalidating NO; "an explicit denial does not automatically justify NO", directive line 30); the step-1 record (GAP) must be dirty after `NEGATION(a,d)`; the step-4 record (INADMISSIBLE) is never reused under the initial positive-only flag (§2.1). The possibility `b→c` must appear in the atlas as **uncommitted** with source and branch after session k, and must be absent as a dependency from every trace; after `FACT(b,c)` the promotion must carry a new committed version.

### 8.4 Ablations run against the G probe, with predictions written down now
- `abl_promote_possibility` (memory layer: a possibility/RPA entry or told HYPOTHESIS treated as supporting evidence by the record-first path, or filed as FACT as `abl_no_firewall` does): **predicted failures** at steps 1, 2 and 3 exactly as the fourth column; categories F-A, F-B, F-H.
- `abl_no_sweep` (`^8` route guesses unmarked, `scripts/cas_rpu/ablations.py`): **predicted verdict effect zero** on every G step, because `Workspace.derive` refuses hypothesis support (E-WS-002); possible `named`-column precision loss at step 1 only if an unmarked guess is reported outside the admissible set.

### 8.5 The sentence to use if the measured difference is zero
"On the G-class probes of the held-out set, removing the stage mark on `^8`'s route guesses changed no scored cell in either world (0 of *n* probes); on this evidence the mark is hygiene, not correctness, relative to the organism that lacks it, and the measured difference is zero." No other wording.

---

## 9. Report template

### 9.1 Per-case trace (one block per claimed behavior per seed, both worlds)
```
seed / world / path / context / variant / class
taught        : events (index, kind, triple), session, event IDs, acknowledged at <ts>
initial answer: ASK at index i, session k → verdict, lacunae, contested, state version, support trace (evidence IDs, rule IDs, dependency versions), route (hit|miss|reject|fallback: reason)
changed answer: the mutation (index, kind, triple, ACCEPTED|REFUSED code) → ASK at index j → verdict…, withdrawn keys, records invalidated (IDs, from valid → dirty|unsupported|conflicting)
saved         : checkpoint id, hash, last included event, manifest publish <ts>, bytes
process boundary: session k exit (normal | fault Fn at phase), session k+1 start <ts>, restore: checkpoint opened, tail replayed (n events), rebuilt (index|atlas), digest == reference? validated-before-first-answer? 
restored answer: ASK at index m, session k+1 → verdict…, route, state version
later correction: event (index, kind) → ASK → verdict…, withdrawn, invalidated; and after the next boundary
expected      : oracle verdicts at i, j, m, … (custodian hash)
result        : agree | FAIL (category)
```
Exact state equality (digest) is shown as the explanation; the changed and retained behavior is the result (directive line 84).

### 9.2 Aggregates, all four paths
Per world and path: the PR 248 matrix (`Matrix.render`, `scoring.py:359–377`) extended with the new classes; per-variant verdict table; balance per class; hit/miss/reject/fallback counts with reasons (P2, P3); exactly-once and recovery tables per fault type; §6 cost tables (elapsed, latency distributions, RSS, disk, bytes, reload, rebuild, common work units, warm/cold); workload grid of §6.6; the untaught-twin table beside the taught one. `ctl_recompute`/P0 is the first row of every table (contract §0).

### 9.3 Failures by category
A table of F-A … F-O counts with denominators per path and world, each failure linked to its §9.1 trace and preserved store. The mapping from category to blocked claim: F-A/B/C/D/E/F/I/J/K/L/M/N/O block H-RET for the failing path; F-G blocks H-RET for all paths that share the identity binding; F-H blocks H-RET and the G-probe statement; any correctness failure on P2 blocks H-SPEED-reuse, any on P3 blocks H-SPEED-rpa.

### 9.4 Costs
Total elapsed per (seed, world, path) with the bootstrap interval for each speed hypothesis; construction and replay costs of P0; the full tradeoff table (query speed vs update latency, memory, disk, recovery time) per path; machine cost in dollars from the ledger, run start and finish in PDT.

### 9.5 Decision (short)
One paragraph per recommendation — keep record-first; keep or remove the RPA optimization; retain walk-first; or revise the design — each tied to a numbered table in §9.2–9.4 and to its failure count, and each naming the **next bounded experiment** (e.g. dependency-specific invalidation if whole-context reuse is clean; a separate branch-organization demonstration if P3 equals P2 on speed; a true fresh-process test of a cross-engine lesson if H-COOP is added). Preparation (tests passing, clean builds, serialization checks) is listed under a separate heading from demonstrated behavior (vision §2). Negative findings and zeros are stated as plainly as positives.

---

## 10. Budget and authority note

This plan **proposes**; it grants nothing: no merge, push, run, purchase, credential or outreach authority (directive lines 16, 138). Execution is **AWS-only** under coordinated admission. The project ceiling is **$250**; the ledger stands at **$97.59** with the actual bill pending reconciliation (directive line 16); the nominal remainder is not a grant and **no new run budget is granted** by the directive or by this plan. The blocked operator profile must be resolved through the authorized route before any dependent run (line 16). Before this plan can be frozen, **runtime feasibility must be confirmed** by the §3.4 dry run on development seeds on the target instance, its measured fsync, per-session time and dollar cost ledgered, and A1–A5 replaced by measurements; if the measured total exceeds the admitted window, §3.5 governs what is reduced and the reduction is explained before execution (directive line 75). The drafter's extrapolation (≈ 2.5 h serialized compute on one general-purpose instance) is an estimate, not a cost quote; current instance pricing was not checked in this session.

---

## 11. Freeze procedure and amendment log

1. Contract v1 (roadmap step 2) committed; §4.5 classes included or struck accordingly.
2. Generator extension, work meter, harness and bootstrap script committed; development fingerprints and `--check` green on the development set.
3. Dry run on development seeds on the target instance; §3.4 assumptions replaced; §3.5 applied if needed; budget confirmed through the authorized route.
4. Custodian named; seed commitment published.
5. This document's §1, §4, §5, §6.4, §8 frozen; manifest (§7.3) committed with all hashes; implementation commit hash published.
6. Custodian reveals seeds and expected-outcome hash; scored run; raw artifacts delivered to the custodian; report per §9.

| date | change | reason | by |
|---|---|---|---|
| 2026-10-06 | v0.1 draft | directive §4–5; vision §3 gate | Claude (drafter) |
| 2026-10-06 | §7.2 custodian may be a separately controlled agent (internal separation, not outside audit); §5.1a survival (a) vs (b) and bounded retention before first run | owner decisions, directive amendment log items 1, 3, 4 | Claude |
| 2026-10-06 | **Generator landed** (`scripts/cas_rpu/sessions.py`, `generate_session_set`). Measured shape per seed per world: 27 episodes, 385 events, 82 probes (§3.3 estimated ≈30 / 450–500 / 90; the 16 reused layouts are ≈13 events each). Registered development fingerprints, seeds 0–19, five sessions, default difficulty, twins on: open `9e0d35b0026ddfe363e265c1f2d7a07741011f331708fbb1c5aae5b412d5203a`, closed `deae82a05c8af2e0768a22da1bf034372fa44a812f16bf3a37a8c4bd5822d760`. Three layouts gained balancing probes because the 60% ceiling (E-RS-007) otherwise refuses every set: **§8.2 G-probe** carries, besides `ASK(c,d)→YES` in session k, `ASK(a,b)→YES` in session k and `ASK(c,d)→YES` in session k+2 (closed-world NO share 5/9, not 5/7); **§4.3 D-restate** carries a reverse ask → GAP; **§4.2 X-correct** carries a reverse ask → GAP in session k+2. The §8.3 table is unchanged and asserted exactly in both worlds. T-compose's taught segment is the drawn chain c0..ch with fresh `a`, `e` (route h+2 hops; hops ≥ 5 would violate E-RS-006). Sessions 2–12 supported; 13 raises E-SS-002. | §3.3, §4.10 required a generator; balance ceiling arithmetic; owner decision 8 (internal details settled by audit, not by the owner) | Claude (generator by delegated agent; decisions accepted by the drafter) |
| 2026-10-06 | **Harness landed** (`scripts/cas_memory/session_harness.py`). One fresh OS process per session over `history.Stream`; per-event acknowledgment; four paths; scoring relabelled per episode; recovery probes against fresh recompute over the acknowledged prefix. §4.9 mapping onto the single-document design: F1 kill-before-write, F4 kill-before-replace, F2/F5/F6 kill-after-replace and kill-after-save, F7/F9 kill-during-restore, F8/F11 redeliver (in process and after restart), F10 swap, F3 torn-current, F13 corrupt-current, F12/F13 corrupt-both (history lost beyond retention → E-MEM-046 names the lost rows, serving stops), F15 schema-bump (E-MEM-010), F16 quota (E-MEM-050). **F14 is not applicable**: no index is persisted; the record index and the atlas are rebuilt from the accepted state in every process, and the rebuild is counted in restore time. One fault per seed per run, kinds and boundaries rotating; a planned kill is followed by a recovery session and the remaining boundaries restart normally. Two contract consequences recorded: a host retrying an event recorded before its acknowledgment was lost is acknowledged again without a new row (exactly once); `restore(acknowledged_seq=)` is how the host tells the stream what it acknowledged, and without it a torn current document falls back silently to the retained copy, which is why the harness always passes it. | §3.2, §4.9, §6 | Claude |
