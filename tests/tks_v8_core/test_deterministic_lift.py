from __future__ import annotations

from itertools import product
from math import sqrt
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tks_v8_core import (  # noqa: E402
    DeterministicLift,
    FiniteArrow,
    FiniteObject,
    ValidationError,
    compose,
    identity,
)


def matrix_vector_product(
    matrix: tuple[tuple[int, ...], ...], vector: tuple[int, ...]
) -> tuple[int, ...]:
    return tuple(sum(entry * value for entry, value in zip(row, vector)) for row in matrix)


def square_matrix_product(
    left: tuple[tuple[int, ...], ...], right: tuple[tuple[int, ...], ...]
) -> tuple[tuple[int, ...], ...]:
    if not left:
        return ()
    size = len(left)
    return tuple(
        tuple(sum(left[i][k] * right[k][j] for k in range(size)) for j in range(size))
        for i in range(size)
    )


def transpose(matrix: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    if not matrix:
        return ()
    return tuple(
        tuple(matrix[row][column] for row in range(len(matrix)))
        for column in range(len(matrix[0]))
    )


def rectangular_matrix_product(
    left: tuple[tuple[int, ...], ...],
    right: tuple[tuple[int, ...], ...],
    *,
    inner_size: int,
    column_count: int,
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(
            sum(left[row][inner] * right[inner][column] for inner in range(inner_size))
            for column in range(column_count)
        )
        for row in range(len(left))
    )


class DeterministicLiftTests(unittest.TestCase):
    def test_two_state_constant_map_is_permanent_counterexample(self) -> None:
        x = FiniteObject("X", (0, 1))
        arrow = FiniteArrow("constant", x, x, (0, 0))
        lift = DeterministicLift(arrow)

        self.assertEqual(lift.matrix(), ((1, 1), (0, 0)))
        self.assertEqual(lift.input_gram_matrix(), ((1, 1), (1, 1)))
        self.assertEqual(lift.output_gram_matrix(), ((2, 0), (0, 0)))
        self.assertEqual(lift.output_support_projector(), ((1, 0), (0, 0)))
        self.assertEqual(lift.operator_norm_squared, 2)
        self.assertEqual(lift.operator_norm, sqrt(2))
        self.assertEqual(lift.trace_input_gram, 2)
        self.assertEqual(lift.rank, 1)
        self.assertTrue(lift.is_idempotent)
        self.assertFalse(lift.is_partial_isometry)
        self.assertFalse(lift.is_orthogonal_projector)

    def test_lift_application_and_adjoint_are_typed_by_vector_length(self) -> None:
        x = FiniteObject("X", (0, 1, 2))
        y = FiniteObject("Y", ("a", "b"))
        lift = DeterministicLift(FiniteArrow("f", x, y, (0, 1, 0)))
        self.assertEqual(lift.apply((2, 3, 5)), (7, 3))
        self.assertEqual(lift.adjoint_apply((11, 13)), (11, 13, 11))
        with self.assertRaises(ValidationError):
            lift.apply({2, 3, 5})
        with self.assertRaises(ValidationError):
            lift.adjoint_apply({11, 13})

    def test_nonidentity_permutation_is_isometry_but_not_projector(self) -> None:
        x = FiniteObject("X", (0, 1, 2))
        lift = DeterministicLift(FiniteArrow("cycle", x, x, (1, 2, 0)))
        self.assertTrue(lift.is_injective)
        self.assertTrue(lift.is_isometry)
        self.assertTrue(lift.is_partial_isometry)
        self.assertFalse(lift.is_idempotent)
        self.assertFalse(lift.is_orthogonal_projector)

    def test_partial_isometry_and_projector_classification_exhaustively(self) -> None:
        checked = 0
        for size in range(5):
            carrier = FiniteObject(f"N{size}", tuple(range(size)))
            mappings = [()] if size == 0 else product(range(size), repeat=size)
            for mapping in mappings:
                lift = DeterministicLift(
                    FiniteArrow("f", carrier, carrier, tuple(mapping))
                )
                matrix = lift.matrix()
                gram = lift.input_gram_matrix()
                gram_is_projector = square_matrix_product(gram, gram) == gram
                matrix_is_orthogonal_projector = (
                    square_matrix_product(matrix, matrix) == matrix
                    and transpose(matrix) == matrix
                )
                self.assertEqual(lift.is_partial_isometry, gram_is_projector)
                self.assertEqual(
                    lift.is_orthogonal_projector,
                    matrix_is_orthogonal_projector,
                )
                checked += 1
        self.assertEqual(checked, 289)

    def test_correct_norm_and_gram_structure_exhaustively_for_small_maps(self) -> None:
        checked = 0
        for source_size in range(5):
            for target_size in range(5):
                if source_size and not target_size:
                    continue
                source = FiniteObject(f"X{source_size}", tuple(range(source_size)))
                target = FiniteObject(f"Y{target_size}", tuple(range(target_size)))
                mappings = (
                    [()]
                    if source_size == 0
                    else product(range(target_size), repeat=source_size)
                )
                for mapping in mappings:
                    arrow = FiniteArrow("f", source, target, tuple(mapping))
                    lift = DeterministicLift(arrow)
                    sizes = tuple(mapping.count(y) for y in range(target_size))
                    expected_max = max(sizes, default=0)
                    self.assertEqual(lift.fiber_sizes, sizes)
                    self.assertEqual(lift.operator_norm_squared, expected_max)
                    self.assertEqual(lift.trace_input_gram, source_size)
                    self.assertEqual(lift.rank, sum(size > 0 for size in sizes))
                    self.assertEqual(lift.is_isometry, len(set(mapping)) == source_size)

                    gram = lift.input_gram_matrix()
                    self.assertEqual(
                        gram,
                        tuple(
                            tuple(int(mapping[i] == mapping[j]) for j in range(source_size))
                            for i in range(source_size)
                        ),
                    )
                    if expected_max:
                        maximal_fiber = sizes.index(expected_max)
                        witness = tuple(int(image == maximal_fiber) for image in mapping)
                        self.assertEqual(
                            matrix_vector_product(gram, witness),
                            tuple(expected_max * value for value in witness),
                        )
                    checked += 1
        self.assertEqual(checked, 499)

        for size in range(5):
            carrier = FiniteObject(f"I{size}", tuple(range(size)))
            matrix = DeterministicLift(identity(carrier)).matrix()
            self.assertEqual(
                matrix,
                tuple(
                    tuple(int(row == column) for column in range(size))
                    for row in range(size)
                ),
            )

        composition_pairs = 0
        for source_size in range(4):
            for middle_size in range(4):
                if source_size and not middle_size:
                    continue
                source = FiniteObject(f"FX{source_size}", tuple(range(source_size)))
                middle = FiniteObject(f"FY{middle_size}", tuple(range(middle_size)))
                f_mappings = (
                    [()]
                    if source_size == 0
                    else list(product(range(middle_size), repeat=source_size))
                )
                for target_size in range(4):
                    if middle_size and not target_size:
                        continue
                    target = FiniteObject(f"FZ{target_size}", tuple(range(target_size)))
                    g_mappings = (
                        [()]
                        if middle_size == 0
                        else list(product(range(target_size), repeat=middle_size))
                    )
                    for f_mapping in f_mappings:
                        f = FiniteArrow("f", source, middle, tuple(f_mapping))
                        f_matrix = DeterministicLift(f).matrix()
                        for g_mapping in g_mappings:
                            g = FiniteArrow("g", middle, target, tuple(g_mapping))
                            g_matrix = DeterministicLift(g).matrix()
                            composed_matrix = DeterministicLift(compose(g, f)).matrix()
                            self.assertEqual(
                                composed_matrix,
                                rectangular_matrix_product(
                                    g_matrix,
                                    f_matrix,
                                    inner_size=middle_size,
                                    column_count=source_size,
                                ),
                            )
                            composition_pairs += 1
        self.assertEqual(composition_pairs, 1_678)


if __name__ == "__main__":
    unittest.main()
