"""Turn a tkinter key event into a pynput hotkey string.

No tkinter import, so the mapping can be tested without a display: the GUI's
key-capture widget calls format_hotkey(event.keysym, event.state).
"""

# tkinter event.state bits. Order controls the printed order.
MODIFIERS = [
    (0x0004, "ctrl"),
    (0x0008, "alt"),
    (0x0001, "shift"),
    (0x0040, "cmd"),
]

# Keysym values that are a modifier on their own; a hotkey needs a real key.
MODIFIER_KEYSYMS = {
    "shift_l", "shift_r", "control_l", "control_r", "alt_l", "alt_r",
    "super_l", "super_r", "meta_l", "meta_r", "caps_lock", "num_lock",
    "iso_level3_shift",
}

# tkinter keysym -> pynput Key name, where they differ.
NAMES = {
    "escape": "esc",
    "return": "enter",
    "kp_enter": "enter",
    "prior": "page_up",
    "next": "page_down",
    "print": "print_screen",
    "back_space": "backspace",
}


def _token(name):
    """pynput wants '<ctrl>', '<f6>' but a bare 's' for single characters."""
    return name if len(name) == 1 else f"<{name}>"


def format_hotkey(keysym, state):
    """'s' with Ctrl+Alt held -> '<ctrl>+<alt>+s'. None if only a modifier was pressed."""
    keysym = keysym.lower()
    if keysym in MODIFIER_KEYSYMS:
        return None
    name = NAMES.get(keysym, keysym)
    if not name:
        return None
    parts = [_token(modifier) for bit, modifier in MODIFIERS if state & bit]
    parts.append(_token(name))
    return "+".join(parts)
