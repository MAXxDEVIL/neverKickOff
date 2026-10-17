#!/bin/sh
# neverKickOff installer for macOS and Linux.
#
#   curl -fsSL https://raw.githubusercontent.com/MAXxDEVIL/neverKickOff/main/install.sh | sh
#
# Installs to $XDG_DATA_HOME/neverKickOff (default ~/.local/share/neverKickOff),
# links a `neverkickoff` command into ~/.local/bin, and *prints* - never runs -
# the sudo commands for the system packages it cannot install itself.
set -eu

REPO="https://github.com/MAXxDEVIL/neverKickOff"

say() { printf '%s\n' "$*"; }
die() { printf 'install: %s\n' "$*" >&2; exit 1; }

[ -n "${HOME:-}" ] || die "HOME is not set."

DIR="${XDG_DATA_HOME:-$HOME/.local/share}/neverKickOff"
BIN="$HOME/.local/bin"
LAUNCHER="$BIN/neverkickoff"

# --- 1. a usable python ------------------------------------------------------
PY=""
for candidate in python3 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null || continue
    PY=$(command -v "$candidate")
    break
done
[ -n "$PY" ] || die "no Python 3.8+ found. Install one, then re-run."
say "python   : $PY ($("$PY" -V 2>&1))"

# --- 2. download the source (git not required) -------------------------------
command -v curl >/dev/null 2>&1 || die "curl is required."
command -v tar >/dev/null 2>&1 || die "tar is required."

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM

say "download : $REPO"
curl -fsSL "$REPO/archive/refs/heads/main.tar.gz" | tar xz -C "$TMP" \
    || die "download failed."

SRC="$TMP/neverKickOff-main"
[ -f "$SRC/gui.py" ] || die "unexpected archive layout (no gui.py)."

# Copying over an existing install leaves .venv alone, so re-running is an upgrade.
mkdir -p "$DIR"
cp -R "$SRC/." "$DIR/"

# --- 3. virtualenv + dependencies -------------------------------------------
if [ ! -x "$DIR/.venv/bin/python" ]; then
    say "venv     : creating"
    if ! "$PY" -m venv "$DIR/.venv"; then
        rm -rf "$DIR/.venv"
        die "could not create a venv. On Debian/Ubuntu: sudo apt install python3-venv"
    fi
fi

say "deps     : installing"
"$DIR/.venv/bin/python" -m pip install --disable-pip-version-check \
    -r "$DIR/requirements.txt" -r "$DIR/requirements-tray.txt" \
    || die "pip install failed."

# --- 4. launcher -------------------------------------------------------------
mkdir -p "$BIN"
cat > "$LAUNCHER" <<EOF
#!/bin/sh
exec "$DIR/.venv/bin/python" "$DIR/gui.py" "\$@"
EOF
chmod +x "$LAUNCHER"

# --- 5. what is still missing (printed, never run) ---------------------------
MISSING=""

if ! "$DIR/.venv/bin/python" -c 'import tkinter' 2>/dev/null; then
    if command -v pacman >/dev/null 2>&1; then
        MISSING="$MISSING
  tkinter : sudo pacman -S tk"
    elif command -v apt >/dev/null 2>&1; then
        MISSING="$MISSING
  tkinter : sudo apt install python3-tk"
    elif command -v dnf >/dev/null 2>&1; then
        MISSING="$MISSING
  tkinter : sudo dnf install python3-tkinter"
    else
        MISSING="$MISSING
  tkinter : install the Tk bindings for your distro's Python"
    fi
fi

if [ "$(uname -s)" = "Darwin" ]; then
    MISSING="$MISSING
  macOS   : allow Accessibility AND Input Monitoring for your terminal/Python
            (System Settings -> Privacy & Security), or clicks and hotkeys do nothing."
elif [ "${XDG_SESSION_TYPE:-}" = "wayland" ] && ! command -v ydotool >/dev/null 2>&1; then
    if command -v pacman >/dev/null 2>&1; then
        MISSING="$MISSING
  wayland : sudo pacman -S ydotool && systemctl --user enable --now ydotool"
    elif command -v apt >/dev/null 2>&1; then
        MISSING="$MISSING
  wayland : sudo apt install ydotool && systemctl --user enable --now ydotool"
    elif command -v dnf >/dev/null 2>&1; then
        MISSING="$MISSING
  wayland : sudo dnf install ydotool && systemctl --user enable --now ydotool"
    fi
fi

# --- 6. report ---------------------------------------------------------------
say ""
say "neverKickOff installed."
say "  source : $DIR"
say "  run    : neverkickoff          (opens the GUI)"
say "  verify : $DIR/.venv/bin/python $DIR/test_engine.py"

case ":${PATH:-}:" in
    *":$BIN:"*) ;;
    *)
        say ""
        say "$BIN is not on your PATH. Add it:"
        say "  sh / bash : echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        say "  zsh       : echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
        say "  fish      : fish_add_path ~/.local/bin"
        ;;
esac

if [ -n "$MISSING" ]; then
    say ""
    say "Still needed - run these yourself:"
    say "$MISSING"
fi
