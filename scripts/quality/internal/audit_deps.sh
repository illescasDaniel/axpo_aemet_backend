#!/usr/bin/env bash

set -euo pipefail

internal_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${internal_dir}/lib.sh"

lib_require_venv
lib_activate_venv
pip-audit --skip-editable
