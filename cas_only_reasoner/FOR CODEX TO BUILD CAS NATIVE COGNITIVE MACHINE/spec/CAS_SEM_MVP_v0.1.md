# CAS-Sem MVP v0.1

Status: normative description of the implemented symbolic subset

CAS-Sem MVP is a small typed Horn-rule system over caller-supplied symbols. It is not English semantics, full CAS/TKS semantics, general mathematics, causal reasoning, or a world model.

## 1. Declarations and identifiers

Identifiers match `^[A-Za-z_][A-Za-z0-9_.:-]*$`. A problem declares:

- entities as `(entity_id, entity_type)`;
- predicates as `(predicate_id, argument_types, transitive)`;
- propositions and rules using only those declarations.

Predicate arity and every ground entity type must match. Rule variables begin with `?`, are local to one rule, must have consistent declared types, and every consequent variable must occur in an antecedent. There are no numeric literals, side conditions, confidence scores, or imported facts in the semantic layer.

## 2. Proposition identity

A proposition has exactly:

- `predicate`;
- nonempty ordered string `arguments`;
- Boolean `polarity`;
- `evidence_status`;
- ordered provenance entries;
- a symbolic `scope` string.

It has no separate proposition ID or truth-status field. Its semantic atom key is `predicate(arg1,...,argN)@scope`; the negative semantic key prepends `not:`. Equality for support is exact semantic-key presence.

Evidence status is one of the lowercase values `asserted`, `derived`, `hypothetical`, `contradicted`, or `unknown`. This field records origin/disposition; v0.1 does not implement a general evidence ordering.

## 3. Input evidence

Top-level facts, candidate facts, and RPM-resolver facts must be `asserted` and carry provenance. Candidate assumptions must be `hypothetical` and carry provenance. Rules and resolver rules must carry provenance.

The rule model has no `VERIFIED`/`PROVISIONAL` authority field. A structurally valid rule in the typed packet is admitted for this demonstrator. Therefore packet construction and provenance validation are part of the trust boundary; v0.1 does not independently authenticate a rule source.

## 4. Open-world support and contradiction

The runtime is open-world: lack of a semantic key does not establish its opposite. If the query key is absent after bounded reasoning, the result is normally `NEEDS_INFORMATION` with structural lacunae.

A contradiction exists when both polarities of the same predicate, arguments, and scope are present. The atom key is recorded in the branch. There is no explosion rule; arbitrary propositions cannot follow from contradiction. A branch with a recorded contradiction is classified `CONTRADICTED` and cannot commit.

## 5. Rule operators

Only two operations are valid in a `Rule`:

### `INFER_MODUS_PONENS`

Antecedents are matched in stable order against branch propositions. Variable bindings must unify exactly across all antecedents. The consequent is instantiated with that same complete binding. The derived proposition receives `derived` status and provenance containing the rule ID plus declared rule provenance.

### `INFER_TRANSITIVE`

Input validation requires one binary predicate declared `transitive`, the same type on both positions, exactly two antecedents, and the structural pattern `r(?x,?y), r(?y,?z) -> r(?x,?z)` with three distinct variables. Runtime application then uses the same exact unifier as modus ponens.

No negation-as-failure, contraposition, probabilistic rule, default rule, reverse implication, implicit transitivity, or unstated operator is admitted.

## 6. Exact proof reconstruction

`applicable_proofs` performs iterative antecedent matching in deterministic rule/proposition/substitution/content-ID order. It returns at most one canonical next proof per call and aborts after 4,096 fact-pattern match expansions. Exhaustion is a typed budget disposition, not proof absence. An incoming ordinary inference proof is accepted only if its full serialized form equals the recomputed next candidate, including:

- operation;
- sorted premise keys;
- rule ID;
- conclusion, evidence status, scope, and provenance;
- sorted substitution pairs;
- branch ID;
- `verified: true`;
- proof provenance.

The `verified` Boolean is never sufficient by itself. Recall and RPM child results use separate source-specific reconstruction in the kernel. Alternate proofs of one conclusion may be retained only until an authoritative support path exists; asserted roots are preserved and exact duplicate steps are suppressed.

## 7. Recall

Exact recall searches the supplied episodic snapshot for the first sorted record where `verified` is true and `episode.conclusion.key == query.key`. It does not require the same problem or goal ID. The recalled conclusion becomes `derived` with provenance pointing to that episode, and the kernel checks that the record exists in the installed snapshot.

The admitted public path learns and recalls records inside one persistent `CognitiveMachine`. Public nonempty memory injection is rejected. Engine replay passes the exact snapshot retained by its supplied `RunResult` into a private trusted-host path. That underscore method trusts its same-process caller and does not authenticate snapshot ownership. No durable restore/import API or authenticator exists, and `verified=True` is not a public import credential.

This is exact semantic-key recall only. There is no similarity search, associative retrieval, decay, forgetting category, semantic-memory store, or procedural-memory store.

## 8. Decomposition (`^6`)

`decompose_query` is a pure deterministic function. If the query has authoritative support, it records the asserted query or one canonical authoritative supporting proof, assumptions, contradictions, and the query as predicted effect. A hypothetical-only query or proof chain does not resolve decomposition. Otherwise the function unifies rule consequents with the query and records candidate antecedent keys, rule dependencies, unbound terms, missing keys, contradictions, required prerequisites, and predicted effects.

The kernel accepts a decomposition only when every emitted field exactly equals recomputation from the current branch, query, and rules.

## 9. Association (`^8`) and conclusion (`^9`)

`^8` means surfacing candidates without conferring truth, but the v0.1 runtime contains no native candidate generator. Candidate facts, assumptions, and constraints arrive in declared `CandidateSpec` objects. `ASSOCIATE` remains an enum value, not an accepted derivation operation.

`^9` is realized only by a verified proof conclusion or an exactly reconstructed recall/RPM result. There is no separate noetic-coordinate field in the packet, proof, intent, or state.

## 10. Authoritative support and hypotheses

Candidate assumptions are copied into branch propositions with `hypothetical` status and may participate in mechanical Horn matching. They do not by themselves grant authoritative support. The authoritative-support graph is traversed iteratively:

- an asserted root is authoritative;
- a verified `RECALL` or `RPM_CHILD_RESULT` root is authoritative only after its source-specific reconstruction succeeds;
- an ordinary verified proof conclusion is authoritative only when every referenced premise is authoritative;
- a hypothetical-only query, constraint, or support chain is excluded.

Classification, comparison, commitment gates, and final decomposition use this authoritative relation, not mere key presence. v0.1 does not define a general conditional-conclusion logic or graded evidence calculus.

## 11. RPM child semantics

An RPM resolver is a separately declared target, asserted fact set, and optional rule set. The child computes bounded canonical closure over only that resolver and stops at the exact target-producing prefix. If the target appears, it is wrapped as a `derived` `RPM_CHILD_RESULT` with a deterministic opaque resolver provenance ID. Kernel acceptance re-runs the same resolver and requires the complete proof object and inference cost to match. If the configured step bound truncates closure before target absence is established, the outcome is budget exhaustion. The high-level engine attempts missing prerequisites sequentially.

This is typed missing-premise resolution. It is not D/W/P sufficiency or Foundation reasoning.

## 12. Query disposition

- An authoritatively supported query on an admissible branch can proceed to comparison and commitment.
- Explicit complementary support prevents commitment and normally yields `CONFLICT_UNRESOLVED`.
- Missing rule premises normally yield `NEEDS_INFORMATION`.
- A genuine declared RPM failure is exactly `NEEDS_INFORMATION` with canonical detail; `NEEDS_CAPABILITY` is unavailable to components.
- Invalid inputs fail parsing. Rejected runtime intents remain trace-visible. Only the coordinator's last-tick fail-safe can emit `FAULT`; components cannot self-certify it.

## 13. Semantic non-claims

This subset does not establish natural-language meaning, common sense, causal sufficiency, ethical value, empirical truth, probabilities, or complete CAS/TKS semantics. Foundation and D/W/P meanings remain `OPEN-SEMANTICS`. Drive/Foundation desirability and comparison rank cannot validate a proof.
