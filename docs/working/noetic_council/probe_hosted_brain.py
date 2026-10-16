"""A REAL runtime tick, answered by the recipe brain across the process boundary.

WHAT THIS JOINS
---------------
Two halves that were proved separately and have never met:

- appendix G: the runtime accepts a client operation, calls it on its own path, and hands it the
  task's content;
- appendix H: the brain answers over a process boundary and has never held torch.

This probe puts the brain behind the client. One `runtime._prepare_inference` call now produces a
tensor whose decoded symbol is the brain's answer, read back through the RUNTIME'S OWN DECODER rather
than by inspecting the tensor here.

WHAT IT DOES NOT DO
-------------------
It does not touch a frozen tree, does not write a durable store, and does not run on a machine. The
client holds no learned parameters: it is a conduit, and the answer is the brain's.

Usage:
    C:\\Python314\\python.exe -B probe_hosted_brain.py <patched-parent> <base-tree> <gb-root> <v3-root>
"""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_process_boundary import Boundary  # noqa: E402

LIMIT_MIB = 300.0
CLIENT_ID = "experimental_r1_rt_client"
CLIENT_RELATION_INDEX = 4
LABELS = tuple("FIRST_UNSUPPORTED_LEG_%d" % i for i in range(7)) + ("ALL_LEGS_PRESENT",)
#: Appendix B's frozen out-rule: every channel `1.0`, and `+1` at the label channel of row 0.
BASELINE = 1.0


def oracle(route, edges) -> str:
    """The runtime's rule, computed here so the check does not lean on the brain or the runtime."""
    pairs = {tuple(e) for e in edges}
    for leg, pair in enumerate(zip(route, route[1:])):
        if pair not in pairs:
            return LABELS[leg]
    return LABELS[-1]


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
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    patched_parent, base_tree, gb_root, v3 = (os.path.abspath(p) for p in sys.argv[1:5])
    install_resource_shim()
    for p in (gb_root, base_tree, patched_parent):
        while p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)

    import torch
    from torch import Tensor, nn
    import cas_cjt
    from cas_cjt import CJTNodeSpec, NeuralCJTRuntime
    from cas_cjt.neural import NeuralCJT as NodeClass, OperationRegistration
    from cas_cjt.semantic import DecoderContract
    from cas_cjt.state import make_operation_contract
    from cas_cjt.types import OntologyStatus
    from casformer import CASformerConfig

    print("=" * 78)
    print("A REAL RUNTIME TICK, ANSWERED BY THE BRAIN ACROSS THE BOUNDARY")
    print("=" * 78)
    print("  cas_cjt in use : %s" % os.path.dirname(cas_cjt.__file__))
    if not hasattr(NodeClass, "set_active_case"):
        print("ABORT: not route-D patched; this run would prove nothing.")
        return 1
    try:
        contract = make_operation_contract(CLIENT_ID)
    except Exception as error:
        print("ABORT: the operation table does not know the client: %s" % error)
        return 1

    calls: List[dict] = []

    class BrainClient(nn.Module):
        """The client: reads the case the runtime handed it, asks the brain, writes the tensor.

        It holds NO reference to the bank and NO reference to another `nn.Module`, because holding one
        makes the module graph cyclic and `state_dict()` recurses. `ask` and `read_case` are plain
        callables set from outside, so nothing here joins the module tree except `weight`.
        """

        def __init__(self) -> None:
            super().__init__()
            self.weight = nn.Parameter(torch.zeros(len(LABELS), len(LABELS)))
            self.ask = None            # plain callable: the boundary
            self.read_case = None      # plain callable: reads the bank's held case

        def forward(self, value: Tensor) -> Tensor:
            case = self.read_case() if self.read_case else None
            if case is None:
                raise RuntimeError("the client was called without a case; route D did not deliver")
            route = [int(v) for v in case["route"]]
            edges = [[int(a), int(b)] for a, b in case["edges"]]
            reply = self.ask(route, edges)
            index = reply.get("label_index")
            if index is None:
                raise RuntimeError("the brain returned no answer: %r" % (reply,))
            calls.append({"route": route, "edges": edges, "reply": reply})
            # Appendix B's frozen out-rule, exactly: every channel 1.0, +1 at the label channel of
            # row 0. `decode` refuses an all-zero effect, so a 1.0 baseline also keeps it decodable.
            out = torch.full_like(value, BASELINE)
            out[0, 0, index] = BASELINE + 1.0
            return out

    # ---- the brain's side
    print()
    if not os.path.isdir(os.path.join(v3, "rb")):
        print("REFUSED: no rb package under %s" % v3)
        return 1
    boundary = Boundary(v3)
    hello = boundary.hello
    print("  the brain worker : never held torch: %s, blocker installed: %s, cells: %s"
          % (hello.get("torch_absent"), (hello.get("blocker") or {}).get("blocker_installed"),
             hello.get("cells")))

    folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    runtime = None
    try:
        d_model = len(LABELS)
        nodes = ("A", "B", "C")
        decoders = {
            name: DecoderContract(
                decoder_id="decoder:%s:r1-rt-hosted-v1" % name, version=1, operation_id=CLIENT_ID,
                effect_kind="DECOMPOSITION_SIGNAL", labels=LABELS)
            for name in nodes
        }
        clients = {name: BrainClient() for name in nodes}
        runtime = NeuralCJTRuntime.create(
            Path(folder.name) / "hosted.sqlite3",
            config=CASformerConfig(d_model=d_model, num_heads=2, num_relations=6, num_layers=1,
                                   dropout=0.0, attention_dropout=0.0,
                                   initial_cutoff=0.01, initial_saturation=100.0),
            node_specs=tuple(CJTNodeSpec(name, CLIENT_ID) for name in nodes),
            topology=(),
            seed=7,
            decoder_contracts=decoders,
            extension_operations={
                name: ((OperationRegistration(
                    operation_id=CLIENT_ID, name=CLIENT_ID, relation_index=CLIENT_RELATION_INDEX,
                    admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
                    contract_id=contract.contract_id), clients[name]),)
                for name in nodes
            },
        )
        runtime.network.eval()
        for name in nodes:
            bank = runtime.network.node(name).operations
            clients[name].read_case = (
                lambda b=bank: getattr(b, "_active_case", None))
            clients[name].ask = boundary.ask
        print("  runtime created  : a client on each of %s, wired to the brain" % (nodes,))
        print("  peak so far      : %.1f MiB of the %.0f MiB laptop rule" % (peak_mib(), LIMIT_MIB))

        # ---- two ticks, with different cases, so a constant answer cannot pass
        ticks = [
            {"route": [0, 1, 2], "edges": [[0, 1]], "why": "the second leg is missing"},
            {"route": [0, 1, 2], "edges": [[0, 1], [1, 2]], "why": "every leg present"},
            {"route": [3, 4, 5, 6], "edges": [[3, 4], [4, 5]], "why": "the third leg is missing"},
        ]
        results = []
        for tick, spec in enumerate(ticks, 1):
            content = {"task_id": "native.route_dependency_audit/1",
                       "case_id": "hosted-%d" % tick,
                       "nodes": list(range(8)), "edges": spec["edges"], "route": spec["route"]}
            cause, artifact = runtime.make_input_cause(
                torch.tensor([[[1.0] * d_model] * 8]), tick=tick, content=content,
                goal_context={"goal": "r1-rt hosted"}, candidate_operation_ids=(CLIENT_ID,))
            prepared = runtime._prepare_inference(
                cause=cause, cjt_id="C", expected_symbol=None, opposite_symbol=None, settings=None,
                supplied_artifacts=(artifact,), resume_repair_id=None, write_memory=False)
            decoded = prepared.decoder.decode_artifact(prepared.candidate_effect,
                                                      prepared.candidate_artifact)
            want = oracle(spec["route"], spec["edges"])
            results.append({"tick": tick, "why": spec["why"], "want": want,
                            "runtime_said": decoded.get("symbol"),
                            "agree": decoded.get("symbol") == want})

        print()
        print("  what the RUNTIME'S OWN DECODER reported, tick by tick:")
        for r in results:
            print("    tick %d  %-26s oracle %-26s runtime %-26s %s"
                  % (r["tick"], r["why"], r["want"], r["runtime_said"],
                     "OK" if r["agree"] else "WRONG"))
        print()
        print("  what crossed the boundary:")
        for c in calls:
            print("    route %-22s edges %-22s -> %s"
                  % (c["route"], c["edges"], c["reply"].get("answer")))

        agree = sum(1 for r in results if r["agree"])
        distinct = len({r["runtime_said"] for r in results})
        same_as_brain = all(
            c["reply"].get("answer") == r["runtime_said"] for c, r in zip(calls, results))
        bank_left = getattr(runtime.network.node("C").operations, "_active_case", "MISSING")

        print()
        print("=" * 78)
        print("RESULT")
        print("  a client ran on the runtime's own path      : %s"
              % ("YES" if calls else "NO"))
        print("  it asked the brain across the boundary      : %s"
              % ("YES" if calls else "NO"))
        print("  the runtime's OWN decoder agreed with the oracle: %d of %d" % (agree, len(results)))
        print("  the answers were not constant               : %s (%d distinct)"
              % ("YES" if distinct > 1 else "NO", distinct))
        print("  the runtime's answer IS the brain's answer  : %s"
              % ("YES" if same_as_brain else "NO"))
        print("  the bank was left empty afterwards          : %s"
              % ("YES" if bank_left is None else repr(bank_left)))
        print("  peak memory %.1f MiB of the %.0f MiB laptop rule" % (peak_mib(), LIMIT_MIB))
        verdict = (len(calls) == len(results) and agree == len(results) and distinct > 1
                   and same_as_brain and bank_left is None)
        print("  VERDICT                                     : %s"
              % ("THE BRAIN ANSWERED A REAL RUNTIME TICK" if verdict else "NOT PROVED"))
        print("=" * 78)
        return 0 if verdict else 1
    except Exception as exc:  # noqa: BLE001 - the diagnosis is the point
        print()
        print("  FAILED: %s: %s" % (type(exc).__name__, str(exc)[:600]))
        import traceback
        traceback.print_exc(limit=10)
        print()
        print("=" * 78)
        print("RESULT: THE HOSTED PATH DID NOT COMPLETE")
        print("=" * 78)
        return 1
    finally:
        if runtime is not None:
            runtime.close()
        boundary.close()
        folder.cleanup()


if __name__ == "__main__":
    sys.exit(main())
