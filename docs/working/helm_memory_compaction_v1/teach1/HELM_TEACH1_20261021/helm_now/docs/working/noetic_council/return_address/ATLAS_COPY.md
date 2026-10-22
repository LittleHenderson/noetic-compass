# ATLAS_COPY — the second hop of a read-only copy

This folder holds a copy of the CAS-RPU Recursive Possibility Atlas model, taken **read only**, so
that a return address can name a saved snapshot with a digest the atlas model itself computed, and so
that glue-back can be answered by the model's own `compatibility()` and `certify_overlap()`.

Nothing in this folder was written by this build. Nothing in either source folder was modified.

## The two hops

| hop | from | to | how |
|---|---|---|---|
| 1 | branch `codex/helm-rpa-recorded-run-20260922`, commit `eb9985566bd11a89f485d627186ef0efa7177f02`, inside `C:\Users\wakil\OneDrive\Desktop\tksCAS` | `C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v3\real_atlas\` | one `git show <commit>:<path>` per file, byte for byte; recorded in that folder's `PROVENANCE.md` |
| 2 | `continuity_build_v3\real_atlas\` | `return_address\real_atlas\` (this folder) | `Copy-Item -Recurse`, byte for byte |

`PROVENANCE.md` came across unchanged in hop 2, so it is the record of hop 1 and it mentions
`atlas_adapter.verify_real_model()` — a function of the sibling package, not of this one. It is left
exactly as it was: editing a provenance record to match a new home would defeat the point of it. This
file is the record of hop 2.

## Files, sizes and sha256 (measured on the bytes on disk, after hop 2)

| File here | Bytes | sha256 |
|---|---|---|
| `rpa_model.py` | 24726 | `323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01` |
| `canonical.py` | 1696 | `424323335452fecd26cd6659136475c0fd19bda695ab07811d34d1734564877a` |
| `model.py` | 58492 | `aafa82f0267d0e741a90ba095d939da47401be577b5682832608a6845be54766` |
| `rpa_ohm_atlas.py` | 30449 | `6aa030651278f217965a788427d55d3f475bb666b366a8095d6a5fb05be9694f` |
| `CAS_RPA_OHM_ATLAS_20260922.md` | 8882 | `516aa180212643c97da6241dfe618548d71be422e3d966d747cad812c95acc34` |
| `VERIFICATION.md` | 4917 | `5eec0108af1408d91c44063fb4950723c52e3170856b6947bfad77bef69602d0` |

These are the same six numbers as `PROVENANCE.md`, which is the point: hop 2 changed no byte.

## What is imported, and what is only carried

- **Imported:** `real_atlas.rpa_model` (for `AtlasSnapshot`, `compatibility`, `certify_overlap` and
  the typed records this build reads) and `real_atlas.model` (for its `ContractError`).
- **Carried unchanged, not imported:** `rpa_ohm_atlas.py` needs `rpa_coordinates.py`, which is not
  copied, so it is reference material; the two Markdown files are the recorded run's documentation.
- `real_atlas/__init__.py` is deliberately absent, so Python treats the folder as a namespace package
  and the model's own relative imports resolve inside it.

## The rule these files are under

Read-only inputs. Nothing in this build writes to, patches, subclasses around, or re-hashes them into
a different shape. They are imported, called, and hashed; `atlas_binding.verify_real_model()` fails
the run rather than quietly using a changed file.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NO CIRCUIT USES THIS YET.
