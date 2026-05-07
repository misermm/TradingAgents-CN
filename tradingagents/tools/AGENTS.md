<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tools

## Purpose
工具函数模块，为智能体提供可调用的工具，包括统一新闻获取和技术指标计算。

## Key Files

| File | Description |
|------|-------------|
| `unified_news_tool.py` | 统一新闻工具，聚合多源新闻数据供智能体使用 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `analysis/` | 分析工具：技术指标计算 (indicators.py) |

## For AI Agents

### Working In This Directory
- 新闻工具：`unified_news_tool.py` 提供统一的新闻获取接口
- 技术指标：`analysis/indicators.py` 提供技术分析指标计算
- 工具通过 LangChain Tool 机制注册到智能体

### Testing Requirements
- 工具测试：`python -m pytest tests/ -k "tool" -v`

### Common Patterns
- LangChain Tool 模式：定义工具函数 → @tool 装饰器 → 注册到 Agent

## Dependencies

### Internal
- `tradingagents/dataflows/` - 新闻和数据获取
- `tradingagents/agents/` - 智能体调用工具

### External
- LangChain - Tool 框架

<!-- MANUAL: Custom project notes can be added below -->
