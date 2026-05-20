# Stage 22.6 Inversion Proxy Attribution

**Status:** `STAGE22_6_INVERSION_PROXY_ATTRIBUTION_COMPLETE`

Source product status: `NULL`
Source diagnostic status: `STAGE22_4_DIAGNOSTIC_ROWS_EMITTED`

## Headline

| Metric | Value |
|---|---:|
| Total rows | `4704` |
| Numeric inversion proxy rows | `4704` |
| Numeric inversion proxy rate | `1.000` |

## Per Model

### OLMo-1B (`olmo1b`)

- Numeric measured rows: `2352` / `2352`
- Accepted / suppressed: `1687` / `665`

Decision counts:

| Decision | Rows |
|---|---:|
| `allow` | `1035` |
| `constrain` | `713` |
| `suppress` | `604` |

Axis mean scores:

| Axis | Mean risk |
|---|---:|
| `N` | `0.184` |
| `W` | `0.062` |
| `F` | `0.096` |
| `E` | `0.174` |
| `S` | `0.030` |
| `A` | `0.118` |
| `P` | `0.111` |

### Qwen2.5-1.5B (`qwen15b`)

- Numeric measured rows: `2352` / `2352`
- Accepted / suppressed: `1754` / `598`

Decision counts:

| Decision | Rows |
|---|---:|
| `allow` | `940` |
| `constrain` | `590` |
| `suppress` | `822` |

Axis mean scores:

| Axis | Mean risk |
|---|---:|
| `N` | `0.180` |
| `W` | `0.134` |
| `F` | `0.092` |
| `E` | `0.217` |
| `S` | `0.048` |
| `A` | `0.111` |
| `P` | `0.130` |

## Boundary

Stage 22.6 closes numeric inversion proxy attribution for the Stage 22.4 row contract. It does not claim a full semantic inversion theorem; scores are runtime structural proxies derived without gold labels.
