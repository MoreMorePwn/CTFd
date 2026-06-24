#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
umask 077

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

wait_for_db() {
  local password="$1"
  for _ in $(seq 1 60); do
    if docker compose exec -T db mariadb-admin ping -uroot -p"${password}" --silent >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

OLD_DB_ROOT_PASSWORD="${CTFD_DB_ROOT_PASSWORD:-ctfd}"
OLD_DB_USER="${CTFD_DB_USER:-ctfd}"
OLD_DB_PASSWORD="${CTFD_DB_PASSWORD:-ctfd}"
OLD_DB_NAME="${CTFD_DB_NAME:-ctfd}"

NEW_DB_ROOT_PASSWORD="$(random_alnum 36)"
NEW_DB_PASSWORD="$(random_alnum 36)"
NEW_REDIS_PASSWORD="$(random_alnum 36)"
NEW_MONITOR_USER="monitor_$(random_alnum 8)"
NEW_MONITOR_PASSWORD="$(random_alnum 36)"
NEW_SECRET_KEY="$(openssl rand -hex 64)"
GENERATED_MONITORING_DIR="monitoring/generated"
GENERATED_GRAFANA_DATASOURCES_DIR="${GENERATED_MONITORING_DIR}/grafana-datasources"

if [ -d .data/mysql/mysql ]; then
  echo "Existing MariaDB data detected; updating the database password before writing .env."
  docker compose up -d db
  if ! wait_for_db "${OLD_DB_ROOT_PASSWORD}"; then
    echo "Could not authenticate to the existing MariaDB container with the current root password." >&2
    echo "Check .env or the existing database credentials before rerunning." >&2
    exit 1
  fi

  docker compose exec -T db mariadb -uroot -p"${OLD_DB_ROOT_PASSWORD}" <<SQL
CREATE USER IF NOT EXISTS '${OLD_DB_USER}'@'%' IDENTIFIED BY '${OLD_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${OLD_DB_NAME}\`.* TO '${OLD_DB_USER}'@'%';
ALTER USER '${OLD_DB_USER}'@'%' IDENTIFIED BY '${NEW_DB_PASSWORD}';
ALTER USER 'root'@'localhost' IDENTIFIED BY '${NEW_DB_ROOT_PASSWORD}';
ALTER USER IF EXISTS 'root'@'%' IDENTIFIED BY '${NEW_DB_ROOT_PASSWORD}';
FLUSH PRIVILEGES;
SQL
fi

cat > .env <<EOF
CTFD_DB_ROOT_PASSWORD=${NEW_DB_ROOT_PASSWORD}
CTFD_DB_USER=${OLD_DB_USER}
CTFD_DB_PASSWORD=${NEW_DB_PASSWORD}
CTFD_DB_NAME=${OLD_DB_NAME}
CTFD_REDIS_PASSWORD=${NEW_REDIS_PASSWORD}
PROMETHEUS_BASIC_USER=${NEW_MONITOR_USER}
PROMETHEUS_BASIC_PASSWORD=${NEW_MONITOR_PASSWORD}
EOF

printf '%s\n' "${NEW_SECRET_KEY}" > .ctfd_secret_key
mkdir -p "${GENERATED_GRAFANA_DATASOURCES_DIR}"

PROMETHEUS_BCRYPT="$(
  python3 - "${NEW_MONITOR_PASSWORD}" <<'PY'
import bcrypt
import sys

password = sys.argv[1].encode()
print(bcrypt.hashpw(password, bcrypt.gensalt()).decode())
PY
)"

cat > "${GENERATED_MONITORING_DIR}/prometheus-web.yml" <<EOF
basic_auth_users:
  ${NEW_MONITOR_USER}: "${PROMETHEUS_BCRYPT}"
EOF

cat > "${GENERATED_MONITORING_DIR}/cadvisor.htpasswd" <<EOF
$(htpasswd -nbm "${NEW_MONITOR_USER}" "${NEW_MONITOR_PASSWORD}")
EOF

cat > "${GENERATED_MONITORING_DIR}/prometheus.yml" <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    scrape_interval: 5s
    basic_auth:
      username: "${NEW_MONITOR_USER}"
      password: "${NEW_MONITOR_PASSWORD}"
    static_configs:
      - targets: ["prometheus:9090"]

  - job_name: "cadvisor"
    scrape_interval: 5s
    basic_auth:
      username: "${NEW_MONITOR_USER}"
      password: "${NEW_MONITOR_PASSWORD}"
    static_configs:
      - targets: ["cadvisor-auth:8080"]

  - job_name: "node-exporter"
    scrape_interval: 5s
    static_configs:
      - targets: ["node-exporter:9100"]
EOF

cat > "${GENERATED_GRAFANA_DATASOURCES_DIR}/prometheus.yml" <<EOF
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
    basicAuthUser: ${NEW_MONITOR_USER}
    secureJsonData:
      basicAuthPassword: ${NEW_MONITOR_PASSWORD}
EOF

echo
echo "Generated service credentials:"
echo "  MariaDB root: username=root password=${NEW_DB_ROOT_PASSWORD}"
echo "  MariaDB CTFd app: username=${OLD_DB_USER} password=${NEW_DB_PASSWORD} database=${OLD_DB_NAME}"
echo "  Redis: username=default password=${NEW_REDIS_PASSWORD}"
echo "  Prometheus: username=${NEW_MONITOR_USER} password=${NEW_MONITOR_PASSWORD}"
echo "  cAdvisor auth proxy: username=${NEW_MONITOR_USER} password=${NEW_MONITOR_PASSWORD}"
echo "  CTFd secret key: ${NEW_SECRET_KEY}"
echo "  Grafana login was not changed."
echo

docker compose up -d --build
