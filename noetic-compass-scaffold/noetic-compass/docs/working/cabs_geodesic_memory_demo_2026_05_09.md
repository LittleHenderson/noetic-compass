# CABS Geodesic Memory Demo

Status: partial implementation of the CABS gravity retrieval design.

Related design doc:

`noetic-compass-scaffold/noetic-compass/docs/working/cabs_gravity_retrieval_layer_2026_05_09.md`

## Evidence Level

This is **written + tested math substrate**, not a full CABS retrieval
integration. It intentionally does not wire into `chat.py`, inference, SQLite
persistence, or Mode 7 tracing.

The v1 hygiene queue remains ahead of full integration:

1. Fix truncation / EOS behavior.
2. Wire the compilability gate at inference.
3. Re-grade with a 20-30 record human sample.

The geodesic layer was started in parallel because it is isolated and does not
change runtime behavior. That ordering choice is documented here so future
sessions do not treat v1 hygiene as completed.

## What This Adds

The CABS store already tracks belief strength through vibration, rhythm, RPM,
and inversion gates. The new geodesic memory layer adds the missing geometry:

- each projected memory carries a 40-state CAS simplex vector;
- Fisher-Rao distance measures nearness in CAS thought-space;
- belief mass is derived from vibration + rhythm, with a conservative locked
  belief boost;
- retrieval ranks memories by `effective_mass / distance`;
- top retrieved beliefs can be rendered as a compact context block for later
  generation.

## What Is Deferred

- `simplex_vector` field on persisted `Belief`
- SQLite schema migration
- `BeliefStore.search_by_proximity(...)`
- query-time vibration decay
- inversion / contradiction filtering during retrieval
- `confirmation_kind`: `user_explicit`, `user_implicit`, `model_inferred`
- belief revision API
- Mode 7 retrieval trace hook
- context injection into inference/chat

## Intended Pipeline

1. Convert the current user utterance into a CAS simplex vector.
2. Project existing CABS beliefs into `GeodesicBelief` records.
3. Rank them with `retrieve_by_geodesic_gravity`.
4. Feed `render_retrieval_context(top_results)` to the generator.
5. After the answer, reinforce or contradict beliefs through `BeliefStore`.

## Why This Matters

The model should not treat every user prompt as an isolated translation job.
CABS geodesic retrieval gives ideas memory mass. A repeated, confirmed belief
near the current prompt pulls the response harder than a weak or distant belief.

This is the first concrete step toward "ideas have gravity" in CAS-Native.

## Guardrail

High mass can become over-gravity. Later integration must keep:

- confidence visible,
- locked vs candidate status visible,
- contradiction and inversion gates active,
- user correction able to reduce or overturn a belief.
