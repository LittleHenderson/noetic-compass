"""CAS_RDCJT_001 step two: the numerical wrapper over the shared transformation.

Step one (``recurrence.py``) is the arithmetic on plain Python lists: the reference
implementation, exact and cheap to test. It cannot be the training path, and the
reason is concrete rather than stylistic. ``feedback`` and ``reinjected`` coerce with
``float(value)``, and ``float()`` on a tensor DETACHES it from the autograd graph. A
list-based recurrence would therefore train the first pass, freeze passes two through
eight, and report a successful run. Step two is the numerical path, and it runs the
SAME loop: ``feedback`` and ``reinjected`` gained a ``cast`` hook whose default is
``float`` (so the reference path and its tests are unchanged), and the tensor path
passes an identity instead.

What this module adds:

* ``tensor_rms`` — the reference RMS formula, kept in the graph;
* ``RecurrentGraphLearner`` — the registered one-pass learner, subclassed, with the
  declared number of passes in front of its frozen dot-product readout. The encoding,
  the option vectors, the optimizer and the checkpoint identity are inherited
  untested-against-changes: at depth one the result is the existing computation,
  bitwise, which is asserted rather than asserted-about;
* ``recurrent_batch_step`` — one optimizer step per batch whatever the depth. Eight
  passes are eight sample passes and ONE update, never eight updates;
* ``depth_sweep`` — the fixed-weight R1 / R2 / R4 / R8 / RESET_8 sweep with the
  two-way tally, so gains and losses are both reported and a net-zero depth cannot
  hide behind an average.

Two things this module deliberately does NOT provide:

* **no depth selection.** ``recurrence.select_best_depth`` raises, and nothing here
  offers a way round it. The answer at depth eight is the answer at depth eight, even
  when it spoiled an answer that was correct at depth four;
* **no new trainable parameters.** The class adds a loop, a scale and an add. The
  optimizer is built over ``module.parameters()`` exactly as before, so added capacity
  cannot be what separates the two learners.

The state is allocated per question and starts at zero for each answer. It is carried
between the passes of ONE answer — that is the mechanism — and never between
questions, so an answer-bearing state cannot ride from a guided exercise into an
unassisted test. ``state_isolation_check`` measures that rather than claiming it.
"""
from __future__ import annotations

from collections import OrderedDict

from . import recurrence as rc
from ..graph_teaching.real_framework import GraphLearner

SCHEMA = "cas.recurrent-cjt-learner/0.1"

RESULT_SCHEMA = "cas.recurrent-cjt-sweep/1"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def _keep(value):
    """Identity cast: keeps a tensor in the autograd graph where ``float`` detaches."""
    return value


def tensor_rms(torch, values):
    """RMS with the same formula as ``recurrence.rms``, without leaving the graph.

    Accepts a 1-D tensor or a sequence of 0-dim tensors, because
    ``recurrence.run_passes`` hands the state back as a list.

    Plain numbers are REFUSED, deliberately. A state that has left the autograd graph
    arrives as plain floats, so promoting them here would hand back a detached RMS —
    the silent detach this wrapper exists to prevent, wearing a different hat. The
    caller who wants the reference path calls ``recurrence.rms``.
    """
    if torch.is_tensor(values):
        stacked = values
    else:
        entries = list(values)
        require(entries and all(torch.is_tensor(entry) for entry in entries),
                "TENSOR_RMS_REQUIRES_TENSORS:"
                + (type(entries[0]).__name__ if entries else "EMPTY"))
        stacked = torch.stack(entries)
    return torch.sqrt(torch.mean(stacked * stacked))


# --------------------------------------------------------------------------
# the learner
# --------------------------------------------------------------------------

class RecurrentGraphLearner(GraphLearner):
    """The registered one-pass learner with the declared passes in front of it.

    Subclassed, not rewritten. ``__init__``, the structural problem encoder, the
    option vectors, the content removal, the frozen readout, the AdamW optimizer and
    ``checkpoint_identity`` are the parent's, untouched. Three methods are overridden
    because they are the three places the problem vector reaches the module —
    ``forward``, ``predict`` and ``scores``. Overriding only ``forward`` would be a
    real bug rather than an oversight: ``predict`` and ``scores`` each encode the
    vector themselves on the on-demand path, so a reported answer could come from one
    pass while its reported scores came from eight.
    """

    def __init__(self, torch, framework, public_tasks, device, learning_rate,
                 depth=rc.PRIMARY_DEPTH, reset_each_pass=False, accounting=None):
        super().__init__(torch, framework, public_tasks, device, learning_rate)
        self.depth = None
        self.set_depth(depth)
        self.reset_each_pass = bool(reset_each_pass)
        self.accounting = accounting
        self.transformation_calls = 0   # real F_theta invocations
        self.questions_answered = 0     # calls to passes(), one per question

    # ---------------------------------------------------------------- depth

    def set_depth(self, depth):
        """Set the pass count for the next answer. An undeclared depth is refused."""
        require(depth in rc.DEPTHS, "RECURRENT_DEPTH_NOT_DECLARED:" + str(depth))
        self.depth = int(depth)
        return self.depth

    # ------------------------------------------------------- the recurrence

    def _core(self, incoming):
        """F_theta, the ONE shared transformation, called on whatever it is handed.

        Accepts the list of 0-dim tensors that ``run_passes`` produces and stacks it
        back into the batch shape the registered module expects.
        """
        torch = self.torch
        batched = incoming if torch.is_tensor(incoming) else torch.stack(list(incoming))
        # Counted HERE, at the real call site. It used to be incremented once per
        # passes() call, which is once per QUESTION: at depth eight that reported 1
        # where eight transformations had run, an eightfold understatement in a field
        # whose name promises the count of transformation calls. Accounting was always
        # right; this label was not.
        self.transformation_calls += 1
        return self.module(batched.unsqueeze(0))[0]

    def passes(self, encoded, *, state=None):
        """The final state after ``self.depth`` passes, as a 1-D tensor.

        This calls ``recurrence.run_passes`` itself rather than reimplementing the
        loop, so the reference arithmetic and the training path are one piece of code.
        The only differences are the RMS function and the cast.
        """
        torch = self.torch
        final = rc.run_passes(
            encoded, self._core, depth=self.depth, state=state,
            rms_fn=lambda values: tensor_rms(torch, values), cast=_keep,
            zeros=lambda count: torch.zeros(count, dtype=encoded.dtype,
                                            device=encoded.device),
            reset_each_pass=self.reset_each_pass)
        self.questions_answered += 1
        return torch.stack(list(final))

    def value_at_depth(self, *, problem_vector=None, public=None,
                       carried_state=None):
        """The final state for one question, from the indexed vector or on demand.

        The working state starts at zero here: one fresh state per answer, per
        question, nothing retained between questions. ``carried_state`` exists ONLY
        so the isolation check can hand a question a state borrowed from another one
        and show that the reading would have moved; no answering path supplies it.
        """
        if problem_vector is None:
            require(public is not None, "RECURRENT_INPUT_MISSING")
            problem_vector = self.framework.encoder["encode_problem"](public)
        return self.passes(problem_vector, state=carried_state)

    # ------------------------------------------- the three scoring entrances

    def forward(self, position):
        """The option scores for one indexed question, from the declared depth."""
        value = self.value_at_depth(
            problem_vector=self._problem_vectors[position])
        return self.torch.stack([self.torch.dot(value, vector)
                                 for vector in self._option_vectors[position]])

    def predict(self, task_input):
        """The selected option. The same readout, on the final state."""
        torch = self.torch
        if task_input["record_id"] in self._index:
            position = self._position(task_input)
            scores = self.forward(position)
            return self.tasks[position]["encoded_options"][
                int(torch.argmax(scores).item())]
        _problem_ids, slot_ids = self.framework.encoder["encode"](
            task_input["public"])
        value = self.value_at_depth(public=task_input["public"])
        content = self._content_ids(slot_ids)
        zero = torch.zeros_like(value)
        scores = torch.stack([torch.dot(value, self._sum(item) if item else zero)
                              for item in content])
        return task_input["encoded_options"][int(torch.argmax(scores).item())]

    def scores(self, task):
        """The option scores and the loss for one task, on the final state.

        The returned keys are the parent's exactly. A field only one condition's rows
        carried would be a difference between the two learners that is not part of
        the manipulation, and the depth is recorded in the sweep report instead.
        """
        torch = self.torch
        indexed = task["record_id"] in self._index
        if indexed:
            position = self._position(task)
            value = self.value_at_depth(
                problem_vector=self._problem_vectors[position])
            option_vectors = self._option_vectors[position]
        else:
            _problem_ids, slot_ids = self.framework.encoder["encode"](task["public"])
            value = self.value_at_depth(public=task["public"])
            zero = torch.zeros_like(value)
            option_vectors = [self._sum(item) if item else zero
                              for item in self._content_ids(slot_ids)]
        scores = torch.stack([torch.dot(value, vector) for vector in option_vectors])
        correct = task.get("encoded_correct_index")
        if correct is None and indexed:
            correct = self.tasks[position]["encoded_correct_index"]
        loss = None
        if type(correct) is int and 0 <= correct < int(scores.shape[0]):
            loss = float(torch.nn.functional.cross_entropy(
                scores.unsqueeze(0),
                torch.tensor([correct], device=self.device)).item())
        return {"scores": [round(float(score.detach()), 6) for score in scores],
                "loss": loss, "correct_index": correct,
                "path": "indexed" if indexed else "on_demand",
                "option_count": int(scores.shape[0])}

    # ------------------------------------------------------------ reporting

    def depth_report(self):
        return {"schema": SCHEMA, "depth": self.depth,
                "reset_each_pass": self.reset_each_pass,
                "transformation_calls": self.transformation_calls,
                "questions_answered": self.questions_answered,
                "transformation_calls_meaning": (
                    "invocations of the shared core F_theta, counted at the call "
                    "site; at depth d one question contributes d of these"),
                "trainable_parameters": len(
                    [1 for _ in self.module.named_parameters()]),
                "state_scope": "one fresh zero state per answer, per question",
                "accounting": (self.accounting.report()
                               if self.accounting is not None else None)}


def build_recurrent_learner(torch, framework, tasks, device, learning_rate,
                            *, depth=rc.PRIMARY_DEPTH, reset_each_pass=False,
                            accounting=None):
    """The factory the course and the readout both call, so they cannot diverge."""
    return RecurrentGraphLearner(torch, framework, tasks, device, learning_rate,
                                 depth=depth, reset_each_pass=reset_each_pass,
                                 accounting=accounting)


# --------------------------------------------------------------------------
# one optimizer step per batch, whatever the depth
# --------------------------------------------------------------------------

def recurrent_batch_step(learner, tasks_in_batch, *, accounting=None):
    """One optimizer step for a batch, at the learner's current depth.

    The loss is the mean of the episodes' cross-entropies, so a batch of eight is ONE
    update whatever the depth. The per-episode scores returned here are the ones this
    pass computed and back-propagated, the same rule the one-pass batching path
    follows: the recording path never takes an independent later forward call.

    This mirrors ``face_experiment.batch_step`` field for field on the keys the
    recording path reads, and adds only the depth on the batch envelope.
    """
    torch = learner.torch
    require(tasks_in_batch, "RECURRENT_BATCH_EMPTY")
    depth = learner.depth
    losses, episodes = [], []
    learner.optimizer.zero_grad(set_to_none=True)
    for task in tasks_in_batch:
        position = learner._position(task)
        scores = learner.forward(position)
        correct = learner.tasks[position]["encoded_correct_index"]
        loss = torch.nn.functional.cross_entropy(
            scores.unsqueeze(0),
            torch.tensor([correct], device=learner.device))
        losses.append(loss)
        selected = int(torch.argmax(scores).item())
        episodes.append({
            "scores": [round(float(value.detach()), 6) for value in scores],
            "loss": float(loss.detach()),
            "correct_index": int(correct),
            "selected_index": selected,
            "selected": task["encoded_options"][selected],
            "option_count": int(scores.shape[0])})
    total = sum(losses) / len(losses)
    total.backward()
    learner.optimizer.step()
    account = accounting if accounting is not None else learner.accounting
    if account is not None:
        account.charge(depth=depth, samples=len(tasks_in_batch))
        account.update()
    return {"batch_size": len(tasks_in_batch), "optimizer_steps": 1, "depth": depth,
            "mean_loss": float(total.detach()), "episodes": episodes}


# --------------------------------------------------------------------------
# the fixed-weight depth sweep
# --------------------------------------------------------------------------

def depth_and_reset(label):
    """Evaluation label to (passes, state discarded between passes)."""
    plan = rc.evaluation_depth_plan()
    require(label in plan, "EVALUATION_DEPTH_UNKNOWN:" + str(label))
    return plan[label]["depth"], plan[label]["reset_each_pass"]


def correctness_by_question(rows):
    return OrderedDict((row["item_id"], bool(row["is_correct"])) for row in rows)


def depth_sweep(*, learner, items, evaluate_panel, built=None,
                labels=rc.EVALUATION_DEPTHS):
    """Answer the frozen panel at every declared depth, with the weights fixed.

    ``evaluate_panel`` is injected (``face_experiment.evaluate_panel`` in the deployed
    path) so this function holds no torch and no panel compilation of its own. The
    parameter digest is taken before and after, so "the weights did not move" is a
    reading rather than an assurance.
    """
    identity_before = learner.checkpoint_identity()
    rows = OrderedDict()
    for label in labels:
        depth, reset = depth_and_reset(label)
        learner.set_depth(depth)
        learner.reset_each_pass = reset
        rows[label] = evaluate_panel(learner=learner, items=items, built=built,
                                     phase=label)
    learner.reset_each_pass = False
    learner.set_depth(rc.PRIMARY_DEPTH)
    identity_after = learner.checkpoint_identity()
    return {"schema": RESULT_SCHEMA, "rows": rows,
            "weights_unchanged": identity_before == identity_after,
            "parameter_digest_before": identity_before,
            "parameter_digest_after": identity_after,
            "labels": list(rows),
            "report": sweep_report(rows)}


def sweep_report(rows):
    """The two-way tally, plus the RESET_8 mechanism check.

    The tally is paired on the question against the one-pass baseline and reports
    gains AND losses per depth, because a depth that fixes two questions and spoils
    two is a net-zero result that a single pooled average would hide.
    """
    require("R1" in rows, "SWEEP_REQUIRES_THE_ONE_PASS_BASELINE")
    carried = {depth_and_reset(label)[0]: correctness_by_question(payload)
               for label, payload in rows.items() if label != "RESET_8"}
    tally = rc.two_way_tally(carried)
    report = {"tally": tally,
              "per_depth": OrderedDict(
                  (label, {"depth": depth_and_reset(label)[0],
                           "reset_each_pass": depth_and_reset(label)[1],
                           "correct": sum(1 for value
                                          in correctness_by_question(payload).values()
                                          if value),
                           "total": len(payload)})
                  for label, payload in rows.items()),
              "depth_selection": ("none: the answer at each depth is that depth's "
                                  "answer, and no checker chooses between them"),
              "gains_and_losses_separate": True}
    if "RESET_8" in rows:
        reset = correctness_by_question(rows["RESET_8"])
        one = correctness_by_question(rows["R1"])
        differing = sorted(key for key in set(reset) | set(one)
                           if reset.get(key) != one.get(key))
        report["reset_8_mechanism_check"] = {
            "identical_to_r1": not differing,
            "differing_items": differing,
            "meaning": ("RESET_8 discards the state between passes, so under a "
                        "deterministic transformation it must reproduce R1 exactly. "
                        "Any difference is a finding, not a tolerated tolerance: it "
                        "means the model is not deterministic between passes, e.g. "
                        "dropout was enabled, and then this row measures that and not "
                        "the mechanism.")}
    return report


def state_isolation_check(*, learner, position, other_position):
    """Does answering one question change the next answer? It must not.

    Four readings, and the last one is what gives the first three their power.
    Answering B twice is repeatable. Answering A in between leaves B unchanged. And B
    answered from an explicitly BORROWED state does move, so a leak would have been
    visible here rather than silently passing. The learner's own answering paths never
    supply that borrowed state — ``forward``, ``predict`` and ``scores`` all call
    ``value_at_depth`` without one — which is why the fourth reading is a test of the
    test and not a demonstration of contamination in the delivered path.

    Requires a carried-state setting: with ``reset_each_pass`` on, every pass discards
    the state, so there is nothing that could leak and the check would be vacuous.
    """
    require(not learner.reset_each_pass,
            "ISOLATION_CHECK_REQUIRES_A_CARRIED_STATE")
    torch = learner.torch
    vector_b = learner._problem_vectors[position]
    vector_a = learner._problem_vectors[other_position]
    first = learner.value_at_depth(problem_vector=vector_b)
    second = learner.value_at_depth(problem_vector=vector_b)
    learner.value_at_depth(problem_vector=vector_a)
    third = learner.value_at_depth(problem_vector=vector_b)
    borrowed = learner.value_at_depth(
        problem_vector=vector_b, carried_state=learner.passes(vector_a))
    return {"repeatable": bool(torch.equal(first, second)),
            "order_independent": bool(torch.equal(first, third)),
            "a_borrowed_state_would_have_been_visible":
                not bool(torch.equal(first, borrowed)),
            "depth": learner.depth,
            "state_scope": ("allocated inside each answer, starting at zero; no "
                            "answering path accepts a state from another question"),
            "boundary": ("this checks that questions do not contaminate each other "
                         "within one learner; it says nothing about a state being "
                         "retained across optimizer steps, which is a mode this "
                         "candidate does not implement")}


def sweep_deliverable(payload, *, job, plan=None):
    """The sweep's delivered envelope: full rows first, then the summary."""
    return {"schema": RESULT_SCHEMA, "job": job, "plan": plan or {},
            "weights_unchanged": payload["weights_unchanged"],
            "parameter_digest_before": payload["parameter_digest_before"],
            "parameter_digest_after": payload["parameter_digest_after"],
            "labels": payload["labels"],
            "report": payload["report"],
            "rows": dict(payload["rows"]),
            "boundary": {
                "optimizer_updates_during_sweep": 0,
                "training_performed": False,
                "each_panel_item_is_computed_twice": (
                    "face_experiment._score_task calls predict and then scores, and "
                    "each does its own passes; the sweep's cost is therefore per "
                    "answered question, not per reported row"),
                "weights_measured_not_assumed": True,
                "depth_selection_by_checker": False,
                "automatic_retries": 0}}
