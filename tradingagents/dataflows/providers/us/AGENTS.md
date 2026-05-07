<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# us

## Purpose
美股数据供应商，提供美股市场数据获取，包括行情、基本面和新闻。

## Key Files

| File | Description |
|------|-------------|
| `finnhub.py` | Finnhub 供应商：美股行情、新闻、基本面 (需 API Key) |
| `yfinance.py` | yfinance 供应商：免费美股数据 |
| `optimized.py` | 优化版美股数据获取 |
| `alpha_vantage_common.py` | Alpha Vantage 公共工具 |
| `alpha_vantage_fundamentals.py` | Alpha Vantage 基本面数据 |
| `alpha_vantage_news.py` | Alpha Vantage 新闻数据 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- yfinance 是免费数据源，优先使用
- Finnhub 需 API Key，提供更丰富的数据
- Alpha Vantage 需 API Key，提供基本面和新闻
- 美股代码格式：字母 (如 AAPL)

### Testing Requirements
- 美股测试：`python -m pytest tests/ -k "us_stock" -v`
- Finnhub 测试：`python -m pytest tests/ -k "finnhub" -v`

### Common Patterns
- 美股代码格式：大写字母 (AAPL, GOOGL)

## Dependencies

### Internal
- `tradingagents/dataflows/providers/base_provider.py` - 基类

### External
- Finnhub - 美股数据 API
- yfinance - 免费美股数据
- Alpha Vantage - 美股数据 API

<!-- MANUAL: Custom project notes can be added below -->
