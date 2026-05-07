<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# worker

## Purpose
异步任务执行器，处理数据同步、分析执行等耗时任务。包含各数据源的同步服务和分析 Worker。

## Key Files

| File | Description |
|------|-------------|
| `analysis_worker.py` | 分析 Worker：从队列获取任务、执行分析、推送结果 |
| `akshare_sync_service.py` | AkShare 数据同步服务 |
| `baostock_sync_service.py` | BaoStock 数据同步服务 |
| `tushare_sync_service.py` | Tushare 数据同步服务 |
| `financial_data_sync_service.py` | 财务数据同步服务 |
| `news_data_sync_service.py` | 新闻数据同步服务 |
| `hk_sync_service.py` | 港股数据同步服务 |
| `hk_data_service.py` | 港股数据处理服务 |
| `us_sync_service.py` | 美股数据同步服务 |
| `us_data_service.py` | 美股数据处理服务 |
| `multi_period_sync_service.py` | 多周期数据同步服务 |
| `akshare_init_service.py` | AkShare 初始化服务 |
| `baostock_init_service.py` | BaoStock 初始化服务 |
| `tushare_init_service.py` | Tushare 初始化服务 |
| `example_sdk_sync_service.py` | SDK 同步示例 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- Worker 从 Redis 队列获取任务
- 同步服务模式：连接数据源 → 获取数据 → 写入 MongoDB → 更新进度
- 分析 Worker：获取任务 → 调用 TradingAgentsGraph → 保存结果 → 通知前端

### Testing Requirements
- Worker 测试：`python -m pytest tests/ -k "worker" -v`
- 同步测试：`python -m pytest tests/ -k "sync" -v`

### Common Patterns
- 同步模式：Service 类 → 连接数据源 → 批量获取 → 写入数据库
- 分析模式：Worker → 从队列取任务 → 执行分析 → 保存结果 → SSE 通知

## Dependencies

### Internal
- `tradingagents/` - 核心分析引擎
- `app/core/` - 配置和数据库
- `app/services/` - 业务逻辑

### External
- MongoDB (Motor) - 数据存储
- Redis (aioredis) - 任务队列

<!-- MANUAL: Custom project notes can be added below -->
