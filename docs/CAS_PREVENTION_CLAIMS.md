# CAS Prevention Claims — Conservative Subset

This file is a subset of the main incident database. An incident appears here only if **prevention** — not merely detection — is defensibly claimable based on the structural signature of the documented behavior.

**Detection** means the CAS framework would have flagged a risk. Detection is the default claim in the main database.

**Prevention** is a stronger claim: that had a CAS-instrumented pipeline been in place, the harmful output would have been refused, the decision would have been routed to human review, or the automated action would have been blocked *before* the harm occurred. Prevention requires both a detection mechanism and an enforcement mechanism, and depends on operational integration (where the CAS assessment sits in the decision loop).

## Admission criteria for this file

An incident from the main database is promoted here only if all of the following are true:

1. The primary failure mode is clearly classifiable in the CAS taxonomy.
2. The structural signature would have been visible at *inference time on the specific output* — not only in aggregate.
3. Blocking or routing the output at inference time would have interrupted the harm chain (i.e., the output was the proximate cause of harm, not a contributing factor among many).
4. An existing CAS gate (RPM Gate, Inversion Scanner threshold, Dial System refusal, Wrap pipeline output gate) has a documented mechanism for the required enforcement.
5. We can state, without hedging, *which gate would have fired and why*.

Incidents where the harm chain is long, where the model output was one of many inputs, or where the necessary enforcement would require capabilities CAS does not yet have, are **not** promoted — they stay in the main database under detection-only claims.

## Current promoted incidents: 0

*Scaffold phase. This list grows conservatively as the main database grows.*

## Anti-pattern: why this file exists

AI-safety marketing often claims "our system would have prevented X" for incidents where the marketer has no defensible mechanism for prevention — only a retrospective narrative. This file is the explicit guard against that pattern in our own work. If a claim cannot survive "which specific gate, at what point in the pipeline, with what threshold, would have fired?" it does not belong here.
