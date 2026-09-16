"""Capture unchanged accepted sources before ordered-ingestion CUDA smoke extension."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "source_baseline.json"
HEAD = "a308f0eea30209ea60012873a5416c2de0adbfa6"
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
 "records/learning_ingestion_001/acceptance_001/receipt.json",
 "records/learning_ingestion_001/focused_002/receipt.json",
 "research/CAS_META_2_COMPOSITION/records/learning_panel_001/receipt.json",
 "records/derived_memory_001/acceptance_001/receipt.json",
 "records/derived_memory_001/final_suite_001/receipt.json",
 "records/rpa_scoped_001/acceptance_001/receipt.json",
 "records/rpa_scoped_001/browser_acceptance_002/receipt.json",
 "research/CAS_META_2_COMPOSITION/records/rdcjt_handoff_20260916/post_fix_verification.json",
 "research/CAS_META_2_COMPOSITION/records/ordered_encoder_001/independent_recount_001/recount.json",
]
value = {"schema_version":"cncm.learning-smoke-preservation/0.1",
         "parent_commit":HEAD, "accepted_sources":rows,
         "prior_evidence":[pin(ROOT / name) for name in evidence],
         "previous_goal_turn":"PROGRESS: implemented learner ingestion; 308 tests, 306 source checks and exact 694-file GitHub readback",
         "scope":"Exposed-material CUDA connection/reload check; no matched learning or complete-machine claim"}
raw=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
with OUT.open("xb") as stream: stream.write(raw)
print(json.dumps({"sources":len(rows),"evidence":len(evidence),"sha256":sha256(raw).hexdigest()}))
