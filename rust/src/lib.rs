//! neverKickOff, Rust port.
//!
//! The Python version is the source of truth. Behaviour is pinned by
//! tests/fixtures/contract.json, which Python generates and this crate must
//! reproduce exactly.

pub mod clicker;
pub mod device;
pub mod engine;
pub mod hotkeys;
pub mod keys;
pub mod rdev_input;
pub mod spec;
pub mod window;
pub mod ydotool;
