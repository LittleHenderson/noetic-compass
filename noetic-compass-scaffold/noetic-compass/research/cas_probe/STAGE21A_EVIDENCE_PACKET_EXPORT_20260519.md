# Stage 21A EvidencePacket Export

Date: 2026-05-19

Status: `EVIDENCE_PACKET_EXPORT_READY`

## Boundary

Stage 21A exports canonical packet artifacts from locked Stage 19/20B reports. It is product packaging, not a new model run.

## Canonical Packets

| Trace ID | Model | Mode | Accepted | Readiness | JSON | Markdown |
|---|---|---:|---:|---:|---|---|
| stage21a_allow_qwen15b_000 | Qwen/Qwen2.5-1.5B | `BALANCED` | `True` | `allow` | `evidence_packets/stage21a_allow_qwen15b_000.json` | `evidence_packets/stage21a_allow_qwen15b_000.md` |
| stage21a_caveat_olmo1b_009 | allenai/OLMo-1B-hf | `BALANCED` | `True` | `caveat` | `evidence_packets/stage21a_caveat_olmo1b_009.json` | `evidence_packets/stage21a_caveat_olmo1b_009.md` |
| stage21a_suppress_olmo1b_054 | allenai/OLMo-1B-hf | `BALANCED` | `False` | `suppress` | `evidence_packets/stage21a_suppress_olmo1b_054.json` | `evidence_packets/stage21a_suppress_olmo1b_054.md` |
| stage21a_constrain_olmo1b_054 | allenai/OLMo-1B-hf | `MAX_COVERAGE_TRIAGE` | `False` | `constrain` | `evidence_packets/stage21a_constrain_olmo1b_054.json` | `evidence_packets/stage21a_constrain_olmo1b_054.md` |

## Product Read

Stage 21A turns the report stack into the customer-facing artifact:
one packet per trace, each with provenance, readout, verification mode,
generation readiness, controls, conditioning metrics, caveats, and
rejected claims.
