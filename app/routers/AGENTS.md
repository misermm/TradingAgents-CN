<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# routers

## Purpose
API 路由模块，定义 30+ REST API 端点，覆盖分析、认证、股票数据、同步、筛选、配置等所有业务功能。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 路由注册，导出所有路由模块 |
| `analysis.py` | 分析任务 API：提交、查询、取消 |
| `auth.py` | 认证 API：登录、注册、Token 刷新 |
| `auth_db.py` | 数据库认证 API |
| `stocks.py` | 股票列表 API |
| `stock_data.py` | 股票数据 API：行情、基本面 |
| `financial_data.py` | 财务数据 API |
| `news_data.py` | 新闻数据 API |
| `reports.py` | 分析报告 API |
| `screening.py` | 股票筛选 API |
| `favorites.py` | 自选股 API |
| `tags.py` | 标签管理 API |
| `sync.py` | 数据同步 API |
| `stock_sync.py` | 股票数据同步 API |
| `multi_source_sync.py` | 多源同步 API |
| `multi_period_sync.py` | 多周期同步 API |
| `scheduler.py` | 定时任务 API |
| `queue.py` | 任务队列 API |
| `config.py` | 系统配置 API |
| `system_config.py` | 系统配置管理 API |
| `health.py` | 健康检查 API |
| `cache.py` | 缓存管理 API |
| `database.py` | 数据库管理 API |
| `logs.py` | 日志查询 API |
| `notifications.py` | 通知 API |
| `operation_logs.py` | 操作日志 API |
| `usage_statistics.py` | 使用统计 API |
| `model_capabilities.py` | 模型能力 API |
| `local_models.py` | 本地模型 API |
| `sse.py` | SSE 推送端点 |
| `websocket_notifications.py` | WebSocket 通知端点 |
| `paper.py` | 模拟交易 API |
| `social_media.py` | 社交媒体数据 API |
| `multi_market_stocks.py` | 多市场股票 API |
| `akshare_init.py` | AkShare 初始化 API |
| `baostock_init.py` | BaoStock 初始化 API |
| `tushare_init.py` | Tushare 初始化 API |
| `historical_data.py` | 历史数据 API |
| `internal_messages.py` | 内部消息 API |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 新增路由：创建 `router = APIRouter()` → 定义端点 → 在 `__init__.py` 注册
- 路由前缀：`/api/v1/` 为默认前缀
- 认证：使用 `Depends(get_current_user)` 保护端点
- 响应格式：使用 `core/response.py` 的统一响应

### Testing Requirements
- API 测试：`python -m pytest tests/ -k "api" -v`

### Common Patterns
- 路由模式：APIRouter() → @router.get/post → 调用 Service → 返回 Response
- 认证模式：Depends(get_current_user) → 获取用户 → 权限检查

## Dependencies

### Internal
- `app/services/` - 调用业务逻辑
- `app/core/` - 配置和数据库
- `app/models/` - 请求/响应模型

### External
- FastAPI - Web 框架

<!-- MANUAL: Custom project notes can be added below -->
