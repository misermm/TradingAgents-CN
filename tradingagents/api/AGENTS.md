<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# api

## Purpose
股票数据 API 接口层，为上层模块提供便捷的股票数据获取入口。封装了 `stock_data_service` 统一数据服务，支持完整的降级机制（Tushare → AkShare → BaoStock），并提供股票基础信息查询、历史数据获取、关键词搜索、市场概览和服务状态检查等功能。

## Key Files

| File | Description |
|------|-------------|
| `stock_api.py` | 股票数据 API 接口，提供 `get_stock_info`、`get_all_stocks`、`get_stock_data`、`search_stocks`、`get_market_summary`、`check_service_status` 六个核心函数及对应别名 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 本模块依赖 `tradingagents/dataflows/stock_data_service`，若该服务不可用，所有函数会返回包含 `error` 字段的降级结果
- 修改接口签名时需同步更新底部的别名函数（`get_stock`、`get_stocks`、`search`、`status`）
- 返回值统一使用 `Dict[str, Any]` 或 `List[Dict[str, Any]]`，错误信息通过 `error` 字段传递，不抛异常
- `get_stock_data` 默认查询最近 30 天数据，日期格式为 `YYYY-MM-DD`

### Testing Requirements
- 命令行快速测试：`python -m tradingagents.api.stock_api`
- 单元测试需 mock `stock_data_service`，避免依赖真实数据库连接
- 测试降级逻辑时需模拟 `SERVICE_AVAILABLE = False` 场景

### Common Patterns
- 获取单只股票信息：`from tradingagents.api.stock_api import get_stock_info; info = get_stock_info('000001')`
- 搜索股票：`from tradingagents.api.stock_api import search_stocks; results = search_stocks('平安')`
- 检查服务状态：`from tradingagents.api.stock_api import check_service_status; status = check_service_status()`
- 获取历史数据（带降级）：`from tradingagents.api.stock_api import get_stock_data; data = get_stock_data('000001', '2024-01-01', '2024-01-31')`

## Dependencies

### Internal
- `tradingagents/dataflows/stock_data_service` — 统一股票数据服务（核心依赖）
- `tradingagents/utils/logging_manager` — 日志管理
- `tradingagents/utils/logging_init` — 日志初始化

### External
- Python 标准库：`sys`、`os`、`datetime`、`typing`

<!-- MANUAL: Custom project notes can be added below -->
