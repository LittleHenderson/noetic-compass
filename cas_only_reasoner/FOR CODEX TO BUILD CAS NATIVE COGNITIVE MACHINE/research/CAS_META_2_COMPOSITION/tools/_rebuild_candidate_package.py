import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aws import graph_training_candidate_launch as cl
from aws import graph_training_curriculum_launch as curl

record = ("records/teaching_cycle_001/graph_first_candidate_001/"
          "training_mode_001/cube_verified_teaching_001")
commit = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                 cwd=str(curl.ROOT)).decode().strip()
name = sys.argv[1] if len(sys.argv) > 1 else "candidate_package_003"
receipt = cl.build_candidate_package(record + "/" + name, source_sha=commit)
print("rebuilt package from", commit[:12])
print("directory:", name)
print("archive_sha256:", receipt["archive_sha256"])
print("manifest_sha256:", receipt["manifest_sha256"])
print("bytes:", receipt["archive_bytes"], "| members:", receipt["member_count"])
print("data files carried:", cl.package_data_files())
