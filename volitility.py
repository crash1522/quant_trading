import ccxt 
import time
import datetime
import pandas as pd
import larry
import math


with open("api.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip()
    secret  = lines[1].strip()

binance = ccxt.binance(config={
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

symbol = "BTC/USDT"
long_target = larry.cal_target(binance, symbol)
balance = binance.fetch_balance()
usdt = balance['total']['USDT']
op_mode = False # 맨 처음에는 무포지션
position = {
    "type" : None,
    "amount" : 0
}

def cal_amount(usdt_balance, cur_price):
    portion = 0.1
    usdt_trade = usdt_balance * portion
    amount = math.floor((usdt_trade*1000000)/cur_price) / 1000000
    return amount

def enter_position(exchange, symbol, cur_price, long_target, short_target, amount, position): # 포지션 진입 함수
    if cur_price > long_target: # 롱 진입
        position['type'] = 'long'
        position['amount'] = amount
        exchange.create_market_buy_order(symbol=symbol,amount=amount)

    elif cur_price < short_target: # 숏 진입
        position['type'] = 'short'
        position['amount'] = amount
        exchange.create_market_sell_order(symbol=symbol,amount=amount)

def exit_position(exchange, symbol, position): # 포지션 종료
    amount = position['amount']
    if position['type'] == 'long': #롱이면 매도,  숏이면 매수
        exchange.create_market_sell_order(symbol=symbol,amount=amount)    
    elif position['type'] == 'short':
        exchange.create_market_buy_order(symbol=symbol,amount=amount)
    position['type'] = None #포지션 종료 후 type을 None, 즉 무포지션으로 변경



while True: 
    now = datetime.datetime.now()

    if now.hour == 8 and now.minute == 50 and (0 <= now.second < 10):
        if op_mode and position['type'] is not None:
            exit_position(binance, symbol, position)
            op_mode = False         # 9시 까지는 다시 포지션 진입하지 않음 
            # 8시 50분에 팔았는데, 5type이 None이니까 다시 진입하게 됨

    # udpate target price
    if now.hour == 9 and now.minute == 0 and (20 <= now.second < 30):
        long_target, short_target = larry.cal_target(binance, symbol)
        balance = binance.fetch_balance()
        usdt = balance['total']['USDT']
        op_mode = True 
        time.sleep(10)

    ticker = binance.fetch_ticker(symbol)
    cur_price = ticker['last']
    amount = cal_amount(usdt, cur_price)

    if op_mode and position['type'] is None:
        enter_position(binance, symbol, cur_price, long_target, short_target, amount, position)

    print(now, cur_price)
    time.sleep(1)