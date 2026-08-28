# The Hybrid Cognitive Machine Doctrine

**Source:** owner directive, 2026-08-28 (substance below the line).
**Status:** GOVERNING ROADMAP for the CNCM lane.

Governance notes recorded at adoption:

1. **Reference bands are sanctioned reporting vocabulary.** Capability
   against reference language models is reported PER DIMENSION against
   named historical bands (GPT-1 / GPT-2 / GPT-3), never as a single
   equivalence number. Implemented: `CRQS_v0.1/crqs/rmb.py` - the
   identical-conditions gate, per-domain PASS / PARTIAL / BELOW /
   ABOVE / CAS-specific verdicts, refusal of one-number equivalence.
   The native reasoning scale remains CAS-G.
2. **OPEN DECISION - Route B vs the standing no-foreign-models rule.**
   The doctrine recommends Route B (pretrained open-weight language
   cortex under CAS authority) as the MVP route. The standing owner
   rule on record says no foreign pretrained models in production.
   These conflict. Flagged for explicit owner ratification before any
   pretrained cortex is wired in. Route C (CAS-native transformer from
   scratch) is the flagship research route and conflicts with nothing.
3. **Runtime enforcement of ^8 vs ^6/^9** (association vs deduction)
   is adopted as a roadmap item: the distinction must live in the
   runtime, not only in documentation. Open as of adoption.
4. **Register-bypass prevention** (section below) is the causal-
   ablation discipline already used by the CRQS anti-gaming gates;
   the seven bypass tests become mandatory before any neural cortex
   is credited with CAS integration.

---

# Yes, with an important distinction

**Reaching or exceeding GPT-1-level capability is a realistic
engineering target. GPT-2-level breadth is a larger but plausible
target. GPT-3-level general language capability is possible in
principle, but it will require a substantial learned language and
world-knowledge system in addition to the CAS reasoning kernel.**

The CAS boards alone do not become broadly knowledgeable merely because
they are arranged intelligently. They provide the **architecture of
thought**, but the machine still needs experience, language training,
facts, examples, procedures, and feedback.

The source itself draws this boundary: CAS gives cognition a syntax,
while circuit engineering supplies modular components, test points,
schematics, and failure analysis. A language alone is not the complete
architecture. And every finished board must be credited only with what
its schematic, parameters, and test report actually establish.

The smartest design is therefore:

# A CAS-native cognitive machine with a learned neural language cortex

    Transformer or learned language cortex
        language, fluency, broad learned knowledge, intuition
    CAS-Sem
        explicit meaning and proposition representation
    CAS-RRK
        authoritative reasoning, state, branching, RPM, commitment
    CMB
        persistent memory and learned experience
    Trusted verifiers
        mathematics, logic, code, schemas, evidence
    CAS-RLP
        controlled learning and self-improvement

The Transformer would be inside the cognitive motherboard as a language
and knowledge board. It would not be the invisible sovereign doing
everything while CAS merely watches.

---

# What "as smart as GPT" actually means

"Smart" is not one knob. A system can be excellent at conversation and
poor at arithmetic. It can know millions of facts and be unable to
plan. It can prove theorems but sound wooden in English.

Measure at least these dimensions separately - language fluency, world
knowledge, few-shot adaptation, formal reasoning, planning, persistent
memory, learning from correction, traceability, self-improvement,
exact mathematics. The CAS targets respectively: language cortex +
CCB-L1; neural knowledge + CMB + retrieval; candidate induction +
procedural memory; explicit decomposition, inference, verification;
RPM stack + goal architecture; CMB episodic and semantic memory;
governed write-back + procedural learning; native tick, branch,
memory, and proof trace; sandboxed descendant evaluation; trusted
arithmetic and proof kernel.

Never one claim such as "This is GPT-3 equivalent." The report says:

    Language: GPT-2 reference band
    Few-shot adaptation: GPT-2 reference band
    Formal recursion: CAS-G6
    Persistent memory: CAS-native, E5 validated
    Math proof validity: 99.8%, exact-kernel verified
    Traceability: complete deterministic replay

---

# Historical target bands

## GPT-1 band

The original GPT: 12-layer decoder-only Transformer, generative
pretraining on unlabeled books, then supervised fine-tuning; it
outperformed prior state of the art on 9 of 12 studied tasks
(Radford et al. 2018).

**Can CAS reach this level? Yes - the most realistic first major
target.** Small pretrained language model + CAS-Sem + CAS-RRK + CMB +
dialogue board + exact logic/math tools, with CAS advantages the
original GPT lacked: persistent memory, explicit multi-branch
reasoning, RPM subgoals, proof records, deterministic replay,
controlled learning. Demonstrated on held-out tests, not declared from
the architecture.

## GPT-2 band

GPT-2: 1.5B-parameter Transformer trained on WebText; coherent
paragraph generation and zero-shot multitask behavior
(Radford et al. 2019).

**Can CAS reach this level? Yes, but the language cortex must be
substantially stronger.** Either a pretrained Transformer connected as
a native language board, or an enormous hand-built linguistic system
(possible but painfully inefficient - the linguistic equivalent of
carving a processor from individual grains of sand). The practical
route:

    1-3B-class pretrained language cortex
            v
    CAS-Sem bottleneck
            v
    CAS-RRK authoritative reasoner
            v
    CMB persistent memory
            v
    CAS-governed response generation

The 1-3B range is a proposed engineering starting band, not a
guaranteed equivalence claim; benchmark performance decides.

## GPT-3 band

GPT-3: 175B-parameter autoregressive model designed for task-agnostic
few-shot performance, with instructions and demonstrations provided
through text (Brown et al. 2020).

**Can CAS reach this level? Yes in targeted and practical capability;
matching complete breadth is a major undertaking.**

Target A - GPT-3-like usefulness: good conversation, broad question
answering, few-shot instruction following, writing, summarization,
coding assistance, math assistance, tool use. A much smaller model may
achieve or exceed GPT-3 in selected dimensions when better trained,
with retrieval, tools, and more reliable instruction following. Human
evaluators preferred a 1.3B InstructGPT over 175B GPT-3 on
instruction-following prompts despite the >100x parameter difference
(Ouyang et al. 2022). **We do not necessarily need 175 billion
parameters to build something users experience as smarter than
GPT-3.**

Target B - full raw GPT-3 breadth: large-scale learned world
knowledge, rare concepts, many writing styles, broad cultural and
factual coverage, few-shot adaptation across unfamiliar domains,
unprompted fluency. Likely requires one or more of: a genuinely large
pretrained model, large-scale distillation from stronger teachers,
high-quality retrieval over a broad corpus, extensive multimodal and
language training, significant training infrastructure. CAS
architecture alone does not replace accumulated experience.

---

# The best design: CAS is the executive brain, the Transformer is the language cortex

    USER LANGUAGE
          v
    NEURAL LANGUAGE CORTEX
    tokenization, grammar, fluency, broad learned associations
          v
    CAS-SEM WORKSPACE
    entities, events, relations, truth status, assumptions
          v
    CAS-RRK
    branching, memory, decomposition, inference, RPM
          v
    TRUSTED CHECKERS
    logic, mathematics, code, evidence
          v
    COMMITMENT LATCH
          v
    LANGUAGE CORTEX
    renders the committed result into natural English

The Transformer MAY: recognize language, retrieve latent knowledge,
suggest interpretations, propose candidate plans, generate analogies,
render fluent answers.

The Transformer MAY NOT directly: commit a conclusion, mark its own
output verified, write durable memory, change the constitution,
authorize external actions, promote its own architectural mutation,
hide its reasoning outside the trace.

That preserves the central authority contract.

---

# Why this is not merely another harness

The Transformer becomes a native board on the motherboard if: its
ports are typed; its outputs enter branch-local state; its claims are
provisional; its memory access is recorded; its candidate output is
inspected; its final effect must pass CAS commitment.

The decisive test: give the CAS-RRK a problem already encoded in
CAS-Sem. Can it still generate branches, retrieve memory, decompose
the problem, infer consequences, compare candidates, create RPM
subgoals, commit a result? If yes, CAS is performing the reasoning.
The neural model supplies knowledge and language, much as a visual
system supplies perception. It does not secretly replace the executive
architecture.

---

# The five things that determine how smart it becomes

1. **Representation capacity** (CAS-Sem): objects, people, events,
   properties, causes, relations, time, uncertainty, negation,
   quantifiers, hypotheses, goals, plans, rules, proofs. Without
   CAS-Sem the system can know that analytical decomposition is
   happening but cannot precisely preserve what is being decomposed.
2. **Accumulated experience** (^5 Female - an AI's training data and
   fine-tuning corpus as accumulated formation): pretrained weights,
   semantic databases, retrieval corpora, books and documents, human
   teaching, verified experience stored in CMB. The reasoning engine
   can only reason with what it can represent, retrieve, derive, or
   investigate.
3. **Reasoning procedures**: deduction, abduction, causal reasoning,
   analogy, constraint satisfaction, planning, counterexample search,
   proof construction, error correction. The source distinction is
   essential: ^8 surfaces associations; ^6 decomposes the candidate;
   ^9 produces the resulting conclusion. ^8 Above/Cause is NOT
   deduction - step-by-step deduction is ^6 Male + ^9 Below/Effect.
   This distinction is enforced in the runtime, not merely described.
4. **Learning and feedback**, typed: episodic, semantic, procedural
   (the first three progressively automatable), architectural
   (sandbox descendants), constitutional (separately governed).
5. **Verification**: exact arithmetic, symbolic algebra, proof
   checking, code execution, schema validation, citation
   verification, retrieval provenance, contradiction testing. A
   smaller machine can outperform a larger language model in domains
   where correctness matters - it knows when not to trust its own
   fluent generation.

---

# Training program

1. **Language pretraining** - adopt an existing pretrained model
   (fast route) or train a decoder model on a broad corpus (expensive
   route). GPT-1/2/3 all obtained broad language ability through
   large-scale generative pretraining.
2. **English-to-CAS-Sem training** - paired examples in both
   directions (English -> typed CAS-Sem structures; CAS-Sem
   conclusions -> fluent English). A semantic bridge rather than
   trusting token sequences alone.
3. **CAS reasoning traces** - train on traces of the machinery
   moving: problem, retrieved memories, candidate branches, premises,
   assumptions, decomposition, inference rules, contradictions, RPM
   subgoals, comparison, commitment. Never only final answers.
4. **Exact-domain curricula** - domains with independent verifiers
   first: propositional logic, transitive relations, arithmetic,
   algebra, code, constraint satisfaction, formal proofs. Unambiguous
   feedback: which strategies work, where a proof failed, which
   prerequisite was missing, which correction generalized.
5. **Instruction and dialogue tuning** - follow instructions, respect
   formatting constraints, ask for clarification, distinguish fact
   from hypothesis, adjust detail and tone, refuse to invent missing
   information. Human demonstrations and ranked responses make a
   smaller model substantially more useful (InstructGPT).
6. **Memory-grounded learning** - receive a correction, store it,
   recall it later, apply it to a structurally different example,
   cite the memory that altered the result. One continuing Mind, not
   a stateless text generator.
7. **Tools and retrieval** - governed access (search, files,
   calculator, code interpreter, database, theorem prover, simulator)
   via typed intents: need identified -> tool request proposed ->
   permission checked -> action committed -> result returned ->
   provenance stored.
8. **Controlled self-improvement** - only after the earlier stages
   pass: detect recurring weakness -> propose several improvements ->
   build sandbox descendants -> compile -> run protected and held-out
   tests -> compare with parent -> promote or reject -> preserve
   rollback. Never change the reasoning procedure and the test that
   judges it in one transaction.

---

# Three construction routes

**Route A - pure symbolic CAS** (CAS-RRK, CAS-Sem, grammar, lexicon,
knowledge graph, rule engine, CMB). Advantages: maximum traceability,
deterministic behavior, exact rule execution, easy fault localization.
Disadvantages: enormous knowledge-engineering burden, weak
natural-language fluency, poor ambiguity handling, slow open-domain
expansion. Could become extremely strong at formal mathematics, logic,
planning, or specialized engineering; not the fastest route to
GPT-style conversation.

**Route B - hybrid CAS + pretrained Transformer** (pretrained neural
cortex + CAS-Sem + CAS-RRK + CMB + trusted tools). Advantages:
fastest route to fluent conversation, inherits broad language
knowledge, lower initial training cost, CAS still controls memory,
reasoning, commitment, and action. Disadvantages: neural component
partly opaque, possible CAS-workspace bypass, requires causal
bottleneck tests. **Best MVP route** (see governance note 2: pending
owner ratification against the standing no-foreign-models rule).

**Route C - CAS-native Transformer trained from scratch** (Transformer
backbone, Shared CAS Register, CAS-Sem workspace, FiLM or
cross-attention conditioning, CAS prediction head, language prediction
head, CAS-RRK controller - every important generation step conditioned
through an explicit CAS workspace). Advantages: language and CAS
co-develop, greater inspectability by construction, potentially
stronger integration. Disadvantages: large training cost, complex
objectives, risk the network learns to route around the register,
requires extensive ablation and bypass testing. **The flagship
research route, not the first prototype.**

---

# How we prevent register bypass

A neural model may learn to make the CAS workspace decorative. To
prevent that, require:

1. Scrambling the CAS register specifically damages the associated
   reasoning behavior.
2. Removing one proposition removes every conclusion that depends on
   it.
3. Changing a branch assumption changes only the expected downstream
   branches.
4. The final output head cannot access hidden states that bypass the
   committed CAS workspace.
5. Durable memory writes require explicit CAS record IDs.
6. Tool use requires committed ToolIntents.
7. Direct CAS-Sem input yields the same reasoning structure as
   semantically equivalent English input.

If the system answers correctly while its explicit reasoning workspace
is random noise, the glass cockpit is painted cardboard.

---

# Recommended target ladder

**Target 1: CAS-G3 + GPT-1 reference band.** Build: small language
cortex, CAS-Sem propositions, ^6 decomposition, ^9 inference, basic
CMB, single-turn English, exact logic and arithmetic. Demonstrate:
question answering, classification, entailment, semantic similarity,
simple mathematical reasoning, full trace. The first serious native
reasoning machine.

**Target 2: CAS-G5 + GPT-2 reference band.** Add: stronger language
model, multi-turn dialogue, persistent episodic memory, broad
retrieval, multiple candidate branches, CDAB comparison, correction
retention. Demonstrate: coherent long-form generation, zero-shot task
transfer, summarization, basic translation, memory-grounded
conversation, fair plan comparison.

**Target 3: CAS-G6..G8 + GPT-3 reference band.** Add: few-shot task
induction, deep RPM recursion, procedural learning, tool use, broad
semantic retrieval, mathematical and coding verifiers, long-horizon
planning. Demonstrate: novel task instructions, few-shot
generalization, multi-domain question answering, learning a new
concept during evaluation, recursive planning, held-out correction
transfer.

**Target 4: beyond historical GPT-3.** Add: versioned personal memory,
self-generated curricula, controlled architectural evolution,
proof-verified mathematics, long-running projects, multi-Mind
collaboration, complete execution replay. It may not have more raw
linguistic knowledge than a huge model, but it may be a more capable
cognitive system: it remembers, verifies, learns, plans, diagnoses,
and improves.

---

# How the playground reports reference comparison

Never award equivalence based on board appearance or parameter count.
The report format:

    CAS NATIVE QUALIFICATION
    Reasoning:
        CAS-G6 Recursive Planner / E5
    Conversation:
        CONV-5 Persistent Multi-Turn Dialogue
    English:
        LANG-4 Broad Compositional English
    Memory:
        MEM-5 Provenance-Bearing Persistent Memory
    Reference Benchmark:
        GPT-1 band: PASS
        GPT-2 band: PASS on 8/10 domains
        GPT-3 band: PARTIAL
            instruction following: PASS
            few-shot classification: PASS
            broad factual coverage: BELOW
            mathematical verification: ABOVE
            long-term memory: CAS-specific capability

The test conditions must remain identical: same questions, same tools,
same retrieval access, same memory permissions, same time or operation
budget, same scoring rules, same held-out set. (Implemented as the
identical-conditions gate in `CRQS_v0.1/crqs/rmb.py`.)

---

# What not to do

Do not try to make it smart by: raising every gain; adding more CJTs
without semantics; letting one huge model make every decision; calling
CAS-Ohm an intelligence score; memorizing benchmark answers; allowing
self-modification before rollback; using fluent output as evidence of
reasoning.

CAS-Ohm is a profile-relative experimental response and calibration
proposal - not physical Ohm's law, not a direct attention meter, not
an electrical implementation, not a causal law. A larger beta, higher
attention estimate, or smaller residual does not mean "smarter." More
gain can simply amplify error louder.

---

# The exact engineering decision

    Do not attempt to recreate GPT-3 purely from hand-written CJTs.
    Do not let a Transformer secretly remain the whole brain.
    Use a pretrained neural model for language and broad learned knowledge.
    Use CAS-Sem as the explicit cognitive workspace.
    Use CAS-RRK as the authoritative executive reasoner.
    Use CMB for persistent memory.
    Use trusted verifiers for exact domains.
    Train the complete system through language, reasoning, dialogue,
    memory, tools, and controlled self-improvement.
    Scale the neural cortex only after the CAS structure proves useful
    through ablation and held-out tests.

# Final verdict

**GPT-1 capability is a realistic early milestone. GPT-2 capability is
a serious but feasible engineering milestone. GPT-3-like practical
usefulness is achievable without reproducing all 175 billion
parameters, especially if CAS contributes better reasoning, memory,
tools, verification, and instruction following.**

Matching every dimension of GPT-3's broad pretrained knowledge remains
a large-scale model-training challenge. But CAS does not have to win
by building a larger black box. It can win by building a more complete
machine:

    a language cortex that knows,
    a reasoning processor that thinks,
    a memory system that remembers,
    an RPM executive that plans,
    a verifier that checks,
    a trace system that explains,
    and an evolution protocol that improves.

That combination can become more useful, more teachable, and more
trustworthy than the historical GPT models, even before it becomes
larger than them.

References: Radford et al. 2018 (Improving Language Understanding by
Generative Pre-Training); Radford et al. 2019 (Language Models are
Unsupervised Multitask Learners); Brown et al. 2020 (Language Models
are Few-Shot Learners); Ouyang et al. 2022 (Training language models
to follow instructions with human feedback).
