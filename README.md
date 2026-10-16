# neverKickOff

A tiny cross-platform auto clicker driven by a JSON config.

## Run

```sh
pip install -r requirements.txt
python gui.py               # window with hotkey capture, timing fields, profiles
# or, config-driven:
python main.py              # uses config.json
python main.py my.json      # or your own config
```

In the CLI, `Ctrl+Alt+S` starts and stops clicking; `Esc` panic-stops. Both are
configurable. In the GUI, click a hotkey field and press the combination you want;
`Start / Stop` or the toggle hotkey works from any window.

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
| `interval` | seconds between tick starts |
| `initial_delay` | seconds before the first tick |
| `repeat` | number of ticks, `-1` for until you stop it |
| `jitter` | `0.0`–`1.0`, randomizes `interval` by ± this fraction |
| `hold` | seconds to hold the button/combo before releasing |
| `window` | only tick while the focused window's title contains this text; empty = always |

The loop schedules each tick against a fixed deadline, so a slow tick does not
accumulate drift.

## Test

```sh
python test_engine.py   # timing loop + hotkey formatting, no display needed
```

## Platform notes

- **Windows/macOS**: works out of the box; macOS asks for Accessibility and
  Input Monitoring permission on first run.
- **Linux**: needs X11. Wayland has no global input hook — `shortcut:` fall back
  to `ydotool`/`uinput` if you need Wayland.
- What `window` matches: Windows = window title, X11 = `WM_NAME`, **macOS = the
  app name** (Accessibility API, not a title) — so use the app name there.
- Global hooks plus synthetic input can look like a keylogger to antivirus, and
  games may treat injected input as cheating.
