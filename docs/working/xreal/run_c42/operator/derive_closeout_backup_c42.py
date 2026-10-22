"""Derive closeout_xreal_c42.py and backup_xreal_c42.py from the c40 scripts by exact substitution."""
import hashlib
from pathlib import Path

OP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')
N40 = OP / 'r1_w5_c40_operator_notes'
HERE = OP / 'x_real_c42_operator_notes'
appr = hashlib.sha256(Path(r'C:\Users\wakil\Documents\Codex\2026-10-19\x_real\APPROVAL_RECORD_XREAL.md').read_bytes()).hexdigest()


def sub(text, pairs):
    for old, new in pairs:
        assert text.count(old) >= 1, ('MISSING', old[:120])
        text = text.replace(old, new)
    return text


c = (N40 / 'closeout_r1w5_c40.py').read_text(encoding='utf-8')
c = sub(c, [
    ('"""Closeout for the R1W5 hold (job helm-claude-r1w5-20261019-c40, 1.00 USD): the scored host run c40 only (no torch\nwork on this wave). Derived from closeout_r1w3b_c38.py by substitution (house schema): cleanup proof for c40,',
     '"""Closeout for the X-REAL hold (job helm-claude-xreal-20261019-c42, 1.00 USD): the scored host run c42 only (no torch\nwork). Derived from closeout_r1w5_c40.py by substitution (house schema): cleanup proof for c42,'),
    ('Usage: python -B closeout_r1w5_c40.py <OUTCOME_WORDS>', 'Usage: python -B closeout_xreal_c42.py <OUTCOME_WORDS>'),
    ("JOB = 'helm-claude-r1w5-20261019-c40'", "JOB = 'helm-claude-xreal-20261019-c42'"),
    ("RESERVATION = OP / 'r1_w5_c40_reservation_20261019' / 'BUDGET_RESERVATION_R1_W5_C40.json'\nRESERVATION_SHA256 = '5a7c9dd9c85f3d3092d664a362effb1df4c7ae73c5ab4ebe91a870b35f285878'\nAPPROVAL = OP / 'OWNER_APPROVAL_R1W5_20261019T193227Z.json'\nRECORD = Path(r'C:\\Users\\wakil\\Documents\\Codex\\2026-10-19\\r1_wave5\\R1W5_APPROVAL_RECORD_20261019.md')\nJOBS = [('helm-claude-r1w5-20261019-c40', 'claude-r1w5-c40', OP / 'controller_claude_r1w5_c40')]",
     "RESERVATION = OP / 'x_real_c42_reservation_20261019' / 'BUDGET_RESERVATION_XREAL_C42.json'\nRESERVATION_SHA256 = '7fb27c7ee295cc2418fc9430671906d28afc5aad2295e058482821666c32667c'\nAPPROVAL = OP / 'OWNER_APPROVAL_XREAL_20261020T000138Z.json'\nRECORD = Path(r'C:\\Users\\wakil\\Documents\\Codex\\2026-10-19\\x_real\\APPROVAL_RECORD_XREAL.md')\nJOBS = [('helm-claude-xreal-20261019-c42', 'claude-xreal-c42', OP / 'controller_claude_xreal_c42')]"),
    ('CONSERVATIVE_RATE = 0.46        # RUN_LIMITS_R1W5.json conservative rate', 'CONSERVATIVE_RATE = 0.46        # RUN_LIMITS_XREAL.json conservative rate'),
    ("c40 = OP / 'controller_claude_r1w5_c40'\nproof_path = c40 / 'CLEANUP_PROOF_R1W5_C40.json'", "c42 = OP / 'controller_claude_xreal_c42'\nproof_path = c42 / 'CLEANUP_PROOF_XREAL_C42.json'"),
    ("'helper_cleanup_proof': 'none: no helper job ran (X5 built on the laptop by the custodian, 0 USD; no torch on this wave)'",
     "'helper_cleanup_proof': 'none: no helper job ran (the X-REAL exam was built on the laptop by the custodian, 0 USD; no torch)'"),
    ("rec = OP / ('BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_R1W5_C40_' + stamp + '.json')", "rec = OP / ('BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_XREAL_C42_' + stamp + '.json')"),
    ("\"%s sha256 %s, quoting the owner's R1W5 sign line (sha256 a9dd6ff2; R1W5_APPROVAL_RECORD_20261019.md sha256 %s): package b6598687, one attempt + one plumbing retry, cap 1.00 USD\"",
     "\"%s sha256 %s, quoting the owner's pre-approval line (sha256 2a8a6f86, 121 bytes, 'X-REAL at 1 USD'; APPROVAL_RECORD_XREAL.md sha256 %s binds it to package a9b4c954): one attempt + one plumbing retry, cap 1.00 USD\""),
    ("'helper_note': 'no helper job ran under this hold (X5 laptop-only, 0 USD)'", "'helper_note': 'no helper job ran under this hold (custodian laptop-only, 0 USD)'"),
    ("'conservative_rate_note': 'at RUN_LIMITS_R1W5.json conservative 0.46 USD per host hour", "'conservative_rate_note': 'at RUN_LIMITS_XREAL.json conservative 0.46 USD per host hour"),
    ("'written_by': 'Claude Code sub-agent, AWS launch operator c40 (laptop MSI)'", "'written_by': 'Claude Code sub-agent, AWS launch operator c42 (laptop MSI)'"),
])
for stale in ('r1w5', 'R1W5', 'c40', 'b6598687', 'a9dd6ff2', 'X5'):
    left = [l for l in c.split('"""', 2)[2].splitlines() if stale in l]
    assert not left, (stale, left[:2])
compile(c, 'closeout_xreal_c42.py', 'exec')
(HERE / 'closeout_xreal_c42.py').write_text(c, encoding='utf-8', newline='\n')

b = (N40 / 'backup_r1w5_c40.py').read_text(encoding='utf-8')
b = sub(b, [
    ('"""Back up the R1W5 c40 deliverable and records to D:\\\\tksCAS-archive\\\\r1_wave5_c40_20261019\\\\ with three sha256\nconfirmations per file (source before copy, destination after copy, destination re-read). Writes BACKUP_MANIFEST.\nDerived from backup_r1w3b_c38.py. X5 custody files are copied by bytes only (custody: never opened)."""',
     '"""Back up the X-REAL c42 deliverable and records to D:\\\\tksCAS-archive\\\\x_real_c42_20261019\\\\ with three sha256\nconfirmations per file (source before copy, destination after copy, destination re-read). Writes BACKUP_MANIFEST.\nDerived from backup_r1w5_c40.py. X-REAL custody files are copied by bytes only (custody: never opened)."""'),
    ("W5 = Path(r'C:\\Users\\wakil\\Documents\\Codex\\2026-10-19\\r1_wave5')\nDEST = Path(r'D:\\tksCAS-archive\\r1_wave5_c40_20261019')",
     "XRD = Path(r'C:\\Users\\wakil\\Documents\\Codex\\2026-10-19\\x_real')\nDEST = Path(r'D:\\tksCAS-archive\\x_real_c42_20261019')"),
    ("    'run_c40_r1w5_20261019': W5 / 'run_c40_r1w5_20261019',\n    'controller_claude_r1w5_c40': OP / 'controller_claude_r1w5_c40',\n    'r1_w5_c40_operator_notes': OP / 'r1_w5_c40_operator_notes',\n    'r1_w5_c40_reservation_20261019': OP / 'r1_w5_c40_reservation_20261019',\n    'r1w5kit': OP / 'claude_jobkit' / 'r1w5kit',\n    'x5_custody_exam': W5 / 'x5_custody' / 'exam',",
     "    'run_c42_xreal_20261019': XRD / 'run_c42_xreal_20261019',\n    'controller_claude_xreal_c42': OP / 'controller_claude_xreal_c42',\n    'x_real_c42_operator_notes': OP / 'x_real_c42_operator_notes',\n    'x_real_c42_reservation_20261019': OP / 'x_real_c42_reservation_20261019',\n    'xrealkit': OP / 'claude_jobkit' / 'xrealkit',\n    'xr_custody_exam': XRD / 'xr_custody' / 'exam',\n    'xr_custody_work': XRD / 'xr_custody' / 'work',"),
    ("SINGLE = sorted(OP.glob('OWNER_APPROVAL_R1W5_*.json')) + [\n    OP / 'CLAUDE_R1W5_C40_TRANSPORT_LEASE.json', OP / 'CLAUDE_R1W5_C40_SINGLE_LAUNCH_CLAIM.json',\n    W5 / 'R1W5_APPROVAL_RECORD_20261019.md', W5 / 'OWNER_SIGN_LINE_R1W5.txt', W5 / 'OWNER_SIGN_REQUEST_R1W5.md',\n    W5 / 'LAUNCH_BRIEF_R1W5_20261019.md', W5 / 'PREREGISTRATION_R1W5.md', W5 / 'RUN_LIMITS_R1W5.json',\n    W5 / 'HELM_R1_W5_20261019_SOURCE_R1W5.zip', W5 / 'PACKAGE_FREEZE_R1W5.json',\n    W5 / 'x5_custody' / 'X5_SEALED_20261019T192627Z.json', W5 / 'x5_custody' / 'R1W5_APPROVAL_RECORD.json',\n    OP / 'claude_jobkit' / 'claude_r1w5_c40_config.json', OP / 'claude_jobkit' / 'bus_r1w5_c40_slot_notice.json']\nSINGLE += sorted(OP.glob('BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_R1W5_C40_*.json'))",
     "SINGLE = sorted(OP.glob('OWNER_APPROVAL_XREAL_*.json')) + [\n    OP / 'CLAUDE_XREAL_C42_TRANSPORT_LEASE.json', OP / 'CLAUDE_XREAL_C42_SINGLE_LAUNCH_CLAIM.json',\n    XRD / 'APPROVAL_RECORD_XREAL.md', XRD / 'LAUNCH_BRIEF_XREAL_20261019.md', XRD / 'PREREGISTRATION_X_REAL.md',\n    XRD / 'TEST_COUNTS_XREAL.json', XRD / 'ZIP_SHA256.txt',\n    XRD / 'HELM_XREAL_20261019_SOURCE_XREAL.zip', XRD / 'PACKAGE_FREEZE_XREAL.json',\n    XRD / 'xr_custody' / 'XREAL_SEALED_20261019T235639Z.json',\n    OP / 'claude_jobkit' / 'claude_xreal_c42_config.json', OP / 'claude_jobkit' / 'bus_xreal_c42_slot_notice.json',\n    OP / 'claude_jobkit' / 'bus_xreal_c42_release.json']\nSINGLE += sorted(OP.glob('BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_XREAL_C42_*.json'))"),
    ("'job': 'helm-claude-r1w5-20261019-c40'", "'job': 'helm-claude-xreal-20261019-c42'"),
    ("(DEST / 'BACKUP_MANIFEST_R1W5_C40.json')", "(DEST / 'BACKUP_MANIFEST_XREAL_C42.json')"),
])
for stale in ('r1w5', 'R1W5', 'c40', 'W5 ', 'X5'):
    left = [l for l in b.split('"""', 2)[2].splitlines() if stale in l]
    assert not left, (stale, left[:2])
compile(b, 'backup_xreal_c42.py', 'exec')
(HERE / 'backup_xreal_c42.py').write_text(b, encoding='utf-8', newline='\n')
for p in ('closeout_xreal_c42.py', 'backup_xreal_c42.py'):
    print(p, hashlib.sha256((HERE / p).read_bytes()).hexdigest())
