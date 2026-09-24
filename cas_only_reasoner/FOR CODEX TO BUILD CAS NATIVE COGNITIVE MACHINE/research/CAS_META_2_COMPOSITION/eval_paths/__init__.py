"""Opt-in evaluation paths that sit OUTSIDE the training launcher's input inventory.

The training launcher packages only `cncm/` and `research/CAS_META_2_COMPOSITION/cas_meta2/` source files
(`cas_meta2/typed_teaching/worker_contract.py:135-156`). This folder is outside both, so nothing here can change
what a training job ships or runs. Nothing here is imported by the default learner.
"""
