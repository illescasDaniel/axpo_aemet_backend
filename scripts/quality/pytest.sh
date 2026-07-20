#!/usr/bin/env bash

set -euo pipefail

quality_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=internal/lib.sh
source "${quality_dir}/internal/lib.sh"

lib_require_venv
lib_activate_venv
lib_pytest_args

export AEMET_API_KEY="${AEMET_API_KEY:-test-aemet-key}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///:memory:}"

if [[ ${#LIB_PYTEST_ARGS[@]} -eq 0 ]]; then
	echo "No pytest test directory found (expected tests/ or test/)" >&2
	exit 1
fi

pytest "${LIB_PYTEST_ARGS[@]}" "${LIB_PYTEST_COV[@]}"
