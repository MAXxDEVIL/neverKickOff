"""tkinter front end for neverKickOff.

    python gui.py [config.json]

Reuses the same Clicker, device and config shape as the CLI in main.py.
The click spec is a macro: a list of steps run in order every tick.
"""
import json
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, simpledialog, ttk

from pynput import keyboard

from hotkeys import format_hotkey
from main import Clicker, make_device, parse_combo
from window import active_title
from ydotool import problem

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

FIELD_HELP = {
    "interval": "Seconds between macro runs. 0.1 = ten runs a second.",
    "initial_delay": "Seconds to wait after Start before the first click.",
    "repeat": "How many times to run the macro. -1 runs until you stop it.",
    "jitter": "Random variation (0-1) added to the interval, so the timing looks less robotic.",
    "duration": "Stop automatically after this many seconds. 0 runs until you stop it.",
}


def _font(bold=False):
    face = tkfont.nametofont("TkDefaultFont").copy()
    if bold:
        face.configure(weight="bold")
    return face


def _theme(style):
    """Flat 'clam' look with a few coloured styles. Returns the frame background."""
    style.theme_use("clam")
    style.configure("Accent.TButton", background="#1f883d", foreground="white",
                    font=_font(True), padding=(14, 8))
    style.map("Accent.TButton", background=[("active", "#1a7f37"), ("pressed", "#166b2e")])
    style.configure("Stop.TButton", background="#cf222e", foreground="white",
                    font=_font(True), padding=(14, 8))
    style.map("Stop.TButton", background=[("active", "#b3202b"), ("pressed", "#9a1c25")])
    style.configure("Hint.TLabel", foreground="#57606a")
    style.configure("Error.TLabel", foreground="#cf222e", font=_font(True))
    return style.lookup("TFrame", "background") or "#dcdad5"


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


def _kind(step):
    """mouse, key (exactly one key) or combo (several) - derived, so no schema change."""
    if step["action"] == "mouse":
        return "mouse"
    return "combo" if len([k for k in step["keys"].split("+") if k.strip()]) > 1 else "key"


def _config_dir():
    """Per-user config folder: APPDATA on Windows, Application Support on macOS."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "neverKickOff"


def _profiles_dir():
    return _config_dir() / "profiles"


def _profile_name(name):
    """A filename stem we are willing to write, or None for anything unsafe."""
    name = name.strip()
    if not name or name in (".", "..") or any(char in name for char in "/\\"):
        return None
    return name


class _Tooltip:
    """Hover help: one undecorated toplevel per widget, shown on <Enter>."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, justify="left", background="#fffbe6",
                 relief="solid", borderwidth=1, padx=6, pady=3).pack()

    def _hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class App:
    def __init__(self, root, config, use_profiles=True):
        self.root = root
        root.title("neverKickOff")
        self.bg = _theme(ttk.Style(root))

        click = config["click"]
        hot = config["hotkeys"]
        self.window = tk.StringVar(value=click.get("window", ""))
        self.toggle_key = tk.StringVar(value=hot["toggle"])
        self.panic_key = tk.StringVar(value=hot["panic"])
        self.timing = {name: tk.StringVar(value=str(click.get(name, 0))) for _, name in TIMING}
        self.status = tk.StringVar(value="ready")
        self.error = tk.StringVar()
        self.profile = tk.StringVar()      # what the dropdown shows
        self._loaded = ""                  # what is actually loaded (differs on switching)
        self._snapshot = ""                # last saved/loaded spec, for the unsaved-changes check

        self.steps = _step_from_click(click)
        self.index = 0
        self._loading = False
        self._poll = None
        self.step = {key: tk.StringVar() for key in STEP_KEYS}
        for var in self.step.values():
            var.trace_add("write", lambda *_: self._store_step())
        self.step["action"].trace_add("write", lambda *_: self._sync_action())
        # Separate scratch values for the Mouse/Keyboard/Key-combos builders, so
        # typing there can never rewrite whichever step the Macro tab has selected.
        self.builder = {key: tk.StringVar(value=STEP_DEFAULT[key])
                        for key in ("button", "keys", "count", "hold", "wait")}

        self.clicker = Clicker(make_device(), self._spec(), focused_window=active_title)
        self.listener = None
        self._build()
        self._refresh()
        self._select(0)
        self._sync_run()
        self._register_hotkeys()

        # Profiles live outside the app folder, so nothing is written next to the
        # script. The passed config seeds 'default' on first run only.
        if use_profiles:
            self._open_startup_profile(config)
        else:
            self._snapshot = json.dumps(self._config(), sort_keys=True)
            self._refresh_profiles()

        root.minsize(780, 560)
        root.update_idletasks()
        x = max(0, (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2)
        y = max(0, (root.winfo_screenheight() - root.winfo_reqheight()) // 3)
        root.geometry(f"+{x}+{y}")
        root.protocol("WM_DELETE_WINDOW", self.close)

    # --- layout -------------------------------------------------------------

    def _build(self):
        self.kind_trees = {}
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self._header()
        notebook = ttk.Notebook(self.root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=12)
        self._tab_settings(notebook)
        self._tab_kind(notebook, "Mouse", "mouse")
        self._tab_kind(notebook, "Keyboard", "key")
        self._tab_kind(notebook, "Key combos", "combo")
        self._tab_macro(notebook)
        self._footer()

    def _header(self):
        bar = ttk.Frame(self.root, padding=(12, 12, 12, 8))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        self.run_button = ttk.Button(bar, text="\u25b6  Start", command=self.toggle,
                                     style="Accent.TButton")
        self.run_button.grid(row=0, column=0, sticky="w")
        line = ttk.Frame(bar)
        line.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        line.columnconfigure(1, weight=1)
        self.dot = tk.Canvas(line, width=14, height=14, highlightthickness=0, background=self.bg)
        self.dot.grid(row=0, column=0)
        self._dot = self.dot.create_oval(4, 4, 11, 11, fill="#57606a", outline="")
        ttk.Label(line, textvariable=self.status, wraplength=430, justify="left").grid(
            row=0, column=1, sticky="w", padx=(6, 0))

    def _footer(self):
        bar = ttk.Frame(self.root, padding=(12, 8, 12, 12))
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)
        left = ttk.Frame(bar)
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Profile:").pack(side="left", padx=(0, 6))
        self.profile_box = ttk.Combobox(left, textvariable=self.profile, state="readonly",
                                        width=18, values=[])
        self.profile_box.pack(side="left")
        self.profile_box.bind("<<ComboboxSelected>>", lambda _event: self._switch_profile())
        for text, command in (("Save", self.save), ("Save as\u2026", self.save_as),
                              ("Delete", self.delete), ("Import\u2026", self.load)):
            ttk.Button(left, text=text, command=command).pack(side="left", padx=(6, 0))
        ttk.Label(bar, textvariable=self.error, style="Error.TLabel", wraplength=620,
                  justify="left").grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _tab_settings(self, notebook):
        page = ttk.Frame(notebook, padding=12)

        hot = ttk.LabelFrame(page, text=" Hotkeys ", padding=10)
        hot.pack(fill="x")
        hot.columnconfigure(1, weight=1)
        row = self._field(hot, 0, "Toggle hotkey", self._capture(hot, self.toggle_key),
                          "Click the box, then press the combo, e.g. ctrl+alt+s. "
                          "Starts and stops clicking.")
        row = self._field(hot, row, "Panic hotkey", self._capture(hot, self.panic_key),
                          "Click the box, then press the combo. Stops clicking straight away.")
        ttk.Label(hot, style="Hint.TLabel", justify="left", wraplength=460,
                  text="Global hotkeys work on Windows, macOS and Linux/X11.\n"
                       "On Wayland they may not fire - use the Start/Stop button.").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))

        timing = ttk.LabelFrame(page, text=" Timing ", padding=10)
        timing.pack(fill="x", pady=(10, 0))
        timing.columnconfigure(1, weight=1)
        row = 0
        for label, name in TIMING:
            row = self._field(timing, row, label,
                              ttk.Entry(timing, textvariable=self.timing[name]),
                              FIELD_HELP.get(name))
        self._field(timing, row, "Only click in window",
                    ttk.Entry(timing, textvariable=self.window),
                    "Only click while the focused window title contains this text; empty "
                    "always clicks. Wayland: matches X11/XWayland apps only.")
        notebook.add(page, text="  Settings  ")

    def _tab_kind(self, notebook, title, kind):
        """A focused builder for one step kind, plus a list of just those steps."""
        page = ttk.Frame(notebook, padding=12)
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=1, minsize=300)

        left = ttk.Frame(page)
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        tree = ttk.Treeview(left, columns=("n", "detail", "count"), show="headings",
                            height=7, selectmode="browse")
        for name, text, width in (("n", "#", 40), ("detail", "Detail", 170),
                                  ("count", "Count", 70)):
            tree.heading(name, text=text)
            tree.column(name, width=width, anchor="w", stretch=(name == "detail"))
        tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scroll.set)
        tree.bind("<<TreeviewSelect>>", lambda event, k=kind: self._on_kind_select(k))
        self.kind_trees[kind] = tree

        builder = ttk.LabelFrame(page, text=f" {title} step ", padding=10)
        builder.grid(row=0, column=1, sticky="new", padx=(14, 0))
        builder.columnconfigure(1, weight=1)
        row = self._kind_form(builder, kind)
        ttk.Button(builder, text="Add to macro", command=lambda: self._add_kind(kind)).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(left, style="Hint.TLabel", wraplength=330, justify="left",
                  text="Added steps join the Macro tab in run order.").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        notebook.add(page, text=f"  {title}  ")

    def _kind_form(self, builder, kind):
        if kind == "mouse":
            row = self._field(builder, 0, "Button",
                              self._radios(builder, self.builder["button"],
                                           ["left", "right", "middle"]),
                              "Which mouse button this step clicks.")
        elif kind == "key":
            row = self._field(builder, 0, "Key",
                              self._capture(builder, self.builder["keys"], single=True),
                              "Click the box, then press a single key, e.g. a or enter.")
        else:
            row = self._field(builder, 0, "Key combo",
                              self._capture(builder, self.builder["keys"]),
                              "Click the box, then press two or more keys, e.g. ctrl+c.")
        for label, key, hint in (
                ("Press count", "count", "How many times this step runs each tick."),
                ("Hold each (s)", "hold", "Seconds to keep the button or key held down."),
                ("Wait after (s)", "wait", "Seconds to pause after this step.")):
            row = self._field(builder, row, label,
                              ttk.Entry(builder, textvariable=self.builder[key]), hint)
        return row

    def _add_kind(self, kind):
        keys = [k for k in self.builder["keys"].get().split("+") if k.strip()]
        if kind == "combo" and len(keys) < 2:
            self._fail("a key combo needs at least 2 keys - use the Keyboard tab for one key")
            return
        if kind == "key" and len(keys) != 1:
            self._fail("the Keyboard tab takes exactly one key - use Key combos for several")
            return
        step = dict(STEP_DEFAULT)
        for key in ("count", "hold", "wait"):
            value = self.builder[key].get().strip()
            if value:
                step[key] = value
        if kind == "mouse":
            step["button"] = self.builder["button"].get() or "left"
        else:
            step["action"] = "keys"
            step["keys"] = "+".join(keys)
        self.error.set("")
        self.steps.append(step)
        self.index = len(self.steps) - 1
        self._refresh()
        self._select(self.index)

    def _tab_macro(self, notebook):
        page = ttk.Frame(notebook, padding=12)
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=1, minsize=330)

        left = ttk.Frame(page)
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(left, columns=("n", "action", "detail", "count"),
                                 show="headings", height=7, selectmode="browse")
        for name, text, width in (("n", "#", 40), ("action", "Action", 80),
                                  ("detail", "Detail", 170), ("count", "Count", 70)):
            self.tree.heading(name, text=text)
            self.tree.column(name, width=width, anchor="w", stretch=(name == "detail"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        tools = ttk.Frame(left)
        tools.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        for text, command in (("Add", self._add_step), ("Remove", self._remove_step),
                              ("Up", lambda: self._move(-1)), ("Down", lambda: self._move(1))):
            ttk.Button(tools, text=text, width=8, command=command).pack(side="left", padx=(0, 4))
        ttk.Label(left, style="Hint.TLabel", wraplength=330, justify="left",
                  text="Steps run in order, once per tick.").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        editor = ttk.LabelFrame(page, text=" Selected step ", padding=10)
        editor.grid(row=0, column=1, sticky="new", padx=(14, 0))
        editor.columnconfigure(1, weight=1)
        self._field(editor, 0, "Action", self._radios(editor, self.step["action"], ["mouse", "keys"]),
                    "mouse = click a button. keys = press a key combo.")
        box = ttk.Frame(editor)
        box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        box.columnconfigure(0, weight=1)
        self.button_row = self._group(box, "Button",
                                      self._radios(box, self.step["button"],
                                                   ["left", "right", "middle"]),
                                      "Which mouse button this step clicks.")
        self.keys_row = self._group(box, "Key combo", self._capture(box, self.step["keys"]),
                                    "Click the box, then press the keys, e.g. ctrl+c.")
        self.button_row.grid(row=0, column=0, sticky="ew")
        self.keys_row.grid(row=0, column=0, sticky="ew")
        row = 2
        for label, key, hint in (
                ("Press count", "count", "How many times this step runs each tick."),
                ("Hold each (s)", "hold", "Seconds to keep the button or key held down."),
                ("Wait after (s)", "wait", "Seconds to pause after this step.")):
            row = self._field(editor, row, label, ttk.Entry(editor, textvariable=self.step[key]), hint)
        self._sync_action()
        notebook.add(page, text="  Macro  ")

    def _field(self, parent, row, label, widget, hint=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        widget.grid(row=row, column=1, sticky="ew", pady=4)
        if hint:
            _Tooltip(widget, hint)
        return row + 1

    def _group(self, parent, label, widget, hint=None):
        """A label+widget row in its own frame, so it can be hidden as a unit."""
        frame = ttk.Frame(parent)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=label).grid(row=0, column=0, sticky="w", padx=(0, 10))
        widget.grid(row=0, column=1, sticky="ew")
        if hint:
            _Tooltip(widget, hint)
        return frame

    def _radios(self, parent, var, options):
        frame = ttk.Frame(parent)
        for option in options:
            ttk.Radiobutton(frame, text=option, value=option, variable=var).pack(side="left")
        return frame

    def _capture(self, parent, var, single=False):
        entry = ttk.Entry(parent, textvariable=var)
        entry.bind("<KeyPress>", lambda event: self._captured(event, var, single))
        entry.bind("<FocusOut>", lambda event: self._register_hotkeys())
        return entry

    def _captured(self, event, var, single=False):
        combo = format_hotkey(event.keysym, event.state)
        if combo and (not single or "+" not in combo):
            var.set(combo)
        return "break"  # keep the typed key out of the entry

    def _sync_action(self):
        """A mouse step has no key combo, a keys step has no button."""
        if self.step["action"].get() == "keys":
            self.button_row.grid_remove()
            self.keys_row.grid()
        else:
            self.keys_row.grid_remove()
            self.button_row.grid()

    # --- macro list <-> step editor -----------------------------------------

    def _on_select(self, event=None):
        selection = self.tree.selection()
        if selection and int(selection[0]) != self.index:
            self._select(int(selection[0]))

    def _on_kind_select(self, kind):
        selection = self.kind_trees[kind].selection()
        if selection and int(selection[0]) != self.index:
            self._select(int(selection[0]))

    def _select(self, index):
        if not self.steps:
            return
        self.index = max(0, min(index, len(self.steps) - 1))
        self._loading = True
        for key, var in self.step.items():
            var.set(self.steps[self.index][key])
        self._loading = False
        self._sync_selection()

    def _sync_selection(self):
        """Highlight the selected step in every list.

        Tk queues <<TreeviewSelect>> for these selection_set calls; the handlers
        ignore an event whose index already equals self.index, so no echo loop.
        """
        for tree in (self.tree, *self.kind_trees.values()):
            iid = str(self.index)
            if tree.exists(iid):
                tree.selection_set(iid)
                tree.see(iid)

    def _store_step(self):
        if self._loading or not self.steps:
            return
        self.steps[self.index] = {key: var.get() for key, var in self.step.items()}
        self._refresh()

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, step in enumerate(self.steps):
            detail = step["keys"] if step["action"] == "keys" else step["button"]
            self.tree.insert("", "end", iid=str(i),
                             values=(i + 1, step["action"], detail or "-", f'x{step["count"]}'))
        for kind, tree in self.kind_trees.items():
            tree.delete(*tree.get_children())
            for i, step in enumerate(self.steps):
                if _kind(step) != kind:
                    continue
                detail = step["button"] if kind == "mouse" else step["keys"]
                tree.insert("", "end", iid=str(i),
                            values=(i + 1, detail or "-", f'x{step["count"]}'))
        self._sync_selection()

    def _add_step(self):
        self.steps.append(dict(STEP_DEFAULT))
        self.index = len(self.steps) - 1
        self._refresh()
        self._select(self.index)

    def _remove_step(self):
        if len(self.steps) <= 1:
            self._fail("a macro needs at least one step")
            return
        self.error.set("")
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
        self._select(self.index)

    # --- running ------------------------------------------------------------

    def _fail(self, message):
        self.error.set(message)

    def _register_hotkeys(self):
        if self.listener:
            try:
                self.listener.stop()  # pynput raises if stopped right after start
            except Exception:
                pass
            self.listener = None
        try:
            self.listener = keyboard.GlobalHotKeys({
                self.toggle_key.get(): self._hotkey_toggle,
                self.panic_key.get(): self._hotkey_stop,
            })
            self.listener.start()
            if not self.clicker.running:  # don't overwrite the run state on focus loss
                warn = (" (global hotkeys may not fire on Wayland - use the button)"
                        if os.environ.get("XDG_SESSION_TYPE") == "wayland" else "")
                self.status.set(f"ready - {self.toggle_key.get()} start/stop, "
                                f"{self.panic_key.get()} stop{warn}")
        except Exception as exc:
            self._fail(f"hotkey error: {exc}")

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
            self._fail(f"bad setting: {exc}")
            return
        self.error.set("")
        self.clicker.set_spec(spec)
        started = self.clicker.toggle()
        issue = problem() if started else None
        if issue:
            self.status.set(f"running, but input will not be sent: {issue}")
        elif started and spec["window"] and os.environ.get("XDG_SESSION_TYPE") == "wayland":
            # X11 title queries cannot see native Wayland windows, so this filter
            # matches XWayland apps only. Running is still right (the engine keeps
            # re-reading the title); refusing would break that, so say so instead.
            self.status.set("running - window filter matches XWayland apps only on "
                            "Wayland (clear it to click everywhere)")
        else:
            self.status.set("running" if started else "stopped")
        self._sync_run()

    def stop(self):
        self.clicker.stop()
        self.status.set("stopped")
        self._sync_run()

    def _sync_run(self):
        """Mirror the engine's state on the button and dot."""
        running = self.clicker.running
        self.run_button.configure(text="\u25a0  Stop" if running else "\u25b6  Start",
                                  style="Stop.TButton" if running else "Accent.TButton")
        self.dot.itemconfig(self._dot, fill="#1f883d" if running else "#57606a")
        if running and self._poll is None:
            self._poll = self.root.after(400, self._watch)
        elif not running and self._poll is not None:
            self.root.after_cancel(self._poll)
            self._poll = None

    def _watch(self):
        """The engine can finish on its own (finite repeat/duration) - catch up."""
        self._poll = None
        if not self.clicker.running:
            self.status.set("stopped")
        self._sync_run()

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
        self.error.set("")
        self.status.set("profile loaded")

    # --- profiles -----------------------------------------------------------

    def _profile_path(self, name):
        return _profiles_dir() / f"{name}.json"

    def _profile_names(self):
        try:
            return sorted(p.stem for p in _profiles_dir().glob("*.json"))
        except OSError:
            return []

    def _refresh_profiles(self):
        names = self._profile_names()
        self.profile_box.configure(values=names)
        if self.profile.get() not in names:
            self.profile.set(names[0] if names else "")

    def _dirty(self):
        try:
            return json.dumps(self._config(), sort_keys=True) != self._snapshot
        except Exception:
            return True  # a half-typed number counts as unsaved

    def _remember(self, name):
        try:
            _profiles_dir().joinpath(".last").write_text(name)
        except OSError:
            pass

    def _write_profile(self, name, config=None):
        try:
            folder = _profiles_dir()
            folder.mkdir(parents=True, exist_ok=True)
            self._profile_path(name).write_text(
                json.dumps(config if config is not None else self._config(), indent=2))
        except Exception as exc:
            self._fail(f"could not save '{name}': {exc}")
            return False
        self.error.set("")
        self._snapshot = json.dumps(self._config(), sort_keys=True)
        return True

    def _load_profile(self, name):
        try:
            config = json.loads(self._profile_path(name).read_text())
        except Exception as exc:
            self._fail(f"bad profile '{name}': {exc}")
            return False
        self._apply(config)
        self._loaded = name
        self.profile.set(name)
        self._snapshot = json.dumps(self._config(), sort_keys=True)
        self._remember(name)
        self.status.set(f"profile '{name}'")
        self._refresh_profiles()
        return True

    def _open_startup_profile(self, config):
        """Seed the folder on first run, then reopen the last profile used."""
        try:
            folder = _profiles_dir()
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._fail(f"no profile folder: {exc}")
            self._snapshot = json.dumps(self._config(), sort_keys=True)
            return
        if not self._profile_names():
            self._write_profile("default", config)
        try:
            last = folder.joinpath(".last").read_text().strip()
        except OSError:
            last = ""
        name = last if last in self._profile_names() else "default"
        if not self._load_profile(name):
            self._refresh_profiles()

    def _confirm_discard(self):
        """True when it is safe to lose the current edits; offers to save them."""
        if not self._dirty():
            return True
        name = self._loaded or "default"
        answer = messagebox.askyesnocancel("neverKickOff",
                                           f"Save changes to \"{name}\" before switching?")
        if answer is None:
            return False
        if answer and not self._write_profile(name):
            return False
        if answer:
            self._loaded = name
            self.profile.set(name)
            self._refresh_profiles()
            self.status.set(f"saved '{name}'")
        return True

    def _switch_profile(self):
        name = self.profile.get()
        if name == self._loaded:
            return
        if not self._confirm_discard() or not self._load_profile(name):
            self.profile.set(self._loaded)

    def save(self):
        name = self._loaded or self.profile.get()
        if not name:
            self.save_as()  # nothing to overwrite yet
            return
        try:
            self._config()  # validate before writing, so a bad field cannot land
        except Exception as exc:
            self._fail(f"bad setting: {exc}")
            return
        if self._write_profile(name):
            self._loaded = name
            self.profile.set(name)
            self._refresh_profiles()
            self.status.set(f"saved '{name}'")

    def save_as(self):
        name = simpledialog.askstring("Save profile", "Profile name:", parent=self.root,
                                      initialvalue=self._loaded or "profile")
        if name is None:
            return
        name = _profile_name(name)
        if not name:
            self._fail("a profile name cannot be empty or contain / or \\")
            return
        try:
            self._config()
        except Exception as exc:
            self._fail(f"bad setting: {exc}")
            return
        if self._write_profile(name):
            self._loaded = name
            self._remember(name)
            self._refresh_profiles()
            self.profile.set(name)
            self.status.set(f"saved '{name}'")

    def delete(self):
        name = self._loaded or self.profile.get()
        if not name:
            return
        if not messagebox.askyesno("neverKickOff", f"Delete profile \"{name}\"?"):
            return
        try:
            self._profile_path(name).unlink()
        except OSError as exc:
            self._fail(f"could not delete '{name}': {exc}")
            return
        self.error.set("")
        for name in self._profile_names():  # skip any that fail to parse
            if self._load_profile(name):
                return
        # editor keeps its content, but it is unsaved and Save has no target
        self._loaded = ""
        self._snapshot = ""
        self.profile.set("")
        self._refresh_profiles()
        self.status.set("no profiles left - Save as\u2026 to make one")

    def load(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            config = json.loads(Path(path).read_text())
        except Exception as exc:
            self._fail(f"bad profile: {exc}")
            return
        if not self._confirm_discard():
            return
        self._apply(config)
        self._loaded = ""
        self.profile.set("")
        self._snapshot = json.dumps(self._config(), sort_keys=True)
        self.status.set(f"imported {Path(path).name} - Save as\u2026 to keep it")

    def close(self):
        if not self._confirm_discard():
            return
        if self._poll is not None:
            self.root.after_cancel(self._poll)
            self._poll = None
        self.clicker.stop()
        if self.listener:
            try:
                self.listener.stop()
            except Exception:  # pynput raises if stopped right after start
                pass
        self.root.destroy()


def main():
    # No argument means the normal `nko` launch: the saved profile list is reused.
    # An explicit path is a one-off, so the profile list stays out of the way.
    explicit = len(sys.argv) > 1
    path = Path(sys.argv[1]) if explicit else Path(__file__).with_name("config.json")
    root = tk.Tk()
    App(root, json.loads(path.read_text()), use_profiles=not explicit)
    root.mainloop()


if __name__ == "__main__":
    main()
