<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests/system

## Purpose
系统级测试，验证 API 端点的认证保护、敏感信息脱敏和权限控制。

## Key Files

| File | Description |
|------|-------------|
| `test_config_summary.py` | 测试 /api/system/config/summary 端点：未认证返回 401、认证后敏感字段（密码/密钥）脱敏为 `***`、URI 中凭证遮蔽 |
| `test_local_models_auth.py` | 测试 /api/local-models/scan 端点：未携带 Authorization 头返回 401 |

## For AI Agents

### Working In This Directory
- 使用 FastAPI TestClient 进行 HTTP 级别测试
- 认证通过 `AuthService.create_access_token(sub="admin")` 生成 JWT
- 敏感字段列表：MONGODB_PASSWORD、REDIS_PASSWORD、JWT_SECRET、CSRF_SECRET、STOCK_DATA_API_KEY
- URI 脱敏规则：`mongodb://user:pass@host` → `mongodb://:***@host`

### Testing Requirements
- 运行：`python -m pytest tests/system/ -v`
- 无需真实数据库，使用 TestClient

### Common Patterns
- JWT 生成：`AuthService.create_access_token(sub="admin")`
- 认证头：`{"Authorization": f"Bearer {token}"}`
- 敏感字段断言：`assert s[key] == "***"`
- 最小 FastAPI 应用：仅挂载目标路由进行隔离测试

## Dependencies

### Internal
- `app.main` - FastAPI 应用
- `app.services.auth_service` - 认证服务
- `app.routers.local_models` - 本地模型路由

### External
- pytest - 测试框架
- FastAPI TestClient - HTTP 测试客户端

<!-- MANUAL: Custom project notes can be added below -->
