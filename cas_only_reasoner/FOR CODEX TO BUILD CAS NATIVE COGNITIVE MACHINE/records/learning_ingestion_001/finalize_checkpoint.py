"""Finalize checkpoint summaries only after source-bound pure acceptance."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT.parents[3]
BASE = Path(__file__).parent
def read(path):return json.loads(path.read_bytes())
def checksum(path):return sha256(path.read_bytes()).hexdigest()
def need(condition,reason):
    if not condition:raise RuntimeError(reason)
def write(path,value):
    with path.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(value,stream,sort_keys=True,separators=(",",":"));stream.write("\n")

def main():
    receipt=read(BASE/"acceptance_001/receipt.json")
    focused=read(BASE/"focused_002/receipt.json")
    panel=read(ROOT/"research/CAS_META_2_COMPOSITION/records/learning_panel_001/receipt.json")
    need(receipt["status"]=="PURE_INGESTION_AND_CONTROL_PASS_CUDA_SMOKE_NOT_RUN"
         and receipt["combinations"]==306 and receipt["inputs_unchanged"],"PURE_ACCEPTANCE_INCOMPLETE")
    need(focused["status"]=="PASS" and focused["counts"]=={
        "tests":308,"failures":0,"errors":0,"skipped":0}
        and focused["inputs_unchanged"],"FOCUSED_REGRESSION_INCOMPLETE")
    need(panel["status"]=="AUDIT_ONLY_EXISTING36_SUPPLIED_ORDERED_RUN_NOT_READY"
         and panel["passing_audit_assertions"]==106,"PANEL_AUDIT_INCOMPLETE")
    profiles=read(BASE/"profile_preservation.json")
    need(profiles["status"]=="FIVE_FROZEN_PROFILES_UNCHANGED","PROFILE_PRESERVATION_INCOMPLETE")
    expected_ledger="7e161faad4135b2ec8851b17347a0d3e7dbc81ffaa0f792d2d2a94f03369cc39"
    expected_vision="1d46197498058cb996cbf6e685b27cfcb7bd46d9bdd9f5a4acf0de8504c487c2"
    targets=[(ROOT/"docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md","inner",expected_ledger),
             (HOME/"docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md","outer",expected_ledger),
             (ROOT/"research/CAS_META_2_COMPOSITION/VISION_REQUIREMENTS.md","vision",expected_vision)]
    for path,_,expected in targets:need(checksum(path)==expected,"LEDGER_CHANGED:"+str(path))
    out=BASE/"ledger_update_001";out.mkdir(exist_ok=False)
    addition="""
## 2026-09-16 Source-bound learner connection and existing-panel audit

The new versioned ingestion extension renders declared cube containment as the
learner's actual node/rel syntax, preserves the question and ordered choices,
and separates source-checked training targets from a closed public prediction
packet. Public identity binds content, tokenizer/ordered profile and run-initial
model context. Training cache bytes AND cached target indices are checked before
and after updates; public predictions are retained before private scoring.

Pure source-bound acceptance covered all 306 existing fixture combinations;
308 focused compatibility tests passed without failures, errors or skips. The
test receipt binds the exact current source and test inputs. The acceptance
recipe also checks foreign-import refusal, target-independent public input and
refusal of altered private supervision. Recording-stub calls are explicitly
non-neural. All 601 preserved sources, six earlier evidence receipts and five
runtime profiles remain unchanged. Failed development probes remain retained.

The implemented CUDA smoke entrypoint constructs the ordered encoder explicitly,
fits only training text, injects the newly admitted records into the existing
trainer, checks actual numeric caches and permitted parameter changes, retains
model/optimizer/encoder checkpoints and seals public-only predictions. These
numeric paths have SOURCE REVIEW ONLY and were not executed in this checkpoint.
Provider/source/wheel/budget bindings and real smoke/reload acceptance remain open.

A separate retained-history audit reproduces the existing canonical six-development
and thirty-final candidate families (18 and 90 application tasks). All final tasks
fit the 1024-token ordered framing envelope under three separately identified
tokenizers. The audit's 106 assertions include repeated source-hash checks, not
106 independent learning tests. It preserves one old local-run source-custody
gap and identifies two perspective-derived final variants that overlap development
topology. The canonical 6/30 allocation stays disjoint; no new panel is selected.

Use a fresh matched initializer and freeze the new run's exact training-only
tokenizer, teaching inputs, curriculum and checkpoint-selection rules before
final scoring. Old complementary execution bindings and a legacy checkpoint
cannot silently serve the new ordered encoder. Historical authoring/checking
differs from learner exposure; global all-history novelty is not asserted.

Evidence: records/learning_ingestion_001/STATUS.md and
research/CAS_META_2_COMPOSITION/records/learning_panel_001/REPORT.md.
No neural/tensor/provider execution, AWS launch, spending or learning gain is
reported here. The earlier three-seed recurrence result remains NOT_MET, 0/3
positive. All V01-V18, 31-system and integrated 20-step charter requirements remain
subject to their wider open gates; this checkpoint does not complete the goal.
"""
    changed=[]
    for path,label,expected in targets:
        raw=path.read_bytes();(out/(label+"_before.md.txt")).write_bytes(raw)
        newline="\r\n" if b"\r\n" in raw else "\n"
        value=raw.decode().replace("\r\n","\n").rstrip()+"\n"+addition
        path.write_bytes(value.replace("\n",newline).encode())
        changed.append({"path":str(path),"before_sha256":expected,"after_sha256":checksum(path)})
    need(targets[0][0].read_bytes()==targets[1][0].read_bytes(),"CANONICAL_LEDGERS_DIFFER")
    old_status=BASE/"STATUS.md"
    (out/"status_before.md.txt").write_bytes(old_status.read_bytes())
    text=f"""# Learning ingestion checkpoint

Status: PURE_INGESTION_AND_CONTROL_ACCEPTED / CUDA_SMOKE_NOT_RUN.

The source-bound final recipe passed all 306 exposed cube-fixture combinations,
representing {receipt['unique_public_inputs']} unique public inputs. Source rendering, exact
ordered choices, actual pure tokenizer/framing, teacher-independent prediction
and source-grounded refusal of altered private targets were checked. A recording
stub performed three closed prediction calls; it is not a model or learner.

Final focused regression: 308 passed, zero failures/errors/skips, all declared
inputs unchanged, and zero prohibited imports. Tests cover the new adapter and
cycle, independent adversarial cases, and inherited cube/tokenizer/ordered-encoder
compatibility. This is not a rerun of the prior full 1581-test regression.

Exact receipt identities:

- acceptance_001/receipt.json: {checksum(BASE/'acceptance_001/receipt.json')}
- focused_002/receipt.json: {checksum(BASE/'focused_002/receipt.json')}
- source_baseline.json: {checksum(BASE/'source_baseline.json')}
- profile_preservation.json: {checksum(BASE/'profile_preservation.json')}

All 601 preserved accepted sources, six prior evidence receipts and five runtime
profiles remain unchanged. Failed label, temporary-directory and test-helper
probes and superseded receipt-helper source are retained.

The numeric worker entrypoints are implemented and source-reviewed only.
No local tensor/model run, provider call, AWS launch or new spending occurred.
The actual CUDA teaching smoke, numerical checkpoint reload and fully bound
matched learning experiment remain open. No learning gain is established.

The separate panel audit binds 15 artifacts and 41 source/input files; its 106
assertions include repeated hash checks. It reproduces the existing 6 dev / 30 final
candidate allocation and token envelope while disclosing historical custody and
perspective overlap limits. It selects no new panel and authorizes no new run.

See docs/CNCM_LEARNING_INGESTION_v0.1.md,
docs/CNCM_NEXT_LEARNING_EXPERIMENT_GATE.md and
research/CAS_META_2_COMPOSITION/records/learning_panel_001/REPORT.md.
The full goal stays active; the earlier recurrence result remains NOT_MET.
"""
    old_status.write_text(text,encoding="utf-8",newline="\n")
    write(out/"receipt.json",{"status":"CURRENT_CHECKPOINT_RECONCILED_PRIOR_EVIDENCE_PRESERVED",
          "ledgers":changed,"status_sha256":checksum(old_status),
          "acceptance_receipt_sha256":checksum(BASE/"acceptance_001/receipt.json"),
          "focused_receipt_sha256":checksum(BASE/"focused_002/receipt.json")})
    print(json.dumps({"status":"RECONCILED","ledgers":changed}))

if __name__=="__main__":main()

