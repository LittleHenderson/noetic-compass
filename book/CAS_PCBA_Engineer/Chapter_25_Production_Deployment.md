# Chapter 25: Production Deployment

A new aircraft engine does not go straight from the test stand onto a passenger jet. It runs for thousands of hours on the ground first, instrumented to the bone. Then it flies — but on a test aircraft, with a crew of engineers watching every gauge and a parachute on the airframe's program if anything goes wrong. Then it flies on a freight route with no passengers. Then it carries passengers, but only after a long campaign of in-service data has confirmed that the engine in the air behaves like the engine on the stand. At every step, the engine is the same. What changes is how much trust the world is willing to place in it, and that trust is *earned*, one rung at a time, against evidence.

You have a verified Cognitive Safety Board. In Chapter 18 you designed it; in Chapter 23 you tested it stage by stage; in Chapter 24 you debugged the failures the tests found. The board is correct on the bench. None of that earns it the right to sit between a real user and a real model on day one, refusing real requests. A circuit that is correct on the bench and a circuit that is trusted in production are two different certifications, and the gap between them is bridged the same way the engine's was: a deployment ladder, climbed against evidence, with the ability to stop and step back down at every rung.

This chapter is that ladder. It is the engineering discipline for taking a verified board off the workbench and into a live system *without breaking anything* — and, just as importantly, for proving afterward that the board made the decision it made, when it made it. We use the CSB as the worked example throughout, because the CSB is the board that most needs this discipline: it is the one whose failures hurt people.

## The Deployment Ladder

The single most dangerous thing you can do with a verified safety board is connect it to production and switch it on. Not because the board is wrong — you tested it — but because "tested on the bench" and "behaves correctly against the live distribution of real prompts" are different claims, and the only way to close the gap is to expose the board to reality *gradually*, while it can still do no harm.

The deployment ladder has five rungs. You climb from the bottom, and you only climb a rung when the evidence from the rung below says you've earned it.

| Rung | Name | What the board does | What it can break |
|---|---|---|---|
| 1 | **Simulation** | Runs against recorded/synthetic prompts offline. | Nothing — no live traffic. |
| 2 | **Shadow** | Sees live traffic, computes its decision, **enforces nothing**. | Nothing — output is discarded. |
| 3 | **Flag** | Sees live traffic, decision is surfaced to humans, still **enforces nothing**. | Nothing automatic; humans may act. |
| 4 | **Soft Enforcement** | Enforces, but a human or fallback can override in real time. | Limited — overridable. |
| 5 | **Full Enforcement** | Enforces autonomously; the board is the decision. | Everything — this is production. |

**Rung 1 — Simulation.** The board runs entirely offline against a fixed corpus: the test prompts from Chapter 23, recorded production traffic (scrubbed), and synthetic adversarial prompts. Nothing the board decides touches a user. This is the SPICE stage made continuous — you already did a single-pass version of it in Chapter 18's simulation walk-through. The promotion question is simple: *does the board reproduce its bench behavior on a corpus larger and messier than the one it was tuned on?*

**Rung 2 — Shadow.** Now the board sees *live* prompts — the real ones, in real time — but its output goes nowhere. The production model answers the user exactly as it would with no board at all; the CSB runs alongside, computes its `safety_decision`, and writes that decision to a log. You built the mechanism for this in Chapter 18, Exercise 18.3: a shadow tap that reroutes the MUX to always select `response` while still computing `safety_decision` for logging. Shadow mode is where you discover, at zero risk, that the board you tuned on a clean corpus flags 4% of perfectly benign production prompts — a false-positive rate you could never see on the bench because the bench had no benign-prompt distribution.

**Rung 3 — Flag.** Same as shadow — the board still enforces nothing — but now its decisions are *surfaced* to a human review queue instead of dropped into a passive log. A `safety_decision = FAIL` on a prompt that was nonetheless answered raises a flag a reviewer reads. Flag mode is the human-calibration rung: you are no longer asking "what does the board decide?" (you got that from shadow) but "*when the board and a human disagree, who is right?*" Every flagged disagreement is a labeled data point telling you whether the board is too cautious, too permissive, or correctly catching things humans missed.

**Rung 4 — Soft Enforcement.** Now the board acts. A `FAIL` actually routes to the refusal path and the user gets refused. But the enforcement is *defeasible*: a human reviewer, a fallback policy, or an escape hatch can override the board's refusal in real time, and every override is logged as ground truth. This is the rung where the board carries real weight but cannot yet do irreversible damage, because a wrong refusal can be caught and reversed before it compounds.

**Rung 5 — Full Enforcement.** The board is the decision. A `FAIL` refuses, the fuse latches, and there is no real-time human in the loop. This is production. You arrive here only after the lower rungs have produced sustained evidence that the board's autonomous decisions match the decisions humans would have made — and the monitoring of the rest of this chapter is what keeps it honest once you do.

### Promotion criteria — earning each rung

A rung is not a calendar event. It is a *gate*: a set of conditions that must hold against real evidence before you climb. Vague gates ("looks good") are how unsafe boards reach production. State them as numbers and thresholds you commit to before you start.

| Promotion | Gate (commit to these *before* you climb) |
|---|---|
| Sim → Shadow | Board reproduces bench TP1–TP4 readings on the full simulation corpus; zero `E-CJT-*` compiler errors; saturation-lock test passes on every harmful/injection prompt in the corpus. |
| Shadow → Flag | False-positive rate (benign prompts the board would have refused) below a committed ceiling; **zero false negatives** on the known-harmful set; decision logging verified end-to-end. |
| Flag → Soft Enforce | Board-vs-human agreement on flagged cases above a committed floor over a committed window; every disagreement reviewed and root-caused (board-right or board-wrong). |
| Soft → Full Enforce | Override rate below a committed ceiling over a committed window; no irreversible-harm override in that window; rollback path tested and confirmed working. |

> **Bench Note — false negatives and false positives are not symmetric, and the gates must say so.** On a safety board, a false negative (a harmful prompt the board lets through) is a breach; a false positive (a benign prompt the board refuses) is an annoyance. The Shadow→Flag gate above demands *zero* false negatives on the known-harmful set but only a *bounded* false-positive rate. That asymmetry is the same design stance as the pre-amp's β=3.0 from Chapter 18 — over-surface rather than under-surface, refuse-on-doubt rather than answer-on-doubt. Bake the asymmetry into your promotion numbers, not just your components.

## The Evidence Packet

The whole book has one thesis you can say in seven words: **show your work, or don't ship it.** A power supply ships with a test report — voltages at every test point, the date, the technician, the serial number — because "trust me, it's in spec" is not an engineering claim. A Cognitive Safety Board is no different. Every decision it makes in production must leave behind a structural record complete enough that an inspector can reconstruct *exactly* what happened, without rerunning anything and without trusting anyone.

That record is the **Evidence Packet**. It is requirement four of the CSB (Chapter 18) made into a durable, verifiable object. One packet per decision. The packet is not a log line — a log line is something you hope was written correctly. The packet is a *sealed* artifact: hashed at the moment of decision so that any later tampering is detectable, and persisted so that the proof outlives the request.

A CSB evidence packet carries seven fields:

| Field | What it contains | Why it's in the packet |
|---|---|---|
| `input` | The exact prompt the board received (scrubbed per your data policy). | You cannot audit a decision without the thing decided on. |
| `cas_trace` | The CAS state at each stage: `expanded_prompt`, `attraction`, `aversion`, `risk_signal`, the three cascade nodes, `safety_decision`. | The structural story of *how* the decision formed, stage by stage. |
| `test_points` | The TP1–TP4 readings for this decision (expansion set, risk-signal magnitude, saturation-lock status, selected path). | The same readings an inspector would probe — captured at decision time. |
| `decision` | The final result: PASS/GREEN or FAIL/RED, and whether the fuse latched. | The outcome the user actually experienced. |
| `trace_id` | A unique identifier for this decision. | The handle everything else (the `/verify` endpoint, the review queue, the registry version) keys on. |
| `ccdl_version` | The signed registry version of the CCDL that made this decision. | *Which* board decided — boards change; the packet pins the exact one. |
| `hash` | A cryptographic hash over all the fields above. | The seal. Recompute it and you prove the packet is unaltered. |

The `cas_trace` and `test_points` fields are where the CSB's design pays off. Because the board is a *typed circuit*, not a prompt, the trace is not a post-hoc rationalization the model wrote about itself — it is the actual sequence of CAS states the decision passed through. The trace says: this prompt expanded to *these* interpretations (`^8^C|A` pre-amp, TP1); the differential pair produced *this* risk signal (`aversion − attraction`, TP2); Stage 3's principled aversion (`^3^P|⟨A,f,T⟩`) reached *this* activation against its sat=0.8 lock (TP3); the MUX selected *this* path (TP4). An inspector reads the trace and re-derives the decision the way they re-derive a voltage from a schematic and a measurement.

```cas
// Conceptual shape of a CSB evidence packet (one decision).
packet {
    trace_id:     "csb-7f3a9c…";
    ccdl_version: "csb@1.4.2";            // signed registry version (see Circuit Registry)
    input:        "<scrubbed prompt>";
    cas_trace: Phi<
        ^8^C_{F2}|A,                       // pre-amp: expanded interpretation set (TP1)
        ^2^P_{F7}|T, ^3^P_{F7}|T,          // differential pair: attraction, aversion
        ^1^C_{F2}|A, ^6^E_{F6}|A,          // cascade: categorize, evaluate
        ^3^P_{F7}|⟨A,f,T⟩                  // safety_decision (TP3)
    >;
    test_points:  { tp1: <expansion>, tp2: <risk_signal>, tp3: <sat_lock>, tp4: <path> };
    decision:     { result: "RED/FAIL", fuse: "latched" };
    hash:         "sha256:…";              // seal over every field above
}
```

> **Bench Note — hash the packet at decision time, not at log time.** If you compute the hash when the packet is written to storage, you are sealing whatever survived the trip to storage, not what the board decided. Compute the hash the instant the `safety_decision` resolves, inside the board's own execution, and carry the hash with the packet. Then a corrupted or edited packet fails its own hash check, and you find out. A seal applied after the fact seals nothing.

## The `/verify` Endpoint

A test report sitting in a filing cabinet proves nothing until someone can pull it out and check it. The Evidence Packet is the report; the **`/verify` endpoint** is the filing cabinet with an honest clerk — the interface that lets anyone holding a `trace_id` confirm that *this* board made *this* decision at *this* time, and that the packet describing it has not been altered.

The endpoint answers one question: *is this decision authentic and unaltered?* You hand it a `trace_id` (and, if you want to check a packet you were given, the packet itself). It looks up the sealed packet, recomputes the hash over the packet's fields, and compares. It returns, in plain terms:

- **Whether the packet exists** for that `trace_id` (a decision the board claims it made should be findable).
- **Whether the hash matches** — the integrity check. A mismatch means the packet was altered after the board sealed it.
- **Which CCDL version** made the decision (`ccdl_version`), so the verifier knows exactly which board to hold accountable, and whether its signature in the registry is valid.
- **The decision and its test-point readings**, so the verifier can re-derive the outcome from the structural trace rather than taking the `decision` field on faith.
- **The decision timestamp**, sealed inside the hash, establishing *when*.

What `/verify` returns in practice is a small, structured confirmation object — exists / hash-valid / version / decision / timestamp — plus the trace for re-derivation. We describe its *shape* here as a design; we are not quoting a response from a running server, and you should not invent one. The point is the contract: `/verify` turns a private decision into a publicly checkable fact. An auditor, a regulator, or a wronged user with a `trace_id` can confirm the board's account of itself without access to the board's internals and without trusting the operator's word. That is what "auditable" means as an engineering property rather than a marketing one.

> **Bench Note — `/verify` proves integrity, not correctness.** The endpoint proves the board *made this decision and the record is unaltered*. It does not prove the decision was *right* — that is what the test report (Chapter 23) and certification (Chapter 26) are for. Keep the two claims separate when you talk to a regulator. "We can prove what the board did" and "we can prove the board did the right thing" are different sentences, and conflating them is exactly the kind of overclaim this book exists to prevent.

## Monitoring in Production

A board that passed every promotion gate can still drift once it's carrying live traffic, because the world it sees keeps changing and the board's own substrate (`^5` Female — its accumulated experience) keeps updating through the feedback path. Monitoring is how you catch drift before it becomes a breach. You instrument the board's production behavior the way you'd instrument a power supply on a burn-in rack, watching the same parameters you tuned on the bench — now as live, trending signals with alarms on them.

Four signals are load-bearing for the CSB, each tied to a component you already understand.

**β drift (gain stability — Chapters 9, 11).** Each CJT's gain `β` is a design value: pre-amp 3.0, differential pair 2.0 each, Stage 2 unity 1.0, and so on. In production, measured β can wander — most dangerously the differential pair, where attraction-β creeping above aversion-β is the differential-imbalance failure from Chapter 18 (the board starts over-trusting). Track the live β of every CJT against its design value. *Alert* when any CJT drifts beyond a committed tolerance, and treat the two differential-pair gains drifting *apart* as a higher-severity alarm than either drifting alone — matched β is what gives the pair its common-mode rejection.

**Saturation creep (Chapter 9, 14).** Stage 3 is deliberately saturated at sat=0.8; that lock is the board's safety guarantee. Two failure directions matter. If Stage 3 stops reaching saturation on known-harmful prompts, the lock has weakened toward the Stage-3-cutoff failure — the most dangerous one, where safety silently never fires. If *other* stages that should sit in the active region start saturating (the pre-amp maxing out every prompt, Chapter 18's pre-amp-saturation failure), the board floods with spurious interpretations. Monitor the saturation status at every stage, not just Stage 3. *Alert* when Stage 3's saturation rate on the harmful set drops, and when any active-region stage's saturation rate climbs.

**Noise spectrum (Chapters 12, 16).** The board's filters — the RC low-pass on the feedback path (τ=5 min) — exist to reject fast transients and pass only sustained trends. Watch the frequency content of the signals those filters are protecting. A rising tide of high-frequency energy on the feedback path means either the input distribution has gotten noisier or a filter is failing to do its job — and a feedback path that lets high-frequency content through is a feedback path an attacker can use to yank the constitution (the feedback-runaway failure). *Alert* when high-frequency power on a filtered line exceeds a committed threshold.

**Drive consumption (Chapters 14, 16).** Power management on a CCB tracks how much of each Drive (F1–F7) the board is consuming. The CSB leans hard on F7 Purpose (the constitution's drive) and F6 Structure; a healthy board keeps its inversion-pair Drives in balance (F2↔F6, F1↔F7 — Chapter 2). A board that collapses onto F6 Structure at the expense of F2 Wisdom is becoming rigidly procedural; one starving its F7 Purpose rail is losing the principled drive that powers Stage 3. Monitor per-Drive consumption and the balance across inversion pairs. *Alert* when any Drive rail saturates or starves, or when an inversion pair drifts past a committed imbalance threshold (the Drive-pair inversion axis from the inversion scans).

| Signal | What you watch | Alert when… |
|---|---|---|
| **β drift** | Live gain of each CJT vs design value | Any β beyond tolerance; differential pair gains drift *apart* (higher severity) |
| **Saturation creep** | Saturation status at every stage | Stage 3 stops saturating on harmful set; an active-region stage starts saturating |
| **Noise spectrum** | Frequency content on filtered lines | High-frequency power on the feedback path exceeds threshold |
| **Drive consumption** | Per-Drive (F1–F7) usage and pair balance | A Drive rail saturates/starves; an inversion pair drifts past its imbalance threshold |

> **Bench Note — set thresholds from the bench, ratchet them in production.** Your first alert thresholds come from the test campaign: the tolerances you verified in Chapter 23 are your starting alarm levels. But the bench distribution is not the production distribution, so expect to *tighten* thresholds as shadow and flag mode reveal the real spread of each signal. Set the initial alarms loose enough not to cry wolf on day one, then ratchet them down as you learn what "normal" looks like in the wild. A monitor that alarms constantly gets muted, and a muted monitor is no monitor at all.

## Rollback

Every alert needs an answer, and the fastest, safest answer is almost always the same one: **put back the board that was working.** Rollback is reverting the production board to a previous known-good CCDL — and on a circuit, this is cleaner than on most software, because the entire board *is* a versioned, signed text file. There is no migration, no half-applied state, no schema to unwind. You point production at the previous `ccdl_version` and the previous board runs.

The discipline that makes rollback trustworthy is the same discipline that makes the Evidence Packet trustworthy: you must *know* which board was running and be able to *reproduce* the previous one exactly. That is the Circuit Registry's job (below). A rollback is a one-line operation — select an earlier signed version as live — but it is only safe if (a) that earlier version is still in the registry, intact and signature-valid, and (b) you tested the rollback path itself, because an untested escape hatch is not an escape hatch. The Soft→Full promotion gate above requires a confirmed-working rollback for exactly this reason: you do not climb to autonomous enforcement until you have proven you can step back down.

> **Bench Note — roll back first, diagnose second.** When a production alert fires on a safety board, the instinct to debug the live board *while it's enforcing* is the wrong one. Roll back to the last known-good `ccdl_version`, restore the board you trust, and *then* debug the suspect version offline in simulation (rung 1) with the evidence packets the alert produced. The user is protected by the known-good board the whole time. Debugging in production is how a small drift becomes an incident.

## A/B Deployment: Canary One Instance

Sometimes you are not rolling back from a failure — you are rolling *forward* to an improvement, and you need to know the new board is actually better before you trust it with all the traffic. This is **A/B deployment**, and the safe form of it is the **canary**: you run the new candidate board on one instance (or a small slice of traffic) — the *canary* — while the proven board (the *control*) handles everything else. Both are live; both enforce; both emit evidence packets. You compare.

The comparison uses exactly the signals you already monitor. On the same live distribution, does the canary's false-positive rate match or beat the control's? Does it hold zero false negatives on the known-harmful set? Are its β values, saturation rates, noise spectrum, and Drive balance within tolerance? Because every decision on both boards is a sealed, `/verify`-able evidence packet stamped with its `ccdl_version`, the comparison is not a vibe — it is a like-for-like measurement on real traffic, attributable to the exact board that produced it.

A canary keeps the blast radius small. If the new board has a regression that the simulation corpus didn't catch — a class of prompt it over-refuses, a drift the bench never saw — only the canary slice is affected, and the control board is one rollback away. You promote the canary to control only when its evidence beats the control's against the gates, and you keep the old control in the registry as the rollback target. This is the deployment ladder in miniature, run continuously: every change to a production board canaries before it takes over.

> **Bench Note — the canary needs the *same* gates as a fresh deployment.** It is tempting to wave a new version through because "it's basically the same board with one β tweaked." Don't. A one-parameter change is exactly the kind of thing that quietly collapses CMRR or unlatches a saturation lock. Hold the canary to the Soft→Full gate — agreement, override rate, tested rollback — before it becomes the control. The whole point of the canary is to not trust the change until the evidence does.

## The Circuit Registry

Everything in this chapter depends on one capability: being able to name, retrieve, and trust an *exact* board. The promotion ladder pins a `ccdl_version` to each rung. The evidence packet records which version decided. `/verify` reports the version. Rollback restores a version. The canary compares versions. The thing that makes "a version" a real, trustworthy object is the **Circuit Registry**: a versioned, signed store of CCDL files.

The registry holds every CCDL that has ever been promoted, each one:

- **Versioned** — a unique, immutable identifier (`csb@1.4.2`). A version, once published, never changes; a fix is a new version, never an edit to an old one. This is what lets an evidence packet from six months ago name the precise board that made the decision.
- **Signed** — cryptographically signed so that "this is the official csb@1.4.2" is a checkable claim, not a trusted one. A board running in production with an unsigned or signature-invalid CCDL is a board you cannot account for, and it should not run. `/verify` checks this signature when it reports a decision's `ccdl_version`.
- **Immutable and append-only** — you add versions; you never overwrite or delete them. The previous known-good board must still be there for rollback, and the board that made last quarter's decision must still be there to verify that decision.

```cas
// Conceptual shape of a Circuit Registry entry.
registry_entry {
    version:   "csb@1.4.2";
    ccdl:      "<full signed CCDL source for the CSB>";
    signature: "ed25519:…";          // checkable authenticity
    parent:    "csb@1.4.1";          // the version this was promoted from
    status:    "control";            // one of: candidate | canary | control | retired
    promoted:  "2026-06-14T…";       // when it reached this rung
}
```

The registry closes the loop on the book's traceability thesis. Every production decision (evidence packet) names a registry version; every registry version is a signed, immutable CCDL you can read, re-simulate, and certify; and `/verify` ties a specific decision back to a specific board back to a specific schematic. The chain runs unbroken from a user's prompt, through the CAS trace, to the exact signed board that produced the decision — show-your-work, all the way down. A board you cannot name is a board you cannot roll back, cannot canary, cannot verify, and cannot certify. The registry is what makes the board *nameable*, and naming is the foundation of every other deployment discipline in this chapter.

## Key Takeaways

- **The deployment ladder has five rungs** — Simulation → Shadow → Flag → Soft Enforcement → Full Enforcement — and you climb each rung only against committed, numeric promotion gates, never on a calendar or a hunch. Lower rungs (Shadow, Flag) let the board see live traffic while enforcing nothing, so you find false positives and calibrate against humans at zero risk.
- **Promotion gates are asymmetric on purpose**: zero false negatives on the known-harmful set, a *bounded* false-positive rate — the same refuse-on-doubt stance as the CSB's pre-amp. A confirmed-working rollback is a gate for full enforcement.
- **The Evidence Packet** seals one decision into a verifiable artifact carrying `input`, the `cas_trace` through every stage, the TP1–TP4 `test_points`, the `decision`, a `trace_id`, the `ccdl_version`, and a `hash`. Hash it *at decision time*, not log time. This is requirement four of Chapter 18 made durable: show your work, or don't ship it.
- **The `/verify` endpoint** turns a private decision into a publicly checkable fact: given a `trace_id` it confirms the packet exists, the hash matches, which signed CCDL version decided, the decision and its test points, and the sealed timestamp. It proves *integrity* (what the board did), not *correctness* (whether it was right) — keep those claims separate.
- **Monitor four production signals**: β drift (especially the differential pair drifting apart), saturation creep (Stage 3 must keep saturating; active stages must not), noise spectrum on filtered lines (feedback-path high-frequency energy), and Drive consumption (rail saturation/starvation and inversion-pair imbalance). Start thresholds from the bench tolerances; ratchet them tighter as production reveals the real spread.
- **Rollback** reverts production to a previous known-good `ccdl_version` — clean on a circuit because the board *is* a versioned signed file. On an alert: roll back first, diagnose offline second; the user is protected by the trusted board the whole time.
- **A/B deployment** canaries a new board on one instance against the proven control, comparing like-for-like via `/verify`-able evidence packets stamped with each board's version, keeping the blast radius small. Hold the canary to the same gates as a fresh deployment.
- **The Circuit Registry** — versioned, signed, immutable CCDL files — is the foundation everything else stands on. It makes a board *nameable*, and naming is what makes verification, rollback, canarying, and certification possible. The chain runs unbroken from prompt → CAS trace → decision → signed board → schematic.
- **Honesty**: every mechanism in this chapter is described as *design* — the ladder, the packet, `/verify`, the registry. Nothing here is a live production run or a measured metric. Canonical Noetic names throughout: `^8` Above/Cause, `^2` Positive, `^3` Negative, `^1` Mind, `^6` Male, `^9` Below/Effect, `^5` Female.

---

## Exercises

**Exercise 25.1: Place the Failure on the Ladder**

For each scenario, name the lowest rung of the deployment ladder at which the problem could have been caught, and explain why a lower rung would have missed it:

a) The board refuses 4% of perfectly benign production prompts (a false-positive rate the bench never showed).
b) On flagged disagreements, a human reviewer agrees with the board only 60% of the time.
c) A new candidate board over-refuses one specific class of prompt that the simulation corpus didn't contain.

**Exercise 25.2: Audit a Packet with `/verify`**

A user disputes a refusal and gives you a `trace_id`. You call `/verify` and it reports: packet exists, hash *mismatch*, `ccdl_version = csb@1.4.2` (signature valid).

a) What does the hash mismatch tell you, and what does it *not* tell you about whether the original refusal was correct?
b) Why does the valid CCDL signature not rescue the situation?
c) State, in one sentence, the difference between what `/verify` can prove here and what a Chapter 23 test report would prove.

**Exercise 25.3 (Build): Add a Drive-Imbalance Monitor in CCDL**

The CSB leans on F7 Purpose and F6 Structure. Write a short CCDL fragment that taps the board's per-Drive consumption and raises an alert when the F2↔F6 inversion pair (Wisdom vs Structure) drifts past an imbalance threshold you choose. Use a probe on the relevant Drive rails and a comparator-style alert. State which production failure mode this monitor is designed to catch and why an unmonitored F6-collapse is dangerous. (Answer in Appendix E.)

**Exercise 25.4 (Marquee): Design the CSB Rollout Plan**

Design a complete Shadow → Flag → Soft Enforcement rollout plan for the CSB (assume Simulation is already passed). Your plan must specify, for *each* promotion:

a) The **promotion criteria** — the concrete, numeric gates that must hold before you climb (false-positive ceiling, false-negative requirement, agreement floor, override ceiling, window length — pick committed values and justify them).
b) The **monitoring signals that gate each promotion** — for each rung, which of the four production signals (β drift, saturation creep, noise spectrum, Drive consumption) you watch, with the specific alert thresholds derived from the CSB's design parameters in Chapter 18 (pre-amp β=3.0, differential pair β=2.0 each, Stage 3 sat=0.8, feedback τ=5 min).
c) The **rollback trigger** — the single condition that, if it ever fires at any rung, sends you straight back to the previous known-good `ccdl_version`, and why that condition and not another.

Write the gates as something an inspector could check, not as prose. Remember the asymmetry: false negatives on the known-harmful set are breaches, false positives are annoyances. (Answer in **Appendix E.** Every parameter is a design choice; nothing here is a measured production result. For the one-page notation reference, see **Appendix A: the CAS Quick-Reference Card.**)
