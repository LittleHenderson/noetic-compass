# Provenance Record -- `prereq_planner`

Built according to `SPEC_PREREQUISITE_GRAPH_PLANNER_20261018.md`.

## Vendored Dependencies
- `language_v3/cce.py`: `cce.parse()` for CCE Form 1 prerequisite relations (`needs_first`)
- `dwp_engine_v2/depth.py`: `depth.check_depth()`, `HORIZON = 12` (owner's ruling of 2026-10-16)
- `the_loop_v3/rpm_gate.py`: `rpm_gate()`, `RpmCause`, `GateVerdict` (`PROCEED`, `REPAIR`, `REFUSE`)
- `the_loop_v3/bias.py`: `Bias`, `check_version_increase()`
- `the_loop_v3/asom.py`: `readout()` (display only; never gates)
- `repair_performer/actor.py`: `perform_repair()` (mid-plan single repair)

## Package Files and SHA-256 Digests
| File | Bytes | SHA-256 |
| --- | --- | --- |
| `plan_graph.py` | 14574 | `a3fa0599361695760c95a61a51ef9d74a8b2504324a465784a5217318230f6df` |
| `plan_executor.py` | 8513 | `a3571251b7e5488898aa409a0c2739927b61e258ca9eae4a73022fa2468c5d82` |
| `test_all.py` | 11882 | `bf470b97ab80b4fb7fd1cc734c61ccf19df6a3fbed1c5d3a7fafca6844a3c49f` |
| `README.md` | 3642 | `0da3989bea3b0b6b86d7a1a482f9708727431b352b1f8206849b4f8170edec3d` |
| `PLAN_EXAMPLE.txt` | 1041 | `c40dd5465f5149d8c2295a75d407a584c40d6e71746aef86ee85c10816e43e13` |
