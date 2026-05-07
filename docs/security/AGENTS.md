<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs/security

## Purpose
安全文档，提供 API 密钥安全管理和认证系统改进方案。

## Key Files

| File | Description |
|------|-------------|
| `api_keys_security.md` | API 密钥安全指南：禁止硬编码/提交 .env/日志输出完整密钥、环境变量最佳实践、文件权限设置、.gitignore 配置、密钥轮换策略、泄露应急响应、安全检查清单 |
| `auth_system_improvement.md` | 认证系统改进方案：从配置文件明文密码迁移到数据库哈希存储、动态用户管理、新 API 端点（创建用户/修改密码/重置密码）、用户权限和状态管理、向后兼容策略、部署建议 |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源文档
- API 密钥安全是强制规范，违反即安全漏洞
- 认证系统改进方案已实施：`app/services/user_service.py` + `app/routers/auth_db.py`
- 迁移工具：`scripts/migrate_auth_to_db.py`

### Testing Requirements
- 文档无需运行测试
- 安全验证：检查 .gitignore 包含 .env、代码无硬编码密钥

### Common Patterns
- 密钥脱敏：`api_key[:12] + "..."`
- 密码存储：SHA-256 哈希（建议升级 bcrypt）
- 认证端点迁移：`/api/auth/` → `/api/auth-db/`
- JWT 认证：`AuthService.create_access_token(sub="admin")`
- 安全检查清单：.gitignore、无硬编码、文件权限 600、密钥轮换、使用监控

## Dependencies

### Internal
- `app/services/user_service.py` - 用户管理服务
- `app/routers/auth_db.py` - 数据库认证 API
- `scripts/migrate_auth_to_db.py` - 认证迁移脚本

### External
- 无外部依赖

<!-- MANUAL: Custom project notes can be added below -->
