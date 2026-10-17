package neverkickoff;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * Best-effort title of the focused window - the Java half of {@code window.py}.
 *
 * Used by the "only click while X is focused" option. Returns null when the
 * title cannot be read, which the engine treats as "not a match" (safer: don't
 * click).
 */
public final class Window {
    private Window() {}

    /**
     * Bytes/str -> title or null. python-xlib hands back bytes for some windows;
     * the engine compares str, so bytes are decoded the way Python does, with
     * replacement characters for anything invalid.
     */
    public static String asText(Object value) {
        if (value instanceof byte[]) {
            String text = new String((byte[]) value, StandardCharsets.UTF_8);
            return text.isEmpty() ? null : text;
        }
        if (value instanceof String) {
            String text = (String) value;
            return text.isEmpty() ? null : text;
        }
        return null;
    }

    /**
     * The title of the focused window, or null when it cannot be read.
     *
     * X11 only, and only when {@code xdotool} is installed: python-xlib (which
     * comes with pynput) is not something a JDK-only build can drive, so the
     * same query is made through xdotool.
     */
    public static String activeTitle() {
        if ("wayland".equals(System.getenv("XDG_SESSION_TYPE"))) {
            // The compositor only lets XWayland clients be inspected, exactly as
            // python-xlib sees them, so a Wayland title is not reachable here.
            return null;
        }
        if (!Ydotool.which("xdotool")) {
            return null;
        }
        try {
            Process process = new ProcessBuilder("xdotool", "getactivewindow", "getwindowname").start();
            String text = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8).strip();
            if (process.waitFor() != 0 || text.isEmpty()) {
                return null;
            }
            return text;
        } catch (IOException error) {
            return null;
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            return null;
        }
    }
}
