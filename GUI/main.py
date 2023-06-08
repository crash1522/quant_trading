import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow
import datetime
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import realtime_super_trend
import ccxt
import time

class SupertrendWorker(QThread):
    tradingSent = pyqtSignal(str, str, str, float)
    normalSent = pyqtSignal(str, str, str)

    def __init__(self, symbol, binance):
        super().__init__()
        self.symbol = symbol
        self.binance = binance
        self.alive = True
        
        self.balance = self.binance.fetch_balance()
        self.usdt = self.balance['total']['USDT']
        self.op_mode = True
        self.position = {
            "type": None,
            "amount": 0
        }

    def run(self):
        now = datetime.datetime.now()
        tstring = now.strftime("%Y/%m/%d %H:%M:%S")

        self.normalSent.emit(tstring, "Supertrend", "매매 시작")

        while self.alive:

            now = datetime.datetime.now()
    
            if realtime_super_trend.time_condition_4h():
                ticker = self.binance.fetch_ticker(self.symbol)
                cur_price = ticker['last']
                amount = realtime_super_trend.cal_amount(self.usdt, cur_price)
                trend_5_7, trend_12_8 = realtime_super_trend.renew_stc(self.symbol, self.binance)
                
                if trend_5_7 >= cur_price and trend_12_8 <= cur_price:
                    if self.op_mode == False and self.position['type'] == 'long':
                        realtime_super_trend.exit_position(self.binance, self.symbol, self.position)
                        tstring = now.strftime("%Y/%m/%d %H:%M:%S")
                        self.tradingSent.emit("Supertrend", tstring, "매도", self.position['amount'])

                        time.sleep(2)
                        self.balance = self.binance.fetch_balance() #잔고 업데이트
                        self.usdt = self.balance['total']['USDT']
                        self.op_mode = True
                if trend_5_7 <= cur_price and trend_12_8 >= cur_price:
                    if self.op_mode == False and self.position['type'] == 'short':
                        realtime_super_trend.exit_position(self.binance, self.symbol, self.position)
                        tstring = now.strftime("%Y/%m/%d %H:%M:%S")
                        self.tradingSent.emit("Supertrend", tstring, "매도", self.position['amount'])

                        time.sleep(2)
                        self.balance = self.binance.fetch_balance()
                        self.usdt = self.balance['total']['USDT']
                        self.op_mode = True         # 포지션 정리 후 포지션 진입 가능

                if self.op_mode and self.position['type'] is None:
                    realtime_super_trend.enter_position(self.binance, cur_price ,self.symbol, amount, self.position, trend_5_7, trend_12_8)
                    tstring = now.strftime("%Y/%m/%d %H:%M:%S")
                    self.tradingSent.emit("Supertrend", tstring, "매수", amount)
                    
                    if self.position['type'] is not None:  # 포지션 정리 전까지는 다시 포지션 진입하지 않음
                        self.op_mode = False

            else:
                time.sleep(59)
                continue    

    def close(self):
        self.alive = False

form_class = uic.loadUiType("resource/main.ui")[0]

class MainWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.symbol = "BTC/USDT"
        self.button.clicked.connect(self.clickBtn)
        self.setWindowTitle("Home Trading System")
        now = datetime.datetime.now()
        behind_name = now.strftime("%Y.%m.%d %H-%M-%S")
        self.log_name = "log " + behind_name
        self.log_first = True
        
        f = open(f"logs/{self.log_name}.txt", "w")
        f.close()

        try:
            with open("api.txt") as f:
                lines = f.readlines()
                apikey = lines[0].strip()
                seckey = lines[1].strip()
                self.apiKey.setText(apikey)
                self.secKey.setText(seckey)
                now = datetime.datetime.now()
                tstring = now.strftime("%Y/%m/%d %H:%M:%S")
                self.receiveInfoSignal(tstring, "api.txt의 정보로 자동 api key 입력 완료되었습니다.")
        except:
            pass

    def clickBtn(self):
        if self.button.text() == "매매시작":
            apiKey = self.apiKey.text()
            secKey = self.secKey.text()

            if len(apiKey) != 64 or len(secKey) != 64:
                now = datetime.datetime.now()
                tstring = now.strftime("%Y/%m/%d %H:%M:%S")
                self.receiveInfoSignal(tstring, "KEY가 올바르지 않습니다.")
                return
            else:
                try:
                    self.binance = ccxt.binance(config={
                        'apiKey': self.apiKey.text(),
                        'secret': self.secKey.text(),
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'future'
                        }
                    })
                    self.balance = self.binance.fetch_balance()['total']['USDT']
                except:
                    now = datetime.datetime.now()
                    tstring = now.strftime("%Y/%m/%d %H:%M:%S")
                
                    self.receiveInfoSignal(tstring, "KEY가 올바르지 않습니다.")
                    return

            self.button.setText("매매중지")
            now = datetime.datetime.now()
            behind_name = now.strftime("%Y.%m.%d %H-%M-%S")
            tstring = now.strftime("%Y/%m/%d %H:%M:%S")
            
            if self.log_first == True:
                self.log_first = False
            else:
                self.log_name = "log " + behind_name

                f = open(f"logs/{self.log_name}.txt", "w")
                f.close()
                
            self.receiveInfoSignal(tstring, "------ START ------")
            self.receiveInfoSignal(tstring, f"보유 현금 : {self.balance} USDT")
            self.consumer.tradingSent.connect(self.receiveTradingSignal)
            self.consumer.normalSent.connect(self.receiveNormalSignal)

            self.producer.start()
            time.sleep(10)
            self.consumer.start()

            self.sw = SupertrendWorker(self.symbol, self.binance)
            self.sw.tradingSent.connect(self.receiveTradingSignal)
            self.sw.normalSent.connect(self.receiveNormalSignal)
            self.sw.start()

        else:
            self.vw.close()
            self.producer.close()
            self.consumer.close()
            self.sw.close()
            now = datetime.datetime.now()
            tstring = now.strftime("%Y/%m/%d %H:%M:%S")
            self.receiveInfoSignal(tstring, "------- END -------")
            self.button.setText("매매시작")

    @pyqtSlot(str, str, str)
    def receiveNormalSignal(self, time, strategy, message):
        self.textEdit.append(f"{time} [{strategy}] {message}")

        with open(f"logs/{self.log_name}.txt", 'a') as f:
            f.write(f"\n{time} [{strategy}] {message}")

    @pyqtSlot(str, str, str, float)
    def receiveTradingSignal(self, strategy, time, type, amount):
        self.textEdit.append(f"{time} [{strategy}] {type} : {amount}")

        with open(f"logs/{self.log_name}.txt", 'a') as f:
            f.write(f"\n{time} [{strategy}] {type} : {amount}")

    @pyqtSlot(str, str)
    def receiveInfoSignal(self, time, message):
        self.textEdit.append(f"{time} [INFO] {message}")

        with open(f"logs/{self.log_name}.txt", 'a') as f:
            f.write(f"\n{time} [INFO] {message}")
    
    def closeEvent(self, event):
        self.vw.close()
        self.producer.close()
        self.consumer.close()
        self.sw.close()
        self.widget.closeEvent(event)
        self.widget_2.closeEvent(event)
        self.widget_3.closeEvent(event)

    def currentstate(self):

        state = []
        self.logupdate(state)

    def logupdate(self, statelist):
        self.textEdit.clear()
        lines = []

        with open(f"logs/{self.log_name}.txt", 'r') as f:
            lines = f.readlines()

        for line in lines:
            if "INFO" in line:
                self.textEdit.append(line.strip())
                continue
 
            if "Supertrend" in line and statelist[1] == True:
                self.textEdit.append(line.strip())
                continue

          
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    exit(app.exec_())
