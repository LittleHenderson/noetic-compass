# Defects recorded against *CAS PCBA Engineer* by the Project Coherence monographs

**Subject book:** `CAS_PCBA_Engineer.pdf` — 743 pages
**Baseline identity:** `src-pcba-engineer-20260726`
**SHA-256:** `294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274`
**Compiled:** 2026-08-08, from monographs v0.3 (five volumes)
**Method:** five extraction agents over all 16 chapter/appendix files of `cas_pcba8`, all 16 of `cas_ohm1`, and a completeness sweep of `cas_core8`, `noetic_topos2`, `tks_v8`.

Every page anchor below is given in the monographs' dual form: **PDF p. N (book p. M)**. They
resolve against the exact bytes above and no other build.

---

## Scope, stated honestly before the list

**Which volumes actually criticise this book.** Only two: `cas_pcba8` (built on the book as its
baseline) and `cas_ohm1` (one conflict). The sweep classified all 17 Adverse Findings in the
other three volumes: **zero** target this book — they target prior voided program work products,
the legacy Noetic site, or the candidate software's own artifacts.

**Of the eight Preserved Conflicts in the CAS-Ohm source audit, exactly one is book-directed**
(Conflict 4, gain definition). The other seven cite the Quantification Guide, the operationalization
addendum, or PCBA Appendix I — separate artifacts with their own hashes, not this book.

**What the grammar audit is and is not.** It is a *bounded surface-syntax comparison*: printed
listings against the printed EBNF. It is not a parser, not semantic validation, and not a review of
CCDL's design quality. The monograph is explicit that even 5-of-5 conformance would have said
nothing about semantic validity. Findings attach to this build only and do not transfer to a revised one.

**One board was explicitly cleared.** CCB-2-COB is recorded as *"no direct counterexample found in
bounded surface audit"* — the monograph deliberately refuses to convert this into a conformance pass,
and equally refuses to count it as a defect.

---

## A. Blocking defects

### A1. The published grammar does not cover the book's own reference corpus
*Corroborated in 8 places across two volumes.*

**Verdict of record:** `FORMAL EBNF DOES NOT COVER PUBLISHED FIVE-BOARD CORPUS.`
Direct counterexamples: **four of five** boards. Bounded non-counterexample: one.

The consolidated structural EBNF (**PDF pp. 598–599 / book pp. 582–583**) offers only **seven**
`circuit_item` alternatives and **two** `board_item` alternatives. Against that:

| Board | Location | Defect |
|---|---|---|
| **CCB-1-CSB** | PDF pp. 606–608 (bk 590–592) | *Every* body item is outside the `board_item` production. Nine leaders (`input`, `output`, `node`, `cjt`, `diff`, `mux`, `filter`, `feedback`, `probe`); the production admits only `layer_decl`/`via_decl`. |
| **CCB-3-CDAB** | PDF pp. 618–619 (bk 602–603) | `mirror bias_mirror: replicate(shared_bias) -> [cjt_l, cjt_r]` — call-shaped syntax, an arrow, and a bracketed target list. The grammar's RHS must be `type_name<arg_list>`. Three simultaneous failures. |
| **CCB-4-CMB** | PDF pp. 623–624 (bk 607–608) | Five leaders with no production: `charge`, `select`, `discharge`, `refresh`, `scan`. The monograph calls this the cleanest instance — *no alternative reading is available*. |
| **CCB-5-CPMB** | PDF pp. 628–632 (bk 612–616) | Fourteen leaders with no production: `rail`, `use`, `spec`, `dial`, `constraint`, `monitor`, `on`, `derate`, `route`, `alert`, `hold`, `sequence`, `gate`, `force_state`. "The counterexample of scale." |

**The aggregate that matters:** nineteen distinct leaders have no production *anywhere*, against
seven `circuit_item` alternatives in total. **The corpus uses more statement vocabulary outside the
grammar than inside it.** The published EBNF is a core fragment, not the language.

**Three structurally distinct defect kinds** — they need different fixes, and conflating them will
mislead the repair:
1. **Context mismatch** (CCB-1) — the forms exist in the grammar's world but not in that block context.
2. **Expression mismatch** (CCB-3) — requires a *new expression grammar*; this is language design, not errata.
3. **Register omission** (CCB-4, CCB-5) — whole statement families absent.

**Compounding issues:**
- The book *reserves* eighteen Part-IV statement leaders (**PDF p. 578 / bk 562**) and describes further forms in prose tables (**PDF pp. 591–592 / bk 575–576**) — none of which the EBNF produces. Reserving a word asserts it belongs to the language; the book asserts and then omits.
- `gate` appears in a published listing but is in **neither** the reserved-word list **nor** the grammar.
- **CCB-1 is under-determined**: the book never decides whether `board` should admit circuit content, or whether the listing should have said `circuit`. The two fixes produce *different languages*. An implementer choosing would be "legislating language design, not implementing it."
- **The erratum clause is an admission, not a repair.** Treating it as a fix makes coverage unfalsifiable.
- **Root cause named:** the appendix and the corpus evolved on different schedules, and the book shipped the divergence.

### A2. The flagship safety board's protective fuse can never trip
*Corroborated in 8 places across two volumes.*

**Location:** **PDF p. 342 (book p. 326)**, Chapter 18 primary listing; values repeated at
**PDF p. 608 (book p. 592)**, Appendix D.

The red stage — the final, maximal-severity alarm stage feeding the protective element — carries a
saturation clamp of **`sat = 0.1`**. The downstream fuse carries a trip threshold of **`0.9`**.
The clamp bounds the red-stage output unconditionally at 0.1, and no declared stage on the
clamp-to-fuse path amplifies. **The protective crossing is unreachable: the fuse, as published,
cannot trip.**

The repetition in Appendix D **forecloses the typo defence** — the contradictory pair is published twice.

### A3. Red-stage gain published as `beta = infinity`
*Corroborated in 7 places.*

**Location:** **PDF p. 342 (bk 326)**; repeated **PDF p. 608 (bk 592)**; acknowledged **PDF p. 610 (bk 594)**.

A non-finite value in a language whose grammar and validator rules require finite parameters.
The Appendix D note concedes this in the book's own voice and directs implementers to substitute a
large finite value — **a partial repair that leaves the load-bearing 0.1-vs-0.9 contradiction
untouched.**

---

## B. Secondary safety defects on the same board

These are **independent of the arithmetic** — they would remain even if the clamp/threshold were fixed:

- **No fail-closed latch state machine** is defined for the CSB fuse anywhere in the book.
- **Open-fuse polarity never established** — tripping may *suppress the refusal path it protects*.
- **Red-stage saturation is a memoryless plateau**, so the maximal alarm **de-asserts under oscillation**.
- **Unreachability masks the other two.** Because the fuse never fires, testing would report the board
  **vacuously safe** — the latch and polarity defects would never surface.
- The book **specifies a protective mechanism but provides no demonstration it can ever work.**
- **The book's validators enforce only per-value type checks** and miss relational contradictions —
  which is precisely why a 0.1 clamp and a 0.9 threshold can both pass validation individually.

---

## C. The gain-definition conflict (CAS-Ohm, preserved unresolved)

**Location:** **PDF p. 56 (book p. 40)** and **PDF p. 153 (book p. 137)**.
Registered as `OHM-CONFLICT-GAIN-DEFINITION`.

The book defines gain via **Fisher–Rao displacement ratios**; the operationalization addendum uses a
**Jacobian** gain. These are **unbridged mathematical profiles** — not two notations for one quantity.

- **No chain rule** composes the book's Fisher–Rao ratios along a cascade.
- Identifying the book's gain with the operational gain **requires assumptions nobody has stated**.
- **Still open at the close** — no theorem and no experiment has bridged them.
- It is a **method-identity conflict upstream of all comparison and composition**: until it is
  resolved, gain figures computed under the two definitions are not comparable.

---

## D. Unrepresentable and unsupported constructs

- **Capacitor-like component kind** described in prose has no contract in the candidate's closed catalog.
- **Memristive elements** the book gestures at are **unrepresentable** — path-dependent semantics the type system cannot express.
- The **postponed constructs are exactly the ones with unformalized stateful/temporal semantics** — the hardest register, and the one left out.
- **Borrowed circuit vocabulary is a typed pun.** The names invite physics the model cannot support.
- The book contains **no physical artifact, no telemetry, and no measurement of any kind.**
- **No orthogonality theorem** is imported from the book into the type layer.

---

## E. What the book already says about itself

Useful for revision because the monographs treat these as load-bearing, and they blunt several criticisms:

- **Copyright page (PDF p. 4)** disclaims safety certification, guaranteed model behavior, and legal/medical authority.
- **Appendix D note** concedes the infinite-gain idealization.
- **Erratum language** covers missing appendix forms.
- The **Phase-0 authority matrix** denies the book both safety certification and physical telemetry.
- The candidate's **conditions of use** admit the book as *design text only, never as evidence*.

The monographs' concern is not that these disclaimers are missing but that **no front-matter sentence
reliably dispels the authority the book's genre and weight project.** A 743-page technical book
*reads* as authoritative regardless of what page 4 says.

---

## F. Structural and process criticisms

- **At 743 pages, no reader or reviewer holds the book whole** — mechanical audit is the only available rigor.
- **The medium typesets hypotheses, idealizations, and errors with the same confidence as tested facts.** Nothing in the layout distinguishes them.
- **The internal changelog label predates the supplied build** — the book's own version marker is stale.
- The book publishes **no construct-coverage matrix, no rejection of unsupported forms, and no canonical round-trips** — the three artifacts that would have caught A1 before publication.
- **Named CAS/PCBA claims remain quarantined hypotheses or prohibited inferences.**
- **Hashing the book establishes nothing about its correctness** — *"the baseline is identified, not endorsed."*
- The baseline is **internally inconsistent at precisely identified locations**, and by policy those
  inconsistencies are **preserved and formalized, never repaired in place**. Two of the monographs'
  central results are demonstrations of exactly this.

---

## Suggested revision order

1. **A2 + A3** — the safety board. Two published numbers contradict each other, twice. Highest reputational exposure, smallest edit.
2. **B** — the latch and polarity defects, which the unreachability is currently hiding.
3. **A1** — the grammar. Decide the CCB-1 `board`/`circuit` question first; it is a language-design fork, not an erratum, and it gates the rest.
4. **C** — the gain definition. Pick one definition or state the bridging assumptions.
5. **F** — publish a construct-coverage matrix so A1 cannot silently recur.

---

*Compiled from: `cas_pcba8` ch01–ch03, ch06, ch10–ch12; `cas_ohm1` ch04, ch08, ch09, ch11, ch13, ch14.
69 raw extractions deduplicated to the distinct defects above. Every item traces to a monograph file
and line; the machine-readable extraction is retained in the session scratchpad.*
