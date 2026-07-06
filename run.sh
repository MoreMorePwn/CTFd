#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
umask 077

usage() {
  cat <<'EOF'
Usage:
  ./run.sh             Show this help.
  ./run.sh start       Start CTFd with current data, or initialize a fresh instance.
  ./run.sh reset       Delete local data/config and start as a fresh instance.
  ./run.sh reset --yes Same as reset, without the confirmation prompt.

Default start behavior:
  - If .env exists, current credentials/data are reused and Docker Compose is started.
  - If .env does not exist and no database data exists, new credentials are generated.
  - If database data exists but .env is missing, the script stops to avoid orphaning data.
EOF
}

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

load_env() {
  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
  fi
}

compose_up() {
  docker compose up -d --build
}

generate_credentials() {
  local db_user="${CTFD_DB_USER:-ctfd}"
  local db_name="${CTFD_DB_NAME:-ctfd}"
  local db_root_password
  local db_password
  local redis_password
  local monitor_user
  local monitor_password
  local secret_key

  db_root_password="$(random_alnum 36)"
  db_password="$(random_alnum 36)"
  redis_password="$(random_alnum 36)"
  monitor_user="monitor_$(random_alnum 8)"
  monitor_password="$(random_alnum 36)"
  secret_key="$(openssl rand -hex 64)"

  cat > .env <<EOF
CTFD_DB_ROOT_PASSWORD=${db_root_password}
CTFD_DB_USER=${db_user}
CTFD_DB_PASSWORD=${db_password}
CTFD_DB_NAME=${db_name}
CTFD_REDIS_PASSWORD=${redis_password}
CTFD_SECRET_KEY=${secret_key}
PROMETHEUS_BASIC_USER=${monitor_user}
PROMETHEUS_BASIC_PASSWORD=${monitor_password}
EOF

  printf '%s\n' "${secret_key}" > .ctfd_secret_key
  chmod 600 .env .ctfd_secret_key

  PROMETHEUS_BASIC_USER="${monitor_user}" \
  PROMETHEUS_BASIC_PASSWORD="${monitor_password}" \
    bash monitoring/generate-config.sh --quiet

  echo
  echo "Generated service credentials:"
  echo "  MariaDB root: username=root password=${db_root_password}"
  echo "  MariaDB CTFd app: username=${db_user} password=${db_password} database=${db_name}"
  echo "  Redis: username=default password=${redis_password}"
  echo "  Prometheus: username=${monitor_user} password=${monitor_password}"
  echo "  cAdvisor auth proxy: username=${monitor_user} password=${monitor_password}"
  echo "  CTFd secret key: ${secret_key}"
  echo "  Grafana login was not changed."
  echo
}

ensure_monitoring_config() {
  load_env
  PROMETHEUS_BASIC_USER="${PROMETHEUS_BASIC_USER:-}" \
  PROMETHEUS_BASIC_PASSWORD="${PROMETHEUS_BASIC_PASSWORD:-}" \
    bash monitoring/generate-config.sh --quiet
}

start_existing_or_initialize() {
  if [ -f .env ]; then
    echo "Existing .env detected; starting with current credentials and data."
    ensure_monitoring_config
    compose_up
    return
  fi

  if [ -d .data/mysql/mysql ]; then
    echo "Existing MariaDB data was found, but .env is missing." >&2
    echo "Refusing to generate new credentials that would not match the existing database." >&2
    echo "Restore the matching .env, or run './run.sh reset' to delete local data and start fresh." >&2
    exit 1
  fi

  echo "No .env or MariaDB data detected; initializing a fresh instance."
  generate_credentials
  compose_up
}

confirm_reset() {
  local yes="${1:-false}"

  if [ "${yes}" = true ]; then
    return
  fi

  echo "This will stop Docker Compose and delete local CTFd data, uploads, exports, database, Redis data, generated monitoring config, and credentials."
  printf "Type 'reset' to continue: "
  read -r answer
  if [ "${answer}" != "reset" ]; then
    echo "Reset cancelled."
    exit 1
  fi
}

reset_infra() {
  local yes=false

  while [ "$#" -gt 0 ]; do
    case "$1" in
      -y|--yes)
        yes=true
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown reset option: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
    shift
  done

  confirm_reset "${yes}"

  docker compose down --remove-orphans
  rm -rf .data .export monitoring/generated .env .ctfd_secret_key
  mkdir -p .export

  echo "Local data removed; initializing a fresh instance."
  generate_credentials
  compose_up
}

if [ "$#" -eq 0 ]; then
  usage
  exit 0
fi

command="$1"
if [ "$#" -gt 0 ]; then
  shift
fi

case "${command}" in
  start|up)
    if [ "$#" -ne 0 ]; then
      echo "Unexpected arguments for ${command}: $*" >&2
      usage >&2
      exit 1
    fi
    start_existing_or_initialize
    ;;
  reset|fresh)
    reset_infra "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: ${command}" >&2
    usage >&2
    exit 1
    ;;
esac
