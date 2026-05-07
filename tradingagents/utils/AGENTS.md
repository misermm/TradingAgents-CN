<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# utils

## Purpose
通用工具函数模块，提供日志管理、股票代码校验、新闻过滤、公司名称处理等跨模块复用的工具。

## Key Files

| File | Description |
|------|-------------|
| `logging_init.py` | 日志初始化配置 |
| `logging_manager.py` | 日志管理器，统一日志格式和输出 |
| `stock_utils.py` | 股票代码工具函数 |
| `stock_validator.py` | 股票代码校验器 |
| `company_utils.py` | 公司名称处理工具 |
| `news_filter.py` | 新闻过滤器 |
| `enhanced_news_filter.py` | 增强版新闻过滤器 |
| `enhanced_news_retriever.py` | 增强版新闻检索器 |
| `news_filter_integration.py` | 新闻过滤集成 |
| `dataflow_utils.py` | 数据流工具函数 |
| `tool_logging.py` | 工具调用日志 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 日志使用：通过 `logging_manager.py` 获取统一 logger
- 股票校验：`stock_validator.py` 验证股票代码格式
- 新闻过滤：`news_filter.py` 过滤无关新闻

### Testing Requirements
- 工具测试：`python -m pytest tests/ -k "utils" -v`

### Common Patterns
- 日志模式：`from tradingagents.utils.logging_init import get_logger`
- 校验模式：`StockValidator.validate(code)` → 返回标准化代码

## Dependencies

### Internal
- 被所有模块引用

### External
- Python logging - 日志框架

<!-- MANUAL: Custom project notes can be added below -->
