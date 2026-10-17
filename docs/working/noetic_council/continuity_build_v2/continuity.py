"""continuity.py -- the path builder for one thought.

WHAT THIS MODULE DOES
---------------------
CONTINUITY.md:21 states the design's core claim: "continuity of thought is the path
itself, indexed by station and tick, not only by turn." This module builds that path for
one thought and reads the design's own numbers off it.

``ContinuityPath`` accumulates crossings for ONE thought and exposes:
  * ``points()``       -- one point per station crossing that HAS a point. A station with
                          a FORM gap contributes no point and is counted in
                          ``form_gaps`` (CONTINUITY.md:24-26).
  * ``anchor()``       -- the anchor of the thought (CONTINUITY.md:29). Two sorts, and the
                          path says which: when S0 is bound to an atlas entry the anchor is
                          that entry's DIGEST (the owner's lifted restriction -- S0 is a
                          position in the atlas, OWNER_RULING_RPA_ATLAS_20261015.md:16-18);
                          when no atlas is bound it is the S0 point, exactly as before.
  * ``displacement()`` -- the distance from the anchor to a station's point. Refused with
                          ``ANCHOR_IS_ATLAS_DIGEST`` when the anchor is a digest, because a
                          distance between a digest and a point would be an invented number.
  * ``seams()``        -- the seams found, each with its reason. Within one thought the
                          head does not change, so by the rule at CONTINUITY.md:30-32 this
                          is always empty; ``seam_checks()`` shows, pair by pair, WHY.
  * ``summary()``      -- the counts: crossings, points, form_gaps, seams, nested_depth_max,
                          and the three atlas counts (``atlas_nodes_visited``,
                          ``atlas_edges_crossed``, ``atlas_kind_pollution``).
  * ``drift_checks()`` -- the station-level drift reading of CONTINUITY.md:60-67, reported
                          and never scored.

It also carries CJT CROSSINGS, the second thing this build added: a sequence of
``crossings.Crossing`` objects may be added beside the station crossings, in order, and
``atlas_path()`` returns the ordered node digests the thought visited. A crossing is
accepted only when it really is a Crossing (``crossings.is_cjt``) and only when it starts
at the digest the previous crossing arrived at, so the atlas path cannot contain a jump
that no edge made.

It also enforces the rule the design leans on: a crossing whose head Omega differs from
the thought's head is not a station crossing of this thought at all, so it is refused as
``HEAD_CHANGE_INSIDE_ONE_THOUGHT``. A new head is a new thought with its own anchor.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT build a point from content. ``point(parse(render(R_i)))`` is the DERIVED
    tracker of LM-T2, which is NOT in this build; the point is handed in per crossing.
  * It does NOT decide a threshold. ``seams()`` and ``drift_checks()`` need theta_seam and
    theta_drift from the caller; with none supplied they refuse as
    ``SEAM_THRESHOLD_UNDECIDED`` / ``DRIFT_THRESHOLD_UNDECIDED`` rather than default.
    The frozen station-kind table has no licensed number for either.
  * It does NOT find seams across thoughts. A seam lives between two heads, and two heads
    are two thoughts with two anchors (seams.is_seam and seams.hold_together are the tools
    for that boundary; interpolating across it is refused).
  * It does NOT score anything, and it never writes the Bias substrate. The path is a log;
    the Bias is a different object (CONTINUITY.md:79-80).
  * It does NOT hold or extend an atlas. The atlas crossings are references to nodes and
    edges that live in an atlas the caller built; this module reads their leaf fields and
    never edits the atlas. It does not compute a digest either -- every digest here was
    computed by atlas.py, crossings.py, or stations.py and is copied.
  * It does NOT carry language across the atlas. Nothing in this module parses, renders,
    or moves prose. A payload stays in its node.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE ATLAS IS A MINIMAL OBJECT, NOT HELM VISION ABILITY 6 AT FULL SCOPE. NO LANGUAGE PASSED ACROSS IT.
"""

from __future__ import annotations

from dataclasses import dataclass

import crossings as crossings_module
import seams
import stations

#: Refusal codes.
NO_S0_CROSSING = "NO_S0_CROSSING"
ANCHOR_HAS_NO_POINT = "ANCHOR_HAS_NO_POINT"
NO_POINT_AT_STATION = "NO_POINT_AT_STATION"
STATION_OCCURS_MORE_THAN_ONCE = "STATION_OCCURS_MORE_THAN_ONCE"
HEAD_CHANGE_INSIDE_ONE_THOUGHT = "HEAD_CHANGE_INSIDE_ONE_THOUGHT"
BAD_DISPLACEMENT_ARGUMENT = "BAD_DISPLACEMENT_ARGUMENT"
NO_CROSSINGS = "NO_CROSSINGS"

#: Refusal codes for the atlas side (added with the atlas build).
NOT_A_CJT = "NOT_A_CJT"
ATLAS_CROSSING_OTHER_THOUGHT = "ATLAS_CROSSING_OTHER_THOUGHT"
ATLAS_PATH_BROKEN = "ATLAS_PATH_BROKEN"
ANCHOR_IS_ATLAS_DIGEST = "ANCHOR_IS_ATLAS_DIGEST"

#: The CLARIFY sentence the design pairs with a drift flag (lm_t1\\GRAMMAR_CCE_v0_1.md:105,
#: quoted at CONTINUITY.md:64).
DRIFT_CLARIFY_TEMPLATE = "Are we still on {head}?"


class ContinuityRefusal(Exception):
    """A refusal with a stable code. Nothing is filled in and nothing is guessed."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class PathPoint:
    """One point of the path: the station it was read at, the tick, its RPM depth."""

    station: str
    kind: str
    tick: int
    depth: int
    point: tuple[float, ...]

    def as_dict(self) -> dict:
        return {
            "station": self.station,
            "kind": self.kind,
            "tick": self.tick,
            "depth": self.depth,
            "point": tuple(self.point),
        }


@dataclass(frozen=True)
class SeamRecord:
    """One seam that fired, with the rule's own reason for firing."""

    from_station: str
    to_station: str
    from_tick: int
    to_tick: int
    step: float
    threshold: float
    reason: str

    def as_dict(self) -> dict:
        return {
            "from_station": self.from_station,
            "to_station": self.to_station,
            "from_tick": self.from_tick,
            "to_tick": self.to_tick,
            "step": self.step,
            "threshold": self.threshold,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SeamCheck:
    """One pair of crossings, whether it fired or not, and why."""

    from_station: str
    to_station: str
    from_tick: int
    to_tick: int
    fired: bool
    code: str
    detail: str
    reason: str

    def as_dict(self) -> dict:
        return {
            "from_station": self.from_station,
            "to_station": self.to_station,
            "from_tick": self.from_tick,
            "to_tick": self.to_tick,
            "fired": self.fired,
            "code": self.code,
            "detail": self.detail,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class DriftRecord:
    """One drift reading: reported, never scored (CONTINUITY.md:64-67)."""

    station: str
    tick: int
    step: float | None
    displacement: float
    drifting: bool
    clarify: str | None
    reason: str

    def as_dict(self) -> dict:
        return {
            "station": self.station,
            "tick": self.tick,
            "step": self.step,
            "displacement": self.displacement,
            "drifting": self.drifting,
            "clarify": self.clarify,
            "reason": self.reason,
        }


class ContinuityPath:
    """The crossings of ONE thought, in order, with the design's readings over them.

    ``head_omega`` is the thought's head. It is fixed for the life of the object: within
    one thought the head does not change (CONTINUITY.md:31-32), so a crossing that carries
    a different head is refused here. ``leading_register`` is the thought's register tag,
    used by the seam rule when there is no head.

    ``seam_threshold`` and ``drift_threshold`` are optional. If they are not supplied, the
    frozen station-kind table is consulted, finds ``None``, and the reader refuses: this
    build has no licensed threshold to use and says so instead of picking one.

    ``atlas_crossings`` is an optional sequence of ``crossings.Crossing`` objects -- the
    CJTs this thought made across atlas nodes. They are carried beside the station
    crossings and are counted separately; nothing here mixes the two lists.
    """

    def __init__(
        self,
        thought_id: str,
        head_omega: str | None,
        leading_register: str | None = None,
        seam_threshold: float | None = None,
        drift_threshold: float | None = None,
        atlas_crossings=None,
    ) -> None:
        if not isinstance(thought_id, str) or not thought_id:
            raise ContinuityRefusal("BAD_THOUGHT_ID", "thought_id must be a non-empty string")
        self.thought_id = thought_id
        self.head_omega = head_omega
        self.leading_register = leading_register
        self.seam_threshold = seam_threshold
        self.drift_threshold = drift_threshold
        self._crossings: list[stations.Crossing] = []
        self._atlas_crossings: list[crossings_module.Crossing] = []
        for crossing in atlas_crossings or ():
            self.add_atlas_crossing(crossing)

    # -- building --------------------------------------------------------- #
    def add_crossing(
        self,
        station: str,
        tick: int,
        content=None,
        point=None,
        head_omega=None,
        leading_register=None,
        depth: int = 0,
        next_pointer=None,
        atlas_entry=None,
    ):
        """Add one station crossing and return it.

        ``point`` is ``None`` where the station has a FORM gap: the crossing still exists,
        it just contributes no point, and it is counted in ``form_gaps``.

        ``atlas_entry`` binds this station to an atlas position (the mapping
        ``stations.bind_s0_to_atlas`` returns in ``.binding``). When the S0 crossing carries
        one, ``anchor()`` returns that entry's digest instead of a point.

        A ``head_omega`` different from the thought's head is refused: that crossing
        belongs to a different thought, which gets its own anchor. Passing ``head_omega``
        equal to the thought's head is allowed and is the normal case.
        """
        if head_omega is not None and head_omega != self.head_omega:
            raise ContinuityRefusal(
                HEAD_CHANGE_INSIDE_ONE_THOUGHT,
                f"crossing at {station} names head {head_omega!r} but this path's head is "
                f"{self.head_omega!r}; a new head is a new thought with its own anchor "
                f"(CONTINUITY.md:38-39), and two heads are never blended",
            )
        crossing = stations.Crossing(
            thought_id=self.thought_id,
            station=station,
            tick=tick,
            head_omega=self.head_omega,
            leading_register=self.leading_register if leading_register is None else leading_register,
            content={} if content is None else content,
            point=point,
            depth=depth,
            next_pointer=next_pointer,
            atlas_entry=atlas_entry,
        )
        self._crossings.append(crossing)
        return crossing

    # -- the atlas crossings (the CJTs) ------------------------------------ #
    def add_atlas_crossing(self, crossing):
        """Add one ``crossings.Crossing`` -- a CJT -- and return it.

        Three refusals, and no repair:

          * ``NOT_A_CJT`` -- the object is not a Crossing. ``crossings.is_cjt`` is the only
            test used, so a node, an edge, a dict, or a station crossing cannot slip in
            here by carrying fields that look right;
          * ``ATLAS_CROSSING_OTHER_THOUGHT`` -- the crossing names another thought;
          * ``ATLAS_PATH_BROKEN`` -- the crossing does not start where the previous one
            arrived, so the path would contain a jump that no edge made.
        """
        if not crossings_module.is_cjt(crossing):
            raise ContinuityRefusal(
                NOT_A_CJT,
                f"{type(crossing).__name__} is not a Crossing; a CJT is the crossing, not "
                f"the node, the edge, or a record that carries their names",
            )
        if crossing.thought_id is not None and crossing.thought_id != self.thought_id:
            raise ContinuityRefusal(
                ATLAS_CROSSING_OTHER_THOUGHT,
                f"crossing at tick {crossing.tick} names thought {crossing.thought_id!r} "
                f"but this path is thought {self.thought_id!r}",
            )
        if self._atlas_crossings:
            previous = self._atlas_crossings[-1]
            if previous.to_digest != crossing.from_digest:
                raise ContinuityRefusal(
                    ATLAS_PATH_BROKEN,
                    f"the crossing at tick {crossing.tick} starts at node digest "
                    f"{crossing.from_digest[:16]}... but the previous crossing arrived at "
                    f"{previous.to_digest[:16]}...; a path across the atlas is made of "
                    f"crossings that join end to end",
                )
        self._atlas_crossings.append(crossing)
        return crossing

    @property
    def atlas_crossings(self) -> tuple:
        """The atlas crossings (CJTs) of this thought, in the order they were added."""
        return tuple(self._atlas_crossings)

    def atlas_path(self) -> tuple:
        """The ordered node digests this thought visited across the atlas.

        One digest per node: the first crossing's start node, then the arrival node of every
        crossing in order. Empty when no atlas crossing was added. The digests were computed
        by atlas.py; none is computed here.
        """
        if not self._atlas_crossings:
            return ()
        visited = [self._atlas_crossings[0].from_digest]
        visited.extend(crossing.to_digest for crossing in self._atlas_crossings)
        return tuple(visited)

    def atlas_kind_pollution(self) -> int:
        """How many accepted crossings joined two different kinds without a declaration.

        Zero for any path this module accepts, by construction: ``crossings.cross`` refuses
        an undeclared cross-kind crossing, so it can never be added here. The count is
        computed anyway, from the records held, so the report says what the record says
        instead of restating a rule.
        """
        return sum(
            1
            for crossing in self._atlas_crossings
            if crossing.joins_different_kinds and not crossing.cross_kind_declared
        )

    # -- what the design asks for ----------------------------------------- #
    @property
    def crossings(self) -> tuple:
        """The crossings, in the order they were added."""
        return tuple(self._crossings)

    @property
    def _point_records(self) -> tuple:
        """One PathPoint per crossing that HAS a point. FORM gaps contribute none."""
        return tuple(
            PathPoint(
                station=crossing.station,
                kind=crossing.kind,
                tick=crossing.tick,
                depth=crossing.depth,
                point=crossing.point,
            )
            for crossing in self._crossings
            if crossing.point is not None
        )

    def points(self) -> tuple:
        """One point per station crossing that HAS a point (CONTINUITY.md:24-26).

        A station with a FORM gap contributes no point here; it is counted in
        ``form_gaps`` instead. The order is the order the crossings were added.
        """
        return self._point_records

    @property
    def form_gaps(self) -> int:
        """How many crossings contributed no point, because their station has a FORM gap."""
        return sum(1 for crossing in self._crossings if crossing.point is None)

    @property
    def nested_depth_max(self) -> int:
        """The deepest RPM level any crossing of this thought reached (0 for a flat path)."""
        return max((crossing.depth for crossing in self._crossings), default=0)

    def _s0_crossings(self) -> list:
        return [crossing for crossing in self._crossings if crossing.station == "S0"]

    def anchor(self):
        """The anchor of this thought (CONTINUITY.md:29). Never averaged.

        Two sorts, and the path never leaves the caller guessing which:

          * when the S0 crossing carries an atlas position, the anchor is that entry's
            DIGEST, a 64-character sha256 string. That is the owner's lifted restriction:
            S0 is a position in the atlas, not only the head of a tree
            (OWNER_RULING_RPA_ATLAS_20261015.md:16-18);
          * otherwise the anchor is the S0 point, exactly as this build behaved before the
            atlas existed, so every earlier caller keeps working unchanged.
        """
        if not self._crossings:
            raise ContinuityRefusal(NO_CROSSINGS, "this path has no crossings, so it has no anchor")
        s0 = self._s0_crossings()
        if not s0:
            raise ContinuityRefusal(
                NO_S0_CROSSING, "a thought is S0 -> S1 -> ... -> S6; no S0 crossing exists here"
            )
        if s0[0].atlas_entry is not None:
            return s0[0].atlas_entry["entry_digest"]
        if s0[0].point is None:
            # UNDECIDED IN DESIGN: what the anchor is when the S0 tap has no point (a FORM gap at the head) -- "Anchor of a thought = its S0 point" (CONTINUITY.md:29) does not cover that case, so this build refuses instead of choosing a fallback.
            raise ContinuityRefusal(
                ANCHOR_HAS_NO_POINT,
                "the S0 crossing carries no point (its station has a FORM gap), and the design "
                "says the anchor IS the S0 point, so there is no anchor to measure from",
            )
        return s0[0].point

    def anchor_is_atlas_digest(self) -> bool:
        """True when the anchor is an atlas entry digest rather than a point.

        A predicate, so it answers for a path with no S0 crossing at all instead of raising:
        that case is ``False`` here, and ``anchor()`` is where a missing anchor is refused.
        """
        s0 = self._s0_crossings()
        return bool(s0) and s0[0].atlas_entry is not None

    def _anchor_point(self):
        """The anchor as a point, or a refusal: a digest is not a point and is not one."""
        anchor = self.anchor()
        if isinstance(anchor, str):
            raise ContinuityRefusal(
                ANCHOR_IS_ATLAS_DIGEST,
                "the anchor is an atlas entry digest, not a point of the simplex; a distance "
                "from it would be a number nobody measured, so this build refuses instead of "
                "inventing one",
            )
        return anchor

    def _pick(self, which):
        """A crossing by index (int) or by station code (str), refusing ambiguity."""
        if isinstance(which, bool):
            raise ContinuityRefusal(BAD_DISPLACEMENT_ARGUMENT, "a station or an index is required")
        if isinstance(which, int):
            if not 0 <= which < len(self._crossings):
                raise ContinuityRefusal(
                    BAD_DISPLACEMENT_ARGUMENT,
                    f"crossing index {which} is outside 0..{len(self._crossings) - 1}",
                )
            return self._crossings[which]
        if isinstance(which, str):
            found = [crossing for crossing in self._crossings if crossing.station == which]
            if not found:
                raise ContinuityRefusal(
                    stations.UNKNOWN_STATION if which not in stations.STATION_ORDINALS else NO_CROSSINGS,
                    f"no crossing at station {which!r} on this path",
                )
            if len(found) > 1:
                # UNDECIDED IN DESIGN: how a crossing is addressed when the same station code occurs twice (a nested level inside S5, or the other route of an ALT order) -- the packet gives no addressing scheme, so this build refuses the ambiguous name and asks for an index.
                raise ContinuityRefusal(
                    STATION_OCCURS_MORE_THAN_ONCE,
                    f"station {which!r} occurs {len(found)} times on this path; pass a crossing "
                    f"index instead of a station code",
                )
            return found[0]
        raise ContinuityRefusal(
            BAD_DISPLACEMENT_ARGUMENT,
            f"{which!r} is neither a station code nor a crossing index",
        )

    def displacement(self, which) -> float:
        """The distance from the anchor to the point at ``which`` (a station code or index).

        ``which`` may be a station code ("S3") when that station occurs once on the path, or
        a crossing index. A crossing with no point has nothing to measure, and is refused as
        ``NO_POINT_AT_STATION`` rather than reported as zero. When the anchor is an atlas
        entry digest the measurement is refused as ``ANCHOR_IS_ATLAS_DIGEST``: a distance
        from a digest to a point is not a number this build will invent.
        """
        anchor = self._anchor_point()
        crossing = self._pick(which)
        if crossing.point is None:
            raise ContinuityRefusal(
                NO_POINT_AT_STATION,
                f"station {crossing.station} at tick {crossing.tick} has no point (FORM gap); "
                f"nothing can be measured from the anchor to it",
            )
        return seams.step_size(anchor, crossing.point)

    # -- seams ------------------------------------------------------------ #
    def _require_seam_threshold(self) -> float:
        threshold = self.seam_threshold
        if threshold is None:
            threshold = stations.threshold_of(self._crossings[0].station if self._crossings else "S0", "seam")
        return seams.require_threshold(threshold, "seam")

    def seam_checks(self) -> tuple:
        """Every neighbouring pair, fired or not, with the rule's reason for each.

        This is where the design's statement shows itself: within one thought the head does
        not change, so condition (a) of the rule cannot be met and no pair fires, however
        large the step. The step sizes are still measured and reported -- they are the
        restlessness of the path (CONTINUITY.md:32-33).
        """
        threshold = self._require_seam_threshold()
        checks = []
        for previous, current in zip(self._crossings, self._crossings[1:]):
            fired, reason = seams.is_seam(previous, current, threshold)
            code, detail = seams.decode_reason(reason)
            checks.append(
                SeamCheck(
                    from_station=previous.station,
                    to_station=current.station,
                    from_tick=previous.tick,
                    to_tick=current.tick,
                    fired=fired,
                    code=code,
                    detail=detail,
                    reason=reason,
                )
            )
        return tuple(checks)

    def seams(self) -> tuple:
        """The seams found on this path, each with its reason.

        Within one thought this is empty by rule (CONTINUITY.md:31-32): station crossings can
        never be seams, because the head does not change inside a thought. A seam is found
        between two heads, which is a boundary between two thoughts -- see
        ``seams.is_seam`` for that comparison.
        """
        threshold = self._require_seam_threshold()
        found = []
        for previous, current in zip(self._crossings, self._crossings[1:]):
            fired, reason = seams.is_seam(previous, current, threshold)
            if not fired:
                continue
            step = None
            if previous.point is not None and current.point is not None:
                step = seams.step_size(previous.point, current.point)
            found.append(
                SeamRecord(
                    from_station=previous.station,
                    to_station=current.station,
                    from_tick=previous.tick,
                    to_tick=current.tick,
                    step=step,
                    threshold=threshold,
                    reason=reason,
                )
            )
        return tuple(found)
    # -- drift (reported, never scored) ----------------------------------- #
    def drift_checks(self) -> tuple:
        """The station-level drift reading of CONTINUITY.md:60-67, one record per crossing.

        Drift is flagged when the displacement D_t from the anchor reaches theta_drift while
        every step since the anchor stayed below theta_seam. Both thresholds come from the
        caller; the frozen table has neither. The reading is reported with the depth beside
        it and is never scored in the first test (CONTINUITY.md:64-67).

        Refused as ``ANCHOR_IS_ATLAS_DIGEST`` when S0 is bound to an atlas entry, because
        a displacement is measured from a point and a digest is not one.
        """
        if self.drift_threshold is None:
            raise seams.SeamRefusal(
                "DRIFT_THRESHOLD_UNDECIDED",
                "no drift threshold was supplied; CONTINUITY.md:35-37 leaves the per-station-kind "
                "drift threshold undecided, so this build refuses instead of inventing one",
            )
        seam_threshold = self._require_seam_threshold()
        drift_threshold = seams.require_threshold(self.drift_threshold, "drift")
        anchor = self._anchor_point()
        records = []
        steps: list[float] = []
        for previous, current in zip(self._crossings, self._crossings[1:]):
            pair_step = None
            if previous.point is not None and current.point is not None:
                pair_step = seams.step_size(previous.point, current.point)
                steps.append(pair_step)
            if current.point is None:
                continue
            displacement = seams.step_size(anchor, current.point)
            step_max = max(steps) if steps else 0.0
            drifting = displacement >= drift_threshold and step_max < seam_threshold
            records.append(
                DriftRecord(
                    station=current.station,
                    tick=current.tick,
                    step=pair_step,
                    displacement=displacement,
                    drifting=drifting,
                    clarify=DRIFT_CLARIFY_TEMPLATE.format(head=self.head_omega) if drifting else None,
                    reason=(
                        f"displacement {displacement:.9f} {'>=' if displacement >= drift_threshold else '<'} "
                        f"drift threshold {drift_threshold:.9f}; largest step since the anchor "
                        f"{step_max:.9f} {'<' if step_max < seam_threshold else '>='} seam threshold "
                        f"{seam_threshold:.9f}"
                    ),
                )
            )
        return tuple(records)

    # -- the counts ------------------------------------------------------- #
    def summary(self) -> dict:
        """The counts: station crossings, points, form gaps, seams, and the atlas counts.

        ``seams`` is ``0`` when a threshold was supplied and none fired. When no threshold is
        available it is ``None`` with ``seams_status = THRESHOLD_UNDECIDED``, because this
        build will not report a count it cannot compute.

        The three atlas counts were added with the atlas build, and each says something
        narrow and checkable:

          * ``atlas_nodes_visited`` -- how many distinct node digests this thought's atlas
            path touched;
          * ``atlas_edges_crossed`` -- how many CJT crossings were made;
          * ``atlas_kind_pollution`` -- how many of those crossings joined two different
            kinds without a declaration. It is ``0`` for every path this build accepts, and
            the test file proves that on a real path rather than trusting the sentence.
        """
        crossings = len(self._crossings)
        points = sum(1 for crossing in self._crossings if crossing.point is not None)
        if self.seam_threshold is None:
            seam_count = None
            seams_status = stations.THRESHOLD_UNDECIDED
        else:
            seam_count = len(self.seams())
            seams_status = stations.THRESHOLD_CALIBRATED
        path = self.atlas_path()
        return {
            "thought_id": self.thought_id,
            "head_omega": self.head_omega,
            "crossings": crossings,
            "points": points,
            "form_gaps": self.form_gaps,
            "seams": seam_count,
            "seams_status": seams_status,
            "nested_depth_max": self.nested_depth_max,
            "stations": tuple(crossing.station for crossing in self._crossings),
            "atlas_crossings": len(self._atlas_crossings),
            "atlas_nodes_visited": len(set(path)),
            "atlas_edges_crossed": len(self._atlas_crossings),
            "atlas_kind_pollution": self.atlas_kind_pollution(),
            "atlas_cross_kind_declared": sum(
                1
                for crossing in self._atlas_crossings
                if crossing.joins_different_kinds and crossing.cross_kind_declared
            ),
            "anchor_is_atlas_digest": self.anchor_is_atlas_digest(),
        }


def continuity_summary(path) -> dict:
    """The counts of one path: ``path.summary()``, under the name the build reports them by.

    A thin reader on purpose. It computes nothing itself, so there is one place -- the
    path -- where a count can be wrong.
    """
    if not isinstance(path, ContinuityPath):
        raise ContinuityRefusal(
            "NOT_A_PATH", f"continuity_summary needs a ContinuityPath, got {type(path).__name__}"
        )
    return path.summary()
