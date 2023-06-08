import ccxt 
import time
import datetime
import pandas as pd
import math
from supertrend import supertrendcloud
from collections import deque

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

    elif trend_5_7 >= cur_price and trend_12_8 >= cur_price:
        position['type'] = 'short'
        position['amount'] = amount
        exchange.create_market_sell_order(symbol=symbol,amount=amount)
        
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

def renew_stc(symbol, binance):        
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


