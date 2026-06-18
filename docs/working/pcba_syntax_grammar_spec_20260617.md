# PCBA Component Syntax Grammar Spec

Date: 2026-06-17
Status: Draft research grammar, not approved production CAS compiler syntax

## Purpose

This spec captures the component syntax from the PCBA findings attachment as a research parser target. It is evidence and visualization support only.

## Generic Form

```text
Component< arg1, arg2, key=value, key2=[a, b, c] >
```

Named form:

```text
let limiter = Resistor< ^8^O_{F5}|E, R=75 >;
```

## Covered Components

- `Resistor`
- `Capacitor`
- `Inductor`
- `Diode`
- `Transformer`
- `OpAmp`
- `Oscillator`
- `LogicGate`
- `MUX`
- `DEMUX`
- `Regulator`
- `Fuse`
- `CircuitBreaker`
- `Trace`
- `Via`
- `Varactor`
- `Relay`
- `SchmittTrigger`
- `Photodiode`
- `CrystalOscillator`
- `ADC`
- `DAC`
- `BridgeRectifier`

## Claim Boundary

This grammar is not production compiler authority. It cannot create live trading permission, compiler-enforced safety claims, prompt-injection prevention claims, governance/regulatory proof, or broker `ACCEPT`.
