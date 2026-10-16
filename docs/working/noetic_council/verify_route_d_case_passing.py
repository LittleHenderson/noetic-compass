"""Prove route D's patch works: does an operation actually READ the case?

WHAT THIS TESTS
---------------
Route D's whole purpose is that the runtime's operation module can see the task's own content
rather than only CASformer's attention projection of it. The patch has eight edits; this probe
checks the one that matters behaviourally, on the PATCHED COPY only:

  1. build a RegisteredOperationBank from the patched module,
  2. register one extension operation whose `forward` records the bank's `_active_case`,
  3. call the bank WITH a case and WITHOUT one,
  4. assert the operation saw the case the first time and None the second,
  5. assert the attribute is cleared afterwards, so a case cannot leak into the next call.

Why this probe exists at all: the first version of the patch PASSED the case into the bank and then
dropped it on the floor. The call site looked right and the operation could still not read anything.
Reading the patched file showed it; this probe is the check that would have caught it, so it is kept.

WHAT IT DOES NOT DO
-------------------
It does not create a runtime, does not open a store, does not run CASformer, and does not touch the
frozen source. It imports `cas_cjt.neural` and exercises one class in isolation.

Usage:
    C:\\Python314\\python.exe -B verify_route_d_case_passing.py <patched-cas_cjt-parent>
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Mapping, Optional

# The patched root must come FIRST, before any cas_cjt import. `cas_cjt` is also installed in
# site-packages (an older, UNPATCHED copy — 24 modules against the frozen tree's 34), so a later
# insert would silently test the wrong code. The first probe run did exactly that, and reported a
# refusal from the installed copy while claiming to test the patch.
if len(sys.argv) >= 2:
    _root = os.path.abspath(sys.argv[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    else:
        sys.path.remove(_root)
        sys.path.insert(0, _root)

import torch
from torch import Tensor, nn

import cas_cjt.neural  # noqa: E402  (after the path is fixed, on purpose)
import casformer
from cas_cjt.contracts import canonical_digest
from cas_cjt.neural import NeuralCJTError, OperationRegistration, RegisteredOperationBank
from cas_cjt.types import CauseKind, OntologyStatus, OperationContract

#: The built-ins take relation indices 0 to 3 (^6 decompose, ^2 attract, ^3 avert, ^8 trigger), and
#: the bank refuses a duplicate. Measured from the source, not guessed.
FREE_RELATION_INDEX = 4


def build_contract(registration: OperationRegistration) -> OperationContract:
    """A valid OperationContract for the probe, modelled on the real one in `state.py`.

    Every field value here is copied from `cas_cjt/state.py:154-200` (`make_operation_contract`),
    which builds the four frozen prototype contracts. The probe does not invent the schema: it
    reuses the values the codebase actually uses, and only the identity fields are the probe's own.
    """
    from cas_cjt.state import READINESS_PROFILE_ID, ZERO_DIGEST, CandidateEffectSchema
    from cas_cjt.types import CausePacket

    status = registration.admission
    verifier_descriptor = {
        "verifier_id": "independent-effect-verifier",
        "verifier_version": 1,
        "policy_id": "cas.neural-cjt.exact-semantic-verifier/0.2",
    }
    placeholder = OperationContract(
        contract_id=registration.contract_id,
        contract_version=1,
        operation_id=registration.operation_id,
        operation_name=registration.name,
        ontology_status=status,
        accepted_cause_kinds=(CauseKind.IDEA,),
        accepted_schema_versions=(CausePacket.SCHEMA_VERSION,),
        permitted_evidence_ports=("AUTHORED_TARGET", "MEMORY", "PROVENANCE"),
        neural_transform_id="cas.cjt.neural-transform.r1-rt-probe/0.1",
        effect_schema_id=f"{CandidateEffectSchema.ID}:DECOMPOSITION_SIGNAL",
        memory_interface=("READ_REFERENCES", "PROPOSE_WRITE"),
        readiness_profile_id=READINESS_PROFILE_ID,
        legal_actions=("PROPOSE_EFFECT",),
        legal_bias_paths=("/memory", "/rpm", "/operating", "/theta"),
        temporal_transition_law="EFFECT_TO_CAUSE_ONLY_AFTER_COMMIT",
        verifier_id="independent-effect-verifier",
        verifier_version=1,
        verifier_digest=canonical_digest(verifier_descriptor),
        plasticity_groups=(f"operation:{registration.operation_id}", "bias_update_head"),
        governance_requirements=("execute", "publish_effect", "write_bias", "learn"),
        contract_digest=ZERO_DIGEST,
    )
    from dataclasses import replace
    return replace(
        placeholder,
        contract_digest=canonical_digest(
            placeholder.to_dict(), omit_keys=("contract_digest",)
        ),
    )


class _Recorder(nn.Module):
    """An extension operation that records what the bank was holding when it ran."""

    def __init__(self, bank: RegisteredOperationBank) -> None:
        super().__init__()
        self.bank = bank
        self.weight = nn.Parameter(torch.zeros(4, 4))
        self.seen: List[Optional[Mapping[str, Any]]] = []

    def forward(self, value: Tensor) -> Tensor:
        self.seen.append(getattr(self.bank, "_active_case", "ATTRIBUTE_MISSING"))
        return value


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = os.path.abspath(sys.argv[1])
    print("=" * 72)
    print("ROUTE D: DOES AN OPERATION READ THE CASE?")
    print("=" * 72)
    print("  cas_cjt in use: %s" % os.path.dirname(cas_cjt.neural.__file__))
    print("  torch:          %s" % torch.__version__)

    # num_relations must exceed the highest relation_index the bank will accept; the built-ins
    # take 0 to 3, so a free index of 4 needs at least 5 channels.
    config = casformer.CASformerConfig(d_model=4, num_heads=1, num_relations=6, num_layers=1, d_ff=8)
    bank = RegisteredOperationBank(config)

    registration = OperationRegistration(
        operation_id="experimental_r1_rt_probe",
        name="experimental_r1_rt_probe",
        relation_index=FREE_RELATION_INDEX,
        admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
        contract_id="r1-rt-probe-contract",
    )
    recorder = _Recorder(bank)
    bank.register_operation(registration, recorder)
    bank.bind_contract(build_contract(registration))

    value = torch.zeros(1, 4)

    cases: List[Mapping[str, Any]] = [
        {"task_id": "native.route_dependency_audit/1", "case_id": "probe-1",
         "route": [0, 1, 2], "edges": [[0, 1]], "nodes": [0, 1, 2]},
    ]

    print()
    print("  call 1: WITH a case")
    bank("experimental_r1_rt_probe", value, cases[0])
    got = recorder.seen[-1]
    print("    the operation saw: %r" % (got,))
    ok_with = isinstance(got, Mapping) and got.get("case_id") == "probe-1"

    print("  attribute cleared after the call: %r" % (getattr(bank, "_active_case", "MISSING"),))
    ok_cleared = getattr(bank, "_active_case", "MISSING") is None

    print()
    print("  call 2: WITHOUT a case")
    bank("experimental_r1_rt_probe", value)
    got2 = recorder.seen[-1]
    print("    the operation saw: %r" % (got2,))
    ok_without = got2 is None

    print()
    print("  call 3: with a DIFFERENT case, to prove it is not sticky")
    bank("experimental_r1_rt_probe", value, {"case_id": "probe-3"})
    got3 = recorder.seen[-1]
    print("    the operation saw: %r" % (got3,))
    ok_third = isinstance(got3, Mapping) and got3.get("case_id") == "probe-3"

    print()
    print("  refusal check: an unknown operation id is still refused")
    try:
        bank("not_a_registered_operation", value)
        ok_refuse = False
        print("    NOT REFUSED - the patch weakened the guard")
    except NeuralCJTError as exc:
        ok_refuse = True
        print("    refused as before: %s" % str(exc)[:70])

    results = {
        "operation reads the case when given one": ok_with,
        "the attribute is cleared after the call": ok_cleared,
        "operation sees None when given none": ok_without,
        "a later case is delivered, not sticky": ok_third,
        "unknown operation ids are still refused": ok_refuse,
    }
    print()
    print("=" * 72)
    bad = 0
    for name, ok in results.items():
        print("  %-46s %s" % (name, "PASS" if ok else "FAIL"))
        bad += 0 if ok else 1
    print("=" * 72)
    print("RESULT: %s" % ("ROUTE D WORKS" if bad == 0 else "%d CHECK(S) FAILED" % bad))
    print("=" * 72)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
