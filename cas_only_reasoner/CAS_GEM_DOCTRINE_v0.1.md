# CAS-GEM: Generative Episodic Memory — Doctrine v0.1

**Source:** owner directive, 2026-08-28.
**Status:** ADOPTED design doctrine for the reconstructive memory
board (CMB-R1). Build gates below; implementation NOT started —
Phase 4 (hybrid cortex) precedes it, because the reconstruction
engine is the cortex under CAS authority.

## Definition

CAS-GEM stores a compressed structural representation of an
experience, retrieves it from partial cues, and reconstructs a
probable narrative while preserving which details were stored,
inferred, or imaginatively supplied. The board implementing it is
**CMB-R1 (Reconstructive Cognitive Memory Board)** — an extension of
the existing CMB, which already stores CAS-compressed state
trajectories and carries the two language interfaces.

## The critical distinction

Archival memory stores and retrieves exact data. Reconstructive
memory stores the structural core, receives a partial clue, and
generates the most probable reconstruction. The essential honesty
rule: **once information is discarded during compression, the machine
cannot guarantee exact recovery — only a likely reconstruction from
what remains.** That is the tradeoff that buys enormous compression,
not a flaw — provided the labels never lie.

## Architecture: separate, but in concert

    CAS-SDG      creates structured training episodes + ground truth
    Transformer  learns encoding and narrative reconstruction
    CAS-Sem      represents the actual event content
    CMB-R1       stores and retrieves memory capsules
    CAS-RRK      controls the process and preserves authority
    Verifier     distinguishes anchors from generated details

The Transformer is a replaceable pattern-completion engine. It never
owns memory authority, truth status, durable writes, provenance, or
commitment. Its output is a CANDIDATE reconstruction.

## LOCAL CAS-SDG INVENTORY (search completed 2026-08-28)

The synthetic-data factory the doctrine assigns as the training-data
source EXISTS in this repo:

- **`cas-synthetic/`** — the CAS-Native SDG: `generator/` with twelve
  generator modules (v74_baseline, v75_register, v76_production,
  v77_omega, v77_rule_four, meta_logic, meta_logic_balanced,
  conversational, demographic_tonal_axes/rewrite, cas_transformer,
  base), plus `schemas/`, `scoring/`, `validation/`, `templates/`,
  `mix_controller/`, `llm_interface/`, `tests/`. Path D Wave 2.5
  produced the first SFE-gated corpus (5,268 certified records).
- **`docs/working/level3_conversational_sdg_spec.md`** — the Level 3
  conversational SDG spec: single supervised assistant turns with
  retained CAS expression targets, soft operator/domain target
  distributions, and provenance linking every record to its Level 2
  structural source — exactly the provenance-perfect record shape
  CAS-GEM training requires.
- **`docs/working/gate4_next_board/`** — SDG conversation batches
  (conversations_sdg.jsonl, precheck reports, preregistrations) from
  the harness lane.

The GEM curriculum (Levels 1-7 below) is a NEW generation task for
this existing factory, not a new factory.

## The MemoryCapsule (Gate 1 freeze target)

Both layers required per capsule: CAS cognitive structure (Phi
trajectory, Theta recipe, noetic/domain/drive/foundation profiles)
AND CAS-Sem event content (entities, participants, events, semantic
roles, causal relations). Plus: exact_anchors, sensory_cues,
unusual_features, emotional_signature, gist, unresolved_fields,
contradictions, source_hash, provenance, confidence, embeddings
(semantic + CAS-structural), linked_memories, consolidation_level,
leakage_policy, last_recalled, episode_time + time_precision,
location. The `Phi<...>` / `Θ(Ω)` capsule syntax is a PROPOSED
CAS-GEM extension, not currently canonical CCDL.

## Retrieval: the minor-clue system

A clue (smell, person, phrase, location, feeling, fragment, goal)
becomes a structured CuePacket; retrieval searches several channels
at once (CAS structural similarity, semantic embedding, entity
overlap, time proximity, location, sensory match, causal-graph
overlap, exact-anchor match) with LEARNED, CALIBRATED weights — never
assumed. The top several memories are retrieved as competing memory
hypotheses under the branch manager, never only the first.

## Reconstruction

The transformer receives clue + top capsules + exact anchors +
missing-field mask + detail level + mode, and generates several
candidate narratives. The objective: maximize narrative likelihood
SUBJECT TO every exact anchor, timeline constraint, entity identity,
and stored causal relationship. CDAB compares candidates under the
same memory evidence; a candidate conflicting with stored evidence is
rejected; a modest candidate that marks gaps beats a vivid one that
invents.

## Evidence labels — the most important requirement

Every reconstructed sentence carries one of: **EXACT** (preserved in
the capsule), **DERIVED** (follows logically from stored facts),
**RECONSTRUCTED** (probable connective detail, with probability),
**IMAGINED** (deliberately invented), **UNKNOWN** (insufficient
evidence), **CONTRADICTED** (conflicts with preserved evidence). The
user may ask for a smooth narrative with labels hidden; the trace
preserves them always.

## Memory and imagination: one engine, different constraints

Recall Mode (anchors hard, unknown stays unknown, low temperature) /
Plausible Reconstruction Mode (connective fill, marked) / Simulation
Mode (memories + goals, all outputs hypothetical) / Imagination Mode
(recombination across capsules, source lineage preserved) / Dream
Mode (relaxed boundaries, contributions tracked). Imagination =
controlled recombination of compressed memory structures under
relaxed truth constraints. The distinction is the evidence and
authority gates applied afterward, not the generator.

## Three-tier storage

Hot (recent, raw, full trace; hours-days) / Warm (consolidated
capsules; months-years) / Cold (recipes, schemas, lessons,
generalized knowledge; indefinite). Fits the CMB's existing fast/slow
cell motif.

## Never compress equally

Preserve verbatim: passwords/crypto material, legal commitments,
financial and medical records, exact formulas, source code,
citations, names, dates, measurements, direct quotations,
user-designated permanent memories. Safe to reconstruct: casual
conversation flow, atmosphere, gist, routine episodes, background,
connective language. The memory policy decides which — with user
approval where designated.

## The largest danger: confabulation becoming memory

The forbidden loop: reconstruction stored as original -> later recall
treats invention as fact -> false memory hardens. REQUIRED
INVARIANTS: (1) a reconstruction NEVER overwrites its originating
capsule — OriginalMemoryCapsule, RecallEvent, GeneratedNarrative,
UserCorrection, ConsolidationDecision are separate records; a
correction amends the capsule only through a governed write-back
transaction. (2) Repeated generation does not increase factual
confidence — fluency is not corroboration, repetition is not
evidence.

## Traceability

Every recollection produces a MemoryEvidencePacket (cue packet,
retrieved ids + scores, anchors used, candidate + rejected
reconstructions, contradiction checks, selected narrative,
sentence-level evidence labels, uncertainty, model version, memory
revision, trace id) — answering "why did you remember this, which
details were stored, which reconstructed, how certain, did
imagination fill anything."

## CAS-Ohm

Never supplies the reconstruction likelihood and never decides
whether a memory is true, a reconstruction matches, or a narrative is
authentic. Retrieval/generative models carry their own calibrated
uncertainty. (Per the CAS-Ohm paper's own restrictions.)

## CAS-SDG training curriculum (Gates 2+)

Level 1 exact completion; Level 2 missing surface form (paraphrase
preserving meaning); Level 3 sparse clues; Level 4 interference
(similar memories, one distinctive clue); Level 5 ambiguous recall
(correct output = uncertainty or clarification); Level 6 imagination
(recombination, every component marked); Level 7 correction and
reconsolidation (update the capsule without rewriting unrelated
memories). The SDG knows ground truth for preserved / omitted /
inferable / unrecoverable / hallucinated — that is why it is the
factory.

## Metrics

Compression ratio; exact-anchor precision and recall; semantic
fidelity; event-order, entity-role, temporal, causal accuracy;
false-detail rate; unknown-field honesty; cue retrieval accuracy;
similar-memory discrimination; confidence calibration; cross-memory
contamination; delayed-recall stability; latency, footprint, energy.
The two most important: **narrative usefulness** and
**unsupported-detail rate** — a vivid reconstruction that invents
twelve details is worse than a modest one that admits three gaps.

## Build sequence

Gate 1 MemoryCapsule spec freeze; Gate 2 CAS-SDG training corpus;
Gate 3 retrieval-only prototype (sparse clues find the right capsule
BEFORE any narrative generation); Gate 4 constrained narrative
decoder with evidence labels; Gate 5 candidate comparison and
verification; Gate 6 on-device three-tier hierarchy with encrypted
persistence; Gate 7 imagination modes — ONLY after Memory Mode
cleanly separates stored, inferred, and unknown content.

## Sequencing

CMB-R1 follows Phase 4: the constrained narrative decoder IS the
cortex under CAS authority, so the cortex adapter, authority
firewall, and proposal contract land first and are reused here.
