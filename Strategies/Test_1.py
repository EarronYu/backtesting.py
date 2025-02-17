from backtesting import Strategy
import pandas as pd
from record_trade import record_trade  # 导入独立的 record_trade 函数

class Test_1(Strategy):
    # 定义类属性 symbol 与 timeframe，不再使用 params 字典
    symbol = "1000PEPEUSDT"
    timeframe = "1m"

    def init(self):
        # 初始化简单的移动平均指标（窗口期为2）
        self.sma = self.I(lambda x: pd.Series(x).rolling(2).mean().values, self.data.Close)

    def next(self):
        # 获取当前时间，并使用类名作为策略名称
        current_time = str(self.data.index[-1])

        if not self.position and self.data.Close[-1] > self.sma[-1]:
            self.buy()
            record_trade({
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "date": current_time,
                "signal": f"{self.__class__.__name__} enter_long"
            })
        elif self.position and self.data.Close[-1] < self.sma[-1]:
            self.position.close()
            record_trade({
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "date": current_time,
                "signal": f"{self.__class__.__name__} exit_long"
            })