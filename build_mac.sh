#!/usr/bin/env bash
set -euo pipefail

# Build + optional sign/notarize + package script for MigrationDashboard (macOS)
# Usage examples:
#   ./build_mac.sh
#   APP_NAME="MigrationDashboard" ./build_mac.sh
#   SIGN_APP=1 DEVELOPER_ID="Developer ID Application: Example Corp (TEAMID)" ./build_mac.sh
#   SIGN_APP=1 NOTARIZE=1 DEVELOPER_ID="Developer ID Application: Example Corp (TEAMID)" \
#     APPLE_ID="you@example.com" TEAM_ID="TEAMID" APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" ./build_mac.sh

APP_NAME="${APP_NAME:-MigrationDashboard}"
ENTRYPOINT="${ENTRYPOINT:-run_dashboard.py}"
SIGN_APP="${SIGN_APP:-0}"
NOTARIZE="${NOTARIZE:-0}"
DEVELOPER_ID="${DEVELOPER_ID:-}"
APPLE_ID="${APPLE_ID:-}"
TEAM_ID="${TEAM_ID:-}"
APP_PASSWORD="${APP_PASSWORD:-}"
TIMESTAMP_URL="${TIMESTAMP_URL:-http://timestamp.apple.com/ts01}"

RELEASE_DIR="release/${APP_NAME}-mac"
DIST_DIR="dist/${APP_NAME}"
APP_BUNDLE="${DIST_DIR}/${APP_NAME}.app"
ZIP_NAME="${APP_NAME}-mac.zip"

# Ensure script runs from repo root regardless of CWD
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f "$ENTRYPOINT" ]]; then
  echo "❌ Entrypoint not found: $ENTRYPOINT"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 is required but was not found in PATH"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "📦 Creating local virtual environment (.venv)..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "🧹 Cleaning previous build artifacts..."
rm -rf build dist "$RELEASE_DIR" "$ZIP_NAME"

echo "🏗️ Building portable onedir bundle with PyInstaller..."
pyinstaller "$ENTRYPOINT" \
  --name "$APP_NAME" \
  --onedir \
  --clean \
  --noconfirm \
  --add-data "app.py:." \
  --add-data "pages:pages" \
  --add-data "ui:ui" \
  --add-data "core:core" \
  --add-data "data_loaders:data_loaders" \
  --add-data "models:models" \
  --add-data "analytics:analytics" \
  --add-data "components:components" \
  --add-data "utils:utils" \
  --add-data "export:export" \
  --copy-metadata streamlit \
  --collect-all streamlit

if [[ "$SIGN_APP" == "1" ]]; then
  if [[ -z "$DEVELOPER_ID" ]]; then
    echo "❌ SIGN_APP=1 but DEVELOPER_ID is empty"
    exit 1
  fi
  echo "🔏 Signing app bundle..."
  codesign --deep --force --verify --verbose \
    --options runtime \
    --timestamp \
    --sign "$DEVELOPER_ID" \
    "$APP_BUNDLE"
fi

if [[ "$NOTARIZE" == "1" ]]; then
  if [[ "$SIGN_APP" != "1" ]]; then
    echo "❌ NOTARIZE=1 requires SIGN_APP=1"
    exit 1
  fi
  if [[ -z "$APPLE_ID" || -z "$TEAM_ID" || -z "$APP_PASSWORD" ]]; then
    echo "❌ NOTARIZE=1 requires APPLE_ID, TEAM_ID, and APP_PASSWORD"
    exit 1
  fi

  echo "📦 Creating zip for notarization..."
  ditto -c -k --keepParent "$APP_BUNDLE" "$ZIP_NAME"

  echo "🧾 Submitting for notarization..."
  xcrun notarytool submit "$ZIP_NAME" \
    --apple-id "$APPLE_ID" \
    --team-id "$TEAM_ID" \
    --password "$APP_PASSWORD" \
    --wait

  echo "📌 Stapling notarization ticket..."
  xcrun stapler staple "$APP_BUNDLE"

  echo "✅ Verifying Gatekeeper and signature..."
  spctl --assess --type execute --verbose "$APP_BUNDLE"
  codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE"
fi

echo "📁 Preparing USB-portable release directory..."
mkdir -p "$RELEASE_DIR"
cp -R "$APP_BUNDLE" "$RELEASE_DIR/"
if [[ -f README.md ]]; then
  cp README.md "$RELEASE_DIR/"
fi

# Optional zipped deliverable
(
  cd release
  zip -r "${APP_NAME}-mac-portable.zip" "${APP_NAME}-mac" >/dev/null
)

echo "🎉 Done. Artifacts:"
echo "   - $APP_BUNDLE"
echo "   - $RELEASE_DIR"
echo "   - release/${APP_NAME}-mac-portable.zip"
