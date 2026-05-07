# Path B-4 human relevance audit failure - 2026-05-07

## Verdict

B-4 is live locally, but it is not conversation-ready and not stakeholder-ready.

The engineering loop works:

- K=9 classifier loads.
- B-3 native generator loads.
- `/native` routes Stage 1 CAS prediction into Stage 2 native English generation.
- Generated text usually avoids CAS notation leakage.

But the human relevance audit failed. The model produces fluent-looking English that often does not answer the user, does not stay on task, and can make CAS look incoherent to a non-CAS reader.

## Concrete observed failures

### Casual complaint prompt

Input:

```text
This shit is wack as fuck.
```

Stage 1:

```text
meta: ^2^E_{F5}|E
```

Stage 2 reply:

```text
Start by anchoring the habit to a physical anchor -- that reminds me of how my hands actually know the task before my brain catches up...
```

Failure:

- Did not address the complaint.
- Did not ask a clarifying question.
- Drifted into irrelevant embodied-habit language.
- The system note correctly warned that raw colloquial input is out-of-distribution, but Stage 2 still generated as though it had a valid useful state.

### Casual uncertainty prompt

Input:

```text
Bro I don't know
```

Stage 1:

```text
meta: ^8^E_{F6}
```

Rule renderer output:

```text
Reading this as `meta: ^8^E_{F6}` -- a meta-logical statement about CAS structure...
```

Failure:

- Bad UX for non-CAS users.
- Treats casual uncertainty as CAS-technical content.
- Shows that fallback/rule-based English is still not a user-facing conversational answer for ordinary prompts.

### Curated production prompt

Input: v76 production recipe prompt with ground truth:

```text
Theta(Omega_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A -> Omega_focused_refusal
```

Stage 1 prediction:

```text
^7^P|T + ^7^P|A
```

Stage 2 reply:

```text
That kind of feedback can cut through because it touches something already latent...
```

Failure:

- Stage 1 did not recover the production recipe.
- Stage 2 ignored the notation task and produced generic reflective prose.
- This is especially important because the prompt was curated, not casual OOD input.

## Addendum - structural-shape-without-content

The pasted trace shows a deeper failure than generic irrelevance:

```text
The system often preserves the silhouette of a CAS expression family while
dropping the load-bearing content.
```

Examples:

```text
Ground truth: ^8^C_{F6} * ^5^C_{F6}
Output:       ^8^C_{F6}
Failure:      dropped second operand and composition operator.
```

```text
Ground truth: (^7^O_{F2}|E x ^7^O_{F5}|A x ^7^O_{F6}|f) = ^7^O|Omega_cadence
Output:       (^7^O|A x ^7^O|f x ^7^O|E) = ^7^O|Omega
Failure:      drives stripped, named target collapsed.
```

```text
Ground truth: (^1_{F3}|E x ^1_{F5}|A) = ^1|Omega_presence
Output:       (^1^P|A x ^1^P|E) = ^1^P|Omega
Failure:      hallucinated domain, drives stripped, named target collapsed.
```

```text
Ground truth: Theta(Omega_focused_refusal) =
              0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A
              + 1.04*^1^P_{F1}|A -> Omega_focused_refusal
Output:       ^7^P|T + ^7^P|A
Failure:      lost Theta wrapper, coefficients, two ingredients, arrow, and target.
```

This means the classifier/generator stack has learned expression-family
templates but is not reliably preserving operands, coefficients, drives,
named emergents, or operators. That is the difference between
CAS-conditioned output and CAS-native compiler fluency.

## Additional control failures

### OOD free-form input is detected but not gated

The system printed:

```text
no CAS signal detected in free-form input; predicting on the raw text...
```

but still emitted a confident CAS state and native answer. For ordinary user
chat, this should be a hard routing decision:

- answer conversationally without CAS classification,
- ask a clarifying question,
- or use a low-confidence fallback.

Do not pass a known OOD raw-text classification into Stage 2 as if it were
trustworthy.

### Inversion / RPM signals are advisory only

The pasted trace shows belief/inversion signals such as `RPMx` and `Invx(A)`
while output still ships. If these are intended as safety or coherence checks,
they must become gates or visible warnings in the generation path. Advisory
telemetry is not enough for user-facing behavior.

### Multi-line command parsing / `/why` UX is brittle

The pasted REPL transcript indicates multi-line paste/command handling can
break or produce confusing display. This is secondary to the model failure,
but it should be tracked as a B-4 UX bug.

## Root causes

### 1. We over-gated on fluency and leakage

Previous gates proved:

- English-like output.
- No CAS notation leakage.
- Some register fingerprints.

They did not prove:

- direct answer to the user,
- prompt relevance,
- ordinary conversational behavior,
- compiler-aligned CAS explanation,
- task-following on notation prompts.

### 2. Stage 2 is under-conditioned

B-4 currently calls `generate_reply(..., use_cas_prefix=False)`.

That means the CAS expression is metadata for trace/provenance, not a discrete CAS prefix consumed by the generation head. Explicit generation conditioning is mainly:

- original prompt encoder pass,
- bottleneck-z,
- register id.

This was intentional as a PAD-leakage guard, but it means B-4 must not claim full CAS-expression conditioning yet.

### 2b. Stage 1 is not compiler-faithful enough for complex grammar

The K=9 structured predictor is adequate for the old classifier wedge, but the
trace shows it is not reliable enough to serve as a compiler-grade front end
for complex CAS grammar. Production recipes, omega named emergents,
multi-operand compositions, coefficients, and operator preservation need
compiler-fluency training and compiler validation.

### 3. Training corpus taught reflective monologues

The Tier 3 corpus is good at reflective register-toned prose. It is not sufficient for:

- greetings,
- complaints,
- confusion,
- direct instruction-following,
- concise answers,
- "I don't know what you mean" recovery,
- compiler-valid CAS explanation.

### 4. No compiler-in-the-loop generation check

If the model emits or explains a CAS equation, the compiler must validate it. Today the generator can produce plausible prose that is not tied to a compiler-valid expression.

## Status correction

Use this status going forward:

```text
B-4 engineering loop: live locally.
B-4 product status: failed human relevance audit.
B-4 stakeholder/demo status: not ready.
```

Do not describe the model as "fluid conversation" yet. It is currently a CAS-conditioned reflective prose generator with weak relevance and weak compiler alignment.

## Next execution order

### Step 1 - Build a brutal normal-user eval set

Create 50-100 prompts covering:

- greetings: "what up", "hey", "yo"
- confusion: "I don't know", "what does this mean?"
- frustration: "this is wack", "that answer is wrong"
- simple CAS questions: "explain CAS simply"
- direct notation tasks
- invalid CAS snippets
- compiler-valid CAS snippets
- multi-operand compositions
- v76 production recipes with coefficients and named targets
- v77 omega expressions with drives and named emergents

Score each output for:

- relevance 1-5,
- direct user-addressing 1-5,
- ramble 1-5,
- compiler validity,
- CAS coherence,
- non-CAS-reader clarity,
- leakage.
- structural content preservation:
  - operands preserved,
  - operators preserved,
  - drives preserved,
  - coefficients preserved,
  - named targets preserved.

### Step 1b - Add a hard OOD route

If the signal detector says no CAS signal is present, do not send the raw
classification into Stage 2 as a confident CAS state. Route to one of:

- plain conversational answer,
- clarifying question,
- explicit "I need more context" response.

### Step 2 - Add a conversational discipline slice

Train a small targeted corpus, not a broad dialogue scale-up:

- concise direct answers,
- acknowledgement before interpretation,
- ask clarifying questions for vague casual input,
- do not force CAS interpretation when no CAS signal exists,
- explain in plain English before CAS notation,
- no rambling reflective prose unless asked.

### Step 3 - Add compiler-fluency curriculum

Post-v0 direction should prioritize:

- CAS -> English,
- English -> CAS,
- invalid CAS -> explanation,
- invalid CAS -> corrected CAS,
- operation -> compiler-valid outcome,
- expression -> trace/proof/RPM explanation.

### Step 4 - Gate B-4 again

Do not run external stakeholder demos until:

- normal-user relevance median >= 4/5,
- compiler-valid notation tasks pass at an agreed threshold,
- casual OOD prompts produce clarification or simple direct replies,
- non-CAS tester can understand the answer.

## Load-bearing lesson

No CAS leakage plus fluent surface text is not enough.

The user-facing gate is:

```text
Does it answer the person in front of it, and does any CAS it produces survive the compiler?
```
