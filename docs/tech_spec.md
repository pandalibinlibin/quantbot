# QuantBot 技术规格文档

**版本**: 2.0 (架构重构版)  
**最后更新**: 2026-01-26

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

### Phase 1: 核心 Workflow 执行器 (1周)

**目标**: 实现基础的 Workflow 执行能力

**任务**:

- [x] 研究 Qlib workflow 文档和示例
- [ ] 实现 `QlibWorkflowService`
  - 初始化 Qlib
  - 执行 workflow 配置
  - 返回训练结果和指标
- [ ] 使用 Qlib 内置组件验证全流程
  - Alpha158 因子
  - LGBModel 模型
  - 完整的训练和评估

**验证标准**:

```python
# 能够成功执行以下配置
config = {
    "task": {
        "model": {"class": "LGBModel", ...},
        "dataset": {
            "kwargs": {
                "handler": {"class": "Alpha158", ...},
                "segments": {...}
            }
        }
    }
}
result = workflow_service.execute_workflow(config)
assert "metrics" in result
```

### Phase 2: 配置生成器 (1周)

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

## 📅 变更日志

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

**📊 当前状态**:

Phase 1 核心服务已全部完成：

- ✅ `qlib_config.py` - 配置管理
- ✅ `timer.py` - 耗时监控
- ✅ `qlib_init_service.py` - Qlib 初始化
- ✅ `qlib_workflow_service.py` - 训练工作流执行（完整实现）
- ✅ `test_qlib_workflow_service.py` - 测试脚本

**📝 下一步工作**:

1. 在 Docker 容器中运行测试验证功能
2. 根据测试结果修复可能的问题
3. 创建 API 路由暴露训练工作流服务
4. 通过 Swagger UI 测试 API
5. 实现推理工作流（`execute_inference_workflow`）

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

**📝 下一步工作**:

1. 添加 `qlib_workflow_service.py` 的辅助方法：

   - `_execute_workflow_steps()` - 执行工作流步骤
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
