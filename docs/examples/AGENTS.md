<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs/examples

## Purpose
TradingAgents 框架使用示例文档，覆盖从基础到高级的完整用法，帮助用户快速上手并掌握框架核心功能。

## Key Files

| File | Description |
|------|-------------|
| `basic-examples.md` | 基础使用示例：单股分析、自定义配置、批量分析、LLM 对比、历史回测、实时监控、错误处理、结果保存（8 个示例） |
| `advanced-examples.md` | 高级使用示例：自定义量化分析师、多资产组合优化、实时交易系统、策略回测框架（4 个示例） |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- 所有示例基于 `TradingAgentsGraph` 核心入口，核心用法：`from tradingagents.graph.trading_graph import TradingAgentsGraph`
- 基础示例使用 `DEFAULT_CONFIG.copy()` 作为配置起点
- 高级示例涉及 `BaseAnalyst` 继承、`scipy.optimize` 优化、`asyncio` 异步等模式
- 示例代码为教学用途，非生产就绪

### Testing Requirements
- 文档无需运行测试
- 示例代码依赖 API 密钥和网络连接

### Common Patterns
- 分析入口：`ta = TradingAgentsGraph(debug=True, config=config)` → `state, decision = ta.propagate(symbol, date)`
- 配置优化：调整 `max_debate_rounds`、`deep_think_llm`、`quick_think_llm`、`online_tools`
- 批量分析：循环调用 `propagate`，结果收集为 `pd.DataFrame`
- 错误处理：指数退避重试 + 结果验证
- 结果保存：JSON / Pickle 序列化

## Dependencies

### Internal
- `tradingagents/graph/trading_graph.py` - 示例代码的核心依赖
- `tradingagents/default_config.py` - DEFAULT_CONFIG 配置来源
- `tradingagents/agents/analysts/base_analyst.py` - 高级示例中自定义分析师的基类

### External
- `pandas` - 批量分析结果整理
- `numpy` / `scipy` - 高级示例中的量化计算与优化
- `matplotlib` - 回测可视化
- `asyncio` - 实时交易系统示例

<!-- MANUAL: Custom project notes can be added below -->
