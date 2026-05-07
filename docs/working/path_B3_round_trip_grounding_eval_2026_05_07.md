# Path B-3 round-trip grounding eval - 2026-05-07

## Verdict

CALIBRATED PASS for B-4 experimental wiring.

K=9 does not recover CAS axes from natural dialogue target replies at high
absolute rates, so absolute generated-reply recovery is not a fair gate.
The useful question is whether generated replies preserve the recoverable
signal present in target replies. On that calibrated comparison, generated
reply recovery is strong for register and drive in reply-only mode, strong
for register/domain/drive in prompt+reply mode, and weak only for reply-only
domain plus noetic. Noetic remains report-only for v0.

## Setup

- Samples: 72
- K=9 classifications: 288
- K=9 run dir: `noetic-compass-scaffold\noetic-compass\cas-native\training\runs\structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045`
- Runtime: 7.1s

## Generated vs target recovery

The key diagnostic is generated/target ratio. Target replies calibrate how
well K=9 can recover each axis from natural dialogue text at all.

### Reply-only

| Axis | Target | Generated | Generated/Target | Verdict |
|---|---:|---:|---:|---|
| register | 45.8% | 50.0% | 109.1% | strong |
| domain | 41.7% | 31.9% | 76.7% | gap |
| drive | 20.8% | 22.2% | 106.7% | strong |
| noetic | 8.3% | 4.2% | 50.0% | gap |

### Prompt + reply

| Axis | Target | Generated | Generated/Target | Verdict |
|---|---:|---:|---:|---|
| register | 41.7% | 47.2% | 113.3% | strong |
| domain | 33.3% | 33.3% | 100.0% | strong |
| drive | 20.8% | 20.8% | 100.0% | strong |
| noetic | 4.2% | 4.2% | 100.0% | strong |

## Per-register generated reply-only recovery

| Register | Register | Domain | Drive | Noetic |
|---|---:|---:|---:|---:|
| A | 0.0% | 11.1% | 33.3% | 0.0% |
| E | 11.1% | 27.8% | 33.3% | 0.0% |
| T | 88.9% | 27.8% | 16.7% | 16.7% |
| f | 100.0% | 61.1% | 5.6% | 0.0% |

## Gate

- Strong grounding: generated/target ratio >= 90%
- Acceptable grounding: generated/target ratio >= 80%
- Gap: generated/target ratio < 80%

Interpretation should prioritize register, domain, and drive. Noetic and
all-heads-style exact recovery are reported but should not block v0 alone.
