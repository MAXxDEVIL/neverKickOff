# Test plan

## The idea

The Python implementation is the source of truth, so the ports are not tested
against a written description of the behaviour - they are tested against
**Python's actual output**, frozen into one file:

```
tests/fixtures/contract.json
```

`tests/gen_fixtures.py` runs the real Python functions and writes down what they
returned. Rust and Java then have to reproduce that file exactly. If Python
changes, the contract test fails and the fixture is regenerated deliberately.

This avoids the usual trap of testing a port against a paraphrase, where both the
paraphrase and the port can be wrong together.

## Layers

| Layer | File | What it proves |
|-------|------|----------------|
| Python baseline | `test_engine.py` | The original still behaves as before (24 tests) |
| Contract generation | `tests/gen_fixtures.py` | Records Python's real output |
| Contract drift guard | `tests/test_contract.py` | Python still matches the frozen file |
| Rust contract | `rust/tests/contract.rs` | Rust reproduces every fixture case (7 tests) |
| Rust timing | `rust/tests/timing.rs` | The wall-clock behaviour a fixture cannot pin (4 tests) |
| Java contract | `java/tests/...` | Java reproduces every fixture case |
| CLI parity | manual, scripted | Printed lines match `python -u main.py` |

## What is in the fixture

Only deterministic behaviour. Everything that depends on wall-clock timing is a
per-language test instead, so a slow or loaded machine cannot cause a flaky
failure.

| Section | Cases | Covers |
|---------|------:|--------|
| `normalize_steps` | 5 | Flat spec → implicit step, explicit steps returned verbatim, empty `steps` falls through |
| `parse_combo` | 11 | String and list input, `<>` wrapping, aliases, single chars, f-keys, the exact error message |
| `load_spec` | 4 | Steps form, flat form, combos parsed in place, unknown keys preserved |
| `format_hotkey` | 11 | Modifier bits and order, keysym mapping, modifier-only → null, single char |
| `as_text` | 6 | Bytes, UTF-8 replacement, empty → null, absent → null |
| `keycode` | 16 | Letters, digits, punctuation, named keys, f1/f20, and two failure cases |
| `engine` | 8 | Tick count and exact device-call order for finite runs, `repeat == 0`, window match, steps ordering, count, and the mid-combo failure cleanup |

Deliberately **not** in the fixture: `duration`, `jitter`, `initial_delay` and
stopping mid-hold. Their tick counts depend on the machine.

## Running everything

```sh
# Python: the baseline plus the drift guard
.venv/bin/python test_engine.py            # -> all passed
.venv/bin/python tests/test_contract.py    # -> all passed

# Regenerate the contract after a deliberate Python change
.venv/bin/python tests/gen_fixtures.py

# Rust: format, lints, tests, release build
cd rust
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test
cargo build --release

# Java
cd java
./build.sh && ./run-tests.sh
```

## The timing tests (per language)

These pin the parts of `Engine.run` the fixture cannot:

1. **Duration bounds an unlimited run** - `repeat: -1` with `duration` ends
   promptly and still fires at least once.
2. **Stop before the initial delay fires nothing** - returns 0, no device calls.
3. **Unlimited repeat runs until stop** - and produces exactly one press and
   release per tick.
4. **Stopping mid-hold releases every pressed key** - the device calls are
   exactly `press ctrl, press c, release c, release ctrl`: keys come back up
   newest-first, as a pair, even when the stop arrives during the hold.

## Negative controls

A test suite that cannot fail is worthless, so the harness was checked by
breaking things on purpose:

- When `normalize_steps` was perturbed in memory, `tests/test_contract.py`
  failed with the exact path of the difference
  (`.normalize_steps[0].expect[0].hold: 0.9 != frozen 0.5`).
- The `keycode` fixture contains two cases that **must** fail, and the contract
  test asserts they fail; a port that silently accepted them would be caught.

## What is not tested

- Real input injection: `ydotool` is not installed here and the session is
  Wayland, so nothing can actually click on this machine.
- Global hotkeys on Wayland (X11 only, in all three implementations).
- Windows and macOS code paths (no such machine).
- The GUI and tray (not ported).
