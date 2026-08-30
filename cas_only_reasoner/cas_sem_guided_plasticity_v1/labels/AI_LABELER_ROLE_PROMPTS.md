# AI Labeler Role Prompts

Part of LABEL PHASE 0B. Documentation only; not claim-bearing.

## What this document is

This is a set of ready-to-reuse prompt templates for three AI model roles used in the
LABEL PHASE 0B pipeline. The models help the labeling work. They do NOT decide the final
label. This document gives you the exact words to hand each model, the shape its output
must take, and the hard rule that model output never becomes a claim-bearing label on its
own.

Read the "no authority" rule first, then the templates.

## The one rule that governs everything here

Old rule (retired): "No LLM assigns claim-bearing labels. A human labels each sense."

New rule (in force): "No LLM OUTPUT ALONE has claim-bearing label authority."

Plain English: a model may find sources, quote them, suggest a label, suggest which
mapping rule applies, write paraphrases, spot ambiguity, and argue against a candidate
label. A model may NOT write the final label that a scientific claim will lean on. That
final label is set by a deterministic program, or by the owner correcting a verified
pipeline error. "Deterministic" means the same input always gives the same output, with no
model in the loop.

A claim-bearing label is one of exactly two kinds:
- CONSTRUCTION_GOLD — the CAS state and trace existed BEFORE the sentence was generated.
- RESOURCE_GOLD — a frozen external sense id mapped to a CAS class by an owner-approved
  deterministic rule (claim-bearing only after audit).

Everything a model produces is, at most, MODEL_PROPOSED. MODEL_PROPOSED is NEVER
claim-bearing.

### Why agreement between models grants no authority

- 3 models agreeing does NOT create a gold label.
- 3 models disagreeing does NOT prove a label is false.
- Agreement only changes AUDIT PRIORITY (which items a human looks at first). That is all.

This is "triage only." Triage means sorting by risk, not deciding truth.

Using models from different providers, with different training lineage, lowers the chance
that they all make the same mistake at once (correlated error). That is a reason to trust
the triage sort a little more. It is NOT a reason to treat model votes as human evidence.
Model votes never become human evidence.

## Compute rule for these roles

- These three roles run on REMOTE models only (Bedrock or another remote provider).
- No local CPU neural workload. Ever.
- Bedrock and any other remote model here are "teacher/proposal language only" — they
  propose; they do not decide.
- The deterministic label engine, the source verifier, and the dataset scripts may run
  locally on CPU. Those are not neural workloads.
- AWS GPU is for hidden-state extraction, probing, intervention, training, and protected
  evaluation — NOT for these three labeler roles.

## How the three roles fit together

1. Each role runs its FIRST pass BLIND to the other two. Blind means a role does not see
   the other roles' outputs before it writes its own. This keeps the three views
   independent.
2. Every role writes its output into the `packet["evidence"]` schema (fields listed
   below). That output is NON-authoritative. It is recorded as evidence, nothing more.
3. The deterministic engine `deterministic_label_engine.py` reads only the frozen text
   (gloss, and frame if present) and recomputes which rule fires. It ignores any rule id a
   model proposed, except as a note in the evidence record.

## The evidence schema every role must fill

Every role output must match `packet["evidence"]` exactly. Fields:

- `model_id` — the exact remote model identifier.
- `model_role` — one of: `source_locator`, `adversarial_critic`, `counterexample_generator`.
- `source_locator` — the resource/sense pointer the model used or proposes.
- `exact_gloss` — the gloss text, quoted verbatim from the frozen resource.
- `frame_or_class` — the frame id (if any) or the CAS class the model proposes.
- `proposed_rule_id` — the mapping rule id the model suggests (advisory only).

The full LABEL_PACKET around this evidence block also carries: `packet_id`, `authority`,
`cas_label`, `claim_bearing` (derived, never passed in), `sense{...}`, `construction{...}`,
`fired_rules[]`, `blocked_rules[]`, `abstain_reason`, `surface{...}`, and `provenance{...}`.
The evidence block is one NON-authoritative part of that packet.

Reminder on the derived invariant (enforced in `label_common.make_packet`):
`claim_bearing == (authority in {CONSTRUCTION_GOLD, RESOURCE_GOLD, OWNER_CORRECTED})`.
It is computed, never supplied by a caller and never supplied by a model.

## The 4 CAS classes and rule ids

Labels apply to the SENSE-IN-CONTEXT, never to the bare spelling of a word.

- CAS-N2 `^2` Positive — affinity / attraction / preference / desire / approach TOWARD the
  object.
- CAS-N3 `^3` Negative — aversion / repulsion / avoidance / dread / rejection / withdrawal
  FROM the object.
  - ANTI-DRIFT: `^3` is VISCERAL, not analytical. Critique, scrutiny, and assessment are
    `^6`, and are EXCLUDED from `^3`.
- CAS-N6 `^6` Male — decomposition / analysis / separation into parts / structural
  inspection / testing.
  - ANTI-DRIFT: merely asking a question does NOT qualify. ask / question / inquire /
    query / wonder are EXCLUDED.
- CAS-N8 `^8` Above/Cause — one cue / event / Idea TRIGGERS another Idea or response to
  arise.
  - ANTI-DRIFT: not deduction; mere temporal sequence and ordinary communication do NOT
    qualify. deduce / infer / conclude / prove / say / tell / announce / state are
    EXCLUDED.

Source of these definitions: CLAUDE.md 10-Noetics (verbatim) plus
CAS_FOUNDATIONAL_CLARIFICATIONS Clarification 6; master charter `cas_reasoner.txt`.

## How the deterministic engine fires (models do not do this)

The engine normalizes the gloss (plus frame if present): lowercase; Unicode NFKD; each run
of non-alphanumeric characters becomes a single space; collapse spaces.

A rule fires for its class if and only if: at least one include term matches on a whole
word or whole phrase, AND no exclude term matches.

Across the 4 rules:
- exactly one fires -> RESOURCE_GOLD for that class.
- zero fire -> ABSTAIN with `abstain_reason = no_rule`.
- two or more fire -> ABSTAIN with `abstain_reason = multiple_rules`.
- caller-flagged source disagreement -> ABSTAIN with `abstain_reason = source_conflict`.

A model's `proposed_rule_id` is advisory evidence ONLY. The engine ALWAYS recomputes firing
from the frozen text. The rule table lives in `CAS_MAPPING_RULES_v1.yaml`.

---

# ROLE A — source_locator

## Purpose

Find where a sense actually lives in the frozen resource, quote the exact evidence, and
suggest which mapping rule might apply. This role gathers facts. It does not set labels.

## Prompt template

```
You are the source_locator. You gather source evidence for one sense. You do NOT
assign a final label. Your output is advisory evidence only.

INPUT:
  lemma: {lemma}
  pos: {pos}
  sense_id: {sense_id}
  gloss (from the frozen resource): {gloss}
  frame (if any): {frame}
  frozen resource name + digest: {resource_name} / {frozen_resource_digest}

TASK:
  1. Locate this exact sense id in the frozen resource named above. If it is not
     present, say NOT_FOUND and stop.
  2. Quote the gloss VERBATIM. Do not paraphrase. Do not fix spelling. Copy the
     bytes as they appear. This goes in exact_gloss.
  3. If a frame id is present, report it exactly. Do not invent a frame id.
  4. Propose which ONE of the 4 CAS classes the sense-in-context best matches:
     CAS-N2 ^2 Positive, CAS-N3 ^3 Negative, CAS-N6 ^6 Male, CAS-N8 ^8 Above/Cause.
     Apply the ANTI-DRIFT exclusions. If none fits, propose NONE.
  5. Propose the matching rule id from CAS_MAPPING_RULES_v1.yaml, or NONE.

RULES:
  - You label the SENSE-IN-CONTEXT, never the bare spelling.
  - You may not consult any source that is not the frozen resource above.
  - Your proposed_rule_id is advisory. A deterministic engine recomputes the real
    firing from the frozen text and can overrule you.

OUTPUT (match packet["evidence"] exactly):
  model_id, model_role="source_locator", source_locator, exact_gloss,
  frame_or_class, proposed_rule_id
```

---

# ROLE B — adversarial_critic

## Purpose

Try to break the candidate label. Look for a competing CAS class, point at ambiguity, and
challenge whether the quoted evidence really supports the proposed rule. This role protects
against over-confident labels.

## Prompt template

```
You are the adversarial_critic. Your job is to attack the candidate label, not to
confirm it. You do NOT assign a final label. Your output is advisory evidence only.

INPUT (you run BLIND to the other roles on your first pass):
  lemma: {lemma}
  pos: {pos}
  sense_id: {sense_id}
  gloss (verbatim, frozen): {gloss}
  frame (if any): {frame}
  candidate CAS class under review: {candidate_class}
  candidate rule id under review: {candidate_rule_id}

TASK:
  1. Name the strongest COMPETING CAS class for this sense-in-context, from
     CAS-N2 ^2, CAS-N3 ^3, CAS-N6 ^6, CAS-N8 ^8. Say why it could fit.
  2. Identify any AMBIGUITY: could a careful reader assign more than one class?
     Could this be a multi-label sense? Flag it plainly.
  3. Challenge the evidence: does the quoted gloss actually contain the include
     terms the candidate rule needs? Does any EXCLUDE term apply and defeat it?
     Apply the ANTI-DRIFT rules (^3 is visceral not analytical; a bare question
     is not ^6; deduction and ordinary communication are not ^8).
  4. Recommend: SUPPORTS_ONE_CLASS, or AMBIGUOUS (candidate for ABSTAIN). You
     recommend; you do not decide.

RULES:
  - Agreement or disagreement between models grants NO authority. Your critique
    only changes audit priority.
  - You may not consult sources outside the frozen resource.

OUTPUT (match packet["evidence"] exactly):
  model_id, model_role="adversarial_critic", source_locator, exact_gloss,
  frame_or_class (competing class or AMBIGUOUS), proposed_rule_id (or NONE)
```

---

# ROLE C — counterexample_generator

## Purpose

Show that the label is about sense-in-context, not spelling. Produce OTHER senses of the
same lemma that would take a different CAS class, or no class at all. If the same spelled
word has several meanings, the label must track the meaning, not the letters.

## Prompt template

```
You are the counterexample_generator. You produce other senses of the SAME lemma
to prove that labeling is sense-in-context, not spelling. You do NOT assign a final
label. Your output is advisory evidence only.

INPUT (you run BLIND to the other roles on your first pass):
  lemma: {lemma}
  pos: {pos}
  the sense under label: {sense_id} / {gloss}
  candidate CAS class: {candidate_class}

TASK:
  1. Give up to 3 OTHER senses of the same lemma (different meanings of the same
     spelled word).
  2. For each, state which CAS class it would take (CAS-N2 ^2, CAS-N3 ^3,
     CAS-N6 ^6, CAS-N8 ^8), or NONE, and why.
  3. Point out at least one other sense that would take a DIFFERENT class from
     the candidate, if one exists. This is the proof that spelling alone does
     not fix the label.
  4. If every sense of this lemma would take the same class, say
     SAME_CLASS_ACROSS_SENSES and note that the spelling/sense distinction is
     weak for this lemma.

RULES:
  - The counterexamples are illustrative evidence. They set no label.
  - Apply the ANTI-DRIFT exclusions when you assign classes to your examples.

OUTPUT (match packet["evidence"] exactly):
  model_id, model_role="counterexample_generator", source_locator,
  exact_gloss, frame_or_class, proposed_rule_id (or NONE)
```

---

## Worked example — the deterministic label DISAGREES with a wrong model proposal

This example makes the no-authority point concrete. A model proposes a label. The
deterministic engine returns something DIFFERENT. The engine wins.

Sense under label:
- lemma: `analyze`
- pos: verb
- gloss (frozen, verbatim): `to analyze something closely and critically`

Model A (source_locator) proposes:
- `frame_or_class`: CAS-N3 `^3` Negative
- `proposed_rule_id`: the `^3` rule
- reasoning the model gave: "critical" sounds negative, so this is aversion.

Why the model is WRONG:
- The `^3` ANTI-DRIFT rule says `^3` is VISCERAL (aversion, repulsion, dread), not
  analytical. Critique, scrutiny, and assessment are `^6`, and are EXCLUDED from `^3`.
- "analyze closely and critically" is decomposition and structural inspection. That is
  `^6` Male, not `^3`.

What the deterministic engine does (verified by running the engine on this gloss):
- It normalizes the gloss: `to analyze something closely and critically`.
- It checks the 4 rules against the frozen text.
- The `^3` rule does not fire, because the `^3` visceral include terms (for example
  `hate`, `detest`, `loathe`, `dread`, `shun`, `recoil`, `avoid`) are absent, and the
  analytical wording `analyze` is exactly the kind the `^3` exclude side is built to reject.
- The `^6` rule fires: the include term `analyze` matches (a decomposition / analysis
  term), and no `^6` exclude term (ask / question / inquire / query / wonder) is present.
- Exactly one rule fires -> the engine returns RESOURCE_GOLD for CAS-N6 `^6` Male.
- (Note: a gloss with bare `examine` instead of `analyze` would ABSTAIN with `no_rule`,
  because `examine` alone is NOT a `^6` include term — only phrases like `examine the
  parts` are. The include set is deliberately narrow; the engine never stretches it.)

Result:
- Final `cas_label` = `^6` (CAS-N6), authority = RESOURCE_GOLD (claim-bearing after audit).
- The model's `^3` proposal is kept in `packet["evidence"]` as a NON-authoritative record.
  It did not change the label. It only tells the auditor "a model disagreed here — look at
  this item sooner." That is triage, not authority.

If instead two rules had fired, or none had, the engine would have returned ABSTAIN
(`multiple_rules` or `no_rule`) and the item would be EXCLUDED with `cas_label = null` — no
matter how confident any model was.

## Abstain discipline and no quota rescue

Ambiguous or conflicting items get ABSTAIN and are EXCLUDED. Never broaden the include sets
or the class definitions to reach a round-number sample size. "Better 120 clean senses than
240 semantic puddles." If the smallest class cannot supply the frozen minimum without
ambiguous labels, the pipeline returns INSUFFICIENT_CLEAN_LABEL_COVERAGE. Do not rescue the
study.

## What this document does NOT establish

- It sets no CAS scientific claim. It is a deterministic label backbone plus the prompts
  that feed it.
- No model role here can set a claim-bearing label. Ever.
- The development pilot (46 dev senses -> 40 RESOURCE_GOLD + 6 ABSTAIN; coverage 0.8696;
  abstention 0.1304; source-verification failure rate 0.0; per-rule 10/10/10/10; 40
  construction-gold; 86 total packets; tests 19/19 pass; rule table sha256
  `5599780d2c1e3ffcb0cc71289f0a475d3a712465fdafa37147b8b0ebc256eb86`; dev resource sha256
  `740d72da8a6f5cca347ef816b40abcb3952e4a11c09b0c6896497c3d78dc5c24`) is development-only.
  It proved nothing scientific. It shows the plumbing runs, not that a CAS claim holds.

## Governance

Owner-signed phase approval. Deterministic claim promotion. No hook-based authorization. No
model-written claim status. Claude is NOT the research governor.
