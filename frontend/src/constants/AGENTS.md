<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# constants

## Purpose
常量定义层，提供分析师配置、报告映射和模型供应商映射等静态数据，供分析页面和报告展示使用。

## Key Files

| File | Description |
|------|-------------|
| `analysts.ts` | 分析师定义：常规分析师（市场/基本面/新闻/社媒）、投资大师（13位）、名称-ID 映射、模型-供应商映射 |
| `reports.ts` | 报告映射：分析报告 key → 标题/分类映射，涵盖分析师团队/投资大师/研究团队/交易团队/风险管理/最终决策 |

## For AI Agents

### Working In This Directory
- 分析师分组：`ANALYSTS`（常规，group: 'regular'）+ `MASTER_ANALYSTS`（大师，group: 'master'）= `ALL_ANALYSTS`
- 名称-ID 转换：`convertAnalystNamesToIds()` / `convertAnalystIdsToNames()` 通过 `ANALYST_NAME_TO_ID_MAP` 双向映射
- 报告分类：分析师团队 / 投资大师 / 研究团队 / 交易团队 / 风险管理团队 / 最终决策 / 其他
- 模型供应商：`MODEL_TO_PROVIDER_MAP` 映射模型名 → 供应商（dashscope/openai/google/deepseek/zhipu）

### Testing Requirements
- 映射完整性：验证 `ANALYST_NAME_TO_ID_MAP` 与 `ALL_ANALYSTS` 数据一致
- 报告映射：验证 `REPORT_MAPPINGS` 的 key 与后端返回的报告字段匹配

### Common Patterns
- 获取分析师：`getAnalystById('market')` 或 `getAnalystByName('市场分析师')`
- 验证分析师名：`isValidAnalyst('巴菲特')` → `true`
- 报告标题查找：`REPORT_NAME_MAP['market_report']` → `'📈 市场技术分析'`
- 模型供应商查找：`getProviderByModel('gpt-4o')` → `'openai'`
- 默认分析师：`DEFAULT_ANALYSTS = ['市场分析师', '基本面分析师']`

## Dependencies

### Internal
- 无内部依赖（纯常量定义层）

### External
- 无外部依赖

<!-- MANUAL: Custom project notes can be added below -->
