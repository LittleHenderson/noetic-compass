# Idea Atlas — Spec and Roadmap

Status: Working draft
Owner: Founder (Little Henderson) + Sprint 1 build team (agents E, F, G)
Author: Agent H (spec/roadmap)
Date: 2026-04-26
Working name: Idea Atlas

---

## 1. Product vision

Idea Atlas is a graph-based personal cognitive map. The user captures ideas (notes, observations, beliefs, fragments, questions, claims) the way they would in any modern PKM tool — but every captured idea is CASivenized: the system produces a CAS expression for the idea using the authoritative CAS v7.7 notation (Noetic, Domain, Drive, Register, with production-semantic recipes available where applicable). The CAS expression is the idea's first-class structural fingerprint. Everything else in the product is downstream of that fingerprint.

Existing tools — Obsidian, Roam, Logseq, Tana, Heptabase — link ideas by wiki-style backlinks, hashtags, manual relationship typing, or proximity in an outliner. The link is a string match or a hand-drawn arrow. Idea Atlas links by cognitive structure: two ideas connect because their CAS expressions are structurally near, not because the user remembered to type `[[that other note]]`. The graph is grown by the framework, not by the user's discipline. Inversion, lacunarity, register conflict, and production-recipe overlap are all first-class graph operators rather than ornaments on top of plain text.

The differentiator therefore is not "graph PKM" (the category exists), nor "AI-assisted PKM" (LLM tagging is commodity). The differentiator is that Idea Atlas links by cognitive architecture, with a defensible, founder-authored formal framework (CAS v7.7) underneath every edge and every node. The same CAS layer that powers the Noetic Compass assessment platform powers the user's personal map: an idea in the map is the same kind of object as a state in an incident analysis or a node in a scenario evaluation.

Target use cases (founder-stated): (a) PKM with a cognitive-architecture backbone — the user's second brain literally has architecture; (b) therapy and self-work — surface inversions, lacunae, and recurring recipes in lived experience; (c) research — see structural neighbors across disparate domains; (d) creative work — find ideas adjacent in cognitive shape rather than topic; (e) AI alignment research — instrument the researcher's own model of the field; (f) policy and decision-making — recipe ingredients become explicit and limiting reagents become diagnosable.

---

## 2. Component inventory

The user's spec names seven components. Each is listed with a one-line description, reusable repo infrastructure, and target sprint.

### 2.1 CASivenizer
- One-line: turns natural-language idea into a validated CAS v7.7 expression.
- Reuse: `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py` (`compile_expression`) already validates CAS expressions against the authoritative grammar; `api/routes/notation.py` already exposes a notation-compile route; LLM connectors live under `api/llm_connectors/` (per CLAUDE.md Phase 2 plan). v7.7 register/operator discipline lives in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10.
- Sprint: Sprint 1 (LLM-mock + compiler-validate); production LLM in Sprint 2.

### 2.2 Similarity metric
- One-line: scalar similarity score over two CAS expressions (Noetic, Domain, Drive, Register, MetaSet feature vectors).
- Reuse: feature extraction can lean on the compiler AST; cosine implementation has no repo dependency; the v7.5/v7.6/v7.7 axis structure (10 Noetics, 4 Domains, 7 Drives, 4 Registers) gives a fixed-dimensional vector by construction.
- Sprint: Sprint 1 (Agent G owns design and implementation).

### 2.3 Graph engine
- One-line: nodes are CASivenized ideas; edges are similarity-weighted; queryable for neighbors / inversion-pairs / shared-Ω recipes.
- Reuse: SQLAlchemy + PostgreSQL already wired (`api/store.py`, `api/models_db.py`); JWT auth middleware already exists (`api/main.py`); graph is computed at query time from relational rows in Sprint 1 — no graph DB needed yet.
- Sprint: Sprint 1 (persistence + `GET /ideas`); Sprint 2 (graph rendering).

### 2.4 Inversion engine
- One-line: given a node's CAS expression, produce its inversion (operator-level, drive-level, axis-level) per the 7 Inversion Axes in CAS v7.7.
- Reuse: the founder's external `tootra-tks` engine is referenced in the v7.6/v7.7 product spec but is NOT present in this repo as of 2026-04-26 (grep returns hits only in the IP timeline docs and CHANGELOGs, not in source). Flagged as **external dependency to integrate in Sprint 3**. Until then, Sprint 2 may stub inversion using the involution pairs hard-coded in CAS v7.7 (CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9, F1↔F7, F2↔F6, F3↔F5).
- Sprint: Sprint 3 (full); Sprint 2 (stub for UI scaffolding).

### 2.5 Ripple propagation
- One-line: when a node is inverted (or significantly mutated), neighboring nodes shift along the similarity-weighted graph; UI animates the propagation.
- Reuse: no direct reuse; depends on the similarity metric (2.2) and the inversion engine (2.4). Half-life parameter is open research (see Section 5).
- Sprint: Sprint 3.

### 2.6 Persistent storage
- One-line: durable store of ideas, CAS expressions, similarity edges, user metadata, snapshots.
- Reuse: PostgreSQL via SQLAlchemy already configured in `api/store.py` and `api/models_db.py`; migrations conventionally Alembic-driven. The Idea Atlas adds two tables (`ideas`, `idea_edges`) and one optional snapshot table; no new DB engine needed.
- Sprint: Sprint 1.

### 2.7 UI / UX
- One-line: capture page, list view, graph view, node-inspect panel, inversion controls.
- Reuse: React 18 + TypeScript dashboard at `noetic-compass-scaffold/noetic-compass/dashboard/`; routing and lazy-loading already established (`src/pages/CompilerPage.tsx` is a precedent); `recharts` is installed and pulls in `d3-*` packages, so D3 is already a transitive dep. Auth on the dashboard side already wired.
- Sprint: Sprint 1 (capture + list); Sprint 2 (graph + inspect); Sprint 3 (inversion UI + ripple animation).

---

## 3. Sprint plan

### Sprint 1 — capture, CASivenize, persist, list (current sprint)
Owners: Agent E (backend), Agent F (frontend), Agent G (similarity metric).
- Deliverables:
  - `POST /idea-atlas/casivenize` — accepts NL text, returns validated CAS expression (LLM-mock proposes, compiler validates).
  - `POST /idea-atlas/ideas` — persists `{text, cas_expression, feature_vector, created_at, user_id}`.
  - `GET /idea-atlas/ideas` — paginated list of the user's captured ideas.
  - Similarity metric module: cosine over weighted Noetic/Domain/Drive/Register/MetaSet feature vectors. Unit tests on at least 20 synthetic pairs.
  - Frontend `/idea-atlas` route: capture textarea, submit, display CAS expression, show running list of captured ideas with their CAS expressions.
- End state: user can capture ideas, see CAS, list captured ideas. **No graph view yet.**
- Effort: 4-6 days across the three agents, parallel.
- Dependencies: none (all infra present).

### Sprint 2 — graph rendering
- Deliverables:
  - `GET /idea-atlas/graph` — computes nodes + similarity edges from the ideas table; thresholded edge weights to avoid `O(n^2)` clutter.
  - D3.js force-directed graph component on `/idea-atlas`; toggle between list view and graph view.
  - Click-to-inspect node panel: full text, CAS expression, top-K similar nodes, top-K dissimilar nodes.
  - Promote the LLM-mock CASivenizer to a real LLM connector (OpenAI or Anthropic via existing connector framework).
  - Stub inversion endpoint returning canonical involution-pair flips (no full inversion engine yet).
- Effort: 6-8 days.
- Dependencies: Sprint 1 ideas table; LLM connector framework from Phase 2 of the master plan.

### Sprint 3 — inversion + ripple
- Deliverables:
  - Integrate `tootra-tks` inversion engine (external — must be vendored or wrapped before sprint start).
  - Inversion UI on the node-inspect panel: "show inversion," side-by-side, "apply inversion as new node."
  - Ripple animation: when a node is inverted, animate similarity-weighted neighbors along a configurable half-life.
  - Snapshot table — record graph state at user-triggered moments for therapy/self-work history.
- Effort: 8-12 days.
- Dependencies: `tootra-tks` integration done before sprint start (blocker); Sprint 2 graph view; ripple half-life from open-research item 5.4.

### Sprint 4+ — extensions
- Deliverables (ordered by founder priority, not by dependency):
  - Voice capture (browser SpeechRecognition + LLM cleanup).
  - Mobile-first capture page (PWA).
  - Sharing / collaboration (per-graph ACLs; public read links; comment threads).
  - CAS-Native v2 integration when training completes — replace LLM CASivenizer with the in-house model; eliminates the LLM-validate round-trip.
  - Production-semantic recipe overlay: visualize Ω targets and limiting reagents as graph annotations.
- Effort: open-ended; each item is a 5-15 day bundle.
- Dependencies: CAS-Native v2 training completion (Phase 4 of master plan, months 6-24); voice capture has no blockers; sharing requires an auth-tenant story we do not yet have.

---

## 4. Architecture decisions (Sprint 1)

Each decision below is what the build agents are committing to in Sprint 1, with reasoning and revisit conditions.

- **Persistence: PostgreSQL via SQLAlchemy (NOT Neo4j).** The graph layer is computed at query time from the relational `ideas` and `idea_edges` tables. Reasoning: the repo already runs PostgreSQL/SQLAlchemy; introducing Neo4j is an ops cost the product does not yet need; query-time graph computation is fast enough for the capture-and-list workload of Sprint 1 and the rendering workload of Sprint 2 at the founder's expected node count. Revisit if read perf degrades at 1000+ nodes per user, or if graph algorithms (PageRank, community detection) become hot-path features.

- **CASivenizer: hybrid LLM-proposes-then-compiler-validates (option D in the user's spec).** Sprint 1 ships an LLM-mock (deterministic stub returning canned CAS for fixture inputs) + the existing `compile_expression` validator. Sprint 2 swaps the mock for a production LLM connector (OpenAI/Anthropic via `api/llm_connectors/`). Reasoning: the compiler is the source of truth; the LLM is a proposal generator; validation guarantees no malformed CAS reaches the database.

- **Similarity: cosine on weighted Noetic / Domain / Drive / Register / MetaSet feature vectors (Agent G's design).** Inversion-pair noetics are treated as neutral by default (similarity contribution = 0 between, e.g., `^2` and `^3`), with the option to flip to anti-similar via configuration. Reasoning: structurally, involution pairs are duals — making them anti-similar by default would force the graph into a bipartite shape that distorts neighbor topology; making them similar by default conflates opposite cognitive moves; neutral is the least committal choice consistent with the open research question in 5.1.

- **Graph layout: D3.js force-directed in the browser.** Cytoscape.js, Sigma.js, and vis.js were considered. D3 was picked because the dashboard already has `d3-*` packages as transitive deps via `recharts`, so no new top-level dependency is added. Reasoning: minimize surface area in Sprint 1/2; the force-directed layout is well-understood and matches the product mental model. Revisit if scale exceeds 2000 nodes per graph (force-directed perf cliff) or if WebGL rendering becomes necessary — Sigma.js is the likely successor.

- **Frontend route: `/idea-atlas`, lazy-loaded.** Same lazy-load pattern as `/compiler` in the existing dashboard. Reasoning: keeps the main bundle small; the Idea Atlas is a heavy view (D3 + state) that most assessment-focused users will never open.

---

## 5. Open research questions

Each item is a candidate for a future research note, experiment, or paper. They are NOT blockers for Sprint 1 — Sprint 1 ships defaults — but they are blockers for any claim that Idea Atlas similarity is principled rather than tuned.

### 5.1 Involution-pair similarity
Should involution-pair Noetics (`^2`/`^3`, `^5`/`^6`, `^8`/`^9`) be treated as similar (because they share a structural dimension), anti-similar (because they are duals), or neutral (current default)? Different answers yield different graph topologies and different ripple dynamics. Likely answered empirically: hold-out a set of user-tagged "these belong together" pairs and learn which treatment best predicts user judgment.

### 5.2 Production-semantic similarity weighting
Two ideas may share a `Θ(Ω)` recipe target (CAS v7.6 production semantics) without sharing any Noetic/Domain/Drive surface. Does shared Ω deserve its own weight in the similarity vector — and if so, how is Ω-equivalence detected, given that recipes are user-specified? Possibly addressed by recipe-clustering rather than a flat weight.

### 5.3 Register interaction with similarity
Same content in different registers (`^3^P|A` vs `^3^P|f` vs `^3^P|T`) — how similar are these? CAS v7.7 Clarification 10 distinguishes register-set occupancy, co-presence, and cross-register integration. The similarity metric must take a position. Sprint 1 default: same Noetic/Domain/Drive but different register = high similarity (≈0.85). Sprint 2 or later: validate against user judgment.

### 5.4 Inversion ripple half-life
When a node is inverted, what fraction of similarity-weighted neighbors should also visibly move, and over what half-life? Too aggressive and the graph becomes incoherent on every edit; too conservative and inversion looks like a local effect when it is actually structural. Hypothesis: half-life proportional to `1 / mean_edge_weight_to_inverted_node`. Needs an empirical study with synthetic graphs of known structure.

---

## 6. Naming

Working name: **Idea Atlas**.
Founder's other candidates: "Cognitive Atlas," "CAS Map."
Recommendation: **keep "Idea Atlas"** — it foregrounds the user-facing object (ideas) rather than the framework (CAS) or the vocabulary the user does not yet know (cognitive architecture); "Atlas" preserves the navigational metaphor; it generalizes cleanly to non-technical audiences in a way "CAS Map" does not.
