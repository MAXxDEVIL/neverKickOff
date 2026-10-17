//! Timing loop - the Rust half of `engine.Engine`.
//!
//! Knows nothing about keyboards or mice: it is handed a `Device` and a plain
//! JSON spec. Behaviour is pinned by tests/fixtures/contract.json.

use crate::device::{Device, DeviceError};
use crate::keys::Key;
use crate::spec::{normalize_steps, truthy};
use serde_json::{json, Value};
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

/// `threading.Event`: set-once, and a wait that notices the stop immediately.
#[derive(Default)]
pub struct Stop {
    flag: Mutex<bool>,
    signal: Condvar,
}

impl Stop {
    pub fn new() -> Arc<Stop> {
        Arc::new(Stop::default())
    }

    pub fn set(&self) {
        let mut flag = self.flag.lock().unwrap();
        *flag = true;
        self.signal.notify_all();
    }

    pub fn is_set(&self) -> bool {
        *self.flag.lock().unwrap()
    }

    /// True once the stop is set, False on timeout. A zero or negative wait never sleeps.
    pub fn wait(&self, seconds: f64) -> bool {
        if seconds.is_nan() || seconds <= 0.0 {
            return self.is_set();
        }
        let deadline = Instant::now() + to_duration(seconds);
        let mut flag = self.flag.lock().unwrap();
        while !*flag {
            let now = Instant::now();
            if now >= deadline {
                break;
            }
            let (guard, _) = self.signal.wait_timeout(flag, deadline - now).unwrap();
            flag = guard;
        }
        *flag
    }
}

/// xorshift64*: jitter only needs to be unpredictable, not cryptographic.
struct Rng(u64);

impl Rng {
    fn new() -> Rng {
        let seed = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos() as u64)
            .unwrap_or(0x2545_F491_4F6C_DD1D);
        Rng(seed | 1)
    }

    fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }

    /// Python's `random.uniform(a, b)`.
    fn uniform(&mut self, a: f64, b: f64) -> f64 {
        let unit = (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
        a + (b - a) * unit
    }
}

pub struct Engine<D: Device> {
    device: D,
    focused_window: Arc<dyn Fn() -> Option<String> + Send + Sync>,
    stop: Arc<Stop>,
}

impl<D: Device> Engine<D> {
    pub fn new(
        device: D,
        focused_window: Option<Arc<dyn Fn() -> Option<String> + Send + Sync>>,
    ) -> Self {
        Engine {
            device,
            focused_window: focused_window.unwrap_or_else(|| Arc::new(|| None)),
            stop: Stop::new(),
        }
    }

    pub fn stop_handle(&self) -> Arc<Stop> {
        Arc::clone(&self.stop)
    }

    /// An engine driven by a stop handle the caller already holds, so a UI can
    /// stop it before the run thread has even started.
    pub fn with_stop(
        device: D,
        focused_window: Option<Arc<dyn Fn() -> Option<String> + Send + Sync>>,
        stop: Arc<Stop>,
    ) -> Self {
        Engine {
            device,
            focused_window: focused_window.unwrap_or_else(|| Arc::new(|| None)),
            stop,
        }
    }

    pub fn device(&self) -> &D {
        &self.device
    }

    /// Fire macro ticks until repeat, duration or `stop()` ends it. Returns ticks fired.
    pub fn run(&mut self, spec: &Value) -> Result<usize, DeviceError> {
        let interval = max0(as_f64(spec.get("interval"), 0.1));
        let jitter = max0(as_f64(spec.get("jitter"), 0.0));
        let repeat = as_i64(spec.get("repeat"), -1);
        let duration = max0(as_f64(spec.get("duration"), 0.0));
        let window = as_str(spec.get("window"), "").to_lowercase();
        let steps = normalize_steps(spec);

        let stop = Arc::clone(&self.stop);
        if stop.wait(as_f64(spec.get("initial_delay"), 0.0)) {
            return Ok(0);
        }

        // duration == 0 means no time limit.
        let deadline = Instant::now() + to_duration(duration);
        // Move the deadline by the nominal interval rather than sleeping
        // `interval` after each tick, so a slow tick cannot accumulate drift.
        let mut next_at = Instant::now();
        let mut fired: i64 = 0;
        let mut rng = Rng::new();

        while !stop.is_set() {
            if duration > 0.0 && Instant::now() >= deadline {
                break;
            }
            let now = Instant::now();
            // Python tests `wait > 0`, so an already-due tick does not consult the
            // stop here - the loop condition at the top is what ends it.
            if now < next_at && stop.wait(next_at.duration_since(now).as_secs_f64()) {
                break;
            }
            let focused = (self.focused_window)().unwrap_or_default().to_lowercase();
            if window.is_empty() || focused.contains(&window) {
                if repeat >= 0 && fired >= repeat {
                    // repeat == 0 fires nothing.
                    break;
                }
                self.run_steps(&steps, &stop)?;
                fired += 1;
            }
            next_at += to_duration(max0(interval * (1.0 + rng.uniform(-jitter, jitter))));
        }
        Ok(fired as usize)
    }

    fn run_steps(&mut self, steps: &[Value], stop: &Stop) -> Result<(), DeviceError> {
        for step in steps {
            if stop.is_set() {
                return Ok(());
            }
            let count = std::cmp::max(1, as_i64(step.get("count"), 1));
            let hold = max0(as_f64(step.get("hold"), 0.0));
            for _ in 0..count {
                if stop.is_set() {
                    return Ok(());
                }
                self.fire(step, hold, stop)?;
            }
            if stop.wait(max0(as_f64(step.get("wait"), 0.0))) {
                return Ok(());
            }
        }
        Ok(())
    }

    fn fire(&mut self, step: &Value, hold: f64, stop: &Stop) -> Result<(), DeviceError> {
        if step.get("action").and_then(|a| a.as_str()) == Some("keys") {
            let mut pressed: Vec<Key> = Vec::new();
            let mut result = Ok(());
            for key in keys_of(step) {
                match self.device.key_press(&key) {
                    Ok(()) => pressed.push(key),
                    Err(error) => {
                        result = Err(error);
                        break;
                    }
                }
            }
            if result.is_ok() {
                stop.wait(hold);
            }
            // Release only what actually went down, newest first.
            for key in pressed.iter().rev() {
                let _ = self.device.key_release(key);
            }
            result
        } else {
            let button = step
                .get("button")
                .and_then(|b| b.as_str())
                .unwrap_or("left")
                .to_string();
            self.device.mouse_press(&button)?;
            stop.wait(hold);
            self.device.mouse_release(&button)
        }
    }
}

fn keys_of(step: &Value) -> Vec<Key> {
    let value = step.get("keys").cloned().unwrap_or_else(|| json!([]));
    if !truthy(&value) {
        return Vec::new();
    }
    value
        .as_array()
        .map(|items| items.iter().map(key_from_value).collect())
        .unwrap_or_default()
}

fn key_from_value(value: &Value) -> Key {
    serde_json::from_value::<Key>(value.clone())
        .unwrap_or_else(|_| Key::from_token(value.as_str().unwrap_or("")))
}

/// `max(0.0, x)`, which also folds NaN to 0.0 the way Python's max does.
pub fn max0(value: f64) -> f64 {
    if value > 0.0 {
        value
    } else {
        0.0
    }
}

/// A duration that never panics the way `Duration::from_secs_f64` does on NaN or
/// an infinity; Python would simply wait a very long time.
pub fn to_duration(seconds: f64) -> Duration {
    if seconds.is_finite() && seconds > 0.0 {
        Duration::from_secs_f64(seconds)
    } else {
        Duration::ZERO
    }
}

fn as_f64(value: Option<&Value>, default: f64) -> f64 {
    value.and_then(|v| v.as_f64()).unwrap_or(default)
}

fn as_i64(value: Option<&Value>, default: i64) -> i64 {
    match value {
        Some(Value::Number(number)) => number
            .as_i64()
            .or_else(|| number.as_f64().map(|f| f as i64))
            .unwrap_or(default),
        _ => default,
    }
}

fn as_str(value: Option<&Value>, default: &str) -> String {
    match value {
        Some(Value::String(text)) => text.clone(),
        _ => default.to_string(),
    }
}
