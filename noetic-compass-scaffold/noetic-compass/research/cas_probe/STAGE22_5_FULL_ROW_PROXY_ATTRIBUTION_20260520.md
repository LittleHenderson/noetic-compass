# Stage 22.5 Full-Row Proxy Attribution

**Status:** `STAGE22_5_FULL_ROW_PROXY_ATTRIBUTION_COMPLETE`

Source product status: `NULL`
Source diagnostic status: `STAGE22_4_DIAGNOSTIC_ROWS_EMITTED`

## Headline

| Metric | Value |
|---|---:|
| Total rows | `4704` |
| RPM proxy measurable rows | `4142` |
| RPM proxy measurable rate | `0.881` |
| Lacunarity proxy measurable rows | `4704` |
| Lacunarity proxy measurable rate | `1.000` |
| Inversion numeric measured rows | `0` |

## Per Model

### OLMo-1B (`olmo1b`)

- Row parity: `True`
- Accepted / suppressed: `1687` / `665`
- RPM measurable: `2081` rows
- Lacunarity measurable: `2352` rows
- Inversion measured: `0` rows

Stage counts:

| Stage | Rows |
|---|---:|
| `accepted` | `1687` |
| `drive_ensemble` | `28` |
| `factor_consistency` | `143` |
| `foundation_ensemble` | `226` |
| `register_ensemble` | `17` |
| `trace_stability` | `251` |

RPM proxy decisions:

| Decision | Rows |
|---|---:|
| `allow` | `1938` |
| `constrain` | `271` |
| `suppress` | `143` |

Lacunarity proxy decisions:

| Decision | Rows |
|---|---:|
| `allow` | `1036` |
| `caveat` | `986` |
| `constrain` | `324` |
| `suppress` | `6` |

### Qwen2.5-1.5B (`qwen15b`)

- Row parity: `True`
- Accepted / suppressed: `1754` / `598`
- RPM measurable: `2061` rows
- Lacunarity measurable: `2352` rows
- Inversion measured: `0` rows

Stage counts:

| Stage | Rows |
|---|---:|
| `accepted` | `1754` |
| `drive_ensemble` | `22` |
| `factor_consistency` | `115` |
| `foundation_ensemble` | `238` |
| `register_ensemble` | `31` |
| `trace_stability` | `192` |

RPM proxy decisions:

| Decision | Rows |
|---|---:|
| `allow` | `1946` |
| `constrain` | `291` |
| `suppress` | `115` |

Lacunarity proxy decisions:

| Decision | Rows |
|---|---:|
| `allow` | `941` |
| `caveat` | `933` |
| `constrain` | `426` |
| `suppress` | `52` |

## Boundary

Stage 22.5 attributes runtime proxy diagnostics only. It does not claim neural RPM, neural lacunarity-head, or numeric inversion-scan attribution.
