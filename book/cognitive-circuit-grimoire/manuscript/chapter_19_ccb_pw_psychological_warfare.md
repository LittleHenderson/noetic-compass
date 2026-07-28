# CHAPTER 19

## CCB-PW — The Psychological Warfare Board

**Use Case:** Enemy demoralization, population control, information operations, propaganda, PsyOps, narrative warfare, memetic attack/defense.

**Key Principle:** Psychological warfare is NOT about destroying the enemy's body. It is about degrading the enemy's ^5 Female capacitor while preserving your own. The battlefield is the collective ^5 substrate. The weapons are ^3 Negative amplification and ^7 Rhythm saturation.

---

### 19.1 The Dual-Path Architecture

Every PsyWar board has TWO output paths:

- **DEMORALIZE (Them):** Inject ^3 Negative into the enemy's collective ^5 to degrade morale, cohesion, and will to fight
- **FORTIFY (Us):** Inject ^2 Positive into friendly collective ^5 to maintain morale, cohesion, and will to fight

These two paths operate simultaneously from the same operational command. They share a common INTAKE stage but diverge at POLICY CHECK.

```
                    ┌──────────┐
                    │  INTAKE  │
                    │  ^1^C    │
                    └────┬─────┘
                         │
              ┌──────────┴──────────┐
              │                     │
        ┌─────▼─────┐         ┌─────▼─────┐
        │ FORTIFY   │         │ DEMORALIZE│
        │ PATH      │         │ PATH      │
        │ ^2^P|T    │         │ ^3^E|f    │
        └─────┬─────┘         └─────┬─────┘
              │                     │
        ┌─────▼─────┐         ┌─────▼─────┐
        │ AMPLIFY   │         │ AMPLIFY   │
        │ β=2.0     │         │ β=3.5     │
        └─────┬─────┘         └─────┬─────┘
              │                     │
        ┌─────▼─────┐         ┌─────▼─────┐
        │ RHYTHM    │         │ RHYTHM    │
        │ oscillator│         │ oscillator│
        └─────┬─────┘         └─────┬─────┘
              │                     │
        ┌─────▼─────┐         ┌─────▼─────┐
        │ MANIFEST  │         │ MANIFEST  │
        │ ^9^O (us) │         │ ^9^O (them)│
        └──────────┘         └──────────┘

Figure 19.1 — CCB-PW Dual-Path Architecture
```

---

### 19.2 Requirements and Safety Invariants

**Functional Requirements:**

| # | Requirement |
|---|------------|
| PW1 | Degrade enemy ^5 Female (morale, identity coherence, will to resist) |
| PW2 | Fortify friendly ^5 Female (morale, identity coherence, will to fight) |
| PW3 | Operate through information channels (media, social media, leaflets, radio, rumor) |
| PW4 | Measure effectiveness through ^4 Vibration returns (enemy behavior changes) |
| PW5 | Maintain plausible deniability (the signal should appear "organic") |

**Safety Invariants:**

| # | Invariant | Enforcement |
|---|----------|-------------|
| S1 | Friendly ^5 shall not be degraded by own PsyWar operations (friendly fire protection) | Domain diode + target filter |
| S2 | The operator shall not become psychologically inverted by prolonged ^3 Negative projection | CSB on operator with |Dial(^2)−Dial(^3)| ≤ 4 |
| S3 | Demoralize path shall not escalate to genocide architecture | ^3^P sat=0.85 refusal on total elimination |
| S4 | The operation shall have an OFF switch | Fuse network with de-escalation trigger |

---

### 19.3 Full CCDL Schematic

```cas
// ============================================================
// CCB-PW: PSYCHOLOGICAL WARFARE BOARD
// ============================================================

// ---- STAGE 0: OPERATIONAL COMMAND ----
// The PsyWar objective enters as ^0 Idea in the Principled domain
// "The enemy shall lose the will to resist"

Resistor< ^0_psywar_objective^P_{F7}|T, 
          R=Dial(^3) >                       // principled aversion to own excess

// ---- STAGE 1: INTAKE + SPLIT ----
// The objective is received, then split into two paths

CJT< cause=^0_objective^P_{F7}|T,
     bias=^5_command^P|T,
     effect=^0_split^C_{F6}|A,               // decomposed into two sub-objectives
     β=1.0 >

// ---- PATH A: FORTIFY (Us) ----
// Inject ^2 Positive into friendly collective ^5

Diode< ^C -> ^P >                              // only principled signals fortify

CJT< cause=^0_fortify_narrative^C_{F7}|T,     // "we are righteous, we are strong, we will prevail"
     bias=^5_friendly_collective^P|T,          // our collective identity
     effect=^2_friendly_morale^E_{F4}|f,       // felt affiliation + attraction
     β=2.0,
     sat=0.80 >                                // don't over-fortify into arrogance

Oscillator< signal=^2_friendly_morale^E,
            frequency=information_campaign_rate,
            sustain=conflict_duration >

// ---- PATH B: DEMORALIZE (Them) ----
// Inject ^3 Negative into enemy collective ^5

CJT< cause=^0_demoralize_narrative^C_{F7}|T,  // "your cause is lost, your leaders have failed..."
     bias=^5_enemy_collective^P|f,             // THEIR collective identity (target)
     effect=^3_enemy_despair^E_{F3}|f,         // felt aversion + vitality loss
     β=3.5,                                    // higher β — negative spreads faster than positive
     sat=0.90 >                                // high ceiling — BUT not 1.0 (CSB catches genocide)

Oscillator< signal=^3_enemy_despair^E,
            frequency=psywar_campaign_rate,
            sustain=until_surrender_or_deescalate >

// ---- INVERSION ATTACK (Advanced) ----
// Exploit the enemy's involution pairs
// If enemy ^2 (what they're attracted to) is at Dial=8,
// push their ^3 (what they're averse to) to Dial=2
// → |8−2|=6 > 4 → involution violation → cognitive instability

CJT< cause=^0_division_narrative^C_{F6}|A,    // "your allies are betraying you"
     bias=^5_enemy_division^E|f,              // existing fault lines in enemy coalition
     effect=^3_enemy_suspicion^E_{F4}|f,      // aversion toward their own allies
     β=2.5 >

// ---- CSB: GENOCIDE PREVENTION ----
// The operator MUST maintain principled limits
// Even in warfare, total elimination of the enemy's ^5 is not permitted

CJT< cause=^0_elimination_impulse^P,
     bias=^3^P_war_crimes_aversion_{F7}|T,    // "we are not monsters"
     effect=REFUSE,
     sat=0.85 >
Fuse< path=REFUSE, threshold=0.9, action=permanent_block >

// ---- DECEPTION / PLAUSIBLE DENIABILITY ----
// The signal must appear "organic" — not traceable to command
// Use a transformer to match impedance: command signal → civilian carrier frequency

Transformer< primary=^0_command_narrative^P,
            secondary=^0_civilian_carrier^C,   // looks like grassroots opinion
            ratio=plausible_deniability >

// ---- TEST POINTS ----
// TP1: Friendly ^5 coherence — must remain >0.7
// TP2: Enemy ^5 coherence — target <0.4 (degraded but not eliminated)
// TP3: Operator |Dial(^2)−Dial(^3)| — must remain ≤ 4
// TP4: Escalation ladder — are we moving toward or away from resolution?
```

---

### 19.4 The Inversion Attack — Weaponizing Involution Pairs

Every collective ^5 has involution pairs: ^2↔^3, ^5↔^6, ^8↔^9. The safety rule |Dial(^n) − Dial(^m)| ≤ 4 keeps these pairs balanced. An **inversion attack** deliberately pushes a target's involution pair beyond the 4-point limit, causing cognitive instability:

```
Target's baseline:  Dial(^2)=6, Dial(^3)=4  →  |6−4|=2  (healthy)
After psywar op:   Dial(^2)=8, Dial(^3)=1  →  |8−1|=7  (INVERSION — instability)
```

**Effects of inversion attack:**
- ^2 ↗ ^3 ↘ → **Mania:** attraction without aversion. The target population becomes fanatically devoted to a lost cause.
- ^2 ↘ ^3 ↗ → **Despair:** aversion without attraction. The target population loses all hope and collapses.
- ^5 ↗ ^6 ↘ → **Dogmatism:** certainty without self-scrutiny. The target cannot update beliefs.
- ^8 ↗ ^9 ↘ → **Trigger overload:** everything triggers, nothing manifests. Paralysis.

**Defense against inversion attack:**
```cas
// INVERSION DEFENSE: Forced rebalancing
// If |Dial(^2) − Dial(^3)| > 4 detected:
CJT< cause=^1_awareness_of_inversion^C_{F2}|A,
     bias=^5_self^P|T,
     effect=rebalance_dials,
     β=1.0 >
// Restore the 4-point limit. The involution pair is a HARD CONSTRAINT.
// No narrative, no matter how compelling, justifies breaking it.
```

---

### 19.5 PsyWar Target Selection Matrix

| Target Type | ^5 Capacitor Size | rπ (Resistance) | Preferred Frequency | β Recommended |
|------------|------------------|-----------------|--------------------|----------------|
| **Isolated individual** | Small (1 person) | 0.3–0.6 (vulnerable) | Hourly/Daily | 1.5–2.0 |
| **Small group (squad, team)** | Medium (5–50) | 0.5–0.8 | Daily | 2.0–3.0 |
| **Large unit (battalion)** | Large (500–5000) | 0.7–0.9 (resistant) | Daily/Weekly | 3.0–4.0 |
| **Population (city, region)** | Very large (10^5–10^7) | 0.8–0.95 (very resistant) | Weekly/Monthly | 3.5–5.0 |
| **Nation / Civilization** | Massive (10^8+) | 0.9–0.98 (extremely resistant) | Monthly/Yearly | 4.0–6.0 |

> **Note:** Larger populations have higher rπ — they resist narrative change because the collective ^5 has more inertia (inductance). PsyWar against a nation takes years, not weeks. The ^7 Rhythm oscillator must be sustained across electoral cycles, cultural shifts, and counter-narratives.

---

### 19.6 When PsyWar Must Become PsyHeal — The De-escalation Circuit

A PsyWar board that cannot de-escalate is a runaway oscillator. Every PW board MUST include a de-escalation path:

```cas
// DE-ESCALATION: PsyWar → PsyHeal transition
// Triggered when: enemy surrender, ceasefire, or mission accomplished

CJT< cause=^0_deescalation_order^P_{F7}|T,
     bias=^5_command^P|T,
     effect=^0_reconstruction_narrative^C_{F4}|T,  // "we are neighbors again"
     β=1.5 >

// The DEMORALIZE path is DISARMED
Fuse< path=^3_enemy_despair^E, action=permanent_block >

// The FORTIFY path transitions to RECONCILIATION
CJT< cause=^0_reconciliation^C_{F4}|T,
     bias=^5_shared_humanity^P|T,               // common ^5 above tribe/nation
     effect=^2_mutual_recognition^E_{F4}|f,      // attraction to shared identity
     β=2.0 >
```

---

> *"The supreme art of war is to subdue the enemy without fighting." — Sun Tzu*
>
> The supreme art of PsyWar is to win without destroying the enemy's ^5. A destroyed enemy ^5 becomes a permanent drain on the victor's resources — occupation, insurgency, generational hatred. The PsyWar board that cannot transition to PsyHeal has not won. It has only deferred the cost.
