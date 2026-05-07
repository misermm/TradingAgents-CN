<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# services

## Purpose
业务逻辑层，实现所有后端业务功能，包括分析服务、股票数据、调度、队列、筛选、认证等。是路由层和数据层之间的核心桥梁。

## Key Files

| File | Description |
|------|-------------|
| `analysis_service.py` | 分析服务：单股/批量分析任务提交、执行、进度追踪 |
| `stock_data_service.py` | 股票数据服务：基础信息和行情数据 |
| `scheduler_service.py` | 调度服务：定时任务注册与管理 |
| `queue_service.py` | 队列服务：任务入队、出队、状态管理 |
| `auth_service.py` | 认证服务：用户登录、注册、Token 管理 |
| `user_service.py` | 用户服务：用户信息管理 |
| `screening_service.py` | 筛选服务：股票条件筛选 |
| `enhanced_screening_service.py` | 增强筛选服务 |
| `database_screening_service.py` | 数据库筛选服务 |
| `favorites_service.py` | 自选股服务 |
| `tags_service.py` | 标签管理服务 |
| `financial_data_service.py` | 财务数据服务 |
| `historical_data_service.py` | 历史数据服务 |
| `news_data_service.py` | 新闻数据服务 |
| `social_media_service.py` | 社交媒体服务 |
| `notifications_service.py` | 通知服务 |
| `config_service.py` | 配置服务 |
| `config_provider.py` | 配置供应商 |
| `database_service.py` | 数据库管理服务 |
| `operation_log_service.py` | 操作日志服务 |
| `usage_statistics_service.py` | 使用统计服务 |
| `model_capability_service.py` | 模型能力服务 |
| `quotes_service.py` | 行情服务 |
| `quotes_ingestion_service.py` | 行情数据摄入服务 |
| `foreign_stock_service.py` | 外国股票服务 |
| `unified_stock_service.py` | 统一股票服务 |
| `simple_analysis_service.py` | 简化分析服务 |
| `internal_message_service.py` | 内部消息服务 |
| `log_export_service.py` | 日志导出服务 |
| `data_consistency_checker.py` | 数据一致性检查 |
| `memory_state_manager.py` | 内存状态管理 |
| `redis_progress_tracker.py` | Redis 进度追踪 |
| `progress_log_handler.py` | 进度日志处理 |
| `basics_sync_service.py` | 基础数据同步服务 |
| `websocket_manager.py` | WebSocket 连接管理 |
| `__init__.py` | 包初始化 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `analysis/` | 分析子模块 |
| `basics_sync/` | 基础数据同步：处理逻辑和工具函数 |
| `data_sources/` | 数据源适配：AkShare 适配器、基础适配器、管理器 |
| `database/` | 数据库操作：备份、清理、序列化、状态检查 |
| `enhanced_screening/` | 增强筛选工具 |
| `progress/` | 进度追踪：日志处理和追踪器 |
| `queue/` | 队列辅助：帮助函数和键定义 |
| `screening/` | 筛选评估工具 |

## For AI Agents

### Working In This Directory
- 服务层是业务逻辑核心，路由层调用服务层
- 新增业务功能在 services/ 创建服务类
- 服务通常接收 MongoDB/Redis 连接，操作数据并返回结果
- 分析服务集成 `tradingagents/` 核心库

### Testing Requirements
- 服务测试：`python -m pytest tests/services/ -v`

### Common Patterns
- 服务模式：Service 类 → 注入数据库连接 → 实现业务方法 → 路由调用
- 进度追踪：RedisProgressTracker → 写入 Redis → SSE 推送到前端

## Dependencies

### Internal
- `tradingagents/` - 核心分析引擎
- `app/core/` - 配置和数据库连接
- `app/models/` - 数据模型

### External
- MongoDB (Motor) - 数据存储
- Redis (aioredis) - 缓存和队列
- Pydantic - 数据验证

<!-- MANUAL: Custom project notes can be added below -->
