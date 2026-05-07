<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# examples/dashscope_examples

## Purpose
阿里百炼 DashScope 大模型使用示例 (Apache 2.0)，演示如何使用阿里百炼（通义千问）系列模型运行 TradingAgents 框架进行股票分析。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化文件 |
| `demo_dashscope.py` | DashScope 基础演示：使用 TradingAgentsGraph 运行分析 |
| `demo_dashscope_chinese.py` | 中文优化演示：针对中文用户的股票分析，使用 ChatDashScope 适配器 |
| `demo_dashscope_no_memory.py` | 禁用记忆功能演示：临时关闭记忆功能的分析流程 |
| `demo_dashscope_simple.py` | 简化演示：基本的 LLM 连通性测试 |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源模块
- 运行前需配置 `DASHSCOPE_API_KEY` 环境变量
- 所有示例依赖 `tradingagents/` 核心库

### Testing Requirements
- 直接运行各 `demo_*.py` 脚本验证

### Common Patterns
- 标准流程：加载环境变量 → 初始化 TradingAgentsGraph → 执行分析 → 输出结果
- 中文适配：使用 `ChatDashScope` 适配器替代默认 LLM

## Dependencies

### Internal
- `tradingagents/graph/trading_graph.py` - 分析图引擎
- `tradingagents/llm_adapters` - DashScope LLM 适配器

### External
- `DASHSCOPE_API_KEY` - 阿里百炼 API 密钥
- `python-dotenv` - 环境变量加载

<!-- MANUAL: Custom project notes can be added below -->
