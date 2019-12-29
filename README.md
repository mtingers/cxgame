# cxgame
cxgame -- A Cryptocurrency Exchange Game

The purpose of cxgame is to battle other players on a fake cryptocurrency
exchange. The winner is decided by who has the most holdings after a time limit
is reached or the server receives the admin shutdown command. Each player
writes their own code using the `cxgame.client` module.

cxgame can run in various modes (time limit, endless, whitelisted users, etc).
See the documentation below for server and client examples. Also take a look
at the `examples/` directory for more information.

# Websocket Server Options (CxCmd)

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

* pem_file -- Path to SSL certificate key/cert file.
  default: None

* ssl_verify -- Specify if SSL connections/certs are verified (set to False for
  self signed).
  default: True

Example server, manually start feed and cmd websocket servers:
```python
threads = []
feed_server = server.CxFeed()
cmd_server = server.CxCmd(time_limit=300) # Shuts down after 5 minutes
th1 = threading.Thread(target=feed_server.start)
th2 = threading.Thread(target=cmd_server.start)
th1.start()
th2.start()
threads.append(th1)
threads.append(th2)
for t in threads:
    t.join()
```


# Example Client
```python
from cxgame.client import *

uri = "ws://localhost:9877"
async with websockets.connect(uri) as websocket:
    username = 'bot-'+str(random.randint(0,1000000000))
    cmd = CxCmdClient(user=username, websocket=websocket)
    # Register the username
    x = await cmd.register()
    token = x['data'] # This is the token for future auth

    # Limit buy
    x = await cmd.buy('999.99', '1.321')
    print(x)
    # Cancel limit buy
    await cmd.cancel(x['data']['id'])

    # Market value sell (tries to match closest limit orders)
    x = await cmd.sell_market('2.25')
    print(x)
    
    # Getting other info
    my_open_orders = await cmd.orders()
    my_wallets = await cmd.wallets()
    my_fills = await cmd.fills()
    my_completed_order_detail = await cmd.completed()
    mid_market_price = await cmd.price()
```
