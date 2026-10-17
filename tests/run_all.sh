#!/bin/sh
# Run every test suite in the repository and print one summary.
#
#     sh tests/run_all.sh
#
# A suite whose toolchain or directory is missing is skipped rather than failed,
# so this works on a machine that only has one of the three languages.
set -u
cd "$(dirname "$0")/.." || exit 1

tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
failed=0

if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
else
    PY=$(command -v python3 || command -v python || true)
fi

check() {
    name=$1
    shift
    if "$@" >"$tmp/out" 2>&1; then
        printf 'PASS  %s\n' "$name"
    else
        printf 'FAIL  %s\n' "$name"
        sed 's/^/       /' "$tmp/out" | tail -25
        failed=1
    fi
}

if [ -n "${PY:-}" ]; then
    check "python engine (24 tests)" "$PY" test_engine.py
    check "python contract guard" "$PY" tests/test_contract.py
else
    printf 'SKIP  python (no interpreter found)\n'
fi

if command -v cargo >/dev/null 2>&1 && [ -f rust/Cargo.toml ]; then
    check "rust fmt" sh -c 'cd rust && cargo fmt --check'
    check "rust clippy -D warnings" \
        sh -c 'cd rust && cargo clippy --all-targets --all-features -- -D warnings'
    check "rust contract + timing (11 tests)" sh -c 'cd rust && cargo test'
else
    printf 'SKIP  rust (cargo not found)\n'
fi

if [ -x java/build.sh ] && command -v javac >/dev/null 2>&1; then
    check "java build" sh -c 'cd java && ./build.sh'
    if [ -x java/run-tests.sh ]; then
        check "java contract" sh -c 'cd java && ./run-tests.sh'
    fi
else
    printf 'SKIP  java (java/build.sh or javac not found)\n'
fi

printf '\n'
if [ "$failed" -eq 0 ]; then
    echo "all suites passed"
else
    echo "some suites failed"
fi
exit "$failed"
