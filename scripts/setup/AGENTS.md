<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# setup

## Purpose
系统初始化与数据库环境搭建脚本集合，负责 MongoDB/Redis 的安装引导、集合与索引创建、系统配置生成及连接验证，确保 TradingAgents 可在有或无数据库环境下正常运行（自动降级到文件缓存）。

## Key Files

| File | Description |
|------|-------------|
| `init_database.py` | 数据库初始化脚本：创建 MongoDB 集合（stock_data、analysis_results、user_sessions、configurations）及索引，插入默认配置（缓存 TTL、LLM 模型），初始化 Redis 缓存结构与统计，测试读写功能 |
| `init_mongodb_indexes.py` | MongoDB 索引初始化脚本：为 stock_basic_info 集合创建联合唯一索引 (code, source) 及常用查询字段索引（行业、市值、PE/PB 等），为 sync_status 集合创建任务状态查询索引；仅创建索引不删除已有索引 |
| `initialize_system.py` | 系统初始化主脚本：创建配置目录与缓存目录，自动检测 MongoDB/Redis 可用性，生成 database_config.json 配置文件（支持自动降级到文件缓存），测试缓存系统功能，生成使用指南 |
| `setup_databases.py` | 数据库环境安装脚本：自动安装 Python 依赖包（pymongo、redis、hiredis），根据操作系统（Windows/Linux）提供 MongoDB 和 Redis 安装指南，支持 Docker 一键部署方式，测试数据库连接 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- Apache 2.0 开源模块
- 初始化顺序：先运行 `setup_databases.py` 安装依赖与数据库 → 再运行 `initialize_system.py` 生成配置 → 最后运行 `init_database.py` 创建集合与索引
- `init_mongodb_indexes.py` 可独立运行，用于修复或补充索引，不会删除已有索引
- 系统支持无数据库运行（自动降级到文件缓存），但建议安装 MongoDB + Redis 以获得最佳性能
- 环境变量配置参考项目根目录 `.env.example`

### Testing Requirements
- 测试数据库连接：`python scripts/setup/setup_databases.py --test`
- 测试系统状态：`python scripts/validation/check_system_status.py`
- 单元测试：`python -m pytest tests/ -k "setup" -v`

### Common Patterns
- 初始化脚本模式：检测环境 → 创建目录/集合/索引 → 写入默认配置 → 测试功能 → 输出结果
- 数据库管理器获取：`from tradingagents.config.database_manager import get_database_manager`
- 缓存实例获取：`from tradingagents.dataflows.integrated_cache import get_cache`
- MongoDB 索引创建：使用 `pymongo` 的 `create_index` 方法，联合唯一索引用 `unique=True`

## Dependencies

### Internal
- `tradingagents/config/database_manager.py` - 数据库管理器，提供 MongoDB/Redis 连接与操作
- `tradingagents/dataflows/integrated_cache.py` - 集成缓存系统
- `tradingagents/utils/logging_manager.py` - 日志管理
- `tradingagents/config/runtime_settings.py` - 运行时配置（时区等）

### External
- MongoDB 4.4+ - 主数据库
- Redis 5.0+ - 缓存与队列
- pymongo 4.6+ - MongoDB Python 驱动
- redis 5.0+ - Redis Python 客户端
- hiredis 2.2+ - Redis 高性能解析器

<!-- MANUAL: Custom project notes can be added below -->
