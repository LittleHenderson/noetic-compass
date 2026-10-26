from lab import *


def build():
    R = []

    # W061  tapping the glass, years of daily observation
    p = "W061"
    R.append(rec(p, [
        E("^1", "Wendy", sup(p, 1), "Wendy", "", "clear", ""),
        E("^7", "years of daily observation", sup(p, 1, 2, 3, 4), "Wendy", "the fish tanks", "clear", "Muscle memory."),
    ]))

    # W062  brass bell -> grandfather's boat
    p = "W062"
    trig = "an old, tarnished brass bell"
    eff = "her grandfather's boat"
    R.append(rec(p, [
        E("^1", "Wendy", sup(p, 1), "Wendy", "", "clear", ""),
        E("^1", "her grandfather", sup(p, 3), "her grandfather", "", "clear", ""),
        E("^8", trig, sup(p, 2, 3), "Wendy", eff, "clear", "Made me think of..."),
        E("^9", eff, sup(p, 2, 3), "Wendy", trig, "clear", "The thought came to me."),
    ], ["Wendy also recalls the gentle rocking of the waves; no separate trigger is named for it."]))

    # W063  pure white salt pleases, grey rock salt repels, grit barely noticed
    p = "W063"
    R.append(rec(p, [
        E("^1", "Clara", sup(p, 1), "Clara", "", "clear", ""),
        E("^2", "the dazzling purity of the drying beds", sup(p, 2), "Clara", "", "clear", "Speaks to me."),
        E("^3", "The dull, greyish rock salt piles", sup(p, 3), "Clara", "", "clear", "Rubs me the wrong way."),
        E("^4", "barely noticed it", sup(p, 4), "Clara", "A tiny speck of grit", "clear", "It made no impression on her."),
        E("^2", "A small, perfect crystal landing nearby", sup(p, 5), "Clara", "", "clear", "That makes her day."),
    ]))

    # W064  shelving by feel, years of handling volumes
    p = "W064"
    R.append(rec(p, [
        E("^1", "Philip", sup(p, 1), "Philip", "", "clear", ""),
        E("^7", "Years", sup(p, 2, 3, 4, 5), "Philip", "handling volumes", "clear", "Muscle memory."),
    ]))

    # W065  drawn to fine potatoes, pushes aside knobby ones, flinches at clatter, ignores squeak
    p = "W065"
    R.append(rec(p, [
        E("^1", "Laura", sup(p, 1), "Laura", "", "clear", ""),
        E("^2", "the smooth, clean, perfectly formed potatoes", sup(p, 1), "Laura", "", "clear",
          "Drawn to it like a moth to a flame."),
        E("^3", "The small, knobby ones, covered in bits of soil", sup(p, 2), "Laura", "", "clear", "Rubs me the wrong way."),
        E("^4", "made her flinch", sup(p, 3), "Laura", "The loud clatter of a conveyor belt stopping abruptly", "clear",
          "Hit me hard."),
        E("^4", "barely noticed", sup(p, 4), "Laura", "the persistent, high-pitched squeak from a loose wheel nearby", "clear",
          "It made no impression on her."),
    ]))

    return R


if __name__ == "__main__":
    r = build()
    for x in check(r):
        print(x)
    print("ok", len(r))
