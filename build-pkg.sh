#!/usr/bin/env bash
# =============================================================================
#  Maze Cloak — local Arch package builder
#
#  Builds maze-cloak-<version>-<rel>-<arch>.pkg.tar.zst straight from the
#  current working tree (uncommitted changes included), using packaging/PKGBUILD.
#  The package version is read from mazecloak/__init__.py so it always matches
#  the code being built.
#
#  Building needs no privileges and this script asks for none: it runs makepkg
#  and stops. Installing is a separate, explicit step you run yourself — the
#  command is printed at the end.
#
#  Usage:
#    ./build-pkg.sh              build the package into ./dist-pkg/
#    ./build-pkg.sh --clean      remove ./dist-pkg/ and exit
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_SRC="$ROOT/packaging"
OUT="$ROOT/dist-pkg"

if [[ -t 1 ]]; then
  GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'
else
  GREEN=''; BLUE=''; YELLOW=''; RED=''; RESET=''
fi
info() { echo -e "${BLUE}[*]${RESET} $*"; }
ok()   { echo -e "${GREEN}[✓]${RESET} $*"; }
warn() { echo -e "${YELLOW}[!]${RESET} $*"; }
die()  { echo -e "${RED}[✗]${RESET} $*" >&2; exit 1; }

for arg in "$@"; do
  case "$arg" in
    --clean)   rm -rf "$OUT"; ok "Removed $OUT"; exit 0 ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^#\s\?//'; exit 0 ;;
    *)         die "Unknown option: $arg" ;;
  esac
done

command -v makepkg >/dev/null 2>&1 || die "makepkg not found — run this on Arch (pacman)."
[[ -f "$PKG_SRC/PKGBUILD" ]] || die "Missing $PKG_SRC/PKGBUILD"

# ── Version comes from the source of truth ────────────────────────────────────
VER="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/mazecloak/__init__.py")"
[[ -n "$VER" ]] || die "Could not read __version__ from mazecloak/__init__.py"
info "Building maze-cloak ${VER} from working tree"

# ── Run the test suite first ──────────────────────────────────────────────────
# The suite blocks every subprocess, so this cannot touch the machine or raise
# an authentication prompt — see the note at the top of tests/test_core.py.
if [[ -f "$ROOT/tests/test_core.py" ]]; then
  info "Running tests ..."
  if python3 "$ROOT/tests/test_core.py" >/tmp/maze-cloak-tests.log 2>&1; then
    ok "$(grep -c '\.\.\. ok' /tmp/maze-cloak-tests.log) tests passed"
  else
    tail -30 /tmp/maze-cloak-tests.log
    die "Tests failed — see /tmp/maze-cloak-tests.log"
  fi
fi

# ── Fresh build directory ─────────────────────────────────────────────────────
BUILD="$OUT/build"
rm -rf "$BUILD"
mkdir -p "$BUILD"

# ── Stage the source tree that goes into the tarball ──────────────────────────
STAGE="$OUT/stage/maze-cloak-${VER}"
rm -rf "$OUT/stage"
mkdir -p "$STAGE"
cp -r "$ROOT/mazecloak" "$STAGE/"
find "$STAGE/mazecloak" -name __pycache__ -type d -prune -exec rm -rf {} +
find "$STAGE/mazecloak" -name '*.pyc' -delete
for f in main.py pyproject.toml requirements.txt MAZE-CLOAK.png MAZE-CLOAK-TRAY.png maze-cloak-tray.svg LICENSE README.md; do
  if [[ -f "$ROOT/$f" ]]; then cp "$ROOT/$f" "$STAGE/"; else warn "skipping missing $f"; fi
done

# The polkit rule is not optional: without it, every Start/Stop click in the app
# raises a password dialog.
[[ -f "$PKG_SRC/49-maze-cloak.rules" ]] \
  && cp "$PKG_SRC/49-maze-cloak.rules" "$STAGE/" \
  || die "Missing $PKG_SRC/49-maze-cloak.rules"

info "Creating source tarball"
tar czf "$BUILD/maze-cloak-${VER}.tar.gz" -C "$OUT/stage" "maze-cloak-${VER}"
rm -rf "$OUT/stage"

# ── Assemble the makepkg working dir ──────────────────────────────────────────
cp "$PKG_SRC/PKGBUILD" "$PKG_SRC/maze-cloak.install" "$BUILD/"
# Pin pkgver to the version we just built (leaves packaging/PKGBUILD untouched).
sed -i "s/^pkgver=.*/pkgver=${VER}/" "$BUILD/PKGBUILD"

info "Running makepkg ..."
( cd "$BUILD" && makepkg -f --noconfirm --nodeps )

PKG="$(find "$BUILD" -maxdepth 1 -name '*.pkg.tar.zst' -print -quit)"
[[ -n "$PKG" ]] || die "makepkg finished but produced no .pkg.tar.zst"
mv -f "$PKG" "$OUT/"
FINAL="$OUT/$(basename "$PKG")"
mv -f "$BUILD/maze-cloak-${VER}.tar.gz" "$OUT/"
rm -rf "$BUILD"

ok "Package ready: $FINAL"
echo "    Source:  $OUT/maze-cloak-${VER}.tar.gz"
echo
echo "  To install (this script does not do it for you):"
echo "    sudo pacman -U \"$FINAL\""
echo
echo "  After installing, log out and back in once so your new 'maze' group"
echo "  membership applies, then start the daemon from the app or with:"
echo "    sudo systemctl enable --now maze-cloak.service"
