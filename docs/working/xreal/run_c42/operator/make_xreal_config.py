"""Write the job config for helm-claude-xreal-20261019-c42 (HELM-R1 X-REAL, the scored host run), exactly per
LAUNCH_BRIEF_XREAL_20261019.md step 4 and the sealed package's kit/STAGE_XREAL.json. Modelled line for line on the
run-proven c40 maker (r1w5kit/make_r1w5_config.py); every difference is listed here.

Sources (each archive pinned by sha256 in sources_manifest.json):
  xreal   HELM_XREAL_20261019_SOURCE_XREAL.zip a9b4c954 (entries = 53 frozen members + PACKAGE_FREEZE.json);
  r1w4    HELM_R1_W4_20261019_SOURCE_R1W4.zip 4bd0d740;
  r1w3b   HELM_R1_W3B_20261019_SOURCE_R1W3B.zip a4f82556;
  r1w3    HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip 152bca2a;
  r1w2    HELM_R1_W2_20261018_SOURCE_R1W2.zip 21ad185d;
  w1      HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip 31f97d67;
  xr      XR_CARRIER_V1.zip built here from the custodian's carrier folder xr_custody/carrier/xr: exactly
          xr/INPUTS_XREAL.json (37312a31) + xr/XREAL_PINS.json (4cb97a82), each re-hashed against the custodian's handoff
          XREAL_SEALED_20261019T235639Z.json (names, bytes, sha256). No key file, no sample record, no manifest. The
          operator never opens, parses or prints an exam file.
  x5spent X5SPENT_CARRIER_V1.zip: x5spent/ENGLISH64_X5.json (1eb17c91) + x5spent/FACES64_X5.json (2c7cac21) from
          r1_wave5/x5_custody/exam/, by path and sha256 only (pins in the package's kit/run_xreal.py SPENT).
No source corpus ships (RUN_LIMITS_XREAL.json sources_on_host: none).
Stage = STAGE_XREAL.json with --expected-freeze-sha256 67b48541... filled in; nothing else changed (layout_note dropped,
as c38-c40 kept only the stage keys).

Usage: python -B make_xreal_config.py <job> <short> <folder> <lease_stem> <owner record file name>
"""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(KIT))
from prev_common import OP, ledger_existing, sha  # noqa: E402

job, short, folder, lease_stem, approval = sys.argv[1:6]
assert (OP / approval).is_file(), 'OWNER_RECORD_REQUIRED'
D19 = Path(r'C:\Users\wakil\Documents\Codex\2026-10-19')
XRD = D19 / 'x_real'
PKG = 'HELM_XREAL_20261019'
ZIP = XRD / 'HELM_XREAL_20261019_SOURCE_XREAL.zip'
ZIP_SHA = 'a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249'
FREEZE_SHA = '67b485415078ca11c5c3d984cd3f82a6a1ab1f111efc9ce2a619d3c136c8006d'
W4_ZIP = D19 / 'r1_wave4' / 'HELM_R1_W4_20261019_SOURCE_R1W4.zip'
W4_SHA = '4bd0d740a70852c8d59091494ad88c69ac472f3a0f207a33fc44789b8e3df14c'
W3B_ZIP = D19 / 'r1_wave3b' / 'HELM_R1_W3B_20261019_SOURCE_R1W3B.zip'
W3B_SHA = 'a4f82556bf0fc26de5635a7c81ec8f5053951d4c64a3906c8e5dd474e3814d26'
W3_ZIP = D19 / 'r1_wave3' / 'HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip'
W3_SHA = '152bca2a3c869212642f96514e7d485413727bf92cf67e9aff1774cefa532362'
W2_ZIP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-18\r1_wave2\HELM_R1_W2_20261018_SOURCE_R1W2.zip')
W2_SHA = '21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5'
W1_ZIP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip')
W1_SHA = '31f97d67122b45860cdff2b03481655fa502ff359f10b70a181904972ddbb3c9'
XR_CARRIER_DIR = XRD / 'xr_custody' / 'carrier' / 'xr'
XR_HANDOFF = XRD / 'xr_custody' / 'XREAL_SEALED_20261019T235639Z.json'
XR_MANIFEST = XRD / 'xr_custody' / 'exam' / 'MANIFEST_XREAL.json'
XR_MANIFEST_SHA = '1e535511a6e802a727a9a49cf6b4a317037f46fadd7b92271aac4376604a541e'
XR_PINS_SHA = '4cb97a82f2fa816b2715eea454f1aec48afdd11bcc0aaf1c380e36bad7304999'
XR_INPUTS_SHA = '37312a31c9024e3f40c88118822218f28af1942a08ab13f2bfb40ed3f289bbe2'
X5EXAM = D19 / 'r1_wave5' / 'x5_custody' / 'exam'
X5SPENT = {'ENGLISH64_X5.json': '1eb17c91e8c9c7a032882d317381f3eedda4c40690bc0ae401e362cf9689f99b',
           'FACES64_X5.json': '2c7cac2150da4d03ed6d07a83fa0b5a019495bc2af8dd7680e7c6be85bcdaefa'}
SHIP_NAMES = ('INPUTS_XREAL.json', 'XREAL_PINS.json')
FIXED = (2026, 10, 19, 0, 0, 0)

assert sha(ZIP) == ZIP_SHA and sha(W4_ZIP) == W4_SHA and sha(W3B_ZIP) == W3B_SHA and sha(W3_ZIP) == W3_SHA
assert sha(W2_ZIP) == W2_SHA and sha(W1_ZIP) == W1_SHA
with zipfile.ZipFile(ZIP) as z:
    names = [n for n in z.namelist() if not n.endswith('/')]
    freeze = json.loads(z.read(PKG + '/PACKAGE_FREEZE.json'))
    assert hashlib.sha256(z.read(PKG + '/PACKAGE_FREEZE.json')).hexdigest() == FREEZE_SHA
    assert len(names) == len(freeze['members']) + 1 == 54
    for m, pin in freeze['members'].items():
        raw = z.read(PKG + '/' + m)
        assert hashlib.sha256(raw).hexdigest() == pin['sha256'] and len(raw) == pin['bytes'], m
    stage = json.loads(z.read(PKG + '/kit/STAGE_XREAL.json'))
    runner = z.read(PKG + '/kit/run_xreal.py').decode('utf-8')
assert "CARRIER_FILES = ('INPUTS_XREAL.json', 'XREAL_PINS.json')" in runner, 'RUNNER_CARRIER_NAMES'
for n, want in X5SPENT.items():  # the two spent X5 files are pinned in the runner's SPENT table
    assert ("'%s': '%s'" % (n, want)) in runner, ('X5SPENT_PIN_NOT_IN_PACKAGE', n)

# Custody: names, bytes and sha256 come from the custodian's handoff (XREAL_SEALED_*.json); every file is re-hashed.
handoff = json.loads(XR_HANDOFF.read_bytes())
assert handoff['schema'] == 'helm.xreal.sealed-handoff/1' and handoff['receiver_check_all_pass'] is True
assert handoff['package_zip_sha256'] == ZIP_SHA and handoff['pins_sha256'] == XR_PINS_SHA
assert handoff['owner_line_sha256'] == '2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00'
assert handoff['manifest_sha256'] == XR_MANIFEST_SHA == hashlib.sha256(XR_MANIFEST.read_bytes()).hexdigest()
assert sorted(handoff['carrier_xr']) == sorted(SHIP_NAMES)
assert sorted(p.name for p in XR_CARRIER_DIR.iterdir()) == sorted(SHIP_NAMES), 'CARRIER_FOLDER_HOLDS_EXACTLY_TWO_FILES'
contents, ship_table = {}, {}
for name in SHIP_NAMES:
    entry = handoff['carrier_xr'][name]
    assert entry == handoff['files'][name], ('CARRIER_EQUALS_EXAM_FILE', name)
    size, want = entry['bytes'], entry['sha256']
    raw = (XR_CARRIER_DIR / name).read_bytes()
    assert len(raw) == size and hashlib.sha256(raw).hexdigest() == want, ('XR_FILE_IS_NOT_THE_SEALED_ONE', name)
    contents['xr/' + name] = raw
    ship_table[name] = {'bytes': size, 'sha256': want}
assert ship_table['INPUTS_XREAL.json']['sha256'] == XR_INPUTS_SHA and ship_table['XREAL_PINS.json']['sha256'] == XR_PINS_SHA
spent_contents, spent_table = {}, {}
for name, want in X5SPENT.items():
    raw = (X5EXAM / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == want, ('X5SPENT_FILE_IS_NOT_THE_PINNED_ONE', name)
    spent_contents['x5spent/' + name] = raw
    spent_table[name] = {'bytes': len(raw), 'sha256': want}


def deterministic_zip(path, files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'x', zipfile.ZIP_STORED) as out:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=FIXED)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            out.writestr(info, files[name])
    data = buffer.getvalue()
    if path.exists():
        assert path.read_bytes() == data, ('KIT_ZIP_DIFFERS_FROM_REBUILD', path.name)
    else:
        with open(path, 'xb') as stream:
            stream.write(data)
    with zipfile.ZipFile(path) as check:
        assert check.namelist() == sorted(files) and check.testzip() is None
        for name in sorted(files):
            assert check.read(name) == files[name], name


XR_CARRIER = HERE / 'XR_CARRIER_V1.zip'
deterministic_zip(XR_CARRIER, contents)
SPENT_CARRIER = HERE / 'X5SPENT_CARRIER_V1.zip'
deterministic_zip(SPENT_CARRIER, spent_contents)

argv = list(stage['argv'])
i = argv.index('--expected-freeze-sha256')
assert argv[i + 1].startswith('<')
argv[i + 1] = FREEZE_SHA
st = {k: stage[k] for k in ('name', 'type', 'source', 'cwd', 'pythonpath', 'env', 'limit', 'requires', 'create_output_dir',
                            'required_outputs')}
st['argv'] = argv
assert st['required_outputs'] == ['xreal_out/XREAL_HOST.json', 'xreal_out/XREAL_HOST.json.sha256'] and st['limit'] == 3000
assert st['name'] == 'xreal_host_run' and st['source'] == 'xreal' and st['cwd'] == PKG
assert argv[argv.index('--xr-dir') + 1] == '../../xr/xr' and argv[argv.index('--spent-dir') + 1] == '../../x5spent/x5spent'

GUARDS = ['CAS_NATIVE_TWO_ROUTE_AWS', 'CAS_NATIVE_SEMANTIC_AWS',
          'HELM_XREAL_AWS', 'XREAL_W4_DIR', 'XREAL_W3B_DIR', 'XREAL_W3_DIR', 'XREAL_W2_DIR', 'XREAL_W1_DIR', 'XREAL_XR_DIR',
          'XREAL_WORKERS', 'XREAL_FRAMES_DIR',
          'HELM_R1W5_AWS', 'R1W5_W3B_DIR', 'R1W5_W3_DIR', 'R1W5_W2_DIR', 'R1W5_W1_DIR', 'R1W5_X5_DIR', 'R1W5_X3SPENT_DIR',
          'R1W5_OUTPUT_DIR', 'R1W5_WORKERS', 'R1W5_DEADLINE_SECONDS',
          'HELM_R1W4_AWS', 'R1W4_W3B_DIR', 'R1W4_W3_DIR', 'R1W4_W2_DIR', 'R1W4_W1_DIR', 'R1W4_X4_DIR', 'R1W4_SPENT_DIR',
          'R1W4_OUTPUT_DIR', 'R1W4_WORKERS', 'R1W4_DEADLINE_SECONDS',
          'HELM_R1W3B_AWS', 'R1W3B_W3_DIR', 'R1W3B_W2_DIR', 'R1W3B_W1_DIR', 'R1W3B_X3_DIR', 'R1W3B_X2LANG_DIR',
          'R1W3B_OUTPUT_DIR', 'R1W3B_WORKERS', 'R1W3B_DEADLINE_SECONDS',
          'HELM_R1W3_AWS', 'R1W3_W1_DIR', 'R1W3_W2_DIR', 'R1W3_GB3_ZIP',
          'R1W3_X2_DIR', 'R1W3_OUTPUT_DIR', 'R1W3_WORKERS', 'R1W3_DEADLINE_SECONDS',
          'HELM_R1W2_AWS', 'R1W2_W1_DIR', 'R1W2_GB3_ZIP', 'R1W2_X1_DIR',
          'R1W2_X0_DIR', 'R1W2_OUTPUT_DIR', 'R1W2_WORKERS', 'R1W2_DEADLINE_SECONDS', 'HELM_CANONICAL_BRAIN_DIR',
          'R1W1_HOST', 'R1W1_FRESH_DIR', 'R1W1_OUTPUT_DIR', 'R1W1_WORKERS', 'R1W1_TORCH_SLOTS', 'R1W1_DEADLINE_SECONDS',
          'HELM_R1W1_AWS', 'RB_I1B_OUTPUT_DIR', 'HELM_RB3_AWS', 'RB3_OUTPUT_DIR', 'RB3_GB3_ZIP', 'RB3_WORKERS',
          'RB3_DEADLINE_SECONDS', 'HELM_RB2C_AWS', 'RB2C_OUTPUT_DIR', 'HELM_RB2_AWS', 'RB2_OUTPUT_DIR', 'RB2_GB3_ZIP',
          'RB2_TORCH_PYTHON', 'HELM_GB2_CONTINUITY_AWS', 'GB2_OUTPUT_DIR', 'HELM_GA_NESTED_REPAIR_AWS', 'GA_OUTPUT_DIR',
          'GA_BEFORE_ROOT', 'HELM_ASOM_NATIVE_ADMITTED', 'HELM_ASOM_REFERENCE_S2_AWS', 'HELM_ASOM_REFERENCE_S2_JOB_ID',
          'HELM_ASOM_REFERENCE_S1_AWS', 'HELM_ASOM_REFERENCE_S1_JOB_ID', 'CAS_NATIVE_TEACHING_AWS',
          'CAS_NATIVE_TEACHING_EXTERNAL_CONTROLLER', 'CAS_NATIVE_DIAGNOSIS_AWS', 'HELM_TEST_EVIDENCE_DIR']
existing = ledger_existing()


def names_of(zp):
    with zipfile.ZipFile(zp) as zz:
        return [n for n in zz.namelist() if not n.endswith('/')]


def modules(names_, pkg, sub):
    pre = pkg + '/' + sub + '/'
    return sorted(n[len(pre):-3] for n in names_ if n.startswith(pre) and n.endswith('.py')
                  and '/' not in n[len(pre):] and not n.endswith('__init__.py'))


W4PKG, W3BPKG, W3PKG = 'HELM_R1_W4_20261019', 'HELM_R1_W3B_20261019', 'HELM_R1_W3_20261019'
w4names, w3bnames, w3names = names_of(W4_ZIP), names_of(W3B_ZIP), names_of(W3_ZIP)
config = {
    'job': job, 'short': short, 'folder': folder, 'lease_stem': lease_stem, 'owner_approval_file': approval,
    'previous': None,  # filled by the caller (finalize_config_c42.py)
    'existing_allocation_usd': existing,
    'existing_allocation_note': ('build_job.py requires this to equal the ledger pointer (%r), which ALREADY holds the X-REAL '
                                 'hold of 1.00 USD; widen_window_120_held_xr.py rewrites the controller ledger numbers to '
                                 'existing %r + new 1.00 = combined %r.' % (existing, round(existing - 1.0, 2), existing)),
    'purpose': ("HELM-R1 X-REAL, scored host run (job c42): the first exam built from material outside our own generators - "
                "128 real food sentences (Part S), 64 real recipes as-is and 64 renamed (Parts R-ASIS and R-REBOUND), 192 restart "
                "worlds with real file damage (Part F) - on the frozen wave-4 brain, with the Unity Eye scan, a plain checksum "
                "(WATCHDOG) and the baselines. Package HELM_XREAL_20261019 (sealed a9b4c954, PACKAGE_FREEZE 67b48541, every member "
                "re-hashed). Owner pre-approval line per APPROVAL_RECORD_XREAL.md (sha256 2a8a6f86, also the exam seed source with "
                "the zip hash). The one supervisor stage xreal_host_run (kit/STAGE_XREAL.json) runs kit/run_xreal.py: the wave 1, 2, "
                "3, 3b and 4 carried tests, the X-REAL tests, then the X-REAL pool (23 units two at a time). Raw data only "
                "(xreal_out/XREAL_HOST.json + .sha256); the verdict and the part words come from the frozen laptop reader "
                "xreal/merge_xreal.py. No source corpus ships; the host gets only the custodian's carrier xr. One m6i.xlarge, "
                "2-CPU slice, 14 GiB, us-west-2, ami-0dddfa1ffa6b87af7; XREAL_WORKERS=2; command deadline 2400 s; host window "
                "120 min (force 116, work 111); cap 1.00 USD (the owner total cap); one scored attempt + at most one plumbing retry."),
    'throughput_evidence': ('RUN_LIMITS_XREAL.json estimate: 23 host units, host about 500-700 s (c40: host 489.9 s, runner 205.98 s '
                            'for 41 units); builder laptop pool 21 units in 49.9 s at one worker. Stage limit 3000 s inside the '
                            '120-minute window (host 120 / force 116 / work 111 min = 6660 s); the runner caps the whole command at 2400 s.'),
    'sources': [{'name': 'xreal', 'zip': str(ZIP), 'sha256': ZIP_SHA},
                {'name': 'r1w4', 'zip': str(W4_ZIP), 'sha256': W4_SHA},
                {'name': 'r1w3b', 'zip': str(W3B_ZIP), 'sha256': W3B_SHA},
                {'name': 'r1w3', 'zip': str(W3_ZIP), 'sha256': W3_SHA},
                {'name': 'r1w2', 'zip': str(W2_ZIP), 'sha256': W2_SHA},
                {'name': 'w1', 'zip': str(W1_ZIP), 'sha256': W1_SHA},
                {'name': 'xr', 'zip': str(XR_CARRIER), 'sha256': sha(XR_CARRIER)},
                {'name': 'x5spent', 'zip': str(SPENT_CARRIER), 'sha256': sha(SPENT_CARRIER)}],
    'plan': {
        'scope': 'XREAL_NAMED_CORPORA_HOST_WRITES_RAW_DATA_ONLY_READING_IS_ON_THE_LAPTOP',
        'guard_names': GUARDS,
        'dependencies': ['torch', 'numpy', 'jsonschema'],
        'preflight_modules': {
            'xreal/' + PKG: ['xreal', 'tests_xreal'],
            'xreal/' + PKG + '/kit': ['run_xreal', 'plan_check', 'job_supervisor'],
            'xreal/' + PKG + '/xreal': modules(names, PKG, 'xreal'),
            'r1w4/' + W4PKG: ['r1w4', 'tests_r1w4'],
            'r1w4/' + W4PKG + '/r1w4': modules(w4names, W4PKG, 'r1w4'),
            'r1w3b/' + W3BPKG: ['r1w3b', 'tests_r1w3b'],
            'r1w3b/' + W3BPKG + '/r1w3b': modules(w3bnames, W3BPKG, 'r1w3b'),
            'r1w3/' + W3PKG: ['r1w3', 'tests_r1w3'],
            'r1w3/' + W3PKG + '/r1w3': modules(w3names, W3PKG, 'r1w3'),
            'r1w2/HELM_R1_W2_20261018': ['r1w2', 'tests_r1w2'],
            'w1/HELM_R1_W1_20261015': ['rb', 'rb2', 'rb3', 'r1', 'tests_rb', 'tests_rb2', 'tests_rb3', 'tests_r1', 'label_audit_b'],
            'w1/HELM_R1_W1_20261015/r1': ['common_r1', 'host_summary', 'exams', 'switches', 'gb_arms', 'tb_arms', 'cce_stage',
                                          'merge_r1w1', 'check_fresh_format']},
        'stages': [st]}}
out = KIT / (short.replace('-', '_') + '_config.json')
print(json.dumps({'out': str(out), 'existing': existing, 'sources': [(s['name'], s['sha256'][:8]) for s in config['sources']],
                  'xr_manifest_sha256': XR_MANIFEST_SHA, 'xr_carrier_members': sorted(contents), 'ship_table': ship_table,
                  'spent_table': spent_table, 'stage_argv': argv}, indent=1))
Path(str(out) + '.pending').write_text(json.dumps(config, indent=1), encoding='utf-8', newline='\n')
