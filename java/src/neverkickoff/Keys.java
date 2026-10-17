package neverkickoff;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Key names and combo parsing - the Java half of {@code main.parse_combo}.
 * Behaviour is pinned by tests/fixtures/contract.json.
 */
public final class Keys {
    private Keys() {}

    /** Mirrors Python's {@code KeyError} for an unknown key. */
    public static final class KeyError extends RuntimeException {
        public KeyError(String message) {
            super(message);
        }
    }

    /**
     * Every member of pynput's {@code keyboard.Key} enum, which is what
     * {@code hasattr(Key, name)} tests. Keep in step with the Python version if
     * pynput adds keys.
     */
    public static final Set<String> KEY_NAMES = new HashSet<>(Arrays.asList(
            "alt", "alt_gr", "alt_r", "backspace", "caps_lock", "cmd", "cmd_r", "ctrl",
            "ctrl_r", "delete", "down", "end", "enter", "esc", "f1", "f10", "f11", "f12",
            "f13", "f14", "f15", "f16", "f17", "f18", "f19", "f2", "f20", "f3", "f4",
            "f5", "f6", "f7", "f8", "f9", "home", "insert", "left", "media_next",
            "media_play_pause", "media_previous", "media_volume_down", "media_volume_mute",
            "media_volume_up", "menu", "num_lock", "page_down", "page_up", "pause",
            "print_screen", "right", "scroll_lock", "shift", "shift_r", "space", "tab", "up"));

    /** {@code main.ALIASES}. */
    private static final Map<String, String> ALIASES = new LinkedHashMap<>();
    static {
        ALIASES.put("control", "ctrl");
        ALIASES.put("escape", "esc");
        ALIASES.put("return", "enter");
        ALIASES.put("win", "cmd");
        ALIASES.put("super", "cmd");
        ALIASES.put("meta", "cmd");
        ALIASES.put("capslock", "caps_lock");
        ALIASES.put("pgup", "page_up");
        ALIASES.put("pgdn", "page_down");
    }

    public static String alias(String name) {
        String mapped = ALIASES.get(name);
        return mapped != null ? mapped : name;
    }

    /** {@code main.parse_combo("ctrl+alt+c")}. */
    public static List<Key> parseCombo(String combo) {
        // -1 keeps trailing empty parts, as Python's str.split does.
        return parseComboParts(Arrays.asList(combo.split("\\+", -1)));
    }

    /** {@code parse_combo} when the value may already be a list of parts. */
    public static List<Key> parseComboValue(Object value) {
        if (value instanceof String) {
            return parseCombo((String) value);
        }
        List<String> parts = new ArrayList<>();
        if (value instanceof List) {
            for (Object item : (List<?>) value) {
                parts.add(item instanceof String ? (String) item : "");
            }
        }
        return parseComboParts(parts);
    }

    /** A string is expected to be split before this, so the error reports the split list. */
    public static List<Key> parseComboParts(List<String> parts) {
        List<Key> keys = new ArrayList<>(parts.size());
        for (String part : parts) {
            String name = alias(stripAngles(part.strip()).toLowerCase());
            if (KEY_NAMES.contains(name)) {
                keys.add(Key.named(name));
            } else if (name.length() == 1) {
                keys.add(Key.ofChar(name.charAt(0)));
            } else {
                throw new KeyError("unknown key '" + part + "' in '" + pyListRepr(parts) + "'");
            }
        }
        return keys;
    }

    /** Parse combos into the tagged JSON form, so specs stay plain JSON values. */
    public static List<Object> parseComboToJson(Object value) {
        List<Object> out = new ArrayList<>();
        for (Key key : parseComboValue(value)) {
            out.add(key.toJson());
        }
        return out;
    }

    private static String stripAngles(String text) {
        int start = 0;
        int end = text.length();
        while (start < end && (text.charAt(start) == '<' || text.charAt(start) == '>')) {
            start++;
        }
        while (end > start && (text.charAt(end - 1) == '<' || text.charAt(end - 1) == '>')) {
            end--;
        }
        return text.substring(start, end);
    }

    /** Python's {@code repr()} for the simple strings key names use. */
    private static String pyRepr(String value) {
        if (value.contains("'") && !value.contains("\"")) {
            return "\"" + value + "\"";
        }
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'";
    }

    /** Python's {@code repr()} for a list of strings, e.g. {@code ['ctrl', 'c']}. */
    private static String pyListRepr(List<String> parts) {
        List<String> inner = new ArrayList<>(parts.size());
        for (String part : parts) {
            inner.add(pyRepr(part));
        }
        return "[" + String.join(", ", inner) + "]";
    }
}
