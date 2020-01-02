import os
import random
import time
import asyncio
import hashlib
import threading
import ssl
import queue
import json
import pickle
import traceback
import argparse
from pprint import pprint
from typing import Any, Set
from collections import deque
import websockets
from websockets.server import WebSocketServerProtocol
from .util import *

#STATE_LOCK = threading.Lock()
STATE = {
    'lowest_sell':dec('2000.01'),
    'highest_buy':dec('990.99'),
    'market_price':dec('1000.00'),
    'spread':dec('1.00'),
    'orders':{'buy':[], 'sell':[],},
    'market_orders':{'buy':[], 'sell':[]},
    'orders_completed': [],
    'wallets':{},
    'client_user_map':{},
    'users':{},
    'user_fills':{},
    'queue':queue.Queue()
}

class CxFeed:
    """The broadcast channel. This websocket server broadcasts messages to all
    connected clients. Messages come from the CxExchange websocket server, usually
    in response to CxExchange server client commands (e.g. buy/sell).
    """
    def __init__(self,
            port: int = 9876,
            bind: str = '0.0.0.0',
            pem_file: str = None,
            ssl_verify: bool = True):
        self.port = port
        self.bind = bind
        self.pem_file = pem_file
        self.ssl_verify = ssl_verify
        self.clients = set()
        self.running = False

    @property
    def queue(self):
        return STATE['queue']

    async def _handler(self):
        # Only want 1 handler to broadcast to all clients
        # Subsequent handlers sleep
        if self.running:
            while 1:
                await asyncio.sleep(10)
        else:
            self.running = True
            # Running can be used to shutdown feed server gracefully
            while self.running:
                try:
                    item = self.queue.get(block=False)
                except:
                    await asyncio.sleep(0.25)
                    continue
                print('CxFeed item:', item, 'clients:', len(self.clients))
                for websocket in shuffle2(self.clients):
                    try:
                        await websocket.send(item)
                    except:
                        self.clients.remove(websocket)

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        self.clients.add(websocket)
        await self._handler()

    def start(self):
        ssl_context = None
        if self.pem_file:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(self.pem_file)
            if not self.ssl_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
        asyncio.set_event_loop(asyncio.new_event_loop())
        start_server = websockets.serve(self.handler, self.bind, self.port, ssl=ssl_context)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()


class CxExchange:
    def __init__(self,
            port: int = 9877,
            bind: str = '0.0.0.0',
            time_limit: int = None,
            user_limit: int = None,
            usd_start: Decimal = dec('10000.00'),
            crypto_start: Decimal = dec('10.0'),
            whitelist: set = None,
            pem_file: str = None,
            ssl_verify: bool = True,
            admin_secret: str = 'admin',
            is_started: bool = True):
        self.port = port
        self.bind = bind
        self.time_limit = time_limit
        self.user_limit = user_limit
        self.usd_start = dec(usd_start)
        self.crypto_start = dec(crypto_start)
        self.whitelist = whitelist
        self.pem_file = pem_file
        self.ssl_verify = ssl_verify
        self.clients = set()
        self.admin_secret = admin_secret
        self.running = True
        self.is_started = is_started
        # Accepted commands from clients
        # Make sure to update 'util.py' command list "CMDS"
        self.cmds = {
            'register':self._register,
            'auth':self._auth,
            'bcast':self._bcast,
            'buy':self._buy,
            'buy_market':self._buy_market,
            'sell':self._sell,
            'sell_market':self._sell_market,
            'price':self._price,
            'orders':self._orders,
            'all_orders':self._all_orders,
            'wallets':self._wallets,
            'cancel':self._cancel,
            'fills':self._fills,
            'completed':self._completed,
            'audit':self._audit,
            'shutdown':self._shutdown,
            'start':self._open_for_business,
            'pause':self._pause,
        }
        self.time_start = time.time()
        self.price_history = deque(maxlen=3)
        self.price_history.append(self.market_price)

    def _is_authed(self, websocket: WebSocketServerProtocol):
        exists = False
        if websocket in self.client_user_map:
            exists = True
        return exists

    def _get_user(self, websocket: WebSocketServerProtocol):
        """This assumes you already checked _is_authed()"""
        user = self.client_user_map[websocket]
        return user

    def _broadcast(self, data: Any):
        self.queue.put(jencode(data))

    @property
    def client_user_map(self):
        return STATE['client_user_map']

    @property
    def queue(self):
        return STATE['queue']

    @property
    def market_price(self):
        return STATE['market_price']

    @market_price.setter
    def market_price(self, value: Decimal):
        STATE['market_price'] = dec(value, prec=ROUND_USD)

    @property
    def spread(self):
        return STATE['spread']

    @spread.setter
    def spread(self, value):
        STATE['spread'] = value

    @property
    def market_orders(self):
        return STATE['market_orders']

    @property
    def buy_market_orders(self):
        return STATE['market_orders']['buy']

    @property
    def sell_market_orders(self):
        return STATE['market_orders']['sell']

    @property
    def orders(self):
        return STATE['orders']

    @property
    def orders_completed(self):
        return STATE['orders_completed']

    @property
    def wallets(self):
        return STATE['wallets']

    @property
    def buy_orders(self):
        return STATE['orders']['buy']

    @property
    def sell_orders(self):
        return STATE['orders']['sell']

    @property
    def users(self):
        return STATE['users']

    @property
    def user_fills(self):
        return STATE['user_fills']

    def _fills(self, websocket: WebSocketServerProtocol, params: dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        user = self._get_user(websocket)
        return status_ok('Here are your fills.', data=self.user_fills[user])

    def _sell(self, websocket: WebSocketServerProtocol, params: dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        user = self._get_user(websocket)
        if not 'size' in params or not 'price' in params:
            return status_error('Must size "price" and "size" in params.')
        size = dec(params['size'], prec=ROUND_CRYPTO)
        price = dec(params['price'], prec=ROUND_USD)
        if size < MIN_SIZE:
            return status_error(
                'Size must be greater than or equal to %s' % (MIN_SIZE)
            )
        if price < MIN_PRICE:
            return status_error(
                'Price must be greater than or equal to %s' % (MIN_PRICE)
            )
        if price < self.market_price:
            return status_error(
                'Price must be >= market price (%s).' % (self.market_price)
            )
        if size > self.wallets[user]['crypto']:
            return status_error('Size is > available.')

        # Subtract cost from user's crypto wallet
        self.wallets[user]['crypto'] = dec(self.wallets[user]['crypto'] - size, prec=ROUND_CRYPTO)
        order = {
            'timestamp':time.time(),
            'id':user_token(),
            'size':size,
            'price':price,
            'side':'sell',
            'status':'open', # : open, filled
            'filled_size':dec('0.00'),
            'user':user,
        }
        self.orders['sell'].append(order)
        self._calc_market_price()
        self._broadcast({'type':'sell', 'message':order})
        return status_ok('Sell order placed.', data=order)

    def _buy_market(self, websocket:WebSocketServerProtocol, params:dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        user = self._get_user(websocket)
        if not 'amount' in params:
            return status_error('Must have "amount" in params.')
        amount = dec(params['amount'], prec=ROUND_USD)
        if amount < MIN_AMOUNT:
            return status_error(
                'Amount must be greater than or equal to %s' % (MIN_AMOUNT)
            )
        if amount > self.wallets[user]['usd']:
            return status_error('Not enough USD to buy.')

        if len(self.orders['sell']) < 1:
            return status_error('No available sell orders to match.')
        self.wallets[user]['usd'] = dec(self.wallets[user]['usd'] - amount, prec=ROUND_USD)
        order = {
            'timestamp':time.time(),
            'id':user_token(),
            'price':self.market_price, # Target price, not gauranteed
            'amount':dec(amount, prec=ROUND_USD),
            'side':'buy_market',
            'status':'open', # : open, filled
            'filled_size':dec('0.00'),
            'user':user,
        }
        self.market_orders['buy'].append(order)
        self._broadcast({'type':'buy_market', 'message':order})
        return status_ok('Market buy order placed.', data=order)

    def _sell_market(self, websocket:WebSocketServerProtocol, params:dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        user = self._get_user(websocket)
        if not 'amount' in params:
            return status_error('Must have "amount" in params.')
        amount = dec(params['amount'], prec=ROUND_CRYPTO)
        if amount < MIN_SIZE:
            return status_error(
                'Amount must be greater than or equal to %s' % (MIN_SIZE)
            )
        if amount > self.wallets[user]['crypto']:
            return status_error('Not enough crypto to sell. %s > %s' % (amount,self.wallets[user]['crypto']))

        if len(self.orders['buy']) < 1:
            return status_error('No available buy orders to match.')

        self.wallets[user]['crypto'] = dec(self.wallets[user]['crypto'] - amount, prec=ROUND_CRYPTO)
        order = {
            'timestamp':time.time(),
            'id':user_token(),
            'price':self.market_price, # Target price, not gauranteed
            'amount':amount,
            'side':'sell_market',
            'status':'open', # : open, filled
            'filled_size':dec('0.00'),
            'user':user,
        }
        self.market_orders['sell'].append(order)
        self._broadcast({'type':'sell_market', 'message':order})
        return status_ok('Market sell order placed.', data=order)

    def _calc_market_price(self):
        # TODO: Figure out the best way to calculate market price. Right now
        # it is a naive implementation based off of current maker buy/sell
        # lowest/highest average or previous market price if there is not
        # a current buy or sell placed.
        #'orders':{'buy':[], 'sell':[]}
        buys = self.orders['buy']
        sells = self.orders['sell']
        highest_buy = dec('0.00')
        lowest_sell = dec('999999999999.99')
        found_buy = False
        found_sell = False
        for b in buys:
            if b['status'] != 'open':
                continue
            found_buy = True
            if b['price'] > highest_buy:
                highest_buy = b['price']
        for s in sells:
            if s['status'] != 'open':
                continue
            found_sell = True
            if s['price'] < lowest_sell:
                lowest_sell = s['price']

        if found_sell and not found_buy:
            tmp_price = dec(
                (self.market_price + lowest_sell) / dec('2.0'),
                prec=ROUND_USD
            )
        elif not found_sell and found_buy:
            tmp_price = dec(
                (self.market_price + highest_buy) / dec('2.0'),
                prec=ROUND_USD
            )
        elif not found_sell and not found_buy:
            tmp_price = self.market_price
        else:
            tmp_price = dec(
            (highest_buy + lowest_sell) / dec('2.0'),
            prec=ROUND_USD
        )
        self.market_price = tmp_price
        self.price_history.append(tmp_price)
        # Do some averaging to avoid large jumps per tick
        #price_mean = dec(mean(self.price_history), prec=ROUND_USD)
        #self.market_price = dec(mean([price_mean, tmp_price]), prec=ROUND_USD)
        if found_sell and found_buy:
            self.spread = dec(lowest_sell - highest_buy, prec=ROUND_USD)
        else:
            self.spread = dec(abs(self.price_history[-2] - self.price_history[-1]), prec=ROUND_USD)
            if self.spread < 0.01:
                self.spread = dec('0.01')
        print('MARKET_PRICE:', self.market_price, 'SPREAD:', self.spread)

    def _match_market_buys(self):
        buys = filter(
            lambda x: x['status'] == 'open', self.market_orders['buy']
        )
        for buy in buys:
            closest = None
            closest_diff = None
            sells = filter(lambda x: x['status'] == 'open', self.orders['sell'])
            target_price = buy['price']
            for sell in sells:
                if not closest:
                    closest = sell
                    closest_diff = abs(target_price - sell['price'])
                else:
                    cdiff = abs(target_price - sell['price'])
                    if cdiff < closest_diff:
                        closest = sell
                        closest_diff = abs(target_price - sell['price'])

            # No sells on the exchange, nothing to do.
            if not closest:
                return
            sell = closest
            price = sell['price']
            seller_usd_used = sell['size'] * sell['price']
            buyers_wallet = self.wallets[buy['user']]
            sellers_wallet = self.wallets[sell['user']]
            buy_id = buy['id']
            sell_id = sell['id']
            if buy['amount'] > seller_usd_used:
                # seller is done
                sell_size = sell['size']
                sell['status'] = 'filled'
                sell['size'] = dec('0.00')
                sell['filled_size'] = dec(sell_size + sell['filled_size'], prec=ROUND_CRYPTO)
                sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (sell_size * sell['price']), prec=ROUND_USD)
                # buyer is partially done
                buy['filled_size'] = dec(buy['filled_size'] + sell_size, prec=ROUND_CRYPTO)
                buy['amount'] = dec(buy['amount'] - seller_usd_used, prec=ROUND_USD)
                buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + sell_size, prec=ROUND_CRYPTO)
                # Move to completed and delete from main orders list
                self.orders_completed.append(dict(sell))
                self._delete_order(sell)
                filled_size = sell_size

            elif buy['amount'] < seller_usd_used:
                sell_size = sell['size']
                # find sold size based off of percentage of usd
                bs_ratio = buy['amount'] / seller_usd_used
                buy_size = dec(bs_ratio * sell_size, prec=ROUND_CRYPTO)
                # seller is partial
                sell['size'] = dec(sell_size - buy_size, prec=ROUND_CRYPTO)
                sell['filled_size'] = dec(buy_size + sell['filled_size'], prec=ROUND_CRYPTO)
                sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (buy_size * sell['price']), prec=ROUND_USD)
                # buyer is done
                buy['status'] = 'filled'
                buy['filled_size'] = dec(buy['filled_size'] + buy_size, prec=ROUND_CRYPTO)
                buy['amount'] = dec('0.00')
                buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + buy_size, prec=ROUND_CRYPTO)
                # Move to completed and delete from main orders list
                self.orders_completed.append(dict(buy))
                self._delete_market_order(buy)
                filled_size = buy_size

            else: # equal usd value on both sides, both completed
                sell['status'] = 'filled'
                sell_size = sell['size']
                # seller is done
                sell['size'] = dec('0.00')
                sell['filled_size'] = dec(sell_size + sell['filled_size'], prec=ROUND_CRYPTO)
                sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (sell_size * sell['price']), prec=ROUND_USD)
                # buyer is done
                buy['status'] = 'filled'
                buy['filled_size'] = dec(buy['filled_size'] + sell_size, prec=ROUND_CRYPTO)
                buy['amount'] = dec('0.00')
                buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + sell_size, prec=ROUND_CRYPTO)
                # Move to completed and delete from main orders list
                self.orders_completed.append(dict(sell))
                self.orders_completed.append(dict(buy))
                self._delete_order(sell)
                self._delete_market_order(buy)
                filled_size = sell_size

            self.user_fills[sell['user']].append({
                'fill_id':user_token(),
                'filled_size':filled_size,
                'price':price,
                'buy_id':buy_id,
                'sell_id':sell_id,
            })
            self.user_fills[buy['user']].append({
                'fill_id':user_token(),
                'filled_size':filled_size,
                'price':price,
                'buy_id':buy_id,
                'sell_id':sell_id,
            })
            self._broadcast({'type':'match', 'message':{
                'size':filled_size,
                'price':price,
                'buy_id':buy_id,
                'sell_id':sell_id,
            }})

    def _match_market_sells(self):
        sells = filter(
            lambda x: x['status'] == 'open', self.market_orders['sell']
        )
        for sell in sells:
            closest = None
            closest_diff = None
            buys = filter(lambda x: x['status'] == 'open', self.orders['buy'])
            target_price = sell['price']
            for buy in buys:
                if not closest:
                    closest = buy
                    closest_diff = abs(target_price - buy['price'])
                else:
                    cdiff = abs(target_price - buy['price'])
                    if cdiff < closest_diff:
                        closest = buy
                        closest_diff = abs(target_price - buy['price'])

            # No sells on the exchange, nothing to do.
            if not closest:
                return
            buy = closest
            price = buy['price']
            buyers_wallet = self.wallets[buy['user']]
            sellers_wallet = self.wallets[sell['user']]
            buy_id = buy['id']
            sell_id = sell['id']
            sell_size = sell['amount']
            buy_size = buy['size']
            if buy['size'] > sell['amount']:
                # seller is done
                sell['status'] = 'filled'
                sell['amount'] = dec('0.00')
                sell['filled_size'] = dec(sell['filled_size'] + sell_size, prec=ROUND_CRYPTO)
                sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (sell_size * buy['price']), prec=ROUND_USD)
                # buyer is partial
                buy['filled_size'] = dec(buy['filled_size'] + sell_size, prec=ROUND_CRYPTO)
                buy['size'] = dec(buy['size'] - sell_size, prec=ROUND_CRYPTO)
                buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + sell_size, prec=ROUND_CRYPTO)
                # Move to completed and delete from main orders list
                self.orders_completed.append(dict(sell))
                self._delete_market_order(sell)
                filled_size = sell_size

            elif buy['size'] < sell['amount']:
                # seller is partial
                sell['filled_size'] = dec(sell['filled_size'] + buy_size, prec=ROUND_CRYPTO)
                sell['amount'] = dec(sell['amount'] - buy['size'], prec=ROUND_CRYPTO)
                sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (buy['size'] * buy['price']), prec=ROUND_USD)
                # buyer is done
                buy['status'] = 'filled'
                buy['size'] = dec('0.00')
                buy['filled_size'] = dec(buy['filled_size'] + buy_size, prec=ROUND_CRYPTO)
                buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + buy_size, prec=ROUND_CRYPTO)
                # Move to completed and delete from main orders list
                self.orders_completed.append(dict(buy))
                self._delete_order(buy)
                filled_size = buy_size

            else: # equal usd value on both sides, both completed
                # seller is done
                sell['status'] = 'filled'
                sell['amount'] = dec('0.00')
                sell['filled_size'] = dec(sell['filled_size'] + sell_size, prec=ROUND_CRYPTO)
                sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (sell_size * buy['price']), prec=ROUND_USD)
                # buyer is done
                buy['status'] = 'filled'
                buy['size'] = dec('0.00')
                buy['filled_size'] = dec(buy['filled_size'] + buy_size, prec=ROUND_CRYPTO)
                buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + buy_size, prec=ROUND_CRYPTO)
                # Move to completed and delete from main orders list
                self.orders_completed.append(dict(sell))
                self.orders_completed.append(dict(buy))
                self._delete_market_order(sell)
                self._delete_order(buy)
                filled_size = sell_size

            self.user_fills[sell['user']].append({
                'fill_id':user_token(),
                'filled_size':filled_size,
                'price':price,
                'buy_id':buy_id,
                'sell_id':sell_id,
            })
            self.user_fills[buy['user']].append({
                'fill_id':user_token(),
                'filled_size':filled_size,
                'price':price,
                'buy_id':buy_id,
                'sell_id':sell_id,
            })
            self._broadcast({'type':'match', 'message':{
                'size':filled_size,
                'price':price,
                'buy_id':buy_id,
                'sell_id':sell_id,
            }})


    def _fulfill_maker_order_match(self, buy, sell):
        """Matches maker orders"""
        # 1. update filled_size
        # 2. update remaining size
        # 3. update buyer/seller usd or crypto
        # 4. add user_fills item for each user
        # 5. update status (even though it's removed)
        # 6. add to completed and remove orders
        # 7. broadcast match
        buy_size = buy['size']
        sell_size = sell['size']
        buy_id = buy['id']
        sell_id = sell['id']
        buyers_wallet = self.wallets[buy['user']]
        sellers_wallet = self.wallets[sell['user']]
        price = sell['price']

        if buy_size > sell_size:
            # seller changes
            sell['status'] = 'filled'
            sell['size'] = dec('0.00')
            sell['filled_size'] = dec(sell['filled_size'] + sell_size, prec=ROUND_CRYPTO)
            sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (sell_size * price), prec=ROUND_USD)
            # buyer changes
            buy['size'] = dec(buy_size - sell_size, prec=ROUND_CRYPTO)
            buy['filled_size'] = dec(sell_size + buy['filled_size'])
            buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + sell_size, prec=ROUND_CRYPTO)
            filled_size = sell_size
            # Move to completed and delete from main orders list
            self.orders_completed.append(dict(sell))
            self._delete_order(sell)

        elif buy_size < sell_size:
            # seller changes
            sell['size'] = dec(sell_size - buy_size, prec=ROUND_CRYPTO)
            sell['filled_size'] = dec(buy_size + sell['filled_size'])
            sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (buy_size * price), prec=ROUND_USD)
            # buyer changes
            buy['status'] = 'filled'
            buy['size'] = dec('0.00')
            buy['filled_size'] = dec(buy_size + buy['filled_size'], prec=ROUND_CRYPTO)
            buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + buy_size, prec=ROUND_CRYPTO)
            filled_size = buy_size
            self.orders_completed.append(dict(buy))
            self._delete_order(buy)

        else: # equal sizes, both fulfilled
            # seller changes
            sell['status'] = 'filled'
            sell['size'] = dec('0.00')
            sell['filled_size'] = dec(sell['filled_size'] + sell_size, prec=ROUND_CRYPTO)
            sellers_wallet['usd'] = dec(sellers_wallet['usd'] + (sell_size * price), prec=ROUND_USD)
            # buyer changes
            buy['status'] = 'filled'
            buy['size'] = dec('0.00')
            buy['filled_size'] = dec(buy_size + buy['filled_size'], prec=ROUND_CRYPTO)
            buyers_wallet['crypto'] = dec(buyers_wallet['crypto'] + buy_size, prec=ROUND_CRYPTO)
            filled_size = buy_size # or sell_size
            # Move to completed and delete from main order list
            self.orders_completed.append(dict(buy))
            self.orders_completed.append(dict(sell))
            self._delete_order(buy)
            self._delete_order(sell)

        self.user_fills[sell['user']].append({
            'fill_id':user_token(),
            'filled_size':filled_size,
            'price':price,
            'buy_id':buy_id,
            'sell_id':sell_id,
        })
        self.user_fills[buy['user']].append({
            'fill_id':user_token(),
            'filled_size':filled_size,
            'price':price,
            'buy_id':buy_id,
            'sell_id':sell_id,
        })
        self._broadcast({'type':'match', 'message':{
            'size':filled_size,
            'price':price,
            'buy_id':buy_id,
            'sell_id':sell_id,
        }})

    def _match_maker_orders(self):
        """Try to match buys to sells.
        NOTE:
            - self-trade protection is in place
            - buy/sell priority is FIFO
        """
        buys = filter(lambda x: x['status'] == 'open', self.orders['buy'])
        for buy in buys:
            sells = filter(
                lambda x:
                    x['status'] == 'open' and
                    buy['user'] != x['user'] and
                    x['price'] == buy['price'],
                    #(x['price'] == buy['price'] or x['price'] >= buy['price']),
                self.orders['sell']
            )
            for sell in sells:
                self._fulfill_maker_order_match(buy, sell)
        self._calc_market_price()

    def _completed(self, websocket:WebSocketServerProtocol, params:dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        return status_ok('Completed orders.', data=self.orders_completed)

    def _shutdown(self, websocket:WebSocketServerProtocol, params:dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        if not 'secret' in params:
            return status_error('Admin secret required.')
        if self.admin_secret == params['secret']:
            self._broadcast({'type':'shutdown', 'message':'Shutdown command.'})
            # Force a time limit to trigger on next loop
            # This way stats/csv will be dumped
            self.time_limit = 1
            return status_ok('Command accepted. Shutting down.')
        return status_error('Invalid admin secret.')

    def _open_for_business(self, websocket:WebSocketServerProtocol, params:dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        if not 'secret' in params:
            return status_error('Admin secret required.')
        if self.admin_secret == params['secret']:
            self.is_started = True
            self._broadcast({'type':'start', 'message':'Open for business.'})
            return status_ok('Command accepted. Open for business.')
        return status_error('Invalid admin secret.')

    def _pause(self, websocket:WebSocketServerProtocol, params:dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        if not 'secret' in params:
            return status_error('Admin secret required.')
        if self.admin_secret == params['secret']:
            self.is_started = False
            self._broadcast({'type':'pause', 'message':'Server is paused.'})
            return status_ok('Command accepted. Server is paused.')
        return status_error('Invalid admin secret.')

    def _audit(self, websocket:WebSocketServerProtocol, params:dict):
        """Audit for invalid order states. It should return nothing if all is
        working properly."""
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        data = []
        for order in self.orders['buy']:
            if order['status'] != 'open':
                data.append(('ORDER_STATUS_NOT_OPEN:', order))
        for order in self.orders['sell']:
            if order['status'] != 'open':
                data.append(('ORDER_STATUS_NOT_OPEN:', order))
        for order in self.market_orders['buy']:
            if order['status'] != 'open':
                data.append(('ORDER_STATUS_NOT_OPEN:', order))
        for order in self.market_orders['sell']:
            if order['status'] != 'open':
                data.append(('ORDER_STATUS_NOT_OPEN:', order))
        return status_ok('Audit done.', data=data)

    def _buy(self, websocket:WebSocketServerProtocol, params:dict):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated.')
        user = self._get_user(websocket)
        if not 'size' in params or not 'price' in params:
            return status_error('Must size "price" and "size" in params.')
        size = dec(params['size'], prec=ROUND_CRYPTO)
        price = dec(params['price'], prec=ROUND_USD)
        usd = dec(size * price, prec=ROUND_USD)
        if size < MIN_SIZE:
            return status_error(
                'Size must be greater than or equal to %s' % (MIN_SIZE)
            )
        if price < MIN_PRICE:
            return status_error(
                'Price must be greater than or equal to %s' % (MIN_PRICE)
            )
        if price >= self.market_price:
            return status_error(
                'Price must be < market price (%s).' % (self.market_price)
            )
        if usd > self.wallets[user]['usd']:
            return status_error('Not enough USD.')

        # Subtract cost from user's wallet
        self.wallets[user]['usd'] = dec(self.wallets[user]['usd'] - usd, prec=ROUND_USD)
        order = {
            'timestamp':time.time(),
            'id':user_token(),
            'size':size,
            'usd_used':usd,
            'price':price,
            'side':'buy',
            'status':'open', # : open, filled
            'filled_size':dec('0.00'),
            'user':user,
        }
        self.orders['buy'].append(order)
        self._calc_market_price()
        self._broadcast({'type':'buy', 'message':order})
        return status_ok('Buy order placed.', data=order)

    def _cancel(self, websocket, params, user=False):
        if not user and not self._is_authed(websocket):
            return status_error('Must be authenticated to cancel orders.')
        if not 'order_id' in params:
            return status_error('Missing "order_id" in params.')
        if not user:
            user = self.client_user_map[websocket]
        found = False
        for order in self.orders['buy']:
            if order['status'] != 'open':
                continue
            if order['id'] == params['order_id']:
                found = order
                break
        for order in self.orders['sell']:
            if order['status'] != 'open':
                continue
            if order['id'] == params['order_id']:
                if found:
                    raise Exception('Duplicate order ID between buy/sell. Wat?')
                found = order
                break

        if not found:
            return status_error('Order not found: %s' % (params['order_id']))
        else:
            if user != found['user']:
                # Found an order that belongs to a different user. Pretend it
                # doesn't exist.
                return status_error('Order not found.')

        # must return order to wallet and update exchange market_price
        # buy cancel gives back usd
        # sell cancel gives back crypto
        side = found['side']
        user = found['user']
        if side == 'sell':
            self.wallets[user]['crypto'] = dec(
                self.wallets[user]['crypto'] + found['size']
            )
        else:
            usd_calc = found['price'] * found['size']
            self.wallets[user]['usd'] = dec(
                self.wallets[user]['usd'] + usd_calc,
                prec=ROUND_USD
            )

        found['status'] = 'cancel'
        # Move the order to completed list if filled_size > 0, then delete the
        # order in all cases.
        if found['filled_size'] > 0:
            self.orders_completed.append(dict(found))

        if not self._delete_order(found):
            print('NOTICE: Order was not found while attempting to delete.')

        self._calc_market_price()
        self.queue.put(
            jencode({'type':'cancel', 'message':params['order_id'],})
        )
        return status_ok('Order cancelled and removed.')

    def _delete_market_order(self, order):
        key = 'buy'
        if 'sell' in order['side']:
            key = 'sell'

        for i,o in enumerate(self.market_orders[key]):
            if o['id'] == order['id']:
                del(self.market_orders[key][i])
                return True
        return False


    def _delete_order(self, order):
        for i,o in enumerate(self.orders[order['side']]):
            if o['id'] == order['id']:
                del(self.orders[order['side']][i])
                return True
        return False

    def _bcast(self, websocket, params):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated to broadcast messages.')
        if not 'message' in params:
            return status_error('Missing "message" in params.')
        user = self.client_user_map[websocket]
        self.queue.put(
            jencode({'type':'bcast', 'message':params['message'], 'user':user})
        )
        return status_ok('Message broadcasted.')

    def _price(self, websocket, params):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated to get market price.')
        return status_ok('Market price.', data=self.market_price)

    def _get_open_orders(self, websocket):
        orders = []
        u = self.client_user_map[websocket]
        for order in self.orders['buy']:
            if order['user'] == u:
                orders.append(order)
        for order in self.orders['sell']:
            if order['user'] == u:
                orders.append(order)
        return orders

    def _all_orders(self, websocket, params):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated to get open orders.')
        try:
            data = {'maker':[], 'market':[]}
            for order in self.orders['buy']:
                if order['status'] == 'open':
                    data['maker'].append(order)
            for order in self.orders['sell']:
                if order['status'] == 'open':
                    data['maker'].append(order)
            for order in self.market_orders['buy']:
                if order['status'] == 'open':
                    data['market'].append(order)
            for order in self.market_orders['sell']:
                if order['status'] == 'open':
                    data['market'].append(order)
            return status_ok('All orders list.', data=data)
        except Exception as err:
            data = err
        return status_error('ERROR: All orders list.', data=data)

    def _orders(self, websocket, params):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated to get open orders.')
        try:
            user = self.client_user_map[websocket]
            data = {'maker':[], 'market':[]}
            maker = self._get_open_orders(websocket)
            data['maker'] = maker
            for order in self.market_orders['buy']:
                if order['status'] == 'open' and order['user'] == user:
                    data['market'].append(order)
            for order in self.market_orders['sell']:
                if order['status'] == 'open' and order['user'] == user:
                    data['market'].append(order)
            return status_ok('Open orders list.', data=data)
        except Exception as err:
            data = err
        return status_error('ERROR: Open orders list.', data=data)

    def _wallets(self, websocket, params):
        if not self._is_authed(websocket):
            return status_error('Must be authenticated to get wallets.')
        user = self.client_user_map[websocket]
        return status_ok('Wallets.', data=self.wallets[user])

    def _register(self, websocket, params):
        if not 'username' in params:
            return status_error('Missing "username" in params.')
        user = params['username']
        if user in self.users:
            return status_error('User already registered.')
        if self.whitelist and not user in self.whitelist:
            return status_error('User not in whitelist.')
        if self.user_limit and len(self.users) > self.user_limit:
            return status_error('User limit reached (%d)' % (self.user_limit))
        token = user_token()
        self.users[user] = token
        if not user in self.user_fills:
            self.user_fills[user] = []
        self.wallets[user] = {'usd':self.usd_start, 'crypto':self.crypto_start}
        self.client_user_map[websocket] = user
        self.queue.put(
            jencode({'type':'info', 'message':'Registered: %s' % (user)})
        )
        return status_ok('Registered', data=token)

    def _auth(self, websocket, params):
        if not 'username' in params:
            return status_error('Missing "username" in params.')
        if not 'token' in params:
            return status_error('Missing "token" in params.')
        user = params['username']
        token = params['token']
        if not user in self.users:
            return status_error('User is not registered.')
        if params['token'] != self.users[user]:
            return status_error('Authentication failed: Invalid token.')
        self.client_user_map[websocket] = user
        self.queue.put(
            jencode({'type':'info', 'message':'Authenticated: %s' % (user)})
        )
        return status_ok('Authenticated')

    async def _handler(self, websocket):
        """Main server loop"""
        # self.running can be used to gracefully shutdown handlers
        while self.running:
            await asyncio.sleep(0.1)
            if self.time_limit:
                tdiff = time.time() - self.time_start
                if tdiff > self.time_limit:
                    print('Time limit reached. Shutting down...')
                    self.running = False
                    self._broadcast({
                        'type':'shutdown',
                        'message':'Time limit reached. Shutting down.'
                    })
                    # Calculate final holdings for each user
                    # Cancel all orders to return it to wallets
                    final_price = self.market_price
                    csv = '"user","crypto","usd","holdings"\n'
                    for username in self.users.keys():
                        for order in self.orders['buy']+self.orders['sell']+self.market_orders['buy']+self.market_orders['sell']:
                            if order['user'] != username:
                                continue
                            self._cancel(None, {'order_id':order['id']}, user=username)

                        wallet = self.wallets[username]
                        csv += '"{}","{}","{}","{}"\n'.format(
                            username.replace('"', '-'),
                            wallet['crypto'],
                            wallet['usd'],
                            dec(wallet['usd'] + (wallet['crypto']*final_price), prec=ROUND_USD)
                        )

                    self._broadcast({
                        'type':'csv',
                        'message':'Time limit reached. Shutting down.',
                        'data':csv,
                    })
                    print(csv)
                    break

            try:
                message = await websocket.recv()
                data = jdecode(message)
                cmd_type = get_cmd_type(data)
                if not self.is_started and cmd_type and not cmd_type in ('start', 'auth', 'register'):
                    await websocket.send(
                        cmd_error('Server is paused. Wait for admin "start" command.')
                    )
                    continue

                if not cmd_type:
                    await websocket.send(cmd_error('Invalid message'))
                else:
                    try:
                        cmd = self.cmds[cmd_type]
                        (rc, response, data) = cmd(websocket, data['params'])
                        await websocket.send(
                            cmd_fmt(rc, response, data=data)
                        )
                    except Exception as err:
                        tb = traceback.format_exc()
                        print('-'*80, '\n', tb, '\n')
                        await websocket.send(
                            cmd_error('Invalid command: %s. error=%s' % (
                                cmd_type, err))
                        )
                    try:
                        self._match_market_buys()
                        self._match_market_sells()
                        self._match_maker_orders()
                    except Exception as err:
                        tb = traceback.format_exc()
                        print('-'*80, '\n', tb, '\n')
                        await websocket.send(
                            cmd_error('Command error: %s. error=%s' % (
                                cmd_type, err))
                        )

            except:
                # NOTE: To debug, print traceback
                #tb = traceback.format_exc()
                #print('-'*80, '\n', tb, '\n')
                self.clients.remove(websocket)
                try:
                    del(self.client_user_map[websocket])
                except:
                    # TODO:
                    # Sometimes the client_user_map doesn't contain websocket
                    # yet? Race condition?
                    # NOTE: To debug, print traceback
                    #tb = traceback.format_exc()
                    #print('-'*80, '\n', tb, '\n')
                    pass
                break

    async def handler(self, websocket, path):
        """Event loop handler wrapper"""
        self.clients.add(websocket)
        client_ip, client_port = getattr(websocket, 'remote_address', None)
        self._broadcast({
            'type':'info',
            'message':'New connection from %s:%s' % (client_ip, client_port)
        })
        try:
            await self._handler(websocket)
        except:
            tb = traceback.format_exc()
            print('-'*80, '\n', tb, '\n')

    def start(self):
        """Start the server"""
        ssl_context = None
        if self.pem_file:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(self.pem_file)
            if not self.ssl_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
        asyncio.set_event_loop(asyncio.new_event_loop())
        start_server = websockets.serve(
            self.handler, self.bind, self.port, ssl=ssl_context
        )
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

class CxServer:
    def __init__(self,
            exchange_port: int = 9877,
            feed_port: int = 9876,
            bind: str = '0.0.0.0',
            time_limit: int = None,
            user_limit: int = None,
            usd_start: Decimal = dec('10000.00'),
            crypto_start: Decimal = dec('10.0'),
            whitelist: set = None,
            pem_file: str = None,
            ssl_verify: bool = True,
            admin_secret: str = 'admin',
            is_started: bool = True):
        self.exchange_port = exchange_port
        self.feed_port = feed_port
        self.bind = bind
        self.time_limit = time_limit
        self.user_limit = user_limit
        self.usd_start = dec(usd_start)
        self.crypto_start = dec(crypto_start)
        self.whitelist = whitelist
        self.pem_file = pem_file
        self.ssl_verify = ssl_verify
        self.admin_secret = admin_secret
        self.is_started = is_started

    def start(self):
        feed = CxFeed(
            port=self.feed_port,
            bind=self.bind,
            pem_file=self.pem_file,
            ssl_verify=self.ssl_verify,
        )
        exchange = CxExchange(
            port=self.exchange_port,
            bind=self.bind,
            time_limit=self.time_limit,
            user_limit=self.user_limit,
            usd_start=self.usd_start,
            crypto_start=self.crypto_start,
            whitelist=self.whitelist,
            admin_secret=self.admin_secret,
            pem_file=self.pem_file,
            ssl_verify=self.ssl_verify,
            is_started=self.is_started,
        )
        t1 = threading.Thread(target=feed.start)
        t2 = threading.Thread(target=exchange.start)
        t1.start()
        t2.start()
        for t in (t1, t2):
            t.join()

def main():
    """Provides the command line util 'cxserve'
    """
    parser = argparse.ArgumentParser(description='cxgame server')
    parser.add_argument(
        '-e',
        '--exchangeport',
        dest='exchangeport',
        default=9877,
        type=int,
        help='Exchange server listen port.'
    )
    parser.add_argument(
        '-f',
        '--feedport',
        dest='feedport',
        default=9876,
        type=int,
        help='Feed server listen port.'
    )
    parser.add_argument(
        '-b',
        '--bindaddr',
        dest='bindaddr',
        default='0.0.0.0',
        type=str,
        help='The address to listen on.'
    )
    parser.add_argument(
        '-t',
        '--timelimit',
        dest='timelimit',
        default=None,
        type=int,
        help='Time limit that the exchange is open (in seconds).'
    )
    parser.add_argument(
        '-u',
        '--userlimit',
        dest='userlimit',
        default=None,
        type=int,
        help='Max number of registered users.'
    )
    parser.add_argument(
        '-m',
        '--usdstart',
        dest='usdstart',
        default=Decimal('10000.00'),
        type=Decimal,
        help='Amount of USD each user starts with.'
    )
    parser.add_argument(
        '-c',
        '--cryptostart',
        dest='cryptostart',
        default=Decimal('10.0'),
        type=Decimal,
        help='Amount of cryptocurrency each user starts with.'
    )
    parser.add_argument(
        '-w',
        '--whitelist',
        dest='whitelist_path',
        default=None,
        type=str,
        help='Path to newline separated list of whitelisted usernames.',
    )
    parser.add_argument(
        '-a',
        '--adminsecret',
        dest='adminsecret',
        default='admin_admin',
        type=str,
        help='The server admin password.'
    )
    parser.add_argument(
        '-p',
        '--pemfile',
        dest='pemfile',
        default=None,
        type=str,
        help='Path to SSL/TLS PEM file (enables SSL/TLS mode).'
    )
    parser.add_argument(
        '-s',
        '--sslverify',
        dest='sslverify',
        default='yes',
        type=str,
        help='Verify SSL certs (yes|no).',
    )
    parser.add_argument(
        '-i',
        '--started',
        dest='started',
        default='yes',
        type=str,
        help='Tells the server to accept commands or not (yes|no). If False, server is still able to register users. Useful for waiting for all users to connect before game starts.'
    )
    args = parser.parse_args()
    if args.whitelist_path:
        try:
            whitelist = open(args.whitelist_path).read().strip().split('\n')
        except Exception as err:
            print(err)
            exit(1)
    else:
        whitelist = None
    if args.pemfile and not os.path.exists(args.pemfile):
        print('ERROR: Could not find pem file path "{}"'.format(args.pemfile))
        exit(1)
    if args.adminsecret == 'admin_admin':
        print('WARNING: Default admin password in use!')
    if args.feedport == args.exchangeport:
        print('ERROR: feedport and exchangeport cannot be the same.')
        exit(1)
    if not args.sslverify in ('yes', 'no'):
        print('ERROR: sslverify must be "yes" or "no".')
        exit(1)
    if not args.started in ('yes', 'no'):
        print('ERROR: started must be "yes" or "no".')
        exit(1)
    cxs = CxServer(
        exchange_port=args.exchangeport,
        feed_port=args.feedport,
        bind=args.bindaddr,
        time_limit=args.timelimit,
        user_limit=args.userlimit,
        usd_start=args.usdstart,
        crypto_start=args.cryptostart,
        whitelist=whitelist,
        admin_secret=args.adminsecret,
        pem_file=args.pemfile,
        ssl_verify=args.sslverify,
        is_started=args.started,
    )
    cxs.start()
