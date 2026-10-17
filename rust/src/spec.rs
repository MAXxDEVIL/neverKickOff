//! Spec loading - the Rust half of `main.load_spec` and `engine.normalize_steps`.
//!
//! Specs stay `serde_json::Value` rather than a typed struct on purpose: Python
//! copies dicts and only touches `keys`, so any extra key in a user's config has
//! to survive untouched.

use crate::keys::{parse_combo_value, KeyError};
use serde_json::{json, Map, Value};

/// Python truthiness, which decides whether `steps` or `keys` is "present".
pub fn truthy(value: &Value) -> bool {
    match value {
        Value::Null => false,
        Value::Bool(flag) => *flag,
        Value::Number(number) => number.as_f64().map(|f| f != 0.0).unwrap_or(false),
        Value::String(text) => !text.is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(map) => !map.is_empty(),
    }
}

/// `engine.normalize_steps`: a flat spec becomes one implicit step.
///
/// Explicit steps are returned verbatim, exactly as Python returns the caller's
/// own dicts, so the per-field defaults are applied later at use time.
pub fn normalize_steps(spec: &Value) -> Vec<Value> {
    if let Some(steps) = spec.get("steps") {
        if truthy(steps) {
            if let Some(items) = steps.as_array() {
                return items.clone();
            }
        }
    }
    let mut step = Map::new();
    step.insert(
        "action".into(),
        spec.get("action")
            .cloned()
            .unwrap_or_else(|| json!("mouse")),
    );
    step.insert(
        "button".into(),
        spec.get("button").cloned().unwrap_or_else(|| json!("left")),
    );
    let keys = match spec.get("keys") {
        Some(value) if truthy(value) => value.clone(),
        _ => json!([]),
    };
    step.insert("keys".into(), keys);
    step.insert("count".into(), json!(1));
    step.insert(
        "hold".into(),
        spec.get("hold").cloned().unwrap_or_else(|| json!(0.0)),
    );
    step.insert("wait".into(), json!(0.0));
    vec![Value::Object(step)]
}

/// `main.load_spec`: copy a config's click spec, parsing every key combo.
pub fn load_spec(click: &Value) -> Result<Value, KeyError> {
    let mut spec = click.clone();
    if spec.get("steps").map(truthy).unwrap_or(false) {
        let steps = spec
            .get("steps")
            .and_then(|s| s.as_array())
            .cloned()
            .unwrap_or_default();
        let mut parsed = Vec::with_capacity(steps.len());
        for step in steps {
            let mut step = step;
            if step.get("action").and_then(|a| a.as_str()) == Some("keys") {
                let combo = step.get("keys").cloned().unwrap_or_else(|| json!([]));
                let keys = parse_combo_value(&combo)?;
                if let Some(map) = step.as_object_mut() {
                    map.insert("keys".into(), serde_json::to_value(keys).unwrap());
                }
            }
            parsed.push(step);
        }
        if let Some(map) = spec.as_object_mut() {
            map.insert("steps".into(), Value::Array(parsed));
        }
    } else if spec.get("action").and_then(|a| a.as_str()) == Some("keys") {
        let combo = spec.get("keys").cloned().unwrap_or_else(|| json!([]));
        let keys = parse_combo_value(&combo)?;
        if let Some(map) = spec.as_object_mut() {
            map.insert("keys".into(), serde_json::to_value(keys).unwrap());
        }
    }
    Ok(spec)
}
