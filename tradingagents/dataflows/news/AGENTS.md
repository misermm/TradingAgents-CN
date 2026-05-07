<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# news

## Purpose
新闻获取模块，从多个来源采集新闻数据：中文财经媒体、Google 新闻、Reddit 和实时新闻源。

## Key Files

| File | Description |
|------|-------------|
| `chinese_finance.py` | 中文财经新闻：东方财富、新浪财经等 |
| `google_news.py` | Google 新闻搜索 |
| `realtime_news.py` | 实时新闻获取 |
| `reddit.py` | Reddit 社区讨论数据 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 中文新闻是 A股分析的主要新闻源
- Google 新闻用于全球市场新闻
- Reddit 提供社区情绪数据
- 新闻数据通过 unified_news_tool 供智能体使用

### Testing Requirements
- 新闻测试：`python -m pytest tests/ -k "news" -v`

### Common Patterns
- 新闻获取模式：查询关键词 → 调用 API → 过滤和排序 → 返回结构化新闻

## Dependencies

### Internal
- `tradingagents/dataflows/providers/` - 数据源

### External
- Google News - 新闻搜索
- Reddit API - 社区数据

<!-- MANUAL: Custom project notes can be added below -->
