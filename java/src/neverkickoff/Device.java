package neverkickoff;

/**
 * The device boundary the engine talks to. Same four methods as Python's
 * {@code PynputDevice} / {@code ydotool.YdotoolDevice}, so the engine stays
 * ignorant of keyboards and mice and stays testable.
 *
 * A failed call throws a {@link DeviceException}; a dead device must leave the
 * toggle un-wedged, which the clicker handles.
 */
public interface Device {
    void mousePress(String button);

    void mouseRelease(String button);

    void keyPress(Key key);

    void keyRelease(Key key);
}
