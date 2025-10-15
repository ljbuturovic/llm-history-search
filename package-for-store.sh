#!/bin/bash
# Package conversai extension for Chrome Web Store

set -e

PACKAGE_DIR="conversai-webstore"
ZIP_FILE="conversai-extension.zip"

echo "Creating package directory..."
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

echo "Copying extension files..."
cp background.js content.js db.js index.html "$PACKAGE_DIR/"
cp -r icons "$PACKAGE_DIR/"

echo "Creating production manifest.json (without localhost)..."
cat manifest.json | jq '.externally_connectable.matches = ["http://conversai.us/*"]' > "$PACKAGE_DIR/manifest.json"

echo "Creating ZIP file..."
cd "$PACKAGE_DIR"
zip -r "../$ZIP_FILE" .
cd ..

echo "Cleaning up..."
rm -rf "$PACKAGE_DIR"

echo ""
echo "✓ Package created: $ZIP_FILE"
echo "✓ Ready to upload to Chrome Web Store"
echo ""
echo "Contents:"
unzip -l "$ZIP_FILE"
