# CAS-META-0 / CASformer v0.3 WIP boundary

## Mandatory status

```text
WIP
UNREVIEWED
NOT PART OF V0.2
NOT CLAIM-BEARING
NO TRAINING AUTHORIZED
DO NOT MERGE INTO THE V0.2 RELEASE
```

This checkpoint preserves the supplied meta-logic design without changing the reproduced CASformer v0.2 baseline. A repository and worktree audit found no existing meta-logic runtime implementation to rescue. The smallest coherent checkpoint is therefore documentation-only: preserve the design input, record the separation state, and stop feature development.

## Commit boundary

- Pre-meta parent SHA: `b5d52d1fc9d5dce231ccb0f91ece2be0168dfa78`
- Reproduced v0.2 source-freeze SHA: `dec08c81644f1c47b4b94c29a406a9432df7c7bd`
- Reproduced v0.2 evidence-binding SHA: `b5d52d1fc9d5dce231ccb0f91ece2be0168dfa78`
- Preservation WIP content SHA: `3fe6695ee1230805874df68be653de603f5faaaa`
- WIP branch: `research/casformer-v0.3-meta-logic-wip`
- Clean release branch: `release/casformer-v0.2-source-freeze`
- Clean release branch target: `b5d52d1fc9d5dce231ccb0f91ece2be0168dfa78`

The WIP content commit could not contain its own SHA because changing this file would change that SHA. This exact value is therefore bound by a following documentation-only commit. The binding commit adds no runtime, schema, trace, authority, training, or test behavior.

## Audited v0.2 files

- Modified audited files: none.
- Missing audited files: none.
- Manifest matches: 50 of 50.
- v0.2 manifest SHA-256: `f68b9ba78bb5b6bc184c4b014a799756c1b714f05d05b515dcd464a54c76e634`.
- v0.2 aggregate SHA-256: `5fad64a52c8aef30d56e46fa22f113c26bc171a3016d326c3c88157425b798f1`.
- Evidence-commit changes relative to the source freeze: 51 files, all under `CAS_CJT_TRANSFORMER_v0_2/artifacts/`.

Five untracked `cas_neural_cjt.egg-info` files exist in the user's main worktree. They are generated packaging byproducts, are outside the 50-file manifest, and are not included here. The other dirty main-worktree files are older unrelated user work and are also excluded.

## New files in this WIP checkpoint

- `CAS_META_0_DESIGN_INPUT.md`
- `META_LOGIC_WIP_BOUNDARY.md`
- `records/AUDITED_V0_2_BASELINE.json`
- `records/PRE_SEPARATION_STATE.json`
- `records/PRE_SEPARATION_WORKTREE_STATUS.txt`
- `records/SOURCE_PROVENANCE.json`

No existing file is modified by this checkpoint.

## Change classification

| Area | Change in this checkpoint |
| --- | --- |
| Runtime behavior | None |
| Schemas | None |
| Authority or commitment | None |
| Stored traces or trace format | None |
| Tests | None |
| Neural training | None; not authorized |
| Release-only behavior | None |
| Meta-logic behavior | None; design input only |

## Preserved design scope

The design input covers future work on CAS program representation; deterministic parsing and type checking; a CJT circuit compiler and scheduler; a meta-level program proposer; operation, verifier, readiness, repair, memory, tool, compute-plan, and update-scope contracts; program traces; procedure learning; and program-to-CJT lowering.

Memory strategies must remain interchangeable behind one interface:

- explicit chain tags;
- bounded pulsation;
- true oscillation;
- trajectory readout;
- hybrid tag-plus-pulse.

Oscillatory phase must not be the sole source of chain identity.

## First implementation milestone

Compile one small CAS program into the existing lifecycle:

```text
A -> B -> C -> repair R -> resumed C
```

The compiled and hard-wired forms must produce equivalent Effect outcomes, repair lifecycle, committed Bias, parameter-scope enforcement, restart behavior, and trace validity. No automatic training or capability claim follows.

## Known unfinished work

- Define the minimum CAS program grammar and typed program IR.
- Define deterministic parser and type-checker errors.
- Define the program-to-CJT lowering contract.
- Define compiler-enforced memory, tool, compute, verifier, repair, and update scopes.
- Implement the first compiled lifecycle without changing v0.2.
- Add equivalence tests against the hard-wired v0.2 lifecycle.
- Add matched non-CAS controls before any CAS-specific advantage experiment.
- Keep protected evaluation data closed until designs, controls, and thresholds are frozen.
- Obtain a new review and audit for any v0.3 runtime candidate.

## No-claim statement

This WIP does not establish language capability, general reasoning capability, CAS-specific advantage, completion of the CNCM brain, AGI, production readiness, safe autonomous programming, or permission to train neural parameters. It is not part of the reproduced v0.2 release and must not be merged into either v0.2 release commit.
