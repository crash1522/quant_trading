import pyupbit
import pandas as pd 
import numpy as np
import pandas as pd

def get_ohlcv(ticker): #코인의 정보를 불러옴, 500*n개의 정보
    dfs = [ ]
    df = pyupbit.get_ohlcv(ticker, interval="minute240")
    dfs.append(df)
    df = pd.concat(dfs) #list안에 있는 데이터프레임을 하나로 합쳐줌
    df = df.sort_index()
    return df

def fnRSI(m_Df, m_N = 14):
    
    U = np.where(m_Df.diff(1) > 0, m_Df.diff(1), 0)
    D = np.where(m_Df.diff(1) < 0, m_Df.diff(1) *(-1), 0)
    AU = pd.DataFrame(U).rolling( window=m_N, min_periods=m_N).mean()
    AD = pd.DataFrame(D).rolling( window=m_N, min_periods=m_N).mean()    
    RSI = pd.DataFrame(columns=['rsi','index'])
    RSI['rsi'] = AU.div(AD+AU) *100
    RSI['index'] = m_Df.index
    RSI.set_index('index', inplace=True)
    
    return RSI['rsi']


def cal_stocatsic(df, n_days = 14, slowk_days = 3, slowd_days = 3):
    
    stocastic = pd.DataFrame(columns=['fast_k', 'slow_k', 'slow_d'])
    ndays_high = df.high.rolling(window=n_days, min_periods=1).max()
    ndays_low = df.low.rolling(window=n_days, min_periods=1).min()
    stocastic['fast_k'] = ((df.close - ndays_low) / (ndays_high - ndays_low))*100
    stocastic['slow_k'] = stocastic.fast_k.rolling(slowk_days).mean()
    stocastic['slow_d'] = stocastic.slow_k.rolling(slowd_days).mean()
    
    return stocastic

def get_cur_rsi(ticker):
    tick = get_ohlcv(ticker)['close']
    rsi = fnRSI(tick)
    return float(rsi.iloc[-1:])

def get_cur_stocatsic(ticker):
    tick = get_ohlcv(ticker)
    sto = cal_stocatsic(tick)
    fast = sto['fast_k']
    return float(fast.iloc[-1:])
