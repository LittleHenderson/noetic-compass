"""drive_loop.py -- when each faculty gets a turn.

WHAT THIS MODULE DOES
---------------------
DRIVE_LOOP.md turns the owner's words ("oscillating random through the 7 desire or satisfying
gravitational pulls of each that increase and decrease in satisfied and unsatisfied") into
exact rules. This module runs them, and it is the only thing in the package that decides which
faculty acts on a tick.

One tick, in the design's own order (ARCHITECTURE.md section 1 steps 0-8):

  0. INPUT    new real rows, if any. An empty queue is what makes the tick idle.
  1. SENSE    the idle flag, the stored residual, the buffer's counts.
  2. MEASURE  the previous tick's measured gain is added to the drive that acted; every other
              drive decays.
  3. MASK     a drive with no available action is masked and logged `DRIVE_DEPRIORITIZED:<k>`.
              Never given invented work (the recursive CJT tick's rule).
  4. ARBITRATE the guards in order -- masked, pair cap, max neglect, dwell -- then the arm:
              greedy, round-robin, fixed priority, or the owner's seeded pull-sampling.
  5. ACT      the focus drive's faculty runs and writes candidates into the held buffer.
  6. VERIFY   the one door: `guard.verify` on every HELD candidate, with the evidence supplied
              for this tick. Imagined evidence is refused here and nothing moves.
  7. WRITE    `guard.believe` for candidates the verifier admitted on real rows. Nothing else
              reaches the Bias.
  8. LOG      a frozen `TurnRecord`. Every tick is recorded, including a tick where every
              drive was masked.

Two things about idle:
  * idle means no new input is queued on this tick;
  * pondering is F7's idle-time action (FACULTIES.md 2.3, ARCHITECTURE.md section 2), so F7 is
    *masked* on a tick with queued input. That is how "idle triggers pondering" is made a rule
    of the loop rather than a habit of the caller: the loop cannot reach pondering when busy.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT fit anything. There is no writer, no fitter and no recipe book here, so F7's
    gain is 0 by construction and F2/F4/F6/F1/F3 have no faculty in this build and are masked
    every tick. README.md lists that as unbuilt; it is not a small detail.
  * It does NOT compute Fisher-Rao anything. DRIVE_LOOP.md section 6 asks for restlessness,
    distance to the barycenter, fixation and thrash flags and a GEODESIC-STEP arm. None of
    those is in this build; the four arms here are deterministic for the same inputs (the
    seeded arm's seed is one of those inputs) and their tie order is the fixed one.
  * It does NOT decide what a candidate means. It schedules; `guard` decides.
  * It does NOT run a stage (16 ticks) or the F/E inversion checks. Those need a run with a
    real family, and this build has no world in it.
  * It does NOT let randomness reach anything but the focus draw. The seeded draw picks which
    drive acts. It cannot write a candidate, a verdict, a belief or a gain.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from fractions import Fraction

import guard
from guard import ADMITTED, GuardRefusal
from held import HeldBuffer

__all__ = [
    "DRIVES", "DRIVE_NAMES", "INVOLUTION_PAIRS", "ARMS", "FIXED_PRIORITY",
    "GAMMA", "DECAY", "S_LO", "S_HI", "D_MIN", "N_NEGLECT", "STAGE_TICKS", "K_PROPOSED",
    "DriveLoop", "TurnRecord", "DriveLoopRefusal",
]

#: The 7 Core Drives, in the fixed order everything ties by.
DRIVES = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
DRIVE_NAMES = {
    "F1": "Unity",
    "F2": "Wisdom",
    "F3": "Vitality",
    "F4": "Connection",
    "F5": "Agency",
    "F6": "Structure",
    "F7": "Purpose",
}
#: The three involution pairs and the self-dual drive (DRIVE_LOOP.md section 4, F4 no pair).
INVOLUTION_PAIRS = (("F1", "F7"), ("F2", "F6"), ("F3", "F5"))

#: The arms. Four deterministic ones and the owner's seeded draw.
GREEDY = "GREEDY"
ROUND_ROBIN = "ROUND_ROBIN"
FIXED_PRIORITY_ARM = "FIXED_PRIORITY"
PULL_SAMPLING = "PULL_SAMPLING"
ARMS = (GREEDY, ROUND_ROBIN, FIXED_PRIORITY_ARM, PULL_SAMPLING)
FIXED_PRIORITY = ("F7", "F6", "F2", "F5", "F4", "F1", "F3")

#: The PROPOSED constants of DRIVE_LOOP.md section 1 and 4, exact as written there.
GAMMA = 2
DECAY = Fraction(1, 32)
S_LO = Fraction(1, 64)
S_HI = Fraction(63, 64)
D_MIN = 2
N_NEGLECT = 24
STAGE_TICKS = 16
K_PROPOSED = 8
PAIR_CAP = 4
DIAL_SCALE = 10
SPACE = 2 ** 32

#: Which action each drive has in THIS build. A drive whose entry says "not in this build" is
#: masked every tick, which is the design's treatment of a drive with no available action.
ACTION_NOTE = {
    "F1": "integrate: not in this build",
    "F2": "curiosity schedule: not in this build",
    "F3": "consolidate: expiry is a tick step here, not a faculty turn",
    "F4": "ask: not in this build",
    "F5": "imagination, with wondering nested inside it",
    "F6": "verify: a tick step and always on, not a faculty turn",
    "F7": "pondering, during idle only; the fit is not in this build",
}

#: Refusal codes.
LOOP_NEEDS_A_BIAS = "LOOP_NEEDS_A_BIAS"
LOOP_NEEDS_A_BUFFER = "LOOP_NEEDS_A_BUFFER"
LOOP_NEEDS_A_COORDINATOR = "LOOP_NEEDS_A_COORDINATOR"
LOOP_ARM_NOT_A_WORD = "LOOP_ARM_NOT_A_WORD"
LOOP_BAD_SEED = "LOOP_BAD_SEED"
LOOP_INPUT_NOT_REAL = "LOOP_INPUT_NOT_REAL"
LOOP_BAD_EVIDENCE = "LOOP_BAD_EVIDENCE"
LOOP_NO_ACTION_FOR_DRIVE = "LOOP_NO_ACTION_FOR_DRIVE"

#: Reason words a record carries.
MASKED_NO_FACULTY = "NO_FACULTY_IN_THIS_BUILD"
MASKED_NOT_IDLE = "PONDERING_RUNS_ONLY_WHEN_IDLE"
MASKED_NO_IMAGINATION = "NO_IMAGINATION_BUILDER"
PAIR_CAP_WINS = "PAIR_CAP_RESTRICTED"
PAIR_CAP_UNSERVICEABLE = "PAIR_CAP_UNSERVICEABLE"
FORCED_BY_NEGLECT = "FORCED_BY_MAX_NEGLECT"
HELD_BY_DWELL = "HELD_BY_MIN_DWELL"
NO_UNMASKED_DRIVE = "NO_UNMASKED_DRIVE"
GAIN_NOT_MEASURABLE = "GAIN_NOT_MEASURABLE_WITHOUT_A_FITTER"

# UNDECIDED IN DESIGN: whether "idle" is read per tick or per stage -- FACULTIES.md 2.3 and DRIVE_LOOP.md 2 say the pass runs when "no new input is queued" and give no window, so this build reads it per tick: a tick with an empty input queue is idle, and the next tick with input is not.
# UNDECIDED IN DESIGN: which drive owns pondering and whether wondering is a turn of its own -- ARCHITECTURE.md section 2 puts "imagine + wonder" under F5 and "fit on current Omega; else ponder" under F7, and never says whether wondering is a separate turn or a step nested inside the F5 turn, so this build nests wondering inside the F5 turn with one level receipt per level and gives pondering the F7 turn.
# UNDECIDED IN DESIGN: what gain a faculty earns when the measured outcome needs a fitter this build does not contain -- DRIVE_LOOP.md section 2 defines F7's gain as unexplained rows before minus after and FACULTIES.md leaves the fit outside the faculty, so with no fitter this build records gain 0 and writes GAIN_NOT_MEASURABLE_WITHOUT_A_FITTER on the tick rather than invent a number.
# UNDECIDED IN DESIGN: which HELD candidates the tick's VERIFY step checks -- ARCHITECTURE.md section 1 step 6 says VERIFY runs every tick and does not say whether it checks every HELD candidate or only the ones an arm names, so this build checks every HELD candidate in the buffer against the evidence supplied for that tick.
# UNDECIDED IN DESIGN: the values of the drive loop's PROPOSED constants -- DRIVE_LOOP.md section 1 and OPEN_QUESTIONS.md mark gamma = 2, delta = 1/32, s_lo = 1/64, s_hi = 63/64, D_min = 2, max neglect 24 ticks, the pair cap 4, stage 16 ticks and K = 8 as PROPOSED for the owner to accept or change, so this build uses exactly those numbers and freezes them as constants rather than pretending they were decided.


class DriveLoopRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# The seeded draw: the only random step in the package
# --------------------------------------------------------------------------- #
class _Draw:
    """A small seeded integer generator. Deterministic, saved, replayable.

    DRIVE_LOOP.md section 7 allows exactly one random step in the loop: the PULL-SAMPLING
    focus draw. This is it. It draws an integer in [0, 2**32); it cannot produce a candidate, a
    verdict, a belief or a gain, because nothing else here can read it.
    """

    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise DriveLoopRefusal(LOOP_BAD_SEED, f"a seed is a non-negative integer, got {seed!r}")
        self._seed = seed
        self._state = (seed * 6364136223846793005 + 1442695040888963407) % (2 ** 64)
        self._draws = 0

    @property
    def draws(self) -> int:
        return self._draws

    def integer(self) -> int:
        self._state = (self._state * 6364136223846793005 + 1442695040888963407) % (2 ** 64)
        self._draws += 1
        return (self._state >> 32) % SPACE


# --------------------------------------------------------------------------- #
# One recorded tick
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class TurnRecord:
    """Everything one tick did. Every tick produces one of these, masked or not."""

    tick: int
    idle: bool
    arm: str
    focus: object
    faculty: object
    masked: tuple = ()
    pair_cap: object = None
    forced: object = None
    dwell: object = None
    wrote: tuple = ()
    verified: tuple = ()
    believed: tuple = ()
    expired: tuple = ()
    verify_refused: object = None
    gains: tuple = ()
    satisfactions: tuple = ()
    pulls: tuple = ()
    note: str = ""
    draw: object = None

    @property
    def acted(self) -> bool:
        return self.focus is not None

    def as_dict(self) -> dict:
        return {
            "tick": self.tick,
            "idle": self.idle,
            "arm": self.arm,
            "focus": self.focus,
            "faculty": self.faculty,
            "masked": [list(item) for item in self.masked],
            "pair_cap": self.pair_cap,
            "forced": self.forced,
            "dwell": self.dwell,
            "wrote": list(self.wrote),
            "verified": [list(item) for item in self.verified],
            "believed": [list(item) for item in self.believed],
            "expired": list(self.expired),
            "verify_refused": self.verify_refused,
            "gains": [list(item) for item in self.gains],
            "satisfactions": [list(item) for item in self.satisfactions],
            "pulls": [list(item) for item in self.pulls],
            "note": self.note,
            "draw": self.draw,
        }


# --------------------------------------------------------------------------- #
# The loop
# --------------------------------------------------------------------------- #
class DriveLoop:
    """One drive loop over one Bias and one held buffer.

    `imagine` and `ponder` are the only two faculties this build can give a turn to. Each is a
    callable taking the `idle` flag and returning a `faculties.FacultyReport`. A drive whose
    action is not supplied is masked on every tick, with the reason recorded.
    """

    def __init__(
        self,
        bias,
        held,
        *,
        coordinator,
        arm=GREEDY,
        seed=0,
        imagine=None,
        ponder=None,
    ) -> None:
        if not callable(getattr(bias, "write", None)) or not hasattr(bias, "version"):
            raise DriveLoopRefusal(LOOP_NEEDS_A_BIAS, f"the loop writes a Bias, got {type(bias).__name__}")
        if not isinstance(held, HeldBuffer):
            raise DriveLoopRefusal(LOOP_NEEDS_A_BUFFER, f"the loop needs a HeldBuffer, got {type(held).__name__}")
        if not isinstance(coordinator, str) or not coordinator.strip():
            raise DriveLoopRefusal(LOOP_NEEDS_A_COORDINATOR, f"a coordinator must be named, got {coordinator!r}")
        if arm not in ARMS:
            raise DriveLoopRefusal(LOOP_ARM_NOT_A_WORD, f"arm {arm!r} is not one of {list(ARMS)}")
        if imagine is not None and not callable(imagine):
            raise DriveLoopRefusal(LOOP_NO_ACTION_FOR_DRIVE, "imagine must be callable")
        if ponder is not None and not callable(ponder):
            raise DriveLoopRefusal(LOOP_NO_ACTION_FOR_DRIVE, "ponder must be callable")
        self._bias = bias
        self._held = held
        self._coordinator = coordinator
        self._arm = arm
        self._imagine = imagine
        self._ponder = ponder
        self._draw = _Draw(seed)
        self._seed = seed
        self._s = {drive: Fraction(1, 2) for drive in DRIVES}
        self._tick = 0
        self._history: list = []
        self._last_focus = None
        self._dwell_left = 0
        self._last_seen = {drive: 0 for drive in DRIVES}

    # -- read-only views ---------------------------------------------------- #
    @property
    def arm(self) -> str:
        return self._arm

    @property
    def tick_count(self) -> int:
        return self._tick

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def history(self) -> tuple:
        return tuple(self._history)

    def satisfactions(self) -> tuple:
        return tuple((drive, self._s[drive]) for drive in DRIVES)

    def pulls(self) -> tuple:
        return tuple((drive, self._pull(drive)) for drive in DRIVES)

    def digest(self) -> str:
        """sha256 over every recorded tick. Two loops with the same inputs match on this."""
        payload = [record.as_dict() for record in self._history]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    # -- the arithmetic ----------------------------------------------------- #
    def _pull(self, drive) -> Fraction:
        return (1 - self._s[drive]) ** GAMMA

    def _normalised_pulls(self, unmasked) -> dict:
        total = sum((self._pull(drive) for drive in unmasked), Fraction(0))
        if total == 0:  # pragma: no cover - s_hi < 1 keeps every pull > 0
            return {drive: Fraction(0) for drive in unmasked}
        return {drive: self._pull(drive) / total for drive in unmasked}

    def _measure(self, gains) -> None:
        """Apply last tick's measured gains, then decay every drive that did not act."""
        for drive in DRIVES:
            gain = gains.get(drive)
            if gain is not None and gain > 0:
                self._s[drive] = min(S_HI, self._s[drive] + (1 - self._s[drive]) * gain)
            else:
                self._s[drive] = max(S_LO, self._s[drive] * (1 - DECAY))

    # -- the tick ----------------------------------------------------------- #
    def tick(self, *, new_input=(), evidence=None, unexplained=None, age_cap=None):
        """Run one tick and return its `TurnRecord`.

        `new_input` is the rows that arrived this tick (real rows only). `evidence` is the
        tick's verification evidence; a `RealEvidence` verifies HELD candidates and an
        `ImaginedEvidence` is refused with nothing moving. `unexplained` is what pondering
        breaks down.
        """
        tick = self._tick
        self._held.begin_tick(tick)

        # 0. INPUT -- real rows only. Anything tagged INTERNAL is refused at the door.
        incoming = tuple(new_input)
        for row in incoming:
            if not isinstance(row, guard.Row) or row.tag != guard.REAL:
                raise DriveLoopRefusal(
                    LOOP_INPUT_NOT_REAL,
                    f"input {row!r} is not a real row; imagined rows never enter as input "
                    f"(Rule P)",
                )
        idle = len(incoming) == 0

        # 1. SENSE -- the idle flag is the whole of it in this build: there is no
        # Lacunarity Machine, no stored residual store and no fit-evaluation counter here.
        sensed_idle = idle

        # 2. MEASURE -- last tick's gain, on the drive that acted, then decay the rest.
        previous = getattr(self, "_pending_gains", {})
        self._measure(previous)

        # 3. MASK
        masked, available = self._mask(sensed_idle)

        # 4. ARBITRATE
        focus, pair_cap, forced, dwell, note = self._arbitrate(available, masked)

        # 5. ACT
        report = None
        faculty = None
        if focus is not None:
            faculty, report = self._act(focus, sensed_idle)

        # 6. VERIFY -- the one door, on every HELD candidate.
        verified, verdicts, verify_refused = self._verify(evidence)

        # 7. WRITE -- belief only from an admission on real evidence.
        believed = self._write_belief(verified, verdicts)

        # 8. EXPIRY -- the consolidator's step, only when the caller names a cap.
        expired = ()
        if age_cap is not None:
            expired = self._held.expire(age_cap=age_cap, tick=tick)

        # 9. LOG
        gains = self._gains(focus, report)
        self._pending_gains = gains
        if focus == "F7":
            # Pondering's measured outcome needs the fit this build does not contain, so the
            # tick says so on its own record instead of carrying an invented number.
            note = "; ".join(part for part in (note, GAIN_NOT_MEASURABLE) if part)
        record = TurnRecord(
            tick=tick,
            idle=idle,
            arm=self._arm,
            focus=focus,
            faculty=faculty,
            masked=tuple((f"DRIVE_DEPRIORITIZED:{drive}", why) for drive, why in masked.items()),
            pair_cap=pair_cap,
            forced=forced,
            dwell=dwell,
            wrote=tuple(report.wrote) if report is not None else (),
            verified=verified,
            believed=believed,
            expired=expired,
            verify_refused=verify_refused,
            gains=tuple((drive, gains[drive]) for drive in DRIVES if drive in gains),
            satisfactions=self.satisfactions(),
            pulls=self.pulls(),
            note=note,
            draw=self._draw.draws,
        )
        self._history.append(record)
        if focus is not None:
            self._last_seen[focus] = tick
            self._last_focus = focus
            # D_min ticks in total: a fresh choice holds the next D_min-1 ticks, and each tick
            # the dwell guard holds spends one of them. A held tick that reset the counter
            # would hold for ever, which is the bug this line exists to prevent.
            if dwell is not None:
                self._dwell_left = max(0, self._dwell_left - 1)
            else:
                self._dwell_left = D_MIN - 1
        self._tick += 1
        return record

    # -- step 3: masks ------------------------------------------------------ #
    def _mask(self, idle):
        """Which drives have no action this tick, and why. Masked drives get no work."""
        masked = {}
        available = []
        for drive in DRIVES:
            reason = None
            if drive == "F5":
                if self._imagine is None:
                    reason = MASKED_NO_IMAGINATION
            elif drive == "F7":
                if self._ponder is None:
                    reason = MASKED_NO_FACULTY
                elif not idle:
                    reason = MASKED_NOT_IDLE
            else:
                reason = MASKED_NO_FACULTY
            if reason is None:
                available.append(drive)
            else:
                masked[drive] = reason
        return masked, available

    # -- step 4: guards, then the arm -------------------------------------- #
    def _arbitrate(self, available, masked):
        if not available:
            return None, None, None, None, NO_UNMASKED_DRIVE
        pool = list(available)
        pair_cap = None
        forced = None
        dwell = None

        # Pair cap: dial_k = 10 * p_k; a pair more than 4 apart restricts the tick to the
        # higher-pull member. If that member is masked, nothing is forced (logged).
        for left, right in INVOLUTION_PAIRS:
            dial_left = DIAL_SCALE * self._pull(left)
            dial_right = DIAL_SCALE * self._pull(right)
            if abs(dial_left - dial_right) > PAIR_CAP:
                winner = left if dial_left > dial_right else right
                if winner in masked:
                    pair_cap = f"{PAIR_CAP_UNSERVICEABLE}:{left}/{right}"
                else:
                    pair_cap = f"{PAIR_CAP_WINS}:{left}/{right}->{winner}"
                    pool = [winner]
                break

        # Max neglect: an unmasked drive unseen for N_NEGLECT ticks is forced next.
        if len(pool) > 1:
            for drive in DRIVES:
                if drive in pool and self._tick - self._last_seen[drive] >= N_NEGLECT:
                    forced = drive
                    pool = [drive]
                    break

        # Dwell: the drive that just acted keeps the tick, unless it is masked or forbidden.
        if forced is None and self._dwell_left > 0 and self._last_focus in pool:
            dwell = f"{HELD_BY_DWELL}:{self._last_focus}"
            return self._last_focus, pair_cap, forced, dwell, HELD_BY_DWELL

        focus = self._choose(pool)
        return focus, pair_cap, forced, dwell, ""

    def _choose(self, pool):
        if len(pool) == 1:
            return pool[0]
        q = self._normalised_pulls(pool)
        if self._arm == GREEDY:
            best = max(pool, key=lambda drive: (q[drive], -DRIVES.index(drive)))
            return best
        if self._arm == ROUND_ROBIN:
            start = 0
            if self._last_focus in DRIVES:
                start = DRIVES.index(self._last_focus) + 1
            ordered = DRIVES[start:] + DRIVES[:start]
            for drive in ordered:
                if drive in pool:
                    return drive
            return pool[0]  # pragma: no cover - pool is never empty here
        if self._arm == FIXED_PRIORITY_ARM:
            for drive in FIXED_PRIORITY:
                if drive in pool:
                    return drive
            return pool[0]  # pragma: no cover
        # PULL_SAMPLING -- the one random step in the loop, seeded and saved.
        cumulative = Fraction(0)
        draw = self._draw.integer()
        for drive in pool:
            cumulative += q[drive]
            if draw < cumulative * SPACE:
                return drive
        return pool[-1]

    # -- step 5: act -------------------------------------------------------- #
    def _act(self, focus, idle):
        action = self._imagine if focus == "F5" else self._ponder
        report = action(idle)
        faculty = getattr(report, "faculty", None)
        return faculty, report

    # -- step 6: verify ----------------------------------------------------- #
    def _verify(self, evidence):
        """Run the one door over every HELD candidate. Imagined evidence moves nothing.

        Returns `(log_rows, verdicts_by_id, refusal_code)`. A `GuardRefusal` -- which is what
        an imagined world's evidence gets, and the only way verification can be reached with
        it -- stops the step with the code recorded and nothing moved.
        """
        if evidence is None:
            return (), {}, None
        log = []
        verdicts = {}
        refused = None
        for candidate_id in self._held.held_ids():
            entry = self._held.get(candidate_id)
            try:
                verdict = guard.verify(entry.proposal, evidence)
            except GuardRefusal as exc:
                refused = exc.code
                break
            self._held.settle(candidate_id, verdict)
            verdicts[candidate_id] = verdict
            log.append((candidate_id, verdict.word, verdict.code))
        return tuple(log), verdicts, refused

    # -- step 7: write ------------------------------------------------------ #
    def _write_belief(self, verified, verdicts):
        """The only place a candidate reaches the Bias. A refusal reaches nothing."""
        believed = []
        for candidate_id, word, _code in verified:
            verdict = verdicts[candidate_id]
            if verdict.word != ADMITTED:
                continue
            entry = self._held.get(candidate_id)
            version = guard.believe(
                self._bias,
                coordinator=self._coordinator,
                key=f"candidate:{candidate_id}",
                value={
                    "canonical_form": entry.canonical_form,
                    "candidate_id": candidate_id,
                    "faculty": entry.faculty,
                    "world": entry.proposal.world,
                    "insight": entry.is_insight,
                    "verdict": verdict.code,
                    "verifier": verdict.verifier,
                },
                verdict=verdict,
            )
            believed.append((candidate_id, version))
        return tuple(believed)

    # -- step 9's gains ----------------------------------------------------- #
    def _gains(self, focus, report):
        """The measured gain for this tick's action. Only counted events; never a draw."""
        gains = {}
        if focus is None:
            return gains
        if focus == "F5":
            wrote = len(getattr(report, "wrote", ()) or ())
            k = getattr(report, "k", None) or K_PROPOSED
            gains[focus] = min(Fraction(1), Fraction(wrote, k))
        elif focus == "F7":
            # No fitter in this build, so no measured gain: see the marker above.
            gains[focus] = Fraction(0)
        return gains
