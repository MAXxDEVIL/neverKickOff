#!/usr/bin/env bash
# Build neverkickoff with plain javac/jar. No Maven, no Gradle.
#
#   ./build.sh          compile the library + CLI, the contract test, and the jar
#   ./build.sh test     build and run the contract test
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="${JAVA_HOME:-/usr/lib/jvm/default}/bin:$PATH"

CLASSES="$ROOT/build/classes"
TEST_CLASSES="$ROOT/build/test-classes"
JNH="$ROOT/lib/jnativehook-2.2.2.jar"

rm -rf "$CLASSES" "$TEST_CLASSES"
mkdir -p "$CLASSES" "$TEST_CLASSES" "$ROOT/dist"

# JNativeHook is optional: when present, the hotkey backend compiles and runs.
if [ -f "$JNH" ]; then
    CP_ARGS=(-cp "$JNH")
    echo "building with $JNH"
else
    CP_ARGS=()
    echo "JNativeHook not found; global hotkeys will be unavailable"
fi

SOURCES=("$ROOT"/src/neverkickoff/*.java)
if [ ! -f "$JNH" ]; then
    # Drop the one source that needs JNativeHook so the build still succeeds.
    KEEP=()
    for source in "${SOURCES[@]}"; do
        case "$(basename "$source")" in
            JNativeHookBackend.java) ;;
            *) KEEP+=("$source") ;;
        esac
    done
    SOURCES=("${KEEP[@]}")
fi

javac --release 21 -Xlint:all,-serial -d "$CLASSES" "${CP_ARGS[@]}" "${SOURCES[@]}"

jar --create --file "$ROOT/dist/neverkickoff.jar" --main-class neverkickoff.Main -C "$CLASSES" .

javac --release 21 -d "$TEST_CLASSES" -cp "$CLASSES" "$ROOT"/tests/*.java

if [ "${1:-}" = "test" ]; then
    java -cp "$CLASSES:$TEST_CLASSES" ContractTest
fi

echo "built $ROOT/dist/neverkickoff.jar"
