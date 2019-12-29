import time
from random import uniform, randint
from cxgame.client import *
import cxgame.client
cxgame.client.TEST_URI = 'ws://mtingers.com:9877'

def main():
    while 1:
        p = m('price')
        r = uniform(0.01, 10.5)
        m('buy', float(p)-r, uniform(0.00025, 0.75))
        p = m('price')
        r = uniform(0.01, 10.5)
        m('sell', float(p)+r, uniform(0.00025, 0.75))
        time.sleep(uniform(0.5, 3.5))
        m('sell_market', uniform(0.02, 0.5))
        time.sleep(uniform(0.5, 3.5))
        m('buy_market', uniform(20.0, 100.0))
        time.sleep(uniform(0.1, 1.0))
        if randint(0, 50) == 25:
            print('-'*80)
            print('CANCEL')
            # cancel some orders
            orders = m('orders')
            for order in orders['maker']:
                m('cancel', order['id'])
            for order in orders['market']:
                m('cancel', order['id'])
            time.sleep(randint(2, 5))
        time.sleep(randint(1, 5))

if __name__ == '__main__':
    main()

