<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# database

## Purpose
数据库操作子包。从 `DatabaseService` 拆分出的功能模块，涵盖备份/恢复、数据清理、文档序列化、状态检查。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，导出 `status_checks`、`backups`、`cleanup`、`serialization` 四个子模块 |
| `backups.py` | 备份与导入导出：原生 mongodump 备份、Python 备份、数据导入（单集合/多集合）、数据导出（JSON/CSV/XLSX）、敏感字段脱敏 |
| `cleanup.py` | 数据清理：按天数清理旧分析任务、分析结果、用户会话、登录尝试、操作日志 |
| `serialization.py` | 序列化工具：`serialize_document` 将 MongoDB 特殊类型（ObjectId、datetime）转为 JSON 友好格式 |
| `status_checks.py` | 状态检查：MongoDB/Redis 连接状态、版本信息、性能指标、连接测试 |

## For AI Agents

### Working In This Directory
- 所有函数均为 `async`，阻塞 I/O 操作使用 `asyncio.to_thread` 包装
- `backups.py` 提供两种备份方式：`create_backup_native`（mongodump，推荐）和 `create_backup`（Python，兼容性好）
- 导入数据自动检测格式：新版（含 `export_info`）和旧版（直接集合映射）
- `_sanitize_document` 递归清空敏感字段（api_key、password 等），排除 `max_tokens` 等配置字段
- `cleanup.py` 三个函数分别清理不同集合，均按 `created_at`/`timestamp` 字段判断过期
- `serialization.py` 的 `serialize_document` 递归处理嵌套 dict/list 中的 ObjectId 和 datetime
- `status_checks.py` 返回 MongoDB/Redis 的连接状态、版本、内存等运维指标

### Common Patterns
- 创建备份：`await create_backup_native(name, backup_dir, collections)` 或 `await create_backup(name, backup_dir, collections)`
- 导入数据：`await import_data(content, collection, format="json", overwrite=False)`
- 导出数据：`await export_data(collections, export_dir=dir, format="json", sanitize=False)`
- 清理旧数据：`await cleanup_old_data(days)` / `await cleanup_analysis_results(days)` / `await cleanup_operation_logs(days)`
- 检查状态：`await get_database_status()` → `{mongodb: {...}, redis: {...}}`
- 测试连接：`await test_connections()` → `{mongodb: {success}, redis: {success}, overall: bool}`

### Dependencies

#### Internal
- `app/core/database` - MongoDB/Redis 连接
- `app/core/config` - 配置（MONGO_URI、主机端口等）

#### External
- MongoDB (Motor) - 数据存储
- Redis (aioredis) - 缓存
- mongodump - 原生备份工具（可选）
- pandas - CSV/XLSX 导出
- openpyxl - Excel 写入
- gzip - 压缩备份文件
- python-dateutil - 日期解析

<!-- MANUAL: Custom project notes can be added below -->
