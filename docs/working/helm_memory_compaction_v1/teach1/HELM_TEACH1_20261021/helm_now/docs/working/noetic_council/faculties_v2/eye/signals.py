"""eye/signals.py -- the health signals the eye measures, one recipe per watched package.

WHERE THE INGREDIENTS COME FROM
UNITY_EYE.md section 2.1 gives nine brain signals (receipts passing, lacunae on cadence, stations
aligned, drive pair balance, drive entropy, continuity lawful, memory check holding, answers
determined, language skin exact) over a brain with stations, a drive loop and dialogues. This
project's builds have no stations and no dialogues, so the same arithmetic is applied to the
signals these builds actually produce -- and the owning instruction names the first of them:

    "each package's test suite result is a health signal."

The five ingredients, one rule each, every requirement a_i = 1 (`UNITY_EYE.md:93`):

  1. `tests_passing`     cases passed / cases run, from the package's recorded suite result.
  2. `suite_complete`    cases run / cases registered, where the registered count is counted out
                         of the suite file itself (every `@case` function), so a suite that
                         stopped early reads below 1 even when everything it ran passed.
  3. `mechanism_proofs`  the mechanisms this merge requires of that package, that the package
                         carries and proves with a named passing test / the mechanisms required.
  4. `design_coverage`   parts of its own design the package carries / parts its design names,
                         by each package's own count rule (below).
  5. `read_only`         did the tap's digest hold across the reading: 1 or 0, measured by the
                         tap, never by the package.

THE TWO COUNT RULES FOR `design_coverage`
  * `faculties_v2`: `faculties.FACULTIES` read out of the package's own source (four names) over
    the nine faculties `FACULTIES.md` sections 2.1-2.9 name.
  * `language_v2`: the coverage ledger the package's own suite prints -- cells COVERED over the
    cells probed (`README.md`: "The coverage ledger probes 10 x 4 x 5 = 200 cells").

Both are the same arithmetic -- what the thing carries over what its design names -- and the rule
for each is recorded in the reading, so a reader can check the number rather than trust it.

WHAT THIS MODULE DOES NOT DO
  * It does not run a suite. Running the package's own suite from inside that suite would
    recurse, so the eye reads a recorded result: the exact command, the exact tail, the count,
    and the digest of the file the result was read from. `test_all.py` cross-checks the recorded
    count against the count it can see in the suite file, so a stale record is caught.
  * It does not import the packages it watches. It reads their source as text and counts.
  * It does not score anything, weight anything or learn anything. There are 0 learned
    parameters: every requirement is programmed and every measurement is a count.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import os
import re
from fractions import Fraction

import eye.recipe as recipe
import eye.tap as tap

__all__ = [
    "PACKAGES", "Package", "RecordedSuite", "load_recorded", "cases_registered",
    "declared_cases", "faculty_roster", "measure", "recorded_path",
    "SIGNAL_NAMES", "FACULTY_DESIGN_PARTS",
]

#: The nine faculties `FACULTIES.md` 2.1-2.9 names. Four of them are built; five are not. This
#: list is a programmed requirement, never a learned one (`UNITY_EYE.md:93`: "All requirements
#: a_i = 1 (PROPOSED ...; never learned from an invented gold)").
FACULTY_DESIGN_PARTS = (
    "curiosity", "wondering", "pondering", "imagination", "self_notice",
    "asking", "integration", "refusal", "memory_of_path",
)

SIGNAL_NAMES = (
    "tests_passing", "suite_complete", "mechanism_proofs", "design_coverage", "read_only",
)

# UNDECIDED IN SOURCES: which packages the eye watches, when the owning instruction says to point it at "the real builds in this project" and names no list -- so this build watches the two merged packages, `faculties_v2` and `language_v2`, and says so in the reading rather than deciding for every folder on the disk.
# UNDECIDED IN SOURCES: which signals stand in for the design's nine brain signals, when UNITY_EYE.md section 2.1 names receipts, lacunae, stations, drive balance, drive entropy, continuity, the memory check, the UNDETERMINED rate and the language skin, and these builds have no stations, no drive loop and no dialogues -- so this build measures test results, suite completeness, mechanism proofs, design coverage and read-only integrity, and records each count rule beside its number.
# UNDECIDED IN SOURCES: whether the eye may run a watched package's suite itself, when UNITY_EYE.md gives it a cadence of cheap signals and this build's eye lives inside one of the suites it would run -- so this build reads a recorded result instead, and a test re-counts the suite's cases to catch a stale record.
# UNDECIDED IN SOURCES: whether comparing a faculty-roster yield to a coverage-ledger yield is a like-for-like comparison, when the Limiting Reagent logic assumes one recipe's ingredients and these are two different count rules -- so this build puts each package's rule in the reading and compares the two yields anyway, which is what "the weakest package" means here and is not a claim that the two packages are otherwise alike.
# UNDECIDED IN SOURCES: what counts as the case count a package declares, when the faculties README says "37 cases, all passing" and the language README says "30 runnable cases" -- so this build parses the first "<n> cases" phrase out of the README and reports it, and never uses it to score anything.


@dataclasses.dataclass(frozen=True)
class Package:
    """One watched build: where it lives, what it must prove, and how its coverage is counted."""

    name: str
    folder: str
    suite_file: str = "test_all.py"
    readme_file: str = "README.md"
    roster_file: str = ""
    coverage_rule: str = ""
    required_mechanisms: tuple = ()
    design_parts: tuple = ()

    def root(self, base: str) -> str:
        return os.path.join(base, self.folder)

    def required_mechanism_names(self) -> tuple:
        return tuple(item[0] for item in self.required_mechanisms)


#: The watch list. The two builds this merge produced, and the mechanisms each of them carries.
#: `UNDECIDED IN SOURCES` line in README.md: which packages the eye watches.
PACKAGES = (
    Package(
        name="faculties_v2",
        folder="faculties_v2",
        roster_file="faculties.py",
        coverage_rule="FACULTIES tuples carried over the nine faculties FACULTIES.md 2.1-2.9 name",
        required_mechanisms=(
            ("RESTART_FALLBACK", "test_the_restart_fallback_is_wired_into_pondering"),
            ("UNITY_EYE", "test_the_eye_reads_the_real_builds_and_names_the_weakest_package"),
        ),
        design_parts=FACULTY_DESIGN_PARTS,
    ),
    Package(
        name="language_v2",
        folder="language_v2",
        coverage_rule="coverage-ledger cells COVERED over the cells probed (10 x 4 x 5 = 200)",
        required_mechanisms=(
            ("RESTART_FALLBACK", "the_restart_fallback_is_wired_into_the_tap"),
        ),
        design_parts=(),
    ),
)


@dataclasses.dataclass(frozen=True)
class RecordedSuite:
    """A suite result recorded from a real run: the command, the counts, the tail, the digest."""

    package: str
    command: str
    cases_run: int
    cases_passed: int
    tail: tuple = ()
    passed_tests: tuple = ()
    coverage_covered: object = None
    coverage_probed: object = None
    sha256: str = ""

    @property
    def all_passed(self) -> bool:
        return self.cases_passed == self.cases_run


def recorded_path(base: str) -> str:
    """Where the recorded suite results live: the eye's own store, never the watched folders."""
    return os.path.join(base, "faculties_v2", "eye", "recorded_suite_results.json")


def load_recorded(base: str) -> dict:
    """Read the recorded suite results, keyed by package name. Reading only."""
    path = recorded_path(base)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    out = {}
    for row in payload.get("results", ()):
        out[row["package"]] = RecordedSuite(
            package=row["package"],
            command=row["command"],
            cases_run=int(row["cases_run"]),
            cases_passed=int(row["cases_passed"]),
            tail=tuple(row.get("tail", ())),
            passed_tests=tuple(row.get("passed_tests", ())),
            coverage_covered=row.get("coverage_covered"),
            coverage_probed=row.get("coverage_probed"),
            sha256=row.get("sha256", ""),
        )
    return out


def cases_registered(text: str) -> int:
    """How many cases a suite registers: every function carrying the `@case` decorator."""
    tree = ast.parse(text)
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                name = decorator.id if isinstance(decorator, ast.Name) else None
                if name == "case":
                    count += 1
    return count


_CASES_IN_README = re.compile(r"(\d+)\s+(?:runnable\s+)?(?:test\s+)?cases", re.IGNORECASE)


def declared_cases(text: str) -> object:
    """The case count a package's README claims, or None when it claims none."""
    found = _CASES_IN_README.search(text)
    return int(found.group(1)) if found else None


def faculty_roster(text: str) -> tuple:
    """The faculty names a package's own source carries, read out of `FACULTIES = (...)`.

    Read as text and parsed with `ast`, so the eye never imports the build it watches.
    """
    tree = ast.parse(text)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "FACULTIES":
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):        # pragma: no cover - a computed tuple
                    return ()
                return tuple(item for item in value if isinstance(item, str))
    return ()


def _fraction(numerator, denominator, *, absent_detail):
    if denominator in (None, 0) or numerator is None:
        return None, absent_detail
    return Fraction(int(numerator), int(denominator)), "%d of %d" % (numerator, denominator)


def measure(package: Package, reading: tap.TapReading, recorded, *, read_only):
    """Build the package's one recipe from what was read. Every number is a count, exactly.

    `reading` is the tap's reading of the package folder; `recorded` is that package's recorded
    suite result or None; `read_only` is the tap's own finding about its digest.
    """
    suite_text = ""
    readme_text = ""
    for relative, _digest in reading.files:
        if relative == package.suite_file:
            suite_text = reading.text(relative)
        elif relative == package.readme_file:
            readme_text = reading.text(relative)
    registered = cases_registered(suite_text) if suite_text else 0

    results = recorded if isinstance(recorded, dict) else {}
    result = results.get(package.name)

    tests_passing, tests_detail = _fraction(
        None if result is None else result.cases_passed,
        None if result is None else result.cases_run,
        absent_detail="no recorded suite result for %s" % (package.name,),
    )
    suite_complete, suite_detail = _fraction(
        None if result is None else result.cases_run,
        registered or None,
        absent_detail="the suite file registers no case",
    )

    passed_tests = set(result.passed_tests) if result is not None else set()
    proved = [proof for _mechanism, proof in package.required_mechanisms
              if ("def %s(" % (proof,)) in suite_text and proof in passed_tests]
    mechanisms, mechanisms_detail = _fraction(
        len(proved), len(package.required_mechanisms) or None,
        absent_detail="this package is required to carry no mechanism",
    )

    if package.design_parts:
        roster_text = ""
        for relative, _digest in reading.files:
            if relative == package.roster_file:
                roster_text = reading.text(relative)
        carried = tuple(name for name in faculty_roster(roster_text) if name in package.design_parts)
        coverage, coverage_detail = _fraction(
            len(carried), len(package.design_parts),
            absent_detail="no design part list for %s" % (package.name,),
        )
        coverage_detail = "%d of %d faculties carried: %s" % (
            len(carried), len(package.design_parts), ", ".join(carried) or "none"
        )
    else:
        covered = None if result is None else result.coverage_covered
        probed = None if result is None else result.coverage_probed
        coverage, coverage_detail = _fraction(
            covered, probed,
            absent_detail="no coverage ledger in the recorded result",
        )
        if coverage is not None:
            coverage_detail = "%d of %d probed cells covered" % (covered, probed)

    read_only_measured, read_only_detail = _fraction(
        1 if read_only else 0, 1, absent_detail="the tap did not report"
    )
    read_only_detail = "digest held across the reading" if read_only else "THE DIGEST MOVED"

    counts = (
        ("tests_passing", "cases passed / cases run", recipe.ONE, tests_passing, tests_detail),
        ("suite_complete", "cases run / cases registered in the suite file", recipe.ONE,
         suite_complete, suite_detail),
        ("mechanism_proofs", "required mechanisms proved by a named passing test",
         recipe.ONE, mechanisms, mechanisms_detail),
        ("design_coverage", package.coverage_rule, recipe.ONE, coverage, coverage_detail),
        ("read_only", "the tap's digest held across the reading", recipe.ONE,
         read_only_measured, read_only_detail),
    )
    ingredients = tuple(
        recipe.Ingredient(name=name, count_rule=rule, required=requirement, measured=measured,
                          detail=detail)
        for name, rule, requirement, measured, detail in counts
    )
    return recipe.Recipe("OM_" + package.name, ingredients)
