<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tradingagents

## Purpose
核心分析引擎库 (Apache 2.0)，实现多智能体协作的股票分析框架。包含智能体定义、数据流管理、LLM 客户端封装、图编排逻辑和配置管理，是整个系统的基础。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 模块入口，定义版本号与元信息 |
| `default_config.py` | 默认配置项，提供系统基础参数 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `agents/` | 多智能体定义：分析师、主控、研究员、风控、交易员 (see `agents/AGENTS.md`) |
| `graph/` | LangGraph 图编排：交易分析流程、信号处理、条件逻辑 (see `graph/AGENTS.md`) |
| `dataflows/` | 数据层：多市场数据源管理、缓存、新闻获取 (see `dataflows/AGENTS.md`) |
| `llm_clients/` | LLM 客户端：OpenAI/Google/工厂模式/模型目录 (see `llm_clients/AGENTS.md`) |
| `llm_adapters/` | LLM 适配器：DashScope/DeepSeek/Google OpenAI 兼容层 (see `llm_adapters/AGENTS.md`) |
| `config/` | 配置管理：环境变量、数据库、供应商配置 (see `config/AGENTS.md`) |
| `tools/` | 工具函数：新闻工具、技术指标 (see `tools/AGENTS.md`) |
| `utils/` | 通用工具：日志、股票校验、新闻过滤 (see `utils/AGENTS.md`) |
| `api/` | API 接口：stock_api 股票数据接口 |
| `models/` | 数据模型：stock_data_models 股票数据结构 |
| `constants/` | 常量定义：data_sources 数据源标识 |
| `data_cache/` | 数据缓存：快照存储 (sh/sz 子目录) |

## For AI Agents

### Working In This Directory
- 这是 Apache 2.0 开源模块，可自由修改
- 核心入口：`from tradingagents.graph.trading_graph import TradingAgentsGraph`
- 数据流配置通过 `dataflows/interface.py` 的 `set_config()` 设置
- 智能体注册通过 `agents/utils/analyst_registry.py` 管理
- LLM 客户端通过 `llm_clients/factory.py` 的 `create_llm_client()` 创建

### Testing Requirements
- 单元测试在 `tests/` 目录
- 运行：`python -m pytest tests/ -k "tradingagents" -v`
- 数据同步测试：`python -m pytest tests/ -k "akshare" -v`

### Common Patterns
- 分析流程：创建 TradingAgentsGraph → propagate(股票代码, 日期) → 获取决策
- 数据获取：DataSourceManager → 选择供应商 → 获取数据
- LLM 调用：factory.create_llm_client(provider) → 获取客户端 → 调用

## Dependencies

### Internal
- `langchain/` - LangChain 扩展模块
- `app/` - 后端调用此核心库
- `cli/` - CLI 调用此核心库

### External
- LangChain, LangGraph - AI 编排框架
- ChromaDB - 向量存储
- AkShare, Tushare, BaoStock - A股数据源
- Finnhub, yfinance - 美股数据源
- OpenAI, Google Generative AI - LLM 服务

<!-- MANUAL: Custom project notes can be added below -->
