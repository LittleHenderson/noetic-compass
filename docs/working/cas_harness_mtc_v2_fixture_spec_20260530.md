# CAS Harness MTC v2 Concrete-Scenario Fixture Specification

**Date:** 2026-05-30  
**Status:** Working doc only; not frozen, not WORM-anchored, not a pre-registration  
**Scope:** MTC v2 fixture design for Stage 9 40E and Stage 7 F28 matched-taxonomy controls  

## 1. Purpose

The MTC v2 fixture replaces the first marker-balanced MTC pilot fixture.

The prior pilot solved one problem and exposed another:

- The direct-wording fixture leaked labels through surface text.
- The marker-balanced fixture suppressed that leakage by showing all cue definitions in every prompt and cycling the selected marker independently of class.
- That overcorrected. GPT-NeoX-20B CAS-only recovery was effectively null: 40E best layer reached only 5.5%, and F28 landed at chance.

The correct interpretation is a fixture/configuration null, not a global CAS null. A matched-taxonomy specificity test is only meaningful after the fixture first makes the CAS distinction recoverable from hidden states without making it recoverable from prompt surface shortcuts.

MTC v2 must therefore use ordinary concrete scenarios. It must not expose TKS/CAS source-vocabulary class anchors, visible class badges, or a marker cue-card list in every prompt. At the same time, each row must still require the target CAS distinction by meaning.

## 2. Design Thesis

MTC v2 should make the model represent a practical distinction because the situation demands it, not because the prompt names the distinction.

Each prompt should look like a normal real-world vignette:

- A person, team, process, artifact, or institution faces a concrete situation.
- The situation contains a specific cognitive, procedural, evidential, relational, operational, or evaluative demand.
- The target CAS label is recoverable by interpreting what kind of demand the situation imposes.
- The wording does not contain the class name, a paraphrase of the class name, a symbolic badge, or a repeated cue list.

Plain English rule:

> The scenario should make a capable reader think, "This is the kind of problem where that distinction matters," without the scenario saying the distinction's name.

## 3. Non-Negotiable Constraints

### 3.1 No Source-Vocabulary Anchors In Prompt Text

The prompt body must not contain TKS/CAS source vocabulary that functions as a class anchor.

Forbidden in row-facing prompt text:

- CAS label names.
- TKS source terms.
- Foundation, Drive, Register, Noetic, Domain, operator, element, or similar taxonomy scaffolding terms when they reveal the label system.
- Class codes, symbolic tags, badges, or aliases.
- Obvious paraphrases that become stable class handles.

Allowed outside prompt text:

- Machine labels in hidden metadata.
- Assignment artifacts.
- Audit annotations.
- Fixture specification docs.

### 3.2 No Visible Class Badges

Rows must not include visible markers such as:

- `[A3]`, `Class 17`, `Pattern: X`, `Mode 4`, or similar tags.
- Repeated opening phrases assigned to a class.
- Stable character names, cities, products, colors, or object types that map to a class.
- Header blocks that tell the reader which class family is being tested.

If a surface classifier can learn a class from a badge, the fixture is invalid even when the badge is numerically balanced.

### 3.3 No Marker Cue-Card List In Every Prompt

MTC v2 must not repeat a full list of candidate cue definitions in each prompt.

The marker-balanced pilot made text leakage harder, but the repeated cue-card structure likely flattened the model's reason to represent the intended distinction. V2 should remove that artificial test format and return to ordinary prose.

### 3.4 Concrete Scenarios, Not Taxonomy Definitions

Each prompt must be a concrete situation, not an abstract definition or label-discrimination exercise.

Bad shape:

> A case involves reconciling symbolic structure with operational closure. Which class is this?

Good shape:

> A logistics supervisor notices that the same delivery route fails only when two handoff teams use different package counts. She asks the teams to trace the mismatch from the loading dock to the final scan before changing the schedule.

The good shape can carry a target distinction without naming it.

### 3.5 Meaning Must Carry The CAS Distinction

The target CAS label must be justified by the scenario's semantics. It is not enough for labels to be assigned by template position.

For every row, an author or reviewer should be able to answer:

- What concrete situation is happening?
- What demand makes the CAS label appropriate?
- What plausible neighboring CAS label might be confused with it?
- What sentence-level evidence resolves that confusion?
- Which ordinary non-CAS comparator label also applies, and why is it not just a copy of the CAS label?

## 4. Fixture Shape

### 4.1 Pilot Size

Minimum pilot:

- 40E: 40 classes x 25 rows/class = 1,000 rows.
- F28: 28 classes x 25 rows/class = 700 rows.

### 4.2 Confirmatory Size

Full confirmatory target:

- 40E: 40 classes x 100 rows/class = 4,000 rows.
- F28: 28 classes x 100 rows/class = 2,800 rows.

### 4.3 Required Row Fields

Rows should carry both CAS and matched non-CAS labels before activation capture.

Sketch:

```json
{
  "id": "mtc_v2_40e_train_000001",
  "prompt": "Ordinary concrete scenario text only.",
  "expected_cas_axes": {
    "operator": "^0..^9",
    "domain": "P|C|E|O",
    "element": "^i|D",
    "drive": "F1..F7",
    "register": "T|A|f|E",
    "foundation": "FjR"
  },
  "control_semantic": {
    "topic_40": "healthcare|education|commerce_finance|civic_admin|...",
    "frame_40": "classification|causal_explanation|procedure|tradeoff_decision|risk_mitigation",
    "topic_7": "medical_care|learning_assessment|...",
    "function_4": "describe_state|explain_cause|choose_action|evaluate_risk"
  },
  "metadata": {
    "split": "train|test",
    "fixture_family": "mtc_v2_concrete_scenario",
    "authoring_rule": "ordinary concrete scenario; no visible CAS/TKS anchors"
  }
}
```

The schema above is illustrative for this working doc. Implementation details belong in code only after this design is accepted.

## 5. Authoring Pattern

Each prompt should have a consistent ordinary-world form without becoming a class template.

Recommended structure:

1. One concrete setting.
2. One actor or group with a practical goal.
3. One constraint, mismatch, ambiguity, failure, tradeoff, or decision.
4. One action, observation, or requested judgment that forces the intended distinction.

Example neutral prompt ending:

> What is the main kind of reasoning or response the situation calls for?

This kind of ending asks for meaning without listing labels. If generation uses prompt-only activation capture and no answer text, the ending can be omitted or kept as a neutral continuation cue. The important rule is that the prompt must not expose the answer set.

## 6. Lexical Balance Rules

The text baseline must stay low because the fixture avoids shortcuts, not because the task is incoherent.

Controls:

- Rotate topics across every CAS class.
- Rotate frames across every CAS class.
- Rotate actors, settings, artifacts, verbs, and problem types across classes.
- Avoid repeated class-specific stems.
- Avoid one class always being written as healthcare, another as finance, another as school, etc.
- Include near-neighbor rows where similar surface topics map to different CAS labels because the underlying demand differs.
- Include same-label rows across different topics and frames.

Bad lexical balance:

- One target class always mentions audits.
- One target class always mentions therapy.
- One target class always uses "forecast."
- One target class always starts with "The coordinator compares..."

Good lexical balance:

- The same topic sector appears across many CAS labels.
- The same action verb can appear in multiple labels.
- The same CAS label appears in different topics and ordinary event frames.

## 7. Acceptance Gates

MTC v2 must pass gates in order. Later gates are not interpretable if earlier gates fail.

### Gate 1: Text Baseline Ceiling

Before GPU activation capture:

- Run text-only classification for every claim-bearing CAS label set and matched taxonomy label set.
- Required ceiling: text baseline accuracy `<= 60%`.
- If any claim-bearing label set exceeds 60%, stop and rewrite the fixture.

Verdict if failed:

`BLOCKED_TEXT_BASELINE_TOO_HIGH`

Plain English:

> If a cheap text classifier can solve the row labels from words on the page, the fixture is leaking the answer.

### Gate 2: CAS Recoverability Floor

Before matched controls matter:

- Capture hidden states.
- Run CAS-only recovery for the claim-bearing CAS label set.
- Required floor: CAS hidden readout lift over its own text baseline must be at least `+20 percentage points`.

This gate applies before matched taxonomy specificity. If CAS itself is not recoverable, there is no fair specificity comparison.

Verdict if failed:

`BLOCKED_CAS_NOT_RECOVERABLE`

Plain English:

> If hidden states do not recover the CAS distinction on this fixture, the fixture cannot test whether CAS beats matched alternatives.

### Gate 3: Matched Taxonomy Specificity

Only after Gate 1 and Gate 2 pass:

- Compare CAS lift over text against matched non-CAS taxonomy lift over text.
- Compare flat lacunarity against matched alternatives.
- For F28, compare nested structure against the coherent non-CAS 7 x 4 nested taxonomy.
- Keep scrambled-label and permutation-null controls.

This gate asks the actual MTC question:

> Is CAS cleaner than serious same-size semantic alternatives on the same activations, splits, probe family, and scoring code?

Verdicts should follow the MTC pre-registration vocabulary: `PASS`, `PARTIAL`, `GREY`, `FAIL`, or `BLOCKED`.

## 8. Good Scenario Examples

These examples are intentionally plain English. They do not include class badges or cue-card lists.

### Good 40E-Style Scenario A

> A clinic manager sees that appointment delays are worst on days when lab results arrive after the doctor has already opened the visit note. She asks the front desk, nurses, and lab vendor to reconstruct the handoff sequence so the team can decide whether to change scheduling rules or result-routing rules.

Why it is good:

- It is concrete.
- It does not name a CAS class.
- The distinction depends on the kind of operational mismatch and response demanded.
- The same healthcare topic could be reused for different target labels with different underlying demands.

### Good 40E-Style Scenario B

> A city repair crew receives conflicting reports about a bridge sensor. One report says the sensor is broken, another says the bridge moved during heavy rain, and a third says the maintenance software rounded the reading differently after an update. The supervisor asks for a short account of what would have to be true in each case before sending a crew.

Why it is good:

- The scenario forces a meaning-level distinction among possible explanations.
- The topic is ordinary civic infrastructure, not a taxonomy cue.
- No visible source-vocabulary anchor appears in the prompt.

### Good F28-Style Scenario A

> A teacher notices that a student can solve practice problems when shown the first step but freezes on new examples. Instead of adding more drills immediately, she asks the student to explain what he checks first, what he ignores, and where he decides the problem has changed.

Why it is good:

- It expresses a concrete learning and response pattern.
- It can carry a drive/register distinction through behavior and context.
- It does not display the drive or register names.

### Good F28-Style Scenario B

> A product team is deciding whether to delay a release after a small group of users reports data loss. The engineer wants more logs, the support lead wants to warn customers now, and the manager asks the team to separate reversible annoyances from failures that could permanently harm users.

Why it is good:

- The target distinction is required by the meaning of risk, action, and evaluation.
- The same software-release topic could support multiple labels if the practical demand changes.
- The prompt remains ordinary prose.

## 9. Bad Scenario Examples

### Bad: Visible Class Anchor

> This case is an example of a Foundation-Register interaction. The correct class is F3A. A team decides how to respond to a customer complaint.

Why it is bad:

- It exposes the label family.
- It includes a visible class badge.
- A text classifier can solve it without understanding the scenario.

### Bad: Source-Vocabulary Paraphrase

> The analyst performs recursive noetic integration across the operational domain while preserving the closure of the symbolic structure.

Why it is bad:

- It is abstract taxonomy prose, not an ordinary scenario.
- It uses source-vocabulary-like wording as the class signal.
- It is likely to be unrecoverable as a concrete model-internal distinction or trivially recoverable as jargon.

### Bad: Cue-Card List

> The possible patterns are: pattern one means checking evidence, pattern two means choosing action, pattern three means emotional adjustment, pattern four means procedural repair. In this row the selected marker is pattern two.

Why it is bad:

- It repeats the answer set inside the prompt.
- It recreates the marker-balanced overcorrection.
- The model can treat the prompt as a list-manipulation task instead of representing the ordinary situation.

### Bad: Stable Topic-To-Class Shortcut

> Every hospital scenario maps to one class, every school scenario maps to another class, every bank scenario maps to a third class, and every software scenario maps to a fourth class.

Why it is bad:

- Topic becomes the label.
- The matched non-CAS taxonomy is confounded with the CAS label.
- The text baseline can learn the shortcut.

### Bad: Too Generic To Demand The Distinction

> A team has a problem and discusses what to do next.

Why it is bad:

- It is ordinary but under-specified.
- Multiple labels could fit with no evidence.
- If hidden readout fails, the failure would be a fixture ambiguity, not evidence against CAS.

## 10. Review Rubric

Each row should pass this checklist before inclusion:

- The prompt is understandable without knowing CAS or TKS.
- The prompt contains no visible class code, class badge, marker, or cue-card list.
- The prompt contains no TKS/CAS source-vocabulary anchor.
- The intended CAS label is justified by scenario meaning.
- At least one near-neighbor label was considered.
- The matched non-CAS label is independently justified.
- Topic, actor, and wording do not create a stable shortcut.
- The row would still make sense if moved into a normal benchmark dataset.

Fixture-level checklist:

- Every class is balanced by row count.
- Train/test split is class-balanced and fixed before scoring.
- Topic sectors are distributed across CAS labels.
- Event frames are distributed across CAS labels.
- No class has a distinctive repeated phrase stem.
- Text baseline is measured before activation capture.
- CAS recoverability is measured before matched specificity is interpreted.

## 11. Claim Discipline

Before gates pass, say:

> MTC v2 is a redesigned fixture intended to test matched-taxonomy specificity without surface label leakage or marker-list overcorrection.

If Gate 1 passes but Gate 2 fails, say:

> The v2 fixture passed the text-leakage ceiling but did not make CAS recoverable from hidden states. This is a fixture/configuration null for specificity testing.

If Gate 1 and Gate 2 pass but matched controls win or match CAS, say:

> CAS is recoverable on this fixture, but this run does not license a CAS-specific claim over matched semantic taxonomies.

Only if all gates pass, say:

> On this fixture and model, CAS is recoverable from hidden states and factorizes the representation more cleanly than matched same-size semantic alternatives under the pre-registered scoring rules.

## 12. Immediate Next Work

1. Draft a small human-reviewed scenario seed set for 40E and F28 using the rules above.
2. Check the seed set manually for source-vocabulary leakage and topic-to-class shortcuts.
3. Expand by controlled variation across topics, frames, actors, and near-neighbor distinctions.
4. Run the text baseline before any 20B activation capture.
5. Stop unless text baseline is `<= 60%`.
6. After capture, stop unless CAS hidden readout lift is `>= +20 pp` over text.
7. Only then run matched taxonomy specificity.

