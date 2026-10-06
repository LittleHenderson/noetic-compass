# HELM §6 — Cross-engine meaning reconciliation: conformance fixtures and interchange envelope (DRAFT)

Date: 2026-10-06. Status: DRAFT for owner review. Grants nothing; proposes a contract extension only.
Scope: MEANING (polarity, negation, unknown, conflict, correction, retraction, rules/recipes, lesson
promotion, reload, world mode, context/branch) and the envelope that carries it. The REUSE MAP of CNCM
recovery code is a separate document by another agent and is not duplicated here.

Sources inspected (read-only):

- CAS-RPU, main checkout `/home/user/noetic-compass` at `8d8035cf` (branch `claude/cas-reasoning-processor-i47toc`):
  `scripts/cas_rpu/{events,workspace,organism,revision,runtime,encoder}.py`, `scripts/ccb_r1/rpm.py`,
  `docs/working/revision_streams_contract_2026_10_06.md` (cited below as `contract.md`).
- CNCM, read-only checkout `/home/user/noetic-compass/.claude/worktrees/rpa-readonly/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`
  at `eb9985566bd11a89f485d627186ef0efa7177f02` (cited below as `CNCM/`).
- Directive: `scratchpad/helm_in/directive.txt` lines 100–116 (§6) and 108–111 (reconcile meanings; envelope).

Evidence gap stated up front: the directive's evidence item [3] cites `CNCM_WORKSTREAM_RECONCILIATION_20261006.md`
and `CNCM_NEXT_BEHAVIOR_EXPERIMENT_20261006.md` "in the home-base docs folder" (directive.txt:145). Neither file
exists in the pinned CNCM checkout (`CNCM/docs/` listing) nor anywhere under `/home/user` (searched), and
`docs/HELM_VISION_AND_ROADMAP.md:70` already records that they are not in this repository. Everything below about
the "frozen v0.1 entrypoint" is therefore cited from what IS present (`CNCM/README_HANDOFF.md`, `CNCM/cncm/cli.py`,
`CNCM/AUTHORITY_MANIFEST.yaml`), not from the two reconciliation documents. DeepSeek's source was not available in
any checkout; every DeepSeek cell below is UNVERIFIED.

Conventions: `file:line` cites are exact to the checkouts above. `[inference]` marks a conclusion drawn from code
behaviour rather than a stated contract. `[unverified]` marks claims about artifacts not present.

---

## 1. Side-by-side meaning table

### 1.0 Reading guide — the two engines are not the same shape

- CAS-RPU is an **event stream** engine: five event kinds (`events.py:14-21`), one living `Workspace`
  (`organism.py:8-10`), verdicts over a positive ASK (`events.py:117-118`), three-valued plus INADMISSIBLE
  (`contract.md:106-126`). Ground truth is a function of the stream and the replayer `revision.replay()` is the
  oracle (`revision.py:626-646`, `contract.md:14-24`).
- CNCM RRK v0.1 is a **per-run immutable packet** engine: a `ProblemPacket` carries entities, predicates, facts,
  rules and one query (`CNCM/cncm/model.py:483-497`); state mutates only through intents validated by a sole-writer
  `TransactionCoordinator` (`CNCM/cncm/kernel.py:1`, `CNCM/AUTHORITY_MANIFEST.yaml:153`); the only cross-run carry
  is same-instance episodic memory (`CNCM/cncm/engine.py:94-110`, `CNCM/README_HANDOFF.md:108,124-126`). Retraction,
  correction and source-attested values exist only in the later semantic (v0.4) / compound (v0.5) / derived (v0.6)
  layers (`CNCM/cncm/semantic_model.py:61-94`, `derived_model.py:100-114`), and lesson promotion exists only in the
  isolated apprenticeship laboratories with zero kernel authority (`CNCM/cncm/cognitive_apprenticeship.py:1-14`,
  `CNCM/README_HANDOFF.md:278-279`).

A field-name match between these shapes is therefore never sufficient; every row below says what breaks.

### 1.1 The table

| Concept | CAS-RPU representation | CNCM representation | Mismatch | Proposed reconciliation | Lost by naive field mapping |
|---|---|---|---|---|---|
| **Assertion** | `events.fact(s, o, relation="leads_to")` → `Workspace.fact(...)` → `Proposition(status=FACT, negated=False)` keyed `s\|rel\|o` (`events.py:101-102`, `organism.py:520-531`, `workspace.py:78-98,253-254`). Re-asserting a weaker status is a no-op; a stronger status wins (`workspace.py:241-251`). | `Proposition(predicate, arguments, polarity=True, evidence_status=ASSERTED, provenance, scope="global")`, key `predicate(args)@scope` (`CNCM/cncm/model.py:263-296`); packet facts MUST be `evidence_status: asserted` with ≥1 provenance (`CNCM/schemas/problem_packet.schema.json:99-115`). Only ASSERTED roots count as authoritative support (`CNCM/cncm/semantics.py:54-69`). | CAS-RPU facts are binary triples with one relation; CNCM facts are n-ary predicates with mandatory provenance and scope. CAS-RPU has no provenance field on `Event` (`events.py:48-54`). | Envelope `proposition` carries `{predicate, arguments[], polarity, relation}`; adapter to CAS-RPU accepts ONLY arity-2 with `relation ∈ {leads_to}` (and `co_occurs` for FACT/RETRACT only, `contract.md:60-64`); adapter to CNCM synthesises `provenance=[{source_type: "<source_engine>", source_id: "<event_id>"}]` from the envelope. | Provenance (CAS-RPU has none → fabricated on export). Arity > 2 and non-string terms (CAS-RPU rejects `|`/`~` in names, `events.py:60-64`). Status strength ordering (CNCM has no FACT>DERIVED>ASSUMPTION>HYPOTHESIS ladder, `workspace.py:69-74`). |
| **Explicit negation** | Separate event kind `NEGATION` (`events.py:19,109-110`); becomes `Proposition(negated=True)` whose `pid` is `"~" + key` (`workspace.py:96-98`); same key, opposite `negated` ⇒ `contradicts` (`workspace.py:100-101`). ASK has NO polarity (`events.py:117-118`); verdict NO arises from an ASSERTIVE negative record or closed world (`workspace.py:398-401`, `contract.md:123-125`). | Boolean flag `Proposition.polarity` (`CNCM/cncm/model.py:267,283-284`; schema `proposition.schema.json:16`); key prefix `"not:"` (`model.py:296`). The QUERY itself carries polarity (`model.py:493`; unify requires `pattern.polarity == fact.polarity`, `semantics.py:128-131`). Rules may conclude a negation (`semantics.py:184-191`). Conversation facade: `"X is not Y."` → `DialogueFact.polarity=False` (`CNCM/cncm/conversation.py:307-310,523`). | Both are explicit polarity FLAGS at the proposition level; the directive's "negation predicate" form was not found in CNCM (see §1.2). The real divergence is **where polarity sits in a question**: CAS-RPU asks "P?" and may answer NO; CNCM asks "P?" or "¬P?" and answers supported/not-supported. CNCM has no NO verdict (`AUTHORITY_MANIFEST.yaml:188-199`). | Envelope `proposition.polarity` is REQUIRED (no default). A CAS-RPU NEGATION exports as `polarity:false, status:accepted`. A CNCM `polarity:false` fact imports as `events.negation`. A CAS-RPU ASK exports as polarity `true` query; a CNCM negative query imports ONLY if the adapter can express "is ¬P held?" — today it cannot (ASK is positive-only) → **reject** `query.polarity=false` toward CAS-RPU until an ASK-polarity extension exists. | Mapping CNCM `NEEDS_INFORMATION` on a positive query to CAS-RPU UNKNOWN loses the case where the denial is held and CAS-RPU says NO (contract rule 4). Mapping CNCM CONCLUDED on `¬P` to CAS-RPU "NO on P" is a meaning change unless `¬P` is ASSERTIVE in the workspace. |
| **Unknown / absence** | Open world: ASK on absent key → `UNKNOWN` with lacunae (`workspace.py:385-401`, `contract.md:126,148-177`); `Terminal.NEEDS_INFORMATION` (`scripts/ccb_r1/rpm.py:42-52`). A dispute is NOT a gap (`workspace.py:420-449`). Absence-based answers are invalidated by later FACTs (organism re-asks, `organism.py:661-683`). | `TerminalStatus.NEEDS_INFORMATION` with `global_workspace.lacunae = branch.unknowns` (`CNCM/cncm/engine.py:214-221`, `:957`); unknowns computed by `decompose_query` (`semantics.py:288-362`); `BranchStatus.BLOCKED` (`model.py:40-49`); golden `missing_information.json` → `halt_status: NEEDS_INFORMATION`, `lacunae: ["holds(P)@global"]` (`CNCM/golden/expected_final_states/missing_information.json`, fields near lines 194-210). | Both open-world UNKNOWN+lacunae. CNCM lacunae are rule-antecedent keys; CAS-RPU lacunae are `s\|leads_to\|o` keys bounded by `required ⊆ reported ⊆ admissible` (`contract.md:160-163`). CNCM has no closed-world mode at all (no field in `ProblemPacket`, `model.py:483-497`). | Envelope `answer.verdict = "UNKNOWN"` with `lacunae[]` in envelope proposition form; adapter maps CNCM NEEDS_INFORMATION → UNKNOWN **only when** `world_mode = open` (always true for CNCM RRK). | Lacuna scoring bounds (CNCM reports all unknowns; CAS-RPU requires the §4 bounds). The "dispute is not a gap" rule — CNCM reports both `contradictions` and `unknowns` on one branch (`engine.py:960-969`). |
| **World mode** | Per-workspace flag `Workspace.closed_world` (`workspace.py:172,385-401`); `Problem.closed_world` (`runtime.py:144`); closed world turns an unclosable chain into NO (`runtime.py:704-710`); paired streams differ only by UNKNOWN→NO (`contract.md:271-274`). A HYPOTHESIS does not reopen a closed world (`contract.md:139-140`). | RRK: none — open world by construction (no field; `NEEDS_INFORMATION` is the only absence outcome). Typed-teaching ingestion v0.2 has a per-snapshot **completeness declaration** line and states "This version does not implement open-world answers" (`CNCM/docs/CNCM_LEARNING_INGESTION_v0.2.md:19-24`). | Mode is a workspace property on one side, absent on the RRK side, and a per-snapshot text declaration on the typed-teaching side. The directive says world mode is a dependency (directive.txt:30). | Envelope `semantics.world_mode ∈ {"open","closed"}` REQUIRED. CNCM RRK adapter accepts only `"open"` and **rejects** `"closed"` (`E-IX-WORLD`), never coerces. Any answer record carries the world mode it was derived under. | Closed-world NO silently becoming UNKNOWN (or vice versa) across the boundary; invalidation of a closed-world NO when the world mode changes (directive.txt:42). |
| **Conflict** | Assertive vs assertive on one key ⇒ both `CONTRADICTED`, dependents cascade (`workspace.py:214-225,323-327`); assertive vs hypothesis ⇒ refutation, guess dies (`workspace.py:231-239`). Verdict INADMISSIBLE with `contested` keys — LOCAL to the queried route (Rule C, `runtime.py:449-468,480-500`; `contract.md:115-121,142-146`). Off-route disputes do not poison an answer (C-unrelated/C-bypassed, `contract.md:262`); `ctl_global_poison` is the named broken control (`contract.md:350`). | `detect_contradictions` groups by `atom_key` ignoring evidence_status (`CNCM/cncm/semantics.py:116-120`); recorded via `RECORD_CONTRADICTION` intent (`engine.py:502-522`, `kernel.py:854-866`); branch status CONTRADICTED; halt `CONFLICT_UNRESOLVED` if ANY branch has a contradiction (`engine.py:176,209-213`); `DECISION_COMMIT` rejected `UNRESOLVED_CONTRADICTION` (`kernel.py:1242-1244`); golden `contradiction.json` → `CONFLICT_UNRESOLVED`, diagnostics "explicit contradiction prevented commitment". | CNCM conflict is **branch-global**; CAS-RPU conflict is **route-local**. CNCM detection ignores status, so a HYPOTHETICAL vs ASSERTED pair would register as a contradiction `[inference from semantics.py:116-120; whether assumptions enter branch.propositions is not confirmed — see §5]`; CAS-RPU calls that a refutation. CNCM also has `INADMISSIBLE` but with a different meaning: "no admissible candidate survived comparison" (`engine.py:217-219`). | Envelope `answer.verdict` keeps CAS-RPU's four values and a separate `engine_terminal` field with the source engine's own terminal. Adapter from CNCM: `CONFLICT_UNRESOLVED` → `INADMISSIBLE` **only if** the contradicted atom lies on a supporting route of the query; otherwise the adapter must RE-DERIVE on the receiving side, not map. Conflicting independent assertions are preserved with provenance on both sides (directive.txt:29). | Rule-C locality (an off-route contradiction becomes a wrong INADMISSIBLE). The refutation/contradiction distinction (a guess becomes a dispute). The `contested_required` set equality (`contract.md:146`). CNCM's INADMISSIBLE ≠ CAS-RPU INADMISSIBLE. |
| **Correction** | No single event. Expressed as `RETRACT` then `FACT`/`NEGATION` (`events.py:19-20`, `contract.md:91-95`). Asserting the opposite WITHOUT retracting produces a CONTRADICTION, not a replacement (`workspace.py:217-225`). Retracting one side of a dispute reinstates the other (`workspace.py:313-321`, `organism.py:590-597`). | Semantic v0.4: `SourceStatement(action="ASSERT", previous_digest=<old>)` supersedes a prior statement (`CNCM/cncm/semantic_model.py:61-83`); statuses only `USER_ATTESTED`/`TEST_FIXTURE` (`:38,76`). Derived v0.6: `DerivedDefinition(revision, supersedes)` (`derived_model.py:100-114`); "Superseded definitions, corrected sources ... cannot silently reuse an old scalar" (`CNCM/docs/CNCM_DERIVED_MEMORY_IMPLEMENTATION_v0.6.md:45-47`). Conversation fixture `correction_learning` corrects a referent alias (act_type `CORRECT`), not a fact (`CNCM/fixtures/conversation/correction_learning/case.json`). RRK v0.1 has no correction (packet immutable per run). | CNCM corrections carry a `previous_digest`/`supersedes` LINK and a scalar VALUE; CAS-RPU has neither values nor a supersedes link, and its "correction" is two events with an intermediate UNKNOWN state. CNCM semantic values are rationals (`semantic_model.py:81`) — CAS-RPU has no value slot. | Envelope `event_type: "CORRECTION"` = atomic pair `{retracts: <event_id or proposition>, asserts: <proposition>}` with `supersedes` carried in `provenance.dependency_ids`. Adapter to CAS-RPU emits `retract(...)` then `fact(...)`/`negation(...)` and requires the RETRACT to be ACCEPTED (else the whole correction is rejected — `E-ORG-001/002` surface as `E-IX-CORRECTION-REFUSED`). Adapter to CNCM semantic layer emits `SourceStatement ASSERT` with `previous_digest`. Scalar values are **rejected** toward CAS-RPU (`E-IX-VALUE`). | The supersedes chain (lost in CAS-RPU; must be kept in envelope for round-trip). The intermediate "retracted → UNKNOWN" state (CNCM has no such moment). The refusal to "correct" a DERIVED belief (`organism.py:581-589`). |
| **Retraction** | `RETRACT` = epistemic withdrawal of a GIVEN; afterwards absence = UNKNOWN/NO by world (`events.py:19-20`). Refused for absent/retracted/hypothesis/assumption (`E-ORG-002`, `organism.py:563-580`) and for derived (`E-ORG-001`, names roots, `:581-589`). Transitive cascade by construction (`workspace.py:298-327`). No negative retract in the grammar (`contract.md:89-90`). Response names `withdrawn` standing conclusions (`organism.py:685-694`). | Semantic v0.4: `SourceStatement(action="RETRACT", value=None, previous_digest)` (`semantic_model.py:77-83`). RRK v0.1: none; a later packet simply omits the fact — but same-instance **episodic recall** still returns a prior conclusion by `conclusion.key` alone (`engine.py:378-385`), with RECALL treated as authoritative support (`semantics.py:78-79`); README documents this warm path with the `memory_recall` packet that has `facts: []` (`CNCM/README_HANDOFF.md:108`, `CNCM/fixtures/memory_recall/problem.json`). Apprenticeship `ROLLED_BACK` is version rollback, a different notion (`cognitive_apprenticeship.py:201-206`). | CAS-RPU retraction reaches transitive dependents; CNCM RRK has no retraction and its recall path does not re-check that the recalled conclusion's original premises are still present `[inference from engine.py:368-416 and the memory_recall fixture]`. This is precisely the directive's "old answers must never escape through the faster path" (directive.txt:9). | Envelope `event_type: "RETRACT"` targets a prior accepted event id AND the proposition; receiving owner must verify the target is a GIVEN (not derived) in its own stream or reject. Any imported retraction must trigger the receiver's own invalidation (CAS-RPU cascade; CNCM: no mechanism → receiver must reject or mark dependent episodes dirty — a gap for the reuse map). `polarity:false` retract is **rejected** both ways (`E-IX-NEG-RETRACT`). | Transitivity (CNCM recall). The GIVEN-vs-DERIVED refusal. Reinstatement of a denial after retracting the contested positive (`contract.md:93-95,403-404`). |
| **Rule / recipe storage** | No user-level rules. The only chained relation is `leads_to` with transitivity built into `^6`/`^9` banks; `co_occurs` is associative only (`events.py:29-30,121-123`, `contract.md:55-58`). HYPOTHESIS/NEGATION/ASK restricted to `leads_to` (`E-RS-009`, `revision.py:594-605`). Rules are therefore constants, not events; the contract says "Rules and world mode are dependencies too" (directive.txt:30). | Horn rules in the packet: `Rule(rule_id, operation ∈ {INFER_MODUS_PONENS, INFER_TRANSITIVE}, antecedents, consequent, provenance)` (`CNCM/cncm/model.py:347-392`, `rule.schema.json:11-14`); predicates declare `transitive` (`model.py:235`). Rules are per-packet, not persisted. Conversation facade holds in-session `DialogueRule` (`conversation.py:114-135,654-682`). Derived v0.6 stores `DerivedDefinition` recipes with revision lineage (`derived_model.py:100-139`). `^8` association is not generated by the runtime (`AUTHORITY_MANIFEST.yaml:132`; `NON_GOALS.md:12`). | CAS-RPU: one implicit transitive rule. CNCM: explicit, versioned rules with provenance. Associative `co_occurs` has no CNCM counterpart. | Envelope `event_type: "RULE"` with `{rule_id, operation, antecedents[], consequent, version}`. Adapter to CAS-RPU accepts exactly one rule — `INFER_TRANSITIVE` over predicate `leads_to` — and **rejects** every other rule (`E-IX-RULE-UNSUPPORTED`). Adapter to CNCM maps CAS-RPU `leads_to` to `PredicateDecl(leads_to, transitive=true)` + the matching transitive rule, and **rejects** `co_occurs` (`E-IX-RELATION`). Rule ids enter every answer's `dependency_ids`. | Modus ponens, n-ary rules, negative consequents (CAS-RPU cannot hold them). Association (CNCM cannot hold it). Rule versioning as an invalidation cause. |
| **Lesson promotion (guess → accepted)** | `HYPOTHESIS` enters `Status.HYPOTHESIS`, stage `"stream"` (`organism.py:91,533-542`); cannot support a derivation (`E-WS-002`, `workspace.py:283-292`); dead on arrival against a given or denial (`contract.md:83-87`). Promotion = a later `FACT` on the same pair: `pos.add; hyp.discard` (`contract.md:80-81`), stronger status wins (`workspace.py:241-251`). No receipt, no custody. | Kernel: `EvidenceStatus.HYPOTHETICAL` (`model.py:35`) excluded from support (`semantics.py:63`); only a COMMITTED, sealed branch may `WRITE_EPISODE` (`kernel.py:1289-1302`). Apprenticeship ladder: `PROPOSED → QUALIFIED → PROVISIONAL_LOCAL → DURABLE_LOCAL` with qualification + retention receipts from an examiner who is not the teacher (`cognitive_apprenticeship.py:189-198,1340-1365,1974-2004,2084-2117`; language twin `language_apprenticeship.py:150-157,1575-1598,1665-1688`); protected categories never promote (`:1978-1981`); zero kernel writes (`README_HANDOFF.md:278-279`). RPA: `NodeStatus.HYPOTHETICAL` vs `OBSERVED/VERIFIED`; `current_state_id` must be observed/verified, `hypothesis_branch_id` must be hypothetical (`rpa_model.py:36-41,412-419`); adapter proposals are `PROPOSAL_ONLY` hypothetical nodes (`rpa_native_adapter.py:193-199`). | CAS-RPU promotion is a one-event status upgrade with no evidence requirement; CNCM promotion is receipt-gated, multi-stage, local-only, and never writes kernel state. Neither side today produces an "accepted event retaining origin" for an imported lesson (directive.txt:111). | Envelope `status ∈ {"proposed","accepted"}` REQUIRED. An imported `proposed` lesson lands as HYPOTHESIS (CAS-RPU) / PROPOSED or HYPOTHETICAL (CNCM) and may never be promoted by the importer. Promotion happens only by a NEW accepted event authored by the receiving stream owner that cites the proposal's `event_id` in `provenance.origin` (directive.txt:111). | CNCM receipts/examiner independence (collapsed into "FACT"). CAS-RPU's "hypothesis vs hypothesis coexist" (`workspace.py:201-203`). Protected-category refusals. |
| **Reload** | None implemented. `Workspace.snapshot()` is a 4-field summary (`workspace.py:482-488`), not a checkpoint (directive.txt:21). `Organism` has no save/load; recompute from the event log is the oracle (`revision.py:626-646`). `Workspace.journal` is a list of strings (`workspace.py:174`). | Native/compound journals replayed from a caller-trusted genesis + expected complete digest + pinned source profile; every transition must reproduce its saved trace event and final state (`CNCM/cncm/native_recovery.py:110-180`, `compound_recovery.py:341-430`); replay receipt (`compound_recovery.py:456-467`). RRK episodic import is prohibited (`engine.py:96-101`, `AUTHORITY_MANIFEST.yaml:166`, `README_HANDOFF.md:126,288-289`). RPA is rebuilt from the replayed journal (`rpa_native_adapter.py:62-65`); recorded view labelled `ARCHIVED_RUN_RECORD_NOT_LIVE_HELM` (`rpa_recorded_helm.py:39`). Derived v0.6 reproduction continues saved prefixes in a fresh child process (`CNCM_DERIVED_MEMORY_IMPLEMENTATION_v0.6.md:72-73`). | CNCM reload = deterministic re-execution of intents under external trust anchors; CAS-RPU reload = (proposed) replay of accepted events. Neither imports foreign state directly. | Envelope `reload` is NOT an event type. Reload is the receiver replaying its OWN accepted stream; imported envelopes are themselves accepted events in that stream, so a reload replays the import, not the source engine's journal. Envelope carries `source_state_digest` so a post-reload audit can check the imported record against the source. | Nothing is lost if reload is kept out of the envelope; a naive "import the journal" mapping would violate CNCM's no-import rule and CAS-RPU's single-writer rule simultaneously. |
| **Context / branch** | None on `Event` (`events.py:48-54`). Isolation is procedural: one `Organism` per `StreamItem`, tokens drawn per item (`contract.md:224-226`). Branch concept = `Status.ASSUMPTION` "taken on for a branch" (`workspace.py:49`), counted ASSERTIVE (`workspace.py:61`; directive.txt:30 asks for explicit scope). | `Proposition.scope` (default `"global"`) embedded in `atom_key` (`model.py:270,291-292`); `branch_id` on `BranchFrame`/`Intent`/`ProofStep` (`model.py:863,721,1289`); `problem_id`/`goal_id` per packet (`model.py:486-487`); RPA `AtlasContext(context_id, model_version, observation_id, observation_time, record_version)` (`rpa_model.py:109-114`); semantic `scope,key` (`semantic_model.py:63-64`); derived `DerivedResultRef.scope` (`derived_model.py:51`). Episodic recall matches `conclusion.key` only (`engine.py:378-385`) — key includes scope but NOT problem_id. | CAS-RPU has no context identity at all; CNCM has several (scope, branch, problem, atlas context) that do not coincide. Same-named entities in two CNCM problems with the same scope share episodic memory `[inference from engine.py:378-385]`. | Envelope `context_id` and `branch_id` REQUIRED. Adapter to CAS-RPU maps `context_id` → a distinct `Organism` instance (today) or a workspace namespace (future); adapter to CNCM maps `context_id` → `Proposition.scope` (identifier-safe) so keys differ across contexts. Assumptions export with `status:"accepted"` plus `branch_id` ≠ main and `assumption:true`. | Cross-context answer leakage (directive.txt:23,81). Assumption scope. |

### 1.2 Polarity flag vs negation predicate — the dedicated subsection

**What was found.** Both engines represent negation as an explicit boolean on the proposition:

- CAS-RPU: `Proposition.negated: bool` (`workspace.py:84`), surfaced to the stream as a distinct event KIND
  (`EventKind.NEGATION`, `events.py:36`) rather than a flag on FACT ("Five kinds, and no sixth hidden in a flag",
  `events.py:14`). Identity-with-polarity is the string `pid = ("~" if negated else "") + key` (`workspace.py:96-98`).
- CNCM: `Proposition.polarity: bool` (`CNCM/cncm/model.py:267`), key `("" if polarity else "not:") + atom_key`
  (`model.py:296`); schema `polarity: boolean, default true` (`proposition.schema.json:16`). Conversation facade and
  language lab also use flags (`conversation.py:98`, `language_apprenticeship.py:119-121`).

**Where a "negation predicate" could arise.** No CNCM module defines a predicate named `not`/`neg`. Two places an
adapter could *manufacture* one, which is the hazard the directive names (directive.txt:109):

1. The CNCM key string `not:holds(P)@global` — a naive adapter that splits on the first `(` would read predicate
   `not:holds`. `[inference]`
2. The CAS-RPU pid `~AA|leads_to|BB` — a naive adapter that treats the leading `~` as part of the subject would
   produce subject `~AA`, which CAS-RPU itself rejects (`E-EV-002`, `events.py:60-64`).

DeepSeek's representation is `[unverified]`; the directive's phrase most plausibly refers to it (directive.txt:106
asks DeepSeek to "describe lesson, repair and reload semantics" from its own source). Resolution rule: **the envelope
carries polarity ONLY as `proposition.polarity: boolean` (required, no default). Any predicate name beginning with
`not`, `neg`, `~`, `¬` or `!` is rejected (`E-IX-NEG-PREDICATE`) rather than interpreted.** Round-trip is checked by
re-encoding the receiver's record into the envelope and comparing `polarity`, never by string-matching keys.

**Concrete example in both notations and the expected answer each side gives.**

Stream: "AA leads to BB" is given; "AA does not lead to CC" is given; then ask AA→CC.

CAS-RPU (events.py constructors):
```python
fact("AA", "BB")            # AA -> BB
negation("AA", "CC")        # AA -/-> CC   (pid "~AA|leads_to|CC", status FACT, negated=True)
ask("AA", "CC")             # verdict?
```
Expected: `NO` in BOTH worlds — contract rule 4 "an explicit denial with no route at all is knowledge, not a gap"
(`contract.md:123-124`); `Workspace.ask` returns NO because `~AA|leads_to|CC` is ASSERTIVE (`workspace.py:398-400`).
Lacunae: none (`contract.md:169`). Response.verdict = "NO".

CNCM (cncm.problem/0.1 packet, shape per `CNCM/fixtures/contradiction/problem.json:8-23`):
```json
{ "schema_version": "cncm.problem/0.1", "problem_id": "pol_ex", "goal_id": "ask_aa_cc", "seed": 0,
  "entities": [{"entity_id":"AA","entity_type":"node"},{"entity_id":"BB","entity_type":"node"},{"entity_id":"CC","entity_type":"node"}],
  "predicates": [{"predicate_id":"leads_to","argument_types":["node","node"],"transitive":true}],
  "facts": [
    {"predicate":"leads_to","arguments":["AA","BB"],"polarity":true, "evidence_status":"asserted","provenance":[{"source_type":"cas_rpu","source_id":"ev-0001"}]},
    {"predicate":"leads_to","arguments":["AA","CC"],"polarity":false,"evidence_status":"asserted","provenance":[{"source_type":"cas_rpu","source_id":"ev-0002"}]}
  ],
  "rules": [{"rule_id":"leads_to_transitive","operation":"INFER_TRANSITIVE",
             "antecedents":[{"predicate":"leads_to","arguments":["?x","?y"]},{"predicate":"leads_to","arguments":["?y","?z"]}],
             "consequent":{"predicate":"leads_to","arguments":["?x","?z"]},
             "provenance":[{"source_type":"cas_rpu","source_id":"builtin-transitivity"}]}],
  "query": {"predicate":"leads_to","arguments":["AA","CC"],"polarity":true} }
```
Expected (positive query): `NEEDS_INFORMATION` — `leads_to(AA,CC)@global` is not supported; `not:leads_to(AA,CC)@global`
is a different key (`model.py:296`) and no rule consequent unifies the positive query from AA→BB alone
(`semantics.py:335-351` adds the query key to unknowns; `engine.py:214-216`). `query_result.supported = false`
(`engine.py:955`). `[inference: exact lacunae set depends on rule unification with two unbound antecedents; the
verdict class is what the fixture pins]`

Same packet, `query.polarity: false`: Expected `CONCLUDED` with conclusion key `not:leads_to(AA,CC)@global`, because
the negated fact is ASSERTED and authoritative (`semantics.py:54-69,297-334`).

**So the SAME knowledge yields CAS-RPU `NO` and CNCM `NEEDS_INFORMATION` for the positive question.** An adapter that
maps `NEEDS_INFORMATION → UNKNOWN` fails this fixture; an adapter that preserves meaning must ask CNCM BOTH polarities
(or read the negative record directly) before emitting a CAS-RPU-comparable verdict, and must mark the result as
derived under `world_mode: open`. Conversely a CNCM `CONCLUDED` on `¬P` must not be exported as "NO on P" unless the
receiver's own check finds `¬P` ASSERTIVE in its workspace.

---

## 2. Conformance fixtures

Pass criterion for every fixture (directive.txt:109): the adapter passes only if the RECEIVING engine's answer equals
the expected answer column AND the expected state holds, checked on the receiver's own query path (for CAS-RPU: the
organism's `Response.verdict`, not `Workspace.ask`, per directive.txt:38). Field-name agreement alone is a FAIL.

Notation: CAS-RPU events use `scripts/cas_rpu/events.py` constructors. CNCM input is a `cncm.problem/0.1` packet
(RRK) or `SourceStatement` (semantic v0.4) where the RRK packet cannot express the step; successive CNCM steps mean
successive `CognitiveMachine.run()` calls on one persistent instance (`CNCM/README_HANDOFF.md:108,124`). Common
declarations for all CNCM packets: entities `node`, predicate `leads_to` (`transitive:true`), rule
`leads_to_transitive` as in §1.2. Provenance on exported facts: `{source_type:"cas_rpu", source_id:"<event_id>"}`.

### F01 — Assertion (positive given, direct hit)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `fact("AA","BB")`; `ask("AA","BB")` | facts: `leads_to(AA,BB) polarity:true asserted`; query `leads_to(AA,BB) polarity:true` |
| Expected answer | `YES` (`workspace.py:395-397`; `contract.md:122`) | `CONCLUDED`, `query_result.supported=true` (`engine.py:955`; cf. `golden/.../deduction.json`) |
| Expected state | `props["AA\|leads_to\|BB"].status == FACT`; pid enters `standing` after the YES (`organism.py:609-614`) | branch COMMITTED, `commitment_state.conclusion.key == "leads_to(AA,BB)@global"`; one episodic record if `WRITE_EPISODE` authorised (`kernel.py:1279-1327`) |
| Adapter must preserve | Status FACT (not DERIVED); provenance `ev-id` on the CNCM side. | |

### F02 — Explicit negation (the §1.2 example)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `fact("AA","BB")`; `negation("AA","CC")`; `ask("AA","CC")` | packet of §1.2, query polarity `true`; then the same packet with query polarity `false` |
| Expected answer | `NO` in open AND closed world (`contract.md:123-124`) | positive query: `NEEDS_INFORMATION`; negative query: `CONCLUDED` on `not:leads_to(AA,CC)@global` |
| Expected state | `props["~AA\|leads_to\|CC"].status == FACT`, no contradiction (`workspace.py:214-216` finds no positive counter) | both facts ASSERTED in `working_memory`; `branch.contradictions == []` |
| Adapter must preserve | Envelope `polarity:false, status:accepted`. Importing into CAS-RPU as `negation(...)`, NOT as `fact("AA","CC")` with a `not:` predicate. A CNCM→CAS-RPU verdict translation that emits UNKNOWN here FAILS. | |

### F03 — Unknown, open world (absence with a named gap)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `Organism(closed_world=False)`; `fact("AA","BB")`; `ask("AA","CC")` | facts: `leads_to(AA,BB)`; query `leads_to(AA,CC)` |
| Expected answer | `UNKNOWN`; lacunae must satisfy `required ⊆ reported ⊆ admissible` with `required = ∅` here (no hyp/assoc), so `()` is correct (`contract.md:150-174`) | `NEEDS_INFORMATION`; `lacunae` non-empty (CNCM reports rule-antecedent unknowns, `semantics.py:341-351`) |
| Expected state | no new props; `motivation.owed` has the want (`organism.py:639-640`) | branch BLOCKED (`engine.py:214-216`) |
| Adapter must preserve | UNKNOWN ↔ NEEDS_INFORMATION ONLY under `world_mode:open`. Lacuna lists are NOT compared for equality across engines (different key spaces); the envelope carries each engine's list under its own `engine_terminal` block. | |

### F04 — Closed-world NO from absence (and the CNCM rejection)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `Organism(closed_world=True)`; `fact("AA","BB")`; `ask("AA","CC")` | envelope with `semantics.world_mode:"closed"` presented to the CNCM adapter |
| Expected answer | `NO` (`contract.md:125`; `runtime.py:704-710`) | **REJECTED** at intake: `E-IX-WORLD unsupported world_mode "closed"`; no packet is built, no run occurs |
| Expected state | unchanged | unchanged |
| Adapter must preserve | A closed-world NO is never exported as a context-free NO: the answer record carries `world_mode:"closed"` and is invalidated if the mode changes (directive.txt:42). CNCM must not silently run it as open (which would return NEEDS_INFORMATION and look like "agreement on uncertainty"). | |

### F05 — Conflict on the queried route

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `fact("AA","BB")`; `fact("BB","CC")`; `negation("BB","CC")`; `ask("AA","CC")` | facts: `leads_to(AA,BB)`, `leads_to(BB,CC) polarity:true`, `leads_to(BB,CC) polarity:false`; query `leads_to(AA,CC)` |
| Expected answer | `INADMISSIBLE`, `contested == ("BB\|leads_to\|CC",)` (rule 3, `contract.md:117-121`; Rule C `runtime.py:480-500`) | `CONFLICT_UNRESOLVED`, `branch.contradictions == ["leads_to(BB,CC)@global"]` (`engine.py:209-213`; golden `contradiction.json`) |
| Expected state | both `BB\|leads_to\|CC` and `~BB\|leads_to\|CC` CONTRADICTED (`workspace.py:217-225`) | branch status CONTRADICTED; `DECISION_COMMIT` would be rejected `UNRESOLVED_CONTRADICTION` (`kernel.py:1242-1244`) |
| Adapter must preserve | Both conflicting assertions with their provenance (directive.txt:29); the contested atom identity. Mapping `CONFLICT_UNRESOLVED → INADMISSIBLE` is acceptable HERE because the contradicted atom is on the route — F06 shows where it is not. | |

### F06 — Conflict OFF the queried route (locality divergence; adapter must not map)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `fact("AA","BB")`; `fact("BB","CC")`; `fact("XX","YY")`; `negation("XX","YY")`; `ask("AA","CC")` | same facts in one packet; query `leads_to(AA,CC)` |
| Expected answer | `YES` — an off-route dispute does not poison the answer (C-unrelated, `contract.md:262`; Rule C comment `runtime.py:480-486`). `ctl_global_poison` is the control that gets this WRONG (`contract.md:350`). | `CONFLICT_UNRESOLVED` — any contradiction in the branch blocks commitment (`engine.py:176,211-213`) `[inference: the fixture pins the class; a run is required to confirm no earlier halt]` |
| Expected state | `XX\|leads_to\|YY`/`~XX\|leads_to\|YY` CONTRADICTED; `AA\|leads_to\|CC` DERIVED and standing | branch CONTRADICTED with `contradictions == ["leads_to(XX,YY)@global"]`, no commitment |
| Adapter must preserve | **This is a genuine meaning difference, not a mapping defect.** The adapter must NOT translate CNCM's `CONFLICT_UNRESOLVED` into INADMISSIBLE: the envelope carries `engine_terminal: CONFLICT_UNRESOLVED` with the contradicted atoms, and the CAS-RPU owner re-derives on its own path. An adapter that outputs INADMISSIBLE here FAILS; one that outputs YES by its own derivation PASSES. | |

### F07 — Correction (retract then re-assert; superseded value)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `fact("AA","BB")`; `ask("AA","BB")` → YES; `retract("AA","BB")`; `fact("AA","CC")`; `ask("AA","BB")`; `ask("AA","CC")` | semantic v0.4 only: `SourceStatement(scope,"k",source_id,value="11",status USER_ATTESTED,action ASSERT, previous_digest None)`, then `SourceStatement(... value="17", action ASSERT, previous_digest=<digest of first>)` (`semantic_model.py:61-94`; the 11→17 correction is the documented sequence, `CNCM_DERIVED_MEMORY_IMPLEMENTATION_v0.6.md:56-59`). RRK v0.1 cannot express this fixture — run 2 simply omits the old fact. |
| Expected answer | 2nd ask AA→BB: `UNKNOWN` (open) / `NO` (closed); ask AA→CC: `YES`. The RETRACT is ACCEPTED (`contract.md:91`). | reuse of a result derived under the first statement is a **stale refusal**, then the refreshed derivation uses 17 (`CNCM_DERIVED_MEMORY_IMPLEMENTATION_v0.6.md:45-47,56-59`) |
| Expected state | `AA\|leads_to\|BB` RETRACTED; `Response.withdrawn` names the formerly standing pid at the RETRACT (`organism.py:685-694`, `contract.md:179-209`) | `memory_statements` holds both statements; new bindings cite the second digest |
| Adapter must preserve | Correction is an ATOMIC `{retracts, asserts}` pair; if CAS-RPU refuses the retract (E-ORG-001/002) the whole correction is rejected, never half-applied. Toward CNCM semantic layer the `previous_digest` link is mandatory. Scalar values are rejected toward CAS-RPU (`E-IX-VALUE`). Any importer that models correction as "assert the new thing" alone FAILS (it would create a CONTRADICTION if polarity differs, `workspace.py:217-225`, or a no-op if same polarity). | |

### F08 — Retraction with a transitive dependent (R-stale) and the recall-escape hazard

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `fact("AA","BB")`; `fact("BB","CC")`; `ask("AA","CC")` → YES (now standing); `retract("BB","CC")`; `ask("AA","CC")` | run 1: facts `leads_to(AA,BB)`, `leads_to(BB,CC)`, query `leads_to(AA,CC)` → CONCLUDED, episode written; run 2 on the SAME `CognitiveMachine`: facts `leads_to(AA,BB)` only (BB→CC omitted = "retracted"), same query |
| Expected answer | 2nd ask: `UNKNOWN` (open) / `NO` (closed); RETRACT ACCEPTED; `withdrawn == ("AA\|leads_to\|CC",)` is **required** (`contract.md:184-203`, R-stale `contract.md:260`) | Expected by MEANING: not supported. Expected by CURRENT CODE `[inference]`: `CONCLUDED` via exact episodic RECALL of `leads_to(AA,CC)@global` (`engine.py:378-416`), because recall matches `conclusion.key` and RECALL counts as authoritative (`semantics.py:78-79`); the warm `memory_recall` fixture has `facts: []` and is documented to recall (`README_HANDOFF.md:108`). |
| Expected state | `BB\|leads_to\|CC` RETRACTED, `AA\|leads_to\|CC` RETRACTED by cascade (`workspace.py:323-327`); heartbeat audit silent (`organism.py:333-360`) | episodic memory still holds the run-1 record (no invalidation path exists in v0.1) |
| Adapter must preserve | An imported RETRACT must reach transitive dependents in the receiver. For CNCM RRK the honest outcome is **REJECT** the retraction (`E-IX-RETRACT-UNSUPPORTED`: receiver cannot invalidate dependents) rather than accept it and let recall answer stale — exactly the directive's stop condition (directive.txt:136). This fixture is the acceptance test for whatever the reuse map proposes for CNCM-side invalidation. | |

### F09 — Rule / recipe storage (explicit vs built-in; associative relation rejected)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | (a) `fact("AA","BB")`; `fact("BB","CC")`; `ask("AA","CC")` — transitivity is implicit. (b) `associate("AA","CC")` (= FACT under `co_occurs`, `events.py:121-123`); `ask("AA","CC")` | (a) packet with `leads_to` `transitive:true` and rule `leads_to_transitive`; (b) envelope `RULE` event with `operation: INFER_MODUS_PONENS` toward CAS-RPU; (c) envelope FACT with `relation: co_occurs` toward CNCM |
| Expected answer | (a) `YES` via `^6`/`^9` (`contract.md:122`). (b) `UNKNOWN`/`NO` — association is not a route (`events.py:122` "`^6` rejects it"); N-gap names `AA\|leads_to\|CC` as a lacuna when a shadow is present (`contract.md:263`) | (a) `CONCLUDED` with a proof step `rule_id: leads_to_transitive` in `dependency_ids`. (b) **REJECTED** `E-IX-RULE-UNSUPPORTED`. (c) **REJECTED** `E-IX-RELATION` (no CNCM counterpart; `^8` not generated, `AUTHORITY_MANIFEST.yaml:132`) |
| Expected state | (a) `AA\|leads_to\|CC` DERIVED with support `("AA\|leads_to\|BB","BB\|leads_to\|CC")` | (a) `branch.proof_steps` contains one `INFER_TRANSITIVE` step; evidence `dependencies` lists the rule id |
| Adapter must preserve | The rule id as a dependency of every derived answer (directive.txt:25,42). Exactly one rule crosses into CAS-RPU; nothing associative crosses into CNCM. | |

### F10 — Lesson promotion (proposed guess → accepted fact, by a new accepted event only)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | `fact("AA","BB")`; `hypothesis("BB","CC")`; `ask("AA","CC")`; then `fact("BB","CC")` (the promotion); `ask("AA","CC")` | run 1: `candidates:[{candidate_id:"guess", assumptions:[leads_to(BB,CC) hypothetical]}]`, facts `leads_to(AA,BB)`, query `leads_to(AA,CC)`; run 2: `leads_to(BB,CC)` as an ASSERTED fact with provenance `{source_type:"cas_rpu", source_id:"<promotion event id>"}` |
| Expected answer | 1st ask: `UNKNOWN` with lacuna `BB\|leads_to\|CC` **required** (H-bridge, `contract.md:261,266-269`; derive refuses hypothesis support `workspace.py:287-292`); closed world: `NO` (`contract.md:139-140`). 2nd ask: `YES`. | run 1: not CONCLUDED on the main branch (hypothetical-only support excluded, `README_HANDOFF.md:271`); run 2: `CONCLUDED` |
| Expected state | after promotion `BB\|leads_to\|CC` status FACT (stronger wins, `workspace.py:241-251`; oracle `hyp.discard`, `contract.md:80-81`) | run-2 fact ASSERTED; the run-1 hypothetical is NOT promoted in place — it is a new asserted record with its own provenance |
| Adapter must preserve | `status:"proposed"` imports as HYPOTHESIS / HYPOTHETICAL and can never be promoted by the importer. Promotion = a NEW `status:"accepted"` event authored by the receiving owner, citing the proposal's `event_id` in `provenance.origin` (directive.txt:111). An adapter that flips the proposal's status field in place FAILS. CNCM apprenticeship receipts (`cognitive_apprenticeship.py:1974-2004`) are carried as `provenance.evidence_ids`, never as an acceptance credential. | |

### F11 — Reload (fresh process; imported record survives through the receiver's OWN replay)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | process 1: `fact("AA","BB")` (local), accepted import of envelope E1 = `leads_to(BB,CC)` from CNCM, `ask("AA","CC")` → YES; persist the accepted event log (mechanism per reuse map); process 2: replay accepted events, then `ask("AA","CC")` | process 1: native/compound machine runs episodes, `save_native_journal` (`native_recovery.py:183-202`); process 2: `replay_native_journal(journal, trusted_genesis, expected_journal_digest)` (`native_recovery.py:110-180`) then query |
| Expected answer | `YES` in process 2 WITHOUT re-teaching; the answer's support trace cites E1's `event_id` and `origin.source_engine == "cncm"` | identical final state hash and trace to process 1 (`native_recovery.py:169-179`); a wrong digest or profile FAILS CLOSED (`:129-134`) |
| Expected state | replay of E1 is idempotent: a second delivery of E1 is a no-op by `event_id` (duplicate intake, directive.txt:62,111) | journal digest equals the retained receipt |
| Adapter must preserve | Reload is the receiver replaying its own accepted stream, which CONTAINS the import as an accepted event. The source engine's journal is never imported (`engine.py:96-101`). `source_state_digest` on E1 lets an audit confirm the imported record against the source after reload. | |

### F12 — Same name, different context (identically named entities must not answer for each other)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | context `ctx1`: `fact("AA","BB")`; context `ctx2`: `ask("AA","BB")` (two `Organism` instances today, `contract.md:224-226`; a namespaced workspace later) | run 1 (`problem_id:"ctx1"`, scope `ctx1`): facts `leads_to(AA,BB)`, query `leads_to(AA,BB)` → CONCLUDED, episode written; run 2 on the same `CognitiveMachine` (`problem_id:"ctx2"`): `facts: []`, query `leads_to(AA,BB)` with scope `ctx2` |
| Expected answer | `UNKNOWN` (open) / `NO` (closed) in `ctx2` | `NEEDS_INFORMATION` — because scope is part of the key (`model.py:291-296`) the run-1 episode key `leads_to(AA,BB)@ctx1` ≠ `leads_to(AA,BB)@ctx2` and recall does not match (`engine.py:382`). **Control variant** (both runs scope `global`): recall WOULD match and answer `CONCLUDED` `[inference]` — this is the failure the fixture exists to catch; it must be run to confirm. |
| Expected state | `ctx2` workspace empty | run-2 branch BLOCKED; episodic memory unchanged |
| Adapter must preserve | Envelope `context_id` is REQUIRED and maps to `Proposition.scope` (CNCM) and to a distinct organism/namespace (CAS-RPU). An envelope with `context_id` missing or equal to `"global"` for a context-bound record is **rejected** (`E-IX-CONTEXT`). Zero cross-context answers is a pass criterion (directive.txt:81). | |

### F13 — Reject-unsupported-rather-than-coerce (negative retract; negated association; guessed association)

| | CAS-RPU | CNCM |
|---|---|---|
| Input | (a) envelope `RETRACT` with `polarity:false` of `AA→CC`; (b) envelope `NEGATION` with `relation:"co_occurs"`; (c) envelope `HYPOTHESIS` with `relation:"co_occurs"` | the same three envelopes toward CNCM |
| Expected answer | (a) **REJECTED** `E-IX-NEG-RETRACT` — the grammar has no negative retract (`contract.md:89-90`); (b),(c) **REJECTED** `E-IX-RELATION` — oracle refuses `E-RS-009` (`revision.py:594-605`, `contract.md:60-64`) and the organism must not record what the oracle cannot score | (a) REJECTED `E-IX-NEG-RETRACT` (semantic RETRACT is value-less and polarity-less, `semantic_model.py:77-83`); (b),(c) REJECTED `E-IX-RELATION` |
| Expected state | unchanged on both sides; the rejection is recorded in the receiver's intake log with the envelope's `event_id` | |
| Adapter must preserve | No silent conversion into "a different question" (directive.txt:36,110). The rejection code and the untouched source representation are returned to the sender. | |

Fixture count: 13 (F01–F13), covering all nine directive-listed concepts plus world mode (F04), conflict locality
(F06), same-name/different-context (F12) and reject-not-coerce (F13).

---

## 3. Interchange envelope

### 3.1 Rules the envelope enforces (from directive.txt:110-111 and §1 above)

1. **Reject, never coerce.** Every enum is closed; unknown or unsupported values fail the whole envelope with a
   named `E-IX-*` code. No defaults for `polarity`, `world_mode`, `status`, `context_id`.
2. **Source representation travels.** `source_representation` is the sender's own serialised record (CAS-RPU
   `Event.canonical()` `events.py:77-84` + the resulting `Proposition` fields; CNCM `Proposition.to_dict()`
   `model.py:343-344` or `SourceStatement.to_dict()`), kept verbatim for audit and round-trip; the receiver never
   interprets it.
3. **Receiving owner validates and accepts.** An envelope is a PROPOSAL to the receiving stream's single writer. The
   receiver re-derives what it can, validates against its own current state version, then either appends its own
   accepted event (whose `provenance.origin` cites the envelope) or rejects. No component writes another component's
   files (directive.txt:111; CNCM analogue: intents through `TransactionCoordinator` only, `AUTHORITY_MANIFEST.yaml:153`;
   CAS-RPU analogue: `Organism.consume` is the only mutator, `organism.py:470-513`).
4. **An imported lesson gets its own accepted event retaining its origin.** `status:"proposed"` never flips in place
   (F10).
5. **Circular replay prevention.** `provenance.origin.hops[]` lists every (engine, stream, event_id) the record has
   passed through; a receiver rejects an envelope whose hops already include its own `(engine, stream_id)`
   (`E-IX-CYCLE`). A re-export of an imported record keeps the full chain.
6. **Duplicate intake prevention.** `event_id` is content-addressed (`sha256` of the canonical envelope body minus
   `event_id`, following CNCM's `content_id` convention, `canonical.py:49-50`); a receiver that has already accepted
   or rejected that `event_id` returns the earlier disposition and changes nothing (directive.txt:62). CNCM's
   coalescing of identical writes (`kernel.py:1679-1685`) is the model.
7. **Contradictory independent writers.** Two envelopes for the same `(context_id, proposition.key)` with opposite
   polarity and both `status:"accepted"` are BOTH accepted as records and the receiver's own conflict machinery decides
   the verdict (CAS-RPU: CONTRADICTED + INADMISSIBLE; CNCM: RECORD_CONTRADICTION + CONFLICT_UNRESOLVED). Never
   last-write-wins (directive.txt:29). Two envelopes with the same `expected_version` racing for one stream: the
   second is rejected `E-IX-STALE` (CNCM precedent `STALE_SNAPSHOT`, `kernel.py:642-646`).
8. **Stale expected version.** `sequence.expected_version` must equal the receiver stream's last committed sequence
   or the envelope is rejected `E-IX-STALE` (explicit serialisation is the receiver's alternative, directive.txt:29).

### 3.2 JSON Schema sketch (`helm.interchange/0.1`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://noetic-compass.local/schemas/helm_interchange_v0_1.json",
  "title": "HELM cross-engine interchange envelope v0.1 (DRAFT)",
  "type": "object", "additionalProperties": false,
  "required": ["schema_version","event_id","source","target","identity","sequence","event_type",
               "status","semantics","proposition","provenance","source_representation"],
  "properties": {
    "schema_version": {"const": "helm.interchange/0.1"},
    "event_id": {"type":"string","pattern":"^ix-[0-9a-f]{16}$",
                 "description":"content_id over the canonical envelope without this field"},
    "source": {"type":"object","additionalProperties":false,"required":["engine","engine_version","schema_version","stream_id"],
      "properties":{
        "engine": {"enum":["cas_rpu","cncm_rrk","cncm_semantic","cncm_compound","cncm_derived","deepseek"]},
        "engine_version": {"type":"string","description":"e.g. cas_rpu: git sha of scripts/cas_rpu; cncm: RUNTIME_VERSION 0.1.0 / 0.4.0 / 0.5.0 / 0.6.0"},
        "schema_version": {"type":"string","description":"source wire version, e.g. cncm.problem/0.1, cncm.semantic-source-statement/0.4, revision_streams_contract_2026_10_06"},
        "stream_id": {"type":"string"}}},
    "target": {"type":"object","additionalProperties":false,"required":["engine","stream_id"],
      "properties":{"engine":{"enum":["cas_rpu","cncm_rrk","cncm_semantic","cncm_compound","cncm_derived","deepseek"]},
                    "stream_id":{"type":"string"}}},
    "identity": {"type":"object","additionalProperties":false,"required":["organism_id","project_id","context_id","branch_id"],
      "properties":{"organism_id":{"type":"string"},"project_id":{"type":"string"},
                    "context_id":{"type":"string","pattern":"^[A-Za-z_][A-Za-z0-9_.:-]*$","not":{"const":"global"}},
                    "branch_id":{"type":"string"}}},
    "sequence": {"type":"object","additionalProperties":false,"required":["source_seq","expected_version"],
      "properties":{"source_seq":{"type":"integer","minimum":0},
                    "expected_version":{"type":"integer","minimum":0,"description":"receiver stream version this envelope expects to extend"}}},
    "event_type": {"enum":["FACT","NEGATION","HYPOTHESIS","RETRACT","CORRECTION","RULE","ASK","ANSWER","PROMOTION"]},
    "status": {"enum":["proposed","accepted"]},
    "semantics": {"type":"object","additionalProperties":false,"required":["world_mode","relation","semantics_version"],
      "properties":{"world_mode":{"enum":["open","closed"]},
                    "relation":{"enum":["leads_to","co_occurs"]},
                    "semantics_version":{"type":"string","description":"verdict/contract version, e.g. revision_streams_contract_2026_10_06 §3"}}},
    "proposition": {"type":"object","additionalProperties":false,"required":["predicate","arguments","polarity"],
      "properties":{"predicate":{"type":"string","pattern":"^(?!not|neg|~|¬|!)[A-Za-z_][A-Za-z0-9_.:-]*$"},
                    "arguments":{"type":"array","minItems":2,"maxItems":2,"items":{"type":"string","pattern":"^[A-Za-z][A-Za-z0-9_-]*$"}},
                    "polarity":{"type":"boolean"},
                    "value":{"type":"string","description":"canonical rational; present only for cncm_semantic/derived; rejected by cas_rpu adapters (E-IX-VALUE)"}}},
    "correction": {"type":"object","additionalProperties":false,"required":["retracts_event_id","supersedes"],
      "properties":{"retracts_event_id":{"type":"string"},"supersedes":{"type":"string","description":"source-side digest or event id of the superseded record"}}},
    "rule": {"type":"object","additionalProperties":false,"required":["rule_id","operation","antecedents","consequent","version"],
      "properties":{"rule_id":{"type":"string"},"operation":{"enum":["INFER_TRANSITIVE","INFER_MODUS_PONENS"]},
                    "antecedents":{"type":"array","items":{"$ref":"#/properties/proposition"}},
                    "consequent":{"$ref":"#/properties/proposition"},"version":{"type":"string"}}},
    "answer": {"type":"object","additionalProperties":false,"required":["verdict","engine_terminal","state_version","dependency_ids"],
      "properties":{"verdict":{"enum":["YES","NO","UNKNOWN","INADMISSIBLE"]},
                    "engine_terminal":{"type":"string","description":"source engine's own terminal, e.g. CONCLUDED/NEEDS_INFORMATION/CONFLICT_UNRESOLVED/INADMISSIBLE"},
                    "lacunae":{"type":"array","items":{"$ref":"#/properties/proposition"}},
                    "contested":{"type":"array","items":{"$ref":"#/properties/proposition"}},
                    "state_version":{"type":"integer"},
                    "dependency_ids":{"type":"array","items":{"type":"string"},"description":"event ids, rule ids, world_mode binding, semantics_version"}}},
    "provenance": {"type":"object","additionalProperties":false,"required":["origin","evidence_ids","dependency_ids","source_state_digest"],
      "properties":{
        "origin":{"type":"object","additionalProperties":false,"required":["hops"],
          "properties":{"hops":{"type":"array","minItems":1,"items":{"type":"object","additionalProperties":false,
            "required":["engine","stream_id","event_id"],
            "properties":{"engine":{"type":"string"},"stream_id":{"type":"string"},"event_id":{"type":"string"},
                          "receipt_ids":{"type":"array","items":{"type":"string"}}}}}}},
        "evidence_ids":{"type":"array","items":{"type":"string"}},
        "dependency_ids":{"type":"array","items":{"type":"string"}},
        "source_state_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"}}},
    "source_representation": {"type":"object","description":"sender's verbatim serialised record; opaque to the receiver; kept for audit and round-trip"}
  },
  "allOf": [
    {"if":{"properties":{"event_type":{"const":"CORRECTION"}}},"then":{"required":["correction"]}},
    {"if":{"properties":{"event_type":{"const":"RULE"}}},"then":{"required":["rule"]}},
    {"if":{"properties":{"event_type":{"const":"ANSWER"}}},"then":{"required":["answer"]}},
    {"if":{"properties":{"event_type":{"enum":["HYPOTHESIS","NEGATION","ASK"]}}},
     "then":{"properties":{"semantics":{"properties":{"relation":{"const":"leads_to"}}}}}},
    {"if":{"properties":{"event_type":{"const":"RETRACT"}}},
     "then":{"properties":{"proposition":{"properties":{"polarity":{"const":true}}}}}},
    {"if":{"properties":{"event_type":{"const":"PROMOTION"}}},
     "then":{"properties":{"status":{"const":"accepted"}},"required":["correction"],
             "description":"PROMOTION reuses correction.retracts_event_id to name the proposal being superseded by acceptance"}}
  ]
}
```

Rejection codes (closed list for v0.1): `E-IX-SCHEMA`, `E-IX-WORLD`, `E-IX-RELATION`, `E-IX-VALUE`,
`E-IX-NEG-PREDICATE`, `E-IX-NEG-RETRACT`, `E-IX-RULE-UNSUPPORTED`, `E-IX-CONTEXT`, `E-IX-STALE`, `E-IX-DUP`
(returns prior disposition), `E-IX-CYCLE`, `E-IX-CORRECTION-REFUSED`, `E-IX-RETRACT-UNSUPPORTED`,
`E-IX-TARGET-OWNER` (envelope addressed to a stream the receiver does not own).

### 3.3 Worked example A — an imported FACT (CNCM → CAS-RPU)

CNCM semantic/RRK side has an asserted fact `leads_to(BB,CC)@ctx_helm_a` from a committed run; Codex's adapter emits:

```json
{ "schema_version":"helm.interchange/0.1",
  "event_id":"ix-3f9a1c2e7b4d6a08",
  "source":{"engine":"cncm_rrk","engine_version":"0.1.0","schema_version":"cncm.problem/0.1","stream_id":"cncm-run-b331da8cd5303c42"},
  "target":{"engine":"cas_rpu","stream_id":"rpu-org-7-ctx_helm_a"},
  "identity":{"organism_id":"rpu-org-7","project_id":"helm","context_id":"ctx_helm_a","branch_id":"main"},
  "sequence":{"source_seq":12,"expected_version":41},
  "event_type":"FACT","status":"accepted",
  "semantics":{"world_mode":"open","relation":"leads_to","semantics_version":"revision_streams_contract_2026_10_06"},
  "proposition":{"predicate":"leads_to","arguments":["BB","CC"],"polarity":true},
  "provenance":{
    "origin":{"hops":[{"engine":"cncm_rrk","stream_id":"cncm-run-b331da8cd5303c42","event_id":"intent-6a9107e3143496c1"}]},
    "evidence_ids":["run-b331da8cd5303c42"],
    "dependency_ids":[],
    "source_state_digest":"3933360265307e1461e8bae7b2726d57ec8133e248edaedf66ee8a2a1e0119e1"},
  "source_representation":{"predicate":"leads_to","arguments":["BB","CC"],"polarity":true,"evidence_status":"asserted",
                           "provenance":[{"source_type":"fixture","source_id":"bb_cc","detail":""}],"scope":"ctx_helm_a"} }
```

Receiver (CAS-RPU stream owner for `ctx_helm_a`) processing:
1. Validates schema; `world_mode:open` matches the organism's `closed_world=False`; `relation:leads_to` OK; `polarity`
   present; `context_id` matches the stream; `expected_version 41` equals last committed → proceed.
2. Duplicate check on `event_id` → none. Cycle check: no hop is `(cas_rpu, rpu-org-7-ctx_helm_a)` → proceed.
3. Appends ITS OWN accepted event `rpu-ev-0042 = events.fact("BB","CC")` with `provenance.origin.hops` extended by
   `{engine:"cas_rpu", stream_id:"rpu-org-7-ctx_helm_a", event_id:"rpu-ev-0042"}`, and stores the envelope verbatim.
4. `Organism.consume(fact("BB","CC"))` → `Response.accepted=True`, note "given as fact" (`organism.py:520-531`); wants
   closed by this fact may trigger a self re-ask (`organism.py:525-526`).
5. Round-trip check: re-encode `props["BB|leads_to|CC"]` → `{predicate:"leads_to", arguments:["BB","CC"], polarity:true}`
   equals the envelope's `proposition` → PASS. The CNCM provenance list is retained only inside `source_representation`.

Expected behaviour change (the directive's "changes a later answer", directive.txt:8): if `AA→BB` was already given,
`ask("AA","CC")` now returns `YES` with support `("AA|leads_to|BB","BB|leads_to|CC")`; the answer record's
`dependency_ids` includes `rpu-ev-0042` and, through it, `ix-3f9a1c2e7b4d6a08`.

### 3.4 Worked example B — an imported PROPOSED lesson, later promoted (CAS-RPU → CNCM, then CNCM owner accepts)

Step 1 — CAS-RPU exports a guess it holds as HYPOTHESIS (`organism.py:533-542`):

```json
{ "schema_version":"helm.interchange/0.1","event_id":"ix-8c21d4e09f7a3b55",
  "source":{"engine":"cas_rpu","engine_version":"8d8035cf","schema_version":"revision_streams_contract_2026_10_06","stream_id":"rpu-org-7-ctx_helm_a"},
  "target":{"engine":"cncm_rrk","stream_id":"cncm-machine-helm-a"},
  "identity":{"organism_id":"rpu-org-7","project_id":"helm","context_id":"ctx_helm_a","branch_id":"guess-1"},
  "sequence":{"source_seq":57,"expected_version":9},
  "event_type":"HYPOTHESIS","status":"proposed",
  "semantics":{"world_mode":"open","relation":"leads_to","semantics_version":"revision_streams_contract_2026_10_06"},
  "proposition":{"predicate":"leads_to","arguments":["CC","DD"],"polarity":true},
  "provenance":{"origin":{"hops":[{"engine":"cas_rpu","stream_id":"rpu-org-7-ctx_helm_a","event_id":"rpu-ev-0057"}]},
                "evidence_ids":[],"dependency_ids":[],
                "source_state_digest":"<sha256 of the organism's accepted-event log at seq 57>"},
  "source_representation":{"kind":"hypothesis","subject":"CC","relation":"leads_to","obj":"DD",
                           "proposition":{"negated":false,"status":"hypothesis","stage":"stream","support":[]}} }
```

CNCM owner intake: validates; cannot be placed in a packet's `facts` (schema requires `asserted`,
`problem_packet.schema.json:99-115`); places it as a candidate ASSUMPTION `evidence_status: hypothetical` with
provenance `{source_type:"cas_rpu", source_id:"rpu-ev-0057"}` (`problem_packet.schema.json:116-131` hypothetical
shape), scope `ctx_helm_a`. Expected: queries that need `leads_to(CC,DD)` are NOT concluded on the main branch
(hypothetical-only support excluded, `README_HANDOFF.md:271`). The envelope is recorded with disposition
`ACCEPTED_AS_PROPOSED`. Nothing is promoted.

Step 2 — later, the CNCM owner obtains independent support (e.g. its own asserted source, or an apprenticeship
qualification + retention receipt pair `cognitive_apprenticeship.py:2084-2117`) and authors a NEW accepted event:

```json
{ "schema_version":"helm.interchange/0.1","event_id":"ix-b7e0c35a9d12f846",
  "source":{"engine":"cncm_rrk","engine_version":"0.1.0","schema_version":"cncm.problem/0.1","stream_id":"cncm-machine-helm-a"},
  "target":{"engine":"cncm_rrk","stream_id":"cncm-machine-helm-a"},
  "identity":{"organism_id":"cncm-machine-helm-a","project_id":"helm","context_id":"ctx_helm_a","branch_id":"main"},
  "sequence":{"source_seq":10,"expected_version":10},
  "event_type":"PROMOTION","status":"accepted",
  "semantics":{"world_mode":"open","relation":"leads_to","semantics_version":"revision_streams_contract_2026_10_06"},
  "proposition":{"predicate":"leads_to","arguments":["CC","DD"],"polarity":true},
  "correction":{"retracts_event_id":"ix-8c21d4e09f7a3b55","supersedes":"rpu-ev-0057"},
  "provenance":{"origin":{"hops":[
       {"engine":"cas_rpu","stream_id":"rpu-org-7-ctx_helm_a","event_id":"rpu-ev-0057"},
       {"engine":"cncm_rrk","stream_id":"cncm-machine-helm-a","event_id":"ix-b7e0c35a9d12f846",
        "receipt_ids":["ccb-t1-qualification-<id>","ccb-t1-retention-<id>"]}]},
                "evidence_ids":["<source statement digest or run id>"],"dependency_ids":["ix-8c21d4e09f7a3b55"],
                "source_state_digest":"<cncm state_hash after acceptance>"},
  "source_representation":{"predicate":"leads_to","arguments":["CC","DD"],"polarity":true,"evidence_status":"asserted",
                           "provenance":[{"source_type":"cas_rpu","source_id":"rpu-ev-0057","detail":"promoted by cncm owner"}],"scope":"ctx_helm_a"} }
```

Expected after step 2: CNCM queries needing `leads_to(CC,DD)` now CONCLUDE on the main branch; the asserted record's
provenance retains `cas_rpu / rpu-ev-0057` (origin retained, directive.txt:111). If this promotion is later exported
back to CAS-RPU, the cycle check sees hop `(cas_rpu, rpu-org-7-ctx_helm_a)` already present → the CAS-RPU owner
treats it as a PROMOTION of its own `rpu-ev-0057`, not as a fresh fact: it emits `fact("CC","DD")` (stronger status
wins over the hypothesis, `workspace.py:241-251`) and records the CNCM receipts in provenance. A second delivery of
`ix-b7e0c35a9d12f846` is `E-IX-DUP` and changes nothing. Retraction of the promoted premise later (`retract("CC","DD")`
on the CAS-RPU side, or a CNCM semantic RETRACT) invalidates conclusions like any other dependency (directive.txt:45).

---

## 4. Ownership and custody — PROPOSED, not accepted

Per directive.txt:102-107, these are proposals. "No current DeepSeek lead or session has been verified, and no
DeepSeek message or agreement has been obtained" (directive.txt:103). Nothing here is a commitment.

| Role | PROPOSED owner | Owns (single writer) | Does not own |
|---|---|---|---|
| CAS-RPU organism stream(s) | Claude | accepted event log per `(organism_id, context_id)`; the CAS-RPU adapter's intake validation; PR 248 compatibility (`directive.txt:104`) | any CNCM file; any DeepSeek branch |
| CNCM integration | Codex | intake through the frozen home-base entrypoint and existing adapters; the one canonical RPA implementation (link, not copy, `directive.txt:105`); CNCM-side envelope validation | CAS-RPU workspace; `research/` repositories (kept separate) |
| DeepSeek | DeepSeek (unverified) | its own source review of lesson, repair and reload semantics; its protected branch (`directive.txt:106`) | adopting Codex's interpretation before its own review |
| Evaluation custody | an independent custodian, to be named before the scored run (`directive.txt:107`) | final seeds and expected answers until the frozen code is committed | implementation |

**Verified-route requirement before dispatch.** Ownership is established only through a verified project-manager
route; an old inbox that could start an unbounded paid run must not be used (directive.txt:103). Until that route has
confirmed each owner, every envelope with `target.engine: "deepseek"` is held (not sent), and no envelope from
`source.engine: "deepseek"` is accepted (`E-IX-TARGET-OWNER`). The `$250` ceiling / `$97.59` ledger and AWS-only
rules (directive.txt:16) are unchanged by this draft.

**What the frozen CNCM home-base entrypoint v0.1 is.** From what is present in the checkout:
- The package entrypoint is `python -m cncm` (`CNCM/cncm/__main__.py:1-4` → `cli.main`), whose parser is
  `prog="cncm", description="CAS Native Cognitive Machine v0.1 reference kernel"` with subcommands `check`, `run`,
  `replay`, `verify`, `demo` (`CNCM/cncm/cli.py:29-52`); the handoff's run commands use exactly this
  (`CNCM/README_HANDOFF.md:59,82-90`).
- The host-facing API is `cncm/api.py` ("Stable host-facing API for the v0.1 reference implementation", `api.py:1`,
  `KernelSession` keeps state ownership inside the kernel, `api.py:32-33`).
- Frozen wire versions and the sole-writer model are fixed in `CNCM/AUTHORITY_MANIFEST.yaml:61-87,149-170`; the
  "Frozen boundaries" list is `CNCM/README_HANDOFF.md:261-283` (schemas `cncm.problem/0.1`, `cncm.evidence/0.1`,
  runtime `0.1.0`; only working-state changes and a committed episodic write are admitted, `:276`).
- The reconciliation documents the directive cites for this freeze ([3]) are NOT present `[unverified]`; the
  statement "frozen at v0.1" is taken from the directive and is consistent with the artifacts above.

**Why it must not be bypassed.** (1) Every admitted state change passes the `TransactionCoordinator`'s authority,
tick and `state_hash` checks (`kernel.py:617-648`); writing state any other way defeats the single-writer guarantee
the directive requires (directive.txt:29,111). (2) Episodic import is prohibited by construction
(`engine.py:96-101`, `AUTHORITY_MANIFEST.yaml:166`): a "shortcut" that injects records would be exactly the
unauthenticated import the handoff rules out (`README_HANDOFF.md:126`). (3) Recovery validity depends on replaying
through the same coordinator against a caller-trusted genesis and digest (`native_recovery.py:110-134`); a bypass
produces state that no replay can reconstruct, so the directive's restore sequence (directive.txt:58-59) could not be
verified. (4) Preserving the frozen boundary is what keeps CNCM, nested vision-next and DeepSeek "not yet
interchangeable implementations" honest (directive.txt:101) — an interchange envelope presented through the entrypoint
is a proposal the owner can validate; a write around it is a meaning change the stop conditions forbid
(directive.txt:137).

---

## 5. Open questions for the owners

1. **ASK polarity (Claude).** CAS-RPU `ask` has no polarity (`events.py:117-118`). Should the contract be extended
   with a negative ASK ("is ¬P held?") so CNCM negative queries can be imported, or should the adapter reject them
   permanently? Extension would be a versioned contract change, not a fork (directive.txt:16).
2. **Conflict locality (Codex).** Does CNCM intend `CONFLICT_UNRESOLVED` to remain branch-global (`engine.py:176,211`)?
   If so, F06 is a permanent, documented divergence and the envelope must never translate it. If a route-local
   contradiction notion is planned, which version introduces it?
3. **Hypothetical vs asserted conflict (Codex).** `detect_contradictions` ignores `evidence_status`
   (`semantics.py:116-120`). Do candidate `assumptions` ever enter `branch.propositions` such that a HYPOTHETICAL
   can contradict an ASSERTED fact? `[inference pending; BranchFrame keeps them in separate fields, model.py:867-868]`
   CAS-RPU treats that case as refutation, not contradiction (`workspace.py:231-239`).
4. **Episodic recall without premise re-check (Codex).** `_recall_exact_episode` matches on `conclusion.key` alone
   (`engine.py:378-385`). Is the F08 behaviour (recall of a conclusion whose premise is absent from the current
   packet) intended? If yes, the CNCM adapter must reject imported retractions (`E-IX-RETRACT-UNSUPPORTED`) until a
   dependency-aware invalidation exists; this belongs to the reuse-map audit.
5. **Scope as context (Codex, Claude).** Is `Proposition.scope` the right carrier for `context_id` on the CNCM side,
   given the schema requires an identifier (`proposition.schema.json:27-32`) and recall keys include it
   (`model.py:291-296`)? On the CAS-RPU side, is "one Organism per context" acceptable for the first run, or is a
   workspace namespace required before the multi-session suite (directive.txt:77)?
6. **Assumption scope (Claude).** Assumptions count as ASSERTIVE (`workspace.py:61`); the directive requires explicit
   context scope before multi-session reuse (directive.txt:30). Is `branch_id ≠ main` in the envelope sufficient, or
   does the workspace need a per-proposition context field?
7. **Values (Codex).** CNCM semantic/derived records carry rational values (`semantic_model.py:81`,
   `derived_model.py`); CAS-RPU has none. Confirm `E-IX-VALUE` rejection toward CAS-RPU is acceptable, or define a
   value-bearing relation in a later contract version.
8. **Association (Codex).** `co_occurs` has no CNCM counterpart and `^8` is not generated by the runtime
   (`AUTHORITY_MANIFEST.yaml:132`). Confirm permanent rejection, or name the CNCM version that would admit an
   associative proposition without granting it truth.
9. **DeepSeek semantics (DeepSeek, via verified route).** Where does DeepSeek represent negation (flag or predicate),
   unknown, conflict, correction, retraction, rules, lesson promotion and reload? Its reported reload test was
   same-process (directive.txt:113); which fixtures (F07, F08, F11) can it run in a fresh process? All DeepSeek rows in
   this draft are `[unverified]`.
10. **Reconciliation documents (Codex).** Please supply or link `CNCM_WORKSTREAM_RECONCILIATION_20261006.md` and
    `CNCM_NEXT_BEHAVIOR_EXPERIMENT_20261006.md` so the "frozen v0.1 entrypoint" statement in §4 can be cited from the
    source rather than from the directive.
11. **Lacuna comparison (Claude, Codex).** CAS-RPU scores lacunae by set bounds (`contract.md:160-163`); CNCM reports
    all unknown antecedent keys. Should the envelope's `answer.lacunae` be scored at all across engines, or carried
    for explanation only?
12. **Promotion evidence (Codex).** Are CCB-T1/CCB-L1 receipts (`cognitive_apprenticeship.py:2084-2117`) acceptable as
    `provenance.evidence_ids` on a PROMOTION envelope, given they are "local evidence artifacts ... not CAS-RRK
    authorization" (`README_HANDOFF.md:279`)? If not, what independent support may a CNCM owner cite when promoting an
    imported proposal?
13. **Idempotency key (both).** `event_id` as a content id excludes `sequence.expected_version`? If the version is
    inside the hash, a legitimately retried envelope after `E-IX-STALE` gets a new id and the duplicate check cannot
    see it; if outside, two different intended versions collide. Proposed: hash excludes `sequence` and includes a
    sender-supplied `intent_nonce`; owners to confirm.
