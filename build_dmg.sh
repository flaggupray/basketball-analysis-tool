#!/usr/bin/env bash
# Build Basketball Analyzer DMG for macOS
# Prerequisites: pip install pyinstaller
#                Python 3.10+ with Tkinter

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

APP_NAME="Basketball Analyzer"
DMG_NAME="BasketballAnalyzer"
VERSION="${VERSION:-1.0.0}"

echo "=========================================="
echo "  Building ${APP_NAME} v${VERSION}"
echo "=========================================="

# ── 1. Generate icon (if needed) ──────────────────────────────
ICON_DIR="build_assets/icons"
ICON_ICNS="${ICON_DIR}/icon.icns"

if [ ! -f "$ICON_ICNS" ]; then
    echo ""
    echo "[1/5] Generating app icon..."
    python3 build_assets/generate_icon.py
    cp assets/icon_*.png "$ICON_DIR/" 2>/dev/null || true

    ICONSET="${ICON_DIR}/icon.iconset"
    mkdir -p "$ICONSET"
    for sz in 16 32 64 128 256 512; do
        cp "${ICON_DIR}/icon_${sz}x${sz}.png" "$ICONSET/icon_${sz}x${sz}.png"
        sz2=$((sz * 2))
        if [ -f "${ICON_DIR}/icon_${sz2}x${sz2}.png" ]; then
            cp "${ICON_DIR}/icon_${sz2}x${sz2}.png" "$ICONSET/icon_${sz}x${sz}@2x.png"
        fi
    done
    iconutil -c icns "$ICONSET" -o "$ICON_ICNS"
    rm -rf "$ICONSET"
    echo "  ✓ icon.icns created"
else
    echo ""
    echo "[1/5] Using existing icon: $ICON_ICNS"
fi

# ── 2. Build .app with PyInstaller ────────────────────────────
echo ""
echo "[2/5] Building .app with PyInstaller..."
export PATH="$HOME/Library/Python/3.11/bin:$PATH"
pyinstaller --clean --noconfirm build_assets/gui.spec 2>&1 | tail -10
echo "  ✓ .app built in dist/"

# ── 3. Verify .app exists ─────────────────────────────────────
APP_PATH="dist/${APP_NAME}.app"
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: .app not found at $APP_PATH"
    exit 1
fi

# ── 4. Create DMG ─────────────────────────────────────────────
echo ""
echo "[3/5] Creating DMG..."
DMG_FILE="dist/${DMG_NAME}-${VERSION}.dmg"
TMP_DMG="dist/${DMG_NAME}-tmp.dmg"

# Remove old DMGs
rm -f "$DMG_FILE" "$TMP_DMG"

# Create a temporary directory for DMG contents
DMG_SRC="dist/dmg_src"
rm -rf "$DMG_SRC"
mkdir -p "$DMG_SRC"

# Copy .app
cp -R "$APP_PATH" "$DMG_SRC/"

# Create Applications symlink
ln -s /Applications "$DMG_SRC/Applications"

# Create readme in DMG
cat > "$DMG_SRC/README.txt" << 'DMGREADME'
Basketball Inability Analyzer

To install:
  Drag "Basketball Analyzer" into the Applications folder.

After installation, launch from:
  /Applications/Basketball Analyzer.app

First launch may require:
  Right-click → Open (to bypass Gatekeeper for unsigned apps)
DMGREADME

# Create the uncompressed DMG
hdiutil create -volname "${APP_NAME}" \
    -srcfolder "$DMG_SRC" \
    -ov -format UDRW \
    "$TMP_DMG" > /dev/null

# Mount it
DEVICE=$(hdiutil attach -readwrite -noverify -noautoopen "$TMP_DMG" | \
         egrep '^/dev/' | sed 1q | awk '{print $1}')
MOUNT_POINT="/Volumes/${APP_NAME}"

# Set DMG window layout via AppleScript
echo "  Arranging DMG window..."
osascript << ENDOSA
tell application "Finder"
    tell disk "${APP_NAME}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {200, 200, 700, 500}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 96
        set position of item "${APP_NAME}.app" of container window to {120, 140}
        set position of item "Applications" of container window to {380, 140}
        set position of item "README.txt" of container window to {250, 40}
        close
        open
        update without registering applications
        delay 1
    end tell
end tell
ENDOSA

# Unmount
hdiutil detach "$DEVICE" -force > /dev/null

# Convert to compressed read-only DMG
hdiutil convert "$TMP_DMG" -format UDZO -imagekey zlib-level=9 -o "$DMG_FILE" > /dev/null

# Cleanup
rm -f "$TMP_DMG"
rm -rf "$DMG_SRC"

echo "  ✓ DMG created: $DMG_FILE"

# ── 4. Verify ─────────────────────────────────────────────────
echo ""
echo "[4/5] Verifying..."
hdiutil verify "$DMG_FILE" > /dev/null 2>&1 && echo "  ✓ DMG verified OK" || echo "  ⚠ Verification had issues (DMG may still work)"

# ── 5. Summary ────────────────────────────────────────────────
echo ""
echo "[5/5] Done!"
echo ""
echo "  App:  $(du -sh "$APP_PATH" | awk '{print $1}')  →  $APP_PATH"
echo "  DMG:  $(du -sh "$DMG_FILE" | awk '{print $1}')  →  $DMG_FILE"
echo ""
echo "To install: open $DMG_FILE and drag to Applications"
echo "To also notarize (optional): xcrun notarytool submit ..."
