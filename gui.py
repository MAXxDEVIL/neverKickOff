"""tkinter front end for neverKickOff.

    python gui.py [config.json]

Reuses the same Clicker, device and config shape as the CLI in main.py.
"""
import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from pynput import keyboard

from hotkeys import format_hotkey
from main import Clicker, PynputDevice, parse_combo
from window import active_title

FIELDS = [
    ("Interval (s)", "interval"),
    ("Initial delay (s)", "initial_delay"),
    ("Repeat (-1 = until stopped)", "repeat"),
    ("Jitter (0-1)", "jitter"),
    ("Hold (s)", "hold"),
]


def _number(text):
    try:
        return int(text)
    except ValueError:
        return float(text)


class App:
    def __init__(self, root, config):
        self.root = root
        root.title("neverKickOff")
        click = config["click"]
        hot = config["hotkeys"]

        self.action = tk.StringVar(value=click.get("action", "mouse"))
        self.button = tk.StringVar(value=click.get("button", "left"))
        keys = click.get("keys", "")
        self.keys = tk.StringVar(value="+".join(keys) if isinstance(keys, list) else keys)
        self.window = tk.StringVar(value=click.get("window", ""))
        self.toggle_key = tk.StringVar(value=hot["toggle"])
        self.panic_key = tk.StringVar(value=hot["panic"])
        self.values = {name: tk.StringVar(value=str(click.get(name, 0))) for _, name in FIELDS}
        self.status = tk.StringVar(value="ready")

        self.clicker = Clicker(PynputDevice(), self._spec(), focused_window=active_title)
        self.listener = None
        self._build()
        self._register_hotkeys()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        self.root.columnconfigure(1, weight=1)
        row = 0
        row = self._row(row, "Toggle hotkey", self._capture(self.toggle_key))
        row = self._row(row, "Panic hotkey", self._capture(self.panic_key))
        row = self._row(row, "Action", self._radios(self.action, ["mouse", "keys"]))
        row = self._row(row, "Button", self._radios(self.button, ["left", "right", "middle"]))
        row = self._row(row, "Keys (keys action)", ttk.Entry(self.root, textvariable=self.keys))
        row = self._row(row, "Only click in window",
                        ttk.Entry(self.root, textvariable=self.window))
        for label, name in FIELDS:
            row = self._row(row, label, ttk.Entry(self.root, textvariable=self.values[name]))
        buttons = ttk.Frame(self.root)
        ttk.Button(buttons, text="Start / Stop", command=self.toggle).pack(side="left")
        ttk.Button(buttons, text="Save profile", command=self.save).pack(side="left")
        ttk.Button(buttons, text="Load profile", command=self.load).pack(side="left")
        buttons.grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=4)
        ttk.Label(self.root, textvariable=self.status).grid(
            row=row + 1, column=0, columnspan=2, sticky="w", padx=4)

    def _row(self, row, label, widget):
        ttk.Label(self.root, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        widget.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        return row + 1

    def _radios(self, var, options):
        frame = ttk.Frame(self.root)
        for option in options:
            ttk.Radiobutton(frame, text=option, value=option, variable=var).pack(side="left")
        return frame

    def _capture(self, var):
        entry = ttk.Entry(self.root, textvariable=var)
        entry.bind("<KeyPress>", lambda event: self._captured(event, var))
        entry.bind("<FocusOut>", lambda event: self._register_hotkeys())
        return entry

    def _captured(self, event, var):
        combo = format_hotkey(event.keysym, event.state)
        if combo:
            var.set(combo)
        return "break"  # keep the typed key out of the entry

    def _register_hotkeys(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        try:
            self.listener = keyboard.GlobalHotKeys({
                self.toggle_key.get(): self._hotkey_toggle,
                self.panic_key.get(): self._hotkey_stop,
            })
            self.listener.start()
            self.status.set(f"{self.toggle_key.get()} start/stop, {self.panic_key.get()} stop")
        except Exception as exc:
            self.status.set(f"hotkey error: {exc}")

    # Global hotkeys fire on the pynput listener thread; tkinter is not
    # thread-safe, so hop back to the main thread before touching the UI.
    def _hotkey_toggle(self):
        self.root.after(0, self.toggle)

    def _hotkey_stop(self):
        self.root.after(0, self.stop)

    def toggle(self):
        try:
            self.clicker.set_spec(self._spec())
        except Exception as exc:
            self.status.set(f"bad setting: {exc}")
            return
        self.status.set("running" if self.clicker.toggle() else "stopped")

    def stop(self):
        self.clicker.stop()
        self.status.set("stopped")

    def _spec(self):
        spec = {"action": self.action.get(), "button": self.button.get(), "keys": [],
                "window": self.window.get().strip()}
        for _, name in FIELDS:
            spec[name] = _number(self.values[name].get())  # raises on bad input, caught in toggle()
        if spec["action"] == "keys":
            spec["keys"] = parse_combo(self.keys.get() or [])
        return spec

    def _config(self):
        click = {"action": self.action.get(), "button": self.button.get(),
                 "keys": self.keys.get(), "window": self.window.get().strip()}
        for _, name in FIELDS:
            click[name] = _number(self.values[name].get())
        return {"hotkeys": {"toggle": self.toggle_key.get(), "panic": self.panic_key.get()},
                "click": click}

    def _apply(self, config):
        click = config.get("click", {})
        self.action.set(click.get("action", "mouse"))
        self.button.set(click.get("button", "left"))
        self.window.set(click.get("window", ""))
        keys = click.get("keys", "")
        self.keys.set("+".join(keys) if isinstance(keys, list) else keys)
        for _, name in FIELDS:
            if name in click:
                self.values[name].set(str(click[name]))
        hot = config.get("hotkeys", {})
        self.toggle_key.set(hot.get("toggle", self.toggle_key.get()))
        self.panic_key.set(hot.get("panic", self.panic_key.get()))
        self._register_hotkeys()
        self.status.set("profile loaded")

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            Path(path).write_text(json.dumps(self._config(), indent=2))
            self.status.set(f"saved {Path(path).name}")

    def load(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self._apply(json.loads(Path(path).read_text()))
        except Exception as exc:
            self.status.set(f"bad profile: {exc}")

    def close(self):
        self.clicker.stop()
        if self.listener:
            self.listener.stop()
        self.root.destroy()


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("config.json")
    root = tk.Tk()
    App(root, json.loads(path.read_text()))
    root.mainloop()


if __name__ == "__main__":
    main()
