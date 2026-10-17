//! The device boundary the engine talks to.
//!
//! Same four methods as `main.PynputDevice` / `ydotool.YdotoolDevice`, so the
//! engine stays ignorant of keyboards and mice and stays testable.

use crate::keys::Key;

/// A device call failed. Mirrors the exception the Python device would raise.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeviceError(pub String);

impl std::fmt::Display for DeviceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for DeviceError {}

pub trait Device {
    fn mouse_press(&mut self, button: &str) -> Result<(), DeviceError>;
    fn mouse_release(&mut self, button: &str) -> Result<(), DeviceError>;
    fn key_press(&mut self, key: &Key) -> Result<(), DeviceError>;
    fn key_release(&mut self, key: &Key) -> Result<(), DeviceError>;
}

/// So a `Box<dyn Device>` is itself a `Device`, which lets the clicker hold one
/// interchangeable backend without becoming generic.
impl<T: Device + ?Sized> Device for Box<T> {
    fn mouse_press(&mut self, button: &str) -> Result<(), DeviceError> {
        (**self).mouse_press(button)
    }

    fn mouse_release(&mut self, button: &str) -> Result<(), DeviceError> {
        (**self).mouse_release(button)
    }

    fn key_press(&mut self, key: &Key) -> Result<(), DeviceError> {
        (**self).key_press(key)
    }

    fn key_release(&mut self, key: &Key) -> Result<(), DeviceError> {
        (**self).key_release(key)
    }
}
