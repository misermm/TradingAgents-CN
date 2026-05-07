<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# core

## Purpose
后端核心配置模块，管理应用设置、数据库连接、日志、Redis 客户端、限流和启动验证。

## Key Files

| File | Description |
|------|-------------|
| `config.py` | Settings 类 (Pydantic V2)，管理所有运行时参数 |
| `unified_config.py` | 统一配置管理，整合多来源配置 |
| `config_bridge.py` | 配置桥接，连接 app 和 tradingagents 配置 |
| `config_compat.py` | 配置兼容层 |
| `dev_config.py` | 开发环境配置 |
| `database.py` | MongoDB 与 Redis 连接池管理 |
| `redis_client.py` | Redis 客户端封装 |
| `logging_config.py` | 日志配置 |
| `logging_context.py` | 日志上下文管理 |
| `rate_limiter.py` | API 限流器 |
| `response.py` | 统一响应格式 |
| `startup_validator.py` | 启动时配置和环境验证 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 配置获取：`from app.core.config import get_settings`
- 数据库连接：`from app.core.database import get_database`
- Redis：`from app.core.redis_client import get_redis`
- 新增配置项在 Settings 类中添加

### Testing Requirements
- 配置测试：`python -m pytest tests/config/ -v`

### Common Patterns
- 配置模式：Settings 类定义 → .env 加载 → get_settings() 获取单例
- 数据库模式：启动时初始化连接池 → 依赖注入使用 → 关闭时清理

## Dependencies

### Internal
- `tradingagents/config/` - 核心库配置

### External
- Pydantic V2 - 配置验证
- Motor - MongoDB 异步驱动
- aioredis - Redis 异步驱动

<!-- MANUAL: Custom project notes can be added below -->
