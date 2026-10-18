"""eye -- the Unity Eye (F1 watcher) over this project's real builds.

Internal name: "Unity Eye (F1 watcher)". Form: MINI-VERSION, ACCEPTED_BY_OWNER
(`OWNER_RULING_UNITY_EYE_20261015.md`). Public name, when one is needed: "F1 Unity Monitor"
(PROPOSED, `UNITY_EYE.md` Q23). The owner's phrase "all-seeing eye" is the metaphor and is never
a product name; it is mapped point for point in `UNITY_EYE.md` section 7.

What is in here, one line each:

  * `recipe.py`   -- the one recipe, Y_T = min_i(x_i / a_i), the Limiting Reagent, gate G1-G3,
                     and the eta / epsilon receipt on every reading.
  * `signals.py`  -- the five measured health ingredients and where each number is counted from.
  * `tap.py`      -- the read-only, digest-checked tap: the folder's digest before = after, or
                     the reading is refused.
  * `eye.py`      -- the watcher: reads every watched package, names the weakest, logs, proposes
                     in report-only mode, and acts on nothing.

The eye sits outside what it watches. It cannot write a fact, a candidate or a learned value; it
has no route to the verifier, the buffer or the Bias; and nothing it produces is read by any
decision in this package. `test_all.py` proves all three.

CLAIM CEILING: this is a mechanism, run over recorded test results on this laptop. It is not a
claim that any build is healthy or unified.
"""

from eye.eye import (  # noqa: F401
    EyeReading,
    EyeRefusal,
    FIX,
    HELP,
    NO_PROPOSAL,
    PROPOSAL_KINDS,
    REPORTED,
    REPORT_ONLY,
    UnityEye,
)
from eye.recipe import (  # noqa: F401
    G1_INGREDIENT_ABSENT,
    G2_NOTHING_READ,
    G3_TIE_AT_THE_MINIMUM,
    G4_LAST_RECEIPT_FAILED,
    UNDETERMINED,
    Ingredient,
    Recipe,
    RecipeReading,
    RecipeRefusal,
)
from eye.signals import (  # noqa: F401
    PACKAGES,
    Package,
    RecordedSuite,
    load_recorded,
    measure,
    recorded_path,
)
from eye.tap import (  # noqa: F401
    WATCHED_VALUE_MOVED,
    Tap,
    TapReading,
    TapRefusal,
    folder_digest,
)

__all__ = [
    "UnityEye", "EyeReading", "EyeRefusal", "REPORT_ONLY", "FIX", "HELP", "REPORTED",
    "NO_PROPOSAL", "PROPOSAL_KINDS",
    "Recipe", "RecipeReading", "Ingredient", "RecipeRefusal", "UNDETERMINED",
    "G1_INGREDIENT_ABSENT", "G2_NOTHING_READ", "G3_TIE_AT_THE_MINIMUM", "G4_LAST_RECEIPT_FAILED",
    "Tap", "TapReading", "TapRefusal", "folder_digest", "WATCHED_VALUE_MOVED",
    "PACKAGES", "Package", "RecordedSuite", "load_recorded", "measure", "recorded_path",
]
