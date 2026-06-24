#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

confirm_reset() {
  echo "This will export the current CTFd instance, stop Docker Compose, delete CTFd data, and start a fresh stack."
  echo "The export will be saved in .reset before anything is deleted."
  echo "The current .export folder will also be zipped into .reset before it is deleted."
  echo

  for count in 1 2 3 4 5 6 7; do
    read -r -p "Confirmation ${count}/7: type yes to continue: " answer
    if [ "${answer}" != "yes" ]; then
      echo "Reset aborted."
      exit 1
    fi
  done
}

write_secret_key() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 64 > .ctfd_secret_key
    return
  fi

  python3 - <<'PY' > .ctfd_secret_key
import secrets

print(secrets.token_hex(64))
PY
}

wait_for_export() {
  local container_path="$1"

  for _ in $(seq 1 60); do
    if docker compose exec -T ctfd sh -lc "/opt/venv/bin/python manage.py export_ctf '${container_path}'"; then
      return 0
    fi
    sleep 2
  done

  return 1
}

archive_export_folder() {
  local archive_path="$1"

  if [ ! -d .export ]; then
    echo "No .export folder found; skipping .export archive."
    return 0
  fi

  python3 - "${archive_path}" <<'PY'
from pathlib import Path
import sys
import zipfile

archive = Path(sys.argv[1])
root = Path(".export")

with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
    zip_file.write(root, ".export/")
    for path in root.rglob("*"):
        zip_file.write(path, path.as_posix())
PY

  if [ ! -s "${archive_path}" ]; then
    echo ".export archive is missing or empty." >&2
    exit 1
  fi

  echo ".export archive saved to ${archive_path}"
}

confirm_reset

timestamp="$(date -u +%Y%m%d_%H%M%S)"
reset_dir="${PWD}/.reset"
host_export="${reset_dir}/ctfd-reset-${timestamp}.zip"
auto_export_archive="${reset_dir}/auto-exports-${timestamp}.zip"
container_export="/tmp/ctfd-reset-${timestamp}.zip"

mkdir -p "${reset_dir}"

echo "Starting CTFd services required for export..."
docker compose up -d db cache ctfd

ctfd_container="$(docker compose ps -q ctfd)"
if [ -z "${ctfd_container}" ]; then
  echo "Could not find the running ctfd container." >&2
  exit 1
fi

echo "Exporting current CTFd data..."
if ! wait_for_export "${container_export}"; then
  echo "Export failed. Reset was not performed." >&2
  exit 1
fi

docker cp "${ctfd_container}:${container_export}" "${host_export}"
docker compose exec -T ctfd rm -f "${container_export}" >/dev/null 2>&1 || true

if [ ! -s "${host_export}" ]; then
  echo "Export file is missing or empty. Reset was not performed." >&2
  exit 1
fi

echo "Export saved to ${host_export}"
echo "Stopping Docker Compose stack..."
docker compose down --remove-orphans

echo "Archiving .export folder..."
archive_export_folder "${auto_export_archive}"

echo "Deleting CTFd persisted data..."
rm -rf .data .export
mkdir -p .data/CTFd/logs .data/CTFd/uploads .export
write_secret_key
bash monitoring/generate-config.sh

echo "Starting fresh Docker Compose stack..."
docker compose up -d --build

echo
echo "CTFd reset complete."
echo "Backup export: ${host_export}"
echo ".export archive: ${auto_export_archive}"
