"""Add the round-17 amendment-log rows to the council directive.

IDEMPOTENT PER ROW, and the guard is the ROW ITSELF. Rows are inserted ABOVE the round-13 anchor.

Usage:
    C:\\Python314\\python.exe -B add_directive_round17.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

ROWS = [
    (
        "the client operation is built and measured",
        "| 2026-10-16 | **The client operation is BUILT AND MEASURED: the runtime calls it and hands "
        "it the task's own content.** A copy of the frozen runtime carrying eleven edits \u2014 route "
        "D's nine plus two more \u2014 creates a runtime whose node spec names an experimental client "
        "operation. `runtime._prepare_inference` returned `_PreparedInference`; the client RAN on the "
        "runtime's own path, once, on node `C`, and received `case_id='client-probe'`; the bank was "
        "left empty afterwards; peak **220.1 MiB** of the 300 MiB laptop rule. All 34 of 34 modules "
        "compile after the patch. This answers items 1, 2 and 4 of appendix E section 7. Recorded as "
        "appendix G. |",
    ),
    (
        "the client costs three edits, not one",
        "| 2026-10-16 | **The client costs THREE edits where route D assumed one, and both extras "
        "were forced by measured refusals rather than guessed.** (1) `make_operation_contract` raises "
        "`StateContractError(\"unknown operation identity\")` for anything outside a four-entry table "
        "(`state.py:110-151`) \u2014 measured by trying it, not read. (2) Nothing can replace a "
        "built-in (`neural.py:217-218`), so a client can only ever be an **added** identity, never the "
        "`^6` the task's decoder names. (3) The extension module must exist **before** the state "
        "envelope is built: `parameter_names_for_node` refuses an empty operation slot with \"node "
        "plasticity allowlist selected no parameters\", and `operation_initializers` cannot serve as "
        "the way in because it looks the module up **by operation id** and so requires it to be there "
        "already. |",
    ),
    (
        "what a client run bypasses, and what it cannot claim",
        "| 2026-10-16 | **What a client run bypasses, stated so the claim cannot overreach.** "
        "`native_task.task_decoder_contracts` requires `operation_id == \"^6\"` and refuses anything "
        "else, so a client run **cannot use the task's own decoder contract** and must supply its own "
        "\u2014 and that must be **version 2** to match the frozen output rule (appendix B), which in "
        "turn requires an exact explicit semantic lineage. So the honest description of a client run "
        "is *HELM's runtime, its store, its verifier and its repair machinery, answering the "
        "route-dependency task with the recipe brain in place of `^6` for the node that was asked* "
        "\u2014 not *the task ran exactly as its contract defines it*. |",
    ),
    (
        "four defects found while building the client",
        "| 2026-10-16 | **Four defects found by running, kept on the page.** (1) **A cleanup error "
        "masked an entire run**: on Windows the SQLite handle can outlive `runtime.close()` for a "
        "moment and the `WinError 32` from the temporary directory replaced everything the probe had "
        "measured. A tidy-up failure must never hide a measurement, so cleanup errors are now ignored. "
        "(2) **A version-1 decoder refuses the version-2 algorithm** \u2014 `SemanticDecodeError: v1 "
        "decoder requires the unchanged full-width algorithm`. (3) **The runtime refuses a network "
        "with fewer than three nodes**: \"a network state requires at least three typed BiasState "
        "records\". (4) **`operation_initializers` looked like the injection point and is not**, for "
        "the reason recorded above. |",
    ),
]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = (Path(sys.argv[1]) / "docs" / "working"
              / "helm_tks_noetic_council_directive_2026_10_16.md")
    if not target.is_file():
        print("REFUSED: no directive at %s" % target)
        return 1
    text = target.read_text(encoding="utf-8")

    if "--list" in sys.argv:
        for label, row in ROWS:
            print("%-8s %s" % ("PRESENT" if row in text else "ABSENT", label))
        return 0

    if len({r for _l, r in ROWS}) != len(ROWS):
        print("REFUSED: two rows are identical, so the presence test cannot count insertions.")
        return 1

    missing = [(label, row) for label, row in ROWS if row not in text]
    if not missing:
        print("all %d rows are already present; nothing to do" % len(ROWS))
        return 0
    if ANCHOR not in text:
        print("REFUSED: anchor not found: %r" % ANCHOR)
        return 1
    if text.count(ANCHOR) != 1:
        print("REFUSED: anchor appears %d times" % text.count(ANCHOR))
        return 1

    block = "".join(row + "\n" for _l, row in missing)
    target.write_text(text.replace(ANCHOR, block + ANCHOR), encoding="utf-8")
    for label, _row in missing:
        print("ADDED   %s" % label)
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
