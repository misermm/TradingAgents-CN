<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# progress

## Purpose
进度追踪子包。对分析任务的进度跟踪与日志处理进行结构化组织，提供 Redis/文件双存储的进度追踪器和日志自动解析处理器。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，导出 `RedisProgressTracker`、`get_progress_by_id`、`ProgressLogHandler`、`get_progress_log_handler`、`register_analysis_tracker`、`unregister_analysis_tracker` |
| `tracker.py` | 进度追踪器 `RedisProgressTracker`：动态生成分析步骤、估算耗时、更新进度、Redis/文件双存储；`get_progress_by_id` 按任务 ID 查询进度 |
| `log_handler.py` | 日志处理器 `ProgressLogHandler`：监控 TradingAgents 日志输出，通过正则匹配自动识别分析阶段并更新进度追踪器 |

## For AI Agents

### Working In This Directory
- `RedisProgressTracker` 根据分析师列表和研究深度动态生成步骤，每步有权重用于计算进度百分比
- 耗时估算基于实测数据：分析师数量乘数、研究深度级别、模型速度系数
- 存储优先使用 Redis（`REDIS_ENABLED=true`），降级为本地文件 `./data/progress/{task_id}.json`
- `ProgressLogHandler` 是 `logging.Handler` 子类，通过正则匹配日志消息识别分析阶段
- 全局单例 `get_progress_log_handler()` 注册到 `agents`、`tradingagents` 等日志记录器
- `register_analysis_tracker` / `unregister_analysis_tracker` 用于绑定/解绑任务与追踪器

### Common Patterns
- 创建追踪器：`tracker = RedisProgressTracker(task_id, analysts, research_depth, llm_provider)`
- 更新进度：`tracker.update_progress(progress_update)` - 接受 dict 或字符串
- 标记完成/失败：`tracker.mark_completed()` / `tracker.mark_failed(reason)`
- 查询进度：`get_progress_by_id(task_id)` → `dict | None`
- 注册日志监控：`register_analysis_tracker(task_id, tracker)`

### Dependencies

#### Internal
- `tradingagents/llm_clients/provider_keys` - LLM Provider 标准化

#### External
- Redis - 进度数据存储（可选）
- threading - 日志处理器线程安全

<!-- MANUAL: Custom project notes can be added below -->
