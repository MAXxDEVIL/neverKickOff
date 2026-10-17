#!/usr/bin/env bash
# Run the Java contract test. tests/run_all.sh looks for exactly this file.
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/build.sh" test
