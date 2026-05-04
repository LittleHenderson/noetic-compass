# Level 3 Conversational v2 — Demographic and Tonal Axis Specification

Status: locked vocabulary for Phase 1 Tasks T2 (demographic axis) and T3 (tonal axis) of the Noetic Compass Version B conversational SDG track. The values defined here are canon for the T4 lexicon-builder agent and the T7 invariance enforcer. No new axes may be added under this spec; only the values listed below may be emitted by SDG.

## 1. Purpose and Scope

Version B of the Level 3 conversational dataset adds two surface-form axes on top of the existing CAS structural target. The structural CAS signal — `cas_expression`, `soft_operator_targets`, `soft_domain_targets`, `bucket`, and the underlying Noetic / Domain / Drive / Register decomposition — is already locked by Level 2 and the v1 Level 3 SDG spec. Version B does not change what the model learns structurally. It changes how the surface form of the user prompt and the assistant response can vary while the structural target stays fixed.

Two new optional schema blocks carry the variation:

- `demographic_profile` — a five-axis specification of who the surface speaker is, modeled as linguistic and contextual variation. These are not identity claims about the underlying user. They are surface markers the SDG paraphrase generator must respect when rendering the conversational turn.
- `tonal_profile` — a four-axis specification of how the turn sounds, covering emotional register, conversational distance, urgency, and speaker register.

Both blocks are optional. v1 Level 3 records remain valid under v2. When either block is present, every axis listed under that block must be present and must take a value from the closed vocabulary defined here.

The motivating problem is that v1 Level 3 paraphrase coverage is structurally narrow. The same CAS state surfaces in only a handful of surface forms, dominated by middle-class, neutral-register, calm, professional voicings. The CAS-Native model has learned to map a narrow surface distribution to the structural target and is brittle on out-of-distribution surface forms that carry the same structural CAS content. Locking demographic and tonal vocabularies, then driving SDG to systematically cover the cross-product, expands surface coverage without changing structural supervision.

## 2. Load-Bearing Invariant

The single load-bearing invariant for Version B is:

> Demographic and tonal axis values MUST NOT change `cas_expression`, `soft_operator_targets`, or `soft_domain_targets`. They only change surface form.

The same CAS structural state can be uttered by a calm older professional in formal British English and by an agitated young adult in AAVE in an urban setting and by a resigned middle-aged speaker in rural southern US English. All three records share the same `cas_expression`, the same `soft_operator_targets` vector, the same `soft_domain_targets` vector, and the same `bucket`. Only the surface text — `user_prompt`, `assistant_response`, `follow_up_question`, `natural_language_mapping` — varies, plus the new `demographic_profile` and `tonal_profile` blocks.

T7 enforces this invariant. T7 takes a v1 Level 3 record as the structural anchor, generates N v2 records that vary only on demographic and tonal axes, and rejects any v2 record whose structural targets diverge from the anchor by more than the floating-point tolerance already used by the v1 validator (`abs(sum - 1.0) <= 0.001` per soft target, exact equality on `cas_expression` and `bucket`). Any drift in structural targets across a paraphrase family is treated as a generation defect, not as legitimate variation.

This invariant exists because surface-form variation is not the same kind of signal as structural variation. Structural variation is the supervision target. Surface variation is the input distribution. Confounding the two would re-introduce the v1 problem at higher resolution: the model would learn that a particular demographic or tonal profile correlates with a particular CAS state, when the design intent is the exact opposite — that any CAS state can be expressed under any demographic and tonal profile.

A secondary invariant follows from the first: demographic and tonal axes are not training targets. The CAS-Native model is not asked to predict `demographic_profile` or `tonal_profile` from `user_prompt`. These blocks are SDG metadata used to drive surface coverage, validate paraphrase invariance, and audit dataset balance. They do not appear in the model's loss.

## 3. Demographic Profile — five axes

`demographic_profile` is a JSON object with exactly five required keys when present. Each key takes a value from a closed vocabulary defined below. The vocabularies were chosen to model linguistic and contextual surface variation that legitimately changes prompt phrasing while preserving structural CAS content. They are deliberately not racial, ethnic, or national-identity labels.

### 3.1 `age_band` (5 values)

Age band controls vocabulary register, slang density, cultural reference frame, and stance toward institutions. It is a coarse band, not a precise age.

- **`youth`** — adolescent surface register, 13-17 equivalent. High slang density, peer-oriented framing, school as default institution, parents as authority frame. Surface phrases: "my friends would think I'm weird," "my mom would freak out if she knew," "in class today."
- **`young_adult`** — 18-29 equivalent. College, early career, dating, roommates, student debt, identity-formation themes. Slang present but more current than `youth`. Surface phrases: "trying to figure out my next move," "my roommate said," "honestly I'm just over it."
- **`adult`** — 30-44 equivalent. Career mid-stage, partnership, young children, mortgage, professional networks. Surface phrases: "balancing this with my kid's schedule," "I've been at this job five years and," "my partner and I."
- **`middle_aged`** — 45-59 equivalent. Career senior stage, teenage or adult children, aging parents, retirement planning, health more salient. Surface phrases: "my kids are out of the house now," "since my dad's diagnosis," "at this stage of my career."
- **`older_adult`** — 60+ equivalent. Retirement, grandchildren, fixed income, long memory of historical context, health and mobility salient. Surface phrases: "in my day we used to," "since my husband passed," "my grandkids tell me."

### 3.2 `dialect_family` (8 values)

Dialect family is a linguistic-variety axis, not a racial or ethnic identity axis. The eight values cover major English dialect surface markers the SDG must handle without confounding them with the speaker's race, nationality, or class. A speaker of any racial or national identity may use any dialect family; the value records the surface variety of the utterance, not the demographic attribution of the speaker.

- **`general_american`** — neutral US English, low regional marking, broadcast-standard. Surface phrases: "I think," "kind of," "you know what I mean."
- **`aave`** — African-American Vernacular English, including habitual `be`, copula deletion, double negation, lexical markers. Authenticity is reviewer-gated (see Open Questions). Surface phrases: "she be telling me," "ain't nobody got time," "this how it is."
- **`southern_us`** — US southern surface markers: `y'all`, `fixing to`, drawl-marking spelling like `gonna` / `wanna`, hospitality framing. Surface phrases: "y'all," "fixin' to," "bless your heart."
- **`british`** — UK English including BrE spelling and lexicon, understatement framing. Surface phrases: "I reckon," "having a bit of a moment," "rather," "queue."
- **`south_asian_english`** — Indian / Pakistani / Bangladeshi / Sri Lankan English surface markers: progressive use with stative verbs, `only` as emphatic, code-switched politeness markers. Surface phrases: "I am having," "kindly do the needful," "only," "no?"
- **`east_asian_english`** — second-language surface patterns from Mandarin / Cantonese / Japanese / Korean L1 backgrounds: article omission, topic-comment ordering, polite hedging. Surface phrases: "I think maybe," "is little bit difficult," "actually."
- **`latino_us`** — US Latino English surface markers: code-switched Spanish lexical items, calque structures, family-orientation framing. Surface phrases: "tia said," "no manches," "my abuela," "for real."
- **`west_african_english`** — Nigerian / Ghanaian / Cameroonian English surface markers: `o` particle, `now-now`, pidgin-adjacent lexicon, communal framing. Surface phrases: "I'm coming now-now," "this thing eh," "abi?"

### 3.3 `gender_register` (4 values)

Gender register is a surface-marker axis for how the utterance is voiced, not an identity claim about the speaker. The label records which set of stylistic markers the surface text uses.

- **`feminine`** — surface markers conventionally associated with feminine voicing: hedging tags, intensifiers like `so`, social-relational framing. Surface phrases: "I just feel like," "literally," "she was so sweet about it."
- **`masculine`** — surface markers conventionally associated with masculine voicing: declarative framing, lower hedge density, action-orientation. Surface phrases: "look," "yeah," "we just got it done."
- **`neutral`** — register-flat, no strong markers in either direction, broadcast-style. Surface phrases: "I think," "the situation is," "what I'd say is."
- **`non_binary`** — explicit non-binary surface markers when the prompt context warrants them: `they/them` self-reference, unmarked-gender framing, identity-aware vocabulary. Surface phrases: "as a non-binary person," "my partner — they," "I use they/them."

### 3.4 `socioeconomic_register` (4 values)

Socioeconomic register controls vocabulary, abstraction level, institutional reference frame, and topic salience. It is a register axis, not a wealth claim.

- **`working_class`** — concrete vocabulary, immediate-time framing, hourly-wage and physical-job reference frame, non-academic institutions. Surface phrases: "after my shift," "the bills are due," "my supervisor said."
- **`middle_class`** — moderate vocabulary, salaried-job reference frame, suburban institutional default, mortgage and college as recurring topics. Surface phrases: "my manager," "we're saving up for," "the kids' school."
- **`professional_class`** — higher abstraction, white-collar reference frame, professional-network framing, optimization vocabulary. Surface phrases: "my team," "the strategic angle," "stakeholders."
- **`academic`** — highest abstraction density, theory and citation framing, conference and publication reference frame, register-marked hedges. Surface phrases: "as the literature suggests," "in my view, and others have argued," "the framing here."

### 3.5 `regional_setting` (3 values)

Regional setting controls institutional defaults, transportation framing, density-of-contact assumptions, and infrastructure salience.

- **`urban`** — city defaults: public transit, neighborhood density, anonymous-stranger contact, apartment living. Surface phrases: "on the train this morning," "my building," "the corner store."
- **`suburban`** — suburb defaults: car commute, single-family home, school district as identity frame, chain retail. Surface phrases: "the drive in," "our neighborhood," "the soccer game."
- **`rural`** — rural defaults: long drives, agricultural or extractive industry presence, small-town institutional density, weather salience. Surface phrases: "the drive into town," "out at the farm," "everybody knows everybody."

## 4. Tonal Profile — four axes

`tonal_profile` is a JSON object with exactly four required keys when present. Each key takes a value from a closed vocabulary defined below. Tonal axes are orthogonal to demographic axes — any tonal value may co-occur with any demographic value, subject to T7 invariance enforcement on the structural targets.

### 4.1 `emotional_register` (7 values)

Emotional register is the dominant felt-tone of the utterance. Note this is the **surface** affect of the speaker, not a CAS Affective Register classification (`|f`); the CAS Register axis is encoded in `cas_expression`. Emotional register can co-occur with any CAS Register including `|A` Analytical and `|T` Transcendent.

- **`calm`** — low arousal, even pacing, hedged stance, no urgency markers. Surface phrases: "I've been thinking about," "it's not a big deal but," "I'm okay with."
- **`warm`** — positive valence, relational openness, generous framing, affectionate markers. Surface phrases: "I really appreciate," "that's so kind of you to," "honestly I love that."
- **`distressed`** — negative valence, elevated arousal, stress markers, help-seeking framing. Surface phrases: "I don't know what to do," "I've been crying about this," "I'm just so worried."
- **`agitated`** — high arousal, irritation or anger markers, sharper sentence structure, lower hedge density. Surface phrases: "I cannot believe," "honestly fed up with," "this is ridiculous."
- **`resigned`** — negative valence, low arousal, futility markers, acceptance-of-bad-state framing. Surface phrases: "I guess that's just how it is," "nothing I can do," "whatever, it is what it is."
- **`curious`** — open stance, question-density elevated, exploration framing, low defensiveness. Surface phrases: "I wonder if," "what would happen if," "I'm trying to understand."
- **`skeptical`** — guarded stance, doubt markers, evidence-seeking framing, low affirmation density. Surface phrases: "I'm not so sure," "is that actually," "that doesn't quite track for me."

### 4.2 `conversational_distance` (5 values)

Conversational distance is how socially close the speaker positions the listener. It controls disclosure depth, name-use, idiom density, and politeness markers.

- **`intimate`** — disclosure depth high, names and pet-names present, low politeness scaffolding, idiom and inside-reference density high. Surface phrases: "babe," "I haven't told anyone this but," "you know how I get."
- **`familiar`** — friend or close-colleague distance, first names, casual idioms, moderate disclosure. Surface phrases: "hey, so," "you know me," "long story short."
- **`collegial`** — workplace-peer distance, last names or first-names-with-context, professional vocabulary, moderate politeness. Surface phrases: "I wanted to run something by you," "in our last sync," "from my side."
- **`formal`** — institutional distance, titles, full hedging, low idiom density, explicit politeness scaffolding. Surface phrases: "I would like to inquire about," "thank you for your time," "please advise."
- **`adversarial`** — opposed-stance distance, low or absent politeness, contestation markers, accusatory or defensive framing. Surface phrases: "you're not actually saying," "with respect, that's wrong," "I disagree with the premise."

### 4.3 `urgency` (4 values)

Urgency is the perceived time-pressure of the utterance. It controls sentence length, hedge density, repetition, and request-directness.

- **`low`** — no time pressure, full hedging, exploratory pacing. Surface phrases: "whenever you have a moment," "no rush on this," "just thinking out loud."
- **`moderate`** — soft time pressure, normal pacing, light specificity about timing. Surface phrases: "by end of week ideally," "when you get a chance today," "trying to wrap this up."
- **`high`** — strong time pressure, shorter sentences, explicit deadline framing, lower hedge density. Surface phrases: "I need this by tonight," "this is due in an hour," "can we do this now."
- **`acute`** — emergency framing, fragmented sentences, explicit crisis markers, repetition of the core ask. Surface phrases: "I need help right now," "please," "this is urgent please."

Note: `acute` does not entail crisis-content or self-harm content; it records surface urgency only. CAS structural framing is unchanged. Crisis-content classification is a separate orthogonal pipeline already covered by the v1 assistant_response safety gates.

### 4.4 `speaker_register` (4 values)

Speaker register is the load-bearing axis for Version B. It records the operational character of the speaking voice and is the surface complement to the CAS Register axis (`|T` / `|A` / `|f` / `|E`) carried inside `cas_expression`. The two are deliberately allowed to differ — a `visceral` speaker register may legitimately surface a `|A` Analytical CAS state, and a `formal` speaker register may legitimately surface an `|f` Affective CAS state. The cross-product is a primary source of Version B coverage.

- **`formal`** — full hedges, complete sentences, professional vocabulary, low colloquialism density, explicit grammatical scaffolding. Surface phrases: "I would like to articulate," "the position I am taking is," "in light of the foregoing."
- **`casual`** — colloquial vocabulary, contractions, sentence fragments acceptable, idioms present, hedges informal. Surface phrases: "yeah so," "kinda like," "honestly I just."
- **`professional`** — workplace-standard vocabulary, structured sentences, jargon present where domain-appropriate, polished but not maximally formal. Surface phrases: "from my perspective," "the consideration here is," "what I'd recommend."
- **`visceral`** — body-anchored vocabulary, sensorimotor and affective lexical density, directness, low hedging, gut-response framing. Surface phrases: "my stomach dropped," "I felt it in my chest," "something just clicked." `visceral` is the canonical surface complement to the CAS `|E` Embodied Register but is independent of it; CAS Register lives in the structural target.

## 5. Schema diff for `cas-synthetic/schemas/level3_conversation.schema.json`

The following additions are proposed for Version B. Do NOT edit the schema file itself as part of this spec; the schema patch will land in T8 once T2/T3/T4/T7 are integrated. The diff is shown verbatim here for the lexicon-builder and validator agents to plan against.

Two new optional top-level properties are added under `properties`:

```json
"demographic_profile": {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "age_band",
    "dialect_family",
    "gender_register",
    "socioeconomic_register",
    "regional_setting"
  ],
  "properties": {
    "age_band": {
      "type": "string",
      "enum": [
        "youth",
        "young_adult",
        "adult",
        "middle_aged",
        "older_adult"
      ]
    },
    "dialect_family": {
      "type": "string",
      "enum": [
        "general_american",
        "aave",
        "southern_us",
        "british",
        "south_asian_english",
        "east_asian_english",
        "latino_us",
        "west_african_english"
      ]
    },
    "gender_register": {
      "type": "string",
      "enum": [
        "feminine",
        "masculine",
        "neutral",
        "non_binary"
      ]
    },
    "socioeconomic_register": {
      "type": "string",
      "enum": [
        "working_class",
        "middle_class",
        "professional_class",
        "academic"
      ]
    },
    "regional_setting": {
      "type": "string",
      "enum": [
        "urban",
        "suburban",
        "rural"
      ]
    }
  },
  "description": "Optional v2 surface-marker profile for the speaker. Does not change structural CAS targets. Enforced by T7 invariance gate."
},
"tonal_profile": {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "emotional_register",
    "conversational_distance",
    "urgency",
    "speaker_register"
  ],
  "properties": {
    "emotional_register": {
      "type": "string",
      "enum": [
        "calm",
        "warm",
        "distressed",
        "agitated",
        "resigned",
        "curious",
        "skeptical"
      ]
    },
    "conversational_distance": {
      "type": "string",
      "enum": [
        "intimate",
        "familiar",
        "collegial",
        "formal",
        "adversarial"
      ]
    },
    "urgency": {
      "type": "string",
      "enum": [
        "low",
        "moderate",
        "high",
        "acute"
      ]
    },
    "speaker_register": {
      "type": "string",
      "enum": [
        "formal",
        "casual",
        "professional",
        "visceral"
      ]
    }
  },
  "description": "Optional v2 tonal profile. Does not change structural CAS targets. Enforced by T7 invariance gate."
}
```

Two new optional fields are added under `provenance.properties`:

```json
"demographic_axis_version": {
  "type": "string",
  "minLength": 1,
  "description": "Locked vocabulary version for demographic_profile. v2 spec ships as 2.0.0."
},
"tonal_axis_version": {
  "type": "string",
  "minLength": 1,
  "description": "Locked vocabulary version for tonal_profile. v2 spec ships as 2.0.0."
}
```

Both new top-level blocks are optional. v1 records remain valid. v2 records that include either block must include all required axes within that block. v2 records that include either block must also set the corresponding `*_axis_version` string under `provenance` so the dataset can be audited against this spec at any time.

## 6. T4 lexicon-builder canon

This section is the contract the T4 lexicon-builder agent depends on. T4 must:

1. Treat the enums in section 3 and section 4 as closed. T4 may not introduce new values, may not rename existing values, and may not collapse values. Adding a new dialect family or emotional register requires a new spec revision and a new `*_axis_version` string.
2. Use the surface phrases listed for each value as **seed entries**, not as the full lexicon. T4 expands each seed list to a target size (planned: roughly 40 entries per axis value, summing across both blocks to approximately 1880 seed entries) using the methodology in `cas_lexicon_scaling_methodology.md`.
3. Tag each lexicon entry with the axis and value it belongs to so T7 can audit which surface markers were used to generate any given Version B record.
4. Flag any axis-value combination that produces fewer than 20 plausible surface phrases for human review before lexicon lock. Combinations that legitimately produce few phrases should be flagged not silently dropped; the dataset balance plan handles low-frequency cells separately.
5. Pass authenticity-sensitive dialect families (`aave`, `south_asian_english`, `east_asian_english`, `latino_us`, `west_african_english`) through the reviewer gate flagged in Open Questions before lexicon lock.

## 7. T7 invariance enforcement

T7 is the gate that enforces the load-bearing invariant in section 2. The contract:

1. Group v2 records by `source_level2_id`. A "paraphrase family" is the set of v2 records sharing the same `source_level2_id` (and therefore the same v1 anchor).
2. Within a paraphrase family, assert: identical `cas_expression`, identical `bucket`, `soft_operator_targets` componentwise within `1e-3` tolerance, `soft_domain_targets` componentwise within `1e-3` tolerance.
3. Reject the family (not just the divergent member) if any of these checks fails. A family with structural drift is a generation defect; surface coverage gained by accepting drifted records is not worth the contamination cost.
4. Log rejection reasons by axis-value pair so T4 lexicon revisions can target specific entries that produced drift. A common failure mode is a lexicon entry that smuggles structural content into surface form (e.g., a `visceral` phrase that introduces an embodied claim absent from the v1 anchor); these are lexicon defects, not invariance defects, and must be corrected at the lexicon layer.
5. Maintain a paraphrase-family acceptance rate metric. Phase 1 target: at least 95% of generated paraphrase families pass the invariance gate. Below 90% indicates a lexicon-layer or generator-layer defect that must be addressed before T8 dataset release.

T7 does not enforce balance across the demographic-by-tonal cross-product. Balance is a separate concern handled by T6 (dataset balance plan). T7 enforces invariance only.

## 8. Open Questions

The following questions cannot be resolved without user judgment. They are listed here so the rollout sequence can incorporate user input before T4 lexicon lock.

1. **AAVE authenticity reviewer.** AAVE surface markers are linguistically well-attested but production datasets have a long history of generating offensive caricature when assembled without native-speaker review. The spec lists AAVE as a closed value to keep the vocabulary stable, but T4 lexicon expansion for AAVE must pass a native-speaker authenticity review before lock. Open question: who is the reviewer, and is this an internal hire, an external contractor, or a partnership with an existing AAVE-focused linguistics group? The same question applies in lower-stakes form to the other non-American dialect families.

2. **`non_binary` gender register prevalence.** `non_binary` is included to ensure the SDG can render non-binary speakers without forcing them into `feminine`, `masculine`, or `neutral`. Open question: what is the target frequency of `non_binary` in the dataset balance plan? Demographic accuracy (low-single-digit percent) competes with sufficient training signal for the model to learn the register reliably.

3. **`acute` urgency by crisis-content overlap.** `acute` is documented above as surface urgency only, with crisis-content handling left to the v1 assistant_response safety gates. Open question: should T4 explicitly avoid generating `acute` records that surface as self-harm or imminent-violence content, or should it generate them and rely on the v1 safety gates to constrain the assistant_response? The first option simplifies T4 and accepts a coverage gap; the second exposes T4 to a class of failure modes it was not designed for.

4. **Code-switch density caps.** Several dialect families (`aave`, `latino_us`, `west_african_english`) naturally code-switch with another language or register. Open question: should T4 cap the code-switch density per record (e.g., at most one Spanish phrase per `latino_us` record at moderate density, with a separate high-density variant), or let the lexicon set its own distribution? A cap is more controllable; an uncapped distribution is more authentic.

5. **`speaker_register=visceral` by CAS Register `|E` Embodied confound.** The spec explicitly allows `visceral` speaker register with any CAS Register, including non-`|E` registers. Open question: should T6 dataset balance enforce a minimum frequency of `visceral` by non-`|E` records to teach the model that visceral surface form does not entail embodied CAS state? Without enforced balance the model may learn the lazy correlation.

6. **Older-adult dialect interaction.** `older_adult` plus several dialect families produces surface markers that are historically time-locked rather than currently used (e.g., 1960s slang in older_adult plus general_american). Open question: should T4 lexicons be time-stamped within an age band, or should the time-stamping be an implicit property of the surface phrases T4 generates? Time-stamped lexicons are auditable; implicit time-stamping is simpler.

7. **`provenance.demographic_axis_version` and `tonal_axis_version` initial values.** The spec proposes both ship as `2.0.0`. Open question: should they be coupled (always upgraded together) or independent (each axis can revise without forcing the other)? Independent versioning is more flexible for future revisions; coupled versioning is simpler to audit. The default in this spec is independent.
