from __future__ import annotations

import torch
import pytest

from casformer import DifferentiableConductanceCircuit


DTYPE = torch.float64


def test_passive_circuit_solve_satisfies_the_regularized_nodal_equation():
    circuit = DifferentiableConductanceCircuit(damping=0.1, minimum_resistance=0.1)
    incidence = torch.tensor([[-1.0, 1.0]], dtype=DTYPE)
    resistance = torch.tensor([2.0], dtype=DTYPE, requires_grad=True)
    drive = torch.tensor([[[1.0], [-1.0]]], dtype=DTYPE, requires_grad=True)
    result = circuit(incidence, resistance, drive)
    assert torch.max(result.solve_residual.abs()).item() < 1e-12
    assert torch.equal(result.conductance, torch.tensor([[0.5]], dtype=DTYPE))
    assert torch.allclose(result.laplacian, result.laplacian.transpose(-2, -1))
    result.node_potential.square().sum().backward()
    assert torch.isfinite(resistance.grad).all()
    assert torch.isfinite(drive.grad).all()


def test_two_parallel_paths_equal_one_path_with_the_same_total_conductance():
    circuit = DifferentiableConductanceCircuit(damping=0.1, minimum_resistance=0.1)
    single_incidence = torch.tensor([[-1.0, 1.0]], dtype=DTYPE)
    parallel_incidence = torch.tensor([[-1.0, 1.0], [-1.0, 1.0]], dtype=DTYPE)
    drive = torch.tensor([[[1.0], [-1.0]]], dtype=DTYPE)
    single = circuit(single_incidence, torch.tensor([2.0], dtype=DTYPE), drive)
    parallel = circuit(
        parallel_incidence, torch.tensor([4.0, 4.0], dtype=DTYPE), drive
    )
    assert torch.allclose(single.node_potential, parallel.node_potential, atol=1e-12, rtol=1e-10)
    assert torch.allclose(single.laplacian, parallel.laplacian, atol=1e-12, rtol=1e-10)
    assert torch.allclose(
        single.edge_current.sum(dim=1),
        parallel.edge_current.sum(dim=1),
        atol=1e-12,
        rtol=1e-10,
    )


def test_circuit_rejects_zero_negative_and_nonfinite_resistance():
    circuit = DifferentiableConductanceCircuit()
    incidence = torch.tensor([[-1.0, 1.0]], dtype=DTYPE)
    drive = torch.zeros(1, 2, 1, dtype=DTYPE)
    for resistance in (0.0, -1.0, float("nan")):
        try:
            circuit(incidence, torch.tensor([resistance], dtype=DTYPE), drive)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid resistance {resistance!r} was accepted")


@pytest.mark.parametrize("field", ("damping", "minimum_resistance"))
def test_circuit_rejects_nonfinite_constructor_limits(field: str):
    values = {"damping": 1e-3, "minimum_resistance": 0.1}
    values[field] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        DifferentiableConductanceCircuit(**values)


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("damping", "damping"),
        ("minimum_resistance", "minimum_resistance"),
    ),
)
def test_circuit_rejects_limits_that_underflow_in_runtime_dtype(
    field: str, message: str
):
    values = {"damping": 0.1, "minimum_resistance": 0.1}
    values[field] = 1e-50
    circuit = DifferentiableConductanceCircuit(**values)
    incidence = torch.tensor([[-1.0, 1.0]])
    resistance = torch.tensor([1.0])
    drive = torch.tensor([[[1.0], [-1.0]]])

    with pytest.raises(ValueError, match=message):
        circuit(incidence, resistance, drive)


def test_circuit_rejects_nonfinite_reciprocal_conductance():
    smallest_positive = torch.nextafter(
        torch.tensor(0.0), torch.tensor(1.0)
    ).item()
    circuit = DifferentiableConductanceCircuit(
        damping=0.1, minimum_resistance=smallest_positive
    )
    incidence = torch.tensor([[-1.0, 1.0]])
    resistance = torch.tensor([smallest_positive])
    drive = torch.tensor([[[1.0], [-1.0]]])

    with pytest.raises(ValueError, match="conductance"):
        circuit(incidence, resistance, drive)


def test_circuit_rejects_damping_that_rounds_away_from_laplacian():
    circuit = DifferentiableConductanceCircuit(damping=5e-8, minimum_resistance=0.1)
    incidence = torch.tensor([[-1.0, 1.0]])
    resistance = torch.tensor([1.0])
    drive = torch.tensor([[[1.0], [-1.0]]])

    with pytest.raises(ValueError, match="survive addition"):
        circuit(incidence, resistance, drive)
