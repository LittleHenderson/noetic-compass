# CAS v7.5 Rollout Plan — Phenomenological Register Axis Integration

**Status.** Active working plan. Tracks follow-on work required to propagate the Phenomenological Register axis (admitted in Clarification 8 on 2026-04-20) across all CAS artifacts.

**Scope.** The Register axis is integrated into authoritative references (Clarification 8, CLAUDE.md, Taxonomy Development Notes, TKS translation key) as of the admission date. Propagation across peer-review paper, book manuscript, codebase, dashboard, LLM scoring prompt, incident database, scenario catalog, and NL signal analyzer is a multi-week effort tracked here.

**Cadence expectation.** Not all propagation is urgent. Some artifacts (peer-review paper, LLM scoring prompt) are blocking for specific external milestones; others (full book rollout, scenario catalog) can proceed on natural research cadence. Each artifact section below includes a priority tag.

---

## Principle: Backward Compatibility

CAS v7.4 expressions remain valid in v7.5 (register-unspecified = register-neutral). No existing artifact is "broken" by the v7.5 admission. The propagation work **adds** register-specification capacity to artifacts that currently operate in v7.4 semantics; it does not **require** retroactive updates to every prior expression.

Propagation is therefore staged: new work in each artifact uses v7.5 semantics and Register specification where analytically useful; retrofit of existing v7.4 expressions is opportunistic (during normal maintenance) unless a specific artifact has blocking requirements for v7.5 (flagged below).

---

## Legal Framing

Register is framed as **specification of operational characteristics of existing Noetic × Domain × Drive primitives**, not as introduction of new ontological primitives. The 40 Cognitive States and 7 Drives remain unchanged from CAS v7.4. Register enriches how each primitive is characterized.

This framing preserves the integrity of the provisional patent filing **USPTO #64/037,173**, which describes the topos structure and 40-state matrix. The primitives in that filing are unchanged in v7.5.

**IP attorney consultation is required before the full utility patent is filed** to confirm that:

1. The Register-as-specification framing suffices under USPTO continuation-in-part rules, OR
2. A continuation-in-part filing is warranted to cover the Register axis as an extension.

Action: Wakil to schedule consultation with IP attorney before utility patent filing date. Specific questions to cover in consultation:

- Does the specification framing (axis of characterization, not new primitive) suffice under current USPTO interpretation?
- If a CIP is warranted, what filing window and fee structure applies?
- Does admission of v7.5 before full utility filing affect priority date of v7.4 content in the provisional?
- Are there any register-specific claims that should be drafted for independent protection?

This consultation is **blocking** for any public disclosure of v7.5 that might affect patent priority (e.g., arXiv submission of the v7.5 peer-review paper, major public announcement of v7.5, etc.).

---

## (a) Peer-Review Paper

**Location.** `peer_review/journal_submission/main.tex`.

**Priority.** High (blocking for arXiv submission of v7.5 paper).

**Required updates:**

1. Add Register axis to axiomatization. Specify the four Register values (T, A, f, E), the notation (`^n|R`, `F_k|R`, `^n^D_{F_k}|R`, `^n|R_n^D_{F_k|R_d}`), and the orthogonality of Register to the Noetic, Domain, and Drive axes.
2. Update operator definitions to acknowledge Register as a specification axis. No change to the 10 Noetic definitions themselves; addition of a "Register specification" subsection after the 10 Noetics.
3. Add worked examples demonstrating Register's expressive power. At minimum, include the three worked examples from Clarification 8 Section 9 (philosopher engaging unifying truth, AI refusing harmful request, surgeon in operating room).
4. Update abstract and introduction to reflect v7.5 designation. Acknowledge v7.4 as the prior specification.
5. Add cross-validation section referencing TKS 40 Elements and 28 Foundations independent structural confirmation, with translation-key pointer (`docs/reference/tks_28_foundations_translation_key.md`). Legal framing (specification, not new primitive) made explicit in the cross-validation section.
6. Update bibliography if new references are added for the Register axis.

**Dependencies.** IP attorney consultation must complete before arXiv submission.

---

## (b) Book Manuscript

**Location.** `book/manuscript/FULL_MANUSCRIPT.md`.

**Priority.** Medium (not blocking external milestones; benefits substantially from v7.5 enrichment).

**Required updates:**

1. **New chapter or section introducing Register.** Suggested placement: as a new chapter between current Chapter 9 (The 40 Cognitive States) and Chapter 10 (Cognitive Fractals). Content: full treatment of the Register axis with the worked examples from Clarification 8, the cross-validation via TKS structure, and the implications for reading the rest of the book.
   - Alternative placement: integrated into Chapter 9 as a concluding "The Fifth Axis" section. Decision between new-chapter and Chapter-9-extension to be made by Wakil based on pedagogical flow.
2. **Update Chapter 2 (The Ten Noetics).** Add a brief "Phenomenological Register: a specification layer" note after the Colloquialism Test sub-section, referencing the new Register chapter for full treatment. Do not duplicate the full Register treatment in Chapter 2; a single pointer paragraph suffices.
3. **Update Chapter 6 (Inversions).** Add a Register-specific inversions section addressing register-monoculture failures (e.g., over-Analytical at the cost of Embodied, over-Affective at the cost of Transcendent). Integrates with existing Reader-Level Inversions section.
4. **Update Chapter 9 (40 Cognitive States).** Show register variations for at least one state per domain (e.g., `^6^O|A` vs `^6^O|E` for the surgeon case). Demonstrates how Register multiplies the 40-state matrix expressively without changing the state count.
5. **Human application chapters (12-17).** These benefit most from Register enrichment. Retrofit existing examples to specify Register where the register distinction is pedagogically load-bearing. Priority within 12-17: Chapter 13 (Relationships — `F_4` register variation), Chapter 14 (Health — `F_3` register variation), Chapter 12 (Career — David's analyst-to-director transition is substantially a register shift).
6. **AI application chapters (18-22).** Register distinctions are pedagogically powerful for AI safety analysis. Chapter 21 (Adversarial Resilience) benefits particularly — the `^3^P|A` vs `^3^P|f` vs `^3^P|T` refusal-mechanism analysis from Clarification 8 Section 9 belongs here as a worked case.
7. **Mathematics chapters (23-27).** Formal treatment of Register in the topos. Register as an orthogonal axis; its interaction with the Fisher-Rao metric (does register partition the simplex, or does it cross-cut uniformly?); formal statement of the v7.5 axiomatization.
8. **Appendix D (Glossary).** Add entries for Transcendent, Analytical, Affective, Embodied Registers; Phenomenological Register; Register (abbreviated).
9. **Appendix A (40-Element Reference Table).** Consider adding a column for typical register variations, or a supplementary table (10 × 4 × 4 = 160 positions, but most register combinations are unremarkable). Decision: probably include the supplementary table in a new Appendix G with the specific register variants that matter pedagogically.

**Dependencies.** None blocking, but benefits from peer-review paper language stability.

---

## (c) Compiler

**Location.** `api/notation/compiler.py` (and related `api/notation/` files).

**Priority.** Medium-high (needed before LLM scoring prompt can use Register in v7.5 mode; backward compatibility must be preserved).

**Required updates:**

1. Add optional `|R` modifier to grammar (BNF extension).
2. Validate register values ∈ {T, A, f, E}. Reject invalid register values with specific error messages.
3. Update error messages to reference Register axis.
4. **Backward compatibility mandate:** expressions without Register remain valid. Omission of `|R` returns a register-neutral state representation. Parser must not require Register specification.
5. Update compiler tests to cover Register expressions (valid register values, invalid register values, register-neutral expressions, independent Noetic and Drive register specification).
6. Update `OPERATOR_NAMES` documentation or comments to note that the canonical framework is now v7.5 and Register is the optional specification layer.

**Dependencies.** None blocking.

---

## (d) Rust Engine

**Location.** `cas-engine/src/`.

**Priority.** Medium.

**Required updates:**

1. Add Register field (optional) to cognitive state representations (e.g., `CognitiveState` struct). Enum `Register { Transcendent, Analytical, Affective, Embodied }` or `Option<Register>`.
2. Update scoring functions to optionally consider register. If register is specified, lacunarity and balance calculations may extend to Register-axis lacunarity (currently not defined; deferred).
3. Backward compatibility preserved: engine accepts states without Register, treating them as register-neutral.
4. Update ontology module to document the v7.5 four-axis structure.
5. Add Register-related tests to `tests/` directory.
6. Register-axis lacunarity metric is a future design decision — not required in initial rollout. Flagged for later research.

**Dependencies.** None blocking.

---

## (e) Dashboard

**Location.** `dashboard/src/`.

**Priority.** Medium-high (Phase A of multi-modal visualization is a v7.5 rollout dependency; Phases B-E are progressive enhancement).

**Scope expanded on 2026-04-20:** Decision 5 from the Open Decisions section has been resolved as a full multi-modal visualization system. Specification lives at `docs/design/cas_v7_5_multimodal_display_specification.md`. Dashboard work now includes both visual (Radial Architecture Display) and auditory (Temporal Cognitive Score) modalities, formally corresponded via CAS algebra.

**Required updates — base (apply to all phases):**

1. Update state-display components to optionally show Register when assessment returns register-specified states.
2. Add Register explanation to UI (tooltip, help panel, or dedicated explanation page).
3. Update `dashboard/src/lib/interpretations.ts` to optionally interpret Register variations of the same Noetic × Domain × Drive combination.
4. Update tooltips to reference the four Registers when hovering over a state display.

**Required updates — Phase A (v7.5 rollout dependency):**

1. Static Radial Architecture Display rendering (concentric rings: Domains at compass points, 10 Noetic petals per Domain, Register quadrants per petal, Drive indicators at perimeter).
2. Basic interactive hover and click behaviors (cell-detail overlay on hover).
3. Domain / Noetic / Register / Drive display at all four rings.
4. Lacunarity void indication (empty quadrants with dashed outline).
5. Color palette with colorblind-accessibility considerations and value-encoding for grayscale.
6. Alternative text-based view for accessibility.
7. Keyboard navigation.

**Required updates — Phase B (enhanced mandala):**

1. Full interactive mandala (toggle register layers, toggle involution highlight, composition trace animation, comparison mode).
2. Involution visualization with connecting lines.
3. Composition tracing with animated flow between input cells and compound cell.
4. Side-by-side comparison mode for two Minds or two time points.
5. Zoomed Noetic sub-mandala (16 Domain × Register combinations for a single Noetic).

**Required updates — Phase C (auditory modality):**

1. Sonification engine implementation (Tone.js web audio).
2. Formal pitch / dynamic / tempo / rhythm / key-signature mappings per Part 2 of the multi-modal spec.
3. Playback controls (play, pause, scrub, loop).
4. Audio export (WAV, MP3).
5. Score notation rendering (four domain staves).

**Required updates — Phase D (multi-modal integration):**

1. Synchronized playback (cursor traverses score; mandala pulses in sync).
2. Cross-modal interactivity (click mandala plays score passage; playback highlights mandala).
3. Combined export formats (video with synchronized animation and playback).

**Required updates — Phase E (advanced research features):**

1. MIDI export for musicians wanting to edit/remix.
2. Score notation export (PDF, MusicXML).
3. Scientific audio analysis tools (spectrum, rhythm extraction).
4. Research-grade data export (JSON, CSV) with full axis values.

**Dependencies.** Phase A requires compiler and Rust engine Register support first. Phases B-E build progressively on Phase A. Phase C (sonification) is largely independent of the compiler/engine work and can proceed in parallel once mandala base is stable.

**Cross-reference:** full design specification at `docs/design/cas_v7_5_multimodal_display_specification.md`.

---

## (f) LLM Scoring Prompt

**Location.** `api/llm_connectors/base.py` (`CAS_BASE_SYSTEM_PROMPT`).

**Priority.** High (directly shapes scoring quality; user-visible effect).

**Required updates:**

1. Update prompt to instruct the scoring LLM to identify Register in addition to Noetic, Domain, and Drive where identifiable.
2. Add Register definitions verbatim from Clarification 8 Section 2 into the prompt, specifying human / AI / biological instantiations of each register.
3. Preserve backward-compatible scoring: if register is not identifiable from the input text, LLM should return register-neutral state (no `|R` specification).
4. Update prompt to note that Register resolves the Evaluative-domain ambiguity (analytical assessment vs affective response) via `|A` vs `|f` specification.
5. Retain the existing anti-drift annotations for `^3` (visceral-not-analytical) and `^8` (associative-not-deductive); these interact with the Register axis (`^3^E|f` is visceral-affective; `^6^C|A` is analytical-decomposition), and the prompt should surface that relationship.
6. Update `CAS_SELF_SCORING_APPENDIX` to request register specification as part of operator scores when appropriate.

**Dependencies.** None blocking. Update independently of compiler / Rust engine changes since the LLM prompt is a standalone string.

---

## (g) Incident Database

**Location.** `docs/AI_MISALIGNMENT_INCIDENTS_DATABASE.md`.

**Priority.** Low-medium (improves analytical depth but not blocking).

**Required updates:**

1. Re-examine the existing verified incidents (Incident 1 Uber ATG, Incident 2 Dutch toeslagenaffaire) under v7.5 Register lens. Add register-specified Noetic expressions where they illuminate the structural failure that register-neutral expressions did not.
2. Add register analysis to future incidents as standard procedure. Update the incident-entry template to include a "Register specification" field for each structural-analysis Noetic.
3. Update `docs/INCIDENT_CATEGORIES.md` Boundary Failures subcategory to address how register mismatches at the human-AI interface (e.g., AI running `^5^E|A` analytical-Mind-impregnation while human operates in `^5^E|f` affective-Mind-impregnation) may be a mechanism of interface failure.

**Dependencies.** None blocking.

---

## (h) Scenario Catalog

**Location.** `scenarios/` directory.

**Priority.** Low.

**Required updates:**

1. Update scenario expected-outputs to optionally specify register when the register distinction is part of what the scenario tests.
2. Audit existing scenarios for register coverage: do the ~238 scenarios cover register variations of key Noetics, or are they register-neutral? Surface gaps.
3. Add new scenarios specifically exercising Register distinctions (register-monoculture failure, register-balanced success, etc.).

**Dependencies.** Requires compiler support for Register parsing so scenarios can express register-specified expected outputs.

---

## (i) Natural Language Signal Analyzer

**Location.** `api/pipeline/text_signal_analyzer.py` and `dashboard/src/lib/textSignalAnalyzer.ts`.

**Priority.** Low-medium.

**Required updates:**

1. Add register detection to English-to-CAS translation. Map register indicators in natural-language input to the corresponding register-specified CAS expression.
2. Vocabulary mappings for register indicators:
   - `|T`: "sensed that," "had a vision of," "saw it all as one," "understood at the deepest level."
   - `|A`: "reasoned that," "worked it out," "concluded that," "deduced that," "stepped through the logic."
   - `|f`: "felt that," "was moved by," "had a gut feeling," "was emotionally struck by."
   - `|E`: "knew it in my bones," "felt it in my body," "did it without thinking," "my hands just did it."
3. Register becomes part of the translated CAS expression when vocabulary indicators are present; omitted when not.
4. Update English-generation scripts (for synthetic training data) to include register variations.

**Dependencies.** Requires compiler support for Register.

---

## Sequencing Recommendation

Suggested order for propagation work:

1. **Peer-review paper update** (blocking arXiv submission; gated on IP attorney consultation).
2. **Compiler Register support** (unblocks downstream LLM prompt, Rust engine, dashboard, and scenario work).
3. **LLM scoring prompt update** (benefits from compiler support but can proceed in parallel since it's a string update).
4. **Rust engine Register field** (downstream dependency for dashboard Phase A).
5. **Dashboard Phase A — minimum viable visualization** (Radial Architecture Display static rendering, basic interactivity, lacunarity void indication, accessibility baseline). **v7.5 rollout dependency.**
6. **Dashboard Phase B — enhanced mandala** (full interactivity, involution visualization, composition tracing, comparison mode). Progressive enhancement.
7. **Dashboard Phase C — auditory modality** (sonification engine, pitch/dynamic/tempo mappings, playback controls, audio export). Progressive enhancement. Largely independent of earlier work once Phase A is stable; can proceed in parallel with book work.
8. **Dashboard Phase D — multi-modal integration** (synchronized playback, cross-modal interactivity, combined exports). Builds on Phases B and C.
9. **Book manuscript Register chapter** (independent of technical stack; can proceed in parallel with dashboard work).
10. **Human-application chapter enrichment (12-17)** (after Register chapter establishes the axis).
11. **AI-application chapter enrichment (18-22)** (after Register chapter).
12. **Mathematics chapter formalization (23-27)** (after peer-review paper establishes formal treatment).
13. **Appendix updates** (final polish after main chapters stabilize).
14. **Incident database re-examination** (opportunistic during normal incident-analysis work).
15. **Scenario catalog register coverage** (after compiler support exists).
16. **NL signal analyzer register detection** (after compiler support exists).
17. **Dashboard Phase E — advanced research features** (MIDI export, MusicXML, scientific analysis tools). Research extension. Non-blocking.
18. **TKS 28 Foundations translation key full population** (requires Wakil source access and review; can proceed in parallel with other work).

This sequencing respects the backward-compatibility mandate: at every stage, existing v7.4 expressions continue to work. Register is added as optional capacity; nothing breaks.

**v7.5 rollout dependencies (items that must complete before v7.5 is considered rolled out):**

- (1) Peer-review paper update (or deferred per IP attorney guidance).
- (2) Compiler Register support.
- (3) LLM scoring prompt update.
- (4) Rust engine Register field.
- (5) Dashboard Phase A (minimum viable multi-modal visualization, visual modality only).

Items 6-18 are progressive enhancement, not rollout blockers.

---

## Open Decisions

1. ~~**Register heatmap visualization format** (dashboard). 4-axis visualization is a design problem with no obvious best form. Decision deferred.~~ **RESOLVED 2026-04-20:** Multi-modal system combining Radial Architecture Display (visual) and Temporal Cognitive Score (auditory), formally corresponded via CAS algebra. Full specification at `docs/design/cas_v7_5_multimodal_display_specification.md`. Phased implementation (Phase A as v7.5 dependency, Phases B-E as progressive enhancement) added to section (e) Dashboard above.
2. **Register-axis lacunarity metric** (Rust engine). Does lacunarity extend to Register? If so, with what formula? Research decision deferred until empirical Register-distribution data exists.
3. **New chapter vs. Chapter 9 extension** for book Register introduction. Pedagogical-flow decision for Wakil.
4. **Supplementary Appendix G** (160 Noetic × Domain × Register positions). Decision on full enumeration vs selective pedagogical highlighting for Wakil.
5. ~~**Continuation-in-part filing** (legal). IP attorney consultation outcome governs.~~ *(numbering preserved for historical reference; see legal-framing section earlier in this document for current IP-attorney action item.)*

**Note on numbering.** Decision 1 (formerly the dashboard-visualization decision) is resolved as of 2026-04-20. Remaining open decisions keep their original numbers for historical consistency.
