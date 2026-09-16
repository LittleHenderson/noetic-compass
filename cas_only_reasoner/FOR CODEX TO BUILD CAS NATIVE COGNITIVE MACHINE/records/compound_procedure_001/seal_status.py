"""Seal successful bounded acceptance and append current canonical progress."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

RECORD = Path(__file__).resolve().parent
ROOT = RECORD.parents[1]
HOME = Path('C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE')
sys.path.insert(0, str(ROOT))
from cncm.compound_profile import load_compound_profile
from cncm.semantic_profile import load_semantic_profile
from cncm.nested_profile import load_nested_profile
from cncm.native_profile import load_native_profile


def read(path):
    return json.loads(path.read_bytes())


def identity(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def save(path, value):
    raw = (value if type(value) is str else json.dumps(value, indent=2) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)


stats = read(RECORD / 'final_validation_summary.json')
assert stats['pytest_exit_code'] == 0 and stats['source_unchanged']
assert all(stats[k] == 0 for k in ('errors', 'failures', 'skipped'))
xml = RECORD / 'final_full_suite_tests.xml'
suite = ET.fromstring(xml.read_bytes()).find('testsuite')
assert int(suite.attrib['tests']) == stats['tests_passed'] + stats['subtests_passed']
assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))
acceptance = RECORD / 'acceptance_001'
receipt_path = acceptance / 'receipt.json'
receipt = read(receipt_path)
assert receipt['status'] == 'BOUNDED_COMPOUND_CONSTRUCTION_ACCEPTANCE_PASSED'
assert receipt['maximum_acquisition_depth'] == 2 and receipt['candidate_count'] == 420 and receipt['unique_survivors'] == 1
assert receipt['producer_pid'] != receipt['fresh_process_pid']
assert receipt['later_source_scalar_omitted'] and receipt['correction_authorized_after_initial_episode']
assert receipt['uncorrected_later_control_output'] == '4' and receipt['corrected_later_output'] == '3'
assert receipt['model_or_provider_work'] is False and receipt['full_goal_complete'] is False
profile = load_compound_profile()
assert profile.profile_digest == receipt['source_profile_digest'] == stats['source_profile_digest'] == read(RECORD / 'source_freeze_final.json')['source_profile_digest']
assert load_semantic_profile().profile_digest == '6a27f94656b45a4c4732d1a185844517f382390d6e3d1ce4259b63861badcecf'
assert load_nested_profile().profile_digest == '49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38'
assert load_native_profile().profile_digest == 'c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607'
for row in receipt['files']:
    found = identity(acceptance / row['path'])
    assert (found['bytes'], found['sha256']) == (row['bytes'], row['sha256'])
assert identity(ROOT / 'tools/reproduce_compound_construction.py')['sha256'] == receipt['reproducer_sha256']
golden = read(RECORD / 'golden_verification.json')
assert golden['valid'] and golden['fixture_count'] == 14
tests = f"{stats['tests_passed']} tests plus {stats['subtests_passed']} subtests"

report = f'''# Native compound construction 0.5 checkpoint

Status: BOUNDED_COMPOUND_CONSTRUCTION_ACCEPTANCE_PASSED.
The full CNCM vision remains open. This is deterministic construction in one
finite grammar over exact rational arithmetic, not general or neural learning.

## What now executes

The task supplies a*(b*x+c)+d=e through five literals or scoped memory references.
It supplies no answer, execution graph, ready program or resolver. An absent
compound procedure suspends its caller; a missing primitive opens a second
acquisition frame. The kernel selects and qualifies that primitive, returns to
construction, tests 420 call structures on four public development cases and
finds one survivor: primitive(a,d,e), then primitive(b,c,r0).

Separate qualification uses eight positive and four invalid-domain cases. The
governed installation retains the exact program and primitive pin. The original
caller resumes with its remaining budget. Each actual output is independently
substituted into the original expression before ordinary reasoning, comparison
and commitment gates can conclude. The checker does not solve for x.

All work shares one episode budget. Full literal acquisition reserves 40,852
instruction units and 1,728 checker calls; the retained sourced episode also
stores and recalls a fixture claim, reserving 40,876/1,730. A later literal task
reserves 40/2; a memory-reference task reserves 52/3. These are policy units,
not CPU measurements, physical energy or money. Failed expensive checks retain
their allocations; malformed envelopes cannot initiate expensive work.

## Actual retained acceptance

The initial engineering source records c=5. The machine solves
2*(3*x+5)+7=35 as 3 through depth 2 acquisition. After that episode, trusted-host
ingress admits an identified TEST_FIXTURE correction c=8, giving 2 for the same
equation. The source label remains TEST_FIXTURE, not verified world truth.

Fresh process PID {receipt['fresh_process_pid']} (producer PID {receipt['producer_pid']})
replays and resumes all {receipt['fresh_process_cuts']} retained cuts:
{receipt['primary_cut_count']} acquisition/correction cuts and
{receipt['failure_cut_count']} budget/depth/search/domain/acquisition-disabled cuts.
Complete journals, exact frames, returns, results and remaining budgets agree.

After replay, all four acquisition/qualification aliases are patched to raise.
Actual new calls reuse the pinned program: signed parameters return 6/5 and
fractional parameters return -19/18. A later task omits the recalled scalar and
returns 3; its otherwise matched uncorrected control returns 4, both spending 52/3.
Current-call checking stays enabled. Parent recovery also replays the child's
retained final journals using external genesis, source chronology and anchors.

Independent rollback branches remove either the compound head or its primitive
authorization. Both prevent subsequent dispatch with acquisition disabled while
preserving old artifacts, memory and evidence. Zero leading factors, insufficient
budget, depth limit and incomplete construction prefixes refuse explicitly;
SEARCH_EXHAUSTED does not establish mathematical impossibility.

## Verification and preserved failures

The final full suite passed **{tests}**, with zero failures/errors/skips.
All 14 original fixtures reproduce, including the contract-only mathematics case
whose status remains contract-only. Prior 0.2/0.3/0.4 source profiles are unchanged.
Tests cover generated rational cases, both rollbacks, all-cut process recovery,
typed schemas, stale/duplicate/malformed proposals, exact saved caller/branch,
source correction chronology, wrong return IDs, overflow and rejected outputs.

Independent adversarial review found two real gaps before final acceptance.
A qualified supplied artifact could skip its required acquisition record; now
installation also requires matching current-episode selection/construction.
A valid receipt for different inputs could be accepted by the receiver; now
sealed reports bind exact current inputs, caller, branch, program, primitive and
nested executor/checker results. Memory and construction receipts receive their
own exact context checks. Ten adversarial regressions pass with failure charges
retained and no unauthorized installation, answer or commitment.

Earlier failed XML files and source_freeze_001.json are preserved. They include
the initial qualifier-status mismatch, a test assertion about branch Python
class rather than canonical wire identity, the receipt-binding findings, and a
temporary indentation error while applying the lineage fix. full_suite_001.xml
is preliminary and overlaps source changes; it is not the final acceptance.
Only the final XML, final source freeze and acceptance_001 below identify this
checkpoint. Hashes bind code and records; they are not principal authentication.

## Exact evidence identities

- Runtime profile ({len(profile.source_files)} files): `{profile.profile_digest}`
- Acceptance receipt SHA256: `{identity(receipt_path)['sha256']}`
- Final full-suite XML SHA256: `{identity(xml)['sha256']}`
- Program digest: `{receipt['constructed_program_digest']}`
- Pinned primitive: `{receipt['pinned_primitive_sha256']}`
- Final reuse journal: `{receipt['reuse_journal_digest']}`
- Reproducer SHA256: `{receipt['reproducer_sha256']}`

acceptance_001/receipt.json binds {len(receipt['files'])} retained artifact files.
Reproduce with python -B tools/reproduce_compound_construction.py --output
records/compound_procedure_001/NEW_RUN. Use a new directory; evidence is never
overwritten. No model/provider imports, paid compute or AWS launch were needed.

## CAS-RPA fit and remaining charter work

The user-supplied atlas and overview were re-read and their identities confirmed.
The existing receipt-bound native 0.2 RPA prototype and mathematical review remain
unchanged. docs/CAS_RPA_COMPOUND_EXTENSION_v0.1.md specifies a new compound
adapter, trusted replay boundary, bounded report pages and equal-record graph/
flower comparison. That extension is design only; the current viewer does not
yet display 0.5 journals. The note records the two-input limit on the atlas's
XOR/exactly-one and XNOR/equality wording. No geometric benefit is inferred.

This advances bounded V03/V05/V06/V08/V10/V15 and systems7/8/9/18/20/31.
No full requirement is complete. The finite grammar has at most two primitive
calls and one affine family. Public engineering panels are not a protected
held-out learning examination. General construction, language, neural assembly,
independently proved semantic memory, verifier federation, CMB-R1, full
Foundations, adaptive flow, tools, Foundry and governed evolution remain open.
The full V01-V18, 31-system and integrated 20-step destination remains open;
previous negative experiments are preserved and no performance advantage is claimed.
'''

addition = f'''
## 2026-09-16 bounded native compound procedure construction

Runtime 0.5 constructs a reusable one/two-call program for a*(b*x+c)+d=e.
The task supplies five typed inputs and a query, without an answer or execution
graph. A real compound acquisition frame may suspend again for its primitive;
both return to the exact caller with conserved instruction/checker budget.
All 420 canonical call structures are checked on four public development cases.
One survivor receives separate 12-case qualification and governed installation.
Each actual invocation is independently checked against the original expression.

Final source profile: {profile.profile_digest}.
Evidence: records/compound_procedure_001/STATUS.md and acceptance_001/receipt.json
in vision-next. Full suite: {tests}; all 14 original fixtures reproduce.
Earlier native 0.2/nested 0.3/semantic 0.4 source profiles remain unchanged.
Fresh-process recovery resumes {receipt['fresh_process_cuts']} exact journal cuts.
New signed/fractional inputs reuse the installed structure with acquisition and
qualification disabled. A later source correction changes a matched task from
control 4 to 3 while preserving TEST_FIXTURE status and omitting the source scalar
from the new request. Both compound and primitive rollback block future dispatch.

Adversarial review repaired installation that could skip acquisition lineage
and receipt handling that could accept a check for different inputs. Regressions
preserve failure charges and prohibit unauthorized heads, outputs and commitment.
The new CAS-RPA compound extension document maps these records and specifies
the next read-only adapter; the existing viewer remains native 0.2 only. Both
supplied PDFs and all old RPA receipt-bound sources remain unchanged.

This advances bounded V03/V05/V06/V08/V10/V15 and systems7/8/9/18/20/31; none is
complete. Finite public-panel construction does not prove general or neural
learning, protected held-out transfer or independently verified source facts.
General procedure structures, semantic proof, CMB-R1, language, Foundations,
flow, tools, Foundry, evolution and the full V01-V18/31-system/integrated 20-step
vision retain open gates. No paid model/provider work or AWS launch was used.
'''
paths = [
    (HOME / 'docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md', '9f8db4a3127b498c5f0a2f3c5f7ed9fb825e97cb0d0cf4d41f009a729bdf0a37'),
    (ROOT / 'docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md', '9f8db4a3127b498c5f0a2f3c5f7ed9fb825e97cb0d0cf4d41f009a729bdf0a37'),
    (ROOT / 'research/CAS_META_2_COMPOSITION/VISION_REQUIREMENTS.md', 'f60ed906a42018805a4c175709c218b4154cdda1f782e5c18ed04246657eaef8'),
]
before = [p.read_bytes() for p, _ in paths]
assert all(sha256(raw).hexdigest() == expected for raw, (_, expected) in zip(before, paths))
save(RECORD / 'STATUS.md', report)
rows = []
for raw, (path, expected) in zip(before, paths):
    path.write_bytes(raw + addition.encode())
    rows.append({'path': str(path), 'before_sha256': expected, 'after_sha256': identity(path)['sha256'],
                 'original_bytes_preserved': path.read_bytes().startswith(raw), 'full_goal_complete': False})
save(RECORD / 'ledger_update.json', {'ledgers': rows, 'acceptance_receipt': identity(receipt_path),
    'full_suite': identity(xml), 'source_profile_digest': profile.profile_digest,
    'acceptance_files_verified': len(receipt['files'])})
print(json.dumps({'tests': tests, 'source_profile_digest': profile.profile_digest,
    'receipt_sha256': identity(receipt_path)['sha256'], 'ledgers_updated': len(rows)}))
