"""Timing loop for the auto clicker.

Deliberately knows nothing about keyboards or mice: it is handed a `device`
with mouse_press/mouse_release/key_press/key_release and a plain dict spec.
That keeps the schedule testable without a display or an input library.

A spec is a macro: a list of `steps` run in order every tick. A spec with no
`steps` is wrapped as one implicit step, so the older flat config still works.
"""
import random
import threading
import time


def normalize_steps(spec):
    """spec -> list of step dicts. A flat spec becomes a single implicit step."""
    steps = spec.get("steps")
    if steps:
        return steps
    return [{
        "action": spec.get("action", "mouse"),
        "button": spec.get("button", "left"),
        "keys": spec.get("keys") or [],
        "count": 1,
        "hold": spec.get("hold", 0.0),
        "wait": 0.0,
    }]


class Engine:
    def __init__(self, device, focused_window=None):
        self._device = device
        self._focused_window = focused_window or (lambda: None)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self, spec):
        """Fire macro ticks until repeat, duration or stop() ends it. Returns ticks fired."""
        interval = max(0.0, float(spec.get("interval", 0.1)))
        jitter = max(0.0, float(spec.get("jitter", 0.0)))
        repeat = int(spec.get("repeat", -1))
        duration = max(0.0, float(spec.get("duration", 0.0)))
        window = str(spec.get("window", "")).lower()
        steps = normalize_steps(spec)

        if self._stop.wait(float(spec.get("initial_delay", 0.0))):
            return 0

        deadline = time.monotonic() + duration  # duration == 0 means no time limit
        # Move the deadline by the nominal interval rather than sleeping
        # `interval` after each tick, so a slow tick cannot accumulate drift.
        next_at = time.monotonic()
        fired = 0
        while not self._stop.is_set():
            if duration and time.monotonic() >= deadline:
                break
            wait = next_at - time.monotonic()
            if wait > 0 and self._stop.wait(wait):
                break
            if not window or window in (self._focused_window() or "").lower():
                if 0 <= repeat <= fired:  # repeat == 0 fires nothing
                    break
                self._run_steps(steps)
                fired += 1
            next_at += max(0.0, interval * (1 + random.uniform(-jitter, jitter)))
        return fired

    def _run_steps(self, steps):
        for step in steps:
            if self._stop.is_set():
                return
            count = max(1, int(step.get("count", 1)))
            hold = max(0.0, float(step.get("hold", 0.0)))
            for _ in range(count):
                if self._stop.is_set():
                    return
                self._fire(step, hold)
            if self._stop.wait(max(0.0, float(step.get("wait", 0.0)))):
                return

    def _fire(self, step, hold):
        device = self._device
        if step.get("action") == "keys":
            keys = step.get("keys") or []
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
            button = step.get("button", "left")
            device.mouse_press(button)
            try:
                self._stop.wait(hold)
            finally:
                device.mouse_release(button)
