"""Timing loop for the auto clicker.

Deliberately knows nothing about keyboards or mice: it is handed a `device`
with mouse_press/mouse_release/key_press/key_release and a plain dict spec.
That keeps the schedule testable without a display or an input library.
"""
import random
import threading
import time


class Engine:
    def __init__(self, device):
        self._device = device
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
            self._fire(spec, hold)
            fired += 1
            if 0 <= repeat <= fired:
                break
            next_at += max(0.0, interval * (1 + random.uniform(-jitter, jitter)))
        return fired

    def _fire(self, spec, hold):
        device = self._device
        if spec.get("action") == "keys":
            keys = spec.get("keys") or []
            for key in keys:
                device.key_press(key)
            try:
                self._stop.wait(hold)
            finally:
                for key in reversed(keys):  # a stuck modifier is worse than a missed tick
                    device.key_release(key)
        else:
            button = spec.get("button", "left")
            device.mouse_press(button)
            try:
                self._stop.wait(hold)
            finally:
                device.mouse_release(button)
