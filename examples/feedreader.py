import ssl
import asyncio
import websockets
import sys

async def feed():
    ssl_context = None
    if len(sys.argv) == 2:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.load_verify_locations(sys.argv[1])
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        uri = "wss://localhost:9876"
    else:
        uri = "ws://localhost:9876"
    async with websockets.connect(uri, ssl=ssl_context) as websocket:
        while 1:
            response = await websocket.recv()
            print(response)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(feed())
