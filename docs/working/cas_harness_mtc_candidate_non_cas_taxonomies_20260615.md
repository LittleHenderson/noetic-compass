# Candidate Non-CAS Taxonomies For CAS/TKS Matched Controls

Date: 2026-06-15  
Status: working design note  
Purpose: list concrete non-CAS comparators that can be used against CAS/TKS-definition fixtures instead of arguing by assertion.

## Plain Rule

A matched-control taxonomy does not need to be another compiler-backed CAS/TKS DSL.

For hidden-state CAS/TKS specificity, the control needs to test a narrower question:

> Is the model recovering CAS/TKS structure specifically, or is it recovering any coherent human-meaning taxonomy present in the scenario text?

The comparator should be:

- non-CAS / non-TKS
- fixed before the run
- externally grounded where possible
- close in class count
- labelable from the same plain-English scenario
- stripped of obvious answer-key words
- run through the same text-baseline, hidden-readout, and matched-control gates

## Best First 40-Class Comparator

### `mft5_diamonds8_40`

Build a 40-class control from:

- Moral Foundations Theory, five-foundation version:
  - `care_harm`
  - `fairness_cheating`
  - `loyalty_betrayal`
  - `authority_subversion`
  - `sanctity_degradation`
- DIAMONDS Situational Eight:
  - `duty`
  - `intellect`
  - `adversity`
  - `mating`
  - `positivity`
  - `negativity`
  - `deception`
  - `sociality`

Cross-product:

```text
5 moral foundations x 8 situation dimensions = 40 labels
```

Example labels:

```text
care_harm__duty
fairness_cheating__deception
authority_subversion__sociality
sanctity_degradation__adversity
```

Why this is the best first comparator:

- It is non-CAS and non-TKS.
- It directly covers ethics plus situation structure.
- It is exactly 40 classes, matching the CAS/TKS 40E axis.
- It is interpretable enough for blind human raters.
- It does not require inventing a fake alternative DSL.

Use this against the CAS/TKS 40E line before trying weaker controls.

## Other Useful Controls

### `schwartz10_values`

Use Schwartz basic human values as a 10-class comparator against the 10 Noetic axis, not as a direct 40E comparator.

Candidate labels:

```text
self_direction
stimulation
hedonism
achievement
power
security
conformity
tradition
benevolence
universalism
```

Use when testing whether a 10-way hidden readout is CAS/TKS Noetic structure or generic value/motivation structure.

### `mac7_morality_as_cooperation`

Use Morality-as-Cooperation as a 7-class moral comparator against drive-like or foundation-like claims.

Candidate labels:

```text
family
group_loyalty
reciprocity
bravery
deference
fairness
property
```

Use against 7-drive claims or as one side of a future 28-class control only if a non-CAS four-mode axis is selected and preregistered.

### `hexaco6_or_facets`

Use HEXACO personality dimensions or facets only as a lower-priority psychological control.

Candidate six domains:

```text
honesty_humility
emotionality
extraversion
agreeableness
conscientiousness
openness
```

This is useful for checking whether CAS/TKS readout is just broad personality-style signal, but it is not the best ethics/situational comparator.

## Not Hidden-State MTC Controls, But Useful Prior-Art Comparators

These are not direct semantic taxonomies for the CAS/TKS hidden-state matched-control run. They are useful if the question is about the narrower "compiler-backed DSL" claim.

- LegalRuleML: formal legal/normative rules markup.
- eFLINT: domain-specific language for executable norm specifications.
- Scenic: domain-specific probabilistic scenario language.

These show that norm/scenario DSLs exist. They do not by themselves defeat the narrower claim that CAS/TKS is a distinctive compiler-backed BNF DSL for psychological ethics and situational ontology.

## Recommended Next Run

Build `mft5_diamonds8_40` first.

Run it as:

1. Create or relabel a plain-English scenario set where both CAS/TKS 40E and `mft5_diamonds8_40` labels are possible.
2. Remove literal CAS/TKS and MFT/DIAMONDS answer-key words.
3. Run a local text baseline.
4. Require blind meaning-preservation review.
5. Capture hidden states only after the surface gate passes.
6. Compare CAS/TKS 40E against `mft5_diamonds8_40` under the same probe method and split.

Passing condition should be preregistered. Do not claim CAS/TKS comparative specificity unless CAS/TKS beats the matched control by the preregistered margin.

