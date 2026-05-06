# TradingAgents-CN 开发指南

## 项目概述

多智能体 AI 股票分析学习平台，基于 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)。支持 A股/港股/美股分析，LLM 供应商聚合（OpenAI、Google、DeepSeek、阿里百炼等）。

**定位**: 学习与研究用途，不提供实盘交易指令。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 核心框架 | Python 3.10+ |
| 后端 | FastAPI + Uvicorn (app/ 目录，专有) |
| 前端 | Vue 3 + Vite + Element Plus (frontend/ 目录，专有) |
| 数据库 | MongoDB + Redis |
| AI/ML | LangChain, LangGraph, ChromaDB |
| 数据源 | AkShare, Tushare, BaoStock, Finnhub, yfinance |

---

## 许可证 (重要)

```
├──Apache 2.0 (开源)     │ tradingagents/, tests/, scripts/, docs/
├──专有 (需授权)          │ app/, frontend/
└──app/LICENSE          │ 后端专有许可证
└──frontend/LICENSE     │ 前端专有许可证
```

商业使用 `app/` 或 `frontend/` 需联系 **hsliup@163.com** 获取授权。

---

## 核心入口

```python
# 基础用法
from tradingagents.graph.trading_graph import TradingAgentsGraph
ta = TradingAgentsGraph(debug=True)
_, decision = ta.propagate("000001", "2024-05-10")
```

---

## 开发命令

### 本地运行
```bash
# Docker 方式 (推荐)
docker-compose -f docker-compose.local.yml up -d

# 本地开发
python main.py  # 核心分析
python -m pytest tests/ -v  # 运行测试 (-m integration 可跑集成测试)
```

### 数据同步 (Docker 内)
```bash
docker exec -it tradingagents-cn-backend-1 python -c "
from scripts.akshare_sync_optimized import main; import asyncio
asyncio.run(main(['000001', '600519'], limit=1000))
"
```

### 数据库 (Docker 内)
```bash
# MongoDB Shell
docker exec -it tradingagents-cn-mongodb-1 mongosh -u admin -p tradingagents123

# Redis CLI
docker exec -it tradingagents-cn-redis-1 redis-cli -a tradingagents123
```

---

## 目录结构

```
tradingagents/           # 核心库 (开源)
├── graph/              # TradingAgentsGraph 主逻辑
│   └── trading_graph.py
├── agents/             # 多智能体定义
│   ├── analysts/        # 各类分析师
│   ├── masters/       # 主控智能体
│   └── risk_mgmt/     # 风控模块
├── llm_clients/        # LLM 客户端封装
│   ├── openai_client.py
│   ├── google_client.py
│   └── model_catalog.py
├── dataflows/          # 数据层 (关键)
│   ├── data_source_manager.py     # 数据源管理
│   ├── china_fundamental_snapshot.py
│   └── optimized_china_data.py
└── tools/             # 工具函数
    └── unified_news_tool.py

app/                  # FastAPI 后端 (专有)
├── routers/           # API 路由
├── services/         # 业务逻辑
└── worker/          # 异步任务

frontend/             # Vue 前端 (专有)

tests/                # 测试 (开源)
├── pytest.ini         # 配置: -m "not integration"
└── test_*.py       # 200+ 测试文件

scripts/              # 运维脚本 (开源)
├── migrations/       # 数据库迁移
└── startup/        # 启动脚本
```

---

## 配置

### 环境变量 (.env)
必需配置见 `.env.example`，关键项：

```env
# 数据库 (必需)
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=tradingagents123

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=tradingagents123

# JWT (必需，生产需修改)
JWT_SECRET=your-super-secret-jwt-key-change-in-production
CSRF_SECRET=your-csrf-secret-key-change-in-production

# LLM (至少配置一个)
DEEPSEEK_API_KEY=sk-xxx
DASHSCOPE_API_KEY=sk-xxx
GOOGLE_API_KEY=xxx

# 代理 (访问国外 LLM 时)
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
NO_PROXY=localhost,127.0.0.1,eastmoney.com,api.tushare.pro,baostock.com
```

---

## 测试约定

```bash
# pytest.ini 配置 (tests/pytest.ini)
testpaths = tests                    # 只扫描 tests/ 目录
addopts = -m "not integration"    # 默认跳过集成测试

# 运行特定测试
python -m pytest tests/test_analysis.py -v
python -m pytest tests/ -k "akshare" -v
python -m pytest tests/ -m integration -v  # 跑集成测试
```

---

## 关键架构要点

### 前端/后端分离
- **app/** - FastAPI 后端 (专有，商用需授权)
- **frontend/** - Vue 3 前端 (专有，商用需授权)
- **tradingagents/** - 核心库 (Apache 2.0)
- **tests/** - 测试套件 (Apache 2.0)

### 数据层 (重要)
`tradingagents/dataflows/` 是核心数据管理模块：
- `data_source_manager.py` - 多数据源管理 (AkShare/Tushare/BaoStock)
- `optimized_china_data.py` - A股数据处理
- `china_fundamental_snapshot.py` - 基本面快照

---

## 重要注意事项

### 数据同步前置
分析股票前**必须**先同步数据，否则分析结果会出现数据错误：
```bash
# AkShare 同步示例
python scripts/akshare_sync_optimized.py --codes 000001,600519 --limit 365
```

### 代理配置 (关键)
- 国内数据源需走直连 (NO_PROXY 绕过代理)
- 国外 LLM (Google) 需走 HTTP_PROXY
- Windows: 使用完整域名，不支持通配符 `*`

### 常见问题
1. **数据缺失**: 同步数据后再分析
2. **LLM 连接失败**: 配置 HTTP_PROXY / 检查 API Key
3. **数据库连接**: 检查 MongoDB/Redis 服务是否运行

### 调试技巧
- 查看日志: `logs/` 目录或 Docker 日志
- 快速测试数据源: `python tests/simple_akshare_test.py`
- 检查配置: `python scripts/check_api_config.py`
- LLM 连接测试: `python tests/test_google_api_connection.py`

---

## 文档

- 完整文档: `docs/`
- 配置指南: `docs/configuration_guide.md`
- 部署指南: `docs/deployment/database_setup.md`
- 更新日志: `docs/releases/CHANGELOG.md`

---

## 相关链接

- GitHub: https://github.com/hsliuping/TradingAgents-CN
- 邮箱: hsliup@163.com
- 微信公众号: TradingAgents-CN