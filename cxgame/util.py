import time
import random
import hashlib
import json
from typing import Tuple, Union, Any, Dict, Optional
from decimal import *

# Crypto max size is 32 - 10 (10 decimals) number characters
getcontext().prec = 32

# Rounding for crypto and usd
ROUND_CRYPTO = Decimal('0.0000000000')
ROUND_USD = Decimal('0.00')

# Minimums for crypto size and price (for orders: buys/sells)
MIN_SIZE = Decimal('0.00000001')
MIN_PRICE = Decimal('0.1')
MIN_AMOUNT = Decimal('10.00')

def mean(l):
    if not l or len(l) < 2:
        return l
    return sum(l) / len(l)

def shuffle2(l:list) -> list:
    """Copy then shuffle (not in-place shuffle)"""
    x = list(l)
    random.shuffle(x)
    return x

class DecimalEncoder(json.JSONEncoder):
    """Makes it so json.dumps(x, cls=DecimalEncoder) can handle Decimal"""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def dec_rnd(
        s: Union[int, str, float, Decimal],
        prec: Decimal=ROUND_CRYPTO,
        rounding=ROUND_HALF_EVEN) -> Decimal:
    return Decimal(s).quantize(prec, rounding=rounding)

def dec(s, prec: Decimal=None, rounding=ROUND_HALF_EVEN) -> Decimal:
    if prec is not None:
        return dec_rnd(str(s), prec=prec, rounding=rounding)
    return Decimal(str(s))

def dec_str(s: Union[int, float, str]) -> str:
    """Convert a string, int, or float to string, then to decimal, then back to
    a string. This avoids floating point innacuracies when passing in floats
    to other methods.
    """
    return str(Decimal(str(s)))

def status_error(msg: str, data: Any=None) -> Tuple[bool, str, Optional[Dict[Any, Any]]]:
    return (False, msg, data)

def status_ok(msg: str, data: Any=None) -> Tuple[bool, str, Optional[Dict[Any, Any]]]:
    return (True, msg, data)

def cmd_fmt(status: bool, msg: str, data: Any=None) -> str:
    response = {
        'status':status,
        'message':msg,
        'data':data,
    }
    return json.dumps(response, cls=DecimalEncoder)

def cmd_error(msg, data=None):
    return cmd_fmt(False, msg, data=data)

def cmd_ok(msg, data=None):
    return cmd_fmt(True, msg, data=data)

CMDS = (
    'register',
    'auth',
    'bcast',
    'buy',
    'buy_market',
    'sell',
    'sell_market',
    'cancel',
    'price',
    'orders',
    'all_orders',
    'wallets',
    'fills',
    'completed',
    'audit',
    'shutdown',
)

def get_cmd_type(data):
    if not 'cmd' in data:
        return False
    c = data['cmd']
    if not c in CMDS:
        return False
    if not 'params' in data:
        return False
    return c

def jdecode(msg):
    #print('decode:', msg)
    try:
        return json.loads(msg)
    except Exception as err:
        print('EDECODE:', err)
        return False

def jencode(msg):
    return json.dumps(msg, cls=DecimalEncoder)

def user_token():
    r1 = str(random.getrandbits(256))
    r2 = str(time.time())
    r = (r1+r2).encode('utf-8')
    return hashlib.sha256(r).hexdigest()
