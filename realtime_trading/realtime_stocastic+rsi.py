import ccxt 
import time
import datetime
import pandas as pd
import math
import get_sto_rsi

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
symbol_upbit = "KRW-BTC"
balance = binance.fetch_balance()
usdt = balance['total']['USDT']
op_mode = True
position = {
    "type" : None,
    "amount" : 0
}

def cal_amount(usdt_balance, cur_price):
    portion = 0.1
    usdt_trade = usdt_balance * portion
    amount = math.floor((usdt_trade*1000000)/cur_price) / 1000000
    return amount

def enter_position(exchange, symbol, amount, position): # 포지션 진입 함수
    stocasitc = get_sto_rsi.get_cur_stocatsic(symbol_upbit)
    rsi = get_sto_rsi.get_cur_rsi(symbol_upbit)
    if (stocasitc <= 20) and rsi <= 50\
        and rsi >= 40: # 롱 진입
        position['type'] = 'long'
        position['amount'] = amount
        exchange.create_market_buy_order(symbol=symbol,amount=amount)
    elif (stocasitc >= 80) and rsi <= 50\
        and rsi >= 40: # 숏 진입
        position['type'] = 'short'
        position['amount'] = amount
        exchange.create_market_sell_order(symbol=symbol,amount=amount)

        
def exit_position(exchange, symbol, position): # 포지션 종료
    amount = position['amount']
    if position['type'] == 'long': #롱이면 매도,  숏이면 매수
        exchange.create_market_sell_order(symbol=symbol,amount=amount)
        position['type'] = None    
    elif position['type'] == 'short':
        exchange.create_market_buy_order(symbol=symbol,amount=amount)
        position['type'] = None #포지션 종료 후 type을 None, 즉 무포지션으로 변경

while True: 
    now = datetime.datetime.now()
    stocasitc = get_sto_rsi.get_cur_stocatsic(symbol_upbit)
    rsi = get_sto_rsi.get_cur_rsi(symbol_upbit)
    
    if stocasitc >= 80 and rsi <= 50 and rsi >= 40:
        if op_mode and position['type'] == 'long':
            exit_position(binance, symbol, position)
            time.sleep(2)
            balance = binance.fetch_balance() #잔고업데이트
            usdt = balance['total']['USDT']
            op_mode = True
    if stocasitc <= 20 and rsi <= 50 and rsi >= 40:
        if op_mode and position['type'] == 'short':
            exit_position(binance, symbol, position)
            time.sleep(2)
            balance = binance.fetch_balance()
            usdt = balance['total']['USDT']
            op_mode = True         # 포지션 정리 후 포지션 진입 가능

    ticker = binance.fetch_ticker(symbol)
    cur_price = ticker['last']
    amount = cal_amount(usdt, cur_price)
    
    if op_mode and position['type'] is None:
        enter_position(binance, symbol, amount, position)
        if position['type'] is not None:  # 포지션 정리 전까지는 다시 포지션 진입하지 않음
            op_mode = False
            
    print(now, cur_price)
    time.sleep(1)