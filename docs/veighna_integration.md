# VeighNa 集成指南

> 本文档面向零基础用户，详细介绍如何将 QuantBot 选股系统与 VeighNa 量化交易平台集成。

## 目录

1. [VeighNa 简介](#1-veighna-简介)
2. [安装 VeighNa](#2-安装-veighna)
3. [VeighNa 核心概念](#3-veighna-核心概念)
4. [回测功能](#4-回测功能)
5. [模拟盘交易](#5-模拟盘交易)
6. [实盘交易](#6-实盘交易)
7. [与 QuantBot 集成](#7-与-quantbot-集成)
8. [常见问题](#8-常见问题)

---

## 1. VeighNa 简介

### 1.1 什么是 VeighNa？

VeighNa（原名 vnpy）是一套基于 Python 的开源量化交易程序开发框架，提供从交易 API 对接到策略自动交易的完整解决方案。

**核心特点：**

- **开源免费**：完全开源，无授权费用
- **Python 生态**：充分利用 Python 社区的数据研究和机器学习生态
- **多市场支持**：证券、期货、期权、外盘等
- **完整流程**：数据维护 → 策略开发 → 回测研究 → 实盘交易

### 1.2 VeighNa 能做什么？

```
┌─────────────────────────────────────────────────────────────────┐
│                      VeighNa 功能全景                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   数据管理    │    │   策略开发    │    │   回测研究    │      │
│  │              │    │              │    │              │      │
│  │ • 行情录制   │ →  │ • CTA策略    │ →  │ • 历史回测   │      │
│  │ • 数据下载   │    │ • 组合策略   │    │ • 参数优化   │      │
│  │ • 数据导入   │    │ • 算法交易   │    │ • 结果分析   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│           │                  │                  │               │
│           ▼                  ▼                  ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   模拟交易    │    │   实盘交易    │    │   风险管理    │      │
│  │              │    │              │    │              │      │
│  │ • 本地仿真   │ →  │ • 自动下单   │ →  │ • 流控限制   │      │
│  │ • 实时行情   │    │ • 多接口    │    │ • 持仓监控   │      │
│  │ • 撮合模拟   │    │ • 算法执行   │    │ • 止损止盈   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 交易模式说明

**关于您的问题：VeighNa 是直接对接实盘交易，还是发送信号给交易员？**

VeighNa 支持**两种模式**：

| 模式         | 说明                                   | 适用场景             |
| ------------ | -------------------------------------- | -------------------- |
| **自动交易** | 策略直接通过交易接口下单，无需人工干预 | 高频策略、程序化交易 |
| **信号提示** | 策略生成信号，交易员手动执行           | 需要人工确认的策略   |

对于 QuantBot 的场景（日频选股），推荐：

1. **初期**：信号提示模式，人工确认后执行
2. **成熟后**：自动交易模式，程序自动调仓

---

## 2. 安装 VeighNa

### 2.1 方案一：VeighNa Studio（推荐新手）

VeighNa Studio 是官方提供的一键安装包，包含所有依赖。

**步骤：**

1. **下载安装包**

   - 访问 [VeighNa 官网](https://www.vnpy.com/)
   - 下载 VeighNa Studio 安装包（约 1GB）

2. **安装**

   ```
   1. 右键安装包 → 以管理员身份运行
   2. 选择【快速安装】
   3. 推荐安装路径：C:\veighna_studio
   4. 等待安装完成（约 5-10 分钟）
   ```

3. **验证安装**
   - 桌面出现 VeighNa Station 图标
   - 双击启动，看到主界面即安装成功

### 2.2 方案二：手动安装（适合开发者）

如果您需要更灵活的环境控制：

**前置条件：**

- Python 3.10 64位
- pip 包管理器

**步骤：**

```bash
# 1. 创建虚拟环境（推荐）
python -m venv veighna_env
veighna_env\Scripts\activate

# 2. 下载 VeighNa 源码
# 从 https://github.com/vnpy/vnpy/releases 下载 zip

# 3. 解压后进入目录，运行安装脚本
install.bat

# 4. 安装额外模块（根据需要）
pip install vnpy_ctp          # CTP期货接口
pip install vnpy_xtp          # 中泰XTP股票接口
pip install vnpy_ib           # 盈透证券接口
pip install vnpy_datamanager  # 数据管理模块
pip install vnpy_ctabacktester # CTA回测模块
pip install vnpy_paperaccount  # 模拟交易模块
```

### 2.3 启动 VeighNa Trader

```bash
# 进入 examples/veighna_trader 目录
cd examples/veighna_trader

# 启动
python run.py
```

**run.py 配置示例：**

```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp

# 导入交易接口（根据需要取消注释）
# from vnpy_ctp import CtpGateway        # 期货
# from vnpy_xtp import XtpGateway        # A股
# from vnpy_ib import IbGateway          # 海外

# 导入应用模块
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctabacktester import CtaBacktesterApp
from vnpy_datamanager import DataManagerApp
from vnpy_paperaccount import PaperAccountApp

def main():
    qapp = create_qapp()

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加交易接口
    # main_engine.add_gateway(CtpGateway)
    # main_engine.add_gateway(XtpGateway)

    # 添加应用模块
    main_engine.add_app(CtaStrategyApp)
    main_engine.add_app(CtaBacktesterApp)
    main_engine.add_app(DataManagerApp)
    main_engine.add_app(PaperAccountApp)

    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    qapp.exec()

if __name__ == "__main__":
    main()
```

---

## 3. VeighNa 核心概念

### 3.1 交易接口（Gateway）

交易接口是 VeighNa 与券商/交易所的连接通道。

**国内 A 股常用接口：**

| 接口名称 | 代码           | 支持品种           | 获取方式         |
| -------- | -------------- | ------------------ | ---------------- |
| 中泰 XTP | vnpy_xtp       | A股、两融、ETF期权 | 联系中泰证券开通 |
| 华鑫奇点 | vnpy_torastock | A股                | 联系华鑫证券开通 |
| 东方证券 | vnpy_ost       | A股                | 联系东方证券开通 |
| 国泰君安 | vnpy_hft       | A股、两融          | 联系国泰君安开通 |

**期货接口：**

| 接口名称 | 代码         | 说明             |
| -------- | ------------ | ---------------- |
| CTP      | vnpy_ctp     | 最常用的期货接口 |
| CTP测试  | vnpy_ctptest | SimNow模拟环境   |

**海外接口：**

| 接口名称 | 代码    | 说明           |
| -------- | ------- | -------------- |
| 盈透证券 | vnpy_ib | 支持全球多市场 |

### 3.2 合约代码格式

VeighNa 使用 `vt_symbol` 格式：`合约代码.交易所`

**示例：**

```
600519.SSE    # 贵州茅台（上交所）
000858.SZSE   # 五粮液（深交所）
IF2403.CFFEX  # 沪深300股指期货
rb2405.SHFE   # 螺纹钢期货
```

**交易所代码对照：**

| 交易所         | VeighNa代码 | QuantBot代码 |
| -------------- | ----------- | ------------ |
| 上海证券交易所 | SSE         | SH           |
| 深圳证券交易所 | SZSE        | SZ           |
| 中金所         | CFFEX       | -            |
| 上期所         | SHFE        | -            |
| 大商所         | DCE         | -            |
| 郑商所         | CZCE        | -            |

### 3.3 数据结构

**TickData（逐笔行情）：**

```python
@dataclass
class TickData:
    symbol: str           # 合约代码
    exchange: Exchange    # 交易所
    datetime: datetime    # 时间
    last_price: float     # 最新价
    volume: int           # 成交量
    bid_price_1: float    # 买一价
    ask_price_1: float    # 卖一价
    # ...
```

**BarData（K线数据）：**

```python
@dataclass
class BarData:
    symbol: str
    exchange: Exchange
    datetime: datetime
    interval: Interval    # 周期：分钟/小时/日
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
```

**OrderData（委托数据）：**

```python
@dataclass
class OrderData:
    symbol: str
    exchange: Exchange
    orderid: str
    direction: Direction  # 买/卖
    offset: Offset        # 开/平
    price: float
    volume: float
    status: Status        # 委托状态
```

---

## 4. 回测功能

### 4.1 CTA 回测模块

VeighNa 提供图形化的回测界面，无需编写代码即可进行策略回测。

**启动回测模块：**

1. 启动 VeighNa Trader
2. 菜单栏 → 功能 → CTA回测

**回测流程：**

```
┌─────────────────────────────────────────────────────────────────┐
│                        回测流程                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 准备数据                                                     │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ • 从数据服务下载（RQData、TuShare等）                 │    │
│     │ • 从交易接口下载（IB等）                              │    │
│     │ • 导入CSV文件                                        │    │
│     └─────────────────────────────────────────────────────┘    │
│                              ↓                                  │
│  2. 配置回测参数                                                 │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ • 策略选择：选择要回测的策略类                        │    │
│     │ • 本地代码：如 rb2405.SHFE                           │    │
│     │ • 时间范围：开始日期 ~ 结束日期                       │    │
│     │ • 交易成本：滑点、手续费                              │    │
│     │ • 合约属性：乘数、最小价格变动                        │    │
│     └─────────────────────────────────────────────────────┘    │
│                              ↓                                  │
│  3. 执行回测                                                     │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ • 点击【开始回测】                                    │    │
│     │ • 配置策略参数                                        │    │
│     │ • 等待回测完成                                        │    │
│     └─────────────────────────────────────────────────────┘    │
│                              ↓                                  │
│  4. 分析结果                                                     │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ • 业绩图表：收益曲线、回撤曲线                        │    │
│     │ • 统计指标：年化收益、夏普比率、最大回撤              │    │
│     │ • 详细信息：每笔交易记录                              │    │
│     └─────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 回测参数说明

| 参数     | 说明           | 示例             |
| -------- | -------------- | ---------------- |
| 交易策略 | 策略类名称     | AtrRsiStrategy   |
| 本地代码 | vt_symbol格式  | rb2405.SHFE      |
| K线周期  | 数据频率       | 1分钟/1小时/日线 |
| 开始日期 | 回测起始       | 2023-01-01       |
| 结束日期 | 回测结束       | 2024-01-01       |
| 滑点     | 成交滑点（跳） | 1                |
| 手续费率 | 百分比         | 0.0001           |
| 合约乘数 | 每手数量       | 10               |
| 价格跳动 | 最小变动       | 1                |
| 回测资金 | 初始资金       | 1000000          |

### 4.3 回测结果指标

| 指标       | 说明              |
| ---------- | ----------------- |
| 总收益率   | 回测期间总收益    |
| 年化收益率 | 折算年化收益      |
| 最大回撤   | 最大亏损幅度      |
| 夏普比率   | 风险调整后收益    |
| 胜率       | 盈利交易占比      |
| 盈亏比     | 平均盈利/平均亏损 |

---

## 5. 模拟盘交易

### 5.1 PaperAccount 模块

PaperAccount 是 VeighNa 的本地仿真交易模块，基于**实盘行情**进行模拟撮合。

**特点：**

- 使用真实的实时行情数据
- 本地撮合，不发送到交易所
- 支持限价单、市价单、停止单
- 持仓数据持久化保存

### 5.2 启动模拟交易

**步骤：**

1. **连接行情接口**

   - 启动 VeighNa Trader
   - 连接一个支持行情的接口（如 CTP、XTP）
   - 等待日志显示"合约信息查询成功"

2. **启动模拟交易模块**

   - 菜单栏 → 功能 → 模拟交易
   - 此时所有交易请求将被本地模块接管

3. **订阅行情**

   - 在主界面订阅需要交易的合约行情
   - 必须先订阅行情才能下单

4. **下单交易**
   - 在主界面的交易区域输入委托信息
   - 点击下单，委托将在本地撮合

### 5.3 撮合规则

| 委托类型 | 撮合规则              |
| -------- | --------------------- |
| 限价买入 | 卖一价 ≤ 委托价时成交 |
| 限价卖出 | 买一价 ≥ 委托价时成交 |
| 市价单   | 立即以对手价成交      |
| 停止单   | 触发价格后转为市价单  |

**注意事项：**

- 不考虑盘口挂单量，一次性全部成交
- 资金不做计算，仅记录持仓
- 持仓数据保存在本地文件

---

## 6. 实盘交易

### 6.1 实盘交易流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      实盘交易流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 开通交易接口                                                 │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ • 联系券商开通程序化交易权限                          │    │
│     │ • 获取交易服务器地址、账号密码                        │    │
│     │ • 签署相关协议                                        │    │
│     └─────────────────────────────────────────────────────┘    │
│                              ↓                                  │
│  2. 配置连接参数                                                 │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ • 在 VeighNa Trader 中配置接口参数                    │    │
│     │ • 填写服务器地址、账号、密码等                        │    │
│     │ • 保存配置                                            │    │
│     └─────────────────────────────────────────────────────┘    │
│                              ↓                                  │
│  3. 连接交易接口                                                 │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ • 点击【连接】按钮                                    │    │
│     │ • 等待日志显示"合约信息查询成功"                      │    │
│     │ • 确认账户资金、持仓信息正确                          │    │
│     └─────────────────────────────────────────────────────┘    │
│                              ↓                                  │
│  4. 执行交易                                                     │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ 方式A：手动下单                                       │    │
│     │   • 在交易界面输入委托信息                            │    │
│     │   • 点击下单                                          │    │
│     │                                                       │    │
│     │ 方式B：策略自动交易                                   │    │
│     │   • 启动策略模块（CTA/组合策略）                      │    │
│     │   • 初始化并启动策略                                  │    │
│     │   • 策略自动发出交易信号                              │    │
│     │                                                       │    │
│     │ 方式C：脚本交易                                       │    │
│     │   • 使用 ScriptTrader 编写脚本                        │    │
│     │   • 程序化执行交易逻辑                                │    │
│     └─────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 A 股交易接口开通

以中泰 XTP 为例：

1. **联系券商**

   - 在中泰证券开户
   - 联系客户经理申请 XTP 接口权限
   - 签署《程序化交易协议》

2. **获取接口信息**

   - 交易服务器地址
   - 行情服务器地址
   - 账号、密码
   - 客户号

3. **配置 VeighNa**

   ```python
   # 在 run.py 中添加
   from vnpy_xtp import XtpGateway
   main_engine.add_gateway(XtpGateway)
   ```

4. **连接参数**
   ```json
   {
     "账号": "your_account",
     "密码": "your_password",
     "客户号": 1,
     "行情地址": "120.27.164.138",
     "行情端口": 6002,
     "交易地址": "120.27.164.69",
     "交易端口": 6001,
     "行情协议": "TCP",
     "授权码": "your_auth_code"
   }
   ```

### 6.3 风险管理

VeighNa 提供 RiskManager 模块进行前端风控：

| 风控规则 | 说明               |
| -------- | ------------------ |
| 交易流控 | 限制每秒下单次数   |
| 单笔数量 | 限制单笔委托数量   |
| 活动委托 | 限制未成交委托数量 |
| 撤单总数 | 限制撤单次数       |
| 合约冻结 | 禁止特定合约交易   |

---

## 7. 与 QuantBot 集成

### 7.1 集成架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    QuantBot + VeighNa 集成架构                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    QuantBot 选股系统                      │   │
│  │                                                          │   │
│  │  每日盘后执行 Routine:                                    │   │
│  │  1. 下载最新数据                                          │   │
│  │  2. 计算因子                                              │   │
│  │  3. 模型预测                                              │   │
│  │  4. 生成目标持仓                                          │   │
│  │                                                          │   │
│  │  输出: target_portfolio.json                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    数据交换层                             │   │
│  │                                                          │   │
│  │  方式1: JSON 文件                                         │   │
│  │  方式2: REST API                                          │   │
│  │  方式3: 数据库共享                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    VeighNa 交易系统                       │   │
│  │                                                          │   │
│  │  每日盘前/盘中执行:                                       │   │
│  │  1. 读取目标持仓                                          │   │
│  │  2. 查询当前持仓                                          │   │
│  │  3. 计算调仓差异                                          │   │
│  │  4. 执行交易（自动/手动）                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 数据交换格式

**QuantBot 输出格式（target_portfolio.json）：**

```json
{
  "generated_at": "2026-03-04T16:30:00",
  "target_date": "2026-03-05",
  "benchmark": "000300.SH",
  "total_capital": 10000000,
  "positions": [
    {
      "symbol": "600519.SH",
      "name": "贵州茅台",
      "weight": 0.05,
      "target_value": 500000,
      "target_shares": 300,
      "action": "overweight",
      "score": 0.85
    },
    {
      "symbol": "000858.SZ",
      "name": "五粮液",
      "weight": 0.03,
      "target_value": 300000,
      "target_shares": 2000,
      "action": "underweight",
      "score": 0.72
    }
  ],
  "summary": {
    "total_stocks": 300,
    "overweight_count": 120,
    "underweight_count": 100,
    "neutral_count": 80
  }
}
```

### 7.3 符号转换

QuantBot 和 VeighNa 使用不同的交易所代码：

```python
def convert_quantbot_to_veighna(symbol: str) -> str:
    """
    将 QuantBot 符号转换为 VeighNa 符号

    600519.SH -> 600519.SSE
    000858.SZ -> 000858.SZSE
    """
    code, exchange = symbol.split(".")

    exchange_map = {
        "SH": "SSE",
        "SZ": "SZSE",
    }

    veighna_exchange = exchange_map.get(exchange, exchange)
    return f"{code}.{veighna_exchange}"


def convert_veighna_to_quantbot(vt_symbol: str) -> str:
    """
    将 VeighNa 符号转换为 QuantBot 符号

    600519.SSE -> 600519.SH
    000858.SZSE -> 000858.SZ
    """
    code, exchange = vt_symbol.split(".")

    exchange_map = {
        "SSE": "SH",
        "SZSE": "SZ",
    }

    quantbot_exchange = exchange_map.get(exchange, exchange)
    return f"{code}.{quantbot_exchange}"
```

### 7.4 VeighNa 调仓脚本

使用 ScriptTrader 模块实现自动调仓：

```python
"""
QuantBot 调仓脚本
用于读取 QuantBot 生成的目标持仓并执行调仓
"""
import json
from time import sleep
from datetime import datetime
from vnpy_scripttrader import ScriptEngine


def convert_symbol(quantbot_symbol: str) -> str:
    """符号转换"""
    code, exchange = quantbot_symbol.split(".")
    exchange_map = {"SH": "SSE", "SZ": "SZSE"}
    return f"{code}.{exchange_map.get(exchange, exchange)}"


def load_target_portfolio(filepath: str) -> dict:
    """加载目标持仓"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def run(engine: ScriptEngine):
    """
    脚本主函数
    """
    engine.write_log("=" * 50)
    engine.write_log("QuantBot 调仓脚本启动")
    engine.write_log("=" * 50)

    # 配置参数
    PORTFOLIO_FILE = "C:/quantbot/target_portfolio.json"
    TOTAL_CAPITAL = 10000000  # 总资金

    # 1. 加载目标持仓
    engine.write_log("正在加载目标持仓...")
    try:
        target = load_target_portfolio(PORTFOLIO_FILE)
        engine.write_log(f"目标日期: {target['target_date']}")
        engine.write_log(f"股票数量: {len(target['positions'])}")
    except Exception as e:
        engine.write_log(f"加载目标持仓失败: {e}")
        return

    # 2. 获取当前持仓
    engine.write_log("正在查询当前持仓...")
    current_positions = {}
    for pos in engine.get_all_positions():
        if pos.volume > 0:
            current_positions[pos.vt_symbol] = pos.volume
    engine.write_log(f"当前持仓数量: {len(current_positions)}")

    # 3. 计算调仓差异
    engine.write_log("正在计算调仓差异...")
    orders_to_execute = []

    for item in target["positions"]:
        vt_symbol = convert_symbol(item["symbol"])
        target_shares = item.get("target_shares", 0)
        current_shares = current_positions.get(vt_symbol, 0)

        diff = target_shares - current_shares

        if diff != 0:
            orders_to_execute.append({
                "vt_symbol": vt_symbol,
                "name": item["name"],
                "target": target_shares,
                "current": current_shares,
                "diff": diff,
                "action": "买入" if diff > 0 else "卖出"
            })

    # 4. 显示调仓计划
    engine.write_log("-" * 50)
    engine.write_log("调仓计划:")
    for order in orders_to_execute[:10]:  # 只显示前10条
        engine.write_log(
            f"  {order['name']}({order['vt_symbol']}): "
            f"{order['current']} -> {order['target']} "
            f"({order['action']} {abs(order['diff'])}股)"
        )
    if len(orders_to_execute) > 10:
        engine.write_log(f"  ... 共 {len(orders_to_execute)} 条调仓指令")
    engine.write_log("-" * 50)

    # 5. 执行交易（需要确认）
    engine.write_log("请确认是否执行调仓？(在控制台输入 'yes' 确认)")

    # 注意：实际使用时，这里可以改为自动执行
    # 以下代码演示如何下单

    """
    # 自动执行示例（取消注释启用）
    for order in orders_to_execute:
        vt_symbol = order["vt_symbol"]
        diff = order["diff"]

        # 获取最新行情
        tick = engine.get_tick(vt_symbol)
        if not tick:
            engine.write_log(f"无法获取 {vt_symbol} 行情，跳过")
            continue

        if diff > 0:
            # 买入：以卖一价下单
            price = tick.ask_price_1
            engine.buy(vt_symbol, price, abs(diff))
            engine.write_log(f"买入 {vt_symbol} {abs(diff)}股 @ {price}")
        else:
            # 卖出：以买一价下单
            price = tick.bid_price_1
            engine.sell(vt_symbol, price, abs(diff))
            engine.write_log(f"卖出 {vt_symbol} {abs(diff)}股 @ {price}")

        # 控制下单频率
        sleep(0.5)
    """

    engine.write_log("调仓脚本执行完成")
```

### 7.5 信号提示模式

如果不想自动执行交易，可以生成调仓报告供交易员参考：

```python
def generate_rebalance_report(target_portfolio: dict, current_positions: dict) -> str:
    """
    生成调仓报告
    """
    report = []
    report.append("=" * 60)
    report.append("QuantBot 调仓报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"目标日期: {target_portfolio['target_date']}")
    report.append("=" * 60)
    report.append("")

    # 买入清单
    report.append("【买入清单】")
    report.append("-" * 60)
    buy_orders = []
    for item in target_portfolio["positions"]:
        vt_symbol = convert_symbol(item["symbol"])
        target = item.get("target_shares", 0)
        current = current_positions.get(vt_symbol, 0)
        diff = target - current
        if diff > 0:
            buy_orders.append({
                "name": item["name"],
                "symbol": item["symbol"],
                "shares": diff,
                "value": item.get("target_value", 0) * diff / target if target > 0 else 0
            })

    buy_orders.sort(key=lambda x: x["value"], reverse=True)
    for i, order in enumerate(buy_orders, 1):
        report.append(
            f"{i:3d}. {order['name']:10s} ({order['symbol']:12s}) "
            f"买入 {order['shares']:8d} 股"
        )

    report.append("")

    # 卖出清单
    report.append("【卖出清单】")
    report.append("-" * 60)
    sell_orders = []
    for item in target_portfolio["positions"]:
        vt_symbol = convert_symbol(item["symbol"])
        target = item.get("target_shares", 0)
        current = current_positions.get(vt_symbol, 0)
        diff = target - current
        if diff < 0:
            sell_orders.append({
                "name": item["name"],
                "symbol": item["symbol"],
                "shares": abs(diff)
            })

    for i, order in enumerate(sell_orders, 1):
        report.append(
            f"{i:3d}. {order['name']:10s} ({order['symbol']:12s}) "
            f"卖出 {order['shares']:8d} 股"
        )

    report.append("")
    report.append("=" * 60)
    report.append(f"买入: {len(buy_orders)} 只  |  卖出: {len(sell_orders)} 只")
    report.append("=" * 60)

    return "\n".join(report)
```

### 7.6 QuantBot API 扩展

在 QuantBot 后端添加目标持仓导出 API：

```python
# backend/app/api/v1/portfolio.py

from fastapi import APIRouter, Depends
from app.services.online_serving_service import OnlineServingService

router = APIRouter()

@router.get("/export")
async def export_target_portfolio(
    format: str = "json",
    service: OnlineServingService = Depends()
):
    """
    导出目标持仓

    Args:
        format: 导出格式 (json/csv)

    Returns:
        目标持仓数据
    """
    # 获取最新的目标持仓
    portfolio = service.get_latest_portfolio()

    if format == "csv":
        # 返回 CSV 格式
        return generate_csv(portfolio)
    else:
        # 返回 JSON 格式
        return portfolio
```

---

## 8. 常见问题

### 8.1 安装问题

**Q: 安装时提示 ta-lib 安装失败？**

A: ta-lib 需要预编译的二进制文件：

1. 从 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib 下载对应版本
2. 使用 `pip install TA_Lib‑xxx.whl` 安装

**Q: 启动时提示缺少 DLL？**

A: 安装 Visual C++ Redistributable：

- 下载地址：https://aka.ms/vs/17/release/vc_redist.x64.exe

### 8.2 连接问题

**Q: 连接交易接口失败？**

A: 检查以下几点：

1. 服务器地址和端口是否正确
2. 账号密码是否正确
3. 是否在交易时间内
4. 防火墙是否阻止连接

**Q: 如何获取 A 股交易接口？**

A: 需要联系券商开通：

1. 中泰证券 → XTP 接口
2. 华鑫证券 → 奇点接口
3. 东方证券 → OST 接口
4. 国泰君安 → HFT 接口

### 8.3 策略问题

**Q: 如何将 QuantBot 的选股结果用于 VeighNa 回测？**

A: 目前 VeighNa 的 CTA 回测主要针对单合约策略。对于多股票组合策略，建议：

1. 使用 PortfolioStrategy 模块
2. 或者使用 Python 脚本进行自定义回测

**Q: 调仓频率如何设置？**

A: 对于日频选股策略：

1. 每日收盘后运行 QuantBot 生成目标持仓
2. 次日开盘前/开盘后执行调仓
3. 可以使用 TWAP 算法分散执行，降低冲击成本

### 8.4 风险提示

⚠️ **重要提示：**

1. **模拟先行**：在实盘交易前，务必使用模拟盘充分测试
2. **小资金试水**：初次实盘建议使用小资金测试
3. **监控运行**：自动交易时需要持续监控程序运行状态
4. **风控设置**：务必配置好风险管理规则
5. **备份策略**：保持手动干预的能力，以应对突发情况

---

## 附录

### A. 相关链接

- VeighNa 官网：https://www.vnpy.com/
- VeighNa 文档：https://www.vnpy.com/docs/cn/index.html
- VeighNa GitHub：https://github.com/vnpy/vnpy
- VeighNa 社区论坛：https://www.vnpy.com/forum/

### B. 推荐学习路径

```
1. 安装 VeighNa Studio
       ↓
2. 熟悉 VeighNa Trader 界面
       ↓
3. 使用 DataManager 下载数据
       ↓
4. 使用 CtaBacktester 进行回测
       ↓
5. 使用 PaperAccount 模拟交易
       ↓
6. 学习 ScriptTrader 脚本编写
       ↓
7. 集成 QuantBot 目标持仓
       ↓
8. 申请实盘接口，小资金测试
       ↓
9. 正式实盘运行
```

### C. 版本信息

- 文档版本：1.0
- 更新日期：2026-03-04
- 适用 VeighNa 版本：3.x
- 适用 QuantBot 版本：当前版本
