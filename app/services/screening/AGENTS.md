<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# screening

## Purpose
筛选评估工具子包。从 `ScreeningService` 拆分出的 DSL 解析与条件评估逻辑，支持基本面快照评估和技术面 DataFrame 评估。

## Key Files

| File | Description |
|------|-------------|
| `eval_utils.py` | 评估工具函数：`collect_fields_from_conditions` 递归收集条件字段；`evaluate_fund_conditions` 基本面快照评估；`evaluate_conditions` DataFrame 技术面评估（含交叉判断）；`safe_float` 安全浮点转换 |

## For AI Agents

### Working In This Directory
- 条件 DSL 为树形结构：`group` 节点含 `logic`（AND/OR）和 `children`；叶子节点含 `field`、`op`、`value`/`right_field`
- `evaluate_fund_conditions` 用于基本面快照（dict），跳过非基本面字段
- `evaluate_conditions` 用于技术面 DataFrame，支持 `cross_up`/`cross_down` 交叉判断（需最近两行数据）
- 支持的操作符：`>`、`<`、`>=`、`<=`、`==`、`!=`、`between`、`cross_up`、`cross_down`
- `safe_float` 处理 None 和 NaN，返回 `Optional[float]`

### Common Patterns
- 收集条件字段：`collect_fields_from_conditions(node, allowed_fields)` → `[field_name, ...]`
- 基本面评估：`evaluate_fund_conditions(snap, node, fund_fields)` → `bool`
- 技术面评估：`evaluate_conditions(df, node, allowed_fields, allowed_ops)` → `bool`
- 安全转换：`safe_float(value)` → `float | None`

### Dependencies

#### Internal
- 无内部依赖（纯工具函数）

#### External
- pandas - DataFrame 操作
- numpy - NaN 检测

<!-- MANUAL: Custom project notes can be added below -->
