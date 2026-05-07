<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# trader

## Purpose
交易员智能体，基于所有分析结果做出最终交易决策（买入/卖出/持有）。

## Key Files

| File | Description |
|------|-------------|
| `trader.py` | 交易员：综合分析师、研究员、主控和风控结果，做出最终交易决策 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 交易员是分析流程的最终节点
- 输入所有前置分析结果，输出交易决策

### Testing Requirements
- 交易决策测试：`python -m pytest tests/ -k "trader" -v`

### Common Patterns
- 决策模式：接收所有分析输入 → LLM 综合判断 → 输出买入/卖出/持有建议

## Dependencies

### Internal
- `tradingagents/agents/` - 所有前置智能体结果
- `tradingagents/llm_clients/` - LLM 调用

### External
- LangChain - Agent 框架

<!-- MANUAL: Custom project notes can be added below -->
