# Triad adapter results — `helm_triad.py` (2026-10-18 PDT, laptop MSI, 0 USD)

**Status: `ENGINEERED-NOT-VALIDATED`, ceiling `SYNTHETIC_ONLY`.** These are code tests on planted cases. They show the wrapper does what the owner's rulings say. They do not show that real ingredients, minds or models carry a Purpose / Wisdom / Power triad.

## What was built, in plain words

- A new module, `helm_triad.py`. It wraps HELM's one licensed brain (`helm_brain_canonical.CanonicalRecipeBrain`) without editing it. The sealed package and `helm_brain_canonical.py` are untouched (tested). `helm_end_to_end_loop.py` and `helm_chat.py` are untouched (another builder owns them; tested with `git status`).
- Each ingredient can carry three faces: Purpose, Wisdom, Power. Each face uses the owner's one scale: Rising 1/4, Peak 1, Waning 1/2, Absent 0.
- The lowest face sets how much of the ingredient counts: `x_eff = min(Purpose, Wisdom, Power) × stock`, in exact fractions (owner ruling "min"). The brain answers on `x_eff` exactly as it answers today.
- The answer names the ingredient that runs out first (the brain's), and the face to blame: the **earliest** face not at Peak, in the order Purpose, Wisdom, Power (owner ruling "earliest"). The smallest face is reported beside it and never decides.
- The whole recipe can carry one Purpose (the RPM Gate's door question). Absent → UNDETERMINED, and the gate needs "the Purpose of Ω_X" (ask; never guess). Rising or Waning → the expected yield is that fraction of the brain's yield (Clarification 9 efficiency).
- Wisdom follows the owner's rule C: it never drifts down. It may fall only through a named event with evidence: STORAGE_FAULT, CORRECTION or UNEXPLAINED_YIELD. A drop with no event is refused and logged.
- Every face write is written, read back and receipted (the η∘ε check). Receipts are kept apart from the records. On reload, a record that does not match its receipt is a STORAGE_FAULT: its value is not taken, and answers that need it are UNDETERMINED until the face is stated again.
- A witnessed batch is converted before the sealed writer sees it: the writer gets the effective stock, so requirements are learned per effective unit.
- **Default OFF.** `TriadBrain(brain)` passes every call straight through. `enabled=True` turns it on.
- **Nothing is learned. Learned parameters: 0.** Stored values are stated inputs, each with a named source and evidence digest. Ceiling on the live brain: 8 ingredients × 3 faces + 4 recipe Purposes = **28** stored values. The `__main__` self-report prints `learned_parameters 0, stored_values 0, stored_value_ceiling 28` on an empty table; test_14 prints `stored_values 3` after one ingredient's three faces are stated.

## Test results (recorded output: `docs/working/traces/TEST_OUTPUT_TRIAD_ADAPTER_20261018.txt`)

`python test_helm_triad.py` → **15 / 15 OK** (0.485 s on the first run; the recorded run is the second, after closing two file handles that raised ResourceWarnings; no assertion changed).

| Check | Exact count |
|---|---|
| Default OFF: record identical to the brain's own | **100 / 100** |
| Triad ON, every face Peak (once unstated, once stated Peak): status, label, gate, yield and limiting ingredient identical to the brain's | **400 / 400** (8 rows UNDETERMINED = 4 stocks × 2 tables, exactly where the brain itself says UNDETERMINED) |
| Planted starved face, decoy stock (the starved ingredient has the most raw stock): right ingredient | **120 / 120** |
| Same rows: right face (earliest rule) | **120 / 120** |
| Recipe Purpose Absent → UNDETERMINED, gate `PURPOSE_ABSENT`; Waning → yield 3/2 of Y_T 3; Rising → 3/4 | pass |
| Worked example: Flour (Peak, Peak, Waning) → 3/2 loaves, Flour, face Power; Water (Waning, Rising, Peak) → 1 loaf, Water, face blamed **Purpose**, smallest face **Wisdom** | pass |
| Wisdom drop with no event: refused (`WISDOM_DROP_NEEDS_EVENT`), logged, value kept; an event with empty evidence also refused; Power drops freely | pass (2 refusals logged) |
| Wisdom drop with STORAGE_FAULT evidence naming this record's receipt: accepted; evidence naming a receipt the table never wrote: refused | pass |
| UNEXPLAINED_YIELD computed from the brain's own learned requirement: accepted when Purpose and Power are stated and cannot explain it; refused when Power explains it, or when Purpose and Power are not stated | pass |
| CORRECTION: refused without a statement digest; accepted with source and digest | pass |
| η∘ε read-back receipts | **52 / 52** writes passed; 4 bad writes refused and wrote nothing; 28 stored values = the ceiling |
| Reload: clean → 0 events, same snapshot; one tampered Wisdom record → 1 STORAGE_FAULT, value not taken, answer UNDETERMINED (`TRIAD_FACE_UNKNOWN`), then re-stated → answer back | pass |
| An Absent face → the brain's own gate G2 (yield 0) → UNDETERMINED, and the receipt names the face (`zeroed_by: Yeast → POWER`) | pass |
| Witness converted: 12 Flour at Power Waning → the writer sees 6 → requirement 2; recipe Purpose Absent with something made → `TRIAD_CONTRADICTION`; replay on a fresh brain admits the same row | pass |
| 3-valued sums: RIGHT 80 + WRONG 1 + UNDETERMINED 1 = 82 rows (the 1 WRONG and 1 UNDETERMINED are two hand-made rows that check the rule itself) | pass |
| Learned parameters / stored values / ceiling | **0 / 3 / 28** |
| Sealed package freeze sha256 = `8c55c4136e1b…`; `helm_brain_canonical.py`, `helm_end_to_end_loop.py`, `helm_chat.py` unmodified | pass |

## Existing suites, same worktree (nothing they test was changed)

- `python -m unittest test_helm_end_to_end_loop.py` → **18 OK**
- `python -m unittest test_helm_english_in.py` → **31 OK**
- `python -m unittest test_helm_voice.py` → **22 OK**
- `python -m pytest -q test_helm_chat_nuance.py` → **5 passed**

## What is not done (open)

- The triad is **not wired into the live loop** (`helm_end_to_end_loop.py` belongs to the English-in builder today). No live end-to-end trace with the triad exists yet.
- No English reader states faces yet. Faces are set through `TriadTable.set_face` with a named source.
- Faces are stored per ingredient (coordinator choice). Reading them from the 28 drive cells or the 22 pathways is NOT built (owner question Q3 still open).
- Book ladders ("100%+" mastery) are not carried; the one scale tops out at Peak.

## Files

`helm_triad.py` (sha256 `0d9d0bdaf3ba594e49c72c81f8f2a5749317cee1611906d8b847f8db6c00db1e`), `test_helm_triad.py` (sha256 `15cb6ad25f0243a1cd7fbd492d144ed792402845e3b4e5c3a922d34d0cc3bbd2`), `docs/working/traces/TEST_OUTPUT_TRIAD_ADAPTER_20261018.txt` (sha256 `de41e28d8a1389ba12b41f114dc1503b70ae0d316e2491dbf3dec81a9cb283e6`). Design: `Documents/Codex/2026-10-18/dwp_design_v0_2/`. Wisdom rule evidence: DWP-T2, `Documents/Codex/2026-10-18/dwp_t2/RESULTS.md` (`C_EARNED_KEEP`, spec sheet §7.61).
