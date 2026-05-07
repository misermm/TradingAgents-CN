<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# enhanced_screening

## Purpose
增强筛选工具子包。为 `EnhancedScreeningService` 提供条件分析和格式转换的独立逻辑，分离关注点。

## Key Files

| File | Description |
|------|-------------|
| `utils.py` | 工具函数：`analyze_conditions` 分析筛选条件类型与数据库兼容性；`convert_conditions_to_traditional_format` 将结构化条件转为传统格式 |

## For AI Agents

### Working In This Directory
- `analyze_conditions` 统计条件中基本面/技术面/基础字段的数量，判断是否可走数据库查询路径
- `convert_conditions_to_traditional_format` 将 `ScreeningCondition` 列表转为 `{field: {op: value}}` 字典格式
- 依赖 `app/models/screening` 中的 `ScreeningCondition`、`FieldType`、`BASIC_FIELDS_INFO`

### Common Patterns
- 分析条件：`analyze_conditions(conditions)` → `{total_conditions, can_use_database, needs_technical_indicators, ...}`
- 转换格式：`convert_conditions_to_traditional_format(conditions)` → `{field: {min/max, op: value, ...}}`

### Dependencies

#### Internal
- `app/models/screening` - 筛选条件模型与字段定义

<!-- MANUAL: Custom project notes can be added below -->
