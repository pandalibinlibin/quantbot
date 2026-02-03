import yfinance as yf
import pandas as pd

# 测试Yahoo Finance的复权价格情况
symbol = "000001.SZ"
print(f"Testing {symbol}")

ticker = yf.Ticker(symbol)

# 默认获取（已复权）
hist_default = ticker.history(start="2024-01-01", end="2024-01-31")
print(f"Default columns: {list(hist_default.columns)}")
print(f"Default Close (已复权): {hist_default['Close'].iloc[0]:.6f}")

# 获取原始价格
hist_raw = ticker.history(start="2024-01-01", end="2024-01-31", auto_adjust=False)
print(f"Raw columns: {list(hist_raw.columns)}")
print(f"Raw Close (原始): {hist_raw['Close'].iloc[0]:.6f}")
if "Adj Close" in hist_raw.columns:
    print(f"Adj Close (前复权): {hist_raw['Adj Close'].iloc[0]:.6f}")
