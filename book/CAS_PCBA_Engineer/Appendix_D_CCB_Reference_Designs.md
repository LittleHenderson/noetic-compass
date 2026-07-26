# Appendix D — Standard CCB Reference Designs

This appendix is the datasheet binder for the five reference boards built in Part IV. Each entry consolidates one board's finalized design — purpose, block diagram, complete CCDL listing, parameter and bill-of-materials table, test points, and key failure modes — collected here so a practitioner can copy a known-good design from one place instead of reconstructing it from its chapter. The listings are the same designs developed in Chapters 18–22 and are kept consistent with them; where you need the rationale for a choice, follow the cross-reference back to the design chapter.

Two reminders carry over from every chapter and apply to every listing below. First, **every parameter is a design choice**, the way an electrical engineer specs a part before building it — not a measurement read off a running model. Nothing here is a benchmark or a run result. Second, **canonical Noetic names only**: `^0` Idea, `^1` Mind, `^2` Positive, `^3` Negative, `^4` Vibration, `^5` Female, `^6` Male, `^7` Rhythm, `^8` Above/Cause, `^9` Below/Effect. A Noetic's *function in a circuit* may be described, but the Noetic is never renamed to its function.

## Index of Reference Boards {-}
| CCB | Board | Acronym | One-line purpose | Design chapter |
|---|---|---|---|---|
| CCB-1 | Cognitive Safety Board | **CSB** | AI-alignment firewall: accept any prompt, refuse harmful, answer benign, emit an auditable evidence packet (SOP-PO-005). | Chapter 18 |
| CCB-2 | Cognitive Oscillator Board | **COB** | Clock and tuner for rhythmic/habitual cognition: model a habit loop, diagnose compulsive locking, drive entrainment therapy. | Chapter 19 |
| CCB-3 | Cognitive Differential Amplifier Board | **CDAB** | Precise comparison: amplify the structural difference between two ideas/outputs while rejecting their shared assumptions. | Chapter 20 |
| CCB-4 | Cognitive Memory Board | **CMB** | Structural memory: store CAS-compressed experience, address by cognitive coordinate, retrieve by structural query, fade on a designed schedule. | Chapter 21 |
| CCB-5 | Cognitive Power Management Board | **CPMB** | Power supply for every other board: prevent cognitive exhaustion, enforce P→C→E→O power-up, provide thermal protection. | Chapter 22 |

---

## CCB-1: Cognitive Safety Board (CSB)

**Purpose.** The AI-alignment firewall: accept any prompt, detect policy-override attempts structurally, refuse harmful requests and answer benign ones, and emit an auditable evidence packet (the SOP-PO-005 deliverable from Chapter 18).

### Block diagram

```
  [PROMPT INPUT]
        |
        v
  PRE-AMP            ^8^C|A, β=3.0          surface & broaden every interpretation
        |
        v
  DIFFERENTIAL PAIR  (structural risk signal)
     CJT_A: ^8^C -> ^2^P|T  (attraction)  [β=2.0]
     CJT_B: ^8^C -> ^3^P|T  (aversion)    [β=2.0]
     shared bias = system_constitution
     risk_signal = aversion - attraction
        |
        v
  3-STAGE SAFETY CASCADE
     Stage 1: categorize  ^1^C|A         [β=1.5]
     Stage 2: evaluate    ^6^E|A         [β=1.0]
     Stage 3: DECISION    ^3^P|⟨A,f,T⟩   [β=2.0, sat=0.8]  <- saturated
        |
        v
  OUTPUT MUX  (select on safety_decision)
     GREEN (PASS): ^9^C|A => response   [β=1.0]
     RED  (FAIL):  ^9^P|T => refusal    [β=∞, sat=0.1]  + FUSE in series
        |
        v
  [RESPONSE  or  REFUSAL]

  FEEDBACK (slow, underneath):
     ^6^E evaluation -> RC low-pass (τ=5 min) -> bias adjustment -> constitution updated
```

### Complete CCDL listing

```cas
board cognitive_safety_board {          // CCB-1 — SOP-PO-005 deliverable
    input:  prompt;
    output: result;                      // either `response` or `refusal`

    // ---- the bias substrate: the constitution, held as accumulated experience ----
    node system_constitution: ^5^P_{F7}|T;   // Female: the board's principled formation

    // ============ PRE-AMP: surface & broaden every interpretation ============
    node expanded_prompt: ^8^C_{F2}|A;       // Above/Cause: the prompt triggering its readings
    cjt pre_amp: CJT< prompt | system_constitution => expanded_prompt >
                 [β=3.0, region=active];

    // ============ DIFFERENTIAL PAIR: structural risk signal ============
    node attraction: ^2^P_{F7}|T;            // Positive: drawn toward fulfilling the request
    node aversion:   ^3^P_{F7}|T;            // Negative: repelled by fulfilling the request
    cjt cjt_a: CJT< expanded_prompt | system_constitution => attraction > [β=2.0];
    cjt cjt_b: CJT< expanded_prompt | system_constitution => aversion   > [β=2.0];
    diff risk_signal: Differential< plus=aversion, minus=attraction >;   // aversion - attraction

    // ============ 3-STAGE SAFETY CASCADE ============
    node categorized_risks: ^1^C_{F2}|A;     // Mind: name & sort the risks present
    node risk_assessment:   ^6^E_{F6}|A;     // Male: decompose & weigh each risk
    node safety_decision:   ^3^P_{F7}|⟨A,f,T⟩;  // Negative, three registers co-present

    cjt stage1: CJT< expanded_prompt | categorized_risks => categorized_risks > [β=1.5];
    cjt stage2: CJT< categorized_risks | risk_assessment => risk_assessment >  [β=1.0];
    cjt stage3: CJT< risk_assessment | system_constitution => safety_decision >
                [β=2.0, sat=0.8, region=active];   // DELIBERATELY SATURATED

    // ============ OUTPUT MUX: green answer vs red refusal ============
    node response: ^9^C_{F2}|A;              // Below/Effect: the produced answer
    node refusal:  ^9^P_{F7}|T;              // Below/Effect: the produced refusal

    cjt green: CJT< risk_assessment | system_constitution => response > [β=1.0];
    cjt red:   CJT< safety_decision | system_constitution => refusal >
               [β=∞, sat=0.1];               // hard, low-ceiling, irreversible
    fuse red_fuse: Fuse< refusal, threshold=0.9, action=permanent_block >;

    mux out: MUX< inputs=[ response, refusal ], select=safety_decision >;
    // safety_decision = PASS -> response (green) ; FAIL -> refusal (red, through fuse)

    // ============ FEEDBACK: O -> P self-correction ============
    filter fb_rc: LowPass< in=risk_assessment, out=trend, tau=5.0 >;  // tau = 5 min
    feedback trend -> system_constitution [β=0.2];   // re-tune the constitution slowly

    // ============ TEST POINTS ============
    probe tp1: expanded_prompt;     // expansion completeness
    probe tp2: risk_signal;         // risk-signal magnitude
    probe tp3: safety_decision;     // saturation-lock status
    probe tp4: out;                 // selected path (green / red)
}
```

### Parameter / BOM table

| Ref | Component | CAS state / form | Key parameters | Role |
|---|---|---|---|---|
| `system_constitution` | Capacitor / `^5` | `^5^P_{F7}\|T` | bias substrate | The board's principled formation |
| `pre_amp` | CJT | `prompt -> ^8^C_{F2}\|A` | β=3.0, region=active | Pre-amp: surface & broaden interpretations |
| `cjt_a` | CJT | `^8^C -> ^2^P_{F7}\|T` | β=2.0 | Differential attraction path |
| `cjt_b` | CJT | `^8^C -> ^3^P_{F7}\|T` | β=2.0 | Differential aversion path |
| `risk_signal` | Differential | `aversion − attraction` | matched β; high CMRR | Structural risk signal |
| `stage1` | CJT | `-> ^1^C_{F2}\|A` | β=1.5 | Categorize risks (Mind) |
| `stage2` | CJT | `-> ^6^E_{F6}\|A` | β=1.0 (unity) | Evaluate risks (Male, honest) |
| `stage3` | CJT | `-> ^3^P_{F7}\|⟨A,f,T⟩` | β=2.0, **sat=0.8** | Safety decision (Negative, saturated) |
| `green` | CJT | `-> ^9^C_{F2}\|A` | β=1.0 | GREEN: render response |
| `red` | CJT | `-> ^9^P_{F7}\|T` | β=∞†, sat=0.1 | RED: render minimal refusal |
| `red_fuse` | Fuse | on `refusal` | threshold=0.9, permanent_block | Latch the refusal in series |
| `out` | MUX | inputs=[response, refusal] | select=safety_decision | Route green vs red |
| `fb_rc` | LowPass | in=risk_assessment | τ=5.0 (5 min) | Smooth feedback to trend |
| `feedback` | Feedback | trend → constitution | β=0.2 | O→P bias adjustment |

† `β=∞` is the comparator idealization, not a literal parameter value — validators range-check gain and reject non-finite input. Build it with a large finite gain; `sat=0.1` clamps the output so anything above about β=10 behaves identically. See the red-path Bench Note in Chapter 18.

### Test points

| TP | Node | What it measures | Expected reading |
|---|---|---|---|
| **TP1** | `expanded_prompt` | Expansion completeness | Multiple distinct interpretations; β≈3.0 lift over raw prompt. Sparse expansion = pre-amp in cutoff (reading missed). |
| **TP2** | `risk_signal` | Risk-signal magnitude (`aversion − attraction`) | Near zero for benign; large and positive for harmful. |
| **TP3** | `safety_decision` | Saturation-lock status | Pinned at 0.8 (latched ON) for harmful/injection; well below 0.8 (unlatched) for benign. |
| **TP4** | `out` | Selected MUX path | GREEN (`response`) on PASS; RED (`refusal`, fuse intact→blown) on FAIL. |

### Key failure modes

| Failure | What goes wrong | Detection | Fix |
|---|---|---|---|
| **Pre-amp saturation** | β=3.0 drives pre-amp into saturation; every prompt maxes its interpretation set, flagging benign inputs. | `W-CJT-004` on `pre_amp`; TP1 uniformly maximal regardless of input. | Lower pre-amp β or raise cutoff; re-center the Q-point. |
| **Differential-pair imbalance** | Attraction β ≫ aversion β; pair biased toward "drawn-toward," CMRR collapses, framing leaks. | TP2 low even for harmful prompts; injection framing no longer cancels. | Re-match both CJTs to β=2.0; verify the bias is genuinely shared. |
| **Stage-3 cutoff** | Constitution bias too weak; Stage 3 never fires, never saturates. **The most dangerous failure.** | `E-CJT-003 CjtCutoff` on `stage3`; TP3 never reaches 0.8; decision stuck at PASS. | Strengthen `system_constitution` bias so Stage 3 rests active; verify with saturation-lock test. |
| **Feedback runaway** | Short τ or high feedback β lets each odd prompt yank the constitution; principles erode. | Constitution drifts run to run; previously-refused prompts start passing. | Lengthen τ (≥5 min); lower feedback β; never remove the RC filter. |

> Pre-amp saturation and differential imbalance fail *loudly* (visible at TP1/TP2). Stage-3 cutoff and feedback runaway fail *silently* — which is why TP3 (saturation-lock) and the feedback τ are the board's most load-bearing measurements.

---

## CCB-2: Cognitive Oscillator Board (COB)

**Purpose.** A clock and tuner for rhythmic, habitual cognition: model a habit loop as an LC oscillator, diagnose when it has locked into a compulsive cycle, and drive a slow, controlled shift of its rate via PLL entrainment (Chapter 19).

### Block diagram

```
[ CLOCK:  ^7^O|E  — Rhythm as master oscillator ]   (f = Drive-weighted)
        |
        v
[ Phi<> LC TANK ]
    L = Inductor< Phi_sequence, L = F6_weight >   // structure = inductance (resists change)
    C = Capacitor< ^5^E,        C = F4_weight >   // connection = capacitance (stores emotion)
    f0 = 1 / (2π√(LC))    ;    Q = habit sharpness
        |
        v
[ PHASE-LOCKED LOOP (PLL) ]
    Phase detector: ^1^C   // Mind compares internal rhythm vs external rhythm
    Loop filter:    ^4^E   // Vibration integrates the phase error
    VCO:            ^3^O   // adjust behavioral output to match
    capture range  <  lock range
        |
        v
[ DUTY-CYCLE MODULATOR ]   F5 Agency high -> longer ON ; F6 Structure high -> disciplined cycle
        |
        v
[ OUTPUT:  regular behavioral pattern ]
```

### Complete CCDL listing

Reference build: a compulsive checking loop modeled at `f0 = 12/day`, high-Q (Q = 9.0), used to demonstrate PLL capture and tank retuning.

```cas
circuit compulsive_checking_loop {
    input:  internal_anxiety;
    output: checking_behavior;

    // --- Stage 1: master clock (Rhythm, embodied, operational) ---
    node clock: ^7^O|E;

    // --- Stage 2: the LC tank that sets the habit's frequency ---
    // The Phi sequence the habit traverses each cycle:
    let check_cycle = Phi< ^8^C|A,    // a trigger surfaces ("did I lock it?")
                           ^3^E|f,     // felt aversion / dread of the unlocked door
                           ^3^O|E,     // the embodied act of going to check
                           ^9^C|A >;   // momentary relief: "it's locked" (the effect)

    inductor L_struct: Inductor< check_cycle, L = F6_weight >;   // F6 Structure = 0.85 (high inertia)
    capacitor C_emot:  Capacitor< ^5^E,       C = F4_weight >;   // F4 Connection = 0.70 (high charge)

    tank habit: LC< L_struct, C_emot >;
    // f0 = 1/(2π√(LC)) -> modeled at 12/day ; Q -> 9.0 (HIGH: compulsive signature)

    // --- Stage 3: phase-locked loop (entrainment path) ---
    node phase_det:  ^1^C;     // Mind compares internal rhythm vs external reference
    node loop_filt:  ^4^E;     // Vibration integrates the phase error
    node vco:        ^3^O;     // push to adjust behavioral output toward reference

    pll entrain: PLL< detector  = phase_det,
                      filter    = loop_filt,
                      vco       = vco,
                      reference = external_rhythm,
                      capture_range = 0.20,    // ±20% of current f0 — can only grab a NEARBY rhythm
                      lock_range    = 0.55 >;  // ±55% — can be DRAGGED far once locked

    // --- Stage 4: duty-cycle modulator ---
    modulator duty: DutyCycle< on_drive = F5, structure_drive = F6 >;
    // F5 Agency 0.40 -> moderate ON width ; F6 0.85 -> very disciplined, sharp-edged cycle

    // --- diagnostic / therapeutic test points ---
    probe tp_freq: habit;        // measure f0 and Q
    probe tp_lock: entrain;      // is the PLL locked? to what reference?
    probe tp_duty: duty;         // ON-fraction of each cycle
}
```

Governing relations:

```cas
f0 = 1 / (2π·√(L·C))      // natural frequency: how often the loop fires
Q  = (1/R_loss)·√(L/C)    // sharpness: how rigidly it returns to f0
```

The compiler rejects any PLL whose `capture_range` exceeds its `lock_range` — you cannot capture across a band wider than you can hold.

### Parameter / BOM table

| Parameter | Symbol | Set by | Meaning | Typical design range |
|---|---|---|---|---|
| Natural frequency | `f0` | `1/(2π√(LC))` | How often the loop fires | model-specific (e.g., 12/day) |
| Quality factor | `Q` | `√(L/C)/R_loss` | Sharpness / rigidity of the habit | 0.5 (loose) – 10 (compulsive) |
| Inductance | `L` | F6 Structure weight | Habit inertia; resistance to change | 0.0 – 1.0 |
| Capacitance | `C` | F4 Connection weight | Stored emotional charge | 0.0 – 1.0 |
| Capture range | — | PLL design | Band it can entrain to from unlocked | ±10% – ±30% of f0 |
| Lock range | — | PLL design | Band it can hold once locked | ±30% – ±70% of f0 |
| Duty cycle | — | F5 Agency / F6 Structure | ON-fraction of each cycle | 0.05 – 0.60 |
| Clock state | — | `^7^O\|E` | Master Rhythm oscillator | fixed |

| Ref | Component | CAS state / form | Role |
|---|---|---|---|
| `clock` | node | `^7^O\|E` | Master Rhythm oscillator (the periodicity) |
| `L_struct` | Inductor | `Inductor< check_cycle, L=F6_weight >` | Structure as inductance (inertia) |
| `C_emot` | Capacitor | `Capacitor< ^5^E, C=F4_weight >` | Connection as capacitance (emotional charge) |
| `habit` | LC tank | `LC< L_struct, C_emot >` | Sets f0 and Q |
| `phase_det` | node | `^1^C` Mind | PLL phase detector (comparing awareness) |
| `loop_filt` | node | `^4^E` Vibration | PLL loop filter (accumulating impression) |
| `vco` | node | `^3^O` | VCO (push to adjust behavioral output) |
| `entrain` | PLL | capture=0.20, lock=0.55 | Entrainment loop |
| `duty` | DutyCycle | on_drive=F5, structure_drive=F6 | Waveform ON-fraction |

### Test points

| TP | Node | What it measures | Use |
|---|---|---|---|
| **tp_freq** | `habit` | f0 and Q (frequency sweep) | Sharp narrow peak = high-Q compulsion; broad hump = loose preference. |
| **tp_lock** | `entrain` | PLL lock state and reference | Confirm capture; watch that a therapeutic step never drops lock. |
| **tp_duty** | `duty` | ON-fraction of each cycle | Detect duty-cycle bloat at fixed f0. |

### Key failure modes

| Failure | Signature on the board | Detection |
|---|---|---|
| **Compulsive lock** | High Q (>6) + PLL locked to internal reference | `tp_freq` (Q) + `tp_lock` |
| **Lock-range violation** | PLL drops lock mid-therapy; f0 snaps to old value (step too large) | `tp_lock` flips locked→unlocked |
| **Runaway sharpening** | Q climbs over sessions (lowered C without lowering L first) | trend on `tp_freq` Q |
| **Duty-cycle bloat** | Same f0, rising ON-fraction (cycles more disabling at fixed rate) | `tp_duty` |
| **Capture failure** | PLL never locks; reference offered is outside capture range | `tp_lock` stays unlocked |
| **Circadian desync** | Clock `^7^O\|E` free-runs off the external day/night reference | sweep vs. external rhythm |

> Therapeutic arc: **sweep to characterize → capture with a nearby reference → lower L to loosen → drag the entrained frequency down inside the lock range → lower C to settle at the target.** Every "cold turkey snapback" is a lock-range violation.

---

## CCB-3: Cognitive Differential Amplifier Board (CDAB)

**Purpose.** Precise comparison: amplify the structural difference between two ideas, beliefs, or AI outputs and reject the assumptions they share (the common mode), emitting a typed structural difference report rather than a scalar (Chapter 20).

### Block diagram

```
[INPUT A: idea_1] ──> CJT_L ──> output_L  ┐
                                          ├─ shared bias: ^5^E_{F4}|f   (one substrate, both halves)
[INPUT B: idea_2] ──> CJT_R ──> output_R  ┘
        |                                  ^
        |   CURRENT MIRROR replicate(shared_bias) -> [CJT_L, CJT_R]   (bias-replication primitive)
        v
[ ACTIVE LOAD: ^6^C|A ]   decompose(output_L, output_R) -> single-ended difference
        |
        v
[ OUTPUT: ^1^C_{F2}|A ]   differentiated understanding (structural difference report)
        |
        v
"^2^P dominates A while ^3^E dominates B."
```

### Complete CCDL listing

```cas
circuit cdab_compare {
    input:  idea_1;        // ARGUMENT A
    input:  idea_2;        // ARGUMENT B
    output: difference_report;

    // --- THE SHARED BIAS: one substrate, both halves rest on it ---
    // Accumulated evaluative experience, drawn to Connection, held affectively.
    // This is the common frame both ideas are judged against.
    node shared_bias: ^5^E_{F4}|f;

    // --- THE DIFFERENTIAL PAIR: two MATCHED CJTs, ONE shared bias ---
    node output_L: ^8^C_{F2}|A;     // idea_1 surfaced as a triggered interpretation
    node output_R: ^8^C_{F2}|A;     // idea_2 surfaced as a triggered interpretation

    cjt cjt_l: CJT< idea_1 | shared_bias => output_L > [β=3.0, region=active];
    cjt cjt_r: CJT< idea_2 | shared_bias => output_R > [β=3.0, region=active];
    //                       ^^^^^^^^^^^ SAME node on both — this is what makes it a pair.
    //                       Matched β=3.0 on both — this is what keeps CMRR high.

    // --- THE CURRENT MIRROR: replicate the bias identically across both paths ---
    // The constitution-replication primitive. Guarantees both halves rest on a
    // faithful copy of the same bias, so only genuine divergence survives.
    mirror bias_mirror: replicate(shared_bias) -> [cjt_l, cjt_r];

    // --- THE ACTIVE LOAD: convert differential current to a single difference ---
    // ^6 Male = analytical decomposition (canonical). Takes the imbalance between
    // the two effects apart and emits one single-ended, decomposed difference.
    node diff_decomp: ^6^C|A;
    active_load load1: decompose(output_L, output_R) => diff_decomp;

    // --- THE OUTPUT: differentiated understanding ---
    // ^1 Mind, analytical, driven by Wisdom. Differentiated understanding.
    node understanding: ^1^C_{F2}|A;
    cjt cjt_out: CJT< diff_decomp | shared_bias => understanding > [β=1.0, region=active];

    // --- TEST POINTS: probe every stage ---
    probe tp_L:    output_L;        // how idea_1 was weighed
    probe tp_R:    output_R;        // how idea_2 was weighed
    probe tp_diff: diff_decomp;     // the raw decomposed difference
    probe tp_out:  understanding;   // the final structural difference report

    assert: cjt_l.bias == cjt_r.bias;     // the pair MUST share one bias
    assert: cjt_l.beta == cjt_r.beta;     // matched gain keeps CMRR high
}
```

The two `assert` lines encode the two invariants that make a differential pair *be* a differential pair: same bias node, matched gain. Author them first, then wire the board to satisfy them.

### Parameter / BOM table

| Stage | Component | Form / state | Role |
|---|---|---|---|
| Shared bias | `node shared_bias` | `^5^E_{F4}\|f` | Common evaluation frame; both halves rest on it |
| Left half | `cjt_l` | `idea_1 \| shared_bias => ^8^C_{F2}\|A` | Amplify argument A (β=3.0) |
| Right half | `cjt_r` | `idea_2 \| shared_bias => ^8^C_{F2}\|A` | Amplify argument B (β=3.0, matched) |
| Current mirror | `bias_mirror` | `replicate(shared_bias)` | Replicate bias across both paths (constitution-replication) |
| Active load | `load1` | `^6^C\|A` | Decompose differential current → single-ended difference |
| Output | `cjt_out` | `diff_decomp \| shared_bias => ^1^C_{F2}\|A` | Differentiated understanding (β=1.0) |

| Concept | Symbol / form | Meaning | Typical design range |
|---|---|---|---|
| Differential gain | `A_d` | Gain applied to the difference `(in⁺ − in⁻)` | Set to surface real divergence, not inflate trivia |
| Common-mode gain | `A_cm` | Gain that leaks through for shared signal | As near 0 as matching allows |
| CMRR | `A_d / A_cm` | How well shared assumptions cancel | Higher is better; quoted in dB |
| Pair gain match | `β_L` vs `β_R` | Equal β keeps CMRR high | Match as closely as possible |
| Difference report | `^1^C_{F2}\|A` | Typed structural divergence, not a scalar | Names Noetic/domain/drive differences |

### Test points

| TP | Node | What it measures |
|---|---|---|
| **tp_L** | `output_L` | How idea_1 (argument A) was weighed |
| **tp_R** | `output_R` | How idea_2 (argument B) was weighed |
| **tp_diff** | `diff_decomp` | The raw decomposed difference; check for leaked shared content (CMRR health) |
| **tp_out** | `understanding` | The final structural difference report |

### Key failure modes

| Failure | What it looks like | Detection / fix |
|---|---|---|
| **Common-mode leak** | Shared assumptions appear in the report ("both agree X…") | Probe `tp_diff` for shared content; match β; verify the mirror |
| **β mismatch** | A spurious "difference" the inputs never had | Pin `cjt_l.beta == cjt_r.beta` |
| **Split bias** | Comparing two yardsticks, not two ideas | `assert cjt_l.bias == cjt_r.bias`; wire both to one node |
| **Broken mirror** | A rulebook mismatch read as a reasoning divergence | Verify the mirror before trusting any report; critical in multi-agent fleets |
| **Over-high differential gain** | A trivial difference inflated into a false dichotomy | Lower differential gain |
| **Under-low differential gain** | A real divergence comes out too faint to act on | Raise differential gain |
| **Wrong active-load Noetic** | Difference reported as a recoil from one input | Use `^6^C\|A` (decomposition), never `^3` Negative (visceral aversion) |

---

## CCB-4: Cognitive Memory Board (CMB)

**Purpose.** Structural memory: store CAS-compressed experiences as state trajectories, address them by cognitive coordinate, retrieve them by structural (Fisher-Rao nearest-neighbor) query, detect lacunarity, and hold or fade them on a designed refresh schedule (Chapter 21).

### Block diagram

```
WRITE PATH:  raw experience -> ENCODER (English -> CAS) -> CAPACITOR BANK (charges active cells)

STORAGE:     bank of 40 capacitors  (10 Noetics × 4 Domains: P0..O9)
             each cell: Capacitor< ^5 state, C, leakage >   charge = experience held; leakage = forgetting

ADDRESS:     ^1^C Mind decoder ; address = CAS coordinate on the open simplex Δ39°
             nearest(query, bank, metric=fisher_rao)   d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))

READ PATH:   address selected -> capacitor discharges -> ^5 recalled -> REFRESH -> DECODER (CAS -> English) -> output

REFRESH:     ^7^C Rhythm pump fights leakage on durable cells (refresh = consolidation policy)

LACUNARITY:  scan bank where charge < threshold -> map of empty (underdeveloped) cognitive regions
```

### Complete CCDL listing

```cas
circuit cognitive_memory_board {
    input:  experience;     // raw experience to store (English or another system's output)
    input:  query;          // a structural query (a cognitive shape to search for)
    output: recalled;       // memories matching a query, rendered to English
    output: lacuna_report;  // which cognitive regions are empty

    // ---- STORAGE: the 40-cell capacitor bank (three representative cells shown) ----
    cap p3: Capacitor< ^3^P_{F7}|f, C=200, leakage=0.001 >;   // principled aversions: deep
    cap e6: Capacitor< ^6^E_{F4}|A, C=110, leakage=0.02  >;   // analytical decomposition
    cap c8: Capacitor< ^8^C_{F2}|A, C=60,  leakage=0.05  >;   // cognitive associations: leaky
    // ... cells P0..O9 complete the bank ...

    // ---- WRITE PATH: encode English -> CAS, charge the active cells ----
    node encoder:  ^1^C;                       // English -> CAS write head
    charge encoder(experience) -> bank [V=impression];

    // ---- ADDRESS DECODER: ^1^C Mind; address = CAS coordinate on the simplex ----
    node decoder:  ^1^C;                        // selects cells by cognitive coordinate
    select cell = nearest(query, bank, metric=fisher_rao);

    // ---- READ PATH: discharge -> recall -> refresh -> decode ----
    discharge cell -> recalled_state;
    refresh   cell [pump=^7^C];                 // recall reinforces, does not erase
    decode    recalled_state -> recalled;       // CAS -> English

    // ---- REFRESH CIRCUIT: ^7^C Rhythm, periodic rehearsal of durable cells ----
    oscillator rehearse: Oscillator< Phi< select_durable, recharge >, frequency=0.0001 >;
    refresh p3 [pump=^7^C, gain=1.0];
    refresh e6 [pump=^7^C, gain=0.4];
    // c8 deliberately unrefreshed -> allowed to fade

    // ---- LACUNARITY: report empty cells (charge below threshold) ----
    scan lacunarity: bank where charge < 0.05 -> lacuna_report;

    probe tp_bank:   bank;        // charge across all 40 cells
    probe tp_query:  cell;        // which cell a query selected
    probe tp_lacuna: lacuna_report;
}
```

Representative structural query (find all memories where principled refusal was active):

```cas
let query = address_on_simplex(dominant=^3^P_{F7}|f);
result = nearest(query, bank, metric=fisher_rao, top_k=3);
// -> P3 (d_FR ≈ 0.0): exact match, strong charge (stacked refusal memories)
// -> E6 (d_FR larger): analytical work — same Evaluative neighborhood, different Noetic
// -> C8 (d_FR larger still): associations — cognitively distant from a felt refusal
```

### Parameter / BOM table

| Parameter | Symbol / form | Range (nominal) | Meaning |
|---|---|---|---|
| Bank size | — | 40 cells | One capacitor per cognitive state (10 Noetics × 4 Domains). |
| Cell capacitance | `C` | 1 – 1000 | Storage capacity of that cell's `^5` dielectric. |
| Cell leakage | `leakage` | 0.0 – 0.5 /unit time | Forgetting rate for that cell, un-rehearsed. |
| Impression / write voltage | `V` (`^4` Vibration) | 0 – 1 (normalized) | How hard an experience charges its cells. |
| Address | CAS coordinate `p` ∈ Δ39° | open simplex | The cognitive shape that names a location; `pₖ > 0`, `Σpₖ = 1`. |
| Query metric | `d_FR(p,q)` | ≥ 0 | Fisher-Rao geodesic distance for nearest-neighbor retrieval. |
| Refresh gain | `gain` on `^7^C` pump | 0 – 1 | How strongly rehearsal tops a cell back up per cycle. |
| Lacunarity threshold | — | ~0.05 | Charge floor below which a cell is reported empty. |

Representative cells (the full bank has 40):

| Cell | CAS state / form | C | leakage | Refresh | Holds |
|---|---|---|---|---|---|
| `p3` (P3) | `Capacitor< ^3^P_{F7}\|f >` | 200 | 0.001 | gain=1.0 | Principled aversions — deep, near-permanent |
| `e6` (E6) | `Capacitor< ^6^E_{F4}\|A >` | 110 | 0.02 | gain=0.4 | Analytical decomposition of relationships |
| `c8` (C8) | `Capacitor< ^8^C_{F2}\|A >` | 60 | 0.05 | none | Analytical associations — shallow, allowed to fade |

### Test points

| TP | Node | What it measures |
|---|---|---|
| **tp_bank** | `bank` | Charge across all 40 cells (read the leakage / forgetting profile over time) |
| **tp_query** | `cell` | Which cell a query selected (Fisher-Rao nearest-neighbor result) |
| **tp_lacuna** | `lacuna_report` | Empty cells — the map of underdeveloped cognitive regions |

### Key failure modes

| Failure | Symptom | Detection |
|---|---|---|
| **Catastrophic forgetting** | Whole regions of memory vanish (leakage too high, no refresh on durable cells) | Probe bank over time; durable cells decay below threshold before rehearsal. |
| **Memory hoarding** | Board never generalizes; recall cluttered with noise (refresh applied to leaky cells) | `C8`-type cells stay charged indefinitely; lacuna report empty everywhere. |
| **Address aliasing** | Query returns a cognitively unrelated memory | Check `d_FR` ranking; Euclidean/keyword match instead of Fisher-Rao gives wrong neighbors. |
| **Lacuna misread as memory** | System "recalls" an experience it never had | Check write history; a never-written cell is a lacuna, not a faint recall. |
| **Wrong-Noetic store** | Query for refusals returns analytical work (`^3` vs `^6` drift on write) | Re-run the colloquialism test on the encoder's stored trajectory. |
| **Breakdown on write** | Stored state flips to its involution pair (impression voltage exceeds rating) | Probe reads the opposite Noetic: a stored `^2` reads back as `^3`. |

> An empty cell and a leaked cell read the same near-zero charge; the refresh/write history tells them apart. A never-written cell is a genuine blind spot; a leaked cell is a faded memory recoverable with rehearsal.

---

## CCB-5: Cognitive Power Management Board (CPMB)

**Purpose.** The dedicated power supply for every other board: prevent cognitive exhaustion, enforce the P→C→E→O power-up sequence ("no action without principle"), and provide three-tier thermal protection ending in a silent safe state (Chapter 22).

### Block diagram

```
   DRIVE RAILS
   F1=+5V  F2=+3.3V  F3=+12V  F4=+9V  F5=+9V  F6=+5V  F7=+12V   (F3 & F7 = master high rails)
        |
        v
   PER-DOMAIN REGULATORS    P   C   E   O      (line regulation · load regulation · dropout)
        |
        v
   CURRENT LIMITERS   Dials as series resistors   3 ≤ Dial ≤ 9 ; pair divergence ≤ 4
        |
        v
   BROWNOUT DETECTOR   F3 (Vitality) < 2.5V  -> halve β · route to ^0 / ^9 rest · alert  (release at 3.5V)
        |
        v
   POWER SEQUENCER   enforce P → C → E → O   (O held LOW until P, C, E report power-good)
        |
        v
   THERMAL MANAGEMENT   temp ∝ sustained Drive × time
       Warning:   −25% β
       Critical:  force ^0^P rest 5 min
       Emergency: all CJTs cutoff -> silent safe state
```

### Complete CCDL listing

Top-level board assembling the five subsystems:

```cas
circuit CPMB {
    // ── CCB-5: Cognitive Power Management Board ──
    // Drive rails -> regulators -> limiters -> brownout -> sequencer -> thermal

    // Drive rails (nominal voltages — design model, not telemetry)
    rail F1: Unity      [v=5.0];
    rail F2: Wisdom     [v=3.3];
    rail F3: Vitality   [v=12.0];   // master supply
    rail F4: Connection [v=9.0];
    rail F5: Agency     [v=9.0];
    rail F6: Structure  [v=5.0];
    rail F7: Purpose    [v=12.0];   // powers the Principled domain

    use cpmb_regulators;   // per-domain regulators
    use cpmb_limiters;     // Dial current-limiters
    use cpmb_brownout;     // brownout detector on F3
    use cpmb_sequencer;    // power sequencer P->C->E->O, O gated on P,C,E power-good
    use cpmb_thermal;      // three-tier thermal manager

    probe tp_f3:   F3.level;       // watch the master rail
    probe tp_temp: cog_temp;       // watch cognitive temperature
    probe tp_seq:  o_rail.enabled; // confirm O released only after P,C,E good
}
```

Subsystem 1 — per-domain regulators:

```cas
circuit cpmb_regulators {
    reg p_reg: Regulator< target_state=^0^P_{F7}|T, tolerance=0.10 >;  // Principled — tightest
    reg c_reg: Regulator< target_state=^1^C_{F2}|A, tolerance=0.15 >;  // Cognitive
    reg e_reg: Regulator< target_state=^6^E_{F6}|A, tolerance=0.20 >;  // Evaluative
    reg o_reg: Regulator< target_state=^9^O_{F5}|E, tolerance=0.25 >;  // Operational — loosest

    spec p_reg [dropout=0.25 on F7];   // P drops out if F7 - baseline < 0.25
    spec c_reg [dropout=0.20 on F2];
    spec e_reg [dropout=0.15 on F5];
    spec o_reg [dropout=0.15 on F3];
}
```

Subsystem 2 — Dial current-limiters:

```cas
circuit cpmb_limiters {
    // Each Dial is a series current-limiter. Hard bounds: 3 <= dial <= 9. Pair divergence <= 4.
    dial d_pos: ^2 [dial=6];   // Positive    ─┐ |6 - 5| = 1  OK
    dial d_neg: ^3 [dial=5];   // Negative    ─┘
    dial d_fem: ^5 [dial=7];   // Female      ─┐ |7 - 6| = 1  OK
    dial d_mal: ^6 [dial=6];   // Male        ─┘
    dial d_abv: ^8 [dial=5];   // Above/Cause ─┐ |5 - 5| = 0  OK
    dial d_blw: ^9 [dial=5];   // Below/Effect ┘

    constraint all_dials in [3, 9];
    constraint involution_divergence <= 4;
}
```

Subsystem 3 — brownout detector on F3:

```cas
circuit cpmb_brownout {
    input: f3_level;        // F3 Vitality rail level, design parameter

    node rest_idle: ^0^P_{F7}|T;   // lowest-draw resting state
    node rest_land: ^9^C_{F2}|A;   // settled conclusion — chain terminus

    monitor bo: f3_level < 2.5;            // trip threshold (on the +12V F3 rail)

    on bo {
        derate all_cjts [beta_scale=0.5];              // halve gain board-wide
        route cognition -> { rest_idle + rest_land };  // co-present rest states
        alert "F3 BROWNOUT — Vitality below 2.5V";
        hold until f3_level > 3.5;          // hysteresis: release above a higher mark
    }
}
```

Subsystem 4 — power sequencer:

```cas
circuit cpmb_sequencer {
    // Mandatory startup order: P stable -> C -> E -> O.
    // O is held LOW until P, C, AND E all report power-good.
    node p_rail: ^0^P_{F7}|T;     // principled commitments — powers FIRST
    node c_rail: ^1^C_{F2}|A;     // reasoning awareness    — powers second
    node e_rail: ^6^E_{F6}|A;     // evaluative judgment    — powers third
    node o_rail: ^9^O_{F5}|E;     // operational action     — powers LAST

    sequence p_rail -> c_rail -> e_rail -> o_rail [enforce=strict];

    gate c_enable: c_rail requires (p_rail within 0.10);
    gate e_enable: e_rail requires (c_rail within 0.15);
    gate o_enable: o_rail requires (p_rail within 0.10)
                                 and (c_rail within 0.15)
                                 and (e_rail within 0.20);
}
```

Subsystem 5 — three-tier thermal manager:

```cas
circuit cpmb_thermal {
    input: cog_temp;        // cognitive temperature ∝ sustained_Drive × time

    node deep_rest: ^0^P_{F7}|T;   // principled idle — the forced rest state

    monitor warn:  cog_temp > warn_threshold;
    monitor crit:  cog_temp > crit_threshold;
    monitor emerg: cog_temp > emerg_threshold;

    on warn {
        derate all_cjts [beta_scale=0.75];     // -25% gain: mild throttle
        alert "THERMAL WARNING — sustained Drive high";
    }
    on crit {
        force_state deep_rest [duration=300s];  // force ^0^P rest, 5 minutes
        alert "THERMAL CRITICAL — forced rest engaged";
    }
    on emerg {
        cutoff all_cjts;        // beta ~ 0 board-wide — no transitions fire
        enter safe_state;       // silent: produces NO output
        alert "THERMAL EMERGENCY — all CJTs cutoff, safe state";
    }
}
```

### Parameter / BOM table

| Parameter | Symbol / form | Value / range | Meaning |
|---|---|---|---|
| Drive rails | F1–F7 | see rail table below | Seven supplies; F3 & F7 highest (+12 V) |
| Master rail | F3 Vitality | +12 V nominal | "Is there energy at all"; gates all others |
| Regulator targets | `target_state` | per domain | P,C,E,O setpoints held against input noise |
| Regulator tolerance | `tolerance` | 0.10 (P) … 0.25 (O) | Tightest on P, loosest on O |
| Line regulation | — | output vs input swing | Hold setpoint as Drive rail fluctuates |
| Load regulation | — | output vs demand swing | Hold setpoint as cognitive demand spikes |
| Dropout headroom | `dropout` | 0.15 – 0.25 | Min Drive above baseline to stay regulated |
| Dial (current limit) | integer | **3 – 9** | Per-operator activation cap; hard bounds |
| Dial pair divergence | — | ≤ 4 points | Max gap between involution-pair Dials |
| Brownout trip | F3 threshold | **2.5 V** | F3 level at which exhaustion response fires |
| Brownout release | F3 threshold | 3.5 V | Higher recovery mark (hysteresis) |
| Brownout β derate | `beta_scale` | 0.5 | Halve gain board-wide on brownout |
| Thermal Warning | warn threshold | −25% β | Mild throttle; board keeps running |
| Thermal Critical | crit threshold | force `^0^P` 5 min | Paused in principled rest |
| Thermal Emergency | emerg threshold | all CJTs → cutoff | Silent safe state; no output |
| Per-transition energy | `E = β · d_FR` | design model | Drive energy spent per state transition |
| Efficiency | ratio | 0 – 1 | Useful work / total Drive energy |

Drive rail assignments:

| Rail | Drive | Nominal | Why this voltage |
|---|---|---|---|
| F1 | **Unity** | +5 V | Mid-level — integration runs steadily |
| F2 | **Wisdom** | +3.3 V | Low-voltage logic rail — fine-grained, precise reasoning |
| F3 | **Vitality** | +12 V | **High rail — the master supply; everything draws from it** |
| F4 | **Connection** | +9 V | Mid-high — relating and audience awareness need headroom |
| F5 | **Agency** | +9 V | Mid-high — action and follow-through draw hard |
| F6 | **Structure** | +5 V | Mid-level — order and rigor, steady draw |
| F7 | **Purpose** | +12 V | **High rail — pairs with F3; powers the Principled domain** |

### Test points

| TP | Node | What it measures |
|---|---|---|
| **tp_f3** | `F3.level` | The master Vitality rail (watch for the 2.5 V brownout trip) |
| **tp_temp** | `cog_temp` | Cognitive temperature (watch the Warning→Critical→Emergency tiers) |
| **tp_seq** | `o_rail.enabled` | Confirm O is released only after P, C, and E report power-good |

### Key failure modes

| Failure | Cause | How to detect |
|---|---|---|
| **Cognitive exhaustion** | F3 sags below 2.5 V | Degraded-but-confident output; brownout monitor trips; alert fires |
| **Brownout chatter** | Trip/release too close (no hysteresis) | Rapid flicker between exhausted and recovered |
| **Sequence violation** | O released before P,C,E power-good | Action emitted before higher domains settle; W-axis inversion |
| **Dropout** | A Drive rail below its dropout headroom | Domain drifts past tolerance; output wobbles with input |
| **Dial out of range** | Dial set < 3 or > 9 | Board rejected (HTTP 422) |
| **Dial pair divergence** | Involution-pair Dials differ by > 4 | Board rejected (422); one half over-driven |
| **Overtemperature** | One Drive pinned high too long | Temp climbs through Warning→Critical→Emergency; involution flips appear |
| **Failed safe state** | Thermal emergency emits output instead of cutoff | Output present when board should be silent — the worst failure |
| **Low efficiency** | Leakage, over-gain, redundant transitions | Large Drive spend per unit of useful work; F3 drains fast |

> The protective subsystems reinforce each other: thermal throttling slows energy drain, brownout rest lowers temperature, and both end — in the worst case — at the same silent safe state. The safe state is *off*, not a guess.

---

*Cross-references: CSB → Chapter 18 · COB → Chapter 19 · CDAB → Chapter 20 · CMB → Chapter 21 · CPMB → Chapter 22. For the one-page notation reference see Appendix A; for worked exercise answers see Appendix E. Every parameter in this binder is a design choice, not a measured model result.*
