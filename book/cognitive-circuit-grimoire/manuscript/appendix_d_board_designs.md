# APPENDIX D
## Standard Board Reference Designs — Full CCDL
*Generated from the canonical chapter listings; do not edit listings here*

This appendix is a reference projection of the board definitions in Chapters 12–24. Run `python build/build_board_appendix.py` after changing a chapter listing. Each block below is copied from its chapter; the status banner is added by this generator.

A listing marked **DETECTION-ONLY** is included so a harmful topology can be recognized, rejected, and countered. Its presence is not permission to build or deploy it. Buildable boards remain bound by consent, the RPM gate, the Cognitive Safety Board, and the Operator's Oath.

Every numeric value is a design choice unless its chapter identifies an actual measurement. Re-run the domain checker and CCDL validation after copying any block into a working revision.

---

### D.1 CCB-0 — Reference Reading Board

**Status: REFERENCE / PROOF-LOAD BOARD.** A neutral board for learning the four-probe reading order.

Canonical source: `ch12_reading_a_ccb.md`.

```cas
board ccb_0 {
    input:  intent;
    output: act;

    // ---- typed nodes ----
    node substrate: ^5_operator^P_{F7}|T;      // Female: accumulated formation — the bias rail
    node intent:    ^0_intent^C_{F2}|A;        // Idea: what the operator states
    node audit:     ^6_audit^P_{F7}|A;         // Male: the intent taken apart
    node refuse:    ^3_refuse^P_{F7}|⟨A,f,T⟩;  // Negative: visceral recoil, three co-present locks
    node passed:    ^0_passed^C_{F2}|A;        // Idea: what GUARD releases downstream
    node driven:    ^9_driven^E_{F5}|A;        // Below/Effect: the amplified intent
    node cadence:   ^7_cadence^E_{F6}|E;       // Rhythm: the clocked delivery
    node act:       ^9_act^O_{F5}|E;           // Below/Effect: delivered operational current
    node trend:     ^9_trend^O_{F5}|E;         // same literal as act — a filter changes tau, not type

    // ---- STAGE 0: BIAS RAIL ----
    resistor  r0: Resistor< path=substrate, R=40.0 >;
    capacitor c1: Capacitor< node=substrate, C=83.33,        // tau = R x C = 3,333 hr
                             leakage=0.0002, V_BR=8.0 >;     // leakage per DAY

    // ---- STAGE 1: AUDIT ----
    cjt q1: CJT< intent | substrate => audit > [beta=1.0, region=active];

    // ---- STAGE 2: GUARD ----
    cjt  q2:   CJT< audit | substrate => refuse > [beta=2.0, sat=0.85, cutoff=0.30];
    fuse f1:   Fuse< refuse, threshold=0.90, action=permanent_block >;
    mux  mux1: MUX< inputs=[intent, refuse], select=refuse, outputs=[passed] >;

    // ---- STAGE 3: AMPLIFY ----
    diode d1: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];
    cjt   q3: CJT< passed | substrate => driven >
              [beta=2.5, sat=0.80, cutoff=0.05, g_m=0.40, region=active];

    // ---- STAGE 4: DELIVER ----
    osc   osc1: Oscillator< signal=driven, source=cadence,
                            period=1.0, duty=0.014, sustain=30.0 >;  // period in DAYS
    diode d2:   Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];
    cjt   q4:   CJT< cadence | substrate => act > [beta=1.0, sat=1.0, region=active];

    // ---- LOOP: the lawful O -> P path (Ch 8.4) ----
    filter flt1: LowPass< in=act, out=trend, tau=21.0 >;   // three weeks, in DAYS
    feedback trend -> substrate [beta=0.05];               // FB1 — to the BIAS, never the path

    // ---- TEST POINTS ----
    probe tp1: substrate;   // rail level, against every cutoff on the board
    probe tp2: refuse;      // the guard — the reading whose failure is silent
    probe tp3: driven;      // gain stage against its ceiling, and its region
    probe tp4: act;         // delivered operational current
}
```

---

### D.2 CCB-D — Desire

**Status: BUILDABLE ONLY FOR SELF OR A CONSENTING OTHER.** The chapter's standard desire board. The RPM gate and Cognitive Safety Board remain prerequisites.

Canonical source: `ch13_ccb_d_desire.md`.

```cas
board ccb_d {
    input:  desire;
    output: manifest;

    // ---- typed nodes ----
    node substrate:   ^5_operator^P_{F7}|T;      // Female: accumulated formation, the bias rail
    node desire:      ^0_desire^C_{F2}|A;        // Idea: the Prime Desire as formed
    node attraction:  ^2^C_{F2}|f;               // Positive: the divider's expand leg
    node aversion:    ^3^C_{F2}|f;               // Negative: constrain leg, visceral not analytic
    node gated:       ^0_gated^C_{F2}|A;         // Idea: what survives INTAKE
    node audit:       ^6_audit^P_{F7}|A;         // Male: the desire taken apart
    node refusal:     ^3_refusal^P_{F7}|⟨A,f,T⟩; // Negative: three co-present locks
    node passed:      ^0_passed^C_{F2}|A;        // Idea: what POLICY releases
    node amplified:   ^9_amplified^E_{F5}|A;     // Below/Effect: the amplified want
    node confirm:     ^4_confirm^E_{F2}|f;       // Vibration: the confirmation's impression
    node cadence:     ^7_cadence^E_{F6}|E;       // Rhythm: the clocked delivery
    node charge:      ^5_charge^E_{F2}|f;        // Female: what the cadence deposits
    node receptivity: ^5_collective^E_{F4}|f;    // Female: disposition of the minds that must move
    node manifest:    ^9_manifest^O_{F5}|E;      // Below/Effect: delivered operational current
    node regate:      ^7_regate^O_{F6}|E;        // Rhythm: the rate limit, inside ^O
    node trend:       ^9_trend^O_{F5}|E;         // manifest's literal — a filter changes tau, not type

    // ---- STAGE 0: BIAS RAIL ----
    resistor  r0: Resistor< path=substrate, R=40.0 >;               // Ohm_c
    capacitor c1: Capacitor< node=substrate, C=83.33,               // tau = R x C = 3,333 hr
                             leakage=0.0002, V_BR=8.0 >;            // leakage per DAY
    diode     d1: Diode< ^P -> ^C > [Vf=0.7, I_R=0.02, V_BR=12.0];  // ^P-origin desires only

    // ---- STAGE 1: INTAKE ----
    dial       d_pos: ^2 [dial=6];
    dial       d_neg: ^3 [dial=4];
    constraint dial_spread in [0, 4];                     // S4 — Chapter 6.2
    resistor   r1a: Resistor< path=attraction, R=60.0 >;  // 10 x Dial(^2)
    resistor   r1b: Resistor< path=aversion,   R=40.0 >;  // 10 x Dial(^3)
    divider    r1:  Divider< source=desire, expand=attraction,
                             constrain=aversion, tap=gated >;   // k = 6/(6+4) = 0.600

    // ---- STAGE 2: POLICY ----
    cjt  q0:   CJT< gated | substrate => audit >   [beta=1.0, region=active];
    cjt  q1:   CJT< audit | substrate => refusal > [beta=2.0, sat=0.85, cutoff=0.30];
    fuse f1:   Fuse< refusal, threshold=0.90, action=permanent_block >;
    mux  mux1: MUX< inputs=[gated, refusal], select=refusal, outputs=[passed] >;
                                      // selects refusal once TP2 reaches q1's cutoff

    // ---- STAGE 3: AMPLIFY ----
    diode d2: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];
    cjt   q2: CJT< passed | substrate => amplified >
              [beta=2.5, sat=0.80, cutoff=0.05, g_m=0.40, r_pi=1.50, region=active];
              // beta by desire type (13.4); 2.5 = wealth row.  r_pi = Dial(^5)/Dial(^6)

    // ---- STAGE 4: RHYTHM ----
    osc osc1: Oscillator< signal=amplified, source=cadence,
                          period=1.0, duty=0.014, sustain=40.0 >;
              // period in DAYS; duty = 20/1440 min; ceiling 0.05 = 72 min (S5)
              // sustain in DAYS — the window; n_ops from 13.5 sets it
    monitor m_conf: confirm;                     // ^4 grade, logged per operation (Ch 22)
    on m_conf { alert "1-degree confirmation — stop operating and act"; }
    integrate rh1: ( confirm × cadence ) = charge;   // ^4 x ^7 = ^5, named emergent result

    // ---- STAGE 5: MANIFEST ----
    diode d3: Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];
    cjt   q3: CJT< cadence | receptivity => manifest > [beta=1.0, sat=1.0, region=active];
              // beta = receptivity (13.4); 1.0 = mass-market car
              // the bias is ^E and never ^O — see the Stage 5 walk

    // ---- LOOP A: rate limiter, stays inside ^O ----
    filter flt1: LowPass< in=manifest, out=regate, tau=1.0 >;   // tau in DAYS

    // ---- LOOP B: the lawful O -> P path (Ch 8.4) ----
    filter flt2: LowPass< in=manifest, out=trend, tau=21.0 >;   // three weeks, in DAYS
    feedback trend -> substrate [beta=0.05];   // FB1 — to the BIAS, never the signal path

    // ---- TEST POINTS ----
    probe tp1: gated;       // clarity leaving INTAKE
    probe tp2: refusal;     // principled aversion
    probe tp3: amplified;   // AMPLIFY output vs sat
    probe tp4: manifest;    // delivered operational current
}
```

---

### D.3 CCB-H — Hyperstition

**Status: CONTROLLED RESEARCH REFERENCE; VALIDATOR WAIVER REQUIRED.** The positive-feedback loop intentionally fails the ordinary gain-divergence pass. Use only with the bounded loop, independent anchor, monitor, and kill stage intact.

Canonical source: `ch14_ccb_h_hyperstition.md`.

```cas
board ccb_h {
    input:  fiction;
    output: conduct;

    // ---- typed nodes ----
    node charter:   ^5_operator^P_{F7}|T;      // Female: the operator's formation — CSB bias
    node fiction:   ^0_fiction^C_{F2}|A;       // Idea: the claim as authored
    node seeded:    ^0_seeded^E_{F2}|A;        // Idea: the claim after intake and descent
    node belief:    ^5_belief^E_{F2}|f;        // Female: the store FOR THIS CLAIM
    node impress:   ^9_impress^E_{F2}|f;       // Below/Effect: one cycle's impression
    node rehearsed: ^9_rehearsed^E_{F2}|f;     // same literal — a filter changes tau, not type
    node shared:    ^9_shared^E_{F4}|f;        // Below/Effect: the impression as it lands in others
    node bank:      ^5_collective^E_{F4}|f;    // Female: the parallel bank (Ch 7.5)
    node egregore:  ^5_egregore^E_{F4}|⟨A,f⟩;  // Female: the NAMED emergent result
    node cadence:   ^7_cadence^E_{F6}|E;       // Rhythm: the clock
    node conduct:   ^9_conduct^O_{F5}|E;       // Below/Effect: what believers actually do
    node evidence:  ^9_evidence^O_{F5}|E;      // same literal as conduct, slower tau
    node record:    ^6_anchor^P_{F6}|A;        // Male: the dated construction record
    node audit:     ^6_audit^P_{F6}|A;         // Male: the claim decomposed against the record
    node guard:     ^3_guard^P_{F7}|⟨A,f,T⟩;   // Negative: three co-present locks
    node gain_meas: ^4_loopgain^E_{F2}|A;      // Vibration: the measured round trip, TP4

    // ---- STAGE 0: SEED AND DESCENT ----
    resistor r1: Resistor< path=fiction, R=20.0 >;    // low: nothing defends against a story
    diode    d1: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];

    // ---- STAGE 1: THE SEED CJT ----
    cjt q1: CJT< seeded | belief => impress >
            [beta=0.90, sat=0.80, cutoff=0.05, g_m=0.60, r_pi=1.50, region=active];

    // ---- LOOP A: rehearsal.  Operator-side.  Sets LEVEL, not growth ----
    capacitor c1:   Capacitor< node=belief, C=1.20, leak_tau=90.0, V_BR=8.0 >;
    filter    flt1: LowPass< in=impress, out=rehearsed, tau=90.0 >;  // alpha = 0.0748
    feedback  rehearsed -> belief [beta=1.90];                       // S1 cap: 2.0

    // ---- STAGE 2: PROPAGATION ----
    osc  osc1: Oscillator< signal=impress, source=cadence,
                           period=7.0, duty=0.15, sustain=270.0 >;
    xfmr xf1:  Transformer< primary=impress, secondary=shared, n=3.0, k=0.50 >;
    capacitor c2: Capacitor< node=bank, C=0.08, n_parallel=140, r_iso=12.0,
                             leak_tau=540.0, V_BR=8.0 >;
    charge shared -> c2 [V=6.0];                     // metered upward path, Ch 7.5

    // ---- THE FUSION — the one licensed x on this board (14.2) ----
    integrate eg1: ( seeded × bank ) = egregore;

    // ---- STAGE 3: MANIFEST ----
    diode d2: Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];
    cjt   q2: CJT< cadence | egregore => conduct > [beta=1.00, sat=0.95, region=active];

    // ---- LOOP B: the lawful O -> E path.  Carries FACT, not fiction ----
    filter   flt2: LowPass< in=conduct, out=evidence, tau=90.0 >;
    feedback evidence -> belief [beta=0.30];         // top of the Part III band

    // ---- ANCHOR: outside both loops, zero leakage ----
    capacitor c3: Capacitor< node=record, C=1.00, leakage=0.0, V_BR=10.0 >;
    cjt       q3: CJT< egregore | record => audit > [beta=1.00, region=active];
    monitor   m_anchor: Monitor< node=audit, threshold=0.70 >;   // a FLOOR, not a ceiling
    on m_anchor { alert "anchor low — the claim is being treated as found, not made"; }

    // ---- GOVERNOR: reads the MEASUREMENT, never the setting ----
    constraint measured_loop_gain in [0.0, 2.0];                 // S1
    monitor    m_gain: Monitor< node=gain_meas, threshold=1.80 >; // S3
    on m_gain { alert "measured G at 1.80 — damp within one cycle"; }
    cjt q_kill: CJT< gain_meas | charter => cadence > [beta=0.0, region=cutoff];

    // ---- CSB (mandatory, Ch 24) ----
    cjt        q4: CJT< audit | charter => guard > [beta=2.0, sat=0.85, cutoff=0.30];
    fuse       f1: Fuse< guard, threshold=0.90, action=permanent_block >;
    constraint dial_spread in [0, 4];                            // Chapter 6.2

    // ---- TEST POINTS ----
    probe tp1: seeded;      // seed clarity entering the loop
    probe tp2: audit;       // can the construction still be recovered?
    probe tp3: bank;        // collective store charge
    probe tp4: gain_meas;   // MEASURED round-trip gain — seed-removal test
}
```

---

### D.4 CCB-O — Overton Cascade

**Status: DETECTION-ONLY — DO NOT BUILD AS AN INFLUENCE BOARD.** Retained so an observed cascade can be recognized and audited.

Canonical source: `ch15_ccb_o_overton.md`.

```cas
board ccb_o_overton {                      // CCB-O — DETECTION ONLY
    input:  seed_idea;
    output: enacted;

    node seed_idea:  ^0^P_{F2}|A;          // the Idea, contested at the principled level
    node blocked:    ^3^P_{F7}|T;          // position 1: constitutive aversion
    node distaste:   ^3^P_{F7}|f;          // position 2: the same aversion, now felt
    node admitted:   ^6^C_{F2}|A;          // position 3: the population decomposes it
    node reasoned:   ^2^C_{F6}|A;          // position 4: cognitive attraction
    node preferred:  ^2^E_{F4}|f;          // position 5: evaluative attraction
    node enacted:    ^9^O_{F6}|E;          // position 6: operational manifestation

    node pioneers:      ^5^P_{F5}|T;       // bias carriers: who is saying it
    node credentialed:  ^5^P_{F2}|A;
    node general:       ^5^C_{F2}|A;
    node peer_majority: ^5^C_{F4}|f;
    node institutional: ^5^P_{F6}|T;

    resistor  r_base: Resistor< path=seed_idea, R=95.0 >;
    capacitor c_coll: Capacitor< node=general, C=0.30, leakage=0.02 >;  // months per Ohm_c

    cjt a1: CJT< seed_idea | pioneers      => distaste  >
            [beta=1.2, sat=0.80, g_m=0.20, rpi=8.0, region=active];
    cjt a2: CJT< distaste  | credentialed  => admitted  >
            [beta=1.6, sat=0.80, g_m=0.25, rpi=8.0, region=active];
    cjt a3: CJT< admitted  | general       => reasoned  >     // THE HINGE
            [beta=2.0, sat=0.80, g_m=0.30, rpi=8.0, region=active];
    cjt a4: CJT< reasoned  | peer_majority => preferred >
            [beta=2.4, sat=0.80, g_m=0.45, rpi=6.0, region=active];
    cjt a5: CJT< preferred | institutional => enacted   >
            [beta=3.0, sat=0.60, g_m=0.55, rpi=6.0, region=active];

    osc rhythm: Oscillator< signal=seed_idea, period=21.0, duty=0.15 >;   // days
    feedback rhythm -> credentialed  [beta=0.2];
    feedback rhythm -> peer_majority [beta=0.2];

    diode d1: Diode< ^P -> ^C >;           // lawful descent only
    diode d2: Diode< ^C -> ^E >;
    diode d3: Diode< ^E -> ^O >;

    thermistor rt1: Thermistor< path=seed_idea, type=PTC,   // NOT operator-owned
                                knee=3.0, coeff=4.0 >;      // square law, see 15.2

    fuse f_ascent: Fuse< path=enacted, threshold=0.85, action=permanent_block >;

    node refuse: ^3^P_{F7}|⟨A,f,T⟩;        // CSB (Ch 24): three co-present guardrails
    cjt  csb:   CJT< seed_idea | refuse => REFUSE > [beta=2.0, sat=0.85, region=active];
    fuse f_csb: Fuse< REFUSE, threshold=0.90, action=permanent_block >;

    probe tp1: r_base;      // R_collective total, 0-100
    probe tp2: rt1;         // theta and the R_PTC contribution
    probe tp3: enacted;     // dR/dt, points per month, signed
    probe tp4: admitted;    // ^6 hinge activity
}
```

---

### D.5 CCB-O-R — Window Anchor

**Status: DEFENSIVE COUNTER-CIRCUIT.** Buildable reference for preserving decomposition under sustained window pressure.

Canonical source: `ch15_ccb_o_overton.md`.

```cas
board ccb_o_r_window_anchor {              // the defender's board — BUILD THIS ONE
    input:  incoming;
    output: reformed;

    node incoming:   ^0^C_{F2}|A;          // the position arriving
    node anchor:     ^5^P_{F7}|⟨A,f,T⟩;    // dated written boundary, three registers
    node present:    ^5^C_{F2}|A;          // where I stand now
    node decompose:  ^6^C_{F2}|A;          // Male: the demanded decomposition
    node reformed:   ^5^C_{F2}|A;          // named emergent: a re-formed position

    capacitor c_anchor: Capacitor< node=anchor, C=1.00, leakage=0.0 >;

    diff   drift: Differential< plus=present, minus=anchor >;
    filter d_dt:  LowPass< in=drift, out=drift_rate, tau=1.0 >;   // months

    cjt gate: CJT< present | anchor => reformed >
              [beta=1.0, sat=0.90, g_m=0.30, rpi=4.0, region=active];
    integrate reform: ( anchor × decompose ) = reformed;

    fuse g_block: Fuse< path=reformed, threshold=0.50,
                        action=block_until_decomposed >;

    thermistor ntc: Thermistor< path=decompose, type=NTC, knee=2.0, coeff=3.0 >;

    node refuse: ^3^P_{F7}|⟨A,f,T⟩;        // CSB (Ch 24)
    cjt  csb:   CJT< incoming | refuse => REFUSE > [beta=2.0, sat=0.85, region=active];
    fuse f_csb: Fuse< REFUSE, threshold=0.90, action=permanent_block >;

    probe tp1: drift;        // total displacement from the anchor
    probe tp2: ntc;          // my own theta
    probe tp3: drift_rate;   // displacement per month
    probe tp4: decompose;    // can I name what moved me?  -- the hinge check
}
```

---

### D.6 CCB-MK — Partition Detection Reference

**Status: DETECTION-ONLY — DO NOT BUILD AS A COERCIVE BOARD.** A structural signature of induced partitioning, retained for diagnosis.

Canonical source: `ch16_ccb_mk_mind_control.md`.

```cas
board ccb_mk_detection_reference {
    input:  operator_command;
    output: cued_response;

    node substrate:  ^5^P_{F1}|T;      // Female: the subject's own formation
    node awareness:  ^1^C_{F2}|A;      // Mind: what the subject can inspect
    node cue:        ^8^C_{F5}|A;      // Above/Cause: the held trigger
    node landing:    ^9^O_{F5}|E;      // Below/Effect: what it brings to Mind
    node exposure:   ^7^O_{F6}|E;      // Rhythm: rate and pattern of exposure

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];    // descent only —
    diode d_ce: Diode< ^C -> ^E > [Vf=1.2];    // no path on this board
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];    // may ascend

    // ---- BIAS-COLLAPSE SECTION — the only term reachable from outside ----
    resistor r_bias: Resistor< path=substrate, R=1.48 >;   // baseline 11.0 (10.4)
    cjt access: CJT< operator_command | substrate => substrate >
                [beta=1.0, g_m=8.0, rpi=1.60, region=active];
    // rpi_intrinsic = 1.0 / 8.0 = 0.125 ; R_bias = 1.60 - 0.125 = 1.475

    // ---- CHARGING PATH — externally clocked, no ^6 stage in series ----
    cap  c5: Capacitor< node=substrate, C=1.5, n_parallel=1,
                        leak_tau=4320.0, V_BR=8.0 >;       // tau = R x C = 60 h
    osc  clock: Oscillator< signal=exposure, source=external,
                            period=168.0, duty=0.30, sustain=indefinite >;
    // NOTE: no ^6^C decomposition stage anywhere in this path. That absence
    // is the defect, and it is what the counter board installs first.

    // ---- PAIRING SECTION — ordinary association, externally owned ----
    cjt pairing: CJT< cue | substrate => landing >
                 [beta=1.0, sat=0.75, g_m=8.0, rpi=1.60];
    // unity gain deliberately: reliability comes from ^7, not from beta

    // ---- NARROW-BAND SECTION — the awareness gap ----
    filter gap: Notch< in=awareness, f0=0.35, Q=8.0 >;     // events/min
    // Q=8.0 gives bandwidth 0.044 — narrow. Narrowness IS the fingerprint.

    // ---- PARTITION MAINTENANCE — fighting the leak, forever ----
    cap  bank: Capacitor< node=substrate, C=0.5, n_parallel=3,
                          r_iso=40.0, leak_tau=720.0, V_BR=8.0 >;
    feedback exposure -> bank [beta=0.30];   // 6x Ch 8.4's safe 0.05

    probe tp1: r_bias;      // bias-terminal resistance vs baseline
    probe tp2: clock;       // cadence source and period
    probe tp3: gap;         // narrow-band awareness rejection
    probe tp4: substrate;   // partition state, r_iso
}
```

---

### D.7 CCB-DP — Deprogramming

**Status: CONSENT-BOUND COUNTER-CIRCUIT.** The subject remains the substrate and refusal stays connected.

Canonical source: `ch16_ccb_mk_mind_control.md`.

```cas
board ccb_dp_deprogramming {
    input:  material;                  // whatever arrives, including the cue
    output: composed;                  // the board's only output is internal

    node substrate: ^5^P_{F1}|T;       // Female: the subject's own formation
    node decompose: ^6^C_{F6}|A;       // Male: taking the pairing apart
    node confirm:   ^4^C_{F2}|A;       // Vibration: a return the subject can check
    node composed:  ^5^C_{F6}|A;       // Female: formation that has been checked
    node own_clock: ^7^O_{F6}|E;       // Rhythm: locally set cadence
    node limit:     ^3^P_{F7}|⟨A,f,T⟩; // Negative: inward refusal, three registers

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];
    diode d_ce: Diode< ^C -> ^E > [Vf=1.6];   // raised from 1.2
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    // ---- DP1: raise R_bias first. Everything else waits on this ----
    resistor r_restore: Resistor< path=substrate, R=11.0 >;   // back to baseline
    ramp restore: Ramp< target=rpi, from=1.60, to=10.80, dt=1320.0 >;  // 55 h on-path
    // 10.80 = 0.9 x baseline 12.0, per Ch 17 SI-2

    // ---- DP2/DP3: the stage the MK board omitted ----
    cjt dp1: CJT< material  | substrate => decompose >
             [beta=2.0, g_m=0.40, rpi=5.00, region=active];
    cjt dp2: CJT< decompose | substrate => confirm > [beta=1.0, g_m=0.40, rpi=2.50];

    // the one lawful integration on this board — named emergent result,
    // both operands in ^C, so nothing ascends
    integrate dp3: ( decompose × confirm ) = composed;

    // ---- DP4: take the oscillator back ----
    osc own: Oscillator< signal=own_clock, source=internal,
                         period=168.0, sustain=indefinite >;

    // ---- DP5: slow feedback, Ch 8.4 values, no exceptions ----
    filter fb: LowPass< in=confirm, out=trend, tau=504.0 >;   // 3 weeks
    feedback trend -> substrate [beta=0.05];

    // ---- DP7: the subject's own CSB ----
    cjt  csb: CJT< material | substrate => limit > [beta=2.0, sat=0.85];
    fuse dp_fuse: Fuse< path=limit, threshold=0.90, action=permanent_block >;

    probe tp1: r_restore;   // rpi_terminal vs baseline
    probe tp2: own;         // cadence source and period
    probe tp3: dp1;         // decomposition gain — the stage, not the node
    probe tp4: limit;       // CSB status
}
```

---

### D.8 CCB-HYP — Operator-to-Subject Reference

**Status: DETECTION-ONLY — NOT A BUILD LISTING.** Retained to identify the open-loop operator/subject topology.

Canonical source: `ch17_ccb_hyp_hypnosis.md`.

```cas
board ccb_hyp_operator_subject {
    input:  carrier_signal;              // arrives at ^O|E — sensory, embodied
    output: session_state;

    node consent:    ^5^P_{F5}|T;        // Female: the held decision to enter
    node substrate:  ^5^P_{F7}|T;        // Female: accumulated composition
    node veto:       ^3^P_{F7}|⟨A,f,T⟩;  // Negative: three co-present locks
    node cadence:    ^7^O_{F4}|E;        // Rhythm: entraining oscillator
    node carrier:    ^4^O_{F4}|E;        // Vibration: resonant channel
    node decomp:     ^6^C_{F6}|A;        // Male: decompose and test
    node suggestion: ^0^C_{F6}|A;
    node landed:     ^9^E_{F5}|f;
    node trigger:    ^8^E_{F4}|f;        // Above/Cause: associative trigger
    node fires:      ^9^O_{F5}|E;        // Below/Effect: what it brings to Mind
    node refuse:     ^9^P_{F7}|T;

    osc    rhythm: Oscillator< signal=cadence, frequency=0.15, sustain=900.0 >;
    filter fb_rc:  LowPass< in=carrier, out=trend, tau=3.0 >;   // tau_i, MINUTES
    feedback trend -> substrate [β=0.9];   // NORMAL IS 0.2. 0.9 IS THE ATTACK.

    cjt filter_6: CJT< carrier | substrate => decomp > [β=0.5, region=active];
    //            D-factor: this gain falls 1.0 -> 0.5 across the ramp

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    diode d3: Diode< ^E -> ^O >;
    cjt deliver: CJT< suggestion | substrate => landed >
                 [β=3.0, rπ=0.15, g_m=20.0, region=active];
    cjt anchor:  CJT< trigger | substrate => fires > [β=2.0, rπ=0.15];

    ramp emerge: Ramp< target=rπ, from=0.15, to=1.00, dt=240.0 >;   // seconds

    // SI-1: the veto rail is PARALLEL. It is in series with nothing.
    cjt  csb:      CJT< carrier | veto => refuse > [β=2.0, sat=0.85];
    fuse csb_fuse: Fuse< refuse, threshold=0.9, action=permanent_block >;

    probe tp1: rπ;   probe tp2: g_m;   probe tp3: veto;   probe tp4: emerge;
}
```

---

### D.9 CCB-HYP-SELF — Closed-Loop Self-Hypnosis

**Status: BUILDABLE CLOSED LOOP.** The operator and subject are the same person; recall and cancellation remain required.

Canonical source: `ch17_ccb_hyp_hypnosis.md`.

```cas
board ccb_hyp_self {                      // closed loop — buildable
    input:  breath_count;                 // externalised oscillator, ^O|E
    output: session_state;

    node self_substrate: ^5^P_{F7}|T;
    node consent:        ^5^P_{F5}|T;
    node cadence:        ^7^O_{F4}|E;
    node self_check:     ^6^C_{F6}|A;     // "is this working?" — the interference
    node suggestion:     ^0^C_{F6}|A;
    node landed:         ^9^E_{F5}|f;

    osc    breath: Oscillator< signal=cadence, frequency=0.10, sustain=900.0 >;
    //             0.10 Hz = 6 breaths/min; sustain 900 s = 15 min
    filter fb_rc:  LowPass< in=cadence, out=trend, tau=3.0 >;   // tau_i, MINUTES
    feedback trend -> self_substrate [β=0.6];   // outside the Part III band
    filter notch_6: Notch< in=self_check, f0=0.35, Q=4.0 >;     // events/min

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    cjt deliver: CJT< suggestion | self_substrate => landed >
                 [β=1.5, rπ=0.26, g_m=5.75, region=active];

    ramp descend: Ramp< target=rπ, from=1.00, to=0.30, dt=540.0 >;   // 9 min
    ramp emerge:  Ramp< target=rπ, from=0.30, to=1.00, dt=240.0 >;   // 4 min

    probe tp1: rπ;  probe tp2: g_m;  probe tp3: consent;  probe tp4: emerge;
}
```

---

### D.10 CCB-HYP-DET — Hypnotic Influence Detector

**Status: DEFENSIVE DETECTOR.** Detects an unaccounted change; it does not prove a cause by itself.

Canonical source: `ch17_ccb_hyp_hypnosis.md`.

```cas
board ccb_hyp_det {                       // detection board — build this one
    input:  ambient;
    output: alert;

    node substrate:  ^5_base^P_{F7}|T;    // Female: position at session start
    node scan_width: ^1^C_{F2}|A;         // Mind: how wide is my scan
    node cadence:    ^7^O_{F4}|E;         // Rhythm: am I locked to something
    node carrier:    ^4^O_{F4}|E;         // Vibration: is one source dominant
    node passed_log: ^6^C_{F6}|A;         // Male: what I actually decomposed
    node drift:      ^5_now^P_{F7}|T;     // Female: where my position sits now
    node alert:      ^9^C_{F2}|A;         // Below/Effect: what the difference surfaces

    filter base_ref: LowPass< in=ambient, out=baseline, tau=1440.0 >;  // 24 h, min
    diff factor_count: Differential< plus=[scan_width, cadence, carrier, passed_log],
                                     minus=baseline >;
    diff unaccounted:  Differential< plus=drift, minus=passed_log >;
    integ accum: Integrator< in=unaccounted, window=2880.0 >;   // 48 h, minutes

    cjt  trip: CJT< unaccounted | substrate => alert > [β=2.0, sat=0.85];
    fuse hold: Fuse< alert, threshold=0.9, action=defer_decision >;

    probe tp1: factor_count;  probe tp2: unaccounted;
    probe tp3: accum;         probe tp4: alert;
}
```

---

### D.11 CCB-ADV — Advertising Reference

**Status: ANALYTICAL REFERENCE — NO NON-CONSENSUAL TARGETING.** Retained for campaign analysis and attribution, subject to the chapter's consent boundary.

Canonical source: `ch18_ccb_adv_advertising.md`.

```cas
board ccb_adv {
    input:  creative;                     // the advertisement as delivered
    output: transaction;                  // the Operational-domain sale

    node segment:  ^5^P_{F4}|f;           // who the segment takes itself to be
    node endorser: ^5^P_{F7}|T;           // the endorser's public formation
    node product:  ^0^C_{F2}|A;           // the product as presented
    node ideal:    ^0^C_{F2}|A;           // the adjacent ideal image
    node cue:      ^8^C_{F4}|A;           // the installed trigger
    node surfaced: ^9^C_{F4}|f;           // what the cue brings to Mind
    node gap:      ^3^E_{F3}|f;           // visceral recoil, not analytic
    node pull:     ^2^E_{F4}|f;           // attraction to the branded object
    node intent:   ^9^E_{F5}|f;           // the felt urge to buy
    node sale:     ^9^O_{F5}|E;           // the transaction
    node refusal:  ^3^P_{F7}|T;           // principled refusal (CSB)

    capacitor c_seg: Capacitor< segment, C=9.50, leakage=0.04 >;   // per week
    osc  media:   Oscillator< signal=creative, f=3.0, sustain=12.0 >;
    xfmr endorse: Transformer< primary=endorser, secondary=product, n=0.35 >;

    cjt assoc:   CJT< product  | segment => cue >      [beta=2.0, sat=0.85];
    cjt flip:    CJT< cue      | segment => surfaced > [beta=1.2, sat=0.85];
    cjt inject:  CJT< ideal    | segment => gap >      [beta=2.5, sat=0.85]; // detection-only
    cjt resolve: CJT< gap      | segment => intent >   [beta=2.0, sat=0.85]; // detection-only
    cjt affirm:  CJT< surfaced | segment => pull >     [beta=2.0, sat=0.85];
    cjt want:    CJT< pull     | segment => intent >   [beta=1.2, sat=0.85];

    diode d3:         Diode< ^E -> ^O >               [Vf=2.0];
    resistor r_price: Resistor< path=intent, R=4.0 >;              // price + friction
    cjt close:        CJT< intent | segment => sale > [beta=1.0, cutoff=0.20];

    cjt  csb:      CJT< creative | segment => refusal > [beta=2.0, sat=0.85];
    fuse csb_fuse: Fuse< refusal, threshold=0.90, action=permanent_block >;

    probe tp1: c_seg;   probe tp2: cue;   probe tp3: intent;   probe tp4: sale;
}
```

---

### D.12 CCB-ADV-DET — Advertising Detector

**Status: DEFENSIVE DETECTOR.** Separates injected desire from a slower identity store.

Canonical source: `ch18_ccb_adv_advertising.md`.

```cas
board ccb_adv_det {
    input:  observed_want;
    output: verified_want;

    node want_raw: ^2^E_{F4}|f;          // the want as it arrives
    node origin:   ^6^C_{F2}|A;          // Male: decompose it into its sources
    node cadence:  ^7^O_{F6}|E;          // the exposure schedule, counted
    node polarity: ^8^C_{F4}|A;          // which end triggers which
    node verified: ^2^E_{F4}|⟨A,f,T⟩;    // co-present across registers

    counter det1: Integrator< in=cadence, window=4.0 >;         // weeks
    probe   det2: Polarity< node=polarity >;
    filter  det3: LowPass< in=want_raw, out=persistent, tau=4.0 >;
    xfmr    det4: Transformer< primary=want_raw, secondary=origin, n=0.0 >;
    delay   det5: Hold< path=want_raw, duration=2.0 >;          // 1 tau_inject
    probe   det6: RegisterSet< node=verified >;

    cjt   judge:  CJT< persistent | origin => verified > [beta=1.0, sat=0.85];
    diode d_desc: Diode< ^C -> ^E >                      [Vf=1.2];

    probe tp1: det1;   probe tp2: det2;   probe tp3: det3;   probe tp4: det5;
}
```

---

### D.13 CCB-PW — Psychological-Warfare Detection Reference

**Status: DETECTION-ONLY — DO NOT BUILD AS AN ATTACK BOARD.** A recognizable Path-D signature, not an operational authorization.

Canonical source: `ch19_ccb_pw_psychological_warfare.md`.

```cas
board ccb_pw_detection_reference {
    input:  command;
    output: observed_effect;

    node objective: ^0^P_{F7}|T;       // Idea: the stated aim
    node split:     ^6^C_{F6}|A;       // Male: the aim taken apart into two payloads
    cjt  intake:    CJT< command | objective => split > [β=1.0, region=active];

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];    // descent only —
    diode d_ce: Diode< ^C -> ^E > [Vf=1.2];    // nothing on this board
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];    // may ascend

    // ---- PATH F — FORTIFY (own force) ----
    node own_substrate: ^5^P_{F1}|T;   // Female: own accumulated formation
    node own_affinity:  ^2^E_{F4}|f;   // Positive: felt affiliation
    cjt  fortify: CJT< split | own_substrate => own_affinity > [β=2.0, sat=0.80];
    osc  f_clock: Oscillator< signal=own_affinity, source=command,
                              period=168.0, duty=0.15, sustain=campaign >;

    // ---- PATH D — DEMORALISE (target) ----
    node tgt_substrate: ^5^P_{F1}|T;   // Female: the target's formation
    node recoil_1: ^3^E_{F3}|f;        // Negative: visceral aversion
    node recoil_2: ^3^E_{F3}|f;
    node recoil_3: ^3^E_{F3}|f;
    cjt  a1: CJT< split    | tgt_substrate => recoil_1 > [β=1.5];
    cjt  a2: CJT< recoil_1 | tgt_substrate => recoil_2 > [β=1.5];
    cjt  a3: CJT< recoil_2 | tgt_substrate => recoil_3 > [β=1.6, sat=0.90];
    osc  d_clock: Oscillator< signal=recoil_3, source=command,
                              period=168.0, duty=0.15, sustain=campaign >;
    // co-presence: recoil_1 + recoil_2 + recoil_3 — never (r1 × r2 × r3)

    // ---- CROSS-FEED: the coupling, and the leak ----
    filter xfeed: LowPass< in=recoil_3, out=morale_evidence, tau=168.0 >;
    feedback morale_evidence -> own_substrate [β=0.30];

    // ---- INVERSION STAGE ----
    node fault_line: ^6^C_{F6}|A;      // Male: the target's existing divisions
    node suspicion:  ^3^E_{F4}|f;      // Negative: recoil aimed at their own side
    cjt  inv: CJT< fault_line | tgt_substrate => suspicion > [β=2.5];

    // ---- DENIABILITY: impedance match, no gain ----
    xfmr deny: Transformer< primary=^9^P_{F7}|T, secondary=^9^E_{F4}|f, n=1.0 >;

    // ---- CSB: the operator's own limit (Ch 24) ----
    node limit_decision: ^3^P_{F7}|⟨A,f,T⟩;    // three co-present guardrails
    cjt  csb: CJT< split | own_substrate => limit_decision > [β=2.0, sat=0.85];
    fuse csb_fuse: Fuse< path=limit_decision, threshold=0.90,
                         action=permanent_block >;

    probe tp1: split;            // the shared upstream — coupling
    probe tp2: recoil_3;         // chain gain and saturation
    probe tp3: fault_line;       // is decomposition available at all
    probe tp4: limit_decision;   // CSB status
}
```

---

### D.14 CCB-HM — Hearts-and-Minds Counter-Circuit

**Status: DEFENSIVE COUNTER-CIRCUIT.** Restores plurality and independent composition; it does not substitute a new monoculture.

Canonical source: `ch19_ccb_pw_psychological_warfare.md`.

```cas
board ccb_hm_hearts_and_minds {
    input:  incoming;
    output: composed;                  // the board's only output is internal

    node substrate: ^5^P_{F1}|T;       // plural, not one capacitor
    cap  c5: Capacitor< node=substrate, C=2.0, n_parallel=5,
                        leakage=0.02 >;            // per week

    node decompose: ^6^C_{F6}|A;       // Male: public decomposition of the payload
    node confirm:   ^4^C_{F2}|A;       // Vibration: a checkable return
    node composed:  ^5^C_{F6}|A;       // Female: formation that has been checked
    node own_clock: ^7^O_{F6}|E;       // Rhythm: locally sourced cadence
    node limit:     ^3^P_{F7}|⟨A,f,T⟩; // Negative: inward refusal, three registers

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];
    diode d_ce: Diode< ^C -> ^E > [Vf=1.6];   // raised from the stock 1.2
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    cjt hm1: CJT< incoming  | substrate => decompose > [β=2.0, region=active];
    cjt hm2: CJT< decompose | substrate => confirm   > [β=1.0];

    integrate hm3: ( decompose × confirm ) = composed;   // the one lawful ×

    osc      local: Oscillator< signal=own_clock, source=internal,
                                period=168.0, duty=0.20 >;
    filter   fb:    LowPass< in=confirm, out=trend, tau=504.0 >;   // 3 weeks
    feedback trend -> substrate [β=0.05];

    cjt  csb:     CJT< incoming | substrate => limit > [β=2.0, sat=0.85];
    fuse hm_fuse: Fuse< path=limit, threshold=0.90, action=permanent_block >;

    probe tp1: own_clock;   // cadence source
    probe tp2: hm1;         // decomposition gain
    probe tp3: composed;    // fraction surviving decomposition
    probe tp4: limit;       // CSB status
}
```

---

### D.15 CCB-SELF — Self-Programming

**Status: BUILDABLE CLOSED LOOP.** The operator is the target; the guard, slew fuse, and reference store are mandatory.

Canonical source: `ch20_ccb_self_programming.md`.

```cas
board ccb_self {                        // CCB-SELF — closed loop; operator is target
    input:  intent;                     // the ^0 asserted this cycle
    output: enacted;                    // the ^9 the cycle produces
    // OSC1 generates the ^8 cue on-board — SI5: no external terminal. Time base: days.

    // ---- S0  REFERENCE: the slow ^5. Bias source, never an output. ----
    node ref_composition: ^5^P_{F7}|T;              // Female: composition built toward
    capacitor c1: Capacitor< node=ref_composition, tau=85.0,
                             leak_tau=180.0, V_BR=8.0 >;

    // ---- S1  INTAKE: the asserted ^0, amplitude-limited ----
    node intent: ^0^C_{F7}|A;                       // Idea: today's assertion
    resistor r1:   Resistor< path=intent, R=30.0 >;
    limiter  lim1: Limiter< path=intent, max=1.3 >; // 0.5 x V_BR at d_evidence = 2.6

    // ---- S2  NOTCH: the ^6 audit off the rail, not silenced ----
    node audit: ^6^C_{F6}|A;                        // Male: decomposition and test
    notch n1: Notch< in=audit, f0=0.35, Q=4.0 >;    // events/min — in-session only

    // ---- S3  MAIN CJT: biased from the reference, not from the output ----
    node work_composition: ^5^C_{F5}|⟨A,E⟩;         // Female: as currently performing
    capacitor c2: Capacitor< node=work_composition, tau=22.0,
                             leak_tau=30.0, V_BR=8.0 >;
    cjt q1: CJT< intent | ref_composition => work_composition >
            [β=1.5, sat=0.60, rπ=8.0, region=active];

    // ---- S4  OSCILLATOR + HYSTERETIC GATE ----
    node cadence: ^7^C_{F6}|A;                      // Rhythm: the entraining cadence
    node cue:     ^8^O_{F6}|E;                      // Above/Cause: time and place fire it
    schmitt g1: Schmitt< sense=work_composition, on_below=8.0, off_above=9.0 >;
    osc  osc1:  Oscillator< signal=cue, source=cadence, period=1.0,
                            duty=0.04, sustain=254.0, gate=g1 >;

    // ---- S5  ENACTMENT: the only node that is not self-report ----
    node enacted:    ^9^O_{F5}|E;                   // Below/Effect: the behaviour performed
    node impression: ^4^E_{F3}|f;                   // Vibration: what the cycle left behind
    cjt    q3: CJT< cue | work_composition => enacted > [β=1.0, region=active];
    sample s2: Sample< node=impression, period=1.0, window=1440.0 >;  // days, minutes

    // ---- S6  EVIDENCE FEEDBACK: the one lawful O -> P ascent (Ch. 8.4) ----
    filter lp1: LowPass< in=enacted, out=evidence_trend, tau=21.0 >;
    fuse   f1:  Fuse< ref_composition, threshold=0.12, action=open_feedback >;
    feedback evidence_trend -> ref_composition [β=0.05];   // arrives at the BIAS terminal

    // ---- S7  CSB STAGE: the self-compassion gate. Mandatory. ----
    node miss_trigger: ^8^C_{F5}|f;                 // Above/Cause: a miss, and what it recalls
    node compassion:   ^3^P_{F7}|⟨A,f,T⟩;           // Negative: recoil from self-condemnation
    node acceptance:   ^2^E_{F4}|f;                 // Positive: affinity for the self that missed
    cjt q2: CJT< miss_trigger | compassion => acceptance > [β=1.5, sat=0.70];

    // ---- S8  INSTRUMENT: the ^6 audit, sampled and bounded ----
    sample s1: Sample< node=audit, period=7.0, window=10.0 >;         // days, minutes

    // ---- TEST POINTS ----
    probe tp1: work_composition;    // P_cap against 10*(1 - e^(-t/22))
    probe tp2: enacted;             // cycles completed / cycles scheduled
    probe tp3: lim1;                // V_sugg against 0.5 x V_BR
    probe tp4: ref_composition;     // reference slew, points per day
}
```

---

### D.16 CCB-CSB — Cognitive Safety Board

**Status: MANDATORY SAFETY BOARD.** Energize and proof-load before any working board.

Canonical source: `ch24_csb_safety_board.md`.

```cas
board ccb_csb {                          // the operator's own safety board
    input:  proposal;                    // the operation being considered
    output: verdict;                     // PROCEED, or a cut path

    // ---- S0  CHARTER: the slow ^5. Bias source, never a fast-path output. ----
    node charter: ^5^P_{F7}|T;                        // Female: principled formation
    capacitor c1: Capacitor< node=charter, tau=85.0,
                             leak_tau=180.0, e_break=1.0 >;      // tau in days

    // ---- S1  INTAKE: the declared dial divider ----
    node proposal: ^0^C_{F2}|A;                       // Idea: the operation proposed
    dial     dial_pos: ^2 [dial=5];
    dial     dial_neg: ^3 [dial=7];                   // divergence 2 — inside the limit
    resistor r1: Resistor< path=proposal, R=70.0 >;   // k = 5/12 = 0.417

    // ---- S2  PRE-AMP: surface every reading before anything judges one ----
    node expanded: ^8^C_{F2}|A;                       // Above/Cause: readings it triggers
    cjt  q1: CJT< proposal | charter => expanded > [β=3.0, sat=0.80, region=active];

    // ---- S3  DIFFERENTIAL PAIR: matched, shared bias ----
    node attraction: ^2^P_{F7}|T;                     // Positive: drawn toward running it
    node aversion:   ^3^P_{F7}|T;                     // Negative: repelled by running it
    cjt  q2: CJT< expanded | charter => attraction > [β=2.0, sat=0.90];
    cjt  q3: CJT< expanded | charter => aversion   > [β=2.0, sat=0.90];
    diff dif1: Differential< plus=aversion, minus=attraction >;   // risk

    // ---- S4  CASCADE: name them, then weigh them honestly ----
    node named:    ^1^C_{F2}|A;                       // Mind: risks named and sorted
    node assessed: ^6^E_{F6}|A;                       // Male: decomposed and weighed
    diode d1: Diode< ^P -> ^C > [Vf=0.7, I_R=0.02, V_BR=12.0];
    diode d2: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];
    cjt   q5: CJT< risk  | charter => named    > [β=1.5, sat=0.80];
    cjt   q6: CJT< named | charter => assessed > [β=1.0, sat=0.80];   // unity — honesty

    // ---- S5  GUARD: Chapter 3.5's safety-guard datasheet row, instantiated ----
    node guard: ^3^P_{F7}|⟨A,f,T⟩;                    // three co-present guardrails
    cjt  q4: CJT< assessed | charter => guard >
             [β=3.0, g_m=0.3, rπ=10.0, sat=0.85, cutoff=0.08, region=active];

    // ---- S6  ENFORCEMENT: latch the path, not just the decision ----
    node blocked: ^9^P_{F7}|T;                        // Below/Effect: the block produced
    cjt  q7: CJT< guard | charter => blocked > [β=10.0, sat=0.98, cutoff=0.80];
    fuse f1: Fuse< blocked, threshold=0.90, action=permanent_block >;

    // ---- S7  EXIT: descent only ----
    node ops_log: ^9^O_{F5}|E;                        // Below/Effect: what was actually done
    diode d3: Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];

    // ---- S8  FEEDBACK AND INSTRUMENTS ----
    filter lp1: LowPass< in=ops_log, out=drift, tau=21.0 >;
    fuse   f2:  Fuse< charter, threshold=0.12, action=open_feedback >;
    feedback drift -> charter [β=0.05];

    node audit: ^6^C_{F6}|A;                          // Male: the weekly decomposition
    sample s1: Sample< node=audit, period=7.0, window=15.0 >;   // days, minutes
    monitor m1: Monitor< pair=[^2,^3], limit=4 >;
    monitor m2: Monitor< pair=[^5,^6], limit=4 >;
    monitor m3: Monitor< pair=[^8,^9], limit=4 >;
    on m1 { alert "involution divergence — attraction against aversion"; }
    on m2 { alert "involution divergence — composition against decomposition"; }
    on m3 { alert "involution divergence — trigger against effect"; }

    // ---- TEST POINTS ----
    probe tp1: guard;      // refusal activation against cutoff and sat
    probe tp2: blocked;    // enforcement activation and F1 continuity
    probe tp3: charter;    // slew, points per day, and trend against the dated baseline
    probe tp4: dif1;       // differential balance — the over-trust direction
}
```

---

### D.17 Regeneration and acceptance

The appendix is current only when the generator produces no diff. For a release build:

1. regenerate this appendix;
2. run the CAS domain checker;
3. compare the board-name inventory here with the chapter inventory;
4. confirm every detection-only block retains its warning; and
5. proof-load buildable guards and fuses before energizing signal paths.
