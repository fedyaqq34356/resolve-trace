#!/usr/bin/env sh
set -eu

REPO_URL="https://github.com/fedyaqq34356/resolve-trace"
NAME="resolve-trace"
BIN="rt"

red()  { printf '\033[31m%s\033[0m\n' "$1"; }
grn()  { printf '\033[32m%s\033[0m\n' "$1"; }
ylw()  { printf '\033[33m%s\033[0m\n' "$1"; }

command -v python3 >/dev/null 2>&1 || { red "python3 not found. Install Python 3.8+ and retry."; exit 1; }

PYVER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 8) else 1)' \
    || { red "Python $PYVER too old, need 3.8+."; exit 1; }
grn "python3 $PYVER ok"

if [ -f "$(dirname "$0")/$BIN" ]; then
    SRC=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
else
    DEST_REPO="${XDG_DATA_HOME:-$HOME/.local/share}/$NAME"
    if [ -d "$DEST_REPO/.git" ]; then
        ylw "updating existing checkout in $DEST_REPO"
        git -C "$DEST_REPO" pull --ff-only
    else
        command -v git >/dev/null 2>&1 || { red "git not found. Install git or download the repo manually."; exit 1; }
        ylw "cloning into $DEST_REPO"
        git clone --depth 1 "$REPO_URL" "$DEST_REPO"
    fi
    SRC="$DEST_REPO"
fi

chmod +x "$SRC/$BIN"

BINDIR="$HOME/.local/bin"
mkdir -p "$BINDIR"
ln -sf "$SRC/$BIN" "$BINDIR/$BIN"
grn "linked $BINDIR/$BIN -> $SRC/$BIN"

case ":$PATH:" in
    *":$BINDIR:"*) grn "done. run: $BIN pacman" ;;
    *)
        ylw "$BINDIR is not on PATH yet."
        echo "add this to your shell rc (~/.zshrc or ~/.bashrc):"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo "then reopen the shell and run: $BIN pacman"
        ;;
esac
