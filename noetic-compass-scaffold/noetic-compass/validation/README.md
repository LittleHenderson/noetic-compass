# Validation Framework

Reproducibility and sensitivity tests for the Noetic Compass CAS pipeline.

## Tests

- **reproducibility_test.py** — Verifies deterministic mock scoring (identical inputs produce identical outputs) and benchmark fixture compliance.
- **sensitivity_test.py** — Verifies that the pipeline responds to dial changes, prompt variation, and that domain averages satisfy open simplex constraints.

## Usage

```bash
# From project root
make validate

# Or directly
pytest validation/ -v
```

## Benchmark Fixture

`benchmark_fixture.json` contains a frozen reference input and expected output ranges. The reproducibility test checks that the pipeline produces results within these bounds.
