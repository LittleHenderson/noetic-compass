"""Make the version 2.2 tools from the frozen version 2.1 tools. Plain Python. Every change is an exact replacement with a
checked count, so a moved anchor stops the build and the v2.1 files are never touched.

What changes, and nothing else:
  all five tools     names: *_v21 -> *_v22, guide/plan/instructions file names, schema names, "version 2.1" -> "version 2.2",
                     "attempt 2" -> "attempt 3"
  writer             40 + 10 new settings; the 50 settings of attempt 2 join EARLIER; new seeds; new job-list fingerprints;
                     the request ledger stays the shared one in label_v21 (one Gemini key, one daily count)
  seal               new seeds; output folders; every earlier passage set is compared for exact repeats, and a missing one is refused; it also fingerprints the owner's answers and team A's wrapper
  scorer             new names and schemas only; it imports the unchanged checker check_labels_v21.py; the measure is unchanged
  team A, team B     default guide, instructions and checker
The checker check_labels_v21.py and the fixture label_v21/fixture are used unchanged."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / 'tools'

COMMON = [
    ('write_passages_v21', 'write_passages_v22'),   # the checker stays check_labels_v21.py, unchanged
    ('team_a_receipt_v21', 'team_a_receipt_v22'), ('label_outside_v21', 'label_outside_v22'), ('seal_v21', 'seal_v22'),
    ('verdict_v21', 'verdict_v22'), ('label-agreement-v21-', 'label-agreement-v22-'),
    ('02_LABELING_GUIDE_v2_1.md', '02_LABELING_GUIDE_v2_2.md'), ('09_LABEL_AGREEMENT_PLAN_v2_1.md', '09_LABEL_AGREEMENT_PLAN_v2_2.md'),
    ('label_v21/LABELER_INSTRUCTIONS.txt', 'label_v22/LABELER_INSTRUCTIONS.txt'),
    ('version 2.1', 'version 2.2'), ('VERSION 2.1', 'VERSION 2.2'), ('guide v2.1', 'guide v2.2'), ('attempt 2', 'attempt 3'),
]

VERDICT_SETTINGS = [
    'a sweet shop', "a florist's shop", 'a fish smokehouse', "a hairdresser's salon", 'a wedding reception', 'a car boot sale',
    'a cricket pavilion', 'a football stadium', 'a canoe club', "a greengrocer's shop", 'a delicatessen', 'a pizza takeaway',
    'a petting zoo', "a builder's merchant", 'a timber yard', 'a cattery', 'a gymnasium', 'a music shop', 'a charity shop',
    'a church organ loft', 'a coastguard lookout', 'a beach café', 'a caravan park', 'a stationery shop', 'an observatory',
    'a nursing home', 'an exam hall', 'an art gallery', 'a cathedral', 'a pig farm', 'a bridal shop', 'an antique shop',
    'a sheep shearing shed', 'a lido', 'a bandstand', 'a holiday cottage', 'a bingo hall', 'a bird hide', 'a falconry display',
    'a ploughing match']
PRACTICE_SETTINGS = ['a rugby clubhouse', 'a fish and chip shop', 'a yoga class', 'a record shop', 'a jumble sale', 'a bell tower',
                     'a beach hut', 'a cable car', 'a sculpture park', 'a wool shop']
assert len(VERDICT_SETTINGS) == 40 and len(PRACTICE_SETTINGS) == 10 and len(set(VERDICT_SETTINGS + PRACTICE_SETTINGS)) == 50


def make(src_name, dst_name, specific, common=True):
    text = (TOOLS / src_name).read_text(encoding='utf-8')
    assert '\r\n' not in text, src_name
    if common:      # the renames first, so the specific changes below keep their own words (e.g. "attempt 2", "_v21.py")
        for old, new in COMMON:
            text = text.replace(old, new)
    for old, new, count in specific:
        n = text.count(old)
        if n != count:
            sys.exit('FAILED %s: %r found %d times, expected %d' % (src_name, old[:80], n, count))
        text = text.replace(old, new)
    left = sorted(set(re.findall(r'[^\n]*(?:v21|v2\.1|v2_1|label_v21)[^\n]*', text)))
    (TOOLS / dst_name).write_text(text, encoding='utf-8', newline='\n')
    print('written tools/%s; lines still naming 2.1: %d' % (dst_name, len(left)))
    for line in left:
        print('   ', line.strip()[:150])


# ---- writer
src = (TOOLS / 'write_passages_v21.py').read_text(encoding='utf-8')
old_settings = re.search(r'SETTINGS = \{\n.*?\n\}\n', src, re.S).group(0)
new_settings = ('SETTINGS = {\n    \'verdict\': %r,\n    \'practice\': %r,\n}\n' % (VERDICT_SETTINGS, PRACTICE_SETTINGS))
sys.path.insert(0, str(TOOLS))
import write_passages_v21 as w21  # noqa: E402  (read only: the 50 settings of attempt 2)
earlier_add = ('EARLIER += %r   # the 50 settings of attempt 2, in tools/write_passages_v21.py\n'
               % (list(w21.SETTINGS['verdict']) + list(w21.SETTINGS['practice'])))
old_earlier_end = re.search(r"'picture framing shop; a snooker hall; a soap workshop; a dance school; a youth hostel'\)\.split\('; '\)\n", src).group(0)
make('write_passages_v21.py', 'write_passages_v22.py', [
    (old_settings, new_settings, 1),
    (old_earlier_end, old_earlier_end + earlier_add, 1),
    ("SEEDS = {'verdict': 20261021, 'practice': 20261022}", "SEEDS = {'verdict': 20261031, 'practice': 20261032}", 1),
    ("len(EARLIER) != 112", "len(EARLIER) != 162", 1),
    ("    for tool in ('write_verdict_passages.py', 'write_passages_outside.py', 'write_passages_v2.py'):",
     "    for tool in ('write_verdict_passages.py', 'write_passages_outside.py', 'write_passages_v2.py', 'write_passages_v21.py'):", 1),
    # the shared request ledger stays where it is: keep its folder name out of the common rename
    ("HERE.parent / 'label_v21' / 'writer_request_ledger.json'", "HERE.parent / 'label_v21' / 'writer_request_ledger.json'  # shared with attempt 2", 1),
])

# the writer's own fingerprints of its new job lists, computed by the writer itself
import importlib  # noqa: E402
w22 = importlib.import_module('write_passages_v22')
fp = {'verdict': w22.jobs_sha256('verdict'), 'practice': w22.jobs_sha256('practice')}
wtext = (TOOLS / 'write_passages_v22.py').read_text(encoding='utf-8')
old_fp = re.search(r"EXPECTED_JOBS_SHA256 = \{'verdict': '[0-9a-f]{64}',\n\s+'practice': '[0-9a-f]{64}'\}", wtext).group(0)
wtext = wtext.replace(old_fp, "EXPECTED_JOBS_SHA256 = {'verdict': '%s',\n                        'practice': '%s'}" % (fp['verdict'], fp['practice']))
(TOOLS / 'write_passages_v22.py').write_text(wtext, encoding='utf-8', newline='\n')
print('job-list fingerprints:', fp)

# ---- seal
make('seal_v21.py', 'seal_v22.py', [
    ("SEEDS = {'practice': 20261024, 'verdict': 20261023}", "SEEDS = {'practice': 20261034, 'verdict': 20261033}", 1),
    ("OLD_PASSAGES = ROOT / 'verdict' / 'passages_sealed.json'   # the 428 passages of attempt 1",
     "OLD_PASSAGES = [ROOT / 'verdict' / 'passages_sealed.json',                  # the 428 passages of attempt 1\n"
     "                ROOT / 'label_v21' / 'verdict' / 'passages_sealed.json',     # the 427 sealed passages of attempt 2\n"
     "                ROOT / 'label_v21' / 'practice' / 'passages_practice.json']  # the 30 practice passages of attempt 2", 1),
    ("    not_in, practice_block = [Path(p) for p in args.also_not_in] + ([OLD_PASSAGES] if OLD_PASSAGES.is_file() else []), None",
     "    gone = [str(p) for p in OLD_PASSAGES if not p.is_file()]\n"
     "    if gone:\n"
     "        refuse('an earlier passage set to compare against is missing: %s' % ', '.join(gone))\n"
     "    not_in, practice_block = [Path(p) for p in args.also_not_in] + list(OLD_PASSAGES), None", 1),
    ("compared_for_exact_repeats=[p.name for p in not_in]",
     "compared_for_exact_repeats=[os.path.relpath(p, ROOT).replace(os.sep, '/') for p in not_in]", 1),
    ("owner_ruling=Path(part_a.RULING))   # not options: the check reads these very files",
     "owner_ruling=Path(part_a.RULING),\n"
     "                  owner_answers=ROOT / 'label_v22_draft' / 'OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json',\n"
     "                  team_a_wrapper=ROOT / 'label_v22' / 'TEAM_A_WRAPPER.txt',\n"
     "                  flag_gate=HERE / 'flag_gate_v22.py')   # not options: the check reads these very files", 1),
    ("moved = [role for role in ('guide', 'plan', 'attempt1_program', 'canon', 'owner_ruling')",
     "moved = [role for role in ('guide', 'plan', 'attempt1_program', 'canon', 'owner_ruling', 'owner_answers', 'team_a_wrapper', 'flag_gate')", 1),
    ("SIGNED: label-agreement v2.1, guide", "SIGNED: label-agreement v2.2, guide", 2),
    ("label-agreement v2\\.1,", "label-agreement v2\\.2,", 1),
])

# ---- scorer
make('verdict_v21.py', 'verdict_v22.py', [
    ("str(HERE.parent / 'label_v21' / 'LABELER_INSTRUCTIONS.txt')", "str(HERE.parent / 'label_v22' / 'LABELER_INSTRUCTIONS.txt')", 1),
])

# ---- team A and team B
make('team_a_receipt_v21.py', 'team_a_receipt_v22.py', [
    ("default=str(ROOT / 'label_v21' / 'LABELER_INSTRUCTIONS.txt')", "default=str(ROOT / 'label_v22' / 'LABELER_INSTRUCTIONS.txt')", 1),
])
make('label_outside_v21.py', 'label_outside_v22.py', [])
