"""The construction decisions the learner makes, as finite declared choices.

The handoff is explicit that this is not a script pouring facts into six numbered
fields, and equally explicit about the boundary that makes the measurement real:

    The serializer may write the selected edits. A checker may reject unsupported
    edits. Neither may silently replace the learner's construction with the correct
    construction and then report that the model built it.

So every profile here produces a task with a **finite** choice space, keeps the
teacher's choice private on the task (never inside the learner's options), and
returns records that name who actually chose:

* ``producer: "learned_policy"`` only when a selection came back from the policy;
* ``producer: "authored_rule"`` when a declared rule chose - which is legitimate, and
  is recorded as such rather than dressed up as learning.

``apply_selection`` is the only path that turns a choice into cube edits, and it
refuses to run without a selection. ``substitute_teacher_choice`` exists solely so a
test can assert it raises: there is no supported way to swap the learner's
construction for the correct one.

Nothing here trains, scores or mutates a model.
"""
from __future__ import annotations

from . import diagnosis as dg

SCHEMA = "cas.rpm-cfc-constructor-policy-tasks/0.1"

#: The seven profiles, exactly as the implementation profile declares them.
PROFILES = ("GAP_ROUTE", "SOURCE_CHOICE", "CUBE_FIELD_EDIT", "CUBE_RELATION_EDIT",
            "CROSS_CUBE_MAP", "LEARNING_RECIPE", "CUBE_REVISION")

#: The routes a GAP_ROUTE choice may name, from the diagnosis stage.
ROUTE_CHOICES = tuple(dg.ROUTES)

#: The six face meanings, unchanged. A choice names a face, never a magnitude.
FACE_MEANINGS = {1: "technical_definition_and_function",
                 2: "context_environment_interactions",
                 3: "analogy_with_declared_scope",
                 4: "explicit_role_and_relation_correspondence",
                 5: "parts_and_structural_relationships",
                 6: "recomposition_or_bounded_process"}

#: Edit kinds a cube proposal may carry, and the fields each may touch.
EDIT_FIELDS = {"field": ("definition", "context", "analogy", "correspondence",
                         "parts", "recomposition", "identity_in_context"),
               "relation": ("contains", "is_part_of", "corresponds_to",
                            "analogous_to")}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def _options(values):
    """A finite choice space, in a deterministic order."""
    return sorted({str(value) for value in values})


# --------------------------------------------------------------------------
# choice spaces
# --------------------------------------------------------------------------

def choice_space(profile, context):
    """Every choice the profile allows here, and nothing outside it."""
    require(profile in PROFILES, "POLICY_PROFILE_UNKNOWN:" + str(profile))
    if profile == "GAP_ROUTE":
        return _options(ROUTE_CHOICES)
    if profile == "SOURCE_CHOICE":
        return _options(context.get("permitted_sources") or ())
    if profile == "CUBE_FIELD_EDIT":
        faces = _options(context.get("open_faces") or dg.FACES)
        fields = _options(EDIT_FIELDS["field"])
        return sorted("%s@%s" % (face, field) for face in faces for field in fields)
    if profile == "CUBE_RELATION_EDIT":
        return _options(context.get("relation_candidates") or ())
    if profile == "CROSS_CUBE_MAP":
        return _options(context.get("cross_cube_candidates") or ())
    if profile == "LEARNING_RECIPE":
        return _options(context.get("recipe_candidates") or ())
    return _options(context.get("revision_candidates") or ())


def compile_task(profile, context, *, teacher_choice, episode_id, task_id=None):
    """One task: the choices the learner may make, and the teacher's kept private.

    The teacher's choice is stored under ``teacher_target`` and never inside
    ``options``; the learner sees only the public problem and the finite choices.
    """
    require(profile in PROFILES, "POLICY_PROFILE_UNKNOWN:" + str(profile))
    options = choice_space(profile, context)
    require(options, "POLICY_CHOICE_SPACE_EMPTY:" + profile)
    require(str(teacher_choice) in options,
            "POLICY_TEACHER_CHOICE_OUTSIDE_THE_SPACE:%s:%s"
            % (profile, teacher_choice))
    public = {"profile": profile, "options": options,
              "context_keys": sorted(context)}
    task = {"schema": SCHEMA, "task_id": task_id or ("%s:%s" % (episode_id, profile)),
            "episode_id": episode_id, "task_profile": profile,
            "public": public, "options": options,
            "teacher_target": {"choice": str(teacher_choice),
                               "visibility": "teacher_private",
                               "never_inside_options": True}}
    dg.screen_learner_inputs(public)
    return task


def score_task(task, selection):
    """Whether a selection matches the teacher's, without revealing it."""
    require(task.get("schema") == SCHEMA, "POLICY_TASK_SCHEMA")
    require(selection is not None, "POLICY_SELECTION_REQUIRED")
    chosen = str(selection)
    require(chosen in task["options"], "POLICY_SELECTION_OUTSIDE_THE_SPACE:" + chosen)
    return {"task_id": task["task_id"], "profile": task["task_profile"],
            "selected": chosen, "correct": chosen == task["teacher_target"]["choice"]}


# --------------------------------------------------------------------------
# the boundary: a selection becomes edits, and only a selection does
# --------------------------------------------------------------------------

def apply_selection(task, selection, *, evidence_keys, cube_id=None, editor=None):
    """Turn the learner's selection into records, naming who chose.

    ``editor`` is the policy that chose. When it is None the selection is treated as
    an authored rule's - recorded honestly as such, never as the learner's.
    """
    require(task.get("schema") == SCHEMA, "POLICY_TASK_SCHEMA")
    require(selection is not None, "POLICY_SELECTION_REQUIRED")
    chosen = str(selection)
    require(chosen in task["options"], "POLICY_SELECTION_OUTSIDE_THE_SPACE:" + chosen)
    profile = task["task_profile"]
    producer = "learned_policy" if editor is not None else "authored_rule"
    record = {"schema": SCHEMA, "task_id": task["task_id"], "profile": profile,
              "selection": chosen, "producer": producer, "evidence_keys":
              sorted(evidence_keys), "score": score_task(task, chosen)}
    if profile == "CUBE_FIELD_EDIT":
        face, _, field = chosen.partition("@")
        record["edits"] = [{"kind": "field", "face": int(face), "field": field}]
    elif profile == "CUBE_RELATION_EDIT":
        source, _, rest = chosen.partition("->")
        target, _, predicate = rest.partition(":")
        record["edits"] = [{"kind": "relation", "source": source,
                            "target": target, "predicate": predicate}]
    elif profile == "CUBE_REVISION":
        record["edits"] = [{"kind": "field", "face": int(chosen.split("@")[0]),
                            "field": chosen.split("@")[1],
                            "revision": True}]
    else:
        record["edits"] = []
        record["decision"] = chosen
    if cube_id is not None and record["edits"]:
        for edit in record["edits"]:
            edit.setdefault("cube_id", cube_id)
        record["patch"] = dg.cube_patch(cube_id=cube_id, edits=record["edits"],
                                        producer=producer,
                                        evidence_keys=evidence_keys)
    return record


def substitute_teacher_choice(*_args, **_kwargs):
    """Deliberately unsupported.

    A serializer or checker that replaces the learner's construction with the correct
    one and reports that the learner built it is the failure this function exists to
    make impossible to call by accident.
    """
    raise ValueError("POLICY_TEACHER_SUBSTITUTION_IS_NOT_A_SUPPORTED_PATH")


def rejected(record, *, reason, checker="authored_checker"):
    """A checker refuses an edit. It does not repair it, and it does not replace it."""
    require(reason, "POLICY_REJECTION_REASON_REQUIRED")
    return {"schema": SCHEMA, "task_id": record.get("task_id"),
            "profile": record.get("profile"), "selection": record.get("selection"),
            "rejected": True, "reason": reason, "checker": checker,
            "learner_construction_preserved": True,
            "note": ("rejection is recorded against the learner's own selection; no "
                     "correct construction is written in its place")}


def profile_report():
    """What each profile lets the learner choose, for the record."""
    return {"schema": SCHEMA, "profiles": list(PROFILES),
            "routes": list(ROUTE_CHOICES), "faces": dict(FACE_MEANINGS),
            "edit_fields": {kind: list(fields)
                            for kind, fields in sorted(EDIT_FIELDS.items())},
            "teacher_substitution_supported": False}
