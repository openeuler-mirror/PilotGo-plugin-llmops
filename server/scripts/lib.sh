#!/usr/bin/env bash

require_cmd() {
  local cmd="$1"
  local hint="${2:-}"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Error: required command not found: ${cmd}" >&2
    [[ -n "${hint}" ]] && echo "${hint}" >&2
    exit 1
  fi
}

pids_on_port() {
  local port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -ti ":${port}" 2>/dev/null | sort -u
    return
  fi

  if command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null \
      | awk -v port=":${port}" '$4 ~ port { match($0, /pid=[0-9]+/); if (RSTART) print substr($0, RSTART + 4, RLENGTH - 4) }' \
      | sort -u
    return
  fi

  if command -v netstat >/dev/null 2>&1; then
    netstat -tlnp 2>/dev/null \
      | awk -v port=":${port}" '$4 ~ port { match($0, /[0-9]+\/[^ ]+/); if (RSTART) { split(substr($0, RSTART, RLENGTH), a, "/"); print a[1] } }' \
      | sort -u
  fi
}

port_in_use() {
  local port="$1"
  [[ -n "$(pids_on_port "${port}")" ]]
}

stop_port() {
  local port="$1"
  local pids
  pids="$(pids_on_port "${port}")"
  if [[ -z "${pids}" ]]; then
    echo "Nothing running on port ${port}"
    return
  fi

  echo "Stopping process on port ${port}: ${pids}"
  # shellcheck disable=SC2086
  kill ${pids} 2>/dev/null || true
  sleep 1
}

resolve_minio_bin() {
  if [[ -n "${MINIO_BIN:-}" && -x "${MINIO_BIN}" ]]; then
    echo "${MINIO_BIN}"
    return 0
  fi
  if [[ -x "${RUNTIME_BASE}/bin/minio" ]]; then
    echo "${RUNTIME_BASE}/bin/minio"
    return 0
  fi
  if command -v minio >/dev/null 2>&1; then
    command -v minio
    return 0
  fi
  return 1
}

resolve_go_bin() {
  if [[ -n "${GO_BIN:-}" && -x "${GO_BIN}" ]]; then
    echo "${GO_BIN}"
    return 0
  fi
  if [[ -x "${RUNTIME_BASE}/go/bin/go" ]]; then
    echo "${RUNTIME_BASE}/go/bin/go"
    return 0
  fi
  if command -v go >/dev/null 2>&1; then
    command -v go
    return 0
  fi
  return 1
}
