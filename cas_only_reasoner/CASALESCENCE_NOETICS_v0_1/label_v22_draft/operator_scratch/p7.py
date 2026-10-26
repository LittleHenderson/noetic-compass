from lab import *


def build():
    R = []

    # W071  pocket watch examined part by part, deduces a slipped gear (rule 15b)
    p = "W071"
    whole = "the old pocket watch"
    R.append(rec(p, [
        E("^1", "Michael", sup(p, 1), "Michael", "", "clear", ""),
        E("^6", "Its minute hand", sup(p, 1, 2), "", whole, "ambiguous", "Looking at what's underneath.", other="none"),
        E("^6", "the winding stem", sup(p, 1, 2, 3), "", whole, "ambiguous", "Looking at what's underneath.", other="none"),
        E("^6", "the faint scratch marks around the casing", sup(p, 1, 2, 3, 4), "", whole, "ambiguous", "Looking at what's underneath.", other="none"),
        E("^9", "the small gear connecting the stem to the mainspring had slipped", sup(p, 4, 5), "Michael", "", "clear",
          "It just clicked.", reached="reasoning"),
    ]))

    # W072  complex wallpaper design broken down
    p = "W072"
    whole = "The new wallpaper design"
    R.append(rec(p, [
        E("^1", "Mrs. Davies", sup(p, 1), "Mrs. Davies", "", "clear", ""),
        E("^6", "the main repeating motif", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "its background colors", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "the subtle texture", sup(p, 1, 2, 3), "", whole, "clear", "Breaking it down."),
        E("^6", "how the edges matched up for seamless hanging", sup(p, 1, 2, 3), "", whole, "clear", "Breaking it down."),
    ]))

    # W073  school of fish read by a long-time student (rule 15d) + years of study
    p = "W073"
    sign = "the school of silver fish, moving as one fluid entity"
    fact = "an ancient, silent language"
    R.append(rec(p, [
        E("^1", "Quinn", sup(p, 1), "Quinn", "", "clear", ""),
        E("^5", "years studying shoaling patterns in the open ocean", sup(p, 2), "Quinn", "", "clear",
          "We are the sum of our experiences."),
        E("^8", sign, sup(p, 1, 2, 3, 4), "Quinn", fact, "ambiguous", "Made me think of...", other="reasoning"),
        E("^9", fact, sup(p, 1, 2, 3, 4), "Quinn", sign, "ambiguous", "It just clicked.", other="reasoning"),
    ], ["The fish are named, but the passage gives them no thoughts of their own."]))

    # W074  weld seam: details compared, conclusion about cooling rate (rule 15b)
    p = "W074"
    whole = "The pattern of information"
    R.append(rec(p, [
        E("^1", "David", sup(p, 1), "David", "", "clear", ""),
        E("^6", "a slight discoloration", sup(p, 1, 2, 3, 4), "", whole, "ambiguous", "Pulling apart the argument.", other="none"),
        E("^6", "the temperature readings", sup(p, 1, 2, 3, 4), "", whole, "ambiguous", "Pulling apart the argument.", other="none"),
        E("^6", "the material batch number", sup(p, 1, 2, 3, 4), "", whole, "ambiguous", "Pulling apart the argument.", other="none"),
        E("^6", "the specification sheet", sup(p, 1, 2, 3, 4), "", whole, "ambiguous", "Pulling apart the argument.", other="none"),
        E("^9", "an issue with the alloy's cooling rate", sup(p, 3, 4), "David", "", "clear",
          "It just clicked.", reached="reasoning"),
    ]))

    # W075  daily sales report dissected into segments
    p = "W075"
    whole = "the daily sales report"
    R.append(rec(p, [
        E("^1", "Chloe", sup(p, 1), "Chloe", "", "clear", ""),
        E("^6", "the cone sales", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "the tub sales", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "the individual flavour popularity", sup(p, 1, 2), "", whole, "clear", "Breaking it down."),
        E("^6", "the timing of purchases", sup(p, 1, 2, 3), "", whole, "clear", "Breaking it down."),
    ]))

    return R


if __name__ == "__main__":
    r = build()
    for x in check(r):
        print(x)
    print("ok", len(r))
