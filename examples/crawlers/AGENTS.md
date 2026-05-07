<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# examples/crawlers

## Purpose
社交媒体与内部消息爬虫示例 (Apache 2.0)，演示如何从微博、抖音等平台采集股票相关社媒数据，以及内部消息数据的爬取与入库流程。

## Key Files

| File | Description |
|------|-------------|
| `social_media_crawler.py` | 社媒消息爬虫：微博/抖音数据采集、清洗、情绪分析、入库 |
| `internal_message_crawler.py` | 内部消息爬虫：内部消息数据采集与入库 |
| `message_crawler_scheduler.py` | 爬虫调度器：统一调度社媒与内部消息爬取任务 |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源模块
- 当前使用模拟数据（`_simulate_*_api`），实际部署需替换为真实 API 调用
- 爬虫基类 `SocialMediaCrawler` 提供文本清洗、情绪分析、关键词提取、重要性评估等通用方法
- 数据通过 `app/services/` 入库，依赖 MongoDB

### Testing Requirements
- 直接运行 `python social_media_crawler.py` 验证
- 需要后端服务与数据库运行

### Common Patterns
- 异步爬虫模式：`async with XxxCrawler() as crawler: await crawler.crawl_stock_messages(symbol)`
- 数据标准化流程：原始数据 → 清洗 → 情绪分析 → 评估重要性/可信度 → 入库
- 调度器模式：`crawl_and_save_social_media(symbols, platforms)` 批量爬取并保存

## Dependencies

### Internal
- `app/core/database.py` - 数据库初始化
- `app/services/social_media_service.py` - 社媒消息服务
- `app/services/internal_message_service.py` - 内部消息服务

### External
- `aiohttp` - 异步 HTTP 客户端

<!-- MANUAL: Custom project notes can be added below -->
