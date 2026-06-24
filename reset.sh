#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

random_alnum() {
  python3 - "${1:-32}" <<'PY'
import secrets
import string
import sys

length = int(sys.argv[1])
alphabet = string.ascii_letters + string.digits
print("".join(secrets.choice(alphabet) for _ in range(length)))
PY
}

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

ensure_monitoring_config() {
  local monitoring_dir="monitoring/generated"
  local grafana_datasource_dir="${monitoring_dir}/grafana-datasources"
  local monitor_user="${PROMETHEUS_BASIC_USER:-}"
  local monitor_password="${PROMETHEUS_BASIC_PASSWORD:-}"
  local generated_env=false

  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
    monitor_user="${PROMETHEUS_BASIC_USER:-${monitor_user}}"
    monitor_password="${PROMETHEUS_BASIC_PASSWORD:-${monitor_password}}"
  fi

  if [ -z "${monitor_user}" ]; then
    monitor_user="monitor_$(random_alnum 8)"
    generated_env=true
  fi
  if [ -z "${monitor_password}" ]; then
    monitor_password="$(random_alnum 36)"
    generated_env=true
  fi

  mkdir -p "${grafana_datasource_dir}"

  if [ "${generated_env}" = true ]; then
    {
      echo "PROMETHEUS_BASIC_USER=${monitor_user}"
      echo "PROMETHEUS_BASIC_PASSWORD=${monitor_password}"
    } >> .env
  fi

  local prometheus_bcrypt
  prometheus_bcrypt="$(
    python3 - "${monitor_password}" <<'PY'
import bcrypt
import sys

password = sys.argv[1].encode()
print(bcrypt.hashpw(password, bcrypt.gensalt()).decode())
PY
  )"

  cat > "${monitoring_dir}/prometheus-web.yml" <<EOF
basic_auth_users:
  ${monitor_user}: "${prometheus_bcrypt}"
EOF

  cat > "${monitoring_dir}/cadvisor.htpasswd" <<EOF
$(htpasswd -nbm "${monitor_user}" "${monitor_password}")
EOF

  cat > "${monitoring_dir}/prometheus.yml" <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    scrape_interval: 5s
    basic_auth:
      username: "${monitor_user}"
      password: "${monitor_password}"
    static_configs:
      - targets: ["prometheus:9090"]

  - job_name: "cadvisor"
    scrape_interval: 5s
    basic_auth:
      username: "${monitor_user}"
      password: "${monitor_password}"
    static_configs:
      - targets: ["cadvisor-auth:8080"]

  - job_name: "node-exporter"
    scrape_interval: 5s
    static_configs:
      - targets: ["node-exporter:9100"]
EOF

  cat > "${grafana_datasource_dir}/prometheus.yml" <<EOF
apiVersion: 1

deleteDatasources:
  - name: prometheus-1
    orgId: 1

datasources:
  - name: prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    basicAuth: true
    basicAuthUser: ${monitor_user}
    secureJsonData:
      basicAuthPassword: ${monitor_password}
EOF

  if [ "${generated_env}" = true ]; then
    echo "Generated monitoring credentials: username=${monitor_user} password=${monitor_password}"
  fi
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
ensure_monitoring_config

echo "Starting fresh Docker Compose stack..."
docker compose up -d --build

echo
echo "CTFd reset complete."
echo "Backup export: ${host_export}"
echo ".export archive: ${auto_export_archive}"
