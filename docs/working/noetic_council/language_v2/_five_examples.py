import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import cce_parse, cce_render
from content import CASContent, Recipe, RecipeTerm, State, Term

def show(n, kind, content):
    try:
        said = cce_render.render(content)
    except Exception as e:
        print("%d. TYPE %s\n   RENDER REFUSED (%s): %s\n" % (n, kind, type(e).__name__, e)); return
    print("%d. TYPE: %s" % (n, kind))
    print("   ENGLISH: %s" % said)
    try:
        back = cce_parse.parse(said)
        print("   READ BACK: %s" % ("IDENTICAL to the input content" if back == content else "DIFFERENT"))
    except Exception as e:
        print("   READ BACK REFUSED (%s): %s" % (type(e).__name__, e))
    print()

show(1, "FRAME - attraction (Noetic ^2)",
     CASContent(terms=(Term(2, slots={"M": "I", "I": '"the offer"'}),)))

# 2. nested, with Ana declared in the same content so it is not an undeclared guess
inner = CASContent(terms=(Term(2, slots={"M": "Ana", "I": '"the offer"'}),))
show(2, "NESTED FRAME - a thought inside a thought, with the name declared",
     CASContent(terms=(Term(1, slots={"M": "I", "I": inner, "ACT": "stores"}),),
                relations=(("is_a", "Ana", "Mind"),)))

# 3. recipe, with the target named
show(3, "RECIPE - exact fractions with no decimal form",
     CASContent(recipe=Recipe(omega="\u03a9_bread",
         terms=(RecipeTerm("1/3", kind="state", state=State(5, domain="C")),
                RecipeTerm("2", kind="state", state=State(7, domain="O", register=("A",), drive="F6")),
                RecipeTerm("3/7", kind="outcome", name="\u03a9_starter")))))

show(4, "DECLARATION - what a name IS",
     CASContent(terms=(Term(2, slots={"M": "Ana", "I": '"the offer"'}),),
                relations=(("is_a", "Ana", "Mind"),)))

show(5, "REFUSAL - the brain declining to answer",
     CASContent(gate="UNDETERMINED"))
