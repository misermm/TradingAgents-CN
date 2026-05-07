<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# graph

## Purpose
LangGraph 图编排模块，定义多智能体分析流程的有向图结构。包含主图构建、信号处理、条件路由、数据预取和反思机制。

## Key Files

| File | Description |
|------|-------------|
| `trading_graph.py` | TradingAgentsGraph 主类，编排整个分析流程 |
| `propagation.py` | Propagator 类，创建初始状态和获取图参数 |
| `signal_processing.py` | SignalProcessor 类，处理信号和提取核心交易决策 |
| `conditional_logic.py` | ConditionalLogic 类，定义辩论和风险讨论的条件路由 |
| `reflection.py` | 反思机制，评估和改进分析结果 |
| `setup.py` | 图初始化设置 |
| `data_prefetch.py` | 数据预取，在分析前加载必要数据 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 核心入口：`TradingAgentsGraph` 类
- 使用方式：`ta = TradingAgentsGraph(debug=True); _, decision = ta.propagate("000001", "2024-05-10")`
- 图结构：分析师 → 研究员辩论 → 主控综合 → 风控辩论 → 交易决策
- 条件逻辑控制辩论轮次和深度

### Testing Requirements
- 图流程测试：`python -m pytest tests/ -k "graph" -v`
- 路由测试：`python -m pytest tests/test_graph_routing.py -v`

### Common Patterns
- 图构建模式：定义节点 → 添加边 → 设置条件路由 → 编译图
- 信号处理模式：收集各智能体输出 → 提取关键信号 → 生成决策

## Dependencies

### Internal
- `tradingagents/agents/` - 智能体节点
- `tradingagents/dataflows/` - 数据获取
- `tradingagents/llm_clients/` - LLM 调用

### External
- LangGraph - 图编排框架
- LangChain - Agent 工具

<!-- MANUAL: Custom project notes can be added below -->
