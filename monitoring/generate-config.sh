#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
umask 077

quiet=false
if [ "${1:-}" = "--quiet" ]; then
  quiet=true
fi

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

monitor_user="${PROMETHEUS_BASIC_USER:-}"
monitor_password="${PROMETHEUS_BASIC_PASSWORD:-}"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
  monitor_user="${PROMETHEUS_BASIC_USER:-${monitor_user}}"
  monitor_password="${PROMETHEUS_BASIC_PASSWORD:-${monitor_password}}"
fi

generated_env=false
if [ -z "${monitor_user}" ]; then
  monitor_user="monitor_$(random_alnum 8)"
  generated_env=true
fi
if [ -z "${monitor_password}" ]; then
  monitor_password="$(random_alnum 36)"
  generated_env=true
fi

monitoring_dir="monitoring/generated"
grafana_datasource_dir="${monitoring_dir}/grafana-datasources"
mkdir -p "${grafana_datasource_dir}"

if [ "${generated_env}" = true ]; then
  {
    echo "PROMETHEUS_BASIC_USER=${monitor_user}"
    echo "PROMETHEUS_BASIC_PASSWORD=${monitor_password}"
  } >> .env
fi

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

if [ "${quiet}" = false ]; then
  echo "Monitoring config written to ${monitoring_dir}"
  if [ "${generated_env}" = true ]; then
    echo "Generated monitoring credentials: username=${monitor_user} password=${monitor_password}"
  else
    echo "Using monitoring credentials from .env or the current environment."
  fi
fi
