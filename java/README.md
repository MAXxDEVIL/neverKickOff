# neverKickOff - Java port

A JDK-only port of the Python auto clicker. The Python version is the source of
truth; behaviour is pinned by `../tests/fixtures/contract.json`, which Python
generates and this port reproduces exactly. It mirrors the working Rust port in
`../rust/`.

    java/build.sh          build everything (javac + jar, no build tool)
    java/build.sh test     build and run the cross-language contract test

Requires a JDK (tested on JDK 27, compiled with `--release 21`). No Maven, no
Gradle, no third-party jars required.

## Layout

```
src/neverkickoff/*.java   the port, one class per Rust/Java-spec module
tests/ContractTest.java   reads ../tests/fixtures/contract.json, checks every section
build.sh                  javac + jar
lib/jnativehook-2.2.2.jar optional: real global hotkeys
dist/neverkickoff.jar     build output (main class neverkickoff.Main)
```

`Json`, `Key`, `Keys`, `Hotkeys`, `Spec`, `Device`, `Engine`, `Ydotool`,
`Window`, `Clicker`, `Main` mirror the Rust modules. `RobotDevice` is the
X11/XWayland input device (the role pynput's `Controller` plays); `Ydotool`
covers Wayland.

## Run

    java -jar dist/neverkickoff.jar ../config.json
    java -jar dist/neverkickoff.jar ../config.json --tray

The output matches the Python version:

    warning: Wayland ignores pynput's input: install ydotool and start ydotoold (see the Wayland section of README.md)
    ready - <ctrl>+<alt>+s start/stop, <esc> panic-stop

## Global hotkeys

`lib/jnativehook-2.2.2.jar` (JNativeHook 2.2.2, from Maven Central) enables real
global hotkeys. It is not committed and nothing fetches it for you, so download it
first (`java/lib/` is git-ignored):

    mkdir -p lib && curl -fL -o lib/jnativehook-2.2.2.jar \
      https://repo1.maven.org/maven2/com/github/kwhat/jnativehook/2.2.2/jnativehook-2.2.2.jar

Expected SHA-256: `2c7904423bc680af02d9ea9557ae233c35199e302d072773a9d0304b568acd41`

The jar built by `build.sh` does not embed it, so to get real hotkeys put it on the
classpath yourself:

    java -cp "dist/neverkickoff.jar:lib/jnativehook-2.2.2.jar" neverkickoff.Main ../config.json

On JDK 24+ the native load prints a warning; silence it with
`--enable-native-access=ALL-UNNAMED`. `Main` loads the backend by reflection, so
if JNativeHook is absent it prints

    cannot watch for hotkeys: JNativeHook is not on the classpath (see java/README.md)

and exits non-zero after the `warning:`/`ready` lines. Everything else - the
contract test, the engine, the ydotool and Robot devices - works without it.

## Known gaps

- **Tray**: no tray backend. `--tray` prints
  `tray unavailable (no tray backend in this build); running without it`, like
  the Rust build, and keeps running.
- **Focused-window title**: X11 only, via `xdotool` (a JDK-only build cannot use
  python-xlib). On Wayland it returns null, so a `window` filter never matches.
  Windows/macOS titles are not read.
- **Hotkey key names**: a few JNativeHook virtual-key names are mapped by hand;
  exotic keys a combo might name can be refused with "hotkey key not supported".
