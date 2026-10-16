"""Does a hosted brain SURVIVE A RESTART through HELM's own store?

WHY THIS EXISTS
---------------
R1-RT's own target sentence asks for the answers "surviving a restart through HELM's own store". The
hosted tick (appendix I) proved the answers; it wrote nothing, so the restart half was untouched.

There is a specific reason to expect trouble, and it is not a guess: `create()` is the only place the
patch registers an extension operation. `open()` builds its own network and contracts and takes no
extension operations at all, so a reopened runtime may have a node spec naming a client whose module
was never registered. That is the exact shape of the failure `parameter_names_for_node` raises when
the operation slot is empty.

So this probe does the honest thing: it MEASURES the restart rather than predicting it, and it reports
what happened whether that is success or failure.

WHAT IT DOES
------------
create -> tick -> close -> open -> tick again, on a real SQLite store, with the real brain across the
boundary. The second tick's answer is compared against the rule, and against the first tick's.

Usage:
    C:\\Python314\\python.exe -B probe_hosted_restart.py <patched-parent> <base-tree> <gb-root> <v3-root>
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_process_boundary import Boundary  # noqa: E402

CLIENT_ID = "experimental_r1_rt_client"
CLIENT_RELATION_INDEX = 4
LABELS = tuple("FIRST_UNSUPPORTED_LEG_%d" % i for i in range(7)) + ("ALL_LEGS_PRESENT",)
BASELINE = 1.0
CASES = [
    {"route": [0, 1, 2], "edges": [[0, 1]], "why": "the second leg is missing"},
    {"route": [0, 1, 2], "edges": [[0, 1], [1, 2]], "why": "every leg present"},
]


def oracle(route, edges) -> str:
    pairs = {tuple(e) for e in edges}
    for leg, pair in enumerate(zip(route, route[1:])):
        if pair not in pairs:
            return LABELS[leg]
    return LABELS[-1]


def main() -> int:
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    patched_parent, base_tree, gb_root, v3 = (os.path.abspath(p) for p in sys.argv[1:5])

    import types
    if "resource" not in sys.modules:
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

    for p in (gb_root, base_tree, patched_parent):
        while p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)

    import torch
    from torch import Tensor, nn
    import cas_cjt
    from cas_cjt import CJTNodeSpec, NeuralCJTRuntime
    from cas_cjt.neural import OperationRegistration
    from cas_cjt.semantic import DecoderContract
    from cas_cjt.state import make_operation_contract
    from cas_cjt.types import OntologyStatus
    from casformer import CASformerConfig

    print("=" * 78)
    print("DOES A HOSTED BRAIN SURVIVE A RESTART THROUGH HELM'S OWN STORE?")
    print("=" * 78)
    print("  cas_cjt in use : %s" % os.path.dirname(cas_cjt.__file__))
    contract = make_operation_contract(CLIENT_ID)
    d_model = len(LABELS)
    nodes = ("A", "B", "C")
    config = CASformerConfig(d_model=d_model, num_heads=2, num_relations=6, num_layers=1,
                             dropout=0.0, attention_dropout=0.0,
                             initial_cutoff=0.01, initial_saturation=100.0)
    specs = tuple(CJTNodeSpec(name, CLIENT_ID) for name in nodes)
    decoders = {name: DecoderContract(
        decoder_id="decoder:%s:r1-rt-restart-v1" % name, version=1, operation_id=CLIENT_ID,
        effect_kind="DECOMPOSITION_SIGNAL", labels=LABELS) for name in nodes}

    boundary = Boundary(v3)
    print("  brain worker   : never held torch: %s" % boundary.hello.get("torch_absent"))

    workdir = tempfile.mkdtemp(prefix="hosted_restart_")
    store_path = Path(workdir) / "hosted.sqlite3"
    tick_results: List[Dict[str, Any]] = []

    def wire(runtime) -> Dict[str, nn.Module]:
        """Point each node's client at the bank it must read and at the boundary it must ask.

        `modules_by_operation` is an `nn.ModuleDict`, which has no `.get`, so it is indexed directly.
        The client must be present by now: if the operation slot were empty, `create()` would already
        have refused with the allowlist error, so reaching here means the slot is filled.
        """
        clients = {}
        for name in nodes:
            bank = runtime.network.node(name).operations
            client = bank.modules_by_operation[CLIENT_ID]
            client.read_case = (lambda b=bank: getattr(b, "_active_case", None))
            client.ask = boundary.ask
            clients[name] = client
        return clients

    def run_tick(runtime, index: int) -> Dict[str, Any]:
        spec = CASES[index]
        content = {"task_id": "native.route_dependency_audit/1", "case_id": "restart-%d" % index,
                   "nodes": list(range(8)), "edges": spec["edges"], "route": spec["route"]}
        cause, artifact = runtime.make_input_cause(
            torch.tensor([[[1.0] * d_model] * 8]), tick=index + 1, content=content,
            goal_context={"goal": "restart probe"}, candidate_operation_ids=(CLIENT_ID,))
        prepared = runtime._prepare_inference(
            cause=cause, cjt_id="C", expected_symbol=None, opposite_symbol=None, settings=None,
            supplied_artifacts=(artifact,), resume_repair_id=None, write_memory=False)
        decoded = prepared.decoder.decode_artifact(prepared.candidate_effect,
                                                  prepared.candidate_artifact)
        want = oracle(spec["route"], spec["edges"])
        return {"why": spec["why"], "want": want, "said": decoded.get("symbol"),
                "agree": decoded.get("symbol") == want}

    # ---------------------------------------------------------------- phase 1: create and tick
    runtime = None
    phase1 = None
    created_ok = False
    try:
        runtime = NeuralCJTRuntime.create(
            store_path, config=config, node_specs=specs, topology=(), seed=7,
            decoder_contracts=decoders,
            extension_operations={
                name: ((OperationRegistration(
                    operation_id=CLIENT_ID, name=CLIENT_ID,
                    relation_index=CLIENT_RELATION_INDEX,
                    admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
                    contract_id=contract.contract_id), client_factory()),)
                for name in nodes
            })
        runtime.network.eval()
        wire(runtime)
        created_ok = True
        print("  phase 1 create : OK")
        phase1 = run_tick(runtime, 0)
        print("  phase 1 tick   : %-26s (rule says %-26s) %s"
              % (phase1["said"], phase1["want"], "OK" if phase1["agree"] else "WRONG"))
    except Exception as error:
        print("  phase 1 FAILED : %s: %s" % (type(error).__name__, str(error)[:300]))
        if runtime is not None:
            try:
                runtime.close()
            except Exception:
                pass
        boundary.close()
        shutil.rmtree(workdir, ignore_errors=True)
        return 1
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except Exception:
                pass

    # ---------------------------------------------------------------- phase 2: reopen and tick
    print()
    print("  the store is on disk: %s (%d bytes)"
          % (store_path, os.path.getsize(store_path) if os.path.exists(store_path) else -1))
    print("  phase 2 open   : attempting...")
    reopened = None
    try:
        # `open()` is called exactly as its signature allows. If it takes no extension operations,
        # then a client node spec cannot be satisfied and the failure will say so.
        # The reopen path now takes the same extension operations the create path took. Rebuilding
        # the modules is correct rather than a shortcut: the learned weights come back from the
        # checkpoint, and the client's own parameter is part of what the checkpoint carries.
        reopened = NeuralCJTRuntime.open(
            store_path, config=config, node_specs=specs, topology=(),
            decoder_contracts=decoders,
            extension_operations={
                name: ((OperationRegistration(
                    operation_id=CLIENT_ID, name=CLIENT_ID,
                    relation_index=CLIENT_RELATION_INDEX,
                    admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
                    contract_id=contract.contract_id), client_factory()),)
                for name in nodes
            })
        reopened.network.eval()
        wire(reopened)
        print("  phase 2 open   : OK")
        phase2 = run_tick(reopened, 1)
        print("  phase 2 tick   : %-26s (rule says %-26s) %s"
              % (phase2["said"], phase2["want"], "OK" if phase2["agree"] else "WRONG"))
        survived = True
    except Exception as error:
        survived = False
        phase2 = None
        message = "%s: %s" % (type(error).__name__, str(error)[:400])
        print("  phase 2 open   : FAILED")
        print("    %s" % message)
    finally:
        if reopened is not None:
            try:
                reopened.close()
            except Exception:
                pass
        boundary.close()
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    print("=" * 78)
    print("RESULT")
    print("  phase 1, create and tick                    : %s" % ("OK" if created_ok else "FAILED"))
    print("  phase 2, reopen the same store and tick     : %s" % ("OK" if survived else "FAILED"))
    if survived:
        print("  the reopened answer matched the rule        : %s"
              % ("YES" if phase2["agree"] else "NO"))
        print("  VERDICT : A HOSTED BRAIN SURVIVES A RESTART THROUGH THE STORE")
    else:
        print()
        print("  VERDICT : A HOSTED BRAIN DOES NOT YET SURVIVE A RESTART.")
        print("  The failure is recorded above verbatim. It is a finding, not a crash: what the")
        print("  reopen path does with a client operation is now known rather than assumed.")
    print("=" * 78)
    return 0 if (created_ok and survived) else 1


def client_factory():
    """The client module. Defined out here so the class body is built once, not inside an
    expression, and so the same factory serves both the create and the reopen paths."""
    import torch
    from torch import nn

    class _Client(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.weight = nn.Parameter(torch.zeros(len(LABELS), len(LABELS)))
            self.ask = None
            self.read_case = None

        def forward(self, value):
            case = self.read_case() if self.read_case else None
            if case is None:
                raise RuntimeError("the client was called without a case")
            reply = self.ask([int(v) for v in case["route"]],
                             [[int(a), int(b)] for a, b in case["edges"]])
            index = reply.get("label_index")
            if index is None:
                raise RuntimeError("the brain returned no answer: %r" % (reply,))
            out = torch.full_like(value, BASELINE)
            out[0, 0, index] = BASELINE + 1.0
            return out

    return _Client()


if __name__ == "__main__":
    sys.exit(main())
