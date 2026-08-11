#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT=/workspace/cas-jlcv1-dependency-bundle-a8969eb7
REJECTED=/workspace/cas-jlcv1-dependency-bundle-rejected-pycache-cfbe1680
STAGING=/workspace/cas-jlcv1-dependency-bundle-rebuild-cfbe1680
SOURCE=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1
PY=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
WORKER=/workspace/cas-jlcv1-official-a8969eb7-cfbe1680/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker

test -d "$ROOT"
test ! -L "$ROOT"
test -d "$ROOT/jlens/__pycache__"
test ! -e "$REJECTED"
test ! -e "$STAGING"
test "$(readlink -f /workspace)" = /workspace

mkdir -p "$STAGING"
while IFS= read -r relative_path; do
  test -f "$SOURCE/$relative_path"
  test ! -L "$SOURCE/$relative_path"
  mkdir -p "$STAGING/$(dirname "$relative_path")"
  cp "$SOURCE/$relative_path" "$STAGING/$relative_path"
done <<'FILES'
LICENSE
jlens/__init__.py
jlens/_logging.py
jlens/data/README.md
jlens/data/blackmail.json
jlens/data/slice_vis.html
jlens/examples.py
jlens/fitting.py
jlens/hf.py
jlens/hooks.py
jlens/lens.py
jlens/protocol.py
jlens/vis.py
pyproject.toml
uv.lock
FILES

"$PY" -I -B -c "import json,sys; from pathlib import Path; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_dependency_bundle import verify_dependency_bundle; value=verify_dependency_bundle(Path('$STAGING')); print(json.dumps({'file_count': value.file_count, 'file_manifest_sha256': value.file_manifest_sha256, 'dependency_lock_sha256': value.uv_lock_sha256}, sort_keys=True, separators=(',', ':')))"

mv "$ROOT" "$REJECTED"
mv "$STAGING" "$ROOT"

"$PY" -I -B -c "import json,sys; from pathlib import Path; sys.path.insert(0, '$WORKER'); from research.jacobian_lens_dependency_bundle import verify_dependency_bundle; value=verify_dependency_bundle(Path('$ROOT')); print(json.dumps({'file_count': value.file_count, 'file_manifest_sha256': value.file_manifest_sha256, 'dependency_lock_sha256': value.uv_lock_sha256}, sort_keys=True, separators=(',', ':')))"

printf 'rejected_contaminated_root=%s\nclean_dependency_root=%s\n' "$REJECTED" "$ROOT"
