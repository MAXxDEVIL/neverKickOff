# neverKickOff

A tiny cross-platform auto clicker: custom keys and key combinations, a timing
system, a GUI, and click-only-while-a-window-is-focused. Driven by a JSON config.

## Installation

### Requirements

- **Python 3.8 or newer** — the code uses only the standard library plus `pynput`.
- **tkinter** for the GUI. It ships with the Windows and macOS installers from
  [python.org](https://www.python.org/downloads/); on Linux it is a separate
  package (see the Linux notes below).
- Windows, macOS, or Linux with an **X11** session.

### Install

```sh
git clone https://github.com/MAXxDEVIL/neverKickOff.git
cd neverKickOff

python -m venv .venv
```

Activate it with the line for **your** shell - each shell has its own script:

```sh
source .venv/bin/activate            # bash / zsh
source .venv/bin/activate.fish       # fish
.venv\Scripts\activate               # Windows, cmd
.venv\Scripts\Activate.ps1           # Windows, PowerShell
```

Then install:

```sh
pip install -r requirements.txt      # the only required dependency is pynput
```

### Verify

```sh
python test_engine.py
```

Prints `all passed`. The tests need no display, so they pass over SSH or headless.

### Platform specifics

- **Windows** — nothing extra. To click into an **elevated** window, run
  neverKickOff as administrator too; Windows blocks input from a normal process
  to an elevated one.
- **macOS** — install Python from python.org, or `brew install python-tk` for
  tkinter. On first run allow **Accessibility** and **Input Monitoring** for your
  terminal/Python in *System Settings → Privacy & Security*; without both, hotkeys
  and injected clicks are silently ignored. A packaged `.app` would need signing
  and notarisation to run on someone else's Mac.
- **Linux** — tkinter is not bundled:

  | Distro | Command |
  |---|---|
  | Arch / CachyOS | `sudo pacman -S tk` |
  | Debian / Ubuntu | `sudo apt install python3-tk` |
  | Fedora | `sudo dnf install python3-tkinter` |

  Global hooks require **X11**. On Wayland `pynput` cannot see global input, so
  hotkeys and clicks do nothing — use an "X11"/"Xorg" session instead. The tray
  needs a desktop backend (GTK/AppIndicator or Qt).
- `window` matching is per-OS: Windows = window title, X11 = `WM_NAME`,
  **macOS = the app name** (Accessibility API, not a title) — use the app name.
- Global hooks plus synthetic input can look like a keylogger to antivirus, and
  some games treat injected input as cheating — check their rules first.

## Run

```sh
python gui.py               # window: capture hotkeys, edit timing, profiles
python main.py              # config-driven CLI, uses config.json
python main.py my.json      # any config file
python main.py --tray       # CLI plus a system-tray toggle (see Tray)
```

CLI: `Ctrl+Alt+S` starts/stops, `Esc` panic-stops. GUI: click a hotkey field and
press the combination you want; `Start / Stop` or the toggle hotkey works from any
window.

### Tray (optional)

Off by default and needs two more packages:

```sh
pip install -r requirements-tray.txt   # pystray + Pillow
python main.py --tray
```

Without them `--tray` prints a notice and runs without the tray.

## Configure

```json
{
  "hotkeys": {
    "toggle": "<ctrl>+<alt>+s",
    "panic": "<esc>"
  },
  "click": {
    "action": "mouse",
    "button": "left",
    "keys": "ctrl+c",
    "window": "",

    "interval": 0.1,
    "initial_delay": 2.0,
    "repeat": -1,
    "jitter": 0.0,
    "hold": 0.0
  }
}
```

| Field | Meaning |
|---|---|
| `action` | `mouse` clicks a button, `keys` presses a key combo each tick |
| `button` | `left`, `right` or `middle` (mouse action) |
| `keys` | combo pressed together each tick, e.g. `"ctrl+c"` or `["ctrl","c"]` (keys action) |
| `window` | only tick while the focused window's title contains this text; empty = always |
| `interval` | seconds between tick starts |
| `initial_delay` | seconds before the first tick |
| `repeat` | number of ticks, `-1` for until you stop it |
| `jitter` | `0.0`–`1.0`, randomizes `interval` by ± this fraction |
| `hold` | seconds to hold the button/combo before releasing |

The loop schedules each tick against a fixed deadline, so a slow tick does not
accumulate drift.

## Build a standalone app (optional)

To hand someone a single file instead of a Python project:

```sh
pip install pyinstaller
pyinstaller --onefile --windowed gui.py
```

The result lands in `dist/` (`.exe` on Windows, binary/`.app` on macOS/Linux).
PyInstaller does not cross-compile: build on each OS you want to target.

## Troubleshooting

| Symptom | Fix |
|---|---|
| fish: `'case' builtin not inside of switch block` when activating | Use `source .venv/bin/activate.fish`, not `activate` |
| `No module named pynput` | Activate the venv, then `pip install -r requirements.txt` |
| `No module named tkinter`, or `libtk8.6.so: cannot open shared object file` | Install the tkinter package for your distro |
| Hotkeys do nothing on macOS | Grant Accessibility **and** Input Monitoring |
| Hotkeys do nothing on Linux | You are on Wayland; switch to an X11 session |
| Hotkeys do nothing anywhere else | Another app owns that combination — change it in the config or GUI |
| Clicks land in the wrong window | Set `window` to the title to watch for (app name on macOS); the check runs one tick before the click |
| `--tray` says "tray unavailable" | `pip install -r requirements-tray.txt`, plus a desktop backend on Linux |
| Antivirus flags the program | Expected for input injection; sign it or allowlist it |

## Uninstall

Delete the cloned folder (and its `.venv`). If you installed into your system
Python instead: `pip uninstall pynput pystray Pillow`.
