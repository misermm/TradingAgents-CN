<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# middleware

## Purpose
中间件模块，提供全局请求处理：错误捕获、操作日志记录、API 限流和请求 ID 追踪。

## Key Files

| File | Description |
|------|-------------|
| `error_handler.py` | 全局错误处理中间件，捕获未处理异常并返回统一错误响应 |
| `operation_log_middleware.py` | 操作日志中间件，记录 API 请求和响应 |
| `rate_limit.py` | API 限流中间件 |
| `request_id.py` | 请求 ID 中间件，为每个请求分配唯一标识 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 中间件在 `main.py` 中注册，按顺序执行
- 请求 ID 中间件应最先注册
- 错误处理中间件应最后注册（捕获所有异常）

### Testing Requirements
- 中间件测试：`python -m pytest tests/middleware/ -v`

### Common Patterns
- 中间件模式：定义类 → 实现 dispatch() → 在 main.py 添加_middleware

## Dependencies

### Internal
- `app/core/` - 配置和日志

### External
- FastAPI - 中间件框架

<!-- MANUAL: Custom project notes can be added below -->
