# cxgame: A Cryptocurrency Exchange Game

cxgame is a fake cryptocurrency exchange that has a few goals in mind:
1. Educational: Learn or test out new programmatic trading strategies.
2. A game: Battle other bots to test your skills.

# Components

cxgame has 4 primary components:
1. `cxgame.server.CxExchange` -- The exchange server
2. `cxgame.server.CxFeed` -- The broadcast channel. Exchange activity is
    broadcasted to all connected clients here (e.g. orders, server messages)
3. `cxgame.client.CxClient` -- The API for creating your own client to
    communicate with the CxExchange server.
4. `cxgame.server.CxServer` -- Wraps and controls `CxExchange` and `CxFeed`.

cxgame can run in various modes (time limit, endless, whitelisted users, etc).
See the documentation below for server and client examples. Also take a look
at the `examples/` directory for more information.

# Contributing

If you find missing features or bugs, please open an issue or a pull
request.

# Install

No PyPI package as of yet. Install using:
1. `python3 -m venv  venv`
2. `source venv/bin/activate`
3. `pip install -r requirements.txt`
4. `python setup.py install`

After install, the command `cxserve` will be available. Running it starts the
exchange and feed servers with default options (see: `cxgame.server.main()`).

# The Exchange & Feed Servers (cxgame.server.CxServer)

The primary websocket servers that run the exchange and broadcast feed:

1. Registration and authentication. Stores user credentials.
2. Stores user wallets (USD and crypto).
3. Sets the (mid) market price.
4. Handles limit orders (buy, sell, cancel).
5. Handles market orders (buy & sell at market price).
6. Stores past completed order detail.
7. Stores past filled orders (order matches).
8. Sends information on the feed channel to broadcast messages to clients.

## Init Options

`CxServer()` __init__ options:

* exchange_port -- Websocket `CxExchange` listen port.
  default: 9877 (int)

* feed_port -- Websocket `CxFeed` listen port.
  default: 9876 (int)

* bind -- Address(es) to listen on.
  default: 0.0.0.0 (str)

* usd_start -- New users will start with this much USD in their wallet.
  default: 10000.00 (Decimal, int, str, or float. Auto-converts to Decimal.)

* crypto_start -- New users will start with this much crypto in their wallet.
  default: 10.0 (Decimal, int, str, or float. Auto-converts to Decimal.)

* user_limit -- The max amount of users allowed to connect.
  default: None (int)

* time_limit -- Exchange will run for this amount of time (in seconds).
  default: None (int)

* whitelist -- A whitelist of users allowed to connect. All users must be
  connected before the exchange will run.
  default: None (list[str])

* pem_file -- Path to SSL key/cert file.
  default: None (str)

* ssl_verify -- Specify if SSL connections/certs are verified (set to False for
  self signed).
  default: True (bool)

* admin_secret -- The admin password. Required to run certain commands like
  shutdown.
  default: admin (str)

* is_started -- Tells the server to accept commands or not. If False, commands
  are rejected until the 'start' command is issued.
  default: True (bool)

NOTE: `CxServer` is a wrapper that passes down options to `CxExchange` and
`CxFeed`.

## Running A Server

The command `cxserve` can be used to launch the exchange & feed server threads
and comes with command line option parsing.

To manually run a server, it can be done a few ways. Look at
`examples/server.py` for a more in-depth example.

# Exchange and Client Commands

The following is a list and example of the exchange server's commands. These
are also implemented on the client side `CxClient`, as shown in the examples.

NOTE: The response is a `Response()` class from `cxgame.client.Response`. It
contains these variables:
1. status -- True or False
2. msg -- Free text response. Helpful for debugging errors.
3. data -- The data line. It has a varying type in the response and depends on
   the type method that was called.
4. raw -- The raw json string returned from the server. For debugging purposes.

## What is the `r()` Helper Method?

The `CxClient.r()` helper method is a shortcut that wraps `websockets.connect`
and is short for `run`.

It does create a new connection on every call, so not ideal for long running
clients and defeats the purpose of a websocket, but useful for testing or
demonstration purposes. See the `cxgame/client.py` source code `r()` and
`runcmd()` methods for more explanation.

## register
Register a new user on the exchange. The response will contain a token for
future authentication.

```python
from cxgame.client import CxClient
```

```python
cx = CxClient(user='new-username123', uri='ws://mtingers.com:9877')
response = cx.r('register')
print(response.status, response.msg)

# If successful, store the token for later auth
if response.status:
    token = response.data

```

## auth
```python
cx = CxClient(user='root', uri='ws://mtingers.com:9877', token='123...')
response = cx.r('auth')
```

## bcast
Broadcasts a message on the feed server:
```python
response = cx.r('broadcast', 'Hello, World!')
```

## buy
Places a maker limit buy order:
```python
price = '999.99'
size = '1.5'
response = cx.r('buy', price, size)
print('order:', response.data)
```

## buy_market
Places a market buy order. This attempts to match limit sell orders that are
the closest in price at the time of the market order:
```python
amount = '999.99' # The amount of your wallet's USD to use for this buy.
response = cx.r('buy_market', amount)
print('order:', response.data)
```

## sell
Places a maker limit sell order:
```python
price = '1000.01'
size = '1.5'
response = cx.r('sell', price, size)
```

## sell_market
Places a market sell order. This attempts to match limit buy orders that are
the closest in price at the time of the market order:
```python
amount = '2.25' # The amount of your wallet's crypto to use for this sell.
response = cx.r('sell_market', amount)
```

## price
```python
mid_market_price = cx.r('price').data
```

## orders
Get your open orders:
```python
my_orders = cx.r('orders').data
for order in my_orders:
    print('id={} price={}'.format(order['id'], order['price']))
```

## all_orders
Get all open orders (all users):
```python
all_orders = cx.r('all_orders').data
for order in all_orders:
    print('user={} id={} price={}'.format(
        order['user'], order['id'], order['price'])
    )
```

## wallets
Get your current wallets for USD and crypto:
```python
wallets = cx.r('wallets').data
print('crypto={} usd={}'.format(wallets['crypto'], wallets['usd']))
```

## cancel
Cancel an order, by order ID:
```python
cancelled = cx.r('cancel', order_id)
```

## fills
Get your fills. This is orders that were matched partially or full:
```python
my_fills = cx.r('fills').data
for fill in my_fills:
    print(fill)
```

## completed
Get your completed orders. These are orders that were completed/filled.
```python
my_completed_orders = cx.r('completed').data
for order in my_completed_orders:
    print(order)
```
## audit
For debugging and admin use. Runs an audit on all order status to detect bugs
in the code (invalid states).

## shutdown
```python
cx = CxClient(user='root', uri='ws://mtingers.com:9877', token='123...')
response = cx.r('auth')
response = cx.r('shutdown', 'adminpassword123')
```

## start
```python
cx = CxClient(user='root', uri='ws://mtingers.com:9877', token='123...')
response = cx.r('auth')
response = cx.r('start', 'adminpassword123')
```

## pause
```python
cx = CxClient(user='root', uri='ws://mtingers.com:9877', token='123...')
response = cx.r('auth')
response = cx.r('pause', 'adminpassword123')
```

# Test Servers

An open test exchange is running at: `ws://mtingers.com:9877`
The feed for this server is at: `ws://mtingers.com:9876`


# TODO

1. Add admin user auth
2. Finish mypy typing
3. Finish docstrings
4. Add logging
5. Add state saving
6. Add tests
7. Add PyPI
8. Add server CLI arg parsing
