import time
import pandas as pd
import random

def wait_until_kline_complete(timeframe):
    """
    等待直到当前K线结束，使后续获取的数据不包含未完成的K线。
    例如，对于1分钟K线，如果当前处于11:25:xx（11:25K线未结束），则等待到11:26:00以后再取数据；
    对于30分钟K线，等待当前K线结束后再进行数据拉取。
    """
    if timeframe.endswith('m'):
        period_sec = int(timeframe[:-1]) * 60
        freq = f"{int(timeframe[:-1])}T"
    elif timeframe.endswith('h'):
        period_sec = int(timeframe[:-1]) * 3600
        freq = f"{int(timeframe[:-1])}H"
    else:
        period_sec = 60
        freq = "1T"
    
    now = pd.Timestamp.now()
    # 当前K线的起始时间（对齐至周期边界）
    current_candle_start = now.floor(freq)
    # 当前K线的收盘时间
    current_candle_close = current_candle_start + pd.Timedelta(seconds=period_sec)
    
    if now < current_candle_close:
        # 生成一个 1 到 5 秒之间的随机数
        random_wait_time = random.uniform(1, 10)
        wait_time = (current_candle_close - now).total_seconds() + random_wait_time
        print(f"当前K线未结束，等待 {wait_time:.3f} 秒，直至收盘...")
        time.sleep(wait_time)
    else:
        print("当前K线数据已完整。")
