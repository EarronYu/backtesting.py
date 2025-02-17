import requests
import pandas as pd
from datetime import datetime

def execute_signal(file_path: str, commas_secret: str, commas_max_lag: str,
                   commas_exchange: str, commas_ticker: str, commas_bot_uuid: str,
                   strategy_name: str = None):
    """
    执行信号功能：
    读取指定交易对的历史记录 CSV 文件，检查最新 K 线数据的 signal 列中是否存在信号。
    如果存在多个信号（以分号分隔），则逐个处理并向 3commas 发送对应的信号。

    参数:
      file_path: CSV 文件路径
      commas_secret: 3commas 密钥
      commas_max_lag: 最大延迟参数
      commas_exchange: 交易所名称
      commas_ticker: 交易对（ticker）
      commas_bot_uuid: 3commas 机器人的 UUID
      strategy_name: 策略名称，用于验证信号是否匹配当前策略（例如 "strategy_1"）。
                     如果提供此参数，则只有以该名字为前缀的信号会被处理。

    示例发送的 payload 格式如下：
      {
          "secret": commas_secret,
          "max_lag": commas_max_lag,
          "timestamp": "{{timenow}}",
          "trigger_price": "{{close}}",
          "tv_exchange": commas_exchange,
          "tv_instrument": commas_ticker,
          "action": "enter_long",  // 或者 "exit_long", "enter_short", "exit_short"
          "bot_uuid": commas_bot_uuid
      }
    """
    try:
        # 读取 CSV 文件，假定第一列为索引且解析为日期类型
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    if df.empty:
        print("文件无数据")
        return

    # 获取最新一行 K 线数据
    latest_row = df.iloc[-1]
    signals = latest_row.get("signal", "")

    # 调试打印最新 K 线数据及 signal 信息
    print(f"[{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}] 最新含 Signal 的 K 线信息:")
    print(f"K线时间 (UTC): {latest_row.name}")
    print(f"开盘: {latest_row.get('Open', '')}")
    print(f"最高: {latest_row.get('High', '')}")
    print(f"最低: {latest_row.get('Low', '')}")
    print(f"收盘: {latest_row.get('Close', '')}")
    print(f"成交量: {latest_row.get('Volume', '')}")
    print(f"Signal: {signals}")

    if isinstance(signals, str) and signals.strip():
        signals_list = [s.strip() for s in signals.split(';') if s.strip()]
        # 使用最新 K 线的 Close 作为触发价格
        trigger_price = latest_row.get("Close", "")
        # 当前 UTC 时间作为时间戳
        timenow = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        # 3commas webhook 地址
        url = "https://api.3commas.io/signal_bots/webhooks"
        for sig in signals_list:
            action = None
            # 如果提供了策略名称，则验证信号前缀
            if strategy_name:
                if sig.startswith(f"{strategy_name} "):
                    # 移除前缀及空格，获取实际信号
                    command = sig[len(strategy_name) + 1:].strip()
                elif sig.startswith(f"{{{strategy_name}}} "):
                    # 支持大括号包裹的策略前缀，如 "{strategy_name} "
                    # 计算前缀长度：len("{" + strategy_name + "}") + 1 (空格)
                    command = sig[len(strategy_name) + 3:].strip()
                else:
                    print(f"信号 {sig} 不匹配当前策略 {strategy_name}, 已忽略")
                    continue
            else:
                # 未指定策略时按原逻辑处理
                command = sig.strip()

            if command == "enter_long":
                action = "enter_long"
            elif command == "exit_long":
                action = "exit_long"
            elif command == "enter_short":
                action = "enter_short"
            elif command == "exit_short":
                action = "exit_short"
            else:
                print(f"未知信号: {sig}")
                continue

            payload = {
                "secret": commas_secret,
                "max_lag": commas_max_lag,
                "timestamp": timenow,
                "trigger_price": str(trigger_price),
                "tv_exchange": commas_exchange,
                "tv_instrument": commas_ticker,
                "action": action,
                "bot_uuid": commas_bot_uuid
            }
            try:
                response = requests.post(url, json=payload)
                print(f"发送信号 {action} 响应: {response.status_code}, {response.text}")
            except Exception as e:
                print(f"发送信号 {action} 时发生异常: {e}")
    else:
        print("最新K线未产生任何信号") 