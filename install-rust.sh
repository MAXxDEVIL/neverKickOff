#!/bin/sh
# neverKickOff compiled-binary installer for macOS and Linux.
#
#   curl -fsSL https://raw.githubusercontent.com/MAXxDEVIL/neverKickOff/main/install-rust.sh | sh
#
# Downloads the prebuilt binary for this OS and CPU from the latest GitHub
# release, checks its SHA-256, installs it into ~/.local/bin, and *prints* -
# never runs - the sudo commands for the system bits it cannot install itself.
#
# Env:
#   NKO_VERSION=v1.0.0     install that release instead of the latest
#   NKO_BASE_URL=<url>     download from somewhere else (used by the tests)
set -eu

REPO="MAXxDEVIL/neverKickOff"
BIN="$HOME/.local/bin"
LAUNCHER="$BIN/neverkickoff"

say() { printf '%s\n' "$*"; }
die() { printf 'install: %s\n' "$*" >&2; exit 1; }

[ -n "${HOME:-}" ] || die "HOME is not set."

# --- 1. which build does this machine need -----------------------------------
case "$(uname -s)" in
    Linux)  os_part="unknown-linux-gnu" ;;
    Darwin) os_part="apple-darwin" ;;
    *) die "unsupported OS '$(uname -s)'. On Windows use install-rust.ps1." ;;
esac

case "$(uname -m)" in
    x86_64|amd64)   arch_part="x86_64" ;;
    arm64|aarch64)  arch_part="aarch64" ;;
    *) die "unsupported CPU '$(uname -m)' (only x86_64 and arm64 builds are published)." ;;
esac

target="$arch_part-$os_part"
asset="neverkickoff-$target.tar.gz"

# /releases/latest/download/ is a redirect, so no API call and no rate limit.
if [ -n "${NKO_VERSION:-}" ]; then
    base="https://github.com/$REPO/releases/download/$NKO_VERSION"
else
    base="https://github.com/$REPO/releases/latest/download"
fi
base="${NKO_BASE_URL:-$base}"

command -v curl >/dev/null 2>&1 || die "curl is required."
command -v tar >/dev/null 2>&1 || die "tar is required."

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM

say "platform : $target"
say "download : $base/$asset"
curl -fsSL "$base/$asset" -o "$TMP/$asset" \
    || die "download failed - is there a release with a $target build yet?
         Nothing is published until a v* tag is pushed; see .github/workflows/release.yml."
curl -fsSL "$base/SHA256SUMS" -o "$TMP/SHA256SUMS" \
    || die "could not download SHA256SUMS."

# --- 2. verify the download --------------------------------------------------
# macOS ships shasum, not sha256sum.
if command -v sha256sum >/dev/null 2>&1; then
    sum() { sha256sum "$1" | awk '{print $1}'; }
else
    sum() { shasum -a 256 "$1" | awk '{print $1}'; }
fi

expected=$(awk -v f="$asset" '$2 == f { print $1 }' "$TMP/SHA256SUMS")
[ -n "$expected" ] || die "SHA256SUMS has no entry for $asset."
actual=$(sum "$TMP/$asset")
[ "$expected" = "$actual" ] || die "checksum mismatch for $asset."
say "checksum : ok"

# --- 3. install --------------------------------------------------------------
mkdir -p "$TMP/x"
tar xzf "$TMP/$asset" -C "$TMP/x" || die "could not unpack $asset."
src="$TMP/x/neverkickoff-$target/neverkickoff"
[ -f "$src" ] || die "unexpected archive layout (no neverkickoff binary)."

mkdir -p "$BIN"
if [ -f "$LAUNCHER" ] && [ "$(head -c 2 "$LAUNCHER" 2>/dev/null)" = "#!" ]; then
    say "note     : replacing the existing script at $LAUNCHER with the binary."
fi
if command -v install >/dev/null 2>&1; then
    install -m 0755 "$src" "$LAUNCHER"
else
    cp "$src" "$LAUNCHER" && chmod 0755 "$LAUNCHER"
fi

# With no path argument the app reads config.json from next to the executable,
# so the default ships beside it - but never clobber a config you have edited.
if [ ! -e "$BIN/config.json" ] && [ -f "$TMP/x/neverkickoff-$target/config.json" ]; then
    cp "$TMP/x/neverkickoff-$target/config.json" "$BIN/config.json"
fi

version=$("$LAUNCHER" --version 2>/dev/null) || die "the installed binary would not run."
say "installed: $LAUNCHER ($version)"

# --- 4. what is still missing (printed, never run) ---------------------------
MISSING=""

if [ "$os_part" = "unknown-linux-gnu" ]; then
    if ! ldconfig -p 2>/dev/null | grep -q 'libXtst\.so'; then
        if command -v pacman >/dev/null 2>&1; then
            MISSING="$MISSING
  libXtst : sudo pacman -S libxtst"
        elif command -v apt >/dev/null 2>&1; then
            MISSING="$MISSING
  libXtst : sudo apt install libxtst6"
        elif command -v dnf >/dev/null 2>&1; then
            MISSING="$MISSING
  libXtst : sudo dnf install libXtst"
        else
            MISSING="$MISSING
  libXtst : install the X11 XTest library for your distro"
        fi
    fi
    if [ "${XDG_SESSION_TYPE:-}" = "wayland" ] && ! command -v ydotool >/dev/null 2>&1; then
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
else
    MISSING="$MISSING
  macOS   : allow Accessibility AND Input Monitoring for your terminal
            (System Settings -> Privacy & Security), or clicks and hotkeys do nothing."
fi

# --- 5. report ---------------------------------------------------------------
say ""
say "neverKickOff installed."
say "  binary : $LAUNCHER"
say "  config : $BIN/config.json"
say "  run    : neverkickoff                 (with no argument it uses that config)"

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
