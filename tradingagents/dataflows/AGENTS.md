<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# dataflows

## Purpose
数据层核心模块，管理多市场（A股/港股/美股）数据获取、缓存、新闻采集和技术指标计算。通过供应商模式支持 AkShare/Tushare/BaoStock/Finnhub/yfinance 等数据源。

## Key Files

| File | Description |
|------|-------------|
| `data_source_manager.py` | DataSourceManager 类，多数据源管理与切换 |
| `data_orchestrator.py` | DataOrchestrator 类，协调数据流和处理逻辑 |
| `data_quality_engine.py` | 数据质量引擎，校验和清洗数据 |
| `data_completeness_checker.py` | 数据完整性检查 |
| `optimized_china_data.py` | A股优化数据处理 |
| `china_fundamental_snapshot.py` | A股基本面快照 |
| `cn_data_service.py` | A股数据服务 |
| `hk_data_service.py` | 港股数据服务 |
| `us_data_service.py` | 美股数据服务 |
| `stock_data_service.py` | 通用股票数据服务 |
| `interface.py` | 数据流接口，set_config() 配置入口 |
| `config.py` | 数据流配置 |
| `realtime_metrics.py` | 实时指标计算 |
| `realtime_news_utils.py` | 实时新闻工具 |
| `unified_dataframe.py` | 统一数据帧格式 |
| `stock_api.py` | 股票 API 封装 |
| `_compat_imports.py` | 兼容性导入 |
| `akshare_utils.py` | AkShare 工具函数 |
| `tushare_utils.py` | Tushare 工具函数 |
| `finnhub_utils.py` | Finnhub 工具函数 |
| `googlenews_utils.py` | Google 新闻工具 |
| `README.md` | 数据流说明文档 |
| `__init__.py` | 包初始化 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `providers/` | 数据供应商：中国/港股/美股/基础供应商 (see `providers/AGENTS.md`) |
| `cache/` | 缓存层：文件缓存、MongoDB缓存、自适应缓存 (see `cache/AGENTS.md`) |
| `news/` | 新闻获取：中文财经、Google新闻、Reddit、实时新闻 (see `news/AGENTS.md`) |
| `technical/` | 技术分析：StockStats 指标计算 (see `technical/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- 数据获取入口：`DataSourceManager` 或各市场 `*_data_service.py`
- 配置入口：`interface.set_config()` 设置数据源和参数
- 新增数据源需在 `providers/` 添加供应商实现
- 数据质量通过 `data_quality_engine.py` 和 `data_completeness_checker.py` 保障
- 分析前必须先同步数据

### Testing Requirements
- 数据流测试：`python -m pytest tests/ -k "dataflow" -v`
- AkShare 测试：`python -m pytest tests/ -k "akshare" -v`
- 数据源测试：`python -m pytest tests/ -k "data_source" -v`

### Common Patterns
- 供应商模式：继承 BaseProvider → 实现获取方法 → 注册到 DataSourceManager
- 缓存模式：检查缓存 → 缓存未命中则获取 → 写入缓存 → 返回数据
- 服务模式：DataService 封装供应商调用 → 添加业务逻辑 → 返回统一格式

## Dependencies

### Internal
- `tradingagents/config/` - 数据库和环境配置
- `tradingagents/agents/` - 智能体使用数据

### External
- AkShare - A股数据
- Tushare - A股数据 (需 Token)
- BaoStock - A股数据
- Finnhub - 美股数据 (需 API Key)
- yfinance - 美股数据
- Alpha Vantage - 美股数据 (需 API Key)
- stockstats - 技术指标

<!-- MANUAL: Custom project notes can be added below -->
