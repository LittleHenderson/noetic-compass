"""Prepare (NOT apply) route D's patch against a COPY of the frozen cas_cjt runtime.

WHAT ROUTE D IS
---------------
R1-RT wants the recipe brain where the runtime's operation module sits. Measured in appendix C, that
module is called with one tensor and an operation id, so the brain can no longer see the question —
only CASformer's attention projection of it. Route D passes the case to the operation, so the frozen
input rule keeps working on the clean case and the identity check keeps meaning what it says.

WHY THIS SCRIPT DOES NOT TOUCH THE FROZEN SOURCE
------------------------------------------------
Where the runtime source is frozen, a package edit needs a new seal and the owner's line. This
script therefore copies the runtime into a scratch directory and patches the COPY. Nothing under
`controller_r6_restoration_op13` is written to.

WHAT IT PROVES
--------------
1. Every anchor it edits exists, and the patch applies cleanly.
2. All 34 modules still compile after the patch (`compileall`).
3. Each changed line is shown, so the diff can be read rather than trusted.

Usage:
    C:\\Python314\\python.exe -B prepare_route_d_patch.py [--apply-to <dir>]
"""
from __future__ import annotations

import os
import py_compile
import shutil
import sys
from typing import List, Tuple

FROZEN = (r"C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation"
          r"\controller_r6_restoration_op13\source_r6\cas_cjt")
SCRATCH = r"C:\Users\wakil\Documents\Codex\2026-10-16\_route_d_patch\cas_cjt"

# ----------------------------------------------------------------------------- the four edits
#: (relative file, the exact text to find, the exact text to write, why)
#:
#: Every anchor below is copied from the frozen source AS IT IS, not from memory. The first draft of
#: this script guessed the signatures and two anchors matched nothing; the script refused and wrote
#: nothing, which is the behaviour that matters.
EDITS: List[Tuple[str, str, str, str]] = [
    (
        "neural.py",
        """from dataclasses import dataclass

import torch""",
        """from dataclasses import dataclass
from typing import Any, Mapping

import torch""",
        "neural.py gains the typing names the patch uses",
    ),
    (
        "neural.py",
        """    def forward(self, operation_id: str, value: Tensor) -> Tensor:
        registration = self.executable_registration(operation_id)""",
        """    def forward(
        self,
        operation_id: str,
        value: Tensor,
        case: Mapping[str, Any] | None = None,
    ) -> Tensor:
        # ROUTE D: `case` is the task's own content, passed through from the runtime so an
        # operation can see the QUESTION rather than only the attention's projection of it.
        # It is optional and defaults to None, so every existing caller behaves as before.
        registration = self.executable_registration(operation_id)""",
        "the operation bank accepts the case",
    ),
    (
        "neural.py",
        """        registration = self.executable_registration(operation_id)
        if not isinstance(value, Tensor):
            raise NeuralCJTError("operation input must be a torch.Tensor")
        result = self.modules_by_operation[registration.operation_id](value)""",
        """        registration = self.executable_registration(operation_id)
        if not isinstance(value, Tensor):
            raise NeuralCJTError("operation input must be a torch.Tensor")
        # ROUTE D: hold the case where the operation module can READ it. An operation's `forward`
        # takes only `value`, so the case cannot arrive as an argument; it is exposed as an
        # attribute and cleared in a finally so it cannot leak into another call.
        #
        # The first version of this patch passed the case IN and then dropped it, which would have
        # left the operation unable to read it while looking correct at the call site. Found by
        # importing the patched module and reading what the bank actually did with `case`.
        self._active_case = case
        try:
            result = self.modules_by_operation[registration.operation_id](value)
        finally:
            self._active_case = None""",
        "the bank holds the case where the operation can read it",
    ),
    (
        "neural.py",
        """        transformed = self.operations(operation_id, projected_effect)""",
        """        transformed = self.operations(operation_id, projected_effect, self._active_case)""",
        "the node hands the active case to the operation",
    ),
    (
        "neural.py",
        """    def forward(
        self,
        x: Tensor,
        control: CASControl,
        *,
        operation_id: str,
    ) -> NeuralCJTProposal:""",
        """    def set_active_case(self, case: Mapping[str, Any] | None) -> None:
        \"\"\"ROUTE D: record the case for the duration of one forward pass.\"\"\"
        self._active_case = case

    def forward(
        self,
        x: Tensor,
        control: CASControl,
        *,
        operation_id: str,
    ) -> NeuralCJTProposal:""",
        "the node gains a place to hold the case",
    ),
    (
        "neural.py",
        """        self.operations = RegisteredOperationBank(config)""",
        """        self.operations = RegisteredOperationBank(config)
        self._active_case: Mapping[str, Any] | None = None  # ROUTE D""",
        "the node initialises the holder",
    ),
    (
        "network.py",
        """        control: CASControl,
    ) -> NeuralCJTProposal:
        with operation_event("forward", {"cjt_id": cjt_id, "boundary": "NeuralCJTNetwork.forward_node", "input_shape": str(tuple(x.shape)) if isinstance(x, Tensor) else type(x).__name__, "input_dtype": str(x.dtype) if isinstance(x, Tensor) else "non_tensor"}):
            spec = self.spec(cjt_id)
            return self.node(cjt_id)(x, control, operation_id=spec.operation_id)""",
        """        control: CASControl,
        case: Mapping[str, Any] | None = None,
    ) -> NeuralCJTProposal:
        # ROUTE D: the case travels with the call so the operation can see it. Optional, so
        # every existing caller keeps the old behaviour.
        with operation_event("forward", {"cjt_id": cjt_id, "boundary": "NeuralCJTNetwork.forward_node", "input_shape": str(tuple(x.shape)) if isinstance(x, Tensor) else type(x).__name__, "input_dtype": str(x.dtype) if isinstance(x, Tensor) else "non_tensor"}):
            spec = self.spec(cjt_id)
            node = self.node(cjt_id)
            node.set_active_case(case)
            try:
                return node(x, control, operation_id=spec.operation_id)
            finally:
                node.set_active_case(None)""",
        "the network passes the case to the node and clears it afterwards",
    ),
    (
        "runtime.py",
        """        proposal = self.network.forward_node(
            cjt_id,
            materialized.cause_tensor,
            materialized.control,
        )""",
        """        proposal = self.network.forward_node(
            cjt_id,
            materialized.cause_tensor,
            materialized.control,
            cause.content,  # ROUTE D: the task's own content, so the operation sees the question
        )""",
        "the runtime hands the case to the network",
    ),
]


def main() -> int:
    global FROZEN
    apply_to = None
    if "--apply-to" in sys.argv:
        apply_to = sys.argv[sys.argv.index("--apply-to") + 1]
    if "--source" in sys.argv:
        # WHICH cas_cjt this patches. Measured: GB3's carrier ships its OWN cas_cjt (29 modules)
        # beside its own casformer, and the `gb` scaffold uses THAT one, not the R6 source
        # (34 modules). They are different trees and the anchors happen to match in both. The
        # source is therefore a parameter with a default, never an assumption.
        FROZEN = os.path.abspath(sys.argv[sys.argv.index("--source") + 1])
    target = apply_to or SCRATCH

    print("=" * 74)
    print("ROUTE D PATCH, PREPARED AGAINST A COPY")
    print("=" * 74)
    print("  frozen source (never written to): %s" % FROZEN)
    print("  target of the patch             : %s" % target)

    if apply_to:
        if os.path.abspath(target).lower() == os.path.abspath(FROZEN).lower():
            print("REFUSED: the target IS the frozen source.")
            return 1
        # `--apply-to` must still start from a COPY of the frozen source; the flag chooses WHERE
        # the copy goes, not whether one is made. The first version of this read the target
        # directly and failed on a directory that did not exist yet.
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copytree(FROZEN, target)
        print("  copied the frozen source into the requested target")
    else:
        shutil.rmtree(os.path.dirname(target), ignore_errors=True)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copytree(FROZEN, target)
    print("  files in the patched tree: %d"
          % sum(len(f) for _, _, f in os.walk(target)))

    print()
    print("=" * 74)
    print("ANCHOR CHECKS AND EDITS")
    print("=" * 74)
    cache: dict = {}
    problems = 0
    for rel, old, new, why in EDITS:
        path = os.path.join(target, rel)
        if rel not in cache:
            cache[rel] = open(path, encoding="utf-8").read()
        text = cache[rel]
        n = text.count(old)
        if n != 1:
            print("  REFUSED %-12s anchor found %d times (must be exactly 1): %s"
                  % (rel, n, why))
            problems += 1
            continue
        cache[rel] = text.replace(old, new, 1)
        print("  OK      %-12s %s" % (rel, why))

    if problems:
        print()
        print("%d anchor(s) did not match; nothing was written." % problems)
        return 1

    for rel, text in cache.items():
        with open(os.path.join(target, rel), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    print()
    print("=" * 74)
    print("COMPILE CHECK: every module in the patched tree")
    print("=" * 74)
    bad = []
    total = 0
    for base, _dirs, files in os.walk(target):
        for name in files:
            if not name.endswith(".py"):
                continue
            total += 1
            path = os.path.join(base, name)
            try:
                # Compile in memory. `py_compile` to os.devnull fails on Windows, which is a
                # quirk of the devnull name and not a problem with the patch.
                with open(path, encoding="utf-8") as fh:
                    compile(fh.read(), path, "exec")
            except (SyntaxError, ValueError) as exc:
                bad.append("%s: %s" % (name, exc))
    print("  %d of %d module(s) compile" % (total - len(bad), total))
    for b in bad:
        print("   ", b)

    print()
    print("=" * 74)
    print("THE CHANGED LINES")
    print("=" * 74)
    for rel in cache:
        old_lines = open(os.path.join(FROZEN, rel), encoding="utf-8").read().splitlines()
        new_lines = cache[rel].splitlines()
        added = [l for l in new_lines if l not in old_lines]
        print("  %s: +%d line(s)" % (rel, len(added)))
        for l in added:
            print("     + %s" % l[:104])

    print()
    print("=" * 74)
    print("RESULT: %s" % ("PATCH PREPARED AND COMPILES" if not bad else "COMPILE PROBLEMS"))
    print("        nothing under the frozen source was written to")
    print("=" * 74)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
