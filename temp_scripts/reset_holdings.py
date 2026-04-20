#!/usr/bin/env python3
"""
Restore current_holdings.json based on 2026-03-27 target portfolio.
The target_shares from 2026-03-27 represent the holdings AFTER that day's trades.
"""
import json
from pathlib import Path
from datetime import datetime

holdings_file = Path("/app/data/target_portfolio/current_holdings.json")

# Restore holdings based on 2026-03-27 target portfolio (target_shares = actual holdings after trade)
# These are the holdings as of end of 2026-03-27 trading day
restored_holdings = {
    "SH510300": 125000,  # ETF
    "SH600515": 16700,  # 海南机场
    "SZ000166": 12300,  # 申万宏源
    "SZ001391": 10700,  # 国货航
    "SH601018": 13500,  # 宁波港
    "SH600115": 12600,  # 中国东航
    "SH600023": 9600,  # 浙能电力
    "SH600362": 1100,  # 江西铜业
    "SZ300476": 200,  # 胜宏科技
    "SH600795": 10200,  # 国电电力
}

data = {
    "holdings": restored_holdings,
    "updated_at": datetime.now().isoformat(),
    "trade_date": "2026-03-27",
    "position_count": len(restored_holdings),
    "note": "Restored from 2026-03-27 target portfolio (holdings after that day's trades)",
}

with open(holdings_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Holdings restored from 2026-03-27 target portfolio:")
for symbol, shares in restored_holdings.items():
    print(f"  - {symbol}: {shares:,} shares")
print(f"\nTotal positions: {len(restored_holdings)}")
print(f"Saved to: {holdings_file}")
