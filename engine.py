"""Timing loop for the auto clicker.

Deliberately knows nothing about keyboards or mice: it is handed a `device`
with mouse_press/mouse_release/key_press/key_release and a plain dict spec.
That keeps the schedule testable without a display or an input library.
"""
import random
import threading
import time


class Engine:
    def __init__(self, device, focused_window=None):
        self._device = device
        self._focused_window = focused_window or (lambda: None)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self, spec):
        """Fire ticks until `repeat` is reached or stop() is called. Returns ticks fired."""
        device = self._device
        interval = max(0.0, float(spec["interval"]))
        jitter = max(0.0, float(spec.get("jitter", 0.0)))
        hold = max(0.0, float(spec.get("hold", 0.0)))
        repeat = int(spec.get("repeat", -1))
        window = str(spec.get("window", "")).lower()

        if self._stop.wait(float(spec.get("initial_delay", 0.0))):
            return 0

        # Move the deadline by the nominal interval rather than sleeping
        # `interval` after each tick, so a slow tick cannot accumulate drift.
        next_at = time.monotonic()
        fired = 0
        while not self._stop.is_set():
            wait = next_at - time.monotonic()
            if wait > 0 and self._stop.wait(wait):
                break
            if not window or window in (self._focused_window() or "").lower():
                if 0 <= repeat <= fired:  # repeat == 0 fires nothing
                    break
                self._fire(spec, hold)
                fired += 1
            next_at += max(0.0, interval * (1 + random.uniform(-jitter, jitter)))
        return fired

    def _fire(self, spec, hold):
        device = self._device
        if spec.get("action") == "keys":
            keys = spec.get("keys") or []
            pressed = []
            try:
                for key in keys:
                    device.key_press(key)
                    pressed.append(key)
                self._stop.wait(hold)
            finally:
                for key in reversed(pressed):  # release only what actually went down
                    device.key_release(key)
        else:
            button = spec.get("button", "left")
            device.mouse_press(button)
            try:
                self._stop.wait(hold)
            finally:
                device.mouse_release(button)
