# Scoped Atlas browser checks

These checks open local, offline HTML in an owned headless Chromium process. They do not start or change the native reasoning runtime. The Chrome debugging connection is local loopback traffic; page HTTP/HTTPS requests are counted separately and must remain zero.

Run from the inner project root, using a new output directory for each attempt:

```powershell
python records/rpa_scoped_001/browser_draft_001/check_documents.py records/rpa_scoped_001/development_001 records/rpa_scoped_001/browser_draft_001/new_attempt
```

`check_documents.py` binds the input documents, renderer, adapter, and three helper sources before the run and verifies their bytes again at completion. It renders each validated document, calls `scoped_browser_helper.py`, and compares the observed browser results against the Python scoped-navigation API and the validated source evidence catalog.

`check_scoped_browser.mjs` exercises every reachable declared scope at desktop 1440×1100 and mobile 390×844. It inspects every direct child, checks eight-child pages in both directions, enters every non-leaf through both the selector and the petal control, returns by the back button and breadcrumbs, and verifies that leaf entry is disabled. It checks fixed source/current identities after interactions, confirms returned inspection-state arrays are copies, and tests rejection of a leaf and an undeclared direct entry.

Every inspected node is compared to its supplied record in the browser, then its UTF-8 JSON hash is compared independently to the Python source. Evidence bodies remain exact text, including large integer digits. Their text hashes are compared to the reconstructed canonical catalog bodies. The receipt does not claim a new execution, learned rule, measured geometry, or external source authentication.

The per-page browser result retains scope paths, child pages, relationships, evidence identities and hashes, viewport bounds, font sizes, and fixed identities. Screenshots cover the loaded state and available program, bindings, and primitive-instruction scopes. A final receipt is produced only if all document checks pass and all bound inputs remain unchanged.

Preserved attempts:

- `renderer_initial.py.txt` and `initial_source.json`: the original renderer before CSS edits.
- `initial_smoke_001`: original renderer showed overlapping desktop cards, horizontal scrolling on desktop/mobile, and 13.33-pixel projection text. No source mutation or page network request was observed.
- `layout_002`: the refined renderer passed the initial layout probe and the complete checked-solution browser traversal.
- `all_pages_003`: the first batch helper stopped before a browser launched because a relative source path was compared against the absolute root; its original helper and failure note are retained.
- `all_pages_004`: complete batch using resolved paths, independent Python comparisons, and compact exact-content hashes.

The helper only closes its own Chrome process. Temporary profiles use a short name inside the declared `_scratch` directory to avoid Windows path-length failures. The source HTML is copied byte-for-byte to the owned profile and is checked again after browser closure.
