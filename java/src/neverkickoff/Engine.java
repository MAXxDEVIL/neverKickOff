package neverkickoff;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.function.Supplier;

/**
 * Timing loop - the Java half of {@code engine.Engine}.
 *
 * Knows nothing about keyboards or mice: it is handed a {@link Device} and a
 * plain JSON spec. Behaviour is pinned by tests/fixtures/contract.json.
 */
public final class Engine<D extends Device> {
    private final D device;
    private final Supplier<String> focusedWindow;
    private final Stop stop = new Stop();
    private final Random rng = new Random();

    public Engine(D device, Supplier<String> focusedWindow) {
        this.device = device;
        this.focusedWindow = focusedWindow != null ? focusedWindow : () -> null;
    }

    public D device() {
        return device;
    }

    public void stop() {
        stop.set();
    }

    /** Fire macro ticks until repeat, duration or {@link #stop()} ends it. Returns ticks fired. */
    public long run(Object specValue) {
        Map<String, Object> spec = Spec.asMap(specValue);
        double interval = max0(asDouble(spec.get("interval"), 0.1));
        double jitter = max0(asDouble(spec.get("jitter"), 0.0));
        long repeat = asLong(spec.get("repeat"), -1);
        double duration = max0(asDouble(spec.get("duration"), 0.0));
        String window = asString(spec.get("window"), "").toLowerCase();
        List<Object> steps = Spec.normalizeSteps(spec);

        if (stop.await(asDouble(spec.get("initial_delay"), 0.0))) {
            return 0;
        }

        // duration == 0 means no time limit.
        long deadline = System.nanoTime() + (long) (duration * 1_000_000_000.0);
        // Move the deadline by the nominal interval rather than sleeping
        // `interval` after each tick, so a slow tick cannot accumulate drift.
        double nextAt = System.nanoTime();
        long fired = 0;
        while (!stop.isSet()) {
            if (duration > 0 && System.nanoTime() >= deadline) {
                break;
            }
            double wait = (nextAt - System.nanoTime()) / 1_000_000_000.0;
            if (wait > 0 && stop.await(wait)) {
                break;
            }
            String focusedRaw = focusedWindow.get();
            String focused = (focusedRaw == null ? "" : focusedRaw).toLowerCase();
            if (window.isEmpty() || focused.contains(window)) {
                if (repeat >= 0 && fired >= repeat) {
                    // repeat == 0 fires nothing.
                    break;
                }
                runSteps(steps);
                fired++;
            }
            nextAt += max0(interval * (1.0 + uniform(-jitter, jitter))) * 1_000_000_000.0;
        }
        return fired;
    }

    private void runSteps(List<Object> steps) {
        for (Object stepValue : steps) {
            if (stop.isSet()) {
                return;
            }
            Map<String, Object> step = Spec.asMap(stepValue);
            long count = Math.max(1, asLong(step.get("count"), 1));
            double hold = max0(asDouble(step.get("hold"), 0.0));
            for (long i = 0; i < count; i++) {
                if (stop.isSet()) {
                    return;
                }
                fire(step, hold);
            }
            if (stop.await(max0(asDouble(step.get("wait"), 0.0)))) {
                return;
            }
        }
    }

    private void fire(Map<String, Object> step, double hold) {
        if ("keys".equals(step.get("action"))) {
            List<Key> pressed = new ArrayList<>();
            RuntimeException failure = null;
            try {
                for (Key key : keysOf(step)) {
                    device.keyPress(key);
                    pressed.add(key);
                }
                stop.await(hold);
            } catch (RuntimeException error) {
                failure = error;
            } finally {
                // Release only what actually went down, newest first.
                for (int i = pressed.size() - 1; i >= 0; i--) {
                    try {
                        device.keyRelease(pressed.get(i));
                    } catch (RuntimeException ignored) {
                        // A release failure must not mask the original error.
                    }
                }
            }
            if (failure != null) {
                throw failure;
            }
        } else {
            String button = asString(step.get("button"), "left");
            device.mousePress(button);
            try {
                stop.await(hold);
            } finally {
                device.mouseRelease(button);
            }
        }
    }

    private List<Key> keysOf(Map<String, Object> step) {
        Object value = step.get("keys");
        if (!Spec.truthy(value)) {
            return new ArrayList<>();
        }
        List<Key> keys = new ArrayList<>();
        if (value instanceof List) {
            for (Object item : (List<?>) value) {
                if (item instanceof Key) {
                    keys.add((Key) item);
                } else if (item instanceof Map) {
                    keys.add(Key.fromJson(item));
                } else {
                    keys.add(Key.fromToken(item == null ? "" : String.valueOf(item)));
                }
            }
        }
        return keys;
    }

    private double uniform(double a, double b) {
        return a + (b - a) * rng.nextDouble();
    }

    /** {@code max(0.0, x)}, which also folds NaN to 0.0 the way Python's max does. */
    public static double max0(double value) {
        return value > 0.0 ? value : 0.0;
    }

    private static double asDouble(Object value, double fallback) {
        return value instanceof Number ? ((Number) value).doubleValue() : fallback;
    }

    private static long asLong(Object value, long fallback) {
        return value instanceof Number ? ((Number) value).longValue() : fallback;
    }

    private static String asString(Object value, String fallback) {
        return value instanceof String ? (String) value : fallback;
    }

    /**
     * {@code threading.Event}: set-once, and a wait that notices the stop
     * immediately rather than sleeping out the whole timeout.
     */
    public static final class Stop {
        private boolean stopped;

        public synchronized void set() {
            stopped = true;
            notifyAll();
        }

        public synchronized boolean isSet() {
            return stopped;
        }

        /** True once the stop is set, false on timeout. A zero or negative wait never sleeps. */
        public boolean await(double seconds) {
            if (Double.isNaN(seconds) || seconds <= 0.0) {
                synchronized (this) {
                    return stopped;
                }
            }
            double bounded = Double.isInfinite(seconds) ? Long.MAX_VALUE / 1_000_000_000.0 : seconds;
            long deadline = System.nanoTime() + (long) (bounded * 1_000_000_000.0);
            synchronized (this) {
                while (!stopped) {
                    long remaining = deadline - System.nanoTime();
                    if (remaining <= 0) {
                        break;
                    }
                    try {
                        wait(remaining / 1_000_000L, (int) (remaining % 1_000_000L));
                    } catch (InterruptedException error) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
                return stopped;
            }
        }
    }
}
