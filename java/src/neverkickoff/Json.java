package neverkickoff;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Minimal JSON parser, writer and deep-equals. The JDK ships no JSON, so the
 * port carries its own, mirroring the shapes serde_json gives the Rust port:
 * objects become {@link LinkedHashMap}, arrays {@link List}, strings
 * {@link String}, integers {@link Long} (no {@code .}/{@code e}/{@code E}) and
 * reals {@link Double}.
 */
public final class Json {
    private Json() {}

    public static final class JsonException extends RuntimeException {
        public JsonException(String message) {
            super(message);
        }
    }

    public static Object parse(String text) {
        Parser parser = new Parser(text);
        parser.skip();
        Object value = parser.value();
        parser.skip();
        if (parser.i < parser.len) {
            throw new JsonException("trailing data at offset " + parser.i);
        }
        return value;
    }

    /**
     * Structural equality: maps compare without regard to key order, and Long
     * and Double are different types, matching Python's int/float distinction.
     */
    public static boolean deepEquals(Object a, Object b) {
        if (a == null || b == null) {
            return a == b;
        }
        if (a instanceof Map && b instanceof Map) {
            Map<?, ?> left = (Map<?, ?>) a;
            Map<?, ?> right = (Map<?, ?>) b;
            if (left.size() != right.size()) {
                return false;
            }
            for (Map.Entry<?, ?> entry : left.entrySet()) {
                if (!right.containsKey(entry.getKey())) {
                    return false;
                }
                if (!deepEquals(entry.getValue(), right.get(entry.getKey()))) {
                    return false;
                }
            }
            return true;
        }
        if (a instanceof List && b instanceof List) {
            List<?> left = (List<?>) a;
            List<?> right = (List<?>) b;
            if (left.size() != right.size()) {
                return false;
            }
            for (int i = 0; i < left.size(); i++) {
                if (!deepEquals(left.get(i), right.get(i))) {
                    return false;
                }
            }
            return true;
        }
        // Long and Double are deliberately distinct, as Python separates int and float.
        if ((a instanceof Long && b instanceof Double) || (a instanceof Double && b instanceof Long)) {
            return false;
        }
        return a.equals(b);
    }

    public static String stringify(Object value) {
        StringBuilder out = new StringBuilder();
        write(value, out);
        return out.toString();
    }

    private static void write(Object value, StringBuilder out) {
        if (value == null) {
            out.append("null");
            return;
        }
        if (value instanceof String) {
            writeString((String) value, out);
            return;
        }
        if (value instanceof Boolean || value instanceof Long || value instanceof Integer || value instanceof Double) {
            out.append(value);
            return;
        }
        if (value instanceof Map) {
            out.append('{');
            boolean first = true;
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) value).entrySet()) {
                if (!first) {
                    out.append(',');
                }
                first = false;
                writeString(String.valueOf(entry.getKey()), out);
                out.append(':');
                write(entry.getValue(), out);
            }
            out.append('}');
            return;
        }
        if (value instanceof List) {
            out.append('[');
            boolean first = true;
            for (Object item : (List<?>) value) {
                if (!first) {
                    out.append(',');
                }
                first = false;
                write(item, out);
            }
            out.append(']');
            return;
        }
        throw new JsonException("cannot serialize " + value.getClass().getName());
    }

    private static void writeString(String text, StringBuilder out) {
        out.append('"');
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            switch (c) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                case '\b': out.append("\\b"); break;
                case '\f': out.append("\\f"); break;
                default:
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
            }
        }
        out.append('"');
    }

    private static final class Parser {
        private final String text;
        private final int len;
        private int i;

        Parser(String text) {
            this.text = text;
            this.len = text.length();
        }

        void skip() {
            while (i < len) {
                char c = text.charAt(i);
                if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
                    i++;
                } else {
                    break;
                }
            }
        }

        Object value() {
            if (i >= len) {
                throw new JsonException("unexpected end of input");
            }
            switch (text.charAt(i)) {
                case '{': return object();
                case '[': return array();
                case '"': return string();
                case 't': expect("true"); return Boolean.TRUE;
                case 'f': expect("false"); return Boolean.FALSE;
                case 'n': expect("null"); return null;
                default: return number();
            }
        }

        private void expect(String word) {
            if (!text.startsWith(word, i)) {
                throw new JsonException("invalid token at offset " + i);
            }
            i += word.length();
        }

        private Map<String, Object> object() {
            Map<String, Object> map = new LinkedHashMap<>();
            i++; // {
            skip();
            if (i < len && text.charAt(i) == '}') {
                i++;
                return map;
            }
            while (true) {
                skip();
                if (i >= len || text.charAt(i) != '"') {
                    throw new JsonException("expected object key at offset " + i);
                }
                String key = string();
                skip();
                if (i >= len || text.charAt(i) != ':') {
                    throw new JsonException("expected ':' at offset " + i);
                }
                i++;
                skip();
                map.put(key, value());
                skip();
                if (i >= len) {
                    throw new JsonException("unterminated object");
                }
                char c = text.charAt(i++);
                if (c == '}') {
                    return map;
                }
                if (c != ',') {
                    throw new JsonException("expected ',' or '}' at offset " + (i - 1));
                }
            }
        }

        private List<Object> array() {
            List<Object> list = new ArrayList<>();
            i++; // [
            skip();
            if (i < len && text.charAt(i) == ']') {
                i++;
                return list;
            }
            while (true) {
                skip();
                list.add(value());
                skip();
                if (i >= len) {
                    throw new JsonException("unterminated array");
                }
                char c = text.charAt(i++);
                if (c == ']') {
                    return list;
                }
                if (c != ',') {
                    throw new JsonException("expected ',' or ']' at offset " + (i - 1));
                }
            }
        }

        private String string() {
            StringBuilder out = new StringBuilder();
            i++; // opening quote
            while (true) {
                if (i >= len) {
                    throw new JsonException("unterminated string");
                }
                char c = text.charAt(i++);
                if (c == '"') {
                    return out.toString();
                }
                if (c != '\\') {
                    out.append(c);
                    continue;
                }
                if (i >= len) {
                    throw new JsonException("unterminated escape");
                }
                char escaped = text.charAt(i++);
                switch (escaped) {
                    case '"': out.append('"'); break;
                    case '\\': out.append('\\'); break;
                    case '/': out.append('/'); break;
                    case 'b': out.append('\b'); break;
                    case 'f': out.append('\f'); break;
                    case 'n': out.append('\n'); break;
                    case 'r': out.append('\r'); break;
                    case 't': out.append('\t'); break;
                    case 'u':
                        if (i + 4 > len) {
                            throw new JsonException("bad unicode escape");
                        }
                        out.append((char) Integer.parseInt(text.substring(i, i + 4), 16));
                        i += 4;
                        break;
                    default:
                        throw new JsonException("bad escape \\" + escaped);
                }
            }
        }

        private Object number() {
            int start = i;
            if (i < len && (text.charAt(i) == '-' || text.charAt(i) == '+')) {
                i++;
            }
            boolean isFloat = false;
            while (i < len) {
                char c = text.charAt(i);
                if (c >= '0' && c <= '9') {
                    i++;
                } else if (c == '.' || c == 'e' || c == 'E') {
                    isFloat = true;
                    i++;
                } else if ((c == '-' || c == '+')
                        && i > start
                        && (text.charAt(i - 1) == 'e' || text.charAt(i - 1) == 'E')) {
                    i++;
                } else {
                    break;
                }
            }
            String token = text.substring(start, i);
            if (token.isEmpty()) {
                throw new JsonException("invalid number at offset " + start);
            }
            if (isFloat) {
                return Double.parseDouble(token);
            }
            try {
                return Long.parseLong(token);
            } catch (NumberFormatException error) {
                return Double.parseDouble(token);
            }
        }
    }
}
