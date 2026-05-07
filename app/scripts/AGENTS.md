<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# scripts

## Purpose
后端运维与数据维护脚本集合，负责 LLM 供应商数据初始化、MongoDB 数据库迁移以及供应商键名规范化，确保系统配置数据的一致性与可迁移性。

## Key Files

| File | Description |
|------|-------------|
| `init_providers.py` | 初始化 LLM 供应商数据到 MongoDB `llm_providers` 集合，预设 OpenAI、Anthropic、Google、智谱AI、DeepSeek、阿里云百炼、硅基流动、302.AI、AIHubMix、Ollama、LM Studio 等厂家的名称、描述、API 地址及支持功能，执行前会清除已有数据 |
| `migrate_mongo_db.py` | MongoDB 跨库迁移工具，支持在源库与目标库之间按集合复制文档，提供增量迁移（基于 `updated_at`/`created_at` 时间戳）、默认排除大集合（行情、新闻等）、批量 upsert、dry-run 预览、文档数量限制及迁移摘要 JSON 输出 |
| `normalize_provider_keys.py` | 供应商键名规范化脚本，将 `llm_providers`、`system_configs`、`model_catalog` 三个集合中的供应商名称统一为规范形式（如 `dashscope` → `qwen`），合并同义重复记录，支持 dry-run 预览与唯一索引修复 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 这些脚本直接操作 MongoDB，运行前确保数据库服务可用且连接配置正确
- `init_providers.py` 会**清除并重建** `llm_providers` 集合，生产环境慎用
- `migrate_mongo_db.py` 和 `normalize_provider_keys.py` 均支持 `--dry-run`，建议先预览再执行
- 供应商别名映射来自 `tradingagents.llm_clients.provider_keys` 模块的 `canonical_aliases` 和 `normalize_provider_key`

### Testing Requirements
- 手动执行验证：`python -m app.scripts.init_providers`
- 迁移预览：`python -m app.scripts.migrate_mongo_db --dry-run`
- 规范化预览：`python -m app.scripts.normalize_provider_keys --dry-run`
- 查看默认排除集合：`python -m app.scripts.migrate_mongo_db --show-default-excludes`

### Common Patterns
- 异步数据库操作：`from app.core.database import init_db, get_mongo_db`
- 同步数据库操作：`from pymongo import MongoClient` + `from app.core.config import settings`
- 供应商键名规范化：`from tradingagents.llm_clients.provider_keys import canonical_aliases, normalize_provider_key`
- 命令行参数解析：统一使用 `argparse`，入口函数 `main(argv)` 返回退出码

## Dependencies

### Internal
- `app.core.database` — 异步 MongoDB 连接（init_providers 使用）
- `app.core.config` — 同步配置读取（settings.MONGO_URI 等）
- `app.models.config` — 数据模型定义（LLMProvider）
- `tradingagents.llm_clients.provider_keys` — 供应商键名规范映射

### External
- `pymongo` — MongoDB 同步驱动
- `motor` — MongoDB 异步驱动（通过 app.core.database 间接使用）

<!-- MANUAL: Custom project notes can be added below -->
