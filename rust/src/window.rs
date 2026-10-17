//! Best-effort title of the focused window - the Rust half of `window.py`.
//!
//! Used by the "only click while X is focused" option. Returns None when the
//! title cannot be read, which the engine treats as "not a match" (safer: don't
//! click).

/// Whatever an underlying API handed back, before it is normalised.
pub enum RawTitle<'a> {
    Bytes(&'a [u8]),
    Text(&'a str),
    Unavailable,
}

/// Bytes/str -> title or None, matching `window._as_text`.
///
/// python-xlib hands back bytes for some windows; the engine compares str, so
/// the bytes are decoded the same lossy way Python does.
pub fn as_text(value: RawTitle<'_>) -> Option<String> {
    match value {
        RawTitle::Bytes(bytes) => {
            let text = String::from_utf8_lossy(bytes).to_string();
            if text.is_empty() {
                None
            } else {
                Some(text)
            }
        }
        RawTitle::Text(text) => {
            if text.is_empty() {
                None
            } else {
                Some(text.to_string())
            }
        }
        RawTitle::Unavailable => None,
    }
}

/// The title of the focused window, or None when it cannot be read.
///
/// X11 only, and only when `xdotool` is installed: the Python version reads the
/// window through python-xlib, which comes with pynput. Windows and macOS titles
/// are a known gap (see MIGRATION_REPORT.md).
pub fn active_title() -> Option<String> {
    if std::env::var("XDG_SESSION_TYPE").as_deref() == Ok("wayland") {
        // The compositor only lets XWayland clients be inspected, exactly as
        // python-xlib sees them, so a Wayland title is not reachable here.
        return None;
    }
    if !on_path("xdotool") {
        return None;
    }
    let output = std::process::Command::new("xdotool")
        .args(["getactivewindow", "getwindowname"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if text.is_empty() {
        None
    } else {
        Some(text)
    }
}

fn on_path(binary: &str) -> bool {
    std::env::var_os("PATH")
        .map(|paths| std::env::split_paths(&paths).any(|dir| dir.join(binary).is_file()))
        .unwrap_or(false)
}
