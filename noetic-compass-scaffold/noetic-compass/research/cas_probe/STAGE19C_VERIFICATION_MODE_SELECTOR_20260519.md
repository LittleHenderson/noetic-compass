# Stage 19C Verification Mode Selector

**Status:** `MODE_SELECTOR_READY`

## Headline

| Mode | Cross-arch status | Product use |
|---|---|---|
| `HIGH_PRECISION` | `MODE_SUPPORTED_CROSS_ARCH` | Regulator, legal, safety, and high-trust review where suppression is preferred over a wrong accepted answer. |
| `BALANCED` | `MODE_SUPPORTED_CROSS_ARCH` | Normal customer audit flow where throughput matters but factor conflicts should still be suppressed. |
| `MAX_COVERAGE_TRIAGE` | `MODE_SUPPORTED_CROSS_ARCH` | Exploratory triage and batch review queues where human review remains expected. |

## Per-Model Mode Table

### `HIGH_PRECISION`

Highest precision; lower coverage is expected.

| Model | Meets target | Accepted acc | Coverage | Silent error | Suppressed |
|---|---:|---:|---:|---:|---:|
| OLMo-1B | `true` | `0.9816` | `0.7173` | `0.0184` | `0.2827` |
| Qwen2.5-1.5B | `true` | `0.9949` | `0.7457` | `0.0051` | `0.2543` |

### `BALANCED`

Coverage restored above 80% with lower precision than HIGH_PRECISION.

| Model | Meets target | Accepted acc | Coverage | Silent error | Suppressed |
|---|---:|---:|---:|---:|---:|
| OLMo-1B | `true` | `0.9422` | `0.8240` | `0.0578` | `0.1760` |
| Qwen2.5-1.5B | `true` | `0.9661` | `0.8274` | `0.0339` | `0.1726` |

### `MAX_COVERAGE_TRIAGE`

Triage mode only; not a licensed high-confidence claim mode.

| Model | Meets target | Accepted acc | Coverage | Silent error | Suppressed |
|---|---:|---:|---:|---:|---:|
| OLMo-1B | `true` | `0.8975` | `0.9039` | `0.1025` | `0.0961` |
| Qwen2.5-1.5B | `true` | `0.9281` | `0.8988` | `0.0719` | `0.1012` |

## Product Boundary

Users can choose the operating mode. They cannot choose away the tradeoff:

- `HIGH_PRECISION` gives the strongest accepted predictions and suppresses more.
- `BALANCED` is the default new-customer mode: it recovers coverage with lower accepted accuracy.
- `MAX_COVERAGE_TRIAGE` is for surfacing candidates, not final high-confidence claims.

Default mode: `BALANCED`.

BALANCED is the new-customer default because it restores the Stage 19B coverage floor while retaining factor-decomposition agreement. HIGH_PRECISION remains opt-in for regulator/legal workflows; MAX_COVERAGE_TRIAGE remains opt-in for human-review queues.

## Source Component Verification

Source review confirms `factor_consistent` means Foundation factor-decomposition agreement: the Stage 19B runner first requires 2-of-3 Foundation readout consensus, then separately requires Drive and Register readout consensus, recomposes Drive x Register into a 28-way Foundation label, and suppresses the row as `factor_conflicted` if the recomposed label does not match the Foundation consensus.

Gold labels are used only to score these mode profiles after the fact. Runtime mode selection uses the same non-oracle signals from Stage 19B.
