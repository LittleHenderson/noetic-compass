from lab import *


def build():
    R = []

    # W041  ozone smell -> grandfather's workshop
    p = "W041"
    ws = "his grandfather’s workshop"
    R.append(rec(p, [
        E("^1", "Martin", sup(p, 1), "Martin", "", "clear", ""),
        E("^1", "his grandfather", sup(p, 2), "his grandfather", "", "clear", ""),
        E("^8", "the faint scent of ozone", sup(p, 1, 2), "Martin", ws, "clear", "Triggered a memory."),
        E("^9", ws, sup(p, 1, 2), "Martin", "the faint scent of ozone", "clear", "It just popped into my head."),
    ], ["Martin also remembers the old bakelite cases; no separate trigger is named for them."]))

    # W042  fish and chip smell -> stormy afternoon with Leo
    p = "W042"
    R.append(rec(p, [
        E("^1", "Clara", sup(p, 1), "Clara", "", "clear", ""),
        E("^1", "Leo", sup(p, 3), "Leo", "", "clear", ""),
        E("^8", "A particular sharp, salty smell", sup(p, 2, 3), "Clara", "a stormy afternoon years ago", "clear", "That reminds me..."),
        E("^9", "a stormy afternoon years ago", sup(p, 2, 3), "Clara", "A particular sharp, salty smell", "clear", "It just popped into my head."),
    ]))

    # W043  registry search, following a clue (reasoning, rule 15b)
    p = "W043"
    R.append(rec(p, [
        E("^1", "Rebecca", sup(p, 1), "Rebecca", "", "clear", ""),
        E("^9", "the detailed record in a separate land ownership ledger", sup(p, 3, 4), "Rebecca", "", "clear",
          "It just clicked.", reached="reasoning"),
    ], ["Rebecca follows a clue by searching; the passage shows no flash of memory."]))

    # W044  potato sorting, nothing but a Mind
    p = "W044"
    R.append(rec(p, [
        E("^1", "Gary", sup(p, 1), "Gary", "", "clear", ""),
    ]))

    # W045  wallpaper process broken into stages
    p = "W045"
    whole = "the process for hanging patterned wallpaper"
    R.append(rec(p, [
        E("^1", "Ursula", sup(p, 1), "Ursula", "", "clear", ""),
        E("^6", "preparation of the walls", sup(p, 1, 2, 3), "", whole, "clear", "Breaking it down."),
        E("^6", "carefully measuring and cutting the strips", sup(p, 1, 2, 3, 4), "", whole, "clear", "Breaking it down."),
        E("^6", "the paste application", sup(p, 2, 3, 4, 5), "", whole, "clear", "Breaking it down."),
        E("^6", "hanging each strip from the ceiling down", sup(p, 3, 4, 5, 6), "", whole, "clear", "Breaking it down."),
    ], ["The whole is named in the first sentence; the last two stages are more than four sentences away from it."]))

    return R


if __name__ == "__main__":
    r = build()
    for x in check(r):
        print(x)
    print("ok", len(r))
