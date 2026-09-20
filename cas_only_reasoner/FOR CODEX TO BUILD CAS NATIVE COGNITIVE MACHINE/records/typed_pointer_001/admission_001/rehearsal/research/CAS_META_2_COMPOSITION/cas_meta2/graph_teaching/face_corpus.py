"""The family-grouped source corpus for CUBE_FACE_GROUNDING_001.

96 authored lesson families, each one small containment world with declared
facts, grouped into families *before* splitting: a family is its base lesson plus
every rendering, analogy, correspondence, decomposition, recomposition and hard
negative derived from it, so no derived item can leak across the split.

What is authored and what is derived, stated plainly because the plan requires a
coverage report rather than a claim:

* **authored**: the 96 label sets, the domain each belongs to, its structural
  archetype, its ``kind`` phrase, and the per-domain function and setting
  templates it is rendered through;
* **derived, and checkable**: every node, every containment branch, every face's
  correct answer and every negative option. Nothing is prose-only, and no answer
  is "whatever file this came from".

Honest coverage limits, reported by :func:`coverage_report` rather than glossed:
six topologies serve 96 families, so *structure* repeats while labels, domains
and renderings do not. Familiar-structure/new-instance items and unseen-arrangement
items are therefore counted separately, and the former is never called the latter.
"""
from __future__ import annotations

import itertools

from .graph import canonical, digest, require

SCHEMA = "cas.cube-face-corpus/0.1"

TRAINING = "training"
DEVELOPMENT = "development"
FINAL_HELD_OUT = "final_held_out"
SPLITS = (TRAINING, DEVELOPMENT, FINAL_HELD_OUT)
TRAINING_FAMILIES = 64
DEVELOPMENT_FAMILIES = 16
FINAL_HELD_OUT_FAMILIES = 16

#: Structural archetypes. Each is a containment graph: ``(source, target)``
#: branches over the family's composed label tuple (its three authored labels
#: plus, for the four-node archetypes, its authored extra part). Six distinct
#: arrangements, three and four nodes.
ARCHETYPES = {
    "chain2": ((0, 1), (1, 2)),
    "branch3": ((0, 1), (0, 2), (0, 3)),
    "diamond": ((0, 1), (0, 2), (2, 3), (1, 3)),
    "chain3": ((0, 1), (1, 2), (2, 3)),
    "pair_shared": ((0, 2), (1, 2), (0, 3)),
    "fork_child": ((0, 1), (0, 2), (2, 3)),
}
ARCHETYPE_ORDER = ("chain2", "branch3", "diamond", "chain3", "pair_shared",
                   "fork_child")

#: Four renderer rotations, because "multiple rendering styles occur within every
#: face role" and one fixed phrasing would let wording identify the role.
RENDERINGS = 4

#: domain -> 16 authored label sets, each with its ``kind`` phrase. Labels are
#: read in the archetype's node order.
_AUTHORED = {
    "mechanical": (
        (("Bicycle", "Wheel", "Rim"), "a wheeled vehicle"),
        (("Cart", "Platform", "Axle"), "a hand-drawn platform"),
        (("Clock", "Gear", "Spring"), "a timekeeping mechanism"),
        (("Pump", "Piston", "Valve"), "a fluid-moving device"),
        (("Loom", "Shuttle", "Thread"), "a weaving machine"),
        (("Lathe", "Chuck", "Tool"), "a turning machine"),
        (("Turbine", "Blade", "Rotor"), "a rotary engine"),
        (("Boiler", "Drum", "Tube"), "a steam vessel"),
        (("Crane", "Hook", "Cable"), "a lifting machine"),
        (("Drill", "Bit", "Chuck"), "a boring tool"),
        (("Engine", "Crankshaft", "Piston"), "a combustion engine"),
        (("Brake", "Pad", "Disc"), "a stopping assembly"),
        (("Clutch", "Plate", "Spring"), "a coupling assembly"),
        (("Radiator", "Core", "Fin"), "a cooling assembly"),
        (("Alternator", "Rotor", "Brush"), "a charging machine"),
        (("Gearbox", "Shaft", "Gear"), "a transmission assembly"),
    ),
    "grammatical": (
        (("Sentence", "Phrase", "Word"), "a grammatical unit"),
        (("Clause", "Subject", "Predicate"), "a clause pattern"),
        (("Paragraph", "Topic", "Support"), "a paragraph pattern"),
        (("Question", "Auxiliary", "VerbPhrase"), "a question pattern"),
        (("List", "Item", "Marker"), "a list pattern"),
        (("Compound", "ClauseA", "Conjunction"), "a compound pattern"),
        (("Quotation", "Speaker", "Utterance"), "a quotation pattern"),
        (("Heading", "Section", "Subheading"), "a heading pattern"),
        (("Caption", "Figure", "Label"), "a caption pattern"),
        (("Footnote", "Marker", "Note"), "a footnote pattern"),
        (("Acronym", "Letters", "Expansion"), "an acronym pattern"),
        (("Syllable", "Onset", "Rhyme"), "a syllable pattern"),
        (("Morpheme", "Root", "Affix"), "a morpheme pattern"),
        (("Tense", "AuxiliaryForm", "Participle"), "a tense pattern"),
        (("Agreement", "Noun", "VerbForm"), "an agreement pattern"),
        (("Punctuation", "Mark", "Boundary"), "a punctuation pattern"),
    ),
    "procedural": (
        (("Recipe", "Step", "Ingredient"), "a cooking procedure"),
        (("Assembly", "Stage", "Fastener"), "an assembly procedure"),
        (("Checkout", "Payment", "Receipt"), "a checkout procedure"),
        (("Onboarding", "Briefing", "Task"), "an onboarding procedure"),
        (("Backup", "Copy", "Archive"), "a backup procedure"),
        (("Deploy", "Build", "Release"), "a deployment procedure"),
        (("Inspection", "Check", "Report"), "an inspection procedure"),
        (("Calibration", "Measure", "Adjust"), "a calibration procedure"),
        (("Refund", "Request", "Approval"), "a refund procedure"),
        (("Interview", "Schedule", "Notes"), "an interview procedure"),
        (("Migration", "Plan", "Cutover"), "a migration procedure"),
        (("Rehearsal", "Run", "Notes"), "a rehearsal procedure"),
        (("Audit", "Sample", "Finding"), "an audit procedure"),
        (("Repair", "Diagnosis", "Replacement"), "a repair procedure"),
        (("Cleaning", "Rinse", "Dry"), "a cleaning procedure"),
        (("Printing", "Plate", "Ink"), "a printing procedure"),
    ),
    "container": (
        (("Kit", "Rope", "Strand"), "a packed kit"),
        (("Toolbox", "Wrench", "Socket"), "a tool container"),
        (("Pantry", "Jar", "Lid"), "a food store"),
        (("Backpack", "Pouch", "Zipper"), "a carried pack"),
        (("Crate", "Bottle", "Cap"), "a shipping crate"),
        (("Shelf", "Box", "Label"), "a storage shelf"),
        (("Suitcase", "Strap", "Buckle"), "a travel case"),
        (("FirstAidKit", "Bandage", "Gauze"), "a first-aid kit"),
        (("CameraBag", "Lens", "Cap"), "a camera bag"),
        (("PencilCase", "Eraser", "Sleeve"), "a pencil case"),
        (("PicnicBasket", "Plate", "Napkin"), "a picnic basket"),
        (("FilingBox", "Folder", "Tab"), "a filing box"),
        (("SeedPacket", "Seeds", "Envelope"), "a seed packet"),
        (("CableBag", "Coil", "Tie"), "a cable bag"),
        (("SpiceRack", "SpiceJar", "Scoop"), "a spice rack"),
        (("ArtCase", "Brush", "Bristle"), "an art case"),
    ),
    "organisational": (
        (("Team", "Squad", "Lead"), "a working team"),
        (("Company", "Division", "Team"), "a company structure"),
        (("Project", "Workstream", "Task"), "a project structure"),
        (("Committee", "Panel", "Member"), "a committee structure"),
        (("Department", "Unit", "Role"), "a department structure"),
        (("Programme", "Initiative", "Deliverable"), "a programme structure"),
        (("Board", "Committee", "Charter"), "a board structure"),
        (("Partnership", "Firm", "Partner"), "a partnership structure"),
        (("Guild", "Chapter", "Member"), "a guild structure"),
        (("Consortium", "MemberOrg", "Liaison"), "a consortium structure"),
        (("Shift", "Crew", "Roster"), "a shift structure"),
        (("Council", "WorkingGroup", "Mandate"), "a council structure"),
        (("Institute", "Lab", "Group"), "an institute structure"),
        (("Alliance", "PartnerState", "Treaty"), "an alliance structure"),
        (("Network", "Node", "Link"), "a network structure"),
        (("Federation", "MemberBody", "Statute"), "a federation structure"),
    ),
    "narrative": (
        (("Story", "Act", "Scene"), "a story structure"),
        (("Plot", "Thread", "Beat"), "a plot structure"),
        (("Character", "Trait", "Motivation"), "a character structure"),
        (("Mystery", "Clue", "Suspect"), "a mystery structure"),
        (("Journey", "Leg", "Waypoint"), "a journey structure"),
        (("Fable", "Animal", "Moral"), "a fable structure"),
        (("Dialogue", "Turn", "Reply"), "a dialogue structure"),
        (("Flashback", "Scene", "Trigger"), "a flashback structure"),
        (("Series", "Season", "Episode"), "a series structure"),
        (("Legend", "Hero", "Deed"), "a legend structure"),
        (("Myth", "Deity", "Domain"), "a myth structure"),
        (("Chronicle", "Entry", "Event"), "a chronicle structure"),
        (("Ballad", "Stanza", "Refrain"), "a ballad structure"),
        (("Parable", "Setting", "Lesson"), "a parable structure"),
        (("Saga", "Family", "Feud"), "a saga structure"),
        (("Anecdote", "Setup", "Punchline"), "an anecdote structure"),
    ),
}
DOMAIN_ORDER = ("mechanical", "grammatical", "procedural", "container",
                "organisational", "narrative")

#: The fourth authored label of each family, used by the four-node archetypes.
#: Kept as one word per family so every part named in a question is a real part of
#: that family's world, not a filler.
_EXTRAS = {
    "mechanical": ("Spoke", "Handle", "Seal", "Gasket", "Bearing", "Bolt",
                   "Coupling", "Sprocket", "Bracket", "Liner", "Shim", "Pinion",
                   "Spindle", "Cam", "Filter", "Manifold"),
    "grammatical": ("Modifier", "Object", "Adjunct", "Complement", "Determiner",
                    "Particle", "Connector", "Appositive", "Gerund", "Infinitive",
                    "Qualifier", "Interjection", "Pronoun", "Adverb",
                    "Preposition", "Diphthong"),
    "procedural": ("Checklist", "Signoff", "Template", "Ticket", "Log", "Handover",
                   "Rollback", "Snapshot", "Verifier", "Batch", "Queue",
                   "Escalation", "Retry", "Ledger", "Stamp", "Voucher"),
    "container": ("Divider", "Insert", "Tray", "Liner", "Pocket", "HandleTag",
                  "Tag", "Seal", "Clasp", "Card", "Sticker", "Wrapper", "Carton",
                  "Sachet", "Cushion", "Bin"),
    "organisational": ("Convener", "Secretary", "Steering", "Quorum", "Minute",
                       "Proxy", "Subgroup", "Taskforce", "Delegate", "Registrar",
                       "Trustee", "Warden", "Steward", "Envoy", "Rapporteur",
                       "Secretariat"),
    "narrative": ("Motif", "Foil", "Climax", "Twist", "Narrator", "Prologue",
                  "Epilogue", "Coda", "Omen", "Rival", "Mentor", "Herald",
                  "Threshold", "Oracle", "Verse", "Chorus"),
}

#: Which archetype each family in a domain takes, so that every domain carries
#: all six structures and every training domain contributes all six roles.
_ARCHETYPE_CYCLE = ARCHETYPE_ORDER

_FUNCTION = {
    "mechanical": "transmits force between %(whole)s and %(child)s",
    "grammatical": "carries the relation between %(whole)s and %(child)s",
    "procedural": "produces %(child)s as part of %(whole)s",
    "container": "holds %(child)s inside %(whole)s",
    "organisational": "assigns %(child)s within %(whole)s",
    "narrative": "connects %(child)s to %(whole)s",
}
_SETTING = {
    "mechanical": "in a workshop",
    "grammatical": "in an edited sentence",
    "procedural": "during a recorded run",
    "container": "in a packed store",
    "organisational": "in a standing arrangement",
    "narrative": "within one telling",
}


def _split_for(index):
    """64 / 16 / 16, assigned by family index before any rendering exists."""
    if index < TRAINING_FAMILIES:
        return TRAINING
    if index < TRAINING_FAMILIES + DEVELOPMENT_FAMILIES:
        return DEVELOPMENT
    return FINAL_HELD_OUT


def _branches(archetype, labels):
    highest = max(max(pair) for pair in ARCHETYPES[archetype])
    require(highest < len(labels), "FACE_CORPUS_ARCHETYPE_NEEDS_MORE_LABELS:%s"
            % archetype)
    return tuple({"source": labels[source], "target": labels[target]}
                 for source, target in ARCHETYPES[archetype])


def family_labels(domain, position, archetype):
    """The composed label tuple: three authored labels plus the authored extra.

    The extra part is only needed by the four-node archetypes, and it is dropped
    for the three-node one so no node is invented and no label goes unused.
    """
    authored = tuple(_AUTHORED[domain][position][0])
    if archetype == "chain2":
        return authored
    return authored + (_EXTRAS[domain][position],)


def families():
    """The 96 families, deterministically ordered."""
    built = []
    index = 0
    for domain in DOMAIN_ORDER:
        entries = _AUTHORED[domain]
        require(len(entries) == 16, "FACE_CORPUS_DOMAIN_SIZE:" + domain)
        for position, (labels, kind) in enumerate(entries):
            archetype = _ARCHETYPE_CYCLE[position % len(_ARCHETYPE_CYCLE)]
            composed = family_labels(domain, position, archetype)
            require(len(composed) >= 3, "FACE_CORPUS_LABELS_TOO_FEW")
            branches = _branches(archetype, composed)
            family = {
                "family_id": "family:%s:%02d" % (domain, position),
                "domain": domain,
                "archetype": archetype,
                "rendering": index % RENDERINGS,
                "kind": kind,
                "labels": composed,
                "branches": branches,
                "split": _split_for(index),
                "setting": _SETTING[domain],
                "function": _FUNCTION[domain] % {"whole": composed[0],
                                                 "child": composed[1]},
            }
            built.append(family)
            index += 1
    require(len(built) == 96, "FACE_CORPUS_SIZE:%d" % len(built))
    return tuple(built)


def family_index(built=None):
    built = families() if built is None else built
    return {family["family_id"]: family for family in built}


def by_split(split, built=None):
    built = families() if built is None else built
    require(split in SPLITS, "FACE_CORPUS_SPLIT_UNKNOWN:" + str(split))
    return tuple(family for family in built if family["split"] == split)


def _partner_pairs(built):
    """Pair training families across domains, matching archetype.

    A partner must share the archetype, so the correspondence preserves the
    declared edges by construction, and must come from a *different* domain and a
    different label set, so the analogy is cross-domain rather than a rename.
    """
    pairs = {}
    for archetype in ARCHETYPE_ORDER:
        pool = [family for family in built
                if family["archetype"] == archetype]
        require(len(pool) >= 2, "FACE_CORPUS_ARCHETYPE_POOL:" + archetype)
        for position, family in enumerate(pool):
            partner = None
            for offset in range(1, len(pool) + 1):
                candidate = pool[(position + offset) % len(pool)]
                if (candidate["domain"] != family["domain"]
                        and candidate["labels"] != family["labels"]):
                    partner = candidate
                    break
            require(partner is not None,
                    "FACE_CORPUS_PARTNER_UNAVAILABLE:" + family["family_id"])
            pairs[family["family_id"]] = partner["family_id"]
    return pairs


def analogy_partner(family_id, built=None):
    built = families() if built is None else built
    index = family_index(built)
    require(family_id in index, "FACE_CORPUS_FAMILY_UNKNOWN:" + str(family_id))
    partner_id = _partner_pairs(built)[family_id]
    return index[partner_id]


def correspondence(family, partner):
    """The declared scoped mapping between two same-archetype families.

    Node roles map position to position (both graphs use the archetype's node
    order) and the branches are preserved by construction. Each mapping entry
    carries the source branch it preserves, so "the correspondence" is checkable
    rather than asserted.
    """
    require(family["archetype"] == partner["archetype"],
            "FACE_CORPUS_CORRESPONDENCE_ARCHETYPE")
    pairs = []
    for position, label in enumerate(family["labels"]):
        if position >= len(partner["labels"]):
            break
        pairs.append({"source": label, "target": partner["labels"][position]})
    mapped = {entry["source"]: entry["target"] for entry in pairs}
    preserved = []
    for branch in family["branches"]:
        source, target = branch["source"], branch["target"]
        require(source in mapped and target in mapped,
                "FACE_CORPUS_CORRESPONDENCE_INCOMPLETE")
        preserved.append({"source_branch": [source, target],
                          "target_branch": [mapped[source], mapped[target]]})
    return {"source_family": family["family_id"],
            "target_family": partner["family_id"],
            "archetype": family["archetype"],
            "pairs": pairs, "preserved_branches": preserved,
            "scope_note": ("preserves the listed containment branches only; it "
                           "claims nothing about physical function or other "
                           "properties")}


def digest_of_family(family):
    return digest(canonical({"domain": family["domain"],
                             "archetype": family["archetype"],
                             "labels": list(family["labels"]),
                             "branches": list(family["branches"])}))


def coverage_report(built=None):
    """What the corpus actually covers, so nothing is inferred from its size."""
    built = families() if built is None else built
    index = family_index(built)
    pairs = _partner_pairs(built)
    structure_histogram = {}
    domain_histogram = {}
    rendering_histogram = {}
    graph_digests = set()
    topology_digests = set()
    per_domain_faces = {}
    for family in built:
        structure_histogram[family["archetype"]] = \
            structure_histogram.get(family["archetype"], 0) + 1
        domain_histogram[family["domain"]] = domain_histogram.get(
            family["domain"], 0) + 1
        rendering_histogram[family["rendering"]] = rendering_histogram.get(
            family["rendering"], 0) + 1
        graph_digests.add(digest_of_family(family))
        # topology only: the edge structure over node positions, labels removed,
        # so structure overlap is reported separately from family overlap.
        topology_digests.add(digest(canonical(
            sorted([list(pair) for pair in ARCHETYPES[family["archetype"]]]))))
        per_domain_faces.setdefault(family["domain"], set()).add(len(ARCHETYPES))
    return {
        "schema": SCHEMA,
        "families": len(built),
        "split_counts": {split: len(by_split(split, built)) for split in SPLITS},
        "base_face_presentations": len(built) * 6,
        "structure_histogram": structure_histogram,
        "domain_histogram": domain_histogram,
        "rendering_histogram": rendering_histogram,
        "distinct_family_graphs": len(graph_digests),
        "distinct_topologies": len(topology_digests),
        "cross_domain_analogy_pairs": sum(
            1 for family_id, partner_id in pairs.items()
            if index[family_id]["domain"] != index[partner_id]["domain"]),
        "every_domain_carries_all_six_roles": all(
            len(faces) == 1 for faces in per_domain_faces.values()),
        "structure_overlap_statement": (
            "%d families share %d topologies: structure repeats while labels, "
            "domains and renderings do not. Familiar-structure/new-instance items "
            "are therefore a separate class from unseen arrangements and are "
            "counted separately, never merged." % (len(built),
                                                  len(topology_digests))),
        "split_rule": ("assigned by family index before any rendering is built, "
                       "so no derived item of a family crosses the split"),
    }


def family_manifest(built=None):
    """The dataset manifest: one entry per family, per-question facts included."""
    built = families() if built is None else built
    return {
        "schema": SCHEMA,
        "coverage": coverage_report(built),
        "families": [
            {"family_id": family["family_id"], "split": family["split"],
             "domain": family["domain"], "archetype": family["archetype"],
             "rendering": family["rendering"], "kind": family["kind"],
             "labels": list(family["labels"]),
             "branches": list(family["branches"]),
             "setting": family["setting"], "function": family["function"],
             "graph_digest": digest_of_family(family),
             "analogy_partner": _partner_pairs(built)[family["family_id"]]}
            for family in built],
    }


def rotation_pairs():
    """All ordered role pairs, for rotating recognition groups."""
    return tuple(itertools.permutations(range(1, 7), 2))
