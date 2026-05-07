<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# basics_sync

## Purpose
基础数据同步子包。封装与股票基础信息同步相关的阻塞调用与处理函数，为 `basics_sync_service.py` 提供底层能力。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，导出 `fetch_stock_basic_df`、`find_latest_trade_date`、`fetch_daily_basic_mv_map`、`fetch_latest_roe_map`、`add_financial_metrics` |
| `utils.py` | Tushare 阻塞式工具函数：获取股票列表、探测最新交易日、获取日度基础指标映射、获取最新 ROE 映射 |
| `processing.py` | 共享文档构建/指标处理：`add_financial_metrics` 将市值/估值/交易/股本指标追加到文档 |

## For AI Agents

### Working In This Directory
- `utils.py` 中的函数均为**同步阻塞**调用，直接操作 Tushare API，需在异步上下文中用 `asyncio.to_thread` 包装
- `processing.py` 中的 `add_financial_metrics` 就地修改传入的 `doc` 字典，不返回新对象
- 市值字段从万元转换为亿元（÷10000）；估值/交易/股本字段过滤 NaN/None
- `fetch_latest_roe_map` 按最近财政季度逆序探测，找到第一期非空数据即返回
- 依赖 `TUSHARE_ENABLED=true` 和有效 `TUSHARE_TOKEN`，否则抛出 `RuntimeError`

### Common Patterns
- 获取股票列表：`fetch_stock_basic_df()` → DataFrame
- 获取日度指标映射：`fetch_daily_basic_mv_map(trade_date)` → `{ts_code: {field: value}}`
- 追加财务指标：`add_financial_metrics(doc, daily_metrics)` → 就地修改 doc

### Dependencies

#### Internal
- `tradingagents/dataflows/providers/china/tushare` - Tushare 数据源 Provider
- `app/core/config` - 配置（`TUSHARE_ENABLED` 等）

#### External
- Tushare Pro API - A股基础数据源

<!-- MANUAL: Custom project notes can be added below -->
