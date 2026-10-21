"""Build the c52 payload (HELM-R1 wave 7 v4, the CHAT WAVE re-run) from pinned archives. Reads zips in memory; never opens exam
content (the carrier is copied as bytes from the custodian's pinned zip and checked by sha256 and member NAMES only).
Layout = STAGE_R1W7.json layout_note: sources/<name>/<archive member>; execution/job_plan.json; execution/job_supervisor.py;
payload_inventory.json. Modelled on build_payload_c51.py (run-proven attempt 2, 2026-10-20) with the c51 lessons built in:
  * the assembled plan is validated with the SAME supervisor bytes the host will run (`validate_plan`) before the zip is written
    (DeepSeek checklist line 3; c51 attempt 1 died on PLAN_INVALID);
  * no `<...>` or `{{...}}` fill token may survive in the plan, and `--expected-freeze-sha256` must equal the sha256 of the
    package's own PACKAGE_FREEZE.json (checklist lines 4-5);
  * the payload sha256 is written into C52_VALUES.json so the kit fill can never carry a stale value (the c50 lesson).
Usage: python -X utf8 -B -I build_payload_c52.py        (reads C52_VALUES.json: ZIP_SHA, CARRIER_SHA, CUSTODY_DIR, RUN_DATE)"""
import hashlib, importlib.util, io, json, re, tempfile, zipfile
from pathlib import Path, PurePosixPath

C = Path(r'C:\Users\wakil\Documents\Codex')
W6 = C / '2026-10-19' / 'r1_wave6'
D = W6 / 'deps'
W7 = C / '2026-10-20' / 'r1_wave7'
V = json.loads((W7 / 'C52_VALUES.json').read_text(encoding='utf-8'))
RUN = W7 / ('run_c52_r1w7v4_%s' % V['RUN_DATE'])
OUT = RUN / 'payload_c52' / 'c52-payload.zip'
JOB = 'helm-claude-r1w7v4-%s-c52' % V['RUN_DATE']
ZIP = W7 / V['ZIP_NAME']
CARRIER = W7 / V['CUSTODY_DIR'] / 'X7_CARRIER_V1.zip'
for k in ('ZIP_SHA', 'FREEZE_SHA', 'CARRIER_SHA'):
    assert re.fullmatch(r'[0-9a-f]{64}', str(V.get(k, ''))), 'C52_VALUES.json: %s must be a full sha256 (fill it first)' % k
SOURCES = {
 'r1w7': (ZIP, V['ZIP_SHA'], 'HELM_R1_W7_20261020'),
 'w1': (D / 'HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip', '31f97d67122b45860cdff2b03481655fa502ff359f10b70a181904972ddbb3c9', 'HELM_R1_W1_20261015'),
 'r1w3': (D / 'HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip', '152bca2a3c869212642f96514e7d485413727bf92cf67e9aff1774cefa532362', 'HELM_R1_W3_20261019'),
 'r1w3b': (D / 'HELM_R1_W3B_20261019_SOURCE_R1W3B.zip', 'a4f82556bf0fc26de5635a7c81ec8f5053951d4c64a3906c8e5dd474e3814d26', 'HELM_R1_W3B_20261019'),
 'r1w6': (W6 / 'HELM_R1_W6_20261019_SOURCE_R1W6.zip', 'f1b64a5edf0df2b152c867f328c71b3df8640a759836108079590e7959c31b47', 'HELM_R1_W6_20261019'),
 'rbw1t': (D / 'HELM_RBW1T_20261019_SOURCE_RBW1T.zip', '3a8ae37eb51c18414bfa83a71b9079dd7ec2282bec6ba3952d86ac0454f0e967', 'HELM_RBW1T_20261019'),
 'x7': (CARRIER, V['CARRIER_SHA'], 'x7'),
}
CARRIER_NAMES = sorted(['x7/INPUTS_REAL_X7.json', 'x7/INPUTS_CONV_X7.json', 'x7/INPUTS_NOISE_X7.json', 'x7/X7_PINS.json'])
h = lambda b: hashlib.sha256(b).hexdigest()
members = {}
assert not OUT.exists(), 'PAYLOAD_EXISTS'
for name, (p, want, top) in SOURCES.items():
    raw = p.read_bytes(); assert h(raw) == want, (name, 'SHA_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files = [i for i in z.infolist() if not i.is_dir()]
        if name == 'x7':
            assert sorted(i.filename for i in files) == CARRIER_NAMES, ('x7', 'CARRIER_MEMBERS', sorted(i.filename for i in files))
        for i in files:
            parts = PurePosixPath(i.filename).parts
            assert parts[0] == top, (name, i.filename)
            assert '..' not in parts and not i.filename.startswith('/') and '__pycache__' not in parts
            assert PurePosixPath(i.filename).suffix not in ('.pyc', '.pyo', '.so', '.pth'), i.filename
            assert 'KEYS' not in i.filename.upper() or name != 'x7', i.filename
            key = 'sources/%s/%s' % (name, i.filename)
            assert key not in members
            members[key] = z.read(i)
PKG = 'sources/r1w7/HELM_R1_W7_20261020/'
freeze_sha = h(members[PKG + 'PACKAGE_FREEZE.json'])
assert freeze_sha == V['FREEZE_SHA'], 'FREEZE_SHA in C52_VALUES.json does not match the package'
stage = json.loads(members[PKG + 'kit/STAGE_R1W7.json'])
argv = stage['argv']; i = argv.index('--expected-freeze-sha256'); argv[i + 1] = freeze_sha
stage.pop('layout_note', None)
assert stage['name'] == 'r1w7_host_run' and stage['cwd'] == 'HELM_R1_W7_20261020' and stage['source'] == 'r1w7'
assert stage['pythonpath'] == ['HELM_R1_W7_20261020'], ('v4 stage pythonpath', stage['pythonpath'])
r1w7 = ['HELM_R1W7_AWS', 'HELM_CANONICAL_BRAIN_DIR', 'HELM_WIDE_BRAIN', 'HELM_WIDE_UNITS_NOTE', 'HELM_CAS_ADDRESS', 'HELM_CONTINUITY',
        'HELM_SESSION_DIR', 'R1W7_X7_DIR', 'R1W7_FRAMES_DIR', 'R1W7_OUTPUT_DIR', 'R1W7_WORKERS', 'R1W7_SUITES_FILE',
        'R1W7_DEADLINE_SECONDS'] + ['R1W7_%s_DIR' % n for n in ('W1', 'W3', 'W3B', 'W6', 'RBW1T')]
r1w6 = ['HELM_R1W6_AWS', 'R1W6_X6_DIR', 'R1W6_SPENT_DIR', 'R1W6_OUTPUT_DIR', 'R1W6_WORKERS', 'R1W6_SUITES_FILE',
        'R1W6_DEADLINE_SECONDS'] + ['R1W6_%s_DIR' % n for n in ('W1', 'W2', 'W3', 'W3B', 'W4', 'W5', 'RBW1T')]
older = ['HELM_RBW1T_AWS', 'RBW1T_W3_DIR', 'RBW1T_W3B_DIR', 'RBW1T_W1_DIR', 'RBW1T_FRAMES_DIR',
         'HELM_R1W5_AWS', 'R1W5_W3B_DIR', 'R1W5_W3_DIR', 'R1W5_W2_DIR', 'R1W5_W1_DIR', 'R1W5_X5_DIR', 'R1W5_X3SPENT_DIR',
         'R1W5_OUTPUT_DIR', 'R1W5_WORKERS', 'R1W5_DEADLINE_SECONDS', 'HELM_R1W4_AWS', 'R1W4_W3B_DIR', 'R1W4_W3_DIR',
         'R1W4_W2_DIR', 'R1W4_W1_DIR', 'R1W4_X4_DIR', 'R1W4_SPENT_DIR', 'R1W4_OUTPUT_DIR', 'R1W4_WORKERS',
         'R1W4_DEADLINE_SECONDS', 'HELM_R1W3B_AWS', 'R1W3B_W3_DIR', 'R1W3B_W2_DIR', 'R1W3B_W1_DIR', 'R1W3B_X3_DIR',
         'R1W3B_X2LANG_DIR', 'R1W3B_OUTPUT_DIR', 'R1W3B_WORKERS', 'R1W3B_DEADLINE_SECONDS', 'HELM_R1W3_AWS', 'R1W3_W1_DIR',
         'R1W3_W2_DIR', 'R1W3_GB3_ZIP', 'R1W3_X2_DIR', 'R1W3_OUTPUT_DIR', 'R1W3_WORKERS', 'R1W3_DEADLINE_SECONDS',
         'HELM_R1W2_AWS', 'R1W2_W1_DIR', 'R1W2_GB3_ZIP', 'R1W2_X1_DIR', 'R1W2_X0_DIR', 'R1W2_OUTPUT_DIR', 'R1W2_WORKERS',
         'R1W2_DEADLINE_SECONDS', 'R1W1_HOST', 'R1W1_FRESH_DIR', 'R1W1_OUTPUT_DIR', 'R1W1_WORKERS', 'R1W1_TORCH_SLOTS',
         'R1W1_DEADLINE_SECONDS', 'HELM_R1W1_AWS']
guards = ['CAS_NATIVE_TWO_ROUTE_AWS', 'CAS_NATIVE_SEMANTIC_AWS'] + r1w7 + r1w6 + [g for g in older if g not in r1w6]
assert len(guards) == len(set(guards))
plan = {'job': JOB, 'scope': 'R1W7V4_CHAT_WAVE_RERUN_NAMED_CORPORA_PLUS_SYNTHETIC_HOST_WRITES_RAW_DATA_ONLY_READING_IS_ON_THE_LAPTOP',
        'guard_names': guards, 'dependencies': [], 'preflight_modules': {}, 'stages': [stage]}
# ---- the c51 lessons, as programs ----
plan_text = json.dumps(plan)
assert '<' not in ''.join(stage['argv']) and '{{' not in plan_text, 'FILL_TOKEN_SURVIVES_IN_PLAN'
sup = members[PKG + 'kit/job_supervisor.py']
assert h(sup) == '3b2337ca75b189287c4591ed44671e308d37ef92d043f7bebb37ede77e6a1b01'   # byte copy of the run-proven supervisor
with tempfile.TemporaryDirectory() as td:
    sp = Path(td) / 'job_supervisor.py'; sp.write_bytes(sup)
    spec = importlib.util.spec_from_file_location('job_supervisor_c52_check', sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert m.validate_plan(json.loads(plan_text)) is True, 'VALIDATE_PLAN_REFUSED'
plan_raw = (json.dumps(plan, indent=1, sort_keys=True) + '\n').encode()
members['execution/job_plan.json'] = plan_raw
members['execution/job_supervisor.py'] = sup
inv = {'schema': 'helm.r1w7v4.c52.payload-inventory/1', 'job': JOB,
       'source_archives': {n: w for n, (_, w, _t) in SOURCES.items()}, 'carrier_zip_path': str(CARRIER),
       'plan_validated_with_supervisor_sha256': h(sup), 'expected_freeze_sha256': freeze_sha,
       'members': {k: {'sha256': h(v), 'bytes': len(v)} for k, v in sorted(members.items())}}
inv_raw = (json.dumps(inv, indent=1, sort_keys=True) + '\n').encode()
OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT, 'x', zipfile.ZIP_DEFLATED) as z:
    for k in sorted(members):
        z.writestr(k, members[k])
    z.writestr('payload_inventory.json', inv_raw)
(OUT.parent / 'job_plan.json').write_bytes(plan_raw)
(OUT.parent / 'payload_inventory.json').write_bytes(inv_raw)
res = {'payload': str(OUT), 'sha256': h(OUT.read_bytes()), 'bytes': OUT.stat().st_size, 'members': len(members),
       'expanded_bytes': sum(len(v) for v in members.values()), 'job_plan_sha256': h(plan_raw), 'inventory_sha256': h(inv_raw),
       'carrier_zip_sha256': V['CARRIER_SHA'], 'guard_names': len(guards), 'validate_plan': True}
(OUT.parent / 'PAYLOAD_RESULT_C52.json').write_text(json.dumps(res, indent=1, sort_keys=True) + '\n', encoding='utf-8')
V['PAYLOAD_SHA'] = res['sha256']; V['PAYLOAD_SHA8'] = res['sha256'][:8]
(W7 / 'C52_VALUES.json').write_text(json.dumps(V, indent=1, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(res, indent=1))
