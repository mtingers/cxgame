import sys
import random
import time
import asyncio
import websockets
import hashlib
import threading
import ssl
import queue
import json
import pickle
from pprint import pprint
from util import *

class CxCmdClient:
    def __init__(self, user=None, websocket=None, token=None):
        self.user = user
        self.token = token
        self.websocket = websocket

    async def _send_recv(self, msg):
        await self.websocket.send(json.dumps(msg))
        x = await self.websocket.recv()
        j = json.loads(x)
        return j

    async def register(self):
        msg = {'cmd': 'register', 'params': {'username': self.user}}
        j = await self._send_recv(msg)
        if j['status']:
            self.token = j['data']
        return j

    async def auth(self):
        msg = {'cmd': 'auth', 'params': {'username': self.user, 'token':self.token}}
        return await self._send_recv(msg)

    async def buy(self, price, size):
        price = dec(price, prec=ROUND_USD)
        size = dec(size, prec=ROUND_CRYPTO)
        msg = {'cmd':'buy', 'params':{'price':dec_str(price), 'size':dec_str(size)}}
        return await self._send_recv(msg)

    async def buy_market(self, amount):
        amount = dec(amount, prec=ROUND_USD)
        msg = {'cmd':'buy_market', 'params':{'amount':dec_str(amount)}}
        return await self._send_recv(msg)

    async def sell(self, price, size):
        price = dec(price, prec=ROUND_USD)
        size = dec(size, prec=ROUND_CRYPTO)
        msg = {'cmd':'sell', 'params':{'price':dec_str(price), 'size':dec_str(size)}}
        return await self._send_recv(msg)

    async def sell_market(self, amount):
        amount = dec(amount, prec=ROUND_CRYPTO)
        msg = {'cmd':'sell_market', 'params':{'amount':dec_str(amount)}}
        return await self._send_recv(msg)

    async def broadcast(self, message):
        msg = {'cmd': 'bcast', 'params': {'message':message}}
        j = await self._send_recv(msg)
        return j

    async def cancel(self, order_id):
        msg = {'cmd': 'cancel', 'params': {'order_id':order_id}}
        j = await self._send_recv(msg)
        return j

    async def price(self):
        msg = {'cmd': 'price', 'params': {}}
        j = await self._send_recv(msg)
        if j['status']:
            return j['data']
        return False

    async def audit(self):
        msg = {'cmd': 'audit', 'params': {}}
        j = await self._send_recv(msg)
        if j['status']:
            return j['data']
        return False

    async def orders(self):
        msg = {'cmd': 'orders', 'params': {}}
        j = await self._send_recv(msg)
        if j['status']:
            return j['data']
        return False

    async def fills(self):
        msg = {'cmd': 'fills', 'params': {}}
        j = await self._send_recv(msg)
        if j['status']:
            return j['data']
        return False

    async def completed(self):
        msg = {'cmd': 'completed', 'params': {}}
        j = await self._send_recv(msg)
        if j['status']:
            return j['data']
        return False

    async def all_orders(self):
        msg = {'cmd': 'all_orders', 'params': {}}
        j = await self._send_recv(msg)
        if j['status']:
            return j['data']
        return False

    async def wallets(self):
        msg = {'cmd': 'wallets', 'params': {}}
        j = await self._send_recv(msg)
        if j['status']:
            return j['data']
        return False

"""
The following is a test client implementation.
"""

TEST_TOKEN = None
TEST_USER = None
async def runcmd(method, *a):
    global TEST_TOKEN, TEST_USER
    uri = "ws://localhost:9877"
    async with websockets.connect(uri) as websocket:
        if not TEST_USER:
            username = 'bot-'+str(random.randint(0,1000000000))
            TEST_USER = username
            print('new_user_generated:', username)
        cmd = CxCmdClient(user=TEST_USER, websocket=websocket, token=TEST_TOKEN)
        if not TEST_TOKEN:
            x = await cmd.register()
            TEST_TOKEN = x['data']
        else:
            cmd.token = TEST_TOKEN
            x = await cmd.auth()

        m = getattr(cmd, method, None)
        if not m:
            raise Exception('Invalid command name: %s' % (method))
        x = await m(*a)
        pprint(x)
        return x

def m(method, *a):
    global TEST_TOKEN, TEST_USER
    if 'reset' == method.strip():
        TEST_TOKEN = None
        TEST_USER = None
        return None
    return asyncio.get_event_loop().run_until_complete(runcmd(method, *a))
