package neverkickoff;

import java.util.function.Supplier;

/**
 * Toggles one background {@link Engine} at a time - the Java half of
 * {@code main.Clicker}.
 */
public final class Clicker {
    private final Device device;
    private final Supplier<String> focusedWindow;
    private final Object lock = new Object();
    private Object spec;
    private Engine<Device> engine;

    public Clicker(Device device, Object spec, Supplier<String> focusedWindow) {
        this.device = device;
        this.spec = spec;
        this.focusedWindow = focusedWindow;
    }

    public void setSpec(Object spec) {
        synchronized (lock) {
            this.spec = spec;
        }
    }

    /** Start clicking, or stop it if already running. Returns true when started. */
    public boolean toggle() {
        Engine<Device> started;
        synchronized (lock) {
            if (engine != null) {
                engine.stop();
                engine = null;
                System.out.println("stopped");
                return false;
            }
            started = new Engine<>(device, focusedWindow);
            engine = started;
        }
        System.out.println("running");
        Thread thread = new Thread(() -> run(started), "neverkickoff-engine");
        thread.setDaemon(true);
        thread.start();
        return true;
    }

    private void run(Engine<Device> started) {
        long fired = 0;
        try {
            fired = started.run(spec);
        } catch (Exception error) {
            // A dead engine must not leave the toggle wedged.
            System.out.println("stopped after error: " + error.getMessage());
        } finally {
            synchronized (lock) {
                if (engine == started) {
                    engine = null;
                }
            }
        }
        System.out.println("done (" + fired + " ticks)");
    }

    public void stop() {
        synchronized (lock) {
            if (engine != null) {
                engine.stop();
                engine = null;
                System.out.println("stopped");
            }
        }
    }

    /** True while an engine is live; false once a finite run finishes. */
    public boolean running() {
        synchronized (lock) {
            return engine != null;
        }
    }
}
