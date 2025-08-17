import asyncio
import websockets
import json
async def send_payload(websocket, payload):
    await websocket.send(json.dumps(payload))
    response = await websocket.recv()
    print("Response: ", response)
    await asyncio.sleep(1)

async def test_mouse(ws):
    await send_payload(ws, {"type": "MOUSE", "key": "RCLICK", "action": "CLICK"})
    await send_payload(ws, {"type": "MOUSE", "key": "LCLICK", "action": "CLICK"})
    await send_payload(ws, {"type": "MOUSE", "key": "2", "action": "SCROLL"})
    await send_payload(ws, {"type": "MOUSE", "key": "-2", "action": "SCROLL"})
    await send_payload(ws, {"type": "MOUSE", "key": "20|20", "action": "MOVE"})
    await send_payload(ws, {"type": "MOUSE", "key": "-20|-20", "action": "MOVE"})


async def test_client():
    uri = "ws://raspberrypi.local:5000"
    async with websockets.connect(uri) as ws:
        await test_mouse(ws)




asyncio.run(test_client())

