<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests/dataflows

## Purpose
数据流模块测试，验证实时金融指标计算（PE/PB）及降级策略。

## Key Files

| File | Description |
|------|-------------|
| `test_realtime_metrics.py` | 测试实时 PE/PB 计算：验证逻辑、Mock 数据计算、缺失数据处理、降级到静态数据 |

## For AI Agents

### Working In This Directory
- 核心被测模块：`tradingagents.dataflows.realtime_metrics`
- 三个关键函数：`calculate_realtime_pe_pb`、`validate_pe_pb`、`get_pe_pb_with_fallback`
- 测试覆盖：正常计算 → 缺失数据返回 None → 实时失败降级到 daily_basic 静态数据
- PE 允许负值（亏损企业），但限制极端值（±1500/150）；PB 限制范围 0.05~150

### Testing Requirements
- 运行：`python -m pytest tests/dataflows/ -v`
- 无需真实 MongoDB，使用 MockClient/MockCollection 模拟

### Common Patterns
- Mock MongoDB 层级：`MockClient → MockDB → MockCollection`
- `monkeypatch.setattr` 替换模块级函数实现降级测试
- 降级链路：实时计算 → 失败 → 查询 stock_basic_info 静态数据

## Dependencies

### Internal
- `tradingagents.dataflows.realtime_metrics` - 实时指标计算模块

### External
- pytest - 测试框架

<!-- MANUAL: Custom project notes can be added below -->
