from backtesting import Backtest, Strategy
from backtesting.test import GOOG
import pandas as pd

class BBTFStrategy(Strategy):
    # 策略参数（可在优化时调整）
    bb_length = 20           # 布林带计算周期
    bb_stddev = 2.0          # 布林带标准差倍数
    ema_length = 100         # 移动平均周期
    useEma = True            # 是否使用 EMA 过滤
    ema_type = 'Ema'         # 'Ema' 或 'Sma'
    checkboxLong = True      # 允许多头进场
    checkboxShort = True     # 允许空头进场

    # 时间窗口参数（默认时间与 Pine 脚本中一致）
    use_time_window = True
    start_date = pd.Timestamp('2022-01-01 00:00:00')
    end_date   = pd.Timestamp('2029-12-31 23:59:00')

    # 提示消息（仅在下单时打印）
    messageEntry = "入场订单提示"
    messageExit  = "退出订单提示"
    messageClose = "平仓订单提示"

    def init(self):
        # 计算布林带中轨和标准差（利用滚动均值和标准差）
        self.bb_middle = self.I(lambda c: pd.Series(c).rolling(self.bb_length).mean(), self.data.Close)
        self.bb_std_val  = self.I(lambda c: pd.Series(c).rolling(self.bb_length).std(), self.data.Close)
        self.bb_upper = self.bb_middle + self.bb_stddev * self.bb_std_val
        self.bb_lower = self.bb_middle - self.bb_stddev * self.bb_std_val

        # 计算移动平均滤波，决定进场方向
        if self.ema_type == 'Ema':
            self.ma = self.I(lambda c: pd.Series(c).ewm(span=self.ema_length, adjust=False).mean(), self.data.Close)
        else:
            self.ma = self.I(lambda c: pd.Series(c).rolling(self.ema_length).mean(), self.data.Close)

        # 初始化挂单引用变量
        self.long_order = None
        self.short_order = None

    def next(self):
        # 判断是否处于指定交易时间窗口
        if self.use_time_window:
            current_time = self.data.index[-1]
            in_trade_window = (current_time >= self.start_date) and (current_time < self.end_date)
        else:
            in_trade_window = True

        if not in_trade_window:
            # 不在交易窗口内，取消挂单
            if self.long_order:
                self.cancel(self.long_order)
                self.long_order = None
            if self.short_order:
                self.cancel(self.short_order)
                self.short_order = None
            return

        # 获取前一个和当前 K 线的收盘价
        close_prev = self.data.Close[-1]
        close_curr = self.data.Close[0]

        # 根据移动平均过滤，若使用 EMA 则：多头要求当前价大于 MA，空头要求小于 MA；若关闭，则均不过滤
        if self.useEma:
            long_filter = close_curr > self.ma[0]
            short_filter = close_curr < self.ma[0]
        else:
            long_filter = True
            short_filter = True

        # 布林带条件：若前一 K 线收盘价在上轨以下、当前收盘价突破上轨，则认为是多头信号
        openLong = (close_prev < self.bb_upper[-1]) and (close_curr > self.bb_upper[0]) and long_filter
        # 类似地，若前一 K 线收盘价在下轨以上、当前收盘价跌破下轨，则认为是空头信号
        openShort = (close_prev > self.bb_lower[-1]) and (close_curr < self.bb_lower[0]) and short_filter

        # 如果当前没有持仓，则考虑入场
        if not self.position:
            if openLong and self.checkboxLong:
                # 利用当前 K 线的最高价作为触发价格
                entry_price = self.data.High[0]
                self.long_order = self.buy(stop=entry_price)
                print(f"提交多头入场订单，触发价：{entry_price}，消息：{self.messageEntry}")
            elif openShort and self.checkboxShort:
                entry_price = self.data.Low[0]
                self.short_order = self.sell(stop=entry_price)
                print(f"提交空头入场订单，触发价：{entry_price}，消息：{self.messageEntry}")
            else:
                # 条件不满足时，取消所有未成交挂单
                if self.long_order:
                    self.cancel(self.long_order)
                    self.long_order = None
                if self.short_order:
                    self.cancel(self.short_order)
                    self.short_order = None
        else:
            # 已有持仓时，取消所有挂单
            if self.long_order:
                self.cancel(self.long_order)
                self.long_order = None
            if self.short_order:
                self.cancel(self.short_order)
                self.short_order = None

            # 根据布林中轨设置退出订单：对于多头，若价格跌破中轨则退出；对于空头，若价格突破中轨则退出
            if self.position.is_long:
                self.exit(stop=self.bb_middle[0])
                print(f"提交多头止损订单，止损价：{self.bb_middle[0]}，消息：{self.messageExit}")
            elif self.position.is_short:
                self.exit(stop=self.bb_middle[0])
                print(f"提交空头止损订单，止损价：{self.bb_middle[0]}，消息：{self.messageExit}")

