package neverkickoff;

/** A device call failed. Mirrors the exception the Python device would raise. */
public class DeviceException extends RuntimeException {
    public DeviceException(String message) {
        super(message);
    }

    public DeviceException(String message, Throwable cause) {
        super(message, cause);
    }
}
