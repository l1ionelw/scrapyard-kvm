#!/usr/bin/env python3
import socket, threading, sys, os, time

# Paths created by the gadget
KBD_DEV = "/dev/hidg0"
MOU_DEV = "/dev/hidg1"

# HID keycodes (USB HID Usage IDs) – minimal set; add as needed
KEYCODES = {
    # letters
    **{chr(ord('a')+i): 0x04+i for i in range(26)},
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
    "f1":0x3A,"f2":0x3B,"f3":0x3C,"f4":0x3D,"f5":0x3E,"f6":0x3F,
    "f7":0x40,"f8":0x41,"f9":0x42,"f10":0x43,"f11":0x44,"f12":0x45,
    "right":0x4F,"left":0x50,"down":0x51,"up":0x52,
}

# Modifier bits
MOD = {"lctrl":1<<0,"lshift":1<<1,"lalt":1<<2,"lgui":1<<3,"rctrl":1<<4,"rshift":1<<5,"ralt":1<<6,"rgui":1<<7}

def write_keyboard(mod=0, keys=[]):
    # 8-byte boot keyboard report: [mod, reserved, k1..k6]
    report = bytes([mod, 0] + keys[:6] + [0]*(6-len(keys)))
    with open(KBD_DEV, "wb", buffering=0) as f:
        f.write(report)

def key_press_release(key, modifiers=[]):
    modbits = 0
    for m in modifiers:
        modbits |= MOD.get(m,0)
    kc = KEYCODES.get(key)
    if kc is None:
        return
    write_keyboard(modbits, [kc])   # press
    time.sleep(0.01)
    write_keyboard(0, [])           # release

def type_text(text):
    # simple ASCII typing; shift letters as needed
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
    # 4-byte mouse report: [buttons, x, y, wheel]
    def clamp(v):
        return max(-127, min(127, int(v)))
    report = bytes([(buttons & 0x07), (clamp(dx) & 0xFF), (clamp(dy) & 0xFF), (clamp(wheel) & 0xFF)])
    with open(MOU_DEV, "wb", buffering=0) as f:
        f.write(report)

def click(btnname):
    mask = {"left":1, "right":2, "middle":4}.get(btnname, 1)
    write_mouse(mask, 0, 0, 0)  # down
    time.sleep(0.01)
    write_mouse(0, 0, 0, 0)     # up

def handle_client(conn, addr):
    f = conn.makefile("r")
    conn.sendall(b"OK Ready. Commands: TYPE <text>, KEY <name> [mods...], MOVE dx dy, SCROLL n, CLICK <left|right|middle>\n")
    for line in f:
        try:
            line=line.strip()
            if not line: 
                continue
            parts=line.split()
            cmd=parts[0].upper()
            if cmd=="TYPE":
                text=line[5:] if len(line)>=5 else ""
                type_text(text)
            elif cmd=="KEY":
                key=parts[1].lower()
                mods=[p.lower() for p in parts[2:]]
                key_press_release(key, mods)
            elif cmd=="MOVE":
                dx=int(parts[1]); dy=int(parts[2])
                write_mouse(0, dx, dy, 0)
            elif cmd=="SCROLL":
                n=int(parts[1])
                write_mouse(0, 0, 0, n)
            elif cmd=="CLICK":
                btn=parts[1].lower() if len(parts)>1 else "left"
                click(btn)
            else:
                conn.sendall(b"ERR Unknown command\n")
                continue
            conn.sendall(b"OK\n")
        except Exception as e:
            conn.sendall(f"ERR {e}\n".format(e).encode())
    conn.close()

def main():
    # Ensure devices exist
    for p in (KBD_DEV, MOU_DEV):
        if not os.path.exists(p):
            print(f"Missing {p}. Is the USB gadget up?", file=sys.stderr)
            sys.exit(1)

    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 5555))
    s.listen(1)
    print("HID server listening on 0.0.0.0:5555")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__=="__main__":
    main()
