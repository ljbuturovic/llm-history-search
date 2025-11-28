#!/bin/bash
# Package llm-history-search extension for Chrome Web Store

set -e

PACKAGE_DIR="llm-history-search-webstore"
ZIP_FILE="llm-history-search-extension.zip"

echo "Creating package directory..."
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

echo "Copying extension files..."
cp background.js content.js db.js "$PACKAGE_DIR/"
cp -r icons "$PACKAGE_DIR/"

echo "Creating production manifest.json (without localhost)..."
cat manifest.json | jq '.externally_connectable.matches = ["https://conversai.us/*"]' > "$PACKAGE_DIR/manifest.json"

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
