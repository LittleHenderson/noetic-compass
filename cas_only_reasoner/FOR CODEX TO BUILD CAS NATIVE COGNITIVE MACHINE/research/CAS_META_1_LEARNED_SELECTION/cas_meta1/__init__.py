"""CAS-META-1: isolated, GPU-only learned selection pilot."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
META0_ROOT = ROOT.parent / "CASFORMER_v0_3_META_LOGIC_WIP"
# The accepted meta layer has no wheel. Neural dependencies MUST be installed
# from their frozen wheels and are checked separately; do not shadow them.
if not META0_ROOT.is_dir():
    raise RuntimeError("MISSING_ACCEPTED_META0_SIBLING")
if str(META0_ROOT) not in sys.path:
    sys.path.insert(0, str(META0_ROOT))

__version__ = "0.1.0"
