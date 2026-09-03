"""Assemble P6_AUDIT_PACKAGE.md for an independent auditor FROM THE FILES, never by retyping.

Every number an auditor sees is pulled verbatim from a committed script or a raw stdout receipt
in this directory. The narrative in NARRATIVE below states only record facts (what is and is not
committed) and the defect, and asks questions. It states no verdict on the science.

Run:  python build_p6_audit_package.py      ($0, control-plane only)
"""
import hashlib
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
COMMITTED = HERE.parent.parent / "CJT_PREC_CLOSURE" / "p6_order_test.py"
FILES = {
    "committed_script": COMMITTED,
    "committed_repro_stdout": HERE / "p6_committed_repro_stdout.txt",
    "committed_repro_time": HERE / "p6_committed_repro_time.txt",
    "committed_repro_env": HERE / "p6_committed_repro_env.txt",
    "heldout_script": HERE / "p6_heldout_repro.py",
    "heldout_stdout": HERE / "p6_heldout_repro_stdout.txt",
    "heldout_time": HERE / "p6_heldout_repro_time.txt",
}
OUT = HERE / "P6_AUDIT_PACKAGE.md"


def lf(p):
    return p.read_bytes().replace(b"\r\n", b"\n")


def sha(p):
    return hashlib.sha256(lf(p)).hexdigest()


NARRATIVE = """# P6 AUDIT PACKAGE -- does the specific order P > C > E > O have evidence of value?

**For an INDEPENDENT AUDITOR of a different model family.** Claude (built the script and this
correction) and Zhipu GLM (author of a proof sketch in the adjacent precedence lane) are recused.

## 0. Record facts (verifiable from git; the auditor is asked to trust none of the science)

- Repository branch under audit: `research/cmb-r1-rgm02-v1`, HEAD `1e58d7254d97c88effa609f7ad05ee2fca9b1aee`.
- The experiment script `cas_only_reasoner/CJT_PREC_CLOSURE/p6_order_test.py` was committed ONCE, in
  `1e58d725` (2026-09-02 21:29:49 -0700), the same commit whose message reports the results.
  There is NO earlier commit containing the registered prediction. "Written before running" is
  therefore not verifiable from the repository.
- The result numbers (0.9689, 0.9272, 0.9471, 0.8181, ...) appear in the COMMIT MESSAGE only.
  No raw stdout, receipt, result JSON, findings section, spec-sheet row or CHANGELOG row was
  committed for P6. The clean-room reproduction in section 2 is the first committed raw output.
- The script tests THREE fixed orders (CAS `(0,1,2,3)`, reversed `(3,2,1,0)`, one fixed
  non-CAS order `(2,0,3,1)`) plus a mechanism-free bag. It does NOT test all 24 orders.
- The script's own conclusion logic (lines 219-253) has three branches. The auditor is asked
  (Q5) whether any branch could ever have concluded that the specific CAS order has value.

## 1. The committed script, verbatim
"""

DEFECT = """
## 3. Clean-room finding: the "held-out" set is the training set

In `run_condition()` (committed lines 157-167) the training set is drawn with
`np.random.default_rng(1000 + sd)` and the "held-out" set with a FRESH `np.random.default_rng(1000 + sd)`
-- the same seed. Each world function draws its parameters and then its evidence from that one
stream, and `NTR == NTE == 1500`, so the two draws are identical. Checked before the correction
was written: `np.array_equal(Etr, Ete) and np.array_equal(ytr, yte)` is `True` for all 5 seeds in
all three world functions (15 of 15). Every accuracy the committed script prints is a training-fit
accuracy. The comment `# same world, fresh draw` (line 162) and the banner
`1500 train / 1500 held out` (line 173) are false.

## 4. The correction, verbatim -- the ONLY change is a genuinely fresh held-out draw

The committed script is left untouched. The correction loads the committed definitions (digest-
pinned), rebuilds the same training sets (asserted element-wise equal to the committed draw),
draws the held-out set from the same world parameters with seed stream `500000 + sd`, trains the
same arms with the same init seeds, steps and optimiser, and applies the same controls and the
same registered thresholds to the held-out numbers. Its positive control is that the train-fit
numbers must reproduce the committed numbers exactly.
"""

QUESTIONS = """
## 6. QUESTIONS -- answer every one, quoting line numbers

Q1. Is the finding in section 3 correct: in the committed script, is the held-out set identical to
    the training set for every seed and every world? If you disagree, show the draw that differs.
Q2. Does the correction in section 4 change ANYTHING other than the held-out draw (arms, orders,
    seeds, steps, learning rate, thresholds, controls, worlds)? List every difference you find.
Q3. On the corrected HELD-OUT numbers (section 5), which of the registered predictions (a), (b),
    (c) hold at the committed thresholds? Is the committed conclusion -- "order matters, CAS
    ordering does not; CAS_PRECEDENCE_VALUE_NOT_ESTABLISHED" -- supported, over-stated or
    under-stated by the held-out numbers?
Q4. Is the world generator an answer key for any arm? Is "order matters" (every chain arm beats
    the bag) confounded by capacity -- the bag arm has `U = 0`, i.e. fewer effective parameters --
    or by anything else? State the STRONGEST claim about generic sequencing this experiment
    supports, and the weakest.
Q5. Is there ANY evidence in this experiment for a value of the SPECIFIC order P > C > E > O beyond
    what any fixed order gets? Could any branch of the script's verdict logic (lines 219-253) ever
    have concluded that it has value? If not, what would a fair test of that question require?
Q6. Statistics: 5 seeds; thresholds 0.02 (a), 0.03 (b), 0.05 (negative control); the printed
    +/- is the seed standard deviation (ddof=1). Are the reported differences (for example
    +0.0219 in (a), -0.0136 in (c)) distinguishable from seed noise? Are the arms paired by seed
    (same world draw, same init seed per arm) and does that change the analysis?
Q7. Only 3 of 24 fixed orders were tested. What does that limit, exactly?
Q8. Record status: the numbers exist only in a commit message; the "registered prediction" is
    committed in the same commit as the results; no receipt was committed. What evidentiary status
    does the ORIGINAL run deserve, and what status does the clean-room reproduction plus
    correction deserve?
Q9. Any other shortcut, leak, or defect you can find in either script.

Then answer in one word each:
    SPECIFIC_CAS_ORDER_HAS_EVIDENCE_OF_VALUE: YES / NO / CANNOT_SAY
    GENERIC_SEQUENCING_HELPS_IN_THIS_WORLD:   YES / NO / CANNOT_SAY

Return EXACTLY ONE final line:
    P6_AUDIT_PASS:<the exact claim you certify>
    P6_AUDIT_PARTIAL:<what is unresolved>
    P6_AUDIT_FAIL:<the contradiction, shortcut or defect that invalidates the reported conclusion>
Do not fix anything. Do not redesign. State what is true.
"""


def fence(text, lang=""):
    return f"```{lang}\n{text.rstrip()}\n```\n"


def main():
    for k, p in FILES.items():
        if not p.exists():
            raise SystemExit(f"missing {k}: {p}")
    parts = [NARRATIVE]
    parts.append(f"sha256 (LF-normalised): `{sha(FILES['committed_script'])}`\n\n")
    parts.append(fence(lf(FILES["committed_script"]).decode("utf-8"), "python"))
    parts.append("\n## 2. Committed script, clean-room reproduction -- raw stdout, unedited\n\n")
    parts.append(f"environment: `{lf(FILES['committed_repro_env']).decode().strip().replace(chr(10), ' | ')}`; "
                 f"wall time: `{lf(FILES['committed_repro_time']).decode().strip().replace(chr(10), ' | ')}`\n\n")
    parts.append(fence(lf(FILES["committed_repro_stdout"]).decode("utf-8"), "text"))
    parts.append(DEFECT)
    parts.append(f"\nsha256 (LF-normalised) of the correction: `{sha(FILES['heldout_script'])}`\n\n")
    parts.append(fence(lf(FILES["heldout_script"]).decode("utf-8"), "python"))
    parts.append("\n## 5. The correction -- raw stdout, unedited\n\n")
    parts.append(f"wall time: `{lf(FILES['heldout_time']).decode().strip().replace(chr(10), ' | ')}`\n\n")
    parts.append(fence(lf(FILES["heldout_stdout"]).decode("utf-8"), "text"))
    parts.append(QUESTIONS)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
