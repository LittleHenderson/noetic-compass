"""Tests for CASTrainer._eval_step (added 2026-04-29).

Two tiers:

- **AST tier** (always runs): structural checks that don't need torch — verifies
  ``_eval_step`` exists on CASTrainer, calls the shared forward+loss helper,
  uses ``torch.no_grad()``, and does NOT contain backward / optimizer.step /
  scheduler.step / optimizer.zero_grad calls in its body. Catches regression
  if the method is accidentally collapsed back into ``_train_step``.

- **Runtime tier** (skipped when torch.utils unavailable in local env): build
  a minimal CASTrainer on a tiny model, call ``_eval_step``, verify
  (a) parameters don't change, (b) it runs cleanly inside ``torch.no_grad()``,
  (c) the loss components dict matches the keys produced by ``_train_step``
  (loss-function parity).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINER_PATH = REPO_ROOT / "cas-native" / "training" / "trainer.py"


def _trainer_module_ast():
    return ast.parse(TRAINER_PATH.read_text(encoding="utf-8"))


def _find_method(tree: ast.AST, class_name: str, method_name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return item
    return None


def _executable_body(method: ast.FunctionDef) -> list[ast.stmt]:
    """Return method body excluding the leading docstring (if any)."""
    body = method.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        return body[1:]
    return body


# ---------------------------------------------------------------- AST tier

class TestEvalStepStructure:
    """AST-level structural checks. Run anywhere, no torch dependency."""

    def test_eval_step_method_exists(self):
        tree = _trainer_module_ast()
        method = _find_method(tree, "CASTrainer", "_eval_step")
        assert method is not None, "CASTrainer._eval_step must exist"

    def test_compute_helper_method_exists(self):
        tree = _trainer_module_ast()
        method = _find_method(tree, "CASTrainer", "_compute_forward_and_loss_components")
        assert method is not None, "CASTrainer._compute_forward_and_loss_components must exist"

    def test_eval_step_calls_shared_helper(self):
        tree = _trainer_module_ast()
        method = _find_method(tree, "CASTrainer", "_eval_step")
        body_src = ast.unparse(method)
        assert "_compute_forward_and_loss_components" in body_src, (
            "_eval_step must reuse the shared forward+loss helper for parity with _train_step"
        )

    def test_eval_step_uses_no_grad(self):
        tree = _trainer_module_ast()
        method = _find_method(tree, "CASTrainer", "_eval_step")
        body_src = ast.unparse(_executable_body(method))
        assert "torch.no_grad" in body_src, (
            "_eval_step must wrap forward+loss in torch.no_grad() to avoid grad_fn errors"
        )

    @pytest.mark.parametrize("forbidden", [
        ".backward()",
        "optimizer.step",
        "scheduler.step",
        "optimizer.zero_grad",
    ])
    def test_eval_step_body_excludes_gradient_calls(self, forbidden):
        """_eval_step must NOT call backward/optimizer/scheduler — the bug
        from 2026-04-28 was that the runner called _train_step inside no_grad,
        and _train_step's internal backward() failed. A correct _eval_step
        omits gradient-application code entirely.
        """
        tree = _trainer_module_ast()
        method = _find_method(tree, "CASTrainer", "_eval_step")
        body_stmts = _executable_body(method)
        for stmt in body_stmts:
            stmt_src = ast.unparse(stmt)
            assert forbidden not in stmt_src, (
                f"_eval_step body must not contain {forbidden!r}; found in:\n{stmt_src}"
            )

    def test_train_step_still_has_backward_and_step(self):
        """Sanity: the refactor preserves _train_step's gradient application."""
        tree = _trainer_module_ast()
        method = _find_method(tree, "CASTrainer", "_train_step")
        body_src = ast.unparse(_executable_body(method))
        assert ".backward()" in body_src
        assert "optimizer.step" in body_src
        assert "scheduler.step" in body_src

    def test_components_to_metrics_accepts_python_float_scalars(self):
        """production_weight is a Python float; metrics must not drop it."""
        tree = _trainer_module_ast()
        method = _find_method(tree, "CASTrainer", "_components_to_metrics")
        body_src = ast.unparse(_executable_body(method))
        assert "float(v)" in body_src
        assert "TypeError" in body_src
        assert "ValueError" in body_src

    def test_run_v2_full_defaults_fire_eval_for_batch_128_run(self):
        """Batch=128 gives 189 steps; eval/checkpoint defaults must fire."""
        run_path = REPO_ROOT / "cas-native" / "training" / "run_v2_full.py"
        run_src = run_path.read_text(encoding="utf-8")
        assert 'CAS_V2_BATCH_SIZE", 128' in run_src
        assert 'CAS_V2_EVAL_EVERY", 100' in run_src
        assert 'CAS_V2_CHECKPOINT_EVERY", 100' in run_src
        assert 'CAS_V2_PRODUCTION_WARMUP", 100' in run_src


# ------------------------------------------------------------ runtime tier
#
# Skipped at class level when torch.utils is unavailable (known local env
# block). The class-level skip lets the AST-tier tests above still run.

def _torch_runtime_available() -> bool:
    try:
        import torch  # noqa: F401
        import torch.utils  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.fixture
def tiny_setup():
    import torch
    from cas_native.training.config import (
        TrainingConfig, V2ComponentFlags, V74Hyperparameters,
    )
    from cas_native.training.trainer import CASTrainer
    from cas_native.model import CASNativeModel, CASNativeConfig
    """Build a minimal CASTrainer + 2-batch synthetic data for runtime tests."""
    model = CASNativeModel(CASNativeConfig())
    # Synthetic 2-record dataset using a simple list-backed loader.
    # Each "batch" is a dict with the keys CASDataset.__getitem__ produces.
    # Build via the actual data pipeline so labels are realistic.
    from cas_native.training.data_pipeline import (
        CASDataset, cas_collate_fn,
    )
    from torch.utils.data import DataLoader

    data = [
        {
            "prompt": "tiny",
            "response": "test",
            "cas_expression": "^2^P_{F2}",
            "scores": {"operator_scores": [0]*2 + [1] + [0]*7, "domain_scores": [1, 0, 0, 0]},
        },
        {
            "prompt": "another",
            "response": "example",
            "cas_expression": "^5^C_{F4}",
            "scores": {"operator_scores": [0]*5 + [1] + [0]*4, "domain_scores": [0, 1, 0, 0]},
        },
    ]
    train_loader = DataLoader(CASDataset(data), batch_size=2, collate_fn=cas_collate_fn)
    val_loader = DataLoader(CASDataset(data), batch_size=2, collate_fn=cas_collate_fn)

    cfg = TrainingConfig(
        component_flags=V2ComponentFlags(),  # all v2 off — keeps runtime fast
        v7_4_hyperparameters=V74Hyperparameters(lr=1e-4, warmup_steps=10, max_steps=10),
    )
    trainer = CASTrainer(model=model, train_loader=train_loader, val_loader=val_loader, config=cfg)
    return trainer, train_loader, val_loader


@pytest.mark.skipif(not _torch_runtime_available(), reason="torch.utils unavailable (known local env issue)")
class TestEvalStepRuntime:
    """Runtime checks. Skipped if torch.utils blocked locally."""

    def test_eval_step_does_not_modify_parameters(self, tiny_setup):
        import torch
        """_eval_step must not change any model parameter (no backward, no step)."""
        trainer, _, val_loader = tiny_setup
        snapshot = {n: p.detach().clone() for n, p in trainer.model.named_parameters()}
        batch = next(iter(val_loader))
        metrics = trainer._eval_step(batch)
        assert isinstance(metrics, dict) and "total" in metrics
        for n, p in trainer.model.named_parameters():
            assert torch.equal(snapshot[n], p), (
                f"parameter {n} mutated by _eval_step (forward-only must not update params)"
            )

    def test_eval_step_runs_inside_caller_no_grad_context(self, tiny_setup):
        """Caller may already be inside torch.no_grad(); _eval_step still works."""
        import torch
        trainer, _, val_loader = tiny_setup
        batch = next(iter(val_loader))
        with torch.no_grad():
            metrics = trainer._eval_step(batch)
        assert "total" in metrics
        # No grad_fn errors should propagate; loss is finite.
        assert not (metrics["total"] != metrics["total"])  # not NaN

    def test_eval_step_metrics_match_train_step_keys(self, tiny_setup):
        """_eval_step and _train_step must compute the same loss components.

        Both call _compute_forward_and_loss_components, so the resulting
        keys (modulo train-only side-effect keys like current_tau which both
        emit) must be identical. This is the loss-function parity check.
        """
        trainer, train_loader, val_loader = tiny_setup
        batch = next(iter(train_loader))
        # Run a train step first to advance optimizer state.
        train_metrics = trainer._train_step(batch)
        eval_metrics = trainer._eval_step(batch)
        # Set semantics: same keys (lr / current_tau included in both).
        assert set(train_metrics.keys()) == set(eval_metrics.keys()), (
            f"key parity broken — train-only: {set(train_metrics) - set(eval_metrics)}, "
            f"eval-only: {set(eval_metrics) - set(train_metrics)}"
        )
