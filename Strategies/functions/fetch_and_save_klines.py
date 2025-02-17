import ccxt
import pandas as pd
import datetime

def fetch_and_save_klines(symbol, timeframe, limit, filename):
    """
    使用 ccxt 的 binanceusdm 接口获取指定交易对的 K 线数据，
    并将数据保存到本地 CSV 文件中。

    注意：
      1. 通过对时间戳进行 floor 操作对齐各 K 线的开始时刻；
      2. 如果最新一根 K 线未完整（例如，1 分钟 K 线在 11:25:01 调用时，
         其起始时间为 11:25:00，但该 K 线尚未结束），则丢弃这根数据，
         保证策略只使用完整的 K 线数据。
    """
    # 创建 Binance USDM 实例
    exchange = ccxt.binanceusdm({
        'enableRateLimit': True,
        'proxies': {
            'http': 'http://127.0.0.1:1522',
            'https': 'http://127.0.0.1:1522',
        },
    })
    print("开始拉取数据……")
    # 获取最新的 K 线数据
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    
    # 将数据转换为 DataFrame
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    # 将 timestamp 转换为 datetime
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("datetime", inplace=True)
    # 删除原始 timestamp 列
    df.drop("timestamp", axis=1, inplace=True)
    
    # 将列名转换为大写，符合 backtesting.py 的要求
    df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }, inplace=True)
    
    # ------【新增对齐时间的逻辑】------
    # 根据传入的 timeframe 对 index 向下取整（floor）
    if timeframe.endswith("m"):
        period_minutes = int(timeframe[:-1])
        freq = f"{period_minutes}T"   # 例如 "1T" 或 "30T"
        df.index = df.index.floor(freq)
    elif timeframe.endswith("h"):
        period_hours = int(timeframe[:-1])
        freq = f"{period_hours}H"
        df.index = df.index.floor(freq)
    # ------END 新增逻辑------
    
    # ------【新增判断数据完整性逻辑】------
    # 计算当前系统时间（假定与数据时间一致）
    current_time = pd.Timestamp.now()
    # 根据 timeframe 计算 K 线周期（秒）
    if timeframe.endswith("m"):
        period_sec = int(timeframe[:-1]) * 60
    elif timeframe.endswith("h"):
        period_sec = int(timeframe[:-1]) * 3600
    else:
        period_sec = 60

    # 删除最后一根K线
    df = df.iloc[:-1]
    # ------END 新增逻辑------
    
    # 保存到 CSV 文件
    df.to_csv(filename)
    print(f"数据已保存到 {filename}")
    return df
