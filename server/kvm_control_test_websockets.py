#!/usr/bin/env python3
"""
WebSocket client for the Pi Zero W HID WS server.

Usage examples:
  python hid_client_ws.py --url ws://raspberrypi.local:5555 --cmd "TYPE hello from websockets!"
  python hid_client_ws.py --url ws://raspberrypi.local:5555 --cmd "KEY enter"
  python hid_client_ws.py --url ws://raspberrypi.local:5555 --cmd "MOVE 50 0"
  python hid_client_ws.py --url ws://raspberrypi.local:5555 --interactive
"""

import argparse
import asyncio
import sys

import websockets

async def send_command(url: str, command: str, timeout: float = 5.0) -> str:
    async with websockets.connect(url, open_timeout=timeout, close_timeout=timeout) as ws:
        # Try to read greeting (optional)
        try:
            greeting = await asyncio.wait_for(ws.recv(), timeout=1.0)
            if greeting:
                try:
                    sys.stdout.write(greeting)
                except Exception:
                    pass
        except Exception:
            pass

        await ws.send(command.strip())

        # Try to read response; server may keep connection open for interactive use
        resp = ""
        try:
            chunk = await asyncio.wait_for(ws.recv(), timeout=2.0)
            if isinstance(chunk, (bytes, bytearray)):
                chunk = chunk.decode(errors="ignore")
            resp += chunk
        except Exception:
            pass
        return resp

async def interactive(url: str):
    print(f"Connected target set to {url}")
    print("Type commands like:")
    print('  TYPE hello world!')
    print('  KEY enter')
    print('  KEY a lshift')
    print('  MOVE 30 10')
    print('  SCROLL -1')
    print('  CLICK left')
    print("Ctrl+C to quit.\n")

    # Keep one WS connection open for REPL
    async with websockets.connect(url) as ws:
        # Read greeting if any
        try:
            greeting = await asyncio.wait_for(ws.recv(), timeout=1.0)
            if greeting:
                print(greeting, end="" if str(greeting).endswith("\n") else "\n")
        except Exception:
            pass

        loop = asyncio.get_event_loop()
        while True:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                await ws.send(line)
                try:
                    reply = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if isinstance(reply, (bytes, bytearray)):
                        reply = reply.decode(errors="ignore")
                    print(reply, end="" if reply.endswith("\n") else "\n")
                except asyncio.TimeoutError:
                    # Best-effort if server didn't reply
                    pass
            except KeyboardInterrupt:
                print("\nBye.")
                return

def main():
    parser = argparse.ArgumentParser(description="Client for Pi HID WebSocket server")
    parser.add_argument("--url", default="ws://raspberrypi.local:5555", help="WebSocket URL of the Pi server")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--cmd", help='Send a single command (quoted), e.g. --cmd "TYPE hello"')
    group.add_argument("--interactive", action="store_true", help="Interactive REPL mode")
    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive(args.url))
        return

    if not args.cmd:
        parser.error('Provide --cmd "..." or use --interactive')

    try:
        resp = asyncio.run(send_command(args.url, args.cmd))
        if resp:
            print(resp, end="" if resp.endswith("\n") else "\n")
    except Exception as e:
        print(f"Failed to send command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
