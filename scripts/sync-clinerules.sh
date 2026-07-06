#!/usr/bin/env bash

set -euo pipefail

UPSTREAM_REMOTE_NAME="${UPSTREAM_REMOTE_NAME:-clinerules}"
UPSTREAM_REMOTE_URL="${UPSTREAM_REMOTE_URL:-https://github.com/ondrej-winter/clinerules}"
UPSTREAM_BRANCH="${UPSTREAM_BRANCH:-master}"
UPSTREAM_REF="${UPSTREAM_REMOTE_NAME}/${UPSTREAM_BRANCH}"

sync_folder() {
  local source_path="$1"
  local destination_path="$2"
  local temp_root
  local extracted_path
  local staging_path

  temp_root="$(mktemp -d)"
  extracted_path="${temp_root}/${source_path}"
  staging_path="${temp_root}/staged"

  trap 'rm -rf "${temp_root}"' RETURN

  git archive --format=tar "${UPSTREAM_REF}" "${source_path}" | tar -xf - -C "${temp_root}"

  mkdir -p "${staging_path}"
  cp -R "${extracted_path}/." "${staging_path}/"

  rm -rf "${destination_path}"
  mkdir -p "${destination_path}"
  cp -R "${staging_path}/." "${destination_path}/"
}

ensure_remote() {
  if ! git remote get-url "${UPSTREAM_REMOTE_NAME}" >/dev/null 2>&1; then
    git remote add "${UPSTREAM_REMOTE_NAME}" "${UPSTREAM_REMOTE_URL}"
  fi
}

ensure_remote
git fetch "${UPSTREAM_REMOTE_NAME}" "${UPSTREAM_BRANCH}"

# Example: sync the Python hexagonal ruleset into this target repository.
# Adjust these mappings for the assets the target repository should consume.
sync_folder "python/hexagonal/agents" ".agents"
sync_folder "python/hexagonal/clinerules" ".clinerules"
