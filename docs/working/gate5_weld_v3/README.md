# WELD v3: sealed, fixed-pipeline preregistration scaffold

Status: `ENGINEERED / NOT_RUN / NOT_VALIDATED`

WELD v3 is an offline control-plane successor to WELD v2. It does not call a
provider or a model, and it does not contain a result. Its purpose is to make a
future result harder to manufacture accidentally:

* every public case is sent to the same executable with the same command,
  schema, and ordered pipeline;
* the actor phase receives only public cases and a domain-separated,
  independently salted HMAC-SHA-256 commitment to the truth;
* adjudication is impossible until an external custodian has anchored the
  exact actor-receipt hash and invocation count, then released the committed
  high-entropy HMAC key after that seal;
* a matched control receives its own expected outcome and can independently
  fail the pair and the overall verdict;
* Python compares closed decision enums only. All numerical decision rules
  must live in the pinned Rust executable;
* the executable, runtime version evidence, Rust crate version, `Cargo.toml`,
  `Cargo.lock`, and scanner source are bound by absolute path, byte count, and
  SHA-256 before the actor phase; production binding also parses both Cargo
  files and requires the executable's JSON version probe to repeat the exact
  source identities;
* J1, J2, and Stage 5 have typed adapter contracts, all explicitly `NOT_RUN`.

The protocol is intentionally inert. A production freeze cannot use the
checked-in templates. A custodian must first build a native Rust executable
that implements the adapter protocol, materialize an exact binding, prepare
opaque public cases, generate independent 256-bit-or-greater salt and HMAC key
material, anchor the commitment evidence outside this tree, and keep truth and
key off the actor host. After the actor finishes, the custodian must externally
anchor the actor receipt before releasing either truth or key.

This revision validates the linkage of mock custody records but has no trusted
external-anchor signature verifier. It therefore rejects every
`PRODUCTION_RUST` adjudication even if locally authored files claim external
custody. A new frozen revision must add and test that verifier before any
production verdict can exist.

## Directory map

* `WELD_V3_PROTOCOL.md` — normative design and claim boundary.
* `WELD_V2_AUDIT.md` — line-grounded adversarial audit that motivates v3.
* `protocol/protocol.json` — machine-readable fixed pipeline.
* `protocol/runtime_binding.template.json` — deliberately unbound production
  template.
* `protocol/truth_commitment.template.json` — deliberately uncommitted truth
  template.
* `protocol/external_commitment_evidence.template.json` — pre-freeze external
  custodian receipt template.
* `protocol/actor_receipt_seal.template.json` — post-actor, pre-truth external
  seal template.
* `protocol/custodian_release.template.json` — post-seal truth-key release
  template; it must never enter the preregistration or result roots.
* `adapter_contracts/model_adapter_contracts.json` — J1/J2/Stage-5 bridge
  contracts, all `NOT_RUN`.
* `src/weld_v3/` — standard-library-only freeze, actor, and adjudication code.
* `tests/test_weld_v3.py` — temporary-directory mock protocol tests. Mocks do
  not test CAS efficacy.
* `evidence/README.md` — exact evidence expected from a future real run.

## Current Rust source observation, not a runtime binding

The isolated checkout at commit `34442035c69e7feccd6c3b67447568776fe3528f`
contains `cas-engine` version `0.1.1`:

| Artifact | SHA-256 |
|---|---|
| `noetic-compass-scaffold/noetic-compass/cas-engine/Cargo.toml` | `883b74b40e342a6c680a2fd00bc8955f282fd82e58974b38b39a81c210ec119e` |
| `noetic-compass-scaffold/noetic-compass/cas-engine/Cargo.lock` | `eab516c79e212cccb08ba2798d685d57c260b197b019e17481f1da0251dfcd0a` |
| `noetic-compass-scaffold/noetic-compass/cas-engine/src/inversions/mod.rs` | `bae6968135e1d3ddc8350859c556ff69af0e5f7d866f0243fcb4a87284c56f70` |
| `noetic-compass-scaffold/noetic-compass/cas-engine/src/python_bindings.rs` | `e5077e8f8cfc5669888fda996ea540d84df55ef0302b64b48fcf8f7944dc9220` |

This is not yet runnable WELD-v3 evidence. The installed editable Python
package reports version `0.1.0`, has no module `__version__`, points to the
older OneDrive checkout, and loads a `.pyd` with SHA-256
`b7c60b9b6bd70e9e24acce734cf71ef100c90da8952d930731ce7d06a379ee0c`.
That mismatch is one reason v3 refuses ambient imports.

## Mock verification

From this directory:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m unittest discover -s .\tests -v
```

The 21 tests create their adapter, preregistration bundle, external mock
custody records, truth commitment, actor receipt, and adjudication in a
temporary directory. They also attack zero-invocation receipt fabrication,
post-seal mutation, low-diversity key material, Python-as-Rust relabelling,
runtime-attestation substitution, nested roots, shared case directories, and
information-matching gaps. Nothing in this checked-in directory is a result or
a production binding, and the mock custody records are not real external
evidence.
