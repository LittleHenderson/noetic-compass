# Unified Cube Store (`cube_store`)

Implements `SPEC_CUBE_STORE_UNIFIED_20261018.md`, extending `Cube_Node_Schema_v0.1.md` with:
- One cube store, three operations (`LIST_PARTS`, `FIND_SHARED_PART`, `REACHED_VIA`), two producers (curriculum teaching and interactive conversation).
- The five additions:
  1. `core.kind` gains `"directive"` (concept | instance | event | procedure | directive).
  2. `turn_index`: integer recording conversational temporal order.
  3. `confidence`: object | null (separate from availability; unknown != uncertain).
  4. `provenance.source`: `"USER_SAID"` | `"AUTHORED"` | `"CHECKED"` | `"NONE"`.
  5. Orthogonal `assertion` ("ASSERTED" | "DENIED") and `valence` ("POSITIVE" | "NEGATIVE" | "NEUTRAL"), with legacy `polarity` preserved as a deprecated compatibility alias. Valence comes from the frozen ALIAS-WIDE lexicon and the Noetic ^2/^3 frames. Affect words outside the lexicon resolve to NEUTRAL and are not guessed.
- Six things not to build: no new parser, no new polarity, no new visibility system, no neural weights, no 3D renderer, no schema fork.

### CLAIM CEILING
MECHANISM ONLY.
KNOWLEDGE IS STORED AS CUBES; ANSWERS COME FROM THREE OPERATIONS OVER THAT STORE.
AN UNKNOWN FACE IS REPORTED AS UNKNOWN AND IS NEVER FILLED.
NO UNDERSTANDING OF THE REQUEST IS CLAIMED.

### Measured Metrics
- `answer_trace_rate`: **1.0** (every answered turn cites the operation run and cube(s) read).
- `S3_paraphrase_equivalence`: **1.0** (`"What do we have in stock"` and `"what've we got on hand then"` execute identical `LIST_PARTS` operations and return identical answers).
- `K8_lexical_valence_honest_boundary`: **1.0** (words outside the frozen ALIAS-WIDE lexicon resolve honestly to `NEUTRAL` without guessing).
- `H4_honesty_compliance`: **1.0** (ungrounded domains like `"Study medieval poetry"` emit no fabricated thermal inputs and are strictly refused).
