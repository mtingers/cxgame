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
from .util import *

class Response:
    def __init__(self, status=False, msg=None, data=None, raw=None):
        self.status = status
        self.msg = msg
        self.data = data
        self.raw = raw

class CxClient:
    def __init__(self, user=None, websocket=None, token=None, uri=None):
        """
        Note: if a websocket is specified, this is an existing connection.
        Specifying a websocket is like the runcmd() method, but you're in
        control of the socket. If you call r() or runcmd(), they will replace
        self.websocket.
        """
        self.user = user
        self.token = token
        self.websocket = websocket
        self.uri = uri
        
    async def _send_recv(self, msg):
        response = Response()
        try:
            await self.websocket.send(json.dumps(msg))
            x = await self.websocket.recv()
            j = json.loads(x)
            response.status = j['status']
            response.msg = j['message']
            response.data = j['data']
            response.raw = x
        except Exception as error:
            response.status = False
            response.msg = str(error)
        return response

    async def register(self):
        msg = {'cmd': 'register', 'params': {'username': self.user}}
        response = await self._send_recv(msg)
        if response.status:
            self.token = response.data
        return response

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
        return await self._send_recv(msg)

    async def cancel(self, order_id):
        msg = {'cmd': 'cancel', 'params': {'order_id':order_id}}
        return await self._send_recv(msg)

    async def price(self):
        msg = {'cmd': 'price', 'params': {}}
        response = await self._send_recv(msg)
        response.data = dec(response.data, prec=ROUND_USD)
        return response

    async def audit(self):
        msg = {'cmd': 'audit', 'params': {}}
        return await self._send_recv(msg)

    async def orders(self):
        msg = {'cmd': 'orders', 'params': {}}
        return await self._send_recv(msg)

    async def fills(self):
        msg = {'cmd': 'fills', 'params': {}}
        return await self._send_recv(msg)

    async def completed(self):
        msg = {'cmd': 'completed', 'params': {}}
        return await self._send_recv(msg)

    async def all_orders(self):
        msg = {'cmd': 'all_orders', 'params': {}}
        return await self._send_recv(msg)

    async def wallets(self):
        msg = {'cmd': 'wallets', 'params': {}}
        return await self._send_recv(msg)

    def random_username(self, prefix='test'):
        username = prefix+'-'+str(random.randint(0,1000))+str(time.time())
        self.user = username
        self.token = None
        return username

    async def runcmd(self, method, *a):
        async with websockets.connect(self.uri) as websocket:
            self.websocket = websocket
            if not self.token:
                response = await self.register()
            elif self.user:
                response = await cmd.auth()
            else:
                raise Exception('Username and/or token is not set.')
            m = getattr(self, method, None)
            if not m:
                raise Exception('Invalid command name: %s' % (method))
            response = await m(*a)
            return response

    def r(self, method, *a):
        if 'reset' == method.strip():
            self.random_username()
            return True
        return asyncio.get_event_loop().run_until_complete(self.runcmd(method, *a))

