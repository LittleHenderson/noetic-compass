from lab import *


def build():
    R = []

    # W046  handwritten sign, "knowing" the card machine is down (rule 15d)
    p = "W046"
    sign = "a small, handwritten sign"
    fact = "the card machine was likely down again"
    R.append(rec(p, [
        E("^1", "Frank", sup(p, 1), "Frank", "", "clear", ""),
        E("^8", sign, sup(p, 2, 3, 4), "Frank", fact, "ambiguous", "Made me think of...", other="reasoning"),
        E("^9", fact, sup(p, 2, 3, 4), "Frank", sign, "ambiguous", "It just clicked.", other="reasoning"),
    ], ["The word 'again' hints at earlier trouble with the machine; the passage does not say what Frank has lived through."]))

    # W047  fray traced back to a burr (reasoning, rule 15b)
    p = "W047"
    R.append(rec(p, [
        E("^1", "David", sup(p, 1), "David", "", "clear", ""),
        E("^9", "the burr was catching the filament, causing the damage", sup(p, 4, 5), "David", "", "clear",
          "It just clicked.", reached="reasoning"),
    ], ["David checks the spool, the tension setting and the spindle in turn; no whole that they compose is named."]))

    # W048  ticket stub matched to a coat (reasoning, rule 15b)
    p = "W048"
    R.append(rec(p, [
        E("^1", "Karen", sup(p, 1), "Karen", "", "clear", ""),
        E("^1", "The owner", sup(p, 2), "The owner", "", "clear", ""),
        E("^9", "The owner must have mistakenly left the stub", sup(p, 4, 5), "Karen", "", "clear",
          "It just clicked.", reached="reasoning"),
    ], ["Karen also remembers handing out dark blue coats; the passage does not say the owner's words brought this to mind."]))

    # W049  archiving habit
    p = "W049"
    R.append(rec(p, [
        E("^1", "Chloe", sup(p, 1), "Chloe", "", "clear", ""),
        E("^7", "whenever she finished with a document", sup(p, 1, 2), "Chloe", "her archiving job", "clear", "Getting into a groove."),
    ]))

    # W050  weekly folding routine
    p = "W050"
    R.append(rec(p, [
        E("^1", "Chloe", sup(p, 1), "Chloe", "", "clear", ""),
        E("^7", "Years", sup(p, 2, 3, 4, 5), "Chloe", "repeating the same routine", "clear", "Muscle memory."),
    ]))

    return R


if __name__ == "__main__":
    r = build()
    for x in check(r):
        print(x)
    print("ok", len(r))
