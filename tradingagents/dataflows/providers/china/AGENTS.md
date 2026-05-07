<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# china

## Purpose
A股数据供应商，提供多种数据源获取中国 A股市场数据，包括行情、基本面、财务指标等。

## Key Files

| File | Description |
|------|-------------|
| `akshare.py` | AkShare 供应商：免费 A股数据，主要数据源 |
| `tushare.py` | Tushare 供应商：需 Token，高质量财务数据 |
| `baostock.py` | BaoStock 供应商：免费历史数据，K线和基本面 |
| `eastmoney_direct.py` | 东方财富直连：实时行情数据 |
| `sina_finance.py` | 新浪财经：实时行情和新闻 |
| `fundamentals_snapshot.py` | 基本面快照：快速获取核心财务指标 |
| `ttm_calculator.py` | TTM 计算器：滚动十二个月财务指标计算 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- AkShare 是主要免费数据源，优先使用
- Tushare 需要配置 Token，提供更高质量的财务数据
- BaoStock 作为备用数据源
- 东方财富和新浪提供实时行情
- TTM 计算器用于标准化财务指标

### Testing Requirements
- AkShare 测试：`python -m pytest tests/ -k "akshare" -v`
- Tushare 测试：`python -m pytest tests/ -k "tushare" -v`
- BaoStock 测试：`python -m pytest tests/ -k "baostock" -v`

### Common Patterns
- 数据获取模式：检查缓存 → 调用 API → 解析数据 → 标准化格式 → 缓存结果

## Dependencies

### Internal
- `tradingagents/dataflows/providers/base_provider.py` - 基类
- `tradingagents/config/` - Tushare Token 配置

### External
- AkShare - A股数据
- Tushare - A股财务数据
- BaoStock - A股历史数据

<!-- MANUAL: Custom project notes can be added below -->
