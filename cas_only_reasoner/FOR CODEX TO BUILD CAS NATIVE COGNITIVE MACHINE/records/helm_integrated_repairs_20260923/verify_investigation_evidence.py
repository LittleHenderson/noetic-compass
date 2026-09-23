"""Read-only verification of the two preserved investigation bundles."""
import hashlib
import json
from pathlib import Path

CN = Path(__file__).resolve().parents[2]
REPO = CN.parents[1]
OUT = Path(__file__).resolve().parent
def pin(path):
    raw=path.read_bytes()
    return {"path":str(path.resolve()),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
results=[]
ours=CN/"records/helm_failure_research_20260922/RESEARCH_OUTPUT_MANIFEST.json"
m=json.loads(ours.read_text(encoding="utf-8"))
for row in m["outputs"]:
    p=REPO/row["path"]
    got=pin(p) if p.is_file() else {"path":str(p),"missing":True}
    results.append({"bundle":"codex","expected":row,"observed":got,"matches":got.get("sha256")==row["sha256"] and got.get("bytes")==row["bytes"]})
peer=CN/"records/helm_why_review_20260922/EVIDENCE_MANIFEST.json"
m=json.loads(peer.read_text(encoding="utf-8"))
for row in m["files"]:
    p=peer.parent/row["committed_as"] if row["committed_as"] else Path(m["archive"])/row["scratch_path"]
    got=pin(p) if p.is_file() else {"path":str(p),"missing":True}
    results.append({"bundle":"claude","location":"checkout" if row["committed_as"] else "archive_only",
                    "expected":row,"observed":got,"matches":got.get("sha256")==row["sha256"] and got.get("bytes")==row["bytes"]})
report={"schema":"helm.integrated-evidence-verification/1","source_commits":{"codex":"a6e6f95bcae348775b910438109c9ed3842a5c19","claude":"26f1b46515c960a7aed6023f370df95d591ca36a"},
        "manifests":[pin(ours),pin(peer)],"records":results,
        "matched":sum(r["matches"] for r in results),"total":len(results),
        "limitations":"Verifies bytes against recorded manifests, not independent reproduction of all research experiments."}
(OUT/"INVESTIGATION_EVIDENCE_VERIFICATION.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print({"matched":report["matched"],"total":report["total"],"failures":[r["observed"] for r in results if not r["matches"]]})
