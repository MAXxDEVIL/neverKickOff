package neverkickoff;

import com.github.kwhat.jnativehook.GlobalScreen;
import com.github.kwhat.jnativehook.NativeInputEvent;
import com.github.kwhat.jnativehook.keyboard.NativeKeyEvent;
import com.github.kwhat.jnativehook.keyboard.NativeKeyListener;

import java.lang.reflect.Field;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * The global-hotkey backend, built on JNativeHook.
 *
 * This class only compiles when {@code lib/jnativehook-2.2.2.jar} is on the
 * classpath (see build.sh), and Main loads it reflectively. It mirrors pynput's
 * GlobalHotKeys: the toggle starts or stops clicking, the panic key stops it.
 */
public final class JNativeHookBackend implements HotkeyBackend {
    @Override
    public void run(String toggle, String panic, Runnable onToggle, Runnable onPanic) throws Exception {
        Hotkey toggleHotkey = Hotkey.parse(toggle);
        Hotkey panicHotkey = Hotkey.parse(panic);

        // JNativeHook logs every event at INFO by default; keep the CLI output clean.
        Logger logger = Logger.getLogger(GlobalScreen.class.getPackage().getName());
        logger.setLevel(Level.OFF);
        logger.setUseParentHandlers(false);

        GlobalScreen.registerNativeHook();
        GlobalScreen.addNativeKeyListener(new Listener(toggleHotkey, panicHotkey, onToggle, onPanic));
        new CountDownLatch(1).await();
    }

    /** A parsed pynput-style combo: a key code plus the exact modifier set it needs. */
    static final class Hotkey {
        private final int keyCode;
        private final boolean ctrl;
        private final boolean alt;
        private final boolean shift;
        private final boolean meta;

        private Hotkey(int keyCode, boolean ctrl, boolean alt, boolean shift, boolean meta) {
            this.keyCode = keyCode;
            this.ctrl = ctrl;
            this.alt = alt;
            this.shift = shift;
            this.meta = meta;
        }

        static Hotkey parse(String combo) {
            boolean ctrl = false;
            boolean alt = false;
            boolean shift = false;
            boolean meta = false;
            int keyCode = -1;
            for (String raw : combo.split("\\+")) {
                String name = strip(raw).toLowerCase();
                switch (name) {
                    case "ctrl": case "control": ctrl = true; break;
                    case "alt": alt = true; break;
                    case "shift": shift = true; break;
                    case "cmd": case "super": case "win": case "meta": meta = true; break;
                    default: keyCode = virtualCode(name);
                }
            }
            if (keyCode < 0) {
                throw new IllegalArgumentException("hotkey has no key: " + combo);
            }
            return new Hotkey(keyCode, ctrl, alt, shift, meta);
        }

        boolean matches(int modifiers, int pressedCode) {
            if (pressedCode != keyCode) {
                return false;
            }
            if (((modifiers & NativeInputEvent.CTRL_MASK) != 0) != ctrl) {
                return false;
            }
            if (((modifiers & NativeInputEvent.ALT_MASK) != 0) != alt) {
                return false;
            }
            if (((modifiers & NativeInputEvent.SHIFT_MASK) != 0) != shift) {
                return false;
            }
            return ((modifiers & NativeInputEvent.META_MASK) != 0) == meta;
        }

        private static String strip(String text) {
            String trimmed = text.strip();
            int start = 0;
            int end = trimmed.length();
            while (start < end && (trimmed.charAt(start) == '<' || trimmed.charAt(start) == '>')) {
                start++;
            }
            while (end > start && (trimmed.charAt(end - 1) == '<' || trimmed.charAt(end - 1) == '>')) {
                end--;
            }
            return trimmed.substring(start, end);
        }

        /** pynput-ish key name -> JNativeHook virtual key code, resolved by name. */
        private static int virtualCode(String name) {
            String field;
            if (name.length() == 1) {
                field = "VC_" + Character.toUpperCase(name.charAt(0));
            } else {
                field = FIELD_NAMES.getOrDefault(name, "VC_" + name.toUpperCase());
            }
            try {
                Field constant = NativeKeyEvent.class.getField(field);
                return constant.getInt(null);
            } catch (ReflectiveOperationException error) {
                throw new IllegalArgumentException("hotkey key not supported: " + name);
            }
        }

        private static final Map<String, String> FIELD_NAMES = new LinkedHashMap<>();
        static {
            FIELD_NAMES.put("esc", "VC_ESCAPE");
            FIELD_NAMES.put("escape", "VC_ESCAPE");
            FIELD_NAMES.put("enter", "VC_ENTER");
            FIELD_NAMES.put("return", "VC_ENTER");
            FIELD_NAMES.put("space", "VC_SPACE");
            FIELD_NAMES.put("tab", "VC_TAB");
            FIELD_NAMES.put("backspace", "VC_BACK_SPACE");
            FIELD_NAMES.put("delete", "VC_DELETE");
            FIELD_NAMES.put("insert", "VC_INSERT");
            FIELD_NAMES.put("up", "VC_UP");
            FIELD_NAMES.put("down", "VC_DOWN");
            FIELD_NAMES.put("left", "VC_LEFT");
            FIELD_NAMES.put("right", "VC_RIGHT");
            FIELD_NAMES.put("home", "VC_HOME");
            FIELD_NAMES.put("end", "VC_END");
            FIELD_NAMES.put("page_up", "VC_PAGE_UP");
            FIELD_NAMES.put("page_down", "VC_PAGE_DOWN");
            FIELD_NAMES.put("caps_lock", "VC_CAPS_LOCK");
            FIELD_NAMES.put("num_lock", "VC_NUM_LOCK");
            FIELD_NAMES.put("scroll_lock", "VC_SCROLL_LOCK");
            FIELD_NAMES.put("print_screen", "VC_PRINTSCREEN");
            FIELD_NAMES.put("pause", "VC_PAUSE");
            FIELD_NAMES.put("menu", "VC_CONTEXT_MENU");
            FIELD_NAMES.put("ctrl", "VC_CONTROL");
            FIELD_NAMES.put("ctrl_l", "VC_CONTROL");
            FIELD_NAMES.put("ctrl_r", "VC_CONTROL");
            FIELD_NAMES.put("alt", "VC_ALT");
            FIELD_NAMES.put("alt_l", "VC_ALT");
            FIELD_NAMES.put("alt_r", "VC_ALT");
            FIELD_NAMES.put("shift", "VC_SHIFT");
            FIELD_NAMES.put("shift_l", "VC_SHIFT");
            FIELD_NAMES.put("shift_r", "VC_SHIFT");
            FIELD_NAMES.put("cmd", "VC_META");
            FIELD_NAMES.put("cmd_l", "VC_META");
            FIELD_NAMES.put("cmd_r", "VC_META");
        }
    }

    /** Fires the matching action on the key's press transition only. */
    private static final class Listener implements NativeKeyListener {
        private final Hotkey toggle;
        private final Hotkey panic;
        private final Runnable onToggle;
        private final Runnable onPanic;
        private final Set<Integer> down = new HashSet<>();

        Listener(Hotkey toggle, Hotkey panic, Runnable onToggle, Runnable onPanic) {
            this.toggle = toggle;
            this.panic = panic;
            this.onToggle = onToggle;
            this.onPanic = onPanic;
        }

        @Override
        public void nativeKeyPressed(NativeKeyEvent event) {
            int code = event.getKeyCode();
            if (!down.add(code)) {
                return; // auto-repeat
            }
            int modifiers = event.getModifiers();
            if (toggle.matches(modifiers, code)) {
                onToggle.run();
            } else if (panic.matches(modifiers, code)) {
                onPanic.run();
            }
        }

        @Override
        public void nativeKeyReleased(NativeKeyEvent event) {
            down.remove(event.getKeyCode());
        }
    }
}
