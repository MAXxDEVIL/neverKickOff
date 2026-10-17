//! Toggles one background engine at a time - the Rust half of `main.Clicker`.

use crate::device::Device;
use crate::engine::{Engine, Stop};
use serde_json::Value;
use std::sync::{Arc, Mutex};

type FocusedWindow = Arc<dyn Fn() -> Option<String> + Send + Sync>;

pub struct Clicker {
    make_device: Box<dyn Fn() -> Box<dyn Device + Send> + Send + Sync>,
    spec: Mutex<Value>,
    focused_window: Option<FocusedWindow>,
    current: Arc<Mutex<Option<Arc<Stop>>>>,
}

impl Clicker {
    pub fn new(
        make_device: impl Fn() -> Box<dyn Device + Send> + Send + Sync + 'static,
        spec: Value,
        focused_window: Option<Box<dyn Fn() -> Option<String> + Send + Sync>>,
    ) -> Self {
        Clicker {
            make_device: Box::new(make_device),
            spec: Mutex::new(spec),
            focused_window: focused_window.map(Arc::from),
            current: Arc::new(Mutex::new(None)),
        }
    }

    pub fn set_spec(&self, spec: Value) {
        *self.spec.lock().unwrap() = spec;
    }

    /// Start clicking, or stop it if already running. Returns true when started.
    pub fn toggle(&self) -> bool {
        {
            let mut current = self.current.lock().unwrap();
            if let Some(stop) = current.take() {
                stop.set();
                println!("stopped");
                return false;
            }
        }

        let stop = Stop::new();
        *self.current.lock().unwrap() = Some(Arc::clone(&stop));
        println!("running");

        let spec = self.spec.lock().unwrap().clone();
        let device = (self.make_device)();
        let focused = self.focused_window.clone();
        let current = Arc::clone(&self.current);
        let engine_stop = Arc::clone(&stop);

        std::thread::spawn(move || {
            let mut engine = Engine::with_stop(device, focused, Arc::clone(&engine_stop));
            let fired = match engine.run(&spec) {
                Ok(count) => count,
                Err(error) => {
                    // A dead engine must not leave the toggle wedged.
                    println!("stopped after error: {}", error);
                    0
                }
            };
            let mut slot = current.lock().unwrap();
            if slot
                .as_ref()
                .map(|running| Arc::ptr_eq(running, &engine_stop))
                .unwrap_or(false)
            {
                *slot = None;
            }
            drop(slot);
            println!("done ({} ticks)", fired);
        });
        true
    }

    pub fn stop(&self) {
        if let Some(stop) = self.current.lock().unwrap().take() {
            stop.set();
            println!("stopped");
        }
    }

    /// True while an engine is live; false once a finite run finishes.
    pub fn running(&self) -> bool {
        self.current.lock().unwrap().is_some()
    }
}
