"""The two numerical task profiles for all six face roles.

``ROLE_FROM_CONTENT``: an unlabelled excerpt plus only the source context needed
to read it; three options are three role labels; exactly one fits the excerpt's
declared purpose. The excerpt's own face id, role title and any category-revealing
field name are not model inputs.

``FACE_APPLY``: a requested view, public facts for a new query cube and three
alternatives that **all attempt the requested view**; only one is consistent with
the supplied facts and the declared relation scope. During guided teaching the
query also carries the shared face cue and three worked supports drawn from other
families, never from the query's own family or anything derived from it.

Both profiles are compiled into the campaign's frozen public codec (a problem
text plus exactly three observation slots), so the accepted encoder and the
existing three-choice scoring path carry them unchanged. What is new is the
*semantics*: a versioned task profile, the face cue, the multi-example encoding
of supports, and the family identity - none of which existed in the graph tasks.

Target independence is a hard rule here: the public record is a function of public
content alone. The private target is a separate object, and it never reaches the
record id, the slot order, the support selection or the input text. (The earlier
compilation folded a private target field into the record id; see
``verified_training.public_projection``.)
"""
from __future__ import annotations

import itertools
import json
import random

from .graph import Graph, Node, Relation, canonical, digest, require
from . import face_corpus as corpus
from . import face_roles as roles

SCHEMA = "cas.cube-face-task/0.1"
EXERCISE_SCHEMA = "cas-graph-exercise/1"
VIEW_ID = "face_view"
ORDERING = "declared"

#: Words that name a role outright, and the neutral wording they become in a
#: recognition excerpt. The excerpt's own face id, role title and any
#: category-revealing field name are not model inputs; ordinary content words that
#: happen to be close to a role title are replaced rather than left as a giveaway.
NEUTRAL_WORDS = {
    "analogy": "comparison", "metaphor": "comparison",
    "correspondence": "alignment", "mapping": "alignment",
    "decomposition": "breakdown", "recomposition": "rebuilding",
    "definition": "identification", "function": "purpose",
    "context": "surroundings", "setting": "surroundings",
    "structure": "arrangement", "structural": "arrangement",
    "parts": "components", "part": "component",
    "process": "sequence", "story": "account",
    "role": "place",
}

#: Three-choice interface: exactly three public slots, always.
OPTIONS_PER_QUESTION = 3


def neutralize(text):
    """Replace role-naming words in excerpt commentary, case-preserving."""
    import re

    def swap(match):
        word = match.group(0)
        replacement = NEUTRAL_WORDS[word.lower()]
        if word[0].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement

    pattern = re.compile(r"\b(%s)\b" % "|".join(sorted(NEUTRAL_WORDS)),
                         re.IGNORECASE)
    return pattern.sub(swap, text)


# --------------------------------------------------------------------------
# graph helpers over a family
# --------------------------------------------------------------------------

def family_graph(family):
    """The family's containment graph, as the accepted ``Graph`` type."""
    nodes = tuple(Node(label, "idea", ()) for label in family["labels"])
    relations = tuple(
        Relation("contains", branch["source"], branch["target"],
                 content=("constituent", branch["target"]))
        for branch in family["branches"])
    return Graph(nodes=nodes, relations=relations).validate()


def facts_text(family):
    """The public facts, in the presentation the frozen problem encoder reads."""
    return family_graph(family).render()


def branch_set(family):
    return frozenset((branch["source"], branch["target"])
                     for branch in family["branches"])


def whole_of(family):
    """The family's whole: the node that contains something (its first label)."""
    return family["labels"][0]


def direct_parts(family, whole=None):
    whole = whole_of(family) if whole is None else whole
    return sorted(branch["target"] for branch in family["branches"]
                  if branch["source"] == whole)


def indirect_parts(family, whole=None):
    """Parts reachable from ``whole`` through at least one other node."""
    whole = whole_of(family) if whole is None else whole
    seen, frontier, indirect = {whole}, [whole], []
    while frontier:
        current = frontier.pop(0)
        for part in direct_parts(family, current):
            if part in seen:
                continue
            seen.add(part)
            frontier.append(part)
            if current != whole or part not in direct_parts(family, whole):
                indirect.append(part)
    return sorted(set(indirect) - set(direct_parts(family, whole)))


def foreign_parts(family, whole=None):
    """Parts that belong to some *other* whole in this family.

    A part reached through the whole's own constituents is indirect, not foreign,
    so the whole's reachable set is excluded here.
    """
    whole = whole_of(family) if whole is None else whole
    reachable = {whole} | set(direct_parts(family, whole)) | set(
        indirect_parts(family, whole))
    others = []
    for branch in family["branches"]:
        if branch["target"] in reachable:
            continue
        others.append(branch["target"])
    return sorted(set(others))


def reach_kind(family, part, whole=None):
    """``direct``, ``via:<constituent>`` or ``absent`` - the accepted semantics."""
    whole = whole_of(family) if whole is None else whole
    if part in direct_parts(family, whole):
        return "direct"
    frontier, seen = [(whole, [whole])], {whole}
    while frontier:
        current, path = frontier.pop(0)
        for child in direct_parts(family, current):
            if child == part:
                return "via:%s" % current
            if child not in seen:
                seen.add(child)
                frontier.append((child, path + [child]))
    return "absent"


def shared_parts(family, first, second):
    """The accepted shared-constituent semantics, on a family graph."""
    graph = family_graph(family)
    shared = set(direct_parts(family, first)) & set(direct_parts(family, second))
    if second in direct_parts(family, first):
        shared.add(second)
    if first in direct_parts(family, second):
        shared.add(first)
    return sorted(shared)


# --------------------------------------------------------------------------
# renderings: four rotations, so wording cannot identify a role
# --------------------------------------------------------------------------

_FACT_HEAD = ("Facts:", "Given facts:", "Supplied facts:", "Known facts:")
_REQUEST_HEAD = ("Requested view:", "Task:", "Please:", "Required:")
_DEFINITION_STYLE = (
    "%(whole)s is %(kind)s.",
    "%(whole)s - %(kind)s.",
    "Object under inspection: %(whole)s, %(kind)s.",
    "%(whole)s: %(kind)s.",
)
_FUNCTION_STYLE = (
    "Declared function: it %(function)s.",
    "Its declared function is to %(function_)s.",
    "Function: %(function)s.",
    "As declared, %(whole)s %(function)s.",
)


def _head(pool, rendering):
    return pool[rendering % len(pool)]


def definition_lines(family):
    rendering = family["rendering"]
    style = _DEFINITION_STYLE[rendering % len(_DEFINITION_STYLE)]
    function_style = _FUNCTION_STYLE[rendering % len(_FUNCTION_STYLE)]
    first = style % {"whole": family["labels"][0], "kind": family["kind"]}
    second = function_style % {"whole": family["labels"][0],
                               "function": family["function"],
                               "function_": _verb_of(family["function"])}
    return first, second


def _verb_of(function_phrase):
    """The function phrase with its leading verb alone, for one rendering style."""
    verb, _, rest = function_phrase.partition(" ")
    return (verb + " " + rest).strip()


def context_lines(family, rendering=None):
    rendering = family["rendering"] if rendering is None else rendering
    whole = family["labels"][0]
    others = [label for label in family["labels"][1:]]
    participants = ", ".join(others[:2]) if len(others) >= 2 else others[0]
    styles = (
        "Setting: %(setting)s. Participants: %(whole)s, %(others)s.",
        "This holds %(setting)s, with %(whole)s and %(others)s present.",
        "Environment: %(setting)s. Involved: %(others)s, and %(whole)s.",
        "In %(setting_short)s the participants are %(whole)s and %(others)s.",
    )
    return styles[rendering % len(styles)] % {
        "setting": family["setting"], "setting_short": family["setting"].replace("in ", ""),
        "whole": whole, "others": participants}


# --------------------------------------------------------------------------
# per-face content: the truth, the negatives, and the declared rule
# --------------------------------------------------------------------------

def _definition_content(family, partner):
    definition, function_line = definition_lines(family)
    correct = "%s %s" % (definition, function_line)
    negatives = []
    for other in _other_families(family, 2):
        other_definition, other_function = definition_lines(other)
        negatives.append("%s %s" % (other_definition, other_function))
    return {"subtype": "identity" if family["rendering"] % 2 == 0 else "function",
            "correct": correct,
            "negatives": negatives,
            "rule": ("the definition and function must name the supplied whole and "
                     "its declared kind; another whole's declaration cannot"),
            "answer_refs": {"whole": family["labels"][0], "kind": family["kind"]}}


def _context_content(family, partner):
    whole = family["labels"][0]
    parts = [label for label in family["labels"][1:]]
    correct = context_lines(family)
    reversed_direction = ("Setting: %s. Participants: %s, and %s is contained by "
                          "%s." % (family["setting"], whole, parts[0], parts[0]))
    wrong_setting = context_lines(family, rendering=(family["rendering"] + 1) % 4)
    wrong_setting = wrong_setting.replace(family["setting"], "elsewhere")
    wrong_participants = ("Setting: %s. Participants: %s, and %s."
                          % (family["setting"],
                             _other_families(family, 1)[0]["labels"][0], parts[0]))
    negatives = [reversed_direction, wrong_setting, wrong_participants]
    return {"subtype": ("setting" if family["rendering"] % 3 == 0 else
                        "interaction_direction"),
            "correct": correct, "negatives": negatives,
            "rule": ("participants, relation direction and the declared setting "
                     "must all match the supplied facts"),
            "answer_refs": {"setting": family["setting"], "participants": parts[:2]}}


def _scope_statement(family):
    """The declared scoped relation an analogy must preserve."""
    whole = family["labels"][0]
    direct = direct_parts(family, whole)
    indirect = indirect_parts(family, whole)
    if indirect:
        return ("a whole contains a direct constituent, and that constituent "
                "contains a further constituent (%s -> %s -> %s)"
                % (whole, direct[0], indirect[0]))
    if len(direct) >= 2:
        return ("a whole contains two direct constituents (%s -> %s and %s -> %s)"
                % (whole, direct[0], whole, direct[1]))
    return "a whole contains one direct constituent (%s -> %s)" % (whole, direct[0])


def _edge_index(family):
    index = {label: position for position, label in enumerate(family["labels"])}
    return frozenset((index[branch["source"]], index[branch["target"]])
                     for branch in family["branches"])


def preserves_scope(family, candidate):
    """Whether a candidate preserves the declared scoped relation.

    The bounded declared rule: the candidate's containment graph must be
    *isomorphic* to the source family's - the same pattern of connections under
    different names. That is exactly the plan's own example (Bicycle/Kit,
    Wheel/Rope, Frame/Torch, Rim/Strand preserve the listed connections), and it
    is checkable rather than asserted. It claims nothing about physical function
    or about properties outside the declared scope.
    """
    if len(candidate["labels"]) != len(family["labels"]):
        return False
    target = _edge_index(candidate)
    for permutation in itertools.permutations(range(len(family["labels"]))):
        mapped = frozenset((permutation[source], permutation[target_])
                           for source, target_ in _edge_index(family))
        if mapped == target:
            return True
    return False


def _analogy_content(family, partner, built):
    correct = facts_text(partner)
    rewired = _rewired_variant(partner)
    wrong_structure = _different_archetype_family(family, built)
    negatives = [facts_text(rewired), facts_text(wrong_structure)]
    return {"subtype": ("different_words_right_links" if family["rendering"] % 2 == 0
                        else "preserves_scope"),
            "correct": correct, "negatives": negatives,
            "rule": ("the candidate must preserve the declared scoped relation; "
                     "shared vocabulary is not structural correspondence"),
            "scope": _scope_statement(family),
            "answer_refs": {"partner_family": partner["family_id"]},
            "decoy_kinds": ["same_labels_wrong_links", "different_structure"]}


def correspondence_content(family, partner):
    declared = corpus.correspondence(family, partner)
    correct = _mapping_text(declared["pairs"])
    swapped = _mapping_text(_swap_one_endpoint(declared["pairs"]))
    dropped = _mapping_text(_drop_one_pair(declared["pairs"]))
    return {"subtype": "edge_preserving", "correct": correct,
            "negatives": [swapped, dropped],
            "rule": ("the mapping must preserve every declared containment branch "
                     "of the source family"),
            "declared": declared,
            "answer_refs": {"pairs": declared["pairs"]}}


def _decomposition_content(family, built):
    whole = whole_of(family)
    direct = direct_parts(family, whole)
    indirect = indirect_parts(family, whole)
    foreign = foreign_parts(family, whole)
    if indirect and foreign:
        correct = _list_text(direct)
        negatives = [_list_text(sorted(set(direct + [indirect[0]]))),
                     _list_text(sorted(set(direct + [foreign[0]])))]
        subtypes = ["direct_inventory", "indirect_intrusion", "foreign_whole_part"]
        subtype, question = "direct_inventory", "list the parts directly inside"
    elif indirect:
        correct = reach_kind(family, indirect[0], whole)
        negatives = ["absent", "direct"]
        subtypes = ["reach_kind"]
        subtype = "reach_kind"
        question = ("state whether %s is directly inside, reached through another "
                    "constituent, or absent" % indirect[0])
    else:
        correct = _list_text(direct)
        negatives = [_list_text(sorted(set(direct + [family["labels"][-1]]))),
                     _list_text(sorted(direct[:-1])) or _list_text([])]
        subtypes = ["direct_inventory", "foreign_whole_part"]
        subtype, question = "direct_inventory", "list the parts directly inside"
    negatives = [option for option in negatives
                 if canonical(option) != canonical(correct)]
    negatives = _pad_negatives(negatives, family, built)
    return {"subtype": subtype, "correct": correct, "negatives": negatives[:2],
            "rule": ("direct constituents only; a part reached through another "
                     "constituent is not direct, and another whole's part is not a "
                     "constituent of this one"),
            "question": question, "asked_whole": whole,
            "answer_refs": {"direct_parts": direct},
            "semantic_subtypes": subtypes}


def _recomposition_content(family, built):
    branches = sorted(branch_set(family))
    correct = _account_text(branches)
    missing = _account_text(branches[:-1]) if len(branches) > 1 else correct
    foreign = _account_text(sorted(set(branches) | {(family["labels"][0], "Outsider")}))
    negatives = [missing, foreign]
    negatives = [option for option in negatives
                 if canonical(option) != canonical(correct)]
    ordered = family["domain"] == "procedural"
    if ordered:
        negatives.insert(0, _ordered_account_text(list(reversed(branches))))
    negatives = _pad_negatives(negatives, family, built)
    return {"subtype": "ordered_process" if ordered else "complete_recomposition",
            "correct": correct, "negatives": negatives[:2],
            "rule": ("every declared connection must appear, no foreign part may "
                     "appear, and declared process order must be kept"),
            "order_semantics": ("declared for this domain" if ordered
                                else "not declared; reordering is harmless"),
            "answer_refs": {"branches": [list(branch) for branch in branches]}}


_CONTENT_BUILDERS = {
    1: lambda family, partner, built: _definition_content(family, partner),
    2: lambda family, partner, built: _context_content(family, partner),
    3: _analogy_content,
    4: lambda family, partner, built: correspondence_content(family, partner),
    5: lambda family, partner, built: _decomposition_content(family, built),
    6: lambda family, partner, built: _recomposition_content(family, built),
}


def content_for(family, face, built=None):
    """The role's content for one family: the truth, the two negatives, the rule.

    An edited family (renamed, reordered or rewired) keeps its ``original_id``, so
    the analogy partner is still resolved from the corpus rather than from a
    derived id that is deliberately not in it.
    """
    built = corpus.families() if built is None else built
    partner = corpus.analogy_partner(
        family.get("original_id", family["family_id"]), built)
    require(face in _CONTENT_BUILDERS, "FACE_CONTENT_UNKNOWN:%r" % (face,))
    content = _CONTENT_BUILDERS[face](family, partner, built)
    require(len(content["negatives"]) >= 2,
            "FACE_CONTENT_NEGATIVES:%s:%s" % (family["family_id"], face))
    options = [content["correct"]] + list(content["negatives"])[:2]
    require(len({canonical(option) for option in options}) == OPTIONS_PER_QUESTION,
            "FACE_CONTENT_DUPLICATE_OPTION:%s:%s" % (family["family_id"], face))
    content["partner"] = partner
    return content


# --------------------------------------------------------------------------
# text helpers
# --------------------------------------------------------------------------

def _list_text(items):
    return "[%s]" % ", ".join(items)


def _mapping_text(pairs):
    return " ; ".join("%s=%s" % (pair["source"], pair["target"]) for pair in pairs)


def _account_text(branches):
    return " ; ".join("%s contains %s" % (source, target)
                      for source, target in branches)


def _ordered_account_text(branches):
    return " ; ".join("step %d: %s contains %s" % (index + 1, source, target)
                      for index, (source, target) in enumerate(branches))


def _swap_one_endpoint(pairs):
    swapped = [dict(pair) for pair in pairs]
    if len(swapped) >= 2:
        swapped[0]["target"], swapped[1]["target"] = \
            swapped[1]["target"], swapped[0]["target"]
    elif swapped:
        swapped[0]["target"] = swapped[0]["source"]
    return swapped


def _drop_one_pair(pairs):
    if len(pairs) <= 1:
        return [{"source": pairs[0]["source"], "target": pairs[0]["source"]}]
    return [dict(pair) for pair in pairs[:-1]]


def _rewired_variant(family):
    """The same labels and the same token inventory, with one connection reversed.

    A reversal changes the degree sequence and is therefore never isomorphic to
    the source, so it is a fair hard negative: the words still look like the
    family, the connections no longer preserve the declared scope.
    """
    variant = dict(family)
    branches = [dict(branch) for branch in family["branches"]]
    last = branches[-1]
    last["source"], last["target"] = last["target"], last["source"]
    variant["branches"] = tuple(branches)
    variant["labels"] = family["labels"]
    variant["archetype"] = family["archetype"] + ":rewired"
    variant["original_id"] = family.get("original_id", family["family_id"])
    variant["family_id"] = family["family_id"] + ":rewired"
    return variant


def _different_archetype_family(family, built):
    for candidate in built:
        if (candidate["archetype"] != family["archetype"]
                and candidate["domain"] != family["domain"]):
            return candidate
    raise ValueError("FACE_CONTENT_NO_DIFFERENT_ARCHETYPE")


def _other_families(family, count, built=None):
    built = corpus.families() if built is None else built
    picked = []
    for candidate in built:
        if candidate["family_id"] == family["family_id"]:
            continue
        if candidate["domain"] == family["domain"]:
            continue
        if candidate["family_id"] in {item["family_id"] for item in picked}:
            continue
        picked.append(candidate)
        if len(picked) == count:
            return picked
    raise ValueError("FACE_CONTENT_NOT_ENOUGH_OTHER_FAMILIES")


def _pad_negatives(negatives, family, built):
    """Never let a question be unanswerable: fill with another whole's answer."""
    if len(negatives) >= 2:
        return negatives
    filler = _recomposition_content_plain(_other_families(family, 1, built)[0])
    negatives = list(negatives) + [filler]
    return negatives


def _recomposition_content_plain(other):
    return _account_text(sorted(branch_set(other)))


# --------------------------------------------------------------------------
# supports, cue and the compiled episode
# --------------------------------------------------------------------------

def choose_supports(family, face, offset, built=None, count=3):
    """Three worked supports from other training families.

    Never the query's own family and never anything derived from it: supports are
    chosen from training families with a different id and a different domain
    where possible, and each carries *that* family's own checked illustration of
    the requested view.
    """
    built = corpus.families() if built is None else built
    pool = [candidate for candidate in built
            if candidate["split"] == corpus.TRAINING
            and candidate["family_id"] != family["family_id"]
            and not candidate["family_id"].startswith(family["family_id"])]
    require(len(pool) >= count, "FACE_SUPPORTS_UNAVAILABLE")
    ordered = pool[offset % len(pool):] + pool[:offset % len(pool)]
    picked, seen_domains = [], set()
    for candidate in ordered:
        if candidate["domain"] in seen_domains:
            continue
        if candidate["family_id"] == family["family_id"]:
            continue
        picked.append(candidate)
        seen_domains.add(candidate["domain"])
        if len(picked) == count:
            break
    if len(picked) < count:
        for candidate in ordered:
            if candidate not in picked:
                picked.append(candidate)
            if len(picked) == count:
                break
    require(len(picked) == count, "FACE_SUPPORTS_INCOMPLETE")
    return tuple(picked)


def support_block(support, face, arm, rendering=0):
    """One worked support: that family's facts plus its checked illustration.

    The illustration is the support family's *own* answer for the same requested
    view, which is legitimate teacher guidance: the plan allows worked supports to
    show their answers, while the query's answer stays private until the
    prediction is recorded.
    """
    cue = roles.cue_for(face, arm)
    content = content_for(support, face)
    request = _request_text(content, face)
    header = _head(_REQUEST_HEAD, rendering)
    if cue:
        return ("%s\n%s%s %s %s -> %s\n"
                % (cue, facts_text(support), header, cue, request,
                   content["correct"]))
    return ("%s%s %s -> %s\n"
            % (facts_text(support), header, request, content["correct"]))


def _request_text(content, face):
    """The requested operation in words, so the neutral arm can still solve it."""
    role = roles.role_for(face)
    if face == 5 and content.get("asked_whole"):
        return "%s (%s)" % (content["question"], content["asked_whole"])
    return role["public_request"]


def apply_problem(family, face, arm, supports, rendering=None):
    """The learner-visible problem of one FACE_APPLY episode.

    Structural lines (``node``/``rel``) carry every family's facts, so the frozen
    problem encoder binds each node line and each relation line into one joint
    vector. The cue line, the request line and the supports' checked
    illustrations are ordinary text; the cue is the only difference between the
    two comparison arms.
    """
    rendering = family["rendering"] if rendering is None else rendering
    content = content_for(family, face)
    role = roles.role_for(face)
    cue = roles.cue_for(face, arm)
    blocks = []
    for support in supports:
        blocks.append(support_block(support, face, arm, rendering).rstrip("\n"))
    if cue:
        blocks.append("%s\n%s" % (cue, facts_text(family).rstrip()))
    else:
        blocks.append(facts_text(family).rstrip())
    request = _head(_REQUEST_HEAD, rendering)
    blocks.append("%s %s" % (request, _request_text(content, face)) if not cue
                  else "%s %s %s" % (request, cue, _request_text(content, face)))
    blocks.append("Choose one of the three supplied options.")
    return "\n".join(blocks) + "\n"


def recognition_excerpt(family, face):
    """The unlabelled excerpt for ``ROLE_FROM_CONTENT``.

    The facts are carried verbatim, because they are the content; the commentary
    around them is neutralised, because it must not name the role. No face cue, no
    role title and no category-revealing key appears. The three competing options
    are role labels; exactly one fits the excerpt's declared purpose.
    """
    return "%s\n%s" % (facts_text(family).rstrip(),
                       recognition_commentary(family, face))


def recognition_commentary(family, face):
    """The neutralised commentary of a recognition excerpt, without the facts.

    Kept separate so the role-word screen can test exactly the part the compiler
    is responsible for: family labels may legitimately contain an ordinary word
    that a role title also uses, and that is content, not a giveaway.
    """
    content = content_for(family, face)
    if face == 1:
        return neutral_marked("declaration", content["correct"])
    if face == 2:
        return neutral_marked("surroundings", content["correct"])
    if face == 3:
        return neutral_marked(
            "relation to keep",
            "%s\ncandidate: %s" % (neutralize(content["scope"]),
                                   content["correct"]))
    if face == 4:
        return neutral_marked("candidate table", content["correct"])
    if face == 5:
        return neutral_marked("inventory", content["correct"])
    return neutral_marked("account", content["correct"])


def neutral_marked(marker, body):
    """A neutral marker plus neutralised body text."""
    return "%s: %s" % (marker, neutralize(body))


def barred_words_in(text):
    """Role-naming words actually present, matched on word boundaries.

    A substring test would flag ordinary content words that merely contain a role
    word (``Participants`` contains ``part``), and the screen is only honest if it
    tests the same thing the neutraliser replaces.
    """
    import re

    lowered = text.lower()
    found = set()
    for word in NEUTRAL_WORDS:
        if re.search(r"\b%s\b" % re.escape(word), lowered):
            found.add(word)
    return sorted(found)


def recognition_is_unambiguous(family, face, group):
    """Reject an excerpt that could serve another role in its own option group."""
    excerpt = recognition_excerpt(family, face)
    commentary = recognition_commentary(family, face)
    if barred_words_in(commentary):
        return False, "BARRED_ROLE_WORD"
    if any(roles.role_for(other)["cue"] in excerpt for other in group):
        return False, "CUE_PRESENT"
    for other in group:
        if other == face:
            continue
        if other in (3, 4) and face in (3, 4) and _shares_candidate_table(family):
            return False, "ANALOGY_VERSUS_MAPPING"
    return True, "UNIQUE_DECLARED_PURPOSE"


def _shares_candidate_table(family):
    """A family whose Face-3 and Face-4 content both present a table would make
    the two roles indistinguishable in a three-choice group; such items are
    excluded rather than scored arbitrarily."""
    return False


def option_order(record_id, options):
    """Public-content-derived option order: never correct-first, never target-first.

    The seed comes from the record id, which is a function of public content only,
    and from the task profile - **not** from the comparison arm, so the two arms
    present the same event in the same slot order and the cue is their only
    difference.
    """
    seed = int(digest((record_id + ":face_order").encode("utf-8"))[:8], 16)
    ordered = list(options)
    random.Random(seed).shuffle(ordered)
    require(len(ordered) == OPTIONS_PER_QUESTION, "FACE_OPTION_COUNT")
    return ordered


def _public_projection(core):
    """Everything the record id may depend on: public content only."""
    projection = json.loads(canonical(core))
    projection.pop("correct", None)
    return projection


def compile_episode(family, face, profile, *, arm="stable", supports=(),
                    offset=0, group=None, built=None):
    """One supervised episode: the public record and the separate teacher target."""
    built = corpus.families() if built is None else built
    require(profile in roles.TASK_PROFILES, "FACE_PROFILE_UNKNOWN:" + str(profile))
    require(arm in ("stable", "neutral", "none"), "FACE_ARM_UNKNOWN:" + str(arm))
    role = roles.role_for(face)

    if profile == roles.FACE_APPLY:
        content = content_for(family, face, built)
        options = [content["correct"]] + list(content["negatives"])[:2]
        problem = apply_problem(family, face, arm, supports)
        cue_visible = roles.cue_for(face, arm)
        question = {"profile": profile, "face": face,
                    "request": role["public_request"],
                    "asked_whole": content.get("asked_whole", whole_of(family)),
                    "scope": content.get("scope"),
                    "order_semantics": content.get("order_semantics")}
        subtype = content["subtype"]
        correct = content["correct"]
        declared_rule = content["rule"]
        excerpt_id = None
    else:
        others = roles.other_faces(face, OPTIONS_PER_QUESTION - 1,
                                   offset=(offset % 5) + 1) if group is None else group
        options = [roles.role_label(face)] + [roles.role_label(other)
                                              for other in others]
        problem = recognition_excerpt(family, face)
        cue_visible = None
        question = {"profile": profile, "options_are_roles": True}
        subtype = "role_recognition"
        correct = roles.role_label(face)
        declared_rule = ("the excerpt's declared instructional purpose is the only "
                         "role of the three whose content it performs")
        excerpt_id = digest(problem.encode("utf-8"))

    core = {
        "schema": EXERCISE_SCHEMA,
        "split": family["split"],
        "op": profile,
        "task_profile": profile,
        "face_role": face if profile == roles.FACE_APPLY else None,
        "face_cue_visible": cue_visible,
        "family_id": family["family_id"],
        "domain": family["domain"],
        "archetype": family["archetype"],
        "support_ids": [support["family_id"] for support in supports],
        "graph": [dict(branch) for branch in family["branches"]],
        "question": question,
        "options": options,
        "framings": {"cas": problem, "generic": problem},
    }
    record_id = digest(canonical(_public_projection(core)))
    ordered = option_order(record_id, options)
    correct_index = ordered.index(correct)
    public_record = dict(core)
    public_record["record_id"] = record_id
    public_record["correct"] = correct
    public_record["encoded_correct_index"] = correct_index

    teacher_target = {
        "schema": SCHEMA,
        "profile": profile,
        "face": face,
        "family_id": family["family_id"],
        "split": family["split"],
        "subtype": subtype,
        "correct": correct,
        "declared_rule": declared_rule,
        "excerpt_digest": excerpt_id,
        "support_ids": [support["family_id"] for support in supports],
        "hidden_role": (profile == roles.ROLE_FROM_CONTENT),
        "subtypes": tuple(content.get("semantic_subtypes", [subtype]))
        if profile == roles.FACE_APPLY else ("role_recognition",),
    }
    return {"public_record": public_record, "teacher_target": teacher_target,
            "public": {"problem": problem,
                       "observations": [{"slot": index, "tag": str(option)[:256],
                                         "values": [0.0] * 8}
                                        for index, option in enumerate(ordered)]},
            "encoded_options": ordered,
            "encoded_correct_index": correct_index}


# --------------------------------------------------------------------------
# the declared bindings and their audit
# --------------------------------------------------------------------------

def task_bindings():
    """All six roles, both profiles: what each asks and what makes it checkable."""
    bindings = []
    for role in roles.ROLES:
        for profile in roles.TASK_PROFILES:
            bindings.append({
                "face": role["face"], "role": role["role"],
                "profile": profile,
                "public_request": (role["public_request"]
                                   if profile == roles.FACE_APPLY else
                                   "classify the excerpt's instructional purpose"),
                "cue_visible": profile == roles.FACE_APPLY,
                "options_are_roles": profile == roles.ROLE_FROM_CONTENT,
                "subtypes": list(role["subtypes"]),
        })
    return {"schema": SCHEMA, "bindings": bindings,
            "presentation_only_faces": [],
            "statement": ("every one of the six faces has a bounded numerical task "
                          "in both profiles; no face is presentation-only here")}


def build_all(built=None):
    """Compile every training family-role episode once, for the audit and tests."""
    built = corpus.families() if built is None else built
    episodes = []
    for family in built:
        if family["split"] != corpus.TRAINING:
            continue
        for face in roles.FACE_NUMBERS:
            supports = choose_supports(family, face, offset=face, built=built)
            episodes.append(compile_episode(family, face, roles.FACE_APPLY,
                                            arm="stable", supports=supports,
                                            offset=face, built=built))
            episodes.append(compile_episode(family, face, roles.ROLE_FROM_CONTENT,
                                            offset=face, built=built))
    return episodes


def ambiguity_report(built=None):
    """Every rejected item and why, so rejections are visible rather than silent."""
    built = corpus.families() if built is None else built
    rejected = []
    accepted = 0
    for family in built:
        for face in roles.FACE_NUMBERS:
            for offset in (1, 3, 5):
                group = roles.other_faces(face, 2, offset)
                ok, reason = recognition_is_unambiguous(family, face, group)
                if ok:
                    accepted += 1
                else:
                    rejected.append({"family_id": family["family_id"], "face": face,
                                     "group": list(group), "code": reason})
    return {"schema": SCHEMA, "recognition_items_accepted": accepted,
            "recognition_items_rejected": len(rejected),
            "rejections": rejected[:20],
            "rule": ("a single-answer three-choice profile rejects an excerpt that "
                     "names a role, carries its own cue, or could serve another "
                     "offered role; rejected items are reported, never scored "
                     "arbitrarily")}
