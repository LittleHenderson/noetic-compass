"""Assemble the 33 audit verdicts from retained independent checks."""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent/'audit_package_20260922'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    verdicts = {}
    for name in ('ohm/CLAIM_VERDICTS.json', 'merge/claim_verdicts.json'):
        for row in read(HERE/name)['claims']:
            verdicts[row['id']] = {k: row[k] for k in ('auditor_verdict','auditor_observed')}
            verdicts[row['id']]['evidence'] = name
    book = read(HERE/'book/book_probe.json')['claim_checks']
    summaries = {
        'BOOK-1': 'All eight canon files match main eb3c9b1e and all sixteen expected LF hashes; no book changes since d50abbbc.',
        'BOOK-2': '8 files,202 insertions,95 deletions. Original noisy commit1765/1658.39 top-level Markdown files; recursive Git pathspec includes one build Markdown file.',
        'BOOK-3': 'Original text calls XOR both-active; independent truth table gives XOR(true,true)=false and AND(true,true)=true. Correction is justified.',
        'BOOK-4': 'At dbb388ee Chapter10:278 already uses gate; Chapter14:80 and326 also use gate. Self-correction reproduces.',
        'BOOK-5': 'At dbb388ee Chapter10:278 uses gate; AppendixE:327 uses xor. Corrected canon uses gate conflict:AND in both.',
        'BOOK-6': 'Final text is corrected, but the intermediate owner-edited pre-fix copy and exclusive authorship are not independently retained.',
        'BOOK-7': '58 circuit/board blocks,42 distinct names at both pre-edit and canon pins, using the published anchored regex.',
        'BOOK-8': 'Both disclosed CJT/op-amp sentences remain at Chapter10:322 and AppendixB:65, despite changed headings.',
        'GOV-3': 'OD9/10 agent-written artifacts exist; actual owner chat authenticity is not independently available. Prior refusal exists at CODEX_CONTINUATION_20260921.md:53-55, not the named verification file.',
    }
    for key, observed in summaries.items():
        verdicts[key] = {'auditor_verdict': book[key]['verdict'], 'auditor_observed': observed,
                         'evidence': 'book/book_probe.json#/claim_checks/'+key}
    compiler = ET.parse(HERE/'compiler_tests.xml').getroot().find('testsuite')
    lab = ET.parse(HERE/'lab_tests.xml').getroot().find('testsuite')
    assert compiler.attrib['tests'] == '639' and compiler.attrib['failures'] == compiler.attrib['errors'] == '0'
    assert lab.attrib['tests'] == '348' and lab.attrib['failures'] == lab.attrib['errors'] == '0'
    groups = Counter(case.attrib['classname'] for case in compiler.findall('testcase'))
    assert groups['tests.test_notation_compiler'] == 99
    assert groups['tests.test_offline_help_text_canon'] == 454
    own = {
        'TEST-1': ('REPRODUCES', '458 is the historical merged-suite count before restoration: current639 minus restored181. At frozen626 the prescribed current-tree command actually yields639; see stale-instruction finding. Historical comparison and function inventory are retained.', 'compiler_tests.xml; merge/merge_results.json'),
        'TEST-2': ('REPRODUCES', 'Final exact nine-file lab command:348 passed,0 failures,0 errors. Earlier six failures were missing-schema sparse-checkout setup errors, corrected without source edits and retained separately.', 'lab_tests.xml'),
        'TEST-3': ('REPRODUCES', 'Original test_notation_compiler.py bytes are identical from c3855275 to626; current XML contains99 cases from that file.', 'package_results.json; compiler_tests.xml'),
        'TEST-4': ('REPRODUCES', 'Historical merged help file:6 functions,273 cases,including270 parameter rows. Current restored file:9 functions,454 cases; current fullsuite639. Current checkout must contain allthree help sources to reproduce counts.', 'merge/merge_results.json; compiler_tests.xml'),
        'TEST-5': ('REPRODUCES', 'Frozen626 current five-file compiler command:639 passed,0 failures,0 errors;454 are help/canon cases. One unknown asyncio_mode config warning under disabled plugins.', 'compiler_tests.xml'),
        'GOV-1': ('UNVERIFIABLE', 'No new neural-run evidence was found in the reviewed changes; the recorded checks are symbolic. Local source/artifact absence cannot prove that no historical inference, provider action or spending occurred. This audit itself ran no model/cloud workload.', 'package_results.json; audit scope in REPORT.md'),
        'GOV-2': ('UNVERIFIABLE', 'Main repo currently at eb3c9b1e on codex/casformer-v0.2-release;3 commits not in local remote refs; upstream missing. Fresh ls-remote returns no branch of that name. These observations reproduce the local state, not a historical never-pushed guarantee.', 'package_results.json#/main_repository_observations'),
    }
    for key,(verdict,observed,evidence) in own.items():
        verdicts[key] = {'auditor_verdict':verdict,'auditor_observed':observed,'evidence':evidence}
    claims = read(PACKAGE/'01_CLAIMS_TO_CHECK.json')['claims']
    assert set(verdicts) == {row['id'] for row in claims}
    output = {'schema':'cas.peer-audit.claim-verdicts/1.0',
              'source_commit':'626cc84b574e60217a103b72d2f09388d7aa5e34',
              'verdict_meaning':'REPRODUCES is limited to the stated revision and observed cases. Historical results are not silently promoted to current HEAD; UNVERIFIABLE does not mean false.',
              'counts':dict(Counter(row['auditor_verdict'] for row in verdicts.values())),
              'compiler_case_counts':dict(groups),
              'claims':[{'id':row['id'],'original_claim':row['claim'],**verdicts[row['id']]} for row in claims]}
    (HERE/'CLAIM_VERDICTS.json').write_text(json.dumps(output,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    print(json.dumps({'claims':len(claims),'counts':output['counts'],'compiler_cases':639,'lab_cases':348}))


if __name__ == '__main__':
    main()
