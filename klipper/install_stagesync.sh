#!/usr/bin/env bash
set -euo pipefail

# install_stagesync.sh - copia stagesync.py nella directory klipper extras

# Directory in cui si trova questo script (~/StageSync/klipper)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# File sorgente da installare
SRC_FILE="$SCRIPT_DIR/stagesync.py"

# Directory di destinazione nel firmware Klipper
DEST_DIR="$HOME/klipper/klippy/extras"
DEST_FILE="$DEST_DIR/stagesync.py"

# Verifica che il file sorgente esista
if [ ! -f "$SRC_FILE" ]; then
  echo "Errore: non trovo '$SRC_FILE'. Assicurati di essere nella directory corretta." >&2
  exit 1
fi

# Verifica che la directory di destinazione esista
if [ ! -d "$DEST_DIR" ]; then
  echo "Errore: directory di destinazione '$DEST_DIR' non trovata." >&2
  exit 1
fi

# Copia il file, sostituendo eventuale versione precedente
if [ -f "$DEST_FILE" ]; then
  echo "File esistente trovato in '$DEST_FILE', lo sostituisco..."
else
  echo "Installo stagesync.py in '$DEST_DIR'..."
fi
cp -f "$SRC_FILE" "$DEST_FILE"

# Feedback finale
if [ $? -eq 0 ]; then
  echo "Installazione completata: '$DEST_FILE'"
else
  echo "Errore durante la copia di '$SRC_FILE'." >&2
  exit 1
fi
