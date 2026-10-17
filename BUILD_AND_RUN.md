# Build and run

Three implementations of the same program live side by side. The Python version
is the original and the reference; the others are ports.

```
engine.py main.py hotkeys.py ydotool.py window.py gui.py tray.py   # Python (source of truth)
rust/                                                              # Rust port
java/                                                              # Java port
tests/fixtures/contract.json                                       # the shared contract
tests/run_all.sh                                                   # runs every suite
```

## Requirements

| To build | You need |
|----------|----------|
| Python | Python 3.8+; `pynput` (and `Xlib`/`evdev` on Linux); tkinter for the GUI. `pip install -r requirements.txt` |
| Rust | A stable Rust toolchain (`cargo`). No system packages: `rdev` builds against the X11 libraries already present |
| Java | A JDK, version 21 or newer. **No Maven, no Gradle** - the build is plain `javac`/`jar` |

To actually *inject input on Wayland* you also need `ydotool`, in every language:

```sh
sudo pacman -S ydotool            # or your distribution's package
systemctl --user enable --now ydotool
```

Without it the program starts, prints a warning, and does not click. That is the
same in all three implementations.

## Python

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python main.py                 # uses config.json next to main.py
python main.py my-config.json  # or a specific one
python main.py --tray          # with the tray icon, if pystray is installed
python gui.py                  # the six-tab GUI
```

Tests:

```sh
python test_engine.py          # 24 engine tests
python tests/test_contract.py  # does Python still match the frozen contract?
```

## Rust

```sh
cd rust

cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test                     # 7 contract tests + 4 timing tests

cargo build --release
./target/release/neverkickoff ../config.json
./target/release/neverkickoff ../config.json --tray
```

The binary is self-contained: `target/release/neverkickoff`, about 0.9 MB, no
runtime dependencies beyond libc and the X11 libraries `rdev` links against.

Input backends, chosen the same way Python chooses them:

- `ydotool` on PATH and not an X11 session → shells out to `ydotool`
- otherwise → `rdev` over XTest, the pynput equivalent

A copy of the release binary is placed in `dist/neverkickoff`.

## Java

See [java/README.md](java/README.md) for the authoritative commands. In outline:

```sh
cd java
./build.sh                     # javac --release 21 + jar, no build tool
./run-tests.sh                 # the contract test against tests/fixtures/contract.json

java -jar dist/neverkickoff.jar ../config.json
```

Input backends:

- `ydotool` on PATH and not an X11 session → shells out to `ydotool`
- otherwise → `java.awt.Robot` over XTest, the pynput equivalent

Global hotkeys use JNativeHook. The jar is vendored in `java/lib/`, so no
network access is needed to build.

## Run everything at once

```sh
sh tests/run_all.sh
```

It runs the Python baseline, the contract drift guard, and the Rust and Java
suites, then prints one summary. A suite whose toolchain is missing is skipped
rather than failed.

## The shared contract

`tests/fixtures/contract.json` holds the behaviour the ports must reproduce. It
is generated from the Python implementation:

```sh
.venv/bin/python tests/gen_fixtures.py    # regenerate after a deliberate Python change
```

Every port has a test that reads this file and asserts it. If Python changes and
the fixture is not regenerated, `tests/test_contract.py` fails and names the
exact path that moved. See [TEST_PLAN.md](TEST_PLAN.md).

## Installing beside the Python version

`install.sh` and `install.ps1` install the **Python** version into a user
directory with a launcher on `PATH`. They are unchanged by the ports. To install
a port instead, copy the artifact and make your own launcher:

```sh
install -Dm755 rust/target/release/neverkickoff ~/.local/bin/neverkickoff
install -Dm644 config.json ~/.config/neverkickoff/config.json
```

## Troubleshooting

| Symptom | Cause |
|---------|-------|
| `warning: Wayland ignores pynput's input: install ydotool ...` | You are on Wayland without `ydotool`. Install it as above. |
| `ydotool cannot reach ydotoold (...)` | `ydotoold` is not running: `systemctl --user enable --now ydotool` |
| `java: command not found` | Install a JDK 21+; the build needs `javac` and `jar`. |
| `cannot read /path/config.json` | The path is wrong. With no argument, the config is looked up next to the executable. |
