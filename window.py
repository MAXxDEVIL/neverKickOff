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
    # shortcut: input focus's WM_NAME only; some apps set _NET_WM_NAME (UTF-8)
    # instead. Upgrade to read _NET_WM_NAME if titles come back empty.
    return _x11_display.get_input_focus().focus.get_wm_name() or None
