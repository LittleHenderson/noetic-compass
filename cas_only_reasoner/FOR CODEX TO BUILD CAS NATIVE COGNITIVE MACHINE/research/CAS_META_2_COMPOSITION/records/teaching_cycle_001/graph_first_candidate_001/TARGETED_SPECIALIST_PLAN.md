# Targeted ^6 specialist plan — graph-first whole–part teaching (design only)

Status: **DESIGN ONLY.** No training has been performed, no trainer was
modified, no AWS job exists, and no reservation was made. This plan names the
real registered module the owner directed us to target and the exact gates a
future authorized run must pass. Any paid run requires a separate owner
authorization (new job, new reservation).

## 1. What is targeted

- **Neural module:** the `decompose` operation registered in
  `cas_cjt/neural.py` `OPERATION_REGISTRATIONS` — relation_index 0, admission
  `CANONICAL_ADMITTED`, contract `cas.cjt.operation.^6.decompose/0.2`.
- **Permitted parameters:** only the plasticity group admitted by the
  operation contract (fixture/registry role `operator.^6`), resolved through
  `cas_cjt/learning.py` `_resolve_plasticity_groups` (groups scoped to the
  Bias CJT; nothing outside the admit list may change).
- **Frozen:** every other parameter group of the decompose module and all
  other modules (binding selector, other operations, embeddings, tokenizer).
- **Adapter option (if the module has no free head to train):** a small
  trainable adapter attached at the module's interfaces; original weights
  preserved. This is the established freezing-plus-adapter technique, not a
  claim that the current module already knows graph containment.

Claim vocabulary: success means "a learned capability of the selected module
working through its interfaces", never "the concept lives in these neurons".

## 2. The job the specialist learns

> Given an idea and its available structure, identify its constituent ideas
> and their relationships.

Structured requests (no unrestricted English in lesson 1):

| Request | Expected behavior in the bicycle/cart/wheel graph |
|---|---|
| `LIST_PARTS(bicycle)` | wheel, frame, pedals |
| `FIND_SHARED_PART(bicycle, cart)` | wheel |
| `LIST_PARTS(wheel)` | rim, hub, spokes |
| `REACHED_VIA(hub, bicycle)` | `via:wheel` (not directly inside) |

The shared `wheel` is the common sub-idea; the module must learn to FIND that
relationship, not repeat the word. Later lessons change objects, parts, names,
and layout; some pairs share a part, others share none; direct containment and
containment through another constituent are taught separately. First objective:
reading and using SUPPLIED structure (graph extraction from ordinary language
is a later skill).

## 3. Learning path (one update cycle)

1. Graph and structured request enter the targeted module.
2. The module predicts a part, relationship, or path.
3. The deterministic checker (`cas_meta2/graph_teaching/reference.py`)
   compares the prediction with the training answer. The graph supplies facts;
   the checker supplies corrective feedback. The module makes the selection
   itself — the checker never answers on its behalf, and the graph contains no
   answer edge.
4. Training error updates ONLY the designated parameter group.
5. Another worked example reinforces the relationship (repeated guided
   phase intact; worked answers and corrections precede independent testing).

## 4. Verification gates (both, separately)

**Specialization.** After guided teaching, the specialist must handle fresh
graphs, shuffled node positions, unfamiliar name/style combinations, and
nested containment (the REACHED_VIA cases) — measured on the sealed
validation/test splits of `cas_meta2/graph_teaching` only.

**Containment of the update.** Compare parameter records before and after;
only permit-listed groups may differ. Then retest neighboring skills (binding
selection and any other operation) through their interfaces. Fixed weights do
not logically guarantee unchanged behavior — neighbors receive different
outputs from the retrained module — so the neighbor retest is behavioral, not
a weight check.

## 5. Relation to other work

- The existing input-binding protocol trains the binding SELECTOR and leaves
  the internal ^6 operation untrained; this plan trains the ^6 module itself.
  That is a change in what receives the teaching, not just lesson wording.
- This plan complements, does not replace, the pending binding-fit diagnosis
  (attempt 004 authorization request still awaiting owner signature).

## 6. What does NOT exist yet (honest gap list)

- No trainer mode for the targeted module exists in this repository; the
  graph-teaching package ships curriculum + checker only.
- No run adapter (AWS), no reservation, no owner authorization for training
  the ^6 specialist.
- No integration with `gpu_adapter` / governed learning has been exercised
  against these exercises.
Before any AWS training is proposed, a trainer mode must be built and pass
pure tests with injected tensors, then be preregistered and owner-authorized —
exactly like every other claim-bearing run in this campaign.
