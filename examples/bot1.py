import time
from random import uniform, randint
from cxgame.client import *

def main():
    cx = CxClient(uri='ws://mtingers.com:9877')
    user = client.random_username()
    print('using username:', user)

    while 1:
        # Random numbers for buys/sells
        r1 = dec(uniform(0.01, 10.5))
        r2 = dec(uniform(0.01, 10.5))
        r3 = dec(uniform(0.00025, 0.75))

        # Limit buy
        price = cx.r('price').data
        response = cx.r('buy', price-r1, r3)
        print(response.status, response.msg, response.data)
        time.sleep(uniform(0.5, 3.5))

        # Limit sell
        price = cx.r('price').data
        response = cx.r('sell', price+r2, r3)
        print(response.status, response.msg, response.data)
        time.sleep(uniform(0.5, 3.5))

        # Random buy/sell market price
        response = cx.r('sell_market', uniform(0.02, 0.5))
        response = cx.r('buy_market', uniform(20.0, 100.0))

        # Randomly cancel orders
        if randint(0, 50) == 25:
            # cancel some orders
            orders = cx.r('orders').data
            for order in orders['maker']:
                cx.r('cancel', order['id'])
            for order in orders['market']:
                cx.r('cancel', order['id'])

        # Getting other info
        my_open_orders = await cx.orders().data
        my_wallets = await cx.wallets().data
        my_fills = await cx.fills().data
        my_completed_order_detail = await cx.completed().data
        mid_market_price = await cx.price().data

        # Broadcast a message on the feed server
        await cx.broadcast('Hello, World!')

if __name__ == '__main__':
    main()

