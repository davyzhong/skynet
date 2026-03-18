# SkyNet 整体架构设计

## 概述

SkyNet（天网）是一个企业内部数据智能平台，用于多源数据采集、指标计算、报表生成，并结合 AI Agent 实现数据推送、异常监控和智能分析。

## 项目背景

- **使用场景**：企业内部数据平台
- **团队规模**：一人全栈开发
- **数据规模**：小规模（<10GB/日），离线批处理为主
- **技术栈**：Python 生态

## 架构方案

采用**单体模块化架构**，一个 FastAPI 应用内按模块划分，边界清晰，便于一人维护和未来演进。

```
┌─────────────────────────────────────────────────────────────┐
│                        SkyNet 架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  数据采集    │───▶│  指标引擎    │───▶│  报表中心    │     │
│  │  Ingestion  │    │  Metrics    │    │  Reports    │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            ▼                                │
│                    ┌─────────────┐                          │
│                    │  AI Agent   │◀──── 外部消息通道         │
│                    │  智能助手    │      (飞书/企微/钉钉)     │
│                    └─────────────┘                          │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│    异常告警            自然语言查询         智能洞察          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  基础设施层                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │PostgreSQL│  │ Redis   │  │对象存储 │  │ Celery  │        │
│  │ 元数据   │  │ 缓存/队列│  │ 文件/报表│  │ 任务调度│        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 模块设计

### 1. 数据采集模块 (Ingestion)

**职责**：连接多种数据源，抽取数据，标准化后存入系统

**支持的数据源**：
| 类型 | 实现 | 说明 |
|------|------|------|
| Database | SQLAlchemy + psycopg2 | PostgreSQL, MySQL, SQLite |
| API | httpx + pydantic | REST API，支持认证和分页 |
| File | pandas/openpyxl | Excel, CSV, JSON |
| Stream | confluent-kafka | Kafka（预留，按需启用） |

**同步策略**：
- 全量同步：每次拉取全部数据（小表）
- 增量同步：基于时间戳/ID 增量拉取（大表）

**配置示例**：
```yaml
sources:
  - name: order_db
    type: postgresql
    connection: ${ORDER_DB_URL}
    sync_mode: incremental
    schedule: "0 */1 * * *"  # 每小时
```

### 2. 指标引擎模块 (Metrics)

**职责**：基于原始数据计算业务指标，支持多维度聚合

**指标类型**：
| 类型 | 说明 | 示例 |
|------|------|------|
| 原子指标 | 直接聚合计算 | 日销售额、日订单数 |
| 衍生指标 | 基于其他指标计算 | 客单价 = 销售额/订单数 |
| 窗口指标 | 时间窗口计算 | 7日移动平均、环比增长率 |

**计算引擎**：Polars（比 Pandas 快 10-100 倍）

**配置示例**：
```yaml
metrics:
  - name: daily_revenue
    description: "日营收"
    type: sum
    source: orders
    field: amount
    dimensions: [date, region, product]
    filters:
      status: completed
    schedule: "0 1 * * *"
```

### 3. 报表中心模块 (Reports)

**职责**：基于指标生成报表，支持多种格式和分发渠道

**报表类型**：
| 类型 | 场景 | 输出格式 |
|------|------|----------|
| 定时报表 | 每日/每周自动推送 | Markdown 卡片 + 图片 |
| 仪表盘 | 实时数据看板 | Web 页面 |
| Ad-hoc | 临时查询导出 | Excel/CSV |

**分发渠道**：飞书、企业微信、钉钉、邮件

**Web 仪表盘**：FastAPI + Vue 3 + ECharts（或 Streamlit 快速 MVP）

### 4. AI Agent 模块 (Agents)

**职责**：智能化的数据交互和主动监控

**核心能力**：
| 能力 | 实现方式 | 示例 |
|------|----------|------|
| 通知推送 | Celery 定时任务 + Webhook | 每早9点推送日报 |
| 异常检测 | 统计规则 + LLM 辅助 | 销售额环比下降超 20% 告警 |
| 自然语言查询 | Text-to-SQL + LLM | "上周华东区销售额是多少" |
| 智能洞察 | LLM 分析数据 | "本周转化率下降，建议检查..." |

**LLM 网关**：
- 优先级：本地模型 (Ollama) > Claude API > OpenAI API > 国内模型

**告警配置示例**：
```yaml
alerts:
  - name: revenue_drop
    metric: daily_revenue
    condition:
      type: percentage_change
      compare_to: previous_day
      threshold: -20%
    severity: warning
    channels: [feishu, email]
```

## 项目结构

```
skynet/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── ingestion/              # 数据采集模块
│   │   ├── connectors/         # 数据源连接器
│   │   ├── sync.py             # 同步逻辑
│   │   └── loader.py           # 数据加载器
│   ├── metrics/                # 指标引擎模块
│   │   ├── engine.py           # 计算引擎
│   │   ├── registry.py         # 指标注册表
│   │   └── aggregators.py      # 聚合函数
│   ├── reports/                # 报表中心模块
│   │   ├── builder.py          # 报表构建器
│   │   ├── renderer.py         # 渲染引擎
│   │   └── distribution.py     # 分发逻辑
│   ├── agents/                 # AI Agent 模块
│   │   ├── llm.py              # LLM 网关
│   │   ├── nl_query.py         # 自然语言查询
│   │   ├── anomaly.py          # 异常检测
│   │   └── insight.py          # 智能洞察
│   └── storage/                # 存储层
│       ├── models.py           # 数据模型
│       └── repository.py       # 数据访问层
│
├── config/
│   ├── sources.yaml            # 数据源配置
│   ├── metrics.yaml            # 指标配置
│   ├── reports.yaml            # 报表配置
│   └── alerts.yaml             # 告警配置
│
├── tasks/
│   └── celery_app.py           # Celery 任务定义
│
├── tests/                      # 测试文件
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## 核心依赖

```toml
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "polars>=0.20.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.29.0",
    "celery>=5.3.0",
    "redis>=5.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "httpx>=0.26.0",
    "openpyxl>=3.1.0",
    "plotly>=5.18.0",
    "anthropic>=0.18.0",
]
```

## 部署策略

**Docker Compose 部署**：
```yaml
services:
  skynet:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: .
    command: celery -A app.celery_app worker -l info
    depends_on:
      - redis

  celery-beat:
    build: .
    command: celery -A app.celery_app beat -l info
    depends_on:
      - redis

  postgres:
    image: postgres:16-alpine

  redis:
    image: redis:7-alpine
```

**云服务推荐（阿里云）**：
| 组件 | 推荐服务 |
|------|----------|
| 应用运行 | ECS / 容器服务 |
| 数据库 | RDS PostgreSQL |
| 缓存 | Redis 云版 |
| 对象存储 | OSS |

## 设计原则

1. **模块内聚**：每个模块职责单一，内部实现可独立演进
2. **松耦合**：模块间通过明确的接口/消息通信
3. **配置驱动**：数据源、指标、报表都通过配置定义，减少硬编码
4. **可演进**：模块边界清晰，未来可按需拆分为微服务
