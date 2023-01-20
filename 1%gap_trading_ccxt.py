import threading
import queue
import time
import pyupbit
import ccxt
import pprint
from collections import deque
import pandas as pd

class Consumer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.ticker = "BTC/USDT"
        
        self.ma15 = deque(maxlen=15)
        self.ma50 = deque(maxlen=50)
        self.ma120 = deque(maxlen=120)

        exchange = ccxt.binance()

        btc = exchange.fetch_ohlcv(
            symbol = self.ticker,
            timeframe = '1m',
            since = None
        )

        df = pd.DataFrame(
            data = btc,
            columns=['datetime', 'open', 'high', 'low', 'close', 'volume']      
        )
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df.set_index('datetime', inplace=True)

        self.ma15.extend(df['close'])
        self.ma50.extend(df['close'])
        self.ma120.extend(df['close'])
        print(self.ma15)
        
    def run(self):
        print("매매시작\n")
        price_curr = None        
        hold_flag = False # 조건을 만족하면 time.sleep 간격마다 계속 매수하려고 할테니 flag추가
        wait_flag = False # 급등하게 되면 하나의 봉안에서 여러번의 매수,매도를 진행 -> 이를 방지 // 의도하여 실행해도 됨
        
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

        cash = binance.fetch_balance(params={'type':'future'})['USDT']
        print("보유현금", cash)
        
        while True:
            try:
                if not self.q.empty():
                    if price_curr != None:
                        self.ma15.append(price_curr)
                        self.ma50.append(price_curr)
                        self.ma120.append(price_curr)
                    
                    curr_ma15 = sum(self.ma15) / len(self.ma15)
                    curr_ma50 = sum(self.ma50) / len(self.ma50)
                    curr_ma120 = sum(self.ma120) / len(self.ma120)

                    price_open = self.q.get()
                    price_buy = price_open * 1.01
                    price_sell = price_open * 1.02 
                    wait_flag = False # 시가가 업데이트될 때 False로 초기화
                    
                price_curr = binance.fetch_ticker(self.ticker)['close']    
                # hold_flag가 False이면 즉, 현재 무포지션을 때만 시행 // 하나의 봉안에서 매수\매도를 했으면 매매 중지
                if hold_flag == False and \
                    wait_flag == False and \
                    price_curr >= price_buy and curr_ma15 >= curr_ma50 and \
                    curr_ma15 <= curr_ma50 * 1.03 and curr_ma120 <= curr_ma50 :
                    ret = binance.create_order(
                        symbol = "BTC/USDT",
                        type = "MARKET",
                        side = "buy",
                        amount = 0.001 # 나중에 따로 계산
                    )
                    print("매수주문 완료")
                    pprint.pprint(ret)
                    time.sleep(1)
                    ret = binance.create_order(
                        symbol = "BTC/USDT",
                        type = "TAKE_PROFIT_MARKET",
                        side = "sell",
                        amount = 0.001,
                        params = {'stopPrice': price_sell}
                    )
                    print("매도주문 완료")
                    hold_flag = True
                
                if hold_flag == True:
                    uncomp = binance.fetch_open_orders(
                            symbol= self.ticker
                        )
                    if len(uncomp) == 0: # 모든 주문이 체결이 됐다는 뜻
                        cash = binance.binance.fetch_balance(params={'type':'future'})['USDT'] # 현금 업데이트를 해줘야 다음 매매는 업데이트된 현금으로 진행
                        print("매도완료", cash)
                        hold_flag = False # 무포지션으로 표시
                        wait_flag = True # 한번 매도를 진행하면, 그 봉안에서는 기다리라는 의미에서 True
                time.sleep(0.2)
                
            except:
                print("ERROR")
                
class Producer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q

    def run(self):
        
        bin = ccxt.binance()
        while True:
            print("1분마다 업데이트")
            price = bin.fetch_ticker("BTC/USDT")['close']
            self.q.put(price) 
            time.sleep(60) # 1분마다 조회를 해줌   
                    
                    
q = queue.Queue()
Producer(q).start()
Consumer(q).start()