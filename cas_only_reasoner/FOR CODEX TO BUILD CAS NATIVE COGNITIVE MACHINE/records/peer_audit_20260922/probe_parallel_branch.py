"""Check existing parallel-branch capabilities without changing or merging either branch."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = next(p for p in reversed(HERE.parents) if p.name == 'FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE')
OTHER_ROOT = BASE/'_worktrees/codex-rpa-recorded-run'
OTHER_CN = OTHER_ROOT/'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE'
EXPECTED = 'eb9985566bd11a89f485d627186ef0efa7177f02'


def main():
    actual = subprocess.check_output(['git','rev-parse','HEAD'],cwd=OTHER_ROOT,text=True).strip()
    if actual != EXPECTED:
        raise RuntimeError('Parallel checkout moved; inspect and record a new source identity before running.')
    lab = OTHER_CN/'research/helm_cas_expression_lab'
    sys.path.insert(0, str(lab))
    import cas_ohm_connections as links
    scale = {'id':'peer-audit-declared','drive_unit':'declared_drive','attention_unit':'declared_attention'}
    drive = {'value':'12','scale':scale,'origin':'design','reference':'audit:declared-drive'}
    resistance = {'scale':scale,'origin':'design','reference':'audit:declared-resistance'}
    source = 'board audit_board { node a: ^8^C|A; resistor r1: Resistor<a, R=4.00>; }'
    result = links.pcba_resistor_flow(source, 'r1', drive, resistance)
    assert result['pcba_check']['parse_status'] == result['pcba_check']['structural_status'] == 'PASS'
    assert result['quantity_report']['exact_value'] == {'numerator':'3','denominator':'1'}
    assert result['measurement_status'] == 'NO_MEASUREMENT_PERFORMED'
    output = {'schema':'cas.peer-audit.parallel-branch/1.0','commit':actual,
              'board_source':source,'board_source_sha256':sha256(source.encode()).hexdigest(),
              'compiler':str(links.__file__), 'result':result,
              'boundary':'Uses the existing declared-scale compiler helper, not api/cas_ohm/quantifiers.py.',
              'model_execution':'NOT_RUN','source_changes':'NONE'}
    (HERE/'parallel_branch_result.json').write_text(json.dumps(output,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    print(json.dumps({'commit':actual,'parse':result['pcba_check']['parse_status'],
                      'structure':result['pcba_check']['structural_status'],
                      'compiled_exact_value':result['quantity_report']['exact_value'],
                      'measurement_status':result['measurement_status'],'model_execution':'NOT_RUN'}))


if __name__ == '__main__':
    main()
