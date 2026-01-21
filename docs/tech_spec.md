# 量化交易系统技术规格文档

## 项目概述

本项目旨在结合Microsoft Qlib和FastAPI Full Stack Template，开发一个完整的AI驱动量化投资平台。系统将提供从数据处理到策略执行的全流程量化投资解决方案。

### 核心目标

- 构建基于AI的量化投资研究平台
- 提供完整的量化投资工作流程
- 支持多种机器学习范式（监督学习、强化学习、市场动态建模）
- 实现从研究到生产的端到端解决方案

## 技术栈分析

### 当前FastAPI Full Stack Template技术栈

- **后端**: FastAPI + SQLModel + Pydantic + PostgreSQL
- **前端**: React + TypeScript + Vite + TailwindCSS + shadcn/ui
- **部署**: Docker Compose + Traefik
- **认证**: JWT认证 + 安全密码哈希
- **测试**: Pytest + Playwright

### Qlib核心功能

- **数据处理**: 高性能时序数据存储和处理引擎
- **因子挖掘**: Alpha158、Alpha360等因子库
- **模型构建**: 支持LightGBM、Transformer、TCN、ADARNN等多种模型
- **策略研发**: 完整的策略开发框架
- **回测系统**: 高性能回测引擎
- **强化学习**: 支持连续决策建模
- **市场动态适应**: 处理金融市场非平稳性

## 系统功能规划

### 1. 数据管理模块

- **数据源接入**: 支持多种数据源（Yahoo Finance、tushare、akshare、本地数据等）
- **数据清洗**: 自动化数据质量检查和清洗
- **数据存储**: 高性能时序数据库
- **数据API**: RESTful API提供数据访问接口
- **数据共享**: 所有用户都可以访问和管理数据源

### 2. 因子工程模块

- **因子计算**: 基于Qlib的因子计算引擎
- **因子评估**: 因子有效性分析和评估
- **因子管理**: 因子库管理和版本控制
- **自定义因子**: 支持用户自定义因子开发

### 3. 模型开发模块

- **模型训练**: 支持多种机器学习模型
- **模型评估**: 模型性能评估和比较
- **模型管理**: 模型版本控制和部署管理
- **AutoML**: 自动化模型选择和调参

### 4. 策略研发模块

- **策略开发**: 可视化策略开发界面
- **策略回测**: 高性能回测引擎
- **策略优化**: 参数优化和策略改进
- **策略组合**: 多策略组合管理

### 5. 交易执行模块

- **模拟交易**: 模拟盘交易环境
- **信号发布**: 交易信号生成和发布
- **风险控制**: 实时风险监控和控制
- **执行分析**: 交易执行效果分析

### 6. 监控分析模块

- **实时监控**: 策略和模型实时监控
- **性能分析**: 收益、风险、回撤等指标分析
- **报告生成**: 自动化报告生成
- **告警系统**: 异常情况告警

## 用户访问设计

### 统一用户模式

系统采用统一用户访问模式，所有注册用户都可以访问全部功能模块：

**核心功能访问**:

- **数据管理**: 所有用户都可以配置和管理数据源
- **因子工程**: 所有用户都可以进行因子挖掘和开发
- **模型开发**: 所有用户都可以训练和管理机器学习模型
- **策略研发**: 所有用户都可以开发策略和进行回测
- **交易执行**: 所有用户都可以使用模拟交易功能
- **监控分析**: 所有用户都可以查看实时监控和分析报告

**设计优势**:

- **简化权限管理**: 无需复杂的角色权限控制逻辑
- **提升用户体验**: 用户可以自由探索所有功能
- **降低开发复杂度**: 减少权限相关的代码和测试工作
- **便于协作**: 团队成员可以无障碍地协作和分享

## 数据源集成方案

### 支持的数据源

1. **Yahoo Finance**

   - 免费数据源，适合开发测试
   - 支持全球主要市场股票数据
   - 实时和历史数据获取

2. **Tushare**

   - 中国金融数据专业接口
   - 支持A股、港股、美股等市场数据
   - 提供基本面、技术面、宏观经济数据

3. **AkShare**

   - 开源金融数据接口库
   - 覆盖股票、期货、期权、基金等
   - 支持多种数据格式和频率

4. **本地数据**
   - 支持CSV、Excel等格式导入
   - 自定义数据源接入
   - 历史数据备份和恢复

### 数据源管理

- **统一数据接口**: 封装不同数据源的API差异
- **数据缓存策略**: 减少重复请求，提高性能
- **数据质量监控**: 自动检测数据异常和缺失
- **数据更新机制**: 定时更新和实时数据推送

## 系统架构设计

### 整体架构

```
前端层 (React + TypeScript)
├── 数据管理界面
├── 因子工程界面
├── 模型开发界面
├── 策略研发界面
├── 交易监控界面
└── 分析报告界面

API网关层 (FastAPI)
├── 认证授权
├── 请求路由
├── 数据验证
└── 错误处理

业务逻辑层
├── 数据服务
├── 因子服务
├── 模型服务
├── 策略服务
├── 交易服务
└── 分析服务

Qlib集成层
├── 数据处理引擎
├── 因子计算引擎
├── 模型训练引擎
├── 回测引擎
└── 强化学习引擎

数据存储层
├── PostgreSQL (用户数据、配置数据)
├── Qlib数据存储 (时序数据、因子数据)
├── Redis (缓存、会话管理)
└── 文件存储 (模型文件、报告文件)
```

## 部署方案

### Docker部署架构

基于FastAPI Full Stack Template的Docker部署方案：

```yaml
services:
  frontend: # React前端
  backend: # FastAPI后端
  db: # PostgreSQL数据库
  redis: # Redis缓存
  qlib-data: # Qlib数据服务
  traefik: # 反向代理
```

### 环境配置

- **开发环境**: Docker Compose本地开发
- **测试环境**: 容器化测试部署
- **生产环境**: Docker Swarm或Kubernetes部署
- **监控**: 集成Prometheus + Grafana

## 开发计划

### 阶段一：基础架构搭建 (2-3周)

#### 第1周：环境搭建和基础集成

1. **Qlib环境搭建**

   - 在Docker容器中安装和配置Qlib
   - 集成Qlib到FastAPI项目
   - 配置Qlib数据存储路径

2. **数据源集成准备**
   - 安装tushare、akshare依赖
   - 配置API密钥管理
   - 设计数据源适配器接口

#### 第2周：数据模型扩展

1. **量化业务模型**

   - 设计数据源配置模型
   - 设计因子库管理模型
   - 设计策略和模型管理模型
   - 设计用户偏好和配置模型

#### 第3周：基础API和前端框架

1. **API接口开发**

   - 开发数据源管理API
   - 开发基础的Qlib集成API
   - 实现用户偏好设置API

2. **前端框架搭建**
   - 设计统一的用户界面布局
   - 实现基础的导航和功能模块
   - 搭建数据管理页面框架

### 阶段二：数据管理模块 (2-3周)

1. 数据源接入功能
2. 数据清洗和质量检查
3. 数据存储和管理
4. 数据API开发
5. 数据管理前端界面

### 阶段三：因子工程模块 (3-4周)

1. 因子计算引擎集成
2. 因子评估功能
3. 因子管理API
4. 因子工程前端界面

### 阶段四：模型开发模块 (3-4周)

1. 模型训练接口
2. 模型评估功能
3. 模型管理系统
4. 模型开发前端界面

### 阶段五：策略研发模块 (4-5周)

1. 策略开发框架
2. 回测系统集成
3. 策略管理功能
4. 策略研发前端界面

### 阶段六：交易执行模块 (3-4周)

1. 模拟交易系统
2. 信号发布功能
3. 风险控制系统
4. 交易监控界面

### 阶段七：监控分析模块 (2-3周)

1. 实时监控系统
2. 性能分析功能
3. 报告生成系统
4. 告警系统

### 阶段八：系统优化和测试 (2-3周)

1. 性能优化
2. 系统测试
3. 文档完善
4. 部署准备

## 技术难点和解决方案

### 1. Qlib与FastAPI集成

- **难点**: 两个框架的数据模型和API设计差异
- **解决方案**: 设计适配层，统一数据接口和模型转换

### 2. 高性能数据处理

- **难点**: 大量时序数据的存储和计算性能
- **解决方案**: 利用Qlib的高性能数据引擎，结合缓存策略

### 3. 实时性要求

- **难点**: 实时数据处理和信号发布的延迟控制
- **解决方案**: 异步处理架构，WebSocket实时通信

### 4. 系统稳定性

- **难点**: 7x24小时稳定运行要求
- **解决方案**: 完善的监控告警，自动恢复机制

## 第一阶段详细任务清单

### Docker和环境配置

- [ ] 更新docker-compose.yml，添加Qlib服务容器
- [ ] 配置Qlib数据存储卷映射
- [ ] 安装Python量化相关依赖（qlib, tushare, akshare）
- [ ] 配置环境变量管理（API密钥等）

### 后端开发任务

- [x] 简化User模型，移除角色字段
- [ ] 创建DataSource模型（管理数据源配置）
- [ ] 创建Factor模型（因子库管理）
- [ ] 创建Strategy模型（策略管理）
- [ ] 创建Model模型（机器学习模型管理）
- [ ] 开发数据源管理API路由
- [ ] 开发Qlib集成服务层

### 前端开发任务

- [ ] 设计统一Dashboard布局
- [ ] 创建数据源管理页面
- [ ] 创建用户偏好设置页面
- [ ] 设计量化系统专用组件库

### 测试和文档

- [ ] 编写单元测试（后端API）
- [ ] 编写集成测试（Qlib集成）
- [ ] 更新API文档
- [ ] 编写部署文档

## 下一步行动

1. ✅ 确认功能需求和优先级
2. ✅ 详细设计数据模型
3. ✅ 制定详细的开发时间表
4. ✅ 搭建开发环境（第一阶段第1周）
5. 🔄 开始第一阶段开发工作

### 当前开发状态 (2026年1月13日)

✅ **基础环境搭建完成**

- Docker环境稳定运行
- FastAPI后端正常启动，日志输出正常
- Swagger UI可访问 (http://localhost:8000/docs)
- 所有服务容器健康运行
- 代码库基础版本已提交

✅ **已完成的工作**

- 深入研究Qlib完整HTML文档
- 理解Qlib四层架构和核心工作流程
- 掌握Qlib数据处理、特征工程、模型训练、策略回测全流程

✅ **Qlib环境搭建完成 (2026年1月13日 22:35)**

- 成功添加Qlib相关依赖到pyproject.toml
- 重新构建Docker容器，安装所有量化依赖
- 验证Qlib 0.9.7安装成功
- 测试所有核心依赖正常工作：pandas, numpy, lightgbm, torch, sklearn
- Qlib环境完全就绪，可以开始数据模型开发

✅ **DataSource模块开发完成 (2026年1月14日 00:27)**

- 设计并实现DataSource数据模型（支持5种数据源类型）
- 创建数据库迁移并成功执行
- 开发完整的CRUD API路由
- 通过Swagger UI测试所有API端点（创建、查询、更新）
- 所有用户可以增删改查所有数据源（管理员模式）

✅ **Factor模块开发完成 (2026年1月14日 01:04)**

- 深入研究Qlib因子系统和Alpha158因子库
- 设计并实现Factor数据模型（支持4种因子类别）
- 因子不绑定特定数据源，符合Qlib设计理念
- 创建数据库迁移并成功执行
- 开发完整的CRUD API路由
- 通过Swagger UI测试所有API端点（创建、更新）
- 支持Qlib表达式格式的因子定义

✅ **Model模块开发完成 (2026年1月15日 06:30)**

- 深入理解Qlib模型系统和预测分数生成流程
- 明确系统架构：各模块完全独立，回测时由用户自由组合
- 设计并实现MLModel数据模型（支持3种状态：TRAINED/OUTDATED/UNTRAINED）
- 模型不绑定因子，因子不绑定数据源，策略不绑定模型
- 创建数据库迁移并成功执行，创建mlmodel表
- 开发完整的CRUD API路由
- 通过Swagger UI测试所有API端点（创建、查询、更新、删除）
- 支持Qlib内置模型类（如：qlib.contrib.model.gbdt.LGBModel）

✅ **Strategy模块开发完成 (2026年1月15日 07:51)**

- 深入研究Qlib策略系统和Portfolio Strategy工作流程
- 设计并实现Strategy数据模型（支持2种状态：ACTIVE/INACTIVE）
- 策略完全独立，不绑定模型、因子或数据源
- 创建数据库迁移并成功执行，创建strategy表
- 开发完整的CRUD API路由
- 通过Swagger UI测试所有API端点（创建、查询、更新、删除）
- 支持Qlib内置策略类（如：qlib.contrib.strategy.TopkDropoutStrategy）
- 使用class_path + config JSON配置策略参数

🔄 **正在进行的任务 (2026年1月15日 08:13)**

**Backtest（回测）模块设计和开发**

### Backtest模块设计方案

#### 1. 核心设计理念

Based on Qlib documentation research, the backtest module is the core execution layer of the entire quantitative system. It combines all user-configured components (data source, factors, model, strategy) to execute the complete backtest workflow.

**Qlib Backtest Workflow:**

```
Data Loading → Factor Calculation → Model Training/Prediction → Strategy Execution → Backtest Analysis
     ↓               ↓                      ↓                         ↓                    ↓
DataSource  →    Factor      →      Model.predict        →      Strategy      →   backtest_daily
```

#### 2. Data Storage Strategy

**Raw Data (DataSource):**

- **Network API data (tushare/akshare)**: NOT stored in DB, fetched in real-time and cached in memory
- **Local data**: Read directly from Qlib data directory
- **Rationale**: Avoid data redundancy, maintain data freshness, reduce storage costs

**Computed Results (Factor):**

- **Factor values**: Store in dedicated factor data table (to be implemented)
- **Format**: Time-series data, support fast query and reuse
- **Rationale**: Factor calculation is time-consuming, caching significantly improves performance

**Backtest Results:**

- **Performance metrics summary**: Store in `backtest.result_summary` field (JSON format)
- **Detailed reports**: Store in file system `storage/backtests/{backtest_id}/`
  - `report.csv` - Daily return report (return, bench, cost, etc.)
  - `positions.csv` - Position records
  - `metrics.json` - Complete performance metrics (annualized return, Sharpe ratio, max drawdown, etc.)
- **Rationale**: Database stores key metrics for querying, file system stores detailed data for download and analysis

#### 3. Asynchronous Execution Solution

**Problem Analysis:**
Backtest tasks take considerable time (several minutes to tens of minutes):

- Data loading and preprocessing (10-30 seconds)
- Factor calculation (30 seconds - 2 minutes)
- Model training (if needed, 1-10 minutes)
- Backtest execution (1-5 minutes)

**Solution: Background Tasks + Progress Tracking**

Use Python's built-in `concurrent.futures.ThreadPoolExecutor` for async execution:

```python
# State machine
PENDING → RUNNING → COMPLETED/FAILED

# Progress tracking (0-100%)
0%   - Task created
20%  - Data loading completed
40%  - Factor calculation completed
60%  - Model training/loading completed
80%  - Backtest execution completed
100% - Results saved
```

**Frontend Display:**

- Return task ID immediately after creating backtest
- Frontend polls `/backtests/{id}` to get status and progress
- Display progress bar and current step description
- Show result summary and download link when completed

#### 4. Qlib Initialization Solution

**Configuration Management:**

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    QLIB_DATA_PATH: str = "./qlib_data"  # Qlib data directory
    QLIB_REGION: str = "cn"  # Market region (cn/us)
    QLIB_CACHE_PATH: str = "./qlib_cache"  # Cache directory
```

**Initialization Strategy:**

- Each backtest task initializes Qlib independently (avoid conflicts)
- Use user-selected data source configuration
- Support switching between multiple data sources

#### 5. Factor Calculation Solution

**User-defined factor expressions → Qlib DataHandler:**

```python
# Factor expressions defined by user in Factor table
factor_expressions = [
    "$close / $open - 1",           # Intraday return
    "Mean($close, 5)",              # 5-day moving average
    "$volume / Mean($volume, 20)"   # Volume ratio
]

# System dynamically builds Qlib DataHandler
class CustomHandler(DataHandlerLP):
    def __init__(self, instruments, start_time, end_time, factor_expressions):
        self.factor_exprs = factor_expressions
        super().__init__(instruments, start_time, end_time)

    def get_feature_config(self):
        # Convert factor expressions to Qlib format
        return [(expr, expr) for expr in self.factor_exprs]
```

#### 6. Data Model Design

```python
class BacktestStatus(str, Enum):
    PENDING = "pending"      # Waiting for execution
    RUNNING = "running"      # Executing
    COMPLETED = "completed"  # Completed
    FAILED = "failed"        # Failed

class Backtest(SQLModel, table=True):
    id: uuid.UUID
    name: str  # Backtest name
    description: str | None  # Backtest description

    # Associated components (user freely selects)
    strategy_id: uuid.UUID  # Required: which strategy to use
    model_id: uuid.UUID | None  # Optional: which model to use
    factor_ids: str  # JSON array: which factors to use
    datasource_id: uuid.UUID  # Required: which data source to use

    # Backtest configuration
    start_time: str  # Backtest start time (e.g., 2017-01-01)
    end_time: str    # Backtest end time (e.g., 2020-08-01)
    benchmark: str   # Benchmark index (e.g., SH000300)
    initial_capital: float  # Initial capital (e.g., 100000000)

    # Trading configuration (JSON string)
    exchange_config: str  # Contains trading costs, limit thresholds, etc.
    # Example: {"limit_threshold": 0.095, "deal_price": "close",
    #           "open_cost": 0.0005, "close_cost": 0.0015, "min_cost": 5}

    # Execution mode
    retrain_model: bool  # Whether to retrain the model

    # Status and results
    status: BacktestStatus
    progress: int  # Execution progress (0-100)
    current_step: str | None  # Current step description
    result_summary: str | None  # JSON format performance metrics summary
    result_file_path: str | None  # Detailed result file path
    error_message: str | None  # Error message

    # Timestamps
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None  # Execution start time
    completed_at: datetime | None  # Completion time
    created_by: uuid.UUID
```

#### 7. API Endpoint Design

```
POST   /api/v1/backtests/          - Create backtest task
GET    /api/v1/backtests/          - Get all backtest list
GET    /api/v1/backtests/{id}      - Get backtest details (with status and progress)
POST   /api/v1/backtests/{id}/execute  - Execute backtest (async)
GET    /api/v1/backtests/{id}/results  - Get backtest results
DELETE /api/v1/backtests/{id}      - Delete backtest
```

#### 8. Execution Flow

```python
# 1. User creates backtest configuration (select strategy, model, factors, data source, time range, etc.)
# 2. System validates all components exist and are valid
# 3. Create backtest record, set status to PENDING
# 4. User calls execute endpoint, system submits to background task queue
# 5. Background task execution:
#    a. Update status to RUNNING, progress 0%
#    b. Initialize Qlib (progress 10%)
#    c. Load data source (progress 20%)
#    d. Calculate factors (progress 40%)
#    e. Train/load model (progress 60%)
#    f. Generate prediction scores (progress 70%)
#    g. Execute strategy backtest (progress 80%)
#    h. Calculate performance metrics (progress 90%)
#    i. Save result files (progress 95%)
#    j. Update database record (progress 100%)
# 6. Frontend polls to get status and progress, display progress bar
# 7. Show result summary and download link when completed
```

#### 9. Development Steps

1. ✅ Research Qlib backtest documentation and workflow
2. ✅ Design complete Backtest module architecture
3. ⏳ Add Backtest data model to `models.py`
4. ⏳ Create database migration
5. ⏳ Create Backtest API route file
6. ⏳ Register routes to main application
7. ⏳ Test CRUD API via Swagger UI
8. ⏳ Implement backtest execution engine
9. ⏳ Test complete backtest workflow
10. ⏳ Commit code

📋 **Next Tasks**

1. Develop frontend data management interface

📋 **后续功能规划**

1. **自定义策略上传功能**（重要）

   - 用户可以编写自定义策略类（继承BaseStrategy或WeightStrategyBase）
   - 通过Web界面上传Python代码
   - 系统自动解析策略类的参数需求和依赖
   - 动态加载和验证自定义策略
   - 提供策略模板和开发文档

2. **智能策略配置界面**

   - 选择策略后自动显示所需参数
   - 自动显示策略依赖的模型/因子类型
   - 参数验证和默认值提示
   - 策略参数说明和示例

3. **策略性能分析和优化**
   - 策略参数优化（网格搜索、贝叶斯优化）
   - 多策略对比分析
   - 策略组合和集成

---

## 🔄 重大架构调整 (2026年1月15日 10:45)

### 架构重构：三模块分离设计

经过深入讨论，我们决定对系统架构进行重大调整，将**因子计算、模型训练、回测推理**分离为三个独立的任务模块。

#### 调整原因

**原设计问题：**

1. `MLModel` 表既存储模型定义，又存储训练结果（`model_file_path`, `status`），职责不清
2. 每次回测都需要重新训练模型，速度慢，不适合模拟盘场景
3. 无法灵活地用不同训练集训练多个模型版本
4. 无法复用训练好的模型进行多次回测

**新架构优势：**

1. **性能优化**：因子计算一次多次复用，模型训练一次多次推理，回测速度极快
2. **灵活性**：用户完全控制每个环节，可以用不同训练集训练多个模型版本
3. **可追溯性**：每个任务独立记录，清晰的数据血缘关系
4. **商业化潜力**：因子数据和训练好的模型可以通过API对外售卖

#### 新架构工作流程

```
User Workflow:
  Step 1: Create Model Definition (MLModel)
  Step 2: Create Training Task (ModelTraining) → trained_model.pkl
  Step 3: Create Backtest Task (Backtest) → performance results
  Step 4: Reuse trained model for multiple backtests
```

#### 模块重构计划

**1. MLModel 重构**

- 移除 `model_file_path` 和 `status` 字段
- 只存储模型定义/模板（class_path + default config）
- 一个 MLModel 可以对应多个 ModelTraining

**2. ModelTraining 新增**

- 存储训练任务和结果
- 关联 `model_id`（使用哪个模型定义）
- 关联 `factor_ids`（使用哪些因子）
- 训练/验证时间段配置
- 训练状态和进度跟踪
- 训练结果：`model_file_path`, `training_metrics`

**3. Backtest 调整**

- 关联 `model_training_id`（使用哪个训练好的模型）
- 关联 `strategy_id`（使用哪个策略）
- 只做推理，不训练模型
- 快速执行，适合模拟盘

#### 重构步骤

**Phase 1: MLModel 重构（已完成 2026-01-15）**

1. ✅ 更新 tech_spec.md 记录架构调整
2. ✅ 重构 MLModel 数据模型（移除 model_file_path 和 status）
3. ✅ 更新 MLModel API 路由（无需修改，自动适配）
4. ✅ 创建数据库迁移修改 mlmodel 表
5. ✅ 执行数据库迁移
6. ✅ 测试 MLModel API 确保正常
7. ✅ 提交代码：MLModel 重构完成

**Phase 2: 新模块开发（已完成 2026-01-16）**

8. ✅ 添加 ModelTraining 数据模型到 models.py
9. ✅ 添加 Backtest 数据模型到 models.py
10. ✅ 更新 User 模型关系
11. ✅ 创建数据库迁移添加新表（迁移文件：77f04ed09ace）
12. ✅ 执行数据库迁移
13. ✅ 开发 ModelTraining API 路由（/api/model-trainings）
14. ✅ 开发 Backtest API 路由（/api/backtests）
15. ✅ 注册 API 路由到主路由器
16. ✅ 通过 Swagger UI 测试 API（全部通过）
17. ✅ 提交代码：新架构完全就绪

**测试结果：**

- ModelTraining API 测试通过（创建任务 ID: 558eef06-a0c7-4a36-9113-12c05b506980）
- Backtest API 测试通过（创建任务 ID: fc137d05-f0c3-4bce-91a6-5095864c6f94）
- 所有 CRUD 操作正常
- 外键关联正确
- 数据验证正常

**新增文件：**

- `backend/app/api/routes/model_trainings.py` - ModelTraining API 路由
- `backend/app/api/routes/backtests.py` - Backtest API 路由
- `backend/app/alembic/versions/77f04ed09ace_add_modeltraining_and_backtest_tables.py` - 数据库迁移文件

**修改文件：**

- `backend/app/models.py` - 添加 ModelTraining 和 Backtest 数据模型，更新 User 关系
- `backend/app/api/main.py` - 注册新的 API 路由

**下一步计划（Phase 3）：**

- 开发 ModelTraining 执行引擎（调用 Qlib 进行模型训练）
- 开发 Backtest 执行引擎（调用 Qlib 进行回测）
- 添加任务队列和异步执行机制
- 开发前端页面

---

## Qlib深度理解总结 (2026年1月13日)

### Qlib四层架构

基于完整文档研究，Qlib采用四层架构设计：

**1. Infrastructure Layer (基础设施层)**

- **DataServer**: 高性能时序数据存储和检索
- **Trainer**: 灵活的模型训练过程控制
- **Redis**: 缓存和锁机制支持
- **MongoDB**: 任务管理和集群处理支持

**2. Learning Framework Layer (学习框架层)**

- **监督学习**: 支持LightGBM、MLP、LSTM、Transformer等模型
- **强化学习**: 支持连续决策建模和策略优化
- **模型训练**: 统一的模型训练和评估框架

**3. Workflow Layer (工作流层)**

- **Information Extractor**: 数据特征提取
- **Forecast Model**: 预测信号生成（alpha、risk等）
- **Decision Generator**: 交易决策生成（组合、订单）
- **Execution Env**: 交易执行环境
- **Strategy**: 多层次策略嵌套支持

**4. Interface Layer (接口层)**

- **Analyser**: 详细的分析报告生成
- **用户友好的API接口**

### Qlib核心工作流程

**数据处理流程：**

1. **数据准备**: 下载原始数据并转换为Qlib格式(.bin文件)
2. **特征工程**: 使用表达式引擎创建特征 (如 "Ref($close, 60) / $close")
3. **数据处理**: 通过processors进行复杂处理(标准化、归一化等)
4. **数据集准备**: 为机器学习模型准备特定格式的数据集

**量化投资流程：**

1. **数据获取**: 通过DataServer获取高质量时序数据
2. **因子计算**: 使用表达式引擎计算Alpha158、Alpha360等因子
3. **模型训练**: 训练预测模型生成交易信号
4. **策略执行**: 基于信号生成投资组合和交易决策
5. **回测分析**: 评估策略性能和风险指标

### 我们系统的定位

**核心价值主张：**

我们的系统本质上是为Qlib添加一个完整的Web前端界面，让用户通过浏览器来使用Qlib的所有功能，而不需要写Python代码。

**系统架构映射：**

- **前端界面** ↔ **Qlib Interface Layer**
- **FastAPI后端** ↔ **Qlib Workflow Layer**
- **数据模型** ↔ **Qlib Learning Framework Layer**
- **Qlib集成** ↔ **Qlib Infrastructure Layer**

---

_文档创建时间: 2026年1月8日_
_最后更新时间: 2026年1月14日_

## 更新日志

### 2026年1月14日

- **完成DataSource模块开发**:

  - 实现DataSource数据模型（支持5种数据源类型：Yahoo Finance、Tushare、AkShare、本地文件、自定义API）
  - 创建并执行数据库迁移，成功创建datasource表
  - 开发完整的CRUD API路由（创建、读取、更新、删除）
  - 通过Swagger UI验证所有API功能正常
  - 采用共享模式，所有用户可管理所有数据源

- **完成Factor模块开发**:
  - 深入研究Qlib因子系统，理解Alpha因子和表达式系统
  - 实现Factor数据模型（支持4种因子类别：技术指标、价量、基本面、自定义）
  - 因子设计为通用表达式，不绑定特定数据源，符合Qlib架构理念
  - 创建并执行数据库迁移，成功创建factor表
  - 开发完整的CRUD API路由
  - 通过Swagger UI验证创建和更新功能
  - 支持Qlib表达式格式（如：EMA($close, 12) - EMA($close, 26)）

### 2026年1月15日

- **完成Model模块开发**:

  - 深入研究Qlib模型系统，理解fit和predict接口
  - 明确架构原则：模型、因子、数据源、策略完全解耦
  - 实现MLModel数据模型（支持TRAINED/OUTDATED/UNTRAINED三种状态）
  - 创建并执行数据库迁移，成功创建mlmodel表
  - 开发完整的CRUD API路由
  - 通过Swagger UI验证所有API功能正常
  - 支持模型配置（class_path + config JSON）
  - 为回测模块奠定基础（用户可自由组合策略、模型、因子、数据源）

- **完成Strategy模块开发**:
  - 深入研究Qlib策略系统，理解BaseStrategy和WeightStrategyBase
  - 实现Strategy数据模型（支持ACTIVE/INACTIVE两种状态）
  - 策略保持完全独立，不绑定任何其他模块
  - 创建并执行数据库迁移，成功创建strategy表
  - 开发完整的CRUD API路由
  - 通过Swagger UI验证所有API功能正常
  - 支持Qlib内置策略（TopkDropoutStrategy等）
  - 使用class_path + config方式灵活配置策略参数

### 2026年1月13日

- **深入研究Qlib完整文档**: 基于HTML文档全面理解Qlib四层架构
- **掌握Qlib核心工作流程**: 数据处理、特征工程、模型训练、策略回测
- **明确系统定位**: 为Qlib添加Web前端界面的量化投资平台
- **完成Qlib环境搭建**:
  - 添加pyqlib等量化依赖到pyproject.toml
  - 重新构建Docker容器，成功安装Qlib 0.9.7
  - 验证所有核心依赖正常工作
  - Qlib环境完全就绪，可以开始数据模型开发

### 2026年1月17日

- **Phase 3: 数据管理模块核心功能完成**:

  - **数据源抽象架构实现**:

    - 创建 `BaseDataSource` 抽象基类，定义统一的数据源接口
    - 实现 `QlibYahooDataSource` 具体实现类，支持 Qlib 预构建数据下载
    - 建立清晰的数据源扩展机制，为后续 Tushare/AkShare 集成奠定基础

  - **Qlib 深度集成**:

    - 实现 Qlib 工具函数：`init_qlib()`, `get_qlib_data_path()`, `ensure_qlib_data_exists()`
    - 成功下载并配置 Qlib 预构建中国市场数据（约 200MB，包含 calendars/instruments/features）
    - 解决 Qlib 交互式确认问题，使用 subprocess 自动化数据下载流程

  - **数据采集服务层**:

    - 创建 `DataCollectorService` 统一服务接口
    - 实现数据状态检查、数据下载、数据信息查询三大核心功能
    - 提供高级封装，隐藏底层 Qlib 复杂性

  - **完整的数据管理 API**:

    - `POST /api/v1/data/download/{region}` - 数据下载（已测试通过）
    - `GET /api/v1/data/status/{region}` - 数据状态检查（已测试通过）
    - `GET /api/v1/data/info/{region}` - 数据详细信息（已测试通过）
    - 所有 API 通过 Swagger UI 完整测试，返回正确的 JSON 响应

  - **Docker 网络配置优化**:

    - 配置代理支持（HTTP_PROXY, HTTPS_PROXY）解决容器网络访问问题
    - 配置 DNS（8.8.8.8, 8.8.4.4）确保域名解析正常
    - 下载 Qlib 官方脚本（get_data.py）到项目中
    - 实现热更新开发环境，代码修改自动生效

  - **技术难题解决**:
    - **Qlib 模块路径问题**: 从错误的 `qlib.run.get_data` 改为正确的 `qlib.tests.data.GetData` API
    - **DNS 解析失败**: 通过配置 Google DNS 解决容器网络问题
    - **代理网络问题**: 配置 Clash 代理环境变量，使容器能访问 GitHub
    - **交互式输入问题**: 使用 subprocess 的 input 参数自动回答确认提示
    - **Docker 热更新**: 利用 volume 挂载和 FastAPI --reload 实现代码热更新

**Phase 3 成果总结**:

- ✅ 完整的数据源抽象架构（支持扩展）
- ✅ Qlib 环境完全集成（数据下载、初始化、路径管理）
- ✅ 三个核心数据管理 API（全部测试通过）
- ✅ Docker 开发环境优化（网络、代理、热更新）
- ✅ 为 Phase 4（因子工程）奠定坚实基础

**下一步计划（Phase 4）**:

- 完善 QlibYahooDataSource 其他方法（get_stock_list, get_daily_data, get_trading_calendar）
- 实现 Tushare 数据源验证架构扩展性
- 开发前端数据管理界面
- 集成 Qlib 因子计算引擎

### 2026年1月9日

- **简化用户访问模式**: 移除用户角色区分，所有用户都可以访问全部功能
- **完成基础环境配置**: 添加量化依赖、配置Docker热更新、环境变量管理
- **准备第一次代码提交**: 基础架构搭建完成

### 2026年1月20日 - Phase 4 数据访问API完成

**重大里程碑**: 完成了完整的数据访问API实现和测试

**核心成果**:

- ✅ **QlibYahooDataSource 完整实现**:

  - `get_stock_list()`: 成功获取 3875 只中国股票列表
  - `get_trading_calendar()`: 成功获取交易日历（支持日期范围查询）
  - `get_daily_data()`: 成功获取历史OHLCV数据（支持多股票、多字段）

- ✅ **数据访问API完整测试**:

  - `GET /api/v1/data/stocks/{region}`: 返回股票列表（测试通过）
  - `GET /api/v1/data/calendar/{region}`: 返回交易日历（测试通过）
  - `POST /api/v1/data/daily/{region}`: 返回历史数据（测试通过）

- ✅ **Docker数据持久化**:

  - 配置 `qlib-data` Docker Volume 持久化 Qlib 数据
  - 解决数据下载后丢失问题，数据现在永久保存

- ✅ **网络连接优化**:
  - 修复代理配置（更新为正确的主机IP 192.168.110.152）
  - 成功下载 Qlib 中国股市数据（196MB，3875只股票）

**技术突破**:

- **字段名自动转换**: 实现 API 字段名（如 "close"）到 Qlib 格式（如 "$close"）的自动转换
- **多数据源架构**: 发现 yfinance 可获取最新数据（2026-01-20），为实时数据更新奠定基础
- **错误处理完善**: 所有 API 都有完整的错误处理和状态返回

**数据覆盖范围**:

- **时间范围**: 1999-11-10 至 2020-09-25（Qlib 预构建数据）
- **股票数量**: 3875 只（上海、深圳、创业板全覆盖）
- **数据字段**: OHLCV + 技术指标支持

**发现的关键问题**:

- Qlib 预构建数据只到 2020年，需要实现实时数据更新机制
- yfinance 可获取最新数据，将在后续版本中集成

**下一步计划**:

- 实现 yfinance 实时数据更新机制
- 开发混合数据源（Qlib历史 + yfinance实时）
- 开始因子工程模块开发

### 2026年1月19日 - Phase 5 YFinance混合架构迁移完成

**重大突破**: 成功实现YFinance混合架构，解决Qlib数据过时问题

**核心成果**:

- ✅ **混合数据源架构**:

  - **股票列表**: 使用Qlib获取完整的3875只股票列表
  - **交易日历**: 使用yfinance获取2026年实时交易日历
  - **历史数据**: 使用yfinance获取2026年最新OHLCV数据

- ✅ **股票代码格式转换**:

  - 实现`_convert_qlib_to_yfinance_symbol()`方法
  - 转换逻辑: `SH600000` → `600000.SS`, `SZ000001` → `000001.SZ`
  - 完美解决Qlib格式与Yahoo Finance格式兼容问题

- ✅ **三大API全面升级测试**:
  - `GET /api/v1/data/stocks/cn`: 3875只股票（Qlib完整列表）
  - `GET /api/v1/data/calendar/cn`: 2026年实时交易日历（yfinance）
  - `GET /api/v1/data/daily/cn`: 2026年真实市场数据（yfinance）

**真实数据验证**:

- **浦发银行(SH600000)**: 开盘11.22，收盘11.16，成交量6927万股
- **平安银行(SZ000001)**: 开盘11.33，收盘11.31，成交量8849万股
- **数据质量**: 高精度浮点数，真实价格波动和成交量

**技术架构优势**:

- **数据完整性**: Qlib提供全面股票覆盖
- **数据实时性**: yfinance提供最新市场数据
- **API兼容性**: 完全保持Qlib API格式标准
- **扩展性**: 支持未来多数据源集成

**解决的关键问题**:

- ✅ Qlib预构建数据只到2020年 → yfinance提供2026年实时数据
- ✅ yfinance无法提供完整股票列表 → 混合架构完美解决
- ✅ 股票代码格式不兼容 → 自动转换机制

**下一步计划**:

- 开始因子工程模块开发
- 集成Alpha158因子库
- 实现自定义因子计算引擎

## Phase 6 规划：因子工程模块开发

### 因子工程核心概念（金融背景）

**Alpha因子定义**：

- **Alpha**：超额收益，即超过市场基准的收益部分
- **因子**：能够解释和预测股票收益的特征变量
- **目标**：发现能够产生稳定超额收益的数学公式

**因子分类**：

1. **技术因子**：基于价格和成交量的技术指标（如MACD、RSI、布林带）
2. **基本面因子**：基于财务数据的指标（如PE、ROE、债务比率）
3. **量价因子**：结合价格和成交量的复合指标
4. **时序因子**：基于时间序列特征的指标（如动量、反转）

### Qlib因子工程架构

**Alpha158因子库**：

- **因子数量**：158个预定义因子
- **覆盖范围**：技术指标、价量特征、时序特征
- **计算引擎**：基于Qlib高性能数据处理引擎
- **配置方式**：通过YAML配置文件即插即用

**表达式系统**：

- **Feature**：从数据提供者加载基础数据（$close, $volume等）
- **ExpressionOps**：使用算子进行特征构造
- **自定义算子**：支持用户定义新的计算算子

### 因子工程模块API设计

**核心功能模块**：

1. **因子计算引擎**：

   - 计算Alpha158预定义因子
   - 支持批量因子计算
   - 高性能并行计算

2. **因子评估系统**：

   - IC（信息系数）：因子与收益的相关性
   - IR（信息比率）：IC的稳定性指标
   - 因子分布分析和统计检验

3. **自定义因子开发**：

   - 表达式解析器
   - 因子公式验证
   - 因子回测和验证

4. **因子管理系统**：
   - 因子库版本控制
   - 因子元数据管理
   - 因子使用统计

**API端点设计**：

```
# 因子列表和信息
GET /api/v1/factors/list/{category} - 获取因子列表（按类别）
GET /api/v1/factors/info/{factor_name} - 获取因子详细信息

# 因子计算
POST /api/v1/factors/calculate - 计算指定因子
POST /api/v1/factors/batch_calculate - 批量计算多个因子

# 因子评估
POST /api/v1/factors/evaluate - 因子有效性评估
GET /api/v1/factors/performance/{factor_name} - 因子历史表现

# 自定义因子
POST /api/v1/factors/custom/create - 创建自定义因子
GET /api/v1/factors/custom/list - 获取自定义因子列表
PUT /api/v1/factors/custom/{factor_id} - 更新自定义因子
DELETE /api/v1/factors/custom/{factor_id} - 删除自定义因子

# 因子组合
POST /api/v1/factors/combination/create - 创建因子组合
GET /api/v1/factors/combination/optimize - 因子组合优化
```

**数据流设计**：

```
原始数据(OHLCV) → 因子计算引擎 → 因子值 → 因子评估 → 因子排序 → 投资决策
```

### 开发优先级

**Phase 6.1**：Alpha158因子库集成

- 实现Alpha158因子计算API
- 集成Qlib因子计算引擎
- 完成因子列表和信息查询API

**Phase 6.2**：因子评估系统

- 实现IC/IR计算
- 因子有效性统计分析
- 因子表现可视化数据

**Phase 6.3**：自定义因子开发

- 表达式解析器实现
- 自定义因子CRUD操作
- 因子验证和回测功能

**Phase 6.4**：前端界面开发

- 因子浏览和搜索界面
- 因子计算参数配置
- 因子评估结果展示

### 2026年1月20日 - Phase 6 架构重设计

**重大架构决策**: 发现数据流问题，决定重新设计数据源架构

**问题分析**:

- **数据流冲突**: YFinance通过API获取实时数据但不保存本地，Alpha158从Qlib本地数据库读取但只有2020年旧数据
- **架构不清晰**: 数据获取与因子计算混合在一起，违反单一职责原则
- **扩展困难**: 现有架构难以支持tushare、akshare等多数据源

**新架构设计原则**:

1. **统一数据接口**: 所有数据源实现相同的接口标准
2. **Qlib原生兼容**: 数据源直接实现Qlib DataLoader接口
3. **职责分离**: 数据获取与因子计算完全分离
4. **易于扩展**: 为未来数据源提供清晰的实现模板

**新架构设计**:

```
services/data_sources/
├── base_data_provider.py       # 抽象基类 (继承Qlib DataLoader)
├── yfinance_provider.py        # YFinance实时数据提供者
├── qlib_provider.py           # Qlib本地数据提供者 (未来)
└── tushare_provider.py        # Tushare数据提供者 (未来)

services/factors/
├── alpha158_handler.py        # 纯因子计算，使用data_providers
└── factor_service.py          # 因子服务协调器
```

**核心技术方案**:

- **BaseDataProvider**: 继承Qlib的DataLoader，同时提供Web API接口
- **双重接口**: 每个数据源既支持Qlib的load()方法，又支持Web API方法
- **数据格式统一**: 内部统一转换为Qlib标准的MultiIndex DataFrame格式
- **缓存机制**: 避免重复获取相同数据，提高性能

**实施计划**:

1. 清理现有代码，保留备份
2. 创建BaseDataProvider抽象基类
3. 实现YFinanceDataProvider
4. 重写Alpha158Handler使用新的数据提供者
5. 通过Swagger UI测试新架构
6. 为tushare等数据源建立实现模板

**预期优势**:

- ✅ 解决数据流问题：Alpha158直接使用YFinance实时数据
- ✅ 保持Qlib兼容：完全利用Qlib的高性能因子计算引擎
- ✅ 架构清晰：数据源与因子计算职责分离
- ✅ 易于扩展：标准化的数据源实现模板
- ✅ 高性能：原生Qlib DataLoader接口，无额外转换开销

### 2026年1月20日 - BaseDataProvider抽象基类完成

**重大里程碑**: 完成统一数据源架构的抽象基类设计和实现

**核心成果**:

- ✅ **BaseDataProvider抽象基类**:

  - 继承Qlib的DataLoader接口，确保与因子计算引擎完全兼容
  - 定义标准化的Web API接口，支持FastAPI端点集成
  - 实现双重接口设计：既支持Qlib原生调用，又支持Web服务
  - 提供完整的工具方法：日期标准化、符号验证、响应格式化

- ✅ **核心接口设计**:

  - `load()`: Qlib DataLoader标准接口，支持fields参数扩展
  - `get_stock_list()`: 获取股票列表的Web API接口
  - `get_trading_calendar()`: 获取交易日历的Web API接口
  - `get_daily_data()`: 获取日线数据的Web API接口
  - `get_data_source_name()`: 动态返回数据源名称

- ✅ **设计特色**:
  - **字段扩展性**: 支持OHLCV基础字段和自定义扩展字段
  - **错误处理**: 统一的成功/错误响应格式，便于API集成
  - **类型安全**: 完整的类型注解，支持IDE智能提示
  - **文档完善**: 详细的方法文档和使用示例

**技术亮点**:

- **双重继承**: 同时继承DataLoader和ABC，确保Qlib兼容性和接口强制实现
- **字段灵活性**: load()方法支持fields参数，可获取超过OHLCV的扩展字段
- **响应标准化**: 统一的\_create_success_response和\_create_error_response方法
- **符号验证**: \_validate_symbols方法确保输入数据的有效性
- **日期标准化**: \_normalize_date方法支持多种日期格式输入

**代码质量**:

**架构验证**:
- **职责分离**: 数据获取与因子计算完全解耦
- **标准化接口**: 遵循BaseDataProvider抽象类规范
- **Qlib原生兼容**: 直接实现DataLoader，零性能损失
- **扩展性强**: 为tushare、akshare等数据源提供清晰实现模板
- **创新设计**: 多API策略解决传统单API限制问题

**使用示例**:
```python
# 创建数据提供者
config = {"region": "cn", "timeout": 30}
provider = YFinanceProvider(config)

# 默认字段加载（OHLCV + adj_close）
data = provider.load(
    instruments=['SH600000', 'SZ000001'],
    start_time='2026-01-01',
    end_time='2026-01-20'
)

# 指定字段加载（包含基本面数据）
data = provider.load(
    instruments=['SH600000'],
    start_time='2026-01-01', 
    end_time='2026-01-20',
    fields=['close', 'volume', 'market_cap', 'pe_ratio']
)
```

**下一步计划**:
1. 创建Alpha158Handler使用新数据源架构
2. 通过Swagger UI测试新架构
3. 为tushare、akshare等数据源建立实现模板
