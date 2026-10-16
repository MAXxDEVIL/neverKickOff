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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
    print("all passed")
