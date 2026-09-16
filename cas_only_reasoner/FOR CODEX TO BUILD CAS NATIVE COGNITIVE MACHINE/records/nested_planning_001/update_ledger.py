"""Append verified nested-planning progress while preserving the full goal."""
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
HOME=Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
RECORD=Path(__file__).parent
tests=RECORD/"final_full_suite_tests.xml"
suite=ET.fromstring(tests.read_bytes()).find("testsuite")
assert suite is not None and int(suite.attrib["tests"])==1316
assert all(int(suite.attrib[key])==0 for key in ("failures","errors","skipped"))
receipt_path=RECORD/"acceptance_002/receipt.json"
receipt=json.loads(receipt_path.read_bytes())
assert receipt["status"]=="BOUNDED_NATIVE_NESTED_EPISODE_PASSED"
assert receipt["source_profile_digest"]=="49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38"
assert receipt["fresh_process_cuts"]==31 and receipt["procedure_installations"]==1
addition="""
## 2026-09-16 native nested dependency discovery and exact continuation

Runtime0.3 now discovers dependency execution order from a bounded typed
equation graph and query, with no supplied resolver, answer or execution plan.
A parent can suspend for a missing equation result; that child can itself
suspend for an absent arithmetic procedure. All calls share the same budget
and governed registry. Separate immutable call workspaces preserve the saved
parent; only exact checked child execution records may bind downstream inputs.

The retained real episode has a shared prerequisite and an irrelevant
unexecutable equation. It reaches three active frames, installs one checked
atomic procedure, executes four calls once each, and concludes21/2 through the
ordinary commitment gates. A separate process reconstructs all31 journal cuts
and resumes each to the identical full result. A later graph with new inputs
returns12 with new-call selection/qualification disabled. Rollback removes
dispatch while preserving records; the next call correctly refuses.

The final source profile is
49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38.
Evidence: records/nested_planning_001/STATUS.md and acceptance_002/receipt.json
in vision-next. Full homebase verification passed820 tests plus496 subtests;
all14 retained golden fixtures reproduce. The older native0.2 source profile
c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607
remains unchanged. Missing input, cycles, depth, budgets, wrong child returns,
forged references, false checker outputs and128-bit composition boundaries
have explicit negative coverage and retained failure records.

This advances bounded composition/planning portions of V03/V04/V05/V08/V10/
V15 and systems2/7/9/14/19/31; none is declared complete. The equation planner
is deterministic. Its atomic acquisition still selects twelve authored forms
and uses a public engineering panel. It does not learn new program topology,
implement general planning, prove a performance advantage, or supply the
complete Foundation system. Source/genesis/host trust is still explicit.

The next integrated gaps include provenance-bound semantic correction memory
and a common verifier contract, then broader checked program construction and
the remaining language, flow, learning, tool and Foundry systems. The full
V01-V18,31-system and integrated20-step vision remains open. No new paid
model/provider work was used and prior negative experiments remain intact.
"""
paths=[(HOME/"docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md","1474c6e6fc9d688adc9cfebd54593a0a6e7e6ca06b5e7fc5743c84b94771c94e"),
    (ROOT/"docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md","1474c6e6fc9d688adc9cfebd54593a0a6e7e6ca06b5e7fc5743c84b94771c94e"),
    (ROOT/"research/CAS_META_2_COMPOSITION/VISION_REQUIREMENTS.md","ff0e01166c9787a5650b297a9a61c873b853b3af8dc10d81b638ed1c500e09ec")]
before=[path.read_bytes() for path,_ in paths]
assert all(sha256(raw).hexdigest()==expected for raw,(_,expected) in zip(before,paths))
rows=[]
for raw,(path,expected) in zip(before,paths):
    path.write_bytes(raw+addition.encode())
    rows.append({"path":str(path),"before_sha256":expected,
        "after_sha256":sha256(path.read_bytes()).hexdigest(),
        "original_bytes_preserved":path.read_bytes().startswith(raw),"full_goal_complete":False})
record={"ledgers":rows,"final_tests_sha256":sha256(tests.read_bytes()).hexdigest(),
    "acceptance_receipt_sha256":sha256(receipt_path.read_bytes()).hexdigest()}
with (RECORD/"ledger_update.json").open("x",encoding="utf-8",newline="\n") as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(json.dumps(record))
