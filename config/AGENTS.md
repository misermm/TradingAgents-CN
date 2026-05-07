<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# config

## Purpose
配置文件目录，存放日志配置等非代码配置文件。

## Key Files

| File | Description |
|------|-------------|
| `logging_docker.toml` | Docker 环境下的日志配置 (TOML 格式) |
| `README.md` | 配置说明文档 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 日志配置使用 Python logging TOML 格式
- Docker 环境使用 `logging_docker.toml`

### Testing Requirements
- 无需测试

### Common Patterns
- 日志配置通过 TOML 文件定义，在应用启动时加载

## Dependencies

### Internal
- `app/` - 后端使用此目录的日志配置

### External
- Python logging - 日志框架

<!-- MANUAL: Custom project notes can be added below -->
