from lab import *


def build():
    R = []

    # W066  pier maintenance budget taken in parts; big costs catch her eye
    p = "W066"
    whole = "the proposed budget for the pier’s annual maintenance"
    R.append(rec(p, [
        E("^1", "Eleanor", sup(p, 1), "Eleanor", "", "clear", ""),
        E("^6", "timber replacement", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "structural steel inspections", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "paintwork", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "light bulb changes", sup(p, 1, 2, 3), "", whole, "clear", "Breaking it down."),
        E("^6", "refuse collection", sup(p, 1, 2, 3), "", whole, "clear", "Breaking it down."),
        E("^6", "winter storm barrier repairs", sup(p, 1, 2, 3), "", whole, "clear", "Breaking it down."),
        E("^4", "always caught her eye", sup(p, 4), "Eleanor", "the initial costs for the largest sections", "ambiguous",
          "Made an impression.", other="none"),
    ]))

    # W067  kennel keeper recognises a greyhound's whimper (rule 15d) + decades of experience
    p = "W067"
    sign = "the faint whimpering"
    fact = "a greyhound, missing its familiar blanket"
    R.append(rec(p, [
        E("^1", "Victor", sup(p, 1), "Victor", "", "clear", ""),
        E("^1", "the new arrival", sup(p, 1), "the new arrival", "", "clear", ""),
        E("^1", "new staff", sup(p, 2), "new staff", "", "clear", ""),
        E("^5", "run the kennels for decades", sup(p, 1), "Victor", "", "clear", "We are the sum of our experiences."),
        E("^8", sign, sup(p, 1, 2, 3), "Victor", fact, "ambiguous", "Made me think of...", other="reasoning"),
        E("^9", fact, sup(p, 1, 2, 3), "Victor", sign, "ambiguous", "It just clicked.", other="reasoning"),
    ], ["Victor also knows to fetch a soft bed; the passage does not say how he knew."]))

    # W068  landscape, no being that thinks
    p = "W068"
    R.append(rec(p, [], none=True))

    # W069  watching an apprentice, remembers her own years of struggle
    p = "W069"
    trig = "a quick, light touch"
    eff = "she had struggled for years to achieve that same delicate precision"
    R.append(rec(p, [
        E("^1", "Felicity", sup(p, 1), "Felicity", "", "clear", ""),
        E("^1", "an apprentice", sup(p, 1), "an apprentice", "", "clear", ""),
        E("^5", "having ruined countless herself learning the skill", sup(p, 3, 4), "Felicity", "", "clear",
          "We are the sum of our experiences."),
        E("^8", trig, sup(p, 2, 3), "Felicity", eff, "ambiguous", "That reminds me...", other="none"),
        E("^9", eff, sup(p, 2, 3), "Felicity", trig, "ambiguous", "It just popped into my head.", other="none"),
    ], ["The passage says Felicity remembered; it does not say the apprentice's touch brought the memory to mind."]))

    # W070  glint on a pivot "meant" a burr (rule 15d) + decades of delicate work
    p = "W070"
    sign = "a slight glint on one of its pivots"
    fact = "a microscopic burr"
    R.append(rec(p, [
        E("^1", "Susan", sup(p, 1), "Susan", "", "clear", ""),
        E("^5", "Decades of delicate work", sup(p, 5), "Susan", "", "clear", "We are the sum of our experiences."),
        E("^8", sign, sup(p, 2, 3), "Susan", fact, "ambiguous", "Made me think of...", other="reasoning"),
        E("^9", fact, sup(p, 2, 3), "Susan", sign, "ambiguous", "It just clicked.", other="reasoning"),
    ]))

    return R


if __name__ == "__main__":
    r = build()
    for x in check(r):
        print(x)
    print("ok", len(r))
