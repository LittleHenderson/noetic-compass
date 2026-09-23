"""R4: scripted-logit replay through the repo's own free_decode + the smoke job's equality check.
Shows the decode/checker path CAN return exact depth-3 answers when logits carry them. No torch."""
import json, sys, pathlib
ROOT = pathlib.Path(sys.argv[1]); LAB = ROOT / "research" / "helm_cas_expression_lab"
sys.path.insert(0, str(LAB))
import learner_q4_decoder as dec
from learner_q4_representation import Bottleneck
cases = json.loads((ROOT / "records/q4_authorized_20260922/inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
exact = 0; steps = []
for c in cases:
    gold = dec.ast_to_tokens(c["checker_reference_ast"])
    def scripted(_b, prefix, gold=gold):
        return tuple(1.0 if k == gold[len(prefix)] else 0.0 for k in range(len(dec.TOKENS)))
    r = dec.free_decode(Bottleneck((0.0,)), scripted)
    exact += (r.ast == c["checker_reference_ast"])   # same comparison as q4_smoke_job.py:388
    steps.append(r.steps)
print("scripted-gold replay: exact %d/16 ; steps %s" % (exact, steps))
pred = cases[0]["original_learned_prediction"]["ast"]
print("saved prediction tokens:", [dec.TOKENS[t] for t in dec.ast_to_tokens(pred)])
print("saved prediction == any of 16 references:", sum(pred == c["checker_reference_ast"] for c in cases))
