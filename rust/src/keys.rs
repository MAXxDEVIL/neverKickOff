//! Key names and combo parsing - the Rust half of `main.parse_combo`.

use serde::{Deserialize, Serialize};

/// A key, in the same neutral shape the cross-language contract uses.
///
/// Python hands pynput `Key`/`KeyCode` objects to the device; this is the
/// equivalent, and `token()` produces the same string pynput's `str()` does for
/// the names the engine records.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub enum Key {
    Named {
        name: String,
    },
    Char {
        #[serde(rename = "char")]
        ch: char,
    },
}

impl Key {
    /// The string a device call is recorded as: `ctrl`, `f6`, `c`.
    pub fn token(&self) -> String {
        match self {
            Key::Named { name } => name.clone(),
            Key::Char { ch } => ch.to_string(),
        }
    }

    /// Build from a bare token, the way `parse_combo` classifies a name.
    pub fn from_token(token: &str) -> Key {
        if token.chars().count() == 1 {
            Key::Char {
                ch: token.chars().next().unwrap(),
            }
        } else {
            Key::Named {
                name: token.to_string(),
            }
        }
    }
}

/// Every member of pynput's `keyboard.Key` enum, which is what `hasattr(Key, name)`
/// tests. Sorted; keep in step with the Python version if pynput adds keys.
pub const KEY_NAMES: &[&str] = &[
    "alt",
    "alt_gr",
    "alt_r",
    "backspace",
    "caps_lock",
    "cmd",
    "cmd_r",
    "ctrl",
    "ctrl_r",
    "delete",
    "down",
    "end",
    "enter",
    "esc",
    "f1",
    "f10",
    "f11",
    "f12",
    "f13",
    "f14",
    "f15",
    "f16",
    "f17",
    "f18",
    "f19",
    "f2",
    "f20",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "home",
    "insert",
    "left",
    "media_next",
    "media_play_pause",
    "media_previous",
    "media_volume_down",
    "media_volume_mute",
    "media_volume_up",
    "menu",
    "num_lock",
    "page_down",
    "page_up",
    "pause",
    "print_screen",
    "right",
    "scroll_lock",
    "shift",
    "shift_r",
    "space",
    "tab",
    "up",
];

/// `main.ALIASES`.
pub fn alias(name: &str) -> &str {
    match name {
        "control" => "ctrl",
        "escape" => "esc",
        "return" => "enter",
        "win" => "cmd",
        "super" => "cmd",
        "meta" => "cmd",
        "capslock" => "caps_lock",
        "pgup" => "page_up",
        "pgdn" => "page_down",
        other => other,
    }
}

/// Mirrors Python's `KeyError` for an unknown key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeyError {
    pub message: String,
}

impl std::fmt::Display for KeyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for KeyError {}

/// Python's `repr()` for the simple strings that appear in key names.
///
/// Python picks double quotes when the value holds a single quote, then escapes
/// backslashes and control characters; key names never contain those, so a
/// faithful-enough subset is enough here.
fn py_repr(value: &str) -> String {
    if value.contains('\'') && !value.contains('"') {
        format!("\"{}\"", value)
    } else {
        format!("'{}'", value.replace('\\', "\\\\").replace('\'', "\\'"))
    }
}

/// Python's `repr()` for a list of strings, e.g. `['ctrl', 'c']`.
fn py_list_repr(parts: &[String]) -> String {
    let inner: Vec<String> = parts.iter().map(|p| py_repr(p)).collect();
    format!("[{}]", inner.join(", "))
}

/// `parse_combo` for a string or a list of names.
///
/// A string is split on `+` first, exactly as Python does before building the
/// error message, so `"ctrl+q"` reports the split list.
pub fn parse_combo_parts(parts: &[String]) -> Result<Vec<Key>, KeyError> {
    let mut keys = Vec::with_capacity(parts.len());
    for part in parts {
        let name = alias(
            part.trim()
                .trim_matches(|c| c == '<' || c == '>')
                .to_lowercase()
                .as_str(),
        )
        .to_string();
        if KEY_NAMES.contains(&name.as_str()) {
            keys.push(Key::Named { name });
        } else if name.chars().count() == 1 {
            keys.push(Key::Char {
                ch: name.chars().next().unwrap(),
            });
        } else {
            return Err(KeyError {
                message: format!("unknown key '{}' in '{}'", part, py_list_repr(parts)),
            });
        }
    }
    Ok(keys)
}

/// `main.parse_combo("ctrl+alt+c")`.
pub fn parse_combo(combo: &str) -> Result<Vec<Key>, KeyError> {
    let parts: Vec<String> = combo.split('+').map(|s| s.to_string()).collect();
    parse_combo_parts(&parts)
}

/// `parse_combo` when the value may already be a list of parts.
pub fn parse_combo_value(value: &serde_json::Value) -> Result<Vec<Key>, KeyError> {
    if let Some(text) = value.as_str() {
        return parse_combo(text);
    }
    let parts: Vec<String> = value
        .as_array()
        .map(|items| {
            items
                .iter()
                .map(|i| i.as_str().unwrap_or("").to_string())
                .collect()
        })
        .unwrap_or_default();
    parse_combo_parts(&parts)
}
