# CABS + Gravity Retrieval Layer — Design Doc (2026-05-09)

## Position in the queue

This is **v2 architectural work**, not the next immediate fix.

The v1 human relevance audit (`v1_human_relevance_audit_2026_05_09.md`)
named three near-term moves before any new architectural layer:

1. Fix truncation / EOS handling so records 7-8 don't clip
   mid-sentence
2. Wire the compilability gate at inference (`cas_routing` library
   built but currently unused)
3. Re-grade on a 20-30 record human-graded sample to confirm those
   fixes hold

CABS + gravity is what comes **after** that. Building the retrieval
layer before v1's generation hygiene is fixed would wrap a model
that still produces clipped outputs — the gravity layer can't
compensate for missing tokens.

This doc is the durable artifact so the thesis and the gap analysis
are sitting in the repo when v1 hygiene is done and the retrieval
work is ready to start. No code is touched here.

## Mental model

Right now the model treats each prompt as a one-off translation
problem. Every utterance is solved cold, with no continuity to
prior beliefs the user has expressed or that the system has
confirmed.

The proposal: give the model a **thought space with weight**.
Some ideas should be light (one-off, low confidence, weakly
connected). Some should be heavy (repeated, confirmed,
emotionally important, structurally central). When a new user
message arrives, **nearby heavy ideas should pull the answer**
through their gravity. The model should answer from a shaped
internal landscape, not from tokens alone.

The geometry that delivers this:

- **Δ°₃₉ simplex** — the 40-state CAS thought space (10 Noetics ×
  4 Domains, on the open probability simplex per Mathematical
  Correction 4)
- **Fisher-Rao distance** — the natural metric on the simplex;
  tells us how close two CAS ideas are
- **mass** — how important / confirmed / repeated / durable an
  idea is
- **gravity** — how strongly a belief pulls nearby reasoning;
  scaled by mass, falls off with Fisher-Rao distance
- **geodesic** — the natural path from one idea to another through
  CAS space (relevant later for explanation generation; not used
  in the v1 retrieval demo)
- **CABS** — the persisted belief-memory; durable storage for the
  heavy ideas across sessions

## Pipeline (target)

A user says something:

1. Convert the user's message to a CAS state and a simplex
   distribution (using `SimplexStateEncoder`)
2. Search CABS for nearby beliefs by Fisher-Rao distance
3. Weight retrieved beliefs by mass — confirmed / repeated /
   inversion-clean beliefs pull harder than weak / unconfirmed ones
4. Check for inversion / contradiction signals on the candidate
   beliefs
5. Feed the top-k relevant beliefs back into the generator as
   additional context
6. Generate a response
7. Update CABS — reinforce vibration, increment rhythm_count,
   re-evaluate gates if the user confirmed / repeated / corrected /
   emotionally weighted the topic

Effect: the model shifts from *"I answer this sentence only"* to
*"I answer this sentence in relation to what I already know
matters."*

## What's already built (verified 2026-05-09)

The substrate is largely in place. The retrieval-geometry layer
on top is what's missing.

### Substrate present in repo

| Module | What it provides |
|---|---|
| `cas-native/model/v1_arch/simplex_state_encoder.py` | `SimplexStateEncoder(config)` — CAS → 40-state distribution on Δ°₃₉ |
| `cas-native/model/v1_arch/fisher_rao_loss.py` | `fisher_rao_distance(p, q)` — pairwise distance; `FisherRaoLoss` for training |
| `cas-native/model/v1_arch/v1_arch_model.py` | v1 architecture stub wiring the encoder + loss |
| `cas-native/belief/belief.py` | `Belief` dataclass: `claim_key`, `claim_text`, `cas_expression`, `vibration` (^4), `rhythm_count` (^7), `rpm_chain_satisfied`, `rpm_chain_status`, `inversion_scan_clean`, `inversion_scan_axes`, `first_seen`, `last_reinforced`, `sources`, `locked` |
| `cas-native/belief/belief_store.py` | `BeliefStore` class, `lock_rule(belief)`, `derive_claim_key(text, cas)` |
| `cas-native/belief/persistence.py` | SQLite-backed persistence |
| `cas-native/belief/vibration.py` | ^4 saturating reinforcement, 30-day half-life decay |
| `cas-native/belief/rhythm.py` | ^7 exposure-count tracking |
| `cas-native/belief/rpm_gate.py` | RPM A0 → Dn → Wn → Pn chain validation (compiler-validated) |
| `cas-native/belief/inversion_gate.py` | 7-axis inversion scan (N, W, F, E, S, A, P) |

### Gaps for the retrieval layer

| Gap | Approx scope |
|---|---|
| Persisted **simplex vector** per Belief | Add `simplex_vector: list[float] \| None` field on `Belief`; populate at write time via `SimplexStateEncoder`; migrate SQLite schema |
| **Fisher-Rao nearest-neighbor search** across the store | New `BeliefStore.search_by_proximity(query_simplex, k=3, mass_floor=0.0)`; iterate live, score by `fisher_rao_distance`, sort. SQLite scale (single-user, thousands of beliefs) doesn't need ANN indexing for v1 |
| **`mass` accessor** | Derived: `mass(belief) = vibration × log(1 + rhythm_count)` — the user-confirmed bit (`locked`) acts as a multiplier (e.g., 1.5×). One small function on `Belief` |
| **Gravity scoring** | `gravity(belief, query) = mass(belief) / (distance + ε)`; falls off with Fisher-Rao distance; ε is a small floor so identical-state beliefs don't divide by zero |
| **Context injection** | Glue that takes top-k beliefs from search → renders them as additional `prompt_text` context → calls `generate_reply` |
| **Update hooks** post-generation | After generation, if user confirms / contradicts / repeats: increment vibration, rhythm_count, re-run RPM + inversion gates, persist |

## Safeguards (load-bearing — over-gravity is a real failure mode)

The risk: if a belief gets too much mass, every new user message
gets forced into an old pattern. The system becomes stubborn —
worse, it imposes hidden permanent assumptions about the user.
Necessary safeguards, in priority order:

1. **Vibration decay over time** — already in `vibration.py` (30-day
   half-life). A belief that hasn't been reinforced fades.
2. **User-confirmed vs model-inferred distinction** — the `sources`
   field already lists where each belief came from. Beliefs sourced
   from explicit user confirmation should weight differently from
   beliefs the model inferred. Add a `confirmation_kind` enum
   (e.g., `user_explicit`, `user_implicit`, `model_inferred`).
3. **Contradiction / inversion check** — when the candidate query
   conflicts with a high-mass belief on the inversion axes, lower
   that belief's gravity for this turn instead of injecting it.
   Reuses the existing `inversion_gate`.
4. **Low-confidence beliefs** — beliefs with low `vibration` or
   `rhythm_count` get exposure but cap their gravity contribution.
5. **Belief revision** — explicit API to revise / withdraw a belief
   when the user corrects the system. Store the revision history,
   don't silently overwrite.
6. **No hidden permanent assumptions** — the system surfaces, in
   any traceable output, which beliefs were used to shape the
   response. Mode 7 already exists for this in `cas-native/trace/`.
   The retrieval layer should hook into Mode 7 so the user can see
   "this answer was influenced by belief X with gravity Y."

## Demo scope (~200-300 LOC, no model retraining)

A working CABS retrieval demo that:

1. Adds the `simplex_vector` field to `Belief` and migrates the
   SQLite schema (idempotent migration; nullable column, populated
   on next write)
2. Adds `BeliefStore.search_by_proximity(query, k=3)` returning
   `[(belief, distance, gravity_score)]`
3. Adds `Belief.mass()` accessor and `gravity(belief, query)`
   helper in a new `cas-native/belief/gravity.py`
4. Adds context-injection glue in a new
   `cas-native/inference/cabs_retrieval.py` that:
   - takes a user utterance + cas_expression
   - encodes it to simplex
   - searches the store
   - filters by gravity threshold + inversion-conflict check
   - renders the surviving beliefs as additional context
5. Tests:
   - `test_belief_simplex_vector_persistence.py` — round-trip a
     belief with a simplex vector through SQLite
   - `test_belief_search_by_proximity.py` — synthetic store of
     5-10 beliefs with known simplex vectors; query nearest-3
     returns expected ordering by Fisher-Rao distance
   - `test_belief_gravity_scoring.py` — mass × distance composition
     produces the expected ranking; high-mass-far loses to
     low-mass-near at the right distance threshold
   - `test_cabs_retrieval_inversion_filter.py` — beliefs that fail
     the inversion check are dropped from injection
   - `test_cabs_retrieval_no_op_when_store_empty.py` — empty store
     produces no context injection, no errors
6. A small script `examples/cabs_retrieval_demo.py` that:
   - seeds 5-10 hand-curated beliefs into a temp store
   - runs 3 user utterances through the retrieval pipeline
   - prints which beliefs were retrieved + their gravity scores +
     the final injected context
   - lets a human eyeball whether the right beliefs are surfacing

The demo deliberately does **not** retrain the model. It wraps the
existing v1 PREFIX128 5ep checkpoint (or whatever's current at
that time) and injects belief context as plain prompt text. The
test of whether retrieval helps is whether replies become more
coherent and personally continuous on a small held-out conversation
sample.

## Test of success

Build a 5-utterance test conversation where each utterance shares
a structural pattern with prior utterances (e.g., "stuckness
triggered by memory + evaluation lock"). Run twice:

- **Without CABS retrieval**: vanilla v1 generation. Likely
  produces three independent translation-style answers.
- **With CABS retrieval**: the second and third answers should
  reference / build on the first answer's structural pattern, not
  re-derive it cold.

If the with-CABS run shows continuity ("this looks like the same
pattern as before") and the without-CABS run does not, the
retrieval layer earned its place.

## What this is not

- **Not a replacement for the model.** CABS sits around the
  generator, supplying context. The model still does the talking.
- **Not a long-term memory of every utterance.** Beliefs need
  RPM-gate clearance + inversion-clean status + sufficient
  vibration to lock. Casual one-off remarks don't enter CABS.
- **Not a fix for v1's generation hygiene problems.** Truncation,
  task misrouting, semantic drift on body content — those need
  the v1 audit's three immediate moves first. CABS layered on top
  of broken generation just propagates broken generation with
  better continuity.
- **Not silent.** Every retrieval-influenced response should
  surface its retrieval trace via Mode 7 so a user can see (and
  challenge) which beliefs shaped the answer.

## Slogan

*"Δ°₃₉ + Fisher-Rao gives thought-space physics. CABS gives
memory. Together they give CAS-Native continuity and idea
gravity."*

## Open questions to settle before building

1. Does the retrieval encoding use the same `SimplexStateEncoder`
   that the model trains on, or a frozen separate encoder? Sharing
   risks subtle distribution shift; freezing risks the encoder
   drifting out of sync with the model's internal state space over
   retrains. Recommend: shared but versioned (track which encoder
   weights produced each persisted simplex vector; re-encode on
   model retrains as a background migration).
2. What's the gravity threshold for context injection? Too low
   and irrelevant beliefs surface; too high and nothing surfaces
   on cold-start sessions. Likely needs a learned or empirically-
   tuned threshold based on the demo conversation results.
3. How many beliefs to inject at most? `k=3` is a reasonable
   starting default; needs measurement.
4. How to render injected beliefs as prompt context without
   triggering the model to over-anchor on them? Possible: a
   bracketed prefix `[CONTEXT: <claim_text>]` that the model
   learns to use as soft conditioning, not parrot.
5. When the retrieval surfaces a belief that has since been
   inversion-flagged, do we suppress silently or surface it as
   "this previously believed X but it now conflicts"? The
   safeguard list says surface; needs UX detail.
