<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# hk

## Purpose
港股数据供应商，提供港股市场数据获取功能。

## Key Files

| File | Description |
|------|-------------|
| `hk_stock.py` | 港股数据供应商：基础港股数据获取 |
| `improved_hk.py` | 改进版港股供应商：增强数据质量和覆盖 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 港股数据通过 AkShare 的港股接口获取
- improved_hk.py 提供更好的错误处理和数据质量

### Testing Requirements
- 港股测试：`python -m pytest tests/ -k "hk" -v`

### Common Patterns
- 港股代码格式：5位数字（如 00700）

## Dependencies

### Internal
- `tradingagents/dataflows/providers/base_provider.py` - 基类

### External
- AkShare - 港股数据接口

<!-- MANUAL: Custom project notes can be added below -->
