#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=dev-env.sh
source "${SCRIPT_DIR}/dev-env.sh"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

case "${1:-all}" in
  minio)
    stop_port 9000
    stop_port 9001
    ;;
  server)
    stop_port 7070
    ;;
  all)
    stop_port 7070
    stop_port 9000
    stop_port 9001
    ;;
  *)
    echo "Usage: $0 [all|minio|server]"
    exit 1
    ;;
esac
