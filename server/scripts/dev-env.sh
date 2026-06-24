#!/usr/bin/env bash
# Shared environment for LLMOps server local dev scripts.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SERVER_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PILOTGO_ROOT="$(cd "${SERVER_DIR}/.." && pwd)"
export WEB_DIR="${PILOTGO_ROOT}/web"
export RUNTIME_BASE="${RUNTIME_BASE:-${PILOTGO_ROOT}/.runtime}"
export GOPROXY="${GOPROXY:-https://proxy.golang.org,direct}"

export MINIO_ROOT_USER="${MINIO_ROOT_USER:-admin}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-admin123}"

export LOG_DIR="${RUNTIME_BASE}/logs"
export DATA_DIR="${RUNTIME_BASE}/data"
export BIN_DIR="${RUNTIME_BASE}/bin"
export SERVER_BIN="${SERVER_BIN:-${BIN_DIR}/llmops-server}"

mkdir -p "${LOG_DIR}" "${DATA_DIR}/minio" "${BIN_DIR}"

# Prefer project-local toolchain, then fall back to system PATH.
if [[ -d "${RUNTIME_BASE}/go/bin" ]]; then
  export GOROOT="${RUNTIME_BASE}/go"
fi
export PATH="${RUNTIME_BASE}/go/bin:${BIN_DIR}:${PATH}"
