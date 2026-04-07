#!/usr/bin/env bash
# Build Audiobook Maker.app + DMG for macOS distribution
# Prerequisites: pip install pyinstaller; brew install create-dmg

set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="Audiobook Maker"
BUNDLE_ID="com.audiobook.maker"
VERSION="1.0.0"

echo "==> Cleaning previous build…"
rm -rf build dist

echo "==> Running PyInstaller…"
pyinstaller \
  --windowed \
  --onedir \
  --name "$APP_NAME" \
  --add-data "converter.py:." \
  --osx-bundle-identifier "$BUNDLE_ID" \
  app.py

echo "==> Signing ad-hoc (no Apple Developer account required)…"
codesign --deep --force --sign - "dist/${APP_NAME}.app" || true

echo "==> Creating DMG…"
# create-dmg install: brew install create-dmg
create-dmg \
  --volname "$APP_NAME $VERSION" \
  --volicon "" \
  --window-pos 200 120 \
  --window-size 500 320 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 120 150 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 380 150 \
  "dist/${APP_NAME}-${VERSION}.dmg" \
  "dist/${APP_NAME}.app" \
  || {
    # Fallback: plain zip if create-dmg is not installed
    echo "  create-dmg not found, falling back to zip…"
    cd dist
    zip -r "${APP_NAME}-${VERSION}.zip" "${APP_NAME}.app"
    cd ..
    echo "  Packaged as dist/${APP_NAME}-${VERSION}.zip"
  }

echo ""
echo "✅  Build complete!"
ls dist/
