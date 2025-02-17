import numpy as np
import talib as ta
from backtesting import Strategy
from backtesting.lib import crossover
# from record_trade import record_trade  # 导入独立的 record_trade 函数

class ConnorsReversal(Strategy):
    symbol = "1000PEPEUSDT"  # 添加交易对标识
    timeframe = "1m"         # 添加时间周期

    # 定义策略参数
    lowest_point_bars = 16    # 用于确定最低点的周期数
    rsi_length = 4           # RSI指标的计算周期 
    sell_barrier = 73        # RSI的卖出阈值
    dca_parts = 8            # DCA分批次数
    
    def init(self):
        # 计算RSI
        self.rsi = self.I(ta.RSI, self.data.Close, self.rsi_length)
        
        # 记录开仓数量
        self.open_trades = 0
        
        # 计算每份资金的比例
        self.unit_ratio = 1 / self.dca_parts
        
    def next(self):
        current_time = str(self.data.index[-1])
        # 计算最低点
        lookback = self.lowest_point_bars * (self.open_trades + 1)
        if len(self.data.Close) < lookback:
            return
            
        recent_low = np.min(self.data.Low[-lookback:])
        is_lowest = self.data.Low[-1] == recent_low
        
        # 计算买入条件
        price_below_avg = True
        if self.position:
            # 计算平均持仓价格
            trades = self._broker.trades  # 获取所有交易
            if trades:
                # 计算加权平均价格
                total_size = sum(abs(trade.size) for trade in trades)
                avg_price = sum(trade.entry_price * abs(trade.size) for trade in trades) / total_size
                # 修正：当前价格应该低于调整后的平均价格
                price_below_avg = (self.data.Close[-1] < avg_price * (1 - 0.01 * self.open_trades))
            
        is_buy = (is_lowest and (price_below_avg or self.open_trades == 0))
        
        # 计算卖出条件
        is_close = self.rsi[-1] > self.sell_barrier
        
        # 执行交易
        if is_buy and self.open_trades < self.dca_parts:
            # 计算当前应该使用的资金比例 (累进式)
            current_ratio = self.unit_ratio * (self.open_trades + 1)
            self.buy(size=current_ratio)
            # record_trade({
            #     "symbol": self.symbol,
            #     "timeframe": self.timeframe,
            #     "date": current_time,
            #     "signal": f"{self.__class__.__name__} enter_long"
            # })
            self.open_trades += 1
            
        if is_close and self.position:
            self.position.close()
            # record_trade({
            #     "symbol": self.symbol,
            #     "timeframe": self.timeframe,
            #     "date": current_time,
            #     "signal": f"{self.__class__.__name__} exit_long"
            # })
            self.open_trades = 0
