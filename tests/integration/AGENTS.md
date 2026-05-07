<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests/integration

## Purpose
集成测试包，存放需要外部服务（MongoDB、Redis、LLM API、数据源）的端到端集成测试。默认被 `-m "not integration"` 标记跳过。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，标记为集成测试包 |

## For AI Agents

### Working In This Directory
- 集成测试需要真实的外部服务连接
- 默认不运行，必须显式使用 `-m integration` 标记
- 新增集成测试应标记 `@pytest.mark.integration`

### Testing Requirements
- 运行：`python -m pytest tests/integration/ -m integration -v`
- 需要运行中的 MongoDB、Redis 和配置正确的 API 密钥

### Common Patterns
- 使用 `@pytest.mark.integration` 装饰器标记
- 测试真实服务连接和数据获取

## Dependencies

### Internal
- `tradingagents/` - 核心库
- `app/` - 后端服务

### External
- pytest - 测试框架
- MongoDB / Redis - 数据库服务
- 各数据源 API - 网络访问

<!-- MANUAL: Custom project notes can be added below -->
