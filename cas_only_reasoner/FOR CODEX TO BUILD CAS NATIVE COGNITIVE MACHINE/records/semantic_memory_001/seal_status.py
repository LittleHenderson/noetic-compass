"""Seal checked status and append-only canonical progress after final validation."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
HOME=Path('C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE')
RECORD=Path(__file__).parent
sys.path.insert(0,str(ROOT))
from cncm.semantic_profile import load_semantic_profile
from cncm.nested_profile import load_nested_profile
from cncm.native_profile import load_native_profile


def identity(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(value if type(value) is str else json.dumps(value,indent=2)+'\n')


stats=json.loads((RECORD/'final_validation_summary.json').read_bytes())
tests=RECORD/'final_full_suite_tests.xml'
suite=ET.fromstring(tests.read_bytes()).find('testsuite')
assert suite is not None and int(suite.attrib['tests'])==stats['tests_passed']+stats['subtests_passed']
assert all(int(suite.attrib[k])==0 for k in ('errors','failures','skipped'))
receipt_path=RECORD/'acceptance_002/receipt.json'
receipt=json.loads(receipt_path.read_bytes())
assert receipt['status']=='BOUNDED_SOURCED_CORRECTION_EPISODE_PASSED'
assert receipt['fresh_process_cuts']==35 and receipt['correction_authorized_after_initial_episode']
assert receipt['later_input_omits_value'] and receipt['corrected_later_output']=='9'
profile=load_semantic_profile()
assert profile.profile_digest==receipt['source_profile_digest']==json.loads((RECORD/'source_freeze_final.json').read_bytes())['source_profile_digest']
assert load_nested_profile().profile_digest=='49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38'
assert load_native_profile().profile_digest=='c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607'
for row in receipt['files']:
    p=receipt_path.parent/row['path'];actual=identity(p)
    assert actual['bytes']==row['bytes'] and actual['sha256']==row['sha256'],str(p)
golden=json.loads((RECORD/'golden_verification.json').read_bytes())
assert golden['valid'] and golden['fixture_count']==14
test_text=f"{stats['tests_passed']} tests plus {stats['subtests_passed']} subtests"
report=f'''# Native sourced correction memory0.4 checkpoint

Status: BOUNDED_SOURCED_CORRECTION_EPISODE_PASSED. The complete CNCM vision is open.
This record covers exact rational input memory and conditional nested arithmetic,
not independently verified world facts, general language learning or CMB-R1.

## What now executes

The actual transaction coordinator admits scoped source statements, checks
supersession against each source's exact head, recalls current compatible claims,
and independently checks their substitution into the original equation templates.
Statements, bindings, receipts and input identity are part of runtime0.4 state.
All memory and procedure work spends the same conservative instruction/checker
budget. No local neural, provider model, or new paid compute work was used.

A later correction can be authorized after the first task has ended. The host
appends exact source digests at a quiescent episode boundary. Recovery requires
the external initial set and ordered extension schedule; a journal cannot grant
itself source authority. This is trusted host/custody, not cryptographic proof of
the source identity or a human attestation. Earlier claims remain immutable.

USER_ATTESTED and TEST_FIXTURE remain distinct source labels. Neither satisfies
INDEPENDENTLY_VERIFIED. Checked arithmetic stays conditional on those premises.
Missing, retracted, conflicting or insufficiently verified claims refuse before
arithmetic. Retraction leaves a tombstone; another active source may still support
a reference, with retractions retained in the receipt. Exact scope prevents
unrelated facts from being reused silently.

## Retained engineering demonstration

The initial task recalls fee5 and solves 3*x+fee=26 as7. After that episode,
the host authorizes an identified engineering correction fee8; a governed update
preserves fee5 and makes the same equation return6. These are TEST_FIXTURE claims,
not invented real user statements or externally protected learning examples.

A separate Python process recovers the corrected chain and solves a fresh task
3*x+fee=35 as9. Its task packet contains only the memory reference and omits the
fee value. An uncorrected control returns10. New-call selection and qualification
are patched to raise after recovery, proving installed procedure reuse. A new
two-level equation structure returns-5; another scope still returns8. Procedure
rollback removes dispatch, preserves semantic memory and yields NEEDS_CAPABILITY.

All35 cuts across the initial and correction episodes replay and resume to the
identical complete journals. Fresh-process PID{receipt['fresh_process_pid']} differs
from producer PID{receipt['producer_pid']}. The later simple task allocates58
instructions/4 checks including recall, resolution and current arithmetic.
These are policy units, not measured CPU, energy, runtime or money.

## Verification and retained failures

- Full homebase suite: **{test_text} passed**, zero failures/errors/skips.
- All14 original reference fixtures reproduce, including the one contract-only
  mathematics fixture, which is not reclassified as executed.
- Source/profile, exact correction chronology, stale/replayed/foreign source,
  conflicting/revoked claims, evidence thresholds, wrong references, internally
  consistent false receipts, corrupted numeric substitution, disabled/stale/
  duplicate proposals, exhausted budgets, suspended-parent isolation, large
  exact values, forged/rehashed histories and actual-process recovery are covered.
- Six closed schemas validate original/refined problems, state, journal, source
  profile, accepted transitions and domain-specific common verifier receipts.
  Shape validation alone grants no truth or execution authority.

Initial artifacts are retained: kernel_tests_001.xml reports setup attempted
before the new recovery file existed; kernel_tests_002.xml found a test-control
patch affecting an independent baseline and was corrected. Adversarial scope
fault injection found a real bad-reference path that could retry and crash;
the kernel now requires the requested reference, binding body and receipt to
agree before writing. The regression checks one charged refusal with no bad
memory write. Preliminary acceptance_001 is preserved under its own source
profile. Final acceptance_002 below is the authoritative checkpoint.

## Exact evidence identities

- Runtime0.4 source profile ({len(profile.source_files)} files):
  `{profile.profile_digest}`
- Final acceptance receipt SHA256: `{identity(receipt_path)['sha256']}`
- Full-suite XML SHA256: `{identity(tests)['sha256']}`
- Correction journal: `{receipt['correction_journal_digest']}`
- Final six-episode journal: `{receipt['final_journal_digest']}`
- Reproducer SHA256: `{receipt['reproducer_sha256']}`
- Old nested0.3 profile unchanged:
  `49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38`
- Old native0.2 profile unchanged:
  `c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607`

See acceptance_002/receipt.json for every retained artifact byte count/hash and
seven saved refusal histories. Reproduce with Python-B and
tools/reproduce_semantic_memory.py --output records/semantic_memory_001/NEW_RUN.
Use a new output directory; the reproducer refuses to overwrite evidence.

## Remaining charter work

This advances bounded portions of V05/V06/V10/V16 and systems10/14/18/31, and
fixture-level steps18-19. No whole requirement is complete. Common receipts
cover three memory obligations, not the entire verifier federation. The current
solver still selects among twelve authored atomic programs; it does not learn
new procedure topology or provide general semantic/structural retrieval.

Independently proved semantic knowledge, CMB-R1 reconstruction/lacunarity,
broader checked program construction, verified learning/evolution, full
Foundations, language, live tools, flow, Foundry and every remaining V01-V18,
31-system and integrated20-step requirement remain open. Previous negative
experiments remain unchanged. No broader capability grade or performance
advantage is claimed.
'''
save(RECORD/'STATUS.md',report)
addition=f'''
## 2026-09-16 native sourced correction memory and later-task reuse

Runtime0.4 now stores scoped source assertions/corrections/retractions through
the actual transaction coordinator. Each source has an exact supersession head;
history remains immutable. Recall binds current compatible source digests and
statuses. An independent checker reconstructs every recalled scalar in the
reachable original equation graph before any nested execution. Memory and
procedure work share one conserved episode budget.

A new correction may arrive after the first episode: the trusted host appends
its authorized digest at a quiescent boundary. Fresh-process recovery requires
the initial source set and exact external extension chronology. Journal data
cannot authorize itself. Source custody remains a trusted-host boundary, not
cryptographic principal authentication or proof of world facts.

The retained TEST_FIXTURE episode stores fee5, accepts a later correction fee8,
and changes a new task's answer from control10 to9 without resupplying the fee.
All35 pause points replay/resume exactly in a separate process. A new nested
structure returns-5, a neighboring scope still returns8, and procedure rollback
preserves semantic memory while removing future dispatch. New-call procedure
selection and qualification are disabled for the reuse demonstrations.

Final source profile:
{profile.profile_digest}.
Evidence: records/semantic_memory_001/STATUS.md and acceptance_002/receipt.json
in vision-next. The full suite passed{test_text}; all14 original fixtures
reproduce and both earlier native source profiles remain byte-identical.
Missing, retracted, conflicting, insufficiently verified and unauthorized data,
wrong references, false bindings, failed-check cost, budget exhaustion, scoped
retention, ingress chronology and rehashed false histories have direct coverage.

This advances bounded V05/V06/V10/V16, systems10/14/18/31 and fixture-level
steps18-19, without completing them. USER_ATTESTED and TEST_FIXTURE are never
promoted to independently verified fact by an arithmetic receipt. Three common
memory verifier obligations are implemented; full verifier federation and
CMB-R1 remain open. These engineering variants are not a protected held-out
learning study or proof of improved reasoning/general learning.

The next substantive gap is wider checked program construction beyond the
twelve authored atomic forms, alongside independently proved semantic facts
and all remaining language/flow/tool/Foundry/learning requirements. The full
V01-V18,31-system,integrated20-step vision remains open. No new paid model or
provider work was used; prior negative experiments remain intact.
'''
paths=[(HOME/'docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md','b1c4bf07b2a23cc66b453c6c33ba74f900de36d22beb29819c12615718ed44f6'),
       (ROOT/'docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md','b1c4bf07b2a23cc66b453c6c33ba74f900de36d22beb29819c12615718ed44f6'),
       (ROOT/'research/CAS_META_2_COMPOSITION/VISION_REQUIREMENTS.md','33b3f0987dba4e931a3a119346709cd47c3a3886212758322da96602ebfc1a91')]
before=[p.read_bytes() for p,_ in paths]
assert all(sha256(raw).hexdigest()==expected for raw,(_,expected) in zip(before,paths))
rows=[]
for raw,(path,expected) in zip(before,paths):
    path.write_bytes(raw+addition.encode())
    rows.append({'path':str(path),'before_sha256':expected,'after_sha256':sha256(path.read_bytes()).hexdigest(),
                 'original_bytes_preserved':path.read_bytes().startswith(raw),'full_goal_complete':False})
save(RECORD/'ledger_update.json',{'ledgers':rows,'acceptance_receipt':identity(receipt_path),
    'full_suite':identity(tests),'source_profile_digest':profile.profile_digest,
    'acceptance_files_verified':len(receipt['files'])})
print(json.dumps({'source_profile_digest':profile.profile_digest,'test_results':test_text,
                  'ledgers_updated':len(rows),'receipt_sha256':identity(receipt_path)['sha256']}))
