<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# queue

## Purpose
队列辅助子包。集中定义 Redis 键名常量与队列操作的辅助函数，供 `queue_service.py` 做薄委托。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，导出所有键名常量和辅助函数 |
| `keys.py` | Redis 键名与配置常量：就绪列表、任务/批次前缀、处理中/已完成/失败集合、并发控制键、可见性超时键、并发限制常量 |
| `helpers.py` | Redis 操作辅助函数：用户/全局并发限制检查、标记/取消任务处理中、设置/清除可见性超时 |

## For AI Agents

### Working In This Directory
- 所有键名以 `qa:` 为前缀，集中管理避免硬编码
- 开源版全局最大并发限制为 3（`GLOBAL_CONCURRENT_LIMIT`），用户默认并发限制为 3（`DEFAULT_USER_CONCURRENT_LIMIT`）
- 可见性超时默认 300 秒（5 分钟），防止任务被重复消费
- `helpers.py` 中所有函数均为 `async`，接收 `redis.asyncio.Redis` 实例
- 并发控制基于 Redis Set 实现：`SET_PROCESSING` 全局集合 + `USER_PROCESSING_PREFIX` 用户集合

### Common Patterns
- 检查并发限制：`await check_user_concurrent_limit(r, user_id, limit)` / `await check_global_concurrent_limit(r, limit)`
- 标记处理中：`await mark_task_processing(r, task_id, user_id)`
- 取消标记：`await unmark_task_processing(r, task_id, user_id)`
- 设置超时：`await set_visibility_timeout(r, task_id, worker_id, timeout_seconds)`

### Dependencies

#### Internal
- `app/core/database` - Redis 连接

#### External
- Redis (aioredis) - 队列存储与并发控制

<!-- MANUAL: Custom project notes can be added below -->
