<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# install

## Purpose
安装配置文件目录，存放 Docker 镜像的数据库预配置数据与说明，用于容器首次启动时快速初始化系统。

## Key Files

| File | Description |
|------|-------------|
| `database_export_config.json` | 预配置数据说明文档（JSON 格式），描述各集合的结构与用法 |
| `database_export_config_2026-04-20.json` | 实际配置数据文件，包含系统配置、用户、LLM 提供商、模型目录、市场分类等完整初始化数据 |

## For AI Agents

### Working In This Directory
- 配置数据已打包到 Docker 镜像的 `/app/install/` 目录
- 首次部署使用：`docker exec -it tradingagents-backend python scripts/import_config_and_create_user.py`
- 仅创建用户：`--create-user-only` 参数
- 覆盖已有数据：`--overwrite` 参数
- 导出当前配置：`docker exec -it tradingagents-backend python scripts/export_config.py`

### Preconfigured Collections
- `system_configs` - 系统配置参数（约 79 项）
- `users` - 默认管理员账号（admin/admin123）
- `llm_providers` - 8 个 LLM 服务提供商
- `model_catalog` - 15+ 个可用模型
- `market_categories` - 沪深A股/港股/美股
- `market_quotes` - 实时行情示例数据（约 5760 条）
- `stock_basic_info` - 股票基础信息（约 5684 条）

### Common Patterns
- 导入配置：通过 `scripts/import_config_and_create_user.py` 读取本目录 JSON 文件写入 MongoDB
- 导出配置：通过 `scripts/export_config.py` 将 MongoDB 数据导出为 JSON

## Dependencies

### Internal
- `scripts/import_config_and_create_user.py` - 配置导入脚本
- `scripts/export_config.py` - 配置导出脚本
- MongoDB - 配置数据存储目标

<!-- MANUAL: Custom project notes can be added below -->
