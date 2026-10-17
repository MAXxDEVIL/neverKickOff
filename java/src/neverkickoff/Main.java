package neverkickoff;

import java.io.IOException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * neverKickOff CLI - the Java half of {@code main.main()}.
 *
 *     neverkickoff [config.json] [--tray]
 *
 * Toggle clicking with the config's hotkeys.toggle combo (default Ctrl+Alt+S),
 * panic-stop with hotkeys.panic (default Esc). See README.md.
 */
public final class Main {
    private Main() {}

    public static void main(String[] argv) {
        boolean wantsTray = false;
        List<String> args = new ArrayList<>();
        for (String arg : argv) {
            if ("--tray".equals(arg)) {
                wantsTray = true;
            } else {
                args.add(arg);
            }
        }

        Path path = args.isEmpty() ? defaultConfigPath() : Paths.get(args.get(0));
        String text;
        try {
            text = new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
        } catch (IOException error) {
            System.err.println("cannot read " + path + ": " + error.getMessage());
            System.exit(1);
            return;
        }
        Object config;
        try {
            config = Json.parse(text);
        } catch (RuntimeException error) {
            System.err.println("cannot parse " + path + ": " + error.getMessage());
            System.exit(1);
            return;
        }
        Object spec;
        try {
            spec = Spec.loadSpec(get(config, "click"));
        } catch (RuntimeException error) {
            System.err.println("bad config: " + error.getMessage());
            System.exit(1);
            return;
        }

        String toggle = asString(get(get(config, "hotkeys"), "toggle"), "<ctrl>+<alt>+s");
        String panic = asString(get(get(config, "hotkeys"), "panic"), "<esc>");

        Clicker clicker = new Clicker(makeDevice(), spec, Window::activeTitle);

        String issue = Ydotool.problem();
        if (issue != null) {
            System.out.println("warning: " + issue);
        }
        System.out.println("ready - " + toggle + " start/stop, " + panic + " panic-stop");

        if (wantsTray) {
            // The Python version can fall back to pystray/Pillow when they import.
            // This build has no tray backend; see java/README.md.
            System.out.println("tray unavailable (no tray backend in this build); running without it");
        }

        HotkeyBackend backend = loadBackend();
        if (backend == null) {
            System.err.println("cannot watch for hotkeys: JNativeHook is not on the classpath "
                    + "(see java/README.md)");
            clicker.stop();
            System.exit(1);
            return;
        }
        try {
            backend.run(toggle, panic, clicker::toggle, clicker::stop);
        } catch (Throwable error) {
            System.err.println("cannot watch for hotkeys: " + error.getMessage());
            clicker.stop();
            System.exit(1);
        }
    }

    /** ydotool on a Wayland session (the X11 device cannot inject there), else Robot. */
    private static Device makeDevice() {
        if (Ydotool.available()) {
            System.out.println("input: ydotool (Wayland)");
            return new Ydotool.YdotoolDevice();
        }
        return new RobotDevice();
    }

    /** JNativeHook lives outside the main jar, so it is loaded if present and only then. */
    private static HotkeyBackend loadBackend() {
        try {
            return (HotkeyBackend) Class.forName("neverkickoff.JNativeHookBackend")
                    .getDeclaredConstructor()
                    .newInstance();
        } catch (Throwable missing) {
            return null;
        }
    }

    private static Path defaultConfigPath() {
        try {
            URL location = Main.class.getProtectionDomain().getCodeSource().getLocation();
            Path path = Paths.get(location.toURI());
            Path dir = Files.isDirectory(path) ? path : path.getParent();
            return dir.resolve("config.json");
        } catch (Exception error) {
            return Paths.get("config.json");
        }
    }

    private static Object get(Object map, String key) {
        if (map instanceof Map) {
            return ((Map<?, ?>) map).get(key);
        }
        return null;
    }

    private static String asString(Object value, String fallback) {
        return value instanceof String ? (String) value : fallback;
    }
}
