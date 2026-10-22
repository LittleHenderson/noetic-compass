"""how_it_talks.py -- what the real translator actually says. English in, CAS, English out.

Uses language_v3 (the reconciled base: lm_t1's cce.py plus the owner's p/q ruling and the
REFUSE and CLOSE turn forms). Every line below is produced by the program, not written by hand.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cce


def say_back(sentence, seeds=(0,)):
    """Parse English, then say it again. Returns (content, [renderings])."""
    content = cce.parse(sentence)
    outs = []
    for seed in seeds:
        try:
            got = cce.say(content, seed)
            outs.append(got["sentence"] if isinstance(got, dict) else str(got))
        except Exception as exc:
            outs.append("<draw failed: %s: %s>" % (type(exc).__name__, exc))
    return content, outs


def show(label, sentence, seeds=(0,)):
    print("=" * 96)
    print(label)
    print("-" * 96)
    print("  IN   : %s" % sentence)
    try:
        content, outs = say_back(sentence, seeds)
    except Exception as exc:
        print("  REFUSED: %s: %s" % (type(exc).__name__, str(exc)[:90]))
        print()
        return
    for index, out in enumerate(outs):
        print("  OUT %d: %s" % (index, out))
    # the round trip: does the spoken sentence read back to the same content?
    try:
        again = cce.parse(outs[0])
        same = cce.canonical(again) == cce.canonical(content)
        print("  SAME CONTENT AFTER A ROUND TRIP: %s" % ("YES" if same else "NO"))
    except Exception as exc:
        print("  SAME CONTENT AFTER A ROUND TRIP: NO (%s)" % (str(exc)[:60],))
    print()


# ---- 1. the ten Noetics say themselves ------------------------------------------------
show("1. A FEELING HELD", 'I have an affinity for "the offer".', seeds=(0, 1, 2, 3, 4))
show("2. THE SAME FACT, SAID FIVE DIFFERENT WAYS", 'I have an affinity for "the offer".',
     seeds=(5, 6, 7, 8, 9))
show("3. AVERSION - visceral, never analytical", 'I am repelled by "the offer".',
     seeds=(0, 1, 2))

# ---- 2. a mind and a thought about it -------------------------------------------------
show("4. A NAME DECLARED, THEN A THOUGHT STORED ABOUT IT",
     'Ana is a Mind. I intake that [Ana is attracted toward "the offer"].', seeds=(0, 1))

# ---- 3. the owner's fraction ruling ----------------------------------------------------
show("5. A RECIPE WITH 1/3 - THE p/q RULING. No decimal can hold a third.",
     'To make \u03a9_bread, use 1/3 of Below/Effect, operational.', seeds=(0, 1, 2))

# ---- 4. the things a conversation does ------------------------------------------------
show("6. A REFUSAL OF AN ACT - the new REFUSE turn",
     'I will not do that: boundary violation.', seeds=(0,))
show("7. A CLOSING TURN - the new CLOSE turn", 'That closes the turn.', seeds=(0,))
show("8. A REFUSAL OF A CLAIM", 'I cannot support that: no evidence.', seeds=(0,))
show("9. ASKING FOR THE MISSING THING",
     'I need the amount for \u03a9_x. What is it?', seeds=(0,))

# ---- 5. cause, prerequisite, absence --------------------------------------------------
show("10. A PREREQUISITE - RPM, one direction only",
     '\u03a9_b needs \u03a9_a first.', seeds=(0,))
show("11. ABSENCE IS NOT A SMALL QUANTITY - there is no stock",
     'There is no \u03a9_flour.', seeds=(0,))

# ---- 6. evidence ----------------------------------------------------------------------
show("12. A CLAIM WITH EVIDENCE", 'I checked: "the offer" resonates with me to degree 7.',
     seeds=(0,))

# ---- 7. the two things it will not do -------------------------------------------------
show("13. IT WILL NOT PRETEND TO KNOW", 'I cannot tell.', seeds=(0,))
show("14. IT WILL NOT TURN 'NOT' INTO AVERSION",
     'I am not attracted toward "the offer".', seeds=(0,))
show("15. IT WILL NOT DEDUCE - 'therefore' is refused",
     'Therefore we deduce it follows logically.', seeds=(0,))
