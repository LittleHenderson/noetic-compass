# TKS v7.4 Gate 1 theorem/corrigendum lane

Status: `INTERNAL AUDIT / OPEN / NOT FROZEN`

This directory binds a reproducible theorem-surface inventory and a manually
adjudicated load-bearing corrigendum to the registered TKS v7.4 sources. It does
not claim that all proofs in the 539-page rendering have been checked.

The lane has two distinct completeness boundaries:

1. `TKS_V74_SURFACE_INVENTORY_v0.1.json` is complete for declarations that the
   stated regular expression detects in the registered integrated text. It
   records counts and a sequence digest, not a claim that every prose claim was
   detected or proved.
2. `TKS_V74_CORRIGENDUM_v0.1.json` is an item-level adjudication of the
   load-bearing clusters identified by the registered correction overlays and
   the Project Coherence mathematical red team. Other declarations remain
   `OPEN` by default.

Authority rules:

- The registered integrated text is the line-addressed semantic source.
- The owner-supplied 539-page PDF is the citation rendering; PDF page numbers
  in the corrigendum are physical pages, counted from one.
- The master TeX is a registered wrapper. Its nine present `\input` modules are
  hashed in the surface inventory as unregistered dependency context; they do
  not silently become separate semantic authorities.
- The three correction PDFs outrank blanket inheritance statements only in
  their stated correction scopes.
- `VERIFIED` means verified only at the narrow mathematical boundary stated in
  the record. It is not proof-assistant certification or external peer review.
- Every record is `NOT LICENSED`; this lane changes no empirical, product, or
  publication claim status.

Run the verifier from the repository root:

```powershell
python scripts/verify_project_coherence_v74.py
```
