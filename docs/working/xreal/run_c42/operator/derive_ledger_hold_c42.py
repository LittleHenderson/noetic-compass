"""Derive ledger_hold_xreal_c42.py from r1_w5_c40_operator_notes/ledger_hold_r1w5_c40.py by exact substitution."""
import hashlib
from pathlib import Path

OP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')
src = (OP / 'r1_w5_c40_operator_notes' / 'ledger_hold_r1w5_c40.py').read_text(encoding='utf-8')
appr_sha = hashlib.sha256(Path(r'C:\Users\wakil\Documents\Codex\2026-10-19\x_real\APPROVAL_RECORD_XREAL.md').read_bytes()).hexdigest()
head_end = src.index('import datetime')
src = ('"""Place a SOURCE_BOUND_SINGLE_ATTEMPT_RESERVATION of 1.00 USD for job helm-claude-xreal-20261019-c42, bound to the\n'
       'sealed X-REAL zip (a9b4c954). Authority: the owner\'s pre-approval line (APPROVAL_RECORD_XREAL.md; line sha256 2a8a6f86,\n'
       '121 bytes, "...X-REAL at 1 USD...") under the owner\'s 200 USD ceiling ruling. Derived from ledger_hold_r1w5_c40.py by\n'
       'substitution (derive_ledger_hold_c42.py). Placed only when the last HISTORY line is the c41 (Scribe L4) closeout; the\n'
       'before value is read from the pointer at that moment (sha-checked twice). No other hold touched; ceiling unchanged.\n'
       'Read-modify-write with checks; atomic writes; one history line.\n\n'
       'Usage: python -B ledger_hold_xreal_c42.py <expected pointer sha256 as just read by the operator>"""\n') + src[head_end:]
pairs = [
    ('W5 = CODEX / "2026-10-19" / "r1_wave5"\nAPPROVAL = W5 / "R1W5_APPROVAL_RECORD_20261019.md"\n'
     'APPROVAL_SHA = "7c8589eefc9b1b50c23cc44da5ee52aae4b548403d922d270fc699aaca0df735"\n'
     'OPERATOR_RECORD = PREP / "OWNER_APPROVAL_R1W5_20261019T193227Z.json"\n'
     'OPERATOR_RECORD_SHA = "231dbef2046b70f4406660783c258ecb583fc73a76cda12621846f4b0ef3c63c"',
     'XR = CODEX / "2026-10-19" / "x_real"\nAPPROVAL = XR / "APPROVAL_RECORD_XREAL.md"\n'
     'APPROVAL_SHA = "' + appr_sha + '"\n'
     'OPERATOR_RECORD = PREP / "OWNER_APPROVAL_XREAL_20261020T000138Z.json"\n'
     'OPERATOR_RECORD_SHA = "6b4799b22750ca1c0c3050588f2364a66fc743c9ba0cd2245e9dc627399c4d6e"'),
    ('ZIP = W5 / "HELM_R1_W5_20261019_SOURCE_R1W5.zip"\nZIP_SHA = "b6598687190bc9e41f52695144eeeac5428913ab804f8bec64841093ea825d6c"\n'
     'FREEZE_SHA = "a325ea13b8851f9d8ed928dd73c2c3892315fa534fc876a146c6eb975bdc0334"\nJOB = "helm-claude-r1w5-20261019-c40"\n'
     'PARALLEL_JOB = "helm-claude-r1w4-20261019-c39"',
     'ZIP = XR / "HELM_XREAL_20261019_SOURCE_XREAL.zip"\nZIP_SHA = "a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249"\n'
     'FREEZE_SHA = "67b485415078ca11c5c3d984cd3f82a6a1ab1f111efc9ce2a619d3c136c8006d"\nJOB = "helm-claude-xreal-20261019-c42"\n'
     'PARALLEL_JOB = "helm-claude-scribe-l4-score-20261019-c41"'),
    ('OPERATOR = "claude-code-subagent-launch-operator-c40-20261019"\nLINE_SHA = "a9dd6ff2ecce4fa7943837559af3d1ee30afc40a84bb51c3ba24484b626aac83"',
     'OPERATOR = "claude-code-subagent-launch-operator-c42-20261019"\nLINE_SHA = "2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00"'),
    ("assert JOB not in history and '-c40\"' not in history and \"-c40-\" not in history and \"-c40a\" not in history, \"c40 already used\"",
     "assert JOB not in history and '-c42\"' not in history and \"-c42-\" not in history and \"-c42a\" not in history and \"-c42#\" not in history, \"c42 already used\""),
    ('("PARALLEL_C39_NOT_CLOSED_OUT_YET", last.get("job"), last.get("action"))', '("C41_NOT_CLOSED_OUT_YET", last.get("job"), last.get("action"))'),
    ('rdir = PREP / "r1_w5_c40_reservation_20261019"', 'rdir = PREP / "x_real_c42_reservation_20261019"'),
    ('rpath = rdir / "BUDGET_RESERVATION_R1_W5_C40.json"', 'rpath = rdir / "BUDGET_RESERVATION_XREAL_C42.json"'),
    ('"controller not built yet (X5 sealed 2026-10-19T19:25:11Z); the controller is bound at launch time"',
     '"controller not built yet (X-REAL exam sealed 2026-10-19T23:56:39Z by the separate custodian); the controller is bound at launch time"'),
    ("\"owner sign line 'APPROVE R1W5: EYE_PAIRING wave, sealed package b6598687, one attempt + one plumbing retry, cap $1.00.' (sha256 a9dd6ff2; recorded 2026-10-19T19:21:08Z) under the owner's 200 USD ceiling ruling; the 1.00 USD is the TOTAL cap and covers the scored attempt and at most one plumbing retry (no torch on this wave); the launch brief orders the coordinator to place this hold before launch\"",
     "\"owner pre-approval line 'I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.' (sha256 2a8a6f86, 121 bytes) bound to package a9b4c954 by APPROVAL_RECORD_XREAL.md, under the owner's 200 USD ceiling ruling; this hold covers ONLY the X-REAL line (1.00 USD TOTAL cap: the scored attempt and at most one plumbing retry; no torch); the 8 USD transformer line is not touched here; the launch brief orders the coordinator to place this hold before launch\""),
    ("\"wave 4 (helm-claude-r1w4-20261019-c39) ran in parallel on its own instance; this hold is a separate line placed after c39's closeout line, so neither job's hold is double-counted or released by the other\"",
     "\"the previous ledger line is the c41 (Scribe L4) closeout; this hold is a separate line placed after it, so no hold is double-counted or released by another job\""),
    ('"reservation_id": f"r1w5-c40-{uuid.uuid4().hex}"', '"reservation_id": f"xreal-c42-{uuid.uuid4().hex}"'),
    ('"client_token": f"r1w5-c40-{uuid.uuid4().hex}"', '"client_token": f"xreal-c42-{uuid.uuid4().hex}"'),
    ('of HELM_R1_W5_20261019 (zip sha256 b6598687..., freeze a325ea13...)', 'of HELM_XREAL_20261019 (zip sha256 a9b4c954..., freeze 67b48541...)'),
    ('"NOT_LAUNCHED; owner approval given; X5 sealed (pins 77313c43)"', '"NOT_LAUNCHED; owner pre-approval given; X-REAL exam sealed (manifest 1e535511, pins 4cb97a82)"'),
    ('PREP / "r1_w5_c40_operator_notes" / "LEDGER_HOLD_RESULT_R1_W5_C40.json"', 'PREP / "x_real_c42_operator_notes" / "LEDGER_HOLD_RESULT_XREAL_C42.json"'),
]
for old, new in pairs:
    assert src.count(old) == 1, (old[:100], src.count(old))
    src = src.replace(old, new)
for stale in ('R1W5', 'r1w5', 'c40', 'b6598687', 'a9dd6ff2', 'X5', 'c39', 'W5'):
    left = [l for l in src.split('"""', 2)[2].splitlines() if stale in l]
    assert not left, (stale, left[:2])
compile(src, 'ledger_hold_xreal_c42.py', 'exec')
(OP / 'x_real_c42_operator_notes' / 'ledger_hold_xreal_c42.py').write_text(src, encoding='utf-8', newline='\n')
print('ledger_hold_xreal_c42.py', hashlib.sha256((OP / 'x_real_c42_operator_notes' / 'ledger_hold_xreal_c42.py').read_bytes()).hexdigest())
