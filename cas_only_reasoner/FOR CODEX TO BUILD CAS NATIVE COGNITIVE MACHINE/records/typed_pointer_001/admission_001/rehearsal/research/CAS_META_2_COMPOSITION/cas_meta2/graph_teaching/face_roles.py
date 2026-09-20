"""CUBE_FACE_GROUNDING_001 — the six face roles as teaching handles.

STATUS: candidate-only specification and compilation. Nothing here trains, loads
a model, reserves capacity or launches. The registry is the *handle*: a stable
categorical marker attached to varied content, never a magnitude to average.

Boundaries this module keeps, from the plan it implements:

* the six roles keep their existing meanings and numbering, and a face number is
  **not** a Noetic operator number (Face 5 is the decomposition teaching face
  associated with the intended Male/^6 lesson, not ^5);
* a role marker is categorical. ``CUBE_FACE_5`` is one token, not the integer
  55,555 and not five repeated digits;
* the *excerpt's own* face id is never a model input for role recognition; the
  marker appears only where the role is a legitimate public instruction
  (``FACE_APPLY``), and the comparison's neutral arm replaces it with one common
  cue so that both arms can still solve every task;
* mixed-purpose excerpts are rejected rather than forced into one role.
"""
from __future__ import annotations

from .graph import require

SCHEMA = "cas.cube-face-roles/0.1"

#: The stable cue of the neutral-cue control arm. One common marker, never a
#: false or contradictory category.
NEUTRAL_CUE = "CUBE_FACE_NEUTRAL"

#: The two task profiles this plan adds. They are new semantics with their own
#: names: neither is a renamed LIST_PARTS, and neither is scored as one.
ROLE_FROM_CONTENT = "ROLE_FROM_CONTENT"
FACE_APPLY = "FACE_APPLY"
TASK_PROFILES = (ROLE_FROM_CONTENT, FACE_APPLY)

#: Role registry. ``subtypes`` name the bounded semantic categories each role's
#: choices are balanced over, so a per-face report cannot hide one subtype.
ROLES = (
    {"face": 1, "cue": "CUBE_FACE_1", "role": "name_definition_function",
     "title": "Technical name, definition and function",
     "objective": "recognize and select a definition or function consistent with "
                  "the supplied facts",
     "public_request": "state what the whole is and what it is for, as declared",
     "subtypes": ("identity", "function")},
    {"face": 2, "cue": "CUBE_FACE_2", "role": "context_environment",
     "title": "Context, environment and interactions",
     "objective": "recognize and select a contextual account consistent with the "
                  "supplied facts",
     "public_request": "state the setting and the interactions that hold here",
     "subtypes": ("setting", "interaction_direction", "participants")},
    {"face": 3, "cue": "CUBE_FACE_3", "role": "analogy_metaphor",
     "title": "Analogy or metaphor within a declared scope",
     "objective": "recognize a bounded cross-domain comparison and select the "
                  "analogy that preserves the specified relationship",
     "public_request": "choose the example whose declared relationships match",
     "subtypes": ("preserves_scope", "same_words_wrong_links",
                  "different_words_right_links")},
    {"face": 4, "cue": "CUBE_FACE_4", "role": "explicit_correspondence",
     "title": "Explicit correspondence",
     "objective": "recognize and select the role and relationship mapping between "
                  "two presentations",
     "public_request": "choose the mapping that preserves the declared relations",
     "subtypes": ("edge_preserving", "endpoint_swapped", "child_edge_dropped")},
    {"face": 5, "cue": "CUBE_FACE_5", "role": "parts_structure",
     "title": "Parts and structural relationships",
     "objective": "recognize decomposition and correctly identify constituents "
                  "and their connections",
     "public_request": "list the parts directly inside the requested whole",
     "subtypes": ("direct_inventory", "indirect_intrusion",
                  "foreign_whole_part", "shared_constituent", "reach_kind")},
    {"face": 6, "cue": "CUBE_FACE_6", "role": "recomposition_process",
     "title": "Recomposition, story or bounded process",
     "objective": "recognize and select a valid account of how supplied parts or "
                  "steps form a whole, within the declared process semantics",
     "public_request": "choose the complete account of how these parts make the "
                       "whole",
     "subtypes": ("complete_recomposition", "missing_connection",
                  "foreign_part", "ordered_process")},
)

FACE_NUMBERS = tuple(role["face"] for role in ROLES)
CUES = tuple(role["cue"] for role in ROLES)
ROLE_BY_FACE = {role["face"]: role for role in ROLES}
ROLE_BY_CUE = {role["cue"]: role for role in ROLES}
ROLE_BY_NAME = {role["role"]: role for role in ROLES}

#: Every ordered pair of distinct roles, so the three-choice groups can be
#: rotated over all face pairs instead of reusing one permanent triple.
ROLE_PAIRS = tuple((a, b) for a in FACE_NUMBERS for b in FACE_NUMBERS if a != b)


def role_for(face):
    require(face in ROLE_BY_FACE, "FACE_ROLE_UNKNOWN:%r" % (face,))
    return ROLE_BY_FACE[face]


def cue_for(face, arm="stable"):
    """The in-input handle for a role under one comparison arm.

    ``stable`` gives every role its own marker; ``neutral`` gives all six the same
    one; ``none`` omits the marker entirely, which is the evaluation arm - the
    requested role is then stated in words, so the panel is identical for both
    comparison arms and doubles as the cue-removal diagnostic. Both arms keep the
    same request line, so the neutral arm can still solve every task and the
    comparison isolates the added value of the numbered marker rather than
    comparing semantics with no semantics.
    """
    role = role_for(face)
    require(arm in ("stable", "neutral", "none"), "FACE_CUE_ARM_UNKNOWN:" + str(arm))
    if arm == "none":
        return None
    return role["cue"] if arm == "stable" else NEUTRAL_CUE


def role_label(face):
    """The public option text used when three roles compete in recognition."""
    role = role_for(face)
    return "%d: %s" % (role["face"], role["title"].lower())


def other_faces(face, count=2, offset=1):
    """``count`` other roles, rotated over the five alternatives by ``offset``.

    The rotation runs over the ordered list of the *other* roles, so every offset
    selects a different group and no offset can fail to fill one. This is what
    keeps recognition groups from being one permanent triple.
    """
    require(face in FACE_NUMBERS, "FACE_ROLE_UNKNOWN:%r" % (face,))
    require(1 <= count < len(FACE_NUMBERS), "FACE_ROLE_GROUP_TOO_LARGE")
    others = [candidate for candidate in FACE_NUMBERS if candidate != face]
    start = offset % len(others)
    rotated = others[start:] + others[:start]
    return tuple(rotated[:count])


def registry_report():
    """The registry as data, for the manifest and the evidence packet."""
    return {"schema": SCHEMA, "neutral_cue": NEUTRAL_CUE,
            "task_profiles": list(TASK_PROFILES),
            "faces": [dict(role) for role in ROLES],
            "boundary": (
                "A face number is a categorical teaching handle, not a Noetic "
                "operator number, not a magnitude, and not a model input when the "
                "role is the thing being recognized.")}
