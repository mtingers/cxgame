# cxgame -- A Cryptocurrency Exchange Game

cxgame is a fake cryptocurrency exchange that has a few goals in mind:
1. Educational: Learn or test out new programmatic trading stategies.
2. A game: Battle other bots to test your skills.

cxgame has 3 primary components:
1. `cxgame.server.CxExchange` -- The exchange server
2. `cxgame.server.CxFeed` -- The broadcast channel. Exchange activity is
    broadcasted to all connected clients here (e.g. orders, server messages)
3. `cxgame.client.CxClient` -- The API for creating your own client to
    communicate with the CxExchange server.

cxgame can run in various modes (time limit, endless, whitelisted users, etc).
See the documentation below for server and client examples. Also take a look
at the `examples/` directory for more information.

# Contributing

If you find missing features or bugs, please open an issue or send pull
requests.

# Install

No PyPI package as of yet. Install using:
1. `python3 -m venv  venv`
2. `source venv/bin/activate`
3. `pip install -r requirements.txt`
4. `python setup.py install`

# The Exchange Server (cxgame.server.CxExchange)

The primary websocket server that runs the exchange:

1. Registration and authentication. Stores user credentials.
2. Stores user wallets (USD and crypto).
3. Sets the (mid) market price.
4. Handles limit orders (buy, sell, cancel).
5. Handles market orders (buy & sell at market price).
6. Stores past completed order detail.
7. Stores past filled orders (order matches).
8. Sends information to the feed server to broadcast messages.

## Exchange Init Options

`CxExchange()` init options:

* port -- Websocket listen port.
  default: 9877

* bind -- Address(es) to listen on.
  default: 0.0.0.0

* usd_start -- New users will start with this much USD in their wallet.
  default: 10000.00

* crypto_start -- New users will start with this much crypto in their wallet.
  default: 10.0

* user_limit -- The max amount of users allowed to connect.
  default: None

* time_limit -- Exchange will run for this amount of time (in seconds).
  default: None

* whitelist -- A whitelist of users allowed to connect. All users must be
  connected before the exchange will run.
  default: None

* pem_file -- Path to SSL key/cert file.
  default: None

* ssl_verify -- Specify if SSL connections/certs are verified (set to False for
  self signed).
  default: True

## Commands

The following is a list and example of the exchange server's commands. These
are also implemented on the client side `CxClient`, as shown in the examples.

NOTE: The response is a `Response()` class from `cxgame.client.Response`. It
contains these variables:
1. status -- True or False
2. msg -- Free text response. Helpful for debugging errors.
3. data -- The data line. It has a varying type in the response and depends on
   the type method that was called.
4. raw -- The raw json string returned from the server. For debugging purposes.

### register
Register a new user on the exchange. The response will contain a token for
future authentication.

```python
cx = CxClient(user='new-username123', websocket=websocket)
response = cx.r('register')
print(response.status, response.message)

# If successful, store the token for later auth
if response.status:
    token = response.data

```

### auth
### bcast
### buy
### buy_market
### sell
### sell_market
### price
### orders
### all_orders
### wallets
### cancel
### fills
### completed
### audit


# TODO

1. Add admin user auth
2. Add admin start and shutdown command. Reject commands until game starts.
3. Finish mypy typing
4. Finish docstrings
5. Add logging
6. Add state saving
7. Finish user_limit
8. Add tests
9. Add PyPI
10. Add server CLI arg parsing
