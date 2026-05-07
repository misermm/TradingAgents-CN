<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# config

## Purpose
配置管理模块，管理环境变量、数据库配置、供应商设置、运行时参数和使用量追踪。支持 .env 文件和 MongoDB 持久化配置。

## Key Files

| File | Description |
|------|-------------|
| `config_manager.py` | ConfigManager 类，统一配置管理入口 |
| `database_config.py` | 数据库连接配置 |
| `database_manager.py` | DatabaseManager 类，数据库管理操作 |
| `env_utils.py` | 环境变量工具函数 |
| `mongodb_storage.py` | MongoDB 存储后端，配置持久化 |
| `providers_config.py` | LLM 供应商配置管理 |
| `runtime_settings.py` | 运行时设置，动态参数 |
| `tushare_config.py` | Tushare 专属配置 (Token 等) |
| `usage_models.py` | 使用量数据模型 (Token 计费等) |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 配置获取：`ConfigManager` 提供统一配置访问
- 环境变量：通过 `env_utils.py` 读取 .env 文件
- 供应商配置：`providers_config.py` 管理 API Key 和模型选择
- 数据库配置：`database_config.py` 管理 MongoDB/Redis 连接

### Testing Requirements
- 配置测试：`python -m pytest tests/ -k "config" -v`

### Common Patterns
- 配置加载：.env 文件 → env_utils 解析 → ConfigManager 合并 → 运行时使用
- 持久化配置：ConfigManager → mongodb_storage → MongoDB 存储

## Dependencies

### Internal
- 被所有其他模块引用

### External
- python-dotenv - .env 文件解析
- Pydantic - 配置验证
- MongoDB - 配置持久化

<!-- MANUAL: Custom project notes can be added below -->
