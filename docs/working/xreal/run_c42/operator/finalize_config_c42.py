"""Fill config['previous'] and write the final c42 config.

The controller family's previous-slot gate (aws_control.py, from the run-proven c01 controller) reads a c01-family
independent-cleanup record. The last slot user, c41 (Scribe L4 score, helm-claude-scribe-l4-score-20261019-c41), ran a
different, custom controller (aws_control_c41.py) whose cleanup record has another schema. So:
  - the controller's pinned previous is c40 (helm-claude-r1w5-20261019-c40, the last c01-family controller; independent
    cleanup VERIFIED 3d131b6d; it re-checks c40's instance and volume live before launch, as at every job);
  - c41 is checked HERE, before anything is written: its independent cleanup e6d6cf07 must read VERIFIED (instance
    terminated, its one volume absent, prefix empty, no multipart uploads), its controller cleanup proof VERIFIED, and its
    SLOT RELEASED notice must exist; the facts are recorded in config['previous_slot_user_c41'] and the review summary,
    and the operator re-checks c41's instance and volume live (read-only) just before launch."""
import hashlib
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
from prev_common import OP, previous_block  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


C41 = OP / 'controller_claude_scribe_l4_c41'
c41_ind = C41 / 'aws-c41-a1-independent-cleanup.json'
c41_proof = C41 / 'CLEANUP_PROOF_SCRIBE_L4_C41.json'
c41_release = KIT / 'bus_scribe_l4_c41_release.json'
assert sha(c41_ind) == 'e6d6cf0701d3bb968cab3230af010ac9d72d5b6582c1aa27828c2549d6bdb609'
ind = json.loads(c41_ind.read_bytes())
assert ind['job'] == 'helm-claude-scribe-l4-score-20261019-c41' and ind['status'] == 'VERIFIED' and ind['cleanup_verified'] is True
assert ind['instance_state'] == 'terminated' and ind['volume_observations'] == {ind['all_job_volumes'][0]: 'ABSENT'}
assert ind['prefix_versions_remaining'] == [] and ind['prefix_delete_markers_remaining'] == [] and ind['multipart_uploads_remaining'] == 0
assert ind['prefix'] == 'bridge-control-20260822/helm-pointer-saturation-20261001-v4/'
proof = json.loads(c41_proof.read_bytes())
assert proof['status'] == 'VERIFIED' and proof['job'] == ind['job']
assert 'SLOT RELEASED' in json.loads(c41_release.read_bytes())['subject']

pend = KIT / 'claude_xreal_c42_config.json.pending'
cfg = json.loads(pend.read_text(encoding='utf-8'))
cfg['previous'] = previous_block('controller_claude_r1w5_c40', 'aws-claude-r1w5-c40', 'helm-claude-r1w5-20261019-c40')
cfg['previous_slot_user_c41'] = {
    'job': ind['job'], 'controller': 'custom aws_control_c41.py (not the c01 family)', 'instance': ind['instance'],
    'volumes': ind['all_job_volumes'], 'independent_cleanup_file': str(c41_ind), 'independent_cleanup_sha256': sha(c41_ind),
    'independent_cleanup_utc': ind['utc'], 'cleanup_proof_sha256': sha(c41_proof), 'release_notice_sha256': sha(c41_release),
    'note': 'last user of the shared four-key prefix; VERIFIED; the controller previous-gate pins c40 (last c01-family controller) and re-checks it live; c41 re-checked live read-only by the operator before launch'}
out = KIT / 'claude_xreal_c42_config.json'
with open(out, 'x', encoding='utf-8', newline='\n') as f:
    f.write(json.dumps(cfg, indent=1))
print(json.dumps({'previous': cfg['previous'], 'c41': cfg['previous_slot_user_c41']}, indent=1))
print('config', sha(out))
