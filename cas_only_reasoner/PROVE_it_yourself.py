"""PROVE IT YOURSELF:  python PROVE_it_yourself.py

You type an equation. The machine tells you TRUE (and it is proved by
exact algebra) or FALSE (and it shows you an exact counterexample).
It uses exact rational arithmetic - it is never 'pretty sure', and it
cannot be fooled by an equation that only LOOKS right.

Try to break it. Type a false identity that looks true and watch it
catch you. Examples to type at the prompt:

    (a + b)^2 = a^2 + b^2              <- looks right, is FALSE
    (a + b)^2 = a^2 + 2*a*b + b^2      <- TRUE, it will prove it
    (a + b)*(a - b) = a^2 - b^2        <- TRUE (difference of squares)
    3*(x + 4) = 3*x + 12              <- TRUE
    3*(x + 4) = 3*x + 4               <- FALSE
    2 + 2 = 5                          <- FALSE

Use letters a b c x y z, numbers, and  +  -  *  ^  ( )  and one  = .
Type 'quit' to leave.
"""
import os
import sys

LANE = os.path.dirname(os.path.abspath(__file__))
for sub in ("CCB_M1_v0.1", "CAS_MATH_LADDER_v0.1"):
    sys.path.insert(0, os.path.join(LANE, sub))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from mathschool.mathir import MathParseError
from mathschool.sdg import attack_equation, verify_identity


def main() -> None:
    print("MATH PROVER - you type an equation, i tell you TRUE (with "
          "a proof) or FALSE (with a counterexample). 'quit' to "
          "leave.")
    while True:
        try:
            line = input("equation> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("quit", "exit"):
            break
        if "=" not in line:
            print("  (i need an equation - something with an '=' "
                  "sign)")
            continue
        try:
            holds, witness = verify_identity(line)
        except MathParseError as exc:
            print(f"  i cannot read that: {exc}")
            continue
        except Exception as exc:
            print(f"  outside what i can check: {exc}")
            continue
        if holds:
            print("  TRUE.  proved by exact algebra - both sides are "
                  "the same polynomial for every value.")
        else:
            if witness and "point" in witness:
                point = ", ".join(f"{k}={v}"
                                  for k, v in witness["point"].items())
                where = f"at {point}" if point else "as written"
                print(f"  FALSE.  counterexample {where}: the left "
                      f"side is {witness['left']}, the right side is "
                      f"{witness['right']}.")
            else:
                print("  FALSE.")


if __name__ == "__main__":
    main()
