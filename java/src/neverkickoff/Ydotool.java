package neverkickoff;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Input injection through ydotool, for Wayland sessions - the Java half of
 * {@code ydotool.py}.
 *
 * Shells out exactly like the Python version: this is the backend that actually
 * works on Wayland, where the X11/XWayland device cannot inject.
 */
public final class Ydotool {
    private Ydotool() {}

    /** ydotool's button bitmask: low bits pick the button, 0x40 is press, 0x80 release. */
    static final Map<String, Integer> BUTTONS = Map.of("left", 0x00, "right", 0x01, "middle", 0x02);

    /** pynput {@code Key.name} -> the {@code KEY_*} name in {@code <linux/input-event-codes.h>}. */
    static final Map<String, String> KEYS = buildKeys();

    /** Punctuation parse_combo can produce; letters and digits are handled directly. */
    static final Map<String, String> SYMBOLS = buildSymbols();

    /** {@code KEY_*} name -> Linux input-event code, dumped from evdev (Linux 6.x). */
    static final Map<String, Integer> LINUX_CODES = buildCodes();

    private static Map<String, String> buildKeys() {
        Map<String, String> map = new LinkedHashMap<>();
        map.put("ctrl", "LEFTCTRL");
        map.put("ctrl_l", "LEFTCTRL");
        map.put("ctrl_r", "RIGHTCTRL");
        map.put("alt", "LEFTALT");
        map.put("alt_l", "LEFTALT");
        map.put("alt_r", "RIGHTALT");
        map.put("alt_gr", "RIGHTALT");
        map.put("shift", "LEFTSHIFT");
        map.put("shift_l", "LEFTSHIFT");
        map.put("shift_r", "RIGHTSHIFT");
        map.put("cmd", "LEFTMETA");
        map.put("cmd_l", "LEFTMETA");
        map.put("cmd_r", "RIGHTMETA");
        map.put("enter", "ENTER");
        map.put("esc", "ESC");
        map.put("tab", "TAB");
        map.put("space", "SPACE");
        map.put("backspace", "BACKSPACE");
        map.put("delete", "DELETE");
        map.put("insert", "INSERT");
        map.put("up", "UP");
        map.put("down", "DOWN");
        map.put("left", "LEFT");
        map.put("right", "RIGHT");
        map.put("home", "HOME");
        map.put("end", "END");
        map.put("page_up", "PAGEUP");
        map.put("page_down", "PAGEDOWN");
        map.put("caps_lock", "CAPSLOCK");
        map.put("num_lock", "NUMLOCK");
        map.put("print_screen", "SYSRQ");
        map.put("pause", "PAUSE");
        map.put("menu", "MENU");
        // KEYS.update({f"f{i}": f"F{i}" for i in range(1, 21)})
        for (int i = 1; i <= 20; i++) {
            map.put("f" + i, "F" + i);
        }
        return map;
    }

    private static Map<String, String> buildSymbols() {
        Map<String, String> map = new LinkedHashMap<>();
        map.put("-", "KEY_MINUS");
        map.put("=", "KEY_EQUAL");
        map.put("[", "KEY_LEFTBRACE");
        map.put("]", "KEY_RIGHTBRACE");
        map.put(";", "KEY_SEMICOLON");
        map.put("'", "KEY_APOSTROPHE");
        map.put(",", "KEY_COMMA");
        map.put(".", "KEY_DOT");
        map.put("/", "KEY_SLASH");
        map.put("\\", "KEY_BACKSLASH");
        map.put("`", "KEY_GRAVE");
        return map;
    }

    private static Map<String, Integer> buildCodes() {
        Map<String, Integer> map = new HashMap<>();
        Object[][] codes = {
                {"KEY_ESC", 1}, {"KEY_1", 2}, {"KEY_2", 3}, {"KEY_3", 4}, {"KEY_4", 5},
                {"KEY_5", 6}, {"KEY_6", 7}, {"KEY_7", 8}, {"KEY_8", 9}, {"KEY_9", 10},
                {"KEY_0", 11}, {"KEY_MINUS", 12}, {"KEY_EQUAL", 13}, {"KEY_BACKSPACE", 14},
                {"KEY_TAB", 15}, {"KEY_Q", 16}, {"KEY_W", 17}, {"KEY_E", 18}, {"KEY_R", 19},
                {"KEY_T", 20}, {"KEY_Y", 21}, {"KEY_U", 22}, {"KEY_I", 23}, {"KEY_O", 24},
                {"KEY_P", 25}, {"KEY_LEFTBRACE", 26}, {"KEY_RIGHTBRACE", 27}, {"KEY_ENTER", 28},
                {"KEY_LEFTCTRL", 29}, {"KEY_A", 30}, {"KEY_S", 31}, {"KEY_D", 32}, {"KEY_F", 33},
                {"KEY_G", 34}, {"KEY_H", 35}, {"KEY_J", 36}, {"KEY_K", 37}, {"KEY_L", 38},
                {"KEY_SEMICOLON", 39}, {"KEY_APOSTROPHE", 40}, {"KEY_GRAVE", 41},
                {"KEY_LEFTSHIFT", 42}, {"KEY_BACKSLASH", 43}, {"KEY_Z", 44}, {"KEY_X", 45},
                {"KEY_C", 46}, {"KEY_V", 47}, {"KEY_B", 48}, {"KEY_N", 49}, {"KEY_M", 50},
                {"KEY_COMMA", 51}, {"KEY_DOT", 52}, {"KEY_SLASH", 53}, {"KEY_RIGHTSHIFT", 54},
                {"KEY_LEFTALT", 56}, {"KEY_SPACE", 57}, {"KEY_CAPSLOCK", 58}, {"KEY_F1", 59},
                {"KEY_F2", 60}, {"KEY_F3", 61}, {"KEY_F4", 62}, {"KEY_F5", 63}, {"KEY_F6", 64},
                {"KEY_F7", 65}, {"KEY_F8", 66}, {"KEY_F9", 67}, {"KEY_F10", 68},
                {"KEY_NUMLOCK", 69}, {"KEY_F11", 87}, {"KEY_F12", 88}, {"KEY_RIGHTCTRL", 97},
                {"KEY_SYSRQ", 99}, {"KEY_RIGHTALT", 100}, {"KEY_HOME", 102}, {"KEY_UP", 103},
                {"KEY_PAGEUP", 104}, {"KEY_LEFT", 105}, {"KEY_RIGHT", 106}, {"KEY_END", 107},
                {"KEY_DOWN", 108}, {"KEY_PAGEDOWN", 109}, {"KEY_INSERT", 110},
                {"KEY_DELETE", 111}, {"KEY_PAUSE", 119}, {"KEY_LEFTMETA", 125},
                {"KEY_RIGHTMETA", 126}, {"KEY_MENU", 139}, {"KEY_F13", 183}, {"KEY_F14", 184},
                {"KEY_F15", 185}, {"KEY_F16", 186}, {"KEY_F17", 187}, {"KEY_F18", 188},
                {"KEY_F19", 189}, {"KEY_F20", 190},
        };
        for (Object[] entry : codes) {
            map.put((String) entry[0], (Integer) entry[1]);
        }
        return map;
    }

    /** {@code KEYS} plus the entries Python adds dynamically; the table already holds them. */
    private static String namedKey(String name) {
        return KEYS.get(name);
    }

    /**
     * {@code ydotool.keycode}: a key -> a Linux input-event keycode. A failure
     * throws, which is all the contract records - the message is Python's.
     */
    public static int keycode(Key key) {
        String name;
        if (!key.isNamed()) {
            char c = key.charValue();
            if (c >= 'a' && c <= 'z') {
                name = "KEY_" + Character.toUpperCase(c);
            } else if (c >= '0' && c <= '9') {
                name = "KEY_" + c;
            } else {
                String symbol = SYMBOLS.get(String.valueOf(c));
                if (symbol == null) {
                    throw new DeviceException("ydotool has no keycode for '" + c + "'");
                }
                name = symbol;
            }
        } else {
            String mapped = namedKey(key.name());
            if (mapped == null) {
                throw new DeviceException("ydotool has no keycode for Key." + key.name());
            }
            name = "KEY_" + mapped;
        }
        Integer code = LINUX_CODES.get(name);
        if (code == null) {
            throw new DeviceException("ydotool has no keycode for " + name);
        }
        return code;
    }

    /** {@code shutil.which}, good enough for "is this binary on PATH". */
    static boolean which(String binary) {
        String path = System.getenv("PATH");
        if (path == null) {
            return false;
        }
        for (String dir : path.split(File.pathSeparator)) {
            if (dir.isEmpty()) {
                continue;
            }
            File file = new File(dir, binary);
            if (file.isFile() && file.canExecute()) {
                return true;
            }
        }
        return false;
    }

    /**
     * True when this session should inject through ydotool rather than the X11
     * device: "ydotool is installed and we are not on X11", so a session that
     * never set XDG_SESSION_TYPE still works.
     */
    public static boolean available() {
        return which("ydotool") && !"x11".equals(System.getenv("XDG_SESSION_TYPE"));
    }

    /** Why injected input will not arrive, or null when it will. */
    public static String problem() {
        if (!available()) {
            if ("wayland".equals(System.getenv("XDG_SESSION_TYPE"))) {
                return "Wayland ignores pynput's input: install ydotool and start "
                        + "ydotoold (see the Wayland section of README.md)";
            }
            return null;
        }
        try {
            Process process = new ProcessBuilder("ydotool", "debug").start();
            String stdout = readAll(process.getInputStream());
            int code = process.waitFor();
            if (code != 0) {
                String trimmed = stdout.strip();
                String first = trimmed.isEmpty() ? "no response" : trimmed.split("\\R", -1)[0];
                return "ydotool cannot reach ydotoold (" + first + ")";
            }
            return null;
        } catch (IOException error) {
            return "ydotool cannot reach ydotoold (no response)";
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            return "ydotool cannot reach ydotoold (no response)";
        }
    }

    private static String readAll(InputStream stream) throws IOException {
        return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
    }

    private static int buttonBits(String button) {
        Integer bits = BUTTONS.get(button);
        if (bits == null) {
            throw new DeviceException("unknown button " + button);
        }
        return bits;
    }

    /** Same interface as the X11 device, but every call shells out to ydotool. */
    public static final class YdotoolDevice implements Device {
        private void exec(String... args) {
            String[] command = new String[args.length + 1];
            command[0] = "ydotool";
            System.arraycopy(args, 0, command, 1, args.length);
            try {
                Process process = new ProcessBuilder(command).inheritIO().start();
                int code = process.waitFor();
                if (code != 0) {
                    throw new DeviceException("ydotool exited with " + code);
                }
            } catch (IOException error) {
                throw new DeviceException(error.getMessage());
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
                throw new DeviceException("interrupted");
            }
        }

        @Override
        public void mousePress(String button) {
            exec("click", String.format("0x%x", 0x40 | buttonBits(button)));
        }

        @Override
        public void mouseRelease(String button) {
            exec("click", String.format("0x%x", 0x80 | buttonBits(button)));
        }

        @Override
        public void keyPress(Key key) {
            exec("key", keycode(key) + ":1");
        }

        @Override
        public void keyRelease(Key key) {
            exec("key", keycode(key) + ":0");
        }
    }
}
