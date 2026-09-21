# Agreement and disagreement ledger
## ChatGPT, Claude, and the decision Fable should implement

**Prepared:** 2026-09-21. **Status:** source-grounded comparison plus explicit engineering decisions; not an independent checkout audit. Source identifiers refer to `sources/SOURCE_MAP.md`.

The latest Claude addendum changes its original rejection of component-matching. It accepts a behavioral test against an executable CAS operation, a controlled intermediate intervention, matched comparison arms, explicit bindings, and behavior-paired synthetic data. These are genuine areas of agreement. Do not continue quoting the earlier NOT LICENSED paragraph as though the addendum did not revise it. [S1 addendum]

The original output-only prohibition and several causal interpretations remain disputed. This ledger does not claim Claude accepted corrections introduced after its pasted response.

## Agreements now explicit

| ID | Shared position | Implementation consequence |
|---|---|---|
| A01 | Elements organize content; component contracts organize transformations. | Maintain typed expression content separately from parameterized operators. |
| A02 | Individual floating-point weights need not have a unique readable CAS meaning. | Attribute behavior to a declared module and its tested contract, not to a name on a scalar. |
| A03 | CAS-Native has reusable components, but those components are not already integrated into Helm. | Reuse audited resources through explicit adapters; keep model/run identities distinct. |
| A04 | A learned operation can be scored against a specified CAS reference. | Implement operation-specific consistency and error-domain tests. |
| A05 | A decoder or label alone is not enough for the stronger claim. Claude adopts the intervention test. | Correct an intermediate binding without supplying the answer, and evaluate downstream behavior. |
| A06 | Exact roles and bindings matter; a profile does not preserve everything. | Preserve operand roles, order, relations, context, and the original problem identity. |
| A07 | Compare conventional, CAS-heads-only, and CAS-computation arms. | Match information, capacity, data exposure, and tuning budgets; report residual differences. |
| A08 | Behavior-paired SDG is useful. | Record inputs, operations, prerequisites, outcomes, and negative cases with independent checks. |
| A09 | Syntax-only PCBA constructs are not executable semantics. | Start with a verified subset; introduce boards after parser and contracts are frozen. |
| A10 | A shuffle control can be vacuous; ontologies must be versioned. | Test that a semantic corruption can affect the reference, and keep all three 28-way namespaces separate. |

A01-A10 are grounded in the latest addendum and surrounding review. They do not establish that any new experiment passed. [S1 lines 270-343 in the supplied review]

## Remaining disagreements and how to resolve them

### D01. CAS input versus leaked answers

**Claude's position:** CAS belongs in the output and registry, never in inputs; existing Helm analogy can exploit type equality. The review identifies a real substring-label example but labels the universal compiler-ceiling claim as argued, not run. [S1 §§The one-paragraph answer; What the evidence kills; Claim states]

**My position:** the shortcut invalidates that particular task as evidence of the intended skill, not every structured input design. A problem expressed in CAS is not necessarily its answer. A native predicted CAS intermediate representation is another legitimate experimental design.

**Decision:** preserve the existing frozen input policy. In a new versioned experimental task, permit answer-free typed descriptions. Prohibit target labels, oracle-derived outcomes, and hidden solution methods from the model-visible packet. Compare against type-equality, substring, and exact symbolic baselines. Do not make CAS input a performance claim before testing it.

### D02. The SDG runs in the other direction

**Agreement:** the documented generator starts with CAS structure and emits English; it is not a native general inverse translator. [S1 §§The SDG runs the other way]

**My refinement:** paired CAS-to-English examples can train a separate English-to-CAS learner. The target is allowed in supervised training, not as an inference input for the same prediction. That does not turn a foreign model's proposed interpretation into ground truth.

**Decision:** use deterministic/source-checked generation first. Put gold expressions and intermediate answers in a separate target channel. Keep natural-language interpretation outside the first algebra-only critical path. Add it later as a distinct experiment with ambiguity handling and unseen templates.

### D03. Vector closure and expression validity

**Claude's concern:** arbitrary vector sums/scalings remain vectors, whereas some CAS expressions are invalid. [S1 §What the evidence kills, item 1]

**My position:** an encoder can map legal expressions into a subset of a vector space, and a decoder can reject other points. The subset need not be closed under arbitrary arithmetic. This does not imply that a finite-precision fixed vector can losslessly store arbitrary-length expressions.

**Decision:** compare a bounded strict bottleneck with an order-preserving sequence/tree representation. Variable-sized structured memory is the preferred integration option. Keep legal syntax, semantic validity, and latent geometry separate. Published grammar-latent work is a precedent, not validation of CAS. [E2]

### D04. Fixed algebra versus learned modules

**Claude's combined sequence:** make algebra fixed inside the model, then train modules to match the executable operations. [S1 §§Fix, never learn; combined plan]

**My refinement:** those are two different execution paths. A learned candidate cannot obtain its answer by calling the fixed reference and then receive credit for learning.

**Decision:** freeze the reference interpreter outside neural prediction. Train the candidate against its labels. Keep a separate, useful fixed-symbolic/hybrid product arm and label its contribution. Discover whether RegisterFiLM has trainable parameters; a parameterized transform is not a universally fixed algebraic oracle. A registry alone is not an operation.

### D05. Which project receives the first experiment?

**Claude's suggestion:** start where the executable semantics already live, with the owner choosing CAS-Native or Helm.

**Decision in this directive:** first build a standalone CAS Expression Lab using audited engine/CAS-Native resources. Finish the real Helm baseline in parallel. Helm remains the intended integration target. This avoids choosing between a stale transformer integration and an unready pointer interface. It is an implementation choice for the handoff, not a claim that the repositories are already connected.

### D06. Dataset ordering

**Claude's combined sequence:** consistency/intervention work precedes behavior-paired SDG. [S1 combined plan]

**My position:** define the task, oracle, behavior records, and held-out splits before training and intervention evaluation. Otherwise the experiment can drift toward what the candidate happened to learn.

**Decision:** contracts and behavior-paired data precede module training. Add more generation features later as versioned extensions, not after inspecting the final evaluation.

### D07. Recurrence is a defect, not a complete causal diagnosis

**Agreement:** the report identifies neighborhood messages computed from frozen input instead of updated node state. Fixing that is an important mechanism repair. [S3 §1]

**Disagreement:** identical messages do not imply every hidden state is identical. The reported recurrence still changes its local state. Global pooling and heads also exist; the local two-hop test is not a proof that every whole-model output has only one-hop information. A falling gradient does not prove that all further training is useless. [S3 §§1-3]

**Decision:** verify the local repair, then measure whole-model behavior using controlled ablations. Do not require agreement with a sole-cause explanation. More rounds, wider networks, and schedules remain hypotheses, not guaranteed gains.

### D08. Sinkhorn is not a discrete assignment guarantee

**Claude's original framing:** a few normalizations make one-to-one correspondence an output property. [S3 F2; S2 matching details]

**My refinement:** Sinkhorn is a continuous matching relaxation. Even an exactly doubly stochastic matrix can produce repeated target selections under independent row argmax. [E3]

For example, rows of [[0.40,0.35,0.25], [0.45,0.30,0.25], [0.15,0.35,0.50]] and columns all sum to one, but the first two row maxima select the same column. This is direct arithmetic, not a Helm result.

**Decision:** specify the actual task's complete/partial matching rules and jointly decode or validate accordingly. Independent pair scores can represent a correct set of preferences; they simply do not enforce the joint constraints by themselves. Report soft scores and decoded assignments separately.

### D09. Baselines need not be at chance for useful tasks

**Claude's proposal:** require a one-hop/literal baseline at chance on new board questions. [S1 §PCBA boards]

**My position:** direct port lookup should be easy for an exact typed parser. That can validate an interface without proving advanced reasoning. A baseline above chance does not automatically mean leakage; it can mean the task contains usable information.

**Decision:** separate basic contract tests, genuinely compositional tasks, and construction tasks. Measure lift on identical appropriate tasks. Keep strong exact baselines rather than hiding input information to force neural necessity.

### D10. A registry and reconstruction test are useful but incomplete

**Claude:** proposes a compiled registry, decoder, and held-out round-trip. The addendum also accepts causal intervention. [S1 §§1-2 and addendum]

**My refinement:** a declared operation name does not certify its weights; reconstructing an expression does not establish that it governed the answer. Gold tree side channels can make decoding trivial.

**Decision:** report reconstruction, typed operation fidelity, causal participation, and comparative benefit separately. Instrument the prediction path for oracle calls and bypasses. A permitted full structured memory must not be advertised as strict fixed-vector compression.

## Additional specifications, not established disagreements

**Forty coordinates:** differing orderings can be connected by a tested permutation when meanings agree. Use domain-major internally in the isolated lab, preserve tokenizer IDs and round-trip tests, and do not change the global ontology. [S1]

**Twenty-eight categories:** preserve three explicit namespaces and defer a unified 28-way learned head. The user's compositional-40 clarification lets the first pilot proceed without resolving that separate semantic choice. [S1 addendum]

**Arithmetic-only structure test:** the quoted composition (i+j) mod 10 is commutative and associative. A repeated sum can solve that restricted algebra without learning operand order or tree grouping. Use it for finite behavioral checks, not as the sole evidence of expression-structure reasoning. Confirm the actual code's contract first. [S1; mathematical derivation]

**17 of 39:** this is about 43.6%, not two-thirds. Preserve the exact unsupported-leader list rather than the addendum's inconsistent fraction. [S1]

**Old checkpoints:** a shape change does not erase the validity of an old artifact under its original code. It prevents silent loading into a changed model. Migrations require explicit identities and initialized/missing tensor reports. [S2]

**Evaluation trust:** the reported scorer gap needs an external trusted anchor and independent rescoring, not merely a digest that the same run can rewrite. Historical reports remain preserved. [S2]

## What Fable is being asked to prove

Build one complete example in which a versioned CAS representation preserves necessary structure, a learned module uses it to produce a checked typed result, a meaningful intermediate correction changes downstream behavior as intended, and the checkpoint survives a fresh restart. Then test whether integrating that mechanism helps Helm on declared held-out tasks.

An excellent negative result is preferable to a false positive. But an absent optional provider, an unresolved unrelated namespace, or a failed first mechanism is not a reason to stop implementing the unblocked core.
