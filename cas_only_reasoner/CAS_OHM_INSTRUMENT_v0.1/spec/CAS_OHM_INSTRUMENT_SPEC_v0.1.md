# CAS-Ohm Instrumentation Panel v0.1

## Profile-Specific Measurement Under the Paper's Own Restrictions

**Status:** FROZEN. The panel is OPTIONAL instrumentation, never part of
the reasoning loop and never a truth source. Every restriction of the
CAS-Ohm 1.0 v0.2 paper is an executable rule here, not a disclaimer.

## 1. The restrictions, as rules

    R1  CAS-Ohm is NOT physical Ohm's law.
    R2  It is NOT an electrical implementation.
    R3  It is NOT a measure of attention.
    R4  It is NOT a causal law.
    R5  Series, parallel, and gain composition are capability-gated
        structural research calculations, not universal laws.
    R6  A residual can rank follow-up probes; it CANNOT identify a
        hidden cause, policy, bypass, or failure by sign alone.
    R7  No live calibration is admitted. Calibration and validation
        splits are DISJOINT and enforced as such.
    R8  History-dependent dynamics remain open.
    R9  Whether the model predicts anything is decided by controlled,
        independently audited experiments - nothing here preempts
        that answer.
    R10 The reasoning runtime must not depend on any CAS-Ohm quantity.

## 2. The measurement protocol

    MeasurementManifest {
        profile_id,
        calibration_indices, validation_indices   (disjoint, enforced),
        typed quantities: alpha dose, activation response,
        source label (v0.1: "synthetic_mock" - deterministic,
        no model was measured),
    }

## 3. ASOM: operating condition, not intelligence

ASOM classifies the local operating condition - Starved, Aligned,
Oversaturated, Misaligned - from the response REGION and the semantic
OUTCOME, classified independently. Active does not mean intelligent;
high gain does not mean correct; saturation does not mean expert; a
small residual does not prove good reasoning.

## 4. The report

Every instrument report prints R1-R10 verbatim, labels its source as
synthetic when it is, and states: no live calibration, no causal
claims, no attention measurement, controlled experiments pending.
