# Immutable v1 historical evidence boundary

Board-change v2 does not modify or absorb the v1 pilot. The controlling v1 result commit is:

`18be4f05b2cf06ffe461bf68b32c48fabfb6510b`  
`result(gate4): board-CHANGE 16-conversation PILOT RUN under A1 -- both claims VACUOUS`

The pilot's own recorded claim-bearing hashes were:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `PREREG_BOARD_CHANGE_V1.md` | 65,506 | `7f5ae357c803d201f1622cec413f0af0bf5a76b2ed9c3a272340cb468db6b2a0` |
| `board_change_test.py` | 113,668 | `240916387bb45bdbec9d378caba70001e913a7ec950057accba1d4b26ba6cd99` |
| `board_change_seeds_blind.json` | 5,068 | `c6b3455613bcfc11334d5f8eb5cd11f0bd7e178bc75f1d0e16906567562613fb` |
| `conversations_change_pilot.jsonl` | 1,134,319 | `f68a9c126e1630f38a7a49f8aa1651882ceb63661ccd6144b1417d7e5e011c7d` |
| `label_calls_change_pilot.jsonl` | 77,033 | `1fcf701c35f076998b39ea4140b16de8ed9488f95247f7918c66924fec54e259` |
| `batch_meta_change_pilot.jsonl` | 1,678 | `8d67c4a21894896643a22ab68948c0beab3e0e06116b48d4f32c8eb2cb6f1727` |
| `board_change_report_pilot.json` | 2,321,795 | `ae19db5154b2b2ac094c99823793e255f500987925308ef50612174c7e6b0962` |
| `board_change_hashes_pilot.json` | 317 | `aafe8c51ef370e9677f18f6a82c4cf49d97ea514604a47762debbfb466650010` |
| `board_change_gate0_pilot.json` | 3,700 | `6b7991899cef085d870adfdbfeb8f086f70d80b8a2276728a4e2a4c719829e58` |
| `board_change_pilot_size_pilot.json` | 573 | `02a60ee692fde94918f154e5ef075a02e625a411413560bcbb83004646918b25` |

## Honest v1 result

On the exact 16-conversation, Stratum-N-only, deliberately enriched and scripted pilot:

- 138 pairs were analysable and 26 were labelled `CHANGE`;
- the observed model-initiated change rate was `0.1884`, producing the prospective sizing
  result `K_neutral=72`;
- T-BOARD Fleiss κ was `0.3732`, T-CHANGE κ was `0.2853`, and T-USER κ was `-0.0410`;
- B0 occupied 115 of 157 consensus board labels (`0.7325`), above the frozen `0.40`
  ceiling; and
- Gate 0 failed, so both claims were `VACUOUS`, not accepted or rejected.

The pilot had no Stratum S, so the T-USER positive control was uncomputable. Its negative
result is useful historical evidence about that exact fixture. It does not establish that
the taxonomy fails on natural conversation, that v1 is universally dead, or that more data
cannot change a statistic.

V2 uses only the prospective sizing decision. It does not reuse v1 conversations, labels,
or seed prompts in its claim-bearing result.

`v1_seed_fingerprints.json` preserves 80 exact and 80 normalized prompt fingerprints: 44
seeds from `board_change_seeds_blind.json` and 36 historical prompts from
`gen_real_outputs.py::PROMPTS`. Normalization is NFKC, Unicode-whitespace collapse/trim,
casefold, UTF-8, then SHA-256. The source-result commit and source blob hashes are recorded
in that bank; v2 rejects either exact or normalized reuse.
