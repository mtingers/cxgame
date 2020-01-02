import time
from random import uniform, randint
from cxgame.client import *

def main():
    cx = CxClient(uri='ws://mtingers.com:9877')
    user = cx.random_username()
    cx.user = user
    token = cx.r('register').data
    print('using username:', user)
    print('token:', token)

    while 1:
        # Random numbers for buys/sells
        r1 = dec(uniform(0.01, 20.5))
        r2 = dec(uniform(0.01, 20.5))
        r3 = dec(uniform(0.00025, 0.75))

        # Limit buy
        price = cx.r('price').data
        response = cx.r('buy', price-r1, r3)
        print(response)
        #time.sleep(uniform(0.5, 3.5))

        # Limit sell
        price = cx.r('price').data
        response = cx.r('sell', price+r2, r3)
        print(response)

        # Random buy/sell market price
        response = cx.r('sell_market', uniform(0.02, 0.5))
        response = cx.r('buy_market', uniform(20.0, 100.0))

        # Randomly cancel orders
        if randint(0, 50) == 2:
            # cancel some orders
            orders = cx.r('orders').data
            for order in orders['maker']:
                cx.r('cancel', order['id'])
            for order in orders['market']:
                cx.r('cancel', order['id'])

        # Getting other info
        #my_open_orders = cx.r('orders').data
        #my_wallets = cx.r('wallets').data
        #my_fills = cx.r('fills').data
        #my_completed_order_detail = cx.r('completed').data
        #mid_market_price = cx.r('price').data

        # Broadcast a message on the feed server
        #cx.r('broadcast', 'Hello, World!')
        #time.sleep(0.2)

if __name__ == '__main__':
    main()
