//! X11/XWayland input injection and global hotkeys through rdev.
//!
//! This is the pynput equivalent: rdev drives the X server with XTest, so it has
//! exactly pynput's reach (including its inability to inject into a Wayland
//! compositor, which is why the ydotool backend exists).

use crate::device::{Device, DeviceError};
use crate::keys::{parse_combo, Key};

/// rdev key <-> the key name the rest of the program uses.
///
/// The right-hand modifiers keep their `_r` names for injection; `collapse`
/// folds them onto the plain names when matching a hotkey, because a config says
/// `<ctrl>` and either physical Ctrl should satisfy it.
const KEY_TABLE: &[(rdev::Key, &str)] = &[
    (rdev::Key::ControlLeft, "ctrl"),
    (rdev::Key::ControlRight, "ctrl_r"),
    (rdev::Key::ShiftLeft, "shift"),
    (rdev::Key::ShiftRight, "shift_r"),
    (rdev::Key::Alt, "alt"),
    (rdev::Key::AltGr, "alt_gr"),
    (rdev::Key::MetaLeft, "cmd"),
    (rdev::Key::MetaRight, "cmd_r"),
    (rdev::Key::Return, "enter"),
    (rdev::Key::Escape, "esc"),
    (rdev::Key::Tab, "tab"),
    (rdev::Key::Space, "space"),
    (rdev::Key::Backspace, "backspace"),
    (rdev::Key::Delete, "delete"),
    (rdev::Key::Insert, "insert"),
    (rdev::Key::UpArrow, "up"),
    (rdev::Key::DownArrow, "down"),
    (rdev::Key::LeftArrow, "left"),
    (rdev::Key::RightArrow, "right"),
    (rdev::Key::Home, "home"),
    (rdev::Key::End, "end"),
    (rdev::Key::PageUp, "page_up"),
    (rdev::Key::PageDown, "page_down"),
    (rdev::Key::CapsLock, "caps_lock"),
    (rdev::Key::NumLock, "num_lock"),
    (rdev::Key::PrintScreen, "print_screen"),
    (rdev::Key::ScrollLock, "scroll_lock"),
    (rdev::Key::Pause, "pause"),
    (rdev::Key::KeyA, "a"),
    (rdev::Key::KeyB, "b"),
    (rdev::Key::KeyC, "c"),
    (rdev::Key::KeyD, "d"),
    (rdev::Key::KeyE, "e"),
    (rdev::Key::KeyF, "f"),
    (rdev::Key::KeyG, "g"),
    (rdev::Key::KeyH, "h"),
    (rdev::Key::KeyI, "i"),
    (rdev::Key::KeyJ, "j"),
    (rdev::Key::KeyK, "k"),
    (rdev::Key::KeyL, "l"),
    (rdev::Key::KeyM, "m"),
    (rdev::Key::KeyN, "n"),
    (rdev::Key::KeyO, "o"),
    (rdev::Key::KeyP, "p"),
    (rdev::Key::KeyQ, "q"),
    (rdev::Key::KeyR, "r"),
    (rdev::Key::KeyS, "s"),
    (rdev::Key::KeyT, "t"),
    (rdev::Key::KeyU, "u"),
    (rdev::Key::KeyV, "v"),
    (rdev::Key::KeyW, "w"),
    (rdev::Key::KeyX, "x"),
    (rdev::Key::KeyY, "y"),
    (rdev::Key::KeyZ, "z"),
    (rdev::Key::Num0, "0"),
    (rdev::Key::Num1, "1"),
    (rdev::Key::Num2, "2"),
    (rdev::Key::Num3, "3"),
    (rdev::Key::Num4, "4"),
    (rdev::Key::Num5, "5"),
    (rdev::Key::Num6, "6"),
    (rdev::Key::Num7, "7"),
    (rdev::Key::Num8, "8"),
    (rdev::Key::Num9, "9"),
    (rdev::Key::Minus, "-"),
    (rdev::Key::Equal, "="),
    (rdev::Key::LeftBracket, "["),
    (rdev::Key::RightBracket, "]"),
    (rdev::Key::SemiColon, ";"),
    (rdev::Key::Quote, "'"),
    (rdev::Key::Comma, ","),
    (rdev::Key::Dot, "."),
    (rdev::Key::Slash, "/"),
    (rdev::Key::BackSlash, "\\"),
    (rdev::Key::BackQuote, "`"),
    (rdev::Key::F1, "f1"),
    (rdev::Key::F2, "f2"),
    (rdev::Key::F3, "f3"),
    (rdev::Key::F4, "f4"),
    (rdev::Key::F5, "f5"),
    (rdev::Key::F6, "f6"),
    (rdev::Key::F7, "f7"),
    (rdev::Key::F8, "f8"),
    (rdev::Key::F9, "f9"),
    (rdev::Key::F10, "f10"),
    (rdev::Key::F11, "f11"),
    (rdev::Key::F12, "f12"),
];

fn token_of(key: &rdev::Key) -> Option<String> {
    KEY_TABLE
        .iter()
        .find(|(candidate, _)| candidate == key)
        .map(|(_, name)| (*name).to_string())
}

fn rdev_key(key: &Key) -> Option<rdev::Key> {
    let name = key.token();
    KEY_TABLE
        .iter()
        .find(|(_, candidate)| *candidate == name)
        .map(|(k, _)| *k)
}

/// A right-hand modifier answers for its left-hand name in a hotkey.
fn collapse(name: &str) -> String {
    match name {
        "ctrl_r" => "ctrl",
        "shift_r" => "shift",
        "alt_r" | "alt_gr" => "alt",
        "cmd_r" => "cmd",
        other => other,
    }
    .to_string()
}

fn rdev_button(button: &str) -> Result<rdev::Button, DeviceError> {
    match button {
        "left" => Ok(rdev::Button::Left),
        "right" => Ok(rdev::Button::Right),
        "middle" => Ok(rdev::Button::Middle),
        other => Err(DeviceError(format!("unknown button {}", other))),
    }
}

fn send(event: rdev::EventType) -> Result<(), DeviceError> {
    rdev::simulate(&event).map_err(|_| DeviceError("rdev could not send the event".to_string()))
}

/// Input injection over XTest, the pynput path.
pub struct RdevDevice;

impl Default for RdevDevice {
    fn default() -> Self {
        RdevDevice
    }
}

impl RdevDevice {
    pub fn new() -> Self {
        RdevDevice
    }
}

impl Device for RdevDevice {
    fn mouse_press(&mut self, button: &str) -> Result<(), DeviceError> {
        send(rdev::EventType::ButtonPress(rdev_button(button)?))
    }

    fn mouse_release(&mut self, button: &str) -> Result<(), DeviceError> {
        send(rdev::EventType::ButtonRelease(rdev_button(button)?))
    }

    fn key_press(&mut self, key: &Key) -> Result<(), DeviceError> {
        let mapped = rdev_key(key)
            .ok_or_else(|| DeviceError(format!("rdev has no key for {}", key.token())))?;
        send(rdev::EventType::KeyPress(mapped))
    }

    fn key_release(&mut self, key: &Key) -> Result<(), DeviceError> {
        let mapped = rdev_key(key)
            .ok_or_else(|| DeviceError(format!("rdev has no key for {}", key.token())))?;
        send(rdev::EventType::KeyRelease(mapped))
    }
}

/// Which configured hotkey fired.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Hotkey {
    Toggle,
    Panic,
}

fn combo_set(combo: &str) -> Result<Vec<String>, String> {
    let mut keys: Vec<String> = parse_combo(combo)
        .map_err(|error| error.message)?
        .iter()
        .map(|key| collapse(&key.token()))
        .collect();
    keys.sort();
    Ok(keys)
}

/// Watch for the two configured combos, calling back when one is pressed.
///
/// Blocks, like `listener.join()` does in Python. A combo fires when the set of
/// held keys is exactly the combo, so it does not fire again while held.
pub fn listen(
    toggle_combo: &str,
    panic_combo: &str,
    mut on_hotkey: impl FnMut(Hotkey) + 'static,
) -> Result<(), String> {
    let toggle = combo_set(toggle_combo)?;
    let panic = combo_set(panic_combo)?;
    let mut held: Vec<String> = Vec::new();

    rdev::listen(move |event| match event.event_type {
        rdev::EventType::KeyPress(key) => {
            let Some(name) = token_of(&key) else {
                return;
            };
            let name = collapse(&name);
            if held.iter().any(|existing| existing == &name) {
                return; // auto-repeat: the combo already fired on the first press
            }
            held.push(name);
            let mut current = held.clone();
            current.sort();
            if current == toggle {
                on_hotkey(Hotkey::Toggle);
            } else if current == panic {
                on_hotkey(Hotkey::Panic);
            }
        }
        rdev::EventType::KeyRelease(key) => {
            if let Some(name) = token_of(&key) {
                let name = collapse(&name);
                held.retain(|existing| existing != &name);
            }
        }
        _ => {}
    })
    .map_err(|error| format!("{:?}", error))
}
