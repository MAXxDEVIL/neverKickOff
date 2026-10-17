package neverkickoff;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * tkinter key event -> hotkey string, the Java half of {@code hotkeys.format_hotkey}.
 */
public final class Hotkeys {
    private Hotkeys() {}

    /** {@code (state bit, modifier name)}. Order controls the printed order. */
    private static final int[] MODIFIER_BITS = {0x0004, 0x0008, 0x0001, 0x0040};
    private static final String[] MODIFIER_NAMES = {"ctrl", "alt", "shift", "cmd"};

    /** Keysyms that are a modifier on their own; a hotkey needs a real key. */
    private static final Set<String> MODIFIER_KEYSYMS = Set.of(
            "shift_l", "shift_r", "control_l", "control_r", "alt_l", "alt_r",
            "super_l", "super_r", "meta_l", "meta_r", "caps_lock", "num_lock",
            "iso_level3_shift");

    /** tkinter keysym -> pynput name, where they differ. */
    private static final Map<String, String> NAMES = new LinkedHashMap<>();
    static {
        NAMES.put("escape", "esc");
        NAMES.put("return", "enter");
        NAMES.put("kp_enter", "enter");
        NAMES.put("prior", "page_up");
        NAMES.put("next", "page_down");
        NAMES.put("print", "print_screen");
        NAMES.put("back_space", "backspace");
    }

    /** {@code 's'} with Ctrl+Alt held -> {@code <ctrl>+<alt>+s}. Null if only a modifier was pressed. */
    public static String formatHotkey(String keysym, int state) {
        String lower = keysym.toLowerCase();
        if (MODIFIER_KEYSYMS.contains(lower)) {
            return null;
        }
        String name = NAMES.getOrDefault(lower, lower);
        if (name.isEmpty()) {
            return null;
        }
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < MODIFIER_BITS.length; i++) {
            if ((state & MODIFIER_BITS[i]) != 0) {
                if (out.length() > 0) {
                    out.append('+');
                }
                out.append(token(MODIFIER_NAMES[i]));
            }
        }
        if (out.length() > 0) {
            out.append('+');
        }
        out.append(token(name));
        return out.toString();
    }

    /** pynput wants {@code <ctrl>}, {@code <f6>} but a bare {@code s} for single characters. */
    private static String token(String name) {
        return name.length() == 1 ? name : "<" + name + ">";
    }
}
