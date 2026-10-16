"""neverKickOff - a small cross-platform auto clicker.

    python main.py [config.json]

Toggle clicking with the config's hotkeys.toggle combo (default Ctrl+Alt+S),
panic-stop with hotkeys.panic (default Esc). See README.md.
"""
import json
import sys
import threading
from pathlib import Path

from pynput import keyboard, mouse

from engine import Engine
import window

BUTTONS = {
    "left": mouse.Button.left,
    "right": mouse.Button.right,
    "middle": mouse.Button.middle,
}

ALIASES = {
    "control": "ctrl",
    "escape": "esc",
    "return": "enter",
    "win": "cmd",
    "super": "cmd",
    "meta": "cmd",
    "capslock": "caps_lock",
    "pgup": "page_up",
    "pgdn": "page_down",
}


def parse_combo(combo):
    """'ctrl+alt+c' or ['ctrl', 'c'] -> [Key.ctrl, Key.alt, KeyCode('c')], in order."""
    if isinstance(combo, str):
        combo = combo.split("+")
    keys = []
    for part in combo:
        name = ALIASES.get(part.strip().strip("<>").lower(), part.strip().strip("<>").lower())
        if hasattr(keyboard.Key, name):
            keys.append(getattr(keyboard.Key, name))
        elif len(name) == 1:
            keys.append(keyboard.KeyCode.from_char(name))
        else:
            raise KeyError(f"unknown key '{part}' in '{combo}'")
    return keys


def load_spec(click):
    """Copy a config's click spec, parsing every key combo into pynput keys."""
    spec = dict(click)
    if spec.get("steps"):
        steps = []
        for step in spec["steps"]:
            step = dict(step)
            if step.get("action") == "keys":
                step["keys"] = parse_combo(step.get("keys", []))
            steps.append(step)
        spec["steps"] = steps
    elif spec.get("action") == "keys":
        spec["keys"] = parse_combo(spec.get("keys", []))
    return spec


class PynputDevice:
    def __init__(self):
        self._keyboard = keyboard.Controller()
        self._mouse = mouse.Controller()

    def mouse_press(self, button):
        self._mouse.press(BUTTONS[button])

    def mouse_release(self, button):
        self._mouse.release(BUTTONS[button])

    def key_press(self, key):
        self._keyboard.press(key)

    def key_release(self, key):
        self._keyboard.release(key)


class Clicker:
    """Toggles one background Engine at a time."""

    def __init__(self, device, spec, focused_window=None):
        self._device = device
        self._spec = spec
        self._focused_window = focused_window
        self._engine = None
        self._lock = threading.Lock()

    def set_spec(self, spec):
        self._spec = spec

    def toggle(self):
        """Start clicking, or stop it if already running. Returns True when started."""
        with self._lock:
            if self._engine:
                self._engine.stop()
                self._engine = None
                print("stopped")
                return False
            engine = self._engine = Engine(self._device, self._focused_window)
        print("running")
        threading.Thread(target=self._run, args=(engine,), daemon=True).start()
        return True

    def _run(self, engine):
        fired = 0
        try:
            fired = engine.run(self._spec)
        except Exception as exc:  # a dead engine must not leave the toggle wedged
            print(f"stopped after error: {exc}")
        finally:
            with self._lock:
                if self._engine is engine:
                    self._engine = None
        print(f"done ({fired} ticks)")

    def stop(self):
        with self._lock:
            if self._engine:
                self._engine.stop()
                self._engine = None
                print("stopped")


def main():
    args = [arg for arg in sys.argv[1:] if arg != "--tray"]
    path = Path(args[0]) if args else Path(__file__).with_name("config.json")
    config = json.loads(path.read_text())
    spec = load_spec(config["click"])

    clicker = Clicker(PynputDevice(), spec, focused_window=window.active_title)
    listener = keyboard.GlobalHotKeys({
        config["hotkeys"]["toggle"]: clicker.toggle,
        config["hotkeys"]["panic"]: clicker.stop,
    })
    listener.start()
    print(f"ready - {config['hotkeys']['toggle']} start/stop, "
          f"{config['hotkeys']['panic']} panic-stop")
    try:
        if "--tray" in sys.argv:
            try:
                import tray
                tray.run(clicker)
                return
            except Exception as exc:  # no tray backend (e.g. no GTK): keep working
                print(f"tray unavailable ({exc}); running without it")
        listener.join()
    except KeyboardInterrupt:
        pass
    finally:
        clicker.stop()
        try:
            listener.stop()
        except Exception:  # pynput raises if stopped right after start
            pass


if __name__ == "__main__":
    main()
