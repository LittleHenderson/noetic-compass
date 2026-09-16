"""Short Windows entry point for the unchanged accepted-byte browser runner."""
from pathlib import Path
import runpy
import sys

folder=Path(__file__).resolve().parent
sys.path.insert(0,str(folder))
runner=folder/'check_accepted_documents.py'
sys.argv=[str(runner),*sys.argv[1:]]
runpy.run_path(str(runner),run_name='__main__')
