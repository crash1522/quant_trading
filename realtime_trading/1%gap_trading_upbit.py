import threading
import queue
import time
import pybithumb
import pyupbit
from collections import deque

class Consumer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.ticker = "KRW-BTC"
        
        self.ma15 = deque(maxlen=15)
        self.ma50 = deque(maxlen=50)
        self.ma120 = deque(maxlen=120)

        df = pyupbit.get_ohlcv(self.ticker, interval="minute1")
        self.ma15.extend(df['close'])
        self.ma50.extend(df['close'])
        self.ma120.extend(df['close'])
        
    def run(self):
        print("매매시작\n")
        price_curr = None        
        hold_flag = False # 조건을 만족하면 time.sleep 간격마다 계속 매수하려고 할테니 flag추가
        wait_flag = False # 급등하게 되면 하나의 봉안에서 여러번의 매수,매도를 진행 -> 이를 방지 // 의도하여 실행해도 됨
        
        with open("upbit_api.txt", "r") as f:
            key0 = f.readline().strip()
            key1 = f.readline().strip()
        
        upbit = pyupbit.Upbit(key0,key1)
        cash = upbit.get_balance()
        print("보유현금:",cash)
        i = 0
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
                    if hold_flag == False:
                        price_buy = price_open * 1.01
                        price_sell = price_open * 1.02
                
                    wait_flag = False # 시가가 업데이트될 때 False로 초기화
 
                price_curr = pyupbit.get_current_price(self.ticker)    
                if price_curr == None:
                        print("가상화폐 가격 조회 오류")
                        continue

                # hold_flag가 False이면 즉, 현재 무포지션을 때만 시행 // 하나의 봉안에서 매수\매도를 했으면 매매 중지
                if hold_flag == False and wait_flag == False and \
                    price_curr >= price_buy and curr_ma15 >= curr_ma50 and \
                    curr_ma15 <= curr_ma50 * 1.03 and curr_ma120 <= curr_ma50 :

                    ret = upbit.buy_market_order(self.ticker, cash*0.9995) # 올인하려면 cash * (1-수수료)
                    print("매수 주문", ret)
                    if ret == None or "error" in ret: # 매수가 정상적으로 이루어지지 않았으면 while의 처음으로 돌아감
                        print("매수 주문 오류")
                        continue
                    
                    while True: #모든 api 주문에 에러처리를 해줌
                        order = upbit.get_order(ret['uuid'])
                        if order != None and len(order['trades']) > 0: #정상적으로 매수 주문 조회가 이루어지면 다음 코드 실행 
                            print("매수 처리 완료", order)
                            break
                        else:
                            print("매수 주문 대기 중")
                            time.sleep(0.5)
                    
                    while True:
                        volume = upbit.get_balance(self.ticker)
                        if volume != None:
                            print(self.ticker,volume)
                            break
                        print("수량 조회 대기 중")
                        time.sleep(0.5)
                        
                    while True:
                        price_sell = pyupbit.get_tick_size(price_sell)   
                        ret = upbit.sell_limit_order(self.ticker, price_sell, volume)
                        if ret == None or "error" in ret:
                            print("매도 주문 오류")
                            time.sleep(0.5)
                        else:
                            print("매도 주문", ret)
                            hold_flag = True
                            break
                    
                if hold_flag == True:
                    uncomp = upbit.get_order(self.ticker)
                    if uncomp != None and len(uncomp) == 0: # 모든 주문이 체결이 됐다는 뜻
                        # 여기서 오류가 발생하면 while문 처음으로 돌아갈테니 while로 에러처리는 하지 않아도됨
                        # uncomp를 제대로 받아왔는지만 확인
                        cash = upbit.get_balance() # 현금 업데이트를 해줘야 다음 매매는 업데이트된 현금으로 진행
                        if cash == None:  
                            continue
                        print("매도완료", cash)
                        hold_flag = False # 무포지션으로 표시
                        wait_flag = True # 한번 매도를 진행하면, 그 봉안에서는 기다리라는 의미에서 True
                time.sleep(60)
         
            except:
                print("ERROR")
                
class Producer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q

    def run(self):
        while True:
            price = pyupbit.get_current_price("KRW-BTC")
            self.q.put(price) 
            time.sleep(60) # 1분마다 조회를 해줌   
                    
                    
q = queue.Queue()
Producer(q).start()
Consumer(q).start()