from lab import *


def build():
    R = []

    # W056  finest oil pleases; thin bitter sample pushed aside, hardly registers
    p = "W056"
    sample = "a sample from a different batch"
    R.append(rec(p, [
        E("^1", "Maria", sup(p, 1), "Maria", "", "clear", ""),
        E("^2", "the finest oil", sup(p, 5), "Maria", "", "clear", "Speaks to me."),
        E("^4", "its intensity a genuine pleasure", sup(p, 5), "Maria", "the finest oil", "clear",
          "It made quite an impression on her."),
        E("^3", sample, sup(p, 3, 4), "Maria", "", "ambiguous", "Wouldn't touch it with a ten-foot pole.", other="^4"),
        E("^4", "hardly registering its flavour", sup(p, 3, 4), "Maria", sample, "clear",
          "It made no impression on her."),
    ]))

    # W057  sea air and chips -> summer holidays by the sea
    p = "W057"
    trig = "The aroma, mixed with the faint scent of fried chips"
    eff = "summer holidays by the sea"
    R.append(rec(p, [
        E("^1", "Simon", sup(p, 1), "Simon", "", "clear", ""),
        E("^8", trig, sup(p, 2), "Simon", eff, "clear", "Triggered a memory."),
        E("^9", eff, sup(p, 2), "Simon", trig, "clear", "It took him right back there."),
    ], ["Simon then pictures sandcastles and his younger self; these read as parts of the same memory."]))

    # W058  glue paste smell -> grandmother's pantry
    p = "W058"
    trig = "The faint, sweet smell of the paste"
    eff = "his grandmother's pantry"
    R.append(rec(p, [
        E("^1", "Quinn", sup(p, 1), "Quinn", "", "clear", ""),
        E("^1", "his grandmother", sup(p, 3), "his grandmother", "", "clear", ""),
        E("^8", trig, sup(p, 2, 3), "Quinn", eff, "clear", "That reminds me..."),
        E("^9", eff, sup(p, 2, 3), "Quinn", trig, "clear", "All at once it came back to him."),
    ]))

    # W059  morning air and apple scent -> childhood bedroom window
    p = "W059"
    trig = "The cool morning air and the sweet scent of apples"
    eff = "her childhood bedroom window, open to a similar breeze"
    R.append(rec(p, [
        E("^1", "Tina", sup(p, 1), "Tina", "", "clear", ""),
        E("^8", trig, sup(p, 2, 3), "Tina", eff, "clear", "That reminds me..."),
        E("^9", eff, sup(p, 2, 3), "Tina", trig, "clear", "Out of nowhere I thought of..."),
    ], ["A sense of youthful freedom also comes to Tina; no separate trigger is named for it."]))

    # W060  shelving, nothing but a Mind
    p = "W060"
    R.append(rec(p, [
        E("^1", "Wendy", sup(p, 1), "Wendy", "", "clear", ""),
    ]))

    return R


if __name__ == "__main__":
    r = build()
    for x in check(r):
        print(x)
    print("ok", len(r))
