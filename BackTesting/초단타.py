import pyupbit
import pybithumb
import pandas as pd
import numpy as np
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def get_ohlcv(ticker):
    dfs = [ ]
    df = pyupbit.get_ohlcv(ticker, interval="minute1", to ="20220112 23:00:00")
    dfs.append(df)
    #df = pybithumb.get_ohlcv('BTC', interval="minute1")
    for i in range(5000):
        df = pyupbit.get_ohlcv(ticker, interval="minute1", to = df.index[0]) #to: 출력할 max date time을 지정
        dfs.append(df)
        time.sleep(0.2) #한 번에 너무 많은 데이터를 요청하면 웹서버에서 차단할 수 있음

    df = pd.concat(dfs) #list안에 있는 데이터프레임을 하나로 합쳐줌
    df = df.sort_index()
    return df
    
def short_trading_for_1percent(df):
    ma15 = df['close'].rolling(15).mean().shift(1)
    ma50 = df['close'].rolling(50).mean().shift(1)
    ma120 = df['close'].rolling(120).mean().shift(1)
    
    cond_0 = df['high'] >= df['open'] * 1.01
    cond_1 = (ma15 >= ma50) & (ma15 <= ma50 * 1.03) # 단기 이평과 장기 이평이 이격이 너무 벌어졌을 때 매수하는 것을 방지하여 고점에서 물리는 것을 방지
    cond_2 = ma50 > ma120
    buy_cond =  cond_0 & cond_1 & cond_2#참과 거짓이 저장된 series객체
    #print(df.index[buy_cond]) #조건이 참인경우만 출력
    
    acc_ror = 1 #원금

    ax_ror = [] #누적수익률은 매도 시점에 업데이트 -> 언제 업데이트
    ay_ror = [] #업데이트 결과
    
    sell_date = None
    
    for buy_date in df.index[buy_cond]:
        if sell_date != None and buy_date <= sell_date: # 매수 후 매도하지 못했는데 시그널이 오면 그냥 패스
            continue
        
        target = df.loc[buy_date: ]
        
        sell_cond = target['high'] >= df.loc[buy_date,'open'] * 1.02 # 매도조건, 1퍼센트 이득보면 매도    
        sell_candidate = target.index[sell_cond] # 매도조건을 만족한 시간의 리스트
        
        if len(sell_candidate) == 0: #만약 매도조건을 만족한 시간이 없으면 break // 마지막 날의 가격으로 판매한 것으로 가정
            buy_price = df.loc[buy_date, 'open'] * 1.01
            sell_price = df.iloc[-1,3] #-1 -> 마지막 날의 가격 3-> 종가를 의미
            acc_ror *= (sell_price/buy_price) - 0.005
            ax_ror.append(df.index[-1]) # 팔지못했을 때
            ay_ror.append(acc_ror) # 동일
            break
        else:
            sell_date = sell_candidate[0]
            acc_ror *= 1.01 - 0.005 # 수수료 계산 수수료는 정확한 값 알아보기
            ax_ror.append(sell_date) # 매도 날짜를 plot으로 그리기 위해 
            ay_ror.append(acc_ror) # ror을 plot으로
    
    
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


"""
for ticker in ["KRW-BTC", "KRW-XRP", "KRW-ETH","KRW-ADA"]:
    df = get_ohlcv(ticker)
    df.to_excel(f"{ticker}_lately.xlsx")
    ror = short_trading_for_1percent(df)
    print(ticker, ror)
"""
    
for ticker in ["KRW-BTC", "KRW-XRP", "KRW-ETH","KRW-ADA"]:
    df = pd.read_excel(f"{ticker}.xlsx", index_col=0)
    ror = short_trading_for_1percent(df)
    holding = df.iloc[-1,3] / df.iloc[0,0] # 단순 보유하고 있을 때 수익률 -> 단순 대조군
    print(ticker, "ror: ",ror, "holing: ",holding)

