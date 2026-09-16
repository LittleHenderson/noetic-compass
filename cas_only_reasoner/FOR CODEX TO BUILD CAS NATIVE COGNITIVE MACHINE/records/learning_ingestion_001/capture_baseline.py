"""Capture unchanged accepted sources before learning-ingestion extension."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "source_baseline.json"
HEAD = "089223d81b70bbaab63e82e1aea763e7ea41caea"
def pin(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == HEAD
assert not subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT).strip()
tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
prefixes = ("cncm/", "tests/", "tools/", "schemas/", "spec/", "authority/",
            "research/CAS_META_2_COMPOSITION/cas_meta2/",
            "research/CAS_META_2_COMPOSITION/tests/")
names = [name for name in tracked if name and name.startswith(prefixes)
         and Path(name).suffix in (".py", ".json", ".md", ".yaml")]
rows = [pin(ROOT / name) for name in sorted(names)]
evidence = [
 "records/derived_memory_001/acceptance_001/receipt.json",
 "records/derived_memory_001/final_suite_001/receipt.json",
 "records/rpa_scoped_001/acceptance_001/receipt.json",
 "records/rpa_scoped_001/browser_acceptance_002/receipt.json",
 "research/CAS_META_2_COMPOSITION/records/rdcjt_handoff_20260916/post_fix_verification.json",
 "research/CAS_META_2_COMPOSITION/records/ordered_encoder_001/independent_recount_001/recount.json",
]
value = {"schema_version":"cncm.learning-ingestion-preservation/0.1",
         "parent_commit":HEAD, "accepted_sources":rows,
         "prior_evidence":[pin(ROOT / name) for name in evidence],
         "previous_goal_turn":"PROGRESS: completed tested memory/navigation checkpoint and exact GitHub readback",
         "scope":"New learner connection; no complete-machine or neural-learning claim"}
raw=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
with OUT.open("xb") as stream: stream.write(raw)
print(json.dumps({"sources":len(rows),"evidence":len(evidence),"sha256":sha256(raw).hexdigest()}))

