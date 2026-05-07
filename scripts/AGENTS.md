<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# scripts

## Purpose
运维脚本 (Apache 2.0)，包含数据同步、数据库初始化、索引创建、系统部署等脚本。

## Key Files

| File | Description |
|------|-------------|
| `akshare_sync_optimized.py` | AkShare 数据同步优化版，支持批量股票代码同步 |
| `create_default_admin.py` | 创建默认管理员账户 |
| `mongo-init.js` | MongoDB 初始化脚本 (Docker 用) |
| `redeploy.bat` | Windows 重新部署脚本 |
| `README.md` | 脚本使用说明 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `setup/` | 系统初始化脚本：数据库创建、索引初始化、消息集合创建 |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源模块
- 数据同步是分析的前置条件
- AkShare 同步：`python scripts/akshare_sync_optimized.py --codes 000001,600519 --limit 365`
- 数据库初始化：`python scripts/setup/initialize_system.py`

### Testing Requirements
- 同步脚本测试：`python -m pytest tests/ -k "sync" -v`

### Common Patterns
- 同步脚本模式：解析参数 → 连接数据源 → 批量获取 → 写入 MongoDB
- 初始化脚本模式：检查环境 → 创建集合/索引 → 写入默认数据

## Dependencies

### Internal
- `tradingagents/` - 使用核心库的数据接口

### External
- MongoDB - 数据存储目标
- AkShare/Tushare/BaoStock - 数据源

<!-- MANUAL: Custom project notes can be added below -->
