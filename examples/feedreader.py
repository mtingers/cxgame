import asyncio
import websockets
import sys

async def feed():
    async with websockets.connect('ws://mtingers.com:9876') as websocket:
        while 1:
            response = await websocket.recv()
            print(response)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(feed())
