"""Self-check for the timing loop. No display needed: engine talks to a fake device.

    python test_engine.py
"""
import threading
import time

from engine import Engine


class FakeDevice:
    def __init__(self, work=0.0):
        self.work = work
        self.events = []  # (timestamp, kind, arg)

    def _do(self, *event):
        self.events.append((time.monotonic(),) + event)
        if self.work:
            time.sleep(self.work)

    def mouse_press(self, button):
        self._do("mouse_press", button)

    def mouse_release(self, button):
        self._do("mouse_release", button)

    def key_press(self, key):
        self._do("key_press", key)

    def key_release(self, key):
        self._do("key_release", key)


class FlakyDevice(FakeDevice):
    """Fails on the Nth key_press, to test cleanup of a half-pressed combo."""

    def __init__(self, fail_on):
        super().__init__()
        self.fail_on = fail_on
        self._presses = 0

    def key_press(self, key):
        self._presses += 1
        if self._presses == self.fail_on:
            raise RuntimeError("device failure")
        super().key_press(key)


def test_repeat_and_paired_releases():
    device = FakeDevice()
    fired = Engine(device).run(
        {"action": "mouse", "button": "left", "interval": 0.01, "repeat": 5})
    assert fired == 5, fired
    kinds = [e[1] for e in device.events]
    assert kinds == ["mouse_press", "mouse_release"] * 5, kinds


def test_no_drift_when_a_tick_is_slower_than_the_interval():
    device = FakeDevice(work=0.015)  # press + release = 0.03 per tick
    started = time.monotonic()
    fired = Engine(device).run({"action": "mouse", "interval": 0.02, "repeat": 5})
    elapsed = time.monotonic() - started
    assert fired == 5, fired
    # A tick costs 0.03 > the 0.02 interval, so the loop must fire back-to-back
    # (~5*0.03). Sleeping the interval after each tick instead would be ~5*0.05.
    assert elapsed < 0.20, elapsed


def test_stop_mid_hold_releases_keys():
    device = FakeDevice()
    engine = Engine(device)
    thread = threading.Thread(target=engine.run, args=(
        {"action": "keys", "keys": ["ctrl", "c"], "interval": 5, "hold": 5},))
    thread.start()
    time.sleep(0.05)
    engine.stop()
    thread.join(2)
    assert not thread.is_alive()
    kinds = [e[1] for e in device.events]
    assert kinds == ["key_press", "key_press", "key_release", "key_release"], kinds


def test_jitter_stays_within_bounds():
    device = FakeDevice()
    Engine(device).run({"action": "mouse", "interval": 0.02, "jitter": 0.5, "repeat": 6})
    stamps = [e[0] for e in device.events if e[1] == "mouse_press"]
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    assert gaps, "no ticks recorded"
    for gap in gaps:
        assert 0.01 - 0.01 <= gap <= 0.03 + 0.01, gap


def test_parse_combo_order_and_errors():
    try:
        from main import parse_combo
    except ImportError:
        return  # pynput not installed; skip
    assert [str(k) for k in parse_combo("ctrl+alt+c")] == ["Key.ctrl", "Key.alt", "'c'"]
    assert len(parse_combo(["ctrl", "c"])) == 2
    try:
        parse_combo("ctrl+nosuchkey")
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown key must raise")

    # end to end: parsed combo -> engine -> device
    device = FakeDevice()
    fired = Engine(device).run({"action": "keys", "keys": parse_combo("ctrl+c"),
                                "interval": 0.01, "repeat": 2})
    assert fired == 2
    assert [e[1] for e in device.events] == ["key_press", "key_press",
                                             "key_release", "key_release"] * 2


def test_format_hotkey():
    from hotkeys import format_hotkey
    combos = {
        ("s", 0x0004 | 0x0008): "<ctrl>+<alt>+s",
        ("F6", 0): "<f6>",
        ("Escape", 0): "<esc>",
        ("S", 0x0001): "<shift>+s",
    }
    for (keysym, state), expected in combos.items():
        assert format_hotkey(keysym, state) == expected, format_hotkey(keysym, state)
    assert format_hotkey("Control_L", 0x0004) is None
    try:
        from pynput.keyboard import HotKey
    except ImportError:
        return  # pynput not installed; the string shape is untested against it
    for combo in combos.values():
        assert HotKey.parse(combo), combo  # pynput must accept what we generate


def test_window_filter():
    # matching window: fires the clicks
    device = FakeDevice()
    fired = Engine(device, focused_window=lambda: "notes.txt - Notepad").run(
        {"action": "mouse", "interval": 0.01, "repeat": 3, "window": "notepad"})
    assert fired == 3, fired
    assert len([e for e in device.events if e[1] == "mouse_press"]) == 3

    # non-matching and unknown focused window: never clicks, so `repeat` is never
    # reached -> the loop waits for a stop instead of returning on its own.
    for answer in ("Browser", None):
        device = FakeDevice()
        engine = Engine(device, focused_window=lambda: answer)
        thread = threading.Thread(target=engine.run, args=({"action": "mouse", "interval": 0.01,
                                                            "repeat": 3, "window": "notepad"},))
        thread.start()
        time.sleep(0.05)
        engine.stop()
        thread.join(2)
        assert not thread.is_alive(), answer
        assert device.events == [], (answer, device.events)


def test_active_title_never_raises():
    from window import active_title
    # headless/no DISPLAY here: must swallow the failure and return None
    assert active_title() is None or isinstance(active_title(), str)


def test_clicker_toggle_stop_and_finish():
    try:
        from main import Clicker
    except ImportError:
        return  # pynput not installed; skip
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        # running: first press starts, second press stops, then nothing more fires
        device = FakeDevice()
        clicker = Clicker(device, {"action": "mouse", "button": "left",
                                   "interval": 0.02, "repeat": -1, "window": ""})
        assert clicker.toggle() is True
        time.sleep(0.1)
        assert clicker.toggle() is False
        time.sleep(0.05)
        count = len(device.events)
        time.sleep(0.1)
        assert len(device.events) == count, "still clicking after stop"

        # repeat ran out: the engine clears itself, so the next press starts again
        device = FakeDevice()
        clicker = Clicker(device, {"action": "mouse", "button": "left",
                                   "interval": 0.01, "repeat": 2, "window": ""})
        clicker.toggle()
        time.sleep(0.2)
        assert len([e for e in device.events if e[1] == "mouse_press"]) == 2
        assert clicker.toggle() is True
        clicker.stop()
        time.sleep(0.2)  # let the worker print its "done" line inside the redirect


def test_shipped_config_runs():
    import json
    from pathlib import Path

    config = json.loads(Path(__file__).with_name("config.json").read_text())
    assert set(config["hotkeys"]) == {"toggle", "panic"}
    spec = dict(config["click"])
    spec["repeat"] = 2  # the shipped file is repeat=-1 (infinite)
    assert Engine(FakeDevice()).run(spec) == 2

    try:
        from pynput.keyboard import HotKey
    except ImportError:
        return  # pynput not installed; the hotkey strings stay unvalidated
    for combo in config["hotkeys"].values():
        assert HotKey.parse(combo), combo


def test_repeat_zero_fires_nothing():
    device = FakeDevice()
    fired = Engine(device).run({"action": "mouse", "button": "left",
                                "interval": 0.01, "repeat": 0})
    assert fired == 0, fired
    assert device.events == [], device.events


def test_partial_key_press_is_released():
    device = FlakyDevice(fail_on=2)
    engine = Engine(device)
    try:
        engine.run({"action": "keys", "keys": ["ctrl", "c"], "interval": 0.01, "repeat": 1})
    except RuntimeError:
        pass
    else:
        raise AssertionError("the device error should propagate")
    # ctrl went down before 'c' failed, so ctrl must come back up
    assert [(e[1], e[2]) for e in device.events] == [("key_press", "ctrl"),
                                                     ("key_release", "ctrl")], device.events


def test_clicker_recovers_after_device_error():
    try:
        from main import Clicker
    except ImportError:
        return  # pynput not installed; skip
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        device = FlakyDevice(fail_on=1)
        clicker = Clicker(device, {"action": "keys", "keys": ["ctrl"], "interval": 0.01,
                                   "repeat": -1, "window": ""})
        assert clicker.toggle() is True
        time.sleep(0.1)  # the run dies on the device error and must clear itself
        assert clicker.toggle() is True, "engine error left the toggle wedged"
        clicker.stop()
        time.sleep(0.2)


def test_tray_is_optional():
    import tray  # must import with no pystray/Pillow installed
    assert callable(tray.run)
    try:
        import pystray  # noqa: F401
        return  # installed here, so the missing-dependency path cannot be checked
    except ImportError:
        pass
    try:
        tray.run(object())
    except ImportError:
        pass
    else:
        raise AssertionError("run() must ask for the tray deps when they are absent")


def test_steps_run_in_order_each_tick():
    device = FakeDevice()
    fired = Engine(device).run({"interval": 0.01, "repeat": 2, "steps": [
        {"action": "keys", "keys": ["ctrl", "c"], "count": 1, "hold": 0.0, "wait": 0.0},
        {"action": "mouse", "button": "left", "count": 1, "hold": 0.0, "wait": 0.0},
    ]})
    assert fired == 2, fired
    assert [e[1] for e in device.events] == [
        "key_press", "key_press", "key_release", "key_release",
        "mouse_press", "mouse_release"] * 2, device.events


def test_step_count_presses_many_times():
    device = FakeDevice()
    Engine(device).run({"interval": 0.01, "repeat": 1, "steps": [
        {"action": "mouse", "button": "left", "count": 3, "hold": 0.0, "wait": 0.0}]})
    assert len([e for e in device.events if e[1] == "mouse_press"]) == 3, device.events


def test_step_wait_delays_the_next_step():
    device = FakeDevice()
    Engine(device).run({"interval": 0.01, "repeat": 1, "steps": [
        {"action": "mouse", "button": "left", "count": 1, "hold": 0.0, "wait": 0.05},
        {"action": "mouse", "button": "right", "count": 1, "hold": 0.0, "wait": 0.0}]})
    stamps = [e[0] for e in device.events if e[1] == "mouse_press"]
    assert [e[2] for e in device.events if e[1] == "mouse_press"] == ["left", "right"]
    assert stamps[1] - stamps[0] >= 0.04, stamps[1] - stamps[0]


def test_duration_stops_the_run():
    device = FakeDevice()
    started = time.monotonic()
    fired = Engine(device).run({"action": "mouse", "button": "left", "interval": 0.01,
                                "repeat": -1, "duration": 0.1})
    elapsed = time.monotonic() - started
    assert fired > 0, fired
    assert elapsed < 0.3, elapsed
    assert fired == len([e for e in device.events if e[1] == "mouse_press"])


def test_normalize_steps_wraps_a_flat_spec():
    from engine import normalize_steps
    steps = normalize_steps({"action": "keys", "keys": ["ctrl"], "hold": 0.5})
    assert len(steps) == 1, steps
    assert steps[0]["action"] == "keys" and steps[0]["keys"] == ["ctrl"], steps
    assert steps[0]["hold"] == 0.5 and steps[0]["count"] == 1, steps
    assert normalize_steps({"steps": [{"action": "mouse"}]})[0]["action"] == "mouse"


def test_load_spec_parses_step_combos():
    try:
        from main import load_spec
    except ImportError:
        return  # pynput not installed; skip
    spec = load_spec({"steps": [{"action": "keys", "keys": "ctrl+c"},
                                {"action": "mouse", "button": "left"}]})
    assert [str(k) for k in spec["steps"][0]["keys"]] == ["Key.ctrl", "'c'"]
    assert spec["steps"][1]["button"] == "left"
    assert len(load_spec({"action": "keys", "keys": "ctrl+c"})["keys"]) == 2


def test_gui_step_conversion():
    try:
        import gui
    except ImportError:
        return  # tkinter or pynput not installed; skip
    # a legacy flat click becomes a single step, holding the old key/hold
    steps = gui._step_from_click({"action": "keys", "keys": "ctrl+c", "hold": 0.3})
    assert len(steps) == 1, steps
    assert steps[0]["action"] == "keys" and steps[0]["keys"] == "ctrl+c", steps
    assert steps[0]["hold"] == "0.3" and steps[0]["count"] == "1", steps
    # an explicit macro is kept, and list keys are joined back into a combo
    steps = gui._step_from_click({"steps": [
        {"action": "keys", "keys": ["ctrl", "c"], "count": 2, "hold": 0.1, "wait": 0.2},
        {"action": "mouse", "button": "right", "count": 1, "hold": 0, "wait": 0}]})
    assert steps[0]["keys"] == "ctrl+c" and steps[0]["count"] == "2", steps
    assert steps[0]["wait"] == "0.2" and steps[1]["button"] == "right", steps


def test_window_title_bytes_are_decoded():
    from window import _as_text
    # python-xlib returns bytes for some windows; a bytes title would make the
    # engine's `str in title.lower()` raise, so it must come back as str.
    assert _as_text(b"VRStream") == "VRStream"
    assert _as_text("Notepad") == "Notepad"
    assert _as_text(b"") is None
    assert _as_text(None) is None
    assert _as_text(b"\xc3\xa9") == "\u00e9"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
    print("all passed")
