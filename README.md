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

  Global hooks require **X11**: on Wayland `pynput` cannot see or send global
  input, so hotkeys and clicks silently do nothing. neverKickOff detects a
  Wayland session and, when the `ydotool` binary is installed, injects through
  it instead (that is what makes clicks work there):

  ```sh
  sudo pacman -S ydotool        # Arch / CachyOS
  systemctl --user enable --now ydotool
  ```

  Start `ydotoold` the way your package ships it (Arch's package provides the
  `ydotool` user service above; some distros use a system service). The app
  prints `input: ydotool (Wayland)` when it picks it. Hotkeys still need X11 —
  ydotool only fixes clicking and key injection, not global hotkey detection,
  so on Wayland drive it from the GUI buttons. The tray needs a desktop backend
  (GTK/AppIndicator or Qt).
- `window` matching is per-OS: Windows = window title, X11 = `WM_NAME` or
  `_NET_WM_NAME`, **macOS = the app name** (Accessibility API, not a title) — use
  the app name. On a Wayland session titles come back empty for native Wayland
  apps, so a `window` filter can never match there; the GUI says so when you start.
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
press the combination you want; the **Start** button at the top (it becomes
**Stop** while running) or the toggle hotkey works from any window. Settings live
in five tabs - **Settings** (hotkeys and timing), **Mouse**, **Keyboard** and
**Key combos** (a focused builder each; a keyboard step is one key, a combo is two
or more) and **Macro** (the ordered run of every step) - and every field shows a
tooltip on hover.

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
    "window": "",

    "interval": 0.1,
    "initial_delay": 2.0,
    "repeat": -1,
    "jitter": 0.0,
    "duration": 0.0,

    "steps": [
      { "action": "keys",  "keys": "ctrl+c", "count": 3, "hold": 0.05, "wait": 0.2 },
      { "action": "mouse", "button": "left",   "count": 1, "hold": 0.0,  "wait": 0.0 }
    ]
  }
}
```

`steps` is the macro: every tick runs the steps **in order**, then waits
`interval` before the next tick. Build it in the GUI's *Macro steps* list
(Add / Remove / Up / Down), or write it by hand.

| Field | Meaning |
|---|---|
| `steps[].action` | `mouse` clicks a button, `keys` presses a key combo |
| `steps[].button` | `left`, `right` or `middle` (mouse step) |
| `steps[].keys` | combo pressed together, e.g. `"ctrl+c"` or `["ctrl","c"]` (keys step) |
| `steps[].count` | how many times that step's press repeats |
| `steps[].hold` | seconds each press is held down before release |
| `steps[].wait` | seconds to pause after the step, before the next one |
| `window` | only tick while the focused window's title contains this text; empty = always |
| `interval` | seconds between tick starts |
| `initial_delay` | seconds before the first tick |
| `repeat` | number of ticks, `-1` for until you stop it |
| `jitter` | `0.0`–`1.0`, randomizes `interval` by ± this fraction |
| `duration` | stop the whole run after this many seconds; `0` = no limit |

The loop schedules each tick against a fixed deadline, so a slow tick does not
accumulate drift.

A config with no `steps` still works: its `action` / `button` / `keys` / `hold`
are treated as a single step, so older profiles keep running.

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
| Hotkeys do nothing on Linux | You are on Wayland; install and run `ydotool` (see Platform specifics) and use the GUI buttons, since only X11 delivers global hotkeys |
| Clicks do nothing on Linux | On Wayland ensure `ydotool` is installed and `ydotoold` is running, and that the app printed `input: ydotool (Wayland)` |
| Hotkeys do nothing anywhere else | Another app owns that combination — change it in the config or GUI |
| Clicks land in the wrong window | Set `window` to the title to watch for (app name on macOS); the check runs one tick before the click |
| `--tray` says "tray unavailable" | `pip install -r requirements-tray.txt`, plus a desktop backend on Linux |
| Antivirus flags the program | Expected for input injection; sign it or allowlist it |

## Uninstall

Delete the cloned folder (and its `.venv`). If you installed into your system
Python instead: `pip uninstall pynput pystray Pillow`.
