# QuantBot 技术规格文档

**版本**: 3.2 (Email Notification 完成版)  
**最后更新**: 2026-02-24

---

## 📋 项目概述

QuantBot 是一个基于 **Microsoft Qlib** 和 **FastAPI Full Stack Template** 的 AI 驱动量化投资平台。

### 🎯 核心定位

**本项目的本质是为 Qlib 提供 Web 前端界面**，而不是重新实现量化系统。

### ⚡ 设计原则

1. **完全基于 Qlib Workflow**: 使用 Qlib 官方验证的工作流系统
2. **配置驱动**: 通过配置生成而非手动编码
3. **扩展而非替代**: 只扩展数据源、因子、模型、策略，不重写核心逻辑
4. **简单可靠**: 依赖 Qlib 的稳定性，减少自定义代码

---

## 🏗️ 系统架构

### 架构理念

```
用户请求 → 生成 Qlib Workflow 配置 → 执行 Workflow → 返回结果
```

### 架构分层

```
┌─────────────────────────────────────────────┐
│           Frontend (React + UI)             │
│  - 配置界面（因子/模型/策略选择）            │
│  - 结果展示（训练指标/回测报告）            │
│  - 可视化分析（图表/性能分析）              │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│        Backend API (FastAPI)                │
│  - 配置验证（参数校验）                      │
│  - Workflow 配置生成（转换为 Qlib 格式）     │
│  - 结果存储和查询（数据库持久化）            │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│      Qlib Workflow Executor                 │
│  - 接收配置（Python dict/YAML）             │
│  - 执行 Qlib Workflow（qlib.workflow API）   │
│  - 返回结果（训练指标/预测结果）            │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│         Qlib Core System                    │
│  ┌─────────────────────────────────────┐   │
│  │  Data Layer (扩展点)                 │   │
│  │  - Qlib 内置数据源                   │   │
│  │  - 自定义数据源 (扩展)               │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Factor Layer (扩展点)               │   │
│  │  - Alpha158/Alpha360 (内置)         │   │
│  │  - 自定义因子引擎 (扩展)             │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Model Layer (扩展点)                │   │
│  │  - LGBModel/LinearModel (内置)      │   │
│  │  - 自定义模型 (扩展)                 │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Strategy Layer (扩展点)             │   │
│  │  - TopkDropout (内置)                │   │
│  │  - 自定义策略 (扩展)                 │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 架构优势

1. ✅ **简单清晰**: 只负责配置生成和结果展示
2. ✅ **稳定可靠**: 依赖 Qlib 官方验证的 workflow
3. ✅ **易于扩展**: 通过插件机制扩展各层组件
4. ✅ **符合定位**: 真正的"Qlib 前端"，而不是"Qlib 替代品"

### 插件化架构设计

**核心理念**：Workflow 执行器保持稳定，通过配置文件插拔不同组件

```
配置文件 (YAML/Dict)
    ↓
Workflow 执行器 (通用，基本不变)
    ↓
├─ Data Handler (可插拔组件)
├─ Model (可插拔组件)
└─ Strategy (可插拔组件)
```

**设计优势**：

- **高度解耦**：Workflow 不关心具体用什么数据源、因子、模型
- **易于扩展**：新增组件不需要修改 Workflow 代码，只需实现标准接口
- **配置驱动**：同一个 Workflow 可以运行不同的策略，通过配置文件切换
- **可复用性强**：组件可以在不同 Workflow 中复用

**扩展点**：

1. **Data Collector** (数据采集器)

   - 继承 `BaseCollector`
   - 实现 `collect_data()` 方法
   - 数据格式统一为 Qlib 格式

2. **Factor Handler** (因子引擎)

   - 继承 `DataHandlerLP`
   - 定义因子表达式（使用 Qlib 表达式语言）
   - 配置 Processor（归一化、去极值等）

3. **Model** (模型)

   - 继承 `ModelFT` 或 `Model`
   - 实现 `fit()` 和 `predict()` 方法
   - 支持 MLflow 跟踪

4. **Strategy** (策略)
   - 继承 `BaseStrategy` 或 `WeightStrategyBase`
   - 实现 `generate_trade_decision()` 方法
   - 支持回测和实盘

---

## 🛠️ 技术栈

### 前端

- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **UI 库**: TailwindCSS + shadcn/ui
- **状态管理**: React Query (TanStack Query)
- **图表**: Recharts / ECharts

### 后端

- **框架**: FastAPI
- **ORM**: SQLModel
- **数据库**: PostgreSQL
- **缓存**: Redis
- **任务队列**: (待定，可能使用 Celery)

### 量化引擎

- **核心**: Microsoft Qlib
- **数据存储**: Qlib 二进制格式 (.bin)
- **工作流**: Qlib Workflow API

### 部署

- **容器化**: Docker + Docker Compose
- **反向代理**: Traefik
- **环境**: Development / Production

---

## 📦 核心功能模块

### 1. Workflow 配置生成器

**职责**: 将用户输入转换为 Qlib Workflow 配置

**输入**:

- 因子选择（Alpha158, Alpha360, 自定义）
- 模型选择（LGBModel, LinearModel, 自定义）
- 数据范围（开始日期、结束日期、训练/验证比例）
- 模型参数（超参数配置）

**输出**:

```python
{
    "task": {
        "model": {
            "class": "LGBModel",
            "module_path": "qlib.contrib.model.gbdt",
            "kwargs": {...}
        },
        "dataset": {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {...},
                "segments": {...}
            }
        },
        "record": [...]
    }
}
```

### 2. Workflow 执行器

**职责**: 执行 Qlib Workflow 并返回结果

**核心代码**:

```python
from qlib.workflow import R
from qlib.utils import init_instance_by_config

with R.start(experiment_name=f"exp_{task_id}"):
    model = init_instance_by_config(config["task"]["model"])
    dataset = init_instance_by_config(config["task"]["dataset"])

    model.fit(dataset)

    recorder = R.get_recorder()
    metrics = recorder.list_metrics()
```

### 3. 结果存储和查询

**职责**: 持久化训练结果，提供查询接口

**存储内容**:

- 训练任务配置
- 训练指标（IC, Rank IC, MSE 等）
- 模型文件路径
- 训练日志

### 4. 扩展点管理

**职责**: 注册和管理自定义组件

**扩展点**:

- 自定义数据源
- 自定义因子引擎
- 自定义模型
- 自定义策略

---

## 🗂️ 数据库设计

### 核心表

保留现有的数据库模型定义（`app/models.py`），用于：

- 用户管理
- 任务记录
- 结果存储
- 配置管理

**注意**: 不存储原始市场数据和因子数据，这些由 Qlib 管理。

---

## 🎯 关键技术决策

### 数据对齐策略

**问题**: 如何处理数据时间范围对齐？

**决策**: 完全依赖 Qlib 的自动对齐机制

- Handler 层只需指定整体数据范围（`start_time`, `end_time`）
- Dataset 层通过 `segments` 自动切分训练/验证/测试集
- Qlib 内部自动处理：
  - 交易日对齐
  - 因子计算所需的历史数据
  - 标签计算的未来数据
  - 缺失值和边界情况

**优势**: 避免手动管理数据对齐导致的 NaN 和错误

### 用户和数据管理

**决策**: 单用户系统 + 共享数据目录

```python
QLIB_DATA_DIR = "/app/qlib_data"      # 所有用户共享
QLIB_MLRUNS_DIR = "/app/mlruns"      # 所有实验记录共享
```

**原因**: 简化系统复杂度，专注核心功能

### 性能优化策略

**决策**: 使用 Qlib 所有内置加速机制

启用的加速功能：

- **ExpressionCache**: 因子表达式缓存
- **DatasetCache**: 数据集缓存
- **Redis Cache**: 分布式缓存（使用 Docker Compose 中的 Redis）
- **多进程并行**: 数据加载和因子计算

```python
qlib.init(
    provider_uri=QLIB_DATA_DIR,
    region=REG_CN,
    redis_host="redis",
    redis_port=6379,
    expression_cache=True,
    dataset_cache=True
)
```

### 扩展点实现顺序

**决策**: 数据源 → 因子引擎 → 模型 → 策略

**原因**:

1. 数据源：先能获取数据
2. 因子引擎：基于数据计算因子
3. 模型：基于因子训练模型
4. 策略：基于模型预测生成交易决策

每个阶段都可以独立测试验证。

### 配置界面设计

**决策**: 完整配置 + 预设模板

**预设模板示例**:

```python
TEMPLATES = {
    "lightgbm_alpha158": {
        "name": "LightGBM + Alpha158",
        "description": "默认配置，适合快速开始",
        "config": {...}
    },
    "linear_alpha360": {
        "name": "线性模型 + Alpha360",
        "description": "更多因子，适合大规模数据",
        "config": {...}
    }
}
```

**优势**:

- 新手可以快速开始（使用模板）
- 高级用户可以精细调整（完整配置）

---

## 🚀 开发计划

### Phase 1: 核心 Workflow 执行器 ✅ 已完成

**目标**: 实现基础的 Workflow 执行能力

**任务**:

- [x] 研究 Qlib workflow 文档和示例
- [x] 实现 `QlibWorkflowService`
  - [x] 初始化 Qlib
  - [x] 执行训练 workflow 配置
  - [x] 返回训练结果和指标
- [x] 使用 Qlib 内置组件验证全流程
  - [x] Alpha158 因子
  - [x] LGBModel 模型
  - [x] 完整的训练和评估
- [x] 下载 Qlib 数据
  - [x] 获取官方数据下载脚本
  - [x] 下载中国市场数据（3877 只股票）
- [x] 修复并测试完整工作流
  - [x] 修复数据传递 Bug
  - [x] 测试通过（25.4 秒完成训练）

**验证结果**: ✅ 测试通过

```python
# 成功执行的配置
config = {
    "task": {
        "model": {"class": "LGBModel", ...},
        "dataset": {
            "kwargs": {
                "handler": {"class": "Alpha158", ...},
                "segments": {
                    "train": ("2019-01-01", "2020-06-30"),
                    "valid": ("2020-07-01", "2020-09-30"),
                    "test": ("2020-10-01", "2020-12-31")
                }
            }
        }
    }
}
result = workflow_service.execute_training_workflow(config)
# 返回: {"status": "success", "predictions_count": 0, "model_saved": True}
```

---

### Phase 2: API 和回测工作流 (当前阶段)

**目标**: 暴露训练 API 并实现回测工作流

#### 2.1 训练 API (1-2 天)

**任务**:

- [ ] 创建 API 路由 `POST /api/v1/workflows/training`
  - [ ] 定义请求/响应模型（Pydantic）
  - [ ] 集成 `QlibWorkflowService.execute_training_workflow()`
  - [ ] 添加异常处理和日志
- [ ] 通过 Swagger UI 测试 API
  - [ ] 测试成功场景
  - [ ] 测试错误处理
  - [ ] 验证响应格式

**验证标准**:

- API 能够接收配置并返回训练结果
- Swagger UI 文档完整且可用
- 错误处理友好

#### 2.2 回测工作流 (3-5 天)

**任务**:

- [ ] 研究 Qlib 回测系统
  - [ ] 阅读 Qlib 回测文档
  - [ ] 理解 Strategy 和 Backtest 接口
  - [ ] 学习 TopkDropoutStrategy 示例
- [ ] 实现 `execute_backtest_workflow()`
  - [ ] 加载训练好的模型
  - [ ] 生成预测信号
  - [ ] 执行策略回测
  - [ ] 计算性能指标（收益、夏普比率、最大回撤等）
- [ ] 创建回测 API `POST /api/v1/workflows/backtest`
- [ ] 测试验证

**验证标准**:

- 能够加载模型并生成预测
- 回测结果包含完整的性能指标
- API 正常工作

---

### Phase 3: 推理和模拟盘工作流 (1-2 周)

#### 3.1 推理工作流

**目标**: 使用训练好的模型生成实时预测

**任务**:

- [ ] 实现 `execute_inference_workflow()`
  - [ ] 加载最新模型
  - [ ] 获取最新数据
  - [ ] 生成预测信号
  - [ ] 返回交易建议
- [ ] 创建推理 API `POST /api/v1/workflows/inference`
- [ ] 支持批量预测和单次预测

#### 3.2 模拟盘工作流

**目标**: 实时模拟交易

**任务**:

- [ ] 实现 `execute_paper_trading_workflow()`
  - [ ] 实时获取市场数据
  - [ ] 生成交易信号
  - [ ] 模拟执行交易
  - [ ] 跟踪持仓和收益
- [ ] 创建模拟盘 API
- [ ] 实现持仓管理和风控

---

### Phase 4: 扩展组件库 (持续进行)

**目标**: 扩展数据源、因子、模型、策略

#### 4.1 数据源扩展

**优先级**: 高

**任务**:

- [ ] 实现 `TushareCollector`（中国 A 股专业数据）
  - [ ] 支持日线、分钟线数据
  - [ ] 支持基本面数据
  - [ ] 支持财务数据
- [ ] 实现 `AkshareCollector`（开源金融数据）
  - [ ] 支持多市场数据
  - [ ] 支持宏观经济数据
- [ ] 实现 `LocalCSVCollector`（本地 CSV 文件）
  - [ ] 支持自定义格式
  - [ ] 数据验证和清洗

**扩展点**: 继承 `BaseCollector`，实现 `collect_data()` 方法

#### 4.2 因子引擎扩展

**优先级**: 中

**任务**:

- [ ] 实现自定义技术指标因子
  - [ ] MACD、RSI、布林带等
  - [ ] 动量因子、波动率因子
- [ ] 实现基本面因子
  - [ ] PE、PB、ROE 等
  - [ ] 财务指标因子
- [ ] 实现情绪因子
  - [ ] 新闻情绪
  - [ ] 社交媒体情绪

**扩展点**: 继承 `DataHandlerLP`，定义因子表达式

#### 4.3 模型扩展

**优先级**: 中

**任务**:

- [ ] 集成 XGBoost 模型
- [ ] 集成 CatBoost 模型
- [ ] 实现深度学习模型
  - [ ] LSTM
  - [ ] Transformer
  - [ ] GRU
- [ ] 实现集成学习模型

**扩展点**: 继承 `ModelFT` 或 `Model`，实现 `fit()` 和 `predict()`

#### 4.4 策略扩展

**优先级**: 低（先完成回测工作流）

**任务**:

- [ ] 实现多因子选股策略
- [ ] 实现行业轮动策略
- [ ] 实现对冲策略
- [ ] 实现自适应策略

**扩展点**: 继承 `BaseStrategy`，实现 `generate_trade_decision()`

---

### Phase 5: 前端开发 (2-3 周)

**目标**: 实现 Web 界面

**任务**:

- [ ] 训练配置界面
- [ ] 回测配置界面
- [ ] 结果展示界面
- [ ] 性能分析图表
- [ ] 模型管理界面

---

### Phase 6: 优化和部署 (1-2 周)

**目标**: 性能优化和生产部署

**任务**:

- [ ] 性能优化
  - [ ] 缓存优化
  - [ ] 并行计算
  - [ ] 数据库查询优化
- [ ] 生产部署
  - [ ] Docker 镜像优化
  - [ ] 监控和日志
  - [ ] 备份和恢复

---

## 📋 当前工作重点

**Phase 2.1: 创建训练 API** (选项 A)

1. 创建 API 路由暴露训练工作流
2. 通过 Swagger UI 测试 API
3. 验证端到端流程

**下一步**: 实现回测工作流

---

### Phase 2: 配置生成器 (暂缓)

**目标**: 将用户输入转换为 Qlib 配置

**任务**:

- [ ] 实现 `ConfigGeneratorService`
  - 模型配置生成
  - 数据集配置生成
  - 配置验证
- [ ] 实现配置模板管理
  - 预设模板定义
  - 模板加载和应用
- [ ] 实现配置持久化
  - 保存用户配置
  - 配置版本管理

### Phase 3: 数据源扩展 (1周)

**目标**: 支持自定义数据源

**任务**:

- [ ] 实现 `CustomDataLoader` 基类
- [ ] 集成 Yahoo Finance
- [ ] 集成 tushare
- [ ] 集成 akshare
- [ ] 实现数据源注册机制

### Phase 4: 因子引擎扩展 (1周)

**目标**: 支持自定义因子

**任务**:

- [ ] 实现 `CustomFactorHandler` 基类
- [ ] 提供因子表达式编辑器
- [ ] 实现因子注册机制
- [ ] 提供常用因子模板

### Phase 5: 模型扩展 (1周)

**目标**: 支持自定义模型

**任务**:

- [ ] 实现 `CustomModel` 基类
- [ ] 集成常用模型（PyTorch/TensorFlow）
- [ ] 实现模型注册机制
- [ ] 提供模型模板

### Phase 6: 策略扩展 (1周)

**目标**: 支持自定义策略

**任务**:

- [ ] 实现 `CustomStrategy` 基类
- [ ] 提供策略模板
- [ ] 实现策略注册机制
- [ ] 集成回测功能

### Phase 7: API 端点 (1周)

**目标**: 提供完整的 REST API

**任务**:

- [ ] 实现 workflow 管理 API
- [ ] 实现配置管理 API
- [ ] 实现扩展点管理 API
- [ ] 实现结果查询 API
- [ ] 编写 API 文档

### Phase 8: 前端集成 (2周)

**目标**: 提供用户友好的界面

**任务**:

- [ ] 配置向导界面
- [ ] 模板选择界面
- [ ] 训练监控界面
- [ ] 结果分析界面
- [ ] 扩展点管理界面

---

## 📝 开发规范

### 代码规范

- 注释使用英文
- 遵循 PEP 8 (Python) 和 ESLint (TypeScript)
- 不硬编码，使用配置文件
- 考虑国际化支持

### Git 工作流

- 功能开发使用 master 分支
- 提交信息遵循 Conventional Commits
- 每次提交前更新此文档

### 测试要求

- 关键路径必须有集成测试
- API 端点必须有 E2E 测试

---

## 📚 参考资料

- [Qlib 官方文档](https://qlib.readthedocs.io/)
- [Qlib GitHub](https://github.com/microsoft/qlib)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [FastAPI Full Stack Template](https://github.com/tiangolo/full-stack-fastapi-template)

---

## 👥 合作模式

### 开发协作规则

本项目采用**教学式协作开发模式**，遵循以下原则：

#### 1. 一次只推进一小步

- ✅ 每次只创建/修改一个小的代码片段
- ✅ 完成一步后检查，再进行下一步
- ❌ 不要一次性给出大量代码

#### 2. 先教知识，再写代码

- ✅ 先解释涉及的概念和背景知识
- ✅ 用生活类比帮助理解
- ✅ 讲解设计模式和架构思想
- ❌ 不要直接给代码而不解释

#### 3. 代码修改流程

- ✅ AI 说明要改哪里、为什么改
- ✅ 用户执行修改
- ✅ AI 检查结果
- ❌ AI 不直接修改代码（除非特别说明）

#### 4. 命令执行流程

- ✅ AI 给出命令
- ✅ 用户执行命令
- ✅ 用户粘贴结果
- ✅ AI 检查结果
- ❌ AI 不直接执行命令

#### 5. 详细解释要求

- **前端部分**: 详细讲解（用户只会基本 JavaScript，无 React 经验）
- **Qlib 部分**: 详细讲解（用户对 Qlib 一无所知）
- **金融知识**: 讲解背景知识（用户知识有限）
- **设计模式**: 讲解架构和设计模式（用户缺乏相关经验）

#### 6. 基于 Qlib 文档开发

- ✅ 仔细研究 Qlib 官方文档 (`docs/qlib-html`)
- ✅ 使用 Qlib 提供的机制，不重复造轮子
- ✅ 扩展 Qlib，而不是改写 Qlib

#### 7. 文档管理

- ✅ 使用 `tech_spec.md` 记录开发过程
- ✅ 每次提交前更新文档
- ✅ AI 可以直接编辑 `tech_spec.md`

#### 8. 代码规范

- ✅ 注释使用英文
- ✅ 不要硬编码
- ✅ 考虑多语言支持

#### 9. 开发流程

- ✅ 先通过 Swagger UI 测试后端 API
- ✅ 后端测试通过后再做前端

### 示例：创建文件的正确流程

```
步骤 1: 讲解概念
- 解释这个文件的作用
- 讲解涉及的技术概念
- 用类比帮助理解

步骤 2: 创建基础结构
- 只创建类定义和文档字符串
- 不包含复杂逻辑

步骤 3: 检查基础结构
- 用户创建文件
- AI 检查拼写和格式

步骤 4: 逐个添加方法
- 一次只添加一个方法
- 解释方法的作用
- 检查后再继续

步骤 5: 完整测试
- 所有方法添加完成后
- 编写测试脚本验证
```

---

## 🔄 数据源模块重新设计 (2026-02-14)

### 📊 现状分析

通过深入研究Qlib源码和文档，发现我们当前的数据源实现存在以下问题：

**当前实现问题**：

1. **架构不符合Qlib标准**：直接调用脚本，未使用Qlib BaseCollector架构
2. **扩展性限制**：每个新数据源需要新脚本和API端点，代码重复
3. **缺少标准化接口**：没有统一的Collector接口，难以插件化扩展
4. **错误处理不完善**：缺少Qlib标准的重试、并发控制、数据验证机制

### 🎯 新架构设计

基于Qlib官方BaseCollector标准，重新设计数据源模块：

#### 目录结构

```
backend/app/services/data_collectors/
├── __init__.py                 # 模块初始化和导出
├── base.py                     # BaseDataCollector (继承Qlib BaseCollector)
├── exceptions.py               # 数据收集异常定义
├── registry.py                 # 收集器注册机制 (工厂模式)
├── yahoo_collector.py          # Yahoo数据收集器
├── tushare_collector.py        # Tushare数据收集器 (未来)
├── akshare_collector.py        # AKShare数据收集器 (未来)
└── csv_collector.py            # 本地CSV收集器 (未来)
```

#### 核心设计原则

1. **标准化接口**：所有收集器继承BaseDataCollector，实现统一接口
2. **插件化架构**：通过注册机制自动发现和管理收集器
3. **配置驱动**：通过配置文件定义数据源参数和字段映射
4. **Qlib兼容**：完全符合Qlib BaseCollector标准，利用其并发、重试、验证机制

#### 架构优势

- ✅ **符合Qlib标准**：使用官方BaseCollector架构
- ✅ **高度可扩展**：新数据源只需实现标准接口并注册
- ✅ **统一错误处理**：利用Qlib的重试和错误恢复机制
- ✅ **高性能**：支持并发收集和数据验证
- ✅ **API兼容**：保持现有前端和API接口不变

### 🚀 实施计划

#### 阶段1：基础架构 (1-2天)

1. **更新tech_spec.md**：记录新设计方案 ✅
2. **清理旧代码**：删除不需要的脚本和实现
3. **创建目录结构**：建立新的data_collectors模块
4. **实现基础框架**：
   - `exceptions.py` - 异常定义
   - `base.py` - BaseDataCollector基类
   - `registry.py` - 注册机制

#### 阶段2：Yahoo收集器重构 (2-3天)

1. **实现YahooCollector**：基于Qlib BaseCollector标准
2. **集成注册机制**：自动注册和发现
3. **重构data_utils.py**：使用新的收集器架构
4. **保持API兼容**：确保现有API正常工作

#### 阶段3：测试和验证 (1天)

1. **功能测试**：验证数据收集功能正常
2. **性能测试**：对比新旧实现的性能
3. **API测试**：确保前端集成无问题

#### 阶段4：扩展数据源 (未来)

1.  **Tushare收集器**：中国A股专业数据
2.  **AKShare收集器**：开源金融数据
3.  **CSV收集器**：本地文件导入

                end_datetime: pd.Timestamp) -> pd.DataFrame:
        """Collect data for specific symbol and time range"""

````

#### 收集器注册机制

```python
class CollectorRegistry:
    """Factory pattern for data collector management"""

    _collectors = {}

    @classmethod
    def register(cls, name: str, collector_class: Type[BaseDataCollector]):
        """Register a data collector"""

    @classmethod
    def get_collector(cls, name: str, **kwargs) -> BaseDataCollector:
        """Get collector instance by name"""

    @classmethod
    def list_collectors(cls) -> List[str]:
        """List all registered collectors"""
````

#### 服务层接口重构

```python
class DataCollectorService:
    """Unified service layer for data collection"""

    def collect_data(self, source: str, **params) -> CollectionResult:
        """Collect data using specified source"""

    def get_available_sources(self) -> List[DataSourceInfo]:
        """Get list of available data sources"""

    def validate_source_params(self, source: str, params: dict) -> ValidationResult:
        """Validate parameters for specific data source"""
```

### 🔄 迁移策略

1. **保持API兼容**：现有的`/api/v1/data/`端点保持不变
2. **渐进式迁移**：先实现Yahoo收集器，验证后再扩展其他数据源
3. **配置驱动**：通过配置文件管理数据源参数，无需修改代码
4. **向后兼容**：保留旧的data_utils.py接口，内部使用新架构

---

## 🐛 pkg_resources 错误解决方案 (2026-02-16)

### 问题描述

在Docker backend容器启动时遇到 `ModuleNotFoundError: No module named 'pkg_resources'` 错误，导致FastAPI服务无法正常启动。

### 根本原因分析

1. **缺少setuptools依赖**：`pkg_resources` 是 `setuptools` 包的一部分，但在 `pyproject.toml` 中没有显式声明
2. **依赖版本漂移**：关键依赖包（`pyqlib`、`mlflow`）没有锁定版本范围，可能导致兼容性问题
3. **git submodule冲突**：之前添加的 `qlib-source` git submodule 可能导致路径冲突和依赖解析问题

### 解决方案

#### 1. 添加setuptools显式依赖

在 `backend/pyproject.toml` 中添加：

```toml
dependencies = [
    # ... 其他依赖
    "setuptools>=68.0,<70.0",  # 提供pkg_resources模块
]
```

#### 2. 锁定关键依赖版本

```toml
dependencies = [
    "pyqlib>=0.9.0,<0.10.0",   # 锁定pyqlib版本范围
    "mlflow>=2.0.0,<3.0.0",    # 锁定mlflow版本范围
    "setuptools>=68.0,<70.0",  # 锁定setuptools版本范围
    # ... 其他依赖
]
```

#### 3. 移除qlib-source git submodule

```bash
# 完全移除git submodule
git submodule deinit -f qlib-source
git rm qlib-source
del .gitmodules
```

#### 4. 配置.gitignore和.dockerignore

为了支持研究用途的qlib源代码，但不影响Docker构建：

**.gitignore**:

```
# Qlib source code for research purposes only
qlib-source/
```

**backend/.dockerignore**:

```
# Qlib source code (research only, not for Docker)
../qlib-source
```

#### 5. 修改Dockerfile构建策略

移除 `--frozen` 参数，让Docker自动生成 `uv.lock`：

```dockerfile
# 修改前
RUN uv sync --frozen

# 修改后
RUN uv sync
```

### 实施步骤

1. ✅ **删除现有uv.lock文件**
2. ✅ **修改pyproject.toml添加setuptools依赖**
3. ✅ **锁定关键依赖版本**
4. ✅ **移除qlib-source git submodule**
5. ✅ **配置.gitignore和.dockerignore**
6. ✅ **重新构建backend镜像**
7. ✅ **验证服务正常启动**

### 验证结果

- ✅ Backend容器成功启动，状态为 "healthy"
- ✅ FastAPI服务运行在 http://0.0.0.0:8000
- ✅ 健康检查端点正常响应
- ✅ 没有pkg_resources相关错误
- ✅ 所有服务正常运行

### 经验教训

1. **显式声明依赖**：即使是Python标准库的一部分，也应该在依赖中显式声明
2. **版本锁定重要性**：关键依赖应该锁定版本范围，避免意外的版本漂移
3. **Docker构建隔离**：确保研究用代码不会意外影响生产环境的Docker构建
4. **git submodule管理**：谨慎使用git submodule，可能导致意外的路径冲突

### 后续计划

现在backend服务已经稳定运行，可以继续：

1. 在根目录创建qlib-source目录用于研究Alpha158等因子实现
2. 恢复和运行测试脚本验证Yahoo Finance数据功能
3. 继续开发数据收集和因子工程功能

---

## ✅ 分钟数据系统验证完成 (2026-02-17)

### 📊 验证成果

成功完成了分钟级数据收集、处理和验证的完整系统，确保数据pipeline的准确性和可靠性。

#### 核心验证指标

1. **数据一致性验证** ✅

   - Yahoo Finance API → CSV → Qlib bin 全流程验证
   - 所有OHLCV数据数值完全一致（差异0.000000）
   - 330条分钟记录完整覆盖交易时段（09:30-14:59）

2. **前端显示验证** ✅

   - Date Range: `2026-02-10 to 2026-02-10`
   - Features: `close.1min`, `high.1min`, `low.1min`, `open.1min`, `volume.1min`
   - Data Interval: `Minute (1m)`
   - 295个股票数据状态正确显示

3. **后端API验证** ✅

   - `/api/v1/data-source/status` 正确返回分钟数据元数据
   - 支持1min.txt日历文件解析
   - data_range_start/data_range_end 不再为null

4. **Qlib数据结构验证** ✅
   - 正确的`.1min.bin`特征文件（close, high, low, open, volume）
   - 正确的`1min.txt`日历文件
   - 文件大小和时间戳正确

#### 关键技术修复

1. **频率检测动态化** ✅

   - 自动检测CSV数据时间间隔
   - 动态设置Qlib转换频率参数
   - 修复硬编码freq="day"问题

2. **数据标准化优化** ✅

   - 跳过分钟数据的日频日历对齐
   - 保持分钟级数据精度
   - 异常时间戳过滤机制

3. **后端API增强** ✅

   - 支持多种日历文件格式（1min.txt, day.txt）
   - 正确提取分钟数据的日期部分
   - 元数据解析逻辑完善

4. **前端界面优化** ✅
   - 修复双按钮加载动画问题
   - 正确显示分钟数据特征
   - Date Range显示逻辑修复

#### 数据质量保证

- **异常过滤**: 1条异常时间戳正确过滤
- **数据完整性**: CSV vs Qlib 100%一致性
- **时间精度**: 分钟级时间戳保持完整
- **市场覆盖**: 295个CSI300股票完整支持

### 🔧 验证工具开发

创建了完整的数据一致性验证脚本(`verify_data_consistency.py`)：

- **多源数据比较**: Yahoo API vs CSV vs Qlib bin
- **股票代码自动匹配**: 支持不同命名格式
- **频率自适应查询**: 自动处理1min和1d数据
- **详细统计报告**: 差异分析和成功率统计

### 📈 系统状态

**分钟数据系统已完全就绪**，可安全用于：

- 因子工程开发
- 模型训练和回测
- 策略开发和验证
- 生产环境部署

---

## 🎉 数据收集管道完整实现 (2026-02-16)

### 📋 实现概述

成功完成了Qlib数据收集管道的完整开发和测试，包括Yahoo Finance数据源集成、跨市场数据管理、增量下载、数据规范化和Qlib格式转换。

### 🚀 主要成就

#### 1. Yahoo Finance数据收集器 ✅

**核心功能**：

- 支持日线(1d)和分钟线(1m)数据下载
- 支持CN市场(csi300, csi500)和US市场(sp500, nasdaq100)
- 完整的OHLCV数据字段
- 自动股票池管理和代表性指数选择

**技术实现**：

- 基于yahooquery库的高性能数据获取
- 并发下载机制，支持最多8个并发请求
- 完善的错误处理和重试机制
- 详细的进度日志和成功率统计

#### 2. 跨市场数据存储分离 ✅

**存储架构**：

```
/app/csv_data/
├── cn_data/     # 中国市场CSV数据
└── us_data/     # 美国市场CSV数据

/app/qlib_data/  # Qlib二进制数据(统一存储)
├── calendars/   # 交易日历
├── instruments/ # 股票列表
└── features/    # OHLCV特征数据
```

**市场识别逻辑**：

- CN市场：csi300, csi500 → 使用000001.SS作为代表指数
- US市场：sp500, nasdaq100 → 使用SPY作为代表指数
- 自动region设置：CN→"cn", US→"us"

#### 3. 增量下载功能 ✅

**智能增量更新**：

- 自动检测现有Qlib数据的日期范围
- 计算缺失的日期区间
- 只下载缺失的数据，避免重复下载
- 支持CSV数据合并和去重

**日期范围检测**：

- 使用Qlib交易日历进行精确的日期对齐
- 支持跨年度的增量更新
- 自动处理交易日和非交易日

#### 4. 数据规范化系统 ✅

**UniversalNormalize模块**：

- 支持多市场交易日历(CN/US)
- Yahoo Finance真实交易日历获取
- 数据对齐和缺失值处理
- 类级别缓存机制，避免重复获取日历

**交易日历管理**：

- 优先使用Qlib内置日历
- Fallback到Yahoo Finance真实交易日历
- 支持1538个交易日的完整日历缓存

#### 5. 边界处理修复 ✅

**Yahoo Finance API边界问题**：

- 发现并修复Yahoo Finance API的end参数排他性问题
- 自动将结束日期+1天，确保包含请求的最后一天
- 验证修复效果：请求到2024-01-31，确实获取到2024-01-31的数据

#### 6. 元数据记录系统 ✅

**准确的状态报告**：

- Pipeline完成后自动保存metadata.json文件
- 记录准确的stock_pool、market、region等信息
- Status API优先读取元数据，避免错误推断
- 支持所有4种stock_pool：csi300, csi500, sp500, nasdaq100

### 🔧 技术架构

#### 数据收集管道流程

```
用户请求 → 参数验证 → 增量检测 → 并发下载 → 数据规范化 → Qlib转换 → 元数据保存
    ↓           ↓           ↓           ↓           ↓           ↓           ↓
API接收 → 市场识别 → 日期计算 → Yahoo API → 交易日历 → dump_bin → metadata.json
```

#### 核心组件

1. **YahooDataCollector**

   - 继承BaseCollector标准接口
   - 支持多种时间间隔(1d, 1m)
   - 自动字段映射和数据清洗

2. **UniversalNormalize**

   - 市场感知的数据规范化
   - 交易日历缓存和管理
   - 数据对齐和质量保证

3. **Pipeline Service**

   - 端到端的数据处理流程
   - 增量下载逻辑
   - 错误处理和恢复

4. **Status API**
   - 基于元数据的准确状态报告
   - 数据范围和质量统计
   - 存储大小和更新时间

### 📊 测试验证结果

#### CN市场测试 ✅

- 股票池：csi300 (296只股票)
- 数据范围：2024-01-29 到 2024-01-31
- 成功率：98.6%
- 数据大小：0.03MB

#### US市场测试 ✅

- 股票池：sp500 (497只股票)
- 数据范围：2024-01-16 到 2024-01-16
- 成功率：98.6%
- 数据大小：0.03MB
- Status API正确显示"sp500"

#### 增量下载测试 ✅

- 自动检测现有数据范围
- 只下载缺失的2024-01-31数据
- CSV数据成功合并和去重
- 边界处理完全正确

#### 边界处理测试 ✅

- 修复前：请求2024-01-31，实际只到2024-01-30
- 修复后：请求2024-01-31，正确获取到2024-01-31
- Yahoo Finance API排他性问题完全解决

### 🛠️ 核心修复和优化

#### 1. 日期类型不匹配修复

```python
# 修复增量下载中的日期类型不匹配
if not isinstance(existing_df.index, pd.DatetimeIndex):
    existing_df.index = pd.to_datetime(existing_df.index)
if not isinstance(df.index, pd.DatetimeIndex):
    df.index = pd.to_datetime(df.index)
```

#### 2. Yahoo Finance边界处理修复

```python
# 修复Yahoo Finance API的排他性end参数
if isinstance(end_datetime, str):
    end_dt = datetime.strptime(end_datetime, "%Y-%m-%d")
else:
    end_dt = end_datetime

# 加1天确保包含结束日期
adjusted_end = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
```

#### 3. 路径一致性修复

```python
# 统一使用QLIB_DATA_PATH而不是QLIB_DATA_DIR
qlib_data_path = Path(settings.QLIB_DATA_PATH)
```

#### 4. 元数据记录机制

```python
# 保存准确的元数据信息
metadata = {
    "source": "yahoo",
    "stock_pool": stock_pool,
    "market": market_type,
    "region": region,
    "interval": interval,
    "download_date": datetime.now().isoformat(),
    "instruments_count": total_collected,
    "date_ranges": [(start, end) for start, end in download_ranges]
}
```

### 📈 性能指标

- **下载速度**：4.0-4.3 instruments/sec
- **并发处理**：最多8个并发请求
- **成功率**：98.6% (496/503 instruments)
- **数据质量**：完整的OHLCV字段，无缺失值
- **存储效率**：0.03MB/天/500只股票

### 🔄 API端点

#### 数据下载API

```
POST /api/v1/data-source/download
{
  "source": "yahoo",
  "stock_pool": "sp500",
  "start_date": "2024-01-01",
  "end_date": "2024-01-15",
  "incremental": false,
  "interval": "1d"
}
```

#### 状态查询API

```
GET /api/v1/data-source/status
{
  "source_name": "yahoo",
  "data_exists": true,
  "data_range_start": "2024-01-16",
  "data_range_end": "2024-01-16",
  "instruments_count": 497,
  "stock_pool": "sp500",
  "features": ["close.day", "high.day", "low.day", "open.day", "volume.day"],
  "data_size_mb": 0.03
}
```

### 🎯 下一阶段计划

#### 即将进行的测试

1. **分钟级数据测试** - 验证1m间隔数据下载
2. **Clear API测试** - 验证数据清理功能
3. **多市场切换测试** - 验证CN/US市场数据隔离

#### 未来扩展

1. **更多数据源** - Tushare, AKShare集成
2. **更多时间间隔** - 5m, 15m, 1h数据支持
3. **实时数据** - WebSocket实时数据流
4. **数据质量监控** - 自动数据质量检查和报告

---

## 🎉 UniversalNormalize模块完整实现 (2026-02-16)

### 📋 实现概述

成功完成了基于Qlib BaseNormalize架构的UniversalNormalize类实现，提供了统一的OHLCV数据标准化处理能力。

### 🏗️ 架构设计

#### 核心组件

1. **BaseNormalize抽象基类**

   - 基于Qlib源码设计的标准接口
   - 定义`normalize()`和`_get_calendar_list()`抽象方法
   - 完全兼容Qlib的Normalize工作流

2. **UniversalNormalize实现类**
   - 继承BaseNormalize，实现所有抽象方法
   - 支持多数据源：yahoo, tushare等
   - 支持多市场：US, CN等
   - 支持多频率：日级、分钟级数据

#### 关键特性

- ✅ **市场自动检测**：根据股票代码自动识别CN/US市场
- ✅ **交易时间支持**：CN市场(09:30-11:30+13:00-15:00)，US市场(09:30-16:00)
- ✅ **异常数据修正**：自动检测和修正股票分割等异常价格
- ✅ **日历对齐**：集成Qlib交易日历系统
- ✅ **变化率计算**：自动计算价格变化率并添加change列
- ✅ **完整错误处理**：详细的日志记录和异常处理

### 📁 文件结构

```
backend/app/services/data_collectors/
├── normalize.py                 # 完整的normalize模块
│   ├── BaseNormalize           # 抽象基类
│   └── UniversalNormalize      # 统一实现类
└── temp_scripts/normalize_tests/
    ├── test_normalize_basic.py     # 基础功能测试
    └── test_normalize_complete.py  # 完整功能测试
```

### 🔧 核心方法实现

#### 1. 市场检测方法

```python
def detect_market_from_symbol(self, symbol: str) -> str:
    # CN: .SZ, .SH, .SS后缀或6位数字
    # US: 其他格式（默认）
```

#### 2. 日历生成方法

```python
def _get_calendar_list(self) -> Iterable[pd.Timestamp]:
    # 集成Qlib的D.calendar(freq="day")
    # 支持分钟级日历生成

def generate_1min_from_daily(self, daily_calendar, market="US"):
    # 从日级日历生成分钟级日历
    # 支持不同市场的交易时间
```

#### 3. 核心标准化方法

```python
@staticmethod
def normalize_universal(df, calendar_list=None, ...):
    # 时间索引处理和去重
    # 日历对齐（可选）
    # 异常价格检测和修正
    # 价格变化率计算
    # 数据清洗和验证
```

#### 4. 主接口方法

```python
def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
    # BaseNormalize抽象方法实现
    # 自动市场检测
    # 调用normalize_universal核心逻辑
```

### 🧪 测试验证

#### 测试环境

- **Docker容器**：quantbot-backend-1
- **测试脚本**：temp_scripts/normalize_tests/
- **测试数据**：模拟OHLCV数据（美股AAPL，A股000001.SZ）

#### 测试结果

```
🧪 Starting UniversalNormalize Complete Tests
============================================================

📦 Test 1: Import Test
✅ Successfully imported UniversalNormalize

🏗️ Test 2: Create Normalizer Instance
✅ Successfully created UniversalNormalize instance

🌍 Test 3: Market Detection
✅ AAPL detected as: US
✅ 000001.SZ detected as: CN

🔄 Test 4: Complete Normalize Functionality
📊 Input data shape: (10, 7)
📊 Output data shape: (10, 8)
✅ Change column successfully added
✅ Date column has correct datetime type

🎉 All complete tests passed!
```

#### 验证要点

- ✅ 模块导入成功
- ✅ 实例创建正常
- ✅ 市场检测准确（US/CN）
- ✅ 数据处理完整（10行7列→10行8列）
- ✅ change列正确添加和计算
- ✅ 数据类型正确（datetime索引）

### 🔧 技术细节

#### 导入依赖修复

在开发过程中解决了两个关键导入问题：

1. **List类型未定义**：添加`from typing import List, Iterable, Optional`
2. **copy模块未导入**：添加`import copy`

#### 日历对齐逻辑优化

修复了空日历导致数据清空的问题：

```python
# 修复前
if calendar_list is not None:

# 修复后
if calendar_list is not None and len(calendar_list) > 0:
```

### 🎯 集成就绪

UniversalNormalize模块现已完全就绪，可以：

1. **集成到数据收集器**：YahooCollector等可直接使用
2. **兼容Qlib工作流**：符合Qlib Normalize标准接口
3. **支持多数据源**：统一处理不同来源的OHLCV数据
4. **扩展新市场**：易于添加新的市场和交易时间支持

### 📈 下一步计划

1. ✅ **UniversalNormalize模块已完成**
2. 🔄 **实施数据获取Pipeline**（当前任务）
3. 扩展支持更多数据源（Tushare, AKShare等）
4. 优化性能和错误处理机制

---

## 🚀 数据获取Pipeline完整方案 (2026-02-16)

### 📋 方案概述

基于Qlib官方Yahoo数据pipeline架构，设计统一的数据获取pipeline，将data collector、normalize、dump_bin三个阶段串联起来，提供完整的数据处理流程。

### 🏗️ 架构设计

#### 整体流程

```
用户请求 → DataPipelineService → [Collector → Normalize → DumpBin] → Qlib数据格式
```

#### 核心组件

**1. DataPipelineService（统一入口）**

```python
class DataPipelineService:
    """
    Unified data acquisition pipeline service

    Features:
    - Single entry point for all data collection requests
    - Orchestrates complete pipeline: collect → normalize → dump
    - Progress tracking and error handling
    - Integration with FastAPI endpoints
    """

    def execute_pipeline(self,
                        source: str,           # "yahoo", "tushare", etc.
                        symbols: List[str],    # ["AAPL", "000001.SZ"]
                        start_date: str,       # "2023-01-01"
                        end_date: str,         # "2023-12-31"
                        interval: str = "1d",  # "1d" or "1min"
                        **kwargs) -> PipelineResult
```

**2. 三阶段Pipeline处理**

**阶段1：数据收集（Data Collection）**

- 使用现有的YahooCollector
- 输出：原始CSV文件到临时目录
- 支持并发收集和重试机制

**阶段2：数据标准化（Data Normalization）**

- 使用刚实现的UniversalNormalize
- 集成Qlib的Normalize工作流类
- 输出：标准化的CSV文件

**阶段3：数据转储（Data Dumping）**

- 使用Qlib的DumpDataUpdate
- 输出：Qlib .bin格式数据
- 自动生成instruments和calendars

#### 目录结构设计

```
/app/data/pipeline_workspace/
├── temp_csv/              # 阶段1：原始CSV数据
│   ├── AAPL.csv
│   └── 000001.SZ.csv
├── normalized/            # 阶段2：标准化数据
│   ├── AAPL.csv
│   └── 000001.SZ.csv
└── qlib_data/            # 阶段3：Qlib格式数据
    ├── calendars/
    ├── features/
    └── instruments/
```

### 🔧 技术实现

#### API设计

**新增Pipeline端点**

```python
@router.post("/data/pipeline/execute")
async def execute_data_pipeline(request: DataPipelineRequest) -> DataPipelineResponse:
    """Execute complete data acquisition pipeline"""

@router.get("/data/pipeline/status/{task_id}")
async def get_pipeline_status(task_id: str) -> PipelineStatusResponse:
    """Get pipeline execution status"""
```

**保持现有端点兼容**

- 现有的collect/normalize端点继续工作
- 内部重构为使用pipeline组件

#### 配置示例

```python
pipeline_config = {
    "source": "yahoo",
    "symbols": ["AAPL", "MSFT", "000001.SZ"],
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "interval": "1d",
    "workspace_dir": "/app/data/pipeline_workspace",
    "qlib_data_dir": "/app/data/qlib_data",
    "cleanup_temp": True,
    "max_workers": 4
}
```

### 🎯 实施计划

#### 阶段1：基础框架 (1-2天)

1. **创建DataPipelineService基础框架**

   - 定义Pipeline接口和数据结构
   - 实现基础的任务管理和状态跟踪
   - 创建工作目录管理

2. **集成现有YahooCollector**
   - 适配YahooCollector到pipeline框架
   - 实现进度回调和错误处理
   - 测试数据收集阶段

#### 阶段2：标准化集成 (1天)

3. **集成UniversalNormalize**
   - 创建Normalize工作流适配器
   - 集成我们的UniversalNormalize类
   - 测试标准化阶段

#### 阶段3：数据转储 (1天)

4. **集成Qlib的DumpDataUpdate**
   - 研究和适配DumpDataUpdate类
   - 实现.bin格式数据生成
   - 测试完整pipeline流程

#### 阶段4：API和界面 (1-2天)

5. **添加API端点**

   - 实现pipeline执行端点
   - 添加状态查询和进度跟踪
   - 更新Swagger文档

6. **前端界面集成**
   - 更新数据收集界面
   - 添加pipeline进度显示
   - 集成错误处理和重试

### 💡 方案优势

1. **完全兼容Qlib**：直接使用Qlib的标准组件
2. **复用现有代码**：
   - ✅ YahooCollector（已有）
   - ✅ UniversalNormalize（刚完成）
   - ✅ DumpDataUpdate（Qlib提供）
3. **统一错误处理**：整个pipeline的异常处理和重试
4. **进度跟踪**：用户可见的处理进展
5. **资源管理**：自动清理临时文件
6. **扩展性强**：易于添加新数据源和市场

### 🔄 扩展性设计

- **多数据源支持**：通过CollectorRegistry添加Tushare、AKShare
- **多市场支持**：UniversalNormalize已支持CN/US市场
- **多频率支持**：支持日级和分钟级数据
- **增量更新**：支持增量数据更新

### 📋 文件结构

```
backend/app/services/
├── data_collectors/
│   ├── normalize.py           # ✅ UniversalNormalize (已完成)
│   ├── yahoo_collector.py     # ✅ YahooCollector (已有)
│   └── pipeline/              # 🔄 新增Pipeline模块
│       ├── __init__.py
│       ├── service.py         # DataPipelineService
│       ├── models.py          # Pipeline数据模型
│       ├── stages.py          # Pipeline阶段实现
│       └── utils.py           # Pipeline工具函数
└── api/v1/
    └── data_pipeline.py       # 🔄 新增Pipeline API端点
```

---

## 📊 YahooQuery字段探索结果 (2026-02-16)

### 🎯 探索目标

通过创建专门的测试脚本 `temp_scripts/data_exploration/test_yahooquery_fields.py`，深入分析yahooquery库返回的数据字段结构，为BaseCollector metadata配置提供准确的技术依据。

### 🔬 测试方法

#### 测试环境设置

- **测试脚本位置**: `temp_scripts/data_exploration/test_yahooquery_fields.py`
- **Docker volume映射**: `./temp_scripts:/app/temp_scripts:cached`
- **测试执行环境**: quantbot-backend-1 Docker容器
- **yahooquery版本**: 2.3.0+

#### 测试样本选择

- **美股样本**: AAPL (Apple Inc.)
- **A股样本**: 000001.SZ (平安银行)
- **测试参数**: period="1mo", interval="1d"

### 📋 关键发现

#### 1. 字段结构分析

**美股 (AAPL) 返回字段**:

```python
['open', 'high', 'low', 'close', 'volume', 'adjclose', 'dividends']
```

**A股 (000001.SZ) 返回字段**:

```python
['open', 'high', 'low', 'close', 'volume', 'adjclose']
```

**市场差异**:

- ✅ 核心OHLCV字段在所有市场一致
- ✅ adjclose字段在所有市场可用
- ⚠️ dividends字段仅在美股市场可用

#### 2. 数据类型分析

```python
# 所有市场统一的数据类型
{
    "open": "float64",      # 开盘价
    "high": "float64",      # 最高价
    "low": "float64",       # 最低价
    "close": "float64",     # 收盘价
    "volume": "int64",      # 成交量
    "adjclose": "float64",  # 调整收盘价
    "dividends": "float64"  # 分红 (仅美股)
}
```

#### 3. close vs adjclose 价格调整分析

**美股 AAPL 数据**:

- close: 259.96
- adjclose: 259.72
- 差异: 0.24 (约0.09%)
- **结论**: 存在除权除息调整，但差异很小

**A股 000001.SZ 数据**:

- close: 11.47
- adjclose: 11.47
- 差异: 0.0 (完全相同)
- **结论**: 无除权除息调整或Yahoo对A股处理不同

#### 4. auto_adjust参数验证

**重要发现**: yahooquery的`history()`方法**不支持**`auto_adjust`参数

- 测试显示: `Ticker.history() got an unexpected keyword argument 'auto_adjust'`
- **结论**: yahooquery默认行为已经包含必要的价格调整

### 🎯 BaseCollector配置决策

基于测试结果，确定采用**简化的OHLCV配置方案**：

#### 核心字段配置

```python
YAHOOQUERY_FIELD_METADATA = {
    "open": {
        "type": "float64",
        "required": True,
        "description": "Opening price"
    },
    "high": {
        "type": "float64",
        "required": True,
        "description": "Highest price"
    },
    "low": {
        "type": "float64",
        "required": True,
        "description": "Lowest price"
    },
    "close": {
        "type": "float64",
        "required": True,
        "description": "Closing price (effectively adjusted)"
    },
    "volume": {
        "type": "int64",
        "required": True,
        "description": "Trading volume"
    }
}
```

#### 设计原则

1. **使用close作为前复权价格**: 基于测试发现close和adjclose差异极小
2. **忽略adjclose和dividends**: 简化配置，专注核心OHLCV字段
3. **跨市场一致性**: 美股和A股使用相同的字段配置
4. **符合Qlib标准**: 标准OHLCV格式符合Qlib BaseCollector期望

### 💡 技术洞察

#### 1. yahooquery默认行为

- yahooquery的close字段已经包含了必要的价格调整
- 不需要额外的参数来获取前复权价格
- 默认返回的数据适合直接用于量化分析

#### 2. 市场差异处理

- 核心OHLCV字段在所有市场保持一致
- 可选字段(如dividends)的缺失不影响核心功能
- 统一的字段配置可以处理多个市场

#### 3. 数据质量验证

- 价格字段使用float64确保精度
- 成交量字段使用int64适合大数值
- 数据类型在不同市场保持一致

### 🚀 实施影响

#### 对YahooDataCollector的影响

1. **简化字段提取**: 只需提取OHLCV五个核心字段
2. **统一处理逻辑**: 不需要区分市场的特殊处理
3. **减少配置复杂性**: 避免adjclose和dividends的额外处理

#### 对Yahoo Normalize的影响

1. **标准化输入**: 接收标准OHLCV格式数据
2. **简化验证逻辑**: 只需验证五个核心字段
3. **提高处理效率**: 减少不必要的字段转换

#### 对整体架构的影响

1. **配置驱动**: 通过metadata配置驱动字段处理
2. **扩展性**: 其他数据源可以参考相同的字段配置模式
3. **维护性**: 简化的配置更容易维护和调试

### 📝 后续任务

基于字段探索结果，下一步需要：

1. ✅ **完成BaseCollector metadata配置**
2. 🔄 **实现Yahoo Normalize模块**
3. 🔄 **更新YahooDataCollector使用新的字段配置**
4. 🔄 **集成测试验证数据收集流程**

---

## 🔍 Qlib BaseCollector深度架构分析 (2026-02-14)

### 📋 关键发现

通过深入研究Qlib源码 `qlib-source/scripts/data_collector/base.py` 和 `yahoo/collector.py`，发现我们当前的数据源实现**完全偏离了Qlib标准架构**。

### 🏗️ Qlib BaseCollector标准架构

#### **核心设计模式**：

1. **抽象基类模式**：`BaseCollector`定义标准接口
2. **模板方法模式**：`collector_data()`定义完整收集流程
3. **并发处理**：使用`joblib.Parallel`进行高效并发收集
4. **错误重试机制**：`max_collector_count`参数控制重试次数
5. **数据验证**：`check_data_length`验证数据完整性
6. **缓存机制**：`mini_symbol_map`缓存小数据集

#### **必须实现的抽象方法**：

```python
@abc.abstractmethod
def get_instrument_list(self) -> List[str]:
    """获取股票代码列表"""

@abc.abstractmethod
def normalize_symbol(self, symbol: str) -> str:
    """标准化股票代码格式"""

@abc.abstractmethod
def get_data(self, symbol: str, interval: str,
            start_datetime: pd.Timestamp,
            end_datetime: pd.Timestamp) -> pd.DataFrame:
    """获取单个股票的数据"""
```

#### **标准化数据流程**：

1. **数据收集**：`BaseCollector.collector_data()`
2. **数据标准化**：`BaseNormalize.normalize()`
3. **数据转换**：`dump_bin.py` 转换为Qlib二进制格式

### 🚨 当前实现的问题

我们的 `backend/app/services/data_utils.py` 实现存在严重问题：

1. **完全绕过Qlib架构**：直接调用外部脚本，未使用BaseCollector
2. **缺少标准化流程**：没有数据验证、重试、并发控制机制
3. **不符合扩展约定**：无法利用Qlib的生态系统和最佳实践
4. **维护困难**：每个数据源需要独立的脚本和API端点

### 🎯 正确的重新设计方案

基于Qlib BaseCollector标准，重新设计数据源架构：

#### **新架构核心原则**：

1. **完全基于Qlib BaseCollector**：继承并实现标准接口
2. **利用Qlib内置机制**：并发、重试、验证、缓存
3. **保持API兼容性**：现有前端和API接口不变
4. **插件化扩展**：新数据源只需实现标准接口

#### **实现策略**：

```python
# 基于Qlib BaseCollector的标准实现
class YahooDataCollector(BaseCollector):
    """Yahoo Finance data collector following Qlib standards"""

    def get_instrument_list(self) -> List[str]:
        # 实现股票列表获取逻辑

    def normalize_symbol(self, symbol: str) -> str:
        # 实现符号标准化逻辑

    def get_data(self, symbol: str, interval: str,
                start_datetime: pd.Timestamp,
                end_datetime: pd.Timestamp) -> pd.DataFrame:
        # 实现数据获取逻辑，使用yahooquery
```

#### **服务层重构**：

```python
class DataCollectorService:
    """统一的数据收集服务层"""

    def collect_data(self, source: str, **params) -> CollectionResult:
        # 使用对应的BaseCollector实现
        collector = self._get_collector(source, **params)
        collector.collector_data()  # 使用Qlib标准流程

    def _get_collector(self, source: str, **params) -> BaseCollector:
        # 工厂模式获取收集器实例
```

### 📊 架构对比

| 方面     | 当前实现       | Qlib标准实现        |
| -------- | -------------- | ------------------- |
| 基础架构 | 独立脚本调用   | BaseCollector继承   |
| 并发处理 | 无             | joblib.Parallel     |
| 错误重试 | 无             | max_collector_count |
| 数据验证 | 无             | check_data_length   |
| 扩展性   | 每个源需新脚本 | 实现标准接口即可    |
| 维护性   | 高耦合         | 标准化、低耦合      |

### 🚀 实施计划更新

#### **阶段1：基础架构重构 (2-3天)**

1. ✅ **深入研究Qlib源码**：完成BaseCollector架构分析
2. **创建BaseDataCollector**：继承Qlib BaseCollector
3. **实现YahooDataCollector**：基于Qlib标准的Yahoo收集器
4. **重构DataCollectorService**：使用新的收集器架构

#### **阶段2：集成和测试 (1-2天)**

1. **重构data_utils.py**：内部使用新架构，保持API兼容
2. **API测试**：确保现有端点正常工作
3. **性能对比**：验证新架构的性能优势

#### **阶段3：扩展和优化 (未来)**

1. **Tushare收集器**：基于相同架构
2. **AKShare收集器**：基于相同架构
3. **本地CSV收集器**：基于相同架构

### 💡 关键技术洞察

1. **Qlib生态系统**：完全基于BaseCollector构建，我们必须遵循
2. **标准化流程**：collect → normalize → dump_bin → qlib_data
3. **并发优化**：Qlib内置了最佳的并发处理机制
4. **错误处理**：成熟的重试和错误恢复机制
5. **数据质量**：内置的数据长度检查和验证机制

## 🔄 数据收集器架构重新设计 (2026-02-14 21:46)

### 📋 架构问题识别

经过深入分析，发现初始设计存在两个关键问题：

#### **问题1：绕过Qlib二进制格式机制**

- **问题**：直接返回DataFrame，未利用Qlib的核心性能优化
- **影响**：失去压缩、缓存、加速等关键优势
- **Qlib标准流程**：`BaseCollector.collector_data()` → `BaseNormalize.normalize()` → `dump_bin.py` → 二进制存储

#### **问题2：缺少字段元数据支持**

- **问题**：无法为前端提供数据源支持的字段信息
- **影响**：前端无法动态显示可用字段，用户体验下降
- **需求**：前端需要知道每个数据源支持哪些字段（OHLCV、技术指标等）

### 🎯 重新设计的核心原则

#### **1. 完全遵循Qlib标准流程**

```python
# 正确的Qlib数据流程
BaseCollector.collector_data()  # 主要收集入口
├── get_instrument_list()       # 获取股票列表
├── normalize_symbol()          # 标准化股票代码
├── get_data()                 # 获取单个股票数据
└── 自动转换为二进制格式        # Qlib内部处理
```

#### **2. 集成字段元数据系统**

```python
# 新增的元数据支持方法
get_supported_fields()         # 返回支持的字段列表
get_field_metadata()          # 返回字段详细信息
get_data_schema()             # 返回完整数据模式
```

#### **3. 保持API兼容性**

- 现有前端和API接口保持不变
- 内部使用新的Qlib标准架构
- 通过服务层进行适配

### 🏗️ 新架构设计

#### **BaseDataCollector核心功能**

1. **Qlib集成**：

   - 继承`qlib.data.data.BaseCollector`
   - 实现必需的抽象方法
   - 利用Qlib内置的并发、重试、验证机制

2. **字段元数据管理**：

   - `get_supported_fields()`: 返回字段列表和类型信息
   - `get_field_descriptions()`: 返回字段描述和单位
   - `get_data_schema()`: 返回完整的数据模式定义

3. **性能优化**：

   - 使用Qlib二进制格式存储
   - 利用Qlib缓存机制
   - 支持并发数据收集

4. **前端集成**：
   - 提供字段元数据API
   - 支持动态字段选择
   - 保持现有UI功能

#### **数据流程优化**

```
前端请求 → API层 → 服务层 → BaseDataCollector
                              ↓
                         Qlib标准流程
                              ↓
                        二进制格式存储 ← Qlib缓存系统
                              ↓
                         快速数据访问
```

### 📊 架构对比更新

| 方面       | 初始设计          | 重新设计       |
| ---------- | ----------------- | -------------- |
| Qlib集成   | 部分遵循          | 完全遵循标准   |
| 数据存储   | DataFrame直接返回 | Qlib二进制格式 |
| 性能优化   | 无缓存机制        | Qlib缓存+压缩  |
| 字段元数据 | 不支持            | 完整支持       |
| 前端集成   | 基础功能          | 动态字段显示   |
| 扩展性     | 中等              | 高度可扩展     |

### 🚀 实施计划更新

#### **阶段1：核心架构重构 (当前)**

1. ✅ **创建基础文件结构**：`__init__.py`, `exceptions.py`
2. 🔄 **重新设计BaseDataCollector**：集成Qlib标准和字段元数据
3. **创建字段元数据系统**：支持前端动态显示
4. **实现YahooDataCollector**：基于新架构的具体实现

#### **阶段2：服务层适配 (1-2天)**

1. **重构DataCollectorService**：适配新的BaseCollector架构
2. **保持API兼容性**：确保现有端点正常工作
3. **添加字段元数据API**：为前端提供字段信息

#### **阶段3：前端集成优化 (1-2天)**

1. **集成字段元数据显示**：动态显示可用字段
2. **优化用户体验**：基于字段类型提供不同的UI组件
3. **性能测试**：验证Qlib二进制格式的性能优势

### 💡 关键洞察

1. **Qlib二进制格式的重要性**：

   - 数据压缩率可达90%以上
   - 访问速度提升10-100倍
   - 内置缓存机制避免重复计算

2. **字段元数据的价值**：

   - 提升用户体验和系统可用性
   - 支持动态UI生成
   - 便于数据源扩展和维护

3. **架构设计的平衡**：
   - 完全遵循Qlib标准确保性能
   - 保持API兼容性确保稳定性
   - 增强元数据支持提升体验

## 🔍 Qlib二进制转换机制澄清 (2026-02-14 21:55)

### 📋 关键问题澄清

经过深入分析，澄清了Qlib二进制转换的真实机制：

#### **问题**：`get_data()` 返回DataFrame是否正确？

**答案**：✅ **完全正确！这是Qlib的标准接口**

#### **Qlib标准数据处理流程**：

```python
# 正确的Qlib数据处理链
1. BaseCollector.collector_data()     # 主入口，调用下面的方法
   ├── get_instrument_list()          # 获取股票列表
   ├── get_data() → DataFrame         # 返回DataFrame（标准接口）
   └── 内部处理：
       ├── BaseNormalize.normalize()  # 数据标准化
       └── dump_bin.py               # 转换为二进制格式

2. 数据使用时：
   DataLoader.load() → 从二进制文件读取 → 高速访问
```

### 🎯 架构职责分工

#### **BaseCollector的职责**（我们负责）

- `get_instrument_list()`: 返回股票列表
- `normalize_symbol()`: 标准化股票代码
- `get_data()`: **返回DataFrame**（这是标准接口）
- `collector_data()`: 主收集流程（继承自Qlib）

#### **Qlib系统的职责**（自动处理）

- 数据标准化：`BaseNormalize.normalize()`
- 二进制转换：`dump_bin.py`
- 缓存管理：自动缓存机制
- 高速访问：`DataLoader`从二进制文件读取

### 📊 完整使用流程示例

```python
# 1. 数据收集阶段（我们的BaseDataCollector）
collector = YahooDataCollector()
collector.collector_data()  # 调用get_data()，返回DataFrame

# 2. 数据处理阶段（Qlib自动处理）
# 通过Qlib命令行工具或脚本完成：
# python scripts/dump_bin.py --source yahoo --target qlib_data/

# 3. 数据使用阶段（享受性能优化）
import qlib
qlib.init(provider_uri="qlib_data")  # 使用二进制数据
data = D.features(["AAPL"], ["$close", "$volume"])  # 高速访问
```

### 💡 关键洞察

1. **DataFrame接口是正确的**：

   - `get_data()` 返回DataFrame是Qlib标准
   - 二进制转换由Qlib其他组件处理
   - 我们不需要手动实现二进制转换

2. **性能优化的实现位置**：

   - **数据收集**：我们返回DataFrame（标准接口）
   - **数据存储**：Qlib自动转换为二进制格式
   - **数据使用**：Qlib从二进制文件高速读取

3. **架构设计验证**：
   - 我们的BaseDataCollector设计是正确的
   - 字段元数据系统设计是有价值的
   - 完全符合Qlib的标准架构

## 📚 DataSource模块完整理解总结 (2026-02-14 22:21)

### 🎯 核心架构理解

#### **Qlib数据处理的三阶段流程**

```
阶段1: 数据收集 (BaseCollector)
├── get_instrument_list() → 获取股票列表
├── normalize_symbol() → 标准化股票代码
├── get_data() → 返回DataFrame (这是正确的标准接口)
└── collector_data() → 主入口，保存DataFrame为CSV

阶段2: 数据标准化 (BaseNormalize)
├── 需要为每个数据源单独开发
├── 处理数据格式差异和股票代码转换
└── 输出标准化的CSV文件

阶段3: 二进制转换 (dump_bin)
├── 通用函数，可以复用
├── 将标准化CSV转换为Qlib二进制格式
└── 实现90%+压缩率和10-100x性能提升
```

#### **关键设计原则确认**

1. **✅ DataFrame接口正确**：`get_data()`返回DataFrame是Qlib标准，不需要手动转换二进制
2. **✅ 三阶段分离**：`collector_data()`只负责第一阶段，后续需要手动触发
3. **✅ 组件复用性**：每个数据源需要Collector+Normalize，dump_bin通用复用
4. **✅ 字段元数据**：支持前端动态显示，提升用户体验

### 🏗️ 架构组件职责分工

#### **BaseDataCollector (我们负责开发)**

- **职责**：数据收集和基础验证
- **输出**：DataFrame格式的OHLCV数据
- **复用性**：每个数据源需要单独实现
- **关键方法**：
  - `get_instrument_list()`: 返回股票列表
  - `normalize_symbol()`: 标准化股票代码
  - `get_data()`: 获取DataFrame数据
  - `get_supported_fields()`: 字段元数据支持

#### **BaseNormalize (需要为每个数据源开发)**

- **职责**：数据格式标准化
- **输入**：原始CSV文件
- **输出**：标准化的CSV文件
- **复用性**：每个数据源需要单独实现
- **原因**：不同数据源的格式、字段名、日期格式、股票代码都不同

#### **dump_bin (Qlib提供，完全复用)**

- **职责**：二进制格式转换
- **输入**：标准化的CSV文件
- **输出**：Qlib二进制格式
- **复用性**：通用函数，所有数据源共享
- **性能**：90%+压缩，10-100x访问速度提升

### 📊 数据源扩展模式

#### **标准扩展模式**

```python
# 每个新数据源需要的组件
DataSource = {
    "Collector": "XxxDataCollector",    # 继承BaseDataCollector (必须开发)
    "Normalize": "XxxNormalize",        # 继承BaseNormalize (必须开发)
    "DumpBin": "dump_bin"               # Qlib通用函数 (直接复用)
}
```

#### **开发工作量评估**

| 组件          | 开发需求      | 复用性      | 难度  | 时间估算 |
| ------------- | ------------- | ----------- | ----- | -------- |
| BaseCollector | ✅ 每个数据源 | ❌ 不可复用 | 🔴 高 | 2-3天    |
| BaseNormalize | ✅ 每个数据源 | ❌ 不可复用 | 🟡 中 | 1-2天    |
| dump_bin      | ❌ 不需要     | ✅ 完全复用 | 🟢 无 | 0天      |

### 🔄 完整数据流程示例

#### **方式1：分步执行（推荐用于开发调试）**

```python
# 步骤1：数据收集
collector = YahooDataCollector(save_dir="./raw_data")
collector.collector_data()  # DataFrame → CSV

# 步骤2：数据标准化（手动调用）
normalizer = YahooNormalize(
    source_dir="./raw_data",
    target_dir="./normalized_data"
)
normalizer.normalize()  # CSV → 标准化CSV

# 步骤3：二进制转换（手动调用）
dump_bin(
    csv_path="./normalized_data",
    qlib_dir="./qlib_data/bin"
)  # 标准化CSV → 二进制
```

#### **方式2：一体化流程（推荐用于生产）**

```python
def complete_data_pipeline(data_source: str):
    """完整的数据处理管道"""
    # 动态选择数据源
    collector_class = get_collector_class(data_source)
    normalize_class = get_normalize_class(data_source)

    # 执行三阶段流程
    collector = collector_class(save_dir=f"./raw_{data_source}")
    collector.collector_data()

    normalizer = normalize_class(
        source_dir=f"./raw_{data_source}",
        target_dir=f"./normalized_{data_source}"
    )
    normalizer.normalize()

    dump_bin(
        csv_path=f"./normalized_{data_source}",
        qlib_dir="./qlib_data/bin"
    )
```

### 💡 关键技术洞察

1. **性能优化的实现位置**：
   - **数据收集**：BaseCollector返回DataFrame（标准接口）
   - **数据存储**：Qlib自动转换为二进制格式
   - **数据使用**：Qlib从二进制文件高速读取

## 🎯 YahooDataCollector完整实现 (2026-02-15 17:24)

### 📋 实现完成状态

#### **核心功能实现** ✅

1. **多市场支持**：

   - CN市场：CSI300（沪深300）、CSI500（中证500）
   - US市场：SP500（标普500）、NASDAQ100（纳斯达克100）
   - 市场参数验证和时区自动配置

2. **三个必需抽象方法完整实现**：

   **`get_instrument_list()`**：

   - 基于yfiua.github.io API动态获取指数成分股
   - API端点：`/constituents-csi300.json`, `/constituents-csi500.json`, `/constituents-sp500.json`, `/constituents-nasdaq100.json`
   - 自动解析JSON格式：`[{"Symbol": "NVDA", "Name": "Nvidia"}, ...]`
   - 完整的错误处理：网络错误、JSON解析错误、字段缺失错误

   **`normalize_symbol()`**：

   - CN市场：`"000001.SZ"` → `"SZ000001"`，`"600519.SS"` → `"SH600519"`
   - US市场：`"AAPL"` → `"AAPL"`（保持不变）
   - 支持异常情况的容错处理

   **`get_data()`**：

   - 使用yahooquery库获取OHLCV历史数据
   - 支持1d和1min时间间隔
   - **统一字段管理**：使用`BaseCollector._field_metadata`获取字段列表
   - 返回标准DataFrame格式，索引为'date'，列名为小写

3. **统一字段配置系统**：

   - 继承`BaseCollector._field_metadata`字段定义
   - 所有数据收集器使用统一的字段配置
   - 支持动态字段扩展和前端字段显示

4. **完整的日志和错误处理**：
   - 使用logger替代print输出
   - 分类异常处理：DataSourceError、DataValidationError、DataCollectionError
   - 详细的调试信息和错误追踪

### 🏗️ 架构设计亮点

#### **字段元数据统一管理**

```python
# BaseCollector中的字段定义
self._field_metadata = {
    "open": "Opening price",
    "high": "Highest price",
    "low": "Lowest price",
    "close": "Closing price",
    "volume": "Trading volume",
}

# YahooDataCollector中使用统一字段
required_columns = list(self._field_metadata.keys())
```

**优势**：

- 🎯 **统一性**：所有数据收集器使用相同字段定义
- 🔧 **可扩展性**：在BaseCollector中修改字段，所有子类自动继承
- 📊 **一致性**：确保前端显示和后端数据处理使用相同字段
- 🛡️ **维护性**：字段配置集中管理，减少重复代码

#### **多市场配置架构**

```python
MARKET_CONFIG = {
    "CN": {
        "timezone": "Asia/Shanghai",
        "supported_indices": ["CSI300", "CSI500"],
        "exchange_mapping": {
            "60": ".SS",  # 上海主板
            "68": ".SS",  # 科创板
            "00": ".SZ",  # 深圳主板
            "30": ".SZ",  # 创业板
        }
    },
    "US": {
        "timezone": "America/New_York",
        "supported_indices": ["SP500", "NASDAQ100"],
        "exchange_mapping": {}
    }
}
```

#### **API配置和错误处理**

```python
INDEX_API_CONFIG = {
    "base_url": "https://yfiua.github.io/index-constituents",
    "endpoints": {
        "CSI300": "/constituents-csi300.json",
        "CSI500": "/constituents-csi500.json",
        "SP500": "/constituents-sp500.json",
        "NASDAQ100": "/constituents-nasdaq100.json"
    }
}
```

### 📊 技术规格总结

| 功能模块   | 实现状态 | 技术特点                    |
| ---------- | -------- | --------------------------- |
| 市场支持   | ✅ 完成  | CN/US双市场，4个主要指数    |
| 成分股获取 | ✅ 完成  | 基于JSON API，实时动态获取  |
| 数据获取   | ✅ 完成  | yahooquery，支持1d/1min间隔 |
| 字段管理   | ✅ 完成  | 统一元数据系统，可扩展      |
| 错误处理   | ✅ 完成  | 分类异常，详细日志          |
| 代码标准化 | ✅ 完成  | CN/US不同格式转换           |

### 🚀 下一步计划

1. **功能测试**：验证多市场数据获取功能
2. **YahooNormalize类**：实现CSV数据标准化
3. **数据获取pipeline**：集成三个阶段的完整流程
4. **API系统集成**：与现有FastAPI系统集成
5. **前端对接**：实现前端界面和数据显示

### 💡 关键技术洞察

1. **Qlib标准遵循**：

   - 完全遵循BaseCollector接口规范
   - 利用Qlib内置的并发、重试、验证机制
   - 返回DataFrame是正确的标准接口

2. **字段元数据价值**：

   - 提升用户体验和系统可用性
   - 支持动态UI生成
   - 便于数据源扩展和维护

3. **多市场架构设计**：

   - 配置驱动的市场支持
   - 统一的接口，不同的实现细节
   - 易于扩展到其他市场和指数

   - 数据收集：我们返回DataFrame（标准接口）
   - 数据存储：Qlib自动转换为二进制格式
   - 数据使用：Qlib从二进制文件高速读取

4. **字段元数据的价值**：

   - 前端动态显示可用字段
   - 支持不同数据源的字段差异
   - 提升用户体验和系统可用性

5. **架构设计的平衡**：
   - 完全遵循Qlib标准确保性能
   - 保持API兼容性确保稳定性
   - 增强元数据支持提升体验
   - 分阶段设计提供灵活性和错误恢复能力

### 🚀 下一步实施计划

1. **✅ 基础架构**：BaseDataCollector, exceptions, **init**.py
2. **🔄 当前任务**：重新实现base.py文件内容
3. **📋 后续计划**：
   - 实现YahooDataCollector
   - 实现YahooNormalize
   - 集成到现有API系统
   - 前端字段元数据显示
   - 扩展其他数据源（Tushare, AKShare等）

---

## 📅 变更日志

### 2026-02-03 凌晨 - Yahoo Finance 数据收集器完整实现 ✅

**🎯 核心成就**: 成功解决了 `adj_close.day` 字段缺失问题，建立了配置驱动的数据收集架构

**✅ 已完成的工作**:

1. **深度调试 Yahoo Finance 数据结构**

   - ✅ 创建测试脚本直接分析 Yahoo Finance API 返回数据
   - ✅ 发现关键问题：Yahoo Finance **不提供** `Adj Close` 字段
   - ✅ 确认重要发现：Yahoo Finance 默认的 `Close` **就是前复权价格**
   - ✅ 验证数据：`Default Close (7.992281) = Adj Close (7.992281) ≠ Raw Close (9.210000)`

2. **配置文件架构优化**

   - ✅ 更新 `backend/app/core/data_fields.yaml`：
     - 移除 `adj_close` 字段（Yahoo Finance 不提供）
     - 更新 `close` 字段描述为 "adjusted for splits and dividends"
     - 保持 `vwap` 计算字段
   - ✅ 实现配置驱动的字段映射机制
   - ✅ 消除硬编码，提高系统扩展性

3. **数据收集器代码优化**

   - ✅ 移除 `get_data_yahoo_realtime.py` 中的 `adj_close` 映射逻辑
   - ✅ 清理调试代码，保持代码整洁
   - ✅ 保持 VWAP 计算功能正常工作
   - ✅ 确保配置驱动的字段处理流程

4. **完整功能验证**
   - ✅ 数据收集 API 测试通过：297只CSI300股票成功收集
   - ✅ 数据状态 API 验证通过：
     ```json
     "features": [
       "close.day",    // ✅ 前复权价格 (Yahoo Finance默认)
       "high.day",     // ✅ 最高价
       "low.day",      // ✅ 最低价
       "open.day",     // ✅ 开盘价
       "volume.day",   // ✅ 成交量
       "vwap.day"      // ✅ 计算字段 (成功生成)
     ]
     ```
   - ✅ 数据大小：0.16MB，时间范围：2024-01-02 到 2024-01-30

**🎓 关键技术决策和知识点**:

1. **Yahoo Finance 数据特性理解**：

   - Yahoo Finance 的 `ticker.history()` 默认返回前复权价格
   - 只有设置 `auto_adjust=False` 才会提供原始价格和 `Adj Close` 字段
   - 这个发现解决了长期困扰的前复权价格获取问题

2. **配置驱动架构的价值**：

   - 通过 `data_fields.yaml` 统一管理所有数据源的字段定义
   - 支持字段映射、描述、验证的集中配置
   - 为未来扩展其他数据源（Tushare、AKShare）奠定基础

3. **调试方法论**：
   - 遇到数据问题时，直接分析数据源 API 的原始返回结果
   - 使用简单的测试脚本验证假设
   - 从根本原因入手，而不是在症状层面修补

**🏗️ 架构成果**:

建立了完整的**配置驱动数据收集架构**：

```
用户请求 → API路由 → data_utils.py → YahooDataCollector
    ↓
配置文件 (data_fields.yaml) → 字段定义和映射
    ↓
Yahoo Finance API → CSV数据 → dump_bin.py → Qlib格式
    ↓
数据状态API → 验证和监控
```

**优势**：

- ✅ **可扩展性强**：新增数据源只需添加配置文件
- ✅ **维护性好**：字段定义集中管理，修改影响范围可控
- ✅ **可靠性高**：配置驱动减少硬编码错误
- ✅ **标准化**：统一的数据处理流程

**🚀 下一步工作方向**:

1. **前端数据管理界面开发** (优先级：高)

   - 数据源选择界面
   - 数据收集参数配置
   - 数据状态监控面板

2. **其他数据源集成** (优先级：中)

   - Tushare 数据源（中国A股专业数据）
   - AKShare 数据源（开源金融数据）
   - 本地CSV文件导入

3. **因子工程模块开发** (优先级：中)
   - 基于完整数据的Alpha158因子计算
   - 自定义因子表达式编辑器

**📊 项目状态更新**:

- **Phase 1**: Qlib 核心工作流 ✅ 已完成
- **Phase 2.1**: 数据收集器实现 ✅ 已完成
- **Phase 2.2**: API 端点开发 ✅ 已完成
- **Phase 3**: 前端开发 🔄 准备开始

---

### 2026-01-27 上午 - Phase 1 训练工作流测试通过 ✅

**✅ 已完成的工作**:

1. **下载 Qlib 官方数据下载脚本**

   - ✅ 从 Qlib GitHub 仓库下载 `scripts/get_data.py`
   - ✅ 保存到 `backend/scripts/get_data.py`（可提交到版本控制）
   - ✅ 使用 curl 在 Docker 容器中下载成功

2. **下载 Qlib 中国市场数据**

   - ✅ 使用官方脚本下载数据：`python scripts/get_data.py qlib_data --target_dir /app/qlib_data --region cn`
   - ✅ 数据大小：188MB（压缩包）
   - ✅ 数据内容：3877 只股票的日线数据（OHLCV + 因子）
   - ✅ 数据结构：`calendars/`、`features/`、`instruments/`
   - ✅ 下载耗时：约 1 分钟

3. **修复 `qlib_workflow_service.py` 的 Bug**

   **Bug 1**: `_create_and_train_model` 方法传递错误参数

   - ❌ 问题：传递 DataFrame 给 `model.fit()`，但 LGBModel 期望 Dataset 对象
   - ✅ 修复：直接传递 `dataset` 对象，让模型内部处理数据准备
   - ✅ 简化代码：删除手动调用 `dataset.prepare()` 的代码

   **Bug 2**: `_record_results` 方法传递错误参数

   - ❌ 问题：传递 DataFrame 给 `model.predict()`，但期望 Dataset 对象
   - ✅ 修复：直接传递 `dataset` 对象
   - ✅ 简化代码：删除手动准备测试数据的代码

   **Bug 3**: MLflow API 调用错误

   - ❌ 问题：使用 `R.save_object()`，但正确的 API 是 `R.save_objects()`（复数）
   - ✅ 修复：改为 `R.save_objects(model=model)`

4. **成功运行完整测试**
   - ✅ 测试脚本：`backend/tests/services/test_qlib_workflow_service.py`
   - ✅ 测试结果：**全部通过** ✅
   - ✅ 性能数据：
     - 数据集准备：22.0 秒（Alpha158 因子计算）
     - 模型训练：3.3 秒（LGBModel，使用早停）
     - 结果记录：0.05 秒
     - 总耗时：25.4 秒

**🎓 关键知识点**:

1. **Qlib 模型的数据接口设计**：

   - `model.fit(dataset)` - 模型内部会调用 `dataset.prepare()` 获取训练/验证数据
   - `model.predict(dataset)` - 模型内部会调用 `dataset.prepare()` 获取测试数据
   - **不要手动准备数据**：让模型自己处理，避免参数传递错误

2. **Qlib 数据下载的正确方法**：

   - 使用官方脚本：`scripts/get_data.py`
   - 脚本是轻量级包装器，调用 `qlib.tests.data.GetData` 类
   - 支持参数：`--target_dir`、`--region`、`--interval`

3. **Dataset Segments 的灵活性**：

   - 可以只配置 `train` + `test`（简化版）
   - 可以配置 `train` + `valid` + `test`（标准版，推荐）
   - 可以使用自定义名称
   - LGBModel 必需 `train`，可选 `valid`（用于早停）

4. **Qlib 数据结构**：
   ```
   qlib_data/
   ├── calendars/        # 交易日历
   ├── features/         # 股票特征数据（按股票代码组织）
   └── instruments/      # 股票列表和元数据
   ```

**🐛 调试过程总结**:

遇到的错误和解决方案：

1. **AttributeError: 'DataFrame' object has no attribute 'segments'**

   - 原因：传递 DataFrame 而不是 Dataset 对象
   - 解决：直接传递 dataset 对象

2. **AttributeError: 'list' object has no attribute 'prepare'**

   - 原因：`dataset.prepare()` 返回的是 list/DataFrame，不能再调用 prepare
   - 解决：不要手动准备数据，让模型自己处理

3. **AttributeError: 'QlibRecorder' object has no attribute 'save_object'**
   - 原因：API 名称错误
   - 解决：使用 `save_objects()`（复数形式）

**📊 当前状态**:

Phase 1 核心服务已全部完成并测试通过：

- ✅ `qlib_config.py` - 配置管理
- ✅ `timer.py` - 耗时监控
- ✅ `qlib_init_service.py` - Qlib 初始化（已修复缓存配置）
- ✅ `qlib_workflow_service.py` - 训练工作流执行（已修复所有 Bug）
- ✅ `test_qlib_workflow_service.py` - 测试脚本（测试通过 ✅）
- ✅ `scripts/get_data.py` - Qlib 数据下载脚本
- ✅ Qlib 数据已下载并可用

**📝 下一步工作**:

1. ✅ ~~在 Docker 容器中运行测试验证功能~~ - 已完成
2. ✅ ~~根据测试结果修复可能的问题~~ - 已完成
3. 创建 API 路由暴露训练工作流服务
4. 通过 Swagger UI 测试 API
5. 实现推理工作流（`execute_inference_workflow`）

---

### 2026-01-27 凌晨 - Phase 1 工作流服务完成

**✅ 已完成的工作**:

1. **完善 `backend/app/services/qlib_workflow_service.py`**

   - ✅ 添加 `_execute_workflow_steps()` 方法：协调三个主要步骤的执行
   - ✅ 添加 `_create_dataset()` 方法：使用 `init_instance_by_config` 创建数据集
   - ✅ 添加 `_create_and_train_model()` 方法：创建模型、准备训练数据、训练模型
   - ✅ 添加 `_record_results()` 方法：在测试集上评估、保存模型到 MLflow、返回指标
   - ✅ 重命名主方法：从 `execute_workflow` 改为 `execute_training_workflow`（更明确的语义）

2. **创建测试文件 `backend/tests/services/test_qlib_workflow_service.py`**

   - ✅ 使用 Qlib 内置组件（Alpha158 + LGBModel）
   - ✅ 配置简化的训练工作流（2020年数据，减少测试时间）
   - ✅ 完整的测试流程：执行训练、验证结果、打印计时信息
   - ✅ 异常处理和错误报告

3. **代码清理**
   - ✅ 删除旧的 `backend/tests/services/data_sources/` 目录

**🎓 知识讲解**:

在今天的开发过程中，详细讲解了以下概念：

1. **Qlib 配置的层次结构**：

   - 全局数据源配置（在 `qlib.init()` 中）
   - Handler 配置（数据加载和因子计算）
   - Dataset 配置（数据分割）

2. **训练 vs 推理工作流的区别**：

   - 训练工作流：创建数据集 → 训练模型 → 记录结果
   - 推理工作流：加载模型 → 生成预测（待实现）

3. **Data Collector 的执行时机**：

   - 独立于 Workflow 运行
   - 定时任务（推荐）或手动触发
   - 数据收集和模型训练解耦

4. **Qlib 的数据流程**：
   ```
   qlib.init() 设置全局数据源
   ↓
   Handler 从数据源读取并计算因子
   ↓
   Dataset 分割数据（train/valid/test）
   ↓
   Model 训练和评估
   ```

---

### 2026-01-26 晚 - Phase 1 核心服务完成

**✅ 已完成的文件**:

1. **`backend/app/core/qlib_config.py`** - Qlib 配置管理

   - 使用 Pydantic Settings 管理所有 Qlib 配置参数
   - 支持从环境变量读取配置
   - 使用 `@lru_cache` 实现单例模式
   - 配置项：数据目录、区域、MLflow 路径、Redis 连接、缓存开关等

2. **`backend/app/core/timer.py`** - 简化的耗时监控工具

   - `Timer` 上下文管理器：用于单个代码块计时
   - `WorkflowTimer` 类：用于跟踪多步骤工作流的耗时
   - 通过日志输出开始时间、结束时间和执行时长
   - 设计简洁，易于使用

3. **`backend/app/services/qlib_init_service.py`** - Qlib 初始化服务

   - 使用单例模式（`__new__` 方法）确保只初始化一次
   - 配置 MLflow 实验管理器用于跟踪训练过程
   - 启用 Redis 缓存加速因子计算和数据加载
   - 提供 `initialize()` 方法供其他服务调用
   - 集成 `Timer` 监控初始化耗时

4. **`backend/app/services/qlib_workflow_service.py`** - 工作流执行服务（框架）
   - 类定义和完整的文档字符串
   - `execute_workflow()` 方法框架：
     - 确保 Qlib 已初始化
     - 使用 `WorkflowTimer` 跟踪各步骤耗时
     - 使用 `R.start()` 启动 MLflow 实验
     - 异常处理和日志记录
   - 预留 TODO 标记，待添加实际的工作流执行逻辑

**🎯 协作模式的建立**:

今天我们成功建立了**教学式协作开发模式**，并记录在文档的"合作模式"章节中：

- ✅ **一次只推进一小步**：每次只创建/修改一个小的代码片段
- ✅ **先教知识，再写代码**：先解释概念（如 `@contextmanager` 装饰器、单例模式、MLflow 等），再编写代码
- ✅ **用类比帮助理解**：用生活中的例子（如餐厅主厨、实验笔记本）解释技术概念
- ✅ **逐步检查**：每完成一小步就检查，发现问题立即修正
- ✅ **详细讲解**：对 Qlib、设计模式、Python 特性进行详细讲解

这种模式虽然进度较慢，但确保了：

- 代码质量高，错误少
- 用户能够理解每一行代码的含义
- 知识积累扎实，为后续开发打下良好基础

**📝 当前优先任务**：

1. **开发Yahoo Finance实时数据收集脚本** (最高优先级) ✅ 已完成

   - 目标：创建 `backend/scripts/get_data_yahoo_realtime.py`
   - 方法：使用yfinance SDK获取实时数据（延迟15-20分钟）
   - 输出：CSV格式，兼容现有dump_bin.py转换流程
   - 重要性：为后续回测、模拟盘等workflow提供实时数据支持
   - 符合Qlib标准：CSV → dump_bin.py → Qlib二进制格式

2. 继续完成数据源管理页面的前端集成
3. 按照开发计划推进后续功能

**🎯 Yahoo Collector开发计划**:

**阶段1：研究和设计**

- [ ] 深入研究Qlib文档中的Collector基类接口
- [ ] 分析yfinance库的API和数据格式
- [ ] 设计符合Qlib标准的collector架构

**阶段2：实现核心功能**

- [ ] 创建标准目录结构：`scripts/data_collector/yahoo/`
- [ ] 实现YahooFinanceCollector类，继承Qlib Collector基类
- [ ] 支持股票池选择：CSI300、CSI500、All Stocks
- [ ] 实现增量更新机制（--trading_date参数）

**阶段3：集成和测试**

- [ ] 更新data_utils.py调用新的collector
- [ ] 通过Docker环境测试collector功能
- [ ] 验证输出的Qlib数据格式正确性

**阶段4：部署和优化**

- [ ] 配置crontab定时任务支持
- [ ] 性能优化和错误处理
- [ ] 文档和使用说明

---

### 2026-02-01 上午 - 数据源管理API完成并验证 ✅

**✅ 已完成的工作**:

1. **成功验证数据源管理API功能**

   - ✅ 通过Swagger UI测试下载API：`POST /api/v1/data-source/download`
   - ✅ 验证状态检测API：`GET /api/v1/data-source/status`
   - ✅ 确认完整数据集下载：3875只股票，271.33MB数据
   - ✅ 验证数据时间范围：1999-11-10 到 2020-09-25（20年历史数据）
   - ✅ 确认股票池识别：正确识别为"yahoo_cn_full"

2. **数据一致性验证成功**

   - ✅ 确认文件命名格式：`SH600000`, `SZ000001`等标准Qlib格式
   - ✅ 验证目录结构：`features/`, `instruments/`, `calendars/`
   - ✅ 确认现有代码兼容性：无需修改现有逻辑

3. **实时数据更新需求规划**
   - ✅ 在tech_spec.md中详细记录Phase 7实时数据更新需求
   - ✅ 制定AKShare集成计划解决Yahoo数据滞后问题
   - ✅ 设计增量更新和自动调度机制
   - ✅ 规划复用现有API的扩展方案

**🎯 关键成就**:

从85只股票升级到3875只股票（45倍增长），数据源管理API全面验证通过：

- **API端点**: 3个REST API（状态、清理、下载）全部测试通过
- **数据规模**: 从85只股票扩展到3875只股票
- **数据质量**: 20年完整历史数据，7个标准技术指标
- **兼容性**: 保持文件命名一致性，现有代码无需修改
- **可扩展性**: 为实时数据更新奠定基础

**📊 测试结果总结**:

```json
// 下载API响应
{
  "task_id": "93124f48-1dd2-4456-97a8-d8cdc55208c4",
  "status": "completed",
  "message": "Successfully completed full data refresh"
}

// 状态API响应
{
  "source_name": "yahoo",
  "data_exists": true,
  "instruments_count": 3875,
  "stock_pool": "yahoo_cn_full",
  "data_range_start": "1999-11-10",
  "data_range_end": "2020-09-25",
  "data_size_mb": 271.33
}

经过讨论，确定采用**简化设计方案**：

- **用户只需选择**：数据源类型 + 股票池
- **系统自动处理**：获取该数据源支持的完整时间范围
- **显示结果**：实际时间范围、股票数量、数据大小、时效性提示

**界面组成**：

1. 数据源选择：Yahoo Finance / AKShare / Tushare
2. 股票池选择：CSI300 / CSI500 / All Stocks
3. 操作按钮：下载数据、清空数据
4. 状态显示：当前数据源信息、时间范围、股票数量、数据大小

**用户体验流程**：

```

选择数据源和股票池 → 点击下载 → 系统自动获取完整数据 → 显示实际结果

````

这种设计避免了用户手动配置时间范围的复杂性，符合"获取完整历史数据"的核心需求。

**📋 Collector脚本扩展计划（修订版）**:

**⚠️ 重要发现**：经过深入研究Qlib文档，发现我们当前的方法不完全符合Qlib标准做法。

**Qlib标准做法**：
- 官方提供 `scripts/data_collector/` 目录下的标准collector
- 使用 `qlib.workflow.task.collect.Collector` 基类
- 直接输出Qlib格式，无需CSV中转和dump_bin转换

**修订后的扩展方案**：

### 方案A：继承Qlib Collector基类（推荐）
```python
from qlib.workflow.task.collect import Collector

class YFinanceCollector(Collector):
    def collect(self, **kwargs):
        # 直接输出Qlib二进制格式
        # 支持增量更新和时间范围参数
        pass
````

### 方案B：标准collector目录结构

```
backend/scripts/data_collector/
├── yfinance/
│   ├── collector.py  # 主收集器，模仿官方yahoo collector
│   └── README.md
├── tushare/
│   ├── collector.py
│   └── README.md
└── akshare/
    ├── collector.py
    └── README.md
```

**架构优势**：

- 符合Qlib官方标准和最佳实践
- 直接输出Qlib格式，性能更高
- 支持官方的增量更新机制
- 可集成到Qlib的任务管理系统
- 便于使用crontab等标准调度工具

**实现计划**：

1. 研究 `qlib.workflow.task.collect.Collector` 基类接口
2. 参考官方 `scripts/data_collector/yahoo/collector.py` 实现
3. 创建标准的collector目录结构
4. 实现直接输出Qlib二进制格式的数据收集器

**🔄 重要更新**：经过与用户确认，当前架构完全符合Qlib标准！

**✅ 确认的标准做法**：

```
数据源 → get_data.py脚本 → CSV格式 → dump_bin.py → Qlib二进制格式
```

**数据源扩展的正确方式**：

1. **Yahoo Finance实时**：开发 `get_data_yahoo_realtime.py`，使用yfinance SDK获取实时数据
2. **Tushare**：开发 `get_data_tushare.py`，集成Tushare Pro API
3. **AKShare**：开发 `get_data_akshare.py`，使用AKShare开源库

**统一转换流程**：所有数据源脚本输出CSV格式，然后统一使用 `scripts/qlib/dump_bin.py` 转换为Qlib格式。

---

## 🔄 实时数据更新需求 (Phase 7)

### 需求概述

**目标**: 实现数据源切换后的自动实时数据更新机制

**核心需求**:

- 用户切换数据源后，系统自动清空旧数据
- 下载新数据源的完整历史数据（尽可能获取到最新数据）
- 建立每日自动更新机制，保持数据时效性

### 详细需求分析

#### 1. 数据源切换流程

```

用户选择新数据源 (如 CSI300)
↓
清空现有数据 (qlib_data + csv_data)
↓
下载完整历史数据 (从数据源支持的最早日期到最新日期)
↓
转换为 Qlib 格式
↓
启用每日自动更新

```

#### 2. 实时数据更新策略

**数据源优先级**:

1. **AKShare** (推荐) - 免费、开源、实时更新
2. **Tushare** - 专业数据、有免费额度
3. **Yahoo Finance** (当前) - 数据滞后，仅到2020年

**更新频率**:

- **每日更新**: 交易日收盘后自动更新
- **增量更新**: 只下载缺失的日期数据
- **全量刷新**: 用户手动触发或定期执行

#### 3. 技术实现方案

**3.1 数据源抽象层**

```python
class BaseDataSource:
    def get_latest_date(self) -> str
    def download_data(self, start_date: str, end_date: str) -> bool
    def supports_realtime(self) -> bool
    def get_supported_instruments(self) -> List[str]
```

**3.2 增量更新机制**

```python
class IncrementalUpdater:
    def check_missing_dates(self) -> List[str]
    def update_missing_data(self, missing_dates: List[str]) -> bool
    def validate_data_integrity(self) -> bool
```

**3.3 调度系统**

```python
# 使用 APScheduler 或 Celery
@scheduler.scheduled_job('cron', hour=18, minute=0)  # 每日18:00
def daily_data_update():
    updater = IncrementalUpdater()
    updater.update_missing_data()
```

### 开发计划

#### Phase 7.1: AKShare 集成 (1-2周)

- [ ] 安装和配置 AKShare 库
- [ ] 实现 AKShare 数据收集器
- [ ] 支持 A股、港股实时数据获取
- [ ] 数据格式标准化和验证

#### Phase 7.2: 增量更新机制 (1周)

- [ ] 实现数据完整性检查
- [ ] 实现增量数据下载
- [ ] 数据冲突检测和处理
- [ ] 更新日志和监控

#### Phase 7.3: 自动调度系统 (1周)

- [ ] 集成 APScheduler 或 Celery
- [ ] 实现每日自动更新任务
- [ ] 错误处理和重试机制
- [ ] 更新状态通知

#### Phase 7.4: 数据源管理界面 (1周)

- [ ] 数据源选择和配置界面
- [ ] 更新状态监控界面
- [ ] 手动触发更新功能
- [ ] 数据质量报告

### 复用现有功能

**可复用的API端点**:

- `GET /api/v1/data-source/status` - 检查数据状态
- `DELETE /api/v1/data-source/clear` - 清空数据
- `POST /api/v1/data-source/download` - 下载数据

**扩展方向**:

- 添加 `source` 参数支持多数据源 (akshare, tushare)
- 添加 `update_mode` 参数 (full, incremental)
- 添加调度配置接口

### 预期效果

**用户体验**:

- 一键切换数据源，自动处理数据更新
- 数据始终保持最新，支持实时回测和训练
- 透明的更新状态，用户了解数据时效性

**系统稳定性**:

- 增量更新减少网络和存储压力
- 错误恢复机制保证数据完整性
- 监控和日志便于问题排查

**数据质量**:

- 支持多数据源交叉验证
- 自动数据质量检查
- 历史数据和实时数据无缝衔接

### 风险和挑战

**技术风险**:

- 不同数据源的数据格式差异
- 网络不稳定导致的下载失败
- 大量历史数据的存储和处理

**解决方案**:

- 统一的数据格式转换层
- 重试机制和断点续传
- 数据压缩和分片存储

**数据风险**:

- 数据源服务不稳定
- 数据质量问题
- 实时性要求vs数据准确性

**解决方案**:

- 多数据源备份机制
- 数据验证和清洗流程
- 可配置的更新策略
  - `_create_dataset()` - 创建数据集
  - `_create_and_train_model()` - 创建并训练模型
  - `_record_results()` - 记录结果

2. 编写测试脚本：

   - 使用 Qlib 内置组件（Alpha158 + LGBModel）
   - 验证整个流程是否正常工作

3. 创建 API 路由暴露服务功能

4. 通过 Swagger UI 测试 API

### 2026-01-26 早 - 架构重构与方案确定

### 2026-01-26 - 架构重构与方案确定

**重大变更**: 从手动实现改为完全基于 Qlib Workflow

**删除的代码**:

- 所有手动实现的服务层代码
- 所有手动实现的 API 路由
- 自定义的因子/模型处理逻辑

**保留的代码**:

- 基础 FastAPI 模板结构
- 用户认证和权限系统
- 数据库模型定义（用于未来参考）

**原因**:

- 手动实现过于复杂且容易出错（特别是数据对齐问题）
- Qlib Workflow 是官方验证的标准方式
- 符合项目"为 Qlib 加前端"的定位

**关键技术决策**:

1. **数据对齐**: 完全依赖 Qlib 自动对齐机制，避免手动管理
2. **用户管理**: 单用户系统 + 共享数据目录，简化复杂度
3. **性能优化**: 使用 Qlib 所有内置加速机制（Redis Cache、Expression Cache 等）
4. **扩展顺序**: 数据源 → 因子引擎 → 模型 → 策略
5. **配置界面**: 完整配置 + 预设模板，兼顾易用性和灵活性

**下一步**:

- Phase 1: 实现核心 Workflow 执行器
- 使用 Qlib 内置组件（Alpha158 + LGBModel）验证全流程
- 确保数据对齐问题得到彻底解决

### 2026-01-27 晚 - Qlib Workflow API 开发完成

**🎉 重要里程碑**: 成功完成 Qlib Workflow API 的完整开发和测试

**主要成就**:

#### 1. 完整的 Pydantic 模型体系

**文件**: `backend/app/models.py` (第870-1048行)

- **QlibComponentConfig**: 基础模型，定义 `class_name`, `module_path`, `kwargs` 字段
- **ModelConfig**: 继承基础模型，用于机器学习模型配置
- **DataHandlerConfig**: 继承基础模型，用于数据处理器配置
- **DatasetSegments**: 定义训练/验证/测试时间段
- **DatasetKwargs**: 组合数据处理器和时间段配置
- **DatasetConfig**: 完整的数据集配置
- **TaskConfig**: 组合模型和数据集的任务配置
- **TrainingWorkflowRequest**: API 请求模型
- **TrainingWorkflowResponse**: API 响应模型

**关键技术决策**:

- 移除了 `serialization_alias` 以兼容当前 Pydantic 版本
- 使用 `class_name` 字段映射到 Qlib 的 `class` 配置
- 建立了完整的嵌套模型层次结构

#### 2. 功能完整的 API 路由

**文件**: `backend/app/api/routes/qlib_workflow.py`

- **GET /api/v1/qlib/health**: 健康检查端点
- **POST /api/v1/qlib/training-workflow**: 训练工作流端点

**核心功能**:

- 完整的请求验证和错误处理
- Pydantic 模型到 Qlib 配置的正确转换
- 与 `QlibWorkflowService` 的无缝集成
- 结构化的响应格式

**关键修复**:

- 修复了 `await` 语法错误（改为同步调用）
- 正确的字段映射：`class_name` → `"class"`
- 优化的数据范围配置（2017-2020，4年数据）

#### 3. 成功的端到端测试

**测试结果**:

```json
// 健康检查测试
GET /api/v1/qlib/health
Status: 200
Response: {
  "status": "healthy",
  "service": "qlib_workflow",
  "message": "Qlib workflow service is ready"
}

// 训练工作流测试
POST /api/v1/qlib/training-workflow
Status: 200
Response: {
  "status": "success",
  "predictions_count": 54000,
  "model_saved": true,
  "experiment_name": "test_api_quick",
  "error_message": null
}
```

**性能指标**:

- **predictions_count**: 54000（约225只股票 × 240个交易日）
- **训练时间**: 优化后的4年数据范围，训练速度显著提升
- **模型保存**: 成功集成 MLflow 模型管理

#### 4. 架构验证和技术决策

**同步 vs 异步设计**:

- 确认同步设计正确：机器学习训练是 CPU 密集型任务
- 异步化不会带来性能提升，反而增加复杂度
- 未来如需高并发，应使用任务队列而非异步编程

**数据范围优化**:

- 从12年数据（2008-2020）优化为4年数据（2017-2020）
- 平衡了训练效果和执行速度
- 验证了 Qlib 数据处理的正确性

**字段映射设计**:

- 解决了 Python 保留字 `class` 的命名冲突
- 建立了 Pydantic 模型到 Qlib 配置的正确映射
- 确保了 API 输入输出的一致性

#### 5. 开发过程总结

**协作模式验证**:

- 成功实践了"一次只改一小步"的开发方式
- 每个步骤都有详细的教学解释和技术分析
- 问题发现和修复过程清晰可追溯

**关键问题解决**:

1. **Pydantic 版本兼容性**: 移除不支持的 `serialization_alias`
2. **字段映射错误**: 修复 `class_name` 到 `class` 的映射
3. **异步语法错误**: 移除不必要的 `await` 关键字
4. **数据范围优化**: 缩短训练数据范围提升性能

**技术栈验证**:

- ✅ FastAPI + Pydantic: 强类型 API 开发
- ✅ Qlib Workflow: 稳定的量化交易工作流
- ✅ SQLModel: 数据模型定义
- ✅ Docker: 容器化开发环境

---

## 🎨 训练工作流 UI 优化 (2026-01-29)

### 实现的功能

**1. 后端配置管理系统**

创建了智能配置管理系统，自动填充 Qlib 组件配置：

- **QlibComponentRegistry** (`backend/app/services/qlib_component_registry.py`)

  - 维护 Model、Handler、Dataset 的 class → module_path 映射
  - 支持 10 种模型：LGBModel, XGBModel, CatBoostModel, LinearModel, MLPModel, GRUModel, LSTMModel, GATs, ALSTM, TransformerModel
  - 支持 4 种 Handler：Alpha158, Alpha101, Alpha360, DataHandlerLP
  - 支持 2 种 Dataset：DatasetH, TSDatasetH
  - 自动填充 `module_path` 字段，前端无需提供

- **模型超参数配置文件** (`backend/app/config/model_hyperparameters.py`)
  - 为每个模型定义默认超参数
  - 包含详细的参数说明和教育性注释
  - 用户可通过编辑配置文件调整超参数，无需修改代码
  - 后端自动读取并填充到训练请求中

**2. 前端用户配置界面**

- **Instruments 配置**：CSI 300, CSI 500, CSI 800, All Stocks
- **Frequency 配置**：Daily, Weekly, Monthly
- **简化的 API 请求**：前端只需发送 `class_name`，后端自动填充 `module_path` 和默认超参数

**3. 用户体验优化**

- **按钮 Loading 状态**：

  - 点击 "Start Training" 后按钮变为 "Training..."
  - 显示旋转加载图标
  - 按钮禁用防止重复提交

- **训练进度提示**：
  - 实时显示训练阶段："Preparing request..." → "Initializing Qlib and preparing dataset..." → "Training completed!"
  - 蓝色背景的进度提示框
  - 训练失败时显示错误提示

### 技术实现

**后端修改**：

- `backend/app/models.py`: 将 `module_path` 字段改为可选 (`str | None`)
- `backend/app/api/routes/qlib_workflow.py`: 使用 registry 自动填充配置
- 新增配置文件和 registry 服务

**前端修改**：

- `frontend/src/routes/_layout/training.tsx`:
  - 添加 `useState` 管理训练状态
  - 添加 `instruments` 和 `freq` 表单字段
  - 实现按钮 loading 状态和进度显示
  - 简化 API 请求体，移除硬编码的 `module_path` 和超参数

### 测试结果

✅ **训练工作流完整测试通过**：

- 数据加载：56.66 秒，成功加载 CSI300 数据
- 特征处理：DropnaLabel + CSZScoreNorm
- 模型训练：LightGBM，early stopping 在第 3 轮
- 验证集 L2 损失：0.996521
- 生成预测：18,900 个预测结果
- 模型保存到 MLflow：成功
- HTTP 响应：200 OK

### 架构优势

1. **配置驱动**：用户通过配置文件调整超参数，无需修改代码
2. **前端简化**：前端只需关注业务逻辑，技术细节由后端处理
3. **易于扩展**：添加新模型只需在 registry 和配置文件中注册
4. **用户友好**：清晰的进度反馈和加载状态

---

**📝 下一步工作**:

**Phase 2: 前端功能扩展**

1. ✅ ~~创建 React 组件调用训练工作流 API~~
2. ✅ ~~设计用户友好的配置界面~~
3. 实现训练结果的可视化展示
4. 添加训练历史记录查询

**Phase 3: API 功能扩展**

1. 添加回测工作流端点
2. 添加策略评估端点
3. 实现模型管理和版本控制

**Phase 4: 系统优化**

1. 添加任务队列支持长时间训练
2. 实现实时训练进度追踪（WebSocket）
3. 添加超参数在线编辑功能（高级用户）

---

### 2026-02-02 上午 - Yahoo Finance 实时数据收集器开发完成并测试通过 ✅

**🎉 重要里程碑**: 成功完成 Yahoo Finance 实时数据收集器的完整开发、实现和测试验证

**主要成就**:

#### 1. 完整的数据收集器实现

**文件**: `backend/scripts/get_data_yahoo_realtime.py` (384行)

**核心组件**:

- **StockPool类**: 动态获取CSI300/CSI500成分股

  - 使用第三方API: `https://yfiua.github.io/index-constituents/`
  - 成功获取300只CSI300股票
  - 完善的错误处理和日志记录

- **YahooDataCollector类**: 核心数据收集逻辑

  - 支持增量更新机制
  - 可扩展字段配置 (`--fields` 参数)
  - 兼容 `get_data.py` 接口
  - 使用 `yfinance` SDK 获取历史数据

- **命令行接口**: 完整的 `argparse` 实现
  - 兼容参数: `--file_name`, `--target_dir`
  - 扩展参数: `--stock_pool`, `--fields`, `--period`, `--start_date`, `--end_date`, `--incremental`
  - 子命令结构: `download_data`

#### 2. 成功的功能测试验证

**测试环境**: Docker容器中完整测试

**第一次测试 (2024-01-01 到 2024-01-05)**:

- ✅ StockPool API调用成功: 获取300只CSI300成分股
- ✅ 数据下载成功: 298/300股票成功下载 (98.3%成功率)
- ✅ CSV文件生成: 每个文件约300-320字节，包含3天完整OHLCV数据
- ✅ 文件格式正确: 标准CSV格式，列名符合Qlib标准

**增量更新测试 (2024-01-06 到 2024-01-08)**:

- ✅ 增量检测正确: 自动检测现有文件最后日期 (2024-01-04)
- ✅ 增量下载成功: 从2024-01-05开始下载新数据
- ✅ 数据追加正确: 文件行数从4行增加到5行
- ✅ 294/300股票成功更新

**CSV格式验证**:

```csv
date,open,high,low,close,volume
2024-01-02,8.148481668921864,8.174514924007113,7.99228048324585,7.99228048324585,115836645
2024-01-03,7.974924019854992,8.000958101189676,7.940212738990963,7.983602046966553,73361031
2024-01-04,7.974924888626745,7.974924888626745,7.879469062747461,7.9055023193359375,86419399
```

#### 3. 关键技术问题解决

**问题1: Docker热更新配置**

- 问题: `get_data_yahoo_realtime.py` 未同步到Docker容器
- 解决: 修正 `docker-compose.override.yml` volume配置
- 修复: `./scripts:/app/scripts:cached` → `./backend/scripts:/app/scripts:cached`

**问题2: 代码拼写错误**

- 问题: `_save_csv_daa` 方法名拼写错误
- 解决: 修正为 `_save_csv_data`
- 影响: 修复后所有CSV保存功能正常工作

**问题3: 数据时间范围**

- 问题: 春节休市期间无数据导致大量错误
- 解决: 使用历史数据测试 (2024年1月)
- 结果: 98.3%成功率，只有2只股票无数据 (新股或退市股)

#### 4. 设计架构验证

**参数兼容性**: ✅ 完全兼容

- 继承 `get_data.py` 所有参数
- 扩展自定义参数不影响现有调用
- 可直接集成到 `data_utils.py` 工作流

**输出格式标准**: ✅ 完全符合

- CSV格式与Qlib标准一致
- 文件命名规范: `{symbol}.csv`
- 列名标准: `date,open,high,low,close,volume`

**增量更新机制**: ✅ 工作正常

- CSV级别增量检测
- 数据追加而非覆盖
- 避免重复下载，提高效率

**错误处理**: ✅ 健壮可靠

- API失败优雅处理
- 个别股票失败不影响整体
- 详细日志记录便于调试

#### 5. 性能表现

**API响应速度**: ~0.5秒/股票
**数据质量**: 历史数据完整可靠
**错误率**: 仅2%股票无数据 (主要是新股或退市股)
**增量效率**: 正确避免重复下载

#### 6. 集成就绪状态

**脚本完全就绪，可以**:

1. **集成到 `data_utils.py`** 中供后端API调用
2. **通过Swagger UI测试** 数据收集接口
3. **开发前端界面** 进行数据源管理
4. **扩展其他数据源** (Tushare、AKShare等)

**集成调用示例**:

```python
# 在 data_utils.py 中替换现有调用
cmd_download = [
    "python", "/app/scripts/get_data_yahoo_realtime.py",
    "download_data",
    "--stock_pool", "csi300",
    "--incremental",
    "--target_dir", "/app/csv_data/cn_data",
    "--fields", "open,high,low,close,volume"
]
```

#### 7. 开发过程总结

**协作模式成功验证**:

- 一次只改一小步的开发方式高效可靠
- 每个步骤都有详细的教学解释
- 问题发现和修复过程清晰可追溯

**关键学习成果**:

- Docker volume配置的重要性
- 热更新机制的正确配置方法
- 中国股市数据的特殊性 (春节休市等)
- yfinance SDK的使用方法和限制
- CSV格式标准化的重要性

**技术栈验证**:

- ✅ yfinance SDK: 稳定的Yahoo Finance数据获取
- ✅ pandas: 高效的数据处理和CSV输出
- ✅ requests: 可靠的第三方API调用
- ✅ argparse: 标准的命令行接口
- ✅ pathlib: 现代的文件路径处理

**📊 最终测试数据总结**:

```
测试1 (初始下载):
- 时间范围: 2024-01-01 到 2024-01-05
- 成功股票: 298/300 (98.3%)
- 生成文件: 298个CSV文件
- 数据完整性: ✅ 通过

测试2 (增量更新):
- 时间范围: 2024-01-06 到 2024-01-08
- 成功股票: 294/300 (98.0%)
- 文件更新: 从4行增加到5行
- 增量机制: ✅ 工作正常
```

**🎯 当前状态**: Yahoo Finance实时数据收集器开发完成，所有功能测试通过，可投入生产使用

**📝 下一步工作**:

1. 将脚本集成到 `data_utils.py` 中
2. 通过Swagger UI测试数据收集API
3. 开发前端数据源管理界面
4. 扩展支持其他数据源 (Tushare、AKShare)

---

## 🎯 数据收集器设计原则 (2026-02-02)

### 核心设计原则

基于Yahoo Finance数据收集器的开发经验，确立以下设计原则，适用于所有未来的数据收集器开发：

#### 1. **字段收集策略**

**原则**：配置驱动的字段收集，收集器根据配置文件自动调用多个API获取所需字段，失败时透明反馈

**设计理念**：

- **配置驱动**：在配置文件中统一定义需要收集的字段，而非通过用户参数传递
- **自动收集**：收集器根据配置自动调用多个API获取所有配置的字段
  class DataCollector:
  def **init**(self, data_source: str):
  self.config = self.\_load_config(data_source)
  self.required_fields = self.config['required_fields']
  self.field_api_mapping = self.config['field_api_mapping']
  def collect_data(self) -> Dict[str, Any]:
  """根据配置自动收集所有必需字段"""
  results = {}
  failed_fields = []

          # 按API分组字段，减少API调用次数
          api_groups = self._group_fields_by_api(self.required_fields)

          for api_name, fields in api_groups.items():
              try:
                  api_data = self._call_api(api_name, fields)
                  results.update(api_data)
              except APINotSupportedException:
                  failed_fields.extend(fields)
                  logger.warning(f"API {api_name} 不支持字段: {fields}")
              except APICallException as e:
                  failed_fields.extend(fields)
                  logger.error(f"API {api_name} 调用失败: {e}")

          # 生成收集报告
          successful_fields = [f for f in self.required_fields if f not in failed_fields]
          self._log_collection_report(successful_fields, failed_fields)

          return results, successful_fields, failed_fields

````

**多API调用策略**：

```python
def _group_fields_by_api(self, fields: List[str]) -> Dict[str, List[str]]:
    """将字段按API分组，优化调用效率"""
    api_groups = defaultdict(list)

    for field in fields:
        api_name = self.field_api_mapping.get(field)
        if api_name:
            api_groups[api_name].append(field)
        else:
            # 尝试通过字段推断可能的API
            api_name = self._infer_api_for_field(field)
            if api_name:
                api_groups[api_name].append(field)

    return dict(api_groups)

def _infer_api_for_field(self, field: str) -> Optional[str]:
    """智能推断字段可能对应的API"""
    # 价格相关字段
    if any(keyword in field.lower() for keyword in ['price', 'open', 'high', 'low', 'close']):
        return "price_api"

    # 成交量相关
    if any(keyword in field.lower() for keyword in ['volume', 'turnover', 'amount']):
        return "price_api"

    # 基本面相关
    if any(keyword in field.lower() for keyword in ['pe', 'pb', 'market_cap', 'revenue']):
        return "fundamentals_api"

    return None
````

**用户体验**：

- 前端显示每个数据源支持的字段列表
- 当用户选择的字段不被支持时，提供清晰的错误提示
- 建议用户选择其他数据源或调整字段需求

#### 2. **参数接口标准化**

**原则**：所有数据收集器遵循统一的参数接口标准

**标准参数**：

```python
def download_data(
    target_dir: str,           # 输出目录
    stock_pool: str,           # 股票池选择
    start_date: str,           # 开始日期
    end_date: str,             # 结束日期
    incremental: bool,         # 增量更新
    fields: str,               # 字段选择
    period: str = None,        # 相对时间范围（与绝对时间互斥）
) -> Tuple[bool, str]:
```

**兼容性要求**：

- 继承 `get_data.py` 的基础参数（`--file_name`, `--target_dir`）
- 扩展自定义参数不影响现有调用
- 支持命令行和API两种调用方式

#### 3. **错误处理和用户反馈**

**原则**：提供清晰、可操作的错误信息

**错误分类**：

- **配置错误**：参数格式错误、字段不支持等
- **网络错误**：API调用失败、超时等
- **数据错误**：股票代码无效、数据缺失等

**反馈格式**：

```python
# 成功示例
return True, f"成功收集 {success_count}/{total_count} 只股票数据"

# 错误示例
return False, f"字段验证失败: 不支持字段 {invalid_fields}"
return False, f"网络错误: 无法连接到 {data_source} API"
return False, f"数据错误: {error_count} 只股票无可用数据"
```

#### 4. **扩展性设计**

**原则**：为未来数据源扩展提供标准模板

**模板结构**：

```
backend/scripts/get_data_{source}_realtime.py
├── StockPool类：股票池管理
├── {Source}DataCollector类：核心数据收集逻辑
├── 字段验证：_validate_fields()
├── 日期解析：_parse_date_range()
├── 增量更新：_check_incremental()
└── CSV输出：_save_csv_data()
```

**命名约定**：

- 脚本文件：`get_data_{source}_realtime.py`
- 收集器类：`{Source}DataCollector`
- 股票池类：`StockPool` (可复用或继承)

#### 5. **数据质量保证**

**原则**：确保输出数据的一致性和可靠性

**质量检查**：

- **格式验证**：CSV格式、列名、数据类型
- **完整性检查**：时间序列连续性、缺失值处理
- **一致性验证**：与Qlib标准格式的兼容性

**输出标准**：

```csv
date,open,high,low,close,volume
2024-01-02,8.148,8.175,7.992,7.992,115836645
2024-01-03,7.975,8.001,7.940,7.984,73361031
```

### 应用示例

**Yahoo Finance收集器**：

- ✅ 支持8个字段：OHLCV + adj_close + dividends + splits
- ✅ 统一参数接口，兼容现有API
- ✅ 完善的字段验证和错误处理
- ✅ 支持增量更新和时间范围选择

**未来Tushare收集器**：

- 将支持更多基本面字段：PE、PB、市值等
- 遵循相同的接口标准和错误处理模式
- 提供字段映射，兼容不同数据源的字段命名

**未来AKShare收集器**：

- 支持实时数据和更多市场（港股、美股）
- 统一的股票池管理和字段验证机制
- 保持与其他收集器的接口一致性

### 设计价值

1. **用户体验**：简化操作流程，提供清晰反馈
2. **开发效率**：标准化模板，加速新数据源集成
3. **系统稳定性**：统一的错误处理和质量保证
4. **可维护性**：一致的代码结构和命名约定
5. **扩展性**：为未来功能扩展奠定基础

---

# 🗂️ 数据源管理系统开发记录 (2026-01-29)

## 📋 开发目标

实现数据源管理功能，允许用户从前端页面选择数据源并下载数据。基于用户需求分析，确定了以下关键设计决策：

### 关键设计决策

**1. 数据源切换策略**

- **问题**：当切换数据源时（如从Yahoo Finance切换到Tushare），是否需要清空现有数据？
- **分析**：由于每个实例只针对一个市场（cn或us），且同一市场的不同数据源（如Tushare、AkShare、Yahoo Finance CN）可能存在数据格式和质量差异
- **决策**：采用清空策略 - 切换数据源时清空现有数据，确保数据一致性

**2. 标准化数据收集流程**

- **设计理念**：基于Qlib官方机制，不重新造轮子
- **标准流程**：`Collector脚本 → CSV数据 → dump_bin.py → .bin格式`
- **优势**：
  - 完全遵循Qlib官方工具链
  - 为未来数据源扩展提供标准化方式
  - CSV格式便于调试和数据验证

**3. 数据收集器架构**

- **核心工具**：使用`backend/scripts/get_data.py`（基于`qlib.tests.data.GetData`）
- **调用方式**：`python scripts/get_data.py download_data --file_name csv_data_cn.zip --target_dir ~/.qlib/csv_data/cn_data`
- **扩展性**：每个数据源有专门的函数（如`download_yahoo_csv_data`），而非通用函数

## 🏗️ 技术实现

### Phase 1: 基础模型和工具函数

**1. Pydantic模型设计** ✅

- `DataSourceStatus`: 数据源状态信息
- `DownloadDataRequest`: 下载请求参数
- `DownloadTaskResponse`: 任务创建响应
- `DownloadTaskStatus`: 任务状态追踪
- `ClearDataResponse`: 数据清空响应

**2. 数据工具函数**

- `clear_qlib_data()`: 安全清空qlib_data目录
- `execute_yahoo_data_collector()`: 调用Yahoo collector下载CSV数据

**3. 配置系统设计**

- **路径配置集中化**：在`backend/app/core/config.py`中统一管理所有数据路径
- **配置项**：
  - `QLIB_DATA_PATH = "/app/qlib_data"`: Qlib数据存储路径
  - `CSV_DATA_PATH = "/app/csv_data"`: CSV数据临时存储路径
  - `DEFAULT_CSV_FILE_NAME = "csv_data_cn.zip"`: 默认数据文件名
- **分层架构**：
  - `*_impl`函数：处理具体业务逻辑，接受参数
  - 公共函数：使用配置系统，确保路径一致性
- **优势**：
  - 避免数据清空和创建时路径不一致问题
  - 集中管理，便于维护和环境适配
  - 为未来多数据源扩展提供标准模式

### Phase 2: 数据收集器实现

**优化后的标准化流程设计**：

```python
# Step 1: 清空旧数据（确保数据一致性）
clear_qlib_data()              # 清空现有qlib_data

# Step 2: 下载CSV数据（特定数据源）
execute_yahoo_data_collector()    # Yahoo Finance
execute_tushare_data_collector()  # Tushare (未来实现)
execute_akshare_data_collector()  # AkShare (未来实现)

# Step 3: 转换为Qlib格式（通用）
convert_csv_to_qlib_format()   # 调用dump_bin.py
```

**流程优势**：

- **数据一致性**：先清空避免新旧数据混合
- **错误处理**：下载失败时保持环境干净
- **存储优化**：避免同时存储多份数据
- **调试友好**：每步状态明确，便于排查问题

**当前进展**：

### 已完成功能

- ✅ Yahoo数据收集器已完成
- ✅ 配置系统已完成
- ✅ CSV到Qlib格式转换功能已完成
- ✅ 数据源状态查询API已完成
- ✅ 股票池智能识别功能已完成
- ✅ 完整的21年历史数据解析已完成
- ✅ Yahoo Finance实时数据收集器设计

### 设计决策 (2026-02-01)

基于对Qlib文档的深入研究和现有系统架构分析，我们设计了一个符合Qlib标准实践的Yahoo Finance实时数据收集器。

#### 核心设计原则

1. **Qlib标准兼容性**：

   - 输出CSV格式与 `get_data.py` 完全一致
   - 兼容现有的 `dump_bin.py` 转换工作流
   - 遵循Qlib数据收集器模式：`Collector → CSV → dump_bin.py → Qlib format`

2. **参数接口兼容性**：

   - **继承 `get_data.py` 的所有参数**：`--file_name`, `--target_dir` 等
   - **扩展自定义参数**：`--stock_pool`, `--fields`, `--period`, `--start_date`, `--incremental`
   - **保持调用方式一致**：可直接替换到现有 `data_utils.py` 工作流中

3. **数据收集器开发原则**（适用于所有未来数据源）：

   ```bash
   # 基础兼容参数（必须支持）
   --file_name          # 输出文件名（与get_data.py一致）
   --target_dir         # 目标目录（与get_data.py一致）

   # 数据源特定扩展参数
   --stock_pool         # 股票池选择（csi300, csi500）
   --fields             # 数据字段选择（open,high,low,close,volume）
   --period             # 时间周期（1y, 6m, 3m）
   --start_date         # 开始日期（YYYY-MM-DD）
   --end_date           # 结束日期（YYYY-MM-DD）
   --incremental        # 增量更新模式
   ```

#### 输出格式标准

1. **文件结构**：

   - 每个股票一个CSV文件：`{symbol}.csv`
   - 文件保存到 `target_dir` 指定目录
   - 与现有系统的 `csv_data/cn_data/` 结构一致

2. **CSV格式**：

   ```csv
   date,open,high,low,close,volume
   2023-01-01,100.0,105.0,99.0,103.0,1000000
   2023-01-02,103.0,107.0,102.0,106.0,1200000
   ```

3. **可扩展字段支持**：

   - **默认字段**：`open,high,low,close,volume`（Qlib标准OHLCV）
   - **当前扩展字段**：`adj_close,dividends,splits`（通过 `--fields` 参数）
   - **未来扩展能力**：支持添加基本面数据、技术指标等

   **--fields 参数设计**：

   - 格式：逗号分隔的字段名列表
   - 示例：`--fields open,high,low,close,volume,adj_close`
   - 验证：自动检查请求字段是否在支持列表中
   - 扩展：新字段只需在代码中添加到支持列表即可

   **支持的扩展字段类型**：

   - **价格调整**：`adj_close`（考虑分红和拆股的调整价格）
   - **公司行为**：`dividends`（分红信息）、`splits`（股票分割）
   - **未来可扩展**：`market_cap`（市值）、`pe_ratio`（市盈率）、`turnover`（换手率）等

#### 股票池管理系统

1. **动态成分股获取**：

   - 使用第三方API：`https://yfiua.github.io/index-constituents/`
   - 支持CSI300、CSI500指数成分股
   - API失败时的本地备选方案

2. **StockPool类设计**：
   ```python
   class StockPool:
       def get_symbols(self) -> List[str]
       def get_name(self) -> str
   ```

#### 命令行接口设计

```bash
# 基础用法（兼容get_data.py）
python get_data_yahoo_realtime.py --file_name data.zip --target_dir /app/csv_data/cn_data

# 扩展用法（新增功能）
python get_data_yahoo_realtime.py --stock_pool csi300 --period 1y --target_dir /app/csv_data/cn_data
python get_data_yahoo_realtime.py --stock_pool csi500 --start_date 2023-01-01 --target_dir /app/csv_data/cn_data
python get_data_yahoo_realtime.py --stock_pool csi300 --incremental --target_dir /app/csv_data/cn_data

# 字段扩展用法（未来功能）
python get_data_yahoo_realtime.py --stock_pool csi300 --fields open,high,low,close,volume,adj_close --target_dir /app/csv_data/cn_data
```

#### 技术架构

1. **核心组件**：

   ```
   get_data_yahoo_realtime.py
   ├── StockPool（股票池管理）
   ├── YahooDataCollector（数据收集核心）
   ├── IncrementalUpdater（增量更新逻辑）
   └── CSVExporter（CSV格式输出）
   ```

2. **增量更新机制**：

   - **CSV级别增量**：检查现有CSV文件的最后日期，只下载缺失日期的数据
   - **二进制级别增量**：使用Qlib的 `update_data_to_bin` 命令增量转换
   - **数据追加**：新数据追加到现有CSV文件，避免重复下载

3. **增量更新工作流**：

   ```bash
   # 步骤1：增量下载CSV数据
   python get_data_yahoo_realtime.py download_data --stock_pool csi300 --incremental --target_dir /app/csv_data/cn_data

   # 步骤2：增量转换为Qlib二进制格式
   python scripts/qlib/dump_bin.py update_data_to_bin --qlib_data_1d_dir /app/qlib_data
   ```

4. **data_utils.py 集成调用方式**：

   ```python
   # 增量下载Yahoo Finance数据
   cmd_download = [
       "python", "/app/scripts/get_data_yahoo_realtime.py",
       "download_data",
       "--stock_pool", stock_pool,  # csi300/csi500
       "--incremental",             # 启用增量模式
       "--target_dir", csv_data_path,
       "--fields", "open,high,low,close,volume"  # 可扩展字段
   ]

   # 增量转换为Qlib格式
   cmd_convert = [
       "python", "/app/scripts/qlib/dump_bin.py",
       "update_data_to_bin",        # 使用增量更新命令
       "--qlib_data_1d_dir", qlib_data_path
   ]
   ```

5. **集成点**：
   - 直接替换 `data_utils.py` 中的 `get_data.py` 调用
   - 兼容现有API端点
   - 保持相同的错误处理模式
   - 支持增量和全量两种更新模式通过Swagger UI测试API功能

### 后续阶段

1. 实现前端数据源管理界面
2. 添加进度追踪和用户反馈
3. 扩展支持Tushare和AkShare数据源
4. 实现数据状态监控和报告

## 📚 技术要点

**教育性说明**：

- **Service Layer Pattern**: 将业务逻辑从API路由中分离
- **Command Pattern**: 使用subprocess调用外部脚本
- **Strategy Pattern**: 不同数据源使用不同的收集策略
- **Pipeline Pattern**: 标准化的数据处理流水线

**安全考虑**：

- 路径验证防止误删重要目录
- 错误处理和异常捕获
- 进程执行的安全性检查

---

## 🎯 数据源管理模块完成总结 (2026-02-03)

### ✅ 第一阶段：数据管理模块 - 完全实现

**开发周期**: 2026-01-26 至 2026-02-03 (约1周)

#### 🚀 核心功能实现

**1. 后端API系统**:

- ✅ **数据状态API** (`/api/v1/data-source/status`) - 实时数据状态查询
- ✅ **数据清理API** (`/api/v1/data-source/clear`) - 完整数据清空
- ✅ **数据下载API** (`/api/v1/data-source/download`) - 支持完整和增量下载
- ✅ **增量更新支持** - 智能识别现有数据，只下载缺失部分

**2. 前端管理界面** (`frontend/src/routes/_layout/data-sources.tsx`):

- ✅ **实时数据状态监控** - 数据源、股票池、工具数量、数据大小、日期范围
- ✅ **数据收集配置** - 数据源选择、股票池选择、日期范围设置
- ✅ **三种操作模式**:
  - **Download Data**: 按配置完整重新下载
  - **Incremental Update**: 智能补充最新数据(独立于配置)
  - **Clear Data**: 清空所有现有数据
- ✅ **用户体验优化** - 加载动画、状态反馈、错误处理

**3. 数据收集器优化** (`backend/scripts/get_data_yahoo_realtime.py`):

- ✅ **增量更新逻辑** - 自动从最后日期继续下载
- ✅ **日期边界修复** - 修复yfinance左闭右开区间问题
- ✅ **配置驱动字段** - 支持动态字段配置
- ✅ **错误处理增强** - 完善的异常处理和日志记录

#### 🔧 关键技术决策和解决方案

**1. 增量更新架构设计**:

- **决策**: 增量更新独立于用户配置，自动更新到最新日期
- **实现**: 前端智能获取当前数据状态，后端从最后日期+1天开始下载
- **优势**: 用户无需手动调整日期，真正的"一键更新"体验

**2. 日期边界值问题解决**:

- **问题**: yfinance使用`[start, end)`左闭右开区间，导致缺失最后一天数据
- **解决**: 在`_download_symbol_data`方法中将`end_date`加1天传给yfinance
- **结果**: 用户配置的日期范围与实际获取数据完全一致

**3. 前端状态管理优化**:

- **问题**: 数据清空后前端状态显示异常
- **解决**: 改进数据状态检测逻辑，正确识别`source_name="unknown"`的无数据状态
- **结果**: 清空数据后正确显示"No data available"提示

**4. 用户界面交互完善**:

- **加载动画**: 所有操作按钮都有旋转图标和状态文本
- **按钮优化**: Download按钮图标从Download改为RefreshCw，适合旋转动画
- **状态反馈**: 实时显示操作进度和结果

#### 📊 功能验证结果

**测试场景覆盖**:

- ✅ 初始数据下载 (2024-01-01 to 2024-01-31)
- ✅ 增量数据更新 (自动扩展到2026-02-02)
- ✅ 数据完全清空 (状态正确重置)
- ✅ 按新配置重新下载 (2024-02-01 to 2024-02-28)
- ✅ 日期边界验证 (确保包含配置的最后一天)

**性能指标**:

- 数据下载速度: ~296个CSI300股票，约30秒
- 增量更新效率: 只下载缺失日期，显著提升速度
- 用户体验: 所有操作都有即时视觉反馈

#### 🎯 架构优势

**1. 模块化设计**:

- 前后端完全分离，API标准化
- 数据收集器独立可测试
- 配置驱动，易于扩展新数据源

**2. 用户体验优先**:

- 智能增量更新，无需手动配置
- 实时状态监控，信息透明
- 一致的视觉反馈，操作可预期

**3. 技术债务控制**:

---

## 🧮 第二阶段：因子工程模块设计方案 (2026-02-03)

### ✅ Qlib因子系统架构研究完成

**研究成果**:

- ✅ **Qlib Data Handler扩展约定** - 深入理解继承和接口要求
- ✅ **Alpha158实现模式分析** - 掌握标准因子引擎实现方法
- ✅ **工作流集成机制** - 理解QlibComponentRegistry注册和配置系统
- ✅ **表达式系统原理** - 掌握Qlib因子表达式语法和计算机制

### 🏗️ 自定义因子引擎架构设计

#### 🎯 设计目标

**核心需求**:

- 用户可通过前端界面使用Qlib表达式语法动态添加因子
- 完全符合Qlib Data Handler扩展约定
- 与现有workflow系统无缝集成
- 支持因子验证、管理和性能分析

**技术约束**:

- 必须继承Qlib标准Data Handler基类
- 遵循Qlib表达式系统规范
- 兼容现有QlibComponentRegistry架构
- 支持MLflow实验跟踪和缓存机制

#### 🔧 核心组件设计

**1. CustomFactorHandler (自定义因子引擎核心)**

```python
# 位置: backend/app/services/custom_factor_handler.py
class CustomFactorHandler(DataHandlerLP):
    """
    自定义因子引擎 - 符合Qlib扩展约定

    功能特性:
    - 继承DataHandlerLP支持可学习处理器
    - 动态加载用户自定义因子表达式
    - 兼容Alpha158因子库
    - 支持因子缓存和批量计算优化
    """

    def __init__(self,
                 start_time, end_time, fit_start_time, fit_end_time,
                 instruments,
                 custom_factors=None,      # 用户自定义因子列表
                 include_alpha158=True,    # 是否包含Alpha158因子
                 factor_cache=True,        # 因子计算缓存
                 **kwargs):
        # 实现符合Qlib约定的初始化逻辑
```

**2. FactorExpressionManager (因子表达式管理器)**

```python
# 位置: backend/app/services/factor_expression_manager.py
class FactorExpressionManager:
    """
    因子表达式管理系统

    核心功能:
    - Qlib表达式语法验证和解析
    - 用户自定义因子CRUD操作
    - 因子版本管理和回滚
    - 表达式性能分析和优化建议
    """

    def validate_expression(self, expression: str) -> ValidationResult
    def parse_expression(self, expression: str) -> ParsedFactor
    def save_factor(self, factor: CustomFactor) -> str
    def get_factor_list(self, user_id: str) -> List[CustomFactor]
```

**3. 因子管理API端点**

```python
# 位置: backend/app/api/routes/factor_management.py
# RESTful API设计:
# POST   /api/v1/factors              - 创建新因子
# GET    /api/v1/factors              - 获取因子列表
# GET    /api/v1/factors/{factor_id}  - 获取特定因子
# PUT    /api/v1/factors/{factor_id}  - 更新因子
# DELETE /api/v1/factors/{factor_id}  - 删除因子
# POST   /api/v1/factors/validate     - 验证因子表达式
# POST   /api/v1/factors/test         - 测试因子计算
```

**4. QlibComponentRegistry集成**

```python
# 扩展现有注册表:
HANDLER_REGISTRY = {
    "Alpha158": "qlib.contrib.data.handler",
    "Alpha101": "qlib.contrib.data.handler",
    "Alpha360": "qlib.contrib.data.handler",
    "CustomFactorHandler": "app.services.custom_factor_handler",  # 新增
    "DataHandlerLP": "qlib.contrib.data.handler",
}
```

#### 📊 数据模型设计

**CustomFactor (自定义因子模型)**

```python
class CustomFactor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, description="因子名称")
    expression: str = Field(description="Qlib表达式")
    description: Optional[str] = Field(description="因子描述")
    category: str = Field(description="因子分类")
    created_by: str = Field(description="创建用户")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    validation_status: str = Field(description="验证状态")
```

#### 🔄 工作流集成方案

**Workflow配置示例**:

```yaml
task:
  dataset:
    class: DatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: CustomFactorHandler # 使用自定义因子引擎
        module_path: app.services.custom_factor_handler
        kwargs:
          start_time: "2020-01-01"
          end_time: "2023-12-31"
          fit_start_time: "2020-01-01"
          fit_end_time: "2022-12-31"
          instruments: "csi300"
          custom_factors: # 用户自定义因子
            - name: "custom_rsi"
              expression: "RSI($close, 14)"
            - name: "custom_macd"
              expression: "EMA($close, 12) - EMA($close, 26)"
          include_alpha158: true # 同时包含Alpha158
```

### 🚀 实施计划

#### 第一步: CustomFactorHandler基础框架 (1-2天)

- **目标**: 创建符合Qlib约定的基础Data Handler类
- **任务**:
  - 继承DataHandlerLP并实现必需接口
  - 支持基础的因子表达式解析
  - 实现与Alpha158的兼容性
  - 添加基础的错误处理和日志

#### 第二步: 因子表达式管理系统 (2-3天)

- **目标**: 实现完整的因子管理后端逻辑
- **任务**:
  - 开发FactorExpressionManager类
  - 实现Qlib表达式语法验证
  - 创建因子数据库模型和CRUD操作
  - 添加因子版本管理功能

#### 第三步: API端点开发 (1-2天)

- **目标**: 提供RESTful API接口
- **任务**:
  - 实现因子管理API端点
  - 添加请求验证和错误处理
  - 集成到FastAPI应用
  - 编写API文档和测试

#### 第四步: 系统集成 (1天)

- **目标**: 集成到现有Qlib工作流系统
- **任务**:
  - 注册到QlibComponentRegistry
  - 测试workflow配置兼容性
  - 验证与现有系统的集成

#### 第五步: 前端界面开发 (3-4天)

- **目标**: 创建用户友好的因子管理界面
- **任务**:
  - 因子列表和详情页面
  - 因子表达式编辑器
  - 实时语法验证
  - 因子测试和预览功能

#### 第六步: 测试和优化 (2-3天)

- **目标**: 确保系统稳定性和性能
- **任务**:
  - 端到端功能测试
  - 性能基准测试
  - 错误处理完善
  - 文档更新

---

## 🧮 因子工程模块完整方案 (Pipeline集成版) - 2026-02-17

### 📋 方案概述

基于用户最终确认的Pipeline集成架构，实现一个完全兼容Qlib Workflow的高性能因子引擎系统。

#### 🎯 核心目标

- **Pipeline直接集成**: 因子计算作为FactorStage直接集成到数据Pipeline中
- **极简逻辑**: 全量数据→全量计算，增量数据→增量计算，无复杂状态检测
- **数据库驱动**: 因子定义存储在数据库，通过前端界面管理，无用户权限区分
- **预存储机制**: 因子数据存储为bin文件，训练时高速读取
- **Qlib加速**: 多进程并行计算，性能提升3-5倍
- **完整功能**: IC分析、数据下载、依赖分析等全套工具

### 🏗️ 系统架构设计

#### Pipeline集成架构

```
数据Pipeline流程 (简化版):
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CollectStage  │ -> │ NormalizeStage  │ -> │   DumpStage     │ -> │  FactorStage    │
│   数据收集       │    │   数据标准化     │    │  转换bin格式     │    │  因子计算        │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                                                              │
                                                                              ▼
                                                                    ┌─────────────────┐
                                                                    │  bin文件存储     │
                                                                    │ /features/      │
                                                                    └─────────────────┘
```

#### 核心组件架构

```
前端管理界面:
├── 因子CRUD管理 (Factor Management)
├── Pipeline监控 (Pipeline Monitor)
├── 数据下载功能 (Data Download)
├── 依赖字段显示 (Dependency Analysis)
├── IC分析图表 (IC Analysis)
└── Alpha158开关 (Alpha158 Toggle)

Pipeline集成层:
├── FactorStage (核心Pipeline阶段)
├── 全量/增量自动检测 (Auto Detection)
├── Qlib加速计算 (Qlib Acceleration)
└── bin文件存储 (Binary Storage)

后端服务层:
├── CustomFactorHandler (Qlib兼容Handler)
├── AcceleratedFactorEngine (高性能计算引擎)
├── FactorAnalysisEngine (IC分析引擎)
├── DataDownloadService (数据导出服务)
├── FactorDependencyAnalyzer (依赖分析器)
└── ExpressionValidator (表达式验证器)

数据存储层:
├── 因子数据库 (Factor, FactorAnalysis)
├── bin文件存储 (/app/qlib_data/features/)
└── 原始数据存储 (/app/qlib_data/)
```

### 📊 数据库模型设计

#### 简化的Factor模型 (移除用户权限和分类)

```python
class Factor(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100, description="Factor name")
    expression: str = Field(description="Factor expression in Qlib format")
    description: str | None = Field(default=None, max_length=500)
    status: FactorStatus = Field(default=FactorStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # IC分析字段
    last_ic_value: float | None = Field(default=None, description="Latest IC value")
    last_ic_date: datetime | None = Field(default=None, description="Latest IC calculation date")
    avg_ic_value: float | None = Field(default=None, description="Average IC value")
    ic_ir_ratio: float | None = Field(default=None, description="IC Information Ratio")

    # 计算状态字段
    last_computed_at: datetime | None = Field(default=None, description="Last computation time")
    computation_status: str | None = Field(default=None, description="pending/computing/completed/failed")
    data_points_count: int | None = Field(default=None, description="Number of data points computed")

    # 移除字段: created_by, category, creator (简化设计)
```

#### 因子分析结果模型

```python
class FactorAnalysis(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    factor_id: uuid.UUID = Field(foreign_key="factor.id")
    analysis_date: datetime = Field(default_factory=datetime.utcnow)

    # IC分析结果
    ic_value: float | None = Field(default=None)
    ic_pvalue: float | None = Field(default=None)
    rank_ic_value: float | None = Field(default=None)

    # 相关性分析结果
    correlation_matrix: dict | None = Field(default=None, description="JSON format")

    # 统计指标
    mean_value: float | None = Field(default=None)
    std_value: float | None = Field(default=None)
    sharpe_ratio: float | None = Field(default=None)

class FactorDependency(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    factor_id: uuid.UUID = Field(foreign_key="factor.id")
    field_name: str = Field(description="Required data field like $close, $volume")
    field_type: str = Field(description="price/volume/technical")
    is_available: bool = Field(description="Whether field is available in current data")
    description: str | None = Field(default=None)
```

### 🔧 核心组件实现规划

#### 1. FactorStage (Pipeline集成核心)

**文件位置**: `backend/app/services/pipeline/factor_stage.py`
**核心功能**:

- 继承Pipeline基类，作为数据Pipeline的一个阶段
- 从workspace自动获取数据更新类型（全量/增量）
- 简化逻辑：根据数据类型选择计算模式
- 集成Qlib加速机制，支持多进程并行计算
- 自动存储因子数据为bin文件格式

#### 2. CustomFactorHandler (Qlib兼容)

**文件位置**: `backend/app/services/custom_factor_handler.py`
**核心功能**:

- 继承Qlib的DataHandlerLP类，完全兼容Qlib Workflow
- 从数据库动态加载活跃因子定义
- 支持Alpha158因子库的可选集成
- 构建符合Qlib标准的feature配置
- 优先使用预计算的bin文件，fallback到动态计算

#### 3. AcceleratedFactorEngine (高性能计算)

**文件位置**: `backend/app/services/accelerated_factor_engine.py`
**核心功能**:

- 基于Qlib的多进程加速机制
- 支持全量和增量两种计算模式
- 因子数据存储为Qlib标准bin格式
- 集成Qlib的缓存和优化机制
- 性能监控和计算状态跟踪

#### 4. 分析和工具服务

**FactorAnalysisEngine**: IC分析、相关性分析
**DataDownloadService**: 因子数据和原始数据下载
**FactorDependencyAnalyzer**: 依赖数据字段分析
**ExpressionValidator**: Qlib表达式验证

### 🌐 前端界面设计

#### 因子管理页面 (`frontend/src/routes/_layout/factors.tsx`)

- **因子列表**: 显示所有因子，支持CRUD操作
- **表达式编辑器**: 实时语法验证的Qlib表达式编辑
- **Alpha158开关**: 全局Alpha158因子库集成控制
- **计算状态**: 显示因子计算进度和状态

#### Pipeline监控页面 (`frontend/src/routes/_layout/pipeline-monitor.tsx`)

- **Pipeline状态**: 各阶段执行进度和状态
- **FactorStage监控**: 因子计算专项监控
- **配置控制**: 因子计算开关、加速设置
- **日志查看**: 实时Pipeline执行日志

#### 数据分析页面 (`frontend/src/routes/_layout/factor-analysis.tsx`)

- **IC分析图表**: 时序IC值、统计指标
- **相关性热力图**: 因子间相关性矩阵
- **依赖分析**: 显示因子依赖的数据字段
- **数据下载**: 多格式因子数据导出

### 🔌 API设计

#### 因子管理API

```python
# 基础CRUD
POST   /api/v1/factors                    # 创建因子
GET    /api/v1/factors                    # 获取因子列表
PUT    /api/v1/factors/{id}               # 更新因子
DELETE /api/v1/factors/{id}               # 删除因子

# 表达式验证
POST   /api/v1/factors/validate           # 验证Qlib表达式
POST   /api/v1/factors/{id}/dependencies  # 分析因子依赖

# Alpha158管理
GET    /api/v1/factors/alpha158/status    # Alpha158开关状态
POST   /api/v1/factors/alpha158/toggle    # 切换Alpha158开关
```

#### Pipeline集成API

```python
# Pipeline监控
GET    /api/v1/pipeline/status            # Pipeline整体状态
GET    /api/v1/pipeline/factor-stage      # FactorStage专项状态
POST   /api/v1/pipeline/factor-config     # 更新因子计算配置

# 手动触发 (开发初期使用)
POST   /api/v1/factors/compute            # 手动触发因子计算
GET    /api/v1/factors/compute/status     # 查询计算状态
```

#### 数据分析API

```python
# IC分析
POST   /api/v1/factors/analyze/ic         # 触发IC分析
GET    /api/v1/factors/{id}/ic-results    # 获取IC分析结果

# 数据下载
POST   /api/v1/factors/download           # 下载因子数据
POST   /api/v1/data/download              # 下载原始数据
```

### 🚀 实施计划 (3周)

#### 第1周: Pipeline集成和核心引擎

**Day 1-2: 研究Qlib源码**

- 深入研究Alpha158实现 (`qlib-source/qlib/contrib/data/handler.py`)
- 研究qrun命令实现 (`qlib-source/qlib/workflow/`)
- 理解Pipeline和DataHandler集成机制

**Day 3-4: FactorStage实现**

- 实现Pipeline集成的FactorStage类
- 集成数据更新类型自动检测
- 实现全量/增量计算逻辑分发

**Day 5-7: AcceleratedFactorEngine**

- 实现基于Qlib加速的因子计算引擎
- 支持bin文件存储和读取
- 集成多进程并行计算

#### 第2周: Handler和服务层

**Day 8-10: CustomFactorHandler**

- 重构现有CustomFactorHandler
- 实现数据库驱动的因子加载
- 集成Alpha158可选支持

**Day 11-12: 分析和工具服务**

- 实现FactorAnalysisEngine (IC分析)
- 实现DataDownloadService (数据导出)
- 实现FactorDependencyAnalyzer (依赖分析)

**Day 13-14: API端点开发**

- 创建因子管理API端点
- 实现Pipeline监控API
- 集成数据分析API

#### 第3周: 前端和集成测试

**Day 15-17: 前端界面开发**

- 因子管理页面 (CRUD + Alpha158开关)
- Pipeline监控页面 (状态 + 配置)
- 数据分析页面 (IC图表 + 下载)

**Day 18-19: 系统集成测试**

- Pipeline端到端测试
- Qlib Workflow兼容性测试
- 性能基准测试

**Day 20-21: 优化和文档**

- 性能优化和错误处理完善
- API文档和用户手册
- 部署和配置指南

### ✅ 验收标准

#### 功能完整性

- ✅ Pipeline自动因子计算 (全量/增量)
- ✅ 因子CRUD管理 (数据库驱动，无用户权限)
- ✅ Alpha158集成开关
- ✅ 数据下载功能 (因子数据 + 原始数据)
- ✅ IC分析工具 (时序分析 + 统计指标)
- ✅ 依赖分析 (显示所需数据字段)
- ✅ Pipeline监控 (状态 + 配置 + 日志)

#### 性能要求

- ✅ 因子计算速度提升3-5倍 (Qlib加速)
- ✅ 训练速度提升10-100倍 (预存储bin文件)
- ✅ 支持1000+因子管理
- ✅ 增量计算效率优化

#### 系统稳定性

- ✅ Qlib Workflow完全兼容
- ✅ Pipeline集成无缝运行
- ✅ 错误处理和恢复机制
- ✅ 数据一致性保证

### 🎯 技术优势

#### 1. 极简架构

- **Pipeline直接集成**: 无需复杂的数据状态检测
- **自动触发**: 跟随数据更新自动执行因子计算
- **逻辑清晰**: 全量→全量，增量→增量，简单明了

#### 2. 高性能设计

- **Qlib原生加速**: 多进程并行，GPU支持
- **预存储机制**: bin文件格式，训练时高速读取
- **增量优化**: 只计算新增数据，避免重复计算

#### 3. 用户友好

- **数据库驱动**: 通过界面管理，无需修改配置文件
- **简化权限**: 无用户权限区分，降低复杂度
- **完整工具链**: 从因子开发到分析的全套工具

---

### 🎯 预期成果

**功能交付**:

- ✅ 完整的自定义因子引擎系统
- ✅ 用户友好的因子管理界面
- ✅ 与Qlib工作流的无缝集成
- ✅ 因子表达式验证和测试工具

**技术价值**:

- 扩展了Qlib的因子工程能力
- 提供了标准化的因子管理解决方案
- 为后续Alpha158集成和因子分析奠定基础
- 展示了Qlib扩展开发的最佳实践

**用户价值**:

- 量化研究员可以快速创建和测试新因子
- 支持因子的版本管理和团队协作
- 降低了因子开发的技术门槛
- 提高了因子研发的效率和质量

---

## 📊 因子表达式验证系统设计 (2026-02-11更新)

### 🔍 研究发现和重大决策

#### Qlib表达式处理机制深度研究

**研究时间**: 2026-02-11  
**研究范围**: Qlib官方文档 `docs/qlib-html/index.html`

**核心发现**:

1. **Qlib表达式系统架构**:

   - **D.features()方法**: Qlib处理表达式的核心接口
   - **ExpressionOps类**: 负责表达式操作的基础类
   - **Expression类**: 表达式的基础抽象类
   - **ElemOperator类**: 元素级操作符

2. **支持的表达式类型**:

   ```python
   # 基础字段
   '$close', '$open', '$high', '$low', '$volume'

   # 时序操作符
   'Ref($close, 1)'      # 获取前1期收盘价
   'Ref($close, -2)'     # 获取后2期收盘价(用于标签)

   # 统计操作符
   'Mean($close, 3)'     # 3期移动平均
   'EMA($close, 12)'     # 12期指数移动平均

   # 横截面操作符
   '$rank($close)'       # 收盘价排名

   # 算术操作符
   '$high-$low'          # 价格差
   '$close/$open'        # 价格比率

   # 复杂表达式示例
   'MACD': '2 * ((EMA($close, 12) - EMA($close, 26))/$close - EMA((EMA($close, 12) - EMA($close, 26))/$close, 9))'
   'Label': 'Ref($close, -2)/Ref($close, -1) - 1'
   ```

3. **表达式验证机制**:
   - **关键发现**: Qlib本身**没有提供独立的表达式验证API**
   - **验证时机**: 表达式验证发生在`D.features()`**执行时**
   - **错误处理**: 语法错误时Qlib会抛出异常
   - **缓存机制**: ExpressionCache可以缓存表达式计算结果

#### 重大架构决策

**决策1: 基于Qlib的验证策略**

- **原则**: 遵循第3点规则"基于qlib，不要造轮子"
- **方案**: 使用Qlib的`D.features()`方法进行"试运行"验证
- **实现**: 通过最小数据集调用来检测表达式语法错误

**决策2: 数据库模型复用**

- **发现**: `backend/app/models.py`中已存在完整的Factor数据库模型
- **包含字段**: name, expression, description, category, status, timestamps, created_by
- **决策**: 复用现有模型，无需重新创建

**决策3: CustomFactorHandler架构完善**

- **状态**: 第一步(拼写错误修正)和第二步(数据库模型确认)已完成
- **当前**: 进入第三步(表达式验证实现)

### 🎯 表达式验证系统完整设计方案

#### 核心设计思路

**验证策略**:

1. 使用Qlib的D.features()方法进行表达式验证
2. 通过最小数据集试运行来检测语法错误
3. 捕获Qlib异常并转换为用户友好的错误提示
4. 支持批量验证和结果缓存

#### 系统架构

```
┌─────────────────────────────────────────────┐
│     Factor Expression Validator             │
│  - validate_expression()                    │
│  - validate_expressions_batch()             │
│  - get_supported_operators()                │
│  - get_expression_examples()                │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│         CustomFactorHandler                 │
│  - Enhanced _validate_custom_factors()      │
│  - Integration with expression validator    │
│  - Database factor loading with validation  │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│       Factor Management API                 │
│  - POST /api/v1/factors/validate            │
│  - POST /api/v1/factors (with validation)   │
│  - CRUD operations for factors              │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│      Frontend Factor Management             │
│  - Expression editor with syntax highlight  │
│  - Real-time validation feedback            │
│  - Factor library and examples              │
└─────────────────────────────────────────────┘
```

#### 详细实施计划

**阶段1: 表达式验证服务基础框架 (1-2天)**

- 文件: `backend/app/services/factor_expression_validator.py`
- 核心功能:
  ```python
  class FactorExpressionValidator:
      def validate_expression(self, expression: str) -> ValidationResult
      def validate_expressions_batch(self, expressions: List[str]) -> List[ValidationResult]
      def get_supported_operators(self) -> List[str]
      def get_expression_examples(self) -> Dict[str, str]
  ```

**阶段2: 验证服务功能完善 (1天)**

- 详细错误处理和用户友好提示
- 表达式语法检查和建议
- 性能优化和结果缓存

**阶段3: CustomFactorHandler集成 (1天)**

- 修改`_validate_custom_factors()`方法
- 集成表达式验证逻辑
- 增强错误信息和调试支持

**阶段4: 因子管理API开发 (2天)**

- 文件: `backend/app/api/routes/factor_management.py`
- API端点:
  - `POST /api/v1/factors/validate` - 表达式验证
  - `POST /api/v1/factors` - 创建因子(含验证)
  - `GET /api/v1/factors` - 获取因子列表
  - `PUT /api/v1/factors/{id}` - 更新因子
  - `DELETE /api/v1/factors/{id}` - 删除因子

**阶段5: 前端界面开发 (3-4天)**

- 因子管理页面设计
- 表达式编辑器实现
- 实时验证反馈
- 因子库和示例展示

### 🔧 技术实现细节

#### 表达式验证核心逻辑

```python
def validate_expression(self, expression: str) -> ValidationResult:
    """
    使用Qlib的D.features()方法验证表达式语法

    Educational Notes:
    - 通过最小数据集试运行来检测语法错误
    - 捕获Qlib异常并转换为友好提示
    - 支持常见错误的智能建议
    """
    try:
        # 使用最小数据集进行试运行
        test_instruments = ["SH600000"]  # 单只股票
        test_fields = [expression]

        # 调用Qlib进行验证
        D.features(
            instruments=test_instruments,
            fields=test_fields,
            start_time='2020-01-01',
            end_time='2020-01-02'  # 最小时间范围
        )

        return ValidationResult.VALID

    except Exception as e:
        # 解析Qlib异常并提供友好提示
        return self._parse_qlib_error(str(e))
```

#### 错误处理和用户提示

```python
def _parse_qlib_error(self, error_msg: str) -> ValidationResult:
    """
    解析Qlib错误信息并提供用户友好的提示

    常见错误类型:
    - 语法错误: 括号不匹配、操作符错误等
    - 函数错误: 不支持的函数名、参数错误等
    - 字段错误: 不存在的字段名等
    """
    if "syntax error" in error_msg.lower():
        return ValidationResult(
            status="invalid_syntax",
            message="Expression syntax error",
            suggestion="Check parentheses and operator usage"
        )
    # ... 更多错误类型处理
```

### 📈 当前开发状态

**已完成**:

- ✅ CustomFactorHandler拼写错误修正
- ✅ 因子数据库模型确认(复用现有模型)
- ✅ Qlib表达式处理机制深度研究
- ✅ 表达式验证系统完整设计方案

**进行中**:

- 🔄 tech_spec.md文档更新(当前任务)

**待开始**:

- ⏳ 表达式验证服务基础框架实现
- ⏳ 验证服务功能完善
- ⏳ CustomFactorHandler集成
- ⏳ 因子管理API开发
- ⏳ 前端界面开发

### 🎯 下一步行动计划

**立即执行**:

1. 完成tech_spec.md文档更新
2. 开始实施阶段1: 创建表达式验证服务基础框架

**预期时间线**:

- 阶段1-3: 3-4天 (后端核心功能)
- 阶段4: 2天 (API开发和测试)
- 阶段5: 3-4天 (前端界面)
- 总计: 8-10天完成完整的因子表达式验证系统

**成功标准**:

- 用户可以通过前端界面创建和验证因子表达式
- 系统提供实时的语法检查和错误提示
- 因子可以成功集成到Qlib工作流中
- 通过Swagger UI完成所有API测试

---

## 🔄 Pipeline集成到现有API (2026-02-16)

### 📊 当前状态

- ✅ Pipeline三个阶段已完成实现
- ✅ DataPipelineService主服务已完成
- ✅ 模块导出已完成
- 🔄 准备集成到现有API端点

### 🎯 集成方案

#### 现有API流程分析

现有 `download_data_source_endpoint` 使用三步流程：

1. `clear_qlib_data()` - 清理现有数据
2. `execute_yahoo_data_collector()` - 下载CSV数据
3. `convert_csv_to_qlib_format()` - 转换为Qlib格式

#### Pipeline集成策略

- **保持API接口不变**：继续使用 `DownloadDataRequest` 和 `DownloadTaskResponse`
- **替换内部实现**：用 `execute_data_pipeline(request)` 替换三步流程
- **向后兼容**：前端无需任何修改

#### 集成优势

1. **统一数据流**：collect → normalize → dump 一体化
2. **更好的错误处理**：每个阶段独立验证和错误报告
3. **工作空间管理**：自动创建和清理临时文件
4. **扩展性**：易于添加新数据源支持

### 🚀 实施计划

1. 修改 `data_source.py` 导入pipeline模块
2. 替换 `download_data_source_endpoint` 的实现
3. 在Swagger中测试新的pipeline
4. 在前端页面中测试完整流程

### 📋 注意事项

- 遵循规则12：不引用qlib-source代码，只使用pyqlib暴露的接口
- 保持现有API契约不变
- 确保错误处理和日志记录完整

### 🔧 技术实现细节

#### Pipeline模块结构

```
backend/app/services/data_collectors/pipeline/
├── __init__.py          # ✅ 模块导出
├── service.py           # ✅ DataPipelineService主服务
└── stages.py            # ✅ 三个阶段实现
```

#### 核心组件

- **CollectStage**: 数据收集（支持Yahoo数据源）
- **NormalizeStage**: 数据标准化（使用UniversalNormalize）
- **DumpStage**: 数据转储（转换为Qlib .bin格式）
- **DataPipelineService**: 主服务编排器
- **execute_data_pipeline**: API集成便利函数

#### 数据流程

```
DownloadDataRequest → execute_data_pipeline() →
CollectStage → NormalizeStage → DumpStage →
DownloadTaskResponse
```

---

## 📊 Yahoo Finance API数据限制 (2026-02-17)

### ⚠️ 重要限制说明

基于Yahoo Finance API官方文档分析，系统在获取分钟级数据时存在以下限制：

#### 🕐 分钟级数据限制

**数据可用性限制**：

- ✅ **支持间隔**：1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h
- 📅 **时间范围**：仅支持**最近30天**的分钟级数据
- 📦 **单次请求**：每次请求最多**7天**的分钟级数据
- 🔄 **自动分批**：yahooquery库会自动将长时间范围分批处理

**技术实现细节**：

```python
# Yahoo Finance API限制示例
# ✅ 正确：请求最近7天的1分钟数据
tickers.history(period='7d', interval='1m')

# ✅ 正确：请求最近30天数据（自动分4批，每批7天）
tickers.history(period='1mo', interval='1m')

# ❌ 错误：请求超过30天的历史分钟数据
tickers.history(start='2024-01-01', end='2024-01-31', interval='1m')
```

#### 📈 日级数据限制

**数据可用性**：

- ✅ **历史范围**：支持多年历史数据
- ✅ **无特殊限制**：1d, 5d, 1wk, 1mo等间隔均可正常使用
- ✅ **推荐使用**：用于历史回测和长期分析

### 🎨 前端界面限制和提示

#### 必须实现的用户界面限制

**1. 分钟级数据选择限制**：

```javascript
// 当用户选择分钟级间隔时，限制日期选择范围
if (interval.includes("m") || interval.includes("h")) {
  const maxDate = new Date();
  const minDate = new Date();
  minDate.setDate(maxDate.getDate() - 30); // 最近30天

  // 限制日期选择器范围
  dateRangePicker.setMinDate(minDate);
  dateRangePicker.setMaxDate(maxDate);
}
```

**2. 用户提示信息**：

- **警告提示**：选择分钟级数据时显示"⚠️ 分钟级数据仅支持最近30天"
- **日期验证**：实时验证所选日期是否在允许范围内
- **自动调整**：当用户选择超出范围的日期时，自动调整到最近可用日期

**3. 界面交互优化**：

```jsx
// React组件示例
const IntervalSelector = () => {
  const [interval, setInterval] = useState("1d");
  const [dateRange, setDateRange] = useState([]);

  const isMinuteInterval = interval.includes("m") || interval.includes("h");
  const maxHistoryDays = isMinuteInterval ? 30 : 365 * 10; // 分钟数据30天，日数据10年

  return (
    <div>
      <Select value={interval} onChange={setInterval}>
        <Option value="1d">1 Day</Option>
        <Option value="1h">1 Hour ⚠️</Option>
        <Option value="1m">1 Minute ⚠️</Option>
      </Select>

      {isMinuteInterval && (
        <Alert type="warning">
          分钟级数据仅支持最近30天，请选择合适的日期范围
        </Alert>
      )}

      <DateRangePicker
        maxDate={new Date()}
        minDate={new Date(Date.now() - maxHistoryDays * 24 * 60 * 60 * 1000)}
        value={dateRange}
        onChange={setDateRange}
      />
    </div>
  );
};
```

#### 🔧 后端验证逻辑

**API请求验证**：

```python
def validate_minute_data_request(request: DownloadDataRequest):
    """验证分钟级数据请求的日期范围"""
    if request.interval in ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h']:
        start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(request.end_date, '%Y-%m-%d')
        now = datetime.now()

        # 检查是否超过30天限制
        if (now - start_date).days > 30:
            raise HTTPException(
                status_code=400,
                detail="分钟级数据仅支持最近30天，请调整开始日期"
            )

        # 检查单次请求是否超过7天
        if (end_date - start_date).days > 7:
            logger.warning("请求超过7天，将自动分批处理")

    return True
```

### 📋 开发任务清单

**前端开发必须实现**：

- [ ] 间隔选择器添加分钟数据警告标识
- [ ] 日期选择器根据间隔动态限制范围
- [ ] 实时日期范围验证和用户提示
- [ ] 分钟数据请求前的确认对话框
- [ ] 错误处理：显示API限制相关的友好错误信息

**后端开发已完成**：

- [x] API请求参数验证
- [x] 分钟数据范围检查
- [x] 错误信息返回
- [x] 自动分批处理支持

### 🎯 用户体验目标

1. **透明性**：用户清楚了解数据获取限制
2. **预防性**：界面主动防止无效请求
3. **友好性**：提供清晰的错误信息和解决建议
4. **智能性**：自动调整和优化用户选择

---

## 🐛 1min因子计算返回空数据问题修复 (2026-02-19)

### 问题描述

在前端下载1分钟数据后，因子计算（如`daily_return.1min`, `ma5.1min`）返回空DataFrame，但原始数据（OHLCV）可以正常显示。同时，Data Size显示异常小（0.02 MB），Features列表不显示原始数据字段。

### 根本原因分析

经过深入诊断，发现了**三个相关问题**：

#### 问题1：时间格式不匹配

**现象**：`D.features`调用返回空数据

**原因**：

- `factor_processor.py`传递给`D.features`的时间格式是`2026-02-11`（只有日期）
- Qlib的1min calendar从`09:30:00`开始，不是`00:00:00`
- 日期格式`2026-02-11`被Qlib解析为`2026-02-11 00:00:00`
- 查询范围`00:00:00`不在calendar范围`09:30:00-15:00:00`内，导致返回空数据

**验证**：

```python
# 只用日期格式查询1min数据 - 返回空
D.features(['sh600000'], fields=['$close'], start_time='2026-02-11', end_time='2026-02-11', freq='1min')
# Shape: (0, 1) - EMPTY

# 使用完整时间格式查询 - 返回数据
D.features(['sh600000'], fields=['$close'], start_time='2026-02-11 09:30:00', end_time='2026-02-11 15:00:00', freq='1min')
# Shape: (11, 1) - 有数据
```

#### 问题2：数据状态API只检查单一目录

**现象**：Data Size只有0.02 MB，Features列表不显示原始数据字段

**原因**：

- `data_utils.py`的`get_data_source_status_impl()`只检查`/app/qlib_data`目录
- 1min数据存储在`/app/qlib_data_1min`目录
- 导致Data Size计算不包含1min数据，Features列表也不包含1min字段

#### 问题3：不同市场交易时间不同

**现象**：美股数据使用中国市场交易时间会导致数据不完整

**原因**：

- 中国A股交易时间：09:30-15:00（含午休11:30-13:00）
- 美股交易时间：09:30-16:00 EST（无午休）
- 需要根据stock_pool自动判断市场并使用正确的交易时间

### 解决方案

#### 修复1：factor_processor.py - 自动扩展时间格式

```python
# For minute-level frequencies, expand date-only format to include full trading hours
if self.freq in ["1min", "5min", "15min", "30min", "60min"]:
    start_str = str(start_time)
    end_str = str(end_time)

    # Determine market trading hours based on region
    region = "cn"  # Default to China
    try:
        metadata_file = Path(settings.QLIB_DATA_PATH_1MIN) / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                stock_pool = metadata.get("stock_pool", "").lower()
                if stock_pool in ["sp500", "nasdaq100", "dow30"]:
                    region = "us"
    except Exception:
        pass

    # Set trading hours based on region
    if region == "us":
        market_open = "09:30:00"
        market_close = "16:00:00"  # US market closes at 16:00 EST
    else:
        market_open = "09:30:00"
        market_close = "15:00:00"  # China market closes at 15:00

    # Expand date-only format to full trading hours
    if len(start_str) == 10:  # Format: YYYY-MM-DD
        start_time = f"{start_str} {market_open}"
    if len(end_str) == 10:
        end_time = f"{end_str} {market_close}"
```

#### 修复2：data_utils.py - 检查两个数据目录

```python
def get_data_source_status_impl() -> dict:
    qlib_data_path = Path(settings.QLIB_DATA_PATH)
    qlib_data_path_1min = Path(settings.QLIB_DATA_PATH_1MIN)

    # Calculate directory size for both directories
    total_size = 0
    for data_path in [qlib_data_path, qlib_data_path_1min]:
        if data_path.exists():
            for dirpath, dirnames, filenames in os.walk(data_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)

    # Parse features from both directories
    features_dirs_to_check = []
    if (qlib_data_path_1min / "features").exists():
        features_dirs_to_check.append(qlib_data_path_1min / "features")
    if (qlib_data_path / "features").exists():
        features_dirs_to_check.append(qlib_data_path / "features")

    # ... merge features from all directories
```

#### 修复3：前端提示 - 显示不同市场的交易时间

```tsx
{
  /* Minute Data Warning */
}
{
  interval === "1m" && (
    <Alert>
      <AlertCircle className="h-4 w-4" />
      <AlertDescription>
        <strong>Minute Data Info:</strong>
        <ul className="list-disc list-inside mt-1 space-y-1">
          <li>
            Yahoo Finance only provides minute-level data for the last 30 days
          </li>
          {stockPool === "sp500" || stockPool === "nasdaq100" ? (
            <>
              <li>
                <strong>Actual trading hours (US):</strong> {startDate} 09:30:00
                to {endDate} 16:00:00 EST
              </li>
              <li>
                Data will be collected for US market trading hours (09:30-16:00
                EST)
              </li>
            </>
          ) : (
            <>
              <li>
                <strong>Actual trading hours (CN):</strong> {startDate} 09:30:00
                to {endDate} 15:00:00
              </li>
              <li>
                Data will be collected for A-share market trading hours
                (09:30-11:30, 13:00-15:00)
              </li>
            </>
          )}
        </ul>
      </AlertDescription>
    </Alert>
  );
}
```

### 修改的文件

1. **`backend/app/services/factor_processor.py`**

   - 添加分钟级频率的时间格式自动扩展
   - 根据metadata.json中的stock_pool判断市场区域
   - 使用对应市场的交易时间

2. **`backend/app/services/data_utils.py`**

   - 修改`get_data_source_status_impl()`检查两个数据目录
   - 合并两个目录的Data Size计算
   - 合并两个目录的Features列表

3. **`frontend/src/routes/_layout/data-sources.tsx`**
   - 增强分钟数据提示，显示实际交易时间
   - 根据stock_pool显示不同市场的交易时间

### 验证结果

- ✅ 1min因子计算正常返回数据
- ✅ Data Size正确显示（1.87 MB）
- ✅ Features列表显示原始数据字段（close.1min, high.1min, low.1min, open.1min, volume.1min）和因子数据
- ✅ 前端正确显示不同市场的交易时间提示

### 经验教训

1. **时间格式一致性**：对于分钟级数据，必须使用完整的datetime格式（包含时分秒），不能只用日期
2. **多目录数据管理**：当数据存储在多个目录时，状态API需要聚合所有目录的信息
3. **市场差异处理**：不同市场的交易时间不同，系统需要自动识别并处理

---

## 📋 数据和因子模块完整测试方案 (2026-02-19)

### 测试目标

验证数据收集、因子计算在不同市场、不同频率、不同更新模式下的完整功能。

### 测试矩阵

| 测试维度 | 选项                                           |
| -------- | ---------------------------------------------- |
| **市场** | A股 (csi300, csi500) / 美股 (sp500, nasdaq100) |
| **频率** | 日线 (1d) / 分钟线 (1m)                        |
| **模式** | 全量下载 / 增量更新                            |

### 详细测试用例

#### 测试组1：A股日线数据

**测试1.1：A股日线全量下载**

- Stock Pool: `csi300`
- Data Interval: `Daily (1d)`
- Start Date: `2026-02-10`
- End Date: `2026-02-11`
- 操作: 点击 "Download Data"
- 预期结果:
  - ✅ 数据下载成功
  - ✅ Features显示: close.day, high.day, low.day, open.day, volume.day + 因子
  - ✅ Data Size > 0
  - ✅ Instruments Count ≈ 300

**测试1.2：A股日线增量更新**

- 前置条件: 测试1.1完成
- 操作: 点击 "Incremental Update"
- 预期结果:
  - ✅ 增量更新成功
  - ✅ Date Range扩展到最新日期
  - ✅ 数据完整性保持

#### 测试组2：A股分钟数据

**测试2.1：A股分钟全量下载**

- Stock Pool: `csi300`
- Data Interval: `Minute (1m)`
- Start Date: 最近7天内的日期
- End Date: 最近7天内的日期
- 操作: 点击 "Download Data"
- 预期结果:
  - ✅ 提示显示: "Actual trading hours (CN): YYYY-MM-DD 09:30:00 to YYYY-MM-DD 15:00:00"
  - ✅ 数据下载成功
  - ✅ Features显示: close.1min, high.1min, low.1min, open.1min, volume.1min + 因子
  - ✅ 因子数据不为空 (daily_return.1min, ma5.1min等)

**测试2.2：A股分钟增量更新**

- 前置条件: 测试2.1完成
- 操作: 点击 "Incremental Update"
- 预期结果:
  - ✅ 增量更新成功
  - ✅ 新数据追加到现有数据

#### 测试组3：美股日线数据

**测试3.1：美股日线全量下载**

- Stock Pool: `S&P 500` 或 `NASDAQ 100`
- Data Interval: `Daily (1d)`
- Start Date: `2026-02-10`
- End Date: `2026-02-11`
- 操作: 先 "Clear Data"，然后 "Download Data"
- 预期结果:
  - ✅ 数据下载成功
  - ✅ Features显示美股数据
  - ✅ Instruments Count ≈ 500 (S&P 500) 或 ≈ 100 (NASDAQ 100)

**测试3.2：美股日线增量更新**

- 前置条件: 测试3.1完成
- 操作: 点击 "Incremental Update"
- 预期结果:
  - ✅ 增量更新成功

#### 测试组4：美股分钟数据

**测试4.1：美股分钟全量下载**

- Stock Pool: `S&P 500` 或 `NASDAQ 100`
- Data Interval: `Minute (1m)`
- Start Date: 最近7天内的日期
- End Date: 最近7天内的日期
- 操作: 先 "Clear Data"，然后 "Download Data"
- 预期结果:
  - ✅ 提示显示: "Actual trading hours (US): YYYY-MM-DD 09:30:00 to YYYY-MM-DD 16:00:00 EST"
  - ✅ 数据下载成功
  - ✅ 因子计算正常（使用美股交易时间16:00而非15:00）

**测试4.2：美股分钟增量更新**

- 前置条件: 测试4.1完成
- 操作: 点击 "Incremental Update"
- 预期结果:
  - ✅ 增量更新成功

#### 测试组5：数据清除功能

**测试5.1：清除数据**

- 操作: 点击 "Clear Data"
- 预期结果:
  - ✅ 所有数据被清除
  - ✅ 状态显示 "No data available"
  - ✅ Data Size = 0

### 测试检查清单

```
□ 测试1.1: A股日线全量下载
□ 测试1.2: A股日线增量更新
□ 测试2.1: A股分钟全量下载
□ 测试2.2: A股分钟增量更新
□ 测试3.1: 美股日线全量下载
□ 测试3.2: 美股日线增量更新
□ 测试4.1: 美股分钟全量下载
□ 测试4.2: 美股分钟增量更新
□ 测试5.1: 数据清除功能
```

### 测试执行顺序建议

1. **第一轮：A股测试**

   - 清除数据 → A股日线全量 → A股日线增量 → 清除数据 → A股分钟全量 → A股分钟增量

2. **第二轮：美股测试**
   - 清除数据 → 美股日线全量 → 美股日线增量 → 清除数据 → 美股分钟全量 → 美股分钟增量

### 监控命令

测试过程中可使用以下命令监控后端日志：

```powershell
# 实时查看后端日志
docker logs quantbot-backend-1 --tail=50 -f

# 查看最近的错误
docker logs quantbot-backend-1 2>&1 | findstr /i "error"
```

### 问题排查指南

如果测试失败，检查以下内容：

1. **数据下载失败**

   - 检查网络连接
   - 检查Yahoo Finance API限制（分钟数据仅30天内）
   - 查看后端日志中的错误信息

2. **因子计算为空**

   - 确认时间格式是否正确扩展
   - 检查calendar文件是否存在
   - 验证instruments文件是否正确

3. **增量更新失败**
   - 确认已有数据存在
   - 检查日期范围是否有效
   - 查看后端日志中的详细错误

---

## 🔧 增量更新因子计算修复 (2026-02-19)

### 📋 问题描述

增量更新后，因子数据不完整或不正确。具体表现为：

1. 因子`.bin`文件只包含1个数据点，而不是预期的10个
2. 1min数据增量更新时，检测到的缺失日期范围错误

### 🔍 根本原因分析

#### 问题1：因子计算日期范围错误

**症状**：增量更新后，MA5等因子只有1个值

**原因**：

- 因子计算使用了增量日期范围（如`2026-02-11`到`2026-02-18`），而不是完整的历史日期范围
- MA5等因子需要历史数据才能正确计算（需要前5个数据点）
- Qlib的`D.features()`在只给增量日期范围时，返回空数据或不完整数据

**解决方案**：采用**方案B（全量重算）**

- 增量更新后，重新计算所有因子数据（使用完整的calendar日期范围）
- 覆盖现有的因子`.bin`文件
- 虽然计算量稍大，但保证数据完整性和正确性

#### 问题2：Qlib缓存导致数据不更新

**症状**：增量下载后，因子计算仍使用旧的calendar数据

**原因**：

- Qlib在`init()`时会缓存calendar和其他元数据
- 增量更新后，新的calendar数据没有被Qlib感知
- 因子计算使用的是缓存的旧calendar

**解决方案**：

- 在`QlibInitService`中添加`reinitialize()`方法
- 增量更新完成后、因子计算前，强制重新初始化Qlib
- 这会清除Qlib的内存缓存，加载最新的calendar数据

```python
# qlib_init_service.py
def reinitialize(self) -> bool:
    """Force re-initialization of Qlib to refresh cached data."""
    self._initialized = False
    return self.initialize()
```

#### 问题3：1min数据增量日期范围检测错误

**症状**：1min数据增量更新时，检测到的缺失范围是`2026-02-16 to 2026-02-18`，而不是`2026-02-12`

**原因**：

- `_get_missing_date_ranges()`函数使用`D.calendar(freq="day")`获取calendar
- 对于1min数据，应该使用1min的calendar文件
- 使用错误的calendar导致日期检测不准确

**解决方案**：

- 修改`_get_missing_date_ranges()`函数，接收`interval`参数
- 根据interval选择正确的calendar文件（`day.txt`或`1min.txt`）
- 直接读取calendar文件，而不是使用`D.calendar()`（避免Qlib缓存问题）

```python
def _get_missing_date_ranges(
    requested_start: str, requested_end: str, interval: str = "1d"
) -> List[Tuple[str, str]]:
    is_minute_data = interval == "1m"
    if is_minute_data:
        calendar_file = qlib_data_path_1min / "calendars" / "1min.txt"
    else:
        calendar_file = qlib_data_path / "calendars" / "day.txt"
    # 直接读取文件，提取日期部分
```

#### 问题4：Stock Pool显示错误

**症状**：下载S&P 500数据后，前端显示Stock Pool为"csi500"

**原因**：

- `get_data_status()`函数根据instruments数量推断stock_pool
- 499个股票被错误归类为csi500（条件是`<= 600`）
- 没有区分美股和A股

**解决方案**：

- 根据股票代码格式区分市场
- A股：以`sh`或`sz`开头（如`sh600000`）
- 美股：纯字母（如`aapl`）
- 根据市场类型使用不同的推断逻辑

### 📝 Qlib使用注意事项

#### 1. Qlib缓存机制

**重要**：Qlib在`init()`时会缓存以下数据：

- Trading calendar（交易日历）
- Instruments list（股票列表）
- Feature data（特征数据）

**影响**：

- 增量更新数据后，Qlib可能仍使用缓存的旧数据
- 必须重新初始化Qlib才能加载新数据

**解决方案**：

```python
# 增量更新后，强制重新初始化Qlib
qlib_service = get_qlib_init_service()
qlib_service.reinitialize()
```

#### 2. D.calendar() vs 直接读取文件

**问题**：`D.calendar()`受Qlib缓存影响，可能返回旧数据

**建议**：

- 在需要最新calendar数据的场景，直接读取calendar文件
- 特别是在增量更新的日期范围检测中

```python
# 直接读取calendar文件
with open(calendar_file, "r") as f:
    calendar_lines = [line.strip() for line in f if line.strip()]
```

#### 3. 因子计算的历史数据依赖

**重要**：某些因子（如MA5、RSI等）需要历史数据才能正确计算

**影响**：

- 如果只计算增量日期的因子，结果可能不完整或错误
- MA5需要前5个数据点，RSI需要前14个数据点

**解决方案**：

- 方案A：计算增量因子时，传入完整的历史数据范围，但只保存增量部分
- 方案B（推荐）：增量更新后，重新计算所有因子并覆盖

#### 4. 数据频率分离

**重要**：日线数据和分钟数据必须存储在不同的目录

**目录结构**：

```
/app/qlib_data/        # 日线数据
├── calendars/day.txt
├── instruments/all.txt
└── features/

/app/qlib_data_1min/   # 分钟数据
├── calendars/1min.txt
├── instruments/all.txt
└── features/
```

**注意**：

- 检测增量日期范围时，必须使用对应频率的calendar
- 因子计算时，必须使用对应频率的数据目录

#### 5. Yahoo Finance API特性

**日期边界**：

- `end`参数是排他的，需要+1天才能包含请求的最后一天
- 分钟数据只能获取最近30天内的数据

**数据返回**：

- 可能返回请求范围外的数据（如最后一条是未来日期）
- 需要过滤异常时间戳

### ✅ 测试验证结果 (2026-02-19)

| 测试用例 | 市场       | 频率 | 类型 | 结果 | 数据变化 |
| -------- | ---------- | ---- | ---- | ---- | -------- |
| 1.1      | A股 csi300 | 1day | 全量 | ✅   | -        |
| 1.2      | A股 csi300 | 1day | 增量 | ✅   | 7→10     |
| 2.1      | A股 csi300 | 1min | 全量 | ✅   | -        |
| 2.2      | A股 csi300 | 1min | 增量 | ✅   | 328→991  |
| 3.1      | 美股 sp500 | 1day | 全量 | ✅   | -        |
| 3.2      | 美股 sp500 | 1day | 增量 | ✅   | 7→12     |
| 4.1      | 美股 sp500 | 1min | 全量 | ✅   | -        |
| 4.2      | 美股 sp500 | 1min | 增量 | ✅   | 390→1951 |

**数据准确性验证**：

- Close价格与Yahoo Finance API完全一致
- MA5因子计算正确（误差在浮点精度范围内）

### 🔄 修改的文件

1. **`backend/app/services/qlib_init_service.py`**

   - 添加`reinitialize()`方法，强制重新初始化Qlib

2. **`backend/app/services/data_collectors/pipeline/service.py`**

   - 增量更新后调用`qlib_service.reinitialize()`
   - 修改`_get_missing_date_ranges()`接收`interval`参数
   - 根据interval使用正确的calendar文件

3. **`backend/app/services/data_utils.py`**

   - 修改`get_data_status()`的stock_pool推断逻辑
   - 根据股票代码格式区分美股和A股

4. **`backend/app/services/factor_pipeline.py`**

   - 确保因子计算始终使用`overwrite=True`

5. **`backend/app/services/factor_storage.py`**
   - 移除复杂的合并逻辑，简化为直接覆盖

---

## 🚀 模型训练 Workflow 设计 (2026-02-19)

### 📋 概述

基于 Qlib 的 `qrun` 命令研究，设计并实现模型训练工作流。该工作流参考 `qrun` 的核心实现（`qlib/model/trainer.py` 的 `_exe_task` 函数），但集成到 Web 服务中，使用我们自己的因子引擎（`CustomFactorHandler`）。

### 🎯 设计目标

1. **使用我们的因子引擎** - `CustomFactorHandler` 作为 DataHandler
2. **参考 qrun 实现** - 保持与 Qlib 标准工作流兼容
3. **配置驱动** - 通过 YAML/JSON 配置文件定义训练任务
4. **产出模型文件** - 训练好的模型保存到文件系统
5. **为未来扩展做准备** - 模拟盘 Workflow、回测 Workflow

### 🔍 qrun 核心机制分析

#### qrun 的执行流程

```
qrun configuration.yaml
    ↓
1. qlib.init() - 初始化 Qlib
2. task_train() - 执行训练任务
    ↓
_exe_task():
    model = init_instance_by_config(task_config["model"])
    dataset = init_instance_by_config(task_config["dataset"])
    model.fit(dataset)
    R.save_objects(model=model, dataset=dataset)
    for record in records:
        record.generate()  # SignalRecord, PortAnaRecord 等
```

#### qrun 配置文件结构

```yaml
qlib_init:
  provider_uri: "~/.qlib/qlib_data/cn_data"
  region: cn

task:
  model: { ... }
  dataset: { ... }
  record: [...]
```

### 📐 架构设计

#### 数据频率与 provider_uri

**重要**：日线数据和分钟数据使用不同的目录：

| 数据频率      | provider_uri          | 说明         |
| ------------- | --------------------- | ------------ |
| 日线 (1d)     | `/app/qlib_data`      | 日线数据目录 |
| 分钟线 (1min) | `/app/qlib_data_1min` | 分钟数据目录 |

**解决方案**：在配置中通过 `freq` 参数自动选择正确的 `provider_uri`，而不是维护两套配置文件。

```python
def get_provider_uri(freq: str) -> str:
    if freq == "1min":
        return "/app/qlib_data_1min"
    else:
        return "/app/qlib_data"
```

#### 训练工作流架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Training Workflow                         │
├─────────────────────────────────────────────────────────────┤
│  1. 数据检查                                                 │
│     - 检查 provider_uri 目录是否存在                         │
│     - 检查 calendar、instruments、features 是否完整          │
│     - 如果数据不存在，返回错误提示用户先下载数据              │
├─────────────────────────────────────────────────────────────┤
│  2. Qlib 初始化                                              │
│     - 根据 freq 选择正确的 provider_uri                      │
│     - 设置 region (cn/us)                                    │
├─────────────────────────────────────────────────────────────┤
│  3. Dataset 构建                                             │
│     - 使用 CustomFactorHandler 加载因子                      │
│     - 从数据库加载用户定义的因子表达式                        │
│     - 可选：启用 Alpha158 因子                               │
├─────────────────────────────────────────────────────────────┤
│  4. 模型训练                                                 │
│     - 初始化模型 (LGBModel, XGBoost, etc.)                   │
│     - 执行 model.fit(dataset)                                │
├─────────────────────────────────────────────────────────────┤
│  5. 结果记录                                                 │
│     - SignalRecord: 生成预测结果 (pred.pkl)                  │
│     - PortAnaRecord: 回测分析 (可选)                         │
├─────────────────────────────────────────────────────────────┤
│  6. 模型保存                                                 │
│     - 保存模型到文件系统 (/app/models/)                      │
│     - 保存到 MLflow 实验追踪                                 │
└─────────────────────────────────────────────────────────────┘
```

### 📝 配置文件格式

#### 完整配置示例

```yaml
# training_config.yaml
qlib_init:
  provider_uri: "/app/qlib_data" # 自动根据 freq 调整
  region: cn

market: &market csi300
benchmark: &benchmark SH000300

data_handler_config: &data_handler_config
  start_time: 2026-02-02
  end_time: 2026-02-18
  fit_start_time: 2026-02-02
  fit_end_time: 2026-02-10
  instruments: *market
  freq: day
  enable_alpha158: false # 是否包含 Alpha158 因子

task:
  model:
    class: LGBModel
    module_path: qlib.contrib.model.gbdt
    kwargs:
      loss: mse
      colsample_bytree: 0.8879
      learning_rate: 0.05
      subsample: 0.8789
      lambda_l1: 205.6999
      lambda_l2: 580.9768
      max_depth: 8
      num_leaves: 210
      num_threads: 4

  dataset:
    class: DatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: CustomFactorHandler
        module_path: app.services.custom_factor_handler
        kwargs: *data_handler_config
      segments:
        train: [2026-02-02, 2026-02-10]
        valid: [2026-02-11, 2026-02-13]
        test: [2026-02-14, 2026-02-18]

  record:
    - class: SignalRecord
      module_path: qlib.workflow.record_temp
      kwargs: {}
    - class: PortAnaRecord
      module_path: qlib.workflow.record_temp
      kwargs:
        config:
          strategy:
            class: TopkDropoutStrategy
            module_path: qlib.contrib.strategy.strategy
            kwargs:
              topk: 50
              n_drop: 5
              signal: <PRED>
          backtest:
            start_time: 2026-02-14
            end_time: 2026-02-18
            account: 100000000
            benchmark: *benchmark
            exchange_kwargs:
              limit_threshold: 0.095
              deal_price: close
              open_cost: 0.0005
              close_cost: 0.0015
              min_cost: 5
```

### 🔧 实现计划

#### 阶段 1：增强 QlibWorkflowService

**文件**: `backend/app/services/qlib_workflow_service.py`

**修改内容**:

1. 添加数据存在性检查方法
2. 添加 Record 执行逻辑（参考 qrun 的 `_exe_task`）
3. 添加模型保存到文件系统功能
4. 支持从 YAML 配置文件加载

```python
class QlibWorkflowService:
    def check_data_exists(self, freq: str = "day") -> Dict[str, Any]:
        """检查数据是否存在"""
        pass

    def execute_training_workflow(self, config: Dict, experiment_name: str) -> Dict:
        """执行训练工作流（增强版）"""
        # 1. 检查数据
        # 2. 初始化 Qlib
        # 3. 构建 Dataset
        # 4. 训练模型
        # 5. 执行 Records
        # 6. 保存模型
        pass

    def save_model_to_filesystem(self, model, model_name: str) -> str:
        """保存模型到文件系统"""
        pass
```

#### 阶段 2：创建训练 API

**文件**: `backend/app/api/routes/training.py`

**端点**:

- `POST /api/v1/training/start` - 启动训练任务
- `GET /api/v1/training/{task_id}/status` - 获取训练状态
- `GET /api/v1/training/{task_id}/results` - 获取训练结果
- `GET /api/v1/training/models` - 列出已训练的模型

#### 阶段 3：创建前端训练页面

**页面功能**:

1. 训练配置表单（选择模型、参数、日期范围）
2. 数据状态检查（显示是否有可用数据）
3. 训练进度展示
4. 结果分析页面（预测结果、回测指标）

### 📊 产出物

| 产出物   | 格式            | 存储位置                       | 说明               |
| -------- | --------------- | ------------------------------ | ------------------ |
| 训练模型 | `.pkl`          | `/app/models/{model_name}.pkl` | 可用于推理         |
| 预测结果 | `pred.pkl`      | MLflow artifacts               | SignalRecord 生成  |
| 标签数据 | `label.pkl`     | MLflow artifacts               | SignalRecord 生成  |
| 回测报告 | `report.pkl`    | MLflow artifacts               | PortAnaRecord 生成 |
| 持仓记录 | `positions.pkl` | MLflow artifacts               | PortAnaRecord 生成 |

### 🔮 未来扩展

本训练 Workflow 设计为可扩展架构，未来将支持：

1. **模拟盘 Workflow** - 使用训练好的模型进行模拟交易
2. **回测 Workflow** - 独立的回测分析功能
3. **模型管理** - 模型版本控制、比较、部署

### 📁 相关文件

| 文件                                                   | 说明                    |
| ------------------------------------------------------ | ----------------------- |
| `backend/app/services/qlib_workflow_service.py`        | 训练工作流核心服务      |
| `backend/app/services/custom_factor_handler.py`        | 自定义因子引擎          |
| `backend/app/api/routes/training.py`                   | 训练 API 路由（待创建） |
| `backend/app/api/routes/qlib_workflow.py`              | 现有 Qlib 工作流路由    |
| `backend/tests/services/test_qlib_workflow_service.py` | 测试脚本                |

---

## ✅ 模型训练 Workflow 完成 (2026-02-19)

### 📋 完成概述

成功完成了基于 Qlib 的模型训练工作流，实现了从预计算的 bin 文件加载数据、训练 LightGBM 模型、保存模型和生成预测结果的完整流程。

### 🎯 核心成就

#### 1. CustomFactorHandler 完善 ✅

**关键修复**：

- 修复 `setup_data()` 方法，正确调用父类 `DataHandlerLP.setup_data()` 初始化 `_learn` 和 `_infer` 属性
- 修复 `process_type` 默认值，使用 `DataHandlerLP.PTYPE_A`（与 Alpha158 一致）
- 移除自定义 `fetch()` 方法，继承父类实现避免参数冲突
- 修复 `config()` 方法，只引用实际存在的属性
- 保存 `fit_start_time`、`fit_end_time` 等属性供序列化使用

**数据加载验证**：

```
Found 4 pre-computed factors: ['hl_mid_price', 'daily_return', 'ma5', 'return_1d']
Total feature expressions: 9
Added 9 pre-computed factors from bin files
Using pre-computed label: ['$return_1d']
```

#### 2. 训练配置文件 ✅

**文件**: `backend/app/config/training_config.yaml`

**关键配置**：

- `market: all` - 使用 `instruments/all.txt` 文件
- `freq: day` - 日线数据频率
- `enable_alpha158: false` - 只使用预计算因子
- 完整的 LGBModel 超参数配置
- 训练/验证/测试集时间段划分

#### 3. 训练结果验证 ✅

**训练指标**：

```
[100]   train's l2: 0.80908     valid's l2: 0.86486
```

**输出结果**：

```json
{
  "status": "success",
  "model_path": "/app/models/LGBModel_20260219_083431.pkl",
  "test_predictions_count": 481,
  "model_saved": true,
  "timings": {
    "total": 5.505871534347534
  }
}
```

**预测样本**：

```
                          score
datetime   instrument
2026-02-09 SH600000   -0.011018
           SH600010    0.178395
           SH600011   -0.091300
```

### 🔧 关键技术点

#### 数据从 bin 文件加载（非计算）

**证据**：

1. 使用 `$` 前缀表达式（如 `$open`, `$ma5`, `$return_1d`）表示直接从 bin 文件读取
2. 日志显示 "Added 9 pre-computed factors from bin files"
3. 没有计算表达式（如 `Ref($close, -1)/$close - 1`）

#### DataHandlerLP 继承机制

**关键理解**：

- `DataHandlerLP.setup_data()` 负责调用 `fit()` 和 `process_data()`
- 这些方法设置 `_learn` 和 `_infer` DataFrame
- 子类必须调用 `super().setup_data()` 才能正确初始化

### 📊 测试验证矩阵

| 验证项              | 状态 | 说明                            |
| ------------------- | ---- | ------------------------------- |
| 数据从 bin 文件加载 | ✅   | 使用 `$` 前缀表达式             |
| OHLCV 数据正确      | ✅   | 与 Yahoo Finance 一致           |
| 因子数据正确        | ✅   | MA5、daily_return、hl_mid_price |
| Label 数据正确      | ✅   | return_1d 计算正确              |
| 模型训练成功        | ✅   | LightGBM 训练完成               |
| 模型保存成功        | ✅   | 保存到 `/app/models/`           |

### 修改的文件

| 文件                                            | 修改内容                                 |
| ----------------------------------------------- | ---------------------------------------- |
| `backend/app/services/custom_factor_handler.py` | 修复 setup_data、process_type、config 等 |
| `backend/app/config/training_config.yaml`       | 更新 market、freq、segments 配置         |
| `backend/app/services/qlib_workflow_service.py` | 移除错误的 provider_uri 参数             |

---

## 回测 Workflow 设计方案 (2026-02-19)

### 概述

基于 Qlib 的回测系统设计回测工作流，采用 **方案 A + 方案 B 结合** 的架构，既支持训练时自动回测，也支持独立回测 API（为模拟盘做准备）。

### 设计目标

1. **训练时自动回测**：训练完成后立即验证模型效果
2. **独立回测 API**：支持加载已有模型进行回测，为模拟盘提供基础
3. **策略可配置化**：只需修改 YAML 配置即可切换策略，不需要改代码
4. **复用 Qlib 官方实现**：使用 `PortAnaRecord` 和 `backtest()` 函数

### Qlib 回测机制分析

#### 核心组件

| 组件              | 说明                              | 文件位置                       |
| ----------------- | --------------------------------- | ------------------------------ |
| **backtest()**    | 回测主入口函数                    | `qlib/backtest/__init__.py`    |
| **PortAnaRecord** | 回测记录模板，集成到训练 workflow | `qlib/workflow/record_temp.py` |
| **BaseStrategy**  | 策略基类                          | `qlib/strategy/base.py`        |
| **BaseExecutor**  | 执行器基类                        | `qlib/backtest/executor.py`    |
| **Exchange**      | 交易所模拟（交易成本、涨跌停等）  | `qlib/backtest/exchange.py`    |

#### 回测流程

```
加载模型 → 生成预测 → 策略决策 → 模拟执行 → 生成报告
    ↓           ↓           ↓           ↓           ↓
model.pkl   pred.pkl   Strategy   Executor   report.pkl
```

### 架构设计

#### 方案 A：训练时集成回测（PortAnaRecord）

**原理**：在训练配置中添加 `PortAnaRecord`，训练完成后自动执行回测。

**配置示例**：

```yaml
record:
  - class: SignalRecord
    module_path: qlib.workflow.record_temp
    kwargs: {}
  - class: PortAnaRecord
    module_path: qlib.workflow.record_temp
    kwargs:
      config:
        strategy:
          class: TopkDropoutStrategy
          module_path: qlib.contrib.strategy
          kwargs:
            signal: <PRED>
            topk: 50
            n_drop: 5
        backtest:
          start_time: 2026-02-09
          end_time: 2026-02-10
          account: 100000000
          benchmark: SH000300
          exchange_kwargs:
            limit_threshold: 0.095
            deal_price: close
            open_cost: 0.0005
            close_cost: 0.0015
            min_cost: 5
```

**产出物**：

- `report_normal_1day.pkl` - 每日收益报告
- `positions_normal_1day.pkl` - 每日持仓记录
- `port_analysis.pkl` - 风险分析（夏普比率、最大回撤等）

#### 方案 B：独立回测 API

**用途**：支持模拟盘场景，每天用最新数据执行回测。

**API 设计**：

```python
POST /api/v1/backtest/run
{
  "model_path": "/app/models/LGBModel_xxx.pkl",
  "start_time": "2026-02-09",
  "end_time": "2026-02-10",
  "strategy": {
    "class": "TopkDropoutStrategy",
    "kwargs": {"topk": 50, "n_drop": 5}
  }
}
```

**实现方式**：

```python
from qlib.backtest import backtest

# 1. 加载模型
model = load_model(model_path)

# 2. 生成预测
pred = model.predict(dataset)

# 3. 执行回测
portfolio_metric, indicator = backtest(
    start_time=start_time,
    end_time=end_time,
    strategy=strategy_config,
    executor=executor_config,
    benchmark=benchmark,
    account=account,
    exchange_kwargs=exchange_kwargs
)
```

### 策略选择

#### 当前策略：TopkDropoutStrategy

**参数说明**：

- `topk: 50` - 持有 50 只股票
- `n_drop: 5` - 每天换仓 5 只（换手率 10%）
- `method_sell: bottom` - 卖出预测分数最低的
- `method_buy: top` - 买入预测分数最高的

**适用场景**：简单的多头策略，适合验证模型预测效果。

#### 未来策略：EnhancedIndexingStrategy

**特点**：指数增强策略，目标是跑赢基准指数同时控制跟踪误差。

**额外要求**：需要准备风险模型数据

```
/app/riskmodel/
├── 20260209/
│   ├── factor_exp.pkl    # 因子暴露
│   ├── factor_cov.pkl    # 因子协方差
│   ├── specific_risk.pkl # 特异性风险
│   └── blacklist.pkl     # 黑名单（可选）
```

**切换方式**：只需修改 YAML 配置

```yaml
strategy:
  class: EnhancedIndexingStrategy # 改这里
  module_path: qlib.contrib.strategy
  kwargs:
    signal: <PRED>
    riskmodel_root: /app/riskmodel # 添加风险模型路径
    market: csi300
```

### 策略可配置化设计

**关键原则**：策略配置完全通过 YAML 传递，代码中使用 `init_instance_by_config`。

```python
from qlib.utils import init_instance_by_config

# 代码中不硬编码策略类型
strategy = init_instance_by_config(config["strategy"])
```

**这样设计的好处**：

1. 切换策略只需修改 YAML 文件
2. 支持任何符合 Qlib 接口的自定义策略
3. 便于 A/B 测试不同策略

### 回测指标

| 指标         | 说明                       |
| ------------ | -------------------------- |
| **累计收益** | 回测期间的总收益率         |
| **年化收益** | 年化后的收益率             |
| **夏普比率** | 风险调整后收益（越高越好） |
| **最大回撤** | 最大亏损幅度               |
| **超额收益** | 相对基准的超额收益         |
| **信息比率** | 超额收益/跟踪误差          |
| **换手率**   | 每日换仓比例               |

### 实施计划

#### 阶段 1：方案 A - 训练时集成回测 ⚠️ 暂缓

- PortAnaRecord 存在 `index out of bounds` 边界问题
- 已实现但暂时禁用，等待 Qlib 修复或深入调查

#### 阶段 2：方案 B - 独立回测 API ✅ 已完成

1. ✅ 在 `QlibWorkflowService` 中实现 `execute_backtest()` 方法
2. ✅ 创建 `backtest_config.yaml` 配置文件
3. ✅ 创建 `/api/v1/backtest/run` API 端点
4. ✅ 创建 `/api/v1/backtest/status` API 端点
5. ✅ 测试独立回测功能（36 交易日，净收益 10.4%）

#### 阶段 3：模拟盘准备

模拟盘功能已具备基础：

- ✅ 增量数据下载
- ✅ 模型训练和预测
- ✅ 独立回测 API

待实现：

- [ ] 创建模拟盘调度服务（每日自动执行）
- [ ] 持仓跟踪和管理
- [ ] 交易信号推送

### 相关文件

| 文件                                            | 说明                  |
| ----------------------------------------------- | --------------------- |
| `backend/app/config/training_config.yaml`       | 训练配置（动态 freq） |
| `backend/app/config/backtest_config.yaml`       | 回测配置 ✅           |
| `backend/app/services/qlib_workflow_service.py` | 训练 + 回测服务 ✅    |
| `backend/app/api/routes/training.py`            | 训练 API 路由 ✅      |
| `backend/app/api/routes/backtest.py`            | 回测 API 路由 ✅      |

---

## 🎉 核心功能完成里程碑 (2026-02-19)

### 📊 已完成功能总览

| 功能模块         | 状态 | 说明                                           |
| ---------------- | ---- | ---------------------------------------------- |
| **数据全量下载** | ✅   | Yahoo Finance 数据源，支持 CN/US 市场          |
| **数据增量下载** | ✅   | 智能检测缺失日期，只下载增量数据               |
| **因子计算**     | ✅   | CustomFactorHandler，支持自定义因子和 Alpha158 |
| **模型训练**     | ✅   | LGBModel，动态时间配置，SignalRecord           |
| **回测**         | ✅   | 独立回测 API，TopkDropoutStrategy              |

### 🔧 技术亮点

#### 1. 动态配置系统

- **freq 动态检测**：自动检测数据目录，确定使用 day 或 1min 频率
- **时间范围动态计算**：从 Qlib calendar 获取实际数据范围
- **70/15/15 自动分割**：train/valid/test 数据集自动划分

#### 2. API 路由重构

按领域分离为独立 router：

| 路由前缀              | 文件             | 功能       |
| --------------------- | ---------------- | ---------- |
| `/api/v1/data-source` | `data_source.py` | 数据源管理 |
| `/api/v1/factors`     | `factors.py`     | 因子管理   |
| `/api/v1/training`    | `training.py`    | 模型训练   |
| `/api/v1/backtest`    | `backtest.py`    | 回测       |

#### 3. 独立回测 API (Plan B)

绕过 PortAnaRecord 的 index 错误，直接使用 `backtest_daily`：

```python
# 使用 Qlib 的 backtest_daily 函数
report_df, positions = backtest_daily(
    start_time=start_time,
    end_time=end_time,
    strategy=TopkDropoutStrategy(signal=pred, topk=50, n_drop=5),
    account=100000000,
    benchmark="SH000300",
    exchange_kwargs={...}
)
```

#### 4. 配置文件结构

**training_config.yaml**：

- 模型配置（LGBModel 参数）
- 数据集配置（CustomFactorHandler）
- Record 配置（SignalRecord）
- 无硬编码时间和 freq

**backtest_config.yaml**：

- 策略配置（TopkDropoutStrategy）
- 回测参数（account, benchmark, exchange_kwargs）
- 无硬编码 freq

### 📈 回测结果示例

```json
{
  "status": "success",
  "start_time": "2025-12-18",
  "end_time": "2026-02-09",
  "trading_days": 36,
  "total_return": 0.1101,
  "total_cost": 0.0058,
  "net_return": 0.1043,
  "final_account": 110760196.3
}
```

### ✅ 已完成的前端页面

#### 1. Data Sources 页面 (`/data-sources`)

**功能**：

- 展示当前数据状态（股票数量、日期范围、数据频率）
- 下载数据（全量下载）
- 增量更新数据
- 导出数据为 CSV
- 清除数据

**API 调用**：
| API | 用途 |
|-----|------|
| `GET /api/v1/data-source/status` | 获取数据状态 |
| `POST /api/v1/data-source/download` | 下载数据 |
| `POST /api/v1/data-source/export-data` | 导出 CSV |
| `DELETE /api/v1/data-source/clear` | 清除数据 |

**布局修复**：
使用以下结构防止页面滚动到导航栏：

```tsx
<div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
  <div className="h-full overflow-y-auto p-6 md:p-8">{/* 页面内容 */}</div>
</div>
```

#### 2. Training 页面 (`/training`)

**功能**：

- 展示模型配置（从 `training_config.yaml` 读取）
  - 模型类型（LGBModel）
  - 超参数（learning_rate, max_depth, num_leaves 等）
- 展示已训练的模型列表
  - 模型文件名、大小、创建时间
- 展示训练状态（Idle / Training / Completed / Failed）
- 启动训练按钮

**API 调用**：
| API | 用途 |
|-----|------|
| `GET /api/v1/training/config` | 获取训练配置 |
| `GET /api/v1/training/models` | 获取已训练模型列表 |
| `POST /api/v1/training/start` | 启动训练 |

**训练流程验证**：

```
Training until validation scores don't improve for 50 rounds
[20]       train's l2: 0.99534     valid's l2: 0.996307
[40]       train's l2: 0.994794    valid's l2: 0.996388
Early stopping, best iteration is:
[20]       train's l2: 0.99534     valid's l2: 0.996307
```

**设计原则**：

- 用户不能修改模型配置（配置在 YAML 文件中管理）
- 页面只展示配置信息，唯一操作是"Start Training"按钮
- 训练完成后自动刷新模型列表

#### 3. Backtest 页面 (`/backtest`)

**功能**：

- 展示策略配置（从 `backtest_config.yaml` 读取）
  - 策略类型（TopkDropoutStrategy）
  - 策略参数（topk, n_drop, account, benchmark）
  - 交易成本参数（open_cost, close_cost, min_cost）
- 展示回测状态（是否有预测可用、最新模型）
- 展示回测结果
  - 交易天数、总收益率、净收益率
  - 交易成本、最终账户价值
- Run Backtest 按钮

**API 调用**：
| API | 用途 |
|-----|------|
| `GET /api/v1/backtest/config` | 获取回测配置 |
| `GET /api/v1/backtest/status` | 获取回测状态 |
| `GET /api/v1/backtest/latest-result` | 获取最近回测结果（持久化） |
| `POST /api/v1/backtest/run` | 执行回测 |

**回测流程验证**：

```
INFO:app.services.qlib_workflow_service:Found latest predictions: /app/mlruns/.../pred.pkl
INFO:app.services.qlib_workflow_service:Loaded predictions: 11025 records
INFO:app.services.qlib_workflow_service:Backtest period: 2025-12-18 to 2026-02-09
backtest loop: 100%|██████████| 36/36 [00:00<00:00, 72.77it/s]
INFO:app.services.qlib_workflow_service:Backtest completed: 36 trading days, return=0.1101
```

**设计原则**：

- 用户不能修改策略配置（配置在 YAML 文件中管理）
- 页面只展示配置信息，唯一操作是"Run Backtest"按钮
- 回测结果持久化到后端缓存，页面切换后不会丢失

### 🚀 下一阶段工作计划

#### Phase 1：前端开发 (2-3 周)

按以下顺序开发：

1. **因子管理和因子分析页面**

   - 因子列表展示（Features vs Labels）
   - 因子创建和编辑
   - 因子分析和可视化

2. ~~**数据页面**~~ ✅ 已完成

3. ~~**训练和分析页面**~~ ✅ 已完成

4. ~~**回测和指标分析页面**~~ ✅ 已完成

**注意**：不需要独立的模型管理页面。系统只使用最新训练的模型进行回测。如果配置文件中更换了模型类型，需要删除旧模型后重新训练。

#### Phase 2：模拟盘功能 (1-2 周)

1. **调度服务**

   - 每日自动执行数据更新
   - 每日自动执行预测和回测

2. **持仓管理**

   - 当前持仓展示
   - 历史持仓记录

3. **交易信号生成**

   - 每日买卖信号生成
   - 信号格式化输出

4. **信号推送**
   - 微信推送（Server酱/企业微信）
   - 邮件推送
   - 可配置推送渠道

#### Phase 3：扩展功能 (持续)

1. **数据源扩展**

   - Tushare（中国 A 股专业数据）
   - AKShare（开源金融数据）
   - 本地 CSV 导入

2. **策略扩展**

   - EnhancedIndexingStrategy（指数增强）
   - 自定义策略支持
   - 策略参数可配置

3. **模型扩展**
   - XGBoost
   - CatBoost
   - 深度学习模型（LSTM/Transformer）

### 📝 关于模拟盘

**问题**：回测和模拟盘有什么区别？

**回答**：

- **回测**：使用历史数据验证策略表现
- **模拟盘**：使用实时数据进行模拟交易，但不实际下单

**当前状态**：

- 回测功能已完成，可以作为模拟盘的基础
- 模拟盘需要额外的调度服务来每日自动执行
- 核心逻辑（预测 + 回测）已经就绪

---

## 🐛 常见问题与经验教训

### 问题 1：股票代码大小写不匹配（重复出现多次）

**问题描述**：

在 Qlib 数据目录中，`instruments/all.txt` 文件中的股票代码是**大写**（如 `SH600000`），但 `features/` 目录下的子目录是**小写**（如 `sh600000`）。这导致路径匹配失败，无法读取数据。

**错误表现**：

```
{"detail":"No data could be read from bin files"}
```

或者 Qlib API 返回空数据。

**根本原因**：

- Yahoo Finance 数据源返回的股票代码格式与 Qlib 内部存储格式不一致
- 数据写入时使用了一种大小写，读取时使用了另一种大小写
- Linux 文件系统区分大小写，Windows 不区分，导致问题在不同环境表现不同

**解决方案**：

```python
# 读取 instruments 时统一转换为小写
with open(instruments_file, "r") as f:
    instruments = [line.strip().split("\t")[0].lower() for line in f if line.strip()]
```

**预防措施**：

1. **数据写入时统一格式**：在数据下载和存储时，统一将股票代码转换为小写
2. **读取时做防御性处理**：读取数据时始终转换为小写后再匹配
3. **添加日志**：在关键路径添加日志，记录实际使用的路径和文件名
4. **单元测试**：添加测试用例验证大小写处理

---

### 问题 2：Qlib 初始化状态不一致

**问题描述**：

在 Docker 容器热重载后，Qlib 的 `provider_uri` 配置可能不正确，导致 `D.calendar()` 和 `D.features()` 等 API 调用失败。

**错误表现**：

```
ValueError: can't find a freq from [] that can resample to day!
data_path={'__DEFAULT_FREQ': PosixPath('/app')}  # 应该是 /app/qlib_data
```

**根本原因**：

- `QlibInitService` 使用类级别的 `_initialized` 标志
- 热重载后 Python 进程重启，`_initialized` 被重置为 `False`
- 但 Qlib 内部状态可能不一致，或者被其他代码错误初始化

**解决方案**：

对于数据导出功能，**完全绕过 Qlib API**，直接读取二进制文件：

```python
import struct

# 直接读取 bin 文件
with open(bin_file, "rb") as f:
    data = f.read()
num_values = len(data) // 4
values = struct.unpack(f"{num_values}f", data)
```

**为什么选择直接读取**：

| Qlib API 方式                 | 直接读取方式       |
| ----------------------------- | ------------------ |
| 需要正确初始化 `provider_uri` | 不需要 Qlib 初始化 |
| 热重载后状态不一致            | 每次独立读取       |
| 依赖 Qlib 内部缓存            | 直接读取文件系统   |
| 复杂的多频率配置              | 简单的文件操作     |

---

### 问题 3：前端 API URL 路径问题

**问题描述**：

前端使用相对路径 `/api/v1/...` 发送请求，但在 Docker 环境中，前端容器和后端容器是分离的，相对路径会发送到前端容器自己。

**错误表现**：

```
Failed to load resource: the server responded with a status of 404 (Not Found)
api/v1/data-source/export-data:1
```

**根本原因**：

- 生成的 API client 使用 `OpenAPI.BASE = import.meta.env.VITE_API_URL`
- 但手动编写的 `fetch` 调用使用了相对路径
- 前端容器（nginx）没有配置代理到后端

**解决方案**：

```typescript
// 使用环境变量构建完整 URL
const apiUrl = import.meta.env.VITE_API_URL || "";
const response = await fetch(`${apiUrl}/api/v1/data-source/export-data`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  },
});
```

**预防措施**：

1. **统一使用生成的 API client**：尽量使用 OpenAPI 生成的 client，而不是手动 fetch
2. **如果必须手动 fetch**：始终使用 `import.meta.env.VITE_API_URL` 作为基础 URL
3. **检查网络请求**：开发时使用浏览器开发者工具检查实际发送的 URL

---

### 问题 4：Qlib 二进制文件格式

**知识点**：

Qlib 使用 `float32` 格式存储二进制数据：

```python
import struct

# 读取 bin 文件
with open("close.day.bin", "rb") as f:
    data = f.read()

# 解析为 float32 数组
num_values = len(data) // 4  # float32 = 4 bytes
values = struct.unpack(f"{num_values}f", data)
```

**文件结构**：

```
qlib_data/
├── calendars/
│   └── day.txt           # 交易日历，每行一个日期
├── instruments/
│   └── all.txt           # 股票列表，格式：代码\t开始日期\t结束日期
└── features/
    └── sh600000/         # 每个股票一个目录
        ├── close.day.bin # 收盘价
        ├── open.day.bin  # 开盘价
        ├── high.day.bin  # 最高价
        ├── low.day.bin   # 最低价
        └── volume.day.bin # 成交量
```

---

### 调试技巧总结

1. **使用 curl 直接测试后端 API**：

   ```bash
   curl -X POST "http://localhost:8000/api/v1/data-source/export-data"
   ```

2. **检查 Docker 容器内的文件结构**：

   ```bash
   docker compose exec backend ls -la /app/qlib_data/features/
   docker compose exec backend cat /app/qlib_data/instruments/all.txt | head -5
   ```

3. **查看后端日志**：

   ```bash
   docker compose logs backend --tail=100
   ```

4. **添加详细日志**：在关键路径添加 `logger.info()` 记录变量值

5. **浏览器开发者工具**：检查 Network 标签页，查看实际发送的请求 URL 和响应

---

## 📝 更新日志

### 2026-02-20: 模型管理优化

**改动内容**：

- 在 `_save_model_to_filesystem` 方法中添加删除旧模型的逻辑
- 训练新模型前，自动删除 `MODELS_DIR` 目录中所有现有的 `.pkl` 文件
- 确保系统中只保留最新训练的模型

**修改文件**：

- `backend/app/services/qlib_workflow_service.py`

**代码位置**：第 482-488 行

```python
# Delete all existing model files before saving new one
for old_model in MODELS_DIR.glob("*.pkl"):
    try:
        old_model.unlink()
        self.logger.info(f"Deleted old model: {old_model}")
    except Exception as e:
        self.logger.warning(f"Failed to delete old model {old_model}: {e}")
```

**设计理由**：

- 简化模型管理，避免模型文件堆积
- 系统设计为单模型架构，只需保留最新模型用于回测

### 2026-02-20: 回测逻辑重构

**问题**：

- 原回测逻辑使用训练时生成的 `pred.pkl` 文件
- 无法在最新数据上回测，必须重新训练才能更新预测
- 不符合实际量化投资的使用场景

**正确的回测流程**：

1. 加载最新的模型文件
2. 加载 bin 文件中的全部特征数据（不包括 label）
3. 用模型对全部数据做推理，生成预测
4. 用预测结果执行回测

**修改文件**：

- `backend/app/api/routes/backtest.py`
- `backend/app/services/qlib_workflow_service.py`

**主要改动**：

1. **`GET /backtest/status`**：就绪条件从检查 `pred.pkl` 改为检查模型是否存在
2. **`POST /backtest/run`**：使用模型推理而不是加载 `pred.pkl`
3. **`BacktestResponse`**：新增 `data_start_time` 和 `data_end_time` 字段，表示数据范围

**新的回测流程**：

```python
# Step 1: Load the latest model
model = pickle.load(open(latest_model_path, "rb"))

# Step 2: Get data time range from bin files
time_range = self._get_data_time_range()

# Step 3: Create dataset for inference (features only, no labels)
handler = CustomFactorHandler(instruments="all", start_time=..., end_time=...)
dataset = DatasetH(handler=handler, segments={"backtest": [start, end]})

# Step 4: Generate predictions using the model
pred = model.predict(dataset, segment="backtest")

# Step 5: Execute backtest
strategy = TopkDropoutStrategy(signal=pred, topk=topk, n_drop=n_drop)
report_df, positions = backtest_daily(strategy=strategy, ...)
```

**设计理由**：

- 数据增量更新后，无需重新训练即可回测
- 回测使用全部数据，更接近实际使用场景
- 模型复用，提高效率

### 2026-02-20: 回测支持任意数据频率

**问题**：

- 原回测逻辑使用 `backtest_daily`，只支持日频数据
- 系统支持下载分钟数据、训练分钟模型，但回测不支持分钟频率
- 用户下载分钟数据后，回测会使用错误的频率

**解决方案**：

使用 Qlib 的通用 `backtest` 函数替代 `backtest_daily`，根据数据频率动态配置回测参数。

**修改文件**：

- `backend/app/services/qlib_workflow_service.py`

**主要改动**：

```python
# Use general backtest function that supports any frequency
from qlib.backtest import backtest as backtest_func
from qlib.backtest.executor import SimulatorExecutor
from qlib.utils.time import Freq

# Create executor with correct frequency
executor_config = {
    "time_per_step": freq,  # "day" or "1min"
    "generate_portfolio_metrics": True,
}
executor = SimulatorExecutor(**executor_config)

# Update exchange_kwargs with correct frequency
_exchange_kwargs = {
    "freq": freq,
    "limit_threshold": ...,
    "deal_price": ...,
    ...
}

# Execute backtest
portfolio_metric_dict, indicator_dict = backtest_func(
    start_time=start_time,
    end_time=end_time,
    strategy=strategy,
    executor=executor,
    account=account,
    benchmark=benchmark,
    exchange_kwargs=_exchange_kwargs,
)

# Extract report from the correct frequency key
analysis_freq = "{0}{1}".format(*Freq.parse(freq))
report_df, positions = portfolio_metric_dict.get(analysis_freq)
```

**设计理由**：

- 回测逻辑正确支持日频和分钟频率
- 当前使用 TopkDropoutStrategy，分钟级回测会每分钟调仓（成本高）
- 后续可以实现更适合分钟级的策略（如 TWAP、VWAP）

**注意事项**：

- TopkDropoutStrategy 是日频策略，分钟级使用会导致高换手率和高成本
- 分钟级策略优化留待后续版本实现

### 2026-02-20: 回测结果持久化

**问题**：

- 回测结果存储在内存中（全局变量 `_latest_backtest_result`）
- 服务器重启后结果丢失
- 用户刷新页面后无法恢复上次的回测结果

**解决方案**：

将回测结果保存到 JSON 文件，而不是内存。

**存储位置**：`/app/backtest_results/latest_result.json`

**修改文件**：

- `backend/app/api/routes/backtest.py`

**主要改动**：

```python
# File path for persisting latest backtest result
BACKTEST_RESULTS_DIR = Path(settings.QLIB_DATA_PATH).parent / "backtest_results"
LATEST_RESULT_FILE = BACKTEST_RESULTS_DIR / "latest_result.json"

def _save_backtest_result(result: dict) -> None:
    """Save backtest result to JSON file."""
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(LATEST_RESULT_FILE, "w") as f:
        json.dump(result, f, indent=2)

def _load_backtest_result() -> Optional[dict]:
    """Load backtest result from JSON file."""
    if LATEST_RESULT_FILE.exists():
        with open(LATEST_RESULT_FILE, "r") as f:
            return json.load(f)
    return None
```

**设计理由**：

- 服务器重启后结果不丢失
- 简单，无需数据库
- JSON 格式易于调试和查看
- 只保存最新一次结果，符合当前需求

---

## 2025-02-22: Phase 3 - Online Serving Integration (Phase 1 Implementation)

### Overview

Implemented Qlib Online Serving integration to enable automated daily workflow:

- Data incremental update
- Rolling model training
- Signal generation
- Paper trading (Phase 4)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Scheduled Task (Daily after market close)                      │
│  POST /api/v1/online/routine                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 0: Auto-initialize (if first call)                        │
│  - Create OnlineManager, RollingStrategy, TrainerRM             │
│  - Execute first_train() to train initial models                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Data incremental update                                │
│  - Call data source module to fetch latest data                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: OnlineManager.routine()                                │
│  - Check if rolling training is needed                          │
│  - Train new models if needed                                   │
│  - Update online models                                         │
│  - Generate trading signals                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Get signals for paper trading                          │
│  - OnlineManager.get_signals()                                  │
└─────────────────────────────────────────────────────────────────┘
```

### New Files

| File                                             | Description                  |
| ------------------------------------------------ | ---------------------------- |
| `backend/app/services/online_serving_service.py` | Online Serving service class |
| `backend/app/api/routes/online.py`               | Online Serving API routes    |

### Modified Files

| File                          | Changes                                        |
| ----------------------------- | ---------------------------------------------- |
| `backend/app/core/config.py`  | Added MongoDB and Online Serving configuration |
| `backend/app/api/main.py`     | Registered online routes                       |
| `docker-compose.override.yml` | Added MongoDB service and mlruns volume        |

### Configuration (config.py)

```python
# MongoDB Configuration (for Qlib Online Serving TaskManager)
MONGODB_URI: str = "mongodb://mongodb:27017"
MONGODB_DATABASE: str = "quantbot_qlib"

# Qlib Recorder/MLflow Configuration
QLIB_MLRUNS_PATH: str = "/app/mlruns"

# Online Serving Configuration
ONLINE_SERVING_EXPERIMENT_NAME: str = "quantbot_online"
ONLINE_SERVING_ROLLING_STEP: int = 20  # Rolling step in trading days
ONLINE_SERVING_ROLLING_TYPE: Literal["expanding", "sliding"] = "expanding"
```

### API Endpoints

| Endpoint                 | Method | Description                              |
| ------------------------ | ------ | ---------------------------------------- |
| `/api/v1/online/routine` | POST   | Execute daily routine (main entry point) |
| `/api/v1/online/status`  | GET    | Get current status                       |
| `/api/v1/online/signals` | GET    | Get latest trading signals               |
| `/api/v1/online/reset`   | POST   | Reset state (for debugging)              |

### Key Components

1. **OnlineServingService**: Main service class managing Online Serving workflow
2. **OnlineManager**: Qlib component managing online strategies and models
3. **RollingStrategy**: Defines rolling training strategy
4. **TrainerRM**: MongoDB-based trainer for task management
5. **RollingGen**: Generates rolling training tasks

### Auto-initialization

The system auto-initializes on first `/routine` call:

- No manual initialization required
- First call takes longer (trains initial models)
- Subsequent calls are faster (only trains if rolling step reached)

### Dynamic Frequency Detection

The system automatically detects data frequency:

- Checks for minute-level data in `QLIB_DATA_PATH_1MIN`
- Falls back to day-level frequency if no minute data found

---

## 2026-02-22: Phase 4 - Paper Trading Implementation

### Overview

Implemented Paper Trading service for simulated trading based on Online Serving signals.

**Key Design Decisions**:

- **Percentage-based trading plan**: Uses percentages instead of absolute quantities to ensure consistency between paper trading and real trading
- **Limit order with market order fallback**: Provides clear trading instructions for traders

### Trading Plan Design

| Field             | Description                                   |
| ----------------- | --------------------------------------------- |
| `sell_pct`        | Percentage of position to sell (usually 100%) |
| `target_weight`   | Target percentage of total assets to allocate |
| `reference_price` | Reference price (currently: opening price)    |
| `limit_price`     | Limit order price with slippage buffer        |
| `instruction`     | Clear trading instruction for traders         |

### Trading Instruction Example

```json
{
  "sell_orders": [
    {
      "instrument": "000001.SZ",
      "direction": "SELL",
      "sell_pct": 100.0,
      "reference_price": 15.2,
      "limit_price": 15.12,
      "instruction": "挂限价单 ≥15.12 卖出全部持仓，若未成交则改市价单"
    }
  ],
  "buy_orders": [
    {
      "instrument": "600519.SH",
      "direction": "BUY",
      "target_weight": 2.0,
      "reference_price": 1850.5,
      "limit_price": 1859.75,
      "instruction": "挂限价单 ≤1859.75 买入(金额=总资产×2.0%)，若未成交则改市价单"
    }
  ]
}
```

### API Endpoints

| Endpoint                            | Method | Description                            |
| ----------------------------------- | ------ | -------------------------------------- |
| `/api/v1/paper-trading/portfolio`   | GET    | Get current portfolio status           |
| `/api/v1/paper-trading/plan`        | POST   | Generate percentage-based trading plan |
| `/api/v1/paper-trading/execute`     | POST   | Execute paper trades (simulation)      |
| `/api/v1/paper-trading/trades`      | GET    | Get trade history                      |
| `/api/v1/paper-trading/performance` | GET    | Get performance metrics                |
| `/api/v1/paper-trading/reset`       | POST   | Reset paper trading state              |

### New Files

| File                                            | Description                 |
| ----------------------------------------------- | --------------------------- |
| `backend/app/services/paper_trading_service.py` | Paper Trading service class |
| `backend/app/api/routes/paper_trading.py`       | Paper Trading API routes    |

### Future Improvements (TODO)

#### Phase 4.1: Price Prediction Model

- [ ] Use LSTM/Transformer to predict more accurate reference prices
- [ ] Replace simple opening price with model-predicted prices
- [ ] Improve limit order pricing accuracy
- [ ] Reduce slippage losses

#### Phase 4.2: Dynamic Slippage Adjustment

- [ ] Calculate historical volatility for each stock
- [ ] Dynamically adjust slippage based on volatility
- [ ] Consider trading volume impact on slippage
- [ ] Implement adaptive slippage model

#### Phase 4.3: Real-time Price Integration

- [ ] Integrate real-time price data source (AKShare/Tushare)
- [ ] Fetch actual opening prices instead of placeholders
- [ ] Support intraday price updates
- [ ] Add price alert functionality

#### Phase 4.4: Trade Execution Tracking

- [ ] Record actual trade execution results from traders
- [ ] Compare paper trading vs real trading performance
- [ ] Generate execution quality reports
- [ ] Track slippage statistics

---

## Bug Fixes (2026-02-22)

### 1. Signal Date Range Issue

**Problem**: Paper trading plan showed signals only up to `2026-02-10` despite data being available until `2026-02-13`.

**Root Cause**: In Qlib's `OnlineManager`, when `prepare_signals()` collects predictions from recorders, both "online" and "offline" tagged recorders are included. Due to duplicate `rec_key` (model class + test segment), offline recorders' predictions (with older data) override online recorders' predictions (with latest data).

**Solution**: Added `_prepare_signals_with_online_filter()` method in `OnlineServingService` to:

1. Filter recorders by "online" tag using `OnlineToolR.get_online_tag()`
2. Create a filtered collector with only online recorders
3. Re-prepare signals after `routine()` execution

**Modified Files**:

- `backend/app/services/online_serving_service.py`
  - Added `_prepare_signals_with_online_filter()` method
  - Called in `_auto_init()` and `routine()` after standard routine execution

**Key Code**:

```python
def _prepare_signals_with_online_filter(self) -> None:
    from qlib.workflow.online.utils import OnlineToolR
    from qlib.model.ens.ensemble import RollingEnsemble, AverageEnsemble
    from qlib.workflow.task.collect import MergeCollector

    online_tool = OnlineToolR()

    def online_filter(rec):
        return online_tool.get_online_tag(rec) == OnlineToolR.ONLINE_TAG

    collector_dict = {}
    for strategy in self._online_manager.strategies:
        collector = strategy.get_collector(
            process_list=[RollingEnsemble()],
            rec_filter_func=online_filter
        )
        collector_dict[strategy.name_id] = collector

    merge_collector = MergeCollector(collector_dict, process_list=[])
    signals = AverageEnsemble()(merge_collector())
    self._online_manager.signals = signals
```

### 2. Reference Price Placeholder Issue

**Problem**: `reference_price` in trading plan was always `10.0` (hardcoded placeholder).

**Root Cause**: `_get_latest_prices()` method in `PaperTradingService` was not implemented, returning default value `10.0` for all instruments.

**Solution**: Implemented real price fetching from Qlib data:

1. Convert instrument format from `SH600000` to `sh600000` (lowercase for Qlib)
2. Use `D.features()` to fetch `$close` prices
3. Extract latest close price for each instrument

**Modified Files**:

- `backend/app/services/paper_trading_service.py`
  - Rewrote `_get_latest_prices()` method to fetch real prices from Qlib

**Key Code**:

```python
def _get_latest_prices(self, instruments: List[str]) -> Dict[str, float]:
    from qlib.data import D

    # Convert: SH600000 -> sh600000 (lowercase for Qlib)
    qlib_instruments = [inst.lower() for inst in instruments]

    df = D.features(qlib_instruments, fields=["$close"], freq="day")

    for qlib_inst in qlib_instruments:
        inst_data = df.xs(qlib_inst, level="instrument")
        latest_close = inst_data["$close"].dropna().iloc[-1]
        prices[original_inst] = float(latest_close)
```

**Result**: Trading plan now shows real stock prices (e.g., SH600309: 84.96, SZ300750: 365.34)

---

## Configuration Refactoring (2026-02-22)

### Overview

Refactored the configuration system to centralize all Qlib-related configurations and improve maintainability.

### Requirements Implemented

#### Requirement 1: Data Configuration Centralization

**Problem**: Data type (day/1min), data source (yahoo/tushare), and stock pool (csi300/csi500) configurations were scattered across multiple files and could be configured from frontend, leading to inconsistency.

**Solution**: Created `system_config.yaml` as the single source of truth for data configuration.

**Key Features**:

- Configuration change detection: When `freq`, `source`, `stock_pool`, or `region` changes, existing data is automatically cleaned up
- Download range based on freq: day data downloads 365 days, 1min data downloads 5 days
- Frontend no longer configures these parameters

**Configuration File**: `backend/app/config/qlib/system_config.yaml`

```yaml
data:
  freq: "day" # "day" or "1min"
  source: "yahoo" # "yahoo", "tushare", "akshare"
  stock_pool: "csi300" # "csi300", "csi500", "csi800", "all", "sp500", "nasdaq100"
  region: "cn" # "cn" or "us"
  download_days:
    day: 365
    1min: 5
```

**Modified Files**:

- `backend/app/config/qlib/__init__.py` - New QlibConfig class
- `backend/app/config/qlib/system_config.yaml` - New config file
- `backend/app/services/data_source_manager.py` - Uses qlib_config, detects config changes
- `backend/app/services/online_serving_service.py` - Uses qlib_config instead of settings
- `backend/app/services/paper_trading_service.py` - Uses qlib_config instead of settings
- `backend/app/core/config.py` - Removed migrated Qlib settings

#### Requirement 2: Factor Computation from Bin Data

**Problem**: When adding a new factor, need to compute factor values from existing bin data and save to bin files. When updating a factor, need to delete old bin files and recompute.

**Solution**: Added methods to `FactorStorage` and `FactorService` for factor computation and cleanup.

**New Methods in `FactorStorage`**:

```python
def delete_factor_bin_files(self, factor_name: str) -> Dict[str, Any]:
    """Delete all bin files for a specific factor across all symbols."""

def compute_factor_from_expression(self, factor_name: str, expression: str, ...) -> pd.DataFrame:
    """Compute factor values from expression using existing bin data via D.features()."""

def compute_and_save_factor(self, factor_name: str, expression: str, ...) -> Dict[str, Any]:
    """Compute factor from expression and save to bin files."""
```

**New Methods in `FactorService`**:

```python
def compute_and_save_factor(self, factor_id: uuid.UUID, freq: str = "day") -> Dict[str, Any]:
    """Compute factor from its expression and save to bin files."""

def update_factor_with_recompute(self, factor_id: uuid.UUID, factor_data: FactorUpdate, ...) -> Dict[str, Any]:
    """Update factor and recompute if expression changed."""

def delete_factor_with_cleanup(self, factor_id: uuid.UUID, freq: str = "day") -> Dict[str, Any]:
    """Delete factor from database and clean up bin files."""
```

**Test Result**:

```
Computing factor 'test_ma5' from expression: Mean($close, 5)
Found 300 instruments
Computed factor 'test_ma5': shape=(74987, 1), non-null=74987
Factor 'test_ma5' written to 300 symbol directories
Deleted 300 bin files for factor 'test_ma5' (failed: 0)
```

#### Requirement 3: Reorganize Config Files

**Problem**: Configuration files were scattered in `config/` directory. Need to organize all Qlib-related configs into a dedicated folder.

**Solution**: Moved all Qlib config files to `backend/app/config/qlib/` directory.

**New Directory Structure**:

```
backend/app/config/qlib/
├── __init__.py              # QlibConfig class - loads all configs
├── system_config.yaml       # Data source, stock pool, freq, region, MongoDB, Online Serving
├── training_config.yaml     # Model configuration, dataset configuration, training parameters
├── backtest_config.yaml     # Strategy configuration, backtest parameters, trading costs
└── paper_trading_config.yaml # Portfolio settings, strategy settings, risk management
```

**QlibConfig Class Features**:

- Singleton pattern for global access
- Loads all 4 config files on initialization
- Provides property accessors for all configuration values
- `to_dict()` method returns all configurations

**Usage Example**:

```python
from app.config.qlib import qlib_config

# System config
print(qlib_config.freq)        # "day"
print(qlib_config.stock_pool)  # "csi300"

# Training config
print(qlib_config.task_config)

# Backtest config
print(qlib_config.backtest_strategy)

# Paper trading config
print(qlib_config.initial_cash)  # 100000000.0
print(qlib_config.topk)          # 50
```

#### Requirement 4: Clean Up Unused Code

**Problem**: Some code files were not being used and cluttered the codebase.

**Solution**: Identified and removed unused files.

**Deleted Files**:

- `backend/app/services/factor_expression_validator.py` - Not referenced by any other file
- `backend/app/config/training_config.yaml` - Moved to qlib/ folder
- `backend/app/config/backtest_config.yaml` - Moved to qlib/ folder

### Lessons Learned

1. **PowerShell and `$` in strings**: When testing Qlib expressions in PowerShell, `$close` is interpreted as a variable. Solution: Use test script files instead of inline commands.

2. **Qlib instrument format**: Qlib uses lowercase instrument names (e.g., `sh600000`) in `features/` directories, but uppercase in `instruments/all.txt`. Always convert to lowercase when querying data.

3. **Configuration change detection**: Use a hash of key configuration values to detect changes and trigger data cleanup.

4. **Singleton pattern for config**: Using singleton pattern ensures consistent configuration access across the application.

---

## 🎨 Frontend Refactor: Factor Page Complete (2026-02-22)

### 📋 Overview

Successfully completed the Factor page refactoring with comprehensive testing of create, update, and delete operations, including bin file synchronization verification.

### ✅ Implemented Features

#### 1. Summary Cards

Added three summary cards at the top of the Factor page:

- **Total Factors**: Count of all active factors (features + labels)
- **Features**: Count of feature-type factors
- **Labels**: Count of label-type factors

Each card displays the count with appropriate icons (Database, Layers, Tag).

#### 2. Built-in OHLCV Features Display

- Built-in features (close.day, high.day, low.day, open.day, volume.day) are correctly displayed
- Marked as "Built-in" and locked (non-editable, non-deletable)
- Retrieved from data source status API

#### 3. Factor CRUD Operations with Bin File Synchronization

**Create Factor**:

- Frontend creates factor in database
- Backend automatically computes and saves bin files to `/app/qlib_data/features/{symbol}/`
- Uses Qlib's `D.features()` to compute factor values from expression
- Saves to all 300 symbol directories

**Update Factor**:

- Frontend updates factor expression
- Backend detects expression change
- Automatically deletes old bin files
- Recomputes and saves new bin files
- Database record updated

**Delete Factor**:

- Frontend triggers delete operation
- Backend performs hard delete (removes from database completely)
- Automatically deletes all associated bin files
- Clean removal from all 300 symbol directories

### 🔧 Technical Fixes

#### Fix 1: FactorStorage Path Configuration

**Problem**: `FactorStorage` was using incorrect path (`.` instead of `/app/qlib_data`)

**Solution**: Modified `_get_storage_dir_for_freq()` to use `qlib_config`:

```python
def _get_storage_dir_for_freq(self, freq: str) -> Path:
    from app.config.qlib import qlib_config

    if freq == "1min":
        qlib_data_dir = qlib_config.qlib_data_path_1min
    else:
        qlib_data_dir = qlib_config.qlib_data_path_day

    return Path(qlib_data_dir)
```

#### Fix 2: Delete API Response Error

**Problem**: DELETE endpoint returned 204 No Content but had response body, causing `RuntimeError: Response content longer than Content-Length`

**Solution**: Changed from `JSONResponse` to `Response`:

```python
# Before
return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

# After
return Response(status_code=status.HTTP_204_NO_CONTENT)
```

#### Fix 3: Soft Delete to Hard Delete

**Problem**: `delete_factor_with_cleanup()` was performing soft delete (setting status to DELETED), causing factors to remain in database

**Solution**: Changed to hard delete:

```python
# Before
factor.status = FactorStatus.DELETED
factor.updated_at = datetime.utcnow()
session.add(factor)
session.commit()

# After
session.delete(factor)
session.commit()
```

### ✅ Comprehensive Testing Results

#### Test 4a: Create Factor and Verify Bin Files ✅

**Steps**:

1. Created factor `test_rsi` with expression `Mean($close, 14)`
2. Verified bin file creation: `test_rsi.day.bin` exists
3. Verified data integrity: 253 data points, 100% valid

**Results**:

- ✅ Bin file created successfully
- ✅ Data size: 1012 bytes
- ✅ Non-NaN count: 253/253 (100%)
- ✅ Values correct: [10.27, 10.285, 10.326667, ...]

#### Test 4b: Update Factor and Verify Bin Files ✅

**Steps**:

1. Updated expression from `Mean($close, 14)` to `Mean($close, 20)`
2. Verified file modification time changed
3. Verified database expression updated
4. Verified bin files recomputed

**Results**:

- ✅ Database expression updated to `Mean($close, 20)`
- ✅ File mtime changed: 1771757475 → 1771757763
- ✅ 300 old bin files deleted
- ✅ 300 new bin files created
- ✅ Data recomputed correctly

#### Test 4c: Delete Factor and Verify Bin Files Deleted ✅

**Steps**:

1. Deleted `test_rsi` factor from frontend
2. Verified bin files deleted
3. Verified database record removed

**Results**:

- ✅ Bin file deleted: `test_rsi.day.bin` does not exist
- ✅ Database record removed: Not found
- ✅ 300 bin files deleted from all symbol directories
- ✅ Frontend no longer displays the factor

### 📊 System Architecture

**Factor Lifecycle Flow**:

```
Frontend Action → Backend API → FactorService → FactorStorage → Qlib Data
     ↓                ↓              ↓              ↓              ↓
  Create         POST /factors   create_factor   compute_and_   features/
                                                  save_factor    {symbol}/
                                                                 *.day.bin
     ↓                ↓              ↓              ↓              ↓
  Update         PUT /factors    update_factor_  delete_old +   Delete old
                                 with_recompute  recompute      + Create new
     ↓                ↓              ↓              ↓              ↓
  Delete         DELETE /factors delete_factor_  delete_factor  Delete all
                                 with_cleanup    _bin_files     bin files
```

### 🎯 Key Achievements

1. **Complete CRUD Operations**: All factor operations work correctly with bin file synchronization
2. **Data Integrity**: 100% consistency between database and bin files
3. **Automatic Cleanup**: No orphaned bin files or database records
4. **User Experience**: Smooth frontend interactions with proper error handling
5. **Built-in Features**: Correctly displayed and protected from modification

### 📝 Files Modified

**Backend**:

- `backend/app/services/factor_storage.py` - Fixed path configuration
- `backend/app/services/factor_service.py` - Changed to hard delete
- `backend/app/api/routes/factors.py` - Fixed DELETE response

**Frontend**:

- `frontend/src/routes/_layout/factors.tsx` - Added summary cards

### 🚀 Next Steps

Factor page refactoring is complete. Ready to proceed with:

1. Data Source page design and implementation
2. Training page design and implementation
3. Backtest page design and implementation
4. Paper Trading page design and implementation

---

## 🔍 Frontend Refactor: Data Source Page Design (2026-02-22)

### 📋 Design Objectives

Refactor the Data Source page to:

1. Remove manual data collection controls (handled by routine)
2. Add frequency indicator to summary cards
3. Integrate Qlib data quality analysis features
4. Provide comprehensive data health monitoring

### 🎯 Design Requirements

Based on user requirements:

1. ✅ Remove incremental update and download data buttons (routine handles this)
2. ✅ Remove entire data collection configuration card (configured in code)
3. ✅ Add frequency (freq) to summary cards
4. ✅ Integrate Qlib data quality analysis and metrics

### 🔍 Qlib Data Analysis Research

#### Discovered Features (from `qlib-source/scripts/check_data_health.py`)

**DataHealthChecker Class** provides:

1. **Missing Data Detection**

   - Identifies instruments with missing OHLCV data
   - Counts missing values per column (open, high, low, close, volume)
   - Output: Per-instrument breakdown

2. **Large Step Changes Detection**

   - Detects abnormal price/volume jumps (potential data errors)
   - Thresholds: Price 50%, Volume 300% (configurable)
   - Output: Instrument, column, date, percentage change

3. **Required Columns Validation**

   - Ensures all required OHLCV columns exist
   - Output: Instruments with missing columns

4. **Factor Column Validation**

   - Checks if adjustment factor column exists and has data
   - Output: Instruments with missing/empty factor column

5. **Directory Case Validation**
   - Ensures all feature directories are lowercase (Linux compatibility)
   - Output: Non-lowercase directory names

### 📐 Page Layout Design

```
┌─────────────────────────────────────────────────────┐
│  Data Sources Title                                  │
├─────────────────────────────────────────────────────┤
│  Summary Cards (5 cards)                            │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌───┐│
│  │Source  │ │Pool    │ │Freq ⭐ │ │Count   │ │Size││
│  │Yahoo   │ │CSI300  │ │Daily   │ │300     │ │150M││
│  └────────┘ └────────┘ └────────┘ └────────┘ └───┘│
├─────────────────────────────────────────────────────┤
│  Data Overview Card                                 │
│  - Date Range, Trading Days, Features, Label        │
│  - Export and Clear buttons only                    │
├─────────────────────────────────────────────────────┤
│  Data Quality Metrics Card ⭐ NEW                   │
│  - Completeness: 98.5% ✅                           │
│  - Missing Data: 3 instruments [Details]            │
│  - Anomalies: 2 detected [Details]                  │
│  - Integrity: All checks passed ✅                  │
└─────────────────────────────────────────────────────┘
```

### 🎨 Component Design

#### Summary Cards (5 cards)

1. **Data Source** - Yahoo Finance / Tushare (Database icon)
2. **Stock Pool** - CSI300 / CSI500 / SP500 / NASDAQ100 (TrendingUp icon)
3. **Frequency** ⭐ - Daily (1d) / Minute (1m) (Clock icon)
4. **Instruments** - Count of instruments (BarChart3 icon)
5. **Data Size** - Size in MB (HardDrive icon)

#### Data Overview Card

- Date Range: Start → End
- Features: List of available features
- Label: Prediction target (if configured)
- **Actions**: Export Data, Clear Data (only these two)

#### Data Quality Metrics Card ⭐ NEW

**Summary Display**:

- **Completeness**: Percentage with status badge
- **Missing Data**: Count with [Details] button
- **Anomalies**: Count with [Details] button
- **Integrity**: Status with checkmarks

**Details Dialog**:

- Triggered by [Details] button
- Shows complete list of issues
- Scrollable and searchable
- Example format:
  ```
  Missing Data Details
  ┌────────────────────────────────────┐
  │ sh600000                           │
  │   - open: 2 missing values         │
  │   - close: 1 missing value         │
  ├────────────────────────────────────┤
  │ sh600001                           │
  │   - volume: 5 missing values       │
  └────────────────────────────────────┘
  ```

### 🔧 Implementation Plan

#### Backend Implementation

**1. Configuration File Update**

Add to `backend/app/config/qlib/system_config.yaml`:

```yaml
data_quality:
  large_step_threshold_price: 0.5 # 50% for price columns
  large_step_threshold_volume: 3.0 # 300% for volume
  missing_data_threshold: 0 # Max allowed missing values
```

**2. Create DataHealthService**

File: `backend/app/services/data_health_service.py`

- Integrate Qlib's DataHealthChecker logic
- Implement health check methods
- Return summary statistics and detailed lists

**3. Integrate with Routine**

In routine's data preparation step:

- After data download/conversion completes
- Run data health check
- Cache results for frontend query

**4. API Endpoint**

`GET /api/v1/data-source/health`

- Returns cached data health metrics
- Response includes summary and details

**Response Model**:

```python
class DataHealthMetrics(BaseModel):
    completeness_percentage: float
    missing_data_count: int
    missing_data_details: List[MissingDataDetail]
    anomaly_count: int
    anomalies: List[DataAnomaly]
    integrity_checks: IntegrityChecks

class MissingDataDetail(BaseModel):
    instrument: str
    open: int
    high: int
    low: int
    close: int
    volume: int

class DataAnomaly(BaseModel):
    instrument: str
    column: str
    date: str
    pct_change: float

class IntegrityChecks(BaseModel):
    required_columns: bool
    factor_column: bool
    directory_case: bool
```

#### Frontend Implementation

**1. Update Summary Cards**

- Add Frequency card (5th card)
- Display freq from data source status

**2. Simplify Actions**

- Remove: Incremental Update button
- Remove: Download Data button
- Keep: Export Data, Clear Data

**3. Remove Configuration Card**

- Delete entire Data Collection Configuration Card

**4. Add Data Quality Metrics Card**

- Display summary statistics
- Add [Details] buttons
- Implement Details dialogs

**Components**:

- Use shadcn/ui Dialog for details
- Use Badge for status indicators (✅ ⚠️ ❌)
- Use Alert for warnings

### 📊 Implementation Details

#### Data Quality Check Timing

- **Trigger**: After routine's data preparation step completes
- **Frequency**: On each data update
- **Caching**: Results cached for frontend queries
- **Performance**: Expensive operation, run in background

#### Anomaly Threshold Configuration

- **Location**: Configuration file
- **Defaults**: Qlib defaults (price 50%, volume 300%)
- **Customization**: Can be adjusted in config

#### Display Detail Level

- **Main View**: Summary statistics only
- **Details View**: Complete issue lists via dialog
- **User Control**: Click [Details] to expand

### 🎯 Key Features

1. **Simplified UI**: Removed manual data collection controls
2. **Enhanced Monitoring**: Real-time data quality metrics
3. **Qlib Integration**: Leverages Qlib's data health checker
4. **User-Friendly**: Summary + details on demand
5. **Automated**: Quality checks run automatically with routine

---

## ✅ Frontend Refactor: Data Source Page Implementation (2026-02-22)

### 📋 Implementation Summary

Successfully completed the Data Source page refactoring with full backend and frontend integration.

### 🔧 Backend Implementation

#### 1. Configuration (`backend/app/config/qlib/system_config.yaml`)

Added data quality configuration:

```yaml
data_quality:
  large_step_threshold_price: 0.5 # 50% price change threshold
  large_step_threshold_volume: 3.0 # 300% volume change threshold (not used)
  missing_data_threshold: 0 # No missing values allowed
```

#### 2. Data Health Service (`backend/app/services/data_health_service.py`)

Created comprehensive data health checking service:

**Features**:

- Load all instruments data from Qlib
- Check missing data in OHLCV columns (excluding factor)
- Detect large step changes in price columns only (OHLC, not volume)
- Validate required columns existence
- Check factor column availability
- Validate directory naming conventions

**Key Methods**:

- `check_data_health()` - Main entry point
- `_load_qlib_data()` - Load data for all 300 instruments
- `_check_missing_data()` - Check OHLCV completeness
- `_check_large_step_changes()` - Detect price anomalies (>50% change)
- `_check_required_columns()` - Validate OHLCV columns
- `_check_missing_factor()` - Check factor column
- `_check_features_dir_lowercase()` - Validate directory naming

**Bug Fixes**:

- Replace infinity values with 0 to prevent JSON serialization errors
- Only check OHLCV columns for missing data (factor checked separately)
- Only detect price anomalies, not volume anomalies (reduces false positives)

#### 3. API Models (`backend/app/models.py`)

Added data health models:

```python
class MissingDataDetail(SQLModel):
    instrument: str
    open: int
    high: int
    low: int
    close: int
    volume: int

class DataAnomaly(SQLModel):
    instrument: str
    column: str
    date: str
    pct_change: float

class IntegrityChecks(SQLModel):
    required_columns: bool
    factor_column: bool
    directory_case: bool

class DataHealthMetrics(SQLModel):
    data_exists: bool
    completeness_percentage: float
    missing_data_count: int
    missing_data_details: List[MissingDataDetail]
    anomaly_count: int
    anomalies: List[DataAnomaly]
    integrity_checks: IntegrityChecks
    checked_at: str
```

#### 4. API Endpoint (`backend/app/api/routes/data_source.py`)

Added health check endpoint:

```python
@router.get("/health", response_model=DataHealthMetrics)
def get_data_health_endpoint():
    """Get data health metrics."""
    health_service = get_data_health_service()
    freq = qlib_config.freq
    health_metrics = health_service.check_data_health(freq=freq)
    return DataHealthMetrics(**health_metrics)
```

#### 5. Configuration Access (`backend/app/config/qlib/__init__.py`)

Added `data_quality` property to QlibConfig for accessing configuration.

### 🎨 Frontend Implementation

#### 1. Summary Cards (`frontend/src/routes/_layout/data-sources.tsx`)

Added 5 summary cards:

- **Data Source** (Database icon)
- **Stock Pool** (TrendingUp icon)
- **Frequency** ⭐ NEW (Clock icon) - Shows "Daily (1d)" or "Minute (1m)"
- **Instruments** (BarChart3 icon)
- **Data Size** (HardDrive icon)

#### 2. Removed Components

- ❌ Incremental Update button
- ❌ Download Data button
- ❌ Data Collection Configuration Card (entire card removed)

Kept only:

- ✅ Export Data button
- ✅ Clear Data button

#### 3. Data Quality Metrics Card ⭐ NEW

**Main Display**:

- **Completeness**: Percentage with color-coded badge (Good/Warning/Poor)
- **Missing Data**: Count with [Details] button
- **Anomalies**: Count with [Details] button
- **Integrity**: Three status badges (Columns OK, Factor OK, Naming OK)

**Details Dialogs**:

- **Missing Data Dialog**: Shows instruments with missing OHLCV values
- **Anomalies Dialog**: Shows price anomalies with instrument, column, date, and change percentage

#### 4. UI Components Used

- shadcn/ui Card, Badge, Button, Dialog
- Lucide icons: CheckCircle, AlertTriangle, XCircle, Database, TrendingUp, Clock, BarChart3, HardDrive

### 🧪 Testing Results

**Test 1: UI Display** ✅

- Summary cards display correctly with frequency
- Data Quality Metrics Card shows proper metrics
- Completeness: 99.3% (298/300 instruments)
- Missing Data: 2 instruments
- Anomalies: Reduced from 170 to minimal (only price anomalies)

**Test 2: Missing Data Details** ✅

- Dialog opens correctly
- Shows detailed breakdown by instrument and column

**Test 3: Anomalies Details** ✅

- Dialog opens correctly
- Shows only price anomalies (OHLC), not volume
- Displays instrument, column, date, and percentage change

**Test 4: Export Functionality** ✅

- Export Data button works correctly
- Downloads CSV file with proper data

**Test 5: Clear Functionality** ⏭️

- Deferred to avoid data loss during testing

### 📝 Key Decisions

1. **Factor Column Handling**: Yahoo Finance doesn't provide factor data, so it's checked separately and failure is expected
2. **Volume Anomalies**: Excluded from detection to reduce false positives (volume naturally has high volatility)
3. **Sample Size**: Check all 300 instruments (removed 50-instrument limit)
4. **Infinity Values**: Replace with 0 to prevent JSON serialization errors
5. **Completeness Calculation**: Based on OHLCV data only, not factor

### 🎯 Achievements

1. ✅ Simplified UI by removing manual controls
2. ✅ Added frequency indicator to summary cards
3. ✅ Integrated Qlib data quality analysis
4. ✅ Provided comprehensive health monitoring
5. ✅ Implemented details-on-demand pattern
6. ✅ Fixed all JSON serialization and data loading issues
7. ✅ Reduced false positive anomalies by focusing on price only

### 🚀 Next Steps

Data Source page refactoring is complete. Ready to proceed with:

1. Models page design and implementation
2. Backtest page design and implementation
3. Paper Trading page design and implementation

---

## 📊 Frontend Refactor: Models Page Design (2026-02-22)

### 📋 Design Objectives

Refactor the Training page to Models page:

1. Rename page from "Training" to "Models"
2. Display Rolling Ensemble model performance metrics
3. Provide comprehensive model analysis with charts
4. No training controls (training handled by routine)

### 🎯 Design Requirements

**Key Decisions**:

1. ✅ Display only the active Rolling Ensemble model (not individual models)
2. ✅ Use feature importance from the latest model (Model 13)
3. ✅ Calculate metrics in Routine (not on page load)
4. ✅ Chart-heavy UI with text explanations

**Rolling Training Context**:

- System uses Rolling Training with 13 models (240 days / 20-day step)
- Each model trained on expanding window (e.g., Model 13 uses all 240 days)
- Final predictions use RollingEnsemble (average of all 13 models)
- Models page displays ensemble performance, not individual models

### 📊 Metrics to Display

Based on Qlib's professional quantitative analysis:

#### 1. IC Metrics (Information Coefficient)

- **IC Mean**: Average correlation between predictions and returns
- **IC Std**: Standard deviation of IC
- **ICIR**: IC Information Ratio (IC Mean / IC Std)
- **Rank IC Mean**: Spearman correlation (rank-based)
- **Rank IC Std**: Standard deviation of Rank IC
- **Rank ICIR**: Rank IC Information Ratio

**Evaluation Standards**:

- IC > 0.03: Good
- IC > 0.05: Excellent
- IC > 0.08: Outstanding
- ICIR > 1.0: Stable
- ICIR > 1.5: Very stable

#### 2. Long-Short Strategy Performance

- **Long-Short Ann Return**: Annualized return of long-short strategy
- **Long-Short Ann Sharpe**: Sharpe ratio (return/risk)
- **Long-Avg Ann Return**: Long vs market average return
- **Long-Avg Ann Sharpe**: Long-average Sharpe ratio

**Evaluation Standards**:

- Return > 10%: Good
- Return > 15%: Excellent
- Sharpe > 1.0: Acceptable
- Sharpe > 1.5: Excellent
- Sharpe > 2.0: Outstanding

#### 3. Feature Importance

- Top 20 features from latest model
- Bar chart visualization
- Helps understand key factors

#### 4. Prediction Quality

- **Long Precision**: Accuracy of up predictions (>0.55 good, >0.60 excellent)
- **Short Precision**: Accuracy of down predictions
- **Auto Correlation**: Prediction stability (0.1-0.3 normal)

#### 5. Group Return Analysis

- 5 groups by prediction score
- Cumulative return curves
- Validates model's ranking ability

### 🎨 Page Layout

```
┌─────────────────────────────────────────────────────┐
│  Models                                              │
│  Current Active Model: Rolling Ensemble (13 models) │
├─────────────────────────────────────────────────────┤
│  📊 Model Overview (4 Summary Cards)                │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │
│  │Model   │ │Trained │ │IC      │ │Sharpe  │      │
│  │Rolling │ │2026-02 │ │0.045   │ │1.8     │      │
│  │Ensemble│ │        │ │        │ │        │      │
│  └────────┘ └────────┘ └────────┘ └────────┘      │
├─────────────────────────────────────────────────────┤
│  📈 IC Analysis Card                                │
│  ┌─────────────────────────────────────────────┐   │
│  │ [IC Time Series Chart - Daily IC bars]      │   │
│  │ Explanation: IC measures prediction-return  │   │
│  │ correlation. Higher is better.              │   │
│  │ Current: IC=0.045 (Excellent), ICIR=1.23   │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ [Monthly IC Heatmap]                        │   │
│  │ Explanation: Observe IC stability over time │   │
│  └─────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  💰 Long-Short Performance Card                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ [5-Group Cumulative Return Chart]           │   │
│  │ Explanation: Group1 (highest prediction)    │   │
│  │ should have highest return                  │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ [Long-Short Return Distribution]            │   │
│  │ Ann Return: 15.2%, Sharpe: 1.8 (Excellent)  │   │
│  └─────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  🔍 Feature Importance Card                         │
│  ┌─────────────────────────────────────────────┐   │
│  │ [Top 20 Features Bar Chart]                 │   │
│  │ Explanation: Shows most valuable factors    │   │
│  │ [View All Features] button                  │   │
│  └─────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  ✅ Prediction Quality Card                         │
│  │ Long Precision: 0.58, Short Precision: 0.56│   │
│  ┌─────────────────────────────────────────────┐   │
│  │ [Auto Correlation Time Series]              │   │
│  │ Explanation: Measures prediction stability  │   │
│  │ Current: 0.12 (Normal, not overfitting)     │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 🔧 Technical Implementation

#### Backend Architecture

**1. ModelMetricsService** (`backend/app/services/model_metrics_service.py`)

- Calculates all metrics using Qlib's analysis functions
- Methods:
  - `calculate_all_metrics()`: Main entry point
  - `_calculate_ic_metrics()`: IC, ICIR, Rank IC, time series, monthly heatmap
  - `_calculate_long_short_metrics()`: Returns, Sharpe, cumulative data
  - `_calculate_quality_metrics()`: Precision, auto correlation
  - `_calculate_feature_importance()`: From latest model
  - `_calculate_group_returns()`: 5-group analysis
  - `save_metrics()`: Save to JSON file
  - `load_metrics()`: Load from JSON file

**2. Integration with Routine** (`backend/app/services/online_serving_service.py`)

- Added Step 5 in `routine()` method
- Calls `_calculate_model_metrics()` after signal generation
- Automatically loads label data
- Extracts latest model for feature importance
- Saves to `mlruns/model_metrics/active_metrics.json`

**3. Data Flow**:

```
Routine → Train Models → Generate Signals → Calculate Metrics → Save JSON
                                                ↓
                                        Frontend API Request
                                                ↓
                                        Load JSON → Display
```

#### Qlib Analysis Functions Used

From `qlib.contrib.eva.alpha`:

- `calc_ic()`: Calculate IC and Rank IC
- `calc_long_short_return()`: Calculate long-short returns
- `calc_long_short_prec()`: Calculate precision
- `pred_autocorr()`: Calculate auto correlation

From `qlib.model.interpret.base`:

- `get_feature_importance()`: Extract feature importance

From `qlib.contrib.report.analysis_model`:

- Monthly IC calculation logic
- Group return analysis logic

#### Metrics Storage

**File**: `mlruns/model_metrics/active_metrics.json`

**Structure**:

```json
{
  "model_type": "Rolling Ensemble",
  "calculated_at": "2026-02-22T10:00:00Z",
  "frequency": "day",
  "ic_metrics": {
    "ic_mean": 0.045,
    "ic_std": 0.035,
    "icir": 1.23,
    "rank_ic_mean": 0.052,
    "rank_ic_std": 0.038,
    "rank_icir": 1.45,
    "ic_series": [...],
    "rank_ic_series": [...],
    "monthly_ic": [...]
  },
  "long_short_metrics": {
    "long_short_ann_return": 0.152,
    "long_short_ann_sharpe": 1.8,
    "long_avg_ann_return": 0.085,
    "long_avg_ann_sharpe": 1.2,
    "long_short_series": [...]
  },
  "quality_metrics": {
    "long_precision": 0.58,
    "short_precision": 0.56,
    "auto_correlation": 0.12,
    "auto_corr_series": [...]
  },
  "feature_importance": [...],
  "group_returns": {
    "Group1": [...],
    "Group2": [...],
    ...
  }
}
```

### 📝 Key Design Decisions

1. **Why Rolling Ensemble?**

   - Online Serving uses RollingEnsemble to combine 13 models
   - Ensemble predictions are what's actually used in production
   - More accurate than showing individual model metrics

2. **Why Calculate in Routine?**

   - Metrics calculation is expensive (involves loading label data)
   - Pre-calculating avoids page load delays
   - Metrics only need to update when new models are trained

3. **Why Latest Model for Feature Importance?**

   - Ensemble doesn't have a single feature importance
   - Latest model (Model 13) has most data and is most representative
   - Still provides valuable insights for factor engineering

4. **Why Chart + Text?**
   - Charts provide visual intuition
   - Text explanations help non-experts understand
   - Evaluation standards guide interpretation

### 🎯 Implementation Status

**Phase 1: Backend - Metrics Calculation** ✅

- ✅ Created ModelMetricsService with all metrics
- ✅ Integrated into Routine service
- ✅ Automatic label data loading
- ✅ Latest model extraction for feature importance
- ✅ JSON storage for frontend access

**Phase 2: Backend - API Endpoints** ✅

- ✅ API models for metrics response
- ✅ GET /api/v1/models/active/metrics
- ✅ GET /api/v1/models/active/charts/{chart_type}

**Phase 3: Frontend - UI Implementation** ✅

- ✅ Renamed Training page to Models
- ✅ Implemented all chart components
- ✅ Added text explanations and interpretations
- ✅ Integrated with API

---

## 📊 Models Page - Chart Implementation Details

**Last Updated**: 2026-02-23

### Overview

The Models page displays comprehensive metrics for the Rolling Ensemble model, including IC analysis, Long-Short strategy performance, prediction quality, and feature importance.

### Charts Implemented

| Chart               | Purpose                                   | Data Source                              |
| ------------------- | ----------------------------------------- | ---------------------------------------- |
| IC Time Series      | Daily IC values over time                 | `ic_metrics.ic_series`                   |
| Monthly IC Heatmap  | IC aggregated by month                    | `ic_metrics.monthly_ic`                  |
| IC Distribution     | Histogram of daily IC values              | `ic_metrics.ic_distribution.histogram`   |
| Q-Q Plot            | Check if IC follows normal distribution   | `ic_metrics.ic_distribution.qq_plot`     |
| Group Returns       | Cumulative returns by prediction quintile | `group_returns` (separate API)           |
| Cumulative Returns  | Long-Short strategy cumulative returns    | `long_short_metrics.cumulative_returns`  |
| Return Distribution | Histogram of daily returns                | `long_short_metrics.return_distribution` |
| Turnover Analysis   | Top/Bottom stock turnover over time       | `quality_metrics.turnover`               |
| Feature Importance  | Model feature importance ranking          | `feature_importance`                     |

### Key Metrics Explained

#### IC (Information Coefficient)

- **Definition**: Correlation between model predictions and actual returns
- **Range**: -1 to +1
- **Good IC**: > 0.03, Very Good: > 0.05
- **ICIR**: IC Mean / IC Std (measures stability)

#### Turnover

- **Definition**: Percentage of stocks changed daily in Top/Bottom selection
- **High Turnover (>50%)**: High trading costs, unstable predictions
- **Low Turnover (<30%)**: Low trading costs, stable predictions
- **Current Model**: ~73% (high, needs optimization)

#### Group Returns

- Stocks sorted by prediction score into 5 groups (quintiles)
- Group 1: Top 20% (predicted to rise most)
- Group 5: Bottom 20% (predicted to fall most)
- Ideal: Clear separation with Group 1 on top

### Backend Implementation

#### Pydantic Models Added (`app/models.py`)

```python
# IC Distribution models
class ICDistributionBin(SQLModel):
    bin_start: float
    bin_end: float
    count: int
    bin_center: float

class QQPlotPoint(SQLModel):
    theoretical: float
    sample: float

class ICDistribution(SQLModel):
    histogram: List[ICDistributionBin]
    qq_plot: List[QQPlotPoint]
    mean: float
    std: float
    skewness: float
    kurtosis: float

# Cumulative Returns models
class CumulativeReturnPoint(SQLModel):
    datetime: str
    cumulative_return: float

class ReturnDistributionBin(SQLModel):
    bin_start: float
    bin_end: float
    count: int
    bin_center: float

# Turnover models
class TurnoverPoint(SQLModel):
    datetime: str
    turnover: float

class TurnoverData(SQLModel):
    top_turnover_series: List[TurnoverPoint]
    bottom_turnover_series: List[TurnoverPoint]
    avg_top_turnover: float
    avg_bottom_turnover: float

# Updated metrics models with chart data
class ICMetrics(SQLModel):
    # ... basic metrics ...
    monthly_ic: Optional[List[Dict[str, Any]]]
    ic_distribution: Optional[ICDistribution]

class LongShortMetrics(SQLModel):
    # ... basic metrics ...
    cumulative_returns: Optional[List[CumulativeReturnPoint]]
    return_distribution: Optional[List[ReturnDistributionBin]]

class QualityMetrics(SQLModel):
    # ... basic metrics ...
    turnover: Optional[TurnoverData]
```

#### Metrics Calculation (`app/services/model_metrics_service.py`)

Key methods added:

- `_calculate_monthly_ic()`: Aggregates IC by year-month for heatmap
- `_calculate_ic_distribution()`: Creates histogram bins and Q-Q plot data
- `_calculate_turnover()`: Calculates daily Top/Bottom stock turnover

### Problems Encountered and Solutions

#### Problem 1: Charts Not Displaying

**Symptom**: New charts (Monthly IC, IC Distribution, etc.) not showing on frontend
**Root Cause**: Pydantic models (`ICMetrics`, `LongShortMetrics`, `QualityMetrics`) didn't include new fields
**Solution**: Added new Pydantic models and updated existing models with Optional chart data fields

#### Problem 2: API Returns Data But findstr Fails

**Symptom**: `curl ... | findstr "ic_distribution"` shows "line too long"
**Cause**: JSON response is a single long line, exceeds findstr's line limit
**Solution**: This actually confirms data is present; use `> file.json` to save and inspect

#### Problem 3: Chart Container Size -1

**Symptom**: Console shows "width(-1) and height(-1) of chart should be greater than 0"
**Cause**: Recharts ResponsiveContainer needs parent with defined dimensions
**Solution**: Ensure parent div has explicit height (e.g., `h-64` class)

### Frontend Implementation (`frontend/src/routes/_layout/models.tsx`)

Key components:

- `MonthlyICHeatmap`: Custom SVG-based heatmap component
- IC Distribution: Recharts BarChart
- Q-Q Plot: Recharts ScatterChart with reference line
- Cumulative Returns: Recharts AreaChart
- Turnover Analysis: Recharts LineChart with dual lines

### Lessons Learned

1. **Pydantic Model Sync**: When adding new fields to backend JSON, must update Pydantic models for API to return them
2. **Optional Fields**: Use `Optional[T] = Field(default=None)` for backward compatibility
3. **Chart Sizing**: Always provide explicit height for Recharts containers
4. **Data Validation**: PowerShell `findstr` has line length limits; use file output for large JSON

### Model Performance Interpretation

Current model metrics indicate weak predictive power:

- IC Mean ≈ -0.001 (should be > 0.03)
- ICIR ≈ -0.009 (should be > 0.5)
- Turnover ≈ 73% (should be < 30%)

**Potential Improvements**:

1. Add more factors (Alpha158 has 158 factors vs current 8)
2. Extend prediction horizon (predict 5-day returns instead of 1-day)
3. Add turnover penalty in strategy
4. Use more training data

---

## Backtest Page Implementation

**Date**: 2026-02-24

### Overview

The Backtest page provides comprehensive strategy backtesting functionality with risk analysis and visualization. It allows users to evaluate trading strategy performance using historical data.

### Architecture

```
Frontend (backtest.tsx)
    ↓ API Calls
Backend API (/api/v1/backtest/*)
    ↓
OnlineServingService.execute_backtest()
    ↓
Qlib backtest_func() + risk_analysis()
    ↓
Results with Risk Metrics + Chart Data
```

### Backend Implementation

#### New Router: `backend/app/api/routes/backtest.py`

Dedicated backtest router with 4 endpoints:

| Endpoint         | Method | Description                                        |
| ---------------- | ------ | -------------------------------------------------- |
| `/config`        | GET    | Get backtest configuration from YAML               |
| `/status`        | GET    | Check if backtest is ready (predictions available) |
| `/latest-result` | GET    | Get persisted latest backtest result               |
| `/run`           | POST   | Execute backtest and return results                |

#### Pydantic Models

```python
class RiskMetrics(BaseModel):
    annualized_return: Optional[float]  # Annualized return rate
    max_drawdown: Optional[float]       # Maximum drawdown
    sharpe_ratio: Optional[float]       # Risk-adjusted return (Information Ratio)
    volatility: Optional[float]         # Standard deviation of returns
    calmar_ratio: Optional[float]       # Annualized Return / Max Drawdown
    win_rate: Optional[float]           # Percentage of profitable days
    profit_loss_ratio: Optional[float]  # Avg gain / Avg loss

class BacktestRunResponse(BaseModel):
    status: str
    # Basic metrics
    total_return: Optional[float]
    net_return: Optional[float]
    total_cost: Optional[float]
    # Enhanced metrics
    risk_metrics: Optional[RiskMetrics]
    charts: Optional[Dict[str, Any]]
```

#### Risk Metrics Calculation (`online_serving_service.py`)

```python
def _calculate_risk_metrics(self, report_df, freq):
    # Use Qlib's risk_analysis - returns DataFrame with 'risk' column
    analysis_df = risk_analysis(returns, freq=freq)

    metrics = {
        "annualized_return": analysis_df.loc["annualized_return", "risk"],
        "max_drawdown": analysis_df.loc["max_drawdown", "risk"],
        "sharpe_ratio": analysis_df.loc["information_ratio", "risk"],
        "volatility": analysis_df.loc["std", "risk"],
    }

    # Additional calculated metrics
    metrics["calmar_ratio"] = annualized_return / |max_drawdown|
    metrics["win_rate"] = positive_days / total_days
    metrics["profit_loss_ratio"] = avg_gain / avg_loss
```

#### Chart Data Generation

```python
def _generate_backtest_charts(self, report_df, benchmark):
    charts = {
        "cumulative_returns": [...],  # Strategy vs Benchmark
        "return_distribution": [...],  # Histogram bins
        "max_drawdown_info": {
            "max_drawdown": float,
            "peak_date": str,
            "max_drawdown_date": str,
            "peak_value": float,
            "trough_value": float,
        }
    }
```

### Frontend Implementation

#### File: `frontend/src/routes/_layout/backtest.tsx`

**Key Components**:

1. **Strategy Configuration Card**: Displays backtest config from YAML
2. **Backtest Status Card**: Shows readiness and mutation status
3. **Backtest Results Card**: Basic metrics (trading days, returns, costs)
4. **Risk Metrics Card**: 7 risk indicators with tooltip explanations
5. **Cumulative Returns Chart**: AreaChart with max drawdown annotation
6. **Return Distribution Chart**: BarChart histogram

**MetricTooltip Component**:

```tsx
function MetricTooltip({ content }: { content: string }) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help ml-1" />
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[250px]">
          <p className="text-xs">{content}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
```

**Max Drawdown Visualization**:

- Orange vertical line: Peak date (start of drawdown)
- Red vertical line: Trough date (bottom of drawdown)
- Summary box below chart with drawdown details

### Risk Metrics Explained

| Metric                | Description                    | Good Value              |
| --------------------- | ------------------------------ | ----------------------- |
| **Annualized Return** | Yearly return rate             | > 0%                    |
| **Max Drawdown**      | Largest peak-to-trough decline | > -30%                  |
| **Sharpe Ratio**      | Risk-adjusted return           | > 1.0 (excellent > 2.0) |
| **Volatility**        | Return standard deviation      | Lower is more stable    |
| **Calmar Ratio**      | Return / Drawdown              | > 1.0                   |
| **Win Rate**          | % of profitable days           | > 50%                   |
| **Profit/Loss Ratio** | Avg win / Avg loss             | > 1.0                   |

### Problems Encountered and Solutions

#### Problem 1: Risk Metrics All Zero

**Symptom**: All risk metrics displayed as 0.00%
**Root Cause**: Qlib's `risk_analysis()` returns a DataFrame, not a dict
**Solution**:

```python
# Wrong: analysis.get("annualized_return", 0)
# Correct: analysis_df.loc["annualized_return", "risk"]
```

**Debugging Command**:

```powershell
docker exec quantbot-backend-1 python -c "from qlib.contrib.evaluate import risk_analysis; import pandas as pd; import numpy as np; returns = pd.Series(np.random.randn(100) * 0.01); result = risk_analysis(returns, freq='day'); print(type(result)); print(result)"
```

#### Problem 2: Confusing Drawdown Chart

**Symptom**: Separate drawdown chart showed every day as "losing"
**Root Cause**: Drawdown chart shows distance from historical high, not daily P&L
**Solution**: Removed separate drawdown chart, integrated max drawdown annotation into cumulative returns chart

**Best Practice for Drawdown Visualization**:

- Show drawdown on cumulative returns chart
- Mark peak (start) and trough (bottom) with vertical lines
- Display summary box with key dates and values

#### Problem 3: Trading Costs Display Precision

**Symptom**: `open_cost: 0.0003` displayed as `0`
**Root Cause**: `toLocaleString()` rounds small decimals
**Solution**:

```tsx
{
  value < 0.01 && value > 0 ? value.toFixed(4) : value.toLocaleString();
}
```

#### Problem 4: 404 Errors on Backtest API

**Symptom**: Frontend called `/api/v1/backtest/*` but got 404
**Root Cause**: Backend only had `/api/v1/online/backtest` endpoint
**Solution**: Created dedicated `/api/v1/backtest` router matching frontend expectations

### Lessons Learned

1. **Qlib API Return Types**: Always verify return types with test commands before assuming dict/DataFrame
2. **Drawdown Visualization**: Professional approach is to annotate on cumulative returns chart, not separate chart
3. **Tooltip for Complex Metrics**: Non-finance users need explanations; use hover tooltips
4. **API Design**: Frontend-first approach - design backend endpoints to match frontend needs
5. **Precision Display**: Small decimal values need special formatting (toFixed vs toLocaleString)

### Files Modified

**Backend**:

- `backend/app/api/routes/backtest.py` (new)
- `backend/app/api/main.py` (register router)
- `backend/app/services/online_serving_service.py` (add risk metrics + charts)
- `backend/app/api/routes/online.py` (remove redundant backtest endpoint)

**Frontend**:

- `frontend/src/routes/_layout/backtest.tsx` (complete rewrite)
- `frontend/src/components/Sidebar/AppSidebar.tsx` (rename Models → Model)
- `frontend/src/routes/_layout/models.tsx` (rename page title)

---

## Routine Page Implementation

### Overview

The Routine page provides a manual trigger for the daily routine task and displays execution status. The routine is typically executed after market close via scheduled tasks, but a manual trigger button is provided for testing and debugging.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Routine Page                                                │
├─────────────────────────────────────────────────────────────┤
│  [Run Routine Button]                                        │
├─────────────────────────────────────────────────────────────┤
│  Routine Execution Status                                    │
│  - Status: Completed / Running / Failed                      │
│  - Last Executed: timestamp                                  │
│  - Data Range: start_date ~ end_date                         │
│  - Signal Count: number                                      │
│  - Total Duration: seconds                                   │
│  - Step Details (table with duration and status)             │
└─────────────────────────────────────────────────────────────┘
```

### Backend API

Uses existing `/api/v1/online` endpoints:

- `POST /api/v1/online/routine` - Execute routine
- `GET /api/v1/online/status` - Get status

### Frontend Route

- Path: `/routine`
- File: `frontend/src/routes/_layout/routine.tsx`

### Implementation Status: COMPLETED

**Date**: 2026-02-24

**Features Implemented**:

1. **Status Overview Cards**:

   - Initialization status (Initialized/Not Initialized)
   - Last execution timestamp
   - Data range (start_date ~ end_date)
   - Signal count

2. **Run Routine Button**:

   - Manual trigger for routine execution
   - Loading state during execution
   - Success/error toast notifications

3. **Last Routine Result**:

   - Execution timestamp and total duration
   - Step-by-step results table with:
     - Step name (initialization, data_update, online_manager_routine, signal_generation, model_metrics_calculation)
     - Status badge (Success/Failed)
     - Duration in seconds
     - Details/error message

4. **Configuration Display**:
   - Shows current online serving configuration (experiment_name, rolling_step, rolling_type, etc.)

**Files Modified**:

- `frontend/src/routes/_layout/routine.tsx` (new)
- `frontend/src/components/Sidebar/AppSidebar.tsx` (add Routine menu item)
- `backend/app/api/routes/online.py` (add DataRange model, update StatusResponse)
- `backend/app/services/online_serving_service.py` (add data_range and signal_count to status)

**Bug Fixes**:

- Fixed recharts formatter type errors in `backtest.tsx` and `models.tsx` caused by stricter TypeScript types in recharts@3.7.0

---

## Paper Trading Page Implementation

### Overview

The Paper Trading page provides complete simulated trading functionality:

1. **Portfolio & Trades**: Execute trading, view holdings, today's trades
2. **Performance Analysis**: Risk metrics and charts based on paper trading history
3. **Notification Settings**: Email notification configuration

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Paper Trading Page                                          │
├─────────────────────────────────────────────────────────────┤
│  Part 1: Portfolio & Trades                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [Execute Trading Button]                             │    │
│  │                                                      │    │
│  │ Portfolio Summary                                    │    │
│  │ - Total Value, Cash, Positions Count                 │    │
│  │ - Total P/L, Today P/L, Total Cost                   │    │
│  │                                                      │    │
│  │ Current Holdings (table)                             │    │
│  │ - Stock, Shares, Cost, Current, P/L                  │    │
│  │                                                      │    │
│  │ Today's Trades (table with Export CSV)               │    │
│  │ - Stock, Action, Shares, Price, Weight               │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  Part 2: Performance Analysis                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Paper Trading Period: start ~ end                    │    │
│  │ Trading Days: count                                  │    │
│  │ Warning if < 30 days                                 │    │
│  │                                                      │    │
│  │ Risk Metrics (based on paper trading period)         │    │
│  │ - Annualized Return, Max Drawdown, Sharpe Ratio      │    │
│  │                                                      │    │
│  │ Cumulative Returns Chart (Strategy vs Benchmark)     │    │
│  │ Turnover Chart                                       │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  Part 3: Notification Settings                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Enable Email Notification (toggle)                   │    │
│  │ Recipients (list with add/remove)                    │    │
│  │ [Test Email] [Save Settings]                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Backend API Design

New router: `/api/v1/paper-trading`

| Endpoint               | Method | Description                |
| ---------------------- | ------ | -------------------------- |
| `/status`              | GET    | Get paper trading status   |
| `/execute`             | POST   | Execute simulated trading  |
| `/portfolio`           | GET    | Get current holdings       |
| `/trades`              | GET    | Get trade history          |
| `/trades/export`       | GET    | Export trades as CSV       |
| `/performance`         | GET    | Get performance analysis   |
| `/notification/config` | GET    | Get notification config    |
| `/notification/config` | PUT    | Update notification config |
| `/notification/test`   | POST   | Send test email            |

### Data Persistence

| Data                | Location                                       | Format |
| ------------------- | ---------------------------------------------- | ------ |
| Portfolio state     | `mlruns/paper_trading/portfolio.json`          | JSON   |
| Trade history       | `mlruns/paper_trading/trades.json`             | JSON   |
| Daily reports       | `mlruns/paper_trading/reports/YYYY-MM-DD.json` | JSON   |
| Notification config | `config/notification.yaml`                     | YAML   |

### Today's Trades Fields

| Field  | Description      | Example                                             |
| ------ | ---------------- | --------------------------------------------------- |
| Stock  | Stock code       | SH600519                                            |
| Action | Trade action     | BUY / SELL / HOLD                                   |
| Shares | Number of shares | 100                                                 |
| Price  | Execution price  | 1850.0                                              |
| Weight | Target weight    | → 2.00% (buy to), = 2.00% (hold), → 0.00% (sell to) |

### Risk Metrics (Qlib-based)

| Metric      | Calculation Basis    | Description            |
| ----------- | -------------------- | ---------------------- |
| Ann. Return | Paper trading period | Annualized return rate |
| Max DD      | Paper trading period | Maximum drawdown       |
| Sharpe      | Paper trading period | Sharpe ratio           |

Note: If trading days < 30, display warning "Insufficient data, metrics for reference only"

### Frontend Route

- Path: `/paper-trading`
- File: `frontend/src/routes/_layout/paper-trading.tsx`

### Implementation Phases

| Phase   | Features                                                               |
| ------- | ---------------------------------------------------------------------- |
| Phase 1 | Routine page (execution status display)                                |
| Phase 2 | Paper Trading basics (execute, portfolio, today's trades + CSV export) |
| Phase 3 | Paper Trading analysis (risk metrics, charts)                          |
| Phase 4 | Email notification (config, send)                                      |

---

## Paper Trading Implementation Complete (2026-02-24)

### Features Implemented

#### Backend API (`/api/v1/paper-trading`)

| Endpoint       | Method | Description                                     |
| -------------- | ------ | ----------------------------------------------- |
| `/plan`        | POST   | Generate trading plan with last executed trades |
| `/execute`     | POST   | Execute simulated trading based on signals      |
| `/portfolio`   | GET    | Get current portfolio holdings                  |
| `/trades`      | GET    | Get trade history                               |
| `/performance` | GET    | Get performance metrics                         |
| `/reset`       | POST   | Reset paper trading state                       |

#### Trading Plan Features

- **Percentage-based orders**: Uses `target_weight` (% of total assets) for buys and `sell_pct` (% of position) for sells
- **TopkDropout Strategy**: Holds top K stocks, drops N worst performers daily
- **Last Executed Trades**: Shows most recent executed trades even when Online Serving is not initialized
- **Trading Plan in Execute Response**: Returns the generated trading plan along with execution results

#### Performance Metrics

| Metric              | Description                               |
| ------------------- | ----------------------------------------- |
| `total_return`      | Total return since inception              |
| `annualized_return` | Annualized return (CAGR formula)          |
| `max_drawdown`      | Maximum drawdown from peak                |
| `sharpe_ratio`      | Sharpe ratio (requires >= 2 trading days) |
| `win_rate`          | Win rate for sell trades                  |
| `trading_days`      | Number of trading days                    |

#### Frontend Features

1. **Performance Metrics Card**: Displays initial cash, current value, cumulative return, annualized return, max drawdown, Sharpe ratio, trading days, position count

2. **Trading Plan Tab**:

   - Shows pending orders (sell/buy/hold) when Online Serving is initialized
   - Shows last executed trades when Online Serving is not initialized
   - Order summary with executed sells/buys count

3. **Portfolio Tab**: Current holdings with instrument, shares, average cost, current value

4. **Trade History Tab**: Complete trade history with filtering

5. **Execute Button**: Triggers simulated trading with loading state and error handling

6. **Reset Button**: Resets all paper trading state (portfolio, trades, daily records)

### Data Persistence

| Data            | File Path                                 |
| --------------- | ----------------------------------------- |
| Portfolio       | `/app/paper_trading/portfolio.json`       |
| Trades          | `/app/paper_trading/trades.json`          |
| Daily Records   | `/app/paper_trading/daily_records.json`   |
| Trading Started | `/app/paper_trading/trading_started.json` |

### Key Implementation Details

1. **Initial Cash**: 10,000,000 (configurable via `qlib_config.initial_cash`)

2. **Slippage Model**: 0.1% default slippage applied to execution prices

3. **State Management**:

   - `trading_started.json` tracks if paper trading has been initiated
   - Reset clears all state files and marks trading as not started

4. **Error Handling**:
   - Returns `last_executed_trades` even when Online Serving is not initialized
   - Graceful handling of edge cases (single trading day, zero return, etc.)

### Files Modified

**Backend**:

- `backend/app/api/routes/paper_trading.py` - API routes and response models
- `backend/app/services/paper_trading_service.py` - Business logic

**Frontend**:

- `frontend/src/routes/_layout/paper-trading.tsx` - Paper Trading page component

---

## Email Notification Feature (2026-02-24)

### Overview

Implemented email notification system for Paper Trading that automatically sends trading plan emails after successful trade execution.

### Features

1. **Notification Configuration API**

   - GET/PUT `/api/v1/paper-trading/notification/config` - Manage notification settings
   - POST `/api/v1/paper-trading/notification/recipient` - Add email recipient
   - DELETE `/api/v1/paper-trading/notification/recipient` - Remove recipient
   - POST `/api/v1/paper-trading/notification/test` - Send test email

2. **Automatic Email on Execute**

   - Trading plan email sent automatically after successful trade execution
   - Only sent for non-dry-run executions
   - Includes detailed buy/sell orders with target weights and reference prices

3. **Email Content**
   - Subject: `QuantBot: Trading Plan {date}`
   - HTML formatted with styled tables
   - Sell orders with sell percentage and reason
   - Buy orders with target weight (%), reference price, and score
   - Portfolio summary (total value, cash)
   - Execution summary (sells/buys executed count)

### SMTP Configuration

Configured via `.env` file (gitignored for security):

```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_authorization_code
SMTP_SSL=True
EMAILS_FROM_EMAIL=your_email@qq.com
```

### Docker Compose Configuration

Updated `docker-compose.override.yml`:

- Uses environment variable substitution for SMTP settings
- Added DNS servers (223.5.5.5, 114.114.114.114) for container DNS resolution
- Added `smtp.qq.com` to `NO_PROXY` to bypass proxy for SMTP connections

### Files Modified

**Backend**:

- `backend/app/services/notification_service.py` - NotificationService with email sending logic
- `backend/app/api/routes/paper_trading.py` - Added notification endpoints and execute integration

**Configuration**:

- `.env` - SMTP configuration (gitignored)
- `docker-compose.override.yml` - Docker environment variables and DNS settings

### API Response Examples

**Get Notification Config**:

```json
{
  "success": true,
  "config": {
    "enabled": true,
    "recipients": ["user@example.com"],
    "smtp_host": "smtp.qq.com",
    "smtp_port": 465,
    "smtp_user": "sender@qq.com",
    "smtp_tls": false,
    "from_email": "sender@qq.com",
    "from_name": "QuantBot"
  }
}
```

**Execute Response with Email**:

```
INFO:app.utils:send email result: <emails.backend.SMTPResponse status_code=250 status_text=b'OK: queued as.'>
INFO:app.api.routes.paper_trading:Trading plan email sent: Trading plan sent to 1 recipients
```

---
