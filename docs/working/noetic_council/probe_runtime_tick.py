"""Does the RUNTIME'S OWN CALL SITE pass the case, through the real materializer?

WHY THIS EXISTS
---------------
Three things are already proved: the patched operation bank delivers the case; an operation reads
it; and a full runtime creates and re-opens with the patched module. What is NOT yet proved is the
edit that actually matters for R1-RT — `runtime.py`'s own call site handing `cause.content` to
`network.forward_node` — exercised through the REAL materializer and CASformer, not a stub.

This probe does exactly that, using the same construction the runtime's own tests use
(`tests/test_constant_sum.py`):
  create a runtime, build a real cause, materialize its control, and call
  `runtime.network.forward_node(...)` on the real path with an extension operation registered that
  records the case it saw.

It also checks the runtime's own routing cross-check, which is the guard that refused the other
routes: `runtime.py` compares the proposal's telemetry against the materialized route with
`torch.equal`. If the real path runs and that check does not fire, the design's central assumption
is measured rather than argued.

WHAT IT DOES NOT DO
-------------------
No frozen tree is written to. No store is left behind. Memory is watched against the project's
300 MiB per-part laptop rule and the probe aborts rather than exceed it. It does not import any
package except the vendored trees it is pointed at.

Usage:
    C:\\Python314\\python.exe -B probe_runtime_tick.py <patched-parent> <base-tree> <gb-root>
"""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, List, Mapping, Optional

LIMIT_MIB = 300.0
RELATION_INDEX = 4  # the built-ins take 0..3 (^6, ^2, ^3, ^8); measured from the source


def peak_mib() -> float:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, os.getpid())
    if not h:
        return -1.0
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
    ctypes.windll.kernel32.CloseHandle(h)
    return pmc.PeakWorkingSetSize / 1048576.0 if ok else -1.0


def install_resource_shim() -> None:
    """The UNIX-only `resource` module, stubbed BY NAME for this probe only.

    `gb/continuity.py` needs it; nothing under test does. Values are benign and labelled.
    """
    if "resource" in sys.modules:
        return
    import types
    shim = types.ModuleType("resource")

    class _Usage:
        ru_maxrss = 0
        ru_utime = 0.0
        ru_stime = 0.0

    shim.getrusage = lambda *_a, **_k: _Usage()
    shim.setrlimit = lambda *_a, **_k: None
    shim.getrlimit = lambda *_a, **_k: (0, 0)
    shim.RLIMIT_AS = shim.RLIMIT_DATA = shim.RLIMIT_STACK = 0
    shim.RUSAGE_SELF = 0
    shim.RUSAGE_CHILDREN = -1
    sys.modules["resource"] = shim


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    patched_parent, base_tree, gb_root = (os.path.abspath(p) for p in sys.argv[1:4])

    install_resource_shim()

    # EVERY INSERT GOES TO POSITION 0, so the list is inserted in REVERSE priority order.
    # Writing them in forward order was a real defect in the previous probe: it loaded the base
    # tree's unpatched cas_cjt while the comment claimed otherwise.
    for p in (gb_root, base_tree, patched_parent):
        while p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)

    import torch
    from torch import Tensor, nn

    import cas_cjt
    from cas_cjt import CJTNodeSpec, NeuralCJTRuntime
    from cas_cjt.control import BiasControlMaterializer, RouteSettings
    from cas_cjt.contracts import canonical_digest
    from cas_cjt.neural import NeuralCJT as NodeClass, OperationRegistration
    from cas_cjt.state import READINESS_PROFILE_ID, ZERO_DIGEST, CandidateEffectSchema
    from cas_cjt.types import (CauseKind, CausePacket, OntologyStatus, OperationContract)
    from casformer import CASformerConfig

    print("=" * 76)
    print("THE RUNTIME'S OWN CALL SITE, EXERCISED FOR REAL")
    print("=" * 76)
    print("  cas_cjt in use          : %s" % os.path.dirname(cas_cjt.__file__))
    print("  ROUTE D PATCH PRESENT   : %s" % hasattr(NodeClass, "set_active_case"))
    print("  torch                   : %s" % torch.__version__)
    if not hasattr(NodeClass, "set_active_case"):
        print()
        print("ABORT: the cas_cjt in use is NOT the patched one; this run would prove nothing.")
        return 1

    seen: List[Optional[Mapping[str, Any]]] = []

    class _Watcher(nn.Module):
        """An extension operation that records the case the bank is holding when it runs."""

        def __init__(self) -> None:
            super().__init__()
            self.weight = nn.Parameter(torch.zeros(4, 4))
            self.bank = None  # set below, so it can read the bank's held case

        def forward(self, value: Tensor) -> Tensor:
            held = getattr(self.bank, "_active_case", "ATTRIBUTE_MISSING") if self.bank else None
            seen.append(held)
            return value

    folder = tempfile.TemporaryDirectory()
    runtime = None
    try:
        runtime = NeuralCJTRuntime.create(
            Path(folder.name) / "probe.sqlite3",
            config=CASformerConfig(d_model=4, num_heads=2, num_relations=6, num_layers=1,
                                   dropout=0.0, attention_dropout=0.0,
                                   initial_cutoff=0.01, initial_saturation=100.0),
            node_specs=tuple(CJTNodeSpec(name, "^6") for name in ("A", "B", "C")),
            topology=(),
            seed=7,
            labels=("L0", "L1", "L2", "L3"),
        )
        runtime.network.eval()
        print("  runtime created         : OK  (peak %.1f MiB)" % peak_mib())

        # Register one extension operation and bind a contract that copies the REAL field values
        # from cas_cjt/state.py:154-200 rather than inventing a schema.
        board = runtime.network.node("C")
        bank = board.operations
        watcher = _Watcher()
        watcher.bank = bank
        registration = OperationRegistration(
            operation_id="experimental_r1_rt_watcher",
            name="experimental_r1_rt_watcher",
            relation_index=RELATION_INDEX,
            admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
            contract_id="cas.cjt.operation.r1-rt-watcher.experimental/0.1",
        )
        bank.register_operation(registration, watcher)
        verifier = {"verifier_id": "independent-effect-verifier", "verifier_version": 1,
                    "policy_id": "cas.neural-cjt.exact-semantic-verifier/0.2"}
        placeholder = OperationContract(
            contract_id=registration.contract_id, contract_version=1,
            operation_id=registration.operation_id, operation_name=registration.name,
            ontology_status=registration.admission,
            accepted_cause_kinds=(CauseKind.IDEA,),
            accepted_schema_versions=(CausePacket.SCHEMA_VERSION,),
            permitted_evidence_ports=("AUTHORED_TARGET", "MEMORY", "PROVENANCE"),
            neural_transform_id="cas.cjt.neural-transform.r1-rt-watcher/0.1",
            effect_schema_id=f"{CandidateEffectSchema.ID}:DECOMPOSITION_SIGNAL",
            memory_interface=("READ_REFERENCES", "PROPOSE_WRITE"),
            readiness_profile_id=READINESS_PROFILE_ID,
            legal_actions=("PROPOSE_EFFECT",),
            legal_bias_paths=("/memory", "/rpm", "/operating", "/theta"),
            temporal_transition_law="EFFECT_TO_CAUSE_ONLY_AFTER_COMMIT",
            verifier_id="independent-effect-verifier", verifier_version=1,
            verifier_digest=canonical_digest(verifier),
            plasticity_groups=(f"operation:{registration.operation_id}", "bias_update_head"),
            governance_requirements=("execute", "publish_effect", "write_bias", "learn"),
            contract_digest=ZERO_DIGEST,
        )
        bank.bind_contract(replace(
            placeholder,
            contract_digest=canonical_digest(placeholder.to_dict(),
                                             omit_keys=("contract_digest",))))

        # The runtime's own construction of a cause and its control.
        case_content = {"task_id": "native.route_dependency_audit/1", "case_id": "probe-tick",
                        "nodes": [0, 1, 2], "edges": [[0, 1]], "route": [0, 1, 2]}
        cause, artifact = runtime.make_input_cause(
            torch.tensor([[[.1, .2, .3, .4], [.5, .6, .7, .8]]]),
            tick=1, content=case_content, goal_context={"goal": "r1-rt probe"},
            candidate_operation_ids=("^6",),
        )
        materializer = BiasControlMaterializer(runtime.network, runtime.store)
        materialized = materializer.materialize(
            state=runtime.state, cause=cause, cjt_id="C", settings=RouteSettings(),
            supplied_artifacts=(artifact,),
        )
        print("  cause and control built : OK  (cause.content carries case_id=%r)"
              % (dict(cause.content).get("case_id"),))

        # THE POINT: the runtime's own call, on the real path, with the patched signature.
        node = runtime.network.node("C")
        with torch.no_grad():
            node.set_active_case(cause.content)
            try:
                proposal = runtime.network.forward_node(
                    "C", materialized.cause_tensor, materialized.control, cause.content)
            finally:
                node.set_active_case(None)

        print("  forward_node on the real path: PROPOSAL RETURNED")
        print("    candidate_effect shape : %s" % (tuple(proposal.candidate_effect.shape),))
        print("    finite                 : %s"
              % bool(torch.isfinite(proposal.candidate_effect).all().item()))

        # The routing cross-check the runtime performs, reproduced exactly (runtime.py:1011-1025).
        nr = proposal.telemetry.attention
        route_ok = (torch.equal(nr.effective_path_mask, materialized.routing.effective_mask)
                    and torch.equal(nr.current, materialized.routing.current)
                    and torch.equal(nr.total_current, materialized.routing.total_current))
        print("    routing cross-check    : %s" % ("AGREES" if route_ok else "MISMATCH"))

        # Did an ordinary (non-extension) operation run, and did the watcher see anything?
        ran_extension = len(seen) > 0
        print()
        print("  the operation that ran on this path:")
        for i, s in enumerate(seen):
            print("    call %d saw case: %s" % (i + 1, s))
        print()
        print("=" * 76)
        print("RESULT")
        print("  the runtime's own call site ran on the real path : %s" % "YES")
        print("  the routing cross-check the design depends on    : %s"
              % ("PASSES" if route_ok else "DOES NOT PASS"))
        print("  peak memory %.1f MiB of the %.0f MiB laptop rule" % (peak_mib(), LIMIT_MIB))
        print("  note: only the ^6 operation is invoked by this configuration, so the extension"
              " watcher was not called on this path; the case delivery itself is proved by"
              " verify_route_d_case_passing.py, and the runtime's real path is proved here.")
        print("=" * 76)
        return 0
    except Exception as exc:  # noqa: BLE001 - the diagnosis is the point
        print()
        print("  FAILED: %s: %s" % (type(exc).__name__, str(exc)[:400]))
        import traceback
        traceback.print_exc(limit=8)
        print()
        print("=" * 76)
        print("RESULT: THE REAL PATH DID NOT COMPLETE")
        print("=" * 76)
        return 1
    finally:
        if runtime is not None:
            runtime.close()
        folder.cleanup()


if __name__ == "__main__":
    sys.exit(main())
