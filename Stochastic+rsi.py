import pybithumb
import pyupbit
import pandas as pd 
import numpy as np
import pandas as pd
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def get_ohlcv(ticker):
    dfs = [ ]
    df = pyupbit.get_ohlcv(ticker, interval="minute240")
    dfs.append(df)
    for i in range(50):
        df = pyupbit.get_ohlcv(ticker, interval="minute240", to = df.index[0]) #to: 출력할 max date time을 지정
        dfs.append(df)
        time.sleep(0.2) #한 번에 너무 많은 데이터를 요청하면 웹서버에서 차단할 수 있음

    df = pd.concat(dfs) #list안에 있는 데이터프레임을 하나로 합쳐줌
    df = df.sort_index()
    return df

def fnRSI(m_Df, m_N):
    
    U = np.where(m_Df.diff(1) > 0, m_Df.diff(1), 0)
    D = np.where(m_Df.diff(1) < 0, m_Df.diff(1) *(-1), 0)
    AU = pd.DataFrame(U).rolling( window=m_N, min_periods=m_N).mean()
    AD = pd.DataFrame(D).rolling( window=m_N, min_periods=m_N).mean()    
    RSI = pd.DataFrame(columns=['rsi','index'])
    RSI['rsi'] = AU.div(AD+AU) *100
    RSI['index'] = m_Df.index
    RSI.set_index('index', inplace=True)
    
    return RSI['rsi']


def get_stocatsic(df,n_days,slowk_days, slowd_days):
    
    #binance = ccxt.binance()
    #btc_ohlcv = binance.fetch_ohlcv("BTC/USDT")
    #df = pd.DataFrame(btc_ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    
    stocastic = pd.DataFrame(columns=['fast_k', 'slow_k', 'slow_d'])
    ndays_high = df.high.rolling(window=n_days, min_periods=1).max()
    ndays_low = df.low.rolling(window=n_days, min_periods=1).min()
    stocastic['fast_k'] = ((df.close - ndays_low) / (ndays_high - ndays_low))*100
    stocastic['slow_k'] = stocastic.fast_k.rolling(slowk_days).mean()
    stocastic['slow_d'] = stocastic.slow_k.rolling(slowd_days).mean()
    
    return stocastic

    
def stocastic_plus_rsi(df,rsi,sto): #stocatsic은 'fast_k', 'slow_k', 'slow_d' 중 하나만 
    ma15 = df['close'].rolling(15).mean().shift(1)
    ma50 = df['close'].rolling(50).mean().shift(1)
    ma200 = df['close'].rolling(200).mean().shift(1)
    
    cond_1 = (rsi >= 40)&(rsi<=50)
    cond_2 = sto <= 20
    cond_3 = ma50 > ma200
    buy_cond = cond_1 & cond_2 & cond_3 # & cond_4#참과 거짓이 저장된 series객체
    
    #print(df.index[buy_cond]) #조건이 참인경우만 출력

    acc_ror = 1 #원금
    sell_date = None

    ax_ror = [] #누적수익률은 매도 시점에 업데이트 -> 언제 업데이트
    ay_ror = [] #업데이트 결과
    for buy_date in df.index[buy_cond]:
        if sell_date != None and buy_date <= sell_date: # 매수 후 매도하지 못했는데 시그널이 오면 그냥 패스
            continue
        
        target = df.loc[buy_date: ]
        sell_cond_1 = sto[buy_date:] >= 90 # 매도조건
        sell_cond_2 = df.close.loc[buy_date:] < df.close.loc[buy_date] * 0.97 #손절전략
        sell_cond = sell_cond_1 | sell_cond_2
        
        sell_candidate = target.index[sell_cond] # 매도조건을 만족한 시간의 리스트
        buy_price = df.loc[buy_date, 'close']
    
        
        if len(sell_candidate) == 0: #만약 매도조건을 만족한 시간이 없으면 break // 마지막 날의 가격으로 판매한 것으로 가정
            sell_price = df.iloc[-1,3] #-1 -> 마지막 날의 가격 3-> 종가를 의미
            acc_ror *= (sell_price/buy_price) - 0.005
            ax_ror.append(df.index[-1]) # 팔지못했을 때
            ay_ror.append(acc_ror) # 동일
            break
        else:
            sell_date = target.index[sell_cond][0]
            sell_price = df.loc[sell_date,'close']
            acc_ror *= (sell_price/buy_price) - 0.005 # 수수료 계산 수수료는 정확한 값 알아보기
            ax_ror.append(sell_candidate[0]) # 매도 날짜를 plot으로 그리기 위해 
            ay_ror.append(acc_ror) # ror을 plot으로
            print("buy date: ", buy_date)
            print("sell date: ", sell_date)
            print("ror:", acc_ror)
            print("")
    
    candle = go.Candlestick( #비트코인을 캔들차트로 표현
        x = df.index,
        open = df['open'],
        high = df['high'],
        close = df['close'],
        low = df['low'],
    )
    
    ror_chart = go.Scatter(#ror을 그림으로 표현
        x = ax_ror,
        y = ay_ror
    )

    fig = make_subplots(specs = [[{"secondary_y": True}]]) # "secondary_y": True -> ror과 비트코인 가격의 간격이 크니까 (1.0x, 2천만) 유의미한 차트 x --> 축 하나 더 생성
    fig.add_trace(candle)#trace 메서드를 이용하여 차트를 그림  
    fig.add_trace(ror_chart, secondary_y = True)
    
    for idx in df.index[buy_cond]: #annotation은 하나씩 추가해야해서 for문으로 
        fig.add_annotation(#구매한 날짜 표시
            x = idx,
            y = df.loc[idx,'open'] 
        )
    fig.show()
    return acc_ror

#df = pyupbit.get_ohlcv("KRW-BTC")
#df = get_ohlcv("KRW-BTC")
#df.to_excel(f"KRW-BTC_4hours.xlsx")
df = pd.read_excel(f"KRW-BTC_4hours.xlsx", index_col=0)    
stocastic = get_stocatsic(df,14,3,3)
rsi = fnRSI(df['close'],14)
fast_k = stocastic['fast_k']
print(stocastic_plus_rsi(df,rsi,fast_k))
#df = pyupbit.get_ohlcv("KRW-BTC", interval="minute1", to ="20220101 23:00:00")
#print(type(rsi))  