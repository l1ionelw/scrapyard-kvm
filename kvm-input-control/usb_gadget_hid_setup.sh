#!/bin/bash
set -euo pipefail

# === Settings ===
G=/sys/kernel/config/usb_gadget/zerogadget
PRODUCT_STR="Generic USB Mouse & Keyboard"
MANUF_STR="Raspberry Pi"
SERIAL_STR="0001"
WITH_RNDIS=1   # set to 0 if you do NOT want USB networking

# Optional: clean out conflicting single-function gadgets
# (If you boot with g_ether, it will block the UDC)
for m in g_ether g_serial g_mass_storage g_multi; do
  if lsmod | grep -q "^${m}"; then
    echo "Unloading $m"
    modprobe -r "$m" || true
  fi
done

# Ensure configfs is mounted
if ! mount | grep -q "type configfs"; then
  mount -t configfs none /sys/kernel/config
fi

modprobe libcomposite

# Create gadget
mkdir -p "$G"
echo 0x1d6b > "$G/idVendor"   # Linux Foundation (dev/testing)
echo 0x0104 > "$G/idProduct"  # Multifunction Composite Gadget
echo 0x0200 > "$G/bcdDevice"
echo 0x0200 > "$G/bcdUSB"

mkdir -p "$G/strings/0x409"
echo "$SERIAL_STR"  > "$G/strings/0x409/serialnumber"
echo "$MANUF_STR"   > "$G/strings/0x409/manufacturer"
echo "$PRODUCT_STR" > "$G/strings/0x409/product"

mkdir -p "$G/configs/c.1" "$G/configs/c.1/strings/0x409"
echo "Config 1" > "$G/configs/c.1/strings/0x409/configuration"
echo 250 > "$G/configs/c.1/MaxPower"

# --- HID Keyboard (hidg0) ---
mkdir -p "$G/functions/hid.usb0"
echo 1 > "$G/functions/hid.usb0/protocol"       # Keyboard
echo 1 > "$G/functions/hid.usb0/subclass"
echo 8 > "$G/functions/hid.usb0/report_length"
# 8-byte boot keyboard descriptor
echo -ne \
'\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x01\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0' \
> "$G/functions/hid.usb0/report_desc"

# --- HID Mouse (hidg1) ---
mkdir -p "$G/functions/hid.usb1"
echo 2 > "$G/functions/hid.usb1/protocol"       # Mouse
echo 1 > "$G/functions/hid.usb1/subclass"
echo 4 > "$G/functions/hid.usb1/report_length"
# 4-byte mouse: buttons, X, Y, wheel
echo -ne \
'\x05\x01\x09\x02\xa1\x01\x09\x01\xa1\x00\x05\x09\x19\x01\x29\x03\x15\x00\x25\x01\x95\x03\x75\x01\x81\x02\x95\x01\x75\x05\x81\x01\x05\x01\x09\x30\x09\x31\x15\x81\x25\x7f\x75\x08\x95\x02\x81\x06\x09\x38\x15\x81\x25\x7f\x75\x08\x95\x01\x81\x06\xc0\xc0' \
> "$G/functions/hid.usb1/report_desc"

# Link HID functions
ln -sf "$G/functions/hid.usb0" "$G/configs/c.1/"
ln -sf "$G/functions/hid.usb1" "$G/configs/c.1/"

# --- Optional RNDIS function (Windows-friendly USB networking) ---
if [ "$WITH_RNDIS" -eq 1 ]; then
  # Some kernels need rndis_host on the other side; here we add RNDIS function
  mkdir -p "$G/functions/rndis.usb0"
  # Random-ish MACs in fe:xx:xx range
  HOST_MAC="02:1A:11:00:00:01"
  DEV_MAC="02:1A:11:00:00:02"
  echo "$HOST_MAC" > "$G/functions/rndis.usb0/host_addr" || true
  echo "$DEV_MAC"  > "$G/functions/rndis.usb0/dev_addr"  || true
  ln -sf "$G/functions/rndis.usb0" "$G/configs/c.1/"
fi

# Bind to first available UDC
UDC=$(ls /sys/class/udc | head -n1)
if [ -z "$UDC" ]; then
  echo "No UDC found. Is dwc2 loaded and dtoverlay=dwc2 set? Are you on the USB *data* port?"
  exit 1
fi

echo "$UDC" > "$G/UDC"

echo "Composite USB gadget up."
echo "If WITH_RNDIS=1, you should see USB networking + a keyboard and mouse."
echo "Device files should now exist: /dev/hidg0 (kbd), /dev/hidg1 (mouse)."

