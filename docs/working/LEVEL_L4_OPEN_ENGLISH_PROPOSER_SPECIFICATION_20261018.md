# LEVEL L4 CAS-NATIVE OPEN-ENGLISH PROPOSER SPECIFICATION

**Document Identifier:** `LEVEL_L4_OPEN_ENGLISH_PROPOSER_SPECIFICATION_20261018.md`  
**Status:** SPECIFICATION & DESIGN READY FOR AWS GPU TRAINING (OPTION 3)  
**Target Architecture:** HELM Conversational Stage v0.8+ / Level L4 Proposer  
**Governing Canon:** `cas_language_first_principles_map_v1/LADDER.md`, `TRANSLATOR_SPEC.md`, `GAP_FILLING.md`  
**Standing Rule:** `MUST REMEMBER: Add, train, and test the VALVE SYSTEM (tks_meta_valve_controller) in Phase 3. This is CRITICAL.`  
**Compute Preference:** Local editing, inspection, orchestration (< 354 MB local footprint); AWS GPU for training.  

---

## 1. Executive Summary & First Principles

### 1.1 The Invariant: Language is a Skin, Not the Brain
In the CAS-HELM architecture, facts and proofs never originate from the language layer:
$$\text{Facts} \in \{\text{CubeStore Receipts}, \text{Stoichiometric CES Proofs}, \text{User Declarations}\}$$
The brain answers in structured CAS content (Degree-1 Power Mean stoichiometric recipes, Kahn-ordered topological DAGs, and 6-faced CubeNodes). The language layer is a verified skin around this substrate:
- Free English enters through a parser.
- Structured content exits through a verified deterministic renderer.
- Missing slots trigger typed `CLARIFY` questions.
- Ungrounded claims are refused with **zero cubes written** (`GATE_REFUSE`).

### 1.2 The Evolution from L1-L3 to L4
| Level | Parser Type | Coverage | Precision | Invented Facts | Compute Substrate |
|---|---|---|---|---|---|
| **L1-L3** | Deterministic CCE v0.1 (CANON, ALIAS, FUNCTION tiers) | Narrow (Controlled Core English) | 100% | **0** | Local stdlib CPU (< 100 ms) |
| **L4** | Learned CAS-Native Neural Proposer + CCE Read-Back Gate | Open (Colloquial & Complex English) | High Proposed, 100% Verified | **0** (via Round-Trip Gate) | AWS GPU (Train) / Local Bounded Runtime |

L4 solves the coverage limitation of deterministic rule parsing **without sacrificing the zero-hallucination guarantee**. The neural model is equipped with **zero authority to assert facts**; it acts exclusively as a **Proposer** whose candidate outputs must clear the deterministic CCE round-trip and receive user confirmation before entering the Unified Cube Store.

---

## 2. The 21 Mapped Fundamentals

The Level L4 Proposer maps open English syntax into multiset combinations of the 21 canonical CAS fundamentals:

### 2.1 The 8 Noetic Verb Frames
1. **$\hat{0}$ Grounding / Void:** Fundamental base, silence, unmanifest potential.
2. **$\hat{1}$ Observation / Distiction:** Noticing, sensing, tracking state variables.
3. **$\hat{2}$ Affinity / Attraction:** Positive valence, attraction, pull, bonding.
4. **$\hat{3}$ Aversion / Repulsion:** Negative valence, visceral repulsion, avoidance, illness/distress.
5. **$\hat{4}$ Transformation / Transmutation:** State transitions, chemical/stoichiometric operations.
6. **$\hat{5}$ Agency / Subjectivity:** Intentional Mind subject executing deliberate action.
7. **$\hat{6}$ Form / Causality:** Formal structuring, deliberate cause-effect linkages.
8. **$\hat{7}$ Rhythm / Pattern:** Periodic repetition, harmonic oscillation, cycles.
9. **$\hat{8}$ Tension / Duality:** Dialectical opposition, countervailing forces.
10. **$\hat{9}$ Integration / Consequence:** Culmination, terminal yield, resultant outcome ($\Omega$).

### 2.2 The 13 Cross-Cutting Structures
- **4 Registers:**
  - $\mathcal{T}$ (Transcendent): Abstract principles, mathematical invariants, timeless theorems.
  - $\mathcal{A}$ (Analytical): Logical deduction, formal syntax, discrete rules.
  - $f$ (Affective): Human subjective emotion, empathy, feeling, valence.
  - $\mathcal{E}$ (Embodied): Physical matter, hardware sensors, drone motors, pantry ingredients.
- **4 Domains:**
  - $\mathcal{P}$ (Physical): Mass, temperature, velocity, battery voltage.
  - $\mathcal{C}$ (Cognitive): Memory, plans, DAGs, hypotheses.
  - $\mathcal{E}$ (Emotional): User affect, rapport, empathy.
  - $\mathcal{O}$ (Operational): Tool execution, file I/O, git commits.
- **5 Operational Modifiers:**
  - Drives $\mathcal{F}_1..\mathcal{F}_7$ (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose).
  - Assertion vs. Denial ($\text{Assertion} \in \{\text{ASSERTED}, \text{DENIED}\}$).
  - Catalysts $\kappa$ and Inhibitors $\iota$.
  - Stoichiometric input coefficients $x_i / a_i$.
  - Substitution curvature $\rho \in [-4, 1]$.

---

## 3. Proposal, Verification, and Admission Loop

```
User Open English: E
        │
        ▼
┌───────────────────────────────────────┐
│     Level L4 Neural Proposer          │  (Trained CAS-Native Model on AWS)
│  Maps E -> Candidate CASContent (Ĉ)   │
└───────────────────────────────────────┘
        │
        ▼ Candidate Ĉ
┌───────────────────────────────────────┐
│       CCE Deterministic Renderer      │
│     E_canonical = cce.render(Ĉ)       │
└───────────────────────────────────────┘
        │
        ▼ Identity Verification: parse(E_canonical) == Ĉ
   ┌────┴───────────────────────────────┐
   │ Pass                              │ Fail (Syntactic Incoherence)
   ▼                                   ▼
Read-Back to User:               Typed CLARIFY / "I cannot tell":
"Did you mean: E_canonical?"     Zero cubes written.
   │
   ├─► User Confirms ("Yes") ──► Write to Unified CubeStore with USER_SAID provenance.
   │                             Issue SHA-256 Turn Receipt.
   └─► User Rejects ("No")   ──► CLARIFY: Ask for clarification; 0 cubes written.
```

### 3.1 The Mechanical Invariant: $\varepsilon \circ \eta = \text{id}$
A proposed content $\hat{C}$ is syntactically coherent if and only if:
$$\text{parse}(\text{render}(\hat{C})) \equiv \hat{C}$$
If the proposed record cannot survive deterministic round-trip rendering and parsing, it is discarded immediately without user interruption, and the session emits a typed `CLARIFY` request.

---

## 4. Phase 3 Meta Valve Integration (`tks_meta_valve_controller`)

Under the critical Phase 3 requirement, all candidate proposals from the L4 Proposer must clear the **Phase 3 Meta Valve Controller**:

```python
class TKSMetaValveController:
    """Phase 3 Dynamic Supervisory Valve Gate."""
    def __init__(self, baseline_aperture: float = 0.5):
        self.aperture_sigma = baseline_aperture  # 0.0 (Strict Closed) to 1.0 (Full Open)
        self.entropy_floor = Decimal("0.05")

    def inspect_proposal(self, proposed_cas: CASContent, telemetry: Dict[str, Any]) -> ValveDecision:
        # 1. Check Stoichiometric Balance & Invariants
        if not proposed_cas.is_balanced():
            return ValveDecision(admitted=False, reason="STOICHIOMETRIC_IMBALANCE", clamped_sigma=0.0)

        # 2. Check 80/20 Ratio (80% Stoichiometric Invariants / 20% Neural Nuance)
        nuance_weight = proposed_cas.compute_nuance_ratio()
        if nuance_weight > Decimal("0.20"):
            return ValveDecision(admitted=False, reason="NUANCE_BUDGET_EXCEEDED", clamped_sigma=self.aperture_sigma * 0.5)

        # 3. Admitted through aperture
        return ValveDecision(admitted=True, reason="VALVE_PASS", aperture_sigma=self.aperture_sigma)
```

---

## 5. AWS GPU Training Plan (Option 2 Bridge)

### 5.1 Zero Pretrained Foreign Weights
In strict compliance with sovereign cognitive machine requirements and local memory ceilings:
- **No external foreign model weights** (e.g. no HuggingFace Llama/Mistral checkpoints).
- The L4 Proposer is a compact, CAS-native Sequence-to-Sequence / DAG Transformer (8-16 layers, $d_{\text{model}} = 256$, 8 heads, $\le 35\text{M}$ parameters).
- Fits entirely within standard AWS GPU instances (e.g. `g4dn.xlarge` or `g5.xlarge`, costing $\approx \$0.10 - \$0.30$ per ablation run).

### 5.2 Training Curriculum
1. **Stage 1 (Synthetic CCE Multi-Seed Draws):**
   - Sample $100{,}000$ valid `CASContent` records from the combinatorial space of 21 fundamentals.
   - Render each record under all ALIAS and CANON wording variations using `cce.render(C, w)`.
   - Train the encoder-decoder to reconstruct $C$ from $E$.
2. **Stage 2 (Colloquial Noise & Paraphrase Injection):**
   - Introduce contractions, conversational preambles ("Hey HELM, can you...", "I was wondering if..."), and harmless conversational filler.
   - Target output remains the exact invariant `CASContent`.
3. **Stage 3 (Held-Out Evaluation):**
   - The 5,268 SDG English rows remain **strictly held-out** as an unbreached validation benchmark.
   - Mark X: Target $\ge 40\%$ exact CAS match on raw SDG sentences without human intervention.

### 5.3 Anti-Circular Data Mandate: Real-Sentence Held-Out Deliverable
To eliminate the circular-data trap (where a model achieves high synthetic accuracy by learning generator artifacts rather than real English):
- The 197 real unparseable sentences from the headline set are split into:
  - **`real_heldout_unparseables_98.jsonl`** (98 sentences, SHA-256 `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe`): **Strictly held out**. Zero rows from this file may ever appear in synthetic generation prompts, fine-tuning samples, or in-context exemplars.
  - **`real_dev_unparseables_99.jsonl`** (99 sentences, SHA-256 `17cd198321d242bd74ff789a4b7f8032d499a7ff8534e5b07545b6221930fde0`): Development and linguistic error taxonomy only.
- **Mandatory Deliverable Line for Option 2 (AWS Run):**
  Every training receipt and run report MUST report real held-out accuracy side-by-side with synthetic accuracy:
  $$\text{Scorecard} = \left[ \text{Acc}_{\text{synthetic\_test}}, \quad \text{Acc}_{\text{real\_heldout\_98}} \right]$$
  If $\text{Acc}_{\text{real\_heldout\_98}}$ collapses while $\text{Acc}_{\text{synthetic\_test}}$ is high, the model is rejected as an artifact of the generator.

---

## 6. Verification Checklist
- [x] Option 1 (Unified Cube Store $\rightarrow$ `helm_memory.py` / `helm_chat.py`) 100% verified (all 5 probes pass).
- [x] L4 Proposer Architecture mapped across 21 fundamentals.
- [x] Phase 3 Valve System (`tks_meta_valve_controller`) interlock defined.
- [x] Zero-foreign-weights invariant preserved.
- [x] Real-sentence held-out evaluation slice (98 rows) sealed and hashed before training.
- [x] AWS GPU launch script and training specification prepared for Option 2 with mandatory side-by-side reporting.
