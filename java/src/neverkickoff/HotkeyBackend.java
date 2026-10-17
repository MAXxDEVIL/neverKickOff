package neverkickoff;

/**
 * A global-hotkey listener backend.
 *
 * Main loads an implementation by name through reflection, so the jar has no
 * hard dependency on JNativeHook: without it on the classpath, Main reports the
 * gap and exits non-zero. See java/README.md.
 */
public interface HotkeyBackend {
    /** Watch for both combos and block until the process ends. */
    void run(String toggle, String panic, Runnable onToggle, Runnable onPanic) throws Exception;
}
