import ccxt
import numpy as np
import pandas as pd
import pybithumb
 
#binance = ccxt.binance()
#btc_ohlcv = binance.fetch_ohlcv("BTC/USDT","4h")

def get_ror(k):

   #df = pybithumb.get_ohlcv('BTC')
   df = pd.read_excel(f"KRW-BTC_1days.xlsx", index_col=0)
   #df = pd.DataFrame(btc_ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])

   df['range'] = (df['high'] - df['low'])*k
   df['long_target'] = df['open'] + df['range'].shift(1)
   df['short_target'] = df['open'] - df['range'].shift(1)

   fee = 0.05
   df['long_ror'] = np.where(df['high'] > df['long_target'] , df['close'] / df['long_target'] - fee , 1)
   df['short_ror'] = np.where(df['low'] < df['short_target'] , df['short_target'] / df['close'] - fee , 1)
   return round(df['long_ror'].cumprod()[-2],-10) , round(df['short_ror'].cumprod()[-2],-10)

for k in np.arange(0.1 ,1.0 , 0.1):
    ror = get_ror(k)  
    print(ror)
