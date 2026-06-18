# PCBA Semantics Review Bundle

Generated: `2026-06-17T23:11:13.598616+00:00`
Scope: `production_pcba_component_syntax only`
Ready for human signature: `true`
Licensed: `false`

## Reviewed Artifacts

| Artifact | Exists | SHA-256 |
|---|---:|---|
| `docs\working\pcba_syntax_grammar_spec_20260617.md` | `true` | `7a903a6b41495953247b70cfea5eeb96097397ec9aa6305fe25180f4b078e5fc` |
| `cas-forex\cas_forex\pcba_syntax.py` | `true` | `c66fdc6cd979c636644563901938ade90bf4841bbaa67597697e899878c73735` |
| `cas-forex\cas_forex\pcba_compiler.py` | `true` | `2e4ef193182fbcf63a699a62332907ecbf9a148db0a3f65b3b14cbf90152360e` |

## Parser Cases

| Expression | Passed | Component |
|---|---:|---|
| `Resistor< ^8^C_{F2}|A, R=50 >` | `true` | `resistor` |
| `Capacitor< ^5^E_{F4}|f, C=100, leakage=0.01 >` | `true` | `capacitor` |
| `OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >` | `true` | `op_amp` |
| `Fuse< ^8^O_{F5}|E, threshold=0.9, action=permanent_block >` | `true` | `fuse` |
| `Trace< ^2^P -> ^2^C >` | `true` | `trace` |
| `Via< layer=P, to_layer=C, transition=^2^P->^2^C >` | `true` | `via` |

## Invalid Parser Cases

| Expression | Rejected | Error |
|---|---:|---|
| `UnknownPart< ^2^P|A >` | `true` | `Unknown PCBA component 'UnknownPart'` |
| `Resistor<>` | `true` | `1 validation error for PcbaComponentNode
  Value error, PCBA component body cannot be empty [type=value_error, input_value={'name': None, 'kind': <P...args': [], 'params': {}}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error` |
| `Resistor< ^8^C|A, R=-1 >` | `true` | `1 validation error for PcbaComponentNode
  Value error, Parameter 'R' must be non-negative [type=value_error, input_value={'name': None, 'kind': <P...'], 'params': {'R': -1}}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error` |
| `Resistor< ^8^C|A, R=nan >` | `true` | `Invalid non-finite value 'nan'` |
| `Fuse< ^8^O|E, threshold=2 >` | `true` | `1 validation error for PcbaComponentNode
  Value error, Parameter 'threshold' must be between 0 and 1 [type=value_error, input_value={'name': None, 'kind': <P...rams': {'threshold': 2}}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error` |
| `LogicGate< gate=XNOR, inputs=[a, b] >` | `true` | `1 validation error for PcbaComponentNode
  Value error, Unsupported logic gate [type=value_error, input_value={'name': None, 'kind': <P..., 'inputs': ['a', 'b']}}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error` |

## Compiler Cases

| Expression | Expected | Valid | Reason |
|---|---|---:|---|
| `Resistor< ^8^C_{F2}|A, R=50 >` | pass | `true` | Embedded CAS expressions compiled successfully. |
| `OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >` | pass | `true` | Embedded CAS expressions compiled successfully. |
| `Trace< ^2^P -> ^2^C >` | pass | `true` | Embedded CAS expressions compiled successfully. |
| `Via< layer=P, to_layer=C, transition=^2^P->^2^C >` | pass | `true` | Embedded CAS expressions compiled successfully. |
| `Resistor< ^2^Z_{F2}|A, R=50 >` | fail | `false` | One or more embedded CAS expressions failed compilation. |
| `Diode< ^P -> ^C >` | fail | `false` | No compiler-checkable CAS expressions found in PCBA component. |

## Claim Boundaries

- `production_pcba_component_syntax`: `OPEN`
- `compiler_enforced_safety_claim`: `NOT LICENSED`
- `prompt_injection_prevention_claim`: `NOT LICENSED`
- `broker_accept_creation`: `NOT LICENSED`

## Commands

- Finalize: `python scripts\finalize_pcba_authority_receipt.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"`
- Verify: `python scripts\verify_pcba_semantics_receipt.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"`

Ready for human semantics signature.
