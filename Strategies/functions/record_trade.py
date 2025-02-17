import os
import csv
import pandas as pd

def record_trade(trade_data):
    """
    直接将交易信号记录到 OHLC CSV 文件中，对应指定时间行新增或更新 signal 栏。
    
    trade_data 是一个字典，包含：
        - symbol: 交易对
        - timeframe: K线周期
        - date: 产生信号的时间（字符串格式，必须与 CSV 中的日期完全一致）
        - signal: 交易信号（例如 "enter_long", "exit_long"）
    
    此函数直接在 "binance_{symbol}_{timeframe}.csv" 文件中添加或更新 'signal' 列，
    确保信号与对应时间的 K 线数据对齐。
    """
    # Debug输出：记录传入数据
    # print("record_trade: called with trade_data =", trade_data)
    
    # 构造 OHLC CSV 文件名（不加 _with_signals 后缀）
    filename = f"binance_{trade_data['symbol']}_{trade_data['timeframe']}.csv"
    
    if not os.path.isfile(filename):
        print(f"record_trade: 文件 {filename} 不存在!")
        return
    
    # 读取 CSV 文件，假设第一列为 datetime 索引（解析为日期）
    try:
        df = pd.read_csv(filename, index_col=0, parse_dates=True)
    except Exception as e:
        print("record_trade: 读取 CSV 文件失败:", e)
        return
    
    # 检查是否存在 'signal' 列，不存在则新增空列
    if "signal" not in df.columns:
        df["signal"] = ""
    
    # 将传入的 date 转换为 Timestamp
    try:
        trade_time = pd.to_datetime(trade_data["date"])
    except Exception as e:
        print("record_trade: 日期转换失败:", e)
        return
    
    # 检查 CSV 中是否包含该时间
    if trade_time not in df.index:
        print(f"record_trade: CSV 中未找到时间 {trade_time} 对应的行!")
        return
    
    # 如果该行已有信号，则判断是否为 NaN 或空字符串；若是，则直接赋值，否则追加信号
    current_signal = df.loc[trade_time, "signal"]
    if pd.isna(current_signal) or str(current_signal).strip() == "":
        df.loc[trade_time, "signal"] = trade_data["signal"]
    else:
        df.loc[trade_time, "signal"] = str(current_signal) + ";" + trade_data["signal"]
    
    # 保存回 CSV 文件
    try:
        df.to_csv(filename)
        # print(f"record_trade: 已更新文件 {filename} 中时间 {trade_time} 的 signal 为 {df.loc[trade_time, 'signal']}")
    except Exception as e:
        print("record_trade: 写入 CSV 文件失败:", e) 