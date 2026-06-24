#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=dev-env.sh
source "${SCRIPT_DIR}/dev-env.sh"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

check_port() {
  local name="$1"
  local port="$2"
  if port_in_use "${port}"; then
    echo "[OK] ${name} listening on :${port}"
  else
    echo "[--] ${name} not running on :${port}"
  fi
}

echo "Project root: ${PILOTGO_ROOT}"
echo "Server dir:   ${SERVER_DIR}"
echo "Runtime dir:  ${RUNTIME_BASE}"
echo
echo "Managed: MinIO, LLMOps Server (see restart/stop-services.sh)"
echo "Check only: MySQL, Web (start web with: cd web && npm run dev)"
echo

check_port "MySQL" 3306
check_port "MinIO API" 9000
check_port "MinIO Console" 9001
check_port "LLMOps Server" 7070
check_port "Web Dev Server" 4100

if command -v curl >/dev/null 2>&1 && curl -fsS http://localhost:7070/ping >/dev/null 2>&1; then
  echo "[OK] /ping -> $(curl -fsS http://localhost:7070/ping)"
fi
