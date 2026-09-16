"""Check the frozen proof gate with candidate-solving entry points disabled."""
from pathlib import Path
from hashlib import sha256
import json
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from cncm.canonical import canonical_json
from cncm.math_kernel import check_math_step, verify_math_receipt
from cncm.math_model import MathClaim, MathClaimStatus, MathStepOperation, MathStepProposal, MathStepReceipt
from cncm.math_parser import parse_math_statement
from cncm.model import Provenance
import cncm.math_engine as engine

def run_case(notation, result, accepted):
    claim = MathClaim.create(
        statement=parse_math_statement(notation, declared_variables=("y",)),
        status=MathClaimStatus.ASSUMED,
        provenance=(Provenance("design_fixture", "formal-assumption", notation),))
    proposal = MathStepProposal.create(
        operation=MathStepOperation.VERIFY_LINEAR_SOLUTION,
        premise_claim_ids=(claim.claim_id,),
        proposed_conclusion=parse_math_statement("y="+result, declared_variables=("y",)))
    receipt = check_math_step(proposal, (claim,))
    assert receipt.accepted is accepted
    assert verify_math_receipt(proposal, (claim,), receipt)
    forged = MathStepReceipt.create(proposal=proposal, accepted=True,
        reconstructed_conclusion=proposal.proposed_conclusion)
    forged_accepted = verify_math_receipt(proposal, (claim,), forged)
    if not accepted:
        assert not forged_accepted
    return {"input": notation, "candidate": result, "expected_accepted": accepted,
        "claim": claim.to_dict(), "proposal": proposal.to_dict(), "receipt": receipt.to_dict(),
        "resealed_forgery_accepted": forged_accepted}

def main():
    target = Path(__file__).with_name("receipt.json")
    assert not target.exists(), "retain earlier evidence"
    with patch.object(engine, "solve_linear_equation", side_effect=AssertionError("solver invoked")), \
         patch.object(engine, "verify_math_result", side_effect=AssertionError("solver regrader invoked")):
        rows = [run_case(*case) for case in (
            ("2*y+1=11", "5", True), ("2*y+1=11", "6", False),
            ("2*y+1=17", "5", False), ("2*y+1=17", "8", True),
            ("0*y+1=1", "5", False), ("0*y+1=2", "5", False))]
    sources = {}
    for name in ("math_kernel.py", "math_model.py", "math_normalize.py", "math_parser.py"):
        raw = (ROOT/"cncm"/name).read_bytes()
        sources["cncm/"+name] = {"bytes":len(raw), "sha256":sha256(raw).hexdigest()}
    body = {"schema_version":"cncm.derived-memory-design-probe/0.1",
        "cases":rows, "sources":sources, "candidate_solver_calls":0, "solver_regrader_calls":0,
        "boundary":"Frozen formal step gate only; no derived-memory implementation or world-fact claim.",
        "limitation":"The standalone checker has no external source custody or memory scope. The new coordinator must bind those."}
    with target.open("x", encoding="utf-8", newline="\n") as out:
        out.write(canonical_json(body)+"\n")
    print(json.dumps({"cases":len(rows),"receipt":str(target),"sha256":sha256(target.read_bytes()).hexdigest()}))

if __name__ == "__main__":
    main()

