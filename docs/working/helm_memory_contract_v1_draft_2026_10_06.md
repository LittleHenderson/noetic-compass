# HELM Memory Contract v1 — DRAFT

**Version:** helm-memory/1.0 (draft, unreviewed). **Extends:** `docs/working/revision_streams_contract_2026_10_06.md` §0–§12, which stays binding and unchanged; this document adds sections M0–M13 and alters no rule, verdict, bound or wording of the base contract. Where this draft and the base contract appear to disagree, the base contract governs and M13 must record the disagreement before anything is implemented.
**Serves:** `docs/HELM_VISION_AND_ROADMAP.md` ability 3 (Retains) and the ground of 6 (Organizes with RPA); roadmap step 2 ("Memory contract v1 — ability 3; preparation").
**Implements:** sections 1–3 of the 2026-10-06 lasting-memory directive (`docs/directives/2026_10_06_helm_lasting_memory_and_restart_recovery.md`): memory authority and the small versioned contract (§1), safe answer reuse (§2), recovery after interruption (§3) — **as amended by the owner's decisions of 2026-10-06** (that file, "Amendment log", items 1–8; cited below as *owner decision n*). Sections 4–8 of the directive (evaluation, cost, coordination, work tree, decision) are out of scope here except where a rule below exists so that they can later be measured; the evaluation plan draft is `docs/working/helm_eval_plan_draft_2026_10_06.md` and the cross-engine meaning draft is `docs/working/helm_interchange_and_fixtures_draft_2026_10_06.md`.
**Builds on:** the reuse audit `docs/working/helm_reuse_audit_2026_10_06.md` (landed in `11de4a7ee`). Per owner decision 2 the audit, not this contract, chooses the single writer and the save/load discipline; this contract cites those choices (M6.1, M9) and does not re-decide them.
**Authority:** none. This draft grants no merge, push, run, purchase or credential authority and asks for none. Planning needs no new approval; the $250 project ceiling stands; $97.59 is the last verified provisional commitment with actual billing pending reconciliation; the earlier $1 approvals belong to their own jobs and do not fund this; **silence is never permission** for publication, pushing, merging or spending (owner decisions 7, 8). It is preparation in the sense of vision §2 and is labelled so.
**Status of claims about code:** every statement about existing behaviour cites `file:line` in the checkout at `/home/user/noetic-compass` (branch `claude/cas-reasoning-processor-i47toc`; every `scripts/` file cited is byte-identical to PR #248's pinned head `4377a7d`, audit "Path keys") or in the RPA worktree at `.claude/worktrees/rpa-readonly` (HEAD `eb9985566bd11a89f485d627186ef0efa7177f02`, the commit the directive names). The worktree files were read at that HEAD while drafting; at the time of writing the worktree is **no longer mounted** (`git worktree list` shows only the main checkout) and the directive's path `_worktrees/codex-rpa-recorded-run` does not exist in this environment — the audit records the same path and the same commit, so the citations stand but a reader must re-mount before verifying (M12 Q3). Anything not read directly from code is marked **INFERRED**. Nothing below claims implemented durability: no persistence code exists for the organism today (audit §3), and the CAS memory substrate document is a proposal (`docs/architecture/CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.md:4`).

How to read: each rule states what it requires, **why**, and the failure it prevents, in the base contract's voice. Error codes `E-MEM-nnn` are proposed names for rules this contract introduces; they join the existing `E-EV`, `E-WS`, `E-ORG`, `E-RS`, `E-RT`, `E-BANK`, `E-ENC` families and are not yet implemented.

---

## M0. Scope, version, and the gate answer

### M0.1 What "lasting memory" is allowed to mean here

The directive's own bound: lasting memory means correct behaviour across the sessions, restarts and failure conditions actually tested. It does not mean permanent retention, neural learning or a lifetime guarantee. Every rule below is a rule about *accepted symbolic state* — the organism's workspace, standing conclusions, motivation, memory board, heartbeat and journal — and about the one faster path that may read it. M7 says what this contract does not cover.

**Claim-wording rule (owner decision 1).** Every retention claim names **which survival it demonstrated**, in one of exactly two forms, and never lets the first be read as the second:

- **(a) same-machine survival** — the state survived a clean process exit (or a killed process) and a restart on the same machine and the same filesystem;
- **(b) replacement survival** — the state survived termination of the machine and restoration on a replacement machine, through the existing authorized storage arrangement.

A folder on an AWS machine is not automatically lasting storage; it may vanish when the machine is terminated. (a) is established by process-exit and kill tests; (b) only by an actual terminate-and-replace test against the authorized storage arrangement (M9.0). Until (b) is run, every claim reads "(a)". The audit says the same of today's gap: until the durability text, fault tests, retention and idempotent re-delivery exist, "the claim must read 'survives a clean process exit and restart on a POSIX filesystem', nothing more" (audit §7).

### M0.2 Version and compatibility

- `schema_version = "helm-memory/1.0"` names the on-disk record shapes in M1–M5.
- `semantics_version = "revision-streams/2026-10-06 + helm-memory/1.0"` names the meaning of a verdict. The verdict rules are the base contract's §3 rules 1–6, unchanged.
- A reader of this version must refuse any artefact whose `schema_version` it does not list as compatible (M10.2). **Why:** silently reading a shape you do not understand is how a field is misread as zero and a belief is resurrected.
- Backward compatibility with PR #248 (`4377a7d` base, `17dbe73` head): `Organism.consume` (organism.py:470), `events.Event` (events.py:47), `Workspace` (workspace.py:165) and the base contract's oracle are unchanged by this contract. Everything new sits in a history document around events (M2, M9), an index beside the workspace (M3), a reference digest and restore check for the organism (M4), a projection for the atlas (M5) and the host process that calls `consume` (M6). A reader may verify that by diff: no rule here requires a change to `scripts/cas_rpu/{revision,controls,ablations,scoring}.py`. This work **extends the existing project**; it is never a competing build (owner decision 8).

### M0.3 Gate answer (vision §3, five parts)

1. **Ability:** 3 (Retains). Ground for 6 (RPA as a read-only index over accepted history).
2. **Observable behaviour, before/after on a named input:** on a generated revision stream (base contract §7 classes) extended across sessions — a FACT taught in session *n* changes the verdict of a later ASK from UNKNOWN/NO to YES; the accepted state is saved; the OS process is terminated; a fresh process restores and answers the same ASK YES without the FACT being re-sent; a RETRACT or CORRECTION of that FACT in session *n+1* changes every dependent answer back, both before and after a further restart. This document specifies the state, events and sequences that make that behaviour testable; it does not itself exhibit it.
3. **Control that lacks the mechanism:** fresh recompute from the accepted event history (the `ctl_recompute` replayer of base §9, `controls.py:388` per the audit, fed from the history document). For the RPA claim, record-first without RPA (an ordinary keyed index, M8.6).
4. **Pass criterion and denominator (frozen before the run, directive §4):** exact agreement with the independently computed expected verdict, lacunae and contested keys on every deterministic probe (denominator: probes); zero fast-path answers that are unsupported, stale, cross-context or guessed-as-fact (denominator: fast-path hits); every acknowledged update recovered within the declared failure model (denominator: acknowledged updates × injected faults); every replayed update applied exactly once (denominator: replayed events); and **every claim names which survival it showed, (a) or (b)** (vision roadmap step 3, as amended). Coverage (owner decision 6): **20 starting conditions, each followed through 5 fresh processes** — not 100 independent conditions. The crucial question at each process boundary is what survives: a useful correction, its supporting reasons, and any later withdrawal. Opening the program 100 times proves little.
5. **What it will not show:** permanent retention, neural learning or any lifetime guarantee; nor that record-first or RPA is necessary — a correct replayer is also correct; nor (b)-survival unless the terminate-and-replace test was actually run.

This document itself is **preparation**, and its CHANGELOG entry must say so (M12 Q11 on where that entry goes).

### M0.4 Ownership, custody and implementation boundaries (owner decisions 4, 5, 8)

- **Ownership.** Claude owns the processor portion (`scripts/cas_rpu/`, the organism, this contract's M2–M4, M6–M10). Codex coordinates the integration map and the canonical RPA entrypoint (M5). DeepSeek's participation **remains proposed** until the actual current lead is reached; nothing here implies an agreement exists, and no unrelated DeepSeek build is started.
- **Evaluation custody.** The custodian of final seeds and expected answers need not be a human. A separately controlled evaluation agent or role may hold them. What matters, and what this contract requires of the evaluation plan, is that the builder and the learner **cannot inspect or select against the final answers while improving the implementation**: the held-out set, seeds and expected answers are produced and sealed (hash published) by the custodian role before the implementation is frozen, and are opened only against the frozen commit. This is **internal separation of responsibilities**; it is never described as an independent outside audit. The absence of a named human custodian does not stop code preparation.
- **Implementation.** Already-authorized, narrowly scoped implementation proceeds within its existing boundaries once this contract is clear. Writing tests and running them are separate actions under the AWS-only requirement; pushing, opening a PR, merging and paid execution each fit the applicable authorization and none is implied by this document.

---

## M1. Identity

### M1.1 The stream identity record

One **authoritative stream** is the committed event history of exactly one organism in exactly one context on exactly one branch. Its identity record is written once at genesis, carried in the header of every history document (M4.5), and compared on every restore (M9.3) and every fast-path lookup (M8.2). The audit calls this the "R3 identity header" (audit §7).

| field | meaning | why it is here |
|---|---|---|
| `project_id` | `"noetic-compass"` | A history document copied between projects must not be mistaken for local history. |
| `organism_id` | the reasoner instance | Two organisms over the same context are two streams; their motivation, CMB and standing differ. |
| `context_id` | the knowledge context (the base contract's "item": one token universe `AA..ZZ`, §6) | **The collision rule, M1.3.** |
| `branch_id` | `"trunk"` for accepted history; any other value is an uncommitted branch (M8.5) | A guess on a branch must never be read as trunk truth. |
| `stream_id` | canonical string of `(project_id, organism_id, context_id, branch_id)`; grammar `[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}` per segment, joined by `.` (the identifier grammar of `rpa_model.py:32`) | A `stream_id` can never contain `|` or `~`, which is what makes the key format of M1.2 parseable. |
| `world_mode` | `open` or `closed` | `Workspace.closed_world` is fixed at construction (organism.py:454) and copied into every `Problem` (organism.py:606, 679). It is identity, not a per-query flag. See M6.6. |
| `constructor_args` | the `Organism(...)` keyword arguments other than `closed_world` (profile digest, `processor_kwargs`, `motivation_kwargs`, `workspace_factory` name) | Restore is `Organism(**args).run_stream(events)` (audit §7); the arguments are part of what the state is a function of. |
| `schema_version` | M0.2 | — |
| `semantics_version` | M0.2 | — |
| `engine_version` | digest over (a) the git commit of `scripts/cas_rpu/` and `scripts/ccb_r1/`, and (b) an explicit constants digest: `STRENGTH` (workspace.py:69-74), `ASSERTIVE`/`LIVE` (workspace.py:57, 61), `HypothesisBank.surface` defaults `max_hops=6, limit=8` (banks.py:177-178), `CommitGate(high=0.65, low=0.35)` (runtime.py:223-224), `max_ticks=64`, `learn_beta=0.05` (runtime.py:250-252), `TIER_LEAKAGE` (cmb.py:40-44), `LACUNA_FLOOR=0.05` (cmb.py:72), `LOW_GAIN`, `ENGAGEMENT` (organism.py:80, 87), `Motivation(relax=0.1, beta=0.05)` (organism.py:179-183), the constitution `FoundationProfile` digest | A record derived under `limit=8` is a record about "no route surfaced within 8 candidates and 6 hops" (M6.4). Base §6 forbids attributing a failure to a design constant; this contract forbids *reusing a record across a change of one*. The constants are listed explicitly because a commit hash alone cannot tell a reviewer which constant moved. |
| `genesis_digest` | digest of the identity record above at creation | The restore compares against it (M9.3 step 2); the RPA worktree's recovery requires a trusted genesis for the same reason (native_recovery.py:118, 143-145). |
| `last_committed_seq` | the `seq` of the newest ACCEPTED-or-REFUSED row at the durable boundary (M9.1) | Equals `Organism.clock - 1` (organism.py:463, 472-473) after restore; `standing` and `Want.index` store these numbers (organism.py:614, 640), so the numbering must be stream-global, never per-process. |

### M1.2 Canonical key format (extends `s|relation|o`, does not break it)

Existing, unchanged:
- `key = f"{subject}|{relation}|{obj}"` (workspace.py:91-93; events.py:68-71).
- `pid = ("~" if negated else "") + key` (workspace.py:95-98). `|` and `~` are refused inside any field (events.py:60-64), so a pid has exactly two single bars and at most one leading tilde.

Added by this contract, **outside** the workspace:

```
RecordKey  := <stream_id> "||" "belief" "||" <pid>
AnswerKey  := <stream_id> "||" "answer" "||" <world_mode> "||" <key>
```

Parsing splits on the **first** two `||`. `||` cannot occur inside a pid (fields are non-empty and bar-free), and cannot occur inside a `stream_id` (grammar above), so the split is unambiguous.

**Why outside the workspace:** inside one `Workspace` there is exactly one context by construction — the organism owns ONE workspace (organism.py:454) and the runner instantiates one organism per item (base §6). The pid is already unique there. Scoping the pid itself would change `Proposition.key`, which is the lacuna key the scorer converts (base §4, "keyed `s|leads_to|o`") and the fingerprint input of every pinned test. The scope therefore lives where more than one context can meet: on disk, in the host's index, and in the atlas.

### M1.3 The collision rule (E-MEM-001)

A record from one context never answers a query in another by name collision. Concretely:
- Every lookup is by full `RecordKey`/`AnswerKey`. There is no pid-keyed index shared across streams.
- The fast path binds `stream_id` from the **restored identity** of the organism being asked, never from the query text or a caller-supplied field (M8.1 step 2).
- A restored organism whose identity header does not match the document it was loaded from does not serve (M9.3).

**Failure prevented:** base §6 draws tokens per item from `AA..ZZ`; item *k*'s `VS|leads_to|TR` and item *j*'s are different claims with the same spelling. A shared index would let item *j* answer YES from item *k*'s route — the "zero cross-context answers" criterion the directive makes zero-tolerance. The audit notes this collision "is possible in the organism and impossible in CNCM" (audit §6). Required test: two streams, identical tokens, opposite facts, interleaved queries, zero cross hits (M8.4 row "context").

---

## M2. Events

### M2.1 The existing event is the payload, not the record

`events.Event(kind, subject, obj, relation)` is frozen, dependency-free, and has a `canonical()` form intended "for fingerprints and journals" (events.py:47-84). Its five kinds are stated as complete — "Five kinds, and no sixth hidden in a flag" (events.py:14). This contract does **not** add a sixth kind to `EventKind` (events.py:33-38). It wraps every event in a history row and adds three **row-level** types that reduce to the existing kinds or to no organism input at all (M2.3). The audit reaches the same shape: "Wrap, do not change, `Event`: a journal row `{seq, event_id, source, canonical, accepted, code}` written by the single writer" (audit R4).

### M2.2 The row

```
HistoryRow {
  seq                 dense integer from 0; equals the organism's `index` for this consume (organism.py:472)
  event_id            sha256(stream_id, seq, canonical)  — the audit's scheme (audit R4); M2.4
  type                FACT | HYPOTHESIS | NEGATION | RETRACT | ASK | CORRECTION | RULE_CHANGE | BRANCH_PROMOTION
  payload             Event.canonical() for the five kinds; structured bodies for the three (M2.3)
  polarity            "+" | "-"            (M2.5)
  source              { kind: generator|encoder|operator|host|promotion|import, ref, engine, version }
  expected_version    the `last_committed_seq` the proposer observed  (M6.2)
  commit_status       ACCEPTED | REFUSED | REJECTED_STALE | QUARANTINED  (M2.6)
  refusal_code        E-ORG-001 | E-ORG-002 | E-MEM-… | null
  outcome             projection of `Response` (organism.py:366-392): verdict, lacunae, contested,
                      withdrawn, satisfied, resolved_count, work_asks, work_scanned, route (M8.7),
                      beat_no, fault_count
}
```

Rows live inside the per-organism **history document** (M4.5, M9.1), whose header is the identity record (M1.1) and whose footer is the reference digest (M4.4). The document, not the row, is the unit of durability in v1 (audit §7, R24).

### M2.3 Event types and how each maps onto `events.Event`

| type | organism sees | mapping and rule |
|---|---|---|
| FACT | `Event(FACT)` → `ws.fact(...)` (organism.py:520-531) | Unchanged base §8. |
| HYPOTHESIS | `Event(HYPOTHESIS)` → `ws.hypothesize(..., stage="stream")` (organism.py:533-542) | Unchanged. Committed as an event, held as `Status.HYPOTHESIS`, **not assertive** (workspace.py:61). The firewall is the workspace's (`derive` refuses hypothesis support, workspace.py:287-292). |
| NEGATION | `Event(NEGATION)` → `ws.fact(..., negated=True)` (organism.py:544-552) | Unchanged. |
| RETRACT | `Event(RETRACT)` → the §8 status rule (organism.py:554-597) | Unchanged. Only the positive pid is retractable (base §2, §8); REFUSED outcomes are rows (M2.6). |
| ASK | `Event(ASK)` → `_ask` (organism.py:599-621) | Unchanged, **and ASK is an authoritative event**, not a read. It mutates: `standing` (organism.py:614), `_asked` and `_marks` (workspace.py:346, 394), motivation via `perturb`/`owe` (organism.py:638-640), the CMB at LEARN (runtime.py:573), `asks_made` (organism.py:600), `^8` route hypotheses created then swept (banks.py:243-244; runtime.py:326), and every consume beats (organism.py:490). A replay that omits ASKs restores a different organism. |
| CORRECTION | two consecutive `Event`s: `RETRACT(s,o)` then `FACT(s,o')` or `NEGATION(s,o)` | Occupies `seq` and `seq+1`, linked by `correction_id` in both payloads. **Atomic:** the host pre-checks the RETRACT by the §8 status table — a pure read on `ws.props` (organism.py:561-590) — and refuses the whole correction (`E-MEM-010`) applying nothing if the RETRACT would be REFUSED. Both rows are in the same saved document before acknowledgment (M9.1). **Why atomic:** a correction whose retract half is lost leaves the old and new claim both standing — the state the directive calls an old answer escaping. **Caveat, decision needed:** a refused CORRECTION does not call `consume`, so it does not beat, whereas a REFUSED RETRACT does (organism.py:490 runs for every consume). M12 Q6. |
| RULE_CHANGE | nothing | Payload `{field, from, to}` for any component of `engine_version` or `world_mode`. Effect: `engine_version` (or identity) changes; **whole-context invalidation** — every answer record in the stream becomes `dirty` (M3.3) and the fast path misses until records are re-derived under the new version. No `Event` is constructed; the organism's constants are code, so a RULE_CHANGE is only legal at a session boundary where the new code/flag constructs the organism (M6.6, M10.2). **Reserved in v1:** the audit records that "no counterpart exists" in the organism for rules or branches and marks the kinds not applicable until they do (audit R4); the shape is fixed here so that the first such event has a defined place to land, and no code is required for it in v1. |
| BRANCH_PROMOTION | one `Event(FACT)` or `Event(NEGATION)` per promoted given | Payload `{branch_id, branch_head_digest, promoted: [Event.canonical()...]}`. Each promoted given is consumed on trunk as an ordinary FACT/NEGATION with `source.kind = promotion` and the branch record digest as provenance. Only **givens** are promoted; branch derivations are not — dependents are re-derived on trunk, exactly as a revived given's "old consequences stay down until re-derived" (base §8). An ASSUMPTION on the branch is promoted as FACT explicitly or dropped; it never arrives on trunk as `Status.ASSUMPTION` (M6.7). A promoted pair that is CONTRADICTED on trunk joins the dispute silently (`Workspace.add` returns the existing record, workspace.py:208-212); the per-item `outcome.note` reports that (organism.py:527-528) and the promotion is not thereby "accepted as fact". **Reserved in v1** on the same ground as RULE_CHANGE. |

Everything the organism consumes is still one of the five kinds. The base contract's grammar restriction (base §1, E-RS-009) applies to promoted events too.

### M2.4 Unique event ID and ordering

- `seq` is the single total order. It is assigned by the host at the moment it calls `consume` (M6.1), never by the proposer.
- `event_id = sha256(stream_id, seq, canonical)` (audit R4). It makes duplicate delivery harmless (M9.3 step 4, M10.1): intake skips a row whose `event_id` equals an already-applied row's id and returns the stored `outcome` without consuming again (audit R31 `consume_row`); a row with a known `event_id` but a different payload is refused (`E-MEM-003`); a row whose `seq != clock` is refused as out of order (audit R31). A proposer retrying after a lost acknowledgment therefore resends the same row and gets the original outcome — exactly once.
- `Organism.clock` (organism.py:463) is `last_committed_seq + 1` after restore (M4.2 row `clock`). **Why:** `standing` maps a pid to "the index of the ASK that established it" (organism.py:460-461, 614); if the clock restarted at 0 after restore, a new ASK could claim an older pid's establishing index and the §5 withdrawn bookkeeping would mis-attribute.

### M2.5 Explicit polarity

`polarity` is a field, not an inference from `type`. In v1 the field must agree with the kind's implied polarity — FACT `+`, HYPOTHESIS `+` (`_hypothesis` never negates, organism.py:535), NEGATION `-`, RETRACT `+` (only positive pids retractable), ASK `+` — else `E-MEM-002`. **Why a redundant field now:** the directive's §6 names an unreconciled difference between explicit polarity and a negation predicate across engines (the audit notes the organism's polarity "is explicit via FACT vs NEGATION kind", R4). A field that exists and is checked gives the interchange envelope (`helm_interchange_and_fixtures_draft_2026_10_06.md`) a place to land without later reinterpreting `kind`, and makes the check "does this adapter preserve polarity" a comparison of two fields rather than a parse.

### M2.6 Commit status

The host records `ACCEPTED` or `REFUSED` (the organism's own §8 outcome, `Response.accepted/code`, organism.py:366-375), `REJECTED_STALE` (M6.2; nothing was applied and **no seq is consumed**), or `QUARANTINED` (M9.4; applied to nothing, kept for diagnosis).

**REFUSED events are rows, consume a `seq`, and are replayed.** Two reasons. First, base §6 compares the organism's ACCEPTED/REFUSED per event with the oracle's `refused` indices; dropping refused events changes the indices. Second, a REFUSED RETRACT still beats — `consume` runs `_withdraw` and `heartbeat.beat` unconditionally (organism.py:489-490) — so the CMB decays and motivation relaxes once more. A replay that skips REFUSED events restores a CMB and motivation that differ from the live organism's, and the reference digest (M4.4) would fail for no real reason.

---

## M3. Beliefs and answers

### M3.1 Belief record ↔ `workspace.Proposition`

```
BeliefRecord {
  key            RecordKey (M1.2)
  pid, subject, relation, obj, negated         = Proposition fields (workspace.py:82-86)
  status         Status                        (workspace.py:45-53)
  support        tuple[pid]                    (workspace.py:87)  — the direct supports of a derivation
  stage, cas                                   (workspace.py:88-89)
  established_by event_id                      — the row whose consume last set `status`; host index (M3.4)
  status_history [(seq, status)]               — rebuilt from the rows; compactable (M10.4)
  validity       valid | dirty | unsupported | conflicting   (M3.3)
  derived_at     { seq, engine_version, semantics_version, world_mode }
}
```

`Proposition` carries no event provenance and no version; `established_by` and `derived_at` are the host's index, rebuilt from the rows, never fields the workspace must learn. **Why not extend `Proposition`:** it is frozen, compared by identity in tests (`assertIs(second.episode.conclusion, first.episode.conclusion)`, test_cas_rpu_organism.py:83) and fingerprinted; adding fields would change every pinned fingerprint for no behavioural gain.

### M3.2 Answer record ↔ `Response` + `Episode`

```
AnswerRecord {
  key              AnswerKey (M1.2)
  verdict          YES | NO | UNKNOWN | INADMISSIBLE          (Response.verdict, organism.py:380)
  terminal         Terminal                                   (organism.py:379)
  rule             1..6, the base §3 rule that produced it    (M6.4 table; INFERRED from COMMIT notes)
  lacunae          on UNKNOWN only                            (organism.py:381)
  contested        on INADMISSIBLE only                       (organism.py:382)
  conclusion_pid   on YES: the DERIVED pid (`episode.conclusion.pid`, organism.py:614)
  support_trace    `ws.justification(conclusion_pid)` at derivation (runtime.py:591; workspace.py:451-468)
  roots            `ws.roots(conclusion_pid)` at derivation   (workspace.py:470-480)
  evidence_ids     event_ids of the givens at `roots`         (via BeliefRecord.established_by)
  rule_ids         engine_version + `rule`
  dependencies     positive: the transitive support set of conclusion_pid
                   negative (absence): see M3.3 — rules 4, 5, 6 depend on "no route within (6, 8)"
  derived_at       { seq (the ASK's seq), state_version = seq, engine_version, world_mode }
  validity         M3.3
}
```

Store enough to answer "why is this supported": the support trace and roots are already produced by the runtime at derivation (runtime.py:591) and need only be kept. Answer records are **index entries rebuilt from the rows**, not stored truth (M4.1).

### M3.3 Validity ∈ {valid, dirty, unsupported, conflicting}

Evaluated against the committed state at a pinned read version (M8.1 step 5). Most severe wins when several apply: `conflicting` > `unsupported` > `dirty` > `valid`.

| status | definition (YES records) | the existing predicate it reuses |
|---|---|---|
| **valid** | `conclusion_pid` status ∈ ASSERTIVE **and** every pid in `dict.fromkeys((pid,) + ws.roots(pid))` is ASSERTIVE **and** `~key` is neither ASSERTIVE nor CONTRADICTED **and** `derived_at.engine_version == current` **and** version check passes (phase 1: no ACCEPTED non-ASK row with `seq > derived_at.seq` in this stream; phase 2: no status change on any pid of the transitive support since `derived_at.seq`) | The structural part is exactly `Heartbeat.audit` (organism.py:333-359): "the pid and all `ws.roots(pid)` must be ASSERTIVE". The audit runs once per beat on `standing`; validity runs it on demand for one record (the reuse audit recommends the same: "`standing` plus the per-pid `Heartbeat.audit` check, never `Workspace.ask`", audit §7). |
| **dirty** | structural checks pass; a version check fails | Nothing in the workspace knows about versions; this is new. Dirty means "not re-verified since something changed", never "known wrong". A dirty record may be shown for explanation; it may not supply an answer (`E-MEM-020`). |
| **unsupported** | `conclusion_pid` is RETRACTED, or some support pid is RETRACTED or absent | `Workspace.retract` + `_cascade` set this (workspace.py:298-327); `roots` raises `E-WS-001` on an absent pid (workspace.py:472-474). |
| **conflicting** | `conclusion_pid` or any support/root is CONTRADICTED, or `~key` is ASSERTIVE or CONTRADICTED | `Workspace.add`'s assertive-vs-assertive branch marks both sides and cascades (workspace.py:217-225); `contested()` names a key held CONTRADICTED in both polarities (workspace.py:408-418). |

For NO, UNKNOWN and INADMISSIBLE records, `validity` is `dirty` after **any** ACCEPTED mutation in the stream, because each depends on an absence (M6.4), and in v1 none of them is ever servable regardless of validity (directive §2: reuse only a still-valid held positive). They are stored for explanation and for the four-path comparison, not for serving. M12 Q9 asks whether to store them at all in v1.

"Stale" in the directive's wording = dirty or worse.

### M3.4 Mapping onto `Organism.standing`

`standing: dict[pid, seq]` (organism.py:460-461) is populated on CONCLUDED YES (organism.py:614) and pruned by `_withdraw` when a pid is no longer ASSERTIVE (organism.py:685-693). It is therefore already the in-memory set of **candidate servable YES records**: the fast path's candidate set is a subset of `standing` (M8.1 step 4). What `standing` lacks and the record layer adds: the query → pid mapping (a YES on `ASK(s,t)` establishes pid `s|relation|t`), `derived_at` versions, and the support trace at derivation time. What the record layer must **not** do is diverge from `standing`: `standing ⊆ {pid : BeliefRecord.status ∈ ASSERTIVE}` is a restore-time invariant (M9.3 step 6).

Holding state (base §5: held / uncertain / dead) is the oracle's; the organism's `standing` is "within those bounds, not equal" (base §5). The record layer tracks the organism, not the oracle.

---

## M4. The accepted-state checkpoint

### M4.1 What a checkpoint is in v1, and what it is not

`Workspace.snapshot()` returns four summary values (workspace.py:482-488). It is an inspection summary, as the directive says, and this contract does not reuse the name.

Per the reuse audit (§7, owner decision 2), the v1 checkpoint is the **history document**: identity header (M1.1), ordered rows (M2.2) and a **reference digest of the rebuilt state** (M4.4). Nothing else is stored, because every other field of the organism is a deterministic function of those inputs under `consume()` replay — CMB decay and motivation relaxation included — and self re-asks recur on replay and must not be stored (audit §7, §3). Restore is `Organism(**args).run_stream(events)` followed by digest equality **before** the organism is returned (M9.3).

The table in M4.2 is therefore read as follows. **Retained** means: the restored value must equal the live value and is **covered by the reference digest**; in v1 it is produced by replay, not deserialised. **Reset** means: the live value is not part of the accepted state and the restored value may differ without changing any later behaviour. **Rebuilt** means: a disposable structure recomputed after restore validation. If replay cost or a retention limit (M10.3) later makes full replay infeasible, a **materialised snapshot** (v1.x, not v1) serialises exactly the fields marked Retained — the table is also that specification, and the amendment that admits it must prove materialised-restore equals replay-restore by digest.

The audit's proposed digest covers "sorted `props` tuples, `standing`, `motivation.g`, `clock`, counters" (audit §7). This contract **extends** that list — compatibly, by adding fields — with `_prior`, `owed`, the CMB cells, `beats` and `faults`, for the reasons given row by row. It does not remove anything the audit included.

### M4.2 Field by field: retained, safely reset, or deterministically rebuilt

**Organism (organism.py:442-466)**

| field | class | why |
|---|---|---|
| `profile` (constitution `FoundationProfile`) | configuration — digest in `engine_version`, value in `constructor_args` | It is the home motivation relaxes toward (organism.py:221-226) and the RPM Desire gate reads `g[F2]` from the derived profile (base §8). Mismatched constitution = different engagement = different self re-asks. Recording it in identity makes the mismatch a restore refusal rather than a quiet divergence. |
| `memory: CognitiveMemoryBoard` | **retained** (all 40 `Cell(charge, tier)` cmb.py:48-53, 75; counters `writes`, `recalls` cmb.py:77-78; `lacuna_floor`) — extension to the audit's digest | Only `C5` (`EXPERIENCE_CELL`, runtime.py:105) is ever written: at LEARN on a CONCLUDED YES (runtime.py:573) and decayed on every beat (organism.py:319 → cmb.py:97, leakage 0.05 per recall at EPISODIC). Read at FETCH without decay and used only in the trace note (runtime.py:348-356) — **no verdict reads it** (INFERRED from reading runtime.py; a grep test should pin that `recalled` reaches only `log`). It is rebuilt by replaying every consume *including every beat*: `charge` after N events is `charge_0 · 0.95^N` interleaved with LEARN maxima (cmb.py:88, 97), so a replay that skips any row (REFUSED ones included, M2.6) rebuilds a different board. It belongs in the digest because the directive asks for state equality to *support* the explanation, and 40 floats are cheap. Float canonicalisation: M12 Q13. |
| `ws: MeteredWorkspace` | see Workspace rows | — |
| `processor: ReasoningProcessor` | configuration (`max_ticks`, `gate`, `learn_beta`, runtime.py:250-252) + stateless banks | `HypothesisBank`, `DecompositionBank`, `InferenceBank` hold only a `CjtSpec` (banks.py:151-163, 345-354); the stage trace used by the short-circuit detector is a per-episode `BankTrace` local to `run_in` (runtime.py:314, banks.py:415-433). No bank state crosses episodes. |
| `motivation: Motivation` | `constitution`, `beta`, `relax_rate`: configuration. `g: dict[Drive, float]` (organism.py:195): **retained** (in the audit's digest). `owed: list[Want]` (organism.py:196): **retained** — extension. `perturbations` (organism.py:197): **retained** counter (reset would be behaviour-safe; nothing reads it; kept for equality). | `g` relaxes toward the constitution on every beat (organism.py:221-226, 320) and is perturbed per episode (organism.py:207-219); it decides `engaged` (organism.py:234) and so whether a closed want is re-asked (organism.py:525-526). `owed` is the list of unmet wants; `_fact` compares wants before/after and re-asks on its own (organism.py:521-526, 661-683); a lost `owed` means a FACT that closes a want in the next session does not trigger the self re-ask, which changes the CMB (the re-ask's LEARN) and the `resolved` column. Verdicts do not change (hard law, base §8), but the state does. Replay rebuilds it exactly; the digest must therefore include it or a replay divergence in self re-asks goes unnoticed. |
| `heartbeat: Heartbeat` | `beats` (organism.py:313): **retained** — extension. `reports: list[BeatReport]` (organism.py:314): **reset/compactable** (M10.4). `faults: list[str]` (organism.py:315): **retained, and non-empty faults are a serving stop** (M9.3 step 7) — extension. | `beats` counts decays applied; equality needs it. `reports` is read on the answer path by nothing; `report()` reads `reports[-1].charge` (organism.py:705-731). `faults` is the structural-failure signal ("standing conclusion with dead root", organism.py:348, 357): a faulted organism that restarts with an empty fault list would serve as if healthy — the exact thing the heartbeat exists to prevent. On replay, faults recur deterministically; the digest pins that they did. |
| `standing: dict[pid, seq]` | **retained** (in the audit's digest) | The held conclusions; `_withdraw` and the audit read it (organism.py:685-693, 333-359). Values are stream `seq`s (M2.4). Restore invariant: every key is ASSERTIVE in `ws.props` (M9.3 step 6). |
| `log: list[Response]` | **reset**; the cost ledger it feeds is **rebuilt** from `outcome` projections in the rows | `Response.episode.workspace` is a reference to the live workspace (runtime.py:178; organism.py:376-378) and episodes carry traces, candidates and decompositions — not a serialisable value. Nothing on the answer path reads `self.log`; only `report()` sums `work_asks`/`work_scanned` over it (organism.py:725-726). On replay the log is regenerated, so it is not "lost"; it is excluded from the digest because its episodes hold object references. |
| `clock` | **retained** = `last_committed_seq + 1` (in the audit's digest) | M2.4. |
| `asks_made`, `reasks_made` | **retained** (the audit's "counters") | They name problems `ask{n}`/`reask{n}` (organism.py:601-607, 673-680), and the name reaches `Goal(name=…)` and the RPM trace. No verdict depends on them (INFERRED: `Goal.name` is a label); equality of traces does. |
| `_scanned` | **reset** | Per-event scratch, zeroed at the top of every consume (organism.py:475). |

**Workspace / MeteredWorkspace (workspace.py:172-181; organism.py:102-118)**

| field | class | why |
|---|---|---|
| `closed_world` | identity (M1.1 `world_mode`); checked, not restored | The single switch between NO and UNKNOWN (workspace.py:22-27, 401; runtime.py:704-717). A history restored under the other flag is a different stream (M6.6). |
| `props: dict[pid, Proposition]` | **retained, in insertion order, including RETRACTED entries** (the audit digests sorted tuples; this contract requires the digest to be taken over the **ordered** sequence as well) | The accepted belief state. Insertion order matters: `_cascade` iterates `list(self.props.values())` (workspace.py:325), `sweep` sorts (workspace.py:336-338), `surface` builds then sorts edges (banks.py:209-216), `live`/`assertive` iterate (workspace.py:350-354). Whether any end-state depends on the iteration order is **INFERRED to be no but not demonstrated**; digesting the ordered sequence removes the question. RETRACTED entries are kept because `roots()`/`justification()` of a fallen derivation still name them and raise `E-WS-001` if absent (workspace.py:460-461, 472-474) — explanation of *why a record fell* needs them. Compaction of a subset is permitted under M10.4 rule 4 only. |
| `journal: list[str]` | **reset/compactable** (M10.4) | The workspace's own text trail (workspace.py:175). Grep: every reference in `scripts/cas_rpu/*.py` is an `.append` — there is no reader on the answer path. Behaviour does not depend on it; explanation does, and replay regenerates it. |
| `_asked: dict[key, mark]`, `_marks: int` | **retained** — extension | `_asked[key] = self._marks` at every ask (workspace.py:394); `lacunae(since=mark)` reports only keys asked at or after the FETCH mark (workspace.py:420-449; runtime.py:346, 676; organism.py:643-645). Resetting both together is **behaviour-safe for scored cells** (INFERRED: a new episode's lacunae are `since` its own new mark) but changes `ws.snapshot()["lacunae"]`, `ws.lacunae()` with default `since=0`, and the digest. Replay rebuilds them; the digest should include them so a divergence in episode marks is visible. |
| `_prior: dict[pid, Status]` | **retained** — extension, behaviour-bearing | Retracting one side of a contradiction reinstates the other to the status it had before (workspace.py:313-321), defaulting to FACT when the entry is missing (workspace.py:319). A materialised snapshot that dropped `_prior` would reinstate a formerly DERIVED counterpart as FACT, which then survives a later RETRACT of its own roots and changes the §8 refusal (`E-ORG-001` names roots of a derivation; a FACT has none). Replay rebuilds it; the digest must cover it so that any future materialised snapshot is forced to carry it. |
| `asks` (MeteredWorkspace) | **reset** to 0 | Read only as a delta within one consume (organism.py:474, 492); the cumulative total is reported from `log`, which the rows rebuild. |

**Not in the organism, but part of restore**

| item | class | why |
|---|---|---|
| host index (BeliefRecord/AnswerRecord, M3) | **rebuilt** from `props` + rows at restore, after validation (M9.3 step 5) | A disposable index; it must never be the thing that is trusted (directive §1: RPA is not the persistence engine; the same holds for the ordinary index). |
| RPA atlas (M5) | **rebuilt** after authoritative restore validation only | M5.3. |
| `^8`-stage LIVE hypotheses | none exist at a row boundary | Every `run_in` exit sweeps them (runtime.py:326; workspace.py:329-341). Their RETRACTED remains stay in `props` and are the main compaction target (M10.4 rule 4). |

### M4.3 Beat-count caveat, stated once

"Deterministically rebuilt by replaying `consume()`" is exact only if **every** row is replayed in order, REFUSED ones included, because every consume beats (organism.py:490), every beat decays `C5` (organism.py:319) and relaxes `g` (organism.py:320). A restore that applies only ACCEPTED mutations rebuilds the workspace correctly and the CMB/motivation incorrectly. The restore sequence (M9.3) therefore replays rows, not "facts" — which is exactly what `run_stream(events)` does (organism.py:515-516).

### M4.4 Hashes

- `reference_digest = sha256(canonical_json(retained fields in the order of M4.2))`, computed by the live organism at save time and recomputed by the restored organism after replay. Canonical JSON: sorted keys, compact separators, no non-finite numbers — the rule the RPA worktree's `canonical_json`/`digest` already implement (native_recovery.py:15; rpa_native_adapter.py imports the same module). The organism code cannot import from that branch (`cncm/` is not on the main branch, audit "Path keys"); one implementation of the same rule lives in `scripts/cas_rpu/organism.py` beside `save`/`load` and is checked against the worktree's by a fixture test (M12 Q2).
- `document_digest = sha256(canonical bytes of header + rows + reference_digest)` — the whole-document digest in the native pattern (native_recovery.py:129-131), stored in the document footer and in the retained-copy filename (M10.3).
- `identity_digest` = M1.1 `genesis_digest`.

### M4.5 The history document and its retained copies

```
HistoryDocument {
  header:   identity record (M1.1) incl. constructor_args, schema/semantics/engine versions,
            last_committed_seq, created_at, writer_id
  rows:     [HistoryRow …]  (M2.2), seq 0..last_committed_seq, dense
  footer:   reference_digest (M4.4), document_digest
}
```

Written by `save(path)` following `native_recovery.py:183-202` **by reference** (temp file in the destination directory → write → `flush` → `fsync(file)` → `os.replace` → `fsync(directory)` → read-back digest; audit §7). The directory fsync and read-back are the two steps the native pattern omits and the audit names as missing (audit §2.2); they are added, not replaced. The previous document is retained as `history.<seq>.json` copies (audit R27) rather than overwritten in place; M10.3 sets how many.

### M4.6 Restore-before-answer

No ASK — fast path or walk — is served by a restored organism until M9.3 has completed, including identity match, `reference_digest` equality, `Heartbeat.audit` run **at restore time** (organism.py:333-359, callable directly), `standing ⊆ ASSERTIVE`, and `faults == []`. **Why not wait for the first beat:** the beat runs *after* the handler (organism.py:489-490), so the first ASK after restore would be answered before the audit speaks — the directive's "the current post-event heartbeat is too late" names exactly this ordering, and the audit puts the validation in `load` for the same reason ("this is where 'validate before any answer' lives, not in the heartbeat", audit §7).

---

## M5. RPA entries

### M5.1 What exists

The RPA worktree (`eb99855`) defines `AtlasNode(status ∈ {OBSERVED, HYPOTHETICAL, UNKNOWN, REJECTED, VERIFIED})` (rpa_model.py:36-41), `NodeKind` (rpa_model.py:44-48), `LinkType` (rpa_model.py:51-56) and `AtlasSnapshot(current_state_id, focus_node_id, hypothesis_branch_id)` whose validation requires the current state to be a STATE node with status OBSERVED or VERIFIED and the hypothesis branch, if any, to be a HYPOTHETICAL node (rpa_model.py:385-418). The native adapter **replays first, then projects**: `native_atlas_from_journal` calls `replay_native_journal` and reads `machine.journal()` before building any node (rpa_native_adapter.py:62-66); evidence nodes carry record digests in `evidence` (rpa_native_adapter.py:186-191); its scope string says suggestions have no write authority (rpa_native_adapter.py:206). The recorded adapter labels its view `ARCHIVED_RUN_RECORD_NOT_LIVE_HELM` and `authority: INSPECTION_ONLY` (rpa_recorded_helm.py:36-50). There is **no adapter from `Organism`/`Workspace` to an `AtlasSnapshot` today** — that is the gap, and the smallest change is one read-only projection function, `organism_atlas_from_history`, placed next to `rpa_native_adapter.py` on the RPA branch and linked by commit (audit §7), built only after `load` validates. Codex coordinates where it lands (M0.4).

### M5.2 Entry shape (projection rules)

| organism fact | atlas node | status | evidence |
|---|---|---|---|
| BeliefRecord with `status` FACT or DERIVED, validity `valid` | STATE / EVIDENCE node keyed by `RecordKey` | OBSERVED (VERIFIED after a restore validation that re-checked it) | `(record_digest, established_by event_id)` |
| BeliefRecord `status` HYPOTHESIS (stage `stream`) | node on the hypothesis branch | HYPOTHETICAL | the HYPOTHESIS event_id — marked uncommitted-as-fact |
| BeliefRecord CONTRADICTED (either polarity) | both polarities' nodes, linked `references_same_idea` | OBSERVED with field `disputed=true` | both establishing event_ids — a dispute is shown, never resolved by the atlas |
| BeliefRecord RETRACTED | node kept for explanation | REJECTED | retracting event_id |
| AnswerRecord | REGION node summarising query → verdict, `validity`, `derived_at` | OBSERVED if `valid`, UNKNOWN otherwise | the ASK event_id and `support_trace` digest |
| uncommitted branch (M8.5) | separate branch subtree, `hypothesis_branch_id` pointing at its root | HYPOTHETICAL throughout | the branch's own document digest |

Every entry carries a **dependency/version summary**: `derived_at`, `engine_version`, `validity`, and the count of transitive supports — enough to *narrow* a search (M8.6), never enough to *answer*.

### M5.3 Three rules

- **An atlas entry never substitutes for evidence (E-MEM-030).** The fast path may use the atlas to find candidate `RecordKey`s; it then reads the **record** (workspace status, supports, row provenance) and runs M3.3 on it. An implementation that answers from node fields is the directive's "silently promote a possibility into a fact" with extra steps. Required test: corrupt an atlas node's fields while leaving records intact; the served answer must not change.
- **The atlas is rebuilt only after authoritative restore validation** (M9.3 step 8), mirroring replay-then-project (rpa_native_adapter.py:62-66). A stale atlas file found on disk is deleted or ignored, never trusted.
- **Branch ownership.** Every node carries `stream_id` (hence `branch_id`); `current_state_id` points only at trunk STATE nodes (rpa_model.py:413 already restricts to OBSERVED/VERIFIED); `hypothesis_branch_id` is the only way a branch is in view. Narrowing for a trunk query returns trunk keys only.

RPA is not the persistence engine; it is a disposable index bounded by M10.3 (M10.1 "rebuild a disposable index without changing accepted beliefs").

---

## M6. Update and conflict behaviour

### M6.1 One writer per authoritative stream — decided by the reuse audit

Per owner decision 2 the audit chooses, and it chose: **`Organism.consume` is the single writer** for a stream — "the only event intake" (audit R8, organism.py:470-513) — and "PR 248's `Organism` is the single implementation; add no framework" (audit §7). This contract cites that and does not re-decide it. Consequences:

- The **host** is whatever process holds the `Organism` instance and calls `save`/`load`. There is one host per stream. Every other component — generator, encoder (`repl.py`), an RPA tool, a CNCM adapter, the evaluation harness — **proposes** a row and receives the committed row back; none calls `consume` on another host's organism and none writes the stream's files. **Why:** `Organism` is a single in-memory object with no locking (audit §3); two callers of `consume` would interleave events and the `seq`/`clock` identity of M2.4 would be meaningless.
- No new journal module is proposed. The audit's R24 leaves one choice unresolved — whole-document rewrite per commit (the CNCM pattern) versus an NDJSON hash-chained append log — and this contract takes the **whole-document rewrite** as the v1 mechanism because it is reuse by reference of `native_recovery.py:183-202` with no torn-tail case to handle (audit §2.4: "not applicable per event — there is no append log"). The append log is admitted only if the whole-document write is **shown to fail** — by measurement of its O(n)-per-commit cost at the suite's scale (M10.3 defaults bound n), or by a fault it cannot survive — and that showing goes in M13 first.

### M6.2 Stale expected version: reject (proposed default)

A proposal carries `expected_version` (M2.2). If `expected_version != last_committed_seq` when the host takes it, the host records `REJECTED_STALE` with the current head and **applies nothing, calling `consume` not at all, consuming no seq**. The proposer re-reads and re-proposes knowingly. ASK proposals are the exception the directive permits: they may be **serialised explicitly** — re-bound to the current head and recorded with `serialized_from = expected_version` — because an ASK proposes no change of belief. **Why reject mutations rather than serialise them:** a RETRACT or CORRECTION proposed against an older state may be correcting something already corrected; applying it against the new head is a guess about the proposer's intent. M12 Q7.

### M6.3 Conflicts are preserved with provenance; never last-write-wins

The workspace already does the preserving: an assertive claim meeting its assertive denial marks **both** CONTRADICTED, remembers each side's prior status in `_prior`, journals `contradiction <key>` and cascades (workspace.py:217-225); a later arrival on a CONTRADICTED record is absorbed, not applied (workspace.py:208-212); only retracting one side reinstates the other (workspace.py:313-321). The **declared conflict policy** is therefore: base §3 verdict precedence for answers, base §8 retract rule for resolution, and this contract adds only that both sides' `established_by` event_ids are kept in the BeliefRecord so the dispute can be explained across sessions. The named failures this prevents are already in the base contract's control and ablation rows — `ctl_last_writer` and `abl_last_writer_add`, where "a later polarity overwrites the earlier; nothing is ever contested" (base §9, §10).

### M6.4 Full verdict precedence preserved, and "an explicit denial does not automatically justify NO" reconciled with rules 1–6

Base §3, evaluated in order, first match wins:

```
1. (s,t) in neg  and reach(s,t, clean)            → INADMISSIBLE, contested_required = {(s,t)}
2. reach(s,t, clean)                              → YES
3. reach(s,t, clean | contested)                  → INADMISSIBLE, contested_required = disputed links on simple routes
4. (s,t) in neg                                   → NO (both worlds)
5. closed world                                   → NO
6. open world                                     → UNKNOWN + lacunae
```

Where the runtime implements each (so a reader can check the mapping, not take it on trust):

| rule | runtime location | mechanism |
|---|---|---|
| 1 | runtime.py:451-464 | `^9` landed but `derive`→`add` met the assertive denial, so the conclusion is CONTRADICTED (workspace.py:217-225) → INADMISSIBLE naming the exact key |
| 2 | runtime.py:520-591 | COMPARE, RPM, Schmitt commit, ACT, LEARN → CONCLUDED YES |
| 3 | runtime.py:487-496 | Rule C: every absent constituent of the only routes is contested (`Decomposition.blocked_only_by_dispute`, banks.py:123-127) |
| 4 | runtime.py:396-402 (no candidates) and runtime.py:508-511 (all candidates failed, none merely disputed) | the given denial is consulted **after** routes and disputes |
| 5 | runtime.py:704-710 | `_prerequisite_stop`, closed world |
| 6 | runtime.py:711-717 | `_prerequisite_stop`, open world, lacunae since the FETCH mark |

**The reconciliation, precisely.** The directive's sentence "an explicit denial does not automatically justify NO" is not a new rule; it is a description of rule 4's **position**. Rule 4 fires only after rules 1–3 have failed, i.e. only when there is **no route at all** — clean or contested — from *s* to *t*. The base contract says why in its own words: "a denial that is itself disputed is not knowledge, and a denied pair whose only route runs through a disputed link is a dispute about that link" (base §3, after the rule list); the runtime pins both orderings by test (`test_a_contradictory_premise_set_is_inadmissible`, `test_a_contested_claim_asked_directly_is_a_dispute_not_a_denial`, test_cas_rpu_runtime.py:180, 320) and pins that a denial does outrank a *partial* route `^8` surfaced but `^6` could not complete (`test_a_given_denial_outranks_a_partial_route_association_surfaced`, test_cas_rpu_runtime.py:296).

What this means for **records**, which is the only new thing: a NO produced under rule 4 has two kinds of dependency — the denial `~pid` being ASSERTIVE, **and the absence of every route within the bank's bound**. The second is a dependency on the whole context: any later FACT (or BRANCH_PROMOTION) can add a route and move the verdict to rule 1 or rule 3 (INADMISSIBLE), and a later NEGATION on a link can move it from rule 2/3 territory into rule 4. A record keyed only on "`~pid` is ASSERTIVE" would therefore serve a NO that the §3 order no longer licenses. Hence, in this contract:

- Rule-4 NO records are **absence-dependent** (M3.3) and are **never served by the fast path in v1** (directive §2 keeps denial, conflict, INADMISSIBLE and unknown on the current path). `Workspace.ask` returning "NO" from an assertive denial (workspace.py:398-400) is exactly the shortcut that would violate the order, which is one of the reasons M8.3 says `Workspace.ask` alone is insufficient.
- Rule-2 YES records depend on their route's supports being ASSERTIVE and the exact pair not being denied. Both are checked structurally (M3.3 `valid`): a NEGATION of the exact pair makes the DERIVED pid CONTRADICTED (workspace.py:217-225) → `conflicting`; a NEGATION of a link cascades the conclusion to RETRACTED (workspace.py:223-224, 323-327) → `unsupported`; a RETRACT of a root cascades the same way. A YES is stable under FACT additions (a FACT adds to `pos`, never to `neg`, base §2; rules 1 and 3 need `neg`/`contested`) — so in phase 2 a YES record need not be dirtied by FACTs, but in phase 1 (whole-context invalidation) it is dirtied anyway and re-verified, which is the safe direction.

Precedence is thus preserved by **construction**: the fast path serves only when the workspace's own rules — the same rules the runtime relies on for rules 1 and 3 — show the exact pair undenied and the route undisputed. Any check that cannot be made falls back to derivation, which is the runtime's full rule order. This is a claim to be **pinned by test** on every §7 class across a restart, not a proof in this document.

### M6.5 Absence-based NO/UNKNOWN invalidated by new facts

Rules 4, 5 and 6 are absence-based. In phase 1 (whole-context invalidation, directive §2 "start with whole-context invalidation"), any ACCEPTED FACT, NEGATION, RETRACT, CORRECTION, BRANCH_PROMOTION or RULE_CHANGE marks every NO/UNKNOWN/INADMISSIBLE record in the stream `dirty`. HYPOTHESIS events also dirty UNKNOWN records: a hypothesis does not reopen a closed world (base §3 convention) but it does enter the open-world lacuna graph `G_all` (base §4) and can change the reported lacuna set. Phase 2 (dependency-specific) is admitted only after phase 1 has demonstrated correctness on the held-out run (directive §2, vision roadmap step 4).

### M6.6 Rules and world mode are dependencies

Every AnswerRecord carries `engine_version` and `world_mode` (M3.2 `derived_at`). A mismatch with the current identity is a `dirty` record (M3.3). World mode is identity (M1.1): it is bound at construction (organism.py:454) and copied into every `Problem` (organism.py:606, 679), so a change is a RULE_CHANGE applied only at a session boundary by constructing the organism from the history with the new flag; beliefs (`props`) are world-independent and survive; every answer record is dirtied (`E-MEM-011` if an in-session change is attempted). M12 Q12 asks whether v1 should allow it at all rather than requiring a new stream.

### M6.7 Assumptions get explicit scope before multi-session reuse

`Status.ASSUMPTION` counts as ASSERTIVE (workspace.py:61) and can carry derivations, but the organism never creates one — no event kind maps to `ws.assume` (workspace.py:256) and a RETRACT of one is refused (organism.py:575-580). This contract: an ASSUMPTION pid carries `scope = (context_id, branch_id)` in its BeliefRecord; it may exist only on a non-trunk branch (M8.5); a **trunk history whose rebuilt state contains any ASSUMPTION fails restore validation (`E-MEM-012`)** until branch semantics are admitted; promotion converts it to an explicit FACT event or drops it (M2.3). **Failure prevented:** an assumption taken "for the sake of a branch" (workspace.py:49) that outlives the branch into another session is a premise nobody was told, carrying derivations as if given.

---

## M7. Symbolic vs neural retention

This contract covers **symbolic state only**: the workspace's propositions and their statuses, standing conclusions, motivation levels and owed wants, the 40-cell memory board's charges, heartbeat counters and faults, the event rows, and the records and atlas built over them. All of it is reconstructible from the rows by replay (M4.3) and none of it is a learned parameter.

It does **not** cover neural retention, and nothing in it may be cited for one. A neural-retention claim needs, separately verified: model weights, optimizer state, update counters and random-number-generator state, each checkpointed and restored, **plus** learned behaviour measured before and after a fresh-process restart, with retrieval disabled as well as enabled (vision §2 "Neural growth"; directive §1 "Keep symbolic and neural retention separate"). The `cas-native/` training infrastructure has its own checkpoints and is out of scope (vision §4 row 5). The RPA worktree's recorded adapter explicitly excludes learner, Torch import and checkpoint decode (rpa_recorded_helm.py:3-6), and the CMB's `C5` charge is a scalar decayed by a constant (cmb.py:97), not a learned parameter. There is no RNG on the organism's consume path (grep of organism.py, runtime.py, workspace.py, banks.py, foundations.py, cmb.py, rpm.py, cdab.py for `random`: none; the audit records "no neural state anywhere", R10 — to be pinned by a test the way the bank-call ban is, test_cas_rpu_organism.py:498). A saved atlas, a deserialised `Organism`, or a larger record count establishes symbolic retention at most, and only after the behaviour of M0.3 is observed, and only at the survival level — (a) or (b) — actually tested.

---

## M8. The guarded positive-answer path (feature flag)

### M8.0 Scope of v1

Two independent flags, both default **off**: `record_first` and `rpa_routing` (M8.7; the audit's "two routing flags", §7). With `record_first` off, the organism is PR #248's walk-first reasoner unchanged. With it on, **only a still-valid held YES** may be served from a record; NO, UNKNOWN, INADMISSIBLE, every REFUSED path and every uncertain check fall back to the existing derivation. Whole-context invalidation first (M6.5).

The audit places the flag in `_ask`, "reusing `standing` plus the per-pid `Heartbeat.audit` check, never `Workspace.ask`" (audit §7). The index and the atlas lookup remain outside `Organism` (the organism "itself never calls a bank (a test greps its source)", base §8, test_cas_rpu_organism.py:498; the same discipline keeps index code out of organism.py) — M8.7 names the smallest touch point.

### M8.1 Required query sequence

```
serve_ask(proposal):
  1  CANONICALIZE  — build events.Event(ASK, s, o, relation) through the existing constructor
                     (events.py:117): E-EV-001/002/003 reject malformed input. English goes through
                     encoder.encode (encoder.py:327) which REJECTS anything outside its five productions
                     (E-ENC-001…008, encoder.py:50-70) rather than converting it. No synonym mapping,
                     no reordering, no default relation beyond the grammar's.
  2  BIND          — stream_id, branch_id, world_mode, semantics_version from the RESTORED IDENTITY
                     (M1.1), polarity "+" (M2.5). A caller-supplied context is compared, never used.
  3  READ VERSION  — v = last_committed_seq (M1.1). All checks below are against state at v.
  4  LOOKUP        — candidates = index.get(AnswerKey) ∩ { pid ∈ organism.standing }   (M3.4)
                     if rpa_routing: candidates = rpa.narrow(candidates)  — may only REMOVE (M8.6)
                     if none: route = "miss" → step 9
  5  VALIDATE      — for the single candidate record r:
                       a  r.commit_status == ACCEPTED and r.derived_at.seq ≤ v             (committed)
                       b  r.key.stream_id == bound stream_id                               (context)
                       c  r.established_by and every evidence_id resolve to ACCEPTED rows  (provenance)
                       d  M3.3 validity(r, at v) == valid — i.e. pid ASSERTIVE; every pid in
                          (pid,)+roots(pid) ASSERTIVE; ~key neither ASSERTIVE nor CONTRADICTED;
                          engine_version match; no ACCEPTED non-ASK row with seq > r.derived_at.seq
                          (phase 1). This is the clean-route / disputed-route check of M6.4.
                       e  heartbeat.faults == []                                           (M4.2)
                     any failure: route = "rejected:<which>" → step 9
  6  PIN           — if last_committed_seq != v after validation: either retry from step 3 (bounded,
                     say 3 attempts) or answer from the pinned read at v, stating v. Never validate at
                     v and publish against v' > v.  (E-MEM-021)  [With one host and one writer this
                     can only happen if the host interleaves proposals; the rule exists so that it
                     stays true if it ever does.]
  7  RETURN        — verdict YES, state_version = v, support_trace = r.support_trace re-read from the
                     live workspace (ws.justification(pid), workspace.py:451) so the trace is current,
                     route = "hit". Bookkeeping: the ASK is still a row (M2.3): seq assigned, outcome
                     recorded, beat run (M8.7 side effects), standing unchanged (setdefault semantics,
                     organism.py:614).
  8  (done)
  9  DERIVE        — the existing `_reason` path (organism.py:625-641) — the full runtime (M6.4 table).
                     If CONCLUDED YES, the new/refreshed AnswerRecord is written with derived_at = this
                     seq, inside the same saved document as the ASK row (M9.1).
                     route = "fallback:<reason>" or "miss".
```

**Restore validation happens before step 1 of the first ASK after a restore** (M4.6, M9.3), not at the post-event heartbeat.

### M8.2 Why the bind step uses restored identity

If `stream_id` came from the proposal, a proposer with the wrong context would get the wrong context's record (M1.3). The restored identity is the only thing the host has verified against a document digest.

### M8.3 Why `Workspace.ask` alone is insufficient

`Workspace.ask(s, rel, o)` (workspace.py:385-401) returns `"YES"` when the positive pid is ASSERTIVE, `"NO"` when the negative pid is ASSERTIVE, else the world default. Four reasons it cannot be the fast path's check:

1. **It does not check roots.** A DERIVED pid with a dead root would still read YES. The cascade makes that impossible on a healthy organism, but the audit exists precisely because the cascade can be broken (organism.py:333-359); a check that does not look at roots cannot tell a healthy record from one the audit would fault.
2. **It does not enforce contested-route semantics.** It answers NO from an assertive denial regardless of routes — the shortcut rule 4's position forbids (M6.4). And it knows nothing of rule 3: a pair with no direct record but a disputed route is UNKNOWN/NO to `ask` and INADMISSIBLE under §3.
3. **It has side effects.** Every call records `_asked[key] = _marks` (workspace.py:394), which changes what `lacunae(since=…)` reports for the current episode, and it is the metered unit of `work_asks` (organism.py:117). Using it as a check would corrupt both the lacuna column and the cost column.
4. **It has no version.** It reads whatever is in `props` now; M8.1 step 6 needs a pinned `v`.

The runtime itself never relies on `ask` for a verdict: `^6` asks per link and the no-candidate path asks once (runtime.py:396), then consults the denial and the frontiers explicitly.

### M8.4 Every cause of invalidation, the event type that triggers it, and the test that must exist

| cause | trigger (M2.3 type) | effect on a held YES record | existing test | required test (across a fresh-process restart, both worlds) |
|---|---|---|---|---|
| a root given is withdrawn | RETRACT (ACCEPTED) | cascade → `unsupported`; leaves `standing` | `test_a_retracted_support_withdraws_the_standing_conclusion_and_says_so` (organism tests:86) | R-stale/R-deep: teach, ask YES, save, restart, RETRACT, ask → UNKNOWN/NO; fast path logs `rejected:unsupported`, never `hit` |
| a route link is denied | NEGATION on a link | link CONTRADICTED → cascade → `unsupported`/`conflicting` | `test_a_held_conclusion_falls_when_its_support_becomes_disputed` (:283) | C-stale across restart; re-ask → INADMISSIBLE (rule 3) or YES via a clean second route (`test_a_clean_second_route_beats_a_disputed_one`, :260) — in the second case the fast path must still miss, because the held record's route died |
| the exact pair is denied | NEGATION on (s,t) | pid CONTRADICTED → `conflicting` (base §11 case) | `test_a_denied_derivation_is_a_dispute_on_re_ask` (:296) | same across restart; re-ask → INADMISSIBLE (rule 1) |
| a given is corrected | CORRECTION | as RETRACT + FACT, atomically | — | correct `F(a,b)`→`F(a,c)`: dependents of (a,b) fall, routes via (a,c) derive fresh; a crash between the two consumes and the save → neither in the restored state (M9.4) |
| a withdrawn given returns | FACT re-asserting a RETRACTED root (R-revive) | root revives; conclusion stays RETRACTED until re-derived (base §8) | `test_a_revived_given_lets_the_conclusion_be_re_derived` (:113) | fast path must `rejected:unsupported` even though roots are back; the next walk re-derives and refreshes the record |
| a new fact adds a route | FACT, BRANCH_PROMOTION | YES unaffected in phase 2; dirtied in phase 1. NO/UNKNOWN records: `dirty` (M6.5) | N-actionable class (base §7) | absence-based NO (closed) and UNKNOWN (open) flip after a FACT taught in a later session; no stale NO/UNKNOWN is ever served (v1 never serves them; the test pins that the walk gives the new verdict) |
| a guess arrives | HYPOTHESIS | YES unaffected (no-op when held, base §2); UNKNOWN lacunae may change | H-control, H-bridge | hypothesis on a held pair across restart is a no-op; on an open pair it never produces a `hit` |
| a rule constant changes | RULE_CHANGE | `engine_version` mismatch → `dirty` | — | bump `limit`/`max_hops`/gate/`learn_beta`; every record misses; re-derivation refreshes `derived_at.engine_version` |
| world mode changes | RULE_CHANGE(world_mode) at session boundary | all answer records `dirty`; beliefs retained | `test_the_same_gap_is_a_plain_no_under_a_closed_world` (:325) | restore under the other flag: identity mismatch refused (`E-MEM-011`) unless the RULE_CHANGE row precedes it; then zero hits until re-derived |
| the context differs | any query bound to another `stream_id` | no record is even a candidate (M1.3) | `test_outputs_are_deterministic_across_two_identical_organisms` (:568) is the same-context analogue | two streams with identical tokens and opposite facts; zero cross hits (denominator: all fast-path lookups) |
| schema/engine code changes | new `schema_version`/`engine_version` | migration or refusal (M10.2) | — | old document under new reader: refused or migrated; never silently read |
| a promoted premise is retracted | RETRACT of a promoted given | cascade like any other given | — | promote → derive → RETRACT → withdrawn; before and after restart |
| the organism has faulted | any beat with `E-ORG-003` | fast path disabled for the stream (`E-MEM-022`) | `test_the_heartbeat_decays_experience_and_audits_standing_conclusions` (:346) | inject a broken cascade (ablation) → fault → zero hits thereafter and after restart |
| restart itself | — | restore validation gate (M9.3) | — | corrupt digest → no answers served; report the lost boundary |

Each invalidation is applied **in the same committed transition** as the event that causes it (M9.1 step 4): the workspace cascade already does this synchronously inside `consume` (workspace.py:323-327), and the record layer's `dirty` marks are set before the document is saved and the row acknowledged. Correctness never waits for a background cleanup.

### M8.5 Guesses stay on uncommitted branches; promotion rules

- A **stream HYPOTHESIS** is committed history (it is an event) but is held as `Status.HYPOTHESIS`, never ASSERTIVE, never a candidate (M8.1 step 4 intersects with `standing`, which holds only CONCLUDED YES pids). In the atlas it is HYPOTHETICAL (M5.2).
- An **uncommitted branch** is a separate `stream_id` with `branch_id ≠ trunk`, its own history document, its own scratch organism, its own ASSUMPTIONs (M6.7). It may guide exploration (RPA shows it, M5.3). Nothing with a branch `stream_id` is ever a trunk candidate (M1.3).
- **Promotion** is only by an explicit BRANCH_PROMOTION row (M2.3, reserved in v1), accepted through the trunk host's `consume`, producing new committed `seq`s. It promotes givens only; it validates each promoted given by consuming it (the workspace's own refusal/contradiction rules apply); it never copies a branch derivation or `standing` entry. Retraction of a promoted premise cascades like any other (M8.4 row).
- The directive's **meaningful guess probe** (an unsupported tempting guess, a supported competing fact, a later correction, with frozen expected outcomes; the audit's "H-tempting generator variant", R20) is expressible under this contract because every served answer carries `route` (M8.7): the probe's pass condition includes "zero `hit`s whose record rests on a HYPOTHESIS", which the hit log makes countable. If the measured difference is zero, it is reported as zero.

### M8.6 Ordinary index and RPA narrowing

- The **ordinary index** is a dictionary `AnswerKey → AnswerRecord` and `RecordKey → BeliefRecord`, rebuilt from the workspace and rows at restore. It is the required comparison path ("record-first without RPA").
- **RPA narrowing** (`rpa_routing`) may only return a subset of the index's candidates (`E-MEM-031` if it returns a key the index did not). Everything after step 4 of M8.1 is identical in both paths, so a measured difference is attributable to the atlas alone (directive §4).

### M8.7 Reversibility and measurement

- `record_first` and `rpa_routing` are independent; turning either off loses no accepted event (the history document is the authority; indexes are disposable). Walk-first is restored from the same document by constructing the organism and not consulting the index. The audit's rollback holds: "delete the two functions and the flags — the walk-first path and all 393/262 tests are untouched; a history document with no reader is inert data" (audit §7).
- Every ASK row's `outcome.route` ∈ `{hit, miss, rejected:<check>, fallback:<reason>, disabled}` (M2.2). Hit/miss/rejection/fallback reasons are the evaluation's denominators.
- **Work is measured as performed.** `Organism._reason` adds `len(self.ws.props)` to `_scanned` on every walk (organism.py:633) — the walk's *input size*, not its visits. A hit must record `work_scanned = 0`, `work_asks = 0`, and two new counters: `records_examined` and `dependency_edges_checked` (= the size of the transitive support set walked in step 5d). A miss or fallback records the walk's counters **plus** the fast path's own, so its overhead is charged, never hidden. For the common work unit across the four paths (directive §5 "examined dependency edges"), the smallest compatible change is for `HypothesisBank.surface` to report the number of edges it actually expanded alongside its `Reading` (banks.py:168-247) — **proposed, INFERRED compatible**, not required by this contract.
- **Smallest compatible change to `Organism`** (proposed, consistent with the audit's "flag in `_ask`"): `_ask` consults the record-first check when the flag is on and, on a validated hit, builds the `_Outcome` without calling `_reason`. Everything else in `consume` — clock, `_withdraw`, beat, metering, `Response`, `log` — runs unchanged. The index lookup itself is injected (an optional callable), so organism.py gains no index code. `Response` gains a defaulted `route: str = ""` field (frozen dataclass, keyword-constructed at organism.py:493-511, so a trailing default is compatible). **Side effects of a hit — decision needed (M12 Q5):** on the walk path a CONCLUDED YES perturbs motivation (organism.py:638) and writes the CMB at LEARN (runtime.py:573). Either (A) the hit emulates both from the record's stored confidence so that the accepted-state digest is **path-independent** and the four paths can be compared by digest, or (B) it does neither and CMB/motivation are excluded from the cross-path digest. (A) is recommended: digest equality across paths is the cheapest strong check that the fast path changed only work, not state.

---

## M9. Durability contract

### M9.0 Acknowledgment, survival levels, assumptions, and what tests cannot show

- **An update is acknowledged** only after: (i) `consume` has returned, so the event and all its invalidations are applied to the in-memory committed state (M9.1 step 4); (ii) the history document containing the new row has been written to a temp file, `flush`ed, `fsync`ed, atomically replaced into place, the directory `fsync`ed, and read back with a matching `document_digest` (M9.1 step 6). The acknowledgment returns the committed `seq`, `event_id`, `commit_status` and `outcome`.
- **What survives** an acknowledgment, and at which level (owner decision 1):
  - **(a) same-machine survival:** every acknowledged row, recoverable by M9.3 from the current document or, failing that, the retained previous document plus nothing (the document is complete). Failure model: process termination at any instruction, including between any two steps of M9.1/M9.3; a crash during the temp write leaves the previous document intact (audit §2.4).
  - **(b) replacement survival:** every acknowledged row, **only if** the document directory lives on, or is copied to, the **existing authorized storage arrangement** that outlives the machine — and only once a terminate-and-replace test has actually restored from it. A folder on an AWS machine is not automatically lasting storage; it may vanish when the machine is terminated. Which arrangement that is, and how the directory reaches it, is M12 Q1; until it is named and tested, no (b) claim is made.
- **Storage and filesystem assumptions for (a):** a local POSIX filesystem that honours `fsync` on files and directories and makes `os.replace` atomic with respect to crashes (ext4/XFS on an AWS EBS volume, per the directive's AWS-only scope); one host; no other process modifies the directory; no network filesystem; disk capacity reported by the OS (M10.1 "full storage budget").
- **Outside the model, and stated so:** disk or volume loss, silent media corruption beyond what the document digest detects, a filesystem or device that acknowledges `fsync` without persisting, host loss without volume persistence, and clock or identity tampering. **Ordinary file-write, rename and process-kill tests establish (a) on a filesystem that keeps its promises; they cannot establish (b), nor survival through every disk, host or power failure**, because the only way to test an `fsync` lie is to remove power or use a fault-injecting filesystem, and the only way to test (b) is to terminate and replace the machine. Any claim made from these tests says "(a), under the declared failure model".
- **Claim wording** follows M0.1: "(a)" or "(b)", never one read as the other.

### M9.1 Commit and checkpoint sequence (whole-document rewrite, by reference to `native_recovery.py:183-202`)

In v1 the checkpoint **is** the commit: every acknowledged row is in a complete, digest-sealed document. There is no separate tail to replay.

```
commit(proposal):
  1  VALIDATE VERSION   — proposal.expected_version == last_committed_seq, else REJECTED_STALE (M6.2),
                          except ASK which may be serialised explicitly.
  2  ASSIGN             — seq = organism.clock; event_id = sha256(stream_id, seq, canonical) (M2.4).
                          A row already present with this event_id → return its stored outcome
                          (lost-ack retry, exactly once); same id, different payload → E-MEM-003.
  3  PRE-CHECK          — CORRECTION: §8 status table on the RETRACT half (organism.py:561-590);
                          BRANCH_PROMOTION (reserved): branch_head_digest matches the branch document.
  4  APPLY              — organism.consume(event) → Response  (one per Event; two for CORRECTION).
                          This is where every invalidation happens: the workspace cascade is
                          synchronous (workspace.py:323-327), _withdraw and the beat run (organism.py:489-490).
  5  MARK RECORDS       — write/refresh AnswerRecord on CONCLUDED YES; set `dirty` on every absence-based
                          record (phase 1: on any ACCEPTED mutation). Same transition as step 4.
  6  SAVE               — save(path): document = header + rows[0..seq] + reference_digest (M4.4);
                          canonical bytes; size bound (M10.3); tempfile in the destination directory;
                          write; flush; fsync(file); os.replace(temp, current); fsync(directory);
                          read back; document_digest must match (E-MEM-040 → the previous document stands,
                          temp removed, the in-memory organism is discarded and reloaded from it).
                          Retain the previous document as history.<seq-1>.json per M10.3.
  7  ACK                — last_committed_seq = seq; return.  Nothing before this line is "committed";
                          a crash before it means the proposer never saw an ack and must retry (step 2
                          makes the retry exactly-once).
  (ordering note)       Steps 4–5 precede 6: the in-memory state is ahead of the durable document for the
                          width of one save. A crash there loses an event nobody was told was committed;
                          restore (M9.3) rebuilds from the last complete document, so the lead is harmless.
                          This ordering is forced because `consume` must run to know the outcome the row
                          records. Documented here as the directive requires; recovery rule in M9.4.
```

**Why whole-document rewrite in v1:** it is the CNCM pattern reused by reference (audit §2.2), it has no torn-tail case (audit §2.4), and the audit judges its O(n)-per-commit cost acceptable at the family's scale (audit R24, INFERRED there). Its cost is **measured**, not assumed: the evaluation reports cumulative bytes written and save latency per commit (directive §5). If at the M10.3 bounds the cost is shown to fail the declared speed workload, the hash-chained append log is the recorded alternative (M6.1) and its torn-tail rule is then added to M9.4 by amendment.

### M9.2 Smallest compatible mapping to existing recovery

| requirement | existing | what it already does | exact gap | smallest compatible change |
|---|---|---|---|---|
| atomic durable write | `save_native_journal` (native_recovery.py:183-202), `save_compound_journal` (compound_recovery.py:231) | temp + fsync(file) + `os.replace`, byte bound | no directory fsync; no read-back verification; single path overwritten in place (audit §2.2) | `save(path)` in organism.py following it by reference; add dir fsync, read-back digest, retained copies |
| digest verified against a trusted anchor | `replay_native_journal` (native_recovery.py:110-131), `recover_compound_journal` (compound_recovery.py:139-176) | caller supplies `expected_journal_digest` from a trusted receipt; schema and profile checked | the anchor lives with the caller; the organism has no caller-side receipt | document footer digest + reference digest; where an external anchor lives is M12 Q2 |
| replay reproduces every transition | native_recovery.py:159-178 (`require(outcome.trace_event == wire)`, final state reconstructs) | exact-reproduction replay | the organism's analogue is `consume` reproducing each row's `outcome` | M9.3 step 4 compares the `Response` projection to the row's `outcome` |
| framed append with checksum | — | — | exists nowhere (audit R24) | **not needed under whole-document rewrite**; alternative only if that is shown to fail (M6.1) |
| bounds on journal size | `MAX_JOURNAL_BYTES`, `MAX_JOURNAL_EVENTS`, `MAX_EPISODES` (native_recovery.py:18; native_engine.py:345-349) | refuses oversize journals | numbers are CNCM's; no retention anywhere (audit R27) | M10.3 defaults |
| idempotent re-delivery | — (CNCM replay fails closed on any deviation, audit §2.4) | — | exactly-once "cannot be expressed without an id layer" (audit §6) | `event_id` intake rule (M2.4, audit R31) |
| read-only projection after replay | `native_atlas_from_journal` (rpa_native_adapter.py:62-66) | replay first, project second | no `Organism` adapter | M5.1 |

### M9.3 Restore sequence

```
restore(stream_dir, expected identity, optional reference):
  1  OPEN              — read history.current; parse with duplicate-key and non-finite rejection
                         (the native decoder's rules, native_recovery.py:37-43); verify document_digest.
                         If missing or invalid → step 1' with the newest retained history.<seq>.json.
                         If none verifies → STOP (M9.5).
  2  VERIFY IDENTITY   — header.identity == expected identity (project, organism, context, branch,
                         world_mode, constructor_args); schema_version compatible (M10.2);
                         semantics_version and engine_version equal to the running code's, else
                         RULE_CHANGE handling (M6.6) or refusal.  A hash alone does not authenticate the
                         stream (native_recovery.py:5 says the same of its journal); identity fields are
                         compared one by one.
  3  CONSTRUCT         — organism = Organism(**header.constructor_args, closed_world=header.world_mode)
  4  REPLAY            — for each row in seq order: refuse seq != organism.clock (out of order, E-MEM-041
                         → quarantine, M9.4); skip a row whose event_id was already applied (duplicate
                         delivery harmless); organism.consume(row.event); compare the Response projection
                         with row.outcome (verdict, lacunae, contested, withdrawn, accepted, code) — a
                         mismatch is a semantics divergence → STOP.  RULE_CHANGE / BRANCH_PROMOTION rows
                         (reserved) are applied per M2.3 without a consume.
  5  REBUILD INDEX     — ordinary index from props + rows (M3); validate standing ⊆ ASSERTIVE.
  6  VERIFY STATE      — reference_digest(organism) == footer.reference_digest  — BEFORE returning
                         (audit §7). Heartbeat.audit(organism) == [] now (organism.py:333), not at the
                         next beat; faults == []; no ASSUMPTION on trunk (M6.7).
  7  COMPARE REFERENCE — if the evaluation supplies a reference (ctl_recompute over the same rows, the
                         control of M0.3), compare verdicts/lacunae/contested per ASK row; mismatch → STOP.
  8  REBUILD RPA       — only now (M5.3); failures here never affect serving.
  9  SERVE             — last_committed_seq = organism.clock - 1; accept proposals.
```

The fresh-process form of this test is modelled on `tests/test_native_recovery.py:410-458` (audit §2.5): `subprocess.run([sys.executable, "-c", script])` with an import guard against model libraries.

### M9.4 Torn final event, quarantine, fallback

- **Torn write:** under whole-document rewrite a crash during step 6 leaves the previous `history.current` intact and a stray temp file, which restore removes (audit §2.4, INFERRED there for the gap between `os.replace` and directory fsync — this contract adds the directory fsync so the gap is closed on filesystems that need it). The rows added since that document were never acknowledged (M9.0), so losing them is correct. A CORRECTION whose two consumes happened but whose save did not is lost whole — never half (M8.4 row).
- **Corruption inside a document** (digest mismatch, parse failure, a row whose `outcome` does not reproduce under replay, a `seq` gap): **quarantine** — keep the damaged file aside under `quarantine/`, record the boundary (last good `seq` from the newest retained document that does verify, the failing check), and fall back to the newest retained `history.<seq>.json` that verifies. Never skip a row and claim success: rows after it were produced by an organism that had consumed it.
- **Damaged latest document:** fall back to the retained previous one (M10.3 keeps at least two). Rows between the two are the acknowledged updates lost; **report them by seq range** — that is "the exact boundary lost".
- **Lost acknowledgment, retried update:** step 2 of M9.1 returns the original outcome for an identical `event_id`; a row already in the document is never applied twice (step 4 of M9.3).

### M9.5 Stop serving when trust cannot be established

If no document verifies, or identity mismatches, or `reference_digest`/`outcome` comparison fails, or the audit speaks, or a reference comparison fails: the host **does not serve any answer**, fast or walk, and reports exactly: the last trusted `seq`, which check failed, which documents were tried, and the seq range lost. Continuing with a partially trusted state would be serving an answer whose provenance cannot be stated — the thing M3 exists to make impossible. The native recovery already fails closed on any mismatch (native_recovery.py:169-179, audit R29); this contract adds the fallback and the report.

---

## M10. Faults to inject, migration and rollback, retention, compaction

### M10.1 Faults to inject deliberately (directive §3, verbatim as a checklist)

- [ ] Terminate a fresh operating-system process before and after each commit boundary; during log append; during snapshot write; before and after manifest publication; and during replay.
- [ ] Replay the same event twice, interrupt recovery and restart it, present out-of-order events, and retry an update whose acknowledgment was lost. Each accepted logical update must appear exactly once.
- [ ] Test truncated logs, corrupt snapshot bytes, a missing index, incompatible schema versions and a full storage budget. Rebuild a disposable index without changing accepted beliefs.

Mapping to v1's shapes: "log append" and "snapshot write" are both the single `save` of M9.1 step 6 (kill before the temp write, during it, between `os.replace` and the directory fsync, and after); "manifest publication" is the `os.replace`; "truncated logs" and "corrupt snapshot bytes" are a truncated or corrupted `history.current`. Each run of this checklist is an **(a)-level** test (M0.1). The **(b)-level** test — terminate the machine, replace it, restore from the authorized storage arrangement — is a separate line, run separately, reported separately. For every fault: compare recovered answers and support traces with the independent reference through the acknowledged prefix, then continue learning after recovery and restart again (directive §4).

### M10.2 Migration and rollback

- Schema migration is explicit and versioned: a migrator reads `schema_version = X`, writes a **new** document under `Y` and leaves `X` untouched and compatible (never overwritten, never deleted during migration). The migrated document is validated by M9.3 steps 1–7 under the `Y` reader, and its replayed behaviour compared with the `X` reader's on the same rows, before `history.current` is switched atomically. CNCM already keys each schema to a distinct string and refuses unknown ones (native_recovery.py:21, 128; audit §2.6) — the same rule here.
- Rollback: the `X` reader must still open the untouched `X` document. If the `Y` document gained row types `X` cannot read (e.g. RULE_CHANGE), the rollback boundary is stated precisely as "rollback to `X` is supported up to seq *n*; rows after *n* are not readable by `X`" — a precise unsupported-rollback boundary rather than a silent one.
- Do not overwrite data the previous version needs: `X` files are read-only after migration until the owner decides to retire them (M10.3).

### M10.3 Retention limits — initial engineering defaults (owner decision 3)

These are **bounded initial limits set before the first run, as conservative engineering choices to be revised from measurements**. They are not "keep everything until measured". When a limit is reached the system **stops safely and reports the limit**; it never silently discards accepted knowledge. Each is a named constant in `scripts/cas_rpu/organism.py` beside `save`/`load` and is recorded in the document header so a reader knows under which limits a document was written.

| constant | default | why this number | when reached |
|---|---|---|---|
| `MAX_HISTORY_EVENTS` (rows per stream document) | **4,096** | The suite is 20 starting conditions × 5 sessions (owner decision 6); the §7 family runs ≈ 89 probes per world over 40 items, so a condition followed through 5 sessions is a few hundred rows. 4,096 is ≈ 8× that, and keeps whole-document rewrite cost small (M9.1). | `E-MEM-050`: refuse new mutations (ASKs may continue to be answered from the walk, not saved); report; the owner either compacts under M10.4 or opens a new stream with a recorded `continues_from` link. |
| `MAX_HISTORY_BYTES` (one document) | **8 MiB** | Matches `MAX_ATLAS_BYTES = 8 * 1024 * 1024` (rpa_model.py:30) — one existing bound reused rather than a new one invented; ≈ 2 KiB per row at 4,096 rows. | as above |
| `MIN_RETAINED_DOCUMENTS` | **2** (current + previous) | M9.4 fallback needs one verified predecessor; never fewer. | — |
| `MAX_RETAINED_DOCUMENTS` | **8** per stream, plus one pinned copy per session end | Enough to roll back across a whole 5-session condition; bounded so a stream cannot fill the volume with copies. | Oldest **archived** (moved to `archive/`, never deleted by code); the owner decides deletion. |
| `MAX_STREAMS_PER_VOLUME` | **64** | 20 conditions + branches + scratch; 64 × 8 docs × 8 MiB = 4 GiB worst case, an explicit volume budget. | refuse to open new streams; report |
| `MAX_BRANCHES_PER_STREAM` / `MAX_BRANCH_EVENTS` | **4** / **512** | Branches are reserved in v1 (M2.3); the bound exists so that admitting them cannot silently multiply storage. | refuse to open a branch; report |
| `MAX_ANSWER_RECORDS` (index, per stream) | **2,048** | ≤ one per ASK row at `MAX_HISTORY_EVENTS`; index is disposable. | evict `dirty`/`unsupported`/`conflicting` first, logged; a `valid` record is never evicted silently — if only valid records remain, report instead |
| `MAX_RPA_NODES` / `MAX_RPA_BYTES` | **10,000** / **8 MiB** | Under the recorded adapter's `MAX_JSON_NODES = 100000` and equal to `MAX_ATLAS_BYTES` (rpa_recorded_helm.py:32, counted from the header read at `eb99855`; rpa_model.py:30). | refuse to build the atlas (serving is unaffected, M5.3); report |
| `MIN_FREE_BYTES` (volume) | **max(64 MiB, 10 × current document size)** | A save needs room for the temp file beside the current one; headroom so a full disk is reported before, not during, a write. | `E-MEM-051`: refuse new mutations; abandon any in-progress save (temp removed); the previous document stands; report |

All numbers are to be revised from the first run's measurements (cumulative bytes written, save latency, rows per session), and the revision is an M13 amendment with the measurement cited.

### M10.4 Compaction rules (what may be compacted, and what never)

Compaction in v1 means producing a new document whose replay yields the same reference digest as the old one's (M4.4), verified before the old one is archived.

1. **Retained document copies** beyond `MAX_RETAINED_DOCUMENTS` may be archived off the hot path, provided the retained ones verify (M9.3 step 1). Archived, not deleted by code: "report the limit rather than silently dropping knowledge" applies to history as much as to beliefs.
2. **`Workspace.journal` strings** and **`Heartbeat.reports`** are regenerated by replay and are not in the document at all; nothing to compact.
3. **`BeliefRecord.status_history`** (index only) may be collapsed to the current status plus the last transition, since the rows have the rest.
4. **RETRACTED `^8`-stage propositions with empty `support` that no retained proposition names in its `support`** may be removed from a *materialised* state (v1.x). They are the remains of every episode's route guesses (banks.py:243-244, swept at runtime.py:326) and grow by up to 8 per ASK. `surface` skips stage `^8` regardless of status (banks.py:211), `derive` can never have rested on them (workspace.py:287-292), and `add` treats a RETRACTED existing entry exactly like an absent one (workspace.py:241-249). **INFERRED safe; required test:** the §7 family's fingerprints equal with and without this compaction, across a restart. Not applicable to v1's replay-based restore, where they are regenerated.
5. **Rows are never compacted away in v1.** A row cannot be dropped without changing the replayed CMB and motivation (M4.3), and a REFUSED row cannot be dropped without changing the oracle's refused indices (M2.6). If `MAX_HISTORY_EVENTS` is reached, the remedy is a new stream with a recorded `continues_from` and a materialised state (v1.x), never a shortened history presented as complete.
6. **Never compacted anywhere:** any proposition whose status is not RETRACTED; any RETRACTED proposition named in a retained proposition's `support` (explanation would raise `E-WS-001`, workspace.py:472-474); `_prior`; `standing`; `owed`; `g`; the CMB; `faults`; any row; any `valid` AnswerRecord.

Compaction preserves accepted meaning, the provenance needed for retraction (every ASSERTIVE pid's roots and their establishing event_ids), and recovery (the retained documents). When a limit prevents compaction under these rules, the host reports the limit.

---

## M11. Reuse map (requirement → existing module → gap → smallest compatible change)

This table summarises; the authoritative requirement-by-requirement audit is `docs/working/helm_reuse_audit_2026_10_06.md` §4 (R1–R31), which this contract follows.

| directive requirement | existing | already does | exact gap | smallest change |
|---|---|---|---|---|
| events with unique id, order, type, payload, polarity | `events.Event` (events.py:47-96) | canonical form, reserved-character and reflexive refusals | no id, seq, source, polarity field, commit status, version | row M2.2 (audit R4); no change to `Event` |
| corrections, rule changes, promotions | — | — | not expressible; "no counterpart exists" for rules/branches (audit R4) | CORRECTION as two rows (M2.3); RULE_CHANGE / BRANCH_PROMOTION shapes reserved |
| beliefs with provenance and validity | `Proposition` (workspace.py:77-98), `roots`/`justification` (workspace.py:451-480), `Heartbeat.audit` (organism.py:333-359) | status, support, support trees, dead-root audit | no event provenance, no version, no validity enum | host index M3; audit reused as the `valid` predicate |
| answers with support trace | `Episode` (runtime.py:171), `justification=ws.justification(...)` (runtime.py:591), `Response` (organism.py:366) | trace produced at derivation | not kept across sessions | AnswerRecord M3.2 |
| standing conclusions | `Organism.standing` (organism.py:461, 614, 685-693) | held YES pids, pruned on fall | no version, pid-keyed | candidate set of the fast path (M3.4) |
| complete checkpoint | `Workspace.snapshot` (workspace.py:482-488) | 4-value summary | not a checkpoint | history document + reference digest (M4, audit §7) |
| CMB, motivation, heartbeat state | `CognitiveMemoryBoard` (cmb.py:68), `Motivation` (organism.py:155), `Heartbeat` (organism.py:303) | in-memory; deterministic under replay | not in the audit's digest | extend the digest (M4.1, M4.2) |
| RPA entries, read-only, rebuilt after validation | `rpa_model.AtlasSnapshot` (rpa_model.py:385), `rpa_native_adapter` (rpa_native_adapter.py:62) | typed nodes/status, replay-then-project | no organism adapter | `organism_atlas_from_history`, linked by commit (M5; audit §7) |
| single writer, stale-version handling | `Organism.consume` (organism.py:470-513) | only event intake | no expected-version check, no id layer | decided by the audit (M6.1); host-side check before `consume` (M6.2) |
| conflict preservation | `Workspace.add` (workspace.py:217-225), `retract` reinstatement (workspace.py:313-321) | both sides kept, prior statuses, cascade | provenance not cross-session | event_ids in BeliefRecord (M6.3) |
| verdict precedence | runtime.py:396-402, 451-464, 487-496, 508-511, 704-717 | §3 rules 1–6 | none | fast path serves YES only when the same rules show clean (M6.4) |
| guarded positive path | `test_a_standing_conclusion_is_answered_from_the_record_on_re_ask` (organism tests:75) shows the walk already hits the DERIVED pid as a 1-hop route | correct answer from the record, after paying the walk | the walk is paid every time (base §0 item 3; results note §5.4) | flag in `_ask` + `route` field (M8.7; audit §7) |
| durability | `save_native_journal`, `replay_native_journal` (native_recovery.py:110-202); compound equivalents | atomic whole-file write, digest-anchored exact replay | no organism `save`/`load`; no dir fsync, read-back, retention, idempotent re-delivery, fault tests (audit §2.6, §7) | `save`/`load` by reference (~80 lines, audit §7) + M9/M10 |

---

## M12. Open questions for the owner

Decided by the owner on 2026-10-06 and therefore **not** open here: the single writer (audit decides → `Organism.consume`), retention philosophy and the need for initial numbers (M10.3 proposes them), the custodian's nature (M0.4), ownership (M0.4), the suite shape (M0.3), authority (header), implementation boundaries (M0.4), and the (a)/(b) claim-wording rule (M0.1, M9.0).

1. **The existing authorized storage arrangement.** Owner decision 1 says reuse it and verify what survives machine replacement. Which arrangement is it (a specific EBS volume that persists past termination, an S3 bucket, something else already authorized), and how does the stream directory reach it — mounted directly, or copied at session end? This decides whether any (b) test can be run.
2. **Trusted anchor for the document digest.** The native design keeps the expected digest with the *caller* (native_recovery.py:112-115). For the organism, does the `reference_digest`/`document_digest` in the footer suffice for (a), with the custodian role holding a copy of each session-end digest for (b) and for the evaluation — or is a separate anchor location required? Also: where the one `canonical_json`/`digest` implementation lives on the main branch, since `cncm/` is not importable from it.
3. **Canonical RPA checkout.** The directive names `_worktrees/codex-rpa-recorded-run`; the audit and this draft read `.claude/worktrees/rpa-readonly` at the same commit `eb99855`, and that worktree is no longer mounted. Which path is linked, who re-mounts it, and does Codex confirm it as the canonical entrypoint (M0.4)?
4. **Interim read of the reserved types.** RULE_CHANGE and BRANCH_PROMOTION are defined but reserved (M2.3, audit R4). Should v1's `load` refuse a document containing them (strict) or apply them per M2.3 (forward-compatible)?
5. **Fast-path hit side effects:** option A (emulate LEARN write and motivation perturb from the record so digests are path-independent) or option B (exclude CMB/motivation from the cross-path digest). M8.7.
6. **Refused CORRECTION and the beat:** a pre-checked refusal does not call `consume` and so does not beat, whereas a REFUSED RETRACT does. Accept the asymmetry, or route the refusal through a no-op consume so every row beats?
7. **Stale expected version:** reject mutations and serialise only ASKs (proposed), or serialise everything with explicit `serialized_from`?
8. **ASK in the authoritative history** (proposed yes, because ASK mutates state, M2.3; the audit stores "ordered `Event.canonical()` rows" without distinguishing) versus a separate query log — this changes what "fresh recompute" must replay and how its cost is reported.
9. **Store NO/UNKNOWN/INADMISSIBLE answer records in v1** for explanation and the four-path comparison, or YES only?
10. **`engine_version` definition:** commit hash plus the explicit constants digest (proposed) or commit hash alone (the audit's "engine digest").
11. **Where the amendment log and CHANGELOG entry go.** CLAUDE.md requires reading and updating `CHANGELOG.md`, but `git ls-files` shows no `CHANGELOG.md` on this branch; the vision doc says the contract carries "its amendment log" (roadmap step 2). Which file records M13 and the "preparation" label?
12. **World-mode change:** allow it as a session-boundary RULE_CHANGE (M6.6) or require a new stream always?
13. **Float canonicalisation** for the CMB and motivation digest: `repr` round-trip (exact, platform-sensitive in principle) or fixed rounding (robust, lossy for equality)?

---

## M12a. Resolutions (2026-10-06, by the implementer under owner decision 8: "don't make me choose internal module details that your audit can settle")

Only M12 item 1 remains with the owner, and it does not block (a)-level work. The rest are resolved as engineering defaults; each is reversible by an M13 amendment citing a measurement or a failing test.

| # | resolution | why |
|---|---|---|
| 1 | **Owner.** Until the authorized storage arrangement is identified, v1 claims survival level **(a)** only; every (b) sentence is written as "not demonstrated". | The implementer cannot see the environment's storage. Nothing in (a) waits on it. |
| 2 | The footer `document_digest` and `reference_digest` suffice for (a). For (b) and for the evaluation, the custodian role (M0.4) holds a copy of each session-end digest. One `canonical_json`/`digest` helper lives in `organism.py` and is imported by the test harness, never duplicated. | Matches native_recovery's "caller holds the anchor" by giving the custodian the caller's role. |
| 3 | The RPA checkout is linked by commit `eb99855` and branch `codex/helm-rpa-recorded-run-20260922`; it is re-mounted read-only on demand and never copied into this tree. Codex's confirmation of the canonical entrypoint stays PROPOSED (M0.4). | Owner decision 5; the audit §1.1 names the entrypoint. |
| 4 | `load` is **strict** in v1: a document containing RULE_CHANGE or BRANCH_PROMOTION rows is refused with `E-MEM-0xx` naming the row. | Reserved means reserved; forward-compatible application of undefined semantics is how a reader lies about a document. |
| 5 | **Option B.** CMB charge and motivation `g` are excluded from the cross-path digest and reported as per-path diagnostics; the cross-path digest covers props (status, support, stage, negated), `standing`, `clock`, counters and the event rows. | They are path-dependent by design (a fast-path hit does not LEARN); including them would make agreement between paths impossible by construction, not by defect. |
| 6 | A refused CORRECTION is routed through `consume` as a no-op row so **every row beats**. | One rule for all rows; the audit (§3) relies on beat count being a function of the row count. |
| 7 | Stale expected version: **reject mutations**, **serialise ASKs** with `serialized_from`. | A question cannot corrupt state; a mutation against a stale version can. |
| 8 | ASK rows are in the authoritative history. Fresh recompute replays them and reports that cost. | ASK mutates state (`standing`, motivation, `_asked`), M2.3. |
| 9 | Store answer records for **every verdict** (explanation, four-path comparison); the guarded path **reuses YES only** (M8.0). | Explanation needs the record; reuse safety needs the restriction. |
| 10 | `engine_version` = commit hash **plus** the explicit constants digest. | A constant change without a commit hash change would otherwise be invisible to the reader. |
| 11 | The amendment log is M13 in this file. The project CHANGELOG is `noetic-compass-scaffold/noetic-compass/CHANGELOG.md` (it exists; the drafter searched the wrong path) and receives the "preparation" entry when code lands. | CLAUDE.md requirement, satisfied at its actual path. |
| 12 | A world-mode change requires a **new stream** in v1. | World mode is a dependency of every absence-based record (M6.6); changing it in place would dirty them all, which is the same as a new stream with less clarity. |
| 13 | Floats: `repr` round-trip (exact). Revisit for (b) across machines with an M13 amendment and a measurement. | (a) is same-machine; exactness is the stronger check there. |

## M13. Amendment log

| date | finding | change | where |
|---|---|---|---|
| 2026-10-06 | v1.0 draft written against the base contract and the code cited above; nothing implemented | — | — |
| 2026-10-06 | Owner decisions 1–8 received (directive amendment log) and the reuse audit landed (`11de4a7ee`) | (a)/(b) survival levels and claim-wording rule added; single writer = `Organism.consume` per the audit, whole-document `save`/`load` by reference to `native_recovery.py` replaces the drafted append-framed log (kept only as a recorded alternative if reuse is shown to fail); v1 checkpoint = history document + reference digest, with the field table re-read as digest coverage; initial retention numbers proposed as engineering defaults; custodian described as internal separation of responsibilities; ownership and suite shape restated; authority wording updated; open questions reduced from 16 to 13 | header, M0.1, M0.3, M0.4, M2.4, M4.1, M4.4, M4.5, M6.1, M9, M10.1, M10.3, M10.4, M11, M12 |

Amendments to this contract are made in place with a dated row here, as the base contract does in its §12. It is not forked.
| 2026-10-06 | Landed in the repository; M12 items 2–13 resolved as engineering defaults (M12a); item 1 left with the owner, non-blocking for level (a) | M12a added | docs/working/helm_memory_contract_v1_draft_2026_10_06.md |
| 2026-10-06 | Implementation landed as `scripts/cas_rpu/history.py` (`Stream`, `Identity`, `reference_digest`, `canonical_json`/`digest`) rather than inside `organism.py`; `organism.py` is untouched and remains the single writer behind `Stream.commit` | M12a item 2 placement amended; one module, imported by the tests, never duplicated | `scripts/cas_rpu/history.py` |
| 2026-10-06 | `engine_version` implemented as a digest of the package sources (`scripts/cas_rpu/*.py`, `scripts/ccb_r1/*.py`), which subsumes the commit hash and the explicit constants digest of M1.1 | M1.1 / M12a item 10 amended | `history.engine_version` |
| 2026-10-06 | Retained copies are numbered by rows committed (`history.<n>.json`), genesis being `00000000`; copies beyond `MAX_RETAINED_DOCUMENTS` move to `archive/` | M4.5 / M10.3 wording | `Stream.save` |
| 2026-10-06 | First development measurement (104 rows, 8 generated items, this container): commit median 3.6 ms, p95 5.9 ms, max 9.0 ms; current document 45 KB; restore with replay and reference comparison 16 ms; cumulative bytes written 2.4 MB (whole-document rewrite × retained copies). M10.3 numbers unchanged pending the target-instance dry run | measurement recorded, no limit revised | `scripts/tests/test_cas_rpu_memory.py` run |
| 2026-10-06 | Guarded positive-answer path implemented: `Organism(record_first=..., record_invalidation="context"|"dependency")`; the check lives in `_ask` only, never calls `Workspace.ask`, serves only a held YES whose pid and every root are ASSERTIVE, whose denial is neither asserted nor disputed, and whose organism has no faults; `Response.route` ∈ {disabled, miss, hit, rejected:<check>}; a hit records `work_asks = work_scanned = 0` and `dependency_edges_checked`; `validated_at` is the record's `derived_at`, refreshed by every CONCLUDED YES walk. The `rpa_routing` flag and the external index/atlas lookup (M8.6) are NOT implemented yet. | M8.0, M8.1, M8.7 implemented in part | `scripts/cas_rpu/organism.py`, `test_cas_rpu_record_first.py` |
| 2026-10-06 | Hard law measured (n=80 both worlds, 181 probes each): both modes agree with the oracle on every probe, zero faults. Routes, dependency mode: 11 hits / 170 misses; context mode: 1 hit / 10 rejected / 170 misses (the generator interleaves unrelated facts before most probes, which whole-context invalidation refuses by design). Cost within the organism's own currency at n=40: repeat asks 10.9 (dependency) vs 13.7 (walk-first); a hit costs the size of its support set (4 for a three-hop chain) | measurement recorded | `revision_experiment.py` rows `organism_record_ctx`, `organism_record_dep` |
| 2026-10-06 | Level (b) path implemented: `Stream(mirror=store)` puts every sealed document (current and retained) into a dedicated remote location after the local write, with the store's own read-back; a remote refusal is `E-MEM-052` (local stands, not acknowledged at level b, healed by the next save); `Stream.restore_from(store, stream_id, fresh_dir)` rebuilds a stream on a machine with none of the local state and runs every restore check. The S3 client (`scripts/cas_memory/s3store.py`: Signature V4 over the standard library, put/get/head/list, never delete, never outside its prefix, signer verified against AWS's published example) lives OUTSIDE the reasoning package because the sever law forbids network reach inside it; it is injected, never imported by `history.py`. M12a item 1 amended: the owner named the arrangement as "a dedicated persistent location in the existing AWS setup" | M9.0 survival levels, M12a item 1 | `history.py`, `scripts/cas_memory/s3store.py`, `test_cas_rpu_replacement.py` |
| 2026-10-06 | Replacement proof, mechanism (offline, `DirectoryStore` as the second location): three fresh OS processes, each machine's local state destroyed before the next restores from the remote alone; taught fact answered, retraction withdraws dependents, retraction survives the third restart. **Live S3 run not performed:** the sandbox's AWS key is rejected by the service (`InvalidAccessKeyId`, both existing buckets, 2026-10-06). The live test is in place and gated on `HELM_S3_BUCKET` plus a valid key; it skips with the reason until then. Level (b) is therefore NOT yet demonstrated on the real location | measurement and blocker recorded | same |

