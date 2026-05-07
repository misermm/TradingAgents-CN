<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# analysts

## Purpose
分析师智能体，从不同维度分析股票：基本面、市场行情、新闻舆情、社交媒体和A股市场特色。

## Key Files

| File | Description |
|------|-------------|
| `fundamentals_analyst.py` | 基本面分析师：财务数据、估值指标、盈利能力 |
| `market_analyst.py` | 市场分析师：行情数据、技术指标、市场情绪 |
| `news_analyst.py` | 新闻分析师：新闻舆情、事件驱动分析 |
| `social_media_analyst.py` | 社交媒体分析师：社区讨论、情绪分析 |
| `china_market_analyst.py` | A股市场分析师：A股特色指标和政策分析 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 每个分析师使用 LangChain Agent 模式
- 分析师通过工具获取数据并生成分析报告
- 新增分析师需创建文件并在 analyst_registry 注册

### Testing Requirements
- 分析师测试：`python -m pytest tests/ -k "analyst" -v`

### Common Patterns
- 分析师模式：定义工具列表 → 创建 Agent → 执行分析 → 返回结构化结果

## Dependencies

### Internal
- `tradingagents/dataflows/` - 数据获取
- `tradingagents/llm_clients/` - LLM 调用
- `tradingagents/agents/utils/` - 注册表和工具

### External
- LangChain - Agent 框架

<!-- MANUAL: Custom project notes can be added below -->
