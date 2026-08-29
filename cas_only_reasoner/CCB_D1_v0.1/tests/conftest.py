import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
LANE = os.path.dirname(BOARD)
for path in (BOARD, os.path.join(LANE, "CAS_CORTEX_v0.1"),
             os.path.join(LANE, "CCB_L1_v0.1")):
    if path not in sys.path:
        sys.path.insert(0, path)
