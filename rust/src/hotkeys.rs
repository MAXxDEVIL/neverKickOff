//! tkinter key event -> hotkey string, the Rust half of `hotkeys.format_hotkey`.

/// `(state bit, modifier name)`. Order controls the printed order.
pub const MODIFIERS: &[(u32, &str)] = &[
    (0x0004, "ctrl"),
    (0x0008, "alt"),
    (0x0001, "shift"),
    (0x0040, "cmd"),
];

/// Keysyms that are a modifier on their own; a hotkey needs a real key.
pub const MODIFIER_KEYSYMS: &[&str] = &[
    "shift_l",
    "shift_r",
    "control_l",
    "control_r",
    "alt_l",
    "alt_r",
    "super_l",
    "super_r",
    "meta_l",
    "meta_r",
    "caps_lock",
    "num_lock",
    "iso_level3_shift",
];

/// tkinter keysym -> pynput name, where they differ.
pub fn mapped_name(keysym: &str) -> &str {
    match keysym {
        "escape" => "esc",
        "return" => "enter",
        "kp_enter" => "enter",
        "prior" => "page_up",
        "next" => "page_down",
        "print" => "print_screen",
        "back_space" => "backspace",
        other => other,
    }
}

/// pynput wants `<ctrl>`, `<f6>` but a bare `s` for a single character.
fn token(name: &str) -> String {
    if name.chars().count() == 1 {
        name.to_string()
    } else {
        format!("<{}>", name)
    }
}

/// `'s'` with Ctrl+Alt held -> `<ctrl>+<alt>+s`. None if only a modifier was pressed.
pub fn format_hotkey(keysym: &str, state: u32) -> Option<String> {
    let keysym = keysym.to_lowercase();
    if MODIFIER_KEYSYMS.contains(&keysym.as_str()) {
        return None;
    }
    let name = mapped_name(&keysym);
    if name.is_empty() {
        return None;
    }
    let mut parts: Vec<String> = MODIFIERS
        .iter()
        .filter(|(bit, _)| state & bit != 0)
        .map(|(_, modifier)| token(modifier))
        .collect();
    parts.push(token(name));
    Some(parts.join("+"))
}
