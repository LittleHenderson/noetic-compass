# Appendix H Fragment — Worked Answers for Chapters 17–24

This fragment contains the complete model answers for Chapters 17 through 24. The numerical values are consequences of the chapters' stated design assumptions, not empirical measurements. Chapters 17–19 remain detection-, defence-, and counter-circuit only: no answer supplies a procedure for coercing another person. Every self-directed design assumes informed, continuing consent and an immediate stop on withdrawal.

## Chapter 17

### H.17.1 — Relate gain, resistance, and framing sensitivity

Use the identity `rπ = β/g_m`, rearranged as `g_m = β/rπ`:

```text
initial: g_m = 2.0/0.40 = 5.0
target:  g_m = 2.0/0.20 = 10.0
```

The target framing sensitivity is therefore `10/1 = 10` times the waking reference, and the requested change doubles `g_m` while leaving `β` fixed. Of the four factors in `g_m = g_0 N R V D`, the most likely supplier is `D`, the effective dampening of the `^6` decomposition filter: lowering that filter's gain makes framing reach the bias terminal more readily. The arithmetic alone cannot identify the factor, so a real detector must log all four; naming `D` is a topology-based diagnosis, not a measurement.

### H.17.2 — Bound a guarded ramp

The attention change is `Δi = 0.85 − 0.15 = 0.70 A_c`, and a linear ramp obeys `V_kick = L_s Δi/dt`. At the Chapter 9 ceiling,

```text
V_kick,max = 3(24) = 72 V_c
dt_min     = 300(0.70)/72 = 2.92 min.
```

At CCB-HYP's tighter 1× working limit,

```text
V_kick,max = 24 V_c
dt_min     = 300(0.70)/24 = 8.75 min.
```

Eight minutes forty-five seconds is a session a willing participant could sit through, and it lies just inside Chapter 17's roughly nine-to-fifteen-minute usable window for this guardedness. The engineering conclusion is not permission to operate on a guarded person: the narrow window makes consent, continuous veto access, and a pre-budgeted reverse ramp more important. Without informed and withdrawable consent, the correct duration is no session at all.

### H.17.3 — Type recoil and later analysis separately

The canonical definition is: `^3` Negative is “an Idea the Mind is adverse to and repelled by.” An over-fast ramp produces an immediate, felt cannot-stomach-this recoil, so the state is Evaluative, affective, and tied to F3 Vitality: `^3^E_{F3}|f`.

`^6` Male instead decomposes an Idea and tests what it is made of. `^6^E_{F6}|A` is therefore the later analytical account—perhaps “this method is nonsense” or “the pacing was wrong”—that arrives after the kick has already landed and the person can inspect it. Calling the first event `^6` would hide the rate fault and invite argument when the repair is simply to stop, restore baseline, and reduce `di/dt`.

### H.17.4 — Read unaccounted drift

This is TP2, the `unaccounted` probe on CCB-HYP-DET. Its definition is

```text
unaccounted = drift − passed_log.
```

The colleague reports non-zero movement in `^5` but cannot name a proposition that their `^6` filter evaluated and accepted, so `passed_log` does not account for the change and `unaccounted > 0`. That is a detector reading, not proof of an operator or an attribution.

The in-conversation manual check is **restatement**: pause and restate the last material as a flat assertion in one's own words. A presupposition then becomes an explicit claim that can be accepted or rejected, or it evaporates. The after-the-fact drift ledger would also record the discrepancy, but restatement is the check that could have surfaced the missing proposition while the conversation was still running.

### H.17.5 — Fit a consent-bound twenty-minute closed loop

This is a self-directed, continuously consented loop. The attention span is `Δi = 0.50 A_c`, so

```text
|di/dt|max = V_drive/L_s = 18/150 = 0.120 A_c/min
τ_i,min    = Δi/|di/dt|max = 0.50/0.120 = 4.167 min.
```

Choose `τ_i = 4.5 min`. Then `3τ_i = 13.5 min`; using the same 4.5-minute interval for emergence leaves exactly `20 − 13.5 − 4.5 = 2.0 min` for the suggestion. The initial exponential slope is `0.50/4.5 = 0.1111 A_c/min`, giving

```text
V_kick = 150(0.1111) = 16.67 V_c = 0.926 × rail
```

in both directions. With `rπ(t)=0.26+0.74e^(−t/4.5)`, the trajectory is:

```text
1τ: rπ = 0.26 + 0.74e^-1 = 0.532
2τ: rπ = 0.26 + 0.74e^-2 = 0.360
3τ: rπ = 0.26 + 0.74e^-3 = 0.297
```

One canonical closed-loop fragment is:

```cas
board answer_h_17_5 {
    input: breath_count;
    output: session_state;

    node self_substrate: ^5^P_{F7}|T;
    node consent:        ^5^P_{F5}|T;
    node cadence:        ^7^O_{F4}|E;
    node self_check:     ^6^C_{F6}|A;
    node suggestion:     ^0^C_{F6}|A;
    node landed:         ^9^E_{F5}|f;

    osc breath: Oscillator< signal=cadence, frequency=0.10, sustain=1200.0 >;
    filter fb_rc: LowPass< in=cadence, out=trend, tau=4.5 >;
    feedback trend -> self_substrate [β=0.6];
    notch notch_6: Notch< in=self_check, f0=0.35, Q=4.0 >;

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    cjt deliver: CJT< suggestion | self_substrate => landed >
                 [β=1.5, rπ=0.26, g_m=5.75, region=active];

    ramp descend: Ramp< target=rπ, from=1.00, to=0.297, dt=810.0 >;
    ramp emerge:  Ramp< target=rπ, from=0.297, to=1.00, dt=270.0 >;

    probe tp1: rπ;  probe tp2: g_m;
    probe tp3: consent;  probe tp4: emerge;
}
```

Both diodes descend, the O→P move is the explicitly filtered feedback terminating at the Principled bias, and the delivery CJT's `^P` bias is above its `^C` cause. Consent is sampled as a live node; withdrawal ends the loop and starts emergence.

### H.17.6 — Make recall a self-owned interlock

For safety, the executable form below is a self-owned recall/cancellation test, not an installation circuit for another person. A zero-leak dated record sits in the operator's own `^5`; an AND gate prevents the `^8`→`^9` readout unless the record clears a recall monitor:

```cas
board answer_h_17_6_recall_interlock {
    input: self_trigger;
    output: cancelable_recall;

    node trigger:           ^8^C_{F4}|A;
    node installation_log:  ^5_record^P_{F5}|T;
    node recall_ok:          ^6^C_{F6}|A;
    node cancelable_recall:  ^9^C_{F5}|A;

    capacitor record: Capacitor< node=installation_log, C=1.0,
                                  leakage=0.0, V_BR=10.0 >;
    monitor recall_threshold: Monitor< signal=installation_log,
                                       limit=[0.80, 1.00],
                                       action_on_violation=HOLD >;
    gate recall_interlock: AND< trigger, recall_threshold >;
    cjt anchor_read: CJT< recall_interlock | installation_log => cancelable_recall >
                     [β=1.0, sat=0.85];

    probe tp_record: installation_log;
    probe tp_recall: cancelable_recall;
}
```

The enforcing component is `recall_interlock`; `0.80` is the declared recall threshold. At `g_m = 20`, `^1` is narrowed and its analytical register is least available, so the installation event is less likely to be encoded into a reconstructable record. At `g_m = 5`, scan width and analytical access are broader, making a recallable installation record more plausible.

The circuit still cannot guarantee subjective future recall, truthful recording, or a person's practical ability to cancel under changed conditions. It can only refuse to emit when its record probe is low. That residual is why the hetero-operator listing in §17.4 remains DETECTION-ONLY even when each individual stage is described with a consented reading.

## Chapter 18

### H.18.1 — Set the dark interval

Leakage follows `P(t)=P_0e^(−λt)`, so the maximum interval is

```text
t_max = ln(P_0/P_floor)/λ.
```

For the 8.5 floor,

```text
t_max = ln(9.50/8.50)/0.06 = 1.854 weeks.
```

For the 7.0 floor,

```text
t_max = ln(9.50/7.00)/0.06 = 5.090 weeks.
```

Accepting the lower floor buys about `5.090 − 1.854 = 3.236` additional dark weeks, but gives up stored salience: the next flight begins from 7.0 rather than 8.5 and spends more of its exposure budget recharging old loss instead of adding new association.

### H.18.2 — Locate both saturation knees

The association stage saturates when `β c b = sat`, hence

```text
β_knee = sat/(c b).
```

Without an endorser,

```text
β_knee = 0.85/(0.45 × 0.950) = 1.988.
```

The endorser adds `Δc = n(P_celeb/10) = 0.60(0.88) = 0.528`, so the effective cause is `0.45 + 0.528 = 0.978` and

```text
β_knee,endorser = 0.85/(0.978 × 0.950) = 0.915.
```

The endorsed campaign should stop creative A/B testing first: it is already above the knee at ordinary gains, where distinct variants clamp to the same output. The safe response is to test below saturation or measure before the clamped stage, not to raise gain.

### H.18.3 — Remove the junction's flattery

The downstream lift exaggeration factor is

```text
V_drive/(V_drive − Vf) = 6.20/(6.20 − 2.00) = 1.476.
```

Therefore the estimated upstream gain lift is

```text
44%/1.476 = 29.8%.
```

`R = 5.0` sets absolute flow but cancels from this local relative correction. The estimate assumes the two variants share the same segment bias, junction drop, and resistance and that neither stage is saturated. Check it with matched branches below the knee and measure the pre-junction drive as well as the sale current; if a 20% cause change does not move the effect, the stage is clipped and the correction is invalid.

### H.18.4 — Read endorsement polarity

As a concrete self-audit: Nike's logo tends to surface an athletic/agentic identity, so product surfaces identity; Rolex's status identity tends to surface the watch, so identity surfaces product; Patagonia's environmental/outdoor identity tends to surface the product, so identity surfaces product. These are my own association readings, not population measurements.

Nike is the complete flip in that set: the product/logo has become `^8`, and the aspirational identity is the `^9` it brings to mind. If a strongly associated endorser's public formation changed tomorrow, every product sighting could continue to fire the installed association. Dropping the endorser stops new exposures but does not discharge the stored pairing; reducing that exposure requires an overwrite across another full `^7` cycle.

### H.18.5 — Separate a recent injection from a long-held want

Assign the advertised jacket `τ_j = 2 weeks`, the chapter's injected-want scale, and the long-wanted tool `τ_t = 40 weeks`, the identity scale. Across a two-week hold from now:

```text
jacket: e^(−2/2)   = 0.368 survives; 0.632 removed
tool:   e^(−2/40)  = 0.951 survives; 0.049 removed
```

The survival discrimination is `0.951/0.368 = 2.59`: the filter passes about 2.6 times as much of the long-held want. Because the jacket exposure was already six days (`0.857 weeks`) ago, only `e^(−(2.857)/2)=0.240` of its exposure-time peak remains after the additional hold. The honest cost is `0.049` tool-want units per unit present now—about 4.9% of a genuine desire—plus the practical cost of waiting.

### H.18.6 — Keep learning on the advertiser's bench

`sale` is Operational while the segment substrate is Principled. Integrating them under `×` would make an `^O` result ascend into `^P`, violating the domain order and the ban on `^O × ^P`.

The valid topology leaves the target board one-way and puts the learning record on the advertiser's own compliance bench. To preserve this chapter's defensive boundary, the fragment below audits the relationship but does not emit or tune a new persuasive variant:

```cas
board answer_h_18_6_compliance_bench {
    input: sale_log;
    output: audit_record;

    node sales:        ^9^O_{F5}|E;
    node bench_review: ^6^C_{F6}|A;
    node audit_record: ^6^O_{F6}|A;

    filter trend: LowPass< in=sales, out=sale_trend, tau=3.0 >;
    cjt audit: CJT< sale_trend | bench_review => audit_record >
               [β=1.0, sat=0.85];
    diode d_out: Diode< ^C -> ^E >;
}
```

The semantic loop lives between completed flights in the advertiser's own operational records, where a sale may inform a later, separately reviewed planning decision. It never feeds a sale into the non-consenting audience's Principled substrate, and this defensive listing intentionally stops at the audit record rather than supplying an optimization path.

### H.18.7 — Detect wear-out without driving it

Measure attraction and aversion separately before they become one undifferentiated activation. Define `wear_margin = attraction − aversion`, and warn while attraction still leads:

```cas
board answer_h_18_7_wear_detector {
    input: observed_response;
    output: review_alarm;

    node consumer_baseline: ^5^P_{F4}|T;
    node attraction:        ^2^E_{F4}|f;
    node aversion:          ^3^E_{F3}|f;
    node wear_margin:       ^6^E_{F6}|A;
    node review_alarm:      ^9^E_{F6}|A;

    diff polarity_margin: Differential< plus=attraction,
                                        minus=aversion,
                                        out=wear_margin >;
    filter trend: Filter< in=wear_margin, out=margin_trend,
                          type=lowpass, tau=3.0 >;
    monitor pre_inversion: Monitor< signal=margin_trend,
                                    limit=[0.20, 1.00],
                                    action_on_violation=DEFER_CAMPAIGN >;
    cjt alarm: CJT< margin_trend | consumer_baseline => review_alarm >
               [β=1.0, sat=0.85];
}
```

The `0.20` threshold reserves a visible margin before polarity reaches zero; it is a conservative design choice rather than a measured human constant. The alarm must not be wired to increase frequency, change copy, or drive the audience. It may only pause the campaign and request a human review, otherwise the detector becomes a tuning loop for the very non-consenting influence it is meant to constrain.

### H.18.8 — Price a personal purchase hold honestly

For kitchen tools I would use `τ_inject = 1.5 weeks`: novelty-driven wants in my own records usually fade within a fortnight. I would use `τ_identity = 30 weeks`: tools tied to recurring cooking projects persist across seasons. A one-`τ_inject` hold is 1.5 weeks:

```text
injected remaining = e^(−1.5/1.5) = 0.368; removed = 0.632
genuine remaining  = e^(−1.5/30)  = 0.951; removed = 0.049
```

Suppose a year's baseline contains six injected purchase impulses and twelve genuine ones. The hold blocks about `6(0.632)=3.79` injected purchases and `12(0.049)=0.59` purchases I would have been glad to make. To locate the point where cost exceeds benefit, solve

```text
12(1 − e^(−h/30)) = 6(1 − e^(−h/1.5)).
```

The non-zero crossing is `h = 20.79 weeks`. Beyond roughly twenty-one weeks the expected number of blocked genuine purchases exceeds the injected purchases filtered out. This is a self-owned purchasing rule; it neither diagnoses desire nor licenses imposing a hold on someone else.

## Chapter 19

### H.19.1 — Compute coupling without claiming attribution

The geometric term is

```text
√(L1L2) = √(6000 × 1500) = √9,000,000 = 3000 h·Ω_c.
```

Therefore

```text
M_independent = 0.20(3000) = 600 h·Ω_c
M_observed    = 0.55(3000) = 1650 h·Ω_c
ratio         = 1650/600 = 2.75.
```

The observed coupling is 2.75 times the chapter's honest-independence ceiling. That entitles a defender to inspect for a shared clock or common upstream and to reduce reliance on cadence alone. It does not identify an actor, prove intent, establish that either stream is false, or authorize a counter-operation against a person.

### H.19.2 — Classify payloads by what remains

The first item—anger with nothing new—is `^3`: a visceral aversion was amplified, and the bench test “what checkable thing did I learn?” returns nothing. The second is `^6`: three claims remain available for decomposition and checking. The third is also `^3`: the affect is certain while the proposition cannot be stated.

The three-claim item is not evidence of a Path D operation; it has the structure of analysis even if its claims later prove wrong. More strongly, no single `^3` item proves an operation either. Operational detection requires the structural fingerprints—shared clock, polarity asymmetry, cross-feed, or repeated chain gain—not a judgement that an angry item must have been engineered.

### H.19.3 — Recover per-stage gain

For three equal stages,

```text
β_stage^3 = 0.62/0.15 = 4.1333
β_stage   = (4.1333)^(1/3) = 1.605.
```

Each probe therefore sees a modest gain near 1.6, while the full chain produces 4.13. Splitting the gain avoids an unmistakable single amplifier and delays clipping: a detector placed at any one intermediate stage sees something compatible with ordinary discourse. Defence therefore compares the end-to-end product and its shared timing, rather than declaring any one modest stage malicious.

### H.19.4 — Diagnose compound inversion

Compute the three involution divergences:

```text
|Dial(^2) − Dial(^3)| = |4 − 9| = 5  → despair signature
|Dial(^5) − Dial(^6)| = |9 − 4| = 5  → dogmatism signature
|Dial(^8) − Dial(^9)| = |6 − 5| = 1  → inside the limit
```

The first two are axis-N pair inversions; because two pairs are simultaneously beyond four, the chapter classifies the combined state as a compound axis-P inversion. I would restore `^6` decomposition first, using the inward CCB-HM stage, because it makes subsequent claims inspectable and can reduce the `^5/^6` divergence without projecting a new recoil.

Raising `^2` first merely adds attraction while decomposition remains starved. It does not repair `^5/^6`, can create the opposite runaway-affinity fault, and risks rebuilding Path F instead of a counter-circuit.

### H.19.5 — Replace an ascending diode with a lawful guard

`Diode< ^C -> ^P >` is refused because a diode may only descend `P → C → E → O`; the listing violates the no-domain-ascent invariant. “Only principled signals fortify” is better represented as a Principled bias judging a Cognitive claim and emitting a lower-domain, checked result:

```cas
board answer_h_19_5_defensive_gate {
    input: incoming_claim;
    output: checked_affinity;

    node principle:        ^5^P_{F7}|T;
    node incoming_claim:   ^6^C_{F6}|A;
    node checked_affinity: ^2^E_{F4}|f;

    cjt verify: CJT< incoming_claim | principle => checked_affinity >
                [β=1.0, sat=0.80];
    diode d_out: Diode< ^E -> ^O > [Vf=2.0];
}
```

`β=1.0` prevents the defensive checker from manufacturing reassurance; `sat=0.80` caps affinity before it can become dogmatic. The bias is `^P`, above the `^C` cause, and the effect is below the bias, so the CJT is domain-coherent.

### H.19.6 — Configure a counter board for a monoculture

The board must describe the population honestly: it starts with one live capacitor, not five imaginary ones. I would install the following defensive settings and publish them for audit:

```cas
board answer_h_19_6_hm {
    input: incoming;
    output: composed;

    node substrate: ^5^P_{F1}|T;
    cap c5: Capacitor< node=substrate, C=10.0, n_parallel=1,
                       leakage=0.02 >;

    node decompose: ^6^C_{F6}|A;
    node confirm:   ^4^C_{F2}|A;
    node composed:  ^5^C_{F6}|A;
    node own_clock: ^7^O_{F6}|E;
    node limit:     ^3^P_{F7}|⟨A,f,T⟩;
    node blocked:   ^9^P_{F7}|T;

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];
    diode d_ce: Diode< ^C -> ^E > [Vf=1.6];
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    cjt hm1: CJT< incoming | substrate => decompose > [β=2.5, region=active];
    cjt hm2: CJT< decompose | substrate => confirm > [β=1.0];
    integrate hm3: ( decompose × confirm ) = composed;

    osc local: Oscillator< signal=own_clock, source=internal,
                           period=168.0, duty=0.20 >;
    filter fb: LowPass< in=confirm, out=trend, tau=672.0 >;
    feedback trend -> substrate [β=0.03];

    cjt csb: CJT< incoming | substrate => limit > [β=2.0, sat=0.85];
    cjt hm_enforce: CJT< limit | substrate => blocked >
                    [β=10.0, sat=0.98, cutoff=0.80];
    fuse hm_fuse: Fuse< path=blocked, threshold=0.90,
                        action=permanent_block >;

    probe tp1: own_clock;  probe tp2: hm1;
    probe tp3: composed;   probe tp4: limit;
}
```

The current `C=10, n_parallel=1` preserves truth about the monoculture; a five-cell plural target is a long-term civic programme, not a four-week parameter edit. Raising D2 from 0.4 to 1.6 protects against disagreement instantly becoming affect, at the cost of slower response to a genuine emergency. Raising `hm1` from 2.0 to 2.5 buys more decomposition against an active chain, at the cost of more analysis delay; it remains below the paralysis region above 3.0. Slowing feedback from 504 to 672 hours and lowering `β` from 0.05 to 0.03 protect a substrate already exposed for four weeks, at the cost of slower learning from legitimate outcomes. `hm2` stays at unity, because defensive reassurance must not be manufactured. `hm_enforce` is required so the 0.90 fuse is reachable from a 0.98 ceiling; a fuse placed directly on the 0.85 refusal would be dead metal.

HM4—bringing every pair back inside four—cannot honestly be guaranteed in four weeks. HM2 can be installed immediately, but rebuilding public decomposition is the chapter's roughly forty-eight-week task, and HM4 depends on it. I would say plainly that four weeks can stop further externally clocked driving, restore local checks, and begin repair; it cannot deliver normalized dials. The board has no outward `^3^E|f` stage, so HM6 remains architectural rather than aspirational.

## Chapter 20

### H.20.1 — Reject a fast reference

The separation ratio is

```text
τ_ref/τ_work = 1.5/22 = 0.0682.
```

That is far below SI1's minimum of 3, so the reference and working node are effectively shorted in time. On the first missed cycle TP4 moves on the same day as the TP2 miss instead of remaining a slow, independent baseline. The correlation is the safety finding: the operator's “do I feel like this?” node is chasing performance, and F1 should open the feedback rather than letting the miss become a Principled verdict.

### H.20.2 — Derive three equilibria and the required cadence

Use `P_eq = ΔP_session τ_leak/T` with `ΔP_session=0.50` and `τ_leak=24 d`:

```text
daily, T=1.0:       P_eq = 0.50(24)/1.0 = 12.0 → clips at 10.0
alternate, T=2.0:   P_eq = 0.50(24)/2.0 = 6.0
twice weekly, T=3.5:P_eq = 0.50(24)/3.5 = 3.43
```

For `P_target=7.0`,

```text
T_max = 0.50(24)/7.0 = 1.714 days
sessions/week = 7/1.714 = 4.083.
```

Thus the mean cadence must be a little more than four sessions a week; four exactly is slightly under budget, so a practical schedule uses five or explicitly accepts a lower equilibrium.

### H.20.3 — Compare assertion stress with evidence thickness

Two enactments give

```text
V_BR = 2/10 = 0.20 V_c
V_sugg/V_BR = 6.0/0.20 = 30
30/0.5 = 60 times the derated design limit.
```

Ignoring the rating clamp for a moment, the condition `6.0 ≤ 0.5(n/10)` requires `n ≥ 120` enactments. At six per week that is 20 weeks total, or `118/6 = 19.67` additional weeks after the two already logged.

But the canonical store rating clamps at `V_BR=8.0`, whose half-rating limit is only 4.0. Therefore the six-point assertion never becomes admissible on this board, even at 120 nominal enactments. The safe repair is to lower `V_sugg` to at most 4.0—and much lower early on—not to wait for a rating the component cannot possess.

### H.20.4 — Separate an audit load from a recoil

`^3` Negative is “an Idea the Mind is adverse to and repelled by.” The sentence “this is pointless; I should be doing something useful” takes the session apart, compares it with another use of time, and tests its worth. That is `^6^C_{F6}|A`, analytical decomposition, not visceral `^3^E_{F3}|f`.

The `^6` repair is Chapter 20's notch-and-sample arrangement, using the Chapter 11 notch: move the audit off the in-session signal path and run it later as a bounded, high-impedance measurement. A genuine `^3` recoil calls for Chapter 9's rate repair—lower amplitude, lengthen the taper, and reduce `di/dt`. Silencing a real recoil with the notch would remove the safety reading rather than fix the cause.

### H.20.5 — Replace daily chatter with hysteresis

For `P(t)=10(1−e^(−t/18))`, the single 8.5 threshold is reached at

```text
t_8.5 = −18 ln(1−0.85) = 18 ln(6.667) = 34.15 days.
```

Leakage there is `8.5/25 = 0.34 points/day`. With the chapter's daily oscillator, the level falls below the threshold inside one day and the next session pushes it back above, so the gate chatters on an approximately one-day period. The operator experiences an alternating “formed/not formed” verdict every day.

With thresholds 8.0/9.0:

```text
t_8 = 18 ln 5  = 28.97 days
t_9 = 18 ln 10 = 41.45 days
top-up interval = 25 ln(9/8) = 2.94 days.
```

The operator instead experiences one continuous formation run across a 12.48-day band, followed by a predictable maintenance top-up about every three days. The band turns a judgement into a schedule.

### H.20.6 — Build the smallest safe self-board

The reference check is

```text
τ_ref/τ_work = 40/10 = 4.0 ≥ 3  → PASS.
```

At the requested target,

```text
T_max = ΔP τ_leak/P_target = 0.30(20)/8.5 = 0.706 d
cadence = 7/0.706 = 9.92 sessions/week.
```

One session a day reaches only `P_eq=0.30(20)=6.0`, so 8.5 is not reachable at that cadence. I would initially lower the target to 6.0 rather than increase deposit without evidence; raising `ΔP` to the required `8.5/20=0.425` is acceptable only after the limiter shows enough `V_BR`. The reference's maximum lawful slew is `10/40=0.25 points/day`, so `F1` is set to 0.25.

```cas
board answer_h_20_6 {
    input: intent;
    output: enacted;

    node ref_composition:  ^5^P_{F7}|T;
    node work_composition: ^5^C_{F5}|⟨A,E⟩;
    node intent:           ^0^C_{F7}|A;
    node cadence:          ^7^C_{F6}|A;
    node cue:              ^8^O_{F6}|E;
    node enacted:          ^9^O_{F5}|E;

    capacitor c1: Capacitor< node=ref_composition, tau=40.0,
                             leak_tau=120.0, V_BR=8.0 >;
    capacitor c2: Capacitor< node=work_composition, tau=10.0,
                             leak_tau=20.0, V_BR=8.0 >;
    cjt q1: CJT< intent | ref_composition => work_composition >
            [β=1.5, sat=0.60, rπ=8.0, region=active];

    schmitt g1: Schmitt< sense=work_composition,
                         on_below=5.5, off_above=6.5 >;
    osc osc1: Oscillator< signal=cue, source=cadence, period=1.0,
                          duty=0.04, sustain=120.0, gate=g1 >;
    cjt q3: CJT< cue | work_composition => enacted >
            [β=1.0, region=active];

    filter lp1: LowPass< in=enacted, out=evidence_trend, tau=21.0 >;
    fuse f1: Fuse< ref_composition, threshold=0.25,
                    action=open_feedback >;
    feedback evidence_trend -> ref_composition [β=0.05];

    probe tp1: work_composition;  probe tp2: enacted;
    probe tp3: q1;  probe tp4: ref_composition;
}
```

`LP1` retains Chapter 8.4's `τ=21 d` floor and `β=0.05` ceiling, and its O→P path terminates only at the bias. The revised 5.5/6.5 gate honestly implements the reachable first-stage target; after evidence justifies a larger deposit, the 8.0/9.0 band can be restored in a logged revision.

### H.20.7 — Read the slow store, not the amplifier

The operator is misreading TP1, the working composition, as if it were the identity reference. TP1 at 9.50 and TP2 at 0.86 say the behaviour is formed and the schedule ran; the correct identity reading is TP4 at 5.40, still charging lawfully.

If suggestion voltage scales with `β`,

```text
V_sugg,new = 2.4(5.0/1.5) = 8.0
half-rating = 0.5(5.7) = 2.85
8.0/2.85 = 2.81 times the derated limit.
```

It also exceeds `V_BR=5.7`, entering store puncture rather than “making it land.” The correct intervention is to leave gain at 1.5 and continue the existing evidence cadence: TP4's `0.05 points/day` is below the `0.12` slew fuse, while TP1 and TP2 already show success. At the observed local slope, the remaining `9.50−5.40=4.10` points would be about 82 days, though the exponential model—not a linear forecast—governs the actual tail.

The circuit cannot tell the operator what the word “musician” ought to mean to them, whether adopting it remains wanted, or whether another life circumstance explains the report. It can distinguish the two stores; it cannot adjudicate identity.

## Chapter 21

### H.21.1 — Let the object-premium probe decide

The two A0 differences are

```text
witness_load   = 0.70 − 0.66 = 0.04
object_premium = 0.70 − 0.58 = 0.12.
```

`witness_load=0.04 < 0.30`, so the desire is not witness-carried and F1 remains intact. `object_premium=0.12 < 0.20`, so the named target is indistinguishable from the underlying condition and M1 returns `PROXY_TARGET`; the gate holds.

The object-premium instrument alone decided the result. The repair is to use `^6` decomposition to name the condition directly, then take three fresh readings before doing either subtraction. A pass on one A0 half cannot compensate for failure on the other because the gate is an AND, not a score.

### H.21.2 — Pay every descent drop

The desire begins at `^P`, so all three junctions are crossed:

```text
ΣVf = 0.7 + 1.2 + 2.0 = 3.9 V_c
V_drive = 8 + 5 = 13 V_c
R = 15 + 40 + 10 + 5 = 70 Ω_c
I_attention = (13 − 3.9)/70 = 0.130 A_c
margin = 0.130/0.10 = 1.30.
```

The verdict is **MARGINAL**: it fires today but lacks the required 2× campaign margin. I would repair `R_context=10` first, even though `R_policy=40` is largest, because context is the cheapest reversible term—a clarification or schedule definition can move it without rewriting a principle. Changing the policy term merely because it is numerically largest would edit the operator's guardrail to make the gate pass.

### H.21.3 — Quantify the naive overstatement

The naive calculation is

```text
I_naive = 13/70 = 0.1857 A_c
margin_naive = 0.1857/0.10 = 1.857.
```

The correct margin from H.21.2 is `1.300`. The relative error is

```text
(1.857 − 1.300)/1.300 = 0.4286 = 42.9%.
```

The naive reading nearly reports a PASS where the actual gate is MARGINAL. The error grows as the origin moves upward because a higher-domain desire must cross more P→C→E→O junctions; `ΣVf` consumes a larger fraction of the same drive before the resistance stack receives it.

### H.21.4 — Refuse a weighted W-gate

Six possession boxes cannot override `clarity=0.52`, because item 1 itself requires at least 0.60; the correct output is `HOLD: IDEA_UNFORMED`, followed by rewriting the condition as one concrete scene. The invariant is S1—readiness gates are AND gates, never weighted sums—so allowing the score would arm an undefined operation whose `^0` Idea has not been formed.

The resulting operation is not “slightly less ready.” It is a cast whose cause terminal contains a sentence rather than the scene the selected board expects, so every downstream measurement would be about a different input.

### H.21.5 — Re-plan the capacity gate two ways

The plan consumes

```text
planned   = 6(25) = 150 min
available = 18(15) = 270 min
load      = 150/270 = 0.556.
```

Because `0.556 > 0.50`, the P-gate holds. Changing operation count, five operations use `5(25)=125 min`, giving `125/270=0.463`, which passes. Holding six operations fixed, the half-load rule requires at least `150/0.50=300` available minutes. At 15 minutes per day that means a 20-day horizon, where `150/(20×15)=0.500`, exactly on the limit. The first plan gives up one operation; the second gives up two days of speed.

### H.21.6 — Build a counter-operation, not a fictitious inverse

(a) The requested un-cast is an inverse to realization: a path from the post-cast prerequisite state `R(I)'` back to the original `R(I)`, undoing `ε_I : R(I) → I`. That arrow is exactly what `η_I ∘ ε_I ≠ id_R(I)` says is absent.

(b) `β=∞` changes gain on an existing component; it cannot create a missing morphism. It is also non-finite input that the validator rejects, but even a very large finite β would only amplify a newly declared forward path. It would not erase the log row, the operator's experience, or the fact that the first cast occurred.

(c) Build a new counter-operation with its own A0, D, W, and P gates and its own ledger. It may mitigate consequences or establish a different state. It differs from reversal because both operations remain in the history and the second begins from `R(I)'`, not from the original prerequisite configuration.

### H.21.7 — Count re-entry without forcing a cast

One canonical addition uses an integrator as the counter, counts only while no cast has occurred, and emits a review flag after the fourth re-wording:

```cas
board answer_h_21_7_reentry {
    input: reword_event;
    output: review_flag;

    node practice_rail: ^5^P_{F7}|T;
    node reword_event:  ^7^O_{F6}|E;
    node cast_event:    ^9^O_{F5}|E;
    node reentry_count: ^6^E_{F6}|A;
    node review_flag:   ^9^E_{F6}|A;

    gate no_cast: NOT< cast_event >;
    gate countable_reword: AND< reword_event, no_cast >;
    integrator reentry: Integrator< in=countable_reword,
                                    out=reentry_count, window=campaign >;
    monitor m_reentry: Monitor< signal=reentry_count, limit=[0.0, 3.0],
                                action_on_violation=HOLD_FOR_REVIEW >;
    cjt flag: CJT< reentry_count | practice_rail => review_flag >
              [β=1.0, sat=0.85];
}
```

The campaign window closes when `cast_event` makes `no_cast` false; a later target starts a fresh ledger instance rather than mutating the old count. It catches **gate churn**: repeated decomposition becoming a way to avoid choosing or testing any target. The opposite failure it introduces is **premature fixation**—the operator may treat the fourth wording as forbidden and cast a worse third wording merely to avoid the flag. Therefore the action is HOLD_FOR_REVIEW, never ARM and never permanent rejection.

## Chapter 22

### H.22.1 — Compute the row and act on the smooth quantity

A 20-minute operation lies in the 10–30 minute working band, so `^7 = 2°`. The coupling sum and timing ratio are

```text
S = m + v = 2 + 2 = 4
A = 3t_conf/t_op = 3(75)/20 = 11.25.
```

`A=11.25` is in the RE-SPEC band (`A ≥ 9`). Act on `A`: stop raising amplitude and return to decomposition or route selection. Record `S=4` only as the ordinal cross-check. It cannot rescue the row, be averaged as a magnitude, or be traded against the timing ratio.

### H.22.2 — Diagnose a flat circuit under improving conditions

The `S` series improves from 4 to 3 and then stays there, while `A` remains near 9 despite every β increase. Under §22.5, `A` flat while `S` falls means operating conditions improved but the circuit did not. Because the changed lever was repeatedly the amplifier, the named failure mode is **saturation blindness** (or an amplifier change that never reaches delivered current): the stage has pinned and larger β values all produce the same output.

The first demanded measurement is a proof-load across the amplifier: increase its cause by 20% while observing the effect before and after the stage. If the cause moves and the effect does not, the stage is on its ceiling. Until that measurement passes, no further β change is admissible and the pleasant fall in `S` remains an operator-condition reading.

### H.22.3 — Enforce three separate anti-hindsight rules

First, six hours is over the two-hour edge, so the vibration grader assigns `^4 = 3°`, not 1°. Second, grading the following morning violates H2's thirty-minute hold from noticing; the stored impression is already reconstruction. Third, waiting until manifestation and then assigning the grade violates the write-once fuse F3: it lets outcome knowledge revise the record.

The correct entry is `3°`, written within thirty minutes of noticing the first confirmation and then permanently latched. If the grade was not captured in that window, the honest entry is a late/invalid-grade flag rather than a retrospectively improved 1°. The event may still remain in prose, but it cannot enter a comparable row under the claimed grade.

### H.22.4 — Keep the row that supplied no ratio

The deletion argument is superficially tidy: Op 4 has no `t_conf`, so it yields neither `A` nor `S`, cannot enter the three-row trend, and appears to add no numerical information.

That is exactly why it must stay. NO-READ is the observation that no qualifying confirmation arrived inside a horizon fixed in advance; deleting it conditions the log on successes and makes the apparent confirmation rate exceed the operator's base rate by construction. The row still preserves `^1`, `^7`, the declared horizon, and the absence itself, so it constrains any later claim that “every operation confirmed.” It is excluded from the ratio, not erased from the evidence.

### H.22.5 — Reject multiplication of ordinal grades

Measurement-theory objection: `m` and `v` are ordinal bins whose intervals and zero points are undefined, so multiplying them asserts ratio-scale structure the instrument does not possess.

CAS-notation objection: the readings are distinct co-present states joined by `+`; `×` would assert a fused emergent state, and no such result is named or defined.

I would put the measurement objection first in design review because it invalidates `S'` independently of this book's notation and prevents a superficially compilable implementation from being treated as quantitative. The notation objection follows as the repository-enforceable form of the same discipline.

### H.22.6 — Flag an attribution collision and retain the row

The collision stage sits after the first-only limiter and before row assembly. It is a coincidence/AND gate over the admitted confirmation and the count of other operations whose horizons are still open:

```cas
board answer_h_22_6_collision {
    input: admitted_confirmation;
    output: flagged_row;

    node admitted:    ^9^C_{F2}|A;
    node other_live:  ^7^C_{F6}|A;
    node operation_set: ^5^P_{F7}|T;
    node collision:   ^6^E_{F6}|A;
    node flagged_row: ^6^O_{F6}|A;

    gate g_collision: AND< admitted, other_live >;
    cjt flag_collision: CJT< g_collision | operation_set => collision >
                        [β=1.0, sat=0.85];
    monitor m_collision: Monitor< signal=collision, threshold=1.0,
                                  action_on_violation=AMBIGUOUS >;
    mux retain: MUX< inputs=[admitted, collision],
                      select=m_collision >;
    diode d_log: Diode< ^E -> ^O >;
}
```

The component type is a coincidence gate backed by a monitor. Its location ensures later confirmations cannot enter and ensures ambiguity is known before the row is latched. It must **not** delete, reassign, or improve the row; it marks `AMBIGUOUS`, retains both candidate operation IDs, and excludes that confirmation from ratios and the rolling median.

### H.22.7 — Keep the scope fuse

F4 belongs on the board because S1 is a scope invariant that no numeric reading can test. The physical event that blows it is routing a row, degree, or trend into a comparison with another operator or into a claim presented as externally validated. The fuse then permanently blocks that export path while leaving the operator's own ledger intact.

Without F4 the enforcement mechanism would be a person reading the intended-use statement and declining to export the scale. That may be good practice, but it is not a circuit: it has no terminal, continuity state, or test point. Since the board claims every safety invariant has enforcement, leaving S1 to memory while pretending otherwise would be the decorative choice.

## Chapter 23

### H.23.1 — Reduce the pair and blow the re-spec fuse

The raw timing ratio is

```text
η = t_op/t_conf = 45/240 = 3/16 = 0.1875.
```

Applying the one-third scale,

```text
η/3 = (3/16)(1/3) = 1/16,
(a,b) = (1,16),
A = b/a = 16
  = 3(240)/45.
```

`A=16` is in RE-SPEC. The first response is decomposition of the target or a lower-resistance route, because the number is already beyond the amplifier-instruction boundary. Raising β would misread `A` as a component setting, compound demand, and hide the target or resistance fault that the fuse is designed to surface.

### H.23.2 — Let the stable ratio outrank the unstable pair

Raw reduction:

```text
(t_op)/(3t_conf) = 27/192 = 9/64,
(a,b) = (9,64),
A_raw = 3(64)/27 = 7.11.
```

On the five-minute grid, `27 → 25` and `64 → 65`:

```text
25/(3×65) = 25/195 = 5/39,
(a,b) = (5,39),
A_grid = 3(65)/25 = 7.80.
```

The pair changes from `(9,64)` to `(5,39)`—not a small perturbation—while both `A` readings remain in DRIVE and call for one-lever work. Because `a>3` in both reductions, discard the pair and act on `A`; the comparison demonstrates that the smooth quotient is the usable instrument.

### H.23.3 — Recognize a decline that is too slow

The convergence ratios are

```text
ρ_1 = 9.6/12.0 = 0.800
ρ_2 = 7.7/9.6  = 0.802
ρ_3 = 6.2/7.7  = 0.805.
```

The series is falling, but it is not converging by the chapter's `ρ ≤ 0.6` design threshold. Using the latest `ρ=0.805`, solve

```text
6.2(0.805)^n ≤ 1
n ≥ ln(1/6.2)/ln(0.805) = 8.42,
```

so nine further operations would be needed if that rate held. I would not keep casting to realize that projection: by operation three the sustained ratio has failed the threshold, and demand is compounding. Stop, return to A0/decomposition, and change the target, route, or resistance before another operation.

### H.23.4 — Shed the densest coupling first

Label the F5 operations A and B, the unrelated F2 operation C, and the F4 same-person operation D. The six pairings are:

```text
A–B: 0.35  (same Drive, shared sigil alphabet)
A–C: 0.05  (different Drive/domain, no shared symbol)
B–C: 0.05
A–D: 0.35  (assuming A is the same-person F5 operation)
B–D: 0.05
C–D: 0.05
```

The mean pair coefficient is `(0.35+0.35+4×0.05)/6 = 0.15`. For `N=4`,

```text
k(N−1) = 0.15(3) = 0.45,
```

above the 0.30 design ceiling. Shed D first because it removes the second 0.35 edge. The remaining A/B/C network has mean `k=(0.35+0.05+0.05)/3=0.15`, so `k(N−1)=0.30`, exactly at the ceiling. For working margin, shed either A or B next; the remaining different-Drive pair has `k(N−1)=0.05`.

### H.23.5 — Derate a cast into another band

For `N=3`, `k=0.35`,

```text
derating = 1 − k(N−1) = 1 − 0.35(2) = 0.30
η_effective = 0.75(0.30) = 0.225.
```

Thus

```text
t_conf = t_op/η_effective = 40/0.225 = 177.78 min
        → 180 min on the five-minute grid,
A = 3(180)/40 = 13.5.
```

In isolation, `A=3/0.75=4.0`, inside DRIVE. Under concurrency, `A=13.5`, so the band changes to RE-SPEC. The cast itself need not be repaired; shed the related live operations until `k(N−1)≤0.3`, then take a fresh attributable reading.

### H.23.6 — Delete the tautology, keep the trend

Six 9.0 entries prove only that the absolute-target column was computed from quantities defined to cancel; a column that cannot vary would stay flat for a converging, stalled, or diverging campaign. Show me the comparable `A` values and the `ρ=A_next/A_current` column instead—`ρ≤0.6` across at least three operations is the chapter's evidence of convergence.

That is the complete two-sentence reply. The absolute column may be retained as an algebra check, but it must not appear as a campaign finding.

## Chapter 24

### H.24.1 — Rank three guard knees

Using `knee=sat/β`:

```text
[β=2.0, sat=0.85]: knee = 0.85/2 = 0.425
[β=3.0, sat=0.85]: knee = 0.85/3 = 0.283
[β=3.0, sat=0.60]: knee = 0.60/3 = 0.200
```

Ranked by assessed risk required to latch, from most to least: 0.425, 0.283, 0.200. For an operator who has just blown a fuse for the first time, I would temporarily build the `β=3.0, sat=0.60` guard because it stops listening earliest while the event is reviewed. The cost is more false refusal and less room for evidence before saturation; after the review and charter check, returning to the canonical 0.85 ceiling may be justified.

### H.24.2 — Move the fuse to a reachable enforcement path

Across Q4, the fuse never blows: the guard clamps at 0.85 and cannot reach threshold 0.90. The compiler accepts the listing because each value is locally valid, and the operator believes a permanent block exists even though the fuse is dead metal.

The two-line correction is:

```cas
cjt q7: CJT< guard | charter => blocked > [β=10.0, sat=0.98, cutoff=0.80];
fuse f1: Fuse< blocked, threshold=0.90, action=permanent_block >;
```

Q4's `0.85` ceiling clears Q7's `0.80` cutoff by 0.05, and Q7's `0.98` ceiling clears F1's `0.90` threshold by 0.08. Both margins must be checked; either missing margin produces a silent safety failure.

### H.24.3 — Rerun the Commission at the lawful dial edge

The divider becomes

```text
k = Dial(^2)/(Dial(^2)+Dial(^3)) = 8/(8+4) = 0.667.
intake = 0.48(0.667) = 0.320.
```

Q1 requests `0.320(3)=0.960` and clamps at its 0.80 ceiling. With the same two attractive and four aversive readings:

```text
attraction = [0.80(2/6)](2.0) = 0.533
aversion   = [0.80(4/6)](2.0) = 1.067 → clamps at 0.900
risk       = 0.900 − 0.533 = 0.367
Q5         = 0.367(1.5) = 0.550
Q6         = 0.550(1.0) = 0.550 assessed risk.
```

The guard requests `0.550(3)=1.650`, clamps at 0.85, and latches; Q7 then reaches 0.98 and F1 enforces. The design conclusion is that a lawful attraction-heavy dial setting does not defeat a matched, charter-biased differential on a structurally refusable proposal. Q1 does saturate, so the board must still be proof-loaded on benign proposals to ensure the pre-amp is not making everything look maximal.

### H.24.4 — Keep evaluation `^6` and refusal `^3`

The canonical definition is: `^3` Negative is “an Idea the Mind is adverse to and repelled by.” Q6 names and weighs the proposal's parts; that is analytical decomposition, so `^6^E_{F6}|A` is exact. Typing it `^3^E_{F3}|f` would turn an audit into a felt recoil and destroy the distinction between evidence and refusal.

The anti-drift rule is **“`^3` Negative is visceral aversion, not analysis”**: “I cannot stomach that” supports `^3`; “let me test its premises” supports `^6`. Q4 is correctly `^3^P_{F7}|⟨A,f,T⟩` because it is the principled, multi-register refusal that follows the audit and stops responding once saturated.

### H.24.5 — Give an intermediate operator a slower charter filter

Two years places the operator in the **intermediate** band, one to three months. I would set `LP1 τ=60 days`, the middle of that band, rather than inherit the adept default of 21 days.

The charter alone could move at most `10(1−e^(−56/85))=4.83` points over 56 days under a full-scale step; LP1 makes the actual response slower. For a sustained step passed through LP1 and then the 85-day charter, the normalized two-pole response is

```text
y(t) = 1 − [85e^(−t/85) − τ_f e^(−t/τ_f)]/(85 − τ_f).
```

At eight weeks (`t=56 d`):

```text
τ_f=21 d: y=0.3355 of the eventual feedback-driven displacement;
           slew at day 56 = 0.006999 ΔP∞ points/day.
τ_f=60 d: y=0.1844 of the eventual feedback-driven displacement;
           slew at day 56 = 0.004969 ΔP∞ points/day.
```

Here `ΔP∞` is the eventual charter displacement after the feedback gain and input scale are applied. Even at the largest possible ten-point displacement, the two day-56 slews are only 0.070 and 0.050 points/day. TP3 therefore shows substantially more movement under the inherited adept setting, while the 60-day setting preserves more of the dated baseline. Both remain below F2's `0.12 points/day`, so the slew fuse distinguishes neither; only TP3 compared with a current dated baseline distinguishes the accumulated movements.

### H.24.6 — Integrate a sequence that never reaches the guard knee

Choose a 30-day rolling window and a threshold of 1.0 risk-unit—roughly four proposals just below the 0.283 knee. The component observes the already-assessed internal risk and has no outward terminal:

```cas
board answer_h_24_6_subthreshold {
    input: assessed;
    output: accumulated;

    node charter:        ^5^P_{F7}|T;
    node assessed:       ^6^E_{F6}|A;
    node accumulated:    ^6^E_{F6}|A;

    integrator risk_memory: Integrator< in=assessed, out=accumulated,
                                        window=30.0 >;
    monitor sequence_limit: Monitor< signal=accumulated,
                                     limit=[0.0, 1.0],
                                     action_on_violation=BLOCK_REVIEW >;
    fuse f_sequence: Fuse< accumulated, threshold=1.0,
                            action=block_until_decomposed >;

    probe tp_each: assessed;
    probe tp_sum: accumulated;
}
```

The chosen threshold makes a repeated near-knee sequence visible without treating one low-risk proposal as a refusal. It does not fix **charter drift** or a dead guard: if the upstream charter and differential assess formerly refusable proposals as zero or negative, the integrator receives nothing honest to accumulate. Q4's saturation offers no protection because saturation is memoryless; each proposal remains below 0.283, the cause disappears between proposals, and Q4 stores no sum.

### H.24.7 — Restore the charter before tuning the guard

(a) The combined signature is charter drift producing a dead guard: TP1 is zero under a proof-load, TP2 never arms, and TP4 is negative on a proposal that once produced refusal. Lowering Q4's cutoff cannot repair an exhausted or shifted bias, an imbalanced differential, or a non-positive assessed-risk input; zero multiplied by the guard gain remains zero.

(b) Using a 30-day month for the stated eleven-month interval,

```text
movement bound = 0.041 points/day × 330 days = 13.53 points.
```

That exceeds the entire 0–10 charter scale. F2 would never open because `0.041 < 0.12 points/day` at every sample; the fault is a slow slope, not a slew event.

(c) Bring-up follows TP1–TP4. First restore and date C1, then proof-load TP1 and require a live guard response (normally ≥0.15, reaching 0.85 on the known refusable case). Second read TP2 and verify Q7 reaches 0.98 and F1's continuity matches its dated record. Third set LP1 to the operator's proper band and read TP3 as both slew and displacement from the new written baseline. Fourth re-match Q2/Q3 on one bias net and require TP4 near zero on benign proposals and positive on the proof-load.

C1, the charter capacitor, must be brought into spec before any other reading means anything because every guard stage takes bias from it. The circuit still cannot tell the operator what their charter ought to say, whether the old refusal was ethically correct, or whether their wider situation calls for human support; it can only show that the present board is not enforcing the reference it claims to enforce.
