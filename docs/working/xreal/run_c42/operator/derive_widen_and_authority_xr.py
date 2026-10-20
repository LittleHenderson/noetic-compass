"""Derive (1) widen_window_120_held_xr.py (job c42, the scored X-REAL run) from r1w5kit/widen_window_120_held_w5.py
(c40, run-proven) and (2) write_authority_job_cap100_120_held_xr.py from r1w5kit/write_authority_job_cap100_120_held_w5.py,
by exact substitutions. Window numbers unchanged (host 120 / force 116 / work 111 min; the package supervisor is wave 2's
byte for byte, RUN_LIMITS_XREAL.json). Changes:
  - hold: the c42 reservation (BUDGET_RESERVATION_XREAL_C42.json, 1.00 USD; sha256 read from
    x_real_c42_operator_notes/LEDGER_HOLD_RESULT_XREAL_C42.json); controller existing = pointer - 1.00, combined = pointer;
    cap 1.00 unchanged;
  - job_supervisor.py: REPLACED by the sealed X-REAL package's kit/job_supervisor.py (sha256 3b2337ca..., the same bytes
    as waves 2, 3, 3b, 4 and 5), after checking the built copy is the kit base (5088f4fb...);
  - authority text names the X-REAL line."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
W5K = HERE.parent / 'r1w5kit'
OP = HERE.parent.parent
hold = json.loads((OP / 'x_real_c42_operator_notes' / 'LEDGER_HOLD_RESULT_XREAL_C42.json').read_bytes())
RES_PATH = OP / 'x_real_c42_reservation_20261019' / 'BUDGET_RESERVATION_XREAL_C42.json'
assert hold['reservation'] == str(RES_PATH) and hashlib.sha256(RES_PATH.read_bytes()).hexdigest() == hold['reservation_sha256']
RES_SHA = hold['reservation_sha256']
SUP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-19\x_real\HELM_XREAL_20261019\kit\job_supervisor.py')
assert hashlib.sha256(SUP.read_bytes()).hexdigest() == '3b2337ca75b189287c4591ed44671e308d37ef92d043f7bebb37ede77e6a1b01'


def sub(text, pairs):
    for old, new, count in pairs:
        assert text.count(old) == count, (old[:120], text.count(old))
        text = text.replace(old, new)
    return text


t = (W5K / 'widen_window_120_held_w5.py').read_text(encoding='utf-8')
t = sub(t, [
    ('"""[c40 R1W5, derived by r1w5kit/derive_widen_and_authority_w5.py from the c39 script (itself from the run-proven c38 script): 120/116/111 min, package supervisor swapped in, cap 1.00 = the 1.00 total hold.]',
     '"""[c42 X-REAL, derived by xrealkit/derive_widen_and_authority_xr.py from the run-proven c40 script: 120/116/111 min, package supervisor swapped in, cap 1.00 = the 1.00 total hold.]', 1),
    ("RESERVATION = Path(r'C:\\Users\\wakil\\Documents\\Codex\\2026-10-01\\task-2\\helm_operator_preparation\\r1_w5_c40_reservation_20261019\\BUDGET_RESERVATION_R1_W5_C40.json')\n"
     "RESERVATION_SHA256 = '5a7c9dd9c85f3d3092d664a362effb1df4c7ae73c5ab4ebe91a870b35f285878'\n"
     "PARENT_JOB = 'helm-claude-r1w5-20261019-c40'\nPARENT_HOLD = 1.0\n"
     "PKG_SUPERVISOR = Path(r'C:\\Users\\wakil\\Documents\\Codex\\2026-10-19\\r1_wave5\\HELM_R1_W5_20261019\\kit\\job_supervisor.py')\n",
     "RESERVATION = Path(r'C:\\Users\\wakil\\Documents\\Codex\\2026-10-01\\task-2\\helm_operator_preparation\\x_real_c42_reservation_20261019\\BUDGET_RESERVATION_XREAL_C42.json')\n"
     "RESERVATION_SHA256 = '" + RES_SHA + "'\n"
     "PARENT_JOB = 'helm-claude-xreal-20261019-c42'\nPARENT_HOLD = 1.0\n"
     "PKG_SUPERVISOR = Path(r'C:\\Users\\wakil\\Documents\\Codex\\2026-10-19\\x_real\\HELM_XREAL_20261019\\kit\\job_supervisor.py')\n", 1),
    ("refuse('USAGE', 'python -B widen_window_120_held_w5.py <built controller folder>')",
     "refuse('USAGE', 'python -B widen_window_120_held_xr.py <built controller folder>')", 1),
    ("'status': 'WIDENED_120_116_111_W5_PACKAGE_SUPERVISOR_HOLD_ALREADY_IN_POINTER'", "'status': 'WIDENED_120_116_111_XR_PACKAGE_SUPERVISOR_HOLD_ALREADY_IN_POINTER'", 1),
    ("'run raise_memory_14g.py, then the review, then r1w5kit/write_authority_job_cap100_120_held_w5.py'",
     "'run raise_memory_14g.py, then the review, then xrealkit/write_authority_job_cap100_120_held_xr.py'", 1),
])
body = t.split('"""', 2)[2]
for stale in ('helm-claude-r1w5-20261019', 'R1_W5_C40', 'r1_w5_c40', '5a7c9dd9', "r1_wave5\\\\", 'w5.py'):
    assert stale not in body, (stale, [l for l in body.splitlines() if stale in l][:3])
compile(t, 'widen_window_120_held_xr.py', 'exec')
(HERE / 'widen_window_120_held_xr.py').write_text(t, encoding='utf-8', newline='\n')

a = (W5K / 'write_authority_job_cap100_120_held_w5.py').read_text(encoding='utf-8')
a = sub(a, [
    ('[c40 R1W5: derived from r1w4kit/write_authority_job_cap100_120_held_w4.py by exact substitution; cap 1.00 = the 1.00 total hold, host 120 min (force 116, work 111)]',
     '[c42 X-REAL: derived from r1w5kit/write_authority_job_cap100_120_held_w5.py by exact substitution; cap 1.00 = the 1.00 total hold, host 120 min (force 116, work 111)]', 1),
    ("'Owner direct in-chat approval to Claude Code, %s sha256 %s; one host m6i.xlarge 2-CPU slice, $1.00 all-services = the owner-approved $1.00 R1W5 total cap, 120 min, one scored attempt + at most one plumbing retry, no automatic retry'",
     "'Owner pre-approval line (X-REAL at 1 USD) bound to package a9b4c954 by APPROVAL_RECORD_XREAL.md, operator record %s sha256 %s; one host m6i.xlarge 2-CPU slice, $1.00 all-services = the owner-approved $1.00 X-REAL total cap, 120 min, one scored attempt + at most one plumbing retry, no automatic retry'", 1),
])
for stale in ('R1W5', 'R1W4', 'R1W3b', 'R1W3B'):
    assert stale not in a.split('"""', 2)[2], stale
compile(a, 'write_authority_job_cap100_120_held_xr.py', 'exec')
(HERE / 'write_authority_job_cap100_120_held_xr.py').write_text(a, encoding='utf-8', newline='\n')
for p in ('widen_window_120_held_xr.py', 'write_authority_job_cap100_120_held_xr.py'):
    print(p, hashlib.sha256((HERE / p).read_bytes()).hexdigest())
