<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests/unit

## Purpose
单元测试，使用 Mock 隔离外部依赖，验证核心模块的纯逻辑正确性。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化（空文件） |
| `test_core_modules.py` | 核心模块 Mock 单元测试：merge_dicts reducer、_merge_master_state 状态合并、DataQualityEngine 评分/补全/溯源、DataOrchestrator 降级框架、CacheConfig 缓存键/TTL |
| `test_stocks_kline_news_api.py` | 股票 K 线/新闻 API 测试：K 线数据返回格式校验、无效 period 返回 400、新闻含公告和来源信息 |
| `test_sync_mongo_fallbacks.py` | MongoDB 同步降级测试：DataSourceManager 不可用时使用默认优先级、TushareProvider 不可用时跳过 DB 查询 |

## For AI Agents

### Working In This Directory
- 所有测试使用 Mock/monkeypatch，无需真实数据库或网络
- `test_core_modules.py` 覆盖 4 个核心类，是最全面的单元测试文件
- `test_stocks_kline_news_api.py` 使用 `dependency_overrides` 绕过认证
- `test_sync_mongo_fallbacks.py` 使用 `object.__new__()` 绕过 `__init__` 构造轻量对象

### Testing Requirements
- 运行：`python -m pytest tests/unit/ -v`
- 无需外部服务

### Common Patterns
- `merge_dicts`：LangGraph AgentState reducer，None/空字符串保留旧值
- `_merge_master_state`：4 个 master 字段（reports/tool_calls/quality/quantitative）合并
- `DataQualityEngine`：0~5 分评分，FieldProvenance 溯源，build_provenance_summary 摘要
- `DataOrchestrator`：按市场/类型获取可用源，try_sources_in_order 降级链
- API 测试：`patch("app.services.data_sources.manager.DataSourceManager.method")` Mock 数据源

## Dependencies

### Internal
- `tradingagents.agents.utils.agent_states` - Agent 状态工具
- `tradingagents.graph.trading_graph` - 交易图核心
- `tradingagents.dataflows.data_quality_engine` - 数据质量引擎
- `tradingagents.dataflows.data_orchestrator` - 数据编排器
- `tradingagents.dataflows.cache.cache_config` - 缓存配置
- `app.routers.stocks` - 股票路由
- `app.services.data_sources.manager` - 数据源管理器
- `tradingagents.dataflows.providers.china.tushare` - Tushare 提供者

### External
- pytest - 测试框架
- FastAPI TestClient - HTTP 测试客户端
- pandas / numpy - 数据处理

<!-- MANUAL: Custom project notes can be added below -->
