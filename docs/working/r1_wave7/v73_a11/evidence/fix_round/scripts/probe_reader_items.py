"""probe_reader_items.py <helm_dir> <out_json> -- reproduce the reader-regression reviewer items (R-1 .. R-5) on ONE scratch
HELM copy (run once on helm_v72, once on helm_v73r). Every recipe and sentence is the prober's own (made up here). Prints
and writes JSON. Scratch evidence only; nothing here is a result."""
import json
import os
import sys
import tempfile
from fractions import Fraction

HELM = os.path.abspath(sys.argv[1])
sys.path.insert(0, HELM)
os.environ["HELM_SESSION_DIR"] = tempfile.mkdtemp(prefix="probe_sess_")
import helm_wide_turn as WT            # noqa: E402
import helm_end_to_end_loop as E2E     # noqa: E402


def rw(text):
    r = WT.read_wide(text)
    c = r.get("clarify")
    return {"status": r["status"], "clarify": c, "ran_out": (r.get("witness") or {}).get("ran_out"),
            "spoken": WT.say_reader_question(c) if c else None}


def flow(turns):
    loop = E2E.HELMEndToEndLoop(wide_brain=True)
    out = []
    for k, s in enumerate(turns, 1):
        r = loop.process_turn(s, tick=k)
        rr = r.get("recipe_receipt") or {}
        out.append({"text": s, "status": r.get("loop_status"), "path": r.get("path"), "value": r.get("output_value"),
                    "limiting": r.get("limiting_ingredient") or r.get("limiting"),
                    "ingredient": rr.get("ingredient"), "said": r.get("everyday_english_response")})
    return out


def main():
    res = {"helm": HELM, "reader": WT.READER_VERSION}
    # R-1: the person's own words already pick the line ("fresh", "large", "whole")
    salsa = ["We made 1 salsa from 1 can tomatoes in juice, 8 cups fresh tomatoes and 4 onions and ran out of tomatoes.",
             "We made 1 salsa from 2 can tomatoes in juice, 4 cups fresh tomatoes and 4 onions and ran out of fresh tomatoes.",
             "We made 1 salsa from 2 can tomatoes in juice, 8 cups fresh tomatoes and 2 onions and ran out of onions.",
             "We have 3 can tomatoes in juice, 6 cups fresh tomatoes and 5 onions.",
             "How much salsa can we make?"]
    res["R1_flow_salsa_fresh_vs_in_juice"] = flow(salsa)
    res["R1_read_wide"] = {
        "large eggs vs egg for glazing": rw("We made 1 bun from 4 large eggs, 1 egg for glazing and 4 cups flour and ran out of large eggs."),
        "whole milk vs milk for brushing": rw("We made 1 roll from 2 cups whole milk, 2 tablespoons milk for brushing and 6 cups flour "
                                              "and ran out of whole milk."),
        "fresh tomatoes vs tomatoes in juice": rw(salsa[1]),
    }
    # R-2: every way of naming the SHORT line binds back to the same exact name, so the which-line question repeats
    base = "We made 1 sauce from 2 can tomatoes in juice, 2 tomatoes and 4 onions and ran out of {}."
    replies = ["tomatoes", "the 2 tomatoes", "plain tomatoes", "fresh tomatoes", "whole tomatoes", "tomato", "2 tomatoes",
               "the tomatoes, not the ones in juice", "the loose tomatoes", "tomatoes in juice"]
    res["R2_replies"] = {x: rw(base.format(x)) for x in replies}
    res["R2_subject_form"] = rw("We made 1 sauce from 2 can tomatoes in juice, 2 tomatoes and 4 onions, and the tomatoes ran out first.")
    # R-3: the R2g sentence quotes HELM's bound name; a stated tie still asks which one
    res["R3_fresh_said"] = flow([salsa[1]])
    res["R3_tie"] = flow(["We made 1 sauce from 2 can tomatoes in juice, 2 tomatoes and 4 onions and ran out of tomatoes and "
                          "tomatoes in juice."])
    res["R3_tie_sugar"] = flow(["We made 1 cake from 1 cup sugar, 1 tablespoon sugar for dusting and 3 cups flour and ran out of "
                                "sugar and sugar for dusting at the same time."])
    # R-4: purpose / condition phrases inside a name
    res["R4_read_wide"] = {
        "sugar vs sugar for dusting": rw("We made 1 cake from 1 cup sugar, 2 tablespoons sugar for dusting and 6 cups flour and ran out of sugar."),
        "butter vs butter for the pan": rw("We made 1 loaf from 1 cup butter, 1 tablespoon butter for the pan and 4 cups flour and ran out of butter."),
        "eggs vs egg for glazing": rw("We made 1 bun from 3 eggs, 1 egg for glazing and 4 cups flour and ran out of eggs."),
        "water vs water if needed": rw("We made 1 dough from 2 cups water, 1 tablespoon water if needed and 4 cups flour and ran out of water."),
        "butter vs butter at room temperature": rw("We made 1 cookie from 1 cup butter, 2 tablespoons butter at room temperature and 3 "
                                                   "cups flour and ran out of butter."),
        "tuna vs tuna in oil": rw("We made 1 salad from 2 cans tuna, 1 can tuna in oil and 2 cups rice and ran out of tuna."),
    }
    # R-5: the which-one question on a STOCK sentence speaks of "the batch"
    res["R5_stock_which_one"] = rw("We have 3 cups honey or, 3 cups maple syrup and 5 cups oats.")
    out = json.dumps(res, indent=1, sort_keys=True, default=str)
    open(sys.argv[2], "w", encoding="utf-8").write(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
