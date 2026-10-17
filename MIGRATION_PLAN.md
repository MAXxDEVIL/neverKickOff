# Migration plan

Port the Python neverKickOff to Rust and Java without changing what it does.

## Ground rules

1. **The Python implementation is the source of truth.** It is not modified,
   moved, renamed or deleted, and it stays runnable at every commit.
2. **Behaviour first.** Preserve behaviour, then correctness, then executable
   builds, then improvements. Never "fix" a quirk on the way past - record it
   ([FUNCTIONALITY_MAP.md](FUNCTIONALITY_MAP.md)) and reproduce it.
3. **If it is different, it is a documented difference.** Anything a port cannot
   reproduce gets a line in [COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md)
   and [MIGRATION_REPORT.md](MIGRATION_REPORT.md).
4. **No silent dependencies.** Every new crate or jar is named and agreed before
   it is added.
5. **Only two new source trees** (`rust/`, `java/`) plus shared fixtures
   (`tests/`), build output (`dist/`) and documentation.

## Why a fixture, not a written spec

The risk in a port is that the spec and the port are both wrong together. So the
contract is generated from Python's *real* output rather than written down by
hand: `tests/gen_fixtures.py` records what Python does, and Rust and Java must
reproduce that file. See [TEST_PLAN.md](TEST_PLAN.md).

## Stages

| # | Stage | Deliverable | Exit criteria | Status |
|---|-------|-------------|---------------|--------|
| 0 | Baseline and contract | `tests/gen_fixtures.py`, `tests/fixtures/contract.json`, `tests/test_contract.py`, planning docs | Python still green (24 + 1), fixture generated, drift guard proven to catch a change | **PASS** |
| 1 | Rust engine + CLI | `rust/src/{engine,spec,keys,hotkeys,window,ydotool,device,clicker,main}.rs`, `rust/tests/*` | `cargo fmt --check`, `clippy -D warnings`, `cargo test` all clean; release binary; CLI prints the Python lines | **PASS** |
| 2 | Java engine + CLI | `java/src/neverkickoff/*.java`, contract test, jar | Contract test green; jar runs and prints the Python lines | **IN PROGRESS** |
| 3 | Input layers | Rust `rdev_input.rs`; Java `RobotDevice`/`HotkeyListener` | Engine drives a real device; hotkeys wired | **PASS** (Rust) / **IN PROGRESS** (Java) |
| 4 | GUIs | Swing (`java`) and egui/eframe (`rust`) | Feature parity with the six Python tabs | **NOT STARTED** |
| 5 | Packaging | `dist/` native binary, jar, `jpackage` image | The packaged artifact is what was tested | **NOT STARTED** |
| 6 | Report | `MIGRATION_REPORT.md`, `BUILD_AND_RUN.md` | Every claim above is evidenced | **IN PROGRESS** |

## Decisions already taken

| Decision | Choice | Why |
|----------|--------|-----|
| Cross-language contract | A JSON fixture generated from Python | Removes the paraphrase risk |
| GUI parity | Functional, not pixel-identical | Tkinter cannot be reproduced exactly in Swing or egui |
| Rust config parsing | `serde` / `serde_json` | Standard, small |
| Rust CLI argument parsing | Hand-rolled | The CLI takes `[config] [--tray]`; a parser crate would be larger than the need |
| Rust global hotkeys + X11 input | `rdev` 0.5 | One small crate covers both; no system package is needed on this machine |
| Rust Wayland input | `ydotool` subprocess | Exactly what the Python version does; no crate, no FFI |
| Java build | Plain `javac` + `jar`, `--release 21` | Maven and Gradle are not installed and must not be |
| Java JSON | Hand-rolled | The JDK has no JSON and the build must stay dependency-free |
| Java X11 input | `java.awt.Robot` | Part of the JDK; uses XTest, the same mechanism as pynput |
| Java global hotkeys | JNativeHook | The only maintained JDK-compatible option; agreed before adding |

## Order of work, and why

The engine and the CLI went first because they are the whole program's logic and
they are testable with no display, no input library and no GUI. Only once two
independent implementations agreed with Python on the contract was it worth
touching input, and only after that the GUIs.

## Open items

| Item | Status |
|------|--------|
| macOS `window`-title support in the ports | Documented gap (needs a platform API per language) |
| Tray icon in the ports | Not ported; the CLI reports it and keeps running |
| GUIs | Not started |
| Real injection testing | Blocked: `ydotool` is not installed and the session is Wayland |
