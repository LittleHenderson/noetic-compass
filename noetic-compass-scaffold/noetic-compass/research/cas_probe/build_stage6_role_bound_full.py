"""Build the Stage 6 full role-bound noetic counterfactual fixture.

This is the scaled fixture from STAGE6_ROUNDTABLE_V3_PLAN_20260516.md:

    60 lexical contrast bundles
    5 hard noetic pairs per bundle
    2 focused roles per pair
    4 core paraphrase families for every split
    3 extra locked-test-only paraphrase families

Total:
    train: 30 bundles * 5 * 2 * 4 = 1,200 rows
    val:   10 bundles * 5 * 2 * 4 =   400 rows
    test:  20 bundles * 5 * 2 * 7 = 1,400 rows
    all:                                      3,000 rows

This script only builds a locked fixture. It does not capture activations,
train probes, or support a scientific claim by itself.

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/build_stage6_role_bound_full.py
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_DATE = "20260516"
_OUT_JSONL = _HERE / f"stage6_role_bound_full_{_DATE}.jsonl"
_OUT_MANIFEST = _HERE / f"stage6_role_bound_full_manifest_{_DATE}.json"

_NOETIC_NAMES = {
    0: "Idea",
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
}

_PAIR_ORDER = ("0_1", "2_3", "4_7", "5_6", "8_9")
_PAIR_META = {
    "0_1": {
        "labels": (0, 1),
        "roles": {
            0: "object_content",
            1: "active_processing",
        },
    },
    "2_3": {
        "labels": (2, 3),
        "roles": {
            2: "toward_vector",
            3: "away_vector",
        },
    },
    "4_7": {
        "labels": (4, 7),
        "roles": {
            4: "impression_strength",
            7: "repeated_cadence",
        },
    },
    "5_6": {
        "labels": (5, 6),
        "roles": {
            5: "carrier_shaped_by_received_contents",
            6: "construct_made_of_inner_parts",
        },
    },
    "8_9": {
        "labels": (8, 9),
        "roles": {
            8: "source_cue",
            9: "resulting_content",
        },
    },
}

_CORE_FAMILIES = (
    "role_inverse_minimal",
    "no_alias_plain",
    "concrete_human",
    "system_process",
)
_TEST_ONLY_FAMILIES = (
    "compressed_minimal",
    "long_embedded_clause",
    "counter_alias_hard_negative",
)

_BUNDLE_FIELDS = (
    "slug",
    "split",
    "object",
    "processor",
    "toward",
    "away",
    "impression",
    "cadence",
    "carrier",
    "prior",
    "construct",
    "parts",
    "cue",
    "result",
)

_BUNDLE_SPECS = [
    ("expense_audit", "train", "expense report", "auditor", "verified receipt trail", "missing receipt gap", "flagged ledger row", "monthly close pass", "finance desk", "vendor history", "reimbursement package", "claim, receipt, approval, and payout", "audit notice", "review workflow"),
    ("garden_irrigation", "train", "garden bed", "grower", "steady drip line", "dry soil patch", "wilting leaf cluster", "dawn watering pass", "greenhouse crew", "seasonal notes", "irrigation plan", "sensor, valve, hose, and timer", "soil meter", "watering routine"),
    ("library_archive", "train", "archive folder", "librarian", "clear catalog entry", "misfiled shelf slot", "faded margin mark", "weekly sorting pass", "records room", "old accession logs", "index card", "title, date, author, and shelf", "call slip", "retrieval route"),
    ("warehouse_pick", "train", "shipping order", "picker", "matching bin code", "wrong pallet lane", "flashing scanner alert", "shift scan cycle", "floor team", "previous inventory counts", "packing ticket", "aisle, bin, quantity, and box", "barcode beep", "pick path"),
    ("city_crosswalk", "train", "crosswalk request", "planner", "safer walking route", "blind corner", "near miss report", "traffic survey pass", "street office", "older crash notes", "street revision", "paint, sign, signal, and curb", "resident letter", "safety review"),
    ("satellite_relay", "train", "satellite relay task", "mission controller", "stable downlink", "dropped packet window", "signal spike", "orbit check cycle", "ground station", "prior pass logs", "relay schedule", "antenna, window, channel, and handoff", "telemetry ping", "contact sequence"),
    ("robot_arm", "train", "robot arm move", "calibration tech", "clean gripper path", "joint wobble", "servo buzz", "bench test loop", "automation cell", "factory trials", "motion recipe", "pose, grip, release, and reset", "alignment mark", "pick motion"),
    ("climate_brief", "train", "climate brief", "analyst", "transparent uncertainty note", "overstated risk chart", "heat anomaly map", "seasonal review pass", "research team", "station records", "forecast summary", "data, range, caveat, and action", "temperature spike", "risk memo"),
    ("loan_review", "train", "loan file", "underwriter", "complete income proof", "thin documentation", "late payment marker", "weekly approval queue", "credit desk", "payment records", "lending package", "income, debt, collateral, and term", "score alert", "review checklist"),
    ("language_lesson", "train", "grammar exercise", "tutor", "clear sentence pattern", "awkward phrasing", "student pause", "evening drill set", "learning table", "prior worksheets", "lesson segment", "word, tense, phrase, and correction", "example prompt", "practice response"),
    ("theater_rehearsal", "train", "stage cue", "director", "clean entrance", "missed line", "spotlight flash", "rehearsal run", "cast member", "script notes", "scene plan", "line, gesture, prop, and exit", "stage bell", "blocking move"),
    ("game_tutorial", "train", "tutorial step", "designer", "clear player choice", "confusing menu", "first failure screen", "playtest loop", "design squad", "session notes", "onboarding flow", "prompt, input, reward, and retry", "hint popup", "skill unlock"),
    ("museum_catalog", "train", "artifact record", "curator", "accurate period note", "wrong display case", "patina detail", "exhibit rotation", "collection office", "donor records", "gallery card", "origin, material, date, and placement", "inventory tag", "display plan"),
    ("security_incident", "train", "access event", "responder", "confirmed login trail", "unknown device entry", "red console alert", "hourly watch pass", "security desk", "badge history", "incident packet", "account, device, time, and action", "monitor alarm", "containment task"),
    ("search_result", "train", "search query", "ranker", "relevant source page", "spam result", "click surge", "index refresh loop", "retrieval service", "query logs", "ranking plan", "terms, source, score, and snippet", "user click", "result list"),
    ("flight_checklist", "train", "takeoff checklist", "pilot", "verified runway clearance", "instrument mismatch", "warning tone", "preflight pass", "cockpit crew", "maintenance sheet", "departure routine", "fuel, flaps, weather, and clearance", "tower call", "runway decision"),
    ("construction_site", "train", "site inspection", "foreman", "stable scaffold", "loose rail", "cracked support mark", "morning walk pass", "build crew", "permit notes", "work order", "frame, brace, crew, and check", "safety call", "repair queue"),
    ("supply_chain", "train", "supplier quote", "buyer", "reliable delivery window", "uncertain lead time", "price jump notice", "weekly sourcing pass", "procurement team", "vendor memory", "purchase plan", "quote, sample, contract, and delivery", "stock alert", "order change"),
    ("lab_trial", "train", "sample batch", "chemist", "clean assay reading", "contaminated vial", "color shift", "timed lab cycle", "bench team", "protocol notes", "experiment setup", "sample, reagent, control, and measure", "timer chime", "assay step"),
    ("emergency_drill", "train", "evacuation drill", "coordinator", "clear exit route", "blocked stairwell", "alarm pulse", "annual drill pass", "response team", "site maps", "drill script", "room, route, role, and count", "alarm bell", "movement plan"),
    ("court_filing", "train", "court filing", "clerk", "complete docket entry", "missing exhibit", "stamp mark", "filing calendar pass", "records counter", "case history", "submission packet", "motion, exhibit, signature, and date", "filing receipt", "docket update"),
    ("hiring_review", "train", "candidate packet", "recruiter", "strong work sample", "unclear reference", "portfolio highlight", "interview round", "hiring panel", "prior screening notes", "selection brief", "resume, sample, interview, and followup", "calendar invite", "interview plan"),
    ("elder_care", "train", "care note", "nurse", "timely medication plan", "missed dosage risk", "patient grimace", "rounding interval", "care team", "health history", "support plan", "symptom, dose, meal, and rest", "bedside call", "care response"),
    ("therapy_note", "train", "session note", "counselor", "steady coping step", "rumination spiral", "quiet tear", "weekly meeting pass", "therapy office", "past journal entries", "support frame", "feeling, story, practice, and check-in", "memory cue", "coping exercise"),
    ("architecture_brief", "train", "floor plan", "architect", "sunlit courtyard", "narrow corridor", "shadow pattern", "design review loop", "studio group", "site survey", "building concept", "room, path, light, and material", "client note", "layout revision"),
    ("network_routing", "train", "routing table", "engineer", "stable packet path", "packet loss window", "latency spike", "monitoring cycle", "network team", "outage notes", "routing change", "prefix, gateway, metric, and failover", "health probe", "traffic shift"),
    ("battery_design", "train", "battery cell", "materials lead", "longer charge hold", "thermal runaway risk", "heat mark", "cycle test run", "lab group", "aging data", "cell design", "anode, cathode, separator, and case", "voltage dip", "design change"),
    ("peer_review", "train", "paper draft", "reviewer", "clear method section", "unsupported conclusion", "margin note", "revision cycle", "journal desk", "literature notes", "review letter", "claim, method, result, and limit", "citation gap", "revision request"),
    ("grant_proposal", "train", "grant proposal", "program officer", "focused public benefit", "vague budget line", "impact chart", "panel review pass", "funding office", "past award notes", "proposal package", "goal, method, budget, and milestone", "scoring sheet", "funding decision"),
    ("call_center", "train", "support call", "agent", "clear refund path", "angry hold loop", "raised voice", "ticket review pass", "support desk", "customer history", "service script", "issue, policy, option, and close", "account lookup", "case resolution"),
    ("food_safety", "val", "kitchen report", "inspector", "clean storage practice", "expired ingredient bin", "sour odor", "inspection pass", "health office", "prior visit notes", "correction notice", "temperature, storage, cleaning, and record", "fridge reading", "compliance step"),
    ("water_utility", "val", "water sample", "technician", "clear quality reading", "cloudy tap complaint", "chlorine smell", "daily test pass", "utility lab", "pipe records", "testing sheet", "sample, meter, threshold, and notice", "sensor reading", "maintenance visit"),
    ("school_schedule", "val", "class schedule", "administrator", "balanced room assignment", "overcrowded period", "bell change", "semester planning pass", "school office", "past attendance files", "schedule grid", "teacher, room, time, and roster", "enrollment notice", "room change"),
    ("claims_adjustment", "val", "insurance claim", "adjuster", "verified repair estimate", "inflated damage note", "photo detail", "weekly claims queue", "review desk", "policy history", "settlement packet", "damage, coverage, estimate, and payment", "claim photo", "settlement path"),
    ("translation_review", "val", "translated paragraph", "editor", "faithful wording", "awkward idiom", "reader pause", "draft review loop", "language team", "style guide", "revision note", "sentence, idiom, tone, and check", "glossary hint", "wording choice"),
    ("sports_training", "val", "drill routine", "coach", "balanced footwork", "sloppy turn", "whistle blast", "practice rotation", "training group", "match tape", "workout plan", "warmup, drill, rest, and replay", "whistle cue", "movement pattern"),
    ("market_research", "val", "survey response", "researcher", "clear buying reason", "confusing sample skew", "trend spike", "weekly panel read", "insight team", "prior survey waves", "market note", "question, segment, rating, and quote", "dashboard flag", "consumer insight"),
    ("tax_return", "val", "tax return", "preparer", "complete deduction record", "unverified expense line", "audit stamp", "filing season cycle", "tax office", "receipt folder", "return package", "income, deduction, credit, and signature", "form notice", "filing check"),
    ("park_maintenance", "val", "park work order", "maintenance lead", "safe playground repair", "rusted swing chain", "broken latch mark", "weekly grounds pass", "parks crew", "inspection notes", "repair plan", "part, tool, crew, and signoff", "visitor report", "fix schedule"),
    ("newsroom_edit", "val", "news article", "editor", "verified interview quote", "rumor paragraph", "headline jolt", "daily edit pass", "news desk", "source notes", "story package", "lead, quote, context, and correction", "tip email", "publish decision"),
    ("patient_triage", "test", "triage note", "clinician", "urgent treatment path", "dismissed symptom", "pain score jump", "shift handoff", "medical team", "chart history", "care decision", "symptom, sign, risk, and next step", "vital reading", "priority action"),
    ("disaster_relief", "test", "relief request", "coordinator", "available shelter route", "damaged access road", "flood marker", "field update cycle", "relief desk", "local reports", "aid plan", "need, supply, route, and team", "radio call", "delivery task"),
    ("energy_grid", "test", "grid alert", "dispatcher", "stable load transfer", "overheated line", "frequency wobble", "control room sweep", "grid crew", "load records", "switching plan", "station, feeder, load, and reserve", "meter alarm", "power reroute"),
    ("privacy_review", "test", "privacy request", "officer", "clear consent record", "hidden data sharing", "complaint notice", "monthly review queue", "privacy desk", "access history", "disclosure plan", "request, consent, data, and deletion", "user appeal", "privacy action"),
    ("wildfire_watch", "test", "fire watch report", "ranger", "clear containment route", "dry ridge hazard", "smoke plume", "hourly patrol pass", "forest crew", "weather logs", "response plan", "wind, fuel, crew, and boundary", "lookout call", "containment move"),
    ("farming_plan", "test", "crop plan", "farmer", "healthy seed choice", "pest damage risk", "leaf spot", "seasonal planting pass", "field crew", "soil history", "field schedule", "seed, water, nutrient, and harvest", "rain gauge", "planting adjustment"),
    ("child_tutoring", "test", "reading passage", "tutor", "confident word decoding", "frustration pause", "bright smile", "after-school practice", "learning coach", "reading log", "skill plan", "letter, sound, word, and story", "page prompt", "reading response"),
    ("forensics_lab", "test", "evidence sample", "technician", "clean chain record", "unsealed bag", "trace mark", "lab intake cycle", "forensics unit", "case notes", "sample process", "container, swab, test, and report", "case tag", "lab finding"),
    ("restaurant_service", "test", "dinner order", "server", "timely table service", "wrong plate", "guest frown", "table check loop", "dining crew", "reservation notes", "service flow", "order, kitchen, table, and bill", "ticket print", "service recovery"),
    ("mobile_app", "test", "login screen", "developer", "simple sign-in flow", "crash screen", "spinner delay", "sprint review pass", "app team", "bug history", "release plan", "input, session, error, and fix", "error report", "patch task"),
    ("public_transit", "test", "bus route", "dispatcher", "reliable transfer window", "missed connection", "crowd surge", "service review loop", "transit office", "ridership notes", "route update", "stop, vehicle, interval, and notice", "driver report", "schedule change"),
    ("wildlife_study", "test", "nest survey", "biologist", "clear migration clue", "disturbed habitat", "unusual call", "field visit cycle", "study crew", "species records", "study protocol", "site, count, photo, and note", "trail camera", "survey finding"),
    ("procurement_bid", "test", "bid package", "buyer", "transparent scoring method", "conflict concern", "price variance", "review board cycle", "procurement office", "supplier history", "award plan", "requirement, bid, score, and award", "bid question", "award recommendation"),
    ("housing_case", "test", "housing application", "case worker", "available unit match", "missing document", "urgent voicemail", "weekly intake pass", "housing office", "tenant history", "placement plan", "income, need, unit, and lease", "eligibility notice", "placement step"),
    ("ocean_survey", "test", "reef survey", "marine scientist", "healthy coral zone", "bleached reef patch", "color change", "dive transect pass", "field vessel", "reef records", "survey map", "site, depth, photo, and sample", "dive marker", "reef assessment"),
    ("hardware_repair", "test", "laptop repair", "technician", "working display cable", "loose connector", "flicker pattern", "bench repair loop", "repair shop", "service history", "repair ticket", "case, cable, board, and test", "boot chime", "repair action"),
    ("training_manual", "test", "manual section", "trainer", "clear safety step", "skipped warning", "trainee hesitation", "course review pass", "training office", "incident notes", "lesson page", "task, hazard, step, and check", "quiz prompt", "training correction"),
    ("warehouse_forecast", "test", "demand forecast", "planner", "steady stock target", "overstock risk", "sales spike", "planning cycle", "inventory group", "seasonal orders", "forecast plan", "history, demand, stock, and order", "sales alert", "reorder move"),
    ("vehicle_recall", "test", "recall notice", "safety engineer", "confirmed defect pattern", "ignored complaint", "dashboard light", "review board pass", "vehicle team", "warranty records", "recall plan", "symptom, part, owner, and fix", "service bulletin", "repair instruction"),
    ("youth_program", "test", "mentoring session", "program lead", "encouraging project goal", "discouraging peer conflict", "student grin", "weekly meetup", "youth staff", "attendance notes", "activity plan", "mentor, task, reflection, and share", "project prompt", "growth activity"),
]


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _bundles() -> list[dict[str, str]]:
    bundles: list[dict[str, str]] = []
    for index, spec in enumerate(_BUNDLE_SPECS, start=1):
        item = dict(zip(_BUNDLE_FIELDS, spec, strict=True))
        item["id"] = f"bundle{index:03d}_{item['slug']}"
        item["lexical_pack_id"] = f"stage6_full_pack_{index:03d}_{item['slug']}"
        bundles.append(item)
    return bundles


def _role_text(pair_key: str, bundle: dict[str, str], family: str) -> tuple[str, str]:
    if pair_key == "0_1":
        variants = {
            "role_inverse_minimal": (
                f"A is the {bundle['object']} inside the {bundle['construct']}",
                f"B is the {bundle['processor']} holding and comparing that item against {bundle['prior']}",
            ),
            "no_alias_plain": (
                f"A marks the {bundle['object']} currently under review",
                f"B keeps the item available while the {bundle['processor']} checks {bundle['parts']}",
            ),
            "concrete_human": (
                f"A is the {bundle['object']} placed before the {bundle['processor']}",
                f"B is the working attention that keeps the item active through {bundle['construct']}",
            ),
            "system_process": (
                f"A supplies the current input for the {bundle['construct']}",
                f"B runs the comparison pass using {bundle['prior']} and {bundle['parts']}",
            ),
            "compressed_minimal": (
                f"A is the {bundle['object']}",
                f"B handles that item through the {bundle['construct']}",
            ),
            "long_embedded_clause": (
                f"A remains the {bundle['object']} being examined while {bundle['prior']} frames the case",
                f"B is the {bundle['processor']}'s active handling of that item across {bundle['parts']}",
            ),
            "counter_alias_hard_negative": (
                f"A is not the worker; A is the {bundle['object']} inside the task",
                f"B is not the object; B keeps and compares it during the {bundle['construct']}",
            ),
        }
    elif pair_key == "2_3":
        variants = {
            "role_inverse_minimal": (
                f"A draws the agent toward {bundle['toward']} for the {bundle['object']}",
                f"B makes the agent pull back from {bundle['away']} during the same task",
            ),
            "no_alias_plain": (
                f"A favors the route with {bundle['toward']}",
                f"B rejects the route with {bundle['away']}",
            ),
            "concrete_human": (
                f"A feels like the useful path because it offers {bundle['toward']}",
                f"B feels like the path to avoid because it carries {bundle['away']}",
            ),
            "system_process": (
                f"A raises the score for {bundle['toward']} in the {bundle['construct']}",
                f"B lowers the score for {bundle['away']} in that same evaluation",
            ),
            "compressed_minimal": (
                f"A moves toward {bundle['toward']}",
                f"B moves away from {bundle['away']}",
            ),
            "long_embedded_clause": (
                f"A becomes the preferred pull when the {bundle['processor']} sees {bundle['toward']} in the case",
                f"B becomes the refusal point when the same case shows {bundle['away']}",
            ),
            "counter_alias_hard_negative": (
                f"A accepts a path that contains relief from {bundle['away']} and leads to {bundle['toward']}",
                f"B refuses a path that loses {bundle['toward']} and exposes {bundle['away']}",
            ),
        }
    elif pair_key == "4_7":
        variants = {
            "role_inverse_minimal": (
                f"A hits the {bundle['processor']} with the force of the {bundle['impression']}",
                f"B returns through the pattern of the {bundle['cadence']}",
            ),
            "no_alias_plain": (
                f"A is the strong felt mark left by the {bundle['impression']}",
                f"B is the repeated schedule carried by the {bundle['cadence']}",
            ),
            "concrete_human": (
                f"A is the moment that stands out when the {bundle['impression']} lands",
                f"B is the practice pattern that keeps coming back as the {bundle['cadence']}",
            ),
            "system_process": (
                f"A registers a strong signal from the {bundle['impression']}",
                f"B sequences the next pass using the {bundle['cadence']}",
            ),
            "compressed_minimal": (
                f"A is the strong mark from the {bundle['impression']}",
                f"B is the repeated pass of the {bundle['cadence']}",
            ),
            "long_embedded_clause": (
                f"A is what remains intense after the {bundle['impression']} cuts through the surrounding details",
                f"B is what organizes the recurring pass of the {bundle['cadence']} over time",
            ),
            "counter_alias_hard_negative": (
                f"A is not the schedule; A is the standout force from the {bundle['impression']}",
                f"B is not the one-time mark; B is the returning pattern of the {bundle['cadence']}",
            ),
        }
    elif pair_key == "5_6":
        variants = {
            "role_inverse_minimal": (
                f"A is the {bundle['carrier']} shaped by {bundle['prior']}",
                f"B is the {bundle['construct']} built from {bundle['parts']}",
            ),
            "no_alias_plain": (
                f"A carries a history formed by {bundle['prior']}",
                f"B is an assembled plan made from {bundle['parts']}",
            ),
            "concrete_human": (
                f"A is the holder changed by earlier material from {bundle['prior']}",
                f"B is the thing being made out of {bundle['parts']}",
            ),
            "system_process": (
                f"A stores what the {bundle['carrier']} has received from {bundle['prior']}",
                f"B decomposes the {bundle['construct']} into {bundle['parts']}",
            ),
            "compressed_minimal": (
                f"A is the holder shaped by {bundle['prior']}",
                f"B is the build made from {bundle['parts']}",
            ),
            "long_embedded_clause": (
                f"A is the carrying side that already contains material from {bundle['prior']} before the task begins",
                f"B is the constructed side whose internal makeup is {bundle['parts']}",
            ),
            "counter_alias_hard_negative": (
                f"A is not the inner breakdown; A is the {bundle['carrier']} changed by received material",
                f"B is not the holder; B is the {bundle['construct']} assembled from its parts",
            ),
        }
    elif pair_key == "8_9":
        variants = {
            "role_inverse_minimal": (
                f"A is the {bundle['cue']} that brings up B",
                f"B is the {bundle['result']} brought up by A",
            ),
            "no_alias_plain": (
                f"A starts the recall chain through the {bundle['cue']}",
                f"B is what appears as the {bundle['result']}",
            ),
            "concrete_human": (
                f"A is the sign noticed first: the {bundle['cue']}",
                f"B is what the person then has in view: the {bundle['result']}",
            ),
            "system_process": (
                f"A initiates the handoff through the {bundle['cue']}",
                f"B is the downstream content named as the {bundle['result']}",
            ),
            "compressed_minimal": (
                f"A brings up B through the {bundle['cue']}",
                f"B is the {bundle['result']} that appears",
            ),
            "long_embedded_clause": (
                f"A is the first noticed sign, the {bundle['cue']}, which sends the system into the next item",
                f"B is the {bundle['result']} that arrives after that first sign is taken in",
            ),
            "counter_alias_hard_negative": (
                f"A is not what appears afterward; A is the {bundle['cue']} that starts the handoff",
                f"B is not the starting sign; B is the {bundle['result']} that arrives from it",
            ),
        }
    else:
        raise ValueError(f"unknown pair_key {pair_key!r}")
    return variants[family]


def _swap_marker(text: str, old: str, new: str) -> str:
    return text.replace(f"{old} ", f"{new} ", 1)


def _make_base_sentence(pair_key: str, bundle: dict[str, str], family: str, swap: bool) -> tuple[str, dict[int, str]]:
    labels = _PAIR_META[pair_key]["labels"]
    role_a, role_b = _role_text(pair_key, bundle, family)
    if not swap:
        return f"{role_a}; {role_b}.", {labels[0]: "A", labels[1]: "B"}
    return f"{_swap_marker(role_b, 'B', 'A')}; {_swap_marker(role_a, 'A', 'B')}.", {
        labels[0]: "B",
        labels[1]: "A",
    }


def _mapping_note(label: int, focus: str, pair_key: str) -> str:
    role = _PAIR_META[pair_key]["roles"][label]
    return f"Focus {focus} is the {role} role for {label}:{_NOETIC_NAMES[label]}."


def _family_list(split: str) -> tuple[str, ...]:
    if split == "test":
        return _CORE_FAMILIES + _TEST_ONLY_FAMILIES
    return _CORE_FAMILIES


def _build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle_index, bundle in enumerate(_bundles(), start=1):
        for family_index, family in enumerate(_family_list(bundle["split"]), start=1):
            for pair_index, pair_key in enumerate(_PAIR_ORDER, start=1):
                swap = (bundle_index + family_index + pair_index) % 2 == 0
                base, label_to_focus = _make_base_sentence(pair_key, bundle, family, swap=swap)
                labels = _PAIR_META[pair_key]["labels"]
                pair_id = f"{bundle['id']}_{family}_{pair_key}"
                for label in labels:
                    focus = label_to_focus[label]
                    english = f"{base} Focus: {focus}."
                    rows.append(
                        {
                            "sample_id": f"stage6_full_{bundle['id']}_{family}_{pair_key}_n{label}",
                            "dataset_version": "stage6_role_bound_noetic_full_v0",
                            "dataset_scope": "locked_fixture_no_probe_run",
                            "split": bundle["split"],
                            "contrast_bundle_id": bundle["id"],
                            "lexical_pack_id": bundle["lexical_pack_id"],
                            "template_id": f"{bundle['id']}_{family}_{pair_key}_template_v01",
                            "counterfactual_pair_id": pair_id,
                            "paraphrase_family": family,
                            "surface_style": "role_bound_system_plain",
                            "english": english,
                            "base_sentence": base,
                            "noetic_label": label,
                            "noetic_name": _NOETIC_NAMES[label],
                            "canonical_noetic": label,
                            "canonical_label": _NOETIC_NAMES[label],
                            "cas_expression": f"^{label}",
                            "focus_span": focus,
                            "contrast_partner_label": labels[1] if label == labels[0] else labels[0],
                            "hard_contrast_labels": list(labels),
                            "semantic_role": _PAIR_META[pair_key]["roles"][label],
                            "mapping_note": _mapping_note(label, focus, pair_key),
                            "anti_leak_flags": {
                                "contains_cas_notation": False,
                                "contains_label_name": False,
                                "approved_alias_used": False,
                                "counterbalanced_keyword_pack": True,
                            },
                            "source_strategy": "codex_authored_role_bound_counterfactual_template",
                            "review_status": "locked_fixture_pending_blind_review",
                            "confidence": "fixture_locked_unreviewed",
                        }
                    )
    return rows


def _split_sha(rows: list[dict[str, Any]], split: str) -> str:
    raw = b"".join(
        (json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n").encode("utf-8")
        for row in rows
        if row["split"] == split
    )
    return _sha256_bytes(raw)


def main() -> int:
    rows = _build_rows()
    _OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with _OUT_JSONL.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")

    counts = Counter(int(row["noetic_label"]) for row in rows)
    split_counts = Counter(str(row["split"]) for row in rows)
    family_counts = Counter(str(row["paraphrase_family"]) for row in rows)
    manifest = {
        "schema_version": "stage6_role_bound_full_manifest.v1",
        "dataset_version": "stage6_role_bound_noetic_full_v0",
        "status": "locked_fixture_no_probe_run",
        "output_file": _OUT_JSONL.name,
        "output_sha256": _sha256_of_file(_OUT_JSONL),
        "split_sha256": {split: _split_sha(rows, split) for split in ("train", "val", "test")},
        "n_records": len(rows),
        "n_bundles": len({row["contrast_bundle_id"] for row in rows}),
        "n_counterfactual_pairs": len({row["counterfactual_pair_id"] for row in rows}),
        "class_distribution": {str(k): counts[k] for k in sorted(counts)},
        "split_distribution": {k: split_counts[k] for k in sorted(split_counts)},
        "paraphrase_family_distribution": {k: family_counts[k] for k in sorted(family_counts)},
        "design": {
            "train_bundles": 30,
            "val_bundles": 10,
            "test_bundles": 20,
            "core_paraphrase_families": list(_CORE_FAMILIES),
            "test_only_paraphrase_families": list(_TEST_ONLY_FAMILIES),
            "pairs_per_bundle": 5,
            "labels_per_pair": 2,
            "focus_markers_counterbalanced": True,
            "model_input_field": "english",
            "model_input_excludes_mapping_note": True,
            "claim_boundary": "No activations or probes are produced by this script.",
        },
    }
    _OUT_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
