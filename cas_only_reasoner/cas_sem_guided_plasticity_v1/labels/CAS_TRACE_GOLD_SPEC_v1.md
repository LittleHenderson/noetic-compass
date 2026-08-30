# CAS Trace Gold Spec v1

Part of LABEL PHASE 0C. Documentation only; not claim-bearing. Specification only — NOT
implemented in this phase.

## 1. Why this spec exists

The Phase 0B construction generator was CIRCULAR: each class picked verbs from its own
list, and the round-trip checker used the same `VERB_TO_CLASS` table to read the class
back. The loop (class selects verb → sentence contains verb → same table reads class back
→ round trip passes) proves the lookup table agrees with itself, nothing more. Some `^8`
outputs ("The analyst triggered the device.") were generic physical causation — not one
Idea bringing another Idea to Mind, which is what `^8 Above/Cause` means. That generator is
retired to `CONTROLLED_TEMPLATE_FIXTURE` (unit tests only; the promotion program refuses
it).

This spec defines the replacement: **Tier A ground truth by construction from formal CAS
traces**, with an independent preservation check.

## 2. The pipeline

```
formal CAS state or CNCM trace
    -> CAS-Sem graph
    -> controlled language realization (deterministic lane)
    -> optional AI paraphrase (secondary lane)
    -> INDEPENDENT preservation checks
    -> CONSTRUCTION_CANDIDATE packet
    -> generator audit + owner-signed promotion
    -> CONSTRUCTION_GOLD (claim-bearing)
```

The core label comes from the formal state, the transition, the trace, and the CAS-Sem
role graph — it exists BEFORE any English is produced. No human annotator labels items.

## 3. Full typed records

Each item carries the full CAS state, not just a class tag:

```
noetic        (what:  ^2 / ^3 / ^6 / ^8 for the four-class study)
domain        (where: P / C / E / O)
drive         (why:   F1..F7)
register      (how:   T / A / f / E)

cause, bias, effect

CAS-Sem entities, CAS-Sem relations, semantic roles

source trace id, generator digest, surface realization
```

The four axes (what/where/why/how) are the CAS state definition from the master charter
(`cas_reasoner.txt`). This is more CAS-specific than four verb synonym buckets.

## 4. Preventing trivial lexical decoding

The generator MUST avoid: one exclusive verb list per class; one template per class; one
obvious keyword that gives away the label. It MUST use:

- shared vocabulary across classes (the same word appears in several contexts where the
  formal operation differs);
- several templates per operation;
- held-out template families and held-out vocabulary;
- balanced sentence length and balanced noun/verb frequencies;
- surface-matched minimal pairs;
- multiple paraphrase generators (for the secondary lane).

The label comes from the underlying trace, not from the spelling.

## 5. The independent preservation check (the anti-circularity rule)

Generation and verification MUST be separate components that share NO verb-to-class
lookup:

```
Generator:            formal trace -> surface sentence
Checker:              surface sentence -> CAS-Sem candidate (independent implementation)
Comparator:           recovered CAS-Sem graph vs seed graph
Adversarial critic:   searches for another valid interpretation (model role, advisory)
```

Enforced in code: any packet whose `provenance.preservation_check` equals
`"shared_verb_lookup"` is refused by the promotion program (`FIXTURE_NOT_PROMOTABLE`).
The new checker must record its own implementation digest in provenance, distinct from
the generator's.

For deterministic primary items, use tightly controlled language. For AI paraphrases, any
unresolved disagreement produces `ABSTAIN`.

## 6. The ^8 rule (the hardest class)

Every accepted `^8` seed must represent one Idea, event, or cue causing ANOTHER IDEA OR
RESPONSE TO ARISE in a Mind. Generic physical causation ("triggered the device", "caused
the leak") does NOT qualify. The CAS-Sem graph of an `^8` item must contain a cue entity
and an arising-idea/response entity, and the comparator must verify both survive
realization.

## 7. What Tier A feeds

The first claim-bearing experiment is not merely "can a probe read a label." It is:

> Does CAS-structured supervision help the same Transformer learn a controlled task with
> fewer examples or less forgetting than matched generic and shuffled structures?

Conditions: (A) ordinary training; (B) random labels, matched dimensions; (C) generic
semantic structure; (D) CAS Noetic structure; (E) full CAS Noetic+Domain structure;
(F) shuffled CAS structure. Only the final behavioral result matters. Claim boundaries per
`LABEL_CLAIM_BOUNDARY.md`: only Claim B licenses "CAS-specific". Stop after Claims A and B
before attempting intervention or CAS-Ohm.

## 8. Status

Specification only. Implementation requires owner approval of this spec, of
`PREREGISTRATION_v0_3B_CANDIDATE.md`, and a signed phase approval. No neural work, no
generation run, no GPU in this phase.
