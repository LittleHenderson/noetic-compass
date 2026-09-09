"""Prepared neural diagnostic for the ln(3) flat-loss symptom.

Neural execution requires separate owner authorization; this module is the
fail-closed measurement spec. It runs ONLY inside an authorized AWS job and
measures the quantities the non-neural diagnostic cannot:

  1. per-record three scores and their spread (after the frozen projection,
     mean-pooling, the ^6 module, and the fixed readout),
  2. pairwise cosine similarity among the three option vectors and between
     the problem vector and each option vector,
  3. a same-example, alternative-target gradient test: loss values and
     per-matrix gradient norms (left.weight, merge.weight, right.weight) for
     each of the three targets, WITHOUT any optimizer step.

No weights are updated. Results are returned as a JSON-safe report for the
authorized run's evidence path.
"""
from __future__ import annotations

from .graph import require

DIAGNOSTIC_SCHEMA = "cas-graph-training-ln3-neural-diagnostic/1"


def _option_vectors(learner, position):
    return learner._option_vectors[position]


def _problem_vector(learner, position):
    return learner._problem_vectors[position]


def measure_scores(learner):
    """Three scores + spread per record (no updates)."""
    rows = []
    for position, task in enumerate(learner.tasks):
        scores = learner.forward(position)
        rows.append({
            "record_id": task["record_id"], "op": task["op"],
            "scores": [float(value.item()) for value in scores],
            "spread": float((scores.max() - scores.min()).item()),
            "correct_slot": task["encoded_correct_index"],
            "correct_score": float(scores[task["encoded_correct_index"]].item())})
    return rows


def measure_option_geometry(learner):
    """Pairwise cosine among option vectors; problem-option cosine."""
    rows = []
    for position, task in enumerate(learner.tasks):
        options = _option_vectors(learner, position)
        problem = _problem_vector(learner, position)

        def cosine(a, b):
            dot = float(learner.torch.dot(a, b).item())
            norm_a = float(learner.torch.linalg.vector_norm(a).item())
            norm_b = float(learner.torch.linalg.vector_norm(b).item())
            return dot / (norm_a * norm_b + 1e-12)

        option_pairs = [cosine(options[i], options[j])
                        for i in range(3) for j in range(i + 1, 3)]
        problem_option = [cosine(problem, option) for option in options]
        rows.append({"record_id": task["record_id"], "op": task["op"],
                     "option_pair_cosines": option_pairs,
                     "problem_option_cosines": problem_option})
    return rows


def measure_gradient_test(learner, position):
    """Same example, three alternative targets, NO optimizer step.

    Returns per-target loss and per-matrix gradient norms. Weight decay is
    0.0 in the learner, so any parameter movement in the recorded pilot came
    from these task gradients.
    """
    task = learner.tasks[position]
    scores = learner.forward(position)
    module = learner.module
    results = []
    for target in (0, 1, 2):
        module.zero_grad()
        loss = learner.torch.nn.functional.cross_entropy(
            scores.unsqueeze(0),
            learner.torch.tensor([target], device=learner.device))
        loss.backward()
        norms = {}
        for name, parameter in module.named_parameters():
            if parameter.grad is not None:
                norms[name] = float(
                    learner.torch.linalg.vector_norm(parameter.grad).item())
        results.append({"target": target,
                        "loss": float(loss.item()),
                        "gradient_norms": norms,
                        "correct_target": task["encoded_correct_index"]})
    return {"record_id": task["record_id"], "op": task["op"], "results": results}


def launch(*, run_id, learner):
    """Authorized-run measurement; no updates are performed."""
    require(type(run_id) is str and run_id, "RUN_ID_REQUIRED")
    require(learner is not None, "LEARNER_REQUIRED")
    report = {"schema": DIAGNOSTIC_SCHEMA, "run_id": run_id,
              "scores": measure_scores(learner),
              "option_geometry": measure_option_geometry(learner),
              "gradient_test": [measure_gradient_test(learner, position)
                                for position in range(min(3, len(learner.tasks)))],
              "boundary": ("measurement only; no optimizer step was taken; "
                           "weights unchanged by this diagnostic")}
    return report
