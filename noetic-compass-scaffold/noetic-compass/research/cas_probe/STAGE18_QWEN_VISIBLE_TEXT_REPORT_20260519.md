# Stage 18 Qwen Visible Text-Quality Judge

**Status:** `NULL_STAGE18_QWEN_VISIBLE_TEXT_SHIFT_NOT_ESTABLISHED`

## Gate Result

| Metric | Value | Gate |
|---|---:|---:|
| Drive judge test accuracy | `0.6679` | `>= 0.65` |
| Probe-readable minus partner-readable margin | `-0.1414` | `>= +0.10` |
| Probe-readable delta vs none | `0.0178` | `>= +0.05` |
| Probe > partner positive rows | `12 / 112` | `>= 65/112` |
| Probe > partner Wilcoxon p | `0.999759` | `< 0.05` |
| Probe raw delta vs none | `-0.1116` | `< +0.05` |

## Drive Judgment

| Condition | Target Pred Rate | Partner Pred Rate | Mean Target-Partner Prob | Delta vs None |
|---|---:|---:|---:|---:|
| none | 0.661 | 0.214 | 0.3700 | 0.0000 |
| gold_readable | 0.759 | 0.241 | 0.4066 | 0.0365 |
| probe_readable | 0.741 | 0.250 | 0.3879 | 0.0178 |
| partner_readable | 0.839 | 0.161 | 0.5293 | 0.1592 |
| probe_raw | 0.661 | 0.321 | 0.2584 | -0.1116 |

## Foundation Judgment

| Condition | Target Pred Rate | Partner Pred Rate | Mean Target-Partner Prob | Delta vs None |
|---|---:|---:|---:|---:|
| none | 0.518 | 0.161 | 0.1233 | 0.0000 |
| gold_readable | 0.705 | 0.223 | 0.1654 | 0.0421 |
| probe_readable | 0.696 | 0.223 | 0.1589 | 0.0356 |
| partner_readable | 0.795 | 0.134 | 0.2090 | 0.0857 |
| probe_raw | 0.562 | 0.277 | 0.1002 | -0.0231 |

## Boundary

Stage 18 does not establish visible text-quality shift. CPL2 likelihood remains the load-bearing eta-to-epsilon result.
