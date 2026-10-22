
## Amendment A-TEACH2-22 (2026-10-22 PDT) — FIX FIRST: two defects in HELM's cube answers found by builder practice round 3; the HELM cut moves to the fix commit; written before the fix

Status: appended after A-TEACH2-21 (`0aa9ced6…`); nothing above is edited. Only builder practice worlds have run.

**What practice round 3 showed (2 practice worlds, every unit exit 0; practice facts that decide nothing).**
1. Asked "What did I say about the buses on the Glenhollow line in January?" (a fact the person said they did not remember), every arm that answers from cubes or a table said "Glenhollow, buses line, September: nineteen": the answer matcher ignores months, so a question about one month took another month's fact. In CUBE_OSC this made U2 (a harm condition) false.
2. HG-H8 read false on the TABLE rival only: without a compactor HELM numbers lines by position, so once the budget is full every new line has the same number (helm_memory's pinned OFF rule, kept unchanged), and a table answer whose line was long dropped was still labelled EXACT.

**F1. The fix, in HELM's cube module only (`helm_cube_osc.py`, behind `HELM_CUBE_OSC`, default OFF; `helm_memory.py` and the OFF path are not touched).** (a) A question that names a month is answered only from a fact that holds that month (a branch whose second node is that month, or a table entry whose slot words hold it). (b) A table entry also keeps the person's line that wrote it; a table answer is EXACT only when a live line has that number and that text. Test first: `test_helm_cube_month_label.py` (4 tests; 3 fail on the old code). HELM's own suites must stay green.

**F2. The HELM cut** in the TEACH-2 package moves to the commit that holds the fix (recorded in `contract/HELM_CUT_TEACH2.json` and the seal record). The reader is unchanged; A-TEACH2-21 R1's harness-side source check stays as a second check.

**F3. Unchanged:** every threshold, arm, gate, mark, status word, label and the licence ceiling.
