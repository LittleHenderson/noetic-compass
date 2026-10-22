"""Prove route D delivers the case to an operation, without making the test itself the failure.

WHAT THIS TESTS
---------------
Route D's purpose: the runtime's operation module can see the task's own content, not only
CASformer's attention projection of it. The patched operation bank receives a `case` and holds it in
`self._active_case` for the duration of the call. This probe registers one extension operation that
records what the bank is holding when it runs, and checks:

  1. the operation sees the case when one is given,
  2. the attribute is cleared afterwards, so a case cannot leak into the next call,
  3. the operation sees None when none is given,
  4. a later, different case is delivered rather than the first one sticking,
  5. an unknown operation id is still refused (the patch weakened no guard),
  6. `state_dict()` still works — the module graph did not become cyclic.

THREE DEFECTS THIS PROBE ALREADY CAUGHT, all kept as comments where they happened:
  * the first version of the PATCH passed the case in and dropped it, so nothing could read it;
  * the first version of this PROBE had the recorder hold a reference to its own parent bank, which
    made the module graph cyclic and sent `state_dict()` into `RecursionError`;
  * a version in between put the patched tree at the wrong end of `sys.path`, so it tested the
    installed copy. The probe now prints which `cas_cjt` it loaded.

Usage:
    C:\\Python314\\python.exe -B verify_route_d_case_passing.py <patched-cas_cjt-parent>
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Mapping, Optional

# The patched root must come FIRST, before any cas_cjt import. `cas_cjt` is also installed in
# site-packages as an older, UNPATCHED copy (24 modules against the frozen tree's 34), so a later
# insert silently tests the wrong code.
if len(sys.argv) >= 2:
    _root = os.path.abspath(sys.argv[1])
    while _root in sys.path:
        sys.path.remove(_root)
    sys.path.insert(0, _root)

import torch
from torch import Tensor, nn

import cas_cjt.neural  # noqa: E402  (after the path is fixed, on purpose)
import casformer
from cas_cjt.contracts import canonical_digest
from cas_cjt.neural import NeuralCJTError, OperationRegistration, RegisteredOperationBank
from cas_cjt.state import READINESS_PROFILE_ID, ZERO_DIGEST, CandidateEffectSchema
from cas_cjt.types import CauseKind, CausePacket, OntologyStatus, OperationContract

#: The built-ins take relation indices 0 to 3 (^6 decompose, ^2 attract, ^3 avert, ^8 trigger), and
#: the bank refuses a duplicate. Measured from the source, not guessed.
FREE_RELATION_INDEX = 4
FREE_OPERATION_ID = "experimental_r1_rt_probe"


def build_contract(registration: OperationRegistration) -> OperationContract:
    """A valid contract for the probe, modelled on the real one in `cas_cjt/state.py:154-200`.

    Every field value is copied from `make_operation_contract`, which builds the four frozen
    prototype contracts. The probe does not invent the schema: two earlier attempts that guessed
    were refused by the contract's own validator, which is the code working as intended.
    """
    from dataclasses import replace

    verifier = {"verifier_id": "independent-effect-verifier", "verifier_version": 1,
                "policy_id": "cas.neural-cjt.exact-semantic-verifier/0.2"}
    placeholder = OperationContract(
        contract_id=registration.contract_id,
        contract_version=1,
        operation_id=registration.operation_id,
        operation_name=registration.name,
        ontology_status=registration.admission,
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
        verifier_digest=canonical_digest(verifier),
        plasticity_groups=(f"operation:{registration.operation_id}", "bias_update_head"),
        governance_requirements=("execute", "publish_effect", "write_bias", "learn"),
        contract_digest=ZERO_DIGEST,
    )
    return replace(placeholder,
                   contract_digest=canonical_digest(placeholder.to_dict(),
                                                    omit_keys=("contract_digest",)))


class _Recorder(nn.Module):
    """An extension operation that records what the bank was holding when it ran.

    It reads the bank through a PLAIN Python attribute holding a reference, and the recorder itself
    keeps only a tensor and a list. The first version stored the bank directly on the module, which
    made the object graph cyclic — the bank is an `nn.Module` too — and `state_dict()` recursed
    until Python raised `RecursionError`. Module bookkeeping must stay out of the module tree.
    """

    def __init__(self, read_case) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.zeros(4, 4))
        self._read_case = read_case          # a plain callable, not a Module
        self.seen: List[Any] = []

    def forward(self, value: Tensor) -> Tensor:
        self.seen.append(self._read_case())
        return value


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    print("=" * 72)
    print("ROUTE D: DOES AN OPERATION READ THE CASE?")
    print("=" * 72)
    print("  cas_cjt in use : %s" % os.path.dirname(cas_cjt.neural.__file__))
    print("  torch          : %s" % torch.__version__)
    if not hasattr(cas_cjt.neural.NeuralCJT, "set_active_case"):
        print()
        print("ABORT: this cas_cjt is NOT the patched one. Put the patched parent first.")
        return 1

    # num_relations must exceed the highest relation_index: the built-ins take 0 to 3, so a free
    # index of 4 needs at least 5 channels.
    config = casformer.CASformerConfig(d_model=4, num_heads=1, num_relations=6, num_layers=1,
                                       d_ff=8)
    bank = RegisteredOperationBank(config)

    registration = OperationRegistration(
        operation_id=FREE_OPERATION_ID,
        name=FREE_OPERATION_ID,
        relation_index=FREE_RELATION_INDEX,
        admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
        contract_id="cas.cjt.operation.r1-rt-probe.experimental/0.1",
    )
    recorder = _Recorder(lambda: getattr(bank, "_active_case", "ATTRIBUTE_MISSING"))
    bank.register_operation(registration, recorder)
    bank.bind_contract(build_contract(registration))

    value = torch.zeros(1, 4)
    first_case = {"task_id": "native.route_dependency_audit/1", "case_id": "probe-1",
                  "route": [0, 1, 2], "edges": [[0, 1]], "nodes": [0, 1, 2]}

    print()
    print("  call 1: WITH a case")
    bank(FREE_OPERATION_ID, value, first_case)
    got = recorder.seen[-1]
    print("    the operation saw: %r" % (got,))
    ok_with = isinstance(got, Mapping) and got.get("case_id") == "probe-1"

    print("  holder cleared after the call: %r" % (getattr(bank, "_active_case", "MISSING"),))
    ok_cleared = getattr(bank, "_active_case", "MISSING") is None

    print()
    print("  call 2: WITHOUT a case")
    bank(FREE_OPERATION_ID, value)
    got2 = recorder.seen[-1]
    print("    the operation saw: %r" % (got2,))
    ok_without = got2 is None

    print()
    print("  call 3: with a DIFFERENT case, to prove it is not sticky")
    bank(FREE_OPERATION_ID, value, {"case_id": "probe-3"})
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

    print()
    print("  module-graph check: state_dict() still works with the extension registered")
    try:
        keys = list(bank.state_dict().keys())
        ok_graph = True
        print("    state_dict has %d entries, no recursion" % len(keys))
    except RecursionError:
        ok_graph = False
        print("    RecursionError: the probe's own bookkeeping entered the module tree")

    results = {
        "operation reads the case when given one": ok_with,
        "the holder is cleared after the call": ok_cleared,
        "operation sees None when given none": ok_without,
        "a later case is delivered, not sticky": ok_third,
        "unknown operation ids are still refused": ok_refuse,
        "state_dict still works (no cyclic module graph)": ok_graph,
    }
    print()
    print("=" * 72)
    bad = 0
    for name, ok in results.items():
        print("  %-52s %s" % (name, "PASS" if ok else "FAIL"))
        bad += 0 if ok else 1
    print("=" * 72)
    print("RESULT: %s" % ("ROUTE D WORKS" if bad == 0 else "%d CHECK(S) FAILED" % bad))
    print("=" * 72)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
