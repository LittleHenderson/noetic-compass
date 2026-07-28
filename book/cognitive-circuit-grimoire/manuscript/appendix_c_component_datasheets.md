# APPENDIX C
## CCB Component Datasheets
*Selection limits, governing equations, failure signatures, and proof-load tests*

These sheets condense Part II. They do not replace the chapters: a datasheet
tells you whether a part belongs on a board and how to prove the installed part;
the chapter explains why the part behaves that way.

All numeric ranges are **book design ranges**, not measurements of nature.
`V_c`, `A_c`, `Ω_c`, `F_c`, and `h·Ω_c` are scaled cognitive-circuit units.
Before accepting any design:

1. verify every state literal against Appendix A;
2. verify every statement form against Appendix B;
3. compute the operating point rather than reading a parameter in isolation;
4. test the part under the condition meant to trip, saturate, filter, or stress
   it; and
5. retain the failed proof load in the ledger.

---

### C.1 Fixed Resistor — deliberate constraint

**CAS role.** A fixed resistor is a declared obstacle on an attention path. It
implements the deliberate `R_policy` term in the operating resistance:

```text
R_op = R_capacity + R_policy + R_context + R_residual
I_attention = V_drive / R_op
```

**CCDL form.**

```cas
resistor r1: Resistor< path=request, R=40.0 >;
```

| Item | Specification |
|---|---|
| `R` | 10–90 `Ω_c` in the book's standard design window |
| Path ceiling | `I_max = 1.00 A_c` |
| Series network | `R_series = ΣR_k` |
| Parallel network | `1/R_parallel = Σ(1/R_k)` and `R_parallel < min(R_k)` |

**Selection.** Use a resistor for graded friction. Use a fuse for an absolute
stop. A rule that permits no flow but is built as a very large resistor will be
removed when ordinary work cannot pass it.

**Failure signatures.**

- Too low: the policy is cosmetic; output nearly equals input.
- Too high: the path starves; operators route around or remove the guard.
- Undeclared parallel route: the bypass dominates the total resistance.
- Series/parallel swap: a vulnerability is counted as a wall.

**Proof load.** Apply a known `V_drive`; read flow before and after the part.
The measured ratio must match `V/R` within the declared tolerance. Enumerate
every other route between the same nodes before calling the reading complete.

---

### C.2 Noetic Dial and Drive Divider

**CAS role.** A dial turns a bounded Noetic setting into resistance. A paired
`^2` / `^3` divider determines how much Drive reaches the next stage:

```text
R_dial = 10 × Dial
k = Dial(^2) / (Dial(^2) + Dial(^3))
```

| Item | Specification |
|---|---|
| Dial range | integers 3–9 |
| Involution spread | `|Dial(a) − Dial(a*)| ≤ 4` |
| Resulting resistance | 30–90 `Ω_c` |
| Lawful `k` range | 0.30–0.70 |

**Selection.** Use the divider when attraction and aversion must both remain
connected. Do not use it as a way to make doubt vanish. The lawful maximum
transmission is `(7,3) → 0.700`, not `(9,3) → 0.750`; the latter pair is
illegal, and `(9,5)` transmits only 0.643.

**Failure signatures.**

- Dial outside 3–9 or spread above 4: compile-time rejection, never clamping.
- Attraction maximized by appetite: lower transmission than the lawful optimum.
- `k = 1` requested: an attempt to delete the involution partner.

**Proof load.** Read both dials and compute the ratio independently. A displayed
`k` without the two source settings is not auditable.

---

### C.3 Thermistor — temperature-dependent constraint

**CAS role.** The cognitive temperature `θ` belongs to the discourse around an
Idea. A PTC thermistor raises resistance as temperature passes its knee; an NTC
lowers it.

```cas
thermistor rt1: Thermistor<
    path=topic,
    type=PTC,
    theta_k=2.5,
    coeff=3.5
>;
```

| Item | Specification |
|---|---|
| `θ` operating scale | 1.0–6.0 |
| PTC knee `θ_k` | 2.0–3.0 |
| PTC coefficient | 3.0–4.0 `Ω_c/θ²` |
| Guard polarity | PTC |

**Failure signatures.**

- NTC on a guard: calm bring-up passes, then resistance falls as pressure
  rises—thermal runaway.
- Knee too low: ordinary discussion is taxed.
- Knee too high: the guard engages after the damage.
- Temperature attached to the Idea instead of the discourse: the wrong signal
  tunes the part.

**Proof load.** Sweep `θ` slowly across the knee while monitoring resistance.
Any protective part whose resistance falls with increasing `θ` is removed
before downstream tests.

---

### C.4 Capacitor — composed substrate and retained charge

**CAS role.** A `^5` substrate stores a pattern. `^7` is feed cadence, `^4` is
per-exposure amplitude, and a controlled `^6` path discharges or decomposes it.

```text
P_charge(t) = V_drive(1 − e^(−t/τ))
τ = R × C
P(t) = P_eq + (P_0 − P_eq)e^(−t/τ_leak)
P_eq = feed × τ_leak
τ_leak = −Δt / ln(1 − leakage)
```

```cas
capacitor c1: Capacitor<
    node=substrate,
    C=0.05,
    leak_tau=90.0,
    V_BR=8.0
>;
```

| Item | Specification |
|---|---|
| `C` | non-negative `F_c`, with time base declared |
| `τ` | positive; derive from `R × C` |
| `leakage` | 0–1 per stated interval |
| `leak_tau` | positive; alternative spelling of leakage, not a second knob |
| `V_BR` | positive and declared |
| Working stress | at or below 0.5 × `V_BR` |
| Rail | 0–10 `V_c`; the rail is the final ceiling |

**Failure signatures.**

- Feed below `P/τ_leak`: slow decay with no dramatic fault.
- High intensity without cadence: memorable sessions, no retention.
- Cadence without impression: a perfect schedule depositing nothing.
- Target above `V_drive`: permanent plateau below target; more time cannot fix
  it.
- Wrong leakage conversion: an apparently viable schedule settles far below
  intent.
- Rising rest leakage: cumulative dielectric stress.

**Proof load.** Read charge and feed together. Then stop the feed for one stated
interval and compare the decay with the declared `τ_leak`. Finally measure
working stress against `V_BR`; do not wait for breakdown.

---

### C.5 Capacitor Bank — co-present stores

**CAS role.** Multiple distinct stores sharing a rail are co-present:

```text
^5^P|T + ^5^P|T + …
```

They are not integrated with `×` unless a named emergent result is actually
specified.

```cas
capacitor c_bank: Capacitor<
    node=shared_composition,
    C=0.05,
    n_parallel=12,
    r_iso=12.0,
    leak_tau=18.0,
    V_BR=8.0
>;
```

| Item | Specification |
|---|---|
| Parallel capacitance | `C_total = ΣC_k` |
| `n_parallel` | integer ≥ 1 |
| Per-cell ballast `r_iso` | ≥ 0 `Ω_c`; book default 12 |
| Series chain | smallest `C` receives the greatest voltage stress |

**Failure signatures.**

- No per-cell isolation: one failed cell drags the rail.
- Whole persons counted as capacitance instead of their shared composition:
  calendar and capacity are inflated.
- Series chain without balancing: the smallest cell exceeds its rating.
- Unnamed `×`: a group is called a single mind with no emergent result defined.

**Proof load.** Scan each cell, not only the rail. Open and short one cell under
a safe test level; verify the remaining cells do not collapse or exceed their
stress allocation.

---

### C.6 Domain Diode — one-way descent

**CAS role.** A domain diode permits descent only:

```text
P ≻ C ≻ E ≻ O
```

```cas
diode d1: Diode< from=principle, to=analysis, Vf=0.7 >;
```

| Item | Specification |
|---|---|
| Lawful direction | P→C, C→E, E→O, including skipped downward stages |
| Ordinary upward direction | rejected |
| Drop `Vf` | declared design cost on the path |
| Reverse leakage | treated as a fault unless the explicit feedback form applies |

**The one lawful ascent.** Operational outcomes may update a Principled
substrate only through the filtered, low-gain O→P feedback path:

```text
β_feedback = 0.05–0.30
low-pass τ ≥ 1 week
outcomes only, never prompts
```

**Failure signatures.**

- O→P diode described as “checking” or “learning”: counterfeit promotion.
- Feedback with no gain: open upward path.
- High-pass on feedback: one dramatic event rewrites the constitution.
- Reversed diode: a lower-precedence state silently authors a higher one.

**Proof load.** Forward-bias with a known descending signal, then reverse-bias.
The reverse test must yield no ordinary transmission. Test the explicit
feedback path separately with a spike and a sustained outcome: the spike dies;
the trend passes at declared attenuation.

---

### C.7 Cognitive Junction Transistor — gated gain

**CAS role.** A CJT has cause, bias, and effect terminals. Cause supplies the
signal; bias determines whether and how the stage conducts; effect is the
output.

```cas
cjt q1: CJT<
    cause=input,
    bias=frame,
    effect=output,
    beta=1.5,
    gm=0.50,
    rpi=5.0,
    cutoff=0.10,
    sat=0.80
>;
```

```text
effect = clamp(β × cause, 0, sat)
rπ_intrinsic = β/g_m
R_bias = rπ_terminal − β/g_m
β_required = target_effect / arriving_cause
```

| Item | Specification |
|---|---|
| `β` | 0.05–4.0; zero is cutoff, not attenuation |
| Decision-stage `sat` | 0.60–0.85 |
| Production-stage `sat` | ≥ 1.25 × peak effect |
| `cutoff` | 0.05–0.20 and strictly below `sat` |
| baseline `g_0` | 0.25–1.00 `S_c` |
| `R_bias` | 0–6 `Ω_c` |
| Cascade depth | ≤ 6 at assumed per-stage contamination `ε = 0.03` |

**Selection.** Set gain from the effect required after known resistance, never
from appetite. Saturate a decision on purpose; keep a measurement or production
stage in its active region.

**Failure signatures.**

- Guard left at `sat=0.95`: extra steerable cause-space before it latches.
- Production stage saturated: a clipped instrument reporting false stability.
- `sat` above substrate `I_c(max)`: designed latch is unreachable.
- `β`, `g_m`, and `rπ` independently plausible but `R_bias < 0`: nonexistent
  stage described by three good-looking numbers.
- Unlogged `g_m`: framing changes dominate without appearing in the plan.
- Long cascade: tolerances and contamination compound.

**Proof load.** Read TP1 bias, TP2 cause, TP3 effect and region, TP4
re-reference drift. Increase cause by 20 percent: a production effect must move;
a deliberately saturated decision must remain pinned. Independently subtract
`β/g_m` from terminal `rπ`.

---

### C.8 Inductor — resistance to rate of change

**CAS role.** An inductor opposes changes in attention flow:

```text
V_opposition = L × di/dt
τ = L/R
I_final = V/R
```

Inductance scales with pattern depth and domain:

| Domain | Book factor `k_d` |
|---|---|
| O Operational | 0.5 |
| E Evaluative | 1.0 |
| C Cognitive | 2.0 |
| P Principled | 4.0 |

**Failure signatures.**

- Abrupt interruption: large back-EMF landing as felt aversion.
- Taper faster than the modeled limit: contacts open instead of moving.
- No flyback / substitute path: the vacated cadence fills with the nearest
  available pattern.
- Lowering `R` to “make it easier”: a slower, deeper transition, not a faster
  one.
- Unmodeled coupling: another person's backlash omitted from the circuit.

**Proof load.** Establish the substitute path first. Then read new-path flow,
`di/dt`, old-path exponential decay, and kick voltage—in that order. Book
designed tapers use roughly 0.002–0.03 `A_c/h`; readings above 0.05 indicate an
opening contact.

---

### C.9 Transformer — coupled change

**CAS role.** A transformer transfers *change*, not steady state:

```text
V_secondary = M × di_primary/dt
V2/V1 = n
```

| Item | Specification |
|---|---|
| Match ratio | within ×3 of unity for standard designs |
| Operational floor | secondary at least 3.9 `V_c` |
| Maximum ratio | `n ≤ V1/3.9` |
| Direction | primary domain at or above secondary domain |

**Failure signatures.**

- Perfect content match with no modulation: nothing transfers.
- Excessive ratio: the signal is beautifully matched and nobody can enact it.
- Ascending secondary: relabeling a lower-domain output as higher authority.
- Coupling inferred from simultaneous motion: correlation substituted for a
  measured mutual path.

**Proof load.** Hold the primary steady; the secondary must fall to zero. Apply
a known ramp and compare the secondary with `M·di/dt`. Verify domain direction
before energizing the output.

---

### C.10 Fuse — irreversible path state

**CAS role.** A fuse makes a stop structural.

```cas
fuse f1: Fuse<
    path=enforcement,
    threshold=0.90,
    action=permanent_block
>;
```

| Item | Specification |
|---|---|
| Standard threshold | 0.85–0.95; book default 0.90 |
| Action | `permanent_block` where irreversibility is claimed |
| Reachability rule | threshold must lie within the monitored node's reachable range |

**Failure signatures.**

- Threshold above the node's saturation ceiling: fuse can never trip.
- Fuse placed on refusal instead of enforcement: tripping cuts the objection
  and fails open.
- Warning action used where a latch was promised: prose without structure.
- Reset path hidden in an operational control: “permanent” until inconvenient.

**Proof load.** Drive the monitored node through its threshold under an isolated
test revision. Confirm the enforcement path—not the detector—becomes
permanently blocked. A fuse never observed to trip is untested, not proven.

---

### C.11 Oscillator — periodic Drive

**CAS role.** An oscillator implements the rate-and-pattern requirement of
`^7` Rhythm.

```cas
oscillator osc1: Oscillator<
    out=clock,
    period=7.0,
    duty=0.20,
    sustain=270.0
>;
```

| Item | Specification |
|---|---|
| Period | `T ≤ τ_leak/3` |
| Duty | 0.10–0.25 |
| Sustain | ≥ 3 × `τ_leak` |

**Failure signatures.**

- `T ≥ τ_leak`: large ripple; no stable plateau.
- Duty ≥ 0.6: effectively DC, with little impression contrast.
- External clock stopped and cadence disappears: rented rhythm, not entrainment.
- More frequency added to an empty pulse: schedule intensified without charge.

**Proof load.** Verify period and duty, then stop the source after the declared
sustain interval. Continued cadence is the decisive reading.

---

### C.12 Filters — selective destruction

| Filter | Passes | Destroys | Standard limit |
|---|---|---|---|
| Low-pass | sustained trend | spike / rapid variation | O→P feedback `τ` from 21 days (adept) to 6 months (novice), absolute floor 1 week |
| High-pass | change / edge | level / baseline | detection only on safety-sensitive paths |
| Notch | frequencies outside one band | selected recurrence | `Q ≥ 3.0` |

```cas
filter lp1: LowPass< in=outcome, out=trend, tau=21.0 >;
```

**Failure signatures.**

- High-pass on the O→P path: the one event the low-pass should kill is passed.
- Low-pass in hours: no constitutional filter remains.
- Notch with `Q < 3`: broad decomposition loss described as narrow.
- Notch aimed at principled `^3`: the refusal cadence is deliberately erased.

**Proof load.** Inject a step, a spike, and a sinusoid at the target recurrence.
Record what each filter destroys. A response plot without the rejected input
shown beside it is half a datasheet.

---

### C.13 Differential Comparator — matched-bias judgment

**CAS role.** A comparator reads a difference only after common framing has
been rejected.

| Item | Specification |
|---|---|
| CMRR on guard path | ≥ 1000 |
| Open-loop gain | finite, 100–1000 |
| Input matching | identical Domain, Drive, Register, and bias substrate; only the compared Noetic term may differ |

**Failure signatures.**

- Inputs on different substrates: permanent offset reported as a finding.
- CMRR raised by gain alone: larger answer, no better discrimination.
- Infinite gain: rejected idealization; rail clips first.
- Neutral input produces a verdict: mismatch, not insight.

**Proof load.** Tie both inputs to a neutral, common source. Output must sit near
zero. Apply equal common-mode motion and verify rejection before applying the
differential signal.

---

### C.14 Universal bring-up order

For a board containing several component classes:

1. **Power off:** validate syntax, literal axes, domain directions, parameter
   identities, threshold reachability, and named emergent results for every
   `×`.
2. **Guards only:** energize thermistors, refusal CJTs, comparators, and fuses.
3. **Storage:** verify rail, leakage, derating, and cell isolation.
4. **Timing:** verify oscillator, ramp, and filter behavior with signal stages
   disconnected.
5. **Signal chain:** add one CJT or passive stage at a time, probing upstream to
   downstream.
6. **Feedback last:** apply a spike and a sustained proof load before closing
   the return path.
7. **Destructive proof in an isolated revision:** trip the fuse and retain the
   artifact showing which path stopped.

If a later step changes an earlier reading, return to the earlier step. A
component that passes alone but fails when connected has not passed its board
test.
