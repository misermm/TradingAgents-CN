<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# risk_mgmt

## Purpose
风控辩论智能体，从激进、保守和中立三个视角评估投资风险，通过辩论机制形成全面的风险评估。

## Key Files

| File | Description |
|------|-------------|
| `aggresive_debator.py` | 激进辩论者：强调收益机会，倾向于承担风险 |
| `conservative_debator.py` | 保守辩论者：强调风险控制，倾向于规避风险 |
| `neutral_debator.py` | 中立辩论者：平衡风险与收益，客观评估 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 三个辩论者成组使用
- 辩论结果由风险管理器综合

### Testing Requirements
- 风控测试：`python -m pytest tests/ -k "risk" -v`

### Common Patterns
- 风控辩论模式：三方交替发言 → 风险管理器综合 → 形成风险评估

## Dependencies

### Internal
- `tradingagents/agents/masters/` - 使用主控决策
- `tradingagents/llm_clients/` - LLM 调用

### External
- LangChain - Agent 框架

<!-- MANUAL: Custom project notes can be added below -->
