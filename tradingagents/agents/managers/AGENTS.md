<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# managers

## Purpose
管理器智能体，负责协调研究员和风控辩论的流程管理。

## Key Files

| File | Description |
|------|-------------|
| `research_manager.py` | 研究管理器：协调看多/看空研究员的辩论 |
| `risk_manager.py` | 风险管理器：协调风控辩论流程 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 研究管理器控制辩论轮次和总结
- 风险管理器控制风控讨论流程

### Testing Requirements
- 管理器测试：`python -m pytest tests/ -k "manager" -v`

### Common Patterns
- 管理器模式：接收输入 → 分发给子智能体 → 收集结果 → 综合决策

## Dependencies

### Internal
- `tradingagents/agents/researchers/` - 研究员
- `tradingagents/agents/risk_mgmt/` - 风控辩论者
- `tradingagents/llm_clients/` - LLM 调用

### External
- LangChain - Agent 框架

<!-- MANUAL: Custom project notes can be added below -->
