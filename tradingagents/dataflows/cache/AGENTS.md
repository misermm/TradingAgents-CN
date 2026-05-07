<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# cache

## Purpose
数据缓存层，提供多级缓存策略（文件缓存、MongoDB 缓存、自适应缓存），减少重复数据获取，提升性能。

## Key Files

| File | Description |
|------|-------------|
| `cache_config.py` | 缓存配置：TTL、容量等参数 |
| `file_cache.py` | 文件缓存：本地文件系统缓存 |
| `db_cache.py` | 数据库缓存：MongoDB 缓存 |
| `mongodb_cache_adapter.py` | MongoDB 缓存适配器 |
| `app_adapter.py` | 应用层缓存适配器 |
| `adaptive.py` | 自适应缓存：根据访问模式自动调整策略 |
| `integrated.py` | 集成缓存：组合多种缓存策略 |
| `__init__.py` | 包初始化 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `data_cache/` | 缓存数据存储 (含 us_fundamentals 等) |

## For AI Agents

### Working In This Directory
- 缓存优先级：内存 → 文件 → MongoDB → 远程获取
- 自适应缓存根据数据访问频率调整 TTL
- 新增缓存策略需实现缓存接口

### Testing Requirements
- 缓存测试：`python -m pytest tests/ -k "cache" -v`

### Common Patterns
- 缓存模式：检查缓存 → 命中则返回 → 未命中则获取 → 写入缓存

## Dependencies

### Internal
- `tradingagents/config/` - 数据库配置

### External
- MongoDB - 缓存存储
- Redis - 缓存存储

<!-- MANUAL: Custom project notes can be added below -->
