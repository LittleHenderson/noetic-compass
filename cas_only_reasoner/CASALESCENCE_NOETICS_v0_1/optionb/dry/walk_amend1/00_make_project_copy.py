"""[MADE-UP DATA WALK, NOT A RESULT] Make the scratch copy of the study folder for the walk of amendments A1 to A12.

It copies program files and rule texts, byte for byte, from the real study folder into
optionb/dry/walk_amend1/<name>/. It copies no label file, no passage file and no design file: those
are made up by 01_make_fixture.py. It opens none of the copied files; it only hashes them.
It changes nothing outside optionb/dry/walk_amend1/.

Usage: python -B 00_make_project_copy.py <name>     name = project (the walk) or project_dev (the builder test)
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REAL = HERE.parent.parent.parent
assert (HERE.name, HERE.parent.name, HERE.parent.parent.name) == ('walk_amend1', 'dry', 'optionb')

TOOLS = ['tools/ob_assemble.py', 'tools/ob_check_questions.py', 'tools/ob_check_support.py', 'tools/ob_eligibility.py',
         'tools/ob_role_notes.py', 'tools/ob_screen_notes.py', 'tools/ob_seal.py', 'tools/ob_select.py', 'tools/ob_solve_blind.py',
         'tools/ob_write_ordinary_notes.py', 'tools/ob_write_questions.py']
RULE_TEXTS = ['tools/verdict.py', 'tools/write_verdict_passages.py', 'tools/scorer_v0_1.py',
              '08_OPTION_B_PLAN_v1_0.md', '02_LABELING_GUIDE_v1_2.md', '03_SCORER_RULES_v0_1.md', 'scorer_examples_v0_1.json',
              'design_v2/optionB_reviews.json', 'OWNER_DIRECTION_POINTING_AND_OPTION_B_20261005.json', 'DIRECTIVE_R2.md',
              'optionb/FILE_FORMATS.md', 'optionb/PLAN_CONSTANTS.json',
              'optionb/job/runner_b1.py', 'optionb/job/scorer_v0_1_1.py', 'optionb/job/gate_b1.py', 'optionb/job/analysis_b1.py',
              'optionb/job/scorer_examples_v0_1_1.json']
DEV_ONLY = ['optionb/dry/build_dev_package.py', 'optionb/controller_b1_draft/worker_v02.py',
            'optionb/controller_b1_draft/build_source_zip_b1.py', 'optionb/controller_b1_draft/build_contract_b1.py']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    name = sys.argv[1]
    if name not in ('project', 'project_dev'):
        raise SystemExit('name must be project or project_dev')
    target = HERE / name
    if target.exists():
        raise SystemExit('%s exists already' % target)
    names = TOOLS + RULE_TEXTS + (DEV_ONLY if name == 'project_dev' else [])
    rows = []
    for relative in names:
        source, copy = REAL / relative, target / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, copy)
        a, b = sha(source), sha(copy)
        if a != b:
            raise SystemExit('copy differs: %s' % relative)
        rows.append({'path': relative, 'bytes': source.stat().st_size, 'sha256': a, 'copy_is_byte_identical': True})
    out = {'note': 'MADE-UP DATA WALK, NOT A RESULT. Byte copies of program files and rule texts only.', 'copy': name, 'files': rows}
    with open(HERE / ('COPIED_FILES_%s.json' % name), 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(out, indent=1) + '\n')
    print('copied %d files into %s; every copy has the sha256 of its source' % (len(rows), target))


if __name__ == '__main__':
    main()
