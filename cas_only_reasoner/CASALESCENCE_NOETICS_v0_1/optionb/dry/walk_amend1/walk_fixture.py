"""[MADE-UP DATA WALK, NOT A RESULT] The made-up people, passages, questions and notes of the walk.

Everything here is made up. No real passage, label, question or note is read or copied.
This module is shared by 01_make_fixture.py (which writes the made-up source files) and by
walk_stub.py (which stands in for the outside services inside the walk).
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LF = chr(10)

NAME_PARTS = ['Tam', 'Odr', 'Ils', 'Bram', 'Mar', 'Cor', 'Edd', 'Joss', 'Wren', 'Fenn', 'Lies', 'Ans', 'Petr', 'Hal', 'Sunn']
NAME_ENDS = ['a', 'en', 'in', 'o', 'is', 'et', 'ol', 'ic', 'ar', 'ey']
ADJ_PAIRS = [('tar', 'wire'), ('bone', 'steel'), ('oak', 'tin'), ('copper', 'iron'), ('hemp', 'nylon'), ('wicker', 'mesh'),
             ('wooden', 'metal'), ('brass', 'plastic'), ('long', 'short'), ('small', 'large'), ('curved', 'straight'),
             ('fine', 'flat'), ('birch', 'zinc')]
NOUNS = ['brush', 'needle', 'scoop', 'hammer', 'ladle', 'tray', 'mould', 'ruler', 'saw', 'spindle', 'rake']
DISLIKED = ['bilge pump', 'rusty winch', 'damp cellar', 'leaky bellows', 'lye vat', 'loose stair', 'broken ladder']
OBJECTS = ['lantern', 'kettle', 'ledger', 'bucket', 'rack', 'oilcan', 'stool', 'globe', 'sledge']
SPOTS = ['shelf', 'stove', 'counter', 'ledge', 'table']
THINGS = ['coil of rope', 'ball of twine', 'sack of barley', 'pair of tongs', 'tub of madder', 'heap of straw', 'stack of pallets', 'roll of tape']
PLACES = ['boat shed', 'net loft', 'seed store', 'nail forge', 'dye house', 'bell tower']

MARKER_NOT_SUPPORTED = 'The roof was painted green last spring.'      # the made-up checker fails a note that holds this
LEAK_SENTENCE = 'The passage gives no answer about the weather.'      # holds a word of the answer-leak screen, rule d


def person(index):
    """One made-up person. index counts from 0."""
    pron = 'She' if index % 2 == 0 else 'He'
    adj = ADJ_PAIRS[index % len(ADJ_PAIRS)]
    noun = NOUNS[index % len(NOUNS)]
    p = {'index': index, 'name': NAME_PARTS[index % 15] + NAME_ENDS[index // 15], 'pron': pron, 'pron_l': pron.lower(),
         'place': PLACES[index % len(PLACES)], 'liked': '%s %s' % (adj[0], noun), 'other': '%s %s' % (adj[1], noun),
         'disliked': DISLIKED[index % len(DISLIKED)], 'obj': OBJECTS[index % len(OBJECTS)], 'spot': SPOTS[index % len(SPOTS)],
         'thing': THINGS[index % len(THINGS)]}
    return p


def sentences(p):
    return ['%(name)s opened the %(place)s before dawn.' % p,
            '%(pron)s always reached for the %(liked)s before the %(other)s.' % p,
            'The %(obj)s stood on the %(spot)s by the door.' % p,
            'A %(thing)s lay beside it.' % p,
            '%(pron)s kept well away from the %(disliked)s.' % p,
            'Every morning for nine years %(pron_l)s had dusted the %(obj)s first.' % p]


def passage_text(p):
    return ' '.join(sentences(p))


def question_goes_for(p):
    return {'form': 'GOES_FOR',
            'question': 'A free hour comes up next week. Going only by the passage, which of these does %(name)s do first?' % p,
            'right': 'reaching for the %(liked)s again' % p,
            'wrong': ['reaching for the %(other)s again' % p, 'moving the %(obj)s to the yard' % p, 'hanging the %s on a hook' % p['thing'].split()[-1],
                      'sweeping the %s floor twice' % p['place'].split()[-1], 'leaving the door wide open'],
            'anchors': ['reached for the %(liked)s' % p]}


def question_keeps_away(p):
    return {'form': 'KEEPS_AWAY',
            'question': 'A visitor asks for help later that day. Going only by the passage, which of these does %(name)s leave to someone else?' % p,
            'right': 'working on the %(disliked)s' % p,
            'wrong': ['working with the %(liked)s' % p, 'carrying the %(obj)s outside' % p, 'counting every %s there' % p['thing'].split()[-1],
                      'locking up the %(place)s' % p, 'lighting the big lamp'],
            'anchors': ['away from the %(disliked)s' % p]}


def question_long_break(p):
    return {'form': 'LONG_BREAK',
            'question': '%(name)s spends two years far from the %(place)s. Going only by the passage, which of these has most likely faded '
                        'when %(pron_l)s comes back?' % p,
            'right': 'dusting the %(obj)s before anything else' % p,
            'wrong': ['opening the %(place)s before dawn' % p, 'finding the %(spot)s by the door' % p, 'seeing the %s beside it' % p['thing'].split()[-1],
                      'knowing where the %(obj)s stands' % p, 'walking in through the door'],
            'anchors': ['Every morning for nine years']}


def question_fact(p):
    return {'question': 'On the day %(name)s opened up, where did the %(obj)s stand?' % p, 'right': 'on the %(spot)s' % p,
            'wrong': ['under the bench', 'behind the gate', 'inside the cart']}


def note_pool(p):
    """Made-up sentences a made-up note writer might write. None holds an option text or a sentence of a question."""
    return ['%(name)s opens the %(place)s before dawn.' % p,
            '%(name)s reaches for the %(liked)s before the %(other)s.' % p,
            'The %(obj)s stands on the %(spot)s by the door.' % p,
            'A %(thing)s lies beside the %(obj)s.' % p,
            '%(name)s keeps well away from the %(disliked)s.' % p,
            'The %(other)s comes after the %(liked)s.' % p,
            'The %(spot)s is by the door of the %(place)s.' % p,
            '%(name)s dusts the %(obj)s first every morning.' % p,
            'The %(place)s is open before dawn.' % p,
            'The dusting has gone on for nine years.' % p,
            'The %(thing)s and the %(obj)s are close together.' % p,
            'The %(liked)s is picked up first.' % p]


WORD = re.compile(r"[A-Za-z0-9']+")


def made_up_note(p, target_words, shift=0, extra=None):
    """A made-up ordinary note of about target_words words."""
    pool, parts, at = note_pool(p), ([extra] if extra else []), shift
    while len(WORD.findall(' '.join(parts))) < target_words:
        parts.append(pool[at % len(pool)])
        at += 1
    return ' '.join(parts)


def load_table():
    """The table 01_make_fixture.py wrote: passage id -> the person and the special marks of that made-up passage."""
    return json.loads((HERE / 'FIXTURE_TABLE.json').read_text(encoding='utf-8'))
