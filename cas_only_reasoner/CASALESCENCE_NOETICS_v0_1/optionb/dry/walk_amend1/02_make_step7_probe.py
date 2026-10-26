"""[MADE-UP DATA WALK, NOT A RESULT] Made-up files for a dry run of seal step 7 in the scratch project.

Nothing here is a real receipt, a real self-test record or the owner's table. Every text says so.
Usage: python -B 02_make_step7_probe.py [--table]      --table also writes the made-up status table into the scratch project
"""
import hashlib, json, sys, zipfile
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
P = HERE / 'project'
OUT = HERE / 'step7_probe'
OUT.mkdir(exist_ok=True)
C = json.loads((P / 'optionb' / 'PLAN_CONSTANTS.json').read_text(encoding='utf-8'))
MADE_UP = 'MADE-UP FOR THE WALK. NOT A RESULT. NOT THE OWNER.'

def sha(data): return hashlib.sha256(data).hexdigest()
def dump(path, doc):
    with open(path, 'w', encoding='utf-8', newline='\n') as s: s.write(json.dumps(doc, indent=1) + '\n')

selftest = {'schema': 'casalescence/optionb/selftest/v1', 'note': MADE_UP, 'mode': 'precheck', 'status': C['selftest_pass_status'],
            'checks': [{'name': 'package_matches_seal', 'passed': True}], 'prompt_list_sha256': sha(b'made-up prompt list'),
            'padding_plan_sha256': sha(b'made-up padding plan')}
dump(OUT / 'selftest.json', selftest)
raw = (OUT / 'selftest.json').read_bytes()
seals = {'good': (P / 'optionb' / 'SEAL_OPTIONB.jsonl').read_bytes(),
         'devpkg': (HERE / 'project_dev' / 'optionb' / 'dry' / 'dev_package' / 'project' / 'optionb' / 'SEAL_OPTIONB.jsonl').read_bytes()}
for name, data in seals.items():
    with zipfile.ZipFile(OUT / ('source_%s.zip' % name), 'w', compression=zipfile.ZIP_STORED) as z:
        z.writestr(zipfile.ZipInfo('SEAL_OPTIONB.jsonl', date_time=(2026, 10, 5, 0, 0, 0)), data)
def values(zip_name):
    return {'source_zip_sha256': sha((OUT / zip_name).read_bytes()), 'selftest_status': selftest['status'],
            'prompt_list_sha256': selftest['prompt_list_sha256'], 'padding_plan_sha256': selftest['padding_plan_sha256'], 'selftest_json_sha256': sha(raw)}
kind, passed = C['seal']['step_7_receipt_kind'], C['seal']['step_7_receipt_status']
dump(OUT / 'receipt_devtest.json', {'note': MADE_UP, 'precheck_kind': 'DEVELOPMENT_TEST', 'status': passed, 'values_never_for_a_seal_file': values('source_devpkg.zip')})
dump(OUT / 'receipt_sealed_but_devpkg_zip.json', {'note': MADE_UP, 'precheck_kind': kind, 'status': passed, 'seal_step_7_values': values('source_devpkg.zip')})
dump(OUT / 'receipt_sealed_findings.json', {'note': MADE_UP, 'precheck_kind': kind, 'status': 'PRECHECK_COMPLETE_WITH_FINDINGS', 'seal_step_7_values': values('source_good.zip')})
dump(OUT / 'receipt_good.json', {'note': MADE_UP, 'precheck_kind': kind, 'status': passed, 'seal_step_7_values': values('source_good.zip')})
if '--table' in sys.argv:
    rule, tiers = C['spec_sheet_status'], C['tiers']
    keys = ([row['code'] for row in C['outcome_codes_in_checking_order']] + [c + tiers['exploratory_suffix'] for c in tiers['suffix_applies_to']]
            + list(C['stop_codes']) + list(rule['extra_keys']))
    word = 'MADE_UP_WORD_NOT_A_STATUS'
    dump(P / rule['table_file'], {'schema': 'casalescence/optionb/outcome_status_table/v1', 'owner_words_verbatim': MADE_UP, 'received_utc': MADE_UP,
                                 'channel': MADE_UP, 'spec_sheet': {'path': MADE_UP, 'sha256': sha(b'made-up')}, 'legend_words': [word],
                                 'table': {key: word for key in keys}})
    print('made-up status table written:', rule['table_file'], len(keys), 'keys')
print('made-up probe files:', sorted(p.name for p in OUT.iterdir()))
