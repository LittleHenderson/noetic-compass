#!/usr/bin/env bash
set -euo pipefail

ATTEMPT_ROOT=/workspace/cas-jlcv1-official-a8969eb7-cfbe1680
DEPENDENCY_ROOT=/workspace/cas-jlcv1-dependency-bundle-a8969eb7
MODEL_ROOT=/workspace/cas-model-a8969eb7
RECORDS_ROOT=/workspace/cas-jlcv1-attempt3-readonly-audit-cfbe1680
EXPECTED_COMMIT=a8969eb71c6d3e5c43d7ee2b7c7d4aa90dd70fc0
EXPECTED_TREE=cce2d477bb0f423ee6a2669ee680eaac7b999322

test -d "$ATTEMPT_ROOT"
test -d "$DEPENDENCY_ROOT"
test -d "$MODEL_ROOT"
test ! -e "$RECORDS_ROOT"

umask 077
mkdir -p "$RECORDS_ROOT"

emit_regular_file_inventory() {
  local root=$1
  local output=$2
  (
    cd "$root"
    while IFS= read -r -d '' relative_path; do
      relative_path=${relative_path#./}
      sha256=$(sha256sum -- "$relative_path" | cut -d ' ' -f 1)
      byte_count=$(stat -c '%s' -- "$relative_path")
      printf '%s\t%s\t%s\n' "$sha256" "$byte_count" "$relative_path"
    done < <(find . -type f ! -type l -print0 | LC_ALL=C sort -z)
  ) > "$output"
}

emit_link_inventory() {
  local root=$1
  local output=$2
  (
    cd "$root"
    while IFS= read -r -d '' relative_path; do
      relative_path=${relative_path#./}
      printf '%s\t%s\n' "$relative_path" "$(readlink -- "$relative_path")"
    done < <(find . -type l -print0 | LC_ALL=C sort -z)
  ) > "$output"
}

emit_type_counts() {
  local root=$1
  local output=$2
  {
    printf 'regular_files=%s\n' "$(find "$root" -type f ! -type l | wc -l)"
    printf 'directories=%s\n' "$(find "$root" -type d | wc -l)"
    printf 'symbolic_links=%s\n' "$(find "$root" -type l | wc -l)"
    printf 'other_entries=%s\n' "$(find "$root" ! -type f ! -type d ! -type l | wc -l)"
  } > "$output"
}

date -u +'%Y-%m-%dT%H:%M:%S.%NZ' > "$RECORDS_ROOT/audit_utc.txt"

{
  printf 'hostname='; hostname
  printf 'boot_id_sha256='; sha256sum /proc/sys/kernel/random/boot_id | cut -d ' ' -f 1
  printf 'machine_id_sha256='; sha256sum /etc/machine-id | cut -d ' ' -f 1
  printf 'gpu_csv='; nvidia-smi --query-gpu=name,uuid,memory.total,memory.used,utilization.gpu,driver_version --format=csv,noheader,nounits
} > "$RECORDS_ROOT/host_gpu_continuity.txt"

{
  for directory_name in output runlog environment_post; do
    entry_count=$(find "$ATTEMPT_ROOT/$directory_name" -mindepth 1 | wc -l)
    printf '%s_entry_count=%s\n' "$directory_name" "$entry_count"
  done
  printf 'matching_processes_begin\n'
  pgrep -af '[r]un_jacobian_lens_canary_v1' || true
  pgrep -af '[j]acobian_lens_canary_v1_seccomp' || true
  pgrep -af '[j]lcv1-rfc3161-cfbe1680' || true
  printf 'matching_processes_end\n'
} > "$RECORDS_ROOT/execution_absence.txt"

{
  printf 'head='; git -C "$ATTEMPT_ROOT/repo" rev-parse HEAD
  printf 'tree='; git -C "$ATTEMPT_ROOT/repo" rev-parse 'HEAD^{tree}'
  printf 'expected_head=%s\n' "$EXPECTED_COMMIT"
  printf 'expected_tree=%s\n' "$EXPECTED_TREE"
  printf 'status_porcelain_begin\n'
  git -C "$ATTEMPT_ROOT/repo" status --porcelain=v1 --untracked-files=all
  printf 'status_porcelain_end\n'
} > "$RECORDS_ROOT/repository_identity_and_status.txt"

test "$(git -C "$ATTEMPT_ROOT/repo" rev-parse HEAD)" = "$EXPECTED_COMMIT"
test "$(git -C "$ATTEMPT_ROOT/repo" rev-parse 'HEAD^{tree}')" = "$EXPECTED_TREE"
test -z "$(git -C "$ATTEMPT_ROOT/repo" status --porcelain=v1 --untracked-files=all)"

emit_regular_file_inventory "$ATTEMPT_ROOT" "$RECORDS_ROOT/official_attempt_regular_files.tsv"
emit_link_inventory "$ATTEMPT_ROOT" "$RECORDS_ROOT/official_attempt_symbolic_links.tsv"
emit_type_counts "$ATTEMPT_ROOT" "$RECORDS_ROOT/official_attempt_type_counts.txt"

emit_regular_file_inventory "$DEPENDENCY_ROOT" "$RECORDS_ROOT/dependency_regular_files.tsv"
emit_link_inventory "$DEPENDENCY_ROOT" "$RECORDS_ROOT/dependency_symbolic_links.tsv"
emit_type_counts "$DEPENDENCY_ROOT" "$RECORDS_ROOT/dependency_type_counts.txt"

emit_regular_file_inventory "$MODEL_ROOT" "$RECORDS_ROOT/model_snapshot_regular_files.tsv"
emit_link_inventory "$MODEL_ROOT" "$RECORDS_ROOT/model_snapshot_symbolic_links.tsv"
emit_type_counts "$MODEL_ROOT" "$RECORDS_ROOT/model_snapshot_type_counts.txt"

test "$(find "$DEPENDENCY_ROOT" -type f ! -type l | wc -l)" = 15
test "$(find "$DEPENDENCY_ROOT" -type l | wc -l)" = 0
test "$(find "$DEPENDENCY_ROOT" ! -type f ! -type d ! -type l | wc -l)" = 0
test "$(find "$ATTEMPT_ROOT/output" -mindepth 1 | wc -l)" = 0
test "$(find "$ATTEMPT_ROOT/runlog" -mindepth 1 | wc -l)" = 0
test "$(find "$ATTEMPT_ROOT/environment_post" -mindepth 1 | wc -l)" = 0

(
  cd "$ATTEMPT_ROOT/control"
  find . -maxdepth 1 -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum
) > "$RECORDS_ROOT/control_sha256.txt"

{
  printf 'official_attempt_inventory_sha256='; sha256sum "$RECORDS_ROOT/official_attempt_regular_files.tsv" | cut -d ' ' -f 1
  printf 'dependency_inventory_sha256='; sha256sum "$RECORDS_ROOT/dependency_regular_files.tsv" | cut -d ' ' -f 1
  printf 'model_snapshot_inventory_sha256='; sha256sum "$RECORDS_ROOT/model_snapshot_regular_files.tsv" | cut -d ' ' -f 1
  printf 'control_sha256_record_sha256='; sha256sum "$RECORDS_ROOT/control_sha256.txt" | cut -d ' ' -f 1
} > "$RECORDS_ROOT/inventory_record_hashes.txt"

find "$RECORDS_ROOT" -maxdepth 1 -type f -printf '%f\n' | LC_ALL=C sort > "$RECORDS_ROOT/records_file_names.txt"
sha256sum "$RECORDS_ROOT"/* | LC_ALL=C sort -k 2 > "$RECORDS_ROOT/records_sha256_before_recovery.txt"

printf 'READ_ONLY_AUDIT_COMPLETE\n'
