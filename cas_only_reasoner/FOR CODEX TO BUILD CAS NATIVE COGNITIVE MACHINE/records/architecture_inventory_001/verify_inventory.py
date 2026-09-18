"""Inventory the registered operations: what the architecture declares, and what the run exercises.

Read-only. No forward pass, no training, no device, no target, no provider. `torch` is used only to
instantiate the operation bank so its modules and parameter names can be enumerated; nothing is run
through them.

This completes `records/bias_role_001/STATUS.md`. That record found the `^6` contract admits two
plasticity groups and the run's module contains one. This one asks the larger question: **how much of
the declared architecture does the canonical path exercise at all?**

Run it to reproduce `records/architecture_inventory_001/STATUS.md`. It self-checks the recorded
operation list and admissions and reports if they change.
"""

from __future__ import annotations

from pathlib import Path
import sys

HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

#: Recorded at the time of the inventory. A change here changes the record's conclusion.
EXPECTED = {
    "^6": ("decompose", "CANONICAL_ADMITTED", 16384),
    "^2": ("experimental_attract", "EXPERIMENTAL_OPEN_SEMANTICS", 8192),
    "^3": ("experimental_avert", "EXPERIMENTAL_OPEN_SEMANTICS", 8192),
    "^8": ("experimental_trigger", "EXPERIMENTAL_CONFLICTED_SEMANTICS", 8192),
}

#: The parameter names the typed learner asserts as its entire scope.
LEARNER_PARAMETERS = ("left.weight", "merge.weight", "right.weight")


def main() -> int:
    from cas_cjt.neural import DECOMPOSE, OPERATION_REGISTRATIONS, NeuralCJT, RegisteredOperationBank
    from casformer import CASformerConfig

    config = CASformerConfig(
        d_model=64, num_heads=2, num_relations=4, num_layers=1, dropout=0.0,
        attention_dropout=0.0, initial_cutoff=0.01, initial_saturation=100.0,
    )
    bank = RegisteredOperationBank(config)

    print("=" * 100)
    print("REGISTERED OPERATIONS")
    print("=" * 100)
    print()
    print(f"{'op':>4} {'name':>22} {'admission':>32} {'params':>8} {'module':>22}")
    print("-" * 100)
    observed = {}
    for registration in OPERATION_REGISTRATIONS:
        module = bank.modules_by_operation[registration.operation_id]
        count = sum(parameter.numel() for _, parameter in module.named_parameters())
        observed[registration.operation_id] = (
            registration.name, registration.admission.name, count
        )
        print(f"{registration.operation_id:>4} {registration.name:>22}"
              f" {registration.admission.name:>32} {count:8d} {type(module).__name__:>22}")
    print()

    matches = observed == EXPECTED
    print(f"  operation inventory matches the record : {matches}")
    if not matches:
        print("  -> THE RECORD IS STALE. records/architecture_inventory_001/STATUS.md must be "
              "revisited.")
        for op in sorted(set(observed) | set(EXPECTED)):
            if observed.get(op) != EXPECTED.get(op):
                print(f"     {op}: recorded {EXPECTED.get(op)}  observed {observed.get(op)}")
    print()

    total = sum(count for _, _, count in observed.values())
    canonical = [op for op, (_, admission, _) in observed.items()
                 if admission == "CANONICAL_ADMITTED"]
    experimental = [op for op in observed if op not in canonical]
    canonical_parameters = sum(observed[op][2] for op in canonical)
    experimental_parameters = total - canonical_parameters

    print("=" * 100)
    print("WHAT THE RUN EXERCISES")
    print("=" * 100)
    print()
    print(f"  registered operations          : {len(observed)}  ({', '.join(sorted(observed))})")
    print(f"  CANONICALLY ADMITTED           : {len(canonical)}  ({', '.join(sorted(canonical))})")
    print(f"  experimental / open / conflicted: {len(experimental)}  "
          f"({', '.join(sorted(experimental))})")
    print()
    print(f"  registered plastic parameters  : {total}")
    print(f"    canonical ^6 alone           : {canonical_parameters}"
          f"  ({100 * canonical_parameters / total:.1f}%)")
    print(f"    experimental operations      : {experimental_parameters}"
          f"  ({100 * experimental_parameters / total:.1f}%)")
    print()

    decompose = bank.modules_by_operation[DECOMPOSE]
    decompose_parameters = [name for name, _ in decompose.named_parameters()]
    print(f"  the run's module ({type(decompose).__name__}) parameters: {decompose_parameters}")
    print(f"  equals the typed learner's asserted scope: "
          f"{sorted(decompose_parameters) == sorted(LEARNER_PARAMETERS)}")

    cjt = NeuralCJT(config)
    head = [name for name, _ in cjt.named_parameters() if "bias_update_head" in name]
    head_count = sum(p.numel() for n, p in cjt.named_parameters() if "bias_update_head" in n)
    print(f"  NeuralCJT bias_update_head: {head}, {head_count} parameters")
    print()

    print("=" * 100)
    print("THE FINDING")
    print("=" * 100)
    print()
    print(
        f"  The architecture declares {len(observed)} operations and {total} plastic parameters.\n"
        f"  EXACTLY ONE is CANONICALLY ADMITTED: ^6, at {canonical_parameters} parameters"
        f" ({100 * canonical_parameters / total:.1f}%).\n"
        f"  The other {len(experimental)} are EXPERIMENTAL_OPEN_SEMANTICS or\n"
        f"  EXPERIMENTAL_CONFLICTED_SEMANTICS - the condition this project's own ledger records as\n"
        f"  OPEN-SEMANTICS, where implementation must not derive behaviour from invented meaning.\n"
        f"\n"
        f"  So the run exercises ^6 alone, and that choice is well founded: it is the only operation\n"
        f"  whose semantics are frozen. The unreached {experimental_parameters} parameters are\n"
        f"  unreached because of UNFROZEN SEMANTICS, not because of missing engineering.\n"
        f"\n"
        f"  bias_update_head remains the one genuinely admitted-but-unused plastic role belonging\n"
        f"  to the canonical operation's own contract. See OS-027."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
