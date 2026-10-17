//! Timing behaviour that cannot be a byte-exact fixture.
//!
//! The contract file pins the deterministic core; duration, initial delay and
//! stopping mid-hold depend on wall-clock timing, so they are asserted here.

use neverkickoff::device::{Device, DeviceError};
use neverkickoff::engine::{Engine, Stop};
use neverkickoff::keys::Key;
use serde_json::json;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

#[derive(Clone, Default)]
struct Log(Arc<Mutex<Vec<String>>>);

impl Log {
    fn entries(&self) -> Vec<String> {
        self.0.lock().unwrap().clone()
    }

    fn push(&self, text: &str) {
        self.0.lock().unwrap().push(text.to_string());
    }
}

impl Device for Log {
    fn mouse_press(&mut self, button: &str) -> Result<(), DeviceError> {
        self.push(&format!("mouse_press {}", button));
        Ok(())
    }

    fn mouse_release(&mut self, button: &str) -> Result<(), DeviceError> {
        self.push(&format!("mouse_release {}", button));
        Ok(())
    }

    fn key_press(&mut self, key: &Key) -> Result<(), DeviceError> {
        self.push(&format!("key_press {}", key.token()));
        Ok(())
    }

    fn key_release(&mut self, key: &Key) -> Result<(), DeviceError> {
        self.push(&format!("key_release {}", key.token()));
        Ok(())
    }
}

fn stop_after(stop: Arc<Stop>, millis: u64) {
    thread::spawn(move || {
        thread::sleep(Duration::from_millis(millis));
        stop.set();
    });
}

#[test]
fn duration_bounds_an_unlimited_run() {
    let log = Log::default();
    let mut engine = Engine::new(log, None);
    let spec = json!({
        "action": "mouse", "button": "left",
        "interval": 0.005, "repeat": -1, "duration": 0.05,
    });
    let started = Instant::now();
    let fired = engine.run(&spec).unwrap();
    assert!(fired > 0, "duration must allow at least one tick");
    assert!(
        started.elapsed() < Duration::from_secs(2),
        "duration must end the run promptly"
    );
}

#[test]
fn stop_before_the_initial_delay_fires_nothing() {
    let log = Log::default();
    let mut engine = Engine::new(log.clone(), None);
    stop_after(engine.stop_handle(), 30);
    let spec = json!({
        "action": "mouse", "button": "left",
        "interval": 0.001, "repeat": -1, "initial_delay": 5.0,
    });
    let fired = engine.run(&spec).unwrap();
    assert_eq!(fired, 0);
    assert!(
        log.entries().is_empty(),
        "nothing should have been injected"
    );
}

#[test]
fn unlimited_repeat_runs_until_stop() {
    let log = Log::default();
    let mut engine = Engine::new(log.clone(), None);
    stop_after(engine.stop_handle(), 50);
    let spec = json!({"action": "mouse", "button": "left", "interval": 0.001, "repeat": -1});
    let fired = engine.run(&spec).unwrap();
    assert!(fired > 0);
    assert_eq!(
        log.entries().len(),
        fired * 2,
        "one press and release per tick"
    );
}

#[test]
fn stopping_mid_hold_releases_every_pressed_key() {
    let log = Log::default();
    let mut engine = Engine::new(log.clone(), None);
    stop_after(engine.stop_handle(), 50);
    let spec = json!({
        "interval": 0.0, "repeat": -1,
        "steps": [{
            "action": "keys",
            "keys": [{"kind": "named", "name": "ctrl"}, {"kind": "char", "char": "c"}],
            "count": 1, "hold": 5.0, "wait": 0.0,
        }],
    });
    let fired = engine.run(&spec).unwrap();
    assert_eq!(fired, 1);
    assert_eq!(
        log.entries(),
        vec![
            "key_press ctrl",
            "key_press c",
            "key_release c",
            "key_release ctrl"
        ],
        "keys must come back up, newest first, and always as a pair"
    );
}
