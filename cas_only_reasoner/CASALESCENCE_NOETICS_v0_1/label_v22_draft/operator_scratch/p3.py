from lab import *


def build():
    R = []

    # W051  winds -> remembered turbulent flight; experience taught caution
    p = "W051"
    winds = "the distant high-altitude winds"
    flight = "a turbulent flight years ago"
    R.append(rec(p, [
        E("^1", "Robert", sup(p, 1), "Robert", "", "clear", ""),
        E("^5", flight, sup(p, 2, 3), "Robert", "", "clear", "We are the sum of our experiences."),
        E("^8", winds, sup(p, 1, 2), "Robert", flight, "ambiguous", "That reminds me...", other="none"),
        E("^9", flight, sup(p, 1, 2), "Robert", winds, "ambiguous", "The thought came to me.", other="none"),
    ], ["The passage does not say the winds brought the flight to mind; it only puts the two side by side."]))

    # W052  likes balancing, irritated by rush, bang barely registers
    p = "W052"
    R.append(rec(p, [
        E("^1", "Quinn", sup(p, 1), "Quinn", "", "clear", ""),
        E("^2", "the precise work of balancing a wheel", sup(p, 1), "Quinn", "", "clear", "Speaks to me."),
        E("^3", "The frantic rush of a walk-in puncture repair", sup(p, 2), "Quinn", "", "clear", "Rubs me the wrong way."),
        E("^4", "barely registered with him", sup(p, 3), "Quinn", "A sudden loud bang from a dropped tool", "clear",
          "It made no impression on him."),
        E("^2", "a perfectly tightened lug nut", sup(p, 4), "Quinn", "", "clear", "That is the kind of thing he loves."),
    ]))

    # W053  discolouration on a leaf, expert knew (rule 15d) + decades of experience
    p = "W053"
    sign = "a faint discolouration on the underside of a single leaf"
    fact = "the early stages of a fungal infection"
    R.append(rec(p, [
        E("^1", "Gina", sup(p, 1), "Gina", "", "clear", ""),
        E("^5", "a horticulturist for decades", sup(p, 1), "Gina", "", "clear", "We are the sum of our experiences."),
        E("^8", sign, sup(p, 2, 3, 4), "Gina", fact, "ambiguous", "Made me think of...", other="reasoning"),
        E("^9", fact, sup(p, 2, 3, 4), "Gina", sign, "ambiguous", "It just clicked.", other="reasoning"),
    ]))

    # W054  racing shells attract, rusty motorboat repels, chatter fades
    p = "W054"
    R.append(rec(p, [
        E("^1", "Fiona", sup(p, 1), "Fiona", "", "clear", ""),
        E("^2", "the sleek racing shells", sup(p, 1, 2), "Fiona", "", "clear", "Drawn to it like a moth to a flame."),
        E("^3", "the rusty old motorboat", sup(p, 3), "Fiona", "", "clear", "Rubs me the wrong way."),
        E("^4", "faded into the background", sup(p, 4), "Fiona", "The distant chatter from the clubhouse", "clear",
          "It made no impression on her."),
    ]))

    # W055  yellow and blue balloon pulls, grey balloon barely registers
    p = "W055"
    R.append(rec(p, [
        E("^1", "Sarah", sup(p, 1), "Sarah", "", "clear", ""),
        E("^2", "the bright yellow and blue one", sup(p, 2), "Sarah", "", "clear", "Can't resist."),
        E("^4", "barely registered its presence", sup(p, 3), "Sarah", "another balloon, a dull grey one", "clear",
          "It made no impression on her."),
    ], ["Sarah imagines herself soaring; the passage does not say the balloon brought that picture to mind."]))

    return R


if __name__ == "__main__":
    r = build()
    for x in check(r):
        print(x)
    print("ok", len(r))
