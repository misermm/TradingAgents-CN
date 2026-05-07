<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests/config

## Purpose
配置模块测试，验证应用配置加载、环境变量覆盖、日志初始化及废弃别名兼容性。

## Key Files

| File | Description |
|------|-------------|
| `test_deprecations.py` | 测试旧版环境变量别名（API_HOST/PORT/DEBUG）映射到新键，验证 DeprecationWarning 触发 |
| `test_logging_config.py` | 测试日志配置文件选择逻辑：默认 logging.toml / Docker 环境 logging_docker.toml |
| `test_logging_json.py` | 测试 JSON 控制台格式器启用：TOML 中 json=true 时使用 SimpleJsonFormatter |
| `test_settings.py` | 测试 Settings 默认值与环境变量覆盖：MongoDB URI 构建、Redis URL 拼接（含/不含密码） |

## For AI Agents

### Working In This Directory
- 所有测试使用 monkeypatch 隔离环境变量，无需真实 .env 文件
- 日志测试依赖 tmp_path 创建临时 TOML 配置，通过 monkeypatch.chdir 切换工作目录
- Settings 测试验证 MONGO_URI 凭证拼接和 REDIS_URL 密码嵌入格式

### Testing Requirements
- 运行：`python -m pytest tests/config/ -v`
- 无需外部服务（MongoDB/Redis），全部 Mock

### Common Patterns
- `monkeypatch.setenv/delenv` 控制环境变量
- `importlib.reload` 重新加载模块以应用环境变更
- `tmp_path` pytest fixture 创建临时配置文件

## Dependencies

### Internal
- `app.core.config` - Settings 配置类
- `app.core.logging_config` - 日志初始化模块
- `app.core.logging_context` - 日志上下文过滤器

### External
- pytest - 测试框架
- pydantic-settings - 配置管理

<!-- MANUAL: Custom project notes can be added below -->
