import ccxt 
import time
import datetime
import pandas as pd
import math
from supertrend import supertrendcloud
from collections import deque

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
    portion = 0.8
    usdt_trade = usdt_balance * portion
    amount = math.floor((usdt_trade*1000000)/cur_price) / 1000000
    return amount

def enter_position(exchange, cur_price, symbol, amount, position, trend_5_7, trend_12_8): # 포지션 진입 함수 
    if trend_5_7 <= cur_price and trend_12_8 <= cur_price: # 롱 진입
        position['type'] = 'long'
        position['amount'] = amount
        exchange.create_market_buy_order(symbol=symbol,amount=amount)
        print("롱 포지션 매수")
    elif trend_5_7 >= cur_price and trend_12_8 >= cur_price:
        position['type'] = 'short'
        position['amount'] = amount
        exchange.create_market_sell_order(symbol=symbol,amount=amount)
        print("숏 포지션 매수")
        
def exit_position(exchange, symbol, position): # 포지션 종료 
    amount = position['amount']
    if position['type'] == 'long': #롱이면 매도,  숏이면 매수
        exchange.create_market_sell_order(symbol=symbol,amount=amount)
        position['type'] = None
        print("롱 포지션 매도")    
    elif position['type'] == 'short':
        exchange.create_market_buy_order(symbol=symbol,amount=amount)
        position['type'] = None #포지션 종료 후 type을 None, 즉 무포지션으로 변경
        print("숏포지션 매도")
        
def time_condition_4h():
    now = datetime.datetime.now()
    hour = [1,5,9,13,17,21]  
    for i in hour:
        if now.hour == i and now.minute ==0 and (0 <= now.second <= 59):
            return True
    return False

def renew_stc(symbol):        
    btc = binance.fetch_ohlcv(
        symbol = symbol,
        timeframe = '4h',
        since = None,
        limit = 20
    )

    df = pd.DataFrame(
        data = btc,
        columns=['datetime', 'open', 'high', 'low', 'close', 'volume']      
    )
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)

    stc = supertrendcloud(df,5,12,7,8)
    trend1 = stc['trend_5_7']
    trend2 = stc['trend_12_8']
    
    return trend1.iloc[-1], trend2.iloc[-1]

while True: 
    
    if time_condition_4h():
        ticker = binance.fetch_ticker(symbol)
        cur_price = ticker['last']
        amount = cal_amount(usdt, cur_price)
        trend_5_7, trend_12_8 = renew_stc(symbol)
        
        if trend_5_7 >= cur_price and trend_12_8 <= cur_price:
            if op_mode == False and position['type'] == 'long':
                exit_position(binance, symbol, position)
                time.sleep(2)
                balance = binance.fetch_balance() #잔고업데이트
                usdt = balance['total']['USDT']
                op_mode = True
        if trend_5_7 <= cur_price and trend_12_8 >= cur_price:
            if op_mode == False and position['type'] == 'short':
                exit_position(binance, symbol, position)
                time.sleep(2)
                balance = binance.fetch_balance()
                usdt = balance['total']['USDT']
                op_mode = True         # 포지션 정리 후 포지션 진입 가능

        if op_mode and position['type'] is None:
            enter_position(binance, cur_price ,symbol, amount, position, trend_5_7, trend_12_8)
            if position['type'] is not None:  # 포지션 정리 전까지는 다시 포지션 진입하지 않음
                op_mode = False
        
        now = datetime.datetime.now()        
        print(now, cur_price)
    else:
        time.sleep(60)
        continue

