<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# app

## Purpose
FastAPI 后端服务 (专有许可证，商用需授权)。提供 REST API、WebSocket、SSE 推送，集成核心分析引擎，管理用户认证、股票数据、分析任务队列、定时调度和数据同步。

## Key Files

| File | Description |
|------|-------------|
| `main.py` | FastAPI 应用入口，初始化数据库、路由、中间件、定时任务 |
| `worker.py` | Worker 入口，异步任务执行器 |
| `__main__.py` | 模块运行入口 |
| `database.py` | 数据库连接管理 (兼容层) |
| `LICENSE` | 专有许可证文件 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `core/` | 核心配置：Settings、数据库连接、日志、Redis、限流 (see `core/AGENTS.md`) |
| `routers/` | API 路由：30+ 路由模块覆盖所有业务端点 (see `routers/AGENTS.md`) |
| `services/` | 业务逻辑：分析、股票数据、调度、队列等 (see `services/AGENTS.md`) |
| `worker/` | 异步任务：数据同步、分析执行 (see `worker/AGENTS.md`) |
| `models/` | 数据模型：Pydantic 模型定义 (see `models/AGENTS.md`) |
| `middleware/` | 中间件：错误处理、操作日志、限流、请求ID (see `middleware/AGENTS.md`) |
| `schemas/` | 请求/响应 Schema |
| `utils/` | 工具函数：API Key、时区、交易时间、报告导出 |
| `constants/` | 常量：模型能力定义 |
| `scripts/` | 运维脚本：数据库迁移、供应商初始化 |

## For AI Agents

### Working In This Directory
- 专有许可证模块，商用需联系 hsliup@163.com
- 应用配置通过 `core/config.py` 的 Settings 类管理 (Pydantic V2)
- 数据库连接通过 `core/database.py` 管理 MongoDB 和 Redis 连接池
- 新增 API 路由需在 `routers/` 添加并在 `main.py` 注册
- 新增业务逻辑在 `services/` 中实现
- 异步任务在 `worker/` 中定义

### Testing Requirements
- API 测试：`python -m pytest tests/ -k "api" -v`
- 服务测试：`python -m pytest tests/services/ -v`
- 中间件测试：`python -m pytest tests/middleware/ -v`

### Common Patterns
- 路由定义：`router = APIRouter()` → 定义端点 → 在 main.py 注册
- 服务调用：注入 Service 实例 → 调用业务方法 → 返回 Response
- 任务队列：QueueService 入队 → Worker 出队执行 → 进度通过 SSE 推送
- 配置获取：`from app.core.config import get_settings` → 使用 Settings 属性

## Dependencies

### Internal
- `tradingagents/` - 核心分析引擎，被 services 和 worker 调用
- `frontend/` - 前端通过 API 调用此后端

### External
- FastAPI + Uvicorn - Web 框架
- MongoDB (Motor) - 异步数据库驱动
- Redis (aioredis) - 缓存与消息队列
- Pydantic V2 - 数据验证
- python-jose - JWT 认证
- APScheduler - 定时任务调度

<!-- MANUAL: Custom project notes can be added below -->
