#!/usr/bin/env python3
"""
Simple TCP client for the Pi Zero W HID server.
Works on Windows/macOS/Linux.

Usage examples:
  python hid_client.py --host 192.168.1.50 --port 5555 --cmd "TYPE hello from windows!"
  python hid_client.py --host 192.168.1.50 --cmd "KEY enter"
  python hid_client.py --host 192.168.1.50 --cmd "MOVE 50 0"
  python hid_client.py --host 192.168.1.50 --interactive

Command format (sent to the Pi server):
  TYPE <text with spaces allowed>
  KEY <name> [modifiers...]
  MOVE <dx> <dy>
  SCROLL <n>
  CLICK <left|right|middle>
"""

import argparse
import socket
import sys

# -------- Default endpoint (override via CLI flags) --------
PI_HOST = "raspberrypi.local"   # <-- change this to your Pi's IP or hostname
PI_PORT = 5555             # <-- change if you modified the server port

# -----------------------------------------------------------

def send_command(host: str, port: int, command: str, timeout: float = 5.0) -> str:
    """Send one command, return server response (or raise on error)."""
    with socket.create_connection((host, port), timeout=timeout) as s:
        # Read server greeting (non-fatal if not present)
        s.settimeout(1.0)
        try:
            greeting = s.recv(4096)
            if greeting:
                try:
                    sys.stdout.write(greeting.decode(errors="ignore"))
                except Exception:
                    pass
        except Exception:
            pass

        # Send the command with newline
        payload = (command.strip() + "\n").encode()
        s.sendall(payload)

        # Read response until socket closes or timeout
        s.settimeout(2.0)
        chunks = []
        try:
            while True:
                data = s.recv(4096)
                if not data:
                    break
                chunks.append(data)
        except Exception:
            # timeout or server kept connection open—best-effort read
            pass

    return b"".join(chunks).decode(errors="ignore")


def interactive(host: str, port: int):
    print(f"Connected target set to {host}:{port}")
    print("Type commands like:")
    print('  TYPE hello world!')
    print('  KEY enter')
    print('  KEY a lshift')
    print('  MOVE 30 10')
    print('  SCROLL -1')
    print('  CLICK left')
    print("Ctrl+C to quit.\n")
    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            resp = send_command(host, port, line)
            if resp:
                print(resp, end="" if resp.endswith("\n") else "\n")
        except KeyboardInterrupt:
            print("\nBye.")
            return
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Client for Pi HID TCP server")
    parser.add_argument("--host", default=PI_HOST, help="Pi hostname or IP")
    parser.add_argument("--port", type=int, default=PI_PORT, help="Pi TCP port")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--cmd", help="Send a single command (quoted)")
    group.add_argument("--interactive", action="store_true", help="Interactive REPL mode")
    args = parser.parse_args()

    if args.interactive:
        interactive(args.host, args.port)
        return

    if not args.cmd:
        parser.error("Provide --cmd \"...\" or use --interactive")

    try:
        resp = send_command(args.host, args.port, args.cmd)
        if resp:
            print(resp, end="" if resp.endswith("\n") else "\n")
    except Exception as e:
        print(f"Failed to send command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
