# Graph-first teaching candidate — preregistration (pure phase)

Status: **DESIGNED_AND_PURE_TESTED, NOT_TRAINED.** No neural run of any kind
has occurred; no AWS launch; no reservation; the campaign ledger is untouched.

## Frozen candidate identity

- Package: `cas_meta2/graph_teaching/` (graph, reference, lessons).
- Design record: `DESIGN.md` (four pieces; branches = connectors; connector
  content = commonality of the two adjacent nodes; no limit on node
  connectors/contents).
- Targeted-module plan: `TARGETED_SPECIALIST_PLAN.md` (contract
  `cas.cjt.operation.^6.decompose/0.2`, plasticity group `operator.^6`,
  everything else frozen).
- Dataset: `dataset_001/` (train / practice / validation / test), generated
  with seed `20260909`, byte-fixed by `receipt.json`.

## Frozen discipline

1. Only `train` and `practice` may ever be shown to a learner.
2. `validation` and `test` are sealed and disjoint; nothing in the package
   reads them.
3. No answer edges: the checker computes every answer; validation rejects
   forbidden kinds and any connector content that is not the endpoints'
   commonality.
4. Derived connectors (`shares`, `produced_by`) are never stored.
5. CAS and generic framings share identical graph bytes and identical
   reference answers; only CAS adds the three Noetic questions.

## Pure evidence (deterministic, no GPU, no network)

- `tests/test_graph_teaching.py`: 20 tests, all passing — graph invariants,
  branch-is-connector, relabel preservation, contents-change semantics,
  commonality derivation, no-answer-edge sweep, split disjointness and
  determinism, golden-thread derivation labels, CAS/generic equivalence,
  dataset receipt stability, and the owner's bicycle/cart/wheel example.

## Not authorized / not done

- No trainer mode for the targeted module exists yet (gap list in
  `TARGETED_SPECIALIST_PLAN.md` section 6).
- No AWS run is authorized for this candidate.
- The binding-fit attempt-004 authorization request remains awaiting the
  owner's signature, unchanged by this candidate.
