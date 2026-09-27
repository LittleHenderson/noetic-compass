# HELM-Q1 delivery package

Prepared for Little Henderson on September 27, 2026.

## What is delivered

The full engineering directive specifies the classical/quantum boundary, Q0-Q7 implementation gates, later quantum-CAS research tracks, a 40-item required acceptance matrix, current cloud research, and source references. `HANDOFF_TO_EXISTING_LEADS.md` gives the starting assignment. `config/policy.json` defaults to no cloud execution and no spending.

The package also includes three runnable **offline** helpers: a dated price calculator, a fail-closed planning-policy checker, and a finite classical instruction-synthesis reference fixture. These are not a quantum backend, a HELM adapter, or a production authorization system. They do not contact any provider.

## Run the delivered helpers

Use Python 3.10 or later. No third-party packages or credentials are needed. In a terminal inside this extracted package:

```sh
python tools/q1_tools.py check-policy
python tools/q1_tools.py quote --device rigetti_cepheus --tasks 10 --shots 1000
python tools/q1_tools.py fixture-reference --length 3
python -m unittest discover -s tests -v
```

The price calculation should give a QPU-only total of $7.25 using the September 27 snapshot. It is not a live quote. The classical fixture examines 64 candidate programs over all four inputs. Its reference counts are evaluation data, not permission to build an answer-lookup oracle.

Read `receipts/DELIVERY_STATUS.json` and `receipts/helper_tests.txt` for actual execution status. The 40 required tests inside the directive are implementation obligations, not claimed HELM passes. The separate helper tests exercise only this package's new offline utilities.

## First action for the implementation team

Read the directive and handoff, reconcile the admitted HELM source and current ownership, and complete Q0. Preserve active training and existing budget/evidence custody. Do not submit cloud jobs or treat the illustrative $10 pilot as authorization.

No repository changes, provider enrollment, quantum-hardware calls, HELM runs, or paid resources were made by preparing this package.
