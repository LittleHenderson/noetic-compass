"""Format checker for label records, labeling guide v2.0. One program, the same for both label teams.

==========================================================================================
WHAT THIS PROGRAM IS
==========================================================================================
Plain Python, standard library only. No model. No project code. It runs on ONE team's
record for ONE passage. It never sees the other team's labels, the writer's kinds or the
writer's brief. It decides nothing about meaning: it never says that a role is right or
wrong, present or absent. Source of every check: design_v2/labeling_final.json, spec
field entry_format, section THE CHECKER (C1 to C9) and section DROPS; the clean-up, the
word rule, the sentence rule and the same-reading test come from the spec field
matching_algorithm_precise (steps 0, 1, 2, 3, 5, 6, 7). The form lines added after the one
review round of the build are printed in the guide: section B1, 'How the fields go
together', and section B2, checks C1, C5, C6 and C8.

STATUS. Candidate program, not frozen. The check list is part of a design PROPOSAL. It
takes effect only when the owner signs the proposal, before any new passage is sealed.

THE RECIPE FOR A LABELER WHO RUNS THE CHECKER BY HAND
  The fixed words are the constant TEAM_A_RECIPE below. Print them with
      check_labels_v2.py --recipe
  They are meant to be copied, word for word, into the one fixed launch text that the plan
  names for those labelers. A labeler is never told to open this source file.
  The other team gets the very same loop: tools/label_outside_v2.py runs it for an outside
  model with the same function (take_try), the same messages and the same three tries.

THE CHECKS (each one has a fixed message; the entry number and the quoted text are filled in)
R0  The record as a whole: one JSON object; passage_id is the passage's id; "entries" is a
    list of objects; none_of_these is true or false; none_of_these true means no entries.
C1  Allowed values. noetic '^1'..'^9'. certainty clear / ambiguous / held. other_candidate
    with ambiguous and only then. held_under with held and only then, and the code belongs
    to that Noetic. reached_by only on a ^9, never with held, never with other_candidate
    'reasoning'. clue only on a ^6, only when this record has a ^9 with reached_by
    reasoning, and only with certainty clear. Quoted fields are text. An optional field
    with an empty value is read as left out.
C2  support is an exact copy of passage text (after the one fixed clean-up). The program
    widens it to whole sentences. The widened support has at most 4 sentences.
C3  label is an exact copy, has 1 to 12 words and lies inside the widened support.
C4  measure is filled and lies inside the support for ^4 and ^7. Empty for the others.
C5  mind is the label of one of this record's own ^1 entries. In a ^1 entry mind equals
    its own label. In a ^6 entry mind is always empty.
C6  relative_to. ^8: the label of a ^9 entry with the same mind, certainty and hold code
    that points back; never a ^9 with reached_by reasoning (rule 15b: 'Do not mark ^8').
    ^9: the reverse; always empty with reached_by. ^6: an exact copy of 1 to 12 words;
    always empty with clue true. Every other Noetic: empty.
C7  Pointer check on every label except a ^1 label, and on a ^6 relative_to, unless
    no_fuller_name is true.
C8  No duplicate: no two entries of one record, for one Noetic, that the scorer's own test
    calls the same reading. The certainty does not matter: the same thing written once
    clear and once held (or once clear and once ambiguous) is a duplicate, and so is one
    piece written both as a clue and as a plain part. The later one fails. Two sizes for
    one thing (^4) and copies that point at different partners (^8, ^9) stay allowed.
C9  One question, never a rejection: a ^2 or ^3 label whose last content word is a feeling
    word. Asked once per label. The same label sent again is accepted.

THREE TRIES AND WHAT IS KEPT (spec section DROPS)
- A try that passes R0 and C1 to C8, with no new C9 question, is ACCEPTED and final.
- Otherwise the messages go back and the team tries again, up to three tries.
- After the third try the third record is final. Each entry that still fails C1 to C8 is
  DROPPED. A dropped entry does not vanish: it stays in the record, flagged, and the scorer
  keeps it in its row as an unmatched entry when its noetic and certainty are valid.
- If the third try gives no usable record (R0 fails), the passage is NOT LABELED by this team.

A FAILING ENTRY THAT IS LEFT OUT IS PUT BACK
  A labeler could answer a re-ask by leaving the failing entry out. The entry would then be
  in no row and in no drop count. So the try log keeps every entry that failed C1 to C7 on
  a try that was sent back. When the record becomes final, the program compares, for each
  Noetic, how many entries that try held with how many the final record holds. If the final
  record holds fewer, the missing failed entries are put back into the final row, marked
  "dropped": true, "failed_checks": [...], "removed_after_reask": true. The scorer keeps
  them in their row and in the dropped share like any other dropped entry.
  The exact rule (function _put_back):
  - Tries are compared from the latest to the earliest. An entry that is put back counts
    as held from then on, so one entry is never put back twice.
  - Per Noetic. An entry whose noetic is not valid has no Noetic to count under: it is put
    back only when the record as a whole lost entries.
  - If fewer entries are missing than failed, the program has to tell which failed entry
    was corrected and which was left out. Each failed entry is paired with the held entry
    of that Noetic that is most like it (shared content words of the two labels, counted
    twice, plus shared content words of the two supports; a held entry is used once). A
    failed entry with no partner is taken first, then the ones least like their partner,
    then by their order in the record. This choice never changes how many are put back.
  - Not put back: an entry with a message that says the entry may be removed. There are two
    such messages: C8 (a repeated entry: 'Remove one of the two'), and C6 on a ^8 that
    names a ^9 reached by reasoning (rule 15b says 'Do not mark ^8'; without this the only
    way out with no dropped entry would be to write a clear pair, and the checker must not
    push a labeler toward one reading of rule 15). Such entries are left out of both counts.
  - Not kept: the entries of a try whose record cannot be taken as this passage's record
    (another passage_id, or none_of_these true together with entries).
  - A row never holds none_of_these true together with entries. When an entry is put back
    into such a row, none_of_these is written false and the "checker" block keeps
    "none_of_these_as_sent": true.
  Two known limits. (1) An entry that failed and was then written under ANOTHER Noetic is put
  back under the first one. That thing is then counted twice: once as dropped, once under the
  new Noetic. (2) An entry that only got a C9 question (never a failure) and was then left
  out is not put back. Every try whose entries can be read keeps "per_noetic" in the try
  log: the count of its entries per Noetic. So both cases can be counted from the logs.

COMMAND LINE
  check_labels_v2.py PASSAGES LABELS                       plain check of one record or a whole labels
                                                           file; nothing is counted; exit 0 pass, 1 fail
  check_labels_v2.py PASSAGES RECORD --tries LOG [--id ID] one counted try per record (the recipe)
  check_labels_v2.py PASSAGES --export OUT --tries LOG [LOG ...]
                     [--guide G] [--instructions I] [--launch-text L] [--seal SEAL] [--close-unfinished]
                                                           write the final labels file from try logs, and
                                                           its receipt OUT.receipt.json
  check_labels_v2.py --recipe                              print the fixed recipe text
Exit codes: 0 pass or accepted; 1 a check failed (try again), or an export with passages that are
not final; 3 final with dropped entries or not labeled; 2 the command was wrong.
  --seal SEAL   the seal record (SEAL.json) or the practice record (PRACTICE_SET.json). The export is
                refused, and nothing is written, unless this checker, the passage file, the guide and the
                instructions (and the launch text, when one is named or sealed) have the sha256 that the
                record holds. With --seal, --guide and --instructions must be given.
  --close-unfinished   make the last try of an unfinished passage final. The row is marked
                "closed_before_third_try". Whether this may ever be used is the plan's to say.

AS A FUNCTION
  import check_labels_v2 as chk
  result = chk.check_record(passage_text, record, passage_id='V123')   # result['passes'], result['messages']
  state = chk.new_state(); outcome = chk.take_try(state, 'V123', passage_text, record)
  The text rules of the matching algorithm can be imported too, so that the scorer and the checker
  cannot drift apart: clean, split_sentences, Passage (occurrences, widen, word_positions,
  content_positions, same_thing, overlap), entry_class.

THE FINAL LABELS FILE (written by --export, and by label_outside_v2.py for the other team)
  A JSON list, one row per passage, in the order of the passage file. A row holds the record as the
  labeler last sent it (passage_id, none_of_these, entries, not_enough_information, guide_problem)
  and the marks below. Only this program writes them. They are the marks tools/verdict_v2.py reads.
    on an entry that is dropped:  "dropped": true, "failed_checks": ["C3", ...]
    on an entry that was put back: the same two marks and "removed_after_reask": true. Such an
                 entry stands after the entries the labeler last sent.
    on the row:  "labeler_failed": true   only when the passage is not labeled by this team
                 "reasks": [{"try", "entry", "noetic", "check"}, ...]   one item per failed check per
                           try that was sent back (R0 = the record as a whole, C9 = the question)
                 "checker": {"checker": "check_labels_v2/1", "tries": 1..3,
                             "final": "LABELED" | "LABELED_WITH_DROPPED_ENTRIES" | "NOT_LABELED" |
                                      "UNFINISHED" | "NOT_ATTEMPTED",
                             "dropped": [{"entry": number from 1, "noetic", "certainty", "class",
                                          "stays_in_row", "checks"}],
                             "removed_after_reask": how many of the dropped entries were put back}
                 A put-back item in "dropped" also has "removed_after_reask": true and "from_try".
                 "closed_before_third_try": true is in the block only after --close-unfinished.
  A dropped entry stays in "entries". "stays_in_row" false means 'dropped, no row'.
  An optional field with an empty value is not written: "" or null for other_candidate, held_under
  and reached_by; false or null for clue and no_fuller_name. Left out and empty mean the same.
  Checking an exported row again with check_record never fails an entry that is not marked dropped.

THE RECEIPT (OUT.receipt.json; label_outside_v2.py writes one with the same keys for its team)
  "format": "check_labels_v2.receipt/1"; the sha256 of the labels file, of the passage file and of this
  checker; the sha256 of the guide, the instructions and the launch text when they were named; the try
  logs with their sha256; whether every passage is final; how many rows were closed before the third
  try; and, with --seal, the seal record's sha256 and each compared hash.
  What a receipt can show: the labels file was written by this checker from these try logs, and every
  try was made on the passage text of this passage file (each try log keeps the sha256 of the text).
  What it cannot show: which guide a labeler who works by hand really read. For that team the guide,
  instructions and launch text hashes are the files the coordinator named at export.

ENTRIES THAT LEAN ON EACH OTHER
  A Mind is located through its ^1 entry. A ^8 or a ^9 is located through the other member of its
  pair. A dropped entry has no place (matching step 3). So when a ^1 entry fails a check, every entry
  that names that Mind fails C5; and when one member of a pair fails, the other fails C6. The message
  names the entry to correct. This is the same rule tools/verdict_v2.py applies when it locates
  entries, so the labeler is told during its tries about every entry the scorer would drop.
"""
import argparse
import copy
import datetime
import glob
import hashlib
import json
import os
import re
import sys
from pathlib import Path

CHECKER = 'check_labels_v2/1'
TRIES_FORMAT = 'check_labels_v2.tries/1'
RECEIPT_FORMAT = 'check_labels_v2.receipt/1'
MAX_TRIES = 3
NOETICS = ['^%d' % i for i in range(1, 10)]
NO_NOETIC = 'no valid Noetic'
# The fixed words for a labeler who runs the checker by hand. Printed by --recipe. They name no other team and no
# other program. The plan's one fixed launch text for those labelers holds them word for word.
TEAM_A_RECIPE = """HOW TO CHECK YOUR OWN RECORD AND TRY AGAIN
You have three tries per passage. The checker counts them. Work on one passage at a time.

1. Label ONE passage. Save its record as ONE JSON object in a file of its own, named after
   the passage. Example: work/V123.json
2. Run the checker on that file. Every run with --tries is one try. It is a try even when
   the file did not change. It is a try even when the file is not valid JSON.
       /c/Python314/python.exe -B tools/check_labels_v2.py PASSAGES.json work/V123.json --tries work/tries_NAME.json
   PASSAGES.json is the passage file you were given. tries_NAME.json is your own try log.
   Use one log for all your passages. The checker writes it. Never edit it. Never delete it.
3. Read the lines it prints, and read the exit code.
   exit 0  ACCEPTED. The record is final. Do not change it. Go to the next passage.
   exit 1  TRY AGAIN. Each line names an entry, a check (C1 to C9, or R0 for the record as a
           whole) and what is wrong. Correct what the messages name, in the same file.
           Keep every entry in the file. Then do step 2 again.
   exit 3  FINAL. The three tries are used. The record stays as it is. An entry that still
           fails is counted as dropped. Do not change the record. Go to the next passage.
   exit 2  The command was wrong (a file is missing, the passage id is unknown). This is
           not a try. Correct the command.
4. An entry that failed a check does not vanish when you leave it out of your next try. The
   checker puts it back and counts it as a dropped entry of yours. Leave an entry out only
   when its own message says that you may remove it.
5. Check C9 is a question, not a failure. It is asked once for a label. Read its message.
   'Send the same label again' means: leave the label as it is and run the checker again.
   The label is then accepted.
6. The checker reads form only. It does not say whether any role is right or wrong.
   A record that passes is not thereby correct.
7. Do not read another labeler's records or try log.
8. Never run the checker on your own record without --tries, and never call it from your
   own code. That would be a free extra look. No labeler gets one.
9. When all your passages are final, hand back your try log. The final labels file is
   written from the try logs. So the record that counts is the one the checker last saw,
   not a file edited later.
"""
CERTAINTIES = ('clear', 'ambiguous', 'held')
OTHER_CANDIDATES = tuple(NOETICS) + ('none', 'reasoning')
HOLD_CODES = {'H2-COMFORT': ('^2',), 'H3-NOPULL': ('^3',), 'H3-BORED': ('^3',), 'H5-ROLE': ('^5',),
              'H7-RESULT': ('^7',), 'H7-NOEFFECT': ('^7',), 'H7-UNBROKEN': ('^7',), 'H89-FOLLOWS': ('^8', '^9')}
MAX_LABEL_WORDS = 12
MAX_SUPPORT_SENTENCES = 4
START_TOLERANCE = 2
# the 34 filler words of tools/verdict.py (matching step 1)
FILLER = frozenset(('the a an of to in on at and or his her their its he she it that this was had with for from by as him '
                    'them they is were be been not').split())
assert len(FILLER) == 34
ABBREVIATIONS = ('Mr', 'Mrs', 'Ms', 'Dr', 'St', 'Prof', 'Sr', 'Jr', 'No', 'vs', 'etc', 'e.g', 'i.e')
# check C7 (rule 16, steps 3 and 4)
PRONOUNS = frozenset('it this that they them he she here there one'.split())
POINTER_STARTS = ('this', 'that', 'these', 'those', 'such')
BARE_WORDS = frozenset(('sound noise smell scent odour odor aroma fragrance sight feeling sensation memory image picture '
                        'thought moment').split())
HOLDER_LEADS = ('a memory of', 'the memory of', 'memories of', 'a picture of', 'pictures of', 'an image of', 'a vision of',
                'a thought of', 'the thought of')
# check C9
FEELING_WORDS = frozenset(('satisfaction pleasure comfort peace calm relief aversion annoyance disgust unease irritation '
                           'distaste dislike yearning longing feeling sense').split())
C9_MESSAGE = ("Your label names a feeling. If it is the Mind's own pull or push and the passage names what it is aimed at, "
              "use that thing as the label. If the feeling is itself what the Mind is drawn to or repelled by, send the same "
              "label again.")
FORM_ONLY = 'The checker reads form only. It does not say whether any role is right or wrong.'
KEEP_EVERY_ENTRY = ('Keep every entry in the record. An entry that failed a check and is then left out is put back and '
                    'counted as a dropped entry of yours. Leave an entry out only when its own message says that you may '
                    'remove it.')
QUOTED_FIELDS = ('mind', 'label', 'support', 'measure', 'relative_to')
# the optional fields and the empty values that mean 'left out' (guide B1, 'How the fields go together')
EMPTY_OPTIONALS = {'other_candidate': ('', None), 'held_under': ('', None), 'reached_by': ('', None),
                   'clue': (False, None), 'no_fuller_name': (False, None)}
MARKS = ('dropped', 'failed_checks', 'removed_after_reask')      # written by this program only, never by a labeler
_CURLY = ((chr(0x2018), "'"), (chr(0x2019), "'"), (chr(0x201c), '"'), (chr(0x201d), '"'))
_WORD = re.compile(r'[A-Za-z0-9]+')
_SENTENCE_END = re.compile(r'[.!?]+["\')\]]*(?=\s|$)')
_EDGE_PUNCTUATION = '.,;:!?"\'()[]'


class UsageError(Exception):
    """The command or a file is wrong. Never a try. The command line turns it into exit code 2."""


# ---------------------------------------------------------------- text rules (matching steps 0 to 5)

def clean(text):
    """The one fixed clean-up: curly quotes become straight, every run of white space becomes one space, ends trimmed."""
    if not isinstance(text, str):
        return ''
    for curly, straight in _CURLY:
        text = text.replace(curly, straight)
    return re.sub(r'\s+', ' ', text).strip()


def split_sentences(text):
    """Sentence spans (start, end) of a cleaned text. A sentence ends after a run of . ! or ? (plus closing quotes or
    brackets) that is followed by a space or the end. One full stop right after Mr, Mrs, Ms, Dr, St, Prof, Sr, Jr, No,
    vs, etc, e.g or i.e does not end a sentence. Semicolons do not end sentences."""
    spans, start = [], 0
    for match in _SENTENCE_END.finditer(text):
        before = text[start:match.start()].split()[-1:]
        if before and before[0].lstrip('"\'([') in ABBREVIATIONS and match.group() == '.':
            continue
        spans.append((start, match.end()))
        start = match.end()
        while start < len(text) and text[start] == ' ':
            start += 1
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def word_count(text):
    """Words as the guide counts them for a label: stretches between spaces."""
    return len(clean(text).split())


def content_words(text):
    """Content words of a string: runs of A-Z a-z 0-9, lower-cased, 2 or more characters, not a filler word.
    If there are none, all the words."""
    words = [w.lower() for w in _WORD.findall(text)]
    kept = [w for w in words if len(w) >= 2 and w not in FILLER]
    return kept or words


class Passage:
    """A cleaned passage with its words and sentences. All places are character positions in the cleaned text."""

    def __init__(self, text):
        self.text = clean(text)
        self.words = [(m.start(), m.end(), m.group().lower()) for m in _WORD.finditer(self.text)]
        self.sentences = split_sentences(self.text)

    def occurrences(self, quote, lo=0, hi=None):
        """Every place where the quote occurs between lo and hi. A quote occurs at a place only if the character
        before it and the character after it are not a letter or a digit."""
        quote, text = clean(quote), self.text
        hi = len(text) if hi is None else hi
        places = []
        if not quote:
            return places
        at = text.find(quote, lo)
        while at >= 0 and at + len(quote) <= hi:
            end = at + len(quote)
            if (at == 0 or not text[at - 1].isalnum()) and (end == len(text) or not text[end].isalnum()):
                places.append((at, end))
            at = text.find(quote, at + 1)
        return places

    def widen(self, span):
        """The span widened to whole sentences."""
        starts = [s[0] for s in self.sentences if s[0] <= span[0] < s[1]]
        ends = [s[1] for s in self.sentences if s[0] < span[1] <= s[1]]
        return (min(starts) if starts else span[0], max(ends) if ends else span[1])

    def sentences_in(self, span):
        return sum(1 for s in self.sentences if s[0] >= span[0] and s[1] <= span[1])

    def word_positions(self, span):
        """W(span): the positions (0, 1, 2, ...) of the words that lie wholly inside the span."""
        return [k for k, (start, end, _) in enumerate(self.words) if start >= span[0] and end <= span[1]]

    def content_positions(self, span):
        """C(span): the content words among W(span); if there are none, all of W(span)."""
        every = self.word_positions(span)
        kept = [k for k in every if len(self.words[k][2]) >= 2 and self.words[k][2] not in FILLER]
        return kept or every

    def overlap(self, p, q):
        return bool(set(self.content_positions(p)) & set(self.content_positions(q)))

    def same_thing(self, p, q, tolerance=START_TOLERANCE):
        """The two places share a content word at the same position and start at most `tolerance` words apart."""
        wp, wq = self.word_positions(p), self.word_positions(q)
        if not wp or not wq or not self.overlap(p, q):
            return False
        return tolerance is None or abs(wp[0] - wq[0]) <= tolerance


def entry_class(entry):
    """The class of an entry (matching step 6). None when its noetic or its certainty is not valid."""
    if not isinstance(entry, dict):
        return None
    noetic, certainty = entry.get('noetic'), entry.get('certainty')
    if noetic not in NOETICS or certainty not in CERTAINTIES:
        return None
    if certainty == 'held':
        return 'held ' + noetic
    if certainty == 'ambiguous':
        return ('uncertain ' if entry.get('other_candidate') == 'reasoning' else 'ambiguous ') + noetic
    if noetic == '^9' and entry.get('reached_by') == 'reasoning':
        return '^9 reached by reasoning'
    if noetic == '^6' and entry.get('clue') is True:
        return '^6 clue'
    return noetic


def pointer_reason(phrase):
    """Why a phrase is a pointer under check C7, or None. Rule 16, steps 3 and 4. Closed lists, nothing else."""
    tokens = [t.strip(_EDGE_PUNCTUATION).lower() for t in clean(phrase).split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    if len(tokens) == 1 and tokens[0] in PRONOUNS:
        return "it is the pronoun '%s' alone" % tokens[0]
    if tokens[0] in POINTER_STARTS:
        return "it starts with '%s'" % tokens[0]
    if len(tokens) == 2 and tokens[0] in ('the', 'a', 'an') and tokens[1] in BARE_WORDS:
        return "it is '%s' plus the bare word '%s'" % (tokens[0], tokens[1])
    joined = ' '.join(tokens)
    for lead in HOLDER_LEADS:
        if joined == lead or joined.startswith(lead + ' '):
            return "it starts with the holder words '%s'" % lead
    return None


def feeling_label(label):
    """The feeling word that check C9 asks about, or None: the last content word of the label, if it is on the list."""
    words = content_words(clean(label))
    return words[-1] if words and words[-1] in FEELING_WORDS else None


def c9_key(noetic, mind, label):
    return '%s|%s|%s' % (noetic, clean(mind), clean(label))


# ---------------------------------------------------------------- the check of one record

def _show(text, limit=70):
    text = clean(text) if isinstance(text, str) else repr(text)
    return text if len(text) <= limit else text[:limit - 3] + '...'


def _field(entry, name, problems):
    """A quoted field as cleaned text. A missing field is ''. Anything that is not text is a C1 problem."""
    value = entry.get(name)
    if value is None:
        return ''
    if not isinstance(value, str):
        problems.append(('C1', '%s must be text in double quotes. You wrote %s.' % (name, _show(json.dumps(value)))))
        return ''
    return clean(value)


def _not_a_copy(passage, name, quote):
    base = ('%s is not an exact, unbroken copy of passage text. Copy it letter for letter as one stretch: the same capital '
            'letters, the same punctuation, no word left out, no word added.' % name)
    if quote in passage.text:
        return ('%s starts or stops in the middle of a word. It must start at the start of a word and stop at the end of '
                'a word.' % name)
    lowered_text, lowered_quote = passage.text.lower(), quote.lower()
    if len(lowered_text) == len(passage.text):
        at = lowered_text.find(lowered_quote)
        if at >= 0:
            return base + " Only the capital letters differ. The passage has: '%s'." % passage.text[at:at + len(quote)]
    if '...' in quote or chr(0x2026) in quote:
        return base + " Do not use '...' to skip words."
    return base


def _inside(places, span):
    return [p for p in places if p[0] >= span[0] and p[1] <= span[1]]


def check_record(passage_text, record, passage_id=None, c9_asked=()):
    """Check one team's record for one passage. Reads form only; decides nothing about meaning.

    passage_text: the passage (or a Passage). record: the parsed JSON object. passage_id: the id the record must carry
    (None: not checked). c9_asked: the C9 keys this team was already asked about for this passage.

    Returns a dict:
      usable    R0 passed (the record can be read at all)
      passes    usable, and no entry fails C1 to C8
      accept    passes, and no new C9 question
      messages  every message, in order (R0 first, then entry by entry)
      entries   one dict per entry: entry (number from 1), noetic, certainty, class, stays_in_row, failed (checks C1..C8),
                may_be_removed (one of its messages says that the entry may be removed: C8, or C6 on a ^8 that names
                a ^9 reached by reasoning),
                asked_c9, messages, and health facts (label_words, support_sentences, support_widened, label_places)
      entries_stand  False when the record cannot be taken as this passage's record: another passage_id, or
                none_of_these true together with entries. The entries of such a try are not kept for putting back.
      c9_new    the C9 keys asked in this pass
      failed_checks  how many entries fail each check
    """
    passage = passage_text if isinstance(passage_text, Passage) else Passage(passage_text)
    result = {'checker': CHECKER, 'passage_id': passage_id, 'usable': True, 'passes': False, 'accept': False,
              'entries_stand': True,
              'record_messages': [], 'notices': [], 'entries': [], 'c9_new': [], 'failed_checks': {}, 'messages': []}

    def record_fail(text, entries_stand=True):
        result['usable'] = False
        if not entries_stand:
            result['entries_stand'] = False
        result['record_messages'].append('record: R0. ' + text)

    def finish():
        result['passes'] = result['usable'] and not any(e['failed'] for e in result['entries'])
        result['accept'] = result['passes'] and not result['c9_new']
        result['messages'] = list(result['record_messages']) + [m for e in result['entries'] for m in e['messages']]
        counts = {}
        for e in result['entries']:
            for check in e['failed']:
                counts[check] = counts.get(check, 0) + 1
        result['failed_checks'] = dict(sorted(counts.items()))
        return result

    if not isinstance(record, dict):
        record_fail('The record is not one JSON object. Send ONE JSON object with the keys passage_id, none_of_these, '
                    'entries, not_enough_information and guide_problem.')
        return finish()
    if passage_id is not None and record.get('passage_id') != passage_id:
        record_fail('passage_id is %s. It must be "%s".' % (_show(json.dumps(record.get('passage_id'))), passage_id),
                    entries_stand=False)
    none_of_these = record.get('none_of_these', False)
    if not isinstance(none_of_these, bool):
        record_fail('none_of_these must be true or false, without quotes.')
        none_of_these = False
    entries = record.get('entries')
    if entries is None and none_of_these:
        entries = []
    if not isinstance(entries, list):
        record_fail('"entries" must be a list of entry objects. Write "entries": [] when there is no entry.')
        return finish()
    not_objects = [str(k) for k, e in enumerate(entries, 1) if not isinstance(e, dict)]
    if not_objects:
        record_fail('Every item of "entries" must be a JSON object. Not an object: item %s.' % ', '.join(not_objects))
        return finish()
    if none_of_these and entries:
        record_fail('none_of_these is true, so "entries" must be empty. If you keep an entry, set none_of_these to false.',
                    entries_stand=False)
    if record.get('not_enough_information') is not None and not isinstance(record.get('not_enough_information'), list):
        result['notices'].append('not_enough_information should be a list of short notes.')
    if record.get('guide_problem') is not None and not isinstance(record.get('guide_problem'), str):
        result['notices'].append('guide_problem should be one short sentence of text, or "".')

    has_reasoned_9 = any(e.get('noetic') == '^9' and e.get('reached_by') == 'reasoning' for e in entries)
    work = []
    for number, entry in enumerate(entries, 1):
        problems = []
        noetic, certainty = entry.get('noetic'), entry.get('certainty')
        valid_noetic = isinstance(noetic, str) and noetic in NOETICS
        w = {'number': number, 'entry': entry, 'noetic': noetic if valid_noetic else None, 'problems': problems,
             'class': entry_class(entry), 'label_places': [], 'measure_places': [], 'mind_place': None, 'rel_places': [],
             'support_span': None, 'support_sentences': 0, 'support_widened': False, 'asked_c9': False,
             'reasoned': False,       # a ^9 with reached_by 'reasoning' (rule 15b), whatever else is wrong with it
             'remove_ok': 0}          # how many of its messages say that the entry may be removed
        for name in QUOTED_FIELDS:
            w[name] = _field(entry, name, problems)

        # C1: allowed values
        if not valid_noetic:
            problems.append(('C1', "noetic is %s. It must be one of '^1' to '^9'." % _show(json.dumps(noetic))))
        if certainty not in CERTAINTIES:
            problems.append(('C1', "certainty is %s. It must be 'clear', 'ambiguous' or 'held'." % _show(json.dumps(certainty))))
        other = entry.get('other_candidate')
        if certainty == 'ambiguous':
            if other in (None, ''):
                problems.append(('C1', "certainty is 'ambiguous', so other_candidate is needed: '^1' to '^9', 'none' or "
                                       "'reasoning'."))
            elif other not in OTHER_CANDIDATES:
                problems.append(('C1', "other_candidate is %s. It must be '^1' to '^9', 'none' or 'reasoning'."
                                 % _show(json.dumps(other))))
        elif other not in (None, ''):
            problems.append(('C1', "other_candidate is only for certainty 'ambiguous'. Leave it out."))
        held_under = entry.get('held_under')
        if certainty == 'held':
            if held_under in (None, ''):
                problems.append(('C1', "certainty is 'held', so held_under is needed: one of %s." % ', '.join(HOLD_CODES)))
            elif not isinstance(held_under, str) or held_under not in HOLD_CODES:
                problems.append(('C1', 'held_under is %s. It must be one of %s.'
                                 % (_show(json.dumps(held_under)), ', '.join(HOLD_CODES))))
            elif valid_noetic and noetic not in HOLD_CODES[held_under]:
                problems.append(('C1', 'held_under %s belongs to %s, not to %s.'
                                 % (held_under, ' and '.join(HOLD_CODES[held_under]), noetic)))
        elif held_under not in (None, ''):
            problems.append(('C1', "held_under is only for certainty 'held'. Leave it out."))
        reached_by = entry.get('reached_by')
        if reached_by not in (None, ''):
            if reached_by != 'reasoning':
                problems.append(('C1', "reached_by is %s. Its only value is 'reasoning'." % _show(json.dumps(reached_by))))
            elif noetic != '^9':
                problems.append(('C1', 'reached_by is only for a ^9 entry (rule 15b). Leave it out.'))
            else:
                w['reasoned'] = True
                if certainty == 'held':
                    problems.append(('C1', "reached_by 'reasoning' never goes with certainty 'held'. A conclusion the Mind "
                                           "worked out (rule 15b) is not a held kind. A held pair (rule 17, H89-FOLLOWS) has "
                                           'no reached_by. Decide by rules 15 and 17 which of the two this is.'))
                elif certainty == 'ambiguous' and other == 'reasoning':
                    problems.append(('C1', "reached_by 'reasoning' never goes with other_candidate 'reasoning'. "
                                           "other_candidate 'reasoning' is for the uncertain pair of rule 15(d), where each "
                                           'entry names the other. reached_by is for a conclusion the Mind worked out (rule '
                                           '15b). Use one or the other.'))
        clue = entry.get('clue')
        if clue is not None and not isinstance(clue, bool):
            problems.append(('C1', 'clue must be true, without quotes, or left out.'))
            clue = None
        if clue is True:
            if noetic != '^6':
                problems.append(('C1', 'clue is only for a ^6 entry. Leave it out.'))
            else:
                if not has_reasoned_9:
                    problems.append(('C1', "clue is true, but this record has no ^9 entry with reached_by 'reasoning'. "
                                           'Write clue only in such a passage (rule 7).'))
                if certainty in ('ambiguous', 'held'):
                    problems.append(('C1', "clue is true, so certainty must be 'clear' (rule 7). A missing whole is not a "
                                           "reason to write '%s'." % certainty))
        no_fuller = entry.get('no_fuller_name')
        if no_fuller is not None and not isinstance(no_fuller, bool):
            problems.append(('C1', 'no_fuller_name must be true, without quotes, or left out.'))
            no_fuller = None
        w['clue'], w['no_fuller'] = clue is True, no_fuller is True

        # C2: support
        if not w['support']:
            problems.append(('C2', 'support is empty. Copy the whole sentence or sentences from the passage.'))
        else:
            places = passage.occurrences(w['support'])
            if not places:
                problems.append(('C2', _not_a_copy(passage, 'support', w['support'])))
            else:
                wide = passage.widen(places[0])
                w['support_span'], w['support_widened'] = wide, wide != places[0]
                w['support_sentences'] = passage.sentences_in(wide)
                if w['support_sentences'] > MAX_SUPPORT_SENTENCES:
                    problems.append(('C2', 'support covers %d sentences. At most %d (rule 16, step 7).'
                                     % (w['support_sentences'], MAX_SUPPORT_SENTENCES)))

        # C3: label
        if not w['label']:
            hint = ' The field "words" is no longer used: write label and support.' if 'words' in entry else ''
            problems.append(('C3', 'label is empty. Every entry needs a label of 1 to %d words.%s' % (MAX_LABEL_WORDS, hint)))
        else:
            if word_count(w['label']) > MAX_LABEL_WORDS:
                problems.append(('C3', 'label has %d words. It must have 1 to %d. Stop after the %dth word.'
                                 % (word_count(w['label']), MAX_LABEL_WORDS, MAX_LABEL_WORDS)))
            places = passage.occurrences(w['label'])
            if not places:
                problems.append(('C3', _not_a_copy(passage, 'label', w['label'])))
            elif w['support_span']:
                inside = _inside(places, w['support_span'])
                if not inside:
                    problems.append(('C3', 'label is not inside support. The label is in the passage, but not in the '
                                           'sentences you copied as support. The support must hold the label.'))
                else:
                    # a ^1 label is located at the first place the name occurs in the passage, whatever the support
                    w['label_places'] = [places[0]] if noetic == '^1' else inside

        # C4: measure
        if noetic in ('^4', '^7'):
            if not w['measure']:
                problems.append(('C4', 'measure is empty. A ^4 or ^7 entry needs measure (rule 16, step 8).'))
            else:
                places = passage.occurrences(w['measure'])
                if not places:
                    problems.append(('C4', _not_a_copy(passage, 'measure', w['measure'])))
                elif w['support_span']:
                    w['measure_places'] = _inside(places, w['support_span'])
                    if not w['measure_places']:
                        problems.append(('C4', 'measure is not inside support. The support must hold the measure.'))
        elif valid_noetic and w['measure']:
            problems.append(('C4', 'measure is only for ^4 and ^7. Leave it empty for %s.' % noetic))

        # C7: pointer check on the label (never on a ^1 label)
        if valid_noetic and noetic != '^1' and w['label'] and not w['no_fuller']:
            reason = pointer_reason(w['label'])
            if reason:
                problems.append(('C7', 'label is a pointer: %s. A pointer is never a label (rule 16, steps 3 and 4). Use the '
                                       'naming it points at. Keep a pointer, with no_fuller_name true, only when no noun '
                                       'anywhere in the passage names the thing.' % reason))
        work.append(w)

    # the Minds of this record: the ^1 entries, by label
    minds = {}
    for w in work:
        if w['noetic'] == '^1' and w['label']:
            minds.setdefault(w['label'], []).append(w)
    mind_list = ', '.join("'%s'" % _show(m, 40) for m in minds) or 'none'

    for w in work:
        noetic, problems = w['noetic'], w['problems']
        w['partners'] = []
        # C5: mind, on the strings alone
        if noetic == '^1':
            if w['mind'] != w['label']:
                problems.append(('C5', "In a ^1 entry, mind equals its own label. mind is '%s' and label is '%s'."
                                 % (_show(w['mind'], 40), _show(w['label'], 40))))
        elif noetic == '^6':
            if w['mind']:
                problems.append(('C5', "mind must be empty in a ^6 entry. Write \"mind\": \"\". You wrote '%s'."
                                 % _show(w['mind'], 40)))
        elif noetic is not None:
            if not w['mind']:
                problems.append(('C5', 'mind is empty. Write the label of your ^1 entry for this Mind. '
                                       'Your ^1 labels: %s.' % mind_list))
            elif w['mind'] not in minds:
                problems.append(('C5', "mind '%s' is not the label of any of your ^1 entries. Copy that label character for "
                                       'character. Your ^1 labels: %s. Every Mind you name needs its own ^1 entry (rule 4).'
                                 % (_show(w['mind'], 40), mind_list)))

        # C6: relative_to, on the strings alone
        if noetic in ('^8', '^9'):
            want = '^9' if noetic == '^8' else '^8'
            if w['reasoned']:
                # rule 15(b): a conclusion reached by reasoning stands alone. 'Do not mark ^8'.
                if w['relative_to']:
                    problems.append(('C6', "relative_to must be empty in a ^9 with reached_by 'reasoning' (rule 15b: 'Do not "
                                           "mark ^8'). If the Mind worked this out, write \"relative_to\": \"\" and write no "
                                           '^8 for it. If the passage shows a thing bringing this Idea to Mind, it is a pair: '
                                           'leave reached_by out.'))
            elif not w['relative_to']:
                if noetic == '^8':
                    problems.append(('C6', 'relative_to is empty. A ^8 entry copies the label of its ^9 (rule 16, step 9).'))
                else:
                    problems.append(('C6', "relative_to is empty. A ^9 entry copies the label of its ^8 (rule 16, step 9). "
                                           "It is empty only with reached_by 'reasoning' (rule 15b)."))
            else:
                # a ^9 with reached_by 'reasoning' is never the partner of a ^8
                others = [o for o in work if o['noetic'] == want and not o['reasoned']]
                named = [o for o in others if o['label'] == w['relative_to']]
                same_mind = [o for o in named if o['mind'] == w['mind']]
                same_status = [o for o in same_mind if o['entry'].get('certainty') == w['entry'].get('certainty')
                               and (o['entry'].get('held_under') or '') == (w['entry'].get('held_under') or '')]
                back = [o for o in same_status if o['relative_to'] == w['label']]
                w['partners'] = back
                reasoned = [o for o in work if o['noetic'] == want and o['reasoned'] and o['label'] == w['relative_to']]
                if not named and reasoned:
                    problems.append(('C6', "relative_to names your ^9 entry %d, which has reached_by 'reasoning'. Rule 15(b) "
                                           "says 'Do not mark ^8' for a conclusion reached by reasoning. If the Mind worked "
                                           'the conclusion out, you may remove this ^8 entry. If the passage shows this thing '
                                           'bringing the Idea to Mind, it is a pair: leave reached_by out of entry %d and '
                                           'point its relative_to at this label.' % (reasoned[0]['number'], reasoned[0]['number'])))
                    w['remove_ok'] += 1
                elif not named:
                    labels = ', '.join("'%s'" % _show(o['label'], 50) for o in others) or 'none'
                    problems.append(('C6', "relative_to '%s' is not the label of any of your %s entries. Copy the label of "
                                           'the other member of the pair character for character (rule 16, step 9). '
                                           'Your %s labels: %s.' % (_show(w['relative_to'], 50), want, want, labels)))
                elif not same_mind:
                    problems.append(('C6', "relative_to copies the label of your %s entry %d, but that entry has mind '%s' "
                                           "and this entry has mind '%s'. Both entries of a pair carry the same mind."
                                     % (want, named[0]['number'], _show(named[0]['mind'], 40), _show(w['mind'], 40))))
                elif not same_status:
                    problems.append(('C6', 'relative_to copies the label of your %s entry %d, but the two entries differ in '
                                           'certainty or in held_under. Both entries of a pair carry the same certainty and '
                                           'the same held_under.' % (want, same_mind[0]['number'])))
                elif not back:
                    problems.append(('C6', "your %s entry %d does not point back at this entry. Its relative_to is '%s'. This "
                                           "entry's label is '%s'. In a pair, the relative_to of each entry is the label of "
                                           'the other. Write one %s entry for each %s (rule 16, step 10).'
                                     % (want, same_status[0]['number'], _show(same_status[0]['relative_to'], 50),
                                        _show(w['label'], 50), want, noetic)))
        elif noetic == '^6':
            if w['clue']:
                if w['relative_to']:
                    problems.append(('C6', 'relative_to must be empty when clue is true (rule 7): a clue is written with no '
                                           'whole. Write "relative_to": "". If this piece is a plain part of a named whole '
                                           'and not a clue, leave clue out.'))
            elif not w['relative_to']:
                problems.append(('C6', 'relative_to is empty. A ^6 entry needs the whole (rule 16, step 9). It is empty '
                                       'only for a clue, with clue true (rule 7).'))
            else:
                if word_count(w['relative_to']) > MAX_LABEL_WORDS:
                    problems.append(('C6', 'relative_to has %d words. The whole has 1 to %d words.'
                                     % (word_count(w['relative_to']), MAX_LABEL_WORDS)))
                places = passage.occurrences(w['relative_to'])
                if not places:
                    problems.append(('C6', _not_a_copy(passage, 'relative_to', w['relative_to'])))
                elif w['label_places']:
                    # the place of the whole that ends nearest before the part; if none before it, the first place
                    before = [p for p in places if p[1] <= w['label_places'][0][0]]
                    w['rel_places'] = [max(before, key=lambda p: p[1]) if before else places[0]]
                if not w['no_fuller']:
                    reason = pointer_reason(w['relative_to'])
                    if reason:
                        problems.append(('C7', 'relative_to is a pointer: %s. A pointer is never the whole (rule 16, step '
                                               '9b). Use the naming it points at. Keep a pointer, with no_fuller_name true, '
                                               'only when no noun anywhere in the passage names the thing.' % reason))
        elif noetic is not None and w['relative_to']:
            problems.append(('C6', 'relative_to is only for ^6, ^8 and ^9. Leave it empty for %s.' % noetic))

    # Entries lean on each other. A Mind is located through its ^1 entry, and a ^8 or ^9 through the other member of
    # its pair. An entry that fails is dropped in the end and then has no place (matching step 3), so an entry that
    # leans on it cannot be located either. It is told so now (C5, C6), while it can still be corrected. Then C8: no
    # two entries of one Noetic that the scorer's own test calls the same reading, whatever their certainty; the later
    # one fails. Repeated until nothing changes.
    changed = True
    while changed:
        changed = False
        for w in work:
            if w['problems'] or w['noetic'] is None:
                continue
            if w['noetic'] == '^1':
                w['mind_place'] = w['label_places'][0]
            elif w['mind']:
                standing = [o for o in minds[w['mind']] if not o['problems']]
                if not standing:
                    number = minds[w['mind']][0]['number']
                    w['problems'].append(('C5', 'mind copies the label of your ^1 entry %d, but entry %d fails a check. '
                                                'Correct entry %d.' % (number, number, number)))
                    changed = True
                    continue
                w['mind_place'] = standing[0]['label_places'][0]
            if w['noetic'] in ('^8', '^9') and w['relative_to']:
                standing = [o for o in w['partners'] if not o['problems']]
                if not standing:
                    number = w['partners'][0]['number']
                    w['problems'].append(('C6', 'the other member of the pair, entry %d, fails a check. Correct entry %d. '
                                                'If its label changes, copy the new label here.' % (number, number)))
                    changed = True
                    continue
                w['rel_places'] = standing[0]['label_places']
        kept = []
        for w in work:
            if w['problems'] or w['class'] is None:
                continue
            for earlier in kept:
                if earlier['noetic'] == w['noetic'] and _same_reading(passage, earlier, w):
                    if earlier['class'] == w['class']:
                        text = ('this entry repeats entry %d: the same Noetic, the same Mind, and labels that start at the '
                                'same place. Write one entry per thing, role and Mind (rule 16, step 10). Remove one of the '
                                'two.' % earlier['number'])
                    else:
                        text = ('this entry and entry %d are one thing written twice for the same Noetic%s: '
                                'entry %d is %s, this entry is %s. One thing gets one entry, whatever the certainty (rule '
                                '16, step 10). Decide by the guide which of the two it is. Remove the other.'
                                % (earlier['number'], '' if w['noetic'] in ('^1', '^6') else ' and the same Mind',
                                   earlier['number'], _status_words(earlier), _status_words(w)))
                    w['problems'].append(('C8', text))
                    w['remove_ok'] += 1
                    changed = True
                    break
            else:
                kept.append(w)

    # C9: one question, never a rejection
    asked = set(c9_asked)
    for w in work:
        if w['noetic'] in ('^2', '^3') and w['label'] and feeling_label(w['label']):
            key = c9_key(w['noetic'], w['mind'], w['label'])
            if key not in asked:
                w['asked_c9'] = True
                if key not in result['c9_new']:
                    result['c9_new'].append(key)

    for w in work:
        head = 'entry %d' % w['number']
        if w['noetic']:
            head += " (%s, label '%s')" % (w['noetic'], _show(w['label'], 50)) if w['label'] else ' (%s)' % w['noetic']
        failed, lines = [], []
        for check, text in w['problems']:
            if check not in failed:
                failed.append(check)
            lines.append('%s: %s. %s' % (head, check, text))
        if w['asked_c9']:
            lines.append('%s: C9 (a question, not a failure). %s' % (head, C9_MESSAGE))
        entry = w['entry']
        valid_row = w['class'] is not None
        result['entries'].append({'entry': w['number'], 'noetic': w['noetic'],
                                  'certainty': entry.get('certainty') if entry.get('certainty') in CERTAINTIES else None,
                                  'class': w['class'],
                                  'stays_in_row': valid_row, 'failed': sorted(failed),
                                  'may_be_removed': w['remove_ok'] > 0,
                                  'asked_c9': w['asked_c9'],
                                  'messages': lines, 'label_words': word_count(w['label']),
                                  'support_sentences': w['support_sentences'], 'support_widened': w['support_widened'],
                                  'label_places': len(w['label_places']), 'no_fuller_name': w['no_fuller']})
    return finish()


def _same_field(passage, p, q):
    if not p and not q:
        return True
    if not p or not q:
        return False
    return any(passage.same_thing(a, b) for a in p for b in q)


def _same_reading(passage, x, y):
    """Matching step 7 (tests R1 to R4), applied to two located entries of ONE team with the same Noetic (for check
    C8). Their classes may differ: one thing gets one entry, whatever the certainty (rule 16, step 10). One piece
    written both as a clue and as a plain part is compared by its label alone, because a clue has no whole."""
    noetic = x['noetic']
    if not x['label_places'] or not y['label_places'] or not _same_field(passage, x['label_places'], y['label_places']):
        return False
    if noetic not in ('^1', '^6'):
        if not _same_field(passage, [x['mind_place']] if x['mind_place'] else [], [y['mind_place']] if y['mind_place'] else []):
            return False
    if noetic in ('^8', '^9') or (noetic == '^6' and not x['clue'] and not y['clue']):
        if not _same_field(passage, x['rel_places'], y['rel_places']):
            return False
    if noetic in ('^4', '^7'):
        if not any(passage.overlap(a, b) for a in x['measure_places'] for b in y['measure_places']):
            return False
    return True


def _status_words(w):
    """How an entry is written, in the words of a C8 message."""
    entry = w['entry']
    certainty = entry.get('certainty')
    if certainty == 'held':
        return 'held under %s' % entry.get('held_under')
    if certainty == 'ambiguous':
        return "ambiguous (other_candidate '%s')" % entry.get('other_candidate')
    if w['noetic'] == '^6':
        return 'a clue' if w['clue'] else 'a plain part'
    if w['reasoned']:
        return 'reached by reasoning'
    return 'clear'


# ---------------------------------------------------------------- the three tries (the same loop for both teams)

def checker_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def record_sha256(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def text_sha256(passage_text):
    """The sha256 of a passage text after the one fixed clean-up. A try log keeps it, so that every try is tied to
    the text it was made on."""
    text = passage_text.text if isinstance(passage_text, Passage) else clean(passage_text)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def new_state():
    """The try state of one passage for one team."""
    return {'tries': [], 'c9_asked': [], 'final': None, 'final_record': None, 'passage_sha256': None, 'put_back': []}


def _dropped(result):
    return [{'entry': e['entry'], 'noetic': e['noetic'], 'certainty': e['certainty'], 'class': e['class'],
             'stays_in_row': e['stays_in_row'], 'checks': e['failed']} for e in result['entries'] if e['failed']]


def _per_noetic(result):
    """How many entries a record holds per Noetic. An entry whose every message allows removing it is not counted."""
    counts = {}
    for e in result['entries']:
        if not e['may_be_removed']:
            key = e['noetic'] or NO_NOETIC
            counts[key] = counts.get(key, 0) + 1
    return counts


def _label_of(entry):
    return clean(entry.get('label')) if isinstance(entry, dict) else ''


def _words_of(entry):
    """The content words of an entry's label and of its support, as two sets. Used only to tell which of several
    failed entries a labeler corrected and which it left out."""
    if not isinstance(entry, dict):
        return frozenset(), frozenset()
    return (frozenset(content_words(clean(entry.get('label')))), frozenset(content_words(clean(entry.get('support')))))


def _alike(x, y):
    """How alike two entries are: shared content words of the labels, counted twice, plus those of the supports."""
    return 2 * len(x[0] & y[0]) + len(x[1] & y[1])


def _left_out_first(candidates, held):
    """The failed entries of one try and one Noetic, the ones most surely left out first. Each failed entry is
    paired with the held entry that is most like it; a held entry is used once. A failed entry with no partner
    comes first, then the ones least like their partner, then the order in the record."""
    words = [_words_of(f['record']) for f in candidates]
    pairs = sorted(((_alike(w, h), c, k) for c, w in enumerate(words) for k, h in enumerate(held) if _alike(w, h) > 0),
                   key=lambda item: (-item[0], item[1], item[2]))
    partner, used = {}, set()
    for score, c, k in pairs:
        if c not in partner and k not in used:
            partner[c] = score
            used.add(k)
    order = sorted(range(len(candidates)), key=lambda c: (c in partner, partner.get(c, 0), c))
    return [candidates[c] for c in order]


def _put_back(earlier, record, result):
    """The entries that failed C1 to C7 on a try that was sent back and are missing from the final record.

    earlier: the tries before the final record. record, result: the final record and its check. The rule is in the
    text at the top of this file, section A FAILING ENTRY THAT IS LEFT OUT IS PUT BACK. Returns a list of
    {'from_try', 'entry_in_that_try', 'noetic', 'certainty', 'class', 'stays_in_row', 'checks', 'record'}."""
    have = _per_noetic(result)
    held = {}                         # per Noetic: the words of every entry the final row holds so far
    for e in result['entries']:
        held.setdefault(e['noetic'] or NO_NOETIC, []).append(_words_of(record['entries'][e['entry'] - 1]))
    back = []
    for attempt in reversed(earlier):
        had = attempt.get('per_noetic')
        if attempt.get('status') != 'TRY_AGAIN' or not had:
            continue
        stored = [f for f in attempt['failed'] if 'record' in f]
        for key in NOETICS + [NO_NOETIC]:
            gap = had.get(key, 0) - have.get(key, 0)
            if key == NO_NOETIC:      # no Noetic to count under: only when the record as a whole lost entries
                gap = min(gap, sum(had.values()) - sum(have.values()))
            if gap <= 0:
                continue
            candidates = [f for f in stored if (f['noetic'] or NO_NOETIC) == key]
            for f in _left_out_first(candidates, held.get(key, []))[:gap]:
                back.append({'from_try': attempt['try'], 'entry_in_that_try': f['entry'], 'noetic': f['noetic'],
                             'certainty': f['certainty'], 'class': f['class'], 'stays_in_row': f['stays_in_row'],
                             'checks': list(f['checks']), 'record': copy.deepcopy(f['record'])})
                have[key] = have.get(key, 0) + 1
                held.setdefault(key, []).append(_words_of(f['record']))
    back.sort(key=lambda item: (item['from_try'], item['entry_in_that_try']))
    return back


def _close(state, number, record, result, earlier):
    """Make the latest try final: LABELED, LABELED_WITH_DROPPED_ENTRIES or NOT_LABELED. `earlier` is the list of tries
    before this record. Returns (status, put_back)."""
    state['put_back'] = []
    if record is None or not result['usable']:
        state['final'] = {'status': 'NOT_LABELED', 'try': number, 'entries': 0, 'dropped': [], 'removed_after_reask': 0}
        state['final_record'] = None
        return 'FINAL_NOT_LABELED', []
    failing = _dropped(result)
    back = _put_back(earlier, record, result)
    sent = len(result['entries'])
    dropped = failing + [{'entry': sent + k, 'noetic': item['noetic'], 'certainty': item['certainty'],
                          'class': item['class'], 'stays_in_row': item['stays_in_row'], 'checks': item['checks'],
                          'removed_after_reask': True, 'from_try': item['from_try']} for k, item in enumerate(back, 1)]
    state['final'] = {'status': 'LABELED_WITH_DROPPED_ENTRIES' if dropped else 'LABELED', 'try': number,
                      'record_sha256': record_sha256(record), 'entries': sent + len(back), 'dropped': dropped,
                      'removed_after_reask': len(back)}
    state['final_record'] = copy.deepcopy(record)
    state['put_back'] = [item['record'] for item in back]
    return ('FINAL_WITH_DROPPED_ENTRIES' if failing else 'ACCEPTED'), back


def take_try(state, passage_id, passage_text, record, problem=None, extra=None):
    """One counted try. The same function for both teams.

    state: new_state() for this passage, kept between tries. record: the parsed JSON object, or None when no JSON
    object could be read (then `problem` says why). extra: facts to store with the try (the raw reply, token counts).
    Returns {'status', 'try', 'messages', 'result', 'put_back'}. status is ACCEPTED, TRY_AGAIN,
    FINAL_WITH_DROPPED_ENTRIES, FINAL_NOT_LABELED, or ALREADY_FINAL (nothing was counted). put_back lists the entries
    that failed on an earlier try, were left out of the final record and are kept as dropped (see _put_back).
    Raises UsageError, and counts nothing, when the passage text is not the text of the earlier tries.
    """
    if state.get('final'):
        return {'status': 'ALREADY_FINAL', 'try': state['final']['try'], 'messages': [], 'result': None, 'put_back': []}
    text_hash = text_sha256(passage_text)
    if state.get('passage_sha256') not in (None, text_hash):
        raise UsageError('passage %s: the passage text is not the text of the earlier tries. One passage, one text. '
                         'No try was counted.' % passage_id)
    state['passage_sha256'] = text_hash
    number = len(state['tries']) + 1
    result = check_record(passage_text, record, passage_id, state['c9_asked'])
    if record is None:
        result['record_messages'] = ['record: R0. ' + (problem or 'No JSON object could be read. Send ONE JSON object and '
                                                                  'nothing else.')]
        result['messages'] = list(result['record_messages'])
    state['c9_asked'] = list(state['c9_asked']) + [k for k in result['c9_new'] if k not in state['c9_asked']]
    back = []
    if result['accept'] or number >= MAX_TRIES:
        # the last try is final whatever it holds; a C9 question alone never keeps a record open on the last try
        status, back = _close(state, number, record, result, state['tries'])
        state.pop('last_record', None)
    else:
        status = 'TRY_AGAIN'
        state['last_record'] = copy.deepcopy(record)
    # A try that is sent back keeps each entry that failed C1 to C7, so that it cannot vanish from a later try.
    keep = status == 'TRY_AGAIN' and result['entries_stand'] and bool(result['entries'])
    failed = []
    for e in result['entries']:
        if not e['failed']:
            continue
        item = {'entry': e['entry'], 'noetic': e['noetic'], 'certainty': e['certainty'], 'class': e['class'],
                'stays_in_row': e['stays_in_row'], 'checks': e['failed'], 'may_be_removed': e['may_be_removed']}
        if keep and not e['may_be_removed']:
            item['record'] = copy.deepcopy(record['entries'][e['entry'] - 1])
        failed.append(item)
    entry = {'try': number, 'status': status, 'usable': result['usable'],
             'record_sha256': record_sha256(record) if record is not None else None,
             'entries': len(result['entries']),
             'failed': failed,
             'asked_c9': [{'entry': e['entry'], 'noetic': e['noetic']} for e in result['entries'] if e['asked_c9']],
             'messages': list(result['messages'])}
    if result['entries_stand'] and result['entries']:
        entry['per_noetic'] = _per_noetic(result)     # read by _put_back for a try that was sent back
    if back:
        entry['put_back'] = [{k: v for k, v in item.items() if k != 'record'} for item in back]
    if extra:
        entry.update(extra)
    state['tries'].append(entry)
    return {'status': status, 'try': number, 'messages': list(result['messages']), 'result': result, 'put_back': back}


def close_unfinished(state, passage_text, passage_id):
    """Make the last try of an unfinished passage final, as if no try were left. Used only on an explicit request."""
    if state.get('final') or not state['tries']:
        return
    last = state.pop('last_record', None)
    result = check_record(passage_text, last, passage_id, state['c9_asked'])
    _close(state, len(state['tries']), last, result, state['tries'][:-1])
    state['final']['closed_before_third_try'] = True


def describe(passage_id, outcome, again='Then run the checker on the whole record again.'):
    """The lines a labeler reads after one try. Both teams get these lines; only the last sentence (`again`) says how
    the next try is handed in."""
    status, number = outcome['status'], outcome['try']
    head = 'passage %s: try %d of %d: ' % (passage_id, number, MAX_TRIES)
    problems = [m for m in outcome['messages'] if ': C9 (a question' not in m]
    lines = []
    if status == 'ACCEPTED':
        lines.append(head + 'ACCEPTED. The record is final. Do not change it.')
        if outcome['messages']:
            lines.append('A C9 question came up on the last try. It is never a failure. The label is accepted as sent.')
    elif status == 'TRY_AGAIN':
        lines.append(head + 'TRY AGAIN. %d problem%s, %d question%s.' % (
            len(problems), '' if len(problems) == 1 else 's', len(outcome['messages']) - len(problems),
            '' if len(outcome['messages']) - len(problems) == 1 else 's'))
        lines += ['  ' + m for m in outcome['messages']]
        lines.append(FORM_ONLY)
        lines.append(KEEP_EVERY_ENTRY)
        lines.append('Correct what the messages name. ' + again)
    elif status == 'FINAL_WITH_DROPPED_ENTRIES':
        lines.append(head + 'FINAL. The three tries are used. The record stays as it is. Do not change it.')
        lines.append('Entries that still fail are counted as dropped:')
        lines += ['  ' + m for m in problems]
    elif status == 'FINAL_NOT_LABELED':
        lines.append(head + 'FINAL, NOT LABELED. The three tries are used and the record cannot be read.')
        lines += ['  ' + m for m in problems]
    back = outcome.get('put_back') or []
    if back:
        lines.append('%d entr%s failed a check on an earlier try and %s not in this record. The program keeps %s and counts '
                     '%s as dropped:' % (len(back), 'y' if len(back) == 1 else 'ies', 'is' if len(back) == 1 else 'are',
                                         'it' if len(back) == 1 else 'them', 'it' if len(back) == 1 else 'them'))
        for item in back:
            lines.append("  try %d, entry %d (%s, label '%s'): failed %s" % (
                item['from_try'], item['entry_in_that_try'], item['noetic'] or NO_NOETIC,
                _show(_label_of(item['record']), 50), ', '.join(item['checks'])))
    return lines


# ---------------------------------------------------------------- try logs and the final labels file

def new_log():
    return {'format': TRIES_FORMAT, 'checker': CHECKER, 'checker_sha256': checker_sha256(), 'max_tries': MAX_TRIES,
            'passages': {}}


def load_log(path):
    path = Path(path)
    if not path.exists():
        return new_log()
    log = json.loads(path.read_text(encoding='utf-8'))
    if log.get('format') != TRIES_FORMAT:
        raise UsageError('%s is not a try log of this checker.' % path)
    if log.get('checker_sha256') != checker_sha256():
        raise UsageError('%s was written by another version of the checker. One run uses one checker.' % path)
    return log


def write_json(path, data):
    """Write through a .partial file, then rename. LF line ends, UTF-8."""
    path = Path(path)
    partial = path.with_name(path.name + '.partial')
    partial.write_text(json.dumps(data, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))
    os.replace(partial, path)


def load_passages(path):
    """The passages as a list of (id, text). Refuses a passage file that holds anything but id and text, so that a
    file with the writer's kinds is never handed to a label team by mistake."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(data, dict) and 'id' in data and 'text' in data:
        data = [data]
    if isinstance(data, dict):
        return [(str(k), v) for k, v in data.items()]
    if not isinstance(data, list) or not all(isinstance(p, dict) and 'id' in p and 'text' in p for p in data):
        raise UsageError('the passage file must be a JSON list of {"id": ..., "text": ...}.')
    extra = sorted({k for p in data for k in p} - {'id', 'text'})
    if extra:
        raise UsageError('the passage file has other fields than id and text (%s). Label teams must not see those. '
                         'Give the passage file that holds only id and text.' % ', '.join(extra))
    return [(p['id'], p['text']) for p in data]


def sent_back_items(state):
    """One item per failed check per try that was sent back: {"try", "entry", "noetic", "check"}. The scorer reads
    this list as "reasks". R0 is the record as a whole; C9 is the question."""
    items = []
    for attempt in (state or {}).get('tries', []):
        if attempt['status'] != 'TRY_AGAIN':
            continue
        if not attempt['usable']:
            items.append({'try': attempt['try'], 'entry': None, 'noetic': 'record', 'check': 'R0'})
        for failed in attempt['failed']:
            for check in failed['checks']:
                items.append({'try': attempt['try'], 'entry': failed['entry'],
                              'noetic': failed['noetic'] or 'no valid Noetic', 'check': check})
        for asked in attempt['asked_c9']:
            items.append({'try': attempt['try'], 'entry': asked['entry'], 'noetic': asked['noetic'], 'check': 'C9'})
    return items


def _plain_entry(entry):
    """An entry as it is written into a final row: no mark of this program's names, and no optional field with an
    empty value (left out and empty mean the same; one spelling only)."""
    entry = copy.deepcopy(entry)
    for key in MARKS:
        entry.pop(key, None)
    for key, empty in EMPTY_OPTIONALS.items():
        if key in entry and any(entry[key] is value or (isinstance(value, str) and entry[key] == value) for value in empty):
            del entry[key]
    return entry


def final_row(passage_id, state):
    """One row of the final labels file: the record as the labeler last sent it, then the entries that were put back
    (see _put_back), plus the marks the scorer reads. The marks are written here and nowhere else. A mark of the same
    name written by a labeler is thrown away."""
    blank = {'passage_id': passage_id, 'none_of_these': False, 'entries': [], 'not_enough_information': [],
             'guide_problem': ''}
    tries = len(state['tries']) if state else 0
    final = state.get('final') if state else None
    reasks = sent_back_items(state)
    if not final:
        return dict(blank, labeler_failed=True, reasks=reasks,
                    checker={'checker': CHECKER, 'tries': tries, 'final': 'UNFINISHED' if tries else 'NOT_ATTEMPTED',
                             'dropped': [], 'removed_after_reask': 0})
    block = {'checker': CHECKER, 'tries': tries, 'final': final['status'], 'dropped': final['dropped'],
             'removed_after_reask': final.get('removed_after_reask', 0)}
    if final.get('closed_before_third_try'):
        block['closed_before_third_try'] = True
    if final['status'] == 'NOT_LABELED':
        return dict(blank, labeler_failed=True, reasks=reasks, checker=block)
    row = copy.deepcopy(state['final_record'])
    for key in ('labeler_failed', 'reasks', 'checker'):
        row.pop(key, None)
    for key, value in blank.items():
        row.setdefault(key, value)
    put_back = state.get('put_back') or []
    row['entries'] = [_plain_entry(entry) for entry in (row['entries'] or [])] + [_plain_entry(entry) for entry in put_back]
    for drop in final['dropped']:
        entry = row['entries'][drop['entry'] - 1]
        entry['dropped'] = True
        entry['failed_checks'] = list(drop['checks'])
        if drop.get('removed_after_reask'):
            entry['removed_after_reask'] = True
    if put_back and row['none_of_these'] is True:
        row['none_of_these'] = False       # a row never holds none_of_these true together with entries
        block['none_of_these_as_sent'] = True
    row['reasks'] = reasks
    row['checker'] = block
    return row


def summarize(rows):
    """Counts for the health table: passages by final status, entries, drops, drops per check and per Noetic, and the
    same counts for the dropped entries that were put back after a labeler left them out."""
    out = {'passages': len(rows), 'by_final': {}, 'entries': 0, 'dropped': 0, 'dropped_no_row': 0,
           'dropped_per_check': {}, 'dropped_per_noetic': {}, 'removed_after_reask': 0,
           'removed_after_reask_per_check': {}, 'removed_after_reask_per_noetic': {}, 'closed_before_third_try': 0}
    for row in rows:
        final = row['checker']['final']
        out['by_final'][final] = out['by_final'].get(final, 0) + 1
        out['entries'] += len(row['entries'])
        out['closed_before_third_try'] += 1 if row['checker'].get('closed_before_third_try') else 0
        for drop in row['checker']['dropped']:
            out['dropped'] += 1
            out['dropped_no_row'] += 0 if drop['stays_in_row'] else 1
            for check in drop['checks']:
                out['dropped_per_check'][check] = out['dropped_per_check'].get(check, 0) + 1
            name = drop['noetic'] or 'no row'
            out['dropped_per_noetic'][name] = out['dropped_per_noetic'].get(name, 0) + 1
            if drop.get('removed_after_reask'):
                out['removed_after_reask'] += 1
                for check in drop['checks']:
                    out['removed_after_reask_per_check'][check] = out['removed_after_reask_per_check'].get(check, 0) + 1
                out['removed_after_reask_per_noetic'][name] = out['removed_after_reask_per_noetic'].get(name, 0) + 1
    for name in ('by_final', 'dropped_per_check', 'dropped_per_noetic', 'removed_after_reask_per_check',
                 'removed_after_reask_per_noetic'):
        out[name] = dict(sorted(out[name].items()))
    out['dropped_share'] = out['dropped'] / out['entries'] if out['entries'] else 0.0
    not_labeled = sum(v for k, v in out['by_final'].items() if k in ('NOT_LABELED', 'UNFINISHED', 'NOT_ATTEMPTED'))
    out['not_labeled_share'] = not_labeled / len(rows) if rows else 0.0
    return out


def count_tries(logs):
    """Counts from try logs, the same for both teams: how many tries each final passage used, and how often each check
    sent a record back (per check and per Noetic). R0 is the record as a whole; C9 is the question."""
    out = {'passages_with_tries': 0, 'final_on_try': {}, 'sent_back': 0, 'sent_back_per_check': {}, 'sent_back_per_noetic': {}}

    def add(table, key):
        table[key] = table.get(key, 0) + 1

    for log in logs:
        for state in log['passages'].values():
            if not state['tries']:
                continue
            out['passages_with_tries'] += 1
            if state.get('final'):
                add(out['final_on_try'], str(state['final']['try']))
            for attempt in state['tries']:
                if attempt['status'] != 'TRY_AGAIN':
                    continue
                out['sent_back'] += 1
                if not attempt['usable']:
                    add(out['sent_back_per_check'], 'R0')
                for failed in attempt['failed']:
                    for check in failed['checks']:
                        add(out['sent_back_per_check'], check)
                        add(out['sent_back_per_noetic'], '%s %s' % (failed['noetic'] or 'no row', check))
                for asked in attempt['asked_c9']:
                    add(out['sent_back_per_check'], 'C9')
                    add(out['sent_back_per_noetic'], '%s C9' % asked['noetic'])
    for name in ('final_on_try', 'sent_back_per_check', 'sent_back_per_noetic'):
        out[name] = dict(sorted(out[name].items()))
    return out


def export_rows(passages, logs):
    """The final labels file as a list of rows in passage order, from one or more try logs."""
    states, twice = {}, []
    for log in logs:
        for passage_id, state in log['passages'].items():
            if passage_id in states and states[passage_id]['tries'] and state['tries']:
                twice.append(passage_id)
            if passage_id not in states or state['tries']:
                states[passage_id] = state
    if twice:
        raise UsageError('These passages have tries in more than one log: %s. One labeler per passage.'
                         % ', '.join(sorted(twice)))
    known = {p for p, _ in passages}
    strangers = sorted(set(states) - known)
    if strangers:
        raise UsageError('The logs hold passages that are not in the passage file: %s.' % ', '.join(strangers[:10]))
    other_text = sorted(passage_id for passage_id, text in passages
                        if (states.get(passage_id) or {}).get('passage_sha256') not in (None, text_sha256(text)))
    if other_text:
        raise UsageError('The tries of these passages were made on another text than the text in this passage file: %s. '
                         'Labels and passages must belong together.' % ', '.join(other_text[:10]))
    return [final_row(passage_id, states.get(passage_id)) for passage_id, _ in passages]


# ---------------------------------------------------------------- the seal record and the receipt

SEAL_ROLE_WORDS = {'guide': 'labeling guide', 'instructions': 'labeler instructions', 'checker': 'checker',
                   'passages': 'passage file', 'launch_text': 'launch text', 'team_b_tool': 'team B labeling tool'}
# Where a record of tools/seal_v2.py keeps the sha256 of a role. SEAL.json keeps each role at the top.
# PRACTICE_SET.json keeps them under "files_when_this_practice_set_was_written" and its passages under
# "practice_passages". Each node is {"file": ..., "sha256": ...}.
_SEAL_NODES = {'guide': ('guide',), 'checker': ('checker',), 'passages': ('passages', 'practice_passages'),
               'instructions': ('instructions',), 'launch_text': ('team_a_launch',), 'team_b_tool': ('team_b_tool',)}
_SEAL_BOXES = ('files_when_this_practice_set_was_written',)
_SEAL_FILE_NAMES = {'instructions': ('LABELER_INSTRUCTIONS.txt',), 'launch_text': ('TEAM_A_LAUNCH.txt',),
                    'team_b_tool': ('label_outside_v2.py',)}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def read_seal(path):
    try:
        seal = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise UsageError('cannot read the seal record %s: %s' % (path, error))
    if not isinstance(seal, dict):
        raise UsageError('the seal record %s is not one JSON object.' % path)
    return seal


def sealed_sha256(seal, role, file_name=None):
    """The sha256 a seal record holds for a role, or None. It is looked for as a node of its own ({"sha256": ...}),
    at the top or in the practice record's box, then in the list "also_hashed" by file name, then in "tools_sha256"
    by file name."""
    boxes = [seal] + [seal[box] for box in _SEAL_BOXES if isinstance(seal.get(box), dict)]
    for box in boxes:
        for name in _SEAL_NODES.get(role, (role,)):
            node = box.get(name)
            if isinstance(node, dict) and isinstance(node.get('sha256'), str):
                return node['sha256'].lower()
    if role == 'passages' and isinstance(seal.get('passages_sealed_sha256'), str):
        return seal['passages_sealed_sha256'].lower()
    names = set(_SEAL_FILE_NAMES.get(role, ())) | ({file_name} if file_name else set())
    for item in seal.get('also_hashed') or []:
        if isinstance(item, dict) and item.get('file') in names and isinstance(item.get('sha256'), str):
            return item['sha256'].lower()
    tools = seal.get('tools_sha256')
    for name in sorted(names):
        if isinstance(tools, dict) and isinstance(tools.get(name), str):
            return tools[name].lower()
    return None


def check_against_seal(seal_path, files):
    """Compare files with a seal record. files: role -> path, or None when no file was named for the role.
    Returns (problems, info). An empty list of problems means every named file has the sha256 the record holds.
    A role the record holds no sha256 for is a problem: nothing is taken on trust."""
    seal = read_seal(seal_path)
    info = {'file': Path(seal_path).name, 'sha256': sha256_file(seal_path), 'schema': seal.get('schema'),
            'is_a_seal': seal.get('is_a_seal') is True, 'compared': {}}
    problems = []
    for role, path in files.items():
        words = SEAL_ROLE_WORDS.get(role, role)
        if path is None:
            if role == 'launch_text' and sealed_sha256(seal, role) is not None:
                problems.append('the seal record holds a sha256 for the %s, but no %s was named' % (words, words))
            continue
        if not Path(path).is_file():
            problems.append('the %s was not found: %s' % (words, path))
            continue
        actual, sealed = sha256_file(path), sealed_sha256(seal, role, Path(path).name)
        info['compared'][role] = {'file': Path(path).name, 'sha256': actual, 'sha256_in_seal_record': sealed}
        if sealed is None:
            problems.append('the seal record holds no sha256 for the %s (%s)' % (words, Path(path).name))
        elif sealed != actual:
            problems.append('the %s %s has sha256 %s, but the seal record says %s' % (words, Path(path).name, actual, sealed))
    return problems, info


def receipt_core(written_by, labels_path, passages_path, rows, guide=None, instructions=None, seal_info=None):
    """The keys every labels receipt has, whichever tool wrote the labels file. The scorer can tie a labels file to
    the sealed checker, guide and passages by these."""
    summary = summarize(rows)
    open_ids = [row['passage_id'] for row in rows if row['checker']['final'] in ('UNFINISHED', 'NOT_ATTEMPTED')]
    return {'format': RECEIPT_FORMAT, 'written_by': written_by, 'written_utc': now_utc(),
            'labels_file': Path(labels_path).name, 'labels_sha256': sha256_file(labels_path),
            'passages_file': Path(passages_path).name, 'passages_sha256': sha256_file(passages_path),
            'checker': CHECKER, 'checker_sha256': checker_sha256(),
            'guide_file': Path(guide).name if guide else None, 'guide_sha256': sha256_file(guide) if guide else None,
            'instructions_file': Path(instructions).name if instructions else None,
            'instructions_sha256': sha256_file(instructions) if instructions else None,
            'seal_record': seal_info,
            'complete': not open_ids, 'every_passage_final': not open_ids, 'open_passages': open_ids,
            'closed_before_third_try': summary['closed_before_third_try'],
            'removed_after_reask': summary['removed_after_reask'],
            'summary': summary}


# ---------------------------------------------------------------- command line

def _plain_check(passages, rows):
    texts = dict(passages)
    totals = {'records': 0, 'not_labeled': 0, 'failing_records': 0, 'entries': 0, 'failing_entries': 0, 'checks': {},
              'questions': 0}
    print('Plain check. Nothing is counted. A labeler checks its own record with --tries, never this way.')
    for row in rows:
        totals['records'] += 1
        passage_id = row.get('passage_id') if isinstance(row, dict) else None
        if not isinstance(passage_id, str) or passage_id not in texts:
            print('record %d: R0. passage_id %s is not in the passage file.' % (totals['records'], _show(json.dumps(passage_id))))
            totals['failing_records'] += 1
            continue
        if row.get('labeler_failed'):
            totals['not_labeled'] += 1
            print('passage %s: not labeled by this team.' % passage_id)
            continue
        result = check_record(texts[passage_id], row, passage_id)
        totals['entries'] += len(result['entries'])
        totals['failing_entries'] += sum(1 for e in result['entries'] if e['failed'])
        totals['questions'] += sum(1 for e in result['entries'] if e['asked_c9'])
        for check, count in result['failed_checks'].items():
            totals['checks'][check] = totals['checks'].get(check, 0) + count
        if not result['passes']:
            totals['failing_records'] += 1
        if result['messages']:
            print('passage %s: %s' % (passage_id, 'PASS' if result['passes'] else 'FAIL'))
            for line in result['messages']:
                print('  ' + line)
        elif len(rows) == 1:
            print('passage %s: PASS' % passage_id)
    share = totals['failing_entries'] / totals['entries'] if totals['entries'] else 0.0
    print('checked %d record%s: %d fail, %d not labeled | %d entries, %d fail C1 to C8 (share %.4f) | per check %s | C9 '
          'questions %d' % (totals['records'], '' if totals['records'] == 1 else 's', totals['failing_records'],
                            totals['not_labeled'], totals['entries'], totals['failing_entries'], share,
                            json.dumps(dict(sorted(totals['checks'].items()))), totals['questions']))
    print(FORM_ONLY)
    return 1 if totals['failing_records'] or totals['not_labeled'] else 0


def _counted_tries(passages, labels_path, log_path, forced_id):
    """One counted try for each record in the file. Which passage a one-record file is for: --id, else the file
    name when it is a passage id, else the record's own passage_id."""
    texts = dict(passages)
    log = load_log(log_path)
    stem = Path(labels_path).stem
    try:
        data = json.loads(Path(labels_path).read_text(encoding='utf-8'))
        problem = None
    except ValueError as error:
        data, problem = None, 'The file is not valid JSON (%s). Write ONE JSON object.' % str(error)[:120]
    if isinstance(data, list):
        if forced_id:
            raise UsageError('--id is for a file that holds one record.')
        rows = [(row.get('passage_id') if isinstance(row, dict) else None, row) for row in data]
    else:
        own = data.get('passage_id') if isinstance(data, dict) else None
        rows = [(forced_id or (stem if stem in texts else own), data)]
    unknown = [json.dumps(p) for p, _ in rows if not isinstance(p, str) or p not in texts]
    if unknown:
        raise UsageError('The passage is not known (%s), so no try was counted. Name the file after the passage, or add '
                         '--id.%s' % (', '.join(unknown[:5]), ' ' + problem if problem else ''))
    other_text = [p for p, _ in rows if (log['passages'].get(p) or {}).get('passage_sha256')
                  not in (None, text_sha256(texts[p]))]
    if other_text:
        raise UsageError('The passage text of %s is not the text of the earlier tries in this log. One passage, one text. '
                         'No try was counted.' % ', '.join(other_text[:5]))
    statuses = []
    for passage_id, row in rows:
        state = log['passages'].setdefault(passage_id, new_state())
        outcome = take_try(state, passage_id, texts[passage_id], row, problem)
        if outcome['status'] == 'ALREADY_FINAL':
            final = state['final']
            same = row is not None and final.get('record_sha256') == record_sha256(row)
            print('passage %s: already final (%s, try %d). No try was counted.%s' % (
                passage_id, final['status'], final['try'],
                '' if same else ' The file differs from the final record. The change is not taken.'))
            statuses.append('ACCEPTED' if same and final['status'] == 'LABELED' else 'FINAL')
            continue
        statuses.append(outcome['status'])
        for line in describe(passage_id, outcome):
            print(line)
    write_json(log_path, log)
    if 'TRY_AGAIN' in statuses:
        return 1
    return 0 if all(status == 'ACCEPTED' for status in statuses) else 3


def _export(passages, args):
    """Write the final labels file from try logs, and its receipt. With --seal nothing is written unless the files
    have the sha256 that the seal record holds."""
    out_path, close = args.export, args.close_unfinished
    paths = []
    for pattern in args.tries:
        paths += sorted(glob.glob(pattern)) or [pattern]
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        raise UsageError('cannot find the try log %s' % ', '.join(missing))
    for name, path in (('--guide', args.guide), ('--instructions', args.instructions), ('--launch-text', args.launch_text)):
        if path and not Path(path).is_file():
            raise UsageError('cannot find the file named with %s: %s' % (name, path))
    seal_info = None
    if args.seal:
        if not args.guide or not args.instructions:
            raise UsageError('with --seal, name the guide and the instructions the labelers were given: --guide G '
                             '--instructions I.')
        problems, seal_info = check_against_seal(args.seal, {
            'checker': __file__, 'passages': args.passages, 'guide': args.guide, 'instructions': args.instructions,
            'launch_text': args.launch_text})
        if problems:
            raise UsageError('the files do not match the seal record %s. Nothing was written. %s.'
                             % (Path(args.seal).name, '; '.join(problems)))
    logs = [load_log(p) for p in paths]
    texts = dict(passages)
    if close:
        for log in logs:
            for passage_id, state in log['passages'].items():
                if passage_id in texts:
                    close_unfinished(state, texts[passage_id], passage_id)
    rows = export_rows(passages, logs)
    write_json(out_path, rows)
    receipt = receipt_core('check_labels_v2.py --export', out_path, args.passages, rows, args.guide, args.instructions,
                           seal_info)
    receipt.update({
        'launch_text_file': Path(args.launch_text).name if args.launch_text else None,
        'launch_text_sha256': sha256_file(args.launch_text) if args.launch_text else None,
        'try_logs': [{'file': Path(p).name, 'sha256': sha256_file(p), 'checker_sha256': log.get('checker_sha256'),
                      'passages_with_tries': sum(1 for s in log['passages'].values() if s['tries'])}
                     for p, log in zip(paths, logs)],
        'close_unfinished_was_used': bool(close),
        'tries': count_tries(logs),
        'what_this_receipt_cannot_show': 'Which guide a labeler who works by hand really read. The guide, instructions '
                                         'and launch text hashes are the files named at export.'})
    receipt_path = Path(out_path).with_name(Path(out_path).name + '.receipt.json')
    write_json(receipt_path, receipt)
    summary = receipt['summary']
    print('wrote %s from %d try log%s, and the receipt %s' % (out_path, len(logs), '' if len(logs) == 1 else 's',
                                                               receipt_path.name))
    print(json.dumps(summary, indent=1))
    print(json.dumps(receipt['tries'], indent=1))
    if summary['removed_after_reask']:
        print('%d entr%s failed a check, then left out by the labeler, put back and counted as dropped: per check %s, per '
              'Noetic %s' % (summary['removed_after_reask'], 'y' if summary['removed_after_reask'] == 1 else 'ies',
                             json.dumps(summary['removed_after_reask_per_check']),
                             json.dumps(summary['removed_after_reask_per_noetic'])))
    if close:
        print('--close-unfinished was used: %d row%s closed before the third try. Each is marked '
              '"closed_before_third_try".' % (summary['closed_before_third_try'],
                                               '' if summary['closed_before_third_try'] == 1 else 's'))
    open_rows = len(receipt['open_passages'])
    if open_rows:
        print('%d passage%s not final. Resume each one with its own try log until it is final.'
              % (open_rows, ' is' if open_rows == 1 else 's are'))
    return 1 if open_rows else 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Format checker for label records, guide v2.0. Reads form only.')
    parser.add_argument('passages', nargs='?', help='the passage file: a JSON list of {"id", "text"}')
    parser.add_argument('labels', nargs='?', help='one record (a JSON object) or a labels file (a JSON list of records)')
    parser.add_argument('--tries', nargs='+', metavar='LOG', help='count one try per record and keep the try log here')
    parser.add_argument('--id', help='the passage id, when the record file cannot say it')
    parser.add_argument('--export', metavar='OUT', help='write the final labels file from the try logs, and its receipt')
    parser.add_argument('--guide', help='with --export: the labeling guide the labelers were given (hashed into the receipt)')
    parser.add_argument('--instructions', help='with --export: the labeler instructions they were given')
    parser.add_argument('--launch-text', help='with --export: the fixed launch text they were given')
    parser.add_argument('--seal', help='with --export: SEAL.json or PRACTICE_SET.json; refuse unless the files match it')
    parser.add_argument('--close-unfinished', action='store_true',
                        help='with --export: make the last try of an unfinished passage final')
    parser.add_argument('--recipe', action='store_true', help='print the fixed recipe for a labeler who runs the checker by hand')
    args = parser.parse_args(argv)
    if args.recipe:
        sys.stdout.flush()
        sys.stdout.buffer.write(TEAM_A_RECIPE.encode('utf-8'))     # bytes, so that the line ends stay LF on every system
        sys.stdout.buffer.flush()
        return 0
    try:
        if not args.passages:
            raise UsageError('give the passage file.')
        if not args.export and (args.guide or args.instructions or args.launch_text or args.seal or args.close_unfinished):
            raise UsageError('--guide, --instructions, --launch-text, --seal and --close-unfinished go with --export only.')
        try:
            passages = load_passages(args.passages)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise UsageError('cannot read the passage file: %s' % error)
        if args.export:
            if not args.tries or args.labels:
                raise UsageError('--export needs --tries LOG [LOG ...] and no labels file.')
            return _export(passages, args)
        if not args.labels:
            raise UsageError('give a record file or a labels file to check.')
        if not Path(args.labels).exists():
            raise UsageError('cannot find %s' % args.labels)
        if args.tries:
            if len(args.tries) != 1:
                raise UsageError('a counted try uses exactly one try log.')
            return _counted_tries(passages, args.labels, args.tries[0], args.id)
        try:
            data = json.loads(Path(args.labels).read_text(encoding='utf-8'))
        except ValueError as error:
            print('record: R0. The file is not valid JSON (%s).' % str(error)[:120])
            return 1
        return _plain_check(passages, data if isinstance(data, list) else [data])
    except UsageError as error:
        print('command not run: %s' % error)
        return 2


if __name__ == '__main__':
    sys.exit(main())
