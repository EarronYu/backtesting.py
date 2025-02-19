import os
import time
import ccxt
import pandas as pd
import datetime

def timeframe_to_seconds(timeframe):
    """
    将 timeframe 转换为秒数（目前支持分钟和小时）
    """
    if timeframe.endswith("m"):
        return int(timeframe[:-1]) * 60
    elif timeframe.endswith("h"):
        return int(timeframe[:-1]) * 3600
    else:
        return 60

def fetch_historical_klines(symbol, timeframe, since, limit=100):
    """
    获取历史K线数据，从指定时间戳（毫秒）以来的数据
    注意：
      1. 每次最多获取 limit 根K线；
      2. 删除返回数据中最新一根可能尚未完整的K线；
      3. 对齐K线起始时间。
    """
    exchange = ccxt.binanceusdm({
        'enableRateLimit': True,
        'proxies': {
            'http': 'http://127.0.0.1:1522',
            'https': 'http://127.0.0.1:1522',
        },
    })
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
    if not ohlcv:
        return pd.DataFrame()
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    # 将 timestamp 转换为 datetime，并设置为索引
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("datetime", inplace=True)
    df.drop("timestamp", axis=1, inplace=True)
    df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }, inplace=True)

    # 对齐K线起始时间：向下取整
    if timeframe.endswith("m"):
        period_minutes = int(timeframe[:-1])
        freq = f"{period_minutes}T"
        df.index = df.index.floor(freq)
    elif timeframe.endswith("h"):
        period_hours = int(timeframe[:-1])
        freq = f"{period_hours}H"
        df.index = df.index.floor(freq)
    
    # 删除最后一根可能未完整的K线
    df = df.iloc[:-1]
    return df

def fetch_latest_complete_kline(symbol, timeframe, limit=2):
    """
    获取最新完整的K线数据，返回最新一根完整K线（DataFrame格式）。
    limit 设置为 2，以便确保最新返回的一根是完整的。
    """
    exchange = ccxt.binanceusdm({
        'enableRateLimit': True,
        'proxies': {
            'http': 'http://127.0.0.1:1522',
            'https': 'http://127.0.0.1:1522',
        },
    })
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not ohlcv:
        return pd.DataFrame()
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("datetime", inplace=True)
    df.drop("timestamp", axis=1, inplace=True)
    df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }, inplace=True)

    if timeframe.endswith("m"):
        period_minutes = int(timeframe[:-1])
        freq = f"{period_minutes}T"
        df.index = df.index.floor(freq)
    elif timeframe.endswith("h"):
        period_hours = int(timeframe[:-1])
        freq = f"{period_hours}H"
        df.index = df.index.floor(freq)
    
    # 舍弃最后一根K线，确保使用完整数据
    df = df.iloc[:-1]
    if df.empty:
        return pd.DataFrame()
    return df.iloc[[-1]]

def fetch_klines_for_day(symbol, timeframe, day):
    """
    获取指定日期（day）内的K线数据，只取当天数据
    参数:
      symbol: 交易对
      timeframe: K线周期
      day: 日期字符串，格式例如 '2025-02-05'
    """
    import time
    day_dt = pd.to_datetime(day)
    start_ts = int(pd.Timestamp(f"{day_dt.date()} 00:00:00").timestamp() * 1000)
    end_ts = int(pd.Timestamp(f"{day_dt.date()} 23:59:59").timestamp() * 1000)
    
    exchange = ccxt.binanceusdm({
        'enableRateLimit': True,
        'proxies': {
            'http': 'http://127.0.0.1:1592',
            'https': 'http://127.0.0.1:1592',
        },
    })
    all_data = []
    current_since = start_ts
    while current_since < end_ts:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=current_since, limit=1000)
        if not ohlcv:
            break
        all_data.extend(ohlcv)
        # 更新为最后一根K线的结束时间
        current_since = ohlcv[-1][0] + 1
        time.sleep(0.8)
    if not all_data:
        return pd.DataFrame()
    df = pd.DataFrame(all_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("datetime", inplace=True)
    df.drop("timestamp", axis=1, inplace=True)
    df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }, inplace=True)
    # 仅保留当天数据
    target_date = pd.to_datetime(day).date()
    df = df[df.index.date == target_date]
    df.sort_index(inplace=True)
    # 舍弃当天最后一根K线，确保数据完整
    if len(df) > 0:
        df = df.iloc[:-1]
    return df

def initialize_klines_pool(symbol, timeframe, pool_size=2000):
    """
    使用按天获取数据的方式初始化历史K线数据。
    每次只取一天的数据，逐日向前累积数据，直到累计出至少 pool_size 根完整K线，
    最终返回最近 pool_size 根数据（按时间升序排列）。
    """
    # 获取昨日的日期（当天数据可能不完整）
    current_day = pd.Timestamp.now(tz='UTC').normalize() - pd.Timedelta(days=1)
    all_data = pd.DataFrame()
    while len(all_data) < pool_size:
        day_str = current_day.strftime("%Y-%m-%d")
        print(f"获取 {symbol} {timeframe} {day_str} 的数据...")
        df_day = fetch_klines_for_day(symbol, timeframe, day_str)
        if not df_day.empty:
            all_data = pd.concat([df_day, all_data])
            all_data.sort_index(inplace=True)
        current_day -= pd.Timedelta(days=1)
        # 至多回溯1年的数据
        if (pd.Timestamp.now(tz='UTC') - current_day).days > 365:
            print("回溯数据超过1年，停止补充。")
            break
    return all_data.tail(pool_size)

def update_klines_pool(symbol, timeframe, pool_df, pool_size=2000):
    """
    利用先进先出更新K线数据池：
      1. 获取最新完整的K线数据；
      2. 若新K线的时间戳大于数据池中最后一根，则追加；
      3. 超过 pool_size 时删除最旧的数据，保持数据池大小不变。
    返回更新后的数据池以及是否更新的布尔值。
    """
    new_kline = fetch_latest_complete_kline(symbol, timeframe)
    if new_kline.empty:
        print("未获取到新的完整K线数据。")
        return pool_df, False
    if new_kline.index[0] > pool_df.index[-1]:
        pool_df = pd.concat([pool_df, new_kline])
        if len(pool_df) > pool_size:
            pool_df = pool_df.tail(pool_size)
        print("已更新K线数据池，新增一根K线。")
        return pool_df, True
    else:
        print("最新K线数据与现有数据一致，无需更新。")
        return pool_df, False

def main():
    symbol = "1000PEPEUSDT"  # 交易对
    timeframe = "30m"         # K线周期
    pool_size = 2000         # 数据池大小
    csv_filename = f"binance_{symbol}_{timeframe}.csv"

    # 如果本地数据池文件存在，则加载之；否则初始化数据池
    if os.path.exists(csv_filename):
        pool_df = pd.read_csv(csv_filename, index_col=0, parse_dates=True)
        if len(pool_df) < pool_size:
            print("本地数据池不足2000条，自动补充历史数据...")
            pool_df = initialize_klines_pool(symbol, timeframe, pool_size=pool_size)
        print(f"加载本地K线数据池，共有 {len(pool_df)} 根数据。")
    else:
        print("本地K线数据池不存在，开始初始化历史数据...")
        pool_df = initialize_klines_pool(symbol, timeframe, pool_size=pool_size)
        print(f"历史数据累计完成，共有 {len(pool_df)} 根数据。")
    
    # 仅补充缺失的历史数据后保存一次CSV，然后退出
    pool_df.to_csv(csv_filename)
    print(f"数据池更新后已保存至 {csv_filename}")

if __name__ == "__main__":
    main() 