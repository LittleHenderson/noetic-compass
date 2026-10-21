"""DeepSeek's launch checklist (report 2026-10-20, section 6.3), lines 1-10, each as a program. Run on the laptop right before
`aws_control_c52.py launch N`; stop at the first failure. Prints one line per check and writes PREFLIGHT_CHECKS_C52_aN.json into
the job record. Usage: python -X utf8 -B -I preflight_checks_c52.py <attempt 1|2>"""
import hashlib, importlib.util, json, re, sys, tempfile, zipfile
from pathlib import Path

A = int(sys.argv[1])
C = Path(r'C:\Users\wakil\Documents\Codex')
W7 = C / '2026-10-20' / 'r1_wave7'
V = json.loads((W7 / 'C52_VALUES.json').read_text(encoding='utf-8'))
RUN = W7 / ('run_c52_r1w7v4_%s' % V['RUN_DATE'])
JR = RUN / 'job_record'
TAG = 'aws-c52-a%d' % A
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows = []


def check(name, ok, detail=''):
    rows.append({'check': name, 'ok': bool(ok), 'detail': str(detail)[:300]}); print(('PASS ' if ok else 'FAIL ') + name + ('  ' + str(detail)[:120] if detail else ''))
    if not ok:
        (JR / ('PREFLIGHT_CHECKS_C52_a%d.json' % A)).write_text(json.dumps(rows, indent=1) + '\n', encoding='utf-8')
        raise SystemExit('STOP: ' + name)


# 1 the watchdog is running before any launch
w = JR / (TAG + '-watch.json')
check('1 watchdog READY', w.exists() and json.loads(w.read_bytes()).get('status') == 'READY', 'start `aws_control_c52.py watch %d` first and leave it running' % A)
# 2 the attempt is unused
check('2 attempt unused', not (JR / (TAG + '-launch-intent.json')).exists() and not (JR / (TAG + '-control.json')).exists())
# 3 the plan passes the supervisor's own validator
payload = RUN / 'payload_c52' / 'c52-payload.zip'
with zipfile.ZipFile(payload) as z:
    plan = json.loads(z.read('execution/job_plan.json')); sup = z.read('execution/job_supervisor.py'); inv = json.loads(z.read('payload_inventory.json'))
    freeze_bytes = z.read('sources/r1w7/HELM_R1_W7_20261020/PACKAGE_FREEZE.json'); names = set(z.namelist())
with tempfile.TemporaryDirectory() as td:
    sp = Path(td) / 'job_supervisor.py'; sp.write_bytes(sup)
    spec = importlib.util.spec_from_file_location('js_pf', sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    try:
        ok = m.validate_plan(plan) is True; det = 'validate_plan True'
    except Exception as e:
        ok, det = False, repr(e)
check('3 validate_plan on the shipped plan', ok, det)
# 4 --expected-freeze-sha256 equals sha256(payload PACKAGE_FREEZE.json)
argv = plan['stages'][0]['argv']; exp = argv[argv.index('--expected-freeze-sha256') + 1]
check('4 expected freeze == payload freeze', exp == hashlib.sha256(freeze_bytes).hexdigest() == V['FREEZE_SHA'], exp[:16])
# 5 no fill token survives in the plan
pt = json.dumps(plan)
check('5 no fill token in plan', '<' not in ''.join(argv) and '{{' not in pt)
# 6 every value in C52_VALUES.json equals the artefact on disk
cust = W7 / V['CUSTODY_DIR']; appr = W7 / 'approval_v4'
vals = {'ZIP_SHA': h(W7 / V['ZIP_NAME']), 'FREEZE_SHA': h(W7 / 'PACKAGE_FREEZE_R1W7_v4.json'), 'CARRIER_SHA': h(cust / 'X7_CARRIER_V1.zip'),
        'MANIFEST_SHA': h(cust / 'out' / 'MANIFEST_X7.json'), 'RECEIVER_CHECK_SHA': h(cust / 'out' / 'RECEIVER_CHECK_X7.json'),
        'PINS_SHA': h(cust / 'out' / 'carrier' / 'x7' / 'X7_PINS.json'), 'CUSTODY_HANDOFF_SHA': h(cust / V['CUSTODY_HANDOFF_NAME']),
        'APPROVAL_MD_SHA': h(appr / 'APPROVAL_RECORD_R1W7.md'), 'APPROVAL_JSON_SHA': h(appr / 'APPROVAL_RECORD_R1W7.json'), 'PAYLOAD_SHA': h(payload)}
bad = {k: (V.get(k, '')[:8], v[:8]) for k, v in vals.items() if V.get(k) != v}
check('6 values file equals artefacts on disk', not bad, bad or '%d values match' % len(vals))
# 7 the worker template's substitution sites are intact
ctrl = (JR / 'aws_control_c52.py').read_text(encoding='utf-8'); worker = (JR / 'worker_c52.sh').read_text(encoding='utf-8')
check('7 template sites intact', ctrl.count("'__PAYLOAD_SHA__'") == 1 and worker.count('__PAYLOAD_SHA__') == 1 and '{{' not in ctrl and '{{' not in worker
      and re.search(r"^PAYLOAD_SHA = '%s'" % V['PAYLOAD_SHA'], ctrl, re.M) is not None, 'controller constant equals payload sha; one template site each')
# 8 simulate the worker fill
filled = worker.replace('__JOB__', 'helm-claude-r1w7v4-%s-c52' % V['RUN_DATE']).replace('__PAYLOAD_SHA__', V['PAYLOAD_SHA']).replace('__OS_SHUTDOWN_MIN__', '60')
for ph in ('__URL_INPUT__', '__URL_PROGRESS__', '__URL_TRANSPORT__', '__URL_DELIVERABLE__'):
    filled = filled.replace(ph, 'https://example.invalid/x')
check('8 worker fill simulation', not re.findall(r'__[A-Z_]+__', filled) and filled.count(V['PAYLOAD_SHA']) == 1)
# 9 the ledger hold exists and its sha is in the closeout
res = C / '2026-10-01' / 'task-2' / 'helm_operator_preparation' / ('r1w7v4_c52_reservation_%s' % V['RUN_DATE']) / 'BUDGET_RESERVATION_R1W7V4_C52.json'
led = json.loads((C / 'AWS_COMBINED_ALLOCATION_CURRENT.json').read_text(encoding='utf-8'))
clo = (JR / 'closeout_c52.py').read_text(encoding='utf-8')
check('9 ledger hold present and pinned', res.is_file() and h(res) == V.get('RESERVATION_SHA') and ("RESERVATION_SHA256 = '%s'" % V.get('RESERVATION_SHA')) in clo
      and ('helm-claude-r1w7v4-%s-c52' % V['RUN_DATE']) in led.get('last_jobs', []), 'hold in ledger last_jobs; closeout pinned')
# 9b the transport lease exists for this job (the controller refuses LEASE_REQUIRED without it; c50 lesson)
lease = RUN / 'CLAUDE_R1W7V4_C52_TRANSPORT_LEASE.json'
check('9b transport lease present', lease.is_file() and json.loads(lease.read_bytes()).get('job') == 'helm-claude-r1w7v4-%s-c52' % V['RUN_DATE'])
# 10 the payload's members match its inventory
check('10 payload members match inventory', names == set(inv['members']) | {'payload_inventory.json'} and len(inv['members']) == len(names) - 1, '%d members' % len(inv['members']))
(JR / ('PREFLIGHT_CHECKS_C52_a%d.json' % A)).write_text(json.dumps(rows, indent=1) + '\n', encoding='utf-8')
print('ALL 10 PRE-LAUNCH CHECKS PASS; next: aws_control_c52.py preflight %d, then launch %d' % (A, A))
