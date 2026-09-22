# PCBA circuit and board reader — 2026-09-21

The lab now reads complete CCDL circuit/board documents and checks a bounded
set of structural rules. It reuses the recovered PCBA/CJT component parsers
through a strict adapter. The main CAS compiler, frozen engine, Q3 records,
and Q4 learning code are unchanged.

This closes the missing whole-document reader and named-connection checker
work item. It does not implement circuit execution, prove general circuit
stability, validate every book rule, or teach Helm to perform these checks.

## Run it

From this CNCM worktree's homebase (the directory containing **research**):

~~~powershell
& "C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe" research/helm_cas_expression_lab/pcba_check.py research/helm_cas_expression_lab/examples/pcba_named_feedback.ccdl
~~~

The CLI prints JSON. Exit 0 means the supported static checks passed.
Exit 2 means malformed input, a failed rule, an unsupported form, or an
unverified structural result. The current local interpreter is Python 3.12.10
with Pydantic 2.13.3. The adapter needs Pydantic 2; Python 3.14 on this machine
does not have it. Missing dependencies produce a failed report.

The Python entry point is **check_pcba_document(source)** in **pcba_check.py**.
It accepts Unicode text or UTF-8 bytes. Import it with the lab directory on
the Python import path.

## Read the four results separately

| Field | Meaning |
|---|---|
| parse_status | PASS, FAIL, or UNSUPPORTED for reading the complete document |
| structural_status | PASS, FAIL, UNVERIFIED, or NOT_RUN for the implemented checks |
| execution_status | NOT_IMPLEMENTED |
| helm_status | NOT_TRAINED |

**valid** is true only when both parsing and the implemented structural checks
pass. It does **not** mean full-book validity. Every report also says
**full_book_validation_status: UNVERIFIED** and
**engine_admissibility_status: NOT_RUN_OPERATOR_UNSPECIFIED**.
No operator is invented for an unannotated connection.

Diagnostics carry the original statement's line and column. The report keeps
the document, named symbols, full state metadata, component parameters,
resolved terminals, directed edges, and loop evidence. Exact decimal strings
are used for parameter comparisons and loop-gain proofs; numeric summaries
are not used for those decisions.

## Implemented

- One complete circuit or board, comments, input/output declarations,
  nodes, components, reusable let declarations, feedback, probes, layers,
  vias, transitions, series links, and simple static assertions.
- Two-pass resolution supports forward references. Duplicate names,
  unresolved terminals, layer-domain mismatches, component-prefix/type
  mismatches, incomplete state literals, and duplicate parameter aliases fail.
- Complete component checks for CJT, Resistor, Capacitor, Inductor, Diode,
  and Transformer. The cap prefix is accepted. Known additional component
  forms remain preserved but explicitly unverified.
- Exact Appendix C parameter ranges and CJT defaults. Bias must sit at or
  above the cause domain. A downward via may skip layers.
- Directed simple cycles retain parallel edges and use the whole path's gain
  product. CJT cause edges use beta; bias edges use gm, never beta as a substitute.
  A known complete path product >= 1 raises E-CJT-005.
- Unknown gain, passive influence on a loop, interacting loops, ambiguous
  inline net identity, and incomplete searches cannot produce a structural PASS.
- Bias and scalar parameter equality assertions. Named net identity is
  distinct from equality of the state values written on those nets.

Declared, unused I/O is legal but inert and produces a warning. Referenced
untyped I/O produces UNVERIFIED. No state type or wiring is invented.
Macro declarations and references to unspecified component ports remain
unverified; preserving their syntax does not instantiate them.

## Book examples actually checked

| Saved example | Parse | Structure | Reason |
|---|---|---|---|
| pcba_named_feedback.ccdl | PASS | PASS | Known single declared loop gain 1/10; unused I/O warnings |
| pcba_first_circuit_book.ccdl | PASS | FAIL | E-CJT-002: the Chapter 4 E-domain bias is below the C-domain cause |
| pcba_board_layout_book.ccdl | PASS | UNVERIFIED | Upward-feedback policy and inline net identity are not fully specified |
| pcba_safety_filter_book.ccdl | PASS | UNVERIFIED | Untyped input, operator admission, coupled loops, and unknown transfers remain open |

The last three files are code fences extracted from the reviewed book snapshots,
not repaired examples. The Chapter 4 conflict is reported against Appendix C's
explicit bias rule. Appendix C itself prints an upward CJT guard as admissible,
so the checker does not reject all upward CJTs using the simpler via rule.

The book supplies examples of low-gain upward feedback but no complete general
acceptance policy. It also supplies no executable cascade-depth threshold,
push-pull tolerance, full passive transfer functions, or temporal semantics.
The checker does not invent them. Unsupported advanced rail, sequence, monitor,
memory, event, and test forms are reported rather than silently skipped.

## Source identity and isolation

**pinned_sources/pcba_book/** holds the three reviewed current main-checkout
Markdown files. Their original paths and normalized SHA-256 values are in
**pcba_evidence/SOURCE_AND_EXAMPLE_MANIFEST.json**. The inherited book copy in
the starting worktree differs; for example, its vocabulary omits xnor/XNOR.
The pinned current Appendix C governs this work.

**pinned_sources/cas-forex/cas_forex/** holds four exact source snapshots. The
adapter verifies their raw hashes before use and records their original paths.
The recovered PCBA syntax hash starts ca4728d4; the inherited top-level
worktree variant starts c66fdc6c and was not substituted for it.

Only the original parser code and the two required schema enum definitions are
loaded into private namespaces. The adapter removes the schema imports before
loading parser ASTs. It does not import the cas-forex package, trading services,
or the permissive substring compiler bridge. Its strict wrapper supplies the
missing full-terminal and duplicate-parameter checks. The main CAS compiler
is loaded from this checkout at its existing reviewed hash solely to parse and
type complete state literals; no circuit code is executed.

## Bounds and open work

The reader accepts up to 64 KiB of UTF-8, 512 statements, 32 nesting levels,
and 65,536 tokens. Components are limited to 16,384 characters, 64 arguments,
and 512 characters per numeric literal. The graph search permits 20,000
expansions; exact gain products permit 65,536 numerator/denominator bits.
Reaching a graph/proof limit returns UNVERIFIED, never partial success.
Large proven products have bounded display labels while their exact input
literals remain in the edge evidence.

Remaining work requires explicit semantics for operator selection/admissibility,
upward feedback, full component/combined-network transfer, macro/port expansion,
advanced statement families, and temporal execution. Learned Helm use is a
separate milestone. These are not silently classified as completed by this patch.

See **pcba_evidence/VERIFICATION.md** for commands, test totals, initial invocation
failures, source hashes, and independently generated boundary-review evidence.
