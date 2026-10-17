package neverkickoff;

import java.awt.Robot;
import java.awt.event.InputEvent;
import java.awt.event.KeyEvent;

/**
 * The X11/XWayland input device, the role pynput's Controller plays in Python.
 *
 * {@code java.awt.Robot} is JDK-only, so no dependency is needed; it drives the
 * same X server pynput does, and is just as invisible to a Wayland compositor
 * (see {@link Ydotool}). The Robot is created lazily so a headless start prints
 * its lines and only fails when the first key or click is actually injected.
 */
public final class RobotDevice implements Device {
    private Robot robot;

    private Robot robot() {
        if (robot == null) {
            try {
                robot = new Robot();
            } catch (Exception error) {
                throw new DeviceException("cannot create AWT Robot: " + error.getMessage());
            }
        }
        return robot;
    }

    private static int buttonMask(String button) {
        switch (button) {
            case "left": return InputEvent.BUTTON1_DOWN_MASK;
            case "middle": return InputEvent.BUTTON2_DOWN_MASK;
            case "right": return InputEvent.BUTTON3_DOWN_MASK;
            default: throw new DeviceException("unknown button " + button);
        }
    }

    @Override
    public void mousePress(String button) {
        robot().mousePress(buttonMask(button));
    }

    @Override
    public void mouseRelease(String button) {
        robot().mouseRelease(buttonMask(button));
    }

    @Override
    public void keyPress(Key key) {
        robot().keyPress(keyCode(key));
    }

    @Override
    public void keyRelease(Key key) {
        robot().keyRelease(keyCode(key));
    }

    private static int keyCode(Key key) {
        if (!key.isNamed()) {
            int code = KeyEvent.getExtendedKeyCodeForChar(key.charValue());
            if (code == KeyEvent.VK_UNDEFINED) {
                throw new DeviceException("no AWT keycode for '" + key.charValue() + "'");
            }
            return code;
        }
        String name = key.name();
        switch (name) {
            case "ctrl": case "ctrl_l": case "ctrl_r": return KeyEvent.VK_CONTROL;
            case "alt": case "alt_l": case "alt_r": return KeyEvent.VK_ALT;
            case "alt_gr": return KeyEvent.VK_ALT_GRAPH;
            case "shift": case "shift_l": case "shift_r": return KeyEvent.VK_SHIFT;
            case "cmd": case "cmd_l": case "cmd_r": return KeyEvent.VK_META;
            case "enter": return KeyEvent.VK_ENTER;
            case "esc": return KeyEvent.VK_ESCAPE;
            case "tab": return KeyEvent.VK_TAB;
            case "space": return KeyEvent.VK_SPACE;
            case "backspace": return KeyEvent.VK_BACK_SPACE;
            case "delete": return KeyEvent.VK_DELETE;
            case "insert": return KeyEvent.VK_INSERT;
            case "up": return KeyEvent.VK_UP;
            case "down": return KeyEvent.VK_DOWN;
            case "left": return KeyEvent.VK_LEFT;
            case "right": return KeyEvent.VK_RIGHT;
            case "home": return KeyEvent.VK_HOME;
            case "end": return KeyEvent.VK_END;
            case "page_up": return KeyEvent.VK_PAGE_UP;
            case "page_down": return KeyEvent.VK_PAGE_DOWN;
            case "caps_lock": return KeyEvent.VK_CAPS_LOCK;
            case "num_lock": return KeyEvent.VK_NUM_LOCK;
            case "scroll_lock": return KeyEvent.VK_SCROLL_LOCK;
            case "print_screen": return KeyEvent.VK_PRINTSCREEN;
            case "pause": return KeyEvent.VK_PAUSE;
            case "menu": return KeyEvent.VK_CONTEXT_MENU;
            default:
                if (name.length() > 1 && name.charAt(0) == 'f') {
                    try {
                        int number = Integer.parseInt(name.substring(1));
                        if (number >= 1 && number <= 24) {
                            return KeyEvent.VK_F1 + (number - 1);
                        }
                    } catch (NumberFormatException ignored) {
                        // fall through to the unsupported-key error
                    }
                }
                throw new DeviceException("no AWT keycode for Key." + name);
        }
    }
}
