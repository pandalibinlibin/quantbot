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

## 🚀 开发计划

### Phase 1: 研究和设计 (1-2天)

- [ ] 深入研究 Qlib workflow 文档和示例
- [ ] 设计 Workflow 配置生成器接口
- [ ] 设计 API 端点结构
- [ ] 设计配置验证规则

### Phase 2: 核心实现 (3-5天)

- [ ] 实现 Workflow 配置生成器
- [ ] 实现 Workflow 执行器
- [ ] 实现结果存储服务
- [ ] 实现 API 端点
- [ ] 编写单元测试

### Phase 3: 扩展点实现 (2-3天)

- [ ] 设计插件注册机制
- [ ] 实现自定义因子引擎注册
- [ ] 实现自定义模型注册
- [ ] 实现自定义策略注册
- [ ] 编写扩展示例

### Phase 4: 测试和优化 (2-3天)

- [ ] 端到端测试
- [ ] 性能测试和优化
- [ ] 文档完善
- [ ] 前端适配

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

## 📅 变更日志

### 2026-01-26 - 架构重构

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

- 手动实现过于复杂且容易出错
- Qlib Workflow 是官方验证的标准方式
- 符合项目"为 Qlib 加前端"的定位
