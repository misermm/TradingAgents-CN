<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# examples

## Purpose
使用示例与演示代码 (Apache 2.0)，展示核心库的各种用法，包括基础分析、批量分析、自定义分析、数据配置和新闻过滤等。

## Key Files

| File | Description |
|------|-------------|
| `README.md` | 示例使用说明 |
| `simple_analysis_demo.py` | 简单分析演示 |
| `batch_analysis.py` | 批量股票分析 |
| `custom_analysis_demo.py` | 自定义分析演示 |
| `demo_deepseek_analysis.py` | DeepSeek 模型分析演示 |
| `demo_news_filtering.py` | 新闻过滤演示 |
| `stock_query_examples.py` | 股票查询示例 |
| `config_management_demo.py` | 配置管理演示 |
| `token_tracking_demo.py` | Token 用量追踪演示 |
| `test_installation.py` | 安装验证脚本 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `crawlers/` | 爬虫示例：社交媒体数据采集 |
| `dashscope_examples/` | 阿里百炼 DashScope 使用示例 |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源模块
- 示例可直接运行验证功能
- `test_installation.py` 可用于验证环境配置

### Testing Requirements
- 示例无需测试框架，直接运行验证

### Common Patterns
- 演示模式：导入核心库 → 配置参数 → 执行分析 → 打印结果
- 测试安装：运行 test_installation.py 验证依赖

## Dependencies

### Internal
- `tradingagents/` - 所有示例调用核心库

### External
- 各示例依赖对应的 LLM API Key

<!-- MANUAL: Custom project notes can be added below -->
