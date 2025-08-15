#!/bin/bash
set -euo pipefail

G=/sys/kernel/config/usb_gadget/zerogadget

if [ -d "$G" ]; then
  # Unbind
  if [ -f "$G/UDC" ]; then
    echo "" > "$G/UDC" || true
  fi

  # Remove function links
  find "$G/configs" -type l -exec rm -f {} +

  # Remove functions
  rm -rf "$G/functions/"* || true

  # Remove configs and strings
  rm -rf "$G/configs/"* || true
  rm -rf "$G/strings/"* || true

  # Remove gadget
  rmdir "$G" || true
fi

echo "Gadget torn down."
