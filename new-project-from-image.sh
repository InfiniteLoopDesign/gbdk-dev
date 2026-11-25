#!/usr/bin/env bash
set -euo pipefail

starter_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec "$starter_root/new-project.sh" --published-image "$@"
