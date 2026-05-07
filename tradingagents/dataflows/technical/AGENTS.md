<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# technical

## Purpose
技术分析模块，提供基于 stockstats 的技术指标计算功能。

## Key Files

| File | Description |
|------|-------------|
| `stockstats.py` | StockStats 技术指标计算：MACD、RSI、布林带等 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 技术指标通过 stockstats 库计算
- 输入为股票行情数据 DataFrame
- 输出为技术指标值

### Testing Requirements
- 技术指标测试：`python -m pytest tests/ -k "technical" -v`

### Common Patterns
- 指标计算模式：DataFrame → StockStats 包装 → 计算指标 → 返回结果

## Dependencies

### Internal
- `tradingagents/dataflows/` - 行情数据

### External
- stockstats - 技术指标库

<!-- MANUAL: Custom project notes can be added below -->
