# Compatibility matrix

How much of the Python implementation each port reproduces, and how that is
proven. Nothing here is "compatible" unless a test in
[TEST_PLAN.md](TEST_PLAN.md) says so.

## Feature compatibility

| Behaviour | Python | Rust | Java | Evidence |
|-----------|:------:|:----:|:----:|----------|
| Macro timing loop | ✅ | ✅ | ✅ | `contract.json` `engine` cases + timing tests |
| Flat spec → implicit step | ✅ | ✅ | ✅ | `contract.json` `normalize_steps` |
| Config spec loading | ✅ | ✅ | ✅ | `contract.json` `load_spec` |
| Key combo parsing | ✅ | ✅ | ✅ | `contract.json` `parse_combo` |
| Combo error message | ✅ | ✅ | ✅ | `contract.json` `parse_combo[].error` |
| Hotkey capture formatting | ✅ | ✅ | ✅ | `contract.json` `format_hotkey` |
| Linux keycode mapping | ✅ | ✅ | ✅ | `contract.json` `keycode` |
| Focused-title normalisation | ✅ | ✅ | ✅ | `contract.json` `as_text` |
| ydotool injection (Wayland) | ✅ | ✅ | ✅ | Shells out; parity by construction, `available`/`problem` ported |
| XTest injection (X11) | ✅ | ✅ | ✅ | pynput ↔ rdev ↔ `java.awt.Robot`, all XTest |
| Global hotkeys | ✅ | ✅ | ✅ | pynput ↔ rdev ↔ JNativeHook |
| Toggle/stop controller | ✅ | ✅ | ✅ | Ported; CLI parity checked |
| CLI stdout contract | ✅ | ✅ | ✅ | Compared against `python -u main.py config.json` |
| Window filter on X11 | ✅ | ⚠️ | ⚠️ | Rust needs `xdotool` on PATH; Java needs `xdotool` |
| Window filter on Wayland | ❌ | ❌ | ❌ | Compositor limitation, same in all three |
| Jitter (statistical) | ✅ | ✅ | ✅ | Per-language test, not a byte-exact fixture |
| Duration limit | ✅ | ✅ | ✅ | Per-language timing test |
| Stop mid-hold releases keys | ✅ | ✅ | ✅ | Per-language timing test |
| Tray icon | ✅ | ❌ | ❌ | Not ported (see report) |
| Six-tab GUI | ✅ | ❌ | ❌ | Not ported (see report) |

Legend: ✅ done and tested · ⚠️ works but with a documented platform gap ·
❌ not implemented or not possible.

## Platform reach

| Session | Python | Rust | Java | Notes |
|---------|:------:|:----:|:----:|-------|
| Wayland, ydotool installed | ✅ | ✅ | ✅ | The only combination that injects on Wayland |
| Wayland, no ydotool | ❌ | ❌ | ❌ | Warns and does not click; identical in all three |
| X11 | ✅ | ✅ | ✅ | XTest in every case |
| Windows | ✅ | ✅ | ✅ | Ported; not exercised on this machine |
| macOS | ✅ | ✅ | ✅ | Ported; not exercised on this machine |

`java.awt.Robot`, rdev and pynput all reach X11 through XTest, so they share the
same Wayland limitation. That is parity, not a regression.

## Behavioural differences that are accepted

See the two tables at the end of [FUNCTIONALITY_MAP.md](FUNCTIONALITY_MAP.md).
In short: traceback text, the `keycode` error string, and the tray fallback
message differ; nothing the user can observe from a successful run does.

## Not yet verified

| Item | Rust | Java | Why |
|------|:----:|:----:|-----|
| Injection against real hardware | ❌ | ❌ | `ydotool` is not installed on this machine and the session is Wayland, so nothing can actually click here |
| Global hotkeys on Wayland | ❌ | ❌ | rdev and JNativeHook both go through X11 |
| Tray, GUI | ❌ | ❌ | Not written |
| Windows / macOS behaviour | ❌ | ❌ | No such machine available |
