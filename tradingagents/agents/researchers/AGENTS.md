<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# researchers

## Purpose
研究员智能体，从看多和看空两个对立视角分析股票，通过辩论机制发现投资机会和风险。

## Key Files

| File | Description |
|------|-------------|
| `bull_researcher.py` | 看多研究员：寻找投资亮点和上涨理由 |
| `bear_researcher.py` | 看空研究员：发现风险因素和下跌理由 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 看多/看空研究员成对使用
- 辩论结果由研究管理器综合

### Testing Requirements
- 辩论测试：`python -m pytest tests/ -k "debate" -v`

### Common Patterns
- 辩论模式：Bull 研究员提出看多论点 → Bear 研究员反驳 → 交替辩论 → 管理器总结

## Dependencies

### Internal
- `tradingagents/agents/analysts/` - 使用分析师结果
- `tradingagents/llm_clients/` - LLM 调用

### External
- LangChain - Agent 框架

<!-- MANUAL: Custom project notes can be added below -->
