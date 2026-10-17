"""eye/eye.py -- the Unity Eye (F1 watcher): it reads, it computes, it logs, it acts on nothing.

THE FORM (ACCEPTED_BY_OWNER, `OWNER_RULING_UNITY_EYE_20261015.md` section 3)
MINI-VERSION: one recipe over the measured health signals (`eye/recipe.py`), the Limiting Reagent
readout naming the component most short of unity, its own Lacunarity-free log, the RPM gate words
G1-G4, and an eta / epsilon receipt on every reading. 0 learned parameters.

THE THREE PROPERTIES, AND WHERE EACH IS ENFORCED
  1. **It sits outside what it watches.** The eye is a gauge, not a part of the engine
     (`UNITY_EYE.md:50-53`). It reads each package through `eye/tap.py`, which hashes the folder
     before and after and refuses when the digest moves.
  2. **It cannot write.** The eye has no `write`, no `believe`, no verdict and no handle on any
     watched object: its own store is `self._log`, an in-memory list, plus whatever the caller
     does with the records it returns. `UnityEye` exposes no method that takes a value to store
     in a watched build, and the modules it lives beside (`restart.py`, `faculties.py`,
     `drive_loop.py`, `guard.py`, `held.py`) do not import it at all.
  3. **It never gates.** No method here returns a yes/no that any decision reads. `read()` returns
     a reading; `would_propose()` returns proposals marked report-only; nothing in this package
     is consulted by the drive loop, by the verifier or by the buffer. The ablation test in
     `test_all.py` runs the drive loop with the eye and without it and compares the records, the
     buffer digest and the Bias digest.

WHAT "FIX" AND "HELP" MEAN HERE (`UNITY_EYE.md:43-49`)
A proposal is a record. "Fix" = propose a repair that must go through the same VERIFY and receipt
path as any other change; "help" = propose that a missing part be built or a check be re-run. The
eye never performs either. Every proposal carries the word `REPORT_ONLY`, and the ones the design
says must never be fixed by the watcher carry `REPORTED` instead, so "I saw this and it is not
mine to touch" is a recorded word and not a silence.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses
import os

import eye.recipe as recipe
import eye.signals as signals
import eye.tap as tap

__all__ = [
    "UnityEye", "EyeReading", "EyeRefusal", "PROPOSAL_KINDS", "REPORT_ONLY",
    "FIX", "HELP", "REPORTED", "NO_PROPOSAL", "EYE_STORES_NOTHING",
]

FIX = "FIX"
HELP = "HELP"
REPORTED = "REPORTED"
NO_PROPOSAL = "NONE"
PROPOSAL_KINDS = (FIX, HELP, REPORTED, NO_PROPOSAL)

#: Every proposal the eye makes is marked with this word, so no caller can mistake it for an act.
REPORT_ONLY = "REPORT_ONLY"

#: The word the eye has no authority over: it reports and stops.
EYE_STORES_NOTHING = "REPORT_ONLY_THE_EYE_STORES_NOTHING_IT_WATCHES"

#: Refusal codes.
EYE_NO_PACKAGES = "EYE_NO_PACKAGES"
EYE_NEEDS_A_FOLDER = "EYE_NEEDS_A_FOLDER"

# UNDECIDED IN SOURCES: whether the eye may make a FIX proposal at all here, when the owner's acting ruling approves acting only inside test U1 on the laptop and this build is not U1 -- so this build marks every proposal REPORT_ONLY, performs none, and records the kind (FIX, HELP, REPORTED) as a word for what a later acting build would do.
# UNDECIDED IN SOURCES: how a tie between two packages is reported, when the gate word G3 names both and this instruction asks the output to name one weakest package -- so this build names both in `tied_with`, breaks the tie for the headline by the package's name in sorted order, and prints the G3 word beside the answer.
# UNDECIDED IN SOURCES: whether the eye's log may be written to disk, when UNITY_EYE.md says its only write is its own append-only log and the log's durability is never specified -- so this build keeps the log in memory, returns it to the caller, and writes nothing anywhere.
# UNDECIDED IN SOURCES: what the eye should do when its own package is the weakest, when nothing in the sources says a watcher may or may not report on the build it lives in -- so this build reports it, because suppressing it would be the eye preferring a flattering reading to a measured one.


class EyeRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclasses.dataclass(frozen=True)
class EyeReading:
    """One reading of the whole watch list: the per-package recipes, the weakest, and the gate."""

    stage_id: str
    components: tuple
    taps: tuple
    weakest: dict
    gate: object
    receipt: dict

    def component(self, name) -> recipe.RecipeReading:
        for component in self.components:
            if component.component == "OM_" + name:
                return component
        raise EyeRefusal("EYE_NO_SUCH_COMPONENT", f"{name!r} is not one of {[c.component for c in self.components]}")

    def as_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "components": [item.record() for item in self.components],
            "taps": list(self.taps),
            "weakest": dict(self.weakest),
            "gate": self.gate,
            "receipt": dict(self.receipt),
        }

    def text(self) -> str:
        """The plain-English reading, naming the weakest package and saying why."""
        if self.weakest.get("package") is None:
            return "the eye read %d packages and none of them could be ordered" % (len(self.components),)
        weak = self.weakest
        return (
            "weakest package: %s (Y_T %s). Limiting reagent: %s -- %s. Gate: %s."
            % (weak["package"], weak["Y_T"], weak["ingredient"], weak["why"],
               (self.gate or "no gate word; one limiting reagent, everything present"))
        )

    def __repr__(self) -> str:
        return "EyeReading(%s, %d packages, gate=%r)" % (
            self.stage_id, len(self.components), self.gate
        )


class UnityEye:
    """The watcher. Reads every package on its list and names the one most short of unity.

    `base` is the folder that holds the watched packages; it defaults to the folder above the
    eye's own. `packages` is the watch list. `recorded` is the recorded suite results, read from
    the eye's own store when it is not passed.
    """

    def __init__(self, base: str = None, packages=None, recorded=None) -> None:
        if base is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isdir(base):
            raise EyeRefusal(EYE_NEEDS_A_FOLDER, f"the eye reads a folder of builds, got {base!r}")
        self._base = os.path.abspath(base)
        self._packages = tuple(signals.PACKAGES if packages is None else packages)
        if not self._packages:
            raise EyeRefusal(EYE_NO_PACKAGES, "the eye has nothing to watch")
        self._recorded = signals.load_recorded(self._base) if recorded is None else recorded
        self._log: list = []
        self._watched_digests: dict = {}

    # -- read-only views ----------------------------------------------------- #
    @property
    def base(self) -> str:
        return self._base

    @property
    def packages(self) -> tuple:
        return tuple(package.name for package in self._packages)

    def readings(self) -> tuple:
        """Every reading this eye has taken, in order. Append-only; nothing is removed."""
        return tuple(self._log)

    def watched_digests(self) -> dict:
        """The digest the eye saw for each watched folder on its last reading, and before it."""
        return dict(self._watched_digests)

    # -- the reading --------------------------------------------------------- #
    def read(self, stage_id: str = "stage-1") -> EyeReading:
        """Read every watched package and compute the one readout the eye exists to produce."""
        components = []
        taps = []
        receipts = {}
        for package in self._packages:
            tap_on_package = tap.Tap(package.root(self._base), exclude=tap.DEFAULT_EXCLUDE)
            reading = tap_on_package.read()                 # refuses if the digest moved
            before = reading.digest_before
            built = signals.measure(package, reading, self._recorded, read_only=reading.wrote_nothing)
            after = reading.digest_after
            self._watched_digests.setdefault(package.name, []).append((before, after))
            components.append(built.read())
            receipts[package.name] = built.read().receipt()
            taps.append(reading.as_dict())
        weakest, gate = _weakest(components)
        receipt = {
            "component_receipts": receipts,
            "all_hold": all(item["holds"] for item in receipts.values()),
            "eye_wrote_nothing": all(row["moved"] is False for row in taps),
            "stage_id": stage_id,
        }
        reading = EyeReading(
            stage_id=stage_id,
            components=tuple(components),
            taps=tuple(taps),
            weakest=weakest,
            gate=gate,
            receipt=receipt,
        )
        self._log.append(reading)
        return reading

    # -- epsilon: re-read the eye's own record and recompute ----------------- #
    def recheck(self, reading: EyeReading = None) -> dict:
        """The epsilon half of the receipt: recompute Y_T and L from the stored counts.

        The design's rule (`UNITY_EYE.md:98-99`): "eta = write the reading record; epsilon =
        re-read it from the eye's log and recompute Y_T and L from the stored counts; they must
        be equal; cached, never recomputed." Nothing here recomputes a corpus; it re-derives the
        two numbers from the counts the reading already stored.
        """
        if reading is None:
            if not self._log:
                raise EyeRefusal("EYE_HAS_READ_NOTHING", "there is no reading to re-check")
            reading = self._log[-1]
        checked = {}
        for component in reading.components:
            receipt = component.receipt()
            why = recipe.RecipeReading.recompute(component.counts)[0]
            checked[component.component] = {
                "holds": receipt["holds"] and (why == component.theoretical_yield()),
                "written_Y_T": receipt["written_Y_T"],
                "reread_Y_T": receipt["reread_Y_T"],
                "limiting": list(component.limiting()),
            }
        weakest, gate = _weakest(reading.components, last_receipt_held=all(
            row["holds"] for row in checked.values()
        ))
        return {
            "holds": all(row["holds"] for row in checked.values()),
            "components": checked,
            "weakest": weakest,
            "gate": gate,
        }

    # -- what it would propose, and never do --------------------------------- #
    def would_propose(self, reading: EyeReading = None) -> tuple:
        """The report-only proposals. Every one is a record; none of them happens.

        The map from a low reading to a proposal kind follows `UNITY_EYE.md:131-142`'s table of
        planted faults and right proposals. A missing part of the design is `REPORTED`: no
        remedy is defined for it by the sources, and a watcher that invented one would be
        inventing relevance.
        """
        if reading is None:
            if not self._log:
                raise EyeRefusal("EYE_HAS_READ_NOTHING", "there is no reading to propose from")
            reading = self._log[-1]
        proposals = []
        for component in reading.components:
            name = component.component[len("OM_"):]
            target = component.theoretical_yield()
            if target is None:
                proposals.append(_proposal(
                    name, REPORTED, "nothing_measured",
                    detail="no ingredient of this package was measured",
                    through="nothing: the eye reports and fixes nothing",
                    never="guessing a number for a package it could not read",
                ))
                continue
            if target >= recipe.ONE:
                # Every ingredient met its requirement: there is no missing part to name, and a
                # watcher that invented one would be inventing relevance.
                proposals.append(_proposal(
                    name, NO_PROPOSAL, "none",
                    detail="every ingredient met its requirement (Y_T %s)"
                           % ("%d/%d" % (target.numerator, target.denominator),),
                    through="nothing", never="inventing work where nothing is short",
                ))
                continue
            for ingredient in component.limiting():
                measured = component.get(ingredient)
                count = measured.detail
                if ingredient == "design_coverage":
                    proposals.append(_proposal(
                        name, REPORTED, ingredient,
                        detail=count,
                        through="nothing: building a missing part is outside a report-only watcher",
                        never="claiming the part exists, or building it silently",
                    ))
                elif ingredient in ("tests_passing", "suite_complete"):
                    proposals.append(_proposal(
                        name, HELP, ingredient,
                        detail=count,
                        through="re-running the package's own suite and reading its tail again",
                        never="editing a test to make it pass",
                    ))
                elif ingredient == "mechanism_proofs":
                    proposals.append(_proposal(
                        name, FIX, ingredient,
                        detail=count,
                        through="wiring the mechanism and proving it with a named test; the "
                                "package's own VERIFY and receipts still decide",
                        never="a write the verifier did not accept",
                    ))
                elif ingredient == "read_only":
                    proposals.append(_proposal(
                        name, REPORTED, ingredient,
                        detail=("a watched value moved during the reading"
                                if measured.measured is not None and measured.measured < recipe.ONE
                                else count),
                        through="nothing: the eye logs FAILURE_SEEN and repairs nothing it watches",
                        never="repairing what it watches",
                    ))
        if not proposals:
            proposals.append(_proposal(
                reading.weakest.get("package"), NO_PROPOSAL, "none",
                detail="every ingredient is at its requirement",
                through="nothing", never="nothing",
            ))
        return tuple(proposals)

    def report(self, reading: EyeReading = None) -> str:
        """The eye's output: the weakest package, named, with the reason and the gate."""
        if reading is None:
            reading = self.read()
        lines = [reading.text()]
        for component in reading.components:
            lines.append("  " + component.text())
        for proposal in self.would_propose(reading):
            lines.append(
                "  %s %s: %s (%s) -- would do: %s; must never: %s"
                % (proposal["kind"], proposal["package"], proposal["ingredient"],
                   proposal["detail"] or "no detail", proposal["through"], proposal["never"])
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return "UnityEye(%s, watches %s)" % (self._base, list(self.packages))


def _proposal(package, kind, ingredient, detail, through, never) -> dict:
    if kind not in PROPOSAL_KINDS:
        raise EyeRefusal("EYE_BAD_PROPOSAL", f"{kind!r} is not one of {list(PROPOSAL_KINDS)}")
    return {
        "package": package,
        "kind": kind,
        "ingredient": ingredient,
        "detail": detail,
        "through": through,
        "never": never,
        "mode": REPORT_ONLY,
    }


def _weakest(components, *, last_receipt_held=True):
    """The Limiting Reagent across the packages: the lowest Y_T wins, and nothing gates."""
    scored = []
    undetermined = []
    for component in components:
        target = component.theoretical_yield()
        if target is None:
            undetermined.append(component.component[len("OM_"):])
            continue
        scored.append((target, component))
    if not scored:
        return ({"package": None, "Y_T": None, "ingredient": None,
                 "why": "no package could be measured", "undetermined": tuple(undetermined)},
                recipe.G2_NOTHING_READ)
    lowest = min(target for target, _component in scored)
    winners = [component for target, component in scored if target == lowest]
    gate = None
    if len(winners) > 1:
        gate = recipe.G3_TIE_AT_THE_MINIMUM
    if not last_receipt_held:
        gate = recipe.G4_LAST_RECEIPT_FAILED
    chosen = sorted(winners, key=lambda component: component.component)[0]
    limiting = chosen.limiting()
    ingredient = limiting[0] if limiting else None
    why = ""
    if ingredient is not None:
        why = chosen.get(ingredient).detail or chosen.get(ingredient).count_rule
    weakest = {
        "package": chosen.component[len("OM_"):],
        "Y_T": "%d/%d" % (lowest.numerator, lowest.denominator),
        "ingredient": ingredient,
        "why": why,
        "limiting": list(limiting),
        "tied_with": [component.component[len("OM_"):] for component in winners
                      if component.component != chosen.component],
        "undetermined": tuple(undetermined),
    }
    return weakest, gate
