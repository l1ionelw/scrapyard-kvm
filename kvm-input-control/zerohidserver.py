import asyncio
from typing import List
import websockets
import json
from zero_hid import Mouse, Keyboard, KeyCodes
import argparse

mouse = Mouse()
keyboard = Keyboard()
debug = False

def to_int(val):
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            val = val.strip()
            if val.lower().startswith("0x"):
                return int(val, 16)
            return int(val)
        raise ValueError(f"Unsupported type for HID code: {val!r}")

def keyboard_handler(payload):
    print("ALT CODE: ", KeyCodes.MOD_LEFT_ALT)
    print("CTRL CODE: ", KeyCodes.MOD_LEFT_CONTROL)
    print("SHIFT CODE: ", KeyCodes.MOD_LEFT_SHIFT)
    """
    {type: 'KEYBOARD', action: 'PRESS', modifiers: [0x01, 0x03], key: 0x1E}
    """
    if payload["action"] == "TYPE": 
        key = payload["key"]
        print("typing: ", payload["key"]) # should be a single string
        keyboard.type(payload["key"])
        return f"typed {key}"
    modifiers_raw = payload["modifiers"]
    print(modifiers_raw)
    key = int(payload["key"])
    modifiers = []
    keyboard.press(modifiers_raw, key, release=True)
    return f"Sent {modifiers_raw} + {key}"
    

def mouse_handler(payload):
    """ 
    {type: 'MOUSE', action: 'CLICK', key: 'LCLICK'} 
    {type: 'MOUSE', action: 'CLICK', key: 'RCLICK'} 
    {type: 'MOUSE', action: 'SCROLL', key: '-10'} 
    {type: 'MOUSE', action: 'SCROLL', key: '10'} 
    {type: 'MOUSE', action: 'MOVE', key: '10|10'} 
    {type: 'MOUSE', action: 'MOVE', key: '-10|10'} 
    """
    print("handling mouse input")

    action = payload["action"]
    key = payload["key"]

    if action == "CLICK":
        if key == "LCLICK":
            mouse.left_click()
        elif key == "RCLICK":
            mouse.right_click()

    elif action == "SCROLL":
        mouse.scroll_y(int(key))

    elif action == "MOVE":
        x_str, y_str = key.split("|")
        mouse.move(int(x_str), int(y_str))



async def handler(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            try:
                return_message = "OK"
                payload = json.loads(message)
                print("Received payload:", payload)

                if payload["type"] == "KEYBOARD":
                    if debug:
                        await asyncio.sleep(1)

                    # keyboard.press(mods=[], key_code=0x04)
                    return_message = keyboard_handler(payload)
                    print(return_message)

                elif payload["type"] == "MOUSE":
                    if debug:
                        await asyncio.sleep(0.1)
                    mouse_handler(payload)

                await websocket.send(return_message)

            except json.JSONDecodeError:
                print("Invalid JSON:", message)
                await websocket.send("ERROR: Invalid JSON")

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")


async def main():
    async with websockets.serve(handler, "0.0.0.0", 5000):
        print("WebSocket server running on ws://0.0.0.0:5000")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true",
                        help="Enable 1s artificial delay on KEYBOARD actions")
    args = parser.parse_args()
    debug = args.debug
    asyncio.run(main())
