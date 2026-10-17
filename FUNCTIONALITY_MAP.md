# Functionality map

Where each behaviour of the Python implementation lives in every port. The Python
files are the source of truth; the other two columns are ports of them.

`—` means "not ported yet"; see [MIGRATION_REPORT.md](MIGRATION_REPORT.md) for why.

| # | Behaviour | Python | Rust | Java |
|---|-----------|--------|------|------|
| 1 | Timing loop / macro scheduler | `engine.py` `Engine.run` | `rust/src/engine.rs` `Engine::run` | `java/src/neverkickoff/Engine.java` |
| 2 | Step normalisation (flat spec → one implicit step) | `engine.py` `normalize_steps` | `rust/src/spec.rs` `normalize_steps` | `Spec.java` `normalizeSteps` |
| 3 | Config spec loading (parse combos in place) | `main.py` `load_spec` | `rust/src/spec.rs` `load_spec` | `Spec.java` `loadSpec` |
| 4 | Key combo parsing (`ctrl+alt+c` → keys) | `main.py` `parse_combo` | `rust/src/keys.rs` `parse_combo` | `Keys.java` `parseCombo` |
| 5 | Key names / aliases (the 56 pynput names) | `main.py` `ALIASES` + `pynput.keyboard.Key` | `rust/src/keys.rs` `KEY_NAMES` | `Keys.java` `KEY_NAMES` |
| 6 | Hotkey string built from a GUI key event | `hotkeys.py` `format_hotkey` | `rust/src/hotkeys.rs` `format_hotkey` | `Hotkeys.java` `formatHotkey` |
| 7 | Linux keycode table | `ydotool.py` `KEYS`/`SYMBOLS` + `evdev.ecodes` | `rust/src/ydotool.rs` `LINUX_CODES` | `Ydotool.java` `LINUX_CODES` |
| 8 | Injection through ydotool (Wayland) | `ydotool.py` `YdotoolDevice` | `rust/src/ydotool.rs` `YdotoolDevice` | `Ydotool.java` `YdotoolDevice` |
| 9 | ydotool availability / diagnosis | `ydotool.py` `available`/`problem` | `rust/src/ydotool.rs` `available`/`problem` | `Ydotool.java` `available`/`problem` |
| 10 | Injection through XTest (X11) | `main.py` `PynputDevice` | `rust/src/rdev_input.rs` `RdevDevice` | `RobotDevice.java` (`java.awt.Robot`) |
| 11 | Global hotkeys (toggle / panic) | `pynput.keyboard.GlobalHotKeys` | `rust/src/rdev_input.rs` `listen` | `HotkeyListener.java` (JNativeHook) |
| 12 | Focused-window title (window filter) | `window.py` `active_title` | `rust/src/window.rs` `active_title` | `Window.java` `activeTitle` |
| 13 | Toggle/stop controller, background run | `main.py` `Clicker` | `rust/src/clicker.rs` `Clicker` | `Clicker.java` |
| 14 | CLI entry point and stdout contract | `main.py` `main` | `rust/src/main.rs` `main` | `Main.java` `main` |
| 15 | Tray icon | `tray.py` | `—` | `—` |
| 16 | Six-tab GUI | `gui.py` | `—` | `—` |
| 17 | Config read/write through the GUI | `gui.py` | `—` | `—` |
| 18 | One-line installers | `install.sh`, `install.ps1` | n/a (Python-only by design) | n/a |

## Behaviour that is deliberately preserved, not fixed

These are quirks of the Python original. Each port reproduces them, so the three
implementations agree. Fixing any of them would be a functional change and needs
the user's approval.

| # | Quirk | Where |
|---|-------|-------|
| 1 | `repeat == 0` fires nothing (the `0 <= repeat <= fired` check breaks before the first tick) | `Engine.run` |
| 2 | Keys come back up in **reverse** order of what was pressed, inside a `finally` | `Engine._fire` |
| 3 | A failing key press still releases the keys that already went down | `Engine._fire` |
| 4 | `parse_combo`'s error message embeds a **Python list repr** of the split parts: `unknown key 'q' in '['ctrl', 'q']'` | `parse_combo` |
| 5 | `parse_combo` lower-cases a single-character key, so `ctrl+Q` becomes `q` | `parse_combo` |
| 6 | `make_device()` prints `input: ydotool (Wayland)` to stdout as a side effect | `main.make_device` |
| 7 | `listener.stop()` raises `AttributeError: ... has no attribute '_display_record'` when stopped right after `start()`; the CLI swallows it | `main.main` |
| 8 | A `window` filter never matches on Wayland (the compositor does not expose native titles) | `window.active_title` |
| 9 | Jitter is applied as `next_at += interval * (1 + uniform(-jitter, jitter))`, i.e. a drift-corrected deadline, never a sleep of `interval` | `Engine.run` |

## Out-of-contract differences (documented, no objection raised)

| # | Difference | Why |
|---|-----------|-----|
| 1 | Traceback **text** is not reproduced; exit codes and the printed message are | Python's traceback formatting is not meaningful in another language |
| 2 | `ydotool.keycode`'s `ValueError` text is not reproduced (it embeds a pynput repr); the failure itself is | `<Key.media_volume_up: 269025043>` has no counterpart in Rust or Java |
| 3 | The `--tray` fallback message names no module (`tray unavailable (no tray backend in this build)`) vs Python's `tray unavailable (No module named 'pystray')` | No tray backend is ported |
| 4 | `parse_combo("name")` returns a garbage object in Python (it collides with `Enum.name`); the ports reject it | Degenerate input; reproducing it would mean reproducing a bug with no defined behaviour |
