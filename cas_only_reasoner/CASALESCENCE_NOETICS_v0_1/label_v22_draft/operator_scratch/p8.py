from lab import *


def build():
    R = []

    # W076  clues on the pier pieced into a story (rule 15b)
    p = "W076"
    R.append(rec(p, [
        E("^1", "Janet", sup(p, 1), "Janet", "", "clear", ""),
        E("^1", "Someone", sup(p, 4), "Someone", "", "clear", ""),
        E("^9", "Someone was enjoying a treat, then dropped their money, then got distracted", sup(p, 3, 4), "Janet", "",
          "clear", "It just clicked.", reached="reasoning"),
    ], ["The passage does not say Janet worked the story out step by step.",
        "The gulls are named, but the passage gives them no thoughts of their own."]))

    # W077  ship repair project broken down into components
    p = "W077"
    whole = "the ship repair project"
    R.append(rec(p, [
        E("^1", "Michael", sup(p, 1), "Michael", "", "clear", ""),
        E("^6", "the hull plating inspection and replacement", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "the propulsion system", sup(p, 1, 2, 3), "", whole, "clear", "Breaking it down."),
        E("^6", "the electrical systems", sup(p, 1, 2, 3, 4), "", whole, "clear", "Breaking it down."),
        E("^6", "interior refitting", sup(p, 1, 2, 3, 4), "", whole, "clear", "Breaking it down."),
        E("^6", "the painting and finishing work", sup(p, 2, 3, 4, 5), "", whole, "clear", "Breaking it down."),
    ], ["The whole is named in the first sentence; the last component is more than four sentences away."]))

    # W078  boathouse in a storm, no being that thinks
    p = "W078"
    R.append(rec(p, [], none=True))

    # W079  olive press at work, no being that thinks
    p = "W079"
    R.append(rec(p, [], none=True))

    # W080  budgie chirping -> aunt's house
    p = "W080"
    trig = "the soft chirping of the budgies"
    eff = "her aunt's house"
    R.append(rec(p, [
        E("^1", "Lily", sup(p, 1), "Lily", "", "clear", ""),
        E("^1", "her aunt", sup(p, 2), "her aunt", "", "clear", ""),
        E("^8", trig, sup(p, 1, 2), "Lily", eff, "clear", "Triggered a memory."),
        E("^9", eff, sup(p, 1, 2), "Lily", trig, "clear", "It took her right back."),
    ], ["Lily also recalls Sunday visits and the flutter of wings; no separate trigger is named for them.",
        "The budgies are named, but the passage gives them no thoughts of their own."]))

    return R


if __name__ == "__main__":
    r = build()
    for x in check(r):
        print(x)
    print("ok", len(r))
