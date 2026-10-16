"""Prepare (NOT apply) the two edits the R1-RT client needs, against a COPY of the frozen runtime.

WHY TWO EDITS AND NOT ONE
-------------------------
Route D's patch (appendix D) passes the task's content to the operation. That is necessary but not
sufficient to host the recipe brain, because of two measured facts about the frozen runtime:

1. `make_operation_contract` raises `StateContractError("unknown operation identity")` for any
   operation id outside a fixed four-entry table (`cas_cjt/state.py:110-151`). So `create()` refuses a
   node spec whose operation is the client's, which was measured, not read:
   `CJTNodeSpec('C', 'experimental_r1_rt_client')` fails with exactly that error.
2. `register_operation` REFUSES to replace a built-in identity
   (`neural.py:217-218`), so the client cannot take the `^6` slot. It can only be ADDED.

So the client needs one more edit, and it is a DATA edit, not a logic edit: one entry in the frozen
operation table. The consequence is stated in the appendix rather than hidden: the task's own decoder
contract (`native_task.task_decoder_contracts`) requires `operation_id == "^6"`, so a run with the
client BYPASSES the task's decoder contract and supplies its own. That changes what "the same task"
can be claimed, and the appendix must say so.

WHAT THIS SCRIPT DOES NOT DO
----------------------------
It does not touch `controller_r6_restoration_op13`. It copies into scratch and patches the copy.

Usage:
    C:\\Python314\\python.exe -B prepare_client_patch.py [--apply-to <dir>]
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare_route_d_patch import EDITS as ROUTE_D_EDITS, FROZEN  # noqa: E402

SCRATCH = r"C:\Users\wakil\Documents\Codex\2026-10-16\_client_patch\cas_cjt"

#: The one extra edit. Anchored on the closing brace of `_OPERATION_DETAILS`, which is preceded by
#: the `^8` block exactly as the frozen source has it.
CLIENT_EDITS: List[Tuple[str, str, str, str]] = [
    (
        "state.py",
        """        "ASSOCIATION_SIGNAL",
    ),
}""",
        """        "ASSOCIATION_SIGNAL",
    ),
    # R1-RT CLIENT: one entry so `make_operation_contract` knows the identity. This is a DATA edit;
    # no logic in the runtime changes. The identity is deliberately experimental, which is what
    # `register_operation` requires of anything that is not a built-in.
    "experimental_r1_rt_client": (
        "experimental_r1_rt_client",
        OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
        "prototype.op.r1_rt_client.v1",
        "cas.cjt.operation.r1-rt-client.experimental/0.1",
        (CauseKind.IDEA, CauseKind.EFFECT),
        "DECOMPOSITION_SIGNAL",
    ),
}""",
        "the frozen operation table gains the client's identity",
    ),
    (
        "runtime.py",
        """        operation_initializers: Mapping[str, Mapping[str, Tensor]] | None = None,""",
        """        operation_initializers: Mapping[str, Mapping[str, Tensor]] | None = None,
        extension_operations: Mapping[str, Sequence[tuple[Any, Any]]] | None = None,""",
        "create() gains a way to be handed an extension operation",
    ),
    (
        "runtime.py",
        """        checkpoint = encode_module_checkpoint(network)""",
        """        # R1-RT CLIENT: an extension operation's module must exist BEFORE the state envelope is
        # built, because `parameter_names_for_node` refuses a node whose operation slot is empty:
        # "node plasticity allowlist selected no parameters". `operation_initializers` cannot serve
        # as the way in, because it looks the module up BY operation id and so requires the module
        # to be there already. Measured, not assumed: the client node spec failed inside create()
        # with exactly that error until this block existed.
        if extension_operations is not None:
            for cjt_id, items in extension_operations.items():
                bank = network.node(cjt_id).operations
                for registration, module in items:
                    bank.register_operation(registration, module)
        checkpoint = encode_module_checkpoint(network)""",
        "create() registers extension operations before the envelope is sealed",
    ),
    (
        "runtime.py",
        """        decoder_contracts: Mapping[str, DecoderContract] | None = None,
        semantic_lineage: Mapping[str, Any] | None = None,
        enable_teaching: bool = False,
    ) -> "NeuralCJTRuntime":
        network = NeuralCJTNetwork(config, node_specs, topology=topology)""",
        """        decoder_contracts: Mapping[str, DecoderContract] | None = None,
        semantic_lineage: Mapping[str, Any] | None = None,
        extension_operations: Mapping[str, Sequence[tuple[Any, Any]]] | None = None,
        enable_teaching: bool = False,
    ) -> "NeuralCJTRuntime":
        network = NeuralCJTNetwork(config, node_specs, topology=topology)
        # R1-RT CLIENT: `open()` needs the same way in that `create()` has. Without it a reopened
        # runtime has a node spec naming a client whose module was never registered, and the
        # checkpoint's key set no longer matches the network's. MEASURED, not predicted: reopening a
        # store created with a client failed with
        #     CheckpointError: checkpoint keys do not match the Neural CJT module
        # That error fires at `load_module_checkpoint` further down, which is why the registration
        # has to happen here, before the load, and not after it.
        if extension_operations is not None:
            for cjt_id, items in extension_operations.items():
                bank = network.node(cjt_id).operations
                for registration, module in items:
                    bank.register_operation(registration, module)""",
        "open() gains the same way in, before its checkpoint is compared",
    ),
]

EDITS = list(ROUTE_D_EDITS) + CLIENT_EDITS


def compile_all(root: str) -> Tuple[int, List[str]]:
    """Compile every module in memory and return the count and any failures."""
    ok, bad = 0, []
    for base, _dirs, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(base, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    source = fh.read()
                compile(source, path, "exec")
                ok += 1
            except (SyntaxError, OSError) as error:
                bad.append("%s: %s" % (os.path.relpath(path, root), error))
    return ok, bad


def main() -> int:
    target = SCRATCH
    if "--apply-to" in sys.argv:
        target = os.path.abspath(sys.argv[sys.argv.index("--apply-to") + 1])
    if os.path.abspath(target).rstrip("\\/").lower() == os.path.abspath(FROZEN).rstrip("\\/").lower():
        print("REFUSED: that is the frozen source. This script patches copies only.")
        return 1

    print("=" * 78)
    print("THE R1-RT CLIENT: ROUTE D'S PATCH PLUS ONE DATA EDIT")
    print("=" * 78)
    print("  source : %s" % FROZEN)
    print("  target : %s" % target)
    if not os.path.isdir(FROZEN):
        print("REFUSED: the frozen source is not at that path.")
        return 1

    if os.path.isdir(target):
        shutil.rmtree(target)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copytree(FROZEN, target)

    print()
    print("  %d edits, each anchored on text copied from the frozen source:" % len(EDITS))
    applied = 0
    for index, (relative, old, new, why) in enumerate(EDITS, 1):
        path = os.path.join(target, relative)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if text.count(old) != 1:
            print("  REFUSED: anchor %d in %s matches %d times: %s"
                  % (index, relative, text.count(old), why))
            return 1
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.replace(old, new, 1))
        applied += 1
        print("    %2d  %-12s %s" % (index, relative, why))

    count, failures = compile_all(target)
    print()
    print("  modules that compile : %d of %d" % (count - len(failures), count))
    if failures:
        for f in failures[:8]:
            print("    FAILED %s" % f)
        return 1
    print("  edits applied        : %d of %d" % (applied, len(EDITS)))
    print()
    print("=" * 78)
    print("RESULT: the client's patch is prepared at %s" % target)
    print("  Nothing under controller_r6_restoration_op13 was written to.")
    print("  FOUR edits are now required beyond route D, where the design expected none. Three are")
    print("  small (a table entry, and two blocks); the fourth is open(), and the consequences the")
    print("  appendix must state are:")
    print("    (a) the task's own decoder contract pins ^6, so a client run BYPASSES it and supplies")
    print("        its own, which changes what \"the same task\" can be claimed;")
    print("    (b) nothing in the frozen runtime can replace a built-in operation, so a client can")
    print("        only ever be an ADDED identity, never the ^6 the task's decoder names.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
