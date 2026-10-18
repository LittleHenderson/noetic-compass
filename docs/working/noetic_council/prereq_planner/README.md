# Prerequisite-Graph Planner (`prereq_planner`)

Replaces naive keyword matching and hardcoded tool sequences with a formal prerequisite-graph planner.

Parses explicit prerequisites (Form 1: CCE `needs_first`) and temporal discourse markers (Form 2: `first...then`, `before`, `after`, `then`, `finally`), constructs a directed prerequisite graph, validates acyclicity and recursion horizon ($HORIZON=12$), sorts deterministically via Kahn's algorithm, and gates execution at every step via the RPM Gate.

---

## CLAIM CEILING

```
MECHANISM ONLY. ORDERING IS DERIVED FROM STATED PREREQUISITES. NO UNDERSTANDING OF THE REQUEST IS CLAIMED.
```

---

## WHAT THIS DOES NOT DO — Verbatim (§8 of Specification)

- It does **not** understand the request. It reads prerequisite sentences and temporal markers out of controlled English and builds edges from them. Nothing more.
- It does **not** invent a prerequisite. If a dependency was not stated, there is no edge, and `"order_source"` says so.
- It does **not** resolve a contradiction. A cycle is refused (`PLAN_CYCLE`).
- It does **not** claim topological planning of arbitrary tasks. It is prerequisite-graph ordering over $\Omega$ production targets, in a grammar that already has the edge and already round-trips it.
- **The steps it orders are tool actions, not recipe productions, until someone wires the tools to $\Omega$ targets.** Do not let the plan's $\Omega$ names imply the executor is doing stoichiometry.

---

## ARCHITECTURE & DATA MODEL

1. **`PlanNode`**:
   - `omega`: Production target byte-for-byte from request. Never guessed or normalized.
   - `recipe`: Parsed recipe content if declared.
   - `needs`: Tuple of prerequisite target names.
   - `depth`: Computed DAG depth ($0$ for leaves, $1 + \max(\text{depth}(\text{needs}))$).
   - `kind`: `'leaf'` if `needs == ()` else `'internal'`.
   - `vibration`: Priority integer for Kahn sort tie-breaking.

2. **`PlanEdge`**:
   - `before`: Node that must finish first.
   - `after`: Node that requires it.
   - `source`: Mandatory sentence that generated this edge. An edge without a source is an invented edge and is refused with `PLAN_EDGE_WITHOUT_SOURCE`.

3. **`PlanResult`**:
   - `nodes`: Topologically sorted tuple of `PlanNode`.
   - `edges`: Tuple of `PlanEdge`.
   - `order`: Tuple of omega names.
   - `order_source`: Tracking code (`CCE_PREREQUISITE`, `TEMPORAL_BEFORE`, `TEMPORAL_FIRST_THEN`, `TEMPORAL_SEQUENCE`, or `NONE`).
   - `digest`: Deterministic SHA-256 over canonical plan JSON.

4. **Self-Checking Execution (`plan_executor.py`)**:
   - Evaluates each node against `the_loop_v3/rpm_gate.py`.
   - If a prerequisite is missing, the gate answers `REPAIR` with `PREREQUISITE_MISSING`.
   - The executor immediately halts with `PLAN_ORDER_VIOLATION`. The order violation is proved by the gate, not local heuristics.
   - Updates `the_loop_v3/bias.py` working memory, asserting strict version increases via `check_version_increase()`.
   - Takes diagnostic ASOM readout (`ALIGNED`, etc.) for display only.

---

## TYPED REFUSALS (§6)

- `PLAN_EMPTY`: No production targets found in request.
- `PLAN_CYCLE`: Request contains contradictions (directed cycle); names all cycle members.
- `PLAN_HORIZON`: Recursion depth reaches or exceeds $HORIZON=12$; names 13th node.
- `PLAN_UNDECLARED_OMEGA`: Edge references target never declared in request.
- `PLAN_ORDER_VIOLATION`: RPM Gate returned `REPAIR` for a node positioned as ready.
- `PLAN_EDGE_WITHOUT_SOURCE`: Prerequisite edge has empty source sentence.
- `PLAN_REPAIR_FAILED`: Mid-plan execution failure could not be closed by `repair_performer`.
