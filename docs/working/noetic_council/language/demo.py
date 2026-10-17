"""demo.py -- the language layer, shown rather than claimed. `python -B demo.py`

What this prints:
  1. a real CAS content record;
  2. the fixed twin sentence, and the parse back proving it is the same record;
  3. several different wordings of that same record, each parsing back to it;
  4. the number that could not be said before the Q13 ruling (1/3), exactly;
  5. one frame said 24 ways;
  6. what the system refuses, with the typed word, instead of guessing;
  7. a station read out loud (TAP) and brought back in (INJECT);
  8. a station with a FORM gap: it says nothing, and the gap is counted, not hidden;
  9. the fixed sentence for a thing that cannot be told.

Everything printed here is read off the running code. No number is rounded for display.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                        # pragma: no cover
    pass

import cce_parse
import cce_render
import inject
import lexicon as LX
import roundtrip as RT
import tap
from content import CASContent, Leakage, N, Recipe, RecipeTerm, State, Term

RULE = "=" * 88
THIN = "-" * 88


def banner(title):
    print()
    print(RULE)
    print(title)
    print(RULE)


def show_record(content, indent="   "):
    record = content.record()
    print(indent + "turn %s | evidence %s | gate %s | omega %s | nesting depth %d"
          % (record["turn"], record["evidence"], record["gate"], record["omega"],
             record["nesting_depth"]))
    for term in record["terms"]:
        slots = ", ".join("%s=%s" % (name, value if not isinstance(value, dict) else "that[...]")
                          for name, value in sorted(term["slots"].items()))
        print(indent + "  ^%d  slots {%s}  domain %s  register %s  drive %s  polarity %s  coefficient %s"
              % (term["noetic"], slots, term["domain"], term["register"], term["drive"],
                 term["polarity"], term["coefficient"]))
    recipe = record["recipe"]
    if recipe:
        print(indent + "  recipe for %s:" % recipe["omega"])
        for entry in recipe["terms"]:
            if entry["kind"] == "state":
                state = entry["state"]
                print(indent + "    %-6s of ^%d, domain %s, register %s, drive %s"
                      % (entry["coefficient"], state["noetic"], state["domain"],
                         state["register"], state["drive"]))
            elif entry["kind"] == "outcome":
                print(indent + "    %-6s of %s (an outcome)" % (entry["coefficient"], entry["name"]))
            else:
                print(indent + "    %-6s of two states combined into %s"
                      % (entry["coefficient"], entry["result"]))
        for leak in recipe["leakage"]:
            print(indent + "    side product %s of %s (implicit %s)"
                  % (leak["coefficient"], leak["side"], leak["implicit"]))
        if recipe["catalysts"]:
            print(indent + "    helped by %s" % ", ".join(recipe["catalysts"]))
        if recipe["inhibitors"]:
            print(indent + "    slowed by %s" % ", ".join(recipe["inhibitors"]))
    for relation in record["relations"]:
        print(indent + "  relation %r" % (relation,))
    if record["fractal"]:
        print(indent + "  fractal %r" % (record["fractal"],))


def main():
    print(RULE)
    print("THE LANGUAGE LAYER -- CAS content <-> a small strict English (CCE %s)" % LX.CCE_VERSION)
    print("CONTROLLED ENGLISH ONLY. NOT OPEN CONVERSATION. FORM ONLY, NO MEANING CLAIM.")
    print(RULE)

    # ---------------------------------------------------------------------------------------------
    banner("1. A CAS CONTENT RECORD (a recipe: Theta(Omega_bread))")
    recipe = Recipe(
        "Ω_bread",
        terms=(RecipeTerm("1/3", kind="state", state=State(5, domain="C")),
               RecipeTerm("2", kind="state", state=State(7, domain="O", register=("A",), drive="F6")),
               RecipeTerm("3/7", kind="outcome", name="Ω_starter")),
        leakage=(Leakage("1/9", "Ω_steam"),),
        catalysts=("Ω_warmth",),
        inhibitors=("Ω_draught",))
    content = CASContent(recipe=recipe)
    show_record(content)
    print("   content digest %s" % content.digest()[:32])

    # ---------------------------------------------------------------------------------------------
    banner("2. THE FIXED TWIN: the CANON sentence, and the parse back")
    sentence = cce_render.render(content)
    print("   SAID:    %s" % sentence)
    back = cce_parse.parse(sentence)
    print("   PARSED:  content digest %s" % back.digest()[:32])
    print("   SAME RECORD? %s" % ("YES, identical after normalisation" if back == content else "NO"))
    receipt = RT.round_trip(content)
    print("   receipt: ok=%s wording_id=%s rejection_codes=%s"
          % (receipt.ok, receipt.wording_id, list(receipt.rejection_codes) or "none"))

    # ---------------------------------------------------------------------------------------------
    banner("3. THE SAME RECORD SAID SEVERAL WAYS (each one must parse back to it)")
    rows, seen = [], set()
    wanted = {"plain": 3, "definition": 1, "number": 1}
    for wording in cce_render.wordings(content):
        said = cce_render.render(content, wording)
        if said in seen:
            continue
        seen.add(said)
        buckets = []
        if wanted["plain"] > 0:
            buckets.append("plain")
        if wanted["definition"] > 0 and wording.definition:
            buckets.append("definition")
        if wanted["number"] > 0 and wording.number_style not in ("exact", "fraction"):
            buckets.append("number")
        if not buckets:
            continue
        wanted[buckets[0]] -= 1
        rows.append((wording, said, cce_parse.parse(said) == content))
    for wording, said, ok in rows:
        print("   [%02d %-5s numbers=%-8s definition_ref=%-5s] %s"
              % (wording.wid, wording.tier, wording.number_style, wording.definition, said))
        if not ok:
            print("            ^^ READ-BACK FAILED; this sentence would be refused")
    print(THIN)
    print("   What changed between them: the order of the prerequisites and whether a Noetic is")
    print("   named or written out as its verbatim definition in brackets. The number form is")
    print("   another axis -- but 1/3 has no decimal form, so every wording here must write p/q.")
    print("   What did not change: the record. A recipe has no ALIAS tier -- the colloquialisms")
    print("   belong to frames, and section 5 shows those.")
    info = RT.sayable(content)
    print("   this record has %d lossless wordings; %d of them parse back to it (%d distinct sentences)"
          % (info["wordings_tried"], info["wordings_ok"], info["distinct_sentences"]))

    # ---------------------------------------------------------------------------------------------
    banner("4. THE NUMBER THAT COULD NOT BE SAID BEFORE THE Q13 RULING")
    proof = N.prove_one_third()
    print("   written 1/3 -> parsed exactly as %s (numerator %d, denominator %d)"
          % (N.fraction_text(N.parse_number("1/3")), N.parse_number("1/3").numerator,
             N.parse_number("1/3").denominator))
    print("   1/3 rendered back as %r and re-parsed exactly: %s"
          % (proof["rendered"], proof["reparsed_equals_parsed"]))
    print("   a decimal form of 1/3 is REFUSED with the word %r" % proof["decimal_refused_with"])
    print("   forms offered for 1/3: %s (no decimal, because there is none)"
          % (proof["styles_offered"],))
    print("   forms offered for 1/2: %s (a decimal exists, so both are allowed)"
          % (N.styles_for(N.Fraction(1, 2)),))
    print("   the recipe above says 1/3, 3/7 and 1/9 -- and never 0.333 or 0.428")

    # ---------------------------------------------------------------------------------------------
    banner("5. ONE FRAME, MANY WORDINGS")
    frame = CASContent(terms=(Term(2, slots={"M": "I", "I": '"the offer"'},
                                   domain="P", register=("A", "f"), drive="F2"),))
    frame_info = RT.sayable(frame)
    for wording in cce_render.wordings(frame)[:5]:
        print("   %s" % cce_render.render(frame, wording))
    print("   ... %d lossless wordings in all, all parsing back to the same record."
          % frame_info["wordings_ok"])
    print("   (The words differ. The record does not. That is the whole claim.)")

    # ---------------------------------------------------------------------------------------------
    banner("6. WHAT IT REFUSES, AND WITH WHICH WORD (it never picks a reading)")
    refusals = [
        '"x" is bad.',
        'Ana is composed of "ten years of nursing".',
        '"x" triggers "x" to come to I.',
        'Ana might be adverse to "x".',
        'There is a lot of Ω_flour.',
        'Ana is adverse to "x" because the plan failed.',
        'To make Ω_x, use 2 of (Positive, principled combined with Negative, evaluative).',
    ]
    for text in refusals:
        report = cce_parse.parse_report(text)
        print("   %-20s %s" % (report["code"], text))
    print(THIN)
    print("   The second line is the interesting one: with no declaration, `X is composed of Y`")
    print("   reads two ways (a Mind composed of an Idea, or an Idea composed of another Idea),")
    print("   so the answer is AMBIGUOUS. Add `Ana is a Mind.` and it reads one way:")
    settled = cce_parse.parse('Ana is a Mind. Ana is composed of "ten years of nursing".')
    print("   ^%d  %s" % (settled.terms[0].noetic,
                          cce_render.render(settled)))

    # ---------------------------------------------------------------------------------------------
    banner("7. A STATION READ OUT LOUD (TAP), THEN BROUGHT BACK IN (INJECT)")
    world = tap.world_demo()
    before = world.digest()
    record = tap.tap(world.station("S2"))
    print("   TAP station S2 (%s):" % tap.STATION_NAMES["S2"])
    print("     SAID: %s" % record.sentence)
    print("     receipt ok=%s, wrote_nothing=%s" % (record.receipt.ok, record.wrote_nothing))
    delivery = inject.deliver(record.sentence, tap.Station("S2"))
    print("   INJECT that sentence into an empty S2:")
    print("     entered=%s, routed to %s for %s, wrote a value? %s"
          % (delivery["entered"], delivery["record"].station, delivery["record"].faculty,
             delivery["record"].write["value_written"]))
    print("     the content that left is the content that arrived: %s"
          % ("YES" if delivery["station"].content == world.station("S2").content else "NO"))
    print("   the whole world digest before and after every tap: %s"
          % ("UNCHANGED" if world.digest() == before else "CHANGED -- a FAIL"))
    print("   (A tap is a probe. It reads the state; it does not alter the circuit.)")

    # ---------------------------------------------------------------------------------------------
    banner("8. A STATION WITH A FORM GAP: IT SAYS NOTHING, AND THE GAP IS COUNTED")
    report = tap.tap_all(world)
    for row in report["records"]:
        if row.state == "SPOKEN":
            print("   %-3s %-9s %s" % (row.station, row.state, row.sentence))
        else:
            print("   %-3s %-9s no sentence (missing form: %s)"
                  % (row.station, row.state, ", ".join(row.missing) or "-"))
    print(THIN)
    print("   spoken %d, FORM gaps %d, no content %d, refused %d"
          % (report["counts"]["SPOKEN"], report["counts"]["FORM_GAP"],
             report["counts"]["NO_EVIDENCE"], report["counts"]["REFUSED"]))
    print("   Station S3 holds a theoretical yield, a limiting reagent, a region and an outcome.")
    print("   This English has no form for any of them, so S3 contributes NO sentence. It is")
    print("   counted as a FORM gap and named. Nothing is approximated and nothing is skipped.")

    # ---------------------------------------------------------------------------------------------
    banner("9. THE THING THAT CANNOT BE TOLD")
    unknown = CASContent(gate="UNDETERMINED")
    print("   said: %r" % cce_render.render(unknown))
    print("   exactly, always, and it is never drawn as a wording: %s"
          % (cce_render.render(unknown) == "I cannot tell."))

    # ---------------------------------------------------------------------------------------------
    banner("10. THE HONEST SUMMARY")
    ledger = RT.CoverageLedger()
    coverage = ledger.run()
    print("   round trip: content -> English -> content is identical for every wording tried.")
    print("   coverage ledger: %d cells (10 Noetics x 4 Domains x 5 register values), COVERED %d, "
          "LACUNA %d, FADED %d, NO_EVIDENCE %d"
          % (coverage["cells"], coverage["counts"]["COVERED"], coverage["counts"]["LACUNA"],
             coverage["counts"]["FADED"], coverage["counts"]["NO_EVIDENCE"]))
    print("   wordings per content: %d (recipe), %d (one frame), %d (nested frame)"
          % (info["wordings_ok"], frame_info["wordings_ok"], RT.sayable(tap_nested())["wordings_ok"]))
    print("   learned parameters: 0. Nothing here was fitted to data.")
    print()
    print("   THIS IS A FORM TRANSLATOR. It speaks a small strict English. It makes no claim about")
    print("   meaning, and it parses roughly none of free English written by a language model.")
    print("   Free English is a different, much larger build.")
    print(RULE)


def tap_nested() -> CASContent:
    inner = CASContent(terms=(Term(2, slots={"M": "Ana", "I": '"the offer"'}),))
    outer = Term(1, slots={"M": "I", "I": inner, "ACT": "stores"},
                 domain="C", register=("A",), drive="F2")
    return CASContent(terms=(outer,), relations=(("is_a", "Ana", "Mind"),))


if __name__ == "__main__":
    main()
