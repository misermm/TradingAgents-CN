<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests/middleware

## Purpose
中间件测试，验证 HTTP 请求中间件功能（请求追踪、日志上下文注入等）。

## Key Files

| File | Description |
|------|-------------|
| `test_trace_id.py` | 测试 RequestIDMiddleware：验证 X-Trace-ID / X-Request-ID 响应头生成（UUID 格式）、日志中注入 trace_id 上下文 |

## For AI Agents

### Working In This Directory
- 被测中间件：`app.middleware.request_id.RequestIDMiddleware`
- 测试验证两个维度：HTTP 响应头 + 日志输出
- trace_id 为 UUID v4 格式，同时出现在响应头和日志格式中
- 日志捕获使用 `io.StringIO` + 临时 StreamHandler

### Testing Requirements
- 运行：`python -m pytest tests/middleware/ -v`
- 无需外部服务，使用 FastAPI TestClient

### Common Patterns
- `FastAPI + TestClient` 构建最小测试应用
- `LoggingContextFilter` 注入 trace_id 到日志格式 `%(trace_id)s`
- UUID 正则校验：`^[0-9a-f]{8}-[0-9a-f]{4}-...`

## Dependencies

### Internal
- `app.middleware.request_id` - 请求 ID 中间件
- `app.core.logging_config` - 日志配置
- `app.core.logging_context` - 日志上下文过滤器

### External
- pytest - 测试框架
- FastAPI TestClient - HTTP 测试客户端

<!-- MANUAL: Custom project notes can be added below -->
