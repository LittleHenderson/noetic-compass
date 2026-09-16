"""Reconcile current summaries only after the final runtime and suite pass."""
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HOME=ROOT.parents[3]
HERE=Path(__file__).parent
EXPECTED_LEDGER='3b5e8a3fbc9ff2aa725aab66fa4f1dbadd0cfd689ee149f82346a76b897625b1'
EXPECTED_VISION='7d0e51b3a291d0015655893ab30c7678f22edf7b10d3e1915197f93c2dfce647'

def read(path):return json.loads(path.read_bytes())
def checksum(path):return sha256(path.read_bytes()).hexdigest()
def require(condition,message):
    if not condition:raise AssertionError(message)

def replace_once(text,old,new):
    require(text.count(old)==1,'Expected unique text missing: '+old[:95])
    return text.replace(old,new,1)

def table_rows(text,updates,column=5):
    lines=text.splitlines();seen=set()
    for index,line in enumerate(lines):
        for key,value in updates.items():
            if line.startswith('| '+key+' |'):
                require(key not in seen,'Duplicate table row '+key)
                parts=line.split('|');require(len(parts)>column+1,'Malformed table row')
                parts[column]=' '+value+' ';lines[index]='|'.join(parts);seen.add(key)
    require(seen==set(updates),'Missing requested table rows')
    return '\n'.join(lines)+'\n'

def ledger(text):
    text=replace_once(text,'- bounded declared RPM child resolution;\n- exact semantic-key episodic recall inside one process;',
        '- bounded native equation-dependency planning and nested missing-procedure acquisition;\n'
        '- scoped source correction/retraction, installed procedures and checked formal-result\n'
        '  memory across externally anchored episodes, with fresh-process journal reconstruction;')
    text=replace_once(text,'## Current verification state','## Historical v0.1 verification snapshot')
    text=replace_once(text,'At this source snapshot:\n\n- Python: `181 passed`, `403 subtests passed`.',
        'These are retained historical results, not a fresh deployment check. Current native\n'
        'runtime, scoped-view and regression evidence appears in the dated checkpoints below.\n\n'
        '- Python: `181 passed`, `403 subtests passed`.')
    updates={
      '2':'Preserve the frozen v0.1 kernel. Accepted native0.3–0.6 add bounded nested planning, explicit advance APIs and exact fresh-process journal reconstruction/resumption under externally trusted genesis and source chronology. General planning, authenticated durable custody, broader halt coverage and production crash semantics remain open.',
      '6':'Branch isolation exists. Accepted0.5 deterministically constructs and checks420 candidate call structures in a bounded two-call arithmetic grammar;0.6 proposes and independently checks a missing formal scalar. General native ^8 interpretation/hypothesis/plan generation, broader proof/analogy/causal candidates and provenance/diversity controls remain open.',
      '9':'Runtime0.3 provides bounded equation dependencies;0.5 suspends compound construction for a missing primitive and returns exact callers with conserved work. Version0.6 adds a saved-parent RPM child for missing formal results, checked admission and exact resumption; all141 retained0.6 prefixes reconstruct and continue in one fresh child process. General prerequisite discovery, research/tool/dialogue subgoals and long-horizon planning remain open.',
      '10':'Runtime0.4/0.5 retain scoped source corrections/retractions and installed procedures across anchored episodes. Accepted0.6 adds scoped proof-backed formal-result records, logical creation/use history, later-task reuse and transitive source/definition freshness. These are conditional mathematical consequences, not independently verified world facts. Full CAS-GEM/CMB-R1, metadata/forgetting, similarity retrieval, hot/warm/cold storage and authenticated custody remain open.',
      '14':'Runtime0.3–0.6 journals bind problems, state, source profiles, exact proposals, saved frames, work and retained records. Another process reconstructs and resumes each retained cut under externally trusted genesis, ingress chronology and complete journal digest. Version0.6 additionally binds proof-memory, transitive source/definition support and the commitment-before-storage stage. This is integrity under explicit custody, not principal authentication. Full conversational continuity, common inputs_read/biases_read contracts, authenticated durable custody and live CAS-Ohm observation remain open.',
      '18':'The isolated language and CCB-T1 laboratories retain local qualification receipts with zero CNCM writes; they still lack kernel-authorized grammar/general-strategy promotion. Separately, native0.2–0.6 execute bounded governed procedure qualification/install/return/reuse/rollback, source correction and checked-result memory under versioned intents. Public finite panels do not establish the complete R1 learning contract or neural learning. Trace-driven weakness detection, live teacher/CAS-SDG adapters, authenticated fixture custody, broad semantic destinations, descendant sandboxes, cross-capability qualification and the complete R0–R3 authority rings remain open.',
      '19':'The frozen exact-rational IR/parser/proof-step checker and standalone solver remain implemented. Native0.2–0.5 check admitted calls and original expressions before authorized commitment. Accepted0.6 adds reusable conditional formal-result admission and rechecking through check_math_step/verify_math_receipt, with independent original typed-input binding. Solver regeneration is not treated as an independent proof check. General math workspaces, broader theories and approximation metadata remain open.',
      '24':'The browser playground and isolated apprenticeship benches remain bounded surfaces. Accepted read-only compound/cube workbenches expose retained execution and authored structure. The separate scoped-navigation extension enters declared calls, bindings, primitive instructions and evidence, returning through breadcrumbs with fixed execution identity. It is not an executing planner, Foundry or learning result. The component library, typed-port canvas/DRC, full P/C/E/O and motherboard views, live Mind control, learning/evolution panes and general board-to-runtime integration remain open.',
      '31':'Protected logic/math/proof checks and0.4/0.5 source-update, exact-recall and substitution receipts execute. Accepted0.6 adds exact proof/definition/original-input bindings and bounded transitive-support checks. A valid arithmetic derivation never upgrades a source assertion into world truth. Full common request/result federation, broader symbolic/code/theorem/citation/tool checks and independently governed checker lifecycle remain open.',
    }
    text=table_rows(text,updates)
    text=table_rows(text,{
      '3 — memory, RPM, and verifiers':'Accepted native0.3–0.6 execute bounded nested acquisition, source correction, checked calls, proof-backed result reuse and externally anchored fresh-process recovery. Multi-class CAS-GEM/CMB-R1, general research/tool prerequisites, common verifier federation and protected held-out learning remain open. The bounded engineering sequence does not complete this phase.',
      '5 — governed learning':'The isolated language/CCB-T1 labs still lack kernel-authorized grammar or general-strategy promotion. Separately, native0.2–0.6 provide governed finite procedure acquisition/qualification/install/return/retention/rollback, source memory and checked-result reuse across reconstructed episodes. These public bounded mechanisms do not establish full R1 learning, neural improvement, live teacher/CAS-SDG integration, authenticated held-out custody or all native semantic destinations.'},column=3)
    return text

def vision(text):
    old='The active owner goal raises the total AWS cap to $400 and makes the full vision override any conflicting part of the earlier 12-hour campaign. Work after that campaign remains inside the same cap. The exact active-goal response is retained in `records/budget/OWNER_APPROVAL_SOURCE.json`.'
    new='Historical campaign authorization snapshot: the original goal set a $400 cap and gave the full vision precedence over the earlier 12-hour campaign. `records/budget/OWNER_APPROVAL_SOURCE.json` retains that original authority. Later authorization and budget evidence are in `records/budget/OWNER_BUDGET_AMENDMENT_001.json`, `records/budget/campaign_ledger.json` and the ordered-encoder checkpoint records. These are historical/local records, not a fresh provider-capacity or billing check; reservations are not invoices.'
    text=replace_once(text,old,new)
    return table_rows(text,{
      'V04':'Partial: accepted native dependency-order planning and finite compound construction/acquisition support bounded nested execution and exact parent returns. New composition/learning tests must withhold entire structures and deeper real operation paths. General recursion and full CAS semantics remain open.',
      'V05':'Partial: native0.4/0.5 retain scoped source correction/retraction and installed procedures across anchored episodes. Accepted0.6 adds scoped proof-backed result memory, logical use history and transitive freshness; current source bindings alter later tasks without resupplied scalars. Formal conclusions remain conditional on admitted sources. General retrieval, full memory classes/metadata and CMB-R1 remain open.',
      'V06':'Partial: native0.2–0.5 acquire, qualify, install, retain and roll back bounded procedures during real suspended calls. Accepted0.6 adds checked result retention and later-task reuse with new generation disabled. This is symbolic reuse, not measured neural learning. General skill acquisition and protected held-out retention/transfer remain open.',
      'V08':'Partial: native0.3–0.5 acquire bounded equation/procedure prerequisites and resume exact callers with conserved work and explicit failures. Accepted0.6 adds missing-formal-result acquisition and checked memory admission;141 saved prefixes reconstruct and continue in one fresh child process. General diagnosis, native Foundation semantics and broad self-model remain open.',
      'V10':'Partial: native0.3–0.6 journals restore bounded dependencies, acquisition frames, source/definition lineage, proof-memory, procedure heads and conserved budgets under external genesis/ingress/journal anchors. General long-lived project/tool execution, authenticated durable custody and cross-device continuity remain open.',
      'V13':'Partial: accepted compound/cube evidence viewers and a separate scoped-navigation extension expose retained records and declared nested interiors while execution identity stays fixed. Broader integrated goals/memory/flow, editing, simulation, learning and rollback controls remain open. Inspection is not recursive reasoning or learning.',
      'V16':'Partial: bounded native procedure acquisition/qualification, exact saved-caller resumption and retained-neighbor checks exist. Functional cognitive addresses, neural scoped teaching, cross-capability retention and measured transferred learning remain open.'},column=3)

def main():
    derived=read(HERE/'acceptance_001/receipt.json')
    suite=read(HERE/'final_suite_001/receipt.json')
    scoped=read(ROOT/'records/rpa_scoped_001/acceptance_001/receipt.json')
    browser=read(ROOT/'records/rpa_scoped_001/browser_acceptance_002/receipt.json')
    delivery=read(ROOT/'records/rpa_scoped_001/delivery_001.json')
    require(derived['status']=='PASS' and derived['exact_cuts']==141,'Final derived acceptance is not complete')
    require(suite['status']=='PASS' and suite['inputs_unchanged'],'Full regression has not passed unchanged')
    require(browser['status']=='PASS' and delivery['prior_deliveries_unchanged'],'Scoped browser/delivery incomplete')
    targets=[(ROOT/'docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md','inner_cncm',EXPECTED_LEDGER,ledger),
             (HOME/'docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md','outer_cncm',EXPECTED_LEDGER,ledger),
             (ROOT/'research/CAS_META_2_COMPOSITION/VISION_REQUIREMENTS.md','vision',EXPECTED_VISION,vision)]
    for path,_,expected,_ in targets:require(checksum(path)==expected,'Ledger changed before reconciliation: '+str(path))
    out=HERE/'ledger_reconciliation_002';out.mkdir(exist_ok=False)
    latest=('\n## 2026-09-16 Checked result memory and declared scoped navigation\n\n'
      'Accepted native0.6 now acquires a missing formal result through a saved-parent\n'
      'child, independently checks and stores it, resumes the exact task, and reuses\n'
      'checked results in later arithmetic. Corrections invalidate stale and transitive\n'
      'support; new generation/acquisition can be disabled independently. Ten actual\n'
      'episode outcomes and all141 saved cuts passed the source-bound final recipe.\n'
      'Every cut reconstructs and continues in one fresh child process, not a separate\n'
      'OS process per cut. The141 checks include commitment-before-storage recovery.\n\n'
      'The separate versioned scoped viewer enters declared procedure calls, input\n'
      'bindings, primitive instructions and retained evidence, with breadcrumbs and\n'
      'unchanged execution-state identity. Ten accepted compound0.5 documents cover\n'
      '65 scopes; final browser checks cover130 scope visits and1,244 inspections on\n'
      'desktop/mobile. Exact profile40 and overlap-certificate observations remain\n'
      'empty in those ten inputs and the four separately checked cube documents.\n'
      'The38-file outer output/rpa_scoped_001 delivery preserves both earlier packages.\n\n'
      f'Full symbolic regression: {suite["counts"]["tests"]} JUnit-counted tests/subtests, zero failures,\n'
      'errors or skips, with all declared suite inputs unchanged. The focused checks\n'
      'passed107 memory tests and37 scoped-navigation tests. Failed development and\n'
      'browser probes remain retained. Records: derived_memory_001/STATUS.md and\n'
      'rpa_scoped_001/STATUS.md, including exact runtime/browser/suite receipts.\n\n'
      'All126 frozen prior source files, four earlier runtime profiles and367 prior\n'
      'recurrence/handoff evidence files remain unchanged. No neural/provider execution\n'
      'or AWS launch was performed for this checkpoint. This is bounded symbolic\n'
      'retention/reuse and inspection, not improved neural learning or full CNCM.\n\n'
      'The next learning gate is docs/CNCM_NEXT_LEARNING_EXPERIMENT_GATE.md: add a\n'
      'source-bound learner-compatible record adapter, pin the opt-in ordered encoder\n'
      'equally in controls, close inference answer leakage and freeze a genuinely\n'
      'separate topology/family panel before actual matched multi-seed training.\n'
      'The earlier recurrence result remains NOT_MET,0/3 positive; the later encoder\n'
      'diagnostic was zero-update and establishes no trained-transfer gain. The full\n'
      'V01–V18,31-system and integrated20-step charter remains open.\n')
    results=[]
    for path,label,expected,transform in targets:
        raw=path.read_bytes();(out/(label+'_before.md.txt')).write_bytes(raw)
        text=raw.decode('utf-8').replace('\r\n','\n')
        changed=transform(text)
        # Preserve the dated starting checkpoint while making its temporal role explicit.
        changed=replace_once(changed,'## 2026-09-16 derived-result memory integration started',
            '## 2026-09-16 derived-result memory integration started (historical checkpoint)')
        changed=changed.rstrip()+'\n'+latest
        newline='\r\n' if b'\r\n' in raw else '\n'
        path.write_bytes(changed.replace('\n',newline).encode('utf-8'))
        results.append({'path':str(path),'before_sha256':expected,'after_sha256':checksum(path)})
    require(targets[0][0].read_bytes()==targets[1][0].read_bytes(),'Canonical CNCM ledgers diverged')
    with (out/'receipt.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump({'status':'RECONCILED_CURRENT_SUMMARIES_HISTORICAL_EVIDENCE_PRESERVED','files':results,
            'derived_acceptance_sha256':checksum(HERE/'acceptance_001/receipt.json'),
            'full_suite_sha256':checksum(HERE/'final_suite_001/receipt.json')},stream,sort_keys=True,separators=(',',':'));stream.write('\n')
    print(json.dumps(results))

if __name__=='__main__':main()
