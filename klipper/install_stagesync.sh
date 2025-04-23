#!/usr/bin/env bash
set -euo pipefail

# install_stagesync.sh - copy stagesync.py into Klipper extras directory

# Directory where this script is located (e.g., ~/stagesync/klipper)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source file to install
SRC_FILE="$SCRIPT_DIR/stagesync.py"

# Destination directory in Klipper firmware and full destination file path
DEST_DIR="$HOME/klipper/klippy/extras"
DEST_FILE="$DEST_DIR/stagesync.py"

# Ensure source file exists
if [ ! -f "$SRC_FILE" ]; then
  echo "Error: cannot find '$SRC_FILE'. Make sure you're in the correct directory." >&2
  exit 1
fi

# Ensure destination directory exists
if [ ! -d "$DEST_DIR" ]; then
  echo "Error: destination directory '$DEST_DIR' not found." >&2
  exit 1
fi

# Install or update the plugin
if [ -f "$DEST_FILE" ]; then
  echo "Updating stagesync.py"
else
  echo "Installing stagesync.py"
fi
cp -f "$SRC_FILE" "$DEST_FILE"

# Final feedback
if [ $? -eq 0 ]; then
  echo "Installation completed!"
else
  echo "Error copying '$SRC_FILE'." >&2
  exit 1
fi
