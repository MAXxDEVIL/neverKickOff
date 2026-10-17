package neverkickoff;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * A key in the neutral shape the cross-language contract uses: either a named
 * pynput key or a single character. Python hands pynput {@code Key}/{@code KeyCode}
 * objects to the device; this is the equivalent, and {@link #token()} produces the
 * same string the engine records.
 */
public final class Key {
    private final String name;   // non-null for a named key
    private final Character ch;  // non-null for a character key

    private Key(String name, Character ch) {
        this.name = name;
        this.ch = ch;
    }

    public static Key named(String name) {
        return new Key(name, null);
    }

    public static Key ofChar(char c) {
        return new Key(null, c);
    }

    public boolean isNamed() {
        return name != null;
    }

    public String name() {
        return name;
    }

    public char charValue() {
        return ch;
    }

    /** The string a device call is recorded as: {@code ctrl}, {@code f6}, {@code c}. */
    public String token() {
        return name != null ? name : String.valueOf(ch);
    }

    /** Build from a bare token, the way parse_combo classifies a name. */
    public static Key fromToken(String token) {
        if (token.length() == 1) {
            return ofChar(token.charAt(0));
        }
        return named(token);
    }

    /** The tagged JSON form: {@code {"kind":"named","name":"ctrl"}} or {@code {"kind":"char","char":"c"}}. */
    public Map<String, Object> toJson() {
        Map<String, Object> out = new LinkedHashMap<>();
        if (name != null) {
            out.put("kind", "named");
            out.put("name", name);
        } else {
            out.put("kind", "char");
            out.put("char", String.valueOf(ch));
        }
        return out;
    }

    public static Key fromJson(Object value) {
        if (value instanceof Key) {
            return (Key) value;
        }
        if (value instanceof String) {
            return fromToken((String) value);
        }
        if (!(value instanceof Map)) {
            throw new IllegalArgumentException("not a key: " + value);
        }
        Map<?, ?> map = (Map<?, ?>) value;
        Object kind = map.get("kind");
        if ("named".equals(kind)) {
            return named(String.valueOf(map.get("name")));
        }
        if ("char".equals(kind)) {
            Object raw = map.get("char");
            String text = raw == null ? "" : String.valueOf(raw);
            if (text.isEmpty()) {
                throw new IllegalArgumentException("empty char key");
            }
            return ofChar(text.charAt(0));
        }
        if (kind == null && map.containsKey("name")) {
            return named(String.valueOf(map.get("name")));
        }
        throw new IllegalArgumentException("unknown key form: " + value);
    }

    @Override
    public String toString() {
        return token();
    }
}
