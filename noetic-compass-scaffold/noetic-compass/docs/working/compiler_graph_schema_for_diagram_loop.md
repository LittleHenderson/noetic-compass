# Compiler Graph Schema — Diagram-Loop Lever

**Author**: Claude Code (Session — diagram-loop-impl)
**Date**: 2026-05-03
**Purpose**: Document the typed graph schema produced by `api/notation/compiler.py`
so the diagram-loop lever can encode it as ML-friendly tensor input.

---

## 1. Callable Python API

The stable entry point is `CASCompiler` in `api/notation/compiler.py`:

```python
import sys
sys.path.insert(0, str(project_root))     # project root must be in sys.path
from api.notation.compiler import CASCompiler

result = CASCompiler(cas_expression_string).compile()
if result.valid:
    diagram = result.diagram()            # → dict (see §2 below)
else:
    diagram = None                        # compile error, fall back to empty
```

`result.diagram()` delegates to `build_diagram(result.ast)` which calls
`_DiagramBuilder().walk(ast)` and returns `_DiagramBuilder.to_dict()`.

**No separate `compile_to_graph` function exists** on master; the serialization
module (`diagram_serialization.py`) wraps this API.

---

## 2. Diagram dict schema

`result.diagram()` returns:

```python
{
    "kind": "cas_diagram",
    "schema_version": "1.0",
    "layouts": ["semantic", ...],   # sorted list of layout hints (strings)
    "nodes":  [...],                # list of node dicts
    "edges":  [...],                # list of edge dicts
    "containers": [...],            # list of container dicts (logical groupings)
}
```

### 2.1 Node dict

```python
{
    "id": "state:E4_F2|E",         # unique within diagram, string slug
    "kind": "<node_kind>",          # see NODE_KINDS below
    "label": "<human-readable>",
    "role": "<role_string>",        # optional
    # optional CAS-axis attrs (present when applicable):
    "operator": 4,                  # int 0-9, Noetic operator index
    "noetic": "CO-4",               # string alias, always = f"CO-{operator}"
    "domain": "E",                  # "P" | "C" | "E" | "O"
    "drive": "F2",                  # "F1"–"F7" string
    "register": "E",                # str | tuple[str,...] | None
                                    #   str = single register ("T","A","f","E")
                                    #   tuple = register-set e.g. ("A","f","T")
    "step": 1,                      # int, fractal sequence position (fractal nodes only)
    "activation": 0.5,              # float, state-vector weight (state_vector edges)
    "coefficient": 0.3,             # float, recipe weight (recipe_prerequisite edges)
    "arity": 3,                     # int, tuple/function arity
    "cardinality": 40,              # int, meta_set cardinality
    "expanded": True,               # bool, meta_set expansion flag
    "statement_count": 2,           # int, program node
}
```

### 2.2 Node kind vocabulary (NODE_KINDS)

```
"noetic"            atomic Noetic operator CO-0..CO-9
"state"             full cognitive state with domain (and optionally drive, register)
"drive"             Core Drive F1-F7 (optionally with domain or register)
"domain"            Processing Domain P/C/E/O
"register"          Phenomenological Register T/A/f/E
"state_variant"     state with register variant (StateVariantSet)
"operator"          binary/unary CAS operator node (+, ×, ÷, ∘, etc.)
"emergent"          EmergentResult (named Ω target of cross-register integration)
"coordinate"        CASCoordinate / Coordinate tuple
"tuple"             Tuple literal (non-coordinate)
"cardinality"       |X| cardinality expression
"rpm_stage"         A0/Dn/Wn/Pn node in RPM chain
"rpm"               RPM(...) call without explicit drive
"production_target" Omega_* production target literal
"catalyst"          κ catalyst in recipe
"inhibitor"         ι inhibitor in recipe
"state_vector"      S state-vector literal
"yield"             Y_T / Y_A yield expression
"program"           root program node (multi-statement)
"function"          fn definition
"module"            use import
"symbol"            domain/register MetaSymbol (bare letter)
"subfoundation"     sub-foundation set element
"foundation"        foundation family element
"relation"          relation element in RelationCluster
```

Container kinds (from `containers` list, not `nodes`):
```
"meta_set"               Noetics/Domains/Registers/etc.
"noetic_cluster"         NoeticCluster{...} or NoeticSet{...}
"state_cluster"          StateSet{...} or StateCluster{...}
"state_variant_cluster"  StateVariantSet{...} or StateVariantCluster{...}
"relation_cluster"       RelationCluster{...} or RelationSet{...}
"typed_meta_set"         other TypedMetaSetLiteral kinds
```

### 2.3 Edge dict

```python
{
    "id": "edge:1",
    "source": "<node_id>",
    "target": "<node_id>",
    "kind": "<edge_kind>",
    "directed": True,
    "label": "<display label>",    # optional
    "coefficient": 0.3,            # optional, recipe_prerequisite edges
    "activation": 0.5,             # optional, activation edges
}
```

### 2.4 Edge kind vocabulary (EDGE_KINDS)

```
"instantiates"        noetic → state (Noetic operator instantiates a state)
"locates"             domain → state (Domain locates a state)
"modulates"           drive → state (Drive modulates a state)
"register"            register → state (Register attaches to a state)
"dependency"          left → right (→ relation, RPM chain, causal)
"results_from"        right ← left (← relation)
"bidirectional"       left ↔ right (undirected relation)
"operand"             operand → binary_op node
"fractal_step"        op_i → op_{i+1} in fractal sequence
"rpm_descent"         A0→D→W→P prerequisite chain (section retraction)
"rpm_query"           state → RPM node (query entry)
"emerges_as"          integration_node → emergent (= named result)
"statement"           program → statement child
"tuple_slot"          element → tuple (positional slot)
"membership"          element ∈ set
"proper_subset"       A ⊂ B
"subset"              A ⊆ B
"proper_superset"     A ⊃ B
"superset"            A ⊇ B
"equals"              A = B
"recipe_prerequisite" state → production_target (weighted, coefficient attr)
"catalyst"            catalyst → production_target
"inhibitor"           inhibitor → production_target
"leakage"             target → side_product
"activation"          state → state_vector (weighted, activation attr)
"yield_query"         target → yield node
"yield_input"         state/recipe → yield node
"cardinality"         collection → cardinality node
"product_axis"        element → Product call
"cover_base"          base → CoverOf call
"cover_member"        member → CoverOf call
"partition_base"      base → PartitionOf call
"partition_member"    member → PartitionOf call
"pullback_leg"        element → Pullback call
"argument"            arg → generic function call
```

---

## 3. Concrete walk-through: `(^4^E_{F2}|E × ^4^E_{F2}|f × ^4^E_{F2}|A) = ^4^E|Ω_attunement`

This expression parses as:
```
EmergentResult(
    inner=BinaryExpr(TIMES,
        left=BinaryExpr(TIMES,
            left=StateLiteral(op=4, domain="E", drive=2, register="E"),
            right=StateLiteral(op=4, domain="E", drive=2, register="f")),
        right=StateLiteral(op=4, domain="E", drive=2, register="A")),
    assigned_name="^4^E|Ω_attunement")
```

**Nodes produced**:
- `state:E4_F2|E`   kind=state, operator=4, domain="E", drive="F2", register="E"
- `noetic:CO-4`     kind=noetic, operator=4
- `domain:E`        kind=domain
- `drive:F2`        kind=drive
- `register:E`      kind=register
- `state:E4_F2|f`   kind=state, operator=4, domain="E", drive="F2", register="f"
- `register:f`      kind=register
- `state:E4_F2|A`   kind=state, operator=4, domain="E", drive="F2", register="A"
- `register:A`      kind=register
- `operator:1`      kind=operator, label="×" (inner ×)
- `operator:2`      kind=operator, label="×" (outer ×)
- `emergent:^4^E|Ω_attunement`  kind=emergent, label="^4^E|Ω_attunement"

(Plus noetic/domain/drive nodes for states 2 and 3 if not deduped — the builder
uses `nodes.setdefault` so deduplication happens by `node_id`.)

**Edges produced**:
- `noetic:CO-4` → `state:E4_F2|E`  kind="instantiates"
- `domain:E` → `state:E4_F2|E`      kind="locates"
- `drive:F2` → `state:E4_F2|E`      kind="modulates"
- `register:E` → `state:E4_F2|E`    kind="register"
- (similar for state 2 and 3)
- `state:E4_F2|E` → `operator:1`    kind="operand", label="left"
- `state:E4_F2|f` → `operator:1`    kind="operand", label="right"
- `operator:1` → `operator:2`        kind="operand", label="left"
- `state:E4_F2|A` → `operator:2`    kind="operand", label="right"
- `operator:2` → `emergent:...`      kind="emerges_as", label="="

---

## 4. Node feature encoding for ML (NODE_FEATURE_DIM = 48)

Defined in `diagram_serialization.py`:

| Slice       | Dims | Encoding |
|-------------|-----:|----------|
| node_kind   | 23   | one-hot over NODE_KINDS (last dim = "other") |
| noetic      | 10   | one-hot, index = `node["operator"]` if present else zeros |
| domain      | 4    | one-hot over P/C/E/O from `node["domain"]` if present |
| drive       | 7    | one-hot over F1-F7 from `node["drive"]` if present |
| register    | 4    | multi-hot over T/A/f/E from `node["register"]` if present |
| **Total**   | **48** | |

Register is multi-hot because a node can carry a register-set `("A","f","T")`.

## 5. Edge feature encoding (EDGE_FEATURE_DIM = 34)

One-hot over EDGE_KINDS (33 kinds + 1 "other" = 34 dims).

---

## 6. Stable API gap assessment

**`compile_to_graph` does NOT exist on master.** The diagram-loop serialization
module adds it as a thin wrapper around `CASCompiler(...).compile().diagram()`.
No changes to the compiler are required.

The `build_diagram` and `empty_diagram` functions are importable from
`api.notation.compiler` directly if needed, but `CASCompiler.diagram()` is the
recommended entry point as it handles the `valid` check.

---

## 7. Containers vs nodes

The diagram dict separates `nodes` (atomic elements) from `containers` (logical
groupings like `NoeticCluster{^2, ^7}`). For the ML encoder:

- **Containers are skipped** in Phase 2 serialization — they are grouping
  annotations used by the dashboard renderer, not structural graph nodes that
  carry CAS-axis signal.
- **Only `nodes` and `edges` are encoded** into tensor input for the
  `GraphEncoder`.

This simplification is correct for the structural-prediction task: the content
heads (noetic/domain/drive/registers) are resolved by state-level features, not
by which cluster a state belongs to.
