#!/usr/bin/env bash
# One-command runner for eta_epsilon_weight_learning_v0.1 (Phases 1-7).
# Requires: the cas-gpu venv (torch+cu, transformers), and the local
# Qwen/Qwen2.5-0.5B-Instruct snapshot (see ../MODEL_IDENTITY.json).
set -e
PY="${PY:-$HOME/venvs/cas-gpu/Scripts/python.exe}"
cd "$(dirname "$0")/.."
echo "== Phase 1 (CPU) =="; python -m pytest tests/test_phase1_realizer.py -q
echo "== Phase 2 readout =="; "$PY" src/phase2_capacity_probe.py; "$PY" src/phase2_correctness_readout.py
echo "== Phase 3 bridge =="; "$PY" src/phase3_activation_bridge.py
echo "== Phase 4 weights =="; "$PY" src/phase4_lora_weight_update.py
echo "== Phase 5 dose =="; "$PY" src/phase5_cas_ohm_dose.py
echo "== Phase 6 learning =="; "$PY" src/phase6_learning_benefit.py
echo "== Phase 7 consolidation =="; "$PY" src/phase7_consolidation.py
echo "All phases done. Raw results in reports/."
