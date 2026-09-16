"""Reconcile current requirement summaries with accepted evidence; no new pass claim."""
from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[2]
OUTER=ROOT.parents[3]
TRACK=Path(__file__).parent
UPDATES={
"docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md": (
"89ab030f39d7e10e98126b5e1994ee2d1a3aa2967ac176894c174df861833ca2", {
"| 9 |": "| 9 | RPM recursive planning and clarification executive | `PARTIAL — NATIVE NESTED ACQUISITION` | 8107-8158, 10268-10290, 11435-11469 | Runtime0.3 provides bounded equation dependencies;0.5 suspends compound construction for a missing primitive and returns both exact callers with conserved work. All75 accepted0.5 journal cuts recover in another process (records/compound_procedure_001). General prerequisite discovery, research/tool/dialogue subgoals, long-horizon planning and independently checked derived-memory acquisition remain open;0.6 is in development. |",
"| 10 |": "| 10 | CMB multi-class memory and lacunarity system | `PARTIAL — SOURCE CORRECTION + PROCEDURE RETENTION` | 7944-7988, 9002-9023, 10245-10264 | Runtime0.4/0.5 retain scoped source assertions, supersession/retraction history and installed procedures across anchored episodes. Current source bindings alter later derivations without resupplying their scalars. Source labels remain USER_ATTESTED/TEST_FIXTURE. Checked derived-result memory0.6 is in development, not accepted. CAS-GEM/CMB-R1, full metadata/forgetting, reconstruction/similarity retrieval, hot/warm/cold storage and authenticated custody remain open. |",
"| 14 |": "| 14 | Trace, evidence, provenance, and deterministic replay fabric | `IMPLEMENTED-BOUNDED + CAS-OHM SIDECAR CONTRACT` | 7741-7742, 7831-7834, 9235-9253, 9483-9505, 11576-11627 | Runtime0.3-0.5 journals bind problem, state, source profile, exact proposals, frames, work and retained records. Another process reconstructs every retained0.5 cut under caller-supplied genesis, ingress chronology and complete journal digest. This is integrity under explicit custody, not principal authentication. Full conversational continuity, common inputs_read/biases_read contracts, authenticated durable custody and live CAS-Ohm observation remain open. |",
"| 19 |": "| 19 | CAS-Math IR and protected exact-verification kernel | `IMPLEMENTED-BOUNDED` | 6904-6925, 7010-7191, 7584-7646, 12990-13025 | The frozen exact-rational IR/parser/proof-step checker and standalone solver remain implemented. Native0.2-0.5 independently check admitted procedure calls and original expressions before coordinator-authorized commitment. Reusable proof-backed formal results, general math workspaces/proof packets, broader theories and approximation metadata remain open;0.6 is developing result-memory admission under the existing protected step checker. |",
"| 31 |": "| 31 | Trusted verifier federation | `PARTIAL — BOUNDED DOMAIN RECEIPTS` | 12126-12137, 12990-13025 | Protected logic/math/proof checks and0.4/0.5 source-update, exact-recall and input-substitution receipts execute. A valid arithmetic relation never upgrades a source assertion into world truth. Derived-memory checking0.6 is in development. Full common request/result federation, broader symbolic/code/theorem/citation/tool checks and independently governed checker lifecycle remain open. |"
}),
"research/CAS_META_2_COMPOSITION/VISION_REQUIREMENTS.md": (
"55c010c202b879677c3aaa31d3de7f7a8a0c726416b338ef80213bb2e16724ef", {
"| V05 |": "| V05 | Durable working, episodic, semantic, procedural memory with provenance, time, structure and truth labels; semantic/structural recall and dynamic working sets | Partial: accepted native0.4/0.5 retain scoped source correction/retraction history and installed procedures across externally anchored episodes. Exact current source bindings change later results without resupplying scalars; source attestations remain conditional. Checked derived-result memory0.6 is in development. General retrieval, full memory classes/metadata and CMB-R1 remain open. |",
"| V06 |": "| V06 | Lifelong instruction and skill learning; context versus durable memory versus neural skill; scoped changes, retention, versioning and rollback | Partial: native0.2-0.5 acquire, independently qualify, install, retain and roll back bounded authored/constructed procedures during real suspended calls. Public finite engineering panels do not establish general teaching or neural learning. Derived-result retention0.6 is in development; general skill acquisition, protected held-out retention and neural identity transitions remain open. |",
"| V08 |": "| V08 | Practical self-model and RPM Desire/Wisdom/Power diagnosis; acquire missing prerequisites, verify, resume exact caller and budget | Partial:0.3-0.5 detect missing equation/procedure prerequisites, acquire checked bounded procedures and resume exact saved callers with conserved work and explicit failures. Runtime0.5 has75 fresh-process cut recoveries. Checked derived-knowledge acquisition0.6 is in development; general diagnosis, native Foundation semantics and broad self-model remain open. |",
"| V10 |": "| V10 | Persistent goals, dependencies, unfinished calls and authorized project/tool work with evidence-backed completion | Partial: anchored native journals restore nested dependencies, acquisition frames, current source lineage, procedure heads and conserved budgets at every retained0.5 cut. Derived-memory continuation0.6 is in development. General long-lived project/tool execution and cross-device authorized continuity remain open. |"
})}
note="""

## 2026-09-16 derived-result memory integration started

Current-state review confirmed that accepted0.5 retains source statements and
procedures but cannot yet resolve a typed checked derived-result reference.
The top-level summaries above now reflect already accepted0.3-0.5 evidence;
their earlier shallow/same-process descriptions were historical, not current.

The new versioned0.6 work connects protected mathematical proof checking to
native result memory, missing-prerequisite frames and later compound execution.
Implementation and acceptance are pending. The six-case frozen proof-gate probe
passed with both solver entry points disabled; it is not an integrated0.6 pass.
See spec/CNCM_DERIVED_MEMORY_v0.6.md and records/derived_memory_001/STATUS.md.

The preservation baseline binds126 accepted source files, all four prior runtime
profiles and367 recurrence/handoff evidence files. The original helper field-name
failure remains retained. No neural/provider run, AWS launch or new learning
claim was made. The complete V01-V18,31-system,integrated20-step charter is open.
"""
def main():
    planned=[]
    for relative,(expected,replacements) in UPDATES.items():
        targets=[ROOT/relative]
        if relative.startswith("docs/"):targets.append(OUTER/relative)
        for path in targets:
            raw=path.read_bytes()
            assert sha256(raw).hexdigest()==expected,str(path)
            newline="\r\n" if b"\r\n" in raw else "\n"
            lines=raw.decode("utf-8").splitlines()
            for prefix,replacement in replacements.items():
                hits=[i for i,line in enumerate(lines) if line.startswith(prefix)]
                assert len(hits)==1,(prefix,len(hits))
                lines[hits[0]]=replacement
            out=(newline.join(lines)+newline+note.strip("\n").replace("\n",newline)+newline).encode("utf-8")
            planned.append((path,raw,out))
    evidence=TRACK/"ledger_reconciliation_001"
    evidence.mkdir(exist_ok=False)
    rows=[]
    for index,(path,raw,out) in enumerate(planned):
        (evidence/f"before_{index}.txt").write_bytes(raw)
        path.write_bytes(out)
        assert path.read_bytes()==out
        rows.append({"path":str(path),"before_sha256":sha256(raw).hexdigest(),
                     "after_sha256":sha256(out).hexdigest()})
    (evidence/"receipt.json").write_text(json.dumps({"status":"UPDATED_SUMMARIES_NO_NEW_ACCEPTANCE","files":rows},indent=2)+"\n",encoding="utf-8")
    print(json.dumps(rows))
if __name__=="__main__":main()

