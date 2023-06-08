import pybithumb
import pyupbit
import pandas as pd 
import numpy as np
import pandas as pd
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#코인의 정보를 불러옴, 500*n개의 정보
def get_ohlcv(ticker,n): 
    dfs = [ ]
    df = pyupbit.get_ohlcv(ticker, interval="minute60")
    dfs.append(df)
    for i in range(n):
        df = pyupbit.get_ohlcv(ticker, interval="minute60", to = df.index[0]) #to: 출력할 max date time을 지정
        dfs.append(df)
        #한 번에 너무 많은 데이터를 요청하면 웹서버에서 차단할 수 있음
        time.sleep(0.2) 
    #list안에 있는 데이터프레임을 하나로 합쳐줌
    df = pd.concat(dfs) 
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
    stocastic = pd.DataFrame(columns=['fast_k', 'slow_k', 'slow_d'])
    ndays_high = df.high.rolling(window=n_days, min_periods=1).max()
    ndays_low = df.low.rolling(window=n_days, min_periods=1).min()
    stocastic['fast_k'] = ((df.close - ndays_low) / (ndays_high - ndays_low))*100
    stocastic['slow_k'] = stocastic.fast_k.rolling(slowk_days).mean()
    stocastic['slow_d'] = stocastic.slow_k.rolling(slowd_days).mean()
    return stocastic

#stocatsic은 'fast_k', 'slow_k', 'slow_d' 중 하나만
def stocastic_plus_rsi(df,rsi,sto):  
    ma10 = df['close'].rolling(10).mean().shift(1)
    ma20 = df['close'].rolling(20).mean().shift(1)
    ma50 = df['close'].rolling(50).mean().shift(1)
    ma200 = df['close'].rolling(200).mean().shift(1)
    
    lcond_1 = (rsi >= 40)&(rsi<=50)
    lcond_2 = sto <= 20
    # &(ma20>ma50) 이동평균선이 정렬되어 있을 경우에만 매수 -> 하락장 회피
    lcond_3 = (ma50 > ma200)&(ma10 > ma20) 
    #  & cond_4#참과 거짓이 저장된 series객체
    long_cond = lcond_1 & lcond_2 & lcond_3
    
    scond_1 = (rsi >= 40)&(rsi<=50)
    scond_2 = sto >= 80
    # &(ma20>ma50) 이동평균선이 역정렬되어 있을 경우에만 매수 -> 상승장 회피
    scond_3 = (ma50 < ma200)&(ma10 < ma20) 
    #  & cond_4#참과 거짓이 저장된 series객체
    short_cond = scond_1 & scond_2 & scond_3
    
    #원금
    acc_ror = 1 
    long_sell_date = None
    #누적수익률은 매도 시점에 업데이트 -> 언제 업데이트 
    ax_ror = []
    #업데이트 결과
    ay_ror = []
    
    for buy_date in df.index[long_cond]:
         # 매수 후 매도하지 못했는데 시그널이 오면 그냥 패스
        if long_sell_date != None and buy_date <= long_sell_date:
            continue
    
        target = df.loc[buy_date: ]
        # 매도조건/ rsi가 80 85 93 95에서 높을수록 성능이 좋게 나옴
        long_sell_cond_1 = rsi[buy_date:] >= 95 
        #손절전략_매수가격보다 종가기준 3%이상 하락하면 손절
        long_sell_cond_2 = df.close.loc[buy_date:] < df.close.loc[buy_date] * 0.97 
        long_sell_cond = long_sell_cond_1 | long_sell_cond_2
        # 매도조건을 만족한 시간의 리스트
        sell_candidate = target.index[long_sell_cond] 
        buy_price = df.loc[buy_date, 'close']
    
        #만약 매도조건을 만족한 시간이 없으면 break // 마지막 날의 가격으로 판매한 것으로 가정
        if len(sell_candidate) == 0: 
            #-1 -> 마지막 날의 가격 3-> 종가를 의미
            sell_price = df.iloc[-1,3] 
            acc_ror *= (sell_price/buy_price) - 0.005
            # 팔지못했을 때
            ax_ror.append(df.index[-1])
            # 동일 
            ay_ror.append(acc_ror) 
            break
        else:
            long_sell_date = target.index[long_sell_cond][0]
            sell_price = df.loc[long_sell_date,'close']
            # 수수료 계산 수수료는 정확한 값 알아보기
            acc_ror *= (sell_price/buy_price) - 0.005
            # 매도 날짜를 plot으로 그리기 위해 
            ax_ror.append(sell_candidate[0])
            # ror을 plot으로  
            ay_ror.append(acc_ror) 
            
            print("buy date: ", buy_date)
            print("sell date: ", long_sell_date)
            print("ror:", acc_ror)
            print("")
    #비트코인을 캔들차트로 표현
    candle = go.Candlestick( 
        x = df.index,
        open = df['open'],
        high = df['high'],
        close = df['close'],
        low = df['low'],
    )
    #ror을 그림으로 표현
    ror_chart = go.Scatter( 
        x = ax_ror,
        y = ay_ror
    )
    # "secondary_y": True -> ror과 비트코인 가격의 간격이 크니까 (1.0x, 2천만) 유의미한 차트 x --> 축 하나 더 생성
    fig = make_subplots(specs = [[{"secondary_y": True}]]) 
    #trace 메서드를 이용하여 차트를 그림 
    fig.add_trace(candle)  
    fig.add_trace(ror_chart, secondary_y = True)
    #annotation은 하나씩 추가해야해서 for문으로
    for idx in df.index[long_cond]:
         #구매한 날짜 표시  
        fig.add_annotation(
            x = idx,
            y = df.loc[idx,'open'] 
        )
    fig.show()
    
    return acc_ror
"""
df = pyupbit.get_ohlcv("KRW-BTC")
df = get_ohlcv("KRW-BTC",50)
df.to_excel(f"KRW-BTC_1hours.xlsx")
"""
df = pd.read_excel(f"KRW-BTC_1hours.xlsx", index_col=0)    
stocastic = get_stocatsic(df,14,3,3)
rsi = fnRSI(df['close'],14)
fast_k = stocastic['fast_k']
stocastic_plus_rsi(df,rsi,fast_k)
