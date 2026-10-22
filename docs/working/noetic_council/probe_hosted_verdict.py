"""What does HELM's verifier actually DO with a hosted brain's answer?

WHY THIS EXISTS
---------------
Reading `verifier.py:304-340` suggests something that matters a great deal and had not been measured.
The chain is:

    CUTOFF region            -> ABSTAIN
    BREAKDOWN region         -> QUARANTINE
    NOT canonical-admitted   -> ABSTAIN, reason EXPERIMENTAL_OPERATION_NOT_AUTHORITY_ADMITTED
    no evidence              -> ABSTAIN
    content matches expected -> ACCEPT
    content matches opposite -> REPAIR
    anything else            -> REPAIR

The client's operation is `EXPERIMENTAL_OPEN_SEMANTICS`, so the third test fires **before the semantic
comparison is ever reached**. If that is right, then:

- the runtime never ACCEPTS a hosted answer, and
- it never REPAIRS one either, because REPAIR is only reachable through the semantic comparison.

That would mean R1-RT's third requirement — "a real nested repair" — cannot be met by a client
operation as things stand, and the honest thing is to measure it rather than reason about it.

WHAT IT DOES
------------
One hosted tick, with the brain answering across the boundary, and the verifier's receipt printed in
full. Only one tick is needed: the question is what the verifier does, not how many times it does it.

Usage:
    C:\\Python314\\python.exe -B probe_hosted_verdict.py <patched-parent> <base-tree> <gb-root> <v3-root>
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_process_boundary import Boundary  # noqa: E402
from probe_hosted_restart import client_factory, oracle, LABELS, CLIENT_ID, CLIENT_RELATION_INDEX  # noqa: E402


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
    import cas_cjt
    from cas_cjt import CJTNodeSpec, NeuralCJTRuntime
    from cas_cjt.neural import OperationRegistration
    from cas_cjt.semantic import DecoderContract
    from cas_cjt.state import make_operation_contract
    from cas_cjt.types import OntologyStatus
    from casformer import CASformerConfig

    print("=" * 78)
    print("WHAT DOES HELM'S VERIFIER DO WITH A HOSTED BRAIN'S ANSWER?")
    print("=" * 78)
    contract = make_operation_contract(CLIENT_ID)
    print("  the client's contract status : %s" % contract.ontology_status)
    print("  cas_cjt in use               : %s" % os.path.dirname(cas_cjt.__file__))

    d_model = len(LABELS)
    nodes = ("A", "B", "C")
    config = CASformerConfig(d_model=d_model, num_heads=2, num_relations=6, num_layers=1,
                             dropout=0.0, attention_dropout=0.0,
                             initial_cutoff=0.01, initial_saturation=100.0)
    specs = tuple(CJTNodeSpec(name, CLIENT_ID) for name in nodes)
    decoders = {name: DecoderContract(
        decoder_id="decoder:%s:r1-rt-verdict-v1" % name, version=1, operation_id=CLIENT_ID,
        effect_kind="DECOMPOSITION_SIGNAL", labels=LABELS) for name in nodes}

    boundary = Boundary(v3)
    workdir = tempfile.mkdtemp(prefix="hosted_verdict_")
    runtime = None
    try:
        runtime = NeuralCJTRuntime.create(
            Path(workdir) / "verdict.sqlite3", config=config, node_specs=specs, topology=(), seed=7,
            decoder_contracts=decoders,
            extension_operations={name: ((OperationRegistration(
                operation_id=CLIENT_ID, name=CLIENT_ID, relation_index=CLIENT_RELATION_INDEX,
                admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
                contract_id=contract.contract_id), client_factory()),) for name in nodes})
        runtime.network.eval()
        for name in nodes:
            bank = runtime.network.node(name).operations
            client = bank.modules_by_operation[CLIENT_ID]
            client.read_case = (lambda b=bank: getattr(b, "_active_case", None))
            client.ask = boundary.ask

        route, edges = [0, 1, 2], [[0, 1]]
        content = {"task_id": "native.route_dependency_audit/1", "case_id": "verdict-1",
                   "nodes": list(range(8)), "edges": edges, "route": route}
        cause, artifact = runtime.make_input_cause(
            torch.tensor([[[1.0] * d_model] * 8]), tick=1, content=content,
            goal_context={"goal": "verdict probe"}, candidate_operation_ids=(CLIENT_ID,))
        prepared = runtime._prepare_inference(
            cause=cause, cjt_id="C", expected_symbol=None, opposite_symbol=None, settings=None,
            supplied_artifacts=(artifact,), resume_repair_id=None, write_memory=False)

        receipt = prepared.verifier_receipt
        print()
        print("  the brain answered       : %s" % oracle(route, edges))
        print("  the runtime decoded      : %s"
              % prepared.decoder.decode_artifact(prepared.candidate_effect,
                                                 prepared.candidate_artifact).get("symbol"))
        print()
        print("  the verifier's receipt:")
        for field in ("disposition", "semantic_outcome", "reason_codes", "repair_required"):
            print("    %-18s %s" % (field, getattr(receipt, field, "ABSENT")))
        print()
        print("  was a repair frame opened : %s" % (prepared.repair_frame is not None))
        print("  was a repair subgoal set   : %s" % (prepared.repair_subgoal is not None))
        print("  repair outcome             : %s" % (prepared.repair_outcome,))
        print("  operating region           : %s" % (prepared.region,))
        print("  audit_only                 : %s" % (prepared.audit_only,))

        disposition = str(getattr(receipt, "disposition", "")).split(".")[-1]
        reasons = list(getattr(receipt, "reason_codes", ()) or ())
        accepted = disposition == "ACCEPT"
        repairish = disposition in ("REPAIR", "QUARANTINE") or bool(getattr(receipt, "repair_required", False))

        print()
        print("=" * 78)
        print("RESULT")
        print("  the runtime ACCEPTED the brain's answer        : %s" % ("YES" if accepted else "NO"))
        print("  the runtime asked for a repair                 : %s" % ("YES" if repairish else "NO"))
        print("  the disposition was                            : %s" % disposition)
        print("  the reason was                                 : %s" % ", ".join(reasons))
        print()
        if not accepted and not repairish:
            print("  So the verifier neither accepts nor repairs a hosted answer. It ABSTAINS, and the")
            print("  reason code says why: the operation is not authority-admitted, and that test runs")
            print("  BEFORE the semantic comparison. A REPAIR is only reachable through that")
            print("  comparison, so a client operation can never reach one.")
            print()
            print("  CONSEQUENCE: R1-RT's third requirement, a real nested repair, cannot be met by a")
            print("  client operation as the design stands. Reaching it needs either the operation to")
            print("  be canonical-admitted, which `register_operation` forbids for anything but the")
            print("  frozen four, or a different route into the repair machinery.")
        elif accepted:
            print("  The verifier ACCEPTED the hosted answer.")
        else:
            print("  The verifier asked for a repair, so a nested repair can be driven from here.")
        print("=" * 78)
        return 0
    except Exception as exc:  # noqa: BLE001 - the diagnosis is the point
        print()
        print("  FAILED: %s: %s" % (type(exc).__name__, str(exc)[:600]))
        import traceback
        traceback.print_exc(limit=8)
        return 1
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except Exception:
                pass
        boundary.close()
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
