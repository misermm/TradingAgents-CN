<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# providers

## Purpose
数据供应商模块，按市场分区实现数据获取。包含基础供应商接口、中国市场（AkShare/Tushare/BaoStock/东方财富/新浪）、港股和美股供应商。

## Key Files

| File | Description |
|------|-------------|
| `base_provider.py` | BaseProvider 基类，定义供应商统一接口 |
| `tushare_provider.py` | Tushare 供应商实现 |
| `resilient_http_client.py` | 弹性 HTTP 客户端，支持重试和超时 |
| `__init__.py` | 包初始化 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `china/` | A股数据供应商：AkShare/BaoStock/东方财富/新浪/基本面快照/TTM计算 (see `china/AGENTS.md`) |
| `hk/` | 港股数据供应商 (see `hk/AGENTS.md`) |
| `us/` | 美股数据供应商：Finnhub/yfinance/Alpha Vantage (see `us/AGENTS.md`) |
| `examples/` | 供应商使用示例 |

## For AI Agents

### Working In This Directory
- 新增供应商需继承 `base_provider.py` 的 BaseProvider
- HTTP 请求使用 `resilient_http_client.py` 确保可靠性
- 供应商通过 DataSourceManager 注册和调度

### Testing Requirements
- 供应商测试：`python -m pytest tests/ -k "provider" -v`

### Common Patterns
- 供应商模式：继承 BaseProvider → 实现获取方法 → 注册到 DataSourceManager

## Dependencies

### Internal
- `tradingagents/dataflows/cache/` - 缓存层
- `tradingagents/config/` - 配置

### External
- AkShare, Tushare, BaoStock - A股数据
- Finnhub, yfinance, Alpha Vantage - 美股数据

<!-- MANUAL: Custom project notes can be added below -->
