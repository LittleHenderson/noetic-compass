# PROVENANCE — the real atlas model, copied in read-only

This folder holds the CAS-RPU Recursive Possibility Atlas model that already existed in the
repository. Nothing here was written by this build. Every file below was copied byte for byte
out of one git commit, and the sha256 recorded next to it is the hash of the bytes now on disk.

## Where it came from

- Repository: `C:\Users\wakil\OneDrive\Desktop\tksCAS`
- Branch: `codex/helm-rpa-recorded-run-20260922`
- Commit: `eb9985566bd11a89f485d627186ef0efa7177f02`
- Extracted without switching branches, with one command per file:

```
git -C C:\Users\wakil\OneDrive\Desktop\tksCAS show ^<commit^>:"^<path^>" > ^<outfile^>
```

## Files, sizes and sha256 (measured on the bytes on disk)

| File here | Source path inside the commit | Bytes | sha256 |
|---|---|---|---|
| `rpa_model.py` | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/cncm/rpa_model.py` | 24726 | `323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01` |
| `canonical.py` | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/cncm/canonical.py` | 1696 | `424323335452fecd26cd6659136475c0fd19bda695ab07811d34d1734564877a` |
| `model.py` | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/cncm/model.py` | 58492 | `aafa82f0267d0e741a90ba095d939da47401be577b5682832608a6845be54766` |
| `rpa_ohm_atlas.py` | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/cncm/rpa_ohm_atlas.py` | 30449 | `6aa030651278f217965a788427d55d3f475bb666b366a8095d6a5fb05be9694f` |
| `CAS_RPA_OHM_ATLAS_20260922.md` | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/docs/CAS_RPA_OHM_ATLAS_20260922.md` | 8882 | `516aa180212643c97da6241dfe618548d71be422e3d966d747cad812c95acc34` |
| `VERIFICATION.md` | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/rpa_ohm_atlas_20260922/VERIFICATION.md` | 4917 | `5eec0108af1408d91c44063fb4950723c52e3170856b6947bfad77bef69602d0` |

`atlas_adapter.verify_real_model()` re-hashes these six files on every test run and refuses if
any byte changed. `atlas_adapter.REAL_MODEL_SHA256` holds the same six hashes.

## Why `model.py` is here

`rpa_model.py` does `from .model import ContractError`, so the real model's own exception class is
a hard dependency of the real model. `model.py` imports only the standard library and
`canonical.py`. No other file from `cncm/` is needed to import and use `rpa_model.py`.

## What was NOT copied, and why

- `cncm/__init__.py` is not copied, so Python treats `real_atlas` as a namespace package and the
  real model's relative imports (`from .canonical import ...`) resolve inside this folder only.
  Importing the real `cncm` package would pull in the whole 78-module package and its own
  dependencies; this build needs three of those modules and nothing else.
- `rpa_coordinates.py` is the one import `rpa_ohm_atlas.py` needs that is not in this folder, so
  `rpa_ohm_atlas.py` is copied as reference material and is **not imported** by this build. The
  adapter uses `rpa_model.py` directly.
- `records/rpa_ohm_atlas_20260922/demo/` and the PNG captures are not copied: they are the
  recorded run's evidence, not model code, and this build reads none of them.

## The rule these files are under

These are read-only inputs. Nothing in this build writes to, patches, subclasses around, or
re-hashes them into a different shape. They are imported, called, and hashed.

## Measured interface used by the adapter

Taken from the files above, not from a summary:

- `AtlasContext(context_id, model_version, observation_id, observation_time, record_version)`
- `AtlasNode(node_id, idea_id, label, context, status, fields, members, profile40,
  profile_basis, expansion_ref, kind, evidence_refs)` with `.view_key` and `.region_digest`
- `AtlasLink(link_id, source_id, target_id, relation, projection, action_id, evidence_refs,
  certificate_id, transition_status)`, `relation` typed by `LinkType`
- `OverlapCertificate`, `certify_overlap(nodes, witness_id=None)`
- `CompatibilityReport`, `compatibility(nodes)`
- `DeferredExpansion`, `ExpansionResult`, `AtlasSnapshot` with `.snapshot_digest`
- `validate_profile40(profile, basis)`, `NodeKind`, `NodeStatus`, `LinkType`
- Measured bounds in the file: `MAX_NODES = 512`, `MAX_LINKS = 2048`, `MAX_MEMBERS = 512`,
  `MAX_DEPTH = 32`, `MAX_ATLAS_BYTES = 8 * 1024 * 1024`, `MAX_FIELD_VALUE = 262144`
