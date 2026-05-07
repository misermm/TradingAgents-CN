<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests/services

## Purpose
服务层测试，验证后端业务服务的核心逻辑（行情回填、选股筛选等）。

## Key Files

| File | Description |
|------|-------------|
| `test_quotes_backfill.py` | 测试 QuotesIngestionService 非交易时段回填：空数据库触发 backfill、Mock DataSourceManager 和 MongoDB Collection |
| `test_screening_roe_field.py` | 测试 DatabaseScreeningService ROE 字段：构建 $gte/$lte 查询、结果中保留 roe 字段值 |

## For AI Agents

### Working In This Directory
- 两个服务均使用 `asyncio.run()` 执行异步方法
- Mock 策略：`monkeypatch.setattr` 替换模块级依赖（DataSourceManager、get_mongo_db）
- QuotesIngestionService 测试验证：非交易时间 + 空集合 → 触发 bulk_write
- DatabaseScreeningService 测试验证：ROE between 查询构建 + 结果格式化保留 roe 字段

### Testing Requirements
- 运行：`python -m pytest tests/services/ -v`
- 无需真实 MongoDB，全部 Mock

### Common Patterns
- 异步测试模式：`asyncio.run(_run())` 包装
- Mock MongoDB 层级：`_FakeDB → _FakeColl → _FakeCursor`
- `monkeypatch.setattr(module, "ClassName", FakeClass)` 替换服务依赖

## Dependencies

### Internal
- `app.services.quotes_ingestion_service` - 行情数据采集服务
- `app.services.database_screening_service` - 数据库选股服务
- `app.core.database` - 数据库连接

### External
- pytest - 测试框架

<!-- MANUAL: Custom project notes can be added below -->
