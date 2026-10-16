"""Input injection through ydotool, for Wayland sessions.

pynput drives the X11/XWayland server, and a Wayland compositor ignores the
synthetic events it produces, so clicking silently does nothing there. ydotool
injects at the kernel level through /dev/uinput, which the compositor does
honour. It needs the `ydotool` binary and its `ydotoold` daemon running; see
the Wayland section of README.md.

main.make_device() prefers it on any session that is not X11, where pynput
cannot inject at all.
"""
import os
import shutil
import subprocess

# ydotool's button bitmask: the low bits pick the button, 0x40 means press and
# 0x80 means release, so left-down is 0x40 and right-up is 0x81.
BUTTONS = {
    "left": 0x00,
    "right": 0x01,
    "middle": 0x02,
}

# pynput Key.name -> the KEY_* name in <linux/input-event-codes.h>.
KEYS = {
    "ctrl": "LEFTCTRL", "ctrl_l": "LEFTCTRL", "ctrl_r": "RIGHTCTRL",
    "alt": "LEFTALT", "alt_l": "LEFTALT", "alt_r": "RIGHTALT", "alt_gr": "RIGHTALT",
    "shift": "LEFTSHIFT", "shift_l": "LEFTSHIFT", "shift_r": "RIGHTSHIFT",
    "cmd": "LEFTMETA", "cmd_l": "LEFTMETA", "cmd_r": "RIGHTMETA",
    "enter": "ENTER", "esc": "ESC", "tab": "TAB", "space": "SPACE",
    "backspace": "BACKSPACE", "delete": "DELETE", "insert": "INSERT",
    "up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT",
    "home": "HOME", "end": "END", "page_up": "PAGEUP", "page_down": "PAGEDOWN",
    "caps_lock": "CAPSLOCK", "num_lock": "NUMLOCK", "print_screen": "SYSRQ",
    "pause": "PAUSE", "menu": "MENU",
}
KEYS.update({f"f{i}": f"F{i}" for i in range(1, 21)})

# Punctuation parse_combo can produce; letters and digits are handled directly.
SYMBOLS = {
    "-": "KEY_MINUS", "=": "KEY_EQUAL", "[": "KEY_LEFTBRACE", "]": "KEY_RIGHTBRACE",
    ";": "KEY_SEMICOLON", "'": "KEY_APOSTROPHE", ",": "KEY_COMMA", ".": "KEY_DOT",
    "/": "KEY_SLASH", "\\": "KEY_BACKSLASH", "`": "KEY_GRAVE",
}


def available():
    """True when this session should inject through ydotool rather than pynput.

    Not tied to Wayland: it is simply "ydotool is installed and we are not on
    X11", so a session that never set XDG_SESSION_TYPE still works. ydotool
    also runs on X11, but pynput is lighter there, so X11 keeps pynput.
    """
    return bool(shutil.which("ydotool")) and os.environ.get("XDG_SESSION_TYPE") != "x11"


def problem(run=subprocess.run):
    """Why injected input will not arrive, or None when it will.

    On X11 pynput always works. Everywhere else we need ydotool, and its daemon
    must be reachable: `ydotool debug` connects to the socket and injects
    nothing, so a non-zero exit means ydotoold is not running.
    """
    if not available():
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            return ("Wayland ignores pynput's input: install ydotool and start "
                    "ydotoold (see the Wayland section of README.md)")
        return None
    probe = run(["ydotool", "debug"], capture_output=True, text=True)
    if probe.returncode:
        lines = (probe.stdout or "").strip().splitlines()
        return f"ydotool cannot reach ydotoold ({lines[0] if lines else 'no response'})"
    return None


def keycode(key):
    """pynput Key/KeyCode -> a Linux input-event keycode (evdev's KEY_*)."""
    from evdev import ecodes
    char = getattr(key, "char", None)
    if char:
        if "a" <= char <= "z":
            name = "KEY_" + char.upper()
        elif "0" <= char <= "9":
            name = "KEY_" + char
        else:
            name = SYMBOLS.get(char)
        if not name:
            raise ValueError(f"ydotool has no keycode for {char!r}")
        return ecodes.ecodes[name]
    name = KEYS.get(getattr(key, "name", None))
    if not name:
        raise ValueError(f"ydotool has no keycode for {key!r}")
    return ecodes.ecodes["KEY_" + name]


class YdotoolDevice:
    """Same interface as main.PynputDevice, but every call shells out to ydotool.

    `run` is injectable so tests can check the commands without ydotool installed.
    """

    def __init__(self, run=subprocess.run):
        self._run = run

    def _exec(self, *args):
        self._run(["ydotool", *args], check=True)

    def mouse_press(self, button):
        self._exec("click", hex(0x40 | BUTTONS[button]))

    def mouse_release(self, button):
        self._exec("click", hex(0x80 | BUTTONS[button]))

    def key_press(self, key):
        self._exec("key", f"{keycode(key)}:1")

    def key_release(self, key):
        self._exec("key", f"{keycode(key)}:0")
