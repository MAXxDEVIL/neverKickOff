"""Best-effort title of the focused window.

Used by the "only click while X is focused" option. Returns None when the title
cannot be read, which the engine treats as "not a match" (safer: don't click).
The underlying libraries already come with pynput on each platform.
"""
import sys

_x11_display = None  # one X connection, not one per tick


def active_title():
    try:
        if sys.platform.startswith("win"):
            return _windows()
        if sys.platform == "darwin":
            return _macos()
        return _x11()
    except Exception:
        return None


def _windows():
    import ctypes
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value or None


def _macos():
    from AppKit import NSWorkspace
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return app.localizedName() if app else None


def _x11():
    global _x11_display
    if _x11_display is None:
        from Xlib import display
        _x11_display = display.Display()
    d = _x11_display
    for window in (d.get_input_focus().focus, _active_window(d)):
        if window is None:
            continue
        try:
            title = _title(d, window)
        except Exception:
            continue
        if title:
            return title
    return None


def _active_window(d):
    """The window the WM reports as active (_NET_ACTIVE_WINDOW), if it reports one."""
    prop = d.screen().root.get_full_property(d.intern_atom("_NET_ACTIVE_WINDOW"), 0)
    if prop and len(prop.value) and prop.value[0]:
        return d.create_resource_object("window", prop.value[0])
    return None


def _title(d, window):
    """WM_NAME, else the UTF-8 _NET_WM_NAME that GTK/Chromium apps set instead."""
    name = _as_text(window.get_wm_name())
    if name:
        return name
    prop = window.get_full_property(d.intern_atom("_NET_WM_NAME"), 0)
    return _as_text(prop.value if prop else None)


def _as_text(value):
    """python-xlib hands back bytes for some windows; the engine compares str."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace") or None
    return value or None
