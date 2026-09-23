"""RT8 supplementary checks. Pure Python, torch blocked, visible/record files only."""
import importlib.abc, json, pathlib, sys, collections
class _B(importlib.abc.MetaPathFinder):
    def find_spec(self, n, p=None, t=None):
        if n.split(".")[0] in ("torch", "numpy"):
            raise ImportError("NOT_RUN_TORCH_DEPENDENCY: " + n)
sys.meta_path.insert(0, _B())
ROOT = pathlib.Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"; DATA = LAB / "data/q3_v0_7"; REC = ROOT / "records/q4_authorized_20260922"
sys.path.insert(0, str(LAB))
import q3_load, learner_q4_decoder as dec
pin = q3_load.check_pins(DATA)
plan = json.loads((REC / "run_001/plan.json").read_text(encoding="utf-8"))
print("check_pins OK; pinned manifest", pin["manifest_sha256"][:16], "| q3_load.manifest_sha", q3_load.manifest_sha(DATA)[:16], "| run plan manifest_sha256", plan["manifest_sha256"][:16], "| equal", q3_load.manifest_sha(DATA) == plan["manifest_sha256"])
res = json.loads((REC / "run_001/result.json").read_text(encoding="utf-8"))
print("result.json engineering_status", res["engineering_status"], "actual_updates", res["actual_updates"], "dev_by_depth", res["dev_by_depth"])
ups = [json.loads(l) for l in (REC / "run_001/updates.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
print("updates.jsonl rows", len(ups), "last update", ups[-1]["update"])
preds = [json.loads(l) for l in (REC / "run_001/dev_predictions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
cons = sum(1 for p in preds if p["outcome"] == "GENERATED" and len(dec.ast_to_tokens(p["ast"])) == p["steps"] and dec.tokens_to_ast(dec.ast_to_tokens(p["ast"])) == p["ast"])
print("smoke dev_predictions: rows", len(preds), "| GENERATED + re-encode length == steps + round-trip:", cons, "| steps values", collections.Counter(p["steps"] for p in preds))
print("torch/numpy loaded:", sorted(m for m in sys.modules if m.split(".")[0] in ("torch", "numpy")) or "NONE")
