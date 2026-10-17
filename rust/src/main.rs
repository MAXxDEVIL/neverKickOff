//! neverKickOff CLI - the Rust half of `main.main()`.
//!
//!     neverkickoff [config.json] [--tray]
//!
//! Toggle clicking with the config's hotkeys.toggle combo (default Ctrl+Alt+S),
//! panic-stop with hotkeys.panic (default Esc).

use neverkickoff::clicker::Clicker;
use neverkickoff::device::Device;
use neverkickoff::rdev_input::{self, Hotkey};
use neverkickoff::spec::load_spec;
use neverkickoff::ydotool;
use serde_json::Value;
use std::path::PathBuf;
use std::process::exit;
use std::sync::Arc;

/// ydotool on a Wayland session (XTest cannot inject there), else rdev.
fn make_device() -> Box<dyn Device + Send> {
    if ydotool::available() {
        println!("input: ydotool (Wayland)");
        return Box::new(ydotool::YdotoolDevice::new());
    }
    Box::new(rdev_input::RdevDevice::new())
}

fn config_path(args: &[String]) -> PathBuf {
    if let Some(first) = args.first() {
        return PathBuf::from(first);
    }
    std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().map(|dir| dir.join("config.json")))
        .unwrap_or_else(|| PathBuf::from("config.json"))
}

fn main() {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    let wants_tray = argv.iter().any(|arg| arg == "--tray");
    let args: Vec<String> = argv
        .iter()
        .filter(|arg| *arg != "--tray")
        .cloned()
        .collect();

    let path = config_path(&args);
    let text = match std::fs::read_to_string(&path) {
        Ok(text) => text,
        Err(error) => {
            eprintln!("cannot read {}: {}", path.display(), error);
            exit(1);
        }
    };
    let config: Value = match serde_json::from_str(&text) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("cannot parse {}: {}", path.display(), error);
            exit(1);
        }
    };
    let spec = match load_spec(&config["click"]) {
        Ok(spec) => spec,
        Err(error) => {
            eprintln!("bad config: {}", error.message);
            exit(1);
        }
    };

    let toggle = config["hotkeys"]["toggle"]
        .as_str()
        .unwrap_or("<ctrl>+<alt>+s")
        .to_string();
    let panic = config["hotkeys"]["panic"]
        .as_str()
        .unwrap_or("<esc>")
        .to_string();

    let clicker = Arc::new(Clicker::new(
        make_device,
        spec,
        Some(Box::new(neverkickoff::window::active_title)),
    ));

    if let Some(issue) = ydotool::problem() {
        println!("warning: {}", issue);
    }
    println!("ready - {} start/stop, {} panic-stop", toggle, panic);

    if wants_tray {
        // The Python version can fall back to pystray/Pillow when they import.
        // The Rust build has no tray backend yet; see MIGRATION_REPORT.md.
        println!("tray unavailable (no tray backend in this build); running without it");
    }

    let handler = Arc::clone(&clicker);
    if let Err(error) = rdev_input::listen(&toggle, &panic, move |hotkey| match hotkey {
        Hotkey::Toggle => {
            handler.toggle();
        }
        Hotkey::Panic => handler.stop(),
    }) {
        eprintln!("cannot watch for hotkeys: {}", error);
        clicker.stop();
        exit(1);
    }
}
