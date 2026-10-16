"""tkinter front end for neverKickOff.

    python gui.py [config.json]

Reuses the same Clicker, device and config shape as the CLI in main.py.
The click spec is a macro: a list of steps run in order every tick.
"""
import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from pynput import keyboard

from hotkeys import format_hotkey
from main import Clicker, make_device, parse_combo
from window import active_title
from ydotool import input_will_be_ignored

TIMING = [
    ("Interval (s)", "interval"),
    ("Initial delay (s)", "initial_delay"),
    ("Repeat (-1 = until stopped)", "repeat"),
    ("Jitter (0-1)", "jitter"),
    ("Duration (s, 0 = no limit)", "duration"),
]

STEP_KEYS = ("action", "button", "keys", "count", "hold", "wait")
STEP_DEFAULT = {"action": "mouse", "button": "left", "keys": "",
                "count": "1", "hold": "0", "wait": "0"}


def _number(text):
    try:
        return int(text)
    except ValueError:
        return float(text)


def _step_from_click(click):
    """A config's click section -> list of editable step dicts (string values)."""
    steps = []
    for raw in click.get("steps") or []:
        step = dict(STEP_DEFAULT)
        for key in STEP_KEYS:
            if key in raw:
                value = raw[key]
                step[key] = "+".join(value) if isinstance(value, list) else str(value)
        steps.append(step)
    if steps:
        return steps
    keys = click.get("keys", "")
    return [{**STEP_DEFAULT,
             "action": click.get("action", "mouse"),
             "button": click.get("button", "left"),
             "keys": "+".join(keys) if isinstance(keys, list) else str(keys),
             "hold": str(click.get("hold", 0))}]


class App:
    def __init__(self, root, config):
        self.root = root
        root.title("neverKickOff")
        click = config["click"]
        hot = config["hotkeys"]

        self.window = tk.StringVar(value=click.get("window", ""))
        self.toggle_key = tk.StringVar(value=hot["toggle"])
        self.panic_key = tk.StringVar(value=hot["panic"])
        self.timing = {name: tk.StringVar(value=str(click.get(name, 0))) for _, name in TIMING}
        self.status = tk.StringVar(value="ready")

        self.steps = _step_from_click(click)
        self.index = 0
        self._loading = False
        self.step = {key: tk.StringVar() for key in STEP_KEYS}
        for var in self.step.values():
            var.trace_add("write", lambda *_: self._store_step())

        self.clicker = Clicker(make_device(), self._spec(), focused_window=active_title)
        self.listener = None
        self._build()
        self._refresh()
        self._select(0)
        self._register_hotkeys()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        self.root.columnconfigure(1, weight=1)
        row = 0
        row = self._row(row, "Toggle hotkey", self._capture(self.root, self.toggle_key))
        row = self._row(row, "Panic hotkey", self._capture(self.root, self.panic_key))
        row = self._row(row, "Only click in window",
                        ttk.Entry(self.root, textvariable=self.window))
        row = self._heading(row, "Timing")
        for label, name in TIMING:
            row = self._row(row, label, ttk.Entry(self.root, textvariable=self.timing[name]))
        row = self._heading(row, "Macro steps (run in order, every tick)")
        row = self._macro(row)
        buttons = ttk.Frame(self.root)
        ttk.Button(buttons, text="Start / Stop", command=self.toggle).pack(side="left")
        ttk.Button(buttons, text="Save profile", command=self.save).pack(side="left")
        ttk.Button(buttons, text="Load profile", command=self.load).pack(side="left")
        buttons.grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=4)
        ttk.Label(self.root, textvariable=self.status).grid(
            row=row + 1, column=0, columnspan=2, sticky="w", padx=4)

    def _macro(self, row):
        frame = ttk.Frame(self.root)
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4)
        frame.columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(frame, height=5, exportselection=False)
        self.listbox.grid(row=0, column=0, sticky="ew")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        side = ttk.Frame(frame)
        side.grid(row=0, column=1, sticky="n", padx=(4, 0))
        for text, command in (("Add", self._add_step), ("Remove", self._remove_step),
                              ("Up", lambda: self._move(-1)), ("Down", lambda: self._move(1))):
            ttk.Button(side, text=text, width=8, command=command).pack(fill="x", pady=1)

        editor = ttk.LabelFrame(frame, text="Selected step")
        editor.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        editor.columnconfigure(1, weight=1)
        r = 0
        r = self._sub_row(editor, r, "Action",
                          self._radios(editor, self.step["action"], ["mouse", "keys"]))
        r = self._sub_row(editor, r, "Button",
                          self._radios(editor, self.step["button"], ["left", "right", "middle"]))
        r = self._sub_row(editor, r, "Key combo", self._capture(editor, self.step["keys"]))
        for label, key in (("Press count", "count"), ("Hold each (s)", "hold"),
                           ("Wait after (s)", "wait")):
            r = self._sub_row(editor, r, label, ttk.Entry(editor, textvariable=self.step[key]))
        return row + 1

    def _heading(self, row, text):
        ttk.Label(self.root, text=text).grid(row=row, column=0, columnspan=2,
                                             sticky="w", padx=4, pady=(8, 0))
        return row + 1

    def _row(self, row, label, widget):
        ttk.Label(self.root, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        widget.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        return row + 1

    def _sub_row(self, parent, row, label, widget):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        widget.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        return row + 1

    def _radios(self, parent, var, options):
        frame = ttk.Frame(parent)
        for option in options:
            ttk.Radiobutton(frame, text=option, value=option, variable=var).pack(side="left")
        return frame

    def _capture(self, parent, var):
        entry = ttk.Entry(parent, textvariable=var)
        entry.bind("<KeyPress>", lambda event: self._captured(event, var))
        entry.bind("<FocusOut>", lambda event: self._register_hotkeys())
        return entry

    def _captured(self, event, var):
        combo = format_hotkey(event.keysym, event.state)
        if combo:
            var.set(combo)
        return "break"  # keep the typed key out of the entry

    # --- macro list <-> step editor -----------------------------------------

    def _on_select(self, event):
        if self.listbox.curselection():
            self._select(self.listbox.curselection()[0])

    def _select(self, index):
        if not self.steps:
            return
        self.index = max(0, min(index, len(self.steps) - 1))
        self._loading = True
        for key, var in self.step.items():
            var.set(self.steps[self.index][key])
        self._loading = False

    def _store_step(self):
        if self._loading or not self.steps:
            return
        self.steps[self.index] = {key: var.get() for key, var in self.step.items()}
        self._refresh()

    def _refresh(self):
        self.listbox.delete(0, "end")
        for i, step in enumerate(self.steps):
            detail = step["keys"] if step["action"] == "keys" else step["button"]
            self.listbox.insert("end", f'{i + 1}. {step["action"]} {detail} x{step["count"]}')
        self.listbox.selection_clear(0, "end")
        if self.steps:
            self.listbox.selection_set(self.index)

    def _add_step(self):
        self.steps.append(dict(STEP_DEFAULT))
        self.index = len(self.steps) - 1
        self._refresh()
        self._select(self.index)

    def _remove_step(self):
        if len(self.steps) <= 1:
            self.status.set("a macro needs at least one step")
            return
        del self.steps[self.index]
        self.index = min(self.index, len(self.steps) - 1)
        self._refresh()
        self._select(self.index)

    def _move(self, delta):
        target = self.index + delta
        if not 0 <= target < len(self.steps):
            return
        self.steps[self.index], self.steps[target] = self.steps[target], self.steps[self.index]
        self.index = target
        self._refresh()

    # --- running ------------------------------------------------------------

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
            spec = self._spec()
        except Exception as exc:
            self.status.set(f"bad setting: {exc}")
            return
        self.clicker.set_spec(spec)
        started = self.clicker.toggle()
        if started and input_will_be_ignored():
            self.status.set("running - Wayland session: install and start ydotool "
                            "or clicks and keys do nothing (see README)")
        elif started and spec["window"] and active_title() is None:
            self.status.set("running - focused window title unreadable, so a "
                            "window filter can never match (Wayland?)")
        else:
            self.status.set("running" if started else "stopped")

    def stop(self):
        self.clicker.stop()
        self.status.set("stopped")

    def _spec(self):
        spec = {"window": self.window.get().strip(), "steps": []}
        for _, name in TIMING:
            spec[name] = _number(self.timing[name].get())
        for step in self.steps:
            built = {"action": step["action"], "count": int(_number(step["count"])),
                     "hold": _number(step["hold"]), "wait": _number(step["wait"])}
            if step["action"] == "keys":
                built["keys"] = parse_combo(step["keys"] or [])
            else:
                built["button"] = step["button"]
            spec["steps"].append(built)
        return spec

    def _config(self):
        click = {"window": self.window.get().strip(), "steps": []}
        for _, name in TIMING:
            click[name] = _number(self.timing[name].get())
        for step in self.steps:
            entry = {"action": step["action"], "count": int(_number(step["count"])),
                     "hold": _number(step["hold"]), "wait": _number(step["wait"])}
            if step["action"] == "keys":
                entry["keys"] = step["keys"]
            else:
                entry["button"] = step["button"]
            click["steps"].append(entry)
        return {"hotkeys": {"toggle": self.toggle_key.get(), "panic": self.panic_key.get()},
                "click": click}

    def _apply(self, config):
        click = config.get("click", {})
        self.window.set(click.get("window", ""))
        for _, name in TIMING:
            if name in click:
                self.timing[name].set(str(click[name]))
        self.steps = _step_from_click(click)
        self.index = 0
        self._refresh()
        self._select(0)
        hot = config.get("hotkeys", {})
        self.toggle_key.set(hot.get("toggle", self.toggle_key.get()))
        self.panic_key.set(hot.get("panic", self.panic_key.get()))
        self._register_hotkeys()
        self.status.set("profile loaded")

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self._config(), indent=2))
        except Exception as exc:
            self.status.set(f"bad setting: {exc}")
            return
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
            try:
                self.listener.stop()
            except Exception:  # pynput raises if stopped right after start
                pass
        self.root.destroy()


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("config.json")
    root = tk.Tk()
    App(root, json.loads(path.read_text()))
    root.mainloop()


if __name__ == "__main__":
    main()
