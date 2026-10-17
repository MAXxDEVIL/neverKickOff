//! Input injection through ydotool, for Wayland sessions - the Rust half of
//! `ydotool.py`.
//!
//! Shells out exactly like the Python version, so it needs no crate and no FFI:
//! this is the backend that actually works on Wayland.

use crate::device::{Device, DeviceError};
use crate::keys::Key;

/// ydotool's button bitmask: low bits pick the button, 0x40 is press, 0x80 release.
pub const BUTTONS: &[(&str, u8)] = &[("left", 0x00), ("right", 0x01), ("middle", 0x02)];

/// pynput `Key.name` -> the `KEY_*` name in `<linux/input-event-codes.h>`.
pub const KEYS: &[(&str, &str)] = &[
    ("ctrl", "LEFTCTRL"),
    ("ctrl_l", "LEFTCTRL"),
    ("ctrl_r", "RIGHTCTRL"),
    ("alt", "LEFTALT"),
    ("alt_l", "LEFTALT"),
    ("alt_r", "RIGHTALT"),
    ("alt_gr", "RIGHTALT"),
    ("shift", "LEFTSHIFT"),
    ("shift_l", "LEFTSHIFT"),
    ("shift_r", "RIGHTSHIFT"),
    ("cmd", "LEFTMETA"),
    ("cmd_l", "LEFTMETA"),
    ("cmd_r", "RIGHTMETA"),
    ("enter", "ENTER"),
    ("esc", "ESC"),
    ("tab", "TAB"),
    ("space", "SPACE"),
    ("backspace", "BACKSPACE"),
    ("delete", "DELETE"),
    ("insert", "INSERT"),
    ("up", "UP"),
    ("down", "DOWN"),
    ("left", "LEFT"),
    ("right", "RIGHT"),
    ("home", "HOME"),
    ("end", "END"),
    ("page_up", "PAGEUP"),
    ("page_down", "PAGEDOWN"),
    ("caps_lock", "CAPSLOCK"),
    ("num_lock", "NUMLOCK"),
    ("print_screen", "SYSRQ"),
    ("pause", "PAUSE"),
    ("menu", "MENU"),
];

/// Punctuation `parse_combo` can produce; letters and digits are handled directly.
pub const SYMBOLS: &[(&str, &str)] = &[
    ("-", "KEY_MINUS"),
    ("=", "KEY_EQUAL"),
    ("[", "KEY_LEFTBRACE"),
    ("]", "KEY_RIGHTBRACE"),
    (";", "KEY_SEMICOLON"),
    ("'", "KEY_APOSTROPHE"),
    (",", "KEY_COMMA"),
    (".", "KEY_DOT"),
    ("/", "KEY_SLASH"),
    ("\\", "KEY_BACKSLASH"),
    ("`", "KEY_GRAVE"),
];

/// `KEY_*` name -> Linux input-event code, dumped from evdev (Linux 6.x).
pub const LINUX_CODES: &[(&str, u16)] = &[
    ("KEY_ESC", 1),
    ("KEY_1", 2),
    ("KEY_2", 3),
    ("KEY_3", 4),
    ("KEY_4", 5),
    ("KEY_5", 6),
    ("KEY_6", 7),
    ("KEY_7", 8),
    ("KEY_8", 9),
    ("KEY_9", 10),
    ("KEY_0", 11),
    ("KEY_MINUS", 12),
    ("KEY_EQUAL", 13),
    ("KEY_BACKSPACE", 14),
    ("KEY_TAB", 15),
    ("KEY_Q", 16),
    ("KEY_W", 17),
    ("KEY_E", 18),
    ("KEY_R", 19),
    ("KEY_T", 20),
    ("KEY_Y", 21),
    ("KEY_U", 22),
    ("KEY_I", 23),
    ("KEY_O", 24),
    ("KEY_P", 25),
    ("KEY_LEFTBRACE", 26),
    ("KEY_RIGHTBRACE", 27),
    ("KEY_ENTER", 28),
    ("KEY_LEFTCTRL", 29),
    ("KEY_A", 30),
    ("KEY_S", 31),
    ("KEY_D", 32),
    ("KEY_F", 33),
    ("KEY_G", 34),
    ("KEY_H", 35),
    ("KEY_J", 36),
    ("KEY_K", 37),
    ("KEY_L", 38),
    ("KEY_SEMICOLON", 39),
    ("KEY_APOSTROPHE", 40),
    ("KEY_GRAVE", 41),
    ("KEY_LEFTSHIFT", 42),
    ("KEY_BACKSLASH", 43),
    ("KEY_Z", 44),
    ("KEY_X", 45),
    ("KEY_C", 46),
    ("KEY_V", 47),
    ("KEY_B", 48),
    ("KEY_N", 49),
    ("KEY_M", 50),
    ("KEY_COMMA", 51),
    ("KEY_DOT", 52),
    ("KEY_SLASH", 53),
    ("KEY_RIGHTSHIFT", 54),
    ("KEY_LEFTALT", 56),
    ("KEY_SPACE", 57),
    ("KEY_CAPSLOCK", 58),
    ("KEY_F1", 59),
    ("KEY_F2", 60),
    ("KEY_F3", 61),
    ("KEY_F4", 62),
    ("KEY_F5", 63),
    ("KEY_F6", 64),
    ("KEY_F7", 65),
    ("KEY_F8", 66),
    ("KEY_F9", 67),
    ("KEY_F10", 68),
    ("KEY_NUMLOCK", 69),
    ("KEY_F11", 87),
    ("KEY_F12", 88),
    ("KEY_RIGHTCTRL", 97),
    ("KEY_SYSRQ", 99),
    ("KEY_RIGHTALT", 100),
    ("KEY_HOME", 102),
    ("KEY_UP", 103),
    ("KEY_PAGEUP", 104),
    ("KEY_LEFT", 105),
    ("KEY_RIGHT", 106),
    ("KEY_END", 107),
    ("KEY_DOWN", 108),
    ("KEY_PAGEDOWN", 109),
    ("KEY_INSERT", 110),
    ("KEY_DELETE", 111),
    ("KEY_PAUSE", 119),
    ("KEY_LEFTMETA", 125),
    ("KEY_RIGHTMETA", 126),
    ("KEY_MENU", 139),
    ("KEY_F13", 183),
    ("KEY_F14", 184),
    ("KEY_F15", 185),
    ("KEY_F16", 186),
    ("KEY_F17", 187),
    ("KEY_F18", 188),
    ("KEY_F19", 189),
    ("KEY_F20", 190),
];

fn lookup<'a>(table: &'a [(&'a str, &'a str)], name: &str) -> Option<&'a str> {
    table.iter().find(|(k, _)| *k == name).map(|(_, v)| *v)
}

/// `KEYS` plus the f1..f20 entries Python adds with `KEYS.update(...)`.
fn named_key(name: &str) -> Option<String> {
    if let Some(rest) = name.strip_prefix('f') {
        if let Ok(number) = rest.parse::<usize>() {
            if (1..=20).contains(&number) {
                return Some(format!("F{}", number));
            }
        }
    }
    lookup(KEYS, name).map(|s| s.to_string())
}

/// `ydotool.keycode`: a key -> a Linux input-event keycode.
///
/// The `Err` string is not part of the contract - Python's version embeds a
/// pynput repr that has no meaning here - but the failure itself is.
pub fn keycode(key: &Key) -> Result<u16, String> {
    let name = match key {
        Key::Char { ch } => {
            let ch = *ch;
            if ch.is_ascii_lowercase() {
                format!("KEY_{}", ch.to_ascii_uppercase())
            } else if ch.is_ascii_digit() {
                format!("KEY_{}", ch)
            } else {
                match lookup(SYMBOLS, &ch.to_string()) {
                    Some(named) => named.to_string(),
                    None => return Err(format!("ydotool has no keycode for '{}'", ch)),
                }
            }
        }
        Key::Named { name } => match named_key(name) {
            Some(named) => format!("KEY_{}", named),
            None => return Err(format!("ydotool has no keycode for Key.{}", name)),
        },
    };
    LINUX_CODES
        .iter()
        .find(|(n, _)| *n == name)
        .map(|(_, code)| *code)
        .ok_or_else(|| format!("ydotool has no keycode for {}", name))
}

/// `shutil.which`, good enough for "is this binary on PATH".
fn which(binary: &str) -> bool {
    std::env::var_os("PATH")
        .map(|paths| std::env::split_paths(&paths).any(|dir| dir.join(binary).is_file()))
        .unwrap_or(false)
}

/// True when this session should inject through ydotool rather than pynput.
///
/// Not tied to Wayland: it is simply "ydotool is installed and we are not on
/// X11", so a session that never set XDG_SESSION_TYPE still works.
pub fn available() -> bool {
    which("ydotool") && std::env::var("XDG_SESSION_TYPE").as_deref() != Ok("x11")
}

/// Why injected input will not arrive, or None when it will.
pub fn problem() -> Option<String> {
    if !available() {
        if std::env::var("XDG_SESSION_TYPE").as_deref() == Ok("wayland") {
            return Some(
                "Wayland ignores pynput's input: install ydotool and start ydotoold \
                 (see the Wayland section of README.md)"
                    .to_string(),
            );
        }
        return None;
    }
    match std::process::Command::new("ydotool").arg("debug").output() {
        Ok(output) if output.status.success() => None,
        Ok(output) => {
            let text = String::from_utf8_lossy(&output.stdout);
            let first = text
                .trim()
                .lines()
                .next()
                .unwrap_or("no response")
                .to_string();
            Some(format!("ydotool cannot reach ydotoold ({})", first))
        }
        Err(_) => Some("ydotool cannot reach ydotoold (no response)".to_string()),
    }
}

fn button_bits(button: &str) -> Result<u8, DeviceError> {
    BUTTONS
        .iter()
        .find(|(name, _)| *name == button)
        .map(|(_, bits)| *bits)
        .ok_or_else(|| DeviceError(format!("unknown button {}", button)))
}

/// Same interface as the pynput device, but every call shells out to ydotool.
pub struct YdotoolDevice;

impl Default for YdotoolDevice {
    fn default() -> Self {
        YdotoolDevice
    }
}

impl YdotoolDevice {
    pub fn new() -> Self {
        YdotoolDevice
    }

    fn exec(&self, args: &[String]) -> Result<(), DeviceError> {
        match std::process::Command::new("ydotool").args(args).status() {
            Ok(status) if status.success() => Ok(()),
            Ok(status) => Err(DeviceError(format!("ydotool exited with {}", status))),
            Err(error) => Err(DeviceError(error.to_string())),
        }
    }
}

impl Device for YdotoolDevice {
    fn mouse_press(&mut self, button: &str) -> Result<(), DeviceError> {
        let mask = 0x40 | button_bits(button)?;
        self.exec(&["click".to_string(), format!("0x{:x}", mask)])
    }

    fn mouse_release(&mut self, button: &str) -> Result<(), DeviceError> {
        let mask = 0x80 | button_bits(button)?;
        self.exec(&["click".to_string(), format!("0x{:x}", mask)])
    }

    fn key_press(&mut self, key: &Key) -> Result<(), DeviceError> {
        let code = keycode(key).map_err(DeviceError)?;
        self.exec(&["key".to_string(), format!("{}:1", code)])
    }

    fn key_release(&mut self, key: &Key) -> Result<(), DeviceError> {
        let code = keycode(key).map_err(DeviceError)?;
        self.exec(&["key".to_string(), format!("{}:0", code)])
    }
}
