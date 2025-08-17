#!/usr/bin/env python3
"""
WebSocket HID server for Raspberry Pi (USB gadget mode).
Command format (same as TCP version):

  TYPE <text with spaces>
  KEY <name> [modifiers...]
  MOVE <dx> <dy>
  SCROLL <n>
  CLICK <left|right|middle>

Run:
  pip install websockets
  python3 server_websockets.py --host 0.0.0.0 --port 5555
"""

import os
import sys
import time
import asyncio
import argparse
from functools import partial

import websockets

# Paths created by the gadget
KBD_DEV = "/dev/hidg0"
MOU_DEV = "/dev/hidg1"

# HID keycodes (USB HID Usage IDs) – minimal set; add as needed
KEYCODES = {
    # letters
    **{chr(ord('a') + i): 0x04 + i for i in range(26)},
    # digits top row
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    # controls
    "enter": 0x28, "esc": 0x29, "backspace": 0x2A, "tab": 0x2B, "space": 0x2C,
    "minus": 0x2D, "equals": 0x2E, "leftbrace": 0x2F, "rightbrace": 0x30,
    "backslash": 0x31, "semicolon": 0x33, "apostrophe": 0x34, "grave": 0x35,
    "comma": 0x36, "dot": 0x37, "slash": 0x38,
    "capslock": 0x39,
    # arrows & function
    "f1": 0x3A, "f2": 0x3B, "f3": 0x3C, "f4": 0x3D, "f5": 0x3E, "f6": 0x3F,
    "f7": 0x40, "f8": 0x41, "f9": 0x42, "f10": 0x43, "f11": 0x44, "f12": 0x45,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
}

# Modifier bits
MOD = {
    "lctrl": 1 << 0, "lshift": 1 << 1, "lalt": 1 << 2, "lgui": 1 << 3,
    "rctrl": 1 << 4, "rshift": 1 << 5, "ralt": 1 << 6, "rgui": 1 << 7
}

def write_keyboard(mod=0, keys=[]):
    """Send an 8-byte boot keyboard report: [mod, reserved, k1..k6]"""
    report = bytes([mod, 0] + keys[:6] + [0] * (6 - len(keys)))
    with open(KBD_DEV, "wb", buffering=0) as f:
        f.write(report)

def key_press_release(key, modifiers=[]):
    """Press and release a single key with optional modifiers (blocking)."""
    modbits = 0
    for m in modifiers:
        modbits |= MOD.get(m, 0)
    kc = KEYCODES.get(key)
    if kc is None:
        return
    write_keyboard(modbits, [kc])   # press
    time.sleep(0.01)
    write_keyboard(0, [])           # release


def type_text(text):
    """Type simple ASCII text (blocking). Extend for more symbols as needed."""
    for ch in text:
        if 'a' <= ch <= 'z':
            key_press_release(ch)
        elif 'A' <= ch <= 'Z':
            key_press_release(ch.lower(), ["lshift"])
        elif ch == ' ':
            key_press_release("space")
        elif ch == '\n':
            key_press_release("enter")
        else:
            # Extend with more symbols if needed
            pass

def write_mouse(buttons=0, dx=0, dy=0, wheel=0):
    """Send a 4-byte mouse report: [buttons, x, y, wheel] (blocking)."""
    def clamp(v):
        return max(-127, min(127, int(v)))
    report = bytes([
        (buttons & 0x07),
        (clamp(dx) & 0xFF),
        (clamp(dy) & 0xFF),
        (clamp(wheel) & 0xFF)
    ])
    with open(MOU_DEV, "wb", buffering=0) as f:
        f.write(report)

def click(btnname):
    """Click left/right/middle (blocking)."""
    mask = {"left": 1, "right": 2, "middle": 4}.get(btnname, 1)
    write_mouse(mask, 0, 0, 0)  # down
    time.sleep(0.01)
    write_mouse(0, 0, 0, 0)     # up

GREETING = (
    "OK Ready (WebSocket). Commands: TYPE <text>, KEY <name> [mods...], "
    "MOVE dx dy, SCROLL n, CLICK <left|right|middle>\n"
)

async def handle_ws(websocket):
    """Per-connection handler (websockets>=12 style)."""
    # Send greeting once connected
    try:
        await websocket.send(GREETING)
    except Exception:
        pass

    loop = asyncio.get_running_loop()

    async for message in websocket:
        line = message.strip()
        if not line:
            continue

        try:
            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "TYPE":
                text = line[5:] if len(line) >= 5 else ""
                await loop.run_in_executor(None, type_text, text)
                await websocket.send("OK\n")

            elif cmd == "KEY":
                key = parts[1].lower()
                mods = [p.lower() for p in parts[2:]]
                await loop.run_in_executor(None, partial(key_press_release, key, mods))
                await websocket.send("OK\n")

            elif cmd == "MOVE":
                dx = int(parts[1]); dy = int(parts[2])
                await loop.run_in_executor(None, partial(write_mouse, 0, dx, dy, 0))
                await websocket.send("OK\n")

            elif cmd == "SCROLL":
                n = int(parts[1])
                await loop.run_in_executor(None, partial(write_mouse, 0, 0, 0, n))
                await websocket.send("OK\n")

            elif cmd == "CLICK":
                btn = parts[1].lower() if len(parts) > 1 else "left"
                await loop.run_in_executor(None, partial(click, btn))
                await websocket.send("OK\n")

            else:
                await websocket.send("ERR Unknown command\n")

        except Exception as e:
            try:
                await websocket.send(f"ERR {e}\n")
            except Exception:
                pass

def ensure_devices():
    for p in (KBD_DEV, MOU_DEV):
        if not os.path.exists(p):
            print(f"Missing {p}. Is the USB gadget up?", file=sys.stderr)
            sys.exit(1)

async def async_main():
    parser = argparse.ArgumentParser(description="WebSocket HID server")
    parser.add_argument("--host", default="raspberrypi.local", help="Bind host (default raspberrypi.local)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default 8765)")
    parser.add_argument("--path", default="/", help="WebSocket path (default /)")
    args = parser.parse_args()

    ensure_devices()

    print(f"HID WS server listening on ws://{args.host}:{args.port}{args.path}")

    async def router(websocket):
        # websockets>=12 provides the request path as websocket.path
        req_path = getattr(websocket, "path", "/")
        if req_path != args.path:
            await websocket.close(code=1008, reason="Invalid path")
            return
        await handle_ws(websocket)

    # Start server (await/context-manager required in >=12)
    async with websockets.serve(
        router,
        args.host,
        args.port,
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(async_main())
