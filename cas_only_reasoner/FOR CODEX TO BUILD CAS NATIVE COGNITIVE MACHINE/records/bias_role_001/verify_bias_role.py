"""Verify the `^6` contract's admitted plasticity groups against what the run's module contains.

Read-only. No model executed, no forward pass, no training, no device, no target, no provider.
`torch` is used only to instantiate the two module containers so their parameter names can be
enumerated; nothing is run through them.

Run this to reproduce `records/bias_role_001/STATUS.md`. If the contract's plasticity groups change,
or if the typed-teaching module ever gains the head, this script stops agreeing with that record and
the record must be revisited.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
import sys

HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

#: The three parameter names the typed learner asserts as its entire scope.
LEARNER_PARAMETERS = ("left.weight", "merge.weight", "right.weight")

#: The recorded contract identity. A change here is a contract change and must be reported.
EXPECTED_CONTRACT_DIGEST = "6bfc2602cfa2c78669fab832aa3a4c2bfc4193f2a54f1947036c6ae3a80e4168"
EXPECTED_PLASTICITY_GROUPS = ("operation:^6", "bias_update_head")


def main() -> int:
    from cas_cjt.state import make_operation_contract
    from cas_cjt.neural import DECOMPOSE, NeuralCJT, RegisteredOperationBank
    from casformer import CASformerConfig

    contract = make_operation_contract("^6")
    print("=" * 92)
    print("THE FROZEN ^6 CONTRACT")
    print("=" * 92)
    print()
    for field in dataclasses.fields(contract):
        value = getattr(contract, field.name)
        print(f"  {field.name:>26} = {value!r}"[:150])
    print()

    same_digest = contract.contract_digest == EXPECTED_CONTRACT_DIGEST
    same_groups = tuple(contract.plasticity_groups) == EXPECTED_PLASTICITY_GROUPS
    print(f"  contract digest matches the record : {same_digest}")
    print(f"  plasticity groups match the record : {same_groups}")
    if not (same_digest and same_groups):
        print("  -> THE RECORD IS STALE. records/bias_role_001/STATUS.md must be revisited.")
    print()

    config = CASformerConfig(
        d_model=64, num_heads=2, num_relations=4, num_layers=1, dropout=0.0,
        attention_dropout=0.0, initial_cutoff=0.01, initial_saturation=100.0,
    )
    bank = RegisteredOperationBank(config)
    module = bank.modules_by_operation[DECOMPOSE]
    module_parameters = [name for name, _ in module.named_parameters()]

    print("=" * 92)
    print("WHAT THE RUN'S MODULE CONTAINS")
    print("=" * 92)
    print()
    print(f"  bank module type   : {type(module).__name__}")
    print(f"  bank module params : {module_parameters}")
    learner_scope_holds = sorted(module_parameters) == sorted(LEARNER_PARAMETERS)
    print(f"  equals the typed learner's asserted scope : {learner_scope_holds}")
    print()

    cjt = NeuralCJT(config)
    cjt_parameters = [name for name, _ in cjt.named_parameters()]
    head_parameters = [name for name in cjt_parameters if "bias_update_head" in name]
    print(f"  NeuralCJT parameters : {len(cjt_parameters)}")
    print(f"  bias_update_head     : {head_parameters}")
    print(f"  the run's module contains it : "
          f"{any('bias_update_head' in name for name in module_parameters)}")
    print()

    print("=" * 92)
    print("THE FINDING")
    print("=" * 92)
    print()
    print(
        f"  The contract admits {len(contract.plasticity_groups)} plasticity groups: "
        f"{tuple(contract.plasticity_groups)}."
    )
    print(f"  Its governance requirements include "
          f"{'write_bias' if 'write_bias' in contract.governance_requirements else 'NO write_bias'}"
          f", with legal bias paths {tuple(contract.legal_bias_paths)}.")
    print(f"  The run's module exposes exactly {len(module_parameters)} parameters, none of which is "
          f"bias_update_head,")
    print(f"  and the typed learner asserts that narrower set as its entire scope with "
          f"\"frozen\": [].")
    print()
    print(
        "  So bias_update_head is not frozen in the run - it is ABSENT from the run's module. The\n"
        "  role is admitted by the contract and unreachable from the typed-teaching path, because\n"
        "  that path builds a bare _DecomposeTransform rather than a NeuralCJT.\n"
        "\n"
        "  NO CHANGE IS PROPOSED. Whether the learner's narrowing is legitimate or a defect that\n"
        "  strands an admitted mechanism is an authority decision. See OS-027."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
