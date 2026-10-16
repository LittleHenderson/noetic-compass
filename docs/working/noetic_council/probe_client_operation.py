"""Does the runtime actually CALL a client operation, and hand it the task's content?

WHY THIS EXISTS
---------------
Appendix E section 7 names four things it could not measure. Two of them are answered here:

- whether the runtime accepts an `EXPERIMENTAL_OPEN_SEMANTICS` operation as a node's registered
  operation;
- whether that operation runs on the real path and receives `cause.content`.

The client here is a RECORDER, not the brain and not the boundary. It answers one question and nothing
else, so a failure cannot be confused with a boundary problem. If this works, the process boundary is
the only remaining piece.

WHAT IT DOES NOT DO
-------------------
No process boundary, no recipe brain, no tensor written from a brain answer, no store left behind.
No frozen tree is written to; the patched copy is only read.

Usage:
    C:\\Python314\\python.exe -B probe_client_operation.py <patched-parent> <base-tree> <gb-root>
"""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, List, Optional

LIMIT_MIB = 300.0
CLIENT_ID = "experimental_r1_rt_client"
#: The four built-ins take 0..3 (^6, ^2, ^3, ^8), measured from `OPERATION_REGISTRATIONS`.
CLIENT_RELATION_INDEX = 4
ANSWER_LABELS = tuple("FIRST_UNSUPPORTED_LEG_%d" % i for i in range(7)) + ("ALL_LEGS_PRESENT",)


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
    """The UNIX-only `resource` module, stubbed BY NAME for this probe only."""
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

    # Reverse priority order: each insert goes to position 0, so the LAST insert wins.
    for p in (gb_root, base_tree, patched_parent):
        while p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)

    import torch
    from torch import Tensor, nn
    import cas_cjt
    from cas_cjt import CJTNodeSpec, NeuralCJTRuntime
    from cas_cjt.contracts import canonical_digest
    from cas_cjt.neural import NeuralCJT as NodeClass, OperationRegistration
    from cas_cjt.semantic import DecoderContract
    from cas_cjt.state import READINESS_PROFILE_ID, ZERO_DIGEST, CandidateEffectSchema
    from cas_cjt.types import (CauseKind, CausePacket, OntologyStatus, OperationContract)
    from casformer import CASformerConfig

    print("=" * 78)
    print("DOES THE RUNTIME CALL A CLIENT OPERATION, AND HAND IT THE CONTENT?")
    print("=" * 78)
    print("  cas_cjt in use   : %s" % os.path.dirname(cas_cjt.__file__))
    print("  torch            : %s" % torch.__version__)
    from cas_cjt.state import make_operation_contract
    try:
        contract = make_operation_contract(CLIENT_ID)
        print("  the client contract : %s" % contract.contract_id)
    except Exception as error:
        print()
        print("ABORT: the operation table does not know the client: %s: %s"
              % (type(error).__name__, error))
        print("       The patched copy under test does not carry the state.py entry.")
        return 1
    if not hasattr(NodeClass, "set_active_case"):
        print("ABORT: the cas_cjt in use is NOT route-D patched; this run would prove nothing.")
        return 1

    seen: List[Optional[Any]] = []

    class _Recorder(nn.Module):
        """A client-shaped module that records the case it was handed.

        It holds NO reference to the bank and NO reference to any other nn.Module: holding the bank
        once made the module graph cyclic and `state_dict()` raised RecursionError. It reads through
        the plain callable below instead, which lives outside the module tree.
        """

        def __init__(self, label: str = "?") -> None:
            super().__init__()
            self.label = label
            self.weight = nn.Parameter(torch.zeros(8, 8))
            self.read_case = None          # a plain callable, set below

        def forward(self, value: Tensor) -> Tensor:
            seen.append((self.label, self.read_case() if self.read_case else None))
            return torch.ones_like(value)

    # ignore_cleanup_errors: on Windows the SQLite store's handle can outlive `runtime.close()` by a
    # moment, and a cleanup failure must not mask the probe's actual result. The first run of this
    # probe reported only the WinError 32 and hid everything the run had measured.
    folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    runtime = None
    try:
        d_model = len(ANSWER_LABELS)
        # At least three nodes: `NetworkStateEnvelope` refuses fewer ("a network state requires at
        # least three typed BiasState records"). Decoder contracts must cover EXACTLY the network's
        # CJTs and all share one label set, so all three carry the client.
        nodes = ("A", "B", "C")
        decoders = {
            name: DecoderContract(
                # v1 on purpose: this probe asks whether the CLIENT is called, not which decoder
                # algorithm runs. v1 requires the unchanged algorithm, no input_width and no
                # channel_indices, and its effect_width is len(labels), so d_model must equal the
                # label count. The real run needs v2 (input_width 64, channels 0..7) plus an exact
                # semantic lineage, which v2 roots require; that is a separate step.
                decoder_id="decoder:%s:r1-rt-client-v1" % name, version=1, operation_id=CLIENT_ID,
                effect_kind="DECOMPOSITION_SIGNAL", labels=ANSWER_LABELS)
            for name in nodes
        }
        # The recorders are built first because `create()` needs their modules at call time. Their
        # `read_case` callables can only be wired AFTER the runtime exists, since the bank they read
        # is inside it. That is fine: `read_case` is a plain attribute, not a parameter, so it is not
        # part of the module tree and setting it later changes no weights.
        recorders = {name: _Recorder(name) for name in nodes}
        runtime = NeuralCJTRuntime.create(
            Path(folder.name) / "client.sqlite3",
            config=CASformerConfig(d_model=d_model, num_heads=2, num_relations=6, num_layers=1,
                                   dropout=0.0, attention_dropout=0.0,
                                   initial_cutoff=0.01, initial_saturation=100.0),
            node_specs=tuple(CJTNodeSpec(name, CLIENT_ID) for name in nodes),
            topology=(),
            seed=7,
            decoder_contracts=decoders,
            extension_operations={
                name: ((OperationRegistration(
                    operation_id=CLIENT_ID,
                    name=CLIENT_ID,
                    relation_index=CLIENT_RELATION_INDEX,
                    admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
                    contract_id=contract.contract_id,
                ), recorders[name]),)
                for name in nodes
            },
        )
        runtime.network.eval()
        for name in nodes:
            node_bank = runtime.network.node(name).operations
            recorders[name].read_case = (
                lambda b=node_bank: getattr(b, "_active_case", "ATTRIBUTE_MISSING"))
        print("  runtime created with a CLIENT node spec : YES  (peak %.1f MiB)" % peak_mib())
        print("  client operation registered : YES  (relation index %d, %d node(s))"
              % (CLIENT_RELATION_INDEX, len(nodes)))

        case_content = {"task_id": "native.route_dependency_audit/1", "case_id": "client-probe",
                        "nodes": [0, 1, 2], "edges": [[0, 1]], "route": [0, 1, 2]}
        cause, artifact = runtime.make_input_cause(
            torch.tensor([[[.1, .2, .3, .4, .5, .6, .7, .8]] * 8]),
            tick=1, content=case_content, goal_context={"goal": "r1-rt client probe"},
            candidate_operation_ids=(CLIENT_ID,),
        )
        prepared = runtime._prepare_inference(
            cause=cause, cjt_id="C", expected_symbol=None, opposite_symbol=None, settings=None,
            supplied_artifacts=(artifact,), resume_repair_id=None, write_memory=False,
        )
        print("  runtime._prepare_inference   : RETURNED  (%s)" % type(prepared).__name__)
        print()
        print("  the client was called %d time(s)" % len(seen))
        for i, item in enumerate(seen, 1):
            label, case = item
            if hasattr(case, "get"):
                print("    call %d  node %s  saw case_id=%r"
                      % (i, label, dict(case).get("case_id")))
            else:
                print("    call %d  node %s  saw %r" % (i, label, case))

        called = len(seen) > 0
        with_content = any(hasattr(c, "get") and dict(c).get("case_id") == "client-probe"
                           for _label, c in seen if c is not None)
        bank = runtime.network.node("C").operations
        left = getattr(bank, "_active_case", "ATTRIBUTE_MISSING")

        print()
        print("=" * 78)
        print("RESULT")
        print("  the runtime accepted a CLIENT node spec          : YES")
        print("  the runtime accepted the client registration     : YES")
        print("  the client RAN on the runtime's own path         : %s"
              % ("YES" if called else "NO"))
        print("  it received the task's own content               : %s"
              % ("YES" if with_content else "NO"))
        print("  the bank was left empty afterwards               : %s"
              % ("YES" if left is None else repr(left)))
        print("  peak memory %.1f MiB of the %.0f MiB laptop rule" % (peak_mib(), LIMIT_MIB))
        print()
        print("  What this answers from appendix E section 7: items 1, 2 and 4.")
        print("  What it does NOT answer: item 3, the cost of a process boundary, and anything about")
        print("  the recipe brain. This recorder is not the brain.")
        print("=" * 78)
        return 0 if (called and with_content and left is None) else 1
    except Exception as exc:  # noqa: BLE001 - the diagnosis is the point
        print()
        print("  FAILED: %s: %s" % (type(exc).__name__, str(exc)[:600]))
        import traceback
        traceback.print_exc(limit=10)
        print()
        print("=" * 78)
        print("RESULT: THE CLIENT PATH DID NOT COMPLETE")
        print("=" * 78)
        return 1
    finally:
        if runtime is not None:
            runtime.close()
        folder.cleanup()


if __name__ == "__main__":
    sys.exit(main())
