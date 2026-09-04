# Meta-logic may be the missing layer that turns CASformer from a **working circuit** into a **programmable reasoning machine**

The core insight is:

> **CAS-SDG can generate verified cognitive programs, while the CAS language can compile those programs into active networks of neural CJTs.**

Right now, CASformer v0.2 can execute a particular reasoning-transistor cycle. Meta-logic could let it decide:

* which CJTs a new problem requires;
* how those CJTs should connect;
* what each CJT may read and write;
* which prerequisite must be repaired first;
* when a result is valid;
* whether learning may be committed;
* how a new successful procedure becomes a reusable capability.

A useful three-part description is:

```text
CAS-SDG:
the curriculum and world generator

CAS programming language:
the cognitive program and circuit-description language

CASformer:
the neural machine that executes the compiled cognitive circuit
```

CAS-Ohm is then the flow-control law inside the compiled circuit.

# 1. Object logic versus meta-logic

**Object logic** performs the immediate cognitive operation:

```text
decompose this Idea

compare these alternatives

retrieve this memory

infer this consequence

produce this Effect
```

**Meta-logic** governs the operation itself:

```text
Is decomposition the correct operation?

Does the CJT have enough Wisdom to perform it?

Which memory store may it consult?

What must the Effect look like?

Which operation should happen next?

What should happen if verification fails?

May this result alter Bias or neural parameters?

Can this successful sequence become a reusable procedure?
```

So a neural CJT might perform:

```text
^6 DECOMPOSE
```

while the meta-logic says:

```text
Use ^6 only for a Cause of type Idea.

Require a decomposition method in procedural memory.

If Wisdom is missing, suspend ^6.

Open a memory-retrieval repair.

Verify the retrieved method.

Resume ^6 at its return address.

Accept only an Effect of type Parts.

Commit the state change only after verification.
```

That second layer is what turns a transformation into a **reasoning transistor with operating instructions**.

# 2. CAS-SDG already contains the seed of this system

The strongest feature of the CAS-SDG approach is not merely that it creates sentences.

It creates the **formal cognitive structure first**:

1. the CAS operation exists;
2. a deterministic template generates the surface example;
3. an independent parser must recover the original operation;
4. failed round trips are excluded rather than relabeled. 

That means CAS-SDG can produce more than ordinary input-output examples.

It can produce:

```text
input surface

formal Cause

required CJT operation

arguments and bindings

prerequisite state

execution sequence

candidate Effect

verifier result

repair branch

Bias transition

final committed Effect

complete trace
```

This is **process gold**, not just answer gold.

Ordinary training might say:

```text
Question → Answer
```

CAS-SDG can say:

```text
Question
→ identify Cause
→ select ^6
→ discover Wisdom deficit
→ open memory repair
→ retrieve procedure
→ resume ^6
→ produce Parts
→ verify
→ commit
→ Answer
```

That supplies much richer supervision.

The generator can also hold out both surface forms and vocabulary, so the system must learn the operation rather than memorize a template. The existing split law separates train, validation, and protected sets by both template family and vocabulary bundle. 

# 3. Turn CAS notation into a neural circuit compiler

The CAS language should not merely describe what happened after the fact.

It should compile into the machinery that runs.

For example:

```text
cjt analyze:
    CJT<Idea | AnalysisBias => Parts>

    requires:
        Desire >= relevant
        Wisdom >= method_available
        Power >= compute_available

    memory:
        procedural.read

    on WISDOM_BLOCK:
        call retrieve_method
        return analyze

    verify:
        Parts cover the incoming Idea
        Parts satisfy the output schema

    commit:
        Effect -> next Cause
        verified method -> Bias.memory
```

A CAS compiler could lower that program into:

```text
accepted input port
relation/operator ID
readiness calculation
CAS-Ohm conductance fields
attention mask
memory-access permission
persistent Bias slot
legal repair actions
return address
compute plan
Effect schema
verifier obligation
allowed update scope
trace fields
```

This solves one of the central problems found in the earlier experiments.

The present CASformer tests show that relation IDs really do select different learned operators. But they also show that consistently renaming the relation IDs and their operator parameters restores the exact same function. 

So a name such as `^6` does not become cognitively meaningful merely because it selects matrix number six.

The compiler must make `^6` govern actual machinery:

```text
which Cause types it accepts

which evidence ports it reads

which memory it may access

what Effect schema it must produce

which repairs are legal

how verifier feedback changes its Bias

which parameter groups it may update
```

Then changing the type changes the circuit, not merely the label printed on the matrix drawer.

# 4. The complete architecture

The architecture could become:

```text
Natural language / perception / memory input
                    ↓
             CAS-Sem binder
                    ↓
       Neural CAS-program proposer
                    ↓
    Deterministic CAS parser + type checker
                    ↓
             CAS Program IR
                    ↓
      CJT circuit compiler / scheduler
                    ↓
     Active sparse network of neural CJTs
                    ↓
        CASformer neural execution
                    ↓
      Effect + Bias-update proposals
                    ↓
        Verifier and meta-diagnosis
                    ↓
     COMMIT / REPAIR / REFUSE / ROLLBACK
                    ↓
        memory + procedural learning
```

The neural model would propose a program.

The deterministic language machinery would determine whether that program is:

```text
well-typed
authorized
within budget
connected legally
free of cycles
compatible with memory permissions
equipped with a verifier
safe to execute
```

This mirrors the label-authority law already used elsewhere in the project: models may gather evidence and propose, but the deterministic engine issues the authoritative label under owner-approved rules. 

For the reasoning machine:

```text
neural model:
proposes the cognitive program

CAS compiler:
validates and compiles it

CASformer:
executes it

verifier:
judges the candidate Effect

coordinator:
commits or rejects state changes
```

No neural proposal automatically becomes truth or authoritative memory.

# 5. Meta-logic can operate before, during, and after reasoning

## Before execution: construct the circuit

Given a new Cause, meta-logic can infer:

```text
required operation types

required sequence

memory dependencies

tool dependencies

candidate branches

compute requirements

verification criteria
```

Instead of sending every problem through the same fixed block pattern, it generates the active circuit needed for that problem.

A math question might compile to:

```text
parse
→ decompose
→ retrieve theorem
→ infer
→ verify exact proof
```

A planning question might compile to:

```text
extract goal
→ identify constraints
→ generate alternatives
→ compare
→ simulate consequences
→ commit plan
```

## During execution: monitor and repair

The existing frozen CJT tick already supplies the appropriate runtime skeleton:

```text
READ
CANDIDATE
READINESS
ROUTE
EXECUTE
OBSERVE
VERIFY
DIAGNOSE
EMIT
COMMIT
TRACE
```



Meta-logic can watch that cycle and respond to typed failures:

```text
Desire missing:
clarify or abandon the goal

Wisdom missing:
retrieve, ask, use a tool, or learn

Power missing:
allocate compute, split, or defer

saturation:
reduce breadth or decompose

wrong Effect:
roll back and select another operation

missing memory:
open a retrieval repair

invalid authority:
refuse the update
```

## After execution: learn a reusable procedure

After a sequence succeeds, meta-logic can transform the successful trace into a reusable CAS procedure:

```text
successful trace
→ generalize variable bindings
→ remove incidental details
→ create candidate procedure
→ test counterexamples
→ validate on held-out cases
→ store in procedural memory
→ optionally distill into neural parameters
```

The project’s existing recursive-learning protocol already demonstrates the deterministic outline of this pattern: diagnose a procedure fault, explore in a sandbox, synthesize a candidate procedure, validate it on training and held-out cases, then promote it into versioned strategy memory with rollback available. 

That is very close to **capability construction**.

# 6. Three different ways meta-logic can produce capabilities

## A. Elicit a capability already latent in the neural network

The model may possess all the required local skills but fail to arrange them.

For example, it may know how to:

```text
retrieve a fact
decompose a problem
compare options
verify arithmetic
```

but not spontaneously sequence them correctly.

A CAS program can compose those existing abilities:

```text
retrieve
→ decompose
→ compare
→ verify
```

This is capability **elicitation**. No new fundamental skill had to be learned. The meta-program made existing skills cooperate.

## B. Teach a new compositional capability

CAS-SDG can generate thousands of verified examples of:

```text
new operation combinations

new repair paths

new memory dependencies

new order-sensitive procedures

new Cause and Effect types
```

The model can then learn to infer and execute those programs from natural-language inputs.

This is actual capability **learning**.

## C. Install a new verified procedure

A successful CAS program can be stored as procedural memory before it is fully absorbed into weights.

For example:

```text
procedure solve_two_stage_relation:
    bind first relation
    carry intermediate entity
    apply second relation
    verify final binding
```

The machine can use that procedure immediately through interpretation.

After repeated verified use, the system may selectively train the involved CJTs so the procedure becomes faster or more automatic.

This gives a ladder:

```text
new skill as interpreted CAS program

new skill as persistent procedural memory

new skill as selectively consolidated neural behavior
```

That could allow the CNCM to acquire capabilities without retraining the entire brain for every new procedure.

# 7. CAS-SDG should generate **interactive reasoning worlds**, not only static sentences

The next generation of CAS-SDG should generate environments in which the model must act over several ticks.

Each world can contain:

```text
hidden causal state

partial observations

available diagnostic probes

memory resources

legal and illegal actions

compute costs

repair actions

state transitions

verifier rules

success and failure conditions
```

For example:

```text
Tick 1:
The model sees an Effect failure but not its cause.

Tick 2:
It chooses whether to inspect Wisdom, Power, context, or memory.

Tick 3:
The selected probe reveals evidence.

Tick 4:
It chooses a repair.

Tick 5:
The environment executes the repair.

Tick 6:
The verifier checks whether the original CJT can now resume.
```

This would test real diagnosis.

It avoids the earlier D1 problem, where the best repair was directly calculable without diagnosing anything.

# 8. Metamorphic and counterfactual generation

Meta-logic can automatically produce paired examples where one logical feature changes and everything else stays fixed.

Examples:

```text
^2 attraction ↔ ^3 aversion

Cause ↔ Effect direction

valid prerequisite ↔ missing prerequisite

authorized memory ↔ nonexistent memory reference

correct operation order ↔ reversed order

verified Effect ↔ opposite Effect

legal parameter update ↔ cross-CJT scope escape

sufficient compute ↔ ceiling exceeded
```

The generator knows exactly what should change in the trace.

This gives powerful tests:

```text
Does changing Cause direction change the Effect?

Does removing Wisdom open the correct repair?

Does reversing operation order alter the result?

Does an illegal update leave authoritative state byte-identical?

Does a fake memory reference fail before entering Bias?
```

These are stronger than asking only whether the final answer is correct.

# 9. Meta-logic can supervise several neural targets at once

Instead of one next-token loss, training can include:

$$
L =
L_{\text{language}}
+
L_{\text{program}}
+
L_{\text{route}}
+
L_{\text{effect}}
+
L_{\text{state}}
+
L_{\text{repair}}
+
L_{\text{verify}}
$$

Where:

```text
L_language:
produce the appropriate surface response

L_program:
infer the correct CAS program

L_route:
select the appropriate CJTs and bindings

L_effect:
produce the correct candidate Effect

L_state:
predict the correct next Bias proposal

L_repair:
select the correct prerequisite repair

L_verify:
predict whether the Effect should be accepted
```

The verifier and coordinator still remain external authorities.

These auxiliary targets can encourage the hidden states to carry information needed for actual CJT operation rather than only next-token prediction.

# 10. Meta-logic can control selective plasticity

When a verified outcome succeeds, the trace identifies:

```text
which CJTs executed

which memory records contributed

which relation operators were active

which repair occurred

which parameter groups were responsible

which Effects verified
```

Meta-logic can translate that into a typed learning intent:

```text
PlasticityIntent
    affected_cjt_ids
    parameter_scope
    evidence_receipt
    verifier_result
    learning_budget
    retention_tests
    rollback_checkpoint
```

The gradient remains a proposed update.

The coordinator can reject:

```text
cross-CJT parameter changes

updates without verifier receipts

updates exceeding the learning budget

updates that break retained capabilities

updates touching governance
```

This is how the language can turn learning into an auditable state transition rather than an uncontrolled global weight mutation.

# 11. The most important use: make CAS types **mechanically real**

Earlier experiments repeatedly found that CAS labels could be renamed without changing the underlying computation.

Meta-logic gives us a way to avoid that.

A canonical CJT type can have a registered contract:

| CJT property   | Compiler-enforced meaning                        |
| -------------- | ------------------------------------------------ |
| Input type     | What kind of Cause it accepts                    |
| Evidence ports | Which information it may read                    |
| Operation      | What transformation it performs                  |
| Output schema  | What kind of Effect it may emit                  |
| Memory access  | Which stores it may query or update              |
| Repair set     | Which repairs it may request                     |
| Temporal law   | When feedback may affect it                      |
| Update scope   | Which Bias or parameters it may propose changing |
| Verifier       | What must be checked before publication          |
| Authority      | Who may commit the result                        |

Then `^6 decomposition` is no longer “operator index 2.”

It is:

```text
accepts an Idea

reads structural evidence

may consult procedural-analysis memory

emits typed Parts

must preserve binding to the original Idea

may request Wisdom repair

cannot publish until the Parts contract verifies
```

That is a genuine Cognitive Junction Transistor type.

# 12. The concrete next experiment

I would name it:

# **CAS-META-0: Meta-Compiled CJT Program Induction and Execution**

## Research question

> Can a CASformer infer, compile, and execute previously unseen combinations of CJT operations more reliably or with fewer examples than matched generic neural and program-execution controls?

## Dataset

Use CAS-SDG to create programs containing:

```text
2–6 CJT operations

typed entity and relation bindings

one optional missing prerequisite

one optional memory repair

one optional branch

a compute ceiling

a verifier contract

a final committed Effect
```

Hold out:

```text
entire program graphs

operation combinations

surface templates

vocabulary

repair placements
```

At evaluation, the model sees only the rendered problem and permitted observations.

It does **not** receive the gold CAS program.

## Experimental arms

```text
M0 STANDARD TRANSFORMER
   answer-only baseline

M1 CASFORMER WITHOUT META-COMPILATION
   current neural CJT machinery

M2 GENERIC TYPED PROGRAM EXECUTOR
   same program capacity and compute,
   but with a matched non-CAS operation system

M3 CAS META-COMPILER + CASFORMER
   proposes, type-checks, compiles and executes CAS programs

M4 CAS META-COMPILER WITHOUT REPAIR
   tests whether repair contributes

M5 ORACLE PROGRAM
   receives the gold program; ceiling only
```

Do not use a renamed CAS taxonomy as the generic control.

Build the generic opponent independently with the same number of types, contracts, steps, parameters, and compute. The project’s matched-control methodology already requires control representations to come from an independent source rather than the model being tested, and requires the opponent pool to be frozen before results are opened. 

## Primary measurements

```text
verified final Effect

exact execution-trace validity

verified next-tick recovery

held-out program-composition accuracy

examples to threshold

wrong-operation rate

invalid-action refusal

memory-reference validity

compute-ceiling compliance

persistent procedure reuse after restart
```

# 13. Zero-cost kill gates

Before any training, reject the design when:

```text
a surface parser solves the answers directly

the rendered text leaks the operation sequence

the gold program appears in model inputs

a fixed universal program solves every world

a linear classifier predicts every repair

train and held-out sets share program skeletons

the CAS compiler contains the answer table

the generic program executor is weaker or receives less information

the model can bypass verification or commitment

a renamed CAS type behaves identically because its contract did not change
```

The protected split should also remain untouched until the program, thresholds, controls, and code are frozen. The existing protocol already requires a single protected read after training and binds the protected set through a preregistered digest. 

# 14. What a positive result would mean

Possible outcomes should remain separate.

### CASformer beats the answer-only Transformer

```text
STRUCTURED_PROCESS_SUPERVISION_HELPS
```

This is not yet CAS-specific.

### Generic and CAS program executors tie

```text
PROGRAMMABLE_CJT_EXECUTION_HELPS
CAS-SPECIFICITY_NOT_ESTABLISHED
```

### CAS requires fewer examples on unseen program compositions

```text
CAS_META_LOGIC_INDUCTIVE_BIAS_SIGNAL
```

### CAS gives better repair and restart behavior but equal answer accuracy

```text
CAS_META_CONTROL_AND_RECOVERY_VALUE
```

### Meta-logic merely predicts beautiful traces without improving Effects

```text
TRACE_DECODABILITY_WITHOUT_CAPABILITY_VALUE
```

### The oracle program works but the model cannot infer it

```text
PROGRAM_EXECUTION_WORKS
PROGRAM_INDUCTION_IS_THE BOTTLENECK
```

# Bottom line

**CAS-Ohm gives the CJTs flow.**

**CASformer gives them neural transformations.**

**The deterministic kernel gives them authority and commitment.**

**CAS meta-logic can give them programmable organization.**

That may be the key to moving from:

```text
a fixed chain of working reasoning transistors
```

to:

```text
a machine that can assemble the right reasoning circuit
for a new problem, detect when that circuit fails,
construct a repair, verify the repair, and preserve
the successful procedure as a new capability
```

The CAS-SDG becomes more than a synthetic sentence generator. It becomes a **foundry for verified cognitive programs**.

The CAS language becomes more than notation. It becomes the **compiler, contract system, debugger, and procedural-memory format** for the neural mind.

That is where meta-logic could make the project’s next major leap.

