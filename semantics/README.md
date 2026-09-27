# Q1-Claude semantics records

Lease: `semantics/` (coordination/FILE_LEASES.md at 35236511). Author: Q1-Claude.

| File | Content |
| --- | --- |
| `instruction_semantics.json` | The four public fixture instructions, their arithmetic, reversible gate realisation, inverse and bit ordering. Derived from `fixtures/public/q1-mod4.json`; synthetic, not CAS-native. |
| `register_layout.md` | Pinned qubit allocation, index convention and the decoding order used by the compiler. |
| `cas_rpm_rpa_mapping.md` | Mapping of problem / candidate / verifier output to the only admitted host interface (`ReturnAddress` in `helm_quantum/contracts.py`) and the explicit UNSUPPORTED list pending approved source exports. |

Nothing in this directory grants execution or retention authority.
