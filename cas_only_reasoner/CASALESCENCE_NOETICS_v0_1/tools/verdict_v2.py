"""Label-agreement scorer, version 2. Plain Python, standard library only. No model, no network, no key.

It implements three sections of design_v2/labeling_final.json, field `spec`:
`matching_algorithm_precise`, `measures_and_bars` and `extra_and_missing_reporting`.

FOUR WAYS TO RUN IT
  verdict   Scores a sealed verdict set. Before it scores anything it runs the gate below. If the gate finds
            one problem it prints REFUSED, scores nothing and ends with exit code 2.
  practice  Scores practice labels. Prints Tables 1, 2 and 5 and the seal conditions S1 to S5. Never a verdict.
            It runs the label part of the gate. Its report names the sha256 of every file it was made with.
  old       Program check part 1. Reads the old v1.2 label files through one fixed mapping. Never a verdict.
  fixture   Program checks part 2, 3 and 4 on the hand-made fixture, compared with FIXTURE_EXPECTED.json.

  verdict_v2.py verdict  --seal SEAL.json --guide G.md --plan P.md --checker C.py --passages passages_sealed.json
                         --labels-a A.json --labels-b B.json --receipt-a RA.json --receipt-b RB.json
                         [--instructions I.txt] [--kinds K.json] [--ruling R.json] [--out REPORT.json]
  verdict_v2.py practice --passages P.json --labels-a A.json --labels-b B.json --checker C.py --guide G.md
                         --instructions I.txt [--kinds K.json] [--fixture-dir DIR --old-dir DIR] [--out REPORT.json]
  verdict_v2.py old      --old-dir DIR [--expected FIXTURE_EXPECTED.json] [--out REPORT.json]
  verdict_v2.py fixture  --dir label_v2/fixture [--checker tools/check_labels_v2.py]

WHAT IT READS
  passages   a JSON list of {"id": ..., "text": ...}.
  labels     a JSON list of passage records: passage_id, none_of_these, entries, not_enough_information, guide_problem.
             An entry has: noetic, mind, label, support, measure, relative_to, certainty, and where they apply
             other_candidate, held_under, reached_by, clue, no_fuller_name. An optional field with an empty value
             ("", false or null) is read as left out.
  marks the checker writes (never the labeler):
             on a record: "labeler_failed": true when the team could not label the passage after three tries;
                          "reasks": [{"noetic": "^7", "check": "C3"}, ...], one item per failed check per try;
                          "checker": {"checker": name, "tries": 1..3, "final": state, ...}.
             on an entry: "dropped": true when it still failed C1 to C8 after the third try, and
                          "failed_checks": ["C3", ...];
                          "removed_after_reask": true when the entry failed a check, was sent back, and the labeler
                          then left it out. The checker puts it back. It is a dropped entry and stays in its row.
  kinds      optional: a JSON list of {"id": ..., "kind": ...}. Used for description (Table 6) and seal condition S4.
  ruling     optional: {"H2-COMFORT": "open" | "counts" | "does_not_count", ...}. A verdict needs "open" for every code.
  seal       the record tools/seal_v2.py writes in verdict mode: schema "casalescence/label-agreement-v2-seal/1",
             "is_a_seal": true, "guide", "plan", "checker", "scorer", "passages" and "hold_table" (each with "file"
             and "sha256"), "owner_signoff" and "seal_conditions". No other layout is read. A practice-set record
             is not a seal. The first attempt's SEAL.json is not read: verdict mode is never run on the old set.
  receipt    one per team: the receipt tools/check_labels_v2.py writes beside the label file at export, and
             tools/label_outside_v2.py writes for its team. A JSON object with "checker_sha256", "guide_sha256",
             "passages_sha256", "instructions_sha256", "labels_sha256", and "launch_text_sha256" (team A) or
             "tool_sha256" (team B).

THE GATE OF VERDICT MODE. Every line is a refusal. Nothing is scored until all of them pass.
  1. The seal is a seal: the schema above; "is_a_seal" true; "no_label_existed_when_sealed" true; an "owner_signoff"
     object with a sha256 and a decision for every sheet item this program carries out (1, 2, 3, 4a to 4h, 5, 6,
     8a to 8e); a "seal_conditions" object; a sha256 for the hold table.
  2. Guide, plan, checker, scorer and passages have the sha256 the seal names.
  3. Every signed value the seal holds (a bar, a minimum count, an outcome word, the ^5 bar row, a number of S2,
     S4 or S5) is the value this program's constants block holds. The seal may keep such a value beside its item
     ("constants") or in one list ("owner_values"); both are read. A hold code the owner ruled on (the item's
     "hold_code_removed", or the list "hold_codes_removed") is not in HOLD_CODES; every other code is.
  4. --ruling, when given, is the sealed hold table (the same sha256). A ruling file that is not the sealed table
     and sets a code to counts or does_not_count is a re-score: every row prints REPORTED_ONLY_NO_BAR.
  5. Both label files hold exactly one row for every sealed passage. Every row carries the checker's block. Every
     row is final: LABELED, LABELED_WITH_DROPPED_ENTRIES, or NOT_LABELED after all three tries. No row was closed
     before its third try. An open row is a refusal, not a passage 'not labeled'.
  6. The sealed checker is loaded from --checker and run again on every final record. An entry that fails C1 to C8
     and is not marked dropped is a refusal. So a label file that did not go through the checker is not scored.
  7. Each team's receipt names the sealed checker, guide and passages. Where the seal names them, it also names
     the sealed labeler instructions, the team A launch text (team A) and the team B labeling tool (team B). Where
     the receipt names its label file or a seal record, they are the ones given. Every try log the receipt lists
     was written by the sealed checker. The receipt does not say that a passage is open or that a row was closed
     early. The two label files are not the same file.
  Practice mode runs lines 5 and 6 as well, with one difference: a row that is not final is listed, and counted
  as not labeled, instead of refused.

THE LOCATION BACKSTOP. The checker is a separate program. This program does not repeat its judgments
(pointer labels, word counts, feeling words). It keeps every drop the checker marked. It also treats as dropped
any entry it cannot place in the passage, or whose fields break a tie between fields that a class rests on, and
names the check that should have caught it (C1 to C6). The ties, as the guide's section B2 writes them: `reached_by`
never with `held` and never with `other_candidate` reasoning; `clue` true only with certainty clear; `mind` empty in
a `^6`; a `^9` with `reached_by` has no `relative_to` and is no partner of a `^8`; a clue has no `relative_to`.
One thing written twice for one Noetic, in one certainty or in two, or once as a clue and once as a plain part:
the checker fails the later one (C8). If one slips past the checker, this program keeps the first and counts the
other as a duplicate. A dropped entry never vanishes: it stays in its row as an unmatched entry.
In fixture mode part 2 scores raw label files, so it tests this backstop alone. Part 3 sends the same files
through the checker first. Verdict and practice mode never score a raw file (gate line 6).

WHAT IT WRITES. Tables go to the screen. With --out it writes three files: the report (all tables, the listing of
every unmatched entry, per-passage counts), <name>.matched_pairs.json (every matched bar-row pair, for option B) and
<name>.owner_sample.json (the owner's reading sample). `old` refuses an --out inside the old label folder.
`fixture` writes nothing.

THE OUTCOME COLUMN. Only a valid `verdict` run with every hold code open prints one of the four outcome words.
  practice, old, fixture      NOT_A_VERDICT, with the word the rule would give beside it, so the arithmetic can be checked.
  an invalid verdict run      INVALID_RUN_NO_VERDICT, with the word the rule would give beside it.
  a run under an owner ruling REPORTED_ONLY_NO_BAR on every row, and no other word.

EXIT CODES. 0 done. 1 a program check found a difference. 2 refused: the gate found a problem; nothing was scored.

STATUS OF THE NUMBERS. Every bar, the hold table, the outcome words, the `^5` bar row and the seal conditions are
PROPOSALS until the owner signs them, before any new passage is sealed. Verdict mode refuses a seal that holds no
owner sign-off record. It reads that record's sha256 and its items. It cannot tell whether a signature is real:
that is the operator's record to keep true.
Outcome words come only from this program. A failed bar is a failure. There is no pass with notes.
"""
import argparse
import collections
import copy
import hashlib
import json
import random
import re
import statistics
import sys
from pathlib import Path

# =====================================================================================================
# CONSTANTS BLOCK. The plan quotes this block. Nothing else in this program is tunable.
# All of it is a PROPOSAL until the owner signs it, before any new passage is sealed.
# =====================================================================================================
BAR_ENTRY_AGREEMENT = 0.80     # entry agreement E must be at least this
BAR_KAPPA = 0.60               # Cohen's kappa on presence must be at least this
MIN_CASES = 50                 # fewer cases than this: NOT_ENOUGH_CASES
MIN_ABSENCES = 50              # fewer passages where neither team marked it: NOT_ENOUGH_CASES
MAX_UNLABELED_SHARE = 0.05     # more than this share of passages not labeled by both teams: the run is invalid
MAX_DROPPED_SHARE = 0.05       # more than this share of one team's entries dropped: the run is invalid
START_TOLERANCE_WORDS = 2      # two labels are the same thing only if they start at most this many words apart
RESAMPLES = 2000               # whole-passage resamples for every 95% interval
SEED_INTERVALS = 20261006      # seed for the resamples
SHUFFLE_ROUNDS = 300           # rounds of the role-shuffle floor
SEED_SHUFFLE = 20261007        # seed for the role-shuffle floor
SEED_OWNER_SAMPLE = 20261008   # seed for the owner's reading sample
SEAL_S2_MAX_DROPPED_SHARE = 0.05   # S2: each team must be under this on the practice labels
SEAL_S4_KIND = 'K1'                # S4 is read on practice passages of this kind
SEAL_S4_MIN_E = 0.80               # S4: entry agreement for ^8 and for ^9 at least this
SEAL_S5_MIN_WHOLE_SHARE = 0.80     # S5: share of ^6 part matches that also match on the whole
FIVE_BAR_ROW = 'without_twins'     # sheet item 6. Which ^5 row carries the bar. 'without_twins': ^5 as the labelers
#                                    wrote it. 'with_twins': that row plus the ^5 this program adds beside each clear ^7.
#                                    The other of the two rows is printed with no bar.
BAR_ROW_5_WITH_TWINS = FIVE_BAR_ROW == 'with_twins'   # the same setting read as true or false. It is never set by
#                                    hand: change FIVE_BAR_ROW. tools/seal_v2.py may read either name.
HOLD_CODES = {                 # rule 17, the hold table: code -> the Noetics it may sit on
    'H2-COMFORT': ('^2',), 'H3-NOPULL': ('^3',), 'H3-BORED': ('^3',), 'H5-ROLE': ('^5',),
    'H7-RESULT': ('^7',), 'H7-NOEFFECT': ('^7',), 'H7-UNBROKEN': ('^7',), 'H89-FOLLOWS': ('^8', '^9')}
OUTCOME_NOT_ENOUGH = 'NOT_ENOUGH_CASES'
OUTCOME_NOT_LABELABLE = 'NOT_LABELABLE_UNDER_THIS_METHOD'
OUTCOME_WAITING = 'NO_VERDICT_WAITING_ON_OWNER'
OUTCOME_LABELABLE = 'LABELABLE_UNDER_THIS_METHOD'
OUTCOME_NO_BAR = 'REPORTED_ONLY_NO_BAR'
# ============================== END OF THE CONSTANTS BLOCK ===========================================

# Fixed word lists. They are part of the written matching rule, not settings.
FILLER = frozenset('the a an of to in on at and or his her their its he she it that this was had with for from by as '
                   'him them they is were be been not'.split())
ABBREVIATIONS = ('Mr', 'Mrs', 'Ms', 'Dr', 'St', 'Prof', 'Sr', 'Jr', 'No', 'vs', 'etc', 'e.g', 'i.e')
NO_IMPRESSION_WORDS = frozenset('no not never none nothing unheard unnoticed unseen unfazed unaffected ignored '
                                'background'.split())
assert len(FILLER) == 34
assert FIVE_BAR_ROW in ('without_twins', 'with_twins') and BAR_ROW_5_WITH_TWINS is (FIVE_BAR_ROW == 'with_twins')

# Fixed names the gate of verdict mode reads. They are not settings.
SEAL_SCHEMA = 'casalescence/label-agreement-v2-seal/1'      # written by tools/seal_v2.py, in verdict mode only
SEALED_ROLES = ('guide', 'plan', 'checker', 'scorer', 'passages')
FINAL_STATES = ('LABELED', 'LABELED_WITH_DROPPED_ENTRIES', 'NOT_LABELED')
HOLD_CODE_ITEMS = {'H2-COMFORT': '4a', 'H3-NOPULL': '4b', 'H3-BORED': '4c', 'H5-ROLE': '4d', 'H7-RESULT': '4e',
                   'H7-NOEFFECT': '4f', 'H7-UNBROKEN': '4g', 'H89-FOLLOWS': '4h'}   # the sheet's item for each code
CONDITION_ITEMS = {'S1': '8a', 'S2': '8b', 'S3': '8c', 'S4': '8d', 'S5': '8e'}      # the sheet's item for each condition
SIGNED_ITEMS_CARRIED_HERE = (['1', '2', '3'] + sorted(HOLD_CODE_ITEMS.values()) + ['5', '6']
                             + sorted(CONDITION_ITEMS.values()))
RECEIPT_KEYS = ('checker_sha256', 'guide_sha256', 'passages_sha256')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
SAYING_AGAINST_RULE = 'Saying against rule:'    # guide rule 14: how such a guide_problem report starts

sys.dont_write_bytecode = True    # leave no cache folder beside the frozen tools when the checker is loaded

NOETICS = ['^%d' % i for i in range(1, 10)]
CERTAINTIES = ('clear', 'ambiguous', 'held')
HELD_NOETICS = [n for n in NOETICS if any(n in v for v in HOLD_CODES.values())]
TIED = ('^6', '^8', '^9')            # Noetics whose entries are tied together by a related thing
WITH_MEASURE = ('^4', '^7')
REASONS = ['DROPPED', 'STATUS', 'FIELD', 'MIND', 'START', 'OTHER_LABEL', 'OTHER_NOETIC', 'FACES_A_DROP',
           'OTHER_THING', 'ABSENT']
CHECKS = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9']
NOT_A_VERDICT = 'NOT_A_VERDICT'
INVALID_RUN = 'INVALID_RUN_NO_VERDICT'
CURLY = ((chr(0x2018), "'"), (chr(0x2019), "'"), (chr(0x201c), '"'), (chr(0x201d), '"'))
WORD = re.compile(r'[A-Za-z0-9]+')
STOP = re.compile(r'[.!?]+["\')\]]*(?=\s|$)')
OLD_WORD = re.compile(r"[A-Za-z0-9']+")


# ----------------------------------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------------------------------
def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))


def f3(value):
    return 'n/a' if value is None else '%.3f' % value


def interval_text(pair):
    return '[n/a]' if not pair or pair[0] is None else '[%.3f, %.3f]' % (pair[0], pair[1])


def ratio(top, bottom):
    return top / bottom if bottom else None


# ----------------------------------------------------------------------------------------------------
# matching steps 0, 1, 2, 4: clean-up, words, sentences, word sets
# ----------------------------------------------------------------------------------------------------
def clean(text):
    """Step 0. Curly quotes become straight quotes. Every run of white space becomes one space. Ends are trimmed."""
    text = text if isinstance(text, str) else ''
    for curly, straight in CURLY:
        text = text.replace(curly, straight)
    return ' '.join(text.split())


def split_sentences(text):
    """Step 2. A sentence ends after a run of . ! ? (plus closing quotes or brackets) followed by a space or the end.
    A single full stop right after a listed abbreviation does not end a sentence."""
    out, start = [], 0
    for stop in STOP.finditer(text):
        if stop.group() == '.':
            before = text[start:stop.start()].split()
            if before and before[-1].lstrip('"\'([') in ABBREVIATIONS:
                continue
        out.append((start, stop.end()))
        start = stop.end()
        while start < len(text) and text[start] == ' ':
            start += 1
    if start < len(text):
        out.append((start, len(text)))
    return out


class Passage:
    def __init__(self, pid, raw_text):
        self.pid = pid
        self.text = clean(raw_text)
        self.words = [(m.start(), m.end(), m.group().lower()) for m in WORD.finditer(self.text)]   # step 1
        self.sentences = split_sentences(self.text)
        self._w, self._c = {}, {}

    def occurrences(self, quote, lo=0, hi=None):
        """Every place the quote occurs between lo and hi with no letter or digit right before or right after it."""
        text = self.text
        hi = len(text) if hi is None else hi
        out = []
        if not quote:
            return out
        at = text.find(quote, lo)
        while at >= 0 and at + len(quote) <= hi:
            end = at + len(quote)
            if (at == 0 or not text[at - 1].isalnum()) and (end == len(text) or not text[end].isalnum()):
                out.append((at, end))
            at = text.find(quote, at + 1)
        return out

    def raw_first(self, quote):
        """Old labels only: the first raw place, word edges not checked."""
        at = self.text.find(quote) if quote else -1
        return (at, at + len(quote)) if at >= 0 else None

    def W(self, span):
        """Step 4. The positions (0, 1, 2, ...) of the words that lie wholly inside the span."""
        if span not in self._w:
            self._w[span] = tuple(k for k, (s, e, _) in enumerate(self.words) if s >= span[0] and e <= span[1])
        return self._w[span]

    def C(self, span):
        """Step 4. The content words among them; if there are none, all of them."""
        if span not in self._c:
            every = self.W(span)
            content = frozenset(k for k in every if len(self.words[k][2]) >= 2 and self.words[k][2] not in FILLER)
            self._c[span] = content or frozenset(every)
        return self._c[span]

    def widen(self, span):
        """Widen a span to whole sentences."""
        starts = [s for s, e in self.sentences if s <= span[0] < e]
        ends = [e for s, e in self.sentences if s < span[1] <= e]
        return (min(starts) if starts else 0, max(ends) if ends else len(self.text))

    def sentence_ids(self, span):
        return frozenset(k for k, (s, e) in enumerate(self.sentences) if s < span[1] and e > span[0])

    def sentence_of(self, position):
        for k, (s, e) in enumerate(self.sentences):
            if s <= position < e:
                return k
        return None


# ----------------------------------------------------------------------------------------------------
# matching step 5: the three tests
# ----------------------------------------------------------------------------------------------------
def same_thing(P, p, q, tolerance):
    """SAME_THING for two single places. tolerance None means: no start rule."""
    wp, wq = P.W(p), P.W(q)
    if not wp or not wq or not (P.C(p) & P.C(q)):
        return False
    return tolerance is None or abs(wp[0] - wq[0]) <= tolerance


def any_same_thing(P, places_a, places_b, tolerance):
    return any(same_thing(P, p, q, tolerance) for p in places_a for q in places_b)


def any_overlap(P, places_a, places_b):
    """OVERLAP: the two share at least one content word at the same position."""
    return any(bool(P.C(p) & P.C(q)) for p in places_a for q in places_b)


def same_field(P, places_a, places_b, tolerance):
    """SAME_FIELD: both empty is yes; one empty is no; otherwise SAME_THING."""
    if not places_a and not places_b:
        return True
    if not places_a or not places_b:
        return False
    return any_same_thing(P, places_a, places_b, tolerance)


def old_content(text):
    words = OLD_WORD.findall(text.lower())
    return [w for w in words if w not in FILLER] or words


def v12_word_test(a, b):
    """The v1.2 word test: the two quotes share at least half of the content words of the longer quote."""
    ta, tb = old_content(a), old_content(b)
    if not ta or not tb:
        return False
    shared = sum((collections.Counter(ta) & collections.Counter(tb)).values())
    return shared / max(len(ta), len(tb)) >= 0.5


# ----------------------------------------------------------------------------------------------------
# entries
# ----------------------------------------------------------------------------------------------------
class Entry:
    _next = 0

    def __init__(self, team, pid, idx, raw):
        Entry._next += 1
        self.uid = Entry._next
        self.team, self.pid, self.idx = team, pid, idx
        self.noetic = raw.get('noetic') if isinstance(raw.get('noetic'), str) else None
        self.certainty = raw.get('certainty') if isinstance(raw.get('certainty'), str) else None
        # An optional field with an empty value ("", false, null) is read as left out (guide B1).
        self.other_candidate = raw.get('other_candidate') or None
        self.held_under = (raw.get('held_under') or None) if isinstance(raw.get('held_under'), str) else None
        self.reached_by = raw.get('reached_by') or None
        self.clue = raw.get('clue') is True
        self.no_fuller_name = raw.get('no_fuller_name') is True
        self.put_back = raw.get('removed_after_reask') is True    # the checker put it back after it was left out
        self.label = clean(raw.get('label'))
        self.support = clean(raw.get('support'))
        self.measure = clean(raw.get('measure'))
        self.mind = clean(raw.get('mind'))
        self.relative_to = clean(raw.get('relative_to'))
        self.L, self.Q, self.M, self.R = [], [], [], []      # the places of label, measure, mind, related thing
        self.sents = frozenset()                             # the sentences its evidence lies in
        self.support_sentences = None
        self.valid_class = True
        self.checker_dropped = False
        self.failed = []
        self.status = 'row'    # row | dropped_in_row | dropped_no_row | duplicate | twin_written | ruled_out | left_out
        self.drop = None       # None | 'in_row' | 'no_row'. Kept even if an owner ruling later takes the entry out.
        self.cls = None
        self.tags = []
        self.c6_fail = False

    def show(self):
        out = {'noetic': self.noetic, 'mind': self.mind, 'label': self.label, 'support': self.support,
               'measure': self.measure, 'relative_to': self.relative_to, 'certainty': self.certainty}
        for key in ('other_candidate', 'held_under', 'reached_by'):
            if getattr(self, key):
                out[key] = getattr(self, key)
        if self.clue:
            out['clue'] = True
        if self.no_fuller_name:
            out['no_fuller_name'] = True
        return out


def order_key(entry):
    return (entry.L[0][0], entry.L[0][1], entry.idx)


def locate_new(team, pid, P, raws):
    """Matching step 3 for the new entry format, with the location backstop (see the top of this file)."""
    entries = []
    for k, raw in enumerate(raws):
        is_dict = isinstance(raw, dict)
        e = Entry(team, pid, k, raw if is_dict else {})
        e.valid_class = e.noetic in NOETICS and e.certainty in CERTAINTIES
        if not e.valid_class:
            e.failed.append('C1')
        if is_dict and (raw.get('dropped') or e.put_back):   # an entry the checker put back is a dropped entry
            e.checker_dropped = True
            named = raw.get('failed_checks')
            for check in ([named] if isinstance(named, str) else named if isinstance(named, list) else []):
                if isinstance(check, str) and check not in e.failed:
                    e.failed.append(check)
            if not e.failed:
                e.failed.append('not named')
        entries.append(e)
    has_reasoned_9 = any(e.noetic == '^9' and e.reached_by == 'reasoning' for e in entries)
    live = [e for e in entries if not e.failed]
    for e in live:                                           # the values a class rests on
        if e.certainty == 'held' and e.noetic not in HOLD_CODES.get(e.held_under, ()):
            e.failed.append('C1')
        elif e.noetic == '^6' and e.clue and not has_reasoned_9:
            e.failed.append('C1')
        elif e.noetic == '^6' and e.clue and e.certainty != 'clear':          # a clue is always clear
            e.failed.append('C1')
        elif e.noetic == '^9' and e.reached_by == 'reasoning' and (e.certainty == 'held'
                                                                    or e.other_candidate == 'reasoning'):
            e.failed.append('C1')                            # reached_by: never held, never an uncertain pair
    for e in live:                                           # support, label, measure
        if e.failed:
            continue
        found = P.occurrences(e.support)
        if not found:
            e.failed.append('C2')
            continue
        span = P.widen(found[0])
        e.sents = P.sentence_ids(span)
        e.support_sentences = len(e.sents)
        if e.noetic == '^1':      # a Mind: the support must hold the name; the place is the first one in the passage
            e.L = P.occurrences(e.label)[:1] if P.occurrences(e.label, span[0], span[1]) else []
        else:                     # every place the label occurs inside the widened support
            e.L = P.occurrences(e.label, span[0], span[1])
        if not e.L:
            e.failed.append('C3')
            continue
        if e.noetic in WITH_MEASURE:
            e.Q = P.occurrences(e.measure, span[0], span[1])
            if not e.Q:
                e.failed.append('C4')
    minds = {}
    for e in live:
        if e.noetic == '^1' and not e.failed:
            minds.setdefault(e.label, e.L[0])
    for e in live:                                           # the Mind, through this team's own ^1 entry
        if e.failed:
            continue
        if e.noetic == '^1':
            e.M = [e.L[0]]
        elif e.noetic != '^6':
            if e.mind in minds:
                e.M = [minds[e.mind]]
            else:
                e.failed.append('C5')
        elif e.mind:                                         # in a ^6 entry mind is always empty
            e.failed.append('C5')
    good = [e for e in live if not e.failed]
    for e in good:                                           # the related thing
        if e.noetic in ('^8', '^9'):
            if e.noetic == '^9' and e.reached_by == 'reasoning':
                e.c6_fail = bool(e.relative_to)              # a ^9 reached by reasoning has no relative_to ...
                continue
            want = '^9' if e.noetic == '^8' else '^8'
            partner = next((y for y in good if y.noetic == want and y.label == e.relative_to and y.mind == e.mind
                            and y.certainty == e.certainty and y.held_under == e.held_under
                            and y.relative_to == e.label and y.reached_by != 'reasoning'), None)   # ... and is no partner
            if partner is None:
                e.c6_fail = True
            else:
                e.R = list(partner.L)
        elif e.noetic == '^6':
            if e.clue:
                e.c6_fail = bool(e.relative_to)              # a clue has no whole
            elif e.relative_to:
                found = P.occurrences(e.relative_to)
                if not found:
                    e.c6_fail = True
                else:
                    before = [place for place in found if place[1] <= e.L[0][0]]
                    e.R = [max(before, key=lambda place: place[1]) if before else found[0]]
            elif not e.clue:
                e.c6_fail = True
    for e in good:
        if e.c6_fail:
            e.failed.append('C6')
    for e in entries:
        if e.failed:
            e.status = 'dropped_in_row' if e.valid_class else 'dropped_no_row'
            e.drop = 'in_row' if e.valid_class else 'no_row'
            e.L, e.Q, e.M, e.R = [], [], [], []              # a dropped entry has no places
    return entries


def locate_old(team, pid, P, raws):
    """Program check part 1: the one fixed mapping from a v1.2 entry. No support. One place per field. No checker."""
    def one(quote):
        found = P.occurrences(quote)
        if found:
            return [found[0]]
        raw = P.raw_first(quote)
        return [raw] if raw else []

    entries = []
    for k, raw in enumerate(raws):
        words = clean(raw.get('words'))
        related = clean(raw.get('relative_to'))
        e = Entry(team, pid, k, {'noetic': raw.get('noetic'),
                                 'certainty': 'ambiguous' if raw.get('certainty') == 'ambiguous' else 'clear',
                                 'other_candidate': raw.get('other_candidate'), 'reached_by': raw.get('reached_by'),
                                 'mind': raw.get('mind')})
        entries.append(e)
        if e.noetic not in NOETICS or not words or words not in P.text:
            e.status = 'left_out'
            continue
        if e.noetic in WITH_MEASURE:      # the old `relative_to` (the thing) is the label; the old `words` the measure
            e.label, e.measure = related, words
            e.L = one(related) if related else []
            e.Q = one(words)
        else:
            e.label = words
            e.L = one(words)
            e.relative_to = related
            if e.noetic == '^6':
                if not related:
                    e.clue = True         # a ^6 with an empty whole goes to the clue row
                elif e.L:
                    found = P.occurrences(related) or one(related)
                    before = [place for place in found if place[1] <= e.L[0][0]]
                    e.R = [max(before, key=lambda place: place[1])] if before else found[:1]
            elif e.noetic in ('^8', '^9'):
                e.R = one(related) if related else []
        e.M = one(e.mind) if e.mind else []
        if not e.L:
            e.status = 'left_out'         # an entry whose label cannot be found is left out
            e.Q, e.M, e.R = [], [], []
            continue
        e.sents = frozenset(P.sentence_of(place[0]) for place in (e.L[:1] + e.Q[:1]))
    return entries


def entry_class(entry, ruling, noetic=None):
    """Matching step 6. Exactly one class. `noetic` overrides the symbol (role-shuffle floor only).
    Returns None for a held entry whose code the owner ruling sets to does_not_count."""
    n = noetic or entry.noetic
    certainty = entry.certainty
    if certainty == 'held':
        state = ruling.get(entry.held_under, 'open')
        if state == 'does_not_count':
            return None
        if state == 'open':
            return 'held ' + n
        certainty = 'clear'               # counts: treated as a clear entry of its Noetic
    if certainty == 'ambiguous':
        return ('uncertain ' if entry.other_candidate == 'reasoning' else 'ambiguous ') + n
    if n == '^9' and entry.reached_by == 'reasoning':
        return '^9 reached by reasoning'
    if n == '^6' and entry.clue:
        return '^6 clue'
    return n


# ----------------------------------------------------------------------------------------------------
# matching step 8: one-to-one pairing (Kuhn's augmenting-path method)
# ----------------------------------------------------------------------------------------------------
def largest_pairing(P, ea, eb, ok):
    """ea and eb are already in the fixed order. Returns the pairs (i, j). The number of pairs is the largest possible."""
    candidates = []
    for x in ea:
        js = [j for j, y in enumerate(eb) if ok(x, y)]
        js.sort(key=lambda j, x=x: (abs(x.L[0][0] - eb[j].L[0][0]), -len(P.C(x.L[0]) & P.C(eb[j].L[0])), j))
        candidates.append(js)
    holder = {}

    def place(i, seen):
        for j in candidates[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in holder or place(holder[j], seen):
                holder[j] = i
                return True
        return False

    for i in range(len(ea)):
        place(i, set())
    return sorted((i, j) for j, i in holder.items())


class PassageRow:
    """One class in one passage."""

    def __init__(self, ea, eb, da, db, pairs):
        self.ea, self.eb, self.da, self.db = ea, eb, da, db
        self.pairs = [(ea[i], eb[j]) for i, j in pairs]
        used_a, used_b = {i for i, _ in pairs}, {j for _, j in pairs}
        self.ua = [x for i, x in enumerate(ea) if i not in used_a]
        self.ub = [y for j, y in enumerate(eb) if j not in used_b]
        self.a, self.b, self.m = len(ea) + len(da), len(eb) + len(db), len(pairs)


class Row:
    """Matching step 9: the counts of one class over all analysed passages."""

    def __init__(self, name, noetic, per, n_passages):
        self.name, self.noetic, self.per, self.n = name, noetic, per, n_passages
        self.A = sum(r.a for r in per.values())
        self.B = sum(r.b for r in per.values())
        self.M = sum(r.m for r in per.values())
        self.only_A, self.only_B = self.A - self.M, self.B - self.M
        self.E = ratio(self.M, self.A + self.B - self.M)
        self.share_A, self.share_B = ratio(self.M, self.A), ratio(self.M, self.B)
        self.cases = len(per)
        self.absences = n_passages - self.cases
        self.fully_matched = sum(1 for r in per.values() if r.a == r.m and r.b == r.m)
        self.with_a_match = sum(1 for r in per.values() if r.m)
        self.match_and_leftovers = self.with_a_match - self.fully_matched
        self.no_match = self.cases - self.with_a_match
        both = sum(1 for r in per.values() if r.a and r.b)
        only_a = sum(1 for r in per.values() if r.a and not r.b)
        only_b = sum(1 for r in per.values() if r.b and not r.a)
        self.kappa = kappa_from_counts(both, only_a, only_b, n_passages)

    def restrict(self, pids, n_passages):
        return Row(self.name, self.noetic, {p: r for p, r in self.per.items() if p in pids}, n_passages)

    def counts(self):
        return {'A': self.A, 'B': self.B, 'M': self.M, 'only_A': self.only_A, 'only_B': self.only_B, 'E': self.E}


def kappa_from_counts(both, only_a, only_b, total):
    """Cohen's kappa on 'this passage has at least one entry of the row'. Whole-number arithmetic until the last step:
    kappa = (agree - chance) / (1 - chance), with both sides multiplied by total * total."""
    if not total:
        return None
    marked_a, marked_b = both + only_a, both + only_b
    agree = total * (both + (total - both - only_a - only_b))
    chance = marked_a * marked_b + (total - marked_a) * (total - marked_b)
    return None if chance == total * total else (agree - chance) / (total * total - chance)


# ----------------------------------------------------------------------------------------------------
# one scoring run
# ----------------------------------------------------------------------------------------------------
class Run:
    def __init__(self, mode, passages, records_a, records_b, ruling=None, kinds=None):
        self.mode = mode                                    # verdict | practice | old | fixture
        self.old = mode == 'old'
        self.P = {p['id']: Passage(p['id'], p['text']) for p in passages}
        self.order = [p['id'] for p in passages]
        self.ruling = {code: 'open' for code in HOLD_CODES}
        for code, state in (ruling or {}).items():
            if code not in HOLD_CODES or state not in ('open', 'counts', 'does_not_count'):
                raise SystemExit('REFUSED: the ruling file may only set the 8 hold codes to open, counts or '
                                 'does_not_count. Found %r: %r' % (code, state))
            self.ruling[code] = state
        self.rescored = any(state != 'open' for state in self.ruling.values())
        self.kinds = kinds or {}
        self.records = {'A': self._records(records_a), 'B': self._records(records_b)}
        self.unlabeled = {t: sorted(p for p in self.P if p not in self.records[t] or self.records[t][p].get('labeler_failed'))
                          for t in 'AB'}
        excluded = set(self.unlabeled['A']) | set(self.unlabeled['B'])
        self.excluded = sorted(excluded)
        self.ids = sorted(p for p in self.P if p not in excluded)
        self.all = {'A': {}, 'B': {}}                       # every entry a team sent, per passage
        locate = locate_old if self.old else locate_new
        for team in 'AB':
            for pid, record in self.records[team].items():
                if pid in self.P and not record.get('labeler_failed'):
                    raws = record.get('entries') if isinstance(record.get('entries'), list) else []
                    self.all[team][pid] = locate(team, pid, self.P[pid], raws)
        self.twins = {'A': {}, 'B': {}}
        # Sheet item 6: which ^5 row carries the bar. The old labels have no twins, so there the row is as written.
        self.twins_in_bar = FIVE_BAR_ROW == 'with_twins' and not self.old
        self.other_five_row = '^5 without twins' if self.twins_in_bar else '^5 with twins'
        self._tests = {}
        self._prepare()

    @staticmethod
    def _records(records):
        if isinstance(records, dict):
            records = list(records.values())
        return {r['passage_id']: r for r in records if isinstance(r, dict) and 'passage_id' in r}

    def _prepare(self):
        for team in 'AB':
            for pid, entries in self.all[team].items():
                P = self.P[pid]
                rows = [e for e in entries if e.status == 'row']
                if not self.old:      # step 3b: the ^5 that goes with a team's own ^7 is taken out of every row
                    sevens = [e for e in rows if e.noetic == '^7' and e.certainty in ('clear', 'held')]
                    for e in rows:
                        if e.noetic == '^5' and any(s.mind == e.mind and any_same_thing(P, e.L, s.L, START_TOLERANCE_WORDS)
                                                    for s in sevens):
                            e.status = 'twin_written'
                for e in entries:     # step 6, under the owner ruling
                    if e.status in ('row', 'dropped_in_row'):
                        e.cls = entry_class(e, self.ruling)
                        if e.cls is None:
                            e.status = 'ruled_out'
                kept = []             # a duplicate that slipped past the checker: keep the first
                for e in entries:
                    if e.status != 'row':
                        continue
                    if any(self.repeats(k, e) for k in kept):
                        e.status = 'duplicate'
                    else:
                        kept.append(e)
                if not self.old:      # step 3b: one program-made ^5 twin for every located clear ^7 entry
                    made = []
                    for e in kept:
                        if e.cls == '^7':
                            twin = Entry(team, pid, e.idx, {'noetic': '^5', 'certainty': 'clear'})
                            twin.mind, twin.label, twin.support = e.mind, e.label, e.support
                            twin.L, twin.M, twin.sents = list(e.L), list(e.M), e.sents
                            twin.cls, twin.status = '^5 with twins', 'twin'
                            made.append(twin)
                    self.twins[team][pid] = made

    # ----- the tests between two entries -----
    def raw_tests(self, x, y, tolerance=START_TOLERANCE_WORDS):
        key = (x.uid, y.uid, tolerance)
        if key not in self._tests:
            P = self.P[x.pid]
            self._tests[key] = (any_same_thing(P, x.L, y.L, tolerance), same_field(P, x.M, y.M, tolerance),
                                same_field(P, x.R, y.R, tolerance), any_overlap(P, x.Q, y.Q))
        return self._tests[key]

    def parts(self, n, x, y, tolerance=START_TOLERANCE_WORDS):
        """R1 to R4 as they apply to Noetic n. A test that does not apply to n counts as passed."""
        r1, r2, r3, r4 = self.raw_tests(x, y, tolerance)
        return r1, (True if n in ('^1', '^6') else r2), (r3 if n in TIED else True), (r4 if n in WITH_MEASURE else True)

    def same_reading(self, n, x, y, tolerance=START_TOLERANCE_WORDS, label_test=None, skip_whole=False):
        """Matching step 7. The supports are never compared."""
        r1, r2, r3, r4 = self.parts(n, x, y, tolerance)
        if label_test is not None:
            r1 = label_test(x, y)
        return r1 and r2 and (r3 or skip_whole) and r4

    def repeats(self, first, later):
        """The backstop for check C8: `later` writes a thing that `first`, of the same team, already wrote.
        Old labels: the same class and the same reading. New format (guide B2, C8): the same Noetic and the same
        reading, whatever the two certainties; and one piece written both as a clue and as a plain part."""
        if self.old:
            return first.cls == later.cls and self.same_reading(later.noetic, first, later)
        if first.noetic != later.noetic:
            return False
        if later.noetic == '^6' and first.clue != later.clue:
            return self.parts('^6', first, later)[0]         # a clue has no whole, so only the piece is compared
        return self.same_reading(later.noetic, first, later)

    # ----- membership -----
    def located(self, team, pid):
        return [e for e in self.all[team].get(pid, []) if e.status == 'row']

    def members(self, team, pid, classes, keep=None, twins=False):
        out = [e for e in self.all[team].get(pid, []) if e.status == 'row' and e.cls in classes and (not keep or keep(e))]
        if twins:
            out += self.twins[team].get(pid, [])
        return sorted(out, key=order_key)

    def dropped(self, team, pid, classes, keep=None):
        return [e for e in self.all[team].get(pid, [])
                if e.status == 'dropped_in_row' and e.cls in classes and (not keep or keep(e))]

    def row(self, name, classes, n, tolerance=START_TOLERANCE_WORDS, label_test=None, skip_whole=False, keep=None,
            twins=False):
        per = {}
        for pid in self.ids:
            ea, eb = self.members('A', pid, classes, keep, twins), self.members('B', pid, classes, keep, twins)
            da, db = self.dropped('A', pid, classes, keep), self.dropped('B', pid, classes, keep)
            if not (ea or eb or da or db):
                continue
            pairs = []
            if ea and eb:
                pairs = largest_pairing(self.P[pid], ea, eb,
                                        lambda x, y: self.same_reading(n, x, y, tolerance, label_test, skip_whole))
            per[pid] = PassageRow(ea, eb, da, db, pairs)
        return Row(name, n, per, len(self.ids))

    # ----- matching step 10: one reason for every unmatched bar-row entry -----
    def relation(self, n, x, y):
        """What two unmatched entries of one class are to each other: FIELD, MIND, START, OTHER_LABEL or nothing."""
        P = self.P[x.pid]
        r1, r2, r3, r4 = self.parts(n, x, y)
        if r1 and r2 and not (r3 and r4):
            return 'FIELD', ('R3 related thing' if not r3 else 'R4 measure')
        if r1 and not r2:
            return 'MIND', None
        if r2 and not r1:
            same_evidence = r3 if n in TIED else r4 if n in WITH_MEASURE else bool(x.sents & y.sents)
            if same_evidence:
                return ('START' if any_overlap(P, x.L, y.L) else 'OTHER_LABEL'), None
        return None, None

    def reason(self, n, x, other_unmatched, other_located, other_in_class, other_dropped_in_class):
        P = self.P[x.pid]
        for y in other_located:                               # 1. STATUS
            if y.noetic == n and y.cls != n:
                r1, r2, _, _ = self.parts(n, x, y)
                if r1 and r2:
                    return 'STATUS', y.cls
        for wanted in ('FIELD', 'MIND', 'START', 'OTHER_LABEL'):   # 2. to 5.
            for y in other_unmatched:
                kind, detail = self.relation(n, x, y)
                if kind == wanted:
                    return kind, detail
        for y in other_located:                               # 6. OTHER_NOETIC
            if y.noetic == n or y.noetic == '^1' or y.certainty == 'ambiguous':
                continue
            if n != '^6' and y.noetic != '^6' and not same_field(P, x.M, y.M, START_TOLERANCE_WORDS):
                continue
            if n in WITH_MEASURE:
                hit = any_overlap(P, x.Q, y.L) or any_overlap(P, x.Q, y.Q)
            else:
                hit = any_same_thing(P, x.L, y.L, START_TOLERANCE_WORDS) or any_overlap(P, x.L, y.Q)
            if hit:
                return 'OTHER_NOETIC', y.noetic
        if not other_in_class and other_dropped_in_class:     # 7.
            return 'FACES_A_DROP', None
        if other_in_class:                                    # 8.
            return 'OTHER_THING', None
        return 'ABSENT', None                                 # 9.

    def reasons_and_ceiling(self, n, row):
        """Step 10 for every unmatched entry of a bar row, and step 11: one-to-one pointing pairs."""
        records, pairs_strict, pairs_all, by_kind, side_by_side = [], 0, 0, collections.Counter(), []
        strict = ('FIELD', 'START', 'OTHER_LABEL') if n in TIED else ('FIELD', 'START')
        for pid, pr in row.per.items():
            P = self.P[pid]
            for team, mine, theirs, mine_dropped, theirs_dropped, theirs_class in (
                    ('A', pr.ua, pr.ub, pr.da, pr.db, pr.eb), ('B', pr.ub, pr.ua, pr.db, pr.da, pr.ea)):
                other = 'B' if team == 'A' else 'A'
                other_located = self.located(other, pid)
                ruled_out = [e for e in self.all[other].get(pid, []) if e.status == 'ruled_out' and e.noetic == n]
                for x in mine:
                    kind, detail = self.reason(n, x, theirs, other_located, len(theirs_class), len(theirs_dropped))
                    for y in ruled_out:
                        r1, r2, _, _ = self.parts(n, x, y)
                        if r1 and r2 and 'clear against a kind ruled out' not in x.tags:
                            x.tags.append('clear against a kind ruled out')
                    records.append({'pid': pid, 'team': team, 'noetic': n, 'reason': kind, 'detail': detail, 'entry': x})
                for x in mine_dropped:
                    records.append({'pid': pid, 'team': team, 'noetic': n, 'reason': 'DROPPED',
                                    'detail': ','.join(x.failed), 'entry': x})
            if pr.ua and pr.ub:
                chosen = largest_pairing(P, pr.ua, pr.ub, lambda x, y: self.relation(n, x, y)[0] in strict)
                pairs_strict += len(chosen)
                for i, j in chosen:
                    by_kind[self.relation(n, pr.ua[i], pr.ub[j])[0]] += 1
                wide = largest_pairing(P, pr.ua, pr.ub,
                                       lambda x, y: self.relation(n, x, y)[0] in ('FIELD', 'START', 'OTHER_LABEL'))
                pairs_all += len(wide)
                for i, j in wide:
                    side_by_side.append({'pid': pid, 'noetic': n, 'kind': self.relation(n, pr.ua[i], pr.ub[j])[0],
                                         'a': pr.ua[i], 'b': pr.ub[j]})
        total = row.A + row.B - row.M
        ceiling = {'pointing_pairs': pairs_strict, 'pairs_by_kind': dict(sorted(by_kind.items())),
                   'ceiling': ratio(row.M + pairs_strict, total - pairs_strict),
                   'pairs_other_label_everywhere': pairs_all,
                   'ceiling_other_label_everywhere': ratio(row.M + pairs_all, total - pairs_all)}
        return records, ceiling, side_by_side

    # ----- 95% intervals: resample whole passages -----
    def intervals(self, rows):
        N = len(self.ids)
        out = {name: {'E': [None, None], 'share_A': [None, None], 'share_B': [None, None], 'kappa': [None, None]}
               for name in rows}
        if not N:
            return out
        position = {pid: k for k, pid in enumerate(self.ids)}
        sparse = {name: [(position[pid], r.a, r.b, r.m) for pid, r in row.per.items()] for name, row in rows.items()}
        drawn = {name: {'E': [], 'share_A': [], 'share_B': [], 'kappa': []} for name in rows}
        rng = random.Random(SEED_INTERVALS)
        for _ in range(RESAMPLES):
            times = [0] * N
            for _ in range(N):
                times[rng.randrange(N)] += 1
            for name, items in sparse.items():
                a = b = m = both = only_a = only_b = 0
                for k, xa, xb, xm in items:
                    t = times[k]
                    if t:
                        a += t * xa
                        b += t * xb
                        m += t * xm
                        if xa and xb:
                            both += t
                        elif xa:
                            only_a += t
                        else:
                            only_b += t
                d = drawn[name]
                if a + b - m:
                    d['E'].append(m / (a + b - m))
                if a:
                    d['share_A'].append(m / a)
                if b:
                    d['share_B'].append(m / b)
                k = kappa_from_counts(both, only_a, only_b, N)
                if k is not None:
                    d['kappa'].append(k)
        for name, d in drawn.items():
            for key, values in d.items():
                values.sort()
                if len(values) >= 0.9 * RESAMPLES:
                    out[name][key] = [values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]]
        return out

    # ----- the role-shuffle floor -----
    def shuffle_floor(self, bar):
        """Shuffle the Noetic symbols among team B's entries inside each passage and recompute E. The cheapest baseline."""
        rng = random.Random(SEED_SHUFFLE)
        a_bar = {pid: {n: self.members('A', pid, [n], twins=self.twins_in_bar and n == '^5') for n in NOETICS}
                 for pid in self.ids}
        b_all = {pid: [e for e in self.all['B'].get(pid, []) if e.status in ('row', 'dropped_in_row')]
                 + (self.twins['B'].get(pid, []) if self.twins_in_bar else []) for pid in self.ids}
        values = {n: [] for n in NOETICS}
        for _ in range(SHUFFLE_ROUNDS):
            b_count = collections.Counter()
            m_count = collections.Counter()
            for pid in self.ids:
                entries = b_all[pid]
                symbols = [e.noetic for e in entries]
                rng.shuffle(symbols)
                by_n = collections.defaultdict(list)
                for e, n in zip(entries, symbols):
                    if entry_class(e, self.ruling, n) == n:
                        b_count[n] += 1
                        if e.status in ('row', 'twin'):
                            by_n[n].append(e)
                for n, eb in by_n.items():
                    ea = a_bar[pid][n]
                    if ea:
                        eb = sorted(eb, key=order_key)
                        m_count[n] += len(largest_pairing(self.P[pid], ea, eb, lambda x, y, n=n: self.same_reading(n, x, y)))
            for n in NOETICS:
                value = ratio(m_count[n], bar[n].A + b_count[n] - m_count[n])
                if value is not None:
                    values[n].append(value)
        return {n: {'rounds': len(v), 'mean_E': (sum(v) / len(v) if v else None), 'lowest_E': (min(v) if v else None),
                    'highest_E': (max(v) if v else None)} for n, v in values.items()}


def outcome_word(cases, absences, E, kappa, inside, outside):
    """The outcome words, in the order the plan gives."""
    if cases < MIN_CASES or absences < MIN_ABSENCES:
        return OUTCOME_NOT_ENOUGH
    if E is None or kappa is None or E < BAR_ENTRY_AGREEMENT or kappa < BAR_KAPPA:
        return OUTCOME_NOT_LABELABLE
    if outside > inside:
        return OUTCOME_WAITING
    return OUTCOME_LABELABLE


# ----------------------------------------------------------------------------------------------------
# the report
# ----------------------------------------------------------------------------------------------------
def start_gap(P, x, y):
    gaps = [abs(P.W(p)[0] - P.W(q)[0]) for p in x.L for q in y.L if same_thing(P, p, q, START_TOLERANCE_WORDS)]
    return min(gaps) if gaps else None


def nearest_other(x, others):
    if not x.L or not others:
        return None
    same = [y for y in others if y.noetic == x.noetic] or others
    best = min(same, key=lambda y: (abs(y.L[0][0] - x.L[0][0]), y.idx))
    return dict(best.show(), **{'class': best.cls})


def analyse(run):
    ids, N = run.ids, len(run.ids)

    def twins_for(n):
        """True for the ^5 rows when the constant FIVE_BAR_ROW puts the program-made twins into the bar row."""
        return run.twins_in_bar and n == '^5'

    bar = {n: run.row(n, [n], n, twins=twins_for(n)) for n in NOETICS}
    nobar = collections.OrderedDict()
    nobar['^9 reached by reasoning'] = run.row('^9 reached by reasoning', ['^9 reached by reasoning'], '^9')
    for n in NOETICS:
        nobar['uncertain ' + n] = run.row('uncertain ' + n, ['uncertain ' + n], n)
    nobar['^6 clue'] = run.row('^6 clue', ['^6 clue'], '^6')
    for n in NOETICS:
        nobar['ambiguous ' + n] = run.row('ambiguous ' + n, ['ambiguous ' + n], n)
    if not run.old:     # the ^5 row that does not carry the bar
        nobar[run.other_five_row] = run.row(run.other_five_row, ['^5'], '^5', twins=not run.twins_in_bar)
    for n in HELD_NOETICS:
        nobar['held ' + n] = run.row('held ' + n, ['held ' + n], n)

    # ----- entries, drops, validity -----
    teams = {}
    drops_by_check = {t: collections.Counter() for t in 'AB'}
    drops_by_noetic = {t: collections.Counter() for t in 'AB'}
    reasks_by_check = {t: collections.Counter() for t in 'AB'}
    reasks_by_noetic = {t: collections.Counter() for t in 'AB'}
    for team in 'AB':
        status = collections.Counter(e.status for entries in run.all[team].values() for e in entries)
        written = sum(status.values())
        dropped = sum(1 for entries in run.all[team].values() for e in entries if e.drop)
        for entries in run.all[team].values():
            for e in entries:
                if e.drop:
                    for check in e.failed:
                        drops_by_check[team][check] += 1
                    drops_by_noetic[team][e.noetic if e.noetic in NOETICS else 'no valid Noetic'] += 1
        for record in run.records[team].values():
            for item in record.get('reasks') or []:
                if isinstance(item, dict):
                    checks = item.get('checks') if isinstance(item.get('checks'), list) else [item.get('check')]
                    for check in checks:
                        reasks_by_check[team][str(check)] += 1
                    reasks_by_noetic[team][str(item.get('noetic'))] += 1
        # entries that failed a check, were sent back, were then left out by the labeler, and were put back by the checker
        put_back = [e for entries in run.all[team].values() for e in entries if e.put_back]
        put_back_by_check = collections.Counter(check for e in put_back for check in e.failed)
        put_back_by_noetic = collections.Counter(e.noetic if e.noetic in NOETICS else 'no valid Noetic' for e in put_back)
        teams[team] = {'entries_sent': written, 'in_rows': status['row'], 'dropped_kept_in_a_row': status['dropped_in_row'],
                       'dropped_no_row': status['dropped_no_row'], 'dropped_total': dropped,
                       'dropped_share': ratio(dropped, written),
                       'put_back_after_being_left_out': len(put_back),
                       'put_back_by_check': dict(sorted(put_back_by_check.items())),
                       'put_back_by_noetic': dict(sorted(put_back_by_noetic.items())),
                       'dropped_by_this_program_not_marked_by_the_checker': sum(
                           1 for entries in run.all[team].values() for e in entries if e.drop and not e.checker_dropped),
                       'records_for_passages_not_in_the_passage_file': sum(1 for pid in run.records[team] if pid not in run.P),
                       'duplicates_removed': status['duplicate'],
                       'twins_written_by_the_labeler_removed': status['twin_written'],
                       'held_entries_ruled_out': status['ruled_out'],
                       'left_out_label_not_found_old_mapping': status['left_out'],
                       'program_made_twins': sum(len(v) for p, v in run.twins[team].items() if p in ids),
                       'passages_not_labeled': run.unlabeled[team],
                       'drops_by_check': dict(sorted(drops_by_check[team].items())),
                       'drops_by_noetic': dict(sorted(drops_by_noetic[team].items())),
                       'reasks_by_check': dict(sorted(reasks_by_check[team].items())),
                       'reasks_by_noetic': dict(sorted(reasks_by_noetic[team].items()))}
    invalid = []
    validity = {'too_many_passages_not_labeled': False, 'team_A_too_many_entries_dropped': False,
                'team_B_too_many_entries_dropped': False}
    unlabeled_share = ratio(len(run.excluded), len(run.P))
    if unlabeled_share is not None and unlabeled_share > MAX_UNLABELED_SHARE:
        validity['too_many_passages_not_labeled'] = True
        invalid.append('%d of %d passages were not labeled by both teams (%.4f, over %.2f)'
                       % (len(run.excluded), len(run.P), unlabeled_share, MAX_UNLABELED_SHARE))
    for team in 'AB':
        share = teams[team]['dropped_share']
        if share is not None and share > MAX_DROPPED_SHARE:
            validity['team_%s_too_many_entries_dropped' % team] = True
            invalid.append('team %s: %d of %d entries dropped (%.4f, over %.2f)'
                           % (team, teams[team]['dropped_total'], teams[team]['entries_sent'], share, MAX_DROPPED_SHARE))
    valid = not invalid

    # ----- Table 1 and Table 2 -----
    spans = run.intervals(bar)
    table_1, table_2, ceilings, reason_records, side_by_side = {}, {}, {}, [], []
    for n in NOETICS:
        row = bar[n]
        records, ceiling, pointing = run.reasons_and_ceiling(n, row)
        reason_records += records
        side_by_side += pointing
        ceilings[n] = ceiling
        outside_rows = ['held ' + n, 'uncertain ' + n, 'ambiguous ' + n]
        outside_rows += ['^9 reached by reasoning'] if n == '^9' else []
        outside_rows += ['^6 clue'] if n == '^6' else []
        outside_rows = [name for name in outside_rows if name in nobar]
        detail = {name: nobar[name].A + nobar[name].B - nobar[name].M for name in outside_rows}
        inside, outside = row.A + row.B - row.M, sum(detail.values())
        codes = sorted({e.held_under or 'no code given' for name in outside_rows if name.startswith('held')
                        for r in nobar[name].per.values() for e in r.ea + r.eb + r.da + r.db})
        dropped_n = sum(len(r.da) + len(r.db) for name in [n] + outside_rows
                        for r in (bar[n] if name == n else nobar[name]).per.values())
        scope = ('clear entries only; %d entries held under codes %s; %d clue entries; %d uncertain entries; '
                 '%d reached by reasoning; %d ambiguous; %d dropped; not covered'
                 % (detail.get('held ' + n, 0), ', '.join(codes) if codes else 'none', detail.get('^6 clue', 0) if n == '^6' else 0,
                    detail.get('uncertain ' + n, 0), detail.get('^9 reached by reasoning', 0) if n == '^9' else 0,
                    detail.get('ambiguous ' + n, 0), dropped_n))
        word = outcome_word(row.cases, row.absences, row.E, row.kappa, inside, outside)
        line = {'cases': row.cases, 'absences': row.absences, 'entries_A': row.A, 'entries_B': row.B, 'matched': row.M,
                'only_A_extra_for_A_missing_from_B': row.only_A, 'only_B_extra_for_B_missing_from_A': row.only_B,
                'entry_agreement_E': row.E, 'E_interval95': spans[n]['E'],
                'A_share_matched': row.share_A, 'A_share_interval95': spans[n]['share_A'],
                'B_share_matched': row.share_B, 'B_share_interval95': spans[n]['share_B'],
                'fully_matched_cases': row.fully_matched, 'cases_with_a_match_and_leftovers': row.match_and_leftovers,
                'cases_with_no_match': row.no_match, 'old_view_cases_with_at_least_one_matched_pair': row.with_a_match,
                'kappa': row.kappa, 'kappa_interval95': spans[n]['kappa'],
                'dropped_kept_in_row_A': sum(len(r.da) for r in row.per.values()),
                'dropped_kept_in_row_B': sum(len(r.db) for r in row.per.values()),
                'entries_outside_the_bar_row_A': sum(nobar[name].A for name in outside_rows),
                'entries_outside_the_bar_row_B': sum(nobar[name].B for name in outside_rows),
                'inside_the_bar_row_matched_plus_only_A_plus_only_B': inside,
                'outside_the_bar_row_matched_plus_only_A_plus_only_B': outside, 'outside_by_row': detail,
                'E_interval_reaches_below_the_bar': bool(spans[n]['E'][0] is not None and spans[n]['E'][0] < BAR_ENTRY_AGREEMENT),
                'kappa_interval_reaches_below_the_bar': bool(spans[n]['kappa'][0] is not None and spans[n]['kappa'][0] < BAR_KAPPA),
                'scope': scope}
        if run.rescored:
            line['outcome'] = OUTCOME_NO_BAR
        elif run.mode != 'verdict':
            line['outcome'], line['rule_would_give'] = NOT_A_VERDICT, word
        elif not valid:
            line['outcome'], line['rule_would_give'] = INVALID_RUN, word
        else:
            line['outcome'] = word
        table_1[n] = line
        table_2[n] = {}
        for team in 'AB':
            mine = [r for r in records if r['team'] == team]
            cells = collections.Counter(r['reason'] for r in mine)
            field = collections.Counter(r['detail'] for r in mine if r['reason'] == 'FIELD')
            other = collections.Counter(r['detail'] for r in mine if r['reason'] == 'OTHER_NOETIC')
            pointing_sum = cells['FIELD'] + cells['START'] + (cells['OTHER_LABEL'] if n in TIED else 0)
            table_2[n][team] = {
                'entries': row.A if team == 'A' else row.B, 'unmatched': len(mine),
                'cells': {name: cells[name] for name in REASONS},
                'FIELD_split': {'R3 related thing': field['R3 related thing'], 'R4 measure': field['R4 measure']},
                'OTHER_NOETIC_by_other_Noetic': dict(sorted(other.items())),
                'sums': {'pointing': pointing_sum,
                         'same_evidence_other_label_not_called_pointing': 0 if n in TIED else cells['OTHER_LABEL'],
                         'presence': cells['STATUS'] + cells['OTHER_THING'] + cells['ABSENT'],
                         'role_mix_up': cells['OTHER_NOETIC'], 'format': cells['DROPPED'] + cells['FACES_A_DROP']},
                'tagged_clear_against_a_kind_ruled_out': sum(1 for r in mine if r['entry'].tags)}

    # ----- Table 3: rows with no bar -----
    table_3 = collections.OrderedDict()
    for name, row in nobar.items():
        n = row.noetic
        line = dict(row.counts(), outcome=OUTCOME_NO_BAR)
        if name != run.other_five_row:
            wrote_clear = {'A': 0, 'B': 0}
            for pid, pr in row.per.items():
                for team, mine in (('A', pr.ua), ('B', pr.ub)):
                    clear_other = [y for y in run.located('B' if team == 'A' else 'A', pid) if y.cls == n]
                    for x in mine:
                        if any(run.parts(n, x, y)[0] and run.parts(n, x, y)[1] for y in clear_other):
                            wrote_clear[team] += 1
            line['unmatched_A_that_B_wrote_as_clear'] = wrote_clear['A']
            line['unmatched_B_that_A_wrote_as_clear'] = wrote_clear['B']
        if name.startswith('held'):
            pairs = [pair for pr in row.per.values() for pair in pr.pairs]
            line['matched_pairs_with_the_same_code'] = sum(1 for x, y in pairs if x.held_under == y.held_under)
            line['matched_pairs_with_different_codes'] = sum(1 for x, y in pairs if x.held_under != y.held_under)
            line['by_code'] = collections.OrderedDict()
            for code in [c for c in HOLD_CODES if n in HOLD_CODES[c]]:
                a = sum(1 for pr in row.per.values() for e in pr.ea + pr.da if e.held_under == code)
                b = sum(1 for pr in row.per.values() for e in pr.eb + pr.db if e.held_under == code)
                same = sum(1 for x, y in pairs if x.held_under == code and y.held_under == code)
                line['by_code'][code] = {
                    'A': a, 'B': b, 'M': same, 'only_A': a - same, 'only_B': b - same, 'E': ratio(same, a + b - same),
                    'A_paired_with_another_code': sum(1 for x, y in pairs if x.held_under == code and y.held_under != code),
                    'B_paired_with_another_code': sum(1 for x, y in pairs if y.held_under == code and x.held_under != code)}
        table_3[name] = line

    # ----- Table 4: checks on the measure -----
    floor = run.shuffle_floor(bar)
    table_4 = {}
    for n in NOETICS:
        pooled_classes = [n] + (['held ' + n] if n in HELD_NOETICS else [])
        t5 = twins_for(n)
        table_4[n] = {
            'all_pointed_entries_clear_and_held_pooled': run.row('pooled', pooled_classes, n, twins=t5).counts(),
            'pointing_ceiling': ceilings[n],
            'E_start_tolerance_0': run.row('tol 0', [n], n, tolerance=0, twins=t5).counts(),
            'E_no_start_rule': run.row('no start rule', [n], n, tolerance=None, twins=t5).counts(),
            'old_view_cases_with_at_least_one_matched_pair': bar[n].with_a_match,
            'v12_word_test_on_the_labels': run.row('v1.2 word test', [n], n, twins=t5,
                                                   label_test=lambda x, y: v12_word_test(x.label, y.label)).counts(),
            'exact_same_span': run.row('exact span', [n], n, twins=t5,
                                       label_test=lambda x, y: bool(set(x.L) & set(y.L))).counts(),
            'role_shuffle_floor': floor[n]}
    table_4['^4']['without_no_impression_measures'] = run.row(
        '^4 without no-impression words', ['^4'], '^4',
        keep=lambda e: not (set(WORD.findall(e.measure.lower())) & NO_IMPRESSION_WORDS)).counts()
    part_alone = run.row('^6 part alone', ['^6'], '^6', skip_whole=True)
    table_4['^6']['matched_on_the_part_alone_whole_ignored'] = part_alone.counts()

    # ----- Table 5: health -----
    table_5 = {'per_team_and_noetic': {}, 'matched_pairs_by_label_start_gap': {}, 'bystander_minds': {}}
    for team in 'AB':
        table_5['per_team_and_noetic'][team] = {}
        for n in NOETICS:
            mine = [e for pid in ids for e in run.located(team, pid) if e.noetic == n]
            words = [len(e.label.split()) for e in mine]
            sentences = [e.support_sentences for e in mine if e.support_sentences]
            table_5['per_team_and_noetic'][team][n] = {
                'entries_in_rows': len(mine),
                'label_words_median': statistics.median(words) if words else None, 'label_words_largest': max(words) if words else None,
                'support_sentences_median': statistics.median(sentences) if sentences else None,
                'support_sentences_largest': max(sentences) if sentences else None,
                'labels_with_more_than_one_candidate_place': sum(1 for e in mine if len(e.L) > 1),
                'no_fuller_name_uses': sum(1 for e in mine if e.no_fuller_name)}
    for n in NOETICS:
        gaps = collections.Counter(start_gap(run.P[pid], x, y) for pid, pr in bar[n].per.items() for x, y in pr.pairs)
        table_5['matched_pairs_by_label_start_gap'][n] = {'0 words': gaps[0], '1 word': gaps[1], '2 words': gaps[2]}
    for team in 'AB':
        count = 0
        for pid, pr in bar['^1'].per.items():
            for x in (pr.ua if team == 'A' else pr.ub):
                if not any(e is not x and e.mind == x.label and e.noetic != '^1' for e in run.all[team].get(pid, [])):
                    count += 1
        table_5['bystander_minds'][team] = count

    # ----- Table 6: by the writer's kind (description only) -----
    table_6 = {}
    if run.kinds:
        for kind in sorted({run.kinds.get(pid, 'no kind given') for pid in ids}):
            pids = {pid for pid in ids if run.kinds.get(pid, 'no kind given') == kind}
            table_6[kind] = {'passages': len(pids), 'table_1': {}, 'table_2': {}}
            for n in NOETICS:
                sub = bar[n].restrict(pids, len(pids))
                table_6[kind]['table_1'][n] = dict(sub.counts(), cases=sub.cases, absences=sub.absences,
                                                   fully_matched_cases=sub.fully_matched)
                table_6[kind]['table_2'][n] = {
                    team: dict(sorted(collections.Counter(r['reason'] for r in reason_records if r['noetic'] == n
                                                          and r['team'] == team and r['pid'] in pids).items()))
                    for team in 'AB'}

    # ----- listing, agreement on none of these, guide problems -----
    reason_of = {r['entry'].uid: r for r in reason_records}
    listing = []
    for name, row in list(bar.items()) + list(nobar.items()):
        if name == run.other_five_row:
            continue
        for pid, pr in sorted(row.per.items()):
            for team, mine in (('A', pr.ua + pr.da), ('B', pr.ub + pr.db)):
                others = run.located('B' if team == 'A' else 'A', pid)
                for x in mine:
                    record = reason_of.get(x.uid)
                    listing.append({'passage': pid, 'team': team, 'class': name, 'label': x.label, 'support': x.support,
                                    'measure': x.measure, 'mind': x.mind, 'relative_to': x.relative_to,
                                    'held_under': x.held_under,
                                    'reason': record['reason'] if record else ('DROPPED' if x.failed else 'row with no bar'),
                                    'reason_detail': record['detail'] if record else (','.join(x.failed) or None),
                                    'tags': list(x.tags), 'other_team_nearest_entry': nearest_other(x, others)})
    none_a = {pid: bool(run.records['A'][pid].get('none_of_these')) for pid in ids}
    none_b = {pid: bool(run.records['B'][pid].get('none_of_these')) for pid in ids}
    none_of_these = {'team_A': sum(none_a.values()), 'team_B': sum(none_b.values()),
                     'both': sum(1 for pid in ids if none_a[pid] and none_b[pid]),
                     'agree': sum(1 for pid in ids if none_a[pid] == none_b[pid]), 'passages': N}
    guide_problems = [{'passage': pid, 'team': team, 'report': record.get('guide_problem')}
                      for team in 'AB' for pid, record in sorted(run.records[team].items())
                      if pid in run.P and record.get('guide_problem')]
    # Guide rule 14: a report that a Part A saying pointed to a Noetic and a numbered rule said to write no entry
    # starts with fixed words, so that these reports can be counted apart. They are counted, never judged.
    saying = {team: sum(1 for g in guide_problems if g['team'] == team and isinstance(g['report'], str)
                        and g['report'].strip().startswith(SAYING_AGAINST_RULE)) for team in 'AB'}
    guide_problem_counts = {'all_reports': {team: sum(1 for g in guide_problems if g['team'] == team) for team in 'AB'},
                            'reports_that_start_with_saying_against_rule': saying}
    per_passage = {pid: {'rows': {}, 'reasons': {}} for pid in ids}
    for name, row in list(bar.items()) + list(nobar.items()):
        for pid, pr in row.per.items():
            per_passage[pid]['rows'][name] = {'A': pr.a, 'B': pr.b, 'M': pr.m}
    for r in reason_records:
        per_passage[r['pid']]['reasons'].setdefault(r['noetic'], []).append(r['team'] + ':' + r['reason'])
    for value in per_passage.values():
        value['reasons'] = {n: sorted(v) for n, v in value['reasons'].items()}

    report = {
        'schema': 'casalescence/label-agreement-v2-report/1', 'mode': run.mode, 'is_a_verdict': run.mode == 'verdict' and valid
        and not run.rescored,
        'what_this_is': {'verdict': 'A verdict run on a sealed set.', 'practice': 'Practice. Not a verdict. Not a claim.',
                         'old': 'Program check part 1: arithmetic on spent labels. Never a verdict.',
                         'fixture': 'A program check on made-up passages. Never a verdict.'}[run.mode],
        'proposal_notice': 'Bars, hold table, outcome words, the ^5 bar row and seal conditions are proposals until the '
                           'owner signs them before the seal. Verdict mode refuses a seal with no owner sign-off record '
                           'in it. It cannot tell whether a signature is real.',
        'constants': {'BAR_ENTRY_AGREEMENT': BAR_ENTRY_AGREEMENT, 'BAR_KAPPA': BAR_KAPPA, 'MIN_CASES': MIN_CASES,
                      'MIN_ABSENCES': MIN_ABSENCES, 'MAX_UNLABELED_SHARE': MAX_UNLABELED_SHARE,
                      'MAX_DROPPED_SHARE': MAX_DROPPED_SHARE, 'START_TOLERANCE_WORDS': START_TOLERANCE_WORDS,
                      'RESAMPLES': RESAMPLES, 'SEED_INTERVALS': SEED_INTERVALS, 'SHUFFLE_ROUNDS': SHUFFLE_ROUNDS,
                      'SEED_SHUFFLE': SEED_SHUFFLE, 'SEED_OWNER_SAMPLE': SEED_OWNER_SAMPLE,
                      'SEAL_S2_MAX_DROPPED_SHARE': SEAL_S2_MAX_DROPPED_SHARE, 'SEAL_S4_KIND': SEAL_S4_KIND,
                      'SEAL_S4_MIN_E': SEAL_S4_MIN_E, 'SEAL_S5_MIN_WHOLE_SHARE': SEAL_S5_MIN_WHOLE_SHARE,
                      'FIVE_BAR_ROW': FIVE_BAR_ROW, 'BAR_ROW_5_WITH_TWINS': BAR_ROW_5_WITH_TWINS,
                      'HOLD_CODES': {k: list(v) for k, v in HOLD_CODES.items()}},
        'five_bar_row': {'the_bar_row_for_^5': '^5 with the program-made twins' if run.twins_in_bar else
                         '^5 as the labelers wrote it', 'the_other_^5_row_printed_with_no_bar': None if run.old
                         else run.other_five_row},
        'owner_ruling': dict(run.ruling), 'rescored_under_an_owner_ruling': run.rescored,
        'passages': {'total': len(run.P), 'analysed': N, 'not_labeled_by_both_teams': run.excluded,
                     'not_labeled_share': unlabeled_share, 'sentences_total': sum(len(p.sentences) for p in run.P.values()),
                     'sentences_per_passage': {pid: len(run.P[pid].sentences) for pid in run.order}},
        'teams': {'A': teams['A'], 'B': teams['B']},
        'run_is_valid': valid, 'why_invalid': invalid, 'validity_rules_broken': validity,
        'table_1_bar_rows': table_1, 'table_2_reasons': table_2, 'table_3_rows_with_no_bar': table_3,
        'table_4_checks_on_the_measure': table_4, 'table_5_health': table_5, 'table_6_by_writer_kind': table_6,
        'agreement_on_none_of_these': none_of_these, 'guide_problem_reports': guide_problems,
        'guide_problem_counts': guide_problem_counts,
        'per_passage': {pid: per_passage[pid] for pid in sorted(per_passage)},
        'listing_of_unmatched_entries': listing}
    extras = {'bar': bar, 'nobar': nobar, 'part_alone': part_alone, 'side_by_side': side_by_side,
              'reason_records': reason_records}
    return report, extras


def seal_conditions(run, report, extras, s1=None):
    """S1 to S5. Process checks read off a practice pass. Anything other than PASS is not a pass."""
    out = collections.OrderedDict()
    out['S1'] = s1 or {'status': 'NOT_EVALUATED', 'note': 'Give --fixture-dir and --old-dir to run the program checks.'}
    shares = {t: report['teams'][t]['dropped_share'] for t in 'AB'}
    if any(v is None for v in shares.values()):
        out['S2'] = {'status': 'NOT_EVALUATED', 'note': 'A team sent no entry.', 'dropped_share': shares}
    else:
        out['S2'] = {'status': 'PASS' if all(v < SEAL_S2_MAX_DROPPED_SHARE for v in shares.values()) else 'FAIL',
                     'dropped_share': shares, 'must_be_under': SEAL_S2_MAX_DROPPED_SHARE}
    reports = report['guide_problem_reports']
    out['S3'] = {'status': 'PASS' if not reports else 'NEEDS_A_READER',
                 'note': 'No labeler wrote a guide problem.' if not reports else
                 'The program cannot tell whether a report names two rules that order opposite things. '
                 'A person must read every report listed. Until then S3 is not passed.',
                 'reports': reports}
    k1 = {pid for pid in run.ids if run.kinds.get(pid) == SEAL_S4_KIND}
    if not run.kinds or not k1:
        out['S4'] = {'status': 'NOT_EVALUATED', 'note': 'No passage of kind %s is known. Give --kinds.' % SEAL_S4_KIND}
    else:
        values = {n: extras['bar'][n].restrict(k1, len(k1)).E for n in ('^8', '^9')}
        ok = all(v is not None and v >= SEAL_S4_MIN_E for v in values.values())
        out['S4'] = {'status': 'PASS' if ok else 'FAIL', 'passages_of_kind': len(k1), 'E': values,
                     'must_be_at_least': SEAL_S4_MIN_E,
                     'counts': {n: extras['bar'][n].restrict(k1, len(k1)).counts() for n in ('^8', '^9')}}
    parts, whole = extras['part_alone'].M, extras['bar']['^6'].M
    share = ratio(whole, parts)
    out['S5'] = {'status': 'NOT_EVALUATED' if share is None else 'PASS' if share >= SEAL_S5_MIN_WHOLE_SHARE else 'FAIL',
                 'pairs_whose_parts_match': parts, 'of_those_also_matching_on_the_whole': whole, 'share': share,
                 'must_be_at_least': SEAL_S5_MIN_WHOLE_SHARE}
    return out


# ----------------------------------------------------------------------------------------------------
# printing
# ----------------------------------------------------------------------------------------------------
def print_header(run, report):
    banner = {'verdict': 'VERDICT MODE. A sealed set. The gate found no problem: the record is a seal with an owner '
                         'sign-off record in it, the five hashes match, and both label files went through the sealed checker.',
              'practice': 'PRACTICE MODE. Not a verdict. Not a claim.',
              'old': 'OLD LABELS MODE (program check part 1). Arithmetic on spent labels. Never a verdict.',
              'fixture': 'FIXTURE MODE (a program check). Made-up passages. Never a verdict.'}[run.mode]
    print(banner)
    seal = report.get('seal_check') or {}
    for role, item in seal.get('files', {}).items():
        print('    sealed %s: %s sha256 %s' % (role, item['file'], item['sha256']))
    if seal:
        print('    owner sign-off record in the seal: sha256 %s' % seal.get('owner_signoff_sha256'))
        print('    items the owner changed: %s | items the owner struck out: %s'
              % (', '.join(seal.get('items_changed_by_the_owner') or []) or 'none',
                 ', '.join(seal.get('items_struck_out_by_the_owner') or []) or 'none'))
        print('    hold table: %s' % seal.get('ruling'))
    for role, item in (report.get('made_with') or {}).items():
        if isinstance(item, dict) and item.get('sha256') and run.mode == 'practice':
            print('    made with %s: %s sha256 %s' % (role, item.get('file') or item.get('folder'), item['sha256']))
    for team, gate in sorted((report.get('label_gate') or {}).items()):
        print('    team %s labels: %d rows, %d final records checked again with the checker given, %d entries; rows not '
              'final %s' % (team, gate['rows'], gate['records_checked_again'], gate['entries_checked_again'],
                            gate['rows_not_final'] or 'none'))
    print('Bars, outcome words and the ^5 bar row are proposals until the owner signs them before the seal. The bar row '
          'for ^5 is: %s.' % report['five_bar_row']['the_bar_row_for_^5'])
    p = report['passages']
    print('passages %d | analysed %d | not labeled by both teams %d %s | sentences %d'
          % (p['total'], p['analysed'], len(p['not_labeled_by_both_teams']), p['not_labeled_by_both_teams'][:12], p['sentences_total']))
    for team in 'AB':
        t = report['teams'][team]
        print('team %s: entries sent %d | in rows %d | dropped, kept in a row %d | dropped, no row %d | dropped share %s | '
              'duplicates removed %d | twins written by the labeler removed %d | program-made twins %d | ruled out %d%s'
              % (team, t['entries_sent'], t['in_rows'], t['dropped_kept_in_a_row'], t['dropped_no_row'],
                 'n/a' if t['dropped_share'] is None else '%.4f' % t['dropped_share'], t['duplicates_removed'],
                 t['twins_written_by_the_labeler_removed'], t['program_made_twins'], t['held_entries_ruled_out'],
                 ' | left out, label not found (old mapping) %d' % t['left_out_label_not_found_old_mapping'] if run.old else ''))
    if report['run_is_valid']:
        print('RUN VALID: no more than %.2f of passages unlabeled, no more than %.2f of a team\'s entries dropped.'
              % (MAX_UNLABELED_SHARE, MAX_DROPPED_SHARE))
    else:
        print('INVALID: ' + ' ; '.join(report['why_invalid']))
        print('INVALID means: no outcome word of this run is a verdict.')
    if report['rescored_under_an_owner_ruling']:
        print('RE-SCORED UNDER AN OWNER RULING %s. Every row prints %s. A verdict under a ruling needs new passages.'
              % ({k: v for k, v in report['owner_ruling'].items() if v != 'open'}, OUTCOME_NO_BAR))


def outcome_text(line):
    if 'rule_would_give' in line:
        return '%s (the rule would give %s)' % (line['outcome'], line['rule_would_give'])
    return line['outcome']


def print_table_1(report):
    print()
    print('TABLE 1. Bar rows: clear entries only. Proposed bars: E at least %.2f, kappa at least %.2f, at least %d cases '
          'and %d absences.' % (BAR_ENTRY_AGREEMENT, BAR_KAPPA, MIN_CASES, MIN_ABSENCES))
    print('Noetic | cases | absences | entries A | entries B | matched | only A (extra for A, missing from B) | '
          'only B (extra for B, missing from A) | E [95%] | A share [95%] | B share [95%] | fully matched cases | '
          'match and leftovers | no match | kappa [95%] | dropped kept A | dropped kept B | outside the bar row A | '
          'outside the bar row B | outcome')
    for n, r in report['table_1_bar_rows'].items():
        print('%s | %d | %d | %d | %d | %d | %d | %d | %s %s | %s %s | %s %s | %d | %d | %d | %s %s | %d | %d | %d | %d | %s'
              % (n, r['cases'], r['absences'], r['entries_A'], r['entries_B'], r['matched'],
                 r['only_A_extra_for_A_missing_from_B'], r['only_B_extra_for_B_missing_from_A'],
                 f3(r['entry_agreement_E']), interval_text(r['E_interval95']), f3(r['A_share_matched']),
                 interval_text(r['A_share_interval95']), f3(r['B_share_matched']), interval_text(r['B_share_interval95']),
                 r['fully_matched_cases'], r['cases_with_a_match_and_leftovers'], r['cases_with_no_match'],
                 f3(r['kappa']), interval_text(r['kappa_interval95']), r['dropped_kept_in_row_A'], r['dropped_kept_in_row_B'],
                 r['entries_outside_the_bar_row_A'], r['entries_outside_the_bar_row_B'], outcome_text(r)))
        notes = []
        if r['E_interval_reaches_below_the_bar']:
            notes.append('the E interval reaches below %.2f' % BAR_ENTRY_AGREEMENT)
        if r['kappa_interval_reaches_below_the_bar']:
            notes.append('the kappa interval reaches below %.2f' % BAR_KAPPA)
        print('    scope: %s | inside the bar row %d, outside %d%s'
              % (r['scope'], r['inside_the_bar_row_matched_plus_only_A_plus_only_B'],
                 r['outside_the_bar_row_matched_plus_only_A_plus_only_B'], ' | ' + '; '.join(notes) if notes else ''))


def print_table_2(report):
    print()
    print('TABLE 2. Why each unmatched bar-row entry was unmatched. One cell per entry. Reasons describe; they change no count.')
    print('Noetic | team | entries | unmatched | ' + ' | '.join(REASONS))
    for n, both in report['table_2_reasons'].items():
        for team in 'AB':
            t = both[team]
            print('%s | %s | %d | %d | %s' % (n, team, t['entries'], t['unmatched'],
                                              ' | '.join(str(t['cells'][name]) for name in REASONS)))
            s = t['sums']
            print('    FIELD split: related thing %d, measure %d | OTHER_NOETIC by Noetic %s | sums: pointing %d; '
                  'same evidence, other label (not called pointing) %d; presence %d; role mix-up %d; format %d%s'
                  % (t['FIELD_split']['R3 related thing'], t['FIELD_split']['R4 measure'], t['OTHER_NOETIC_by_other_Noetic'],
                     s['pointing'], s['same_evidence_other_label_not_called_pointing'], s['presence'], s['role_mix_up'],
                     s['format'], ' | clear against a kind ruled out %d' % t['tagged_clear_against_a_kind_ruled_out']
                     if t['tagged_clear_against_a_kind_ruled_out'] else ''))
    print('Beside the table: duplicates removed A %d, B %d | twins written by the labeler removed A %d, B %d'
          % (report['teams']['A']['duplicates_removed'], report['teams']['B']['duplicates_removed'],
             report['teams']['A']['twins_written_by_the_labeler_removed'],
             report['teams']['B']['twins_written_by_the_labeler_removed']))


def print_table_3(report):
    print()
    print('TABLE 3. Rows with no bar. Every one of them: %s.' % OUTCOME_NO_BAR)
    print('class | entries A | entries B | matched | only A | only B | E | unmatched A that B wrote as clear | '
          'unmatched B that A wrote as clear | held pairs with the same code | with different codes')
    always = ('^9 reached by reasoning', 'uncertain ^8', 'uncertain ^9', '^6 clue', '^5 with twins', '^5 without twins')
    for name, r in report['table_3_rows_with_no_bar'].items():
        if not (r['A'] or r['B']) and name not in always and not name.startswith('held'):
            continue
        print('%s | %d | %d | %d | %d | %d | %s | %s | %s | %s | %s'
              % (name, r['A'], r['B'], r['M'], r['only_A'], r['only_B'], f3(r['E']),
                 r.get('unmatched_A_that_B_wrote_as_clear', 'n/a'), r.get('unmatched_B_that_A_wrote_as_clear', 'n/a'),
                 r.get('matched_pairs_with_the_same_code', 'n/a'), r.get('matched_pairs_with_different_codes', 'n/a')))
        for code, c in (r.get('by_code') or {}).items():
            print('    %s | %d | %d | %d | %d | %d | %s | paired with another code: A %d, B %d'
                  % (code, c['A'], c['B'], c['M'], c['only_A'], c['only_B'], f3(c['E']), c['A_paired_with_another_code'],
                     c['B_paired_with_another_code']))
    print('(rows with no entry are left out of this print, except the ones always shown; the report file has all of them)')


def print_table_4(report):
    print()
    print('TABLE 4. Reported beside the primary numbers. No bar. None of these lines counts toward an outcome.')

    def cell(c):
        return '%d / %d / %d = %s' % (c['A'], c['B'], c['M'], f3(c['E']))
    for n, t in report['table_4_checks_on_the_measure'].items():
        c = t['pointing_ceiling']
        print('%s | all pointed entries (clear and held pooled) A / B / M = E: %s' % (n, cell(t['all_pointed_entries_clear_and_held_pooled'])))
        print('    pointing ceiling %s with %d one-to-one pointing pairs %s | with OTHER_LABEL allowed everywhere %s with %d pairs '
              '(not all of this is pointing)' % (f3(c['ceiling']), c['pointing_pairs'], c['pairs_by_kind'],
                                                  f3(c['ceiling_other_label_everywhere']), c['pairs_other_label_everywhere']))
        print('    start-tolerance check: E at tolerance 0 %s | with no start rule %s'
              % (f3(t['E_start_tolerance_0']['E']), f3(t['E_no_start_rule']['E'])))
        print('    the old view: cases with at least one matched pair %d | v1.2 word test on the labels %s | exact same span %s'
              % (t['old_view_cases_with_at_least_one_matched_pair'], cell(t['v12_word_test_on_the_labels']), cell(t['exact_same_span'])))
        s = t['role_shuffle_floor']
        print('    role-shuffle floor over %d rounds: mean E %s, lowest %s, highest %s'
              % (s['rounds'], f3(s['mean_E']), f3(s['lowest_E']), f3(s['highest_E'])))
        if 'without_no_impression_measures' in t:
            print('    the ^4 row without measures that hold a no-impression word: %s' % cell(t['without_no_impression_measures']))
        if 'matched_on_the_part_alone_whole_ignored' in t:
            print('    ^6 matched on the part alone, the whole ignored: %s' % cell(t['matched_on_the_part_alone_whole_ignored']))
    x = report['agreement_on_none_of_these']
    print("agreement on 'none of these': team A %d, team B %d, both %d, same answer in %d of %d passages"
          % (x['team_A'], x['team_B'], x['both'], x['agree'], x['passages']))


def print_table_5(report):
    print()
    print('TABLE 5. Health.')
    print('team | Noetic | entries in rows | label words median / largest | support sentences median / largest | '
          'labels with more than one candidate place | no_fuller_name uses')
    for team, by_n in report['table_5_health']['per_team_and_noetic'].items():
        for n, t in by_n.items():
            print('%s | %s | %d | %s / %s | %s / %s | %d | %d'
                  % (team, n, t['entries_in_rows'], t['label_words_median'], t['label_words_largest'],
                     t['support_sentences_median'], t['support_sentences_largest'],
                     t['labels_with_more_than_one_candidate_place'], t['no_fuller_name_uses']))
    print('matched bar-row pairs by how far apart the two labels start (0 / 1 / 2 words): '
          + ' ; '.join('%s %d / %d / %d' % (n, g['0 words'], g['1 word'], g['2 words'])
                       for n, g in report['table_5_health']['matched_pairs_by_label_start_gap'].items()))
    print('unmatched ^1 Minds that carry no other entry (bystanders): team A %d, team B %d'
          % (report['table_5_health']['bystander_minds']['A'], report['table_5_health']['bystander_minds']['B']))
    for team in 'AB':
        t = report['teams'][team]
        print('team %s | re-asks per check %s | re-asks per Noetic %s | drops per check %s | drops per Noetic %s | '
              'dropped by this program though the checker had not marked them %d'
              % (team, t['reasks_by_check'], t['reasks_by_noetic'], t['drops_by_check'], t['drops_by_noetic'],
                 t['dropped_by_this_program_not_marked_by_the_checker']))
        print('team %s | entries that failed a check, were left out of a later try and were put back as dropped: %d | '
              'per check %s | per Noetic %s' % (team, t['put_back_after_being_left_out'], t['put_back_by_check'],
                                                t['put_back_by_noetic']))
    g = report['guide_problem_counts']
    print("guide_problem reports: team A %d, team B %d | of those, reports that start with '%s' (rule 14): team A %d, "
          'team B %d' % (g['all_reports']['A'], g['all_reports']['B'], SAYING_AGAINST_RULE,
                         g['reports_that_start_with_saying_against_rule']['A'],
                         g['reports_that_start_with_saying_against_rule']['B']))


def print_table_6(report):
    if not report['table_6_by_writer_kind']:
        return
    print()
    print("TABLE 6. Tables 1 and 2 by the writer's kind. Description only.")
    for kind, t in report['table_6_by_writer_kind'].items():
        print('%s (%d passages)' % (kind, t['passages']))
        for n in NOETICS:
            c = t['table_1'][n]
            if c['A'] or c['B']:
                print('    %s | cases %d | A %d | B %d | matched %d | only A %d | only B %d | E %s | fully matched %d | '
                      'reasons A %s | reasons B %s' % (n, c['cases'], c['A'], c['B'], c['M'], c['only_A'], c['only_B'], f3(c['E']),
                                                         c['fully_matched_cases'], t['table_2'][n]['A'], t['table_2'][n]['B']))


def print_seal_conditions(conditions):
    print()
    print('SEAL CONDITIONS S1 to S5 (proposals; process checks, not claims). Only PASS is a pass.')
    for name, c in conditions.items():
        rest = {k: v for k, v in c.items() if k not in ('status', 'reports', 'lines')}
        print('%s: %s | %s' % (name, c['status'], json.dumps(rest, ensure_ascii=False)))
        for item in c.get('reports') or []:
            print('    guide problem, passage %s, team %s: %s' % (item['passage'], item['team'], item['report']))


def owner_sample(run, report, extras):
    """The owner's reading sample, drawn with a fixed seed."""
    rng = random.Random(SEED_OWNER_SAMPLE)
    bar_lines = [x for x in report['listing_of_unmatched_entries'] if x['class'] in NOETICS]
    unmatched = []
    for team in 'AB':
        groups = collections.OrderedDict()
        for reason in REASONS:
            group = [x for x in bar_lines if x['team'] == team and x['reason'] == reason]
            rng.shuffle(group)
            if group:
                groups[reason] = group
        taken = 0
        while taken < 15 and any(groups.values()):            # one from each reason in turn
            for reason in list(groups):
                if groups[reason] and taken < 15:
                    item = groups[reason].pop()
                    unmatched.append(dict(item, passage_text=run.P[item['passage']].text))
                    taken += 1
    listed = {x['passage'] for x in report['listing_of_unmatched_entries']}
    full = [pid for pid in run.ids if pid not in listed and run.located('A', pid) and run.located('B', pid)]
    chosen = sorted(rng.sample(full, min(20, len(full))))
    pairs = list(extras['side_by_side'])
    picked = rng.sample(pairs, min(20, len(pairs)))
    return {'note': 'For the owner. Drawn with seed %d. 30 unmatched bar-row entries (15 per team, spread over the reasons), '
                    '20 fully matched passages, and up to 20 FIELD, START or OTHER_LABEL pairs side by side.' % SEED_OWNER_SAMPLE,
            'mode': run.mode, 'is_a_verdict': report['is_a_verdict'],
            'unmatched_entries': unmatched,
            'fully_matched_passages': [{'passage': pid, 'text': run.P[pid].text,
                                        'team_A': [e.show() for e in run.located('A', pid)],
                                        'team_B': [e.show() for e in run.located('B', pid)]} for pid in chosen],
            'pointing_pairs_side_by_side': [{'passage': p['pid'], 'text': run.P[p['pid']].text, 'noetic': p['noetic'],
                                             'kind': p['kind'], 'team_A': p['a'].show(), 'team_B': p['b'].show()}
                                            for p in sorted(picked, key=lambda p: (p['pid'], p['noetic']))]}


def matched_pairs_file(run, report, extras):
    """Output for option B: every matched bar-row pair. Nothing held, unmatched, uncertain, clue or dropped is in it."""
    pairs = [{'passage': pid, 'noetic': n, 'team_A': x.show(), 'team_B': y.show()}
             for n in NOETICS for pid, pr in sorted(extras['bar'][n].per.items()) for x, y in pr.pairs]
    return {'note': 'Every matched bar-row pair: the role descriptions two teams agree on. Held, unmatched, uncertain, '
                    'clue and dropped entries are not in this file.',
            'mode': run.mode, 'is_a_verdict': report['is_a_verdict'], 'pairs': pairs}


def score(mode, passages, records_a, records_b, ruling=None, kinds=None, out=None, tables=(1, 2, 3, 4, 5, 6), quiet=False,
          s1=None, seal_info=None, made_with=None, label_gate=None):
    run = Run(mode, passages, records_a, records_b, ruling, kinds)
    report, extras = analyse(run)
    if seal_info:
        report['seal_check'] = seal_info
    if made_with:
        report['made_with'] = made_with       # the sha256 of every file this report was made with
    if label_gate:
        report['label_gate'] = label_gate     # what the label part of the gate counted, per team
    if mode in ('practice', 'fixture'):
        report['seal_conditions'] = seal_conditions(run, report, extras, s1)
    if not quiet:
        print_header(run, report)
        printers = {1: print_table_1, 2: print_table_2, 3: print_table_3, 4: print_table_4, 5: print_table_5, 6: print_table_6}
        for number in tables:
            printers[number](report)
        if mode == 'practice':
            print_seal_conditions(report['seal_conditions'])
    if out:
        out = Path(out)
        write_json(out, report)
        write_json(out.with_name(out.stem + '.matched_pairs.json'), matched_pairs_file(run, report, extras))
        write_json(out.with_name(out.stem + '.owner_sample.json'), owner_sample(run, report, extras))
        if not quiet:
            print()
            print('written: %s, and beside it %s and %s' % (out.name, out.stem + '.matched_pairs.json', out.stem + '.owner_sample.json'))
    return run, report, extras


# ----------------------------------------------------------------------------------------------------
# program checks: the view that FIXTURE_EXPECTED.json is compared with
# ----------------------------------------------------------------------------------------------------
def check_view(report):
    """A plain view of a report for comparing with hand-worked counts. Shares and E are text with 3 decimals."""
    def counts(c):
        return {'A': c['A'], 'B': c['B'], 'M': c['M'], 'only_A': c['only_A'], 'only_B': c['only_B'], 'E': f3(c['E'])}

    def listed(cells, order=None):
        keys = [k for k in (order or sorted(cells)) if cells.get(k)]
        return '; '.join('%s %d' % (k, cells[k]) for k in keys) or 'none'

    row_order = NOETICS + list(report['table_3_rows_with_no_bar'])
    per_passage = {}
    for pid, value in report['per_passage'].items():
        per_passage[pid] = {
            'rows': '; '.join('%s %d/%d/%d' % (name, value['rows'][name]['A'], value['rows'][name]['B'], value['rows'][name]['M'])
                              for name in row_order if name in value['rows']) or 'none',
            'reasons': '; '.join('%s %s' % (n, ' '.join(value['reasons'][n])) for n in NOETICS if n in value['reasons']) or 'none'}
    view = {'sentences_total': report['passages']['sentences_total'],
            'sentences_per_passage': report['passages']['sentences_per_passage'],
            'passages_total': report['passages']['total'], 'passages_analysed': report['passages']['analysed'],
            'passages_not_labeled_by_both_teams': report['passages']['not_labeled_by_both_teams'],
            'run_is_valid': report['run_is_valid'], 'validity_rules_broken': report['validity_rules_broken'],
            'teams': {}, 'rows': {}, 'bar': {}, 'reasons': {}, 'field_split': {},
            'other_noetic': {}, 'ceiling': {}, 'no_bar': {}, 'held_by_code': {}, 'table_4': {}, 'table_5': {},
            'tagged_clear_against_a_kind_ruled_out': {}, 'rescored_under_an_owner_ruling': report['rescored_under_an_owner_ruling'],
            'per_passage': per_passage, 'per_passage_counts': report['per_passage'],
            'none_of_these': report['agreement_on_none_of_these']}
    for team in 'AB':
        t = report['teams'][team]
        view['teams'][team] = {
            'entries_sent': t['entries_sent'], 'dropped_kept_in_a_row': t['dropped_kept_in_a_row'],
            'dropped_no_row': t['dropped_no_row'], 'dropped_total': t['dropped_total'],
            'dropped_share': 'n/a' if t['dropped_share'] is None else '%.4f' % t['dropped_share'],
            'dropped_by_this_program_not_marked_by_the_checker': t['dropped_by_this_program_not_marked_by_the_checker'],
            'duplicates_removed': t['duplicates_removed'],
            'twins_written_by_the_labeler_removed': t['twins_written_by_the_labeler_removed'],
            'program_made_twins': t['program_made_twins'], 'held_entries_ruled_out': t['held_entries_ruled_out'],
            'left_out_label_not_found_old_mapping': t['left_out_label_not_found_old_mapping'],
            'drops_by_check': listed(t['drops_by_check']), 'drops_by_noetic': listed(t['drops_by_noetic']),
            'reasks_by_check': listed(t['reasks_by_check']), 'reasks_by_noetic': listed(t['reasks_by_noetic']),
            'put_back_after_being_left_out': t['put_back_after_being_left_out'],
            'put_back_by_check': listed(t['put_back_by_check']), 'put_back_by_noetic': listed(t['put_back_by_noetic']),
            'passages_not_labeled': t['passages_not_labeled']}
    for n, r in report['table_1_bar_rows'].items():
        view['rows'][n] = {'A': r['entries_A'], 'B': r['entries_B'], 'M': r['matched'],
                           'only_A': r['only_A_extra_for_A_missing_from_B'], 'only_B': r['only_B_extra_for_B_missing_from_A'],
                           'E': f3(r['entry_agreement_E'])}
        view['bar'][n] = {'cases': r['cases'], 'absences': r['absences'], 'fully_matched_cases': r['fully_matched_cases'],
                          'cases_with_a_match_and_leftovers': r['cases_with_a_match_and_leftovers'],
                          'cases_with_no_match': r['cases_with_no_match'],
                          'cases_with_at_least_one_matched_pair': r['old_view_cases_with_at_least_one_matched_pair'],
                          'share_A': f3(r['A_share_matched']), 'share_B': f3(r['B_share_matched']), 'kappa': f3(r['kappa']),
                          'E_interval95': interval_text(r['E_interval95']), 'kappa_interval95': interval_text(r['kappa_interval95']),
                          'dropped_kept_in_row_A': r['dropped_kept_in_row_A'], 'dropped_kept_in_row_B': r['dropped_kept_in_row_B'],
                          'inside': r['inside_the_bar_row_matched_plus_only_A_plus_only_B'],
                          'outside': r['outside_the_bar_row_matched_plus_only_A_plus_only_B'],
                          'outcome': r['outcome'], 'rule_would_give': r.get('rule_would_give', 'not printed')}
        view['reasons'][n] = {team: listed(report['table_2_reasons'][n][team]['cells'], REASONS) for team in 'AB'}
        view['field_split'][n] = {team: listed(report['table_2_reasons'][n][team]['FIELD_split']) for team in 'AB'}
        view['other_noetic'][n] = {team: listed(report['table_2_reasons'][n][team]['OTHER_NOETIC_by_other_Noetic']) for team in 'AB'}
        view['tagged_clear_against_a_kind_ruled_out'][n] = {
            team: report['table_2_reasons'][n][team]['tagged_clear_against_a_kind_ruled_out'] for team in 'AB'}
        c = report['table_4_checks_on_the_measure'][n]['pointing_ceiling']
        view['ceiling'][n] = {'pointing_pairs': c['pointing_pairs'], 'ceiling': f3(c['ceiling']),
                              'pairs_other_label_everywhere': c['pairs_other_label_everywhere'],
                              'ceiling_other_label_everywhere': f3(c['ceiling_other_label_everywhere'])}
        t = report['table_4_checks_on_the_measure'][n]
        view['table_4'][n] = {'pooled_clear_and_held': counts(t['all_pointed_entries_clear_and_held_pooled']),
                              'tolerance_0': counts(t['E_start_tolerance_0']), 'no_start_rule': counts(t['E_no_start_rule']),
                              'v12_word_test': counts(t['v12_word_test_on_the_labels']), 'exact_same_span': counts(t['exact_same_span'])}
        for key in ('without_no_impression_measures', 'matched_on_the_part_alone_whole_ignored'):
            if key in t:
                view['table_4'][n][key] = counts(t[key])
    for name, r in report['table_3_rows_with_no_bar'].items():
        view['rows'][name] = counts(r)
        view['no_bar'][name] = {k: r[k] for k in ('unmatched_A_that_B_wrote_as_clear', 'unmatched_B_that_A_wrote_as_clear',
                                                  'matched_pairs_with_the_same_code', 'matched_pairs_with_different_codes') if k in r}
        for code, c in (r.get('by_code') or {}).items():
            view['held_by_code'][name + ' ' + code] = {k: c[k] for k in ('A', 'B', 'M', 'only_A', 'only_B',
                                                                         'A_paired_with_another_code', 'B_paired_with_another_code')}
    h = report['table_5_health']
    view['table_5'] = {'bystander_minds': h['bystander_minds'], 'matched_pairs_by_label_start_gap': h['matched_pairs_by_label_start_gap'],
                       'labels_with_more_than_one_candidate_place': {
                           team: {n: v['labels_with_more_than_one_candidate_place'] for n, v in by_n.items()
                                  if v['labels_with_more_than_one_candidate_place']} for team, by_n in h['per_team_and_noetic'].items()},
                       'no_fuller_name_uses': {team: sum(v['no_fuller_name_uses'] for v in by_n.values())
                                               for team, by_n in h['per_team_and_noetic'].items()},
                       'label_words_largest': {team: {n: v['label_words_largest'] for n, v in by_n.items() if v['entries_in_rows']}
                                               for team, by_n in h['per_team_and_noetic'].items()},
                       'support_sentences_largest': {team: {n: v['support_sentences_largest'] for n, v in by_n.items()
                                                            if v['support_sentences_largest']}
                                                     for team, by_n in h['per_team_and_noetic'].items()}}
    if 'seal_conditions' in report:
        s = report['seal_conditions']
        view['seal_conditions'] = {'S2': s['S2']['status'], 'S3': s['S3']['status'], 'S3_reports': len(s['S3']['reports']),
                                   'S4': s['S4']['status'], 'S5': s['S5']['status'],
                                   'S4_E': {n: f3(v) for n, v in (s['S4'].get('E') or {}).items()},
                                   'S5_parts': s['S5']['pairs_whose_parts_match'],
                                   'S5_whole': s['S5']['of_those_also_matching_on_the_whole'], 'S5_share': f3(s['S5']['share'])}
    view['table_6_kinds'] = {kind: t['passages'] for kind, t in report['table_6_by_writer_kind'].items()}
    view['guide_problem_counts'] = report['guide_problem_counts']
    view['five_bar_row'] = report['five_bar_row']
    return view


def compare(expected, actual, path, lines):
    """Walk the expected tree. One line per expected value. Keys that start with '_' are notes and are skipped."""
    if isinstance(expected, dict):
        wrong = 0
        for key, value in expected.items():
            if key.startswith('_'):
                continue
            if not isinstance(actual, dict) or key not in actual:
                lines.append('DIFF %s/%s: expected %s | the program printed nothing' % (path, key, json.dumps(value, ensure_ascii=False)))
                wrong += 1
            else:
                wrong += compare(value, actual[key], path + '/' + key, lines)
        return wrong
    same = expected == actual
    lines.append('%s %s: expected %s | program %s' % ('ok  ' if same else 'DIFF', path, json.dumps(expected, ensure_ascii=False),
                                                       json.dumps(actual, ensure_ascii=False)))
    return 0 if same else 1


def load_kinds(path):
    if not path:
        return {}
    data = read_json(path)
    if isinstance(data, dict):
        return data
    return {p['id']: p['kind'] for p in data if 'kind' in p}


def check_old(old_dir, expected=None, out=None, quiet=False):
    """Program check part 1. Reads the old files and writes nothing beside them."""
    old_dir = Path(old_dir)
    if out and old_dir.resolve() in Path(out).resolve().parents:
        raise SystemExit('REFUSED: the old label folder is sealed. Give --out a place outside %s.' % old_dir)
    passages = read_json(old_dir / 'passages_sealed.json')
    kinds_path = old_dir / 'passages_kinds_HIDDEN_FROM_LABELERS.json'
    run, report, extras = score('old', passages, read_json(old_dir / 'labels_team_a.json'),
                                read_json(old_dir / 'labels_team_b.json'),
                                kinds=load_kinds(kinds_path) if kinds_path.exists() else None, out=out, quiet=quiet)
    if expected is None:
        return report, None, []
    lines = []
    wrong = compare(expected, check_view(report), 'old', lines)
    return report, wrong, lines


def merged(base, changes):
    """A copy of `base` with `changes` laid over it. A dict is merged key by key. Any other value replaces.
    A null removes the key."""
    out = copy.deepcopy(base)
    for key, value in changes.items():
        if value is None:
            out.pop(key, None)
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merged(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def score_fixture_set(fixture_dir, spec, records_a, records_b):
    """Score one fixture set, quietly, in fixture mode. `scorer_constants` may switch the ^5 bar row and nothing
    else, so that the fixture can show what the switch of sheet item 6 does."""
    files = spec['files']
    switch = spec.get('scorer_constants') or {}
    if set(switch) - {'FIVE_BAR_ROW'} or switch.get('FIVE_BAR_ROW', FIVE_BAR_ROW) not in ('without_twins', 'with_twins'):
        raise SystemExit("REFUSED: a fixture set may switch FIVE_BAR_ROW ('without_twins' or 'with_twins') and no other constant.")
    kept = FIVE_BAR_ROW

    def hold(value):       # the setting and its true-or-false reading always move together
        globals().update(FIVE_BAR_ROW=value, BAR_ROW_5_WITH_TWINS=value == 'with_twins')

    try:
        hold(switch.get('FIVE_BAR_ROW', kept))
        run, report, extras = score('fixture', read_json(fixture_dir / files['passages']), records_a, records_b,
                                    ruling=read_json(fixture_dir / files['ruling']) if files.get('ruling') else None,
                                    kinds=load_kinds(fixture_dir / files['kinds']) if files.get('kinds') else None, quiet=True)
    finally:
        hold(kept)
    return report


def check_fixture(fixture_dir, quiet=False):
    """Program check part 2: the scorer alone, on raw label files. No checker is run, so every drop in this part is
    made by the scorer's own backstop. Scores every fixture set and compares with FIXTURE_EXPECTED.json."""
    fixture_dir = Path(fixture_dir)
    expected = read_json(fixture_dir / 'FIXTURE_EXPECTED.json')
    total_wrong, all_lines = 0, []
    for name, spec in expected['part_2_fixture']['sets'].items():
        files = spec['files']
        report = score_fixture_set(fixture_dir, spec, read_json(fixture_dir / files['labels_team_a']),
                                   read_json(fixture_dir / files['labels_team_b']))
        lines = []
        wrong = compare(spec['expected'], check_view(report), name, lines)
        total_wrong += wrong
        all_lines += lines
        if not quiet:
            print()
            print('FIXTURE SET %s (raw label files, no checker): %d expected values, %d differ' % (name, len(lines), wrong))
            for line in lines:
                print('  ' + line)
    # The outcome-word rule at its edges. No fixture is large enough to reach 50 cases, so the rule is asked directly.
    lines, wrong = [], 0
    for k, edge in enumerate(expected['part_2_fixture'].get('outcome_rule_edges', {}).get('edges', []), 1):
        number = [None if edge[key] == 'n/a' else float(edge[key]) for key in ('E', 'kappa')]
        word = outcome_word(edge['cases'], edge['absences'], number[0], number[1], edge['inside'], edge['outside'])
        same = word == edge['word']
        wrong += not same
        lines.append('%s outcome_rule_edges/%d (cases %d, absences %d, E %s, kappa %s, inside %d, outside %d): expected "%s" | '
                     'program "%s"' % ('ok  ' if same else 'DIFF', k, edge['cases'], edge['absences'], edge['E'], edge['kappa'],
                                       edge['inside'], edge['outside'], edge['word'], word))
    total_wrong += wrong
    all_lines += lines
    if not quiet and lines:
        print()
        print('THE OUTCOME-WORD RULE AT ITS EDGES: %d expected values, %d differ' % (len(lines), wrong))
        for line in lines:
            print('  ' + line)
    return total_wrong, all_lines, expected


# ----------------------------------------------------------------------------------------------------
# the files a report was made with
# ----------------------------------------------------------------------------------------------------
OLD_FILES = ('passages_sealed.json', 'labels_team_a.json', 'labels_team_b.json', 'passages_kinds_HIDDEN_FROM_LABELERS.json')


def file_node(path):
    return {'file': Path(path).name, 'sha256': sha256_file(path)}


def folder_node(path):
    """The sha256 of every file in a folder, and one hash over that list. This is the rule of sha_of in
    tools/seal_v2.py, so both programs give one folder the same hash."""
    path = Path(path)
    files = sorted(p for p in path.rglob('*') if p.is_file())
    listing = [{'file': p.relative_to(path).as_posix(), 'sha256': sha256_file(p)} for p in files]
    joined = ''.join('%s %s\n' % (row['sha256'], row['file']) for row in listing)
    return {'folder': path.name, 'files': listing, 'sha256': hashlib.sha256(joined.encode('utf-8')).hexdigest()}


def made_with(files, fixture_dir=None, old_dir=None):
    """role -> {"file", "sha256"} for this program and for every file given. The seal tool can compare these with
    the files it seals, so a report made with another scorer, checker, guide or fixture cannot open a seal."""
    out = collections.OrderedDict()
    out['scorer'] = file_node(__file__)
    for role, path in files.items():
        out[role] = file_node(path) if path else None
    out['fixture'] = folder_node(fixture_dir) if fixture_dir else None
    out['old_labels'] = ({name: sha256_file(Path(old_dir) / name) for name in OLD_FILES if (Path(old_dir) / name).is_file()}
                         if old_dir else None)
    return out


# ----------------------------------------------------------------------------------------------------
# the checker: loaded from the file given, never copied into this program
# ----------------------------------------------------------------------------------------------------
def load_checker(path):
    """Load the label checker from the file given. In verdict mode this runs only after its sha256 matched the seal."""
    import importlib.util
    path = Path(path)
    if not path.is_file():
        raise SystemExit('REFUSED: the checker %s does not exist.' % path)
    spec = importlib.util.spec_from_file_location('label_checker_given', str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    missing = [name for name in ('CHECKER', 'MAX_TRIES', 'check_record', 'take_try', 'new_state', 'final_row')
               if not hasattr(module, name)]
    if missing:
        raise SystemExit('REFUSED: %s is not the label checker. It has no %s.' % (path.name, ', '.join(missing)))
    return module


def chain_rows(chk, passages, label_files):
    """One team's fixture labels, sent through the checker's own three-try loop (take_try) and written out by the
    checker's own final_row. This is the hand-over the real run uses. label_files: the label file of try 1, then,
    if there are more, of try 2 and of try 3. A later file holds only the passages whose record changes on that try.
    With one file every record is sent unchanged on each try. A fixture row with "labeler_failed": true stands for
    a reply that could not be read: no record is sent on any try."""
    tries = [{row['passage_id']: row for row in data if isinstance(row, dict) and 'passage_id' in row} for data in label_files]
    rows = []
    for passage in passages:
        pid, state, record = passage['id'], chk.new_state(), None
        for number in range(chk.MAX_TRIES):
            if number < len(tries) and pid in tries[number]:
                record = tries[number][pid]
            sent = None if record is None or record.get('labeler_failed') else copy.deepcopy(record)
            if chk.take_try(state, pid, passage['text'], sent)['status'] != 'TRY_AGAIN':
                break
        rows.append(chk.final_row(pid, state))
    return rows


def marks_view(rows):
    """What the checker wrote into its rows, counted from the rows alone. This is not the scorer's analysis."""
    final, by_check, tries = collections.Counter(), collections.Counter(), collections.Counter()
    out = {'rows': len(rows), 'entries': 0, 'entries_marked_dropped': 0, 'entries_put_back_after_being_left_out': 0,
           'passages_not_labeled': []}
    for row in rows:
        block = row.get('checker') if isinstance(row.get('checker'), dict) else {}
        final[str(block.get('final'))] += 1
        tries[str(block.get('tries'))] += 1
        if row.get('labeler_failed'):
            out['passages_not_labeled'].append(row.get('passage_id'))
        for entry in row.get('entries') or []:
            out['entries'] += 1
            if isinstance(entry, dict) and entry.get('dropped'):
                out['entries_marked_dropped'] += 1
                for check in entry.get('failed_checks') or []:
                    by_check[check] += 1
            if isinstance(entry, dict) and entry.get('removed_after_reask'):
                out['entries_put_back_after_being_left_out'] += 1
    for name, counter in (('marked_dropped_by_check', by_check), ('rows_by_final_state', final), ('rows_by_tries_used', tries)):
        out[name] = '; '.join('%s %d' % item for item in sorted(counter.items())) or 'none'
    return out


# ----------------------------------------------------------------------------------------------------
# the gate of verdict mode (and, for the label files, of practice mode). See the text at the top of this file.
# Each function returns (problems, facts). A problem is (code, plain text). No problem means the gate is open.
# ----------------------------------------------------------------------------------------------------
def same_value(held, value):
    """True and 1 are not the same value here. Numbers are compared as numbers. The rule of tools/seal_v2.py."""
    if isinstance(held, bool) or isinstance(value, bool):
        return isinstance(held, bool) and isinstance(value, bool) and held == value
    if isinstance(value, (int, float)):
        return isinstance(held, (int, float)) and abs(held - value) < 1e-9
    return held == value


def seal_gate(seal, now, ruling=None):
    """Gate lines 1 to 4. seal: the parsed record. now: role -> {"file", "sha256"} of the five files given.
    ruling: None, or {"file", "sha256", "states"} of the file given with --ruling."""
    problems, facts = [], {}

    def bad(code, text):
        problems.append((code, text))

    if not isinstance(seal, dict):
        bad('SEAL_NOT_AN_OBJECT', 'the seal file is not one JSON object')
        return problems, facts
    if seal.get('schema') != SEAL_SCHEMA:
        bad('NOT_THE_SEAL_SCHEMA', 'schema is %s, not "%s"' % (json.dumps(seal.get('schema')), SEAL_SCHEMA))
    if seal.get('is_a_seal') is not True:
        bad('NOT_A_SEAL', '"is_a_seal" is not true. A practice-set record is not a seal')
    if seal.get('no_label_existed_when_sealed') is not True:
        bad('NOT_SEALED_BEFORE_LABELS', '"no_label_existed_when_sealed" is not true')
    signoff = seal.get('owner_signoff')
    if not (isinstance(signoff, dict) and isinstance(signoff.get('sha256'), str) and HEX64.match(signoff['sha256'].lower())):
        bad('NO_OWNER_SIGNOFF', 'the seal holds no owner sign-off record with a sha256. Nothing proposed is in force')
    else:
        # tools/seal_v2.py may keep a signed value in either of two places, and this gate reads both: beside the
        # item ("constants", "hold_code_removed", "seal_condition_removed"), or in one list for the whole record
        # ("owner_values", "hold_codes_removed", "conditions_struck", "lines_struck").
        def listed(key):
            return [value for value in signoff.get(key) or [] if isinstance(value, str)] if isinstance(signoff.get(key), list) else []

        items = {k: v for k, v in (signoff.get('items') if isinstance(signoff.get('items'), dict) else {}).items()
                 if isinstance(v, dict)}
        signed = {}                                       # item -> {constant name: the value signed for it}
        for source in ({k: v.get('constants') for k, v in items.items()}, signoff.get('owner_values')):
            for item, constants in (source.items() if isinstance(source, dict) else ()):
                if isinstance(constants, dict):
                    signed.setdefault(str(item), {}).update(constants)
        ruled = sorted(set(listed('hold_codes_removed'))
                       | {code for code, item in HOLD_CODE_ITEMS.items() if items.get(item, {}).get('hold_code_removed') is True})
        struck = sorted({CONDITION_ITEMS[name] for name in listed('conditions_struck') if name in CONDITION_ITEMS}
                        | {item for item in CONDITION_ITEMS.values() if items.get(item, {}).get('seal_condition_removed') is True})
        facts['owner_signoff_sha256'] = signoff['sha256']
        facts['items_in_the_signoff'] = sorted(items)
        facts['items_changed_by_the_owner'] = sorted(k for k, v in items.items() if v.get('decision') == 'changed')
        facts['items_struck_out_by_the_owner'] = sorted({HOLD_CODE_ITEMS[code] for code in ruled if code in HOLD_CODE_ITEMS}
                                                        | set(struck) | set(listed('lines_struck')))
        facts['signed_values_compared_with_this_program'] = signed
        facts['changed_items_no_program_can_check'] = listed('changed_items_not_checked_by_this_tool')
        for item in SIGNED_ITEMS_CARRIED_HERE:
            if items.get(item, {}).get('decision') not in ('as_proposed', 'changed'):
                bad('SIGNOFF_ITEM_MISSING ' + item, 'the sign-off record in the seal holds no decision for sheet item %s' % item)
        for item, constants in sorted(signed.items()):    # a signed value must be the value this program holds
            for name, value in sorted(constants.items()):
                held = globals().get(name) if isinstance(name, str) and name.isupper() else None
                if held is None or not same_value(held, value):
                    bad('SIGNED_VALUE_NOT_HELD %s %s' % (item, name), 'the owner signed %s = %s under item %s, but this program '
                        'holds %s' % (name, json.dumps(value), item, 'no such constant' if held is None else json.dumps(held)))
        for code, item in HOLD_CODE_ITEMS.items():
            if code in ruled and code in HOLD_CODES:
                bad('HOLD_CODE_RULED_ON_BUT_HELD ' + code, 'the owner ruled on hold code %s (item %s), but this program still '
                    'carries it' % (code, item))
            if code not in ruled and code not in HOLD_CODES:
                bad('HOLD_CODE_NOT_HELD ' + code, 'hold code %s (item %s) is signed as held, but this program does not carry it'
                    % (code, item))
    if not (isinstance(seal.get('seal_conditions'), dict) and seal['seal_conditions']):
        bad('NO_SEAL_CONDITIONS', 'the seal holds no record of the seal conditions S1 to S5')
    table = seal.get('hold_table')
    table_sha = table['sha256'].lower() if isinstance(table, dict) and isinstance(table.get('sha256'), str) else None
    if table_sha is None:
        bad('NO_HOLD_TABLE', 'the seal holds no sha256 for the hold table')
    for role in SEALED_ROLES:
        node, given = seal.get(role), now.get(role)
        if not (isinstance(node, dict) and isinstance(node.get('sha256'), str)):
            bad('HASH_MISSING ' + role, 'the seal holds no sha256 for the %s' % role)
        elif not given:
            bad('FILE_MISSING ' + role, 'no %s file was given' % role)
        elif node.get('file') and Path(str(node['file'])).name != given['file']:
            bad('FILE_NAME_DIFFERS ' + role, 'the seal names the %s as %s, but the file given is %s' % (role, node['file'], given['file']))
        elif node['sha256'].lower() != given['sha256']:
            bad('HASH_DIFFERS ' + role, '%s has sha256 %s but the seal says %s' % (given['file'], given['sha256'], node['sha256']))
    if ruling is None:
        facts['ruling'] = ('no --ruling file was given. Every hold code is open, as this program holds them. The sealed '
                           'hold table (sha256 %s) was not compared.' % table_sha)
    else:
        states = ruling.get('states') if isinstance(ruling.get('states'), dict) else {}
        valid = bool(states) and all(code in HOLD_CODES and state in ('open', 'counts', 'does_not_count')
                                     for code, state in states.items())
        all_open = valid and all(state == 'open' for state in states.values())
        if not valid:
            bad('RULING_NOT_VALID', 'the ruling file may only set hold codes to open, counts or does_not_count')
        elif ruling.get('sha256') == table_sha:
            if not all_open or set(states) != set(HOLD_CODES):
                bad('SEALED_HOLD_TABLE_NOT_ALL_OPEN', 'the sealed hold table does not set exactly the hold codes of this program to open')
            facts['ruling'] = 'the file given with --ruling is the sealed hold table (sha256 %s).' % table_sha
        elif all_open:
            bad('RULING_NOT_THE_SEALED_HOLD_TABLE', 'the file given with --ruling has sha256 %s, but the sealed hold table has %s'
                % (ruling.get('sha256'), table_sha))
        else:
            facts['ruling'] = ('the file given with --ruling is not the sealed hold table. This is a re-score under an owner '
                               'ruling: every row prints %s and nothing here is a verdict.' % OUTCOME_NO_BAR)
    return problems, facts


def label_gate(chk, passages, rows, team, strict):
    """Gate lines 5 and 6 for one team's label file. chk: the checker, loaded from the file given.
    strict (verdict mode): a row that is not final is a refusal. Not strict (practice mode): it is listed."""
    problems = []
    facts = {'rows': 0, 'records_checked_again': 0, 'entries_checked_again': 0, 'rows_not_final': []}

    def bad(code, text):
        problems.append((code, 'team %s: %s' % (team, text)))

    if not isinstance(rows, list):
        bad('LABELS_NOT_A_LIST', 'the label file is not a JSON list of rows')
        return problems, facts
    texts = {p['id']: p['text'] for p in passages}
    seen = {}
    for row in rows:
        pid = row.get('passage_id') if isinstance(row, dict) else None
        if not isinstance(pid, str) or pid not in texts:
            bad('ROW_FOR_NO_PASSAGE ' + json.dumps(pid), 'a row is for a passage that is not in the passage file')
        elif pid in seen:
            bad('ROW_TWICE ' + pid, 'two rows for one passage')
        else:
            seen[pid] = row
    facts['rows'] = len(seen)
    for passage in passages:
        pid = passage['id']
        row = seen.get(pid)
        if row is None:
            bad('ROW_MISSING ' + pid, 'no row for this passage. The label file must hold one row for every passage')
            continue
        block = row.get('checker')
        if not isinstance(block, dict) or 'final' not in block:
            bad('NO_CHECKER_BLOCK ' + pid, 'the row carries no "checker" block, so it did not come out of the checker')
            continue
        if block.get('checker') != chk.CHECKER:
            bad('ANOTHER_CHECKER ' + pid, 'the row names checker %s, the checker given is %s'
                % (json.dumps(block.get('checker')), chk.CHECKER))
        final = block['final']
        if final not in FINAL_STATES:
            facts['rows_not_final'].append(pid)
            if strict:
                bad('ROW_NOT_FINAL ' + pid, 'the row is %s. Every passage is taken to a final state before it is scored'
                    % json.dumps(final))
            if row.get('labeler_failed') is not True:
                bad('OPEN_ROW_NOT_MARKED ' + pid, 'a row that is not final must carry "labeler_failed": true')
            continue
        if strict and block.get('closed_before_third_try'):
            bad('CLOSED_BEFORE_THIRD_TRY ' + pid, 'the row was made final before its third try')
        if final == 'NOT_LABELED':
            if row.get('labeler_failed') is not True:
                bad('NOT_LABELED_NOT_MARKED ' + pid, 'a NOT_LABELED row must carry "labeler_failed": true')
            if strict and block.get('tries') != chk.MAX_TRIES:
                bad('NOT_LABELED_BEFORE_THE_LAST_TRY ' + pid, 'the row is NOT_LABELED after %s tries, not after %d'
                    % (json.dumps(block.get('tries')), chk.MAX_TRIES))
            continue
        entries = row.get('entries')
        if row.get('labeler_failed') or not isinstance(entries, list):
            bad('LABELED_ROW_NOT_READABLE ' + pid, 'the row is %s, but it is marked labeler_failed or has no list of entries' % final)
            continue
        sent = []                                # the record as the labeler last sent it: without the put-back entries
        for number, entry in enumerate(entries, 1):
            if isinstance(entry, dict) and entry.get('removed_after_reask') is True:
                if not entry.get('dropped'):
                    bad('PUT_BACK_NOT_MARKED_DROPPED %s entry %d' % (pid, number), 'an entry the checker put back must be marked dropped')
            else:
                sent.append((number, entry))
        record = dict(row, entries=copy.deepcopy([entry for _, entry in sent]))
        result = chk.check_record(texts[pid], record, pid)
        facts['records_checked_again'] += 1
        if not result.get('usable') or len(result.get('entries', [])) != len(sent):
            bad('RECORD_FAILS_R0 ' + pid, 'the checker given cannot read the final record (check R0)')
            continue
        for (number, entry), verdict in zip(sent, result['entries']):
            facts['entries_checked_again'] += 1
            if verdict['failed'] and not (isinstance(entry, dict) and entry.get('dropped')):
                bad('ENTRY_FAILS_NOT_MARKED %s entry %d %s' % (pid, number, ','.join(verdict['failed'])),
                    'the entry fails the checker given and is not marked dropped. The label file did not go through that checker')
    return problems, facts


def receipt_gate(seal, team, receipt, labels_sha256, seal_sha256=None):
    """Gate line 7 for one team's receipt. The receipt is the one tools/check_labels_v2.py writes at export
    (receipt_core); tools/label_outside_v2.py writes one with the same keys for its team.
    Always needed: the sealed checker, guide and passages. Needed when the seal names them: the labeler instructions
    (both teams), the team A launch text (team A), the team B labeling tool (team B). Compared when the receipt
    names them: the label file itself, and the seal record the export was checked against."""
    problems, facts = [], {'compared_with_the_seal': [], 'not_compared': []}

    def bad(code, text):
        problems.append((code, 'team %s receipt: %s' % (team, text)))

    if not isinstance(receipt, dict):
        bad('RECEIPT_NOT_AN_OBJECT ' + team, 'the receipt is not one JSON object')
        return problems, facts

    also = {str(row.get('file')): row.get('sha256') for row in seal.get('also_hashed') or [] if isinstance(row, dict)}

    def sealed(role, file_name=None):
        node = seal.get(role)
        if isinstance(node, dict) and isinstance(node.get('sha256'), str):
            return node['sha256']
        return also.get(file_name) if file_name else None

    wanted = [(key, sealed(key[:-len('_sha256')]), True) for key in RECEIPT_KEYS]
    wanted.append(('instructions_sha256', sealed('instructions', 'LABELER_INSTRUCTIONS.txt'), False))
    wanted.append(('launch_text_sha256', sealed('team_a_launch'), False) if team == 'A' else
                  ('tool_sha256', sealed('team_b_tool', 'label_outside_v2.py'), False))
    for key, value, always in wanted:
        given = receipt.get(key)
        if not isinstance(value, str):
            if always:
                bad('RECEIPT_KEY_MISSING %s %s' % (team, key), 'the seal holds no sha256 to compare %s with' % key)
            else:
                facts['not_compared'].append(key + ' (the seal does not name it)')
        elif not isinstance(given, str):
            bad('RECEIPT_KEY_MISSING %s %s' % (team, key), 'the receipt holds no %s, and the seal names that file' % key)
        elif given.lower() != value.lower():
            bad('RECEIPT_DIFFERS %s %s' % (team, key), '%s is %s, the seal says %s' % (key, given, value))
        else:
            facts['compared_with_the_seal'].append(key)
    if isinstance(receipt.get('labels_sha256'), str):
        if receipt['labels_sha256'].lower() != labels_sha256:
            bad('RECEIPT_FOR_ANOTHER_LABEL_FILE ' + team, 'the receipt names label file %s, the file given has %s'
                % (receipt['labels_sha256'], labels_sha256))
        else:
            facts['compared_with_the_seal'].append('labels_sha256 (with the label file given)')
    else:
        facts['not_compared'].append('labels_sha256 (the receipt does not name its label file)')
    record = receipt.get('seal_record')
    if isinstance(record, dict) and isinstance(record.get('sha256'), str) and seal_sha256:
        if record['sha256'].lower() != seal_sha256:
            bad('RECEIPT_MADE_WITH_ANOTHER_SEAL ' + team, 'the export was checked against seal record %s, the seal given has %s'
                % (record['sha256'], seal_sha256))
        else:
            facts['compared_with_the_seal'].append('seal_record (the export was checked against this seal)')
    else:
        facts['not_compared'].append('seal_record (the receipt names no seal record)')
    logs = [log for log in receipt.get('try_logs') or [] if isinstance(log, dict)] if isinstance(receipt.get('try_logs'), list) else []
    other = sorted(str(log.get('file')) for log in logs if isinstance(wanted[0][1], str)
                   and str(log.get('checker_sha256')).lower() != wanted[0][1].lower())
    if other:      # team A's try logs: each one names the checker that counted its tries
        bad('RECEIPT_TRY_LOG_OF_ANOTHER_CHECKER ' + team, 'these try logs were not written by the sealed checker: %s' % ', '.join(other))
    elif logs:
        facts['compared_with_the_seal'].append('checker_sha256 of %d try log%s' % (len(logs), '' if len(logs) == 1 else 's'))
    if receipt.get('every_passage_final') is False or receipt.get('complete') is False:
        bad('RECEIPT_SAYS_NOT_FINISHED ' + team, 'the receipt says that not every passage is final')
    if receipt.get('close_unfinished_was_used') is True or (isinstance(receipt.get('closed_before_third_try'), int)
                                                            and not isinstance(receipt.get('closed_before_third_try'), bool)
                                                            and receipt['closed_before_third_try'] > 0):
        bad('RECEIPT_SAYS_CLOSED_EARLY ' + team, 'the receipt says rows were closed before their third try')
    return problems, facts


def same_file_gate(sha256_a, sha256_b):
    if sha256_a == sha256_b:
        return [('LABEL_FILES_ARE_ONE_FILE', 'the label files of team A and team B have the same sha256 %s' % sha256_a)]
    return []


def refused(problems, what):
    print('REFUSED. Nothing is scored. ' + what)
    for code, text in problems:
        print('  %s: %s' % (code, text))
    return 2


# ----------------------------------------------------------------------------------------------------
# program check part 3: the chain. Checker first, then scorer. Part 4: the gates.
# ----------------------------------------------------------------------------------------------------
def check_chain(fixture_dir, chk, expected, quiet=False):
    """Program check part 3. Every chain set is sent through the checker's own try loop, exported by the checker's
    own final_row, and then scored. Three things are compared with FIXTURE_EXPECTED.json: the marks the checker
    wrote, the codes the label gate gives for those rows, and the scorer's output. So a broken checker, or a broken
    hand-over from checker to scorer, shows here."""
    fixture_dir = Path(fixture_dir)
    raw_sets = expected['part_2_fixture']['sets']
    total_wrong, all_lines, made = 0, [], {}
    for name, spec in expected.get('part_3_chain', {}).get('sets', {}).items():
        files = spec['files']
        passages = read_json(fixture_dir / files['passages'])
        rows = {team: chain_rows(chk, passages, [read_json(fixture_dir / path) for path in files[key]])
                for team, key in (('A', 'labels_team_a'), ('B', 'labels_team_b'))}
        made[name] = {'passages': passages, 'rows': rows}
        report = score_fixture_set(fixture_dir, spec, rows['A'], rows['B'])
        actual = {'checker_marks': {team: marks_view(rows[team]) for team in 'AB'},
                  'gate': {team: sorted(code for code, _ in label_gate(chk, passages, rows[team], team, True)[0]) for team in 'AB'},
                  'scorer': check_view(report)}
        scorer = spec.get('scorer', {})
        if spec.get('scorer_as_raw_set'):       # the chain must print what the raw run prints, except the values named
            scorer = merged(raw_sets[spec['scorer_as_raw_set']]['expected'], spec.get('scorer_except', {}))
        wanted = {'checker_marks': spec.get('checker_marks', {}), 'gate': spec.get('gate', {}), 'scorer': scorer}
        lines = []
        wrong = compare(wanted, actual, 'chain/' + name, lines)
        total_wrong += wrong
        all_lines += lines
        if not quiet:
            print()
            print('CHAIN SET %s (checker, then scorer): %d expected values, %d differ' % (name, len(lines), wrong))
            for line in lines:
                print('  ' + line)
    return total_wrong, all_lines, made


def edited_rows(rows, edit, fixture_dir):
    """A copy of chain rows with one hand-made fault, for a gate case."""
    rows = copy.deepcopy(rows)
    at = {row['passage_id']: k for k, row in enumerate(rows)}
    for action, value in edit.items():
        if action == 'raw_file':
            rows = read_json(fixture_dir / value)
        elif action == 'drop_row':
            del rows[at[value]]
        elif action == 'repeat_row':
            rows.append(copy.deepcopy(rows[at[value]]))
        elif action == 'add_row':
            rows.append(copy.deepcopy(value))
        elif action == 'remove_checker':
            rows[at[value]].pop('checker', None)
        elif action == 'set_checker':
            rows[at[value[0]]]['checker'].update(value[1])
        elif action == 'set_row':
            rows[at[value[0]]].update(copy.deepcopy(value[1]))
        elif action == 'unmark_dropped':
            for entry in rows[at[value]]['entries']:
                entry.pop('dropped', None)
                entry.pop('failed_checks', None)
        else:
            raise SystemExit('REFUSED: the fixture names an edit this program does not know: %s' % action)
    return rows


def check_gates(fixture_dir, chk, expected, made, quiet=False):
    """Program check part 4. Hand-made seals, receipts and label rows are shown to the gate of verdict mode. For
    each case the codes of the refusals are compared with FIXTURE_EXPECTED.json. No project file is written."""
    fixture_dir = Path(fixture_dir)
    part = expected.get('part_4_gates', {})
    lines, wrong = [], 0

    def one(path, wanted, problems):
        nonlocal wrong
        got = sorted(code for code, _ in problems)
        same = sorted(wanted) == got
        wrong += not same
        lines.append('%s %s: expected %s | program %s' % ('ok  ' if same else 'DIFF', path, json.dumps(sorted(wanted)), json.dumps(got)))

    block = part.get('seal_gate', {})
    for case in block.get('cases', []):       # `set` is laid over the base seal: dicts merge, a null removes a key
        seal = merged(block['base_seal'], case.get('set', {}))
        now = merged(block['base_now'], case.get('now', {}))
        one('gates/seal/' + case['name'], case['expect'], seal_gate(seal, now, case.get('ruling'))[0])
    block = part.get('receipt_gate', {})
    for case in block.get('cases', []):
        receipt = merged(block['base_receipt'], case.get('set', {}))
        one('gates/receipt/' + case['name'], case['expect'],
            receipt_gate(part['seal_gate']['base_seal'], case.get('team', 'A'), receipt, block['labels_sha256'],
                         block['seal_sha256'])[0])
    for case in part.get('label_gate', {}).get('cases', []):
        if 'same_sha256' in case:
            pair = ('1' * 64, '1' * 64) if case['same_sha256'] else ('1' * 64, '2' * 64)
            one('gates/labels/' + case['name'], case['expect'], same_file_gate(*pair))
            continue
        base = made[case['chain_set']]
        rows = edited_rows(base['rows'][case['team']], case.get('edit', {}), fixture_dir)
        one('gates/labels/' + case['name'], case['expect'], label_gate(chk, base['passages'], rows, case['team'], case.get('strict', True))[0])
    if not quiet and lines:
        print()
        print('THE GATES OF VERDICT MODE: %d expected values, %d differ' % (len(lines), wrong))
        for line in lines:
            print('  ' + line)
    return wrong, lines


def program_checks(fixture_dir, old_dir, checker_path):
    """Seal condition S1: all four program checks, run by this program on itself, with the checker given."""
    chk = load_checker(checker_path)
    wrong_2, lines_2, expected = check_fixture(fixture_dir, quiet=True)
    wrong_3, lines_3, made = check_chain(fixture_dir, chk, expected, quiet=True)
    wrong_4, lines_4 = check_gates(fixture_dir, chk, expected, made, quiet=True)
    _, wrong_1, lines_1 = check_old(old_dir, expected['part_1_old_labels']['expected'], quiet=True)
    parts = collections.OrderedDict()
    for name, lines, wrong in (('part_1_old_labels', lines_1, wrong_1), ('part_2_fixture', lines_2, wrong_2),
                               ('part_3_chain_checker_then_scorer', lines_3, wrong_3),
                               ('part_4_gates_of_verdict_mode', lines_4, wrong_4)):
        parts[name] = {'values_compared': len(lines), 'differ': wrong}
    done = all(part['values_compared'] for part in parts.values())
    s1 = {'status': 'PASS' if done and not any(part['differ'] for part in parts.values()) else 'FAIL'}
    s1.update(parts)
    s1['made_with'] = {'scorer_sha256': sha256_file(__file__), 'checker_sha256': sha256_file(checker_path),
                       'fixture_sha256': folder_node(fixture_dir)['sha256'],
                       'old_labels': {name: sha256_file(Path(old_dir) / name) for name in OLD_FILES
                                      if (Path(old_dir) / name).is_file()}}
    s1['note'] = ('Compared with FIXTURE_EXPECTED.json. The plan must quote the same numbers. A part with no value '
                  'compared is not a pass.')
    return s1


# ----------------------------------------------------------------------------------------------------
# the four ways to run it
# ----------------------------------------------------------------------------------------------------
def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Label-agreement scorer, version 2. See the text at the top of the file.')
    sub = parser.add_subparsers(dest='mode', required=True)
    for name in ('verdict', 'practice'):
        p = sub.add_parser(name)
        p.add_argument('--passages', required=True)
        p.add_argument('--labels-a', required=True)
        p.add_argument('--labels-b', required=True)
        p.add_argument('--checker', required=True, help='tools/check_labels_v2.py: every final record is checked again with it')
        p.add_argument('--guide', required=True, help='the labeling guide the labels were made under')
        p.add_argument('--instructions', required=name == 'practice',
                       help='label_v2/LABELER_INSTRUCTIONS.txt; its sha256 goes into the report (the seal tool looks for it)')
        p.add_argument('--kinds')
        p.add_argument('--out')
        if name == 'verdict':
            p.add_argument('--ruling', help='the sealed hold table, or an owner ruling for a re-score')
            for role in ('seal', 'plan', 'receipt-a', 'receipt-b'):
                p.add_argument('--' + role, required=True)
        else:
            p.add_argument('--fixture-dir')
            p.add_argument('--old-dir')
    p = sub.add_parser('old')
    p.add_argument('--old-dir', required=True)
    p.add_argument('--expected')
    p.add_argument('--out')
    p = sub.add_parser('fixture')
    p.add_argument('--dir', required=True)
    p.add_argument('--checker', default=str(Path(__file__).resolve().parent / 'check_labels_v2.py'),
                   help='the checker that part 3 and part 4 run; default: check_labels_v2.py beside this program')
    args = parser.parse_args(argv)

    if args.mode in ('verdict', 'practice'):
        verdict = args.mode == 'verdict'
        given = {'passages': args.passages, 'labels_a': args.labels_a, 'labels_b': args.labels_b, 'checker': args.checker,
                 'guide': args.guide, 'instructions': args.instructions, 'kinds': args.kinds}
        if verdict:
            given.update(seal=args.seal, plan=args.plan, receipt_a=args.receipt_a, receipt_b=args.receipt_b, ruling=args.ruling)
        else:
            if bool(args.fixture_dir) != bool(args.old_dir):
                return refused([('PROGRAM_CHECKS_NEED_BOTH_FOLDERS', 'give --fixture-dir and --old-dir together, or neither')],
                               'The command is not complete.')
            for role, folder in (('fixture_dir', args.fixture_dir), ('old_dir', args.old_dir)):
                if folder and not Path(folder).is_dir():
                    return refused([('FOLDER_NOT_FOUND ' + role, str(folder))], 'A folder is missing.')
        missing = [('FILE_NOT_FOUND ' + role, str(path)) for role, path in given.items() if path and not Path(path).is_file()]
        if missing:
            return refused(missing, 'A file is missing.')
        try:
            passages = read_json(args.passages)
            rows = {'A': read_json(args.labels_a), 'B': read_json(args.labels_b)}
            seal = read_json(args.seal) if verdict else None
            receipts = {'A': read_json(args.receipt_a), 'B': read_json(args.receipt_b)} if verdict else None
            states = read_json(args.ruling) if verdict and args.ruling else None
        except ValueError as error:
            return refused([('NOT_JSON', str(error)[:160])], 'A file cannot be read as JSON.')
        seal_info = None
        if verdict:       # gate lines 1 to 4, before the checker file is loaded
            now = {role: file_node(path) for role, path in (('guide', args.guide), ('plan', args.plan), ('checker', args.checker),
                                                            ('scorer', __file__), ('passages', args.passages))}
            ruling = None if states is None else {'file': Path(args.ruling).name, 'sha256': sha256_file(args.ruling),
                                                  'states': states}
            problems, seal_info = seal_gate(seal, now, ruling)
            if problems:
                return refused(problems, 'The record is not a seal with an owner sign-off in it, or a file does not match it '
                                         '(gate lines 1 to 4).')
            seal_info.update(seal_file=Path(args.seal).name, seal_sha256=sha256_file(args.seal), files=now)
        chk = load_checker(args.checker)
        shas = {'A': sha256_file(args.labels_a), 'B': sha256_file(args.labels_b)}
        problems, gate = same_file_gate(shas['A'], shas['B']), {}
        for team in 'AB':     # gate lines 5 to 7
            found, gate[team] = label_gate(chk, passages, rows[team], team, strict=verdict)
            problems += found
            if verdict:
                found, gate[team]['receipt'] = receipt_gate(seal, team, receipts[team], shas[team], seal_info['seal_sha256'])
                problems += found
        if problems:
            return refused(problems, 'A label file is not one the checker given wrote, is not finished, or does not belong '
                                     'to the sealed files (gate lines 5 to 7).')
        s1 = None
        if not verdict and args.fixture_dir:
            s1 = program_checks(args.fixture_dir, args.old_dir, args.checker)
        files = collections.OrderedDict((role, given.get(role)) for role in (
            'checker', 'guide', 'instructions', 'plan', 'passages', 'labels_a', 'labels_b', 'kinds', 'seal', 'receipt_a',
            'receipt_b', 'ruling') if role in given)
        score(args.mode, passages, rows['A'], rows['B'], ruling=states, kinds=load_kinds(args.kinds), out=args.out,
              tables=(1, 2, 3, 4, 5, 6) if verdict else (1, 2, 5), s1=s1, seal_info=seal_info, label_gate=gate,
              made_with=made_with(files, None if verdict else args.fixture_dir, None if verdict else args.old_dir))
        return 0

    if args.mode == 'old':
        expected = read_json(args.expected)['part_1_old_labels']['expected'] if args.expected else None
        _, wrong, lines = check_old(args.old_dir, expected, out=args.out)
        if expected is not None:
            print()
            print('PROGRAM CHECK PART 1: %d expected values, %d differ' % (len(lines), wrong))
            for line in lines:
                print('  ' + line)
            return 1 if wrong else 0
        return 0

    chk = load_checker(args.checker)
    wrong_2, lines_2, expected = check_fixture(args.dir)
    wrong_3, lines_3, made = check_chain(args.dir, chk, expected)
    wrong_4, lines_4 = check_gates(args.dir, chk, expected, made)
    print()
    print('checker used for part 3 and part 4: %s sha256 %s' % (Path(args.checker).name, sha256_file(args.checker)))
    failed = False
    for title, lines, wrong in (('PROGRAM CHECK PART 2 (raw label files; the scorer alone)', lines_2, wrong_2),
                                ('PROGRAM CHECK PART 3 (the chain: checker, then scorer)', lines_3, wrong_3),
                                ('PROGRAM CHECK PART 4 (the gates of verdict mode)', lines_4, wrong_4)):
        passed = bool(lines) and not wrong
        failed = failed or not passed
        print('%s: %d expected values, %d differ: %s' % (title, len(lines), wrong, 'PASS' if passed else 'FAIL'))
    print('PROGRAM CHECK PARTS 2, 3 AND 4 TOGETHER: %d expected values, %d differ: %s'
          % (len(lines_2) + len(lines_3) + len(lines_4), wrong_2 + wrong_3 + wrong_4, 'FAIL' if failed else 'PASS'))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
