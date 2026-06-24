#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=dev-env.sh
source "${SCRIPT_DIR}/dev-env.sh"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

start_minio() {
  local minio_bin
  if port_in_use 9000; then
    echo "MinIO already running on :9000"
    return
  fi

  if ! minio_bin="$(resolve_minio_bin)"; then
    echo "Error: minio binary not found." >&2
    echo "Install minio to PATH, or place it at: ${BIN_DIR}/minio" >&2
    echo "Override with: export MINIO_BIN=/path/to/minio" >&2
    exit 1
  fi

  nohup "${minio_bin}" server "${DATA_DIR}/minio" \
    --address ":9000" --console-address ":9001" \
    > "${LOG_DIR}/minio.log" 2>&1 &
  echo "MinIO started (API :9000, console :9001)"
}

start_server() {
  local go_bin

  if [[ ! -f "${SERVER_DIR}/config.yaml" ]]; then
    echo "Missing ${SERVER_DIR}/config.yaml" >&2
    echo "Run: cp ${SERVER_DIR}/config.yaml.templete ${SERVER_DIR}/config.yaml" >&2
    exit 1
  fi

  if [[ ! -x "${SERVER_BIN}" ]]; then
    if ! go_bin="$(resolve_go_bin)"; then
      echo "Error: go compiler not found." >&2
      echo "Install Go to PATH, or place it at: ${RUNTIME_BASE}/go" >&2
      echo "Override with: export GO_BIN=/path/to/go" >&2
      exit 1
    fi
    echo "Building server binary..."
    (cd "${SERVER_DIR}" && "${go_bin}" build -o "${SERVER_BIN}" ./cli/server/main.go)
  fi

  stop_port 7070
  cd "${SERVER_DIR}"
  nohup "${SERVER_BIN}" > "${LOG_DIR}/server.log" 2>&1 &

  require_cmd curl "Install curl to verify server health."
  sleep 1
  if curl -fsS http://localhost:7070/ping >/dev/null 2>&1; then
    echo "Server started on http://localhost:7070"
  else
    echo "Server failed to start. Check ${LOG_DIR}/server.log" >&2
    exit 1
  fi
}

case "${1:-all}" in
  minio)
    stop_port 9000
    stop_port 9001
    start_minio
    ;;
  server)
    start_server
    ;;
  all)
    start_minio
    start_server
    ;;
  *)
    echo "Usage: $0 [all|minio|server]"
    exit 1
    ;;
esac
