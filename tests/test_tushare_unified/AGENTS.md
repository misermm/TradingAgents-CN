# tests/test_tushare_unified/

Parent: ../AGENTS.md
Generated: 2026-05-07
Updated: 2026-05-07

## Purpose

Tushare 统一数据方案测试包。验证 TushareProvider 数据提供者与 TushareSyncService 同步服务的核心功能。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包标识文件，声明为 Tushare 统一方案测试包 |
| `test_tushare_provider.py` | 测试 TushareProvider：连接、股票列表、基础信息、行情、历史数据、ts_code 标准化、数据格式化 |
| `test_tushare_sync_service.py` | 测试 TushareSyncService：初始化、基础信息同步、实时行情同步、历史数据同步、财务数据同步、数据新鲜度检查 |

## Subdirectories

无

## For AI Agents

### Working In This Directory
- 标准 pytest 测试用例，使用 `pytest` + `pytest-asyncio` + `unittest.mock`
- 所有外部依赖（Tushare API、MongoDB）均已 mock，无需真实连接
- `test_tushare_provider.py` 测试 `tradingagents.dataflows.providers.tushare_provider.TushareProvider`
- `test_tushare_sync_service.py` 测试 `app.worker.tushare_sync_service.TushareSyncService`

### Testing
- 运行全部：`python -m pytest tests/test_tushare_unified/ -v`
- 运行单个：`python -m pytest tests/test_tushare_unified/test_tushare_provider.py -v`

### Dependencies
- 内部依赖：`tradingagents.dataflows.providers.tushare_provider`、`app.worker.tushare_sync_service`
- 外部依赖：pytest、pytest-asyncio、pandas
