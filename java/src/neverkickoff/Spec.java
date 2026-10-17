package neverkickoff;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Spec loading - the Java half of {@code main.load_spec} and
 * {@code engine.normalize_steps}. Specs stay plain JSON trees rather than typed
 * objects on purpose: Python copies dicts and only touches {@code keys}, so any
 * extra key in a user's config has to survive untouched.
 */
public final class Spec {
    private Spec() {}

    /** Python truthiness, which decides whether {@code steps} or {@code keys} is "present". */
    public static boolean truthy(Object value) {
        if (value == null) {
            return false;
        }
        if (value instanceof Boolean) {
            return (Boolean) value;
        }
        if (value instanceof Number) {
            return ((Number) value).doubleValue() != 0.0;
        }
        if (value instanceof String) {
            return !((String) value).isEmpty();
        }
        if (value instanceof List) {
            return !((List<?>) value).isEmpty();
        }
        if (value instanceof Map) {
            return !((Map<?, ?>) value).isEmpty();
        }
        return true;
    }

    /**
     * {@code engine.normalize_steps}: a flat spec becomes one implicit step.
     *
     * Explicit steps are returned verbatim, exactly as Python returns the
     * caller's own dicts, so per-field defaults are applied later at use time.
     */
    public static List<Object> normalizeSteps(Object specValue) {
        Map<String, Object> spec = asMap(specValue);
        Object steps = spec.get("steps");
        if (truthy(steps) && steps instanceof List) {
            return new ArrayList<>((List<?>) steps);
        }
        Map<String, Object> step = new LinkedHashMap<>();
        step.put("action", spec.containsKey("action") ? spec.get("action") : "mouse");
        step.put("button", spec.containsKey("button") ? spec.get("button") : "left");
        Object keys = spec.get("keys");
        step.put("keys", truthy(keys) ? keys : new ArrayList<>());
        step.put("count", 1L);
        step.put("hold", spec.containsKey("hold") ? spec.get("hold") : 0.0);
        step.put("wait", 0.0);
        List<Object> out = new ArrayList<>(1);
        out.add(step);
        return out;
    }

    /** {@code main.load_spec}: copy a config's click spec, parsing every key combo. */
    public static Object loadSpec(Object click) {
        Map<String, Object> spec = new LinkedHashMap<>(asMap(click));
        Object steps = spec.get("steps");
        if (truthy(steps)) {
            List<Object> parsed = new ArrayList<>();
            if (steps instanceof List) {
                for (Object rawStep : (List<?>) steps) {
                    Map<String, Object> step = new LinkedHashMap<>(asMap(rawStep));
                    if ("keys".equals(step.get("action"))) {
                        Object combo = step.containsKey("keys") ? step.get("keys") : new ArrayList<>();
                        step.put("keys", Keys.parseComboToJson(combo));
                    }
                    parsed.add(step);
                }
            }
            spec.put("steps", parsed);
        } else if ("keys".equals(spec.get("action"))) {
            Object combo = spec.containsKey("keys") ? spec.get("keys") : new ArrayList<>();
            spec.put("keys", Keys.parseComboToJson(combo));
        }
        return spec;
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> asMap(Object value) {
        if (value instanceof Map) {
            return (Map<String, Object>) value;
        }
        return new LinkedHashMap<>();
    }
}
